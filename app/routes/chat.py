"""
AI Chat API routes for the HR AI Assistant.

This module contains all chat-related endpoints including conversation
management, AI query processing, and chat analytics.
"""

import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.config.database import get_db
from app.models.employee import Employee
from app.models.query import ChatSession, QueryLog, SessionStatus, QueryStatus, QueryCategory
from app.schemas.chat import (
    ChatMessage, ChatResponse, ChatSessionCreate, ChatSessionUpdate, 
    ChatSessionResponse, QueryLogResponse, ChatSearchParams, ChatAnalytics,
    ChatFeedback, ChatEscalation, AutocompleteResponse
)
from app.services.groq_service import groq_service
from app.services.notification_service import notification_service
from app.middleware.auth import get_current_active_user
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new chat session
    
    Args:
        session_data: Chat session creation data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ChatSessionResponse: Created chat session
    """
    try:
        session_id = f"chat_{secrets.token_hex(16)}"
        
        chat_session = ChatSession(
            session_id=session_id,
            employee_id=current_user.id,
            title=session_data.title,
            category=session_data.category,
            status=SessionStatus.ACTIVE
        )
        
        if session_data.context_data:
            chat_session.set_context_data(session_data.context_data)
        
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
        
        logger.info(f"Chat session created: {session_id} for user {current_user.employee_id}")
        
        return ChatSessionResponse.from_orm(chat_session)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session"
        )

@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_message(
    session_id: str,
    message: ChatMessage,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Send a message in chat session and get AI response
    
    Args:
        session_id: Chat session ID
        message: User message
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ChatResponse: AI response to the message
    """
    try:
        # Get chat session
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.employee_id == current_user.id
        ).first()
        
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        if chat_session.status != SessionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chat session is not active"
            )
        
        # Get conversation history for context
        recent_queries = db.query(QueryLog).filter(
            QueryLog.chat_session_id == chat_session.id
        ).order_by(QueryLog.query_timestamp.desc()).limit(10).all()
        
        conversation_history = []
        for query in reversed(recent_queries):
            conversation_history.extend([
                {"role": "user", "content": query.user_query},
                {"role": "assistant", "content": query.ai_response}
            ])
        
        # Generate AI response
        ai_response_data = groq_service.generate_response(
            query=message.content,
            user=current_user,
            conversation_history=conversation_history,
            use_rag=True
        )
        
        # Create query log
        query_log = QueryLog(
            chat_session_id=chat_session.id,
            employee_id=current_user.id,
            user_query=message.content,
            ai_response=ai_response_data["message"],
            query_category=ai_response_data.get("intent", QueryCategory.GENERAL_HR),
            intent_detected=ai_response_data.get("intent", QueryCategory.GENERAL_HR).value,
            processing_time_ms=ai_response_data.get("processing_time_ms", 0),
            tokens_used=ai_response_data.get("tokens_used", 0),
            model_used=ai_response_data.get("model_used", ""),
            confidence_score=ai_response_data.get("confidence_score", 0),
            context_retrieved=ai_response_data.get("context_used", False),
            rag_score=ai_response_data.get("rag_score", 0),
            complexity_level=ai_response_data.get("complexity_level", "medium"),
            status=QueryStatus.ESCALATED if ai_response_data.get("requires_escalation") else QueryStatus.ANSWERED,
            requires_escalation=ai_response_data.get("requires_escalation", False),
            escalation_reason=ai_response_data.get("escalation_reason"),
            user_sentiment=ai_response_data.get("sentiment"),
            sentiment_score=ai_response_data.get("sentiment_score", 0)
        )
        
        # Set documents used for RAG
        if ai_response_data.get("context_sources"):
            doc_ids = [source.get("document_id") for source in ai_response_data["context_sources"] if source.get("document_id")]
            query_log.set_documents_used(doc_ids)
        
        db.add(query_log)
        
        # Update chat session
        chat_session.increment_message_count(is_user_message=True)  # User message
        chat_session.increment_message_count(is_user_message=False)  # AI message
        
        db.commit()
        db.refresh(query_log)
        
        # Send escalation notification if required
        if ai_response_data.get("requires_escalation"):
            try:
                # This would notify HR about the escalation
                # notification_service.notify_escalation(query_log, current_user)
                logger.info(f"Query escalated: {query_log.id}")
            except Exception as e:
                logger.warning(f"Failed to send escalation notification: {e}")
        
        return ChatResponse(
            message=ai_response_data["message"],
            session_id=session_id,
            query_id=query_log.id,
            confidence_score=ai_response_data.get("confidence_score"),
            processing_time_ms=ai_response_data.get("processing_time_ms"),
            context_used=ai_response_data.get("context_used", False),
            documents_referenced=[
                source.get("title", "") for source in ai_response_data.get("context_sources", [])
            ],
            suggested_actions=ai_response_data.get("suggested_actions", []),
            requires_escalation=ai_response_data.get("requires_escalation", False),
            escalation_reason=ai_response_data.get("escalation_reason"),
            metadata=ai_response_data.get("metadata", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )

@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_chat_sessions(
    search_params: ChatSearchParams = Depends(),
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get user's chat sessions with filtering and pagination
    
    Args:
        search_params: Search and filter parameters
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[ChatSessionResponse]: List of chat sessions
    """
    try:
        query = db.query(ChatSession).filter(ChatSession.employee_id == current_user.id)
        
        # Apply filters
        if search_params.category:
            query = query.filter(ChatSession.category == search_params.category)
        
        if search_params.status:
            query = query.filter(ChatSession.status == search_params.status)
        
        if search_params.date_from:
            query = query.filter(ChatSession.created_at >= search_params.date_from)
        
        if search_params.date_to:
            query = query.filter(ChatSession.created_at <= search_params.date_to)
        
        # Apply sorting
        if search_params.sort_by == "created_at":
            if search_params.sort_order == "desc":
                query = query.order_by(ChatSession.created_at.desc())
            else:
                query = query.order_by(ChatSession.created_at.asc())
        elif search_params.sort_by == "last_activity":
            if search_params.sort_order == "desc":
                query = query.order_by(ChatSession.last_activity.desc())
            else:
                query = query.order_by(ChatSession.last_activity.asc())
        
        # Apply pagination
        sessions = query.offset(search_params.skip).limit(search_params.limit).all()
        
        return [ChatSessionResponse.from_orm(session) for session in sessions]
        
    except Exception as e:
        logger.error(f"Error retrieving chat sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat sessions"
        )

@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: str,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get specific chat session details
    
    Args:
        session_id: Chat session ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ChatSessionResponse: Chat session details
    """
    try:
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.employee_id == current_user.id
        ).first()
        
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        return ChatSessionResponse.from_orm(chat_session)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat session"
        )

@router.get("/sessions/{session_id}/messages", response_model=List[QueryLogResponse])
async def get_chat_messages(
    session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get messages from a chat session
    
    Args:
        session_id: Chat session ID
        skip: Number of messages to skip
        limit: Maximum number of messages to return
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[QueryLogResponse]: List of chat messages
    """
    try:
        # Verify session ownership
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.employee_id == current_user.id
        ).first()
        
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # Get messages
        messages = db.query(QueryLog).filter(
            QueryLog.chat_session_id == chat_session.id
        ).order_by(QueryLog.query_timestamp.asc()).offset(skip).limit(limit).all()
        
        return [QueryLogResponse.from_orm(message) for message in messages]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chat messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat messages"
        )

@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_id: str,
    session_update: ChatSessionUpdate,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update chat session details
    
    Args:
        session_id: Chat session ID
        session_update: Session update data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ChatSessionResponse: Updated chat session
    """
    try:
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.employee_id == current_user.id
        ).first()
        
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # Update fields
        update_data = session_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(chat_session, field):
                setattr(chat_session, field, value)
        
        chat_session.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(chat_session)
        
        return ChatSessionResponse.from_orm(chat_session)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update chat session"
        )

@router.post("/sessions/{session_id}/end")
async def end_chat_session(
    session_id: str,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    End a chat session
    
    Args:
        session_id: Chat session ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Confirmation message
    """
    try:
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.employee_id == current_user.id
        ).first()
        
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        chat_session.end_session()
        db.commit()
        
        return {"message": "Chat session ended successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error ending chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to end chat session"
        )

@router.post("/feedback")
async def submit_feedback(
    feedback: ChatFeedback,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Submit feedback for a chat query or session
    
    Args:
        feedback: Feedback data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Feedback submission confirmation
    """
    try:
        if feedback.query_id:
            # Update specific query
            query = db.query(QueryLog).filter(
                QueryLog.id == feedback.query_id,
                QueryLog.employee_id == current_user.id
            ).first()
            
            if not query:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Query not found"
                )
            
            query.was_helpful = feedback.was_helpful
            query.user_rating = feedback.rating
            query.user_feedback = feedback.feedback_text
            
        elif feedback.session_id:
            # Update session
            session = db.query(ChatSession).filter(
                ChatSession.session_id == feedback.session_id,
                ChatSession.employee_id == current_user.id
            ).first()
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
            
            session.was_helpful = feedback.was_helpful
            session.satisfaction_rating = feedback.rating
            session.user_feedback = feedback.feedback_text
        
        db.commit()
        
        logger.info(f"Feedback submitted by user {current_user.employee_id}")
        
        return {"message": "Feedback submitted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )

@router.post("/escalate")
async def escalate_query(
    escalation: ChatEscalation,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Escalate a query to human support
    
    Args:
        escalation: Escalation data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Escalation confirmation
    """
    try:
        query = db.query(QueryLog).filter(
            QueryLog.id == escalation.query_id,
            QueryLog.employee_id == current_user.id
        ).first()
        
        if not query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Query not found"
            )
        
        query.mark_as_escalated(escalation.reason)
        query.hr_action_required = True
        
        db.commit()
        
        # Send notification to HR
        try:
            # This would send an escalation notification
            logger.info(f"Query escalated: {query.id} by {current_user.employee_id}")
        except Exception as e:
            logger.warning(f"Failed to send escalation notification: {e}")
        
        return {"message": "Query escalated to HR successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error escalating query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to escalate query"
        )

@router.get("/suggestions", response_model=AutocompleteResponse)
async def get_query_suggestions(
    q: str = Query(..., min_length=1, max_length=100),
    current_user: Employee = Depends(get_current_active_user)
):
    """
    Get query suggestions for autocomplete
    
    Args:
        q: Partial query string
        current_user: Current authenticated user
        
    Returns:
        AutocompleteResponse: Query suggestions
    """
    try:
        suggestions = groq_service.generate_query_suggestions(q, current_user)
        
        return AutocompleteResponse(
            suggestions=[
                {
                    "text": suggestion,
                    "category": "general_hr",  # Could be enhanced with better categorization
                    "confidence": 0.8,
                    "description": None
                }
                for suggestion in suggestions
            ],
            total_suggestions=len(suggestions)
        )
        
    except Exception as e:
        logger.error(f"Error generating query suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate suggestions"
        )

@router.get("/analytics", response_model=ChatAnalytics)
async def get_chat_analytics(
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get chat analytics for current user
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ChatAnalytics: User's chat analytics
    """
    try:
        from sqlalchemy import func, case
        
        # Basic session stats
        total_sessions = db.query(ChatSession).filter(
            ChatSession.employee_id == current_user.id
        ).count()
        
        active_sessions = db.query(ChatSession).filter(
            ChatSession.employee_id == current_user.id,
            ChatSession.status == SessionStatus.ACTIVE
        ).count()
        
        # Query stats
        total_queries = db.query(QueryLog).filter(
            QueryLog.employee_id == current_user.id
        ).count()
        
        # Average session duration
        avg_duration = db.query(func.avg(ChatSession.duration_seconds)).filter(
            ChatSession.employee_id == current_user.id,
            ChatSession.duration_seconds.isnot(None)
        ).scalar() or 0
        
        # Average messages per session
        avg_messages = db.query(func.avg(ChatSession.total_messages)).filter(
            ChatSession.employee_id == current_user.id
        ).scalar() or 0
        
        # Satisfaction score
        satisfaction_score = db.query(func.avg(ChatSession.satisfaction_rating)).filter(
            ChatSession.employee_id == current_user.id,
            ChatSession.satisfaction_rating.isnot(None)
        ).scalar() or 0
        
        # Resolution rate (queries that were marked as helpful)
        resolved_queries = db.query(QueryLog).filter(
            QueryLog.employee_id == current_user.id,
            QueryLog.was_helpful == True
        ).count()
        
        resolution_rate = (resolved_queries / total_queries * 100) if total_queries > 0 else 0
        
        # Escalation rate
        escalated_queries = db.query(QueryLog).filter(
            QueryLog.employee_id == current_user.id,
            QueryLog.requires_escalation == True
        ).count()
        
        escalation_rate = (escalated_queries / total_queries * 100) if total_queries > 0 else 0
        
        # Top categories
        category_stats = db.query(
            QueryLog.query_category,
            func.count(QueryLog.id).label('count')
        ).filter(
            QueryLog.employee_id == current_user.id
        ).group_by(QueryLog.query_category).all()
        
        top_categories = [
            {"category": cat.value, "count": count}
            for cat, count in category_stats
        ]
        
        # Sentiment breakdown
        sentiment_stats = db.query(
            QueryLog.user_sentiment,
            func.count(QueryLog.id).label('count')
        ).filter(
            QueryLog.employee_id == current_user.id,
            QueryLog.user_sentiment.isnot(None)
        ).group_by(QueryLog.user_sentiment).all()
        
        sentiment_breakdown = {
            sentiment.value if sentiment else "unknown": count
            for sentiment, count in sentiment_stats
        }
        
        return ChatAnalytics(
            total_sessions=total_sessions,
            active_sessions=active_sessions,
            total_queries=total_queries,
            average_session_duration=avg_duration / 60 if avg_duration else 0,  # Convert to minutes
            average_messages_per_session=avg_messages,
            satisfaction_score=satisfaction_score,
            resolution_rate=resolution_rate,
            escalation_rate=escalation_rate,
            top_categories=top_categories,
            sentiment_breakdown=sentiment_breakdown,
            daily_activity=[]  # This could be enhanced with daily breakdown
        )
        
    except Exception as e:
        logger.error(f"Error generating chat analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate analytics"
        )
"""
Query tracking and chat session models for the HR AI Assistant.

This module contains SQLAlchemy ORM models for tracking user queries,
chat sessions, and AI interaction analytics.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Numeric, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum
import json

from app.config.database import Base

class QueryCategory(enum.Enum):
    """Query category enumeration"""
    LEAVE_MANAGEMENT = "leave_management"
    DOCUMENT_REQUEST = "document_request"
    POLICY_QUESTION = "policy_question"
    BENEFITS_INQUIRY = "benefits_inquiry"
    PAYROLL_QUERY = "payroll_query"
    TRAINING_REQUEST = "training_request"
    GENERAL_HR = "general_hr"
    TECHNICAL_SUPPORT = "technical_support"
    FEEDBACK = "feedback"
    OTHER = "other"

class QueryStatus(enum.Enum):
    """Query status enumeration"""
    ANSWERED = "answered"
    PARTIALLY_ANSWERED = "partially_answered"
    ESCALATED = "escalated"
    PENDING = "pending"
    FAILED = "failed"

class SessionStatus(enum.Enum):
    """Chat session status enumeration"""
    ACTIVE = "active"
    ENDED = "ended"
    TIMEOUT = "timeout"
    ERROR = "error"

class SentimentType(enum.Enum):
    """Sentiment analysis enumeration"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"

class ChatSession(Base):
    """Chat session model for tracking user conversations"""
    
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), unique=True, nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # Session details
    title = Column(String(200))  # Auto-generated or user-provided
    description = Column(Text)
    category = Column(Enum(QueryCategory), default=QueryCategory.GENERAL_HR)
    
    # Session metadata
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE)
    total_messages = Column(Integer, default=0)
    user_messages = Column(Integer, default=0)
    ai_messages = Column(Integer, default=0)
    
    # Timing information
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    last_activity = Column(DateTime, default=datetime.utcnow)
    duration_seconds = Column(Integer)
    
    # Session analytics
    satisfaction_rating = Column(Integer)  # 1-5 scale
    was_helpful = Column(Boolean)
    user_feedback = Column(Text)
    resolution_status = Column(String(20))  # resolved, unresolved, escalated
    
    # AI performance metrics
    average_response_time = Column(Numeric(8, 3))  # In seconds
    total_tokens_used = Column(Integer, default=0)
    ai_confidence_avg = Column(Numeric(5, 2))  # Average confidence score
    
    # Context and personalization
    context_data = Column(JSON)  # Stored conversation context
    user_preferences = Column(JSON)  # User interaction preferences
    
    # System fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = relationship("Employee", back_populates="chat_sessions")
    query_logs = relationship("QueryLog", back_populates="chat_session")
    
    @property
    def is_active(self) -> bool:
        """Check if session is currently active"""
        return self.status == SessionStatus.ACTIVE
    
    @property
    def duration_minutes(self) -> float:
        """Get session duration in minutes"""
        if self.duration_seconds:
            return round(self.duration_seconds / 60, 2)
        return 0.0
    
    @property
    def messages_per_minute(self) -> float:
        """Calculate messages per minute rate"""
        if self.duration_minutes > 0:
            return round(self.total_messages / self.duration_minutes, 2)
        return 0.0
    
    def end_session(self):
        """End the chat session"""
        self.status = SessionStatus.ENDED
        self.ended_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = int((self.ended_at - self.started_at).total_seconds())
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    def increment_message_count(self, is_user_message: bool = True):
        """Increment message counters"""
        self.total_messages += 1
        if is_user_message:
            self.user_messages += 1
        else:
            self.ai_messages += 1
        self.update_activity()
    
    def get_context_data(self) -> Dict[str, Any]:
        """Get context data as dictionary"""
        if self.context_data:
            return json.loads(self.context_data) if isinstance(self.context_data, str) else self.context_data
        return {}
    
    def set_context_data(self, context: Dict[str, Any]):
        """Set context data from dictionary"""
        self.context_data = json.dumps(context) if isinstance(context, dict) else context
    
    def to_dict(self) -> dict:
        """Convert chat session to dictionary representation"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "employee_id": self.employee.employee_id if self.employee else None,
            "title": self.title,
            "category": self.category.value if self.category else None,
            "status": self.status.value if self.status else None,
            "total_messages": self.total_messages,
            "user_messages": self.user_messages,
            "ai_messages": self.ai_messages,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_minutes": self.duration_minutes,
            "messages_per_minute": self.messages_per_minute,
            "satisfaction_rating": self.satisfaction_rating,
            "was_helpful": self.was_helpful,
            "resolution_status": self.resolution_status,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<ChatSession(id={self.id}, session_id='{self.session_id}', employee_id={self.employee_id})>"

class QueryLog(Base):
    """Query log model for tracking individual AI queries and responses"""
    
    __tablename__ = "query_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # Query details
    user_query = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    query_category = Column(Enum(QueryCategory), default=QueryCategory.GENERAL_HR)
    intent_detected = Column(String(100))  # Detected user intent
    
    # AI processing information
    processing_time_ms = Column(Integer)  # Processing time in milliseconds
    tokens_used = Column(Integer, default=0)
    model_used = Column(String(50))
    confidence_score = Column(Numeric(5, 2))  # AI confidence in response
    
    # Context and RAG information
    context_retrieved = Column(Boolean, default=False)
    documents_used = Column(JSON)  # Array of document IDs used for context
    rag_score = Column(Numeric(5, 2))  # Relevance score for retrieved context
    
    # Query classification
    complexity_level = Column(String(20))  # simple, medium, complex
    requires_escalation = Column(Boolean, default=False)
    escalation_reason = Column(Text)
    
    # User interaction
    was_helpful = Column(Boolean)
    user_rating = Column(Integer)  # 1-5 scale
    user_feedback = Column(Text)
    follow_up_needed = Column(Boolean, default=False)
    
    # Sentiment analysis
    user_sentiment = Column(Enum(SentimentType))
    sentiment_score = Column(Numeric(5, 2))  # -1 to 1 scale
    emotion_detected = Column(String(50))  # anger, frustration, satisfaction, etc.
    
    # Query resolution
    status = Column(Enum(QueryStatus), default=QueryStatus.ANSWERED)
    resolution_notes = Column(Text)
    hr_action_required = Column(Boolean, default=False)
    action_taken = Column(Text)
    
    # System fields
    query_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chat_session = relationship("ChatSession", back_populates="query_logs")
    employee = relationship("Employee", back_populates="query_logs")
    
    @property
    def processing_time_seconds(self) -> float:
        """Get processing time in seconds"""
        if self.processing_time_ms:
            return self.processing_time_ms / 1000.0
        return 0.0
    
    @property
    def is_resolved(self) -> bool:
        """Check if query is resolved"""
        return self.status == QueryStatus.ANSWERED
    
    @property
    def needs_attention(self) -> bool:
        """Check if query needs human attention"""
        return (self.requires_escalation or 
                self.hr_action_required or 
                self.status in [QueryStatus.FAILED, QueryStatus.PENDING])
    
    def get_documents_used(self) -> List[int]:
        """Get list of document IDs used for context"""
        if self.documents_used:
            docs = json.loads(self.documents_used) if isinstance(self.documents_used, str) else self.documents_used
            return docs if isinstance(docs, list) else []
        return []
    
    def set_documents_used(self, document_ids: List[int]):
        """Set document IDs used for context"""
        self.documents_used = json.dumps(document_ids) if isinstance(document_ids, list) else document_ids
    
    def mark_as_helpful(self, rating: int = 5, feedback: str = None):
        """Mark query as helpful with rating and feedback"""
        self.was_helpful = True
        self.user_rating = rating
        if feedback:
            self.user_feedback = feedback
    
    def mark_as_escalated(self, reason: str):
        """Mark query for escalation"""
        self.requires_escalation = True
        self.escalation_reason = reason
        self.status = QueryStatus.ESCALATED
    
    def to_dict(self) -> dict:
        """Convert query log to dictionary representation"""
        return {
            "id": self.id,
            "chat_session_id": self.chat_session_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "employee_id": self.employee.employee_id if self.employee else None,
            "user_query": self.user_query,
            "ai_response": self.ai_response,
            "query_category": self.query_category.value if self.query_category else None,
            "intent_detected": self.intent_detected,
            "processing_time_seconds": self.processing_time_seconds,
            "tokens_used": self.tokens_used,
            "model_used": self.model_used,
            "confidence_score": float(self.confidence_score) if self.confidence_score else None,
            "context_retrieved": self.context_retrieved,
            "rag_score": float(self.rag_score) if self.rag_score else None,
            "complexity_level": self.complexity_level,
            "status": self.status.value if self.status else None,
            "was_helpful": self.was_helpful,
            "user_rating": self.user_rating,
            "user_sentiment": self.user_sentiment.value if self.user_sentiment else None,
            "sentiment_score": float(self.sentiment_score) if self.sentiment_score else None,
            "requires_escalation": self.requires_escalation,
            "hr_action_required": self.hr_action_required,
            "needs_attention": self.needs_attention,
            "query_timestamp": self.query_timestamp.isoformat() if self.query_timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<QueryLog(id={self.id}, employee_id={self.employee_id}, category='{self.query_category.value}', timestamp='{self.query_timestamp}')>"
"""
Groq AI service for the HR AI Assistant.

This service handles AI chat functionality, natural language processing,
and intelligent response generation using Groq's language models.
"""

import time
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from groq import Groq

from app.config.groq_config import get_groq_client, groq_config, get_hr_system_prompt
from app.services.rag_service import rag_service
from app.models.employee import Employee
from app.schemas.chat import QueryCategoryEnum, SentimentEnum
from app.utils.logger import get_logger

logger = get_logger(__name__)

class GroqService:
    """
    Groq AI service for intelligent HR assistance
    """
    
    def __init__(self):
        self.client = None
        self.model = groq_config.model
        self.max_tokens = groq_config.max_tokens
        self.temperature = groq_config.temperature
        
        # Response configuration
        self.max_context_length = 2000
        self.confidence_threshold = 0.6
        self.escalation_threshold = 0.3
        
        # Intent patterns for query classification
        self.intent_patterns = {
            "leave_request": [
                "leave", "vacation", "sick", "time off", "holiday", "absent", "pto"
            ],
            "document_request": [
                "document", "certificate", "letter", "form", "paper", "download"
            ],
            "policy_question": [
                "policy", "rule", "guideline", "procedure", "regulation", "handbook"
            ],
            "benefits_inquiry": [
                "benefit", "insurance", "health", "dental", "retirement", "401k", "medical"
            ],
            "payroll_query": [
                "salary", "pay", "payroll", "bonus", "overtime", "deduction", "tax"
            ],
            "training_request": [
                "training", "course", "workshop", "certification", "skill", "development"
            ]
        }
    
    def _get_client(self) -> Groq:
        """Get Groq client instance"""
        if self.client is None:
            self.client = get_groq_client()
        return self.client
    
    def classify_query_intent(self, query: str) -> Tuple[QueryCategoryEnum, float]:
        """
        Classify user query intent using keyword matching and patterns
        
        Args:
            query: User query text
            
        Returns:
            Tuple[QueryCategoryEnum, float]: (intent, confidence_score)
        """
        query_lower = query.lower()
        intent_scores = {}
        
        # Calculate scores for each intent
        for intent, keywords in self.intent_patterns.items():
            score = 0
            for keyword in keywords:
                if keyword in query_lower:
                    score += 1
            
            if score > 0:
                intent_scores[intent] = score / len(keywords)
        
        # Find best matching intent
        if not intent_scores:
            return QueryCategoryEnum.GENERAL_HR, 0.5
        
        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[best_intent]
        
        # Map to enum
        intent_mapping = {
            "leave_request": QueryCategoryEnum.LEAVE_MANAGEMENT,
            "document_request": QueryCategoryEnum.DOCUMENT_REQUEST,
            "policy_question": QueryCategoryEnum.POLICY_QUESTION,
            "benefits_inquiry": QueryCategoryEnum.BENEFITS_INQUIRY,
            "payroll_query": QueryCategoryEnum.PAYROLL_QUERY,
            "training_request": QueryCategoryEnum.TRAINING_REQUEST
        }
        
        return intent_mapping.get(best_intent, QueryCategoryEnum.GENERAL_HR), confidence
    
    def analyze_sentiment(self, text: str) -> Tuple[SentimentEnum, float]:
        """
        Analyze sentiment of user text using simple keyword-based approach
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple[SentimentEnum, float]: (sentiment, confidence_score)
        """
        text_lower = text.lower()
        
        # Simple keyword-based sentiment analysis
        positive_words = [
            "good", "great", "excellent", "happy", "satisfied", "pleased", "helpful",
            "thanks", "thank you", "appreciate", "wonderful", "amazing", "perfect"
        ]
        
        negative_words = [
            "bad", "terrible", "awful", "angry", "frustrated", "disappointed", "unhappy",
            "hate", "horrible", "worst", "useless", "annoying", "difficult", "problem"
        ]
        
        positive_score = sum(1 for word in positive_words if word in text_lower)
        negative_score = sum(1 for word in negative_words if word in text_lower)
        
        total_score = positive_score + negative_score
        
        if total_score == 0:
            return SentimentEnum.NEUTRAL, 0.5
        
        if positive_score > negative_score:
            confidence = positive_score / total_score
            return SentimentEnum.POSITIVE, confidence
        elif negative_score > positive_score:
            confidence = negative_score / total_score
            return SentimentEnum.NEGATIVE, confidence
        else:
            return SentimentEnum.MIXED, 0.5
    
    def should_escalate(self, query: str, confidence: float, sentiment: SentimentEnum) -> Tuple[bool, str]:
        """
        Determine if query should be escalated to human HR
        
        Args:
            query: User query
            confidence: AI confidence in response
            sentiment: User sentiment
            
        Returns:
            Tuple[bool, str]: (should_escalate, reason)
        """
        escalation_triggers = [
            "complaint", "harassment", "discrimination", "legal", "lawsuit",
            "terminate", "fire", "quit", "resign", "disciplinary", "grievance",
            "urgent", "emergency", "serious", "violation", "report"
        ]
        
        query_lower = query.lower()
        
        # Check for escalation trigger words
        for trigger in escalation_triggers:
            if trigger in query_lower:
                return True, f"Contains escalation trigger: {trigger}"
        
        # Check confidence threshold
        if confidence < self.escalation_threshold:
            return True, "Low AI confidence in response"
        
        # Check negative sentiment
        if sentiment == SentimentEnum.NEGATIVE:
            return True, "Negative user sentiment detected"
        
        return False, ""
    
    def generate_response(self, 
                         query: str, 
                         user: Optional[Employee] = None,
                         conversation_history: List[Dict[str, str]] = None,
                         use_rag: bool = True) -> Dict[str, Any]:
        """
        Generate AI response to user query
        
        Args:
            query: User query
            user: Current user (for personalization)
            conversation_history: Previous conversation messages
            use_rag: Whether to use RAG for context retrieval
            
        Returns:
            Dict: Response data including message, metadata, and analytics
        """
        start_time = time.time()
        
        try:
            # Classify intent and analyze sentiment
            intent, intent_confidence = self.classify_query_intent(query)
            sentiment, sentiment_score = self.analyze_sentiment(query)
            
            # Get relevant context if RAG is enabled
            context_data = {}
            if use_rag:
                context_data = rag_service.get_relevant_context(query)
            
            # Build system prompt based on intent
            system_prompt = get_hr_system_prompt(intent.value)
            
            # Build messages for API call
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history[-6:])  # Last 6 messages for context
            
            # Add context from RAG if available
            user_message = query
            if context_data.get("has_context"):
                context_text = context_data["context_text"]
                user_message = f"""Based on the following information from our HR documents:

{context_text}

Please answer this question: {query}

If the information provided doesn't fully answer the question, please say so and provide general guidance while recommending the user contact HR for specific details."""
            
            messages.append({"role": "user", "content": user_message})
            
            # Get AI response
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            # Extract response
            ai_message = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Calculate confidence score (simplified)
            confidence_score = self._calculate_confidence(
                ai_message, context_data.get("relevance_score", 0), intent_confidence
            )
            
            # Check if escalation is needed
            should_escalate, escalation_reason = self.should_escalate(
                query, confidence_score, sentiment
            )
            
            # Generate suggested actions
            suggested_actions = self._generate_suggested_actions(intent, ai_message)
            
            return {
                "message": ai_message,
                "intent": intent,
                "intent_confidence": intent_confidence,
                "sentiment": sentiment,
                "sentiment_score": sentiment_score,
                "confidence_score": confidence_score,
                "processing_time_ms": int(processing_time * 1000),
                "tokens_used": tokens_used,
                "model_used": self.model,
                "context_used": context_data.get("has_context", False),
                "context_sources": context_data.get("sources", []),
                "rag_score": context_data.get("relevance_score", 0),
                "requires_escalation": should_escalate,
                "escalation_reason": escalation_reason,
                "suggested_actions": suggested_actions,
                "complexity_level": self._assess_complexity(query, ai_message),
                "metadata": {
                    "user_id": user.id if user else None,
                    "timestamp": datetime.utcnow().isoformat(),
                    "session_data": {
                        "intent_history": [intent.value],
                        "response_quality": confidence_score
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            
            # Return fallback response
            return {
                "message": "I apologize, but I'm having trouble processing your request right now. Please try again later or contact HR directly for assistance.",
                "intent": QueryCategoryEnum.GENERAL_HR,
                "intent_confidence": 0.0,
                "sentiment": SentimentEnum.NEUTRAL,
                "sentiment_score": 0.5,
                "confidence_score": 0.0,
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "tokens_used": 0,
                "model_used": self.model,
                "context_used": False,
                "context_sources": [],
                "rag_score": 0,
                "requires_escalation": True,
                "escalation_reason": "AI service error",
                "suggested_actions": ["Contact HR directly"],
                "complexity_level": "error",
                "error": str(e)
            }
    
    def _calculate_confidence(self, response: str, rag_score: float, intent_confidence: float) -> float:
        """
        Calculate confidence score for AI response
        
        Args:
            response: AI response text
            rag_score: RAG relevance score
            intent_confidence: Intent classification confidence
            
        Returns:
            float: Confidence score (0-1)
        """
        # Base confidence from response characteristics
        base_confidence = 0.5
        
        # Adjust based on response length and completeness
        if len(response) > 50 and "." in response:
            base_confidence += 0.2
        
        # Adjust based on RAG score
        if rag_score > 0.7:
            base_confidence += 0.2
        elif rag_score > 0.5:
            base_confidence += 0.1
        
        # Adjust based on intent confidence
        base_confidence += intent_confidence * 0.1
        
        # Check for uncertainty indicators
        uncertainty_phrases = [
            "i'm not sure", "i don't know", "might be", "possibly", "maybe",
            "you should contact", "please check with", "i recommend contacting"
        ]
        
        response_lower = response.lower()
        for phrase in uncertainty_phrases:
            if phrase in response_lower:
                base_confidence -= 0.1
        
        return max(0.0, min(1.0, base_confidence))
    
    def _assess_complexity(self, query: str, response: str) -> str:
        """
        Assess query complexity level
        
        Args:
            query: User query
            response: AI response
            
        Returns:
            str: Complexity level (simple, medium, complex)
        """
        # Simple heuristics for complexity assessment
        query_length = len(query.split())
        response_length = len(response.split())
        
        if query_length <= 5 and response_length <= 50:
            return "simple"
        elif query_length <= 15 and response_length <= 150:
            return "medium"
        else:
            return "complex"
    
    def _generate_suggested_actions(self, intent: QueryCategoryEnum, response: str) -> List[str]:
        """
        Generate suggested follow-up actions based on intent and response
        
        Args:
            intent: Query intent category
            response: AI response
            
        Returns:
            List[str]: Suggested actions
        """
        suggestions = []
        
        intent_actions = {
            QueryCategoryEnum.LEAVE_MANAGEMENT: [
                "Submit a leave request",
                "Check leave balance",
                "View leave policy"
            ],
            QueryCategoryEnum.DOCUMENT_REQUEST: [
                "Request employment certificate",
                "Download pay slip",
                "Access employee handbook"
            ],
            QueryCategoryEnum.POLICY_QUESTION: [
                "Read full policy document",
                "Contact HR for clarification",
                "Schedule policy training"
            ],
            QueryCategoryEnum.BENEFITS_INQUIRY: [
                "Review benefits package",
                "Contact benefits administrator",
                "Schedule benefits consultation"
            ],
            QueryCategoryEnum.PAYROLL_QUERY: [
                "Check pay slip",
                "Contact payroll department",
                "Update tax information"
            ],
            QueryCategoryEnum.TRAINING_REQUEST: [
                "Browse training catalog",
                "Request training enrollment",
                "Schedule skills assessment"
            ]
        }
        
        suggestions = intent_actions.get(intent, [
            "Contact HR for more information",
            "Browse employee resources",
            "Schedule HR consultation"
        ])
        
        return suggestions[:3]  # Return top 3 suggestions
    
    def generate_query_suggestions(self, partial_query: str, user: Optional[Employee] = None) -> List[str]:
        """
        Generate query suggestions for autocomplete
        
        Args:
            partial_query: Partial user input
            user: Current user (for personalization)
            
        Returns:
            List[str]: Query suggestions
        """
        # Common HR queries for autocomplete
        common_queries = [
            "How do I request sick leave?",
            "What is the company vacation policy?",
            "How do I update my personal information?",
            "Where can I find my pay slip?",
            "How do I enroll in health insurance?",
            "What training programs are available?",
            "How do I report a workplace issue?",
            "What are my benefits?",
            "How do I request a employment certificate?",
            "What is the dress code policy?"
        ]
        
        # Filter suggestions based on partial query
        suggestions = []
        partial_lower = partial_query.lower()
        
        for query in common_queries:
            if partial_lower in query.lower() or any(
                word in query.lower() for word in partial_lower.split()
            ):
                suggestions.append(query)
        
        # Add RAG-based suggestions if available
        try:
            rag_suggestions = rag_service.suggest_related_queries(partial_query, limit=3)
            suggestions.extend(rag_suggestions)
        except Exception:
            pass
        
        return suggestions[:5]  # Return top 5 suggestions

# Global Groq service instance
groq_service = GroqService()
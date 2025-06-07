"""
Chat and query Pydantic schemas for the HR AI Assistant.

This module contains Pydantic models for chat interface validation,
AI query tracking, and conversation management.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

class QueryCategoryEnum(str, Enum):
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

class QueryStatusEnum(str, Enum):
    ANSWERED = "answered"
    PARTIALLY_ANSWERED = "partially_answered"
    ESCALATED = "escalated"
    PENDING = "pending"
    FAILED = "failed"

class SessionStatusEnum(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"
    TIMEOUT = "timeout"
    ERROR = "error"

class SentimentEnum(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"

class MessageRoleEnum(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

# Chat Message Schemas
class ChatMessage(BaseModel):
    role: MessageRoleEnum
    content: str = Field(..., min_length=1, max_length=4000)
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('Message content cannot be empty or only whitespace')
        return v.strip()

class ChatResponse(BaseModel):
    message: str
    session_id: str
    query_id: Optional[int] = None
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[int] = None
    context_used: bool = False
    documents_referenced: List[str] = []
    suggested_actions: List[str] = []
    requires_escalation: bool = False
    escalation_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# Chat Session Schemas
class ChatSessionCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    category: QueryCategoryEnum = QueryCategoryEnum.GENERAL_HR
    context_data: Optional[Dict[str, Any]] = None

class ChatSessionUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    category: Optional[QueryCategoryEnum] = None
    satisfaction_rating: Optional[int] = Field(None, ge=1, le=5)
    was_helpful: Optional[bool] = None
    user_feedback: Optional[str] = Field(None, max_length=1000)
    resolution_status: Optional[str] = Field(None, pattern="^(resolved|unresolved|escalated)$")

class ChatSessionResponse(BaseModel):
    id: int
    session_id: str
    employee_id: int
    employee_name: Optional[str] = None
    title: Optional[str] = None
    category: QueryCategoryEnum
    status: SessionStatusEnum
    total_messages: int
    user_messages: int
    ai_messages: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    last_activity: datetime
    duration_minutes: float
    messages_per_minute: float
    satisfaction_rating: Optional[int] = None
    was_helpful: Optional[bool] = None
    user_feedback: Optional[str] = None
    resolution_status: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Query Log Schemas
class QueryLogCreate(BaseModel):
    user_query: str = Field(..., min_length=1, max_length=4000)
    query_category: QueryCategoryEnum = QueryCategoryEnum.GENERAL_HR
    intent_detected: Optional[str] = Field(None, max_length=100)
    context_data: Optional[Dict[str, Any]] = None

class QueryLogResponse(BaseModel):
    id: int
    chat_session_id: int
    employee_id: int
    employee_name: Optional[str] = None
    user_query: str
    ai_response: str
    query_category: QueryCategoryEnum
    intent_detected: Optional[str] = None
    processing_time_seconds: float
    tokens_used: int
    model_used: Optional[str] = None
    confidence_score: Optional[float] = None
    context_retrieved: bool
    rag_score: Optional[float] = None
    complexity_level: Optional[str] = None
    status: QueryStatusEnum
    was_helpful: Optional[bool] = None
    user_rating: Optional[int] = None
    user_sentiment: Optional[SentimentEnum] = None
    sentiment_score: Optional[float] = None
    requires_escalation: bool
    hr_action_required: bool
    needs_attention: bool
    query_timestamp: datetime
    created_at: datetime

    class Config:
        from_attributes = True

# Chat Conversation Schema
class ChatConversation(BaseModel):
    session: ChatSessionResponse
    messages: List[QueryLogResponse]
    total_messages: int
    has_more: bool = False

# Chat Search and Filter Schemas
class ChatSearchParams(BaseModel):
    employee_id: Optional[int] = None
    category: Optional[QueryCategoryEnum] = None
    status: Optional[SessionStatusEnum] = None
    query_text: Optional[str] = Field(None, max_length=200)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    was_helpful: Optional[bool] = None
    requires_escalation: Optional[bool] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)
    sort_by: Optional[str] = Field("created_at", pattern="^(created_at|last_activity|total_messages|satisfaction_rating)$")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$")

# Chat Analytics Schemas
class ChatAnalytics(BaseModel):
    total_sessions: int
    active_sessions: int
    total_queries: int
    average_session_duration: float
    average_messages_per_session: float
    satisfaction_score: float
    resolution_rate: float
    escalation_rate: float
    top_categories: List[Dict[str, Any]]
    sentiment_breakdown: Dict[str, int]
    daily_activity: List[Dict[str, Any]]

class QueryAnalytics(BaseModel):
    total_queries: int
    answered_queries: int
    escalated_queries: int
    average_processing_time: float
    average_confidence_score: float
    top_intents: List[Dict[str, Any]]
    category_breakdown: Dict[str, int]
    hourly_distribution: List[Dict[str, Any]]
    response_accuracy: float

# AI Model Performance Schema
class ModelPerformance(BaseModel):
    model_name: str
    total_queries: int
    average_processing_time: float
    average_confidence_score: float
    success_rate: float
    user_satisfaction: float
    token_usage: int
    cost_estimate: Optional[float] = None

# Feedback and Rating Schemas
class ChatFeedback(BaseModel):
    query_id: Optional[int] = None
    session_id: Optional[str] = None
    was_helpful: bool
    rating: int = Field(..., ge=1, le=5)
    feedback_text: Optional[str] = Field(None, max_length=1000)
    improvement_suggestions: Optional[str] = Field(None, max_length=500)

class ChatEscalation(BaseModel):
    query_id: int
    reason: str = Field(..., min_length=10, max_length=500)
    priority: str = Field("normal", pattern="^(low|normal|high|urgent)$")
    additional_context: Optional[str] = Field(None, max_length=1000)

# Context and RAG Schemas
class DocumentContext(BaseModel):
    document_id: int
    title: str
    content_snippet: str
    relevance_score: float
    document_type: str

class QueryContext(BaseModel):
    user_profile: Dict[str, Any]
    conversation_history: List[str]
    relevant_documents: List[DocumentContext]
    previous_queries: List[str]
    session_context: Dict[str, Any]

# Suggestion and Autocomplete Schemas
class QuerySuggestion(BaseModel):
    text: str
    category: QueryCategoryEnum
    confidence: float
    description: Optional[str] = None

class AutocompleteResponse(BaseModel):
    suggestions: List[QuerySuggestion]
    total_suggestions: int

# Chat Configuration Schema
class ChatConfig(BaseModel):
    max_session_duration_minutes: int = 60
    max_messages_per_session: int = 100
    auto_escalation_threshold: float = 0.3
    context_window_size: int = 10
    enable_sentiment_analysis: bool = True
    enable_autocomplete: bool = True
    enable_query_suggestions: bool = True
    default_language: str = "en"
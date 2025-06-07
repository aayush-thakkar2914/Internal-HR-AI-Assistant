"""
Survey and engagement Pydantic schemas for the HR AI Assistant.

This module contains Pydantic models for survey validation,
serialization, and API request/response handling.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

class SurveyTypeEnum(str, Enum):
    ENGAGEMENT = "engagement"
    SATISFACTION = "satisfaction"
    FEEDBACK = "feedback"
    EXIT = "exit"
    ONBOARDING = "onboarding"
    PERFORMANCE = "performance"
    PULSE = "pulse"
    CUSTOM = "custom"

class SurveyStatusEnum(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class QuestionTypeEnum(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    SINGLE_CHOICE = "single_choice"
    TEXT = "text"
    TEXTAREA = "textarea"
    RATING = "rating"
    SCALE = "scale"
    YES_NO = "yes_no"
    DATE = "date"
    NUMBER = "number"

class EngagementLevelEnum(str, Enum):
    HIGHLY_ENGAGED = "highly_engaged"
    ENGAGED = "engaged"
    MODERATELY_ENGAGED = "moderately_engaged"
    DISENGAGED = "disengaged"
    HIGHLY_DISENGAGED = "highly_disengaged"

class CompletionStatusEnum(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

# Survey Question Schema
class SurveyQuestion(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    text: str = Field(..., min_length=1, max_length=500)
    type: QuestionTypeEnum
    required: bool = True
    description: Optional[str] = Field(None, max_length=200)
    options: Optional[List[str]] = None  # For choice questions
    scale: Optional[Dict[str, Any]] = None  # For scale/rating questions
    validation: Optional[Dict[str, Any]] = None  # Additional validation rules
    order: Optional[int] = Field(None, ge=1)

    @validator('options')
    def validate_options(cls, v, values):
        question_type = values.get('type')
        if question_type in [QuestionTypeEnum.SINGLE_CHOICE, QuestionTypeEnum.MULTIPLE_CHOICE]:
            if not v or len(v) < 2:
                raise ValueError('Choice questions must have at least 2 options')
        return v

    @validator('scale')
    def validate_scale(cls, v, values):
        question_type = values.get('type')
        if question_type in [QuestionTypeEnum.SCALE, QuestionTypeEnum.RATING]:
            if not v or 'min' not in v or 'max' not in v:
                raise ValueError('Scale questions must have min and max values')
            if v['min'] >= v['max']:
                raise ValueError('Scale min value must be less than max value')
        return v

# Survey Schemas
class SurveyBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    survey_type: SurveyTypeEnum
    instructions: Optional[str] = Field(None, max_length=1000)
    estimated_duration: Optional[int] = Field(None, ge=1, le=300)  # minutes
    is_anonymous: bool = False
    is_mandatory: bool = False
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    reminder_frequency: int = Field(default=7, ge=1, le=30)  # days
    allow_multiple_responses: bool = False
    show_progress: bool = True
    randomize_questions: bool = False
    require_all_questions: bool = True
    target_departments: Optional[List[int]] = None
    target_roles: Optional[List[int]] = None
    target_employees: Optional[List[int]] = None

    @validator('end_date')
    def validate_end_date(cls, v, values):
        if v and values.get('start_date') and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v

    @validator('estimated_duration')
    def validate_duration(cls, v):
        if v and v > 300:  # 5 hours max
            raise ValueError('Estimated duration cannot exceed 300 minutes')
        return v

class SurveyCreate(SurveyBase):
    questions: List[SurveyQuestion] = Field(..., min_items=1)

    @validator('questions')
    def validate_questions(cls, v):
        if not v:
            raise ValueError('Survey must have at least one question')
        
        # Check for duplicate question IDs
        question_ids = [q.id for q in v]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError('Question IDs must be unique')
        
        return v

class SurveyUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    survey_type: Optional[SurveyTypeEnum] = None
    instructions: Optional[str] = Field(None, max_length=1000)
    estimated_duration: Optional[int] = Field(None, ge=1, le=300)
    is_anonymous: Optional[bool] = None
    is_mandatory: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    reminder_frequency: Optional[int] = Field(None, ge=1, le=30)
    allow_multiple_responses: Optional[bool] = None
    show_progress: Optional[bool] = None
    randomize_questions: Optional[bool] = None
    require_all_questions: Optional[bool] = None
    questions: Optional[List[SurveyQuestion]] = None
    target_departments: Optional[List[int]] = None
    target_roles: Optional[List[int]] = None
    target_employees: Optional[List[int]] = None
    status: Optional[SurveyStatusEnum] = None

class SurveyResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    survey_type: SurveyTypeEnum
    instructions: Optional[str] = None
    estimated_duration: Optional[int] = None
    questions: List[SurveyQuestion]
    
    # Settings
    is_anonymous: bool
    is_mandatory: bool
    allow_multiple_responses: bool
    show_progress: bool
    randomize_questions: bool
    require_all_questions: bool
    
    # Scheduling
    status: SurveyStatusEnum
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    reminder_frequency: int
    
    # Targeting
    target_departments: Optional[List[int]] = None
    target_roles: Optional[List[int]] = None
    target_employees: Optional[List[int]] = None
    
    # Analytics
    total_invited: int
    total_responses: int
    completion_rate: float
    response_rate: float
    average_duration: int  # seconds
    
    # Status flags
    is_active: bool
    is_expired: bool
    days_remaining: int
    
    # Metadata
    creator_id: int
    creator_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SurveyList(BaseModel):
    id: int
    title: str
    survey_type: SurveyTypeEnum
    status: SurveyStatusEnum
    is_anonymous: bool
    is_mandatory: bool
    total_invited: int
    total_responses: int
    response_rate: float
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool
    is_expired: bool
    days_remaining: int
    creator_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Survey Response Schemas
class SurveyResponseCreate(BaseModel):
    responses: Dict[str, Any] = Field(..., description="Survey responses")
    start_time: Optional[datetime] = None
    device_type: Optional[str] = Field(None, max_length=20)

    @validator('responses')
    def validate_responses(cls, v):
        if not v:
            raise ValueError('Survey responses cannot be empty')
        if len(v) == 0:
            raise ValueError('Survey responses must contain at least one item')
        return v

class SurveyResponseUpdate(BaseModel):
    responses: Optional[Dict[str, Any]] = None
    completion_status: Optional[CompletionStatusEnum] = None

class SurveyResponseData(BaseModel):
    id: int
    survey_id: int
    survey_title: Optional[str] = None
    employee_id: Optional[int] = None  # None for anonymous
    employee_name: Optional[str] = None
    responses: Dict[str, Any]
    completion_status: CompletionStatusEnum
    completion_percentage: float
    
    # Timing
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    
    # Metadata
    device_type: Optional[str] = None
    ip_address: Optional[str] = None
    
    # Status flags
    is_completed: bool
    is_in_progress: bool
    
    # System fields
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Engagement Metric Schemas
class EngagementMetricBase(BaseModel):
    employee_id: int
    metric_date: date
    engagement_score: Optional[float] = Field(None, ge=0, le=100)
    job_satisfaction_score: Optional[float] = Field(None, ge=0, le=100)
    work_life_balance_score: Optional[float] = Field(None, ge=0, le=100)
    career_development_score: Optional[float] = Field(None, ge=0, le=100)
    compensation_satisfaction_score: Optional[float] = Field(None, ge=0, le=100)
    manager_relationship_score: Optional[float] = Field(None, ge=0, le=100)
    team_collaboration_score: Optional[float] = Field(None, ge=0, le=100)
    company_culture_score: Optional[float] = Field(None, ge=0, le=100)
    productivity_score: Optional[float] = Field(None, ge=0, le=100)
    attendance_score: Optional[float] = Field(None, ge=0, le=100)
    participation_score: Optional[float] = Field(None, ge=0, le=100)
    feedback_frequency: int = Field(default=0, ge=0)
    flight_risk_score: Optional[float] = Field(None, ge=0, le=100)
    burnout_risk_score: Optional[float] = Field(None, ge=0, le=100)
    stress_level_score: Optional[float] = Field(None, ge=0, le=100)
    survey_based: bool = False
    ai_analyzed: bool = False
    notes: Optional[str] = Field(None, max_length=1000)
    action_items: Optional[List[Dict[str, Any]]] = None

class EngagementMetricCreate(EngagementMetricBase):
    pass

class EngagementMetricUpdate(BaseModel):
    engagement_score: Optional[float] = Field(None, ge=0, le=100)
    job_satisfaction_score: Optional[float] = Field(None, ge=0, le=100)
    work_life_balance_score: Optional[float] = Field(None, ge=0, le=100)
    career_development_score: Optional[float] = Field(None, ge=0, le=100)
    compensation_satisfaction_score: Optional[float] = Field(None, ge=0, le=100)
    manager_relationship_score: Optional[float] = Field(None, ge=0, le=100)
    team_collaboration_score: Optional[float] = Field(None, ge=0, le=100)
    company_culture_score: Optional[float] = Field(None, ge=0, le=100)
    productivity_score: Optional[float] = Field(None, ge=0, le=100)
    attendance_score: Optional[float] = Field(None, ge=0, le=100)
    participation_score: Optional[float] = Field(None, ge=0, le=100)
    feedback_frequency: Optional[int] = Field(None, ge=0)
    flight_risk_score: Optional[float] = Field(None, ge=0, le=100)
    burnout_risk_score: Optional[float] = Field(None, ge=0, le=100)
    stress_level_score: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=1000)
    action_items: Optional[List[Dict[str, Any]]] = None

class EngagementMetricResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    employee_employee_id: Optional[str] = None
    metric_date: date
    engagement_level: Optional[EngagementLevelEnum] = None
    engagement_score: Optional[float] = None
    engagement_category: Optional[str] = None
    
    # Detailed scores
    job_satisfaction_score: Optional[float] = None
    work_life_balance_score: Optional[float] = None
    career_development_score: Optional[float] = None
    compensation_satisfaction_score: Optional[float] = None
    manager_relationship_score: Optional[float] = None
    team_collaboration_score: Optional[float] = None
    company_culture_score: Optional[float] = None
    
    # Behavioral indicators
    productivity_score: Optional[float] = None
    attendance_score: Optional[float] = None
    participation_score: Optional[float] = None
    feedback_frequency: int
    
    # Risk indicators
    flight_risk_score: Optional[float] = None
    burnout_risk_score: Optional[float] = None
    stress_level_score: Optional[float] = None
    risk_level: Optional[str] = None
    
    # Data sources
    survey_based: bool
    survey_id: Optional[int] = None
    ai_analyzed: bool
    
    # Notes and actions
    notes: Optional[str] = None
    action_items: Optional[List[Dict[str, Any]]] = None
    
    # System fields
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Search and Filter Schemas
class SurveySearchParams(BaseModel):
    search: Optional[str] = Field(None, max_length=200)
    survey_type: Optional[SurveyTypeEnum] = None
    status: Optional[SurveyStatusEnum] = None
    creator_id: Optional[int] = None
    is_anonymous: Optional[bool] = None
    is_mandatory: Optional[bool] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None
    start_date_from: Optional[datetime] = None
    start_date_to: Optional[datetime] = None
    active_only: Optional[bool] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=1000)
    sort_by: Optional[str] = Field("created_at", pattern="^(title|survey_type|status|created_at|start_date|response_rate)$")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$")

class SurveyResponseSearchParams(BaseModel):
    survey_id: Optional[int] = None
    employee_id: Optional[int] = None
    completion_status: Optional[CompletionStatusEnum] = None
    completed_from: Optional[datetime] = None
    completed_to: Optional[datetime] = None
    min_completion_percentage: Optional[float] = Field(None, ge=0, le=100)
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)
    sort_by: Optional[str] = Field("created_at", pattern="^(created_at|completed_at|completion_percentage|duration_seconds)$")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$")

class EngagementMetricSearchParams(BaseModel):
    employee_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    engagement_level: Optional[EngagementLevelEnum] = None
    min_engagement_score: Optional[float] = Field(None, ge=0, le=100)
    max_flight_risk_score: Optional[float] = Field(None, ge=0, le=100)
    survey_based: Optional[bool] = None
    ai_analyzed: Optional[bool] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)
    sort_by: Optional[str] = Field("metric_date", pattern="^(metric_date|engagement_score|flight_risk_score|employee_name)$")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$")

# Analytics Schemas
class SurveyAnalytics(BaseModel):
    survey_id: int
    survey_title: str
    total_responses: int
    completed_responses: int
    response_rate: float
    completion_rate: float
    average_duration_minutes: float
    question_analytics: Dict[str, Any]
    demographic_breakdown: Dict[str, Any]
    engagement_insights: Optional[Dict[str, Any]] = None
    sentiment_analysis: Optional[Dict[str, Any]] = None
    recommendations: List[str] = []

class EngagementDashboard(BaseModel):
    total_employees_measured: int
    average_engagement_score: float
    engagement_distribution: Dict[str, int]
    risk_summary: Dict[str, int]
    trends: str
    measurement_period: str
    top_performers: List[Dict[str, Any]] = []
    at_risk_employees: List[Dict[str, Any]] = []
    department_comparison: Dict[str, float] = {}
    recommendations: List[str] = []

class SurveyTemplate(BaseModel):
    name: str
    title: str
    description: str
    survey_type: SurveyTypeEnum
    questions: List[SurveyQuestion]
    estimated_duration: int
    instructions: str

# Bulk Operations
class SurveyBulkAction(BaseModel):
    survey_ids: List[int] = Field(..., min_items=1)
    action: str = Field(..., pattern="^(publish|pause|archive|delete)$")

class SurveyResponseBulkAction(BaseModel):
    response_ids: List[int] = Field(..., min_items=1)
    action: str = Field(..., pattern="^(mark_complete|delete|export)$")

# Export Schemas
class SurveyExportRequest(BaseModel):
    survey_id: int
    format: str = Field("csv", pattern="^(csv|excel|json)$")
    include_personal_data: bool = False
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

class SurveyExportResponse(BaseModel):
    file_name: str
    file_size: int
    download_url: str
    expires_at: datetime
    record_count: int
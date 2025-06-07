"""
Survey and engagement models for the HR AI Assistant.

This module contains SQLAlchemy ORM models for employee surveys,
survey responses, and engagement metrics tracking.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, Boolean, ForeignKey, Numeric, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum
import json

from app.config.database import Base

class SurveyType(enum.Enum):
    """Survey type enumeration"""
    ENGAGEMENT = "engagement"
    SATISFACTION = "satisfaction"
    FEEDBACK = "feedback"
    EXIT = "exit"
    ONBOARDING = "onboarding"
    PERFORMANCE = "performance"
    PULSE = "pulse"
    CUSTOM = "custom"

class SurveyStatus(enum.Enum):
    """Survey status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class QuestionType(enum.Enum):
    """Question type enumeration"""
    MULTIPLE_CHOICE = "multiple_choice"
    SINGLE_CHOICE = "single_choice"
    TEXT = "text"
    TEXTAREA = "textarea"
    RATING = "rating"
    SCALE = "scale"
    YES_NO = "yes_no"
    DATE = "date"
    NUMBER = "number"

class EngagementLevel(enum.Enum):
    """Employee engagement level enumeration"""
    HIGHLY_ENGAGED = "highly_engaged"
    ENGAGED = "engaged"
    MODERATELY_ENGAGED = "moderately_engaged"
    DISENGAGED = "disengaged"
    HIGHLY_DISENGAGED = "highly_disengaged"

class Survey(Base):
    """Survey model for employee surveys and feedback collection"""
    
    __tablename__ = "surveys"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    survey_type = Column(Enum(SurveyType), nullable=False)
    
    # Survey configuration
    questions = Column(JSON)  # JSON array of question objects
    instructions = Column(Text)
    estimated_duration = Column(Integer)  # In minutes
    
    # Targeting and access
    target_departments = Column(JSON)  # JSON array of department IDs
    target_roles = Column(JSON)  # JSON array of role IDs
    target_employees = Column(JSON)  # JSON array of employee IDs
    is_anonymous = Column(Boolean, default=False)
    is_mandatory = Column(Boolean, default=False)
    
    # Scheduling
    status = Column(Enum(SurveyStatus), default=SurveyStatus.DRAFT)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    reminder_frequency = Column(Integer, default=7)  # Days between reminders
    
    # Survey settings
    allow_multiple_responses = Column(Boolean, default=False)
    show_progress = Column(Boolean, default=True)
    randomize_questions = Column(Boolean, default=False)
    require_all_questions = Column(Boolean, default=True)
    
    # Results and analytics
    total_invited = Column(Integer, default=0)
    total_responses = Column(Integer, default=0)
    completion_rate = Column(Numeric(5, 2), default=0)
    average_duration = Column(Integer, default=0)  # In seconds
    
    # System fields
    created_by = Column(Integer, ForeignKey("employees.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime)
    
    # Relationships
    creator = relationship("Employee", foreign_keys=[created_by])
    responses = relationship("SurveyResponse", back_populates="survey")
    
    @property
    def is_active(self) -> bool:
        """Check if survey is currently active"""
        if self.status != SurveyStatus.ACTIVE:
            return False
        
        now = datetime.utcnow()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        
        return True
    
    @property
    def is_expired(self) -> bool:
        """Check if survey has expired"""
        if self.end_date:
            return datetime.utcnow() > self.end_date
        return False
    
    @property
    def days_remaining(self) -> int:
        """Calculate days remaining until survey ends"""
        if not self.end_date:
            return 0
        
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)
    
    @property
    def response_rate(self) -> float:
        """Calculate response rate percentage"""
        if self.total_invited == 0:
            return 0
        return round((self.total_responses / self.total_invited) * 100, 2)
    
    def get_questions(self) -> List[Dict[str, Any]]:
        """Get survey questions as list of dictionaries"""
        if self.questions:
            return json.loads(self.questions) if isinstance(self.questions, str) else self.questions
        return []
    
    def set_questions(self, questions: List[Dict[str, Any]]):
        """Set survey questions from list of dictionaries"""
        self.questions = json.dumps(questions) if isinstance(questions, list) else questions
    
    def to_dict(self) -> dict:
        """Convert survey to dictionary representation"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "survey_type": self.survey_type.value if self.survey_type else None,
            "status": self.status.value if self.status else None,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "is_anonymous": self.is_anonymous,
            "is_mandatory": self.is_mandatory,
            "estimated_duration": self.estimated_duration,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "days_remaining": self.days_remaining,
            "total_invited": self.total_invited,
            "total_responses": self.total_responses,
            "response_rate": self.response_rate,
            "completion_rate": float(self.completion_rate) if self.completion_rate else 0,
            "creator": self.creator.full_name if self.creator else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<Survey(id={self.id}, title='{self.title}', type='{self.survey_type.value}')>"

class SurveyResponse(Base):
    """Survey response model for individual employee responses"""
    
    __tablename__ = "survey_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("surveys.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)  # Null for anonymous
    
    # Response data
    responses = Column(JSON, nullable=False)  # JSON object with question_id: answer
    completion_status = Column(String(20), default="in_progress")  # in_progress, completed, abandoned
    completion_percentage = Column(Numeric(5, 2), default=0)
    
    # Timing information
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)  # Time taken to complete
    
    # Response metadata
    ip_address = Column(String(45))  # For analytics (anonymized)
    user_agent = Column(Text)
    device_type = Column(String(20))  # desktop, tablet, mobile
    
    # System fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    survey = relationship("Survey", back_populates="responses")
    employee = relationship("Employee", back_populates="survey_responses")
    
    @property
    def is_completed(self) -> bool:
        """Check if response is completed"""
        return self.completion_status == "completed"
    
    @property
    def is_in_progress(self) -> bool:
        """Check if response is in progress"""
        return self.completion_status == "in_progress"
    
    def get_responses(self) -> Dict[str, Any]:
        """Get response data as dictionary"""
        if self.responses:
            return json.loads(self.responses) if isinstance(self.responses, str) else self.responses
        return {}
    
    def set_responses(self, responses: Dict[str, Any]):
        """Set response data from dictionary"""
        self.responses = json.dumps(responses) if isinstance(responses, dict) else responses
    
    def add_response(self, question_id: str, answer: Any):
        """Add a single question response"""
        current_responses = self.get_responses()
        current_responses[question_id] = answer
        self.set_responses(current_responses)
    
    def calculate_completion_percentage(self, total_questions: int) -> float:
        """Calculate completion percentage based on answered questions"""
        if total_questions == 0:
            return 100.0
        
        answered_questions = len([v for v in self.get_responses().values() if v is not None and v != ""])
        percentage = (answered_questions / total_questions) * 100
        self.completion_percentage = round(percentage, 2)
        return self.completion_percentage
    
    def mark_completed(self):
        """Mark response as completed"""
        self.completion_status = "completed"
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
    
    def to_dict(self) -> dict:
        """Convert survey response to dictionary representation"""
        return {
            "id": self.id,
            "survey_id": self.survey_id,
            "survey_title": self.survey.title if self.survey else None,
            "employee_name": self.employee.full_name if self.employee else "Anonymous",
            "completion_status": self.completion_status,
            "completion_percentage": float(self.completion_percentage) if self.completion_percentage else 0,
            "is_completed": self.is_completed,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "device_type": self.device_type,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<SurveyResponse(id={self.id}, survey_id={self.survey_id}, employee_id={self.employee_id})>"

class EngagementMetric(Base):
    """Engagement metric model for tracking employee engagement over time"""
    
    __tablename__ = "engagement_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # Metric details
    metric_date = Column(Date, nullable=False, index=True)
    engagement_level = Column(Enum(EngagementLevel))
    engagement_score = Column(Numeric(5, 2))  # 0-100 scale
    
    # Detailed scores
    job_satisfaction_score = Column(Numeric(5, 2))
    work_life_balance_score = Column(Numeric(5, 2))
    career_development_score = Column(Numeric(5, 2))
    compensation_satisfaction_score = Column(Numeric(5, 2))
    manager_relationship_score = Column(Numeric(5, 2))
    team_collaboration_score = Column(Numeric(5, 2))
    company_culture_score = Column(Numeric(5, 2))
    
    # Behavioral indicators
    productivity_score = Column(Numeric(5, 2))
    attendance_score = Column(Numeric(5, 2))
    participation_score = Column(Numeric(5, 2))
    feedback_frequency = Column(Integer, default=0)
    
    # Risk indicators
    flight_risk_score = Column(Numeric(5, 2))  # Likelihood to leave
    burnout_risk_score = Column(Numeric(5, 2))
    stress_level_score = Column(Numeric(5, 2))
    
    # Data sources
    survey_based = Column(Boolean, default=False)
    survey_id = Column(Integer, ForeignKey("surveys.id"))
    ai_analyzed = Column(Boolean, default=False)
    
    # Comments and notes
    notes = Column(Text)
    action_items = Column(JSON)  # JSON array of action items
    
    # System fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = relationship("Employee")
    survey = relationship("Survey")
    
    @property
    def overall_engagement_category(self) -> str:
        """Get engagement category based on score"""
        if not self.engagement_score:
            return "Unknown"
        
        score = float(self.engagement_score)
        if score >= 80:
            return "Highly Engaged"
        elif score >= 60:
            return "Engaged"
        elif score >= 40:
            return "Moderately Engaged"
        elif score >= 20:
            return "Disengaged"
        else:
            return "Highly Disengaged"
    
    @property
    def risk_level(self) -> str:
        """Calculate overall risk level"""
        if not self.flight_risk_score:
            return "Unknown"
        
        score = float(self.flight_risk_score)
        if score >= 70:
            return "High Risk"
        elif score >= 40:
            return "Medium Risk"
        else:
            return "Low Risk"
    
    def get_action_items(self) -> List[Dict[str, Any]]:
        """Get action items as list of dictionaries"""
        if self.action_items:
            return json.loads(self.action_items) if isinstance(self.action_items, str) else self.action_items
        return []
    
    def set_action_items(self, items: List[Dict[str, Any]]):
        """Set action items from list of dictionaries"""
        self.action_items = json.dumps(items) if isinstance(items, list) else items
    
    def calculate_engagement_level(self):
        """Calculate and set engagement level based on score"""
        if not self.engagement_score:
            return
        
        score = float(self.engagement_score)
        if score >= 80:
            self.engagement_level = EngagementLevel.HIGHLY_ENGAGED
        elif score >= 60:
            self.engagement_level = EngagementLevel.ENGAGED
        elif score >= 40:
            self.engagement_level = EngagementLevel.MODERATELY_ENGAGED
        elif score >= 20:
            self.engagement_level = EngagementLevel.DISENGAGED
        else:
            self.engagement_level = EngagementLevel.HIGHLY_DISENGAGED
    
    def to_dict(self) -> dict:
        """Convert engagement metric to dictionary representation"""
        return {
            "id": self.id,
            "employee_name": self.employee.full_name if self.employee else None,
            "employee_id": self.employee.employee_id if self.employee else None,
            "metric_date": self.metric_date.isoformat() if self.metric_date else None,
            "engagement_level": self.engagement_level.value if self.engagement_level else None,
            "engagement_score": float(self.engagement_score) if self.engagement_score else None,
            "engagement_category": self.overall_engagement_category,
            "job_satisfaction_score": float(self.job_satisfaction_score) if self.job_satisfaction_score else None,
            "work_life_balance_score": float(self.work_life_balance_score) if self.work_life_balance_score else None,
            "career_development_score": float(self.career_development_score) if self.career_development_score else None,
            "compensation_satisfaction_score": float(self.compensation_satisfaction_score) if self.compensation_satisfaction_score else None,
            "manager_relationship_score": float(self.manager_relationship_score) if self.manager_relationship_score else None,
            "team_collaboration_score": float(self.team_collaboration_score) if self.team_collaboration_score else None,
            "company_culture_score": float(self.company_culture_score) if self.company_culture_score else None,
            "flight_risk_score": float(self.flight_risk_score) if self.flight_risk_score else None,
            "burnout_risk_score": float(self.burnout_risk_score) if self.burnout_risk_score else None,
            "risk_level": self.risk_level,
            "survey_based": self.survey_based,
            "ai_analyzed": self.ai_analyzed,
            "notes": self.notes,
            "action_items": self.get_action_items(),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<EngagementMetric(id={self.id}, employee_id={self.employee_id}, date='{self.metric_date}', score={self.engagement_score})>"
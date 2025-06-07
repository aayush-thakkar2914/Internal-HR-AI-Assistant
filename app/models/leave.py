"""
Leave management models for the HR AI Assistant.

This module contains SQLAlchemy ORM models for leave requests,
leave types, and leave balance tracking.
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, Boolean, ForeignKey, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum

from app.config.database import Base

class LeaveStatus(enum.Enum):
    """Leave request status enumeration"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    WITHDRAWN = "withdrawn"

class LeavePriority(enum.Enum):
    """Leave request priority enumeration"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class LeaveType(Base):
    """Leave type model for different types of leave"""
    
    __tablename__ = "leave_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    code = Column(String(10), unique=True, nullable=False)
    description = Column(Text)
    
    # Leave configuration
    max_days_per_year = Column(Integer, default=0)  # 0 = unlimited
    max_consecutive_days = Column(Integer, default=0)  # 0 = unlimited
    min_advance_notice_days = Column(Integer, default=0)
    max_advance_notice_days = Column(Integer, default=365)
    
    # Approval requirements
    requires_approval = Column(Boolean, default=True)
    requires_manager_approval = Column(Boolean, default=True)
    requires_hr_approval = Column(Boolean, default=False)
    requires_documentation = Column(Boolean, default=False)
    
    # Leave characteristics
    is_paid = Column(Boolean, default=True)
    is_carry_forward = Column(Boolean, default=False)
    carry_forward_limit = Column(Integer, default=0)
    accrual_rate = Column(Numeric(5, 2), default=0)  # Days per month
    
    # System fields
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    leave_requests = relationship("LeaveRequest", back_populates="leave_type")
    leave_balances = relationship("LeaveBalance", back_populates="leave_type")
    
    def __repr__(self):
        return f"<LeaveType(id={self.id}, name='{self.name}', code='{self.code}')>"

class LeaveBalance(Base):
    """Leave balance model for tracking employee leave balances"""
    
    __tablename__ = "leave_balances"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    year = Column(Integer, nullable=False, index=True)
    
    # Balance tracking
    allocated_days = Column(Numeric(5, 2), default=0)
    used_days = Column(Numeric(5, 2), default=0)
    pending_days = Column(Numeric(5, 2), default=0)  # Requested but not approved
    carry_forward_days = Column(Numeric(5, 2), default=0)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = relationship("Employee", back_populates="leave_balances")
    leave_type = relationship("LeaveType", back_populates="leave_balances")
    
    @property
    def available_days(self) -> float:
        """Calculate available leave days"""
        return float(self.allocated_days + self.carry_forward_days - self.used_days - self.pending_days)
    
    @property
    def utilization_percentage(self) -> float:
        """Calculate leave utilization percentage"""
        total_allocated = float(self.allocated_days + self.carry_forward_days)
        if total_allocated == 0:
            return 0
        return round((float(self.used_days) / total_allocated) * 100, 2)
    
    def __repr__(self):
        return f"<LeaveBalance(employee_id={self.employee_id}, leave_type_id={self.leave_type_id}, year={self.year})>"

class LeaveRequest(Base):
    """Leave request model for employee leave applications"""
    
    __tablename__ = "leave_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(20), unique=True, nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    
    # Leave details
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_days = Column(Numeric(5, 2), nullable=False)
    reason = Column(Text, nullable=False)
    emergency_contact = Column(String(100))
    emergency_phone = Column(String(20))
    
    # Request metadata
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING)
    priority = Column(Enum(LeavePriority), default=LeavePriority.NORMAL)
    is_half_day = Column(Boolean, default=False)
    half_day_session = Column(String(10))  # morning, afternoon
    
    # Approval workflow
    manager_id = Column(Integer, ForeignKey("employees.id"))
    manager_approval_date = Column(DateTime)
    manager_comments = Column(Text)
    
    hr_approval_required = Column(Boolean, default=False)
    hr_approver_id = Column(Integer, ForeignKey("employees.id"))
    hr_approval_date = Column(DateTime)
    hr_comments = Column(Text)
    
    # Additional information
    attachments = Column(Text)  # JSON string of file paths
    work_handover = Column(Text)
    backup_contact_id = Column(Integer, ForeignKey("employees.id"))
    
    # System fields
    submitted_date = Column(DateTime, default=datetime.utcnow)
    approved_date = Column(DateTime)
    rejected_date = Column(DateTime)
    cancellation_reason = Column(Text)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("employees.id"))
    
    # Relationships
    employee = relationship("Employee", back_populates="leave_requests", foreign_keys=[employee_id])
    leave_type = relationship("LeaveType", back_populates="leave_requests")
    manager = relationship("Employee", foreign_keys=[manager_id])
    hr_approver = relationship("Employee", foreign_keys=[hr_approver_id])
    backup_contact = relationship("Employee", foreign_keys=[backup_contact_id])
    
    @property
    def is_approved(self) -> bool:
        """Check if leave request is approved"""
        return self.status == LeaveStatus.APPROVED
    
    @property
    def is_pending(self) -> bool:
        """Check if leave request is pending"""
        return self.status == LeaveStatus.PENDING
    
    @property
    def is_active(self) -> bool:
        """Check if leave is currently active"""
        if not self.is_approved:
            return False
        
        today = date.today()
        return self.start_date <= today <= self.end_date
    
    @property
    def is_future(self) -> bool:
        """Check if leave is in the future"""
        return self.start_date > date.today()
    
    @property
    def is_past(self) -> bool:
        """Check if leave is in the past"""
        return self.end_date < date.today()
    
    @property
    def days_until_start(self) -> int:
        """Calculate days until leave starts"""
        if self.start_date <= date.today():
            return 0
        return (self.start_date - date.today()).days
    
    @property
    def duration_in_days(self) -> int:
        """Calculate leave duration in days"""
        return (self.end_date - self.start_date).days + 1
    
    def can_be_cancelled(self) -> bool:
        """Check if leave request can be cancelled"""
        if self.status not in [LeaveStatus.PENDING, LeaveStatus.APPROVED]:
            return False
        
        # Can cancel if not started yet
        return self.start_date > date.today()
    
    def can_be_modified(self) -> bool:
        """Check if leave request can be modified"""
        if self.status != LeaveStatus.PENDING:
            return False
        
        # Can modify if not started yet and pending
        return self.start_date > date.today()
    
    def get_approval_status(self) -> str:
        """Get detailed approval status"""
        if self.status == LeaveStatus.APPROVED:
            return "Fully Approved"
        elif self.status == LeaveStatus.REJECTED:
            return "Rejected"
        elif self.status == LeaveStatus.PENDING:
            if self.hr_approval_required and not self.hr_approval_date:
                if not self.manager_approval_date:
                    return "Pending Manager & HR Approval"
                else:
                    return "Pending HR Approval"
            elif not self.manager_approval_date:
                return "Pending Manager Approval"
            else:
                return "Pending Final Approval"
        else:
            return self.status.value.title()
    
    def to_dict(self) -> dict:
        """Convert leave request to dictionary representation"""
        return {
            "id": self.id,
            "request_id": self.request_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "employee_id": self.employee.employee_id if self.employee else None,
            "leave_type": self.leave_type.name if self.leave_type else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "total_days": float(self.total_days) if self.total_days else 0,
            "reason": self.reason,
            "status": self.status.value if self.status else None,
            "priority": self.priority.value if self.priority else None,
            "is_half_day": self.is_half_day,
            "approval_status": self.get_approval_status(),
            "submitted_date": self.submitted_date.isoformat() if self.submitted_date else None,
            "manager_name": self.manager.full_name if self.manager else None,
            "is_active": self.is_active,
            "is_future": self.is_future,
            "days_until_start": self.days_until_start,
            "can_be_cancelled": self.can_be_cancelled(),
            "can_be_modified": self.can_be_modified()
        }
    
    def __repr__(self):
        return f"<LeaveRequest(id={self.id}, request_id='{self.request_id}', employee_id={self.employee_id}, status='{self.status.value}')>"
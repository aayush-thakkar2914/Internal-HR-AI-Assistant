"""
Leave management Pydantic schemas for the HR AI Assistant.

This module contains Pydantic models for leave request validation,
serialization, and API request/response handling.
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum

class LeaveStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    WITHDRAWN = "withdrawn"

class LeavePriorityEnum(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

# Leave Type Schemas
class LeaveTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    code: str = Field(..., min_length=1, max_length=10)
    description: Optional[str] = None
    max_days_per_year: int = Field(0, ge=0)
    max_consecutive_days: int = Field(0, ge=0)
    min_advance_notice_days: int = Field(0, ge=0)
    max_advance_notice_days: int = Field(365, ge=0)
    requires_approval: bool = True
    requires_manager_approval: bool = True
    requires_hr_approval: bool = False
    requires_documentation: bool = False
    is_paid: bool = True
    is_carry_forward: bool = False
    carry_forward_limit: int = Field(0, ge=0)
    accrual_rate: float = Field(0, ge=0)
    is_active: bool = True

class LeaveTypeCreate(LeaveTypeBase):
    pass

class LeaveTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    max_days_per_year: Optional[int] = Field(None, ge=0)
    max_consecutive_days: Optional[int] = Field(None, ge=0)
    min_advance_notice_days: Optional[int] = Field(None, ge=0)
    max_advance_notice_days: Optional[int] = Field(None, ge=0)
    requires_approval: Optional[bool] = None
    requires_manager_approval: Optional[bool] = None
    requires_hr_approval: Optional[bool] = None
    requires_documentation: Optional[bool] = None
    is_paid: Optional[bool] = None
    is_carry_forward: Optional[bool] = None
    carry_forward_limit: Optional[int] = Field(None, ge=0)
    accrual_rate: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None

class LeaveTypeResponse(LeaveTypeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Leave Balance Schemas
class LeaveBalanceResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    leave_type_id: int
    leave_type_name: Optional[str] = None
    leave_type_code: Optional[str] = None
    year: int
    allocated_days: float
    used_days: float
    pending_days: float
    carry_forward_days: float
    available_days: float
    utilization_percentage: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LeaveBalanceUpdate(BaseModel):
    allocated_days: Optional[float] = Field(None, ge=0)
    carry_forward_days: Optional[float] = Field(None, ge=0)

# Leave Request Schemas
class LeaveRequestBase(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    reason: str = Field(..., min_length=10, max_length=1000)
    emergency_contact: Optional[str] = Field(None, max_length=100)
    emergency_phone: Optional[str] = Field(None, max_length=20)
    priority: LeavePriorityEnum = LeavePriorityEnum.NORMAL
    is_half_day: bool = False
    half_day_session: Optional[str] = Field(None, regex="^(morning|afternoon)$")
    work_handover: Optional[str] = None
    backup_contact_id: Optional[int] = None

    @validator('end_date')
    def validate_date_range(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('End date must be after or equal to start date')
        return v

    @validator('start_date')
    def validate_start_date(cls, v):
        if v < date.today():
            raise ValueError('Start date cannot be in the past')
        return v

    @validator('half_day_session')
    def validate_half_day_session(cls, v, values):
        if values.get('is_half_day') and not v:
            raise ValueError('Half day session must be specified for half day leave')
        if not values.get('is_half_day') and v:
            raise ValueError('Half day session should not be specified for full day leave')
        return v

class LeaveRequestCreate(LeaveRequestBase):
    pass

class LeaveRequestUpdate(BaseModel):
    leave_type_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = Field(None, min_length=10, max_length=1000)
    emergency_contact: Optional[str] = Field(None, max_length=100)
    emergency_phone: Optional[str] = Field(None, max_length=20)
    priority: Optional[LeavePriorityEnum] = None
    is_half_day: Optional[bool] = None
    half_day_session: Optional[str] = Field(None, regex="^(morning|afternoon)$")
    work_handover: Optional[str] = None
    backup_contact_id: Optional[int] = None

class LeaveRequestResponse(BaseModel):
    id: int
    request_id: str
    employee_id: int
    employee_name: Optional[str] = None
    employee_employee_id: Optional[str] = None
    leave_type_id: int
    leave_type_name: Optional[str] = None
    leave_type_code: Optional[str] = None
    start_date: date
    end_date: date
    total_days: float
    reason: str
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    status: LeaveStatusEnum
    priority: LeavePriorityEnum
    is_half_day: bool
    half_day_session: Optional[str] = None
    
    # Approval information
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None
    manager_approval_date: Optional[datetime] = None
    manager_comments: Optional[str] = None
    hr_approval_required: bool
    hr_approver_id: Optional[int] = None
    hr_approver_name: Optional[str] = None
    hr_approval_date: Optional[datetime] = None
    hr_comments: Optional[str] = None
    
    # Additional information
    work_handover: Optional[str] = None
    backup_contact_id: Optional[int] = None
    backup_contact_name: Optional[str] = None
    
    # Status information
    approval_status: Optional[str] = None
    is_active: bool
    is_future: bool
    is_past: bool
    days_until_start: int
    can_be_cancelled: bool
    can_be_modified: bool
    
    # Timestamps
    submitted_date: datetime
    approved_date: Optional[datetime] = None
    rejected_date: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Leave Approval Schemas
class LeaveApprovalAction(BaseModel):
    action: str = Field(..., regex="^(approve|reject)$")
    comments: Optional[str] = Field(None, max_length=500)

class LeaveManagerApproval(LeaveApprovalAction):
    pass

class LeaveHRApproval(LeaveApprovalAction):
    pass

# Leave Cancellation Schema
class LeaveCancellation(BaseModel):
    reason: str = Field(..., min_length=10, max_length=500)

# Leave Search and Filter Schemas
class LeaveRequestSearchParams(BaseModel):
    employee_id: Optional[int] = None
    leave_type_id: Optional[int] = None
    status: Optional[LeaveStatusEnum] = None
    priority: Optional[LeavePriorityEnum] = None
    start_date_from: Optional[date] = None
    start_date_to: Optional[date] = None
    submitted_from: Optional[date] = None
    submitted_to: Optional[date] = None
    manager_id: Optional[int] = None
    is_current: Optional[bool] = None  # Currently active leaves
    is_future: Optional[bool] = None   # Future leaves
    requires_approval: Optional[bool] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)
    sort_by: Optional[str] = Field("submitted_date", regex="^(submitted_date|start_date|employee_name|status)$")
    sort_order: Optional[str] = Field("desc", regex="^(asc|desc)$")

# Leave Calendar Schema
class LeaveCalendarEntry(BaseModel):
    id: int
    employee_name: str
    employee_id: str
    leave_type_name: str
    leave_type_code: str
    start_date: date
    end_date: date
    total_days: float
    status: LeaveStatusEnum
    is_half_day: bool

class LeaveCalendarResponse(BaseModel):
    date: date
    leaves: List[LeaveCalendarEntry]
    total_employees_on_leave: int

# Leave Statistics Schemas
class LeaveTypeStatistics(BaseModel):
    leave_type_id: int
    leave_type_name: str
    leave_type_code: str
    total_requests: int
    approved_requests: int
    pending_requests: int
    rejected_requests: int
    total_days_taken: float
    average_days_per_request: float
    approval_rate: float

class LeaveStatistics(BaseModel):
    total_requests: int
    pending_requests: int
    approved_requests: int
    rejected_requests: int
    total_days_requested: float
    total_days_approved: float
    average_processing_time_days: float
    by_leave_type: List[LeaveTypeStatistics]
    by_month: dict
    by_department: dict

# Leave Balance Summary
class LeaveBalanceSummary(BaseModel):
    employee_id: int
    employee_name: str
    year: int
    balances: List[LeaveBalanceResponse]
    total_allocated: float
    total_used: float
    total_available: float
    total_pending: float

# Bulk Leave Operations
class LeaveBulkApproval(BaseModel):
    leave_request_ids: List[int] = Field(..., min_items=1)
    action: str = Field(..., regex="^(approve|reject)$")
    comments: Optional[str] = Field(None, max_length=500)

class LeaveRequestBatch(BaseModel):
    requests: List[LeaveRequestCreate] = Field(..., min_items=1, max_items=10)

# Leave Policy Validation Response
class LeavePolicyValidation(BaseModel):
    is_valid: bool
    violations: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []
    max_allowed_days: Optional[int] = None
    available_balance: Optional[float] = None
    advance_notice_requirement: Optional[int] = None
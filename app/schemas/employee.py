"""
Employee Pydantic schemas for the HR AI Assistant.

This module contains Pydantic models for employee data validation,
serialization, and API request/response handling.
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum

class EmploymentStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"
    ON_LEAVE = "on_leave"
    PROBATION = "probation"

class GenderEnum(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"

class EmploymentTypeEnum(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERN = "intern"

# Department Schemas
class DepartmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    department_code: str = Field(..., min_length=1, max_length=10)
    budget: Optional[float] = Field(None, ge=0)
    location: Optional[str] = Field(None, max_length=100)
    is_active: bool = True

class DepartmentCreate(DepartmentBase):
    manager_id: Optional[int] = None

class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    budget: Optional[float] = Field(None, ge=0)
    location: Optional[str] = Field(None, max_length=100)
    manager_id: Optional[int] = None
    is_active: Optional[bool] = None

class DepartmentResponse(DepartmentBase):
    id: int
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None
    employee_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Role Schemas
class RoleBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    role_code: str = Field(..., min_length=1, max_length=20)
    level: int = Field(1, ge=1, le=5)
    department_id: int
    min_salary: Optional[float] = Field(None, ge=0)
    max_salary: Optional[float] = Field(None, ge=0)
    required_skills: Optional[str] = None
    is_active: bool = True

    @validator('max_salary')
    def validate_salary_range(cls, v, values):
        if v is not None and values.get('min_salary') is not None:
            if v < values['min_salary']:
                raise ValueError('max_salary must be greater than or equal to min_salary')
        return v

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    level: Optional[int] = Field(None, ge=1, le=5)
    min_salary: Optional[float] = Field(None, ge=0)
    max_salary: Optional[float] = Field(None, ge=0)
    required_skills: Optional[str] = None
    is_active: Optional[bool] = None

class RoleResponse(RoleBase):
    id: int
    department_name: Optional[str] = None
    employee_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Employee Schemas
class EmployeeBase(BaseModel):
    employee_id: str = Field(..., min_length=1, max_length=20)
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    middle_name: Optional[str] = Field(None, max_length=50)
    date_of_birth: Optional[date] = None
    gender: Optional[GenderEnum] = None
    phone_number: Optional[str] = Field(None, max_length=20)
    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=50)
    state: Optional[str] = Field(None, max_length=50)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(default="India", max_length=50)
    
    # Employment
    department_id: int
    role_id: int
    manager_id: Optional[int] = None
    hire_date: date
    employment_status: EmploymentStatusEnum = EmploymentStatusEnum.ACTIVE
    employment_type: EmploymentTypeEnum = EmploymentTypeEnum.FULL_TIME
    
    # Compensation
    salary: Optional[float] = Field(None, ge=0)
    currency: str = Field(default="INR", max_length=3)
    pay_frequency: str = Field(default="monthly", max_length=20)
    
    # Additional info
    bio: Optional[str] = None
    skills: Optional[str] = None
    certifications: Optional[str] = None

    @validator('date_of_birth')
    def validate_birth_date(cls, v):
        if v and v >= date.today():
            raise ValueError('Date of birth must be in the past')
        return v

    @validator('hire_date')
    def validate_hire_date(cls, v):
        if v and v > date.today():
            raise ValueError('Hire date cannot be in the future')
        return v

class EmployeeCreate(EmployeeBase):
    password: str = Field(..., min_length=8, max_length=100)

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class EmployeeUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    middle_name: Optional[str] = Field(None, max_length=50)
    date_of_birth: Optional[date] = None
    gender: Optional[GenderEnum] = None
    phone_number: Optional[str] = Field(None, max_length=20)
    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=50)
    state: Optional[str] = Field(None, max_length=50)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=50)
    
    # Employment
    department_id: Optional[int] = None
    role_id: Optional[int] = None
    manager_id: Optional[int] = None
    employment_status: Optional[EmploymentStatusEnum] = None
    employment_type: Optional[EmploymentTypeEnum] = None
    
    # Compensation
    salary: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=3)
    pay_frequency: Optional[str] = Field(None, max_length=20)
    
    # Additional info
    bio: Optional[str] = None
    skills: Optional[str] = None
    certifications: Optional[str] = None
    is_active: Optional[bool] = None

class EmployeeResponse(BaseModel):
    id: int
    employee_id: str
    email: str
    username: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    full_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[GenderEnum] = None
    phone_number: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    
    # Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    
    # Employment
    department_id: int
    department_name: Optional[str] = None
    role_id: int
    role_title: Optional[str] = None
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None
    hire_date: date
    termination_date: Optional[date] = None
    employment_status: EmploymentStatusEnum
    employment_type: EmploymentTypeEnum
    
    # Compensation
    salary: Optional[float] = None
    currency: Optional[str] = None
    pay_frequency: Optional[str] = None
    
    # Calculated fields
    years_of_service: Optional[float] = None
    age: Optional[int] = None
    is_manager: Optional[bool] = False
    
    # System fields
    is_active: bool
    last_login: Optional[datetime] = None
    profile_picture_url: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[str] = None
    certifications: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class EmployeeList(BaseModel):
    id: int
    employee_id: str
    full_name: str
    email: str
    department_name: Optional[str] = None
    role_title: Optional[str] = None
    employment_status: EmploymentStatusEnum
    hire_date: date
    is_active: bool

    class Config:
        from_attributes = True

# Authentication Schemas
class EmployeeLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)

class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class PasswordReset(BaseModel):
    email: EmailStr
    new_password: str = Field(..., min_length=8, max_length=100)
    reset_token: str = Field(..., min_length=1)

# Employee Search and Filter Schemas
class EmployeeSearchParams(BaseModel):
    search: Optional[str] = Field(None, max_length=100)
    department_id: Optional[int] = None
    role_id: Optional[int] = None
    employment_status: Optional[EmploymentStatusEnum] = None
    employment_type: Optional[EmploymentTypeEnum] = None
    is_active: Optional[bool] = None
    manager_id: Optional[int] = None
    hire_date_from: Optional[date] = None
    hire_date_to: Optional[date] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)
    sort_by: Optional[str] = Field("full_name", regex="^(full_name|email|hire_date|department_name|role_title)$")
    sort_order: Optional[str] = Field("asc", regex="^(asc|desc)$")

# Bulk Operations Schemas
class EmployeeBulkUpdate(BaseModel):
    employee_ids: List[int] = Field(..., min_items=1)
    updates: EmployeeUpdate

class EmployeeBulkStatusUpdate(BaseModel):
    employee_ids: List[int] = Field(..., min_items=1)
    employment_status: EmploymentStatusEnum
    termination_date: Optional[date] = None
    reason: Optional[str] = None

# Employee Statistics Schema
class EmployeeStatistics(BaseModel):
    total_employees: int
    active_employees: int
    inactive_employees: int
    new_hires_this_month: int
    terminations_this_month: int
    average_tenure_years: float
    department_breakdown: dict
    role_breakdown: dict
    employment_type_breakdown: dict
    age_group_breakdown: dict

# Employee Profile Summary
class EmployeeProfileSummary(BaseModel):
    employee_info: EmployeeResponse
    leave_balance_summary: dict
    recent_leave_requests: List[dict]
    pending_document_requests: List[dict]
    engagement_metrics: Optional[dict] = None
    recent_queries: List[dict]
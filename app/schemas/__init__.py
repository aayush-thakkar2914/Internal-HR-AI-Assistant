"""
Pydantic schemas package for HR AI Assistant

This package contains all Pydantic schemas for request/response validation
and serialization.
"""

from .employee import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeList,
    DepartmentCreate, DepartmentUpdate, DepartmentResponse,
    RoleCreate, RoleUpdate, RoleResponse
)
from .leave import (
    LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestResponse,
    LeaveTypeCreate, LeaveTypeUpdate, LeaveTypeResponse,
    LeaveBalanceResponse
)
from .document import (
    DocumentCreate, DocumentUpdate, DocumentResponse,
    DocumentRequestCreate, DocumentRequestUpdate, DocumentRequestResponse
)
from .survey import (
    SurveyCreate, SurveyUpdate, SurveyResponse,
    SurveyResponseCreate, SurveyResponseUpdate, SurveyResponseData,
    EngagementMetricCreate, EngagementMetricResponse
)
from .chat import (
    ChatMessage, ChatResponse, ChatSessionCreate, ChatSessionResponse,
    QueryLogResponse
)

__all__ = [
    # Employee schemas
    "EmployeeCreate", "EmployeeUpdate", "EmployeeResponse", "EmployeeList",
    "DepartmentCreate", "DepartmentUpdate", "DepartmentResponse",
    "RoleCreate", "RoleUpdate", "RoleResponse",
    
    # Leave schemas
    "LeaveRequestCreate", "LeaveRequestUpdate", "LeaveRequestResponse",
    "LeaveTypeCreate", "LeaveTypeUpdate", "LeaveTypeResponse",
    "LeaveBalanceResponse",
    
    # Document schemas
    "DocumentCreate", "DocumentUpdate", "DocumentResponse",
    "DocumentRequestCreate", "DocumentRequestUpdate", "DocumentRequestResponse",
    
    # Survey schemas
    "SurveyCreate", "SurveyUpdate", "SurveyResponse",
    "SurveyResponseCreate", "SurveyResponseUpdate", "SurveyResponseData",
    "EngagementMetricCreate", "EngagementMetricResponse",
    
    # Chat schemas
    "ChatMessage", "ChatResponse", "ChatSessionCreate", "ChatSessionResponse",
    "QueryLogResponse"
]
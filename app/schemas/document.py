"""
Document management Pydantic schemas for the HR AI Assistant.

This module contains Pydantic models for document validation,
serialization, and API request/response handling.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum

class DocumentTypeEnum(str, Enum):
    POLICY = "policy"
    PROCEDURE = "procedure"
    HANDBOOK = "handbook"
    FORM = "form"
    TEMPLATE = "template"
    CERTIFICATION = "certification"
    TRAINING = "training"
    ONBOARDING = "onboarding"
    BENEFITS = "benefits"
    COMPLIANCE = "compliance"
    OTHER = "other"

class DocumentStatusEnum(str, Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    EXPIRED = "expired"

class AccessLevelEnum(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class RequestStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

# Document Schemas
class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    document_type: DocumentTypeEnum
    keywords: Optional[str] = Field(None, max_length=500)
    tags: Optional[str] = Field(None, max_length=500)
    version: str = Field(default="1.0", max_length=20)
    language: str = Field(default="en", max_length=10)
    access_level: AccessLevelEnum = AccessLevelEnum.INTERNAL
    department_access: Optional[str] = None  # JSON string of department IDs
    role_access: Optional[str] = None  # JSON string of role IDs
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    review_date: Optional[datetime] = None
    is_searchable: bool = True
    search_boost: int = Field(default=1, ge=1, le=10)

    @validator('expiry_date')
    def validate_expiry_date(cls, v, values):
        if v and values.get('effective_date') and v <= values['effective_date']:
            raise ValueError('Expiry date must be after effective date')
        return v

    @validator('review_date')
    def validate_review_date(cls, v, values):
        if v and values.get('effective_date') and v <= values['effective_date']:
            raise ValueError('Review date must be after effective date')
        return v

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    document_type: Optional[DocumentTypeEnum] = None
    keywords: Optional[str] = Field(None, max_length=500)
    tags: Optional[str] = Field(None, max_length=500)
    version: Optional[str] = Field(None, max_length=20)
    language: Optional[str] = Field(None, max_length=10)
    access_level: Optional[AccessLevelEnum] = None
    department_access: Optional[str] = None
    role_access: Optional[str] = None
    status: Optional[DocumentStatusEnum] = None
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    review_date: Optional[datetime] = None
    is_searchable: Optional[bool] = None
    search_boost: Optional[int] = Field(None, ge=1, le=10)
    reviewer_id: Optional[int] = None
    approver_id: Optional[int] = None

class DocumentResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    document_type: DocumentTypeEnum
    file_path: str
    file_name: str
    file_size: Optional[int] = None
    file_size_mb: Optional[float] = None
    file_extension: Optional[str] = None
    mime_type: Optional[str] = None
    version: str
    language: str
    access_level: AccessLevelEnum
    status: DocumentStatusEnum
    
    # Author and approval information
    author_id: int
    author_name: Optional[str] = None
    reviewer_id: Optional[int] = None
    reviewer_name: Optional[str] = None
    approver_id: Optional[int] = None
    approver_name: Optional[str] = None
    
    # Dates
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    review_date: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    
    # Status flags
    is_expired: bool
    needs_review: bool
    is_published: bool
    is_searchable: bool
    opensearch_indexed: bool
    
    # Analytics
    view_count: int
    download_count: int
    last_accessed: Optional[datetime] = None
    
    # System fields
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentList(BaseModel):
    id: int
    title: str
    document_type: DocumentTypeEnum
    file_name: str
    file_size_mb: Optional[float] = None
    status: DocumentStatusEnum
    access_level: AccessLevelEnum
    author_name: Optional[str] = None
    view_count: int
    download_count: int
    is_expired: bool
    needs_review: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Document Request Schemas
class DocumentRequestBase(BaseModel):
    document_title: str = Field(..., min_length=1, max_length=200)
    document_type: DocumentTypeEnum
    description: str = Field(..., min_length=10, max_length=1000)
    purpose: Optional[str] = Field(None, max_length=500)
    format_preference: str = Field(default="pdf", max_length=20)
    delivery_method: str = Field(default="email", max_length=20)
    urgency: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    certified_copy: bool = False
    multiple_copies: int = Field(default=1, ge=1, le=10)
    special_instructions: Optional[str] = Field(None, max_length=1000)

class DocumentRequestCreate(DocumentRequestBase):
    document_id: Optional[int] = None  # For requesting existing documents

class DocumentRequestUpdate(BaseModel):
    document_title: Optional[str] = Field(None, min_length=1, max_length=200)
    document_type: Optional[DocumentTypeEnum] = None
    description: Optional[str] = Field(None, min_length=10, max_length=1000)
    purpose: Optional[str] = Field(None, max_length=500)
    format_preference: Optional[str] = Field(None, max_length=20)
    delivery_method: Optional[str] = Field(None, max_length=20)
    urgency: Optional[str] = Field(None, pattern="^(low|normal|high|urgent)$")
    certified_copy: Optional[bool] = None
    multiple_copies: Optional[int] = Field(None, ge=1, le=10)
    special_instructions: Optional[str] = Field(None, max_length=1000)
    processing_notes: Optional[str] = Field(None, max_length=1000)
    completion_notes: Optional[str] = Field(None, max_length=1000)

class DocumentRequestResponse(BaseModel):
    id: int
    request_id: str
    employee_id: int
    employee_name: Optional[str] = None
    employee_employee_id: Optional[str] = None
    
    # Request details
    document_id: Optional[int] = None
    document_title: str
    document_type: DocumentTypeEnum
    description: str
    purpose: Optional[str] = None
    
    # Request specifications
    format_preference: str
    delivery_method: str
    urgency: str
    certified_copy: bool
    multiple_copies: int
    special_instructions: Optional[str] = None
    
    # Workflow information
    status: RequestStatusEnum
    assigned_to: Optional[int] = None
    assigned_to_name: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Approval information
    requires_approval: bool
    approver_id: Optional[int] = None
    approver_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_comments: Optional[str] = None
    
    # Processing information
    processing_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    completion_notes: Optional[str] = None
    
    # Generated document information
    generated_file_path: Optional[str] = None
    generated_file_name: Optional[str] = None
    expiry_date: Optional[datetime] = None
    
    # Status flags
    is_pending: bool
    is_completed: bool
    is_overdue: bool
    days_since_submission: int
    can_be_cancelled: bool
    
    # Timestamps
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentRequestList(BaseModel):
    id: int
    request_id: str
    employee_name: Optional[str] = None
    document_title: str
    document_type: DocumentTypeEnum
    status: RequestStatusEnum
    urgency: str
    submitted_at: datetime
    estimated_completion: Optional[datetime] = None
    is_overdue: bool
    days_since_submission: int

    class Config:
        from_attributes = True

# Document Search and Filter Schemas
class DocumentSearchParams(BaseModel):
    search: Optional[str] = Field(None, max_length=200)
    document_type: Optional[DocumentTypeEnum] = None
    status: Optional[DocumentStatusEnum] = None
    access_level: Optional[AccessLevelEnum] = None
    author_id: Optional[int] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None
    is_expired: Optional[bool] = None
    needs_review: Optional[bool] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=1000)
    sort_by: Optional[str] = Field("updated_at", pattern="^(title|document_type|status|created_at|updated_at|view_count|download_count)$")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$")

class DocumentRequestSearchParams(BaseModel):
    search: Optional[str] = Field(None, max_length=200)
    employee_id: Optional[int] = None
    document_type: Optional[DocumentTypeEnum] = None
    status: Optional[RequestStatusEnum] = None
    urgency: Optional[str] = Field(None, pattern="^(low|normal|high|urgent)$")
    assigned_to: Optional[int] = None
    submitted_from: Optional[datetime] = None
    submitted_to: Optional[datetime] = None
    is_overdue: Optional[bool] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)
    sort_by: Optional[str] = Field("submitted_at", pattern="^(submitted_at|document_title|status|urgency|employee_name)$")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$")

# Document Analytics Schemas
class DocumentAnalytics(BaseModel):
    total_documents: int
    published_documents: int
    draft_documents: int
    expired_documents: int
    needs_review: int
    total_views: int
    total_downloads: int
    popular_documents: List[dict]
    documents_by_type: dict
    documents_by_access_level: dict
    recent_activity: List[dict]

class DocumentRequestAnalytics(BaseModel):
    total_requests: int
    pending_requests: int
    processing_requests: int
    completed_requests: int
    rejected_requests: int
    overdue_requests: int
    average_processing_time_days: float
    requests_by_type: dict
    requests_by_urgency: dict
    monthly_trends: dict

# Bulk Operations Schemas
class DocumentBulkAction(BaseModel):
    document_ids: List[int] = Field(..., min_items=1)
    action: str = Field(..., pattern="^(publish|archive|delete|change_access_level)$")
    access_level: Optional[AccessLevelEnum] = None

class DocumentRequestBulkAction(BaseModel):
    request_ids: List[str] = Field(..., min_items=1)
    action: str = Field(..., pattern="^(assign|approve|reject|cancel)$")
    assigned_to: Optional[int] = None
    comments: Optional[str] = Field(None, max_length=500)

# Upload Schemas
class DocumentUploadResponse(BaseModel):
    success: bool
    document_id: Optional[int] = None
    file_name: str
    file_size: int
    file_size_mb: float
    message: str
    errors: List[str] = []

# Document Version Schemas
class DocumentVersion(BaseModel):
    version: str
    created_at: datetime
    author_name: str
    file_size: int
    changes: Optional[str] = None

class DocumentVersionHistory(BaseModel):
    document_id: int
    current_version: str
    versions: List[DocumentVersion]

# Document Access Log Schema
class DocumentAccessLog(BaseModel):
    document_id: int
    document_title: str
    employee_id: int
    employee_name: str
    action: str  # view, download, edit
    timestamp: datetime
    ip_address: Optional[str] = None
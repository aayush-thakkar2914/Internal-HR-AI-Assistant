"""
Document management models for the HR AI Assistant.

This module contains SQLAlchemy ORM models for document storage,
document requests, and file management.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, BigInteger, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum

from app.config.database import Base

class DocumentType(enum.Enum):
    """Document type enumeration"""
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

class DocumentStatus(enum.Enum):
    """Document status enumeration"""
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    EXPIRED = "expired"

class AccessLevel(enum.Enum):
    """Document access level enumeration"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class RequestStatus(enum.Enum):
    """Document request status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class Document(Base):
    """Document model for HR document management"""
    
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    document_type = Column(Enum(DocumentType), nullable=False)
    
    # File information
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(200), nullable=False)
    file_size = Column(BigInteger)  # Size in bytes
    file_extension = Column(String(10))
    mime_type = Column(String(100))
    
    # Content and metadata
    content_text = Column(Text)  # Extracted text content for search
    keywords = Column(Text)  # Comma-separated keywords
    tags = Column(Text)  # JSON array of tags
    version = Column(String(20), default="1.0")
    language = Column(String(10), default="en")
    
    # Access and permissions
    access_level = Column(Enum(AccessLevel), default=AccessLevel.INTERNAL)
    department_access = Column(Text)  # JSON array of department IDs
    role_access = Column(Text)  # JSON array of role IDs
    
    # Document lifecycle
    status = Column(Enum(DocumentStatus), default=DocumentStatus.DRAFT)
    effective_date = Column(DateTime)
    expiry_date = Column(DateTime)
    review_date = Column(DateTime)
    
    # Approval workflow
    author_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("employees.id"))
    approver_id = Column(Integer, ForeignKey("employees.id"))
    reviewed_at = Column(DateTime)
    approved_at = Column(DateTime)
    published_at = Column(DateTime)
    
    # Search and indexing
    is_searchable = Column(Boolean, default=True)
    opensearch_indexed = Column(Boolean, default=False)
    search_boost = Column(Integer, default=1)  # Search relevance boost
    
    # Analytics
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    last_accessed = Column(DateTime)
    
    # System fields
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    author = relationship("Employee", foreign_keys=[author_id])
    reviewer = relationship("Employee", foreign_keys=[reviewer_id])
    approver = relationship("Employee", foreign_keys=[approver_id])
    document_requests = relationship("DocumentRequest", back_populates="document")
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0.0
    
    @property
    def is_expired(self) -> bool:
        """Check if document is expired"""
        if self.expiry_date:
            return datetime.utcnow() > self.expiry_date
        return False
    
    @property
    def needs_review(self) -> bool:
        """Check if document needs review"""
        if self.review_date:
            return datetime.utcnow() > self.review_date
        return False
    
    @property
    def is_published(self) -> bool:
        """Check if document is published"""
        return self.status == DocumentStatus.PUBLISHED
    
    def increment_view_count(self):
        """Increment document view count"""
        self.view_count += 1
        self.last_accessed = datetime.utcnow()
    
    def increment_download_count(self):
        """Increment document download count"""
        self.download_count += 1
        self.last_accessed = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert document to dictionary representation"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "document_type": self.document_type.value if self.document_type else None,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "file_size_mb": self.file_size_mb,
            "file_extension": self.file_extension,
            "version": self.version,
            "status": self.status.value if self.status else None,
            "access_level": self.access_level.value if self.access_level else None,
            "author": self.author.full_name if self.author else None,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "is_expired": self.is_expired,
            "needs_review": self.needs_review,
            "view_count": self.view_count,
            "download_count": self.download_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}', type='{self.document_type.value}')>"

class DocumentRequest(Base):
    """Document request model for employee document requests"""
    
    __tablename__ = "document_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(20), unique=True, nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # Request details
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)  # For existing documents
    document_title = Column(String(200), nullable=False)  # For new document requests
    document_type = Column(Enum(DocumentType), nullable=False)
    description = Column(Text, nullable=False)
    purpose = Column(Text)  # Why the document is needed
    
    # Request specifics
    format_preference = Column(String(20), default="pdf")  # pdf, docx, etc.
    delivery_method = Column(String(20), default="email")  # email, pickup, etc.
    urgency = Column(String(20), default="normal")  # low, normal, high, urgent
    
    # Additional requirements
    certified_copy = Column(Boolean, default=False)
    multiple_copies = Column(Integer, default=1)
    special_instructions = Column(Text)
    
    # Request workflow
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING)
    assigned_to = Column(Integer, ForeignKey("employees.id"))  # HR personnel assigned
    estimated_completion = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Approval (if required)
    requires_approval = Column(Boolean, default=False)
    approver_id = Column(Integer, ForeignKey("employees.id"))
    approved_at = Column(DateTime)
    approval_comments = Column(Text)
    
    # Processing notes
    processing_notes = Column(Text)
    rejection_reason = Column(Text)
    completion_notes = Column(Text)
    
    # Generated document info
    generated_file_path = Column(String(500))
    generated_file_name = Column(String(200))
    expiry_date = Column(DateTime)  # For time-limited documents
    
    # System fields
    submitted_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = relationship("Employee", back_populates="document_requests", foreign_keys=[employee_id])
    document = relationship("Document", back_populates="document_requests")
    assigned_employee = relationship("Employee", foreign_keys=[assigned_to])
    approver = relationship("Employee", foreign_keys=[approver_id])
    
    @property
    def is_pending(self) -> bool:
        """Check if request is pending"""
        return self.status == RequestStatus.PENDING
    
    @property
    def is_completed(self) -> bool:
        """Check if request is completed"""
        return self.status == RequestStatus.COMPLETED
    
    @property
    def is_overdue(self) -> bool:
        """Check if request is overdue"""
        if self.estimated_completion and self.status not in [RequestStatus.COMPLETED, RequestStatus.CANCELLED]:
            return datetime.utcnow() > self.estimated_completion
        return False
    
    @property
    def days_since_submission(self) -> int:
        """Calculate days since request submission"""
        return (datetime.utcnow() - self.submitted_at).days
    
    def can_be_cancelled(self) -> bool:
        """Check if request can be cancelled"""
        return self.status in [RequestStatus.PENDING, RequestStatus.PROCESSING]
    
    def to_dict(self) -> dict:
        """Convert document request to dictionary representation"""
        return {
            "id": self.id,
            "request_id": self.request_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "employee_id": self.employee.employee_id if self.employee else None,
            "document_title": self.document_title,
            "document_type": self.document_type.value if self.document_type else None,
            "description": self.description,
            "status": self.status.value if self.status else None,
            "urgency": self.urgency,
            "certified_copy": self.certified_copy,
            "multiple_copies": self.multiple_copies,
            "assigned_to": self.assigned_employee.full_name if self.assigned_employee else None,
            "estimated_completion": self.estimated_completion.isoformat() if self.estimated_completion else None,
            "is_overdue": self.is_overdue,
            "days_since_submission": self.days_since_submission,
            "can_be_cancelled": self.can_be_cancelled(),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<DocumentRequest(id={self.id}, request_id='{self.request_id}', employee_id={self.employee_id}, status='{self.status.value}')>"
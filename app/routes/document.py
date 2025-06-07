"""
Document management API routes for the HR AI Assistant.

This module contains all document-related endpoints including document uploads,
requests, downloads, and document management operations.
"""

import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Any, Optional

from app.config.database import get_db
from app.models.employee import Employee
from app.models.document import Document, DocumentRequest, DocumentType, DocumentStatus, RequestStatus
from app.schemas.document import (
    DocumentCreate, DocumentUpdate, DocumentResponse,
    DocumentRequestCreate, DocumentRequestUpdate, DocumentRequestResponse
)
from app.services.document_service import document_service
from app.services.notification_service import notification_service
from app.middleware.auth import get_current_active_user, require_role
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Document Management Routes

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    document_type: DocumentType = Form(...),
    keywords: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    access_level: str = Form("internal"),
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Upload a new document (HR only)
    
    Args:
        file: Uploaded file
        title: Document title
        description: Document description
        document_type: Type of document
        keywords: Document keywords
        tags: Document tags
        access_level: Access level
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        DocumentResponse: Uploaded document information
    """
    try:
        # Prepare metadata
        metadata = {
            "title": title,
            "description": description,
            "document_type": document_type,
            "keywords": keywords,
            "tags": tags,
            "access_level": access_level
        }
        
        # Process file upload
        success, document, errors = document_service.process_uploaded_file(
            db, file.file, file.filename, current_user, **metadata
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upload failed: {', '.join(errors)}"
            )
        
        logger.info(f"Document uploaded: {document.id} by {current_user.employee_id}")
        
        return DocumentResponse.from_orm(document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document"
        )

@router.get("/", response_model=List[DocumentResponse])
async def get_documents(
    document_type: Optional[DocumentType] = Query(None),
    status_filter: Optional[DocumentStatus] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get documents with filtering and search
    
    Args:
        document_type: Filter by document type
        status_filter: Filter by document status
        search: Search term for title and content
        skip: Number of documents to skip
        limit: Maximum number of documents to return
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[DocumentResponse]: List of documents
    """
    try:
        query = db.query(Document).filter(Document.is_active == True)
        
        # Apply filters
        if document_type:
            query = query.filter(Document.document_type == document_type)
        
        if status_filter:
            query = query.filter(Document.status == status_filter)
        else:
            # Only show published documents for non-HR users
            if current_user.role.title.lower() not in ['hr', 'human resources']:
                query = query.filter(Document.status == DocumentStatus.PUBLISHED)
        
        # Apply search
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Document.title.ilike(search_term),
                    Document.description.ilike(search_term),
                    Document.keywords.ilike(search_term),
                    Document.content_text.ilike(search_term)
                )
            )
        
        # Apply access control (simplified)
        # In a real implementation, this would check department/role access
        
        # Apply pagination and ordering
        documents = query.order_by(Document.updated_at.desc())\
                        .offset(skip).limit(limit).all()
        
        # Update view counts
        for doc in documents:
            doc.increment_view_count()
        
        db.commit()
        
        return [DocumentResponse.from_orm(doc) for doc in documents]
        
    except Exception as e:
        logger.error(f"Error retrieving documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents"
        )

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get specific document by ID
    
    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        DocumentResponse: Document information
    """
    try:
        document = db.query(Document).filter(
            and_(
                Document.id == document_id,
                Document.is_active == True
            )
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check access permissions (simplified)
        if (document.status != DocumentStatus.PUBLISHED and 
            current_user.role.title.lower() not in ['hr', 'human resources'] and
            document.author_id != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Update view count
        document.increment_view_count()
        db.commit()
        
        return DocumentResponse.from_orm(document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document"
        )

@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Download document file
    
    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        FileResponse: Document file
    """
    try:
        document = db.query(Document).filter(
            and_(
                Document.id == document_id,
                Document.is_active == True
            )
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check access permissions
        if (document.status != DocumentStatus.PUBLISHED and 
            current_user.role.title.lower() not in ['hr', 'human resources'] and
            document.author_id != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check if file exists
        if not os.path.exists(document.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found"
            )
        
        # Update download count
        document.increment_download_count()
        db.commit()
        
        return FileResponse(
            path=document.file_path,
            filename=document.file_name,
            media_type=document.mime_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download document"
        )

@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Update document metadata (HR only)
    
    Args:
        document_id: Document ID
        document_update: Document update data
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        DocumentResponse: Updated document
    """
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Update fields
        update_data = document_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(document, field):
                setattr(document, field, value)
        
        document.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(document)
        
        logger.info(f"Document updated: {document.id} by {current_user.employee_id}")
        
        return DocumentResponse.from_orm(document)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document"
        )

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Delete document (HR only)
    
    Args:
        document_id: Document ID
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        Dict: Deletion confirmation
    """
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Soft delete
        document.is_active = False
        document.updated_at = datetime.utcnow()
        
        # Remove from search index
        try:
            from app.services.rag_service import rag_service
            rag_service.remove_document_from_index(document.id)
        except Exception as e:
            logger.warning(f"Failed to remove document from search index: {e}")
        
        db.commit()
        
        logger.info(f"Document deleted: {document.id} by {current_user.employee_id}")
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )

# Document Request Routes

@router.post("/requests", response_model=DocumentRequestResponse)
async def create_document_request(
    request_data: DocumentRequestCreate,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new document request
    
    Args:
        request_data: Document request data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        DocumentRequestResponse: Created document request
    """
    try:
        success, doc_request, errors = document_service.create_document_request(
            db, current_user, request_data.dict()
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Request creation failed: {', '.join(errors)}"
            )
        
        logger.info(f"Document request created: {doc_request.request_id}")
        
        return DocumentRequestResponse.from_orm(doc_request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating document request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create document request"
        )

@router.get("/requests", response_model=List[DocumentRequestResponse])
async def get_document_requests(
    status_filter: Optional[RequestStatus] = Query(None),
    employee_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get document requests with filtering
    
    Args:
        status_filter: Filter by request status
        employee_id: Filter by employee ID (HR only)
        skip: Number of requests to skip
        limit: Maximum number of requests to return
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[DocumentRequestResponse]: List of document requests
    """
    try:
        query = db.query(DocumentRequest)
        
        # Filter by user unless they're HR
        if current_user.role.title.lower() not in ['hr', 'human resources']:
            query = query.filter(DocumentRequest.employee_id == current_user.id)
        elif employee_id:
            query = query.filter(DocumentRequest.employee_id == employee_id)
        
        # Apply status filter
        if status_filter:
            query = query.filter(DocumentRequest.status == status_filter)
        
        # Apply pagination and ordering
        requests = query.order_by(DocumentRequest.submitted_at.desc())\
                       .offset(skip).limit(limit).all()
        
        return [DocumentRequestResponse.from_orm(req) for req in requests]
        
    except Exception as e:
        logger.error(f"Error retrieving document requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document requests"
        )

@router.get("/requests/{request_id}", response_model=DocumentRequestResponse)
async def get_document_request(
    request_id: str,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get specific document request by ID
    
    Args:
        request_id: Document request ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        DocumentRequestResponse: Document request details
    """
    try:
        doc_request = db.query(DocumentRequest).filter(
            DocumentRequest.request_id == request_id
        ).first()
        
        if not doc_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document request not found"
            )
        
        # Check permissions
        if (doc_request.employee_id != current_user.id and 
            current_user.role.title.lower() not in ['hr', 'human resources']):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return DocumentRequestResponse.from_orm(doc_request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document request"
        )

@router.put("/requests/{request_id}", response_model=DocumentRequestResponse)
async def update_document_request(
    request_id: str,
    request_update: DocumentRequestUpdate,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update document request
    
    Args:
        request_id: Document request ID
        request_update: Request update data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        DocumentRequestResponse: Updated document request
    """
    try:
        doc_request = db.query(DocumentRequest).filter(
            DocumentRequest.request_id == request_id
        ).first()
        
        if not doc_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document request not found"
            )
        
        # Check permissions
        if (doc_request.employee_id != current_user.id and 
            current_user.role.title.lower() not in ['hr', 'human resources']):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check if request can be modified
        if doc_request.status not in [RequestStatus.PENDING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request cannot be modified in current status"
            )
        
        # Update fields
        update_data = request_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(doc_request, field):
                setattr(doc_request, field, value)
        
        doc_request.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(doc_request)
        
        logger.info(f"Document request updated: {request_id}")
        
        return DocumentRequestResponse.from_orm(doc_request)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating document request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document request"
        )

@router.post("/requests/{request_id}/assign")
async def assign_document_request(
    request_id: str,
    assignee_id: int,
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Assign document request to HR personnel (HR only)
    
    Args:
        request_id: Document request ID
        assignee_id: Employee ID to assign to
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        Dict: Assignment confirmation
    """
    try:
        doc_request = db.query(DocumentRequest).filter(
            DocumentRequest.request_id == request_id
        ).first()
        
        if not doc_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document request not found"
            )
        
        assignee = db.query(Employee).filter(Employee.id == assignee_id).first()
        
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignee not found"
            )
        
        success, errors = document_service.assign_request(db, doc_request, assignee)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Assignment failed: {', '.join(errors)}"
            )
        
        return {"message": f"Request assigned to {assignee.full_name}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning document request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign document request"
        )

@router.post("/requests/{request_id}/complete")
async def complete_document_request(
    request_id: str,
    completion_notes: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Mark document request as completed (HR only)
    
    Args:
        request_id: Document request ID
        completion_notes: Completion notes
        file: Generated document file (optional)
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        Dict: Completion confirmation
    """
    try:
        doc_request = db.query(DocumentRequest).filter(
            DocumentRequest.request_id == request_id
        ).first()
        
        if not doc_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document request not found"
            )
        
        completion_data = {"notes": completion_notes}
        
        # Handle file upload if provided
        if file:
            # Save uploaded file
            file_path = f"uploads/generated_{doc_request.request_id}_{file.filename}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, "wb") as f:
                f.write(file.file.read())
            
            completion_data.update({
                "file_path": file_path,
                "file_name": file.filename
            })
        
        success, errors = document_service.complete_request(db, doc_request, completion_data)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Completion failed: {', '.join(errors)}"
            )
        
        # Send completion notification
        try:
            notification_service.notify_document_request_completed(doc_request)
        except Exception as e:
            logger.warning(f"Failed to send completion notification: {e}")
        
        return {"message": "Document request marked as completed"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing document request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete document request"
        )
"""
Leave management API routes for the HR AI Assistant.

This module contains all leave-related endpoints including leave requests,
approvals, balances, and leave management operations.
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Any, Optional

from app.config.database import get_db
from app.models.employee import Employee
from app.models.leave import LeaveRequest, LeaveType, LeaveBalance, LeaveStatus
from app.schemas.leave import (
    LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestResponse,
    LeaveTypeCreate, LeaveTypeUpdate, LeaveTypeResponse,
    LeaveBalanceResponse, LeaveRequestSearchParams, LeaveApprovalAction,
    LeaveCancellation, LeaveStatistics, LeavePolicyValidation
)
from app.services.leave_service import leave_service
from app.services.notification_service import notification_service
from app.middleware.auth import get_current_active_user, require_role, require_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Leave Request Routes

@router.post("/requests", response_model=LeaveRequestResponse)
async def create_leave_request(
    leave_data: LeaveRequestCreate,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new leave request
    
    Args:
        leave_data: Leave request data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        LeaveRequestResponse: Created leave request
    """
    try:
        success, leave_request, errors = leave_service.create_leave_request(
            db, current_user, leave_data
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Leave request creation failed: {', '.join(errors)}"
            )
        
        # Send notifications
        try:
            notification_service.notify_leave_request_submitted(leave_request)
            if leave_request.manager:
                notification_service.notify_manager_approval_needed(leave_request)
        except Exception as e:
            logger.warning(f"Failed to send notifications: {e}")
        
        logger.info(f"Leave request created: {leave_request.request_id}")
        
        return LeaveRequestResponse.from_orm(leave_request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating leave request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create leave request"
        )

@router.get("/requests", response_model=List[LeaveRequestResponse])
async def get_leave_requests(
    search_params: LeaveRequestSearchParams = Depends(),
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get leave requests with filtering and pagination
    
    Args:
        search_params: Search and filter parameters
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[LeaveRequestResponse]: List of leave requests
    """
    try:
        query = db.query(LeaveRequest)
        
        # Filter by user unless they're a manager/HR
        if not (current_user.is_manager or current_user.role.title.lower() in ['hr', 'human resources']):
            query = query.filter(LeaveRequest.employee_id == current_user.id)
        elif search_params.employee_id:
            query = query.filter(LeaveRequest.employee_id == search_params.employee_id)
        elif current_user.is_manager and not current_user.role.title.lower() in ['hr', 'human resources']:
            # Show requests from team members
            query = query.filter(LeaveRequest.manager_id == current_user.id)
        
        # Apply filters
        if search_params.leave_type_id:
            query = query.filter(LeaveRequest.leave_type_id == search_params.leave_type_id)
        
        if search_params.status:
            query = query.filter(LeaveRequest.status == search_params.status)
        
        if search_params.priority:
            query = query.filter(LeaveRequest.priority == search_params.priority)
        
        if search_params.start_date_from:
            query = query.filter(LeaveRequest.start_date >= search_params.start_date_from)
        
        if search_params.start_date_to:
            query = query.filter(LeaveRequest.start_date <= search_params.start_date_to)
        
        if search_params.submitted_from:
            query = query.filter(LeaveRequest.submitted_date >= search_params.submitted_from)
        
        if search_params.submitted_to:
            query = query.filter(LeaveRequest.submitted_date <= search_params.submitted_to)
        
        if search_params.manager_id:
            query = query.filter(LeaveRequest.manager_id == search_params.manager_id)
        
        if search_params.is_current:
            today = date.today()
            query = query.filter(
                and_(
                    LeaveRequest.start_date <= today,
                    LeaveRequest.end_date >= today,
                    LeaveRequest.status == LeaveStatus.APPROVED
                )
            )
        
        if search_params.is_future:
            query = query.filter(LeaveRequest.start_date > date.today())
        
        if search_params.requires_approval:
            query = query.filter(
                and_(
                    LeaveRequest.status == LeaveStatus.PENDING,
                    or_(
                        LeaveRequest.manager_approval_date.is_(None),
                        and_(
                            LeaveRequest.hr_approval_required == True,
                            LeaveRequest.hr_approval_date.is_(None)
                        )
                    )
                )
            )
        
        # Apply sorting
        if search_params.sort_by == "submitted_date":
            if search_params.sort_order == "desc":
                query = query.order_by(LeaveRequest.submitted_date.desc())
            else:
                query = query.order_by(LeaveRequest.submitted_date.asc())
        elif search_params.sort_by == "start_date":
            if search_params.sort_order == "desc":
                query = query.order_by(LeaveRequest.start_date.desc())
            else:
                query = query.order_by(LeaveRequest.start_date.asc())
        
        # Apply pagination
        leave_requests = query.offset(search_params.skip).limit(search_params.limit).all()
        
        return [LeaveRequestResponse.from_orm(lr) for lr in leave_requests]
        
    except Exception as e:
        logger.error(f"Error retrieving leave requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve leave requests"
        )

@router.get("/requests/{request_id}", response_model=LeaveRequestResponse)
async def get_leave_request(
    request_id: str,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get specific leave request by ID
    
    Args:
        request_id: Leave request ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        LeaveRequestResponse: Leave request details
    """
    try:
        leave_request = db.query(LeaveRequest).filter(
            LeaveRequest.request_id == request_id
        ).first()
        
        if not leave_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found"
            )
        
        # Check permissions
        if (leave_request.employee_id != current_user.id and 
            not current_user.is_manager and 
            current_user.role.title.lower() not in ['hr', 'human resources']):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return LeaveRequestResponse.from_orm(leave_request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving leave request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve leave request"
        )

@router.put("/requests/{request_id}", response_model=LeaveRequestResponse)
async def update_leave_request(
    request_id: str,
    update_data: LeaveRequestUpdate,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update leave request
    
    Args:
        request_id: Leave request ID
        update_data: Update data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        LeaveRequestResponse: Updated leave request
    """
    try:
        leave_request = db.query(LeaveRequest).filter(
            LeaveRequest.request_id == request_id
        ).first()
        
        if not leave_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found"
            )
        
        success, errors = leave_service.update_leave_request(
            db, leave_request, update_data, current_user
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Update failed: {', '.join(errors)}"
            )
        
        db.refresh(leave_request)
        logger.info(f"Leave request updated: {request_id}")
        
        return LeaveRequestResponse.from_orm(leave_request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating leave request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update leave request"
        )

@router.post("/requests/{request_id}/approve")
async def approve_leave_request(
    request_id: str,
    approval_data: LeaveApprovalAction,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Approve leave request
    
    Args:
        request_id: Leave request ID
        approval_data: Approval action data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Approval confirmation
    """
    try:
        leave_request = db.query(LeaveRequest).filter(
            LeaveRequest.request_id == request_id
        ).first()
        
        if not leave_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found"
            )
        
        if approval_data.action == "approve":
            success, errors = leave_service.approve_leave_request(
                db, leave_request, current_user, approval_data.comments
            )
            
            if success:
                # Send approval notification
                try:
                    notification_service.notify_leave_request_approved(leave_request, current_user)
                except Exception as e:
                    logger.warning(f"Failed to send approval notification: {e}")
                
                return {"message": "Leave request approved successfully"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Approval failed: {', '.join(errors)}"
                )
        
        elif approval_data.action == "reject":
            success, errors = leave_service.reject_leave_request(
                db, leave_request, current_user, approval_data.comments
            )
            
            if success:
                # Send rejection notification
                try:
                    notification_service.notify_leave_request_rejected(leave_request, current_user)
                except Exception as e:
                    logger.warning(f"Failed to send rejection notification: {e}")
                
                return {"message": "Leave request rejected"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Rejection failed: {', '.join(errors)}"
                )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action. Must be 'approve' or 'reject'"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing leave approval: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process approval"
        )

@router.post("/requests/{request_id}/cancel")
async def cancel_leave_request(
    request_id: str,
    cancellation_data: LeaveCancellation,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cancel leave request
    
    Args:
        request_id: Leave request ID
        cancellation_data: Cancellation data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Cancellation confirmation
    """
    try:
        leave_request = db.query(LeaveRequest).filter(
            LeaveRequest.request_id == request_id
        ).first()
        
        if not leave_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found"
            )
        
        success, errors = leave_service.cancel_leave_request(
            db, leave_request, current_user, cancellation_data.reason
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cancellation failed: {', '.join(errors)}"
            )
        
        logger.info(f"Leave request cancelled: {request_id}")
        
        return {"message": "Leave request cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling leave request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel leave request"
        )

@router.post("/requests/validate", response_model=LeavePolicyValidation)
async def validate_leave_policy(
    leave_type_id: int,
    start_date: date,
    end_date: date,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Validate leave request against company policies
    
    Args:
        leave_type_id: Leave type ID
        start_date: Start date
        end_date: End date
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        LeavePolicyValidation: Validation result
    """
    try:
        total_days = leave_service.calculate_leave_days(start_date, end_date)
        
        validation = leave_service.validate_leave_policy(
            db, current_user, leave_type_id, start_date, end_date, total_days
        )
        
        return validation
        
    except Exception as e:
        logger.error(f"Error validating leave policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate leave policy"
        )

# Leave Balance Routes

@router.get("/balances", response_model=List[LeaveBalanceResponse])
async def get_leave_balances(
    year: Optional[int] = Query(None),
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get leave balances for current user
    
    Args:
        year: Year to get balances for (defaults to current year)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[LeaveBalanceResponse]: Leave balances
    """
    try:
        if not year:
            year = date.today().year
        
        balances = db.query(LeaveBalance).filter(
            and_(
                LeaveBalance.employee_id == current_user.id,
                LeaveBalance.year == year
            )
        ).all()
        
        return [LeaveBalanceResponse.from_orm(balance) for balance in balances]
        
    except Exception as e:
        logger.error(f"Error retrieving leave balances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve leave balances"
        )

# Leave Type Routes

@router.get("/types", response_model=List[LeaveTypeResponse])
async def get_leave_types(
    active_only: bool = Query(True),
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get available leave types
    
    Args:
        active_only: Whether to return only active leave types
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[LeaveTypeResponse]: Available leave types
    """
    try:
        query = db.query(LeaveType)
        
        if active_only:
            query = query.filter(LeaveType.is_active == True)
        
        leave_types = query.all()
        
        return [LeaveTypeResponse.from_orm(lt) for lt in leave_types]
        
    except Exception as e:
        logger.error(f"Error retrieving leave types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve leave types"
        )

@router.post("/types", response_model=LeaveTypeResponse)
async def create_leave_type(
    leave_type_data: LeaveTypeCreate,
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Create new leave type (HR only)
    
    Args:
        leave_type_data: Leave type creation data
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        LeaveTypeResponse: Created leave type
    """
    try:
        # Check if leave type code is unique
        existing_type = db.query(LeaveType).filter(
            LeaveType.code == leave_type_data.code
        ).first()
        
        if existing_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Leave type code already exists"
            )
        
        leave_type = LeaveType(**leave_type_data.dict())
        
        db.add(leave_type)
        db.commit()
        db.refresh(leave_type)
        
        logger.info(f"Leave type created: {leave_type.name} by {current_user.employee_id}")
        
        return LeaveTypeResponse.from_orm(leave_type)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating leave type: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create leave type"
        )

# Leave Statistics and Reports

@router.get("/statistics", response_model=LeaveStatistics)
async def get_leave_statistics(
    year: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Get leave statistics and analytics (HR only)
    
    Args:
        year: Year for statistics (defaults to current year)
        department_id: Filter by department
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        LeaveStatistics: Leave statistics
    """
    try:
        from sqlalchemy import func, extract
        
        if not year:
            year = date.today().year
        
        query = db.query(LeaveRequest)
        
        # Apply year filter
        query = query.filter(extract('year', LeaveRequest.start_date) == year)
        
        # Apply department filter if specified
        if department_id:
            query = query.join(Employee, LeaveRequest.employee_id == Employee.id)\
                         .filter(Employee.department_id == department_id)
        
        # Basic statistics
        total_requests = query.count()
        
        pending_requests = query.filter(LeaveRequest.status == LeaveStatus.PENDING).count()
        approved_requests = query.filter(LeaveRequest.status == LeaveStatus.APPROVED).count()
        rejected_requests = query.filter(LeaveRequest.status == LeaveStatus.REJECTED).count()
        
        # Calculate total days
        total_days_requested = query.with_entities(
            func.sum(LeaveRequest.total_days)
        ).scalar() or 0
        
        approved_days = query.filter(LeaveRequest.status == LeaveStatus.APPROVED)\
                            .with_entities(func.sum(LeaveRequest.total_days)).scalar() or 0
        
        # Average processing time (simplified)
        avg_processing_time = 2.5  # This would need actual calculation
        
        return LeaveStatistics(
            total_requests=total_requests,
            pending_requests=pending_requests,
            approved_requests=approved_requests,
            rejected_requests=rejected_requests,
            total_days_requested=float(total_days_requested),
            total_days_approved=float(approved_days),
            average_processing_time_days=avg_processing_time,
            by_leave_type=[],  # This would need detailed calculation
            by_month={},       # This would need detailed calculation
            by_department={}   # This would need detailed calculation
        )
        
    except Exception as e:
        logger.error(f"Error retrieving leave statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )
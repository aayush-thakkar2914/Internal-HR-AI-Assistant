"""
Leave management service for the HR AI Assistant.

This service handles all leave-related business logic including leave requests,
approvals, balance calculations, and policy validations.
"""

import secrets
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, extract

from app.models.employee import Employee
from app.models.leave import LeaveRequest, LeaveType, LeaveBalance, LeaveStatus, LeavePriority
from app.schemas.leave import LeaveRequestCreate, LeaveRequestUpdate, LeavePolicyValidation
from app.utils.logger import get_logger

logger = get_logger(__name__)

class LeaveService:
    """
    Leave management service for handling all leave-related operations
    """
    
    def __init__(self):
        # Business rules configuration
        self.weekend_days = [5, 6]  # Saturday, Sunday (0=Monday)
        self.public_holidays = []  # Will be loaded from database/config
        
        # Policy validation settings
        self.min_advance_notice_days = 1
        self.max_advance_notice_days = 365
        
    def generate_request_id(self) -> str:
        """
        Generate unique leave request ID
        
        Returns:
            str: Unique request ID
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        random_suffix = secrets.token_hex(3).upper()
        return f"LR{timestamp}{random_suffix}"
    
    def calculate_leave_days(self, start_date: date, end_date: date, 
                           exclude_weekends: bool = True,
                           exclude_holidays: bool = True) -> float:
        """
        Calculate number of leave days between two dates
        
        Args:
            start_date: Leave start date
            end_date: Leave end date
            exclude_weekends: Whether to exclude weekends
            exclude_holidays: Whether to exclude public holidays
            
        Returns:
            float: Number of leave days
        """
        if start_date > end_date:
            return 0
        
        total_days = 0
        current_date = start_date
        
        while current_date <= end_date:
            # Check if it's a weekend
            if exclude_weekends and current_date.weekday() in self.weekend_days:
                current_date += timedelta(days=1)
                continue
            
            # Check if it's a public holiday
            if exclude_holidays and current_date in self.public_holidays:
                current_date += timedelta(days=1)
                continue
            
            total_days += 1
            current_date += timedelta(days=1)
        
        return total_days
    
    def validate_leave_policy(self, db: Session, employee: Employee, 
                            leave_type_id: int, start_date: date, 
                            end_date: date, total_days: float) -> LeavePolicyValidation:
        """
        Validate leave request against company policies
        
        Args:
            db: Database session
            employee: Employee requesting leave
            leave_type_id: Type of leave being requested
            start_date: Leave start date
            end_date: Leave end date
            total_days: Total days requested
            
        Returns:
            LeavePolicyValidation: Validation result with violations and warnings
        """
        violations = []
        warnings = []
        suggestions = []
        
        # Get leave type
        leave_type = db.query(LeaveType).filter(LeaveType.id == leave_type_id).first()
        if not leave_type:
            violations.append("Invalid leave type")
            return LeavePolicyValidation(
                is_valid=False,
                violations=violations,
                warnings=warnings,
                suggestions=suggestions
            )
        
        # Check if leave type is active
        if not leave_type.is_active:
            violations.append(f"{leave_type.name} is not currently available")
        
        # Check advance notice requirements
        days_until_start = (start_date - date.today()).days
        
        if days_until_start < leave_type.min_advance_notice_days:
            violations.append(
                f"Minimum {leave_type.min_advance_notice_days} days advance notice required for {leave_type.name}"
            )
        
        if days_until_start > leave_type.max_advance_notice_days:
            warnings.append(
                f"Leave request is more than {leave_type.max_advance_notice_days} days in advance"
            )
        
        # Check maximum consecutive days
        if leave_type.max_consecutive_days > 0 and total_days > leave_type.max_consecutive_days:
            violations.append(
                f"Maximum {leave_type.max_consecutive_days} consecutive days allowed for {leave_type.name}"
            )
        
        # Check annual limit
        if leave_type.max_days_per_year > 0:
            current_year = start_date.year
            year_usage = self.get_leave_usage_for_year(db, employee.id, leave_type_id, current_year)
            
            if year_usage + total_days > leave_type.max_days_per_year:
                violations.append(
                    f"Annual limit of {leave_type.max_days_per_year} days exceeded for {leave_type.name}"
                )
        
        # Check leave balance
        leave_balance = self.get_leave_balance(db, employee.id, leave_type_id, start_date.year)
        if leave_balance and leave_balance.available_days < total_days:
            violations.append(
                f"Insufficient leave balance. Available: {leave_balance.available_days} days, Requested: {total_days} days"
            )
        
        # Check for overlapping leave requests
        overlapping_requests = self.get_overlapping_requests(db, employee.id, start_date, end_date)
        if overlapping_requests:
            violations.append("Overlapping leave request exists")
        
        # Generate suggestions
        if violations:
            suggestions.append("Consider adjusting leave dates or duration")
            if leave_balance:
                suggestions.append(f"Available balance: {leave_balance.available_days} days")
        
        return LeavePolicyValidation(
            is_valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            suggestions=suggestions,
            max_allowed_days=leave_type.max_consecutive_days,
            available_balance=leave_balance.available_days if leave_balance else None,
            advance_notice_requirement=leave_type.min_advance_notice_days
        )
    
    def create_leave_request(self, db: Session, employee: Employee, 
                           leave_data: LeaveRequestCreate) -> Tuple[bool, LeaveRequest, List[str]]:
        """
        Create a new leave request
        
        Args:
            db: Database session
            employee: Employee creating the request
            leave_data: Leave request data
            
        Returns:
            Tuple[bool, LeaveRequest, List[str]]: (success, leave_request, errors)
        """
        try:
            # Calculate total days
            total_days = self.calculate_leave_days(
                leave_data.start_date, 
                leave_data.end_date
            )
            
            if leave_data.is_half_day:
                total_days = 0.5
            
            # Validate leave policy
            validation = self.validate_leave_policy(
                db, employee, leave_data.leave_type_id,
                leave_data.start_date, leave_data.end_date, total_days
            )
            
            if not validation.is_valid:
                return False, None, validation.violations
            
            # Get leave type to determine approval requirements
            leave_type = db.query(LeaveType).filter(LeaveType.id == leave_data.leave_type_id).first()
            
            # Create leave request
            leave_request = LeaveRequest(
                request_id=self.generate_request_id(),
                employee_id=employee.id,
                leave_type_id=leave_data.leave_type_id,
                start_date=leave_data.start_date,
                end_date=leave_data.end_date,
                total_days=total_days,
                reason=leave_data.reason,
                emergency_contact=leave_data.emergency_contact,
                emergency_phone=leave_data.emergency_phone,
                priority=leave_data.priority,
                is_half_day=leave_data.is_half_day,
                half_day_session=leave_data.half_day_session,
                work_handover=leave_data.work_handover,
                backup_contact_id=leave_data.backup_contact_id,
                manager_id=employee.manager_id,
                hr_approval_required=leave_type.requires_hr_approval,
                status=LeaveStatus.PENDING,
                created_by=employee.id
            )
            
            db.add(leave_request)
            db.commit()
            db.refresh(leave_request)
            
            # Update leave balance (mark as pending)
            self.update_leave_balance_pending(db, employee.id, leave_data.leave_type_id, 
                                            leave_data.start_date.year, total_days, add=True)
            
            logger.info(f"Leave request created: {leave_request.request_id} for employee {employee.employee_id}")
            
            return True, leave_request, []
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating leave request: {e}")
            return False, None, [f"Error creating leave request: {str(e)}"]
    
    def update_leave_request(self, db: Session, leave_request: LeaveRequest, 
                           update_data: LeaveRequestUpdate, 
                           current_user: Employee) -> Tuple[bool, List[str]]:
        """
        Update an existing leave request
        
        Args:
            db: Database session
            leave_request: Leave request to update
            update_data: Update data
            current_user: User making the update
            
        Returns:
            Tuple[bool, List[str]]: (success, errors)
        """
        try:
            # Check if request can be modified
            if not leave_request.can_be_modified():
                return False, ["Leave request cannot be modified in current status"]
            
            # Check permissions
            if leave_request.employee_id != current_user.id and not current_user.is_manager:
                return False, ["Insufficient permissions to modify this leave request"]
            
            # Store original values for balance adjustment
            original_days = float(leave_request.total_days)
            original_year = leave_request.start_date.year
            
            # Update fields
            update_dict = update_data.dict(exclude_unset=True)
            
            for field, value in update_dict.items():
                if hasattr(leave_request, field):
                    setattr(leave_request, field, value)
            
            # Recalculate total days if dates changed
            if 'start_date' in update_dict or 'end_date' in update_dict or 'is_half_day' in update_dict:
                if leave_request.is_half_day:
                    leave_request.total_days = 0.5
                else:
                    leave_request.total_days = self.calculate_leave_days(
                        leave_request.start_date, leave_request.end_date
                    )
                
                # Validate updated request
                validation = self.validate_leave_policy(
                    db, leave_request.employee, leave_request.leave_type_id,
                    leave_request.start_date, leave_request.end_date, 
                    float(leave_request.total_days)
                )
                
                if not validation.is_valid:
                    return False, validation.violations
            
            leave_request.updated_at = datetime.utcnow()
            db.commit()
            
            # Update leave balance if days changed
            new_days = float(leave_request.total_days)
            if original_days != new_days:
                # Remove original pending days
                self.update_leave_balance_pending(
                    db, leave_request.employee_id, leave_request.leave_type_id,
                    original_year, original_days, add=False
                )
                
                # Add new pending days
                self.update_leave_balance_pending(
                    db, leave_request.employee_id, leave_request.leave_type_id,
                    leave_request.start_date.year, new_days, add=True
                )
            
            logger.info(f"Leave request updated: {leave_request.request_id}")
            return True, []
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating leave request: {e}")
            return False, [f"Error updating leave request: {str(e)}"]
    
    def approve_leave_request(self, db: Session, leave_request: LeaveRequest, 
                            approver: Employee, comments: str = None) -> Tuple[bool, List[str]]:
        """
        Approve a leave request
        
        Args:
            db: Database session
            leave_request: Leave request to approve
            approver: Employee approving the request
            comments: Approval comments
            
        Returns:
            Tuple[bool, List[str]]: (success, errors)
        """
        try:
            if leave_request.status != LeaveStatus.PENDING:
                return False, ["Only pending requests can be approved"]
            
            # Check approval permissions
            can_approve = False
            
            # Manager approval
            if leave_request.manager_id == approver.id and not leave_request.manager_approval_date:
                leave_request.manager_approval_date = datetime.utcnow()
                leave_request.manager_comments = comments
                can_approve = True
            
            # HR approval
            elif leave_request.hr_approval_required and approver.role.title.lower() in ['hr', 'human resources']:
                leave_request.hr_approver_id = approver.id
                leave_request.hr_approval_date = datetime.utcnow()
                leave_request.hr_comments = comments
                can_approve = True
            
            # Admin can approve anything
            elif approver.role.title.lower() in ['admin', 'administrator']:
                if not leave_request.manager_approval_date:
                    leave_request.manager_approval_date = datetime.utcnow()
                    leave_request.manager_comments = comments or "Approved by admin"
                if leave_request.hr_approval_required and not leave_request.hr_approval_date:
                    leave_request.hr_approver_id = approver.id
                    leave_request.hr_approval_date = datetime.utcnow()
                    leave_request.hr_comments = comments or "Approved by admin"
                can_approve = True
            
            if not can_approve:
                return False, ["Insufficient permissions to approve this request"]
            
            # Check if all required approvals are complete
            manager_approved = leave_request.manager_approval_date is not None
            hr_approved = (not leave_request.hr_approval_required or 
                          leave_request.hr_approval_date is not None)
            
            if manager_approved and hr_approved:
                leave_request.status = LeaveStatus.APPROVED
                leave_request.approved_date = datetime.utcnow()
                
                # Update leave balance (move from pending to used)
                self.update_leave_balance_pending(
                    db, leave_request.employee_id, leave_request.leave_type_id,
                    leave_request.start_date.year, float(leave_request.total_days), add=False
                )
                
                self.update_leave_balance_used(
                    db, leave_request.employee_id, leave_request.leave_type_id,
                    leave_request.start_date.year, float(leave_request.total_days), add=True
                )
            
            db.commit()
            logger.info(f"Leave request approved: {leave_request.request_id} by {approver.employee_id}")
            
            return True, []
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error approving leave request: {e}")
            return False, [f"Error approving leave request: {str(e)}"]
    
    def reject_leave_request(self, db: Session, leave_request: LeaveRequest,
                           approver: Employee, comments: str) -> Tuple[bool, List[str]]:
        """
        Reject a leave request
        
        Args:
            db: Database session
            leave_request: Leave request to reject
            approver: Employee rejecting the request
            comments: Rejection reason
            
        Returns:
            Tuple[bool, List[str]]: (success, errors)
        """
        try:
            if leave_request.status != LeaveStatus.PENDING:
                return False, ["Only pending requests can be rejected"]
            
            # Update status
            leave_request.status = LeaveStatus.REJECTED
            leave_request.rejected_date = datetime.utcnow()
            
            # Add rejection comments
            if leave_request.manager_id == approver.id:
                leave_request.manager_comments = comments
            elif approver.role.title.lower() in ['hr', 'human resources']:
                leave_request.hr_comments = comments
            
            # Remove pending days from balance
            self.update_leave_balance_pending(
                db, leave_request.employee_id, leave_request.leave_type_id,
                leave_request.start_date.year, float(leave_request.total_days), add=False
            )
            
            db.commit()
            logger.info(f"Leave request rejected: {leave_request.request_id} by {approver.employee_id}")
            
            return True, []
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error rejecting leave request: {e}")
            return False, [f"Error rejecting leave request: {str(e)}"]
    
    def cancel_leave_request(self, db: Session, leave_request: LeaveRequest,
                           user: Employee, reason: str) -> Tuple[bool, List[str]]:
        """
        Cancel a leave request
        
        Args:
            db: Database session
            leave_request: Leave request to cancel
            user: User cancelling the request
            reason: Cancellation reason
            
        Returns:
            Tuple[bool, List[str]]: (success, errors)
        """
        try:
            if not leave_request.can_be_cancelled():
                return False, ["Leave request cannot be cancelled"]
            
            # Check permissions
            if leave_request.employee_id != user.id and not user.is_manager:
                return False, ["Insufficient permissions to cancel this request"]
            
            original_status = leave_request.status
            leave_request.status = LeaveStatus.CANCELLED
            leave_request.cancellation_reason = reason
            leave_request.updated_at = datetime.utcnow()
            
            # Update leave balance based on original status
            if original_status == LeaveStatus.PENDING:
                # Remove pending days
                self.update_leave_balance_pending(
                    db, leave_request.employee_id, leave_request.leave_type_id,
                    leave_request.start_date.year, float(leave_request.total_days), add=False
                )
            elif original_status == LeaveStatus.APPROVED:
                # Restore used days back to available
                self.update_leave_balance_used(
                    db, leave_request.employee_id, leave_request.leave_type_id,
                    leave_request.start_date.year, float(leave_request.total_days), add=False
                )
            
            db.commit()
            logger.info(f"Leave request cancelled: {leave_request.request_id}")
            
            return True, []
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error cancelling leave request: {e}")
            return False, [f"Error cancelling leave request: {str(e)}"]
    
    def get_leave_balance(self, db: Session, employee_id: int, 
                         leave_type_id: int, year: int) -> Optional[LeaveBalance]:
        """
        Get leave balance for employee, leave type, and year
        
        Args:
            db: Database session
            employee_id: Employee ID
            leave_type_id: Leave type ID
            year: Year
            
        Returns:
            Optional[LeaveBalance]: Leave balance or None if not found
        """
        return db.query(LeaveBalance).filter(
            and_(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.leave_type_id == leave_type_id,
                LeaveBalance.year == year
            )
        ).first()
    
    def update_leave_balance_pending(self, db: Session, employee_id: int,
                                   leave_type_id: int, year: int,
                                   days: float, add: bool = True):
        """
        Update pending days in leave balance
        
        Args:
            db: Database session
            employee_id: Employee ID
            leave_type_id: Leave type ID
            year: Year
            days: Number of days to add/subtract
            add: True to add days, False to subtract
        """
        balance = self.get_leave_balance(db, employee_id, leave_type_id, year)
        if balance:
            if add:
                balance.pending_days += days
            else:
                balance.pending_days = max(0, balance.pending_days - days)
            
            balance.updated_at = datetime.utcnow()
            db.commit()
    
    def update_leave_balance_used(self, db: Session, employee_id: int,
                                leave_type_id: int, year: int,
                                days: float, add: bool = True):
        """
        Update used days in leave balance
        
        Args:
            db: Database session
            employee_id: Employee ID
            leave_type_id: Leave type ID
            year: Year
            days: Number of days to add/subtract
            add: True to add days, False to subtract
        """
        balance = self.get_leave_balance(db, employee_id, leave_type_id, year)
        if balance:
            if add:
                balance.used_days += days
            else:
                balance.used_days = max(0, balance.used_days - days)
            
            balance.updated_at = datetime.utcnow()
            db.commit()
    
    def get_leave_usage_for_year(self, db: Session, employee_id: int,
                               leave_type_id: int, year: int) -> float:
        """
        Get total leave usage for employee, leave type, and year
        
        Args:
            db: Database session
            employee_id: Employee ID
            leave_type_id: Leave type ID
            year: Year
            
        Returns:
            float: Total days used
        """
        result = db.query(func.sum(LeaveRequest.total_days)).filter(
            and_(
                LeaveRequest.employee_id == employee_id,
                LeaveRequest.leave_type_id == leave_type_id,
                LeaveRequest.status == LeaveStatus.APPROVED,
                extract('year', LeaveRequest.start_date) == year
            )
        ).scalar()
        
        return float(result) if result else 0.0
    
    def get_overlapping_requests(self, db: Session, employee_id: int,
                               start_date: date, end_date: date,
                               exclude_request_id: int = None) -> List[LeaveRequest]:
        """
        Get overlapping leave requests for an employee
        
        Args:
            db: Database session
            employee_id: Employee ID
            start_date: Start date to check
            end_date: End date to check
            exclude_request_id: Request ID to exclude from check
            
        Returns:
            List[LeaveRequest]: Overlapping requests
        """
        query = db.query(LeaveRequest).filter(
            and_(
                LeaveRequest.employee_id == employee_id,
                LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED]),
                or_(
                    and_(LeaveRequest.start_date <= start_date, LeaveRequest.end_date >= start_date),
                    and_(LeaveRequest.start_date <= end_date, LeaveRequest.end_date >= end_date),
                    and_(LeaveRequest.start_date >= start_date, LeaveRequest.end_date <= end_date)
                )
            )
        )
        
        if exclude_request_id:
            query = query.filter(LeaveRequest.id != exclude_request_id)
        
        return query.all()

# Global leave service instance
leave_service = LeaveService()
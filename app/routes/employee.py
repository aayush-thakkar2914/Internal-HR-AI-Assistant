"""
Employee management API routes for the HR AI Assistant.

This module contains all employee-related endpoints including profile management,
department and role management, and employee directory operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Dict, Any, Optional

from app.config.database import get_db
from app.models.employee import Employee, Department, Role, EmploymentStatus
from app.schemas.employee import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeList,
    EmployeeSearchParams, EmployeeStatistics, EmployeeProfileSummary,
    DepartmentCreate, DepartmentUpdate, DepartmentResponse,
    RoleCreate, RoleUpdate, RoleResponse
)
from app.services.auth_service import auth_service
from app.middleware.auth import get_current_active_user, require_role, require_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Employee Management Routes

@router.get("/", response_model=List[EmployeeList])
async def get_employees(
    search_params: EmployeeSearchParams = Depends(),
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get employees with search and filtering
    
    Args:
        search_params: Search and filter parameters
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[EmployeeList]: List of employees
    """
    try:
        query = db.query(Employee).join(Department, Employee.department_id == Department.id)\
                                  .join(Role, Employee.role_id == Role.id)
        
        # Apply search filter
        if search_params.search:
            search_term = f"%{search_params.search}%"
            query = query.filter(
                or_(
                    Employee.first_name.ilike(search_term),
                    Employee.last_name.ilike(search_term),
                    Employee.email.ilike(search_term),
                    Employee.employee_id.ilike(search_term),
                    Department.name.ilike(search_term),
                    Role.title.ilike(search_term)
                )
            )
        
        # Apply filters
        if search_params.department_id:
            query = query.filter(Employee.department_id == search_params.department_id)
        
        if search_params.role_id:
            query = query.filter(Employee.role_id == search_params.role_id)
        
        if search_params.employment_status:
            query = query.filter(Employee.employment_status == search_params.employment_status)
        
        if search_params.employment_type:
            query = query.filter(Employee.employment_type == search_params.employment_type)
        
        if search_params.is_active is not None:
            query = query.filter(Employee.is_active == search_params.is_active)
        
        if search_params.manager_id:
            query = query.filter(Employee.manager_id == search_params.manager_id)
        
        if search_params.hire_date_from:
            query = query.filter(Employee.hire_date >= search_params.hire_date_from)
        
        if search_params.hire_date_to:
            query = query.filter(Employee.hire_date <= search_params.hire_date_to)
        
        # Apply sorting
        if search_params.sort_by == "full_name":
            if search_params.sort_order == "desc":
                query = query.order_by(Employee.first_name.desc(), Employee.last_name.desc())
            else:
                query = query.order_by(Employee.first_name.asc(), Employee.last_name.asc())
        elif search_params.sort_by == "email":
            if search_params.sort_order == "desc":
                query = query.order_by(Employee.email.desc())
            else:
                query = query.order_by(Employee.email.asc())
        elif search_params.sort_by == "hire_date":
            if search_params.sort_order == "desc":
                query = query.order_by(Employee.hire_date.desc())
            else:
                query = query.order_by(Employee.hire_date.asc())
        elif search_params.sort_by == "department_name":
            if search_params.sort_order == "desc":
                query = query.order_by(Department.name.desc())
            else:
                query = query.order_by(Department.name.asc())
        elif search_params.sort_by == "role_title":
            if search_params.sort_order == "desc":
                query = query.order_by(Role.title.desc())
            else:
                query = query.order_by(Role.title.asc())
        
        # Apply pagination
        employees = query.offset(search_params.skip).limit(search_params.limit).all()
        
        return [EmployeeList.from_orm(employee) for employee in employees]
        
    except Exception as e:
        logger.error(f"Error retrieving employees: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve employees"
        )

@router.get("/me", response_model=EmployeeResponse)
async def get_my_profile(
    current_user: Employee = Depends(get_current_active_user)
):
    """
    Get current user's profile
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        EmployeeResponse: User's profile information
    """
    return EmployeeResponse.from_orm(current_user)

@router.get("/me/summary", response_model=EmployeeProfileSummary)
async def get_my_profile_summary(
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive profile summary for current user
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        EmployeeProfileSummary: Comprehensive profile summary
    """
    try:
        # Get leave balance summary
        from app.models.leave import LeaveBalance, LeaveRequest
        
        leave_balances = db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == current_user.id,
            LeaveBalance.year == 2024  # Current year
        ).all()
        
        leave_balance_summary = {
            "total_allocated": sum(float(lb.allocated_days) for lb in leave_balances),
            "total_used": sum(float(lb.used_days) for lb in leave_balances),
            "total_available": sum(lb.available_days for lb in leave_balances),
            "balances_by_type": [
                {
                    "leave_type": lb.leave_type.name if lb.leave_type else "Unknown",
                    "allocated": float(lb.allocated_days),
                    "used": float(lb.used_days),
                    "available": lb.available_days
                }
                for lb in leave_balances
            ]
        }
        
        # Get recent leave requests
        recent_leave_requests = db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == current_user.id
        ).order_by(LeaveRequest.created_at.desc()).limit(5).all()
        
        # Get pending document requests
        from app.models.document import DocumentRequest
        pending_document_requests = db.query(DocumentRequest).filter(
            and_(
                DocumentRequest.employee_id == current_user.id,
                DocumentRequest.status.in_(["pending", "processing"])
            )
        ).all()
        
        # Get recent queries
        from app.models.query import QueryLog
        recent_queries = db.query(QueryLog).filter(
            QueryLog.employee_id == current_user.id
        ).order_by(QueryLog.query_timestamp.desc()).limit(5).all()
        
        return EmployeeProfileSummary(
            employee_info=EmployeeResponse.from_orm(current_user),
            leave_balance_summary=leave_balance_summary,
            recent_leave_requests=[lr.to_dict() for lr in recent_leave_requests],
            pending_document_requests=[dr.to_dict() for dr in pending_document_requests],
            recent_queries=[q.to_dict() for q in recent_queries]
        )
        
    except Exception as e:
        logger.error(f"Error retrieving profile summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile summary"
        )

@router.put("/me", response_model=EmployeeResponse)
async def update_my_profile(
    employee_update: EmployeeUpdate,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile
    
    Args:
        employee_update: Employee update data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        EmployeeResponse: Updated employee information
    """
    try:
        # Validate email if being updated
        if employee_update.email:
            is_valid_email, normalized_email = auth_service.validate_email_format(employee_update.email)
            if not is_valid_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid email format"
                )
            
            # Check if email is available (excluding current user)
            if not auth_service.is_email_available(db, normalized_email, current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            employee_update.email = normalized_email
        
        # Update allowed fields
        update_data = employee_update.dict(exclude_unset=True)
        
        # Remove fields that shouldn't be updated by user
        restricted_fields = ['department_id', 'role_id', 'manager_id', 'employment_status', 'salary']
        for field in restricted_fields:
            update_data.pop(field, None)
        
        for field, value in update_data.items():
            if hasattr(current_user, field):
                setattr(current_user, field, value)
        
        current_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"Profile updated for user: {current_user.employee_id}")
        
        return EmployeeResponse.from_orm(current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: str,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get employee by ID
    
    Args:
        employee_id: Employee ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        EmployeeResponse: Employee information
    """
    try:
        employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        return EmployeeResponse.from_orm(employee)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving employee: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve employee"
        )

@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: str,
    employee_update: EmployeeUpdate,
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Update employee (HR only)
    
    Args:
        employee_id: Employee ID
        employee_update: Employee update data
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        EmployeeResponse: Updated employee information
    """
    try:
        employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        # Validate email if being updated
        if employee_update.email:
            is_valid_email, normalized_email = auth_service.validate_email_format(employee_update.email)
            if not is_valid_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid email format"
                )
            
            # Check if email is available (excluding current employee)
            if not auth_service.is_email_available(db, normalized_email, employee.id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            employee_update.email = normalized_email
        
        # Update fields
        update_data = employee_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(employee, field):
                setattr(employee, field, value)
        
        employee.updated_at = datetime.utcnow()
        employee.updated_by = current_user.id
        
        db.commit()
        db.refresh(employee)
        
        logger.info(f"Employee updated: {employee.employee_id} by {current_user.employee_id}")
        
        return EmployeeResponse.from_orm(employee)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating employee: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update employee"
        )

@router.get("/statistics/overview", response_model=EmployeeStatistics)
async def get_employee_statistics(
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Get employee statistics overview (HR only)
    
    Args:
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        EmployeeStatistics: Employee statistics
    """
    try:
        from datetime import date, timedelta
        
        # Basic counts
        total_employees = db.query(Employee).count()
        active_employees = db.query(Employee).filter(Employee.is_active == True).count()
        inactive_employees = total_employees - active_employees
        
        # This month's hires and terminations
        this_month_start = date.today().replace(day=1)
        
        new_hires_this_month = db.query(Employee).filter(
            Employee.hire_date >= this_month_start
        ).count()
        
        terminations_this_month = db.query(Employee).filter(
            and_(
                Employee.termination_date >= this_month_start,
                Employee.termination_date.isnot(None)
            )
        ).count()
        
        # Average tenure
        avg_tenure_result = db.query(
            func.avg(func.julianday('now') - func.julianday(Employee.hire_date)) / 365.25
        ).filter(Employee.is_active == True).scalar()
        
        average_tenure_years = float(avg_tenure_result) if avg_tenure_result else 0
        
        # Department breakdown
        dept_breakdown = db.query(
            Department.name,
            func.count(Employee.id).label('count')
        ).join(Employee, Employee.department_id == Department.id)\
         .group_by(Department.name).all()
        
        department_breakdown = {dept: count for dept, count in dept_breakdown}
        
        # Role breakdown
        role_breakdown = db.query(
            Role.title,
            func.count(Employee.id).label('count')
        ).join(Employee, Employee.role_id == Role.id)\
         .group_by(Role.title).all()
        
        role_breakdown_dict = {role: count for role, count in role_breakdown}
        
        # Employment type breakdown
        emp_type_breakdown = db.query(
            Employee.employment_type,
            func.count(Employee.id).label('count')
        ).group_by(Employee.employment_type).all()
        
        employment_type_breakdown = {emp_type: count for emp_type, count in emp_type_breakdown}
        
        # Age group breakdown (simplified)
        age_group_breakdown = {
            "20-30": 0,
            "31-40": 0,
            "41-50": 0,
            "51-60": 0,
            "60+": 0
        }
        
        return EmployeeStatistics(
            total_employees=total_employees,
            active_employees=active_employees,
            inactive_employees=inactive_employees,
            new_hires_this_month=new_hires_this_month,
            terminations_this_month=terminations_this_month,
            average_tenure_years=average_tenure_years,
            department_breakdown=department_breakdown,
            role_breakdown=role_breakdown_dict,
            employment_type_breakdown=employment_type_breakdown,
            age_group_breakdown=age_group_breakdown
        )
        
    except Exception as e:
        logger.error(f"Error retrieving employee statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )

# Department Management Routes

@router.get("/departments/", response_model=List[DepartmentResponse])
async def get_departments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all departments
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[DepartmentResponse]: List of departments
    """
    try:
        departments = db.query(Department).offset(skip).limit(limit).all()
        return [DepartmentResponse.from_orm(dept) for dept in departments]
        
    except Exception as e:
        logger.error(f"Error retrieving departments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve departments"
        )

@router.post("/departments/", response_model=DepartmentResponse)
async def create_department(
    department_data: DepartmentCreate,
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Create new department (HR only)
    
    Args:
        department_data: Department creation data
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        DepartmentResponse: Created department
    """
    try:
        # Check if department code is unique
        existing_dept = db.query(Department).filter(
            Department.department_code == department_data.department_code
        ).first()
        
        if existing_dept:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department code already exists"
            )
        
        department = Department(**department_data.dict())
        
        db.add(department)
        db.commit()
        db.refresh(department)
        
        logger.info(f"Department created: {department.name} by {current_user.employee_id}")
        
        return DepartmentResponse.from_orm(department)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create department"
        )

# Role Management Routes

@router.get("/roles/", response_model=List[RoleResponse])
async def get_roles(
    department_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all roles with optional department filtering
    
    Args:
        department_id: Filter by department ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[RoleResponse]: List of roles
    """
    try:
        query = db.query(Role)
        
        if department_id:
            query = query.filter(Role.department_id == department_id)
        
        roles = query.offset(skip).limit(limit).all()
        return [RoleResponse.from_orm(role) for role in roles]
        
    except Exception as e:
        logger.error(f"Error retrieving roles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve roles"
        )

@router.post("/roles/", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Create new role (HR only)
    
    Args:
        role_data: Role creation data
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        RoleResponse: Created role
    """
    try:
        # Check if role code is unique
        existing_role = db.query(Role).filter(
            Role.role_code == role_data.role_code
        ).first()
        
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role code already exists"
            )
        
        # Verify department exists
        department = db.query(Department).filter(
            Department.id == role_data.department_id
        ).first()
        
        if not department:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department not found"
            )
        
        role = Role(**role_data.dict())
        
        db.add(role)
        db.commit()
        db.refresh(role)
        
        logger.info(f"Role created: {role.title} by {current_user.employee_id}")
        
        return RoleResponse.from_orm(role)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create role"
        )

@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_update: RoleUpdate,
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Update role (HR only)
    
    Args:
        role_id: Role ID
        role_update: Role update data
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        RoleResponse: Updated role
    """
    try:
        role = db.query(Role).filter(Role.id == role_id).first()
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Update fields
        update_data = role_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(role, field):
                setattr(role, field, value)
        
        role.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(role)
        
        logger.info(f"Role updated: {role.title} by {current_user.employee_id}")
        
        return RoleResponse.from_orm(role)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update role"
        )

@router.get("/managers", response_model=List[EmployeeList])
async def get_managers(
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all employees who are managers
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[EmployeeList]: List of managers
    """
    try:
        # Get employees who have subordinates
        managers = db.query(Employee).filter(
            Employee.id.in_(
                db.query(Employee.manager_id).filter(Employee.manager_id.isnot(None)).distinct()
            )
        ).all()
        
        return [EmployeeList.from_orm(manager) for manager in managers]
        
    except Exception as e:
        logger.error(f"Error retrieving managers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve managers"
        )

@router.get("/my-team", response_model=List[EmployeeList])
async def get_my_team(
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's team members (if user is a manager)
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[EmployeeList]: List of team members
    """
    try:
        if not current_user.is_manager:
            return []
        
        team_members = db.query(Employee).filter(
            Employee.manager_id == current_user.id,
            Employee.is_active == True
        ).all()
        
        return [EmployeeList.from_orm(member) for member in team_members]
        
    except Exception as e:
        logger.error(f"Error retrieving team members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team members"
        )
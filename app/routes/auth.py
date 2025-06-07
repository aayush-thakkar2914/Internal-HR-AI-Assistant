"""
Authentication API routes for the HR AI Assistant.

This module contains all authentication-related endpoints including
login, registration, password management, and session handling.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.config.database import get_db
from app.models.employee import Employee
from app.schemas.employee import EmployeeLogin, PasswordChange, PasswordReset, EmployeeCreate, EmployeeResponse
from app.services.auth_service import auth_service
from app.services.notification_service import notification_service
from app.middleware.auth import get_current_user, get_current_active_user
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
security = HTTPBearer()

@router.post("/login", response_model=Dict[str, Any])
async def login(
    login_data: EmployeeLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return access token
    
    Args:
        login_data: Login credentials
        request: HTTP request object
        db: Database session
        
    Returns:
        Dict: Authentication tokens and user information
    """
    try:
        # Authenticate user
        user = auth_service.authenticate_user(
            db, login_data.username, login_data.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if account is locked
        if auth_service.is_account_locked(login_data.username):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to too many failed login attempts"
            )
        
        # Generate tokens
        token_data = auth_service.create_user_tokens(user)
        
        logger.info(f"User login successful: {user.username} from {request.client.host}")
        
        return {
            "message": "Login successful",
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
            "token_type": token_data["token_type"],
            "expires_in": token_data["expires_in"],
            "user": token_data["user"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )

@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    Args:
        refresh_token: Refresh token string
        db: Database session
        
    Returns:
        Dict: New access token information
    """
    try:
        token_data = auth_service.refresh_access_token(refresh_token)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        return {
            "message": "Token refreshed successfully",
            **token_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during token refresh"
        )

@router.post("/logout")
async def logout(
    session_id: str = None,
    current_user: Employee = Depends(get_current_active_user)
):
    """
    Logout user by invalidating session
    
    Args:
        session_id: Session ID to invalidate
        current_user: Current authenticated user
        
    Returns:
        Dict: Logout confirmation
    """
    try:
        if session_id:
            auth_service.logout_user(session_id)
        
        logger.info(f"User logout: {current_user.username}")
        
        return {"message": "Logout successful"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during logout"
        )

@router.post("/register", response_model=EmployeeResponse)
async def register(
    employee_data: EmployeeCreate,
    db: Session = Depends(get_db)
):
    """
    Register new employee (Admin only)
    
    Args:
        employee_data: Employee registration data
        db: Database session
        
    Returns:
        EmployeeResponse: Created employee information
    """
    try:
        # Validate email format
        is_valid_email, normalized_email = auth_service.validate_email_format(employee_data.email)
        if not is_valid_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        # Check if username is available
        if not auth_service.is_username_available(db, employee_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Check if email is available
        if not auth_service.is_email_available(db, normalized_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Validate password strength
        is_valid_password, password_errors = auth_service.validate_password_strength(employee_data.password)
        if not is_valid_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password validation failed: {', '.join(password_errors)}"
            )
        
        # Create employee
        employee = Employee(
            employee_id=employee_data.employee_id,
            email=normalized_email,
            username=employee_data.username,
            first_name=employee_data.first_name,
            last_name=employee_data.last_name,
            middle_name=employee_data.middle_name,
            date_of_birth=employee_data.date_of_birth,
            gender=employee_data.gender,
            phone_number=employee_data.phone_number,
            emergency_contact_name=employee_data.emergency_contact_name,
            emergency_contact_phone=employee_data.emergency_contact_phone,
            address_line1=employee_data.address_line1,
            address_line2=employee_data.address_line2,
            city=employee_data.city,
            state=employee_data.state,
            postal_code=employee_data.postal_code,
            country=employee_data.country,
            department_id=employee_data.department_id,
            role_id=employee_data.role_id,
            manager_id=employee_data.manager_id,
            hire_date=employee_data.hire_date,
            employment_status=employee_data.employment_status,
            employment_type=employee_data.employment_type,
            salary=employee_data.salary,
            currency=employee_data.currency,
            pay_frequency=employee_data.pay_frequency,
            bio=employee_data.bio,
            skills=employee_data.skills,
            certifications=employee_data.certifications
        )
        
        # Set password
        employee.set_password(employee_data.password)
        
        db.add(employee)
        db.commit()
        db.refresh(employee)
        
        logger.info(f"New employee registered: {employee.employee_id}")
        
        return EmployeeResponse.from_orm(employee)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration"
        )

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change user password
    
    Args:
        password_data: Password change data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dict: Password change confirmation
    """
    try:
        success, errors = auth_service.change_password(
            db, current_user, password_data.current_password, password_data.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password change failed: {', '.join(errors)}"
            )
        
        logger.info(f"Password changed for user: {current_user.username}")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while changing password"
        )

@router.post("/forgot-password")
async def forgot_password(
    email: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Request password reset
    
    Args:
        email: User email address
        request: HTTP request object
        db: Database session
        
    Returns:
        Dict: Password reset request confirmation
    """
    try:
        # Find user by email
        user = db.query(Employee).filter(Employee.email == email).first()
        
        if not user:
            # Don't reveal if email exists or not for security
            return {"message": "If the email exists, a password reset link has been sent"}
        
        # Generate reset token
        reset_token = auth_service.generate_reset_token(email)
        
        # Create reset link (this would be your actual frontend URL)
        reset_link = f"{request.base_url}auth/reset-password?token={reset_token}"
        
        # Send reset email
        notification_service.send_password_reset_email(user, reset_token, reset_link)
        
        logger.info(f"Password reset requested for: {email}")
        
        return {"message": "If the email exists, a password reset link has been sent"}
        
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing password reset request"
        )

@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    Reset password using reset token
    
    Args:
        reset_data: Password reset data
        db: Database session
        
    Returns:
        Dict: Password reset confirmation
    """
    try:
        success, errors = auth_service.reset_password(
            db, reset_data.reset_token, reset_data.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password reset failed: {', '.join(errors)}"
            )
        
        logger.info("Password reset completed successfully")
        
        return {"message": "Password reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting password"
        )

@router.get("/me", response_model=EmployeeResponse)
async def get_current_user_info(
    current_user: Employee = Depends(get_current_active_user)
):
    """
    Get current user information
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        EmployeeResponse: Current user information
    """
    return EmployeeResponse.from_orm(current_user)

@router.get("/verify-token")
async def verify_token(
    current_user: Employee = Depends(get_current_user)
):
    """
    Verify if current token is valid
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Dict: Token validation result
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username,
        "is_active": current_user.is_active
    }
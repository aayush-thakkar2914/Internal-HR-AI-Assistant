"""
Authentication service for the HR AI Assistant.

This service handles user authentication, password management,
session management, and security-related operations.
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from passlib.context import CryptContext
from email_validator import validate_email, EmailNotValidError

from app.models.employee import Employee, EmploymentStatus
from app.middleware.auth import create_access_token, verify_token
from app.utils.logger import get_logger
from app.schemas.employee import EmployeeCreate, EmployeeLogin

logger = get_logger(__name__)

class AuthService:
    """Authentication service for user management and security"""
    
    def __init__(self):
        # Password hashing configuration
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Token configuration
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        
        # Password reset configuration
        self.reset_token_expire_hours = int(os.getenv("RESET_TOKEN_EXPIRE_HOURS", "1"))
        
        # Account lockout configuration
        self.max_login_attempts = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        self.lockout_duration_minutes = int(os.getenv("LOCKOUT_DURATION_MINUTES", "30"))
        
        # In-memory storage for failed attempts and reset tokens
        # In production, use Redis or database
        self.failed_attempts = {}
        self.reset_tokens = {}
        self.active_sessions = {}
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def validate_password_strength(self, password: str) -> Tuple[bool, list]:
        """
        Validate password strength according to security policies
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple[bool, list]: (is_valid, list_of_errors)
        """
        errors = []
        
        # Minimum length
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        # Maximum length
        if len(password) > 128:
            errors.append("Password must be less than 128 characters long")
        
        # Character requirements
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        # Common password check (basic)
        common_passwords = ["password", "123456", "password123", "admin", "qwerty"]
        if password.lower() in common_passwords:
            errors.append("Password is too common")
        
        return len(errors) == 0, errors
    
    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[Employee]:
        """
        Authenticate user with username and password
        
        Args:
            db: Database session
            username: Username or email
            password: Plain text password
            
        Returns:
            Optional[Employee]: Employee object if authentication successful, None otherwise
        """
        # Check if account is locked
        if self.is_account_locked(username):
            logger.warning(f"Login attempt on locked account: {username}")
            return None
        
        # Find user by username or email
        user = db.query(Employee).filter(
            and_(
                (Employee.username == username) | (Employee.email == username),
                Employee.is_active == True,
                Employee.employment_status == EmploymentStatus.ACTIVE
            )
        ).first()
        
        if not user:
            self.record_failed_attempt(username)
            logger.warning(f"Login attempt with invalid username: {username}")
            return None
        
        # Verify password
        if not self.verify_password(password, user.password_hash):
            self.record_failed_attempt(username)
            logger.warning(f"Login attempt with invalid password for user: {username}")
            return None
        
        # Clear failed attempts on successful login
        self.clear_failed_attempts(username)
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        logger.info(f"Successful login for user: {username}")
        return user
    
    def create_user_tokens(self, user: Employee) -> Dict[str, Any]:
        """
        Create access and refresh tokens for user
        
        Args:
            user: Employee object
            
        Returns:
            Dict: Token information
        """
        # Create access token
        access_token_data = {
            "sub": str(user.id),
            "username": user.username,
            "employee_id": user.employee_id,
            "email": user.email,
            "role": user.role.title if user.role else None,
            "department": user.department.name if user.department else None
        }
        
        access_token = create_access_token(
            data=access_token_data,
            expires_delta=timedelta(minutes=self.access_token_expire_minutes)
        )
        
        # Create refresh token
        refresh_token_data = {
            "sub": str(user.id),
            "type": "refresh"
        }
        
        refresh_token = create_access_token(
            data=refresh_token_data,
            expires_delta=timedelta(days=self.refresh_token_expire_days)
        )
        
        # Store session information
        session_id = secrets.token_urlsafe(32)
        self.active_sessions[session_id] = {
            "user_id": user.id,
            "username": user.username,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "access_token": access_token
        }
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
            "session_id": session_id,
            "user": {
                "id": user.id,
                "username": user.username,
                "employee_id": user.employee_id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.title if user.role else None,
                "department": user.department.name if user.department else None
            }
        }
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token string
            
        Returns:
            Optional[Dict]: New token information or None if invalid
        """
        # Verify refresh token
        payload = verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Create new access token
        access_token_data = {
            "sub": user_id,
            "type": "access"
        }
        
        access_token = create_access_token(
            data=access_token_data,
            expires_delta=timedelta(minutes=self.access_token_expire_minutes)
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60
        }
    
    def logout_user(self, session_id: str) -> bool:
        """
        Logout user by invalidating session
        
        Args:
            session_id: Session ID to invalidate
            
        Returns:
            bool: True if logout successful, False otherwise
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"User logged out, session: {session_id}")
            return True
        return False
    
    def change_password(self, db: Session, user: Employee, current_password: str, new_password: str) -> Tuple[bool, list]:
        """
        Change user password
        
        Args:
            db: Database session
            user: Employee object
            current_password: Current password
            new_password: New password
            
        Returns:
            Tuple[bool, list]: (success, list_of_errors)
        """
        # Verify current password
        if not self.verify_password(current_password, user.password_hash):
            return False, ["Current password is incorrect"]
        
        # Validate new password strength
        is_valid, errors = self.validate_password_strength(new_password)
        if not is_valid:
            return False, errors
        
        # Check if new password is different from current
        if self.verify_password(new_password, user.password_hash):
            return False, ["New password must be different from current password"]
        
        # Update password
        user.password_hash = self.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Password changed for user: {user.username}")
        return True, []
    
    def generate_reset_token(self, email: str) -> str:
        """
        Generate password reset token
        
        Args:
            email: User email address
            
        Returns:
            str: Reset token
        """
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=self.reset_token_expire_hours)
        
        self.reset_tokens[token] = {
            "email": email,
            "expires_at": expires_at,
            "used": False
        }
        
        logger.info(f"Password reset token generated for email: {email}")
        return token
    
    def validate_reset_token(self, token: str) -> Optional[str]:
        """
        Validate password reset token
        
        Args:
            token: Reset token
            
        Returns:
            Optional[str]: Email if token is valid, None otherwise
        """
        if token not in self.reset_tokens:
            return None
        
        token_data = self.reset_tokens[token]
        
        # Check if token is expired
        if datetime.utcnow() > token_data["expires_at"]:
            del self.reset_tokens[token]
            return None
        
        # Check if token is already used
        if token_data["used"]:
            return None
        
        return token_data["email"]
    
    def reset_password(self, db: Session, token: str, new_password: str) -> Tuple[bool, list]:
        """
        Reset password using reset token
        
        Args:
            db: Database session
            token: Reset token
            new_password: New password
            
        Returns:
            Tuple[bool, list]: (success, list_of_errors)
        """
        # Validate token
        email = self.validate_reset_token(token)
        if not email:
            return False, ["Invalid or expired reset token"]
        
        # Find user
        user = db.query(Employee).filter(Employee.email == email).first()
        if not user:
            return False, ["User not found"]
        
        # Validate new password
        is_valid, errors = self.validate_password_strength(new_password)
        if not is_valid:
            return False, errors
        
        # Update password
        user.password_hash = self.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        db.commit()
        
        # Mark token as used
        self.reset_tokens[token]["used"] = True
        
        logger.info(f"Password reset for user: {user.username}")
        return True, []
    
    def is_account_locked(self, username: str) -> bool:
        """
        Check if account is locked due to failed login attempts
        
        Args:
            username: Username to check
            
        Returns:
            bool: True if account is locked, False otherwise
        """
        if username not in self.failed_attempts:
            return False
        
        attempt_data = self.failed_attempts[username]
        
        # Check if lockout period has expired
        if datetime.utcnow() > attempt_data["locked_until"]:
            del self.failed_attempts[username]
            return False
        
        return attempt_data["count"] >= self.max_login_attempts
    
    def record_failed_attempt(self, username: str):
        """
        Record failed login attempt
        
        Args:
            username: Username that failed login
        """
        now = datetime.utcnow()
        
        if username not in self.failed_attempts:
            self.failed_attempts[username] = {
                "count": 1,
                "first_attempt": now,
                "last_attempt": now,
                "locked_until": now
            }
        else:
            self.failed_attempts[username]["count"] += 1
            self.failed_attempts[username]["last_attempt"] = now
            
            # Lock account if max attempts reached
            if self.failed_attempts[username]["count"] >= self.max_login_attempts:
                self.failed_attempts[username]["locked_until"] = (
                    now + timedelta(minutes=self.lockout_duration_minutes)
                )
                logger.warning(f"Account locked due to failed attempts: {username}")
    
    def clear_failed_attempts(self, username: str):
        """
        Clear failed login attempts for user
        
        Args:
            username: Username to clear attempts for
        """
        if username in self.failed_attempts:
            del self.failed_attempts[username]
    
    def validate_email_format(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email format
        
        Args:
            email: Email to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, normalized_email)
        """
        try:
            valid = validate_email(email)
            return True, valid.email
        except EmailNotValidError:
            return False, None
    
    def is_username_available(self, db: Session, username: str, exclude_user_id: Optional[int] = None) -> bool:
        """
        Check if username is available
        
        Args:
            db: Database session
            username: Username to check
            exclude_user_id: User ID to exclude from check (for updates)
            
        Returns:
            bool: True if username is available, False otherwise
        """
        query = db.query(Employee).filter(Employee.username == username)
        
        if exclude_user_id:
            query = query.filter(Employee.id != exclude_user_id)
        
        return query.first() is None
    
    def is_email_available(self, db: Session, email: str, exclude_user_id: Optional[int] = None) -> bool:
        """
        Check if email is available
        
        Args:
            db: Database session
            email: Email to check
            exclude_user_id: User ID to exclude from check (for updates)
            
        Returns:
            bool: True if email is available, False otherwise
        """
        query = db.query(Employee).filter(Employee.email == email)
        
        if exclude_user_id:
            query = query.filter(Employee.id != exclude_user_id)
        
        return query.first() is None

# Global auth service instance
auth_service = AuthService()
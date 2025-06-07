"""
Authentication middleware for the HR AI Assistant.

This module handles JWT token validation, user authentication,
and authorization for protected endpoints.
"""

import os
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.employee import Employee
from app.utils.logger import get_logger

logger = get_logger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Security scheme for OpenAPI documentation
security = HTTPBearer(auto_error=False)

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = {
    "/",
    "/docs",
    "/redoc", 
    "/openapi.json",
    "/health",
    "/info",
    "/auth/login",
    "/auth/register",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/static"
}

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware to handle JWT token validation
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and validate authentication if required
        """
        # Check if endpoint requires authentication
        path = request.url.path
        
        # Skip authentication for public endpoints
        if self._is_public_endpoint(path) or request.method == "OPTIONS":
            return await call_next(request)
        
        # Get and validate token
        token = self._extract_token(request)
        if not token:
            return self._unauthorized_response("Missing authentication token")
        
        try:
            # Decode and validate token
            payload = self._decode_token(token)
            if not payload:
                return self._unauthorized_response("Invalid authentication token")
            
            # Add user information to request state
            request.state.user_id = payload.get("sub")
            request.state.username = payload.get("username")
            request.state.employee_id = payload.get("employee_id")
            
        except jwt.ExpiredSignatureError:
            return self._unauthorized_response("Token has expired")
        except jwt.InvalidTokenError:
            return self._unauthorized_response("Invalid token")
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return self._unauthorized_response("Authentication failed")
        
        # Continue with request
        response = await call_next(request)
        return response
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public"""
        # Exact match
        if path in PUBLIC_ENDPOINTS:
            return True
        
        # Prefix match for static files and auth endpoints
        public_prefixes = ["/static/", "/auth/"]
        for prefix in public_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request headers"""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
        
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                return None
            return token
        except ValueError:
            return None
    
    def _decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.InvalidTokenError:
            return None
    
    def _unauthorized_response(self, message: str) -> Response:
        """Return unauthorized response"""
        return Response(
            content=f'{{"detail": "{message}"}}',
            status_code=401,
            headers={"content-type": "application/json"}
        )

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Token payload data
        expires_delta: Token expiration time
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Optional[Dict]: Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid token")
        return None

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Employee:
    """
    Get current authenticated user
    
    Args:
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        Employee: Current authenticated employee
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = db.query(Employee).filter(Employee.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

async def get_current_active_user(
    current_user: Employee = Depends(get_current_user)
) -> Employee:
    """
    Get current active user (must be active)
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Employee: Current active employee
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return current_user

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[Employee]:
    """
    Get current user if authenticated, None otherwise
    
    Args:
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        Optional[Employee]: Current user if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None

def require_role(required_role: str):
    """
    Decorator to require specific role for endpoint access
    
    Args:
        required_role: Required role name
        
    Returns:
        Dependency function
    """
    async def role_checker(
        current_user: Employee = Depends(get_current_active_user)
    ) -> Employee:
        if current_user.role.title.lower() != required_role.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}"
            )
        return current_user
    
    return role_checker

def require_department(required_department: str):
    """
    Decorator to require specific department for endpoint access
    
    Args:
        required_department: Required department name
        
    Returns:
        Dependency function
    """
    async def department_checker(
        current_user: Employee = Depends(get_current_active_user)
    ) -> Employee:
        if current_user.department.name.lower() != required_department.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required department: {required_department}"
            )
        return current_user
    
    return department_checker

def require_manager():
    """
    Decorator to require manager privileges for endpoint access
    
    Returns:
        Dependency function
    """
    async def manager_checker(
        current_user: Employee = Depends(get_current_active_user)
    ) -> Employee:
        if not current_user.is_manager:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Manager privileges required"
            )
        return current_user
    
    return manager_checker

# Token blacklist (in production, use Redis or database)
BLACKLISTED_TOKENS = set()

def blacklist_token(token: str):
    """Add token to blacklist"""
    BLACKLISTED_TOKENS.add(token)

def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted"""
    return token in BLACKLISTED_TOKENS
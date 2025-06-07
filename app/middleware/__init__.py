"""
Middleware package for HR AI Assistant

This package contains middleware components for authentication,
CORS, and other request/response processing.
"""

from .auth import AuthMiddleware, get_current_user, get_current_active_user
from .cors import setup_cors

__all__ = [
    "AuthMiddleware",
    "get_current_user",
    "get_current_active_user", 
    "setup_cors"
]
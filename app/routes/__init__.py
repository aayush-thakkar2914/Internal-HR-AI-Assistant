"""
API Routes package for HR AI Assistant

This package contains all FastAPI route handlers for the application's
REST API endpoints.
"""

from . import auth, chat, employee, leave, document, survey

__all__ = [
    "auth",
    "chat", 
    "employee",
    "leave",
    "document",
    "survey"
]
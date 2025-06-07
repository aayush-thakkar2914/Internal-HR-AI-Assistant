"""
Configuration package for HR AI Assistant

This package contains all configuration modules for database connections,
API integrations, and application settings.
"""

from .database import get_database_url, get_db, engine, SessionLocal
from .opensearch import get_opensearch_client, opensearch_config
from .groq_config import get_groq_client, groq_config

__all__ = [
    "get_database_url",
    "get_db", 
    "engine",
    "SessionLocal",
    "get_opensearch_client",
    "opensearch_config",
    "get_groq_client",
    "groq_config"
]   
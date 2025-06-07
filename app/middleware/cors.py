"""
CORS middleware configuration for the HR AI Assistant.

This module handles Cross-Origin Resource Sharing (CORS) configuration
to enable frontend applications to communicate with the API.
"""

import os
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def get_cors_origins() -> List[str]:
    """
    Get CORS origins from environment configuration.
    
    Returns:
        List[str]: List of allowed origins
    """
    # Default origins for development
    default_origins = [
        "http://localhost:3000",
        "http://localhost:8080", 
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:3001"
    ]
    
    # Get origins from environment variable
    env_origins = os.getenv("CORS_ORIGINS")
    if env_origins:
        try:
            # Parse comma-separated origins
            origins = [origin.strip() for origin in env_origins.split(",")]
            return origins
        except Exception:
            # Fall back to default if parsing fails
            return default_origins
    
    return default_origins

def setup_cors(app: FastAPI) -> None:
    """
    Setup CORS middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Get allowed origins
    origins = get_cors_origins()
    
    # Determine if we're in development mode
    debug_mode = os.getenv("DEBUG", "False").lower() == "true"
    
    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"] if debug_mode else ["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"] if debug_mode else [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-API-Key",
            "X-Client-Version"
        ],
        expose_headers=[
            "X-Process-Time",
            "X-Request-ID",
            "X-Rate-Limit-Remaining",
            "X-Rate-Limit-Reset"
        ],
        max_age=600  # Cache preflight requests for 10 minutes
    )
    
    print(f"CORS configured with origins: {origins}")

# CORS configuration for production environments
PRODUCTION_CORS_CONFIG = {
    "allow_origins": [
        "https://your-domain.com",
        "https://www.your-domain.com",
        "https://hr.your-domain.com"
    ],
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
    "allow_headers": [
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-API-Key"
    ],
    "expose_headers": [
        "X-Process-Time",
        "X-Request-ID"
    ],
    "max_age": 3600
}

def setup_production_cors(app: FastAPI, allowed_origins: List[str]) -> None:
    """
    Setup CORS middleware for production environment.
    
    Args:
        app: FastAPI application instance
        allowed_origins: List of allowed origins for production
    """
    config = PRODUCTION_CORS_CONFIG.copy()
    config["allow_origins"] = allowed_origins
    
    app.add_middleware(CORSMiddleware, **config)
    
    print(f"Production CORS configured with origins: {allowed_origins}")
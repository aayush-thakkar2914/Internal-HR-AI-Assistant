"""
HR AI Assistant FastAPI Application

This is the main FastAPI application entry point for the HR AI Assistant.
It includes all route handlers, middleware, and application configuration.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import uvicorn

# Import configurations
from app.config.database import init_database, check_database_connection, database_health_check
from app.config.opensearch import init_opensearch, check_opensearch_connection, opensearch_health_check
from app.config.groq_config import init_groq, check_groq_connection, groq_health_check

# Import middleware
from app.middleware.cors import setup_cors
from app.middleware.auth import AuthMiddleware

# Import route handlers
from app.routes import (
    auth,
    chat,
    employee,
    leave,
    document,
    survey
)

# Import utilities
from app.utils.logger import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting HR AI Assistant application...")
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_database()
        
        if not check_database_connection():
            logger.error("Database connection failed")
            raise Exception("Database connection failed")
        
        # Initialize OpenSearch
        logger.info("Initializing OpenSearch...")
        init_opensearch()
        
        if not check_opensearch_connection():
            logger.warning("OpenSearch connection failed - RAG features may not work")
        
        # Initialize Groq
        logger.info("Initializing Groq API...")
        init_groq()
        
        if not check_groq_connection():
            logger.error("Groq API connection failed")
            raise Exception("Groq API connection failed")
        
        logger.info("HR AI Assistant application started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise e
    
    yield
    
    # Shutdown
    logger.info("Shutting down HR AI Assistant application...")

# Create FastAPI application
app = FastAPI(
    title="HR AI Assistant",
    description="""
    An intelligent HR assistant powered by AI to help employees with HR-related queries,
    leave management, document requests, and more.
    
    ## Features
    
    * **AI Chat Interface** - Natural language interaction for HR queries
    * **Leave Management** - Request, track, and manage employee leave
    * **Document Management** - Request and access HR documents
    * **Employee Management** - Comprehensive employee data management
    * **Survey & Engagement** - Employee feedback and engagement tracking
    * **Analytics & Reporting** - Insights into HR metrics and trends
    
    ## Authentication
    
    Most endpoints require authentication using JWT tokens. Use the `/auth/login` endpoint
    to obtain an access token.
    """,
    version="1.0.0",
    contact={
        "name": "HR AI Assistant Team",
        "email": "support@hraiassistant.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Setup CORS
setup_cors(app)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Add authentication middleware
app.add_middleware(AuthMiddleware)

# Mount static files
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Custom exception handlers
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with logging"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
    return await http_exception_handler(request, exc)

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom validation exception handler"""
    logger.warning(f"Validation error: {exc.errors()} - {request.url}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "message": "Please check your request data and try again"
        }
    )

@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Database exception handler"""
    logger.error(f"Database error: {str(exc)} - {request.url}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Database error",
            "message": "An error occurred while processing your request. Please try again later."
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"Unexpected error: {str(exc)} - {request.url}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": "An unexpected error occurred. Please contact support if the problem persists."
        }
    )

# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify application status
    """
    try:
        # Check database
        db_health = await database_health_check()
        
        # Check OpenSearch
        opensearch_health = await opensearch_health_check()
        
        # Check Groq API
        groq_health = await groq_health_check()
        
        # Determine overall health
        all_healthy = all([
            db_health["status"] == "healthy",
            opensearch_health["status"] == "healthy",
            groq_health["status"] == "healthy"
        ])
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": "2024-01-01T00:00:00Z",  # Will be replaced with actual timestamp
            "version": "1.0.0",
            "services": {
                "database": db_health,
                "opensearch": opensearch_health,
                "groq_api": groq_health
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": "2024-01-01T00:00:00Z",
                "error": str(e)
            }
        )

@app.get("/", response_class=HTMLResponse, tags=["Root"])
async def read_root():
    """
    Root endpoint serving the frontend application
    """
    try:
        if os.path.exists("frontend/index.html"):
            with open("frontend/index.html", "r") as f:
                return HTMLResponse(content=f.read())
        else:
            return HTMLResponse(
                content="""
                <html>
                    <head><title>HR AI Assistant</title></head>
                    <body>
                        <h1>HR AI Assistant API</h1>
                        <p>Welcome to the HR AI Assistant API!</p>
                        <p><a href="/docs">View API Documentation</a></p>
                        <p><a href="/health">Check System Health</a></p>
                    </body>
                </html>
                """
            )
    except Exception as e:
        logger.error(f"Error serving root page: {e}")
        return HTMLResponse(
            content="<h1>HR AI Assistant</h1><p>Service temporarily unavailable</p>",
            status_code=503
        )

# API Information endpoint
@app.get("/info", tags=["Info"])
async def api_info():
    """
    API information endpoint
    """
    return {
        "name": "HR AI Assistant API",
        "version": "1.0.0",
        "description": "Intelligent HR assistant with AI-powered chat, leave management, and document processing",
        "features": [
            "AI-powered chat interface",
            "Leave request management",
            "Document request processing",
            "Employee management",
            "Survey and engagement tracking",
            "Analytics and reporting"
        ],
        "endpoints": {
            "auth": "/auth/*",
            "chat": "/chat/*", 
            "employees": "/employees/*",
            "leave": "/leave/*",
            "documents": "/documents/*",
            "surveys": "/surveys/*"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        }
    }

# Include route handlers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/chat", tags=["AI Chat"])
app.include_router(employee.router, prefix="/employees", tags=["Employee Management"])
app.include_router(leave.router, prefix="/leave", tags=["Leave Management"])
app.include_router(document.router, prefix="/documents", tags=["Document Management"])
app.include_router(survey.router, prefix="/surveys", tags=["Surveys & Engagement"])

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all incoming requests
    """
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log response
    logger.info(f"Response: {response.status_code} in {process_time:.3f}s")
    
    # Add timing header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# Development server configuration
if __name__ == "__main__":
    import time
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    # Configure logging level
    log_level = "debug" if debug else "info"
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level=log_level,
        access_log=True
    )
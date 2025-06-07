"""
Logging configuration and utilities for the HR AI Assistant.

This module provides centralized logging configuration with structured
logging, file rotation, and different log levels for development and production.
"""

import os
import sys
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional
import structlog
from rich.logging import RichHandler
from rich.console import Console

# Create logs directory
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Get configuration from environment
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"

# Console for rich output
console = Console()

def setup_logging():
    """
    Setup centralized logging configuration for the application.
    
    Configures both standard logging and structured logging with:
    - Console output with rich formatting (development)
    - File output with rotation (production)
    - Structured logging with contextual information
    - Different log levels for different components
    """
    
    # Clear any existing handlers
    logging.getLogger().handlers.clear()
    
    # Set root logger level
    logging.getLogger().setLevel(getattr(logging, LOG_LEVEL))
    
    # Create formatters
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S"
    )
    
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler with rich formatting (for development)
    if DEBUG_MODE:
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True
        )
        console_handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(console_handler)
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(getattr(logging, LOG_LEVEL))
        logging.getLogger().addHandler(console_handler)
    
    # File handlers with rotation
    
    # Application log file
    app_file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "hr_ai_assistant.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    app_file_handler.setFormatter(file_formatter)
    app_file_handler.setLevel(logging.INFO)
    
    # Error log file
    error_file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "errors.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    error_file_handler.setFormatter(file_formatter)
    error_file_handler.setLevel(logging.ERROR)
    
    # Access log file for API requests
    access_file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "access.log",
        maxBytes=50*1024*1024,  # 50MB
        backupCount=5,
        encoding='utf-8'
    )
    access_formatter = logging.Formatter(
        "%(asctime)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    access_file_handler.setFormatter(access_formatter)
    
    # Add file handlers to root logger
    logging.getLogger().addHandler(app_file_handler)
    logging.getLogger().addHandler(error_file_handler)
    
    # Create access logger
    access_logger = logging.getLogger("access")
    access_logger.addHandler(access_file_handler)
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False
    
    # Configure specific loggers
    
    # Database logger
    db_logger = logging.getLogger("sqlalchemy.engine")
    if DEBUG_MODE:
        db_logger.setLevel(logging.INFO)
    else:
        db_logger.setLevel(logging.WARNING)
    
    # HTTP client logger
    http_logger = logging.getLogger("httpx")
    http_logger.setLevel(logging.WARNING)
    
    # OpenSearch logger
    opensearch_logger = logging.getLogger("opensearch")
    opensearch_logger.setLevel(logging.WARNING)
    
    # Groq API logger
    groq_logger = logging.getLogger("groq")
    groq_logger.setLevel(logging.INFO)
    
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Log startup message
    logger = logging.getLogger("hr_ai_assistant.startup")
    logger.info(f"Logging configured - Level: {LOG_LEVEL}, Debug: {DEBUG_MODE}")
    logger.info(f"Log files location: {LOGS_DIR.absolute()}")

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__ from calling module)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)

def get_structured_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__ from calling module)
        
    Returns:
        structlog.BoundLogger: Structured logger instance
    """
    return structlog.get_logger(name)

def log_api_request(method: str, url: str, status_code: int, 
                   duration_ms: float, user_id: Optional[int] = None):
    """
    Log API request information to access log.
    
    Args:
        method: HTTP method
        url: Request URL
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        user_id: User ID if authenticated
    """
    access_logger = logging.getLogger("access")
    user_info = f"user:{user_id}" if user_id else "anonymous"
    access_logger.info(
        f"{method} {url} | {status_code} | {duration_ms:.2f}ms | {user_info}"
    )

def log_auth_event(event_type: str, user_id: Optional[int] = None, 
                  username: Optional[str] = None, ip_address: Optional[str] = None,
                  success: bool = True, details: Optional[str] = None):
    """
    Log authentication events for security monitoring.
    
    Args:
        event_type: Type of auth event (login, logout, password_change, etc.)
        user_id: User ID
        username: Username
        ip_address: Client IP address
        success: Whether the event was successful
        details: Additional details
    """
    auth_logger = logging.getLogger("hr_ai_assistant.auth")
    
    status = "SUCCESS" if success else "FAILED"
    user_info = f"user_id:{user_id}" if user_id else f"username:{username}"
    ip_info = f"ip:{ip_address}" if ip_address else "ip:unknown"
    details_info = f"details:{details}" if details else ""
    
    message = f"AUTH_{event_type.upper()} | {status} | {user_info} | {ip_info}"
    if details_info:
        message += f" | {details_info}"
    
    if success:
        auth_logger.info(message)
    else:
        auth_logger.warning(message)

def log_business_event(event_type: str, entity_type: str, entity_id: str,
                      user_id: int, action: str, details: Optional[dict] = None):
    """
    Log business events for audit trail.
    
    Args:
        event_type: Type of business event (created, updated, deleted, etc.)
        entity_type: Type of entity (leave_request, document, etc.)
        entity_id: Entity ID
        user_id: User performing the action
        action: Specific action performed
        details: Additional details as dictionary
    """
    business_logger = logging.getLogger("hr_ai_assistant.business")
    
    message = f"BUSINESS_{event_type.upper()} | {entity_type}:{entity_id} | user:{user_id} | action:{action}"
    
    if details:
        business_logger.info(message, extra={"details": details})
    else:
        business_logger.info(message)

def log_ai_interaction(query: str, response: str, user_id: int,
                      processing_time_ms: float, confidence_score: float,
                      context_used: bool, escalated: bool = False):
    """
    Log AI chat interactions for analysis and improvement.
    
    Args:
        query: User query
        response: AI response
        user_id: User ID
        processing_time_ms: Processing time in milliseconds
        confidence_score: AI confidence score
        context_used: Whether RAG context was used
        escalated: Whether query was escalated
    """
    ai_logger = logging.getLogger("hr_ai_assistant.ai")
    
    # Log interaction summary (without full content for privacy)
    summary = {
        "user_id": user_id,
        "query_length": len(query),
        "response_length": len(response),
        "processing_time_ms": processing_time_ms,
        "confidence_score": confidence_score,
        "context_used": context_used,
        "escalated": escalated,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    ai_logger.info("AI_INTERACTION", extra=summary)
    
    # Log escalated queries with more detail for review
    if escalated:
        escalation_logger = logging.getLogger("hr_ai_assistant.escalation")
        escalation_logger.warning(
            f"ESCALATED_QUERY | user:{user_id} | confidence:{confidence_score} | query:{query[:100]}..."
        )

def log_performance_metric(metric_name: str, value: float, unit: str = "",
                          context: Optional[dict] = None):
    """
    Log performance metrics for monitoring.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        context: Additional context
    """
    perf_logger = logging.getLogger("hr_ai_assistant.performance")
    
    message = f"METRIC | {metric_name}:{value}"
    if unit:
        message += f"{unit}"
    
    if context:
        perf_logger.info(message, extra=context)
    else:
        perf_logger.info(message)

def log_error_with_context(logger: logging.Logger, error: Exception,
                          context: Optional[dict] = None, user_id: Optional[int] = None):
    """
    Log errors with additional context for debugging.
    
    Args:
        logger: Logger instance to use
        error: Exception that occurred
        context: Additional context information
        user_id: User ID if applicable
    """
    error_context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if user_id:
        error_context["user_id"] = user_id
    
    if context:
        error_context.update(context)
    
    logger.error(f"ERROR | {type(error).__name__}: {str(error)}", extra=error_context, exc_info=True)

# Health check for logging system
def check_logging_health() -> dict:
    """
    Check logging system health.
    
    Returns:
        dict: Health check results
    """
    try:
        # Test log files are writable
        test_logger = logging.getLogger("hr_ai_assistant.health_check")
        test_logger.info("Logging health check")
        
        # Check log file sizes
        log_files = {
            "app_log": LOGS_DIR / "hr_ai_assistant.log",
            "error_log": LOGS_DIR / "errors.log",
            "access_log": LOGS_DIR / "access.log"
        }
        
        file_info = {}
        for name, path in log_files.items():
            if path.exists():
                file_info[name] = {
                    "exists": True,
                    "size_mb": round(path.stat().st_size / (1024*1024), 2),
                    "writable": os.access(path, os.W_OK)
                }
            else:
                file_info[name] = {"exists": False}
        
        return {
            "status": "healthy",
            "log_level": LOG_LEVEL,
            "debug_mode": DEBUG_MODE,
            "logs_directory": str(LOGS_DIR.absolute()),
            "log_files": file_info
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
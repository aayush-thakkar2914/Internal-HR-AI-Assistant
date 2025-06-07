"""
Database configuration for Oracle database connection.

This module handles Oracle database connectivity using SQLAlchemy ORM
with cx_Oracle driver for the HR AI Assistant application.
"""

import os
from typing import Generator
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import oracledb # Make oracledb usage explicit for linters; SQLAlchemy uses it implicitly.
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
ORACLE_HOST = os.getenv("ORACLE_HOST", "localhost")
ORACLE_PORT = os.getenv("ORACLE_PORT", "1521")
ORACLE_SERVICE_NAME = os.getenv("ORACLE_SERVICE_NAME", "XE")
ORACLE_USERNAME = os.getenv("ORACLE_USERNAME")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD")

def get_database_url() -> str:
    """
    Construct Oracle database URL for SQLAlchemy connection.
    
    Returns:
        str: Complete database connection URL
    """
    return (
        f"oracle+oracledb://{ORACLE_USERNAME}:{ORACLE_PASSWORD}@"
        f"{ORACLE_HOST}:{ORACLE_PORT}/{ORACLE_SERVICE_NAME}"
    )

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    get_database_url(),
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=os.getenv("DEBUG", "False").lower() == "true"
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Create declarative base for ORM models
Base = declarative_base()

# Metadata for table operations
metadata = MetaData()

def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    Yields:
        Session: Database session for dependency injection
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def init_database():
    """
    Initialize database by creating all tables.
    This function should be called during application startup.
    """
    try:
        # Import all models to ensure they are registered
        from app.models import employee, leave, document, survey, query
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise e

def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as connection:
            result = connection.execute("SELECT 1 FROM DUAL")
            return result.fetchone() is not None
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

# Database health check function
async def database_health_check() -> dict:
    """
    Perform database health check for monitoring.
    
    Returns:
        dict: Health check status and details
    """
    try:
        db = SessionLocal()
        
        # Test basic query
        result = db.execute("SELECT 1 FROM DUAL")
        row = result.fetchone()
        
        if row:
            db.close()
            return {
                "status": "healthy",
                "message": "Database connection successful",
                "database": "Oracle",
                "host": ORACLE_HOST,
                "port": ORACLE_PORT,
                "service": ORACLE_SERVICE_NAME
            }
        else:
            db.close()
            return {
                "status": "unhealthy",
                "message": "Database query failed",
                "database": "Oracle"
            }
            
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
            "database": "Oracle"
        }

# Connection string for external tools
DATABASE_URL = get_database_url()
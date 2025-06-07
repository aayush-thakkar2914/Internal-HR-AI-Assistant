"""
Employee data models for the HR AI Assistant.

This module contains SQLAlchemy ORM models for employee management,
including employee profiles, departments, and roles.
"""

from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, Boolean, ForeignKey, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum

from app.config.database import Base

class EmploymentStatus(enum.Enum):
    """Employment status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"
    ON_LEAVE = "on_leave"
    PROBATION = "probation"

class GenderType(enum.Enum):
    """Gender type enumeration"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"

class Department(Base):
    """Department model for organizational structure"""
    
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    department_code = Column(String(10), unique=True, nullable=False)
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    budget = Column(Numeric(15, 2), default=0)
    location = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employees = relationship("Employee", back_populates="department", foreign_keys="Employee.department_id")
    manager = relationship("Employee", foreign_keys=[manager_id], post_update=True)
    
    def __repr__(self):
        return f"<Department(id={self.id}, name='{self.name}', code='{self.department_code}')>"

class Role(Base):
    """Role model for job positions and responsibilities"""
    
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    role_code = Column(String(20), unique=True, nullable=False)
    level = Column(Integer, default=1)  # 1=entry, 2=mid, 3=senior, 4=lead, 5=manager
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    min_salary = Column(Numeric(10, 2))
    max_salary = Column(Numeric(10, 2))
    required_skills = Column(Text)  # JSON string of skills
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    department = relationship("Department")
    employees = relationship("Employee", back_populates="role")
    
    def __repr__(self):
        return f"<Role(id={self.id}, title='{self.title}', code='{self.role_code}')>"

class Employee(Base):
    """Employee model for staff information and management"""
    
    __tablename__ = "employees"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Personal information
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    middle_name = Column(String(50))
    date_of_birth = Column(Date)
    gender = Column(Enum(GenderType))
    phone_number = Column(String(20))
    emergency_contact_name = Column(String(100))
    emergency_contact_phone = Column(String(20))
    
    # Address information
    address_line1 = Column(String(200))
    address_line2 = Column(String(200))
    city = Column(String(50))
    state = Column(String(50))
    postal_code = Column(String(20))
    country = Column(String(50), default="India")
    
    # Employment information
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    hire_date = Column(Date, nullable=False)
    termination_date = Column(Date)
    employment_status = Column(Enum(EmploymentStatus), default=EmploymentStatus.ACTIVE)
    employment_type = Column(String(20), default="full_time")  # full_time, part_time, contract, intern
    
    # Compensation
    salary = Column(Numeric(10, 2))
    currency = Column(String(3), default="INR")
    pay_frequency = Column(String(20), default="monthly")  # monthly, bi_weekly, weekly
    
    # System fields
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    profile_picture_url = Column(String(500))
    bio = Column(Text)
    skills = Column(Text)  # JSON string of skills
    certifications = Column(Text)  # JSON string of certifications
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("employees.id"))
    updated_by = Column(Integer, ForeignKey("employees.id"))
    
    # Relationships
    department = relationship("Department", back_populates="employees", foreign_keys=[department_id])
    role = relationship("Role", back_populates="employees")
    manager = relationship("Employee", remote_side=[id], foreign_keys=[manager_id])
    subordinates = relationship("Employee", remote_side=[manager_id])
    
    # Related records
    leave_requests = relationship("LeaveRequest", back_populates="employee")
    leave_balances = relationship("LeaveBalance", back_populates="employee")
    document_requests = relationship("DocumentRequest", back_populates="employee")
    survey_responses = relationship("SurveyResponse", back_populates="employee")
    chat_sessions = relationship("ChatSession", back_populates="employee")
    query_logs = relationship("QueryLog", back_populates="employee")
    
    @property
    def full_name(self) -> str:
        """Get employee's full name"""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    @property
    def display_name(self) -> str:
        """Get employee's display name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_manager(self) -> bool:
        """Check if employee is a manager"""
        return len(self.subordinates) > 0
    
    @property
    def years_of_service(self) -> float:
        """Calculate years of service"""
        if not self.hire_date:
            return 0
        
        end_date = self.termination_date or date.today()
        delta = end_date - self.hire_date
        return round(delta.days / 365.25, 2)
    
    @property
    def age(self) -> Optional[int]:
        """Calculate employee's age"""
        if not self.date_of_birth:
            return None
        
        today = date.today()
        age = today.year - self.date_of_birth.year
        
        # Adjust if birthday hasn't occurred this year
        if today.month < self.date_of_birth.month or \
           (today.month == self.date_of_birth.month and today.day < self.date_of_birth.day):
            age -= 1
            
        return age
    
    def check_password(self, password: str) -> bool:
        """Check if provided password matches the stored hash"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(password, self.password_hash)
    
    def set_password(self, password: str) -> None:
        """Set password hash for the employee"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.password_hash = pwd_context.hash(password)
    
    def to_dict(self) -> dict:
        """Convert employee to dictionary representation"""
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "department": self.department.name if self.department else None,
            "role": self.role.title if self.role else None,
            "manager": self.manager.full_name if self.manager else None,
            "hire_date": self.hire_date.isoformat() if self.hire_date else None,
            "employment_status": self.employment_status.value if self.employment_status else None,
            "is_active": self.is_active,
            "years_of_service": self.years_of_service,
            "phone_number": self.phone_number,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<Employee(id={self.id}, employee_id='{self.employee_id}', name='{self.full_name}')>"
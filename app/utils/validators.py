"""
Validation utilities for the HR AI Assistant.

This module contains validation functions for various data types
including emails, phone numbers, file uploads, and business rules.
"""

import re
import os
from datetime import date, datetime
from typing import List, Tuple, Optional, Any
from pathlib import Path
import mimetypes

def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    if len(email) > 254:
        return False, "Email address too long"
    
    # Check for consecutive dots
    if '..' in email:
        return False, "Email cannot contain consecutive dots"
    
    # Check local part length (before @)
    local_part = email.split('@')[0]
    if len(local_part) > 64:
        return False, "Email local part too long"
    
    return True, ""

def validate_phone(phone: str, country_code: str = "IN") -> Tuple[bool, str]:
    """
    Validate phone number format.
    
    Args:
        phone: Phone number to validate
        country_code: Country code for validation rules
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number is required"
    
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    if country_code == "IN":
        # Indian phone number validation
        # Should be 10 digits or +91 followed by 10 digits
        if cleaned.startswith('+91'):
            digits = cleaned[3:]
            if len(digits) != 10:
                return False, "Indian phone number should have 10 digits after country code"
        elif len(cleaned) == 10:
            digits = cleaned
        else:
            return False, "Invalid Indian phone number format"
        
        # Check if it starts with valid digit (6-9 for mobile)
        if not digits[0] in '6789':
            return False, "Indian mobile number should start with 6, 7, 8, or 9"
        
        # Check all digits are numeric
        if not digits.isdigit():
            return False, "Phone number should contain only digits"
    
    else:
        # Generic phone validation
        if len(cleaned) < 7 or len(cleaned) > 15:
            return False, "Phone number should be between 7 and 15 digits"
    
    return True, ""

def validate_employee_id(employee_id: str, pattern: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate employee ID format.
    
    Args:
        employee_id: Employee ID to validate
        pattern: Optional regex pattern for validation
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not employee_id:
        return False, "Employee ID is required"
    
    if len(employee_id) < 3 or len(employee_id) > 20:
        return False, "Employee ID should be between 3 and 20 characters"
    
    # Default pattern: alphanumeric with optional hyphens/underscores
    default_pattern = r'^[A-Za-z0-9_-]+$'
    validation_pattern = pattern or default_pattern
    
    if not re.match(validation_pattern, employee_id):
        return False, "Employee ID contains invalid characters"
    
    return True, ""

def validate_file_extension(filename: str, allowed_extensions: List[str]) -> Tuple[bool, str]:
    """
    Validate file extension against allowed list.
    
    Args:
        filename: Filename to validate
        allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.docx'])
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not filename:
        return False, "Filename is required"
    
    file_ext = Path(filename).suffix.lower()
    
    if not file_ext:
        return False, "File must have an extension"
    
    if file_ext not in [ext.lower() for ext in allowed_extensions]:
        return False, f"File type {file_ext} not allowed. Allowed types: {', '.join(allowed_extensions)}"
    
    return True, ""

def validate_file_size(file_size: int, max_size_mb: int = 10) -> Tuple[bool, str]:
    """
    Validate file size.
    
    Args:
        file_size: File size in bytes
        max_size_mb: Maximum size in MB
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if file_size <= 0:
        return False, "File is empty"
    
    if file_size > max_size_bytes:
        return False, f"File size ({file_size / (1024*1024):.1f}MB) exceeds maximum allowed size ({max_size_mb}MB)"
    
    return True, ""

def validate_date_range(start_date: date, end_date: date, 
                       min_days: int = 0, max_days: int = 365) -> Tuple[bool, str]:
    """
    Validate date range.
    
    Args:
        start_date: Start date
        end_date: End date
        min_days: Minimum number of days in range
        max_days: Maximum number of days in range
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if start_date > end_date:
        return False, "Start date cannot be after end date"
    
    days_diff = (end_date - start_date).days + 1
    
    if days_diff < min_days:
        return False, f"Date range must be at least {min_days} days"
    
    if days_diff > max_days:
        return False, f"Date range cannot exceed {max_days} days"
    
    return True, ""

def validate_future_date(check_date: date, min_days_ahead: int = 0) -> Tuple[bool, str]:
    """
    Validate that date is in the future.
    
    Args:
        check_date: Date to validate
        min_days_ahead: Minimum days ahead of today
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    today = date.today()
    days_ahead = (check_date - today).days
    
    if days_ahead < min_days_ahead:
        if min_days_ahead == 0:
            return False, "Date cannot be in the past"
        else:
            return False, f"Date must be at least {min_days_ahead} days in the future"
    
    return True, ""

def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, list_of_errors)
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if len(password) > 128:
        errors.append("Password must be less than 128 characters")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    
    # Check for common weak patterns
    weak_patterns = [
        r'(.)\1{2,}',  # Repeated characters (aaa, 111)
        r'(012|123|234|345|456|567|678|789|890)',  # Sequential numbers
        r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)',  # Sequential letters
    ]
    
    for pattern in weak_patterns:
        if re.search(pattern, password.lower()):
            errors.append("Password contains weak patterns (repeated or sequential characters)")
            break
    
    # Check against common passwords
    common_passwords = [
        'password', '123456', 'password123', 'admin', 'qwerty', 'letmein',
        'welcome', 'monkey', '1234567890', 'abc123', 'password1'
    ]
    
    if password.lower() in common_passwords:
        errors.append("Password is too common")
    
    return len(errors) == 0, errors

def validate_salary_range(salary: float, min_salary: float = 0, 
                         max_salary: float = 10000000) -> Tuple[bool, str]:
    """
    Validate salary amount.
    
    Args:
        salary: Salary amount to validate
        min_salary: Minimum allowed salary
        max_salary: Maximum allowed salary
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if salary < min_salary:
        return False, f"Salary cannot be less than {min_salary}"
    
    if salary > max_salary:
        return False, f"Salary cannot exceed {max_salary}"
    
    return True, ""

def validate_json_structure(data: Any, required_fields: List[str]) -> Tuple[bool, str]:
    """
    Validate JSON data structure.
    
    Args:
        data: Data to validate
        required_fields: List of required field names
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Data must be a JSON object"
    
    missing_fields = []
    for field in required_fields:
        if field not in data:
            missing_fields.append(field)
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, ""

def validate_leave_dates(start_date: date, end_date: date, 
                        leave_type: str = "general") -> Tuple[bool, List[str]]:
    """
    Validate leave request dates according to business rules.
    
    Args:
        start_date: Leave start date
        end_date: Leave end date
        leave_type: Type of leave for specific validation
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, list_of_errors)
    """
    errors = []
    
    # Basic date validation
    if start_date > end_date:
        errors.append("Start date cannot be after end date")
    
    # Check if dates are in the past
    today = date.today()
    if start_date < today:
        errors.append("Leave cannot be applied for past dates")
    
    # Check advance notice (general rule: at least 1 day advance)
    if (start_date - today).days < 1:
        errors.append("Leave must be applied at least 1 day in advance")
    
    # Check maximum leave duration
    leave_duration = (end_date - start_date).days + 1
    max_duration = 30  # Default max 30 days
    
    if leave_type == "sick":
        max_duration = 7  # Sick leave max 7 days without doctor's note
    elif leave_type == "vacation":
        max_duration = 21  # Vacation max 21 consecutive days
    
    if leave_duration > max_duration:
        errors.append(f"Maximum {max_duration} consecutive days allowed for {leave_type} leave")
    
    # Check if leave spans over weekends (business rule dependent)
    # This is just an example - actual implementation would depend on company policy
    
    return len(errors) == 0, errors

def validate_survey_questions(questions: List[dict]) -> Tuple[bool, List[str]]:
    """
    Validate survey question structure.
    
    Args:
        questions: List of question dictionaries
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, list_of_errors)
    """
    errors = []
    
    if not questions:
        errors.append("Survey must have at least one question")
        return False, errors
    
    required_fields = ['id', 'text', 'type']
    valid_types = ['text', 'textarea', 'single_choice', 'multiple_choice', 'scale', 'rating', 'yes_no']
    
    for i, question in enumerate(questions):
        # Check required fields
        for field in required_fields:
            if field not in question:
                errors.append(f"Question {i+1}: Missing required field '{field}'")
        
        # Validate question type
        if 'type' in question and question['type'] not in valid_types:
            errors.append(f"Question {i+1}: Invalid question type '{question['type']}'")
        
        # Validate choice questions have options
        if question.get('type') in ['single_choice', 'multiple_choice']:
            if 'options' not in question or not question['options']:
                errors.append(f"Question {i+1}: Choice questions must have options")
        
        # Validate scale questions have range
        if question.get('type') in ['scale', 'rating']:
            if 'scale' not in question:
                errors.append(f"Question {i+1}: Scale questions must have scale definition")
    
    return len(errors) == 0, errors

def validate_file_content_type(file_content: bytes, expected_type: str) -> Tuple[bool, str]:
    """
    Validate file content matches expected type.
    
    Args:
        file_content: File content as bytes
        expected_type: Expected MIME type
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not file_content:
        return False, "File content is empty"
    
    # Simple validation based on file headers/magic numbers
    file_signatures = {
        'application/pdf': b'%PDF',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': b'PK',  # DOCX
        'image/jpeg': b'\xff\xd8\xff',
        'image/png': b'\x89PNG\r\n\x1a\n',
        'text/plain': b'',  # Text files don't have specific signature
    }
    
    if expected_type in file_signatures:
        signature = file_signatures[expected_type]
        if signature and not file_content.startswith(signature):
            return False, f"File content does not match expected type {expected_type}"
    
    return True, ""

def validate_business_email_domain(email: str, allowed_domains: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Validate email domain against allowed business domains.
    
    Args:
        email: Email address to validate
        allowed_domains: List of allowed domains (if None, allows all)
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not email or '@' not in email:
        return False, "Invalid email format"
    
    domain = email.split('@')[1].lower()
    
    # Block common personal email domains for business emails
    personal_domains = [
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
        'yahoo.co.in', 'rediffmail.com', 'ymail.com'
    ]
    
    if allowed_domains:
        if domain not in [d.lower() for d in allowed_domains]:
            return False, f"Email domain '{domain}' is not allowed"
    else:
        # If no specific domains allowed, just block personal ones
        if domain in personal_domains:
            return False, "Personal email domains are not allowed for business accounts"
    
    return True, ""
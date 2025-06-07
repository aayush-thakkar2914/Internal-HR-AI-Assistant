"""
Helper utility functions for the HR AI Assistant.

This module contains various utility functions used throughout the application
for common operations like date formatting, file handling, and data processing.
"""

import os
import re
import hashlib
import secrets
import smtplib
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import unicodedata

def generate_unique_id(prefix: str = "", length: int = 8) -> str:
    """
    Generate a unique ID with optional prefix.
    
    Args:
        prefix: Optional prefix for the ID
        length: Length of the random part
        
    Returns:
        str: Unique ID
    """
    random_part = secrets.token_hex(length)[:length].upper()
    return f"{prefix}{random_part}" if prefix else random_part

def format_date(date_obj: Union[date, datetime], format_type: str = "display") -> str:
    """
    Format date for display or API usage.
    
    Args:
        date_obj: Date or datetime object
        format_type: Type of formatting ("display", "api", "filename")
        
    Returns:
        str: Formatted date string
    """
    if not date_obj:
        return ""
    
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    formats = {
        "display": "%B %d, %Y",           # January 15, 2024
        "short": "%m/%d/%Y",              # 01/15/2024
        "api": "%Y-%m-%d",                # 2024-01-15
        "filename": "%Y%m%d",             # 20240115
        "verbose": "%A, %B %d, %Y"        # Monday, January 15, 2024
    }
    
    return date_obj.strftime(formats.get(format_type, formats["display"]))

def format_currency(amount: float, currency: str = "INR", include_symbol: bool = True) -> str:
    """
    Format currency amount for display.
    
    Args:
        amount: Amount to format
        currency: Currency code (INR, USD, etc.)
        include_symbol: Whether to include currency symbol
        
    Returns:
        str: Formatted currency string
    """
    if amount is None:
        return "0.00"
    
    # Currency symbols
    symbols = {
        "INR": "₹",
        "USD": "$",
        "EUR": "€",
        "GBP": "£"
    }
    
    # Format with Indian numbering system for INR
    if currency == "INR":
        # Convert to string with 2 decimal places
        formatted = f"{amount:,.2f}"
        
        # Convert to Indian numbering (lakhs, crores)
        if amount >= 10000000:  # 1 crore
            crores = amount / 10000000
            formatted = f"{crores:.2f} Cr"
        elif amount >= 100000:  # 1 lakh
            lakhs = amount / 100000
            formatted = f"{lakhs:.2f} L"
        else:
            formatted = f"{amount:,.2f}"
    else:
        formatted = f"{amount:,.2f}"
    
    if include_symbol:
        symbol = symbols.get(currency, currency)
        return f"{symbol}{formatted}"
    
    return formatted

def calculate_business_days(start_date: date, end_date: date, 
                          exclude_weekends: bool = True,
                          holidays: Optional[List[date]] = None) -> int:
    """
    Calculate business days between two dates.
    
    Args:
        start_date: Start date
        end_date: End date
        exclude_weekends: Whether to exclude weekends
        holidays: List of holiday dates to exclude
        
    Returns:
        int: Number of business days
    """
    if start_date > end_date:
        return 0
    
    if holidays is None:
        holidays = []
    
    business_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Check if it's a weekend (Saturday=5, Sunday=6)
        if exclude_weekends and current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue
        
        # Check if it's a holiday
        if current_date in holidays:
            current_date += timedelta(days=1)
            continue
        
        business_days += 1
        current_date += timedelta(days=1)
    
    return business_days

def send_email(to_email: str, subject: str, body: str, 
               html_body: Optional[str] = None,
               from_email: Optional[str] = None,
               smtp_config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Send email using SMTP configuration.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Plain text body
        html_body: HTML body (optional)
        from_email: Sender email (optional)
        smtp_config: SMTP configuration (optional)
        
    Returns:
        bool: True if email sent successfully
    """
    try:
        # Default SMTP configuration
        default_config = {
            "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
            "port": int(os.getenv("SMTP_PORT", "587")),
            "username": os.getenv("SMTP_USERNAME"),
            "password": os.getenv("SMTP_PASSWORD"),
            "use_tls": True
        }
        
        config = smtp_config or default_config
        from_email = from_email or os.getenv("FROM_EMAIL", config["username"])
        
        if not config["username"] or not config["password"]:
            return False
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        
        # Add plain text part
        text_part = MIMEText(body, 'plain')
        msg.attach(text_part)
        
        # Add HTML part if provided
        if html_body:
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(config["host"], config["port"]) as server:
            if config.get("use_tls", True):
                server.starttls()
            server.login(config["username"], config["password"])
            server.send_message(msg)
        
        return True
        
    except Exception:
        return False

def hash_file(file_path: Union[str, Path], algorithm: str = "sha256") -> str:
    """
    Calculate hash of a file.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm (md5, sha1, sha256, etc.)
        
    Returns:
        str: File hash
    """
    hash_obj = hashlib.new(algorithm)
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()

def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename for safe file system usage.
    
    Args:
        filename: Original filename
        max_length: Maximum filename length
        
    Returns:
        str: Sanitized filename
    """
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Normalize unicode characters
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    # Remove multiple spaces and underscores
    filename = re.sub(r'[_\s]+', '_', filename)
    
    # Trim and ensure it's not empty
    filename = filename.strip('_. ')
    if not filename:
        filename = f"file_{generate_unique_id(length=4)}"
    
    # Truncate if too long (preserve extension)
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        available_length = max_length - len(ext)
        filename = name[:available_length] + ext
    
    return filename

def extract_keywords(text: str, min_length: int = 3, max_keywords: int = 20) -> List[str]:
    """
    Extract keywords from text using simple frequency analysis.
    
    Args:
        text: Text to extract keywords from
        min_length: Minimum keyword length
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List[str]: List of keywords
    """
    if not text:
        return []
    
    # Convert to lowercase and split into words
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    
    # Common stop words to exclude
    stop_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
        'after', 'above', 'below', 'between', 'among', 'a', 'an', 'is', 'are',
        'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
        'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can',
        'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we',
        'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its',
        'our', 'their'
    }
    
    # Filter words
    filtered_words = [
        word for word in words 
        if len(word) >= min_length and word not in stop_words
    ]
    
    # Count frequency
    word_freq = {}
    for word in filtered_words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in keywords[:max_keywords]]

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to specified length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        str: Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def parse_name(full_name: str) -> Dict[str, str]:
    """
    Parse full name into components.
    
    Args:
        full_name: Full name string
        
    Returns:
        Dict: Name components (first, middle, last)
    """
    if not full_name:
        return {"first": "", "middle": "", "last": ""}
    
    parts = full_name.strip().split()
    
    if len(parts) == 1:
        return {"first": parts[0], "middle": "", "last": ""}
    elif len(parts) == 2:
        return {"first": parts[0], "middle": "", "last": parts[1]}
    else:
        return {
            "first": parts[0],
            "middle": " ".join(parts[1:-1]),
            "last": parts[-1]
        }

def mask_sensitive_data(data: str, mask_char: str = "*", 
                       preserve_start: int = 2, preserve_end: int = 2) -> str:
    """
    Mask sensitive data for logging/display.
    
    Args:
        data: Data to mask
        mask_char: Character to use for masking
        preserve_start: Number of characters to preserve at start
        preserve_end: Number of characters to preserve at end
        
    Returns:
        str: Masked data
    """
    if not data or len(data) <= preserve_start + preserve_end:
        return mask_char * len(data) if data else ""
    
    start = data[:preserve_start]
    end = data[-preserve_end:] if preserve_end > 0 else ""
    middle_length = len(data) - preserve_start - preserve_end
    middle = mask_char * middle_length
    
    return start + middle + end

def convert_size_to_bytes(size_str: str) -> int:
    """
    Convert size string (e.g., "10MB", "1.5GB") to bytes.
    
    Args:
        size_str: Size string
        
    Returns:
        int: Size in bytes
    """
    size_str = size_str.upper().strip()
    
    # Extract number and unit
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?B?)$', size_str)
    if not match:
        raise ValueError(f"Invalid size format: {size_str}")
    
    number = float(match.group(1))
    unit = match.group(2) or "B"
    
    multipliers = {
        "B": 1,
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
        "TB": 1024**4
    }
    
    return int(number * multipliers[unit])

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    
    size = float(size_bytes)
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"
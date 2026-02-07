"""Grid-X Common Utilities

This module contains shared utility functions used across coordinator and worker modules.
"""

import hashlib
import re
import time
import uuid
from typing import Any, Optional
from datetime import datetime

# ============================================================================
# TIME & TIMESTAMP UTILITIES
# ============================================================================

def now() -> float:
    """Get current timestamp in seconds since epoch"""
    return time.time()


def timestamp_to_datetime(timestamp: float) -> datetime:
    """Convert Unix timestamp to datetime object"""
    return datetime.fromtimestamp(timestamp)


def format_timestamp(timestamp: float) -> str:
    """Format timestamp as human-readable string"""
    dt = timestamp_to_datetime(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string"""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.2f}h"


# ============================================================================
# HASHING & SECURITY
# ============================================================================

def hash_credentials(user_id: str, password: str) -> str:
    """
    Create SHA256 hash of credentials for authentication
    
    Args:
        user_id: User identifier
        password: User password
        
    Returns:
        Hexadecimal hash string
    """
    combined = f"{user_id}:{password}"
    return hashlib.sha256(combined.encode()).hexdigest()


def hash_string(text: str) -> str:
    """Create SHA256 hash of any string"""
    return hashlib.sha256(text.encode()).hexdigest()


def generate_token() -> str:
    """Generate a secure random token"""
    return hashlib.sha256(uuid.uuid4().bytes).hexdigest()


# ============================================================================
# INPUT VALIDATION
# ============================================================================

def validate_uuid(value: str) -> bool:
    """
    Validate UUID format (version 4)
    
    Args:
        value: String to validate
        
    Returns:
        True if valid UUID, False otherwise
    """
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(value))


def validate_user_id(user_id: str) -> bool:
    """
    Validate user_id format
    
    Rules:
    - Alphanumeric, underscore, hyphen only
    - 1-64 characters
    - No special characters
    
    Args:
        user_id: User identifier to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not user_id or not isinstance(user_id, str):
        return False
    if len(user_id) < 1 or len(user_id) > 64:
        return False
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', user_id))


def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength
    
    Requirements:
    - At least 8 characters
    - At most 128 characters
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password or not isinstance(password, str):
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password must be at most 128 characters long"
    
    return True, None


def validate_language(language: str) -> bool:
    """
    Validate programming language
    
    Args:
        language: Language identifier
        
    Returns:
        True if supported language, False otherwise
    """
    from .constants import SUPPORTED_LANGUAGES
    return language in SUPPORTED_LANGUAGES


def validate_code_length(code: str, max_length: int = 1_000_000) -> bool:
    """
    Validate code length
    
    Args:
        code: Code string to validate
        max_length: Maximum allowed length in characters
        
    Returns:
        True if valid length, False otherwise
    """
    return isinstance(code, str) and 0 < len(code) <= max_length


# ============================================================================
# INPUT SANITIZATION
# ============================================================================

def sanitize_string(value: Any, max_length: int = 1000) -> str:
    """
    Sanitize string input
    
    - Converts to string if not already
    - Removes null bytes
    - Limits length
    
    Args:
        value: Input value to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        value = str(value)
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    # Remove other control characters except newlines and tabs
    value = ''.join(char for char in value 
                   if char.isprintable() or char in '\n\r\t')
    
    # Limit length
    return value[:max_length]


def sanitize_user_id(user_id: str) -> str:
    """
    Sanitize user ID by removing invalid characters
    
    Args:
        user_id: User ID to sanitize
        
    Returns:
        Sanitized user ID
    """
    # Remove all non-alphanumeric, non-underscore, non-hyphen characters
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', user_id)
    return sanitized[:64]


# ============================================================================
# FORMATTING UTILITIES
# ============================================================================

def format_bytes(bytes_val: int) -> str:
    """
    Format bytes to human-readable string
    
    Args:
        bytes_val: Number of bytes
        
    Returns:
        Formatted string (e.g., "1.50 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} EB"


def format_percentage(value: float) -> str:
    """
    Format float as percentage
    
    Args:
        value: Float value (0-1 or 0-100)
        
    Returns:
        Formatted percentage string
    """
    if value <= 1.0:
        value *= 100
    return f"{value:.1f}%"


def format_number(value: float, decimals: int = 2) -> str:
    """
    Format number with thousand separators
    
    Args:
        value: Number to format
        decimals: Number of decimal places
        
    Returns:
        Formatted number string
    """
    return f"{value:,.{decimals}f}"


# ============================================================================
# UNIQUE ID GENERATION
# ============================================================================

def generate_job_id() -> str:
    """Generate unique job ID (UUID4)"""
    return str(uuid.uuid4())


def generate_worker_id() -> str:
    """Generate unique worker ID (UUID4)"""
    return str(uuid.uuid4())


def generate_task_id() -> str:
    """Generate unique task ID (UUID4)"""
    return str(uuid.uuid4())


# ============================================================================
# DATA STRUCTURE UTILITIES
# ============================================================================

def safe_get(dictionary: dict, key: str, default: Any = None) -> Any:
    """
    Safely get value from dictionary with default
    
    Args:
        dictionary: Dictionary to access
        key: Key to retrieve
        default: Default value if key not found
        
    Returns:
        Value or default
    """
    return dictionary.get(key, default)


def merge_dicts(*dicts: dict) -> dict:
    """
    Merge multiple dictionaries (later dicts override earlier ones)
    
    Args:
        *dicts: Variable number of dictionaries
        
    Returns:
        Merged dictionary
    """
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result


def remove_none_values(dictionary: dict) -> dict:
    """
    Remove keys with None values from dictionary
    
    Args:
        dictionary: Dictionary to clean
        
    Returns:
        Dictionary without None values
    """
    return {k: v for k, v in dictionary.items() if v is not None}


# ============================================================================
# ERROR HANDLING UTILITIES
# ============================================================================

def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert value to int
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_bool(value: Any, default: bool = False) -> bool:
    """
    Safely convert value to bool
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Boolean value or default
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    try:
        return bool(value)
    except (ValueError, TypeError):
        return default


# ============================================================================
# RESOURCE CALCULATION UTILITIES
# ============================================================================

def calculate_job_cost(
    cpu_cores: int = 1,
    memory_mb: int = 512,
    duration_seconds: float = 60,
    base_cost: float = 1.0
) -> float:
    """
    Calculate job cost based on resources
    
    Args:
        cpu_cores: Number of CPU cores
        memory_mb: Memory in MB
        duration_seconds: Execution duration
        base_cost: Base cost multiplier
        
    Returns:
        Calculated cost
    """
    # Simple formula: base_cost * (cpu * 0.5 + memory_gb * 0.3 + minutes * 0.2)
    memory_gb = memory_mb / 1024
    minutes = duration_seconds / 60
    
    cost = base_cost * (
        (cpu_cores * 0.5) +
        (memory_gb * 0.3) +
        (minutes * 0.2)
    )
    
    return max(cost, base_cost)  # Minimum is base_cost


def calculate_worker_reward(job_cost: float, reward_percentage: float = 0.8) -> float:
    """
    Calculate worker reward from job cost
    
    Args:
        job_cost: Cost of the job
        reward_percentage: Percentage of cost given to worker (0-1)
        
    Returns:
        Worker reward amount
    """
    return job_cost * reward_percentage

"""
Grid-X Common Utilities
Shared utility functions across modules
"""

import hashlib
import time
import re
import uuid
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Time & Timestamp
# ============================================================================

def now() -> float:
    """Get current Unix timestamp"""
    return time.time()


def format_timestamp(ts: float, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format timestamp to readable string"""
    return time.strftime(format_str, time.localtime(ts))


# ============================================================================
# Hashing & Crypto
# ============================================================================

def hash_credentials(user_id: str, password: str) -> str:
    """
    Create SHA256 hash of credentials
    
    Args:
        user_id: User identifier
        password: User password
        
    Returns:
        Hex string of SHA256 hash
    """
    combined = f"{user_id}:{password}"
    return hashlib.sha256(combined.encode()).hexdigest()


def hash_string(value: str) -> str:
    """Create SHA256 hash of string"""
    return hashlib.sha256(value.encode()).hexdigest()


# ============================================================================
# Input Validation
# ============================================================================

def validate_uuid(value: str) -> bool:
    """
    Validate UUID format
    
    Args:
        value: String to validate
        
    Returns:
        True if valid UUID, False otherwise
    """
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def validate_user_id(user_id: str) -> bool:
    """
    Validate user_id format
    
    Rules:
    - Alphanumeric, underscore, hyphen only
    - 1-64 characters
    - Cannot start with numbers
    
    Args:
        user_id: User ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not user_id or not isinstance(user_id, str):
        return False
    
    if len(user_id) < 1 or len(user_id) > 64:
        return False
    
    # Must start with letter
    if not user_id[0].isalpha():
        return False
    
    # Only alphanumeric, underscore, hyphen
    return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', user_id))


def validate_code(code: str, max_length: int = 100000) -> tuple[bool, Optional[str]]:
    """
    Validate code for obvious security issues
    
    Args:
        code: Code to validate
        max_length: Maximum allowed length
        
    Returns:
        (is_valid, error_message)
    """
    if not code or not isinstance(code, str):
        return False, "Code must be non-empty string"
    
    if len(code) > max_length:
        return False, f"Code exceeds maximum length of {max_length}"
    
    # Check for obviously dangerous patterns
    dangerous_patterns = [
        ('rm -rf', 'Dangerous file deletion'),
        (':(){ :|:& };:', 'Fork bomb'),
        ('/dev/sd', 'Direct disk access'),
        ('mkfs.', 'Filesystem formatting'),
        ('dd if=', 'Raw disk operations'),
    ]
    
    code_lower = code.lower()
    for pattern, reason in dangerous_patterns:
        if pattern in code_lower:
            return False, f"Potentially dangerous code: {reason}"
    
    return True, None


def sanitize_input(value: Any, max_length: int = 1000) -> str:
    """
    Sanitize string input
    
    Args:
        value: Value to sanitize
        max_length: Maximum length
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        value = str(value)
    
    # Remove null bytes and control characters
    value = value.replace('\x00', '')
    value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')
    
    # Limit length
    return value[:max_length]


# ============================================================================
# Formatting
# ============================================================================

def format_bytes(bytes_val: int) -> str:
    """
    Format bytes to human-readable string
    
    Args:
        bytes_val: Number of bytes
        
    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} PB"


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "2h 15m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    seconds = seconds % 60
    
    if minutes < 60:
        return f"{minutes}m {seconds:.0f}s"
    
    hours = minutes // 60
    minutes = minutes % 60
    
    return f"{hours}h {minutes}m {seconds:.0f}s"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format percentage"""
    return f"{value:.{decimals}f}%"


# ============================================================================
# ID Generation
# ============================================================================

def generate_id(prefix: str = "") -> str:
    """
    Generate unique ID
    
    Args:
        prefix: Optional prefix for ID
        
    Returns:
        Unique identifier string
    """
    unique_id = str(uuid.uuid4())
    return f"{prefix}{unique_id}" if prefix else unique_id


def generate_short_id(length: int = 8) -> str:
    """
    Generate short unique ID
    
    Args:
        length: Length of ID
        
    Returns:
        Short ID string
    """
    return uuid.uuid4().hex[:length]


# ============================================================================
# Error Handling
# ============================================================================

def safe_get(dictionary: dict, *keys, default=None):
    """
    Safely get nested dictionary value
    
    Args:
        dictionary: Dictionary to search
        *keys: Keys to traverse
        default: Default value if not found
        
    Returns:
        Value or default
    
    Example:
        safe_get(data, 'user', 'profile', 'name', default='Unknown')
    """
    current = dictionary
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default
    return current


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert to integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# ============================================================================
# Logging Helpers
# ============================================================================

def log_function_call(func):
    """Decorator to log function calls"""
    def wrapper(*args, **kwargs):
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} returned {result}")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} raised {type(e).__name__}: {e}")
            raise
    return wrapper


# ============================================================================
# Rate Limiting Helpers
# ============================================================================

class RateLimitTracker:
    """Simple rate limit tracker"""
    
    def __init__(self, max_requests: int, time_window: float):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}
    
    def is_allowed(self, key: str) -> bool:
        """
        Check if request is allowed
        
        Args:
            key: Unique identifier for rate limiting
            
        Returns:
            True if allowed, False if rate limited
        """
        current_time = now()
        
        # Initialize or clean old requests
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove requests outside time window
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if current_time - req_time < self.time_window
        ]
        
        # Check limit
        if len(self.requests[key]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[key].append(current_time)
        return True
    
    def reset(self, key: str):
        """Reset rate limit for key"""
        self.requests.pop(key, None)


# ============================================================================
# Configuration Helpers
# ============================================================================

def load_env_file(filepath: str = ".env") -> dict:
    """
    Load environment variables from file
    
    Args:
        filepath: Path to .env file
        
    Returns:
        Dictionary of environment variables
    """
    import os
    from pathlib import Path
    
    env_vars = {}
    env_path = Path(filepath)
    
    if not env_path.exists():
        return env_vars
    
    try:
        with open(env_path) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    env_vars[key] = value
                    # Also set in os.environ
                    os.environ.setdefault(key, value)
                else:
                    logger.warning(f"Invalid line {line_num} in {filepath}: {line}")
    
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
    
    return env_vars


# ============================================================================
# Retry Helpers
# ============================================================================

def retry_with_backoff(
    func,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry function with exponential backoff
    
    Args:
        func: Function to retry
        max_attempts: Maximum retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Backoff multiplier
        exceptions: Exceptions to catch
        
    Returns:
        Function result
        
    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            if attempt < max_attempts - 1:
                logger.warning(
                    f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(f"All {max_attempts} attempts failed")
    
    raise last_exception
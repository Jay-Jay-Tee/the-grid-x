"""
Grid-X Common Constants
Shared constants across coordinator and worker modules
"""

# ============================================================================
# Default Values
# ============================================================================

DEFAULT_TIMEOUT = 300  # seconds
DEFAULT_CPU_CORES = 1
DEFAULT_MEMORY_MB = 512
DEFAULT_MAX_WORKERS = 100

# ============================================================================
# Status Constants
# ============================================================================

# Job statuses
STATUS_QUEUED = "queued"
STATUS_ASSIGNED = "assigned"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"

# Worker statuses
WORKER_STATUS_IDLE = "idle"
WORKER_STATUS_BUSY = "busy"
WORKER_STATUS_OFFLINE = "offline"

# ============================================================================
# Language Support
# ============================================================================

SUPPORTED_LANGUAGES = ["python", "javascript", "node", "bash"]
DEFAULT_LANGUAGE = "python"

# Docker images for each language
DOCKER_IMAGES = {
    'python': 'python:3.9-slim',
    'node': 'node:18-slim',
    'javascript': 'node:18-slim',
    'bash': 'ubuntu:22.04',
}

# ============================================================================
# Credit System
# ============================================================================

DEFAULT_JOB_COST = 1.0
DEFAULT_WORKER_REWARD = 0.8
DEFAULT_INITIAL_CREDITS = 100.0

# ============================================================================
# Resource Limits
# ============================================================================

# CPU
MIN_CPU_CORES = 0.1
MAX_CPU_CORES = 32
DEFAULT_CPU_QUOTA = 1.0

# Memory
MIN_MEMORY_MB = 64
MAX_MEMORY_MB = 16384  # 16GB
DEFAULT_MEMORY_MB = 512

# Timeout
MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 3600  # 1 hour
DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes

# ============================================================================
# Network/Connection
# ============================================================================

# Ports
DEFAULT_HTTP_PORT = 8081
DEFAULT_WS_PORT = 8080

# Timeouts
WS_PING_INTERVAL = 20  # seconds
WS_PING_TIMEOUT = 20  # seconds
WS_CLOSE_TIMEOUT = 5  # seconds
HTTP_REQUEST_TIMEOUT = 10  # seconds

# Retry settings
MAX_RECONNECT_ATTEMPTS = 10
RECONNECT_DELAY_SECONDS = 5
MAX_RECONNECT_DELAY_SECONDS = 60

# ============================================================================
# Database
# ============================================================================

DB_DEFAULT_PATH = "gridx.db"
DB_MAX_CONNECTIONS = 10
DB_CONNECTION_TIMEOUT = 5  # seconds

# ============================================================================
# Security
# ============================================================================

# Input validation
MAX_CODE_LENGTH = 100000  # 100KB
MAX_USER_ID_LENGTH = 64
MAX_JOB_ID_LENGTH = 128
MAX_WORKER_ID_LENGTH = 128

# Authentication
AUTH_TOKEN_LENGTH = 64  # SHA256 hex
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

# ============================================================================
# Docker Security
# ============================================================================

# Container limits
CONTAINER_CPU_PERIOD = 100000
CONTAINER_DEFAULT_USER = "1000:1000"
CONTAINER_TMP_SIZE = "100m"
CONTAINER_WORKING_DIR = "/workspace"

# Capabilities to drop
DOCKER_DROP_ALL_CAPS = True
DOCKER_MINIMAL_CAPS = ['CHOWN', 'SETGID', 'SETUID']

# Security options
DOCKER_NO_NEW_PRIVILEGES = True
DOCKER_READ_ONLY_ROOT = True
DOCKER_NETWORK_DISABLED = True

# ============================================================================
# Logging
# ============================================================================

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# ============================================================================
# Queue Settings
# ============================================================================

MAX_QUEUE_SIZE = 1000
MAX_COMPLETED_TASKS = 100
TASK_POLL_INTERVAL = 0.5  # seconds

# ============================================================================
# Environment Variables
# ============================================================================

ENV_HTTP_PORT = "GRIDX_HTTP_PORT"
ENV_WS_PORT = "GRIDX_WS_PORT"
ENV_DB_PATH = "GRIDX_DB_PATH"
ENV_INITIAL_CREDITS = "GRIDX_INITIAL_CREDITS"
ENV_JOB_COST = "GRIDX_JOB_COST"
ENV_WORKER_REWARD = "GRIDX_WORKER_REWARD"
ENV_DOCKER_SOCKET = "GRIDX_DOCKER_SOCKET"
ENV_LOG_LEVEL = "GRIDX_LOG_LEVEL"
ENV_WORKSPACE = "GRIDX_WORKSPACE"

# ============================================================================
# Error Messages
# ============================================================================

ERROR_INSUFFICIENT_CREDITS = "Insufficient credits"
ERROR_INVALID_JOB_ID = "Invalid job ID format"
ERROR_INVALID_USER_ID = "Invalid user ID format"
ERROR_JOB_NOT_FOUND = "Job not found"
ERROR_WORKER_NOT_FOUND = "Worker not found"
ERROR_AUTH_FAILED = "Authentication failed"
ERROR_INVALID_CODE = "Invalid or dangerous code detected"
ERROR_UNSUPPORTED_LANGUAGE = "Unsupported language"
ERROR_TIMEOUT = "Task execution timeout"
ERROR_CONTAINER_FAILED = "Container execution failed"

# ============================================================================
# Success Messages
# ============================================================================

MSG_JOB_SUBMITTED = "Job submitted successfully"
MSG_WORKER_REGISTERED = "Worker registered successfully"
MSG_CREDITS_ADDED = "Credits added successfully"
MSG_CREDITS_DEDUCTED = "Credits deducted successfully"
"""Grid-X Common Constants

This module contains all shared constants used across coordinator and worker modules.
"""

# ============================================================================
# DEFAULT VALUES
# ============================================================================

DEFAULT_TIMEOUT = 300  # seconds
DEFAULT_CPU_CORES = 1
DEFAULT_MEMORY_MB = 512
DEFAULT_MEMORY_BYTES = DEFAULT_MEMORY_MB * 1024 * 1024

# ============================================================================
# STATUS CONSTANTS
# ============================================================================

# Job statuses
STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"

# Worker statuses
WORKER_STATUS_IDLE = "idle"
WORKER_STATUS_BUSY = "busy"
WORKER_STATUS_OFFLINE = "offline"

# Task statuses
TASK_STATUS_PENDING = "pending"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"

# ============================================================================
# LANGUAGE SUPPORT
# ============================================================================

SUPPORTED_LANGUAGES = ["python", "javascript", "node", "bash"]
DEFAULT_LANGUAGE = "python"

# Docker images for each language
DOCKER_IMAGES = {
    'python': 'python:3.11-slim',
    'node': 'node:20-slim',
    'javascript': 'node:20-slim',
    'bash': 'ubuntu:22.04',
}

# File extensions for each language
LANGUAGE_EXTENSIONS = {
    'python': '.py',
    'javascript': '.js',
    'node': '.js',
    'bash': '.sh',
}

# ============================================================================
# CREDIT SYSTEM
# ============================================================================

DEFAULT_JOB_COST = 1.0
DEFAULT_WORKER_REWARD = 0.8
DEFAULT_INITIAL_CREDITS = 100.0
MINIMUM_CREDIT_BALANCE = 0.0

# ============================================================================
# NETWORK & CONNECTION
# ============================================================================

DEFAULT_HTTP_PORT = 8081
DEFAULT_WS_PORT = 8080
DEFAULT_COORDINATOR_IP = "localhost"

# Timeouts
CONNECTION_TIMEOUT = 10  # seconds
HEARTBEAT_INTERVAL = 30  # seconds
HEARTBEAT_TIMEOUT = 90  # seconds (3 missed heartbeats)
WEBSOCKET_PING_INTERVAL = 20  # seconds

# ============================================================================
# RESOURCE LIMITS
# ============================================================================

# Per-job limits
MAX_CPU_CORES = 8
MAX_MEMORY_GB = 16
MAX_DISK_GB = 10
MAX_EXECUTION_TIME = 3600  # 1 hour

# Queue limits
MAX_QUEUE_SIZE = 1000
MAX_COMPLETED_TASKS = 100

# ============================================================================
# SECURITY
# ============================================================================

# Password requirements
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

# Input validation
MAX_USER_ID_LENGTH = 64
MAX_CODE_LENGTH = 1_000_000  # 1MB
MAX_OUTPUT_LENGTH = 10_000_000  # 10MB

# Rate limiting
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 60  # seconds

# ============================================================================
# DOCKER CONFIGURATION
# ============================================================================

# Security settings
DOCKER_NETWORK_DISABLED = True
DOCKER_READONLY_ROOT = True
DOCKER_NO_NEW_PRIVILEGES = True
DOCKER_DROP_ALL_CAPABILITIES = True

# Resource limits
DOCKER_CPU_QUOTA = 100000  # 1 CPU core
DOCKER_CPU_PERIOD = 100000
DOCKER_MEMORY_LIMIT = "512m"
DOCKER_PIDS_LIMIT = 100

# Cleanup
DOCKER_REMOVE_AFTER = True
DOCKER_AUTO_REMOVE = True

# ============================================================================
# DATABASE
# ============================================================================

DEFAULT_DB_PATH = "./data/gridx.db"
DB_CONNECTION_TIMEOUT = 30  # seconds

# ============================================================================
# LOGGING
# ============================================================================

LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"
LOG_LEVEL_CRITICAL = "CRITICAL"

DEFAULT_LOG_LEVEL = LOG_LEVEL_INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ============================================================================
# API & HTTP
# ============================================================================

# API versioning
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# HTTP status codes (for clarity)
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_PAYMENT_REQUIRED = 402
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_INTERNAL_ERROR = 500

# ============================================================================
# WORKER CONFIGURATION
# ============================================================================

# Worker capabilities
DEFAULT_WORKER_CAPABILITIES = {
    "cpu_cores": DEFAULT_CPU_CORES,
    "memory_mb": DEFAULT_MEMORY_MB,
    "gpu_count": 0,
    "gpu_memory_mb": 0,
}

# Task execution
MAX_CONCURRENT_TASKS = 5
TASK_POLL_INTERVAL = 1.0  # seconds

# ============================================================================
# MONITORING
# ============================================================================

METRICS_UPDATE_INTERVAL = 5  # seconds
RESOURCE_SAMPLE_INTERVAL = 1  # seconds

# ============================================================================
# MISCELLANEOUS
# ============================================================================

# Application metadata
APP_NAME = "Grid-X"
APP_DESCRIPTION = "Decentralized Distributed Computing Platform"
APP_VERSION = "1.0.0"

# Environment variable names
ENV_HTTP_PORT = "GRIDX_HTTP_PORT"
ENV_WS_PORT = "GRIDX_WS_PORT"
ENV_COORDINATOR_WS = "COORDINATOR_WS"
ENV_DB_PATH = "GRIDX_DB_PATH"
ENV_LOG_LEVEL = "GRIDX_LOG_LEVEL"

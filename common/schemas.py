"""Grid-X Common Data Schemas

This module contains shared data schemas and models used across the platform.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class JobStatus(str, Enum):
    """Job execution status"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkerStatus(str, Enum):
    """Worker availability status"""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Language(str, Enum):
    """Supported programming languages"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    NODE = "node"
    BASH = "bash"


# ============================================================================
# JOB SCHEMAS
# ============================================================================

@dataclass
class JobLimits:
    """Resource limits for job execution"""
    cpu_cores: int = 1
    memory_mb: int = 512
    timeout_seconds: int = 300
    max_output_bytes: int = 10_000_000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobLimits':
        """Create from dictionary"""
        return cls(
            cpu_cores=data.get('cpu_cores', 1),
            memory_mb=data.get('memory_mb', 512),
            timeout_seconds=data.get('timeout_seconds', 300),
            max_output_bytes=data.get('max_output_bytes', 10_000_000)
        )


@dataclass
class JobSchema:
    """Standard job schema"""
    job_id: str
    user_id: str
    code: str
    language: str = "python"
    status: str = JobStatus.QUEUED.value
    worker_id: Optional[str] = None
    created_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    limits: Optional[Dict[str, Any]] = None
    cost: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.job_id,
            'user_id': self.user_id,
            'code': self.code,
            'language': self.language,
            'status': self.status,
            'worker_id': self.worker_id,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'stdout': self.stdout,
            'stderr': self.stderr,
            'exit_code': self.exit_code,
            'error_message': self.error_message,
            'limits': self.limits,
            'cost': self.cost
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobSchema':
        """Create from dictionary"""
        return cls(
            job_id=data.get('id') or data.get('job_id', ''),
            user_id=data.get('user_id', ''),
            code=data.get('code', ''),
            language=data.get('language', 'python'),
            status=data.get('status', JobStatus.QUEUED.value),
            worker_id=data.get('worker_id'),
            created_at=data.get('created_at'),
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            stdout=data.get('stdout', ''),
            stderr=data.get('stderr', ''),
            exit_code=data.get('exit_code'),
            error_message=data.get('error_message'),
            limits=data.get('limits'),
            cost=data.get('cost', 1.0)
        )


@dataclass
class JobSubmission:
    """Job submission request"""
    code: str
    language: str = "python"
    user_id: str = "demo"
    limits: Optional[Dict[str, Any]] = None
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate job submission"""
        if not self.code or not isinstance(self.code, str):
            return False, "Code is required and must be a string"
        
        if len(self.code) > 1_000_000:
            return False, "Code exceeds maximum length of 1MB"
        
        if self.language not in ['python', 'javascript', 'node', 'bash']:
            return False, f"Unsupported language: {self.language}"
        
        return True, None


# ============================================================================
# WORKER SCHEMAS
# ============================================================================

@dataclass
class WorkerCapabilities:
    """Worker hardware capabilities"""
    cpu_cores: int = 1
    memory_mb: int = 512
    gpu_count: int = 0
    gpu_memory_mb: int = 0
    disk_gb: int = 10
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkerCapabilities':
        """Create from dictionary"""
        return cls(
            cpu_cores=data.get('cpu_cores', 1),
            memory_mb=data.get('memory_mb', 512),
            gpu_count=data.get('gpu_count', 0),
            gpu_memory_mb=data.get('gpu_memory_mb', 0),
            disk_gb=data.get('disk_gb', 10)
        )


@dataclass
class WorkerSchema:
    """Standard worker schema"""
    id: str
    owner_id: str
    status: str = WorkerStatus.IDLE.value
    ip_address: str = "unknown"
    capabilities: Optional[Dict[str, Any]] = None
    auth_token: Optional[str] = None
    last_heartbeat: Optional[float] = None
    registered_at: Optional[float] = None
    current_job_id: Optional[str] = None
    jobs_completed: int = 0
    credits_earned: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'owner_id': self.owner_id,
            'status': self.status,
            'ip_address': self.ip_address,
            'capabilities': self.capabilities,
            'auth_token': self.auth_token,
            'last_heartbeat': self.last_heartbeat,
            'registered_at': self.registered_at,
            'current_job_id': self.current_job_id,
            'jobs_completed': self.jobs_completed,
            'credits_earned': self.credits_earned
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkerSchema':
        """Create from dictionary"""
        return cls(
            id=data.get('id', ''),
            owner_id=data.get('owner_id', ''),
            status=data.get('status', WorkerStatus.IDLE.value),
            ip_address=data.get('ip_address', 'unknown'),
            capabilities=data.get('capabilities'),
            auth_token=data.get('auth_token'),
            last_heartbeat=data.get('last_heartbeat'),
            registered_at=data.get('registered_at'),
            current_job_id=data.get('current_job_id'),
            jobs_completed=data.get('jobs_completed', 0),
            credits_earned=data.get('credits_earned', 0.0)
        )


# ============================================================================
# CREDIT SCHEMAS
# ============================================================================

@dataclass
class CreditBalance:
    """User credit balance"""
    user_id: str
    balance: float = 100.0
    total_earned: float = 0.0
    total_spent: float = 0.0
    last_updated: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CreditBalance':
        """Create from dictionary"""
        return cls(
            user_id=data.get('user_id', ''),
            balance=data.get('balance', 100.0),
            total_earned=data.get('total_earned', 0.0),
            total_spent=data.get('total_spent', 0.0),
            last_updated=data.get('last_updated')
        )


@dataclass
class CreditTransaction:
    """Credit transaction record"""
    transaction_id: str
    user_id: str
    amount: float
    transaction_type: str  # 'debit', 'credit', 'transfer'
    description: str
    timestamp: float
    related_job_id: Optional[str] = None
    related_worker_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


# ============================================================================
# TASK SCHEMAS
# ============================================================================

@dataclass
class TaskSchema:
    """Task execution schema"""
    task_id: str
    job_id: str
    status: str = TaskStatus.PENDING.value
    created_at: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    priority: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskSchema':
        """Create from dictionary"""
        return cls(
            task_id=data.get('task_id', ''),
            job_id=data.get('job_id', ''),
            status=data.get('status', TaskStatus.PENDING.value),
            created_at=data.get('created_at', 0.0),
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            result=data.get('result'),
            error=data.get('error'),
            priority=data.get('priority', 0)
        )


# ============================================================================
# WEBSOCKET MESSAGE SCHEMAS
# ============================================================================

@dataclass
class WebSocketMessage:
    """WebSocket message schema"""
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'type': self.type,
            'data': self.data,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebSocketMessage':
        """Create from dictionary"""
        return cls(
            type=data.get('type', ''),
            data=data.get('data', {}),
            timestamp=data.get('timestamp')
        )


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

@dataclass
class ApiResponse:
    """Standard API response"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'success': self.success
        }
        if self.data is not None:
            result['data'] = self.data
        if self.error is not None:
            result['error'] = self.error
        if self.timestamp is not None:
            result['timestamp'] = self.timestamp
        return result


@dataclass
class ErrorResponse:
    """Error response schema"""
    error: str
    code: int
    details: Optional[str] = None
    timestamp: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'error': self.error,
            'code': self.code
        }
        if self.details:
            result['details'] = self.details
        if self.timestamp:
            result['timestamp'] = self.timestamp
        return result

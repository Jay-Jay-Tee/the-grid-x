"""
Task Queue - Manages task queuing and priority scheduling
"""

import asyncio
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid


class TaskPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Task definition"""
    task_id: str
    code: str
    language: str
    requirements: Dict  # Resource requirements
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: int = 300  # seconds
    created_at: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.PENDING
    assigned_worker: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


class TaskQueue:
    """Priority-based task queue"""
    
    def __init__(self, max_queue_size: int = 1000):
        self.max_queue_size = max_queue_size
        self.queue: List[Task] = []
        self.active_tasks: Dict[str, Task] = {}
        self.completed_tasks: Dict[str, Task] = {}
        self._lock = asyncio.Lock()
        self._queue_event = asyncio.Event()
    
    async def enqueue(self, task: Task) -> bool:
        """Add task to queue"""
        async with self._lock:
            if len(self.queue) >= self.max_queue_size:
                return False
            
            task.status = TaskStatus.QUEUED
            self.queue.append(task)
            
            # Sort by priority (higher priority first)
            self.queue.sort(key=lambda t: t.priority.value, reverse=True)
            
            self._queue_event.set()
            return True
    
    async def dequeue(self) -> Optional[Task]:
        """Get next task from queue"""
        async with self._lock:
            if not self.queue:
                self._queue_event.clear()
                return None
            
            task = self.queue.pop(0)
            task.status = TaskStatus.RUNNING
            self.active_tasks[task.task_id] = task
            
            return task

    async def mark_running(self, task_id: str) -> bool:
        """Mark a queued task as running (move from queue -> active_tasks).

        This is provided for callers that reserve tasks without using `dequeue()`.
        Returns True if the task was found and marked running, False otherwise.
        """
        async with self._lock:
            for i, task in enumerate(self.queue):
                if task.task_id == task_id:
                    task = self.queue.pop(i)
                    task.status = TaskStatus.RUNNING
                    self.active_tasks[task.task_id] = task
                    return True
            return False
    
    async def mark_completed(self, task_id: str, result: Optional[Dict] = None):
        """Mark task as completed"""
        async with self._lock:
            if task_id in self.active_tasks:
                task = self.active_tasks.pop(task_id)
                task.status = TaskStatus.COMPLETED
                task.result = result
                self.completed_tasks[task_id] = task
    
    async def mark_failed(self, task_id: str, error: str, result: Optional[Dict] = None):
        """Mark task as failed. Optional result can include duration_seconds for time-based credits."""
        async with self._lock:
            if task_id in self.active_tasks:
                task = self.active_tasks.pop(task_id)
                task.status = TaskStatus.FAILED
                task.error = error
                if result is not None:
                    task.result = result
                self.completed_tasks[task_id] = task
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        async with self._lock:
            # Remove from queue if pending
            for i, task in enumerate(self.queue):
                if task.task_id == task_id:
                    task.status = TaskStatus.CANCELLED
                    self.queue.pop(i)
                    return True
            
            # Cancel active task
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                task.status = TaskStatus.CANCELLED
                del self.active_tasks[task_id]
                return True
            
            return False
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        # Check queue
        for task in self.queue:
            if task.task_id == task_id:
                return task
        
        # Check active
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        
        # Check completed
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id]
        
        return None
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return len(self.queue)
    
    def get_active_count(self) -> int:
        """Get number of active tasks"""
        return len(self.active_tasks)
    
    async def wait_for_task(self, timeout: Optional[float] = None):
        """Wait for a task to be available"""
        try:
            await asyncio.wait_for(self._queue_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
    
    def get_stats(self) -> Dict:
        """Get queue statistics"""
        return {
            'queue_size': len(self.queue),
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'total_tasks': len(self.queue) + len(self.active_tasks) + len(self.completed_tasks),
        }


class TaskDistributor:
    """Distributes tasks across multiple workers"""
    
    def __init__(self, task_queue: TaskQueue):
        self.task_queue = task_queue
        self.workers: Dict[str, Dict] = {}  # worker_id -> worker_info
        self.worker_capacities: Dict[str, int] = {}  # worker_id -> capacity
    
    def register_worker(self, worker_id: str, capacity: int, info: Dict):
        """Register a worker"""
        self.workers[worker_id] = info
        self.worker_capacities[worker_id] = capacity
    
    def unregister_worker(self, worker_id: str):
        """Unregister a worker"""
        if worker_id in self.workers:
            del self.workers[worker_id]
        if worker_id in self.worker_capacities:
            del self.worker_capacities[worker_id]
    
    async def assign_task_to_worker(self, task: Task, worker_id: str) -> bool:
        """Assign a task to a specific worker"""
        if worker_id not in self.workers:
            return False
        
        task.assigned_worker = worker_id
        return True
    
    def find_best_worker(self, requirements: Dict) -> Optional[str]:
        """Find best worker for given requirements"""
        # Simple implementation: find worker with highest capacity
        # In production, this would consider resource availability, pricing, etc.
        best_worker = None
        best_capacity = 0
        
        for worker_id, capacity in self.worker_capacities.items():
            if capacity > best_capacity:
                best_capacity = capacity
                best_worker = worker_id
        
        return best_worker


if __name__ == '__main__':
    # Test task queue
    async def test():
        queue = TaskQueue()
        
        # Create test tasks
        task1 = Task(
            task_id=str(uuid.uuid4()),
            code="print('Hello')",
            language="python",
            requirements={"cpu": {"cores": 1}},
            priority=TaskPriority.HIGH
        )
        
        task2 = Task(
            task_id=str(uuid.uuid4()),
            code="print('World')",
            language="python",
            requirements={"cpu": {"cores": 1}},
            priority=TaskPriority.LOW
        )
        
        # Enqueue tasks
        await queue.enqueue(task1)
        await queue.enqueue(task2)
        
        print(f"Queue size: {queue.get_queue_size()}")
        
        # Dequeue (should get high priority first)
        task = await queue.dequeue()
        print(f"Dequeued task: {task.task_id}, priority: {task.priority}")
        
        # Mark completed
        await queue.mark_completed(task.task_id, {"output": "Hello"})
        
        print(f"Stats: {queue.get_stats()}")
    
    asyncio.run(test())

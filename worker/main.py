"""
Grid-X Worker Main Entry Point
"""

import asyncio
import signal
import sys
from resource_monitor import ResourceMonitor
from resource_advertiser import ResourceAdvertiser
from docker_manager import DockerManager
from task_queue import TaskQueue
from task_executor import TaskExecutor


class GridXWorker:
    """Main worker daemon"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.running = False
        
        # Initialize components
        self.resource_monitor = ResourceMonitor(
            update_interval=self.config.get('monitor_interval', 5.0)
        )
        self.resource_advertiser = ResourceAdvertiser(
            self.resource_monitor,
            api_endpoint=self.config.get('api_endpoint', 'http://localhost:3000'),
            update_interval=self.config.get('advertise_interval', 30.0)
        )
        self.docker_manager = DockerManager()
        self.task_queue = TaskQueue(
            max_queue_size=self.config.get('max_queue_size', 1000)
        )
        self.task_executor = TaskExecutor(self.docker_manager, self.task_queue)
    
    async def start(self):
        """Start the worker"""
        print("Starting Grid-X Worker...")
        self.running = True
        
        # Start resource monitoring
        monitor_task = asyncio.create_task(
            self.resource_monitor.start_monitoring()
        )
        
        # Start resource advertising
        advertiser_task = asyncio.create_task(
            self.resource_advertiser.start_advertising()
        )
        
        # Start task executor
        executor_task = asyncio.create_task(
            self.task_executor.start_executor(
                max_concurrent=self.config.get('max_concurrent_tasks', 5)
            )
        )
        
        print("Worker started successfully")
        print(f"Peer ID: {self.config.get('peer_id', 'N/A')}")
        
        # Wait for all tasks
        try:
            await asyncio.gather(monitor_task, advertiser_task, executor_task)
        except asyncio.CancelledError:
            print("Worker shutting down...")
    
    async def stop(self):
        """Stop the worker"""
        print("Stopping Grid-X Worker...")
        self.running = False
        
        # Stop components
        self.resource_monitor.stop_monitoring()
        self.resource_advertiser.stop_advertising()
        self.task_executor.stop_executor()
        
        # Clean up Docker containers
        await self.docker_manager.cleanup_all()
        
        print("Worker stopped")
    
    def handle_task_request(self, task_request: dict):
        """Handle incoming task request"""
        from task_queue import Task, TaskPriority
        
        task = Task(
            task_id=task_request.get('taskId'),
            code=task_request.get('code'),
            language=task_request.get('language', 'python'),
            requirements=task_request.get('requirements', {}),
            priority=TaskPriority.NORMAL,
            timeout=task_request.get('timeout', 300)
        )
        
        # Check if resources are available
        if self.resource_advertiser.reserve_resources(task.requirements):
            asyncio.create_task(self.task_queue.enqueue(task))
            return {'status': 'accepted', 'taskId': task.task_id}
        else:
            return {'status': 'rejected', 'reason': 'Insufficient resources'}


async def main():
    """Main entry point"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    config = {
        'monitor_interval': float(os.getenv('MONITOR_INTERVAL', '5.0')),
        'advertise_interval': float(os.getenv('ADVERTISE_INTERVAL', '30.0')),
        'api_endpoint': os.getenv('API_ENDPOINT', 'http://localhost:3000'),
        'max_queue_size': int(os.getenv('MAX_QUEUE_SIZE', '1000')),
        'max_concurrent_tasks': int(os.getenv('MAX_CONCURRENT_TASKS', '5')),
        'peer_id': os.getenv('PEER_ID', ''),
    }
    
    worker = GridXWorker(config)
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        print("\nReceived shutdown signal")
        asyncio.create_task(worker.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        await worker.stop()


if __name__ == '__main__':
    asyncio.run(main())

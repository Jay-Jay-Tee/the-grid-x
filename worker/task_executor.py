"""
Task Executor - Executes tasks in Docker containers
"""

import asyncio
import os
import tempfile
import shutil
import logging
from typing import Dict, Callable, List
from task_queue import Task, TaskQueue
from docker_manager import DockerManager, ContainerConfig

# Module logger
logger = logging.getLogger(__name__)


class TaskExecutor:
    """Executes tasks in secure Docker containers"""
    
    def __init__(self, docker_manager: DockerManager, task_queue: TaskQueue):
        self.docker_manager = docker_manager
        self.task_queue = task_queue
        self.running = False
        self.execution_handlers: Dict[str, Callable] = {}
        self._execution_tasks: Dict[str, asyncio.Task] = {}
    
    def register_language_handler(self, language: str, handler: Callable):
        """Register a handler for a specific language"""
        self.execution_handlers[language.lower()] = handler
    
    def _get_docker_image(self, language: str) -> str:
        """Get Docker image for language"""
        images = {
            'python': 'python:3.9-slim',
            'node': 'node:18-slim',
            'bash': 'ubuntu:22.04',
            'javascript': 'node:18-slim',
        }
        return images.get(language.lower(), 'python:3.9-slim')
    
    def _prepare_task_code(self, task: Task, workspace_dir: str) -> tuple[str, List[str]]:
        """Prepare task code for execution"""
        language = task.language.lower()
        
        if language == 'python':
            code_file = os.path.join(workspace_dir, 'task.py')
            with open(code_file, 'w') as f:
                f.write(task.code)
            return code_file, ['python', 'task.py']
        
        elif language in ['javascript', 'node']:
            code_file = os.path.join(workspace_dir, 'task.js')
            with open(code_file, 'w') as f:
                f.write(task.code)
            return code_file, ['node', 'task.js']
        
        elif language == 'bash':
            code_file = os.path.join(workspace_dir, 'task.sh')
            with open(code_file, 'w') as f:
                f.write(task.code)
            # Only set executable bit on non-Windows platforms
            if os.name != 'nt':
                os.chmod(code_file, 0o755)
            return code_file, ['bash', 'task.sh']
        
        else:
            # Default to Python
            code_file = os.path.join(workspace_dir, 'task.py')
            with open(code_file, 'w') as f:
                f.write(task.code)
            return code_file, ['python', 'task.py']
    
    async def execute_task(self, task: Task) -> Dict:
        """Execute a task in a Docker container"""
        try:
            # Check if custom handler exists (case-insensitive)
            lang = (task.language or '').lower()
            if lang in self.execution_handlers:
                return await self.execution_handlers[lang](task)
            
            # Default Docker execution
            return await self._execute_in_docker(task)
        
        except Exception as e:
            error_msg = f"Task execution error: {str(e)}"
            await self.task_queue.mark_failed(task.task_id, error_msg)
            return {
                'status': 'failed',
                'error': error_msg
            }
    
    async def _execute_in_docker(self, task: Task) -> Dict:
        """Execute task in Docker container"""
        container_id = f"task-{task.task_id}"
        created_container = False
        workspace_volume = None

        try:
            # Determine resource limits from requirements
            cpu_limit = task.requirements.get('cpu', {}).get('cores', 1)
            memory_limit = f"{task.requirements.get('memory', {}).get('totalGB', 1) * 1024}m"
            gpu_count = task.requirements.get('gpu', {}).get('count', 0)
            
            # Create container config
            config = ContainerConfig(
                image=self._get_docker_image(task.language),
                cpu_limit=float(cpu_limit),
                memory_limit=memory_limit,
                gpu_count=gpu_count if gpu_count > 0 else None,
                read_only=True,
                network_disabled=True,  # Disable network for security
                timeout=task.timeout,
            )
            
            # Prepare code in workspace (this happens in the container's volume)
            # We'll write the code to the deterministic workspace path used by DockerManager
            workspace_volume = os.path.join(tempfile.gettempdir(), "grid-x-workspace", task.task_id)
            os.makedirs(workspace_volume, exist_ok=True)

            code_file, command = self._prepare_task_code(task, workspace_volume)

            # Update container command before creation
            config.command = command

            # Create container and ensure it uses the same workspace path
            created_container_id, returned_workspace = await self.docker_manager.create_container(config, container_id, workspace_path=workspace_volume)
            # created_container_id should match container_id
            container_id = created_container_id
            created_container = True

            await self.docker_manager.start_container(container_id)
            
            # Wait for completion with timeout
            result = await asyncio.wait_for(
                self.docker_manager.wait_for_container(container_id, timeout=task.timeout),
                timeout=task.timeout + 10
            )
            
            # Get logs/output
            logs = await self.docker_manager.get_container_logs(container_id, tail=1000)
            
            # Get stats
            stats = await self.docker_manager.get_container_stats(container_id)
            
            # Clean up
            try:
                await self.docker_manager.remove_container(container_id)
            except Exception:
                logger.exception("Failed to remove container %s", container_id)
            # Remove host workspace (best-effort)
            if workspace_volume:
                try:
                    shutil.rmtree(workspace_volume, ignore_errors=True)
                except Exception:
                    logger.exception("Failed to remove workspace %s", workspace_volume)
            
            # Parse result
            if result['exit_code'] == 0:
                await self.task_queue.mark_completed(task.task_id, {
                    'output': logs,
                    'stats': stats
                })
                return {
                    'status': 'completed',
                    'output': logs,
                    'stats': stats
                }
            else:
                error_msg = f"Task failed with exit code {result['exit_code']}"
                await self.task_queue.mark_failed(task.task_id, error_msg)
                return {
                    'status': 'failed',
                    'exit_code': result['exit_code'],
                    'error': logs or error_msg
                }
        
        except asyncio.TimeoutError:
            # Stop/remove only if container was created
            if created_container:
                try:
                    await self.docker_manager.stop_container(container_id)
                except Exception:
                    logger.exception("Failed to stop container %s on timeout", container_id)
                try:
                    await self.docker_manager.remove_container(container_id)
                except Exception:
                    logger.exception("Failed to remove container %s on timeout", container_id)
            # Remove workspace
            if workspace_volume:
                try:
                    shutil.rmtree(workspace_volume, ignore_errors=True)
                except Exception:
                    logger.exception("Failed to remove workspace %s on timeout", workspace_volume)
            error_msg = "Task execution timeout"
            await self.task_queue.mark_failed(task.task_id, error_msg)
            return {
                'status': 'failed',
                'error': error_msg
            }
        
        except Exception as e:
            # Ensure cleanup
            try:
                if created_container:
                    await self.docker_manager.remove_container(container_id)
            except Exception:
                logger.exception("Error removing container during exception handling")
            if workspace_volume:
                try:
                    shutil.rmtree(workspace_volume, ignore_errors=True)
                except Exception:
                    logger.exception("Failed to remove workspace during exception handling %s", workspace_volume)
            
            error_msg = f"Execution error: {str(e)}"
            await self.task_queue.mark_failed(task.task_id, error_msg)
            return {
                'status': 'failed',
                'error': error_msg
            }
    
    async def start_executor(self, max_concurrent: int = 5):
        """Start task executor with concurrent execution"""
        self.running = True
        
        while self.running:
            # Wait for tasks
            await self.task_queue.wait_for_task(timeout=1.0)
            
            # Execute up to max_concurrent tasks
            active_count = len(self._execution_tasks)
            while active_count < max_concurrent:
                task = await self.task_queue.dequeue()
                if not task:
                    break

                # Schedule execution as a background task and track it
                execution_task = asyncio.create_task(self._execute_with_monitoring(task))
                self._execution_tasks[task.task_id] = execution_task

                # Ensure tasks are removed from tracking and exceptions are logged
                def _done_callback(t: asyncio.Task, tid=task.task_id):
                    try:
                        exc = t.exception()
                        if exc:
                            logger.exception("Task %s raised: %s", tid, exc)
                    except asyncio.CancelledError:
                        logger.info("Task %s cancelled", tid)
                    finally:
                        self._execution_tasks.pop(tid, None)

                execution_task.add_done_callback(_done_callback)
                active_count = len(self._execution_tasks)
            
            # Clean up completed execution tasks
            completed = [
                task_id for task_id, task in self._execution_tasks.items()
                if task.done()
            ]
            for task_id in completed:
                del self._execution_tasks[task_id]
            
            await asyncio.sleep(0.1)
    
    async def _execute_with_monitoring(self, task: Task):
        """Execute task with monitoring"""
        result = await self.execute_task(task)
        return result
    
    def stop_executor(self):
        """Stop task executor"""
        self.running = False
    
    async def cancel_execution(self, task_id: str) -> bool:
        """Cancel a running task"""
        # Cancel from queue
        cancelled = await self.task_queue.cancel_task(task_id)
        
        # Cancel execution task if running
        if task_id in self._execution_tasks:
            self._execution_tasks[task_id].cancel()
            del self._execution_tasks[task_id]
        
        return cancelled


if __name__ == '__main__':
    # Test task executor
    async def test():
        from docker_manager import DockerManager
        from task_queue import TaskQueue, TaskPriority
        
        docker_manager = DockerManager()
        task_queue = TaskQueue()
        executor = TaskExecutor(docker_manager, task_queue)
        
        # Create test task
        task = Task(
            task_id="test-123",
            code="print('Hello from Grid-X!')",
            language="python",
            requirements={"cpu": {"cores": 1}},
            priority=TaskPriority.NORMAL,
            timeout=30
        )
        
        # Enqueue
        await task_queue.enqueue(task)
        
        # Execute
        result = await executor.execute_task(task)
        print(f"Execution result: {result}")
    
    asyncio.run(test())

"""
Docker Manager - Creates and manages secure Docker containers for task execution
"""

import docker
import asyncio
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
import uuid
import json
import os

# scipy import removed; not required


@dataclass
class ContainerConfig:
    """Container configuration with security settings"""
    image: str
    command: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    cpu_limit: Optional[float] = None  # CPU cores
    memory_limit: Optional[str] = None  # e.g., "512m", "2g"
    gpu_count: Optional[int] = None
    network_disabled: bool = False
    read_only: bool = True
    user: Optional[str] = None  # Non-root user
    working_dir: str = "/workspace"
    timeout: Optional[int] = None  # seconds


class DockerManager:
    """Manages Docker containers with security isolation"""
    
    def __init__(self, docker_socket: Optional[str] = None):
        """
        Initialize Docker manager
        
        Args:
            docker_socket: Docker socket path (default: /var/run/docker.sock or from env)
        """
        self.client = None
        self.available = False
        
        try:
            self.client = docker.from_env() if not docker_socket else docker.DockerClient(base_url=docker_socket)
            # Test connection by getting server version
            self.client.version()
            self.available = True
        except Exception as e:
            # Docker is not available, but worker can still connect to coordinator
            import logging
            logging.warning(f"Docker not available: {e}. Worker will connect but cannot execute tasks.")
            self.client = None
            self.available = False
        
        self.containers: Dict[str, docker.models.containers.Container] = {}
        self._workspace_dir = "/tmp/grid-x-workspace"
        
        # Ensure workspace directory exists
        os.makedirs(self._workspace_dir, exist_ok=True)
    
    def _create_secure_config(self, config: ContainerConfig, workspace_path: Optional[str] = None) -> tuple[Dict[str, Any], str]:
        """Create secure Docker container configuration"""
        docker_config = {
            'image': config.image,
            'command': config.command,
            'environment': config.environment or {},
            'working_dir': config.working_dir,
            'detach': True,
            'auto_remove': False,  # We'll manage removal
            'network_disabled': config.network_disabled,
            'read_only': config.read_only,
            'security_opt': [
                'no-new-privileges:true',  # Prevent privilege escalation
            ],
            'cap_drop': ['ALL'],  # Drop all capabilities
            'cap_add': ['CHOWN', 'SETGID', 'SETUID'],  # Minimal capabilities
        }
        
        # Resource limits
        if config.cpu_limit:
            docker_config['cpu_quota'] = int(config.cpu_limit * 100000)  # Convert to quota
            docker_config['cpu_period'] = 100000
        
        if config.memory_limit:
            docker_config['mem_limit'] = config.memory_limit
        
        # GPU support
        if config.gpu_count and config.gpu_count > 0:
            docker_config['device_requests'] = [
                docker.types.DeviceRequest(
                    count=config.gpu_count,
                    capabilities=[['gpu']]
                )
            ]
        
        # User namespace (non-root)
        if config.user:
            docker_config['user'] = config.user
        else:
            # Use a non-root user (UID 1000)
            docker_config['user'] = '1000:1000'
        
        # Volume mounts - ONLY workspace directory, no host filesystem access
        if workspace_path:
            workspace_volume = workspace_path
        else:
            workspace_volume = f"{self._workspace_dir}/{uuid.uuid4()}"

        os.makedirs(workspace_volume, exist_ok=True)
        docker_config['volumes'] = {
            workspace_volume: {
                'bind': config.working_dir,
                'mode': 'rw'
            }
        }
        
        # Read-only root filesystem
        if config.read_only:
            docker_config['tmpfs'] = {
                '/tmp': 'rw,noexec,nosuid,size=100m'
            }
        
        return docker_config, workspace_volume
    
    async def create_container(self, config: ContainerConfig, container_id: Optional[str] = None, workspace_path: Optional[str] = None) -> tuple[str, str]:
        """
        Create a secure Docker container
        
        Returns:
            Container ID
        """
        if not self.available:
            raise RuntimeError("Docker is not available. Ensure Docker Desktop is running on Windows or Docker daemon is running on Linux/Mac.")
        
        container_id = container_id or str(uuid.uuid4())
        
        try:
            docker_config, workspace_volume = self._create_secure_config(config, workspace_path)

            # Attach labels so we can track workspace
            docker_config['labels'] = {
                'workspace_volume': workspace_volume,
                'grid_x_id': container_id,
            }
            
            # Pull image if not exists
            try:
                self.client.images.get(config.image)
            except docker.errors.ImageNotFound:
                print(f"Pulling image: {config.image}")
                self.client.images.pull(config.image)
            
            # Create container
            container = self.client.containers.create(**docker_config)
            self.containers[container_id] = container

            print(f"Created secure container {container_id} (Docker ID: {container.short_id})")
            return container_id, workspace_volume
        
        except Exception as e:
            print(f"Error creating container: {e}")
            raise
    
    async def start_container(self, container_id: str) -> bool:
        """Start a container"""
        if container_id not in self.containers:
            raise ValueError(f"Container {container_id} not found")
        
        try:
            container = self.containers[container_id]
            container.start()
            print(f"Started container {container_id}")
            return True
        except Exception as e:
            print(f"Error starting container {container_id}: {e}")
            return False
    
    async def stop_container(self, container_id: str) -> bool:
        """Stop a container"""
        if container_id not in self.containers:
            return False
        
        try:
            container = self.containers[container_id]
            container.stop(timeout=10)
            return True
        except Exception as e:
            print(f"Error stopping container {container_id}: {e}")
            return False
    
    async def remove_container(self, container_id: str) -> bool:
        """Remove a container and clean up workspace"""
        if container_id not in self.containers:
            return False
        
        try:
            container = self.containers[container_id]
            workspace_volume = container.labels.get('workspace_volume')
            
            # Stop if running
            try:
                container.stop(timeout=5)
            except:
                pass
            
            # Remove container
            container.remove(force=True)
            del self.containers[container_id]
            
            # Clean up workspace
            if workspace_volume and os.path.exists(workspace_volume):
                import shutil
                shutil.rmtree(workspace_volume, ignore_errors=True)
            
            print(f"Removed container {container_id}")
            return True
        except Exception as e:
            print(f"Error removing container {container_id}: {e}")
            return False
    
    async def get_container_logs(self, container_id: str, tail: int = 100) -> str:
        """Get container logs"""
        if container_id not in self.containers:
            raise ValueError(f"Container {container_id} not found")
        
        container = self.containers[container_id]
        return container.logs(tail=tail).decode('utf-8')
    
    async def get_container_stats(self, container_id: str) -> Dict[str, Any]:
        """Get container resource usage statistics"""
        if container_id not in self.containers:
            raise ValueError(f"Container {container_id} not found")
        
        container = self.containers[container_id]
        stats = container.stats(stream=False)
        
        return {
            'cpu_usage': self._calculate_cpu_percent(stats),
            'memory_usage': stats['memory_stats'].get('usage', 0),
            'memory_limit': stats['memory_stats'].get('limit', 0),
            'network_io': stats.get('networks', {}),
        }
    
    def _calculate_cpu_percent(self, stats: Dict) -> float:
        try:
            cpu_delta = (
                stats['cpu_stats']['cpu_usage']['total_usage']
            -   stats['precpu_stats']['cpu_usage']['total_usage']
            )

            system_cpu = stats['cpu_stats'].get('system_cpu_usage')
            pre_system_cpu = stats['precpu_stats'].get('system_cpu_usage')

            if system_cpu is None or pre_system_cpu is None:
                return 0.0  # Windows / unsupported backend

            system_delta = system_cpu - pre_system_cpu

            if system_delta > 0:
                return (cpu_delta / system_delta) * 100.0

        except Exception:
            pass

        return 0.0

    
    async def wait_for_container(self, container_id: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Wait for container to finish and return exit code
        
        Returns:
            {'exit_code': int, 'status': str}
        """
        if container_id not in self.containers:
            raise ValueError(f"Container {container_id} not found")
        
        container = self.containers[container_id]
        
        try:
            result = container.wait(timeout=timeout)
            return {
                'exit_code': result['StatusCode'],
                'status': 'completed' if result['StatusCode'] == 0 else 'failed'
            }
        except Exception as e:
            return {
                'exit_code': -1,
                'status': 'error',
                'error': str(e)
            }
    
    def list_containers(self) -> List[str]:
        """List all managed container IDs"""
        return list(self.containers.keys())
    
    async def cleanup_all(self):
        """Clean up all containers"""
        container_ids = list(self.containers.keys())
        for container_id in container_ids:
            await self.remove_container(container_id)


if __name__ == '__main__':
    # Test Docker manager
    async def test():
        manager = DockerManager()
        
        config = ContainerConfig(
            image='python:3.9-slim',
            command=['python', '-c', 'print("Hello from secure container!")'],
            cpu_limit=1.0,
            memory_limit='512m',
            read_only=True,
            timeout=30
        )
        
        try:
            container_id, workspace = await manager.create_container(config)
            await manager.start_container(container_id)
            
            result = await manager.wait_for_container(container_id, timeout=30)
            print(f"Container result: {result}")
            
            logs = await manager.get_container_logs(container_id)
            print(f"Container logs:\n{logs}")
            
            await manager.remove_container(container_id)
        except Exception as e:
            print(f"Test failed: {e}")
    
    asyncio.run(test())

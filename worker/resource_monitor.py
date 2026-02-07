"""
Resource Monitor - Tracks CPU, GPU, memory, storage, and bandwidth metrics
"""

import psutil
import time
import asyncio
from typing import Dict, Optional, Any
from dataclasses import dataclass
import platform

try:
    import pynvml
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    pynvml = None


@dataclass
class ResourceMetrics:
    """Resource metrics snapshot"""
    cpu: Dict[str, Any]
    gpu: Optional[Dict[str, Any]]
    memory: Dict[str, Any]
    storage: Dict[str, Any]
    bandwidth: Dict[str, Any]
    timestamp: float


class ResourceMonitor:
    """Monitors system resources in real-time"""
    
    def __init__(self, update_interval: float = 5.0):
        self.update_interval = update_interval
        self.metrics: Optional[ResourceMetrics] = None
        self._running = False
        self._gpu_initialized = False
        
        if GPU_AVAILABLE:
            self._init_gpu()
    
    def _init_gpu(self) -> None:
        """Initialize NVIDIA GPU monitoring"""
        try:
            pynvml.nvmlInit()
            self._gpu_initialized = True
        except Exception as e:
            print(f"Warning: Could not initialize GPU monitoring: {e}")
            self._gpu_initialized = False
    
    def get_cpu_metrics(self) -> Dict[str, Any]:
        """Get CPU metrics"""
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        
        return {
            'cores': cpu_count,
            'available': cpu_count - sum(1 for p in cpu_percent if p > 80),
            'usage_percent': sum(cpu_percent) / len(cpu_percent) if cpu_percent else 0,
            'frequency_mhz': cpu_freq.current if cpu_freq else None,
        }
    
    def get_gpu_metrics(self) -> Optional[Dict[str, Any]]:
        """Get GPU metrics (NVIDIA only)"""
        if not GPU_AVAILABLE or not self._gpu_initialized:
            return None
        
        try:
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count == 0:
                return None
            
            gpus = []
            available_count = 0
            
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                # Get GPU name
                name_raw = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name_raw, bytes):
                    name = name_raw.decode('utf-8')
                else:
                    name = str(name_raw)
                
                # Get memory info
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                total_memory_gb = mem_info.total / (1024 ** 3)
                free_memory_gb = mem_info.free / (1024 ** 3)
                
                # Get utilization
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_util = util.gpu
                
                # Consider GPU available if utilization < 50%
                is_available = gpu_util < 50
                if is_available:
                    available_count += 1
                
                gpus.append({
                    'index': i,
                    'model': name,
                    'memory_total_gb': round(total_memory_gb, 2),
                    'memory_free_gb': round(free_memory_gb, 2),
                    'utilization_percent': gpu_util,
                    'available': is_available,
                })
            
            return {
                'count': device_count,
                'available': available_count,
                'devices': gpus,
            }
        except Exception as e:
            print(f"Error getting GPU metrics: {e}")
            return None
    
    def get_memory_metrics(self) -> Dict[str, Any]:
        """Get memory metrics"""
        mem = psutil.virtual_memory()
        return {
            'total_gb': round(mem.total / (1024 ** 3), 2),
            'available_gb': round(mem.available / (1024 ** 3), 2),
            'used_gb': round(mem.used / (1024 ** 3), 2),
            'usage_percent': mem.percent,
        }
    
    def get_storage_metrics(self) -> Dict[str, Any]:
        """Get storage metrics"""
        disk = psutil.disk_usage('/')
        return {
            'total_gb': round(disk.total / (1024 ** 3), 2),
            'available_gb': round(disk.free / (1024 ** 3), 2),
            'used_gb': round(disk.used / (1024 ** 3), 2),
            'usage_percent': round((disk.used / disk.total) * 100, 2),
        }
    
    def get_bandwidth_metrics(self) -> Dict[str, Any]:
        """Get network bandwidth metrics"""
        net_io = psutil.net_io_counters()
        return {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
        }
    
    def collect_metrics(self) -> ResourceMetrics:
        """Collect all resource metrics"""
        return ResourceMetrics(
            cpu=self.get_cpu_metrics(),
            gpu=self.get_gpu_metrics(),
            memory=self.get_memory_metrics(),
            storage=self.get_storage_metrics(),
            bandwidth=self.get_bandwidth_metrics(),
            timestamp=time.time()
        )
    
    async def start_monitoring(self, callback: Optional[callable] = None):
        """Start continuous monitoring"""
        self._running = True
        
        while self._running:
            self.metrics = self.collect_metrics()
            
            if callback:
                await callback(self.metrics)
            
            await asyncio.sleep(self.update_interval)
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self._running = False
    
    def get_current_metrics(self) -> Optional[ResourceMetrics]:
        """Get current metrics snapshot"""
        if not self.metrics:
            self.metrics = self.collect_metrics()
        return self.metrics
    
    def to_resource_spec(self) -> Dict[str, Any]:
        """Convert metrics to resource specification format"""
        if not self.metrics:
            self.metrics = self.collect_metrics()
        
        spec = {}
        
        # CPU
        if self.metrics.cpu:
            spec['cpu'] = {
                'cores': self.metrics.cpu['cores'],
                'available': self.metrics.cpu['available'],
            }
        
        # GPU
        if self.metrics.gpu and self.metrics.gpu['available'] > 0:
            gpu_info = self.metrics.gpu['devices'][0] if self.metrics.gpu['devices'] else {}
            spec['gpu'] = {
                'count': self.metrics.gpu['count'],
                'available': self.metrics.gpu['available'],
                'model': gpu_info.get('model', 'Unknown'),
                'memoryGB': gpu_info.get('memory_total_gb', 0),
            }
        
        # Memory
        if self.metrics.memory:
            spec['memory'] = {
                'totalGB': self.metrics.memory['total_gb'],
                'availableGB': self.metrics.memory['available_gb'],
            }
        
        # Storage
        if self.metrics.storage:
            spec['storage'] = {
                'totalGB': self.metrics.storage['total_gb'],
                'availableGB': self.metrics.storage['available_gb'],
            }
        
        # Bandwidth
        if self.metrics.bandwidth:
            spec['bandwidth'] = {
                'uploadMbps': 100,  # Simplified - would need actual measurement
                'downloadMbps': 100,
            }
        
        return spec


if __name__ == '__main__':
    # Test the resource monitor
    monitor = ResourceMonitor()
    
    async def print_metrics(metrics: ResourceMetrics):
        print(f"\n=== Metrics at {time.ctime(metrics.timestamp)} ===")
        print(f"CPU: {metrics.cpu}")
        print(f"GPU: {metrics.gpu}")
        print(f"Memory: {metrics.memory}")
        print(f"Storage: {metrics.storage}")
        print(f"Bandwidth: {metrics.bandwidth}")
    
    print("Starting resource monitoring...")
    try:
        asyncio.run(monitor.start_monitoring(print_metrics))
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        monitor.stop_monitoring()

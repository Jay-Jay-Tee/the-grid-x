"""
Resource Advertiser - Publishes available resources to P2P network
"""

import asyncio
import aiohttp
import json
from typing import Dict, Optional, Callable
from resource_monitor import ResourceMonitor, ResourceMetrics


class ResourceAdvertiser:
    """Advertises available resources to the P2P network"""
    
    def __init__(
        self,
        resource_monitor: ResourceMonitor,
        api_endpoint: str = "http://localhost:3000",
        update_interval: float = 30.0
    ):
        self.resource_monitor = resource_monitor
        self.api_endpoint = api_endpoint
        self.update_interval = update_interval
        self._running = False
        self._advertise_callback: Optional[Callable] = None
    
    def set_advertise_callback(self, callback: Callable[[Dict], None]):
        """Set callback for advertising resources (e.g., to P2P network)"""
        self._advertise_callback = callback
    
    async def advertise_resources(self):
        """Advertise current resources"""
        try:
            metrics = self.resource_monitor.get_current_metrics()
            if not metrics:
                return
            
            resource_spec = self.resource_monitor.to_resource_spec()
            
            # Use callback if available (for direct P2P advertising)
            if self._advertise_callback:
                await self._advertise_callback(resource_spec)
            else:
                # Fallback to API endpoint
                await self._advertise_via_api(resource_spec)
        except Exception as e:
            print(f"Error advertising resources: {e}")
    
    async def _advertise_via_api(self, resource_spec: Dict):
        """Advertise resources via REST API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_endpoint}/api/v1/resources/advertise",
                    json=resource_spec,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        print(f"Successfully advertised resources")
                    else:
                        print(f"Failed to advertise resources: {response.status}")
        except Exception as e:
            print(f"API advertisement error: {e}")
    
    async def start_advertising(self):
        """Start continuous resource advertising"""
        self._running = True
        
        while self._running:
            await self.advertise_resources()
            await asyncio.sleep(self.update_interval)
    
    def stop_advertising(self):
        """Stop advertising"""
        self._running = False
    
    async def reserve_resources(self, resource_spec: Dict) -> bool:
        """Reserve resources for a task"""
        current_metrics = self.resource_monitor.get_current_metrics()
        if not current_metrics:
            return False
        
        # Check if resources are available
        available_spec = self.resource_monitor.to_resource_spec()
        
        # Validate availability
        if 'cpu' in resource_spec:
            if available_spec.get('cpu', {}).get('available', 0) < resource_spec['cpu'].get('cores', 0):
                return False
        
        if 'gpu' in resource_spec:
            if available_spec.get('gpu', {}).get('available', 0) < resource_spec['gpu'].get('count', 0):
                return False
        
        if 'memory' in resource_spec:
            if available_spec.get('memory', {}).get('availableGB', 0) < resource_spec['memory'].get('totalGB', 0):
                return False
        
        return True


if __name__ == '__main__':
    # Test the resource advertiser
    monitor = ResourceMonitor()
    advertiser = ResourceAdvertiser(monitor)
    
    async def test():
        # Start monitoring
        monitor_task = asyncio.create_task(monitor.start_monitoring())
        
        # Wait a bit for initial metrics
        await asyncio.sleep(2)
        
        # Start advertising
        advertiser_task = asyncio.create_task(advertiser.start_advertising())
        
        try:
            await asyncio.gather(monitor_task, advertiser_task)
        except KeyboardInterrupt:
            print("\nStopping...")
            monitor.stop_monitoring()
            advertiser.stop_advertising()
    
    asyncio.run(test())

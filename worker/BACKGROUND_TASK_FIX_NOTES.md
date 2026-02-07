# Background Task Cleanup Fix

## Problem:
Background tasks were created but never tracked or cleaned up, causing resource leaks.

## Solution:
Track all background tasks and provide cleanup method:

```python
class WorkerAdapter:
    def __init__(self):
        self.background_tasks = set()
    
    def create_background_task(self, coro):
        task = asyncio.create_task(coro)
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        return task
    
    async def cleanup(self):
        # Cancel all background tasks
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for cancellation
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        self.background_tasks.clear()
```

Call cleanup() during shutdown.

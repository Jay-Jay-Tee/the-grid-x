# Worker Main.py Authentication Fix

## Problem:
The CLI would start even if authentication failed, leading to confusing UX.

## Solution:
Use an asyncio.Event to properly synchronize authentication status:

```python
# In HybridWorker class
self.auth_success_event = asyncio.Event()
self.auth_failed_event = asyncio.Event()

# In run_worker() after authentication:
if authenticated:
    self.auth_success_event.set()
else:
    self.auth_failed_event.set()
    raise RuntimeError("Authentication failed")

# In main() before starting CLI:
# Wait for authentication with timeout
done, pending = await asyncio.wait(
    [
        asyncio.create_task(worker.auth_success_event.wait()),
        asyncio.create_task(worker.auth_failed_event.wait())
    ],
    timeout=10,
    return_when=asyncio.FIRST_COMPLETED
)

# Check result
if worker.auth_failed_event.is_set():
    print("❌ Authentication failed. Please check credentials.")
    for task in pending:
        task.cancel()
    return

if not worker.auth_success_event.is_set():
    print("❌ Authentication timeout.")
    return
```

This ensures CLI only starts after successful authentication.

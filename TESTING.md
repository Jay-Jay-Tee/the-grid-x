# Grid-X Local Testing Guide

This guide will help you test Grid-X on your local computer.

## Prerequisites

Before starting, ensure you have:

1. **Node.js 18+** - [Download](https://nodejs.org/)
2. **Python 3.9+** - [Download](https://www.python.org/downloads/)
3. **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop/)
4. **Git** (optional, if cloning from repo)

Verify installations:
```bash
node --version    # Should be v18 or higher
python --version  # Should be 3.9 or higher
docker --version  # Should be installed
```

## Step 1: Install Dependencies

### Install Node.js Dependencies
```bash
npm install
```

### Install Python Dependencies
```bash
pip install -r requirements.txt
```

**Note for Windows:** If you encounter issues with `nvidia-ml-py`, you can skip it for CPU-only testing by temporarily removing it from `requirements.txt`.

## Step 2: Build TypeScript Code

```bash
npm run build
```

This compiles all TypeScript files to JavaScript in the `dist/` directory.

## Step 3: Configure Environment

Create a `.env` file from the example:
```bash
# On Windows PowerShell
Copy-Item .env.example .env

# On Linux/Mac
cp .env.example .env
```

Edit `.env` and set at minimum:
```env
PORT=3000
JWT_SECRET=your-secret-key-for-testing
```

## Step 4: Start Docker

Make sure Docker Desktop is running. Verify with:
```bash
docker ps
```

If you see an empty list or Docker info, Docker is running correctly.

## Step 5: Start the API Server

Open a terminal and run:
```bash
npm run dev
```

Or if you've built the code:
```bash
npm start
```

You should see:
```
Grid-X API Server running on port 3000
WebSocket server ready
P2P network: Active
Peer ID: <your-peer-id>
```

**Keep this terminal open!**

## Step 6: Start the Worker (Optional)

Open a **new terminal** and run:
```bash
python worker/main.py
```

Or:
```bash
npm run worker
```

You should see:
```
Starting Grid-X Worker...
Worker started successfully
```

**Note:** The worker requires Docker to be running and may need access to the Docker socket. On Windows/Mac with Docker Desktop, this should work automatically.

## Step 7: Test the API

### Test 1: Health Check

Open a browser or use curl:
```bash
curl http://localhost:3000/health
```

Expected response:
```json
{
  "status": "ok",
  "timestamp": "...",
  "p2p": { "connected": 0 },
  "websocket": { "clients": 0 }
}
```

### Test 2: Create an Account / Login

```bash
curl -X POST http://localhost:3000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com"}'
```

Save the `token` from the response for next steps.

### Test 3: Get Account Balance

Replace `YOUR_TOKEN` with the token from step 2:
```bash
curl http://localhost:3000/api/v1/credits/balance \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test 4: Query Resources

```bash
curl http://localhost:3000/api/v1/resources \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test 5: Submit a Task

```bash
curl -X POST http://localhost:3000/api/v1/tasks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "print(\"Hello from Grid-X!\")",
    "language": "python",
    "requirements": {
      "cpu": {"cores": 1},
      "memory": {"totalGB": 1}
    },
    "timeout": 60
  }'
```

Save the `taskId` from the response.

### Test 6: Check Task Status

Replace `TASK_ID` with the task ID from step 5:
```bash
curl http://localhost:3000/api/v1/tasks/TASK_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Step 8: Test with the SDK (TypeScript Example)

### Create a Test Script

Create `test-client.ts`:
```typescript
import { GridXClient } from './sdk/client';

async function test() {
  const client = new GridXClient({
    apiEndpoint: 'http://localhost:3000',
  });

  try {
    // Login
    const user = await client.login('testuser', 'test@example.com');
    console.log('Logged in:', user);

    // Get balance
    const balance = await client.getBalance();
    console.log('Balance:', balance);

    // Submit task
    const task = await client.submitTask({
      code: 'print("Hello from Grid-X SDK!")',
      language: 'python',
      requirements: { cpu: { cores: 1 } },
      timeout: 60,
    });
    console.log('Task submitted:', task);

    // Listen for updates
    client.on('task_update', (data) => {
      console.log('Task update:', data);
    });

    // Wait a bit
    await new Promise(resolve => setTimeout(resolve, 5000));

    // Get task status
    const status = await client.getTask(task.taskId);
    console.log('Task status:', status);

  } catch (error) {
    console.error('Error:', error);
  } finally {
    client.close();
  }
}

test();
```

### Run the Test Script

First, compile it:
```bash
npx ts-node test-client.ts
```

Or add to `package.json`:
```json
"scripts": {
  "test:client": "ts-node test-client.ts"
}
```

Then run:
```bash
npm run test:client
```

## Step 9: Test WebSocket Connection

You can test WebSocket connections using a tool like [WebSocket King](https://websocketking.com/) or create a simple HTML file:

Create `test-websocket.html`:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Grid-X WebSocket Test</title>
</head>
<body>
    <h1>Grid-X WebSocket Test</h1>
    <div id="messages"></div>
    <script>
        const ws = new WebSocket('ws://localhost:3000');
        const messages = document.getElementById('messages');
        
        ws.onopen = () => {
            messages.innerHTML += '<p>Connected!</p>';
            ws.send(JSON.stringify({
                type: 'subscribe',
                payload: { channels: ['task_update'] },
                timestamp: Date.now()
            }));
        };
        
        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            messages.innerHTML += `<p>Received: ${JSON.stringify(msg, null, 2)}</p>`;
        };
        
        ws.onerror = (error) => {
            messages.innerHTML += `<p>Error: ${error}</p>`;
        };
    </script>
</body>
</html>
```

Open this file in a browser after starting the API server.

## Troubleshooting

### Port Already in Use
If port 3000 is already in use:
```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:3000 | xargs kill
```

Or change the port in `.env`:
```env
PORT=3001
```

### Docker Permission Issues
On Linux, you may need to add your user to the docker group:
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

### Python Import Errors
If you get import errors:
```bash
# Make sure you're using the right Python
python3 --version
pip3 install -r requirements.txt

# Or use a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### P2P Network Not Starting
If you see "P2P network: Inactive":
- Check firewall settings
- Try disabling mDNS if on Windows: Set `enableMDNS: false` in the code temporarily
- Check if ports are available

### Task Execution Fails
- Ensure Docker is running: `docker ps`
- Check Docker logs: `docker logs <container-id>`
- Verify the worker is running and can access Docker

## Quick Test Checklist

- [ ] Dependencies installed (`npm install`, `pip install`)
- [ ] TypeScript compiled (`npm run build`)
- [ ] Docker running (`docker ps`)
- [ ] API server started (`npm run dev`)
- [ ] Health check works (`curl http://localhost:3000/health`)
- [ ] Can login (`POST /api/v1/auth/login`)
- [ ] Can query resources (`GET /api/v1/resources`)
- [ ] Can submit task (`POST /api/v1/tasks`)
- [ ] Worker running (optional, `python worker/main.py`)

## Next Steps

Once basic testing works:
1. Try submitting more complex tasks
2. Test the order matching system
3. Test credit transfers
4. Test multiple workers
5. Test P2P resource discovery

For more examples, see `examples/basic-usage.ts`.

# Grid-X Complete Setup Guide
## Distributed Computing Platform - Production Ready

---

## 🎯 Quick Start (5 Minutes)

### Prerequisites
- Python 3.9+
- Docker installed and running
- At least 2 machines for distributed testing (or 1 for local testing)

### Single Machine Setup (Testing)

**Step 1: Install Dependencies**
```bash
pip install fastapi uvicorn websockets requests psutil docker
```

**Step 2: Start Coordinator**
```bash
# In Terminal 1
cd coordinator
python -m coordinator.main
```

You should see:
```
🌐 Grid-X Coordinator - FIXED VERSION 1.0.0
📡 HTTP API:    http://0.0.0.0:8081
🔌 WebSocket:   ws://0.0.0.0:8080/ws/worker
```

**Step 3: Start Worker**
```bash
# In Terminal 2
cd worker
python -m worker.main --user alice --password mypassword123
```

You should see:
```
✓ Worker authenticated (owner: alice)
🎮 CLI ready. Type 'help' for commands
```

**Step 4: Submit a Test Job**
```bash
# In the worker CLI
submit print("Hello from Grid-X!")
```

---

## 🌐 Multi-Machine Setup (Production)

### Architecture
```
┌─────────────────┐
│  Coordinator    │  Machine A (192.168.1.100)
│  HTTP: 8081     │
│  WS:   8080     │
└────────┬────────┘
         │
    ┌────┴────┬──────────┐
    │         │          │
┌───▼──┐  ┌──▼───┐  ┌──▼───┐
│Worker│  │Worker│  │Worker│
│(B)   │  │(C)   │  │(D)   │
└──────┘  └──────┘  └──────┘
```

### Machine A: Coordinator Setup

**1. Configure Firewall**
```bash
# Ubuntu/Debian
sudo ufw allow 8081/tcp  # HTTP API
sudo ufw allow 8080/tcp  # WebSocket

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8081/tcp
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

**2. Get Machine IP**
```bash
# Linux/Mac
hostname -I | awk '{print $1}'

# Windows
ipconfig | findstr IPv4
```

**3. Start Coordinator**
```bash
cd coordinator
export GRIDX_HTTP_PORT=8081
export GRIDX_WS_PORT=8080
python -m coordinator.main
```

**4. Verify Coordinator is Running**
```bash
# From another terminal or machine
curl http://192.168.1.100:8081/health

# Expected response:
{"status":"healthy","service":"grid-x-coordinator","timestamp":...}
```

### Machines B, C, D: Worker Setup

**1. Install Dependencies**
```bash
pip install websockets requests psutil docker
```

**2. Install Docker**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io
sudo usermod -aG docker $USER
# Log out and back in

# Mac
# Install Docker Desktop from docker.com

# Windows
# Install Docker Desktop from docker.com
```

**3. Test Connection to Coordinator**
```bash
# Test HTTP
curl http://192.168.1.100:8081/workers

# Test WebSocket (if you have websocat)
websocat ws://192.168.1.100:8080/ws/worker
```

**4. Start Worker**
```bash
cd worker
python -m worker.main \
  --user worker1 \
  --password securepass123 \
  --coordinator-ip 192.168.1.100 \
  --http-port 8081 \
  --ws-port 8080
```

**5. Verify Worker Connected**
Check coordinator terminal - you should see:
```
✓ Worker abc123... authenticated (owner: worker1)
```

---

## 🐛 Troubleshooting

### Problem: "Connection refused" Error

**Symptoms:**
```
Error: Cannot connect to coordinator at http://192.168.1.100:8081
```

**Solutions:**
1. Verify coordinator is running:
   ```bash
   curl http://192.168.1.100:8081/health
   ```

2. Check firewall on coordinator machine:
   ```bash
   sudo ufw status  # Ubuntu
   sudo firewall-cmd --list-all  # CentOS
   ```

3. Verify IP address is correct:
   ```bash
   ping 192.168.1.100
   ```

4. Check if ports are in use:
   ```bash
   # On coordinator machine
   sudo netstat -tulpn | grep 8081
   sudo netstat -tulpn | grep 8080
   ```

### Problem: "Authentication Failed"

**Symptoms:**
```
❌ Authentication failed for user: alice (wrong password)
```

**Solutions:**
1. **First time user**: Make sure you're using a NEW username
2. **Existing user**: Use the exact same password as before
3. **Reset identity**: Delete worker config file
   ```bash
   rm ~/.gridx/worker_alice.json
   ```

### Problem: "Docker not found"

**Symptoms:**
```
Error: Docker daemon not accessible
```

**Solutions:**
1. **Linux**: Add user to docker group
   ```bash
   sudo usermod -aG docker $USER
   # Log out and back in
   ```

2. **Check Docker is running**:
   ```bash
   docker ps
   ```

3. **Start Docker**:
   ```bash
   # Linux
   sudo systemctl start docker
   
   # Mac/Windows
   # Start Docker Desktop application
   ```

### Problem: "Port already in use"

**Symptoms:**
```
Error: Address already in use
```

**Solutions:**
1. **Find what's using the port**:
   ```bash
   # Linux/Mac
   sudo lsof -i :8081
   sudo lsof -i :8080
   
   # Windows
   netstat -ano | findstr :8081
   ```

2. **Kill the process** or **use different ports**:
   ```bash
   export GRIDX_HTTP_PORT=9081
   export GRIDX_WS_PORT=9080
   python -m coordinator.main
   ```

### Problem: Worker connects but doesn't receive jobs

**Solutions:**
1. Check worker status:
   ```bash
   curl http://192.168.1.100:8081/workers
   ```

2. Verify Docker is working:
   ```bash
   docker run --rm hello-world
   ```

3. Check worker logs for errors

4. Restart both coordinator and worker

---

## 📊 Monitoring

### Check System Status

**Coordinator Status:**
```bash
curl http://COORDINATOR_IP:8081/status

# Response:
{
  "service": "Grid-X Coordinator",
  "version": "1.0.0",
  "workers": {"total": 3, "active": 3},
  "queue_size": 5
}
```

**List Workers:**
```bash
curl http://COORDINATOR_IP:8081/workers

# Response:
{
  "workers": [
    {
      "id": "abc123...",
      "owner_id": "worker1",
      "status": "idle",
      "jobs_completed": 15
    }
  ]
}
```

**Check Credits:**
```bash
curl http://COORDINATOR_IP:8081/credits/alice

# Response:
{
  "user_id": "alice",
  "balance": 95.5,
  "timestamp": 1234567890
}
```

---

## 🔒 Security Best Practices

### 1. Use Strong Passwords
```bash
# Good: At least 8 characters, mix of letters/numbers
--password MySecureP@ss123

# Bad: Short or common passwords
--password 123456
```

### 2. Network Security
- Run coordinator behind firewall
- Only expose necessary ports (8080, 8081)
- Consider using VPN for worker connections
- Use HTTPS/WSS in production (via nginx reverse proxy)

### 3. Resource Limits
Workers automatically enforce:
- CPU limit: 1 core per job
- Memory limit: 512MB per job
- Execution timeout: 300 seconds
- No network access for jobs
- Read-only root filesystem

---

## 📈 Performance Tuning

### Coordinator Machine
- **CPU**: 2+ cores recommended
- **RAM**: 2GB+ for coordinator + database
- **Disk**: SSD recommended for database
- **Network**: 10Mbps+ upload/download

### Worker Machine
- **CPU**: 2+ cores (can run multiple jobs)
- **RAM**: 2GB+ (512MB per concurrent job)
- **Disk**: 10GB+ for Docker images
- **Network**: 5Mbps+ upload/download

### Scaling
- **Single coordinator**: Handles 50-100 workers
- **Worker capacity**: Each worker can run 1-5 concurrent jobs
- **Job throughput**: ~10-20 jobs/second with 10 workers

---

## 🧪 Testing

### Local Test
```bash
# Terminal 1: Start coordinator
cd coordinator && python -m coordinator.main

# Terminal 2: Start worker
cd worker && python -m worker.main --user test --password test123

# Terminal 3: Submit test job
curl -X POST http://localhost:8081/jobs \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","code":"print(\"Hello!\")","language":"python"}'

# Get job result
curl http://localhost:8081/jobs/JOB_ID_HERE
```

### Multi-Machine Test
```bash
# On coordinator machine (192.168.1.100)
cd coordinator && python -m coordinator.main

# On worker machines
cd worker && python -m worker.main --user worker1 --password pass1 --coordinator-ip 192.168.1.100
cd worker && python -m worker.main --user worker2 --password pass2 --coordinator-ip 192.168.1.100
cd worker && python -m worker.main --user worker3 --password pass3 --coordinator-ip 192.168.1.100

# Submit jobs from any machine
curl -X POST http://192.168.1.100:8081/jobs \
  -H "Content-Type: application/json" \
  -d '{"user_id":"worker1","code":"import time; print(\"Job from worker1\"); time.sleep(2)","language":"python"}'
```

---

## 📝 Configuration Reference

### Environment Variables

**Coordinator:**
```bash
GRIDX_HTTP_PORT=8081          # HTTP API port
GRIDX_WS_PORT=8080            # WebSocket port  
GRIDX_DB_PATH=./data/gridx.db # Database location
GRIDX_LOG_LEVEL=INFO          # Logging level
```

**Worker:**
```bash
COORDINATOR_WS=ws://192.168.1.100:8080/ws/worker  # Coordinator WebSocket URL
COORDINATOR_HTTP=http://192.168.1.100:8081        # Coordinator HTTP URL
DOCKER_HOST=unix:///var/run/docker.sock            # Docker socket path
```

### Command Line Options

**Worker:**
```bash
python -m worker.main [OPTIONS]

Required:
  --user USERNAME          # Your username
  --password PASSWORD      # Your password

Optional:
  --coordinator-ip IP      # Coordinator IP (default: localhost)
  --http-port PORT         # HTTP port (default: 8081)
  --ws-port PORT           # WebSocket port (default: 8080)
  --no-cli                 # Run without interactive CLI
```

---

## ✅ Production Deployment Checklist

- [ ] Coordinator machine has static IP or hostname
- [ ] Firewall rules configured (ports 8080, 8081)
- [ ] Docker installed on all worker machines
- [ ] All machines can ping coordinator
- [ ] Strong passwords configured
- [ ] Database backup strategy in place
- [ ] Monitoring/logging configured
- [ ] SSL/TLS configured (if using public internet)
- [ ] Worker machines have adequate resources
- [ ] Tested with sample workload

---

## 🆘 Getting Help

### Common Issues
1. Check this guide's Troubleshooting section
2. Verify all prerequisites are met
3. Test with single machine setup first
4. Check logs for error messages

### Debug Mode
```bash
# Start with verbose logging
export GRIDX_LOG_LEVEL=DEBUG
python -m coordinator.main
```

### Support
- GitHub Issues: [your-repo]/issues
- Email: support@grid-x.example.com

---

## 🎉 Success Indicators

You know it's working when:
1. ✅ Coordinator shows "WebSocket server ready"
2. ✅ Worker shows "✓ Worker authenticated"
3. ✅ `/health` endpoint returns 200 OK
4. ✅ Jobs execute and return results
5. ✅ Credits are deducted and earned correctly


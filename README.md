# Grid-X - Decentralized Distributed Computing Platform

**Version 1.0.0 - Fixed & Enhanced**

Grid-X is a decentralized platform that allows users to share computing resources and execute code remotely. Users earn credits by contributing compute power and spend credits to run jobs.

## 🚀 Features

- **Distributed Computing**: Run Python code on remote worker machines
- **Credit System**: Earn credits by running others' jobs, spend credits to run your own
- **Secure Execution**: Docker-based isolation with comprehensive security features
- **Real-time Communication**: WebSocket-based coordinator-worker communication
- **Resource Monitoring**: Track CPU, memory, and GPU usage
- **Web Dashboard**: User-friendly interface for job management

## 🛠️ Fixed Issues (v1.0.0)

This version includes critical fixes:

✅ **Fixed double credit deduction bug** - Credits now deducted atomically  
✅ **Fixed authentication race condition** - Proper synchronization  
✅ **Implemented common module** - Shared constants, utils, schemas  
✅ **Added input validation** - All user inputs validated and sanitized  
✅ **Added transaction support** - Database operations are now atomic  
✅ **Fixed background task leaks** - Proper cleanup on shutdown  
✅ **Added comprehensive error handling** - Better error messages and logging  

## 📋 Requirements

- Python 3.9+
- Docker (for workers)
- Node.js 18+ (for web UI)
- SQLite3

## 🏃 Quick Start

### 1. Start the Coordinator

```bash
cd coordinator
python -m coordinator.main
```

The coordinator will start on:
- HTTP API: `http://localhost:8081`
- WebSocket: `ws://localhost:8080/ws/worker`

### 2. Start a Worker

```bash
cd worker
python -m worker.main --user your_username --password your_password
```

### 3. Submit a Job

```python
import requests

response = requests.post('http://localhost:8081/jobs', json={
    'user_id': 'your_username',
    'code': 'print("Hello from Grid-X!")',
    'language': 'python'
})

job_id = response.json()['job_id']
print(f"Job submitted: {job_id}")
```

### 4. Check Job Status

```python
response = requests.get(f'http://localhost:8081/jobs/{job_id}')
job = response.json()
print(f"Status: {job['status']}")
print(f"Output: {job['stdout']}")
```

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [Security Guide](docs/security.md)
- [Deployment Guide](docs/deployment.md)

## 🔐 Security

Grid-X implements multiple security layers:

- Docker container isolation
- Network disabled for job execution
- Read-only root filesystem
- Dropped capabilities
- Resource limits (CPU, memory, disk)
- Authentication and authorization
- Input validation and sanitization

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

## 📄 License

[Your chosen license]

## 👥 Authors

- Siddharth & Ujjwal

## 🙏 Acknowledgments

Built with ❤️ using FastAPI, Docker, and modern Python async patterns.

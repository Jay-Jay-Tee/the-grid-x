# Grid-X

A decentralized P2P resource mesh where users can securely share and utilize computational resources (CPU, GPU, bandwidth, storage, memory).

## Features

- **Decentralized P2P Network**: Pure peer-to-peer architecture using libp2p
- **Secure Docker Sandboxing**: Isolated task execution with no host file access
- **Resource Sharing**: Share and discover computational resources across the network
- **Real-time Monitoring**: Track CPU, GPU, memory, storage, and bandwidth
- **Task Execution**: Execute arbitrary tasks in secure Docker containers

## Architecture

- **API Layer** (Node.js/TypeScript): REST API and WebSocket server
- **Worker Daemon** (Python): Resource monitoring and task execution
- **P2P Network** (Node.js/TypeScript): Peer discovery and messaging
- **Client SDK** (Node.js/TypeScript): Easy integration for clients

## Installation

### Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- Docker Engine

### Setup

1. Install Node.js dependencies:
```bash
npm install
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Build TypeScript:
```bash
npm run build
```

## Quick Start

See [QUICKSTART.md](QUICKSTART.md) for a 5-minute setup guide.

## Usage

### Start API Server
```bash
npm run dev
# or
npm start
```

### Start Worker Daemon
```bash
npm run worker
# or
python worker/main.py
```

### Test the System
```bash
# Run automated tests
npm run test:api

# Or use the test client
node test-client.js
```

For detailed testing instructions, see [TESTING.md](TESTING.md).

## Security

Grid-X uses Docker with strict security policies:
- No host file system access
- User namespace isolation
- Resource limits (CPU, memory, GPU)
- Network isolation
- Read-only filesystem where possible

## License

MIT

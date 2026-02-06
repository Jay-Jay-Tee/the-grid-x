# Grid-X Quick Start Guide

Get Grid-X running on your local machine in 5 minutes!

## Prerequisites Check

```bash
node --version    # Need v18+
python --version  # Need 3.9+
docker --version  # Need Docker installed
```

## Quick Setup (3 Steps)

### 1. Install Dependencies

```bash
# Install Node.js packages
npm install

# Install Python packages
pip install -r requirements.txt
```

### 2. Build & Start

```bash
# Build TypeScript
npm run build

# Start API server (in one terminal)
npm run dev

# Start worker (in another terminal - optional)
npm run worker
```

### 3. Test It

```bash
# Run the test client
npm run test:api
```

Or test manually:

```bash
# Health check
curl http://localhost:3000/health

# Login
curl -X POST http://localhost:3000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com"}'
```

## What's Running?

- **API Server**: `http://localhost:3000`
- **WebSocket**: `ws://localhost:3000`
- **Worker**: Monitoring resources and executing tasks

## Next Steps

- Read `TESTING.md` for detailed testing instructions
- Check `examples/basic-usage.ts` for SDK usage
- See `README.md` for architecture details

## Troubleshooting

**Port 3000 in use?**
```bash
# Change PORT in .env file
PORT=3001
```

**Docker not working?**
- Make sure Docker Desktop is running
- On Linux: `sudo usermod -aG docker $USER` then logout/login

**Python import errors?**
```bash
python3 -m pip install -r requirements.txt
```

For more help, see `TESTING.md`.

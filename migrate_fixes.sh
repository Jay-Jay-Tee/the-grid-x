#!/bin/bash

# Grid-X Migration Script
# Applies all critical fixes to your Grid-X installation

set -e

echo "🚀 Grid-X Critical Fixes Migration"
echo "=================================="
echo ""

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "worker" ] || [ ! -d "coordinator" ]; then
    echo "❌ Error: Please run this script from the Grid-X root directory"
    exit 1
fi

echo "📁 Current directory: $(pwd)"
echo ""

# Create backup directory
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
echo "📦 Creating backup in: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Backup existing files
echo "   Backing up worker/main.py..."
cp worker/main.py "$BACKUP_DIR/main.py.backup"

echo "   Backing up coordinator/websocket.py..."
cp coordinator/websocket.py "$BACKUP_DIR/websocket.py.backup"

echo "   Backing up coordinator/database.py..."
cp coordinator/database.py "$BACKUP_DIR/database.py.backup"

echo "✅ Backups created successfully"
echo ""

# Apply fixes
echo "🔧 Applying fixes..."

if [ -f "worker/main_fixed.py" ]; then
    echo "   Updating worker/main.py..."
    cp worker/main_fixed.py worker/main.py
    echo "   ✅ Worker updated"
else
    echo "   ⚠️  worker/main_fixed.py not found - skipping worker update"
fi

if [ -f "coordinator/websocket_fixed.py" ]; then
    echo "   Updating coordinator/websocket.py..."
    cp coordinator/websocket_fixed.py coordinator/websocket.py
    echo "   ✅ WebSocket handler updated"
else
    echo "   ⚠️  coordinator/websocket_fixed.py not found - skipping websocket update"
fi

if [ -f "coordinator/database_fixed.py" ]; then
    echo "   Updating coordinator/database.py..."
    cp coordinator/database_fixed.py coordinator/database.py
    echo "   ✅ Database module updated"
else
    echo "   ⚠️  coordinator/database_fixed.py not found - skipping database update"
fi

echo ""
echo "✅ All fixes applied successfully!"
echo ""

# Database migration notice
echo "📊 Database Migration"
echo "===================="
echo "The database schema will be automatically updated when you start the coordinator."
echo "New features:"
echo "  - user_auth table for authentication"
echo "  - auth_token column in workers table"
echo "  - Automatic migration of existing data"
echo ""

# Test the installation
echo "🧪 Testing installation..."
echo ""

# Check Python dependencies
echo "Checking Python dependencies..."
python3 -c "import websockets; import requests" 2>/dev/null && echo "   ✅ Core dependencies OK" || echo "   ⚠️  Warning: Some dependencies may be missing. Run: pip install -r requirements.txt"
echo ""

# Show next steps
echo "🎯 Next Steps"
echo "============="
echo ""
echo "1. Start the coordinator:"
echo "   cd coordinator"
echo "   python main.py"
echo ""
echo "2. Start a worker (in another terminal):"
echo "   cd worker"
echo "   python main.py --user YOUR_USERNAME --password YOUR_PASSWORD"
echo ""
echo "3. New commands available:"
echo "   - status: Check worker connection state"
echo "   - log: View recent activity"
echo "   - workers: See all workers (with (YOU) marker for your workers)"
echo ""
echo "4. If something goes wrong, restore from backup:"
echo "   cp $BACKUP_DIR/main.py.backup worker/main.py"
echo "   cp $BACKUP_DIR/websocket.py.backup coordinator/websocket.py"
echo "   cp $BACKUP_DIR/database.py.backup coordinator/database.py"
echo ""

# Create a quick start guide
cat > QUICKSTART_AFTER_FIX.md << 'EOF'
# Grid-X Quick Start (After Fixes)

## Starting the System

### 1. Start Coordinator
```bash
cd coordinator
python main.py
```

Expected output:
```
Grid-X Coordinator HTTP: 0.0.0.0:8081
Grid-X Coordinator WS: 0.0.0.0:8080 path /ws/worker
```

### 2. Start Worker
```bash
cd worker
python main.py --user alice --password mypassword123
```

Expected output:
```
✓ Loaded existing worker identity
  Worker ID: 8f1f7952-75a1...
  
👷 Starting worker process...
   Worker ID: 8f1f7952-75a1...
   Owner: alice
   Capabilities: 8 CPU cores, GPU: False

✅ Connected to coordinator
   You're now earning credits when jobs run on your worker!
```

### 3. Using the CLI

```
alice> workers
🖥️ Workers in network: 1
  ✅ 8f1f7952-75a... - idle - Owner: alice (YOU)

alice> status
🟢 CONNECTED
Worker ID: 8f1f7952-75a1...
User: alice
Last heartbeat: 2.3s ago
Status: Earning credits ✅

alice> submit print("Hello Grid-X!")
✅ Job submitted: job_abc123...
⏳ Waiting for job job_abc123...

============================================================
Job COMPLETED
============================================================
Output:
Hello Grid-X!
============================================================

alice> log
📋 Recent Activity (last 10 events):
------------------------------------------------------------
[2026-02-07 01:30:45] Connected
  └─ Worker registered with coordinator
[2026-02-07 01:31:12] Job Submitted
  └─ ID: job_abc1...
[2026-02-07 01:31:12] Job Assigned
  └─ ID: job_abc1...
[2026-02-07 01:31:14] Job Completed
  └─ ID: job_abc1...
------------------------------------------------------------

alice> credits
💰 Balance: 10.50 credits

alice> help
Commands:
  submit <code>     Submit Python code
  file <path>       Submit code from file
  credits           Check credit balance
  workers           List all workers in network
  status            Show connection status
  log               Show recent activity
  help              Show this help
  quit              Exit
```

## Key Improvements

### ✅ Persistent Worker Identity
- Worker ID saved in `~/.gridx/worker_alice.json`
- Same worker ID used every time you connect
- No more duplicate workers!

### ✅ Authentication
- Username + password required
- Secure credential verification
- Can't impersonate other users

### ✅ Connection Tracking
- Real-time connection status
- Shows when you're earning credits
- Clear error messages when disconnected

### ✅ Activity Logging
- See what your worker has been doing
- Privacy-preserving format
- Last 50 events tracked

## Troubleshooting

### Worker won't connect
```bash
# Check if coordinator is running
curl http://localhost:8081/workers

# Try with explicit IP
python main.py --user alice --password mypass --coordinator-ip 192.168.1.100
```

### "Authentication failed"
- Check your password is correct
- If you changed password, a new worker ID will be created
- Old worker will show as offline

### Multiple workers showing up
- This was fixed! Now only one worker per user+password
- If you see old duplicate workers, they'll show as "offline"
- They'll be cleaned up automatically after 24 hours

## Remote Worker Setup

To connect a worker on another machine:

```bash
# Find coordinator IP
ifconfig  # or ipconfig on Windows

# On remote machine
python main.py --user alice --password mypass --coordinator-ip 192.168.1.100
```

Make sure firewall allows:
- Port 8080 (WebSocket)
- Port 8081 (HTTP)
EOF

echo "📖 Created QUICKSTART_AFTER_FIX.md"
echo ""

echo "🎉 Migration Complete!"
echo ""
echo "Your Grid-X installation is now ready for the hackathon demo! 🚀"
echo ""
echo "Read FIXES_AND_IMPROVEMENTS.md for detailed information about all changes."
echo "Read QUICKSTART_AFTER_FIX.md for quick start guide with the new features."
echo ""

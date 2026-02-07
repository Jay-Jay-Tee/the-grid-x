# Grid-X Railway Deployment Guide

## Coordinator (what you deploy on Railway)

Your coordinator is deployed at: **https://the-grid-x-render-deployment-production.up.railway.app**

Railway exposes it on port 8080 internally, but the public URL uses HTTPS (port 443) — **do not add `:8080` to the public URL**.

---

## 1. Railway Project Setup

### Link common and coordinator

- **Root directory**: Your Railway service should use the **project root** (the folder containing `coordinator/`, `common/`, etc.), not just `coordinator/`.
- **Build command**: Railway will auto-detect Python. If needed, set:
  - **Build**: `pip install -r requirements.txt`
  - **Start**: `python -m coordinator.main` (or use the Procfile)

### Environment variables (optional)

| Variable         | Description                         | Default     |
|------------------|-------------------------------------|-------------|
| `PORT`           | Set by Railway (8080)               | —           |
| `GRIDX_DB_PATH`  | SQLite DB path (use a volume)       | `./data/gridx.db` |

For persistent data, add a **Railway Volume** and set:
```
GRIDX_DB_PATH=/data/gridx.db
```
Mount the volume at `/data`.

---

## 2. Connecting the Worker App (Desktop)

In the Worker desktop app **Coordinator URL** field, enter:

```
https://the-grid-x-render-deployment-production.up.railway.app
```

Important:
- Use `https://` (not `http://`)
- Do not add a port (e.g. `:8080`)
- Do not add a trailing slash
- Do not add `/ws/worker` — the app adds that automatically

---

## 3. Connecting the React UI (if used)

Set the API base URL in your UI (e.g. via env or config):

```
VITE_API_BASE=https://the-grid-x-render-deployment-production.up.railway.app
```

Or hardcode in `ui/src/services/api.ts`:

```ts
const DEFAULT_API_BASE = 'https://the-grid-x-render-deployment-production.up.railway.app';
```

---

## 4. Connecting Workers (CLI or Docker)

Set the coordinator URL:

```bash
# Option A: Full URL (Worker App / HybridWorker style)
# In Worker App login: paste the full coordinator URL

# Option B: Environment variables (CLI worker)
export COORDINATOR_HTTP=https://the-grid-x-render-deployment-production.up.railway.app
export COORDINATOR_WS=wss://the-grid-x-render-deployment-production.up.railway.app/ws/worker
```

---

## 5. Verify Deployment

- **Health check**: https://the-grid-x-render-deployment-production.up.railway.app/health  
  Should return `{"status":"healthy",...}`

- **API docs**: https://the-grid-x-render-deployment-production.up.railway.app/docs  
  (if FastAPI docs are enabled)

---

## 6. Troubleshooting

| Issue | Fix |
|-------|-----|
| "common/coordinator not found" | Ensure Railway root is the project root (contains both `coordinator/` and `common/`) |
| Connection refused | Use `https://` and omit the port in the public URL |
| WebSocket fails | Ensure URL is `wss://` (not `ws://`) for HTTPS sites |
| DB resets on deploy | Add a Railway Volume and set `GRIDX_DB_PATH=/data/gridx.db` |

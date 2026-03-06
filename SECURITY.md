# Grid-X Security

This document covers the security model, protections in place, known limitations, and hardening recommendations for Grid-X deployments.

---

## Authentication

### Worker authentication

Workers authenticate to the coordinator at WebSocket connection time via a `hello` message containing `owner_id` and `auth_token`. The auth token is a SHA-256 hash of `"user_id:password"` derived on the worker side.

```
auth_token = SHA-256("user_id:password")
```

On the coordinator:

- If the `owner_id` exists in `user_auth` and the token matches → authentication succeeds
- If the `owner_id` exists but the token does not match → connection is rejected with code `4401`
- If the `owner_id` does not exist → new user is registered and the worker is accepted
- Banned or suspended workers are rejected at the handshake regardless of credentials

Workers that connect without an `auth_token` are accepted for backward compatibility but flagged with a warning. This behavior should be disabled in production by removing the fallback path in `coordinator/websocket.py`.

### HTTP API authentication

There is currently **no authentication on HTTP endpoints**. Anyone who can reach port `8081` can submit jobs, query job results, check credit balances, and access all admin endpoints including ban/suspend controls.

For any deployment beyond a trusted private LAN, place a reverse proxy with authentication in front of the HTTP API before exposing it.

---

## Worker restrictions

The coordinator supports three restriction states per worker, enforced at the WebSocket handshake and via the admin API:

| State | Behavior |
|-------|----------|
| None | Worker can connect and receive jobs normally |
| `suspended` | Worker is disconnected and blocked from reconnecting until unsuspended |
| `banned` | Worker is permanently blocked from connecting |

Admin endpoints:

```
POST /admin/workers/{id}/ban
POST /admin/workers/{id}/suspend
POST /admin/workers/{id}/unsuspend
POST /admin/workers/{id}/disconnect
```

On force-disconnect, the coordinator sends a `"terminated"` message to the worker before closing the WebSocket with code `4400`, allowing the worker client to surface the event to the user.

---

## Job isolation (Docker)

Every job runs in a fresh Docker container that is destroyed after execution. The following security settings are applied to every container by `worker/docker_manager.py`:

| Setting | Value | Effect |
|---------|-------|--------|
| `no-new-privileges` | `true` | Prevents privilege escalation inside the container |
| `cap_drop` | `ALL` | Drops all Linux capabilities |
| `cap_add` | `CHOWN, SETGID, SETUID` | Minimal capabilities re-added for basic file operations |
| `read_only` | `true` | Container root filesystem is read-only |
| `network_disabled` | configurable | Disables network access from within the container |
| `mem_limit` | configurable | Hard memory ceiling per job |
| `cpu_quota` / `cpu_period` | configurable | CPU core limit per job |
| `auto_remove` | `true` | Container is deleted immediately on exit |

Default per-job resource limits:

| Resource | Default |
|----------|---------|
| CPU | 1 core |
| Memory | 512 MB |
| Timeout | 300 seconds |
| Max output | 10 MB |

All limits are configurable per job via the `limits` field in the job submission body and via environment variables on the coordinator.

### Docker images used

| Language | Image |
|----------|-------|
| `python` | `python:3.9-slim` |
| `javascript` / `node` | `node:18-slim` |
| `bash` | `ubuntu:22.04` |

These are minimal base images. For stricter isolation, replace them with distroless or custom images with only the required runtime.

---

## Input validation

All HTTP endpoints validate inputs before processing. The following rules are enforced:

| Field | Rule |
|-------|------|
| `user_id` | Alphanumeric, `_` and `-` only; 1–64 characters |
| `job_id` | Must be a valid UUID4 |
| `worker_id` | Must be a valid UUID4 |
| `code` | String; max 1 MB |
| `language` | Must be one of `python`, `javascript`, `node`, `bash` |
| Admin broadcast `message` | Max 2000 characters |

Inputs are sanitized before storage: null bytes and non-printable characters are stripped; all strings are length-capped.

---

## Network exposure

Grid-X runs two ports:

| Port | Protocol | Purpose |
|------|----------|---------|
| `8081` | HTTP | Job submission, status, credits, admin API |
| `8080` | WebSocket | Worker connections |

Neither port uses TLS by default. All traffic — including worker credentials — is transmitted in plaintext.

**For any deployment outside a trusted LAN:**

- Terminate TLS at a reverse proxy (nginx, Caddy) in front of both ports
- Restrict port `8080` to known worker IP ranges via firewall rules
- Restrict port `8081` admin endpoints (`/admin/*`) to trusted IPs or add HTTP Basic Auth at the proxy level

---

## Known limitations

**No TLS.** Credentials and job payloads are sent in plaintext. This is the highest-priority hardening item for any non-local deployment.

**No HTTP authentication.** All REST endpoints including admin controls are unauthenticated. The admin API (`/admin/workers/{id}/ban`, `/admin/broadcast`, etc.) must be protected at the network or proxy layer.

**No rate limiting.** Rate limit constants are defined in `common/constants.py` (`RATE_LIMIT_REQUESTS = 100`) but are not enforced anywhere in the current codebase.

**Unsalted credential hashing.** Worker auth tokens are SHA-256 of `"user_id:password"` with no salt. This is adequate for a private LAN but vulnerable to precomputation attacks if credentials are ever exposed. A production deployment should use bcrypt or Argon2 with per-user salts.

**Single coordinator.** There is no coordinator replication or failover. A coordinator restart clears the in-memory job queue; the watchdog requeues jobs that were `running` at restart, but jobs that were `queued` in memory and not yet persisted may be lost.

**Worker auth fallback.** Workers that connect without `auth_token` are currently accepted. This allows unauthenticated workers to join the mesh and receive jobs. Disable this in `coordinator/websocket.py` for production.

**Docker socket exposure.** Workers mount `/var/run/docker.sock` to manage job containers. A compromised worker process with access to the Docker socket can escape isolation. Run workers with a dedicated low-privilege user and consider using rootless Docker or a socket proxy (e.g. `tecnativa/docker-socket-proxy`) to restrict the operations workers can perform.

---

## Hardening checklist

- [ ] Place nginx or Caddy with TLS in front of ports 8080 and 8081
- [ ] Add authentication to HTTP endpoints (Basic Auth at proxy, or implement API keys)
- [ ] Restrict `/admin/*` endpoints to trusted IPs via firewall or proxy ACL
- [ ] Disable the no-auth worker fallback in `coordinator/websocket.py`
- [ ] Replace SHA-256 credential hashing with bcrypt or Argon2
- [ ] Use rootless Docker or a Docker socket proxy on worker machines
- [ ] Set `network_disabled: true` in job limits for workloads that do not need outbound access
- [ ] Implement rate limiting on job submission endpoints
- [ ] Replace base Docker images with distroless or custom minimal images
- [ ] Run the coordinator behind a process supervisor (systemd, supervisord) with automatic restart

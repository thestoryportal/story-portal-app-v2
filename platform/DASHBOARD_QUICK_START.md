# Dashboard Quick Start Guide

## Starting the Dashboard

The easiest way to start the L10 Agent Dashboard with all dependencies:

```bash
cd platform
./start_dashboard.sh
```

This script will:
- ✅ Activate the Python virtual environment
- ✅ Check for required packages
- ✅ Stop any existing services on ports 8002 and 8010
- ✅ Start L01 Data Layer on port 8002
- ✅ Start L10 Dashboard on port 8010
- ✅ Wait for both services to be ready
- ✅ Save process IDs for clean shutdown

## Accessing the Dashboard

Once started, access the dashboard at:
- **Dashboard UI**: http://localhost:8010/
- **Data Layer API**: http://localhost:8002/

## Stopping the Dashboard

```bash
cd platform
./stop_dashboard.sh
```

This will gracefully stop both services.

## Viewing Logs

Logs are stored in the `platform/logs/` directory:

```bash
# View L10 Dashboard logs
tail -f platform/logs/l10.log

# View L01 Data Layer logs
tail -f platform/logs/l01.log
```

## Troubleshooting

### Dashboard shows connection errors

If you see 401 authentication errors or connection failures:

1. **Ensure L01 is running**: Check http://localhost:8002/health/live
2. **Check the API key**: L01 uses default dev key "dev_key_CHANGE_IN_PRODUCTION"
3. **Verify venv Python**: Services must run with `.venv/bin/python`, not system Python
4. **Restart both services**: Use `./stop_dashboard.sh` then `./start_dashboard.sh`

### WebSocket disconnections

If the status bar shows frequent disconnections:

1. **Check websockets package**: Ensure `websockets` is installed in venv
   ```bash
   source .venv/bin/activate
   pip list | grep websockets
   ```
2. **Verify L10 is using venv Python**: Check the process with `ps aux | grep L10`
3. **Restart with the script**: `./start_dashboard.sh` ensures correct Python

### Port already in use

The startup script automatically kills existing processes on ports 8002 and 8010. If you still see port conflicts:

```bash
# Manually kill processes
lsof -ti :8002 | xargs kill -9
lsof -ti :8010 | xargs kill -9

# Then restart
./start_dashboard.sh
```

## Service Dependencies

The L10 Dashboard requires:
- **L01 Data Layer** (port 8002) - For persistent data storage
- **PostgreSQL** (port 5432) - Database backend for L01
- **Redis** (port 6379) - Cache and message broker

Ensure PostgreSQL and Redis are running before starting the dashboard:

```bash
# Check PostgreSQL
psql -h localhost -p 5432 -U postgres -l

# Check Redis
redis-cli ping
```

## Architecture

```
┌─────────────────────────────────────┐
│   L10 Human Interface Dashboard     │
│         (port 8010)                 │
│  - Web UI                           │
│  - WebSocket for real-time updates  │
│  - Agent/Goal management            │
└──────────────┬──────────────────────┘
               │ HTTP + WebSocket
               │ (with API key auth)
┌──────────────▼──────────────────────┐
│      L01 Data Layer API             │
│         (port 8002)                 │
│  - Centralized persistence          │
│  - Event sourcing                   │
│  - API key authentication           │
└──────────────┬──────────────────────┘
               │
         ┌─────┴──────┐
         │            │
    ┌────▼───┐   ┌────▼───┐
    │  PostgreSQL │ Redis  │
    │   :5432    │  :6379 │
    └────────┘   └────────┘
```

## Configuration

### L01 API Authentication

L01 Data Layer uses API key authentication. The default development key is:
```
dev_key_CHANGE_IN_PRODUCTION
```

To use custom keys, set environment variable before starting:
```bash
export L01_API_KEYS="your_key_1,your_key_2"
./start_dashboard.sh
```

To disable authentication (NOT recommended for production):
```bash
export L01_AUTH_DISABLED=true
./start_dashboard.sh
```

### Environment Variables

- `L01_API_KEYS`: Comma-separated list of valid API keys
- `L01_DEFAULT_API_KEY`: Default key if L01_API_KEYS not set (default: "dev_key_CHANGE_IN_PRODUCTION")
- `L01_AUTH_DISABLED`: Set to "true" to disable authentication (not recommended)

## Production Deployment

For production environments:

1. **Use a process manager**: systemd, supervisor, or PM2
2. **Set custom API keys**: Never use the default dev key
3. **Enable HTTPS**: Put services behind nginx or traefik
4. **Configure CORS**: Update allowed origins in L01 main.py
5. **Remove --reload flag**: Edit start_dashboard.sh to remove `--reload` from L10 startup

Example systemd service:

```ini
[Unit]
Description=L10 AI Agent Dashboard
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/platform
ExecStart=/path/to/platform/.venv/bin/python -m uvicorn src.L10_human_interface.app:app --host 0.0.0.0 --port 8010
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

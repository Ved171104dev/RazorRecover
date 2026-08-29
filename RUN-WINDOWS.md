# Run RazorRecover on Windows

The repository includes a local demo launcher that installs dependencies, creates
an isolated Python environment, starts FastAPI with a persistent SQLite demo
database, waits for the API health check, and then starts Next.js.

From PowerShell or the VS Code terminal:

```powershell
cd "D:\Ai razpay\razorrecover"
powershell -ExecutionPolicy Bypass -File .\run-local.ps1
```

Open <http://localhost:3000>. Keep the terminal open. Press `Ctrl+C` to stop both
services.

On later runs, dependency installation can be skipped:

```powershell
.\run-local.ps1 -SkipInstall
```

This launcher is intentionally for local demonstration. The Docker Compose stack
continues to use PostgreSQL and Redis for the complete deployment architecture.

## Troubleshooting

- Python 3.11+ and Node.js 20+ must be available in `PATH`.
- If ports 3000 or 8000 are occupied, use
  `.\run-local.ps1 -WebPort 3001 -ApiPort 8001`.
- The frontend is started only after `GET /health` returns HTTP 200, preventing
  signup/login pages from opening against an unavailable API.

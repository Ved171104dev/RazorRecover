# Run RazorRecover on Windows

The local launcher installs dependencies, creates an isolated Python virtual
environment, applies migrations to a persistent SQLite database, starts FastAPI,
waits for its health check, and then starts Next.js.

From PowerShell or the VS Code terminal:

```powershell
cd "D:\Ai razpay\razorrecover"
powershell -ExecutionPolicy Bypass -File .\run-local.ps1
```

Open <http://localhost:3000>, create your own account, and then open **Data
Sources**. New workspaces contain no seeded payments. Connect Razorpay Test Mode
or import the included `data/payment-import-template.csv` file.

Keep the terminal open. Press `Ctrl+C` to stop both services. On later runs:

```powershell
.\run-local.ps1 -SkipInstall
```

The local database is `backend/razorrecover.db`, so accounts and imported data
survive restarts. The Docker Compose deployment uses PostgreSQL and Redis.

## Troubleshooting

- Install Python 3.11+ and Node.js 20+ and ensure both are in `PATH`.
- If ports are occupied, run
  `.\run-local.ps1 -WebPort 3001 -ApiPort 8001`.
- If signup shows `Failed to fetch`, verify that <http://localhost:8000/health>
  returns JSON and that the launcher terminal has not been closed.
- Razorpay execution remains unavailable until a valid `rzp_test_` connection is
  verified from **Data Sources**.

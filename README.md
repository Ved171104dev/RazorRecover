# RazorRecover — Autonomous Revenue Recovery Intelligence

RazorRecover is a merchant-facing revenue recovery application for failed
payments and checkout abandonment. It detects revenue at risk, diagnoses the
cause, compares interventions, applies deterministic policy, executes a
customer-initiated Razorpay Test Mode Payment Link, verifies the provider result,
attributes recovered revenue once, and updates experiments and strategy history.

This repository is **real-data-only by default**:

- Signup creates an empty, isolated merchant workspace.
- Payment history comes from a verified Razorpay Test Mode connection or a
  validated merchant file import.
- Missing provider credentials block execution; they never trigger a silent
  simulation.
- Revenue is counted only after Razorpay API state or a valid signed webhook
  verifies payment success.
- Razorpay Test Mode uses real Razorpay APIs but moves no real money.

## Differentiating intelligence

- **Causal incremental revenue:** merchants can start a deterministic 10% no-contact holdout against a 90% policy-approved treatment. Natural recovery and AI-attributed recovery remain separate, and no winner is declared before 30 completed outcomes per group.
- **Recovery proof receipts:** every action exposes its problem evidence, model estimate, policy result, merchant approval, delivery state, signed-webhook evidence, verified attribution, and financial audit timeline.
- **Live incident radar:** the latest one-hour payment failure clusters are compared with a preceding 23-hour baseline by payment method, provider/bank, and failure code.
- **Shadow mode:** the system scores, recommends, governs, and audits without contacting a customer or executing a provider action.
- **Webhook reliability center:** signed, rejected, duplicate, pending, processed, and failed webhook counts are shown without exposing raw financial payloads.
- **Honest delivery tracking:** link creation, merchant-shared delivery, payment, expiry, cancellation, and failure are distinct states. Creating a Razorpay Payment Link never claims that SMS or email was delivered.
- **Provider-backed outreach:** approved actions can invoke Razorpay's official Payment Link email or SMS notification endpoint. Customer opt-out, quiet hours, missing contact data, and daily contact ceilings are checked first.
- **Reconciliation:** executed links receive scheduled and merchant-triggered Razorpay API verification when a webhook is delayed.
- **Maker–checker:** optional separation of duties prevents the action creator from approving the same recovery; owners can add merchant-scoped Analyst and Approver accounts.
- **Model quality gate:** a database-derived Brier score is shown after verified outcomes and can block execution when calibration exceeds the merchant threshold.
- **Incident automation and webhook replay:** critical provider clusters can activate a timed circuit breaker, while only signed failed/pending webhooks can be safely reprocessed.

## Core loop

```mermaid
flowchart LR
 D[Detect] --> G[Diagnose] --> C[Decide] --> P[Govern]
 P --> E[Execute] --> V[Verify] --> M[Measure] --> L[Learn]
```

```mermaid
flowchart TD
 UI[Next.js / strict TypeScript] --> API[FastAPI]
 API --> Risk[Risk + ML inference]
 API --> Decision[Decision + policy]
 Decision --> Executor[Recovery executor]
 Executor --> Provider[PaymentProvider / RazorpayAdapter]
 Provider --> RP[Razorpay Test Mode]
 RP --> Hook[Raw signed webhook]
 Hook --> Worker[Durable embedded processor or RQ worker]
 Worker --> Verify[Verification + unique attribution]
 Verify --> PG[(PostgreSQL)]
 Verify --> Learning[Experiments + strategy performance]
```

## Implemented capabilities

- Signup, login, logout, seven-day server-side sessions, Argon2id hashing,
  HTTP-only cookies, CSRF checks, rate limits, protected pages, and merchant-level
  isolation.
- SQLAlchemy models and Alembic migrations with foreign keys, indexes, and unique
  constraints for webhook, action, import, and recovery idempotency.
- Encrypted per-merchant Razorpay Test Mode credentials; secrets never return to
  the browser.
- Razorpay order/payment synchronization, Payment Link creation, raw-body HMAC
  webhook verification, duplicate delivery handling, and provider verification.
- CSV, TSV, XLSX, XLS, JSON, and machine-readable PDF-table ingestion with
  signature checks, SHA-256 idempotency, and integer-paise validation.
- Deterministic risk, root cause, expected recovery, policy, approval, execution,
  verification, attribution, experiment, audit, and strategy-learning services.
- Scikit-learn recovery probability pipeline with reproducible generation,
  training, and evaluation scripts.
- Database-grounded merchant-finance assistant for risk, recovered GMV/ARR,
  recovery cost, gateway lift, incrementality, experiments, and policy, with
  optional LLM narration and a deterministic fallback. Personal investment,
  trading, tax, lending, and legal advice remain explicitly out of scope.
- Responsive Next.js dashboard, risk analysis, decisions, actions, experiments,
  audit, assistant, data sources, and settings pages.

## Quick start on Windows / VS Code

Prerequisites: Python 3.11+ and Node.js 20+.

```powershell
cd "D:\Ai razpay\razorrecover"
powershell -ExecutionPolicy Bypass -File .\run-local.ps1
```

Then open <http://localhost:3000>, choose **Create account**, and use your own
valid email address (for example, yourname@gmail.com) and a password containing
uppercase, lowercase, and a number (minimum 10
characters). There is no shared demo login.

The launcher uses persistent `backend/razorrecover.db`. For subsequent runs:

```powershell
.\run-local.ps1 -SkipInstall
```

## Docker setup

Prerequisites: Docker Desktop and Docker Compose.

```powershell
cd "D:\Ai razpay\razorrecover"
Copy-Item .env.example .env
# Replace AUTH_SECRET and CONNECTION_ENCRYPTION_KEY in .env
docker compose up --build
```

The stack starts `web`, `api`, `worker`, PostgreSQL, and Redis. The API applies
migrations and starts without seeding merchant data. Open
<http://localhost:3000> and create an account.

## Native development with PostgreSQL

```powershell
docker compose up -d postgres redis

cd "D:\Ai razpay\razorrecover\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DATABASE_URL = "postgresql+psycopg://razorrecover:razorrecover_dev@localhost:5432/razorrecover"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:EMBEDDED_WORKER_ENABLED = "true"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```powershell
cd "D:\Ai razpay\razorrecover\apps\web"
npm install
$env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
npm run dev
```

For a dedicated RQ process instead, set `EMBEDDED_WORKER_ENABLED=false` on the
API and run `python -m app.workers.runner` in another backend terminal. Do not
run both modes unless you intentionally need redundant consumers; atomic event
claiming still prevents duplicate webhook processing.

## Environment variables

Copy `.env.example` to `.env`.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL/SQLite SQLAlchemy URL |
| `REDIS_URL` | Distributed rate limits and optional external RQ jobs |
| `AUTH_SECRET` | Strong independent session secret, 32+ characters |
| `CONNECTION_ENCRYPTION_KEY` | Strong independent credential-encryption key |
| `PUBLIC_API_URL` | Public API origin used for merchant webhook URLs |
| `API_ORIGIN` | Exact allowed frontend origin |
| `NEXT_PUBLIC_API_URL` | Browser-visible API base URL; contains no secrets |
| `RAZORPAY_KEY_ID` | Optional deployment-level `rzp_test_` fallback |
| `RAZORPAY_KEY_SECRET` | Optional server-only Test Mode secret |
| `RAZORPAY_WEBHOOK_SECRET` | Optional fallback webhook signing secret |
| `OPENAI_API_KEY` | Optional server-only narration provider |
| `OPENAI_MODEL` | Optional narration model name |
| `COOKIE_SECURE` | Set `true` behind HTTPS |
| `AUTO_CREATE_SCHEMA` | Local-only schema compatibility switch |
| `EMBEDDED_WORKER_ENABLED` | Run the durable PostgreSQL-backed processor inside FastAPI |
| `EMBEDDED_WORKER_INTERVAL_SECONDS` | Embedded processor polling interval; minimum 1 second |
| `POSTGRES_PASSWORD` | Docker PostgreSQL password |

Generate secrets:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Merchant onboarding

After signup, open **Data Sources** and choose one or both ingestion paths.

### Razorpay Test Mode

1. Switch Razorpay Dashboard to **Test Mode** and generate API keys.
2. Enter the `rzp_test_` Key ID, Key Secret, and webhook signing secret in
   RazorRecover **Data Sources**.
3. RazorRecover verifies the API connection before encrypting the credentials.
4. Copy the unique webhook URL shown for the merchant into Razorpay Dashboard.
5. Subscribe to `payment.authorized`, `payment.captured`, `payment.failed`,
   `order.paid`, `payment_link.paid`, `payment_link.cancelled`, and
   `payment_link.expired`.
6. Use **Test Connection** whenever credentials or deployment networking change.
7. Click **Sync Last 30 Days** to import orders and payments.

The Data Sources go-live checklist is derived from merchant-scoped database
state. Its operational strip reports API, database, Redis, and recovery-processor health;
the webhook reliability center separately reports signed delivery, duplicate
suppression, processing failures, and replay eligibility.

### Payment history files

Supported formats are `.csv`, `.tsv`, `.xlsx`, `.xls`, `.json`, and `.pdf`.
Create a CSV, TSV, Excel, JSON, or machine-readable PDF using the schema below. Required
columns:

```csv
external_id,order_id,customer_email,customer_name,amount_paise,status,method,failure_code
pay_001,order_001,buyer@example.com,Example Buyer,349900,failed,upi,UPI_TIMEOUT
```

Amounts are integer paise. Files are limited to 10 MB / 5,000 payment rows.
Re-uploading the identical file does not duplicate data. JSON may be an array of
payment objects or an object containing a `payments` array. PDF files must contain
a selectable, machine-readable table; scanned image PDFs are rejected because the
application never guesses financial fields. Imported files supply historical
evidence but do not bypass the Razorpay connection required for Payment Link
execution.

Each uploaded merchant file appears in **Data Sources → Ingestion history**.
Choose **View / Edit** to inspect its normalized payment rows, add a row, edit
customer/payment fields, remove a row, or remove the whole file. Changes
immediately refresh deterministic risk and decision records. A row becomes
immutable after a recovery action is created so executed or verified financial
history cannot be rewritten. Removing a file deletes only payment rows that are
not still supplied by another active imported file. All mutations are
merchant-scoped, CSRF-protected, and written to the financial audit log.

## Recovery and webhook flow

1. Import or synchronize a failed payment.
2. Open **Revenue Risk** and inspect evidence and three candidates.
3. Create a Payment Link recovery. Policy may auto-allow, require approval, or
   block it.
4. The API creates the Payment Link through Razorpay and stores its real provider
   ID and URL.
5. The customer completes a Razorpay test payment.
6. Razorpay sends the event to
   `POST /api/webhooks/razorpay/{merchant_token}`.
7. The API validates `X-Razorpay-Signature` against the untouched raw body,
   persists the event idempotently, and queues processing.
8. Verification updates payment/link state. A unique database attribution records
   the recovered amount once and updates audit and experiment metrics.

Invalid signatures never mutate financial state. Duplicate events and duplicate
actions are safe. A failed Razorpay call is recorded as failed and never reported
as recovery.

## ML scripts

Synthetic data is used only to train and evaluate the model; it is not loaded
into merchant workspaces.

```powershell
cd "D:\Ai razpay\razorrecover\backend"
python scripts/generate_demo_data.py
python scripts/train_model.py
python scripts/evaluate_model.py
```

Metrics are calculated and saved under `backend/artifacts`; the UI does not claim
unmeasured accuracy.

## Tests and acceptance

```powershell
cd "D:\Ai razpay\razorrecover\backend"
pytest -q

cd "D:\Ai razpay\razorrecover\apps\web"
npm test -- --run
npm run typecheck
npm run lint
npm run build

cd "D:\Ai razpay\razorrecover"
docker compose config
```

With the local services running:

```powershell
cd "D:\Ai razpay\razorrecover\backend"
.\.venv\Scripts\python.exe scripts\acceptance_test.py
```

The acceptance script verifies empty signup, payment-file import, deterministic risk and
candidates, provider gating without credentials, database-grounded assistant,
logout protection, persistence, tenant isolation, and frontend routes.

## Deployment

The simplest no-Docker path is the included Render Blueprint. It provisions the
Next.js frontend, FastAPI service with a durable embedded processor, PostgreSQL,
and Redis-compatible Key Value, runs migrations, and keeps authentication
same-origin through a server-side frontend proxy. The embedded processor claims
persisted webhook events atomically and reconciles due actions without requiring
a paid Render background-worker service.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Ved171104dev/RazorRecover)

See [DEPLOY-RENDER.md](DEPLOY-RENDER.md) for the exact deployment and Razorpay
Test Mode webhook steps. Docker remains available for local development but is
not required for this deployment path.

### Vercel frontend + Render backend

The optional split deployment uses Vercel for `apps/web` and Render for the
FastAPI API with embedded recovery processing, PostgreSQL, and Redis. In Vercel, set the project Root
Directory to `apps/web` and configure `API_PROXY_URL` as the public HTTPS Render
API origin, for example `https://razorrecover-api.onrender.com`. Leave
`NEXT_PUBLIC_API_URL` unset in Vercel so browser requests remain same-origin at
`/api/*`; Next.js securely proxies them to Render and authentication cookies stay
on the frontend domain.

On the Render API, set `API_ORIGIN` to the production Vercel URL,
`PUBLIC_API_URL` to the public Render API URL, and `COOKIE_SECURE=true`. Razorpay
webhooks must target `PUBLIC_API_URL`, never the Vercel frontend or localhost.
See [DEPLOY-RENDER.md](DEPLOY-RENDER.md) for the complete variable table.

## Security model

Money is integer paise. Secrets remain server-side and merchant credentials are
encrypted at rest. State-changing browser calls require both an authenticated
HTTP-only session and CSRF header. Every merchant query is tenant scoped. Unique
constraints protect imported hashes, provider IDs, webhook event IDs, action
idempotency keys, and payment attribution. Financial audit records are separate
from application logs.

## Honest limitations

- Razorpay does not support arbitrarily retrying a failed customer payment;
  RazorRecover uses legitimate customer-initiated Payment Links.
- Test Mode executes real Razorpay API workflows but moves no real money.
- Actual Razorpay network calls and public webhook delivery require the merchant's
  Test Mode credentials and a public HTTPS API URL.
- Forgot-password email delivery needs an external email provider; the endpoint is
  enumeration-safe but does not send mail until one is configured.

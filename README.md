# RazorRecover — Autonomous Revenue Recovery Intelligence

RazorRecover answers one operational question: **we found revenue at risk—what should we do, why was it allowed, did it work, and how much did it actually recover?**

It implements one deep recovery engine for failed payments, alternate-payment decisioning, customer-initiated Razorpay Payment Links, and checkout abandonment. Financial calculations and policy decisions are deterministic; the assistant can explain database evidence but cannot create financial truth.

## Core loop

```mermaid
flowchart LR
 D[Detect] --> G[Diagnose]
 G --> C[Decide]
 C --> P[Govern]
 P --> E[Execute]
 E --> V[Verify]
 V --> M[Measure]
 M --> L[Learn]
```

```mermaid
flowchart TD
 UI[Next.js / TypeScript UI] --> API[FastAPI]
 API --> Risk[Risk + ML inference]
 API --> Strategy[Decision + policy]
 Strategy --> Executor[Recovery executor]
 Executor --> Provider[PaymentProvider / RazorpayAdapter]
 Provider --> RP[Razorpay Test Mode]
 RP --> Hook[Signed webhook]
 Hook --> Redis[Redis / RQ worker]
 Redis --> Verify[Verification + attribution]
 Verify --> PG[(PostgreSQL)]
 Verify --> Experiment[Experiment + strategy performance]
```

## What is implemented

- Signup, login, logout, seven-day server-side sessions, Argon2id password hashing, HTTP-only cookies, SameSite cookies, CSRF tokens, protected Next.js routes, API authorization, and merchant-level query isolation.
- PostgreSQL domain schema, foreign keys, unique idempotency/attribution constraints, indexes, Alembic migration, and durable audit/webhook records.
- `PaymentProvider` interface and server-only `RazorpayAdapter` using `https://api.razorpay.com/v1` with HTTP Basic auth, timeouts, error handling, create/fetch order, list order payments, fetch payment, and create/fetch Payment Link.
- Raw-body Razorpay webhook signature verification before JSON parsing, event persistence, duplicate event handling, Redis/RQ processing, and verified recovery attribution.
- Deterministic risk, root-cause evidence, expected recovery in integer paise, policy guardrails, approval flow, idempotent execution, verification, experiment metrics, and transparent strategy learning.
- A scikit-learn recovery probability pipeline trained from 100,000 deterministic generated attempts. Metrics are calculated by the script and written to `backend/artifacts/evaluation_metrics.json`; they are never hardcoded.
- A tool-grounded merchant assistant with deterministic fallback when no LLM key is configured.
- Dark responsive fintech UI and a controlled demo animation whose final state comes from backend transactions.

## Honest operating modes

- **DEMO SIMULATION MODE** works without Razorpay or OpenAI credentials. Simulated provider actions are labelled `SIMULATED — RAZORPAY TEST MODE NOT CONNECTED`. The deterministic demo verification is explicitly marked simulation and never represented as real money.
- **LIVE TEST MODE — NO REAL MONEY** requires an `rzp_test_` key, server-side secret, and webhook secret. Payment Links are real Razorpay Test Mode URLs. Recovery remains unverified until a signed webhook/provider outcome confirms it.

The adapter intentionally rejects non-test Razorpay key IDs.

## Local Docker setup

Prerequisites: Docker Desktop and Docker Compose.

```powershell
cd "D:\Ai razpay\razorrecover"
Copy-Item .env.example .env
docker compose up --build
```

The API container runs `alembic upgrade head`, seeds the demo merchant idempotently, and starts FastAPI. Open `http://localhost:3000`.

Demo credentials:

```text
demo@razorrecover.app
DemoPass123!
```

Or use Signup to create a separate merchant-isolated workspace.

## Native development

PostgreSQL and Redis:

```powershell
docker compose up -d postgres redis
```

Backend:

```powershell
cd "D:\Ai razpay\razorrecover\backend"
python -m pip install -r requirements.txt
$env:DATABASE_URL = "postgresql+psycopg://razorrecover:razorrecover_dev@localhost:5432/razorrecover"
$env:REDIS_URL = "redis://localhost:6379/0"
alembic upgrade head
python -m scripts.seed_demo
uvicorn app.main:app --reload --port 8000
```

Worker:

```powershell
cd "D:\Ai razpay\razorrecover\backend"
$env:DATABASE_URL = "postgresql+psycopg://razorrecover:razorrecover_dev@localhost:5432/razorrecover"
$env:REDIS_URL = "redis://localhost:6379/0"
python -m app.workers.runner
```

Frontend:

```powershell
cd "D:\Ai razpay\razorrecover\apps\web"
npm install
$env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
npm run dev
```

## Environment variables

Copy `.env.example`. Required runtime settings:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL SQLAlchemy URL |
| `REDIS_URL` | Redis/RQ and distributed rate-limit URL |
| `AUTH_SECRET` | Deployment secret; use at least 32 random characters |
| `API_ORIGIN` | Allowed browser origin |
| `NEXT_PUBLIC_API_URL` | Public API base URL (never contains secrets) |
| `RAZORPAY_KEY_ID` | `rzp_test_...` Test Mode key ID |
| `RAZORPAY_KEY_SECRET` | Test Mode secret, API/worker only |
| `RAZORPAY_WEBHOOK_SECRET` | Dashboard webhook signing secret |
| `OPENAI_API_KEY` | Optional server-side narrative provider |
| `DEMO_MODE` | Enables deterministic simulation |
| `COOKIE_SECURE` | Set `true` behind HTTPS |

Generate a secret, for example:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Razorpay Test Mode configuration

1. In Razorpay Dashboard, switch to **Test Mode**.
2. Create Test Mode API keys and set `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` only on the API and worker.
3. In RazorRecover Settings, confirm the masked `rzp_test_` key and disable simulation.
4. Create a public HTTPS tunnel or deploy the API.
5. In Razorpay Dashboard, create a webhook pointing to:
   `https://YOUR_API_HOST/api/webhooks/razorpay`
6. Subscribe to `payment.authorized`, `payment.captured`, `payment.failed`, `order.paid`, and `payment_link.paid`.
7. Put the exact same webhook secret in `RAZORPAY_WEBHOOK_SECRET`.
8. Create a Payment Link from a recovery opportunity, complete it with Razorpay test payment details, and wait for the signed webhook.

The endpoint rejects invalid signatures and processes duplicate deliveries idempotently.

## Demo walkthrough

1. Login or Signup.
2. Open Dashboard; data source labels distinguish seeded and Razorpay Test Mode data.
3. Open Revenue Risk and select the ₹3,499 UPI-timeout opportunity.
4. Inspect structured evidence and three candidate interventions.
5. Review expected recovery, confidence, and deterministic policy.
6. Create the Payment Link recovery.
7. In demo mode, run **Run Recovery Demo** to execute and explicitly simulate verification.
8. In Test Mode, open the real Razorpay URL, complete a test payment, and wait for verification.
9. Confirm Recovered Revenue changes only after attribution.
10. Open Actions, Audit, Experiments, and ask the Assistant why the decision was made.
11. Logout and confirm protected routes redirect to Login.

## Demo data and ML

```powershell
cd "D:\Ai razpay\razorrecover\backend"
python scripts/generate_demo_data.py
python scripts/train_model.py
python scripts/evaluate_model.py
```

The fixed seed recreates 100,000 attempts, 15,000 customer IDs, 5,000 order IDs, UPI timeout clusters, retry patterns, card preference, device/time patterns, and recovery labels.

## Tests and checks

```powershell
cd "D:\Ai razpay\razorrecover\backend"
pytest -q

cd "D:\Ai razpay\razorrecover\apps\web"
npm test
npm run typecheck
npm run lint
npm run build

cd "D:\Ai razpay\razorrecover"
docker compose config
```

Tests cover money calculations, risk, expected recovery, policy, authentication, route protection, webhook signatures/duplicates, execution idempotency, tenant isolation, attribution uniqueness, dashboard, and logout.

## Security model

Secrets never enter the browser bundle. Money is integer paise. Every tenant query includes `merchant_id`. State-changing browser calls require an authenticated HTTP-only session plus CSRF header. Login/signup are rate limited through Redis with a local degradation path. Provider actions are server-only. Unique constraints protect webhook event IDs, action idempotency keys, recovery action/payment attribution, and Razorpay payment attribution. Invalid webhooks never update financial state. Financial audit records are stored separately from application logs.

## Deployment

- Frontend: deploy `apps/web` to Vercel and set `NEXT_PUBLIC_API_URL`.
- API/worker: deploy `backend` to Railway, Render, or Fly.io as two processes (`uvicorn...` and `python -m app.workers.runner`).
- PostgreSQL: Neon, Supabase, or managed PostgreSQL.
- Redis: Upstash Redis or another managed Redis.
- Run `alembic upgrade head` as the API release command.
- Use HTTPS, `COOKIE_SECURE=true`, a strong `AUTH_SECRET`, exact `API_ORIGIN`, and Test Mode Razorpay keys.

## Limitations

Razorpay does not expose an API that arbitrarily retries a failed customer payment. RazorRecover therefore uses legitimate customer-initiated Payment Links or a clearly labelled deterministic simulation. Real Razorpay Test Mode calls and public webhook delivery require credentials and a public HTTPS endpoint; without those external inputs the repository can validate adapter and signature behavior but cannot honestly claim an end-to-end Razorpay network transaction was exercised.

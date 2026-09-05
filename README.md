# RazorRecover - Autonomous Revenue Recovery Intelligence

[![Live Demo](https://img.shields.io/badge/Live_Demo-Open_RazorRecover-B97A12?style=for-the-badge)](https://web-psi-woad-18.vercel.app)
[![Next.js](https://img.shields.io/badge/Next.js-15-111111?logo=nextdotjs)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Data-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Razorpay](https://img.shields.io/badge/Razorpay-Test_Mode-0C63E4)](https://razorpay.com/)

## [Launch the live application](https://web-psi-woad-18.vercel.app)

> Recover revenue. Prove every rupee.

RazorRecover is an autonomous, policy-governed AI agent for failed payments and checkout abandonment. It detects revenue at risk, diagnoses the likely cause, selects a bounded intervention, applies merchant rules, executes an eligible Razorpay Test Mode workflow, verifies the result, and counts recovered revenue only after trusted provider evidence.

## The problem

Payment dashboards usually stop after reporting that a transaction failed. Merchants must then decide whom to contact, which action to take, whether the action is safe, and whether it genuinely recovered money. Blind retries and generic reminders can frustrate customers, create duplicate actions, and overstate recovery.

RazorRecover closes this full loop while keeping the merchant in control.

## How the agent works

~~~mermaid
flowchart LR
 D[Detect] --> G[Diagnose] --> C[Decide] --> P[Govern]
 P --> E[Execute] --> V[Verify] --> M[Measure] --> L[Learn]
~~~

1. **Detect:** Find failed or abandoned payments worth investigating.
2. **Diagnose:** Explain the failure signal and customer context.
3. **Decide:** Compare retry, payment-link, notification, and no-action candidates.
4. **Govern:** Apply confidence thresholds, cooldowns, contact limits, quiet hours, approvals, and hard stops.
5. **Execute:** Create an approved Razorpay Test Mode recovery workflow.
6. **Verify:** Confirm success through provider state or a valid signed webhook.
7. **Measure:** Attribute recovered revenue exactly once.
8. **Learn:** Compare strategy outcomes and update performance evidence.

AI supports prediction and explanation. Deterministic services remain responsible for policy decisions, money calculations, verification, and attribution.

## Key features

- **Revenue-risk intelligence:** risk score, recovery probability, confidence, root cause, and expected recoverable value.
- **Policy-controlled actions:** recommendations can be automatically allowed, require merchant approval, or be blocked.
- **Real Razorpay Test Mode integration:** encrypted merchant credentials, payment synchronization, Payment Links, signed webhooks, and reconciliation.
- **Verified financial truth:** creating a link is not reported as recovery; provider confirmation is required.
- **Safe ingestion:** CSV, TSV, Excel, JSON, and machine-readable PDF imports with validation and file-level idempotency.
- **Recovery proof and audit:** evidence, decisions, approvals, action state, verification source, timestamps, and financial effects remain traceable.
- **Controlled experiments:** treatment and holdout groups distinguish AI-attributed recovery from natural recovery.
- **Financial assistant:** answers merchant-specific questions using database-derived figures, with a deterministic fallback.
- **Operational safeguards:** duplicate-event protection, webhook replay, incident detection, circuit breakers, shadow mode, and maker-checker approval.

## What makes it different

RazorRecover is not another analytics dashboard or unrestricted chatbot. It can progress from evidence to action, but only within merchant-defined boundaries. It separates AI narration from financial truth, prevents duplicate execution, supports genuine merchant data, and reports money only after verification. This makes the automation explainable, accountable, and measurable.

## Technology

| Layer | Technology |
|---|---|
| Frontend | Next.js, React, TypeScript |
| API | FastAPI, Pydantic |
| Data | PostgreSQL, SQLAlchemy, Alembic |
| Intelligence | scikit-learn plus deterministic decision services |
| Queue and reliability | Redis/RQ or durable embedded processing |
| Payments | Razorpay Test Mode APIs and signed webhooks |
| Security | Argon2id, HTTP-only sessions, CSRF protection, encrypted credentials |
| Hosting | Vercel frontend and Render backend |

## Try the demo

1. Open the [live application](https://web-psi-woad-18.vercel.app).
2. Create a merchant account or sign in.
3. Open **Data Sources** and upload [the sample payment dataset](data/razorrecover-merchant-payments-sample.csv).
4. Review detected opportunities under **Risk**.
5. Inspect candidates and policy outcomes under **Decisions**.
6. Follow approved, pending, blocked, and verified actions.
7. Explore **Experiments**, **Audit**, and the merchant-finance **Assistant**.

The hosted Render API uses a free instance, so the first request after inactivity may take longer while it wakes.

## Run locally

Prerequisites: Python 3.11+ and Node.js 20+.

On Windows:

~~~powershell
git clone https://github.com/Ved171104dev/RazorRecover.git
cd RazorRecover
powershell -ExecutionPolicy Bypass -File .\run-local.ps1
~~~

Open [http://localhost:3000](http://localhost:3000). For later runs, use:

~~~powershell
.\run-local.ps1 -SkipInstall
~~~

Docker users can copy `.env.example` to `.env`, replace the secrets, and run `docker compose up --build`.

## Test the project

~~~powershell
cd backend
pytest -q

cd ..\apps\web
npm test -- --run
npm run typecheck
npm run lint
npm run build
~~~

## Security and data integrity

Merchant data is isolated at the query level. Passwords are hashed, session cookies are HTTP-only, state-changing browser requests require CSRF protection, and Razorpay credentials are encrypted at rest. Unique database constraints protect payment attribution, provider IDs, imported-file hashes, webhook event IDs, and action idempotency keys. Invalid webhook signatures never mutate financial state.

The application is real-data-only by default: a new workspace is empty until the merchant connects Razorpay Test Mode or uploads a validated payment file.

## Current limitations

- Razorpay execution is restricted to Test Mode and moves no real money.
- Prediction quality depends on the quantity and quality of merchant data.
- Small experiments cannot establish strong statistical significance.
- The free hosted API may experience cold-start latency.
- Production use requires always-on infrastructure, monitoring, configured email delivery, and additional security and compliance review.

## Deployment

The frontend is deployed on Vercel and communicates with the Render-hosted FastAPI service through a same-origin server-side rewrite. Detailed Render, PostgreSQL, Redis, webhook, and environment-variable instructions are available in [DEPLOY-RENDER.md](DEPLOY-RENDER.md).

## Author

**Thakur Baldev Singh**

[![View Resume](https://img.shields.io/badge/Resume-View_on_Google_Drive-B97A12?style=for-the-badge&logo=googledrive&logoColor=white)](https://drive.google.com/file/d/1g_003kiwb7kPZoZ2VAm63jmhH9PPraVc/view?usp=drivesdk)

- [GitHub profile](https://github.com/Ved171104dev)
- [Live project](https://web-psi-woad-18.vercel.app)

---

Built by **Thakur Baldev Singh** as an academic AI revenue recovery project using Razorpay Test Mode.

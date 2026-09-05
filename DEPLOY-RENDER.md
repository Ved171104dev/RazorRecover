# Deploy RazorRecover: Vercel + Render

The production architecture uses Vercel for the Next.js frontend and a Render Blueprint for the backend services:

- FastAPI service
- PostgreSQL database
- Redis-compatible Render Key Value instance
- Durable embedded recovery processor inside the FastAPI service

Production links:

- Application: <https://web-psi-woad-18.vercel.app>
- API health: <https://razorrecover-api-ved171104dev.onrender.com/health>
- Repository: <https://github.com/Ved171104dev/RazorRecover>

## Deploy the Render backend

1. Sign in to [Render](https://dashboard.render.com/) with GitHub.
2. Open the [RazorRecover Blueprint](https://render.com/deploy?repo=https://github.com/Ved171104dev/RazorRecover).
3. Choose **Apply** after reviewing the resources. The Blueprint creates the API, PostgreSQL, and Redis-compatible Key Value services. It uses embedded recovery processing instead of a paid background worker.
4. No API keys are required during deployment. The assistant uses deterministic explanations until you optionally add an `OPENAI_API_KEY` to the API service later.
5. Wait for the API to show **Live** and confirm its `/health` endpoint.
6. Open <https://web-psi-woad-18.vercel.app> and create an account.

No local Docker installation is required. Render installs Python dependencies, runs migrations, starts the backend services, and redeploys on each push to `main`.

## Razorpay Test Mode after deployment

1. In RazorRecover, open **Data Sources**.
2. Enter the Razorpay Test Mode key ID, key secret, and a webhook signing secret.
3. Select **Verify & Connect**.
4. Copy the merchant-specific HTTPS webhook URL displayed by RazorRecover.
5. In the Razorpay dashboard, create a Test Mode webhook using that URL and the same signing secret.
6. Enable `payment.authorized`, `payment.captured`, `payment.failed`, `order.paid`, `payment_link.paid`, `payment_link.cancelled`, and `payment_link.expired`.
7. Return to Data Sources, select **Test Connection**, and confirm the API,
   database, Redis, and embedded-worker indicators before synchronizing payments.

Secrets entered in the merchant UI are sent only to FastAPI and encrypted before database storage. They are never committed to GitHub or embedded in the frontend build.

## Deploy the frontend on Vercel

Vercel hosts Next.js while Render continues to host FastAPI, PostgreSQL, Redis,
and the embedded recovery processor.

### Vercel settings

1. Import `Ved171104dev/RazorRecover` into Vercel.
2. Set **Root Directory** to `apps/web`.
3. Keep the detected Next.js build command and output settings.
4. Add `API_PROXY_URL=https://razorrecover-api-ved171104dev.onrender.com` for Production and Preview.
5. Do **not** set `NEXT_PUBLIC_API_URL`; requests must remain same-origin and use
   the server-side `/api/*` proxy.
6. Deploy. The current production URL is <https://web-psi-woad-18.vercel.app>.

### Render API settings

Set or update:

```text
API_ORIGIN=https://web-psi-woad-18.vercel.app
PUBLIC_API_URL=https://razorrecover-api-ved171104dev.onrender.com
COOKIE_SECURE=true
```

Keep `DATABASE_URL`, `REDIS_URL`, `AUTH_SECRET`, `EMBEDDED_WORKER_ENABLED=true`, and
`CONNECTION_ENCRYPTION_KEY` configured on Render. Never add Razorpay key secrets
to Vercel; merchant Test Mode credentials are submitted through the application
and encrypted by FastAPI.

After both deployments, create the Razorpay webhook using the merchant-specific
URL generated from the Render `PUBLIC_API_URL`. Test signup, login, logout,
protected-route redirects, and CSRF mutations on the Vercel domain before the
payment-flow demonstration.

# Deploy RazorRecover without Docker

The repository contains a Render Blueprint that creates the complete hosted stack:

- Next.js web application
- FastAPI service
- PostgreSQL database
- Redis-compatible Render Key Value instance
- RQ background worker

## One-click deployment

1. Sign in to [Render](https://dashboard.render.com/) with GitHub.
2. Open the [RazorRecover Blueprint](https://render.com/deploy?repo=https://github.com/Ved171104dev/RazorRecover).
3. Choose **Apply** after reviewing the resources and price. The background worker uses Render's smallest paid worker plan; the web services, Postgres, and Key Value use their available free plans.
4. No API keys are required during deployment. The assistant uses deterministic explanations until you optionally add an `OPENAI_API_KEY` to the API service later.
5. Wait for the API and web services to show **Live**.
6. Open `https://razorrecover-web-ved171104dev.onrender.com` and create an account.

No local Docker installation is required. Render installs Python and Node dependencies, runs migrations, starts the services, and redeploys on each push to `main`.

## Razorpay Test Mode after deployment

1. In RazorRecover, open **Data Sources**.
2. Enter the Razorpay Test Mode key ID, key secret, and a webhook signing secret.
3. Select **Verify & Connect**.
4. Copy the merchant-specific HTTPS webhook URL displayed by RazorRecover.
5. In the Razorpay dashboard, create a Test Mode webhook using that URL and the same signing secret.
6. Enable `payment.authorized`, `payment.captured`, `payment.failed`, `order.paid`, `payment_link.paid`, `payment_link.cancelled`, and `payment_link.expired`.
7. Return to Data Sources, select **Test Connection**, and confirm the API,
   database, Redis, and worker indicators before synchronizing payments.

Secrets entered in the merchant UI are sent only to FastAPI and encrypted before database storage. They are never committed to GitHub or embedded in the frontend build.

## Optional: deploy the frontend on Vercel

Use this split when you want Vercel to host Next.js while Render continues to
host FastAPI, PostgreSQL, Redis, and the RQ worker.

### Vercel settings

1. Import `Ved171104dev/RazorRecover` into Vercel.
2. Set **Root Directory** to `apps/web`.
3. Keep the detected Next.js build command and output settings.
4. Add `API_PROXY_URL=https://<your-render-api>.onrender.com`.
5. Do **not** set `NEXT_PUBLIC_API_URL`; requests must remain same-origin and use
   the server-side `/api/*` proxy.
6. Deploy and copy the final production URL.

### Render API settings

Set or update:

```text
API_ORIGIN=https://<your-vercel-project>.vercel.app
PUBLIC_API_URL=https://<your-render-api>.onrender.com
COOKIE_SECURE=true
```

Keep `DATABASE_URL`, `REDIS_URL`, `AUTH_SECRET`, and
`CONNECTION_ENCRYPTION_KEY` configured on Render. Never add Razorpay key secrets
to Vercel; merchant Test Mode credentials are submitted through the application
and encrypted by FastAPI.

After both deployments, create the Razorpay webhook using the merchant-specific
URL generated from the Render `PUBLIC_API_URL`. Test signup, login, logout,
protected-route redirects, and CSRF mutations on the Vercel domain before the
payment-flow demonstration.

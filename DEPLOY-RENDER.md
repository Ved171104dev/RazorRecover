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

from __future__ import annotations

import os
import time

import httpx

API = os.getenv("ACCEPTANCE_API_URL", "http://127.0.0.1:8000").rstrip("/")
WEB = os.getenv("ACCEPTANCE_WEB_URL", "http://localhost:3000").rstrip("/")


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def csrf(client: httpx.Client) -> dict[str, str | None]:
    return {"X-CSRF-Token": client.cookies.get("rr_csrf")}


def main() -> None:
    suffix = time.time_ns()
    email = f"acceptance-{suffix}@example.com"
    password = "Acceptance123"
    csv_data = (
        "external_id,order_id,customer_email,customer_name,amount_paise,status,method,failure_code\n"
        f"pay-{suffix},order-{suffix},buyer-{suffix}@example.com,Acceptance Buyer,349900,failed,upi,UPI_TIMEOUT\n"
    )
    with httpx.Client(base_url=API, timeout=60) as client:
        signup = client.post(
            "/api/auth/signup",
            json={
                "name": "Acceptance Owner",
                "email": email,
                "password": password,
                "merchant_name": "Acceptance Merchant",
            },
        )
        ok(signup.status_code == 201, f"signup {signup.status_code} {signup.text}")
        empty = client.get("/api/dashboard")
        ok(empty.status_code == 200, "dashboard")
        ok(empty.json()["onboarding"]["payment_count"] == 0, "workspace starts empty")
        operations = client.get("/api/operations/health")
        ok(operations.status_code == 200, "operations health")
        ok(operations.json()["worker"]["mode"] == "embedded_database_worker", "embedded worker mode")
        ok(operations.json()["worker"]["status"] in {"starting", "healthy"}, "embedded worker healthy")
        imported = client.post(
            "/api/data-sources/import/file",
            headers=csrf(client),
            files={"file": ("payments.csv", csv_data, "text/csv")},
        )
        ok(imported.status_code == 200, f"csv import {imported.status_code} {imported.text}")
        risks = client.get("/api/risk/opportunities").json()["items"]
        ok(len(risks) == 1, "one imported risk")
        detail = client.get(f"/api/risk/opportunities/{risks[0]['id']}")
        ok(detail.status_code == 200, "risk detail")
        ok(len(detail.json()["decision"]["candidates"]) == 3, "three candidates")
        execution = client.post(
            "/api/recovery/payment-link",
            headers=csrf(client),
            json={"opportunity_id": risks[0]["id"]},
        )
        ok(execution.status_code == 422, "execution blocked without Razorpay")
        ok("Connect a verified Razorpay" in execution.text, "clear provider setup error")
        assistant = client.post(
            "/api/assistant/query",
            headers=csrf(client),
            json={"query": "Why did you choose this intervention?"},
        )
        ok(assistant.status_code == 200, "assistant")
        ok(assistant.json()["numbers_source"] == "database", "assistant is grounded")
        risk_id = risks[0]["id"]
        logout = client.post("/api/auth/logout", headers=csrf(client))
        ok(logout.status_code == 200, "logout")
        ok(client.get("/api/dashboard").status_code == 401, "protected after logout")
        login = client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        ok(login.status_code == 200, "login again")
        ok(client.get("/api/dashboard").json()["onboarding"]["payment_count"] == 1, "data persists")

    with httpx.Client(base_url=API, timeout=60) as other:
        other_email = f"other-{suffix}@example.com"
        signup = other.post(
            "/api/auth/signup",
            json={
                "name": "Other Owner",
                "email": other_email,
                "password": "OtherTenant123",
                "merchant_name": "Other Merchant",
            },
        )
        ok(signup.status_code == 201, "second tenant signup")
        ok(other.get(f"/api/risk/opportunities/{risk_id}").status_code == 404, "tenant isolation")

    with httpx.Client(base_url=WEB, follow_redirects=False, timeout=20) as web:
        for route in ["/", "/login", "/signup", "/forgot-password"]:
            ok(web.get(route).status_code == 200, f"frontend {route}")
        protected = web.get("/dashboard")
        ok(protected.status_code in {307, 308}, "frontend protected redirect")

    print(
        {
            "signup": "passed",
            "empty_workspace": "passed",
            "embedded_worker": "passed",
            "csv_import": "passed",
            "risk_and_candidates": "passed",
            "missing_provider_blocked": "passed",
            "assistant_database_grounded": "passed",
            "logout_protection": "passed",
            "persistence": "passed",
            "tenant_isolation": "passed",
            "frontend_routes": "passed",
        }
    )


if __name__ == "__main__":
    main()

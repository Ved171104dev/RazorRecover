import hashlib,hmac,json,os,time
def test_dashboard_protected(client):assert client.get("/api/dashboard").status_code==401
def test_auth_and_dashboard(authed):
    assert authed.get("/api/auth/me").status_code==200
    r=authed.get("/api/dashboard");assert r.status_code==200 and r.json()["metrics"]["revenue_at_risk_paise"]>0
def test_signup_starts_empty_and_demo_endpoint_does_not_exist(client):
    email=f"razorrecover.test.{time.time_ns()}@gmail.com"
    r=client.post("/api/auth/signup",json={"name":"Empty Owner","email":email,"password":"EmptyPass123","merchant_name":"Empty Merchant"});assert r.status_code==201,r.text
    dashboard=client.get("/api/dashboard").json();assert dashboard["onboarding"]["payment_count"]==0 and not dashboard["onboarding"]["has_payment_data"]
    csrf=client.cookies.get("rr_csrf");assert client.post("/api/demo/run",headers={"X-CSRF-Token":csrf}).status_code==404
def test_action_cannot_execute_cross_tenant(authed):assert authed.post("/api/actions/not-owned/execute").status_code==404
def test_invalid_webhook_rejected(client):
    os.environ["RAZORPAY_WEBHOOK_SECRET"]="secret";assert client.post("/api/webhooks/razorpay",content=b"{}",headers={"X-Razorpay-Signature":"wrong"}).status_code==401
def test_webhook_signature_and_duplicate(client):
    os.environ["RAZORPAY_WEBHOOK_SECRET"]="secret";raw=json.dumps({"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_test","amount":100,"status":"captured","notes":{}}}}},separators=(",",":")).encode();sig=hmac.new(b"secret",raw,hashlib.sha256).hexdigest();headers={"X-Razorpay-Signature":sig,"X-Razorpay-Event-Id":"evt_test"}
    assert client.post("/api/webhooks/razorpay",content=raw,headers=headers).status_code==200
    assert client.post("/api/webhooks/razorpay",content=raw,headers=headers).json()["status"]=="duplicate"
def test_logout_invalidates_session(authed):
    assert authed.post("/api/auth/logout").status_code==200
    assert authed.get("/api/dashboard").status_code==401

import hashlib,hmac,json,os,time
def test_dashboard_protected(client):assert client.get("/api/dashboard").status_code==401
def test_auth_and_dashboard(authed):
    assert authed.get("/api/auth/me").status_code==200
    r=authed.get("/api/dashboard");assert r.status_code==200 and r.json()["metrics"]["revenue_at_risk_paise"]>0
    metrics=r.json()["metrics"]
    assert {"recovered_gmv_paise","recovered_arr_paise","cost_per_recovery_paise","net_recovered_revenue_paise","gateway_success_rate_improvement_pp"}.issubset(metrics)
    assert metrics["net_recovered_revenue_paise"]<=metrics["recovered_gmv_paise"]
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

def test_merchant_can_prepare_five_policy_bound_actions(authed):
    opportunities=authed.get("/api/risk/opportunities").json()["items"][:5]
    assert len(opportunities)==5
    payload={"opportunity_ids":[item["id"] for item in opportunities]}
    prepared=authed.post("/api/actions/prepare",json=payload)
    assert prepared.status_code==200,prepared.text
    assert len(prepared.json()["items"])==5
    assert all(item["amount_paise"]>0 and item["customer"]["name"] and item["order"]["external_ref"] for item in prepared.json()["items"])
    assert sum(prepared.json()["counts"].values())==5
    first_ids={item["id"] for item in prepared.json()["items"]}
    repeated=authed.post("/api/actions/prepare",json=payload)
    assert repeated.status_code==200
    assert {item["id"] for item in repeated.json()["items"]}==first_ids
    assert authed.post("/api/actions/prepare",json={"opportunity_ids":[str(i) for i in range(11)]}).status_code==422

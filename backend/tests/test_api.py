import hashlib,hmac,json,os,time
from sqlalchemy import select
from app.db import DataIngestionRun,Experiment,ExperimentVariant,Merchant,SessionLocal
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
def test_atomic_action_preparation_audit_and_pending_experiment(client):
    email=f"atomic.actions.{time.time_ns()}@gmail.com"
    signup=client.post("/api/auth/signup",json={"name":"Atomic Owner","email":email,"password":"AtomicActions123","merchant_name":"Atomic Merchant"})
    assert signup.status_code==201,signup.text
    headers={"X-CSRF-Token":client.cookies.get("rr_csrf")}
    merchant_id=client.get("/api/auth/me").json()["merchant"]["id"]
    csv_data=("external_id,order_id,customer_email,customer_name,amount_paise,status,method,failure_code\n"
              "atomic-pay-1,atomic-order-1,atomic.one@gmail.com,Atomic One,699900,failed,upi,UPI_TIMEOUT\n"
              "atomic-pay-2,atomic-order-2,atomic.two@gmail.com,Atomic Two,899900,failed,upi,UPI_TIMEOUT\n")
    imported=client.post("/api/data-sources/import/file",headers=headers,files={"file":("atomic.csv",csv_data,"text/csv")})
    assert imported.status_code==200,imported.text
    opportunities=client.get("/api/risk/opportunities").json()["items"]
    assert len(opportunities)==2
    failed_batch=client.post("/api/actions/prepare",headers=headers,json={"opportunity_ids":[opportunities[0]["id"],"not-owned"]})
    assert failed_batch.status_code==404
    assert client.get("/api/actions").json()["items"]==[]
    prepared=client.post("/api/actions/prepare",headers=headers,json={"opportunity_ids":[item["id"] for item in opportunities]})
    assert prepared.status_code==200,prepared.text
    actions=prepared.json()["items"]
    assert len(actions)==2 and all(item["status"]=="awaiting_approval" and item["experiment"] for item in actions)
    assert client.post(f"/api/actions/{actions[0]['id']}/approve",headers=headers).status_code==200
    assert client.post(f"/api/actions/{actions[1]['id']}/reject",headers=headers).status_code==200
    experiment=next(item for item in client.get("/api/experiments").json()["items"] if item["experiment_type"]=="observational")
    assert experiment["participants"]==2 and experiment["pending_outcomes"]==1 and experiment["excluded_outcomes"]==1
    assert sum(variant["sample_size"] for variant in experiment["variants"])==2
    audit_events=client.get("/api/audit").json()["items"]
    event_types=[item["event_type"] for item in audit_events]
    assert event_types.count("merchant_action_prepared")==2
    assert event_types.count("merchant_action_approved")==1
    assert event_types.count("merchant_action_rejected")==1
    merchant_events=[item for item in audit_events if item["event_type"].startswith("merchant_action_")]
    assert all(item["actor_type"]=="merchant" and item["actor_id"] for item in merchant_events)
    metrics=client.get("/api/dashboard").json()["metrics"]
    assert metrics["recovered_revenue_paise"]==0 and metrics["incremental_revenue_paise"]==0
    with SessionLocal() as db:
        for run in db.query(DataIngestionRun).filter(DataIngestionRun.merchant_id==merchant_id).all():db.delete(run)
        merchant=db.get(Merchant,merchant_id);db.delete(merchant);db.commit()

def test_controlled_holdout_shadow_proof_and_reliability(client):
    email=f"causal.features.{time.time_ns()}@gmail.com"
    signup=client.post("/api/auth/signup",json={"name":"Causal Owner","email":email,"password":"CausalFeature123","merchant_name":"Causal Merchant"})
    assert signup.status_code==201,signup.text
    headers={"X-CSRF-Token":client.cookies.get("rr_csrf")}
    merchant_id=client.get("/api/auth/me").json()["merchant"]["id"]
    csv_data=("external_id,order_id,customer_email,customer_name,amount_paise,status,method,failure_code\n"
              "causal-pay-1,causal-order-1,causal.one@gmail.com,Causal One,349900,failed,upi,UPI_TIMEOUT\n")
    assert client.post("/api/data-sources/import/file",headers=headers,files={"file":("causal.csv",csv_data,"text/csv")}).status_code==200
    created=client.post("/api/experiments",headers=headers,json={"name":"Causal Holdout Test","segment":"UPI timeout recovery","experiment_type":"controlled_holdout"})
    assert created.status_code==200,created.text
    with SessionLocal() as db:
        experiment=db.scalar(select(Experiment).where(Experiment.id==created.json()["id"],Experiment.merchant_id==merchant_id))
        variants=list(db.scalars(select(ExperimentVariant).where(ExperimentVariant.experiment_id==experiment.id)).all())
        for variant in variants:variant.allocation_percent=100 if variant.action_type=="no_action" else 0
        db.commit()
    risk=client.get("/api/risk/opportunities").json()["items"][0]
    prepared=client.post("/api/actions/prepare",headers=headers,json={"opportunity_ids":[risk["id"]]})
    action=prepared.json()["items"][0]
    assert action["status"]=="holdout" and action["delivery_status"]=="suppressed"
    action_id=action["id"]
    assert client.post(f"/api/actions/{action_id}/execute",headers=headers).status_code==409
    proof=client.get(f"/api/actions/{action_id}/proof")
    assert proof.status_code==200,proof.text
    receipt=proof.json()
    assert receipt["experiment"]["assignment_group"]=="control"
    assert receipt["financial_truth"]["actual_verified_recovery_paise"]==0
    assert receipt["delivery"]["notification_delivery_confirmed"] is False
    radar=client.get("/api/risk/incidents")
    assert radar.status_code==200 and radar.json()["incidents"]
    reliability=client.get("/api/webhooks/reliability")
    assert reliability.status_code==200 and reliability.json()["metrics"]["received"]==0
    settings=client.get("/api/settings").json()
    settings["shadow_mode"]=True
    settings.pop("razorpay_configured",None);settings.pop("razorpay",None)
    assert client.put("/api/settings",headers=headers,json=settings).status_code==200
    assert client.get("/api/dashboard").json()["metrics"]["shadow_mode"] is True
    with SessionLocal() as db:
        for run in db.query(DataIngestionRun).filter(DataIngestionRun.merchant_id==merchant_id).all():db.delete(run)
        merchant=db.get(Merchant,merchant_id);db.delete(merchant);db.commit()

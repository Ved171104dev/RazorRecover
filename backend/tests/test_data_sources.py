import hashlib,hmac,io,json
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Table,TableStyle
from sqlalchemy import func,select
from app.db import DataIngestionRun,Payment,RazorpayConnection,RecoveryAction,RiskEvent,SessionLocal,uid,utcnow

def test_connection_is_encrypted_and_secret_is_never_returned(authed,monkeypatch):
    monkeypatch.setattr("app.providers.razorpay_adapter.RazorpayAdapter.verify_connection",lambda self:{"connected":True})
    body={"key_id":"rzp_test_merchant123","key_secret":"merchant-secret-123","webhook_secret":"webhook-secret-123"}
    response=authed.post("/api/data-sources/razorpay/connect",json=body)
    assert response.status_code==200,response.text
    payload=response.json();assert payload["razorpay"]["connected"] is True
    rendered=str(payload);assert body["key_secret"] not in rendered and body["webhook_secret"] not in rendered
    with SessionLocal() as db:
        connection=db.scalar(select(RazorpayConnection).where(RazorpayConnection.key_id_masked.is_not(None)))
        assert connection.key_secret_encrypted and body["key_secret"] not in connection.key_secret_encrypted
        assert connection.webhook_secret_encrypted and body["webhook_secret"] not in connection.webhook_secret_encrypted

def test_csv_import_is_idempotent_and_creates_failed_payment(authed):
    raw=("external_id,order_id,customer_email,customer_name,amount_paise,status,method,failure_code,currency\n"
         "pay_csv_1,order_csv_1,buyer@example.com,Buyer,349900,failed,upi,UPI_TIMEOUT,INR\n").encode()
    first=authed.post("/api/data-sources/import/csv",files={"file":("payments.csv",raw,"text/csv")})
    second=authed.post("/api/data-sources/import/csv",files={"file":("payments.csv",raw,"text/csv")})
    assert first.status_code==200,first.text;assert second.status_code==200,second.text
    assert first.json()["run"]["id"]==second.json()["run"]["id"]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Payment).where(Payment.external_ref=="pay_csv_1"))==1
        assert db.scalar(select(func.count()).select_from(DataIngestionRun).where(DataIngestionRun.source=="merchant_file"))==1

def _xlsx_bytes(external_id:str)->bytes:
    workbook=Workbook();sheet=workbook.active;sheet.append(["external_id","order_id","customer_email","customer_name","amount_paise","status","method","failure_code","currency"]);sheet.append([external_id,f"order_{external_id}",f"{external_id}@example.com","Excel Buyer",249900,"failed","upi","UPI_TIMEOUT","INR"]);stream=io.BytesIO();workbook.save(stream);return stream.getvalue()

def _pdf_bytes(external_id:str)->bytes:
    stream=io.BytesIO();document=SimpleDocTemplate(stream,pagesize=A4);data=[["external_id","order_id","customer_email","customer_name","amount_paise","status","method","failure_code"],[external_id,f"order_{external_id}",f"{external_id}@example.com","PDF Buyer","159900","failed","upi","UPI_TIMEOUT"]];table=Table(data,colWidths=[62,68,95,62,65,42,40,72]);table.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.5,colors.black),("FONTSIZE",(0,0),(-1,-1),6)]));document.build([table]);return stream.getvalue()

def test_xlsx_json_and_pdf_imports_use_shared_validation(authed):
    xlsx=_xlsx_bytes("pay_xlsx_1")
    first=authed.post("/api/data-sources/import/file",files={"file":("payments.xlsx",xlsx,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    duplicate=authed.post("/api/data-sources/import/file",files={"file":("payments.xlsx",xlsx,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert first.status_code==200,first.text;assert first.json()["run"]["counts"]["format"]=="xlsx";assert duplicate.json()["run"]["id"]==first.json()["run"]["id"]
    raw_json=json.dumps({"payments":[{"payment_id":"pay_json_1","order":"order_json_1","email":"json@example.com","customer":"JSON Buyer","amount":199900,"status":"declined","method":"card","error_code":"CARD_DECLINED"}]}).encode()
    result=authed.post("/api/data-sources/import/file",files={"file":("payments.json",raw_json,"application/json")});assert result.status_code==200,result.text;assert result.json()["run"]["counts"]["format"]=="json"
    pdf=_pdf_bytes("pay_pdf_1");result=authed.post("/api/data-sources/import/file",files={"file":("payments.pdf",pdf,"application/pdf")});assert result.status_code==200,result.text;assert result.json()["run"]["counts"]["format"]=="pdf"
    with SessionLocal() as db:
        for external in ["pay_xlsx_1","pay_json_1","pay_pdf_1"]:assert db.scalar(select(func.count()).select_from(Payment).where(Payment.external_ref==external))==1

def test_import_rejects_unsupported_and_spoofed_files(authed):
    unsupported=authed.post("/api/data-sources/import/file",files={"file":("payments.exe",b"MZ executable","application/octet-stream")});assert unsupported.status_code==422 and "Supported files" in unsupported.text
    spoofed=authed.post("/api/data-sources/import/file",files={"file":("payments.pdf",b"MZ executable","application/pdf")});assert spoofed.status_code==422 and "signature" in spoofed.text

def test_imported_file_rows_can_be_added_edited_removed_and_file_deleted(authed):
    first_raw=("external_id,order_id,customer_email,customer_name,amount_paise,status,method,failure_code,currency\n"
               "pay_manage_1,order_manage_1,manage@example.com,Managed Buyer,349900,failed,upi,UPI_TIMEOUT,INR\n").encode()
    second_raw=("external_id,order_id,customer_email,customer_name,amount_paise,status,method,failure_code,currency\n"
                "pay_keep_1,order_keep_1,keep@example.com,Keep Buyer,199900,captured,card,,INR\n").encode()
    first=authed.post("/api/data-sources/import/file",files={"file":("managed.csv",first_raw,"text/csv")});assert first.status_code==200,first.text
    second=authed.post("/api/data-sources/import/file",files={"file":("keep.csv",second_raw,"text/csv")});assert second.status_code==200,second.text
    run_id=first.json()["run"]["id"]
    detail=authed.get(f"/api/data-sources/imports/{run_id}");assert detail.status_code==200 and detail.json()["records"][0]["external_id"]=="pay_manage_1"
    with SessionLocal() as db:
        payment=db.scalar(select(Payment).where(Payment.external_ref=="pay_manage_1"));risk=db.scalar(select(RiskEvent).where(RiskEvent.payment_id==payment.id));risk_id=risk.id
    failed_action=authed.post("/api/recovery/payment-link",json={"opportunity_id":risk_id});assert failed_action.status_code==422
    with SessionLocal() as db:assert db.scalar(select(func.count()).select_from(RecoveryAction).where(RecoveryAction.payment_id==payment.id))==1
    updated={"external_id":"pay_manage_1","order_id":"order_manage_1","customer_email":"manage@example.com","customer_name":"Managed Buyer Updated","amount_paise":459900,"status":"captured","method":"card","failure_code":"","currency":"INR","customer_phone":"9876509999"}
    result=authed.put(f"/api/data-sources/imports/{run_id}/payments/pay_manage_1",json=updated);assert result.status_code==200,result.text
    with SessionLocal() as db:
        payment=db.scalar(select(Payment).where(Payment.external_ref=="pay_manage_1"));assert payment.amount_paise==459900 and payment.status=="captured"
        assert db.scalar(select(func.count()).select_from(RiskEvent).where(RiskEvent.payment_id==payment.id))==0
        assert db.scalar(select(func.count()).select_from(RecoveryAction).where(RecoveryAction.payment_id==payment.id))==0
    added={**updated,"external_id":"pay_manage_2","order_id":"order_manage_2","customer_email":"second.manage@example.com","status":"failed","method":"upi","failure_code":"UPI_TIMEOUT","amount_paise":219900}
    result=authed.post(f"/api/data-sources/imports/{run_id}/payments",json=added);assert result.status_code==200,result.text;assert result.json()["record_count"]==2
    result=authed.delete(f"/api/data-sources/imports/{run_id}/payments/pay_manage_2");assert result.status_code==200,result.text;assert result.json()["record_count"]==1
    assert authed.delete(f"/api/data-sources/imports/{run_id}").status_code==200
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Payment).where(Payment.external_ref.in_(["pay_manage_1","pay_manage_2"])))==0
        assert db.scalar(select(func.count()).select_from(Payment).where(Payment.external_ref=="pay_keep_1"))==1

def test_legacy_csv_import_history_is_manageable(authed):
    with SessionLocal() as db:
        merchant_id=db.scalar(select(DataIngestionRun.merchant_id).where(DataIngestionRun.source=="merchant_file"))
        legacy=DataIngestionRun(id=uid(),merchant_id=merchant_id,source="merchant_csv",idempotency_key=f"legacy:{uid()}",status="completed",counts={"payments":9},records=[],started_at=utcnow(),completed_at=utcnow());db.add(legacy);db.commit();legacy_id=legacy.id
    payload=authed.get("/api/data-sources").json();item=next(x for x in payload["imports"] if x["id"]==legacy_id)
    assert item["editable"] is True and item["filename"]=="legacy-payments.csv" and item["record_count"]==0
    assert authed.get(f"/api/data-sources/imports/{legacy_id}").status_code==200
    assert authed.delete(f"/api/data-sources/imports/{legacy_id}").status_code==200

def test_merchant_webhook_uses_connection_secret_and_is_idempotent(authed,monkeypatch):
    monkeypatch.setattr("app.providers.razorpay_adapter.RazorpayAdapter.verify_connection",lambda self:{"connected":True})
    secret="webhook-secret-456";connected=authed.post("/api/data-sources/razorpay/connect",json={"key_id":"rzp_test_merchant456","key_secret":"merchant-secret-456","webhook_secret":secret})
    path=connected.json()["razorpay"]["webhook_url"].replace("http://testserver","")
    raw=b'{"event":"payment.failed","payload":{"payment":{"entity":{"id":"pay_hook","status":"failed"}}}}';sig=hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest();headers={"X-Razorpay-Signature":sig,"X-Razorpay-Event-Id":"evt_merchant_unique"}
    assert authed.post(path,content=raw,headers=headers).status_code==200
    assert authed.post(path,content=raw,headers=headers).json()["status"]=="duplicate"
    assert authed.post(path,content=raw,headers={**headers,"X-Razorpay-Event-Id":"evt_bad","X-Razorpay-Signature":"bad"}).status_code==401

def test_data_sources_are_protected(client):
    assert client.get("/api/data-sources").status_code==401

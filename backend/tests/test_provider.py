import hashlib,hmac
from app.providers.razorpay_adapter import RazorpayAdapter,verify_webhook_signature
class Resp:
    status_code=200
    def raise_for_status(self):pass
    def json(self):return {"id":"plink_test_123","status":"created","short_url":"https://rzp.io/i/test"}
class Client:
    def __init__(self,**kwargs):self.kwargs=kwargs
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def request(self,method,path,**kwargs):
        assert method=="POST" and path=="/payment_links";assert kwargs["json"]["amount"]==349900;return Resp()
def test_adapter_creates_real_test_link_shape(monkeypatch):
    monkeypatch.setattr("app.providers.razorpay_adapter.httpx.Client",Client);a=RazorpayAdapter("rzp_test_key","secret",False);r=a.create_payment_link(349900,"action-id","Recover order",{"name":"A","email":"a@example.com","phone":None});assert r.mode=="razorpay_test" and r.provider_id=="plink_test_123" and r.url.startswith("https://rzp.io/")
def test_adapter_without_test_credentials_is_explicit_simulation():
    r=RazorpayAdapter(None,None,False).create_order(10000,"INR","receipt");assert r.mode=="simulated" and r.provider_id is None and "SIMULATED" in r.raw["label"]
def test_signature_exact_raw_body():
    raw=b'{"event":"payment.captured"}';sig=hmac.new(b"secret",raw,hashlib.sha256).hexdigest();assert verify_webhook_signature(raw,sig,"secret");assert not verify_webhook_signature(raw+b" ","bad","secret")


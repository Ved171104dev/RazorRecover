from __future__ import annotations
import hashlib,hmac
from abc import ABC,abstractmethod
from dataclasses import dataclass
from typing import Any
import httpx

BASE="https://api.razorpay.com/v1"
class ProviderError(RuntimeError):pass
@dataclass(frozen=True)
class ProviderResult:
    provider_id:str|None;status:str;url:str|None;mode:str;raw:dict[str,Any]
class PaymentProvider(ABC):
    @abstractmethod
    def create_order(self,amount_paise:int,currency:str,receipt:str)->ProviderResult:...
    @abstractmethod
    def fetch_order(self,provider_order_id:str)->dict:...
    @abstractmethod
    def list_order_payments(self,provider_order_id:str)->list[dict]:...
    @abstractmethod
    def fetch_payment(self,provider_payment_id:str)->dict:...
    @abstractmethod
    def create_payment_link(self,amount_paise:int,reference_id:str,description:str,customer:dict)->ProviderResult:...
    @abstractmethod
    def fetch_payment_link(self,provider_link_id:str)->dict:...
class RazorpayAdapter(PaymentProvider):
    def __init__(self,key_id:str|None,key_secret:str|None,demo_mode:bool):
        self.key_id=key_id;self.key_secret=key_secret;self.configured=bool(key_id and key_secret and key_id.startswith("rzp_test_"));self.demo_mode=demo_mode or not self.configured
    def _request(self,method:str,path:str,**kwargs)->dict:
        if not self.configured:raise ProviderError("Razorpay Test Mode credentials are not configured")
        try:
            with httpx.Client(base_url=BASE,auth=(self.key_id or "",self.key_secret or ""),timeout=12) as client:r=client.request(method,path,**kwargs)
            if r.status_code==429:raise ProviderError("Razorpay rate limit reached; retry later")
            r.raise_for_status();data=r.json()
            if not isinstance(data,dict):raise ProviderError("Malformed Razorpay response")
            return data
        except httpx.HTTPStatusError as exc:raise ProviderError(f"Razorpay API rejected request ({exc.response.status_code})") from exc
        except (httpx.RequestError,ValueError) as exc:raise ProviderError("Razorpay API unavailable or returned malformed data") from exc
    def create_order(self,amount_paise:int,currency:str,receipt:str)->ProviderResult:
        if self.demo_mode:return ProviderResult(None,"simulated_order_created",None,"simulated",{"label":"SIMULATED — RAZORPAY TEST MODE NOT CONNECTED"})
        d=self._request("POST","/orders",json={"amount":amount_paise,"currency":currency,"receipt":receipt,"notes":{"source":"RazorRecover"}})
        return ProviderResult(d["id"],d["status"],None,"razorpay_test",d)
    def fetch_order(self,pid:str)->dict:return self._request("GET",f"/orders/{pid}")
    def list_order_payments(self,pid:str)->list[dict]:return self._request("GET",f"/orders/{pid}/payments").get("items",[])
    def fetch_payment(self,pid:str)->dict:return self._request("GET",f"/payments/{pid}")
    def create_payment_link(self,amount_paise:int,reference_id:str,description:str,customer:dict)->ProviderResult:
        if self.demo_mode:return ProviderResult(None,"simulated_link_created",None,"simulated",{"label":"SIMULATED — RAZORPAY TEST MODE NOT CONNECTED","reference_id":reference_id})
        payload={"amount":amount_paise,"currency":"INR","accept_partial":False,"reference_id":reference_id,"description":description,"customer":{"name":customer["name"],"email":customer["email"],**({"contact":customer["phone"]} if customer.get("phone") else {})},"notify":{"sms":False,"email":False},"reminder_enable":True,"notes":{"source":"RazorRecover","recovery_action_id":reference_id}}
        d=self._request("POST","/payment_links",json=payload)
        return ProviderResult(d["id"],d["status"],d.get("short_url"),"razorpay_test",d)
    def fetch_payment_link(self,pid:str)->dict:return self._request("GET",f"/payment_links/{pid}")
def verify_webhook_signature(raw:bytes,signature:str,secret:str)->bool:
    expected=hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
    return bool(signature) and hmac.compare_digest(expected,signature)

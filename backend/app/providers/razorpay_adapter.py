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
    @abstractmethod
    def notify_payment_link(self,provider_link_id:str,medium:str)->dict:...
    @abstractmethod
    def list_orders(self,from_timestamp:int|None=None,limit:int=500)->list[dict]:...
    @abstractmethod
    def list_payments(self,from_timestamp:int|None=None,limit:int=500)->list[dict]:...
    @abstractmethod
    def verify_connection(self)->dict:...
class RazorpayAdapter(PaymentProvider):
    def __init__(self,key_id:str|None,key_secret:str|None):
        self.key_id=key_id;self.key_secret=key_secret;self.configured=bool(key_id and key_secret and key_id.startswith("rzp_test_"))
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
        d=self._request("POST","/orders",json={"amount":amount_paise,"currency":currency,"receipt":receipt,"notes":{"source":"RazorRecover"}})
        return ProviderResult(d["id"],d["status"],None,"razorpay_test",d)
    def fetch_order(self,pid:str)->dict:return self._request("GET",f"/orders/{pid}")
    def list_order_payments(self,pid:str)->list[dict]:return self._request("GET",f"/orders/{pid}/payments").get("items",[])
    def fetch_payment(self,pid:str)->dict:return self._request("GET",f"/payments/{pid}")
    def create_payment_link(self,amount_paise:int,reference_id:str,description:str,customer:dict)->ProviderResult:
        payload={"amount":amount_paise,"currency":"INR","accept_partial":False,"reference_id":reference_id,"description":description,"customer":{"name":customer["name"],"email":customer["email"],**({"contact":customer["phone"]} if customer.get("phone") else {})},"notify":{"sms":False,"email":False},"reminder_enable":True,"notes":{"source":"RazorRecover","recovery_action_id":reference_id}}
        d=self._request("POST","/payment_links",json=payload)
        return ProviderResult(d["id"],d["status"],d.get("short_url"),"razorpay_test",d)
    def fetch_payment_link(self,pid:str)->dict:return self._request("GET",f"/payment_links/{pid}")
    def notify_payment_link(self,pid:str,medium:str)->dict:
        if medium not in {"sms","email"}:raise ProviderError("Notification medium must be sms or email")
        return self._request("POST",f"/payment_links/{pid}/notify_by/{medium}")
    def _paginate(self,path:str,from_timestamp:int|None,limit:int)->list[dict]:
        rows:list[dict]=[];skip=0;limit=max(1,min(limit,5000))
        while len(rows)<limit:
            count=min(100,limit-len(rows));params={"count":count,"skip":skip}
            if from_timestamp is not None:params["from"]=from_timestamp
            page=self._request("GET",path,params=params).get("items",[])
            if not isinstance(page,list):raise ProviderError("Malformed Razorpay collection response")
            rows.extend(x for x in page if isinstance(x,dict))
            if len(page)<count:break
            skip+=len(page)
        return rows
    def list_orders(self,from_timestamp:int|None=None,limit:int=500)->list[dict]:return self._paginate("/orders",from_timestamp,limit)
    def list_payments(self,from_timestamp:int|None=None,limit:int=500)->list[dict]:return self._paginate("/payments",from_timestamp,limit)
    def verify_connection(self)->dict:
        result=self._request("GET","/payments",params={"count":1,"skip":0})
        return {"connected":True,"entity":result.get("entity"),"visible_records":int(result.get("count",0))}
def verify_webhook_signature(raw:bytes,signature:str,secret:str)->bool:
    expected=hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
    return bool(signature) and hmac.compare_digest(expected,signature)

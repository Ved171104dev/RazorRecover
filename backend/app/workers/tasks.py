from __future__ import annotations
from sqlalchemy import select
from app.db import *
from app.services.workflow import verify_and_attribute

def process_webhook(event_db_id:str)->None:
    with SessionLocal() as db:
        event=db.get(WebhookEvent,event_db_id)
        if not event or event.status=="processed":return
        try:
            payload=event.payload;kind=event.event_type
            link=((payload.get("payload") or {}).get("payment_link") or {}).get("entity") or {}
            pay=((payload.get("payload") or {}).get("payment") or {}).get("entity") or {}
            notes=link.get("notes") or pay.get("notes") or {}
            action_id=notes.get("recovery_action_id") or link.get("reference_id")
            action=db.get(RecoveryAction,action_id) if action_id else None
            if action:
                event.merchant_id=action.merchant_id
                rec=db.scalar(select(RazorpayPaymentLink).where(RazorpayPaymentLink.recovery_action_id==action.id))
                if rec:
                    rec.status=link.get("status") or ("paid" if kind in {"payment_link.paid","payment.captured","order.paid"} else rec.status)
                    rec.raw_data=link or rec.raw_data
                if kind in {"payment_link.paid","payment.captured","order.paid"} and pay.get("status","captured") in {"captured","authorized"}:
                    verify_and_attribute(db,action,pay.get("id"),int(pay.get("amount") or link.get("amount_paid") or 0),"verified_webhook")
                elif kind=="payment.failed": action.verification_status="failed";action.status="failed";action.execution_result={"failure_code":pay.get("error_code"),"failure_description":pay.get("error_description")}
            event.status="processed";event.processed_at=utcnow();db.commit()
        except Exception as exc:
            event.status="failed";event.error=str(exc)[:500];db.commit();raise

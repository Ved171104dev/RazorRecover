from __future__ import annotations
from datetime import timedelta

from sqlalchemy import select, update
from app.db import *
from app.services.workflow import reconcile_action,verify_and_attribute

def reconcile_action_job(action_id:str)->None:
    with SessionLocal() as db:
        action=db.get(RecoveryAction,action_id)
        if not action or action.verification_status=="verified" or not action.provider_reference:return
        try:reconcile_action(db,action)
        except Exception as exc:
            action.reconciliation_attempts+=1;action.next_reconcile_at=utcnow()+timedelta(minutes=min(60,5*action.reconciliation_attempts));action.execution_result={**(action.execution_result or {}),"reconciliation_error":str(exc)[:300]};db.commit();raise

def process_webhook(event_db_id:str)->bool:
    with SessionLocal() as db:
        claimed=db.execute(update(WebhookEvent).where(WebhookEvent.id==event_db_id,WebhookEvent.status=="received",WebhookEvent.signature_valid.is_(True)).values(status="processing"))
        db.commit()
        if claimed.rowcount!=1:return False
        event=db.get(WebhookEvent,event_db_id)
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
                    action.delivery_status="paid"
                    verify_and_attribute(db,action,pay.get("id"),int(pay.get("amount") or link.get("amount_paid") or 0),"verified_webhook")
                elif kind=="payment.failed":
                    action.delivery_status="payment_failed";action.verification_status="failed";action.status="failed";action.execution_result={**(action.execution_result or {}),"failure_code":pay.get("error_code"),"failure_description":pay.get("error_description")}
                elif kind in {"payment_link.cancelled","payment_link.expired"}:
                    action.delivery_status="cancelled" if kind.endswith("cancelled") else "expired"
            event.status="processed";event.processed_at=utcnow();db.commit();return True
        except Exception as exc:
            event.status="failed";event.error=str(exc)[:500];db.commit();raise

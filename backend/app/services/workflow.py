from __future__ import annotations
import os
from sqlalchemy import func,select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db import *
from app.providers.razorpay_adapter import ProviderError,RazorpayAdapter
from app.services.recovery import evaluate_policy

def provider(policy:MerchantPolicy)->RazorpayAdapter:
    return RazorpayAdapter(os.getenv("RAZORPAY_KEY_ID"),os.getenv("RAZORPAY_KEY_SECRET"),policy.simulation_mode)
def audit(db:Session,merchant_id:str,event:str,detail:dict,action:RecoveryAction|None=None,decision_id:str|None=None,amount:int=0)->None:
    db.add(AuditLog(merchant_id=merchant_id,event_type=event,detail=detail,action_id=action.id if action else None,decision_id=decision_id,amount_paise=amount))
    db.add(AgentEvent(merchant_id=merchant_id,action_id=action.id if action else None,stage=event,title=event.replace("_"," ").title(),detail=str(detail.get("message") or detail.get("reason") or event),amount_paise=amount))
def ensure_action(db:Session,merchant_id:str,decision:AgentDecision)->RecoveryAction:
    existing=db.scalar(select(RecoveryAction).where(RecoveryAction.merchant_id==merchant_id,RecoveryAction.decision_id==decision.id))
    if existing:return existing
    risk=db.get(RiskEvent,decision.risk_event_id); payment=db.get(Payment,risk.payment_id)
    status="awaiting_approval" if decision.policy_status=="approval_required" else ("approved" if decision.policy_status=="approved" else "blocked")
    action=RecoveryAction(merchant_id=merchant_id,decision_id=decision.id,payment_id=payment.id,action_type=decision.selected_action,status=status,idempotency_key=f"decision:{decision.id}",execution_mode="simulated")
    db.add(action);db.flush()
    if status=="awaiting_approval":db.add(Approval(merchant_id=merchant_id,recovery_action_id=action.id,status="pending"))
    audit(db,merchant_id,"govern",{"message":decision.policy_result["reason"],"policy":decision.policy_result},action,decision.id)
    db.commit();return action
def create_payment_link(db:Session,merchant_id:str,decision:AgentDecision)->RecoveryAction:
    action=ensure_action(db,merchant_id,decision)
    if action.status=="blocked":raise ValueError("Policy blocked this action")
    if action.status=="awaiting_approval":raise PermissionError("Merchant approval required")
    if action.provider_reference or action.execution_result.get("simulated"):return action
    risk=db.get(RiskEvent,decision.risk_event_id);payment=db.get(Payment,risk.payment_id);order=db.get(Order,payment.order_id);customer=db.get(Customer,order.customer_id);policy=db.scalar(select(MerchantPolicy).where(MerchantPolicy.merchant_id==merchant_id))
    current=evaluate_policy(amount_paise=order.amount_paise,retry_count=db.scalar(select(func.count()).select_from(PaymentAttempt).where(PaymentAttempt.payment_id==payment.id)) or 0,confidence=decision.confidence,action=decision.selected_action,allowed_actions=policy.allowed_actions,automatic_threshold_paise=policy.automatic_threshold_paise,approval_threshold_paise=policy.approval_threshold_paise,blocked_threshold_paise=policy.blocked_threshold_paise,max_retries=policy.max_retries,minimum_confidence=policy.minimum_confidence)
    if not current["allowed"]:action.status="blocked";db.commit();raise ValueError(current["reason"])
    try:result=provider(policy).create_payment_link(order.amount_paise,action.id,f"Recover order {order.external_ref}",{"name":customer.name,"email":customer.email,"phone":customer.phone})
    except ProviderError as exc:
        action.status="failed";action.execution_result={"error":str(exc)};audit(db,merchant_id,"execution_failed",{"message":str(exc)},action,decision.id);db.commit();raise
    action.execution_mode=result.mode;action.provider_reference=result.provider_id;action.provider_url=result.url;action.status="simulated" if result.mode=="simulated" else "executed";action.execution_result={"provider_status":result.status,"simulated":result.mode=="simulated"};action.executed_at=utcnow()
    db.add(RazorpayPaymentLink(merchant_id=merchant_id,recovery_action_id=action.id,razorpay_payment_link_id=result.provider_id,short_url=result.url,amount_paise=order.amount_paise,status=result.status,mode=result.mode,raw_data=result.raw))
    audit(db,merchant_id,"execute",{"message":result.raw.get("label","Razorpay Test Mode Payment Link created"),"mode":result.mode},action,decision.id)
    db.commit();return action
def verify_and_attribute(db:Session,action:RecoveryAction,razorpay_payment_id:str|None,amount:int,source:str)->bool:
    if action.verification_status=="verified":return False
    if db.scalar(select(RecoveryAttribution).where(RecoveryAttribution.payment_id==action.payment_id)):return False
    payment=db.get(Payment,action.payment_id);order=db.get(Order,payment.order_id)
    amount=min(amount,order.amount_paise)
    attr=RecoveryAttribution(merchant_id=action.merchant_id,recovery_action_id=action.id,payment_id=payment.id,razorpay_payment_id=razorpay_payment_id,amount_recovered_paise=amount,verification_status="verified")
    db.add(attr);action.status="verified";action.verification_status="verified";action.verification_source=source;action.razorpay_payment_id=razorpay_payment_id;action.actual_recovered_paise=amount;action.verified_at=utcnow();payment.status="captured";order.status="paid_recovered"
    risk=db.scalar(select(RiskEvent).where(RiskEvent.payment_id==payment.id));perf=db.scalar(select(StrategyPerformance).where(StrategyPerformance.merchant_id==action.merchant_id,StrategyPerformance.reason_code==risk.root_cause,StrategyPerformance.action_type==action.action_type))
    if perf:perf.participants+=1;perf.successes+=1;perf.recovered_paise+=amount
    audit(db,action.merchant_id,"verify",{"message":"Payment outcome verified","source":source,"razorpay_payment_id":razorpay_payment_id},action,amount=amount)
    db.commit();return True

from __future__ import annotations
import random
from datetime import timedelta
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.db import *
from app.services.auth import hash_password
from app.services.recovery import calculate_strategies,evaluate_policy

SEED=20260828
FIRST=["Aarav","Diya","Vihaan","Ananya","Kabir","Isha","Arjun","Meera","Rohan","Kavya"]
LAST=["Sharma","Patel","Reddy","Singh","Iyer","Khan","Das","Jain"]

def create_merchant_account(db:Session,name:str,email:str,password:str,merchant_name:str)->tuple[User,Merchant]:
    slug="-".join(merchant_name.lower().split())[:80]+"-"+uid()[:6]
    user=User(name=name,email=email.lower(),password_hash=hash_password(password))
    merchant=Merchant(name=merchant_name,slug=slug);db.add_all([user,merchant]);db.flush()
    db.add_all([MerchantUser(merchant_id=merchant.id,user_id=user.id,role="owner"),MerchantPolicy(merchant_id=merchant.id,allowed_actions=["retry","alternate_payment","recovery_link","checkout_recovery"]),RazorpayConnection(merchant_id=merchant.id)])
    db.commit();return user,merchant

def seed_merchant(db:Session,merchant:Merchant,customer_count:int=300,order_count:int=700)->None:
    if db.scalar(select(func.count()).select_from(Order).where(Order.merchant_id==merchant.id)):return
    rng=random.Random(SEED+sum(ord(x) for x in merchant.id));now=utcnow()
    customers=[]
    for i in range(customer_count):
        pref="card" if i==0 or rng.random()<.62 else "upi"
        customers.append(Customer(id=uid(),merchant_id=merchant.id,external_ref=f"cust_{i:05}",name=f"{rng.choice(FIRST)} {rng.choice(LAST)}",email=f"customer{i}@demo.local",phone=f"+9190000{i%100000:05}",historical_success_rate=.92 if i==0 else round(rng.uniform(.48,.96),2),preferred_method=pref,previous_failures=rng.randint(0,3)))
    db.add_all(customers);db.flush()
    policy=db.scalar(select(MerchantPolicy).where(MerchantPolicy.merchant_id==merchant.id))
    for i in range(order_count):
        c=customers[i%len(customers)]; failed=i<min(2100,order_count) or rng.random()<.12
        amount=349900 if i==0 else rng.randint(299,14999)*100; created=now-timedelta(minutes=rng.randint(0,10080))
        order=Order(merchant_id=merchant.id,customer_id=c.id,external_ref=f"order_{i:05}",amount_paise=amount,status="payment_failed" if failed else "paid",data_source="test_fixture",created_at=created)
        db.add(order);db.flush()
        cause="UPI_TIMEOUT" if failed and (i<max(1,order_count//3) or rng.random()<.35) else ("BANK_DECLINED" if failed else None)
        payment=Payment(merchant_id=merchant.id,order_id=order.id,external_ref=f"payment_{i:05}",amount_paise=amount,method="upi" if failed else c.preferred_method,failure_code=cause,failure_description="Payment timed out at provider" if cause=="UPI_TIMEOUT" else None,bank=rng.choice(["HDFC","ICICI","SBI","Axis"]),status="failed" if failed else "captured",data_source="test_fixture",created_at=created)
        db.add(payment);db.flush()
        retry=1 if i==0 else rng.randint(0,2)
        db.add(PaymentAttempt(merchant_id=merchant.id,payment_id=payment.id,attempt_number=retry+1,method=payment.method or "upi",status=payment.status,failure_code=cause,device="android" if i%4 else "ios",checkout_duration_seconds=rng.randint(18,190),created_at=created))
        if not failed:continue
        probability=.69 if cause=="UPI_TIMEOUT" and c.preferred_method=="card" else round(rng.uniform(.25,.62),2)
        confidence=.87 if i==0 else round(min(.94,probability+rng.uniform(.14,.24)),2)
        reasons=[cause or "FAILED_PAYMENT","RETRY_ALREADY_FAILED" if retry else "FIRST_FAILURE"]+(["CARD_HISTORY"] if c.preferred_method=="card" else [])
        evidence=[{"signal":"failure_pattern","value":cause,"detail":"UPI timeout rate is elevated in the affected segment."},{"signal":"retry_history","value":retry,"detail":"A prior retry lowers same-method recovery."},{"signal":"customer_history","value":c.preferred_method,"detail":"Historical successful method is used as a bounded decision signal."}]
        risk=RiskEvent(merchant_id=merchant.id,payment_id=payment.id,risk_score=round(min(.98,.4+probability*.65),2),recovery_probability=probability,affected_revenue_paise=amount,confidence=confidence,root_cause=cause or "PAYMENT_FAILURE",reason_codes=reasons,evidence=evidence,created_at=created)
        db.add(risk);db.flush()
        strategies=calculate_strategies(amount,probability,cause,c.preferred_method,retry,confidence)
        chosen=strategies[0]
        pr=evaluate_policy(amount_paise=amount,retry_count=retry,confidence=confidence,action=chosen["action"],allowed_actions=policy.allowed_actions,automatic_threshold_paise=policy.automatic_threshold_paise,approval_threshold_paise=policy.approval_threshold_paise,blocked_threshold_paise=policy.blocked_threshold_paise,max_retries=policy.max_retries,minimum_confidence=policy.minimum_confidence)
        db.add(AgentDecision(merchant_id=merchant.id,risk_event_id=risk.id,selected_action=chosen["action"],candidates=strategies,expected_recovery_paise=chosen["expected_recovery_paise"],predicted_probability=chosen["probability"],confidence=confidence,policy_result=pr,policy_status="approval_required" if pr["approval_required"] else ("approved" if pr["allowed"] else "blocked"),explanation=chosen["reason"],created_at=created))
    exp=Experiment(merchant_id=merchant.id,name="UPI timeout users above ₹2,000",segment="UPI timeout · Android · amount > ₹2,000",status="running");db.add(exp);db.flush()
    variants=[ExperimentVariant(merchant_id=merchant.id,experiment_id=exp.id,name="CONTROL — Normal Retry",action_type="retry",allocation_percent=33),ExperimentVariant(merchant_id=merchant.id,experiment_id=exp.id,name="VARIANT A — Payment Link",action_type="recovery_link",allocation_percent=34),ExperimentVariant(merchant_id=merchant.id,experiment_id=exp.id,name="VARIANT B — Alternate Payment",action_type="alternate_payment",allocation_percent=33)]
    db.add_all(variants)
    for reason,action,n,success,revenue in [("UPI_TIMEOUT","retry",148,46,1280000),("UPI_TIMEOUT","recovery_link",154,106,3154000),("UPI_TIMEOUT","alternate_payment",149,61,1921000)]:
        db.add(StrategyPerformance(merchant_id=merchant.id,reason_code=reason,action_type=action,participants=n,successes=success,recovered_paise=revenue))
    db.add_all([AgentEvent(merchant_id=merchant.id,stage="detect",title="Revenue risk detected",detail="UPI timeout cluster observed on Android checkouts",amount_paise=349900),AgentEvent(merchant_id=merchant.id,stage="diagnose",title="Root cause identified",detail="Affected customers have stronger card history",amount_paise=0),AgentEvent(merchant_id=merchant.id,stage="learn",title="Experiment signal available",detail="Payment Link is outperforming normal retry for this segment",amount_paise=0)])
    db.commit()

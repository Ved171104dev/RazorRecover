from app.services.recovery import calculate_strategies,check_policy,ci95
from sqlalchemy import select
from app.db import AgentDecision,MerchantPolicy,Payment,RecoveryAction,RiskEvent,SessionLocal,uid,utcnow
from app.services.workflow import workflow_guardrails
def test_payment_link_beats_retry_for_upi_timeout():
    choices=calculate_strategies(349900,.69,"UPI_TIMEOUT","card",1,.87)
    assert choices[0].action=="recovery_link"
    assert choices[0].expected_recovery_paise>choices[-1].expected_recovery_paise
def test_policy_blocks_retry_limit():
    result=check_policy(amount_paise=200000,retry_count=2,confidence=.8,action="retry",allowed_actions=["retry"],automatic_threshold_paise=500000,approval_threshold_paise=1500000,max_retries=2,minimum_confidence=.65)
    assert not result["allowed"]
def test_policy_requires_approval_for_medium_value():
    result=check_policy(amount_paise=800000,retry_count=0,confidence=.8,action="recovery_link",allowed_actions=["recovery_link"],automatic_threshold_paise=500000,approval_threshold_paise=1500000,max_retries=2,minimum_confidence=.65)
    assert result["allowed"] and result["approval_required"]
def test_confidence_interval_requires_sample():
    assert ci95(2,10) is None
    assert ci95(20,100) is not None

def test_hourly_retry_floor_pauses_merchant_workflows():
    with SessionLocal() as db:
        decision=db.scalars(select(AgentDecision)).first();risk=db.get(RiskEvent,decision.risk_event_id);payment=db.get(Payment,risk.payment_id);policy=db.scalar(select(MerchantPolicy).where(MerchantPolicy.merchant_id==decision.merchant_id))
        action=RecoveryAction(id=uid(),merchant_id=decision.merchant_id,decision_id=decision.id,payment_id=payment.id,action_type="retry",status="failed",idempotency_key=f"circuit-test:{uid()}",execution_mode="test",verification_status="failed",executed_at=utcnow())
        db.add(action);db.flush();state=workflow_guardrails(db,decision.merchant_id,payment,"recovery_link",policy)
        assert state["circuit_breaker_active"] and state["hourly_retry_success_rate"]==0
        assert "15%" in state["circuit_breaker_reason"]
        db.rollback()

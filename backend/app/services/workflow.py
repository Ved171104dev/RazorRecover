from __future__ import annotations

import hashlib
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import *
from app.providers.razorpay_adapter import ProviderError, RazorpayAdapter
from app.services.ingestion import provider_for_merchant
from app.services.recovery import HOURLY_RETRY_SUCCESS_FLOOR, RETRY_CEILING_7_DAYS, evaluate_policy

MANDATE_RETRY_WINDOW_DAYS = 7


def provider(db: Session, merchant_id: str, policy: MerchantPolicy) -> RazorpayAdapter:
    return provider_for_merchant(db, merchant_id)


def audit(db: Session, merchant_id: str, event: str, detail: dict, action: RecoveryAction | None = None, decision_id: str | None = None, amount: int = 0, actor_type: str = "agent", actor_id: str | None = None) -> None:
    db.add(AuditLog(merchant_id=merchant_id, actor_type=actor_type, actor_id=actor_id, event_type=event, detail=detail, action_id=action.id if action else None, decision_id=decision_id, amount_paise=amount))
    db.add(AgentEvent(merchant_id=merchant_id, action_id=action.id if action else None, stage=event, title=event.replace("_", " ").title(), detail=str(detail.get("message") or detail.get("reason") or event), amount_paise=amount))


def workflow_guardrails(db: Session, merchant_id: str, payment: Payment, action_type: str, policy: MerchantPolicy) -> dict:
    """Database-backed stopping rules evaluated immediately before execution."""
    now = utcnow()
    if policy.recovery_paused_until and policy.recovery_paused_until <= now:
        policy.recovery_paused_until = None
        policy.recovery_pause_reason = None
        db.flush()

    hour_start = now - timedelta(hours=1)
    hourly_retry_actions = list(db.scalars(select(RecoveryAction).where(
        RecoveryAction.merchant_id == merchant_id,
        RecoveryAction.action_type == "retry",
        RecoveryAction.executed_at >= hour_start,
    )).all())
    hourly_retry_attempts = len(hourly_retry_actions)
    hourly_retry_successes = sum(item.verification_status == "verified" for item in hourly_retry_actions)
    hourly_retry_success_rate = hourly_retry_successes / hourly_retry_attempts if hourly_retry_attempts else None
    if hourly_retry_attempts and hourly_retry_success_rate is not None and hourly_retry_success_rate < HOURLY_RETRY_SUCCESS_FLOOR:
        reason = f"Hourly retry success rate {hourly_retry_success_rate * 100:.1f}% is below the 15% safety floor"
        if not policy.recovery_paused_until:
            policy.recovery_paused_until = now + timedelta(hours=1)
            policy.recovery_pause_reason = reason
            audit(db, merchant_id, "recovery_circuit_breaker", {"message": reason, "retry_attempts": hourly_retry_attempts, "retry_successes": hourly_retry_successes})
            db.flush()

    invoice_payment_ids = select(Payment.id).where(Payment.merchant_id == merchant_id, Payment.order_id == payment.order_id)
    seven_days_ago = now - timedelta(days=7)
    retry_count_7d = int(db.scalar(select(func.count()).select_from(RecoveryAction).where(
        RecoveryAction.merchant_id == merchant_id,
        RecoveryAction.payment_id.in_(invoice_payment_ids),
        RecoveryAction.action_type == "retry",
        RecoveryAction.created_at >= seven_days_ago,
    )) or 0)
    recurring = payment.payment_type == "recurring"
    mandate_window_active = recurring and payment.created_at >= now - timedelta(days=MANDATE_RETRY_WINDOW_DAYS)
    return {
        "retry_count_7d": retry_count_7d,
        "retry_ceiling_7d": RETRY_CEILING_7_DAYS,
        "hourly_retry_attempts": hourly_retry_attempts,
        "hourly_retry_successes": hourly_retry_successes,
        "hourly_retry_success_rate": round(hourly_retry_success_rate, 4) if hourly_retry_success_rate is not None else None,
        "circuit_breaker_active": bool(policy.recovery_paused_until and policy.recovery_paused_until > now),
        "circuit_breaker_reason": policy.recovery_pause_reason,
        "mandate_grace_window_active": mandate_window_active,
        "payment_type": payment.payment_type,
        "failure_code": payment.failure_code,
        "action_type": action_type,
    }


OBSERVATIONAL_EXPERIMENT_NAME = "Prepared Recovery Strategy Cohort"
CONTROLLED_EXPERIMENT_NAME = "AI Recovery Incrementality Holdout"


def ensure_controlled_experiment(db: Session, merchant_id: str, name: str = CONTROLLED_EXPERIMENT_NAME, segment: str = "Eligible policy-approved recovery opportunities") -> Experiment:
    experiment = db.scalar(select(Experiment).where(
        Experiment.merchant_id == merchant_id,
        Experiment.experiment_type == "controlled_holdout",
        Experiment.status == "running",
    ))
    if experiment:
        return experiment
    experiment = Experiment(merchant_id=merchant_id, name=name, segment=segment, experiment_type="controlled_holdout", status="running")
    db.add(experiment)
    db.flush()
    db.add_all([
        ExperimentVariant(merchant_id=merchant_id, experiment_id=experiment.id, name="CONTROL — No AI Action", action_type="no_action", allocation_percent=10),
        ExperimentVariant(merchant_id=merchant_id, experiment_id=experiment.id, name="TREATMENT — AI Recommended", action_type="ai_recommended", allocation_percent=90),
    ])
    db.flush()
    return experiment


def assign_prepared_experiment(db: Session, merchant_id: str, action: RecoveryAction, decision: AgentDecision) -> ExperimentResult:
    existing = db.scalar(select(ExperimentResult).where(ExperimentResult.merchant_id == merchant_id, ExperimentResult.recovery_action_id == action.id))
    if existing:
        return existing
    risk = db.get(RiskEvent, decision.risk_event_id)
    controlled = db.scalar(select(Experiment).where(
        Experiment.merchant_id == merchant_id,
        Experiment.experiment_type == "controlled_holdout",
        Experiment.status == "running",
    ).order_by(Experiment.created_at))
    if controlled and action.status not in {"blocked", "shadow"}:
        variants = list(db.scalars(select(ExperimentVariant).where(ExperimentVariant.experiment_id == controlled.id).order_by(ExperimentVariant.created_at)).all())
        bucket = int(hashlib.sha256(f"{controlled.id}:{risk.id}".encode()).hexdigest()[:8], 16) % 100
        boundary = 0
        variant = variants[-1]
        for candidate in variants:
            boundary += candidate.allocation_percent
            if bucket < boundary:
                variant = candidate
                break
        control = variant.action_type == "no_action"
        action.experiment_variant_id = variant.id
        original_action = action.action_type
        if control:
            action.action_type = "no_action"
            action.status = "holdout"
            action.execution_mode = "controlled_holdout"
            action.delivery_status = "suppressed"
            action.execution_result = {"recommended_action": original_action, "holdout_reason": "Randomized control; no customer contact or provider execution"}
            approval = db.scalar(select(Approval).where(Approval.recovery_action_id == action.id))
            if approval:
                approval.status = "not_required_holdout"
        result = ExperimentResult(
            merchant_id=merchant_id,
            experiment_id=controlled.id,
            variant_id=variant.id,
            recovery_action_id=action.id,
            risk_event_id=risk.id,
            assignment_group="control" if control else "treatment",
            predicted_probability=decision.predicted_probability,
            predicted_recovery_paise=decision.expected_recovery_paise,
            chosen_action=action.action_type,
            actual_result="pending_control" if control else "pending",
            actual_recovered_paise=0,
        )
        db.add(result)
        audit(db, merchant_id, "controlled_experiment_assigned", {"message": f"Deterministic holdout assignment: {'control' if control else 'treatment'}", "experiment_id": controlled.id, "variant_id": variant.id, "bucket": bucket}, action, decision.id)
        return result
    experiment = db.scalar(select(Experiment).where(Experiment.merchant_id == merchant_id, Experiment.name == OBSERVATIONAL_EXPERIMENT_NAME))
    if not experiment:
        experiment = Experiment(merchant_id=merchant_id, name=OBSERVATIONAL_EXPERIMENT_NAME, segment="All policy-evaluated merchant-prepared recovery actions", experiment_type="observational", status="running")
        db.add(experiment)
        db.flush()
    variant = db.scalar(select(ExperimentVariant).where(ExperimentVariant.experiment_id == experiment.id, ExperimentVariant.action_type == action.action_type))
    if not variant:
        variant = ExperimentVariant(merchant_id=merchant_id, experiment_id=experiment.id, name=f"OBSERVED — {action.action_type.replace('_', ' ').title()}", action_type=action.action_type, allocation_percent=0)
        db.add(variant)
        db.flush()
    action.experiment_variant_id = variant.id
    result = ExperimentResult(merchant_id=merchant_id, experiment_id=experiment.id, variant_id=variant.id, recovery_action_id=action.id, risk_event_id=risk.id, assignment_group="observed", predicted_probability=decision.predicted_probability, predicted_recovery_paise=decision.expected_recovery_paise, chosen_action=action.action_type, actual_result="excluded_policy_blocked" if action.status == "blocked" else ("shadow" if action.status == "shadow" else "pending"), actual_recovered_paise=0)
    db.add(result)
    performance = db.scalar(select(StrategyPerformance).where(StrategyPerformance.merchant_id == merchant_id, StrategyPerformance.reason_code == risk.root_cause, StrategyPerformance.action_type == action.action_type))
    if not performance:
        performance = StrategyPerformance(merchant_id=merchant_id, reason_code=risk.root_cause, action_type=action.action_type, participants=0, successes=0, recovered_paise=0)
        db.add(performance)
    performance.participants += 1
    audit(db, merchant_id, "experiment_assigned", {"message": "Prepared action assigned to observational strategy cohort", "experiment_id": experiment.id, "variant_id": variant.id, "outcome": "pending"}, action, decision.id)
    return result


def set_experiment_outcome(db: Session, action: RecoveryAction, outcome: str, amount_paise: int = 0) -> None:
    result = db.scalar(select(ExperimentResult).where(ExperimentResult.merchant_id == action.merchant_id, ExperimentResult.recovery_action_id == action.id))
    if result:
        result.actual_result = outcome
        result.actual_recovered_paise = amount_paise


def ensure_action(db: Session, merchant_id: str, decision: AgentDecision, *, commit: bool = True) -> RecoveryAction:
    existing = db.scalar(select(RecoveryAction).where(RecoveryAction.merchant_id == merchant_id, RecoveryAction.decision_id == decision.id))
    if existing:
        return existing
    risk = db.get(RiskEvent, decision.risk_event_id)
    payment = db.get(Payment, risk.payment_id)
    status = "awaiting_approval" if decision.policy_status == "approval_required" else ("approved" if decision.policy_status == "approved" else "blocked")
    policy = db.scalar(select(MerchantPolicy).where(MerchantPolicy.merchant_id == merchant_id))
    shadow = bool(policy and policy.shadow_mode and status != "blocked")
    if shadow:
        status = "shadow"
    action = RecoveryAction(merchant_id=merchant_id, decision_id=decision.id, payment_id=payment.id, action_type=decision.selected_action, status=status, idempotency_key=f"decision:{decision.id}", execution_mode="shadow" if shadow else "pending", delivery_status="suppressed" if shadow or status == "blocked" else "not_started")
    db.add(action)
    db.flush()
    if status == "awaiting_approval":
        db.add(Approval(merchant_id=merchant_id, recovery_action_id=action.id, status="pending"))
    audit(db, merchant_id, "shadow_recommendation" if shadow else "govern", {"message": "Shadow mode recorded the recommendation without customer contact or provider execution" if shadow else decision.policy_result["reason"], "policy": decision.policy_result, "shadow_mode": shadow}, action, decision.id)
    assign_prepared_experiment(db, merchant_id, action, decision)
    if commit:
        db.commit()
    else:
        db.flush()
    return action


def create_payment_link(db: Session, merchant_id: str, decision: AgentDecision) -> RecoveryAction:
    action = ensure_action(db, merchant_id, decision)
    if action.status in {"shadow", "holdout"}:
        raise PermissionError("Shadow/holdout action recorded; provider execution and customer contact are intentionally suppressed")
    if action.status == "blocked":
        raise ValueError("Policy blocked this action")
    if action.status == "awaiting_approval":
        raise PermissionError("Merchant approval required")
    if action.provider_reference:
        return action
    if decision.selected_action not in {"recovery_link", "alternate_payment", "checkout_recovery"}:
        action.status = "blocked"
        action.execution_result = {"error": "This endpoint only creates customer-initiated payment links; provider-managed retries are never impersonated"}
        audit(db, merchant_id, "guardrail_blocked", {"message": action.execution_result["error"]}, action, decision.id)
        db.commit()
        raise ValueError(action.execution_result["error"])

    risk = db.get(RiskEvent, decision.risk_event_id)
    payment = db.get(Payment, risk.payment_id)
    order = db.get(Order, payment.order_id)
    customer = db.get(Customer, order.customer_id)
    policy = db.scalar(select(MerchantPolicy).where(MerchantPolicy.merchant_id == merchant_id))
    guardrails = workflow_guardrails(db, merchant_id, payment, decision.selected_action, policy)
    attempt_count = int(db.scalar(select(func.count()).select_from(PaymentAttempt).where(PaymentAttempt.payment_id == payment.id)) or 0)
    current = evaluate_policy(
        amount_paise=order.amount_paise,
        retry_count=max(0, attempt_count - 1),
        confidence=decision.confidence,
        action=decision.selected_action,
        allowed_actions=policy.allowed_actions,
        automatic_threshold_paise=policy.automatic_threshold_paise,
        approval_threshold_paise=policy.approval_threshold_paise,
        blocked_threshold_paise=policy.blocked_threshold_paise,
        max_retries=policy.max_retries,
        minimum_confidence=policy.minimum_confidence,
        payment_type=payment.payment_type,
        payment_method=payment.method,
        failure_code=payment.failure_code,
        mandate_grace_window_active=guardrails["mandate_grace_window_active"],
        retry_count_7d=guardrails["retry_count_7d"],
        circuit_breaker_active=guardrails["circuit_breaker_active"],
        circuit_breaker_reason=guardrails["circuit_breaker_reason"],
    )
    if not current["allowed"]:
        action.status = "blocked"
        action.execution_result = {"error": current["reason"], "policy_code": current.get("policy_code"), "guardrails": guardrails}
        audit(db, merchant_id, "guardrail_blocked", {"message": current["reason"], "policy": current, "guardrails": guardrails}, action, decision.id)
        db.commit()
        raise ValueError(current["reason"])
    try:
        result = provider(db, merchant_id, policy).create_payment_link(order.amount_paise, action.id, f"Recover order {order.external_ref}", {"name": customer.name, "email": customer.email, "phone": customer.phone})
    except ProviderError as exc:
        action.status = "failed"
        action.execution_result = {"error": str(exc)}
        audit(db, merchant_id, "execution_failed", {"message": str(exc)}, action, decision.id)
        db.commit()
        raise
    action.execution_mode = result.mode
    action.provider_reference = result.provider_id
    action.provider_url = result.url
    action.status = "executed"
    action.delivery_status = "link_created"
    action.delivery_channel = "merchant_shared_link"
    action.execution_result = {"provider_status": result.status, "guardrails": guardrails, "delivery": {"channel": "merchant_shared_link", "notification_requested": False, "delivered": "not_confirmed"}}
    action.executed_at = utcnow()
    db.add(RazorpayPaymentLink(merchant_id=merchant_id, recovery_action_id=action.id, razorpay_payment_link_id=result.provider_id, short_url=result.url, amount_paise=order.amount_paise, status=result.status, mode=result.mode, raw_data=result.raw))
    audit(db, merchant_id, "execute", {"message": result.raw.get("label", "Razorpay Test Mode Payment Link created"), "mode": result.mode, "guardrails": guardrails}, action, decision.id)
    db.commit()
    return action


def verify_and_attribute(db: Session, action: RecoveryAction, razorpay_payment_id: str | None, amount: int, source: str) -> bool:
    if action.verification_status == "verified":
        return False
    if db.scalar(select(RecoveryAttribution).where(RecoveryAttribution.payment_id == action.payment_id)):
        return False
    payment = db.get(Payment, action.payment_id)
    order = db.get(Order, payment.order_id)
    amount = min(amount, order.amount_paise)
    attribution = RecoveryAttribution(merchant_id=action.merchant_id, recovery_action_id=action.id, payment_id=payment.id, razorpay_payment_id=razorpay_payment_id, amount_recovered_paise=amount, verification_status="verified")
    db.add(attribution)
    action.status = "verified"
    action.verification_status = "verified"
    action.verification_source = source
    action.razorpay_payment_id = razorpay_payment_id
    action.actual_recovered_paise = amount
    action.delivery_status = "paid"
    action.verified_at = utcnow()
    payment.status = "captured"
    order.status = "paid_recovered"
    risk = db.scalar(select(RiskEvent).where(RiskEvent.payment_id == payment.id))
    performance = db.scalar(select(StrategyPerformance).where(StrategyPerformance.merchant_id == action.merchant_id, StrategyPerformance.reason_code == risk.root_cause, StrategyPerformance.action_type == action.action_type))
    if not performance:
        performance = StrategyPerformance(merchant_id=action.merchant_id, reason_code=risk.root_cause, action_type=action.action_type, participants=1, successes=0, recovered_paise=0)
        db.add(performance)
    performance.successes += 1
    performance.recovered_paise += amount
    set_experiment_outcome(db, action, "success", amount)
    audit(db, action.merchant_id, "verify", {"message": "Payment outcome verified", "source": source, "razorpay_payment_id": razorpay_payment_id}, action, amount=amount)
    db.commit()
    return True

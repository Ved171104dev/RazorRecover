from __future__ import annotations

from math import sqrt

UNRECOVERABLE_RETRY_FAILURES = frozenset({"CARD_EXPIRED", "ACCOUNT_BLOCKED"})
ONE_TIME_METHODS = frozenset({"upi", "card"})
RETRY_CEILING_7_DAYS = 3
HOURLY_RETRY_SUCCESS_FLOOR = 0.15


class StrategyOption(dict):
    __getattr__ = dict.__getitem__


def expected_recovery(amount_paise: int, probability: float, cost_paise: int, risk_penalty_paise: int) -> int:
    if amount_paise < 0 or cost_paise < 0 or risk_penalty_paise < 0 or not 0 <= probability <= 1:
        raise ValueError("invalid recovery inputs")
    return max(0, round(amount_paise * probability) - cost_paise - risk_penalty_paise)


def action_eligibility(
    *,
    action: str,
    payment_type: str,
    payment_method: str | None,
    failure_code: str | None,
    mandate_grace_window_active: bool,
) -> tuple[bool, str, str]:
    """Deterministic regulatory/product boundary; never delegated to an LLM."""
    recurring = payment_type == "recurring"
    failure = (failure_code or "").upper()
    if action == "retry" and failure in UNRECOVERABLE_RETRY_FAILURES:
        return False, f"{failure} is unrecoverable; retries are hard-stopped", "blocked"
    if action == "retry" and not recurring and (payment_method or "").lower() in ONE_TIME_METHODS:
        return False, "One-time UPI/card payments require a customer-initiated recovery link; silent retry is prohibited", "customer_consent_required"
    if action == "retry" and recurring and not mandate_grace_window_active:
        return False, "Recurring retry is outside the configured mandate retry window", "mandate_window_closed"
    if action == "retry" and recurring:
        return True, "Provider-managed subscription retry is eligible inside the mandate window", "provider_managed_subscription_retry"
    if action in {"recovery_link", "alternate_payment", "checkout_recovery"}:
        return True, "Customer initiates and authenticates the new payment", "customer_initiated_payment_link"
    return True, "Eligible recovery intervention", "merchant_workflow"


def calculate_strategies(
    amount_paise: int,
    recovery_probability: float,
    failure_code: str | None,
    preferred_method: str,
    retry_count: int,
    confidence: float,
    history: dict[str, float] | None = None,
    *,
    payment_type: str = "one_time",
    payment_method: str | None = None,
    mandate_grace_window_active: bool = False,
) -> list[StrategyOption]:
    history = history or {}
    upi = failure_code == "UPI_TIMEOUT"
    card = preferred_method == "card"
    raw = [
        ("retry", max(.08, recovery_probability * (.45 if retry_count else .58)), 200, 1200, "Prior retries lower conversion."),
        ("recovery_link", min(.88, .69 if upi and card else recovery_probability * .79), 900, 500, "A Razorpay Payment Link provides a legitimate customer-initiated fallback."),
        ("alternate_payment", min(.90, .66 if upi and card else recovery_probability * .81), 1200, 600, "Failure evidence and successful alternate-method history favour customer choice."),
    ]
    if history:
        raw = [(a, min(.92, max(.05, p * .7 + history.get(a, p) * .3)), c, r, w) for a, p, c, r, w in raw]
    output: list[StrategyOption] = []
    for action, probability, cost, penalty, reason in raw:
        eligible, eligibility_reason, execution_type = action_eligibility(
            action=action,
            payment_type=payment_type,
            payment_method=payment_method,
            failure_code=failure_code,
            mandate_grace_window_active=mandate_grace_window_active,
        )
        output.append(StrategyOption(
            action=action,
            probability=round(probability, 3),
            expected_recovery_paise=expected_recovery(amount_paise, probability, cost, penalty) if eligible else 0,
            cost_paise=cost,
            risk_penalty_paise=penalty,
            confidence=confidence,
            eligible=eligible,
            execution_type=execution_type,
            eligibility_reason=eligibility_reason,
            reason=f"{reason} {eligibility_reason}",
        ))
    return sorted(output, key=lambda item: (item.eligible, item.expected_recovery_paise), reverse=True)


def evaluate_policy(
    *,
    amount_paise: int,
    retry_count: int,
    confidence: float,
    action: str,
    allowed_actions: list[str],
    automatic_threshold_paise: int,
    approval_threshold_paise: int,
    blocked_threshold_paise: int,
    max_retries: int,
    minimum_confidence: float,
    duplicate: bool = False,
    cooldown_active: bool = False,
    payment_type: str = "one_time",
    payment_method: str | None = None,
    failure_code: str | None = None,
    mandate_grace_window_active: bool = False,
    retry_count_7d: int | None = None,
    circuit_breaker_active: bool = False,
    circuit_breaker_reason: str | None = None,
) -> dict:
    def blocked(reason: str, code: str, risk: str = "BLOCKED") -> dict:
        return {"allowed": False, "approval_required": False, "risk_level": risk, "reason": reason, "policy_code": code}

    if duplicate:
        return blocked("Duplicate action already exists", "DUPLICATE_ACTION")
    if circuit_breaker_active:
        return blocked(circuit_breaker_reason or "Recovery circuit breaker is active", "HOURLY_RETRY_CIRCUIT_BREAKER")
    if cooldown_active:
        return blocked("Customer recovery cooldown is active", "CUSTOMER_COOLDOWN")
    eligible, eligibility_reason, execution_type = action_eligibility(
        action=action,
        payment_type=payment_type,
        payment_method=payment_method,
        failure_code=failure_code,
        mandate_grace_window_active=mandate_grace_window_active,
    )
    if not eligible:
        return blocked(eligibility_reason, "REGULATORY_ACTION_INELIGIBLE")
    if action not in allowed_actions:
        return blocked("Intervention disabled by merchant policy", "ACTION_DISABLED")
    if confidence < minimum_confidence:
        return blocked("Confidence is below merchant minimum", "LOW_CONFIDENCE")
    seven_day_retries = retry_count if retry_count_7d is None else retry_count_7d
    if action == "retry" and seven_day_retries >= RETRY_CEILING_7_DAYS:
        return blocked("Hard ceiling reached: maximum 3 retries per invoice within 7 days", "RETRY_CEILING_7D")
    if action == "retry" and retry_count >= max_retries:
        return blocked("Maximum retry count reached under merchant policy", "MERCHANT_RETRY_LIMIT")
    if amount_paise > blocked_threshold_paise:
        return blocked("Amount exceeds safe recovery ceiling", "AMOUNT_CEILING", "HIGH")
    if amount_paise > automatic_threshold_paise:
        return {"allowed": True, "approval_required": True, "risk_level": "HIGH" if amount_paise > approval_threshold_paise else "MEDIUM", "reason": "Merchant approval required for this amount", "policy_code": "MERCHANT_APPROVAL", "execution_type": execution_type}
    return {"allowed": True, "approval_required": False, "risk_level": "LOW", "reason": "Eligible under merchant and regulatory policy", "policy_code": "AUTO_ELIGIBLE", "execution_type": execution_type}


def check_policy(**kwargs):
    aliases = {"retry_payment": "retry", "recovery_reminder": "recovery_link"}
    kwargs["action"] = aliases.get(kwargs["action"], kwargs["action"])
    kwargs["allowed_actions"] = [aliases.get(item, item) for item in kwargs["allowed_actions"]]
    kwargs.setdefault("blocked_threshold_paise", 5_000_000)
    return evaluate_policy(**kwargs)


def recovery_probability(features: dict) -> dict:
    score = .18
    reasons: list[str] = []
    if features.get("failure_code") == "UPI_TIMEOUT":
        score += .24
        reasons.append("UPI_TIMEOUT")
    if features.get("retry_count", 0) > 0:
        score -= .08
        reasons.append("RETRY_ALREADY_FAILED")
    if features.get("historical_success", 0) > .75:
        score += .18
        reasons.append("HIGH_CUSTOMER_SUCCESS")
    if features.get("preferred_method") == "card":
        score += .15
        reasons.append("CARD_HISTORY")
    if features.get("device") == "android":
        score += .03
        reasons.append("ANDROID_CLUSTER")
    probability = max(.05, min(.92, score))
    confidence = min(.95, .70 + abs(probability - .5) * .45)
    return {"risk_score": round(min(.98, .38 + probability * .65), 3), "recovery_probability": round(probability, 3), "confidence": round(confidence, 3), "reason_codes": reasons}


def ci95(successes: int, n: int):
    if n < 30:
        return None
    probability = successes / n
    margin = 1.96 * sqrt(probability * (1 - probability) / n)
    return [round(max(0, probability - margin) * 100, 1), round(min(1, probability + margin) * 100, 1)]

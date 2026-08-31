from app.services.recovery import calculate_strategies,ci95,evaluate_policy,expected_recovery,recovery_probability
from app.ml.inference import RecoveryModel
def test_money_expected_recovery_is_integer_paise():assert expected_recovery(349900,.69,900,500)==240031
def test_upi_card_fallback_is_highest():assert calculate_strategies(349900,.69,"UPI_TIMEOUT","card",1,.87)[0]["action"]=="recovery_link"
def test_policy_blocks_retry_limit():
    x=evaluate_policy(amount_paise=200000,retry_count=2,confidence=.8,action="retry",allowed_actions=["retry"],automatic_threshold_paise=500000,approval_threshold_paise=1500000,blocked_threshold_paise=5000000,max_retries=2,minimum_confidence=.65);assert not x["allowed"]
def test_policy_requires_approval():assert evaluate_policy(amount_paise=800000,retry_count=0,confidence=.8,action="recovery_link",allowed_actions=["recovery_link"],automatic_threshold_paise=500000,approval_threshold_paise=1500000,blocked_threshold_paise=5000000,max_retries=2,minimum_confidence=.65)["approval_required"]
def test_risk_is_reproducible():assert recovery_probability({"failure_code":"UPI_TIMEOUT","retry_count":1,"historical_success":.9,"preferred_method":"card","device":"android"})==recovery_probability({"failure_code":"UPI_TIMEOUT","retry_count":1,"historical_success":.9,"preferred_method":"card","device":"android"})
def test_interval_needs_sample():assert ci95(2,10) is None and ci95(20,100)

def test_one_time_card_or_upi_never_silently_retries():
    choices=calculate_strategies(349900,.69,"UPI_TIMEOUT","card",0,.87,payment_type="one_time",payment_method="upi")
    retry=next(item for item in choices if item["action"]=="retry")
    assert not retry["eligible"] and retry["expected_recovery_paise"]==0
    assert choices[0]["action"] in {"recovery_link","alternate_payment"}

def test_recurring_retry_requires_active_mandate_window():
    open_choices=calculate_strategies(349900,.69,"INSUFFICIENT_FUNDS","card",0,.87,payment_type="recurring",payment_method="card",mandate_grace_window_active=True)
    closed_choices=calculate_strategies(349900,.69,"INSUFFICIENT_FUNDS","card",0,.87,payment_type="recurring",payment_method="card",mandate_grace_window_active=False)
    assert next(item for item in open_choices if item["action"]=="retry")["eligible"]
    assert not next(item for item in closed_choices if item["action"]=="retry")["eligible"]

def test_unrecoverable_failures_and_seven_day_ceiling_block_retry():
    common=dict(amount_paise=200000,retry_count=0,confidence=.8,action="retry",allowed_actions=["retry"],automatic_threshold_paise=500000,approval_threshold_paise=1500000,blocked_threshold_paise=5000000,max_retries=5,minimum_confidence=.65,payment_type="recurring",payment_method="card",mandate_grace_window_active=True)
    assert evaluate_policy(**common,failure_code="CARD_EXPIRED")["policy_code"]=="REGULATORY_ACTION_INELIGIBLE"
    assert evaluate_policy(**common,failure_code="INSUFFICIENT_FUNDS",retry_count_7d=3)["policy_code"]=="RETRY_CEILING_7D"

def test_local_model_warm_inference_is_sub_50ms():
    model=RecoveryModel();features={"amount_paise":349900,"method":"upi","failure_code":"UPI_TIMEOUT","retry_count":1,"historical_success":.9,"preferred_method":"card","device":"android"}
    timings=[model.predict(features)["inference_latency_ms"] for _ in range(3)]
    assert max(timings)<50,timings

from app.services.recovery import calculate_strategies,ci95,evaluate_policy,expected_recovery,recovery_probability
def test_money_expected_recovery_is_integer_paise():assert expected_recovery(349900,.69,900,500)==240031
def test_upi_card_fallback_is_highest():assert calculate_strategies(349900,.69,"UPI_TIMEOUT","card",1,.87)[0]["action"]=="recovery_link"
def test_policy_blocks_retry_limit():
    x=evaluate_policy(amount_paise=200000,retry_count=2,confidence=.8,action="retry",allowed_actions=["retry"],automatic_threshold_paise=500000,approval_threshold_paise=1500000,blocked_threshold_paise=5000000,max_retries=2,minimum_confidence=.65);assert not x["allowed"]
def test_policy_requires_approval():assert evaluate_policy(amount_paise=800000,retry_count=0,confidence=.8,action="recovery_link",allowed_actions=["recovery_link"],automatic_threshold_paise=500000,approval_threshold_paise=1500000,blocked_threshold_paise=5000000,max_retries=2,minimum_confidence=.65)["approval_required"]
def test_risk_is_reproducible():assert recovery_probability({"failure_code":"UPI_TIMEOUT","retry_count":1,"historical_success":.9,"preferred_method":"card","device":"android"})==recovery_probability({"failure_code":"UPI_TIMEOUT","retry_count":1,"historical_success":.9,"preferred_method":"card","device":"android"})
def test_interval_needs_sample():assert ci95(2,10) is None and ci95(20,100)


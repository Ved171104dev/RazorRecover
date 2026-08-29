from app.services.recovery import calculate_strategies,check_policy,ci95
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


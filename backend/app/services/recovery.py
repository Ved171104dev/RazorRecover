from __future__ import annotations
from math import sqrt
class StrategyOption(dict):
    __getattr__=dict.__getitem__
def expected_recovery(amount_paise:int,probability:float,cost_paise:int,risk_penalty_paise:int)->int:
    if amount_paise<0 or cost_paise<0 or risk_penalty_paise<0 or not 0<=probability<=1:raise ValueError("invalid recovery inputs")
    return max(0,round(amount_paise*probability)-cost_paise-risk_penalty_paise)
def calculate_strategies(amount_paise:int,recovery_probability:float,failure_code:str|None,preferred_method:str,retry_count:int,confidence:float,history:dict[str,float]|None=None)->list[StrategyOption]:
    history=history or {};upi=failure_code=="UPI_TIMEOUT";card=preferred_method=="card"
    raw=[("retry",max(.08,recovery_probability*(.45 if retry_count else .58)),200,1200,"Prior retries lower conversion."),
         ("recovery_link",min(.88,.69 if upi and card else recovery_probability*.79),900,500,"A Razorpay Payment Link provides a legitimate customer-initiated card fallback."),
         ("alternate_payment",min(.90,.66 if upi and card else recovery_probability*.81),1200,600,"UPI timeout and successful card history favour alternate payment.")]
    if history:raw=[(a,min(.92,max(.05,p*.7+history.get(a,p)*.3)),c,r,w) for a,p,c,r,w in raw]
    out=[StrategyOption(action=a,probability=round(p,3),expected_recovery_paise=expected_recovery(amount_paise,p,c,r),cost_paise=c,risk_penalty_paise=r,confidence=confidence,reason=w) for a,p,c,r,w in raw]
    return sorted(out,key=lambda x:x.expected_recovery_paise,reverse=True)
def evaluate_policy(*,amount_paise:int,retry_count:int,confidence:float,action:str,allowed_actions:list[str],automatic_threshold_paise:int,approval_threshold_paise:int,blocked_threshold_paise:int,max_retries:int,minimum_confidence:float,duplicate:bool=False,cooldown_active:bool=False)->dict:
    if duplicate:return {"allowed":False,"approval_required":False,"risk_level":"BLOCKED","reason":"Duplicate action already exists"}
    if cooldown_active:return {"allowed":False,"approval_required":False,"risk_level":"BLOCKED","reason":"Customer recovery cooldown is active"}
    if action not in allowed_actions:return {"allowed":False,"approval_required":False,"risk_level":"BLOCKED","reason":"Intervention disabled by merchant policy"}
    if confidence<minimum_confidence:return {"allowed":False,"approval_required":False,"risk_level":"BLOCKED","reason":"Confidence is below merchant minimum"}
    if action=="retry" and retry_count>=max_retries:return {"allowed":False,"approval_required":False,"risk_level":"BLOCKED","reason":"Maximum retry count reached"}
    if amount_paise>blocked_threshold_paise:return {"allowed":False,"approval_required":False,"risk_level":"HIGH","reason":"Amount exceeds safe recovery ceiling"}
    if amount_paise>automatic_threshold_paise:return {"allowed":True,"approval_required":True,"risk_level":"HIGH" if amount_paise>approval_threshold_paise else "MEDIUM","reason":"Merchant approval required for this amount"}
    return {"allowed":True,"approval_required":False,"risk_level":"LOW","reason":"Eligible under merchant policy"}
def check_policy(**kwargs):
    aliases={"retry_payment":"retry","recovery_reminder":"recovery_link"};kwargs["action"]=aliases.get(kwargs["action"],kwargs["action"]);kwargs["allowed_actions"]=[aliases.get(x,x) for x in kwargs["allowed_actions"]];kwargs.setdefault("blocked_threshold_paise",5_000_000)
    return evaluate_policy(**kwargs)
def recovery_probability(features:dict)->dict:
    score=.18;reasons=[]
    if features.get("failure_code")=="UPI_TIMEOUT":score+=.24;reasons.append("UPI_TIMEOUT")
    if features.get("retry_count",0)>0:score-=.08;reasons.append("RETRY_ALREADY_FAILED")
    if features.get("historical_success",0)>.75:score+=.18;reasons.append("HIGH_CUSTOMER_SUCCESS")
    if features.get("preferred_method")=="card":score+=.15;reasons.append("CARD_HISTORY")
    if features.get("device")=="android":score+=.03;reasons.append("ANDROID_CLUSTER")
    probability=max(.05,min(.92,score));confidence=min(.95,.70+abs(probability-.5)*.45)
    return {"risk_score":round(min(.98,.38+probability*.65),3),"recovery_probability":round(probability,3),"confidence":round(confidence,3),"reason_codes":reasons}
def ci95(successes:int,n:int):
    if n<30:return None
    p=successes/n;m=1.96*sqrt(p*(1-p)/n);return [round(max(0,p-m)*100,1),round(min(1,p+m)*100,1)]


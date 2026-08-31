from __future__ import annotations
import hashlib,json,os,re,secrets
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any,Literal
from uuid import uuid4
from fastapi import BackgroundTasks,Depends,FastAPI,File,HTTPException,Request,Response,UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel,EmailStr,Field,model_validator
from sqlalchemy import desc,func,select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db import *
from app.providers.razorpay_adapter import ProviderError,verify_webhook_signature
from app.services.auth import COOKIE,Principal,digest,new_session,principal,require_csrf,verify_password
from app.services.rate_limit import allowed
from app.services.llm import narrate
from app.services.crypto import SecretConfigurationError,decrypt_secret
from app.services.ingestion import add_import_record,backfill_legacy_import_records,connect_razorpay,disconnect_razorpay,ensure_webhook_token,get_import_run,import_payment_file,remove_import_record,remove_import_run,sync_razorpay,update_import_record
from app.services.recovery import ci95
from app.services.seed import create_merchant_account
from app.services.workflow import create_payment_link,provider
from app.workers.tasks import process_webhook

def db_session():
    db=SessionLocal()
    try:yield db
    finally:db.close()
def auth(request:Request,db:Session=Depends(db_session))->Principal:return principal(request,db)
def mutation(request:Request,db:Session=Depends(db_session))->Principal:
    p=principal(request,db);require_csrf(request,db);return p
@asynccontextmanager
async def lifespan(app:FastAPI):
    if os.getenv("AUTO_CREATE_SCHEMA","false").lower()=="true":
        create_all()
        ensure_compat_schema()
    yield
app=FastAPI(title="RazorRecover API",version="2.0.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[x for x in os.getenv("API_ORIGIN","http://localhost:3000").split(",")],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
@app.middleware("http")
async def request_context(request:Request,call_next):
    rid=request.headers.get("X-Request-ID") or str(uuid4());response=await call_next(request);response.headers["X-Request-ID"]=rid;response.headers["X-Content-Type-Options"]="nosniff";response.headers["Referrer-Policy"]="same-origin";return response
@app.exception_handler(IntegrityError)
async def conflict(_:Request,exc:IntegrityError):return JSONResponse(409,{"error":{"code":"CONFLICT","message":"The operation conflicts with existing state"}})

class Signup(BaseModel):
    name:str=Field(min_length=2,max_length=120);email:EmailStr;password:str=Field(min_length=10,max_length=128);merchant_name:str=Field(min_length=2,max_length=160)
    @model_validator(mode="after")
    def strong(self):
        if not re.search(r"[A-Z]",self.password) or not re.search(r"[a-z]",self.password) or not re.search(r"\d",self.password):raise ValueError("Password must include upper, lower, and number")
        return self
class Login(BaseModel):email:EmailStr;password:str=Field(min_length=1,max_length=128)
def set_auth(response:Response,token:str,csrf:str)->None:
    secure=os.getenv("COOKIE_SECURE","false").lower()=="true";response.set_cookie(COOKIE,token,httponly=True,secure=secure,samesite="lax",max_age=604800,path="/");response.set_cookie("rr_csrf",csrf,httponly=False,secure=secure,samesite="lax",max_age=604800,path="/")
def user_out(p:Principal):return {"user":{"id":p.user_id,"name":p.name,"email":p.email},"merchant":{"id":p.merchant_id,"role":p.role}}

@app.get("/health")
def health():return {"status":"ok","service":"api"}
@app.post("/api/auth/signup",status_code=201)
def signup(body:Signup,response:Response,request:Request,db:Session=Depends(db_session)):
    if not allowed(f"signup:{request.client.host if request.client else 'unknown'}",5,300):raise HTTPException(429,"Too many signup attempts")
    if db.scalar(select(User).where(User.email==body.email.lower())):raise HTTPException(409,"An account with this email exists")
    user,merchant=create_merchant_account(db,body.name,body.email,body.password,body.merchant_name)
    token,csrf=new_session(db,user.id);set_auth(response,token,csrf)
    return {"user":{"id":user.id,"name":user.name,"email":user.email},"merchant":{"id":merchant.id,"name":merchant.name,"role":"owner"}}
@app.post("/api/auth/login")
def login(body:Login,response:Response,request:Request,db:Session=Depends(db_session)):
    key=f"login:{request.client.host if request.client else 'unknown'}:{body.email.lower()}"
    if not allowed(key,8,300):raise HTTPException(429,"Too many login attempts; try again later")
    user=db.scalar(select(User).where(User.email==body.email.lower()))
    if not user or not verify_password(user.password_hash,body.password):raise HTTPException(401,"Invalid email or password")
    token,csrf=new_session(db,user.id);set_auth(response,token,csrf);p=principal(request_with_cookie(request,token),db);return user_out(p)
def request_with_cookie(request:Request,token:str):
    request._cookies={**request.cookies,COOKIE:token};return request
@app.post("/api/auth/logout")
def logout(response:Response,request:Request,p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    token=request.cookies.get(COOKIE);s=db.scalar(select(AuthSession).where(AuthSession.token_hash==digest(token or "")))
    if s:s.revoked_at=utcnow();db.commit()
    response.delete_cookie(COOKIE,path="/");response.delete_cookie("rr_csrf",path="/");return {"ok":True}
@app.get("/api/auth/me")
def me(p:Principal=Depends(auth),db:Session=Depends(db_session)):
    m=db.get(Merchant,p.merchant_id);return {**user_out(p),"merchant":{**user_out(p)["merchant"],"name":m.name}}
@app.post("/api/auth/forgot-password")
def forgot(_:dict):return {"message":"If the account exists, recovery instructions will be sent. Email delivery must be configured by the deployment operator."}

def action_out(a:RecoveryAction)->dict:
    return {"id":a.id,"decision_id":a.decision_id,"action_type":a.action_type,"status":a.status,"execution_mode":a.execution_mode,"provider_reference":a.provider_reference,"provider_url":a.provider_url,"execution_result":a.execution_result,"verification_status":a.verification_status,"verification_source":a.verification_source,"razorpay_payment_id":a.razorpay_payment_id,"actual_recovered_paise":a.actual_recovered_paise,"verified_at":a.verified_at.isoformat() if a.verified_at else None,"created_at":a.created_at.isoformat()}
def risk_out(db:Session,r:RiskEvent)->dict:
    pay=db.get(Payment,r.payment_id);order=db.get(Order,pay.order_id);c=db.get(Customer,order.customer_id);d=db.scalar(select(AgentDecision).where(AgentDecision.merchant_id==r.merchant_id,AgentDecision.risk_event_id==r.id));a=db.scalar(select(RecoveryAction).where(RecoveryAction.decision_id==d.id)) if d else None
    return {"id":r.id,"customer":{"id":c.id,"name":c.name,"email":c.email,"preferred_method":c.preferred_method,"success_rate":c.historical_success_rate},"order":{"id":order.id,"external_ref":order.external_ref,"amount_paise":order.amount_paise,"status":order.status,"data_source":order.data_source},"payment":{"id":pay.id,"external_ref":pay.external_ref,"method":pay.method,"payment_type":pay.payment_type,"failure_code":pay.failure_code,"status":pay.status,"data_source":pay.data_source},"risk_score":r.risk_score,"recovery_probability":r.recovery_probability,"confidence":r.confidence,"root_cause":r.root_cause,"reason_codes":r.reason_codes,"evidence":r.evidence,"recommended_intervention":d.selected_action if d else None,"expected_recovery_paise":d.expected_recovery_paise if d else 0,"policy_status":d.policy_status if d else "pending","action_status":a.status if a else "not_created","created_at":r.created_at.isoformat()}
def decision_out(db:Session,d:AgentDecision)->dict:
    r=db.get(RiskEvent,d.risk_event_id);a=db.scalar(select(RecoveryAction).where(RecoveryAction.decision_id==d.id))
    return {"id":d.id,"selected_action":d.selected_action,"candidates":d.candidates,"expected_recovery_paise":d.expected_recovery_paise,"predicted_probability":d.predicted_probability,"confidence":d.confidence,"policy":d.policy_result,"policy_status":d.policy_status,"explanation":d.explanation,"model_version":d.model_version,"risk":risk_out(db,r),"execution":action_out(a) if a else None,"created_at":d.created_at.isoformat()}

@app.get("/api/dashboard")
def dashboard(p:Principal=Depends(auth),db:Session=Depends(db_session)):
    mid=p.merchant_id
    risk=int(db.scalar(select(func.coalesce(func.sum(RiskEvent.affected_revenue_paise),0)).where(RiskEvent.merchant_id==mid,RiskEvent.status=="open")) or 0)
    expected=int(db.scalar(select(func.coalesce(func.sum(AgentDecision.expected_recovery_paise),0)).where(AgentDecision.merchant_id==mid)) or 0)
    recovered=int(db.scalar(select(func.coalesce(func.sum(RecoveryAttribution.amount_recovered_paise),0)).where(RecoveryAttribution.merchant_id==mid)) or 0)
    ac=int(db.scalar(select(func.count()).select_from(RecoveryAction).where(RecoveryAction.merchant_id==mid)) or 0)
    successful=int(db.scalar(select(func.count()).select_from(RecoveryAction).where(RecoveryAction.merchant_id==mid,RecoveryAction.verification_status=="verified")) or 0)
    blocked=int(db.scalar(select(func.count()).select_from(AgentDecision).where(AgentDecision.merchant_id==mid,AgentDecision.policy_status=="blocked")) or 0)
    pending=int(db.scalar(select(func.count()).select_from(RecoveryAction).where(RecoveryAction.merchant_id==mid,RecoveryAction.status=="awaiting_approval")) or 0)
    events=db.scalars(select(AgentEvent).where(AgentEvent.merchant_id==mid).order_by(desc(AgentEvent.created_at)).limit(12)).all()
    bycause=db.execute(select(RiskEvent.root_cause,func.sum(RiskEvent.affected_revenue_paise)).where(RiskEvent.merchant_id==mid).group_by(RiskEvent.root_cause).order_by(desc(func.sum(RiskEvent.affected_revenue_paise))).limit(5)).all()
    connection=db.scalar(select(RazorpayConnection).where(RazorpayConnection.merchant_id==mid));connected=bool(connection and connection.connection_status=="connected");payment_count=int(db.scalar(select(func.count()).select_from(Payment).where(Payment.merchant_id==mid)) or 0)
    recurring_recovered=int(db.scalar(select(func.coalesce(func.sum(RecoveryAttribution.amount_recovered_paise),0)).join(Payment,Payment.id==RecoveryAttribution.payment_id).where(RecoveryAttribution.merchant_id==mid,Payment.payment_type=="recurring")) or 0)
    executed_actions=db.scalars(select(RecoveryAction).where(RecoveryAction.merchant_id==mid,RecoveryAction.executed_at.is_not(None))).all();total_intervention_cost=0
    for action in executed_actions:
        decision=db.get(AgentDecision,action.decision_id);chosen=next((item for item in decision.candidates if item.get("action")==action.action_type),{}) if decision else {};total_intervention_cost+=int(chosen.get("cost_paise") or 0)
    successful_payments=int(db.scalar(select(func.count()).select_from(Payment).where(Payment.merchant_id==mid,Payment.status.in_(["captured","authorized"]))) or 0);baseline_successes=max(0,successful_payments-successful);baseline_rate=baseline_successes/payment_count*100 if payment_count else 0;current_rate=successful_payments/payment_count*100 if payment_count else 0
    policy=db.scalar(select(MerchantPolicy).where(MerchantPolicy.merchant_id==mid));paused=bool(policy and policy.recovery_paused_until and policy.recovery_paused_until>utcnow())
    return {"mode":"RAZORPAY TEST MODE — NO REAL MONEY" if connected else "SETUP REQUIRED — CONNECT A DATA SOURCE","onboarding":{"connected":connected,"has_payment_data":payment_count>0,"payment_count":payment_count},"metrics":{"revenue_at_risk_paise":risk,"recoverable_revenue_paise":expected,"recovered_revenue_paise":recovered,"recovered_gmv_paise":recovered,"recovered_arr_paise":recurring_recovered*12,"recovery_rate":round(recovered/risk*100,1) if risk else 0,"incremental_revenue_paise":max(0,recovered),"total_intervention_cost_paise":total_intervention_cost,"cost_per_recovery_paise":round(total_intervention_cost/successful) if successful else 0,"net_recovered_revenue_paise":max(0,recovered-total_intervention_cost),"gateway_success_rate_before":round(baseline_rate,2),"gateway_success_rate_after":round(current_rate,2),"gateway_success_rate_improvement_pp":round(current_rate-baseline_rate,2),"ai_actions":ac,"successful_actions":successful,"blocked_actions":blocked,"pending_approvals":pending,"active_experiments":int(db.scalar(select(func.count()).select_from(Experiment).where(Experiment.merchant_id==mid,Experiment.status=="running")) or 0),"recovery_circuit_breaker_active":paused,"recovery_circuit_breaker_reason":policy.recovery_pause_reason if paused else None},"events":[{"id":e.id,"stage":e.stage,"title":e.title,"detail":e.detail,"amount_paise":e.amount_paise,"created_at":e.created_at.isoformat()} for e in events],"charts":{"by_cause":[{"name":x,"value_paise":int(v)} for x,v in bycause],"recovery_series":[{"day":x,"recovered_paise":recovered if x=="Today" else 0} for x in ["-6d","-5d","-4d","-3d","-2d","Yesterday","Today"]]}}

@app.get("/api/risk/opportunities")
def risks(limit:int=50,p:Principal=Depends(auth),db:Session=Depends(db_session)):
    rows=db.scalars(select(RiskEvent).where(RiskEvent.merchant_id==p.merchant_id).order_by(desc(RiskEvent.affected_revenue_paise)).limit(min(100,limit))).all();return {"items":[risk_out(db,r) for r in rows]}
@app.get("/api/risk/opportunities/{rid}")
def risk_detail(rid:str,p:Principal=Depends(auth),db:Session=Depends(db_session)):
    r=db.scalar(select(RiskEvent).where(RiskEvent.id==rid,RiskEvent.merchant_id==p.merchant_id))
    if not r:raise HTTPException(404,"Risk opportunity not found")
    out=risk_out(db,r);d=db.scalar(select(AgentDecision).where(AgentDecision.risk_event_id==r.id,AgentDecision.merchant_id==p.merchant_id));return {**out,"decision":decision_out(db,d) if d else None}
@app.get("/api/decisions")
def decisions(p:Principal=Depends(auth),db:Session=Depends(db_session)):
    rows=db.scalars(select(AgentDecision).where(AgentDecision.merchant_id==p.merchant_id).order_by(desc(AgentDecision.created_at)).limit(100)).all();return {"items":[decision_out(db,d) for d in rows]}
@app.get("/api/decisions/{did}")
def decision(did:str,p:Principal=Depends(auth),db:Session=Depends(db_session)):
    d=db.scalar(select(AgentDecision).where(AgentDecision.id==did,AgentDecision.merchant_id==p.merchant_id))
    if not d:raise HTTPException(404,"Decision not found")
    return decision_out(db,d)
@app.get("/api/actions")
def actions(status:str|None=None,p:Principal=Depends(auth),db:Session=Depends(db_session)):
    q=select(RecoveryAction).where(RecoveryAction.merchant_id==p.merchant_id).order_by(desc(RecoveryAction.created_at))
    if status:q=q.where(RecoveryAction.status==status)
    return {"items":[action_out(a) for a in db.scalars(q.limit(100)).all()]}
@app.post("/api/actions/{aid}/approve")
def approve(aid:str,p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    a=db.scalar(select(RecoveryAction).where(RecoveryAction.id==aid,RecoveryAction.merchant_id==p.merchant_id))
    if not a:raise HTTPException(404,"Action not found")
    if a.status!="awaiting_approval":raise HTTPException(409,"Action is not awaiting approval")
    ap=db.scalar(select(Approval).where(Approval.recovery_action_id==a.id));ap.status="approved";ap.reviewed_by_user_id=p.user_id;ap.reviewed_at=utcnow();a.status="approved";db.commit();return action_out(a)
@app.post("/api/actions/{aid}/reject")
def reject(aid:str,p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    a=db.scalar(select(RecoveryAction).where(RecoveryAction.id==aid,RecoveryAction.merchant_id==p.merchant_id))
    if not a:raise HTTPException(404,"Action not found")
    if a.status!="awaiting_approval":raise HTTPException(409,"Action is not awaiting approval")
    ap=db.scalar(select(Approval).where(Approval.recovery_action_id==a.id));ap.status="rejected";ap.reviewed_by_user_id=p.user_id;ap.reviewed_at=utcnow();a.status="rejected";db.commit();return action_out(a)
@app.post("/api/actions/{aid}/execute")
def execute(aid:str,p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    a=db.scalar(select(RecoveryAction).where(RecoveryAction.id==aid,RecoveryAction.merchant_id==p.merchant_id))
    if not a:raise HTTPException(404,"Action not found")
    d=db.get(AgentDecision,a.decision_id)
    try:return action_out(create_payment_link(db,p.merchant_id,d))
    except PermissionError as exc:raise HTTPException(409,str(exc))
    except (ValueError,ProviderError) as exc:raise HTTPException(422,str(exc))

class LinkRequest(BaseModel):opportunity_id:str
@app.post("/api/recovery/payment-link")
def payment_link(body:LinkRequest,p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    risk=db.scalar(select(RiskEvent).where(RiskEvent.id==body.opportunity_id,RiskEvent.merchant_id==p.merchant_id))
    if not risk:raise HTTPException(404,"Recovery opportunity not found")
    d=db.scalar(select(AgentDecision).where(AgentDecision.risk_event_id==risk.id,AgentDecision.merchant_id==p.merchant_id))
    try:a=create_payment_link(db,p.merchant_id,d);return action_out(a)
    except PermissionError as exc:
        a=ensure_action(db,p.merchant_id,d);return JSONResponse(202,{"action":action_out(a),"message":str(exc)})
    except (ValueError,ProviderError) as exc:raise HTTPException(422,str(exc))

class OrderCreate(BaseModel):internal_order_id:str
@app.post("/api/razorpay/orders")
def create_test_order(body:OrderCreate,p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    o=db.scalar(select(Order).where(Order.id==body.internal_order_id,Order.merchant_id==p.merchant_id));policy=db.scalar(select(MerchantPolicy).where(MerchantPolicy.merchant_id==p.merchant_id))
    if not o:raise HTTPException(404,"Order not found")
    try:r=provider(db,p.merchant_id,policy).create_order(o.amount_paise,o.currency,f"rr_{o.id[:24]}")
    except ProviderError as exc:raise HTTPException(502,str(exc))
    rec=RazorpayOrder(merchant_id=p.merchant_id,internal_order_id=o.id,razorpay_order_id=r.provider_id,amount_paise=o.amount_paise,currency=o.currency,status=r.status,raw_data=r.raw);db.add(rec);db.commit()
    return {"id":rec.id,"razorpay_order_id":r.provider_id,"mode":r.mode,"status":r.status}
@app.post("/api/razorpay/orders/{record_id}/sync")
def sync_test_order(record_id:str,p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    rec=db.scalar(select(RazorpayOrder).where(RazorpayOrder.id==record_id,RazorpayOrder.merchant_id==p.merchant_id));policy=db.scalar(select(MerchantPolicy).where(MerchantPolicy.merchant_id==p.merchant_id))
    if not rec:raise HTTPException(404,"Razorpay order record not found")
    try:data=provider(db,p.merchant_id,policy).fetch_order(rec.razorpay_order_id);payments=provider(db,p.merchant_id,policy).list_order_payments(rec.razorpay_order_id)
    except ProviderError as exc:raise HTTPException(502,str(exc))
    rec.status=data["status"];rec.raw_data=data
    for item in payments:
        rp=db.scalar(select(RazorpayPayment).where(RazorpayPayment.merchant_id==p.merchant_id,RazorpayPayment.razorpay_payment_id==item["id"]))
        if not rp:db.add(RazorpayPayment(merchant_id=p.merchant_id,razorpay_payment_id=item["id"],razorpay_order_id=item.get("order_id"),amount_paise=item["amount"],currency=item.get("currency","INR"),status=item["status"],method=item.get("method"),failure_code=item.get("error_code"),raw_data=item))
    db.commit();return {"mode":"razorpay_test","status":rec.status,"payments":payments}

@app.get("/api/experiments")
def experiments(p:Principal=Depends(auth),db:Session=Depends(db_session)):
    result=[]
    for e in db.scalars(select(Experiment).where(Experiment.merchant_id==p.merchant_id)).all():
        variants=[]
        for v in db.scalars(select(ExperimentVariant).where(ExperimentVariant.experiment_id==e.id)).all():
            perf=db.scalar(select(StrategyPerformance).where(StrategyPerformance.merchant_id==p.merchant_id,StrategyPerformance.action_type==v.action_type,RiskEvent.root_cause=="UPI_TIMEOUT")) if False else db.scalar(select(StrategyPerformance).where(StrategyPerformance.merchant_id==p.merchant_id,StrategyPerformance.action_type==v.action_type))
            n=perf.participants if perf else 0;s=perf.successes if perf else 0;rev=perf.recovered_paise if perf else 0
            variants.append({"id":v.id,"variant":v.name,"action_type":v.action_type,"sample_size":n,"successful_recoveries":s,"recovered_paise":rev,"recovery_rate":round(s/n*100,1) if n else 0,"revenue_per_participant_paise":round(rev/n) if n else 0,"confidence_interval":ci95(s,n)})
        control=variants[0] if variants else None;winner=max(variants,key=lambda x:x["recovery_rate"],default=None);result.append({"id":e.id,"name":e.name,"segment":e.segment,"status":e.status,"variants":variants,"winner":winner["variant"] if winner and winner!=control else None,"incremental_revenue_paise":max(0,(winner["recovered_paise"] if winner else 0)-(control["recovered_paise"] if control else 0)),"note":"Observed results with sample sizes and intervals; statistical significance is not claimed."})
    return {"items":result}
class ExperimentCreate(BaseModel):name:str=Field(min_length=4,max_length=160);segment:str=Field(min_length=4,max_length=500)
@app.post("/api/experiments")
def create_experiment(body:ExperimentCreate,p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    e=Experiment(merchant_id=p.merchant_id,name=body.name,segment=body.segment,status="draft");db.add(e);db.flush();db.add_all([ExperimentVariant(merchant_id=p.merchant_id,experiment_id=e.id,name="CONTROL — Normal Retry",action_type="retry",allocation_percent=50),ExperimentVariant(merchant_id=p.merchant_id,experiment_id=e.id,name="VARIANT — Payment Link",action_type="recovery_link",allocation_percent=50)]);db.commit();return {"id":e.id,"status":e.status}
@app.get("/api/experiments/{eid}")
def experiment(eid:str,p:Principal=Depends(auth),db:Session=Depends(db_session)):
    if not db.scalar(select(Experiment).where(Experiment.id==eid,Experiment.merchant_id==p.merchant_id)):raise HTTPException(404,"Experiment not found")
    return next(x for x in experiments(p,db)["items"] if x["id"]==eid)
@app.get("/api/audit")
def audit(p:Principal=Depends(auth),db:Session=Depends(db_session)):
    rows=db.scalars(select(AuditLog).where(AuditLog.merchant_id==p.merchant_id).order_by(desc(AuditLog.created_at)).limit(200)).all();return {"items":[{"id":x.id,"timestamp":x.created_at.isoformat(),"event_type":x.event_type,"action_id":x.action_id,"decision_id":x.decision_id,"detail":x.detail,"amount_paise":x.amount_paise} for x in rows]}
@app.get("/api/agent-events")
def events(p:Principal=Depends(auth),db:Session=Depends(db_session)):
    rows=db.scalars(select(AgentEvent).where(AgentEvent.merchant_id==p.merchant_id).order_by(desc(AgentEvent.created_at)).limit(100)).all();return {"items":[{"id":x.id,"stage":x.stage,"title":x.title,"detail":x.detail,"amount_paise":x.amount_paise,"created_at":x.created_at.isoformat()} for x in rows]}

class AssistantQuery(BaseModel):query:str=Field(min_length=2,max_length=500)
@app.post("/api/assistant/query")
def assistant(body:AssistantQuery,p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    q=body.query.lower();m=dashboard(p,db)["metrics"];tools=[]
    if "why" in q or "largest" in q or "risk" in q:
        tools=["get_dashboard_metrics","get_revenue_opportunities","get_risk_details"];r=db.scalars(select(RiskEvent).where(RiskEvent.merchant_id==p.merchant_id).order_by(desc(RiskEvent.affected_revenue_paise)).limit(1)).first()
        if not r:answer="No revenue risk is available yet. Connect Razorpay Test Mode or import merchant payment data from Data Sources; I will only report risks derived from those records."
        else:
            d=db.scalar(select(AgentDecision).where(AgentDecision.risk_event_id==r.id));answer=f"The largest open risk is ₹{r.affected_revenue_paise/100:,.0f} from {r.root_cause.replace('_',' ').title()}. {d.explanation} Deterministic policy returned {d.policy_status}; predicted recovery is {d.predicted_probability*100:.0f}% and expected recovery is ₹{d.expected_recovery_paise/100:,.0f}."
    elif "blocked" in q:tools=["get_policy_result","get_action_status"];answer=f"{m['blocked_actions']} decisions are blocked by deterministic policy. Blocked actions cannot reach execution."
    elif "strategy" in q or "experiment" in q:
        tools=["get_experiment_results","get_strategy_performance"];items=experiments(p,db)["items"]
        answer=(f"{items[0]['winner'] or 'No winner'} has the highest observed recovery rate. Sample sizes and confidence intervals are shown; statistical significance is not claimed." if items else "No experiment results exist yet. Import real payment history and create an experiment before comparing strategies.")
    else:tools=["get_dashboard_metrics","get_action_status"];answer=f"Verified recovered revenue is ₹{m['recovered_revenue_paise']/100:,.0f} across {m['successful_actions']} actions. Revenue at risk is ₹{m['revenue_at_risk_paise']/100:,.0f}."
    answer,mode=narrate(body.query,{"database_answer":answer,"tools_called":tools},answer)
    return {"answer":answer,"tools_called":tools,"mode":mode,"numbers_source":"database"}

class Settings(BaseModel):
    automatic_threshold_paise:int=Field(ge=0,le=100000000);approval_threshold_paise:int=Field(ge=0,le=100000000);blocked_threshold_paise:int=Field(ge=0,le=500000000);max_retries:int=Field(ge=0,le=10);minimum_confidence:float=Field(ge=0,le=1);cooldown_minutes:int=Field(ge=0,le=10080);allowed_actions:list[str]
@app.get("/api/settings")
def get_settings(p:Principal=Depends(auth),db:Session=Depends(db_session)):
    s=db.scalar(select(MerchantPolicy).where(MerchantPolicy.merchant_id==p.merchant_id));c=db.scalar(select(RazorpayConnection).where(RazorpayConnection.merchant_id==p.merchant_id));configured=bool(c and c.connection_status=="connected")
    return {**{x:getattr(s,x) for x in ["automatic_threshold_paise","approval_threshold_paise","blocked_threshold_paise","max_retries","minimum_confidence","cooldown_minutes","allowed_actions"]},"razorpay_configured":configured,"razorpay":{"connected":configured,"key_id_masked":c.key_id_masked if c else None,"webhook_status":c.webhook_status if c else "not_verified","mode":"TEST MODE — NO REAL MONEY" if configured else "SETUP REQUIRED"}}
@app.put("/api/settings")
def update_settings(body:Settings,p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    s=db.scalar(select(MerchantPolicy).where(MerchantPolicy.merchant_id==p.merchant_id))
    for k,v in body.model_dump().items():setattr(s,k,v)
    db.commit();return get_settings(p,db)

class RazorpayConnect(BaseModel):
    key_id:str=Field(min_length=12,max_length=80);key_secret:str=Field(min_length=8,max_length=200);webhook_secret:str=Field(min_length=8,max_length=200)
class SyncRequest(BaseModel):
    days:int=Field(default=30,ge=1,le=365);max_records:int=Field(default=1000,ge=1,le=5000)

def ingestion_run_out(run:DataIngestionRun,include_records:bool=False)->dict:
    file_source=run.source in {"merchant_file","merchant_csv"}
    filename=run.filename or (run.counts or {}).get("filename") or ("legacy-payments.csv" if file_source else None)
    result={"id":run.id,"source":run.source,"status":run.status,"filename":filename,"counts":run.counts or {},"record_count":len(run.records or []),"editable":file_source and run.removed_at is None,"error":run.error,"started_at":run.started_at.isoformat(),"completed_at":run.completed_at.isoformat() if run.completed_at else None}
    if include_records:result["records"]=run.records or []
    return result

def source_out(db:Session,merchant_id:str)->dict:
    backfill_legacy_import_records(db,merchant_id)
    c=db.scalar(select(RazorpayConnection).where(RazorpayConnection.merchant_id==merchant_id));runs=db.scalars(select(DataIngestionRun).where(DataIngestionRun.merchant_id==merchant_id,DataIngestionRun.removed_at.is_(None)).order_by(desc(DataIngestionRun.started_at)).limit(50)).all()
    if c:
        ensure_webhook_token(c);db.commit()
    public=os.getenv("PUBLIC_API_URL","http://localhost:8000").rstrip("/")
    return {
        "razorpay":{"connected":bool(c and c.connection_status=="connected"),"mode":"TEST MODE — NO REAL MONEY" if c and c.connection_status=="connected" else "NOT CONNECTED","key_id_masked":c.key_id_masked if c else None,"webhook_status":c.webhook_status if c else "not_verified","webhook_url":f"{public}/api/webhooks/razorpay/{c.webhook_token}" if c else None,"last_verified_at":c.last_verified_at.isoformat() if c and c.last_verified_at else None,"last_sync_at":c.last_sync_at.isoformat() if c and c.last_sync_at else None,"sync_status":c.sync_status if c else "never","sync_error":c.sync_error if c else None,"imported_orders":c.imported_orders or 0 if c else 0,"imported_payments":c.imported_payments or 0 if c else 0},
        "imports":[ingestion_run_out(x) for x in runs],
        "upload":{"max_bytes":10000000,"max_rows":5000,"formats":["csv","tsv","xlsx","xls","json","pdf"],"required_columns":["external_id","order_id","customer_email","customer_name","amount_paise","status","method","failure_code"],"optional_columns":["currency","customer_phone","payment_type"]},
    }

@app.get("/api/data-sources")
def data_sources(p:Principal=Depends(auth),db:Session=Depends(db_session)):return source_out(db,p.merchant_id)
@app.post("/api/data-sources/razorpay/connect")
def connect_source(body:RazorpayConnect,p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    try:connect_razorpay(db,p.merchant_id,body.key_id,body.key_secret,body.webhook_secret);return source_out(db,p.merchant_id)
    except (ValueError,ProviderError,SecretConfigurationError) as exc:raise HTTPException(422,str(exc))
@app.delete("/api/data-sources/razorpay")
def disconnect_source(p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    disconnect_razorpay(db,p.merchant_id);return source_out(db,p.merchant_id)
@app.post("/api/data-sources/razorpay/sync")
def sync_source(body:SyncRequest,p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    try:run=sync_razorpay(db,p.merchant_id,body.days,body.max_records);return {"run":{"id":run.id,"status":run.status,"counts":run.counts},"data_sources":source_out(db,p.merchant_id)}
    except (ValueError,ProviderError,SecretConfigurationError) as exc:raise HTTPException(422,str(exc))
@app.post("/api/data-sources/import/file")
@app.post("/api/data-sources/import/csv",include_in_schema=False)
async def upload_payment_file(file:UploadFile=File(...),p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    if not file.filename:raise HTTPException(422,"Choose a payment data file")
    try:run=import_payment_file(db,p.merchant_id,file.filename,await file.read());return {"run":{"id":run.id,"status":run.status,"counts":run.counts},"data_sources":source_out(db,p.merchant_id)}
    except ValueError as exc:raise HTTPException(422,str(exc))

class ImportPaymentBody(BaseModel):
    external_id:str=Field(min_length=1,max_length=120)
    order_id:str=Field(min_length=1,max_length=120)
    customer_email:EmailStr
    customer_name:str=Field(min_length=1,max_length=160)
    amount_paise:int=Field(gt=0,le=2_000_000_000)
    status:Literal["captured","authorized","failed"]
    method:str=Field(min_length=1,max_length=32)
    failure_code:str=Field(default="",max_length=80)
    currency:str=Field(default="INR",min_length=3,max_length=3)
    customer_phone:str=Field(default="",max_length=32)
    payment_type:Literal["one_time","recurring"]="one_time"

@app.get("/api/data-sources/imports/{run_id}")
def import_file_detail(run_id:str,p:Principal=Depends(auth),db:Session=Depends(db_session)):
    try:return ingestion_run_out(get_import_run(db,p.merchant_id,run_id),True)
    except LookupError as exc:raise HTTPException(404,str(exc))

@app.post("/api/data-sources/imports/{run_id}/payments")
def create_import_payment(run_id:str,body:ImportPaymentBody,p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    try:return ingestion_run_out(add_import_record(db,p.merchant_id,run_id,body.model_dump()),True)
    except LookupError as exc:raise HTTPException(404,str(exc))
    except ValueError as exc:raise HTTPException(409,str(exc))

@app.put("/api/data-sources/imports/{run_id}/payments/{external_id}")
def edit_import_payment(run_id:str,external_id:str,body:ImportPaymentBody,p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    try:return ingestion_run_out(update_import_record(db,p.merchant_id,run_id,external_id,body.model_dump()),True)
    except LookupError as exc:raise HTTPException(404,str(exc))
    except ValueError as exc:raise HTTPException(409,str(exc))

@app.delete("/api/data-sources/imports/{run_id}/payments/{external_id}")
def delete_import_payment(run_id:str,external_id:str,p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    try:return ingestion_run_out(remove_import_record(db,p.merchant_id,run_id,external_id),True)
    except LookupError as exc:raise HTTPException(404,str(exc))
    except ValueError as exc:raise HTTPException(409,str(exc))

@app.delete("/api/data-sources/imports/{run_id}")
def delete_import_file(run_id:str,p:Principal=Depends(mutation),db:Session=Depends(db_session)):
    try:remove_import_run(db,p.merchant_id,run_id);return {"ok":True,"data_sources":source_out(db,p.merchant_id)}
    except LookupError as exc:raise HTTPException(404,str(exc))
    except ValueError as exc:raise HTTPException(409,str(exc))

@app.post("/api/webhooks/razorpay/{webhook_token}")
async def merchant_webhook(webhook_token:str,request:Request,background:BackgroundTasks,db:Session=Depends(db_session)):
    connection=db.scalar(select(RazorpayConnection).where(RazorpayConnection.webhook_token==webhook_token, RazorpayConnection.connection_status=="connected"))
    if not connection:raise HTTPException(404,"Webhook connection not found")
    raw=await request.body();sig=request.headers.get("X-Razorpay-Signature","");sha=hashlib.sha256(raw).hexdigest()
    try:secret=decrypt_secret(connection.webhook_secret_encrypted)
    except SecretConfigurationError as exc:raise HTTPException(503,str(exc))
    if not secret or not verify_webhook_signature(raw,sig,secret):
        db.add(WebhookEvent(event_id=request.headers.get("X-Razorpay-Event-Id") or f"invalid:{connection.id}:{sha}",event_type="invalid_signature",payload_sha256=sha,signature_valid=False,status="rejected",merchant_id=connection.merchant_id,payload={"body_size":len(raw)}));
        try:db.commit()
        except IntegrityError:db.rollback()
        raise HTTPException(401,"Invalid Razorpay webhook signature")
    try:payload=json.loads(raw)
    except Exception:raise HTTPException(400,"Malformed webhook JSON")
    event_id=request.headers.get("X-Razorpay-Event-Id") or payload.get("id") or sha;existing=db.scalar(select(WebhookEvent).where(WebhookEvent.event_id==event_id))
    if existing:return {"status":"duplicate","event_id":event_id}
    ev=WebhookEvent(event_id=event_id,event_type=payload.get("event","unknown"),payload_sha256=sha,signature_valid=True,status="received",merchant_id=connection.merchant_id,payload=payload);db.add(ev);connection.webhook_status="verified";db.commit()
    try:
        from redis import Redis
        from rq import Queue
        Queue("razorrecover",connection=Redis.from_url(os.getenv("REDIS_URL","redis://localhost:6379/0"))).enqueue(process_webhook,ev.id,job_id=f"webhook:{event_id}")
    except Exception:background.add_task(process_webhook,ev.id)
    return {"status":"accepted","event_id":event_id}

@app.post("/api/webhooks/razorpay")
async def webhook(request:Request,background:BackgroundTasks,db:Session=Depends(db_session)):
    raw=await request.body();sig=request.headers.get("X-Razorpay-Signature","");secret=os.getenv("RAZORPAY_WEBHOOK_SECRET","");sha=hashlib.sha256(raw).hexdigest()
    if not secret or not verify_webhook_signature(raw,sig,secret):
        db.add(WebhookEvent(event_id=request.headers.get("X-Razorpay-Event-Id") or f"invalid:{sha}",event_type="invalid_signature",payload_sha256=sha,signature_valid=False,status="rejected",payload={"body_size":len(raw)}))
        try:db.commit()
        except IntegrityError:db.rollback()
        raise HTTPException(401,"Invalid Razorpay webhook signature")
    try:payload=json.loads(raw)
    except Exception:raise HTTPException(400,"Malformed webhook JSON")
    event_id=request.headers.get("X-Razorpay-Event-Id") or payload.get("id") or sha;existing=db.scalar(select(WebhookEvent).where(WebhookEvent.event_id==event_id))
    if existing:return {"status":"duplicate","event_id":event_id}
    ev=WebhookEvent(event_id=event_id,event_type=payload.get("event","unknown"),payload_sha256=sha,signature_valid=True,status="received",payload=payload);db.add(ev);db.commit()
    try:
        from redis import Redis
        from rq import Queue
        Queue("razorrecover",connection=Redis.from_url(os.getenv("REDIS_URL","redis://localhost:6379/0"))).enqueue(process_webhook,ev.id,job_id=f"webhook:{event_id}")
    except Exception:background.add_task(process_webhook,ev.id)
    return {"status":"accepted","event_id":event_id}

from __future__ import annotations
import hashlib,os,secrets
from dataclasses import dataclass
from datetime import timedelta
from argon2 import PasswordHasher
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import AuthSession, Merchant, MerchantUser, User, utcnow

COOKIE="rr_session"; ph=PasswordHasher(time_cost=2,memory_cost=19456,parallelism=1)
SESSION_TTL_DAYS=max(1,min(int(os.getenv("SESSION_TTL_DAYS","30")),90))
SESSION_MAX_AGE_SECONDS=SESSION_TTL_DAYS*24*60*60
def digest(value:str)->str:return hashlib.sha256(value.encode()).hexdigest()
def hash_password(password:str)->str:return ph.hash(password)
def verify_password(stored:str,password:str)->bool:
    try:return ph.verify(stored,password)
    except Exception:return False
def new_session(db:Session,user_id:str,days:int=SESSION_TTL_DAYS)->tuple[str,str]:
    token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
    db.add(AuthSession(user_id=user_id,token_hash=digest(token),csrf_hash=digest(csrf),expires_at=utcnow()+timedelta(days=days)));db.commit()
    return token,csrf
@dataclass(frozen=True)
class Principal:user_id:str;merchant_id:str;role:str;email:str;name:str
def principal(request:Request,db:Session)->Principal:
    token=request.cookies.get(COOKIE)
    if not token:raise HTTPException(401,"Authentication required")
    row=db.execute(select(AuthSession,User,MerchantUser,Merchant).join(User,AuthSession.user_id==User.id).join(MerchantUser,MerchantUser.user_id==User.id).join(Merchant,Merchant.id==MerchantUser.merchant_id).where(AuthSession.token_hash==digest(token),AuthSession.revoked_at.is_(None),AuthSession.expires_at>utcnow(),User.is_active.is_(True))).first()
    if not row:raise HTTPException(401,"Session expired or invalid")
    _,user,membership,merchant=row
    return Principal(user.id,merchant.id,membership.role,user.email,user.name)
def require_csrf(request:Request,db:Session)->None:
    token=request.cookies.get(COOKIE);csrf=request.headers.get("X-CSRF-Token")
    if not token or not csrf:raise HTTPException(403,"CSRF token required")
    s=db.scalar(select(AuthSession).where(AuthSession.token_hash==digest(token),AuthSession.revoked_at.is_(None)))
    if not s or not secrets.compare_digest(s.csrf_hash,digest(csrf)):raise HTTPException(403,"Invalid CSRF token")

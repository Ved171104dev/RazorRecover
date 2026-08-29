from __future__ import annotations
import os,time
from collections import defaultdict
try:
    from redis import Redis
except Exception: Redis=None
_fallback:dict[str,list[float]]=defaultdict(list)
def allowed(key:str,limit:int=10,window:int=60)->bool:
    if Redis:
        try:
            r=Redis.from_url(os.getenv("REDIS_URL","redis://localhost:6379/0"),socket_timeout=.2)
            n=r.incr(f"rate:{key}"); r.expire(f"rate:{key}",window,nx=True); return int(n)<=limit
        except Exception:pass
    now=time.time();_fallback[key]=[x for x in _fallback[key] if x>now-window]
    if len(_fallback[key])>=limit:return False
    _fallback[key].append(now);return True

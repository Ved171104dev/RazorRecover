from __future__ import annotations
import json,os
import httpx
def narrate(question:str,facts:dict,fallback:str)->tuple[str,str]:
    key=os.getenv("OPENAI_API_KEY");model=os.getenv("OPENAI_MODEL","gpt-5-mini")
    if not key:return fallback,"deterministic_fallback"
    try:
        payload={"model":model,"store":False,"max_output_tokens":320,"instructions":"You are a merchant payment-recovery finance explainer. Answer only about the authenticated merchant's payments, revenue risk, recovery economics, experiments, and safety policies. Use only supplied database facts. Do not invent, change, recalculate, or add financial numbers. Never provide personal investment, trading, tax, lending, or legal advice. Do not authorize or execute actions. Clearly distinguish predicted, observed, incremental, and verified amounts. If facts are insufficient, say so.","input":f"Merchant question: {question}\\nAuthenticated database facts: {json.dumps(facts,separators=(',',':'))}"}
        r=httpx.post("https://api.openai.com/v1/responses",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},json=payload,timeout=12);r.raise_for_status();data=r.json()
        texts=[c.get("text","") for item in data.get("output",[]) if isinstance(item,dict) for c in item.get("content",[]) if isinstance(c,dict) and c.get("type")=="output_text"]
        text="\\n".join(x.strip() for x in texts if isinstance(x,str) and x.strip())
        if not text or len(text)>4000:return fallback,"deterministic_fallback"
        return text,"openai_responses"
    except Exception:return fallback,"deterministic_fallback"

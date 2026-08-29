from __future__ import annotations
import time
import httpx
API="http://127.0.0.1:8000";WEB="http://localhost:3000"
def ok(condition,message):
    if not condition:raise AssertionError(message)
def csrf(client):return {"X-CSRF-Token":client.cookies.get("rr_csrf")}
def main():
    email=f"acceptance{int(time.time())}@example.com";password="Acceptance123"
    with httpx.Client(base_url=API,timeout=60) as c:
        r=c.post("/api/auth/signup",json={"name":"Acceptance Owner","email":email,"password":password,"merchant_name":"Acceptance Merchant"});ok(r.status_code==201,f"signup {r.status_code} {r.text}")
        ok(c.get("/api/auth/me").status_code==200,"session/me")
        before=c.get("/api/dashboard");ok(before.status_code==200,"dashboard");before_money=before.json()["metrics"]["recovered_revenue_paise"]
        risks=c.get("/api/risk/opportunities").json()["items"];ok(len(risks)>0,"seeded risks")
        detail=c.get(f"/api/risk/opportunities/{risks[0]['id']}");ok(detail.status_code==200 and len(detail.json()["decision"]["candidates"])==3,"risk detail/candidates")
        run=c.post("/api/demo/run",headers=csrf(c));ok(run.status_code==200,f"demo {run.status_code} {run.text}")
        after=c.get("/api/dashboard").json()["metrics"]["recovered_revenue_paise"];ok(after>before_money,"verified recovered revenue changed")
        audit=c.get("/api/audit").json()["items"];ok(any(x["event_type"]=="verify" for x in audit),"verify audit")
        experiments=c.get("/api/experiments").json()["items"];ok(experiments and experiments[0]["variants"],"experiment metrics")
        assistant=c.post("/api/assistant/query",headers=csrf(c),json={"query":"Why did you choose this intervention?"});ok(assistant.status_code==200 and assistant.json()["numbers_source"]=="database","grounded assistant")
        first_risk=risks[0]["id"];logout=c.post("/api/auth/logout",headers=csrf(c));ok(logout.status_code==200,"logout");ok(c.get("/api/dashboard").status_code==401,"protected after logout")
        login=c.post("/api/auth/login",json={"email":email,"password":password});ok(login.status_code==200,f"login again {login.text}");ok(c.get("/api/dashboard").json()["metrics"]["recovered_revenue_paise"]==after,"persistent recovery")
    with httpx.Client(base_url=API,timeout=60) as other:
        other_email=f"other{int(time.time())}@example.com";r=other.post("/api/auth/signup",json={"name":"Other Owner","email":other_email,"password":"OtherTenant123","merchant_name":"Other Merchant"});ok(r.status_code==201,"second tenant signup");ok(other.get(f"/api/risk/opportunities/{first_risk}").status_code==404,"tenant isolation")
    with httpx.Client(base_url=WEB,follow_redirects=False,timeout=20) as w:
        for route in ["/","/login","/signup","/forgot-password"]:ok(w.get(route).status_code==200,f"frontend {route}")
        protected=w.get("/dashboard");ok(protected.status_code in {307,308} and "/login" in protected.headers["location"],"frontend protected redirect")
        rendered=w.get("/dashboard",cookies={"rr_session":"acceptance"});ok(rendered.status_code==200 and "RAZORRECOVER" in rendered.text,"built protected route render")
    print({"signup":"passed","login":"passed","dashboard":"passed","risk_detail":"passed","candidates":3,"demo":"passed","recovered_before_paise":before_money,"recovered_after_paise":after,"audit_verify":"passed","experiments":"passed","assistant_database_grounded":"passed","logout_protection":"passed","persistence":"passed","tenant_isolation":"passed","frontend_routes":"passed"})
if __name__=="__main__":main()


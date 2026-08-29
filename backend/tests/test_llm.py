from app.services.llm import narrate
def test_llm_falls_back_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY",raising=False);assert narrate("why",{"amount":100},"safe")[0]=="safe"
def test_llm_malformed_output_cannot_change_answer(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY","test")
    class R:
        def raise_for_status(self):pass
        def json(self):return {"output":[{"content":[{"type":"wrong","text":"fabricated"}]}]}
    monkeypatch.setattr("app.services.llm.httpx.post",lambda *a,**k:R());assert narrate("why",{"amount":100},"safe")==("safe","deterministic_fallback")


import os
from pathlib import Path
TEST_DB=Path(__file__).parent/"test.db"
if TEST_DB.exists():TEST_DB.unlink()
os.environ["DATABASE_URL"]=f"sqlite:///{TEST_DB.as_posix()}"
os.environ["AUTO_CREATE_SCHEMA"]="false"
os.environ["EMBEDDED_WORKER_ENABLED"]="false"
os.environ["AUTH_SECRET"]="test-only-auth-and-encryption-secret-32-chars"
os.environ["PUBLIC_API_URL"]="http://testserver"
from fastapi.testclient import TestClient
import pytest
from app.db import Base,SessionLocal,engine
from app.main import app
from app.services.rate_limit import _fallback
from app.services.seed import create_merchant_account,seed_merchant
Base.metadata.create_all(engine)
with SessionLocal() as db:
    user,merchant=create_merchant_account(db,"Test Owner","owner@example.com","TestPass123","Test Merchant")
    seed_merchant(db,merchant,25,80)
@pytest.fixture
def client():return TestClient(app)
@pytest.fixture
def authed(client):
    _fallback.clear()
    r=client.post("/api/auth/login",json={"email":"owner@example.com","password":"TestPass123"});assert r.status_code==200,r.text
    csrf=client.cookies.get("rr_csrf");client.headers.update({"X-CSRF-Token":csrf});return client

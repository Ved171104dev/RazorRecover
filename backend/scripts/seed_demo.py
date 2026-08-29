from app.db import SessionLocal
from app.services.seed import bootstrap_demo
if __name__=="__main__":
    with SessionLocal() as db:bootstrap_demo(db)

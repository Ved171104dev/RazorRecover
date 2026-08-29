from __future__ import annotations
from pathlib import Path
import joblib,pandas as pd
from app.services.recovery import recovery_probability
class RecoveryModel:
    def __init__(self):
        path=Path(__file__).parents[2]/"artifacts"/"recovery_probability.joblib";self.model=joblib.load(path) if path.exists() else None
    def predict(self,features:dict)->dict:
        if not self.model:return {**recovery_probability(features),"model_version":"deterministic-fallback-v1"}
        row={"amount_paise":features["amount_paise"],"method":features.get("method","unknown"),"failure_code":features.get("failure_code",""),"retry_count":features.get("retry_count",0),"historical_success":features.get("historical_success",0),"device":features.get("device","unknown")}
        probability=float(self.model.predict_proba(pd.DataFrame([row]))[0,1]);fallback=recovery_probability(features);return {**fallback,"recovery_probability":round(probability,3),"model_version":"hist-gradient-boosting-v1"}

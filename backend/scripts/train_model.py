from __future__ import annotations
import json
from pathlib import Path
import sys
import joblib,pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score,precision_score,recall_score,roc_auc_score
from sklearn.model_selection import train_test_split
BACKEND_ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(BACKEND_ROOT))
from app.ml.inference import FEATURE_SCHEMA,feature_vector
ROOT=Path(__file__).parents[2];DATA=ROOT/"data"/"payment_attempts.csv";ART=BACKEND_ROOT/"artifacts"
def main():
    if not DATA.exists():
        from scripts.generate_demo_data import main as generate
        generate()
    df=pd.read_csv(DATA);features=["amount_paise","method","failure_code","retry_count","historical_success","device"];X=df[features].apply(lambda row:feature_vector(row.to_dict())[0],axis=1,result_type="expand");y=df["recovered"]
    train_x,test_x,train_y,test_y=train_test_split(X,y,test_size=.2,random_state=20260828,stratify=y)
    model=LogisticRegression(max_iter=200,random_state=20260828);model.fit(train_x,train_y)
    pred=model.predict(test_x);prob=model.predict_proba(test_x)[:,1]
    metrics={"precision":precision_score(test_y,pred,zero_division=0),"recall":recall_score(test_y,pred,zero_division=0),"f1":f1_score(test_y,pred,zero_division=0),"roc_auc":roc_auc_score(test_y,prob),"test_rows":len(test_y),"seed":20260828}
    ART.mkdir(exist_ok=True);joblib.dump({"feature_schema":FEATURE_SCHEMA,"model_version":"local-logistic-v2","model":model},ART/"recovery_probability.joblib");(ART/"evaluation_metrics.json").write_text(json.dumps(metrics,indent=2));print(json.dumps(metrics,indent=2))
if __name__=="__main__":main()

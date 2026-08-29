from __future__ import annotations
import json
from pathlib import Path
import joblib,pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import f1_score,precision_score,recall_score,roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
ROOT=Path(__file__).parents[2];DATA=ROOT/"data"/"payment_attempts.csv";ART=Path(__file__).parents[1]/"artifacts"
def main():
    if not DATA.exists():
        from scripts.generate_demo_data import main as generate
        generate()
    df=pd.read_csv(DATA);features=["amount_paise","method","failure_code","retry_count","historical_success","device"];X=df[features];y=df["recovered"]
    train_x,test_x,train_y,test_y=train_test_split(X,y,test_size=.2,random_state=20260828,stratify=y)
    prep=ColumnTransformer([("cat",OneHotEncoder(handle_unknown="ignore",sparse_output=False),["method","failure_code","device"])],remainder="passthrough")
    model=Pipeline([("preprocess",prep),("model",HistGradientBoostingClassifier(max_iter=100,random_state=20260828))]);model.fit(train_x,train_y)
    pred=model.predict(test_x);prob=model.predict_proba(test_x)[:,1]
    metrics={"precision":precision_score(test_y,pred,zero_division=0),"recall":recall_score(test_y,pred,zero_division=0),"f1":f1_score(test_y,pred,zero_division=0),"roc_auc":roc_auc_score(test_y,prob),"test_rows":len(test_y),"seed":20260828}
    ART.mkdir(exist_ok=True);joblib.dump(model,ART/"recovery_probability.joblib");(ART/"evaluation_metrics.json").write_text(json.dumps(metrics,indent=2));print(json.dumps(metrics,indent=2))
if __name__=="__main__":main()

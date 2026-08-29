import csv,random
from pathlib import Path
SEED=20260828
def main():
    r=random.Random(SEED);out=Path(__file__).parents[2]/"data"/"payment_attempts.csv";out.parent.mkdir(exist_ok=True)
    with out.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(["attempt_id","customer_id","order_id","amount_paise","method","failure_code","retry_count","historical_success","device","recovered"])
        for i in range(100000):
            method="upi" if r.random()<.58 else "card";fail="UPI_TIMEOUT" if method=="upi" and r.random()<.19 else ("BANK_DECLINED" if r.random()<.08 else "")
            hist=round(r.uniform(.3,.98),2);retry=r.randint(0,2);recovered=int(bool(fail) and r.random()<(.69 if fail=="UPI_TIMEOUT" and hist>.75 else .34))
            w.writerow([f"att_{i:06}",f"cust_{i%15000:05}",f"order_{i%5000:05}",r.randint(99,15000)*100,method,fail,retry,hist,"android" if i%3 else "ios",recovered])
    print(f"wrote 100000 deterministic rows to {out}")
if __name__=="__main__":main()

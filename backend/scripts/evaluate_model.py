import json
from pathlib import Path
def main():
    p=Path(__file__).parents[1]/"artifacts"/"evaluation_metrics.json"
    if not p.exists():raise SystemExit("Run scripts/train_model.py first")
    print(json.dumps(json.loads(p.read_text()),indent=2))
if __name__=="__main__":main()

"""Reproducible, explainable recovery-probability model trained on synthetic labelled events."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split


def build_dataset(n: int = 12000, seed: int = 20260827):
    rng = np.random.default_rng(seed)
    amount = rng.integers(10_000, 1_500_000, n)
    is_upi_timeout = rng.binomial(1, .29, n)
    has_card_history = rng.binomial(1, .58, n)
    retry_count = rng.integers(0, 4, n)
    success_rate = rng.uniform(.25, .98, n)
    android = rng.binomial(1, .66, n)
    hour = rng.integers(0, 24, n)
    logit = -1.25 + 1.45 * is_upi_timeout * has_card_history + .85 * success_rate - .42 * retry_count - .28 * (amount > 900_000) - .22 * android * is_upi_timeout + .12 * (hour < 20)
    probability = 1 / (1 + np.exp(-logit))
    recovered = rng.binomial(1, probability)
    return np.c_[amount / 1_500_000, is_upi_timeout, has_card_history, retry_count / 3, success_rate, android, hour / 23], recovered


def train_and_evaluate(output_dir: Path | None = None) -> dict:
    X, y = build_dataset()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.25, random_state=20260827, stratify=y)
    model = GradientBoostingClassifier(random_state=20260827, n_estimators=80, max_depth=2).fit(X_train, y_train)
    p = model.predict_proba(X_test)[:, 1]; pred = (p >= .5).astype(int)
    metrics = {"precision": round(float(precision_score(y_test, pred)), 4), "recall": round(float(recall_score(y_test, pred)), 4), "f1": round(float(f1_score(y_test, pred)), 4), "roc_auc": round(float(roc_auc_score(y_test, p)), 4), "training_rows": len(X_train), "validation_rows": len(X_test)}
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "evaluation_metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    print(json.dumps(train_and_evaluate(Path("artifacts")), indent=2))

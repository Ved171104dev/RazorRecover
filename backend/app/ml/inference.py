from __future__ import annotations

from pathlib import Path
from time import perf_counter_ns

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

from app.services.recovery import recovery_probability

FEATURE_SCHEMA = "fast-numeric-v2"


def feature_vector(features: dict) -> np.ndarray:
    method = str(features.get("method") or "unknown").lower()
    failure = str(features.get("failure_code") or "").upper()
    return np.asarray([[
        min(float(features.get("amount_paise") or 0) / 2_000_000, 1.0),
        float(method == "upi"),
        float(method == "card"),
        float(method == "netbanking"),
        float(failure == "UPI_TIMEOUT"),
        float(failure == "CARD_EXPIRED"),
        float(failure == "ACCOUNT_BLOCKED"),
        min(float(features.get("retry_count") or 0) / 3, 1.0),
        min(max(float(features.get("historical_success") or 0), 0), 1),
        float(str(features.get("device") or "").lower() == "android"),
    ]], dtype=np.float64)


def bootstrap_model() -> LogisticRegression:
    """Reproducible local model used when a trained artifact is not mounted."""
    rng = np.random.default_rng(20260831)
    matrix = rng.uniform(0, 1, size=(2048, 10))
    logit = -1.15 - .25 * matrix[:, 0] + .35 * matrix[:, 1] + .22 * matrix[:, 2] + 1.25 * matrix[:, 4] - 1.8 * matrix[:, 5] - 2.1 * matrix[:, 6] - .72 * matrix[:, 7] + 1.35 * matrix[:, 8] - .16 * matrix[:, 9]
    probability = 1 / (1 + np.exp(-logit))
    outcomes = rng.binomial(1, probability)
    return LogisticRegression(max_iter=160, random_state=20260831).fit(matrix, outcomes)


class RecoveryModel:
    def __init__(self):
        path = Path(__file__).parents[2] / "artifacts" / "recovery_probability.joblib"
        artifact = joblib.load(path) if path.exists() else None
        if isinstance(artifact, dict) and artifact.get("feature_schema") == FEATURE_SCHEMA and hasattr(artifact.get("model"), "predict_proba"):
            self.model = artifact["model"]
            self.model_version = str(artifact.get("model_version") or "local-logistic-v2")
            self.model_source = "trained_artifact"
        else:
            self.model = bootstrap_model()
            self.model_version = "local-logistic-bootstrap-v2"
            self.model_source = "reproducible_bootstrap"
        self.model.predict_proba(feature_vector({"amount_paise": 10000, "method": "card", "historical_success": .5}))

    def predict(self, features: dict) -> dict:
        started = perf_counter_ns()
        probability = float(self.model.predict_proba(feature_vector(features))[0, 1])
        fallback = recovery_probability(features)
        result = {
            **fallback,
            "recovery_probability": round(min(.95, max(.03, probability)), 3),
            "model_version": self.model_version,
            "model_source": self.model_source,
            "decision_engine": "local_scikit_learn",
        }
        result["inference_latency_ms"] = round((perf_counter_ns() - started) / 1_000_000, 3)
        return result

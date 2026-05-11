"""
Engine 3 — Anomaly Detection
============================

Loads the pre-trained model bundle (produced by notebooks/train_anomaly_model.ipynb)
and exposes a single `score()` method for the FastAPI routers to call.

Designed for backend devs with light AI experience: you instantiate AnomalyEngine
once at FastAPI startup, then call `.score(features)` on every transaction.
The model object is pickled — no training happens at runtime.

Usage:
    from app.engines.anomaly import AnomalyEngine

    # In app/main.py at startup
    anomaly_engine = AnomalyEngine()

    # In a route
    result = anomaly_engine.score({
        "amount_ngn": 1_200_000,
        "hour_of_day": 14,
        "supplier_age_days": 800,
        "bank_account_changed_recently": 1,
        "supplier_prior_disputes_count": 0,
        "price_vs_market_ratio": 1.0,
        "nafdac_license_active": 1,
    })
    # → {"anomaly_score": 78, "verdict": "warn", "flags": [...], ...}
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np

logger = logging.getLogger(__name__)

# Default location relative to the backend directory
DEFAULT_MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "anomaly_model.pkl"


class AnomalyEngine:
    """
    Wraps the pre-trained XGBoost + Isolation Forest bundle.

    The bundle is produced by notebooks/train_anomaly_model.ipynb and contains:
        - xgb_model (primary classifier)
        - iso_forest (fallback)
        - scaler (StandardScaler fitted on training data)
        - feature_columns (canonical feature order)
        - chosen_threshold (probability above which we flag)
        - metrics (AUC, precision, recall — used by /admin/metrics)
        - feature_importance (used by pitch deck)
    """

    # Required feature keys; if any are missing from input, score() will raise
    REQUIRED_FEATURES = {
        "amount_ngn",
        "hour_of_day",
        "supplier_age_days",
        "bank_account_changed_recently",
        "supplier_prior_disputes_count",
        "price_vs_market_ratio",
        "nafdac_license_active",
    }

    def __init__(self, model_path: str | Path | None = None) -> None:
        """
        Load the bundle from disk. Call this ONCE at FastAPI startup,
        not per request.

        Raises FileNotFoundError if the .pkl is missing — typically means
        the dev forgot to run the training notebook.
        """
        path = Path(model_path) if model_path else DEFAULT_MODEL_PATH

        if not path.exists():
            raise FileNotFoundError(
                f"Anomaly model not found at {path}. "
                f"Run notebooks/train_anomaly_model.ipynb first to generate it."
            )

        logger.info("Loading anomaly model bundle from %s", path)
        bundle = joblib.load(path)

        self.xgb_model = bundle["xgb_model"]
        self.iso_forest = bundle["iso_forest"]
        self.scaler = bundle["scaler"]
        self.feature_columns: list[str] = bundle["feature_columns"]
        self.threshold: float = bundle["chosen_threshold"]
        self.metrics: dict[str, Any] = bundle["metrics"]
        self.feature_importance: dict[str, float] = bundle["feature_importance"]
        self.trained_at: str = bundle["trained_at"]
        self.version: str = bundle["version"]

        logger.info(
            "Anomaly engine ready (v%s, AUC=%.3f, threshold=%.3f, trained_at=%s)",
            self.version,
            self.metrics.get("xgb_auc", 0.0),
            self.threshold,
            self.trained_at,
        )

    def score(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        Score a single transaction.

        Args:
            features: dict with the keys in REQUIRED_FEATURES. Missing
                keys raise ValueError. Extra keys are ignored.

        Returns:
            dict with:
                - anomaly_score: int 0-100 (higher = more anomalous)
                - fraud_probability: float 0-1 (raw model output)
                - verdict: "block" | "warn" | "ok"
                - flags: list[str] of human-readable explanations
                - threshold: float (the cut-off used)
                - model_version: str
        """
        # Validate
        missing = self.REQUIRED_FEATURES - set(features.keys())
        if missing:
            raise ValueError(f"Missing required features: {sorted(missing)}")

        # Build feature vector in the canonical order
        try:
            x = np.array(
                [[float(features[col]) for col in self.feature_columns]]
            )
        except (TypeError, ValueError) as e:
            raise ValueError(f"Feature values must be numeric: {e}") from e

        # Predict
        fraud_proba = float(self.xgb_model.predict_proba(x)[0, 1])
        anomaly_score = int(round(fraud_proba * 100))

        # Verdict from threshold
        if fraud_proba >= self.threshold:
            verdict = "block"
        elif fraud_proba >= self.threshold * 0.6:  # warn zone — still suspicious
            verdict = "warn"
        else:
            verdict = "ok"

        # Generate human-readable flags
        flags = self._explain(features, fraud_proba)

        return {
            "anomaly_score": anomaly_score,
            "fraud_probability": round(fraud_proba, 4),
            "verdict": verdict,
            "flags": flags,
            "threshold": round(self.threshold, 4),
            "model_version": self.version,
        }

    def _explain(self, features: dict[str, Any], fraud_proba: float) -> list[str]:
        """
        Produce human-readable flags. We use rule-based explanations rather
        than feature attribution because:
        1. Rules are interpretable to non-ML users (the pitch judges)
        2. They map to documented Nigerian fraud patterns the buyer recognizes
        3. They're cheap to compute (no SHAP overhead)

        Each flag corresponds to a feature pattern; the model picks up these
        same patterns statistically, but the explanations make it concrete.
        """
        flags: list[str] = []

        if int(features.get("bank_account_changed_recently", 0)) == 1:
            flags.append(
                "Supplier bank account changed in last 7 days — classic BEC fraud pattern"
            )

        age = float(features.get("supplier_age_days", 9999))
        if age < 30:
            flags.append(
                f"Supplier registered only {int(age)} days ago — shell-company risk"
            )
        elif age < 90:
            flags.append(
                f"Supplier is new ({int(age)} days old) — limited track record"
            )

        ratio = float(features.get("price_vs_market_ratio", 1.0))
        if ratio < 0.6:
            flags.append(
                f"Price is {int((1 - ratio) * 100)}% below market — too-good-to-be-true pattern"
            )
        elif ratio < 0.8:
            flags.append(
                f"Price is {int((1 - ratio) * 100)}% below market — verify quality"
            )

        disputes = int(features.get("supplier_prior_disputes_count", 0))
        if disputes >= 3:
            flags.append(
                f"{disputes} prior disputes against this supplier — repeat-offender pattern"
            )
        elif disputes >= 1:
            flags.append(f"{disputes} prior dispute(s) on record")

        if int(features.get("nafdac_license_active", 1)) == 0:
            flags.append("Supplier's NAFDAC license is expired or inactive")

        hour = int(features.get("hour_of_day", 12))
        if hour < 6 or hour >= 22:
            flags.append(f"Transaction initiated at {hour:02d}:00 — outside business hours")

        amount = float(features.get("amount_ngn", 0))
        if amount > 10_000_000:
            flags.append(f"Large transaction (₦{amount:,.0f}) — extra scrutiny applied")

        # If the model thinks this is fraud but no rules fired, explain that
        if not flags and fraud_proba >= self.threshold * 0.6:
            flags.append(
                "Model detected an unusual combination of features that does not match "
                "documented patterns — manual review recommended"
            )

        return flags

    def get_metrics(self) -> dict[str, Any]:
        """
        Return the model's training-time metrics for the /admin/metrics endpoint.
        """
        return {
            "version": self.version,
            "trained_at": self.trained_at,
            "threshold": round(self.threshold, 4),
            "metrics": self.metrics,
            "feature_importance": {
                k: round(v, 4) for k, v in self.feature_importance.items()
            },
        }


# Singleton pattern: instantiate at module level so FastAPI workers share
# the same loaded model. If you need per-request isolation, use FastAPI
# dependency injection instead.
_engine: AnomalyEngine | None = None


def get_engine() -> AnomalyEngine:
    """Lazy-loaded singleton accessor."""
    global _engine
    if _engine is None:
        _engine = AnomalyEngine()
    return _engine

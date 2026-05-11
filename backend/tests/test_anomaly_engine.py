"""
Tests for Engine 3 (Anomaly Detection).

Run from the backend/ directory with:
    pytest tests/test_anomaly_engine.py -v

These tests use the ACTUAL pickle file produced by the training notebook,
so you must run notebooks/train_anomaly_model.ipynb before running these
tests. If the .pkl is missing, every test is skipped with a helpful message.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.engines.anomaly import DEFAULT_MODEL_PATH, AnomalyEngine


@pytest.fixture(scope="module")
def engine():
    """Load the anomaly engine once per test module."""
    if not DEFAULT_MODEL_PATH.exists():
        pytest.skip(
            f"Model not found at {DEFAULT_MODEL_PATH}. "
            f"Run notebooks/train_anomaly_model.ipynb first."
        )
    return AnomalyEngine()


# ---- Smoke tests ----

def test_engine_loads(engine):
    assert engine.xgb_model is not None
    assert engine.iso_forest is not None
    assert engine.scaler is not None
    assert 0.0 < engine.threshold < 1.0
    assert len(engine.feature_columns) == 7


def test_metrics_present(engine):
    m = engine.metrics
    assert "xgb_auc" in m
    assert m["xgb_auc"] > 0.85, "AUC suspiciously low — retrain with more data?"
    assert m["xgb_auc"] < 0.99, "AUC suspiciously high — data may be too separable"


# ---- Scoring tests ----

def _legit_features():
    return {
        "amount_ngn": 850_000,
        "hour_of_day": 11,
        "supplier_age_days": 1200,
        "bank_account_changed_recently": 0,
        "supplier_prior_disputes_count": 0,
        "price_vs_market_ratio": 1.05,
        "nafdac_license_active": 1,
    }


def _shell_supplier_features():
    return {
        "amount_ngn": 2_400_000,
        "hour_of_day": 23,
        "supplier_age_days": 12,
        "bank_account_changed_recently": 0,
        "supplier_prior_disputes_count": 0,
        "price_vs_market_ratio": 0.55,
        "nafdac_license_active": 0,
    }


def test_clean_transaction_passes(engine):
    result = engine.score(_legit_features())
    assert result["verdict"] == "ok"
    assert result["anomaly_score"] < 30
    assert result["fraud_probability"] < 0.3


def test_shell_supplier_blocked(engine):
    result = engine.score(_shell_supplier_features())
    assert result["verdict"] == "block"
    assert result["anomaly_score"] >= 70
    assert result["fraud_probability"] >= engine.threshold


def test_score_output_shape(engine):
    result = engine.score(_legit_features())
    expected_keys = {
        "anomaly_score",
        "fraud_probability",
        "verdict",
        "flags",
        "threshold",
        "model_version",
    }
    assert set(result.keys()) == expected_keys
    assert isinstance(result["anomaly_score"], int)
    assert 0 <= result["anomaly_score"] <= 100
    assert isinstance(result["flags"], list)
    assert result["verdict"] in {"ok", "warn", "block"}


def test_flags_are_human_readable(engine):
    result = engine.score(_shell_supplier_features())
    # Shell supplier has 3 strong signals: age, price, NAFDAC
    assert len(result["flags"]) >= 2
    for flag in result["flags"]:
        assert isinstance(flag, str)
        assert len(flag) > 10  # Not empty or trivial


def test_bec_pattern_flag(engine):
    """When bank_account_changed_recently=1, that flag must appear."""
    features = _legit_features()
    features["bank_account_changed_recently"] = 1
    result = engine.score(features)
    flag_text = " ".join(result["flags"]).lower()
    assert "bank" in flag_text or "bec" in flag_text


# ---- Validation tests ----

def test_missing_features_raises(engine):
    incomplete = _legit_features()
    del incomplete["amount_ngn"]
    with pytest.raises(ValueError, match="Missing required features"):
        engine.score(incomplete)


def test_non_numeric_features_raises(engine):
    bad = _legit_features()
    bad["amount_ngn"] = "not a number"
    with pytest.raises(ValueError, match="numeric"):
        engine.score(bad)


def test_extra_features_ignored(engine):
    """Extra keys should not break scoring."""
    features = _legit_features()
    features["random_extra_key"] = "anything"
    features["another_extra"] = 999
    result = engine.score(features)
    assert "verdict" in result


# ---- Performance ----

def test_score_is_fast(engine):
    """Engine 3 should respond in <100ms on a laptop."""
    import time
    features = _legit_features()
    start = time.perf_counter()
    for _ in range(50):
        engine.score(features)
    elapsed_ms = (time.perf_counter() - start) * 1000 / 50
    assert elapsed_ms < 100, f"Scoring took {elapsed_ms:.1f}ms per call (target <100ms)"


def test_get_metrics_for_admin_dashboard(engine):
    m = engine.get_metrics()
    assert "version" in m
    assert "metrics" in m
    assert "feature_importance" in m
    assert m["metrics"]["xgb_auc"] > 0.85

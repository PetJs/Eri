"""
Admin / observability endpoints.

GET /admin/metrics — REAL. Returns Engine 3's training metrics + cache stats.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.engines.anomaly import DEFAULT_MODEL_PATH, AnomalyEngine
from app.integrations import bank, cac, court_records, nafdac

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/metrics",
    summary="Engine + integration metrics",
    description=(
        "Returns Engine 3's training metrics (AUC, precision, recall, feature "
        "importance) and current cache sizes for each integration. Used by "
        "the admin dashboard and useful for the pitch."
    ),
)
async def metrics() -> dict[str, Any]:
    # Engine 3 metrics (loaded from the pickled model bundle)
    anomaly_metrics: dict[str, Any]
    if DEFAULT_MODEL_PATH.exists():
        engine = AnomalyEngine()
        anomaly_metrics = engine.get_metrics()
    else:
        anomaly_metrics = {
            "error": (
                "Model file not found. Run notebooks/train_anomaly_model.ipynb "
                "to generate it."
            )
        }

    # Integration cache snapshots
    cache_sizes = {
        "cac": cac.cache_size(),
        "nafdac": nafdac.cache_size(),
        "court_records": court_records.cache_size(),
        "bank": bank.cache_size(),
    }

    return {
        "anomaly_engine": anomaly_metrics,
        "cache_sizes": cache_sizes,
    }
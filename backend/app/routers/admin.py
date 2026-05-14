"""
Admin / observability endpoints.

GET  /admin/metrics                  — REAL. Returns Engine 3's training metrics + cache stats.
POST /admin/demo/simulate-payment    — Demo helper: flips an order from pending to funded.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.engines.anomaly import DEFAULT_MODEL_PATH, AnomalyEngine
from app.integrations import bank, cac, court_records, nafdac
from app.routers.orders import _ORDERS, _canned_order

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


# -----------------------------------------------------------------------------
# Demo simulation helper
# -----------------------------------------------------------------------------

class SimulatePaymentRequest(BaseModel):
    order_id: str = Field(..., description="ID of an order to mark as funded")


class SimulatePaymentResponse(BaseModel):
    order_id: str
    previous_status: str
    new_status: str
    message: str


@router.post(
    "/demo/simulate-payment",
    response_model=SimulatePaymentResponse,
    summary="Demo helper: simulate Squad webhook for an order",
    description=(
        "Flips an order from `pending_payment` to `funded` instantly. "
        "Use this during the live demo to mimic 'funds landed in the escrow "
        "virtual account' without waiting for a real Squad sandbox webhook. "
        "Hide behind admin auth in production — for the hackathon it's open."
    ),
)
async def simulate_payment(payload: SimulatePaymentRequest) -> SimulatePaymentResponse:
    order = _ORDERS.get(payload.order_id)
    if order is None:
        canned = _canned_order(payload.order_id)
        if canned is None:
            raise HTTPException(
                status_code=404, detail=f"Order {payload.order_id} not found"
            )
        order = dict(canned)
        _ORDERS[payload.order_id] = order

    previous = order["status"]
    if previous not in {"pending_payment", "funded"}:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot simulate payment for order in status '{previous}'. "
                f"Only pending_payment orders can be funded."
            ),
        )

    order["status"] = "funded"
    return SimulatePaymentResponse(
        order_id=payload.order_id,
        previous_status=previous,
        new_status="funded",
        message=(
            f"Order {payload.order_id} marked as funded "
            f"(₦{order['amount_ngn']:,} from buyer)"
        ),
    )
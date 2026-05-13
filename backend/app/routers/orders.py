"""
Orders / escrow endpoints.

**STUB ROUTER.** All routes return mocked data backed by an in-memory dict.
The schemas and behaviors are designed to match what the real Squad-backed
implementation will return, so the frontend can wire up against them now
and the swap is invisible later.

When the Squad integration lands:
  - POST /orders          → real virtual account creation via Squad API
  - GET  /orders/{id}     → real order from DB (no change for the frontend)
  - POST /orders/{id}/release → real Squad Transfer to the supplier
  - POST /orders/{id}/dispute → real freeze + admin notification

For now, all writes mutate the in-memory _ORDERS dict.
"""
from __future__ import annotations

import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.order import (
    CreateOrderRequest,
    DisputeOrderRequest,
    OrderActionResponse,
    OrderResponse,
    OrderStatus,
    ReleaseOrderRequest,
)

router = APIRouter(prefix="/orders", tags=["orders"])

# -----------------------------------------------------------------------------
# In-memory order store
#
# STUB: when Squad integration is wired in, this gets replaced by Postgres
# (probably via SQLModel or SQLAlchemy). Until then, all order state lives
# in process memory and is lost on restart — which is fine for the demo.
# -----------------------------------------------------------------------------

_ORDERS: dict[str, dict[str, Any]] = {}

# Supplier ID → display info, just for stub responses.
# In production this comes from the suppliers table we'd populate from
# /verify/supplier results.
_KNOWN_SUPPLIERS: dict[str, dict[str, str]] = {
    "sup_medtrust": {
        "name": "MedTrust Nigeria Limited",
        "verdict": "green",
        "score": "100",
    },
    "sup_lagospharma": {
        "name": "Lagos Pharma Distributors",
        "verdict": "amber",
        "score": "64",
    },
    "sup_quickmeds": {
        "name": "QuickMeds Wholesale",
        "verdict": "red",
        "score": "15",
    },
    "sup_pharmaplus": {
        "name": "PharmaPlus Solutions Limited",
        "verdict": "green",
        "score": "95",
    },
}


def _generate_id(prefix: str = "ord", length: int = 10) -> str:
    chars = string.ascii_lowercase + string.digits
    return f"{prefix}_{''.join(random.choices(chars, k=length))}"


def _generate_virtual_account() -> str:
    """A 10-digit-looking number for the demo virtual account."""
    return "".join(random.choices(string.digits, k=10))


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------

@router.post(
    "",
    response_model=OrderResponse,
    status_code=201,
    summary="Create an escrow order (STUB)",
    description=(
        "**STUB** — In production, this calls Squad's Virtual Account API to "
        "provision a unique 10-digit NUBAN for the buyer to transfer into. "
        "Currently returns a mock virtual account number and stores the order "
        "in memory."
    ),
)
async def create_order(payload: CreateOrderRequest) -> OrderResponse:
    supplier = _KNOWN_SUPPLIERS.get(payload.supplier_id)
    if supplier is None:
        # For the demo, accept any supplier_id but mark it as unknown
        supplier = {"name": f"Supplier {payload.supplier_id}", "verdict": "amber", "score": "65"}

    order_id = _generate_id("ord")
    now = datetime.now(timezone.utc)

    order_dict = {
        "id": order_id,
        "status": "pending_payment",
        "supplier_id": payload.supplier_id,
        "supplier_name": supplier["name"],
        "amount_ngn": payload.amount_ngn,
        "description": payload.description,
        "created_at": now,
        "expected_delivery_by": now + timedelta(days=payload.expected_delivery_days),
        "virtual_account_number": _generate_virtual_account(),
        "virtual_account_name": "Eri Escrow / Demo Buyer",
        "virtual_account_bank": "Guaranty Trust Bank",
        "trust_score_at_creation": int(supplier["score"]),
        "trust_verdict_at_creation": supplier["verdict"],
    }
    _ORDERS[order_id] = order_dict
    return OrderResponse(**order_dict)


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get an order's current state (STUB)",
    description=(
        "Returns the order including its current escrow status and virtual "
        "account info. Frontend polls this while waiting for payment confirmation."
    ),
)
async def get_order(order_id: str) -> OrderResponse:
    order = _ORDERS.get(order_id)
    if order is None:
        # Demo helper: special IDs return canned orders so the frontend can
        # render specific states without first creating them.
        canned = _canned_order(order_id)
        if canned is None:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        return OrderResponse(**canned)
    return OrderResponse(**order)


@router.post(
    "/{order_id}/release",
    response_model=OrderActionResponse,
    summary="Release escrow to supplier (STUB)",
    description=(
        "**STUB** — In production, this calls Squad's Transfer API to move "
        "funds from the escrow account to the supplier's resolved bank account. "
        "Currently just updates the in-memory order status."
    ),
)
async def release_order(
    order_id: str, payload: ReleaseOrderRequest
) -> OrderActionResponse:
    order = _ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    if order["status"] not in {"funded", "delivered_pending"}:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot release order in status '{order['status']}'",
        )

    order["status"] = "released"
    return OrderActionResponse(
        order_id=order_id,
        new_status="released",
        message=f"Released ₦{order['amount_ngn']:,} to {order['supplier_name']}",
    )


@router.post(
    "/{order_id}/dispute",
    response_model=OrderActionResponse,
    summary="Raise a dispute on an order (STUB)",
    description=(
        "**STUB** — Freezes the escrow and (in production) notifies the admin. "
        "Currently just flips the in-memory status."
    ),
)
async def dispute_order(
    order_id: str, payload: DisputeOrderRequest
) -> OrderActionResponse:
    order = _ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    if order["status"] not in {"funded", "delivered_pending"}:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot dispute order in status '{order['status']}'",
        )

    order["status"] = "disputed"
    return OrderActionResponse(
        order_id=order_id,
        new_status="disputed",
        message=(
            f"Dispute filed (reason: {payload.reason}). "
            f"Funds frozen pending admin review."
        ),
    )


# -----------------------------------------------------------------------------
# Demo helper: canned orders for specific IDs
# -----------------------------------------------------------------------------

def _canned_order(order_id: str) -> dict[str, Any] | None:
    """Return a pre-built order for special demo IDs.

    Useful for the frontend dev to test specific UI states without going
    through the full create-fund-deliver flow.
    """
    base_time = datetime.now(timezone.utc) - timedelta(hours=4)
    canned: dict[str, dict[str, Any]] = {
        "ord_demo_pending": {
            "id": "ord_demo_pending",
            "status": "pending_payment",
            "supplier_id": "sup_medtrust",
            "supplier_name": "MedTrust Nigeria Limited",
            "amount_ngn": 1_250_000,
            "description": "50 cartons of Coartem 20/120 (NAFDAC 04-9412)",
            "created_at": base_time,
            "expected_delivery_by": base_time + timedelta(days=14),
            "virtual_account_number": "9012345678",
            "virtual_account_name": "Eri Escrow / Demo Buyer",
            "virtual_account_bank": "Guaranty Trust Bank",
            "trust_score_at_creation": 100,
            "trust_verdict_at_creation": "green",
        },
        "ord_demo_funded": {
            "id": "ord_demo_funded",
            "status": "funded",
            "supplier_id": "sup_medtrust",
            "supplier_name": "MedTrust Nigeria Limited",
            "amount_ngn": 1_250_000,
            "description": "50 cartons of Coartem 20/120 (NAFDAC 04-9412)",
            "created_at": base_time,
            "expected_delivery_by": base_time + timedelta(days=14),
            "virtual_account_number": "9012345678",
            "virtual_account_name": "Eri Escrow / Demo Buyer",
            "virtual_account_bank": "Guaranty Trust Bank",
            "trust_score_at_creation": 100,
            "trust_verdict_at_creation": "green",
        },
        "ord_demo_disputed": {
            "id": "ord_demo_disputed",
            "status": "disputed",
            "supplier_id": "sup_quickmeds",
            "supplier_name": "QuickMeds Wholesale",
            "amount_ngn": 950_000,
            "description": "Coartem (delivered packaging is suspect)",
            "created_at": base_time,
            "expected_delivery_by": base_time + timedelta(days=14),
            "virtual_account_number": "9012345679",
            "virtual_account_name": "Eri Escrow / Demo Buyer",
            "virtual_account_bank": "Guaranty Trust Bank",
            "trust_score_at_creation": 15,
            "trust_verdict_at_creation": "red",
        },
    }
    return canned.get(order_id)
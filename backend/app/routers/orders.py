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

import logging
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.orders import (
    CreateOrderRequest,
    DisputeOrderRequest,
    OrderActionResponse,
    OrderResponse,
    OrderStatus,
    ReleaseOrderRequest,
)

logger = logging.getLogger(__name__)

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
        "account_number": "0123456789",
        "bank_code": "058",
        "account_name": "MEDTRUST NIGERIA LIMITED",
    },
    "sup_lagospharma": {
        "name": "Lagos Pharma Distributors",
        "verdict": "amber",
        "score": "64",
        "account_number": "3001234567",
        "bank_code": "044",
        "account_name": "OLUMIDE ADEYEMI",
    },
    "sup_quickmeds": {
        "name": "QuickMeds Wholesale",
        "verdict": "red",
        "score": "15",
        "account_number": "9988776655",
        "bank_code": "058",
        "account_name": "AZURITE LOGISTICS NIGERIA",
    },
    "sup_pharmaplus": {
        "name": "PharmaPlus Solutions Limited",
        "verdict": "green",
        "score": "95",
        "account_number": "2105887301",
        "bank_code": "058",
        "account_name": "PHARMAPLUS SOLUTIONS LIMITED",
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
    summary="Create an escrow order with a real Squad virtual NUBAN",
    description=(
        "Provisions a real virtual GTBank account via Squad's Dynamic Virtual "
        "Account API. The buyer transfers the exact order amount to this NUBAN "
        "from their bank app; Squad fires a webhook to `/webhooks/squad` when "
        "funds land, which flips the order from `pending_payment` to `funded`.\n\n"
        "If Squad's DVA pool is empty, the backend auto-refills and retries "
        "before failing. If Squad is unavailable entirely, the route falls "
        "back to a locally-generated account number so the demo continues "
        "(the order status flow still works via `/admin/demo/simulate-payment`)."
    ),
)
async def create_order(payload: CreateOrderRequest) -> OrderResponse:
    supplier = _KNOWN_SUPPLIERS.get(payload.supplier_id)
    if supplier is None:
        # For the demo, accept any supplier_id but mark it as unknown
        supplier = {"name": f"Supplier {payload.supplier_id}", "verdict": "amber", "score": "65"}

    order_id = _generate_id("ord")
    now = datetime.now(timezone.utc)

    # --- Provision a real virtual account via Squad DVA ---
    # The transaction_ref must be unique per Squad call. We use the order_id
    # directly — it's already unique and lets us correlate webhook events
    # back to the order later.
    virtual_account_number: str
    virtual_account_name: str
    virtual_account_bank: str
    squad_transaction_ref: str = order_id

    try:
        from app.integrations.squad import get_squad_client
        squad = get_squad_client()
        if squad is None:
            # No Squad keys configured — fall back to a local mock account.
            # This keeps the demo working even on machines without env vars set.
            logger.warning("Squad client unavailable; using mock virtual account")
            virtual_account_number = _generate_virtual_account()
            virtual_account_name = "Eri Escrow / Demo Buyer"
            virtual_account_bank = "Guaranty Trust Bank"
        else:
            dva = await squad.initiate_dynamic_va(
                amount_kobo=payload.amount_ngn * 100,
                transaction_ref=squad_transaction_ref,
                email=payload.buyer_email,
                duration_seconds=3600 * 24,  # 24-hour window for buyer to pay
            )
            if dva.success and dva.account_number:
                virtual_account_number = dva.account_number
                virtual_account_name = dva.account_name or "Eri Escrow"
                virtual_account_bank = dva.bank or "Guaranty Trust Bank"
                if dva.refilled_pool:
                    logger.info("DVA pool auto-refilled for order %s", order_id)
            else:
                # Squad call failed — fall back to mock so the order still
                # appears on the buyer's screen. Demo continues; the simulate
                # endpoint can still flip the status to funded for stage demos.
                logger.warning(
                    "Squad DVA failed for order %s: %s. Falling back to mock account.",
                    order_id, dva.error,
                )
                virtual_account_number = _generate_virtual_account()
                virtual_account_name = "Eri Escrow / Demo Buyer"
                virtual_account_bank = "Guaranty Trust Bank"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected Squad DVA error for order %s: %s", order_id, exc)
        virtual_account_number = _generate_virtual_account()
        virtual_account_name = "Eri Escrow / Demo Buyer"
        virtual_account_bank = "Guaranty Trust Bank"

    order_dict = {
        "id": order_id,
        "status": "pending_payment",
        "supplier_id": payload.supplier_id,
        "supplier_name": supplier["name"],
        "amount_ngn": payload.amount_ngn,
        "description": payload.description,
        "buyer_email": payload.buyer_email,
        "created_at": now,
        "expected_delivery_by": now + timedelta(days=payload.expected_delivery_days),
        "virtual_account_number": virtual_account_number,
        "virtual_account_name": virtual_account_name,
        "virtual_account_bank": virtual_account_bank,
        "squad_transaction_ref": squad_transaction_ref,
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
    summary="Release escrow to supplier via Squad Transfer API",
    description=(
        "Releases escrow funds to the supplier's resolved bank account using "
        "Squad's Transfer API. In sandbox, the transfer is simulated (no real "
        "money moves) but the API responds with a real transaction reference "
        "and the order is marked released.\n\n"
        "If Squad is unavailable, the route still flips the order to released "
        "but logs the failure — useful for demo continuity."
    ),
)
async def release_order(
    order_id: str, payload: ReleaseOrderRequest
) -> OrderActionResponse:
    order = _ORDERS.get(order_id)
    if order is None:
        # Allow releasing canned demo orders for the live demo
        canned = _canned_order(order_id)
        if canned is None:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        # Promote the canned order into the in-memory store so we can mutate it
        order = dict(canned)
        _ORDERS[order_id] = order

    if order["status"] not in {"funded", "delivered_pending"}:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot release order in status '{order['status']}'",
        )

    # Try to call Squad's Transfer API for real
    transfer_message: str
    try:
        from app.integrations.squad import get_squad_client
        squad = get_squad_client()
        if squad is None:
            transfer_message = (
                f"Released ₦{order['amount_ngn']:,} to {order['supplier_name']} "
                f"(Squad unavailable — recorded locally)"
            )
        else:
            # Look up which account to pay. The order stub doesn't carry this,
            # so we use the supplier's known account from _KNOWN_SUPPLIERS. In
            # production this would come from the supplier's profile.
            supplier_info = _KNOWN_SUPPLIERS.get(order["supplier_id"], {})
            recipient_account = supplier_info.get("account_number", "0123456789")
            recipient_bank = supplier_info.get("bank_code", "058")
            recipient_name = supplier_info.get(
                "account_name", order["supplier_name"]
            )

            transfer = await squad.initiate_transfer(
                amount_kobo=order["amount_ngn"] * 100,
                bank_code=recipient_bank,
                account_number=recipient_account,
                account_name=recipient_name,
                narration=f"Eri escrow release {order_id}",
                remark=payload.confirmation_note or "Escrow released by buyer",
            )

            if transfer.success:
                order["squad_transfer_ref"] = transfer.transaction_ref
                transfer_message = (
                    f"Transferred ₦{order['amount_ngn']:,} to "
                    f"{order['supplier_name']} (Squad ref: {transfer.transaction_ref})"
                )
            else:
                transfer_message = (
                    f"Released ₦{order['amount_ngn']:,} to {order['supplier_name']} "
                    f"(Squad transfer reported: {transfer.error or 'unknown error'})"
                )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Squad release failed: %s", exc)
        transfer_message = (
            f"Released ₦{order['amount_ngn']:,} to {order['supplier_name']} "
            f"(Squad call failed — recorded locally)"
        )

    order["status"] = "released"
    return OrderActionResponse(
        order_id=order_id,
        new_status="released",
        message=transfer_message,
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
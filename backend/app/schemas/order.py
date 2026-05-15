"""
Schemas for the orders / escrow endpoints (Squad-backed).

These are STUB schemas — the routes that use them currently return mock
data. When the Squad integration is wired in, the routes change but
these schemas stay the same.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

OrderStatus = Literal[
    "pending_payment",      # buyer created order, virtual account waiting for funds
    "funded",               # funds landed in escrow
    "delivered_pending",    # supplier marked delivered, awaiting buyer verification
    "released",             # buyer released funds to supplier
    "disputed",             # buyer raised a dispute, funds frozen
    "refunded",             # admin refunded buyer after dispute
    "cancelled",            # buyer cancelled before funding
]


class CreateOrderRequest(BaseModel):
    """Buyer creates an escrow order with a verified supplier."""

    supplier_id: str = Field(..., description="Supplier from a prior /verify/supplier call")
    amount_ngn: int = Field(
        ...,
        gt=0,
        description="Order amount in whole Naira (kobo conversion happens server-side)",
        examples=[1_250_000],
    )
    description: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="What the order is for (used in invoice + delivery verification)",
        examples=["50 cartons of Coartem 20/120 tablets (NAFDAC 04-9412)"],
    )
    buyer_email: EmailStr = Field(
        ...,
        description=(
            "Buyer's email address. Used by Squad for transaction receipts "
            "and dispute communication."
        ),
        examples=["procurement@stmichaelpharmacy.ng"],
    )
    expected_delivery_days: int = Field(
        default=14,
        ge=1,
        le=180,
        description="When buyer expects delivery. After this, escrow auto-releases unless disputed.",
    )


class OrderResponse(BaseModel):
    """An order record — returned by POST /orders and GET /orders/{id}."""

    id: str = Field(..., description="Order ID, e.g. 'ord_abc123'")
    status: OrderStatus
    supplier_id: str
    supplier_name: str
    amount_ngn: int
    description: str
    created_at: datetime
    expected_delivery_by: datetime | None = None

    # Virtual account info — what the buyer transfers to
    virtual_account_number: str | None = Field(
        default=None,
        description="10-digit NUBAN. Buyer transfers from their bank app.",
    )
    virtual_account_name: str | None = Field(
        default=None,
        description="Always 'Eri Escrow / <buyer name>'.",
    )
    virtual_account_bank: str | None = Field(
        default=None,
        examples=["Guaranty Trust Bank"],
    )

    # Trust score snapshot (captured at order creation time)
    trust_score_at_creation: int | None = None
    trust_verdict_at_creation: str | None = None


class ReleaseOrderRequest(BaseModel):
    """Buyer releases escrow to supplier."""

    confirmation_note: str | None = Field(
        default=None,
        description="Optional note from the buyer (e.g. 'Confirmed delivery via WhatsApp')",
    )


class DisputeOrderRequest(BaseModel):
    """Buyer disputes an order, freezing funds for admin review."""

    reason: Literal[
        "product_mismatch",
        "not_delivered",
        "wrong_quantity",
        "damaged",
        "other",
    ] = Field(..., description="Standardized reason code")
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Buyer's account of what went wrong",
    )


class OrderActionResponse(BaseModel):
    """Generic response for state-change actions (release, dispute, cancel)."""

    order_id: str
    new_status: OrderStatus
    message: str
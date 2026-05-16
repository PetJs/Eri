"""
Schemas for the orders / escrow endpoints.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

OrderStatus = Literal[
    "pending_payment",
    "funded",
    "delivered_pending",
    "released",
    "disputed",
    "refunded",
    "cancelled",
]

# ── Invoice extraction models ─────────────────────────────────────────────────

class InvoiceBankAccount(BaseModel):
    bank_name: str | None = None
    account_name: str | None = None
    account_number: str | None = None


class InvoiceSupplier(BaseModel):
    name: str
    rc_number: str | None = None
    nafdac_premises_license: str | None = None
    address: str | None = None
    bank_account: InvoiceBankAccount = Field(default_factory=InvoiceBankAccount)


class InvoiceBuyer(BaseModel):
    name: str | None = None
    rc_number: str | None = None
    address: str | None = None


class InvoiceMetadata(BaseModel):
    invoice_number: str | None = None
    issue_date: str | None = None
    due_date: str | None = None
    payment_terms: str | None = None


class InvoiceLineItem(BaseModel):
    description: str
    nafdac_registration: str | None = None
    manufacturer: str | None = None
    batch_number: str | None = None
    expiry_date: str | None = None
    quantity: float = Field(..., ge=0)
    unit_price: float = Field(..., ge=0)
    line_total: float = Field(..., ge=0)


class InvoiceTotals(BaseModel):
    subtotal: float = Field(..., ge=0)
    discount: float = Field(0.0, ge=0)
    vat: float = Field(0.0, ge=0)
    grand_total: float = Field(..., gt=0)
    currency: str = "NGN"


class ExtractInvoiceResponse(BaseModel):
    supplier: InvoiceSupplier
    buyer: InvoiceBuyer
    invoice_metadata: InvoiceMetadata
    line_items: list[InvoiceLineItem]
    totals: InvoiceTotals
    extraction_confidence: float = Field(..., ge=0.0, le=1.0)
    raw_text_sample: str | None = None


# ── Order creation ────────────────────────────────────────────────────────────

class CreateOrderFromInvoiceRequest(BaseModel):
    """Buyer submits a reviewed invoice draft to create an escrow order."""

    supplier: InvoiceSupplier
    buyer: InvoiceBuyer | None = None
    line_items: list[InvoiceLineItem] = Field(..., min_length=1)
    totals: InvoiceTotals
    buyer_email: EmailStr
    source_document_id: str | None = None
    expected_delivery_days: int = Field(default=14, ge=1, le=180)


# ── Order response ────────────────────────────────────────────────────────────

class OrderResponse(BaseModel):
    """An order record — returned by POST /orders and GET /orders/{id}."""

    id: str
    status: OrderStatus
    supplier_id: str
    supplier_name: str
    amount_ngn: int
    description: str
    created_at: datetime
    expected_delivery_by: datetime | None = None

    virtual_account_number: str | None = None
    virtual_account_name: str | None = None
    virtual_account_bank: str | None = None

    trust_score_at_creation: int | None = None
    trust_verdict_at_creation: str | None = None

    # Multi-line order fields (None for orders created before this schema)
    line_items: list[InvoiceLineItem] | None = None
    verification_status: str | None = None


# ── Order actions ─────────────────────────────────────────────────────────────

class ReleaseOrderRequest(BaseModel):
    confirmation_note: str | None = Field(default=None)


class DisputeOrderRequest(BaseModel):
    reason: Literal[
        "product_mismatch",
        "not_delivered",
        "wrong_quantity",
        "damaged",
        "other",
    ]
    description: str = Field(..., min_length=10, max_length=2000)


class OrderActionResponse(BaseModel):
    order_id: str
    new_status: OrderStatus
    message: str

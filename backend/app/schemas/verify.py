"""
Schemas for the verification endpoints (Engine 1 + Engine 2).

These mirror the dataclasses in app/engines/supplier_trust.py but are
Pydantic models — what FastAPI uses to validate requests, serialize
responses, and generate OpenAPI/Swagger documentation.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Engine 1 — Supplier verification
# -----------------------------------------------------------------------------

SupplierType = Literal["healthcare", "general"]
CheckStatus = Literal["pass", "warn", "fail", "unverified"]
Verdict = Literal["green", "amber", "red"]


class SupplierVerifyRequest(BaseModel):
    """Submitted by the buyer when adding/verifying a supplier."""

    business_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="The supplier's business name as it should appear on CAC",
        examples=["MedTrust Nigeria Limited"],
    )
    rc_number: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description=(
            "CAC registration number. Accepts 'RC 1234567', 'RC-1234567', or "
            "just '1234567'. We normalize on the digits."
        ),
        examples=["1842301"],
    )
    bank_account_number: str = Field(
        ...,
        description="10-digit Nigerian NUBAN account number",
        examples=["0123456789"],
    )
    bank_code: str = Field(
        ...,
        description=(
            "Either the CBN bank code (e.g. '058' for GTBank) or the bank "
            "name (e.g. 'GTBank'). Both work; we resolve internally."
        ),
        examples=["058"],
    )
    supplier_type: SupplierType = Field(
        default="general",
        description=(
            "'healthcare' triggers NAFDAC verification; 'general' skips it."
        ),
    )
    expected_nafdac_number: str | None = Field(
        default=None,
        description=(
            "Healthcare only: the NAFDAC registration number printed on the "
            "supplier's products. Cross-checked against the live Greenbook."
        ),
        examples=["04-9412"],
    )
    expected_manufacturer: str | None = Field(
        default=None,
        description=(
            "Healthcare only: the manufacturer the buyer expects to receive "
            "(e.g. 'Novartis'). Cross-checked against the NAFDAC registration."
        ),
    )
    expected_product: str | None = Field(
        default=None,
        description=(
            "Healthcare only: the product name the buyer expects to receive "
            "(e.g. 'Coartem 20/120')."
        ),
    )


class TrustCheckResult(BaseModel):
    """One row in the verification checklist UI."""

    name: str = Field(..., description="Human-readable label, e.g. 'CAC Registration'")
    status: CheckStatus = Field(..., description="pass / warn / fail / unverified")
    weight: int = Field(
        ...,
        ge=0,
        le=100,
        description="Contribution to the overall score (percent)",
    )
    detail: str = Field(..., description="Short explanation for the UI")
    raw_signals: list[str] = Field(
        default_factory=list,
        description="Bullet-point concerns to surface in the verdict drawer",
    )


class SupplierTrustResponse(BaseModel):
    """Result of /verify/supplier."""

    score: int = Field(..., ge=0, le=100, description="Weighted trust score, 0-100")
    verdict: Verdict = Field(
        ...,
        description=(
            "green (>=80, safe to transact) / amber (50-79, review) / "
            "red (<50, do not transact)"
        ),
    )
    checks: list[TrustCheckResult] = Field(
        ...,
        description="One entry per verification signal, in display order",
    )
    raw_concerns: list[str] = Field(
        default_factory=list,
        description=(
            "Flat list of every specific concern surfaced by all checks. "
            "Use this for the verdict drawer's bullet list."
        ),
    )

    # Diagnostics — useful for the admin dashboard, ignorable by the UI
    duration_ms: int = Field(..., description="Total time the engine took, in ms")
    signals_attempted: int
    signals_succeeded: int


# -----------------------------------------------------------------------------
# Engine 2 — Delivery verification (STUB schema for now)
# -----------------------------------------------------------------------------

class DeliveryVerifyResponse(BaseModel):
    """Result of /verify/delivery/{order_id} — STUB for now."""

    order_id: str
    verdict: Verdict
    match_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="0-1 confidence that the delivered product matches the order",
    )
    delivered_brand: str | None = None
    delivered_dosage: str | None = None
    delivered_nafdac: str | None = None
    differences: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
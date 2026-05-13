"""
Verification endpoints.

POST /verify/supplier            REAL — wraps Engine 1 (Supplier Trust)
POST /verify/delivery/{order_id} STUB — Engine 2 (Product CV) not built yet

When Engine 2 lands, the delivery route gets a real implementation
without changing the response schema.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.engines.supplier_trust import (
    SupplierInput,
    score_supplier,
)
from app.schemas.verify import (
    DeliveryVerifyResponse,
    SupplierTrustResponse,
    SupplierVerifyRequest,
    TrustCheckResult,
)

router = APIRouter(prefix="/verify", tags=["verify"])


# -----------------------------------------------------------------------------
# Supplier verification — REAL implementation via Engine 1
# -----------------------------------------------------------------------------

@router.post(
    "/supplier",
    response_model=SupplierTrustResponse,
    summary="Verify a supplier before transacting",
    description=(
        "Runs the buyer-supplied supplier details through Engine 1, which "
        "checks the company against CAC, the bank account against the buyer's "
        "expected name, the business against Nigerian court records, and (for "
        "healthcare suppliers) the NAFDAC Greenbook. Returns a weighted 0-100 "
        "trust score, a green/amber/red verdict, and the underlying checks "
        "with their individual statuses and concerns.\n\n"
        "The four signals run in parallel; total latency is dominated by the "
        "slowest external call (usually 300-800ms in practice)."
    ),
    responses={
        200: {
            "description": "Verification completed",
            "content": {
                "application/json": {
                    "examples": {
                        "green_supplier": {
                            "summary": "Clean supplier (MedTrust)",
                            "value": {
                                "score": 100,
                                "verdict": "green",
                                "checks": [
                                    {
                                        "name": "CAC Registration",
                                        "status": "pass",
                                        "weight": 25,
                                        "detail": "Registered as 'MEDTRUST NIGERIA LIMITED' — Active",
                                        "raw_signals": [],
                                    },
                                ],
                                "raw_concerns": [],
                                "duration_ms": 312,
                                "signals_attempted": 4,
                                "signals_succeeded": 4,
                            },
                        },
                        "red_supplier": {
                            "summary": "High-risk supplier (the demo gotcha)",
                            "value": {
                                "score": 15,
                                "verdict": "red",
                                "checks": [],
                                "raw_concerns": [
                                    "RC number 9999999 not found in CAC registry",
                                    "3 active fraud-related case(s) against this business",
                                    "NAFDAC manufacturer mismatch",
                                ],
                                "duration_ms": 284,
                                "signals_attempted": 4,
                                "signals_succeeded": 4,
                            },
                        },
                    }
                }
            },
        }
    },
)
async def verify_supplier(payload: SupplierVerifyRequest) -> SupplierTrustResponse:
    # Translate the API schema into Engine 1's internal input type
    engine_input = SupplierInput(
        business_name=payload.business_name,
        rc_number=payload.rc_number,
        bank_account_number=payload.bank_account_number,
        bank_code=payload.bank_code,
        supplier_type=payload.supplier_type,
        expected_nafdac_number=payload.expected_nafdac_number,
        expected_manufacturer=payload.expected_manufacturer,
        expected_product=payload.expected_product,
    )

    trust = await score_supplier(engine_input)

    # Engine 1 returns dataclasses; serialize them as Pydantic models for FastAPI
    return SupplierTrustResponse(
        score=trust.score,
        verdict=trust.verdict,
        checks=[
            TrustCheckResult(
                name=c.name,
                status=c.status,
                weight=c.weight,
                detail=c.detail,
                raw_signals=c.raw_signals,
            )
            for c in trust.checks
        ],
        raw_concerns=trust.raw_concerns,
        duration_ms=trust.duration_ms,
        signals_attempted=trust.signals_attempted,
        signals_succeeded=trust.signals_succeeded,
    )


# -----------------------------------------------------------------------------
# Delivery verification — REAL implementation via Engine 2
# -----------------------------------------------------------------------------

@router.post(
    "/delivery/{order_id}",
    response_model=DeliveryVerifyResponse,
    summary="Verify a delivered product matches the order",
    description=(
        "Runs the buyer's two photos (originally quoted product + what actually "
        "arrived) through Engine 2, which performs:\n\n"
        "1. **OCR** — Tesseract reads the NAFDAC number off the delivered package "
        "(falls back to Gemini vision OCR if Tesseract returns gibberish)\n"
        "2. **NAFDAC cross-check** — verifies the package's number against the "
        "live Greenbook, and checks it matches what was ordered\n"
        "3. **Visual adjudication** — Gemini multimodal compares the two product "
        "photos and looks for brand, dosage, and packaging differences\n\n"
        "Returns a weighted verdict in the same shape as the supplier verification."
    ),
)
async def verify_delivery(
    order_id: str,
    quote_image: UploadFile = File(..., description="Photo of the originally quoted product"),
    delivery_image: UploadFile = File(..., description="Photo of what was actually delivered"),
    expected_nafdac: str | None = Form(default=None),
    expected_manufacturer: str | None = Form(default=None),
    expected_product: str | None = Form(default=None),
) -> DeliveryVerifyResponse:
    if not order_id:
        raise HTTPException(status_code=400, detail="order_id is required")

    quote_bytes = await quote_image.read()
    delivery_bytes = await delivery_image.read()

    if not quote_bytes or not delivery_bytes:
        raise HTTPException(
            status_code=400,
            detail="Both quote_image and delivery_image must be non-empty",
        )

    from app.engines.product_cv import DeliveryInput, verify_delivery as engine_verify_delivery

    verdict = await engine_verify_delivery(DeliveryInput(
        order_id=order_id,
        quote_image_bytes=quote_bytes,
        delivery_image_bytes=delivery_bytes,
        expected_product_name=expected_product,
        expected_manufacturer=expected_manufacturer,
        expected_nafdac_number=expected_nafdac,
    ))

    return DeliveryVerifyResponse(
        order_id=order_id,
        verdict=verdict.verdict,
        match_confidence=verdict.llm_match_confidence or 0.0,
        delivered_brand=verdict.detected_brand,
        delivered_dosage=verdict.detected_dosage,
        delivered_nafdac=verdict.detected_nafdac_number,
        differences=[],  # Embedded in concerns for now
        concerns=verdict.raw_concerns,
    )
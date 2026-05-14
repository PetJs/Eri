"""
Engine 2 — Product CV (Computer Vision)
=======================================

Verifies that a delivered product matches what the buyer expected to receive.
Runs THREE signals in sequence, each refining the previous:

    1. Tesseract OCR (fast, free)
       └─ extracts the registration number printed on the delivered package
       └─ if gibberish, falls back to Gemini vision OCR

    2. NAFDAC Greenbook cross-check
       └─ if the OCR'd number is registered to a different product/manufacturer
          than what the buyer expected, that's the demo gotcha

    3. Gemini multimodal adjudication
       └─ compares the quoted product image vs the delivered image
       └─ "does this look like the same product? brand? dosage? differences?"

Combined into a weighted verdict (0-100 score, green/amber/red), same shape
as Engine 1 — so the frontend renders both with the same components.

For backend devs:
    from app.engines.product_cv import verify_delivery, DeliveryInput

    result = await verify_delivery(DeliveryInput(
        order_id="ord_123",
        quote_image_bytes=quote_jpg,
        delivery_image_bytes=delivery_jpg,
        expected_product_name="Coartem 20/120",
        expected_manufacturer="Novartis",
        expected_nafdac_number="04-9412",
    ))
    # → DeliveryVerdict(score=18, verdict="red", checks=[...], concerns=[...])
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from app.integrations.nafdac import lookup_nafdac
from app.integrations.ocr import extract_registration_number

logger = logging.getLogger(__name__)


CheckStatus = Literal["pass", "warn", "fail", "unverified"]
Verdict = Literal["green", "amber", "red"]


# -----------------------------------------------------------------------------
# Input / output types
# -----------------------------------------------------------------------------

@dataclass
class DeliveryInput:
    """Everything Engine 2 needs to verify a delivery."""

    order_id: str
    quote_image_bytes: bytes
    delivery_image_bytes: bytes
    expected_product_name: str | None = None
    expected_manufacturer: str | None = None
    expected_nafdac_number: str | None = None
    expected_dosage: str | None = None


@dataclass
class DeliveryCheck:
    """One signal's result, mirrors TrustCheck from Engine 1."""

    name: str
    status: CheckStatus
    weight: int
    detail: str
    raw_signals: list[str] = field(default_factory=list)


@dataclass
class DeliveryVerdict:
    """Engine 2's output — same shape as Engine 1's SupplierTrust."""

    score: int            # 0-100
    verdict: Verdict      # green / amber / red
    checks: list[DeliveryCheck]
    raw_concerns: list[str]

    # Information Engine 2 surfaces that the UI shows in the result drawer
    detected_nafdac_number: str | None = None
    detected_brand: str | None = None
    detected_dosage: str | None = None
    nafdac_lookup_result: dict[str, Any] | None = None
    llm_match_confidence: float | None = None

    # Diagnostics
    duration_ms: int = 0
    ocr_source: str = "unknown"  # "tesseract" / "llm" / "failed" / "disabled"


# -----------------------------------------------------------------------------
# Verdict thresholds (same as Engine 1)
# -----------------------------------------------------------------------------

_GREEN_THRESHOLD = 80
_AMBER_THRESHOLD = 50


def _verdict_from_score(score: int) -> Verdict:
    if score >= _GREEN_THRESHOLD:
        return "green"
    if score >= _AMBER_THRESHOLD:
        return "amber"
    return "red"


# -----------------------------------------------------------------------------
# Scoring weights
#
#   NAFDAC cross-check    50%  — strongest signal; packaging says X, Greenbook says Y
#   LLM visual match      40%  — does the quoted product visually equal delivered?
#   OCR detection         10%  — did we successfully read the package?
# -----------------------------------------------------------------------------

_STATUS_MULTIPLIER: dict[CheckStatus, float] = {
    "pass": 1.0,
    "warn": 0.5,
    "fail": 0.0,
    "unverified": 0.0,  # weight redistributes
}


def _compute_score(checks: list[DeliveryCheck]) -> int:
    applicable_weight = 0
    weighted_sum = 0.0
    for c in checks:
        if c.status == "unverified":
            continue
        applicable_weight += c.weight
        weighted_sum += c.weight * _STATUS_MULTIPLIER[c.status]
    if applicable_weight == 0:
        return 0
    return int(round((weighted_sum / applicable_weight) * 100))


# -----------------------------------------------------------------------------
# LLM client — lazy singleton
# -----------------------------------------------------------------------------

_llm_client: Any | None = None


def _get_llm_client() -> Any | None:
    """Return a memoized LLMClient, or None if it can't be constructed.

    The client raises if GEMINI_API_KEY isn't set. We treat that as
    "no LLM available" rather than crashing — Engine 2 can still run
    with Tesseract-only OCR and skip the visual adjudication.
    """
    global _llm_client
    if _llm_client is not None:
        return _llm_client
    try:
        from app.integrations.llm import LLMClient
        _llm_client = LLMClient()
        return _llm_client
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLMClient unavailable (%s); Engine 2 will degrade", exc)
        return None


# -----------------------------------------------------------------------------
# Signal 1: OCR — extract registration number from delivered packaging
# -----------------------------------------------------------------------------

async def _check_ocr(input_: DeliveryInput) -> tuple[DeliveryCheck, str | None, str]:
    """Try to read the NAFDAC number from the delivery image.

    Returns:
        (check_result, detected_number_or_none, ocr_source)
    """
    weight = 10

    llm = _get_llm_client()
    detected, source = await extract_registration_number(
        input_.delivery_image_bytes,
        registry_type="nafdac",
        llm_client=llm,
    )

    if detected is None:
        return (
            DeliveryCheck(
                name="Package OCR",
                status="warn",  # not finding a number isn't proof of fraud
                weight=weight,
                detail="Could not read a registration number from the package",
                raw_signals=[
                    "OCR could not extract a NAFDAC number — verify packaging visible in photo"
                ],
            ),
            None,
            source,
        )

    return (
        DeliveryCheck(
            name="Package OCR",
            status="pass",
            weight=weight,
            detail=f"Detected NAFDAC number: {detected} (via {source})",
        ),
        detected,
        source,
    )


# -----------------------------------------------------------------------------
# Signal 2: NAFDAC cross-check
# -----------------------------------------------------------------------------

async def _check_nafdac(
    input_: DeliveryInput,
    detected_nafdac: str | None,
) -> tuple[DeliveryCheck, dict[str, Any] | None]:
    """Cross-check the detected NAFDAC number against the Greenbook and
    the buyer's expectations.

    This is where the demo gotcha lands:
      - Buyer expected: Coartem from Novartis (NAFDAC 04-9412)
      - Package says:   NAFDAC 04-6433
      - Greenbook says: 04-6433 is Proguanil from GreenLife
      - Mismatch fires: manufacturer, product, AND wrong-number-for-order
    """
    weight = 50

    if detected_nafdac is None and input_.expected_nafdac_number is None:
        # No package number readable AND no expectation set — skip
        return (
            DeliveryCheck(
                name="NAFDAC Cross-check",
                status="unverified",
                weight=weight,
                detail="No NAFDAC number to cross-check",
            ),
            None,
        )

    # If we expected a NAFDAC number and didn't detect one, that's a soft fail
    if detected_nafdac is None:
        return (
            DeliveryCheck(
                name="NAFDAC Cross-check",
                status="fail",
                weight=weight,
                detail=(
                    f"Expected NAFDAC {input_.expected_nafdac_number} on package "
                    f"but could not read one"
                ),
                raw_signals=[
                    f"Buyer expected NAFDAC {input_.expected_nafdac_number} but "
                    f"the delivered package shows no readable registration number"
                ],
            ),
            None,
        )

    # We detected a number — look it up
    record = await lookup_nafdac(detected_nafdac)
    record_dict = {
        "registered": record.registered,
        "nafdac_number": record.nafdac_number,
        "product_name": record.product_name,
        "manufacturer": record.manufacturer,
        "status": record.status,
        "source": record.source,
    }

    # Did the package show a DIFFERENT number than the buyer expected?
    expected = (input_.expected_nafdac_number or "").strip()
    if expected and detected_nafdac.strip() != expected:
        return (
            DeliveryCheck(
                name="NAFDAC Cross-check",
                status="fail",
                weight=weight,
                detail=(
                    f"Package shows NAFDAC {detected_nafdac}; "
                    f"expected {expected}"
                ),
                raw_signals=[
                    f"NAFDAC number on delivered package ({detected_nafdac}) "
                    f"does not match what was ordered ({expected})",
                ] + (
                    [
                        f"Greenbook says {detected_nafdac} is "
                        f"'{record.product_name}' from {record.manufacturer}"
                    ]
                    if record.registered and record.product_name
                    else []
                ),
            ),
            record_dict,
        )

    # Package matches the expected number — but does Greenbook back it up?
    if not record.registered:
        return (
            DeliveryCheck(
                name="NAFDAC Cross-check",
                status="fail",
                weight=weight,
                detail=f"NAFDAC number {detected_nafdac} is not registered",
                raw_signals=[
                    f"NAFDAC has no record of registration {detected_nafdac}"
                ],
            ),
            record_dict,
        )

    # Cross-check what Greenbook says against the buyer's expected manufacturer / product
    valid, issues = record.is_valid_for(
        expected_manufacturer=input_.expected_manufacturer,
        expected_product=input_.expected_product_name,
    )

    if valid:
        return (
            DeliveryCheck(
                name="NAFDAC Cross-check",
                status="pass",
                weight=weight,
                detail=f"Verified: {record.product_name} from {record.manufacturer}",
            ),
            record_dict,
        )

    # Registered, but mismatch — the canonical demo gotcha
    return (
        DeliveryCheck(
            name="NAFDAC Cross-check",
            status="fail",
            weight=weight,
            detail=issues[0] if issues else "NAFDAC record does not match expectation",
            raw_signals=issues,
        ),
        record_dict,
    )


# -----------------------------------------------------------------------------
# Signal 3: LLM visual adjudication
# -----------------------------------------------------------------------------

async def _check_llm_adjudication(
    input_: DeliveryInput,
) -> tuple[DeliveryCheck, dict[str, Any] | None]:
    """Ask Gemini whether the two images depict the same product.

    Returns the check plus the raw adjudication dict (for the UI's
    'detected brand / dosage / differences' panel).
    """
    weight = 40

    llm = _get_llm_client()
    if llm is None:
        return (
            DeliveryCheck(
                name="Visual Adjudication",
                status="unverified",
                weight=weight,
                detail="LLM service unavailable",
            ),
            None,
        )

    expected_details = {
        k: v for k, v in {
            "name": input_.expected_product_name,
            "manufacturer": input_.expected_manufacturer,
            "registration": input_.expected_nafdac_number,
            "dosage": input_.expected_dosage,
        }.items() if v is not None
    }

    try:
        verdict = await asyncio.to_thread(
            llm.adjudicate_products,
            input_.quote_image_bytes,
            input_.delivery_image_bytes,
            expected_details,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM adjudication failed: %s", exc)
        return (
            DeliveryCheck(
                name="Visual Adjudication",
                status="unverified",
                weight=weight,
                detail=f"Visual comparison failed: {exc}",
            ),
            None,
        )

    match = bool(verdict.get("match", False))
    confidence = float(verdict.get("confidence", 0.0))
    differences = verdict.get("differences", []) or []
    concerns = verdict.get("concerns", []) or []

    if match and confidence >= 0.8:
        return (
            DeliveryCheck(
                name="Visual Adjudication",
                status="pass",
                weight=weight,
                detail=(
                    f"Visual match confirmed "
                    f"({int(confidence * 100)}% confidence)"
                ),
            ),
            verdict,
        )

    if match and confidence >= 0.5:
        return (
            DeliveryCheck(
                name="Visual Adjudication",
                status="warn",
                weight=weight,
                detail=(
                    f"Probable match but with concerns "
                    f"({int(confidence * 100)}% confidence)"
                ),
                raw_signals=list(differences) + list(concerns),
            ),
            verdict,
        )

    # No match
    return (
        DeliveryCheck(
            name="Visual Adjudication",
            status="fail",
            weight=weight,
            detail=(
                f"Visual mismatch detected "
                f"({int(confidence * 100)}% confidence)"
            ),
            raw_signals=list(differences) + list(concerns),
        ),
        verdict,
    )


# -----------------------------------------------------------------------------
# Orchestrator
# -----------------------------------------------------------------------------

async def verify_delivery(input_: DeliveryInput) -> DeliveryVerdict:
    """Run all three signals and return a weighted verdict."""
    started = time.perf_counter()

    # Signal 1 — OCR (always runs; informs signal 2)
    ocr_check, detected_nafdac, ocr_source = await _check_ocr(input_)

    # Signals 2 and 3 can run in parallel (LLM call is slow; NAFDAC lookup is fast)
    nafdac_check_task = asyncio.create_task(
        _check_nafdac(input_, detected_nafdac)
    )
    llm_check_task = asyncio.create_task(
        _check_llm_adjudication(input_)
    )

    nafdac_check, nafdac_record = await nafdac_check_task
    llm_check, llm_verdict_dict = await llm_check_task

    checks = [ocr_check, nafdac_check, llm_check]
    score = _compute_score(checks)
    verdict = _verdict_from_score(score)

    raw_concerns: list[str] = []
    for c in checks:
        raw_concerns.extend(c.raw_signals)

    duration_ms = int((time.perf_counter() - started) * 1000)

    return DeliveryVerdict(
        score=score,
        verdict=verdict,
        checks=checks,
        raw_concerns=raw_concerns,
        detected_nafdac_number=detected_nafdac,
        detected_brand=(
            llm_verdict_dict.get("delivered_name") if llm_verdict_dict else None
        ),
        detected_dosage=(
            llm_verdict_dict.get("delivered_variant") if llm_verdict_dict else None
        ),
        nafdac_lookup_result=nafdac_record,
        llm_match_confidence=(
            llm_verdict_dict.get("confidence") if llm_verdict_dict else None
        ),
        duration_ms=duration_ms,
        ocr_source=ocr_source,
    )
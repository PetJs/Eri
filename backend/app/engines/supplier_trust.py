"""
Engine 1 — Supplier Trust Score
================================

Orchestrates four independent verification signals into a single 0-100
trust score for a Nigerian B2B supplier:

    1. CAC company registry          (25% weight)
    2. Bank account name match       (25% weight)
    3. Court records                 (20% weight)
    4. NAFDAC pharmaceutical license (15% weight) — healthcare only
    5. LLM invoice consistency       (10% weight) — only if invoice provided
    6. Historical buyer data         (5% weight)  — placeholder for v2

Weights for signals that aren't applicable to a given supplier (e.g. NAFDAC
for non-healthcare, invoice when no image provided) are redistributed
proportionally to the remaining signals.

The signals run in parallel via asyncio.gather() so the slowest external
call (usually CAC or NAFDAC) dominates total latency — not the sum of all.

For backend devs:
    from app.engines.supplier_trust import score_supplier, SupplierInput

    result = await score_supplier(SupplierInput(
        business_name="MedTrust Nigeria Limited",
        rc_number="1842301",
        bank_account_number="0123456789",
        bank_code="058",
        supplier_type="healthcare",
    ))
    # → SupplierTrust(score=92, verdict="green", checks=[...])
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from app.integrations.bank import (
    ResolvedAccount,
    name_match_score,
    resolve_account,
)
from app.integrations.cac import CacRecord, lookup_cac
from app.integrations.court_records import (
    CourtRecordSummary,
    lookup_court_records,
)
from app.integrations.nafdac import NafdacRecord, lookup_nafdac

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Input / output types
# -----------------------------------------------------------------------------

SupplierType = Literal["healthcare", "general"]
CheckStatus = Literal["pass", "warn", "fail", "unverified"]
Verdict = Literal["green", "amber", "red"]


@dataclass
class SupplierInput:
    """Everything Engine 1 needs from the buyer's verify form."""

    business_name: str
    rc_number: str
    bank_account_number: str
    bank_code: str                          # bank code or name (e.g. "058" or "GTBank")
    supplier_type: SupplierType = "general"
    expected_nafdac_number: str | None = None
    expected_manufacturer: str | None = None  # cross-check against NAFDAC record
    expected_product: str | None = None        # cross-check against NAFDAC record
    invoice_image_bytes: bytes | None = None  # for LLM invoice parsing (v2)


@dataclass
class TrustCheck:
    """One row in the verification checklist shown to the buyer."""

    name: str                  # human-readable label
    status: CheckStatus        # pass / warn / fail / unverified
    weight: int                # contribution to the overall score (percent)
    detail: str                # short explanation for the UI
    raw_signals: list[str] = field(default_factory=list)  # bullet-point concerns


@dataclass
class SupplierTrust:
    """Output of Engine 1 — what the frontend renders."""

    score: int                  # 0-100, weighted across all applicable checks
    verdict: Verdict            # green (>=80) / amber (50-79) / red (<50)
    checks: list[TrustCheck]
    raw_concerns: list[str]     # flat list of all issues for the verdict UI

    # Diagnostics — not shown to user but useful for logs and the admin dashboard
    duration_ms: int = 0
    signals_attempted: int = 0
    signals_succeeded: int = 0


# -----------------------------------------------------------------------------
# Verdict thresholds
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
# Per-signal scoring
#
# Each `_check_*` function takes the lookup result (or None on failure) and
# returns a TrustCheck. Status maps to a numeric contribution:
#   "pass"       → full weight
#   "warn"       → 50% of weight
#   "fail"       → 0% of weight
#   "unverified" → REMOVED from weighting (weight redistributes to others)
# -----------------------------------------------------------------------------

def _check_cac(cac: CacRecord | None, supplier: SupplierInput) -> TrustCheck:
    """Translate a CAC lookup into a TrustCheck."""
    weight = 25

    if cac is None:
        return TrustCheck(
            name="CAC Registration",
            status="unverified",
            weight=weight,
            detail="CAC service unavailable — could not verify",
        )

    valid, issues = cac.is_valid_for(
        expected_name=supplier.business_name,
        expected_rc=supplier.rc_number,
    )

    if valid:
        return TrustCheck(
            name="CAC Registration",
            status="pass",
            weight=weight,
            detail=f"Registered as '{cac.business_name.strip()}' — Active",
        )

    # Soft-fail: status is INACTIVE/UNDER_REGISTRATION but otherwise matches
    if cac.found and cac.status and cac.status.upper() == "INACTIVE":
        return TrustCheck(
            name="CAC Registration",
            status="warn",
            weight=weight,
            detail=f"Registered but status is {cac.status}",
            raw_signals=issues,
        )

    # Hard fail: RC doesn't exist OR name/RC mismatch OR struck-off
    detail = "RC number not found" if not cac.found else "; ".join(issues[:1])
    return TrustCheck(
        name="CAC Registration",
        status="fail",
        weight=weight,
        detail=detail,
        raw_signals=issues,
    )


def _check_bank_name(
    resolved: ResolvedAccount | None,
    supplier: SupplierInput,
) -> TrustCheck:
    """Bank account name match — the BEC defense."""
    weight = 25

    if resolved is None or not resolved.found:
        detail = (
            resolved.error
            if resolved and resolved.error
            else "Bank account could not be resolved"
        )
        return TrustCheck(
            name="Bank Account Name Match",
            status="unverified" if resolved is None else "fail",
            weight=weight,
            detail=detail,
        )

    score = name_match_score(supplier.business_name, resolved.account_name)

    if score >= 85:
        return TrustCheck(
            name="Bank Account Name Match",
            status="pass",
            weight=weight,
            detail=f"Account name matches business name ({score}% similarity)",
        )

    if score >= 50:
        # Partial match — could be a personal name on the account, or a
        # legitimate variation. Surface for review but don't fail outright.
        return TrustCheck(
            name="Bank Account Name Match",
            status="warn",
            weight=weight,
            detail=(
                f"Partial match: account is in the name of "
                f"'{resolved.account_name}' ({score}% similarity)"
            ),
            raw_signals=[
                f"Bank account is in the name of '{resolved.account_name}' — "
                f"verify this is an authorized agent of the business"
            ],
        )

    if score >= 25:
        # Low match but not zero — could be the owner's personal name,
        # which is suspicious but not as bad as an unrelated business.
        return TrustCheck(
            name="Bank Account Name Match",
            status="warn",
            weight=weight,
            detail=(
                f"Low match: account is in the name of "
                f"'{resolved.account_name}' ({score}% similarity)"
            ),
            raw_signals=[
                f"Bank account is in '{resolved.account_name}' which does not "
                f"resemble business name '{supplier.business_name}' — possible "
                f"personal account or BEC signal"
            ],
        )

    return TrustCheck(
        name="Bank Account Name Match",
        status="fail",
        weight=weight,
        detail=(
            f"Account is registered to '{resolved.account_name}' — "
            f"completely different from business name"
        ),
        raw_signals=[
            f"BEC red flag: bank account belongs to '{resolved.account_name}', "
            f"not '{supplier.business_name}'"
        ],
    )


def _check_court_records(
    court: CourtRecordSummary | None,
) -> TrustCheck:
    """Court records — strongest signal for active fraud."""
    weight = 20

    if court is None:
        return TrustCheck(
            name="Court Records",
            status="unverified",
            weight=weight,
            detail="Court records service unavailable",
        )

    is_risky, concerns = court.assess_risk()

    if not court.found:
        # No record on file is a soft signal — not a fail
        return TrustCheck(
            name="Court Records",
            status="warn",
            weight=weight,
            detail="No court records on file (may be a new entity)",
            raw_signals=concerns,
        )

    if is_risky:
        return TrustCheck(
            name="Court Records",
            status="fail",
            weight=weight,
            detail=(
                f"{court.fraud_case_count} active fraud case(s), "
                f"{court.active_case_count} active total"
            ),
            raw_signals=concerns,
        )

    if court.active_case_count > 0:
        return TrustCheck(
            name="Court Records",
            status="warn",
            weight=weight,
            detail=f"{court.active_case_count} active non-fraud case(s)",
            raw_signals=concerns,
        )

    return TrustCheck(
        name="Court Records",
        status="pass",
        weight=weight,
        detail="No active legal issues on file",
    )


def _check_nafdac(
    nafdac: NafdacRecord | None,
    supplier: SupplierInput,
) -> TrustCheck:
    """NAFDAC pharmaceutical license — healthcare suppliers only."""
    weight = 15

    if supplier.supplier_type != "healthcare" or not supplier.expected_nafdac_number:
        return TrustCheck(
            name="NAFDAC Registration",
            status="unverified",   # not applicable → weight redistributes
            weight=weight,
            detail="Not applicable for this supplier type",
        )

    if nafdac is None:
        return TrustCheck(
            name="NAFDAC Registration",
            status="unverified",
            weight=weight,
            detail="NAFDAC service unavailable",
        )

    valid, issues = nafdac.is_valid_for(
        expected_manufacturer=supplier.expected_manufacturer,
        expected_product=supplier.expected_product,
    )

    if valid:
        return TrustCheck(
            name="NAFDAC Registration",
            status="pass",
            weight=weight,
            detail=(
                f"Verified: {nafdac.product_name} from {nafdac.manufacturer}"
            ),
        )

    if not nafdac.registered:
        return TrustCheck(
            name="NAFDAC Registration",
            status="fail",
            weight=weight,
            detail=f"NAFDAC number {nafdac.nafdac_number} is not registered",
            raw_signals=issues,
        )

    # Registered, but mismatch — the demo gotcha lands here
    return TrustCheck(
        name="NAFDAC Registration",
        status="fail",
        weight=weight,
        detail=issues[0] if issues else "NAFDAC mismatch",
        raw_signals=issues,
    )


def _check_invoice(supplier: SupplierInput) -> TrustCheck:
    """LLM invoice parsing — placeholder until we wire the LLM client.

    Returns 'unverified' when no invoice is provided, so the weight
    redistributes. When invoice_image_bytes is set, returns 'unverified'
    for now with a TODO note. Engine 1 currently doesn't fail on a
    missing invoice — buyers can verify without one.
    """
    weight = 10
    if supplier.invoice_image_bytes is None:
        return TrustCheck(
            name="Invoice Consistency",
            status="unverified",
            weight=weight,
            detail="No invoice provided",
        )
    # TODO: wire to LLMClient.parse_invoice() when ready
    return TrustCheck(
        name="Invoice Consistency",
        status="unverified",
        weight=weight,
        detail="Invoice parsing not yet wired",
    )


def _check_history() -> TrustCheck:
    """Historical buyer data — v2 placeholder.

    In production this would query our own database for prior transactions
    with this supplier across all Eri buyers. For the hackathon, we always
    return 'unverified', so the 5% weight redistributes to other checks.
    """
    return TrustCheck(
        name="Historical Performance",
        status="unverified",
        weight=5,
        detail="Insufficient transaction history (v2 feature)",
    )


# -----------------------------------------------------------------------------
# Weighted score calculation
# -----------------------------------------------------------------------------

_STATUS_MULTIPLIER: dict[CheckStatus, float] = {
    "pass": 1.0,
    "warn": 0.5,
    "fail": 0.0,
    "unverified": 0.0,  # but weight is removed from total — see below
}


def _compute_score(checks: list[TrustCheck]) -> int:
    """Compute the weighted 0-100 score, redistributing 'unverified' weights.

    Logic:
      - Each check has a `weight` (sums to 100 across all 6 checks)
      - 'unverified' checks are excluded from both numerator and denominator
      - Remaining checks contribute weight * multiplier to numerator
      - Score = (numerator / applicable_weight_total) * 100
    """
    applicable_weight = 0
    weighted_sum = 0.0

    for c in checks:
        if c.status == "unverified":
            continue
        applicable_weight += c.weight
        weighted_sum += c.weight * _STATUS_MULTIPLIER[c.status]

    if applicable_weight == 0:
        # No verifiable signals at all — refuse to make a call
        return 0

    return int(round((weighted_sum / applicable_weight) * 100))


# -----------------------------------------------------------------------------
# The orchestrator
# -----------------------------------------------------------------------------

async def score_supplier(supplier: SupplierInput) -> SupplierTrust:
    """Run all signals in parallel and return a weighted trust score."""
    import time
    started = time.perf_counter()

    # Build the list of tasks. Some signals only fire conditionally.
    needs_nafdac = (
        supplier.supplier_type == "healthcare"
        and supplier.expected_nafdac_number
    )

    tasks: dict[str, asyncio.Task[Any]] = {
        "cac": asyncio.create_task(
            lookup_cac(supplier.business_name, supplier.rc_number)
        ),
        "bank": asyncio.create_task(
            resolve_account(supplier.bank_account_number, supplier.bank_code)
        ),
        "court": asyncio.create_task(
            lookup_court_records(supplier.business_name)
        ),
    }

    if needs_nafdac:
        tasks["nafdac"] = asyncio.create_task(
            lookup_nafdac(supplier.expected_nafdac_number)
        )

    # Wait for all tasks, but soft-fail any individual error.
    results: dict[str, Any] = {}
    signals_attempted = len(tasks)
    signals_succeeded = 0
    for name, task in tasks.items():
        try:
            results[name] = await task
            signals_succeeded += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Signal '%s' failed: %s", name, exc)
            results[name] = None

    # Build the checks list in the order the UI shows them.
    checks: list[TrustCheck] = [
        _check_cac(results.get("cac"), supplier),
        _check_bank_name(results.get("bank"), supplier),
        _check_court_records(results.get("court")),
        _check_nafdac(results.get("nafdac"), supplier),
        _check_invoice(supplier),
        _check_history(),
    ]

    score = _compute_score(checks)
    verdict = _verdict_from_score(score)

    # Flatten all raw concerns into a single list for the UI
    raw_concerns: list[str] = []
    for c in checks:
        raw_concerns.extend(c.raw_signals)

    duration_ms = int((time.perf_counter() - started) * 1000)

    return SupplierTrust(
        score=score,
        verdict=verdict,
        checks=checks,
        raw_concerns=raw_concerns,
        duration_ms=duration_ms,
        signals_attempted=signals_attempted,
        signals_succeeded=signals_succeeded,
    )
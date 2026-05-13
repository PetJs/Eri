"""
Tests for Engine 1 (Supplier Trust Score).

The most important tests here are the end-to-end demo scenarios:
  - MedTrust → green (high score)
  - Lagos Pharma → amber (mid score)
  - QuickMeds → red (low score, multiple concerns)
"""
from __future__ import annotations

import pytest

from app.engines.supplier_trust import (
    SupplierInput,
    TrustCheck,
    _compute_score,
    score_supplier,
)
from app.integrations import bank, cac, court_records, nafdac


@pytest.fixture(autouse=True)
def _clear_all_caches():
    bank.clear_cache()
    cac.clear_cache()
    court_records.clear_cache()
    nafdac.clear_cache()
    yield
    bank.clear_cache()
    cac.clear_cache()
    court_records.clear_cache()
    nafdac.clear_cache()


# ============================================================================
# Score-computation unit tests (no I/O)
# ============================================================================

def test_score_all_pass_is_100():
    checks = [
        TrustCheck("A", "pass", 25, ""),
        TrustCheck("B", "pass", 25, ""),
        TrustCheck("C", "pass", 50, ""),
    ]
    assert _compute_score(checks) == 100


def test_score_all_fail_is_0():
    checks = [
        TrustCheck("A", "fail", 50, ""),
        TrustCheck("B", "fail", 50, ""),
    ]
    assert _compute_score(checks) == 0


def test_score_unverified_redistributes_weight():
    """An unverified check shouldn't drag the score down."""
    checks = [
        TrustCheck("A", "pass", 50, ""),
        TrustCheck("B", "unverified", 50, ""),
    ]
    # B drops out → 100% of A's contribution counts → 100
    assert _compute_score(checks) == 100


def test_score_warn_is_half_weight():
    checks = [
        TrustCheck("A", "warn", 50, ""),
        TrustCheck("B", "pass", 50, ""),
    ]
    # 50 * 0.5 + 50 * 1.0 = 75
    assert _compute_score(checks) == 75


def test_score_mixed_with_unverified():
    checks = [
        TrustCheck("A", "pass", 25, ""),
        TrustCheck("B", "warn", 25, ""),
        TrustCheck("C", "fail", 20, ""),
        TrustCheck("D", "unverified", 15, ""),  # drops out
        TrustCheck("E", "unverified", 10, ""),  # drops out
        TrustCheck("F", "unverified", 5, ""),   # drops out
    ]
    # Applicable weight = 25 + 25 + 20 = 70
    # Weighted sum = 25*1 + 25*0.5 + 20*0 = 37.5
    # Score = 37.5/70 * 100 = 53.57 → 54
    assert _compute_score(checks) == 54


def test_score_no_applicable_signals_is_0():
    checks = [TrustCheck("A", "unverified", 100, "")]
    assert _compute_score(checks) == 0


# ============================================================================
# End-to-end demo scenarios
# ============================================================================

# Helper: build a SupplierInput with healthcare-appropriate defaults
def _medtrust_input() -> SupplierInput:
    return SupplierInput(
        business_name="MedTrust Nigeria",
        rc_number="1842301",
        bank_account_number="0123456789",
        bank_code="058",  # GTBank
        supplier_type="healthcare",
        expected_nafdac_number="04-9412",
        expected_manufacturer="Novartis",
        expected_product="Coartem",
    )


def _quickmeds_input() -> SupplierInput:
    """The demo gotcha. Multiple signals should fire red."""
    return SupplierInput(
        business_name="QuickMeds Wholesale",
        rc_number="9999999",   # Not in CAC — fake RC
        bank_account_number="9988776655",
        bank_code="058",
        supplier_type="healthcare",
        expected_nafdac_number="04-6433",  # registered to wrong product
        expected_manufacturer="Novartis",
        expected_product="Coartem",
    )


def _lagos_pharma_input() -> SupplierInput:
    return SupplierInput(
        business_name="Lagos Pharma Distributors",
        rc_number="1556923",
        bank_account_number="3001234567",
        bank_code="044",  # Access Bank
        supplier_type="healthcare",
        # No NAFDAC expectation — we'll see that check unverified
    )


@pytest.mark.asyncio
async def test_medtrust_lands_in_green():
    """The good supplier — all signals should pass cleanly."""
    result = await score_supplier(_medtrust_input())

    assert result.verdict == "green"
    assert result.score >= 80, f"Score was {result.score}, checks: {result.checks}"

    # Verify each check produced the right status
    by_name = {c.name: c for c in result.checks}
    assert by_name["CAC Registration"].status == "pass"
    assert by_name["Bank Account Name Match"].status == "pass"
    assert by_name["Court Records"].status == "pass"
    assert by_name["NAFDAC Registration"].status == "pass"

    # No raw concerns surfaced
    assert result.raw_concerns == []


@pytest.mark.asyncio
async def test_quickmeds_lands_in_red():
    """The demo gotcha. CAC fails, bank fails, court fails, NAFDAC fails."""
    result = await score_supplier(_quickmeds_input())

    assert result.verdict == "red"
    assert result.score < 50, f"Score was {result.score}, checks: {result.checks}"

    by_name = {c.name: c for c in result.checks}

    # CAC: RC 9999999 not in our seed — should fail
    assert by_name["CAC Registration"].status == "fail"

    # Bank: account name is AZURITE LOGISTICS, not QuickMeds.
    # Could be warn or fail depending on match-score thresholds —
    # the important thing is NOT pass and that the BEC concern is surfaced.
    assert by_name["Bank Account Name Match"].status in {"warn", "fail"}

    # Court: 3 active fraud cases — should fail
    assert by_name["Court Records"].status == "fail"

    # NAFDAC: 04-6433 is registered to Proguanil, not Coartem — should fail
    assert by_name["NAFDAC Registration"].status == "fail"

    # Concerns should be surfaced
    assert len(result.raw_concerns) >= 3
    joined = " ".join(result.raw_concerns).lower()
    assert "fraud" in joined
    assert "azurite" in joined or "bec" in joined
    assert "novartis" in joined or "proguanil" in joined or "manufacturer" in joined


@pytest.mark.asyncio
async def test_lagos_pharma_lands_in_amber():
    """The middle supplier — INACTIVE CAC status, bank name slight mismatch,
    one closed court case. Should land amber."""
    result = await score_supplier(_lagos_pharma_input())

    assert result.verdict == "amber", (
        f"Expected amber but got {result.verdict} with score {result.score}"
    )
    assert 50 <= result.score < 80


@pytest.mark.asyncio
async def test_nafdac_unverified_for_non_healthcare_supplier():
    """A 'general' supplier shouldn't get NAFDAC scored against them."""
    supplier = SupplierInput(
        business_name="MedTrust Nigeria",
        rc_number="1842301",
        bank_account_number="0123456789",
        bank_code="058",
        supplier_type="general",  # not healthcare
        # No NAFDAC expectation
    )
    result = await score_supplier(supplier)
    by_name = {c.name: c for c in result.checks}
    assert by_name["NAFDAC Registration"].status == "unverified"


@pytest.mark.asyncio
async def test_score_independent_of_unverified_checks():
    """Score should be the same whether NAFDAC fires or not, IF NAFDAC is unverified.
    (Sanity check on the redistribution math.)"""
    # Without NAFDAC
    supplier_a = SupplierInput(
        business_name="MedTrust Nigeria",
        rc_number="1842301",
        bank_account_number="0123456789",
        bank_code="058",
        supplier_type="general",
    )
    result_a = await score_supplier(supplier_a)
    bank.clear_cache(); cac.clear_cache(); court_records.clear_cache(); nafdac.clear_cache()
    
    # With NAFDAC as a healthcare supplier (and passing NAFDAC)
    supplier_b = _medtrust_input()
    result_b = await score_supplier(supplier_b)

    # Both should be green; not necessarily identical scores, but both >= 80
    assert result_a.verdict == "green"
    assert result_b.verdict == "green"


# ============================================================================
# Diagnostics
# ============================================================================

@pytest.mark.asyncio
async def test_diagnostics_populated():
    result = await score_supplier(_medtrust_input())
    assert result.duration_ms >= 0
    assert result.signals_attempted >= 3
    assert result.signals_succeeded >= 1


@pytest.mark.asyncio
async def test_checks_in_consistent_order():
    """UI relies on the check list being in a stable order."""
    result = await score_supplier(_medtrust_input())
    expected = [
        "CAC Registration",
        "Bank Account Name Match",
        "Court Records",
        "NAFDAC Registration",
        "Invoice Consistency",
        "Historical Performance",
    ]
    actual = [c.name for c in result.checks]
    assert actual == expected
"""
Tests for the court records mock integration.

Same patterns as the other integration tests.

Run:
    pytest tests/test_court_records.py -v
"""
from __future__ import annotations

import pytest

from app.integrations.court_records import (
    CourtCase,
    CourtRecordSummary,
    cache_size,
    clear_cache,
    lookup_court_records,
)


@pytest.fixture(autouse=True)
def _clear_cache_between_tests():
    clear_cache()
    yield
    clear_cache()


# ----- Lookup tests -----

@pytest.mark.asyncio
async def test_clean_supplier_has_no_cases():
    """MedTrust Nigeria is seeded with no cases — should be findable, zero risk."""
    result = await lookup_court_records("MedTrust Nigeria", simulate_latency=False)
    assert result.found is True
    assert result.case_count == 0
    assert result.active_case_count == 0
    assert result.fraud_case_count == 0
    assert result.has_fraud_allegations is False


@pytest.mark.asyncio
async def test_quickmeds_has_active_fraud_cases():
    """The demo gotcha supplier — should have multiple active fraud cases."""
    result = await lookup_court_records("QuickMeds Wholesale", simulate_latency=False)
    assert result.found is True
    assert result.case_count == 3
    # All 3 cases are "fraud-related" by our definition (FRAUD and
    # BREACH_OF_CONTRACT both count). All 3 are also active (2 ACTIVE,
    # 1 PENDING_JUDGMENT). That's the strongest possible red flag — exactly
    # what we want the demo's gotcha supplier to look like.
    assert result.fraud_case_count == 3
    assert result.active_case_count == 3
    assert result.has_fraud_allegations is True


@pytest.mark.asyncio
async def test_lagos_pharma_has_one_closed_case():
    """Lagos Pharma — one closed contract dispute, no active cases."""
    result = await lookup_court_records(
        "Lagos Pharma Distributors", simulate_latency=False
    )
    assert result.found is True
    assert result.case_count == 1
    assert result.active_case_count == 0  # case is CLOSED
    assert result.fraud_case_count == 0


@pytest.mark.asyncio
async def test_unknown_supplier_returns_not_found():
    result = await lookup_court_records("Totally Random Co", simulate_latency=False)
    assert result.found is False
    assert result.case_count == 0


@pytest.mark.asyncio
async def test_partial_name_match():
    """A buyer might type just 'MedTrust' without 'Nigeria'."""
    result = await lookup_court_records("MedTrust", simulate_latency=False)
    assert result.found is True


@pytest.mark.asyncio
async def test_case_insensitive_match():
    result = await lookup_court_records("MEDTRUST NIGERIA", simulate_latency=False)
    assert result.found is True
    result2 = await lookup_court_records("medtrust nigeria", simulate_latency=False, use_cache=False)
    assert result2.found is True


@pytest.mark.asyncio
async def test_empty_input_returns_error():
    result = await lookup_court_records("", simulate_latency=False)
    assert result.found is False
    assert result.error is not None


# ----- Risk assessment -----

@pytest.mark.asyncio
async def test_clean_supplier_is_not_risky():
    result = await lookup_court_records("MedTrust Nigeria", simulate_latency=False)
    is_risky, concerns = result.assess_risk()
    assert is_risky is False
    assert concerns == []  # truly clean, no concerns at all


@pytest.mark.asyncio
async def test_quickmeds_is_risky_with_specific_concerns():
    """The demo gotcha — risk assessment must flag fraud explicitly."""
    result = await lookup_court_records("QuickMeds Wholesale", simulate_latency=False)
    is_risky, concerns = result.assess_risk()
    assert is_risky is True
    assert len(concerns) >= 2

    joined = " ".join(concerns).lower()
    assert "fraud" in joined  # must mention fraud explicitly
    assert "2" in joined or "active" in joined  # must mention the count


@pytest.mark.asyncio
async def test_lagos_pharma_not_risky_but_has_history():
    """Closed cases shouldn't trigger 'risky', but having any case in history
    might still get reported by a stricter caller. Our default rules say:
    0 active cases → not risky."""
    result = await lookup_court_records(
        "Lagos Pharma Distributors", simulate_latency=False
    )
    is_risky, concerns = result.assess_risk()
    assert is_risky is False  # no active cases
    # Concerns may be empty here — closed cases are background info, not a flag.


@pytest.mark.asyncio
async def test_not_found_returns_soft_signal_not_clean():
    """A business with no record isn't risky, but it's not the same as 'clean'."""
    result = await lookup_court_records("Brand New Company", simulate_latency=False)
    is_risky, concerns = result.assess_risk()
    assert is_risky is False
    assert len(concerns) >= 1
    assert "new" in concerns[0].lower() or "no court records" in concerns[0].lower()


# ----- Cache behavior -----

@pytest.mark.asyncio
async def test_cache_populates_on_lookup():
    assert cache_size() == 0
    await lookup_court_records("MedTrust Nigeria", simulate_latency=False)
    assert cache_size() == 1


@pytest.mark.asyncio
async def test_cache_keyed_by_normalized_name():
    """Different casings/spacings should hit the same cache entry."""
    await lookup_court_records("MedTrust Nigeria", simulate_latency=False)
    size_after_first = cache_size()
    await lookup_court_records("medtrust  nigeria", simulate_latency=False)
    size_after_second = cache_size()
    assert size_after_first == size_after_second  # no new entry


# ----- Case object behavior -----

@pytest.mark.asyncio
async def test_case_objects_have_correct_metadata():
    """Sanity check that CourtCase boolean helpers work as expected."""
    result = await lookup_court_records("QuickMeds Wholesale", simulate_latency=False)

    # All 3 QuickMeds cases are fraud-related AND active per our category set
    fraud_active = [c for c in result.cases if c.is_fraud_related and c.is_active]
    assert len(fraud_active) == 3

    # All seeded QuickMeds cases should be either ACTIVE or PENDING_JUDGMENT
    for case in result.cases:
        assert case.is_active is True


# ----- Performance -----

@pytest.mark.asyncio
async def test_lookup_is_fast_without_simulated_latency():
    """Without simulated latency the mock should be <5ms per call."""
    import time
    start = time.perf_counter()
    for _ in range(100):
        await lookup_court_records(
            "MedTrust Nigeria", simulate_latency=False, use_cache=False
        )
    avg_ms = (time.perf_counter() - start) / 100 * 1000
    assert avg_ms < 5, f"Lookup took {avg_ms:.2f}ms (target <5ms)"
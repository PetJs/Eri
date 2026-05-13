"""
Tests for the NAFDAC Greenbook integration.

These tests focus on the seeded fallback path and the cross-check logic
that powers the demo gotcha. The live API path is exercised in integration
tests (test_nafdac_integration.py) that run against the real NAFDAC site
when network access is available.

Run from backend/:
    pytest tests/test_nafdac.py -v
"""
from __future__ import annotations

import asyncio

import pytest

from app.integrations.nafdac import (
    NafdacRecord,
    cache_size,
    clear_cache,
    lookup_nafdac,
)


@pytest.fixture(autouse=True)
def _clear_cache_between_tests():
    """Ensure cache state doesn't leak between tests."""
    clear_cache()
    yield
    clear_cache()


# ----- Seed lookup tests -----

@pytest.mark.asyncio
async def test_seed_returns_known_product():
    """The seeded Accu-Chek entry should be findable by NAFDAC number."""
    result = await lookup_nafdac("03-6514", prefer_live=False)
    assert result.registered is True
    assert "Accu-Chek" in result.product_name
    assert result.manufacturer == "Roche Products Limited"
    assert result.status == "Active"
    assert result.source == "seed"


@pytest.mark.asyncio
async def test_seed_returns_not_registered_for_unknown():
    """An unknown NAFDAC number should return registered=False, not crash."""
    result = await lookup_nafdac("99-9999", prefer_live=False)
    assert result.registered is False
    assert result.nafdac_number == "99-9999"


@pytest.mark.asyncio
async def test_seed_trims_whitespace():
    """Leading/trailing whitespace shouldn't break lookups."""
    result = await lookup_nafdac("  03-6514  ", prefer_live=False)
    assert result.registered is True


@pytest.mark.asyncio
async def test_empty_input_returns_error():
    result = await lookup_nafdac("", prefer_live=False)
    assert result.registered is False
    assert result.error is not None


# ----- The demo gotcha: cross-check logic -----

@pytest.mark.asyncio
async def test_fake_04_6433_is_registered_but_to_wrong_product():
    """The killer demo case.

    NAFDAC 04-6433 is seeded as 'Proguanil from GreenLife Pharmaceuticals'.
    A buyer expecting Coartem from Novartis must see a mismatch flag,
    not a 'not registered' message.
    """
    result = await lookup_nafdac("04-6433", prefer_live=False)
    assert result.registered is True

    # Buyer thinks they're getting Coartem from Novartis
    is_valid, issues = result.is_valid_for(
        expected_manufacturer="Novartis",
        expected_product="Coartem",
    )
    assert is_valid is False
    assert len(issues) >= 2  # both manufacturer AND product mismatch

    # Check the issue messages are useful for the verdict UI
    joined = " ".join(issues).lower()
    assert "manufacturer" in joined
    assert "novartis" in joined
    assert "greenlife" in joined.lower() or "proguanil" in joined.lower()


@pytest.mark.asyncio
async def test_real_match_passes_cross_check():
    """If buyer expectations match the NAFDAC record, no issues raised."""
    result = await lookup_nafdac("04-6433", prefer_live=False)
    is_valid, issues = result.is_valid_for(
        expected_manufacturer="GreenLife Pharmaceuticals",
        expected_product="Proguanil",
    )
    assert is_valid is True
    assert issues == []


@pytest.mark.asyncio
async def test_cross_check_handles_fuzzy_product_names():
    """'Coartem' should fuzzy-match 'Coartem 20/120 mg tablets' (containment-based).

    The record is Inactive, so is_valid is False — but the only issue should be
    the status flag, not a product mismatch. This verifies the containment logic.
    """
    result = await lookup_nafdac("04-3275", prefer_live=False)
    _, issues = result.is_valid_for(
        expected_manufacturer="Novartis",
        expected_product="Coartem",
    )
    assert not any("product mismatch" in i.lower() for i in issues)
    assert not any("manufacturer mismatch" in i.lower() for i in issues)


@pytest.mark.asyncio
async def test_cross_check_without_expectations_just_checks_active():
    """If buyer provides no expectations, only the Active status matters."""
    result = await lookup_nafdac("03-6514", prefer_live=False)
    is_valid, issues = result.is_valid_for()
    assert is_valid is True


@pytest.mark.asyncio
async def test_cross_check_on_unregistered_number():
    """An unregistered NAFDAC number must always fail cross-check."""
    result = await lookup_nafdac("99-9999", prefer_live=False)
    is_valid, issues = result.is_valid_for(expected_manufacturer="Anyone")
    assert is_valid is False
    assert any("not registered" in i.lower() for i in issues)


# ----- Cache behavior -----

@pytest.mark.asyncio
async def test_cache_populates_on_lookup():
    assert cache_size() == 0
    await lookup_nafdac("03-6514", prefer_live=False)
    assert cache_size() == 1


@pytest.mark.asyncio
async def test_cache_hit_returns_cached_source():
    """A second lookup should return source='cache'."""
    await lookup_nafdac("03-6514", prefer_live=False)
    second = await lookup_nafdac("03-6514", prefer_live=False)
    assert second.source == "cache"
    assert second.registered is True


@pytest.mark.asyncio
async def test_cache_can_be_bypassed():
    """use_cache=False forces a fresh lookup."""
    await lookup_nafdac("03-6514", prefer_live=False)
    fresh = await lookup_nafdac("03-6514", prefer_live=False, use_cache=False)
    assert fresh.source == "seed"  # not "cache"


# ----- Performance sanity check -----

@pytest.mark.asyncio
async def test_seed_lookup_is_fast():
    """Seed lookups should be under 5ms (no network)."""
    import time
    start = time.perf_counter()
    for _ in range(100):
        await lookup_nafdac("03-6514", prefer_live=False, use_cache=False)
    avg_ms = (time.perf_counter() - start) / 100 * 1000
    assert avg_ms < 5, f"Seed lookup took {avg_ms:.2f}ms (target <5ms)"
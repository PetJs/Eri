"""
Tests for the CAC integration.

Focus on the seeded fallback path and the cross-check logic. The live API
path is exercised in scripts/test_cac_live.py against the real CAC site.

Run from backend/:
    pytest tests/test_cac.py -v
"""
from __future__ import annotations

import pytest

from app.integrations.cac import (
    CacRecord,
    cache_size,
    clear_cache,
    lookup_cac,
    _names_match,
    _normalize_rc,
)


@pytest.fixture(autouse=True)
def _clear_cache_between_tests():
    clear_cache()
    yield
    clear_cache()


# ----- Normalizer tests -----

def test_normalize_rc_strips_prefix():
    assert _normalize_rc("RC 395010") == "395010"
    assert _normalize_rc("RC-395010") == "395010"
    assert _normalize_rc("rc395010") == "395010"
    assert _normalize_rc("BN 1234567") == "1234567"


def test_normalize_rc_strips_whitespace():
    assert _normalize_rc("  395010  ") == "395010"
    assert _normalize_rc("395 010") == "395010"


def test_names_match_handles_whitespace():
    assert _names_match(
        "MTN NIGERIA COMMUNICATIONS PLC",
        "MTN NIGERIA COMMUNICATIONS PLC          ",  # CAC's dirty data
    )


def test_names_match_handles_partial_names():
    assert _names_match(
        "MTN Nigeria Communications",
        "MTN NIGERIA COMMUNICATIONS PLC",
    )


def test_names_match_case_insensitive():
    assert _names_match("MedTrust Nigeria", "MEDTRUST NIGERIA LIMITED")


def test_names_match_rejects_unrelated():
    assert not _names_match("MedTrust Nigeria", "QuickMeds Wholesale")
    assert not _names_match("MTN Nigeria", "Cadbury Nigeria")


# ----- Seed lookup tests -----

@pytest.mark.asyncio
async def test_seed_returns_known_supplier():
    """MedTrust Nigeria should be findable by its seeded RC."""
    result = await lookup_cac(
        business_name="MedTrust Nigeria Limited",
        rc_number="1842301",
        prefer_live=False,
    )
    assert result.found is True
    assert "MEDTRUST" in result.business_name
    assert result.rc_number == "1842301"
    assert result.status == "ACTIVE"
    assert result.source == "seed"


@pytest.mark.asyncio
async def test_seed_returns_not_found_for_unknown_rc():
    result = await lookup_cac(
        business_name="Some Random Company",
        rc_number="9999999",
        prefer_live=False,
    )
    assert result.found is False


@pytest.mark.asyncio
async def test_seed_handles_rc_prefix_format():
    """Buyer might type 'RC 1842301' or just '1842301'."""
    result1 = await lookup_cac(
        business_name="MedTrust",
        rc_number="RC 1842301",
        prefer_live=False,
    )
    result2 = await lookup_cac(
        business_name="MedTrust",
        rc_number="1842301",
        prefer_live=False,
        use_cache=False,
    )
    assert result1.found is True
    assert result2.found is True
    assert result1.rc_number == result2.rc_number


@pytest.mark.asyncio
async def test_empty_inputs_return_error():
    result = await lookup_cac("", "1234567", prefer_live=False)
    assert result.found is False
    assert "required" in (result.error or "").lower()

    result = await lookup_cac("Company Name", "", prefer_live=False)
    assert result.found is False


# ----- Cross-check logic (the BEC verification scenario) -----

@pytest.mark.asyncio
async def test_cross_check_passes_for_valid_supplier():
    """MedTrust with matching name + RC + Active status = clean pass."""
    result = await lookup_cac(
        business_name="MedTrust Nigeria",
        rc_number="1842301",
        prefer_live=False,
    )
    valid, issues = result.is_valid_for(
        expected_name="MedTrust Nigeria Limited",
        expected_rc="1842301",
    )
    assert valid is True
    assert issues == []


@pytest.mark.asyncio
async def test_cross_check_flags_rc_mismatch():
    """RC 1842301 belongs to MedTrust. If buyer claims it's their other supplier, flag it."""
    result = await lookup_cac(
        business_name="MedTrust Nigeria",
        rc_number="1842301",
        prefer_live=False,
    )
    valid, issues = result.is_valid_for(
        expected_name="MedTrust Nigeria",
        expected_rc="9999999",  # buyer claims a different RC
    )
    assert valid is False
    assert any("rc number mismatch" in i.lower() for i in issues)


@pytest.mark.asyncio
async def test_cross_check_flags_name_mismatch():
    """If buyer enters MedTrust's RC but claims a different business name."""
    result = await lookup_cac(
        business_name="MedTrust",
        rc_number="1842301",
        prefer_live=False,
    )
    valid, issues = result.is_valid_for(
        expected_name="Totally Different Company Ltd",
        expected_rc="1842301",
    )
    assert valid is False
    assert any("business name mismatch" in i.lower() for i in issues)


@pytest.mark.asyncio
async def test_cross_check_flags_inactive_status():
    """Lagos Pharma is seeded as INACTIVE — caution flag."""
    result = await lookup_cac(
        business_name="Lagos Pharma Distributors",
        rc_number="1556923",
        prefer_live=False,
    )
    valid, issues = result.is_valid_for(
        expected_name="Lagos Pharma Distributors",
        expected_rc="1556923",
    )
    assert valid is False  # status alone fails the verdict
    assert any("inactive" in i.lower() for i in issues)


@pytest.mark.asyncio
async def test_cross_check_handles_not_found():
    """Unregistered RC: every cross-check should fail clearly."""
    result = await lookup_cac(
        business_name="Ghost Co",
        rc_number="0000001",
        prefer_live=False,
    )
    valid, issues = result.is_valid_for(
        expected_name="Ghost Co",
        expected_rc="0000001",
    )
    assert valid is False
    assert any("not found" in i.lower() for i in issues)


# ----- Cache behavior -----

@pytest.mark.asyncio
async def test_cache_populates_on_lookup():
    assert cache_size() == 0
    await lookup_cac("MedTrust", "1842301", prefer_live=False)
    assert cache_size() == 1


@pytest.mark.asyncio
async def test_cache_hit_returns_cached_source():
    await lookup_cac("MedTrust", "1842301", prefer_live=False)
    second = await lookup_cac("MedTrust", "1842301", prefer_live=False)
    assert second.source == "cache"
    assert second.found is True


@pytest.mark.asyncio
async def test_cache_keyed_by_rc_not_name():
    """Two different names with the same RC should hit the same cache key."""
    await lookup_cac("MedTrust Nigeria", "1842301", prefer_live=False)
    second = await lookup_cac("MEDTRUST", "1842301", prefer_live=False)
    assert second.source == "cache"


# ----- Performance -----

@pytest.mark.asyncio
async def test_seed_lookup_is_fast():
    """Should complete under 5ms (no network)."""
    import time
    start = time.perf_counter()
    for _ in range(100):
        await lookup_cac("MedTrust", "1842301", prefer_live=False, use_cache=False)
    avg_ms = (time.perf_counter() - start) / 100 * 1000
    assert avg_ms < 5, f"Seed lookup took {avg_ms:.2f}ms"
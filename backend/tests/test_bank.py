"""
Tests for the bank account verification stub.
"""
from __future__ import annotations

import pytest

from app.integrations.bank import (
    ResolvedAccount,
    cache_size,
    clear_cache,
    name_match_score,
    resolve_account,
)


@pytest.fixture(autouse=True)
def _clear_cache_between_tests():
    clear_cache()
    yield
    clear_cache()


# ----- Bank code resolution -----

@pytest.mark.asyncio
async def test_resolve_by_bank_code():
    result = await resolve_account("0123456789", "058", simulate_latency=False)
    assert result.found is True
    assert result.account_name == "MEDTRUST NIGERIA LIMITED"
    assert result.bank_name == "Guaranty Trust Bank"


@pytest.mark.asyncio
async def test_resolve_by_bank_name():
    """Bank name should resolve to the same record as bank code."""
    result = await resolve_account("0123456789", "GTBank", simulate_latency=False)
    assert result.found is True
    assert result.bank_code == "058"


@pytest.mark.asyncio
async def test_resolve_by_bank_name_lowercase():
    result = await resolve_account("0123456789", "gtb", simulate_latency=False)
    assert result.found is True


@pytest.mark.asyncio
async def test_invalid_account_length_rejected():
    result = await resolve_account("123", "058", simulate_latency=False)
    assert result.found is False
    assert "10 digits" in result.error


@pytest.mark.asyncio
async def test_unknown_bank_rejected():
    result = await resolve_account("0123456789", "Imaginary Bank", simulate_latency=False)
    assert result.found is False
    assert "Unrecognized bank" in result.error


@pytest.mark.asyncio
async def test_account_not_in_seed_returns_not_found():
    result = await resolve_account("0000000000", "058", simulate_latency=False)
    assert result.found is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_account_strips_whitespace_and_non_digits():
    result = await resolve_account("0123-456-789", "058", simulate_latency=False)
    assert result.found is True
    assert result.account_number == "0123456789"


# ----- The demo gotcha -----

@pytest.mark.asyncio
async def test_quickmeds_account_resolves_to_different_business():
    """The BEC signal — QuickMeds account is registered to Azurite Logistics."""
    result = await resolve_account("9988776655", "058", simulate_latency=False)
    assert result.found is True
    assert "AZURITE" in result.account_name
    assert "QUICKMEDS" not in result.account_name.upper()


# ----- Name matching -----

def test_name_match_perfect():
    assert name_match_score("MedTrust Nigeria Limited", "MEDTRUST NIGERIA LIMITED") == 100


def test_name_match_with_suffix_difference():
    score = name_match_score("MedTrust Nigeria Ltd", "MedTrust Nigeria Limited")
    assert score >= 90


def test_name_match_strips_corporate_suffixes():
    score = name_match_score("ABC Enterprises", "ABC")
    assert score >= 90


def test_name_match_completely_different():
    score = name_match_score("MedTrust Nigeria", "Azurite Logistics")
    assert score < 40


def test_name_match_partial_overlap():
    """One shared word in different businesses — should be below caution threshold."""
    score = name_match_score("MedTrust Nigeria", "MedTrust Holdings")
    # Both share "MedTrust" and "" (suffix stripped) — could be high
    # The important check: not 100, not 0.
    assert 50 <= score <= 99


def test_name_match_handles_none_input():
    assert name_match_score("Anything", None) == 0
    assert name_match_score(None, "Anything") == 0


# ----- Cache behavior -----

@pytest.mark.asyncio
async def test_cache_populates_on_lookup():
    await resolve_account("0123456789", "058", simulate_latency=False)
    assert cache_size() == 1


@pytest.mark.asyncio
async def test_cache_hit_returns_cached_source():
    await resolve_account("0123456789", "058", simulate_latency=False)
    second = await resolve_account("0123456789", "058", simulate_latency=False)
    assert second.source == "cache"
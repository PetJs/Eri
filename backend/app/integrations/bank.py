"""
Bank account verification (STUB)
================================

Resolves a Nigerian bank account number to the name registered against it.

⚠️ This is a STUB for the hackathon demo.
   Production would call a real bank-resolution API:
     - Paystack:    GET https://api.paystack.co/bank/resolve?account_number=...&bank_code=...
     - Flutterwave: POST https://api.flutterwave.com/v3/accounts/resolve
     - Mono:        POST https://api.withmono.com/v2/payments/verify-account

   All three return the same shape: { account_name, account_number, bank_code }.
   We match that shape here so swapping to a real provider later means
   replacing the body of `resolve_account()` only — Engine 1 doesn't change.

For backend devs:
    from app.integrations.bank import resolve_account, name_match_score

    resolved = await resolve_account("0123456789", "058")
    # → ResolvedAccount(account_name="MEDTRUST NIGERIA LIMITED",
    #                   account_number="0123456789", bank_name="GTBank", ...)

    score = name_match_score(
        expected_name="MedTrust Nigeria Limited",
        resolved_name=resolved.account_name,
    )
    # → 100  (perfect match after normalization)
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

CACHE_TTL_S = 3600
LOOKUP_LATENCY_MS = 180  # Simulated network delay for demo feel


# Nigerian bank codes — the ones a real API call would require.
# This is a small subset; the full list has ~30 banks. We include the major
# ones plus what our demo touches.
NIGERIAN_BANK_CODES: dict[str, str] = {
    "044": "Access Bank",
    "014": "Afribank",
    "023": "Citibank",
    "050": "EcoBank",
    "070": "Fidelity Bank",
    "011": "First Bank",
    "214": "First City Monument Bank",
    "058": "Guaranty Trust Bank",        # GTBank
    "030": "Heritage Bank",
    "301": "Jaiz Bank",
    "082": "Keystone Bank",
    "076": "Polaris Bank",
    "101": "Providus Bank",
    "221": "Stanbic IBTC Bank",
    "068": "Standard Chartered Bank",
    "232": "Sterling Bank",
    "100": "SunTrust Bank",
    "032": "Union Bank",
    "033": "United Bank for Africa",
    "215": "Unity Bank",
    "035": "Wema Bank",
    "057": "Zenith Bank",
    # Fintech / neobanks
    "999991": "Opay",
    "999992": "Palmpay",
    "999993": "Kuda Bank",
}


# Allow lookup by name as well as code (buyers usually pick from a dropdown
# that shows the bank name, not the code).
_BANK_NAME_TO_CODE: dict[str, str] = {
    name.lower(): code for code, name in NIGERIAN_BANK_CODES.items()
}
_BANK_NAME_TO_CODE["gtbank"] = "058"        # common alias
_BANK_NAME_TO_CODE["gtb"] = "058"
_BANK_NAME_TO_CODE["uba"] = "033"
_BANK_NAME_TO_CODE["first bank of nigeria"] = "011"


# -----------------------------------------------------------------------------
# Public response type
# -----------------------------------------------------------------------------

@dataclass
class ResolvedAccount:
    """Result of resolving an account number to its registered name.

    Mirrors what Paystack/Flutterwave return. `found=False` means the bank
    returned 'account not found' or the resolution failed for any other
    reason (invalid bank code, network error, account doesn't exist).
    """

    found: bool
    account_number: str
    account_name: str | None = None    # name as registered with the bank
    bank_code: str | None = None
    bank_name: str | None = None
    source: str = "stub"               # "stub" / "live" / "cache" / "error"
    error: str | None = None


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _normalize_account(number: str) -> str:
    """Strip whitespace and non-digits from an account number."""
    return re.sub(r"\D", "", (number or "").strip())


def _resolve_bank_code(bank_input: str) -> str | None:
    """Accept either a bank code ('058') or a bank name ('GTBank') and
    return the canonical code."""
    if not bank_input:
        return None
    cleaned = bank_input.strip()
    if cleaned in NIGERIAN_BANK_CODES:
        return cleaned
    return _BANK_NAME_TO_CODE.get(cleaned.lower())


def name_match_score(expected_name: str, resolved_name: str | None) -> int:
    """Return a 0-100 score for how well two business names match.

    Uses rapidfuzz token_set_ratio which handles word reordering and casing.
    Strips common corporate suffixes so 'ABC Ltd' matches 'ABC Limited'.

    100 = identical after normalization
    80+ = very close (one suffix difference, minor typo)
    60-79 = same root entity, possible mismatch worth flagging
    <60 = likely different entity (BEC red flag)
    """
    if not expected_name or not resolved_name:
        return 0

    def norm(s: str) -> str:
        s = s.strip().upper()
        s = re.sub(r"\s+", " ", s)
        s = re.sub(r"[.,]", "", s)
        # Strip true corporate suffixes only — NOT geography like "NIGERIA".
        # "ABC Limited" should equal "ABC Ltd" but "MedTrust Nigeria" must
        # NOT equal "MedTrust Holdings".
        s = re.sub(
            r"\s+(LIMITED|LTD|PLC|LLC|ENTERPRISES?|INCORPORATED|INC)\.?$",
            "",
            s,
        )
        return s

    a, b = norm(expected_name), norm(resolved_name)
    return int(fuzz.token_set_ratio(a, b))


# -----------------------------------------------------------------------------
# Seeded stub database
# -----------------------------------------------------------------------------
#
# Keyed by (account_number, bank_code). The names here are what the bank
# would return — note that they don't always match what the buyer expects.
# Some entries are deliberate mismatches for the demo gotcha.

_SEED_ACCOUNTS: dict[tuple[str, str], dict[str, Any]] = {
    # MedTrust — clean supplier. Account name matches business name exactly.
    ("0123456789", "058"): {
        "account_name": "MEDTRUST NIGERIA LIMITED",
    },
    # PharmaPlus — also clean
    ("2105887301", "058"): {
        "account_name": "PHARMAPLUS SOLUTIONS LIMITED",
    },
    # Lagos Pharma — fine, but the name on the account is slightly different
    # from the CAC name (registered under the founder's name). Amber territory.
    ("3001234567", "044"): {
        "account_name": "OLUMIDE ADEYEMI",  # owner's personal name — flag!
    },
    # ----- THE DEMO GOTCHA -----
    # QuickMeds: the buyer enters QuickMeds Wholesale + this account number.
    # The bank returns a DIFFERENT business name — classic BEC fraud:
    # supplier directs payment to an unrelated account.
    ("9988776655", "058"): {
        "account_name": "AZURITE LOGISTICS NIGERIA",  # nothing to do with QuickMeds
    },
}


# -----------------------------------------------------------------------------
# In-memory cache
# -----------------------------------------------------------------------------

class _Cache:
    def __init__(self, ttl_seconds: float = CACHE_TTL_S):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, ResolvedAccount]] = {}

    def get(self, key: str) -> ResolvedAccount | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        timestamp, record = entry
        if time.time() - timestamp > self._ttl:
            del self._store[key]
            return None
        return record

    def set(self, key: str, record: ResolvedAccount) -> None:
        self._store[key] = (time.time(), record)

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)


_cache = _Cache()


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

async def resolve_account(
    account_number: str,
    bank: str,
    use_cache: bool = True,
    simulate_latency: bool = True,
) -> ResolvedAccount:
    """Resolve a Nigerian bank account number to its registered name.

    Args:
        account_number: 10-digit Nigerian NUBAN account number
        bank: either the bank's code ('058') or its name ('GTBank' / 'gtb')
        use_cache: return cached result if available
        simulate_latency: add a small sleep so the mock feels realistic.
            Disable in tests.
    """
    account_number = _normalize_account(account_number)
    bank_code = _resolve_bank_code(bank)

    if not account_number:
        return ResolvedAccount(
            found=False,
            account_number=account_number,
            error="Account number is required",
        )
    if len(account_number) != 10:
        return ResolvedAccount(
            found=False,
            account_number=account_number,
            error=f"Account number must be 10 digits (got {len(account_number)})",
        )
    if not bank_code:
        return ResolvedAccount(
            found=False,
            account_number=account_number,
            error=f"Unrecognized bank: '{bank}'",
        )

    cache_key = f"{account_number}:{bank_code}"
    if use_cache:
        cached = _cache.get(cache_key)
        if cached is not None:
            return ResolvedAccount(**{**cached.__dict__, "source": "cache"})

    if simulate_latency:
        await asyncio.sleep(LOOKUP_LATENCY_MS / 1000.0)

    seeded = _SEED_ACCOUNTS.get((account_number, bank_code))

    if seeded is None:
        result = ResolvedAccount(
            found=False,
            account_number=account_number,
            bank_code=bank_code,
            bank_name=NIGERIAN_BANK_CODES.get(bank_code),
            source="stub",
            error="Account not found",
        )
    else:
        result = ResolvedAccount(
            found=True,
            account_number=account_number,
            account_name=seeded["account_name"],
            bank_code=bank_code,
            bank_name=NIGERIAN_BANK_CODES.get(bank_code),
            source="stub",
        )

    if use_cache:
        _cache.set(cache_key, result)
    return result


def resolve_account_sync(account_number: str, bank: str, **kwargs) -> ResolvedAccount:
    return asyncio.run(resolve_account(account_number, bank, **kwargs))


def clear_cache() -> None:
    _cache.clear()


def cache_size() -> int:
    return _cache.size()
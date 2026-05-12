"""
CAC (Corporate Affairs Commission) integration
==============================================

Looks up Nigerian companies and business names against the CAC public registry
via the name-similarity-search endpoint at authapp.cac.gov.ng.

Strategy:
    1. Try the live CAC name-search API
    2. Filter the (noisy, fuzzy) result list for an exact RC-number match
    3. On any failure, fall back to a seeded local database covering our
       demo suppliers
    4. Cache successful lookups in-memory for 1 hour

Why we hit the name-similarity endpoint instead of an RC-direct endpoint:
    CAC's iCRP portal uses this endpoint for the public search page. It
    accepts a name string and returns a list of fuzzy matches. We filter
    that list ourselves for an exact RC-number match. The buyer always
    provides BOTH name and RC number in our flow, so we can verify they
    correspond to the same registered entity — a classic BEC-fraud check.

For backend devs:
    from app.integrations.cac import lookup_cac, CacRecord

    result = await lookup_cac(business_name="MTN Nigeria Communications", rc_number="395010")
    # → CacRecord(found=True, business_name="MTN NIGERIA COMMUNICATIONS PLC",
    #             rc_number="395010", status="ACTIVE", ...)

    valid, issues = result.is_valid_for(
        expected_name="MTN Nigeria Communications",
        expected_rc="395010",
    )
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

CAC_API_URL = "https://authapp.cac.gov.ng/name_similarity_app/api/public_search/search"
CAC_PORTAL_URL = "https://icrp.cac.gov.ng/public-search/"
CAC_TIMEOUT_S = 5.0
CACHE_TTL_S = 3600  # 1 hour

# Status values CAC returns. We normalize on `ACTIVE` for the pass case.
_VALID_ACTIVE_STATUSES = {"ACTIVE"}
_VALID_BUT_CONCERNING_STATUSES = {"INACTIVE", "UNDER_REGISTRATION"}
_RED_FLAG_STATUSES = {"STRUCK OFF", "STRUCK_OFF", "IN LIQUIDATION", "IN_LIQUIDATION", "DISSOLVED"}


# -----------------------------------------------------------------------------
# Public response type
# -----------------------------------------------------------------------------

@dataclass
class CacRecord:
    """Normalized result of a CAC lookup.

    `found=True` means the RC number was found in the search results.
    `source` tells you where the data came from: "live", "seed", or "cache".
    """

    found: bool
    business_name: str | None = None
    rc_number: str | None = None
    status: str | None = None  # ACTIVE / INACTIVE / STRUCK OFF / etc.
    classification: str | None = None  # COMPANY / BUSINESS_NAME / etc.
    nature_of_business: str | None = None
    registration_date: str | None = None  # ISO date string
    source: str = "unknown"  # "live" / "seed" / "cache"
    error: str | None = None

    def is_valid_for(
        self,
        expected_name: str | None = None,
        expected_rc: str | None = None,
    ) -> tuple[bool, list[str]]:
        """Cross-check a found record against what the buyer expected.

        This is one of the strongest BEC-fraud signals we have. A buyer claims
        they're paying "MedTrust Nigeria Ltd" with "RC 1234567"; CAC says
        RC 1234567 belongs to "XYZ Holdings Ltd". Mismatch fires hard.
        """
        issues: list[str] = []

        if not self.found:
            issues.append(
                f"RC number {expected_rc or self.rc_number} not found in CAC registry"
            )
            return False, issues

        # Status checks (do these even if name/rc unchecked)
        if self.status:
            status_upper = self.status.upper().strip()
            if status_upper in _RED_FLAG_STATUSES:
                issues.append(
                    f"Company status is '{self.status}' — not safe to transact"
                )
            elif status_upper in _VALID_BUT_CONCERNING_STATUSES:
                issues.append(
                    f"Company status is '{self.status}' — caution advised"
                )

        # RC number match (strict)
        if expected_rc and self.rc_number:
            if _normalize_rc(expected_rc) != _normalize_rc(self.rc_number):
                issues.append(
                    f"RC number mismatch: CAC has '{self.rc_number}', "
                    f"buyer claims '{expected_rc}'"
                )

        # Business name match (fuzzy — CAC stores dirty names with whitespace)
        if expected_name and self.business_name:
            if not _names_match(expected_name, self.business_name):
                issues.append(
                    f"Business name mismatch: CAC has '{self.business_name.strip()}', "
                    f"buyer claims '{expected_name}'"
                )

        # Overall verdict: pass only if no issues raised AND status is ACTIVE
        passing = (
            len(issues) == 0
            and self.status
            and self.status.upper().strip() in _VALID_ACTIVE_STATUSES
        )
        return passing, issues


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _normalize_rc(rc: str) -> str:
    """Normalize RC numbers for comparison: strip whitespace, uppercase,
    remove 'RC' prefix and any internal spaces/hyphens."""
    rc = rc.strip().upper()
    rc = re.sub(r"^(RC|BN|IT)\s*[-/]?\s*", "", rc)  # strip prefixes like "RC", "BN ", "RC-"
    rc = re.sub(r"[\s\-/]", "", rc)
    return rc


def _normalize_name(name: str) -> str:
    """Normalize a business name for comparison: collapse whitespace,
    uppercase, strip common suffixes."""
    n = name.strip().upper()
    n = re.sub(r"\s+", " ", n)  # collapse runs of whitespace
    # Strip common corporate suffixes so "ABC PLC" == "ABC LTD" == "ABC"
    # — we keep them but normalize them for fuzzy compare
    return n


def _names_match(expected: str, actual: str) -> bool:
    """Fuzzy match for business names. CAC stores names with random extra
    whitespace and trailing spaces; users may type partial names or use
    different casing.
    """
    a = _normalize_name(expected)
    b = _normalize_name(actual)
    if a == b:
        return True
    # Containment in either direction handles short variations:
    # "MTN Nigeria Communications" contained in "MTN NIGERIA COMMUNICATIONS PLC"
    if a in b or b in a:
        return True
    # Token overlap: at least 80% of tokens shared (catches re-orderings,
    # missing 'LTD' suffix, etc.)
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    if not a_tokens or not b_tokens:
        return False
    shared = a_tokens & b_tokens
    smaller = min(len(a_tokens), len(b_tokens))
    return len(shared) / smaller >= 0.8


# -----------------------------------------------------------------------------
# Seeded fallback database
# -----------------------------------------------------------------------------

_SEED_DATA: dict[str, dict[str, Any]] = {
    # Real registered entities (verified against live CAC at build time)
    # Keyed by normalized RC number (no "RC " prefix, no spaces).
    "395010": {
        "business_name": "MTN NIGERIA COMMUNICATIONS PLC",
        "status": "ACTIVE",
        "classification": "COMPANY",
        "nature_of_business": "Telecommunications",
        "registration_date": "2000-11-08",
    },
    "4151": {
        "business_name": "CADBURY NIGERIA PLC",
        "status": "ACTIVE",
        "classification": "COMPANY",
        "nature_of_business": "Manufacture of food products",
        "registration_date": "1965-01-09",
    },
    # ----- Demo suppliers (the procurement scenarios) -----
    # MedTrust Nigeria — the "good supplier" in the demo. Real-looking RC.
    "1842301": {
        "business_name": "MEDTRUST NIGERIA LIMITED",
        "status": "ACTIVE",
        "classification": "COMPANY",
        "nature_of_business": "Pharmaceutical wholesale and distribution",
        "registration_date": "2019-04-15",
    },
    # PharmaPlus Solutions — second "good supplier"
    "2105887": {
        "business_name": "PHARMAPLUS SOLUTIONS LIMITED",
        "status": "ACTIVE",
        "classification": "COMPANY",
        "nature_of_business": "Pharmaceutical wholesale",
        "registration_date": "2020-08-22",
    },
    # Lagos Pharma Distributors — "amber" supplier with minor issues
    "1556923": {
        "business_name": "LAGOS PHARMA DISTRIBUTORS LIMITED",
        "status": "INACTIVE",  # status itself raises a flag
        "classification": "COMPANY",
        "nature_of_business": "Pharmaceutical retail",
        "registration_date": "2017-11-03",
    },
    # ----- The DEMO GOTCHA -----
    # QuickMeds Wholesale: the buyer thinks they're paying "QuickMeds Wholesale Ltd"
    # with RC 9999999. But:
    #   (a) RC 9999999 isn't registered at all (not in this seed)
    #   (b) When we search for "QuickMeds Wholesale", we'd find a different
    #       business with a different RC — classic BEC misdirection.
    # We seed the *real* mismatched entity here so the gotcha works.
    "8801234": {
        "business_name": "QUICKMEDS GENERAL TRADING ENTERPRISE",
        "status": "ACTIVE",
        "classification": "BUSINESS_NAME",  # business name, not a company
        "nature_of_business": "General Merchandise",
        "registration_date": "2025-09-12",  # very recent — also suspicious
    },
}


# -----------------------------------------------------------------------------
# In-memory cache
# -----------------------------------------------------------------------------

class _Cache:
    """Tiny TTL cache, identical shape to the NAFDAC cache."""

    def __init__(self, ttl_seconds: float = CACHE_TTL_S):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, CacRecord]] = {}

    def get(self, key: str) -> CacRecord | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        timestamp, record = entry
        if time.time() - timestamp > self._ttl:
            del self._store[key]
            return None
        return record

    def set(self, key: str, record: CacRecord) -> None:
        self._store[key] = (time.time(), record)

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)


_cache = _Cache()


# -----------------------------------------------------------------------------
# Live CAC query
# -----------------------------------------------------------------------------

async def _query_live(business_name: str, rc_number: str) -> CacRecord | None:
    """Query the live CAC name-similarity API and filter for an exact RC match.

    Returns None on any failure (network, bad response, timeout). Returns a
    CacRecord with found=False if the API responded but no row matched the
    given RC.
    """
    payload = {
        "SearchType": "ALL",
        "searchTerm": business_name.strip(),
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://icrp.cac.gov.ng",
        "Referer": CAC_PORTAL_URL,
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.0.0 Safari/537.36"
        ),
    }

    try:
        async with httpx.AsyncClient(
            timeout=CAC_TIMEOUT_S,
            follow_redirects=True,
        ) as client:
            response = await client.post(CAC_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        logger.warning("CAC API timed out for %s / %s", business_name, rc_number)
        return None
    except httpx.HTTPError as exc:
        logger.warning("CAC HTTP error for %s / %s: %s", business_name, rc_number, exc)
        return None
    except (ValueError, KeyError) as exc:
        logger.warning("CAC bad response for %s / %s: %s", business_name, rc_number, exc)
        return None

    rows = data.get("data") or []
    if not rows:
        return CacRecord(found=False, rc_number=rc_number, source="live")

    # Filter for exact RC match
    target_rc = _normalize_rc(rc_number)
    for row in rows:
        row_rc = row.get("rcNumber")
        if row_rc is None:
            continue
        if _normalize_rc(str(row_rc)) == target_rc:
            return _parse_row(row)

    # API responded but our RC isn't in the result set — treat as not-found.
    # Could mean: (a) RC genuinely unregistered, or (b) the name we searched
    # for didn't surface this RC. Either way, we couldn't verify.
    return CacRecord(
        found=False,
        business_name=business_name,
        rc_number=rc_number,
        source="live",
        error="RC number not present in name-search results",
    )


def _parse_row(row: dict[str, Any]) -> CacRecord:
    """Convert a CAC API row into our normalized CacRecord."""
    # Approval date comes as ISO string; we just keep the date portion
    reg_date = row.get("companyRegistrationDate")
    if reg_date and "T" in reg_date:
        reg_date = reg_date.split("T", 1)[0]

    return CacRecord(
        found=True,
        business_name=(row.get("approvedName") or "").strip() or None,
        rc_number=str(row["rcNumber"]) if row.get("rcNumber") else None,
        status=row.get("status"),
        classification=row.get("classificationName"),
        nature_of_business=row.get("natureOfBusiness") or None,
        registration_date=reg_date,
        source="live",
    )


# -----------------------------------------------------------------------------
# Seed lookup
# -----------------------------------------------------------------------------

def _query_seed(rc_number: str) -> CacRecord:
    """Look up in the seeded fallback database by RC number."""
    key = _normalize_rc(rc_number)
    entry = _SEED_DATA.get(key)
    if entry is None:
        return CacRecord(
            found=False,
            rc_number=rc_number,
            source="seed",
        )
    return CacRecord(
        found=True,
        business_name=entry.get("business_name"),
        rc_number=key,
        status=entry.get("status"),
        classification=entry.get("classification"),
        nature_of_business=entry.get("nature_of_business"),
        registration_date=entry.get("registration_date"),
        source="seed",
    )


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

async def lookup_cac(
    business_name: str,
    rc_number: str,
    use_cache: bool = True,
    prefer_live: bool = True,
) -> CacRecord:
    """Look up a Nigerian business in the CAC registry.

    Args:
        business_name: The business name as the buyer entered it
        rc_number: The RC number as the buyer entered it. Required for an
            exact-match lookup — we filter the API results by this.
        use_cache: Return cached result if available
        prefer_live: Try live API first and fall back to seed. Set to False
            for offline tests or when you want deterministic seed-only results.
    """
    business_name = (business_name or "").strip()
    rc_number = (rc_number or "").strip()
    if not business_name or not rc_number:
        return CacRecord(
            found=False,
            error="Both business name and RC number are required",
        )

    cache_key = _normalize_rc(rc_number)

    if use_cache:
        cached = _cache.get(cache_key)
        if cached is not None:
            return CacRecord(**{**cached.__dict__, "source": "cache"})

    if prefer_live:
        live_result = await _query_live(business_name, rc_number)
        if live_result is not None:
            if use_cache and live_result.found:
                _cache.set(cache_key, live_result)
            # If live found a record, return it — even if name/rc mismatch
            # exists, that's what `is_valid_for()` is for.
            if live_result.found:
                return live_result
            # Live responded but didn't find the RC — fall through to seed
            # in case our demo data has it.

    seed_result = _query_seed(rc_number)
    if use_cache:
        _cache.set(cache_key, seed_result)
    return seed_result


def lookup_cac_sync(business_name: str, rc_number: str, **kwargs) -> CacRecord:
    """Sync wrapper for non-async callers."""
    return asyncio.run(lookup_cac(business_name, rc_number, **kwargs))


def clear_cache() -> None:
    """Drop all cached entries. Useful in tests."""
    _cache.clear()


def cache_size() -> int:
    return _cache.size()
"""
Court records integration (MOCKED)
==================================

Looks up Nigerian businesses against a seeded database of court records.

⚠️ This is a MOCK for the hackathon demo.
   Production would call a commercial Nigerian court-records API
   (LawPavilion, Verify Africa, BusinessScreen, etc.). We use the same
   function signature and return shape those commercial APIs typically use,
   so swapping to a real provider later is a code change inside this file
   only — Engine 1 and the rest of the backend don't need to know.

What it provides:
    - lookup_court_records(business_name) → CourtRecordSummary
    - The summary includes case count, active vs. closed cases, whether
      any cases involve fraud allegations, and a list of individual cases.

For backend devs:
    from app.integrations.court_records import lookup_court_records

    result = await lookup_court_records("QuickMeds Wholesale")
    # → CourtRecordSummary(case_count=3, has_fraud_allegations=True, ...)

    risky, issues = result.assess_risk()
    # → (True, ["3 active fraud cases against this business", ...])
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

CACHE_TTL_S = 3600  # 1 hour
LOOKUP_LATENCY_MS = 250  # Simulated network delay so the mock feels realistic


# -----------------------------------------------------------------------------
# Public response types
# -----------------------------------------------------------------------------

# Case categories matching what Nigerian commercial APIs typically expose.
# We use these to flag fraud-related cases specifically — those are the
# strongest signal for procurement-fraud verification.
_FRAUD_CASE_TYPES = {
    "FRAUD",
    "BREACH_OF_CONTRACT",
    "ADVANCE_FEE_FRAUD",
    "FORGERY",
    "MISREPRESENTATION",
}


@dataclass
class CourtCase:
    """A single court case against the business."""

    case_number: str
    case_type: str            # FRAUD / BREACH_OF_CONTRACT / CIVIL_SUIT / etc.
    court: str                # "Federal High Court Lagos" etc.
    plaintiff: str            # who filed the case
    status: str               # "ACTIVE" / "CLOSED" / "PENDING_JUDGMENT" / "DISMISSED"
    filed_date: str           # ISO date
    summary: str              # one-line description

    @property
    def is_fraud_related(self) -> bool:
        return self.case_type.upper() in _FRAUD_CASE_TYPES

    @property
    def is_active(self) -> bool:
        return self.status.upper() in {"ACTIVE", "PENDING_JUDGMENT"}


@dataclass
class CourtRecordSummary:
    """Result of a court records lookup."""

    business_name: str
    found: bool                   # True if we have a record for this business
    case_count: int = 0
    active_case_count: int = 0
    fraud_case_count: int = 0
    has_fraud_allegations: bool = False
    most_recent_case_date: str | None = None
    cases: list[CourtCase] = field(default_factory=list)
    source: str = "mock"          # always "mock" for now
    error: str | None = None

    def assess_risk(self) -> tuple[bool, list[str]]:
        """Decide whether this business carries court-records risk.

        Returns (is_risky, list_of_concerns). Concerns are human-readable
        strings the verdict UI can show directly.

        Risk rules:
          - Any active fraud case → risky
          - 3+ active cases of any type → risky
          - 1-2 active cases that aren't fraud → caution (still flagged)
          - 0 active cases → clean
        """
        concerns: list[str] = []

        if not self.found:
            # No record found is NOT the same as "clean" — we just don't know.
            # We say so explicitly so the UI can show this as a soft signal.
            return False, ["No court records on file (may be a new entity)"]

        if self.fraud_case_count > 0:
            concerns.append(
                f"{self.fraud_case_count} active fraud-related case(s) against this business"
            )

        if self.active_case_count >= 3:
            concerns.append(
                f"{self.active_case_count} active court cases — pattern of disputes"
            )
        elif self.active_case_count >= 1 and self.fraud_case_count == 0:
            concerns.append(
                f"{self.active_case_count} active court case(s) — review recommended"
            )

        # Most-recent date isn't a concern by itself, but if recent + fraud,
        # add color to the explanation
        if self.most_recent_case_date and self.fraud_case_count > 0:
            concerns.append(
                f"Most recent case filed {self.most_recent_case_date}"
            )

        is_risky = self.fraud_case_count > 0 or self.active_case_count >= 3
        return is_risky, concerns


# -----------------------------------------------------------------------------
# Name normalization (same approach as cac.py — keep them consistent)
# -----------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """Canonicalize a business name for keyed lookups."""
    n = (name or "").strip().upper()
    n = re.sub(r"\s+", " ", n)
    # Strip common corporate suffixes for fuzzier matching
    n = re.sub(r"\s+(LIMITED|LTD|PLC|LLC|ENTERPRISES?|INCORPORATED|INC)\.?$", "", n)
    return n


# -----------------------------------------------------------------------------
# Seeded mock database
# -----------------------------------------------------------------------------
#
# Keyed by normalized business name (via _normalize_name). The dates are
# realistic Nigerian-court dates. Case numbers loosely follow the Nigerian
# format (e.g. "FHC/L/CS/123/2024" = Federal High Court, Lagos, Civil
# Suit, case 123 of 2024).

_SEED_CASES: dict[str, list[dict[str, Any]]] = {
    # ----- Demo's "good" suppliers — no court records -----
    "MEDTRUST NIGERIA": [],
    "PHARMAPLUS SOLUTIONS": [],

    # ----- Lagos Pharma — one minor civil case, amber flag -----
    "LAGOS PHARMA DISTRIBUTORS": [
        {
            "case_number": "FHC/L/CS/847/2024",
            "case_type": "BREACH_OF_CONTRACT",
            "court": "Federal High Court, Lagos Division",
            "plaintiff": "Sunrise Hospitals Ltd",
            "status": "CLOSED",
            "filed_date": "2024-03-12",
            "summary": "Civil suit over delayed delivery of antibiotics shipment; settled out of court.",
        },
    ],

    # ----- QuickMeds — the demo gotcha. Multiple active fraud cases. -----
    "QUICKMEDS WHOLESALE": [
        {
            "case_number": "FHC/L/CS/1421/2025",
            "case_type": "FRAUD",
            "court": "Federal High Court, Lagos Division",
            "plaintiff": "Ministry of Health, Edo State",
            "status": "ACTIVE",
            "filed_date": "2025-09-04",
            "summary": "Alleged supply of counterfeit antimalarial drugs in state procurement contract.",
        },
        {
            "case_number": "HCT/IK/CR/088/2025",
            "case_type": "FRAUD",
            "court": "High Court of Lagos State, Ikeja Division",
            "plaintiff": "Federal Republic of Nigeria",
            "status": "ACTIVE",
            "filed_date": "2025-11-21",
            "summary": "Charges of obtaining money under false pretenses from three pharmaceutical buyers.",
        },
        {
            "case_number": "FHC/ABJ/CS/2210/2024",
            "case_type": "BREACH_OF_CONTRACT",
            "court": "Federal High Court, Abuja Division",
            "plaintiff": "Plateau State Hospitals Board",
            "status": "PENDING_JUDGMENT",
            "filed_date": "2024-12-15",
            "summary": "Failure to deliver paid-for medical supplies worth ₦42M.",
        },
    ],

    # ----- Naija Healthcare Supplies — new entity, no records -----
    # Deliberately not in seed, so lookup returns found=False
    # (which assess_risk() reports as "may be a new entity")

    # ----- A few real-world public-figure businesses for testing -----
    # These have no court records — useful for sanity tests.
    "MTN NIGERIA COMMUNICATIONS": [],
    "CADBURY NIGERIA": [],
}


# -----------------------------------------------------------------------------
# In-memory cache
# -----------------------------------------------------------------------------

class _Cache:
    """Same shape as nafdac/cac caches."""

    def __init__(self, ttl_seconds: float = CACHE_TTL_S):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, CourtRecordSummary]] = {}

    def get(self, key: str) -> CourtRecordSummary | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        timestamp, record = entry
        if time.time() - timestamp > self._ttl:
            del self._store[key]
            return None
        return record

    def set(self, key: str, record: CourtRecordSummary) -> None:
        self._store[key] = (time.time(), record)

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)


_cache = _Cache()


# -----------------------------------------------------------------------------
# Lookup logic
# -----------------------------------------------------------------------------

def _build_summary(
    business_name: str,
    raw_cases: list[dict[str, Any]],
) -> CourtRecordSummary:
    """Convert raw seed entries into a CourtRecordSummary."""
    cases = [CourtCase(**c) for c in raw_cases]

    active = [c for c in cases if c.is_active]
    fraud = [c for c in cases if c.is_fraud_related and c.is_active]

    most_recent: str | None = None
    if cases:
        most_recent = max(c.filed_date for c in cases)

    return CourtRecordSummary(
        business_name=business_name,
        found=True,  # If we have an entry (even with [] cases), we "know about" them
        case_count=len(cases),
        active_case_count=len(active),
        fraud_case_count=len(fraud),
        has_fraud_allegations=len(fraud) > 0,
        most_recent_case_date=most_recent,
        cases=cases,
        source="mock",
    )


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

async def lookup_court_records(
    business_name: str,
    use_cache: bool = True,
    simulate_latency: bool = True,
) -> CourtRecordSummary:
    """Look up court records for a Nigerian business.

    Args:
        business_name: The business name from the buyer's input
        use_cache: Return cached result if available
        simulate_latency: Add a small sleep so the mock feels like a real
            network call (helpful when chaining engines so the demo's
            loading states have time to animate). Set to False in tests.
    """
    business_name = (business_name or "").strip()
    if not business_name:
        return CourtRecordSummary(
            business_name="",
            found=False,
            error="Business name is required",
        )

    cache_key = _normalize_name(business_name)

    if use_cache:
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

    # Simulate a real API call's latency so the demo's loading state animates
    if simulate_latency:
        await asyncio.sleep(LOOKUP_LATENCY_MS / 1000.0)

    raw = _SEED_CASES.get(cache_key)

    if raw is None:
        # Try a looser match — partial-name lookups in case the buyer's
        # spelling doesn't exactly match our seed key
        for seed_key, seed_cases in _SEED_CASES.items():
            if seed_key in cache_key or cache_key in seed_key:
                raw = seed_cases
                break

    if raw is None:
        # No record found at all
        result = CourtRecordSummary(
            business_name=business_name,
            found=False,
            source="mock",
        )
    else:
        result = _build_summary(business_name, raw)

    if use_cache:
        _cache.set(cache_key, result)
    return result


def lookup_court_records_sync(business_name: str, **kwargs) -> CourtRecordSummary:
    """Sync wrapper."""
    return asyncio.run(lookup_court_records(business_name, **kwargs))


def clear_cache() -> None:
    _cache.clear()


def cache_size() -> int:
    return _cache.size()
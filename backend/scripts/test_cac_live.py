"""
Manual integration test against the live CAC API.

Run from backend/ directory:
    python -m scripts.test_cac_live

What this does:
    1. Tries to fetch a known real company (MTN Nigeria, RC 395010) from the
       live CAC API. Should succeed with source='live'.
    2. Tries a name search that exists but with a fake RC number. Should
       return found=False (the API responds, but no row matches the RC).
    3. Demonstrates the BEC cross-check: name says "MedTrust Nigeria" but
       RC belongs to a different company.
    4. Cache test: a second lookup hits cache.

Run this:
    - First time you pull the CAC integration
    - Before demo day to verify CAC API is still accessible
    - When something seems off
"""
from __future__ import annotations

import asyncio
import sys

from app.integrations.cac import lookup_cac, clear_cache


async def main() -> int:
    print("=" * 70)
    print("CAC API live integration test")
    print("=" * 70)

    # ----- Test 1: live API hit -----
    print("\n[1] Hitting live CAC API for MTN Nigeria (RC 395010)...")
    clear_cache()
    result = await lookup_cac(
        business_name="MTN Nigeria Communications",
        rc_number="395010",
        prefer_live=True,
    )
    print(f"    source: {result.source}")
    print(f"    found: {result.found}")
    if result.found:
        print(f"    business_name: {result.business_name}")
        print(f"    status: {result.status}")
        print(f"    classification: {result.classification}")
        print(f"    registration_date: {result.registration_date}")

    if result.source == "live" and result.found:
        print("    [OK] Live API is reachable and working")
    elif result.source == "seed":
        print("    [WARN] Live API unreachable. Fell back to seed.")
    else:
        print("    [FAIL] Unexpected outcome.")
        return 1

    # ----- Test 2: name match but RC mismatch -----
    print("\n[2] Searching MTN with a fake RC number (9999999)...")
    clear_cache()
    result = await lookup_cac(
        business_name="MTN Nigeria",
        rc_number="9999999",
        prefer_live=True,
    )
    print(f"    source: {result.source}")
    print(f"    found: {result.found}")
    if not result.found:
        print("    [OK] API correctly returned no match for fake RC")
    else:
        print("    [WARN] Got a match for a fake RC. Check the data.")

    # ----- Test 3: BEC-style cross-check on seeded supplier -----
    print("\n[3] BEC scenario: MedTrust name + correct RC vs wrong RC...")
    clear_cache()
    # Use seed for this since MedTrust isn't a real company
    legitimate = await lookup_cac(
        business_name="MedTrust Nigeria",
        rc_number="1842301",
        prefer_live=False,
    )
    valid, issues = legitimate.is_valid_for(
        expected_name="MedTrust Nigeria Limited",
        expected_rc="1842301",
    )
    print(f"    Legitimate flow: valid={valid}, issues={issues}")

    fraudulent = await lookup_cac(
        business_name="MedTrust Nigeria",
        rc_number="1842301",  # same record
        prefer_live=False,
        use_cache=False,
    )
    valid, issues = fraudulent.is_valid_for(
        expected_name="MedTrust Nigeria Limited",
        expected_rc="9999999",  # buyer claims different RC — BEC red flag
    )
    print(f"    BEC scenario:    valid={valid}")
    for issue in issues:
        print(f"      - {issue}")

    if not valid and any("rc number mismatch" in i.lower() for i in issues):
        print("    [OK] BEC cross-check works")
    else:
        print("    [FAIL] BEC cross-check logic broken")
        return 1

    # ----- Test 4: cache -----
    print("\n[4] Cache: second lookup should be source='cache'...")
    clear_cache()
    first = await lookup_cac(
        business_name="MTN Nigeria",
        rc_number="395010",
        prefer_live=True,
    )
    second = await lookup_cac(
        business_name="MTN Nigeria",
        rc_number="395010",
        prefer_live=True,
    )
    print(f"    First source:  {first.source}")
    print(f"    Second source: {second.source}")
    if second.source == "cache":
        print("    [OK] Cache works")
    else:
        print("    [WARN] Cache miss on second lookup")

    print("\n" + "=" * 70)
    print("All checks complete.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
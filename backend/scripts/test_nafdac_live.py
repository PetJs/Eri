"""
Manual integration test against the live NAFDAC Greenbook.

Run from backend/ directory:
    python -m scripts.test_nafdac_live

What this does:
    1. Tries to fetch a known real NAFDAC number (03-6514, Accu-Chek) from the
       live Greenbook API. Should succeed and print real data from NAFDAC.
    2. Tries a number that doesn't exist (99-9999). Should return
       registered=False with source='live'.
    3. Tests the seed fallback explicitly. Should return the demo gotcha
       record for 04-6433.
    4. Demonstrates the cross-check that powers the demo: pretending the
       buyer expected Coartem from Novartis but got 04-6433 (Proguanil).

When to run this:
    - First time the backend dev pulls the NAFDAC integration code
    - Before demo day, to verify NAFDAC is still up and our request shape
      still matches their API
    - When something seems off

When NOT to run this:
    - In CI (no network reliability guarantees)
    - During the actual demo (use the regular code path)
"""
from __future__ import annotations

import asyncio
import sys

from app.integrations.nafdac import lookup_nafdac, clear_cache


async def main() -> int:
    print("=" * 70)
    print("NAFDAC Greenbook live integration test")
    print("=" * 70)

    # ----- Test 1: live API hit -----
    print("\n[1] Hitting live NAFDAC API for known real product (03-6514)...")
    clear_cache()
    result = await lookup_nafdac("03-6514", prefer_live=True)
    print(f"    source: {result.source}")
    print(f"    registered: {result.registered}")
    if result.registered:
        print(f"    product: {result.product_name}")
        print(f"    manufacturer: {result.manufacturer}")
        print(f"    status: {result.status}")

    if result.source == "live" and result.registered:
        print("    [OK] Live API is reachable and working")
    elif result.source == "seed":
        print("    [WARN] Live API unreachable. Fell back to seed.")
        print("           This is fine for development but check network on demo day.")
    else:
        print(f"    [FAIL] Unexpected outcome. Inspect logs.")
        return 1

    # ----- Test 2: live API miss -----
    print("\n[2] Querying nonexistent NAFDAC number (99-9999)...")
    clear_cache()
    result = await lookup_nafdac("99-9999", prefer_live=True)
    print(f"    source: {result.source}")
    print(f"    registered: {result.registered}")
    if result.registered:
        print(f"    [FAIL] Got a match for a fake number. Something is wrong.")
        return 1
    print(f"    [OK] Correctly reported as not registered")

    # ----- Test 3: the demo gotcha -----
    print("\n[3] Demo gotcha: 04-6433 lookup with Coartem/Novartis expectation...")
    clear_cache()
    # Force seed for this test because the live API won't have our fake setup
    result = await lookup_nafdac("04-6433", prefer_live=False)
    print(f"    source: {result.source}")
    print(f"    NAFDAC says this is: {result.product_name} from {result.manufacturer}")

    is_valid, issues = result.is_valid_for(
        expected_manufacturer="Novartis",
        expected_product="Coartem",
    )
    print(f"    Buyer expected: Coartem from Novartis")
    print(f"    Cross-check passed: {is_valid}")
    print(f"    Issues raised:")
    for issue in issues:
        print(f"      - {issue}")

    if not is_valid and len(issues) >= 2:
        print(f"    [OK] Gotcha works — counterfeit detected")
    else:
        print(f"    [FAIL] Gotcha logic is broken")
        return 1

    # ----- Test 4: cache behavior on live hit -----
    print("\n[4] Caching: a second live lookup should hit the cache...")
    clear_cache()
    first = await lookup_nafdac("03-6514", prefer_live=True)
    second = await lookup_nafdac("03-6514", prefer_live=True)
    print(f"    First lookup source:  {first.source}")
    print(f"    Second lookup source: {second.source}")
    if second.source == "cache":
        print(f"    [OK] Cache is working")
    else:
        print(f"    [WARN] Cache didn't hit. May still be fine if first lookup failed.")

    print("\n" + "=" * 70)
    print("All checks complete.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
"""
Squad (HabariPay) API client
============================

Wraps the Squad sandbox API for the two operations we actually use in the demo:

    1. resolve_account(number, bank_code)  → returns the registered account holder name
    2. initiate_transfer(...)              → sends funds from our balance to a supplier's bank

Virtual account creation is NOT wrapped here — that endpoint requires merchant
profiling which we don't have for the hackathon. We keep virtual accounts
stubbed in `app/routers/orders.py` and use this client only for the two
real operations.

Auth: Bearer token from SQUAD_SECRET_KEY env var.
Base URL: https://sandbox-api-d.squadco.com (sandbox).

For backend devs:
    from app.integrations.squad import get_squad_client

    client = get_squad_client()
    resolved = await client.resolve_account("0123456789", "058")
    # → SquadAccountLookup(found=True, account_name="JOHN DOE", ...)

    transfer = await client.initiate_transfer(
        amount_kobo=125_000_000,  # ₦1.25M in kobo
        bank_code="058",
        account_number="0123456789",
        account_name="JOHN DOE",
        narration="Eri escrow release for order ord_abc",
    )
    # → SquadTransfer(success=True, transaction_ref="REF...", ...)
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

# Timeouts: sandbox is usually fast, but slow days happen.
SQUAD_TIMEOUT_S = 10.0


# -----------------------------------------------------------------------------
# Public response types
# -----------------------------------------------------------------------------

@dataclass
class SquadAccountLookup:
    """Result of POST /payout/account/lookup."""

    found: bool
    account_number: str
    account_name: str | None = None
    bank_code: str | None = None
    source: str = "squad"      # "squad" | "error"
    error: str | None = None


@dataclass
class SquadTransfer:
    """Result of POST /payout/transfer."""

    success: bool
    transaction_ref: str
    amount_kobo: int | None = None
    recipient_account: str | None = None
    recipient_name: str | None = None
    status: str | None = None              # "Success" | "Pending" | "Failed"
    nip_session_id: str | None = None      # NIBSS session ID, if returned
    error: str | None = None


@dataclass
class SquadVirtualAccount:
    """Result of POST /virtual-account/initiate-dynamic-virtual-account.

    Represents a virtual NUBAN assigned from our DVA pool to a specific
    transaction. The account expires after `duration` seconds and can only
    receive `expected_amount` exactly — any other amount is mismatched
    and webhook-flagged.
    """

    success: bool
    transaction_reference: str
    account_number: str | None = None
    account_name: str | None = None
    bank: str | None = None
    expected_amount_naira: str | None = None  # Squad returns this as a string
    expires_at: str | None = None              # ISO timestamp
    currency: str = "NGN"
    is_blocked: bool = False
    error: str | None = None
    refilled_pool: bool = False                # True if auto-refill kicked in


# -----------------------------------------------------------------------------
# Client
# -----------------------------------------------------------------------------

class SquadClient:
    """Async Squad API wrapper.

    Constructed lazily by `get_squad_client()` — only fails when actually
    called if SQUAD_SECRET_KEY is missing. This means modules that import
    this client (e.g. bank.py) don't crash on import when running tests
    without Squad credentials configured.
    """

    def __init__(self, secret_key: str, base_url: str) -> None:
        if not secret_key:
            raise RuntimeError(
                "SQUAD_SECRET_KEY is not set. Add it to .env.local "
                "(or your Render env vars) before calling Squad."
            )
        self._secret_key = secret_key
        self._base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Account lookup — used by bank.py for BEC defense
    # ------------------------------------------------------------------

    async def resolve_account(
        self,
        account_number: str,
        bank_code: str,
    ) -> SquadAccountLookup:
        """Look up the registered account-holder name for an account number.

        This is the BEC fraud signal: buyer says "pay to QuickMeds at
        0123456789"; Squad replies "that account belongs to AZURITE
        LOGISTICS NIGERIA" → name mismatch → red flag.

        Returns SquadAccountLookup(found=False, error=...) on any
        error rather than raising — callers fall back to seeded data.
        """
        url = f"{self._base_url}/payout/account/lookup"
        payload = {
            "bank_code": bank_code.strip(),
            "account_number": account_number.strip(),
        }

        try:
            async with self._client() as http:
                response = await http.post(url, json=payload)

            data = response.json()

            # Squad returns 200 with success:true on hit, 200 with
            # success:false on miss, and 4xx/5xx on errors.
            if response.status_code != 200 or not data.get("success"):
                message = data.get("message", "Unknown error")
                return SquadAccountLookup(
                    found=False,
                    account_number=account_number,
                    bank_code=bank_code,
                    error=message,
                    source="error" if response.status_code >= 400 else "squad",
                )

            body = data.get("data") or {}
            return SquadAccountLookup(
                found=True,
                account_number=body.get("account_number", account_number),
                account_name=body.get("account_name"),
                bank_code=body.get("bank_code", bank_code),
                source="squad",
            )

        except httpx.TimeoutException:
            logger.warning("Squad account lookup timed out for %s/%s",
                           bank_code, account_number)
            return SquadAccountLookup(
                found=False,
                account_number=account_number,
                bank_code=bank_code,
                source="error",
                error="Timeout",
            )
        except httpx.HTTPError as exc:
            logger.warning("Squad account lookup HTTP error: %s", exc)
            return SquadAccountLookup(
                found=False,
                account_number=account_number,
                bank_code=bank_code,
                source="error",
                error=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Squad account lookup unexpected error: %s", exc)
            return SquadAccountLookup(
                found=False,
                account_number=account_number,
                bank_code=bank_code,
                source="error",
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Transfer — used by /orders/{id}/release
    # ------------------------------------------------------------------

    async def initiate_transfer(
        self,
        amount_kobo: int,
        bank_code: str,
        account_number: str,
        account_name: str,
        narration: str,
        transaction_reference: str | None = None,
        remark: str | None = None,
    ) -> SquadTransfer:
        """Send funds from our Squad balance to a Nigerian bank account.

        In sandbox, this returns a Success response without moving real money.
        In production, this debits the merchant's Squad balance and credits
        the supplier's bank via NIBSS instant transfer.

        Args:
            amount_kobo: amount in kobo (₦1 = 100 kobo). E.g. ₦1,250,000 = 125_000_000.
            bank_code: 3-digit Nigerian bank code (e.g. "058" for GTBank)
            account_number: 10-digit NUBAN
            account_name: name as returned by `resolve_account()` — Squad
                validates this matches its records before processing.
            narration: short description shown on the supplier's bank statement
            transaction_reference: optional idempotency key; we generate one if absent
            remark: optional internal note
        """
        url = f"{self._base_url}/payout/transfer"
        ref = transaction_reference or f"ERI-{uuid.uuid4().hex[:16].upper()}"

        payload: dict[str, Any] = {
            "transaction_reference": ref,
            "amount": amount_kobo,
            "currency_id": "NGN",
            "bank_code": bank_code.strip(),
            "account_number": account_number.strip(),
            "account_name": account_name,
            "remark": remark or narration[:50],
        }

        try:
            async with self._client() as http:
                response = await http.post(url, json=payload)

            data = response.json()

            if response.status_code != 200 or not data.get("success"):
                message = data.get("message", "Transfer failed")
                logger.warning("Squad transfer failed: %s (status=%s)",
                               message, response.status_code)
                return SquadTransfer(
                    success=False,
                    transaction_ref=ref,
                    error=message,
                )

            body = data.get("data") or {}
            return SquadTransfer(
                success=True,
                transaction_ref=body.get("transaction_reference", ref),
                amount_kobo=body.get("amount", amount_kobo),
                recipient_account=body.get("account_number"),
                recipient_name=body.get("account_name"),
                status=body.get("transaction_status") or body.get("status"),
                nip_session_id=body.get("nip_session_id"),
            )

        except httpx.TimeoutException:
            logger.warning("Squad transfer timed out")
            return SquadTransfer(
                success=False,
                transaction_ref=ref,
                error="Timeout",
            )
        except httpx.HTTPError as exc:
            logger.warning("Squad transfer HTTP error: %s", exc)
            return SquadTransfer(
                success=False,
                transaction_ref=ref,
                error=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Squad transfer unexpected error: %s", exc)
            return SquadTransfer(
                success=False,
                transaction_ref=ref,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Dynamic Virtual Accounts (DVA) — used by orders router for escrow accounts
    # ------------------------------------------------------------------

    async def create_pool_account(self) -> bool:
        """Add a single virtual account to the DVA pool.

        Returns True on success, False otherwise. The pool is the bucket of
        pre-provisioned accounts that `initiate_dynamic_va()` assigns from.
        Called proactively at startup or reactively when the pool runs dry.

        Squad's docs say all fields are optional — we send an empty body
        and let Squad assign whatever default merchant name it wants.
        """
        url = f"{self._base_url}/virtual-account/create-dynamic-virtual-account"
        try:
            async with self._client() as http:
                response = await http.post(url, json={})
            data = response.json()
            if response.status_code == 200 and data.get("success"):
                logger.info("Created new DVA pool account")
                return True
            logger.warning(
                "DVA pool refill failed: status=%s message=%s",
                response.status_code, data.get("message"),
            )
            return False
        except Exception as exc:  # noqa: BLE001
            logger.warning("DVA pool refill exception: %s", exc)
            return False

    async def initiate_dynamic_va(
        self,
        amount_kobo: int,
        transaction_ref: str,
        email: str,
        duration_seconds: int = 3600,
        _retry_after_refill: bool = False,
    ) -> SquadVirtualAccount:
        """Assign a virtual account from the DVA pool to a specific transaction.

        Squad will return one of our pool accounts, tagged with the expected
        amount and an expiry. Buyer transfers the exact amount to this NUBAN
        within `duration_seconds`; Squad fires a webhook when funds land.

        If the pool is empty (Squad returns "Unable to retrieve a virtual
        account"), we auto-refill by calling create_pool_account() once and
        retry. Further failures surface as `success=False`.

        Args:
            amount_kobo: amount in kobo (₦1 = 100 kobo). Squad's amount field
                for THIS endpoint expects a *naira* string — we convert here.
            transaction_ref: unique per call. Reusing this fails.
            email: buyer's email (Squad requires it for receipts / webhooks).
            duration_seconds: how long the account stays valid. Default 1 hour.
            _retry_after_refill: internal — prevents infinite recursion.
        """
        url = f"{self._base_url}/virtual-account/initiate-dynamic-virtual-account"

        # Squad's DVA endpoint expects amount in KOBO (not naira) as a string.
        # Confirmed via sandbox testing: passing "1000" results in
        # merchant_amount: "1.00" (Squad divides by 100 internally).
        # Same convention as the Transfer endpoint.
        amount_kobo_str = str(amount_kobo)

        payload: dict[str, Any] = {
            "amount": amount_kobo_str,
            "transaction_ref": transaction_ref,
            "email": email,
            "duration": str(duration_seconds),
        }

        try:
            async with self._client() as http:
                response = await http.post(url, json=payload)
            data = response.json()

            # Pool-exhausted case: 404 with the specific "Unable to retrieve"
            # message. Refill once and retry — but never recurse twice.
            message = (data.get("message") or "").lower()
            if (
                response.status_code == 404
                and "unable to retrieve" in message
                and not _retry_after_refill
            ):
                logger.info("DVA pool empty — auto-refilling and retrying")
                refilled = await self.create_pool_account()
                if refilled:
                    result = await self.initiate_dynamic_va(
                        amount_kobo=amount_kobo,
                        transaction_ref=transaction_ref,
                        email=email,
                        duration_seconds=duration_seconds,
                        _retry_after_refill=True,
                    )
                    # Mark on the response that we had to refill — useful for
                    # the admin metrics endpoint and any monitoring later.
                    result.refilled_pool = True
                    return result

            if response.status_code != 200 or not data.get("success"):
                return SquadVirtualAccount(
                    success=False,
                    transaction_reference=transaction_ref,
                    error=data.get("message", f"DVA initiate failed (HTTP {response.status_code})"),
                )

            body = data.get("data") or {}
            return SquadVirtualAccount(
                success=True,
                transaction_reference=body.get("transaction_reference", transaction_ref),
                account_number=body.get("account_number"),
                account_name=(body.get("account_name") or "").strip() or None,
                bank=body.get("bank"),
                expected_amount_naira=body.get("expected_amount"),
                expires_at=body.get("expires_at"),
                currency=body.get("currency", "NGN"),
                is_blocked=bool(body.get("is_blocked", False)),
            )

        except httpx.TimeoutException:
            logger.warning("DVA initiate timed out for ref=%s", transaction_ref)
            return SquadVirtualAccount(
                success=False,
                transaction_reference=transaction_ref,
                error="Timeout",
            )
        except httpx.HTTPError as exc:
            logger.warning("DVA initiate HTTP error: %s", exc)
            return SquadVirtualAccount(
                success=False,
                transaction_reference=transaction_ref,
                error=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("DVA initiate unexpected error: %s", exc)
            return SquadVirtualAccount(
                success=False,
                transaction_reference=transaction_ref,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Internal: HTTP client factory
    # ------------------------------------------------------------------

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=SQUAD_TIMEOUT_S,
            headers={
                "Authorization": f"Bearer {self._secret_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )


# -----------------------------------------------------------------------------
# Module-level lazy singleton
# -----------------------------------------------------------------------------

_client_singleton: SquadClient | None = None


def get_squad_client() -> SquadClient | None:
    """Return a memoized SquadClient, or None if Squad isn't configured.

    Returning None (rather than raising) lets callers like bank.py gracefully
    fall back to seeded data when Squad keys aren't configured (e.g. in
    tests, or when running on a machine without SQUAD_SECRET_KEY).
    """
    global _client_singleton
    if _client_singleton is not None:
        return _client_singleton
    if not settings.squad_secret_key:
        logger.debug("SQUAD_SECRET_KEY not set; Squad client unavailable")
        return None
    try:
        _client_singleton = SquadClient(
            secret_key=settings.squad_secret_key,
            base_url=settings.squad_base_url,
        )
        return _client_singleton
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to construct SquadClient: %s", exc)
        return None


def reset_squad_client() -> None:
    """Reset the singleton — useful in tests when monkeypatching."""
    global _client_singleton
    _client_singleton = None
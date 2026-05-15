"""
Tests for the Squad integration:

  - Direct tests of SquadClient against mocked HTTP responses (respx)
  - bank.py hybrid path: Squad first, seed fallback
  - The /admin/demo/simulate-payment endpoint
  - The /orders/{id}/release endpoint with real Squad calls

We mock the Squad API entirely (respx) — no network in tests, deterministic.
"""
from __future__ import annotations

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.integrations import bank
from app.integrations.squad import (
    SquadClient,
    get_squad_client,
    reset_squad_client,
)
from app.main import app
from app.settings import settings


SQUAD_BASE = "https://sandbox-api-d.squadco.com"
DVA_INITIATE_URL = f"{SQUAD_BASE}/virtual-account/initiate-dynamic-virtual-account"
SIMULATE_PAYMENT_URL = f"{SQUAD_BASE}/virtual-account/simulate/payment"


@pytest.fixture(autouse=True)
def _isolate_state(monkeypatch):
    """Reset all relevant caches and the Squad singleton between tests."""
    bank.clear_cache()
    reset_squad_client()
    # Ensure tests always think Squad is configured
    monkeypatch.setattr(settings, "squad_secret_key", "sandbox_sk_test")
    monkeypatch.setattr(settings, "squad_base_url", SQUAD_BASE)
    # Disable webhook signature verification in tests (no secret = bypass)
    monkeypatch.setattr(settings, "squad_webhook_secret", "")
    yield
    bank.clear_cache()
    reset_squad_client()


@pytest.fixture
def client():
    return TestClient(app)


# =============================================================================
# SquadClient direct tests
# =============================================================================

@pytest.mark.asyncio
@respx.mock
async def test_squad_account_lookup_success():
    """Successful Squad account-resolve returns the registered name."""
    respx.post(f"{SQUAD_BASE}/payout/account/lookup").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200,
                "success": True,
                "message": "Success",
                "data": {
                    "account_name": "JOHN DOE",
                    "account_number": "0123456789",
                    "bank_code": "058",
                },
            },
        )
    )

    squad = SquadClient(secret_key="sandbox_sk_test", base_url=SQUAD_BASE)
    result = await squad.resolve_account("0123456789", "058")

    assert result.found is True
    assert result.account_name == "JOHN DOE"
    assert result.source == "squad"


@pytest.mark.asyncio
@respx.mock
async def test_squad_simulate_payment_success():
    """Sandbox payment simulation should post the DVA and return success."""
    respx.post(SIMULATE_PAYMENT_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200,
                "success": True,
                "message": "Simulation triggered",
                "data": {
                    "transaction_reference": "SIM-REF-123",
                    "virtual_account_number": "9999888877",
                    "merchant_reference": "ord_demo_test",
                    "merchant_amount": "100.00",
                    "transaction_status": "success",
                },
            },
        )
    )

    squad = SquadClient(secret_key="sandbox_sk_test", base_url=SQUAD_BASE)
    result = await squad.simulate_virtual_account_payment(
        virtual_account_number="9999888877",
        amount_ngn=100,
        merchant_reference="ord_demo_test",
    )

    assert result.success is True
    assert result.virtual_account_number == "9999888877"
    assert result.amount_naira == "100.00"
    assert result.merchant_reference == "ord_demo_test"


@pytest.mark.asyncio
@respx.mock
async def test_squad_account_lookup_not_found():
    """Squad responds 200 with success:false for unknown accounts."""
    respx.post(f"{SQUAD_BASE}/payout/account/lookup").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200,
                "success": False,
                "message": "Account not found",
                "data": None,
            },
        )
    )

    squad = SquadClient(secret_key="sandbox_sk_test", base_url=SQUAD_BASE)
    result = await squad.resolve_account("9999999999", "058")

    assert result.found is False
    assert "not found" in (result.error or "").lower()


@pytest.mark.asyncio
@respx.mock
async def test_squad_account_lookup_handles_5xx():
    """Squad 500 errors don't raise — they return found=False."""
    respx.post(f"{SQUAD_BASE}/payout/account/lookup").mock(
        return_value=httpx.Response(503, json={"message": "Service unavailable"})
    )

    squad = SquadClient(secret_key="sandbox_sk_test", base_url=SQUAD_BASE)
    result = await squad.resolve_account("0123456789", "058")

    assert result.found is False
    assert result.source == "error"


@pytest.mark.asyncio
@respx.mock
async def test_squad_account_lookup_handles_timeout():
    """Network timeouts surface as found=False, source=error."""
    respx.post(f"{SQUAD_BASE}/payout/account/lookup").mock(
        side_effect=httpx.TimeoutException("slow")
    )

    squad = SquadClient(secret_key="sandbox_sk_test", base_url=SQUAD_BASE)
    result = await squad.resolve_account("0123456789", "058")

    assert result.found is False
    assert result.error == "Timeout"


@pytest.mark.asyncio
@respx.mock
async def test_squad_transfer_success():
    respx.post(f"{SQUAD_BASE}/payout/transfer").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200,
                "success": True,
                "message": "Success",
                "data": {
                    "transaction_reference": "ERI-ABC123",
                    "amount": 125_000_000,
                    "account_number": "0123456789",
                    "account_name": "MEDTRUST NIGERIA LIMITED",
                    "transaction_status": "Success",
                    "nip_session_id": "NIP-XYZ",
                },
            },
        )
    )

    squad = SquadClient(secret_key="sandbox_sk_test", base_url=SQUAD_BASE)
    result = await squad.initiate_transfer(
        amount_kobo=125_000_000,
        bank_code="058",
        account_number="0123456789",
        account_name="MEDTRUST NIGERIA LIMITED",
        narration="Test release",
    )

    assert result.success is True
    assert result.transaction_ref == "ERI-ABC123"
    assert result.status == "Success"


@pytest.mark.asyncio
@respx.mock
async def test_squad_transfer_failure():
    respx.post(f"{SQUAD_BASE}/payout/transfer").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 422,
                "success": False,
                "message": "Insufficient balance",
                "data": None,
            },
        )
    )

    squad = SquadClient(secret_key="sandbox_sk_test", base_url=SQUAD_BASE)
    result = await squad.initiate_transfer(
        amount_kobo=125_000_000,
        bank_code="058",
        account_number="0123456789",
        account_name="MEDTRUST NIGERIA LIMITED",
        narration="Test release",
    )

    assert result.success is False
    assert "Insufficient balance" in (result.error or "")


# =============================================================================
# bank.py hybrid path: Squad first, seed fallback
# =============================================================================

@pytest.mark.asyncio
@respx.mock
async def test_bank_uses_squad_when_available():
    """If Squad recognizes an account, we use its data (source='squad')."""
    respx.post(f"{SQUAD_BASE}/payout/account/lookup").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200,
                "success": True,
                "data": {
                    "account_name": "REAL PERSON FROM SQUAD",
                    "account_number": "1234567890",
                    "bank_code": "058",
                },
            },
        )
    )

    result = await bank.resolve_account(
        "1234567890", "058", simulate_latency=False
    )

    assert result.found is True
    assert result.account_name == "REAL PERSON FROM SQUAD"
    assert result.source == "squad"


@pytest.mark.asyncio
@respx.mock
async def test_bank_falls_back_to_seed_when_squad_says_not_found():
    """For our fictional demo account, Squad returns not-found and we fall back."""
    respx.post(f"{SQUAD_BASE}/payout/account/lookup").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200,
                "success": False,
                "message": "Account not found",
                "data": None,
            },
        )
    )

    # 0123456789 / 058 is MedTrust in our seed
    result = await bank.resolve_account(
        "0123456789", "058", simulate_latency=False
    )

    assert result.found is True
    assert result.account_name == "MEDTRUST NIGERIA LIMITED"
    assert result.source == "stub"


@pytest.mark.asyncio
@respx.mock
async def test_bank_falls_back_to_seed_when_squad_5xxs():
    respx.post(f"{SQUAD_BASE}/payout/account/lookup").mock(
        return_value=httpx.Response(503, json={"message": "down"})
    )

    result = await bank.resolve_account(
        "0123456789", "058", simulate_latency=False
    )

    assert result.found is True
    assert result.source == "stub"


@pytest.mark.asyncio
async def test_bank_uses_seed_when_squad_not_configured(monkeypatch):
    """If SQUAD_SECRET_KEY is empty, skip Squad entirely; seed wins."""
    monkeypatch.setattr(settings, "squad_secret_key", "")
    reset_squad_client()

    result = await bank.resolve_account(
        "0123456789", "058", simulate_latency=False
    )

    assert result.found is True
    assert result.source == "stub"


# =============================================================================
# Demo simulation endpoint
# =============================================================================

def test_simulate_payment_flips_pending_to_funded(client):
    # Create an order first
    respx.post(DVA_INITIATE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200,
                "success": True,
                "data": {
                    "is_blocked": False,
                    "account_name": "Eri",
                    "account_number": "9999888877",
                    "expected_amount": "500000.00",
                    "expires_at": "2026-05-15T00:00:00Z",
                    "transaction_reference": "ord_demo_pending",
                    "bank": "GTBank",
                    "currency": "NGN",
                },
            },
        )
    )
    respx.post(SIMULATE_PAYMENT_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200,
                "success": True,
                "message": "Simulation triggered",
                "data": {
                    "transaction_reference": "SIM-REF-111",
                    "virtual_account_number": "9999888877",
                    "merchant_reference": "ord_demo_pending",
                    "merchant_amount": "500000.00",
                    "transaction_status": "success",
                },
            },
        )
    )
    create = client.post(
        "/orders",
        json={
            "supplier_id": "sup_medtrust",
            "buyer_email": "demo@eri.app",
            "amount_ngn": 500_000,
            "description": "Test",
        },
    )
    order_id = create.json()["id"]

    r = client.post(
        "/admin/demo/simulate-payment",
        json={"order_id": order_id},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["new_status"] == "funded"
    assert body["previous_status"] == "pending_payment"

    # Verify the order is now funded
    get_r = client.get(f"/orders/{order_id}")
    assert get_r.json()["status"] == "funded"


@respx.mock
def test_simulate_payment_triggers_squad_simulation(client):
    """The admin demo route should call Squad's simulate-payment endpoint."""
    respx.post(DVA_INITIATE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200,
                "success": True,
                "data": {
                    "is_blocked": False,
                    "account_name": "Eri",
                    "account_number": "9999888877",
                    "expected_amount": "100.00",
                    "expires_at": "2026-05-15T00:00:00Z",
                    "transaction_reference": "ord_admin_sim",
                    "bank": "GTBank",
                    "currency": "NGN",
                },
            },
        )
    )
    simulate_mock = respx.post(SIMULATE_PAYMENT_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200,
                "success": True,
                "message": "Simulation triggered",
                "data": {
                    "transaction_reference": "SIM-REF-123",
                    "virtual_account_number": "9999888877",
                    "merchant_reference": "ord_admin_sim",
                    "merchant_amount": "100.00",
                    "transaction_status": "success",
                },
            },
        )
    )

    create = client.post(
        "/orders",
        json={
            "supplier_id": "sup_medtrust",
            "buyer_email": "buyer@example.com",
            "amount_ngn": 100,
            "description": "Test order",
        },
    )
    order_id = create.json()["id"]

    r = client.post("/admin/demo/simulate-payment", json={"order_id": order_id})
    assert r.status_code == 200
    assert simulate_mock.called
    assert r.json()["new_status"] == "funded"


def test_simulate_payment_works_on_canned_demo_orders(client):
    """Hits a canned demo order — should flip even though it wasn't 'created'."""
    respx.post(SIMULATE_PAYMENT_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200,
                "success": True,
                "message": "Simulation triggered",
                "data": {
                    "transaction_reference": "SIM-REF-222",
                    "virtual_account_number": "9012345678",
                    "merchant_reference": "ord_demo_pending",
                    "merchant_amount": "100000.00",
                    "transaction_status": "success",
                },
            },
        )
    )
    r = client.post(
        "/admin/demo/simulate-payment",
        json={"order_id": "ord_demo_pending"},
    )
    assert r.status_code == 200
    assert r.json()["new_status"] == "funded"


def test_simulate_payment_404_for_unknown_order(client):
    r = client.post(
        "/admin/demo/simulate-payment",
        json={"order_id": "ord_definitely_nonexistent_xyz"},
    )
    assert r.status_code == 404


def test_simulate_payment_409_for_already_released(client):
    """Can't simulate payment on an order in a non-fundable state."""
    # Create + fund + release an order
    respx.post(DVA_INITIATE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200,
                "success": True,
                "data": {
                    "is_blocked": False,
                    "account_name": "Eri",
                    "account_number": "9999888877",
                    "expected_amount": "100000.00",
                    "expires_at": "2026-05-15T00:00:00Z",
                    "transaction_reference": "ord_release_check",
                    "bank": "GTBank",
                    "currency": "NGN",
                },
            },
        )
    )
    respx.post(SIMULATE_PAYMENT_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200,
                "success": True,
                "message": "Simulation triggered",
                "data": {
                    "transaction_reference": "SIM-REF-333",
                    "virtual_account_number": "9999888877",
                    "merchant_reference": "ord_release_check",
                    "merchant_amount": "100000.00",
                    "transaction_status": "success",
                },
            },
        )
    )
    create = client.post(
        "/orders",
        json={
            "supplier_id": "sup_medtrust",
            "buyer_email": "demo@eri.app",
            "amount_ngn": 100_000,
            "description": "Test order for status check",
        },
    )
    order_id = create.json()["id"]
    client.post("/admin/demo/simulate-payment", json={"order_id": order_id})

    # Mark released by hand (using the release endpoint requires Squad mock, so
    # we just mutate the order store directly for this status test)
    from app.routers.orders import _ORDERS
    _ORDERS[order_id]["status"] = "released"

    r = client.post(
        "/admin/demo/simulate-payment", json={"order_id": order_id}
    )
    assert r.status_code == 409


# =============================================================================
# Release endpoint hits Squad Transfer API
# =============================================================================

@respx.mock
def test_release_endpoint_calls_squad_transfer(client):
    """When releasing a funded order, the route should POST to Squad transfer."""
    # Mock Squad transfer endpoint
    transfer_mock = respx.post(f"{SQUAD_BASE}/payout/transfer").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200,
                "success": True,
                "data": {
                    "transaction_reference": "ERI-MOCK-REF",
                    "amount": 50_000_000,
                    "transaction_status": "Success",
                },
            },
        )
    )

    # Create + fund an order
    create = client.post(
        "/orders",
        json={
            "supplier_id": "sup_medtrust",
            "buyer_email": "demo@eri.app",
            "amount_ngn": 500_000,
            "description": "Test",
        },
    )
    order_id = create.json()["id"]
    client.post("/admin/demo/simulate-payment", json={"order_id": order_id})

    # Release it
    r = client.post(
        f"/orders/{order_id}/release",
        json={"confirmation_note": "All good"},
    )
    assert r.status_code == 200
    assert r.json()["new_status"] == "released"
    assert transfer_mock.called  # Squad was actually called
    # Message should reference Squad's transfer ref
    assert "ERI-MOCK-REF" in r.json()["message"]


@respx.mock
def test_release_handles_squad_failure_gracefully(client):
    """If Squad Transfer fails, release still completes locally (demo continuity)."""
    respx.post(f"{SQUAD_BASE}/payout/transfer").mock(
        return_value=httpx.Response(503, json={"message": "down"})
    )

    create = client.post(
        "/orders",
        json={
            "supplier_id": "sup_medtrust",
            "buyer_email": "demo@eri.app",
            "amount_ngn": 100_000,
            "description": "Test order for release",
        },
    )
    order_id = create.json()["id"]
    client.post("/admin/demo/simulate-payment", json={"order_id": order_id})

    r = client.post(f"/orders/{order_id}/release", json={})
    assert r.status_code == 200
    assert r.json()["new_status"] == "released"


# =============================================================================
# Dynamic Virtual Account (DVA) — initiate + auto-refill
# =============================================================================

DVA_INITIATE_URL = f"{SQUAD_BASE}/virtual-account/initiate-dynamic-virtual-account"
DVA_CREATE_URL = f"{SQUAD_BASE}/virtual-account/create-dynamic-virtual-account"


@pytest.mark.asyncio
@respx.mock
async def test_dva_initiate_success_returns_account_number():
    respx.post(DVA_INITIATE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200, "success": True, "message": "Success",
                "data": {
                    "is_blocked": False,
                    "account_name": "Eri",
                    "account_number": "5677645152",
                    "expected_amount": "1250000.00",
                    "expires_at": "2026-05-15T21:26:27.923Z",
                    "transaction_reference": "ord_abc123",
                    "bank": "GTBank",
                    "currency": "NGN",
                },
            },
        )
    )

    squad = SquadClient(secret_key="sandbox_sk_test", base_url=SQUAD_BASE)
    result = await squad.initiate_dynamic_va(
        amount_kobo=125_000_000,
        transaction_ref="ord_abc123",
        email="buyer@example.com",
    )

    assert result.success is True
    assert result.account_number == "5677645152"
    assert result.bank == "GTBank"
    assert result.refilled_pool is False


@pytest.mark.asyncio
@respx.mock
async def test_dva_initiate_autorefills_when_pool_empty():
    """If pool is empty, the client auto-creates an account and retries once."""
    # First initiate call: 404 "Unable to retrieve" (pool empty)
    # Second initiate call (after refill): 200 success
    initiate_route = respx.post(DVA_INITIATE_URL).mock(
        side_effect=[
            httpx.Response(
                404,
                json={
                    "status": 404,
                    "success": False,
                    "message": "Unable to retrieve a virtual account",
                    "data": {},
                },
            ),
            httpx.Response(
                200,
                json={
                    "status": 200, "success": True, "message": "Success",
                    "data": {
                        "is_blocked": False,
                        "account_name": "Eri",
                        "account_number": "1111111111",
                        "expected_amount": "100.00",
                        "expires_at": "2026-05-15T21:26:27.923Z",
                        "transaction_reference": "ord_refill",
                        "bank": "GTBank",
                        "currency": "NGN",
                    },
                },
            ),
        ]
    )
    # The refill call between them: 200 success
    create_route = respx.post(DVA_CREATE_URL).mock(
        return_value=httpx.Response(
            200,
            json={"status": 200, "success": True, "message": "Success", "data": {}},
        )
    )

    squad = SquadClient(secret_key="sandbox_sk_test", base_url=SQUAD_BASE)
    result = await squad.initiate_dynamic_va(
        amount_kobo=10_000,
        transaction_ref="ord_refill",
        email="buyer@example.com",
    )

    assert result.success is True
    assert result.account_number == "1111111111"
    assert result.refilled_pool is True
    assert initiate_route.call_count == 2  # 1 fail + 1 retry
    assert create_route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_dva_initiate_gives_up_after_one_refill():
    """If even the refilled pool can't satisfy, return failure — no infinite loop."""
    respx.post(DVA_INITIATE_URL).mock(
        return_value=httpx.Response(
            404,
            json={
                "status": 404, "success": False,
                "message": "Unable to retrieve a virtual account",
                "data": {},
            },
        )
    )
    respx.post(DVA_CREATE_URL).mock(
        return_value=httpx.Response(
            200,
            json={"status": 200, "success": True, "data": {}},
        )
    )

    squad = SquadClient(secret_key="sandbox_sk_test", base_url=SQUAD_BASE)
    result = await squad.initiate_dynamic_va(
        amount_kobo=10_000,
        transaction_ref="ord_no_pool",
        email="buyer@example.com",
    )

    assert result.success is False
    assert "Unable to retrieve" in (result.error or "")


@pytest.mark.asyncio
@respx.mock
async def test_create_pool_account_success():
    respx.post(DVA_CREATE_URL).mock(
        return_value=httpx.Response(
            200,
            json={"status": 200, "success": True, "message": "Success", "data": {}},
        )
    )
    squad = SquadClient(secret_key="sandbox_sk_test", base_url=SQUAD_BASE)
    assert await squad.create_pool_account() is True


@pytest.mark.asyncio
@respx.mock
async def test_create_pool_account_failure():
    respx.post(DVA_CREATE_URL).mock(
        return_value=httpx.Response(503, json={"message": "down"})
    )
    squad = SquadClient(secret_key="sandbox_sk_test", base_url=SQUAD_BASE)
    assert await squad.create_pool_account() is False


# =============================================================================
# Create-order endpoint hits Squad DVA
# =============================================================================

@respx.mock
def test_create_order_uses_real_squad_dva(client):
    """POST /orders should call Squad DVA and use the returned account number."""
    dva_route = respx.post(DVA_INITIATE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200, "success": True,
                "data": {
                    "is_blocked": False,
                    "account_name": "Eri",
                    "account_number": "9999888877",
                    "expected_amount": "100000.00",
                    "expires_at": "2026-05-15T00:00:00Z",
                    "transaction_reference": "will-be-replaced",
                    "bank": "GTBank",
                    "currency": "NGN",
                },
            },
        )
    )

    r = client.post(
        "/orders",
        json={
            "supplier_id": "sup_medtrust",
            "buyer_email": "buyer@example.com",
            "amount_ngn": 100_000,
            "description": "Test order with real DVA",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["virtual_account_number"] == "9999888877"
    assert body["virtual_account_bank"] == "GTBank"
    assert dva_route.called


@respx.mock
def test_create_order_falls_back_when_squad_dva_fails(client):
    """If Squad DVA returns an error, order still gets created with a fallback account."""
    respx.post(DVA_INITIATE_URL).mock(
        return_value=httpx.Response(503, json={"message": "Squad down"})
    )

    r = client.post(
        "/orders",
        json={
            "supplier_id": "sup_medtrust",
            "buyer_email": "buyer@example.com",
            "amount_ngn": 100_000,
            "description": "Test order with Squad down",
        },
    )
    assert r.status_code == 201
    body = r.json()
    # Fallback uses a 10-digit numeric string
    assert body["virtual_account_number"] is not None
    assert len(body["virtual_account_number"]) == 10


def test_create_order_requires_buyer_email(client):
    """Schema change: buyer_email is now required."""
    r = client.post(
        "/orders",
        json={
            "supplier_id": "sup_medtrust",
            "amount_ngn": 100_000,
            "description": "Test order without email",
            # buyer_email intentionally missing
        },
    )
    assert r.status_code == 422


# =============================================================================
# Webhook handler flips orders to funded
# =============================================================================

@respx.mock
def test_webhook_flips_order_to_funded(client):
    """Squad webhook with a success event should flip the matching order."""
    # Mock DVA so we can create an order
    respx.post(DVA_INITIATE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200, "success": True,
                "data": {
                    "is_blocked": False,
                    "account_name": "Eri",
                    "account_number": "9999888877",
                    "expected_amount": "100000.00",
                    "expires_at": "2026-05-15T00:00:00Z",
                    "transaction_reference": "ord_for_webhook",
                    "bank": "GTBank",
                    "currency": "NGN",
                },
            },
        )
    )

    create = client.post(
        "/orders",
        json={
            "supplier_id": "sup_medtrust",
            "buyer_email": "buyer@example.com",
            "amount_ngn": 100_000,
            "description": "Test for webhook flow",
        },
    )
    order_id = create.json()["id"]

    # Now fire a webhook as if Squad confirmed payment landed
    wh = client.post(
        "/webhooks/squad",
        json={
            "Event": "successful_transaction",
            "Data": {
                "transaction_ref": order_id,
                "transaction_status": "Success",
                "principal_amount": "100000.00",
            },
        },
    )
    assert wh.status_code == 200

    # Order should now be funded
    get_r = client.get(f"/orders/{order_id}")
    assert get_r.json()["status"] == "funded"


def test_webhook_for_unknown_ref_is_ignored(client):
    """Webhook with a ref we don't know about returns 200 but does nothing."""
    r = client.post(
        "/webhooks/squad",
        json={
            "Event": "successful_transaction",
            "Data": {
                "transaction_ref": "ord_does_not_exist_xyz",
                "transaction_status": "Success",
            },
        },
    )
    assert r.status_code == 200
    assert r.json()["received"] is True
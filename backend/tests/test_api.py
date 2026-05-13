"""
End-to-end API tests for the FastAPI server.

Uses FastAPI's TestClient so we exercise the full routing layer,
schema validation, and serialization — not just the underlying engines.

Run:
    pytest tests/test_api.py -v
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.integrations import bank, cac, court_records, nafdac
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_all_caches():
    bank.clear_cache()
    cac.clear_cache()
    court_records.clear_cache()
    nafdac.clear_cache()
    yield
    bank.clear_cache()
    cac.clear_cache()
    court_records.clear_cache()
    nafdac.clear_cache()


# -----------------------------------------------------------------------------
# Health
# -----------------------------------------------------------------------------

def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "timestamp" in body


# -----------------------------------------------------------------------------
# Supplier verification — REAL implementation
# -----------------------------------------------------------------------------

def test_verify_supplier_green(client):
    r = client.post(
        "/verify/supplier",
        json={
            "business_name": "MedTrust Nigeria",
            "rc_number": "1842301",
            "bank_account_number": "0123456789",
            "bank_code": "058",
            "supplier_type": "healthcare",
            "expected_nafdac_number": "04-9412",
            "expected_manufacturer": "Novartis",
            "expected_product": "Coartem",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "green"
    assert body["score"] >= 80
    assert len(body["checks"]) == 6  # CAC, bank, court, NAFDAC, invoice, history


def test_verify_supplier_red(client):
    r = client.post(
        "/verify/supplier",
        json={
            "business_name": "QuickMeds Wholesale",
            "rc_number": "9999999",
            "bank_account_number": "9988776655",
            "bank_code": "058",
            "supplier_type": "healthcare",
            "expected_nafdac_number": "04-6433",
            "expected_manufacturer": "Novartis",
            "expected_product": "Coartem",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "red"
    assert body["score"] < 50
    # The demo gotcha must surface specific concerns
    concerns_text = " ".join(body["raw_concerns"]).lower()
    assert "fraud" in concerns_text
    assert "manufacturer" in concerns_text or "proguanil" in concerns_text


def test_verify_supplier_rejects_invalid_input(client):
    """Missing required fields should return 422, not 500."""
    r = client.post(
        "/verify/supplier",
        json={
            "business_name": "Some Co",
            # Missing rc_number, bank fields
        },
    )
    assert r.status_code == 422


def test_verify_supplier_general_skips_nafdac(client):
    r = client.post(
        "/verify/supplier",
        json={
            "business_name": "MedTrust Nigeria",
            "rc_number": "1842301",
            "bank_account_number": "0123456789",
            "bank_code": "058",
            "supplier_type": "general",
        },
    )
    assert r.status_code == 200
    body = r.json()
    by_name = {c["name"]: c for c in body["checks"]}
    assert by_name["NAFDAC Registration"]["status"] == "unverified"


# -----------------------------------------------------------------------------
# Delivery verification — STUB
# -----------------------------------------------------------------------------

def test_verify_delivery_stub_returns_green(client):
    """Default stub behavior — returns green/match."""
    r = client.post(
        "/verify/delivery/ord_test_123",
        files={
            "quote_image": ("quote.jpg", b"fake_image_bytes", "image/jpeg"),
            "delivery_image": ("delivery.jpg", b"fake_image_bytes", "image/jpeg"),
        },
        data={"expected_nafdac": "04-9412"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "green"
    assert body["match_confidence"] > 0.5


def test_verify_delivery_stub_returns_red_for_fail_suffix(client):
    """Frontend can suffix '-fail' to test the failure UI."""
    r = client.post(
        "/verify/delivery/ord_test-fail",
        files={
            "quote_image": ("quote.jpg", b"fake", "image/jpeg"),
            "delivery_image": ("delivery.jpg", b"fake", "image/jpeg"),
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "red"
    assert len(body["concerns"]) > 0


# -----------------------------------------------------------------------------
# Orders — STUBS
# -----------------------------------------------------------------------------

def test_create_order_returns_virtual_account(client):
    r = client.post(
        "/orders",
        json={
            "supplier_id": "sup_medtrust",
            "amount_ngn": 1_250_000,
            "description": "50 cartons of Coartem 20/120 tablets",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending_payment"
    assert body["virtual_account_number"] is not None
    assert len(body["virtual_account_number"]) == 10
    assert body["amount_ngn"] == 1_250_000
    assert body["trust_score_at_creation"] == 100


def test_get_order_returns_created_order(client):
    create = client.post(
        "/orders",
        json={
            "supplier_id": "sup_medtrust",
            "amount_ngn": 500_000,
            "description": "Test order",
        },
    )
    order_id = create.json()["id"]

    r = client.get(f"/orders/{order_id}")
    assert r.status_code == 200
    assert r.json()["id"] == order_id


def test_get_order_returns_404_for_unknown(client):
    r = client.get("/orders/ord_nonexistent")
    assert r.status_code == 404


def test_get_order_returns_canned_demo_orders(client):
    """Demo helper IDs should return pre-built orders without creating first."""
    r = client.get("/orders/ord_demo_funded")
    assert r.status_code == 200
    assert r.json()["status"] == "funded"

    r2 = client.get("/orders/ord_demo_disputed")
    assert r2.status_code == 200
    assert r2.json()["status"] == "disputed"


def test_release_order_requires_funded_status(client):
    """Can't release a pending_payment order — only funded or delivered."""
    create = client.post(
        "/orders",
        json={
            "supplier_id": "sup_medtrust",
            "amount_ngn": 100_000,
            "description": "Test",
        },
    )
    order_id = create.json()["id"]

    # Status is pending_payment — release should fail
    r = client.post(f"/orders/{order_id}/release", json={})
    assert r.status_code == 409


def test_dispute_order_requires_funded_status(client):
    create = client.post(
        "/orders",
        json={
            "supplier_id": "sup_medtrust",
            "amount_ngn": 100_000,
            "description": "Test",
        },
    )
    order_id = create.json()["id"]

    r = client.post(
        f"/orders/{order_id}/dispute",
        json={
            "reason": "not_delivered",
            "description": "Supplier ghosted after taking payment",
        },
    )
    # Pending order can't be disputed yet
    assert r.status_code == 409


# -----------------------------------------------------------------------------
# Webhooks
# -----------------------------------------------------------------------------

def test_squad_webhook_acknowledges(client):
    r = client.post(
        "/webhooks/squad",
        json={
            "event": "charge.success",
            "data": {"transaction_ref": "txn_test_123", "amount": 1_250_000},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["received"] is True
    assert body["event"] == "charge.success"


# -----------------------------------------------------------------------------
# Admin
# -----------------------------------------------------------------------------

def test_admin_metrics_returns_engine_3_stats(client):
    r = client.get("/admin/metrics")
    assert r.status_code == 200
    body = r.json()
    assert "anomaly_engine" in body
    assert "cache_sizes" in body
    # Cache sizes should be present for all four integrations
    assert set(body["cache_sizes"].keys()) == {"cac", "nafdac", "court_records", "bank"}


# -----------------------------------------------------------------------------
# OpenAPI / Swagger
# -----------------------------------------------------------------------------

def test_openapi_schema_is_valid(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert schema["openapi"].startswith("3.")
    # All our main routes should be in the schema
    paths = schema["paths"]
    for route in ["/health", "/verify/supplier", "/orders", "/admin/metrics", "/webhooks/squad"]:
        assert route in paths, f"Route {route} missing from OpenAPI schema"


def test_swagger_ui_loads(client):
    r = client.get("/docs")
    assert r.status_code == 200
    assert "swagger" in r.text.lower()


def test_redoc_loads(client):
    r = client.get("/redoc")
    assert r.status_code == 200
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
from app.settings import settings


def _make_order_payload(
    supplier_name: str,
    items: list[dict],
    grand_total: float,
    discount: float = 0.0,
    vat: float = 0.0,
    buyer_email: str = "demo@eri.app",
) -> dict:
    """Build a CreateOrderFromInvoiceRequest JSON dict for tests."""
    line_items = [
        {
            "description": i["description"],
            "nafdac_registration": i.get("nafdac"),
            "manufacturer": i.get("manufacturer"),
            "batch_number": None,
            "expiry_date": None,
            "quantity": i["qty"],
            "unit_price": i["unit_price"],
            "line_total": i["qty"] * i["unit_price"],
        }
        for i in items
    ]
    subtotal = sum(li["line_total"] for li in line_items)
    return {
        "supplier": {
            "name": supplier_name,
            "rc_number": "RC-123456",
            "nafdac_premises_license": None,
            "address": "1 Test Street, Lagos",
            "bank_account": {
                "bank_name": "GTBank",
                "account_name": supplier_name.upper(),
                "account_number": "0123456789",
            },
        },
        "buyer": {"name": "Test Buyer", "rc_number": None, "address": None},
        "line_items": line_items,
        "totals": {
            "subtotal": subtotal,
            "discount": discount,
            "vat": vat,
            "grand_total": grand_total,
            "currency": "NGN",
        },
        "buyer_email": buyer_email,
        "source_document_id": None,
        "expected_delivery_days": 14,
    }


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_all_caches(monkeypatch):
    bank.clear_cache()
    cac.clear_cache()
    court_records.clear_cache()
    nafdac.clear_cache()
    monkeypatch.setattr(settings, "squad_webhook_secret", "")
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

def test_verify_delivery_endpoint_responds(client, monkeypatch):
    """The delivery endpoint should accept image uploads and return a verdict.

    We don't hit the real Gemini API in this test — that's covered by
    test_product_cv.py. Here we just verify the routing + schema layer.
    """
    # Force the engine's LLM client to a stub so we don't need GEMINI_API_KEY
    from app.engines import product_cv as engine_module

    class _StubLLM:
        def extract_registration_number(self, *a, **kw):
            return None
        def adjudicate_products(self, *a, **kw):
            return {
                "match": True,
                "confidence": 0.9,
                "delivered_name": "Coartem",
                "delivered_variant": "20/120 mg",
                "delivered_registration": "04-9412",
                "differences": [],
                "concerns": [],
            }

    monkeypatch.setattr(engine_module, "_get_llm_client", lambda: _StubLLM())

    # Generate a real small image for upload
    from PIL import Image
    import io
    img = Image.new("RGB", (100, 100), "white")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    img_bytes = buf.getvalue()

    r = client.post(
        "/verify/delivery/ord_test_real",
        files={
            "quote_image": ("quote.png", img_bytes, "image/png"),
            "delivery_image": ("delivery.png", img_bytes, "image/png"),
        },
        data={
            "expected_nafdac": "04-9412",
            "expected_manufacturer": "Novartis",
            "expected_product": "Coartem",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["order_id"] == "ord_test_real"
    assert body["verdict"] in {"green", "amber", "red"}
    assert "concerns" in body


def test_verify_delivery_rejects_missing_images(client):
    """Empty upload should 422 (validation) or 400 (our explicit check)."""
    r = client.post(
        "/verify/delivery/ord_test",
        # Don't include any files
        data={"expected_nafdac": "04-9412"},
    )
    assert r.status_code in {400, 422}


# -----------------------------------------------------------------------------
# Orders — STUBS
# -----------------------------------------------------------------------------

def test_create_order_returns_virtual_account(client):
    r = client.post(
        "/orders",
        json=_make_order_payload(
            supplier_name="MedTrust Nigeria Limited",
            items=[{"description": "Coartem 20/120 mg", "nafdac": "04-9412",
                    "qty": 100, "unit_price": 12500}],
            grand_total=1_250_000,
        ),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending_payment"
    assert body["virtual_account_number"] is not None
    assert len(body["virtual_account_number"]) == 10
    assert body["amount_ngn"] == 1_250_000
    assert body["verification_status"] == "pending"
    assert body["line_items"] is not None
    assert len(body["line_items"]) == 1


def test_get_order_returns_created_order(client):
    create = client.post(
        "/orders",
        json=_make_order_payload(
            supplier_name="MedTrust Nigeria Limited",
            items=[{"description": "Test product", "qty": 10, "unit_price": 50_000}],
            grand_total=500_000,
        ),
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
    create = client.post(
        "/orders",
        json=_make_order_payload(
            supplier_name="MedTrust Nigeria Limited",
            items=[{"description": "Test", "qty": 1, "unit_price": 100_000}],
            grand_total=100_000,
        ),
    )
    order_id = create.json()["id"]
    r = client.post(f"/orders/{order_id}/release", json={})
    assert r.status_code == 409


def test_dispute_order_requires_funded_status(client):
    create = client.post(
        "/orders",
        json=_make_order_payload(
            supplier_name="MedTrust Nigeria Limited",
            items=[{"description": "Test", "qty": 1, "unit_price": 100_000}],
            grand_total=100_000,
        ),
    )
    order_id = create.json()["id"]
    r = client.post(
        f"/orders/{order_id}/dispute",
        json={"reason": "not_delivered", "description": "Supplier ghosted after taking payment"},
    )
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


# -----------------------------------------------------------------------------
# Invoice extraction
# -----------------------------------------------------------------------------

def test_extract_invoice_happy_path(client, sample_invoice_pdf, monkeypatch):
    """LLM extracts structured data; we mock parse_invoice to avoid Gemini calls."""
    import sys
    import types

    _stub_result = {
        "supplier": {
            "name": "MedixPharma Limited",
            "rc_number": "RC-654321",
            "nafdac_premises_license": None,
            "address": "5 Pharma Way, Ikeja, Lagos",
            "bank_account": {
                "bank_name": "Zenith Bank",
                "account_name": "MEDIXPHARMA LIMITED",
                "account_number": "1234567890",
            },
        },
        "buyer": {"name": "St. Michael Pharmacy", "rc_number": None, "address": None},
        "invoice_metadata": {
            "invoice_number": "INV-2026-0847",
            "issue_date": "2026-05-15",
            "due_date": None,
            "payment_terms": "Net 30",
        },
        "line_items": [
            {
                "description": "Coartem 20/120 mg tablets",
                "nafdac_registration": "04-9412",
                "manufacturer": "Novartis",
                "batch_number": "BCH-001",
                "expiry_date": "2028-06-30",
                "quantity": 100,
                "unit_price": 12000,
                "line_total": 1200000,
            }
        ],
        "totals": {
            "subtotal": 1200000,
            "discount": 0,
            "vat": 0,
            "grand_total": 1200000,
            "currency": "NGN",
        },
        "extraction_confidence": 0.92,
        "raw_text_sample": "MEDIXPHARMA LIMITED Invoice INV-2026-0847",
    }

    class _StubLLMClient:
        def parse_invoice(self, *a, **kw):
            return _stub_result

    # Inject a fake llm module so the lazy import inside the route handler works
    fake_llm = types.ModuleType("app.integrations.llm")
    fake_llm.LLMClient = _StubLLMClient
    monkeypatch.setitem(sys.modules, "app.integrations.llm", fake_llm)

    r = client.post(
        "/orders/extract-invoice",
        files={"file": ("invoice.pdf", sample_invoice_pdf, "application/pdf")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["supplier"]["name"] == "MedixPharma Limited"
    assert len(body["line_items"]) == 1
    assert body["line_items"][0]["nafdac_registration"] == "04-9412"
    assert body["totals"]["grand_total"] == 1_200_000
    assert body["extraction_confidence"] == 0.92


def test_extract_invoice_too_large(client):
    """Files over 10MB must be rejected before reaching the LLM."""
    big_pdf = b"%PDF-1.4\n" + b"x" * (10 * 1024 * 1024 + 1)
    r = client.post(
        "/orders/extract-invoice",
        files={"file": ("big.pdf", big_pdf, "application/pdf")},
    )
    assert r.status_code == 413


def test_extract_invoice_non_pdf(client):
    """Non-PDF uploads must be rejected with 415."""
    r = client.post(
        "/orders/extract-invoice",
        files={"file": ("invoice.jpg", b"\xff\xd8\xff\xe0fake jpeg", "image/jpeg")},
    )
    assert r.status_code == 415


def test_extract_invoice_llm_failure(client, sample_invoice_pdf, monkeypatch):
    """LLM failure surfaces as HTTP 422 with extraction_failed error."""
    import sys
    import types

    class _BrokenLLMClient:
        def parse_invoice(self, *a, **kw):
            raise RuntimeError("Gemini API quota exceeded")

    # Inject a fake llm module so the lazy import inside the route handler works
    fake_llm = types.ModuleType("app.integrations.llm")
    fake_llm.LLMClient = _BrokenLLMClient
    monkeypatch.setitem(sys.modules, "app.integrations.llm", fake_llm)

    r = client.post(
        "/orders/extract-invoice",
        files={"file": ("invoice.pdf", sample_invoice_pdf, "application/pdf")},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["detail"]["error"] == "extraction_failed"
    assert "Gemini API quota exceeded" in body["detail"]["detail"]


# -----------------------------------------------------------------------------
# Order creation — new multi-line schema
# -----------------------------------------------------------------------------

def test_create_order_n1_line_item(client):
    r = client.post(
        "/orders",
        json=_make_order_payload(
            supplier_name="MedTrust Nigeria Limited",
            items=[{"description": "Coartem 20/120 mg", "nafdac": "04-9412",
                    "qty": 100, "unit_price": 12500}],
            grand_total=1_250_000,
        ),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["amount_ngn"] == 1_250_000
    assert len(body["line_items"]) == 1
    assert body["verification_status"] == "pending"


def test_create_order_n4_line_items(client):
    r = client.post(
        "/orders",
        json=_make_order_payload(
            supplier_name="MedixPharma Limited",
            items=[
                {"description": "Coartem 20/120 mg",      "qty": 100, "unit_price": 12000},
                {"description": "Augmentin 625mg",         "qty": 200, "unit_price": 850},
                {"description": "Emzor Paracetamol 500mg", "qty": 500, "unit_price": 120},
                {"description": "Surgical Gloves Box",     "qty": 50,  "unit_price": 4500},
            ],
            grand_total=1_655_000,
        ),
    )
    assert r.status_code == 201
    body = r.json()
    assert len(body["line_items"]) == 4
    assert body["amount_ngn"] == 1_655_000


def test_create_order_grand_total_mismatch(client):
    """Server must reject when submitted grand_total doesn't match line items."""
    payload = _make_order_payload(
        supplier_name="Dodgy Supplier",
        items=[{"description": "Product A", "qty": 10, "unit_price": 5000}],
        grand_total=999_999,  # real total is 50_000 — massive mismatch
    )
    r = client.post("/orders", json=payload)
    assert r.status_code == 400
    body = r.json()
    assert body["detail"]["error"] == "grand_total_mismatch"


def test_create_order_empty_line_items(client):
    """Zero line items must fail schema validation (422)."""
    payload = _make_order_payload(
        supplier_name="Test",
        items=[{"description": "placeholder", "qty": 1, "unit_price": 1000}],
        grand_total=1000,
    )
    payload["line_items"] = []  # override to empty
    r = client.post("/orders", json=payload)
    assert r.status_code == 422
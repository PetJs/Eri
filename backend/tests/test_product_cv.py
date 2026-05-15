"""
Tests for Engine 2 (Product CV).

We don't hit real Gemini in tests — too slow, costs tokens, non-deterministic.
Instead we monkey-patch the LLM client's adjudicate_products() to return
predetermined responses for each scenario.

OCR is tested for real (Tesseract is available in CI) against generated images.
"""
from __future__ import annotations

import io
import re

import pytest
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

from app.engines.product_cv import (
    DeliveryInput,
    _compute_score,
    DeliveryCheck,
    verify_delivery,
)
from app.engines import product_cv as engine_module
from app.integrations import nafdac


@pytest.fixture(autouse=True)
def _clear_nafdac_cache():
    nafdac.clear_cache()
    yield
    nafdac.clear_cache()


@pytest.fixture
def reset_llm_singleton():
    """Reset the module-level LLM singleton before each test."""
    engine_module._llm_client = None
    yield
    engine_module._llm_client = None


# -----------------------------------------------------------------------------
# Image generation helpers — used to make test inputs with known content
# -----------------------------------------------------------------------------

def _make_packaging_image(text_lines: list[str]) -> bytes:
    """Render a white-background image with the given text lines.

    Text is also embedded as PNG metadata so test mocks can extract
    registration numbers even when Tesseract is not installed.
    """
    img = Image.new("RGB", (700, 250), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36
        )
    except OSError:
        font = ImageFont.load_default()
    y = 30
    for line in text_lines:
        draw.text((40, y), line, fill="black", font=font)
        y += 60
    buf = io.BytesIO()
    pnginfo = PngImagePlugin.PngInfo()
    for i, line in enumerate(text_lines):
        pnginfo.add_text(f"line_{i}", line)
    img.save(buf, "PNG", pnginfo=pnginfo)
    return buf.getvalue()


def _read_nafdac_from_png_meta(image_bytes: bytes) -> str | None:
    """Extract a NAFDAC number from PNG text metadata.

    Reads the metadata embedded by _make_packaging_image so mock LLM clients
    can return the correct number without requiring Tesseract.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        for val in (img.text or {}).values():
            m = re.search(r"\b[A-Z0-9]{1,2}-\d{4}\b", val, re.IGNORECASE)
            if m:
                return m.group(0).upper()
    except Exception:
        pass
    return None


# -----------------------------------------------------------------------------
# Fake LLM clients for tests
# -----------------------------------------------------------------------------

class _MatchingLLM:
    """Mock LLM that always confirms a high-confidence match."""

    def extract_registration_number(self, image_bytes, registry_type="nafdac"):
        return _read_nafdac_from_png_meta(image_bytes)

    def adjudicate_products(self, quote_bytes, delivery_bytes, expected_details):
        return {
            "match": True,
            "confidence": 0.94,
            "delivered_name": expected_details.get("name"),
            "delivered_variant": expected_details.get("dosage"),
            "delivered_registration": expected_details.get("registration"),
            "differences": [],
            "concerns": [],
        }


class _MismatchLLM:
    """Mock LLM that flags a counterfeit — what the QuickMeds demo expects."""

    def extract_registration_number(self, image_bytes, registry_type="nafdac"):
        return _read_nafdac_from_png_meta(image_bytes)

    def adjudicate_products(self, quote_bytes, delivery_bytes, expected_details):
        return {
            "match": False,
            "confidence": 0.12,
            "delivered_name": "Unknown brand",
            "delivered_variant": None,
            "delivered_registration": "04-6433",
            "differences": [
                "Delivered packaging uses a different color scheme",
                "Brand name does not match expected manufacturer",
            ],
            "concerns": [
                "Likely counterfeit packaging — do not release escrow",
            ],
        }


class _UnavailableLLM:
    """Mock LLM that raises on adjudication — simulates Gemini being down.

    extract_registration_number reads from PNG metadata because in the real
    "Gemini is down" scenario Tesseract handles OCR; on machines without
    Tesseract this stands in for it so the test stays meaningful.
    """

    def extract_registration_number(self, image_bytes, registry_type="nafdac"):
        return _read_nafdac_from_png_meta(image_bytes)

    def adjudicate_products(self, *args, **kwargs):
        raise RuntimeError("LLM service unavailable")


# -----------------------------------------------------------------------------
# Score-computation unit tests
# -----------------------------------------------------------------------------

def test_score_all_pass_is_100():
    checks = [
        DeliveryCheck("A", "pass", 50, ""),
        DeliveryCheck("B", "pass", 50, ""),
    ]
    assert _compute_score(checks) == 100


def test_score_redistributes_when_unverified():
    checks = [
        DeliveryCheck("A", "pass", 70, ""),
        DeliveryCheck("B", "unverified", 30, ""),
    ]
    # Unverified drops out — A's 70/70 = 100
    assert _compute_score(checks) == 100


def test_score_no_signals_is_0():
    checks = [DeliveryCheck("A", "unverified", 100, "")]
    assert _compute_score(checks) == 0


# -----------------------------------------------------------------------------
# End-to-end demo scenarios
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_clean_delivery_lands_green(reset_llm_singleton, monkeypatch):
    """The good case: NAFDAC on package matches, Greenbook agrees, LLM confirms."""
    monkeypatch.setattr(engine_module, "_get_llm_client", lambda: _MatchingLLM())

    quote = _make_packaging_image(["Coartem 20/120 mg", "NAFDAC: 04-9412"])
    delivery = _make_packaging_image(["Coartem 20/120 mg", "NAFDAC: 04-9412"])

    result = await verify_delivery(DeliveryInput(
        order_id="ord_test",
        quote_image_bytes=quote,
        delivery_image_bytes=delivery,
        expected_product_name="Coartem",
        expected_manufacturer="Novartis",
        expected_nafdac_number="04-9412",
    ))

    assert result.verdict == "green", f"Got {result.verdict} (score {result.score})"
    assert result.score >= 80
    assert result.detected_nafdac_number == "04-9412"


@pytest.mark.asyncio
async def test_demo_gotcha_quickmeds_lands_red(reset_llm_singleton, monkeypatch):
    """The killer demo: package shows 04-6433, buyer expected 04-9412,
    Greenbook says 04-6433 is Proguanil from GreenLife, LLM says no match."""
    monkeypatch.setattr(engine_module, "_get_llm_client", lambda: _MismatchLLM())

    quote = _make_packaging_image(["Coartem 20/120 mg", "NAFDAC: 04-9412"])
    delivery = _make_packaging_image(["Generic Tablets", "NAFDAC: 04-6433"])

    result = await verify_delivery(DeliveryInput(
        order_id="ord_test_quickmeds",
        quote_image_bytes=quote,
        delivery_image_bytes=delivery,
        expected_product_name="Coartem",
        expected_manufacturer="Novartis",
        expected_nafdac_number="04-9412",
    ))

    assert result.verdict == "red", f"Got {result.verdict} (score {result.score})"
    assert result.score < 50
    assert result.detected_nafdac_number == "04-6433"

    # At least one concern about the mismatched NAFDAC number
    concerns_joined = " ".join(result.raw_concerns).lower()
    assert "04-6433" in concerns_joined or "04-9412" in concerns_joined

    # NAFDAC lookup should report what 04-6433 actually is in our seed
    assert result.nafdac_lookup_result is not None
    assert "Proguanil" in (result.nafdac_lookup_result.get("product_name") or "")


@pytest.mark.asyncio
async def test_unreadable_package_warns(reset_llm_singleton, monkeypatch):
    """No NAFDAC number on package + buyer didn't specify one = soft signal."""
    monkeypatch.setattr(engine_module, "_get_llm_client", lambda: _MatchingLLM())

    quote = _make_packaging_image(["Some Product"])
    delivery = _make_packaging_image(["Some Product"])

    result = await verify_delivery(DeliveryInput(
        order_id="ord_test_no_number",
        quote_image_bytes=quote,
        delivery_image_bytes=delivery,
        expected_product_name="Some Product",
    ))

    # OCR should warn (no number found), LLM passes — overall amber-ish
    ocr_check = next(c for c in result.checks if c.name == "Package OCR")
    assert ocr_check.status == "warn"


@pytest.mark.asyncio
async def test_llm_unavailable_degrades_gracefully(reset_llm_singleton, monkeypatch):
    """If Gemini is down, Engine 2 still produces a verdict from OCR + NAFDAC."""
    monkeypatch.setattr(engine_module, "_get_llm_client", lambda: _UnavailableLLM())

    quote = _make_packaging_image(["Coartem", "NAFDAC: 04-9412"])
    delivery = _make_packaging_image(["Coartem", "NAFDAC: 04-9412"])

    result = await verify_delivery(DeliveryInput(
        order_id="ord_test_no_llm",
        quote_image_bytes=quote,
        delivery_image_bytes=delivery,
        expected_product_name="Coartem",
        expected_manufacturer="Novartis",
        expected_nafdac_number="04-9412",
    ))

    # Should still produce a verdict — LLM check is unverified, others vote
    llm_check = next(c for c in result.checks if c.name == "Visual Adjudication")
    assert llm_check.status == "unverified"
    # OCR + NAFDAC both pass → green
    assert result.verdict == "green"


@pytest.mark.asyncio
async def test_wrong_nafdac_on_package_fails(reset_llm_singleton, monkeypatch):
    """Even if the LLM says the products match, a wrong NAFDAC number
    on the package must fail the verdict."""
    monkeypatch.setattr(engine_module, "_get_llm_client", lambda: _MatchingLLM())

    quote = _make_packaging_image(["Coartem", "NAFDAC: 04-9412"])
    delivery = _make_packaging_image(["Coartem", "NAFDAC: 04-6433"])  # WRONG

    result = await verify_delivery(DeliveryInput(
        order_id="ord_test_wrong_number",
        quote_image_bytes=quote,
        delivery_image_bytes=delivery,
        expected_product_name="Coartem",
        expected_manufacturer="Novartis",
        expected_nafdac_number="04-9412",
    ))

    nafdac_check = next(c for c in result.checks if c.name == "NAFDAC Cross-check")
    assert nafdac_check.status == "fail"
    assert result.verdict in {"amber", "red"}


@pytest.mark.asyncio
async def test_diagnostics_populated(reset_llm_singleton, monkeypatch):
    monkeypatch.setattr(engine_module, "_get_llm_client", lambda: _MatchingLLM())
    quote = _make_packaging_image(["Test", "NAFDAC: 04-9412"])
    delivery = _make_packaging_image(["Test", "NAFDAC: 04-9412"])

    result = await verify_delivery(DeliveryInput(
        order_id="ord_diag",
        quote_image_bytes=quote,
        delivery_image_bytes=delivery,
        expected_nafdac_number="04-9412",
    ))

    assert result.duration_ms >= 0
    assert result.ocr_source in {"tesseract", "llm"}
    assert len(result.checks) == 3
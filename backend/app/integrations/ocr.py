"""
OCR helper — Tesseract first, LLM fallback for stylized packaging.

Used by Engine 2 to extract NAFDAC numbers from delivery photos. Tesseract
is fast and free but bad at fancy packaging fonts; the LLM is slow and
costs tokens but handles anything. We try Tesseract first and only fall
back when its output looks like gibberish.

For backend devs:
    from app.integrations.ocr import extract_registration_number

    number, source = await extract_registration_number(
        image_bytes,
        registry_type="nafdac",
        llm_client=llm_client,  # optional; if None, no fallback
    )
    # → ("04-9412", "tesseract")  or  ("04-9412", "llm")  or  (None, "failed")
"""
from __future__ import annotations

import asyncio
import io
import logging
import re
from typing import Literal

try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except ImportError:  # pragma: no cover
    _OCR_AVAILABLE = False

logger = logging.getLogger(__name__)


RegistryType = Literal["nafdac", "son", "mancap", "none"]
OcrSource = Literal["tesseract", "llm", "failed", "disabled"]


# Regexes for what a "valid-looking" number for each registry type looks like.
# Match Tesseract output against these to decide whether to trust it.
_REGISTRY_PATTERNS: dict[RegistryType, re.Pattern[str]] = {
    "nafdac": re.compile(r"\b[A-Z0-9]{1,2}-\d{4}\b", re.IGNORECASE),
    "son": re.compile(r"\bSON[/\-][A-Z0-9/\-]{3,}\b", re.IGNORECASE),
    "mancap": re.compile(r"\bMANCAP[/\-][A-Z0-9/\-]{3,}\b", re.IGNORECASE),
    "none": re.compile(r"\b[A-Z0-9]{2,}[/\-][A-Z0-9/\-]{3,}\b", re.IGNORECASE),
}


def _normalize_match(raw: str) -> str:
    """Canonicalize a found registration number."""
    return raw.strip().upper().replace(" ", "")


def _run_tesseract(image_bytes: bytes) -> str:
    """Run Tesseract on raw image bytes and return the OCR text.

    Returns an empty string on any failure (Tesseract not installed,
    image not parseable, etc.) — callers should check for emptiness.
    """
    if not _OCR_AVAILABLE:
        return ""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img)
        return text or ""
    except pytesseract.TesseractNotFoundError:
        logger.warning(
            "Tesseract binary not found on PATH — install via "
            "https://github.com/UB-Mannheim/tesseract/wiki (Windows) "
            "or `apt install tesseract-ocr` (Linux). Falling back to LLM OCR."
        )
        return ""
    except Exception as exc:  # noqa: BLE001 — log and continue
        logger.debug("Tesseract OCR failed: %s", exc)
        return ""


def _extract_with_regex(text: str, registry_type: RegistryType) -> str | None:
    """Pick out the first registration-shaped string from Tesseract's output."""
    if not text:
        return None
    pattern = _REGISTRY_PATTERNS[registry_type]
    match = pattern.search(text)
    return _normalize_match(match.group(0)) if match else None


async def extract_registration_number(
    image_bytes: bytes,
    registry_type: RegistryType = "nafdac",
    llm_client: object | None = None,
) -> tuple[str | None, OcrSource]:
    """Extract a registration number from a product image.

    Tries Tesseract first. If Tesseract returns gibberish or nothing,
    falls back to the LLM client's `extract_registration_number` method.

    Args:
        image_bytes: raw bytes of the product photo
        registry_type: nafdac / son / mancap / none
        llm_client: an instance of app.integrations.llm.LLMClient.
            If None, no fallback — returns (None, "failed") when Tesseract fails.

    Returns:
        Tuple of (number_or_none, source) where source is one of:
            "tesseract" — Tesseract succeeded
            "llm"       — Tesseract failed, LLM succeeded
            "failed"    — both failed
            "disabled"  — pytesseract / PIL not installed
    """
    if not _OCR_AVAILABLE:
        if llm_client is None:
            return None, "disabled"
        # No Tesseract, but we have the LLM — skip straight to it
        return await _call_llm(image_bytes, registry_type, llm_client), "llm"

    # Step 1 — Tesseract
    tesseract_text = await asyncio.to_thread(_run_tesseract, image_bytes)
    tesseract_match = _extract_with_regex(tesseract_text, registry_type)

    if tesseract_match is not None:
        logger.debug("Tesseract extracted %s", tesseract_match)
        return tesseract_match, "tesseract"

    # Step 2 — LLM fallback
    if llm_client is None:
        return None, "failed"

    llm_match = await _call_llm(image_bytes, registry_type, llm_client)
    if llm_match is not None:
        return llm_match, "llm"
    return None, "failed"


async def _call_llm(
    image_bytes: bytes,
    registry_type: RegistryType,
    llm_client: object,
) -> str | None:
    """Call the LLM client's OCR method in a worker thread (it's sync)."""
    try:
        # LLMClient.extract_registration_number is sync; wrap it
        result = await asyncio.to_thread(
            llm_client.extract_registration_number,  # type: ignore[attr-defined]
            image_bytes,
            registry_type,
        )
        if result:
            return _normalize_match(result)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM OCR fallback failed: %s", exc)
        return None
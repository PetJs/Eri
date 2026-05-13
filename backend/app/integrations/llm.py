"""Gemini-backed LLM client: invoice parsing, product adjudication, registration OCR fallback."""
import datetime
import json
import logging
import os
import re
from typing import Any, Literal

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.5-flash"
_CACHED_MODEL = "gemini-2.5-flash-001"  # version pin required for context caching
_CACHE_TTL = "3600s"

RegistryType = Literal["nafdac", "son", "mancap", "none"]

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_INVOICE_SYSTEM = """\
You are an expert B2B procurement fraud analyst. Your job is to extract structured
data from supplier invoices and assess their authenticity. The supplier may be in
any sector — healthcare, supply chain, professional services, equipment, food, etc.

When given an invoice image, return a JSON object with exactly these keys:
{
  "supplier_name": "<string or null>",
  "account_number": "<string or null>",
  "phone_number": "<string or null>",
  "registration_numbers": {"<registry>": "<number>", ...},
  "total_amount": <number or null>,
  "line_items": [
    {
      "description": "<string>",
      "quantity": <number or null>,
      "unit_price": <number or null>,
      "total": <number or null>
    }
  ],
  "legitimacy": {
    "verdict": "legitimate" | "suspicious" | "fraudulent",
    "confidence": <0.0 to 1.0>,
    "concerns": ["<string>", ...]
  }
}

Look for universal fraud signals: inconsistent fonts, digital-manipulation artifacts,
mismatched logos, missing standard fields, unrealistic pricing relative to line items,
suspicious account-name vs business-name discrepancies.
If the invoice is from a regulated sector and you see regulatory registration numbers
(e.g. NAFDAC, SON, NCC, MANCAP), extract them — but do not require them.
Return ONLY the JSON object, no explanation, no markdown fences.
"""

_PRODUCT_SYSTEM = """\
You are an expert visual product verification analyst. Your job is to compare two
product images — one showing what was ordered and one showing what was delivered —
and detect substitutions, counterfeits, or quality mismatches. Products may come
from any sector: pharmaceuticals, electronics, food, equipment, consumables, etc.

When given the two images and the expected product details, return a JSON object:
{
  "match": <true | false>,
  "confidence": <0.0 to 1.0>,
  "delivered_name": "<string or null>",
  "delivered_variant": "<string or null>",
  "delivered_registration": "<string or null>",
  "differences": ["<string>", ...],
  "concerns": ["<string>", ...]
}

Compare all visible attributes: name, brand, model/variant, size/quantity/dosage,
manufacturer, packaging design, registration numbers, lot/batch format, security
features. Flag anything that doesn't match the expected details.
Return ONLY the JSON object, no explanation, no markdown fences.
"""

_REGISTRY_PATTERNS: dict[RegistryType, str] = {
    "nafdac": r"[A-Z0-9]{1,2}-\d{4}",          # e.g. 04-9412, A4-0023
    "son":    r"SON/[A-Z0-9/\-]+",               # e.g. SON/NIS/123/456
    "mancap": r"MANCAP[/\-][A-Z0-9/\-]+",        # e.g. MANCAP/001/2023
    "none":   r"[A-Z0-9]{2,}[/\-][A-Z0-9/\-]+", # any visible reg-style number
}

_REGISTRY_HINTS: dict[RegistryType, str] = {
    "nafdac": (
        "Look for a NAFDAC registration number. "
        "Format: XX-XXXX (e.g. 04-9412, A4-0023). "
        "Reply with ONLY the NAFDAC number, or null."
    ),
    "son": (
        "Look for a Standards Organisation of Nigeria (SON) certification mark or number. "
        "Format often starts with SON/ (e.g. SON/NIS/123/456). "
        "Reply with ONLY the SON number, or null."
    ),
    "mancap": (
        "Look for a MANCAP certification number (Manufacturers Association of Nigeria). "
        "Format often starts with MANCAP/ or MANCAP- (e.g. MANCAP/001/2023). "
        "Reply with ONLY the MANCAP number, or null."
    ),
    "none": (
        "Look for any visible regulatory or certification registration number on the product. "
        "Reply with ONLY the number you find (e.g. 04-9412, SON/NIS/123), or null."
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _image_part(image_bytes: bytes) -> types.Part:
    """Convert raw image bytes into a Gemini Part."""
    if image_bytes[:4] == b"%PDF":
        mime = "application/pdf"
    elif image_bytes[:2] == b"\xff\xd8":
        mime = "image/jpeg"
    elif image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    else:
        mime = "image/jpeg"
    return types.Part.from_bytes(data=image_bytes, mime_type=mime)


def _parse_json(text: str) -> dict:
    """Strip optional markdown fences and parse JSON."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text.strip(), flags=re.MULTILINE)
    return json.loads(text.strip())


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class LLMClient:
    """Single entry point for all Gemini-backed AI tasks.

      - parse_invoice           → field extraction + authenticity check (any domain)
      - adjudicate_products     → quote-vs-delivery visual comparison (any product type)
      - extract_registration_number → OCR fallback for NAFDAC / SON / MANCAP / generic
    """

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set")
        self._client = genai.Client(api_key=api_key)
        self._invoice_cache: types.CachedContent | None = None
        self._product_cache: types.CachedContent | None = None

    # ------------------------------------------------------------------
    # Context cache management
    # ------------------------------------------------------------------

    def _get_or_create_cache(
        self,
        attr: str,
        system_instruction: str,
        display_name: str,
    ) -> "types.CachedContent | None":
        """Return a live CachedContent handle, creating/refreshing as needed.

        Returns None when the system prompt is below Gemini's 32 768-token minimum;
        callers must then embed the system prompt inline via GenerateContentConfig.
        """
        cached: types.CachedContent | None = getattr(self, attr)

        if cached is not None:
            try:
                remaining = (
                    cached.expire_time
                    - datetime.datetime.now(datetime.timezone.utc)
                ).total_seconds()
                if remaining > 300:
                    return cached
            except Exception:
                pass

        try:
            handle = self._client.caches.create(
                model=_CACHED_MODEL,
                config=types.CreateCachedContentConfig(
                    display_name=display_name,
                    system_instruction=system_instruction,
                    ttl=_CACHE_TTL,
                ),
            )
            setattr(self, attr, handle)
            return handle
        except Exception as exc:
            msg = str(exc).lower()
            if any(x in msg for x in ("minimum", "32768", "32,768", "token")):
                logger.debug(
                    "System prompt below Gemini cache minimum — using inline prompt for %s",
                    display_name,
                )
                return None
            raise

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_invoice(
        self,
        invoice_image: bytes,
        domain_context: str | None = None,
    ) -> dict[str, Any]:
        """Extract supplier details, line items, and authenticity verdict from an invoice image.

        Args:
            invoice_image: Raw bytes of the invoice (JPEG, PNG, or PDF).
            domain_context: Optional one-liner narrowing the analysis, e.g.
                "Healthcare procurement. Expect NAFDAC registration numbers."
                Omit for fully generic analysis.
        """
        cache = self._get_or_create_cache(
            "_invoice_cache", _INVOICE_SYSTEM, "invoice-analysis"
        )

        prompt_text = "Analyse this invoice image and return the JSON."
        if domain_context:
            prompt_text = f"Domain context: {domain_context}\n\n{prompt_text}"

        contents = [prompt_text, _image_part(invoice_image)]

        if cache:
            config = types.GenerateContentConfig(cached_content=cache.name)
            model = _CACHED_MODEL
        else:
            config = types.GenerateContentConfig(system_instruction=_INVOICE_SYSTEM)
            model = _MODEL

        response = self._client.models.generate_content(
            model=model, contents=contents, config=config
        )
        return _parse_json(response.text)

    def adjudicate_products(
        self,
        quote_image: bytes,
        delivery_image: bytes,
        expected_details: dict[str, Any],
    ) -> dict[str, Any]:
        """Compare a quoted product image against the delivered product and return a match verdict.

        Args:
            quote_image:      Image of the product that was ordered / quoted.
            delivery_image:   Image of the product that was actually delivered.
            expected_details: Dict of known attributes, e.g.:
                              {"name": "Coartem 20/120", "variant": "blister pack of 24",
                               "manufacturer": "Novartis", "registration": "04-9412"}
                              Any keys are accepted; unknown keys are passed through as-is.
        """
        cache = self._get_or_create_cache(
            "_product_cache", _PRODUCT_SYSTEM, "product-verification"
        )

        detail_lines = "\n".join(
            f"  {k}: {v}" for k, v in expected_details.items() if v is not None
        )
        details_text = f"Expected product details:\n{detail_lines}\n"

        contents = [
            details_text,
            "Image 1 — QUOTED product (what was ordered):",
            _image_part(quote_image),
            "Image 2 — DELIVERED product (what arrived):",
            _image_part(delivery_image),
            "Compare the two images against the expected details and return the JSON verdict.",
        ]

        if cache:
            config = types.GenerateContentConfig(cached_content=cache.name)
            model = _CACHED_MODEL
        else:
            config = types.GenerateContentConfig(system_instruction=_PRODUCT_SYSTEM)
            model = _MODEL

        response = self._client.models.generate_content(
            model=model, contents=contents, config=config
        )
        return _parse_json(response.text)

    def extract_registration_number(
        self,
        product_image: bytes,
        registry_type: RegistryType = "none",
    ) -> str | None:
        """Read a regulatory registration number from a product image.

        Intended as a Tesseract fallback — used when OCR fails on stylised packaging.

        Args:
            product_image: Raw image bytes of the product packaging.
            registry_type: Which registry to look for:
                           "nafdac"  → NAFDAC number (XX-XXXX)
                           "son"     → SON certification number
                           "mancap"  → MANCAP certification number
                           "none"    → any visible registration-style number
        """
        hint = _REGISTRY_HINTS[registry_type]
        system = (
            "You are an OCR specialist for product packaging. "
            "Extract a single regulatory registration number from the image. "
            "Reply with ONLY the number, or the word null if you cannot find one. "
            "No explanation, no JSON."
        )
        response = self._client.models.generate_content(
            model=_MODEL,
            contents=[hint, _image_part(product_image)],
            config=types.GenerateContentConfig(system_instruction=system),
        )
        raw = response.text.strip()
        if raw.lower() in ("null", "none", ""):
            return None
        pattern = _REGISTRY_PATTERNS[registry_type]
        match = re.search(pattern, raw, re.IGNORECASE)
        return match.group(0).upper() if match else raw.upper()

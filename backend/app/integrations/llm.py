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
You are a senior procurement compliance analyst specialised in Nigerian B2B trade
documents. Your only output is a single, valid JSON object. No prose, no markdown
fences, no explanation — raw JSON that can be fed directly to json.loads().

════════════════════════════════════════════════════════════
ABSOLUTE RULES
════════════════════════════════════════════════════════════
1.  Never return an empty string "". Any field you cannot extract must be JSON null.
2.  Never invent or guess a value. If it is not visible in the document, return null.
3.  Never wrap output in ``` or ```json. Return raw JSON only.
4.  Return exactly the keys shown in the schema — no additions, no renames.
5.  All monetary amounts are plain numbers: no ₦ symbol, no commas, no spaces.
    "₦1,200,000.00" → 1200000.0
6.  All dates are ISO 8601: YYYY-MM-DD.
    "15 May 2026" → "2026-05-15". Partial dates: "May 2026" → null.
7.  line_items is always an array, even for a single product.
8.  quantity, unit_price, and line_total are always numbers. Use 0 only if the
    field is genuinely present but illegible. null is wrong for these three.
9.  currency defaults to "NGN" unless the invoice explicitly states otherwise.
10. extraction_confidence is your own calibrated estimate (0.0–1.0) based on
    scan quality, completeness, and internal consistency. Never round to exactly
    1.0 unless every field was unambiguous and all arithmetic checks passed.

════════════════════════════════════════════════════════════
OUTPUT SCHEMA
════════════════════════════════════════════════════════════
{
  "supplier": {
    "name":                    "<business name as printed — never null if visible>",
    "rc_number":               "<CAC number e.g. RC-123456, or null>",
    "nafdac_premises_license": "<NAFDAC premises/mfr licence e.g. NAFDAC/OL/xxxxx, or null>",
    "address":                 "<full address block as printed, or null>",
    "bank_account": {
      "bank_name":      "<e.g. Zenith Bank, or null>",
      "account_name":   "<account name exactly as printed, or null>",
      "account_number": "<10-digit NUBAN, or null>"
    }
  },
  "buyer": {
    "name":      "<bill-to / ship-to entity name, or null>",
    "rc_number": "<buyer CAC number if shown, or null>",
    "address":   "<buyer address if shown, or null>"
  },
  "invoice_metadata": {
    "invoice_number": "<invoice / pro-forma / LPO reference number, or null>",
    "issue_date":     "<YYYY-MM-DD, or null>",
    "due_date":       "<YYYY-MM-DD, or null>",
    "payment_terms":  "<e.g. Net 30, Payment on delivery, or null>"
  },
  "line_items": [
    {
      "description":         "<product/service name — required, never null>",
      "nafdac_registration": "<NAFDAC reg number for this item e.g. 04-9412, or null>",
      "manufacturer":        "<manufacturer name for this item, or null>",
      "batch_number":        "<batch / lot number if printed, or null>",
      "expiry_date":         "<YYYY-MM-DD, or null>",
      "quantity":            "<number>",
      "unit_price":          "<number>",
      "line_total":          "<quantity times unit_price — cross-check before returning>"
    }
  ],
  "totals": {
    "subtotal":    "<sum of all line_total values>",
    "discount":    "<discount amount — 0 if none, never null>",
    "vat":         "<VAT/tax amount — 0 if not charged, never null>",
    "grand_total": "<final payable = subtotal minus discount plus vat>",
    "currency":    "<ISO 4217 code, default NGN>"
  },
  "extraction_confidence": "<0.0 to 1.0>",
  "raw_text_sample": "<verbatim text from the document header/first section, 500 chars max>"
}

════════════════════════════════════════════════════════════
ARITHMETIC — VERIFY BEFORE RETURNING
════════════════════════════════════════════════════════════
For every line item:
  Compute quantity times unit_price yourself.
  If the printed line_total disagrees with your computation by more than 1,
  use YOUR computed value and subtract 0.1 from extraction_confidence.

For totals:
  Verify sum(line_totals) approximately equals subtotal (within rounding).
  grand_total must equal subtotal minus discount plus vat (within 1 unit rounding).
  If the document grand_total disagrees, record YOUR computed grand_total and
  subtract 0.15 from extraction_confidence.
  Nigerian VAT is 7.5%. If a VAT line is absent but the invoice says VAT inclusive,
  derive: vat = grand_total times (0.075 / 1.075), rounded to 2 decimal places.

════════════════════════════════════════════════════════════
NIGERIAN FIELD PATTERNS
════════════════════════════════════════════════════════════
RC numbers     : RC 123456 or RC-123456 → normalise to RC-123456
NAFDAC (item)  : pattern XX-XXXX or X-XXXX  e.g. 04-9412, A4-0023
NAFDAC (premises): NAFDAC/OL/12345 or NAFDAC Premises Licence No.
PCN number     : PCN/xxxxx — goes in nafdac_premises_license
Bank accounts  : always 10 digits (NUBAN). Strip spaces.
Common banks   : Access, GTBank, Zenith, First Bank, UBA, Stanbic IBTC, Sterling,
                 Polaris, Union Bank, FCMB, Wema, Keystone, Heritage, Providus, Fidelity
Nett amount    : Nigerian shorthand for grand total after VAT — treat as grand_total.
Supplier name  : prefer the legal name in the letterhead over the stamp.

════════════════════════════════════════════════════════════
FRAUD SIGNAL INDICATORS (lower extraction_confidence, do not add extra JSON keys)
════════════════════════════════════════════════════════════
Reduce confidence by the amounts shown when you observe:

-0.20  Font inconsistency within a single field (suggests digital editing)
-0.20  Bank account name does not match supplier business name
-0.15  Line item unit prices implausible for stated product type and quantity
-0.15  Total arithmetic does not reconcile
-0.10  Invoice number format inconsistent with document date
-0.10  Logo or stamp has pixelation mismatch with surrounding document
-0.10  Key fields (supplier name, grand_total, at least one line item) missing

Clamp extraction_confidence to [0.05, 1.0] — never return exactly 0.

════════════════════════════════════════════════════════════
HANDLING DIFFICULT DOCUMENTS
════════════════════════════════════════════════════════════
Handwritten fields      : extract if legible; null if not.
Scanned / low-res PDF   : do your best; lower confidence appropriately.
Multi-page invoices     : treat all pages as one document; combine line items.
Pro-forma vs tax invoice: extract equally; the distinction does not change the schema.
Table with merged cells : identify each product row individually.
\
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

        user_parts: list[Any] = [
            "Extract all structured data from this invoice document and return "
            "the JSON object defined in your instructions. Perform all arithmetic "
            "cross-checks before responding.",
        ]
        if domain_context:
            user_parts.insert(0, f"Domain context: {domain_context}")
        user_parts.append(_image_part(invoice_image))

        contents = user_parts

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

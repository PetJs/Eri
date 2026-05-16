"""
Orders / escrow endpoints.

POST /orders/extract-invoice  — LLM reads a PDF invoice and returns structured data
POST /orders                  — Create escrow from reviewed invoice draft
GET  /orders/{id}             — Fetch order state
POST /orders/{id}/release     — Release funds to supplier
POST /orders/{id}/dispute     — Freeze funds and raise a dispute

Order state lives in the in-memory _ORDERS dict (replaced by Postgres in v2).
"""
from __future__ import annotations

import asyncio
import logging
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.schemas.orders import (
    CreateOrderFromInvoiceRequest,
    DisputeOrderRequest,
    ExtractInvoiceResponse,
    InvoiceBankAccount,
    InvoiceBuyer,
    InvoiceLineItem,
    InvoiceMetadata,
    InvoiceSupplier,
    InvoiceTotals,
    OrderActionResponse,
    OrderResponse,
    ReleaseOrderRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])

_ORDERS: dict[str, dict[str, Any]] = {}

_KNOWN_SUPPLIERS: dict[str, dict[str, str]] = {
    "sup_medtrust": {
        "name": "MedTrust Nigeria Limited",
        "verdict": "green",
        "score": "100",
        "account_number": "0123456789",
        "bank_code": "058",
        "account_name": "MEDTRUST NIGERIA LIMITED",
    },
    "sup_lagospharma": {
        "name": "Lagos Pharma Distributors",
        "verdict": "amber",
        "score": "64",
        "account_number": "3001234567",
        "bank_code": "044",
        "account_name": "OLUMIDE ADEYEMI",
    },
    "sup_quickmeds": {
        "name": "QuickMeds Wholesale",
        "verdict": "red",
        "score": "15",
        "account_number": "9988776655",
        "bank_code": "058",
        "account_name": "AZURITE LOGISTICS NIGERIA",
    },
    "sup_pharmaplus": {
        "name": "PharmaPlus Solutions Limited",
        "verdict": "green",
        "score": "95",
        "account_number": "2105887301",
        "bank_code": "058",
        "account_name": "PHARMAPLUS SOLUTIONS LIMITED",
    },
}

# Nigerian bank name → CBN bank code mapping
_BANK_CODE_MAP: dict[str, str] = {
    "access": "044",
    "gtbank": "058",
    "guaranty trust": "058",
    "zenith": "057",
    "first bank": "011",
    "firstbank": "011",
    "uba": "033",
    "stanbic": "221",
    "sterling": "232",
    "polaris": "076",
    "union bank": "032",
    "fcmb": "214",
    "wema": "035",
    "keystone": "082",
    "heritage": "030",
    "providus": "101",
    "fidelity": "070",
}

_MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB


def _generate_id(prefix: str = "ord", length: int = 10) -> str:
    chars = string.ascii_lowercase + string.digits
    return f"{prefix}_{''.join(random.choices(chars, k=length))}"


def _generate_virtual_account() -> str:
    return "".join(random.choices(string.digits, k=10))


def _resolve_bank_code(bank_name: str | None) -> str:
    if not bank_name:
        return ""
    lower = bank_name.lower()
    for key, code in _BANK_CODE_MAP.items():
        if key in lower:
            return code
    return ""


# -----------------------------------------------------------------------------
# Invoice extraction helper
# -----------------------------------------------------------------------------

def _map_llm_to_extraction(raw: dict[str, Any]) -> ExtractInvoiceResponse:
    """Map parse_invoice() raw dict → ExtractInvoiceResponse Pydantic model.

    Handles both the new extended schema and gracefully degrades when the LLM
    returns partial / legacy shapes.
    """
    supplier_data: dict = raw.get("supplier") or {}
    # Legacy fallback: flat supplier_name at top level
    if not supplier_data and raw.get("supplier_name"):
        supplier_data = {"name": raw["supplier_name"]}

    bank_data: dict = supplier_data.get("bank_account") or {}
    if not bank_data and raw.get("account_number"):
        bank_data = {"account_number": raw["account_number"]}

    buyer_data: dict = raw.get("buyer") or {}
    meta_data: dict = raw.get("invoice_metadata") or {}
    totals_data: dict = raw.get("totals") or {}

    raw_items = raw.get("line_items") or []
    line_items: list[InvoiceLineItem] = []
    for item in raw_items:
        qty = float(item.get("quantity") or 0)
        up = float(item.get("unit_price") or 0)
        lt = float(item.get("line_total") or item.get("total") or (qty * up))
        line_items.append(InvoiceLineItem(
            description=item.get("description") or "Unknown product",
            nafdac_registration=item.get("nafdac_registration") or None,
            manufacturer=item.get("manufacturer") or None,
            batch_number=item.get("batch_number") or None,
            expiry_date=item.get("expiry_date") or None,
            quantity=qty,
            unit_price=up,
            line_total=lt,
        ))

    if not line_items:
        line_items = [InvoiceLineItem(
            description="Unreadable line item",
            quantity=0,
            unit_price=0,
            line_total=0,
        )]

    subtotal = float(totals_data.get("subtotal") or raw.get("total_amount") or
                     sum(i.line_total for i in line_items))
    discount = float(totals_data.get("discount") or 0)
    vat = float(totals_data.get("vat") or 0)
    grand_total = float(totals_data.get("grand_total") or subtotal - discount + vat or subtotal)
    if grand_total <= 0:
        grand_total = subtotal

    return ExtractInvoiceResponse(
        supplier=InvoiceSupplier(
            name=supplier_data.get("name") or "Unknown Supplier",
            rc_number=supplier_data.get("rc_number") or None,
            nafdac_premises_license=supplier_data.get("nafdac_premises_license") or None,
            address=supplier_data.get("address") or None,
            bank_account=InvoiceBankAccount(
                bank_name=bank_data.get("bank_name") or None,
                account_name=bank_data.get("account_name") or None,
                account_number=bank_data.get("account_number") or None,
            ),
        ),
        buyer=InvoiceBuyer(
            name=buyer_data.get("name") or None,
            rc_number=buyer_data.get("rc_number") or None,
            address=buyer_data.get("address") or None,
        ),
        invoice_metadata=InvoiceMetadata(
            invoice_number=meta_data.get("invoice_number") or None,
            issue_date=meta_data.get("issue_date") or None,
            due_date=meta_data.get("due_date") or None,
            payment_terms=meta_data.get("payment_terms") or None,
        ),
        line_items=line_items,
        totals=InvoiceTotals(
            subtotal=subtotal,
            discount=discount,
            vat=vat,
            grand_total=grand_total,
            currency=totals_data.get("currency") or "NGN",
        ),
        extraction_confidence=float(raw.get("extraction_confidence") or 0.5),
        raw_text_sample=raw.get("raw_text_sample") or None,
    )


# -----------------------------------------------------------------------------
# Background verification: E1, E2×N, E3
# -----------------------------------------------------------------------------

async def _engine1_supplier(order_id: str, supplier: InvoiceSupplier) -> None:
    from app.engines.supplier_trust import SupplierInput, score_supplier

    bank_code = _resolve_bank_code(supplier.bank_account.bank_name)
    inp = SupplierInput(
        business_name=supplier.name,
        rc_number=supplier.rc_number or "",
        bank_account_number=supplier.bank_account.account_number or "",
        bank_code=bank_code,
        supplier_type="healthcare" if supplier.nafdac_premises_license else "general",
    )
    try:
        result = await score_supplier(inp)
        logger.info(
            "Order %s E1 supplier_trust: score=%d verdict=%s",
            order_id, result.score, result.verdict,
        )
        if order_id in _ORDERS:
            _ORDERS[order_id]["trust_score_at_creation"] = result.score
            _ORDERS[order_id]["trust_verdict_at_creation"] = result.verdict
    except Exception as exc:
        logger.warning("Order %s E1 failed: %s", order_id, exc)


async def _engine2_nafdac_lookup(
    order_id: str, idx: int, item: InvoiceLineItem
) -> None:
    from app.integrations.nafdac import lookup_nafdac

    if not item.nafdac_registration:
        logger.info(
            "Order %s E2 item[%d] '%s': no NAFDAC number — skipping",
            order_id, idx, item.description,
        )
        return

    try:
        record = await lookup_nafdac(item.nafdac_registration)
        status = "registered" if record.registered else "NOT registered"
        logger.info(
            "Order %s E2 item[%d] '%s': NAFDAC %s → %s (product=%s manufacturer=%s)",
            order_id, idx, item.description,
            item.nafdac_registration, status,
            record.product_name or "unknown",
            record.manufacturer or "unknown",
        )
        if order_id in _ORDERS:
            verdicts: dict = _ORDERS[order_id].setdefault("line_item_verdicts", {})
            verdicts[str(idx)] = {
                "description": item.description,
                "nafdac_registration": item.nafdac_registration,
                "registered": record.registered,
                "product_name": record.product_name,
                "manufacturer": record.manufacturer,
                "nafdac_status": record.status,
            }
    except Exception as exc:
        logger.warning("Order %s E2 item[%d] failed: %s", order_id, idx, exc)


async def _engine3_anomaly(
    order_id: str, payload: CreateOrderFromInvoiceRequest
) -> None:
    try:
        from app.engines.anomaly import AnomalyEngine
        engine = AnomalyEngine()
    except Exception as exc:
        logger.info("Order %s E3 anomaly engine unavailable: %s", order_id, exc)
        return

    features: dict[str, Any] = {
        "amount_ngn": payload.totals.grand_total,
        "hour_of_day": datetime.now(timezone.utc).hour,
        "supplier_age_days": 0,
        "bank_account_changed_recently": 0,
        "supplier_prior_disputes_count": 0,
        "price_vs_market_ratio": 1.0,
        "nafdac_license_active": 1 if payload.supplier.nafdac_premises_license else 0,
    }
    try:
        result = engine.score(features)
        logger.info(
            "Order %s E3 anomaly: score=%s verdict=%s flags=%s",
            order_id, result.get("anomaly_score"), result.get("verdict"),
            result.get("flags", []),
        )
        if order_id in _ORDERS:
            _ORDERS[order_id]["anomaly_result"] = result
    except Exception as exc:
        logger.warning("Order %s E3 failed: %s", order_id, exc)


async def _run_verification(
    order_id: str, payload: CreateOrderFromInvoiceRequest
) -> None:
    """Run E1 (supplier), E2×N (NAFDAC per line item), E3 (anomaly) in parallel."""
    coros: list[Any] = [_engine1_supplier(order_id, payload.supplier)]
    for idx, item in enumerate(payload.line_items):
        coros.append(_engine2_nafdac_lookup(order_id, idx, item))
    coros.append(_engine3_anomaly(order_id, payload))

    logger.info(
        "Order %s: firing %d verification coroutines (E1 + %d×E2 + E3)",
        order_id, len(coros), len(payload.line_items),
    )
    results = await asyncio.gather(*coros, return_exceptions=True)
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.warning("Order %s verification[%d] raised: %s", order_id, i, r)

    if order_id in _ORDERS:
        _ORDERS[order_id]["verification_status"] = "complete"


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------

@router.post(
    "/extract-invoice",
    response_model=ExtractInvoiceResponse,
    summary="Extract structured invoice data from a PDF using LLM",
    status_code=200,
)
async def extract_invoice(
    file: UploadFile = File(..., description="Invoice or pro-forma PDF, max 10 MB"),
) -> ExtractInvoiceResponse:
    content = await file.read()

    if len(content) > _MAX_PDF_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds 10 MB limit ({len(content):,} bytes received)",
        )

    if not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=415,
            detail="Only PDF files are accepted (file must start with %PDF magic bytes)",
        )

    try:
        from app.integrations.llm import LLMClient
        client = LLMClient()
        raw = client.parse_invoice(content)
    except Exception as exc:
        logger.warning("Invoice extraction failed for %s: %s", file.filename, exc)
        raise HTTPException(
            status_code=422,
            detail={"error": "extraction_failed", "detail": str(exc)},
        )

    return _map_llm_to_extraction(raw)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=201,
    summary="Create an escrow order from a reviewed invoice draft",
)
async def create_order(
    payload: CreateOrderFromInvoiceRequest,
    background_tasks: BackgroundTasks,
) -> OrderResponse:
    # Server-side grand_total validation (anti-tampering)
    computed_total = (
        sum(item.line_total for item in payload.line_items)
        - payload.totals.discount
        + payload.totals.vat
    )
    if abs(computed_total - payload.totals.grand_total) > 1.0:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "grand_total_mismatch",
                "submitted": payload.totals.grand_total,
                "computed": round(computed_total, 2),
                "message": (
                    "grand_total does not match sum(line_totals) − discount + vat. "
                    "Recompute on the client before submitting."
                ),
            },
        )

    order_id = _generate_id("ord")
    now = datetime.now(timezone.utc)
    amount_ngn = round(payload.totals.grand_total)

    supplier_name = payload.supplier.name
    # Build a short description from the first line item (for legacy fields)
    first_item = payload.line_items[0]
    description = (
        f"{first_item.description}"
        + (f" · NAFDAC {first_item.nafdac_registration}" if first_item.nafdac_registration else "")
        + (f" + {len(payload.line_items) - 1} more items" if len(payload.line_items) > 1 else "")
    )

    # Provision Squad DVA
    virtual_account_number: str
    virtual_account_name: str
    virtual_account_bank: str

    try:
        from app.integrations.squad import get_squad_client
        squad = get_squad_client()
        if squad is None:
            logger.warning("Squad client unavailable; using mock virtual account")
            virtual_account_number = _generate_virtual_account()
            virtual_account_name = "Eri Escrow / Demo Buyer"
            virtual_account_bank = "Guaranty Trust Bank"
        else:
            dva = await squad.initiate_dynamic_va(
                amount_kobo=amount_ngn * 100,
                transaction_ref=order_id,
                email=payload.buyer_email,
                duration_seconds=3600 * 24,
            )
            if dva.success and dva.account_number:
                virtual_account_number = dva.account_number
                virtual_account_name = dva.account_name or "Eri Escrow"
                virtual_account_bank = dva.bank or "Guaranty Trust Bank"
                if dva.refilled_pool:
                    logger.info("DVA pool auto-refilled for order %s", order_id)
            else:
                logger.warning(
                    "Squad DVA failed for order %s: %s. Falling back to mock.",
                    order_id, dva.error,
                )
                virtual_account_number = _generate_virtual_account()
                virtual_account_name = "Eri Escrow / Demo Buyer"
                virtual_account_bank = "Guaranty Trust Bank"
    except Exception as exc:
        logger.exception("Unexpected Squad DVA error for order %s: %s", order_id, exc)
        virtual_account_number = _generate_virtual_account()
        virtual_account_name = "Eri Escrow / Demo Buyer"
        virtual_account_bank = "Guaranty Trust Bank"

    order_dict: dict[str, Any] = {
        "id": order_id,
        "status": "pending_payment",
        "supplier_id": f"sup_{supplier_name.lower().replace(' ', '_')[:20]}",
        "supplier_name": supplier_name,
        "amount_ngn": amount_ngn,
        "description": description,
        "buyer_email": str(payload.buyer_email),
        "created_at": now,
        "expected_delivery_by": now + timedelta(days=payload.expected_delivery_days),
        "virtual_account_number": virtual_account_number,
        "virtual_account_name": virtual_account_name,
        "virtual_account_bank": virtual_account_bank,
        "squad_transaction_ref": order_id,
        "trust_score_at_creation": None,
        "trust_verdict_at_creation": None,
        "verification_status": "pending",
        "line_items": [item.model_dump() for item in payload.line_items],
        "source_document_id": payload.source_document_id,
    }
    _ORDERS[order_id] = order_dict

    # Fire E1 + E2×N + E3 in the background — does not block the response
    background_tasks.add_task(_run_verification, order_id, payload)

    logger.info(
        "Order %s created: supplier=%s items=%d total=₦%s",
        order_id, supplier_name, len(payload.line_items), f"{amount_ngn:,}",
    )

    return OrderResponse(
        id=order_id,
        status="pending_payment",
        supplier_id=order_dict["supplier_id"],
        supplier_name=supplier_name,
        amount_ngn=amount_ngn,
        description=description,
        created_at=now,
        expected_delivery_by=order_dict["expected_delivery_by"],
        virtual_account_number=virtual_account_number,
        virtual_account_name=virtual_account_name,
        virtual_account_bank=virtual_account_bank,
        trust_score_at_creation=None,
        trust_verdict_at_creation=None,
        line_items=payload.line_items,
        verification_status="pending",
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get an order's current state",
)
async def get_order(order_id: str) -> OrderResponse:
    order = _ORDERS.get(order_id)
    if order is None:
        canned = _canned_order(order_id)
        if canned is None:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        return OrderResponse(**canned)
    # Reconstruct line_items from stored dicts if present
    raw_items = order.get("line_items")
    line_items = None
    if raw_items:
        try:
            line_items = [InvoiceLineItem(**i) if isinstance(i, dict) else i for i in raw_items]
        except Exception:
            line_items = None
    return OrderResponse(
        id=order["id"],
        status=order["status"],
        supplier_id=order["supplier_id"],
        supplier_name=order["supplier_name"],
        amount_ngn=order["amount_ngn"],
        description=order["description"],
        created_at=order["created_at"],
        expected_delivery_by=order.get("expected_delivery_by"),
        virtual_account_number=order.get("virtual_account_number"),
        virtual_account_name=order.get("virtual_account_name"),
        virtual_account_bank=order.get("virtual_account_bank"),
        trust_score_at_creation=order.get("trust_score_at_creation"),
        trust_verdict_at_creation=order.get("trust_verdict_at_creation"),
        line_items=line_items,
        verification_status=order.get("verification_status"),
    )


@router.post(
    "/{order_id}/release",
    response_model=OrderActionResponse,
    summary="Release escrow to supplier via Squad Transfer API",
)
async def release_order(
    order_id: str, payload: ReleaseOrderRequest
) -> OrderActionResponse:
    order = _ORDERS.get(order_id)
    if order is None:
        canned = _canned_order(order_id)
        if canned is None:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        order = dict(canned)
        _ORDERS[order_id] = order

    if order["status"] not in {"funded", "delivered_pending"}:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot release order in status '{order['status']}'",
        )

    transfer_message: str
    try:
        from app.integrations.squad import get_squad_client
        squad = get_squad_client()
        if squad is None:
            transfer_message = (
                f"Released ₦{order['amount_ngn']:,} to {order['supplier_name']} "
                f"(Squad unavailable — recorded locally)"
            )
        else:
            supplier_info = _KNOWN_SUPPLIERS.get(order["supplier_id"], {})
            recipient_account = supplier_info.get("account_number", "0123456789")
            recipient_bank = supplier_info.get("bank_code", "058")
            recipient_name = supplier_info.get("account_name", order["supplier_name"])

            transfer = await squad.initiate_transfer(
                amount_kobo=order["amount_ngn"] * 100,
                bank_code=recipient_bank,
                account_number=recipient_account,
                account_name=recipient_name,
                narration=f"Eri escrow release {order_id}",
                remark=payload.confirmation_note or "Escrow released by buyer",
            )

            if transfer.success:
                order["squad_transfer_ref"] = transfer.transaction_ref
                transfer_message = (
                    f"Transferred ₦{order['amount_ngn']:,} to "
                    f"{order['supplier_name']} (Squad ref: {transfer.transaction_ref})"
                )
            else:
                transfer_message = (
                    f"Released ₦{order['amount_ngn']:,} to {order['supplier_name']} "
                    f"(Squad transfer reported: {transfer.error or 'unknown error'})"
                )
    except Exception as exc:
        logger.warning("Squad release failed: %s", exc)
        transfer_message = (
            f"Released ₦{order['amount_ngn']:,} to {order['supplier_name']} "
            f"(Squad call failed — recorded locally)"
        )

    order["status"] = "released"
    return OrderActionResponse(
        order_id=order_id,
        new_status="released",
        message=transfer_message,
    )


@router.post(
    "/{order_id}/dispute",
    response_model=OrderActionResponse,
    summary="Raise a dispute on an order",
)
async def dispute_order(
    order_id: str, payload: DisputeOrderRequest
) -> OrderActionResponse:
    order = _ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    if order["status"] not in {"funded", "delivered_pending"}:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot dispute order in status '{order['status']}'",
        )

    order["status"] = "disputed"
    return OrderActionResponse(
        order_id=order_id,
        new_status="disputed",
        message=(
            f"Dispute filed (reason: {payload.reason}). "
            f"Funds frozen pending admin review."
        ),
    )


# -----------------------------------------------------------------------------
# Demo helper
# -----------------------------------------------------------------------------

def _canned_order(order_id: str) -> dict[str, Any] | None:
    base_time = datetime.now(timezone.utc) - timedelta(hours=4)
    canned: dict[str, dict[str, Any]] = {
        "ord_demo_pending": {
            "id": "ord_demo_pending",
            "status": "pending_payment",
            "supplier_id": "sup_medtrust",
            "supplier_name": "MedTrust Nigeria Limited",
            "amount_ngn": 1_250_000,
            "description": "50 cartons of Coartem 20/120 (NAFDAC 04-9412)",
            "created_at": base_time,
            "expected_delivery_by": base_time + timedelta(days=14),
            "virtual_account_number": "9012345678",
            "virtual_account_name": "Eri Escrow / Demo Buyer",
            "virtual_account_bank": "Guaranty Trust Bank",
            "trust_score_at_creation": 100,
            "trust_verdict_at_creation": "green",
        },
        "ord_demo_funded": {
            "id": "ord_demo_funded",
            "status": "funded",
            "supplier_id": "sup_medtrust",
            "supplier_name": "MedTrust Nigeria Limited",
            "amount_ngn": 1_250_000,
            "description": "50 cartons of Coartem 20/120 (NAFDAC 04-9412)",
            "created_at": base_time,
            "expected_delivery_by": base_time + timedelta(days=14),
            "virtual_account_number": "9012345678",
            "virtual_account_name": "Eri Escrow / Demo Buyer",
            "virtual_account_bank": "Guaranty Trust Bank",
            "trust_score_at_creation": 100,
            "trust_verdict_at_creation": "green",
        },
        "ord_demo_disputed": {
            "id": "ord_demo_disputed",
            "status": "disputed",
            "supplier_id": "sup_quickmeds",
            "supplier_name": "QuickMeds Wholesale",
            "amount_ngn": 950_000,
            "description": "Coartem (delivered packaging is suspect)",
            "created_at": base_time,
            "expected_delivery_by": base_time + timedelta(days=14),
            "virtual_account_number": "9012345679",
            "virtual_account_name": "Eri Escrow / Demo Buyer",
            "virtual_account_bank": "Guaranty Trust Bank",
            "trust_score_at_creation": 15,
            "trust_verdict_at_creation": "red",
        },
    }
    return canned.get(order_id)

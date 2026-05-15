"""
Webhook endpoints.

Squad POSTs payment events here when funds land in our DVA accounts.
We correlate by `transaction_ref` (which equals our order_id) and flip
the order status accordingly.

⚠️ Signature verification is currently NOT implemented. Real Squad webhooks
carry an `x-squad-signature` header containing an HMAC-SHA512 of the raw
body using the webhook secret. For production, see the TODO inside the
handler — the code stub is there, just commented out.
"""
from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import APIRouter, Header, Request

from app.schemas.webhooks import SquadWebhookPayload, WebhookAckResponse
from app.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_squad_signature(raw_body: bytes, signature: str | None) -> bool:
    """Verify a Squad webhook's x-squad-signature header.

    Disabled when SQUAD_WEBHOOK_SECRET is empty (current hackathon state).
    Enable by setting the env var; the verification then runs automatically.
    """
    secret = settings.squad_webhook_secret
    if not secret:
        return True  # Skip verification entirely if no secret configured
    if not signature:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(expected, signature.lower())


@router.post(
    "/squad",
    response_model=WebhookAckResponse,
    summary="Receive Squad payment / transfer webhooks",
    description=(
        "Squad calls this endpoint when:\n\n"
        "- **Virtual account payment lands** — flips the matching order to `funded`\n"
        "- **DVA mismatch** — buyer paid wrong amount; surface for review\n"
        "- **DVA expired** — buyer never paid in time\n"
        "- **Transfer succeeds/fails** — confirms our release-escrow calls\n\n"
        "Correlates events back to orders via `transaction_ref` (which equals our "
        "internal order_id). Always returns 200 — Squad retries on non-2xx, "
        "and we never want duplicate processing."
    ),
)
async def squad_webhook(
    request: Request,
    x_squad_signature: str | None = Header(default=None),
) -> WebhookAckResponse:
    raw_body = await request.body()

    # --- Signature verification ---
    if not _verify_squad_signature(raw_body, x_squad_signature):
        logger.warning("Squad webhook signature verification failed")
        # Still ack with 200 so Squad doesn't retry endlessly; just don't
        # process the event. In production, return 401 instead.
        return WebhookAckResponse(received=False, event="signature_failed")

    # Parse body (after sig check so we hash the raw bytes, not the parsed json)
    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Squad webhook had unparseable body: %s", exc)
        return WebhookAckResponse(received=False, event="invalid_body")

    # DEBUG: dump the full payload so we can see Squad's exact field names.
    # Remove this log line once the schema is confirmed in production.
    logger.info("Squad webhook RAW payload: %s", payload)

    # Squad's webhook payload is FLAT (no nested Data). Field names:
    #   - merchant_reference: our order_id (we passed this as transaction_ref to DVA initiate)
    #   - transaction_reference: Squad's internal ID (not our order_id — don't correlate on this)
    #   - transaction_status: "success" | "MISMATCH" | "failed" (case-varies)
    #   - merchant_amount: amount the order expects (naira string)
    #   - amount_received: amount actually paid (naira string)
    #   - transaction_type: e.g. "dynamic_virtual_account"
    order_ref = payload.get("merchant_reference")
    raw_status = (payload.get("transaction_status") or "").lower()
    transaction_type = payload.get("transaction_type", "")
    amount_received = payload.get("amount_received")
    merchant_amount = payload.get("merchant_amount")

    # Treat transaction_status as our event indicator
    event = raw_status or "unknown"
    transaction_ref = order_ref
    transaction_status = raw_status

    logger.info(
        "Squad webhook received: event=%s ref=%s status=%s",
        event, transaction_ref, transaction_status,
    )

    # --- Correlate to an order ---
    # transaction_ref equals our order_id (set in create_order)
    from app.routers.orders import _ORDERS

    if transaction_ref and transaction_ref in _ORDERS:
        order = _ORDERS[transaction_ref]

        # Successful payment to a DVA → mark order funded
        if "success" in transaction_status:
            if order["status"] == "pending_payment":
                order["status"] = "funded"
                order["funded_at"] = payload.get("date")
                order["squad_transaction_ref"] = payload.get("transaction_reference")
                logger.info(
                    "Order %s flipped to funded via Squad webhook (received ₦%s)",
                    transaction_ref, amount_received,
                )

        # Mismatch (buyer paid wrong amount) → flag the order for review
        elif "mismatch" in transaction_status:
            order.setdefault("flags", []).append(
                f"payment_amount_mismatch (expected ₦{merchant_amount}, "
                f"received ₦{amount_received})"
            )
            logger.warning(
                "Order %s has amount mismatch: expected ₦%s, received ₦%s",
                transaction_ref, merchant_amount, amount_received,
            )

        # Failed or expired
        elif "fail" in transaction_status or "expired" in transaction_status:
            if order["status"] == "pending_payment":
                order["status"] = "cancelled"
                logger.info("Order %s cancelled (status=%s)", transaction_ref, transaction_status)
    else:
        logger.info(
            "Squad webhook ref=%s does not match any known order (ignored)",
            transaction_ref,
        )

    return WebhookAckResponse(received=True, event=str(event))
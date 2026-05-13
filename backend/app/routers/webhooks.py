"""
Webhook endpoints.

**STUB.** Squad will POST to /webhooks/squad when funds land in escrow,
when a transfer succeeds, etc. We currently just acknowledge receipt and
log; real signature verification + state machine updates happen when the
Squad integration is wired in.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Header, Request

from app.schemas.webhooks import SquadWebhookPayload, WebhookAckResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post(
    "/squad",
    response_model=WebhookAckResponse,
    summary="Receive Squad webhook events (STUB)",
    description=(
        "**STUB** — Squad sends transaction events here. In production, we'd "
        "verify the HMAC signature in the `x-squad-signature` header against "
        "our webhook secret, then update the corresponding order's state. "
        "Currently we acknowledge receipt and log."
    ),
)
async def squad_webhook(
    request: Request,
    payload: SquadWebhookPayload,
    x_squad_signature: str | None = Header(default=None),
) -> WebhookAckResponse:
    # STUB: when wiring real Squad, verify x_squad_signature here.
    # if not _verify_signature(await request.body(), x_squad_signature):
    #     raise HTTPException(status_code=401, detail="Invalid signature")

    logger.info(
        "Squad webhook received: event=%s data_keys=%s",
        payload.event,
        list(payload.data.keys()),
    )
    return WebhookAckResponse(received=True, event=payload.event)
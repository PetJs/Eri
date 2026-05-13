"""
Schemas for webhooks Squad calls into Eri.

STUB for now — the actual Squad payload shape will be confirmed against
their docs when we wire real integration. We approximate the typical
shape so the route is callable in dev.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SquadWebhookPayload(BaseModel):
    """Approximation of a Squad event payload.

    Real Squad webhooks send `event` (e.g. 'charge.success'), `data`
    containing the transaction details, and a signature in the headers.
    Confirm the exact shape with HabariPay docs before wiring real
    verification.
    """

    event: Literal[
        "charge.success",
        "charge.failed",
        "transfer.success",
        "transfer.failed",
    ]
    data: dict[str, Any] = Field(
        ...,
        description="Event-specific payload (transaction ref, amount, account, etc.)",
    )


class WebhookAckResponse(BaseModel):
    """We acknowledge receipt regardless of processing outcome."""

    received: bool = True
    event: str
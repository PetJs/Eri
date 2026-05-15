"""
Health check endpoint.

Used by deployment platforms (Render, Fly.io, etc.) to verify the service
is alive. Also useful as the first thing the frontend dev hits to confirm
they can reach the backend.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.settings import settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    environment: str
    timestamp: datetime


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Confirms the server is running. Used by load balancers and dev sanity checks.",
)
async def health() -> HealthResponse:
    return HealthResponse(
        app=settings.app_name,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc),
    )
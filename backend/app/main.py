"""
Eri Backend — FastAPI application.

Run in development:
    uvicorn app.main:app --reload --port 8000

Then open http://localhost:8000/docs for the interactive API documentation.

This file just wires things together. The actual logic lives in:
  - app/engines/      (the AI engines)
  - app/integrations/ (external data sources)
  - app/routers/      (HTTP route handlers)
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import admin, health, orders, verify, webhooks
from app.settings import settings

# Configure logging early so router imports inherit the level
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Lifespan — startup / shutdown hooks
# -----------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Eri backend starting up (env=%s)", settings.environment)
    logger.info("CORS origins: %s", settings.cors_origins_list)
    logger.info(
        "Routes available at http://localhost:8000/docs (Swagger) "
        "and http://localhost:8000/redoc"
    )
    yield
    # Shutdown (nothing yet — placeholder for DB pool close, etc.)
    logger.info("Eri backend shutting down")


# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------

app = FastAPI(
    title="Eri Backend API",
    description=(
        "Verification-gated escrow for Nigerian B2B procurement.\n\n"
        "Three AI engines protect every transaction:\n"
        "1. **Supplier Trust** — CAC + bank name + court records + NAFDAC\n"
        "2. **Product CV** — visual verification of delivered goods (coming)\n"
        "3. **Anomaly Detection** — XGBoost classifier trained on Nigerian fraud patterns\n\n"
        "All routes return structured JSON. Routes marked **STUB** return "
        "realistic mock data; their schemas match the real implementations "
        "that will replace them."
    ),
    version="0.1.0",
    contact={
        "name": "Eri Team",
        "url": "https://github.com/your-org/eri",
    },
    lifespan=lifespan,
)


# -----------------------------------------------------------------------------
# CORS
# -----------------------------------------------------------------------------

# In dev we allow the configured origins (Vite + Next.js default ports).
# Tighten for production: only the deployed frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------

app.include_router(health.router)
app.include_router(verify.router)
app.include_router(orders.router)
app.include_router(webhooks.router)
app.include_router(admin.router)
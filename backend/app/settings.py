"""
Application settings.

Loads from environment variables (and a .env file if present).
See .env.example at the project root for the full list of supported vars.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Eri backend configuration.

    All settings can be overridden via environment variables of the same
    name (case-insensitive). For local dev, drop them in `.env.local`.
    """

    # -- Server -----------------------------------------------------------
    app_name: str = "Eri Backend"
    environment: str = "development"  # development | staging | production
    log_level: str = "INFO"

    # -- CORS -------------------------------------------------------------
    # Comma-separated origins allowed to call the API. In dev we allow
    # the default Vite (5173) and Next.js (3000) ports. Tighten in prod.
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    # -- Squad (HabariPay) ------------------------------------------------
    # Used by the orders router (stubs for now, real wiring later)
    squad_secret_key: str = ""
    squad_public_key: str = ""
    squad_base_url: str = "https://sandbox-api-d.squadco.com"
    squad_webhook_secret: str = ""

    # -- LLM --------------------------------------------------------------
    gemini_api_key: str = ""  # used by app/integrations/llm.py

    # -- Pydantic settings config ----------------------------------------
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# Singleton — import this everywhere instead of constructing Settings()
settings = Settings()
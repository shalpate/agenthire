"""
config.py - Centralized configuration for AgentHire.

Usage:
    from config import config
    app.config.from_object(config["development"])

Environment variables:
    FLASK_ENV             development | production (default: development)
    SECRET_KEY            Flask secret key (required in production)
    DATABASE_URL          SQLAlchemy DB URI (default: sqlite:///agenthire.db)
    API_KEY               API key for protected admin/seller mutation routes
    CORS_ORIGINS          Comma-separated allowed origins (default: *)
    RATELIMIT_DEFAULT     Default rate limit string (default: 60/minute)
    FACILITATOR_URL       Optional: Node facilitator service URL
    FACILITATOR_PRIVATE_KEY  Optional: private key for on-chain x402 flow
    GATEKEEPER_PRIVATE_KEY   Optional: private key for dispute signing
    RPC_URL               Optional: Avalanche RPC URL (default: Fuji)
"""
from __future__ import annotations
import os
from typing import Optional


class Config:
    """Base configuration - shared across all environments."""

    # ── Flask ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    DEBUG: bool = False
    TESTING: bool = False

    # ── Database ───────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL", "sqlite:///agenthire.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = False  # Set True to log all SQL in development

    # ── CORS ───────────────────────────────────────────────────────────────
    CORS_ORIGINS: list = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "*").split(",")
        if o.strip()
    ]

    # ── Rate limiting ──────────────────────────────────────────────────────
    RATELIMIT_DEFAULT: str = os.environ.get("RATELIMIT_DEFAULT", "120/minute")
    RATELIMIT_STORAGE_URI: str = "memory://"  # swap to redis:// in production
    RATELIMIT_HEADERS_ENABLED: bool = True

    # ── Auth ───────────────────────────────────────────────────────────────
    API_KEY: Optional[str] = os.environ.get("API_KEY")  # None → auth disabled (local dev)

    # ── On-chain ────────────────────────────────────────────────────────────
    FACILITATOR_URL: Optional[str] = os.environ.get("FACILITATOR_URL")
    FACILITATOR_PRIVATE_KEY: Optional[str] = os.environ.get("FACILITATOR_PRIVATE_KEY")
    GATEKEEPER_PRIVATE_KEY: Optional[str] = os.environ.get("GATEKEEPER_PRIVATE_KEY")
    RPC_URL: str = os.environ.get("RPC_URL", "https://api.avax-test.network/ext/C/rpc")


class DevelopmentConfig(Config):
    """Development - verbose, SQLite, no strict auth."""
    DEBUG = True
    SQLALCHEMY_ECHO = False  # flip to True to debug queries


class TestingConfig(Config):
    """Testing - in-memory SQLite, no rate limiting."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production - strict, no debug, env-driven secrets."""
    DEBUG = False

    @classmethod
    def init_app(cls, app):
        # Warn if secret key is still the default
        if cls.SECRET_KEY == "dev-secret-change-in-production":
            import warnings
            warnings.warn(
                "SECRET_KEY is set to the default value. "
                "Set the SECRET_KEY environment variable in production.",
                stacklevel=2,
            )


# Map FLASK_ENV → config class
config: dict = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

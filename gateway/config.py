"""Settings, read once from the environment.

Every module asks `get_settings()` instead of reading `os.environ` itself, so
the full list of knobs lives here and tests can swap it with `override()`.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    data_dir: Path = Field(default=Path("./data"))
    secret_key: str | None = None
    rate_limit_per_min: int = Field(default=60, ge=1)
    panel_host: str = "127.0.0.1"
    panel_port: int = 8600
    mcp_principal: str = "admin"
    demo_seed: bool = True
    session_ttl_s: int = 8 * 3600

    @property
    def db_path(self) -> Path:
        return self.data_dir / "gateway.db"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.environ.get("GATEWAY_DATA_DIR", "./data")),
            secret_key=os.environ.get("GATEWAY_SECRET_KEY") or None,
            rate_limit_per_min=int(os.environ.get("GATEWAY_RATE_LIMIT_PER_MIN", "60")),
            panel_host=os.environ.get("GATEWAY_PANEL_HOST", "127.0.0.1"),
            panel_port=int(os.environ.get("GATEWAY_PANEL_PORT", "8600")),
            mcp_principal=os.environ.get("GATEWAY_MCP_PRINCIPAL", "admin"),
            demo_seed=_env_bool("GATEWAY_DEMO_SEED", True),
        )


_override: Settings | None = None


@lru_cache(maxsize=1)
def _from_env() -> Settings:
    return Settings.from_env()


def get_settings() -> Settings:
    return _override if _override is not None else _from_env()


def override(settings: Settings | None) -> None:
    """Replace the active settings (tests). `None` goes back to the environment."""
    global _override
    _override = settings

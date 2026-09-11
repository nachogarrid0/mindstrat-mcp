"""Configuration for the MindStrat MCP server, read from the environment."""

from __future__ import annotations

import os
from pathlib import Path

# Backend discovery
PORT_ENV = "MINDSTRAT_MCP_PORT"
DEV_DEFAULT_PORT = 8000
BACKEND_HOST = "127.0.0.1"

# Live trading. No credentials here by design: live tools act as the user
# signed in to the desktop app, whose session the backend attaches.
ALLOW_LIVE_ENV = "MINDSTRAT_MCP_ALLOW_LIVE"

# Output shaping
DEFAULT_LIMIT = 20
MAX_LIMIT = 100

# Timeouts (seconds)
DEFAULT_TIMEOUT = 30.0
LONG_TIMEOUT = 120.0


def appdata_dir() -> Path:
    """Resolve the MindStrat data directory, mirroring backend_entry._appdata_dir."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".local" / "share"
    return base / "MindStrat"


def mcp_state_dir() -> Path:
    """Runtime state owned by the MCP server (job tracker, token cache)."""
    target = appdata_dir() / "mcp"
    target.mkdir(parents=True, exist_ok=True)
    return target


def backend_lock_path() -> Path:
    """File written by backend_entry with the running backend's PID."""
    return appdata_dir() / "backend.lock"


def configured_port() -> int | None:
    raw = os.environ.get(PORT_ENV, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def live_enabled() -> bool:
    return os.environ.get(ALLOW_LIVE_ENV, "").strip() == "1"

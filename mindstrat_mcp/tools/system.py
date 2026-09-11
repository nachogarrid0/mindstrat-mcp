"""System-level tools: backend reachability and MCP server state."""

from __future__ import annotations

from typing import Any

from .. import config
from ..client import BackendClient


async def backend_status(client: BackendClient) -> dict[str, Any]:
    """Report whether the MindStrat backend is reachable and how it was found."""
    port = await client.ensure_port(force=True)
    health = await client.get("/health")
    return {
        "reachable": True,
        "base_url": client.base_url(),
        "port": port,
        "discovered_via": client.discovery_source,
        "health": health,
        "live_tools_enabled": config.live_enabled(),
    }

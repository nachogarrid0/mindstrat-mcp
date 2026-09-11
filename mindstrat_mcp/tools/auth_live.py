"""Session handling for the live-trading endpoints.

``/live`` and ``/exchanges`` proxy to the cloud and carry the user's identity,
so they need a bearer token; the rest of the local API does not.

This server holds no credentials of its own, by design. It acts *as the
signed-in user*: the desktop app mirrors its session into the backend, and the
backend attaches it when a local client calls those routes without an
Authorization header. So there is one identity and one sign-in path, and live
trading is unreachable unless the user is signed in to the app.
"""

from __future__ import annotations

import logging
from typing import Any

from ..client import BackendClient
from ..errors import McpToolError

logger = logging.getLogger(__name__)

NO_SESSION = (
    "No signed-in session. Open the MindStrat app and sign in — this server "
    "acts as the signed-in user and holds no credentials of its own."
)


async def session_status(client: BackendClient) -> dict[str, Any]:
    """Whether the app is signed in, as the backend sees it."""
    snapshot = await client.get("/auth/desktop-session")
    if not isinstance(snapshot, dict):
        return {"active": False}
    return snapshot


async def authed_request(
    client: BackendClient, method: str, path: str, **kwargs: Any
) -> Any:
    """Call a cloud-backed route using the app's session.

    No Authorization header is sent: the backend supplies the signed-in
    session. A 401 therefore means the user is not signed in, not that a
    credential of ours went stale.
    """
    try:
        return await client.request(method, path, **kwargs)
    except McpToolError as exc:
        if "live.no_session" in str(exc) or "401" in str(exc):
            raise McpToolError(NO_SESSION) from exc
        raise

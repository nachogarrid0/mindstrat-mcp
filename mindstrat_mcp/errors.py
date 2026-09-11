"""Error translation between the MindStrat backend and MCP tool results."""

from __future__ import annotations

from typing import Any

import httpx

OPTIMIZER_BUSY = "optimizer.busy_finishing"

BACKEND_UNREACHABLE = (
    "MindStrat backend is not reachable. Open the MindStrat app and retry "
    "(set MINDSTRAT_MCP_PORT if the backend runs on a non-default port)."
)


class McpToolError(Exception):
    """Raised by tools; the message is surfaced to the model."""


def _detail_text(payload: Any) -> str:
    """Unwrap FastAPI error bodies: {"detail": str | {...}} and friends."""
    if isinstance(payload, dict):
        for key in ("detail", "message", "error"):
            if key in payload:
                return _detail_text(payload[key])
        return str(payload)
    if isinstance(payload, list) and payload:
        return "; ".join(_detail_text(item) for item in payload)
    return str(payload)


def _structured_detail(payload: Any) -> str | None:
    """Readable text for the coded errors the preset endpoints answer with.

    Those return i18n keys rather than sentences, so the desktop app can say it
    in the user's language. Rendered here with the app's own English wording,
    which is why an agent gets "Define a number of workers between 1 and 64"
    instead of a key and a dict.
    """
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if not isinstance(detail, dict):
        return None

    from .appdata import validation_text

    issues = detail.get("issues")
    if isinstance(issues, list) and issues:
        lines = [
            f"- {validation_text(str(issue.get('code', '')), issue.get('params'))}"
            for issue in issues
            if isinstance(issue, dict)
        ]
        return "This configuration cannot start a run:\n" + "\n".join(lines)

    code = detail.get("code")
    if isinstance(code, str) and code:
        return validation_text(code, detail.get("params"))
    return None


def from_response(response: httpx.Response) -> McpToolError:
    """Build a tool error from a non-2xx backend response."""
    try:
        payload: Any = response.json()
    except ValueError:
        payload = response.text.strip() or response.reason_phrase

    detail = _detail_text(payload)
    status = response.status_code

    if status == 409 and OPTIMIZER_BUSY in detail:
        return McpToolError(
            "The previous optimization is still shutting down (up to ~150 s). "
            "Wait and retry start_optimization."
        )
    if status == 402:
        reason = ""
        if isinstance(payload, dict):
            inner = payload.get("detail")
            if isinstance(inner, dict):
                reason = str(inner.get("reason") or "")
        suffix = f" (reason: {reason})" if reason else ""
        return McpToolError(f"Payment/quota required{suffix}: {detail}")
    if status == 401:
        return McpToolError(f"Unauthorized: {detail}")
    if status == 404:
        return McpToolError(
            f"Not found: {detail}. Note in-memory job queues are cleared when the "
            "backend restarts."
        )
    if status == 422:
        structured = _structured_detail(payload)
        if structured:
            return McpToolError(structured)

    return McpToolError(f"Backend error {status}: {detail}")

"""Live trading tools: portfolio monitoring and deployment.

Backend surface: /live and /exchanges — thin proxies to AWS that carry the
user's identity. This server holds no credentials: it acts as the user signed
in to the app, whose session the backend attaches (see auth_live).

This is the only section that moves real money, so every mutation is gated
behind MINDSTRAT_MCP_ALLOW_LIVE=1 and, where relevant, an explicit confirm
flag. Reads only need the app to be signed in.
"""

from __future__ import annotations

from typing import Any

import httpx

from .. import config
from ..client import BackendClient
from ..errors import McpToolError
from ..shaping import clamp_limit, paginate, pick, round_numbers
from .auth_live import authed_request, session_status

_STRATEGY_FIELDS = (
    "live_strategy_id",
    "strategy_name",
    "saved_strategy_id",
    "symbol",
    "interval",
    "status",
    "desired_state",
    "assigned_worker_id",
    "total_trades",
    "total_pnl",
    "wins",
    "losses",
    "last_event_at",
    "last_error",
    "created_at",
)


def _require_mutations_enabled(action: str) -> None:
    if not config.live_enabled():
        raise McpToolError(
            f"Live mutations are disabled, so '{action}' was not performed. "
            f"Set {config.ALLOW_LIVE_ENV}=1 in the MCP server environment to "
            "enable deploying, stopping and resizing live strategies."
        )


async def live_auth_status(client: BackendClient) -> dict[str, Any]:
    """Report whether the app is signed in and whether mutations are allowed."""
    snapshot = await session_status(client)
    return {
        "signed_in": bool(snapshot.get("active")),
        "account": snapshot.get("email"),
        "session_expired": bool(snapshot.get("expired")),
        "expires_at": snapshot.get("expires_at"),
        "mutations_enabled": config.live_enabled(),
        "note": (
            "Live tools act as the user signed in to the app; this server "
            "holds no credentials. Sign in there to enable them."
            if not snapshot.get("active")
            else "Reads are available. Mutations also need "
            "MINDSTRAT_MCP_ALLOW_LIVE=1 and confirm=true."
        ),
    }


async def list_live_strategies(
    client: BackendClient, status: str | None = None
) -> dict[str, Any]:
    """Portfolio view: every deployed strategy with its state and P&L."""
    params = {"status": status} if status and status != "all" else None
    payload = await authed_request(client, "GET", "/live/strategies", params=params)
    strategies = (payload or {}).get("strategies", [])

    items = [round_numbers(pick(item, _STRATEGY_FIELDS)) for item in strategies]
    return {
        "items": items,
        "count": len(items),
        "note": (
            "Per-strategy figures as reported by the backend. status is the "
            "observed state and desired_state is what was requested; they "
            "converge asynchronously. No portfolio totals are given: the API "
            "exposes none, and the app's dashboard derives its own from closed "
            "trades, so summing these fields would not match what you see."
        ),
    }


async def get_live_strategy(
    client: BackendClient,
    live_strategy_id: str,
    section: str = "summary",
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    """Inspect one live strategy: summary, trades, events or config."""
    if section not in ("summary", "trades", "events", "config"):
        raise McpToolError("section must be 'summary', 'trades', 'events' or 'config'")

    if section == "config":
        payload = await authed_request(
            client, "GET", f"/live/strategies/{live_strategy_id}/config"
        )
        config_payload = dict(payload or {})
        code = config_payload.pop("strategy_code", None)
        if isinstance(code, str):
            config_payload["strategy_code_lines"] = len(code.splitlines())
        return round_numbers(config_payload)

    details = await authed_request(
        client, "GET", f"/live/strategies/{live_strategy_id}/details"
    )
    details = details or {}
    trades = details.get("trades") or []
    events = details.get("events") or []
    legs = details.get("legs") or []

    if section == "trades":
        return round_numbers(paginate(trades, limit, offset))
    if section == "events":
        return round_numbers(paginate(events, limit, offset))

    recent = clamp_limit(limit) if limit else 5
    return round_numbers(
        {
            "live_strategy_id": live_strategy_id,
            "counts": {"trades": len(trades), "events": len(events), "legs": len(legs)},
            "recent_trades": trades[-recent:],
            "recent_events": events[-recent:],
            "hint": "Use section='trades' or section='events' to page through the full history.",
        }
    )


async def list_exchange_accounts(client: BackendClient) -> dict[str, Any]:
    """List configured exchange accounts (API keys are masked)."""
    payload = await authed_request(client, "GET", "/exchanges/accounts")
    accounts = payload if isinstance(payload, list) else (payload or {}).get("accounts", [])
    return {"items": accounts, "count": len(accounts)}


async def deploy_live_strategy(
    client: BackendClient,
    saved_strategy_id: int,
    symbol: str,
    interval: str,
    environment: str,
    exchange: str = "binance",
    kind: str = "futures",
    margin_type: str | None = "USDM",
    exchange_slug: str = "binance",
    exchange_account_id: str | None = None,
    capital_cfg: dict[str, Any] | None = None,
    auxiliary_datasets: dict[str, Any] | None = None,
    strategy_name: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Deploy a saved strategy to live trading (upload_init -> S3 -> create)."""
    _require_mutations_enabled("deploy_live_strategy")
    if not confirm:
        raise McpToolError(
            f"Refusing to deploy strategy {saved_strategy_id} to '{environment}': "
            "pass confirm=true. On the live environment this trades real money."
        )
    if environment == "live" and not exchange_account_id:
        raise McpToolError(
            "Deploying to the live environment requires exchange_account_id. "
            "List available accounts with list_exchange_accounts."
        )

    code = await client.get(f"/manager/strategies/{saved_strategy_id}/code")
    if not isinstance(code, str) or not code.strip():
        raise McpToolError(f"Strategy {saved_strategy_id} has no source code to deploy")

    init = await authed_request(client, "POST", "/live/strategies/upload_init", json={})
    if not isinstance(init, dict):
        raise McpToolError(f"Unexpected upload_init response: {init}")

    resolved_margin = margin_type if kind == "futures" else None
    config_document = {
        "symbol": symbol,
        "interval": interval,
        "exchange": exchange,
        "kind": kind,
        "margin_type": resolved_margin,
        "environment": environment,
        "capital_cfg": capital_cfg
        or {
            "initial_capital": 10000,
            "order_size_mode": "fixed_value",
            "order_size": 1000,
            "commission": 0,
            "commission_type": "percent",
            "slippage_bps": 0,
        },
    }
    if auxiliary_datasets:
        config_document["auxiliary_datasets"] = auxiliary_datasets

    # The presigned URLs point at S3 directly, bypassing the local backend.
    async with httpx.AsyncClient(timeout=config.LONG_TIMEOUT) as uploader:
        for url, body, content_type in (
            (init["strategy_upload"]["url"], code, "text/x-python"),
            (init["config_upload"]["url"], config_document, "application/json"),
        ):
            data = body if isinstance(body, str) else None
            response = await uploader.put(
                url,
                content=data.encode("utf-8") if data is not None else None,
                json=None if data is not None else body,
                headers={"Content-Type": content_type},
            )
            if response.status_code >= 400:
                raise McpToolError(
                    f"Upload to S3 failed ({response.status_code}): {response.text[:200]}"
                )

    exchange_block: dict[str, Any] = {
        "exchange_slug": exchange_slug,
        "exchange": exchange,
        "kind": kind,
        "margin_type": resolved_margin,
        "environment": environment,
    }
    if exchange_account_id:
        exchange_block["exchange_account_id"] = exchange_account_id

    payload: dict[str, Any] = {
        "live_strategy_id": init["live_strategy_id"],
        "saved_strategy_id": saved_strategy_id,
        "strategy_name": strategy_name or f"Strategy #{saved_strategy_id}",
        "strategy_s3_key": init["strategy_upload"]["key"],
        "config_s3_key": init["config_upload"]["key"],
        "symbol": symbol,
        "interval": interval,
        "connection_id": "web-client",
        "exchange": exchange_block,
    }
    if exchange_account_id:
        # Also sent at root level for backwards compatibility with the Lambda.
        payload["exchange_account_id"] = exchange_account_id
    if auxiliary_datasets:
        payload["auxiliary_datasets"] = auxiliary_datasets

    created = await authed_request(client, "POST", "/live/strategies", json=payload)
    return {
        "deployed": True,
        "live_strategy_id": init["live_strategy_id"],
        "strategy": round_numbers(pick(created or {}, _STRATEGY_FIELDS)) or created,
        "note": "Deployment converges asynchronously; poll list_live_strategies.",
    }


async def stop_live_strategy(
    client: BackendClient, live_strategy_id: str, confirm: bool = False
) -> dict[str, Any]:
    """Request a live strategy to stop trading."""
    _require_mutations_enabled("stop_live_strategy")
    if not confirm:
        raise McpToolError(
            f"Refusing to stop {live_strategy_id}: pass confirm=true. Open "
            "positions may be affected."
        )
    result = await authed_request(
        client, "POST", f"/live/strategies/{live_strategy_id}/stop"
    )
    return {
        "live_strategy_id": live_strategy_id,
        "result": result,
        "note": "Stop is asynchronous; poll list_live_strategies until status is STOPPED.",
    }


async def update_live_order_size(
    client: BackendClient, live_strategy_id: str, order_size: float, confirm: bool = False
) -> dict[str, Any]:
    """Hot-edit the order size of a running live strategy."""
    _require_mutations_enabled("update_live_order_size")
    if not confirm:
        raise McpToolError(
            f"Refusing to change order size of {live_strategy_id}: pass confirm=true. "
            "This changes position sizing on real trades."
        )
    if order_size <= 0:
        raise McpToolError("order_size must be greater than 0")

    result = await authed_request(
        client,
        "PATCH",
        f"/live/strategies/{live_strategy_id}/config",
        json={"order_size": order_size},
    )
    return round_numbers(result)

"""Code Creator tools: strategies, datasets, backtests and the Python kernel.

Backend surface: /ai/tools and /ai/kernel (no auth). These are the same
endpoints the in-app agentic chat calls for its "fastapi" zone tools, so the
response shapes are already agent-sized (paginated, capped).

The editor_* tools drive the Code Creator session (/strategies/parameters,
/update, /run, /library/save-strategy), which is module-global state shared
with the open desktop UI. They mirror how the screen is used: load code, run
it, adjust parameters, run again, and save only once the strategy holds up.
editor_load_code asks for confirmation because it replaces what that screen
currently holds; the rest operate on whatever is already loaded.

Note the difference between the two backtest tools: editor_run_backtest runs
what is in the editor (and picks up parameter edits), while run_backtest is
headless and leaves the editor session untouched.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from .. import config
from ..client import BackendClient
from ..appdata import enum_for
from ..errors import McpToolError
from ..shaping import clamp_limit, round_numbers, strip_bulk

# One kernel namespace per MCP process, so we never share state with the app's
# chat kernels (which are keyed by chat_id).
KERNEL_CHAT_ID = f"mcp:{os.getpid()}-{uuid.uuid4().hex[:8]}"

# Accepted values come from the app's tool registry, not from a copy here.
_SORT_BACKTESTS = enum_for("list_backtests", "sort_by")
_SORT_TRADES = enum_for("get_trades", "sort_by")


async def editor_load_code(
    client: BackendClient, code: str, confirm: bool = False
) -> dict[str, Any]:
    """Load strategy code into the Code Creator, as pasting it there would.

    Returns the parameters, capital settings and auxiliary dataset slots the
    code declares. This is step one of building a strategy: run it, adjust
    parameters, run again, and save once it holds up.
    """
    if not confirm:
        raise McpToolError(
            "This replaces whatever the Code Creator screen currently holds, "
            "including unsaved work. Pass confirm=true to proceed."
        )
    snapshot = await client.post("/strategies/parameters", json={"code": code})
    return round_numbers(
        {
            "parameters": (snapshot or {}).get("parameters"),
            "capital": (snapshot or {}).get("capital"),
            "options": (snapshot or {}).get("options"),
            "auxiliary_datasets": (snapshot or {}).get("auxiliary_datasets"),
            "next_step": "Run it with editor_run_backtest(dataset_id=...).",
        }
    )


async def editor_set_parameters(
    client: BackendClient, updates: dict[str, Any]
) -> dict[str, Any]:
    """Change parameter values on the strategy held in the Code Creator.

    The backend rewrites the code with the new values, so the next
    editor_run_backtest uses them.
    """
    if not updates:
        raise McpToolError("Pass at least one parameter to update.")
    snapshot = await client.post("/strategies/update", json={"updates": updates})
    return round_numbers(
        {
            "parameters": (snapshot or {}).get("parameters"),
            "capital": (snapshot or {}).get("capital"),
            "options": (snapshot or {}).get("options"),
            "applied": updates,
        }
    )


async def editor_run_backtest(
    client: BackendClient,
    dataset_id: str,
    start_time: int | None = None,
    end_time: int | None = None,
    capital_cfg: dict[str, Any] | None = None,
    auxiliary_snapshot_ids: dict[str, str] | None = None,
    intrabar_simulation: bool = False,
    intrabar_timeframe: str | None = None,
) -> dict[str, Any]:
    """Backtest the strategy currently held in the Code Creator.

    Deliberately sends no code, so the run picks up the in-memory version
    including any parameter edits. Trade lists and chart series are omitted;
    page the trades with get_backtest_trades(backtest_id="latest").

    ``intrabar_simulation`` replays each bar at a finer timeframe to resolve
    which of the take-profit and stop-loss was touched first. Without it the
    engine has to assume, and for a strategy whose exits are TP/SL the result
    is optimistic by an unknown margin. Leave ``intrabar_timeframe`` unset to
    use the app's default for the chart timeframe (see
    GET /strategies/intrabar-timeframes/{timeframe}).
    """
    run = await client.post(
        "/strategies/run",
        json={
            "snapshot_id": dataset_id,
            "start_time": start_time,
            "end_time": end_time,
            "capital_cfg": capital_cfg,
            "auxiliary_snapshot_ids": auxiliary_snapshot_ids,
            "intrabar_simulation": intrabar_simulation,
            "intrabar_timeframe": intrabar_timeframe,
        },
        timeout=config.LONG_TIMEOUT,
    )
    execution_error = (run or {}).get("execution_error")
    result = {
        "dataset_id": dataset_id,
        "intrabar_simulation": intrabar_simulation,
        "execution_error": execution_error,
        "parameters": (run or {}).get("parameters"),
        "metrics": strip_bulk((run or {}).get("metrics")),
        "extended_metrics": strip_bulk((run or {}).get("extended_metrics")),
    }
    if execution_error:
        result["hint"] = "Fix the code with editor_load_code and run again."
    else:
        result["next_step"] = (
            "Run the Live-Readiness Audit (mindstrat://msf/parity) and read the "
            "trades with get_backtest_trades('latest'). Then adjust with "
            "editor_set_parameters and re-run, or keep it with "
            "editor_save_to_library and hand off via prepare_optimization."
        )
    return round_numbers(result)


async def editor_save_to_library(
    client: BackendClient,
    name: str,
    dataset_id: str,
    symbol: str | None = None,
    timeframe: str | None = None,
    capital_cfg: dict[str, Any] | None = None,
    auxiliary_snapshot_ids: dict[str, str] | None = None,
    favorite: bool = False,
) -> dict[str, Any]:
    """Save the strategy held in the Code Creator as a saved strategy.

    Requires a successful editor_run_backtest first: the backend saves the
    trades and metrics of that run. symbol and timeframe default to the
    dataset's, as the save dialog prefills them.
    """
    if not symbol or not timeframe:
        catalogue = await client.get("/assets/datasets", params={"limit": 500})
        record = next(
            (
                entry
                for entry in (catalogue or {}).get("datasets", [])
                if entry.get("snapshot_id") == dataset_id
            ),
            None,
        )
        if record is None:
            raise McpToolError(f"Dataset {dataset_id} not found")
        symbol = symbol or record.get("symbol")
        timeframe = timeframe or record.get("timeframe")

    saved = await client.post(
        "/strategies/library/save-strategy",
        json={
            "name": name,
            "symbol": symbol,
            "timeframe": timeframe,
            "hist_id": dataset_id,
            "capital_cfg": capital_cfg,
            "auxiliary_snapshot_ids": auxiliary_snapshot_ids,
            "favorite": favorite,
        },
        timeout=config.LONG_TIMEOUT,
    )
    return {
        "saved_strategy_id": (saved or {}).get("saved_strategy_id"),
        "name": name,
        "symbol": symbol,
        "timeframe": timeframe,
        "dataset_id": dataset_id,
        "note": (
            "Saved without parameter ranges, so pass ranges explicitly when "
            "optimizing it."
        ),
    }


async def list_saved_strategies(
    client: BackendClient,
    symbol: str | None = None,
    timeframe: str | None = None,
    favorite_only: bool = False,
    name_contains: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    """List saved strategies (metadata only)."""
    return await client.get(
        "/ai/tools/list_strategies",
        params={
            "symbol": symbol,
            "timeframe": timeframe,
            "favorite_only": favorite_only,
            "name_contains": name_contains,
            "limit": min(clamp_limit(limit), 50),
            "offset": offset,
        },
    )


async def get_saved_strategy(
    client: BackendClient, strategy_id: str, include_code: bool = False
) -> dict[str, Any]:
    """Fetch one saved strategy; the source code is opt-in."""
    payload = await client.get("/ai/tools/get_strategy", params={"strategy_id": strategy_id})
    if not include_code and isinstance(payload, dict):
        code = payload.get("code")
        if isinstance(code, str):
            payload = dict(payload)
            payload["code"] = None
            payload["code_lines"] = len(code.splitlines())
            payload["code_omitted"] = "Pass include_code=true to retrieve the source."
    return payload


async def list_datasets_for_backtests(
    client: BackendClient, symbol: str | None = None, timeframe: str | None = None
) -> dict[str, Any]:
    """List datasets usable as backtest inputs (dataset_id + coverage)."""
    return await client.get(
        "/ai/tools/list_datasets", params={"symbol": symbol, "timeframe": timeframe}
    )


def _to_epoch_seconds(value: str | int | None, field: str) -> int | None:
    """Accept epoch seconds or an ISO-8601 string and return epoch seconds."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise McpToolError(
            f"{field} must be epoch seconds or an ISO-8601 timestamp, got {value!r}"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())


async def get_intrabar_timeframes(
    client: BackendClient, chart_timeframe: str
) -> dict[str, Any]:
    """The intrabar timeframes the app offers for a chart timeframe."""
    payload = await client.get(f"/strategies/intrabar-timeframes/{chart_timeframe}")
    if isinstance(payload, dict):
        payload = dict(payload)
        payload["note"] = (
            "default_intrabar is what runs when intrabar_timeframe is left "
            "unset. A finer timeframe resolves TP/SL ordering more faithfully "
            "and costs proportionally more wall-clock."
        )
    return payload


async def get_dataset_summary(client: BackendClient, dataset_id: str) -> dict[str, Any]:
    """Coverage and data-quality record for one dataset.

    Reads the same /assets/datasets record the Market Assets screen shows,
    which already carries rows, date range, missing and duplicate counts and
    size. The legacy /ai/tools/get_dataset_summary endpoint is not used: it
    errors on the current parquet schema.
    """
    catalogue = await client.get("/assets/datasets", params={"limit": 500})
    for entry in (catalogue or {}).get("datasets", []):
        if entry.get("snapshot_id") == dataset_id:
            # Same noise discipline as the assets listings: local paths and
            # checksums say nothing about the data and leak filesystem layout.
            return round_numbers(
                {
                    k: v
                    for k, v in entry.items()
                    if k not in ("file_path", "checksum", "symbol_normalized", "timeframe_norm")
                }
            )
    raise McpToolError(f"Dataset {dataset_id} not found in the Market Assets catalogue")


async def get_price_window(
    client: BackendClient,
    dataset_id: str,
    start_time: str | int | None = None,
    end_time: str | int | None = None,
    max_rows: int = 200,
) -> dict[str, Any]:
    """Fetch a bounded OHLCV window (max 500 rows) from a dataset."""
    if max_rows < 1 or max_rows > 500:
        raise McpToolError("max_rows must be between 1 and 500")
    return await client.get(
        f"/strategies/datasets/{dataset_id}/bars",
        params={
            "from": _to_epoch_seconds(start_time, "start_time"),
            "to": _to_epoch_seconds(end_time, "end_time"),
            "limit": max_rows,
        },
    )


async def list_backtests(
    client: BackendClient,
    strategy_id: str | None = None,
    dataset_id: str | None = None,
    min_sharpe: float | None = None,
    sort_by: str = "recent",
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    """List stored backtests with summary metrics."""
    if _SORT_BACKTESTS and sort_by not in _SORT_BACKTESTS:
        raise McpToolError(f"sort_by must be one of {', '.join(_SORT_BACKTESTS)}")
    return round_numbers(
        await client.get(
            "/ai/tools/list_backtests",
            params={
                "strategy_id": strategy_id,
                "dataset_id": dataset_id,
                "min_sharpe": min_sharpe,
                "sort_by": sort_by,
                "limit": min(clamp_limit(limit), 30),
                "offset": offset,
            },
        )
    )


async def get_backtest(client: BackendClient, backtest_id: str = "latest") -> dict[str, Any]:
    """Metrics for one backtest; 'latest' returns the most recent in-session run."""
    payload = await client.get("/ai/tools/get_backtest", params={"backtest_id": backtest_id})
    return round_numbers(strip_bulk(payload))


async def get_backtest_trades(
    client: BackendClient,
    backtest_id: str = "latest",
    side: str | None = None,
    outcome: str | None = None,
    min_pnl_pct: float | None = None,
    max_pnl_pct: float | None = None,
    entry_signal_contains: str | None = None,
    exit_signal_contains: str | None = None,
    sort_by: str = "chronological",
    limit: int = 30,
    offset: int = 0,
) -> dict[str, Any]:
    """Fetch a page of trades (max 30) plus a summary over all matching trades."""
    if side and side not in ("long", "short"):
        raise McpToolError("side must be 'long' or 'short'")
    if outcome and outcome not in ("winners", "losers", "breakeven"):
        raise McpToolError("outcome must be 'winners', 'losers' or 'breakeven'")
    if _SORT_TRADES and sort_by not in _SORT_TRADES:
        raise McpToolError(f"sort_by must be one of {', '.join(_SORT_TRADES)}")
    return round_numbers(
        await client.get(
            "/ai/tools/get_trades",
            params={
                "backtest_id": backtest_id,
                "side": side,
                "outcome": outcome,
                "min_pnl_pct": min_pnl_pct,
                "max_pnl_pct": max_pnl_pct,
                "entry_signal_contains": entry_signal_contains,
                "exit_signal_contains": exit_signal_contains,
                "sort_by": sort_by,
                "limit": max(1, min(limit, 30)),
                "offset": offset,
            },
        )
    )


async def run_backtest(
    client: BackendClient,
    dataset_id: str,
    strategy_id: str | None = None,
    code: str | None = None,
    parameters: dict[str, Any] | None = None,
    auxiliary_dataset_ids: dict[str, str] | None = None,
    strategy_name: str | None = None,
) -> dict[str, Any]:
    """Run a headless backtest from a saved strategy or from raw code."""
    if bool(strategy_id) == bool(code):
        raise McpToolError("Provide exactly one of strategy_id or code.")

    aux = [
        {"slot": slot, "dataset_id": ds_id}
        for slot, ds_id in (auxiliary_dataset_ids or {}).items()
    ]
    params = [{"name": name, "value": value} for name, value in (parameters or {}).items()]

    if strategy_id:
        path = "/ai/tools/run_backtest_from_strategy"
        body: dict[str, Any] = {
            "strategy_id": strategy_id,
            "dataset_id": dataset_id,
            "auxiliary_dataset_ids": aux,
        }
        if params:
            body["params_override"] = params
    else:
        path = "/ai/tools/run_backtest_from_code"
        body = {
            "code": code,
            "dataset_id": dataset_id,
            "auxiliary_dataset_ids": aux,
            "parameters": params,
        }
        if strategy_name:
            body["strategy_name"] = strategy_name

    payload = await client.post(path, json=body, timeout=config.LONG_TIMEOUT)
    shaped = round_numbers(strip_bulk(payload))
    if isinstance(shaped, dict) and not shaped.get("execution_error"):
        shaped["next_step"] = (
            "Run the Live-Readiness Audit (mindstrat://msf/parity) before "
            "presenting these numbers, and read the trades with "
            "get_backtest_trades. A strategy that holds up goes to "
            "prepare_optimization."
        )
    return shaped


async def run_python(
    client: BackendClient,
    code: str,
    reset_kernel: bool = False,
    action: str = "run",
) -> dict[str, Any]:
    """Execute Python in the persistent analysis kernel, or kill that kernel."""
    if action == "kill":
        await client.post("/ai/kernel/kill", json={"chat_id": KERNEL_CHAT_ID})
        return {"killed": True, "kernel": KERNEL_CHAT_ID}
    if action != "run":
        raise McpToolError("action must be 'run' or 'kill'")

    payload = await client.post(
        "/ai/kernel/run",
        json={"chat_id": KERNEL_CHAT_ID, "code": code, "reset_kernel": reset_kernel},
        timeout=config.LONG_TIMEOUT,
    )
    if isinstance(payload, dict):
        payload = dict(payload)
        payload["kernel"] = KERNEL_CHAT_ID
    return payload

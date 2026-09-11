"""Strategy Manager tools: saved strategies, optimizations and their cycles.

Backend surface: /manager (no auth).

Payload discipline matters here more than anywhere else. A raw
/manager/strategies/{id}/detail response is multi-megabyte (full trade list,
every candle and indicator series), and /manager/optimizations/{id}/metadata
carries per-cycle Monte Carlo input curves. Detail responses are therefore
stripped before returning, with drill-down tools for the parts that matter.

Robustness metrics (HoldOut train/val/full, WalkForwardRolling per-fold is_*
and val_* fields, Monte Carlo scores) are passed through verbatim: they must be
read from the backend, never recomputed from the trade list.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Mapping, Sequence
from typing import Any

from .. import config
from ..client import BackendClient
from ..errors import McpToolError
from ..shaping import clamp_limit, envelope, paginate, round_numbers, strip_bulk

# Backends page these endpoints at a fixed 100 records.
BACKEND_PAGE_SIZE = 100

# Each robustness test is served over a different channel, because each is a
# different kind of result: Hold-Out belongs to a candidate and is identified
# by its parameters, Monte Carlo belongs to a cycle and is identified by its
# number, and rolling folds belong to the run. Looking for one in the other's
# place makes a test that ran look like it produced nothing.
_RESULTS_LOCATION = {
    "HoldOut": (
        "Per cycle: the `holdout` block on each row of list_optimization_cycles, "
        "and the train/validation/full comparison in get_cycle_robustness."
    ),
    "MonteCarloTrades": (
        "Per cycle: mc_score and mc_tier on each row of list_optimization_cycles, "
        "and the full breakdown in get_cycle_robustness."
    ),
    "WalkForwardRolling": "Run level: the folds and curves in this response.",
    "IntrabarSimulation": (
        "Not a result: it changes how every cycle is simulated, resolving which "
        "of TP/SL was touched first inside a bar."
    ),
}


def _summarise_robustness(robustness: Any) -> Any:
    """Replace per-cycle robustness blobs with counts and cycle numbers."""
    if not isinstance(robustness, dict):
        return robustness
    summary: dict[str, Any] = {}
    for test_name, entries in robustness.items():
        if test_name == "WalkForwardRolling" and isinstance(entries, dict):
            # A run-level document, not a per-cycle map. The folds count IS
            # the verification the doctrine demands: a rolling run killed by
            # RAM reads 'finished' with 0 folds and no error.
            folds = entries.get("folds")
            summary[test_name] = {
                "folds": len(folds) if isinstance(folds, (list, dict)) else 0,
                "has_analytics": isinstance(entries.get("analytics"), dict),
                "hint": (
                    "Run-level result. 0 folds on a finished run means the "
                    "rolling test died silently — do not trust the run. "
                    "Attach with attach_rolling_to_strategy and read the "
                    "folds in get_strategy_detail."
                ),
            }
        elif isinstance(entries, dict):
            cycles = sorted(entries.keys(), key=lambda k: int(k) if str(k).isdigit() else 0)
            summary[test_name] = {
                "cycles_with_results": len(cycles),
                "cycles": cycles[:25],
                "hint": f"Use get_cycle_robustness for one cycle's {test_name} results.",
            }
        else:
            summary[test_name] = strip_bulk(entries)
    return summary


async def _fetch_detail(client: BackendClient, path: str) -> dict[str, Any]:
    """Fetch a heavy detail response.

    Not cached: the app fetches this endpoint fresh every time it opens a
    detail view, and the response re-runs the backtest, so a cached copy could
    disagree with the app after any edit.
    """
    payload = await client.get(path, timeout=config.LONG_TIMEOUT)
    if not isinstance(payload, dict):
        raise McpToolError(f"Unexpected detail response for {path}")
    return payload


def _shape_detail(payload: dict[str, Any], include_code: bool) -> dict[str, Any]:
    """Strip bulk series and duplicate blocks from a strategy/cycle detail."""
    # `info` duplicates `strategy`; drop it rather than doubling the output.
    result = strip_bulk({k: v for k, v in payload.items() if k != "info"})

    strategy = result.get("strategy")
    if isinstance(strategy, dict):
        code = strategy.get("strategy_code")
        if isinstance(code, str) and not include_code:
            strategy = dict(strategy)
            strategy["strategy_code"] = None
            strategy["strategy_code_lines"] = len(code.splitlines())
            result["strategy"] = strategy

    trades = payload.get("trades")
    if isinstance(trades, list):
        result["trades_available"] = len(trades)
        result["trades_hint"] = "Use get_strategy_trades to page through them."
    return round_numbers(result)


async def list_manager_strategies(
    client: BackendClient,
    search: str | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
    robust: list[str] | None = None,
    favorite: bool = False,
    metrics_filter: str | dict[str, Any] | None = None,
    sort: str | None = None,
    page: int = 1,
    limit: int | None = None,
) -> dict[str, Any]:
    """List saved strategies in the manager with filters and sorting.

    metrics_filter accepts the dict form as well as its JSON string: some MCP
    clients parse a JSON-shaped string argument into an object before sending,
    so a string-only parameter would be unusable through them.
    """
    if isinstance(metrics_filter, dict):
        metrics_filter = json.dumps(metrics_filter)
    payload = await client.get(
        "/manager/strategies",
        params={
            "page": max(page, 1),
            "search": search,
            "symbol": symbol,
            "timeframe": timeframe,
            "robust": robust,
            "favorite": favorite,
            "metrics": metrics_filter,
            "sort": sort,
        },
    )
    results = (payload or {}).get("results", [])
    size = clamp_limit(limit)
    trimmed = [
        round_numbers(strip_bulk(record, extra_keys=("snapshot_path", "history_file")))
        for record in results[:size]
    ]
    return {
        "items": trimmed,
        "count": len(trimmed),
        "total": (payload or {}).get("total"),
        "page": (payload or {}).get("page", page),
        "backend_page_size": (payload or {}).get("page_size", BACKEND_PAGE_SIZE),
        "truncated_from_page": len(results) > size,
    }


async def get_strategy_detail(
    client: BackendClient, strategy_id: int, include_code: bool = False
) -> dict[str, Any]:
    """Metrics, extended metrics and robustness for one saved strategy.

    Trade lists and chart series are omitted; robustness values (HoldOut
    train/val/full, per-fold is_*/val_*, Monte Carlo) come straight from the
    backend.
    """
    payload = await _fetch_detail(client, f"/manager/strategies/{strategy_id}/detail")
    return _shape_detail(payload, include_code)


def _is_final_close(trade: Mapping[str, Any]) -> bool:
    """A row that closes a position for good — what the app's metrics count.

    Partial closes carry ``is_final_close: False`` and are excluded, exactly
    as the app's own trade counting excludes them; the default True preserves
    strategies from before partial closes existed.
    """
    return (
        str(trade.get("type", "")).lower() == "close"
        and bool(trade.get("is_final_close", True))
    )


async def get_strategy_trades(
    client: BackendClient,
    strategy_id: int,
    event_type: str | None = None,
    outcome: str | None = None,
    min_profit: float | None = None,
    max_profit: float | None = None,
    signal_contains: str | None = None,
    sort_by: str = "chronological",
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    """Page through a saved strategy's trade events, filtered and summarised.

    The stored list is the engine's raw event log — open and close rows, not
    paired positions — so profit lives on the close rows, and the outcome and
    profit filters implicitly narrow to final closes. The summary aggregates
    the matching final closes only; the strategy's headline metrics still come
    from get_strategy_detail, never from recomputing this list.
    """
    if event_type and event_type not in ("open", "close"):
        raise McpToolError("event_type must be 'open' or 'close'")
    if outcome and outcome not in ("winners", "losers", "breakeven"):
        raise McpToolError("outcome must be 'winners', 'losers' or 'breakeven'")
    if sort_by not in ("chronological", "profit_desc", "profit_asc"):
        raise McpToolError(
            "sort_by must be 'chronological', 'profit_desc' or 'profit_asc'"
        )

    payload = await _fetch_detail(client, f"/manager/strategies/{strategy_id}/detail")
    rows = [t for t in (payload.get("trades") or []) if isinstance(t, Mapping)]

    def profit_of(trade: Mapping[str, Any]) -> float:
        try:
            return float(trade.get("profit") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    if event_type:
        rows = [t for t in rows if str(t.get("type", "")).lower() == event_type]
    if outcome:
        keep = {
            "winners": lambda p: p > 0,
            "losers": lambda p: p < 0,
            "breakeven": lambda p: p == 0,
        }[outcome]
        rows = [t for t in rows if _is_final_close(t) and keep(profit_of(t))]
    if min_profit is not None or max_profit is not None:
        rows = [
            t for t in rows
            if _is_final_close(t)
            and (min_profit is None or profit_of(t) >= min_profit)
            and (max_profit is None or profit_of(t) <= max_profit)
        ]
    if signal_contains:
        needle = signal_contains.lower()
        rows = [t for t in rows if needle in str(t.get("signal") or "").lower()]

    if sort_by != "chronological":
        rows = sorted(rows, key=profit_of, reverse=sort_by == "profit_desc")

    profits = [profit_of(t) for t in rows if _is_final_close(t)]
    summary = {
        "closed_trades": len(profits),
        "sum_profit": sum(profits),
        "avg_profit": sum(profits) / len(profits) if profits else 0.0,
        "win_rate_pct": (
            sum(1 for p in profits if p > 0) / len(profits) * 100.0 if profits else 0.0
        ),
    }

    page = paginate(rows, limit, offset)
    page["summary_of_matching"] = summary
    return round_numbers(page)


async def list_optimizations(
    client: BackendClient,
    search: str | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
    status: str | None = None,
    method: str | None = None,
    robust: list[str] | None = None,
    sort: str | None = None,
    page: int = 1,
    limit: int | None = None,
) -> dict[str, Any]:
    """List optimization runs with filters and sorting."""
    payload = await client.get(
        "/manager/optimizations",
        params={
            "page": max(page, 1),
            "search": search,
            "symbol": symbol,
            "timeframe": timeframe,
            "status": status,
            "method": method,
            "robust": robust,
            "sort": sort,
        },
    )
    results = (payload or {}).get("results", [])
    size = clamp_limit(limit)
    return {
        "items": round_numbers(results[:size]),
        "count": min(len(results), size),
        "total": (payload or {}).get("total"),
        "page": (payload or {}).get("page", page),
        "truncated_from_page": len(results) > size,
    }


async def get_optimization_summary(client: BackendClient, opt_id: int) -> dict[str, Any]:
    """Status and headline numbers for an optimization run.

    Uses the metadata endpoint, which never returns cycle rows. Per-cycle
    robustness payloads are summarised to cycle counts.
    """
    payload = await client.get(f"/manager/optimizations/{opt_id}/metadata")
    if not isinstance(payload, dict):
        raise McpToolError(f"Unexpected metadata response for optimization {opt_id}")

    active = payload.get("active_tests") or []
    robustness = _summarise_robustness(payload.get("robustness"))
    if isinstance(robustness, dict):
        # Hold-Out results are stored per candidate, keyed by its parameters,
        # so they never appear in this map — the app attaches them to each
        # cycle row instead. Saying so here stops its absence from reading as
        # "the test produced nothing".
        for name in active:
            if name not in robustness:
                robustness[name] = {"results_in": _RESULTS_LOCATION.get(
                    name, "Not reported in this response."
                )}

    return round_numbers(
        {
            "optimization": payload.get("optimization"),
            "total_cycles": payload.get("total_cycles"),
            "active_tests": active,
            "robustness": robustness,
        }
    )


async def list_optimization_cycles(
    client: BackendClient,
    opt_id: int,
    page: int = 1,
    page_size: int | None = None,
    sort_by: str = "cycle",
    sort_order: str = "asc",
    min_profit: float | None = None,
    max_profit: float | None = None,
    min_trades: int | None = None,
    max_drawdown: float | None = None,
    min_winrate: float | None = None,
) -> dict[str, Any]:
    """Page through the cycles of an optimization, sorted and filtered.

    Each row carries the three families the manager's table shows: the cycle's
    own metrics, its Hold-Out block, and its Monte Carlo score. Sorting and
    filtering happen in the backend, but only over the cycle's own metrics —
    Hold-Out and Monte Carlo are joined per row afterwards, exactly as the
    screen does it, so they cannot narrow a large run on their own.
    """
    if sort_order not in ("asc", "desc"):
        raise McpToolError("sort_order must be 'asc' or 'desc'")

    size = max(10, clamp_limit(page_size))
    payload = await client.get(
        f"/manager/optimizations/{opt_id}/cycles",
        params={
            "page": max(page, 1),
            "page_size": size,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "min_profit": min_profit,
            "max_profit": max_profit,
            "min_trades": min_trades,
            "max_drawdown": max_drawdown,
            "min_winrate": min_winrate,
        },
        timeout=config.LONG_TIMEOUT,
    )
    shaped = strip_bulk(payload)
    if isinstance(shaped, dict) and shaped.get("cycles"):
        # Monte Carlo rides each cycle row (`mc`, attached per page by the
        # backend); project it to the manager's score/tier columns. Missing
        # scores are not an error: a run without the test, or with it
        # triggered every N cycles, simply has few.
        for row in shaped["cycles"]:
            if isinstance(row, dict):
                mc_entry = row.pop("mc", None)
                if isinstance(mc_entry, Mapping):
                    row["mc_score"] = mc_entry.get("robustness_score")
                    row["mc_tier"] = mc_entry.get("robustness_tier")
    return round_numbers(shaped)


async def get_cycle_detail(
    client: BackendClient, opt_id: int, cycle: int, include_code: bool = False
) -> dict[str, Any]:
    """Full result of one optimization cycle, with bulk series stripped."""
    payload = await _fetch_detail(
        client,
        f"/manager/optimizations/{opt_id}/cycles/{cycle}/detail",
    )
    return _shape_detail(payload, include_code)


def _curve_shape(curve: Sequence[float] | None) -> dict[str, Any] | None:
    """What a reader would take from looking at an equity curve, as numbers.

    The curve itself is thousands of points and reads poorly as a list of
    decimals; these answer the questions the picture answers. Whether the
    profit is one jump or many, and how much of the time the strategy spends
    below its previous high, decide more than the shape of the line.
    """
    if not curve or len(curve) < 3:
        return None
    steps = [curve[i + 1] - curve[i] for i in range(len(curve) - 1)]
    final = curve[-1]
    peak, underwater, at_high, worst_dd = curve[0], 0, 0, 0.0
    for point in curve:
        peak = max(peak, point)
        gap = peak - point
        worst_dd = max(worst_dd, gap)
        if gap <= 1e-9:
            at_high += 1
        else:
            underwater += 1
    magnitudes = sorted((abs(s) for s in steps), reverse=True)
    scale = abs(final) if abs(final) > 1e-9 else None
    return {
        "final": round(final, 4),
        "worst_drawdown": round(-worst_dd, 4),
        "pct_time_at_high": round(at_high / len(curve) * 100, 1),
        "pct_time_underwater": round(underwater / len(curve) * 100, 1),
        "biggest_step_pct_of_total": (
            round(magnitudes[0] / scale * 100, 1) if scale else None
        ),
        "top5_steps_pct_of_total": (
            round(sum(magnitudes[:5]) / scale * 100, 1) if scale else None
        ),
    }


def _holdout_comparison(
    stored: Mapping[str, Any] | None, replayed: Mapping[str, Any] | None
) -> dict[str, Any]:
    """The detail view's comparison table: train, validation and full period.

    Train and validation come from the entry the run stored, keyed by the
    candidate's parameters; the full period is the replay the detail endpoint
    recomputes. Runs from older versions stored only the validation half, so
    the train column can legitimately be missing.
    """
    stored = stored if isinstance(stored, Mapping) else {}
    replayed = replayed if isinstance(replayed, Mapping) else {}
    full = replayed.get("full_metrics") if isinstance(replayed, Mapping) else None
    full = full if isinstance(full, Mapping) else {}

    rows: dict[str, Any] = {}
    for label, is_key, val_key, full_key in (
        ("net_profit", "is_pnl", "val_pnl", "profit"),
        ("roi_pct", "is_roi", "val_roi", "roi"),
        ("win_rate", "is_win%", "val_win%", "winrate"),
        ("trades", "is_trades", "val_trades", "trades"),
        ("profit_factor", "is_pf", "val_pf", "pf"),
        ("max_drawdown", "is_dd", "val_dd", "drawdown"),
        ("avg_trade", "is_avg", "val_avg", "avg"),
    ):
        row = {
            "train": _as_number(stored.get(is_key)),
            "validation": _as_number(stored.get(val_key)),
            "full_period": _as_number(full.get(full_key)),
        }
        if any(v is not None for v in row.values()):
            rows[label] = row

    result: dict[str, Any] = {"comparison": rows}
    if replayed.get("cfg"):
        result["cfg"] = replayed["cfg"]
    if not any(r.get("train") is not None for r in rows.values()):
        result["note"] = (
            "No train column: this run stored only the validation half. Its "
            "in-sample metrics are the cycle's own metrics, from "
            "list_optimization_cycles."
        )
    return result


def _as_number(value: Any) -> float | int | None:
    """Stored robustness metrics are strings; comparisons need numbers."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else round(number, 4)


def _monte_carlo_report(mc: Mapping[str, Any], mode: str | None) -> dict[str, Any]:
    """The Monte Carlo tab, without the simulations themselves."""
    report: dict[str, Any] = {
        "robustness_score": mc.get("robustness_score"),
        "robustness_tier": mc.get("robustness_tier"),
        "scorer_version": mc.get("scorer_version"),
        "simulations": sum(int(r.get("n") or 0) for r in (mc.get("runs") or [])),
        "base_stats": mc.get("base_stats"),
        "summary": mc.get("summary"),
        "probabilities": mc.get("probabilities"),
        "distribution_shape": mc.get("distribution_shape"),
        "histograms": mc.get("histograms"),
        "policy_weights": mc.get("policy_weights"),
        "per_mode": mc.get("per_mode_table") or mc.get("robustness_per_mode"),
        "costs_tested": mc.get("costs_tested"),
    }
    if mode:
        table = mc.get("per_mode_table") or mc.get("robustness_per_mode") or []
        match = next(
            (row for row in table if isinstance(row, Mapping) and row.get("mode") == mode),
            None,
        )
        if match is None:
            known = sorted(
                str(row.get("mode"))
                for row in table
                if isinstance(row, Mapping) and row.get("mode")
            )
            raise McpToolError(
                f"This cycle has no Monte Carlo mode '{mode}'. It ran: "
                f"{', '.join(known) or 'none'}."
            )
        report["mode"] = match

    best = _curve_shape(mc.get("best_curve"))
    worst = _curve_shape(mc.get("worst_curve"))
    if best or worst:
        report["extreme_paths"] = {"best": best, "worst": worst}
    report["curves_hint"] = (
        "The simulated curves are not returned: a run is thousands of points "
        "and the analysis above already summarises them. To compute on them, "
        "use run_python with ms.manager.monte_carlo(opt_id, cycle), which "
        "splits the curves by perturbation mode inside the kernel."
    )
    return report


async def get_cycle_robustness(
    client: BackendClient,
    opt_id: int,
    cycle: int,
    test: str | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Robustness results of one cycle, as the detail view shows them.

    Hold-Out arrives as the train / validation / full-period comparison, and
    Monte Carlo as its score, per-mode breakdown and outcome distribution.
    No simulated curves: see the hint the report carries.
    """
    wanted = _resolve_test(test)

    detail = await _fetch_detail(
        client, f"/manager/optimizations/{opt_id}/cycles/{cycle}/detail"
    )
    robustness = detail.get("robustness")
    robustness = robustness if isinstance(robustness, Mapping) else {}

    report: dict[str, Any] = {
        "opt_id": opt_id,
        "cycle": cycle,
        "params": detail.get("params"),
        "tests_available": sorted(robustness),
    }

    if wanted in (None, "HoldOut") and "HoldOut" in robustness:
        stored = await _stored_holdout(client, opt_id, cycle)
        report["HoldOut"] = _holdout_comparison(stored, robustness.get("HoldOut"))

    if wanted in (None, "MonteCarloTrades"):
        mc = robustness.get("MonteCarloTrades")
        if isinstance(mc, Mapping):
            report["MonteCarloTrades"] = _monte_carlo_report(mc, mode)
        elif wanted == "MonteCarloTrades":
            raise McpToolError(f"Cycle {cycle} of optimization {opt_id} has no Monte Carlo result.")

    shape = _curve_shape(_equity_curve(detail))
    if shape:
        report["equity_shape"] = shape
    return round_numbers(report)


def _resolve_test(test: str | None) -> str | None:
    if test is None:
        return None
    for known in ("HoldOut", "MonteCarloTrades"):
        if test.lower() == known.lower():
            return known
    raise McpToolError(
        "test must be 'HoldOut' or 'MonteCarloTrades'. Walk-forward rolling is "
        "a run-level result: read it with get_optimization_summary."
    )


def _equity_curve(detail: Mapping[str, Any]) -> list[float] | None:
    """The cycle's own equity curve, as the replay returns it."""
    for holder in (detail.get("robustness") or {}), detail:
        block = holder.get("HoldOut") if isinstance(holder, Mapping) else None
        metrics = block.get("full_metrics") if isinstance(block, Mapping) else None
        curve = metrics.get("profits") if isinstance(metrics, Mapping) else None
        if isinstance(curve, list) and curve:
            return _cumulative(curve)
    return None


def _cumulative(profits: Sequence[Any]) -> list[float]:
    """Per-trade P&L to an equity curve, the way the simulations build theirs."""
    total = 0.0
    curve = [0.0]
    for value in profits:
        try:
            total += float(value)
        except (TypeError, ValueError):
            continue
        curve.append(total)
    return curve


async def _stored_holdout(
    client: BackendClient, opt_id: int, cycle: int
) -> dict[str, Any] | None:
    """The Hold-Out entry the run stored for this cycle.

    The detail endpoint recomputes the full period but does not return the
    train/validation split, so the two halves come from the cycles endpoint —
    the same place the manager's Hold columns read them.
    """
    size = BACKEND_PAGE_SIZE

    async def rows_on(page: int) -> list[dict[str, Any]]:
        payload = await client.get(
            f"/manager/optimizations/{opt_id}/cycles",
            params={"page": max(page, 1), "page_size": size,
                    "sort_by": "cycle", "sort_order": "asc"},
            timeout=config.LONG_TIMEOUT,
        )
        return (payload or {}).get("cycles") or []

    # Cycle numbers are dense, so the page follows from the number. A rejected
    # candidate leaves a gap, so if the guess misses, correct it once by how
    # far off the page's first cycle turned out to be.
    guess = (max(cycle, 1) - 1) // size + 1
    for attempt in range(2):
        rows = await rows_on(guess)
        if not rows:
            return None
        for row in rows:
            if row.get("cycle") == cycle:
                holdout = row.get("holdout")
                return holdout if isinstance(holdout, Mapping) else None
        if attempt:
            return None
        first = rows[0].get("cycle")
        if not isinstance(first, int):
            return None
        guess += (cycle - first) // size
    return None


async def list_metric_filters(client: BackendClient) -> dict[str, Any]:
    """The metric vocabulary a metrics_filter can be built from.

    The keys and operators come from the backend's own filter configuration,
    so a filter built from this response is one the backend accepts rather
    than one that silently matches nothing.
    """
    sections = await client.get("/manager/strategies/metric-sections")
    return round_numbers(
        {
            "sections": sections,
            "operators": ["OFF", ">=", "<=", ">", "<", "==", "!=", "BETWEEN"],
            "example": {
                "strategy": {
                    "profit": {"op": ">=", "val": 0},
                    "trades": {"op": "BETWEEN", "min": 30, "max": 500},
                }
            },
            "note": (
                "Pass the example's shape as metrics_filter to "
                "list_manager_strategies — as a JSON object or its string "
                "form. BETWEEN takes min/max; every other operator takes val; "
                "OFF disables a rule without removing it."
            ),
        }
    )


async def list_portfolios(
    client: BackendClient, name: str | None = None, limit: int | None = None
) -> dict[str, Any]:
    """List portfolios with their strategy counts and metric summaries."""
    payload = await client.get("/manager/portfolios", params={"name": name})
    results = (payload or {}).get("results", [])
    size = clamp_limit(limit)
    return envelope(round_numbers(results[:size]), total=len(results))


async def get_portfolio(client: BackendClient, portfolio_id: int) -> dict[str, Any]:
    """One portfolio's analysis, with the bulk series stripped.

    The backend computes the aggregates — combined totals, metrics, member
    contributions — and they pass through as computed. This response carries
    bulk under its own key names, so they are stripped explicitly on top of
    the shared set: ``portfolio_trades`` (each member's merged trade log),
    ``series`` (the combined and per-member equity curves), and the members'
    local file paths.
    """
    payload = await client.get(f"/manager/portfolios/{portfolio_id}")
    if not isinstance(payload, dict):
        raise McpToolError(f"Unexpected portfolio response for {portfolio_id}")
    return round_numbers(
        strip_bulk(
            payload,
            extra_keys=("portfolio_trades", "series", "snapshot_path", "history_file"),
        )
    )


async def update_strategy_meta(
    client: BackendClient,
    strategy_id: int,
    favorite: bool | None = None,
    name: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Set favorite flag, rename, and/or change the description of a strategy."""
    applied: dict[str, Any] = {}
    if favorite is not None:
        await client.post(f"/manager/strategies/{strategy_id}/favorite", json={"value": favorite})
        applied["favorite"] = favorite
    if name is not None:
        await client.post(f"/manager/strategies/{strategy_id}/rename", json={"name": name})
        applied["name"] = name
    if description is not None:
        await client.post(
            f"/manager/strategies/{strategy_id}/description", json={"description": description}
        )
        applied["description"] = description

    if not applied:
        raise McpToolError("Provide at least one of favorite, name or description.")
    return {"strategy_id": strategy_id, "updated": applied}


async def _find_cycle_record(
    client: BackendClient, opt_id: int, cycle: int
) -> dict[str, Any]:
    """Locate one cycle's stored row in the paginated cycles listing.

    The listing has no by-cycle filter, so this walks it ordered by cycle
    number, which puts the wanted cycle in the first page in the common case
    of contiguous numbering.
    """
    page_size = 500
    page = max(1, (cycle - 1) // page_size + 1)
    for candidate_page in (page, *(p for p in range(1, 21) if p != page)):
        payload = await client.get(
            f"/manager/optimizations/{opt_id}/cycles",
            params={
                "page": candidate_page,
                "page_size": page_size,
                "sort_by": "cycle",
                "sort_order": "asc",
            },
        )
        rows = (payload or {}).get("cycles") or []
        if not rows:
            break
        for row in rows:
            if int(row.get("cycle", -1)) == cycle:
                return row
        if candidate_page >= (payload or {}).get("total_pages", 1):
            break
    raise McpToolError(f"Cycle {cycle} not found in optimization {opt_id}")


async def save_cycle_as_strategy(
    client: BackendClient,
    opt_id: int,
    cycle: int,
    favorite: bool = False,
    wait_seconds: int = 20,
) -> dict[str, Any]:
    """Persist an optimization cycle as a saved strategy (async job).

    Mirrors what the app saves: the params and metrics recorded for the cycle
    during the run, taken from the cycles list, plus history_file and
    dataset_id from the optimization metadata. The cycle detail endpoint is
    deliberately not used as the source — it re-runs the backtest and its
    metrics can differ from the ones the run recorded.
    """
    metadata = await client.get(f"/manager/optimizations/{opt_id}/metadata")
    # The app reads both of these off `info` on the same response.
    info = (metadata or {}).get("info") or {}

    history_file = info.get("history_file") or ""
    if not history_file:
        raise McpToolError(
            f"Optimization {opt_id} has no history_file recorded; the backend "
            "cannot rebuild the strategy from a cycle without it."
        )

    record = await _find_cycle_record(client, opt_id, cycle)

    job = await client.post(
        "/manager/snapshots",
        json={
            "opt_id": opt_id,
            "cycle": cycle,
            "params": record.get("params") or {},
            "metrics": record.get("metrics") or {},
            "history_file": history_file,
            "dataset_id": info.get("dataset_id"),
            "favorite": favorite,
        },
    )

    job_id = (job or {}).get("id")
    deadline = time.monotonic() + max(wait_seconds, 0)
    while job_id and time.monotonic() < deadline:
        if (job or {}).get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
            break
        await asyncio.sleep(1.0)
        job = await client.get(f"/manager/snapshots/jobs/{job_id}")

    result = {"job": job, "poll_with": "get_manager_job_status(kind='snapshot')"}
    if (job or {}).get("status") == "COMPLETED":
        result["next_step"] = _SNAPSHOT_DONE_NEXT_STEP
    return result


async def create_strategy_from_rolling(
    client: BackendClient,
    opt_id: int,
    base_params: dict[str, Any] | None = None,
    favorite: bool = False,
) -> dict[str, Any]:
    """Graduate a TEMPLATE-origin rolling run into a new saved strategy.

    The backend re-runs a full backtest of the default parameters for the
    overview and carries the whole WalkForwardRolling bucket into the new
    snapshot, which is why this takes the long timeout. Saved-strategy rolling
    runs merge into their existing snapshot with attach_rolling_to_strategy
    instead — the backend refuses nothing here, so the routing is this
    server's to get right.
    """
    result = await client.post(
        "/manager/strategies/from-rolling",
        json={
            "opt_id": opt_id,
            "base_params": base_params or {},
            "favorite": favorite,
        },
        timeout=config.LONG_TIMEOUT,
    )
    saved_id = (result or {}).get("saved_strategy_id")
    return {
        "saved_strategy_id": saved_id,
        "next_step": (
            f"Open get_strategy_detail({saved_id}) and confirm the "
            "WalkForwardRolling folds are present and non-empty — a rolling "
            "run killed by RAM reads 'finished' with 0 folds and no error."
        ),
    }


async def manage_portfolio(
    client: BackendClient,
    action: str,
    portfolio_id: int | None = None,
    name: str | None = None,
    description: str | None = None,
    strategy_id: int | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Create, update or delete a portfolio, or add a strategy to one."""
    if action == "create":
        if not name:
            raise McpToolError("create requires name.")
        record = await client.post(
            "/manager/portfolios", json={"name": name, "description": description}
        )
        result = {"action": "create", "portfolio": round_numbers(strip_bulk(record))}
        result["next_step"] = (
            "Add validated strategies with action='add_strategy', then read "
            "the combined book with get_portfolio."
        )
        return result

    if action == "update":
        if portfolio_id is None or not name:
            # The backend's update replaces both fields, so a rename without
            # the name would silently blank it.
            raise McpToolError("update requires portfolio_id and name (description optional).")
        record = await client.put(
            f"/manager/portfolios/{portfolio_id}",
            json={"name": name, "description": description},
        )
        return {"action": "update", "portfolio": round_numbers(strip_bulk(record))}

    if action == "add_strategy":
        if portfolio_id is None or strategy_id is None:
            raise McpToolError("add_strategy requires portfolio_id and strategy_id.")
        await client.post(
            f"/manager/portfolios/{portfolio_id}/strategies",
            json={"strategy_id": strategy_id},
        )
        return {
            "action": "add_strategy",
            "portfolio_id": portfolio_id,
            "strategy_id": strategy_id,
            "next_step": f"get_portfolio({portfolio_id}) shows the combined book.",
        }

    if action == "delete":
        if portfolio_id is None:
            raise McpToolError("delete requires portfolio_id.")
        if not confirm:
            raise McpToolError(
                f"Refusing to delete portfolio {portfolio_id}: pass confirm=true "
                "to proceed. Member strategies survive; the grouping does not."
            )
        await client.delete(f"/manager/portfolios/{portfolio_id}")
        return {"action": "delete", "portfolio_id": portfolio_id, "deleted": True}

    raise McpToolError(
        "action must be 'create', 'update', 'add_strategy' or 'delete'."
    )


async def delete_manager_items(
    client: BackendClient, target_type: str, target_id: int, confirm: bool = False
) -> dict[str, Any]:
    """Queue deletion of a saved strategy or a whole optimization run."""
    if target_type not in ("strategy", "optimization"):
        raise McpToolError("target_type must be 'strategy' or 'optimization'")
    if not confirm:
        raise McpToolError(
            f"Refusing to delete {target_type} {target_id}: pass confirm=true to proceed."
        )

    job = await client.post(
        "/manager/deletions", json={"target_type": target_type, "target_id": target_id}
    )
    return {"job": job, "poll_with": "get_manager_job_status(kind='deletion')"}


# The bridge from a run's winner to the validation pass: the saved strategy is
# a candidate, not a result, until the finalist tests have run against it.
_SNAPSHOT_DONE_NEXT_STEP = (
    "The job's saved_strategy_id is the finalist: run validate_finalist on it "
    "(rolling folds + the harsh Monte Carlo modes + intrabar) before trusting "
    "it, and record the selection reason with update_strategy_meta."
)


async def get_manager_job_status(
    client: BackendClient, kind: str, job_id: str | None = None
) -> dict[str, Any]:
    """Poll snapshot or deletion jobs queued by the manager."""
    if kind not in ("snapshot", "deletion"):
        raise McpToolError("kind must be 'snapshot' or 'deletion'")
    base = "/manager/snapshots/jobs" if kind == "snapshot" else "/manager/deletions/jobs"

    if job_id:
        job = await client.get(f"{base}/{job_id}")
        if (
            kind == "snapshot"
            and isinstance(job, dict)
            and job.get("status") == "COMPLETED"
        ):
            job = dict(job)
            job["next_step"] = _SNAPSHOT_DONE_NEXT_STEP
        return job
    jobs = await client.get(base)
    return {"items": jobs or [], "count": len(jobs or [])}

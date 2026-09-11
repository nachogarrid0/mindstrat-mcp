"""Helpers that keep tool outputs small enough for a model context window.

Several backend endpoints return multi-megabyte payloads (full trade lists,
candle series, indicator series). Tools must never return those raw.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from . import config

# Keys carrying bulk series that must be stripped from detail responses.
# Matched at any nesting depth: several endpoints bury full trade lists and
# candle series inside nested metric objects.
BULK_KEYS = frozenset(
    {
        "trades",
        "trades_list",
        "charts",
        "bars",
        "candles",
        "markers",
        "indicators",
        "indicatorSeries",
        "profits",
        "profits_curve",
        "closed_trade_times",
        "base_curve",
        "concat_curve",
        "equity_curve",
        "input_profits",
        "legs",
        "events",
        # A Walk-Forward Rolling bucket carries its concatenated OOS trade log
        # and the fixed-base counterpart — 16 KB each on a small run. The
        # analytics block already summarises what they say.
        "concat_trades",
        "base_trades",
        # A cycle detail regenerates every Monte Carlo simulation from its
        # saved seeds: 8 modes x 200 runs of a few hundred points each, which
        # is 97% of a 7 MB response. The analysis that comes with them —
        # per-mode scores, the histogram, the distribution shape — is ~12 KB.
        "curves",
        "best_curve",
        "worst_curve",
    }
)

# Keys that are bulk only in one of their shapes. Monte Carlo returns the
# metrics of each simulation as a list beside its curves, while every other
# `metrics` in the app is a single object worth keeping.
BULK_WHEN_LIST = frozenset({"metrics"})


def clamp_limit(limit: int | None) -> int:
    if not limit or limit < 1:
        return config.DEFAULT_LIMIT
    return min(limit, config.MAX_LIMIT)


def round_numbers(value: Any, digits: int = 4) -> Any:
    """Round floats recursively; keeps payloads readable and compact."""
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, dict):
        return {k: round_numbers(v, digits) for k, v in value.items()}
    if isinstance(value, list):
        return [round_numbers(v, digits) for v in value]
    return value


def pick(
    source: Any, keys: Iterable[str], drop: Iterable[str] = ()
) -> dict[str, Any]:
    """Keep the named keys first, then every other scalar the app sent.

    The named keys fix a useful order; they are not a filter. Whatever else is
    scalar comes through too, so a field the app adds tomorrow reaches the
    caller instead of vanishing. ``drop`` is the small, explicit set of fields
    that are known noise — local paths, checksums — and nested lists and dicts
    are left out because they are the bulk these listings exist to avoid.
    """
    if not isinstance(source, dict):
        return {}
    excluded = set(drop)
    chosen = {k: source[k] for k in keys if k in source and k not in excluded}
    for key, value in source.items():
        if key in chosen or key in excluded:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            chosen[key] = value
    return chosen


def strip_bulk(
    payload: Any, extra_keys: Iterable[str] = (), _depth: int = 0
) -> Any:
    """Drop bulk series keys at any depth, recording what was dropped.

    Endpoints nest full trade lists and candle series inside metric objects
    (e.g. metrics.extended.trades_list), so a top-level-only strip leaks them.
    """
    if _depth > 8:
        return payload
    if isinstance(payload, list):
        return [strip_bulk(item, extra_keys, _depth + 1) for item in payload]
    if not isinstance(payload, dict):
        return payload

    always_drop = set(extra_keys)
    kept: dict[str, Any] = {}
    dropped: dict[str, int] = {}
    for key, value in payload.items():
        # Bulk keys are dropped only when they actually hold a series: a scalar
        # named "trades" is a trade count and must survive.
        is_bulk = (
            key in always_drop
            or (key in BULK_KEYS and isinstance(value, (list, dict)))
            or (key in BULK_WHEN_LIST and isinstance(value, list))
        )
        if is_bulk:
            if isinstance(value, (list, dict)):
                dropped[key] = len(value)
            elif value is not None:
                dropped[key] = 1
            continue
        kept[key] = strip_bulk(value, extra_keys, _depth + 1)

    if dropped:
        kept["_omitted"] = dropped
    return kept


def paginate(
    items: Sequence[Any],
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    """Slice a list into the standard {items, total, offset, has_more} envelope."""
    size = clamp_limit(limit)
    start = max(offset, 0)
    window = list(items[start : start + size])
    return {
        "items": window,
        "total": len(items),
        "offset": start,
        "limit": size,
        "has_more": start + len(window) < len(items),
    }


def envelope(items: Sequence[Any], total: int | None = None, **extra: Any) -> dict[str, Any]:
    """Standard list envelope for results already paginated by the backend."""
    payload: dict[str, Any] = {
        "items": list(items),
        "count": len(items),
    }
    if total is not None:
        payload["total"] = total
    payload.update(extra)
    return payload

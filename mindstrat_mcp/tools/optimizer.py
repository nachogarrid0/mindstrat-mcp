"""Optimizer tools: configure, launch, monitor and control optimization runs.

Backend surface: /optimizer (no auth) plus /strategies and /manager for seeding
and reading results.

The backend persists cycles and robustness itself (a DBWriter process), but only
when the start request carries a ``strategy_id`` — that is what makes it create
the optimization row. ``start_optimization`` therefore always sends it.

Progress is read by polling the manager's metadata endpoint, the same data the
Strategy Manager screen shows.

Runs start in the backend, from the configuration ``configure_optimization``
saves — the Optimizer screen does not have to be open for any of this. It shows
that configuration when it is open, and a run it started itself, but it is a
view rather than a precondition.

Only one optimization runs at a time; starting while the previous one is tearing
down returns 409 optimizer.busy_finishing.

See OPTIMIZATION.md for what the search methods and robustness tests actually
measure and how to configure them. The catalogues below are mirrored from the
app and pinned by tests/mcp/test_optimizer_reference.py.
"""

from __future__ import annotations

import ast
import asyncio
import time
import uuid
from typing import Any

from .. import config
from ..client import BackendClient
from ..appdata import describe, monte_carlo_mode_names, search_method_names
from ..errors import McpToolError
from ..shaping import round_numbers, strip_bulk

# Remembers the run this session started, so control/status calls do not have to
# carry the ticket around. Nothing is derived from it — it is just the last
# {opt_id, ticket} the backend handed back.
_last_run: dict[str, Any] = {}

# What each name means. The names themselves are read from the app (see
# appdata), so this is documentation, not a second source of truth.
_SEARCH_METHOD_NOTES = {
    "Random": "Uniform sampling. The safe default for unmapped terrain.",
    "Brute Force": "Every combination. Only when total_combinations is small.",
    "Random Improvements": "Random, building on what improves. Refines a known region.",
    "Sequential Improvement": "One parameter at a time, by priority.",
    "Sequential MC": "Sequential, repeated over several loops.",
    "Sequential Jump": "Sequential with jumps out of local optima.",
    "Annealing Thermal": "Simulated annealing: wide early, narrow later.",
}

# All modes perturb the sequence of trade P&Ls, not the market data.
_MONTE_CARLO_NOTES = {
    "shuffle": {
        "perturbation": "Reorders the trades.",
        "answers": "Was the drawdown an accident of ordering? Cannot test the "
                   "edge: reordering does not change the total.",
        "params": {},
    },
    "bootstrap": {
        "perturbation": "Resamples the trades in blocks.",
        "answers": "Does the edge hold on resampled histories?",
        "params": {"block_size": 10},
    },
    "drop_pct": {
        "perturbation": "Removes a random share of trades.",
        "answers": "Does it survive missing trades?",
        "params": {"pct_min": 0.10, "pct_max": 0.30},
    },
    "drop_best_trades": {
        "perturbation": "Removes the best trades.",
        "answers": "Does the edge depend on a handful of winners? The harshest "
                   "and most informative mode.",
        "params": {"pct": 0.10, "jitter": 0.03},
    },
    "drop_cluster": {
        "perturbation": "Removes a contiguous run of trades.",
        "answers": "Does it survive a bad streak or an outage?",
        "params": {"cluster_pct_min": 0.05, "cluster_pct_max": 0.15},
    },
    "noise_injection": {
        "perturbation": "Perturbs each trade's P&L.",
        "answers": "How sensitive is it to fill quality?",
        "params": {"noise_pct": 0.05},
    },
    "cost_degradation": {
        "perturbation": "Raises commissions and slippage.",
        "answers": "Does it survive worse execution costs?",
        "params": {"max_cost_pct": 0.03},
    },
    "time_slice": {
        "perturbation": "Uses only a window of the history.",
        "answers": "Is the result an artefact of one regime?",
        "params": {"window_pct": 0.40},
    },
}

TRIGGER_MODES = {
    "cycles": "Every N cycles (set `trigger`). The app defaults to 500 for "
              "walk-forward and 50 for Monte Carlo. Cheapest, but only a "
              "handful of candidates end up with any evidence.",
    "new_best": "Whenever a new best candidate appears. Validates every "
                "finalist, but the validated set is exactly the in-sample "
                "winners — a biased sample of the run.",
    "every_pass": "Every single cycle, so every candidate is comparable to "
                  "every other. The only mode that lets you rank the whole run "
                  "by robustness. It costs time, not memory: it multiplies the "
                  "work per cycle, and you pay for it with fewer cycles or "
                  "fewer curves.",
    "_cost_model": "Robustness costs wall-clock, not RAM. Results stream to a "
                   "separate DBWriter process and Monte Carlo's curves are "
                   "summarised and dropped inside the worker, so memory is flat "
                   "across a run. Hold-out roughly doubles a cycle's backtest; "
                   "Monte Carlo scales with modes x curves; intrabar is the "
                   "expensive one because it re-runs bars at a finer timeframe.",
}


async def get_optimizer_capacity(client: BackendClient) -> dict[str, Any]:
    """RAM headroom and the user's own runtime settings, for sizing a run.

    Memory pressure comes from workers x dataset size, not from the robustness
    configuration (that costs wall-clock), so this is what `workers` and
    `max_ram_pct` should be decided against.
    """
    system = await client.get("/optimizer/system-info")
    preset = await _user_preset(client)
    user_config = preset.get("config") or {}
    return round_numbers(
        {
            "system_ram": system,
            "configured": {
                "workers": user_config.get("workers"),
                "max_ram_pct": user_config.get("maxRamPct"),
                "note": "What the user set on the Optimizer screen; null means "
                        "the screen has never saved a preset on this machine.",
            },
            "limits": {"workers": "1-64", "max_ram_pct": "10-99"},
            "sizing_note": (
                "The machine's limits belong to whoever owns the machine: "
                "respect the configured workers unless there is a stated "
                "reason to override, and always send max_ram_pct (the app "
                "uses 80) as the backstop. Robustness tests cost time, not "
                "memory — never cut them to protect RAM."
            ),
        }
    )


async def prepare_optimization(
    client: BackendClient, strategy_id: int, dataset_id: str | None = None
) -> dict[str, Any]:
    """Read a saved strategy's optimizer configuration.

    Returns what the app has stored for it — base parameters, capital config,
    robustness config, auxiliary datasets — plus the catalogue of methods and
    tests. Ranges come back only if the strategy has them saved; choosing them
    is an analysis decision, not something to fill in with a default.
    """
    sync = await client.get(f"/strategies/saved/{strategy_id}/optimizer-sync")
    if not isinstance(sync, dict):
        raise McpToolError(f"Unexpected optimizer-sync response for strategy {strategy_id}")

    # What the code requires, next to what the strategy has saved for it. A slot
    # left unfilled fails every cycle, so it belongs in the preparation rather
    # than in the error that would follow it.
    try:
        code = await client.get(f"/manager/strategies/{strategy_id}/code")
    except Exception:  # noqa: BLE001 — preparation should still return
        code = ""
    declared = _declared_aux_slots(code if isinstance(code, str) else "")
    saved_aux = _panel_auxiliary(sync.get("auxiliary_snapshot_ids"))

    ranges = sync.get("param_ranges") or {}
    preview: dict[str, Any] = {}
    if ranges:
        # The preview endpoint mirrors the UI form: every range field is text.
        def as_text(value: Any) -> str:
            if value is None:
                return ""
            if isinstance(value, bool):
                return "true" if value else "false"
            return str(value)

        rows = [
            {
                "name": name,
                "active": bool(spec.get("active", True)),
                "from": as_text(spec.get("from", spec.get("min"))),
                "to": as_text(spec.get("to", spec.get("max"))),
                "step": as_text(spec.get("step")),
                "default": as_text((sync.get("base_params") or {}).get(name)),
                "priority": float(spec.get("priority", 1) or 1),
            }
            for name, spec in ranges.items()
            if isinstance(spec, dict)
        ]
        if rows:
            preview = await client.post("/optimizer/parameters/preview", json={"rows": rows}) or {}

    return round_numbers(
        {
            "strategy_id": strategy_id,
            "strategy_name": sync.get("strategy_name"),
            "descriptor": sync.get("descriptor"),
            "dataset_id": dataset_id or sync.get("dataset_id"),
            "base_parameters": sync.get("base_params"),
            "parameter_ranges": ranges,
            "parameter_ranges_note": (
                "Saved with the strategy."
                if ranges
                else "This strategy has no saved ranges. Decide them yourself: "
                     "pick a span and a step per parameter from what the "
                     "indicator means and what the data supports, then pass "
                     "them to start_optimization. The Optimizer screen fills "
                     "its form with +/-20% around each value, but that is a "
                     "placeholder to edit, not a recommendation."
            ),
            "capital_cfg": sync.get("capital_cfg"),
            "robust_methods": sync.get("robust_methods"),
            "robust_cfg": sync.get("robust_cfg"),
            "auxiliary_snapshot_ids": sync.get("auxiliary_snapshot_ids"),
            "auxiliary_slots": (
                {
                    slot: {
                        "declares": note,
                        "dataset_id": (saved_aux.get(slot) or {}).get("snapshotId"),
                        "status": (
                            "saved with the strategy" if slot in saved_aux
                            else "MUST be passed to configure_optimization"
                        ),
                    }
                    for slot, note in declared.items()
                }
                if declared
                else "This strategy declares no auxiliary datasets."
            ),
            "search_space": {
                "total_combinations": preview.get("total_combinations"),
                "sequential_cycles": preview.get("sequential_cycles"),
            },
            "range_warnings": _range_warnings(ranges),
            "options": {
                "search_methods": describe(search_method_names(), _SEARCH_METHOD_NOTES),
                "robustness": {
                    "walk_forward": {
                        "holdout": "One split (split_pct: 70 trains on the first "
                                   "70%, validates on the last 30%). Cheap, and "
                                   "the validation window is the recent period.",
                        "rolling": "N moving train/validation folds. Slower, but "
                                   "shows whether the edge is stable across eras.",
                        "reads": "Results come back as is_* and val_* fields.",
                    },
                    "monte_carlo": describe(monte_carlo_mode_names(), _MONTE_CARLO_NOTES),
                    "intrabar": "Replays TP/SL bars at a finer timeframe to "
                                "resolve which level was touched first. Required "
                                "for any strategy whose exits are TP/SL — without "
                                "it those results are optimistic by an unknown "
                                "margin. Options: GET "
                                "/strategies/intrabar-timeframes/{timeframe}.",
                    "matrices": "Declared in the request model but consumed by "
                                "nothing. Ignore it.",
                },
                "trigger_modes": TRIGGER_MODES,
                "recommended": {
                    "mapping_unknown_terrain": "Random, no robustness or "
                                               "holdout on 'cycles'. The goal is "
                                               "coverage: find which region of "
                                               "the space is worth measuring.",
                    "selecting_a_winner": "holdout + the predictive Monte Carlo "
                                          "modes (bootstrap, drop_cluster, "
                                          "drop_pct, time_slice) on "
                                          "'every_pass', with the cycle budget "
                                          "cut to whatever that affords. A "
                                          "partially-validated run cannot be "
                                          "ranked by robustness: 'new_best' "
                                          "measures only in-sample winners.",
                    "validating_finalists": "rolling folds, plus "
                                            "drop_best_trades + cost_degradation "
                                            "+ time_slice, plus intrabar. Run "
                                            "these on the saved strategy, not "
                                            "across the whole search.",
                    "always": "Send max_ram_pct (the app uses 80) as a backstop "
                              "for the worker pool. It is not protection "
                              "against the robustness configuration: that costs "
                              "time, not memory.",
                },
                "selecting_a_winner": "Do not rank by in-sample profit. Look for "
                                      "a parameter plateau among the top cycles, "
                                      "drop parameters that do not cluster, "
                                      "compare val_* against is_*, and check "
                                      "drop_best_trades before believing any of "
                                      "it. See OPTIMIZATION.md.",
            },
            "next_step": "Pass these values to start_optimization (adjust ranges first if needed).",
        }
    )


def _range_warnings(ranges: dict[str, Any]) -> list[str]:
    """Flag ranges that will not search what the caller probably intends.

    The engine walks a range in floats and casts each value back to the type of
    the range's ``default`` (``type(default_val)(cur)``), so an integer default
    with a fractional step truncates every step onto whole numbers — and for a
    percentage that can include 0, which for a stop loss means no stop at all.
    """
    warnings: list[str] = []
    for name, spec in (ranges or {}).items():
        if not isinstance(spec, dict):
            continue
        default = spec.get("default")
        step = spec.get("step")
        if isinstance(default, bool) or default is None:
            continue
        fractional_step = isinstance(step, float) and step != int(step)
        if isinstance(default, int) and fractional_step:
            # Not float(default): the Optimizer screen parses every cell with
            # JavaScript's Number(), which has one numeric type, so a whole
            # number written as 1.0 arrives back as the integer 1. Only a value
            # with a real fractional part survives the trip.
            low = spec.get("from")
            suggestion = (
                low + step if isinstance(low, (int, float)) else float(default) + step
            )
            warnings.append(
                f"{name}: default is the integer {default} but step is {step}, "
                f"so every value truncates onto whole numbers. Pass a default "
                f"with a fractional part that lands on the grid ({suggestion}). "
                "A float whose value is whole (1.0) does NOT work: it reaches "
                "the engine as an int."
            )
        low = spec.get("from")
        if isinstance(low, (int, float)) and low == 0 and "stop" in name.lower():
            warnings.append(
                f"{name}: the range starts at 0, which means running with no "
                "stop loss. Raise `from` unless that is intended."
            )
    return warnings


def _validate_window(
    dataset_id: str, header: dict[str, Any], start_time: Any, end_time: Any
) -> None:
    """Refuse a window the dataset holds no bars for.

    Nothing downstream catches this. The Optimizer screen filters its bars by
    the window, finds none, and falls back to the dataset's full span — so the
    run covers a period nobody asked for, and the only symptom is a result that
    looks fine. It also sets the run's memory footprint, because the intrabar
    data is loaded for whatever span the history ends up covering.

    A window that merely overhangs the dataset is left alone: asking to start
    earlier than the data exists is a normal way to say "from the beginning".
    """
    if start_time is not None and end_time is not None and start_time >= end_time:
        raise McpToolError(
            f"start_time ({start_time}) must be before end_time ({end_time})."
        )

    full_start = header.get("start_date")
    full_end = header.get("end_date")
    if full_start is None or full_end is None:
        return

    def milliseconds_hint(value: Any) -> str:
        # Seconds-vs-milliseconds is the usual way to land outside a dataset,
        # and the corrected value is more use than the diagnosis.
        if isinstance(value, (int, float)) and value > 100_000_000_000:
            return (
                f" It looks like milliseconds — these are epoch SECONDS, so "
                f"that would be {int(value) // 1000}."
            )
        return ""

    if start_time is not None and start_time > full_end:
        raise McpToolError(
            f"start_time ({start_time}) is after the end of dataset {dataset_id}, "
            f"which covers {full_start} to {full_end}, so the window holds no "
            f"bars.{milliseconds_hint(start_time)}"
        )
    if end_time is not None and end_time < full_start:
        raise McpToolError(
            f"end_time ({end_time}) is before the start of dataset {dataset_id}, "
            f"which covers {full_start} to {full_end}, so the window holds no "
            f"bars.{milliseconds_hint(end_time)}"
        )


def _with_defaults(
    ranges: dict[str, Any], base_parameters: dict[str, Any]
) -> dict[str, Any]:
    """Fill each range's ``default`` from the strategy's base parameters.

    The optimizer decides how to expand a range from the *type* of its
    ``default`` (bool, number or string). Without one it produces null
    parameters and every cycle fails, so refuse rather than start a run that
    can only generate garbage. This mirrors the UI form, whose default column
    is populated from the strategy's parameters.
    """
    resolved: dict[str, Any] = {}
    missing: list[str] = []
    for name, spec in ranges.items():
        if not isinstance(spec, dict):
            missing.append(name)
            continue
        if spec.get("default") is None:
            if name not in base_parameters or base_parameters[name] is None:
                missing.append(name)
                continue
            spec = {**spec, "default": base_parameters[name]}
        resolved[name] = spec

    if missing:
        raise McpToolError(
            "These parameters have no default value, which the optimizer needs "
            f"to know how to expand their range: {', '.join(sorted(missing))}. "
            "Add 'default' to each range, or pass base_parameters."
        )
    return resolved


# The Optimizer screen stores its whole form as one preset and hydrates from it,
# so writing a run into that preset is what makes the panel show what is actually
# running. These map the API shape back to the form's field names; the forward
# direction lives in buildMonteCarloPayload / buildWalkForwardPayload in
# frontend/src/features/optimizer/OptimizerConfig.tsx.
_MC_MODE_FIELDS = {
    "shuffle": "shuffle",
    "bootstrap": "bootstrap",
    "drop_pct": "dropPctMode",
    "drop_best_trades": "dropBestTrades",
    "drop_cluster": "dropCluster",
    "noise_injection": "noiseInjection",
    "cost_degradation": "costDegradation",
    "time_slice": "timeSlice",
}

# Per-mode parameters, mapped to the form's field names *and* to its units. The
# screen holds every percentage on a 0-100 scale and divides by 100 when it
# builds the engine's payload, so a fraction written straight into the form
# would run at a hundredth of what was asked. block_size is a trade count.
_MC_MODE_PARAM_FIELDS = {
    ("bootstrap", "block_size"): ("blockSize", 1),
    ("drop_pct", "pct_min"): ("dropPctMin", 100),
    ("drop_pct", "pct_max"): ("dropPctMax", 100),
    ("drop_best_trades", "pct"): ("dropBestPct", 100),
    ("drop_best_trades", "jitter"): ("dropBestJitter", 100),
    ("drop_cluster", "cluster_pct_min"): ("clusterPctMin", 100),
    ("drop_cluster", "cluster_pct_max"): ("clusterPctMax", 100),
    ("noise_injection", "noise_pct"): ("noisePct", 100),
    ("cost_degradation", "max_cost_pct"): ("maxCostPct", 100),
    ("time_slice", "window_pct"): ("windowPct", 100),
}

_WALK_FORWARD_FIELDS = (
    ("mode", "mode"),
    ("train_pct", "trainPct"),
    ("val_pct", "valPct"),
    ("trigger_mode", "triggerMode"),
    ("trigger", "triggerEvery"),
    ("folds", "folds"),
    ("metric", "metric"),
)


async def _user_preset(client: BackendClient) -> dict[str, Any]:
    """The preset the Optimizer screen last saved: the user's own settings.

    Never fatal — a machine that has never opened the screen has no preset, and
    a run should still start.
    """
    try:
        payload = await client.get("/optimizer/settings")
    except Exception:  # noqa: BLE001 — settings are a convenience, not a gate
        return {}
    settings = (payload or {}).get("settings")
    return settings if isinstance(settings, dict) else {}


def _clamp(value: Any, low: int, high: int, fallback: int) -> int:
    try:
        return max(low, min(int(value), high))
    except (TypeError, ValueError):
        return fallback


def _panel_walk_forward(current: Any, cfg: Any) -> dict[str, Any]:
    state = dict(current) if isinstance(current, dict) else {}
    if not isinstance(cfg, dict) or not cfg:
        state["enabled"] = False
        return state
    state["enabled"] = True
    for api_key, panel_key in _WALK_FORWARD_FIELDS:
        if cfg.get(api_key) is not None:
            state[panel_key] = cfg[api_key]
    # The screen splits the run as two percentages; the API takes one.
    split = cfg.get("split_pct")
    if split is not None:
        state["trainPct"] = _clamp(split, 1, 99, 70)
        state["valPct"] = 100 - state["trainPct"]
    return state


def _panel_monte_carlo(current: Any, cfg: Any) -> dict[str, Any]:
    state = dict(current) if isinstance(current, dict) else {}
    if not isinstance(cfg, dict) or not cfg:
        state["enabled"] = False
        return state
    state["enabled"] = True
    curves = cfg.get("curves", cfg.get("n"))
    if curves is not None:
        state["curves"] = curves
    active = set(cfg.get("modes") or ())
    unknown = active - set(_MC_MODE_FIELDS)
    if unknown:
        raise McpToolError(
            f"Unknown Monte Carlo mode(s): {', '.join(sorted(unknown))}. "
            f"Valid modes are: {', '.join(sorted(_MC_MODE_FIELDS))}."
        )
    for api_name, panel_key in _MC_MODE_FIELDS.items():
        state[panel_key] = api_name in active

    # Per-mode parameters. Left alone, each mode runs with whatever the user
    # has on the screen; naming one overrides it. A typo would otherwise be
    # silent — the mode would run at its old setting and say nothing.
    mode_params = cfg.get("mode_params") or {}
    if not isinstance(mode_params, dict):
        raise McpToolError("mode_params must be {mode: {parameter: value}}")
    for mode, params in mode_params.items():
        if mode not in _MC_MODE_FIELDS:
            raise McpToolError(
                f"mode_params names '{mode}', which is not a Monte Carlo mode. "
                f"Valid modes are: {', '.join(sorted(_MC_MODE_FIELDS))}."
            )
        if mode not in active:
            raise McpToolError(
                f"mode_params configures '{mode}' but it is not in modes, so it "
                "would not run. Add it to modes or drop its parameters."
            )
        for param, value in (params or {}).items():
            field = _MC_MODE_PARAM_FIELDS.get((mode, param))
            if field is None:
                accepted = sorted(p for m, p in _MC_MODE_PARAM_FIELDS if m == mode)
                raise McpToolError(
                    f"'{param}' is not a parameter of the {mode} mode. "
                    + (f"It accepts: {', '.join(accepted)}." if accepted
                       else f"{mode} takes no parameters.")
                )
            panel_key, scale = field
            state[panel_key] = value * scale

    if cfg.get("trigger_mode") is not None:
        state["triggerMode"] = cfg["trigger_mode"]
    if cfg.get("trigger") is not None:
        state["triggerEvery"] = cfg["trigger"]
    return state


def _cell(value: Any) -> str:
    """The screen holds every cell as text, booleans included ("True"/"False")."""
    return "" if value is None else str(value)


def _value_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    return "number" if isinstance(value, (int, float)) else "string"


def _panel_parameter_rows(
    current: Any, ranges: dict[str, Any], base: dict[str, Any]
) -> list[dict[str, Any]]:
    """The search space as the screen's parameter table holds it.

    One row per parameter: the ones this run searches carry their from/to/step,
    and the ones it holds fixed collapse to their value. Row ids are kept when
    the name is already on the table, so the user's rows are updated rather
    than replaced.
    """
    known_ids = {
        row.get("name"): row.get("id")
        for row in (current if isinstance(current, list) else [])
        if isinstance(row, dict) and row.get("name")
    }

    def row_for(name: str, spec: Any, active: bool) -> dict[str, Any]:
        spec = spec if isinstance(spec, dict) else {}
        default = spec.get("default", base.get(name))
        return {
            "id": known_ids.get(name) or str(uuid.uuid4()),
            "name": name,
            "active": active,
            "valueType": _value_type(default),
            "from": _cell(spec.get("from", default)),
            "to": _cell(spec.get("to", default)),
            "step": _cell(spec.get("step", 1)),
            "defaultValue": _cell(default),
            "priority": spec.get("priority", 1) or 1,
        }

    rows = [row_for(name, spec, True) for name, spec in ranges.items()]
    rows.extend(
        row_for(name, None, False) for name in base if name not in ranges
    )
    return rows


async def configure_optimization(
    client: BackendClient,
    strategy_id: int,
    dataset_id: str,
    method: str = "Random",
    cycles: int | None = None,
    workers: int | None = None,
    metric: str = "profit",
    parameter_ranges: dict[str, Any] | None = None,
    base_parameters: dict[str, Any] | None = None,
    capital_cfg: dict[str, Any] | None = None,
    robustness: dict[str, Any] | None = None,
    start_time: int | None = None,
    end_time: int | None = None,
    max_ram_pct: int | None = None,
    sequential: dict[str, Any] | None = None,
    auxiliary_snapshot_ids: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fill in the Optimizer screen's form, without starting anything.

    Writes the whole configuration where that screen keeps it, so the user can
    review it before launching and so the run, when it launches, is the one on
    display. Works with the screen closed: the configuration waits on disk and
    is adopted when it opens.
    """
    method = _validate_method(method)
    preset = await _user_preset(client)
    user_config = preset.get("config") or {}
    # The machine's own limits belong to whoever owns the machine: reuse what
    # the screen has configured unless this call overrides it on purpose.
    resolved_workers = (
        _clamp(workers, 1, 64, 4) if workers is not None
        else _clamp(user_config.get("workers"), 1, 64, 4)
    )
    resolved_ram = (
        _clamp(max_ram_pct, 10, 99, 80) if max_ram_pct is not None
        else _clamp(user_config.get("maxRamPct"), 10, 99, 80)
    )

    sync = await client.get(f"/strategies/saved/{strategy_id}/optimizer-sync")
    if not isinstance(sync, dict):
        raise McpToolError(f"Strategy {strategy_id} cannot seed an optimization")

    code = await client.get(f"/manager/strategies/{strategy_id}/code")
    if not isinstance(code, str) or not code.strip():
        raise McpToolError(f"Strategy {strategy_id} has no source code to optimize")

    ranges = parameter_ranges or sync.get("param_ranges") or {}
    if not ranges:
        raise McpToolError(
            "No parameter ranges to search. Call prepare_optimization and pass "
            "parameter_ranges explicitly."
        )
    base = base_parameters or sync.get("base_params") or {}
    ranges = _with_defaults(ranges, base)

    header = await client.get(f"/strategies/datasets/{dataset_id}")
    if not isinstance(header, dict):
        raise McpToolError(f"Dataset {dataset_id} not found")
    _validate_window(dataset_id, header, start_time, end_time)
    span_start = start_time or header.get("start_date")
    span_end = end_time or header.get("end_date")
    if span_start is None or span_end is None:
        raise McpToolError(f"Dataset {dataset_id} has no usable date range")

    merged = dict(preset)
    config_block = dict(merged.get("config") or {})
    config_block.update({
        "method": method,
        "metric": metric,
        "workers": resolved_workers,
        "maxRamPct": resolved_ram,
        "strategyId": str(strategy_id),
        "strategySource": "saved",
        "datasetId": dataset_id,
    })
    if cycles is not None:
        config_block["cycles"] = int(cycles)
    if capital_cfg or sync.get("capital_cfg"):
        config_block.update(_panel_capital(capital_cfg or sync.get("capital_cfg")))
    config_block.update(_panel_sequential(method, sequential))
    merged["config"] = config_block

    merged["walkForward"] = _panel_walk_forward(
        merged.get("walkForward"), (robustness or {}).get("walk_forward")
    )
    merged["monteCarlo"] = _panel_monte_carlo(
        merged.get("monteCarlo"), (robustness or {}).get("monte_carlo")
    )
    merged["intrabar"] = _panel_intrabar(
        merged.get("intrabar"), (robustness or {}).get("intrabar")
    )
    aux = _panel_auxiliary(
        auxiliary_snapshot_ids
        if auxiliary_snapshot_ids is not None
        else sync.get("auxiliary_snapshot_ids")
    )
    # A strategy that declares a slot raises on its first bar without it, so an
    # unfilled slot does not fail the run — it fails every cycle of it, and the
    # only symptom is the same error repeated a thousand times. Nothing
    # downstream catches this: the backend validates the keys that were sent
    # against the declarations, never the other way round.
    declared = _declared_aux_slots(code)
    # A wrong slot name is checked first: it also leaves the real slot unfilled,
    # and "this name does not exist, here are the ones that do" is the diagnosis
    # that fixes it. Reversed, the caller is told to fill a slot they thought
    # they had filled.
    undeclared = [slot for slot in aux if declared and slot not in declared]
    if undeclared:
        raise McpToolError(
            f"auxiliary_snapshot_ids names slot(s) strategy {strategy_id} does not "
            f"declare: {', '.join(sorted(undeclared))}. It declares: "
            f"{', '.join(sorted(declared)) or 'none'}. Slot names come from the "
            "strategy's own code and are not interchangeable; the backend "
            "rejects undeclared keys."
        )
    unfilled = [slot for slot in declared if slot not in aux]
    if unfilled:
        described = "; ".join(f"'{slot}' ({declared[slot]})" for slot in unfilled)
        raise McpToolError(
            f"Strategy {strategy_id} declares auxiliary dataset slot(s) with no "
            f"dataset for them: {described}. Every cycle would fail on the first "
            "bar. Pass auxiliary_snapshot_ids={"
            + ", ".join(f"'{slot}': '<dataset_id>'" for slot in unfilled)
            + "}."
        )
    if aux:
        merged["auxiliaryDatasets"] = await _label_aux(client, aux)
    merged["parameterRows"] = _panel_parameter_rows(
        merged.get("parameterRows"), ranges, base
    )
    # The screen drops a strategy whose code it cannot resolve, so it travels
    # with the preset rather than being fetched again by id.
    merged["strategy"] = {
        "id": str(strategy_id),
        "name": sync.get("strategy_name") or f"Strategy {strategy_id}",
        "origin": "library",
        "code": code,
        "parameterRanges": ranges,
        "baseParameters": base,
    }
    # The screen resolves a dataset's files from its snapshot id and remembers
    # where it put them, but those are per-session temp slices under cache/.
    # Carrying the previous configuration's over hands this run either a slice
    # that no longer exists — the engine refuses with "Dataset path not found" —
    # or, when the dataset changed, another dataset's CSV. Dropped, so the
    # screen re-resolves them from the snapshot id it is given here.
    previous_history = {
        key: value
        for key, value in (merged.get("history") or {}).items()
        if key not in ("cachedPath", "slicePath", "datasetPath", "rows")
    }
    merged["history"] = {
        **previous_history,
        "snapshotId": dataset_id,
        "datasetId": dataset_id,
        "symbol": header.get("symbol"),
        "timeframe": header.get("timeframe"),
        "fullStart": int(header.get("start_date")) if header.get("start_date") else None,
        "fullEnd": int(header.get("end_date")) if header.get("end_date") else None,
        "subsetStart": int(span_start),
        "subsetEnd": int(span_end),
        "strategyId": str(strategy_id),
        "strategySource": "saved",
    }

    await client.post("/optimizer/settings", json={"settings": merged})
    # The screen hydrates its form from this preset when it mounts, and only
    # then. Without this an already-open screen would keep showing the previous
    # configuration and start would run that instead.
    reload = await _send_panel_command(client, "reload_config", wait=5.0)

    return round_numbers({
        "configured": True,
        "strategy_id": strategy_id,
        "dataset_id": dataset_id,
        "method": method,
        "metric": metric,
        "cycles": config_block.get("cycles"),
        "runtime": {
            "workers": resolved_workers,
            "max_ram_pct": resolved_ram,
            "source": "this call" if workers is not None else "the user's Optimizer settings",
        },
        "searching": {
            name: {k: spec.get(k) for k in ("from", "to", "step")}
            for name, spec in ranges.items()
            if isinstance(spec, dict)
        },
        "range": {"start": int(span_start), "end": int(span_end)},
        # The run is configured here, so this is the last point at which a
        # range that cannot search what was intended can still be fixed.
        # prepare_optimization also reports these, but nothing forces a caller
        # through it.
        "range_warnings": _range_warnings(ranges) or None,
        "auxiliary_datasets": aux or None,
        "robustness": _robustness_echo(merged),
        "screen_updated": bool(reload.get("applied")),
        "next_step": (
            "The Optimizer screen now shows this configuration; review it there "
            "and call start_optimization when it is what you want."
            if reload.get("applied")
            else "Saved. The Optimizer screen is closed, so nothing is on "
                 "display — which does not hold anything up: start_optimization "
                 "runs this configuration from the backend either way, and the "
                 "screen adopts it when it opens."
        ),
    })


def _validate_method(method: str) -> str:
    """Refuse a method the engine does not know.

    ``METHODS.get(method, METHODS.get("Random"))`` means an unrecognised name
    costs a whole run and says nothing while it does it. The screen normalises
    what it can, but a name it cannot map falls through to the same silent
    default, so this rejects it here where the caller can still fix it.
    """
    known = search_method_names()
    if not known or method in known:  # source unreadable — do not block the run
        return method
    raise McpToolError(
        f"'{method}' is not a search method this app knows, and the engine "
        f"would silently fall back to Random. Choose one of: "
        f"{', '.join(sorted(known))}."
    )


# The screen keeps the sequential budgets outside `cycles`: Sequential MC runs
# `cycles` as a (mode, loops) pair, and Sequential Jump replaces it with a jump
# config. Leaving these out means the run's budget is whatever the user last
# set, which is not what was asked for.
_SEQ_MODES = ("1 vuelta", "N vueltas", "Hasta sin mejora")
_JUMP_TERMINATIONS = ("never", "cycles", "minutes")


def _panel_sequential(method: str, sequential: Any) -> dict[str, Any]:
    """The sequential-method fields under the names the screen's form uses."""
    sequential = sequential if isinstance(sequential, dict) else {}
    fields: dict[str, Any] = {}

    if method == "Sequential MC":
        mode = sequential.get("seq_mode", "1 vuelta")
        if mode not in _SEQ_MODES:
            raise McpToolError(
                f"seq_mode must be one of {', '.join(_SEQ_MODES)} (got '{mode}')."
            )
        fields["seqMode"] = mode
        if mode == "N vueltas":
            loops = sequential.get("seq_loops")
            if loops is None:
                raise McpToolError(
                    "Sequential MC with seq_mode 'N vueltas' needs seq_loops: it "
                    "is the number of passes, and it is the run's real budget."
                )
            fields["seqLoops"] = _clamp(loops, 1, 10_000, 2)

    elif method == "Sequential Jump":
        fields["jumpSize"] = _clamp(sequential.get("jump_size", 1), 1, 1_000_000, 1)
        termination = sequential.get("jump_termination", "never")
        if termination not in _JUMP_TERMINATIONS:
            raise McpToolError(
                f"jump_termination must be one of {', '.join(_JUMP_TERMINATIONS)} "
                f"(got '{termination}')."
            )
        fields["jumpTermination"] = termination
        if termination == "cycles":
            fields["jumpCycles"] = _clamp(sequential.get("jump_cycles", 10), 1, 1_000_000, 10)
        elif termination == "minutes":
            try:
                fields["jumpMinutes"] = max(0.1, float(sequential.get("jump_minutes", 5)))
            except (TypeError, ValueError):
                fields["jumpMinutes"] = 5.0

    return fields


def _panel_intrabar(current: Any, intrabar: Any) -> dict[str, Any]:
    """Intrabar simulation as the screen's form holds it.

    The screen keeps only whether it is on and an optional timeframe override;
    the symbol, the base timeframe and the exchange it derives from the loaded
    history at start time.
    """
    if not isinstance(intrabar, dict) or not intrabar:
        return {"enabled": False, "timeframe": ""}
    return {
        "enabled": bool(intrabar.get("enabled", True)),
        # "" means let the app pick the recommended finer timeframe.
        "timeframe": str(intrabar.get("intrabar_timeframe") or intrabar.get("timeframe") or ""),
    }


async def _label_aux(client: BackendClient, aux: dict[str, Any]) -> dict[str, Any]:
    """Fill each auxiliary selection's symbol and timeframe from its dataset.

    The screen's own picker stores those alongside the id, and its bubble builds
    its label from them — a selection carrying only a snapshot id renders as
    "Seleccionar...", so the user is told nothing is selected while the run uses
    it. Writing what the picker writes keeps the display honest.
    """
    for selection in aux.values():
        if selection.get("symbol") and selection.get("timeframe"):
            continue
        try:
            header = await client.get(f"/strategies/datasets/{selection['snapshotId']}")
        except Exception:  # noqa: BLE001 — a label is not worth failing the run
            continue
        if isinstance(header, dict):
            selection["symbol"] = selection.get("symbol") or header.get("symbol")
            selection["timeframe"] = selection.get("timeframe") or header.get("timeframe")
    return aux


def _declared_aux_slots(code: str) -> dict[str, str]:
    """The auxiliary slots the strategy's own source declares, with their notes.

    Read from the module-level ``auxiliary_datasets`` dict rather than asked of
    the backend: its only route for this (POST /strategies/parameters) would
    replace whatever the user has open in the Code Creator.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {}

    for node in tree.body:
        targets = (
            node.targets if isinstance(node, ast.Assign)
            else [node.target] if isinstance(node, ast.AnnAssign)
            else []
        )
        if not any(isinstance(t, ast.Name) and t.id == "auxiliary_datasets" for t in targets):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, SyntaxError):
            return {}
        if isinstance(value, dict):
            return {str(k): str(v) for k, v in value.items()}
    return {}


def _panel_auxiliary(auxiliary: Any) -> dict[str, Any]:
    """Auxiliary dataset slots, keyed the way the dataset store keys them."""
    if not isinstance(auxiliary, dict):
        return {}
    slots: dict[str, Any] = {}
    for slot, value in auxiliary.items():
        if isinstance(value, str) and value:
            slots[slot] = {"snapshotId": value}
        elif isinstance(value, dict):
            snapshot_id = value.get("snapshot_id") or value.get("snapshotId")
            if snapshot_id:
                slots[slot] = {
                    "snapshotId": snapshot_id,
                    "symbol": value.get("symbol"),
                    "timeframe": value.get("timeframe"),
                }
    return slots


# The values the form holds for each of its dropdowns. A value outside these
# is not a smaller mistake than a wrong number: the screen renders an unknown
# one as the first option, and the engine reads it as no setting at all — a
# slippage_mode it does not recognise applies no slippage and says nothing, so
# the run silently costs less than it was configured to.
_CAPITAL_OPTIONS = {
    "order_size_mode": ("fixed_value", "fixed_qty", "percent_of_equity"),
    "commission_type": ("percent", "fixed"),
    "slippage_mode": ("none", "fixed", "volume"),
}


def _panel_capital(capital: Any) -> dict[str, Any]:
    """Capital settings under the names the screen's form uses."""
    capital = capital if isinstance(capital, dict) else {}
    for field, allowed in _CAPITAL_OPTIONS.items():
        value = capital.get(field)
        if value is not None and value not in allowed:
            raise McpToolError(
                f"capital_cfg {field}={value!r} is not one the app has. Valid "
                f"values: {', '.join(allowed)}."
            )
    mapping = {
        "initial_capital": "initialCapital",
        "order_size_mode": "orderSizeMode",
        "order_size": "orderSize",
        "commission": "commission",
        "commission_type": "commissionType",
        "slippage_mode": "slippageMode",
        "slippage_bps": "slippageBps",
        "slippage_k": "slippageK",
    }
    return {
        panel_key: capital[api_key]
        for api_key, panel_key in mapping.items()
        if capital.get(api_key) is not None
    }


def _robustness_echo(preset: dict[str, Any]) -> dict[str, Any]:
    """What the configuration says will be validated, read back from the form."""
    wf = preset.get("walkForward") or {}
    mc = preset.get("monteCarlo") or {}
    intrabar = preset.get("intrabar") or {}
    return {
        "intrabar": (
            {"timeframe": intrabar.get("timeframe") or "auto"}
            if intrabar.get("enabled")
            else "off"
        ),
        "walk_forward": (
            {
                "mode": wf.get("mode"),
                "train_pct": wf.get("trainPct"),
                "trigger_mode": wf.get("triggerMode"),
                "trigger": wf.get("triggerEvery"),
            }
            if wf.get("enabled")
            else "off"
        ),
        "monte_carlo": (
            {
                "curves": mc.get("curves"),
                "trigger_mode": mc.get("triggerMode"),
                # Each mode with the parameters it will actually run with,
                # converted back from the form's 0-100 scale. Reading these back
                # is the only way to see a value that was left at the screen's.
                "modes": {
                    api: {
                        param: mc[panel_key] / scale
                        for (mode, param), (panel_key, scale) in _MC_MODE_PARAM_FIELDS.items()
                        if mode == api and mc.get(panel_key) is not None
                    }
                    for api, key in _MC_MODE_FIELDS.items()
                    if mc.get(key)
                },
            }
            if mc.get("enabled")
            else "off"
        ),
    }


async def _send_panel_command(
    client: BackendClient, action: str, args: dict[str, Any] | None = None, wait: float = 30.0
) -> dict[str, Any]:
    """Ask the Optimizer screen to perform an action, and wait for its answer.

    The screen's own handlers bind the run's ticket, open its WebSocket and
    reset the per-run buffers. Asking it to act is what makes a run behave like
    one the user launched — a request sent straight to the engine gets none of
    that, and the run never reaches a terminal state.
    """
    queued = await client.post(
        "/optimizer/panel/command", json={"action": action, "args": args or {}}
    )
    command_id = (queued or {}).get("id")

    # The screen polls once a second, so checking more often than that only
    # shortens the gap between it acting and this returning.
    deadline = time.time() + wait
    while time.time() < deadline:
        await asyncio.sleep(0.25)
        state = await client.get("/optimizer/panel/command")
        if not isinstance(state, dict) or state.get("id") != command_id:
            continue
        if state.get("status") == "done":
            return {"action": action, "applied": True}
        if state.get("status") == "rejected":
            raise McpToolError(
                f"The Optimizer screen refused to {action}: "
                f"{state.get('detail') or 'no reason given'}"
            )

    return {
        "action": action,
        "applied": False,
        "queued": True,
        "note": (
            "The Optimizer screen has not picked this up. It runs there, so it "
            "has to be open — the command is waiting and will run when it is."
        ),
    }


async def start_optimization(client: BackendClient) -> dict[str, Any]:
    """Start the configured run. The Optimizer screen does not have to be open.

    The backend reads the configuration that ``configure_optimization`` saved,
    validates it, shapes the engine's payload and starts the job itself — the
    same start the screen's own button performs. The screen, when it is open,
    is a view of that run rather than a precondition for it.
    """
    result = await client.post(
        "/optimizer/jobs/start-from-preset",
        json={},
        timeout=config.LONG_TIMEOUT,
    )
    opt_id = (result or {}).get("opt_id")
    ticket = (result or {}).get("ticket")

    _last_run.clear()
    if ticket:
        _last_run.update({"opt_id": opt_id, "ticket": ticket, "started_at": time.time()})

    return {
        "started": True,
        "opt_id": opt_id,
        "ticket": ticket,
        "dataset_path": (result or {}).get("dataset_path"),
        "range": {
            "start": (result or {}).get("start_time"),
            "end": (result or {}).get("end_time"),
        },
        "note": (
            "Poll get_optimization_status for saved cycles. An Optimizer screen "
            "that is open will not show this run: it attaches to a run it "
            "started, not to one it did not."
        ),
    }


async def get_optimization_status(
    client: BackendClient, opt_id: int | None = None
) -> dict[str, Any]:
    """Report progress from what the backend has saved for the run.

    The backend exposes no HTTP endpoint for a running job's state, so this
    reads the same manager metadata the Strategy Manager screen uses.
    """
    resolved = opt_id
    if resolved is None and _last_run:
        try:
            resolved = int(_last_run["opt_id"])
        except (KeyError, TypeError, ValueError):
            resolved = None
    if resolved is None:
        raise McpToolError(
            "No optimization started in this session. Pass opt_id, or list runs "
            "with list_optimizations."
        )

    metadata = await client.get(f"/manager/optimizations/{resolved}/metadata")
    info = (metadata or {}).get("optimization") or {}

    # The stored status column stays 'running' forever, so the engine is asked
    # directly. Only one optimization runs at a time: an active job with a
    # different id — or no active job at all — means this run is over.
    try:
        job = await client.get("/optimizer/jobs/active")
    except Exception:  # noqa: BLE001 — progress must still be reported
        job = None
    engine_active = bool((job or {}).get("active"))
    state = (
        "running"
        if engine_active and str((job or {}).get("db_opt_id")) == str(resolved)
        else "finished"
    )

    result: dict[str, Any] = {
        "opt_id": resolved,
        "state": state,
        "engine_active": engine_active,
        "strategy_name": info.get("strategy_name"),
        "method": info.get("method"),
        "cycles_saved": (metadata or {}).get("total_cycles"),
        "best_profit": info.get("best_profit"),
        "robust_methods": info.get("robust_methods"),
        "started": info.get("started"),
    }
    if state == "finished":
        result["note"] = (
            "The engine reports no active run with this id. An app restart "
            "reads the same way, so cross-check with a stable cycles_saved "
            "across two polls before treating a fresh run as finished."
        )
        result["next_step"] = (
            "Shortlist with list_optimization_cycles — narrow by the cycle's "
            "own metrics first, then compare the survivors by val_* and "
            "mc_score — then get_cycle_robustness on the shortlist and "
            "save_cycle_as_strategy for the winner."
        )
    else:
        result["note"] = "cycles_saved grows while the run is active."
    if "WalkForwardRolling" in str(info.get("robust_methods") or ""):
        result["rolling_check"] = (
            "This run carries Walk-Forward Rolling. Before trusting a finished "
            "run, verify the WalkForwardRolling bucket is non-empty with "
            "get_optimization_summary — a rolling run killed by RAM reads "
            "'finished' with 0 folds and no error."
        )
    if _last_run and str(_last_run.get("opt_id")) == str(resolved):
        result["ticket"] = _last_run["ticket"]
        result["age_seconds"] = round(time.time() - _last_run["started_at"], 1)
    return round_numbers(result)


async def control_optimization(
    client: BackendClient, action: str, workers: int | None = None
) -> dict[str, Any]:
    """Pause, resume, stop or rescale the run that is going.

    Addressed to the engine by the run's own ticket, so a run started without
    the Optimizer screen can still be controlled without it. Scaling only takes
    effect on a paused job — that is the engine's rule, and it is why the screen
    has no scale button either.
    """
    if action not in ("pause", "resume", "stop", "scale"):
        raise McpToolError("action must be 'pause', 'resume', 'stop' or 'scale'")
    if action == "scale" and not workers:
        raise McpToolError("scale requires workers (1-64)")

    job = await client.get("/optimizer/jobs/active")
    ticket = (job or {}).get("ticket") or _last_run.get("ticket")
    if not ticket:
        raise McpToolError(
            "No optimization is running. Nothing to " + action + "."
        )

    body: dict[str, Any] = {"ticket": ticket}
    if action == "scale":
        body["workers"] = max(1, min(workers, 64))

    result = await client.post(f"/optimizer/jobs/{action}", json=body)
    return {"action": action, "applied": True, "ticket": ticket, **(result or {})}


# The finalist battery, as OPTIMIZATION.md's "validating finalists" recipe has
# it: the stress modes that answer what the ranking modes cannot, plus
# bootstrap for the outcome distribution.
_FINALIST_MC_MODES = ("drop_best_trades", "cost_degradation", "time_slice", "bootstrap")


async def validate_finalist(
    client: BackendClient,
    strategy_id: int,
    dataset_id: str | None = None,
    folds: int = 6,
    curves: int = 500,
    monte_carlo_modes: list[str] | None = None,
    intrabar_timeframe: str | None = None,
    workers: int | None = None,
    max_ram_pct: int | None = None,
) -> dict[str, Any]:
    """Run the finalist robustness battery against a saved strategy, unchanged.

    The app has no standalone robustness runner, and a run has to be born on
    the Optimizer screen, so this configures a degenerate optimization — one
    combination, the strategy's own parameters — carrying the full finalist
    battery, and asks the screen to start it. The evidence lands where every
    run's evidence lands: rolling folds at the run level, Monte Carlo and
    Hold-Out on the single cycle.
    """
    sync = await client.get(f"/strategies/saved/{strategy_id}/optimizer-sync")
    if not isinstance(sync, dict):
        raise McpToolError(f"Strategy {strategy_id} cannot seed a validation run")
    base = sync.get("base_params") or {}

    # One numeric parameter pinned to its own value holds the space to exactly
    # one combination. A bool default expands to [True, False] and a string to
    # its options however the range is written, so neither can pin it.
    pin = next(
        (
            name
            for name, value in base.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        ),
        None,
    )
    if pin is None:
        raise McpToolError(
            f"validate_finalist pins one numeric parameter to hold the search "
            f"space to a single combination, and strategy {strategy_id} has no "
            "numeric parameter. Configure the run yourself: "
            "configure_optimization with the finalist robustness shape from "
            "mindstrat://settings and any one-combination range."
        )
    value = base[pin]

    resolved_dataset = dataset_id or sync.get("dataset_id")
    if not resolved_dataset:
        raise McpToolError(
            f"Strategy {strategy_id} has no dataset recorded; pass dataset_id."
        )

    robustness = {
        "walk_forward": {
            "mode": "rolling",
            "folds": max(2, int(folds)),
            "train_pct": 70,
            "val_pct": 30,
        },
        "monte_carlo": {
            "curves": max(1, int(curves)),
            "modes": list(monte_carlo_modes or _FINALIST_MC_MODES),
            # every_pass, or the single cycle may fall between 'cycles'
            # triggers and the run would produce no Monte Carlo at all.
            "trigger_mode": "every_pass",
        },
        "intrabar": {"enabled": True, "intrabar_timeframe": intrabar_timeframe},
    }

    configured = await configure_optimization(
        client,
        strategy_id,
        resolved_dataset,
        method="Brute Force",
        cycles=1,
        workers=workers,
        parameter_ranges={
            pin: {"from": value, "to": value, "step": 1, "default": value, "active": True}
        },
        robustness=robustness,
        max_ram_pct=max_ram_pct,
    )
    started = await start_optimization(client)

    result: dict[str, Any] = {
        "strategy_id": strategy_id,
        "dataset_id": resolved_dataset,
        "pinned_parameter": {pin: value},
        "validating": configured.get("robustness"),
        "screen_updated": configured.get("screen_updated"),
        **started,
    }
    if started.get("started"):
        result["next_step"] = (
            "Poll get_optimization_status until state is 'finished', verify "
            "the folds count is non-zero with get_optimization_summary, read "
            "the run's cycles with list_optimization_cycles (a rolling run "
            "writes one row per fold; with pinned parameters they repeat) "
            "and get_cycle_robustness, then "
            f"attach_rolling_to_strategy({strategy_id}, opt_id)."
        )
    return result


async def attach_rolling_to_strategy(
    client: BackendClient, strategy_id: int, opt_id: int
) -> dict[str, Any]:
    """Attach a Walk-Forward Rolling run's results to a saved strategy."""
    result = await client.post(
        f"/strategies/saved/{strategy_id}/attach-rolling",
        json={"opt_id": opt_id},
        timeout=config.LONG_TIMEOUT,
    )
    result = strip_bulk(result)
    if isinstance(result, dict):
        result["next_step"] = (
            f"Open get_strategy_detail({strategy_id}) and confirm the "
            "WalkForwardRolling folds are present and non-empty — a rolling "
            "run killed by RAM reads 'finished' with 0 folds and no error."
        )
    return result

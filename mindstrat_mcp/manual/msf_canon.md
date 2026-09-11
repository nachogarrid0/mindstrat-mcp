# MSF Strategy Canon
> This document defines the MANDATORY format and rules for creating MindStrat Strategy Format (MSF) strategies.
>
> Core features:
> 1. **Dual-library indicator system**: pandas-ta inline for convergent indicators (RSI, ATR, ADX, MACD, BB, SMA/EMA, Stoch, etc.) AND talipp + `engine.persist` for path-dependent indicators (SuperTrend, ParabolicSAR, OBV, session VWAP, Heikin-Ashi, Renko, ZigZag, Ichimoku). Path-dependent indicators implemented as pandas-ta vectorized **break in live** under the sliding window — talipp is mandatory for those.
> 2. **`engine.persist(key, factory)`** primitive that lets state survive between live ticks. Used canonically for talipp objects.
> 3. **Reserved keys in `engine.custom`**: `consecutive_losses` and `consecutive_wins` are framework-managed and reflect REAL exchange closures in live. The strategy reads them; never writes.
>
> Standard requirements: 5-param signature with `engine` as the 5th param, single return value (`visualization_data` dict), `auxiliary_datasets` declaration, `warmup_spec`. The engine handles position/PnL/commissions/equity.

## 1. General Structure & Imports

Every MSF strategy MUST follow this exact structure. Imports and configuration dictionaries must be at the global scope (module level).

### Always-required imports
```python
import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict, Any
```

### Talipp imports (ONLY when using path-dependent indicators)
```python
from talipp.indicators import SuperTrend           # or any other talipp class
from talipp.indicators.SuperTrend import Trend     # output enum (per-indicator)
from talipp.ohlcv import OHLCV                     # input type for OHLCV-based indicators
```

If the strategy only uses convergent indicators (pandas-ta), OMIT the talipp imports.

---

## 2. Configuration Dictionaries (Module Level)

All dictionaries MUST be defined at the **top of the file**, outside any function.

### strategy_parameters
User-tunable inputs. Types: `int`, `float`, `bool`, `str`.

```python
strategy_parameters: Dict[str, Any] = {
    # pandas-ta convergent
    "rsi_length": 14,
    "atr_period": 14,
    # talipp path-dependent
    "atr_multiplier": 3.0,
    # Risk management
    "takeProfitPerc": 2.0,
    "stopLossPerc": 1.0,
    # Auxiliary
    "macro_ema_period": 50,
}
```

### strategy_options
Categorical dropdowns for the UI. Keys **MUST MATCH** `strategy_parameters`.

```python
strategy_options: Dict[str, Any] = {
    "ma_source": ["open", "high", "low", "close", "hl2", "hlc3", "ohlc4"],
}
```

### auxiliary_datasets
Module-level declaration of how many auxiliary datasets the strategy needs and what each is for. The UI shows one dataset selector per declared key.

```python
auxiliary_datasets: Dict[str, str] = {
    "dataset_2": "Macro-trend filter (typically a higher timeframe of the same asset)",
}
```

- If the strategy uses **no** auxiliary datasets, declare an empty dict: `auxiliary_datasets: Dict[str, str] = {}`.
- The strategy **NEVER** hardcodes symbols or timeframes — the user picks each via the UI.
- Keys must be descriptive identifiers (e.g. `"dataset_2"`, `"correlation_asset"`, `"volume_profile"`).

### capital_cfg (injected by the runtime)
The app injects capital configuration via the `capital_cfg` argument of `trading_strategy(...)`. Strategies read it; they do not define it at module level. Shape:

```python
capital_cfg = {
    "initial_capital": 10000.0,
    "order_size_mode": "fixed_value",   # "fixed_value" | "fixed_qty" | "percent_of_equity"
    "order_size": 1000.0,
    "commission": 0.1,
    "commission_type": "percent",        # "percent" | "fixed"

    # Slippage — choose one mode:
    "slippage_mode": "none",             # "none" | "fixed" | "volume" | "random"
    "slippage_bps": 0.0,                 # used by "fixed" mode (basis points subtracted from fill price)
    "slippage_k": 1.0,                   # used by "volume" mode (slip ∝ k·sqrt(order_value / bar_volume_value))
    "slippage_mean_bps": 0.0,            # used by "random" mode (gaussian mean, in bps)
    "slippage_std_bps": 0.0,             # used by "random" mode (gaussian std)
    "slippage_seed": None,               # used by "random" mode (optional; None → non-deterministic)
}
```

---

## 3. Warmup Specification

**Live-trading metadata.** It tells the LIVE engine how many bars to put in the sliding window it hands the strategy on every tick. The BACKTEST never reads it — it passes the whole dataset — so a `warmup_spec` that is wrong, incomplete, or names keys absent from `strategy_parameters` is invisible in backtest and only surfaces after deploy, as indicators that are all NaN.

Declare every rolling lookback the code uses. Talipp Wilder-based indicators (SuperTrend's ATR, talipp RSI) go in the SAME `wilder_lengths` list as their pandas-ta equivalents.

```python
warmup_spec: Dict[str, Any] = {
    # Primary dataset
    "simple_windows": ["ma_period"],
    "wilder_lengths": [
        "rsi_length",        # pandas-ta RSI Wilder smoothing
        "atr_period",        # covers BOTH pandas-ta ATR AND talipp SuperTrend ATR
        ("adx_len", "adx_smooth"),  # tuple = sum the lengths
    ],
    "epsilon": 0.001,

    # Auxiliary datasets (keys MUST match auxiliary_datasets)
    "auxiliary": {
        "dataset_2": {
            "simple_windows": ["macro_ema_period"],
            "wilder_lengths": [],
        },
    },
}
```

**Window types:**
- `simple_windows`: SMA / rolling indicators. Warmup = `max(periods)`.
- `wilder_lengths`: RMA / EMA (Wilder) indicators. Per-key warmup = `ceil(log(epsilon) / log(1 - 1/length))` — the smallest `n` such that `(1 - 1/length)^n < epsilon`. The live engine adds a small fixed pad (+2 bars) on top of the max across all `warmup_spec` entries.
- Compound tuples (e.g. `("adx_len", "adx_smooth")`): the raw param values are summed first, then the Wilder formula is applied to the sum (NOT Wilder-per-key then summed).

**The warmup is a `max()`, not a sum**, and a key is only counted if it exists in `strategy_parameters`. Two consequences worth knowing: a spec that names nothing the params declare yields the pad alone (2 bars), and for a composed indicator — an SMA of an EMA, a z-score over a shifted window — listing the components understates the true lookback. Declare one parameter holding the real total instead.

If `auxiliary_datasets` is empty, omit the `"auxiliary"` section (or set it to `{}`).

---

## 4. Source Parameters & Calculation

- **NEVER** use a generic key `"source"` if multiple indicators are used.
- **USE**: `"rsi_source"`, `"ma_source"`, `"atr_source"`.
- **MATCH**: The key in `strategy_parameters` **MUST MATCH** the key in `strategy_options`.

```python
def compute_source(df: pd.DataFrame, key: str) -> pd.Series:
    if key == "hl2": return (df["high"] + df["low"]) / 2.0
    if key == "hlc3": return (df["high"] + df["low"] + df["close"]) / 3.0
    if key == "ohlc4": return (df["open"] + df["high"] + df["low"] + df["close"]) / 4.0
    return df[key]
```

---

## 5. Main Strategy Function Signature

```python
def trading_strategy(
    data: pd.DataFrame,
    data_aux: Dict[str, pd.DataFrame],
    params: Dict[str, Any],
    capital_cfg: Dict[str, Any],
    engine,                                # PositionEngine injected by runtime
) -> Dict[str, Any]:                       # returns ONLY visualization_data
```

- 5 parameters, in this order, with these names. The 5th parameter MUST be named `engine`. Runtime detection: `len(params) >= 5 and params[4] == "engine"`.
- `data_aux` is a `Dict[str, pd.DataFrame]` keyed by the same identifiers declared in `auxiliary_datasets`.
- Each auxiliary DataFrame has columns `time` (or `open_time`), `open`, `high`, `low`, `close`; `volume` is optional. Sorted ascending by time. **Read-only**.
- If a declared key is not selected by the user, it is simply absent from `data_aux`. The strategy decides whether to tolerate the absence or fail explicitly.

**Return rules:**
- Returns ONLY `visualization_data` dict — NOT a tuple.
- NO `trades` list — the engine collects trades internally.
- NO `state` dict — the engine manages all state.

---

## 6. Engine API (What the strategy uses)

### Position queries (read-only)
```python
engine.is_flat       # True if no position
engine.is_long       # True if long position
engine.is_short      # True if short position
engine.avg_cost      # Weighted average entry price
engine.qty           # Current position size
engine.side          # "long" | "short" | None
engine.equity        # Current equity (in live, injected from LiveState.real_equity)
engine.bars_in_trade # Bars since first entry (0 on entry bar)
engine.last_fill_price
engine.consecutive_wins      # ⚠ field (window-only in live; prefer engine.custom["consecutive_wins"])
engine.consecutive_losses    # ⚠ field (window-only in live; prefer engine.custom["consecutive_losses"])
engine.custom        # dict for arbitrary strategy state (persists across bars; in live persists across ticks)
engine.get_trades()  # ⚠ BACKTEST ONLY — effectively empty in live (see below)
```

### Actions
```python
engine.on_bar(bar=(o, h, l, c), time=timestamp)   # MUST call first every bar
engine.buy(price=None, size=None, signal="BUY")    # price=None -> open, size=None -> auto
engine.sell(price=None, size=None, signal="SELL")  # mirror of buy for short
engine.close(price=None, size=None, signal="CLOSE") # size=None -> close all; size<qty -> partial close
engine.set_exit(tp=None, sl=None, trailing=None)  # set TP/SL/trailing levels (fires intra-bar check)
```

`buy`/`sell`/`close` accept **only** `price`, `size`, `signal`. There is NO `size_fraction`/`fraction`/`pct` kwarg — to size down, pass `size=base_size * fraction`.

### Completed trades & fills — read-only accessors + schema

> **`get_trades()` is a backtest-only accessor. Never build strategy logic on it.**
> In backtest it returns every completed trade of the run. In live the completed-trade
> list is emptied on every tick — closed trades live in the cloud store, and keeping
> them in memory once grew unbounded and killed containers — so it returns at most
> what the current tick's replay reconstructed, never the deploy's history.
>
> A daily trade cap, a cooldown after N losses, an equity-curve filter: all of these
> silently never fire in live if they count `get_trades()`. Count closures yourself
> into `engine.persist` behind a `last_t` guard, or read the framework-maintained
> `engine.custom["consecutive_wins"] / ["consecutive_losses"]` (§9.1).
>
> Reading it for a *reporting* value returned in `visualization_data` is fine.

```python
engine.get_trades()  # list[dict], one per completed (flat→flat) trade
# trade dict keys:
#   side, entry_time, exit_time, avg_entry_price, avg_exit_price,
#   pnl, commission, slippage, bars_in_trade, mfe, mae, fills
#   → PnL key is "pnl" (absolute $). There is NO "pnl_pct"
#     (derive % yourself from avg_entry_price/avg_exit_price if needed).
# fill dict keys (each item in trade["fills"] and in engine._fills):
#   time, type ("buy"|"sell"|"close"), price, size, signal,
#   fee, slippage, is_pyramid, is_partial_close, is_final_close
#   → leg side lives in "type". There is NO "side" key on a fill —
#     count legs with f["type"] == "buy"/"sell"/"close", never f.get("side").
```

### Does NOT exist — common hallucinations (denylist)
These names look plausible but are NOT part of the engine. Using them fails silently
(`getattr` defaults / `.get()` → `None`) or raises `TypeError`:
- `engine.closed_trades`, `engine.closed_trades_count`, `engine.n_trades` → use `engine.get_trades()` / `len(engine.get_trades())` — and only for reporting, never for a decision: it is backtest-only (see the accessor note above).
- `trade["pnl_pct"]` → use `trade["pnl"]`.
- `fill["side"]` → use `fill["type"]`.
- `engine.buy/sell/close(size_fraction=...)` (or `fraction=`, `pct=`) → only `price`, `size`, `signal`.
- Manual TP/SL/trailing on `c[i]`/`h[i]`/`l[i]` → use `engine.set_exit(...)` (see §7.7).

### Sizing by losing/winning streak (correct pattern)
- **Backtest**: read `engine.consecutive_losses` / `engine.consecutive_wins`.
- **Live**: read `engine.custom["consecutive_losses"]` / `["consecutive_wins"]` — the reserved keys the live motor injects each tick (the bare fields are window-only in live; see the `⚠` note in the queries block above).
- Apply the size at entry: `engine.buy(size=base_size * size_fraction, signal=...)`. Do NOT "buy full then close part", and do NOT invent a `size_fraction` kwarg.

### `engine.persist(key, factory=None)` — MSF primitive

```python
result = engine.persist(key: str, factory: Optional[Callable[[], Any]] = None)
```

Behavior:
- If `key` exists in `engine.custom`: returns `engine.custom[key]` (the same reference, not a copy).
- If `key` does not exist and `factory` is provided: calls `factory()`, stores the result in `engine.custom[key]`, returns it.
- If `key` does not exist and `factory` is `None`: returns `None`.

Behavior per engine context:
- **Backtest** (Strategy Creator): one invocation, `engine.custom` empty at start. `persist` acts as "lazy create once".
- **Optimizer**: one invocation per trial, `engine.custom` fresh per trial. No cross-trial contamination.
- **Live**: `trading_strategy` is called per tick. `engine.custom` is preserved between ticks (shallow copy by the live motor). `persist` returns the **same instance** between ticks. This is what makes talipp objects accumulate state correctly.

### Rules
- `on_bar()` MUST be called before any `buy/sell/close` on each bar.
- `buy()` while short raises `EngineError` (close first, then buy).
- `sell()` while long raises `EngineError` (close first, then sell).
- `close()` while flat raises `EngineError`.
- `price` defaults to bar open; must be within `[low, high]` if specified.
- `size` defaults to auto-calculation from `order_size_mode` in `capital_cfg`.
- TP/SL are checked automatically inside `on_bar()` AND inside `set_exit()` (intra-bar hook). Strategy does NOT check them manually.
- TP/SL/trailing reset to `None` when position goes flat.

### `engine._is_live` (read-only)
- `True` only inside the live motor. The strategy generally doesn't need to read this — the patterns work uniformly. Intended for engine internals (e.g., `_complete_trade` skips writing to reserved keys when `_is_live=True` so the live motor's real values aren't overwritten by the bar loop replay).

### Class-of-bug: per-tick re-execution of `trading_strategy()`

In **backtest**, `trading_strategy(data, data_aux, params, capital_cfg, engine)` is called **exactly ONCE** with the full DataFrame. Local variables, counters, lists, and dicts initialized at the top of the function live for the entire run. In **live**, the same function is called **once per WebSocket tick**. Every call is a fresh stack: local variables reset, pandas-ta indicators recompute on a sliding window slice. The only state that survives between ticks is what the function writes to `engine.persist(...)` (shallow-copied from `LiveState.persisted_custom` at the top of every tick).

**The bug class**: any state the strategy needs to ACCUMULATE across bars MUST live in `engine.persist`. State in plain local variables works perfectly in backtest (persists for the entire run because there's only one call) and breaks silently in live (resets every tick). Silent in backtest (counters grow, flags toggle, lists populate as expected). Broken in live (counters always 0-1, flags always False, lists always empty). The strategy "works" in backtest, takes different decisions in live, and the operator has no error to debug — just inexplicably different behavior.

**Common shapes of this bug** — all look fine in backtest, all break in live:
1. **Counter**: `rsi_crosses = 0` at top, incremented in loop. In live re-initializes to 0 every tick.
2. **Flag**: `macro_filter_passed = False` at top, set to True when condition met. In live always re-starts False.
3. **Last-known-value tracker**: `last_swing_high = None` updated inside loop. In live always None at tick start.
4. **Memoization / cache**: dict computed inside the function. In live empty every tick — "optimization" is dead code.
5. **List of past events**: `recent_trades = []` appended in loop. In live always empty at tick start.
6. **Cooldown timer**: `bars_since_last_trade = 0` incremented per bar. In live always re-starts at 0.

**Correct pattern — `engine.persist` + `last_t` timestamp guard**:

```python
def trading_strategy(data, data_aux, params, capital_cfg, engine):
    state = engine.persist("session_state", factory=lambda: {
        "rsi_crosses": 0,
        "last_swing_high": None,
        "last_t": -1,         # timestamp of the last closed bar processed
    })
    for i in range(1, n):
        engine.on_bar(...)
        bar_t = int(tms[i-1])  # timestamp of the closed bar evaluated for signals
        if bar_t > state["last_t"]:
            if rsi_cross[i-1]:
                state["rsi_crosses"] += 1
            if swing_up[i-1]:
                state["last_swing_high"] = float(h[i-1])
            state["last_t"] = bar_t
```

The `factory` lambda runs ONCE per deploy (or first call after a state reset). All subsequent ticks get the SAME dict back, with mutations from prior ticks preserved. The `last_t` **timestamp guard** is essential: in live, the bar loop re-iterates all visible closed bars on every tick — without the guard, counters would be incremented multiple times for the same closed bar. **Use timestamps (`int(tms[i-1])`), NOT indices** — when the strategy is flat in live, the sliding window shifts indices between ticks; timestamps are absolute and stable. Same pattern as the talipp canonical loop in §7.3.

**What does NOT need `engine.persist`** (correctly locals):
- Vectorized arrays computed from `data` at the top (e.g., `ema = ta.ema(data["close"], length=...)`). Pure functions of `data` — recomputing per tick is correct.
- Variables that live within a single iteration of the bar loop (e.g., `curr_price = float(c[i-1])`).
- Values read from `engine.*` (`engine.qty`, `engine.avg_cost`, `engine.is_long`, `engine.equity`, `engine._fills`) — already persisted by the engine.
- Fill counters (`n_buy`, `n_cls`) derived from `engine._fills` each iteration (§7.6) — `_fills` IS persisted by the engine.

**Mental test**: imagine the function is killed and respawned 50 times during a single bar (that's literally what happens in live). Would all accumulators still hold the correct values? If no, they need `engine.persist`.

---

## 7. Two-Engine Indicator System (CRITICAL)

MSF uses two indicator engines side by side. Picking the wrong one is the most common source of strategies that pass backtest and break in live.

### 7.1. pandas-ta (convergent, vectorized, batch)

Use for indicators whose value at bar `t` is determined by a fixed window of past data, with no path dependency on bars BEFORE the window.

Examples: **RSI**, **ATR**, **ADX/DMI**, **MACD**, **Bollinger Bands**, **SMA / EMA / WMA / DEMA / TEMA**, **Stochastic**, **ROC**, **Momentum**, **CCI**, **Williams %R**, **MFI**.

Pattern (vectorized, pre-loop → LOCAL numpy arrays):
```python
rsi_arr = ta.rsi(data["close"], length=int(params["rsi_length"])).to_numpy()
atr_arr = ta.atr(data["high"], data["low"], data["close"],
                 length=int(params["atr_period"])).to_numpy()
```

> ⚠️ **Optimizer-safe code (CRITICAL)**: NEVER assign the result to `data[...]`
> (e.g. `data["RSI"] = ta.rsi(...)`). The optimizer reuses the same `data`
> DataFrame — backed by `multiprocessing.shared_memory` — across every trial
> inside a worker. Assigning a new column forces pandas to reallocate the
> BlockManager out of the shared buffer; multiplied by N workers and M trials
> → RAM exhaustion before the first cycle completes. The strategy works in the
> strategy creator (which `.copy()`s `data` per run) and silently dies in the
> optimizer. Reading via `.values` is fine; writing is forbidden. Same logic
> as the talipp module-level restriction below: anything that pollutes shared
> state across trials is rejected. See `runtime_constraints.md` §6.

### 7.2. talipp (path-dependent, incremental, stateful)

Use for indicators whose value at bar `t` depends on the entire history since session/series start, and would break under a sliding window. Live engines use rolling windows — implementing these as pandas-ta vectorized would compute the indicator over a partial history on every tick, corrupting state.

Examples: **SuperTrend**, **ParabolicSAR**, **OBV**, **session VWAP**, **Heikin-Ashi**, **Renko**, **ZigZag**, **Ichimoku Senkou Span**, **Accumulation/Distribution**, **Chaikin Oscillator**.

> ⚠️ **Most common audit failure**: implementing one of the indicators above with pandas-ta (`ta.obv()`, `ta.psar()`, `ta.supertrend()`, `ta.vwap()`) and then emitting `Live-ready ✅`. The code passes backtest (single full pass) and silently produces different values in live (sliding window reset every tick). When the Live-Readiness Audit enumerates indicators, any indicator from THIS list implemented via pandas-ta is an automatic ❌ — no exceptions.

Pattern (incremental, persisted across ticks):
```python
# Top of trading_strategy()
st = engine.persist(
    "st_obj",
    factory=lambda: SuperTrend(atr_period=atr_len, mult=atr_mult),
)
state = engine.persist("st_state", factory=lambda: {"last_t": -1})

# Feed via add() / update() (next section)
# Read via st.output_values + padding pattern (next-next section)
```

### 7.3. Canonical add+update pattern — CLOSED-BARS-ONLY

**THE RULE**: path-dependent indicators (talipp + `engine.persist`) NEVER receive the forming bar. The strategy iterates feeding loops up to `n_closed = n - 1`, never up to `n`. The forming bar at index `n-1` is ALWAYS quarantined from indicators.

Why: in live, the strategy is re-invoked on every aggTrade tick. The forming bar's OHLC changes continuously. Feeding `st.update(forming_bar)` on every tick produces hundreds of `update()` calls per bar with different partial OHLC values. Most path-dependent indicators (SuperTrend's `final_upper/final_lower`, KAMA's efficiency ratio, OBV's cumulative sum, etc.) carry internal state that **drifts** across these partial-OHLC updates. The closed-bar final value matches at the talipp `input_values[-1]` level, but the path-dependent state derived from it does NOT. Result: trend / band / cumulative value occasionally differs between live and backtest in borderline bars — extra trade or missing trade.

In backtest there are no ticks — every bar is closed when it arrives, so the canonical pattern below works identically (just no per-tick re-execution to drift state).

```python
n_closed = n - 1   # exclude forming bar (last row of `data`)
last_t = state["last_t"]

# Window-slid guard: if the rolling window slid past last_t (live anomaly:
# container paused, WS gap, recovery), the talipp object has stale state for
# bars no longer in the window. Reset and re-warmup from scratch.
if last_t > 0:
    new_idx_check = int(np.searchsorted(tms[:n_closed], last_t, side="right"))
    if new_idx_check == 0:
        engine.custom.pop("st_obj", None)
        engine.custom.pop("st_state", None)
        st = engine.persist("st_obj", factory=lambda: SuperTrend(...))
        state = engine.persist("st_state", factory=lambda: {"last_t": -1})
        last_t = -1

if last_t < 0:
    # First invocation (or post-reset): full warmup with add() — closed bars only.
    for i in range(n_closed):                # NOT range(n)
        st.add(OHLCV(open=float(o[i]), high=float(h[i]),
                     low=float(l[i]), close=float(c[i])))
    if n_closed > 0:
        state["last_t"] = int(tms[n_closed - 1])
else:
    new_idx = int(np.searchsorted(tms[:n_closed], last_t, side="right"))
    if new_idx < n_closed:
        # New bar(s) have CLOSED since the last tick. Add with FINAL OHLC.
        for i in range(new_idx, n_closed):
            st.add(OHLCV(open=float(o[i]), high=float(h[i]),
                         low=float(l[i]), close=float(c[i])))
        state["last_t"] = int(tms[n_closed - 1])
    # else: no new closed bars since last tick — no-op. The forming bar
    # (data.iloc[n-1]) is NEVER fed. TP/SL/trailing intra-bar reactivity
    # remains via engine._bar (set by engine.on_bar()), NOT via indicator value.
```

**Why this preserves intra-bar TP/SL reactivity**: the forming-bar quarantine ONLY applies to path-dependent INDICATORS that feed signals. The position engine's TP/SL/trailing checks read `engine._bar` directly (set by every `engine.on_bar()` call inside the bar loop, with the forming bar's latest OHLC). Those continue firing sub-50ms in live on every aggTrade. See `runtime_constraints.md §11` for the full forming-bar quarantine specification.

### 7.4. `output_values` padding pattern (MANDATORY) — length aligned with `n`

talipp's `output_values` grows by one entry on every `add()` call (entry is `None` during warmup until the indicator has enough history; once warmed up, entries are the actual computed values — so `len(output_values) == len(input_values)` always at the talipp level). Since the strategy only feeds closed bars (§7.3), `len(output_values) == n_closed`. The mismatch with the `n` primary bars is exactly **+1** (the forming bar at index `n-1` is intentionally excluded).

In live, the talipp object is persisted across ticks via `engine.persist`, so across many ticks `output_values` accumulates well past `n_closed`. Slice `[-n_closed:]` to align with the current `n_closed`-bar window, then **append a `None` for the forming bar** so the resulting array has length `n` (aligned with `data`).

**The footgun**: `raw = list(st.output_values)[-n:]` (no padding, no forming-bar slot). Passes backtest, breaks live with broadcast error OR — worse — produces a length-`n` array where `raw[n-1]` is the CLOSED bar `n-2`'s value (mis-indexed by 1) → silently shifted signals.

**Canonical pattern**:
```python
raw = list(st.output_values)                  # length = n_closed
if len(raw) < n_closed:
    raw = [None] * (n_closed - len(raw)) + raw    # warmup gap → pad start
else:
    raw = raw[-n_closed:]                          # live: accumulated → slice end
raw.append(None)                              # forming bar slot — indicator undefined
# raw now has length n. raw[n-1] is None (forming bar). raw[i] for i < n-1 is a closed-bar value.
```

Then convert to NumPy handling the `None` entries (typically with `np.nan`):
```python
trend = np.array([
    (1.0 if v.trend == Trend.UP else -1.0) if v is not None else np.nan
    for v in raw
], dtype=np.float64)
# trend[n-1] is NaN (forming bar). flip_up[n-1] / flip_down[n-1] are False.
# Entries are decided on flip_up[i-1] — the PREVIOUS (closed) bar's signal.
```

### 7.5. The `set_exit` intra-bar hook (CRITICAL)

`engine.set_exit(tp=..., sl=..., trailing=...)` immediately fires `_check_tp_sl` against the current bar's H/L. This is the mechanism that makes TP/SL fire on the same bar as the entry (otherwise TP/SL would only fire on the NEXT bar's `on_bar()`, leaving exposure during the entry bar).

**Consequence**: if the entry bar's H/L already crossed the TP/SL level when you call `set_exit`, the engine **auto-closes the position inside `set_exit`** — same iteration of the bar loop.

**Mandatory pattern**: any engine action AFTER a `set_exit` must re-check `engine.is_long` / `engine.is_short`:

```python
if engine.is_long:
    # ... pyramid logic ...
    engine.buy(size=pyramid_size, signal="PYRAMID_BUY")
    engine.set_exit(sl=engine.avg_cost * (1 - sl_pct))
    # set_exit may have auto-closed → re-check before partial close
    if engine.is_long and h[i-1] >= engine.avg_cost * (1 + tp1_pct):
        engine.close(size=engine.qty * 0.5, signal="PARTIAL_TP1")
        engine.set_exit(tp=engine.avg_cost * (1 + tp2_pct),
                        sl=engine.avg_cost * (1 - sl_pct))
```

Without the re-check, a tight SL on a wide bar will auto-close inside the first `set_exit`, leaving `engine.is_flat=True` and `engine.avg_cost=0`. The next `engine.close(size=qty*0.5)` raises `EngineError("Cannot close: no open position.")`.

### 7.6. Class-of-bug: BT↔live divergence on intra-bar order (guard with fill counters)

`engine.on_bar()` runs **first** in the bar loop. In backtest it receives the bar's complete H/L and resolves TP/SL/trailing **immediately** against the final values — so by the time the rest of your strategy code runs, the engine may have already auto-closed the position. In live, `on_bar` runs per tick: it only sees H/L up to the current tick. Intermediate ticks frequently arrive with `engine.is_long`/`is_short` still True and TP/SL not yet fired — the rest of your strategy code runs in those tick states. Same code, same data, different execution states.

**The bug class**: any code AFTER `engine.on_bar()` that depends on `engine.is_long` / `engine.is_short` (or any state derived from "position is still open") can diverge between modes. A path unreachable in backtest (because `on_bar` auto-closed with final H) can execute in live on intermediate ticks — emitting orders that backtest never produced. Silent in backtest, costly in live (real money on real orders).

**Defensive pattern — guard with fill counters, not only with position flags**: `is_long`/`is_short` cannot distinguish "leg-1 open, no exit yet" from "leg-1+leg-2 open, partial close already done, remainder still open". Both have `is_long==True`. Whenever a strategy has multiple actions on the same position within a single bar (scaling in, scaling out, partial close, re-entry, exit-and-reverse), each action MUST be guarded by **fill counters** describing what already happened in the trade:

```python
n_buy  = sum(1 for f in engine._fills if f["type"] == "buy")    # all opens / pyramid legs (long side)
n_sell = sum(1 for f in engine._fills if f["type"] == "sell")   # all opens / pyramid legs (short side)
n_cls  = sum(1 for f in engine._fills if f["type"] == "close")  # ALL closes — manual AND auto-fired (TP, SL, trailing)

# Every multi-action block guards on trade-state counters, NOT just is_long:
if engine.is_long and n_buy == 1 and n_cls == 0:
    # "I'm in the initial leg, before any partial. Safe to scale in."
    ...
```

Count by `type` **only** — do NOT filter by signal substring. `engine.close()` calls auto-fired by `_check_tp_sl()` (TP/SL/trailing hits) carry engine-generated signals like `"TP"`, `"SL_LONG"`, `"TRAILING_STOP"` which contain neither `"close"` nor `"buy"`/`"sell"` — filtering by signal misses them and the guard re-fires on the next bar.

**`_fills` schema** (each fill dict): `"time"`, `"type"` (`"buy" | "sell" | "close"`), `"price"`, `"size"`, `"signal"`, `"fee"`, `"slippage"`, `"is_pyramid"`, `"is_partial_close"`, `"is_final_close"`. There is **no `"side"` key** — `engine.side` exists at the engine level (string `None`/`"long"`/`"short"`); for branching, use the boolean accessors `engine.is_long` / `engine.is_short` / `engine.is_flat`. When counting fills, always read `f["type"]`.

**Mitigation summary**:
1. After every `engine.set_exit(...)`, re-check `engine.is_long`/`engine.is_short` before the next engine action (§7.5).
2. In any multi-action block, guard each step with fill counters in addition to position state.
3. Mentally simulate both modes: "what does backtest run if `on_bar` already closed the trade?" and "what does live run if it hasn't?". If the two paths produce different orders, the guard is insufficient.

### 7.7. Intra-bar look-ahead on the primary bar — legal inputs at decision time

At bar `i` in the bar loop, the strategy is acting on the **forming** bar in live. Only three price sources exist at that moment and are therefore legal inputs to any decision or level:
- `engine.avg_cost` — the actual fill price (read AFTER `engine.buy()` / `engine.sell()`).
- `engine._bar[0]` / `o[i]` — the bar OPEN (what `buy()`/`sell()` fill at when no explicit price is passed).
- any value from a CLOSED bar, index `≤ i-1` (`c[i-1]`, `h[i-1]`, indicator `[i-1]`, …).

The forming bar's eventual `c[i]` / `h[i]` / `l[i]` do **NOT exist yet** when the loop acts in live. Using them is look-ahead.

**Anti-pattern (silent in backtest, diverges live):**
```python
engine.buy(signal="LONG")          # fills at o[i] (open) → avg_cost = o[i]
entry = float(c[i])                # ❌ c[i] = the entry bar's FINAL close (future)
engine.set_exit(tp=entry * (1 + tp_pct),
                sl=entry * (1 - sl_pct))   # anchored to a price that doesn't exist yet in live
```
In backtest `c[i]` is the known close of the bar → the TP/SL land relative to a future price, inflating results. In live, when this entry fires, `c[i]` is just the current forming price (≈ `o[i]`), so the levels differ → no parity. The damage scales with the entry bar's body: a TP tighter than the open→close range becomes essentially "pre-hit" in backtest (e.g. profit factor collapses from an inflated value to ~1 once anchored correctly).

**Canonical (parity-safe):**
```python
engine.buy(signal="LONG")
engine.set_exit(tp=engine.avg_cost * (1 + tp_pct),
                sl=engine.avg_cost * (1 - sl_pct))   # ✅ anchor to the real fill
```
Same rule for trailing: `engine.set_exit(trailing=engine.avg_cost * trailing_pct)`. And gate the entry/exit DECISION on `[i-1]` (closed) signals, never `[i]`.

**Managed exits ONLY — never a manual trailing/stop in the loop.** TP/SL/trailing must go through `engine.set_exit(...)`. A hand-rolled trailing that ratchets a peak and exits off the current bar's OHLC is NOT parity-safe:
```python
# ❌ ANTI-PATTERN: manual trailing on the chart bar
peak = max(peak, float(h[i]))                 # ratchets on the chart bar's high
if float(c[i]) <= peak * (1 - trail_pct):     # checks the chart bar's close
    engine.close(signal="TRAIL")
```
Two failures: (1) backtest evaluates this **once per chart bar** (with the bar's full H/L) while live re-runs the loop **per tick** → the exit fires at different moments → divergence; (2) it **bypasses the engine's intrabar replay** (the sub-bar simulation only drives `engine.set_exit` exits via `_check_tp_sl`), so enabling intrabar simulation changes nothing. Correct: `engine.set_exit(trailing=engine.avg_cost * trail_pct)` and let the engine handle it.

### 7.8. The two channels — the rule behind ALL of the above

§7.3 (forming-bar quarantine), §7.7 (anchoring + managed exits) and the manual-trailing trap are facets of ONE principle. MSF has two execution channels with different time resolution:

- **Channel 1 — the engine (`engine.set_exit(...)`)**: the ONLY place with intra-bar precision. "Price touches a level *inside* the bar" events — **TP / SL / trailing** — go here. The engine watches them continuously: in live on every tick, in backtest by replaying each chart bar at a finer timeframe. The LEVEL is identical in both; what differs is how finely the bar is resolved — see the note below.
- **Channel 2 — the strategy's `for i in range(1, n)` loop**: **chart-bar granularity, no intrabar**. Everything the strategy decides itself uses the **CLOSED bar `[i-1]`** (signals, gates, signal-exits, partial closes).

**Hard rule:** never read the current bar's `h[i]`/`l[i]`/`c[i]` for a decision, level, or exit. In backtest `[i]` is the bar's full (eventual) high/low = look-ahead; in live it's the forming bar per-tick → they diverge. Safe current-bar reads: `o[i]` (open = fill price) and `engine.avg_cost`. Current-bar `h[i]/l[i]/c[i]` are legal ONLY inside a feed (`engine.on_bar(...)`, `OHLCV(...)`). This one rule covers the whole family — trailing, anchoring (`entry=c[i]`), manual TP/SL, manual partial.

### 7.9. What happens when one bar touches BOTH the TP and the SL

Channel 1 gives you the same LEVEL in backtest and live. It does not, by default, give you the same ANSWER about which level was reached first — and that is the one place where a correct strategy still produces two different numbers.

**Intrabar simulation is off by default**, in every entry point. With it off, the engine replays each chart bar as a single sub-bar: it tests the open for a gap, then the high and the low **in a fixed worst-case-first order**. So a bar whose range spans both levels is booked as the **stop**, never the take-profit. That is conservative on the tie, but it is an assumption about sequencing, not a measurement — and turning intrabar ON can therefore make a result look *better*, not worse.

**With intrabar on**, the chart bar is replayed at a finer timeframe and the real order is resolved. The finer timeframe is **mapped, not 1-minute**:

| Chart | Replay | Chart | Replay | Chart | Replay |
|---|---|---|---|---|---|
| 1m | 1m | 1h | 15m | 8h | 2h |
| 3m | 1m | 2h | 30m | 12h | 4h |
| 5m | 1m | 4h | 1h | 1d | 4h |
| 15m | 5m | 6h | 1h | 1w | 1d |
| 30m | 5m | | | 1M | 1w |

Only 1m/3m/5m charts replay at 1m. On a 1h chart "intrabar" means four 15-minute sub-bars — finer than one bar, far from tick resolution. The finer dataset has to already be downloaded and has to cover the window, or the run falls back to the single-sub-bar path.

**What this means when you write a strategy:**

- For anything that exits via `engine.set_exit`, a run **without** intrabar is a draft, not a result. Enable it on any run whose numbers you intend to compare, save, or act on.
- Size the take-profit and the stop so that a single bar rarely spans both. That is the only fix that removes the ambiguity instead of measuring it more finely — and it is the one that also holds in live, where there is no replay at all and the levels are evaluated against the forming bar as it develops.
- Two runs of the same code on the same data, one with intrabar and one without, are both legitimate and will disagree. Nothing in the app records which one produced a saved number, so say which you used when you report one.

---

## 8. Auxiliary Datasets — Read-Only Inputs

### 8.1. Validation
The backend validates that frontend-supplied keys are declared in `auxiliary_datasets`. Unknown keys → 400 error. Each aux DataFrame is guaranteed to have `time/open_time, open, high, low, close` columns and to be non-empty if present.

### 8.2. Strategy-side validation
If an auxiliary is essential, validate explicitly and raise `ValueError` with a clear message. Never silently change logic when an essential auxiliary is missing.

```python
if "dataset_2" not in data_aux or data_aux["dataset_2"].empty:
    raise ValueError(
        "This strategy requires dataset_2 (macro-trend filter). "
        "Select an auxiliary dataset in the UI."
    )
```

### 8.3. Indicator computation (vectorized, pre-loop)
```python
aux2        = data_aux["dataset_2"]
aux2_times  = aux2["time"].values if "time" in aux2.columns else aux2["open_time"].values
aux2_close  = aux2["close"].values
aux2_ema    = aux2["close"].ewm(span=int(params["macro_ema_period"]), adjust=False).mean().values
```

talipp objects can also be applied to auxiliary datasets — same `engine.persist` + add+update pattern, with `aux2_times` instead of `tms` for tracking.

### 8.4. Temporal alignment (point-in-time, no look-ahead)
Use `np.searchsorted(aux_times, tms[i], side="right") - 1` inside the bar loop:

```python
macro_idx = int(np.searchsorted(aux2_times, tms[i], side="right")) - 1
if macro_idx >= 0:
    macro_bullish = aux2_close[macro_idx] > aux2_ema[macro_idx]
else:
    macro_bullish = False   # no auxiliary data yet
```

**Rules:**
- **ALWAYS** use `side="right"` and subtract 1. This yields "last known value" without look-ahead bias.
- **ALWAYS** handle `idx < 0` (no auxiliary data yet at the start of the period).
- **NEVER** interpolate auxiliaries — use point-in-time values as-is.
- **NEVER** merge / join / reindex auxiliaries with the primary DataFrame. That alters primary length and breaks visualization.
- **NEVER** modify auxiliary DataFrames.

---

## 9. Risk Management via Engine State

The engine exposes cumulative statistics that the strategy can read to implement risk management logic.

### 9.1. Reserved keys in `engine.custom`

Two keys are framework-managed; the strategy READS them, NEVER writes them:

| Key | Backtest | Live |
|-----|---------|------|
| `engine.custom["consecutive_losses"]` | Increments on every `_complete_trade` with PnL < 0 (replay-based) | Reflects REAL exchange closures since deploy start (deploy-cumulative) |
| `engine.custom["consecutive_wins"]` | Increments on every `_complete_trade` with PnL > 0 | Same — REAL exchange closures |

These work uniformly across modes. Use them for risk gates instead of `engine.consecutive_losses` / `engine.consecutive_wins` (the field versions reflect only the current window in live, which is misleading).

```python
if engine.custom.get("consecutive_losses", 0) >= int(params["max_consecutive_losses"]):
    continue   # skip entries; TP/SL of an open trade still active via on_bar()
```

### 9.2. Equity-based gates

`engine.equity` boots at `capital_cfg["initial_capital"]` and accumulates exchange-confirmed PnL:
- Backtest: `initial_capital - fees + cumulative net PnL`, updated as each trade closes.
- Live: re-injected from `LiveState.real_equity` between ticks (deploy-cumulative). Does NOT change inside the bar loop — don't compute intra-bar PnL from `engine.equity` deltas; use `engine.persist` to anchor an entry-equity if needed.

```python
initial = capital_cfg.get("initial_capital", 10000)
if engine.equity < initial * 0.97:    # stop entries below 97% of starting capital
    continue
```

### 9.3. Custom inter-bar state via `engine.custom`

`engine.custom` is a free dict. Use it for any state the engine doesn't already track (cooldowns, custom counters, flags). In live the dict is preserved across ticks via shallow copy — references to objects (talipp instances, lists, dicts) survive intact.

```python
cooldown = engine.custom.get("cooldown_bars", 0)
if cooldown > 0:
    engine.custom["cooldown_bars"] = cooldown - 1
    continue
```

⚠ Do not reuse the reserved key names `consecutive_losses` / `consecutive_wins` for custom counters — overwrites get clobbered (in backtest by `_complete_trade`, in live by the per-tick sync).

### 9.4. How `engine.custom` works in live trading

In live, the engine is created fresh each tick and replays the sliding window. However, `engine.custom` is **persisted by the live motor between ticks** — the motor injects the previous tick's `engine.custom` before calling the strategy, and saves it after.

For talipp objects accessed via `engine.persist`, this means the SAME object accumulates `add()`/`update()` calls across ticks. This is the entire reason `engine.persist` exists — it gives path-dependent indicators continuity.

For `consecutive_losses` / `consecutive_wins`, the live motor injects the REAL deploy-cumulative values BEFORE every tick (overriding whatever the bar loop replay would have computed).

---

## 10. Mandatory Bar-Loop Template

**Available primary data columns**:
- **Always present, no NaN values per row**: `time` (or `open_time`), `open`, `high`, `low`, `close`. Rows missing any of OHLC are dropped upstream by the dataset loader.
- **Always present as a column, but values may be NaN**: `volume`. If the source exchange doesn't report it for a given bar, the cell is NaN. If the strategy uses volume in arithmetic, guard with `np.nan_to_num(volume_arr, nan=0.0)` or filter NaN rows.
- **Advanced (Order Flow) — column may be absent entirely, exchange-dependent**: `quote_asset_volume`, `number_of_trades`, `taker_buy_base`, `taker_buy_quote`. Always guard column existence before reading: `if "quote_asset_volume" in data.columns: ...`. Values within may also be NaN.
- **Auxiliaries** (`data_aux[<slot>]`): same shape as primary — `time`/`open_time`, OHLC always present and non-NaN per row; `volume` column always present but values may be NaN; Order Flow columns may be absent. Use the same time-column name as the primary dataset.

```python
o = data["open"].values
h = data["high"].values
l = data["low"].values
c = data["close"].values
tms = (data["time"] if "time" in data.columns else data["open_time"]).values
n = len(data)

for i in range(1, n):

    # STEP 0: Feed bar to engine (checks TP/SL, updates MFE/MAE, may auto-close)
    engine.on_bar(
        bar=(float(o[i]), float(h[i]), float(l[i]), float(c[i])),
        time=int(tms[i]),
    )

    # STEP 1: Risk gates (reserved-key reads; works uniformly in backtest and live)
    if engine.custom.get("consecutive_losses", 0) >= max_cl:
        continue

    # STEP 2: Signal-based exits (signal from bar i-1, execute at open of bar i)
    if engine.is_long and exit_long_signal[i-1]:
        engine.close(signal="EXIT_LONG_SIGNAL")
    elif engine.is_short and exit_short_signal[i-1]:
        engine.close(signal="EXIT_SHORT_SIGNAL")

    # STEP 3 (optional): Pyramid / partial-close logic (see Section 11)
    # If the strategy multi-legs:
    #   - re-check engine.is_long / is_short after every set_exit call
    #   - use engine.close(size=...) for partials (full close: omit size)

    # STEP 4: Auxiliary alignment (only if auxiliaries are used)
    macro_idx = int(np.searchsorted(aux2_times, tms[i], side="right")) - 1
    macro_bullish = (macro_idx >= 0) and (aux2_close[macro_idx] > aux2_ema[macro_idx])

    # STEP 5: Entry signals (signal from bar i-1, only when flat)
    if buy_signal[i-1] and engine.is_flat and macro_bullish:
        engine.buy(signal="BUY_SIGNAL")
        engine.set_exit(
            tp=engine.avg_cost * (1 + tp_pct),
            sl=engine.avg_cost * (1 - sl_pct),
        )
        # NOTE: set_exit may auto-close intra-bar — see §7.5
    elif sell_signal[i-1] and engine.is_flat and (not macro_bullish):
        engine.sell(signal="SELL_SIGNAL")
        engine.set_exit(
            tp=engine.avg_cost * (1 - tp_pct),
            sl=engine.avg_cost * (1 + sl_pct),
        )
```

**Order of operations per bar:**
1. `engine.on_bar()` — feeds OHLC, auto-checks TP/SL (may auto-close position).
2. Risk gates — short-circuit entries when conditions are met (TP/SL of open trade still fire via `on_bar`).
3. Signal exits — strategy checks its own exit conditions.
4. Pyramid / partial-close logic (if applicable).
5. Auxiliary alignment — derive any aux-based flags via `searchsorted`.
6. Signal entries — strategy opens new positions when flat.

> TP/SL is checked INSIDE `on_bar()` AND inside `set_exit()` (intra-bar hook), with priority over signal exits. This is intentional — TP/SL represents hard limits.

---

## 11. Pyramiding & Partial Closes

MSF natively supports multi-leg trades:
- Multiple `engine.buy()` while long add legs (avg_cost recomputed as weighted average).
- `engine.close(size=X)` with `X < qty` is a partial close (position remains open with reduced qty).

The trade adapter automatically tags each fill in the event stream:
- Initial entry: `is_pyramid: False`, `leg_index: 0`.
- Pyramid leg: `is_pyramid: True`, `leg_index: 1, 2, ...`.
- Partial close: `is_partial_close: True`, `is_final_close: False`.
- Final close (qty → 0): `is_final_close: True` with aggregated `profit` for the round-trip.

Each fill becomes its own row in the order book and its own marker in the chart, preserving the operational reality of the trade.

### 11.1. Pyramid pattern

```python
if engine.is_long and n_buy_fills == 1:
    move_pct = (curr_price - engine.avg_cost) / engine.avg_cost
    if move_pct >= pyr_threshold_pct:
        pyramid_size = engine._fills[0]["size"] * pyr_leg_size_pct
        engine.buy(size=pyramid_size, signal="PYRAMID_BUY")
        engine.set_exit(sl=engine.avg_cost * (1 - sl_pct))
        # set_exit may auto-close intra-bar → re-check engine.is_long below
```

### 11.2. Partial close pattern

**Critical**: do NOT set `tp` in `engine.set_exit` if you want to do a partial close at that level. The engine's TP fires a FULL close, not partial. Set ONLY `sl` initially, detect TP1 manually, do `engine.close(size=qty/2)`, THEN set `tp=tp2` for the engine to auto-close the remainder at tp2.

```python
# After pyramid + set_exit(sl=...) above, re-check:
if engine.is_long and n_close_fills == 0 and h[i-1] >= engine.avg_cost * (1 + tp1_pct):
    engine.close(size=engine.qty * 0.5, signal="PARTIAL_TP1")
    # Now set TP=tp2 for the engine to auto-close the remaining qty.
    engine.set_exit(
        tp=engine.avg_cost * (1 + tp2_pct),
        sl=engine.avg_cost * (1 - sl_pct),
    )
```

### 11.3. Counting fills via `engine._fills` (acceptable)

The strategy can read `engine._fills` to count entries / closes within the current trade:

```python
n_buy_fills   = len([f for f in engine._fills if f["type"] == "buy"])
n_close_fills = len([f for f in engine._fills if f["type"] == "close"])
```

`_fills` resets when `_complete_trade` fires (position fully closed). It contains `{type, time, price, size, signal, fee, slippage}` for each fill of the current open trade.

---

## 12. Flip Position Pattern

To reverse direction, close first then open:

```python
if buy_signal[i-1]:
    if engine.is_short:
        engine.close(signal="Close Short")
    if engine.is_flat:
        engine.buy(signal="BUY")
        engine.set_exit(tp=..., sl=...)
```

> **NEVER** call `engine.buy()` while short or `engine.sell()` while long. This raises `EngineError`. Use pyramid (`engine.buy()` while long) only when ADDING to the same direction.

---

## 13. Auto-Detection

The runtime auto-detects an MSF strategy by checking that the **5th parameter** is named `"engine"`:

```python
sig = inspect.signature(fn)
params_list = list(sig.parameters.keys())
is_msf = len(params_list) >= 5 and params_list[4] == "engine"
```

Code validator additionally enforces:
- talipp imports allowed only at module level (top of file).
- talipp constructors **prohibited** at module level — must be instantiated inside `trading_strategy()` via `engine.persist`.
- Otherwise, the module-level talipp instance would be cached across optimizer trials, contaminating internal state.


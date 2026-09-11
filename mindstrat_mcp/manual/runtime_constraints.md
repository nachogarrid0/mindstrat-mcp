# Runtime Constraints & Prohibitions
> These are HARD RULES. Violating them will cause the strategy generation or execution to FAIL.

## 1. Strictly Prohibited Code Patterns

### NO Markdown in `strategy_code`
The `strategy_code` field in the JSON response must contain **PURE PYTHON CODE**.
- **FORBIDDEN**: Wrapping code in backticks (e.g., ` ```python ... ``` `).
- **FORBIDDEN**: Wrapping code in triple quotes (e.g., `""" ... """`).
- **CORRECT**: Return the raw stringified Python code directly.

### NO Placeholders
The AI must generate **COMPLETE, EXECUTABLE CODE**.
- **FORBIDDEN**: Using `...`, `pass`, `# implementation here`, or `# imports here`.
- **FORBIDDEN**: Leaving `strategy_parameters` empty or incomplete.
- **REQUIRED**: Every function and variable must be fully defined.

### NO Interactive Functions
The strategy runs in a headless backend.
- **FORBIDDEN**: `input()`, `print()` (use `engine.custom` dict for debug state).
- **FORBIDDEN**: `plt.show()`, `fig.show()` (charts rendered by frontend using returned data).

---

## 2. Structural Constraints

### Global Scope
- `strategy_parameters`, `strategy_options`, `auxiliary_datasets`, and `warmup_spec` **MUST** be defined at the **MODULE LEVEL** (top of file).
- **DO NOT** define them inside `trading_strategy` or any other function.
- Capital configuration arrives via the `capital_cfg` argument of `trading_strategy(...)` — it is injected by the runtime, not declared at module level.

### Imports
- **REQUIRED**: `import pandas_ta as ta`.
- **ALLOWED (always)**: `pandas`, `numpy`, `math`, `datetime`, `typing`.
- **ALLOWED (only when used)**: `talipp`, `talipp.indicators`, `talipp.indicators.<Name>` (e.g. `talipp.indicators.SuperTrend`), `talipp.ohlcv`.
- **PROHIBITED**: `sklearn`, `tensorflow`, `torch`, `ccxt`, `requests` (unless explicitly requested and verified as installed).

### Parameter Naming
- **DO NOT** use generic keys like `"source"` if multiple indicators are used.
- **USE**: `"rsi_source"`, `"ma_source"`, `"atr_source"`.
- **MATCH**: The key in `strategy_parameters` **MUST MATCH** the key in `strategy_options`.

### auxiliary_datasets
- **REQUIRED**: declare `auxiliary_datasets: Dict[str, str]` at module level. Use `{}` if the strategy needs none.
- **FORBIDDEN**: hardcoding symbols or timeframes inside the strategy. The user picks the data via the UI; the strategy operates on whatever the runtime injects.
- **REQUIRED**: keys in `warmup_spec["auxiliary"]` must be a subset of the keys declared in `auxiliary_datasets`.

---

## 3. Data & Execution

### NaN Handling
- Indicators (like RSI, SMA) introduce `NaN` values at the start of the DataFrame.
- talipp output_values may contain `None` during warmup (handle via the padding pattern + `np.nan` substitution — see Section 5).
- **REQUIREMENT**: logic must handle `NaN` safely (e.g., `np.nan_to_num`, or skipping initial bars).
- **Standard**: Loop starts at `range(1, len(data))`. Code must handle NaN on its own: `warmup_spec` is live-only metadata and the backtest never reads it, so nothing trims the leading bars for you.

### Array Lengths
- When creating boolean masks (e.g., `buy_sig = ...`), the result may be shorter.
- **CRITICAL**: If logic requires `arr[i-1]`, ensure `i >= 1`.
- **CRITICAL**: `pandas_ta` returns Series with same index as input. Converting to numpy (`.values`) keeps the length.
- **CRITICAL**: every series in `visualization_data` must have the same length as the primary `data` DataFrame. Auxiliary-derived overlays must be projected onto the primary timeline (via `searchsorted`) before being returned.
- **CRITICAL**: talipp arrays MUST go through the padding pattern (Section 5.3) — they don't naturally have length `n`.

### Function Signature
- `trading_strategy` **MUST** accept exactly five parameters in this order: `data, data_aux, params, capital_cfg, engine`.
- The 5th parameter **MUST** be named `engine`. The runtime auto-detects an MSF strategy by inspecting parameter names.
- **WRONG signatures** (these will be rejected):
  - `def trading_strategy(data, params, capital_cfg, engine)` — only 4 params; rejected (5 required, `data_aux` is the 2nd).
  - `def trading_strategy(data, data_aux, params, capital_cfg, eng)` — 5th param must be named exactly `engine`.

### Return Type
- `trading_strategy` **MUST** return a single `Dict[str, Any]` — the `visualization_data`.
- **NOT** a tuple. **NOT** a list of trades. **NOT** a state dict.
- Returning anything else will crash the runner.

---

## 4. Engine Constraints

### on_bar() is MANDATORY
- `engine.on_bar(bar=(o, h, l, c), time=t)` **MUST** be called before any buy/sell/close on each bar.
- Calling buy/sell/close without a prior `on_bar()` raises `EngineError("on_bar() must be called before any action.")`.
- It must be the **FIRST** engine call of every loop iteration, **unconditionally**. Do NOT gate it behind an `if` (e.g. `if hasattr(engine, "on_bar"):`) or place any `buy/sell/close` before it — a branch that skips `on_bar` raises at the next action.

### NO manual profit calculation
- **FORBIDDEN**: `profit = (fill - entry) * size` — the engine calculates PnL.
- **FORBIDDEN**: `trades.append({...})` — the engine records fills internally.
- **FORBIDDEN**: Building a trades list — the runtime extracts trades from the engine.

### NO manual position tracking
- **FORBIDDEN**: `position = "long"` / `position = None` — use `engine.buy()` / `engine.close()`.
- **FORBIDDEN**: `size = order_val / price` — the engine auto-sizes from `capital_cfg`.
- **USE**: `engine.is_flat`, `engine.is_long`, `engine.is_short` for position checks.

### NO manual state management (use `engine.persist` and `engine.custom`)
- **FORBIDDEN**: `state = {"position_side": ...}` — the engine manages all state.
- **FORBIDDEN**: Reading or writing a `state` argument — does not exist.
- **USE**: `engine.persist(key, factory)` for state that should survive across live ticks (talipp objects, custom counters, trackers). The same instance is returned across ticks in live; fresh per call in backtest.
- **USE**: `engine.custom[key]` directly for ad-hoc reads/writes (it's the underlying dict that `persist` manages).

### Reserved keys in `engine.custom`
- `engine.custom["consecutive_losses"]` and `engine.custom["consecutive_wins"]` are **framework-managed reserved keys**. The strategy READS them for risk gates; **NEVER WRITES**. Canonical streak-sizing pattern (backtest field vs live custom key): `msf_canon §6` ("Sizing by losing/winning streak").
- In backtest they reflect `_complete_trade` outcomes (replay-based).
- In live they reflect REAL exchange closures (deploy-cumulative; injected by the live motor before each tick).
- Writing to them is silently overwritten (in backtest by `_complete_trade` on next close, in live by the per-tick sync). Don't rely on writes.

### Direction changes require explicit close
- **FORBIDDEN**: `engine.buy()` while short — raises `EngineError`. Close first.
- **FORBIDDEN**: `engine.sell()` while long — raises `EngineError`. Close first.
- **ALLOWED**: `engine.buy()` while long — pyramids (adds a leg). Same for `engine.sell()` while short.

### The two channels (THE parity rule)
MSF has exactly two places code runs, with different time resolution:
- **Channel 1 — the engine (`engine.set_exit(...)`):** the ONLY place with intra-bar precision. "Price touches a level *inside* the bar" events — TP, SL, trailing — go here. Live resolves them on every tick. Backtest replays each chart bar at a finer timeframe (mapped, NOT 1m — 1h→15m, 4h→1h, 1d→4h; only 1m/3m/5m replay at 1m), and that replay is **off by default**: with it off, a bar whose range spans both the TP and the SL is booked worst-case-first — as the stop. The level is identical in both engines; the resolution of a tie is not. See `msf_canon §7.9`.
- **Channel 2 — the strategy's `for i in range(1, n)` loop:** chart-bar granularity, NO intrabar. Every decision the strategy makes itself uses the **CLOSED bar `[i-1]`**.

**The hard rule:** NEVER read the current bar's high/low/close (`h[i]`/`l[i]`/`c[i]`) for a decision, level, or exit. In backtest `[i]` is the bar's full (eventual) high/low — look-ahead; in live it's the forming bar per-tick → the two diverge. The only safe current-bar reads are `o[i]` (open = the fill price, `engine._bar[0]`) and `engine.avg_cost`. Current-bar `h[i]/l[i]/c[i]` are legal ONLY inside a feed (`engine.on_bar(...)`, `OHLCV(...)`). Generalizes beyond trailing: anchoring (`entry=c[i]`), manual TP/SL, manual partial — all the same bug.

### TP/SL are engine-managed (with intra-bar hook)
- **FORBIDDEN**: manual `if c[i] > tp` / `if l[i] <= sl` checks inside the bar loop FOR FULL-CLOSE TP/SL. The engine evaluates TP/SL via `on_bar()` and via the `set_exit()` intra-bar hook.
- **ALLOWED EXCEPTION**: manual partial-close detection on the **CLOSED bar** — `if h[i-1] >= avg_cost * (1+tp1_pct)` (the engine's TP fires a FULL close, not partial — manual detection is the only way for partials). Use `[i-1]`, **NEVER** the current bar `h[i]` (that's the forming bar → look-ahead).
- **USE**: `engine.set_exit(tp=..., sl=..., trailing=...)` to configure levels.
- TP/SL/trailing reset automatically when the position goes flat.
- TP/SL has priority over signal exits (checked first inside `on_bar` and inside `set_exit`).

### `set_exit` intra-bar hook (CRITICAL)
- `engine.set_exit(tp/sl/trailing)` immediately fires `_check_tp_sl` against the current bar's H/L. If the bar already crossed the level, the engine **auto-closes the position inside `set_exit`**.
- **REQUIRED**: any engine action AFTER a `set_exit` must re-check `engine.is_long` / `engine.is_short`. Otherwise `EngineError("Cannot close: no open position.")` will fire when you try to act on the (now flat) position.

### Entry/exit level anchoring (no intra-bar look-ahead)
- **FORBIDDEN**: anchoring TP/SL/trailing to the current bar's `c[i]` / `h[i]` / `l[i]`, or to a precomputed `entry = c[i]`. In live the bar is still forming when the loop acts — `c[i]` does not exist yet; in backtest it is the bar's known final close → silent look-ahead that diverges live.
- **REQUIRED**: anchor every TP/SL/trailing level to `engine.avg_cost` (read AFTER `buy()`/`sell()`). Gate entry/exit conditions on `[i-1]` (closed-bar) values, never `[i]`. See `msf_canon §7.7`.

### Manual trailing/exits are PROHIBITED — use `engine.set_exit`
- **FORBIDDEN**: a hand-rolled trailing/stop that ratchets a peak and exits off the current bar's OHLC, e.g. `peak = max(peak, h[i]); if c[i] <= peak * (1 - trail): engine.close(...)`. Backtest evaluates it once per chart bar; live re-runs the loop per tick → they diverge. It also **bypasses the intrabar replay** (only `set_exit` exits go through `_check_tp_sl`), so intrabar simulation has no effect on it.
- **REQUIRED**: `engine.set_exit(trailing=engine.avg_cost * trail_pct)` (or `tp=`/`sl=`). The engine handles trailing per tick in live and via intrabar replay in backtest → 1:1. See `msf_canon §7.7`.

### Engine API surface — allowlist & non-existent attributes
- `buy`/`sell`/`close` accept **only** `price`, `size`, `signal`. A `size_fraction`/`fraction`/`pct` kwarg raises `TypeError` — size down with `engine.buy(size=base*frac)`.
- **DOES NOT EXIST** (do not invent): `engine.closed_trades`, `engine.closed_trades_count`, `engine.n_trades` → use `engine.get_trades()`, and only to report — it is **backtest-only** (in live the completed-trade list is emptied every tick, so any gate that counts past trades never fires). Count closures into `engine.persist`, or read `engine.custom["consecutive_losses"] / ["consecutive_wins"]`; `trade["pnl_pct"]` → `trade["pnl"]`; `fill["side"]` → `fill["type"]`. Hallucinated attributes read via `getattr(..., default)` fail **silently** (the feature dies without error) — see `msf_canon §6` for the full schema + denylist.

### Price validation
- If `price` is specified in buy/sell/close, it must be within the bar's `[low, high]` range.
- If `price` is omitted (`None`), the bar's open price is used.

---

## 5. Talipp Constraints

### Module-level instantiation is FORBIDDEN
- **PROHIBITED**: `_GLOBAL_ST = SuperTrend(atr_period=14, mult=3.0)` at module scope. The code validator rejects this.
- **REQUIRED**: instantiate every talipp object inside `trading_strategy()` via `engine.persist`:
  ```python
  st = engine.persist("st_obj", factory=lambda: SuperTrend(atr_period=14, mult=3.0))
  ```
- **Why**: the optimizer caches the strategy module across trials. A module-level talipp instance would carry state from previous trials, silently corrupting backtest results.
- **PROHIBITED**: dict comprehensions or loops at module level that build talipp instances. Same reason.
- **ALLOWED at module level**: `from talipp.indicators import SuperTrend` (import), `class MyST(SuperTrend): pass` (subclass), `def make_st(...): return SuperTrend(...)` (factory function — not called at module level).

### State tracking dict
- **REQUIRED**: pair every persisted talipp object with a state dict that tracks `last_t` for the add+update pattern:
  ```python
  st = engine.persist("st_obj", factory=lambda: SuperTrend(...))
  st_state = engine.persist("st_state", factory=lambda: {"last_t": -1})
  ```

### `add()` vs `update()` semantics — CLOSED-BARS-ONLY rule
- `add(value)`: appends a permanent value to talipp. Output_values grows by 1. Use for **closed bars** ONLY.
- `update(value)`: replaces the last appended value. **PROHIBITED on the forming bar in live trading** — it corrupts path-dependent state (see §11 Forming-bar quarantine below). Reserved for niche use cases where the same closed bar's final OHLC needs correction (e.g., late kline event with revised final value).
- **PROHIBITED anti-shape** (caused a live-divergence bug): feeding closed bars with `add()` and then calling `update(forming_bar)` to "include" the still-forming bar. This pushes the partial, per-tick OHLC of the forming bar into a path-dependent indicator (e.g. VWAP's cumulative sum, SuperTrend bands) → diverges live. The forming bar gets a `None` slot in the output array (`raw.append(None)`), and **never** an `add()` or `update()`.
- `remove()`: undoes the last `add()`. Rarely needed.
- **PROHIBITED**: calling `add()` for the same closed bar more than once. Causes duplicate state.
- **PROHIBITED**: calling `update()` before any `add()`. Raises an error in talipp.
- **PROHIBITED**: feeding the forming bar (last row of `data` in live) via either `add()` OR `update()`. The strategy must iterate up to `n_closed = n - 1`, never to `n`. See §11.

### `output_values` length aligned with `n_closed`, NOT `n`
- talipp's `Indicator.add()` always appends one entry to `output_values` (the entry is `None` during warmup until enough history is in; once warmed up, it's the computed value). So at the talipp level `len(output_values) == len(input_values)`.
- Since the strategy only feeds closed bars (§11), `len(output_values) == n_closed`. The mismatch with the `n` primary bars is **+1** (the forming bar at index `n-1` is intentionally excluded from the indicator).
- Across many live ticks `output_values` accumulates via `engine.persist` and may grow past `n_closed`. The strategy must slice the latest `n_closed` entries and append a `None` for the forming bar slot:
  ```python
  raw = list(st.output_values)
  if len(raw) < n_closed:
      raw = [None] * (n_closed - len(raw)) + raw    # pad start
  else:
      raw = raw[-n_closed:]                          # slice end
  raw.append(None)                                   # forming bar — indicator undefined
  # raw now has length n; trend[n-1] / value[n-1] become NaN.
  ```
- **PROHIBITED**: `raw = list(st.output_values)[-n:]` (no padding, no forming-bar slot). Passes backtest, breaks live OR contaminates signals.

### Window-slid guard
- In live, if the rolling window slides past `last_t` (rare anomaly: container paused, WS gap, multi-bar recovery), the talipp object has stale internal state. The strategy should detect and reset using closed-bar slicing:
  ```python
  if last_t > 0:
      new_idx_check = int(np.searchsorted(tms[:n_closed], last_t, side="right"))
      if new_idx_check == 0:
          # last_t fell out of the window → reset the talipp object
          engine.custom.pop("st_obj", None)
          engine.custom.pop("st_state", None)
          st = engine.persist("st_obj", factory=lambda: SuperTrend(...))
          st_state = engine.persist("st_state", factory=lambda: {"last_t": -1})
          last_t = -1
  ```
- This is canonical defensive code; see the strategy template in the vector store (`Code_Template`) for the full integrated pattern.

### Warmup of talipp Wilder-based indicators
- talipp indicators that use Wilder smoothing (SuperTrend's ATR, talipp RSI, etc.) participate in `warmup_spec["wilder_lengths"]` the same way as their pandas-ta equivalents. The LIVE motor sizes its sliding window from this; the backtest ignores `warmup_spec` entirely and passes the full dataset.
  ```python
  warmup_spec = {
      "simple_windows": [],
      "wilder_lengths": ["atr_period"],  # covers BOTH pandas-ta ATR AND talipp SuperTrend ATR
      "epsilon": 0.001,
  }
  ```

---

## 6. Optimizer-Safe Code

### FORBIDDEN: mutating the input `data` DataFrame
- **PROHIBITED**: `data["RSI"] = ta.rsi(...)`, `data["EMA"] = ...`, or any `data[<column>] = <value>` assignment.
- **Why**: the optimizer reuses the same `data` DataFrame — backed by `multiprocessing.shared_memory` — across every trial inside a worker. Assigning a new column forces pandas to reallocate the BlockManager out of the shared buffer; multiplied by N workers and M trials → RAM exhaustion before the first cycle completes. The strategy works in the strategy creator (which `.copy()`s `data` per run) and silently dies in the optimizer.
- **REQUIRED**: compute every indicator into a LOCAL numpy array via `.to_numpy()`:
  ```python
  rsi_arr = ta.rsi(data["close"], length=rsi_len).to_numpy()
  atr_arr = ta.atr(data["high"], data["low"], data["close"], length=atr_len).to_numpy()
  adx_df  = ta.adx(data["high"], data["low"], data["close"], length=adx_len)
  adx_col = next(c for c in adx_df.columns if c.startswith("ADX_"))
  adx_arr = adx_df[adx_col].to_numpy()
  ```
- **ALLOWED**: reading OHLCV via `.values` (read-only view, free). Only the write path is forbidden:
  ```python
  o = data["open"].values          # OK — read-only view of shared buffer
  h = data["high"].values          # OK
  ```
- This rule mirrors the talipp-module-level prohibition (§5): anything that pollutes shared state across trials is rejected.

---

## 7. Auxiliary Datasets

### Read-only
- **FORBIDDEN**: modifying any DataFrame in `data_aux`.
- **FORBIDDEN**: merging / joining / reindexing auxiliaries with the primary `data`. That alters primary length and breaks visualization.

### No look-ahead
- **REQUIRED**: align auxiliaries via `idx = np.searchsorted(aux_times, tms[i], side="right") - 1`.
- **FORBIDDEN**: `side="left"`, or omitting the `-1`. Both can leak future information.
- **REQUIRED**: handle `idx < 0` (no auxiliary data yet at the start of the period).
- **FORBIDDEN**: interpolating between auxiliary bars. Use point-in-time values as-is.

### Essential auxiliaries must fail-explicit
If an auxiliary is essential to the strategy's logic:
```python
if "<key>" not in data_aux or data_aux["<key>"].empty:
    raise ValueError("This strategy requires <key>. Select an auxiliary dataset in the UI.")
```
- **FORBIDDEN**: silently changing strategy logic when an essential auxiliary is missing.

### Vectorize auxiliary indicators pre-loop
- **REQUIRED**: compute auxiliary pandas-ta indicators on the auxiliary DataFrame **before** the bar loop.
- **REQUIRED**: extract resulting NumPy arrays (`.values`) before the loop.
- **FORBIDDEN**: calling pandas_ta or pandas operations on auxiliaries inside the loop — orders of magnitude slower than NumPy indexing.
- talipp objects can be applied to auxiliaries — same `engine.persist` + add+update pattern, with the auxiliary's `open_time` array for tracking instead of `tms`.

---

## 8. Pandas-TA Output Handling

- **REQUIRED**: Always convert result to DataFrame: `df = res.to_frame() if isinstance(res, pd.Series) else res`.
- **REQUIRED**: Select multi-column outputs by position `.iloc[:, 0]` or by **prefix** (`next(c for c in df.columns if c.startswith("ADX_"))`), **NEVER** by full hardcoded column names. Names include the parameter and change when the user re-tunes.

---

## 9. Library Decision Rule (CRITICAL)

For each indicator the strategy uses, decide which engine handles it. Picking the wrong one is the most common source of strategies that pass backtest and break in live.

### pandas-ta inline (convergent indicators)
Use when the indicator value at bar `t` is determined by a fixed window of past data, with no path dependency on bars BEFORE the window:

**RSI, ATR, ADX/DMI, MACD, Bollinger Bands, SMA, EMA, WMA, DEMA, TEMA, HMA, ALMA, VWMA, Stochastic, ROC, Momentum, CCI, Williams %R, MFI, Awesome Oscillator, Pivot Points (classic).**

### talipp + `engine.persist` (path-dependent indicators)
Use when the indicator value at bar `t` depends on the entire history since session/series start. Sliding windows would corrupt these:

**SuperTrend, ParabolicSAR, OBV, Accumulation/Distribution, Chaikin Oscillator, session VWAP, Heikin-Ashi, Renko, ZigZag, Ichimoku Senkou Span/Cloud.**

### Default error
The most common mistake is using pandas-ta vectorized for path-dependent indicators (e.g., a hand-rolled SuperTrend in NumPy). The strategy will pass backtest (single-shot, full history) but **break in live** (sliding window resets state every tick). Always confirm via `search_msf_spec` or `search_talipp_reference` when unsure.

---

## 10. Commission & Slippage Model

Commissions and slippage are configured in `capital_cfg` (injected by the runtime) and applied automatically by the engine:

```python
capital_cfg = {
    "commission": 0.1,            # Commission value
    "commission_type": "percent", # "percent" or "fixed"
    "slippage_mode": "none",      # "none" | "fixed" | "volume" | "random"
    "slippage_bps": 0.0,
    "slippage_k": 1.0,
}
```

- **percent**: `fee = price * size * (commission / 100)` per fill.
- **fixed**: `fee = commission` per fill (flat rate).
- **slippage**: applied adversely on every fill (buy/close-short pay up, sell/close-long pay down). May push the fill outside `[low, high]` — this is realistic. TP/SL auto-closes also receive slippage.
- Fees and slippage are applied automatically. The strategy does NOT calculate or track them.

---

## 11. Forming-bar quarantine for path-dependent indicators (CRITICAL)

This is the rule that decides whether a strategy is bit-perfect 1:1 with the backtest in live, or drifts by a few flips per day. Violating it is the most common cause of "passes backtest, behaves slightly off in live" for strategies that use path-dependent indicators (SuperTrend, ParabolicSAR, OBV, Ichimoku, KAMA, etc.).

### The rule

> **Indicators with `engine.persist` NEVER receive the forming bar.** The strategy iterates indicator feeding up to `n_closed = n - 1`, NEVER up to `n`. The last row of `data` is the forming bar (live: in-progress aggTrades; backtest: emulated final OHLC); regardless, it is ALWAYS quarantined from any path-dependent indicator.

### Why

In live, the strategy is re-invoked on EVERY aggTrade tick. The last row of `data` (`data.iloc[n-1]`) is the **forming bar** whose H/L/C change with every tick. If the strategy calls `st.update(forming_bar_OHLC)` on every tick:

- Tick at 14:00:00 — H=0.2230, L=0.2228, C=0.2229 → SuperTrend state computed with these partial values.
- Tick at 14:00:42 — H=0.2235, L=0.2228, C=0.2233 → SuperTrend state computed again with new partial values.
- Tick at 14:59:58 — H=0.2237, L=0.2224, C=0.2228 → final partial values.
- Bar 14:00 officially closes at 15:00:00 with the same OHLC as the last tick.

The closed-bar OHLC matches, but the path-dependent internal state (final_upper/final_lower bands for SuperTrend, Wilder smoothed ATR, KAMA's efficiency ratio, etc.) accumulated through ~3600 intermediate `update()` calls. The talipp `update()` documentation promises idempotency over the LAST input_value, but most path-dependent indicators have internal state that DOES drift across many partial-OHLC updates. The result: SuperTrend `trend[bar_t]` in live is occasionally `DOWN` while the backtest computed `UP` (or vice versa) — flipping a `flip_up` / `flip_down` signal and producing an extra trade or skipping a trade.

In backtest the same `trading_strategy()` runs ONCE per backtest. There is no per-tick re-execution. The closed-bar OHLC is fed directly. No drift.

### The correct pattern

```python
n = len(data)
n_closed = n - 1   # exclude the forming bar (always at index n-1)

# Feed talipp with CLOSED bars only.
last_t = st_state["last_t"]
if last_t < 0:
    for i in range(n_closed):                # NOT range(n)
        st.add(OHLCV(float(o[i]), float(h[i]), float(l[i]), float(c[i])))
    if n_closed > 0:
        st_state["last_t"] = int(tms[n_closed - 1])
else:
    new_idx = int(np.searchsorted(tms[:n_closed], last_t, side="right"))
    if new_idx < n_closed:
        for i in range(new_idx, n_closed):
            st.add(OHLCV(float(o[i]), float(h[i]), float(l[i]), float(c[i])))
        st_state["last_t"] = int(tms[n_closed - 1])
    # else: no new closed bars — no-op. Forming bar is NEVER fed.

# Build the trend / value arrays with length n (forming-bar slot = None).
raw = list(st.output_values)            # length = n_closed
if len(raw) < n_closed:
    raw = [None] * (n_closed - len(raw)) + raw
else:
    raw = raw[-n_closed:]
raw.append(None)                         # forming bar: indicator undefined
trend = np.array([
    (1.0 if v.trend == Trend.UP else -1.0) if v is not None else np.nan
    for v in raw
], dtype=np.float64)
```

### Why this still reacts intra-bar to TP/SL/trailing

The forming-bar quarantine is ONLY for path-dependent indicators that feed signals. TP/SL/trailing reactivity is unchanged because:
- `engine.on_bar(bar=(o,h,l,c), time=t)` in the bar loop sets `engine._bar` directly to the forming bar's current OHLC.
- `engine.set_exit(...)` and the internal `_check_tp_sl` evaluate H/L of `engine._bar` against the configured tp/sl/trailing — these run intra-bar in live (sub-50ms reaction per aggTrade) and intra-bar in backtest (via the OHLC simulation).
- Path-dependent indicators are USED to derive `buy_sig` / `sell_sig` at indices `[0..n_closed-1]`. The bar loop reads `buy_sig[i-1]` (PREVIOUS bar's signal), so when `i == n-1` (forming bar iteration), the signal is `buy_sig[n-2]` — a value computed from the previous CLOSED bar's final OHLC. That value is bit-perfect with backtest.

### Forbidden vs allowed

- ❌ `for i in range(n): st.add(...)` — feeds forming bar to indicator.
- ❌ `st.update(OHLCV(open=o[n-1], high=h[n-1], low=l[n-1], close=c[n-1]))` — updates with forming bar's partial OHLC.
- ❌ `raw = list(st.output_values)[-n:]` — assumes indicator has `n` outputs; expectation is `n_closed`.
- ✅ `for i in range(n_closed): st.add(...)` — feeds CLOSED bars only.
- ✅ `raw.append(None)` after slicing to `n_closed` — preserves length-`n` array shape with `NaN` at forming-bar slot.
- ✅ Convergent indicators via pandas-ta CAN be vectorized over the full `data["close"]` array (no path-dependent state to corrupt), but it's good practice to mask the last value to `NaN` for symmetry. Optional, not required.

### Which indicators are affected

Every indicator wrapped in `engine.persist`. From the curated catalog:

**MUST apply forming-bar quarantine** (path-dependent, via talipp + engine.persist):
SuperTrend, ParabolicSAR, OBV, AccuDist, ChaikinOsc, SOBV, ForceIndex, KVO, session VWAP, EMV, KAMA, McGinleyDynamic, ChandeKrollStop, PivotsHL, Ichimoku Senkou, ZigZag — and any DIY persisted indicator (Heikin-Ashi, Renko, custom hysteresis stops).

**Optional but recommended** (convergent, via pandas-ta inline):
RSI, ATR, ADX, MACD, BB, SMA/EMA, Stoch, etc. Convergent indicators don't carry corrupting state across `update()`, but the forming bar's value is still partial — mask the last element to `NaN` if the strategy reads it (it typically reads `arr[i-1]`, so the forming-bar value is unused anyway).

### Live-Readiness Audit dimension

The Live-Readiness Audit (system prompt) MUST verify, for every path-dependent indicator the strategy uses, that the feeding loop iterates over `n_closed`, not `n`. This is dimension **#2.5 (Forming-bar quarantine)**. A strategy that feeds the forming bar to a path-dependent indicator is **NOT live-ready ❌** — fix via `propose_strategy_edit`.

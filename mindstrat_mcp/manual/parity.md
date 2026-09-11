# Writing a strategy that behaves the same live as it did in the backtest

This is the one rule the whole format exists to protect. Read it before writing any code.

The same `trading_strategy()` function runs in **both** engines: in the backtest as a single pass over the full history, and in live as a sliding window re-executed on every tick inside the forming bar. The engine is built so that those two produce the same decisions. **Code that behaves differently across them is a bug, not a tradeoff** — and it is a bug the backtest cannot show you, because in the backtest the window never slides.

Nothing in the app checks this for you. The code validator enforces two things (no talipp at module level, no mutation of `data`) and nothing else. The audit at the end of this document is the whole safety net.

---

## The two channels

Parity rests on two execution channels with different time resolution.

**Channel 1 — the engine, through `engine.set_exit(tp/sl/trailing)`.** The only place with intra-bar precision. Anything of the form "price touches a level *inside* the bar" belongs here. The engine watches those levels continuously — per tick in live, and in the backtest by replaying each chart bar at a finer timeframe.

**Channel 2 — the strategy's own `for i in range(1, n)` loop.** Chart-bar granularity, no intra-bar view. Every decision the strategy makes itself reads the **closed bar `[i-1]`**.

> On a bar that touches the take-profit and the stop-loss both, the two engines resolve the tie differently unless intrabar simulation is on — and it is off by default. See `mindstrat://msf/canon` §7.9 and `mindstrat://settings`.

## The hard rule

> **Never read the current bar's `h[i]`, `l[i]` or `c[i]` for a decision, a level, or an exit.**

In the backtest `[i]` is the bar's finished high and low — that is the future, so it is look-ahead. In live it is the forming bar, changing on every tick. The two diverge by construction.

The only safe current-bar reads are `o[i]` (the open, which is the fill price) and `engine.avg_cost` (read after `buy()`/`sell()`). Current-bar `h[i]`/`l[i]`/`c[i]` are legal **only** inside a feed — `engine.on_bar(...)`, `OHLCV(...)`.

One rule covers the whole family: manual trailing stops, anchoring an entry to `c[i]`, hand-rolled take-profits, manual partial closes.

## Two corollaries

**Cross-bar state lives in `engine.persist`, never in a Python local.** In live the function is respawned on every tick: locals reset, `engine.persist` and `engine.custom` survive. Counters, flags, last-known values, cooldowns, talipp objects — all persisted, each guarded by a `last_t` **timestamp**, never an index, because indices shift as the window slides. The mental test: *respawned fifty times inside one bar, does it still hold?*

**Path-dependent indicators never receive the forming bar.** Feeding loops iterate to `n_closed = n - 1`, never `n`; the output is padded with a trailing `None` for the forming slot; decisions read `signal[i-1]`. Feeding partial forming OHLC per tick into path-dependent state drifts the flips by a bar.

---

## The library decision

The single most consequential mechanical choice, and the one that most often produces a strategy that backtests beautifully and breaks in production.

- **Convergent** indicators — value at bar `t` determined by a fixed window, with no dependency on the bars before it → **pandas-ta**, vectorised into a **local numpy array**. RSI, ATR, ADX, MACD, Bollinger, the moving averages, Stoch, ROC, CCI, MFI, Williams %R, and most oscillators.
- **Path-dependent** indicators — value depends on the entire history since the series started → **talipp + `engine.persist`**. SuperTrend, ParabolicSAR, OBV, AccuDist, ChaikinOsc, session VWAP, ZigZag, Ichimoku, KAMA, McGinleyDynamic.
- **Path-dependent but absent from talipp** — Heikin-Ashi, Renko, custom hysteresis stops → the DIY persist recipe, `mindstrat://msf/examples` Example 4.

**The classic trap** is implementing a path-dependent indicator with pandas-ta: `ta.supertrend()`, `ta.obv()`, `ta.psar()`, `ta.vwap()`. Each passes the backtest — one pass over full history, where the whole path is present — and silently breaks in live, where the sliding window resets the state on every tick.

**Do not decide this from memory.** Call `lookup_indicator(name)`: it returns the documented signature and the binding assignment, read from the catalogues themselves, and flags the trap when both libraries expose the same indicator.

---

## Hard constraints

- **Never mutate `data`.** `data["col"] = ...` is rejected by the validator. The optimizer shares one memory-backed DataFrame across trials; mutating it reallocates and exhausts RAM. Compute into a local array via `.to_numpy()`. Reading with `.values` is fine.
- **Forbidden anywhere**: `input()`, `print()`, `plt.show()`, `sklearn`, `tensorflow`, `torch`, `ccxt`, `requests`, `if __name__`, `while True`. Allowed: `pandas`, `numpy`, `pandas_ta`, `talipp`, `math`, `datetime`, `typing`.
- **Never instantiate talipp at module level** — the validator rejects it. Indicator objects are created inside `trading_strategy` through `engine.persist`.
- **No placeholders.** No `...`, no `pass`, no "imports here". Never leave `strategy_parameters` empty.
- **Never hardcode a symbol or timeframe.** The dataset slot is the contract.
- **Never read `engine.get_trades()` for a decision.** It is backtest-only: in live the completed-trade list is emptied on every tick, so any gate that counts past trades silently never fires. Count closures into `engine.persist`, or read `engine.custom["consecutive_wins"] / ["consecutive_losses"]`.
- **Declare every lookback in `warmup_spec`.** It is live-only metadata — the backtest ignores it and passes the whole dataset — so a wrong or incomplete spec is invisible until deploy, where it shows up as indicators that are all NaN.

---

## The Live-Readiness Audit

Run this after every backtest, before presenting the result. It answers one question only: *will live behave the same as the backtest?* It is decided on mechanical grounds. Never downgrade a verdict for poor performance, and never cite a performance metric as evidence — a money-losing strategy can be perfectly live-ready, and a profitable backtest built on a vectorised path-dependent indicator is not live-ready at all.

Walk every dimension and name every indicator explicitly. An audit done from impression rather than enumeration is not an audit.

| # | Dimension | ❌ when |
|---|---|---|
| 1 | **Library per indicator**, enumerated by name with its classification | any path-dependent indicator via pandas-ta or a hand-rolled numpy loop. `ta.obv/psar/supertrend/vwap` is automatic |
| 2 | **Persisted state** — every cross-bar value in `engine.persist` / `engine.custom` | any cross-bar state in a Python local. ⚠ if persisted without a `last_t` guard |
| 3 | **Forming-bar quarantine** (path-dependent only) | feeding `range(n)`, `update(forming)`, or a slice with no forming slot. Must be `n_closed = n - 1` and a trailing `None` |
| 4 | **`set_exit` safety** — called right after its `buy()`/`sell()` | a post-`set_exit` action that assumes the position is still open; the hook may have closed it |
| 5 | **Aux alignment** — `searchsorted(side="right") - 1`, `idx < 0` handled, warmup declared | a direct index, `side="left"`, or a missing `-1` |
| 6 | **Window-slide safety** — every persisted path-dependent indicator has both the `last_t` guard and the reset block | the reset block missing: a live window-slide then runs on stale state |
| 7 | **Look-ahead and anchoring** — conditions on `[i-1]`; take-profit, stop and trailing anchored to `engine.avg_cost` | any `c[i]`/`h[i]`/`l[i]` in a decision, a precomputed `entry=c[i]`, or hand-rolled trailing on the chart bar |
| 8 | **Engine API** — `on_bar()` first every iteration | a non-existent attribute or kwarg, `on_bar` not first, `f["side"]` instead of `f["type"]`, `trade["pnl_pct"]` (only `"pnl"` exists), or `get_trades()` used for a decision |

Any ❌ means the strategy is not ready: fix it and re-run.

Dimension 6 is the one most often skipped, and it fails **only in live** — never in the backtest, where the window never slides.

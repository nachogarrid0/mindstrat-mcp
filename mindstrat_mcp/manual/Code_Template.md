import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict, Any

# Talipp imports — required when using path-dependent indicators (here: SuperTrend).
# Omit these 3 lines if the strategy uses pandas-ta only.
from talipp.indicators import SuperTrend
from talipp.indicators.SuperTrend import Trend
from talipp.ohlcv import OHLCV


# ─── 1. PARAMETERS (user-tunable inputs) ───────────────────────────

strategy_parameters: Dict[str, Any] = {
    # pandas-ta convergent indicator
    "rsi_length":       14,
    "rsi_overbought":   70.0,
    "rsi_oversold":     30.0,
    # talipp path-dependent indicator (SuperTrend uses Wilder ATR internally)
    "atr_period":       14,
    "atr_multiplier":   3.0,
    # Auxiliary dataset filter (EMA on a higher-timeframe aux dataset)
    "macro_ema_period": 50,
    # Risk management
    "takeProfitPerc":   2.0,
    "stopLossPerc":     1.0,
}


# ─── 2. CATEGORICAL OPTIONS (dropdowns in UI) ───────────────────────

strategy_options: Dict[str, Any] = {
    # Empty {} when no categorical params.
    # Example: "source": ["open", "high", "low", "close", "hl2", "hlc3", "ohlc4"],
}


# ─── 3. AUXILIARY DATASETS (slot declarations) ──────────────────────
# Each key becomes a slot in the UI; the user picks the actual data.
# The strategy NEVER hardcodes symbols or timeframes — the slot is the contract.
# Use {} when the strategy is single-dataset.

auxiliary_datasets: Dict[str, str] = {
    "dataset_2": "Higher-timeframe trend filter (e.g. 4H of the same asset)",
}


# ─── 4. WARMUP SPEC (live-trading metadata) ─────────────────────────
# ONLY these 4 keys at top level — DO NOT invent new keys.
# Wilder-based talipp indicators (SuperTrend's ATR, talipp RSI) go in
# `wilder_lengths` the same as their pandas-ta counterparts.
# The `auxiliary` block mirrors the keys declared in `auxiliary_datasets`
# (one warmup sub-spec per slot). Use {} if no aux datasets.

warmup_spec: Dict[str, Any] = {
    "simple_windows": [],                              # param keys (SMA-like windows)
    "wilder_lengths": ["rsi_length", "atr_period"],    # covers pandas-ta RSI + SuperTrend's ATR
    "epsilon": 0.001,
    "auxiliary": {
        "dataset_2": {
            "simple_windows": ["macro_ema_period"],
            "wilder_lengths": [],
        },
    },
}


# ─── 5. MAIN FUNCTION (5 params; engine MUST be the 5th) ───────────

def trading_strategy(
    data: pd.DataFrame,
    data_aux: Dict[str, pd.DataFrame],
    params: Dict[str, Any],
    capital_cfg: Dict[str, Any],
    engine,
) -> Dict[str, Any]:

    # ── STEP 0: UNPACK PARAMETERS ──
    rsi_len   = int(params["rsi_length"])
    rsi_ob    = float(params["rsi_overbought"])
    rsi_os    = float(params["rsi_oversold"])
    atr_len   = int(params["atr_period"])
    atr_mult  = float(params["atr_multiplier"])
    macro_len = int(params["macro_ema_period"])
    tp_pct    = float(params["takeProfitPerc"]) / 100.0
    sl_pct    = float(params["stopLossPerc"])  / 100.0

    # ── STEP 0.1: VALIDATE ESSENTIAL AUXILIARIES (fail-explicit) ──
    # Raise ValueError with a clear message; the UI surfaces it to the user.
    # Never silently swap to a different logic when an essential aux is missing.
    if "dataset_2" not in data_aux or data_aux["dataset_2"].empty:
        raise ValueError(
            "This strategy requires dataset_2 (higher-timeframe trend filter). "
            "Select an auxiliary dataset in the UI."
        )

    # ── STEP 1: PANDAS-TA CONVERGENT INDICATORS (vectorized, pre-loop) ──
    # CRITICAL: NEVER assign indicator columns to `data` (e.g. `data["RSI"] = ...`).
    # The optimizer reuses the same `data` DataFrame (backed by shared_memory)
    # across every trial inside a worker. Assigning to `data[<col>]` forces pandas
    # to reallocate the BlockManager out of the shared buffer; multiplied by N
    # workers and M trials → RAM exhaustion before the first cycle completes.
    # ALWAYS compute indicators into LOCAL numpy arrays via `.to_numpy()`.
    rsi_arr = ta.rsi(data["close"], length=rsi_len).to_numpy()

    # ── STEP 2: AUXILIARY INDICATORS (vectorized, pre-loop) ──
    # Computed on the aux DataFrame directly; aligned to primary later via
    # searchsorted inside the bar loop. NEVER merge/join aux with primary —
    # that alters primary length and breaks visualization.
    aux2        = data_aux["dataset_2"]
    aux2_times  = aux2["open_time"].values if "open_time" in aux2.columns else aux2["time"].values
    aux2_close  = aux2["close"].values
    aux2_ema    = aux2["close"].ewm(span=macro_len, adjust=False).mean().values

    # ── STEP 3: TALIPP PATH-DEPENDENT INDICATORS (via engine.persist) ──
    # engine.persist returns the SAME instance across live ticks → the talipp
    # object accumulates state correctly tick after tick. In backtest/optimizer
    # the factory fires once per run; the state lives for the entire backtest.
    st = engine.persist(
        "st_obj",
        factory=lambda: SuperTrend(atr_period=atr_len, mult=atr_mult),
    )
    st_state = engine.persist("st_state", factory=lambda: {"last_t": -1})

    # ── STEP 4: NUMPY EXTRACTION (MANDATORY before the bar loop) ──
    o = data["open"].values
    h = data["high"].values
    l = data["low"].values
    c = data["close"].values
    tms = (data["time"] if "time" in data.columns else data["open_time"]).values
    n = len(data)

    # ── STEP 4.5: FEED TALIPP (canonical CLOSED-BARS-ONLY pattern) ──
    # CRITICAL — PATH-DEPENDENT INDICATORS NEVER RECEIVE THE FORMING BAR.
    # The last row of `data` is the forming bar in live (OHLC partial, changing
    # with every aggTrade tick). Feeding it to a path-dependent indicator
    # contaminates its internal state (final_upper/final_lower bands, Wilder
    # ATR smoothing, KAMA's efficiency ratio, etc.) — the indicator value at
    # close-of-bar will DIFFER from what the backtest computed on the same
    # bar's final OHLC. Reproduce backtest 1:1 by iterating ONLY to
    # n_closed = n - 1 and never calling st.update() on the forming bar.
    # See runtime_constraints.md §7 (forming-bar quarantine).
    n_closed = n - 1  # excludes the forming bar (last row of `data`)
    last_t = st_state["last_t"]

    # Window-slid guard: in live, if the rolling window slid past `last_t`, the
    # talipp object has stale state for bars no longer in the window. Reset
    # and re-warmup from scratch.
    if last_t > 0:
        new_idx_check = int(np.searchsorted(tms[:n_closed], last_t, side="right"))
        if new_idx_check == 0:
            engine.custom.pop("st_obj", None)
            engine.custom.pop("st_state", None)
            st = engine.persist(
                "st_obj",
                factory=lambda: SuperTrend(atr_period=atr_len, mult=atr_mult),
            )
            st_state = engine.persist("st_state", factory=lambda: {"last_t": -1})
            last_t = -1

    if last_t < 0:
        # First invocation (or post-reset): full warmup with add() — closed bars only.
        for i in range(n_closed):
            st.add(OHLCV(open=float(o[i]), high=float(h[i]),
                         low=float(l[i]), close=float(c[i])))
        if n_closed > 0:
            st_state["last_t"] = int(tms[n_closed - 1])
    else:
        new_idx = int(np.searchsorted(tms[:n_closed], last_t, side="right"))
        if new_idx < n_closed:
            # New bar(s) have CLOSED since the last tick. Add them with their
            # FINAL OHLC. We never update() the forming bar — that contaminates
            # path-dependent state.
            for i in range(new_idx, n_closed):
                st.add(OHLCV(open=float(o[i]), high=float(h[i]),
                             low=float(l[i]), close=float(c[i])))
            st_state["last_t"] = int(tms[n_closed - 1])
        # else: no new closed bars since last_t — no-op. The forming bar
        # (data.iloc[n-1]) is NOT fed to the indicator. TP/SL/trailing intra-bar
        # remain reactive because they use `engine._bar` directly (set by
        # `engine.on_bar()`), NOT the talipp indicator value.

    # ── STEP 4.6: BUILD TALIPP ARRAYS ALIGNED TO data (length = n) ──
    # talipp's output_values has n_closed entries (one per closed bar). We pad
    # warmup at the start and append a final `None` for the forming bar so the
    # resulting array has length `n` (same as `data`), with `trend[n-1] = NaN`.
    # That NaN guarantees `flip_up[n-1]` / `flip_down[n-1]` are False — entries
    # are decided on the previous (closed) bar's indicator value, NOT on the
    # forming bar's partial OHLC. Matches backtest 1:1.
    raw = list(st.output_values)  # length = n_closed
    if len(raw) < n_closed:
        raw = [None] * (n_closed - len(raw)) + raw
    else:
        raw = raw[-n_closed:]
    raw.append(None)  # forming bar slot — indicator value indefinite, signal stays False
    trend = np.array([
        (1.0 if v.trend == Trend.UP else -1.0) if v is not None else np.nan
        for v in raw
    ], dtype=np.float64)
    st_value = np.array([
        v.value if v is not None else np.nan for v in raw
    ], dtype=np.float64)

    # ── STEP 5: VECTORIZED SIGNAL PRE-COMPUTATION ──
    # Boolean arrays of length n. Adapt this section to the actual strategy logic.
    flip_up   = np.r_[False, (trend[1:] ==  1.0) & (trend[:-1] == -1.0)]
    flip_down = np.r_[False, (trend[1:] == -1.0) & (trend[:-1] ==  1.0)]
    exit_long_signal  = rsi_arr > rsi_ob
    exit_short_signal = rsi_arr < rsi_os

    # ── ENGINE API — exact surface (do NOT invent methods/kwargs/attributes) ──
    # Actions (these are the ONLY kwargs each accepts):
    #   engine.on_bar(bar=(o,h,l,c), time=t)          # FIRST call of EVERY iteration
    #   engine.buy(price=None, size=None, signal=)    # price None→open; size None→auto-size
    #   engine.sell(price=None, size=None, signal=)
    #   engine.close(price=None, size=None, signal=)  # size None→close all; size<qty→partial
    #   engine.set_exit(tp=None, sl=None, trailing=)  # the ONLY way to do TP/SL/trailing
    #   engine.persist(key, factory)
    # Reads: engine.is_flat/is_long/is_short, avg_cost, qty, side, equity, bars_in_trade,
    #   consecutive_wins, consecutive_losses, custom
    #   get_trades() → BACKTEST ONLY. Empty in live (the completed-trade list is cleared
    #   every tick), so never gate on it; count closures into engine.persist instead.
    #   Shape: list[dict]; trade has "pnl" (NOT "pnl_pct"); each trade["fills"]/
    #   engine._fills item has "type" ("buy"|"sell"|"close") — there is NO "side" key.
    # DOES NOT EXIST — do NOT use: engine.closed_trades, engine.closed_trades_count,
    #   trade["pnl_pct"], fill["side"], kwargs size_fraction/fraction/pct on buy/sell/close,
    #   and manual TP/SL/trailing checks on c[i]/h[i]/l[i] (always use engine.set_exit).

    # ── STEP 6: BAR LOOP ──
    for i in range(1, n):

        # 6.0 ALWAYS first: feed bar to engine. BOTH args REQUIRED — no defaults.
        # `bar` is a 4-tuple (open, high, low, close); `time` is the bar timestamp.
        # on_bar() also auto-checks TP/SL/trailing → may auto-close the position.
        engine.on_bar(
            bar=(float(o[i]), float(h[i]), float(l[i]), float(c[i])),
            time=int(tms[i]),
        )

        # 6.1 (optional) Risk gate via framework-managed reserved key:
        # if engine.custom.get("consecutive_losses", 0) >= int(params["max_consec_losses"]):
        #     continue  # skip entries; TP/SL of open trade still active via on_bar()

        # 6.2 Signal-based exits (read signal at i-1; fill lands at open[i]).
        if engine.is_long and exit_long_signal[i-1]:
            engine.close(signal="EXIT_LONG_RSI")
        elif engine.is_short and exit_short_signal[i-1]:
            engine.close(signal="EXIT_SHORT_RSI")

        # 6.3 Auxiliary alignment (point-in-time, no look-ahead).
        # ALWAYS use side="right" minus 1 (= last known value at or before tms[i]).
        # ALWAYS handle macro_idx < 0 (no aux data yet at the start of the period).
        macro_idx = int(np.searchsorted(aux2_times, tms[i], side="right")) - 1
        if macro_idx >= 0:
            macro_bullish = aux2_close[macro_idx] > aux2_ema[macro_idx]
        else:
            macro_bullish = False

        # 6.4 Entries — only when engine.is_flat. on_bar may have auto-closed via TP/SL.
        # Apply the aux filter: only go long when macro bullish, only short when bearish.
        if flip_up[i-1] and engine.is_flat and macro_bullish:
            engine.buy(signal="BUY_FLIP_UP")
            # ANCHOR TO THE REAL FILL (engine.avg_cost) — never `entry = c[i]`
            # (the entry bar's future close): that's intra-bar look-ahead, it
            # inflates the backtest and diverges live. See msf_canon §7.7.
            engine.set_exit(
                tp=engine.avg_cost * (1 + tp_pct),
                sl=engine.avg_cost * (1 - sl_pct),
            )
            # NOTE: set_exit fires _check_tp_sl intra-bar. If H/L of the entry
            # bar already crossed TP/SL, the engine auto-closes inside set_exit.
            # ANY further engine action in this iteration must re-check
            # engine.is_long / engine.is_short first.
        elif flip_down[i-1] and engine.is_flat and (not macro_bullish):
            engine.sell(signal="SELL_FLIP_DOWN")
            engine.set_exit(
                tp=engine.avg_cost * (1 - tp_pct),
                sl=engine.avg_cost * (1 + sl_pct),
            )

    # ── STEP 7: VISUALIZATION (single return value) ──
    # Canonical shape: TOP-LEVEL "series" key, NO wrapper ("main", "panels", etc.).
    # Pass raw .values (NaN → chart gap automatically; do NOT fillna(0)).
    # Aux-derived series MUST be projected onto the primary timeline before being
    # placed here (length must match data length). This example only renders the
    # primary indicators; an aux EMA could be projected via searchsorted if needed.
    return {
        "series": [
            {
                "name": "RSI",
                "type": "line",
                "pane": 1,
                "color": "#2962FF",
                "lineWidth": 2,
                "data": rsi_arr,
                "levels": [
                    {"value": rsi_ob, "color": "#787B86", "style": "dashed", "label": "OB"},
                    {"value": rsi_os, "color": "#787B86", "style": "dashed", "label": "OS"},
                ],
            },
            {
                "name": "SuperTrend",
                "type": "line",
                "pane": 0,
                "color": "#26A69A",
                "lineWidth": 1,
                "data": st_value,
            },
        ],
    }

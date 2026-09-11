# MSF Strategy Library — Gold Standard Examples
> Four progressive examples covering the typical complexity ranges of MSF strategies.
> Each example builds on the previous one. Use them as templates — don't copy verbatim, adapt to the user's actual request.

## Index

1. **Example 1 — Simple pandas-ta only**: RSI + EMA crossover with TP/SL. No path-dependent indicators. The simplest valid MSF shape.
2. **Example 2 — talipp + engine.persist**: SuperTrend (talipp) + RSI/ATR/ADX (pandas-ta) + macro filter via auxiliary 4H dataset. Shows the canonical path-dependent indicator pattern. Validated in backtest and currently running in live.
3. **Example 3 — Pyramid + partial close**: SuperTrend (talipp) + EMA filter + multi-leg entry + partial close at TP1 + final close at TP2 or SL. Shows the multi-leg pattern with the mandatory `engine.is_long` re-checks after each `set_exit`.
4. **Example 4 — DIY path-dependent indicator**: Heikin-Ashi built by hand with `engine.persist`, for path-dependent indicators talipp does not implement.

> The closed-bars-only talipp feed and the `None`-padding pattern appear in full in Examples 2, 3 and 4 because each example is meant to be copied and run as a whole. The rule itself — and why it exists — is stated once in `msf_canon §7.3-7.4` and `runtime_constraints §5`; the examples show it, they do not re-argue it.

---

## Example 1 — Simple pandas-ta only

**Use case**: trend-following with RSI exits, no path-dependent indicators.

**Indicators**:
- RSI (pandas-ta, length 14): overbought/oversold for entries and exits.
- EMA fast & slow (pandas-ta): trend filter.

**Logic**:
- BUY: RSI crosses below 30 (oversold) AND EMA fast > EMA slow (bullish trend).
- SELL: RSI crosses above 70 (overbought) AND EMA fast < EMA slow.
- Exit on opposite RSI cross OR fixed TP/SL.

```python
import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict, Any

# ────────────────────────────────────────────────────────────────
# 1. PARAMETERS
# ────────────────────────────────────────────────────────────────
strategy_parameters: Dict[str, Any] = {
    "rsi_length":      14,
    "rsi_ob":          70.0,
    "rsi_os":          30.0,
    "ema_fast":        20,
    "ema_slow":        50,
    "takeProfitPerc":  2.0,
    "stopLossPerc":    1.0,
}

strategy_options: Dict[str, Any] = {}
auxiliary_datasets: Dict[str, str] = {}

warmup_spec: Dict[str, Any] = {
    "simple_windows": ["ema_fast", "ema_slow"],
    "wilder_lengths": ["rsi_length"],
    "epsilon": 0.001,
}

# ────────────────────────────────────────────────────────────────
# 2. MAIN FUNCTION
# ────────────────────────────────────────────────────────────────
def trading_strategy(
    data: pd.DataFrame,
    data_aux: Dict[str, pd.DataFrame],
    params: Dict[str, Any],
    capital_cfg: Dict[str, Any],
    engine,
) -> Dict[str, Any]:

    # Unpack
    rsi_len  = int(params["rsi_length"])
    rsi_ob   = float(params["rsi_ob"])
    rsi_os   = float(params["rsi_os"])
    ema_fast = int(params["ema_fast"])
    ema_slow = int(params["ema_slow"])
    tp_pct   = float(params["takeProfitPerc"]) / 100.0
    sl_pct   = float(params["stopLossPerc"])  / 100.0

    # Indicators (pandas-ta inline, vectorized → LOCAL numpy arrays).
    # NEVER assign to data[...] — the optimizer reuses this DataFrame across
    # trials; mutation breaks shared-memory backing. See runtime_constraints.md §6.
    rsi   = ta.rsi(data["close"], length=rsi_len).to_numpy()
    ema_f = ta.ema(data["close"], length=ema_fast).to_numpy()
    ema_s = ta.ema(data["close"], length=ema_slow).to_numpy()

    # NumPy extraction (OHLCV only — read-only views are free)
    o = data["open"].values
    h = data["high"].values
    l = data["low"].values
    c = data["close"].values
    tms = (data["time"] if "time" in data.columns else data["open_time"]).values
    n = len(data)

    # Vectorized signals
    cross_below_os = np.r_[False, (rsi[1:] <= rsi_os)  & (rsi[:-1] >  rsi_os)]
    cross_above_ob = np.r_[False, (rsi[1:] >= rsi_ob)  & (rsi[:-1] <  rsi_ob)]
    bull = ema_f > ema_s
    bear = ema_f < ema_s

    buy_signal       = cross_below_os & bull
    sell_signal      = cross_above_ob & bear
    exit_long_signal = cross_above_ob
    exit_short_signal= cross_below_os

    # Bar loop
    for i in range(1, n):

        engine.on_bar(
            bar=(float(o[i]), float(h[i]), float(l[i]), float(c[i])),
            time=int(tms[i]),
        )

        # Signal-based exits
        if engine.is_long and exit_long_signal[i-1]:
            engine.close(signal="EXIT_LONG_RSI")
        elif engine.is_short and exit_short_signal[i-1]:
            engine.close(signal="EXIT_SHORT_RSI")

        # Entries (only when flat — TP/SL may have closed via on_bar)
        if buy_signal[i-1] and engine.is_flat:
            engine.buy(signal="BUY")
            engine.set_exit(
                tp=engine.avg_cost * (1 + tp_pct),
                sl=engine.avg_cost * (1 - sl_pct),
            )
        elif sell_signal[i-1] and engine.is_flat:
            engine.sell(signal="SELL")
            engine.set_exit(
                tp=engine.avg_cost * (1 - tp_pct),
                sl=engine.avg_cost * (1 + sl_pct),
            )

    # Visualization
    return {
        "series": [
            {
                "name": "RSI", "type": "line", "pane": 1,
                "color": "#2962FF", "lineWidth": 2, "data": rsi,
                "levels": [
                    {"value": rsi_ob, "color": "#787B86", "style": "dashed", "label": "OB"},
                    {"value": rsi_os, "color": "#787B86", "style": "dashed", "label": "OS"},
                ],
            },
            {"name": "EMA fast", "type": "line", "pane": 0,
             "color": "#FF6D00", "lineWidth": 2, "data": ema_f},
            {"name": "EMA slow", "type": "line", "pane": 0,
             "color": "#2962FF", "lineWidth": 2, "data": ema_s},
        ]
    }
```

**Notes for the AI**: this is the simplest valid MSF strategy. No talipp imports, no `engine.persist`, no padding pattern. Use this template when the user requests indicators that are all convergent (RSI, ATR, EMA, MACD, BB, etc.). If the user mentions any path-dependent indicator (SuperTrend, PSAR, OBV, VWAP, Heikin-Ashi, etc.), switch to Example 2.

---

## Example 2 — talipp + engine.persist with macro filter

**Use case**: SuperTrend-driven entries with RSI mid-exits, ADX gating, MA filter, and a macro-trend filter via auxiliary higher-timeframe dataset.

**Indicators**:
- **SuperTrend** (**talipp**, path-dependent): trend flip detection.
- RSI, ATR, ADX (pandas-ta): mid-exit triggers, volatility, trend strength.
- MA on primary: trend filter at the bar level.
- EMA on auxiliary 4H (pandas-ta inline): macro trend filter — bullish only if `aux2.close > aux2.EMA(macro_period)`.

**Logic**:
- BUY: SuperTrend flips up (talipp `Trend.DOWN → Trend.UP`) AND close > MA AND ADX > threshold AND macro bullish.
- SELL: mirror.
- Mid-exits: RSI crossing below the `rsi_mid_long` (long) or above `rsi_mid_short` (short).
- TP/SL: fixed percentage.

```python
import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict, Any

# Talipp imports — ONLY because this strategy uses SuperTrend
from talipp.indicators import SuperTrend
from talipp.indicators.SuperTrend import Trend
from talipp.ohlcv import OHLCV

# ────────────────────────────────────────────────────────────────
# 1. PARAMETERS
# ────────────────────────────────────────────────────────────────
strategy_parameters: Dict[str, Any] = {
    "rsilength":          9,
    "rsiOS":              39.0,
    "rsiOB":              83.0,
    "atr_period":         17,        # SuperTrend's ATR + pandas-ta ATR (shared)
    "atr_multiplier":     1.15,      # SuperTrend mult
    "takeProfitPerc":     0.0,       # 0 disables fixed TP
    "stopLossPerc":       0.56,
    "ma_period":          30,
    "ma_source":          "open",
    "adx_threshold":      7.0,
    "adx_len":            2,
    "adx_smoothing":      1,
    "rsiMidExitLong":     22.0,
    "rsiMidExitShort":    35.0,
    "macro_ema_period":   44,
}

strategy_options: Dict[str, Any] = {
    "ma_source": ["open", "high", "low", "close", "hl2", "hlc3", "ohlc4"],
}

auxiliary_datasets: Dict[str, str] = {
    "dataset_2": "Macro-trend filter (typically a higher-timeframe of the same asset)",
}

warmup_spec: Dict[str, Any] = {
    "simple_windows": ["ma_period"],
    "wilder_lengths": [
        "rsilength",
        "atr_period",                          # covers BOTH pandas-ta ATR AND talipp SuperTrend
        ("adx_len", "adx_smoothing"),
    ],
    "epsilon": 0.001,
    "auxiliary": {
        "dataset_2": {
            "simple_windows": ["macro_ema_period"],
            "wilder_lengths": [],
        },
    },
}

def compute_source(df: pd.DataFrame, key: str) -> pd.Series:
    if key == "hl2":  return (df["high"] + df["low"]) / 2.0
    if key == "hlc3": return (df["high"] + df["low"] + df["close"]) / 3.0
    if key == "ohlc4":return (df["open"] + df["high"] + df["low"] + df["close"]) / 4.0
    return df[key]

# ────────────────────────────────────────────────────────────────
# 2. MAIN FUNCTION
# ────────────────────────────────────────────────────────────────
def trading_strategy(
    data: pd.DataFrame,
    data_aux: Dict[str, pd.DataFrame],
    params: Dict[str, Any],
    capital_cfg: Dict[str, Any],
    engine,
) -> Dict[str, Any]:

    # ── Validate essential auxiliary ──
    if "dataset_2" not in data_aux or data_aux["dataset_2"].empty:
        raise ValueError(
            "This strategy requires dataset_2 (macro-trend filter). "
            "Select an auxiliary dataset in the UI."
        )

    # ── Unpack ──
    rsi_len   = int(params["rsilength"])
    rsi_os    = float(params["rsiOS"])
    rsi_ob    = float(params["rsiOB"])
    atr_len   = int(params["atr_period"])
    atr_mult  = float(params["atr_multiplier"])
    tp_pct    = float(params["takeProfitPerc"]) / 100.0
    sl_pct    = float(params["stopLossPerc"]) / 100.0
    ma_len    = int(params["ma_period"])
    ma_key    = params["ma_source"]
    adx_th    = float(params["adx_threshold"])
    adx_len   = int(params["adx_len"])
    adx_smooth= int(params["adx_smoothing"])
    rsi_mid_long  = float(params["rsiMidExitLong"])
    rsi_mid_short = float(params["rsiMidExitShort"])
    macro_len = int(params["macro_ema_period"])

    # ── pandas-ta convergent indicators → LOCAL numpy arrays ──
    # NEVER assign to data[...] — the optimizer reuses this DataFrame across
    # trials; mutation breaks shared-memory backing. See runtime_constraints.md §6.
    src_ma  = compute_source(data, ma_key)
    rsi_arr = ta.rsi(data["close"], length=rsi_len).to_numpy()
    atr_arr = ta.atr(data["high"], data["low"], data["close"], length=atr_len).to_numpy()
    ma_arr  = src_ma.rolling(ma_len).mean().to_numpy()
    adx_df  = ta.adx(data["high"], data["low"], data["close"],
                     length=adx_len, lensig=adx_smooth)
    adx_col = next(c for c in adx_df.columns if c.startswith("ADX_"))
    adx_arr = adx_df[adx_col].to_numpy()

    # ── Auxiliary indicator (macro EMA on dataset_2) ──
    aux2 = data_aux["dataset_2"]
    aux2_times = aux2["open_time"].values if "open_time" in aux2.columns else aux2["time"].values
    aux2_close = aux2["close"].values
    aux2_ema   = aux2["close"].ewm(span=macro_len, adjust=False).mean().values

    # ── talipp path-dependent: SuperTrend via engine.persist ──
    st = engine.persist(
        "st_obj",
        factory=lambda: SuperTrend(atr_period=atr_len, mult=atr_mult),
    )
    st_state = engine.persist("st_state", factory=lambda: {"last_t": -1})

    # ── NumPy extraction (OHLCV only — read-only views are free) ──
    o = data["open"].values
    h = data["high"].values
    l = data["low"].values
    c = data["close"].values
    tms = data["open_time"].values if "open_time" in data.columns else data["time"].values
    n = len(data)

    # ── Feed talipp — CLOSED BARS ONLY (forming-bar quarantine, see runtime_constraints.md §11) ──
    n_closed = n - 1   # exclude the forming bar (data.iloc[n-1])
    last_t = st_state["last_t"]
    if last_t > 0:
        new_idx_check = int(np.searchsorted(tms[:n_closed], last_t, side="right"))
        if new_idx_check == 0:
            engine.custom.pop("st_obj", None)
            engine.custom.pop("st_state", None)
            st = engine.persist("st_obj",
                                factory=lambda: SuperTrend(atr_period=atr_len, mult=atr_mult))
            st_state = engine.persist("st_state", factory=lambda: {"last_t": -1})
            last_t = -1

    if last_t < 0:
        for i in range(n_closed):                # NOT range(n) — forming bar excluded
            st.add(OHLCV(open=float(o[i]), high=float(h[i]),
                         low=float(l[i]), close=float(c[i])))
        if n_closed > 0:
            st_state["last_t"] = int(tms[n_closed - 1])
    else:
        new_idx = int(np.searchsorted(tms[:n_closed], last_t, side="right"))
        if new_idx < n_closed:
            for i in range(new_idx, n_closed):
                st.add(OHLCV(open=float(o[i]), high=float(h[i]),
                             low=float(l[i]), close=float(c[i])))
            st_state["last_t"] = int(tms[n_closed - 1])
        # else: no new closed bars — no-op. NEVER st.update(forming bar).

    # ── Build trend / st_value arrays aligned to `data` (length = n) ──
    raw = list(st.output_values)                  # length = n_closed
    if len(raw) < n_closed:
        raw = [None] * (n_closed - len(raw)) + raw
    else:
        raw = raw[-n_closed:]
    raw.append(None)                               # forming bar slot — indicator undefined
    trend = np.array([
        (1.0 if v.trend == Trend.UP else -1.0) if v is not None else np.nan
        for v in raw
    ], dtype=np.float64)
    st_value = np.array([
        v.value if v is not None else np.nan for v in raw
    ], dtype=np.float64)

    # ── Vectorized signals (length n; trend[n-1] is NaN, so flip_*[n-1] is False) ──
    flip_up   = np.r_[False, (trend[1:] ==  1.0) & (trend[:-1] == -1.0)]
    flip_down = np.r_[False, (trend[1:] == -1.0) & (trend[:-1] ==  1.0)]
    buy_sig   = flip_up   & (c > ma_arr)
    sell_sig  = flip_down & (c < ma_arr)

    def crossunder(arr, thresh):
        cu = (arr[:-1] > thresh) & (arr[1:] <= thresh)
        return np.insert(cu, 0, False)
    def crossover(arr, thresh):
        co = (arr[:-1] < thresh) & (arr[1:] >= thresh)
        return np.insert(co, 0, False)

    exit_long_ob   = crossunder(rsi_arr, rsi_ob)
    exit_short_os  = crossover(rsi_arr, rsi_os)
    exit_long_mid  = crossunder(rsi_arr, rsi_mid_long)
    exit_short_mid = crossover(rsi_arr, rsi_mid_short)

    # ── Bar loop ──
    for i in range(1, n):

        engine.on_bar(
            bar=(float(o[i]), float(h[i]), float(l[i]), float(c[i])),
            time=int(tms[i]),
        )

        # RSI exits
        if engine.is_long and (exit_long_ob[i-1] or exit_long_mid[i-1]):
            engine.close(signal="Close_BUY_RSI" if exit_long_ob[i-1] else "Close_BUY_RSI_Mid")
        elif engine.is_short and (exit_short_os[i-1] or exit_short_mid[i-1]):
            engine.close(signal="Close_SELL_RSI" if exit_short_os[i-1] else "Close_SELL_RSI_Mid")

        # Macro filter via aux 4H
        macro_idx = int(np.searchsorted(aux2_times, tms[i], side="right")) - 1
        macro_bullish = (macro_idx >= 0) and (aux2_close[macro_idx] > aux2_ema[macro_idx])

        # ADX gate
        adx_ok = adx_arr[i-1] > adx_th

        # BUY (only if flat + ADX ok + macro bullish)
        if buy_sig[i-1] and adx_ok and macro_bullish:
            if engine.is_short:
                engine.close(signal="Close Short")
            if engine.is_flat:
                engine.buy(signal="BUY")
                entry_price = engine.avg_cost
                engine.set_exit(
                    tp=entry_price * (1 + tp_pct) if tp_pct > 0 else None,
                    sl=entry_price * (1 - sl_pct),
                )

        # SELL (only if flat + ADX ok + macro bearish)
        elif sell_sig[i-1] and adx_ok and (not macro_bullish):
            if engine.is_long:
                engine.close(signal="Close Long")
            if engine.is_flat:
                engine.sell(signal="SELL")
                entry_price = engine.avg_cost
                engine.set_exit(
                    tp=entry_price * (1 - tp_pct) if tp_pct > 0 else None,
                    sl=entry_price * (1 + sl_pct),
                )

    # ── Visualization ──
    return {
        "series": [
            {"name": "RSI", "type": "line", "pane": 1, "color": "#2962FF", "lineWidth": 2,
             "data": rsi_arr,
             "levels": [
                 {"value": rsi_ob, "color": "#787B86", "style": "dashed", "label": "OB"},
                 {"value": rsi_os, "color": "#787B86", "style": "dashed", "label": "OS"},
                 {"value": rsi_mid_long,  "color": "#E91E63", "style": "dotted", "label": "Mid Long"},
                 {"value": rsi_mid_short, "color": "#4CAF50", "style": "dotted", "label": "Mid Short"},
             ]},
            {"name": "MA", "type": "line", "pane": 0, "color": "#FF6D00", "lineWidth": 2, "data": ma_arr},
            {"name": "ADX", "type": "line", "pane": 2, "color": "#E040FB", "lineWidth": 2,
             "data": adx_arr,
             "levels": [{"value": adx_th, "color": "#787B86", "style": "dashed", "label": "Threshold"}]},
            {"name": "SuperTrend", "type": "line", "pane": 0, "color": "#26A69A", "lineWidth": 1, "data": st_value},
        ]
    }
```

**Notes for the AI**:
- The talipp SuperTrend object is created via `engine.persist("st_obj", factory=...)` — never at module level (the validator rejects). The state dict `engine.persist("st_state", ...)` tracks `last_t` for the add+update pattern.
- The window-slid guard (block before `if last_t < 0`) handles the live edge case where the rolling window slid past `last_t`. In backtest it never triggers (single-shot full-history call) — the guard is defensive code for live.
- The padding pattern (`if len(raw) < n: pad else: slice`) is MANDATORY. Without it the strategy passes backtest but crashes in live with a numpy broadcast error.
- The `engine.set_exit(tp=...)` fires `_check_tp_sl` immediately. If the entry bar already crossed TP/SL, the engine auto-closes inside `set_exit`. Subsequent engine actions (none in this example) would need to re-check `engine.is_long`.

Use this template when the user requests SuperTrend, ParabolicSAR, OBV, session VWAP, Heikin-Ashi, Renko, ZigZag, Ichimoku — any path-dependent indicator. The pandas-ta indicators (RSI, ATR, ADX, etc.) live alongside in the same strategy.

---

## Example 3 — Pyramid + partial close

**Use case**: scaled-in trades. Initial entry on signal, add a pyramid leg if price moves favorably, partial close at TP1, full close at TP2 or SL.

**Indicators**:
- SuperTrend (talipp) for entry signals.
- EMA fast / slow (pandas-ta) for trend filter.

**Logic**:
- Initial entry: SuperTrend flip + close above EMA slow (long) or below (short).
- After entry: if price moves +`pyramid_threshold_pct` favorable, add a 50% pyramid leg. Re-set SL based on new weighted avg_cost.
- Manual TP1 detection (the engine's TP would do a FULL close, not partial): `engine.close(size=qty/2, signal="PARTIAL_TP1")` when H/L crosses tp1.
- After partial: `set_exit(tp=tp2, sl=...)` so the engine auto-closes the remainder at tp2 (full close OK because it's the remaining qty).

**Critical pattern**: every `engine.set_exit` may auto-close intra-bar via the hook. Re-check `engine.is_long` / `engine.is_short` before each subsequent action.

```python
import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict, Any

from talipp.indicators import SuperTrend
from talipp.indicators.SuperTrend import Trend
from talipp.ohlcv import OHLCV

# ────────────────────────────────────────────────────────────────
# 1. PARAMETERS
# ────────────────────────────────────────────────────────────────
strategy_parameters: Dict[str, Any] = {
    "ema_fast":               3,
    "ema_slow":               8,
    "atr_period":             3,
    "atr_multiplier":         1.0,
    # Pyramid + partial close
    "pyramid_threshold_pct":  0.15,
    "pyramid_leg_size_pct":   50.0,
    "tp1_pct":                0.30,
    "tp2_pct":                0.60,
    "stopLossPerc":           0.30,
    "exit_on_flip":           True,
}

strategy_options: Dict[str, Any] = {}
auxiliary_datasets: Dict[str, str] = {}

warmup_spec: Dict[str, Any] = {
    "simple_windows": ["ema_fast", "ema_slow"],
    "wilder_lengths": ["atr_period"],
    "epsilon": 0.001,
}

# ────────────────────────────────────────────────────────────────
# 2. MAIN FUNCTION
# ────────────────────────────────────────────────────────────────
def trading_strategy(
    data: pd.DataFrame,
    data_aux: Dict[str, pd.DataFrame],
    params: Dict[str, Any],
    capital_cfg: Dict[str, Any],
    engine,
) -> Dict[str, Any]:

    # Unpack
    ema_fast_len = int(params["ema_fast"])
    ema_slow_len = int(params["ema_slow"])
    atr_len      = int(params["atr_period"])
    atr_mult     = float(params["atr_multiplier"])
    pyr_th       = float(params["pyramid_threshold_pct"]) / 100.0
    pyr_size     = float(params["pyramid_leg_size_pct"])  / 100.0
    tp1_pct      = float(params["tp1_pct"])  / 100.0
    tp2_pct      = float(params["tp2_pct"])  / 100.0
    sl_pct       = float(params["stopLossPerc"]) / 100.0
    exit_on_flip = bool(params["exit_on_flip"])

    # pandas-ta indicators → LOCAL numpy arrays.
    # NEVER assign to data[...] — the optimizer reuses this DataFrame across
    # trials; mutation breaks shared-memory backing. See runtime_constraints.md §6.
    ema_f = ta.ema(data["close"], length=ema_fast_len).to_numpy()
    ema_s = ta.ema(data["close"], length=ema_slow_len).to_numpy()

    # talipp via engine.persist
    st = engine.persist(
        "st_obj",
        factory=lambda: SuperTrend(atr_period=atr_len, mult=atr_mult),
    )
    st_state = engine.persist("st_state", factory=lambda: {"last_t": -1})

    # NumPy extraction (OHLCV only — read-only views are free)
    o = data["open"].values
    h = data["high"].values
    l = data["low"].values
    c = data["close"].values
    tms = data["open_time"].values if "open_time" in data.columns else data["time"].values
    n = len(data)

    # Feed talipp — CLOSED BARS ONLY (forming-bar quarantine, runtime_constraints.md §11)
    n_closed = n - 1   # exclude forming bar (data.iloc[n-1])
    last_t = st_state["last_t"]
    if last_t > 0:
        new_idx_check = int(np.searchsorted(tms[:n_closed], last_t, side="right"))
        if new_idx_check == 0:
            engine.custom.pop("st_obj", None)
            engine.custom.pop("st_state", None)
            st = engine.persist("st_obj",
                                factory=lambda: SuperTrend(atr_period=atr_len, mult=atr_mult))
            st_state = engine.persist("st_state", factory=lambda: {"last_t": -1})
            last_t = -1

    if last_t < 0:
        for i in range(n_closed):                # NOT range(n)
            st.add(OHLCV(open=float(o[i]), high=float(h[i]),
                         low=float(l[i]), close=float(c[i])))
        if n_closed > 0:
            st_state["last_t"] = int(tms[n_closed - 1])
    else:
        new_idx = int(np.searchsorted(tms[:n_closed], last_t, side="right"))
        if new_idx < n_closed:
            for i in range(new_idx, n_closed):
                st.add(OHLCV(open=float(o[i]), high=float(h[i]),
                             low=float(l[i]), close=float(c[i])))
            st_state["last_t"] = int(tms[n_closed - 1])
        # else: no new closed bars — no-op. NEVER st.update(forming bar).

    # Build trend array (length n; forming-bar slot = None)
    raw = list(st.output_values)                  # length = n_closed
    if len(raw) < n_closed:
        raw = [None] * (n_closed - len(raw)) + raw
    else:
        raw = raw[-n_closed:]
    raw.append(None)                              # forming bar slot
    trend = np.array([
        (1.0 if v.trend == Trend.UP else -1.0) if v is not None else np.nan
        for v in raw
    ], dtype=np.float64)
    st_value = np.array([
        v.value if v is not None else np.nan for v in raw
    ], dtype=np.float64)

    # Vectorized signals (trend[n-1] is NaN, so flip_*[n-1] is False)
    flip_up   = np.r_[False, (trend[1:] ==  1.0) & (trend[:-1] == -1.0)]
    flip_down = np.r_[False, (trend[1:] == -1.0) & (trend[:-1] ==  1.0)]
    bull = c > ema_s
    bear = c < ema_s
    buy_sig  = flip_up   & bull
    sell_sig = flip_down & bear

    # Helpers to count fills of the current trade (resets in _complete_trade)
    def n_entries(side: str) -> int:
        return len([f for f in engine._fills if f["type"] == side])
    def n_closes() -> int:
        return len([f for f in engine._fills if f["type"] == "close"])

    # Bar loop
    for i in range(1, n):

        engine.on_bar(
            bar=(float(o[i]), float(h[i]), float(l[i]), float(c[i])),
            time=int(tms[i]),
        )

        # Flip exit (if enabled)
        if exit_on_flip:
            if engine.is_long and flip_down[i-1]:
                engine.close(signal="Close_BUY_Flip")
            elif engine.is_short and flip_up[i-1]:
                engine.close(signal="Close_SELL_Flip")

        # ── Pyramid + partial close: LONG ──
        # CRITICAL: every set_exit may auto-close intra-bar. Re-check
        # engine.is_long before each subsequent action.
        if engine.is_long:
            n_buy = n_entries("buy")
            n_cls = n_closes()
            curr_price = float(c[i-1])

            # Pyramid: add 1 leg when price moved +pyr_th from initial avg.
            # Class-of-bug guard (system_prompt rule 14b): every block AFTER
            # on_bar that depends on engine.is_long must be guarded by fill
            # counters (n_buy, n_cls), not only by is_long. Position state
            # alone cannot distinguish "leg-1 open, no partial yet" from
            # "leg-1+leg-2, partial done, 50% remaining" — both have is_long
            # = True. In live (per-tick), intermediate states are reachable;
            # in backtest (full H/L), they're not. Different orders unless
            # the strategy guards on counters.
            if n_buy == 1 and n_cls == 0:
                move_pct = (curr_price - engine.avg_cost) / engine.avg_cost
                if move_pct >= pyr_th:
                    pyramid_size = engine._fills[0]["size"] * pyr_size
                    engine.buy(size=pyramid_size, signal="PYRAMID_BUY")
                    engine.set_exit(sl=engine.avg_cost * (1 - sl_pct))
                    # set_exit may have auto-closed → re-check below

            # Partial close at tp1 (manual — engine's TP would do FULL close)
            if engine.is_long and n_cls == 0 and h[i-1] >= engine.avg_cost * (1 + tp1_pct):
                engine.close(size=engine.qty * 0.5, signal="PARTIAL_TP1")
                # Now set TP=tp2 so the engine auto-closes the remainder
                engine.set_exit(
                    tp=engine.avg_cost * (1 + tp2_pct),
                    sl=engine.avg_cost * (1 - sl_pct),
                )

        # ── Pyramid + partial close: SHORT (mirror) ──
        if engine.is_short:
            n_sell = n_entries("sell")
            n_cls  = n_closes()
            curr_price = float(c[i-1])

            # Same `n_cls == 0` guard as LONG branch — see comment above.
            if n_sell == 1 and n_cls == 0:
                move_pct = (engine.avg_cost - curr_price) / engine.avg_cost
                if move_pct >= pyr_th:
                    pyramid_size = engine._fills[0]["size"] * pyr_size
                    engine.sell(size=pyramid_size, signal="PYRAMID_SELL")
                    engine.set_exit(sl=engine.avg_cost * (1 + sl_pct))

            if engine.is_short and n_cls == 0 and l[i-1] <= engine.avg_cost * (1 - tp1_pct):
                engine.close(size=engine.qty * 0.5, signal="PARTIAL_TP1")
                engine.set_exit(
                    tp=engine.avg_cost * (1 - tp2_pct),
                    sl=engine.avg_cost * (1 + sl_pct),
                )

        # ── Initial entries ──
        # Only set SL initially. TP is set ONLY after the partial close (so the
        # engine's TP fires the final close at tp2, not tp1).
        if buy_sig[i-1]:
            if engine.is_short:
                engine.close(signal="Close Short")
            if engine.is_flat:
                engine.buy(signal="BUY")
                engine.set_exit(sl=engine.avg_cost * (1 - sl_pct))
        elif sell_sig[i-1]:
            if engine.is_long:
                engine.close(signal="Close Long")
            if engine.is_flat:
                engine.sell(signal="SELL")
                engine.set_exit(sl=engine.avg_cost * (1 + sl_pct))

    # Visualization
    return {
        "series": [
            {"name": "EMA fast", "type": "line", "pane": 0, "color": "#FF6D00", "lineWidth": 1, "data": ema_f},
            {"name": "EMA slow", "type": "line", "pane": 0, "color": "#2962FF", "lineWidth": 1, "data": ema_s},
            {"name": "SuperTrend", "type": "line", "pane": 0, "color": "#26A69A", "lineWidth": 1, "data": st_value},
        ]
    }
```

**Notes for the AI**:
- The pattern uses `engine._fills` to count entries / closes within the current trade (resets to `[]` when the trade goes flat via `_complete_trade`). This is acceptable — `_fills` is the canonical way to detect leg-state without external counters.
- The initial `engine.set_exit(sl=...)` has only SL. **Do not set `tp`** in the initial — the engine's TP fires a FULL close, which would skip the partial. Manual detection via `if h[i-1] >= avg*(1+tp1_pct)` is the only way to do partial close at a price level.
- After the partial close, `engine.set_exit(tp=tp2, sl=...)` is set so the engine auto-closes the remainder at tp2. That's safe because at that point the remainder is the only qty left — full close at tp2 is what we want.
- The `engine.is_long` re-check before the partial close branch is **mandatory**. Without it, when the pyramid's set_exit auto-closes intra-bar (e.g., if the bar's L crossed the new SL), the partial-close branch would call `engine.close(size=qty*0.5)` on a flat engine → `EngineError`.
- Use this template when the user requests pyramid, scale-in, scale-out, partial close, multi-leg trades, or any combination where the position should add legs intra-trade and exit in stages.

---

## Example 4 — DIY path-dependent indicator via `engine.persist` (Heikin-Ashi)

**Use case**: a path-dependent indicator the user requests is **NOT in the catalog** — neither pandas-ta safe (path-dependent) nor talipp 2.7.0 (gap). Canonical examples: Heikin-Ashi (any flavor), Renko bricks, custom hysteresis stops, regime detectors with cumulative volatility, session anchors. This template shows how to implement them correctly using `engine.persist` so they work uniformly in backtest and live (no sliding-window contamination).

**Why not pandas-ta `ta.ha()`**: pandas-ta computes HA from index 0 of the input array. In live, the input array is a sliding window — index 0 keeps moving. The HA_open of bar 0 would be `(open + close) / 2` of THAT bar, but the REAL HA_open at that moment depends on the entire session before the window. Result: HA values drift between ticks, signals fire at wrong times. The DIY pattern below caches HA values keyed by `open_time`, computed cumulatively, so they stay correct across sliding windows.

**Strategy logic** (illustrative — adapt to user's actual ask):
- HA color flip from red to green (HA close > HA open after being below) → BUY.
- HA color flip from green to red → SELL.
- TP/SL fixed percentage.

```python
import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict, Any

# No talipp imports — this strategy uses a DIY path-dependent indicator instead.

# ────────────────────────────────────────────────────────────────
# 1. PARAMETERS
# ────────────────────────────────────────────────────────────────
strategy_parameters: Dict[str, Any] = {
    "takeProfitPerc":  1.5,
    "stopLossPerc":    0.8,
}

strategy_options: Dict[str, Any] = {}
auxiliary_datasets: Dict[str, str] = {}

warmup_spec: Dict[str, Any] = {
    "simple_windows": [],
    "wilder_lengths": [],
    "epsilon": 0.001,
}


# ────────────────────────────────────────────────────────────────
# 2. MAIN FUNCTION
# ────────────────────────────────────────────────────────────────
def trading_strategy(
    data: pd.DataFrame,
    data_aux: Dict[str, pd.DataFrame],
    params: Dict[str, Any],
    capital_cfg: Dict[str, Any],
    engine,
) -> Dict[str, Any]:

    tp_pct = float(params["takeProfitPerc"]) / 100.0
    sl_pct = float(params["stopLossPerc"])  / 100.0

    # NumPy extraction
    o = data["open"].values
    h = data["high"].values
    l = data["low"].values
    c = data["close"].values
    tms = (data["time"] if "time" in data.columns else data["open_time"]).values
    n = len(data)

    # ── DIY path-dependent indicator via engine.persist ──
    # Cache HA values keyed by open_time. In live, the same bar's HA persists
    # across ticks (forming bar overrides itself, closed bars stay).
    # In backtest the cache is fresh per call (engine.custom resets).
    ha_cache: Dict[int, tuple] = engine.persist(
        "ha_cache",
        factory=lambda: {},
    )

    # 1) Seed: if first bar in window has no cached HA, compute from scratch.
    #    "From scratch" means HA_open[0] = (o[0]+c[0])/2 — the standard HA seed.
    #    In live this only happens on the very first tick (cold start).
    t0 = int(tms[0])
    if t0 not in ha_cache:
        ha_close_0 = (o[0] + h[0] + l[0] + c[0]) / 4.0
        ha_open_0  = (o[0] + c[0]) / 2.0
        ha_high_0  = max(h[0], ha_open_0, ha_close_0)
        ha_low_0   = min(l[0], ha_open_0, ha_close_0)
        ha_cache[t0] = (ha_open_0, ha_high_0, ha_low_0, ha_close_0)

    # 2) For each subsequent bar in window: if not cached, compute cumulatively
    #    from the previous bar's HA. If cached, leave it (it's a closed bar
    #    we've seen before in a prior tick).
    for i in range(1, n):
        t_curr = int(tms[i])
        t_prev = int(tms[i-1])
        if t_curr in ha_cache:
            continue
        prev_ha = ha_cache.get(t_prev)
        if prev_ha is None:
            # Edge case: prev bar not cached (gap in the data). Seed from scratch.
            ha_open_i  = (o[i] + c[i]) / 2.0
        else:
            prev_ha_open, _, _, prev_ha_close = prev_ha
            ha_open_i  = (prev_ha_open + prev_ha_close) / 2.0
        ha_close_i = (o[i] + h[i] + l[i] + c[i]) / 4.0
        ha_high_i  = max(h[i], ha_open_i, ha_close_i)
        ha_low_i   = min(l[i], ha_open_i, ha_close_i)
        ha_cache[t_curr] = (ha_open_i, ha_high_i, ha_low_i, ha_close_i)

    # 3) The FORMING bar (last one) MUST be re-computed every tick — its OHLC
    #    changes within the same minute as new ticks come in. Override the cache.
    t_form = int(tms[n-1])
    prev_ha = ha_cache.get(int(tms[n-2])) if n > 1 else None
    if prev_ha is not None:
        prev_ha_open, _, _, prev_ha_close = prev_ha
        ha_open_form = (prev_ha_open + prev_ha_close) / 2.0
    else:
        ha_open_form = (o[n-1] + c[n-1]) / 2.0
    ha_close_form = (o[n-1] + h[n-1] + l[n-1] + c[n-1]) / 4.0
    ha_high_form  = max(h[n-1], ha_open_form, ha_close_form)
    ha_low_form   = min(l[n-1], ha_open_form, ha_close_form)
    ha_cache[t_form] = (ha_open_form, ha_high_form, ha_low_form, ha_close_form)

    # 4) Trim cache to bounded size — keep only entries for bars in the current
    #    window plus a small buffer. Without trimming, the cache grows unbounded
    #    in live (memory leak after days of running).
    keep_keys = set(int(t) for t in tms)
    for k in list(ha_cache.keys()):
        if k not in keep_keys:
            del ha_cache[k]

    # 5) Build aligned NumPy arrays for vectorized signal computation.
    ha_open  = np.array([ha_cache[int(t)][0] for t in tms], dtype=np.float64)
    ha_high  = np.array([ha_cache[int(t)][1] for t in tms], dtype=np.float64)
    ha_low   = np.array([ha_cache[int(t)][2] for t in tms], dtype=np.float64)
    ha_close = np.array([ha_cache[int(t)][3] for t in tms], dtype=np.float64)

    # ── Signals: HA color flip ──
    # Green candle: HA_close > HA_open. Red candle: HA_close < HA_open.
    is_green       = ha_close > ha_open
    is_red         = ha_close < ha_open
    flip_to_green  = np.r_[False, is_green[1:] & is_red[:-1]]
    flip_to_red    = np.r_[False, is_red[1:]   & is_green[:-1]]

    # ── Bar loop ──
    for i in range(1, n):
        engine.on_bar(
            bar=(float(o[i]), float(h[i]), float(l[i]), float(c[i])),
            time=int(tms[i]),
        )

        # Entries — only when flat
        if flip_to_green[i-1] and engine.is_flat:
            engine.buy(signal="HA_FLIP_GREEN")
            engine.set_exit(
                tp=engine.avg_cost * (1 + tp_pct),
                sl=engine.avg_cost * (1 - sl_pct),
            )
        elif flip_to_red[i-1] and engine.is_flat:
            engine.sell(signal="HA_FLIP_RED")
            engine.set_exit(
                tp=engine.avg_cost * (1 - tp_pct),
                sl=engine.avg_cost * (1 + sl_pct),
            )

    # ── Visualization ──
    return {
        "series": [
            {"name": "HA Open",  "type": "line", "pane": 0, "color": "#999999", "lineWidth": 1, "data": ha_open},
            {"name": "HA Close", "type": "line", "pane": 0, "color": "#26A69A", "lineWidth": 2, "data": ha_close},
        ]
    }
```

### How to adapt this pattern to other path-dependent indicators

The DIY pattern has **5 stages** that map to any custom path-dependent indicator:

1. **Persist a cache via `engine.persist`** keyed by `open_time` (or by sequence number, or a state dict — whatever your indicator needs). The factory returns a fresh empty container.
2. **Seed**: if the first bar in the window has no cached value, compute it from scratch using the indicator's "session start" rule (for HA: `HA_open = (o + c) / 2`).
3. **Cumulative fill**: walk bars 1..n-1; for each bar without a cached value, compute it from the PREVIOUS bar's cached value using the indicator's recursion formula (for HA: `HA_open = (prev_HA_open + prev_HA_close) / 2`).
4. **Forming bar override**: the last bar in the window is "forming" in live and updates intra-tick. Always recompute its values fresh, overriding any prior cache entry for that timestamp.
5. **Cache trim**: delete entries for timestamps no longer in the window. Without this, live runs accumulate memory unbounded over days.

Then build `ha_open`, `ha_high`, etc. NumPy arrays from the cache, aligned to `tms`, and use them in vectorized signal logic just like any other indicator.

### When to use this DIY pattern

- The user requests a path-dependent indicator NOT in the catalog and NOT in talipp 2.7.0.
- Examples: Heikin-Ashi, Heikin-Ashi smoothed, Renko bricks, ATR-trailing stops with hysteresis (custom logic beyond `engine.set_exit`), session anchors, regime detectors built from cumulative volatility.
- For Renko specifically, the cached value per bar is the brick state (price, direction); the recursion is "if abs(close - last_brick_price) >= brick_size, emit a brick".
- For custom trailing stops with hysteresis (e.g., "tighten only if N consecutive bars closed favorably"), the cached value is the (current_stop_level, consecutive_favorable_count) tuple.

### Anti-patterns

- ❌ Using `ta.ha()` from pandas-ta directly. Computes from index 0 of the input array — in live the index 0 keeps shifting, HA drifts.
- ❌ Persisting only the LAST HA values (not a per-bar cache). Sufficient if signals look at the latest bar only, but breaks for vectorized signals over the window.
- ❌ Forgetting the cache trim. Memory grows linearly with deploy duration.
- ❌ Forgetting to override the forming bar each tick. The HA values for the forming bar would freeze with stale OHLC data.

---

## Quick decision guide for the AI

| User request mentions... | Template to use |
|---|---|
| Just RSI, ATR, ADX, MACD, BB, SMA/EMA, Stoch, ROC, MFI, Williams%R, CCI, Momentum | Example 1 |
| SuperTrend, ParabolicSAR, OBV, VWAP (talipp), ZigZag, Ichimoku, A/D, Chaikin Osc, KAMA, McGinley, ChandeKrollStop, PivotsHL | Example 2 |
| Pyramid, scale-in, partial close, multi-leg, average up/down, take profit in stages | Example 3 |
| Heikin-Ashi (any flavor), Renko, smoothed HA, custom hysteresis stops, ad-hoc cumulative state | **Example 4 (DIY path-dependent recipe)** |
| A mix of pandas-ta and talipp catalog indicators without multi-leg | Example 2 (extend with the user's specific indicators) |

**For ANY indicator NOT in the catalog**: don't search for "alternatives" via tool calls. Either it's a catalog convergent → pandas-ta from the catalog, or path-dependent + missing → Example 4 DIY recipe. The catalog is the default surface area; going beyond requires explicit user instruction.

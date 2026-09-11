# talipp Reference
> **Auto-generated** from introspection of `talipp==2.7.0` installed in the project venv.
> Pinned version: `talipp==2.7.0`. If the version upgrades, re-run `tools/build_talipp_reference.py` to refresh.
> Last regeneration: see file timestamp.

## When to use talipp vs pandas-ta

MSF uses two indicator engines side by side:
- **pandas-ta inline** (vectorized, batch) for **convergent** indicators — values stabilize from a fixed window of past data. RSI, ATR, ADX, MACD, BB, SMA/EMA, Stoch, ROC, etc.
- **talipp** (incremental, stateful) for **path-dependent** indicators — values depend on the entire history since session/series start. Sliding windows would corrupt them.

The decision matrix:

| Indicator type | Engine | Why |
|---|---|---|
| Trend (path-dependent): SuperTrend, ParabolicSAR, ZigZag, KAMA, Ichimoku Senkou, McGinley Dynamic | **talipp** | State accumulates across history; sliding window resets it. |
| Volume (cumulative): OBV, AccuDist, ChaikinOsc, SOBV, ForceIndex, KVO | **talipp** | Cumulative sums from session start; full history needed. |
| Momentum (convergent): RSI, MACD, ROC, Stoch, CCI, MFI, Williams, AO, KST, TRIX, TSI, UO | **pandas-ta** | Vectorized, faster, no path dependency. talipp also exposes them. |
| Volatility (convergent): ATR, BB, NATR, Keltner, Donchian, MeanDev, StdDev, ChandeKrollStop | **pandas-ta** | Vectorized. talipp also exposes them. |
| Trend (convergent): SMA, EMA, WMA, DEMA, TEMA, HMA, ALMA, VWMA, ZLEMA, T3, SMMA | **pandas-ta** | Vectorized. talipp also exposes them. |

**Default rule**: if the user asks for a path-dependent indicator (SuperTrend, ParabolicSAR, OBV, ZigZag, AccuDist, etc.), you MUST use talipp + `engine.persist`. Implementing as pandas-ta vectorized passes backtest and breaks live (sliding window resets state every tick).

---

## Canonical pattern (mandatory for every talipp indicator)

```python
# Imports — ONLY when using talipp in this strategy
from talipp.indicators import SuperTrend
from talipp.indicators.SuperTrend import Trend  # output enum (per-indicator if applicable)
from talipp.ohlcv import OHLCV                  # input type for OHLCV-based indicators

# Output `.trend` fields are an ENUM (`Trend.UP` / `Trend.DOWN`), NOT a string.
# ❌ `v.trend == "up"`  → always False → no flips → 0 trades (silent, no error).
# ✅ `v.trend == Trend.UP`  (import Trend from the indicator's module, as above).

def trading_strategy(data, data_aux, params, capital_cfg, engine):

    # 1) Persist via engine.persist (NEVER instantiate at module level — validator rejects)
    st = engine.persist(
        "st_obj",
        factory=lambda: SuperTrend(atr_period=int(params["atr_period"]),
                                   mult=float(params["atr_multiplier"])),
    )
    state = engine.persist("st_state", factory=lambda: {"last_t": -1})

    # 2) NumPy extraction
    o = data["open"].values; h = data["high"].values
    l = data["low"].values;  c = data["close"].values
    tms = (data["time"] if "time" in data.columns else data["open_time"]).values
    n = len(data)

    # 3) Window-slid guard (defensive code for live anomalies)
    last_t = state["last_t"]
    if last_t > 0:
        new_idx_check = int(np.searchsorted(tms, last_t, side="right"))
        if new_idx_check == 0:
            engine.custom.pop("st_obj", None)
            engine.custom.pop("st_state", None)
            st = engine.persist("st_obj", factory=lambda: SuperTrend(...))
            state = engine.persist("st_state", factory=lambda: {"last_t": -1})
            last_t = -1

    # 4) Feed talipp — CLOSED BARS ONLY. The forming bar (data.iloc[n-1]) is
    #    NEVER fed to any path-dependent indicator. See runtime_constraints.md §11.
    n_closed = n - 1
    if last_t < 0:
        for i in range(n_closed):           # NOT range(n)
            st.add(OHLCV(open=float(o[i]), high=float(h[i]),
                         low=float(l[i]), close=float(c[i])))
        if n_closed > 0:
            state["last_t"] = int(tms[n_closed - 1])
    else:
        new_idx = int(np.searchsorted(tms[:n_closed], last_t, side="right"))
        if new_idx < n_closed:
            for i in range(new_idx, n_closed):
                st.add(OHLCV(open=float(o[i]), high=float(h[i]),
                             low=float(l[i]), close=float(c[i])))
            state["last_t"] = int(tms[n_closed - 1])
        # else: no new closed bars — no-op. NEVER st.update(forming_bar).

    # 5) Build aligned NumPy arrays — MANDATORY padding + forming-bar slot.
    #    output_values has length n_closed. We append None for the forming
    #    bar so the final array has length n (aligned with `data`).
    raw = list(st.output_values)             # length = n_closed
    if len(raw) < n_closed:
        raw = [None] * (n_closed - len(raw)) + raw    # warmup pad
    else:
        raw = raw[-n_closed:]
    raw.append(None)                          # forming bar slot

    # 6) Convert to NumPy. None entries (warmup + forming) become np.nan.
    trend_arr = np.array([
        (1.0 if v.trend == Trend.UP else -1.0) if v is not None else np.nan
        for v in raw
    ], dtype=np.float64)
    # Bar loop reads trend_arr[i-1] (PREVIOUS bar's value). For i in [1, n),
    # trend_arr[i-1] is always a closed-bar value (or NaN during warmup).
    # The forming bar's NaN at trend_arr[n-1] is intentional and never used
    # for an entry decision — entries are made on `flip_up[i-1]` etc., which
    # read closed-bar trend values.
```

**Critical rules**:
- Talipp objects are **instantiated inside `trading_strategy()` via `engine.persist`** — never at module level. The code validator rejects module-level instantiation.
- Pair every talipp object with a state dict tracking `last_t` for the add+update pattern.
- The window-slid guard handles live edge cases. Include it always — keeps code uniform across backtest/live.
- **The forming bar is NEVER fed to a path-dependent indicator** — neither via `add()` NOR via `update()`. Iterate up to `n_closed = n - 1`, not `n`. See `runtime_constraints.md §11` for the full rationale (path-dependent state drift across many partial-OHLC `update()` calls breaks BT↔live parity).
- The padding pattern is **MANDATORY** and now ALWAYS terminates in `raw.append(None)` to add the forming-bar slot. The final array has length `n`, indexable as `arr[i]` for `i in [0, n)`. `arr[n-1]` is the forming bar's slot and always `NaN`.

---

## Input types

**`OHLCV` dataclass** — for indicators that need OHLC (and optionally volume):
```python
from talipp.ohlcv import OHLCV
ind.add(OHLCV(open=float(o[i]), high=float(h[i]),
              low=float(l[i]), close=float(c[i]),
              volume=float(v[i])))   # volume optional
```

**`float` scalar** — for indicators that only need close:
```python
ind.add(float(c[i]))
```

The reference below tags each indicator's input type from runtime introspection.

---

## Indicators

The list below is auto-generated from `dir(talipp.indicators)` in talipp 2.7.0. Each entry shows:
- **Constructor signature** as introspected from `__init__`.
- **Input type** (probed by feeding `OHLCV` then `float` and seeing what works).
- **Output type** (captured by feeding 60 dummy bars and inspecting `output_values[-1]`).
- For dataclass outputs, the field names.
- **Description** from the official talipp README when available.



## Trend / Path-Dependent (use talipp)

### ChandeKrollStop

**Constructor**: `ChandeKrollStop(atr_period: int, atr_mult: float, period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `ChandeKrollStopVal` dataclass with fields: `.short_stop`, `.long_stop`

```python
from talipp.indicators import ChandeKrollStop

ind = engine.persist("chandekrollstop", factory=lambda: ChandeKrollStop(atr_period=14, atr_mult=2.0, period=14))
state = engine.persist("chandekrollstop_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### FibonacciRetracement

**Constructor**: `FibonacciRetracement()`
**Input**: ⚠ unknown (introspection probe failed)
**Output**: ⚠ unknown (no .add method — not a streaming indicator (likely a one-shot calculator))

> ⚠ **Introspection note**: no .add method — not a streaming indicator (likely a one-shot calculator)

```python
from talipp.indicators import FibonacciRetracement

ind = engine.persist("fibonacciretracement", factory=lambda: FibonacciRetracement())
state = engine.persist("fibonacciretracement_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(...)  # ⚠ verify input type
```


---

### Ichimoku

**Constructor**: `Ichimoku(kijun_period: int, tenkan_period: int, chikou_lag_period: int, senkou_slow_period: int, senkou_lookup_period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `IchimokuVal` dataclass with fields: `.base_line`, `.conversion_line`, `.lagging_line`, `.cloud_leading_fast_line`, `.cloud_leading_slow_line`

```python
from talipp.indicators import Ichimoku

ind = engine.persist("ichimoku", factory=lambda: Ichimoku(kijun_period=14, tenkan_period=14, chikou_lag_period=14, senkou_slow_period=14, senkou_lookup_period=14))
state = engine.persist("ichimoku_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### KAMA

**Constructor**: `KAMA(period: int, fast_ema_constant_period: int, slow_ema_constant_period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 119.4551)

```python
from talipp.indicators import KAMA

ind = engine.persist("kama", factory=lambda: KAMA(period=14, fast_ema_constant_period=14, slow_ema_constant_period=14))
state = engine.persist("kama_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### McGinleyDynamic

**Constructor**: `McGinleyDynamic(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 123.5313)

```python
from talipp.indicators import McGinleyDynamic

ind = engine.persist("mcginleydynamic", factory=lambda: McGinleyDynamic(period=14))
state = engine.persist("mcginleydynamic_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### ParabolicSAR

**Constructor**: `ParabolicSAR(init_accel_factor: float, accel_factor_inc: float, max_accel_factor: float, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `ParabolicSARVal` dataclass with fields: `.value`, `.trend`, `.ep`, `.accel_factor`
`.trend` is the `Trend` enum (`Trend.UP`/`Trend.DOWN`) — compare `v.trend == Trend.UP`, NOT `== "up"` (string compare is always False → 0 trades). Import: `from talipp.indicators.ParabolicSAR import Trend`.

```python
from talipp.indicators import ParabolicSAR
from talipp.indicators.ParabolicSAR import Trend

ind = engine.persist("parabolicsar", factory=lambda: ParabolicSAR(init_accel_factor=0.02, accel_factor_inc=0.02, max_accel_factor=0.20))
state = engine.persist("parabolicsar_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### PivotsHL

**Constructor**: `PivotsHL(high_period: int, low_period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `PivotsHLVal` dataclass with fields: `.ohlcv`, `.type`

```python
from talipp.indicators import PivotsHL

ind = engine.persist("pivotshl", factory=lambda: PivotsHL(high_period=14, low_period=14))
state = engine.persist("pivotshl_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### SuperTrend

**Constructor**: `SuperTrend(atr_period: int, mult: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `SuperTrendVal` dataclass with fields: `.value`, `.trend`

```python
from talipp.indicators import SuperTrend

ind = engine.persist("supertrend", factory=lambda: SuperTrend(atr_period=14, mult=2.0))
state = engine.persist("supertrend_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### ZigZag

**Constructor**: `ZigZag(sensitivity: float, min_trend_length: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `ZigZagVal` dataclass with fields: `.ohlcv`, `.type`

```python
from talipp.indicators import ZigZag

ind = engine.persist("zigzag", factory=lambda: ZigZag(sensitivity=14, min_trend_length=14))
state = engine.persist("zigzag_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---


## Volume / Cumulative (use talipp)

### AccuDist

**Constructor**: `AccuDist(input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 0.0000)

```python
from talipp.indicators import AccuDist

ind = engine.persist("accudist", factory=lambda: AccuDist())
state = engine.persist("accudist_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### ChaikinOsc

**Constructor**: `ChaikinOsc(fast_period: int, slow_period: int, ma_type: MAType = <MAType.EMA: 3>, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 0.0000)

```python
from talipp.indicators import ChaikinOsc

ind = engine.persist("chaikinosc", factory=lambda: ChaikinOsc(fast_period=14, slow_period=14))
state = engine.persist("chaikinosc_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### EMV

*Ease of Movement*


**Constructor**: `EMV(period: int, volume_div: int, ma_type: MAType = <MAType.SMA: 6>, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 0.0014)

```python
from talipp.indicators import EMV

ind = engine.persist("emv", factory=lambda: EMV(period=14, volume_div=14))
state = engine.persist("emv_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### ForceIndex

**Constructor**: `ForceIndex(period: int, ma_type: MAType = <MAType.EMA: 3>, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 100.0000)

```python
from talipp.indicators import ForceIndex

ind = engine.persist("forceindex", factory=lambda: ForceIndex(period=14))
state = engine.persist("forceindex_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### KVO

*Klinger Volume Oscillator*


**Constructor**: `KVO(fast_period: int, slow_period: int, ma_type: MAType = <MAType.EMA: 3>, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 0.0000)

```python
from talipp.indicators import KVO

ind = engine.persist("kvo", factory=lambda: KVO(fast_period=14, slow_period=14))
state = engine.persist("kvo_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### OBV

*On-balance Volume*


**Constructor**: `OBV(input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 250000.0000)

```python
from talipp.indicators import OBV

ind = engine.persist("obv", factory=lambda: OBV())
state = engine.persist("obv_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### SOBV

**Constructor**: `SOBV(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 243500.0000)

```python
from talipp.indicators import SOBV

ind = engine.persist("sobv", factory=lambda: SOBV(period=14))
state = engine.persist("sobv_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### VWAP

*Volume Weighted Average Price*


**Constructor**: `VWAP(input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 112.4500)

```python
from talipp.indicators import VWAP

ind = engine.persist("vwap", factory=lambda: VWAP())
state = engine.persist("vwap_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### VWMA

**Constructor**: `VWMA(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 124.2500)

```python
from talipp.indicators import VWMA

ind = engine.persist("vwma", factory=lambda: VWMA(period=14))
state = engine.persist("vwma_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---


## Momentum (convergent — talipp also offered)

### AO

*Awesome Oscillator*


**Constructor**: `AO(fast_period: int, slow_period: int, ma_type: MAType = <MAType.SMA: 6>, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 0.0000)

```python
from talipp.indicators import AO

ind = engine.persist("ao", factory=lambda: AO(fast_period=14, slow_period=14))
state = engine.persist("ao_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### Aroon

**Constructor**: `Aroon(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `AroonVal` dataclass with fields: `.up`, `.down`

```python
from talipp.indicators import Aroon

ind = engine.persist("aroon", factory=lambda: Aroon(period=14))
state = engine.persist("aroon_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### BOP

*Balance of Power*


**Constructor**: `BOP(input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 0.0000)

```python
from talipp.indicators import BOP

ind = engine.persist("bop", factory=lambda: BOP())
state = engine.persist("bop_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### CCI

*Commodity Channel Index*


**Constructor**: `CCI(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 123.8095)

```python
from talipp.indicators import CCI

ind = engine.persist("cci", factory=lambda: CCI(period=14))
state = engine.persist("cci_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### CoppockCurve

**Constructor**: `CoppockCurve(fast_roc_period: int, slow_roc_period: int, wma_period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 2.2752)

```python
from talipp.indicators import CoppockCurve

ind = engine.persist("coppockcurve", factory=lambda: CoppockCurve(fast_roc_period=14, slow_roc_period=14, wma_period=14))
state = engine.persist("coppockcurve_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### DPO

*Detrended Price Oscillator*


**Constructor**: `DPO(period: int, ma_type: MAType = <MAType.SMA: 6>, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. -0.1500)

```python
from talipp.indicators import DPO

ind = engine.persist("dpo", factory=lambda: DPO(period=14))
state = engine.persist("dpo_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### IBS

**Constructor**: `IBS(input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 0.5000)

```python
from talipp.indicators import IBS

ind = engine.persist("ibs", factory=lambda: IBS())
state = engine.persist("ibs_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### KST

*Know Sure Thing*


**Constructor**: `KST(roc1_period: int, roc1_ma_period: int, roc2_period: int, roc2_ma_period: int, roc3_period: int, roc3_ma_period: int, roc4_period: int, roc4_ma_period: int, signal_period: int, ma_type: MAType = <MAType.SMA: 6>, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `KSTVal` dataclass with fields: `.kst`, `.signal`

```python
from talipp.indicators import KST

ind = engine.persist("kst", factory=lambda: KST(roc1_period=14, roc1_ma_period=14, roc2_period=14, roc2_ma_period=14, roc3_period=14, roc3_ma_period=14, roc4_period=14, roc4_ma_period=14, signal_period=14))
state = engine.persist("kst_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### MACD

*Moving Average Convergence Divergence*


**Constructor**: `MACD(fast_period: int, slow_period: int, signal_period: int, ma_type: MAType = <MAType.EMA: 3>, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `MACDVal` dataclass with fields: `.macd`, `.signal`, `.histogram`

```python
from talipp.indicators import MACD

ind = engine.persist("macd", factory=lambda: MACD(fast_period=14, slow_period=14, signal_period=14))
state = engine.persist("macd_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### ROC

*Rate of Change*


**Constructor**: `ROC(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 1.1336)

```python
from talipp.indicators import ROC

ind = engine.persist("roc", factory=lambda: ROC(period=14))
state = engine.persist("roc_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### RSI

*Relative strength index*


**Constructor**: `RSI(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 100.0000)

```python
from talipp.indicators import RSI

ind = engine.persist("rsi", factory=lambda: RSI(period=14))
state = engine.persist("rsi_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### STC

*Schaff Trend Cycle*


**Constructor**: `STC(fast_macd_period: int, slow_macd_period: int, stoch_period: int, stoch_smoothing_period: int, stoch_ma_type: MAType = <MAType.SMA: 6>, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 100.0000)

```python
from talipp.indicators import STC

ind = engine.persist("stc", factory=lambda: STC(fast_macd_period=14, slow_macd_period=14, stoch_period=14, stoch_smoothing_period=14))
state = engine.persist("stc_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### Stoch

**Constructor**: `Stoch(period: int, smoothing_period: int, ma_type: MAType = <MAType.SMA: 6>, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `StochVal` dataclass with fields: `.k`, `.d`

```python
from talipp.indicators import Stoch

ind = engine.persist("stoch", factory=lambda: Stoch(period=14, smoothing_period=14))
state = engine.persist("stoch_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### StochRSI

**Constructor**: `StochRSI(rsi_period: int, stoch_period: int, k_smoothing_period: int, d_smoothing_period: int, ma_type: MAType = <MAType.SMA: 6>, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `StochRSIVal` dataclass with fields: `.k`, `.d`

```python
from talipp.indicators import StochRSI

ind = engine.persist("stochrsi", factory=lambda: StochRSI(rsi_period=14, stoch_period=14, k_smoothing_period=14, d_smoothing_period=14))
state = engine.persist("stochrsi_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### TRIX

**Constructor**: `TRIX(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 8.1400)

```python
from talipp.indicators import TRIX

ind = engine.persist("trix", factory=lambda: TRIX(period=14))
state = engine.persist("trix_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### TSI

*True Strength Index*


**Constructor**: `TSI(fast_period: int, slow_period: int, ma_type: MAType = <MAType.EMA: 3>, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 100.0000)

```python
from talipp.indicators import TSI

ind = engine.persist("tsi", factory=lambda: TSI(fast_period=14, slow_period=14))
state = engine.persist("tsi_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### UO

*Ultimate Oscillator*


**Constructor**: `UO(fast_period: int, mid_period: int, slow_period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 50.0000)

```python
from talipp.indicators import UO

ind = engine.persist("uo", factory=lambda: UO(fast_period=14, mid_period=14, slow_period=14))
state = engine.persist("uo_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### VTX

*Vortex Indicator*


**Constructor**: `VTX(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `VTXVal` dataclass with fields: `.plus_vtx`, `.minus_vtx`

```python
from talipp.indicators import VTX

ind = engine.persist("vtx", factory=lambda: VTX(period=14))
state = engine.persist("vtx_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### Williams

**Constructor**: `Williams(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. -21.7391)

```python
from talipp.indicators import Williams

ind = engine.persist("williams", factory=lambda: Williams(period=14))
state = engine.persist("williams_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---


## Volatility (convergent — talipp also offered)

### ATR

*Average True Range*


**Constructor**: `ATR(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 1.0000)

```python
from talipp.indicators import ATR

ind = engine.persist("atr", factory=lambda: ATR(period=14))
state = engine.persist("atr_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### BB

*Bollinger Bands*


**Constructor**: `BB(period: int, std_dev_mult: float, ma_type: MAType = <MAType.SMA: 6>, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `BBVal` dataclass with fields: `.lb`, `.cb`, `.ub`

```python
from talipp.indicators import BB

ind = engine.persist("bb", factory=lambda: BB(period=14, std_dev_mult=2.0))
state = engine.persist("bb_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### CHOP

*Choppiness Index*


**Constructor**: `CHOP(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 68.4391)

```python
from talipp.indicators import CHOP

ind = engine.persist("chop", factory=lambda: CHOP(period=14))
state = engine.persist("chop_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### DonchianChannels

**Constructor**: `DonchianChannels(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `DonchianChannelsVal` dataclass with fields: `.lb`, `.cb`, `.ub`

```python
from talipp.indicators import DonchianChannels

ind = engine.persist("donchianchannels", factory=lambda: DonchianChannels(period=14))
state = engine.persist("donchianchannels_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### KeltnerChannels

**Constructor**: `KeltnerChannels(ma_period: int, atr_period: int, atr_mult_up: float, atr_mult_down: float, ma_type: MAType = <MAType.EMA: 3>, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `KeltnerChannelsVal` dataclass with fields: `.lb`, `.cb`, `.ub`

```python
from talipp.indicators import KeltnerChannels

ind = engine.persist("keltnerchannels", factory=lambda: KeltnerChannels(ma_period=14, atr_period=14, atr_mult_up=2.0, atr_mult_down=2.0))
state = engine.persist("keltnerchannels_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### MassIndex

**Constructor**: `MassIndex(ma_period: int, ma_ma_period: int, ma_ratio_period: int, ma_type: MAType = <MAType.EMA: 3>, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 14.0000)

```python
from talipp.indicators import MassIndex

ind = engine.persist("massindex", factory=lambda: MassIndex(ma_period=14, ma_ma_period=14, ma_ratio_period=14))
state = engine.persist("massindex_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### MeanDev

**Constructor**: `MeanDev(period: int, ma_type: MAType = <MAType.SMA: 6>, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 0.3500)

```python
from talipp.indicators import MeanDev

ind = engine.persist("meandev", factory=lambda: MeanDev(period=14))
state = engine.persist("meandev_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### NATR

**Constructor**: `NATR(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 0.8006)

```python
from talipp.indicators import NATR

ind = engine.persist("natr", factory=lambda: NATR(period=14))
state = engine.persist("natr_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### RogersSatchell

**Constructor**: `RogersSatchell(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `float` scalar (e.g. 0.0057)

```python
from talipp.indicators import RogersSatchell

ind = engine.persist("rogerssatchell", factory=lambda: RogersSatchell(period=14))
state = engine.persist("rogerssatchell_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### SFX

**Constructor**: `SFX(atr_period: int, std_dev_period: int, std_dev_smoothing_period: int, ma_type: MAType = <MAType.SMA: 6>, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `SFXVal` dataclass with fields: `.atr`, `.std_dev`, `.ma_std_dev`

```python
from talipp.indicators import SFX

ind = engine.persist("sfx", factory=lambda: SFX(atr_period=14, std_dev_period=14, std_dev_smoothing_period=14))
state = engine.persist("sfx_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### StdDev

**Constructor**: `StdDev(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 0.4031)

```python
from talipp.indicators import StdDev

ind = engine.persist("stddev", factory=lambda: StdDev(period=14))
state = engine.persist("stddev_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### TTM

**Constructor**: `TTM(period: int, bb_std_dev_mult: float = 2, kc_atr_mult: float = 1.5, ma_type: MAType = <MAType.SMA: 6>, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `TTMVal` dataclass with fields: `.squeeze`, `.histogram`

```python
from talipp.indicators import TTM

ind = engine.persist("ttm", factory=lambda: TTM(period=14))
state = engine.persist("ttm_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---


## Trend (convergent — talipp also offered, pandas-ta default)

### ADX

*Average Directional Index*


**Constructor**: `ADX(di_period: int, adx_period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `OHLCV(open, high, low, close, volume)`
**Output**: `ADXVal` dataclass with fields: `.adx`, `.plus_di`, `.minus_di`

```python
from talipp.indicators import ADX

ind = engine.persist("adx", factory=lambda: ADX(di_period=14, adx_period=14))
state = engine.persist("adx_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(OHLCV(open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i])))
```


---

### ALMA

**Constructor**: `ALMA(period: int, offset: float, sigma: float, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 124.6423)

```python
from talipp.indicators import ALMA

ind = engine.persist("alma", factory=lambda: ALMA(period=14, offset=0.85, sigma=6.0))
state = engine.persist("alma_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### DEMA

**Constructor**: `DEMA(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 124.9000)

```python
from talipp.indicators import DEMA

ind = engine.persist("dema", factory=lambda: DEMA(period=14))
state = engine.persist("dema_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### EMA

**Constructor**: `EMA(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 124.2500)

```python
from talipp.indicators import EMA

ind = engine.persist("ema", factory=lambda: EMA(period=14))
state = engine.persist("ema_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### HMA

**Constructor**: `HMA(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 124.8667)

```python
from talipp.indicators import HMA

ind = engine.persist("hma", factory=lambda: HMA(period=14))
state = engine.persist("hma_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### SMA

**Constructor**: `SMA(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 124.2500)

```python
from talipp.indicators import SMA

ind = engine.persist("sma", factory=lambda: SMA(period=14))
state = engine.persist("sma_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### SMMA

**Constructor**: `SMMA(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 123.6000)

```python
from talipp.indicators import SMMA

ind = engine.persist("smma", factory=lambda: SMMA(period=14))
state = engine.persist("smma_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### T3

**Constructor**: `T3(period: int, factor: float = 0.7, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 124.3150)

```python
from talipp.indicators import T3

ind = engine.persist("t3", factory=lambda: T3(period=14))
state = engine.persist("t3_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### TEMA

**Constructor**: `TEMA(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 124.9000)

```python
from talipp.indicators import TEMA

ind = engine.persist("tema", factory=lambda: TEMA(period=14))
state = engine.persist("tema_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### WMA

**Constructor**: `WMA(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 124.4667)

```python
from talipp.indicators import WMA

ind = engine.persist("wma", factory=lambda: WMA(period=14))
state = engine.persist("wma_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---

### ZLEMA

**Constructor**: `ZLEMA(period: int, input_sampling: SamplingPeriodType = None)`
**Input**: `float` (typically the close price)
**Output**: `float` scalar (e.g. 124.8500)

```python
from talipp.indicators import ZLEMA

ind = engine.persist("zlema", factory=lambda: ZLEMA(period=14))
state = engine.persist("zlema_state", factory=lambda: {"last_t": -1})

# In the canonical add+update loop:
ind.add(float(c[i]))
```


---


## Common patterns

### Combining 2+ talipp objects in the same strategy

Use distinct `engine.persist` keys per object. Each gets its own state dict.

```python
st = engine.persist("st_obj",  factory=lambda: SuperTrend(atr_period=14, mult=3.0))
ps = engine.persist("psar",    factory=lambda: ParabolicSAR(af=0.02, af_step=0.02, af_max=0.20))
st_state = engine.persist("st_state",   factory=lambda: {"last_t": -1})
ps_state = engine.persist("psar_state", factory=lambda: {"last_t": -1})
```

### Talipp on auxiliary datasets

Same pattern, but use the auxiliary's `open_time` for tracking and feed `OHLCV` from `data_aux[<key>]`. Then align the auxiliary's output to the primary timeline via `searchsorted` for use in the primary bar loop.

### Anti-patterns

- ❌ **Module-level instantiation**: `_ST = SuperTrend(...)` at the top of the file. Code validator rejects.
- ❌ **No padding**: `raw = list(st.output_values)[-n:]` without the `if len(raw) < n: pad else: slice` branch. Passes backtest, breaks live.
- ❌ **Calling add() and update() out of order**: every bar calls exactly one. `update` before any `add` raises.
- ❌ **Mixing primary and auxiliary into the same talipp object**: each talipp instance accumulates state from one continuous time series.

---

## Verification before using a talipp indicator in code

This document is auto-generated. If a constructor signature doesn't match what you expected, prefer this document over your training memory. To re-verify a single indicator manually:

```bash
python -c "from talipp.indicators import <Name>; import inspect; print(inspect.signature(<Name>.__init__))"
```

Any class missing from this reference but present in `talipp.indicators` means the categorization mapping in `tools/build_talipp_reference.py` doesn't cover it — it'll appear under "Other / Uncategorized". Update the mapping when adding new indicators.

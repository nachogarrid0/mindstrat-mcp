# Indicator Visualization Format
> This document defines how MSF strategies declare indicator visualizations for the frontend charting system. Visualizations are declarative arrays projected onto the primary timeline.

## 1. Overview

`trading_strategy` returns a single value: `visualization_data`. When a strategy wants its indicators rendered on the chart, it returns a dictionary with a `"series"` key containing an array of series definitions.

```python
visualization_data = {
    "series": [
        { ... series definition ... },
        { ... series definition ... },
    ]
}
```

If the strategy has no indicators to chart, return an empty dict:
```python
visualization_data = {}
```

> **CRITICAL**: an MSF strategy returns ONLY `visualization_data` — not a tuple. The engine collects trades internally; there is no `trades` list and no `state` dict to return.
> **CRITICAL**: every series array must have **the same length as the primary `data` DataFrame**. Auxiliary-derived overlays (computed from `data_aux[...]`) must be projected onto the primary timeline (via `np.searchsorted`) before being placed in `visualization_data`.

---

## 2. Series Object Schema

Each object in the `"series"` array defines one visual element on the chart.

### Required Fields

| Field       | Type           | Description                                                          |
|-------------|----------------|----------------------------------------------------------------------|
| `name`      | `str`          | Display label. Must be unique within the strategy. Shown in the toggle panel. |
| `type`      | `str`          | Chart type: `"line"`, `"histogram"`, or `"area"`.                    |
| `pane`      | `int`          | Target pane index. `0` = overlay on the price chart, `1+` = separate sub-panes. |
| `color`     | `str`          | Hex color code (e.g. `"#2962FF"`). Users can override this in the UI. |
| `data`      | `np.ndarray`   | NumPy array of float values. **Must have the same length as the input DataFrame.** |

### Optional Fields

| Field       | Type           | Default | Description                                                    |
|-------------|----------------|---------|----------------------------------------------------------------|
| `lineWidth` | `int`          | `2`     | Line thickness in pixels. Use `1` for secondary lines, `2` for primary. |
| `levels`    | `list[dict]`   | `[]`    | Horizontal reference lines (e.g. RSI overbought/oversold). See section 4. |

### Example — Minimal Series
```python
{"name": "MA", "type": "line", "pane": 0, "color": "#FF6D00", "lineWidth": 2, "data": ma_array}
```

---

## 3. Pane System

The chart supports multiple panes (windows) stacked vertically.

| Pane | Usage | Examples |
|------|-------|----------|
| `0`  | **Price overlay** — drawn directly on the candlestick chart | Moving Averages, Bollinger Bands, SuperTrend lines |
| `1`  | First sub-pane below the price chart | RSI, Stochastic |
| `2`  | Second sub-pane | ADX, DI+, DI- |
| `3`  | Third sub-pane | ATR, Volume indicators |
| `N`  | Additional sub-panes as needed | Any custom oscillator |

### Rules
- Pane numbers don't need to be contiguous. The frontend maps them in sorted order.
- Multiple series can share the same pane (e.g. ADX, +DI, -DI all in pane 2).
- The main price pane (`0`) always gets 3x the vertical space; each sub-pane gets 1x.
- Each series appears as a toggleable entry in the Visual Indicators panel. Users can enable/disable and change colors.

---

## 4. Reference Levels

The `levels` array adds horizontal reference lines to a series' pane. Common use: RSI overbought/oversold thresholds, ADX strength threshold.

### Level Object Schema

| Field   | Type   | Required | Description                                      |
|---------|--------|----------|--------------------------------------------------|
| `value` | `float`| Yes      | Y-axis value where the line is drawn.            |
| `color` | `str`  | Yes      | Hex color code.                                  |
| `style` | `str`  | Yes      | Line style: `"solid"`, `"dashed"`, or `"dotted"`. |
| `label` | `str`  | No       | Short text label shown on the price axis (e.g. `"OB"`, `"OS"`, `"Threshold"`). |

### Example
```python
{
    "name": "RSI",
    "type": "line",
    "pane": 1,
    "color": "#2962FF",
    "lineWidth": 2,
    "data": rsi_array,
    "levels": [
        {"value": 70.0, "color": "#787B86", "style": "dashed", "label": "OB"},
        {"value": 30.0, "color": "#787B86", "style": "dashed", "label": "OS"},
    ],
}
```

---

## 5. Series Types

### `"line"` (default)
Standard line chart. Use for most indicators: RSI, MA, ADX, ATR, SuperTrend bands.

### `"histogram"`
Vertical bars from zero. Use for volume-like indicators, MACD histogram, momentum bars.
- Automatically uses volume-style price formatting.
- Color applies to all bars. For dual-color histograms (positive/negative), use two separate histogram series.

### `"area"`
Filled area between the line and zero. Use for filled oscillators or range visualization.

---

## 6. Data Array Requirements

### Length
The `data` array **MUST** have the same length as the input `data` DataFrame. The frontend maps each value to its corresponding candle by index position.

```python
# CORRECT: indicator computed on full DataFrame, same length, NaN preserved (becomes gap)
rsi = ta.rsi(data["close"], length=14)
rsi_arr = rsi.values  # Same length as data; warmup NaN → chart gap (see NaN Handling below)

# WRONG: sliced or filtered array
rsi_arr = rsi.dropna().values  # Shorter! Will misalign with candles
```

### NaN Handling
- **Pass NaN values through as-is** (e.g. raw `.values` from a pandas Series with leading NaN warmup entries). The backend pipeline filters NaN/Inf during serialization (`_process_series_visualization` → `_coerce_float`) and the frontend renders those positions as **gaps** in the chart line — exactly what you want for warmup bars.
- **DO NOT** apply `fillna(0)` or `np.nan_to_num(arr, nan=0.0)` before assigning to `data`. Those replace NaN with the numeric value `0.0`, which passes the backend filter as a valid point → the chart paints a **flat line at zero** for every warmup bar instead of a gap. This visibly distorts oscillators (RSI, Stoch) that don't reach zero, and corrupts the baseline of unbounded indicators (ATR, MACD).
- Mid-series NaN (gaps inside a populated indicator) is also valid — the chart simply skips those bars. If a mid-series gap is undesirable, fix the **upstream computation**, not the array.

### Type
- Must be a NumPy array (`np.ndarray`) or a list of numbers.
- Values must be numeric (`int` or `float`).

---

## 7. Complete Example

This example shows a strategy with RSI (sub-pane with levels), MA (price overlay), ADX system (shared sub-pane), SuperTrend bands (price overlay), and ATR (separate sub-pane).

```python
# After computing all indicators...
# Pass NaN through — backend filters to gaps for warmup bars (do NOT fillna(0)).

rsi_arr = rsi.values
ma = data["MA"].values
adx_arr = adx.values
plus = plus_di.values
minu = minus_di.values
up = st_upper.values
dn = st_lower.values
atr = atr_series.values

visualization_data: Dict[str, Any] = {
    "series": [
        # RSI in its own pane with OB/OS reference lines
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
        # Moving Average overlaid on price chart
        {"name": "MA", "type": "line", "pane": 0, "color": "#FF6D00", "lineWidth": 2, "data": ma},
        # ADX system — three lines sharing pane 2
        {
            "name": "ADX",
            "type": "line",
            "pane": 2,
            "color": "#E040FB",
            "lineWidth": 2,
            "data": adx_arr,
            "levels": [
                {"value": adx_threshold, "color": "#787B86", "style": "dashed", "label": "Threshold"},
            ],
        },
        {"name": "+DI", "type": "line", "pane": 2, "color": "#26A69A", "lineWidth": 1, "data": plus},
        {"name": "-DI", "type": "line", "pane": 2, "color": "#EF5350", "lineWidth": 1, "data": minu},
        # SuperTrend bands overlaid on price chart
        {"name": "ST Upper", "type": "line", "pane": 0, "color": "#EF5350", "lineWidth": 1, "data": up},
        {"name": "ST Lower", "type": "line", "pane": 0, "color": "#26A69A", "lineWidth": 1, "data": dn},
        # ATR in its own pane
        {"name": "ATR", "type": "line", "pane": 3, "color": "#FF9800", "lineWidth": 2, "data": atr},
    ]
}

return visualization_data
```

---

## 8. Common Patterns

### Overlay Indicator (pane 0)
Moving averages, Bollinger Bands, SuperTrend — anything that shares the price scale.
```python
{"name": "SMA 50", "type": "line", "pane": 0, "color": "#2196F3", "lineWidth": 2, "data": sma50}
```

### Bounded Oscillator (pane N with levels)
RSI, Stochastic, CCI — oscillators with known boundaries.
```python
{
    "name": "Stochastic %K",
    "type": "line",
    "pane": 1,
    "color": "#2962FF",
    "lineWidth": 2,
    "data": stoch_k,
    "levels": [
        {"value": 80, "color": "#787B86", "style": "dashed", "label": "OB"},
        {"value": 20, "color": "#787B86", "style": "dashed", "label": "OS"},
    ],
}
```

### Multi-Line Shared Pane
ADX + DI, MACD + Signal — related indicators in one pane.
```python
{"name": "MACD",   "type": "line",      "pane": 1, "color": "#2962FF", "lineWidth": 2, "data": macd_line},
{"name": "Signal", "type": "line",      "pane": 1, "color": "#FF6D00", "lineWidth": 1, "data": signal_line},
{"name": "Hist",   "type": "histogram", "pane": 1, "color": "#26A69A", "lineWidth": 1, "data": macd_hist},
```

### Unbounded Indicator (pane N, no levels)
ATR, volume-based indicators — no fixed reference lines.
```python
{"name": "ATR", "type": "line", "pane": 2, "color": "#FF9800", "lineWidth": 2, "data": atr}
```

---

## 9. Anti-Patterns & Common Errors

### Data Length Mismatch
```python
# WRONG: dropna changes array length → misaligns with candles
visualization_data = {"series": [{"data": rsi.dropna().values, ...}]}

# WRONG: fillna(0) preserves length but paints a false zero-line during warmup
# (backend treats 0.0 as a valid point — chart renders flat segment, not a gap)
visualization_data = {"series": [{"data": rsi.fillna(0).values, ...}]}

# CORRECT: raw .values preserves length AND NaN → backend filters NaN to gap
visualization_data = {"series": [{"data": rsi.values, ...}]}
```

### Missing `"series"` Key
```python
# WRONG: flat dict without "series" wrapper
visualization_data = {"RSI": rsi_arr, "MA": ma_arr}

# CORRECT: wrapped in "series" array
visualization_data = {"series": [{"name": "RSI", "data": rsi_arr, ...}]}
```

### Duplicate Names
```python
# WRONG: two series with same name — toggle will conflict
{"name": "Line", ...},
{"name": "Line", ...},

# CORRECT: unique descriptive names
{"name": "EMA 20", ...},
{"name": "EMA 50", ...},
```

### Incorrect Pane for Overlay
```python
# WRONG: putting MA in a sub-pane — scale won't match price
{"name": "MA", "pane": 1, ...}

# CORRECT: overlay on price chart
{"name": "MA", "pane": 0, ...}
```

### Non-Numeric Data
```python
# WRONG: string or boolean array
{"data": data["signal"].values, ...}  # Boolean array

# CORRECT: numeric values only (NaN allowed — renders as gap)
{"data": rsi.values, ...}
```

---

## 10. Auxiliary Dataset Overlays

When a strategy uses auxiliary datasets (`data_aux`) and wants to render aux-derived series on the primary chart, the values **must be projected onto the primary timeline** before being placed in `visualization_data`.

```python
# aux2_times / aux2_ema computed pre-loop from data_aux["dataset_2"]
projected = np.full(n, np.nan, dtype=np.float64)
for i in range(n):
    idx = int(np.searchsorted(aux2_times, tms[i], side="right")) - 1
    if idx >= 0:
        projected[i] = aux2_ema[idx]

visualization_data = {
    "series": [
        {"name": "Macro EMA", "type": "line", "pane": 0, "color": "#9C27B0", "lineWidth": 2, "data": projected},
    ]
}
```

- **REQUIRED**: `len(projected) == len(data)`. Never return raw auxiliary arrays — their length is different.
- **REQUIRED**: use `searchsorted(side="right") - 1` (point-in-time, no look-ahead).
- **ALLOWED**: leaving leading NaN values where the auxiliary had no data yet — the chart will simply skip those bars.

---

## 11. Backward Compatibility

- Strategies that return `visualization_data = {}` (empty dict) will render normally with no indicator overlays.
- The `{"series": [...]}` format is the only supported shape.
- Pane-0 series are rendered with the multi-pane system. The user can toggle each one independently from the Visual Indicators panel.

---

## 12. Quick Reference

```
visualization_data = {
    "series": [
        {
            "name":      str,           # REQUIRED — unique display name
            "type":      str,           # REQUIRED — "line" | "histogram" | "area"
            "pane":      int,           # REQUIRED — 0 = price overlay, 1+ = sub-pane
            "color":     str,           # REQUIRED — hex color "#RRGGBB"
            "data":      np.ndarray,    # REQUIRED — same length as input DataFrame
            "lineWidth": int,           # OPTIONAL — default 2
            "levels":    [              # OPTIONAL — horizontal reference lines
                {
                    "value": float,     # REQUIRED — y-axis position
                    "color": str,       # REQUIRED — hex color
                    "style": str,       # REQUIRED — "solid" | "dashed" | "dotted"
                    "label": str,       # OPTIONAL — axis label text
                },
            ],
        },
    ]
}
```

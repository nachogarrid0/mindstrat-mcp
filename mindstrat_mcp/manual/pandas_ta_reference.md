# Pandas-TA Library Reference (Unified)
> Generated from: indicators.json, events.json, utilities.json


# Category: Candle

# cdl_doji (Candle)
> Doji

**Signature**:
`cdl_doji (open_: Series, high: Series, low: Series, close: Series, length: Int=None, factor: IntFloat=None, scalar: IntFloat=None, asint: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `open_` (Series): open Series
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `factor` (float): Doji value. Default:100
- `scalar` (float): Scalar. Default:100
- `asint` (bool): Returns as Int. Default:True
- `offset` (int): Post shift. Default:0
- `naive` (bool): Prefills potential Doji; bodies that are less than a percentage,factor, of it's High-Low range. Default:False
- `fillna` (value): Replaces na's with value.

## Returns
- Series: 1 column

---

# cdl_inside (Candle)
> Inside Bar

**Signature**:
`cdl_inside (open_: Series, high: Series, low: Series, close: Series, asbool: bool=None, scalar: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `open_` (Series): open Series
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `asbool` (bool): Return booleans. Default:False
- `scalar` (float): Scalar. Default:100
- `offset` (int): Post shift. Default:0
- `fillna` (value): Replaces na's with value.

## Returns
- Series: 1 column

---

# cdl_pattern (Candle)
> Candle Pattern

**Signature**:
`cdl_pattern (open_: Series, high: Series, low: Series, close: Series, name: str | List [ str ]="all", scalar: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `open_` (Series): open Series
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `name` (str|List[str]): Pattern name or a list of pattern names. Default:"all" (default: 'all')
- `scalar` (float): Scalar. Default:100
- `offset` (int): Post shift. Default:0
- `fillna` (value): Replaces na's with value.

## Returns
- DataFrame: Pattern Column(s)

---

# cdl_z (Candle)
> Z Candles

**Signature**:
`cdl_z (open_: Series, high: Series, low: Series, close: Series, length: Int=None, full: bool=None, ddof: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `open_` (Series): open Series
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `full` (bool): Applylengthto whole Data Frame. Default:False
- `ddof` (int): By default, uses Pandasddof=1. For Numpy calculation, use0. Default:1
- `offset` (int): Post shift. Default:0
- `naive` (bool): If True, prefills potential Doji less than the length if it less than a percentage of it's High-Low range. Default:False
- `fillna` (value): Replaces na's with value.

## Returns
- DataFrame: 4 columns

---

# ha (Candle)
> Heikin Ashi Candles

**Signature**:
`ha (open_: Series, high: Series, low: Series, close: Series, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `open_` (Series): open Series
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `offset` (int): Post shift. Default:0
- `fillna` (value): Replaces na's with value.

## Returns
- DataFrame: 4 columns

---


# Category: Candles

# candle_color (Candles)
> Candle Change

**Signature**:
`candle_color (open_: Series, close: Series) -> Series`

## Parameters
- `open_` (Series): open Series
- `close` (Series): close Series

## Returns
- Series: 1 column

---

# high_low_range (Candles)
> High Low Range

**Signature**:
`high_low_range (high: Series, low: Series) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series

## Returns
- .Series: 1 column

---

# real_body (Candles)
> Body Range

**Signature**:
`real_body (open_: Series, close: Series) -> Series`

## Parameters
- `open_` (Series): open Series
- `close` (Series): close Series

## Returns
- Series: 1 column

---


# Category: Cycle

# ebsw (Cycle)
> Even Better Sine Wave

**Signature**:
`ebsw (close: Series, length: Int=None, bars: Int=None, initial_version: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): Max cycle/trend period. Values between40-48work as expected with minimum value:39. Default:40
- `bars` (int): Period of low pass filtering. Default:10
- `offset` (int): Post shift. Default:0
- `fillna` (value): Replaces na's with value.

## Returns
- Series: 1 column

---

# reflex (Cycle)
> Reflex

**Signature**:
`reflex (close: Series, length: Int=None, smooth: Int=None, alpha: IntFloat=None, pi: IntFloat=None, sqrt2: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:20
- `smooth` (int): Super Smoother period. Default:20
- `alpha` (float): Alpha weight of Difference Sums. Default:0.04
- `pi` (float): Ehlers's truncated value:3.14159. Default:3.14159
- `sqrt2` (float): Ehlers's truncated value:1.414. Default:1.414
- `offset` (int): Post shift. Default:0
- `fillna` (value): Replaces na's with value.

## Returns
- Series: 1 column

---


# Category: Events

# above (Events)
> Above

**Signature**:
`above (x: Series, y: Series, asint: bool=True, offset: Int=None, ** kwargs ,) -> Series`

## Parameters
- `x` (Series): x
- `y` (Series): y
- `asint` (bool): Returns as Int. (default: True)
- `offset` (Int): Post shift. Default:0

## Returns
- Series: State wherex >= y.

---

# above_value (Events)
> Above Value

**Signature**:
`above_value (x: Series, value: IntFloat, asint: bool=True, offset: Int=None, ** kwargs ,) -> Series`

## Parameters
- `x` (Series): x
- `value` (IntFloat): Value to compare withx.
- `asint` (bool): Returns as Int. (default: True)

## Returns
- Series: State wherex >= y.

---

# below (Events)
> Below

**Signature**:
`below (x: Series, y: Series, asint: bool=True, offset: Int=None, ** kwargs ,) -> Series`

## Parameters
- `x` (Series): x
- `y` (Series): y
- `asint` (bool): Returns as Int. (default: True)
- `offset` (Int): Post shift. Default:0

## Returns
- Series: State wherex <= y.

---

# below_value (Events)
> Below Value

**Signature**:
`below_value (x: Series, value: IntFloat, asint: bool=True, offset: Int=None, ** kwargs ,) -> Series`

## Parameters
- `x` (Series): x
- `value` (IntFloat): Value to compare withx.
- `asint` (bool): Returns as Int. (default: True)
- `offset` (Int): Post shift. Default:0

## Returns
- Series: State wherex <= y.

---

# cross (Events)
> Cross

**Signature**:
`cross (x: Series, y: Series, above: bool=True, equal: bool=True, asint: bool=True, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `x` (Series): x
- `y` (Series): y
- `above` (bool): Check above. Check below, setabove=False (default: True)
- `equal` (bool): At least/most,=, check. (default: True)
- `asint` (bool): Returns as Int. (default: True)
- `offset` (Int): Post shift. Default:0

## Returns
- Series: Values wherexcrossesy.

---

# cross_value (Events)
> Cross Value

**Signature**:
`cross_value (x: Series, value: IntFloat, above: bool=True, equal: bool=True, asint: bool=True, offset: Int=None, ** kwargs ,) -> Series`

## Parameters
- `x` (Series): x
- `value` (IntFloat): Value to compare withx.
- `above` (bool): Check above. Check below, setabove=False (default: True)
- `equal` (bool): At least/most,=, check. (default: True)
- `asint` (bool): Returns as Int. (default: True)
- `offset` (Int): Post shift. Default:0

## Returns
- Series: Values wherexcrossesy.

---

# signals (Events)
> Signals

**Signature**:
`signals (indicator: Series, xa: IntFloat=None, xb: IntFloat=None, cross_values: bool=None, xseries: Series=None, xseries_a: Series=None, xseries_b: Series=None, cross_series: bool=None, offset: Int=None ,) -> DataFrame`

## Parameters
- `indicator` (Series): Indicator to check for signal crossings.
- `cross_values` (bool): Check if crossed value.
- `xseries` (Series): Cross Series
- `xseries_a` (Series): Cross Above Series
- `xseries_b` (Series): Cross Below Series
- `cross_series` (bool): Check if crossedxseries.
- `xa` (IntFloat): Crossing above value.
- `xb` (IntFloat): Crossing below value.
- `offset` (Int): Post shift. Default:0

## Returns
- DataFrame: 2 columns

---

# tsignals (Events)
> Trend Signals

**Signature**:
`tsignals (trend: Series, asbool: bool=None, trade_offset: Int=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `trend` (Series): trend Series. Boolean or integer values of0and1
- `asbool` (bool): Return booleans. Default:False
- `trade_offset` (value): Shift trade entries/exits with live:0and backesting:1. Default:0
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 4 columns

---

# xsignals (Events)
> Cross Signals

**Signature**:
`xsignals (source: Series, xa: IntFloat | Series, xb: IntFloat | Series, above: bool=True, long: bool=True, asbool: bool=None, trade_offset: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `source` (Series): source Signal
- `xa` (Series): Series the Signal crosses above ifabove=True
- `xb` (Series): Series the Signal crosses below ifabove=True
- `above` (bool): Thesourcecrossing; below is False. (default: True)
- `long` (bool): Thesourceposition; short is False. (default: True)
- `offset` (int): Post shift. Default:0
- `asbool` (bool): Return booleans. Default:False
- `trade_offset` (value): Shift trade entries/exits with live:0and backesting:1. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 4 columns

---


# Category: Math

# combination (Math)
> Combination

**Signature**:
`combination (n: Int=1, r: Int=0, repetition: bool=False, multichoose: bool=False ,) -> Int`

## Parameters
- `n` (Int): n (default: 1)
- `r` (Int): r (default: 0)
- `repetition` (bool): Apply repetition. (default: False)
- `multichoose` (bool): Apply multichoose. (default: False)

## Returns
- Int: Combination value

---

# consecutive_streak (Math)
> Consecutive Streak

**Signature**:
`consecutive_streak (x: Array) -> Array`

## Parameters
- `x` (Array): Numpy array.

## Returns
- Array: Streak array of element changes.

---

# cube (Math)
> Cube Transform

**Signature**:
`cube (src: Series, pwr: IntFloat=None, signal_offset: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `src` (Series): Source
- `pwr` (float): The transform power. Default:3
- `signal_offset` (int): Signal offset. Default:-1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# df_error_analysis (Math)
> Data Frame Correlation Analysis

**Signature**:
`df_error_analysis (A: DataFrame, B: DataFrame, plot: bool=False, triangular: bool=False, method: str="pearson" ,) -> DataFrame`

## Parameters
- `A` (DataFrame): Data Frame A
- `B` (DataFrame): Data Frame B
- `plot` (bool): Create a KDE plot of differences. (default: False)
- `triangular` (bool): Return a Triangular Correlation Data Frame. (default: False)
- `method` (str): Correlation methods:"pearson","kendall", or"spearman". Default:"pearson" (default: 'pearson')

## Returns
- DataFrame: Correlation Data Frame or a KDE Difference plot

---

# erf (Math)
> Error Function

**Signature**:
`erf (x: IntFloat) -> Float`

## Parameters
- `x` (IntFloat): xvalue.

## Returns
- Float: Error value

---

# fibonacci (Math)
> Fibonacci

**Signature**:
`fibonacci (n: Int=2, weighted: bool=False) -> Array`

## Parameters
- `n` (Int): Number of terms (n >= 2). (default: 2)
- `weighted` (bool): Return weighted values. (default: False)

## Returns
- Array: Numpy array results

---

# geometric_mean (Math)
> Geometric Mean

**Signature**:
`geometric_mean (x: Series) -> Float`

## Parameters
- `x` (Series): Values

## Returns
- Float: Geometric Mean

---

# hpoly (Math)
> Horner's Polynomial

**Signature**:
`hpoly (x: Array, v: IntFloat) -> Float`

## Parameters
- `x` (Array): Polynomial coefficients asnp.array
- `v` (IntFloat): Value

## Returns
- Float: Polynomial value.

---

# ifisher (Math)
> Inverse Fisher Transform

**Signature**:
`ifisher (x: Series, amp: IntFloat=None, signal_offset: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `x` (Series): Normalized to range[-1, 1]
- `amp` (float): Amplifier. Default:1
- `signal_offset` (int): Signal line offset. Default:-1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# log_geometric_mean (Math)
> Logarithmic Geometric Mean

**Signature**:
`log_geometric_mean (x: Series) -> Float`

## Parameters
- `x` (Series): Values

## Returns
- Float: Log Geometric Mean or zero

---

# pascals_triangle (Math)
> Pascal's Triangle

**Signature**:
`pascals_triangle (n: Int=None, inverse: bool=False, weighted: bool=False) -> Array`

## Parameters
- `n` (Int): n^throw of Pascal' Triange
- `inverse` (bool): Return Inverse weighted. (default: False)
- `weighted` (bool): Return weighted. (default: False)

## Returns
- Array: Classical, Weighted, or Inversely

---

# percent_rank (Math)
> Percent Rank

**Signature**:
`percent_rank (x: Series, length: int) -> Series`

## Parameters
- `x` (Series): xvalues
- `length` (int): The period.

## Returns
- Series: Percent Rank values.

---

# remap (Math)
> remap

**Signature**:
`remap (x: Series, from_min: IntFloat=None, from_max: IntFloat=None, to_min: IntFloat=None, to_max: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `x` (Series): Series of 'x's
- `from_min` (IntFloat): Input minimum. Default:0.0
- `from_max` (IntFloat): Input maximum. Default:100.0
- `to_min` (IntFloat): Output minimum. Default:0.0
- `to_max` (IntFloat): Output maximum. Default:100.0
- `offset` (Int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# strided_window (Math)
> Strided Window

**Signature**:
`strided_window (x: Array, length: Int) -> Array`

## Parameters
- `x` (Array): Source
- `length` (Int): Window period.

## Returns
- Array: Numpy Array of Strided Window Arrays

---

# sum_signed_rolling_deltas (Math)
> Sum of Signed Rolling Series Deltas

**Signature**:
`sum_signed_rolling_deltas (open_: Series, close: Series, length: Int, exclusive: bool=True ,) -> Series`

## Parameters
- `open_` (Series): open Series
- `close` (Series): close Series
- `length` (Int): Window length. Default:4
- `exclusive` (bool): Exclusive rolling window. Inclusive rolling window when False. (default: True)

## Returns
- Series: 1 column

---

# symmetric_triangle (Math)
> Symmetric Triangle

**Signature**:
`symmetric_triangle (n: Int=None, weighted: bool=False) -> List [ IntFloat ]`

## Parameters
- `n` (Int): Array return size
- `weighted` (bool): Return weighted. (default: False)

## Returns
- List[IntFloat]: List of Symmetric Triangle values.

---

# weights (Math)
> Weights

**Signature**:
`weights (w: Array) -> Callable`

## Parameters
- `w` (Array): Input

## Returns
- Callable: Weights function for dot product.

---

# zero (Math)
> Zero

**Signature**:
`zero (x: IntFloat) -> IntFloat`

## Parameters
- `x` (IntFloat): Value to attempt to zero

## Returns
- IntFloat: 0orx

---


# Category: Momentum

# ao (Momentum)
> Awesome Oscillator

**Signature**:
`ao (high: Series, low: Series, fast: Int=None, slow: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `fast` (int): Fast period. Default:5
- `slow` (int): Slow period. Default:34
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# apo (Momentum)
> Absolute Price Oscillator

**Signature**:
`apo (close: Series, fast: Int=None, slow: Int=None, mamode: str=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `fast` (int): Fast period. Default:12
- `slow` (int): Slow period. Default:26
- `mamode` (str): See help(ta.ma). Default:"sma"
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# bias (Momentum)
> Bias

**Signature**:
`bias (close: Series, length: Int=None, mamode: str=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:26
- `mamode` (str): See help(ta.ma). Default:"sma"
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# bop (Momentum)
> Balance of Power

**Signature**:
`bop (open_: Series, high: Series, low: Series, close: Series, scalar: IntFloat=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `open_` (Series): open Series
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `scalar` (float): Scalar. Default:1
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# brar (Momentum)
> BRAR

**Signature**:
`brar (open_: Series, high: Series, low: Series, close: Series, length: Int=None, scalar: IntFloat=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `open_` (Series): open Series
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:26
- `scalar` (float): Scalar. Default:100
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# cci (Momentum)
> Commodity Channel Index

**Signature**:
`cci (high: Series, low: Series, close: Series, length: Int=None, c: IntFloat=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `c` (float): Scaling Constant. Default:0.015
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# cfo (Momentum)
> Chande Forcast Oscillator

**Signature**:
`cfo (close: Series, length: Int=None, scalar: IntFloat=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:9
- `scalar` (float): Scalar. Default:100
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# cg (Momentum)
> Center of Gravity

**Signature**:
`cg (close: Series, length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# cmo (Momentum)
> Chande Momentum Oscillator

**Signature**:
`cmo (close: Series, length: Int=None, scalar: IntFloat=None, talib: bool=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `scalar` (float): Scalar. Default:100
- `talib` (bool): If installed, use TA Lib. Uses EMA if False. Default:True
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# coppock (Momentum)
> Coppock Curve

**Signature**:
`coppock (close: Series, length: Int=None, fast: Int=None, slow: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): WMA period. Default:10
- `fast` (int): Fast ROC period. Default:11
- `slow` (int): Slow ROC period. Default:14
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# crsi (Momentum)
> Connors Relative Strength Index

**Signature**:
`crsi (close: Series, rsi_length: Int=None, streak_length: Int=None, rank_length: Int=None, scalar: IntFloat=None, talib: bool=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `rsi_length` (int): The RSI period. Default:3
- `streak_length` (int): Streak RSI period. Default:2
- `rank_length` (int): Percent Rank length. Default:100
- `scalar` (float): Scalar. Default:100
- `talib` (bool): If installed, use TA Lib. Default:True
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# cti (Momentum)
> Correlation Trend Indicator

**Signature**:
`cti (close: Series, length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:12
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# dm (Momentum)
> Directional Movement

**Signature**:
`dm (high: Series, low: Series, length: Int=None, mamode: str=None, talib: bool=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `mamode` (str): See help(ta.ma). Default:"rma"
- `talib` (bool): If installed, use TA Lib. Default:True
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# er (Momentum)
> Efficiency Ratio

**Signature**:
`er (close: Series, length: Int=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# eri (Momentum)
> Elder Ray Index

**Signature**:
`eri (high: Series, low: Series, close: Series, length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# exhc (Momentum)
> Exhaustion Count

**Signature**:
`exhc (close: Series, length: Int=None, cap: Int=None, asint: bool=None, show_all: bool=None, nozeros: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): Series of close's
- `length` (int): The period. Default:4
- `cap` (int): Count cap. For no cap, set to0. Default:13
- `show_all` (bool): Counts 1 - 13. For 6 - 9, set to False. Default:True
- `asint` (bool): Returns as Int. Default:False
- `nozeros` (bool): Replace zeros withnp.nan. Default:False
- `offset` (int): Post shift. Default:0

## Returns
- DataFrame: 2 columns

---

# fisher (Momentum)
> Fisher Transform

**Signature**:
`fisher (high: Series, low: Series, length: Int=None, signal: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `length` (int): The period. Default:9
- `signal` (int): Signal period. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# inertia (Momentum)
> Inertia

**Signature**:
`inertia (close: Series, high: Series=None, low: Series=None, length: Int=None, rvi_length: Int=None, scalar: IntFloat=None, refined: bool=None, thirds: bool=None, drift: Int=None, mamode: str=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:20
- `rvi_length` (int): RVI period. Default:14
- `refined` (bool): Use 'refined' calculation. Default:False
- `thirds` (bool): Use 'thirds' calculation. Default:False
- `mamode` (str): See help(ta.ma). Default:"ema"
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# kdj (Momentum)
> KDJ

**Signature**:
`kdj (high: Series, low: Series, close: Series, length: Int=None, signal: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:9
- `signal` (int): Signal period. Default:3
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# kst (Momentum)
> 'Know Sure Thing'

**Signature**:
`kst (close: Series, signal: Int=None, roc1: Int=None, roc2: Int=None, roc3: Int=None, roc4: Int=None, sma1: Int=None, sma2: Int=None, sma3: Int=None, sma4: Int=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `roc1` (int): ROC 1 period. Default:10
- `roc2` (int): ROC 2 period. Default:15
- `roc3` (int): ROC 3 period. Default:20
- `roc4` (int): ROC 4 period. Default:30
- `sma1` (int): SMA 1 period. Default:10
- `sma2` (int): SMA 2 period. Default:10
- `sma3` (int): SMA 3 period. Default:10
- `sma4` (int): SMA 4 period. Default:15
- `signal` (int): Signal period. Default:9
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# macd (Momentum)
> Moving Average Convergence Divergence

**Signature**:
`macd (close: Series, fast: Int=None, slow: Int=None, signal: Int=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `fast` (int): Fast MA period. Default:12
- `slow` (int): Slow MA period. Default:26
- `signal` (int): Signal period. Default:9
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `asmode` (value): Enable AS version of MACD. Default:False
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# mom (Momentum)
> Momentum

**Signature**:
`mom (close: Series, length: Int=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:1
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# pgo (Momentum)
> Pretty Good Oscillator

**Signature**:
`pgo (high: Series, low: Series, close: Series, length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# ppo (Momentum)
> Percentage Price Oscillator

**Signature**:
`ppo (close: Series, fast: Int=None, slow: Int=None, signal: Int=None, scalar: IntFloat=None, mamode: str=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `fast` (int): Fast MA period. Default:12
- `slow` (int): Slow MA period. Default:26
- `signal` (int): Signal period. Default:9
- `scalar` (float): Scalar. Default:100
- `mamode` (str): See help(ta.ma). Default:"sma"
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# psl (Momentum)
> Psychological Line

**Signature**:
`psl (close: Series, open_: Series=None, length: Int=None, scalar: IntFloat=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `open_` (Series): open Series
- `length` (int): The period. Default:12
- `scalar` (float): Scalar. Default:100
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# qqe (Momentum)
> Quantitative Qualitative Estimation

**Signature**:
`qqe (close: Series, length: Int=None, smooth: Int=None, factor: IntFloat=None, mamode: str=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `length` (int): RSI period. Default:14
- `smooth` (int): RSI smoothing period. Default:5
- `factor` (float): QQE Factor. Default:4.236
- `mamode` (str): See help(ta.ma). Default:"ema"
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 4 columns

---

# roc (Momentum)
> Rate of Change

**Signature**:
`roc (close: Series, length: Int=None, scalar: IntFloat=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `scalar` (float): Scalar. Default:100
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# rsi (Momentum)
> Relative Strength Index

**Signature**:
`rsi (close: Series, length: Int=None, scalar: IntFloat=None, mamode: str=None, talib: bool=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `scalar` (float): Scalar. Default:100
- `mamode` (str): See help(ta.ma). Default:"rma"
- `talib` (bool): If installed, use TA Lib. Default:True
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# rsx (Momentum)
> Relative Strength Xtra

**Signature**:
`rsx (close: Series, length: Int=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# rvgi (Momentum)
> Relative Vigor Index

**Signature**:
`rvgi (open_: Series, high: Series, low: Series, close: Series, length: Int=None, swma_length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `open_` (Series): open Series
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `swma_length` (int): SWMA period. Default:4
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# slope (Momentum)
> Slope

**Signature**:
`slope (close: Series, length: Int=None, as_angle: bool=None, to_degrees: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:1
- `as_angle` (bool): Converts slope to an angle in radians pernp.arctan(). Default:False
- `to_degrees` (value): Ifas_angle=True, converts radians to degrees. Default:False
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# smc (Momentum)
> Smart Money Concept

**Signature**:
`smc (open_: Series, high: Series, low: Series, close: Series, abr_length: Int=None, close_length: Int=None, vol_length: Int=None, percent: Int=None, vol_ratio: IntFloat=None, asint: bool=None, mamode: str=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> DictLike`

## Parameters
- `abr_length` (int): ABR length. Default:14
- `close_length` (int): Theclose MA period. Default:50
- `vol_length` (int): Volatility period. Default:20
- `percent` (int): Percent of wick that exceeds the body. Default:5
- `vol_ratio` (float): Volatility ratio (high) limit. Default:1.5
- `asint` (bool): Returns as Int. Default:True
- `mamode` (str): See help(ta.ma). Default:"sma"
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0

## Returns
- DataFrame: 7 columns

---

# smi (Momentum)
> SMI Ergodic Indicator

**Signature**:
`smi (close: Series, fast: Int=None, slow: Int=None, signal: Int=None, scalar: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `fast` (int): The short period. Default:5
- `slow` (int): The long period. Default:20
- `signal` (int): Signal period. Default:5
- `scalar` (float): Scalar. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# squeeze (Momentum)
> Squeeze

**Signature**:
`squeeze (high: Series, low: Series, close: Series, bb_length: Int=None, bb_std: IntFloat=None, kc_length: Int=None, kc_scalar: IntFloat=None, mom_length: Int=None, mom_smooth: Int=None, use_tr: bool=None, mamode: str=None, prenan: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `bb_length` (int): BB period. Default:20
- `bb_std` (float): BB Std. Dev. Default:2
- `kc_length` (int): KC period. Default:20
- `kc_scalar` (float): KC scalar. Default:1.5
- `mom_length` (int): Momentum Period. Default:12
- `mom_smooth` (int): Momentum Smoothing period. Default:6
- `mamode` (str): One of: "ema" or "sma". Default:"sma"
- `prenan` (bool): Apply prenans. Default:False
- `offset` (int): Post shift. Default:0
- `tr` (value): Use True Range for Keltner Channels. Default:True
- `asint` (bool): Returns as Int. Default:True
- `lazybear` (value): Lazy Bear's Trading View. Default:False
- `detailed` (value): Extra detailed. Default:False
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: Default: 4 columns Detailed: 10 columns

---

# squeeze_pro (Momentum)
> Squeeze Pro

**Signature**:
`squeeze_pro (high: Series, low: Series, close: Series, bb_length: Int=None, bb_std: IntFloat=None, kc_length: Int=None, kc_scalar_narrow: IntFloat=None, kc_scalar_normal: IntFloat=None, kc_scalar_wide: IntFloat=None, mom_length: Int=None, mom_smooth: Int=None, use_tr: bool=None, mamode: str=None, prenan: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `bb_length` (int): BB period. Default:20
- `bb_std` (float): BB Std. Dev. Default:2
- `kc_length` (int): KC period. Default:20
- `kc_scalar_normal` (float): Keltner Channel scalar for normal channel. Default:1.5
- `kc_scalar_narrow` (float): Narrow channel KC scalar. Default:1
- `kc_scalar_wide` (float): Wide channel KC scalar. Default:2
- `mom_length` (int): Momentum Period. Default:12
- `mom_smooth` (int): Momentum Smoothing period. Default:6
- `mamode` (str): One of: "ema" or "sma". Default:"sma"
- `prenan` (bool): Apply prenans. Default:False
- `offset` (int): Post shift. Default:0
- `tr` (value): Use True Range for Keltner Channels. Default:True
- `asint` (bool): Returns as Int. Default:True
- `mamode` (value): Which MA to use. Default:"sma"
- `detailed` (value): Extra detailed. Default:False
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 6 columns (default) or 12 columns ifdetailed=True

---

# stc (Momentum)
> Schaff Trend Cycle

**Signature**:
`stc (close: Series, tc_length: Int=None, fast: Int=None, slow: Int=None, factor: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `tc_length` (int): TC period. (Adjust to the half of cycle) Default:10
- `fast` (int): Fast MA period. Default:12
- `slow` (int): Slow MA period. Default:26
- `factor` (float): Smoothing factor for last stoch. calculation. Default:0.5
- `offset` (int): How many bars to shift the results. Default:`0
- `ma1` (Series): User chosen MA. Default:False
- `ma2` (Series): User chosen MA. Default:False
- `osc` (Series): User chosen oscillator. Default:False
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# stoch (Momentum)
> Stochastic

**Signature**:
`stoch (high: Series, low: Series, close: Series, k: Int=None, d: Int=None, smooth_k: Int=None, mamode: str=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `k` (int): The Fast %K period. Default:14
- `d` (int): The Slow %D period. Default:3
- `smooth_k` (int): The Slow %K period. Default:3
- `mamode` (str): See help(ta.ma). Default:"sma"
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# stochf (Momentum)
> Fast Stochastic

**Signature**:
`stochf (high: Series, low: Series, close: Series, k: Int=None, d: Int=None, mamode: str=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `k` (int): The Fast %K period. Default:14
- `d` (int): The Slow %D period. Default:3
- `mamode` (str): See help(ta.ma). Default:"sma"
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# stochrsi (Momentum)
> Stochastic RSI

**Signature**:
`stochrsi (close: Series, length: Int=None, rsi_length: Int=None, k: Int=None, d: Int=None, mamode: str=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `rsi_length` (int): RSI period. Default:14
- `k` (int): The Fast %K period. Default:3
- `d` (int): The Slow %K period. Default:3
- `mamode` (str): See help(ta.ma). Default:"sma"
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# tmo (Momentum)
> True Momentum Oscillator

**Signature**:
`tmo (open_: Series, close: Series, tmo_length: Int=None, calc_length: Int=None, smooth_length: Int=None, momentum: bool=None, normalize: bool=None, exclusive: bool=None, mamode: str=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `open_` (Series): open Series
- `close` (Series): close Series
- `tmo_length` (int): TMO period. Default:14
- `calc_length` (int): Initial MA period. Default:5
- `smooth_length` (int): Main and smooth signal MA period. Default:3
- `mamode` (str): See help(ta.ma). Default:"ema"
- `momentum` (bool): Compute main and smooth momentum. Default:False
- `normalize` (bool): Normalize. Default:False
- `exclusive` (bool): Exclusive period overnbars, or inclusively overn-1bars. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): Data Frame.fillna(value)

## Returns
- DataFrame: 4 columns

---

# trix (Momentum)
> Trix

**Signature**:
`trix (close: Series, length: Int=None, signal: Int=None, scalar: IntFloat=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:18
- `signal` (int): Signal period. Default:9
- `scalar` (float): Scalar. Default:100
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# tsi (Momentum)
> True Strength Index

**Signature**:
`tsi (close: Series, fast: Int=None, slow: Int=None, signal: Int=None, scalar: IntFloat=None, mamode: str=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `fast` (int): Fast MA period. Default:13
- `slow` (int): Slow MA period. Default:25
- `signal` (int): Signal period. Default:13
- `scalar` (float): Scalar. Default:100
- `mamode` (str): Signal MA. See help(ta.ma). Default:"ema"
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# uo (Momentum)
> Ultimate Oscillator

**Signature**:
`uo (high: Series, low: Series, close: Series, fast: Int=None, medium: Int=None, slow: Int=None, fast_w: IntFloat=None, medium_w: IntFloat=None, slow_w: IntFloat=None, talib: bool=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `fast` (int): The Fast %K period. Default:7
- `medium` (int): The Slow %K period. Default:14
- `slow` (int): The Slow %D period. Default:28
- `fast_w` (float): The Fast %K period. Default:4.0
- `medium_w` (float): The Slow %K period. Default:2.0
- `slow_w` (float): The Slow %D period. Default:1.0
- `talib` (bool): If installed, use TA Lib. Default:True
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# willr (Momentum)
> William's Percent R

**Signature**:
`willr (high: Series, low: Series, close: Series, length: Int=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---


# Category: Overlap

# alligator (Overlap)
> Bill Williams Alligator

**Signature**:
`alligator (close: Series, jaw: Int=None, teeth: Int=None, lips: Int=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `jaw` (int): Jaw period. Default:13
- `teeth` (int): Teeth period. Default:8
- `lips` (int): Lips period. Default:5
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# alma (Overlap)
> Arnaud Legoux Moving Average

**Signature**:
`alma (close: Series, length: Int=None, sigma: IntFloat=None, dist_offset: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:9
- `sigma` (float): Smoothing value. Default6.0
- `dist_offset` (float): Distribution offset, range[0, 1]. Default0.85
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# dema (Overlap)
> Double Exponential Moving Average

**Signature**:
`dema (close: Series, length: Int=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# ema (Overlap)
> Exponential Moving Average

**Signature**:
`ema (close: Series, length: Int=None, talib: bool=None, presma: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `talib` (bool): If installed, use TA Lib. Default:True
- `presma` (bool): Initialize with SMA like TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `adjust` (bool): 
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# fwma (Overlap)
> Fibonacci's Weighted Moving Average

**Signature**:
`fwma (close: Series, length: Int=None, asc: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `asc` (bool): Recent values weigh more. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# hilo (Overlap)
> Gann Hi Lo Activator

**Signature**:
`hilo (high: Series, low: Series, close: Series, high_length: Int=None, low_length: Int=None, mamode: str=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `high_length` (int): High period. Default:13
- `low_length` (int): Low period. Default:21
- `mamode` (str): See help(ta.ma). Default:"sma"
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# hl2 (Overlap)
> HL2

**Signature**:
`hl2 (high: Series, low: Series, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value). Only works when offset.

## Returns
- Series: 1 column

---

# hlc3 (Overlap)
> HLC3

**Signature**:
`hlc3 (high: Series, low: Series, close: Series, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value). Only works when offset.

## Returns
- Series: 1 column

---

# hma (Overlap)
> Hull Moving Average

**Signature**:
`hma (close: Series, length: Int=None, mamode: str=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `mamode` (str): One of: 'ema', 'sma', or 'wma'. Default:"wma"
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# hwma (Overlap)
> Holt-Winter Moving Average

**Signature**:
`hwma (close: Series, na: IntFloat=None, nb: IntFloat=None, nc: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `na` (float): Smoothed series parameter (from 0 to 1). Default: 0.2
- `nb` (float): Trend parameter (from 0 to 1). Default: 0.1
- `nc` (float): Seasonality parameter (from 0 to 1). Default: 0.1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: Series

---

# ichimoku (Overlap)
> Ichimoku KinkÅ HyÅ

**Signature**:
`ichimoku (high: Series, low: Series, close: Series, tenkan: Int=None, kijun: Int=None, senkou: Int=None, include_chikou: bool=True, offset: Int=None, ** kwargs: DictLike ,) -> Tuple [ DataFrame, DataFrame ]`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `tenkan` (int): Tenkan period. Default:9
- `kijun` (int): Kijun period. Default:26
- `senkou` (int): Senkou period. Default:52
- `include_chikou` (bool): Whether to include chikou component. (default: True)
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)
- `lookahead` (value): To avoid data leakage set to False.

## Returns
- Tuple[pd.DataFrame,pd.DataFrame]: Historical Data Frame, 5 columns Forward Looking Data Frame, 2 columns

---

# jma (Overlap)
> Jurik Moving Average Average

**Signature**:
`jma (close: Series, length: IntFloat=None, phase: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:7
- `phase` (float): Phase value between [-100, 100]. Default:0
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# kama (Overlap)
> Kaufman's Adaptive Moving Average

**Signature**:
`kama (close: Series, length: Int=None, fast: Int=None, slow: Int=None, mamode: str=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `fast` (int): Fast MA period. Default:2
- `slow` (int): Slow MA period. Default:30
- `mamode` (str): See help(ta.ma). Default:"sma"
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# linreg (Overlap)
> Linear Regression Moving Average

**Signature**:
`linreg (close: Series, length: Int=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `angle` (bool): Returns the slope angle in radians. Default:False
- `degrees` (bool): Return the slope angle in degrees. Default:False
- `intercept` (bool): Return the intercept. Default:False
- `r` (bool): Return the 'r' correlation. Default:False
- `slope` (bool): Return the slope. Default:False
- `tsf` (bool): Return the Time Series Forecast value. Default:False
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# mama (Overlap)
> MESA Adaptive Moving Average

**Signature**:
`mama (close: Series, fastlimit: IntFloat=None, slowlimit: IntFloat=None, prenan: Int=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `fastlimit` (float): Fast limit. Default:0.5
- `slowlimit` (float): Slow limit. Default:0.05
- `prenan` (int): Prenans to apply. TV-LB3, Ehler's6, TA Lib32. Default:3
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# mcgd (Overlap)
> Mc Ginley Dynamic Indicator

**Signature**:
`mcgd (close: Series, length: Int=None, c: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `c` (float): Denominator multiplier. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# midpoint (Overlap)
> Midpoint

**Signature**:
`midpoint (close: Series, length: Int=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:2
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# midprice (Overlap)
> Midprice

**Signature**:
`midprice (high: Series, low: Series, length: Int=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `length` (int): The period. Default:2
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# ohlc4 (Overlap)
> OHLC4

**Signature**:
`ohlc4 (open_: Series, high: Series, low: Series, close: Series, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `open_` (Series): open Series
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value). Only works when offset.

## Returns
- Series: 1 column

---

# pwma (Overlap)
> Pascal's Weighted Moving Average

**Signature**:
`pwma (close: Series, length: Int=None, asc: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `asc` (bool): Ascending. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 1 column

---

# rma (Overlap)
> wilde R's Moving Average

**Signature**:
`rma (close: Series, length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# sinwma (Overlap)
> Sine Weighted Moving Average

**Signature**:
`sinwma (close: Series, length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# sma (Overlap)
> Simple Moving Average

**Signature**:
`sma (close: Series, length: Int=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `adjust` (bool): Adjust the values. Default:True
- `presma` (bool): If True, uses SMA for initial value.
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# smma (Overlap)
> SMoothed Moving Average

**Signature**:
`smma (close: Series, length: Int=None, mamode: str=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `mamode` (str): See help(ta.ma). Default:"sma"
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# ssf (Overlap)
> Ehlers's Super Smoother Filter

**Signature**:
`ssf (close: Series, length: Int=None, everget: bool=None, pi: IntFloat=None, sqrt2: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:20
- `everget` (bool): Everget's implementation of ssf that uses pi instead of 180 for the b factor of ssf. Default:False
- `pi` (float): The default is Ehlers's truncated value:3.14159. Default:3.14159
- `sqrt2` (float): The default is Ehlers's truncated value:1.414. Default:1.414
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# ssf3 (Overlap)
> Ehlers's 3 Pole Super Smoother Filter

**Signature**:
`ssf3 (close: Series, length: Int=None, pi: IntFloat=None, sqrt3: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,)`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:20
- `pi` (float): The value of PI. The default is Ehler's truncated value:3.14159. Default:3.14159
- `sqrt3` (float): The value ofsqrt(3)to use. The default is Ehler's truncated value:1.732. Default:1.732
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# supertrend (Overlap)
> Supertrend

**Signature**:
`supertrend (high: Series, low: Series, close: Series, length: Int=None, atr_length: Int=None, multiplier: IntFloat=None, atr_mamode: str=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:7
- `atr_length` (int): ATR period. Default:length
- `multiplier` (float): Coefficient for upper and lower band distance to midrange. Default:3.0
- `atr_mamode` (str)): MA type to be used for ATR calculation. See help(ta.ma). Default:"rma"
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 4 columns

---

# swma (Overlap)
> Symmetric Weighted Moving Average

**Signature**:
`swma (close: Series, length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# t3 (Overlap)
> T3

**Signature**:
`t3 (close: Series, length: Int=None, a: IntFloat=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `a` (float): The a factor, 0 < a < 1. Default:0.7
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `adjust` (bool): 
- `presma` (bool): If True, uses SMA for initial value.
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# tema (Overlap)
> Triple Exponential Moving Average

**Signature**:
`tema (close: Series, length: Int=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `adjust` (bool): 
- `presma` (bool): If True, uses SMA for initial value.
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# trima (Overlap)
> Triangular Moving Average

**Signature**:
`trima (close: Series, length: Int=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `adjust` (bool): 
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# vidya (Overlap)
> Variable Index Dynamic Average

**Signature**:
`vidya (close: Series, length: Int=None, talib: bool=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `talib` (bool): If installed, use TA Lib. Default:True
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# wcp (Overlap)
> Weighted Closing Price

**Signature**:
`wcp (high: Series, low: Series, close: Series, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# wma (Overlap)
> Weighted Moving Average

**Signature**:
`wma (close: Series, length: Int=None, asc: bool=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `asc` (bool): Recent values weigh more. Default:True
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# zlma (Overlap)
> Zero Lag Moving Average

**Signature**:
`zlma (close: Series, length: Int=None, mamode: str=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `mamode` (str): One of: "dema", "ema", "fwma", "hma", "linreg", "midpoint", "pwma", "rma", "sinwma", "ssf", "swma", "t3", "tema", "trima", "vidya", or "wma". Default:"ema"
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---


# Category: Performance

# drawdown (Performance)
> Drawdown

**Signature**:
`drawdown (close: Series, offset: Int=None, ** kwargs: DictLike) -> DataFrame`

## Parameters
- `close` (Series): close Series.
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# log_return (Performance)
> Log Return

**Signature**:
`log_return (close: Series, length: Int=None, cumulative: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:20
- `cumulative` (bool): If True, returns the cumulative returns. Default:False
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# percent_return (Performance)
> Percent Return

**Signature**:
`percent_return (close: Series, length: Int=None, cumulative: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:1
- `cumulative` (bool): If True, returns the cumulative returns. Default:False
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---


# Category: Statistics

# entropy (Statistics)
> Entropy

**Signature**:
`entropy (close: Series, length: Int=None, base: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `base` (float): Logarithmic Base. Default:2
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# kurtosis (Statistics)
> Rolling Kurtosis

**Signature**:
`kurtosis (close: Series, length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:30
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# mad (Statistics)
> Rolling Mean Absolute Deviation

**Signature**:
`mad (close: Series, length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:30
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# median (Statistics)
> Rolling Median

**Signature**:
`median (close: Series, length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:30
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# quantile (Statistics)
> Rolling Quantile

**Signature**:
`quantile (close: Series, length: Int=None, q: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:30
- `q` (float): The quantile. Default:0.5
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# skew (Statistics)
> Rolling Skew

**Signature**:
`skew (close: Series, length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:30
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# stdev (Statistics)
> Rolling Standard Deviation

**Signature**:
`stdev (close: Series, length: Int=None, ddof: Int=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:30
- `ddof` (int): Delta Degrees of Freedom. Default:1
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# tos_stdevall (Statistics)
> TD Ameritrade's Think or Swim Standard Deviation All

**Signature**:
`tos_stdevall (close: Series, length: Int=None, stds: List=None, ddof: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `length` (int): Bars since current/last bar, Series[-1].
- `stds` (list): List of standard deviations in increasing order from the central Linear Regression line. Default:[1,2,3]
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 7+ columns

---

# variance (Statistics)
> Rolling Variance

**Signature**:
`variance (close: Series, length: Int=None, ddof: Int=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:30
- `ddof` (int): Delta Degrees of Freedom. Default:1
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# zscore (Statistics)
> Rolling Z Score

**Signature**:
`zscore (close: Series, length: Int=None, std: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:30
- `std` (float): Number of deviation standards. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---


# Category: Trend

# adx (Trend)
> Average Directional Movement

**Signature**:
`adx (high: Series, low: Series, close: Series, length: Int=None, signal_length: Int=None, adxr_length: Int=None, scalar: IntFloat=None, talib: bool=None, tvmode: bool=None, mamode: str=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `signal_length` (int): Signal period. Default:length
- `adxr_length` (int): ADXR period. Default:2
- `scalar` (float): Scalar. Default:100
- `talib` (bool): If installed, use TA Lib. Default:True
- `tvmode` (bool): Trading View. Default:False
- `mamode` (str): See help(ta.ma). Default:"rma"
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 4 columns

---

# alphatrend (Trend)
> Alpha Trend

**Signature**:
`alphatrend (open_: Series, high: Series, low: Series, close: Series, volume: Series=None, src: str=None, length: int=None, multiplier: IntFloat=None, threshold: IntFloat=None, lag: Int=None, mamode: str=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,)`

## Parameters
- `open_` (Series): open Series
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `volume` (Series): volume Series.
- `src` (str): One of: "open", "high", "low" or "close". Default:"close"
- `length` (int): ATR, MFI, or RSI period. Default:14
- `multiplier` (float): Trailing ATR multiple. Default:1
- `threshold` (float): Momentum threshold. Default:50
- `lag` (int): Lag period of main trend. Default:2
- `mamode` (str): See help(ta.ma). Default:"sma"
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# amat (Trend)
> Archer Moving Averages Trends

**Signature**:
`amat (close: Series, fast: Int=None, slow: Int=None, lookback: Int=None, mamode: str=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `fast` (int): Fast MA period. Default:8
- `slow` (int): Slow MA period. Default:21
- `lookback` (int): Lookback period forlong_runandshort_run. Default:2
- `mamode` (str): See help(ta.ma). Default:"ema"
- `offset` (int): Post shift. Default:0
- `run_length` (int): OBV trend period. Default:2
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# aroon (Trend)
> Aroon & Aroon Oscillator

**Signature**:
`aroon (high: Series, low: Series, length: Int=None, scalar: IntFloat=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `length` (int): The period. Default:14
- `scalar` (float): Scalar. Default:100
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# chop (Trend)
> Choppiness Index

**Signature**:
`chop (high: Series, low: Series, close: Series, length: Int=None, atr_length: Int=None, ln: bool=None, scalar: IntFloat=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `atr_length` (int): ATR period. Default:1
- `ln` (bool): Uselninstead oflog10. Default:False
- `scalar` (float): Scalar. Default:100
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# cksp (Trend)
> Chande Kroll Stop

**Signature**:
`cksp (high: Series, low: Series, close: Series, p: Int=None, x: IntFloat=None, q: Int=None, tvmode: bool=None, mamode: str=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `p` (int): ATR and first stop period; see Note. Default:10for both modes
- `x` (float): ATR scalar; see Note. Default:1or3
- `q` (int): Second stop period; see Note. Default:9or20
- `tvmode` (bool): Trading View mode. Default:True
- `mamode` (str): See help(ta.ma).
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# decay (Trend)
> Decay

**Signature**:
`decay (close: Series, length: Int=None, mode: str=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:1
- `mode` (str): Either"linear"or"exp"(exponetional) Default:"linear"
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# decreasing (Trend)
> Decreasing

**Signature**:
`decreasing (close: Series, length: Int=None, strict: bool=None, asint: bool=None, percent: IntFloat=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:1
- `strict` (bool): Check if continuously increasing. Default:False
- `percent` (float): Percent, i.e.5.0.
- `asint` (bool): Returns as Int. Default:True
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# dpo (Trend)
> Detrend Price Oscillator

**Signature**:
`dpo (close: Series, length: Int=None, centered: bool=True, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:20
- `centered` (bool): Shift the dpo back byint(0.5 * length) + 1. Set to Falseto remove data leakage. (default: True)
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# ht_trendline (Trend)
> Hilbert Transform Trend Line

**Signature**:
`ht_trendline (close: Series, talib: bool=None, prenan: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series.
- `talib` (bool): If installed, use TA Lib. Default:True
- `prenan` (int): Prenans to apply. Ehlers's6or12, TALib63Default:63
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# increasing (Trend)
> Increasing

**Signature**:
`increasing (close: Series, length: Int=None, strict: bool=None, asint: bool=None, percent: IntFloat=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:1
- `strict` (bool): Check if continuously increasing. Default:False
- `percent` (float): Percent, i.e.5.0.
- `asint` (bool): Returns as Int. Default:True
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# long_run (Trend)
> Long Run

**Signature**:
`long_run (fast: Series, slow: Series, length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `fast` (Series): fast Series.
- `slow` (Series): slow Series.
- `length` (int): Thedecreasingandincreasingperiod. Default:2
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# psar (Trend)
> Parabolic Stop and Reverse

**Signature**:
`psar (high: Series, low: Series, close: Series=None, af0: IntFloat=None, af: IntFloat=None, max_af: IntFloat=None, tv=False, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): Optionalclose Series
- `af0` (float): Initial Acceleration Factor. Default:0.02
- `af` (float): Acceleration Factor. Default:0.02
- `max_af` (float): Maximum Acceleration Factor. Default:0.2
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 4 columns

---

# qstick (Trend)
> Q Stick

**Signature**:
`qstick (open_: Series, close: Series, length: Int=None, mamode: str=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `open_` (Series): open Series
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `mamode` (str): See help(ta.ma). Default:"sma"
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# rwi (Trend)
> Random Walk Index

**Signature**:
`rwi (high: Series, low: Series, close: Series, length: Int=None, mamode: str=None, talib: bool=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `mamode` (str): See help(ta.ma). Default:"rma"
- `talib` (bool): If installed, use TA Lib. Default:True
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# short_run (Trend)
> Short Run

**Signature**:
`short_run (fast: Series, slow: Series, length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `fast` (Series): fast Series.
- `slow` (Series): slow Series.
- `length` (int): Thedecreasingandincreasingperiod. Default:2
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# trendflex (Trend)
> Trendflex

**Signature**:
`trendflex (close: Series, length: Int=None, smooth: Int=None, alpha: IntFloat=None, pi: IntFloat=None, sqrt2: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:20
- `smooth` (int): Super Smoother period. Default: ```20````
- `alpha` (float): Alpha weight. Default:0.04
- `pi` (float): Ehlers's truncated value:3.14159. Default:3.14159
- `sqrt2` (float): Ehlers's truncated value:1.414. Default:1.414
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# ttm_trend (Trend)
> TTM Trend

**Signature**:
`ttm_trend (high: Series, low: Series, close: Series, length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:6
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 1 column

---

# vhf (Trend)
> Vertical Horizontal Filter

**Signature**:
`vhf (close: Series, length: Int=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:28
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# vortex (Trend)
> Vortex

**Signature**:
`vortex (high: Series, low: Series, close: Series, length: Int=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# zigzag (Trend)
> Zigzag

**Signature**:
`zigzag (high: Series, low: Series, close: Series=None, legs: int=None, deviation: IntFloat=None, backtest: bool=None, offset: Int=None, ** kwargs: DictLike ,)`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series.
- `legs` (int): Number of legs (> 2). Default:10
- `deviation` (float): Reversal deviation percentage. Default:5
- `backtest` (bool): 
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---


# Category: Volatility

# aberration (Volatility)
> Aberration

**Signature**:
`aberration (high: Series, low: Series, close: Series, length: Int=None, atr_length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:5
- `atr_length` (int): ATR period. Default:15
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 4 columns

---

# accbands (Volatility)
> Acceleration Bands

**Signature**:
`accbands (high: Series, low: Series, close: Series, length: Int=None, c: IntFloat=None, drift: Int=None, mamode: str=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:10
- `c` (int): Multiplier. Default:4
- `mamode` (str): See help(ta.ma). Default:"sma"
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# atr (Volatility)
> Average True Range

**Signature**:
`atr (high: Series, low: Series, close: Series, length: Int=None, mamode: str=None, talib: bool=None, prenan: bool=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `mamode` (str): See help(ta.ma). Default:"rma"
- `talib` (bool): If installed, use TA Lib. Default:True
- `prenan` (bool): Sets initial values tonp.nanbased ondrift. Default:False
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `percent` (bool): Return as percent. Default:False
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# atrts (Volatility)
> ATR Trailing Stop

**Signature**:
`atrts (high: Series, low: Series, close: Series, length: Int=None, ma_length: Int=None, k: IntFloat=None, mamode: str=None, talib: bool=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `ma_length` (int): MA Length. Default:20
- `k` (int): ATR multiplier. Default:3
- `mamode` (str): See help(ta.ma). Default:"ema"
- `talib` (bool): If installed, use TA Lib. Default:True
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `percent` (bool): Return as percent. Default:False
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# bbands (Volatility)
> Bollinger Bands

**Signature**:
`bbands (close: Series, length: Int=None, lower_std: IntFloat=None, upper_std: IntFloat=None, ddof: Int=None, mamode: str=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:5
- `lower_std` (IntFloat): Lower standard deviation. Default:2.0
- `upper_std` (IntFloat): Upper standard deviation. Default:2.0
- `ddof` (int): Degrees of Freedom to use. Default:0
- `mamode` (str): See help(ta.ma). Default:"sma"
- `talib` (bool): If installed, use TA Lib. Default:True
- `ddof` (int): By default, uses Pandasddof=1. For Numpy calculation, use0. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 5 columns

---

# chandelier_exit (Volatility)
> Chandelier Exit

**Signature**:
`chandelier_exit (high: Series, low: Series, close: Series, high_length: Int=None, low_length: Int=None, atr_length: Int=None, multiplier: IntFloat=None, mamode: str=None, talib: bool=None, use_close: bool=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,)`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `high_length` (int): Highest high period. Default:22
- `low_length` (int): Lowest low period. Default:22
- `atr_length` (int)): ATR length. Default:14
- `multiplier` (float): Lower & Upper Bands scalar. Default:2.0
- `mamode` (str): See help(ta.ma). Default:"rma"
- `talib` (bool): If installed, use TA Lib. Default:True
- `use_close` (bool): Usemax(high_length, low_length)for theclose. Default:False
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# donchian (Volatility)
> Donchian Channels

**Signature**:
`donchian (high: Series, low: Series, lower_length: Int=None, upper_length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `lower_length` (int): Lower period. Default:20
- `upper_length` (int): Upper period. Default:20
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# hwc (Volatility)
> Holt-Winter Channel

**Signature**:
`hwc (close: Series, scalar: IntFloat=None, channels: bool=None, na: IntFloat=None, nb: IntFloat=None, nc: IntFloat=None, nd: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `scalar` (float): Channel scalar. Default:1
- `channels` (bool): Return width and percentage columns. Default:True
- `na` (float): Smoothed series in range[0, 1]. Default:0.2
- `nb` (float): Trend value in range[0, 1]. Default:0.1
- `nc` (float): Seasonality value in range[0, 1]. Default:0.1
- `nd` (float): Channel value in range[0, 1]. Default:0.1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# kc (Volatility)
> Keltner Channels

**Signature**:
`kc (high: Series, low: Series, close: Series, length: Int=None, scalar: IntFloat=None, tr: bool=None, mamode: str=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:20
- `scalar` (float): Band scalar. Default:2
- `mamode` (str): See help(ta.ma). Default:"ema"
- `offset` (int): Post shift. Default:0
- `tr` (bool): Use True Range calculation. Otherwise usehigh - lowfor range computation. Default:True
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# massi (Volatility)
> Mass Index

**Signature**:
`massi (high: Series, low: Series, fast: Int=None, slow: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `fast` (int): Fast period. Default:9
- `slow` (int): Slow period. Default:25
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# natr (Volatility)
> Normalized Average True Range

**Signature**:
`natr (high: Series, low: Series, close: Series, length: Int=None, scalar: IntFloat=None, mamode: str=None, talib: bool=None, prenan: bool=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:20
- `scalar` (float): Scalar. Default:100
- `mamode` (str): See help(ta.ma). Default:"ema"
- `talib` (bool): If installed, use TA Lib. Default:True
- `prenan` (bool): Sets initial values tonp.nanbased ondrift. Default:False
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# pdist (Volatility)
> Price Distance

**Signature**:
`pdist (open_: Series, high: Series, low: Series, close: Series, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `open_` (Series): open Series
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# rvi (Volatility)
> Relative Volatility Index

**Signature**:
`rvi (close: Series, high: Series=None, low: Series=None, length: Int=None, scalar: IntFloat=None, refined: bool=None, thirds: bool=None, mamode: str=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `scalar` (float): Bands scalar. Default:100
- `refined` (bool): Use 'refined' calculation which is the average of RVI(high) and RVI(low) instead of RVI(close). Default:False
- `thirds` (bool): Average ofhigh,lowandclose. Default:False
- `mamode` (str): See help(ta.ma). Default:"ema"
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# thermo (Volatility)
> Elders Thermometer

**Signature**:
`thermo (high: Series, low: Series, length: Int=None, long: Int=None, short: Int=None, mamode: str=None, asint: bool=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `length` (int): The period. Default:20
- `long` (int): Buy factor. Default:2
- `short` (float): Sell factor. Default:0.5
- `mamode` (str): See help(ta.ma). Default:"ema"
- `asint` (int): Returns as int. Default:True
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 4 columns

---

# true_range (Volatility)
> True Range

**Signature**:
`true_range (high: Series, low: Series, close: Series, talib: bool=None, prenan: bool=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `talib` (bool): If installed, use TA Lib. Default:True
- `prenan` (bool): Sets initial values tonanbased ondrift. Default:False
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# ui (Volatility)
> Ulcer Index

**Signature**:
`ui (close: Series, length: Int=None, scalar: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `length` (int): The period. Default:14
- `scalar` (float): Bands scalar. Default:100
- `offset` (int): Post shift. Default:0
- `everget` (value): Use Evergets' Trading View SMA. Default:False
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---


# Category: Volume

# ad (Volume)
> Accumulation/Distribution

**Signature**:
`ad (high: Series, low: Series, close: Series, volume: Series, open_: Series=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `volume` (Series): volume Series
- `open_` (Series): Optionalopen Series
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# adosc (Volume)
> Accumulation/Distribution Oscillator

**Signature**:
`adosc (high: Series, low: Series, close: Series, volume: Series, open_: Series=None, fast: Int=None, slow: Int=None, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `open_` (Series): open Series
- `volume` (Series): volume Series
- `fast` (int): Fast MA period. Default:12
- `slow` (int): Slow MA period. Default:26
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# aobv (Volume)
> Archer On Balance Volume

**Signature**:
`aobv (close: Series, volume: Series, fast: Int=None, slow: Int=None, max_lookback: Int=None, min_lookback: Int=None, mamode: str=None, run_length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `volume` (Series): volume Series
- `fast` (int): Fast MA period. Default:4
- `slow` (int): Slow MA period. Default:12
- `max_lookback` (int): Maximum OBV period. Default:2
- `min_lookback` (int): Minimum OBV period. Default:2
- `run_length` (int): Long and short run period. Default:2
- `mamode` (str): See help(ta.ma). Default:"ema"
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 6 columns

---

# cmf (Volume)
> Chaikin Money Flow

**Signature**:
`cmf (high: Series, low: Series, close: Series, volume: Series, open_: Series=None, length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `volume` (Series): volume Series
- `length` (int): The period. Default:20
- `offset` (int): Post shift. Default:0
- `open_` (Series): Optionalopen Series. Default:None
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# efi (Volume)
> Elder's Force Index

**Signature**:
`efi (close: Series, volume: Series, length: Int=None, mamode: str=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `volume` (Series): volume Series
- `length` (int): The period. Default:13
- `mamode` (str): See help(ta.ma). Default:"ema"
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# eom (Volume)
> Ease of Movement

**Signature**:
`eom (high: Series, low: Series, close: Series, volume: Series, length: Int=None, divisor: IntFloat=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `volume` (Series): volume Series
- `length` (int): The period. Default:14
- `divisor` (float): Divisor. Default:100_000_000
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# kvo (Volume)
> Klinger Volume Oscillator

**Signature**:
`kvo (high: Series, low: Series, close: Series, volume: Series, fast: Int=None, slow: Int=None, signal: Int=None, mamode: str=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `volume` (Series): volume Series
- `fast` (int): Fast MA period. Default:34
- `slow` (int): Slow MA period. Default:55
- `signal` (int): Signal period. Default:13
- `mamode` (str): See help(ta.ma). Default:"ema"
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# mfi (Volume)
> Money Flow Index

**Signature**:
`mfi (high: Series, low: Series, close: Series, volume: Series, length: Int=None, talib: bool=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `volume` (Series): volume Series
- `length` (int): The period. Default:14
- `talib` (bool): If installed, use TA Lib. Default:True
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# nvi (Volume)
> Negative Volume Index

**Signature**:
`nvi (close: Series, volume: Series, length: Int=None, initial: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `volume` (Series): volume Series
- `length` (int): The period. Default:13
- `initial` (int): Initial value. Default:1000
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# obv (Volume)
> On Balance Volume

**Signature**:
`obv (close: Series, volume: Series, talib: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `volume` (Series): volume Series
- `talib` (bool): If installed, use TA Lib. Default:True
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# pvi (Volume)
> Positive Volume Index

**Signature**:
`pvi (close: Series, volume: Series, length: Int=None, initial: Int=None, mamode: str=None, overlay: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `volume` (Series): volume Series
- `length` (int): The period. Default:255
- `initial` (int): Initial value. Default:100
- `mamode` (str): See help(ta.ma). Default:"ema"
- `overlay` (bool): Overlayinitial. Default:False
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 2 columns

---

# pvo (Volume)
> Percentage Volume Oscillator

**Signature**:
`pvo (volume: Series, fast: Int=None, slow: Int=None, signal: Int=None, scalar: IntFloat=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `volume` (Series): volume Series
- `fast` (int): Fast MA period. Default:12
- `slow` (int): Slow MA period. Default:26
- `signal` (int): Signal period. Default:9
- `scalar` (float): Scalar. Default:100
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# pvol (Volume)
> Price-Volume

**Signature**:
`pvol (close: Series, volume: Series, signed: bool=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `volume` (Series): volume Series
- `signed` (bool): Return with signs. Default:False
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# pvr (Volume)
> Price Volume Rank

**Signature**:
`pvr (close: Series, volume: Series, drift: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `volume` (Series): volume Series
- `drift` (int): Difference amount. Default:1

## Returns
- Series: 1 column

---

# pvt (Volume)
> Price-Volume Trend

**Signature**:
`pvt (close: Series, volume: Series, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `volume` (Series): volume Series
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# tsv (Volume)
> Time Segmented Value

**Signature**:
`tsv (close: Series, volume: Series, length: Int=None, signal: Int=None, mamode: str=None, drift: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `volume` (Series): volume Series
- `length` (int): The period. Default:18
- `signal` (int): Signal period. Default:10
- `mamode` (str): See help(ta.ma). Default:"sma"
- `drift` (int): Difference amount. Default:1
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 3 columns

---

# vhm (Volume)
> Volume Heatmap

**Signature**:
`vhm (volume: Series, length: Int=None, std_length=None, mamode: str=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `volume` (Series): volume Series
- `length` (int): The period. Default:610
- `std_length` (int): Standard devation. Default:610
- `mamode` (str): Mean MA. See help(ta.ma). Default:"sma"
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---

# vp (Volume)
> Volume Profile

**Signature**:
`vp (close: Series, volume: Series, width: Int=None, sort: bool=None, ** kwargs: DictLike ,) -> DataFrame`

## Parameters
- `close` (Series): close Series
- `volume` (Series): volume Series
- `width` (int): Source distrubution count. Default:10
- `sort` (value): Sortclosebefore splitting into ranges. Default:False
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- DataFrame: 5 columns

---

# vwap (Volume)
> Volume Weighted Average Price

**Signature**:
`vwap (high: Series, low: Series, close: Series, volume: Series, anchor: str=None, bands: List=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `high` (Series): high Series
- `low` (Series): low Series
- `close` (Series): close Series
- `volume` (Series): volume Series
- `anchor` (str): VWAP Anchor. Default:"D".
- `bands` (list): List of positive Int Floatdeviations. Default:[]
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series|pd.DataFrame: Data Framewhenbandsis set. Default:Series

---

# vwma (Volume)
> Volume Weighted Moving Average

**Signature**:
`vwma (close: Series, volume: Series, length: Int=None, offset: Int=None, ** kwargs: DictLike ,) -> Series`

## Parameters
- `close` (Series): close Series
- `volume` (Series): volume Series
- `length` (int): The period. Default:10
- `offset` (int): Post shift. Default:0
- `fillna` (value): pd.Data Frame.fillna(value)

## Returns
- Series: 1 column

---


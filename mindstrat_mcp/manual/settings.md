# Settings — what every control means, and which defaults lie

Read this before configuring a backtest or an optimization. Most of what is here is not discoverable from a tool response: several defaults produce confidently wrong results, and two adjacent fields use units that differ by 100×.

---

## 1. The cost model — the setting that decides whether a result means anything

**Every default in this app is commission 0 and slippage 0.** Not "low" — zero. It is the default in the Strategy Creator, in the engine itself, in the Optimizer form, in the Optimizer's stored configuration, in the Go Live screen and in the MCP deploy tool. A frictionless market makes every strategy look better than it is, and nothing in the UI warns about it.

It is worse than a stale form: the backend **never reads capital settings out of strategy code** — it returns an empty capital block by design — so the screen substitutes its defaults on every load. Loading a strategy that was saved with a real commission silently resets it to 0.

**So: pass `capital_cfg` explicitly on every call that accepts it, every time.** Nothing carries it forward for you.

```
initial_capital    the account the run starts with
order_size_mode    "fixed_value" | "fixed_qty" | "percent_of_equity"
order_size         meaning depends on the mode — see below
commission         a PERCENT of fill notional. 0.05 means 0.05% = 5 bps
commission_type    "percent" | "fixed"   ("fixed" = a flat amount per fill)
slippage_mode      "none" | "fixed" | "volume"
slippage_bps       BASIS POINTS. 5 means 5 bps = 0.05%
```

For Binance futures a realistic figure is **0.05 per side** (5 bps), charged per fill — so a round trip pays it twice. A stress run at 0.10 is a reasonable harsher setting.

Three traps in this block:

- **`commission` is a percent; `slippage_bps` is basis points.** They sit next to each other and differ by 100×. Entering `5` in both gives 500 bps of commission against 5 bps of slippage.
- **`slippage_bps` does nothing unless `slippage_mode` is `"fixed"`.** The mode defaults to `"none"`, and in that mode the price is returned untouched before the bps value is ever read. Set the two together or neither.
- **`order_size` means three different things** and the label never changes. Under `fixed_value` it is quote-currency notional; under `fixed_qty` it is base-asset contracts; under `percent_of_equity` it is a percent on a 0-100 scale — `10` means 10%, and `1.0` means 1%. Changing the mode does not re-seed the value, so a `fixed_value` of 1000 becomes 1000% of equity with one dropdown change.

Also worth knowing: `initial_capital` does not constrain position size. There is no margin or insufficient-funds check, so `fixed_value` sizing can trade far more notional than the account holds, and ROI is simply net profit over initial capital.

---

## 2. Units, across the whole app

| Quantity | Unit | Note |
|---|---|---|
| `commission` | percent of notional | `0.05` = 5 bps |
| `slippage_bps` | basis points | `5` = 5 bps. Inert without `slippage_mode: "fixed"` |
| `order_size` under `percent_of_equity` | percent, 0-100 | `10` = 10% |
| Win rate | **0-100** | Never multiply by 100 |
| ROI | percent, 0-100 | |
| Drawdown (optimizer / manager) | **negative currency**, not a percent | A filter of `>= -500` means "lost at most 500 quote currency peak-to-trough" |
| Monte Carlo mode parameters | **fractions, 0-1**, at the engine | The screen shows percentages and divides by 100. Writing them directly means `0.05`, not `5` |
| Monte Carlo `bootstrap.block_size` | **a number of trades** | The one MC parameter that is not a fraction |
| Monte Carlo score | stored 0-1, displayed ×100 | |
| Download `start` / `end` | **milliseconds** | Everything read back — dataset ranges, price windows, the optimizer's date window — is **seconds** |

---

## 3. The Optimizer

### Search method

A name that is not one the engine knows **silently falls back to `Random`**, so a typo costs a whole run. The methods:

| Method | How it searches | Use it when |
|---|---|---|
| `Random` | Uniform sampling | Mapping unknown terrain; the safe default |
| `Brute Force` | Every combination | The space is genuinely small — check the combination count first |
| `Random Improvements` | Random, building on what improves | Refining a known promising region |
| `Sequential Improvement` | One parameter at a time, in priority order | Few parameters, or you want each one's contribution |
| `Sequential MC` | Sequential, repeated over several loops | When one pass is not enough to settle |
| `Sequential Jump` | Sequential with jumps out of local optima | Sequential is getting stuck |
| `Annealing Thermal` | Wide early, narrow later | A rugged space where greedy search traps itself |

### Objective metric

**Only `profit` and `winrate` actually work.** The dropdown also offers `sharpe`, and the rolling dialog offers `sqn`, but neither key exists in the engine's metrics. The comparison reads a missing key as 0, so with one of those selected **every candidate scores 0, nothing ever beats anything, and the run's "best" is simply the first cycle evaluated** — with no error, and the run persists normally.

If you want risk-adjusted selection, optimise on `profit` and constrain the rest with metric filters.

### Parameter ranges

Each entry is `{from, to, step, default, active, priority}`.

**The TYPE of `default` decides how the range is expanded** — not the type of `step`. The engine walks the range in floats and casts each value back to the default's type:

- `default: 1` with `from 1, to 2, step 0.25` yields `[1, 1, 1, 1, 2]`. The cast truncates and the search collapses to two values.
- `default: 1.25` with the same range yields 1.0, 1.25, 1.5, 1.75, 2.0.
- A boolean default searches True/False; a string default with declared options searches that list.

This is silent, and an integer default for a percentage can include `0` — which for a stop-loss parameter means **searching candidates that have no stop at all**, and those will always look better on drawdown than they can ever be live.

A float default whose value happens to be whole (`1.0`) does not help: the form holds every cell as text and parses it with a single numeric type, so it arrives as an integer. **The workaround that survives is a default with a real fractional part that lands on the grid** — for `from 1, to 2, step 0.25`, pass `1.25`. The default is only a type carrier for the expansion, so any grid point works.

Two more:

- **`step: 0` or blank becomes `1.0`**, turning a requested fine sweep into whole-number steps with no warning.
- **`active: false` does not drop the row** — the parameter stays pinned at its default for every cycle. That is an active choice, not an absence.

Never name a strategy parameter after a capital field (`commission`, `order_size`, `initial_capital`, `slippage_bps`, …): the optimizer merges any searched parameter whose name collides into the cost configuration, so the run sweeps its own costs.

### Auxiliary slots

A strategy declares its slots in its own source. The names belong to the strategy and are not interchangeable — the backend rejects a key the code does not declare.

**An unfilled slot does not fail the run; it fails every cycle of the run.** The strategy raises on its first bar without the data, so a thousand-cycle run produces a thousand identical errors. The validation is one-way: the start endpoint checks the keys you *sent* against the declarations, never the reverse.

### Robustness: when each test runs

| `trigger_mode` | Meaning |
|---|---|
| `cycles` + `trigger: N` | Every N cycles — only a fraction of candidates end up with evidence |
| `new_best` | Whenever a new best appears |
| `every_pass` | Every cycle — every candidate comparable to every other |

Robustness costs **wall-clock, not memory**. Results are batched into a bounded queue and written by a separate process, and Monte Carlo's simulated curves are summarised and dropped inside the worker — only the summary and the seed persist. So the budget to reason about is time: hold-out roughly doubles a cycle's work, Monte Carlo scales with `modes × curves`, and intrabar is the expensive one because it re-runs bars at a finer timeframe.

`max_ram_pct` is a backstop for the worker pool. **Omitting it does not apply a default — it disables the RAM monitor entirely.** Always send it; the app's own value is 80.

### Robustness: walk-forward

- **`holdout`** — one split. `split_pct: 70` trains on the first 70% and validates on the last 30%.
- **`rolling`** — `folds: N` moving train/validation windows. Slower, but shows whether the edge is stable across eras rather than lucky in one split.

Results come back as `is_*` (in-sample) and `val_*` (validation). Read them from the backend; win rate is on a 0-100 scale.

**A rolling run that dies of memory pressure is recorded as finished with zero folds and no error.** Always confirm the fold count is non-zero before trusting a rolling result.

### Robustness: Monte Carlo

All modes perturb the **sequence of trade P&Ls**, not the market data. `curves` is simulations per mode — and the total is `curves × modes`, not `curves`. Fewer than 30 simulations for a mode drops it from scoring entirely; if every mode is dropped the run finishes with no score at all.

Parameters below are in **engine units (fractions)**:

| Mode | Perturbation | Parameters (defaults) | What it answers |
|---|---|---|---|
| `shuffle` | Reorders the trades | — | Was the drawdown an accident of ordering? Cannot test the edge — reordering does not change the total |
| `bootstrap` | Resamples in blocks | `block_size` (10 — **trades**, not a fraction) | Does the edge hold on resampled histories? |
| `drop_pct` | Removes a random share | `pct_min` (0.10), `pct_max` (0.30) | Does it survive missing trades? |
| `drop_best_trades` | Removes the best ones | `pct` (0.10), `jitter` (0.03) | Does the profit depend on a handful of winners? |
| `drop_cluster` | Removes a contiguous run | `cluster_pct_min` (0.05), `cluster_pct_max` (0.15) | Does it survive a bad streak or an outage? |
| `noise_injection` | Perturbs each P&L | `noise_pct` (0.05) | Sensitivity to fill quality |
| `cost_degradation` | Haircuts each trade's P&L | `max_cost_pct` (0.03) | See the caveat below |
| `time_slice` | Uses one window only | `window_pct` (0.40) | Is it a regime artefact? |

Two caveats. `jitter: 0` makes `drop_best_trades` deterministic — every simulation removes the same trades, so it stops being Monte Carlo. And **`cost_degradation` is not a commission test**: it subtracts a share of each trade's own magnitude, never re-runs the backtest and never touches `capital_cfg`. A real commission increase falls hardest on small-P&L trades; this falls hardest on large ones. To test costs, re-run with a higher `commission`.

### Robustness: intrabar

When a strategy exits on take-profit or stop-loss and both levels sit inside one candle, the engine has to decide which was touched first. Symptoms of the ambiguity in results: trades with zero bars in trade, identical entry and exit timestamps.

Intrabar replays those bars at a finer timeframe to resolve the ordering. **With it off, the tie is resolved worst-case-first — booked as the stop.** So enabling it can make a result look better, not worse.

The finer timeframe is **mapped, not 1-minute**:

| Chart | Replay | Chart | Replay | Chart | Replay |
|---|---|---|---|---|---|
| 1m | 1m | 1h | 15m | 8h | 2h |
| 3m | 1m | 2h | 30m | 12h | 4h |
| 5m | 1m | 4h | 1h | 1d | 4h |
| 15m | 5m | 6h | 1h | 1w | 1d |
| 30m | 5m | | | 1M | 1w |

The finer dataset must already be downloaded and must cover the window. In the Strategy Creator a missing one is a hard error; **in the Optimizer it degrades silently** — the run continues without intrabar and is still recorded as having used it. Confirm the finer dataset exists before configuring a run that depends on it.

### Metric filters

Filters decide **which cycles are written to the database at all**. A candidate a filter rejects is counted as generated and then discarded — it cannot be recovered afterwards. A run that saves zero cycles because of an inherited filter looks exactly like a broken strategy.

A filter whose key is not in the metrics dict, or whose value is null, is skipped silently.

---

## 4. When zero does not mean zero

| Setting | `0` means |
|---|---|
| `commission` | no fee at all — and the detail view renders it as the word "None", so a deliberate zero and a never-configured one look identical |
| `slippage_bps` | slippage off, even with the mode set to `fixed` |
| Stop-loss / take-profit percentage | **no stop / no target** — the level is only stored when it is above zero |
| `max_ram_pct` | no RAM ceiling |
| Parameter `step` | step 1.0 |
| Monte Carlo `curves` | 30 (the minimum), not zero |
| `duplicates` on a dataset | nobody counted |

The one loud exception: an `order_size` of 0 raises on the first trade rather than being skipped, which is why a zeroed order size surfaces as "every cycle failed" instead of "no trades".

---

## 5. Values that are quietly replaced

- An unknown **search method** → `Random`.
- An unknown **objective metric** → accepted, then every candidate scores 0.
- An unknown **`commission_type`** → zero commission.
- **Unparseable** commission or slippage text → 0.0. A typo in the commission box produces a costless run.
- An **optimizer date window** that selects no bars → silently reset to the dataset's full span.
- **Intrabar** whose finer dataset fails to load, inside an optimizer run → disabled for the whole run, printed to the backend console only.
- A **hold-out** with no derivable split → runs as if disabled, producing no validation data and no error.

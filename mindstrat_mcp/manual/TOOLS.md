# Tool catalogue

56 tools across six groups. Every one but `lookup_indicator` is a thin wrapper
over the app's local HTTP API: the MCP server never computes trading results, it
calls the same endpoints the desktop screens call and reshapes the response so
it fits in a model's context. (`lookup_indicator` reads the indicator catalogues from the manual that ships
with this server, under `manual/`.)

What the app is and what each section does is in `mindstrat://product-map`;
what every control means is in `mindstrat://settings`. This server registers
no prompts.

Legend: **RO** read-only · **D** destructive (needs `confirm=true`) ·
**live-gated** also needs `MINDSTRAT_MCP_ALLOW_LIVE=1`.

## System

| Tool | Purpose | Backend |
|---|---|---|
| `backend_status` **RO** | Confirm the app is up and report the port it was found on. Call this first when anything fails to connect. | `GET /health` |

## Market Assets

Everything under `/assets` is gated on the signed-in desktop session (like the
other product routers), so these tools need the app signed in. The download
queue is the backend's own — jobs survive as long as the backend does, and are
lost on restart.

| Tool | Purpose | Backend |
|---|---|---|
| `assets_overview` **RO** | Environments for an exchange, tradable symbols, and total storage used. | `GET /assets/environments`, `/symbols`, `/metrics` |
| `list_datasets` **RO** | Downloaded datasets with row counts, date coverage and size. Filter by symbol/timeframe. | `GET /assets/datasets` |
| `start_download` | Queue a candle download. `start`/`end` are UNIX **milliseconds**; omit for full history. | `POST /assets/downloads/jobs` |
| `get_download_jobs` **RO** | Poll one job or list recent ones: `queued\|running\|completed\|failed\|cancelled`, progress 0-100, `snapshot_id` when done. | `GET /assets/downloads/jobs[/{id}]` |
| `cancel_download` | Cancel a queued or running job. | `DELETE /assets/downloads/jobs/{id}` |
| `maintain_dataset` | `refresh` extends a dataset to the latest candle; `repair_gaps` refills missing bars. Both return a job to poll. | `POST /assets/datasets/{id}/refresh` \| `/repair-gaps` |
| `delete_dataset` **D** | Delete a snapshot. Strategies referencing it lose their data. | `DELETE /assets/datasets/{id}` |

## Code Creator

### Knowing what to write

| Tool | Purpose | Source |
|---|---|---|
| `lookup_indicator` **RO** | One indicator's documented signature **and which library must implement it**. Convergent → pandas-ta inline; path-dependent → talipp + `engine.persist`. Names the trap when both libraries expose the same indicator, and routes to the DIY persist recipe for path-dependent ones talipp lacks. Accepts either catalogue's spelling (`psar` or `ParabolicSAR`). | `pandas_ta_reference.md`, `talipp_reference.md`, `runtime_constraints.md` §9 |

> The library assignment is the mechanical decision that decides whether a
> strategy behaves in live the way it did in the backtest. Implementing a
> path-dependent indicator with pandas-ta — `ta.supertrend()`, `ta.obv()`,
> `ta.psar()`, `ta.vwap()` — passes the backtest and silently breaks in live.
> Call this once per indicator instead of deciding from memory.

The rest of the manual is served as resources, not tools:
`mindstrat://msf/parity` (the rule that keeps live and backtest agreeing),
`mindstrat://msf/canon`, `mindstrat://msf/runtime-constraints`,
`mindstrat://msf/template`, `mindstrat://msf/examples` and
`mindstrat://msf/visualization`.

### Building a strategy — the editor loop

These four drive the Code Creator session, which is server-side state shared
with the open screen. They mirror how a person uses it: load, run, adjust, run
again, and save only once the strategy holds up.

| Tool | Purpose | Backend |
|---|---|---|
| `editor_load_code` **D** | Load strategy code into the screen and return the parameters, capital settings and auxiliary dataset slots it declares. Destructive because it replaces whatever is loaded, including unsaved work. | `POST /strategies/parameters` |
| `editor_run_backtest` | Backtest what is currently loaded, against `dataset_id`. Returns metrics and execution errors; trade lists and chart series are stripped. | `POST /strategies/run` |
| `editor_set_parameters` | Change parameter values. The backend rewrites the code with them, so the next run picks them up. | `POST /strategies/update` |
| `editor_save_to_library` | Save as a saved strategy, keeping the trades and metrics of the last run. `symbol`/`timeframe` default to the dataset's. | `POST /strategies/library/save-strategy` |

> `editor_run_backtest` deliberately sends **no** `code` field. The backend would
> treat it as an override and discard the parameter edits, which are applied by
> rewriting the in-memory source. A unit test pins this.

### Reading and running without touching the editor

| Tool | Purpose | Backend |
|---|---|---|
| `list_saved_strategies` **RO** | The saved-strategy library, metadata only. | `GET /ai/tools/list_strategies` |
| `get_saved_strategy` **RO** | One strategy; source only with `include_code=true`. | `GET /ai/tools/get_strategy` |
| `list_backtest_datasets` **RO** | Datasets as the creator sees them. | `GET /ai/tools/list_datasets` |
| `get_dataset_summary` **RO** | Coverage and data quality for one dataset (rows, range, missing, duplicates, size) — the same record the Market Assets screen shows. | `GET /assets/datasets` |
| `get_intrabar_timeframes` **RO** | The intrabar timeframes the app offers for a chart timeframe, and the default it picks when none is given. Call before enabling intrabar anywhere. | `GET /strategies/intrabar-timeframes/{tf}` |
| `get_price_window` **RO** | A bounded OHLCV window, max 500 bars. Accepts ISO-8601 or epoch seconds. | `GET /strategies/datasets/{id}/bars` |
| `list_backtests` **RO** | Stored backtests with headline metrics. | `GET /ai/tools/list_backtests` |
| `get_backtest` **RO** | One backtest's metrics; `"latest"` reads the last run. | `GET /ai/tools/get_backtest` |
| `get_backtest_trades` **RO** | Trades page (max 30) plus a summary over the whole filtered set. | `GET /ai/tools/get_trades` |
| `run_backtest` | Headless backtest of a saved strategy **or** arbitrary code. Leaves the editor session untouched. | `POST /ai/tools/run_backtest_from_strategy` \| `_from_code` |
| `run_python` | Persistent Python kernel with the `ms` SDK, pandas and pandas-ta. Uses its own `chat_id` namespace so it never collides with the app's chat kernels. | `POST /ai/kernel/run`, `/ai/kernel/kill` |

## Strategy Manager

| Tool | Purpose | Backend |
|---|---|---|
| `list_manager_strategies` **RO** | Saved strategies with filters (search, symbol, timeframe, active robustness methods, favourites, metric predicates) and sorting. | `GET /manager/strategies` |
| `get_strategy_detail` **RO** | Metrics, extended metrics, robustness and capital config. Trade lists and chart series are removed. | `GET /manager/strategies/{id}/detail` |
| `get_strategy_trades` **RO** | Page the trade events out of that same response, with filters (event type, outcome, profit range, signal text) and a summary over all matching final closes. The rows are the raw engine event log, not paired positions. | same endpoint |
| `list_metric_filters` **RO** | The metric vocabulary a `metrics_filter` can be built from: keys, bounds, operators and a worked example. | `GET /manager/strategies/metric-sections` |
| `list_optimizations` **RO** | Optimization runs. | `GET /manager/optimizations` |
| `get_optimization_summary` **RO** | One run's summary and totals — the light endpoint, safe on huge runs. Each active robustness test reports where its own results live. | `GET /manager/optimizations/{id}/metadata` |
| `list_optimization_cycles` **RO** | Cycles paginated, sortable (`cycle`, `profit`, `metrics.X`) and filterable by profit, trades, drawdown, win rate. Each row carries the manager table's three families: its metrics, its HoldOut block (`is_*`/`val_*`) and its Monte Carlo `mc_score`/`mc_tier`. | `GET .../cycles` + `/metadata` |
| `get_cycle_robustness` **RO** | One cycle's robustness evidence: the HoldOut train/validation/full comparison and the Monte Carlo score, distribution and per-mode breakdown. No simulated curves — `equity_shape` instead. | `GET .../cycles/{n}/detail` + `/cycles` |
| `get_cycle_detail` **RO** | One cycle in full, stripped like a strategy detail. | `GET .../cycles/{n}/detail` |
| `update_strategy_meta` | Favourite, rename, set description. | `POST /manager/strategies/{id}/favorite` \| `/rename` \| `/description` |
| `save_cycle_as_strategy` | Persist a cycle as a saved strategy through the backend's job queue, polling briefly for the result. | `POST /manager/snapshots` |
| `create_strategy_from_rolling` | Graduate a **template-origin** rolling run into a new saved strategy carrying the whole WalkForwardRolling bucket. Saved-origin runs use `attach_rolling_to_strategy` instead. | `POST /manager/strategies/from-rolling` |
| `list_portfolios` **RO** | Portfolios with strategy counts and metric summaries. | `GET /manager/portfolios` |
| `get_portfolio` **RO** | One portfolio's combined book: summary, totals, metrics, member contributions. Trades and the combined curve are stripped. | `GET /manager/portfolios/{id}` |
| `manage_portfolio` **D** | Create, update, delete a portfolio or add a strategy to one. Delete needs `confirm=true`. | `POST/PUT/DELETE /manager/portfolios...` |
| `delete_manager_items` **D** | Delete a strategy or an optimization through the deletion queue. | `POST /manager/deletions` |
| `get_manager_job_status` **RO** | Poll the snapshot and deletion queues. A completed snapshot job points at the finalist validation pass. | `GET /manager/{snapshots\|deletions}/jobs/{id}` |

> `save_cycle_as_strategy` takes the cycle's parameters and metrics from the
> cycles listing, not from the cycle detail. The detail endpoint re-runs the
> backtest and its numbers can differ from what the run recorded; the app saves
> the recorded ones.

## Optimizer

| Tool | Purpose | Backend |
|---|---|---|
| `prepare_optimization` **RO** | Build a runnable configuration from a saved strategy — base parameters, ranges, capital config, robustness config, auxiliary datasets — plus the size of the search space. Ranges come back only if the strategy has them saved — choosing them is an analysis decision, not a default to fill in. | `GET /strategies/saved/{id}/optimizer-sync`, `POST /optimizer/parameters/preview` |
| `configure_optimization` | Fill in the Optimizer screen's form — strategy, dataset, search space, method, metric, cycles, robustness (walk-forward, Monte Carlo **and intrabar**), the sequential methods' own budgets, and auxiliary datasets — then ask the screen to show it, and start nothing. Works with the screen closed; `screen_updated` says whether it is on display. Workers and RAM cap stay the user's unless overridden. | `POST /optimizer/settings` + `reload_config` |
| `start_optimization` | Press Start on that screen, running what is configured there. No arguments. | `POST /optimizer/panel/command` |
| `get_optimization_status` **RO** | Cycles saved, best profit, and `state` (`running`/`finished`) read from the engine itself — the stored status column never leaves 'running'. A finished run's response carries the selection sequence as `next_step`. | `GET /manager/optimizations/{id}/metadata` + `GET /optimizer/jobs/active` |
| `control_optimization` | Pause, resume, stop, or rescale workers — through the screen, like the start. | `POST /optimizer/panel/command` |
| `get_optimizer_capacity` **RO** | System RAM next to the user's configured workers and RAM cap, for sizing a run. | `GET /optimizer/system-info` + `/settings` |
| `validate_finalist` | The finalist battery against a **saved strategy, unchanged**: rolling folds + harsh Monte Carlo modes at `every_pass` + intrabar, configured as a one-combination run (one numeric parameter pinned to its own value, Brute Force, 1 cycle). | composes `configure_optimization` + `start_optimization` |
| `attach_rolling_to_strategy` | Attach a **saved-origin** rolling run's folds to its strategy — the last step of finalist validation. Template-origin runs use `create_strategy_from_rolling`. | `POST /strategies/saved/{id}/attach-rolling` |

> Every parameter range needs a `default`: the optimizer decides how to expand
> a range from that value's *type*. Without one it generates null parameters and
> every cycle fails with `int() argument ... not 'NoneType'`, wasting the run.
> `configure_optimization` fills it from the strategy's base parameters and
> refuses when it cannot.

**Configuring and starting are separate because the app separates them, and
because the start has to happen where the user's start happens.** The screen's
own handler validates the form, shapes the payloads the engine expects — the
cycles budget becomes a `(mode, loops)` pair for Sequential MC and a jump
config for Sequential Jump, and a rolling walk-forward rewrites it into cycles
per fold — then binds the run's ticket, opens the result stream and resets the
per-run buffers. A run launched straight at `POST /optimizer/jobs/start` gets
none of that, stops producing cycles when it reaches its budget and never
declares itself finished — leaving the backend refusing new runs. So the MCP
configures the form and asks the screen to press its button.

Both go through `POST /optimizer/panel/command`, a single-slot mailbox the
screen polls once a second while it is mounted and acks with `done` or
`rejected` plus its own message. Configuring queues `reload_config` after
writing the preset, because the screen hydrates its form when it mounts and
only then — without it an open screen would keep showing the previous run.

The consequence: **the Optimizer screen must be open to start.** If it is not,
the command waits up to ten minutes and then expires, and the tool says so
rather than reporting a run that never began — an optimization firing an hour
later, when the screen next happens to open, is a surprise with a real compute
cost. Configuring has no such requirement: the preset is on disk either way,
and `screen_updated: false` reports that nothing is on display yet.

Results are read with the Strategy Manager tools above. The optimization itself
— search method, workers, robustness tests, Monte Carlo perturbations,
persistence — runs entirely inside the app.

`prepare_optimization` returns the whole catalogue: the seven search methods,
the eight Monte Carlo perturbations with their parameters, the walk-forward
modes, intrabar, and the trigger modes that decide how often each test runs. It
also returns `range_warnings` for ranges that will not search what you intend.
`mindstrat://settings` explains what each one means, in what units, and which
defaults lie. Three things are worth knowing before the first run:

> A `method` that is not one of the seven **silently falls back to `Random`**.
>
> The objective `metric` accepts only `profit` and `winrate`. `sharpe` is
> offered by the screen but does not exist in the engine, so selecting it
> makes every candidate score 0 and the run's "best" is whichever cycle was
> evaluated first — with no error.
>
> Any strategy that exits on TP/SL needs the `intrabar` test before its numbers
> mean anything — otherwise the engine is guessing which level a candle hit
> first.

## Live trading

These act as the user signed in to the desktop app — this server holds no
credentials, and the backend attaches the app's session. Reads need only that
the user be signed in; mutations need the flag **and** `confirm=true`.

| Tool | Purpose | Backend |
|---|---|---|
| `live_auth_status` **RO** | Whether the app is signed in, which account, session expiry, and whether mutations are enabled. | `GET /auth/desktop-session` |
| `list_live_strategies` **RO** | Deployed strategies: observed `status` vs `desired_state`, P&L, wins/losses, last error. | `GET /live/strategies` |
| `get_live_strategy` **RO** | One strategy by section: `summary`, `trades`, `events` or `config`, paginated. | `GET /live/strategies/{id}/details`, `/config` |
| `list_exchange_accounts` **RO** | Connected exchange accounts with masked keys. | `GET /exchanges/accounts` |
| `deploy_live_strategy` **D** live-gated | Full three-step deploy: fetch the strategy code, request presigned URLs, upload code and config to S3, then create. Deploying to `live` additionally requires `exchange_account_id`. | `POST /live/strategies/upload_init` → S3 PUTs → `POST /live/strategies` |
| `stop_live_strategy` **D** live-gated | Request a stop; convergence is observed by re-reading the listing. | `POST /live/strategies/{id}/stop` |
| `update_live_order_size` **D** live-gated | Change order size on a running strategy, effective from the next trade. | `PATCH /live/strategies/{id}/config` |

## Not exposed, and why

- **The Market Assets watchlist** lives in the frontend's localStorage. There is
  no endpoint, so an external process cannot read it.
- **Frontend-zone AI chat tools** (`get_active_editor_state`,
  `propose_strategy_edit`) read the webview's stores. The `editor_*` tools reach
  the same session through the backend instead.
- **`/strategies/cancel`, `/reset`, `/save`** are editor-session verbs that on
  their own would only corrupt the user's screen state.
- **Bulk endpoints** are never called raw: `/optimizer/history/load` returns an
  entire dataset, and `/manager/optimizations/{id}` without paging returns every
  cycle plus its curves.
- **Download schedules** (`/assets/downloads/schedules`) are user-owned
  automation: a recurring job an agent sets up outlives the conversation that
  asked for it, silently spending bandwidth. One-shot downloads plus
  `maintain_dataset` cover the research need.
- **Dataset import/export** (`/assets/datasets/import`, `/file`, `/export`)
  move files by local path, which an MCP client cannot meaningfully provide or
  receive over stdio.
- **Snapshot/deletion job cancels** — the jobs are short-lived; by the time a
  cancel lands they are done.
- **Exchange account creation/removal** (`POST/DELETE /exchanges/accounts`) —
  API credentials enter through the app's own UI, never through an agent.

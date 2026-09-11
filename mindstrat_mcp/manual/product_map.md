# The MindStrat product map

What the app is, what each section does, and the vocabulary you need before you touch anything.

MindStrat is a Windows desktop application for building, testing and deploying algorithmic trading strategies. It runs a local Python backend on the user's own machine; this MCP server talks to that backend over loopback HTTP. **You are operating the user's running app, not a copy of it.** Everything you write lands on the screen they are looking at, and everything you read is the app's own answer — never recompute a metric, a backtest or a robustness score from a trade list.

The app must be running for any tool to work, and the user must be signed in: the local engine is gated on a session the app mirrors into the backend. When a call comes back `401 local.no_session`, the user is signed out or the backend restarted and lost the mirror. You cannot repair it — there is no credential here. Ask them to sign in, or simply to focus the MindStrat window, which re-mirrors.

---

## The six sections, in the order work flows through them

### 1. Market Assets — the historical data store

Where OHLCV candle history is downloaded and kept. Everything downstream consumes a dataset from here, so this is where a research pass starts.

The user picks an exchange, an environment (spot / futures), a symbol, a timeframe and a date range, and queues a download. Each completed download is an immutable **snapshot**: one directory, one CSV, one row in that partition's index. The screen also reports each dataset's coverage and quality — row count, date range, missing bars, duplicates — maintains existing datasets (extend to the latest candle, or refill gaps), and deletes them.

Two things to know before you choose a dataset:

- **The table's rows are aggregates, not snapshots.** A row sums every snapshot of one (exchange, environment, symbol, timeframe) and shows `min(start)..max(end)` — a span no single snapshot need actually cover. The addressable unit is the snapshot.
- **The biggest snapshot is often not the most recent.** Re-downloading "all history" for a symbol that already has data does not start from the beginning: it resolves the start to just after the newest existing end, so it creates a new snapshot holding only the missing tail. A partition can end up with one large snapshot that stops months ago and a small one that is current. **Rank candidates by `end` first, then by rows**, and state the range of the snapshot you chose.

Also: `duplicates: 0` means nobody counted, not that there are none. For a timeframe outside the standard set, `missing: 0` means "not computable" too.

### 2. Strategy Creator — the authoring surface

Where one strategy's Python source is written, parameterised, backtested against one dataset, and saved to the library. A single-strategy, single-dataset workbench: no sweeps, no walk-forward, no portfolios — those live elsewhere.

The unit of work is a loop: load code → run a backtest → adjust parameters → run again → save once it holds up.

The screen exposes the strategy's own parameters as UI controls (generated from the module-level `strategy_parameters` dict), the dataset selector plus one selector per declared auxiliary slot, the capital/cost configuration, an intrabar toggle, the results panel and the chart.

**This screen's state is shared with you.** The loaded code, its parameters and the last backtest live in backend module globals — one set for the whole process, not one per caller. Loading code through the MCP replaces what the user has open, including unsaved work. See "What you share with the user" below.

### 3. Strategy Optimizer — the parameter search

Where a saved strategy's parameters are swept and the survivors are tested for robustness. Takes a saved strategy, a dataset, a search space (a `{from, to, step, default}` range per parameter), a search method, an objective metric and a cycle budget; produces a run holding one **cycle** per candidate that passed the run's filters.

On top of the search it can run three robustness tests — walk-forward (hold-out or rolling folds), Monte Carlo (resampling the trade sequence), and intrabar simulation (replaying each bar at a finer timeframe so take-profit and stop-loss fills are resolved rather than assumed).

Configuring and starting are separate calls on purpose, so the user can review a multi-hour run before it launches. Everything that defines the run is settable; the machine settings (worker count, RAM ceiling) stay the user's unless there is a stated reason to override them.

What each control means, and which defaults lie, is in `mindstrat://settings`.

### 4. Strategy Manager — the library and the results browser

Two things live here, and they are different objects: **saved strategies** and **optimization runs**.

A saved strategy is the deployable unit — code plus one parameter set plus the metrics recorded for it. An optimization run is a search that produced many cycles, none of which is a saved strategy until you promote one.

The screen lists both with filters (text, symbol, timeframe, favourite, active robustness methods, and predicates over metrics) and opens a detail view per item: headline and extended metrics, the equity curve, the trade list, the capital configuration and the robustness evidence.

Two traps worth carrying:

- **The status column is meaningless.** A run is written as `running` and nothing ever updates it, so a finished run, a crashed run and a live one are indistinguishable there. Ask the Optimizer for a run's real state instead.
- **The trade rows are the engine's raw event log** — an open row and a close row per position, plus pyramid and partial-close rows. They are not paired round-trips. Summing them double-counts. The headline metrics come from the app; do not recompute them from this list.

### 5. Portfolios — combining validated strategies

A portfolio is a named grouping of saved strategies re-run and merged into one combined track record. It owns no code; members are references plus a cached trade list and a frozen copy of each member's data taken when it was added.

Adding a member is synchronous and expensive — it re-runs that strategy's full backtest to build the cache, and can take minutes. If the rebuild fails the member stays in the book with an empty cache: it still takes its slice of capital and contributes nothing, so the totals are quietly a different book. Check each member's cache state before quoting an aggregate.

**A strategy cannot be removed from a portfolio** — not through the MCP, not over HTTP, not in the UI. The only exits are deleting the saved strategy (which removes it from every portfolio) or deleting and rebuilding the portfolio. Say so rather than promising a removal.

### 6. Live Trading — deployment

Where a strategy stops being research and starts sending orders. The user picks a saved strategy, pins it to a symbol, timeframe and exchange profile, chooses an environment, sets the capital configuration and deploys.

`environment="demo"` paper-trades against the exchange's testnet. **`environment="live"` trades real money** on the user's own account through a stored API key.

From then on it is a monitoring surface: status per deployed strategy, P&L, trades, events, and two mutations — change the order size, or stop.

Three things that are not obvious:

- **Stopping is asynchronous and does not close the position.** It tells the strategy to stop deciding; anything open stays open on the exchange, and its take-profit and stop-loss stop being watched. Never report a stop as "position closed" — tell the user to close it themselves if they hold one.
- **API keys enter through the app's UI only.** You can list accounts; you can never create or delete one.
- **Live mutations are gated twice** — by an environment flag on this server *and* an explicit confirmation — and the deploy inherits none of the strategy's saved cost configuration by default. Pass it explicitly; see `mindstrat://settings`.

---

## The vocabulary — nouns you must not confuse

Several of these look interchangeable and are not. Passing the wrong one is the most common way a call fails for a reason you cannot see from the response.

| Noun | What it is | Identifier |
|---|---|---|
| **dataset** (as the table shows it) | A display aggregate over every snapshot of one (exchange, environment, symbol, timeframe). | **No id of its own.** Addressed by that tuple. |
| **snapshot** | One immutable download. The real, addressable unit of market data. | 32 lowercase hex, no dashes. The same string appears as `snapshot_id`, `dataset_id` and `hist_id` — they are one thing under three names. |
| **auxiliary slot** | An extra price feed the strategy declares in its own source. | A slot KEY chosen by the strategy author (e.g. `dataset_2`) mapped to a snapshot id. The backend rejects a key the code does not declare, but never checks that you filled them all — a missing one fails on the first bar of every cycle. |
| **saved strategy** | Code + one parameter set + its recorded metrics. The only object that can go live or into a portfolio. | **Integer.** |
| **backtest** | One evaluation of one parameter set over one window under one cost model. A computation, not a stored object. | The literal string `"latest"` — there is one shared slot, and every run overwrites it. |
| **optimization run** | One search: one code, one dataset, one window, one method, one robustness config. Owns N cycles. | **Integer** for every read tool. (The engine also has its own string handle for a running job — do not mix them.) |
| **cycle** | One candidate inside a run that was evaluated and accepted. A candidate rejected by the run's filters is never stored and cannot be recovered. | A 1-based integer **unique only within its run** — address a cycle as the pair (run, cycle). It is a position in a stream, not an identity. |
| **portfolio** | A named grouping of saved strategies. | **Integer.** Names are not unique — always address by id. |
| **live strategy** | A deployed instance running against an exchange. | An **opaque string** minted on deploy. It carries the saved strategy's integer id as a separate field. Passing one where the other belongs is the classic failure here. |
| **exchange account** | A stored API key, secret masked. | An **opaque string**, distinct from the exchange *slug*, which is a composed identifier with a strict grammar. |
| **job** | Background work: a download, a snapshot (promoting a cycle), or a deletion. | 32 hex — **in all three queues**, so an id alone does not say which queue it belongs to. |

"Candidate" and "finalist" are vocabulary, not objects. A candidate is a cycle you are considering; a finalist is a saved strategy you have validated. Promoting a candidate creates a *new* saved strategy, and promoting the same cycle twice creates two.

---

## What you share with the user

Three pieces of state are global to the backend process — one set for everyone, not one per caller. Writing them is visible on the user's screen within seconds.

**The Strategy Creator session.** The loaded code, its parameters and the loaded dataset. Loading code through the MCP replaces whatever the user has open, including unsaved work, with no undo — which is why it requires an explicit confirmation. The screen polls and adopts changes it did not make itself, so your edit visibly takes over their editor. Do not do it while the in-app AI chat is mid-turn.

**The last backtest.** A single slot holding the most recent run's trades, metrics and cost configuration. Every backtest overwrites it — including a "headless" one. This is the basis the user's own *Save as Strategy* button reads from, so a run of yours can make their save fail, or worse, save your numbers under their strategy's name. If they have work in the editor they intend to save, tell them to save first.

**The Optimizer configuration.** A single file holding the entire form. Configuring through the MCP overwrites it wholesale rather than merging, and an open Optimizer screen re-reads it. Anything you do not set is inherited from whatever the user last left there — including the metric filters, which decide which cycles are written to the database at all. State plainly what you set and what you inherited.

---

## Resources of which there is exactly one

- **The optimization run slot.** One run app-wide. You cannot start one while the user is running one, and a start is refused for several seconds after a run ends while its workers tear down.
- **The download worker.** One queue, drained one job at a time across the whole app.
- **The "latest" backtest**, and **the Optimizer configuration** — see above.
- **Your Python kernel.** One per MCP server process, not shared with the in-app assistant or with another MCP session. Variables loaded in one are invisible to the other.
- **Detail windows.** One per strategy or cycle. Re-opening focuses the existing window rather than refetching, so a long-open one shows stale numbers — and you cannot open, focus or close any of them.

## What survives an app restart, and what does not

**Survives**, on disk or in the cloud: downloaded datasets, the strategy database (saved strategies, runs, cycles, portfolios), the Optimizer configuration, and everything live — deployed strategies, their trades and events, exchange keys.

**Lost**, because it lives in backend memory: the signed-in session mirror, the download queue, the Strategy Creator session and the last backtest, a running optimization's in-flight batch, the snapshot and deletion job queues, and every Python kernel namespace.

Two consequences worth acting on. A job that vanished after a restart is indistinguishable from one that never ran — poll by job id rather than scanning a list. And after a restart the first calls will fail with a session error until the user focuses the app window.

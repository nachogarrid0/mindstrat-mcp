"""MindStrat MCP server (stdio transport).

Exposes the local MindStrat backend as MCP tools so an agent can drive the
desktop app while it is running. This is the only module that imports the MCP
SDK; tool implementations live in ``mindstrat_mcp/tools/`` as plain async
functions taking a BackendClient.

Entry point: the ``mindstrat-mcp`` console script (see pyproject.toml).
Registered with: claude mcp add mindstrat -- uvx --from git+<repo> mindstrat-mcp
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402

from mindstrat_mcp import config  # noqa: E402
from mindstrat_mcp.client import BackendClient  # noqa: E402
from mindstrat_mcp.tools import assets as assets_tools  # noqa: E402
from mindstrat_mcp.tools import creator as creator_tools  # noqa: E402
from mindstrat_mcp.tools import knowledge as knowledge_tools  # noqa: E402
from mindstrat_mcp.tools import live as live_tools  # noqa: E402
from mindstrat_mcp.tools import manager as manager_tools  # noqa: E402
from mindstrat_mcp.tools import optimizer as optimizer_tools  # noqa: E402
from mindstrat_mcp.tools import system as system_tools  # noqa: E402


def _configure_logging() -> None:
    """Log to stderr and a rotating file. Never stdout: it carries the protocol."""
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    try:
        log_path = config.mcp_state_dir() / "mcp.log"
        handlers.append(
            RotatingFileHandler(
                log_path, maxBytes=2_000_000, backupCount=2, encoding="utf-8"
            )
        )
    except OSError:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


_configure_logging()
logger = logging.getLogger("mindstrat.mcp")

READ_ONLY = ToolAnnotations(read_only_hint=True)
DESTRUCTIVE = ToolAnnotations(destructive_hint=True, idempotent_hint=False)

INSTRUCTIONS = """\
MindStrat is the user's desktop trading app: market data, strategy creation and
backtests, parameter optimization with robustness tests, a strategy library, and
live trading. Its six sections, the vocabulary of objects and the shape of every
identifier are in `mindstrat://product-map` — read it first if you do not
already know the app. The app must be running for any tool to work; start with
`backend_status` when anything fails to connect, and note the user must also be
signed in, since a `401 local.no_session` means they are signed out and there is
nothing you can do about it but ask.

You are operating the user's own app, not a copy of it. These tools call the
same endpoints its screens call, in the same order, and the app owns every
result: never recompute a metric, a robustness score or a backtest from a trade
list. Win rate is on a 0-100 scale.

Three pieces of state are global to the app and shared with whatever the user
has on screen:

- The **Code Creator** session is the one they have open. `editor_load_code`
  replaces what is loaded there, including unsaved work, which is why it needs
  `confirm=true`. The loop is load -> `editor_run_backtest` ->
  `editor_set_parameters` -> run again -> `editor_save_to_library` once it
  holds up.
- **The last backtest** is a single slot. Every run overwrites it, including
  `run_backtest`, and it is what the user's own Save button reads from — so a
  run of yours can break their save. If they have unsaved work, say so first.
- **The Optimizer configuration** is one stored form. `configure_optimization`
  overwrites it wholesale rather than merging, so anything you do not set is
  inherited from whatever they left there. It saves the configuration and starts
  nothing; `start_optimization` validates it and starts the job, and neither
  needs the screen open.

Before configuring a backtest or an optimization, read `mindstrat://settings`.
The one thing to carry without looking it up: **every cost default in this app
is commission 0 and slippage 0**, loading a strategy resets it, and nothing
carries your cost configuration from one call to the next — so pass `capital_cfg`
explicitly every time, or the numbers you get are frictionless and meaningless.
Three more from that document, because each fails silently: a `method` the
engine does not know falls back to Random; a parameter range is expanded from
the TYPE of its `default`, so an integer default searches whole numbers however
fine the step, and a range reaching 0 on a stop-loss means no stop at all; and
`sharpe` is offered as an objective but does not exist in the engine, which
makes every candidate score 0 and leaves the first cycle as the permanent
"best". Use `profit` or `winrate`.

Writing a strategy is governed by the MSF format and by one rule above all
others: the same `trading_strategy()` runs in the backtest (one pass over full
history) and in live (a sliding window, re-executed per tick inside the forming
bar), so code that behaves differently across the two is a bug, not a tradeoff.
Read `mindstrat://msf/parity` before writing any. The non-negotiables:

- **Never read the current bar's `h[i]`, `l[i]` or `c[i]` for a decision, a
  level or an exit.** In backtest that is the future; in live it is the forming
  bar. Decisions read the closed bar `[i-1]`. The only safe current-bar reads
  are `o[i]` and `engine.avg_cost`. Anything of the form "price touches a level
  inside the bar" belongs to `engine.set_exit(tp/sl/trailing)`, the only channel
  with intra-bar precision.
- **Cross-bar state lives in `engine.persist`, never in a Python local** — in
  live the function is respawned every tick and locals reset. Guard each with a
  `last_t` timestamp, never an index.
- **Path-dependent indicators never receive the forming bar**: feed to
  `n_closed = n - 1`, pad the output with a trailing `None`, decide on `[i-1]`.
- **Convergent indicators go through pandas-ta** into a local numpy array;
  **path-dependent ones through talipp + `engine.persist`**. Implementing a
  path-dependent indicator with pandas-ta (`ta.supertrend`, `ta.obv`, `ta.psar`,
  `ta.vwap`) passes the backtest and silently breaks in live. Call
  `lookup_indicator` rather than deciding this from memory.
- **Never mutate `data`** (`data["col"] = ...` is rejected — the optimizer
  shares one DataFrame across trials).
- **`engine.get_trades()` is backtest-only** — in live the completed-trade list
  is emptied every tick, so a gate that counts past trades never fires. Count
  closures into `engine.persist`, or read `engine.custom["consecutive_losses"]`.
- **`warmup_spec` is live-only metadata.** The backtest ignores it and passes
  the whole dataset, so a wrong or incomplete spec is invisible until deploy.

Nothing in the app verifies any of this — the code validator checks two rules
and no more. The Live-Readiness Audit in `mindstrat://msf/parity` is the whole
safety net, so run it after every backtest and enumerate every indicator by
name rather than judging from impression.

Live trading acts as the user signed in to the app; this server holds no
credentials of its own. Deploying, stopping and resizing need
`MINDSTRAT_MCP_ALLOW_LIVE=1` and `confirm=true`, and `environment="live"`
trades real money. Stopping a live strategy tells it to stop deciding: it does
not close an open position, so never report a stop as a position closed.
"""

mcp = MCPServer(
    name="mindstrat",
    instructions=INSTRUCTIONS,
    version="0.1.0",
)

client = BackendClient()

# The manual. Read on demand rather than carried in every conversation, and
# shipped with the server so it works on a machine that has the app but not this
# repo — which is the whole point of distributing it.
_MANUAL = knowledge_tools.MANUAL_DIR
# Everything served lives in the manual now, including the tool catalogue.
_DOCS = _MANUAL


def _read_doc(path: Path) -> str:
    """Read a reference document, failing loudly when it has moved.

    A resource that quietly returns nothing is worse than one that errors: the
    model would carry on writing strategies without the rules it was supposed to
    have read.
    """
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Reference document missing: {path}") from exc


@mcp.resource(
    "mindstrat://product-map",
    name="The MindStrat product map",
    description=(
        "What the app is and what each of its six sections does — Market "
        "Assets, Strategy Creator, Optimizer, Strategy Manager, Portfolios, "
        "Live Trading — plus the vocabulary of objects and the exact shape of "
        "each identifier (a snapshot id is not a strategy id), which state you "
        "share with the user at the screen, which resources there is exactly "
        "one of, and what is lost when the app restarts. Read this first when "
        "you do not already know the app."
    ),
    mime_type="text/markdown",
)
def product_map() -> str:
    return _read_doc(_MANUAL / "product_map.md")


@mcp.resource(
    "mindstrat://settings",
    name="Settings — units, defaults, and the ones that lie",
    description=(
        "Every control that changes a result: the cost model and why every "
        "default in the app is commission 0 and slippage 0, the units that "
        "differ by 100x between adjacent fields, the optimizer's search "
        "methods and its two objective metrics that actually work, how a "
        "parameter range is expanded from the TYPE of its default, what each "
        "robustness test configures, where 0 means 'off' rather than zero, and "
        "which invalid values are silently replaced instead of refused. Read "
        "before configuring a backtest or an optimization."
    ),
    mime_type="text/markdown",
)
def settings_guide() -> str:
    return _read_doc(_MANUAL / "settings.md")


@mcp.resource(
    "mindstrat://msf/parity",
    name="Writing a strategy that behaves the same live as in the backtest",
    description=(
        "The rule the MSF format exists to protect: the same function runs "
        "once over full history in the backtest and per tick over a sliding "
        "window in live. Covers the two execution channels, the ban on reading "
        "the current bar, cross-bar state in engine.persist, the forming-bar "
        "quarantine, the pandas-ta versus talipp decision, the hard "
        "constraints, and the eight-dimension Live-Readiness Audit. Read "
        "before writing any strategy code."
    ),
    mime_type="text/markdown",
)
def parity_guide() -> str:
    return _read_doc(_MANUAL / "parity.md")


@mcp.resource(
    "mindstrat://msf/canon",
    name="MSF strategy canon",
    description=(
        "The binding structure of an MSF strategy: module-level sections, the "
        "warmup spec, the function signature, the full engine API surface, and "
        "the two-engine indicator system (pandas-ta versus talipp + persist)."
    ),
    mime_type="text/markdown",
)
def msf_canon() -> str:
    return _read_doc(_MANUAL / "msf_canon.md")


@mcp.resource(
    "mindstrat://msf/runtime-constraints",
    name="MSF runtime constraints",
    description=(
        "What the runtime rejects and why: prohibited patterns, structural "
        "limits, engine and talipp constraints, optimizer-safe code, auxiliary "
        "datasets, the library decision rule, the commission model, and the "
        "forming-bar quarantine."
    ),
    mime_type="text/markdown",
)
def msf_runtime_constraints() -> str:
    return _read_doc(_MANUAL / "runtime_constraints.md")


@mcp.resource(
    "mindstrat://msf/template",
    name="MSF canonical template",
    description=(
        "The skeleton every strategy follows, annotated section by section. "
        "Start here when writing code."
    ),
    mime_type="text/markdown",
)
def msf_template() -> str:
    return _read_doc(_MANUAL / "Code_Template.md")


@mcp.resource(
    "mindstrat://msf/examples",
    name="MSF gold-standard examples",
    description=(
        "Complete worked strategies: pandas-ta only, talipp with engine.persist "
        "and a macro filter, pyramiding with partial closes, and the DIY persist "
        "recipe for path-dependent indicators talipp does not implement."
    ),
    mime_type="text/markdown",
)
def msf_examples() -> str:
    return _read_doc(_MANUAL / "strategy_library.md")


@mcp.resource(
    "mindstrat://msf/visualization",
    name="MSF chart series format",
    description=(
        "The schema of the visualization_data return: series objects, the pane "
        "system, reference levels, array length rules (NaN becomes a gap — never "
        "fillna) and the anti-patterns that misalign a series from the candles."
    ),
    mime_type="text/markdown",
)
def msf_visualization() -> str:
    return _read_doc(_MANUAL / "visualization_format.md")


@mcp.resource(
    "mindstrat://tools",
    name="Tool catalogue",
    description=(
        "Every tool grouped by the app screen it drives, which backend endpoint "
        "each one calls, and what is deliberately not exposed."
    ),
    mime_type="text/markdown",
)
def tool_catalogue() -> str:
    return _read_doc(_DOCS / "TOOLS.md")


@mcp.tool(
    name="backend_status",
    description=(
        "Check that the MindStrat backend is reachable and report the port it "
        "was found on. Call this first when other tools fail to connect."
    ),
    annotations=READ_ONLY,
)
async def backend_status() -> dict:
    return await system_tools.backend_status(client)


# --------------------------------------------------------------------------
# Market Assets
# --------------------------------------------------------------------------


@mcp.tool(
    name="list_datasets",
    description=(
        "List OHLCV datasets already downloaded in Market Assets, with row "
        "counts, date coverage and size. Filter by symbol and/or timeframe."
    ),
    annotations=READ_ONLY,
)
async def list_datasets(
    symbol: str | None = None,
    timeframe: str | None = None,
    limit: int | None = None,
) -> dict:
    return await assets_tools.list_datasets(client, symbol, timeframe, limit)


@mcp.tool(
    name="assets_overview",
    description=(
        "Overview of the Market Assets section: available environments for an "
        "exchange, tradable symbols (optionally filtered), and total storage "
        "used by downloaded datasets."
    ),
    annotations=READ_ONLY,
)
async def assets_overview(
    exchange: str = assets_tools.DEFAULT_EXCHANGE,
    environment: str = assets_tools.DEFAULT_ENVIRONMENT,
    symbol_filter: str | None = None,
    symbol_limit: int | None = None,
) -> dict:
    return await assets_tools.assets_overview(
        client, exchange, environment, symbol_filter, symbol_limit
    )


@mcp.tool(
    name="start_download",
    description=(
        "Queue a candle download into Market Assets and return the job. "
        "start/end are UNIX timestamps in MILLISECONDS; omit them to download "
        "the full available history. Poll progress with get_download_jobs."
    ),
)
async def start_download(
    symbol: str,
    timeframe: str,
    start: int | None = None,
    end: int | None = None,
    exchange: str = assets_tools.DEFAULT_EXCHANGE,
    environment: str = assets_tools.DEFAULT_ENVIRONMENT,
    label: str | None = None,
    max_retries: int = 2,
) -> dict:
    return await assets_tools.start_download(
        client, symbol, timeframe, start, end, exchange, environment, label, max_retries
    )


@mcp.tool(
    name="get_download_jobs",
    description=(
        "Poll a download job by id, or list recent jobs. Status is one of "
        "queued, running, completed, failed, cancelled; progress is a percent "
        "(0-100). The queue lives in backend memory and is cleared if the app "
        "restarts."
    ),
    annotations=READ_ONLY,
)
async def get_download_jobs(
    job_id: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> dict:
    return await assets_tools.get_download_jobs(client, job_id, status, limit)


@mcp.tool(
    name="cancel_download",
    description=(
        "Cancel a queued or running Market Assets download job. Cancellation "
        "is not instant — the job winds down and reports status 'cancelled' "
        "when it has; confirm with get_download_jobs. Job state lives in "
        "backend memory, so a job that vanishes after an app restart was "
        "dropped, not completed."
    ),
)
async def cancel_download(job_id: str) -> dict:
    return await assets_tools.cancel_download(client, job_id)


@mcp.tool(
    name="maintain_dataset",
    description=(
        "Maintain an existing dataset: action='refresh' extends it to the "
        "latest candles, action='repair_gaps' refills missing bars. Both queue "
        "a job to poll with get_download_jobs."
    ),
)
async def maintain_dataset(snapshot_id: str, action: str) -> dict:
    return await assets_tools.maintain_dataset(client, snapshot_id, action)


@mcp.tool(
    name="delete_dataset",
    description=(
        "Permanently delete a downloaded dataset snapshot. Requires "
        "confirm=true; strategies referencing the dataset will lose their data."
    ),
    annotations=DESTRUCTIVE,
)
async def delete_dataset(snapshot_id: str, confirm: bool = False) -> dict:
    return await assets_tools.delete_dataset(client, snapshot_id, confirm)


# --------------------------------------------------------------------------
# Code Creator: strategies, datasets, backtests, Python kernel
# --------------------------------------------------------------------------


@mcp.tool(
    name="lookup_indicator",
    description=(
        "Look one indicator up in the MSF reference catalogues and get its "
        "documented signature plus WHICH LIBRARY MUST IMPLEMENT IT — the "
        "mechanical decision that determines whether the strategy behaves in "
        "live the way it did in the backtest.\n"
        "Convergent indicators go through pandas-ta, vectorized into a local "
        "numpy array. Path-dependent ones (SuperTrend, ParabolicSAR, OBV, "
        "AccuDist, session VWAP, ZigZag, Ichimoku...) go through talipp + "
        "engine.persist, because their value depends on the whole history since "
        "the series started and a sliding window corrupts it. Implementing one "
        "of those with pandas-ta passes the backtest and silently breaks in "
        "live; when both libraries expose the same name this tool says so and "
        "which assignment is binding.\n"
        "Call it once per indicator before writing the constructor — never "
        "write a signature or decide a library from memory. Accepts either "
        "catalogue's spelling ('psar' or 'ParabolicSAR'). Optionally pass "
        "library='pandas_ta' or 'talipp' to force which reference comes back."
    ),
    annotations=READ_ONLY,
)
async def lookup_indicator(name: str, library: str | None = None) -> dict:
    return knowledge_tools.lookup_indicator(name, library)


@mcp.tool(
    name="editor_load_code",
    description=(
        "Load strategy code into the Code Creator screen, as pasting it there "
        "would. Returns the parameters, capital settings and auxiliary dataset "
        "slots the code declares. Step one of building a strategy: then run it "
        "with editor_run_backtest, adjust with editor_set_parameters, and save "
        "with editor_save_to_library once it holds up.\n"
        "The code must be valid MSF: the module-level sections, the five-parameter "
        "trading_strategy signature with engine fifth, decisions on the closed "
        "bar [i-1], cross-bar state in engine.persist, and path-dependent "
        "indicators fed only closed bars. Read mindstrat://msf/parity "
        "before writing any, and mindstrat://msf/template for the skeleton — "
        "code that ignores these passes the backtest and diverges in live.\n"
        "WARNING: replaces whatever that screen currently holds, including "
        "unsaved work, so it requires confirm=true."
    ),
    annotations=DESTRUCTIVE,
)
async def editor_load_code(code: str, confirm: bool = False) -> dict:
    return await creator_tools.editor_load_code(client, code, confirm)


@mcp.tool(
    name="editor_set_parameters",
    description=(
        "Change parameter values on the strategy loaded in the Code Creator, "
        "passing a dict of {parameter: value}. The in-memory source itself is "
        "rewritten with the new values — which is why editor_run_backtest "
        "sends no code — so the next run uses them. Values keep their "
        "declared type. This is for logic tuning, a handful of deliberate "
        "changes between runs; sweeping a range of values is the Optimizer's "
        "job (prepare_optimization)."
    ),
)
async def editor_set_parameters(updates: dict) -> dict:
    return await creator_tools.editor_set_parameters(client, updates)


@mcp.tool(
    name="editor_run_backtest",
    description=(
        "Backtest the strategy currently loaded in the Code Creator against a "
        "dataset, including any parameter edits. Returns metrics and execution "
        "errors; trade lists and chart series are omitted, page them with "
        "get_backtest_trades(backtest_id='latest'). Set intrabar_simulation=true "
        "to replay each bar at a finer timeframe and resolve whether the "
        "take-profit or the stop-loss was hit first — without it the engine "
        "assumes, and any TP/SL strategy reads optimistic. Use run_backtest "
        "instead to test a saved strategy or arbitrary code without touching "
        "the editor."
    ),
)
async def editor_run_backtest(
    dataset_id: str,
    start_time: int | None = None,
    end_time: int | None = None,
    capital_cfg: dict | None = None,
    auxiliary_snapshot_ids: dict | None = None,
    intrabar_simulation: bool = False,
    intrabar_timeframe: str | None = None,
) -> dict:
    return await creator_tools.editor_run_backtest(
        client, dataset_id, start_time, end_time, capital_cfg,
        auxiliary_snapshot_ids, intrabar_simulation, intrabar_timeframe,
    )


@mcp.tool(
    name="editor_save_to_library",
    description=(
        "Save the strategy loaded in the Code Creator as a saved strategy, "
        "keeping the trades and metrics of the last editor_run_backtest (run it "
        "first). symbol and timeframe default to the dataset's. Returns the new "
        "strategy id, ready for prepare_optimization."
    ),
)
async def editor_save_to_library(
    name: str,
    dataset_id: str,
    symbol: str | None = None,
    timeframe: str | None = None,
    capital_cfg: dict | None = None,
    auxiliary_snapshot_ids: dict | None = None,
    favorite: bool = False,
) -> dict:
    return await creator_tools.editor_save_to_library(
        client, name, dataset_id, symbol, timeframe, capital_cfg,
        auxiliary_snapshot_ids, favorite,
    )


@mcp.tool(
    name="list_saved_strategies",
    description=(
        "List strategies saved in the Code Creator library, with symbol, "
        "timeframe and headline metrics. Metadata only — no source code."
    ),
    annotations=READ_ONLY,
)
async def list_saved_strategies(
    symbol: str | None = None,
    timeframe: str | None = None,
    favorite_only: bool = False,
    name_contains: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict:
    return await creator_tools.list_saved_strategies(
        client, symbol, timeframe, favorite_only, name_contains, limit, offset
    )


@mcp.tool(
    name="get_saved_strategy",
    description=(
        "Fetch one saved strategy: parameters, dataset, capital config and "
        "metadata. Pass include_code=true to also get the Python source (can "
        "be long)."
    ),
    annotations=READ_ONLY,
)
async def get_saved_strategy(strategy_id: str, include_code: bool = False) -> dict:
    return await creator_tools.get_saved_strategy(client, strategy_id, include_code)


@mcp.tool(
    name="list_backtest_datasets",
    description=(
        "List datasets usable as backtest inputs, with their dataset_id and "
        "date coverage. Same store as list_datasets, shaped for choosing a "
        "backtest input: the dataset_id here is what editor_run_backtest, "
        "run_backtest and configure_optimization take. For one dataset's "
        "quality record (gaps, duplicates, size), use get_dataset_summary."
    ),
    annotations=READ_ONLY,
)
async def list_backtest_datasets(
    symbol: str | None = None, timeframe: str | None = None
) -> dict:
    return await creator_tools.list_datasets_for_backtests(client, symbol, timeframe)


@mcp.tool(
    name="get_dataset_summary",
    description=(
        "One dataset's coverage and quality record, as Market Assets keeps "
        "it: row count, date range, missing and duplicate bar counts, and "
        "size. The gate between having data and using it: check the range "
        "covers the intended window and `missing` is 0 (repair gaps with "
        "maintain_dataset) before characterizing the dataset with run_python "
        "or backtesting on it."
    ),
    annotations=READ_ONLY,
)
async def get_dataset_summary(dataset_id: str) -> dict:
    return await creator_tools.get_dataset_summary(client, dataset_id)


@mcp.tool(
    name="get_intrabar_timeframes",
    description=(
        "The intrabar timeframes the app offers for a chart timeframe, and "
        "the default it picks when intrabar_timeframe is left unset. Call "
        "before enabling intrabar in editor_run_backtest or "
        "configure_optimization instead of guessing: only these values run."
    ),
    annotations=READ_ONLY,
)
async def get_intrabar_timeframes(chart_timeframe: str) -> dict:
    return await creator_tools.get_intrabar_timeframes(client, chart_timeframe)


@mcp.tool(
    name="get_price_window",
    description=(
        "Read a bounded OHLCV window from a dataset (max 500 rows). "
        "start_time and end_time accept ISO-8601 timestamps or epoch seconds; "
        "omit them to get the most recent bars. Use this to inspect price "
        "action — never try to load a whole dataset."
    ),
    annotations=READ_ONLY,
)
async def get_price_window(
    dataset_id: str,
    start_time: str | None = None,
    end_time: str | None = None,
    max_rows: int = 200,
) -> dict:
    return await creator_tools.get_price_window(
        client, dataset_id, start_time, end_time, max_rows
    )


@mcp.tool(
    name="list_backtests",
    description=(
        "List stored backtests with summary metrics. sort_by accepts recent, "
        "sharpe_desc, return_desc or drawdown_asc."
    ),
    annotations=READ_ONLY,
)
async def list_backtests(
    strategy_id: str | None = None,
    dataset_id: str | None = None,
    min_sharpe: float | None = None,
    sort_by: str = "recent",
    limit: int | None = None,
    offset: int = 0,
) -> dict:
    return await creator_tools.list_backtests(
        client, strategy_id, dataset_id, min_sharpe, sort_by, limit, offset
    )


@mcp.tool(
    name="get_backtest",
    description=(
        "Metrics and configuration of one backtest. backtest_id='latest' "
        "returns the most recent run of the current session. Trade lists and "
        "chart series are omitted; use get_backtest_trades for trades."
    ),
    annotations=READ_ONLY,
)
async def get_backtest(backtest_id: str = "latest") -> dict:
    return await creator_tools.get_backtest(client, backtest_id)


@mcp.tool(
    name="get_backtest_trades",
    description=(
        "Page through the trades of a backtest (max 30 per call) with filters "
        "for side, outcome, PnL range and entry/exit signal text. The response "
        "also carries a summary computed over ALL matching trades, not just "
        "the returned page."
    ),
    annotations=READ_ONLY,
)
async def get_backtest_trades(
    backtest_id: str = "latest",
    side: str | None = None,
    outcome: str | None = None,
    min_pnl_pct: float | None = None,
    max_pnl_pct: float | None = None,
    entry_signal_contains: str | None = None,
    exit_signal_contains: str | None = None,
    sort_by: str = "chronological",
    limit: int = 30,
    offset: int = 0,
) -> dict:
    return await creator_tools.get_backtest_trades(
        client,
        backtest_id,
        side,
        outcome,
        min_pnl_pct,
        max_pnl_pct,
        entry_signal_contains,
        exit_signal_contains,
        sort_by,
        limit,
        offset,
    )


@mcp.tool(
    name="run_backtest",
    description=(
        "Run a headless backtest and return its metrics, leaving the Code "
        "Creator session untouched — use this to test a saved strategy or "
        "arbitrary code without disturbing what the user has open. Provide "
        "exactly one of strategy_id (a saved strategy) or code (raw MSF "
        "source, same rules as editor_load_code — see "
        "mindstrat://msf/parity), plus the dataset_id to run on. "
        "parameters overrides strategy params by name; auxiliary_dataset_ids "
        "maps aux slots (e.g. 'dataset_2') to dataset ids. Takes up to ~90 s."
    ),
)
async def run_backtest(
    dataset_id: str,
    strategy_id: str | None = None,
    code: str | None = None,
    parameters: dict | None = None,
    auxiliary_dataset_ids: dict | None = None,
    strategy_name: str | None = None,
) -> dict:
    return await creator_tools.run_backtest(
        client, dataset_id, strategy_id, code, parameters, auxiliary_dataset_ids, strategy_name
    )


@mcp.tool(
    name="run_python",
    description=(
        "Execute Python in a persistent analysis kernel that has pandas, numpy "
        "and pandas_ta preloaded, plus the `ms` SDK (ms.datasets.list(), "
        "ms.datasets.load(dataset_id)) to load MindStrat market data. State "
        "persists between calls. No network and no disk writes; 120 s limit. "
        "Use reset_kernel=true for a clean namespace, or action='kill' to drop "
        "the kernel.\n"
        "This is the research surface: characterize a dataset HERE before "
        "designing a strategy — date range, realized volatility, share of time "
        "trending versus ranging, and the median bar range in %, which is the "
        "noise term a take-profit has to clear. Choosing an indicator family or "
        "a TP/SL without it is guessing.\n"
        "Vectorized numpy/pandas only: .apply(), .iterrows() and "
        "rolling(...).apply() blow the 120 s wall on minute data. A timeout "
        "means the next attempt must be structurally lighter, never a retry."
    ),
)
async def run_python(code: str = "", reset_kernel: bool = False, action: str = "run") -> dict:
    return await creator_tools.run_python(client, code, reset_kernel, action)


# --------------------------------------------------------------------------
# Strategy Manager
# --------------------------------------------------------------------------


@mcp.tool(
    name="list_manager_strategies",
    description=(
        "List saved strategies in the Strategy Manager. Filter by text search, "
        "symbol, timeframe, favorite, active robustness methods (robust, e.g. "
        "['HoldOut','WalkForwardRolling']) or a metrics_filter like "
        '{\"strategy\": {\"profit\": {\"op\": \">=\", \"val\": 10}}} — passed '
        "as a JSON object or its string form, whichever the client sends. "
        "list_metric_filters gives the valid keys and operators. "
        "sort accepts values such as -created, strategy_name or -started."
    ),
    annotations=READ_ONLY,
)
async def list_manager_strategies(
    search: str | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
    robust: list[str] | None = None,
    favorite: bool = False,
    metrics_filter: str | dict | None = None,
    sort: str | None = None,
    page: int = 1,
    limit: int | None = None,
) -> dict:
    return await manager_tools.list_manager_strategies(
        client, search, symbol, timeframe, robust, favorite, metrics_filter, sort, page, limit
    )


@mcp.tool(
    name="get_strategy_detail",
    description=(
        "Full analysis of a saved strategy: metrics, extended metrics, capital "
        "config and robustness results (HoldOut train/val/full metrics, "
        "WalkForwardRolling per-fold is_*/val_* values, Monte Carlo scores and "
        "tiers). Trade lists and chart series are omitted — use "
        "get_strategy_trades for trades. Robustness numbers come from the "
        "backend and must not be recomputed from trades."
    ),
    annotations=READ_ONLY,
)
async def get_strategy_detail(strategy_id: int, include_code: bool = False) -> dict:
    return await manager_tools.get_strategy_detail(client, strategy_id, include_code)


@mcp.tool(
    name="get_strategy_trades",
    description=(
        "Page through a saved strategy's trade events with filters and a "
        "summary over everything that matched, not just the returned page. "
        "The rows are the engine's raw event log — open and close rows, not "
        "paired positions — so profit lives on the close rows, and the "
        "outcome and profit filters narrow to final closes (partial closes "
        "excluded, as the app's own metrics count them). Filter by "
        "event_type ('open'/'close'), outcome ('winners'/'losers'/"
        "'breakeven'), min_profit/max_profit, or signal_contains; sort with "
        "'chronological', 'profit_desc' or 'profit_asc'. The strategy's "
        "headline metrics come from get_strategy_detail — never recompute "
        "them from this list."
    ),
    annotations=READ_ONLY,
)
async def get_strategy_trades(
    strategy_id: int,
    event_type: str | None = None,
    outcome: str | None = None,
    min_profit: float | None = None,
    max_profit: float | None = None,
    signal_contains: str | None = None,
    sort_by: str = "chronological",
    limit: int | None = None,
    offset: int = 0,
) -> dict:
    return await manager_tools.get_strategy_trades(
        client, strategy_id, event_type, outcome, min_profit, max_profit,
        signal_contains, sort_by, limit, offset,
    )


@mcp.tool(
    name="list_optimizations",
    description=(
        "List optimization runs with their method, status, cycle count, best "
        "profit and active robustness tests. Filter by search text, symbol, "
        "timeframe, status, method or robust methods; sort with e.g. -started, "
        "best_profit, cycles."
    ),
    annotations=READ_ONLY,
)
async def list_optimizations(
    search: str | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
    status: str | None = None,
    method: str | None = None,
    robust: list[str] | None = None,
    sort: str | None = None,
    page: int = 1,
    limit: int | None = None,
) -> dict:
    return await manager_tools.list_optimizations(
        client, search, symbol, timeframe, status, method, robust, sort, page, limit
    )


@mcp.tool(
    name="get_optimization_summary",
    description=(
        "Status and headline numbers of an optimization run (method, status, "
        "cycles completed, best profit, active robustness tests). Safe to call "
        "on huge runs: it never returns cycle rows. Use "
        "list_optimization_cycles to inspect cycles. Robustness results are "
        "not all here: each test reports where its own results live, because "
        "Hold-Out is stored per candidate and Monte Carlo per cycle."
    ),
    annotations=READ_ONLY,
)
async def get_optimization_summary(opt_id: int) -> dict:
    return await manager_tools.get_optimization_summary(client, opt_id)


@mcp.tool(
    name="list_optimization_cycles",
    description=(
        "Page through the cycles of an optimization run. Sort with sort_by "
        "(cycle, profit, or metrics.X) and sort_order, and filter by "
        "min_profit, max_profit, min_trades, max_drawdown or min_winrate "
        "(win rate is on a 0-100 scale). Each cycle carries its parameters, "
        "its metrics, its HoldOut block (is_*/val_*) and its Monte Carlo "
        "mc_score/mc_tier — the three families the Strategy Manager table "
        "shows, which is what candidates are picked with. Sorting and "
        "filtering run in the backend over the cycle's own metrics only, so "
        "on a large run narrow by those first, then compare the survivors by "
        "val_* and mc_score. Use get_cycle_robustness on the shortlist."
    ),
    annotations=READ_ONLY,
)
async def list_optimization_cycles(
    opt_id: int,
    page: int = 1,
    page_size: int | None = None,
    sort_by: str = "cycle",
    sort_order: str = "asc",
    min_profit: float | None = None,
    max_profit: float | None = None,
    min_trades: int | None = None,
    max_drawdown: float | None = None,
    min_winrate: float | None = None,
) -> dict:
    return await manager_tools.list_optimization_cycles(
        client,
        opt_id,
        page,
        page_size,
        sort_by,
        sort_order,
        min_profit,
        max_profit,
        min_trades,
        max_drawdown,
        min_winrate,
    )


@mcp.tool(
    name="get_cycle_detail",
    description=(
        "Detailed result of a single optimization cycle: parameters, metrics "
        "and its robustness results. Trade lists, chart series and simulated "
        "curves are omitted. For robustness alone, get_cycle_robustness reads "
        "better and costs less."
    ),
    annotations=READ_ONLY,
)
async def get_cycle_detail(opt_id: int, cycle: int, include_code: bool = False) -> dict:
    return await manager_tools.get_cycle_detail(client, opt_id, cycle, include_code)


@mcp.tool(
    name="get_cycle_robustness",
    description=(
        "The robustness evidence for one cycle, as the detail view shows it — "
        "what to read before deploying a candidate. HoldOut comes back as the "
        "train / validation / full-period comparison of every metric. "
        "MonteCarloTrades comes back as its stability score and tier, the "
        "outcome distribution, the probability of loss or drawdown breach, and "
        "a per-mode breakdown of every perturbation (drop_best_trades, "
        "bootstrap, cost_degradation, ...) with the score each one earned. "
        "Narrow with test ('HoldOut' or 'MonteCarloTrades') and, for Monte "
        "Carlo, mode. The simulated equity curves are deliberately not "
        "returned: a single run is thousands of points, and equity_shape "
        "already answers what the picture answers — whether the profit is one "
        "jump or many, and how long the strategy sits below its high. To "
        "compute on the curves themselves, use run_python with "
        "ms.manager.monte_carlo(opt_id, cycle)."
    ),
    annotations=READ_ONLY,
)
async def get_cycle_robustness(
    opt_id: int, cycle: int, test: str | None = None, mode: str | None = None
) -> dict:
    return await manager_tools.get_cycle_robustness(client, opt_id, cycle, test, mode)


@mcp.tool(
    name="list_metric_filters",
    description=(
        "The vocabulary for building a metrics_filter: every filterable "
        "metric key with its type and bounds, the accepted operators, and a "
        "worked example of the JSON string list_manager_strategies takes. "
        "Read this rather than inventing keys — an unknown key silently "
        "matches nothing."
    ),
    annotations=READ_ONLY,
)
async def list_metric_filters() -> dict:
    return await manager_tools.list_metric_filters(client)


@mcp.tool(
    name="list_portfolios",
    description=(
        "List the user's portfolios: name, description, strategy count and "
        "aggregate metric summaries. A portfolio is where validated "
        "strategies are combined and read as one book; open one with "
        "get_portfolio."
    ),
    annotations=READ_ONLY,
)
async def list_portfolios(name: str | None = None, limit: int | None = None) -> dict:
    return await manager_tools.list_portfolios(client, name, limit)


@mcp.tool(
    name="get_portfolio",
    description=(
        "One portfolio's analysis as the app computes it: summary, combined "
        "totals and metrics, and each member strategy's contribution. The "
        "combined trade list and profit curve are omitted as bulk; the "
        "aggregates pass through as the backend computed them."
    ),
    annotations=READ_ONLY,
)
async def get_portfolio(portfolio_id: int) -> dict:
    return await manager_tools.get_portfolio(client, portfolio_id)


@mcp.tool(
    name="update_strategy_meta",
    description=(
        "Update a saved strategy's metadata: toggle favorite, rename it, or set "
        "its description. Pass only the fields you want to change. The "
        "description is the research log the user sees on the strategy's card "
        "— record the edge verdict, why this candidate was selected over its "
        "run's alternatives, and its validation status there."
    ),
)
async def update_strategy_meta(
    strategy_id: int,
    favorite: bool | None = None,
    name: str | None = None,
    description: str | None = None,
) -> dict:
    return await manager_tools.update_strategy_meta(
        client, strategy_id, favorite, name, description
    )


@mcp.tool(
    name="save_cycle_as_strategy",
    description=(
        "Save an optimization cycle as a new strategy in the manager. Queues a "
        "background job and waits briefly for it; if it is still running, poll "
        "get_manager_job_status with kind='snapshot'."
    ),
)
async def save_cycle_as_strategy(
    opt_id: int, cycle: int, favorite: bool = False, wait_seconds: int = 20
) -> dict:
    return await manager_tools.save_cycle_as_strategy(
        client, opt_id, cycle, favorite, wait_seconds
    )


@mcp.tool(
    name="create_strategy_from_rolling",
    description=(
        "Graduate a TEMPLATE-origin Walk-Forward Rolling run into a new saved "
        "strategy: the backend backtests the default parameters for the "
        "overview and carries the run's whole WalkForwardRolling bucket into "
        "the snapshot. Only for runs whose base was a template — a rolling "
        "run against an already-saved strategy merges into that snapshot with "
        "attach_rolling_to_strategy instead. Takes a while: it re-runs a full "
        "backtest."
    ),
)
async def create_strategy_from_rolling(
    opt_id: int, base_params: dict | None = None, favorite: bool = False
) -> dict:
    return await manager_tools.create_strategy_from_rolling(
        client, opt_id, base_params, favorite
    )


@mcp.tool(
    name="manage_portfolio",
    description=(
        "Create, update or delete a portfolio, or add a saved strategy to "
        "one: action='create' (name, optional description), 'update' "
        "(portfolio_id + name — the backend replaces both fields, so pass the "
        "name even when only changing the description), 'add_strategy' "
        "(portfolio_id + strategy_id), 'delete' (portfolio_id + confirm=true; "
        "member strategies survive, the grouping does not). Portfolios are "
        "the shelf validated finalists graduate onto — read the combined book "
        "with get_portfolio."
    ),
    annotations=DESTRUCTIVE,
)
async def manage_portfolio(
    action: str,
    portfolio_id: int | None = None,
    name: str | None = None,
    description: str | None = None,
    strategy_id: int | None = None,
    confirm: bool = False,
) -> dict:
    return await manager_tools.manage_portfolio(
        client, action, portfolio_id, name, description, strategy_id, confirm
    )


@mcp.tool(
    name="delete_manager_items",
    description=(
        "Permanently delete a saved strategy or an entire optimization run "
        "(with all its cycles). Requires confirm=true. Runs as a background "
        "job; poll get_manager_job_status with kind='deletion'."
    ),
    annotations=DESTRUCTIVE,
)
async def delete_manager_items(
    target_type: str, target_id: int, confirm: bool = False
) -> dict:
    return await manager_tools.delete_manager_items(client, target_type, target_id, confirm)


@mcp.tool(
    name="get_manager_job_status",
    description=(
        "Poll manager background jobs. kind='snapshot' for save-cycle jobs "
        "(carries saved_strategy_id when done), kind='deletion' for deletions "
        "(carries progress counters). Omit job_id to list all known jobs. "
        "Job state lives in backend memory and is lost if the app restarts."
    ),
    annotations=READ_ONLY,
)
async def get_manager_job_status(kind: str, job_id: str | None = None) -> dict:
    return await manager_tools.get_manager_job_status(client, kind, job_id)


# --------------------------------------------------------------------------
# Optimizer
# --------------------------------------------------------------------------


@mcp.tool(
    name="get_optimizer_capacity",
    description=(
        "What the machine can sustain for an optimization run: total and "
        "available RAM, next to the workers and max_ram_pct the user has "
        "configured on the Optimizer screen. Memory pressure comes from "
        "workers x dataset size — robustness tests cost wall-clock, not RAM — "
        "so size a run against this before overriding workers in "
        "configure_optimization, and respect the user's own settings unless "
        "there is a stated reason not to."
    ),
    annotations=READ_ONLY,
)
async def get_optimizer_capacity() -> dict:
    return await optimizer_tools.get_optimizer_capacity(client)


@mcp.tool(
    name="prepare_optimization",
    description=(
        "Build a ready-to-run optimizer configuration from a saved strategy: "
        "base parameters, parameter ranges (from/to/step), capital config "
        "(capital, commission, slippage), robustness config and auxiliary "
        "datasets, plus the total number of parameter combinations. If the "
        "strategy has no saved ranges, they are proposed from its base "
        "parameters the way the Optimizer screen does (+/-20% in five steps); "
        "parameter_ranges_source says which case applies. Call this before "
        "start_optimization to review or adjust the search space."
    ),
    annotations=READ_ONLY,
)
async def prepare_optimization(strategy_id: int, dataset_id: str | None = None) -> dict:
    return await optimizer_tools.prepare_optimization(client, strategy_id, dataset_id)


@mcp.tool(
    name="configure_optimization",
    description=(
        "Save the run's configuration — strategy, dataset, search space, "
        "method, metric, cycles and robustness — WITHOUT starting anything, so "
        "the user can review it before it launches. The Optimizer screen shows "
        "it when open, and does not have to be. Call prepare_optimization "
        "first: it returns the catalogue of methods, robustness tests and "
        "their parameters. Then call start_optimization.\n"
        "method: the app runs Random, Brute Force, Sequential MC, Sequential "
        "Jump and Annealing Thermal. Two older names are folded onto those "
        "without warning — 'Random Improvements' runs as Random and "
        "'Sequential Improvement' runs as Sequential MC — so name what you "
        "actually want. ANY OTHER VALUE SILENTLY FALLS BACK TO Random.\n"
        "cycles is the run's budget and belongs here, with the rest of the "
        "configuration: the run stops itself when it reaches it.\n"
        "Parameter ranges are {from,to,step,default,...}; the optimizer decides "
        "how to expand each range from the TYPE of its default, so an integer "
        "default searches whole numbers only however fine the step is.\n"
        "robustness accepts {walk_forward:{mode:'holdout'|'rolling',split_pct,"
        "folds,train_pct,val_pct,metric,trigger_mode,trigger}, monte_carlo:"
        "{curves,modes:[...],mode_params:{mode:{param:value}},trigger_mode,"
        "trigger}, intrabar:{enabled,intrabar_timeframe}}.\n"
        "monte_carlo.mode_params tunes each perturbation, in the engine's own "
        "units (fractions, not percentages): bootstrap{block_size}, "
        "drop_pct{pct_min,pct_max}, drop_best_trades{pct,jitter}, "
        "drop_cluster{cluster_pct_min,cluster_pct_max}, "
        "noise_injection{noise_pct}, cost_degradation{max_cost_pct}, "
        "time_slice{window_pct}. A mode you name but leave unparameterised "
        "keeps the user's own setting; the response echoes what each will "
        "actually run with.\n"
        "trigger_mode decides how much of the run you can rank. 'every_pass' "
        "measures every candidate and is the only mode under which the whole "
        "run is comparable; 'new_best' measures exactly the in-sample winners, "
        "which is a biased sample; 'cycles' measures an arbitrary few. This "
        "costs TIME, not memory — memory is flat across a run — so buy it by "
        "lowering cycles or curves rather than by skipping validation.\n"
        "Enable intrabar for any strategy that exits on "
        "take-profit or stop-loss: without it the engine guesses which level a "
        "candle touched first and the results read optimistic. Choose the "
        "robustness setup deliberately every "
        "time — which tests to enable, how to configure them and what you mean "
        "to validate. It is never inherited: anything you leave out is turned "
        "off, not carried over.\n"
        "sequential carries the budget of the two sequential methods, which do "
        "not use cycles: Sequential MC takes {seq_mode:'1 vuelta'|'N vueltas'|"
        "'Hasta sin mejora', seq_loops}, and Sequential Jump takes {jump_size, "
        "jump_termination:'never'|'cycles'|'minutes', jump_cycles, "
        "jump_minutes}.\n"
        "auxiliary_snapshot_ids maps auxiliary slots to dataset ids for "
        "multi-dataset strategies, and defaults to what the strategy has saved. "
        "THE SLOT NAMES COME FROM THE STRATEGY'S OWN CODE — 'dataset_2', "
        "'macro_btc', whatever it declares — and are not interchangeable. Any "
        "number of slots is supported. This call refuses when a declared slot "
        "has no dataset, because the strategy raises on its first bar without "
        "it and every cycle of the run would fail identically; "
        "prepare_optimization lists the slots and which are already covered.\n"
        "workers and max_ram_pct default to whatever the user has configured in "
        "the Optimizer screen; pass them only to override that on purpose, and "
        "say why.\n"
        "Works whether or not the screen is open; screen_updated in the "
        "response says whether the screen is showing it yet."
    ),
)
async def configure_optimization(
    strategy_id: int,
    dataset_id: str,
    method: str = "Random",
    cycles: int | None = None,
    workers: int | None = None,
    metric: str = "profit",
    parameter_ranges: dict | None = None,
    base_parameters: dict | None = None,
    capital_cfg: dict | None = None,
    robustness: dict | None = None,
    start_time: int | None = None,
    end_time: int | None = None,
    max_ram_pct: int | None = None,
    sequential: dict | None = None,
    auxiliary_snapshot_ids: dict | None = None,
) -> dict:
    return await optimizer_tools.configure_optimization(
        client,
        strategy_id,
        dataset_id,
        method,
        cycles,
        workers,
        metric,
        parameter_ranges,
        base_parameters,
        capital_cfg,
        robustness,
        start_time,
        end_time,
        max_ram_pct,
        sequential,
        auxiliary_snapshot_ids,
    )


@mcp.tool(
    name="start_optimization",
    description=(
        "Start the run configure_optimization set up. Takes no arguments: "
        "everything is configuration, and it is configured beforehand.\n"
        "The backend validates the configuration, shapes the engine's payload "
        "and starts the job, so THE OPTIMIZER SCREEN DOES NOT HAVE TO BE OPEN "
        "— the user can be anywhere in the app, or nowhere. The run persists "
        "its cycles and reaches its terminal state on its own; poll "
        "get_optimization_status.\n"
        "A configuration that cannot run is refused before anything starts, "
        "with every reason listed in the app's own words."
    ),
)
async def start_optimization() -> dict:
    return await optimizer_tools.start_optimization(client)


@mcp.tool(
    name="get_optimization_status",
    description=(
        "Progress and terminal state of an optimization: cycles saved so far, "
        "the best profit, and `state` — 'running' while the engine reports "
        "this run active, 'finished' once it no longer does. Defaults to the "
        "run started in this session; pass opt_id for any other. An app "
        "restart also reads as finished, so cross-check a fresh run with a "
        "stable cycles_saved across two polls. When finished, `next_step` "
        "carries the selection sequence."
    ),
    annotations=READ_ONLY,
)
async def get_optimization_status(opt_id: int | None = None) -> dict:
    return await optimizer_tools.get_optimization_status(client, opt_id)


@mcp.tool(
    name="control_optimization",
    description=(
        "Control the running optimization: action='pause', 'resume', 'stop', "
        "or 'scale' with workers=N. Addressed to the engine by the run's own "
        "ticket, so the Optimizer screen does not have to be open. Scaling "
        "only takes effect on a paused run — pause, scale, resume. "
        "Stopping takes up to ~150 s to tear down, and a new run "
        "cannot start until it finishes."
    ),
)
async def control_optimization(action: str, workers: int | None = None) -> dict:
    return await optimizer_tools.control_optimization(client, action, workers)


@mcp.tool(
    name="validate_finalist",
    description=(
        "Run the finalist robustness battery against a saved strategy with "
        "its parameters unchanged: rolling walk-forward folds, the harsh "
        "Monte Carlo modes (drop_best_trades, cost_degradation, time_slice, "
        "bootstrap) at every_pass, and intrabar simulation. The app has no "
        "standalone robustness runner, so this configures a one-combination "
        "optimization (one numeric parameter pinned to its own value, Brute "
        "Force, 1 cycle) and asks the Optimizer screen to start it — the "
        "screen must be open, and the run occupies the app's single run "
        "slot. Evidence lands where every run's does: rolling folds at run "
        "level, Monte Carlo and Hold-Out on the single cycle. When it "
        "finishes, verify the WalkForwardRolling bucket is non-empty, read "
        "get_cycle_robustness, and attach_rolling_to_strategy. This is the "
        "step between saving a run's winner and trusting it."
    ),
)
async def validate_finalist(
    strategy_id: int,
    dataset_id: str | None = None,
    folds: int = 6,
    curves: int = 500,
    monte_carlo_modes: list[str] | None = None,
    intrabar_timeframe: str | None = None,
    workers: int | None = None,
    max_ram_pct: int | None = None,
) -> dict:
    return await optimizer_tools.validate_finalist(
        client, strategy_id, dataset_id, folds, curves, monte_carlo_modes,
        intrabar_timeframe, workers, max_ram_pct,
    )


@mcp.tool(
    name="attach_rolling_to_strategy",
    description=(
        "Attach a Walk-Forward Rolling run's folds to a SAVED strategy, so "
        "the evidence shows up in its robustness section (get_strategy_detail "
        "is the dossier). This is the return leg of finalist validation: run "
        "validate_finalist against the saved strategy, then attach its opt_id "
        "here. For a rolling run whose base was a TEMPLATE (no saved strategy "
        "yet), use create_strategy_from_rolling instead — it creates the "
        "strategy and carries the folds in one step. Before attaching, verify "
        "the run's WalkForwardRolling bucket is non-empty with "
        "get_optimization_summary: a rolling run killed by RAM reads "
        "'finished' with 0 folds and no error."
    ),
)
async def attach_rolling_to_strategy(strategy_id: int, opt_id: int) -> dict:
    return await optimizer_tools.attach_rolling_to_strategy(client, strategy_id, opt_id)


# --------------------------------------------------------------------------
# Live trading — reads are open; mutations need MINDSTRAT_MCP_ALLOW_LIVE=1
# --------------------------------------------------------------------------


@mcp.tool(
    name="live_auth_status",
    description=(
        "Check live-trading access: whether the app is signed in, which "
        "account, when the session expires, and whether live mutations "
        "(deploy/stop/resize) are enabled. Live tools act as the signed-in "
        "user — this server holds no credentials of its own, so if nobody is "
        "signed in to the app they simply do not work."
    ),
    annotations=READ_ONLY,
)
async def live_auth_status() -> dict:
    return await live_tools.live_auth_status(client)


@mcp.tool(
    name="list_live_strategies",
    description=(
        "Live portfolio: every deployed strategy with its status "
        "(PENDING/ASSIGNED/RUNNING/ERROR/STOPPED), desired_state, trade count, "
        "wins/losses, total P&L and last error, plus portfolio totals. Filter "
        "with status."
    ),
    annotations=ToolAnnotations(read_only_hint=True, open_world_hint=True),
)
async def list_live_strategies(status: str | None = None) -> dict:
    return await live_tools.list_live_strategies(client, status)


@mcp.tool(
    name="get_live_strategy",
    description=(
        "Inspect one live strategy. section='summary' gives counts and the most "
        "recent trades and events; 'trades' and 'events' page through the full "
        "history; 'config' returns the deployed capital configuration."
    ),
    annotations=ToolAnnotations(read_only_hint=True, open_world_hint=True),
)
async def get_live_strategy(
    live_strategy_id: str,
    section: str = "summary",
    limit: int | None = None,
    offset: int = 0,
) -> dict:
    return await live_tools.get_live_strategy(client, live_strategy_id, section, limit, offset)


@mcp.tool(
    name="list_exchange_accounts",
    description=(
        "List exchange accounts available for live deployment. API keys are "
        "masked; use the exchange_account_id when deploying."
    ),
    annotations=ToolAnnotations(read_only_hint=True, open_world_hint=True),
)
async def list_exchange_accounts() -> dict:
    return await live_tools.list_exchange_accounts(client)


@mcp.tool(
    name="deploy_live_strategy",
    description=(
        "Deploy a saved strategy to live trading. environment='demo' paper "
        "trades; environment='live' TRADES REAL MONEY and requires "
        "exchange_account_id. Requires confirm=true and "
        "MINDSTRAT_MCP_ALLOW_LIVE=1. capital_cfg takes initial_capital, "
        "order_size_mode, order_size, commission, commission_type and "
        "slippage_bps; auxiliary_datasets maps slots to {symbol, interval}."
    ),
    annotations=ToolAnnotations(destructive_hint=True, open_world_hint=True, idempotent_hint=False),
)
async def deploy_live_strategy(
    saved_strategy_id: int,
    symbol: str,
    interval: str,
    environment: str,
    exchange: str = "binance",
    kind: str = "futures",
    margin_type: str | None = "USDM",
    exchange_slug: str = "binance",
    exchange_account_id: str | None = None,
    capital_cfg: dict | None = None,
    auxiliary_datasets: dict | None = None,
    strategy_name: str | None = None,
    confirm: bool = False,
) -> dict:
    return await live_tools.deploy_live_strategy(
        client,
        saved_strategy_id,
        symbol,
        interval,
        environment,
        exchange,
        kind,
        margin_type,
        exchange_slug,
        exchange_account_id,
        capital_cfg,
        auxiliary_datasets,
        strategy_name,
        confirm,
    )


@mcp.tool(
    name="stop_live_strategy",
    description=(
        "Stop a live strategy. Requires confirm=true and "
        "MINDSTRAT_MCP_ALLOW_LIVE=1. Open positions may be affected; the stop "
        "converges asynchronously."
    ),
    annotations=ToolAnnotations(destructive_hint=True, open_world_hint=True, idempotent_hint=False),
)
async def stop_live_strategy(live_strategy_id: str, confirm: bool = False) -> dict:
    return await live_tools.stop_live_strategy(client, live_strategy_id, confirm)


@mcp.tool(
    name="update_live_order_size",
    description=(
        "Change the order size of a running live strategy. Takes effect on the "
        "next trade and reports whether a trade is currently open. Requires "
        "confirm=true and MINDSTRAT_MCP_ALLOW_LIVE=1."
    ),
    annotations=ToolAnnotations(destructive_hint=True, open_world_hint=True, idempotent_hint=False),
)
async def update_live_order_size(
    live_strategy_id: str, order_size: float, confirm: bool = False
) -> dict:
    return await live_tools.update_live_order_size(client, live_strategy_id, order_size, confirm)


def main() -> None:
    logger.info("Starting MindStrat MCP server (stdio)")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

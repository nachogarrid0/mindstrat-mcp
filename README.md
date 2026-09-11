# MindStrat MCP

Drive the [MindStrat](https://mindstrat.ai) desktop trading app from Claude Code — download market data, write and backtest strategies, run optimizations with robustness tests, and deploy to live trading, without leaving your terminal.

It ships with the app's manual, so the agent knows how each screen works, what every setting means, and how to write a strategy in MindStrat's MSF format that behaves in live exactly as it did in the backtest.

---

## Install

You need three things:

1. **The MindStrat desktop app**, installed and **running**. This server talks to the app's local backend; it does nothing on its own.
2. **Signed in** to the app. The local engine is gated on your session.
3. **[uv](https://docs.astral.sh/uv/getting-started/installation/)**, which runs the server.

Then, one command:

```bash
claude mcp add mindstrat --scope user -- uvx --from git+https://github.com/nachogarrid0/mindstrat-mcp mindstrat-mcp
```

Restart Claude Code and check it connected with `/mcp`.

> `--scope user` makes it available in every directory. Without it Claude Code registers the server only for the folder you happened to be in.

### Don't have uv?

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Open a new terminal afterwards so it lands on your PATH.

---

## What you get

**56 tools**, grouped by the screen they drive: Market Assets, the Strategy Creator, the Optimizer, the Strategy Manager, portfolios and live trading. They call the same endpoints the app's own screens call, so the app owns every result — nothing here recomputes a metric.

**The manual**, which is the part that matters for writing strategies. The agent reads it on demand:

| | |
|---|---|
| `mindstrat://product-map` | What the app is and what each section does, the vocabulary of objects, and which state you share with the screen |
| `mindstrat://settings` | Every control that changes a result: units, defaults, and which defaults lie |
| `mindstrat://msf/parity` | The rule the MSF format exists to protect, and the Live-Readiness Audit |
| `mindstrat://msf/canon` | The binding structure of a strategy and the full engine API |
| `mindstrat://msf/runtime-constraints` | What the runtime rejects, and why |
| `mindstrat://msf/template` | The annotated skeleton |
| `mindstrat://msf/examples` | Four complete worked strategies |
| `mindstrat://msf/visualization` | The chart series schema |
| `mindstrat://tools` | The tool catalogue, by screen |

---

## Try it

With the app open, ask Claude Code:

> What datasets do I have for BTCUSDT?

> Write me a SuperTrend strategy on BTCUSDT 4h with an ADX filter, backtest it with realistic costs, and run the Live-Readiness Audit on it.

The second one is the real test. A strategy that passes that audit behaves in live the way it did in the backtest — which is the whole point of the format.

---

## Two things worth knowing before you trade on it

**Every cost default in the app is zero.** Commission and slippage default to 0 in every surface, so an unconfigured backtest prices a frictionless market and every strategy looks better than it is. Set them before you believe a number — for Binance futures, 0.05% per side is realistic.

**A strategy that exits on take-profit or stop-loss needs intrabar simulation.** Without it, when one candle touches both levels the engine has to assume which came first, and it assumes the stop. Turning intrabar on can change a result substantially in either direction.

Both are explained in `mindstrat://settings`. The agent is told to read it.

---

## Troubleshooting

**`BACKEND_UNREACHABLE`** — the app is not running. Start MindStrat and try again. Ask Claude Code to run `backend_status` to confirm.

**`401` / `local.no_session`** — the app is running but you are signed out, or it restarted and lost the session. Sign in, or just click the MindStrat window to bring it into focus.

**`spawn uvx ENOENT`** — Claude Code cannot find `uvx`. Install uv (above) and open a new terminal. If it persists, use the full path: run `where uvx` (Windows) or `which uvx` and put that path in the command instead of `uvx`.

**It connected but the tools do nothing** — check you registered with `--scope user`. Without it the server only exists in one directory.

---

## Live trading is off by default

Deploying, stopping and resizing a live strategy are disabled unless you opt in explicitly, by setting `MINDSTRAT_MCP_ALLOW_LIVE=1` in the server's environment. Every one of them also requires a separate confirmation on the call itself.

`environment="live"` trades real money on your own exchange account. `environment="demo"` paper-trades against the testnet.

Stopping a live strategy tells it to stop deciding — it does **not** close an open position. Anything open stays open on the exchange, and its take-profit and stop-loss stop being watched. Close it yourself.

---

## Privacy

The server runs on your machine and talks to your app over loopback. It holds no credentials of its own: it acts as whoever is signed in to MindStrat. Nothing is sent anywhere else.

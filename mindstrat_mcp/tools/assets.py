"""Market Assets tools: downloaded datasets and the async download queue.

Backend surface: /assets (gated on the signed-in desktop session, like the rest
of the product routers). Timestamps on the wire are milliseconds.
The download queue lives in backend memory, so jobs vanish if the app restarts.
"""

from __future__ import annotations

from typing import Any

from ..client import BackendClient
from ..errors import McpToolError
from ..shaping import clamp_limit, envelope, pick, round_numbers

DEFAULT_EXCHANGE = "binance"
DEFAULT_ENVIRONMENT = "futures_usd"

# Local paths and checksums say nothing about the data and leak filesystem
# layout; everything else the app reports comes through.
_DATASET_NOISE = ("file_path", "checksum", "symbol_normalized", "timeframe_norm")

_DATASET_FIELDS = (
    "snapshot_id",
    "symbol",
    "timeframe",
    "exchange",
    "environment",
    "start_date",
    "end_date",
    "rows",
    "missing",
    "duplicates",
    "size_bytes",
    "source",
    "created_at",
)

_JOB_FIELDS = (
    "id",
    "symbol",
    "timeframe",
    "exchange",
    "environment",
    "status",
    "progress",
    "bars_downloaded",
    "total_bars",
    "attempts",
    "max_retries",
    "snapshot_id",
    "refresh_snapshot_id",
    "repair_snapshot_id",
    "repair_result",
    "error",
)


def _job(payload: Any) -> dict[str, Any]:
    job = round_numbers(pick(payload, _JOB_FIELDS))
    warnings = payload.get("warnings") if isinstance(payload, dict) else None
    if warnings:
        job["warnings"] = warnings
    return job


async def list_datasets(
    client: BackendClient,
    symbol: str | None = None,
    timeframe: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """List downloaded OHLCV datasets, most relevant fields only."""
    size = clamp_limit(limit)
    payload = await client.get(
        "/assets/datasets",
        params={"symbol": symbol, "timeframe": timeframe, "limit": size},
    )
    datasets = (payload or {}).get("datasets", [])
    return envelope(
        [pick(item, _DATASET_FIELDS, drop=_DATASET_NOISE) for item in datasets]
    )


async def assets_overview(
    client: BackendClient,
    exchange: str = DEFAULT_EXCHANGE,
    environment: str = DEFAULT_ENVIRONMENT,
    symbol_filter: str | None = None,
    symbol_limit: int | None = None,
) -> dict[str, Any]:
    """Summarise the Market Assets section: environments, symbols and storage."""
    environments = await client.get("/assets/environments", params={"exchange": exchange})
    symbols_payload = await client.get(
        "/assets/symbols", params={"exchange": exchange, "environment": environment}
    )
    metrics = await client.get("/assets/metrics")

    symbols: list[str] = list(symbols_payload.get("symbols", []) if symbols_payload else [])
    if symbol_filter:
        needle = symbol_filter.upper()
        symbols = [s for s in symbols if needle in s.upper()]

    shown = clamp_limit(symbol_limit)
    return {
        "exchange": exchange,
        "environment": environment,
        "environments": (environments or {}).get("environments", []),
        "symbol_count": len(symbols),
        "symbols": symbols[:shown],
        "symbols_truncated": len(symbols) > shown,
        "storage": round_numbers(metrics),
    }


async def start_download(
    client: BackendClient,
    symbol: str,
    timeframe: str,
    start: int | None = None,
    end: int | None = None,
    exchange: str = DEFAULT_EXCHANGE,
    environment: str = DEFAULT_ENVIRONMENT,
    label: str | None = None,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Enqueue an async candle download; poll it with get_download_jobs."""
    body = {
        "symbol": symbol,
        "timeframe": timeframe,
        "start": start,
        "end": end,
        "label": label,
        "exchange": exchange,
        "environment": environment,
        "max_retries": max_retries,
    }
    payload = await client.post(
        "/assets/downloads/jobs", json={k: v for k, v in body.items() if v is not None}
    )
    job = _job(payload)
    job["note"] = "Queued. Poll get_download_jobs with this id until status is completed."
    return job


async def get_download_jobs(
    client: BackendClient,
    job_id: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Poll one download job, or list recent jobs (newest first)."""
    if job_id:
        job = _job(await client.get(f"/assets/downloads/jobs/{job_id}"))
        if job.get("status") == "completed":
            job["next_step"] = (
                "Dataset ready: check its coverage with get_dataset_summary, "
                "then characterize it with run_python before designing "
                "anything on it."
            )
        return job

    payload = await client.get("/assets/downloads/jobs")
    jobs = [_job(item) for item in (payload or {}).get("jobs", [])]
    if status:
        jobs = [job for job in jobs if job.get("status") == status]
    size = clamp_limit(limit)
    return envelope(jobs[:size], total=len(jobs))


async def cancel_download(client: BackendClient, job_id: str) -> dict[str, Any]:
    """Cancel a queued or running download job."""
    await client.delete(f"/assets/downloads/jobs/{job_id}")
    return {"cancelled": True, "job_id": job_id}


async def maintain_dataset(
    client: BackendClient, snapshot_id: str, action: str
) -> dict[str, Any]:
    """Refresh a dataset to the latest candles, or repair detected gaps."""
    routes = {
        "refresh": f"/assets/datasets/{snapshot_id}/refresh",
        "repair_gaps": f"/assets/datasets/{snapshot_id}/repair-gaps",
    }
    if action not in routes:
        raise McpToolError("action must be 'refresh' or 'repair_gaps'")

    job = _job(await client.post(routes[action]))
    job["note"] = f"{action} queued. Poll get_download_jobs with this id."
    return job


async def delete_dataset(
    client: BackendClient, snapshot_id: str, confirm: bool = False
) -> dict[str, Any]:
    """Permanently delete a dataset snapshot. Requires confirm=true."""
    if not confirm:
        raise McpToolError(
            f"Refusing to delete dataset {snapshot_id}: pass confirm=true to proceed."
        )
    await client.delete(f"/assets/datasets/{snapshot_id}")
    return {"deleted": True, "snapshot_id": snapshot_id}

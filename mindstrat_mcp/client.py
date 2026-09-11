"""HTTP client for the local MindStrat backend, with port discovery."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from . import config
from .errors import BACKEND_UNREACHABLE, McpToolError, from_response

logger = logging.getLogger(__name__)


def _candidate_ports() -> list[tuple[int, str]]:
    """Ports to probe, in priority order, paired with how they were found."""
    candidates: list[tuple[int, str]] = []
    seen: set[int] = set()

    def add(port: int, source: str) -> None:
        if port and port not in seen:
            seen.add(port)
            candidates.append((port, source))

    configured = config.configured_port()
    if configured:
        add(configured, f"{config.PORT_ENV} env var")

    add(config.DEV_DEFAULT_PORT, "dev default")

    for port in _ports_from_backend_lock():
        add(port, "backend.lock PID")

    return candidates


def _ports_from_backend_lock() -> list[int]:
    """Resolve listening ports of the backend process named in backend.lock.

    The packaged app lets Tauri pick a free port and passes it to the sidecar
    via MINDSTRAT_PORT, so it is not discoverable from disk; the PID is.
    """
    lock = config.backend_lock_path()
    try:
        pid = int(lock.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return []

    try:
        import psutil
    except ImportError:
        logger.warning("psutil unavailable; cannot resolve port from PID %s", pid)
        return []

    ports: list[int] = []
    try:
        for conn in psutil.Process(pid).net_connections(kind="inet"):
            if conn.status == psutil.CONN_LISTEN and conn.laddr:
                ports.append(conn.laddr.port)
    except Exception as exc:  # stale lock file, access denied, ...
        logger.debug("Could not inspect backend PID %s: %s", pid, exc)
    return ports


class BackendClient:
    """Thin async wrapper over the backend API.

    Rediscovers the port lazily: the packaged app picks a new one on every
    restart, so a cached base URL can go stale mid-session.
    """

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._client = httpx.AsyncClient(
            timeout=config.DEFAULT_TIMEOUT, transport=transport
        )
        self._port: int | None = None
        self._source: str | None = None

    @property
    def port(self) -> int | None:
        return self._port

    @property
    def discovery_source(self) -> str | None:
        return self._source

    def base_url(self, port: int | None = None) -> str:
        return f"http://{config.BACKEND_HOST}:{port or self._port}"

    async def aclose(self) -> None:
        await self._client.aclose()

    async def ensure_port(self, force: bool = False) -> int:
        """Return a port whose /health responds, probing candidates in order."""
        if self._port is not None and not force:
            return self._port

        for port, source in _candidate_ports():
            try:
                response = await self._client.get(
                    f"http://{config.BACKEND_HOST}:{port}/health", timeout=2.0
                )
            except httpx.HTTPError:
                continue
            if response.status_code == 200:
                self._port = port
                self._source = source
                logger.info("Backend found on port %s (%s)", port, source)
                return port

        self._port = None
        self._source = None
        raise McpToolError(BACKEND_UNREACHABLE)

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        timeout: float | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Call the backend and return parsed JSON (None for 204)."""
        clean_params = (
            {k: v for k, v in params.items() if v is not None} if params else None
        )
        # Identify every call as coming from the MCP server. The Code Creator
        # screen uses this to tell changes it made from changes made for it, so
        # it can offer to open a strategy loaded here instead of overwriting
        # what the user is editing.
        headers = {**(headers or {}), "X-MindStrat-Client": "mcp"}

        for attempt in (1, 2):
            port = await self.ensure_port(force=attempt == 2)
            try:
                response = await self._client.request(
                    method,
                    f"{self.base_url(port)}{path}",
                    params=clean_params,
                    json=json,
                    headers=headers,
                    timeout=timeout or config.DEFAULT_TIMEOUT,
                )
            except httpx.TimeoutException as exc:
                raise McpToolError(f"Backend timed out on {method} {path}: {exc}") from exc
            except httpx.HTTPError as exc:
                if attempt == 1:
                    # The app may have restarted on a different port.
                    logger.info("Connection failed on port %s, rediscovering", port)
                    continue
                raise McpToolError(BACKEND_UNREACHABLE) from exc

            if response.status_code >= 400:
                raise from_response(response)
            if response.status_code == 204 or not response.content:
                return None
            try:
                return response.json()
            except ValueError:
                return response.text

        raise McpToolError(BACKEND_UNREACHABLE)

    async def get(self, path: str, **kwargs: Any) -> Any:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Any:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> Any:
        return await self.request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs: Any) -> Any:
        return await self.request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> Any:
        return await self.request("DELETE", path, **kwargs)

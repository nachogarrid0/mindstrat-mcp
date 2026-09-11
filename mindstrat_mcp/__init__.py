"""MindStrat MCP server package.

Wraps the local MindStrat backend (FastAPI) as MCP tools. Tool implementations
are plain async functions taking a BackendClient, so they stay independent of
the MCP transport and can later be mounted inside the backend itself.
"""

__version__ = "0.1.0"

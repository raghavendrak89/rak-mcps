"""Inspect and stop PVE tasks (UPIDs)."""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..pve_client import PVEClient
from ._safety import ensure_destructive_allowed


def register(mcp: FastMCP, client: PVEClient, settings: Settings) -> None:
    @mcp.tool()
    def task_list(node: str, limit: int = 50, errors_only: bool = False) -> list[dict[str, Any]]:
        """List recent tasks on a node."""
        params: dict[str, Any] = {"limit": limit}
        if errors_only:
            params["errors"] = 1
        return client.api.nodes(node).tasks.get(**params)

    @mcp.tool()
    def task_status(node: str, upid: str) -> dict[str, Any]:
        """Status of a specific task UPID."""
        return client.api.nodes(node).tasks(upid).status.get()

    @mcp.tool()
    def task_log(node: str, upid: str, start: int = 0, limit: int = 200) -> list[dict[str, Any]]:
        """Fetch task log lines."""
        return client.api.nodes(node).tasks(upid).log.get(start=start, limit=limit)

    @mcp.tool()
    def task_wait(node: str, upid: str, timeout: int = 300) -> dict[str, Any]:
        """Block until a task completes (or timeout). Returns final status + log tail."""
        result = client.wait_task(node, upid, timeout)
        return {
            "upid": result.upid,
            "status": result.status,
            "exitstatus": result.exitstatus,
            "ok": result.ok,
            "log_tail": result.log_tail,
        }

    @mcp.tool()
    def task_stop(node: str, upid: str, confirm: bool = False) -> dict[str, Any]:
        """Stop a running task. DESTRUCTIVE: may leave partial state behind."""
        ensure_destructive_allowed(settings, "task_stop", confirm)
        return {"result": client.api.nodes(node).tasks(upid).delete()}

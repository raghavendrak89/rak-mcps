"""Cluster-wide queries: status, resources, log, next free VMID, HA."""
from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from ..pve_client import PVEClient


def register(mcp: FastMCP, client: PVEClient) -> None:
    @mcp.tool()
    def cluster_status() -> list[dict[str, Any]]:
        """Return PVE cluster quorum status and per-node membership.

        Use this first when diagnosing anything cluster-wide. Reveals quorum,
        node online/offline state, and the cluster name + nodeid mapping.
        """
        return client.api.cluster.status.get()

    @mcp.tool()
    def cluster_resources(
        kind: Literal["vm", "storage", "node", "sdn", "all"] = "all",
    ) -> list[dict[str, Any]]:
        """Single-shot inventory of cluster resources by kind.

        Much faster than walking nodes one by one. 'vm' covers both qemu and lxc.
        """
        params = {} if kind == "all" else {"type": kind}
        return client.api.cluster.resources.get(**params)

    @mcp.tool()
    def cluster_next_vmid() -> int:
        """Return the next free VMID the cluster would allocate.

        Use before creating a VM/CT if the caller hasn't specified an id.
        """
        return int(client.api.cluster.nextid.get())

    @mcp.tool()
    def cluster_log(limit: int = 50) -> list[dict[str, Any]]:
        """Recent cluster log entries (newest first). Useful for triaging incidents."""
        return client.api.cluster.log.get(max=limit)

    @mcp.tool()
    def cluster_ha_status() -> dict[str, Any]:
        """HA manager status: current master, quorum, resource states."""
        return {
            "manager_status": client.api.cluster.ha.status.manager_status.get(),
            "resources": client.api.cluster.ha.resources.get(),
            "groups": client.api.cluster.ha.groups.get(),
        }

    @mcp.tool()
    def cluster_tasks(limit: int = 50, errors_only: bool = False) -> list[dict[str, Any]]:
        """Recent cluster tasks. Use errors_only=true to surface only failed UPIDs."""
        params: dict[str, Any] = {"limit": limit}
        if errors_only:
            params["errors"] = 1
        return client.api.cluster.tasks.get(**params)

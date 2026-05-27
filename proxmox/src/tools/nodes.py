"""Per-node ops: list, status, stats, services, reboot/shutdown."""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..pve_client import PVEClient
from ._safety import ensure_destructive_allowed


def register(mcp: FastMCP, client: PVEClient, settings: Settings) -> None:
    @mcp.tool()
    def node_list() -> list[dict[str, Any]]:
        """List all nodes in the cluster with online/offline state and load."""
        return client.api.nodes.get()

    @mcp.tool()
    def node_status(node: str) -> dict[str, Any]:
        """Detailed node status: CPU, memory, uptime, kernel, pveversion."""
        return client.api.nodes(node).status.get()

    @mcp.tool()
    def node_rrd_data(
        node: str,
        timeframe: str = "hour",
        cf: str = "AVERAGE",
    ) -> list[dict[str, Any]]:
        """Time-series stats for a node. timeframe: hour|day|week|month|year."""
        return client.api.nodes(node).rrddata.get(timeframe=timeframe, cf=cf)

    @mcp.tool()
    def node_services(node: str) -> list[dict[str, Any]]:
        """Systemd-managed PVE services on the node (pveproxy, pvedaemon, etc.)."""
        return client.api.nodes(node).services.get()

    @mcp.tool()
    def node_service_action(
        node: str,
        service: str,
        action: str,  # start|stop|restart|reload
    ) -> dict[str, Any]:
        """Control a PVE-managed service. Non-destructive (services restart cleanly)."""
        if action not in {"start", "stop", "restart", "reload"}:
            raise ValueError(f"Unsupported action: {action}")
        method = getattr(client.api.nodes(node).services(service), action)
        upid = method.post()
        return {"upid": upid}

    @mcp.tool()
    def node_reboot(node: str, confirm: bool = False) -> dict[str, Any]:
        """Reboot a Proxmox node. DESTRUCTIVE: takes the node and all its VMs offline.

        Pass confirm=true to proceed. Migrate or fence VMs first if you care about uptime.
        """
        ensure_destructive_allowed(settings, "node_reboot", confirm)
        return {"result": client.api.nodes(node).status.post(command="reboot")}

    @mcp.tool()
    def node_shutdown(node: str, confirm: bool = False) -> dict[str, Any]:
        """Power off a Proxmox node. DESTRUCTIVE: node will need manual/IPMI power-on."""
        ensure_destructive_allowed(settings, "node_shutdown", confirm)
        return {"result": client.api.nodes(node).status.post(command="shutdown")}

    @mcp.tool()
    def node_wakeonlan(node: str) -> dict[str, Any]:
        """Send WOL packet to a powered-off node (must be configured in PVE)."""
        return {"result": client.api.nodes(node).wakeonlan.post()}

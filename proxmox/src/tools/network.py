"""Network and SDN configuration."""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..pve_client import PVEClient
from ._safety import ensure_destructive_allowed


def register(mcp: FastMCP, client: PVEClient, settings: Settings) -> None:
    @mcp.tool()
    def network_interfaces(node: str) -> list[dict[str, Any]]:
        """List network interfaces (bridges, bonds, VLANs) on a node."""
        return client.api.nodes(node).network.get()

    @mcp.tool()
    def network_apply(node: str, confirm: bool = False) -> dict[str, Any]:
        """Apply pending /etc/network/interfaces.new on a node. DESTRUCTIVE: can drop connectivity."""
        ensure_destructive_allowed(settings, "network_apply", confirm)
        return {"result": client.api.nodes(node).network.put()}

    @mcp.tool()
    def network_revert(node: str) -> dict[str, Any]:
        """Discard pending interface changes on a node."""
        return {"result": client.api.nodes(node).network.delete()}

    @mcp.tool()
    def sdn_zones() -> list[dict[str, Any]]:
        return client.api.cluster.sdn.zones.get()

    @mcp.tool()
    def sdn_vnets() -> list[dict[str, Any]]:
        return client.api.cluster.sdn.vnets.get()

    @mcp.tool()
    def sdn_apply(confirm: bool = False) -> dict[str, Any]:
        """Push pending SDN config cluster-wide. DESTRUCTIVE: takes the SDN dataplane through a reload."""
        ensure_destructive_allowed(settings, "sdn_apply", confirm)
        return {"upid": client.api.cluster.sdn.put()}

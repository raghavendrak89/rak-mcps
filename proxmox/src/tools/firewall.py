"""Proxmox firewall rules at cluster, node, and VM scope."""
from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..pve_client import PVEClient
from ._safety import ensure_destructive_allowed

Scope = Literal["cluster", "node", "vm", "lxc"]


def _scope(client: PVEClient, scope: Scope, node: str | None, vmid: int | None):
    if scope == "cluster":
        return client.api.cluster.firewall
    if scope == "node":
        assert node is not None
        return client.api.nodes(node).firewall
    if scope == "vm":
        assert node is not None and vmid is not None
        return client.api.nodes(node).qemu(vmid).firewall
    if scope == "lxc":
        assert node is not None and vmid is not None
        return client.api.nodes(node).lxc(vmid).firewall
    raise ValueError(scope)


def register(mcp: FastMCP, client: PVEClient, settings: Settings) -> None:
    @mcp.tool()
    def firewall_rules_list(scope: Scope, node: str | None = None, vmid: int | None = None) -> list[dict[str, Any]]:
        """List firewall rules at the given scope."""
        return _scope(client, scope, node, vmid).rules.get()

    @mcp.tool()
    def firewall_rule_add(
        scope: Scope,
        action: str,  # ACCEPT | REJECT | DROP
        type: str,    # in | out
        node: str | None = None,
        vmid: int | None = None,
        source: str | None = None,
        dest: str | None = None,
        proto: str | None = None,
        dport: str | None = None,
        sport: str | None = None,
        comment: str | None = None,
        enable: bool = True,
    ) -> dict[str, Any]:
        """Append a firewall rule. Mirrors the PVE rule schema."""
        params: dict[str, Any] = {"action": action, "type": type, "enable": 1 if enable else 0}
        for k, v in {"source": source, "dest": dest, "proto": proto, "dport": dport, "sport": sport, "comment": comment}.items():
            if v is not None:
                params[k] = v
        return {"result": _scope(client, scope, node, vmid).rules.post(**params)}

    @mcp.tool()
    def firewall_rule_delete(
        scope: Scope,
        pos: int,
        node: str | None = None,
        vmid: int | None = None,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Delete firewall rule by position. DESTRUCTIVE (may open or close paths unexpectedly)."""
        ensure_destructive_allowed(settings, "firewall_rule_delete", confirm)
        return {"result": _scope(client, scope, node, vmid).rules(pos).delete()}

    @mcp.tool()
    def firewall_options_get(scope: Scope, node: str | None = None, vmid: int | None = None) -> dict[str, Any]:
        return _scope(client, scope, node, vmid).options.get()

    @mcp.tool()
    def firewall_options_set(
        scope: Scope,
        options: dict[str, Any],
        node: str | None = None,
        vmid: int | None = None,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Modify firewall options (e.g. enable, policy_in). DESTRUCTIVE if it locks you out."""
        ensure_destructive_allowed(settings, "firewall_options_set", confirm)
        return {"result": _scope(client, scope, node, vmid).options.put(**options)}

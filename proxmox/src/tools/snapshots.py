"""Snapshot management for VMs and LXC containers."""
from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..pve_client import PVEClient
from ._safety import ensure_destructive_allowed

GuestKind = Literal["qemu", "lxc"]


def _guest(client: PVEClient, node: str, kind: GuestKind, vmid: int):
    return getattr(client.api.nodes(node), kind)(vmid)


def register(mcp: FastMCP, client: PVEClient, settings: Settings) -> None:
    @mcp.tool()
    def snapshot_list(node: str, kind: GuestKind, vmid: int) -> list[dict[str, Any]]:
        """List snapshots of a VM (kind=qemu) or container (kind=lxc)."""
        return _guest(client, node, kind, vmid).snapshot.get()

    @mcp.tool()
    def snapshot_create(
        node: str,
        kind: GuestKind,
        vmid: int,
        snapname: str,
        description: str | None = None,
        include_ram: bool = False,
    ) -> dict[str, Any]:
        """Create a snapshot. include_ram only valid for running qemu VMs."""
        params: dict[str, Any] = {"snapname": snapname}
        if description:
            params["description"] = description
        if include_ram and kind == "qemu":
            params["vmstate"] = 1
        return {"upid": _guest(client, node, kind, vmid).snapshot.post(**params)}

    @mcp.tool()
    def snapshot_rollback(
        node: str,
        kind: GuestKind,
        vmid: int,
        snapname: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Roll guest state back to a snapshot. DESTRUCTIVE: discards changes since snapshot."""
        ensure_destructive_allowed(settings, "snapshot_rollback", confirm)
        snap = _guest(client, node, kind, vmid).snapshot(snapname).rollback
        return {"upid": snap.post()}

    @mcp.tool()
    def snapshot_delete(
        node: str,
        kind: GuestKind,
        vmid: int,
        snapname: str,
        confirm: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Delete a snapshot. DESTRUCTIVE & IRREVERSIBLE."""
        ensure_destructive_allowed(settings, "snapshot_delete", confirm)
        params = {"force": 1} if force else {}
        return {"upid": _guest(client, node, kind, vmid).snapshot(snapname).delete(**params)}

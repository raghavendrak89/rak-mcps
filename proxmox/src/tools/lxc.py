"""LXC container management."""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..pve_client import PVEClient
from ._safety import ensure_destructive_allowed


def register(mcp: FastMCP, client: PVEClient, settings: Settings) -> None:
    @mcp.tool()
    def lxc_list(node: str | None = None) -> list[dict[str, Any]]:
        """List LXC containers, cluster-wide or per-node."""
        if node:
            return client.api.nodes(node).lxc.get()
        return [r for r in client.api.cluster.resources.get(type="vm") if r.get("type") == "lxc"]

    @mcp.tool()
    def lxc_get(node: str, vmid: int) -> dict[str, Any]:
        """Full container record (config + status)."""
        return {
            "config": client.api.nodes(node).lxc(vmid).config.get(),
            "status": client.api.nodes(node).lxc(vmid).status.current.get(),
        }

    @mcp.tool()
    def lxc_create(
        node: str,
        vmid: int,
        hostname: str,
        ostemplate: str,
        storage: str,
        cores: int = 1,
        memory_mb: int = 512,
        swap_mb: int = 512,
        rootfs_gb: int = 8,
        password: str | None = None,
        ssh_public_keys: str | None = None,
        net0: str = "name=eth0,bridge=vmbr0,ip=dhcp",
        unprivileged: bool = True,
        start: bool = False,
    ) -> dict[str, Any]:
        """Create LXC. ostemplate like 'local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst'."""
        params: dict[str, Any] = {
            "vmid": vmid,
            "hostname": hostname,
            "ostemplate": ostemplate,
            "storage": storage,
            "cores": cores,
            "memory": memory_mb,
            "swap": swap_mb,
            "rootfs": f"{storage}:{rootfs_gb}",
            "net0": net0,
            "unprivileged": 1 if unprivileged else 0,
        }
        if password:
            params["password"] = password
        if ssh_public_keys:
            params["ssh-public-keys"] = ssh_public_keys
        if start:
            params["start"] = 1
        return {"upid": client.api.nodes(node).lxc.post(**params), "vmid": vmid}

    @mcp.tool()
    def lxc_start(node: str, vmid: int) -> dict[str, Any]:
        return {"upid": client.api.nodes(node).lxc(vmid).status.start.post()}

    @mcp.tool()
    def lxc_shutdown(node: str, vmid: int, timeout: int = 60, force_stop: bool = False) -> dict[str, Any]:
        """Graceful container shutdown."""
        params: dict[str, Any] = {"timeout": timeout}
        if force_stop:
            params["forceStop"] = 1
        return {"upid": client.api.nodes(node).lxc(vmid).status.shutdown.post(**params)}

    @mcp.tool()
    def lxc_stop(node: str, vmid: int, confirm: bool = False) -> dict[str, Any]:
        """Hard stop. DESTRUCTIVE: may leave filesystem inconsistent."""
        ensure_destructive_allowed(settings, "lxc_stop", confirm)
        return {"upid": client.api.nodes(node).lxc(vmid).status.stop.post()}

    @mcp.tool()
    def lxc_reboot(node: str, vmid: int) -> dict[str, Any]:
        return {"upid": client.api.nodes(node).lxc(vmid).status.reboot.post()}

    @mcp.tool()
    def lxc_clone(node: str, vmid: int, newid: int, full: bool = True, hostname: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"newid": newid, "full": 1 if full else 0}
        if hostname:
            params["hostname"] = hostname
        return {"upid": client.api.nodes(node).lxc(vmid).clone.post(**params)}

    @mcp.tool()
    def lxc_migrate(node: str, vmid: int, target: str, restart: bool = False) -> dict[str, Any]:
        """Container migration (offline by default; restart=true brings it back up on target)."""
        params: dict[str, Any] = {"target": target}
        if restart:
            params["restart"] = 1
        return {"upid": client.api.nodes(node).lxc(vmid).migrate.post(**params)}

    @mcp.tool()
    def lxc_config_set(node: str, vmid: int, options: dict[str, Any]) -> dict[str, Any]:
        return {"result": client.api.nodes(node).lxc(vmid).config.put(**options)}

    @mcp.tool()
    def lxc_resize(node: str, vmid: int, disk: str, size: str) -> dict[str, Any]:
        """Grow LXC volume. disk='rootfs' usually; size '+10G' or '32G'."""
        return {"result": client.api.nodes(node).lxc(vmid).resize.put(disk=disk, size=size)}

    @mcp.tool()
    def lxc_delete(node: str, vmid: int, confirm: bool = False, purge: bool = True) -> dict[str, Any]:
        """Delete an LXC container and its rootfs. DESTRUCTIVE & IRREVERSIBLE."""
        ensure_destructive_allowed(settings, "lxc_delete", confirm)
        params = {"purge": 1} if purge else {}
        return {"upid": client.api.nodes(node).lxc(vmid).delete(**params)}

"""Backups: vzdump on-demand, scheduled jobs, restore."""
from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..pve_client import PVEClient
from ._safety import ensure_destructive_allowed


def register(mcp: FastMCP, client: PVEClient, settings: Settings) -> None:
    @mcp.tool()
    def backup_list(node: str, storage: str, vmid: int | None = None) -> list[dict[str, Any]]:
        """List backup files in a storage. Optionally filter by VMID."""
        params: dict[str, Any] = {"content": "backup"}
        if vmid is not None:
            params["vmid"] = vmid
        return client.api.nodes(node).storage(storage).content.get(**params)

    @mcp.tool()
    def backup_create(
        node: str,
        vmid: int,
        storage: str,
        mode: Literal["snapshot", "suspend", "stop"] = "snapshot",
        compress: Literal["0", "lzo", "gzip", "zstd"] = "zstd",
        notes: str | None = None,
        mailnotification: Literal["always", "failure"] = "failure",
    ) -> dict[str, Any]:
        """Trigger one-off vzdump backup."""
        params: dict[str, Any] = {
            "vmid": vmid,
            "storage": storage,
            "mode": mode,
            "compress": compress,
            "mailnotification": mailnotification,
        }
        if notes:
            params["notes-template"] = notes
        return {"upid": client.api.nodes(node).vzdump.post(**params)}

    @mcp.tool()
    def backup_delete(
        node: str,
        storage: str,
        volid: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Delete a backup file. DESTRUCTIVE: cannot be undone unless replicated elsewhere."""
        ensure_destructive_allowed(settings, "backup_delete", confirm)
        return {"result": client.api.nodes(node).storage(storage).content(volid).delete()}

    @mcp.tool()
    def backup_jobs_list() -> list[dict[str, Any]]:
        """List scheduled vzdump jobs (cluster-wide)."""
        return client.api.cluster.backup.get()

    @mcp.tool()
    def backup_job_create(
        schedule: str,
        storage: str,
        vmids: str | None = None,
        all_guests: bool = False,
        mode: str = "snapshot",
        compress: str = "zstd",
        enabled: bool = True,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """Create scheduled vzdump job. schedule is systemd timer syntax e.g. 'sat 02:00'."""
        params: dict[str, Any] = {
            "schedule": schedule,
            "storage": storage,
            "mode": mode,
            "compress": compress,
            "enabled": 1 if enabled else 0,
        }
        if all_guests:
            params["all"] = 1
        elif vmids:
            params["vmid"] = vmids
        else:
            raise ValueError("Provide vmids or set all_guests=true")
        if comment:
            params["comment"] = comment
        return {"result": client.api.cluster.backup.post(**params)}

    @mcp.tool()
    def backup_job_delete(job_id: str, confirm: bool = False) -> dict[str, Any]:
        """Remove a scheduled backup job. DESTRUCTIVE (schedule loss; existing backups untouched)."""
        ensure_destructive_allowed(settings, "backup_job_delete", confirm)
        return {"result": client.api.cluster.backup(job_id).delete()}

    @mcp.tool()
    def backup_restore_vm(
        node: str,
        vmid: int,
        archive: str,
        storage: str | None = None,
        force: bool = False,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Restore a VM from backup. DESTRUCTIVE if vmid exists (force=true required, gated)."""
        if force:
            ensure_destructive_allowed(settings, "backup_restore_vm(force)", confirm)
        params: dict[str, Any] = {"vmid": vmid, "archive": archive}
        if storage:
            params["storage"] = storage
        if force:
            params["force"] = 1
        return {"upid": client.api.nodes(node).qemu.post(**params)}

    @mcp.tool()
    def backup_restore_lxc(
        node: str,
        vmid: int,
        ostemplate: str,
        storage: str,
        force: bool = False,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Restore an LXC container from backup. ostemplate is the backup volid."""
        if force:
            ensure_destructive_allowed(settings, "backup_restore_lxc(force)", confirm)
        params: dict[str, Any] = {
            "vmid": vmid,
            "ostemplate": ostemplate,
            "storage": storage,
            "restore": 1,
        }
        if force:
            params["force"] = 1
        return {"upid": client.api.nodes(node).lxc.post(**params)}

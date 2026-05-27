"""QEMU/KVM virtual machine management."""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..pve_client import PVEClient
from ._safety import ensure_destructive_allowed


def register(mcp: FastMCP, client: PVEClient, settings: Settings) -> None:
    @mcp.tool()
    def vm_list(node: str | None = None) -> list[dict[str, Any]]:
        """List VMs. If node given, restrict to that node; else cluster-wide via /cluster/resources."""
        if node:
            return client.api.nodes(node).qemu.get()
        return [r for r in client.api.cluster.resources.get(type="vm") if r.get("type") == "qemu"]

    @mcp.tool()
    def vm_get(node: str, vmid: int) -> dict[str, Any]:
        """Full VM record: config + current status."""
        return {
            "config": client.api.nodes(node).qemu(vmid).config.get(),
            "status": client.api.nodes(node).qemu(vmid).status.current.get(),
        }

    @mcp.tool()
    def vm_rrd_data(node: str, vmid: int, timeframe: str = "hour") -> list[dict[str, Any]]:
        """Time-series CPU/memory/net/disk stats for a VM."""
        return client.api.nodes(node).qemu(vmid).rrddata.get(timeframe=timeframe)

    # ---- lifecycle ----------------------------------------------------

    @mcp.tool()
    def vm_start(node: str, vmid: int) -> dict[str, Any]:
        """Start a VM. Returns task UPID."""
        return {"upid": client.api.nodes(node).qemu(vmid).status.start.post()}

    @mcp.tool()
    def vm_shutdown(node: str, vmid: int, timeout: int = 60, force_stop: bool = False) -> dict[str, Any]:
        """Graceful shutdown via ACPI. If force_stop, falls back to stop after timeout."""
        params: dict[str, Any] = {"timeout": timeout}
        if force_stop:
            params["forceStop"] = 1
        return {"upid": client.api.nodes(node).qemu(vmid).status.shutdown.post(**params)}

    @mcp.tool()
    def vm_stop(node: str, vmid: int, confirm: bool = False) -> dict[str, Any]:
        """Hard stop (power off, no ACPI). DESTRUCTIVE: may corrupt guest filesystems."""
        ensure_destructive_allowed(settings, "vm_stop", confirm)
        return {"upid": client.api.nodes(node).qemu(vmid).status.stop.post()}

    @mcp.tool()
    def vm_reboot(node: str, vmid: int) -> dict[str, Any]:
        """Graceful reboot."""
        return {"upid": client.api.nodes(node).qemu(vmid).status.reboot.post()}

    @mcp.tool()
    def vm_reset(node: str, vmid: int, confirm: bool = False) -> dict[str, Any]:
        """Hard reset. DESTRUCTIVE: like pressing the reset button."""
        ensure_destructive_allowed(settings, "vm_reset", confirm)
        return {"upid": client.api.nodes(node).qemu(vmid).status.reset.post()}

    @mcp.tool()
    def vm_suspend(node: str, vmid: int, to_disk: bool = False) -> dict[str, Any]:
        """Suspend VM. to_disk=true does hibernate-to-storage."""
        params = {"todisk": 1} if to_disk else {}
        return {"upid": client.api.nodes(node).qemu(vmid).status.suspend.post(**params)}

    @mcp.tool()
    def vm_resume(node: str, vmid: int) -> dict[str, Any]:
        """Resume a suspended VM."""
        return {"upid": client.api.nodes(node).qemu(vmid).status.resume.post()}

    # ---- creation / cloning / migration -------------------------------

    @mcp.tool()
    def vm_create(
        node: str,
        vmid: int,
        name: str,
        cores: int = 2,
        memory_mb: int = 2048,
        disk: str | None = None,
        net0: str = "virtio,bridge=vmbr0",
        iso: str | None = None,
        ostype: str = "l26",
        start: bool = False,
    ) -> dict[str, Any]:
        """Create a fresh VM.

        - disk: PVE volume spec e.g. 'local-lvm:32' for 32G on local-lvm.
        - iso: storage:iso/filename.iso, attached to ide2 as cdrom.
        - ostype: l26 (Linux 2.6+), win11, win10, win8, etc.
        """
        params: dict[str, Any] = {
            "vmid": vmid,
            "name": name,
            "cores": cores,
            "memory": memory_mb,
            "net0": net0,
            "ostype": ostype,
        }
        if disk:
            params["scsi0"] = disk
            params["scsihw"] = "virtio-scsi-pci"
            params["bootdisk"] = "scsi0"
        if iso:
            params["ide2"] = f"{iso},media=cdrom"
        if start:
            params["start"] = 1
        upid = client.api.nodes(node).qemu.post(**params)
        return {"upid": upid, "vmid": vmid}

    @mcp.tool()
    def vm_clone(
        node: str,
        vmid: int,
        newid: int,
        name: str | None = None,
        full: bool = True,
        target: str | None = None,
        storage: str | None = None,
    ) -> dict[str, Any]:
        """Clone a VM (or template). full=false makes a linked clone."""
        params: dict[str, Any] = {"newid": newid, "full": 1 if full else 0}
        if name:
            params["name"] = name
        if target:
            params["target"] = target
        if storage:
            params["storage"] = storage
        return {"upid": client.api.nodes(node).qemu(vmid).clone.post(**params)}

    @mcp.tool()
    def vm_migrate(
        node: str,
        vmid: int,
        target: str,
        online: bool = True,
        with_local_disks: bool = False,
    ) -> dict[str, Any]:
        """Migrate VM to another node. online=true is live migration."""
        params: dict[str, Any] = {"target": target, "online": 1 if online else 0}
        if with_local_disks:
            params["with-local-disks"] = 1
        return {"upid": client.api.nodes(node).qemu(vmid).migrate.post(**params)}

    @mcp.tool()
    def vm_template_convert(node: str, vmid: int) -> dict[str, Any]:
        """Convert VM into a template. Irreversible without recreating."""
        return {"result": client.api.nodes(node).qemu(vmid).template.post()}

    # ---- config / resize ----------------------------------------------

    @mcp.tool()
    def vm_config_set(node: str, vmid: int, options: dict[str, Any]) -> dict[str, Any]:
        """Update VM config. Options dict mirrors PVE API (e.g. {'cores': 4, 'memory': 4096})."""
        return {"result": client.api.nodes(node).qemu(vmid).config.put(**options)}

    @mcp.tool()
    def vm_resize_disk(node: str, vmid: int, disk: str, size: str) -> dict[str, Any]:
        """Grow a VM disk. size like '+10G' (delta) or '64G' (absolute). Shrinking not supported."""
        return {"result": client.api.nodes(node).qemu(vmid).resize.put(disk=disk, size=size)}

    # ---- destroy ------------------------------------------------------

    @mcp.tool()
    def vm_delete(
        node: str,
        vmid: int,
        confirm: bool = False,
        purge: bool = True,
        destroy_unreferenced_disks: bool = True,
    ) -> dict[str, Any]:
        """Permanently delete a VM and (optionally) all its disks. DESTRUCTIVE & IRREVERSIBLE."""
        ensure_destructive_allowed(settings, "vm_delete", confirm)
        params: dict[str, Any] = {}
        if purge:
            params["purge"] = 1
        if destroy_unreferenced_disks:
            params["destroy-unreferenced-disks"] = 1
        return {"upid": client.api.nodes(node).qemu(vmid).delete(**params)}

    # ---- guest agent --------------------------------------------------

    @mcp.tool()
    def vm_agent_exec(node: str, vmid: int, command: list[str], wait: int = 5) -> dict[str, Any]:
        """Execute a command via qemu-guest-agent. Requires agent installed and enabled."""
        result = client.api.nodes(node).qemu(vmid).agent.exec.post(command=command)
        pid = result.get("pid")
        if not pid or not wait:
            return result
        import time as _t
        deadline = _t.monotonic() + wait
        while _t.monotonic() < deadline:
            status = client.api.nodes(node).qemu(vmid).agent("exec-status").get(pid=pid)
            if status.get("exited"):
                return status
            _t.sleep(0.5)
        return {"pid": pid, "exited": False, "note": "timed out waiting for exec"}

"""Storage: list, content, upload, wipe."""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..pve_client import PVEClient
from ._safety import ensure_destructive_allowed


def register(mcp: FastMCP, client: PVEClient, settings: Settings) -> None:
    @mcp.tool()
    def storage_list() -> list[dict[str, Any]]:
        """List cluster-defined storages."""
        return client.api.storage.get()

    @mcp.tool()
    def storage_status(node: str) -> list[dict[str, Any]]:
        """Storage usage from a node's POV (active flag, used/total bytes)."""
        return client.api.nodes(node).storage.get()

    @mcp.tool()
    def storage_content(
        node: str,
        storage: str,
        content_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """List contents (volumes, ISOs, backups, templates) of a storage on a node."""
        params: dict[str, Any] = {}
        if content_type:
            params["content"] = content_type
        return client.api.nodes(node).storage(storage).content.get(**params)

    @mcp.tool()
    def storage_volume_delete(
        node: str,
        storage: str,
        volid: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Delete a single volume (ISO, disk image, backup). DESTRUCTIVE & IRREVERSIBLE."""
        ensure_destructive_allowed(settings, "storage_volume_delete", confirm)
        return {"result": client.api.nodes(node).storage(storage).content(volid).delete()}

    @mcp.tool()
    def storage_download_url(
        node: str,
        storage: str,
        url: str,
        filename: str,
        content_type: str = "iso",
        checksum: str | None = None,
        checksum_algorithm: str | None = None,
    ) -> dict[str, Any]:
        """Server-side download a URL into a storage (e.g. fetch an ISO directly to PVE)."""
        params: dict[str, Any] = {
            "url": url,
            "filename": filename,
            "content": content_type,
        }
        if checksum:
            params["checksum"] = checksum
        if checksum_algorithm:
            params["checksum-algorithm"] = checksum_algorithm
        return {"upid": client.api.nodes(node).storage(storage)("download-url").post(**params)}

    @mcp.tool()
    def disks_list(node: str) -> list[dict[str, Any]]:
        """Enumerate physical disks on a node."""
        return client.api.nodes(node).disks.list.get()

    @mcp.tool()
    def disk_wipe(node: str, disk: str, confirm: bool = False) -> dict[str, Any]:
        """Wipe a physical disk on a node. DESTRUCTIVE & IRREVERSIBLE.

        disk like '/dev/sdb'. Verify with disks_list first. This is the kind of
        op you do not want to do twice.
        """
        ensure_destructive_allowed(settings, "disk_wipe", confirm)
        return {"upid": client.api.nodes(node).disks("wipedisk").put(disk=disk)}

    @mcp.tool()
    def storage_remove(storage: str, confirm: bool = False) -> dict[str, Any]:
        """Remove a storage definition from the cluster (data on underlying medium not touched
        unless it's a PVE-managed pool). DESTRUCTIVE: guests referencing it will break."""
        ensure_destructive_allowed(settings, "storage_remove", confirm)
        return {"result": client.api.storage(storage).delete()}

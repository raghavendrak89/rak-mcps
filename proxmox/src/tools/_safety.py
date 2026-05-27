"""Shared helpers used across tool modules."""
from __future__ import annotations

from ..config import Settings


class DestructiveOpBlocked(RuntimeError):
    pass


def ensure_destructive_allowed(settings: Settings, op: str, confirm: bool) -> None:
    """Two-gate check: server-level master switch + per-call confirm arg."""
    if not settings.allow_destructive:
        raise DestructiveOpBlocked(
            f"Destructive op '{op}' refused: allow_destructive=false on server. "
            f"Edit /etc/proxmox-mcp/proxmox-mcp.env and restart the service."
        )
    if not confirm:
        raise DestructiveOpBlocked(
            f"Destructive op '{op}' refused: caller did not pass confirm=true. "
            f"Re-invoke explicitly acknowledging destruction."
        )

"""Proxmox API client wrapper with task-waiting and structured errors."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import structlog
from proxmoxer import ProxmoxAPI, ResourceException

from .config import Settings

log = structlog.get_logger(__name__)


class ProxmoxError(RuntimeError):
    """Raised for any non-recoverable PVE API error, with HTTP status preserved."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


@dataclass
class TaskResult:
    upid: str
    status: str  # "OK" | "stopped" | "running" | etc.
    exitstatus: str | None
    log_tail: list[str]

    @property
    def ok(self) -> bool:
        return self.status == "stopped" and (self.exitstatus or "").upper() == "OK"


class PVEClient:
    """Wrapper around proxmoxer that surfaces the API as a typed surface."""

    def __init__(self, settings: Settings):
        self.settings = settings
        token_user = settings.pve_user
        self._api = ProxmoxAPI(
            host=settings.pve_host,
            port=settings.pve_port,
            user=token_user,
            token_name=settings.pve_token_name,
            token_value=settings.pve_token_value,
            verify_ssl=settings.pve_verify_ssl,
            timeout=30,
        )

    @property
    def api(self) -> ProxmoxAPI:
        """Raw proxmoxer handle; tool modules use this directly for terse code."""
        return self._api

    # ---- task helpers -------------------------------------------------

    def wait_task(self, node: str, upid: str, timeout: int | None = None) -> TaskResult:
        """Poll a PVE task to completion. PVE returns a UPID for async ops; we hide that here."""
        deadline = time.monotonic() + (timeout or self.settings.task_wait_timeout)
        last_status: dict[str, Any] = {}
        while time.monotonic() < deadline:
            try:
                last_status = self._api.nodes(node).tasks(upid).status.get()
            except ResourceException as exc:
                raise ProxmoxError(f"Task status fetch failed: {exc}", getattr(exc, "status_code", None)) from exc
            if last_status.get("status") == "stopped":
                break
            time.sleep(1.0)
        else:
            raise ProxmoxError(f"Timed out waiting for task {upid}")

        try:
            log_entries = self._api.nodes(node).tasks(upid).log.get()
            tail = [entry.get("t", "") for entry in log_entries[-50:]]
        except ResourceException:
            tail = []

        return TaskResult(
            upid=upid,
            status=last_status.get("status", "unknown"),
            exitstatus=last_status.get("exitstatus"),
            log_tail=tail,
        )

    def run_and_wait(self, node: str, upid: str) -> TaskResult:
        """Convenience: wait, raise if not OK."""
        result = self.wait_task(node, upid)
        if not result.ok:
            raise ProxmoxError(
                f"Task {upid} ended {result.status}/{result.exitstatus}. "
                f"Last log: {result.log_tail[-5:] if result.log_tail else 'n/a'}"
            )
        return result

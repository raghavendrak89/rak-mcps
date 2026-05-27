"""proxmox-mcp server entrypoint."""
from __future__ import annotations

import logging
import sys

import structlog
from mcp.server.fastmcp import FastMCP

from .config import load_settings
from .pve_client import PVEClient
from .tools import (
    backups,
    cluster,
    firewall,
    lxc,
    network,
    nodes,
    snapshots,
    storage,
    tasks,
    users,
    vms,
)


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, level.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
    )


def build_server() -> FastMCP:
    settings = load_settings()
    _configure_logging(settings.log_level)
    log = structlog.get_logger("proxmox_mcp")
    log.info(
        "starting",
        host=settings.pve_host,
        bind=f"{settings.bind_host}:{settings.bind_port}",
        transport=settings.transport,
        allow_destructive=settings.allow_destructive,
    )

    mcp = FastMCP(
        "proxmox-mcp",
        host=settings.bind_host,
        port=settings.bind_port,
    )
    client = PVEClient(settings)

    cluster.register(mcp, client)
    nodes.register(mcp, client, settings)
    vms.register(mcp, client, settings)
    lxc.register(mcp, client, settings)
    snapshots.register(mcp, client, settings)
    backups.register(mcp, client, settings)
    storage.register(mcp, client, settings)
    network.register(mcp, client, settings)
    firewall.register(mcp, client, settings)
    users.register(mcp, client, settings)
    tasks.register(mcp, client, settings)

    return mcp


def main() -> None:
    mcp = build_server()
    settings = load_settings()
    if settings.transport == "stdio":
        mcp.run("stdio")
    elif settings.transport == "sse":
        mcp.run("sse")
    else:
        mcp.run("streamable-http")


if __name__ == "__main__":
    main()

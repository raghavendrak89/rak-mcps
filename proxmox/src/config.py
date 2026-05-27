"""Configuration loaded from environment variables or systemd EnvironmentFile."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PROXMOX_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Proxmox API connection
    pve_host: str = Field(..., description="Proxmox host or VIP, e.g. pve1.lan")
    pve_port: int = 8006
    pve_user: str = Field("mcp@pve", description="API user, format user@realm")
    pve_token_name: str = Field(..., description="API token ID")
    pve_token_value: str = Field(..., description="API token secret UUID")
    pve_verify_ssl: bool = Field(
        True,
        description="Verify TLS. Set false ONLY for self-signed PVE certs you trust.",
    )

    # MCP server transport
    bind_host: str = Field(
        "127.0.0.1",
        description="Bind interface. Use Tailscale IP (100.x.y.z) for tailnet-only access.",
    )
    bind_port: int = 8080
    transport: str = Field("streamable-http", description="stdio | streamable-http | sse")

    # Behavior
    allow_destructive: bool = Field(
        True,
        description="Master switch for destructive ops. Set false to disable wipe/delete tools entirely.",
    )
    task_wait_timeout: int = Field(300, description="Seconds to wait for PVE tasks to finish")
    log_level: str = "INFO"


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

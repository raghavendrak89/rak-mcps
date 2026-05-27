"""User, group, ACL, and API token administration."""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from ..pve_client import PVEClient
from ._safety import ensure_destructive_allowed


def register(mcp: FastMCP, client: PVEClient, settings: Settings) -> None:
    @mcp.tool()
    def access_users() -> list[dict[str, Any]]:
        return client.api.access.users.get()

    @mcp.tool()
    def access_groups() -> list[dict[str, Any]]:
        return client.api.access.groups.get()

    @mcp.tool()
    def access_roles() -> list[dict[str, Any]]:
        return client.api.access.roles.get()

    @mcp.tool()
    def access_acl() -> list[dict[str, Any]]:
        return client.api.access.acl.get()

    @mcp.tool()
    def access_acl_set(
        path: str,
        roles: str,
        users: str | None = None,
        groups: str | None = None,
        propagate: bool = True,
    ) -> dict[str, Any]:
        """Set an ACL entry. roles is comma-separated PVE role names."""
        params: dict[str, Any] = {"path": path, "roles": roles, "propagate": 1 if propagate else 0}
        if users:
            params["users"] = users
        if groups:
            params["groups"] = groups
        return {"result": client.api.access.acl.put(**params)}

    @mcp.tool()
    def access_acl_remove(path: str, roles: str, users: str | None = None, groups: str | None = None, confirm: bool = False) -> dict[str, Any]:
        """Remove an ACL entry. DESTRUCTIVE: may lock principals out of resources."""
        ensure_destructive_allowed(settings, "access_acl_remove", confirm)
        params: dict[str, Any] = {"path": path, "roles": roles, "delete": 1}
        if users:
            params["users"] = users
        if groups:
            params["groups"] = groups
        return {"result": client.api.access.acl.put(**params)}

    @mcp.tool()
    def access_token_list(userid: str) -> list[dict[str, Any]]:
        return client.api.access.users(userid).token.get()

    @mcp.tool()
    def access_token_create(userid: str, tokenid: str, privsep: bool = True, expire: int = 0) -> dict[str, Any]:
        """Create an API token. Returns the secret value ONCE - capture it.

        privsep=true means the token is limited to its own ACL subset (recommended).
        """
        return client.api.access.users(userid).token(tokenid).post(privsep=1 if privsep else 0, expire=expire)

    @mcp.tool()
    def access_token_delete(userid: str, tokenid: str, confirm: bool = False) -> dict[str, Any]:
        """Revoke an API token. DESTRUCTIVE: any caller using it stops working."""
        ensure_destructive_allowed(settings, "access_token_delete", confirm)
        return {"result": client.api.access.users(userid).token(tokenid).delete()}

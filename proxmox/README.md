# proxmox-mcp

An MCP server exposing your Proxmox VE cluster to Claude. Designed to run as a service on a small Debian VM inside the cluster, reachable from your Mac over Tailscale.

## Architecture

```
┌──────────────┐   Tailscale    ┌─────────────────────────┐    HTTPS    ┌──────────────┐
│  Mac         │  (WireGuard)   │  Debian VM on Proxmox   │   :8006     │ Proxmox API  │
│ Claude       │ ─────────────► │  proxmox-mcp.service    │ ──────────► │  (cluster)   │
│ Desktop      │  100.x.y.z     │  FastMCP streamable HTTP│  token auth │              │
└──────────────┘   :8080        └─────────────────────────┘             └──────────────┘
```

- **Why a VM inside the cluster, not on PVE itself**: keeps the management plane off the hypervisors, lets you snapshot/back up the MCP host like any other workload, and lets you blow it away without touching PVE.
- **Why Tailscale**: zero public exposure, identity-based ACLs, survives network changes, MagicDNS makes the config readable.
- **Why an API token, not username/password**: revocable independently of the user, no TOTP friction, scoped via PVE ACLs.

## Tool surface

~50 tools grouped by resource:

| Module | Tools |
|--------|-------|
| `cluster` | status, resources, next_vmid, log, ha_status, tasks |
| `nodes` | list, status, rrd_data, services, service_action, reboot, shutdown, wakeonlan |
| `vms` | list, get, create, clone, migrate, start/shutdown/stop/reboot/reset/suspend/resume, config_set, resize_disk, template_convert, delete, agent_exec, rrd_data |
| `lxc` | list, get, create, clone, migrate, start/shutdown/stop/reboot, config_set, resize, delete |
| `snapshots` | list, create, rollback, delete (VM + LXC) |
| `backups` | list, create, delete, jobs_list, job_create, job_delete, restore_vm, restore_lxc |
| `storage` | list, status, content, volume_delete, download_url, disks_list, disk_wipe, storage_remove |
| `network` | interfaces, apply, revert, sdn_zones, sdn_vnets, sdn_apply |
| `firewall` | rules_list, rule_add, rule_delete, options_get, options_set (cluster/node/vm/lxc scope) |
| `users` | users, groups, roles, acl, acl_set, acl_remove, token_list, token_create, token_delete |
| `tasks` | list, status, log, wait, stop |

### Destructive op safety

Every destructive tool (delete, wipe, force-stop, force-restore, hard-reset, ACL removal, etc.) requires **two** gates:

1. `PROXMOX_MCP_ALLOW_DESTRUCTIVE=true` on the server (master switch)
2. `confirm=true` argument on the individual call

If either is missing, the tool raises `DestructiveOpBlocked` and the API is not called.

## Setup

1. [docs/01-proxmox-setup.md](docs/01-proxmox-setup.md) — PVE user, role, token
2. [docs/02-tailscale-setup.md](docs/02-tailscale-setup.md) — Tailscale on the VM
3. Run `sudo deploy/install.sh` on the VM
4. Edit `/etc/proxmox-mcp/proxmox-mcp.env` (token, bind IP)
5. `systemctl start proxmox-mcp`
6. [docs/03-claude-desktop.md](docs/03-claude-desktop.md) — Claude Desktop config

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
# Run locally with PROXMOX_MCP_TRANSPORT=stdio and a .env file:
proxmox-mcp
```

## License

MIT

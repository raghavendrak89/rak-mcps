# Tailscale setup

The MCP server binds to the VM's Tailscale interface. Only your Mac (also on the tailnet) can reach it. Nothing is exposed on LAN or the public internet.

## 1. Install Tailscale on the management VM

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh --hostname proxmox-mcp
```

Open the printed URL on your Mac to authenticate. `--ssh` is optional but handy for management.

## 2. Get the VM's tailnet IP

```bash
tailscale ip -4
# e.g. 100.101.102.103
```

Put that in `/etc/proxmox-mcp/proxmox-mcp.env` as `PROXMOX_MCP_BIND_HOST`.

## 3. Lock it down with an ACL (recommended)

In the Tailscale admin → Access Controls, restrict who can hit the MCP port. Example:

```hujson
{
  "tagOwners": {
    "tag:proxmox-mcp": ["your-email@example.com"],
    "tag:admin":       ["your-email@example.com"],
  },
  "acls": [
    // Only your admin device(s) can reach the MCP port
    {
      "action": "accept",
      "src":    ["tag:admin"],
      "dst":    ["tag:proxmox-mcp:8080"],
    },
  ],
}
```

Then tag the VM:

```bash
sudo tailscale up --advertise-tags=tag:proxmox-mcp
```

And tag your Mac (also via `tailscale up --advertise-tags=tag:admin`, or assign in admin console).

## 4. From the Mac, verify reachability

```bash
nc -vz proxmox-mcp 8080
```

Should connect once the service is running.

# Claude Desktop (Mac) configuration

Claude Desktop talks to the remote MCP server over HTTP via the bundled `mcp-remote` shim.

## 1. Install the shim

```bash
npm install -g mcp-remote
```

(Requires Node.js. Or use `npx mcp-remote` in the config below to skip a global install.)

## 2. Edit Claude Desktop config

Open `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://proxmox-mcp:8080/mcp",
        "--transport",
        "http-only"
      ]
    }
  }
}
```

Notes:
- `proxmox-mcp` is the Tailscale MagicDNS name of the VM. If MagicDNS is off, use the `100.x.y.z` IP.
- Path is `/mcp` for streamable-http (FastMCP default).
- Restart Claude Desktop fully (Cmd-Q, not just close window) after editing.

## 3. Verify

In a new chat, ask Claude: *"What Proxmox tools do you have available?"* — it should list the `cluster_*`, `node_*`, `vm_*`, etc. tools.

Try a read-only smoke test first: *"Show me the cluster status."*

## Destructive op flow

Every destructive tool requires `confirm=true`. In practice the conversation goes:

> You: delete VM 105 on pve2  
> Claude: That will permanently destroy VM 105 and its disks. Confirm? *(does not call the tool yet)*  
> You: yes  
> Claude: *calls `vm_delete(node="pve2", vmid=105, confirm=true)`*

You can also harden the server side: set `PROXMOX_MCP_ALLOW_DESTRUCTIVE=false` to disable the entire class of ops regardless of what Claude tries.

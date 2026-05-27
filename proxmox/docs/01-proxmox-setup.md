# Proxmox setup

Run these on any cluster node (config replicates across the cluster).

## 1. Create a dedicated user

```bash
pveum user add mcp@pve --comment "MCP server identity"
```

## 2. Create a custom role

For "everything including destructive" scope. Trim privileges later if you want to clamp down.

```bash
pveum role add MCPAdmin -privs "\
VM.Allocate,VM.Audit,VM.Clone,VM.Config.CDROM,VM.Config.CPU,VM.Config.Cloudinit,VM.Config.Disk,VM.Config.HWType,VM.Config.Memory,VM.Config.Network,VM.Config.Options,VM.Console,VM.Migrate,VM.Monitor,VM.PowerMgmt,VM.Snapshot,VM.Snapshot.Rollback,VM.Backup,\
Datastore.Allocate,Datastore.AllocateSpace,Datastore.AllocateTemplate,Datastore.Audit,\
Pool.Allocate,Pool.Audit,\
Sys.Audit,Sys.Console,Sys.Modify,Sys.PowerMgmt,Sys.Syslog,\
SDN.Allocate,SDN.Audit,SDN.Use,\
User.Modify,Group.Allocate,Realm.Allocate,Realm.AllocateUser,Permissions.Modify,\
Mapping.Audit,Mapping.Modify,Mapping.Use"
```

(If you want simpler: assign the built-in `Administrator` role instead, which has all privileges. The custom role above just makes the privilege surface explicit.)

## 3. Grant the role at root path

```bash
pveum acl modify / -user mcp@pve -role MCPAdmin
```

## 4. Create an API token

`privsep=0` means the token inherits the user's full ACL. If you set `privsep=1`, you must also `pveum acl modify` for the token id specifically.

```bash
pveum user token add mcp@pve mcp --privsep 0
```

Capture the printed `value` — it appears **only once**. That UUID goes into `PROXMOX_MCP_PVE_TOKEN_VALUE`.

## 5. Smoke test from the management VM

```bash
curl -k -H "Authorization: PVEAPIToken=mcp@pve!mcp=YOUR-UUID" \
  https://pve1.lan:8006/api2/json/cluster/status | jq
```

If you get JSON back with your nodes, you're good.

## Notes on TLS

If your PVE certs are self-signed, you have two options:

1. Install a real cert via the PVE web UI (Datacenter → ACME). Keep `PROXMOX_MCP_PVE_VERIFY_SSL=true`.
2. Set `PROXMOX_MCP_PVE_VERIFY_SSL=false`. Acceptable if the MCP VM and PVE are on the same trusted L2 segment; not acceptable if traffic crosses untrusted networks.

Option 1 is the right answer for a permanent setup.

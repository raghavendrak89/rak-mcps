#!/usr/bin/env bash
# Install proxmox-mcp on a Debian/Ubuntu VM. Run as root.
set -euo pipefail

INSTALL_DIR=/opt/proxmox-mcp
ETC_DIR=/etc/proxmox-mcp
USER=proxmox-mcp
REPO_DIR="${REPO_DIR:-$(pwd)}"

if [[ "$EUID" -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

echo "[1/6] apt deps"
apt-get update
apt-get install -y python3 python3-venv python3-pip ca-certificates

echo "[2/6] system user"
if ! id "$USER" &>/dev/null; then
  useradd --system --home "$INSTALL_DIR" --shell /usr/sbin/nologin "$USER"
fi

echo "[3/6] sync code into $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
rsync -a --delete \
  --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
  "$REPO_DIR/" "$INSTALL_DIR/"
chown -R "$USER:$USER" "$INSTALL_DIR"

echo "[4/6] venv + install"
sudo -u "$USER" python3 -m venv "$INSTALL_DIR/.venv"
sudo -u "$USER" "$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
sudo -u "$USER" "$INSTALL_DIR/.venv/bin/pip" install -e "$INSTALL_DIR"

echo "[5/6] config"
mkdir -p "$ETC_DIR"
if [[ ! -f "$ETC_DIR/proxmox-mcp.env" ]]; then
  cp "$REPO_DIR/deploy/proxmox-mcp.env.example" "$ETC_DIR/proxmox-mcp.env"
  echo "  -> edit $ETC_DIR/proxmox-mcp.env with your PVE token + Tailscale IP, then re-run."
fi
chown -R "$USER:$USER" "$ETC_DIR"
chmod 600 "$ETC_DIR/proxmox-mcp.env"

echo "[6/6] systemd"
cp "$REPO_DIR/deploy/proxmox-mcp.service" /etc/systemd/system/proxmox-mcp.service
systemctl daemon-reload
systemctl enable proxmox-mcp.service
echo "Done. Start with: systemctl start proxmox-mcp && journalctl -u proxmox-mcp -f"

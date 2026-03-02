#!/bin/bash
# Syncthing setup — alternative to Git sync for real-time file sync
#
# Usage: bash deploy/sync/syncthing-setup.sh
#
# After setup, pair your local machine with the Cloud VM using the device ID printed below.

set -euo pipefail

echo "=== Syncthing Setup for Vault Sync ==="

# Install Syncthing
echo "[1/4] Installing Syncthing..."
sudo apt install -y apt-transport-https
curl -L -o /usr/share/keyrings/syncthing-archive-keyring.gpg https://syncthing.net/release-key.gpg
echo "deb [signed-by=/usr/share/keyrings/syncthing-archive-keyring.gpg] https://apt.syncthing.net/ syncthing stable" | sudo tee /etc/apt/sources.list.d/syncthing.list
sudo apt update
sudo apt install -y syncthing

# Configure as systemd service
echo "[2/4] Configuring systemd service..."
sudo systemctl enable syncthing@ai-employee
sudo systemctl start syncthing@ai-employee

# Wait for config generation
sleep 3

# Apply .stignore
echo "[3/4] Applying sync exclusions..."
VAULT_DIR="${VAULT_PATH:-/home/ai-employee/vault}"
if [ -f "$VAULT_DIR/.syncignore" ]; then
    cp "$VAULT_DIR/.syncignore" "$VAULT_DIR/.stignore"
    echo "  Copied .syncignore to .stignore"
fi

# Print device ID for pairing
echo "[4/4] Device ID for pairing:"
echo ""
syncthing -device-id 2>/dev/null || echo "  (Start Syncthing first, then run: syncthing -device-id)"
echo ""
echo "=== Setup complete ==="
echo "Add vault folder in Syncthing web UI: http://localhost:8384"
echo "Share with your local machine using the device ID above."

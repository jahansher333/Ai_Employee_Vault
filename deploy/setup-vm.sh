#!/bin/bash
# Oracle Cloud Free Tier VM Setup for AI Employee
# Target: Ubuntu 22.04 ARM (Ampere A1)
#
# This script provisions the VM with all dependencies for the
# Platinum Tier AI Employee (Cloud zone).
#
# Usage: ssh ubuntu@<vm-ip> 'bash -s' < deploy/setup-vm.sh

set -euo pipefail

echo "============================================"
echo "  AI Employee — Cloud VM Setup"
echo "  Target: Oracle Cloud Free Tier (ARM)"
echo "============================================"

# --- System updates ---
echo "[1/10] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# --- Python 3.11 ---
echo "[2/10] Installing Python 3.11..."
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# --- Docker ---
echo "[3/10] Installing Docker..."
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# --- Other dependencies ---
echo "[4/10] Installing Git, nginx, certbot..."
sudo apt install -y git nginx certbot python3-certbot-nginx

# --- Create ai-employee user ---
echo "[5/10] Creating ai-employee user..."
sudo useradd -m -s /bin/bash ai-employee || true
sudo usermod -aG docker ai-employee

# --- Clone vault repository ---
echo "[6/10] Setting up vault..."
VAULT_DIR="/home/ai-employee/vault"
if [ ! -d "$VAULT_DIR" ]; then
    sudo -u ai-employee git clone "${REPO_URL:-https://github.com/user/vault.git}" "$VAULT_DIR" || true
fi

# --- Python dependencies ---
echo "[7/10] Installing Python requirements..."
if [ -f "$VAULT_DIR/requirements.txt" ]; then
    sudo -u ai-employee python3.11 -m pip install -r "$VAULT_DIR/requirements.txt" --user
fi

# --- Swap file (safety valve for memory) ---
echo "[8/10] Adding 2 GB swap..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

# --- Firewall ---
echo "[9/10] Configuring firewall..."
sudo iptables -I INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
# Save rules (Ubuntu)
sudo apt install -y iptables-persistent || true
sudo netfilter-persistent save || true

# --- Systemd services ---
echo "[10/10] Installing systemd services..."
if [ -f "$VAULT_DIR/deploy/systemd/ai-employee.service" ]; then
    sudo cp "$VAULT_DIR/deploy/systemd/ai-employee.service" /etc/systemd/system/
    sudo cp "$VAULT_DIR/deploy/systemd/vault-sync.service" /etc/systemd/system/ 2>/dev/null || true
    sudo cp "$VAULT_DIR/deploy/systemd/vault-sync.timer" /etc/systemd/system/ 2>/dev/null || true
    sudo systemctl daemon-reload
    sudo systemctl enable ai-employee
    sudo systemctl enable vault-sync.timer 2>/dev/null || true
fi

echo ""
echo "============================================"
echo "  Setup complete!"
echo ""
echo "  Next steps:"
echo "  1. Copy .env: cp deploy/.env.cloud.example .env"
echo "  2. Edit .env with your credentials"
echo "  3. Start Odoo: cd deploy && docker compose up -d"
echo "  4. Get SSL cert: sudo certbot --nginx -d your-domain.com"
echo "  5. Start services: sudo systemctl start ai-employee"
echo "  6. Start sync: sudo systemctl start vault-sync.timer"
echo "============================================"

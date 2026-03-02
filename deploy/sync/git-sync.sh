#!/bin/bash
# Git sync wrapper for cron/systemd
# Sources .env for VAULT_PATH and runs vault_sync.py --once

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VAULT_DIR="${VAULT_PATH:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

# Source env if available
if [ -f "$VAULT_DIR/.env" ]; then
    set -a
    source "$VAULT_DIR/.env"
    set +a
fi

cd "$VAULT_DIR"

# Run sync
python3.11 scripts/vault_sync.py --once --vault-path "$VAULT_DIR" >> Logs/vault_sync.log 2>&1

exit $?

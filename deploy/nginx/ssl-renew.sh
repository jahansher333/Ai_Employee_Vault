#!/bin/bash
# SSL certificate renewal helper — runs via cron twice daily
# Usage: Add to crontab: 0 */12 * * * /home/ai-employee/vault/deploy/nginx/ssl-renew.sh

set -euo pipefail

LOG="/var/log/certbot-renew.log"

echo "[$(date)] Starting certificate renewal check" >> "$LOG"
certbot renew --quiet --deploy-hook "systemctl reload nginx" >> "$LOG" 2>&1
echo "[$(date)] Renewal check complete" >> "$LOG"

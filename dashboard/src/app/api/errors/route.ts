import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { vaultPath } from "@/lib/vault";

export const dynamic = "force-dynamic";

// Load vault .env into a lookup map (vault root, not dashboard)
function loadVaultEnv(): Record<string, string> {
  const envMap: Record<string, string> = {};
  const envFile = vaultPath(".env");
  if (!fs.existsSync(envFile)) return envMap;
  const content = fs.readFileSync(envFile, "utf-8");
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eqIdx = trimmed.indexOf("=");
    if (eqIdx > 0) {
      const key = trimmed.slice(0, eqIdx).trim();
      const val = trimmed.slice(eqIdx + 1).trim().replace(/^['"]|['"]$/g, "");
      if (val) envMap[key] = val;
    }
  }
  return envMap;
}

function hasKey(env: Record<string, string>, keys: string[]): boolean {
  return keys.some((k) => !!env[k] || !!process.env[k]);
}

function checkFileExists(filePath: string): boolean {
  return fs.existsSync(filePath);
}

type ServiceStatus = "operational" | "degraded" | "unavailable" | "not_configured";

function detectServiceHealth(): Record<string, ServiceStatus> {
  const health: Record<string, ServiceStatus> = {};
  const env = loadVaultEnv();

  // Gmail - check credentials.json and token.json
  const vaultRoot = vaultPath("");
  const hasGmailCreds = checkFileExists(path.join(vaultRoot, "credentials.json")) ||
    hasKey(env, ["GMAIL_CREDENTIALS", "GOOGLE_APPLICATION_CREDENTIALS"]);
  const hasGmailToken = checkFileExists(path.join(vaultRoot, "token.json"));
  if (hasGmailCreds && hasGmailToken) {
    health.gmail = "operational";
  } else if (hasGmailCreds) {
    health.gmail = "degraded";
  } else {
    health.gmail = "not_configured";
  }

  // WhatsApp - check session or env
  if (hasKey(env, ["WHATSAPP_SESSION_DIR"])) {
    health.whatsapp = "operational";
  } else {
    health.whatsapp = "not_configured";
  }

  // Telegram - check bot token
  if (hasKey(env, ["TELEGRAM_BOT_TOKEN"])) {
    health.telegram = "operational";
  } else {
    health.telegram = "not_configured";
  }

  // Odoo - check connection env vars from vault .env
  if (hasKey(env, ["ODOO_URL"])) {
    if (hasKey(env, ["ODOO_DB"]) && hasKey(env, ["ODOO_USER"]) && hasKey(env, ["ODOO_PASSWORD"])) {
      health.odoo = "operational";
    } else {
      health.odoo = "degraded";
    }
  } else {
    health.odoo = "not_configured";
  }

  // Facebook - check API tokens OR session
  if (hasKey(env, ["FACEBOOK_PAGE_ACCESS_TOKEN", "FACEBOOK_ACCESS_TOKEN"])) {
    health.facebook = "operational";
  } else {
    health.facebook = "not_configured";
  }

  // Instagram - check API tokens OR session
  if (hasKey(env, ["INSTAGRAM_ACCESS_TOKEN"])) {
    health.instagram = "operational";
  } else {
    health.instagram = "not_configured";
  }

  // Twitter - check API keys
  if (hasKey(env, ["TWITTER_BEARER_TOKEN", "TWITTER_API_KEY"])) {
    health.twitter = "operational";
  } else {
    health.twitter = "not_configured";
  }

  // LinkedIn - check API tokens
  if (hasKey(env, ["LINKEDIN_ACCESS_TOKEN"])) {
    health.linkedin = "operational";
  } else {
    health.linkedin = "not_configured";
  }

  // Slack - check webhook
  if (hasKey(env, ["SLACK_WEBHOOK_URL"])) {
    health.slack = "operational";
  } else {
    health.slack = "not_configured";
  }

  return health;
}

export function GET() {
  const errors: object[] = [];
  const logDir = vaultPath("Logs");

  if (fs.existsSync(logDir)) {
    const logFiles = fs
      .readdirSync(logDir)
      .filter((f) => f.endsWith(".audit.jsonl"))
      .sort()
      .reverse()
      .slice(0, 3);

    for (const logFile of logFiles) {
      try {
        const content = fs.readFileSync(path.join(logDir, logFile), "utf-8");
        const lines = content.trim().split("\n").slice(-100);
        for (const line of lines.reverse()) {
          try {
            const entry = JSON.parse(line);
            if (["error", "failure", "failed"].includes(entry.outcome)) {
              errors.push(entry);
            }
          } catch {
            // skip malformed lines
          }
        }
      } catch {
        // skip unreadable files
      }
    }
  }

  const serviceHealth = detectServiceHealth();

  return NextResponse.json({
    recent_errors: errors.slice(0, 20),
    error_count: errors.length,
    service_health: serviceHealth,
  });
}

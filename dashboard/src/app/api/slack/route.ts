import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { exec } from "child_process";
import { vaultPath, appendAuditLog } from "@/lib/vault";

export const dynamic = "force-dynamic";

function getEnvValue(key: string): string {
  const envPath = vaultPath(".env");
  if (!fs.existsSync(envPath)) return "";
  const content = fs.readFileSync(envPath, "utf-8");
  const match = content.match(new RegExp(`^${key}=(.*)$`, "m"));
  return match ? match[1].trim() : "";
}

function setEnvValue(key: string, value: string): void {
  const envPath = vaultPath(".env");
  if (!fs.existsSync(envPath)) return;
  let content = fs.readFileSync(envPath, "utf-8");
  const regex = new RegExp(`^${key}=.*$`, "m");
  if (regex.test(content)) {
    content = content.replace(regex, `${key}=${value}`);
  } else {
    content += `\n${key}=${value}\n`;
  }
  fs.writeFileSync(envPath, content, "utf-8");
}

export function GET() {
  const webhookUrl = getEnvValue("SLACK_WEBHOOK_URL");
  const channel = getEnvValue("SLACK_CHANNEL") || "(default)";
  const webhookConfigured = !!webhookUrl && webhookUrl.startsWith("https://hooks.slack.com/");

  // Get recent slack notifications from audit logs
  const recentNotifications: object[] = [];
  const logsDir = vaultPath("Logs");
  if (fs.existsSync(logsDir)) {
    const logFiles = fs.readdirSync(logsDir)
      .filter((f) => f.endsWith(".audit.jsonl"))
      .sort()
      .reverse()
      .slice(0, 5);

    for (const logFile of logFiles) {
      const content = fs.readFileSync(path.join(logsDir, logFile), "utf-8");
      const lines = content.trim().split("\n").filter(Boolean);
      for (const line of lines) {
        try {
          const entry = JSON.parse(line);
          if (entry.action && entry.action.includes("slack")) {
            recentNotifications.push(entry);
          }
        } catch { /* skip */ }
      }
    }
  }

  const notificationTypes = [
    { type: "task_complete", label: "Task Completed", color: "#36a64f", description: "When a task moves to Done/" },
    { type: "approval_needed", label: "Approval Needed", color: "#ff9900", description: "When an item needs human review" },
    { type: "briefing_ready", label: "CEO Briefing Ready", color: "#0066cc", description: "When weekly briefing is generated" },
    { type: "low_stock", label: "Low Stock Alert", color: "#ff0000", description: "When products are low on stock" },
    { type: "overdue_invoices", label: "Overdue Invoices", color: "#ff0000", description: "When overdue invoices are detected" },
    { type: "status_summary", label: "Status Summary", color: "#0066cc", description: "Vault status overview" },
  ];

  return NextResponse.json({
    configured: webhookConfigured,
    webhook_preview: webhookConfigured ? `...${webhookUrl.slice(-20)}` : "",
    channel,
    mode: webhookConfigured ? "live" : "simulation",
    notification_types: notificationTypes,
    recent_notifications: recentNotifications.slice(-15).reverse(),
  });
}

export async function POST(request: Request) {
  try {
    const { action, webhook_url, channel, message } = await request.json();

    // Save webhook URL
    if (action === "save_config") {
      if (webhook_url !== undefined) {
        setEnvValue("SLACK_WEBHOOK_URL", webhook_url);
      }
      if (channel !== undefined) {
        setEnvValue("SLACK_CHANNEL", channel);
      }
      appendAuditLog("slack_config_updated", "dashboard", "config", "success");
      return NextResponse.json({ success: true, message: "Slack config saved to .env" });
    }

    // Send test notification
    if (action === "test") {
      const testMsg = message || "Hello from AI Employee Dashboard!";
      const scriptsDir = path.resolve(vaultPath("scripts"));
      const cmd = `python "${path.join(scriptsDir, "slack_notifier.py")}" --test "${testMsg.replace(/"/g, '\\"')}"`;

      const result = await new Promise<{ success: boolean; output: string; error: string }>((resolve) => {
        exec(cmd, { cwd: vaultPath(""), timeout: 15000 }, (error, stdout, stderr) => {
          resolve({
            success: !error,
            output: stdout?.trim() || "",
            error: error ? stderr?.trim() || error.message : "",
          });
        });
      });
      return NextResponse.json(result);
    }

    // Send summary
    if (action === "summary") {
      const scriptsDir = path.resolve(vaultPath("scripts"));
      const cmd = `python "${path.join(scriptsDir, "slack_notifier.py")}" --summary`;

      const result = await new Promise<{ success: boolean; output: string; error: string }>((resolve) => {
        exec(cmd, { cwd: vaultPath(""), timeout: 15000 }, (error, stdout, stderr) => {
          resolve({
            success: !error,
            output: stdout?.trim() || "",
            error: error ? stderr?.trim() || error.message : "",
          });
        });
      });
      return NextResponse.json(result);
    }

    return NextResponse.json({ success: false, error: "Unknown action" }, { status: 400 });
  } catch (err) {
    return NextResponse.json({ success: false, error: String(err) }, { status: 500 });
  }
}

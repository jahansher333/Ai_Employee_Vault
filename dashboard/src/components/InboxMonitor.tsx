"use client";

import { useEffect, useState } from "react";

interface WatcherStatus {
  name: string;
  icon: string;
  color: string;
  configured: boolean;
  configKey: string;
  description: string;
  command: string;
  features: string[];
}

export default function InboxMonitor() {
  const [health, setHealth] = useState<Record<string, string>>({});

  useEffect(() => {
    fetch("/api/errors")
      .then((r) => r.json())
      .then((d) => setHealth(d.service_health || {}))
      .catch(() => {});
  }, []);

  const watchers: WatcherStatus[] = [
    {
      name: "Gmail Watcher",
      icon: "\u2709",
      color: "#ea4335",
      configured: !!process.env.NEXT_PUBLIC_GMAIL_CONFIGURED,
      configKey: "GMAIL_CREDENTIALS",
      description: "Polls Gmail inbox for new emails, creates task files, supports auto-reply",
      command: "python scripts/gmail_watcher.py",
      features: [
        "OAuth2 authentication with token refresh",
        "Polls inbox for unread emails",
        "Creates task files in Needs_Action/",
        "Deduplication via ledger",
        "Marks processed emails as read",
      ],
    },
    {
      name: "WhatsApp Watcher",
      icon: "\uD83D\uDCAC",
      color: "#25d366",
      configured: false,
      configKey: "WHATSAPP_SESSION_DIR",
      description: "Monitors WhatsApp Web for priority messages using Playwright",
      command: "python scripts/whatsapp_watcher.py",
      features: [
        "Playwright browser automation",
        "Priority keyword detection (urgent, invoice, payment, help)",
        "SHA-256 message deduplication",
        "Creates task files from priority messages",
        "Persistent session login",
      ],
    },
    {
      name: "Telegram Bot",
      icon: "\u2708",
      color: "#0088cc",
      configured: false,
      configKey: "TELEGRAM_BOT_TOKEN",
      description: "Telegram Bot API polling for incoming messages",
      command: "python scripts/telegram_watcher.py",
      features: [
        "Bot API getUpdates polling",
        "Priority keyword detection",
        "Creates task files in Needs_Action/",
        "Message deduplication",
        "Configurable poll interval",
      ],
    },
  ];

  const statusColor: Record<string, string> = {
    operational: "var(--green)",
    degraded: "var(--yellow)",
    unavailable: "var(--red)",
  };

  return (
    <>
      {/* Watcher Cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16, marginBottom: 24 }}>
        {watchers.map((w) => {
          const serviceStatus = health[w.name.toLowerCase().split(" ")[0]] || "unknown";
          return (
            <div
              key={w.name}
              className="section"
              style={{ borderLeft: `4px solid ${w.color}` }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <h2 style={{ margin: 0 }}>
                  <span className="section-icon">{w.icon}</span> {w.name}
                </h2>
                <span
                  className="badge"
                  style={{
                    background: serviceStatus === "operational" ? "var(--green-dim)" : "var(--yellow-dim)",
                    color: statusColor[serviceStatus] || "var(--muted)",
                  }}
                >
                  {serviceStatus === "operational" ? "Running" : serviceStatus === "unknown" ? "Not Started" : serviceStatus}
                </span>
              </div>

              <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 12 }}>{w.description}</p>

              {/* Features */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4, marginBottom: 12 }}>
                {w.features.map((f, i) => (
                  <div key={i} style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6, padding: "4px 0" }}>
                    <span style={{ color: "var(--green)", fontSize: 11 }}>{"\u2713"}</span> {f}
                  </div>
                ))}
              </div>

              {/* Command */}
              <div style={{
                background: "var(--bg)", border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)", padding: 10, fontSize: 12,
              }}>
                <span style={{ color: "var(--muted)" }}>Start: </span>
                <code>{w.command}</code>
                <span style={{ color: "var(--muted)", marginLeft: 12 }}>Config: </span>
                <code style={{ color: "var(--yellow)" }}>{w.configKey}</code>
              </div>
            </div>
          );
        })}
      </div>

      {/* Overall Status */}
      <div className="section">
        <h2><span className="section-icon">{"\uD83D\uDCE5"}</span> How Inbox Processing Works</h2>
        <div style={{
          display: "flex", flexDirection: "column", gap: 8, fontSize: 13, color: "var(--muted)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span className="badge badge-info" style={{ minWidth: 24, textAlign: "center" }}>1</span>
            <span>Watchers poll external channels (Gmail, WhatsApp, Telegram) for new messages</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span className="badge badge-info" style={{ minWidth: 24, textAlign: "center" }}>2</span>
            <span>Priority messages create task files in <code>Needs_Action/</code></span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span className="badge badge-info" style={{ minWidth: 24, textAlign: "center" }}>3</span>
            <span>File Watcher detects new tasks and triggers processing pipeline</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span className="badge badge-info" style={{ minWidth: 24, textAlign: "center" }}>4</span>
            <span>Sensitive tasks route to <code>Pending_Approval/</code> for human review</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span className="badge badge-info" style={{ minWidth: 24, textAlign: "center" }}>5</span>
            <span>Completed tasks move to <code>Done/</code> with audit trail</span>
          </div>
        </div>
      </div>
    </>
  );
}

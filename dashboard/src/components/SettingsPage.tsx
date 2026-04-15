"use client";

import { useEffect, useState } from "react";

interface ServiceStatus {
  name: string;
  status: "operational" | "degraded" | "unavailable" | "not_configured" | "unknown";
  description: string;
}

interface Props {
  orchStatus: { running: boolean; pid: number | null };
  apiOnline: boolean;
}

export default function SettingsPage({ orchStatus, apiOnline }: Props) {
  const [health, setHealth] = useState<Record<string, string>>({});

  useEffect(() => {
    fetch("/api/errors")
      .then((r) => r.json())
      .then((d) => setHealth(d.service_health || {}))
      .catch(() => {});
  }, []);

  const services: ServiceStatus[] = [
    {
      name: "Dashboard API",
      status: apiOnline ? "operational" : "unavailable",
      description: "Next.js API routes serving vault data",
    },
    {
      name: "Orchestrator",
      status: orchStatus.running ? "operational" : "unavailable",
      description: orchStatus.running ? `Running (PID: ${orchStatus.pid})` : "Not running",
    },
    {
      name: "Gmail Watcher",
      status: (health.gmail as ServiceStatus["status"]) || "unknown",
      description: health.gmail === "operational" ? "OAuth credentials + token active" : health.gmail === "degraded" ? "credentials.json found, run gmail_watcher.py to generate token" : "Set up credentials.json for Gmail OAuth",
    },
    {
      name: "WhatsApp Watcher",
      status: (health.whatsapp as ServiceStatus["status"]) || "unknown",
      description: health.whatsapp === "operational" ? "Session configured" : "Set WHATSAPP_SESSION_DIR in .env",
    },
    {
      name: "Telegram Bot",
      status: (health.telegram as ServiceStatus["status"]) || "unknown",
      description: health.telegram === "operational" ? "Bot token configured" : "Set TELEGRAM_BOT_TOKEN in .env",
    },
    {
      name: "Odoo ERP",
      status: (health.odoo as ServiceStatus["status"]) || "unknown",
      description: health.odoo === "operational" ? "XML-RPC connection configured (URL + DB + credentials)" : health.odoo === "degraded" ? "ODOO_URL set, missing DB/user/password" : "Set ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD in .env",
    },
    {
      name: "Facebook",
      status: (health.facebook as ServiceStatus["status"]) || "unknown",
      description: health.facebook === "operational" ? "Page Access Token connected via Graph API" : "Set FACEBOOK_PAGE_ACCESS_TOKEN in .env",
    },
    {
      name: "Instagram",
      status: (health.instagram as ServiceStatus["status"]) || "unknown",
      description: health.instagram === "operational" ? "Access Token connected via Graph API" : "Set INSTAGRAM_ACCESS_TOKEN in .env",
    },
    {
      name: "Twitter/X",
      status: (health.twitter as ServiceStatus["status"]) || "unknown",
      description: health.twitter === "operational" ? "API keys + Bearer Token connected" : "Set TWITTER_BEARER_TOKEN & TWITTER_API_KEY in .env",
    },
    {
      name: "LinkedIn",
      status: (health.linkedin as ServiceStatus["status"]) || "unknown",
      description: health.linkedin === "operational" ? "Access Token connected via LinkedIn API" : "Set LINKEDIN_ACCESS_TOKEN in .env",
    },
    {
      name: "Slack Notifications",
      status: (health.slack as ServiceStatus["status"]) || "unknown",
      description: health.slack === "operational" ? "Incoming Webhook connected" : "Set SLACK_WEBHOOK_URL in .env",
    },
  ];

  const statusColor: Record<string, string> = {
    operational: "var(--green)",
    degraded: "var(--yellow)",
    unavailable: "var(--red)",
    not_configured: "var(--orange)",
    unknown: "var(--muted)",
  };

  const statusLabel: Record<string, string> = {
    operational: "Operational",
    degraded: "Degraded",
    unavailable: "Offline",
    not_configured: "Not Configured",
    unknown: "Unknown",
  };

  const operationalCount = services.filter((s) => s.status === "operational").length;
  const configuredCount = services.filter((s) => s.status !== "not_configured" && s.status !== "unknown").length;

  const tiers = [
    { name: "Bronze", color: "#cd7f32", features: ["File Watcher", "Task Processing", "Audit Logging", "Dashboard", "Sensitive Detection"] },
    { name: "Silver", color: "#c0c0c0", features: ["Gmail Integration", "WhatsApp Watcher", "Telegram Bot", "LinkedIn Posting", "Data Analysis", "Weekly Briefing"] },
    { name: "Gold", color: "#ffd700", features: ["Odoo ERP", "Reasoning Engine", "Multi-Platform Social", "MCP Servers", "Error Recovery", "PDF Invoices"] },
    { name: "Platinum", color: "#e5e4e2", features: ["Cloud Sync", "Vault Delegation", "A2A Protocol", "Health Monitor", "Zone Config", "Orchestrator"] },
  ];

  return (
    <>
      {/* System Overview */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: 24 }}>
        <div className="stat-card">
          <div className="label">Services Online</div>
          <div className="value" style={{ color: "var(--green)" }}>{operationalCount}/{services.length}</div>
        </div>
        <div className="stat-card">
          <div className="label">Configured</div>
          <div className="value" style={{ color: configuredCount > 5 ? "var(--green)" : "var(--yellow)" }}>
            {configuredCount}/{services.length}
          </div>
          <div className="sub">{services.length - configuredCount} need setup</div>
        </div>
        <div className="stat-card">
          <div className="label">Feature Tiers</div>
          <div className="value" style={{ color: "var(--purple)" }}>4 Active</div>
        </div>
      </div>

      {/* Services Grid */}
      <div className="section">
        <h2><span className="section-icon">{"\u2699"}</span> Service Connections</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
          {services.map((svc) => (
            <div
              key={svc.name}
              style={{
                background: "var(--bg)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)",
                padding: 14,
                display: "flex",
                alignItems: "center",
                gap: 12,
              }}
            >
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: statusColor[svc.status],
                  flexShrink: 0,
                }}
              />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{svc.name}</div>
                <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>{svc.description}</div>
              </div>
              <span
                className="badge"
                style={{
                  background: `${statusColor[svc.status]}22`,
                  color: statusColor[svc.status],
                }}
              >
                {statusLabel[svc.status]}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Feature Tiers */}
      <div className="section">
        <h2><span className="section-icon">{"\uD83C\uDFC6"}</span> Feature Tiers</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 16 }}>
          {tiers.map((tier) => (
            <div
              key={tier.name}
              style={{
                background: "var(--bg)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)",
                padding: 16,
              }}
            >
              <div style={{ fontWeight: 800, fontSize: 16, color: tier.color, marginBottom: 12 }}>
                {tier.name} Tier
              </div>
              {tier.features.map((f) => (
                <div key={f} style={{ fontSize: 13, padding: "4px 0", display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ color: "var(--green)", fontSize: 12 }}>{"\u2713"}</span>
                  {f}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Configuration */}
      <div className="section">
        <h2><span className="section-icon">{"\uD83D\uDD27"}</span> Configuration</h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div style={{ background: "var(--bg)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: 16 }}>
            <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 12 }}>Environment</div>
            <div style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--muted)" }}>Dashboard Port</span><span>3000</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--muted)" }}>API Server Port</span><span>5000</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--muted)" }}>Auto-Refresh</span><span>10s</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--muted)" }}>Timezone</span><span>PKT (UTC+5)</span>
              </div>
            </div>
          </div>
          <div style={{ background: "var(--bg)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: 16 }}>
            <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 12 }}>Vault Structure</div>
            <div style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--muted)" }}>Needs_Action/</span><span>Incoming tasks</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--muted)" }}>Plans/</span><span>Active plans</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--muted)" }}>Pending_Approval/</span><span>Awaiting review</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--muted)" }}>Approved/</span><span>Approved items</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--muted)" }}>Done/</span><span>Completed</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--muted)" }}>Archive/</span><span>Archived</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

"use client";

import { useEffect, useState } from "react";

interface NotificationType {
  type: string;
  label: string;
  color: string;
  description: string;
}

interface SlackData {
  configured: boolean;
  webhook_preview: string;
  channel: string;
  mode: string;
  notification_types: NotificationType[];
  recent_notifications: Array<{ timestamp?: string; action?: string; outcome?: string }>;
}

interface Props {
  onToast?: (type: "success" | "error", text: string) => void;
}

export default function SlackConfig({ onToast }: Props = {}) {
  const [data, setData] = useState<SlackData | null>(null);
  const [loading, setLoading] = useState(true);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [channel, setChannel] = useState("");
  const [testMsg, setTestMsg] = useState("");
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState("");

  const toast = (type: "success" | "error", text: string) => {
    if (onToast) onToast(type, text);
  };

  const fetchData = () => {
    fetch("/api/slack")
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setChannel(d.channel === "(default)" ? "" : d.channel);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      const res = await fetch("/api/slack", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "save_config", webhook_url: webhookUrl, channel }),
      });
      const result = await res.json();
      if (result.success) {
        toast("success", "Slack webhook saved!");
        setWebhookUrl("");
        fetchData();
      } else {
        toast("error", result.error || "Failed to save");
      }
    } catch {
      toast("error", "Network error");
    }
    setSaving(false);
  };

  const handleSend = async (action: string) => {
    setSending(action);
    try {
      const res = await fetch("/api/slack", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, message: testMsg || undefined }),
      });
      const result = await res.json();
      if (result.success) {
        toast("success", action === "test" ? "Test notification sent!" : "Summary sent!");
        setTestMsg("");
        setTimeout(fetchData, 1000);
      } else {
        toast("error", result.error || result.output || "Failed");
      }
    } catch {
      toast("error", "Network error");
    }
    setSending("");
  };

  if (loading) return <div className="loading"><span className="spinner" /> Loading Slack config...</div>;
  if (!data) return <div className="section"><p style={{ color: "var(--muted)" }}>Failed to load Slack settings</p></div>;

  return (
    <>
      {/* Status Cards */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: 24 }}>
        <div className="stat-card">
          <div className="label">Webhook</div>
          <div className="value" style={{ color: data.configured ? "var(--green)" : "var(--yellow)", fontSize: 20 }}>
            {data.configured ? "Connected" : "Not Set"}
          </div>
          <div className="sub">{data.mode} mode</div>
        </div>
        <div className="stat-card">
          <div className="label">Channel</div>
          <div className="value" style={{ fontSize: 18 }}>{data.channel}</div>
        </div>
        <div className="stat-card">
          <div className="label">Notification Types</div>
          <div className="value" style={{ color: "var(--blue)" }}>{data.notification_types.length}</div>
        </div>
      </div>

      {/* Webhook Config */}
      <div className="section" style={{ marginBottom: 24, borderColor: data.configured ? "var(--green)" : "var(--yellow)" }}>
        <h2><span className="section-icon">{"\u2699"}</span> Webhook Configuration</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {data.configured && (
            <div style={{ fontSize: 13, color: "var(--green)", padding: "8px 12px", background: "var(--green-dim)", borderRadius: "var(--radius-sm)" }}>
              Webhook connected: <code>{data.webhook_preview}</code>
            </div>
          )}
          <div className="form-group" style={{ margin: 0 }}>
            <label>{data.configured ? "Update Webhook URL" : "Slack Webhook URL"}</label>
            <input
              className="form-input"
              placeholder="https://hooks.slack.com/services/T.../B.../..."
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              style={{ padding: "10px 14px" }}
            />
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label>Channel Override (optional)</label>
            <input
              className="form-input"
              placeholder="#general or leave empty for default"
              value={channel}
              onChange={(e) => setChannel(e.target.value)}
              style={{ padding: "10px 14px" }}
            />
          </div>
          <div>
            <button
              className="btn btn-primary"
              onClick={handleSaveConfig}
              disabled={saving || !webhookUrl.trim()}
            >
              {saving ? "Saving..." : "Save Webhook"}
            </button>
          </div>
          {!data.configured && (
            <div style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.6 }}>
              <strong>How to get a webhook URL:</strong><br />
              1. Go to <a href="https://api.slack.com/apps" target="_blank" rel="noreferrer" style={{ color: "var(--blue)" }}>api.slack.com/apps</a><br />
              2. Create or select your app<br />
              3. Enable <strong>Incoming Webhooks</strong><br />
              4. Add a new webhook to your workspace<br />
              5. Copy the URL and paste it above
            </div>
          )}
        </div>
      </div>

      {/* Send Notifications */}
      <div className="section" style={{ marginBottom: 24 }}>
        <h2><span className="section-icon">{"\uD83D\uDCE8"}</span> Send Notification</h2>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <input
            className="form-input"
            placeholder="Test message (optional)"
            value={testMsg}
            onChange={(e) => setTestMsg(e.target.value)}
            style={{ flex: 1, minWidth: 250, padding: "10px 14px" }}
          />
          <button
            className="btn btn-primary"
            onClick={() => handleSend("test")}
            disabled={!!sending}
          >
            {sending === "test" ? "Sending..." : "Send Test"}
          </button>
          <button
            className="btn btn-success"
            onClick={() => handleSend("summary")}
            disabled={!!sending}
          >
            {sending === "summary" ? "Sending..." : "Send Summary"}
          </button>
        </div>
      </div>

      {/* Notification Types */}
      <div className="section">
        <h2><span className="section-icon">{"\uD83D\uDD14"}</span> Notification Types</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
          {data.notification_types.map((nt) => (
            <div
              key={nt.type}
              style={{
                background: "var(--bg)",
                border: "1px solid var(--border)",
                borderLeft: `4px solid ${nt.color}`,
                borderRadius: "var(--radius-sm)",
                padding: 14,
              }}
            >
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{nt.label}</div>
              <div style={{ fontSize: 12, color: "var(--muted)" }}>{nt.description}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Notifications */}
      {data.recent_notifications.length > 0 && (
        <div className="section">
          <h2><span className="section-icon">{"\uD83D\uDCCB"}</span> Recent Notifications</h2>
          <table>
            <thead>
              <tr><th>Time</th><th>Event</th><th>Status</th></tr>
            </thead>
            <tbody>
              {data.recent_notifications.map((n, i) => (
                <tr key={i}>
                  <td style={{ color: "var(--muted)", fontSize: 12 }}>
                    {n.timestamp ? new Date(n.timestamp).toLocaleString() : "\u2014"}
                  </td>
                  <td style={{ fontWeight: 500 }}>{n.action || "\u2014"}</td>
                  <td>
                    <span className={`badge ${n.outcome === "success" ? "badge-paid" : "badge-high"}`}>
                      {n.outcome || "\u2014"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

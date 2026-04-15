"use client";

import { useCallback, useEffect, useState } from "react";

interface Props {
  onToast: (type: "success" | "error", text: string) => void;
}

interface Config {
  enabled: boolean;
  interval_hours: number;
  platforms: {
    facebook: boolean;
    instagram: boolean;
    linkedin: boolean;
    twitter: boolean;
    email: boolean;
    whatsapp: boolean;
  };
  auto_reply: boolean;
  business_description: string;
  tone: string;
  last_run?: string;
  next_run?: string;
}

interface HistoryEntry {
  date: string;
  action: string;
  platform: string;
  status: string;
  detail?: string;
}

const platformMeta: Record<string, { color: string; icon: string; label: string }> = {
  facebook: { color: "#1877F2", icon: "f", label: "Facebook" },
  instagram: { color: "#E4405F", icon: "\u25CB", label: "Instagram" },
  linkedin: { color: "#0A66C2", icon: "in", label: "LinkedIn" },
  twitter: { color: "#1DA1F2", icon: "X", label: "Twitter" },
  email: { color: "var(--blue)", icon: "\u2709", label: "Email" },
  whatsapp: { color: "#25D366", icon: "W", label: "WhatsApp" },
};

export default function Autopilot({ onToast }: Props) {
  const [config, setConfig] = useState<Config | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [lastContent, setLastContent] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch("/api/autopilot");
      if (res.ok) {
        const data = await res.json();
        setConfig(data.config);
        setHistory(data.history || []);
      }
    } catch { /* */ }
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const saveConfig = async (updated: Config) => {
    setConfig(updated);
    try {
      const res = await fetch("/api/autopilot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "save_config", config: updated }),
      });
      const data = await res.json();
      if (data.success) onToast("success", data.message);
    } catch {
      onToast("error", "Failed to save settings");
    }
  };

  const toggleEnabled = async () => {
    try {
      const res = await fetch("/api/autopilot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "toggle" }),
      });
      const data = await res.json();
      if (data.success) {
        setConfig((prev) => prev ? { ...prev, enabled: data.enabled } : prev);
        onToast("success", data.message);
        fetchData();
      }
    } catch {
      onToast("error", "Failed to toggle");
    }
  };

  const runNow = async () => {
    setRunning(true);
    try {
      const res = await fetch("/api/autopilot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "run_now" }),
      });
      const data = await res.json();
      if (data.success) {
        onToast("success", data.message);
        if (data.content) setLastContent(data.content);
        fetchData();
      } else {
        onToast("error", data.error || "Run failed");
      }
    } catch {
      onToast("error", "Network error");
    }
    setRunning(false);
  };

  const formatTime = (ts?: string) => {
    if (!ts) return "Never";
    try {
      const d = new Date(ts);
      return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
    } catch { return ts; }
  };

  const getCountdown = () => {
    if (!config?.next_run || !config.enabled) return null;
    const diff = new Date(config.next_run).getTime() - Date.now();
    if (diff <= 0) return "Running soon...";
    const hours = Math.floor(diff / 3600000);
    const mins = Math.floor((diff % 3600000) / 60000);
    return `${hours}h ${mins}m`;
  };

  if (loading || !config) {
    return <div className="section" style={{ textAlign: "center", padding: 40, color: "var(--muted)" }}>Loading autopilot...</div>;
  }

  return (
    <div>
      {/* Status Banner */}
      <div className="section" style={{
        padding: 20, marginBottom: 24,
        background: config.enabled
          ? "linear-gradient(135deg, rgba(34,197,94,0.12), rgba(99,102,241,0.12))"
          : "var(--card)",
        borderColor: config.enabled ? "var(--green)" : "var(--border)",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{
              width: 50, height: 50, borderRadius: 12,
              background: config.enabled ? "var(--green)" : "var(--muted)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 24, color: "#fff",
            }}>
              {config.enabled ? "\u26A1" : "\u23F8"}
            </div>
            <div>
              <div style={{ fontSize: 18, fontWeight: 700 }}>
                Autopilot {config.enabled ? "Active" : "Inactive"}
              </div>
              <div style={{ fontSize: 13, color: "var(--muted)", marginTop: 2 }}>
                {config.enabled
                  ? `Next run: ${formatTime(config.next_run)} (${getCountdown()})`
                  : "Enable to auto-post and auto-reply every 2 days"
                }
              </div>
              {config.last_run && (
                <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>
                  Last run: {formatTime(config.last_run)}
                </div>
              )}
            </div>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={runNow}
              disabled={running}
              style={{
                padding: "10px 24px", borderRadius: 8, border: "none",
                background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                color: "#fff", fontSize: 14, fontWeight: 600, cursor: "pointer",
                opacity: running ? 0.7 : 1,
              }}
            >
              {running ? "\u23F3 Running..." : "\u25B6 Run Now"}
            </button>
            <button
              onClick={toggleEnabled}
              style={{
                padding: "10px 24px", borderRadius: 8, border: "2px solid",
                borderColor: config.enabled ? "var(--red)" : "var(--green)",
                background: config.enabled ? "var(--red-dim)" : "var(--green-dim)",
                color: config.enabled ? "var(--red)" : "var(--green)",
                fontSize: 14, fontWeight: 600, cursor: "pointer",
              }}
            >
              {config.enabled ? "\u25A0 Disable" : "\u26A1 Enable"}
            </button>
          </div>
        </div>
      </div>

      <div className="two-col">
        {/* Platform Settings */}
        <div className="section" style={{ padding: 20 }}>
          <h3 style={{ marginBottom: 16 }}>Platforms</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {Object.entries(platformMeta).map(([key, meta]) => (
              <label
                key={key}
                style={{
                  display: "flex", alignItems: "center", gap: 12,
                  padding: "10px 14px", borderRadius: 8,
                  background: config.platforms[key as keyof typeof config.platforms] ? `${meta.color}15` : "var(--bg)",
                  border: `1px solid ${config.platforms[key as keyof typeof config.platforms] ? meta.color : "var(--border)"}`,
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={config.platforms[key as keyof typeof config.platforms]}
                  onChange={() => {
                    const updated = { ...config, platforms: { ...config.platforms, [key]: !config.platforms[key as keyof typeof config.platforms] } };
                    saveConfig(updated);
                  }}
                  style={{ width: 18, height: 18, accentColor: meta.color }}
                />
                <span style={{
                  width: 28, height: 28, borderRadius: 6,
                  background: `${meta.color}30`, color: meta.color,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontWeight: 700, fontSize: 12,
                }}>
                  {meta.icon}
                </span>
                <span style={{ fontWeight: 500, fontSize: 14 }}>{meta.label}</span>
                <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--muted)" }}>
                  {key === "facebook" ? "Post + Reply" : key === "instagram" ? "Post (image)" : key === "linkedin" ? "Post" : key === "twitter" ? "Post" : key === "email" ? "Newsletter" : "Broadcast"}
                </span>
              </label>
            ))}
          </div>

          {/* Auto-Reply Toggle */}
          <div style={{ marginTop: 16, padding: "12px 14px", borderRadius: 8, border: "1px solid var(--border)", background: config.auto_reply ? "var(--purple-dim)" : "var(--bg)" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 12, cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={config.auto_reply}
                onChange={() => saveConfig({ ...config, auto_reply: !config.auto_reply })}
                style={{ width: 18, height: 18, accentColor: "var(--purple)" }}
              />
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{"\u2728"} AI Auto-Reply to Comments</div>
                <div style={{ fontSize: 11, color: "var(--muted)" }}>Claude replies to new Facebook comments automatically</div>
              </div>
            </label>
          </div>
        </div>

        {/* Content Settings */}
        <div className="section" style={{ padding: 20 }}>
          <h3 style={{ marginBottom: 16 }}>Content Settings</h3>

          <div className="form-group" style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 13, fontWeight: 600, marginBottom: 6, display: "block" }}>Schedule Interval</label>
            <div style={{ display: "flex", gap: 8 }}>
              {[24, 48, 72].map((h) => (
                <button
                  key={h}
                  onClick={() => saveConfig({ ...config, interval_hours: h })}
                  style={{
                    flex: 1, padding: "8px 12px", borderRadius: 6,
                    border: `2px solid ${config.interval_hours === h ? "var(--purple)" : "var(--border)"}`,
                    background: config.interval_hours === h ? "var(--purple-dim)" : "var(--bg)",
                    color: config.interval_hours === h ? "var(--purple)" : "var(--muted)",
                    fontWeight: config.interval_hours === h ? 700 : 400, fontSize: 13, cursor: "pointer",
                  }}
                >
                  {h === 24 ? "Daily" : h === 48 ? "Every 2 Days" : "Every 3 Days"}
                </button>
              ))}
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 13, fontWeight: 600, marginBottom: 6, display: "block" }}>Tone</label>
            <div style={{ display: "flex", gap: 8 }}>
              {["professional", "casual", "bold", "friendly"].map((t) => (
                <button
                  key={t}
                  onClick={() => saveConfig({ ...config, tone: t })}
                  style={{
                    flex: 1, padding: "8px 12px", borderRadius: 6,
                    border: `2px solid ${config.tone === t ? "var(--blue)" : "var(--border)"}`,
                    background: config.tone === t ? "var(--blue-dim)" : "var(--bg)",
                    color: config.tone === t ? "var(--blue)" : "var(--muted)",
                    fontWeight: config.tone === t ? 700 : 400, fontSize: 12, cursor: "pointer",
                    textTransform: "capitalize",
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 13, fontWeight: 600, marginBottom: 6, display: "block" }}>Business Description</label>
            <textarea
              value={config.business_description}
              onChange={(e) => setConfig({ ...config, business_description: e.target.value })}
              onBlur={() => saveConfig(config)}
              placeholder="Describe your business for AI content generation..."
              style={{
                width: "100%", minHeight: 80, padding: 10, borderRadius: 6,
                background: "var(--bg)", border: "1px solid var(--border)",
                color: "var(--text)", fontSize: 13, fontFamily: "inherit", resize: "vertical",
              }}
            />
            <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>
              Claude uses this to generate relevant posts for your business
            </div>
          </div>
        </div>
      </div>

      {/* Last Generated Content */}
      {lastContent && (
        <div className="section" style={{ padding: 16, marginTop: 16 }}>
          <h3 style={{ marginBottom: 8, fontSize: 14 }}>{"\uD83D\uDCDD"} Last Generated Post</h3>
          <div style={{
            padding: 12, borderRadius: 8, background: "var(--bg)",
            fontSize: 13, lineHeight: 1.6, whiteSpace: "pre-wrap",
          }}>
            {lastContent}
          </div>
        </div>
      )}

      {/* History Log */}
      <div className="section" style={{ padding: 20, marginTop: 16 }}>
        <h3 style={{ marginBottom: 16 }}>Activity History</h3>
        {history.length === 0 ? (
          <div style={{ textAlign: "center", padding: 30, color: "var(--muted)" }}>
            No autopilot runs yet. Click &quot;Run Now&quot; to start.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {history.map((h, i) => {
              const meta = platformMeta[h.platform] || { color: "var(--muted)", icon: "?", label: h.platform };
              return (
                <div key={i} style={{
                  display: "flex", alignItems: "center", gap: 10,
                  padding: "8px 12px", borderRadius: 6,
                  background: h.status === "success" ? "var(--green-dim)" : h.status === "failed" ? "var(--red-dim)" : "var(--bg)",
                }}>
                  <span style={{
                    width: 24, height: 24, borderRadius: 6,
                    background: `${meta.color}30`, color: meta.color,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 10, fontWeight: 700,
                  }}>
                    {meta.icon}
                  </span>
                  <span style={{ fontWeight: 600, fontSize: 13, minWidth: 80 }}>{meta.label}</span>
                  <span style={{
                    fontSize: 11, padding: "2px 8px", borderRadius: 4,
                    background: h.action === "post" ? "var(--blue-dim)" : "var(--purple-dim)",
                    color: h.action === "post" ? "var(--blue)" : "var(--purple)",
                    fontWeight: 600,
                  }}>
                    {h.action}
                  </span>
                  <span style={{
                    fontSize: 11, padding: "2px 8px", borderRadius: 4,
                    background: h.status === "success" ? "var(--green-dim)" : h.status === "failed" ? "var(--red-dim)" : "var(--yellow-dim)",
                    color: h.status === "success" ? "var(--green)" : h.status === "failed" ? "var(--red)" : "var(--yellow)",
                    fontWeight: 600,
                  }}>
                    {h.status}
                  </span>
                  <span style={{ flex: 1, fontSize: 11, color: "var(--muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {h.detail}
                  </span>
                  <span style={{ fontSize: 11, color: "var(--muted)", flexShrink: 0 }}>
                    {formatTime(h.date)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

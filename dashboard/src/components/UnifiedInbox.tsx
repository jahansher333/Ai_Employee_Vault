"use client";

import { useCallback, useEffect, useState } from "react";

interface InboxItem {
  id: string;
  type: "email" | "whatsapp" | "comment";
  platform?: string;
  from: string;
  subject?: string;
  message: string;
  timestamp: string;
  phone?: string;
  post_id?: string;
  post_message?: string;
  reply_to?: string;
}

interface Props {
  onToast: (type: "success" | "error", text: string) => void;
}

const platformColors: Record<string, string> = {
  email: "var(--blue)",
  whatsapp: "#25D366",
  facebook: "#1877F2",
  instagram: "#E4405F",
  linkedin: "#0A66C2",
  twitter: "#1DA1F2",
  comment: "var(--purple)",
};

const platformIcons: Record<string, string> = {
  email: "\u2709",
  whatsapp: "W",
  facebook: "f",
  instagram: "\u25CB",
  linkedin: "in",
  twitter: "X",
  comment: "\uD83D\uDCAC",
};

export default function UnifiedInbox({ onToast }: Props) {
  const [items, setItems] = useState<InboxItem[]>([]);
  const [counts, setCounts] = useState({ email: 0, whatsapp: 0, comment: 0 });
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "email" | "whatsapp" | "comment">("all");
  const [replyingId, setReplyingId] = useState<string | null>(null);
  const [replyText, setReplyText] = useState<Record<string, string>>({});
  const [aiLoading, setAiLoading] = useState<string | null>(null);
  const [sendingId, setSendingId] = useState<string | null>(null);

  const fetchInbox = useCallback(async () => {
    try {
      const res = await fetch("/api/inbox/unified");
      if (res.ok) {
        const data = await res.json();
        setItems(data.items || []);
        setCounts(data.counts || { email: 0, whatsapp: 0, comment: 0 });
      }
    } catch { /* */ }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchInbox();
    const iv = setInterval(fetchInbox, 30000);
    return () => clearInterval(iv);
  }, [fetchInbox]);

  const filtered = filter === "all" ? items : items.filter((i) => i.type === filter);

  const handleAiReply = async (item: InboxItem) => {
    setAiLoading(item.id);
    try {
      const res = await fetch("/api/inbox/ai-reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ item, action: "generate" }),
      });
      const data = await res.json();
      if (data.success && data.reply) {
        setReplyText((prev) => ({ ...prev, [item.id]: data.reply }));
        setReplyingId(item.id);
      } else {
        onToast("error", data.error || "Failed to generate reply");
      }
    } catch {
      onToast("error", "Network error");
    }
    setAiLoading(null);
  };

  const handleSendReply = async (item: InboxItem) => {
    const text = replyText[item.id];
    if (!text?.trim()) return;
    setSendingId(item.id);
    try {
      const res = await fetch("/api/inbox/ai-reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          item: { ...item, customReply: text },
          action: "send",
        }),
      });
      const data = await res.json();
      if (data.success) {
        onToast("success", data.message);
        setReplyingId(null);
        setReplyText((prev) => { const n = { ...prev }; delete n[item.id]; return n; });
      } else {
        onToast("error", data.message || "Failed to send reply");
      }
    } catch {
      onToast("error", "Network error");
    }
    setSendingId(null);
  };

  const getPlatformKey = (item: InboxItem) => item.platform || item.type;
  const getColor = (item: InboxItem) => platformColors[getPlatformKey(item)] || "var(--muted)";
  const getIcon = (item: InboxItem) => platformIcons[getPlatformKey(item)] || "?";

  const formatTime = (ts: string) => {
    try {
      const d = new Date(ts);
      const now = new Date();
      const diff = now.getTime() - d.getTime();
      if (diff < 60000) return "Just now";
      if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
      if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
      return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    } catch { return ts; }
  };

  return (
    <div>
      {/* Stats Bar */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 24 }}>
        {[
          { label: "Total", count: items.length, color: "var(--purple)", key: "all" as const },
          { label: "Emails", count: counts.email, color: "var(--blue)", key: "email" as const },
          { label: "WhatsApp", count: counts.whatsapp, color: "#25D366", key: "whatsapp" as const },
          { label: "Comments", count: counts.comment, color: "var(--orange)", key: "comment" as const },
        ].map((s) => (
          <div
            key={s.key}
            className="stat-card"
            onClick={() => setFilter(s.key)}
            style={{
              cursor: "pointer",
              borderColor: filter === s.key ? s.color : undefined,
              background: filter === s.key ? `${s.color}15` : undefined,
            }}
          >
            <div className="label">{s.label}</div>
            <div className="value" style={{ color: s.color }}>{s.count}</div>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div className="section" style={{ padding: "12px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 8 }}>
          {(["all", "email", "whatsapp", "comment"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: "6px 14px", borderRadius: 6, border: "1px solid",
                borderColor: filter === f ? "var(--purple)" : "var(--border)",
                background: filter === f ? "var(--purple-dim)" : "transparent",
                color: filter === f ? "var(--purple)" : "var(--muted)",
                fontSize: 13, cursor: "pointer", fontWeight: filter === f ? 600 : 400,
              }}
            >
              {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
              {f !== "all" && ` (${f === "email" ? counts.email : f === "whatsapp" ? counts.whatsapp : counts.comment})`}
            </button>
          ))}
        </div>
        <button
          className="btn btn-primary"
          onClick={() => { setLoading(true); fetchInbox(); }}
          disabled={loading}
          style={{ fontSize: 13, padding: "6px 16px" }}
        >
          {loading ? "Loading..." : "\u21BB Refresh"}
        </button>
      </div>

      {/* Inbox Items */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {loading && items.length === 0 && (
          <div className="section" style={{ textAlign: "center", padding: 40, color: "var(--muted)" }}>
            Loading inbox...
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div className="section" style={{ textAlign: "center", padding: 40, color: "var(--muted)" }}>
            No {filter === "all" ? "" : filter} messages found
          </div>
        )}

        {filtered.map((item) => (
          <div key={item.id} className="section" style={{ padding: 16 }}>
            {/* Header Row */}
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
              {/* Platform Badge */}
              <div style={{
                width: 36, height: 36, borderRadius: 8,
                background: `${getColor(item)}20`,
                display: "flex", alignItems: "center", justifyContent: "center",
                color: getColor(item), fontWeight: 700, fontSize: 14,
                flexShrink: 0,
              }}>
                {getIcon(item)}
              </div>

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{item.from}</span>
                  <span style={{
                    fontSize: 10, padding: "2px 8px", borderRadius: 4,
                    background: `${getColor(item)}20`, color: getColor(item),
                    fontWeight: 600, textTransform: "uppercase",
                  }}>
                    {getPlatformKey(item)}
                  </span>
                </div>
                {item.subject && (
                  <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>{item.subject}</div>
                )}
              </div>

              <div style={{ fontSize: 11, color: "var(--muted)", flexShrink: 0 }}>
                {formatTime(item.timestamp)}
              </div>
            </div>

            {/* Message Body */}
            <div style={{
              fontSize: 13, color: "var(--text)", lineHeight: 1.5,
              padding: "8px 12px", background: "var(--bg)", borderRadius: 8,
              marginBottom: 8, maxHeight: 120, overflow: "auto",
            }}>
              {item.message || "(no content)"}
            </div>

            {/* Post reference for comments */}
            {item.post_message && (
              <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 8, fontStyle: "italic" }}>
                On post: &quot;{item.post_message}&quot;
              </div>
            )}

            {/* Action Buttons */}
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <button
                onClick={() => handleAiReply(item)}
                disabled={aiLoading === item.id}
                style={{
                  padding: "7px 16px", borderRadius: 6, border: "none",
                  background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                  color: "#fff", fontSize: 12, fontWeight: 600, cursor: "pointer",
                  opacity: aiLoading === item.id ? 0.7 : 1,
                  display: "flex", alignItems: "center", gap: 6,
                }}
              >
                {aiLoading === item.id ? (
                  <><span className="spinner" style={{ width: 12, height: 12, borderWidth: 2, marginRight: 0 }} /> Generating...</>
                ) : (
                  <>{"\u2728"} AI Auto-Reply</>
                )}
              </button>

              {item.type === "email" && item.reply_to && (
                <button
                  onClick={() => { setReplyingId(item.id); setReplyText((prev) => ({ ...prev, [item.id]: prev[item.id] || "" })); }}
                  style={{
                    padding: "7px 16px", borderRadius: 6, border: "1px solid var(--blue)",
                    background: "var(--blue-dim)", color: "var(--blue)",
                    fontSize: 12, fontWeight: 600, cursor: "pointer",
                  }}
                >
                  {"\u2709"} Reply Email
                </button>
              )}
              {item.type === "whatsapp" && item.phone && (
                <button
                  onClick={() => { setReplyingId(item.id); setReplyText((prev) => ({ ...prev, [item.id]: prev[item.id] || "" })); }}
                  style={{
                    padding: "7px 16px", borderRadius: 6, border: "1px solid #25D366",
                    background: "#25D36615", color: "#25D366",
                    fontSize: 12, fontWeight: 600, cursor: "pointer",
                  }}
                >
                  W Reply WhatsApp
                </button>
              )}
              {item.type === "comment" && item.platform === "facebook" && (
                <button
                  onClick={() => { setReplyingId(item.id); setReplyText((prev) => ({ ...prev, [item.id]: prev[item.id] || "" })); }}
                  style={{
                    padding: "7px 16px", borderRadius: 6, border: "1px solid #1877F2",
                    background: "#1877F215", color: "#1877F2",
                    fontSize: 12, fontWeight: 600, cursor: "pointer",
                  }}
                >
                  {"\uD83D\uDCAC"} Reply Comment
                </button>
              )}
            </div>

            {/* Reply Box */}
            {replyingId === item.id && (
              <div style={{
                marginTop: 12, padding: 12, background: "var(--bg-secondary)",
                borderRadius: 8, border: "1px solid var(--border)",
              }}>
                <textarea
                  value={replyText[item.id] || ""}
                  onChange={(e) => setReplyText((prev) => ({ ...prev, [item.id]: e.target.value }))}
                  placeholder="Type your reply or click AI Auto-Reply to generate one..."
                  style={{
                    width: "100%", minHeight: 100, padding: 10, borderRadius: 6,
                    background: "var(--card)", border: "1px solid var(--border)",
                    color: "var(--text)", fontSize: 13, resize: "vertical",
                    fontFamily: "inherit",
                  }}
                />
                <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                  <button
                    onClick={() => handleSendReply(item)}
                    disabled={sendingId === item.id || !(replyText[item.id] || "").trim()}
                    style={{
                      padding: "8px 20px", borderRadius: 6, border: "none",
                      background: getColor(item), color: "#fff",
                      fontSize: 12, fontWeight: 600, cursor: "pointer",
                      opacity: sendingId === item.id || !(replyText[item.id] || "").trim() ? 0.5 : 1,
                    }}
                  >
                    {sendingId === item.id ? "Sending..." : "\u27A4 Send Reply"}
                  </button>
                  <button
                    onClick={() => { setReplyingId(null); }}
                    style={{
                      padding: "8px 16px", borderRadius: 6,
                      border: "1px solid var(--border)", background: "transparent",
                      color: "var(--muted)", fontSize: 12, cursor: "pointer",
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";

interface PlatformEngagement {
  posts: number;
  comments: number;
  status: string;
}

interface EngagementData {
  platforms: Record<string, PlatformEngagement>;
  recent_activity: Array<{ timestamp?: string; action?: string; input_ref?: string; outcome?: string }>;
  capabilities: string[];
}

interface Comment {
  id: string;
  from: string;
  message: string;
  created_time: string;
  post_id?: string;
  post_message?: string;
  platform: string;
}

interface CommentsData {
  comments: Comment[];
  facebook: { count: number; error: string | null };
  linkedin: { count: number; error: string | null };
  fetched_at: string;
}

const platformColors: Record<string, string> = {
  facebook: "#1877f2",
  instagram: "#e4405f",
  twitter: "#1da1f2",
  linkedin: "#0a66c2",
};

const platformIcons: Record<string, string> = {
  facebook: "f",
  instagram: "\uD83D\uDCF7",
  twitter: "\uD83D\uDC26",
  linkedin: "in",
};

export default function SocialEngagement() {
  const [data, setData] = useState<EngagementData | null>(null);
  const [loading, setLoading] = useState(true);
  const [commentsData, setCommentsData] = useState<CommentsData | null>(null);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"all" | "facebook" | "linkedin">("all");

  useEffect(() => {
    fetch("/api/engagement")
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const fetchComments = async () => {
    setCommentsLoading(true);
    try {
      const res = await fetch("/api/engagement/comments");
      if (res.ok) {
        setCommentsData(await res.json());
      }
    } catch { /* ignore */ }
    setCommentsLoading(false);
  };

  // Auto-fetch comments on load
  useEffect(() => {
    fetchComments();
  }, []);

  if (loading) return <div className="loading"><span className="spinner" /> Loading engagement data...</div>;
  if (!data) return <div className="section"><p style={{ color: "var(--muted)" }}>Failed to load engagement data</p></div>;

  const totalPosts = Object.values(data.platforms).reduce((s, p) => s + p.posts, 0);

  const filteredComments = commentsData?.comments.filter(
    (c) => activeTab === "all" || c.platform === activeTab
  ) || [];

  return (
    <>
      {/* Platform Cards */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 24 }}>
        {Object.entries(data.platforms).map(([name, info]) => (
          <div key={name} className="stat-card" style={{ borderTop: `3px solid ${platformColors[name]}` }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div className="label" style={{ textTransform: "capitalize" }}>{name}</div>
              <span
                className="badge"
                style={{
                  background: info.status === "connected" ? "var(--green-dim)" : "var(--yellow-dim)",
                  color: info.status === "connected" ? "var(--green)" : "var(--yellow)",
                  fontSize: 10,
                }}
              >
                {info.status === "connected" ? "Connected" : "Setup Needed"}
              </span>
            </div>
            <div className="value" style={{ color: platformColors[name], fontSize: 24 }}>{info.posts}</div>
            <div className="sub">posts published</div>
          </div>
        ))}
      </div>

      {/* Comments Section */}
      <div className="section" style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ margin: 0 }}>
            <span className="section-icon">{"\uD83D\uDCAC"}</span> Comments & Replies
          </h2>
          <button
            className="btn btn-primary"
            onClick={fetchComments}
            disabled={commentsLoading}
            style={{ display: "flex", alignItems: "center", gap: 6 }}
          >
            {commentsLoading ? (
              <><span className="spinner" style={{ width: 14, height: 14, borderWidth: 2, marginRight: 0 }} /> Fetching...</>
            ) : (
              <>{"\uD83D\uDD04"} Refresh Comments</>
            )}
          </button>
        </div>

        {/* Platform Filter Tabs */}
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          {(["all", "facebook", "linkedin"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                padding: "8px 16px",
                borderRadius: "var(--radius-sm)",
                border: `2px solid ${activeTab === tab ? (tab === "all" ? "var(--blue)" : platformColors[tab] || "var(--blue)") : "var(--border)"}`,
                background: activeTab === tab ? (tab === "all" ? "var(--blue-dim)" : `${platformColors[tab]}15`) : "var(--bg)",
                color: activeTab === tab ? (tab === "all" ? "var(--blue)" : platformColors[tab]) : "var(--muted)",
                fontWeight: activeTab === tab ? 700 : 500,
                fontSize: 13,
                cursor: "pointer",
                textTransform: "capitalize",
                transition: "all 0.15s",
              }}
            >
              {tab === "all" ? "All Platforms" : `${platformIcons[tab]} ${tab}`}
              {commentsData && (
                <span style={{ marginLeft: 6, opacity: 0.7 }}>
                  ({tab === "all"
                    ? commentsData.comments.length
                    : commentsData[tab as "facebook" | "linkedin"]?.count || 0})
                </span>
              )}
            </button>
          ))}
        </div>

        {/* API Status Messages */}
        {commentsData && (
          <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
            {commentsData.facebook.error && (
              <div style={{
                padding: "6px 12px", borderRadius: "var(--radius-sm)",
                background: "var(--yellow-dim)", border: "1px solid var(--yellow)",
                fontSize: 12, color: "var(--yellow)", flex: 1,
              }}>
                <strong>Facebook:</strong> {commentsData.facebook.error}
              </div>
            )}
            {commentsData.linkedin.error && (
              <div style={{
                padding: "6px 12px", borderRadius: "var(--radius-sm)",
                background: "var(--yellow-dim)", border: "1px solid var(--yellow)",
                fontSize: 12, color: "var(--yellow)", flex: 1,
              }}>
                <strong>LinkedIn:</strong> {commentsData.linkedin.error}
              </div>
            )}
            {!commentsData.facebook.error && !commentsData.linkedin.error && commentsData.comments.length === 0 && (
              <div style={{
                padding: "10px 16px", borderRadius: "var(--radius-sm)",
                background: "var(--surface)", border: "1px solid var(--border)",
                fontSize: 13, color: "var(--muted)", width: "100%", textAlign: "center",
              }}>
                No comments found on recent posts. Comments will appear here when your audience engages.
              </div>
            )}
          </div>
        )}

        {/* Comments List */}
        {filteredComments.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {filteredComments.map((comment) => (
              <div
                key={comment.id}
                style={{
                  padding: "14px 18px",
                  background: "var(--bg)",
                  borderTop: "1px solid var(--border)",
                  borderRight: "1px solid var(--border)",
                  borderBottom: "1px solid var(--border)",
                  borderLeft: `4px solid ${platformColors[comment.platform] || "var(--border)"}`,
                  borderRadius: "var(--radius-sm)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {/* Platform badge */}
                    <span style={{
                      width: 28, height: 28, borderRadius: "50%",
                      background: platformColors[comment.platform],
                      color: "#fff", display: "flex", alignItems: "center",
                      justifyContent: "center", fontSize: 12, fontWeight: 700,
                      flexShrink: 0,
                    }}>
                      {platformIcons[comment.platform] || "?"}
                    </span>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 14 }}>{comment.from}</div>
                      <div style={{ fontSize: 11, color: "var(--muted)" }}>
                        {comment.platform.charAt(0).toUpperCase() + comment.platform.slice(1)}
                        {comment.created_time && (
                          <> {"\u2022"} {new Date(comment.created_time).toLocaleString()}</>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Comment message */}
                <div style={{
                  fontSize: 14, lineHeight: 1.6, color: "var(--text)",
                  padding: "10px 14px", background: "var(--surface)",
                  borderRadius: "var(--radius-sm)", marginBottom: 6,
                }}>
                  {comment.message || <span style={{ color: "var(--muted)", fontStyle: "italic" }}>No text</span>}
                </div>

                {/* Post reference */}
                {comment.post_message && (
                  <div style={{ fontSize: 11, color: "var(--muted)", display: "flex", alignItems: "center", gap: 6 }}>
                    <span>{"\u21B3"}</span>
                    <span>on post: &quot;{comment.post_message}{comment.post_message.length >= 100 ? "..." : ""}&quot;</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Fetched timestamp */}
        {commentsData?.fetched_at && (
          <div style={{ marginTop: 12, fontSize: 11, color: "var(--muted)", textAlign: "right" }}>
            Last fetched: {new Date(commentsData.fetched_at).toLocaleString()}
          </div>
        )}
      </div>

      {/* Engagement Overview */}
      <div className="two-col">
        <div className="section">
          <h2><span className="section-icon">{"\uD83D\uDCCA"}</span> Engagement Summary</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
              <span style={{ color: "var(--muted)" }}>Total Posts Published</span>
              <span style={{ fontWeight: 700 }}>{totalPosts}</span>
            </div>
            {Object.entries(data.platforms).map(([name, info]) => (
              <div key={name} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                <span style={{ color: platformColors[name], fontWeight: 600, textTransform: "capitalize" }}>
                  {platformIcons[name]} {name}
                </span>
                <div style={{ display: "flex", gap: 16 }}>
                  <span style={{ fontSize: 13, color: "var(--muted)" }}>{info.posts} posts</span>
                  <span
                    className="badge"
                    style={{
                      background: info.status === "connected" ? "var(--green-dim)" : "var(--red-dim)",
                      color: info.status === "connected" ? "var(--green)" : "var(--red)",
                    }}
                  >
                    {info.status === "connected" ? "Active" : "Inactive"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Capabilities */}
        <div className="section">
          <h2><span className="section-icon">{"\u2699"}</span> Engagement Capabilities</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {data.capabilities.map((cap, i) => (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "8px 12px", background: "var(--bg)", borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border)", fontSize: 13,
              }}>
                <span style={{ color: "var(--green)" }}>{"\u2713"}</span>
                {cap}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      {data.recent_activity.length > 0 && (
        <div className="section">
          <h2><span className="section-icon">{"\uD83D\uDCDD"}</span> Recent Social Activity</h2>
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Action</th>
                <th>Reference</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_activity.map((a, i) => (
                <tr key={i}>
                  <td style={{ color: "var(--muted)", fontSize: 12 }}>
                    {a.timestamp ? new Date(a.timestamp).toLocaleString() : "\u2014"}
                  </td>
                  <td style={{ fontWeight: 500 }}>{a.action || "\u2014"}</td>
                  <td style={{ color: "var(--muted)", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>
                    {a.input_ref || "\u2014"}
                  </td>
                  <td>
                    <span className={`badge ${a.outcome === "success" ? "badge-paid" : "badge-high"}`}>
                      {a.outcome || "\u2014"}
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

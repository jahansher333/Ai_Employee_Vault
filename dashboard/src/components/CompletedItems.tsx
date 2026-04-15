"use client";

import { useEffect, useState } from "react";

interface DoneItem {
  filename: string;
  type: string;
  completed_at: string;
}

export default function CompletedItems() {
  const [items, setItems] = useState<DoneItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/done?limit=50")
      .then((r) => r.json())
      .then((d) => setItems(d.done || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading"><span className="spinner" /> Loading completed items...</div>;

  // Group by type
  const byType: Record<string, DoneItem[]> = {};
  for (const item of items) {
    const t = item.type || "task";
    if (!byType[t]) byType[t] = [];
    byType[t].push(item);
  }

  const typeIcons: Record<string, string> = {
    social: "\u266A",
    email: "\u2709",
    task: "\u2713",
    plan: "\uD83D\uDCC2",
    invoice: "$",
  };

  const typeColors: Record<string, string> = {
    social: "var(--purple)",
    email: "var(--cyan)",
    task: "var(--green)",
    plan: "var(--yellow)",
    invoice: "var(--orange)",
  };

  // Detect type from filename
  const detectType = (filename: string): string => {
    const upper = filename.toUpperCase();
    if (upper.startsWith("FACEBOOK") || upper.startsWith("TWITTER") || upper.startsWith("LINKEDIN") || upper.startsWith("INSTAGRAM")) return "social";
    if (upper.startsWith("EMAIL")) return "email";
    if (upper.startsWith("PLAN")) return "plan";
    return "task";
  };

  // Platform from filename
  const detectPlatform = (filename: string): string => {
    const upper = filename.toUpperCase();
    if (upper.startsWith("FACEBOOK")) return "Facebook";
    if (upper.startsWith("TWITTER")) return "Twitter";
    if (upper.startsWith("LINKEDIN")) return "LinkedIn";
    if (upper.startsWith("INSTAGRAM")) return "Instagram";
    if (upper.startsWith("EMAIL")) return "Email";
    return "";
  };

  return (
    <div className="section">
      <h2>
        <span className="section-icon">{"\u2713"}</span> Completed Items
        <span style={{ fontSize: 13, fontWeight: 400, color: "var(--muted)", marginLeft: 8 }}>
          ({items.length} total)
        </span>
      </h2>
      {items.length === 0 ? (
        <div style={{ color: "var(--muted)", padding: 20, textAlign: "center" }}>
          No completed items yet.
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Item</th>
              <th>Type</th>
              <th>Platform</th>
              <th>Completed</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const type = detectType(item.filename);
              const platform = detectPlatform(item.filename);
              return (
                <tr key={item.filename}>
                  <td style={{ fontWeight: 500, maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {item.filename.replace(/\.md$/, "").replace(/[-_]/g, " ").slice(0, 60)}
                  </td>
                  <td>
                    <span
                      className="badge"
                      style={{
                        background: `${typeColors[type] || "var(--muted)"}22`,
                        color: typeColors[type] || "var(--muted)",
                      }}
                    >
                      {typeIcons[type] || ""} {type}
                    </span>
                  </td>
                  <td style={{ color: "var(--muted)", fontSize: 13 }}>{platform || "—"}</td>
                  <td style={{ color: "var(--muted)", fontSize: 13 }}>{item.completed_at || "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

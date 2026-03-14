"use client";

import { useEffect, useState } from "react";

interface AuditEntry {
  timestamp?: string;
  action?: string;
  input_ref?: string;
  outcome?: string;
}

export default function AuditLog() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);

  useEffect(() => {
    fetch("/api/audit")
      .then((r) => r.json())
      .then((d) => setEntries((d.entries || []).reverse().slice(0, 15)))
      .catch(() => {});
  }, []);

  return (
    <div className="section">
      <h2>Recent Activity</h2>
      {entries.length === 0 ? (
        <p style={{ color: "var(--muted)" }}>No recent activity</p>
      ) : (
        <table>
          <thead>
            <tr><th>Time</th><th>Action</th><th>Reference</th><th>Status</th></tr>
          </thead>
          <tbody>
            {entries.map((e, i) => {
              const time = e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : "";
              return (
                <tr key={i}>
                  <td style={{ color: "var(--muted)", fontSize: 13 }}>{time}</td>
                  <td>{e.action || ""}</td>
                  <td style={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {e.input_ref || ""}
                  </td>
                  <td>
                    <span className={`badge ${e.outcome === "success" ? "badge-low" : "badge-high"}`}>
                      {e.outcome || ""}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

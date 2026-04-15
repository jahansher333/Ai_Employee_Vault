"use client";

import { useEffect, useState } from "react";

interface Approval {
  filename: string;
  type: string;
  status: string;
  preview: string;
}

interface Props {
  onToast: (type: "success" | "error", text: string) => void;
}

export default function ApprovalsManager({ onToast }: Props) {
  const [items, setItems] = useState<Approval[]>([]);

  const fetchApprovals = () => {
    fetch("/api/approvals")
      .then((r) => r.json())
      .then((d) => setItems(d.approvals || []))
      .catch(() => {});
  };

  useEffect(() => {
    fetchApprovals();
    const iv = setInterval(fetchApprovals, 10000);
    return () => clearInterval(iv);
  }, []);

  const handleAction = async (filename: string, action: "approve" | "reject") => {
    try {
      const res = await fetch("/api/approvals/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename, action }),
      });
      const result = await res.json();
      if (result.success) {
        onToast("success", result.message);
        fetchApprovals();
      } else {
        onToast("error", result.error || "Action failed");
      }
    } catch {
      onToast("error", "Network error");
    }
  };

  const getPlatformColor = (filename: string) => {
    if (filename.startsWith("FACEBOOK")) return "var(--facebook)";
    if (filename.startsWith("INSTAGRAM")) return "var(--instagram)";
    if (filename.startsWith("TWITTER")) return "var(--twitter)";
    if (filename.startsWith("LINKEDIN")) return "var(--linkedin)";
    return "var(--text)";
  };

  return (
    <div className="section">
      <h2>
        <span className="section-icon">{"\u2713"}</span>
        Pending Approvals
        <span className="badge badge-pending" style={{ marginLeft: 8 }}>{items.length}</span>
      </h2>
      {items.length === 0 ? (
        <div style={{ textAlign: "center", padding: 40, color: "var(--muted)" }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>{"\u2714"}</div>
          <div style={{ fontSize: 16, fontWeight: 600 }}>All clear</div>
          <div style={{ fontSize: 13, marginTop: 4 }}>No items waiting for approval</div>
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Item</th>
              <th>Type</th>
              <th>Preview</th>
              <th style={{ textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((a) => (
              <tr key={a.filename}>
                <td style={{
                  maxWidth: 220,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  color: getPlatformColor(a.filename),
                  fontWeight: 600,
                }}>
                  {a.filename}
                </td>
                <td>
                  <span className="badge badge-info">{a.type}</span>
                </td>
                <td style={{ maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--muted)", fontSize: 12 }}>
                  {a.preview}
                </td>
                <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                  <button className="btn btn-sm btn-success" onClick={() => handleAction(a.filename, "approve")} style={{ marginRight: 6 }}>
                    Approve
                  </button>
                  <button className="btn btn-sm btn-danger" onClick={() => handleAction(a.filename, "reject")}>
                    Reject
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

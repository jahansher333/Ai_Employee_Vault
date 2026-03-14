"use client";

import { useEffect, useState } from "react";

interface Approval {
  filename: string;
  type: string;
  status: string;
  preview: string;
}

export default function ApprovalsTable() {
  const [items, setItems] = useState<Approval[]>([]);

  useEffect(() => {
    fetch("/api/approvals")
      .then((r) => r.json())
      .then((d) => setItems(d.approvals || []))
      .catch(() => {});
  }, []);

  return (
    <div className="section">
      <h2>Pending Approvals ({items.length})</h2>
      {items.length === 0 ? (
        <p style={{ color: "var(--muted)" }}>No pending approvals</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>File</th>
              <th>Type</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((a) => (
              <tr key={a.filename}>
                <td style={{ maxWidth: 250, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {a.filename}
                </td>
                <td>{a.type}</td>
                <td>
                  <span className="badge badge-medium">{a.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

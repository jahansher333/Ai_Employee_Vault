"use client";

import { useEffect, useState } from "react";

interface Task {
  filename: string;
  type: string;
  priority: string;
  status: string;
  preview: string;
  modified: string;
}

export default function TasksTable() {
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    fetch("/api/tasks?limit=15")
      .then((r) => r.json())
      .then((d) => setTasks(d.tasks || []))
      .catch(() => {});
  }, []);

  return (
    <div className="section">
      <h2>Pending Tasks ({tasks.length})</h2>
      {tasks.length === 0 ? (
        <p style={{ color: "var(--muted)" }}>No pending tasks</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>File</th>
              <th>Type</th>
              <th>Priority</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.filename}>
                <td style={{ maxWidth: 250, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {t.filename}
                </td>
                <td>{t.type}</td>
                <td>
                  <span className={`badge badge-${t.priority}`}>{t.priority}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

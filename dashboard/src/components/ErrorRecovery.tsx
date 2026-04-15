"use client";

import { useEffect, useState } from "react";

interface ErrorEntry {
  timestamp?: string;
  action?: string;
  input_ref?: string;
  outcome?: string;
  error?: string;
}

interface HealthService {
  status: string;
  failures: number;
}

interface ErrorData {
  recent_errors: ErrorEntry[];
  error_count: number;
  health?: Record<string, HealthService>;
  service_health?: Record<string, string>;
}

export default function ErrorRecovery() {
  const [data, setData] = useState<ErrorData | null>(null);

  const fetchErrors = () => {
    fetch("/api/errors")
      .then((r) => r.json())
      .then(setData)
      .catch(() => {});
  };

  useEffect(() => {
    fetchErrors();
    const iv = setInterval(fetchErrors, 15000);
    return () => clearInterval(iv);
  }, []);

  if (!data) return <div className="section loading"><span className="spinner" />Loading errors...</div>;

  // Support both old health format and new service_health format
  const serviceHealth = data.service_health || {};
  const healthEntries: [string, HealthService][] = Object.keys(data.health || {}).length > 0
    ? Object.entries(data.health!)
    : Object.entries(serviceHealth).map(([name, status]) => [name, { status: status as string, failures: 0 }]);

  return (
    <div>
      {/* Service Health */}
      {healthEntries.length > 0 && (
        <div className="section">
          <h2><span className="section-icon">{"\u2665"}</span> Service Health</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
            {healthEntries.map(([name, svc]) => (
              <div className="stat-card" key={name}>
                <div className="label">{name}</div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div
                    className="status-dot"
                    style={{
                      background: svc.status === "operational" ? "var(--green)"
                        : svc.status === "degraded" ? "var(--yellow)"
                        : svc.status === "not_configured" ? "var(--orange)" : "var(--red)",
                      animation: "none",
                    }}
                  />
                  <span style={{
                    fontSize: 14, fontWeight: 700,
                    color: svc.status === "operational" ? "var(--green)"
                      : svc.status === "degraded" ? "var(--yellow)"
                      : svc.status === "not_configured" ? "var(--orange)" : "var(--red)",
                  }}>
                    {svc.status === "not_configured" ? "Not Configured" : svc.status}
                  </span>
                </div>
                {svc.failures > 0 && (
                  <div className="sub" style={{ color: "var(--red)" }}>
                    {svc.failures} consecutive failure{svc.failures > 1 ? "s" : ""}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error Count Summary */}
      <div className="section">
        <h2>
          <span className="section-icon">{"\u26A0"}</span>
          Recent Errors
          <span className="badge badge-high" style={{ marginLeft: 8 }}>{data.error_count}</span>
        </h2>

        {data.recent_errors.length === 0 ? (
          <div style={{ textAlign: "center", padding: 40, color: "var(--muted)" }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>{"\u2714"}</div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>No errors detected</div>
            <div style={{ fontSize: 13, marginTop: 4 }}>All systems running smoothly</div>
          </div>
        ) : (
          <div>
            {data.recent_errors.slice(0, 15).map((err, i) => {
              const time = err.timestamp ? new Date(err.timestamp).toLocaleString() : "";
              return (
                <div className="error-item" key={i}>
                  <div className="error-dot" />
                  <div className="error-content">
                    <div className="error-action">{err.action || "Unknown action"}</div>
                    <div className="error-detail">
                      {err.input_ref || ""} {err.error ? `- ${err.error}` : ""}
                    </div>
                  </div>
                  <div className="error-time">{time}</div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

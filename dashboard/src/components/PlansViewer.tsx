"use client";

import { useEffect, useState } from "react";

interface PlanStep {
  text: string;
  done: boolean;
}

interface Plan {
  filename: string;
  objective: string;
  status: string;
  priority: string;
  total_steps: number;
  completed_steps: number;
  created_at: string;
  source_file: string;
  steps: PlanStep[];
}

export default function PlansViewer() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/plans")
      .then((r) => r.json())
      .then((d) => setPlans(d.plans || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading"><span className="spinner" /> Loading plans...</div>;

  const statusColor: Record<string, string> = {
    active: "var(--green)",
    awaiting_approval: "var(--orange)",
    pending: "var(--yellow)",
    completed: "var(--blue)",
    done: "var(--blue)",
  };

  const priorityBadge: Record<string, string> = {
    high: "badge-high",
    medium: "badge-medium",
    low: "badge-low",
  };

  return (
    <div className="section">
      <h2><span className="section-icon">{"\uD83D\uDCC2"}</span> Active Plans</h2>
      {plans.length === 0 ? (
        <div style={{ color: "var(--muted)", padding: 20, textAlign: "center" }}>
          No active plans. Plans are created by the reasoning engine for complex tasks.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {plans.map((plan) => {
            const progress = plan.total_steps > 0 ? Math.round((plan.completed_steps / plan.total_steps) * 100) : 0;
            const isExpanded = expanded === plan.filename;

            return (
              <div
                key={plan.filename}
                style={{
                  background: "var(--bg)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-sm)",
                  padding: 16,
                  cursor: "pointer",
                }}
                onClick={() => setExpanded(isExpanded ? null : plan.filename)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{plan.objective}</div>
                    <div style={{ fontSize: 12, color: "var(--muted)", display: "flex", gap: 12, flexWrap: "wrap" }}>
                      <span>Source: {plan.source_file || "—"}</span>
                      {plan.created_at && <span>Created: {new Date(plan.created_at).toLocaleDateString()}</span>}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <span className={`badge ${priorityBadge[plan.priority] || "badge-medium"}`}>
                      {plan.priority}
                    </span>
                    <span
                      className="badge"
                      style={{
                        background: `${statusColor[plan.status] || "var(--muted)"}22`,
                        color: statusColor[plan.status] || "var(--muted)",
                      }}
                    >
                      {plan.status.replace(/_/g, " ")}
                    </span>
                  </div>
                </div>

                {/* Progress bar */}
                <div style={{ marginTop: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>
                    <span>{plan.completed_steps}/{plan.total_steps} steps</span>
                    <span>{progress}%</span>
                  </div>
                  <div style={{ height: 6, background: "var(--border)", borderRadius: 3, overflow: "hidden" }}>
                    <div
                      style={{
                        height: "100%",
                        width: `${progress}%`,
                        background: progress === 100 ? "var(--green)" : "var(--blue)",
                        borderRadius: 3,
                        transition: "width 0.3s",
                      }}
                    />
                  </div>
                </div>

                {/* Expanded steps */}
                {isExpanded && plan.steps.length > 0 && (
                  <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
                    {plan.steps.map((step, i) => (
                      <div
                        key={i}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 0",
                          fontSize: 13,
                          color: step.done ? "var(--green)" : "var(--text)",
                        }}
                      >
                        <span style={{ fontSize: 14 }}>{step.done ? "\u2713" : "\u25CB"}</span>
                        <span style={{ textDecoration: step.done ? "line-through" : "none", opacity: step.done ? 0.7 : 1 }}>
                          {step.text}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

"use client";

interface Props {
  status: {
    needs_action: number;
    plans: number;
    pending_approval: number;
    approved: number;
    done: number;
    archive: number;
    briefings: number;
  };
}

const cards = [
  { key: "needs_action", label: "Needs Action", color: "#ef4444" },
  { key: "plans", label: "Active Plans", color: "#eab308" },
  { key: "pending_approval", label: "Pending Approval", color: "#f97316" },
  { key: "approved", label: "Approved", color: "#3b82f6" },
  { key: "done", label: "Completed", color: "#22c55e" },
  { key: "archive", label: "Archived", color: "#6b7280" },
  { key: "briefings", label: "Briefings", color: "#a855f7" },
] as const;

export default function StatusCards({ status }: Props) {
  return (
    <div className="grid">
      {cards.map(({ key, label, color }) => (
        <div className="stat-card" key={key}>
          <div className="label">{label}</div>
          <div className="value" style={{ color }}>
            {status[key as keyof typeof status]}
          </div>
        </div>
      ))}
    </div>
  );
}

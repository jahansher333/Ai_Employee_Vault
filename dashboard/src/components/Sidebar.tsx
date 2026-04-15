"use client";

interface Props {
  active: string;
  onNavigate: (page: string) => void;
  counts: {
    needs_action: number;
    pending_approval: number;
    errors: number;
  };
}

const navItems = [
  { section: "Overview", items: [
    { id: "dashboard", icon: "\u2302", label: "Dashboard" },
    { id: "briefings", icon: "\uD83D\uDCCB", label: "Briefings" },
    { id: "analytics", icon: "\uD83D\uDCCA", label: "Data Analytics" },
  ]},
  { section: "Actions", items: [
    { id: "unified-inbox", icon: "\uD83D\uDCE8", label: "Unified Inbox" },
    { id: "autopilot", icon: "\u26A1", label: "Autopilot" },
    { id: "social", icon: "\u266A", label: "Social Media" },
    { id: "engagement", icon: "\uD83D\uDCAC", label: "Engagement" },
    { id: "messaging", icon: "\u2709", label: "Email & WhatsApp" },
    { id: "autoreply", icon: "\u21A9", label: "Auto-Reply" },
    { id: "approvals", icon: "\u2713", label: "Approvals" },
  ]},
  { section: "Monitor", items: [
    { id: "tasks", icon: "\u2630", label: "Tasks" },
    { id: "plans", icon: "\uD83D\uDCC2", label: "Plans" },
    { id: "completed", icon: "\u2714", label: "Completed" },
    { id: "inbox", icon: "\uD83D\uDCE5", label: "Inbox Monitor" },
    { id: "errors", icon: "\u26A0", label: "Error Recovery" },
    { id: "financial", icon: "$", label: "Financial" },
    { id: "invoices", icon: "\uD83D\uDCC4", label: "Invoices" },
    { id: "archive", icon: "\uD83D\uDDC4", label: "Archive" },
    { id: "audit", icon: "\u2261", label: "Audit Log" },
  ]},
  { section: "System", items: [
    { id: "slack", icon: "#", label: "Slack" },
    { id: "settings", icon: "\u2699", label: "Settings" },
  ]},
];

export default function Sidebar({ active, onNavigate, counts }: Props) {
  const badgeCounts: Record<string, number> = {
    tasks: counts.needs_action,
    approvals: counts.pending_approval,
    errors: counts.errors,
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <img src="/logo.svg" alt="AI Employee" width={36} height={36} style={{ borderRadius: 8 }} />
          <div>
            <h1>AI Employee</h1>
            <p>Autonomous Business System</p>
          </div>
        </div>
      </div>
      <nav className="sidebar-nav">
        {navItems.map((section) => (
          <div className="nav-section" key={section.section}>
            <div className="nav-section-label">{section.section}</div>
            {section.items.map((item) => (
              <div
                key={item.id}
                className={`nav-item ${active === item.id ? "active" : ""}`}
                onClick={() => onNavigate(item.id)}
              >
                <span className="nav-icon">{item.icon}</span>
                <span>{item.label}</span>
                {badgeCounts[item.id] > 0 && (
                  <span className="nav-badge">{badgeCounts[item.id]}</span>
                )}
              </div>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  );
}

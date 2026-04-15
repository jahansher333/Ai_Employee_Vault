"use client";

import { useCallback, useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import ToastContainer, { ToastMessage } from "@/components/Toast";
import StatusCards from "@/components/StatusCards";
import FinancialSection from "@/components/FinancialSection";
import TasksTable from "@/components/TasksTable";
import ApprovalsTable from "@/components/ApprovalsTable";
import SocialSection from "@/components/SocialSection";
import AuditLog from "@/components/AuditLog";
import InventorySection from "@/components/InventorySection";
import SocialPostForm from "@/components/SocialPostForm";
import MessagingForm from "@/components/MessagingForm";
import ErrorRecovery from "@/components/ErrorRecovery";
import ApprovalsManager from "@/components/ApprovalsManager";
import BriefingsViewer from "@/components/BriefingsViewer";
import PlansViewer from "@/components/PlansViewer";
import CompletedItems from "@/components/CompletedItems";
import AutoReplyManager from "@/components/AutoReplyManager";
import SettingsPage from "@/components/SettingsPage";
import DataAnalytics from "@/components/DataAnalytics";
import SocialEngagement from "@/components/SocialEngagement";
import SlackConfig from "@/components/SlackConfig";
import InvoiceManager from "@/components/InvoiceManager";
import BulkArchive from "@/components/BulkArchive";
import InboxMonitor from "@/components/InboxMonitor";
import UnifiedInbox from "@/components/UnifiedInbox";
import Autopilot from "@/components/Autopilot";

interface Status {
  needs_action: number;
  plans: number;
  pending_approval: number;
  approved: number;
  done: number;
  archive: number;
  briefings: number;
  timestamp: string;
}

interface OrchestratorStatus {
  running: boolean;
  pid: number | null;
}

export default function Home() {
  const [page, setPage] = useState("dashboard");
  const [status, setStatus] = useState<Status | null>(null);
  const [orchStatus, setOrchStatus] = useState<OrchestratorStatus>({ running: false, pid: null });
  const [orchLoading, setOrchLoading] = useState(false);
  const [apiOnline, setApiOnline] = useState(false);
  const [lastUpdate, setLastUpdate] = useState("");
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [errorCount, setErrorCount] = useState(0);

  const addToast = useCallback((type: "success" | "error", text: string) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, type, text }]);
  }, []);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Fetch status
  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [statusRes, orchRes, errRes] = await Promise.all([
          fetch("/api/status"),
          fetch("/api/orchestrator/status"),
          fetch("/api/errors"),
        ]);
        if (statusRes.ok) {
          const data = await statusRes.json();
          setStatus(data);
          setApiOnline(true);
          setLastUpdate(new Date().toLocaleTimeString());
        }
        if (orchRes.ok) {
          setOrchStatus(await orchRes.json());
        }
        if (errRes.ok) {
          const errData = await errRes.json();
          setErrorCount(errData.error_count || 0);
        }
      } catch {
        setApiOnline(false);
      }
    };

    fetchAll();
    const iv = setInterval(fetchAll, 10000);
    return () => clearInterval(iv);
  }, []);

  // Orchestrator start/stop
  const handleOrchestrator = async () => {
    setOrchLoading(true);
    const endpoint = orchStatus.running ? "/api/orchestrator/stop" : "/api/orchestrator/start";
    try {
      const res = await fetch(endpoint, { method: "POST" });
      const result = await res.json();
      if (result.success) {
        addToast("success", result.message);
        setOrchStatus({ running: !orchStatus.running, pid: result.pid || null });
      } else {
        addToast("error", result.error || "Failed");
      }
    } catch {
      addToast("error", "Network error");
    }
    setOrchLoading(false);
  };

  // Page titles
  const pageTitles: Record<string, { title: string; sub: string }> = {
    dashboard: { title: "Dashboard", sub: "Real-time system overview" },
    "unified-inbox": { title: "Unified Inbox", sub: "All emails, WhatsApp messages & comments — reply with AI" },
    autopilot: { title: "Autopilot", sub: "Auto-post & auto-reply every 2 days — Facebook, Instagram, LinkedIn, Email, WhatsApp" },
    briefings: { title: "Briefings", sub: "Weekly CEO briefings and executive summaries" },
    analytics: { title: "Data Analytics", sub: "CSV financial analysis, anomaly detection & trends" },
    social: { title: "Social Media", sub: "Post to Facebook, Instagram, Twitter & LinkedIn" },
    engagement: { title: "Social Engagement", sub: "Monitor comments & replies across all platforms" },
    messaging: { title: "Messaging", sub: "Send emails and WhatsApp messages" },
    autoreply: { title: "Auto-Reply", sub: "Manage email auto-reply templates" },
    approvals: { title: "Approvals", sub: "Review and approve pending items" },
    tasks: { title: "Tasks", sub: "Monitor incoming tasks" },
    plans: { title: "Plans", sub: "Active reasoning plans and execution progress" },
    completed: { title: "Completed", sub: "History of all completed tasks and posts" },
    inbox: { title: "Inbox Monitor", sub: "Gmail, WhatsApp & Telegram watcher status" },
    errors: { title: "Error Recovery", sub: "System health and error tracking" },
    financial: { title: "Financial", sub: "Revenue, expenses and invoices" },
    invoices: { title: "Invoices", sub: "PDF invoice generation and export" },
    archive: { title: "Archive", sub: "Manage stale tasks and bulk archival" },
    audit: { title: "Audit Log", sub: "Complete activity history" },
    slack: { title: "Slack", sub: "Notification configuration and history" },
    settings: { title: "Settings", sub: "System configuration and service status" },
  };

  const currentPage = pageTitles[page] || pageTitles.dashboard;

  return (
    <div className="app-layout">
      <Sidebar
        active={page}
        onNavigate={setPage}
        counts={{
          needs_action: status?.needs_action || 0,
          pending_approval: status?.pending_approval || 0,
          errors: errorCount,
        }}
      />

      <main className="main-content">
        {/* Top Bar */}
        <div className="topbar">
          <div className="topbar-left">
            <h2>{currentPage.title}</h2>
            <p>{currentPage.sub}</p>
          </div>
          <div className="topbar-right">
            <div className={`status-dot ${apiOnline ? "" : "offline"}`} />
            <span className="status-text">
              {apiOnline ? `Live \u2022 ${lastUpdate}` : "API Offline"}
            </span>
            <button
              className={`btn-start ${orchStatus.running ? "stop" : "start"}`}
              onClick={handleOrchestrator}
              disabled={orchLoading || !apiOnline}
            >
              {orchLoading ? (
                <><span className="spinner" style={{ width: 14, height: 14, borderWidth: 2, marginRight: 0 }} /> Working...</>
              ) : orchStatus.running ? (
                <>{"\u25A0"} Stop System</>
              ) : (
                <>{"\u25B6"} Start System</>
              )}
            </button>
          </div>
        </div>

        {/* API Offline Warning */}
        {!apiOnline && (
          <div className="section" style={{ borderColor: "var(--red)", background: "var(--red-dim)", marginBottom: 24 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 24 }}>{"\u26A0"}</span>
              <div>
                <div style={{ fontWeight: 700 }}>API Server Not Reachable</div>
                <div style={{ fontSize: 13, color: "var(--muted)", marginTop: 2 }}>
                  Start the backend: <code style={{ background: "var(--bg)", padding: "2px 8px", borderRadius: 4 }}>
                    python scripts/api_server.py
                  </code>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Page Content */}
        {page === "dashboard" && (
          <>
            {status && <StatusCards status={status} />}
            <FinancialSection />
            <div className="two-col">
              <TasksTable />
              <ApprovalsTable />
            </div>
            <div className="two-col">
              <InventorySection />
              <SocialSection />
            </div>
            <AuditLog />
          </>
        )}

        {page === "unified-inbox" && <UnifiedInbox onToast={addToast} />}

        {page === "autopilot" && <Autopilot onToast={addToast} />}

        {page === "briefings" && <BriefingsViewer />}

        {page === "analytics" && <DataAnalytics />}

        {page === "social" && <SocialPostForm onToast={addToast} />}

        {page === "engagement" && <SocialEngagement />}

        {page === "messaging" && <MessagingForm onToast={addToast} />}

        {page === "autoreply" && <AutoReplyManager onToast={addToast} />}

        {page === "approvals" && <ApprovalsManager onToast={addToast} />}

        {page === "tasks" && (
          <>
            {status && (
              <div className="grid" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
                <div className="stat-card">
                  <div className="label">Needs Action</div>
                  <div className="value" style={{ color: "var(--red)" }}>{status.needs_action}</div>
                </div>
                <div className="stat-card">
                  <div className="label">Active Plans</div>
                  <div className="value" style={{ color: "var(--yellow)" }}>{status.plans}</div>
                </div>
                <div className="stat-card">
                  <div className="label">In Approval</div>
                  <div className="value" style={{ color: "var(--orange)" }}>{status.pending_approval}</div>
                </div>
                <div className="stat-card">
                  <div className="label">Completed</div>
                  <div className="value" style={{ color: "var(--green)" }}>{status.done}</div>
                </div>
              </div>
            )}
            <TasksTable />
          </>
        )}

        {page === "plans" && <PlansViewer />}

        {page === "completed" && <CompletedItems />}

        {page === "inbox" && <InboxMonitor />}

        {page === "errors" && <ErrorRecovery />}

        {page === "financial" && (
          <>
            <FinancialSection />
            <InventorySection />
          </>
        )}

        {page === "invoices" && <InvoiceManager onToast={addToast} />}

        {page === "archive" && <BulkArchive onToast={addToast} />}

        {page === "audit" && <AuditLog />}

        {page === "slack" && <SlackConfig onToast={addToast} />}

        {page === "settings" && <SettingsPage orchStatus={orchStatus} apiOnline={apiOnline} />}
      </main>

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}

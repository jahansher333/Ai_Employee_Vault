"use client";

import { useEffect, useState } from "react";
import StatusCards from "@/components/StatusCards";
import FinancialSection from "@/components/FinancialSection";
import TasksTable from "@/components/TasksTable";
import ApprovalsTable from "@/components/ApprovalsTable";
import InventorySection from "@/components/InventorySection";
import SocialSection from "@/components/SocialSection";
import AuditLog from "@/components/AuditLog";

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

export default function Home() {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState("");
  const [lastUpdate, setLastUpdate] = useState("");

  const fetchStatus = async () => {
    try {
      const res = await fetch("/api/status");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStatus(data);
      setLastUpdate(new Date().toLocaleTimeString());
      setError("");
    } catch (e) {
      setError("API not reachable. Start: python scripts/api_server.py");
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="dashboard">
      <header className="header">
        <div>
          <h1>AI Employee Dashboard</h1>
          <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 4 }}>
            Real-time monitoring & management
          </p>
        </div>
        <div style={{ textAlign: "right" }}>
          {error ? (
            <span className="error">{error}</span>
          ) : (
            <>
              <span className="status">LIVE</span>
              <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 4 }}>
                Updated: {lastUpdate}
              </p>
            </>
          )}
        </div>
      </header>

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
    </div>
  );
}

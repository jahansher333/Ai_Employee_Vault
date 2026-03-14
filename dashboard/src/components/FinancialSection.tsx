"use client";

import { useEffect, useState } from "react";

interface Financial {
  source: string;
  success: boolean;
  total_revenue?: number;
  total_expenses?: number;
  net_income?: number;
  outstanding_invoices?: number;
  overdue_amount?: number;
  overdue_count?: number;
  currency?: string;
  overdue_invoices?: Array<{
    name: string;
    partner: string;
    amount: number;
    due: string;
  }>;
}

function fmt(n: number | undefined, currency = "USD") {
  if (n === undefined) return "$0.00";
  return `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function FinancialSection() {
  const [data, setData] = useState<Financial | null>(null);

  useEffect(() => {
    fetch("/api/financial")
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData({ source: "error", success: false }));
  }, []);

  if (!data) return <div className="section loading">Loading financials...</div>;
  if (!data.success) return <div className="section"><h2>Financial Overview</h2><p style={{color:"var(--muted)"}}>Odoo not connected</p></div>;

  return (
    <div className="section">
      <h2>Financial Overview <span style={{fontSize:12,color:"var(--muted)"}}>({data.source})</span></h2>
      <div className="grid" style={{ gridTemplateColumns: "repeat(5, 1fr)" }}>
        <div className="stat-card">
          <div className="label">Revenue</div>
          <div className="value" style={{ fontSize: 22, color: "var(--green)" }}>{fmt(data.total_revenue)}</div>
        </div>
        <div className="stat-card">
          <div className="label">Expenses</div>
          <div className="value" style={{ fontSize: 22, color: "var(--red)" }}>{fmt(data.total_expenses)}</div>
        </div>
        <div className="stat-card">
          <div className="label">Net Income</div>
          <div className="value" style={{ fontSize: 22, color: "var(--blue)" }}>{fmt(data.net_income)}</div>
        </div>
        <div className="stat-card">
          <div className="label">Outstanding</div>
          <div className="value" style={{ fontSize: 22, color: "var(--yellow)" }}>{fmt(data.outstanding_invoices)}</div>
        </div>
        <div className="stat-card">
          <div className="label">Overdue</div>
          <div className="value" style={{ fontSize: 22, color: "var(--red)" }}>
            {data.overdue_count || 0}
          </div>
          <div className="sub">{fmt(data.overdue_amount)}</div>
        </div>
      </div>

      {data.overdue_invoices && data.overdue_invoices.length > 0 && (
        <>
          <h3 style={{ fontSize: 14, color: "var(--red)", margin: "16px 0 8px" }}>
            Overdue Invoices
          </h3>
          <table>
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Customer</th>
                <th>Amount</th>
                <th>Due Date</th>
              </tr>
            </thead>
            <tbody>
              {data.overdue_invoices.map((inv) => (
                <tr key={inv.name}>
                  <td>{inv.name}</td>
                  <td>{inv.partner}</td>
                  <td style={{ color: "var(--red)" }}>{fmt(inv.amount)}</td>
                  <td><span className="badge badge-overdue">{inv.due}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";

interface MonthlyData {
  month: string;
  revenue: number;
  expenses: number;
  net: number;
  transaction_count: number;
}

interface CategoryData {
  category: string;
  total: number;
  count: number;
  type: string;
}

interface TopExpense {
  date: string;
  description: string;
  amount: number;
  category: string;
}

interface Anomaly {
  date: string;
  description: string;
  amount: number;
  category: string;
  category_avg: number;
  ratio: number;
}

interface AnalyticsData {
  success: boolean;
  total_revenue: number;
  total_expenses: number;
  net_income: number;
  transaction_count: number;
  monthly_breakdown: MonthlyData[];
  category_breakdown: CategoryData[];
  top_expenses: TopExpense[];
  anomalies: Anomaly[];
  files_analyzed: string[];
  generated_at: string;
  error?: string;
}

function fmt(n: number) {
  return `$${Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function DataAnalytics() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [csvText, setCsvText] = useState("");
  const [fileName, setFileName] = useState("");
  const [saveToVault, setSaveToVault] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState("");
  const [showForm, setShowForm] = useState(false);

  const loadExisting = () => {
    setLoading(true);
    fetch("/api/analytics")
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadExisting(); }, []);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name.replace(/\.csv$/, ""));
    const reader = new FileReader();
    reader.onload = (ev) => {
      setCsvText(ev.target?.result as string || "");
    };
    reader.readAsText(file);
  };

  const handleAnalyze = async () => {
    if (!csvText.trim()) { setAnalyzeError("CSV data is empty"); return; }
    setAnalyzing(true);
    setAnalyzeError("");
    try {
      const res = await fetch("/api/analytics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          csv: csvText,
          save_as: saveToVault ? (fileName || `upload-${Date.now()}`) : "",
        }),
      });
      const result = await res.json();
      if (result.success) {
        setData(result);
        setShowForm(false);
        setCsvText("");
        setFileName("");
      } else {
        setAnalyzeError(result.error || "Analysis failed");
      }
    } catch {
      setAnalyzeError("Network error");
    }
    setAnalyzing(false);
  };

  const sampleCSV = `date,description,amount,category
2026-01-05,Client Payment,8500.00,Revenue
2026-01-10,Office Rent,-1500.00,Operations
2026-01-15,Software License,-299.99,Technology
2026-01-20,Freelance Income,3200.00,Revenue
2026-01-25,Marketing Ads,-750.00,Marketing`;

  if (loading) return <div className="loading"><span className="spinner" /> Loading analytics...</div>;

  // Find max monthly revenue for bar chart scale
  const maxMonthly = data?.success ? Math.max(...data.monthly_breakdown.map((m) => Math.max(m.revenue, m.expenses)), 1) : 1;

  return (
    <>
      {/* Analyze Form Toggle */}
      <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
        <button
          className={`btn ${showForm ? "btn-danger" : "btn-primary"}`}
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? "\u2715 Close Form" : "\uD83D\uDCCA Analyze New Data"}
        </button>
        {data?.success && (
          <button className="btn" onClick={loadExisting}>
            Reload Accounting/ Data
          </button>
        )}
      </div>

      {/* Analyze Form */}
      {showForm && (
        <div className="section" style={{ marginBottom: 24, borderColor: "var(--blue)" }}>
          <h2><span className="section-icon">{"\uD83D\uDCCA"}</span> Analyze Financial Data</h2>

          {/* File Upload */}
          <div className="form-group">
            <label>Upload CSV File</label>
            <input
              type="file"
              accept=".csv"
              onChange={handleFileUpload}
              style={{
                width: "100%", padding: "10px 14px",
                background: "var(--bg)", border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)", color: "var(--text)",
                fontSize: 14, cursor: "pointer",
              }}
            />
          </div>

          {/* Or Paste CSV */}
          <div className="form-group">
            <label>Or Paste CSV Data</label>
            <textarea
              className="form-input"
              value={csvText}
              onChange={(e) => setCsvText(e.target.value)}
              placeholder="date,description,amount,category&#10;2026-01-05,Client Payment,8500.00,Revenue&#10;2026-01-10,Office Rent,-1500.00,Operations"
              style={{ minHeight: 160, fontFamily: "monospace", fontSize: 13 }}
            />
          </div>

          {/* Sample Button */}
          <div style={{ marginBottom: 16 }}>
            <button
              className="btn btn-sm"
              onClick={() => { setCsvText(sampleCSV); setFileName("sample-data"); }}
            >
              Load Sample Data
            </button>
            <span style={{ fontSize: 12, color: "var(--muted)", marginLeft: 12 }}>
              Required columns: <strong>amount</strong>. Optional: date, description, category
            </span>
          </div>

          {/* Save option */}
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 13 }}>
              <input
                type="checkbox"
                checked={saveToVault}
                onChange={(e) => setSaveToVault(e.target.checked)}
                style={{ accentColor: "var(--blue)" }}
              />
              Save to Accounting/ folder
            </label>
            {saveToVault && (
              <input
                className="form-input"
                value={fileName}
                onChange={(e) => setFileName(e.target.value)}
                placeholder="filename (without .csv)"
                style={{ maxWidth: 250, padding: "6px 12px" }}
              />
            )}
          </div>

          {/* Error */}
          {analyzeError && (
            <div style={{ color: "var(--red)", fontSize: 13, marginBottom: 12, padding: "8px 12px", background: "var(--red-dim)", borderRadius: "var(--radius-sm)" }}>
              {analyzeError}
            </div>
          )}

          {/* Submit */}
          <button
            className="btn btn-success"
            onClick={handleAnalyze}
            disabled={analyzing || !csvText.trim()}
          >
            {analyzing ? <><span className="spinner" style={{ width: 14, height: 14, borderWidth: 2, marginRight: 8 }} /> Analyzing...</> : "\uD83D\uDD0D Analyze Data"}
          </button>

          {/* Preview */}
          {csvText && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>
                Preview ({csvText.trim().split("\n").length - 1} rows detected)
              </div>
              <div style={{
                background: "var(--bg)", border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)", padding: 12,
                maxHeight: 120, overflow: "auto", fontFamily: "monospace", fontSize: 12,
                whiteSpace: "pre", color: "var(--muted)",
              }}>
                {csvText.trim().split("\n").slice(0, 6).join("\n")}
                {csvText.trim().split("\n").length > 6 && `\n... +${csvText.trim().split("\n").length - 6} more rows`}
              </div>
            </div>
          )}
        </div>
      )}

      {/* No data state */}
      {(!data || !data.success) && !showForm && (
        <div className="section">
          <h2><span className="section-icon">{"\uD83D\uDCCA"}</span> Data Analytics</h2>
          <div style={{ color: "var(--muted)", padding: 20, textAlign: "center" }}>
            {data?.error || "No CSV data found in Accounting/ folder."}
            <div style={{ fontSize: 12, marginTop: 8 }}>
              Click <strong>Analyze New Data</strong> above to upload or paste CSV data
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {data?.success && (
        <>
      {/* Summary Cards */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 24 }}>
        <div className="stat-card">
          <div className="label">Total Revenue</div>
          <div className="value" style={{ color: "var(--green)", fontSize: 22 }}>{fmt(data.total_revenue)}</div>
          <div className="sub">{data.files_analyzed.length} file(s) analyzed</div>
        </div>
        <div className="stat-card">
          <div className="label">Total Expenses</div>
          <div className="value" style={{ color: "var(--red)", fontSize: 22 }}>{fmt(data.total_expenses)}</div>
        </div>
        <div className="stat-card">
          <div className="label">Net Income</div>
          <div className="value" style={{ color: data.net_income >= 0 ? "var(--green)" : "var(--red)", fontSize: 22 }}>
            {data.net_income >= 0 ? "" : "-"}{fmt(data.net_income)}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">Anomalies</div>
          <div className="value" style={{ color: data.anomalies.length > 0 ? "var(--orange)" : "var(--green)", fontSize: 22 }}>
            {data.anomalies.length}
          </div>
          <div className="sub">{data.transaction_count} transactions</div>
        </div>
      </div>

      {/* Monthly Breakdown with Bar Chart */}
      <div className="section">
        <h2><span className="section-icon">{"\uD83D\uDCC8"}</span> Monthly Breakdown</h2>
        {data.monthly_breakdown.length === 0 ? (
          <div style={{ color: "var(--muted)", padding: 20 }}>No monthly data available</div>
        ) : (
          <>
            {/* Visual bar chart */}
            <div style={{ marginBottom: 20 }}>
              {data.monthly_breakdown.map((m) => (
                <div key={m.month} style={{ marginBottom: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, color: "var(--text)" }}>{m.month}</span>
                    <span>Net: <span style={{ color: m.net >= 0 ? "var(--green)" : "var(--red)" }}>{fmt(m.net)}</span></span>
                  </div>
                  <div style={{ display: "flex", gap: 4, height: 20 }}>
                    <div
                      style={{
                        height: "100%",
                        width: `${(m.revenue / maxMonthly) * 100}%`,
                        background: "var(--green)",
                        borderRadius: 3,
                        minWidth: m.revenue > 0 ? 4 : 0,
                        opacity: 0.7,
                      }}
                      title={`Revenue: ${fmt(m.revenue)}`}
                    />
                    <div
                      style={{
                        height: "100%",
                        width: `${(m.expenses / maxMonthly) * 100}%`,
                        background: "var(--red)",
                        borderRadius: 3,
                        minWidth: m.expenses > 0 ? 4 : 0,
                        opacity: 0.7,
                      }}
                      title={`Expenses: ${fmt(m.expenses)}`}
                    />
                  </div>
                </div>
              ))}
              <div style={{ display: "flex", gap: 16, marginTop: 8, fontSize: 11, color: "var(--muted)" }}>
                <span><span style={{ display: "inline-block", width: 10, height: 10, background: "var(--green)", borderRadius: 2, marginRight: 4, opacity: 0.7 }} />Revenue</span>
                <span><span style={{ display: "inline-block", width: 10, height: 10, background: "var(--red)", borderRadius: 2, marginRight: 4, opacity: 0.7 }} />Expenses</span>
              </div>
            </div>

            {/* Data table */}
            <table>
              <thead>
                <tr>
                  <th>Month</th>
                  <th>Revenue</th>
                  <th>Expenses</th>
                  <th>Net</th>
                  <th>Transactions</th>
                </tr>
              </thead>
              <tbody>
                {data.monthly_breakdown.map((m) => (
                  <tr key={m.month}>
                    <td style={{ fontWeight: 600 }}>{m.month}</td>
                    <td style={{ color: "var(--green)" }}>{fmt(m.revenue)}</td>
                    <td style={{ color: "var(--red)" }}>{fmt(m.expenses)}</td>
                    <td style={{ color: m.net >= 0 ? "var(--green)" : "var(--red)", fontWeight: 600 }}>
                      {m.net >= 0 ? "" : "-"}{fmt(m.net)}
                    </td>
                    <td style={{ color: "var(--muted)" }}>{m.transaction_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>

      <div className="two-col">
        {/* Category Breakdown */}
        <div className="section">
          <h2><span className="section-icon">{"\uD83C\uDFF7"}</span> By Category</h2>
          {data.category_breakdown.length === 0 ? (
            <div style={{ color: "var(--muted)" }}>No category data</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {data.category_breakdown.map((c) => {
                const maxCat = Math.max(...data.category_breakdown.map((cc) => Math.abs(cc.total)), 1);
                return (
                  <div key={c.category} style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: "8px 12px", background: "var(--bg)", borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border)",
                  }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{c.category}</div>
                      <div style={{ fontSize: 11, color: "var(--muted)" }}>{c.count} transactions</div>
                    </div>
                    <div style={{ width: 100, height: 6, background: "var(--border)", borderRadius: 3, overflow: "hidden" }}>
                      <div style={{
                        height: "100%",
                        width: `${(Math.abs(c.total) / maxCat) * 100}%`,
                        background: c.total >= 0 ? "var(--green)" : "var(--red)",
                        borderRadius: 3,
                      }} />
                    </div>
                    <span style={{ color: c.total >= 0 ? "var(--green)" : "var(--red)", fontWeight: 600, fontSize: 13, minWidth: 80, textAlign: "right" }}>
                      {c.total >= 0 ? "+" : "-"}{fmt(c.total)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Top 5 Expenses */}
        <div className="section">
          <h2><span className="section-icon">{"\uD83D\uDCB8"}</span> Top 5 Expenses</h2>
          {data.top_expenses.length === 0 ? (
            <div style={{ color: "var(--muted)" }}>No expense data</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Description</th>
                  <th>Amount</th>
                  <th>Category</th>
                </tr>
              </thead>
              <tbody>
                {data.top_expenses.map((e, i) => (
                  <tr key={i}>
                    <td style={{ color: "var(--muted)", fontSize: 12 }}>{e.date}</td>
                    <td style={{ fontWeight: 500 }}>{e.description}</td>
                    <td style={{ color: "var(--red)", fontWeight: 600 }}>{fmt(e.amount)}</td>
                    <td><span className="badge badge-info">{e.category}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Anomalies */}
      <div className="section">
        <h2>
          <span className="section-icon">{"\u26A0"}</span> Anomaly Detection
          <span style={{ fontSize: 12, fontWeight: 400, color: "var(--muted)", marginLeft: 8 }}>
            Transactions {">"}2x category average
          </span>
        </h2>
        {data.anomalies.length === 0 ? (
          <div style={{ color: "var(--green)", padding: 16, textAlign: "center", background: "var(--green-dim)", borderRadius: "var(--radius-sm)" }}>
            No anomalies detected. All transactions within normal range.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Description</th>
                <th>Amount</th>
                <th>Category</th>
                <th>Category Avg</th>
                <th>Ratio</th>
              </tr>
            </thead>
            <tbody>
              {data.anomalies.map((a, i) => (
                <tr key={i}>
                  <td style={{ color: "var(--muted)", fontSize: 12 }}>{a.date}</td>
                  <td style={{ fontWeight: 500 }}>{a.description}</td>
                  <td style={{ color: "var(--orange)", fontWeight: 600 }}>{fmt(a.amount)}</td>
                  <td><span className="badge badge-info">{a.category}</span></td>
                  <td style={{ color: "var(--muted)" }}>{fmt(a.category_avg)}</td>
                  <td>
                    <span className="badge badge-high">{a.ratio}x</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Files Analyzed */}
      <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 8, textAlign: "right" }}>
        Generated: {new Date(data.generated_at).toLocaleString()} | Files: {data.files_analyzed.join(", ")}
      </div>
        </>
      )}
    </>
  );
}

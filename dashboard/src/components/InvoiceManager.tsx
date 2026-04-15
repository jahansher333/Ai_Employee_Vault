"use client";

import { useEffect, useState } from "react";

interface Invoice {
  filename: string;
  size: number;
  created: string;
  name: string;
}

interface Props {
  onToast?: (type: "success" | "error", text: string) => void;
}

export default function InvoiceManager({ onToast }: Props = {}) {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [invoiceName, setInvoiceName] = useState("");

  const toast = (type: "success" | "error", text: string) => {
    if (onToast) onToast(type, text);
  };

  const fetchInvoices = () => {
    fetch("/api/invoices")
      .then((r) => r.json())
      .then((d) => setInvoices(d.invoices || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchInvoices(); }, []);

  const handleDownload = (filename: string) => {
    const a = document.createElement("a");
    a.href = `/api/invoices/download?file=${encodeURIComponent(filename)}`;
    a.download = filename;
    a.click();
  };

  const handleGenerate = async (overdue = false) => {
    setGenerating(true);
    try {
      const res = await fetch("/api/invoices/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(overdue ? { overdue: true } : { invoice: invoiceName }),
      });
      const result = await res.json();
      if (result.success) {
        toast("success", overdue ? "Overdue invoices generated!" : `PDF generated: ${invoiceName}`);
        setInvoiceName("");
        fetchInvoices();
      } else {
        toast("error", result.error || "Generation failed");
      }
    } catch {
      toast("error", "Network error");
    }
    setGenerating(false);
  };

  if (loading) return <div className="loading"><span className="spinner" /> Loading invoices...</div>;

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  return (
    <>
      {/* Stats */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: 24 }}>
        <div className="stat-card">
          <div className="label">PDF Invoices</div>
          <div className="value" style={{ color: "var(--blue)" }}>{invoices.length}</div>
          <div className="sub">in Invoices/ folder</div>
        </div>
        <div className="stat-card">
          <div className="label">Total Size</div>
          <div className="value" style={{ fontSize: 20 }}>
            {formatSize(invoices.reduce((s, i) => s + i.size, 0))}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">Latest</div>
          <div className="value" style={{ fontSize: 16, color: "var(--muted)" }}>
            {invoices.length > 0 ? new Date(invoices[0].created).toLocaleDateString() : "—"}
          </div>
        </div>
      </div>

      {/* Generate PDF Section */}
      <div className="section" style={{ marginBottom: 24 }}>
        <h2><span className="section-icon">{"\uD83D\uDCC4"}</span> Generate PDF Invoice</h2>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <input
            className="form-input"
            placeholder="Invoice name, e.g. INV/2026/00001"
            value={invoiceName}
            onChange={(e) => setInvoiceName(e.target.value)}
            style={{ flex: 1, minWidth: 250, padding: "10px 14px" }}
          />
          <button
            className="btn btn-primary"
            onClick={() => handleGenerate(false)}
            disabled={generating || !invoiceName.trim()}
          >
            {generating ? "Generating..." : "Generate PDF"}
          </button>
          <button
            className="btn btn-danger"
            onClick={() => handleGenerate(true)}
            disabled={generating}
          >
            {generating ? "Generating..." : "Export All Overdue"}
          </button>
        </div>
      </div>

      {/* Invoice List */}
      <div className="section">
        <h2><span className="section-icon">{"\uD83D\uDCE4"}</span> Generated Invoices</h2>
        {invoices.length === 0 ? (
          <div style={{ color: "var(--muted)", padding: 20, textAlign: "center" }}>
            <div>No PDF invoices generated yet.</div>
            <div style={{ fontSize: 12, marginTop: 8 }}>
              Use the form above to generate invoices from Odoo data.
            </div>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Invoice</th>
                <th>File</th>
                <th>Size</th>
                <th>Generated</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.filename}>
                  <td style={{ fontWeight: 600 }}>{inv.name}</td>
                  <td style={{ color: "var(--muted)", fontSize: 12 }}>{inv.filename}</td>
                  <td style={{ color: "var(--muted)" }}>{formatSize(inv.size)}</td>
                  <td style={{ color: "var(--muted)", fontSize: 12 }}>
                    {new Date(inv.created).toLocaleString()}
                  </td>
                  <td>
                    <button
                      className="btn btn-sm btn-success"
                      onClick={() => handleDownload(inv.filename)}
                      style={{ padding: "4px 12px", fontSize: 12 }}
                    >
                      Download PDF
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

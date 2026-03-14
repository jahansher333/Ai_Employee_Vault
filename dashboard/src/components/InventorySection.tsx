"use client";

import { useEffect, useState } from "react";

interface InventoryData {
  success: boolean;
  summary?: {
    total_products: number;
    total_value: number;
    low_stock_count: number;
    out_of_stock_count: number;
  };
  low_stock?: Array<{
    name: string;
    qty_available: number;
    price: number;
  }>;
}

export default function InventorySection() {
  const [data, setData] = useState<InventoryData | null>(null);

  useEffect(() => {
    fetch("/api/inventory")
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData({ success: false }));
  }, []);

  if (!data) return <div className="section loading">Loading inventory...</div>;
  if (!data.success || !data.summary) return (
    <div className="section"><h2>Inventory</h2><p style={{color:"var(--muted)"}}>Not available</p></div>
  );

  const s = data.summary;

  return (
    <div className="section">
      <h2>Inventory</h2>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
        <div className="stat-card">
          <div className="label">Products</div>
          <div className="value" style={{ fontSize: 20 }}>{s.total_products}</div>
        </div>
        <div className="stat-card">
          <div className="label">Total Value</div>
          <div className="value" style={{ fontSize: 20 }}>
            ${s.total_value.toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">Low Stock</div>
          <div className="value" style={{ fontSize: 20, color: "var(--yellow)" }}>{s.low_stock_count}</div>
        </div>
        <div className="stat-card">
          <div className="label">Out of Stock</div>
          <div className="value" style={{ fontSize: 20, color: "var(--red)" }}>{s.out_of_stock_count}</div>
        </div>
      </div>

      {data.low_stock && data.low_stock.length > 0 && (
        <table>
          <thead>
            <tr><th>Product</th><th>Stock</th><th>Price</th></tr>
          </thead>
          <tbody>
            {data.low_stock.slice(0, 5).map((p, i) => (
              <tr key={`${p.name}-${i}`}>
                <td>{p.name}</td>
                <td style={{ color: p.qty_available <= 0 ? "var(--red)" : "var(--yellow)" }}>
                  {p.qty_available <= 0 ? "OUT" : p.qty_available}
                </td>
                <td>${p.price.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

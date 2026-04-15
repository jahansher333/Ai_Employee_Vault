"use client";

import { useEffect, useState } from "react";

interface FileInfo {
  filename: string;
  folder: string;
  path: string;
  age_hours: number;
  modified: string;
}

interface ArchiveData {
  stale_files: FileInfo[];
  recent_files: FileInfo[];
  stale_count: number;
  recent_count: number;
  archived_count: number;
  age_threshold: number;
}

interface Props {
  onToast?: (type: "success" | "error", text: string) => void;
}

export default function BulkArchive({ onToast }: Props = {}) {
  const [data, setData] = useState<ArchiveData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [acting, setActing] = useState(false);

  const toast = (type: "success" | "error", text: string) => {
    if (onToast) onToast(type, text);
  };

  const fetchData = () => {
    fetch("/api/archive")
      .then((r) => r.json())
      .then((d) => { setData(d); setSelected(new Set()); })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  const formatAge = (hours: number) => {
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    if (hours < 24) return `${Math.round(hours)}h`;
    const days = Math.floor(hours / 24);
    const h = Math.round(hours % 24);
    return `${days}d ${h}h`;
  };

  const toggleSelect = (filePath: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(filePath)) next.delete(filePath);
      else next.add(filePath);
      return next;
    });
  };

  const selectAllStale = () => {
    if (!data) return;
    const allPaths = data.stale_files.map((f) => f.path);
    const allSelected = allPaths.every((p) => selected.has(p));
    if (allSelected) setSelected(new Set());
    else setSelected(new Set(allPaths));
  };

  const handleAction = async (action: string, files?: string[]) => {
    setActing(true);
    try {
      const res = await fetch("/api/archive", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, files }),
      });
      const result = await res.json();
      if (result.success) {
        toast("success", result.message);
        fetchData();
      } else {
        toast("error", result.error || "Failed");
      }
    } catch {
      toast("error", "Network error");
    }
    setActing(false);
  };

  if (loading) return <div className="loading"><span className="spinner" /> Scanning tasks...</div>;
  if (!data) return <div className="section"><p style={{ color: "var(--muted)" }}>Failed to load archive data</p></div>;

  const getAgeColor = (hours: number) => {
    if (hours > 720) return "var(--red)";
    if (hours > 168) return "var(--orange)";
    if (hours > 48) return "var(--yellow)";
    return "var(--green)";
  };

  return (
    <>
      {/* Stats */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 24 }}>
        <div className="stat-card">
          <div className="label">Stale Tasks</div>
          <div className="value" style={{ color: data.stale_count > 0 ? "var(--orange)" : "var(--green)" }}>
            {data.stale_count}
          </div>
          <div className="sub">&gt; {data.age_threshold}h old</div>
        </div>
        <div className="stat-card">
          <div className="label">Active Tasks</div>
          <div className="value" style={{ color: "var(--blue)" }}>{data.recent_count}</div>
          <div className="sub">&lt; {data.age_threshold}h old</div>
        </div>
        <div className="stat-card">
          <div className="label">Archived Total</div>
          <div className="value" style={{ color: "var(--muted)" }}>{data.archived_count}</div>
          <div className="sub">in Archive/</div>
        </div>
        <div className="stat-card">
          <div className="label">Threshold</div>
          <div className="value" style={{ fontSize: 20 }}>{data.age_threshold}h</div>
          <div className="sub">default setting</div>
        </div>
      </div>

      {/* Stale Tasks */}
      <div className="section" style={{ marginBottom: 24, borderColor: data.stale_count > 0 ? "var(--orange)" : "var(--border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ margin: 0 }}>
            <span className="section-icon">{"\u23F0"}</span> Stale Tasks ({data.stale_count})
          </h2>
          {data.stale_count > 0 && (
            <div style={{ display: "flex", gap: 8 }}>
              <button
                className="btn btn-sm btn-primary"
                onClick={() => handleAction("archive_selected", Array.from(selected))}
                disabled={acting || selected.size === 0}
              >
                {acting ? "..." : `Archive Selected (${selected.size})`}
              </button>
              <button
                className="btn btn-sm btn-danger"
                onClick={() => handleAction("archive_all")}
                disabled={acting}
              >
                {acting ? "..." : `Archive All (${data.stale_count})`}
              </button>
            </div>
          )}
        </div>

        {data.stale_files.length === 0 ? (
          <div style={{
            padding: 24, textAlign: "center", color: "var(--green)",
            background: "var(--green-dim)", borderRadius: "var(--radius-sm)",
          }}>
            No stale tasks. Everything is up to date!
          </div>
        ) : (
          <>
            {/* Select All */}
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 13, color: "var(--muted)" }}>
                <input
                  type="checkbox"
                  checked={data.stale_files.every((f) => selected.has(f.path))}
                  onChange={selectAllStale}
                  style={{ accentColor: "var(--orange)" }}
                />
                Select all stale tasks
              </label>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {data.stale_files.map((f) => (
                <div
                  key={f.path}
                  style={{
                    display: "flex", alignItems: "center", gap: 12,
                    padding: "12px 16px", background: "var(--bg)",
                    border: `1px solid ${selected.has(f.path) ? "var(--orange)" : "var(--border)"}`,
                    borderLeft: `4px solid ${getAgeColor(f.age_hours)}`,
                    borderRadius: "var(--radius-sm)",
                    transition: "border-color 0.15s",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(f.path)}
                    onChange={() => toggleSelect(f.path)}
                    style={{ accentColor: "var(--orange)", flexShrink: 0 }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {f.filename.replace(/\.md$/, "").replace(/[-_]/g, " ")}
                    </div>
                    {f.folder && (
                      <span style={{ fontSize: 11, color: "var(--muted)", background: "var(--surface)", padding: "1px 6px", borderRadius: 4 }}>
                        {f.folder}/
                      </span>
                    )}
                  </div>
                  <div style={{ textAlign: "right", flexShrink: 0 }}>
                    <div style={{ fontWeight: 700, fontSize: 14, color: getAgeColor(f.age_hours) }}>
                      {formatAge(f.age_hours)}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--muted)" }}>
                      {new Date(f.modified).toLocaleDateString()}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                    <button
                      className="btn btn-sm btn-primary"
                      onClick={() => handleAction("archive_selected", [f.path])}
                      disabled={acting}
                      style={{ padding: "4px 10px", fontSize: 11 }}
                    >
                      Archive
                    </button>
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => handleAction("delete_selected", [f.path])}
                      disabled={acting}
                      style={{ padding: "4px 10px", fontSize: 11 }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Bulk delete selected */}
            {selected.size > 0 && (
              <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                <button
                  className="btn btn-sm btn-danger"
                  onClick={() => handleAction("delete_selected", Array.from(selected))}
                  disabled={acting}
                >
                  Delete Selected ({selected.size})
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Active Tasks */}
      <div className="section">
        <h2><span className="section-icon">{"\u2713"}</span> Active Tasks ({data.recent_count})</h2>
        {data.recent_files.length === 0 ? (
          <div style={{ color: "var(--muted)", padding: 20, textAlign: "center" }}>
            No active tasks in Needs_Action/
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {data.recent_files.map((f) => (
              <div
                key={f.path}
                style={{
                  display: "flex", alignItems: "center", gap: 12,
                  padding: "12px 16px", background: "var(--bg)",
                  border: "1px solid var(--border)",
                  borderLeft: "4px solid var(--green)",
                  borderRadius: "var(--radius-sm)",
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {f.filename.replace(/\.md$/, "").replace(/[-_]/g, " ")}
                  </div>
                  {f.folder && (
                    <span style={{ fontSize: 11, color: "var(--muted)", background: "var(--surface)", padding: "1px 6px", borderRadius: 4 }}>
                      {f.folder}/
                    </span>
                  )}
                </div>
                <div style={{ textAlign: "right", flexShrink: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, color: "var(--green)" }}>
                    {formatAge(f.age_hours)}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--muted)" }}>
                    {new Date(f.modified).toLocaleDateString()}
                  </div>
                </div>
                <span className="badge badge-paid" style={{ flexShrink: 0 }}>active</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

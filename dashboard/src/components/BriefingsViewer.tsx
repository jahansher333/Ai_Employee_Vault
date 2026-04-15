"use client";

import React, { useEffect, useState } from "react";

interface Briefing {
  filename: string;
  date: string;
  status: string;
}

function renderMarkdown(md: string) {
  // Strip frontmatter
  const stripped = md.replace(/^---[\s\S]*?---\s*/, "");
  const lines = stripped.split("\n");
  const elements: React.ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Blank line
    if (!line.trim()) { i++; continue; }

    // Horizontal rule
    if (/^---+$/.test(line.trim())) {
      elements.push(<hr key={key++} style={{ border: "none", borderTop: "1px solid var(--border)", margin: "24px 0" }} />);
      i++; continue;
    }

    // Headers
    if (line.startsWith("# ")) {
      elements.push(<h1 key={key++} style={{ fontSize: 22, fontWeight: 700, color: "var(--text)", margin: "24px 0 12px", borderBottom: "2px solid var(--blue)", paddingBottom: 8 }}>{inlineFormat(line.slice(2))}</h1>);
      i++; continue;
    }
    if (line.startsWith("## ")) {
      elements.push(<h2 key={key++} style={{ fontSize: 17, fontWeight: 700, color: "var(--blue)", margin: "20px 0 10px", borderBottom: "1px solid var(--border)", paddingBottom: 6 }}>{inlineFormat(line.slice(3))}</h2>);
      i++; continue;
    }
    if (line.startsWith("### ")) {
      elements.push(<h3 key={key++} style={{ fontSize: 15, fontWeight: 700, color: "var(--purple)", margin: "16px 0 8px" }}>{inlineFormat(line.slice(4))}</h3>);
      i++; continue;
    }

    // Table
    if (line.includes("|") && i + 1 < lines.length && /^\|?\s*[-:]+/.test(lines[i + 1])) {
      const tableRows: string[][] = [];
      const headerCells = line.split("|").map(c => c.trim()).filter(Boolean);
      tableRows.push(headerCells);
      i += 2; // skip header + separator
      while (i < lines.length && lines[i].includes("|") && lines[i].trim()) {
        const cells = lines[i].split("|").map(c => c.trim()).filter(Boolean);
        tableRows.push(cells);
        i++;
      }
      elements.push(
        <div key={key++} style={{ overflowX: "auto", margin: "12px 0" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr>
                {tableRows[0].map((cell, ci) => (
                  <th key={ci} style={{
                    padding: "10px 14px", textAlign: "left", fontWeight: 700,
                    background: "var(--surface)", borderBottom: "2px solid var(--blue)",
                    color: "var(--text)", fontSize: 12, textTransform: "uppercase", letterSpacing: 0.5,
                  }}>{inlineFormat(cell)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tableRows.slice(1).map((row, ri) => (
                <tr key={ri} style={{ background: ri % 2 === 0 ? "transparent" : "var(--bg)" }}>
                  {row.map((cell, ci) => {
                    const isAmount = /^\$?[\d,]+\.?\d*$/.test(cell.replace(/[*USD ]/g, ""));
                    const isNeg = cell.startsWith("-") || cell.includes("- ");
                    return (
                      <td key={ci} style={{
                        padding: "8px 14px", borderBottom: "1px solid var(--border)",
                        color: isAmount ? (isNeg ? "var(--red)" : "var(--green)") : "var(--text)",
                        fontWeight: cell.startsWith("**") ? 700 : 400,
                      }}>{inlineFormat(cell)}</td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // Ordered list
    if (/^\d+\.\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s+/, ""));
        i++;
      }
      elements.push(
        <ol key={key++} style={{ margin: "10px 0", paddingLeft: 24, display: "flex", flexDirection: "column", gap: 8 }}>
          {items.map((item, ii) => (
            <li key={ii} style={{
              padding: "8px 12px", background: "var(--bg)", borderRadius: "var(--radius-sm)",
              borderTop: "1px solid var(--border)", borderRight: "1px solid var(--border)",
              borderBottom: "1px solid var(--border)", borderLeft: "3px solid var(--blue)", fontSize: 13, lineHeight: 1.6,
            }}>{inlineFormat(item)}</li>
          ))}
        </ol>
      );
      continue;
    }

    // Unordered list
    if (line.startsWith("- ")) {
      const items: string[] = [];
      while (i < lines.length && lines[i].startsWith("- ")) {
        items.push(lines[i].slice(2));
        i++;
      }
      elements.push(
        <ul key={key++} style={{ margin: "10px 0", paddingLeft: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 6 }}>
          {items.map((item, ii) => (
            <li key={ii} style={{
              padding: "8px 12px", background: "var(--bg)", borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border)", fontSize: 13, lineHeight: 1.6,
              display: "flex", gap: 8, alignItems: "flex-start",
            }}>
              <span style={{ color: "var(--blue)", fontWeight: 700, flexShrink: 0 }}>&#x25CF;</span>
              <span>{inlineFormat(item)}</span>
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // Italic paragraph (like footnotes)
    if (line.startsWith("_") && line.endsWith("_")) {
      elements.push(
        <p key={key++} style={{ fontSize: 12, color: "var(--muted)", fontStyle: "italic", margin: "16px 0", textAlign: "center" }}>
          {line.slice(1, -1)}
        </p>
      );
      i++; continue;
    }

    // Regular paragraph
    elements.push(
      <p key={key++} style={{ margin: "8px 0", fontSize: 14, lineHeight: 1.7, color: "var(--text)" }}>
        {inlineFormat(line)}
      </p>
    );
    i++;
  }

  return elements;
}

function inlineFormat(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let k = 0;

  while (remaining.length > 0) {
    // Bold
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    if (boldMatch && boldMatch.index !== undefined) {
      if (boldMatch.index > 0) parts.push(remaining.slice(0, boldMatch.index));
      parts.push(<strong key={`b${k++}`} style={{ color: "var(--text)", fontWeight: 700 }}>{boldMatch[1]}</strong>);
      remaining = remaining.slice(boldMatch.index + boldMatch[0].length);
      continue;
    }
    // Code
    const codeMatch = remaining.match(/`(.+?)`/);
    if (codeMatch && codeMatch.index !== undefined) {
      if (codeMatch.index > 0) parts.push(remaining.slice(0, codeMatch.index));
      parts.push(<code key={`c${k++}`} style={{ background: "var(--bg)", padding: "2px 6px", borderRadius: 4, fontSize: 12, color: "var(--blue)" }}>{codeMatch[1]}</code>);
      remaining = remaining.slice(codeMatch.index + codeMatch[0].length);
      continue;
    }
    // No more formatting
    parts.push(remaining);
    break;
  }

  return parts;
}

export default function BriefingsViewer() {
  const [briefings, setBriefings] = useState<Briefing[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedContent, setSelectedContent] = useState<string | null>(null);
  const [selectedName, setSelectedName] = useState("");

  useEffect(() => {
    fetch("/api/briefings")
      .then((r) => r.json())
      .then((d) => setBriefings(d.briefings || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const viewBriefing = async (filename: string) => {
    setSelectedName(filename);
    try {
      const res = await fetch(`/api/briefings/${encodeURIComponent(filename)}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedContent(data.content);
      }
    } catch {
      setSelectedContent("Failed to load briefing content.");
    }
  };

  if (loading) return <div className="loading"><span className="spinner" /> Loading briefings...</div>;

  return (
    <>
      {selectedContent ? (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 20 }}>{"\uD83D\uDCCB"}</span>
              {selectedName.replace(/\.md$/, "").replace(/_/g, " ")}
            </h2>
            <button className="btn btn-sm" onClick={() => setSelectedContent(null)}>
              {"\u2190"} Back to List
            </button>
          </div>
          <div
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius)",
              padding: "28px 32px",
              maxHeight: "75vh",
              overflowY: "auto",
            }}
          >
            {renderMarkdown(selectedContent)}
          </div>
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: 24 }}>
            <div className="stat-card">
              <div className="label">Total Briefings</div>
              <div className="value" style={{ color: "var(--blue)" }}>{briefings.length}</div>
            </div>
            <div className="stat-card">
              <div className="label">Latest</div>
              <div className="value" style={{ fontSize: 16, color: "var(--text)" }}>
                {briefings.length > 0 ? briefings[0].date || briefings[0].filename.slice(0, 10) : "\u2014"}
              </div>
            </div>
            <div className="stat-card">
              <div className="label">Frequency</div>
              <div className="value" style={{ fontSize: 16, color: "var(--muted)" }}>Weekly (Monday)</div>
            </div>
          </div>

          <div className="section">
            <h2><span className="section-icon">{"\uD83D\uDCCB"}</span> CEO Briefings</h2>
            {briefings.length === 0 ? (
              <div style={{ color: "var(--muted)", padding: 20, textAlign: "center" }}>
                No briefings generated yet. Briefings are auto-generated every Monday.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {briefings.map((b) => (
                  <div
                    key={b.filename}
                    style={{
                      display: "flex", justifyContent: "space-between", alignItems: "center",
                      padding: "16px 20px", background: "var(--bg)",
                      border: "1px solid var(--border)", borderRadius: "var(--radius-sm)",
                      borderLeft: `4px solid ${b.status === "new" ? "var(--blue)" : "var(--green)"}`,
                      cursor: "pointer", transition: "transform 0.1s",
                    }}
                    onClick={() => viewBriefing(b.filename)}
                    onMouseEnter={(e) => (e.currentTarget.style.transform = "translateX(4px)")}
                    onMouseLeave={(e) => (e.currentTarget.style.transform = "none")}
                  >
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>
                        {b.filename.replace(/\.md$/, "").replace(/_/g, " ")}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--muted)" }}>
                        {b.date || "No date"}
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <span className={`badge ${b.status === "new" ? "badge-info" : "badge-paid"}`}>
                        {b.status}
                      </span>
                      <span style={{ color: "var(--muted)", fontSize: 18 }}>{"\u203A"}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </>
  );
}

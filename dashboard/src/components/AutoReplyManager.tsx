"use client";

import { useEffect, useState } from "react";

interface Template {
  id: string;
  name: string;
  subject: string;
  body: string;
}

interface ReplyLog {
  timestamp?: string;
  action?: string;
  template?: string;
  input_ref?: string;
  outcome?: string;
  to?: string;
  details?: Record<string, string>;
}

interface Props {
  onToast?: (type: "success" | "error", text: string) => void;
}

export default function AutoReplyManager({ onToast }: Props = {}) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [recentReplies, setRecentReplies] = useState<ReplyLog[]>([]);
  const [enabled, setEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [acting, setActing] = useState(false);

  // Form states
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState("");
  const [editName, setEditName] = useState("");
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");

  // Draft form
  const [showDraft, setShowDraft] = useState(false);
  const [draftTo, setDraftTo] = useState("");
  const [draftSubject, setDraftSubject] = useState("");
  const [draftTemplate, setDraftTemplate] = useState("acknowledgment");

  const toast = (type: "success" | "error", text: string) => {
    if (onToast) onToast(type, text);
  };

  const fetchData = () => {
    fetch("/api/auto-reply")
      .then((r) => r.json())
      .then((d) => {
        setTemplates(d.templates || []);
        setRecentReplies(d.recent_replies || []);
        setEnabled(d.auto_reply_enabled || false);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  const handleSaveTemplate = async () => {
    if (!editName || !editSubject || !editBody) {
      toast("error", "All fields are required");
      return;
    }
    setActing(true);
    try {
      const id = editId || editName.toLowerCase().replace(/[^a-z0-9]+/g, "_");
      const res = await fetch("/api/auto-reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "save_template", id, name: editName, subject: editSubject, body: editBody }),
      });
      const result = await res.json();
      if (result.success) {
        toast("success", result.message);
        setShowForm(false);
        setEditId(""); setEditName(""); setEditSubject(""); setEditBody("");
        fetchData();
      } else toast("error", result.error);
    } catch { toast("error", "Network error"); }
    setActing(false);
  };

  const handleDelete = async (id: string) => {
    setActing(true);
    try {
      const res = await fetch("/api/auto-reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "delete_template", id }),
      });
      const result = await res.json();
      if (result.success) {
        toast("success", "Template deleted");
        if (selectedTemplate === id) setSelectedTemplate(null);
        fetchData();
      } else toast("error", result.error);
    } catch { toast("error", "Network error"); }
    setActing(false);
  };

  const handleEdit = (t: Template) => {
    setEditId(t.id);
    setEditName(t.name);
    setEditSubject(t.subject);
    setEditBody(t.body);
    setShowForm(true);
    setShowDraft(false);
  };

  const handleGenerateDraft = async () => {
    if (!draftTo || !draftSubject) {
      toast("error", "Recipient and subject are required");
      return;
    }
    setActing(true);
    try {
      const res = await fetch("/api/auto-reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "generate_draft", to: draftTo, subject: draftSubject, template: draftTemplate }),
      });
      const result = await res.json();
      if (result.success) {
        toast("success", result.message);
        setDraftTo(""); setDraftSubject("");
        setShowDraft(false);
        fetchData();
      } else toast("error", result.error);
    } catch { toast("error", "Network error"); }
    setActing(false);
  };

  if (loading) return <div className="loading"><span className="spinner" /> Loading auto-reply settings...</div>;

  const selected = templates.find((t) => t.id === selectedTemplate);

  return (
    <>
      {/* Status Cards */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: 24 }}>
        <div className="stat-card">
          <div className="label">Auto-Reply</div>
          <div className="value" style={{ color: enabled ? "var(--green)" : "var(--red)", fontSize: 20 }}>
            {enabled ? "Enabled" : "Disabled"}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">Templates</div>
          <div className="value" style={{ color: "var(--blue)" }}>{templates.length}</div>
        </div>
        <div className="stat-card">
          <div className="label">Recent Replies</div>
          <div className="value" style={{ color: "var(--purple)" }}>{recentReplies.length}</div>
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
        <button
          className={`btn ${showForm ? "btn-danger" : "btn-primary"}`}
          onClick={() => {
            setShowForm(!showForm);
            setShowDraft(false);
            if (showForm) { setEditId(""); setEditName(""); setEditSubject(""); setEditBody(""); }
          }}
        >
          {showForm ? "\u2715 Close" : "+ New Template"}
        </button>
        <button
          className={`btn ${showDraft ? "btn-danger" : "btn-success"}`}
          onClick={() => { setShowDraft(!showDraft); setShowForm(false); }}
        >
          {showDraft ? "\u2715 Close" : "\u2709 Create Draft Reply"}
        </button>
      </div>

      {/* New/Edit Template Form */}
      {showForm && (
        <div className="section" style={{ marginBottom: 24, borderColor: "var(--blue)" }}>
          <h2><span className="section-icon">{editId ? "\u270E" : "+"}</span> {editId ? "Edit Template" : "New Template"}</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label>Template Name</label>
              <input className="form-input" placeholder="e.g. Follow Up" value={editName} onChange={(e) => setEditName(e.target.value)} style={{ padding: "10px 14px" }} />
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label>Subject Line</label>
              <input className="form-input" placeholder="Re: {{original_subject}}" value={editSubject} onChange={(e) => setEditSubject(e.target.value)} style={{ padding: "10px 14px" }} />
              <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>
                Variables: {"{{original_subject}}"}, {"{{return_date}}"}, {"{{meeting_date}}"}, {"{{meeting_time}}"}
              </div>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label>Reply Body</label>
              <textarea className="form-input" placeholder="Thank you for your email..." value={editBody} onChange={(e) => setEditBody(e.target.value)} style={{ minHeight: 120, padding: "10px 14px", fontFamily: "inherit" }} />
            </div>
            <div>
              <button className="btn btn-primary" onClick={handleSaveTemplate} disabled={acting}>
                {acting ? "Saving..." : editId ? "Update Template" : "Save Template"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Draft Reply Form */}
      {showDraft && (
        <div className="section" style={{ marginBottom: 24, borderColor: "var(--green)" }}>
          <h2><span className="section-icon">{"\u2709"}</span> Create Draft Reply</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label>To (Email)</label>
              <input className="form-input" placeholder="recipient@example.com" value={draftTo} onChange={(e) => setDraftTo(e.target.value)} style={{ padding: "10px 14px" }} />
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label>Subject</label>
              <input className="form-input" placeholder="Original email subject" value={draftSubject} onChange={(e) => setDraftSubject(e.target.value)} style={{ padding: "10px 14px" }} />
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label>Template</label>
              <select className="form-select" value={draftTemplate} onChange={(e) => setDraftTemplate(e.target.value)} style={{ padding: "10px 14px" }}>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
            <div>
              <button className="btn btn-success" onClick={handleGenerateDraft} disabled={acting || !draftTo || !draftSubject}>
                {acting ? "Creating..." : "Create Draft in Pending_Approval/"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Templates */}
      <div className="section" style={{ marginBottom: 24 }}>
        <h2><span className="section-icon">{"\u2709"}</span> Reply Templates</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {templates.map((t) => (
            <div key={t.id}>
              <div
                onClick={() => setSelectedTemplate(selectedTemplate === t.id ? null : t.id)}
                style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "14px 18px", background: selectedTemplate === t.id ? "var(--blue-dim)" : "var(--bg)",
                  borderTop: `1px solid ${selectedTemplate === t.id ? "var(--blue)" : "var(--border)"}`,
                  borderRight: `1px solid ${selectedTemplate === t.id ? "var(--blue)" : "var(--border)"}`,
                  borderBottom: `1px solid ${selectedTemplate === t.id ? "var(--blue)" : "var(--border)"}`,
                  borderLeft: "4px solid var(--blue)",
                  borderRadius: "var(--radius-sm)", cursor: "pointer", transition: "all 0.15s",
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 2 }}>{t.name}</div>
                  <div style={{ fontSize: 12, color: "var(--muted)" }}>{t.subject}</div>
                </div>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <button className="btn btn-sm" onClick={(e) => { e.stopPropagation(); handleEdit(t); }} style={{ padding: "4px 10px", fontSize: 11 }}>Edit</button>
                  <button className="btn btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); handleDelete(t.id); }} disabled={acting} style={{ padding: "4px 10px", fontSize: 11 }}>Delete</button>
                  <span style={{ color: "var(--muted)", fontSize: 16, marginLeft: 4 }}>{selectedTemplate === t.id ? "\u25B2" : "\u25BC"}</span>
                </div>
              </div>

              {/* Template Body Preview */}
              {selectedTemplate === t.id && (
                <div style={{
                  padding: "16px 20px", background: "var(--surface)",
                  border: "1px solid var(--border)", borderTop: "none",
                  borderRadius: "0 0 var(--radius-sm) var(--radius-sm)",
                }}>
                  <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", fontWeight: 700, marginBottom: 8, letterSpacing: 0.5 }}>
                    Preview
                  </div>
                  <div style={{ fontSize: 12, color: "var(--blue)", marginBottom: 10, fontWeight: 600 }}>
                    Subject: {t.subject}
                  </div>
                  <div style={{
                    fontSize: 13, lineHeight: 1.7, whiteSpace: "pre-wrap", color: "var(--text)",
                    padding: 16, background: "var(--bg)", borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border)",
                  }}>
                    {t.body}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Recent Replies */}
      <div className="section">
        <h2><span className="section-icon">{"\uD83D\uDCE4"}</span> Recent Activity</h2>
        {recentReplies.length === 0 ? (
          <div style={{ color: "var(--muted)", padding: 20, textAlign: "center" }}>
            No auto-reply activity yet
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {recentReplies.map((r, i) => (
              <div
                key={i}
                style={{
                  display: "flex", alignItems: "center", gap: 12,
                  padding: "10px 16px", background: "var(--bg)",
                  borderTop: "1px solid var(--border)", borderRight: "1px solid var(--border)",
                  borderBottom: "1px solid var(--border)", borderRadius: "var(--radius-sm)",
                  borderLeft: `4px solid ${r.outcome === "success" ? "var(--green)" : r.outcome === "error" ? "var(--red)" : "var(--muted)"}`,
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>
                    {r.action?.replace(/_/g, " ") || "reply"}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--muted)" }}>
                    {r.input_ref || r.template || r.to || "\u2014"}
                  </div>
                </div>
                <div style={{ fontSize: 11, color: "var(--muted)", textAlign: "right", flexShrink: 0 }}>
                  {r.timestamp ? new Date(r.timestamp).toLocaleString() : "\u2014"}
                </div>
                <span className={`badge ${r.outcome === "success" ? "badge-paid" : r.outcome === "error" ? "badge-high" : "badge-info"}`} style={{ flexShrink: 0 }}>
                  {r.outcome || "sent"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

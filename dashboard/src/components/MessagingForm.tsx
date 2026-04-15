"use client";

import { useState } from "react";

interface Props {
  onToast: (type: "success" | "error", text: string) => void;
}

export default function MessagingForm({ onToast }: Props) {
  // Email state
  const [emailTo, setEmailTo] = useState("");
  const [emailSubject, setEmailSubject] = useState("");
  const [emailBody, setEmailBody] = useState("");
  const [emailLoading, setEmailLoading] = useState(false);
  const [emailMode, setEmailMode] = useState<"send" | "draft">("send");

  // WhatsApp state
  const [waPhone, setWaPhone] = useState("");
  const [waMessage, setWaMessage] = useState("");
  const [waLoading, setWaLoading] = useState(false);
  const [waMode, setWaMode] = useState<"send" | "draft">("send");

  const handleEmailSend = async () => {
    if (!emailTo.trim() || !emailSubject.trim() || !emailBody.trim()) {
      onToast("error", "Please fill all email fields");
      return;
    }
    setEmailLoading(true);
    try {
      const res = await fetch("/api/email/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          to: emailTo.trim(),
          subject: emailSubject.trim(),
          body: emailBody.trim(),
          mode: emailMode === "draft" ? "draft" : undefined,
        }),
      });
      const result = await res.json();
      if (result.success) {
        onToast("success", result.message);
        setEmailTo("");
        setEmailSubject("");
        setEmailBody("");
      } else {
        onToast("error", result.error || result.message || "Failed to send email");
      }
    } catch {
      onToast("error", "Network error - is API running?");
    }
    setEmailLoading(false);
  };

  const handleWhatsAppSend = async () => {
    if (!waPhone.trim() || !waMessage.trim()) {
      onToast("error", "Please fill phone number and message");
      return;
    }
    setWaLoading(true);
    try {
      const res = await fetch("/api/whatsapp/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone: waPhone.trim(),
          message: waMessage.trim(),
          mode: waMode === "draft" ? "draft" : undefined,
        }),
      });
      const result = await res.json();
      if (result.success) {
        onToast("success", result.message);
        setWaPhone("");
        setWaMessage("");
      } else {
        onToast("error", result.error || result.message || "Failed to send");
      }
    } catch {
      onToast("error", "Network error - is API running?");
    }
    setWaLoading(false);
  };

  return (
    <div className="two-col">
      {/* Email Form */}
      <div className="section">
        <h2><span className="section-icon">{"\u2709"}</span> Send Email</h2>
        <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 16 }}>
          Sends via Gmail API using your connected account.
        </div>
        <div className="form-group">
          <label>To</label>
          <input
            className="form-input"
            type="email"
            placeholder="recipient@email.com"
            value={emailTo}
            onChange={(e) => setEmailTo(e.target.value)}
            style={{ padding: "10px 14px" }}
          />
        </div>
        <div className="form-group">
          <label>Subject</label>
          <input
            className="form-input"
            type="text"
            placeholder="Email subject..."
            value={emailSubject}
            onChange={(e) => setEmailSubject(e.target.value)}
            style={{ padding: "10px 14px" }}
          />
        </div>
        <div className="form-group">
          <label>Body</label>
          <textarea
            className="form-input"
            placeholder="Type your email message here..."
            value={emailBody}
            onChange={(e) => setEmailBody(e.target.value)}
            style={{ minHeight: 140, padding: "10px 14px" }}
          />
        </div>

        {/* Mode Toggle */}
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <button
            type="button"
            onClick={() => setEmailMode("send")}
            style={{
              flex: 1, padding: "8px 12px", borderRadius: "var(--radius-sm)",
              border: `2px solid ${emailMode === "send" ? "var(--blue)" : "var(--border)"}`,
              background: emailMode === "send" ? "var(--blue-dim)" : "var(--bg)",
              color: emailMode === "send" ? "var(--blue)" : "var(--muted)",
              fontWeight: emailMode === "send" ? 700 : 500, fontSize: 13, cursor: "pointer",
            }}
          >
            {"\u2709"} Send Now
          </button>
          <button
            type="button"
            onClick={() => setEmailMode("draft")}
            style={{
              flex: 1, padding: "8px 12px", borderRadius: "var(--radius-sm)",
              border: `2px solid ${emailMode === "draft" ? "var(--yellow)" : "var(--border)"}`,
              background: emailMode === "draft" ? "var(--yellow-dim)" : "var(--bg)",
              color: emailMode === "draft" ? "var(--yellow)" : "var(--muted)",
              fontWeight: emailMode === "draft" ? 700 : 500, fontSize: 13, cursor: "pointer",
            }}
          >
            {"\uD83D\uDCDD"} Save Draft
          </button>
        </div>

        <button
          className="btn btn-primary"
          onClick={handleEmailSend}
          disabled={emailLoading || !emailTo.trim() || !emailSubject.trim() || !emailBody.trim()}
          style={{ width: "100%" }}
        >
          {emailLoading ? "Sending..." : emailMode === "send" ? "\u2709 Send Email" : "\uD83D\uDCDD Save Email Draft"}
        </button>
      </div>

      {/* WhatsApp Form */}
      <div className="section">
        <h2>
          <span className="section-icon" style={{ color: "#25D366" }}>W</span>
          Send WhatsApp
        </h2>
        <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 16 }}>
          Sends via WhatsApp Cloud API (Meta Business). Instant delivery, no browser needed.
        </div>
        <div className="form-group">
          <label>Phone Number</label>
          <input
            className="form-input"
            type="tel"
            placeholder="+92 300 1234567"
            value={waPhone}
            onChange={(e) => setWaPhone(e.target.value)}
            style={{ padding: "10px 14px" }}
          />
          <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>
            Include country code (e.g. +92 for Pakistan, +1 for US)
          </div>
        </div>
        <div className="form-group">
          <label>Message</label>
          <textarea
            className="form-input"
            placeholder="Type your WhatsApp message here..."
            value={waMessage}
            onChange={(e) => setWaMessage(e.target.value)}
            style={{ minHeight: 160, padding: "10px 14px" }}
          />
        </div>

        {/* Mode Toggle */}
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <button
            type="button"
            onClick={() => setWaMode("send")}
            style={{
              flex: 1, padding: "8px 12px", borderRadius: "var(--radius-sm)",
              border: `2px solid ${waMode === "send" ? "#25D366" : "var(--border)"}`,
              background: waMode === "send" ? "#25D36615" : "var(--bg)",
              color: waMode === "send" ? "#25D366" : "var(--muted)",
              fontWeight: waMode === "send" ? 700 : 500, fontSize: 13, cursor: "pointer",
            }}
          >
            {"\uD83D\uDCE8"} Send Now
          </button>
          <button
            type="button"
            onClick={() => setWaMode("draft")}
            style={{
              flex: 1, padding: "8px 12px", borderRadius: "var(--radius-sm)",
              border: `2px solid ${waMode === "draft" ? "var(--yellow)" : "var(--border)"}`,
              background: waMode === "draft" ? "var(--yellow-dim)" : "var(--bg)",
              color: waMode === "draft" ? "var(--yellow)" : "var(--muted)",
              fontWeight: waMode === "draft" ? 700 : 500, fontSize: 13, cursor: "pointer",
            }}
          >
            {"\uD83D\uDCDD"} Save Draft
          </button>
        </div>

        <button
          className="btn"
          onClick={handleWhatsAppSend}
          disabled={waLoading || !waPhone.trim() || !waMessage.trim()}
          style={{
            width: "100%",
            background: waMode === "send" ? "#25D366" : "var(--yellow)",
            color: "#fff",
            border: "none",
          }}
        >
          {waLoading
            ? (waMode === "send" ? "Sending..." : "Saving...")
            : waMode === "send"
              ? "W Send WhatsApp Message"
              : "\uD83D\uDCDD Save WhatsApp Draft"
          }
        </button>

        {/* API Info */}
        <div style={{
          marginTop: 12, padding: 10, background: "var(--bg)",
          borderRadius: "var(--radius-sm)", border: "1px solid var(--border)",
          fontSize: 11, color: "var(--muted)",
        }}>
          Uses WhatsApp Cloud API. Recipient must have WhatsApp. Pakistani numbers auto-prefixed with +92.
        </div>
      </div>
    </div>
  );
}

import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { exec } from "child_process";
import { vaultPath, appendAuditLog } from "@/lib/vault";

export const dynamic = "force-dynamic";

const TEMPLATES_FILE = () => vaultPath("auto_reply", "templates.json");

const DEFAULT_TEMPLATES: Record<string, { name: string; subject: string; body: string }> = {
  acknowledgment: {
    name: "Acknowledgment",
    subject: "Re: {{original_subject}}",
    body: "Thank you for your email. We have received your message and will get back to you shortly.\n\nBest regards,\nAI Employee System",
  },
  out_of_office: {
    name: "Out of Office",
    subject: "Out of Office: {{original_subject}}",
    body: "Thank you for your email. I am currently out of the office and will return on {{return_date}}.\n\nFor urgent matters, please contact {{alternate_contact}}.\n\nBest regards",
  },
  invoice_received: {
    name: "Invoice Received",
    subject: "Re: Invoice Received",
    body: "Thank you for sending your invoice. We have received it and it has been forwarded to our accounts department for processing.\n\nPayment will be processed within our standard payment terms.\n\nBest regards,\nAccounts Department",
  },
  meeting_confirm: {
    name: "Meeting Confirmation",
    subject: "Re: Meeting Confirmed",
    body: "Thank you for the meeting request. This is to confirm the meeting has been noted and added to the calendar.\n\nDetails:\n- Date: {{meeting_date}}\n- Time: {{meeting_time}}\n\nBest regards",
  },
};

function loadTemplates(): Record<string, { name: string; subject: string; body: string }> {
  const file = TEMPLATES_FILE();
  if (fs.existsSync(file)) {
    try {
      return JSON.parse(fs.readFileSync(file, "utf-8"));
    } catch { /* fall through */ }
  }
  return { ...DEFAULT_TEMPLATES };
}

function saveTemplates(templates: Record<string, { name: string; subject: string; body: string }>) {
  const dir = path.dirname(TEMPLATES_FILE());
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(TEMPLATES_FILE(), JSON.stringify(templates, null, 2), "utf-8");
}

export function GET() {
  const templates = loadTemplates();

  // Read auto-reply logs
  const logDir = vaultPath("auto_reply", "Logs");
  const recentReplies: object[] = [];

  if (fs.existsSync(logDir)) {
    const files = fs.readdirSync(logDir).filter((f) => f.endsWith(".jsonl")).sort().reverse().slice(0, 5);
    for (const f of files) {
      const content = fs.readFileSync(path.join(logDir, f), "utf-8");
      const lines = content.trim().split("\n").filter(Boolean);
      for (const line of lines.slice(-10)) {
        try { recentReplies.push(JSON.parse(line)); } catch { /* skip */ }
      }
    }
  }

  // Also check main audit logs for reply events
  const mainLogDir = vaultPath("Logs");
  if (fs.existsSync(mainLogDir)) {
    const files = fs.readdirSync(mainLogDir).filter((f) => f.endsWith(".audit.jsonl")).sort().reverse().slice(0, 3);
    for (const f of files) {
      const content = fs.readFileSync(path.join(mainLogDir, f), "utf-8");
      const lines = content.trim().split("\n").filter(Boolean);
      for (const line of lines) {
        try {
          const entry = JSON.parse(line);
          if (entry.action && (entry.action.includes("reply") || entry.action.includes("auto_reply"))) {
            recentReplies.push(entry);
          }
        } catch { /* skip */ }
      }
    }
  }

  // Sort by timestamp desc
  recentReplies.sort((a: any, b: any) => (b.timestamp || "").localeCompare(a.timestamp || ""));

  return NextResponse.json({
    templates: Object.entries(templates).map(([id, t]) => ({ id, ...t })),
    recent_replies: recentReplies.slice(0, 15),
    auto_reply_enabled: fs.existsSync(vaultPath("auto_reply")),
    template_count: Object.keys(templates).length,
  });
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { action } = body;

    // Save/add template
    if (action === "save_template") {
      const { id, name, subject, body: tplBody } = body;
      if (!id || !name || !subject || !tplBody) {
        return NextResponse.json({ success: false, error: "All fields required" }, { status: 400 });
      }
      const templates = loadTemplates();
      const safeId = id.toLowerCase().replace(/[^a-z0-9_]/g, "_");
      templates[safeId] = { name, subject, body: tplBody };
      saveTemplates(templates);
      appendAuditLog("auto_reply_template_saved", "dashboard", safeId, "success");
      return NextResponse.json({ success: true, message: `Template "${name}" saved` });
    }

    // Delete template
    if (action === "delete_template") {
      const { id } = body;
      const templates = loadTemplates();
      if (templates[id]) {
        delete templates[id];
        saveTemplates(templates);
        appendAuditLog("auto_reply_template_deleted", "dashboard", id, "success");
        return NextResponse.json({ success: true, message: "Template deleted" });
      }
      return NextResponse.json({ success: false, error: "Template not found" }, { status: 404 });
    }

    // Send test auto-reply
    if (action === "test_reply") {
      const { template, to, subject } = body;
      const scriptsDir = path.resolve(vaultPath("scripts"));
      const cmd = `python "${path.join(scriptsDir, "auto_reply.py")}" --templates`;

      const result = await new Promise<{ success: boolean; output: string; error: string }>((resolve) => {
        exec(cmd, { cwd: vaultPath(""), timeout: 15000 }, (error, stdout, stderr) => {
          resolve({
            success: !error,
            output: stdout?.trim() || "",
            error: error ? stderr?.trim() || error.message : "",
          });
        });
      });

      appendAuditLog("auto_reply_test", "dashboard", template || "test", "success");
      return NextResponse.json({ ...result, message: "Test reply logged" });
    }

    // Generate draft reply
    if (action === "generate_draft") {
      const { to, subject, template } = body;
      if (!to || !subject) {
        return NextResponse.json({ success: false, error: "Recipient and subject required" }, { status: 400 });
      }

      const templates = loadTemplates();
      const tpl = templates[template] || templates["acknowledgment"];

      const now = new Date();
      const ts = now.toTimeString().slice(0, 8).replace(/:/g, "");
      const safeSub = subject.replace(/[^a-zA-Z0-9]/g, "-").slice(0, 40);
      const filename = `REPLY_${ts}_${safeSub}.md`;

      const replyBody = tpl.body
        .replace(/\{\{original_subject\}\}/g, subject)
        .replace(/\{\{return_date\}\}/g, "TBD")
        .replace(/\{\{alternate_contact\}\}/g, "N/A")
        .replace(/\{\{meeting_date\}\}/g, "TBD")
        .replace(/\{\{meeting_time\}\}/g, "TBD");

      const replySubject = tpl.subject
        .replace(/\{\{original_subject\}\}/g, subject);

      const content = [
        "---",
        `type: email_reply`,
        `to: "${to}"`,
        `subject: "${replySubject}"`,
        `template: ${template}`,
        `status: pending`,
        `created_at: "${now.toISOString()}"`,
        "---",
        "",
        "# Reply Draft",
        "",
        `**To**: ${to}`,
        `**Subject**: ${replySubject}`,
        `**Template**: ${tpl.name}`,
        "",
        "## Reply Text",
        "",
        replyBody,
        "",
      ].join("\n");

      const pendingDir = vaultPath("Pending_Approval");
      if (!fs.existsSync(pendingDir)) fs.mkdirSync(pendingDir, { recursive: true });
      fs.writeFileSync(path.join(pendingDir, filename), content, "utf-8");

      appendAuditLog("auto_reply_draft", "dashboard", filename, "success");
      return NextResponse.json({ success: true, message: `Draft saved: ${filename}`, filename });
    }

    return NextResponse.json({ success: false, error: "Unknown action" }, { status: 400 });
  } catch (err) {
    return NextResponse.json({ success: false, error: String(err) }, { status: 500 });
  }
}

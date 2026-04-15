import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { exec } from "child_process";
import { vaultPath, appendAuditLog } from "@/lib/vault";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const { to, subject, body, mode } = await request.json();

    if (!to || !subject || !body) {
      return NextResponse.json({ success: false, error: "All fields required (to, subject, body)" }, { status: 400 });
    }

    const ts = new Date().toTimeString().slice(0, 8).replace(/:/g, "");
    const toSlug = to.replace(/[^a-zA-Z0-9]/g, "-").slice(0, 30);

    if (mode === "draft") {
      const folder = vaultPath("Pending_Approval");
      if (!fs.existsSync(folder)) fs.mkdirSync(folder, { recursive: true });
      const filename = `EMAIL_SEND_${ts}_${toSlug}.md`;
      const content = `---\ntype: email_send\nto: "${to}"\nsubject: "${subject}"\nstatus: pending\ncreated: ${new Date().toISOString()}\n---\n\n${body}\n`;
      fs.writeFileSync(path.join(folder, filename), content, "utf-8");
      appendAuditLog("email_draft", "dashboard", filename, "success");
      return NextResponse.json({ success: true, message: `Email draft saved: ${filename}` });
    }

    // Send via Gmail API using helper script
    const tmpFile = path.join(vaultPath(""), ".tmp_email.json");
    fs.writeFileSync(tmpFile, JSON.stringify({ to, subject, body }), "utf-8");

    const scriptPath = path.join(vaultPath("scripts"), "send_email_helper.py");
    const cmd = `python "${scriptPath}" "${tmpFile}"`;

    const result = await new Promise<{ success: boolean; message: string }>((resolve) => {
      exec(cmd, { cwd: vaultPath(""), timeout: 30000 }, (error, stdout, stderr) => {
        try { fs.unlinkSync(tmpFile); } catch { /* ignore */ }
        const output = (stdout || "").trim();
        if (output.startsWith("SUCCESS")) {
          resolve({ success: true, message: `Email sent to ${to}!` });
        } else {
          const errMsg = output.replace("FAILED: ", "").replace("ERROR: ", "")
            || (stderr || "").trim() || error?.message || "Failed to send email";
          resolve({ success: false, message: errMsg });
        }
      });
    });

    appendAuditLog("email_send", "dashboard", to, result.success ? "success" : "error");

    if (result.success) {
      const doneFolder = vaultPath("Done");
      if (!fs.existsSync(doneFolder)) fs.mkdirSync(doneFolder, { recursive: true });
      const filename = `EMAIL_SENT_${ts}_${toSlug}.md`;
      const content = `---\ntype: email_send\nto: "${to}"\nsubject: "${subject}"\nstatus: done\nsent: ${new Date().toISOString()}\n---\n\n${body}\n`;
      fs.writeFileSync(path.join(doneFolder, filename), content, "utf-8");
    }

    return NextResponse.json({ success: result.success, message: result.message });
  } catch (err) {
    return NextResponse.json({ success: false, error: String(err) }, { status: 500 });
  }
}

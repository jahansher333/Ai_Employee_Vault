import { NextResponse } from "next/server";
import { exec } from "child_process";
import path from "path";
import { vaultPath, appendAuditLog } from "@/lib/vault";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const { invoice, overdue } = await request.json();
    const scriptsDir = path.resolve(vaultPath("scripts"));
    const script = path.join(scriptsDir, "pdf_invoice.py");

    let cmd: string;
    if (overdue) {
      cmd = `python "${script}" --overdue`;
    } else if (invoice) {
      cmd = `python "${script}" --invoice "${invoice.replace(/"/g, "")}"`;
    } else {
      return NextResponse.json({ success: false, error: "Provide invoice name or overdue flag" }, { status: 400 });
    }

    const result = await new Promise<{ success: boolean; output: string; error: string }>((resolve) => {
      exec(cmd, { cwd: vaultPath(""), timeout: 30000 }, (error, stdout, stderr) => {
        appendAuditLog("pdf_generate", "dashboard", invoice || "overdue", error ? "error" : "success");
        resolve({
          success: !error,
          output: stdout?.trim() || "",
          error: error ? stderr?.trim() || error.message : "",
        });
      });
    });

    return NextResponse.json(result);
  } catch (err) {
    return NextResponse.json({ success: false, error: String(err) }, { status: 500 });
  }
}

import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { vaultPath, appendAuditLog } from "@/lib/vault";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const { filename, action } = await request.json();

    if (!filename || !action) {
      return NextResponse.json({ success: false, error: "Filename and action required" }, { status: 400 });
    }

    const src = path.join(vaultPath("Pending_Approval"), filename);
    if (!fs.existsSync(src)) {
      return NextResponse.json({ success: false, error: "File not found" }, { status: 404 });
    }

    if (action === "approve") {
      const destDir = vaultPath("Approved");
      if (!fs.existsSync(destDir)) fs.mkdirSync(destDir, { recursive: true });
      fs.renameSync(src, path.join(destDir, filename));
      appendAuditLog("approved", "dashboard", filename, "success");
      return NextResponse.json({ success: true, message: `Approved: ${filename}` });
    } else if (action === "reject") {
      const destDir = vaultPath("Archive");
      if (!fs.existsSync(destDir)) fs.mkdirSync(destDir, { recursive: true });
      fs.renameSync(src, path.join(destDir, filename));
      appendAuditLog("rejected", "dashboard", filename, "success");
      return NextResponse.json({ success: true, message: `Rejected: ${filename}` });
    } else {
      return NextResponse.json({ success: false, error: "Invalid action. Use 'approve' or 'reject'" }, { status: 400 });
    }
  } catch (err) {
    return NextResponse.json({ success: false, error: String(err) }, { status: 500 });
  }
}

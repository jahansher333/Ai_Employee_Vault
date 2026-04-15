import { NextResponse } from "next/server";
import fs from "fs";
import { vaultPath } from "@/lib/vault";

export const dynamic = "force-dynamic";

export function GET() {
  const platforms: Record<string, { drafts: number; posted: number }> = {};

  for (const prefix of ["FACEBOOK", "INSTAGRAM", "TWITTER", "LINKEDIN"]) {
    let drafts = 0;
    let posted = 0;

    const pendingDir = vaultPath("Pending_Approval");
    if (fs.existsSync(pendingDir)) {
      drafts = fs.readdirSync(pendingDir).filter((f) => f.startsWith(`${prefix}_`) && f.endsWith(".md")).length;
    }

    const doneDir = vaultPath("Done");
    if (fs.existsSync(doneDir)) {
      posted = fs.readdirSync(doneDir).filter((f) => f.startsWith(`${prefix}_`) && f.endsWith(".md")).length;
    }

    platforms[prefix.toLowerCase()] = { drafts, posted };
  }

  return NextResponse.json({ platforms });
}

import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { vaultPath, readFrontmatter } from "@/lib/vault";

export const dynamic = "force-dynamic";

export function GET() {
  const dir = vaultPath("Pending_Approval");
  const items: object[] = [];

  if (fs.existsSync(dir)) {
    const files = fs.readdirSync(dir).filter((f) => f.endsWith(".md"));
    for (const f of files) {
      const fp = path.join(dir, f);
      const fm = readFrontmatter(fp);
      items.push({
        filename: f,
        type: fm.type || "unknown",
        status: fm.status || "pending",
        preview: (fm._body || "").slice(0, 150),
      });
    }
  }

  return NextResponse.json({ approvals: items, count: items.length });
}

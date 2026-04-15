import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { vaultPath, readFrontmatter } from "@/lib/vault";

export const dynamic = "force-dynamic";

export function GET(request: Request) {
  const url = new URL(request.url);
  const limit = parseInt(url.searchParams.get("limit") || "50");
  const dir = vaultPath("Needs_Action");
  const tasks: object[] = [];

  if (fs.existsSync(dir)) {
    const files = fs.readdirSync(dir).filter((f) => f.endsWith(".md")).slice(0, limit);
    for (const f of files) {
      const fp = path.join(dir, f);
      const fm = readFrontmatter(fp);
      const stat = fs.statSync(fp);
      tasks.push({
        filename: f,
        type: fm.type || "task",
        priority: fm.priority || "medium",
        status: fm.status || "new",
        preview: (fm._body || "").slice(0, 150),
        modified: stat.mtime.toISOString(),
      });
    }
  }

  return NextResponse.json({ tasks, count: tasks.length });
}

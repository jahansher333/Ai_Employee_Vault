import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { vaultPath, readFrontmatter } from "@/lib/vault";

export const dynamic = "force-dynamic";

export function GET(request: Request) {
  const url = new URL(request.url);
  const limit = parseInt(url.searchParams.get("limit") || "20");
  const dir = vaultPath("Done");
  const items: object[] = [];

  if (fs.existsSync(dir)) {
    const files = fs.readdirSync(dir).filter((f) => f.endsWith(".md")).reverse().slice(0, limit);
    for (const f of files) {
      const fp = path.join(dir, f);
      const fm = readFrontmatter(fp);
      items.push({
        filename: f,
        type: fm.type || "task",
        completed_at: fm.completed_at || "",
      });
    }
  }

  return NextResponse.json({ done: items, count: items.length });
}

import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { vaultPath, readFrontmatter } from "@/lib/vault";

export const dynamic = "force-dynamic";

export function GET() {
  const dir = vaultPath("Briefings");
  const briefings: object[] = [];

  if (fs.existsSync(dir)) {
    const files = fs
      .readdirSync(dir)
      .filter((f) => f.endsWith(".md"))
      .sort()
      .reverse()
      .slice(0, 10);

    for (const f of files) {
      const fm = readFrontmatter(path.join(dir, f));
      briefings.push({
        filename: f,
        date: fm.date || "",
        status: fm.status || "new",
      });
    }
  }

  return NextResponse.json({ briefings });
}

import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { vaultPath } from "@/lib/vault";

export const dynamic = "force-dynamic";

export function GET(_req: Request, { params }: { params: Promise<{ filename: string }> }) {
  return params.then(({ filename }) => {
    const fp = path.join(vaultPath("Briefings"), filename);
    if (!fs.existsSync(fp)) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    const content = fs.readFileSync(fp, "utf-8");
    // Strip frontmatter
    const body = content.replace(/^---\s*\n[\s\S]*?\n---\s*\n?/, "");
    return NextResponse.json({ filename, content: body });
  });
}

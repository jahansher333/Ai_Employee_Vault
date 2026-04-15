import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { vaultPath, readFrontmatter } from "@/lib/vault";

export const dynamic = "force-dynamic";

export function GET() {
  const dir = vaultPath("Plans");
  const plans: object[] = [];

  if (fs.existsSync(dir)) {
    const files = fs
      .readdirSync(dir)
      .filter((f) => f.endsWith(".md"))
      .sort()
      .reverse()
      .slice(0, 20);

    for (const f of files) {
      const fp = path.join(dir, f);
      const fm = readFrontmatter(fp);
      const content = fs.readFileSync(fp, "utf-8");

      // Extract steps from markdown
      const steps: { text: string; done: boolean }[] = [];
      const stepRegex = /- \[([ xX])\] \*\*Step \d+\*\*.*?: (.+)/g;
      let m;
      while ((m = stepRegex.exec(content)) !== null) {
        steps.push({ done: m[1] !== " ", text: m[2] });
      }

      plans.push({
        filename: f,
        objective: fm.objective || f.replace(/\.md$/, ""),
        status: fm.status || "active",
        priority: fm.priority || "medium",
        total_steps: parseInt(fm.total_steps || "0") || steps.length,
        completed_steps: parseInt(fm.completed_steps || "0") || steps.filter((s) => s.done).length,
        created_at: fm.created_at || "",
        source_file: fm.source_file || "",
        steps,
      });
    }
  }

  return NextResponse.json({ plans, count: plans.length });
}

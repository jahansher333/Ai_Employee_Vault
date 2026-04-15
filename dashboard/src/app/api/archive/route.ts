import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { vaultPath, appendAuditLog } from "@/lib/vault";

export const dynamic = "force-dynamic";

function scanDir(dir: string, now: number, threshold: number, prefix = "") {
  const stale: object[] = [];
  const recent: object[] = [];
  if (!fs.existsSync(dir)) return { stale, recent };

  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      const sub = scanDir(fullPath, now, threshold, prefix ? `${prefix}/${entry.name}` : entry.name);
      stale.push(...sub.stale);
      recent.push(...sub.recent);
    } else if (entry.name.endsWith(".md")) {
      const stat = fs.statSync(fullPath);
      const ageHours = (now - stat.mtimeMs) / (1000 * 60 * 60);
      const item = {
        filename: entry.name,
        folder: prefix,
        path: prefix ? `${prefix}/${entry.name}` : entry.name,
        age_hours: Math.round(ageHours * 10) / 10,
        modified: stat.mtime.toISOString(),
      };
      if (ageHours > threshold) stale.push(item);
      else recent.push(item);
    }
  }
  return { stale, recent };
}

export function GET() {
  const needsActionDir = vaultPath("Needs_Action");
  const archiveDir = vaultPath("Archive");
  const ageThreshold = 48;
  const now = Date.now();

  const { stale: staleFiles, recent: recentFiles } = scanDir(needsActionDir, now, ageThreshold);

  let archivedCount = 0;
  if (fs.existsSync(archiveDir)) {
    archivedCount = fs.readdirSync(archiveDir).filter((f) => f.endsWith(".md")).length;
  }

  return NextResponse.json({
    stale_files: staleFiles,
    recent_files: recentFiles,
    stale_count: staleFiles.length,
    recent_count: recentFiles.length,
    archived_count: archivedCount,
    age_threshold: ageThreshold,
  });
}

export async function POST(request: Request) {
  try {
    const { action, files } = await request.json();
    const needsActionDir = vaultPath("Needs_Action");
    const archiveDir = vaultPath("Archive");

    if (action === "archive_all" || action === "archive_selected") {
      if (!fs.existsSync(archiveDir)) fs.mkdirSync(archiveDir, { recursive: true });

      const toArchive: string[] = files || [];
      let archived = 0;

      if (action === "archive_all") {
        // Archive all stale
        const now = Date.now();
        const { stale } = scanDir(needsActionDir, now, 48);
        for (const f of stale as Array<{ path: string; filename: string }>) {
          const src = path.join(needsActionDir, f.path);
          let dest = path.join(archiveDir, f.filename);
          if (fs.existsSync(dest)) {
            dest = path.join(archiveDir, `${f.filename.replace(/\.md$/, "")}-${Date.now() % 10000}.md`);
          }
          if (fs.existsSync(src)) {
            fs.renameSync(src, dest);
            archived++;
          }
        }
      } else {
        for (const filePath of toArchive) {
          const safePath = filePath.replace(/\.\./g, "");
          const src = path.join(needsActionDir, safePath);
          const filename = path.basename(safePath);
          let dest = path.join(archiveDir, filename);
          if (fs.existsSync(dest)) {
            dest = path.join(archiveDir, `${filename.replace(/\.md$/, "")}-${Date.now() % 10000}.md`);
          }
          if (fs.existsSync(src)) {
            fs.renameSync(src, dest);
            archived++;
          }
        }
      }

      appendAuditLog("bulk_archive", "dashboard", `${archived} files`, "success");
      return NextResponse.json({ success: true, archived, message: `Archived ${archived} file(s)` });
    }

    if (action === "delete_selected") {
      let deleted = 0;
      for (const filePath of (files || [])) {
        const safePath = filePath.replace(/\.\./g, "");
        const src = path.join(needsActionDir, safePath);
        if (fs.existsSync(src)) {
          fs.unlinkSync(src);
          deleted++;
        }
      }
      appendAuditLog("bulk_delete", "dashboard", `${deleted} files`, "success");
      return NextResponse.json({ success: true, deleted, message: `Deleted ${deleted} file(s)` });
    }

    return NextResponse.json({ success: false, error: "Unknown action" }, { status: 400 });
  } catch (err) {
    return NextResponse.json({ success: false, error: String(err) }, { status: 500 });
  }
}

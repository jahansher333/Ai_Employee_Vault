import fs from "fs";
import path from "path";

// Vault root - parent of dashboard folder
export const VAULT = process.env.VAULT_PATH || path.resolve(process.cwd(), "..");

export function vaultPath(...segments: string[]): string {
  return path.join(VAULT, ...segments);
}

export function countMd(folder: string): number {
  const dir = vaultPath(folder);
  if (!fs.existsSync(dir)) return 0;
  return fs.readdirSync(dir).filter((f) => f.endsWith(".md")).length;
}

export function listMdFiles(folder: string, limit = 50): string[] {
  const dir = vaultPath(folder);
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".md"))
    .slice(0, limit);
}

export function readFrontmatter(filepath: string): Record<string, string> {
  try {
    const content = fs.readFileSync(filepath, "utf-8");
    const match = content.match(/^---\s*\n([\s\S]*?)\n---/);
    const fm: Record<string, string> = {};
    if (match) {
      for (const line of match[1].split("\n")) {
        const idx = line.indexOf(":");
        if (idx > 0) {
          const key = line.slice(0, idx).trim();
          const val = line.slice(idx + 1).trim().replace(/^['"]|['"]$/g, "");
          fm[key] = val;
        }
      }
      fm._body = content.slice(match[0].length, match[0].length + 300);
    } else {
      fm._body = content.slice(0, 200);
    }
    return fm;
  } catch {
    return { _body: "" };
  }
}

export function appendAuditLog(action: string, actor: string, ref: string, outcome: string) {
  const logDir = vaultPath("Logs");
  if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });

  const today = new Date().toISOString().split("T")[0];
  const logFile = path.join(logDir, `${today}.audit.jsonl`);
  const entry = JSON.stringify({
    timestamp: new Date().toISOString(),
    action,
    actor,
    input_ref: ref,
    outcome,
  });
  fs.appendFileSync(logFile, entry + "\n", "utf-8");
}

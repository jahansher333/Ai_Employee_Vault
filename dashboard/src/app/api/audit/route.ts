import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { vaultPath } from "@/lib/vault";

export const dynamic = "force-dynamic";

export function GET() {
  const entries: object[] = [];
  const logDir = vaultPath("Logs");

  if (fs.existsSync(logDir)) {
    const logFiles = fs
      .readdirSync(logDir)
      .filter((f) => f.endsWith(".audit.jsonl"))
      .sort()
      .reverse()
      .slice(0, 3);

    for (const logFile of logFiles) {
      try {
        const content = fs.readFileSync(path.join(logDir, logFile), "utf-8");
        const lines = content.trim().split("\n");
        for (const line of lines) {
          try {
            entries.push(JSON.parse(line));
          } catch {
            // skip
          }
        }
      } catch {
        // skip
      }
    }
  }

  return NextResponse.json({
    entries: entries.slice(-20),
    count: entries.length,
  });
}

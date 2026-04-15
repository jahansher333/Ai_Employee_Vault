import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { vaultPath } from "@/lib/vault";

export const dynamic = "force-dynamic";

export function GET() {
  // Scan Done/ and Pending_Approval/ for social posts to build engagement summary
  const platforms = ["facebook", "instagram", "twitter", "linkedin"];
  const engagement: Record<string, { posts: number; comments: number; status: string }> = {};

  for (const platform of platforms) {
    const prefix = platform.toUpperCase();
    let postCount = 0;

    // Count posts in Done/
    const doneDir = vaultPath("Done");
    if (fs.existsSync(doneDir)) {
      postCount += fs.readdirSync(doneDir).filter((f) => f.toUpperCase().startsWith(prefix)).length;
    }

    // Count drafts in Pending_Approval/
    const pendingDir = vaultPath("Pending_Approval");
    let draftCount = 0;
    if (fs.existsSync(pendingDir)) {
      draftCount = fs.readdirSync(pendingDir).filter((f) => f.toUpperCase().startsWith(prefix)).length;
    }

    // Check for session directories
    const sessionPaths: Record<string, string> = {
      instagram: "~/.ai_employee/instagram_session",
      facebook: "~/.ai_employee/facebook_session",
      twitter: "~/.ai_employee/twitter_session",
      linkedin: "~/.ai_employee/linkedin_session",
    };

    const homeDir = process.env.HOME || process.env.USERPROFILE || "";
    const sessionDir = sessionPaths[platform].replace("~", homeDir);
    const sessionExists = fs.existsSync(sessionDir);

    engagement[platform] = {
      posts: postCount,
      comments: 0, // would need Playwright to check live
      status: sessionExists ? "connected" : "not_configured",
    };
  }

  // Check for engagement activity in audit logs
  const logsDir = vaultPath("Logs");
  const recentActivity: object[] = [];
  if (fs.existsSync(logsDir)) {
    const logFiles = fs.readdirSync(logsDir)
      .filter((f) => f.endsWith(".audit.jsonl"))
      .sort()
      .reverse()
      .slice(0, 3);

    for (const logFile of logFiles) {
      const content = fs.readFileSync(path.join(logsDir, logFile), "utf-8");
      const lines = content.trim().split("\n").filter(Boolean);
      for (const line of lines) {
        try {
          const entry = JSON.parse(line);
          if (entry.action && (
            entry.action.includes("social") ||
            entry.action.includes("comment") ||
            entry.action.includes("post") ||
            entry.action.includes("engagement")
          )) {
            recentActivity.push(entry);
          }
        } catch { /* skip */ }
      }
    }
  }

  return NextResponse.json({
    platforms: engagement,
    recent_activity: recentActivity.slice(0, 20),
    capabilities: [
      "Check Instagram comments & notifications",
      "Check Facebook post comments",
      "Check Twitter/X mentions & replies",
      "Check LinkedIn post comments",
      "Reply to comments on all platforms",
      "Post tweets via Playwright",
    ],
  });
}

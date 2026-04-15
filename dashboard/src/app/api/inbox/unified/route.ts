import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { vaultPath } from "@/lib/vault";

export const dynamic = "force-dynamic";

function getEnvValue(key: string): string {
  try {
    const envFile = fs.readFileSync(path.join(vaultPath(""), ".env"), "utf-8");
    const match = envFile.match(new RegExp(`^${key}=(.*)$`, "m"));
    return match ? match[1].trim() : "";
  } catch {
    return process.env[key] || "";
  }
}

interface InboxItem {
  id: string;
  type: "email" | "whatsapp" | "comment";
  platform?: string;
  from: string;
  subject?: string;
  message: string;
  timestamp: string;
  phone?: string;
  post_id?: string;
  post_message?: string;
  reply_to?: string;
}

// Fetch emails from Gmail via Python helper
async function fetchEmails(): Promise<{ items: InboxItem[]; error?: string }> {
  const { exec } = await import("child_process");
  return new Promise((resolve) => {
    const scriptPath = path.join(vaultPath("scripts"), "gmail_watcher.py");
    if (!fs.existsSync(scriptPath)) {
      resolve({ items: [], error: "gmail_watcher.py not found" });
      return;
    }
    const cmd = `python "${scriptPath}" --list-recent 20 --json`;
    exec(cmd, { cwd: vaultPath(""), timeout: 15000 }, (error, stdout) => {
      if (error || !stdout.trim()) {
        // Fallback: read from Needs_Action folder
        const items = readVaultFolder("Needs_Action", "email");
        resolve({ items });
        return;
      }
      try {
        const emails = JSON.parse(stdout.trim());
        const items: InboxItem[] = emails.map((e: { id?: string; from?: string; subject?: string; snippet?: string; date?: string }) => ({
          id: `email_${e.id || Date.now()}`,
          type: "email" as const,
          from: e.from || "Unknown",
          subject: e.subject || "(no subject)",
          message: e.snippet || "",
          timestamp: e.date || new Date().toISOString(),
          reply_to: e.from,
        }));
        resolve({ items });
      } catch {
        const items = readVaultFolder("Needs_Action", "email");
        resolve({ items });
      }
    });
  });
}

// Read vault folders for messages
function readVaultFolder(folder: string, typeFilter?: string): InboxItem[] {
  const items: InboxItem[] = [];
  const dir = vaultPath(folder);
  if (!fs.existsSync(dir)) return items;

  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".md")).slice(-30);
  for (const file of files) {
    try {
      const content = fs.readFileSync(path.join(dir, file), "utf-8");
      // Handle both \n and \r\n line endings
      const normalized = content.replace(/\r\n/g, "\n");
      const frontmatter = normalized.match(/^---\n([\s\S]*?)\n---/);
      const body = normalized.replace(/^---\n[\s\S]*?\n---\n*/, "").trim();
      const meta: Record<string, string> = {};
      if (frontmatter) {
        frontmatter[1].split("\n").forEach((line) => {
          // Handle quoted values with special chars
          const m = line.match(/^(\w+):\s*"?(.*?)"?\s*$/);
          if (m) meta[m[1]] = m[2].replace(/^["']|["']$/g, "");
        });
      }

      const itemType = meta.type || "";
      if (typeFilter && !itemType.includes(typeFilter)) continue;

      let type: "email" | "whatsapp" | "comment" = "email";
      let platform: string | undefined;
      if (itemType.includes("whatsapp")) type = "whatsapp";
      else if (itemType.includes("facebook") || itemType.includes("instagram") || itemType.includes("linkedin") || itemType.includes("twitter")) {
        type = "comment";
        platform = itemType.replace("_post", "").replace("_comment", "");
      }

      // Extract clean "from" — parse email format like "Name <email@domain.com>"
      let fromName = meta.from || meta.to || meta.phone || "";
      const emailMatch = fromName.match(/^(.+?)\s*<(.+?)>$/);
      if (emailMatch) {
        fromName = emailMatch[1].replace(/["']/g, "").trim();
      }
      if (!fromName) fromName = file.replace(/\.md$/, "").replace(/_/g, " ").slice(0, 40);

      // Extract reply-to email address
      let replyTo = meta.from || meta.to || "";
      const replyEmailMatch = replyTo.match(/<(.+?)>/);
      if (replyEmailMatch) replyTo = replyEmailMatch[1];

      // Extract snippet from body — skip markdown headers and metadata
      let snippet = body;
      const snippetSection = body.match(/## Email Snippet\n+([\s\S]*?)(?:\n##|$)/);
      if (snippetSection) {
        snippet = snippetSection[1].trim();
      } else {
        // Remove markdown headers
        snippet = body.replace(/^#+\s.*$/gm, "").replace(/\*\*[^*]+\*\*/g, "").trim();
      }
      snippet = snippet.replace(/\s+/g, " ").slice(0, 300);

      items.push({
        id: `vault_${file}`,
        type,
        platform,
        from: fromName,
        subject: meta.subject?.replace(/["']/g, ""),
        message: snippet,
        timestamp: meta.created || meta.date || meta.received || new Date().toISOString(),
        phone: meta.phone,
        reply_to: replyTo,
      });
    } catch {
      continue;
    }
  }
  return items;
}

// Fetch Facebook comments
async function fetchFacebookComments(): Promise<InboxItem[]> {
  const pageId = getEnvValue("FACEBOOK_PAGE_ID");
  const token = getEnvValue("FACEBOOK_PAGE_ACCESS_TOKEN");
  if (!pageId || !token) return [];

  try {
    const url = `https://graph.facebook.com/v18.0/${pageId}/posts?fields=id,message,created_time,comments.limit(5){id,from,message,created_time}&limit=5&access_token=${token}`;
    const res = await fetch(url, { signal: AbortSignal.timeout(10000) });
    if (!res.ok) return [];
    const data = await res.json();
    const items: InboxItem[] = [];
    for (const post of data.data || []) {
      for (const c of post.comments?.data || []) {
        items.push({
          id: `fb_${c.id}`,
          type: "comment",
          platform: "facebook",
          from: c.from?.name || "Facebook User",
          message: c.message || "",
          timestamp: c.created_time,
          post_id: post.id,
          post_message: (post.message || "").slice(0, 100),
        });
      }
    }
    return items;
  } catch {
    return [];
  }
}

// Fetch WhatsApp messages from vault
function fetchWhatsAppMessages(): InboxItem[] {
  const items = [
    ...readVaultFolder("Needs_Action", "whatsapp"),
    ...readVaultFolder("Done", "whatsapp"),
  ];
  return items.slice(-20);
}

export async function GET() {
  const [emailResult, fbComments, waMessages, needsAction, doneItems] = await Promise.all([
    fetchEmails(),
    fetchFacebookComments(),
    fetchWhatsAppMessages(),
    Promise.resolve(readVaultFolder("Needs_Action")),
    Promise.resolve(readVaultFolder("Done")),
  ]);

  const all: InboxItem[] = [
    ...fbComments,
    ...needsAction,
    ...doneItems.filter((i) => i.type === "whatsapp" || i.type === "comment"),
    ...emailResult.items.filter((i) => !needsAction.some((n) => n.id === i.id)),
    ...waMessages.filter((i) => !needsAction.some((n) => n.id === i.id)),
  ];

  // Deduplicate by id
  const seen = new Set<string>();
  const unique = all.filter((item) => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });

  // Sort newest first
  unique.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  return NextResponse.json({
    items: unique.slice(0, 50),
    counts: {
      email: unique.filter((i) => i.type === "email").length,
      whatsapp: unique.filter((i) => i.type === "whatsapp").length,
      comment: unique.filter((i) => i.type === "comment").length,
    },
    fetched_at: new Date().toISOString(),
  });
}

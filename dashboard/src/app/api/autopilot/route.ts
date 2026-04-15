import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { exec } from "child_process";
import { vaultPath, appendAuditLog } from "@/lib/vault";

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

const CONFIG_FILE = "autopilot_config.json";

interface AutopilotConfig {
  enabled: boolean;
  interval_hours: number;
  platforms: {
    facebook: boolean;
    instagram: boolean;
    linkedin: boolean;
    twitter: boolean;
    email: boolean;
    whatsapp: boolean;
  };
  auto_reply: boolean;
  business_description: string;
  tone: string;
  last_run?: string;
  next_run?: string;
}

function getConfig(): AutopilotConfig {
  const configPath = path.join(vaultPath(""), CONFIG_FILE);
  if (fs.existsSync(configPath)) {
    return JSON.parse(fs.readFileSync(configPath, "utf-8"));
  }
  return {
    enabled: false,
    interval_hours: 48,
    platforms: { facebook: true, instagram: true, linkedin: true, twitter: false, email: false, whatsapp: false },
    auto_reply: true,
    business_description: "AI Employee System - Automated business operations platform",
    tone: "professional",
  };
}

function saveConfig(config: AutopilotConfig) {
  fs.writeFileSync(path.join(vaultPath(""), CONFIG_FILE), JSON.stringify(config, null, 2), "utf-8");
}

// Generate post content via Claude CLI
function generateContent(type: string, description: string, tone: string): Promise<string> {
  return new Promise((resolve) => {
    const prompt = `Generate a ${type} post for a business. Business: ${description}. Tone: ${tone}. Rules: 1) Max 280 chars for twitter, 500 chars for others. 2) Include relevant hashtags. 3) Be engaging and authentic. 4) Don't use quotes around the text. 5) Output ONLY the post text, nothing else.`;
    const tmpFile = path.join(vaultPath(""), ".tmp_autopilot_prompt.txt");
    fs.writeFileSync(tmpFile, prompt, "utf-8");
    const cmd = `claude -p "$(cat '${tmpFile.replace(/\\/g, "/")}')" 2>/dev/null`;
    exec(cmd, { timeout: 30000, shell: "bash" }, (error, stdout) => {
      try { fs.unlinkSync(tmpFile); } catch { /* */ }
      const text = (stdout || "").trim();
      if (text && !error) resolve(text);
      else resolve(`Boost your business with AI automation! Our AI Employee handles emails, social media, customer replies & more — 24/7. #AIAutomation #Business #Productivity`);
    });
  });
}

// Generate reply via Claude CLI
function generateReply(from: string, message: string, platform: string): Promise<string> {
  return new Promise((resolve) => {
    const prompt = `Reply to this ${platform} comment in 1-2 sentences. Be friendly and professional. Match the sender's language. From: ${from}. Message: ${message}. Output ONLY the reply.`;
    const tmpFile = path.join(vaultPath(""), ".tmp_reply_prompt.txt");
    fs.writeFileSync(tmpFile, prompt, "utf-8");
    const cmd = `claude -p "$(cat '${tmpFile.replace(/\\/g, "/")}')" 2>/dev/null`;
    exec(cmd, { timeout: 30000, shell: "bash" }, (error, stdout) => {
      try { fs.unlinkSync(tmpFile); } catch { /* */ }
      const text = (stdout || "").trim();
      if (text && !error) resolve(text);
      else resolve(`Thank you for your message! We appreciate your engagement.`);
    });
  });
}

// Post to Facebook
async function postFacebook(content: string, imageUrl?: string): Promise<{ ok: boolean; id?: string; error?: string }> {
  const pageId = getEnvValue("FACEBOOK_PAGE_ID");
  const token = getEnvValue("FACEBOOK_PAGE_ACCESS_TOKEN");
  if (!pageId || !token) return { ok: false, error: "Not configured" };

  const url = imageUrl
    ? `https://graph.facebook.com/v18.0/${pageId}/photos`
    : `https://graph.facebook.com/v18.0/${pageId}/feed`;
  const body: Record<string, string> = { message: content, access_token: token };
  if (imageUrl) body.url = imageUrl;

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.id) return { ok: true, id: data.id };
  return { ok: false, error: data.error?.message || "Failed" };
}

// Post to Instagram
async function postInstagram(content: string, imageUrl: string): Promise<{ ok: boolean; id?: string; error?: string }> {
  const userId = getEnvValue("INSTAGRAM_USER_ID");
  const token = getEnvValue("INSTAGRAM_ACCESS_TOKEN");
  if (!userId || !token) return { ok: false, error: "Not configured" };

  // Step 1: Create container
  const containerRes = await fetch(`https://graph.facebook.com/v18.0/${userId}/media`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_url: imageUrl, caption: content, access_token: token }),
  });
  const container = await containerRes.json();
  if (!container.id) return { ok: false, error: container.error?.message || "Container failed" };

  // Step 2: Publish
  await new Promise((r) => setTimeout(r, 5000));
  const pubRes = await fetch(`https://graph.facebook.com/v18.0/${userId}/media_publish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ creation_id: container.id, access_token: token }),
  });
  const pub = await pubRes.json();
  if (pub.id) return { ok: true, id: pub.id };
  return { ok: false, error: pub.error?.message || "Publish failed" };
}

// Post to LinkedIn
async function postLinkedIn(content: string): Promise<{ ok: boolean; id?: string; error?: string }> {
  const token = getEnvValue("LINKEDIN_ACCESS_TOKEN");
  const personUrn = getEnvValue("LINKEDIN_PERSON_URN");
  if (!token || !personUrn) return { ok: false, error: "Not configured" };

  const res = await fetch("https://api.linkedin.com/v2/ugcPosts", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "X-Restli-Protocol-Version": "2.0.0",
    },
    body: JSON.stringify({
      author: personUrn,
      lifecycleState: "PUBLISHED",
      specificContent: {
        "com.linkedin.ugc.ShareContent": {
          shareCommentary: { text: content },
          shareMediaCategory: "NONE",
        },
      },
      visibility: { "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC" },
    }),
  });
  const data = await res.json();
  if (res.ok) return { ok: true, id: data.id };
  return { ok: false, error: data.message || "Failed" };
}

// Reply to Facebook comments
async function autoReplyFacebookComments(): Promise<{ replied: number; errors: string[] }> {
  const pageId = getEnvValue("FACEBOOK_PAGE_ID");
  const token = getEnvValue("FACEBOOK_PAGE_ACCESS_TOKEN");
  if (!pageId || !token) return { replied: 0, errors: ["Facebook not configured"] };

  const errors: string[] = [];
  let replied = 0;

  try {
    const postsUrl = `https://graph.facebook.com/v18.0/${pageId}/posts?fields=id,comments.limit(5){id,from,message,created_time,can_comment}&limit=5&access_token=${token}`;
    const res = await fetch(postsUrl, { signal: AbortSignal.timeout(15000) });
    if (!res.ok) return { replied: 0, errors: ["Failed to fetch posts"] };

    const data = await res.json();
    // Track replied comments
    const repliedFile = path.join(vaultPath(""), ".autopilot_replied.json");
    let repliedIds: string[] = [];
    if (fs.existsSync(repliedFile)) {
      try { repliedIds = JSON.parse(fs.readFileSync(repliedFile, "utf-8")); } catch { /* */ }
    }

    for (const post of data.data || []) {
      for (const comment of post.comments?.data || []) {
        if (repliedIds.includes(comment.id)) continue;
        if (!comment.can_comment) continue;

        try {
          const reply = await generateReply(comment.from?.name || "User", comment.message || "", "facebook");
          const replyRes = await fetch(
            `https://graph.facebook.com/v18.0/${comment.id}/comments?message=${encodeURIComponent(reply)}&access_token=${token}`,
            { method: "POST" }
          );
          const replyData = await replyRes.json();
          if (replyData.id) {
            replied++;
            repliedIds.push(comment.id);
          }
        } catch (e) {
          errors.push(`Reply failed: ${String(e)}`);
        }
      }
    }

    // Save replied IDs (keep last 500)
    fs.writeFileSync(repliedFile, JSON.stringify(repliedIds.slice(-500)), "utf-8");
  } catch (e) {
    errors.push(String(e));
  }

  return { replied, errors };
}

// Send WhatsApp message
async function sendWhatsApp(phone: string, message: string): Promise<{ ok: boolean; error?: string }> {
  const phoneNumberId = getEnvValue("WHATSAPP_PHONE_NUMBER_ID");
  const apiToken = getEnvValue("WHATSAPP_API_TOKEN");
  if (!phoneNumberId || !apiToken) return { ok: false, error: "Not configured" };

  let formatted = phone.replace(/[\s\-\(\)]/g, "");
  if (formatted.startsWith("+")) formatted = formatted.slice(1);
  if (formatted.startsWith("0")) formatted = "92" + formatted.slice(1);

  const res = await fetch(`https://graph.facebook.com/v25.0/${phoneNumberId}/messages`, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiToken}`, "Content-Type": "application/json" },
    body: JSON.stringify({ messaging_product: "whatsapp", to: formatted, type: "text", text: { body: message } }),
  });
  const data = await res.json();
  if (res.ok && data.messages?.length > 0) return { ok: true };
  return { ok: false, error: data.error?.message || "Failed" };
}

// GET: Return config + history
export async function GET() {
  const config = getConfig();

  // Read autopilot log
  const logFile = path.join(vaultPath(""), ".autopilot_log.json");
  let history: Array<{ date: string; action: string; platform: string; status: string; detail?: string }> = [];
  if (fs.existsSync(logFile)) {
    try { history = JSON.parse(fs.readFileSync(logFile, "utf-8")); } catch { /* */ }
  }

  return NextResponse.json({ config, history: history.slice(-50).reverse() });
}

// POST: Update config or trigger run
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { action } = body;

    if (action === "save_config") {
      const config = getConfig();
      const updated = { ...config, ...body.config };
      saveConfig(updated);
      return NextResponse.json({ success: true, message: "Autopilot settings saved!" });
    }

    if (action === "run_now") {
      const config = getConfig();
      const results: Array<{ platform: string; action: string; status: string; detail?: string }> = [];
      const logFile = path.join(vaultPath(""), ".autopilot_log.json");
      let history: Array<{ date: string; action: string; platform: string; status: string; detail?: string }> = [];
      if (fs.existsSync(logFile)) {
        try { history = JSON.parse(fs.readFileSync(logFile, "utf-8")); } catch { /* */ }
      }

      const defaultImage = getEnvValue("INSTAGRAM_DEFAULT_IMAGE_URL");

      // Generate content
      const postContent = await generateContent("social media", config.business_description, config.tone);

      // Post to enabled platforms
      if (config.platforms.facebook) {
        const fb = await postFacebook(postContent);
        const entry = { platform: "facebook", action: "post", status: fb.ok ? "success" : "failed", detail: fb.ok ? `Post ID: ${fb.id}` : fb.error };
        results.push(entry);
        history.push({ date: new Date().toISOString(), ...entry });
      }

      if (config.platforms.instagram && defaultImage) {
        const ig = await postInstagram(postContent, defaultImage);
        const entry = { platform: "instagram", action: "post", status: ig.ok ? "success" : "failed", detail: ig.ok ? `Post ID: ${ig.id}` : ig.error };
        results.push(entry);
        history.push({ date: new Date().toISOString(), ...entry });
      }

      if (config.platforms.linkedin) {
        const li = await postLinkedIn(postContent);
        const entry = { platform: "linkedin", action: "post", status: li.ok ? "success" : "failed", detail: li.ok ? `Post ID: ${li.id}` : li.error };
        results.push(entry);
        history.push({ date: new Date().toISOString(), ...entry });
      }

      // Auto-reply to comments
      if (config.auto_reply) {
        const replyResult = await autoReplyFacebookComments();
        const entry = {
          platform: "facebook",
          action: "auto-reply",
          status: replyResult.replied > 0 ? "success" : "skipped",
          detail: `${replyResult.replied} comments replied${replyResult.errors.length ? `, ${replyResult.errors.length} errors` : ""}`,
        };
        results.push(entry);
        history.push({ date: new Date().toISOString(), ...entry });
      }

      // Save done post to vault
      const ts = new Date().toTimeString().slice(0, 8).replace(/:/g, "");
      const doneFolder = vaultPath("Done");
      if (!fs.existsSync(doneFolder)) fs.mkdirSync(doneFolder, { recursive: true });
      const platforms = results.filter((r) => r.action === "post" && r.status === "success").map((r) => r.platform);
      if (platforms.length > 0) {
        const filename = `AUTOPILOT_${ts}_${platforms.join("-")}.md`;
        const content = `---\ntype: autopilot_post\nplatforms: ${platforms.join(", ")}\nstatus: done\nposted: ${new Date().toISOString()}\n---\n\n${postContent}\n`;
        fs.writeFileSync(path.join(doneFolder, filename), content, "utf-8");
      }

      // Update config
      config.last_run = new Date().toISOString();
      config.next_run = new Date(Date.now() + config.interval_hours * 3600000).toISOString();
      saveConfig(config);

      // Save log
      fs.writeFileSync(logFile, JSON.stringify(history.slice(-200)), "utf-8");

      appendAuditLog("autopilot_run", "dashboard", platforms.join(","), "success");

      const successCount = results.filter((r) => r.status === "success").length;
      return NextResponse.json({
        success: true,
        message: `Autopilot ran: ${successCount}/${results.length} actions succeeded`,
        results,
        content: postContent,
      });
    }

    if (action === "toggle") {
      const config = getConfig();
      config.enabled = !config.enabled;
      if (config.enabled) {
        config.next_run = new Date(Date.now() + config.interval_hours * 3600000).toISOString();
      }
      saveConfig(config);
      return NextResponse.json({ success: true, enabled: config.enabled, message: config.enabled ? "Autopilot enabled!" : "Autopilot disabled" });
    }

    return NextResponse.json({ success: false, error: "Unknown action" }, { status: 400 });
  } catch (err) {
    return NextResponse.json({ success: false, error: String(err) }, { status: 500 });
  }
}

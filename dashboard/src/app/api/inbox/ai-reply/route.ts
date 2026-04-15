import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
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

export async function POST(request: Request) {
  try {
    const { item, action } = await request.json();
    // item: { type, from, message, subject, phone, post_id, platform }
    // action: "generate" | "send"

    if (!item || !item.message) {
      return NextResponse.json({ success: false, error: "No message to reply to" }, { status: 400 });
    }

    if (action === "generate") {
      const replyText = await generateClaudeReply(item);
      return NextResponse.json({ success: true, reply: replyText });
    }

    const replyText = item.customReply || await generateClaudeReply(item);

    // action === "send" — actually send the reply
    let result: { success: boolean; message: string };

    if (item.type === "email" && item.reply_to) {
      result = await sendEmailReply(item.reply_to, item.subject || "Re: Your message", replyText);
    } else if (item.type === "whatsapp" && item.phone) {
      result = await sendWhatsAppReply(item.phone, replyText);
    } else if (item.type === "comment" && item.platform === "facebook" && item.post_id) {
      result = await sendFacebookReply(item.id, replyText);
    } else {
      // Save as draft
      const ts = new Date().toTimeString().slice(0, 8).replace(/:/g, "");
      const folder = vaultPath("Pending_Approval");
      if (!fs.existsSync(folder)) fs.mkdirSync(folder, { recursive: true });
      const filename = `REPLY_${item.type.toUpperCase()}_${ts}.md`;
      const content = `---\ntype: auto_reply\noriginal_from: "${item.from}"\nplatform: "${item.platform || item.type}"\nstatus: pending\ncreated: ${new Date().toISOString()}\n---\n\n**Original:** ${item.message.slice(0, 200)}\n\n**Reply:**\n${replyText}\n`;
      fs.writeFileSync(path.join(folder, filename), content, "utf-8");
      result = { success: true, message: `Reply draft saved: ${filename}` };
    }

    appendAuditLog("ai_reply", "dashboard", `${item.type}:${item.from}`, result.success ? "success" : "error");
    return NextResponse.json(result);
  } catch (err) {
    return NextResponse.json({ success: false, error: String(err) }, { status: 500 });
  }
}

async function generateClaudeReply(item: { type: string; from: string; message: string; subject?: string; platform?: string }): Promise<string> {
  const { exec } = await import("child_process");

  const platformLabel = item.platform || item.type;
  const subjectLine = item.subject ? `Subject: ${item.subject}\n` : "";

  const prompt = `You are a professional business assistant. Generate a short, natural reply to this ${platformLabel} message.

From: ${item.from}
${subjectLine}Message: ${item.message}

Rules:
- Reply in the SAME LANGUAGE as the original message (if Urdu/Roman Urdu, reply in Roman Urdu)
- Keep it short: 2-4 sentences for ${item.type === "comment" ? "comments" : "messages"}
- Be professional but friendly
- Address their specific question/topic directly
- Do NOT use generic "thank you for reaching out" filler
- Do NOT add signatures or "Best regards"
- Match the tone of the sender (formal if formal, casual if casual)
- Only output the reply text, nothing else`;

  return new Promise((resolve) => {
    const tmpPrompt = path.join(vaultPath(""), ".tmp_ai_prompt.txt");
    fs.writeFileSync(tmpPrompt, prompt, "utf-8");
    const cmd = `claude -p "$(cat '${tmpPrompt.replace(/\\/g, "/")}')" 2>/dev/null`;

    exec(cmd, { timeout: 30000, maxBuffer: 1024 * 1024, shell: "bash" }, (error, stdout) => {
      try { fs.unlinkSync(tmpPrompt); } catch { /* */ }
      const reply = (stdout || "").trim();
      if (reply && !error) {
        resolve(reply);
      } else {
        // Fallback: context-aware basic reply
        resolve(getFallbackReply(item));
      }
    });
  });
}

function getFallbackReply(item: { type: string; from: string; message: string }): string {
  const msg = item.message.toLowerCase();
  const name = item.from.split(" ")[0];

  if (msg.includes("price") || msg.includes("cost") || msg.includes("kitna")) {
    return `Hi ${name}, I'd be happy to share pricing details. Which product/service are you interested in?`;
  }
  if (msg.includes("order") || msg.includes("delivery") || msg.includes("shipping")) {
    return `Hi ${name}, let me check your order status and get back to you right away.`;
  }
  if (msg.includes("help") || msg.includes("issue") || msg.includes("problem")) {
    return `Hi ${name}, I'm here to help. Could you share more details about the issue you're facing?`;
  }
  if (item.type === "comment") {
    return `Thanks ${name}! Glad you're engaging with us. Let us know if you have any questions.`;
  }
  return `Hi ${name}, got your message. Let me look into this and get back to you shortly.`;
}

async function sendEmailReply(to: string, subject: string, body: string): Promise<{ success: boolean; message: string }> {
  const { exec } = await import("child_process");
  const tmpFile = path.join(vaultPath(""), ".tmp_reply_email.json");
  fs.writeFileSync(tmpFile, JSON.stringify({ to, subject: `Re: ${subject}`, body }), "utf-8");
  const scriptPath = path.join(vaultPath("scripts"), "send_email_helper.py");

  return new Promise((resolve) => {
    exec(`python "${scriptPath}" "${tmpFile}"`, { cwd: vaultPath(""), timeout: 30000 }, (error, stdout) => {
      try { fs.unlinkSync(tmpFile); } catch { /* */ }
      const output = (stdout || "").trim();
      if (output.startsWith("SUCCESS")) {
        resolve({ success: true, message: `Email reply sent to ${to}` });
      } else {
        resolve({ success: false, message: output || error?.message || "Failed to send email reply" });
      }
    });
  });
}

async function sendWhatsAppReply(phone: string, message: string): Promise<{ success: boolean; message: string }> {
  const phoneNumberId = getEnvValue("WHATSAPP_PHONE_NUMBER_ID");
  const apiToken = getEnvValue("WHATSAPP_API_TOKEN");
  if (!phoneNumberId || !apiToken) {
    return { success: false, message: "WhatsApp Cloud API not configured" };
  }

  let formatted = phone.replace(/[\s\-\(\)]/g, "");
  if (formatted.startsWith("+")) formatted = formatted.slice(1);
  if (formatted.startsWith("0")) formatted = "92" + formatted.slice(1);

  const res = await fetch(`https://graph.facebook.com/v25.0/${phoneNumberId}/messages`, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiToken}`, "Content-Type": "application/json" },
    body: JSON.stringify({ messaging_product: "whatsapp", to: formatted, type: "text", text: { body: message } }),
  });
  const data = await res.json();
  if (res.ok && data.messages?.length > 0) {
    return { success: true, message: `WhatsApp reply sent to +${formatted}` };
  }
  return { success: false, message: data.error?.message || "WhatsApp send failed" };
}

async function sendFacebookReply(commentId: string, message: string): Promise<{ success: boolean; message: string }> {
  const token = getEnvValue("FACEBOOK_PAGE_ACCESS_TOKEN");
  if (!token) return { success: false, message: "Facebook not configured" };

  const cleanId = commentId.replace("fb_", "");
  const res = await fetch(`https://graph.facebook.com/v18.0/${cleanId}/comments?message=${encodeURIComponent(message)}&access_token=${token}`, {
    method: "POST",
  });
  const data = await res.json();
  if (res.ok && data.id) {
    return { success: true, message: `Facebook reply posted (${data.id})` };
  }
  return { success: false, message: data.error?.message || "Facebook reply failed" };
}

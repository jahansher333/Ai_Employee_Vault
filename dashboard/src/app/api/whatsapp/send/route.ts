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

async function sendViaCloudAPI(phone: string, message: string): Promise<{ success: boolean; message: string }> {
  const phoneNumberId = getEnvValue("WHATSAPP_PHONE_NUMBER_ID");
  const apiToken = getEnvValue("WHATSAPP_API_TOKEN");

  if (!phoneNumberId || !apiToken) {
    return {
      success: false,
      message: "WhatsApp Cloud API not configured. Set WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_API_TOKEN in .env",
    };
  }

  // Format phone: remove spaces, dashes, leading +
  let formattedPhone = phone.replace(/[\s\-\(\)]/g, "");
  if (formattedPhone.startsWith("+")) formattedPhone = formattedPhone.slice(1);
  // Pakistani number without country code
  if (formattedPhone.startsWith("0")) formattedPhone = "92" + formattedPhone.slice(1);

  const url = `https://graph.facebook.com/v25.0/${phoneNumberId}/messages`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      messaging_product: "whatsapp",
      to: formattedPhone,
      type: "text",
      text: { body: message },
    }),
  });

  const data = await res.json();

  if (res.ok && data.messages && data.messages.length > 0) {
    return { success: true, message: `WhatsApp message sent to +${formattedPhone} successfully!` };
  }

  const errMsg = data.error?.message || data.error?.error_data?.details || JSON.stringify(data);
  return { success: false, message: `WhatsApp API error: ${errMsg}` };
}

export async function POST(request: Request) {
  try {
    const { phone, message, mode } = await request.json();

    if (!phone || !message) {
      return NextResponse.json({ success: false, error: "Phone and message required" }, { status: 400 });
    }

    const ts = new Date().toTimeString().slice(0, 8).replace(/:/g, "");
    const phoneSlug = phone.replace(/[^0-9]/g, "");

    if (mode === "draft") {
      const folder = vaultPath("Pending_Approval");
      if (!fs.existsSync(folder)) fs.mkdirSync(folder, { recursive: true });
      const filename = `WHATSAPP_SEND_${ts}_${phoneSlug}.md`;
      const content = `---\ntype: whatsapp_send\nphone: "${phone}"\nstatus: pending\ncreated: ${new Date().toISOString()}\n---\n\n${message}\n`;
      fs.writeFileSync(path.join(folder, filename), content, "utf-8");
      appendAuditLog("whatsapp_draft", "dashboard", filename, "success");
      return NextResponse.json({ success: true, message: `WhatsApp draft saved: ${filename}` });
    }

    // Send via WhatsApp Cloud API
    const result = await sendViaCloudAPI(phone, message);

    appendAuditLog("whatsapp_send", "dashboard", phone, result.success ? "success" : "error");

    if (result.success) {
      const doneFolder = vaultPath("Done");
      if (!fs.existsSync(doneFolder)) fs.mkdirSync(doneFolder, { recursive: true });
      const filename = `WHATSAPP_SENT_${ts}_${phoneSlug}.md`;
      const content = `---\ntype: whatsapp_send\nphone: "${phone}"\nstatus: done\nsent: ${new Date().toISOString()}\n---\n\n${message}\n`;
      fs.writeFileSync(path.join(doneFolder, filename), content, "utf-8");
    }

    return NextResponse.json({ success: result.success, message: result.message });
  } catch (err) {
    return NextResponse.json({ success: false, error: String(err) }, { status: 500 });
  }
}

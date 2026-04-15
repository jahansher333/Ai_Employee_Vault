import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { vaultPath, appendAuditLog } from "@/lib/vault";

export const dynamic = "force-dynamic";

function getEnvValue(key: string): string {
  const envPath = path.resolve(process.cwd(), "..", ".env");
  if (!fs.existsSync(envPath)) return "";
  const content = fs.readFileSync(envPath, "utf-8");
  const match = content.match(new RegExp(`^${key}=(.*)$`, "m"));
  return match ? match[1].trim() : "";
}

async function postToFacebook(content: string, videoUrl?: string): Promise<{ success: boolean; message: string; post_id?: string }> {
  const pageId = getEnvValue("FACEBOOK_PAGE_ID");
  const token = getEnvValue("FACEBOOK_PAGE_ACCESS_TOKEN");
  if (!pageId || !token) return { success: false, message: "Facebook not configured" };

  if (videoUrl) {
    // Video post via /videos endpoint
    const res = await fetch(`https://graph.facebook.com/v18.0/${pageId}/videos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_url: videoUrl, description: content, access_token: token }),
    });
    const data = await res.json();
    if (data.id) return { success: true, message: "Video posted to Facebook!", post_id: data.id };
    return { success: false, message: data.error?.message || "Facebook video post failed" };
  }

  const res = await fetch(`https://graph.facebook.com/v18.0/${pageId}/feed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: content, access_token: token }),
  });
  const data = await res.json();
  if (data.id) return { success: true, message: "Posted to Facebook!", post_id: data.id };
  return { success: false, message: data.error?.message || "Facebook post failed" };
}

async function postToInstagram(content: string, imageUrl?: string, videoUrl?: string): Promise<{ success: boolean; message: string; post_id?: string }> {
  const userId = getEnvValue("INSTAGRAM_USER_ID");
  const token = getEnvValue("INSTAGRAM_ACCESS_TOKEN");
  const defaultImage = getEnvValue("INSTAGRAM_DEFAULT_IMAGE_URL");

  if (!userId || !token) return { success: false, message: "Instagram not configured (missing USER_ID or TOKEN)" };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let containerBody: any;

  if (videoUrl) {
    // Video/Reel post
    containerBody = {
      video_url: videoUrl,
      caption: content,
      media_type: "REELS",
      access_token: token,
    };
  } else {
    const img = imageUrl || defaultImage;
    if (!img) return { success: false, message: "Instagram requires an image or video URL." };
    containerBody = {
      image_url: img,
      caption: content,
      access_token: token,
    };
  }

  // Step 1: Create media container
  const containerRes = await fetch(`https://graph.facebook.com/v18.0/${userId}/media`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(containerBody),
  });
  const containerData = await containerRes.json();
  if (!containerData.id) {
    return { success: false, message: containerData.error?.error_user_msg || containerData.error?.message || "Failed to create Instagram media container" };
  }

  // For video, wait for processing
  if (videoUrl) {
    let status = "IN_PROGRESS";
    let attempts = 0;
    while (status === "IN_PROGRESS" && attempts < 30) {
      await new Promise((r) => setTimeout(r, 2000));
      const checkRes = await fetch(`https://graph.facebook.com/v18.0/${containerData.id}?fields=status_code&access_token=${token}`);
      const checkData = await checkRes.json();
      status = checkData.status_code || "FINISHED";
      attempts++;
    }
    if (status === "ERROR") {
      // Get detailed error
      const errRes = await fetch(`https://graph.facebook.com/v18.0/${containerData.id}?fields=status,status_code&access_token=${token}`);
      const errInfo = await errRes.json().catch(() => ({}));
      return { success: false, message: `Instagram video processing failed: ${JSON.stringify(errInfo).slice(0, 200)}. Check format (MP4, H.264) and size.` };
    }
  }

  // Step 2: Publish
  const publishRes = await fetch(`https://graph.facebook.com/v18.0/${userId}/media_publish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ creation_id: containerData.id, access_token: token }),
  });
  const publishData = await publishRes.json();
  if (publishData.id) return { success: true, message: videoUrl ? "Reel posted to Instagram!" : "Posted to Instagram!", post_id: publishData.id };
  return { success: false, message: publishData.error?.message || "Instagram publish failed" };
}

async function postToLinkedIn(content: string): Promise<{ success: boolean; message: string; post_id?: string }> {
  const token = getEnvValue("LINKEDIN_ACCESS_TOKEN");
  const personUrn = getEnvValue("LINKEDIN_PERSON_URN");
  if (!token || !personUrn) return { success: false, message: "LinkedIn not configured" };

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

  if (res.status === 201) {
    const postId = res.headers.get("X-RestLi-Id") || "";
    return { success: true, message: "Posted to LinkedIn!", post_id: postId };
  }
  const errData = await res.json().catch(() => ({}));
  return { success: false, message: (errData as Record<string, string>).message || `LinkedIn error: ${res.status}` };
}

async function postToTwitter(content: string): Promise<{ success: boolean; message: string; post_id?: string }> {
  // Twitter requires OAuth 1.0a signing which is complex in pure JS
  // Fall back to the Python script for Twitter
  const { exec } = await import("child_process");
  const scriptsDir = path.resolve(vaultPath("scripts"));

  // Write content to a temp file to avoid shell escaping issues
  const tmpFile = path.join(vaultPath(""), ".tmp_tweet.txt");
  fs.writeFileSync(tmpFile, content, "utf-8");

  return new Promise((resolve) => {
    const cmd = `python "${path.join(scriptsDir, "social_poster.py")}" --draft "${content.slice(0, 50).replace(/"/g, "'")}" --platform twitter --publish-direct`;
    // Actually, let's use the API route approach - post via approved file
    const ts = new Date().toTimeString().slice(0, 8).replace(/:/g, "");
    const slug = content.slice(0, 50).replace(/[^a-zA-Z0-9]/g, "-").replace(/-+/g, "-");
    const filename = `TWITTER_${ts}_${slug}.md`;
    const approvedFolder = vaultPath("Approved");
    if (!fs.existsSync(approvedFolder)) fs.mkdirSync(approvedFolder, { recursive: true });
    const fileContent = `---\ntype: social_post\nplatform: twitter\nstatus: approved\ncreated: ${new Date().toISOString()}\n---\n\n## Post Content\n\n${content}\n`;
    fs.writeFileSync(path.join(approvedFolder, filename), fileContent, "utf-8");

    exec(`python "${path.join(scriptsDir, "social_poster.py")}" --publish`, {
      cwd: vaultPath(""),
      timeout: 30000,
    }, (error, stdout) => {
      try { fs.unlinkSync(tmpFile); } catch { /* ignore */ }
      if (error) {
        resolve({ success: false, message: `Twitter: ${error.message}` });
      } else {
        resolve({ success: true, message: "Posted to Twitter!", post_id: stdout.trim().slice(-50) });
      }
    });
  });
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { platform, content, mode, image_url, video_url } = body;

    if (!platform || !content) {
      return NextResponse.json({ success: false, error: "Platform and content are required" }, { status: 400 });
    }

    const platformUpper = platform.toUpperCase();
    const ts = new Date().toTimeString().slice(0, 8).replace(/:/g, "");
    const slug = content.slice(0, 50).replace(/[^a-zA-Z0-9]/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");

    if (mode === "draft" || !mode) {
      // Save as draft to Pending_Approval/
      const folder = vaultPath("Pending_Approval");
      if (!fs.existsSync(folder)) fs.mkdirSync(folder, { recursive: true });

      const filename = `${platformUpper}_${ts}_${slug}.md`;
      const filepath = path.join(folder, filename);

      const fileContent = [
        "---",
        `type: social_post`,
        `platform: ${platform}`,
        `status: pending`,
        `created: ${new Date().toISOString()}`,
        image_url ? `image_url: ${image_url}` : null,
        "---",
        "",
        content,
        "",
      ].filter(Boolean).join("\n");

      fs.writeFileSync(filepath, fileContent, "utf-8");
      appendAuditLog("social_draft", "dashboard", filename, "success");

      return NextResponse.json({
        success: true,
        mode: "draft",
        filename,
        message: "Draft saved to Pending_Approval/",
      });
    }

    // Publish mode — post directly via API
    let result: { success: boolean; message: string; post_id?: string };

    switch (platform.toLowerCase()) {
      case "facebook":
        result = await postToFacebook(content, video_url);
        break;
      case "instagram":
        result = await postToInstagram(content, image_url, video_url);
        break;
      case "linkedin":
        result = await postToLinkedIn(content);
        break;
      case "twitter":
        result = await postToTwitter(content);
        break;
      default:
        return NextResponse.json({ success: false, error: `Unknown platform: ${platform}` }, { status: 400 });
    }

    // Save to Done/ on success
    if (result.success) {
      const doneFolder = vaultPath("Done");
      if (!fs.existsSync(doneFolder)) fs.mkdirSync(doneFolder, { recursive: true });
      const filename = `${platformUpper}_${ts}_${slug}.md`;
      const fileContent = [
        "---",
        `type: social_post`,
        `platform: ${platform}`,
        `status: done`,
        `published: ${new Date().toISOString()}`,
        `post_id: ${result.post_id || ""}`,
        "---",
        "",
        content,
        "",
      ].join("\n");
      fs.writeFileSync(path.join(doneFolder, filename), fileContent, "utf-8");
    }

    appendAuditLog("social_publish", "dashboard", platform, result.success ? "success" : "error");

    return NextResponse.json({
      success: result.success,
      mode: "publish",
      message: result.message,
      post_id: result.post_id,
    });
  } catch (err) {
    return NextResponse.json({ success: false, error: String(err) }, { status: 500 });
  }
}

import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

function getEnvValue(key: string): string {
  const envPath = path.resolve(process.cwd(), "..", ".env");
  if (!fs.existsSync(envPath)) return "";
  const content = fs.readFileSync(envPath, "utf-8");
  const match = content.match(new RegExp(`^${key}=(.*)$`, "m"));
  return match ? match[1].trim() : "";
}

interface Comment {
  id: string;
  from: string;
  message: string;
  created_time: string;
  post_id?: string;
  post_message?: string;
  platform: string;
}

async function fetchFacebookComments(): Promise<{ comments: Comment[]; error?: string }> {
  const pageId = getEnvValue("FACEBOOK_PAGE_ID");
  const token = getEnvValue("FACEBOOK_PAGE_ACCESS_TOKEN");

  if (!pageId || !token) {
    return { comments: [], error: "Facebook not configured (missing PAGE_ID or TOKEN)" };
  }

  try {
    // Get recent posts with their comments
    const postsUrl = `https://graph.facebook.com/v18.0/${pageId}/posts?fields=id,message,created_time,comments.limit(10){id,from,message,created_time}&limit=10&access_token=${token}`;
    const res = await fetch(postsUrl, { signal: AbortSignal.timeout(15000) });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return { comments: [], error: `Facebook API error: ${(err as Record<string, Record<string, string>>).error?.message || res.status}` };
    }

    const data = await res.json();
    const comments: Comment[] = [];

    for (const post of data.data || []) {
      if (post.comments?.data) {
        for (const c of post.comments.data) {
          comments.push({
            id: c.id,
            from: c.from?.name || "Unknown",
            message: c.message || "",
            created_time: c.created_time,
            post_id: post.id,
            post_message: (post.message || "").slice(0, 100),
            platform: "facebook",
          });
        }
      }
    }

    return { comments };
  } catch (err) {
    return { comments: [], error: `Facebook fetch failed: ${String(err)}` };
  }
}

async function fetchLinkedInComments(): Promise<{ comments: Comment[]; error?: string }> {
  const accessToken = getEnvValue("LINKEDIN_ACCESS_TOKEN");
  const personUrn = getEnvValue("LINKEDIN_PERSON_URN");

  if (!accessToken || !personUrn) {
    return { comments: [], error: "LinkedIn not configured (missing ACCESS_TOKEN or PERSON_URN)" };
  }

  // Try multiple LinkedIn API endpoints in order of likelihood to work
  const endpoints: Array<{
    url: string;
    extraHeaders: Record<string, string>;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    extractPosts: (data: any) => Array<{ urn: string; text: string }>;
  }> = [
    // Posts API (Community Management API / Marketing)
    {
      url: `https://api.linkedin.com/rest/posts?author=${encodeURIComponent(personUrn)}&q=author&count=10`,
      extraHeaders: { "LinkedIn-Version": "202401" },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      extractPosts: (data: any) => (data.elements || []).map((p: any) => ({
        urn: p.id || p.urn || "",
        text: (p.commentary || "").slice(0, 100),
      })),
    },
    // UGC Posts API
    {
      url: `https://api.linkedin.com/v2/ugcPosts?q=authors&authors=List(${encodeURIComponent(personUrn)})&count=10`,
      extraHeaders: { "X-Restli-Protocol-Version": "2.0.0" },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      extractPosts: (data: any) => (data.elements || []).map((p: any) => ({
        urn: p.id || "",
        text: (p.specificContent?.["com.linkedin.ugc.ShareContent"]?.shareCommentary?.text || "").slice(0, 100),
      })),
    },
  ];

  for (const ep of endpoints) {
    try {
      const res = await fetch(ep.url, {
        headers: { Authorization: `Bearer ${accessToken}`, ...ep.extraHeaders },
        signal: AbortSignal.timeout(15000),
      });

      if (!res.ok) continue;

      const data = await res.json();
      const posts = ep.extractPosts(data);

      if (posts.length === 0) continue;

      const comments: Comment[] = [];
      for (const post of posts) {
        if (post.urn) {
          const postComments = await fetchLinkedInPostComments(post.urn, accessToken, post.text);
          comments.push(...postComments);
        }
      }

      return { comments };
    } catch {
      continue;
    }
  }

  // All endpoints failed — check if the token itself is valid via userinfo
  try {
    const meRes = await fetch("https://api.linkedin.com/v2/userinfo", {
      headers: { Authorization: `Bearer ${accessToken}` },
      signal: AbortSignal.timeout(10000),
    });

    if (meRes.ok) {
      const profile = await meRes.json();
      return {
        comments: [],
        error: `LinkedIn connected as ${profile.name || "user"} (can post). Reading comments requires the Community Management API (r_member_social) — apply at linkedin.com/developers.`,
      };
    }

    const errText = await meRes.text().catch(() => "");
    return { comments: [], error: `LinkedIn token expired or invalid: ${meRes.status} ${errText.slice(0, 150)}` };
  } catch (err) {
    return { comments: [], error: `LinkedIn fetch failed: ${String(err)}` };
  }
}

async function fetchLinkedInPostComments(postUrn: string, accessToken: string, postText?: string): Promise<Comment[]> {
  // Try both REST and v2 comment endpoints
  const encodedUrn = encodeURIComponent(postUrn);
  const commentEndpoints: Array<{ url: string; extraHeaders: Record<string, string> }> = [
    {
      url: `https://api.linkedin.com/rest/socialActions/${encodedUrn}/comments?count=10`,
      extraHeaders: { "LinkedIn-Version": "202401" },
    },
    {
      url: `https://api.linkedin.com/v2/socialActions/${encodedUrn}/comments?count=10`,
      extraHeaders: { "X-Restli-Protocol-Version": "2.0.0" },
    },
  ];

  for (const ep of commentEndpoints) {
    try {
      const res = await fetch(ep.url, {
        headers: { Authorization: `Bearer ${accessToken}`, ...ep.extraHeaders },
        signal: AbortSignal.timeout(10000),
      });

      if (!res.ok) continue;

      const data = await res.json();
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return (data.elements || []).map((c: any) => ({
        id: c.id || c["$URN"] || "",
        from: c.actor?.["com.linkedin.voyager.feed.MemberActor"]?.miniProfile?.firstName
          || c.actorName || "LinkedIn User",
        message: c.message?.text || c.comment || "",
        created_time: c.created?.time
          ? new Date(Number(c.created.time)).toISOString()
          : new Date().toISOString(),
        post_message: (postText || "").slice(0, 100),
        platform: "linkedin",
      }));
    } catch {
      continue;
    }
  }

  return [];
}

export async function GET() {
  // Fetch comments from both platforms in parallel
  const [fbResult, liResult] = await Promise.all([
    fetchFacebookComments(),
    fetchLinkedInComments(),
  ]);

  const allComments = [...fbResult.comments, ...liResult.comments]
    .sort((a, b) => new Date(b.created_time).getTime() - new Date(a.created_time).getTime());

  return NextResponse.json({
    comments: allComments,
    facebook: {
      count: fbResult.comments.length,
      error: fbResult.error || null,
    },
    linkedin: {
      count: liResult.comments.length,
      error: liResult.error || null,
    },
    fetched_at: new Date().toISOString(),
  });
}

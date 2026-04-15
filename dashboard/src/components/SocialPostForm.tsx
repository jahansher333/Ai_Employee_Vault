"use client";

import { useState, useEffect } from "react";

interface SocialData {
  platforms: Record<string, { drafts: number; posted: number }>;
}

interface Props {
  onToast: (type: "success" | "error", text: string) => void;
}

const platforms = [
  { id: "facebook", label: "Facebook", color: "var(--facebook)", icon: "f", btnClass: "btn-facebook" },
  { id: "instagram", label: "Instagram", color: "var(--instagram)", icon: "IG", btnClass: "btn-instagram" },
  { id: "twitter", label: "Twitter / X", color: "var(--twitter)", icon: "X", btnClass: "btn-twitter" },
  { id: "linkedin", label: "LinkedIn", color: "var(--linkedin)", icon: "in", btnClass: "btn-linkedin" },
];

export default function SocialPostForm({ onToast }: Props) {
  const [content, setContent] = useState("");
  const [platform, setPlatform] = useState("facebook");
  const [mode, setMode] = useState<"draft" | "publish">("draft");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<SocialData | null>(null);
  const [imageUrl, setImageUrl] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [mediaType, setMediaType] = useState<"none" | "image" | "video">("none");

  const fetchData = () => {
    fetch("/api/social")
      .then((r) => r.json())
      .then(setData)
      .catch(() => {});
  };

  useEffect(() => {
    fetchData();
    const iv = setInterval(fetchData, 15000);
    return () => clearInterval(iv);
  }, []);

  const handlePost = async (targetPlatform?: string) => {
    const p = targetPlatform || platform;
    if (!content.trim()) {
      onToast("error", "Post content is empty!");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch("/api/social/post", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platform: p, content: content.trim(), mode, image_url: imageUrl || undefined, video_url: videoUrl || undefined }),
      });
      const result = await res.json();
      if (result.success) {
        onToast("success", `${p.charAt(0).toUpperCase() + p.slice(1)}: ${result.message}`);
        if (mode === "publish" || targetPlatform) setContent("");
        fetchData();
      } else {
        onToast("error", result.error || result.message || "Failed to post");
      }
    } catch {
      onToast("error", "Network error - is API running?");
    }
    setLoading(false);
  };

  const handlePostAll = async () => {
    if (!content.trim()) {
      onToast("error", "Post content is empty!");
      return;
    }
    setLoading(true);
    for (const p of platforms) {
      try {
        const res = await fetch("/api/social/post", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ platform: p.id, content: content.trim(), mode, image_url: imageUrl || undefined }),
        });
        const result = await res.json();
        if (result.success) {
          onToast("success", `${p.label}: ${mode === "draft" ? "Draft saved" : "Published"}`);
        } else {
          onToast("error", `${p.label}: ${result.error || "Failed"}`);
        }
      } catch {
        onToast("error", `${p.label}: Network error`);
      }
    }
    setContent("");
    fetchData();
    setLoading(false);
  };

  return (
    <div>
      {/* Platform Stats Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
        {platforms.map((p) => {
          const stats = data?.platforms?.[p.id] || { drafts: 0, posted: 0 };
          return (
            <div className="platform-card" key={p.id}>
              <div className="platform-header">
                <div className="platform-name">
                  <span style={{ color: p.color, fontWeight: 800, fontSize: 14,
                    background: `${p.color}20`, padding: "4px 8px", borderRadius: 6 }}>{p.icon}</span>
                  <span>{p.label}</span>
                </div>
              </div>
              <div className="platform-stats">
                <span style={{ color: "var(--yellow)" }}>{stats.drafts} drafts</span>
                <span style={{ color: "var(--green)" }}>{stats.posted} posted</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Compose Section */}
      <div className="section">
        <h2><span className="section-icon">{"\u270E"}</span> Compose Post</h2>

        <div className="form-group">
          <label>Post Content</label>
          <textarea
            className="form-input"
            placeholder="Write your post content here... Supports all platforms"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            style={{ minHeight: 120 }}
          />
          <div style={{ textAlign: "right", fontSize: 12, color: "var(--muted)", marginTop: 4 }}>
            {content.length} characters
          </div>
        </div>

        {/* Media Type Selector */}
        <div style={{
          padding: 16, background: "var(--bg)", border: "1px solid var(--border)",
          borderRadius: "var(--radius-sm)", marginBottom: 16,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
            <span style={{ fontSize: 16 }}>{"\uD83D\uDCCE"}</span>
            <label style={{ fontWeight: 700, fontSize: 14, margin: 0 }}>Media Attachment</label>
            {platform === "instagram" && mediaType === "none" && (
              <span className="badge" style={{ background: "var(--yellow-dim)", color: "var(--yellow)", fontSize: 10 }}>
                Instagram needs image or video
              </span>
            )}
          </div>

          {/* Toggle Buttons */}
          <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
            {([
              { key: "none", label: "Text Only", icon: "\u270E" },
              { key: "image", label: "Image", icon: "\uD83D\uDDBC" },
              { key: "video", label: "Video", icon: "\uD83C\uDFA5" },
            ] as const).map((opt) => (
              <button
                key={opt.key}
                type="button"
                onClick={() => { setMediaType(opt.key); if (opt.key === "image") setVideoUrl(""); if (opt.key === "video") setImageUrl(""); if (opt.key === "none") { setImageUrl(""); setVideoUrl(""); } }}
                style={{
                  flex: 1,
                  padding: "10px 14px",
                  borderRadius: "var(--radius-sm)",
                  border: `2px solid ${mediaType === opt.key ? "var(--blue)" : "var(--border)"}`,
                  background: mediaType === opt.key ? "var(--blue-dim)" : "var(--surface)",
                  color: mediaType === opt.key ? "var(--blue)" : "var(--muted)",
                  fontWeight: mediaType === opt.key ? 700 : 500,
                  fontSize: 13,
                  cursor: "pointer",
                  transition: "all 0.15s",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                }}
              >
                <span style={{ fontSize: 16 }}>{opt.icon}</span> {opt.label}
              </button>
            ))}
          </div>

          {/* Image Input */}
          {mediaType === "image" && (
            <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
              <div style={{ flex: 1 }}>
                <input
                  className="form-input"
                  placeholder="https://example.com/image.jpg — paste image URL here"
                  value={imageUrl}
                  onChange={(e) => setImageUrl(e.target.value)}
                  style={{ padding: "10px 14px", width: "100%" }}
                />
                <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 6 }}>
                  {platform === "instagram"
                    ? "Leave blank to use the default image from settings. Supported: JPG, PNG."
                    : "Paste a direct image URL. Supported: JPG, PNG. Works with Facebook & Instagram."}
                </div>
              </div>
              {imageUrl && (
                <div style={{
                  width: 80, height: 80, borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border)", overflow: "hidden", flexShrink: 0,
                  background: "var(--surface)", display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={imageUrl}
                    alt="Preview"
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                    onError={(e) => {
                      const el = e.target as HTMLImageElement;
                      el.style.display = "none";
                      if (el.parentElement) {
                        el.parentElement.innerHTML = '<span style="color:var(--red);font-size:11px;text-align:center">Invalid URL</span>';
                      }
                    }}
                  />
                </div>
              )}
            </div>
          )}

          {/* Video Input */}
          {mediaType === "video" && (
            <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
              <div style={{ flex: 1 }}>
                <input
                  className="form-input"
                  placeholder="https://example.com/video.mp4 — paste video URL here"
                  value={videoUrl}
                  onChange={(e) => setVideoUrl(e.target.value)}
                  style={{ padding: "10px 14px", width: "100%" }}
                />
                <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 6 }}>
                  Supported: MP4 (H.264). Facebook up to 10GB, Instagram Reels up to 15min, LinkedIn up to 200MB.
                </div>
              </div>
              {videoUrl && (
                <div style={{
                  width: 120, height: 80, borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border)", overflow: "hidden", flexShrink: 0,
                  background: "var(--surface)",
                }}>
                  {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                  <video
                    src={videoUrl}
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                    muted
                    onMouseEnter={(e) => (e.target as HTMLVideoElement).play().catch(() => {})}
                    onMouseLeave={(e) => { const v = e.target as HTMLVideoElement; v.pause(); v.currentTime = 0; }}
                    onError={(e) => {
                      const el = e.target as HTMLVideoElement;
                      el.style.display = "none";
                      if (el.parentElement) {
                        el.parentElement.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--muted);font-size:11px;text-align:center;padding:4px">Video preview unavailable</div>';
                      }
                    }}
                  />
                </div>
              )}
            </div>
          )}

          {/* Text Only info */}
          {mediaType === "none" && (
            <div style={{ fontSize: 12, color: "var(--muted)", padding: "4px 0" }}>
              Post will contain text only. Select Image or Video above to attach media.
            </div>
          )}
        </div>

        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <div className="form-group" style={{ margin: 0, minWidth: 150 }}>
            <select className="form-select" value={platform} onChange={(e) => setPlatform(e.target.value)}>
              {platforms.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <select className="form-select" value={mode} onChange={(e) => setMode(e.target.value as "draft" | "publish")}>
              <option value="draft">Save as Draft</option>
              <option value="publish">Publish Now</option>
            </select>
          </div>

          <button className="btn btn-primary" onClick={() => handlePost()} disabled={loading || !content.trim()}>
            {loading ? "Posting..." : mode === "draft" ? "Create Draft" : "Publish"}
          </button>
        </div>

        {/* Quick Post Buttons */}
        <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
          <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 10, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5 }}>
            Quick Post to Platform
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {platforms.map((p) => (
              <button
                key={p.id}
                className={`btn ${p.btnClass}`}
                onClick={() => handlePost(p.id)}
                disabled={loading || !content.trim()}
              >
                {p.icon} Post to {p.label}
              </button>
            ))}
            <button
              className="btn btn-primary"
              onClick={handlePostAll}
              disabled={loading || !content.trim()}
              style={{ background: "linear-gradient(135deg, var(--purple), var(--blue))", border: "none" }}
            >
              Post to ALL Platforms
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

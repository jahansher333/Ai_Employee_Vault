"use client";

import { useEffect, useState } from "react";

interface SocialData {
  platforms: Record<string, { drafts: number; posted: number }>;
}

const platformColors: Record<string, string> = {
  facebook: "#1877f2",
  instagram: "#e4405f",
  twitter: "#1da1f2",
  linkedin: "#0a66c2",
};

export default function SocialSection() {
  const [data, setData] = useState<SocialData | null>(null);

  useEffect(() => {
    fetch("/api/social")
      .then((r) => r.json())
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data) return <div className="section loading">Loading social...</div>;

  const total = Object.values(data.platforms).reduce((sum, p) => sum + p.posted, 0);

  return (
    <div className="section">
      <h2>Social Media ({total} posted)</h2>
      <table>
        <thead>
          <tr><th>Platform</th><th>Drafts</th><th>Posted</th></tr>
        </thead>
        <tbody>
          {Object.entries(data.platforms).map(([name, info]) => (
            <tr key={name}>
              <td style={{ color: platformColors[name] || "var(--text)", fontWeight: 600, textTransform: "capitalize" }}>
                {name}
              </td>
              <td>{info.drafts}</td>
              <td style={{ color: "var(--green)" }}>{info.posted}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

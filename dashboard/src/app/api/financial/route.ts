import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API = process.env.API_URL || "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${API}/api/financial`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ source: "none", success: false });
  }
}

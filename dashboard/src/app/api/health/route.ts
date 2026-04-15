import { NextResponse } from "next/server";
import { VAULT } from "@/lib/vault";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json({
    status: "ok",
    vault: VAULT,
    timestamp: new Date().toISOString(),
  });
}

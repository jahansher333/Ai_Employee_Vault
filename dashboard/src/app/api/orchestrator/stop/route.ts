import { NextResponse } from "next/server";
import { stopOrchestrator } from "@/lib/orchestrator";

export const dynamic = "force-dynamic";

export async function POST() {
  const result = stopOrchestrator();
  return NextResponse.json(result);
}

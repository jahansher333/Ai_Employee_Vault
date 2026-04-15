import { NextResponse } from "next/server";
import { startOrchestrator } from "@/lib/orchestrator";

export const dynamic = "force-dynamic";

export async function POST() {
  const result = startOrchestrator();
  return NextResponse.json(result);
}

import { NextResponse } from "next/server";
import { getOrchestratorState } from "@/lib/orchestrator";

export const dynamic = "force-dynamic";

export function GET() {
  const state = getOrchestratorState();
  return NextResponse.json(state);
}

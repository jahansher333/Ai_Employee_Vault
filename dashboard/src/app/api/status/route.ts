import { NextResponse } from "next/server";
import { countMd } from "@/lib/vault";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json({
    needs_action: countMd("Needs_Action"),
    plans: countMd("Plans"),
    pending_approval: countMd("Pending_Approval"),
    approved: countMd("Approved"),
    done: countMd("Done"),
    archive: countMd("Archive"),
    briefings: countMd("Briefings"),
    timestamp: new Date().toISOString(),
  });
}

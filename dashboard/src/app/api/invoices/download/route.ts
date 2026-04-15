import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { vaultPath } from "@/lib/vault";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const filename = searchParams.get("file");

  if (!filename) {
    return NextResponse.json({ error: "Missing file parameter" }, { status: 400 });
  }

  // Prevent path traversal
  const safeName = path.basename(filename);
  if (!safeName.endsWith(".pdf")) {
    return NextResponse.json({ error: "Only PDF files allowed" }, { status: 400 });
  }

  const filePath = path.join(vaultPath("Invoices"), safeName);

  if (!fs.existsSync(filePath)) {
    return NextResponse.json({ error: "File not found" }, { status: 404 });
  }

  const fileBuffer = fs.readFileSync(filePath);

  return new NextResponse(fileBuffer, {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="${safeName}"`,
      "Content-Length": String(fileBuffer.length),
    },
  });
}

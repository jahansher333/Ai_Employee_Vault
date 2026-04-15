import { NextResponse } from "next/server";
import fs from "fs";
import { vaultPath } from "@/lib/vault";

export const dynamic = "force-dynamic";

export function GET() {
  const invoiceDir = vaultPath("Invoices");
  const invoices: object[] = [];

  if (fs.existsSync(invoiceDir)) {
    const files = fs.readdirSync(invoiceDir).filter((f) => f.endsWith(".pdf"));
    for (const f of files) {
      const stat = fs.statSync(`${invoiceDir}/${f}`);
      invoices.push({
        filename: f,
        size: stat.size,
        created: stat.birthtime.toISOString(),
        name: f.replace(/\.pdf$/, "").replace(/_/g, "/"),
      });
    }
  }

  return NextResponse.json({
    invoices: invoices.sort((a: any, b: any) => b.created.localeCompare(a.created)),
    count: invoices.length,
    directory: "Invoices/",
  });
}

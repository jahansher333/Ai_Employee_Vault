"""PDF Invoice Export — generates PDF invoices from Odoo data.

Uses fpdf2 to create professional invoice PDFs from Odoo invoice records.
Saves to Invoices/ folder.

Usage:
    python scripts/pdf_invoice.py --invoice "INV/2026/00001"
    python scripts/pdf_invoice.py --overdue
    python scripts/pdf_invoice.py --output path/to/dir
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger

load_dotenv()

try:
    from fpdf import FPDF

    class InvoicePDF(FPDF):
        """Custom PDF class for invoice generation."""

        def header(self):
            self.set_font("Helvetica", "B", 16)
            self.cell(0, 10, "INVOICE", align="C", new_x="LMARGIN", new_y="NEXT")
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False
    InvoicePDF = None


def generate_invoice_pdf(invoice_data: dict, output_path: Path) -> Path:
    """Generate a PDF invoice from Odoo invoice data.

    Parameters
    ----------
    invoice_data : dict
        Invoice dict from OdooClient.list_invoices() with keys:
        name, partner_name, amount_total, amount_residual,
        invoice_date, invoice_date_due, payment_state, is_overdue,
        lines (optional list of dicts with name, quantity, price_unit)
    output_path : Path
        Directory to save the PDF

    Returns
    -------
    Path to the generated PDF file.
    """
    if not HAS_FPDF:
        raise ImportError("fpdf2 not installed. Run: pip install fpdf2")

    pdf = InvoicePDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    inv_name = invoice_data.get("name", "DRAFT")
    partner = invoice_data.get("partner_name", "Unknown Customer")
    amount_total = invoice_data.get("amount_total", 0.0)
    amount_residual = invoice_data.get("amount_residual", 0.0)
    inv_date = invoice_data.get("invoice_date", "")
    due_date = invoice_data.get("invoice_date_due", "")
    payment_state = invoice_data.get("payment_state", "not_paid")
    is_overdue = invoice_data.get("is_overdue", False)
    currency = invoice_data.get("currency", "USD")

    # Invoice info
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(95, 8, f"Invoice: {inv_name}", new_x="RIGHT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 8, f"Date: {inv_date}", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 7, f"Customer: {partner}", new_x="RIGHT")
    pdf.cell(95, 7, f"Due Date: {due_date}", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.cell(95, 7, f"Currency: {currency}", new_x="RIGHT")
    status_text = payment_state.replace("_", " ").title()
    pdf.cell(95, 7, f"Status: {status_text}", align="R", new_x="LMARGIN", new_y="NEXT")

    # Overdue warning
    if is_overdue:
        pdf.ln(5)
        pdf.set_fill_color(255, 200, 200)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 10, "*** OVERDUE ***", align="C", fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(10)

    # Line items table
    lines = invoice_data.get("lines", [])
    if lines:
        # Header
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(90, 8, "Description", border=1, fill=True)
        pdf.cell(30, 8, "Qty", border=1, align="C", fill=True)
        pdf.cell(35, 8, "Unit Price", border=1, align="R", fill=True)
        pdf.cell(35, 8, "Total", border=1, align="R", fill=True, new_x="LMARGIN", new_y="NEXT")

        # Rows
        pdf.set_font("Helvetica", "", 10)
        for line in lines:
            name = str(line.get("name", "Item"))[:45]
            qty = line.get("quantity", 1)
            price = line.get("price_unit", 0.0)
            total = qty * price
            pdf.cell(90, 7, name, border=1)
            pdf.cell(30, 7, str(qty), border=1, align="C")
            pdf.cell(35, 7, f"${price:,.2f}", border=1, align="R")
            pdf.cell(35, 7, f"${total:,.2f}", border=1, align="R", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 8, "(Line item details not available from Odoo summary)", new_x="LMARGIN", new_y="NEXT")

    # Totals
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(120, 10, "")
    pdf.cell(35, 10, "Total:", align="R")
    pdf.cell(35, 10, f"${amount_total:,.2f}", align="R", new_x="LMARGIN", new_y="NEXT")

    if amount_residual > 0 and amount_residual != amount_total:
        pdf.cell(120, 10, "")
        pdf.set_text_color(200, 0, 0)
        pdf.cell(35, 10, "Balance Due:", align="R")
        pdf.cell(35, 10, f"${amount_residual:,.2f}", align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

    # Footer note
    pdf.ln(15)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, f"Generated by AI Employee on {date.today().isoformat()}", align="C")

    # Save
    output_path.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r'[^\w\-]', '_', inv_name)
    pdf_path = output_path / f"{safe_name}.pdf"
    pdf.output(str(pdf_path))
    return pdf_path


def export_invoice(
    invoice_name: str,
    vault_path: Path,
    output_dir: Path | None = None,
) -> Path:
    """Fetch invoice from Odoo and generate PDF."""
    from odoo_client import OdooClient

    client = OdooClient()
    invoices = client.list_invoices(limit=200, state="all")

    match = None
    for inv in invoices:
        if inv["name"] == invoice_name or str(inv.get("id")) == str(invoice_name):
            match = inv
            break

    if not match:
        raise ValueError(f"Invoice '{invoice_name}' not found in Odoo")

    out = output_dir or vault_path / "Invoices"
    pdf_path = generate_invoice_pdf(match, out)

    logger = AuditLogger(vault_path)
    logger.log("invoice_pdf_exported", match["name"], "success",
               details={"path": str(pdf_path), "amount": match["amount_total"]})

    return pdf_path


def export_all_overdue(
    vault_path: Path,
    output_dir: Path | None = None,
) -> list[Path]:
    """Export all overdue invoices as PDFs."""
    from odoo_client import OdooClient

    client = OdooClient()
    overdue = client.get_overdue_invoices()

    if not overdue:
        print("No overdue invoices to export.")
        return []

    out = output_dir or vault_path / "Invoices"
    logger = AuditLogger(vault_path)
    paths = []

    for inv in overdue:
        try:
            pdf_path = generate_invoice_pdf(inv, out)
            paths.append(pdf_path)
            print(f"  [PDF] {inv['name']} -> {pdf_path.name}")
        except Exception as exc:
            print(f"  [ERROR] {inv['name']}: {exc}")

    logger.log("overdue_pdfs_exported", "system", "success",
               details={"count": len(paths)})
    return paths


def main() -> None:
    if not HAS_FPDF:
        print("ERROR: fpdf2 not installed. Run: pip install fpdf2")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="PDF Invoice Export")
    parser.add_argument("--invoice", type=str, help="Invoice name (e.g. INV/2026/00001)")
    parser.add_argument("--overdue", action="store_true", help="Export all overdue invoices")
    parser.add_argument("--output", type=str, help="Output directory")
    parser.add_argument("--vault-path", default=None)
    args = parser.parse_args()

    vault = Path(args.vault_path or os.getenv("VAULT_PATH", str(Path(__file__).parent.parent)))
    output = Path(args.output) if args.output else None

    if args.invoice:
        path = export_invoice(args.invoice, vault, output)
        print(f"PDF saved: {path}")
        return

    if args.overdue:
        paths = export_all_overdue(vault, output)
        print(f"\nExported {len(paths)} overdue invoice PDFs.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()

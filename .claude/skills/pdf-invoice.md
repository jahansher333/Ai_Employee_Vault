# PDF Invoice Export Skill

## Purpose
Generate PDF invoices from Odoo data. Export individual invoices or batch-export all overdue invoices.

## When to Use
- User asks to "export invoice as PDF"
- User wants to send invoice to a client
- Weekly briefing needs PDF attachments for overdue invoices

## Prerequisites
- `fpdf2` installed: `pip install fpdf2`
- Odoo connection configured in `.env`

## Commands
```bash
# Export a specific invoice
python scripts/pdf_invoice.py --invoice "INV/2026/00001"

# Export all overdue invoices
python scripts/pdf_invoice.py --overdue

# Custom output directory
python scripts/pdf_invoice.py --overdue --output path/to/dir
```

## PDF Content
- Company header
- Invoice number, date, due date
- Customer information
- Line items table (description, qty, price, total)
- Total amount and balance due
- Overdue warning (red highlight if past due)

## Output
PDFs saved to `Invoices/` folder (or custom path via `--output`).

## Configuration
Uses same Odoo credentials from `.env`:
- `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD`

## Script
`scripts/pdf_invoice.py`

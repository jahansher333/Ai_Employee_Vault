"""Tests for pdf_invoice.py."""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

from scripts.pdf_invoice import generate_invoice_pdf


SAMPLE_INVOICE = {
    "id": 1,
    "name": "INV/2026/00001",
    "partner_name": "Acme Corporation",
    "amount_total": 2000.00,
    "amount_residual": 2000.00,
    "currency": "USD",
    "invoice_date": "2026-03-01",
    "invoice_date_due": "2026-03-15",
    "payment_state": "not_paid",
    "is_overdue": True,
    "move_type": "out_invoice",
    "lines": [
        {"name": "Consulting Services", "quantity": 10, "price_unit": 150.0},
        {"name": "Setup Fee", "quantity": 1, "price_unit": 500.0},
    ],
}


@pytest.mark.skipif(not HAS_FPDF, reason="fpdf2 not installed")
class TestPdfGeneration:
    def test_creates_pdf_file(self, tmp_path):
        path = generate_invoice_pdf(SAMPLE_INVOICE, tmp_path)
        assert path.exists()
        assert path.suffix == ".pdf"
        assert path.stat().st_size > 0

    def test_filename_from_invoice_name(self, tmp_path):
        path = generate_invoice_pdf(SAMPLE_INVOICE, tmp_path)
        assert "INV_2026_00001" in path.name

    def test_overdue_invoice(self, tmp_path):
        invoice = {**SAMPLE_INVOICE, "is_overdue": True}
        path = generate_invoice_pdf(invoice, tmp_path)
        assert path.exists()

    def test_paid_invoice(self, tmp_path):
        invoice = {
            **SAMPLE_INVOICE,
            "payment_state": "paid",
            "is_overdue": False,
            "amount_residual": 0,
        }
        path = generate_invoice_pdf(invoice, tmp_path)
        assert path.exists()

    def test_no_line_items(self, tmp_path):
        invoice = {**SAMPLE_INVOICE, "lines": []}
        path = generate_invoice_pdf(invoice, tmp_path)
        assert path.exists()

    def test_missing_fields(self, tmp_path):
        minimal = {"name": "DRAFT", "amount_total": 100.0}
        path = generate_invoice_pdf(minimal, tmp_path)
        assert path.exists()

    def test_creates_output_dir(self, tmp_path):
        out = tmp_path / "new_dir" / "invoices"
        path = generate_invoice_pdf(SAMPLE_INVOICE, out)
        assert out.is_dir()
        assert path.exists()

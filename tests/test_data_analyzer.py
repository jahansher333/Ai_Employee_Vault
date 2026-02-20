"""Tests for scripts/data_analyzer.py."""

from __future__ import annotations

from pathlib import Path

import pytest
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from data_analyzer import (
    analyze,
    clean_data,
    detect_anomalies,
    generate_analytics_markdown,
    map_columns,
    read_financial_csv,
    update_dashboard_analytics,
)


# ---------------------------------------------------------------------------
# Column mapping tests
# ---------------------------------------------------------------------------

class TestMapColumns:
    def test_exact_match(self):
        result = map_columns(["date", "description", "amount", "category"])
        assert result["date"] == "date"
        assert result["description"] == "description"
        assert result["amount"] == "amount"
        assert result["category"] == "category"

    def test_synonym_match(self):
        result = map_columns(["trans_date", "memo", "value", "type"])
        assert result["date"] == "trans_date"
        assert result["description"] == "memo"
        assert result["amount"] == "value"
        assert result["category"] == "type"

    def test_missing_columns(self):
        result = map_columns(["foo", "bar"])
        assert result["amount"] is None
        assert result["date"] is None

    def test_debit_credit_fallback(self):
        result = map_columns(["debit", "credit", "description"])
        assert result["amount"] is None
        assert result.get("_debit") == "debit"
        assert result.get("_credit") == "credit"

    def test_case_insensitive(self):
        # Column names are compared lowercased
        result = map_columns(["Date", "Amount", "Description", "Category"])
        assert result["date"] == "Date"
        assert result["amount"] == "Amount"


# ---------------------------------------------------------------------------
# CSV reading tests
# ---------------------------------------------------------------------------

class TestReadFinancialCSV:
    def test_standard_csv(self, tmp_path):
        csv = tmp_path / "test.csv"
        csv.write_text(
            "date,description,amount,category\n"
            "2026-01-15,Client Payment,5000.00,Revenue\n"
            "2026-01-16,Office Supplies,-150.00,Operations\n",
            encoding="utf-8",
        )
        df = read_financial_csv(csv)
        assert len(df) == 2
        assert "amount" in df.columns
        assert "date" in df.columns
        assert df["amount"].iloc[0] == 5000.00

    def test_missing_amount_column(self, tmp_path):
        csv = tmp_path / "bad.csv"
        csv.write_text("name,value_x\nfoo,100\n", encoding="utf-8")
        df = read_financial_csv(csv)
        assert df.empty

    def test_nonexistent_file(self, tmp_path):
        df = read_financial_csv(tmp_path / "nope.csv")
        assert df.empty

    def test_debit_credit_columns(self, tmp_path):
        csv = tmp_path / "dc.csv"
        csv.write_text(
            "description,debit,credit\n"
            "Payment,0,500\n"
            "Expense,200,0\n",
            encoding="utf-8",
        )
        df = read_financial_csv(csv)
        assert len(df) == 2
        assert df["amount"].iloc[0] == 500.0  # credit - debit
        assert df["amount"].iloc[1] == -200.0


# ---------------------------------------------------------------------------
# Clean data tests
# ---------------------------------------------------------------------------

class TestCleanData:
    def test_removes_nan_amounts(self):
        df = pd.DataFrame({
            "date": [pd.NaT, pd.Timestamp("2026-01-01")],
            "description": ["bad", "good"],
            "amount": [float("nan"), 100.0],
            "category": ["A", "B"],
        })
        cleaned = clean_data(df)
        assert len(cleaned) == 1

    def test_removes_duplicates(self):
        df = pd.DataFrame({
            "date": [pd.Timestamp("2026-01-01")] * 3,
            "description": ["Same"] * 3,
            "amount": [100.0] * 3,
            "category": ["A"] * 3,
        })
        cleaned = clean_data(df)
        assert len(cleaned) == 1

    def test_fills_missing_category(self):
        df = pd.DataFrame({
            "date": [pd.Timestamp("2026-01-01")],
            "description": ["Test"],
            "amount": [50.0],
            "category": [None],
        })
        cleaned = clean_data(df)
        assert cleaned["category"].iloc[0] == "Uncategorized"

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        assert clean_data(df).empty


# ---------------------------------------------------------------------------
# Analysis tests
# ---------------------------------------------------------------------------

class TestAnalyze:
    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame({
            "date": pd.to_datetime(["2026-01-15", "2026-01-16", "2026-02-01"]),
            "description": ["Client Payment", "Office Rent", "Client Payment"],
            "amount": [5000.0, -1500.0, 3000.0],
            "category": ["Revenue", "Operations", "Revenue"],
        })

    def test_totals(self, sample_df):
        result = analyze(sample_df)
        assert result["total_revenue"] == 8000.0
        assert result["total_expenses"] == 1500.0
        assert result["net_income"] == 6500.0

    def test_monthly_breakdown(self, sample_df):
        result = analyze(sample_df)
        months = result["monthly_breakdown"]
        assert len(months) == 2
        jan = next(m for m in months if m["month"] == "2026-01")
        assert jan["revenue"] == 5000.0
        assert jan["expenses"] == 1500.0

    def test_top_expenses(self, sample_df):
        result = analyze(sample_df)
        assert len(result["top_expenses"]) == 1
        assert result["top_expenses"][0]["amount"] == 1500.0

    def test_empty_dataframe(self):
        result = analyze(pd.DataFrame())
        assert result["total_revenue"] == 0.0
        assert result["total_expenses"] == 0.0


# ---------------------------------------------------------------------------
# Anomaly detection tests
# ---------------------------------------------------------------------------

class TestDetectAnomalies:
    def test_detects_anomaly(self):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2026-01-01"] * 4),
            "description": ["Normal", "Normal", "Normal", "HUGE"],
            "amount": [-100.0, -120.0, -80.0, -1000.0],
            "category": ["Ops"] * 4,
        })
        anomalies = detect_anomalies(df)
        assert len(anomalies) == 1
        assert anomalies[0]["description"] == "HUGE"
        assert anomalies[0]["ratio"] > 2.0

    def test_no_anomalies(self):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2026-01-01"] * 3),
            "description": ["A", "B", "C"],
            "amount": [100.0, 110.0, 90.0],
            "category": ["Rev"] * 3,
        })
        assert detect_anomalies(df) == []

    def test_skips_single_item_category(self):
        df = pd.DataFrame({
            "date": [pd.Timestamp("2026-01-01")],
            "description": ["Solo"],
            "amount": [99999.0],
            "category": ["Unique"],
        })
        assert detect_anomalies(df) == []

    def test_empty_dataframe(self):
        assert detect_anomalies(pd.DataFrame()) == []


# ---------------------------------------------------------------------------
# Markdown generation tests
# ---------------------------------------------------------------------------

class TestGenerateAnalyticsMarkdown:
    def test_contains_sections(self):
        summary = {
            "total_revenue": 10000.0,
            "total_expenses": 5000.0,
            "net_income": 5000.0,
            "monthly_breakdown": [
                {"month": "2026-01", "revenue": 10000, "expenses": 5000, "net": 5000, "transaction_count": 5}
            ],
            "top_expenses": [
                {"date": "2026-01-10", "description": "Rent", "amount": 3000.0, "category": "Ops"}
            ],
            "anomalies": [],
            "generated_at": "2026-02-21T10:00:00+00:00",
            "files_analyzed": ["test.csv"],
        }
        md = generate_analytics_markdown(summary)
        assert "## Business Analytics" in md
        assert "### Financial Summary" in md
        assert "$10,000.00" in md
        assert "### Monthly Breakdown" in md
        assert "2026-01" in md
        assert "### Top 5 Expenses" in md
        assert "Rent" in md
        assert "No anomalies detected" in md

    def test_with_anomalies(self):
        summary = {
            "total_revenue": 1000.0,
            "total_expenses": 500.0,
            "net_income": 500.0,
            "monthly_breakdown": [],
            "top_expenses": [],
            "anomalies": [
                {"date": "2026-01-01", "description": "Big", "amount": -999.0,
                 "category": "Test", "category_avg": 100.0, "ratio": 9.9}
            ],
            "generated_at": "2026-02-21T10:00:00",
            "files_analyzed": [],
        }
        md = generate_analytics_markdown(summary)
        assert "### Anomaly Alerts" in md
        assert "Big" in md
        assert "9.9x" in md


# ---------------------------------------------------------------------------
# Dashboard update tests
# ---------------------------------------------------------------------------

class TestUpdateDashboardAnalytics:
    def test_replaces_between_markers(self, tmp_path):
        dashboard = tmp_path / "Dashboard.md"
        dashboard.write_text(
            "# Dashboard\n\n"
            "<!-- START_ANALYTICS -->\nOld content\n<!-- END_ANALYTICS -->\n\n"
            "## Footer\n",
            encoding="utf-8",
        )
        update_dashboard_analytics(tmp_path, "New analytics content\n")
        result = dashboard.read_text(encoding="utf-8")
        assert "New analytics content" in result
        assert "Old content" not in result
        assert "## Footer" in result

    def test_no_markers_warns(self, tmp_path, capsys):
        dashboard = tmp_path / "Dashboard.md"
        dashboard.write_text("# No markers here\n", encoding="utf-8")
        update_dashboard_analytics(tmp_path, "test")
        captured = capsys.readouterr()
        assert "WARN" in captured.out

    def test_no_dashboard_warns(self, tmp_path, capsys):
        update_dashboard_analytics(tmp_path, "test")
        captured = capsys.readouterr()
        assert "WARN" in captured.out

"""Data Analyzer Skill -- reads CSV financial data and updates Dashboard.

Silver Tier: Reads CSV files from Accounting/, cleans data with pandas,
calculates revenue/expenses/net income, groups by month, detects
anomalies (>2x category average), and updates Dashboard.md with a
Business Analytics section.

Usage:
    python scripts/data_analyzer.py [--vault-path /path]
    python scripts/data_analyzer.py --file Accounting/specific.csv
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger

# Column name synonyms for flexible CSV mapping
COLUMN_SYNONYMS: dict[str, list[str]] = {
    "amount": ["amount", "value", "total", "sum"],
    "date": ["date", "transaction_date", "trans_date", "posted_date"],
    "category": ["category", "type", "class", "department"],
    "description": ["description", "memo", "note", "details", "payee"],
}


# ---------------------------------------------------------------------------
# Column mapping
# ---------------------------------------------------------------------------

def map_columns(columns: list[str]) -> dict[str, str | None]:
    """Map standard column names to actual CSV column names.

    Returns a dict like {"amount": "Amount", "date": "trans_date", ...}.
    Values are None if no matching column found.
    """
    lower_cols = {c.lower().strip(): c for c in columns}
    mapping: dict[str, str | None] = {}

    for standard, synonyms in COLUMN_SYNONYMS.items():
        found = None
        for syn in synonyms:
            if syn in lower_cols:
                found = lower_cols[syn]
                break
        mapping[standard] = found

    # Special case: debit/credit columns
    if mapping["amount"] is None:
        debit = lower_cols.get("debit")
        credit = lower_cols.get("credit")
        if debit and credit:
            mapping["_debit"] = debit
            mapping["_credit"] = credit

    return mapping


# ---------------------------------------------------------------------------
# CSV reading and cleaning
# ---------------------------------------------------------------------------

def read_financial_csv(file_path: Path) -> pd.DataFrame:
    """Read a CSV file and normalize to standard columns.

    Returns a DataFrame with columns: date, description, amount, category.
    Returns empty DataFrame if file is unreadable.
    """
    if not HAS_PANDAS:
        print("ERROR: pandas not installed. Run: pip install pandas")
        return pd.DataFrame()

    try:
        df = pd.read_csv(file_path, encoding="utf-8")
    except Exception as e:
        print(f"  [WARN] Could not read {file_path.name}: {e}")
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    col_map = map_columns(list(df.columns))

    result = pd.DataFrame()

    # Amount
    if col_map.get("amount"):
        result["amount"] = pd.to_numeric(df[col_map["amount"]], errors="coerce")
    elif col_map.get("_debit") and col_map.get("_credit"):
        debit = pd.to_numeric(df[col_map["_debit"]], errors="coerce").fillna(0)
        credit = pd.to_numeric(df[col_map["_credit"]], errors="coerce").fillna(0)
        result["amount"] = credit - debit
    else:
        print(f"  [WARN] No amount column found in {file_path.name}")
        return pd.DataFrame()

    # Date
    if col_map.get("date"):
        result["date"] = pd.to_datetime(df[col_map["date"]], errors="coerce")
    else:
        result["date"] = pd.NaT

    # Description
    if col_map.get("description"):
        result["description"] = df[col_map["description"]].fillna("(No description)")
    else:
        result["description"] = "(No description)"

    # Category
    if col_map.get("category"):
        result["category"] = df[col_map["category"]].fillna("Uncategorized")
    else:
        result["category"] = "Uncategorized"

    return result


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean financial data: remove duplicates, drop rows with no amount."""
    if df.empty:
        return df

    # Drop rows where amount is NaN
    df = df.dropna(subset=["amount"])

    # Remove exact duplicates
    df = df.drop_duplicates()

    # Fill missing categories
    df["category"] = df["category"].fillna("Uncategorized")

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(df: pd.DataFrame) -> dict:
    """Analyze financial data and return summary dict.

    Returns dict with keys: total_revenue, total_expenses, net_income,
    monthly_breakdown, top_expenses, anomalies, generated_at, files_analyzed.
    """
    if df.empty:
        return {
            "total_revenue": 0.0,
            "total_expenses": 0.0,
            "net_income": 0.0,
            "monthly_breakdown": [],
            "top_expenses": [],
            "anomalies": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "files_analyzed": [],
        }

    revenue_mask = df["amount"] > 0
    expense_mask = df["amount"] < 0

    total_revenue = float(df.loc[revenue_mask, "amount"].sum())
    total_expenses = float(df.loc[expense_mask, "amount"].abs().sum())
    net_income = total_revenue - total_expenses

    # Monthly breakdown
    monthly = []
    if df["date"].notna().any():
        df_with_date = df.copy()
        df_with_date["month"] = df_with_date["date"].dt.strftime("%Y-%m")
        df_with_date["month"] = df_with_date["month"].fillna("Unknown")

        for month, group in df_with_date.groupby("month", sort=True):
            rev = float(group.loc[group["amount"] > 0, "amount"].sum())
            exp = float(group.loc[group["amount"] < 0, "amount"].abs().sum())
            monthly.append(
                {
                    "month": str(month),
                    "revenue": rev,
                    "expenses": exp,
                    "net": rev - exp,
                    "transaction_count": len(group),
                }
            )

    # Top 5 expenses
    expenses_df = df.loc[expense_mask].copy()
    expenses_df["abs_amount"] = expenses_df["amount"].abs()
    top5 = expenses_df.nlargest(5, "abs_amount")
    top_expenses = []
    for _, row in top5.iterrows():
        date_str = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "N/A"
        top_expenses.append(
            {
                "date": date_str,
                "description": str(row["description"]),
                "amount": float(row["abs_amount"]),
                "category": str(row["category"]),
            }
        )

    # Anomalies
    anomalies = detect_anomalies(df)

    return {
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_income": net_income,
        "monthly_breakdown": monthly,
        "top_expenses": top_expenses,
        "anomalies": anomalies,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files_analyzed": [],
    }


def detect_anomalies(df: pd.DataFrame) -> list[dict]:
    """Detect anomalous transactions (|amount| > 2x category average).

    Skips categories with only 1 transaction.
    """
    if df.empty:
        return []

    anomalies = []
    df_abs = df.copy()
    df_abs["abs_amount"] = df_abs["amount"].abs()

    for category, group in df_abs.groupby("category"):
        if len(group) < 2:
            continue
        cat_avg = group["abs_amount"].mean()
        if cat_avg == 0:
            continue
        flagged = group[group["abs_amount"] > 2 * cat_avg]
        for _, row in flagged.iterrows():
            date_str = (
                row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "N/A"
            )
            anomalies.append(
                {
                    "date": date_str,
                    "description": str(row["description"]),
                    "amount": float(row["amount"]),
                    "category": str(category),
                    "category_avg": round(cat_avg, 2),
                    "ratio": round(float(row["abs_amount"]) / cat_avg, 1),
                }
            )

    return anomalies


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def _fmt_currency(value: float) -> str:
    """Format a number as currency string."""
    return f"${value:,.2f}"


def generate_analytics_markdown(summary: dict) -> str:
    """Generate a Markdown analytics section from a summary dict."""
    ts = summary.get("generated_at", "N/A")
    if "T" in str(ts):
        ts = str(ts).split("T")[0] + " " + str(ts).split("T")[1][:5] + " UTC"
    files_count = len(summary.get("files_analyzed", []))

    lines = [
        "## Business Analytics",
        "",
        f"**Last Updated**: {ts} | **Files Analyzed**: {files_count}",
        "",
    ]

    # Financial Summary
    lines.extend(
        [
            "### Financial Summary",
            "",
            "| Metric | Amount |",
            "|--------|--------|",
            f"| Total Revenue | {_fmt_currency(summary['total_revenue'])} |",
            f"| Total Expenses | {_fmt_currency(summary['total_expenses'])} |",
            f"| Net Income | {_fmt_currency(summary['net_income'])} |",
            "",
        ]
    )

    # Monthly Breakdown
    monthly = summary.get("monthly_breakdown", [])
    if monthly:
        lines.extend(
            [
                "### Monthly Breakdown",
                "",
                "| Month | Revenue | Expenses | Net |",
                "|-------|---------|----------|-----|",
            ]
        )
        for m in monthly:
            lines.append(
                f"| {m['month']} "
                f"| {_fmt_currency(m['revenue'])} "
                f"| {_fmt_currency(m['expenses'])} "
                f"| {_fmt_currency(m['net'])} |"
            )
        lines.append("")

    # Top 5 Expenses
    top = summary.get("top_expenses", [])
    if top:
        lines.extend(
            [
                "### Top 5 Expenses",
                "",
                "| Date | Description | Amount | Category |",
                "|------|-------------|--------|----------|",
            ]
        )
        for t in top:
            lines.append(
                f"| {t['date']} "
                f"| {t['description']} "
                f"| {_fmt_currency(t['amount'])} "
                f"| {t['category']} |"
            )
        lines.append("")

    # Anomaly Alerts
    anomalies = summary.get("anomalies", [])
    if anomalies:
        lines.extend(
            [
                "### Anomaly Alerts",
                "",
                "| Date | Description | Amount | Category | Avg | Ratio |",
                "|------|-------------|--------|----------|-----|-------|",
            ]
        )
        for a in anomalies:
            lines.append(
                f"| {a['date']} "
                f"| {a['description']} "
                f"| {_fmt_currency(abs(a['amount']))} "
                f"| {a['category']} "
                f"| {_fmt_currency(a['category_avg'])} "
                f"| {a['ratio']}x |"
            )
        lines.append("")
    else:
        lines.extend(["### Anomaly Alerts", "", "No anomalies detected.", ""])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dashboard integration
# ---------------------------------------------------------------------------

def update_dashboard_analytics(vault_path: Path, markdown: str) -> None:
    """Replace content between analytics markers in Dashboard.md."""
    dashboard = vault_path / "Dashboard.md"
    if not dashboard.exists():
        print("  [WARN] Dashboard.md not found")
        return

    content = dashboard.read_text(encoding="utf-8")
    start_marker = "<!-- START_ANALYTICS -->"
    end_marker = "<!-- END_ANALYTICS -->"

    if start_marker not in content or end_marker not in content:
        print("  [WARN] Analytics markers not found in Dashboard.md")
        return

    start_idx = content.index(start_marker) + len(start_marker)
    end_idx = content.index(end_marker)

    updated = content[:start_idx] + "\n" + markdown + "\n" + content[end_idx:]
    dashboard.write_text(updated, encoding="utf-8")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_analysis(vault_path: Path) -> dict:
    """Run full analysis: read CSVs, analyze, update dashboard, log."""
    if not HAS_PANDAS:
        print("ERROR: pandas not installed. Run: pip install pandas")
        return {}

    logger = AuditLogger(vault_path)
    accounting = vault_path / "Accounting"

    if not accounting.exists():
        print("No Accounting/ folder found.")
        return {}

    csv_files = sorted(accounting.glob("*.csv"))
    if not csv_files:
        print("No CSV files found in Accounting/.")
        # Update dashboard with empty state
        update_dashboard_analytics(vault_path, "No financial data available.\n")
        return {}

    logger.log(
        "analytics_started",
        "system",
        "success",
        details={"files_found": len(csv_files)},
    )
    print(f"Analyzing {len(csv_files)} CSV file(s) from Accounting/...\n")

    all_frames = []
    filenames = []

    for csv_file in csv_files:
        df = read_financial_csv(csv_file)
        if df.empty:
            logger.log(
                "csv_loaded",
                csv_file.name,
                "error",
                error="No valid data found",
            )
            continue

        df = clean_data(df)
        logger.log(
            "csv_loaded",
            csv_file.name,
            "success",
            details={"rows": len(df)},
        )
        print(f"  [LOADED] {csv_file.name}: {len(df)} rows")
        all_frames.append(df)
        filenames.append(csv_file.name)

    if not all_frames:
        print("No valid financial data found.")
        update_dashboard_analytics(vault_path, "No financial data available.\n")
        return {}

    combined = pd.concat(all_frames, ignore_index=True)
    summary = analyze(combined)
    summary["files_analyzed"] = filenames

    # Log anomalies
    for a in summary.get("anomalies", []):
        logger.log(
            "anomaly_detected",
            a["description"],
            "success",
            details={
                "amount": a["amount"],
                "category": a["category"],
                "ratio": a["ratio"],
            },
        )

    # Generate Markdown and update dashboard
    md = generate_analytics_markdown(summary)
    update_dashboard_analytics(vault_path, md)

    logger.log(
        "analytics_completed",
        "system",
        "success",
        details={
            "total_revenue": summary["total_revenue"],
            "total_expenses": summary["total_expenses"],
            "anomalies_count": len(summary.get("anomalies", [])),
            "files_analyzed": len(filenames),
        },
    )

    # Print report
    print("\n" + "=" * 60)
    print("# DataAnalyzerSkill Report")
    print("=" * 60)
    print(f"\n{md}")
    print("=" * 60)

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Financial Data Analyzer")
    parser.add_argument("--vault-path", default=None)
    parser.add_argument("--file", default=None, help="Analyze a specific CSV file")
    args = parser.parse_args()

    vault = Path(
        args.vault_path
        or os.getenv("VAULT_PATH", str(Path(__file__).parent.parent))
    )

    if args.file:
        file_path = Path(args.file)
        if not file_path.is_absolute():
            file_path = vault / file_path
        if not file_path.exists():
            print(f"File not found: {file_path}")
            sys.exit(1)
        df = read_financial_csv(file_path)
        df = clean_data(df)
        summary = analyze(df)
        summary["files_analyzed"] = [file_path.name]
        md = generate_analytics_markdown(summary)
        print(md)
        return

    run_analysis(vault)


if __name__ == "__main__":
    main()

# DataAnalyzerSkill

**Tier**: Silver
**Module**: `scripts/data_analyzer.py`
**Trigger**: Manual (`python scripts/data_analyzer.py`) or scheduled

## Purpose

Reads financial CSV data from `Accounting/`, performs analysis using pandas,
and updates Dashboard.md with a Business Analytics section.

## What It Does

1. Scans `Accounting/` for `.csv` files
2. Reads and normalizes CSV columns (flexible column name mapping)
3. Cleans data (removes duplicates, handles missing values)
4. Calculates: Total Revenue, Total Expenses, Net Income
5. Groups results by month for trend analysis
6. Detects anomalies (transactions >2x category average)
7. Generates Markdown tables and updates Dashboard.md
8. Logs all events to audit trail

## Output Format

Dashboard.md receives a Business Analytics section with:

| Section | Content |
|---------|---------|
| Financial Summary | Revenue, Expenses, Net Income table |
| Monthly Breakdown | Per-month revenue/expenses/net |
| Top 5 Expenses | Largest expense transactions |
| Anomaly Alerts | Flagged unusual transactions |

## Usage

```bash
# Analyze all CSVs in Accounting/
python scripts/data_analyzer.py

# Analyze a specific file
python scripts/data_analyzer.py --file Accounting/q1-report.csv
```

## CSV Requirements

Minimum: a column mappable to `amount` (or `debit`+`credit` pair).
Optional: `date`, `description`, `category` columns.
Positive amounts = revenue, negative = expenses.

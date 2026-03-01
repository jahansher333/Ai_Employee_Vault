# Contract: Data Analyzer Skill

**Module**: `scripts/data_analyzer.py`
**Purpose**: Read CSV financial data from Accounting/, analyze, and update Dashboard

## Public Interface

### `read_financial_csv(file_path) -> pd.DataFrame`
- **Input**: Path to a CSV file
- **Output**: DataFrame with normalized columns: date, description, amount, category
- **Errors**: Returns empty DataFrame with warning log if file unreadable or no valid columns found
- **Side effects**: None

### `map_columns(df, original_columns) -> dict[str, str]`
- **Input**: DataFrame, list of original column names
- **Output**: Mapping of standard names to actual column names
- **Errors**: Returns partial mapping if some columns not found
- **Side effects**: None

### `clean_data(df) -> df`
- **Input**: DataFrame with raw financial data
- **Output**: Cleaned DataFrame (duplicates removed, amounts parsed, dates parsed, categories filled)
- **Errors**: Logs warnings for skipped rows
- **Side effects**: None

### `analyze(df) -> AnalyticsSummary`
- **Input**: Cleaned DataFrame
- **Output**: AnalyticsSummary dict with totals, monthly breakdown, top expenses, anomalies
- **Errors**: Returns empty summary if DataFrame is empty
- **Side effects**: None

### `detect_anomalies(df) -> list[dict]`
- **Input**: Cleaned DataFrame
- **Output**: List of anomaly dicts (transaction + category_avg + ratio)
- **Errors**: None (returns empty list if insufficient data)
- **Side effects**: None

### `generate_analytics_markdown(summary) -> str`
- **Input**: AnalyticsSummary dict
- **Output**: Markdown string with tables for revenue/expenses, monthly breakdown, top expenses, alerts
- **Errors**: None
- **Side effects**: None

### `update_dashboard_analytics(vault_path, markdown) -> None`
- **Input**: Vault root path, analytics Markdown string
- **Output**: None
- **Errors**: Logs error if Dashboard.md missing or markers not found
- **Side effects**: Updates Dashboard.md between START_ANALYTICS/END_ANALYTICS markers

### `run_analysis(vault_path) -> AnalyticsSummary`
- **Input**: Vault root path
- **Output**: AnalyticsSummary dict
- **Errors**: Returns empty summary if no CSV files found
- **Side effects**: Updates Dashboard.md, writes audit log

## Expected CSV Format

```csv
date,description,amount,category
2026-01-15,Client Payment,5000.00,Revenue
2026-01-16,Office Supplies,-150.00,Operations
2026-01-20,Software License,-299.99,Technology
```

## Column Mapping

| Standard | Accepted Synonyms |
|----------|-------------------|
| amount | amount, value, total, sum |
| date | date, transaction_date, trans_date, posted_date |
| category | category, type, class, department |
| description | description, memo, note, details, payee |

Special case: If `debit` and `credit` columns both exist, amount = credit - debit.

## Output Markdown Format

```markdown
## Business Analytics

**Last Updated**: 2026-02-21 14:30 UTC | **Files Analyzed**: 2

### Financial Summary

| Metric | Amount |
|--------|--------|
| Total Revenue | $15,000.00 |
| Total Expenses | $8,450.00 |
| Net Income | $6,550.00 |

### Monthly Breakdown

| Month | Revenue | Expenses | Net |
|-------|---------|----------|-----|
| 2026-01 | $10,000 | $5,200 | $4,800 |
| 2026-02 | $5,000 | $3,250 | $1,750 |

### Top 5 Expenses

| Date | Description | Amount | Category |
|------|-------------|--------|----------|
| 2026-01-20 | Software License | $2,999.99 | Technology |

### Anomaly Alerts

| Date | Description | Amount | Category | Avg | Ratio |
|------|-------------|--------|----------|-----|-------|
| 2026-01-20 | Large Purchase | $5,000 | Office | $250 | 20.0x |
```

## Audit Events

| Action | Outcome | Details |
|--------|---------|---------|
| analytics_started | success | files_found count |
| csv_loaded | success | filename, rows_count |
| csv_loaded | error | filename, error message |
| anomaly_detected | success | description, amount, ratio |
| analytics_completed | success | revenue, expenses, anomalies_count |
| dashboard_analytics_updated | success | - |

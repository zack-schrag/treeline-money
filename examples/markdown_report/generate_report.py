#!/usr/bin/env python3
"""
Treeline Markdown Spending Report Generator

Generates a markdown report with spending analysis and text-based charts.
Run with: uv run python generate_report.py [output_file]
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import plotext as plt


def connect_to_db() -> duckdb.DuckDBPyConnection:
    """Connect to the Treeline database."""
    db_path = Path.home() / ".treeline" / "treeline.duckdb"

    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        print("Please run 'tl sync' or 'tl import' to populate your database.")
        sys.exit(1)

    return duckdb.connect(str(db_path), read_only=True)


def get_summary_stats(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Get overall summary statistics."""
    query = """
    SELECT
        COUNT(*) as total_transactions,
        SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_spending,
        SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_income,
        AVG(CASE WHEN amount < 0 THEN ABS(amount) ELSE NULL END) as avg_spending,
        MIN(transaction_date) as earliest_date,
        MAX(transaction_date) as latest_date
    FROM transactions
    """
    result = conn.execute(query).fetchone()
    return {
        "total_transactions": result[0],
        "total_spending": result[1] or 0,
        "total_income": result[2] or 0,
        "avg_spending": result[3] or 0,
        "earliest_date": result[4],
        "latest_date": result[5],
    }


def get_monthly_spending(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Get monthly spending breakdown."""
    query = """
    SELECT
        strftime('%Y-%m', transaction_date) as month,
        SUM(ABS(amount)) as spending
    FROM transactions
    WHERE amount < 0
    GROUP BY month
    ORDER BY month DESC
    LIMIT 12
    """
    return conn.execute(query).df()


def get_spending_by_tag(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Get spending breakdown by tag/category."""
    query = """
    WITH tagged_transactions AS (
        SELECT
            transaction_id,
            amount,
            UNNEST(tags) as tag
        FROM transactions
        WHERE amount < 0 AND len(tags) > 0
    )
    SELECT
        tag,
        SUM(ABS(amount)) as total_spending,
        COUNT(*) as num_transactions
    FROM tagged_transactions
    GROUP BY tag
    ORDER BY total_spending DESC
    LIMIT 10
    """
    return conn.execute(query).df()


def get_top_merchants(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Get top merchants by spending."""
    query = """
    SELECT
        description,
        COUNT(*) as num_transactions,
        SUM(ABS(amount)) as total_spent
    FROM transactions
    WHERE amount < 0
    GROUP BY description
    ORDER BY total_spent DESC
    LIMIT 10
    """
    return conn.execute(query).df()


def create_text_bar_chart(
    values: list[float], labels: list[str], max_width: int = 50
) -> str:
    """Create a simple text-based horizontal bar chart."""
    if not values:
        return "No data available"

    max_val = max(values)
    lines = []

    for label, value in zip(labels, values):
        bar_length = int((value / max_val) * max_width) if max_val > 0 else 0
        bar = "█" * bar_length
        lines.append(f"{label:<20} {bar} ${value:,.2f}")

    return "\n".join(lines)


def generate_report(output_path: Path | None = None) -> str:
    """Generate the markdown report."""
    conn = connect_to_db()

    # Get data
    stats = get_summary_stats(conn)
    monthly = get_monthly_spending(conn)
    by_tag = get_spending_by_tag(conn)
    top_merchants = get_top_merchants(conn)

    # Calculate net savings
    net = stats["total_income"] - stats["total_spending"]

    # Build markdown report
    report = f"""# 💰 Treeline Spending Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Data Range:** {stats["earliest_date"]} to {stats["latest_date"]}

---

## Summary

- **Total Transactions:** {stats["total_transactions"]:,}
- **Total Spending:** ${stats["total_spending"]:,.2f}
- **Total Income:** ${stats["total_income"]:,.2f}
- **Net:** ${net:,.2f}
- **Average Transaction:** ${stats["avg_spending"]:,.2f}

---

## Monthly Spending Trend

Last 12 months (most recent first):

```
{create_text_bar_chart(monthly["spending"].tolist(), monthly["month"].tolist())}
```

---

## Spending by Category

Top 10 categories:

"""

    if len(by_tag) > 0:
        report += f"""
```
{create_text_bar_chart(by_tag["total_spending"].tolist(), by_tag["tag"].tolist())}
```

| Category | Transactions | Total Spent |
|----------|-------------|-------------|
"""
        for _, row in by_tag.iterrows():
            report += f"| {row['tag']} | {row['num_transactions']} | ${row['total_spending']:,.2f} |\n"
    else:
        report += "\n⚠️ No tagged transactions found. Use `tl tag` to categorize your spending!\n"

    report += """
---

## Top Merchants

Top 10 merchants by total spending:

| Merchant | Transactions | Total Spent |
|----------|-------------|-------------|
"""

    for _, row in top_merchants.iterrows():
        desc = (
            row["description"][:40] + "..."
            if len(row["description"]) > 40
            else row["description"]
        )
        report += (
            f"| {desc} | {row['num_transactions']} | ${row['total_spent']:,.2f} |\n"
        )

    report += """
---

## Month-over-Month Comparison

"""

    if len(monthly) >= 2:
        current_month = monthly.iloc[0]
        prev_month = monthly.iloc[1]
        change = current_month["spending"] - prev_month["spending"]
        change_pct = (
            (change / prev_month["spending"] * 100) if prev_month["spending"] > 0 else 0
        )

        direction = "📈" if change > 0 else "📉"
        report += f"""
- **{current_month["month"]}:** ${current_month["spending"]:,.2f}
- **{prev_month["month"]}:** ${prev_month["spending"]:,.2f}
- **Change:** {direction} ${abs(change):,.2f} ({change_pct:+.1f}%)
"""
    else:
        report += "\nNot enough data for comparison.\n"

    report += """
---

*To update this report, run `uv run python generate_report.py`*
"""

    conn.close()

    # Write to file if specified
    if output_path:
        output_path.write_text(report)
        print(f"✅ Report saved to {output_path}")
    else:
        print(report)

    return report


if __name__ == "__main__":
    output_file = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    generate_report(output_file)

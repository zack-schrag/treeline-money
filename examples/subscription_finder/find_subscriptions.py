#!/usr/bin/env python3
"""
Treeline Subscription Finder

Analyzes your transactions to detect recurring charges and potential subscriptions.
Run with: uv run python find_subscriptions.py
"""

import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box


def connect_to_db() -> duckdb.DuckDBPyConnection:
    """Connect to the Treeline database."""
    db_path = Path.home() / ".treeline" / "treeline.duckdb"

    if not db_path.exists():
        console = Console()
        console.print(f"[red]❌ Database not found at {db_path}[/red]")
        console.print("Please run 'tl sync' or 'tl import' to populate your database.")
        sys.exit(1)

    return duckdb.connect(str(db_path), read_only=True)


def find_recurring_transactions(
    conn: duckdb.DuckDBPyConnection,
    min_occurrences: int = 3,
    amount_tolerance: float = 0.05,
) -> pd.DataFrame:
    """
    Find recurring transactions based on merchant and amount patterns.

    Args:
        conn: Database connection
        min_occurrences: Minimum number of times a transaction must occur
        amount_tolerance: Tolerance for amount variation (5% by default)
    """
    # Get all spending transactions grouped by merchant
    query = """
    SELECT
        description,
        ABS(amount) as amount,
        transaction_date,
        account_name
    FROM transactions
    WHERE amount < 0  -- Only spending
    ORDER BY description, transaction_date
    """

    df = conn.execute(query).df()

    # Group by merchant and find recurring patterns
    recurring = []

    for merchant, group in df.groupby("description"):
        if len(group) < min_occurrences:
            continue

        # Check for similar amounts (within tolerance)
        amounts = group["amount"].values
        median_amount = pd.Series(amounts).median()

        # Filter to transactions within tolerance of median
        similar = group[
            (group["amount"] >= median_amount * (1 - amount_tolerance))
            & (group["amount"] <= median_amount * (1 + amount_tolerance))
        ].copy()

        if len(similar) < min_occurrences:
            continue

        # Calculate intervals between transactions
        dates = pd.to_datetime(similar["transaction_date"]).sort_values()
        if len(dates) < 2:
            continue

        intervals = []
        for i in range(1, len(dates)):
            interval = (dates.iloc[i] - dates.iloc[i - 1]).days
            intervals.append(interval)

        avg_interval = sum(intervals) / len(intervals)

        # Determine frequency type
        if 25 <= avg_interval <= 35:
            frequency = "Monthly"
            monthly_cost = median_amount
        elif 85 <= avg_interval <= 95:
            frequency = "Quarterly"
            monthly_cost = median_amount / 3
        elif 350 <= avg_interval <= 370:
            frequency = "Yearly"
            monthly_cost = median_amount / 12
        elif 6 <= avg_interval <= 8:
            frequency = "Weekly"
            monthly_cost = median_amount * 4.33  # Average weeks per month
        else:
            frequency = f"Every {int(avg_interval)} days"
            monthly_cost = (
                median_amount * (30 / avg_interval) if avg_interval > 0 else 0
            )

        recurring.append(
            {
                "merchant": merchant,
                "amount": median_amount,
                "frequency": frequency,
                "avg_interval_days": avg_interval,
                "occurrences": len(similar),
                "first_seen": dates.iloc[0].strftime("%Y-%m-%d"),
                "last_seen": dates.iloc[-1].strftime("%Y-%m-%d"),
                "monthly_cost": monthly_cost,
                "account": similar["account_name"].iloc[0],
            }
        )

    return pd.DataFrame(recurring).sort_values("monthly_cost", ascending=False)


def display_results(subscriptions: pd.DataFrame) -> None:
    """Display subscription findings in a nice table."""
    console = Console()

    if len(subscriptions) == 0:
        console.print("[yellow]No recurring subscriptions detected.[/yellow]")
        console.print(
            "\nTip: Try adjusting the detection parameters or ensure you have enough transaction history."
        )
        return

    # Summary panel
    total_monthly = subscriptions["monthly_cost"].sum()
    total_yearly = total_monthly * 12
    num_subscriptions = len(subscriptions)

    summary = f"""
[bold]Detected Subscriptions:[/bold] {num_subscriptions}
[bold]Total Monthly Cost:[/bold] ${total_monthly:,.2f}
[bold]Total Yearly Cost:[/bold] ${total_yearly:,.2f}
    """

    console.print(Panel(summary, title="💳 Subscription Summary", border_style="blue"))
    console.print()

    # Detailed table
    table = Table(title="Recurring Charges", box=box.ROUNDED, show_lines=True)

    table.add_column("Merchant", style="cyan", no_wrap=False, max_width=30)
    table.add_column("Amount", justify="right", style="green")
    table.add_column("Frequency", justify="center")
    table.add_column("Monthly Cost", justify="right", style="yellow")
    table.add_column("Occurrences", justify="center")
    table.add_column("Last Seen", justify="center", style="dim")

    for _, row in subscriptions.iterrows():
        table.add_row(
            row["merchant"],
            f"${row['amount']:.2f}",
            row["frequency"],
            f"${row['monthly_cost']:.2f}",
            str(row["occurrences"]),
            row["last_seen"],
        )

    console.print(table)
    console.print()

    # Warnings for potentially forgotten subscriptions
    console.print("[bold]💡 Tips:[/bold]")
    console.print(
        "• Review these charges to identify subscriptions you may have forgotten"
    )
    console.print("• Check for services you're no longer using")
    console.print("• Consider canceling or downgrading unused subscriptions")

    # Show old subscriptions (not seen in last 60 days)
    old_threshold = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    old_subs = subscriptions[subscriptions["last_seen"] < old_threshold]

    if len(old_subs) > 0:
        console.print()
        console.print(
            "[bold yellow]⚠️  Potentially Cancelled Subscriptions:[/bold yellow]"
        )
        console.print("The following haven't appeared in the last 60 days:")
        for _, row in old_subs.iterrows():
            console.print(f"  • {row['merchant']} (last seen: {row['last_seen']})")


def main() -> None:
    """Main entry point."""
    console = Console()

    console.print(
        "[bold blue]🔍 Analyzing transactions for recurring charges...[/bold blue]\n"
    )

    conn = connect_to_db()
    subscriptions = find_recurring_transactions(
        conn, min_occurrences=3, amount_tolerance=0.05
    )
    conn.close()

    display_results(subscriptions)


if __name__ == "__main__":
    main()

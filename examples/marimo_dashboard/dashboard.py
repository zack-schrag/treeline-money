"""
Treeline Spending Dashboard - Marimo Notebook

A simple interactive dashboard to visualize your spending patterns.
Run with: uv run marimo edit dashboard.py
"""

import marimo

__generated_with = "0.17.8"
app = marimo.App(width="medium")


@app.cell
def __():
    import marimo as mo
    import duckdb
    import pandas as pd
    import plotly.express as px
    from pathlib import Path

    mo.md("# 💰 Treeline Spending Dashboard")
    return Path, duckdb, mo, pd, px


@app.cell
def __(Path, duckdb, mo):
    # Connect to Treeline database
    db_path = Path.home() / ".treeline" / "treeline.duckdb"

    if not db_path.exists():
        mo.md(f"""
        ⚠️ **Database not found**

        Please ensure Treeline is set up and has data.
        Expected location: `{db_path}`

        Run `tl sync` or `tl import` to populate your database.
        """)
        mo.stop()

    conn = duckdb.connect(str(db_path), read_only=True)
    mo.md(f"✅ Connected to database: `{db_path}`")
    return conn, db_path


@app.cell
def __(conn, pd):
    # Load transaction data
    query = """
    SELECT
        transaction_date,
        amount,
        description,
        tags,
        account_name,
        institution_name
    FROM transactions
    WHERE amount < 0  -- Only spending (negative amounts)
    ORDER BY transaction_date DESC
    """

    df = conn.execute(query).df()
    df["amount_abs"] = df["amount"].abs()  # Positive values for display
    df
    return df, query


@app.cell
def __(df, mo):
    # Summary statistics
    total_spending = df["amount_abs"].sum()
    num_transactions = len(df)
    avg_transaction = df["amount_abs"].mean()

    mo.md(f"""
    ## Summary Statistics

    - **Total Spending**: ${total_spending:,.2f}
    - **Number of Transactions**: {num_transactions:,}
    - **Average Transaction**: ${avg_transaction:,.2f}
    """)
    return avg_transaction, num_transactions, total_spending


@app.cell
def __(df, pd, px):
    # Monthly spending trend
    df_monthly = df.copy()
    df_monthly["month"] = (
        pd.to_datetime(df_monthly["transaction_date"]).dt.to_period("M").astype(str)
    )
    monthly_spending = df_monthly.groupby("month")["amount_abs"].sum().reset_index()
    monthly_spending.columns = ["Month", "Total Spending"]

    fig_monthly = px.line(
        monthly_spending,
        x="Month",
        y="Total Spending",
        title="Monthly Spending Trend",
        markers=True,
    )
    fig_monthly.update_layout(
        xaxis_title="Month", yaxis_title="Spending ($)", yaxis_tickformat="$,.0f"
    )
    fig_monthly
    return df_monthly, fig_monthly, monthly_spending


@app.cell
def __(df, mo, pd, px):
    # Spending by tag/category
    # Explode tags array so each tag gets its own row
    df_tags = df[df["tags"].apply(lambda x: len(x) > 0)].copy()

    if len(df_tags) > 0:
        df_tags_exploded = df_tags.explode("tags")
        tag_spending = (
            df_tags_exploded.groupby("tags")["amount_abs"].sum().reset_index()
        )
        tag_spending = tag_spending.sort_values("amount_abs", ascending=False).head(10)
        tag_spending.columns = ["Tag", "Total Spending"]

        fig_tags = px.bar(
            tag_spending,
            x="Tag",
            y="Total Spending",
            title="Top 10 Spending Categories",
            color="Total Spending",
            color_continuous_scale="Reds",
        )
        fig_tags.update_layout(
            xaxis_title="Category",
            yaxis_title="Spending ($)",
            yaxis_tickformat="$,.0f",
            showlegend=False,
        )
        fig_tags
    else:
        mo.md(
            "⚠️ No tagged transactions found. Use `tl tag` to categorize your transactions!"
        )
    return df_tags, df_tags_exploded, fig_tags, tag_spending


@app.cell
def __(df, mo):
    # Recent transactions table
    recent_transactions = df.head(20)[
        ["transaction_date", "description", "amount_abs", "tags", "account_name"]
    ]
    recent_transactions.columns = ["Date", "Description", "Amount", "Tags", "Account"]

    mo.md("## Recent Transactions")
    return (recent_transactions,)


@app.cell
def __(mo, recent_transactions):
    mo.ui.table(recent_transactions, selection=None, page_size=10)
    return


@app.cell
def __(mo):
    mo.md("""
    ---

    💡 **Tips**:
    - Use `tl tag` to categorize transactions and see better insights
    - Export data with `tl query "SELECT * FROM transactions" --format csv`
    - Customize this dashboard by editing the SQL queries above
    """)
    return


if __name__ == "__main__":
    app.run()

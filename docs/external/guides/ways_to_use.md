# Ways to Use Treeline

One of Treeline's core principles is that **your data is actually _your_ data**. We believe you should have full, direct access to your financial data and the freedom to interact with it however you want. Treeline provides the data and keeps it synced - you choose how to use it.

This guide outlines the different ways you can work with your Treeline data.

## 1. The CLI (Standard Way)

The Treeline CLI is the primary interface, designed for interactive data exploration and management.

### What you can do:
- Ask natural language questions about your finances (AI chat)
- Tag transactions with keyboard-driven power mode (TUI)
- Run SQL queries directly
- Sync data from SimpleFIN or other providers
- Visualize data with interactive charts (TUI)

### When to use it:
- Quick, interactive exploration of your financial data
- Tagging and organizing transactions
- Running ad-hoc queries
- Daily financial data management

### Example:
```bash
# Chat with AI about your finances
treeline chat

# Tag transactions interactively
treeline tag --untagged

# Sync latest data
treeline sync

# Run one-off SQL query
treeline query "SELECT * FROM transactions LIMIT 10"

# Launch analysis workspace for deeper exploration
treeline analysis
```

See the [Quickstart Guide](../getting_started/quickstart.md) for more details.

---

## 2. MCP Server (Claude Integration)

**Status: Planned for future release**

Treeline can run as an MCP (Model Context Protocol) server, allowing you to interact with your financial data directly through Claude or other MCP-compatible AI assistants.

### What you can do:
- Ask Claude questions about your finances using natural language
- Have Claude generate and run SQL queries against your data
- Get financial insights and analysis through conversational AI
- Automate complex financial reporting tasks

### When to use it:
- You already use Claude for other tasks and want seamless integration
- You prefer a conversational interface over CLI commands
- You want to combine financial analysis with other AI workflows

### Example conversation with Claude:
```
You: What's my average monthly spending on groceries over the last 6 months?
Claude: [Queries your Treeline database via MCP]
        Based on your transaction data, your average monthly grocery
        spending is $487.23 over the last 6 months.

You: Show me a breakdown by store
Claude: [Runs another query]
        Here's the breakdown...
```

### Setup (when available):
```bash
# Add Treeline MCP server to your Claude configuration
treeline mcp setup
```

---

## 3. Direct Database Access (SQL Tools)

Your Treeline data lives in a local DuckDB file. You can connect to it directly using any DuckDB-compatible SQL tool.

### What you can do:
- Run complex SQL queries using your favorite SQL IDE
- Create custom views and materialized queries
- Export data in any format (CSV, Parquet, JSON)
- Build custom dashboards and reports
- Perform advanced analytics and data science workflows

### When to use it:
- You're comfortable with SQL and prefer a dedicated SQL IDE
- You need to perform complex joins or aggregations
- You want to export data for use in other tools
- You're building custom dashboards or reports

### Recommended Tools:
- **DBeaver** - Full-featured, open-source database tool
- **DataGrip** - JetBrains IDE for databases
- **DuckDB CLI** - Lightweight command-line interface
- **Tableau** - For advanced visualizations (via JDBC/ODBC)

### Example with DBeaver:
1. Install DBeaver: https://dbeaver.io/
2. Create a new DuckDB connection
3. Point to your database file: `~/.treeline/[user-id].duckdb`
4. Run queries directly:

```sql
-- Find all transactions over $500 in the last 30 days
SELECT
    t.transaction_date,
    a.name as account_name,
    t.description,
    t.amount,
    t.tags
FROM sys_transactions t
JOIN sys_accounts a ON t.account_id = a.account_id
WHERE t.transaction_date >= CURRENT_DATE - INTERVAL 30 DAY
  AND ABS(t.amount) > 500
ORDER BY t.transaction_date DESC;
```

### ⚠️ Important Warnings:
- **READ-ONLY is recommended**: Only SELECT queries are safe for external tools
- **DO NOT modify the schema**: Adding/removing columns or tables will break Treeline
- **Avoid concurrent writes**: If Treeline is running, use read-only connections
- **Backup first**: Always backup your database before experimenting with writes
- **Tag updates are safe**: Updating the `tags` column is generally safe if done carefully

---

## 4. Jupyter Notebooks / Marimo

Connect Python notebooks directly to your DuckDB database for data analysis and visualization.

### What you can do:
- Perform exploratory data analysis with pandas
- Create custom visualizations with matplotlib, seaborn, or plotly
- Build financial models and forecasts
- Run statistical analysis on your spending patterns
- Create shareable reports and dashboards

### When to use it:
- You're doing data science or analytical work
- You want to combine financial data with other datasets
- You need reproducible analysis workflows
- You want to create custom visualizations

### Example with Jupyter:
```python
import duckdb
import pandas as pd
import matplotlib.pyplot as plt

# Connect to your Treeline database
conn = duckdb.connect('~/.treeline/[user-id].duckdb', read_only=True)

# Query data
df = conn.execute("""
    SELECT
        DATE_TRUNC('month', transaction_date) as month,
        SUM(amount) as total_spending
    FROM sys_transactions
    WHERE amount < 0
    GROUP BY month
    ORDER BY month
""").df()

# Visualize
df.plot(x='month', y='total_spending', kind='bar')
plt.title('Monthly Spending Trend')
plt.show()

conn.close()
```

### Example with Marimo:
```python
import marimo as mo
import duckdb

# Create a reactive notebook
mo.md("# My Financial Dashboard")

conn = duckdb.connect('~/.treeline/[user-id].duckdb', read_only=True)

# Create interactive widgets
date_range = mo.ui.date_range()
mo.md(f"Select date range: {date_range}")

# Query based on user input
query = f"""
    SELECT * FROM sys_transactions
    WHERE transaction_date BETWEEN '{date_range.value[0]}'
    AND '{date_range.value[1]}'
"""
results = conn.execute(query).df()
mo.ui.table(results)
```

### ⚠️ Important Warnings:
- **Always use `read_only=True`** when connecting from notebooks
- **Don't modify the schema** - stick to SELECT queries
- **Close connections properly** to avoid locking issues
- **Be careful with writes** - updating tags is OK, but schema changes will break Treeline

---

## 5. Custom Scripts & Automation

Build your own Python scripts to automate financial tasks and workflows.

### What you can do:
- Schedule automated reports (daily, weekly, monthly)
- Build custom alerting systems (e.g., "notify me when balance drops below X")
- Create automated exports to other systems
- Build custom integrations with other tools
- Implement your own financial rules and automations

### When to use it:
- You want to automate repetitive tasks
- You need to integrate Treeline data with other systems
- You want custom alerting or notification logic
- You're building your own financial tools on top of Treeline

### Example - Automated Weekly Report:
```python
#!/usr/bin/env python3
"""Send weekly spending summary via email."""

import duckdb
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

# Connect to database
conn = duckdb.connect('~/.treeline/[user-id].duckdb', read_only=True)

# Get last week's data
last_week = datetime.now() - timedelta(days=7)
result = conn.execute("""
    SELECT
        tags[1] as category,
        SUM(ABS(amount)) as total
    FROM sys_transactions
    WHERE transaction_date >= ?
      AND amount < 0
      AND tags IS NOT NULL
    GROUP BY category
    ORDER BY total DESC
    LIMIT 5
""", [last_week.date()]).fetchall()

# Format report
report = "Top 5 Spending Categories This Week:\n\n"
for category, total in result:
    report += f"{category}: ${total:.2f}\n"

# Send email (configure SMTP settings)
msg = MIMEText(report)
msg['Subject'] = 'Weekly Spending Report'
msg['From'] = 'treeline@example.com'
msg['To'] = 'you@example.com'

# Send via SMTP...
print(report)

conn.close()
```

### Schedule with cron:
```bash
# Run every Monday at 9 AM
0 9 * * 1 /path/to/weekly_report.py
```

---

## Choosing the Right Approach

| Use Case | Recommended Approach |
|----------|---------------------|
| Quick exploration & daily tasks | CLI |
| Conversational AI analysis | MCP Server (when available) |
| Complex SQL queries | SQL Tool (DBeaver, etc.) |
| Data science & visualization | Jupyter/Marimo |
| Custom automation | Python Scripts |
| Sharing with non-technical users | Jupyter notebooks or MCP |

---

## Data Location

Your Treeline data is stored locally in:
```
~/.treeline/
├── [user-id].duckdb     # Your financial database
├── queries/             # Saved SQL queries
├── charts/              # Saved chart configurations
├── config.json          # Configuration
└── backups/             # Automatic backups (if enabled)
```

The database file path is: `~/.treeline/[user-id].duckdb`

You can find your user ID by running:
```bash
treeline status
```

---

## Schema Reference

Your DuckDB database contains these core tables:

### `sys_accounts`
- `account_id` (UUID, PRIMARY KEY)
- `name` (VARCHAR)
- `nickname` (VARCHAR)
- `account_type` (VARCHAR)
- `currency` (VARCHAR)
- `institution_name` (VARCHAR)
- And more...

### `sys_transactions`
- `transaction_id` (UUID, PRIMARY KEY)
- `account_id` (UUID, FOREIGN KEY → accounts)
- `amount` (DECIMAL)
- `description` (VARCHAR)
- `transaction_date` (DATE)
- `tags` (VARCHAR[])
- And more...

### `sys_balance_snapshots`
- `snapshot_id` (UUID, PRIMARY KEY)
- `account_id` (UUID, FOREIGN KEY → accounts)
- `balance` (DECIMAL)
- `snapshot_time` (TIMESTAMP)
- And more...

For the complete schema, see [Architecture Documentation](../../internal/architecture.md).

---

## Best Practices

### ✅ Do:
- Use read-only connections when possible
- Back up your database before experimenting
- Close database connections properly
- Update tags carefully if needed
- Use transactions for multi-step writes

### ❌ Don't:
- Modify the database schema (adding/removing tables or columns)
- Run concurrent writes from multiple tools
- Hard-delete records (Treeline expects data to persist)
- Modify `account_id`, `transaction_id`, or other IDs
- Change the `external_ids` field (used for deduplication)

---

## Need Help?

- **Documentation**: https://docs.treeline.money
- **Issues**: https://github.com/treeline-money/treeline/issues
- **Community**: https://discord.gg/treeline

The flexibility is yours - use Treeline however works best for your workflow!

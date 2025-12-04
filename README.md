# Treeline

**Personal finance analysis — your way**

Treeline gives you complete control over your financial data. Built for power users and tinkerers who want direct access to their data.

<!-- TODO: Add screenshot of desktop app dashboard -->
![Treeline Screenshot](./demo.gif)

> **⚠️ Early Stage Software**: Treeline is in active development. Expect potential breaking changes in future releases. Always back up your data.

> **⚠️ Limited Testing**: Treeline has been tested primarily on macOS with USD currency and a small number of US banks (for CSV imports). If you encounter issues, please [file an issue](https://github.com/zack-schrag/treeline-money/issues) or submit a PR!

## Why Treeline?

If you've ever:
- Spent hours building a custom spreadsheet that could rival Mint
- Been frustrated with the lack of customization from existing finance tools
- Wished you could build your own automations tailored to *your* financial life
- Wanted full control over your data

You're in the right place 😃

## Features

Treeline includes a **desktop app** and a **CLI** that work together. Use the app for everyday tasks and the CLI for automation and scripting.

### Desktop App
- **Account Dashboard** — View all accounts, balances, and recent transactions
- **Transaction Tagging** — Categorize transactions with keyboard shortcuts and bulk selection
- **Budget Tracking** — Set monthly budgets by category and track spending
- **CSV Import** — Import bank exports with column auto-detection and live preview
- **SimpleFIN Sync** — Connect bank accounts and sync with one click
- **Plugin System** — Extensible architecture for building custom plugins

### CLI
- **SQL Queries** — Direct DuckDB access to your financial data
- **Scriptable** — JSON output, CSV export, and piping support
- **Full Access** — Everything in the app can also be done via CLI

## Quick Start

### Try Demo Mode

The fastest way to explore Treeline — no bank connection required:

```bash
pip install treeline-money

# Enable demo mode (loads sample data)
tl demo on

# Explore
tl status
tl query "SELECT * FROM transactions LIMIT 10"

# Disable when done
tl demo off
```

> **💡 Tip**: `tl` is an alias for `treeline`

### Install

Download from [GitHub Releases](https://github.com/zack-schrag/treeline-money/releases):
- **Desktop App** — Includes both UI and CLI
- **CLI only** — Standalone binary, no dependencies

Or install via pip: `pip install treeline-money`

### Connect Your Data

#### Option 1: SimpleFIN (Recommended)

[SimpleFIN](https://beta-bridge.simplefin.org/simplefin) is a bank aggregation service ($1.50/month) that connects to your bank accounts. Once set up, sync all your transactions with one command.

```bash
tl setup simplefin   # Paste your setup token
tl sync              # Fetch transactions from all accounts
```

#### Option 2: CSV Import

Import transactions from your bank's CSV exports — completely free.

```bash
tl import            # Interactive mode with auto-detection
tl import bank.csv   # Or specify a file directly
```

<!-- TODO: Add screenshot of CSV import modal -->

## Using Treeline

### Desktop App

<!-- TODO: Add screenshots for each section -->

**Accounts** — View all your accounts and balances. Click an account to see recent transactions.

**Tagging** — Categorize transactions. Use keyboard shortcuts for speed: number keys for quick tags, `e` to edit, `/` to search.

**Budget** — Set monthly spending targets by category. Categories are defined by tags.

### CLI

Run SQL queries directly against your data:

```bash
# Monthly spending
tl query "SELECT strftime('%Y-%m', transaction_date) as month, SUM(amount) as total
          FROM transactions WHERE amount < 0 GROUP BY month ORDER BY month DESC"

# Transactions by tag
tl query "SELECT tags, SUM(amount) as total FROM transactions
          WHERE amount < 0 GROUP BY tags ORDER BY total"

# Export to CSV
tl query "SELECT * FROM transactions" --format csv > export.csv
```

Apply tags via CLI for scripting:

```bash
# Tag specific transactions
tl tag groceries --ids abc123,def456

# Pipe from a query
tl query "SELECT transaction_id FROM transactions WHERE description ILIKE '%COSTCO%'" --json \
  | jq -r '.rows[][] | @text' | tl tag groceries
```

## Database Schema

All data is stored locally in DuckDB. Query these tables:

| Table | Description |
|-------|-------------|
| `transactions` | All transactions with account info joined |
| `accounts` | Account details (name, type, balance, institution) |
| `balance_snapshots` | Historical balance records |

Key fields in `transactions`:
- `transaction_id`, `account_id` — UUIDs
- `amount` — Negative = spending, positive = income
- `description`, `transaction_date`, `posted_date`
- `tags` — Array of tags, e.g. `['groceries', 'food']`
- `account_name`, `institution_name` — Joined from accounts

## Examples

See [examples/](./examples/) for starter projects:
- **marimo_dashboard** — Interactive data exploration
- **markdown_report** — Generate spending reports
- **subscription_finder** — Find recurring charges

Ideas for automation:
- Let Claude Code analyze your finances using CLI commands
- Set up a cron job to run `tl sync` daily
- Build custom reports with the SQL interface

## Getting Help

- **Bug reports & feature requests**: [GitHub Issues](https://github.com/zack-schrag/treeline-money/issues)
- **Questions & discussions**: [GitHub Discussions](https://github.com/zack-schrag/treeline-money/discussions)

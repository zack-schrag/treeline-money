# Treeline

**Personal finance analysis in your terminal**

Treeline gives you complete control over your financial data. Built for power users who want direct access to their data.

> **⚠️ Early Stage Software**: Treeline is in active development. While it's stable for personal use, expect potential breaking changes in future releases. Always back up your data.

If you've ever:
- Spent hours building a custom spreadsheet that could rival Mint
- Been frustrated with the lack of customization from existing finance tools
- Wished you build your own automations tailored to *your* financial life
- Wanted *full* control over your data

You're in the right place 😃

## Features
- **SQL Queries** - Direct DuckDB access to your financial data
- **SimpleFIN Sync** - Automatic bank synchronization via SimpleFIN
- **CSV Import** - Import transactions from any bank CSV export, with automatic deduplication
- **Local Database** - All data stored locally in DuckDB
- **Scriptable** - JSON output, CSV export, and support for input / output piping
- **Auto-Tagging** - Python-based rules to build custom logic for automatically categorizing transactions

## Quick Start

### Try Demo Mode (No Setup)

The fastest way to explore Treeline:

```bash
pip install treeline-money

# Load demo data
export TREELINE_DEMO_MODE=true
tl sync

# Explore with demo data
tl status
tl query "SELECT * FROM transactions LIMIT 10"

# When you're done with demoing:
unset TREELINE_DEMO_MODE
```

> **💡 Note**: Examples use `tl` (the short alias), but `treeline` works too

See [docs/demo_mode.md](./docs/demo_mode.md) for details.

### Real Setup

```bash
# 1. Install
pip install treeline-money

# 2. Connect to SimpleFIN
tl setup simplefin

# 3. Sync your data
tl sync

# 4. Start exploring
tl status
tl query "SELECT * FROM transactions ORDER BY transaction_date DESC LIMIT 10"
```

### Tagging transactions
```bash
# Start interactive tagging mode
tl tag

# Or tag directly from CLI
tl tag apply --ids abc123,def456 groceries,food

# Or pipe IDs from query to apply tags in bulk
# Note: Use intermediate variable to avoid database lock conflicts
TX_IDS=$(tl query "SELECT transaction_id FROM transactions WHERE description ILIKE '%QFC%'" --json | jq -r '.rows[][]')
echo "$TX_IDS" | tl tag apply groceries
```

### Auto-tagging rules on sync or import
```bash
tl new tagger large_purchases
```
This will create a new file in `~/.treeline/taggers/large_purchases.py`. Fill out the Python logic, then test by doing a backfill with optional `--dry-run` flag:
```bash
tl backfill tags --dry-run --verbose
```
This will show the tags that would be applied, but makes no edits to the database. Remove the the `--dry-run` once you're confident in the logic.

## Database Schema

Query these tables with standard SQL:

### `transactions`
Main view for querying transaction data (joins transaction + account details):
- `transaction_id` - UUID of transaction
- `account_id` - UUID of account
- `amount` - Transaction amount (negative = spending, positive = income)
- `description` - Transaction description
- `transaction_date` - Date of transaction
- `posted_date` - Date transaction posted
- `tags` - Array of tags (e.g., `['groceries', 'food']`)
- `account_name` - Name of account (joined)
- `account_type` - Type of account (joined)
- `currency` - Currency code (joined)
- `institution_name` - Bank/institution name (joined)

### `accounts`
Account information:
- `account_id` - UUID of account
- `name` - Account name
- `nickname` - Optional nickname
- `account_type` - Account type (checking, savings, credit, etc.)
- `currency` - Currency code (default: USD)
- `balance` - Current balance
- `external_ids` - JSON of external IDs from integrations
- `institution_name` - Bank/institution name
- `institution_url` - Institution URL
- `institution_domain` - Institution domain
- `created_at` - Created timestamp
- `updated_at` - Last updated timestamp

### `balance_snapshots`
Historical balance data (joins balance + account details):
- `snapshot_id` - UUID of snapshot
- `account_id` - UUID of account
- `balance` - Balance at snapshot time
- `snapshot_time` - When snapshot was taken
- `account_name` - Name of account (joined)
- `institution_name` - Bank/institution name (joined)
- `created_at` - Created timestamp
- `updated_at` - Last updated timestamp

**Example queries:**

```bash
# Spending by tag
tl query "SELECT tags, SUM(amount) as total FROM transactions WHERE amount < 0 GROUP BY tags ORDER BY total"

# Monthly spending trends
tl query "SELECT strftime('%Y-%m', transaction_date) as month, SUM(amount) as total FROM transactions WHERE amount < 0 GROUP BY month ORDER BY month DESC"

# Account balances over time
tl query "SELECT account_name, snapshot_time, balance FROM balance_snapshots ORDER BY snapshot_time DESC"

# Top 10 biggest purchases
tl query "SELECT transaction_date, description, amount, account_name FROM transactions WHERE amount < 0 ORDER BY amount LIMIT 10"

# Transactions without tags
tl query "SELECT transaction_date, description, amount FROM transactions WHERE tags = [] ORDER BY transaction_date DESC LIMIT 20"

# Export all transactions to CSV
tl query "SELECT * FROM transactions" --format csv > all_transactions.csv
```

## What can you do with Treeline?
Some ideas to get you started:
- Build an interactive dashboard with Marimo or Streamlit (or whatever your favorite tool is)
- Have Claude Code analyze your data with natural language by letting it run Treeline CLI commands. Note: by default Claude won't know the DB schema. Point it to this README and it should be able to explore your data and analyze it.
- Automatically parse bank statements, format as CSV, then import into Treeline
- Train an ML model on your data to tag transactions, then use the ML model in a automatic tagger (see `tl new tagger --help`)
- Setup a cron job to run `tl sync` daily
- Setup a cron job to backup your data into Google Drive or Dropbox

## Getting Help

- **Bug reports & feature requests**: [GitHub Issues](https://github.com/zack-schrag/treeline-money/issues)
- **Questions & discussions**: [GitHub Discussions](https://github.com/zack-schrag/treeline-money/discussions)

When filing a bug report, please include:
- Your operating system and Python version
- The command you ran
- The full error message or unexpected behavior
- Steps to reproduce the issue

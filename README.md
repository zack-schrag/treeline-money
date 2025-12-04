# Treeline

**Personal finance that stays on your computer**

Your financial data never leaves your machine. No cloud accounts, no subscriptions, no data harvesting. Just a local database you fully control.

<!-- TODO: hero-screenshot.png - Desktop app showing the Accounts view with sidebar visible, a few accounts listed, and total net worth. Should look polished and give a sense of the full UI. -->
![Treeline](./demo.gif)

> **⚠️ Early Stage Software**: Treeline is in active development. Back up your data and expect breaking changes.

## Why Treeline?

Most finance apps want your data on their servers. Treeline keeps everything local in a DuckDB database that you can query, export, and back up however you want.

- **Your data, your rules** — Everything stored locally. No account required.
- **SQL access** — Query your finances like a database, because it is one.
- **Hackable** — Export anything, script anything, build your own plugins.

## Quick Look

<!-- TODO: quick-look.gif - 15-20 second recording showing: open app → click through Accounts/Tagging/Budget tabs → maybe tag one transaction. Keep it snappy, just enough to show the UI exists and looks good. -->
![Quick demo](./demo.gif)

## Features

- **Account Dashboard** — View all accounts, balances, and recent transactions
- **Transaction Tagging** — Categorize spending with keyboard shortcuts
- **Budget Tracking** — Set monthly targets by category and track progress
- **CSV Import** — Import bank exports with auto-detection and live preview
- **SimpleFIN Sync** — Connect banks for automatic transaction sync
- **CLI** — Optional command-line interface for scripting and automation

## Get Started

### Install

Download from [GitHub Releases](https://github.com/zack-schrag/treeline-money/releases):
- **Desktop App** — Full UI (recommended)
- **CLI only** — Standalone binary for scripting

### Try Demo Mode

Launch the app and enable Demo Mode from Settings to explore with sample data — no bank connection needed.

<!-- TODO: demo-mode.png - Screenshot of Settings with Demo Mode toggle visible, or the demo mode welcome screen -->
![Demo Mode](./demo.gif)

### Connect Your Accounts

**CSV Import** — Export transactions from your bank's website, then use the Import button in the Accounts view. The importer auto-detects columns and shows a live preview.

<!-- TODO: csv-import.png - Screenshot of the CSV import modal after a file is selected, showing the column mapping dropdowns and live preview with a few transactions. -->
![CSV Import](./demo.gif)

**SimpleFIN** — For automatic syncing, connect via Settings → Integrations. [SimpleFIN](https://beta-bridge.simplefin.org/simplefin) is a bank aggregation service ($1.50/month) that pulls transactions from your accounts automatically.

## Using Treeline

### Tagging Transactions

<!-- TODO: tagging.gif - 10 second recording of tagging workflow: select a transaction, press a number key to apply a quick tag, maybe press 'e' to edit, show the tag appearing. Demonstrates the keyboard-driven UX. -->
![Tagging](./demo.gif)

Categorize spending with tags like `groceries`, `dining`, `subscriptions`. Use keyboard shortcuts for speed: number keys apply quick tags, `e` to edit, `/` to search.

### Budget Tracking

<!-- TODO: budget.png - Screenshot of Budget view showing a few categories with progress bars, some under budget (green) and maybe one over (red). -->
![Budget](./demo.gif)

Set monthly targets by category. Categories are defined by tags — tag transactions as `groceries` to budget for groceries.

## CLI (Optional)

The app includes a CLI for scripting and automation. Run SQL queries, export data, or build custom workflows.

```bash
# Query your data
tl query "SELECT * FROM transactions WHERE amount < -100"

# Export to CSV
tl query "SELECT * FROM transactions" --format csv > export.csv

# Bulk tag transactions
tl tag groceries --ids abc123,def456
```

Key tables: `transactions`, `accounts`, `balance_snapshots`

## Examples

See [examples/](./examples/) for projects you can build:
- **marimo_dashboard** — Interactive data exploration notebook
- **markdown_report** — Generate spending reports
- **subscription_finder** — Find recurring charges

## Help

- [GitHub Issues](https://github.com/zack-schrag/treeline-money/issues) — Bugs and feature requests
- [GitHub Discussions](https://github.com/zack-schrag/treeline-money/discussions) — Questions and ideas

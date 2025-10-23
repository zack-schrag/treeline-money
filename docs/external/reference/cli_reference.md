# CLI Reference

Treeline provides a modern, Typer-based CLI for managing your financial data. All commands can be run directly from your shell - there is no REPL or interactive mode (except for the TUI commands which launch dedicated interfaces).

## Quick Reference

```bash
# Authentication and setup
treeline login                    # Login or create account
treeline setup simplefin          # Setup SimpleFIN integration

# Data management
treeline sync                     # Sync data from integrations
treeline import [file]            # Import CSV transactions
treeline status                   # Show account summary

# Query and analysis
treeline query "SELECT..."        # Execute SQL query
treeline schema [table]           # Browse database schema

# Interactive TUIs
treeline tag                      # Launch tagging interface
treeline analysis                 # Launch analysis workspace
treeline queries                  # Browse saved queries
treeline charts                   # Browse saved charts

# AI features
treeline chat                     # Interactive AI chat
treeline ask "question"           # One-shot AI question
treeline clear                    # Clear AI conversation history
```

## Command Categories

### Authentication & Setup

#### `treeline login`
Authenticate with Treeline or create a new account.

**Examples:**
```bash
# Interactive login (recommended)
treeline login

# Login with email (will prompt for password)
treeline login --email user@example.com

# Create new account
treeline login --create-account
```

**Options:**
- `--email TEXT` - Email address
- `--password TEXT` - Password (not recommended - use prompt)
- `--create-account` - Create a new account instead of signing in

---

#### `treeline setup [INTEGRATION]`
Set up financial data integrations.

**Examples:**
```bash
# Interactive wizard
treeline setup

# Direct SimpleFIN setup
treeline setup simplefin
```

**Arguments:**
- `integration` - Integration name (e.g., 'simplefin'). Omit for interactive wizard.

---

### Data Management

#### `treeline sync`
Synchronize data from connected integrations.

**Examples:**
```bash
# Sync all integrations
treeline sync

# Get JSON output for scripting
treeline sync --json
```

**Options:**
- `--json` - Output as JSON

**Output includes:**
- Accounts synced per integration
- Transactions discovered, imported, and skipped
- Balance snapshots created

---

#### `treeline import [FILE]`
Import transactions from CSV files.

**Interactive Mode** (no file path):
```bash
treeline import
# Prompts for file path, account selection, column mapping, preview
```

**Scriptable Mode** (all options via flags):
```bash
treeline import transactions.csv \
  --account-id ABC123 \
  --date-column "Date" \
  --amount-column "Amount" \
  --description-column "Description"
```

**Options:**
- `--account-id TEXT` - Account ID to import into
- `--date-column TEXT` - CSV column name for date
- `--amount-column TEXT` - CSV column name for amount
- `--description-column TEXT` - CSV column name for description
- `--debit-column TEXT` - CSV column name for debits
- `--credit-column TEXT` - CSV column name for credits
- `--flip-signs` - Flip transaction signs (for credit cards)
- `--preview` - Preview only, don't import
- `--json` - Output as JSON

---

#### `treeline status`
Show account summary and statistics.

**Examples:**
```bash
# Human-readable summary
treeline status

# JSON output for scripting
treeline status --json
```

**Options:**
- `--json` - Output as JSON

**Output includes:**
- Number of accounts
- Total transactions
- Balance snapshots
- Connected integrations
- Date range of data

---

### Query & Analysis

#### `treeline query <SQL>`
Execute a SQL query and display results.

**Examples:**
```bash
# Display as table (default)
treeline query "SELECT * FROM transactions LIMIT 10"

# Output as JSON
treeline query "SELECT * FROM transactions LIMIT 10" --json

# Output as CSV
treeline query "SELECT * FROM transactions LIMIT 10" --format csv

# Pipe to file
treeline query "SELECT * FROM transactions" --format csv > transactions.csv
```

**Arguments:**
- `sql` - SQL query to execute (SELECT/WITH only)

**Options:**
- `--format TEXT` - Output format: table, json, csv (default: table)
- `--json` - Output as JSON (alias for --format json)

**Note:** Only SELECT and WITH queries are allowed for safety.

---

#### `treeline schema [TABLE]`
Browse database schema and table structures.

**Examples:**
```bash
# List all tables
treeline schema

# Show columns for specific table
treeline schema transactions

# Output as JSON
treeline schema transactions --json
```

**Arguments:**
- `table` - Table name to inspect (omit to list all tables)

**Options:**
- `--json` - Output as JSON

---

### Interactive TUI Commands

These commands launch full-screen Textual TUI applications for complex workflows.

#### `treeline tag`
Launch interactive transaction tagging interface.

**Examples:**
```bash
# Tag all transactions
treeline tag

# Show only untagged transactions
treeline tag --untagged
```

**Options:**
- `--untagged` - Show only untagged transactions

**Features:**
- Keyboard-driven rapid tagging
- AI-suggested tags
- Multi-tag support
- Account filtering

---

#### `treeline analysis`
Launch interactive data analysis workspace.

**Description:** A Jupyter-like split-panel environment for SQL editing, results viewing, and chart creation.

**Keyboard Shortcuts:**
- `Opt+Enter` / `F5` - Execute query
- `Tab` - Switch focus between SQL editor and results
- `g` - Create chart (wizard)
- `v` - Toggle results ↔ chart view
- `s` - Save query or chart
- `r` - Reset (clear results/chart)
- `?` - Show help
- `Ctrl+C` - Exit

**Example:**
```bash
treeline analysis
```

---

#### `treeline queries`
Browse and manage saved queries.

**Features:**
- List all saved queries
- Load queries into analysis mode
- Delete queries
- Rename queries

**Example:**
```bash
treeline queries
```

---

#### `treeline charts`
Browse and manage saved charts.

**Features:**
- List all saved charts
- Load charts (opens in analysis mode)
- Delete charts
- Rename charts

**Example:**
```bash
treeline charts
```

---

### AI Features

#### `treeline chat`
Start an interactive AI conversation about your finances.

**Example:**
```bash
treeline chat

You: What was my spending on dining last month?
AI: [Shows answer with SQL used]

You: Show me a breakdown by restaurant
AI: [Runs follow-up query]
```

**Commands:**
- Type `exit` or `quit` to end the chat
- Press `Ctrl+C` to exit

---

#### `treeline ask <QUESTION>`
Ask AI a one-shot question about your finances.

**Examples:**
```bash
# Ask a question
treeline ask "What's my spending on groceries this month?"

# Get response as JSON
treeline ask "Show my account balances" --json
```

**Arguments:**
- `question` - Question to ask AI

**Options:**
- `--json` - Output as JSON

---

#### `treeline clear`
Clear AI conversation history.

**Example:**
```bash
treeline clear
```

---

## Scripting with Treeline

Treeline commands are designed to work well in scripts and automation:

```bash
#!/bin/bash
# Daily financial snapshot script

echo "=== Daily Financial Snapshot ==="

# Sync latest data
treeline sync

# Get transaction count
treeline query "SELECT COUNT(*) as total_transactions FROM transactions" --json

# Check spending today
treeline query "SELECT SUM(amount) as daily_spending
                FROM transactions
                WHERE transaction_date = CURRENT_DATE" --json
```

## Output Formats

Many commands support multiple output formats for flexibility:

### Table Format (default)
Human-readable, formatted for terminal display.

### JSON Format (`--json`)
Machine-readable, perfect for scripting and automation.

```json
{
  "columns": ["date", "amount", "description"],
  "rows": [...],
  "row_count": 10
}
```

### CSV Format (`--format csv`)
Parseable by spreadsheet tools and data processing scripts.

```csv
date,amount,description
2025-10-15,342.50,Whole Foods
2025-10-12,287.18,Restaurant Week
```

## Getting Help

Get help on any command:
```bash
treeline --help              # Show all commands
treeline login --help        # Show help for login command
treeline query --help        # Show help for query command
```

## Version Information

Check your Treeline version:
```bash
treeline --version
```

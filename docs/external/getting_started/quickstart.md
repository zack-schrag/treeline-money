# Quickstart

Welcome to Treeline! Follow this guide to get set up with Treeline, import your data, and start exploring your finances!

## Step 1: Installation

### pip Install
```bash
pip install treeline-money
```

### Native Install (coming soon)
Pre-built binaries for macOS, Linux, and Windows will be available soon.

---

## Step 2: Log In or Create an Account

Treeline requires an account to sync data across devices and enable cloud features.

```bash
treeline login
```

You'll be prompted to either:
- **Log in** with existing credentials
- **Create a new account** (select the option when prompted)

Follow the interactive prompts to authenticate.

---

## Step 3: Initialize Your Workspace

Navigate to where you want to store your financial data:

```bash
cd /path/to/data
treeline status
# Initializes treeline in the current directory
# This creates a "treeline" folder in /path/to/data
```

Your data will be stored in `~/.treeline/`:
- `[user-id].duckdb` - Your encrypted DuckDB database
- `queries/` - Saved SQL queries
- `charts/` - Saved chart configurations

---

## Step 4: Import Your Data

Treeline supports several ways to get your financial data:

### SimpleFIN (Recommended)

SimpleFIN lets you securely share your financial data with apps like Treeline. We are not associated with SimpleFIN - it's a completely separate entity, and you will need your own paid account ($1.50/month or $15/year).

**Why SimpleFIN?**

1. **Extremely simple** - Sign up, connect banks, generate a setup token. Done.
2. **Reusable connections** - Use your bank connections with multiple apps
3. **Data portability** - Your data isn't locked to one app
4. **Cost-effective** - Helps us keep our infrastructure costs low

#### Setup Steps

1. Create a SimpleFIN account at https://beta-bridge.simplefin.org/
2. Connect your bank accounts
3. Generate a setup token (see https://beta-bridge.simplefin.org/info/developers)
4. In Treeline, run:

```bash
treeline setup simplefin
```

5. Enter your setup token when prompted
6. Treeline will fetch your accounts and recent transactions
7. Confirm the preview and import

That's it! Treeline will automatically sync your data daily.

### CSV Import

You can also import CSV files downloaded from your bank:

```bash
treeline import
```

Follow the interactive prompts to:
1. Select the CSV file
2. Choose which account to import into
3. Review auto-detected column mappings
4. Preview the transactions
5. Confirm and import

For scriptable CSV imports:
```bash
treeline import transactions.csv \
  --account-id YOUR_ACCOUNT_ID \
  --date-column "Date" \
  --amount-column "Amount" \
  --description-column "Description"
```

### Plaid (Coming Soon)

Plaid integration is coming soon for broader bank support.

---

## Step 5: Explore Your Data

Now that your data is imported, start exploring!

### Check Your Status

```bash
treeline status
```

View account summary, transaction count, and connected integrations.

### Run SQL Queries

```bash
treeline query "SELECT * FROM transactions LIMIT 10"
```

### Browse Schema

```bash
treeline schema                  # List all tables
treeline schema transactions     # Show columns for transactions table
```

### Launch Analysis Mode

```bash
treeline analysis
```

This opens a full-screen TUI with:
- SQL editor (bottom panel)
- Results viewer (top panel)
- Integrated charting
- Save/load queries and charts

See the [TUI Interfaces Guide](../reference/slash_commands.md) for keyboard shortcuts.

---

## Step 6: Tag Your Transactions

Categorize your transactions using the tagging interface:

```bash
treeline tag --untagged
```

This launches an interactive TUI where you can:
- Navigate transactions with arrow keys
- Apply AI-suggested tags with number keys
- Add custom tags with `t`
- Quickly process hundreds of transactions

See the [Tag Mode documentation](../reference/slash_commands.md#tag-mode) for details.

---

## Step 7: Ask AI Questions

Treeline includes AI features to help you analyze your finances:

### Interactive Chat

```bash
treeline chat
```

Then ask questions like:
- "What was my total spending last month?"
- "Show me my top 5 expense categories"
- "How much did I spend on dining in October?"

### One-Shot Questions

```bash
treeline ask "What's my average monthly spending?"
```

---

## Essential Commands

| Command | Description | Example |
|---------|-------------|---------|
| `treeline login` | Login or create account | `treeline login` |
| `treeline setup` | Setup integrations | `treeline setup simplefin` |
| `treeline sync` | Sync data from integrations | `treeline sync` |
| `treeline status` | Show account summary | `treeline status` |
| `treeline import` | Import CSV transactions | `treeline import` |
| `treeline tag` | Tag transactions | `treeline tag --untagged` |
| `treeline analysis` | Launch analysis workspace | `treeline analysis` |
| `treeline query` | Run SQL query | `treeline query "SELECT ..."` |
| `treeline chat` | AI chat about finances | `treeline chat` |

For a complete command reference, see [CLI Reference](../reference/cli_reference.md).

---

## What's Next?

### Explore Advanced Features

- **Saved Queries** - Save frequently-used SQL queries in analysis mode
- **Charts** - Create visualizations with the chart wizard (`g` in analysis mode)
- **Custom Analysis** - Build complex queries and dashboards
- **Automation** - Use scriptable commands in cron jobs or scripts

### Learn the Interfaces

- **[CLI Reference](../reference/cli_reference.md)** - All available commands
- **[TUI Interfaces](../reference/slash_commands.md)** - Keyboard shortcuts and workflows
- **[Ways to Use Treeline](../guides/ways_to_use.md)** - Different ways to access your data

### Join the Community

- **Documentation**: https://docs.treeline.money
- **Issues**: https://github.com/treeline-money/treeline/issues
- **Community**: https://discord.gg/treeline

---

## Troubleshooting

### "Not authenticated" Error

Run `treeline login` to authenticate first.

### Can't Find My Database

Your database is in `~/.treeline/[user-id].duckdb` in your home directory.

### CSV Import Not Working

Make sure your CSV has at least these columns:
- Date column
- Amount column (or separate Debit/Credit columns)
- Description column

Use `--preview` to test before importing:
```bash
treeline import file.csv --preview
```

### SimpleFIN Setup Fails

1. Verify your setup token is correct
2. Check that your SimpleFIN account is active
3. Try generating a new setup token

For more help, see the [full documentation](https://docs.treeline.money) or ask in the community Discord.

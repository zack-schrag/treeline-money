# CLI Reference

Treeline can be used in two ways:
1. **Interactive mode** - Run `treeline` with no arguments to enter a REPL where you can use slash commands and natural language
2. **Scriptable commands** - Run specific commands directly from your shell for scripting and automation

## Interactive Mode

**Command:** `treeline`

**Description:** Enter Treeline interactive mode with a REPL interface

**Example:**
```bash
treeline
# You'll see a prompt where you can use slash commands or ask questions
> /status
> /query SELECT * FROM transactions LIMIT 5
> /import
> /tag
> What was my spending last month?
```

### Available Slash Commands (Interactive Mode Only)

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/login` | Login or create your Treeline account |
| `/status` | Shows summary of current state of your financial data |
| `/query <SQL>` | Execute a SQL query directly (SELECT/WITH only) |
| `/simplefin` | Setup SimpleFIN connection |
| `/sync` | Run an on-demand data synchronization |
| `/import` | Import CSV file of transactions |
| `/tag` | Enter tagging power mode |
| `/clear` | Clear conversation history and start fresh |
| `/exit` | Exit the Treeline REPL |

**Note:** Press `Ctrl+C` at any prompt to cancel and return to the main REPL prompt. Use `/exit` or type `exit` to quit the program.

## Scriptable Commands

These commands are available as top-level CLI commands for use in scripts, automation, and by AI agents. They can be run directly without entering interactive mode.

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `treeline status` | Shows summary of current state of your financial data | `treeline status` |
| `treeline query <SQL>` | Execute a SQL query directly (SELECT/WITH only) | `treeline query "SELECT COUNT(*) FROM transactions"` |
| `treeline sync` | Run an on-demand data synchronization | `treeline sync` |

### Usage Examples

**Check your financial status:**
```bash
treeline status
```

**Run a SQL query:**
```bash
treeline query "SELECT COUNT(*) as total_transactions FROM transactions"
treeline query "SELECT * FROM transactions WHERE amount < 0 ORDER BY transaction_date DESC LIMIT 10"
treeline query "SELECT account_id, SUM(amount) as total FROM transactions GROUP BY account_id"
```

**Sync your accounts:**
```bash
treeline sync
```

**Scripting with Treeline:**
```bash
#!/bin/bash
# Daily financial snapshot script
echo "=== Daily Financial Snapshot ==="
treeline sync
treeline query "SELECT SUM(amount) as daily_spending FROM transactions WHERE transaction_date = CURRENT_DATE"
treeline query "SELECT COUNT(*) as new_transactions FROM transactions WHERE created_at::date = CURRENT_DATE"
```

**AI Agent Usage:**
AI agents (like Claude Code) can use these commands for debugging and analysis:
```bash
# Check system status
uv run treeline status

# Run analytical queries
uv run treeline query "SELECT * FROM transactions WHERE amount > 100 ORDER BY amount DESC LIMIT 5"

# Sync latest data
uv run treeline sync
```

### Help

Get help on any command:
```bash
treeline --help
treeline query --help
```

## Interactive vs Scriptable

**Interactive commands** (`/login`, `/import`, `/tag`, `/simplefin`):
- Require user input and interaction
- Only available as slash commands in interactive mode
- Best for human-driven workflows

**Scriptable commands** (`status`, `query`, `sync`):
- Work non-interactively
- Available both as slash commands (in interactive mode) AND top-level CLI commands
- Perfect for automation, scripts, and AI agents

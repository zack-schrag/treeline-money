# Treeline Vision
Treeline is like Obsidian for personal finance - your data in DuckDB with a documented schema, with tools and plugins built on top.

## PRFAQ
Treeline Money LLC, today announced the introduction of Treeline, a personal finance tool inspired by Obsidian's approach to note-taking. Previously, power users have been stuck building custom spreadsheets, manually exporting CSV files, or forced to conform to a budget app's prescriptive tools that lock in their data. Treeline stores your financial data in DuckDB with a documented schema that you truly own, with a growing ecosystem of tools and plugins that work with that data.

**Treeline is the Obsidian of personal finance.** Just as Obsidian is built on plain markdown files, Treeline is built on DuckDB with a specific schema. Your data lives in a DuckDB database on your computer at `~/.treeline/data.duckdb`. The schema is documented and stable - any tool can read and write to it.

The core Treeline CLI provides essential functionality:
- Importing data
- Syncing data peridiocally
- Basic SQL queries
- Transaction tagging

The CLI is designed for scripting - all commands work in non-interactive mode for automation.

Because your data is in DuckDB with a documented schema, you can use whatever tools you prefer:
- Jupyter notebooks for analysis
- Python/R scripts for custom reports
- BI tools like Metabase or Tableau for dashboards
- Your own custom applications
- AI assistants via MCP (Model Context Protocol)

Treeline is local-first. All data lives on your computer in `~/.treeline/`. Optional cloud backup through plugins keeps your data encrypted server-side.

## Core Features

### Auto-Taggers
Define custom tagging logic using simple Python functions. Auto-taggers run automatically during sync to categorize transactions. Examples:
- Tag all grocery store purchases
- Flag large purchases for review
- Extract ticket numbers from descriptions
- Complex logic with date patterns, amount thresholds, etc.

Auto-taggers can be created via the CLI (`treeline new tagger`) or through plugin UIs. Power users write Python directly, while plugins can generate Python code from UI forms.

All taggers are just Python files in `~/.treeline/taggers/` - edit them directly or generate them through tools.

### Interactive Tag Mode
Rapid transaction tagging interface with keyboard shortcuts. Suggested tags learn from your history. Jump between transactions, bulk tag, and undo mistakes easily. This is built into the core CLI.

### MCP Server Integration
Treeline provides an MCP (Model Context Protocol) server, allowing AI assistants like Claude to interact with your financial data. Ask questions in natural language:
- "What were my top spending categories last month?"
- "Show me transactions over $100 in the last week"
- "How does my spending this quarter compare to last quarter?"

The AI can query your data, but you control access. Your data stays on your computer.

## Plugin Ecosystem

Treeline's power comes from its plugin architecture. The core provides the DuckDB schema and essential CLI tools. Plugins extend functionality:

### Core Plugins (Future)
Core plugins are built and maintained by Treeline, providing essential features:
- **Multi-device Sync** - Cloud backup and mobile app access
- **Query Builder** - Save and browse SQL queries, build charts
- **Alerts** - Custom notifications based on query thresholds
- **Simple Budget** - Traditional envelope budgeting with categories

### Community Plugins (Future)
- **Retirement Planner** - Scenario modeling and projections
- **Export** - Generate reports in various formats (PDF, CSV, Markdown)
- **Mortgage Tracker** - Track mortgage principal, interest, equity
- **Investment Analysis** - Portfolio performance tracking

### Plugin Capabilities
Plugins can extend Treeline by:
- Adding database tables (extends the core schema)
- Providing UI components (web/mobile interfaces)
- Adding CLI commands
- Bundling auto-tagger templates
- Providing data visualizations

## Pricing
Treeline Core (CLI) is **free and open source**.

Optional paid features through plugins:
- **Multi-device Sync** - $5/month - Cloud backup and mobile app access
- **Core Plugin Bundle** - $10/month - All core plugins (Query Builder, Alerts, Budget)

MCP server is free - bring your own AI API key (Claude, GPT, or local models).

## Customer Testimonies
> I have spent years trying every budgeting app and even building my own custom spreadsheets. But they all lacked something: budgeting apps were too rigid. Custom spreadsheets lacked automation. Treeline is the first tool where I actually own my data in a format I can use. As a data analyst, I can query it with SQL, analyze it in Jupyter notebooks, or visualize it with Tableau - using the tools I'm already familiar with.
> - Albert from San Francisco

> The tag mode is incredible. Every budgeting app makes you categorize transactions, but it's always tedious. Treeline's keyboard shortcuts and suggested tags make it actually fast. And the auto-taggers mean most transactions are already tagged when I sync. I can write custom Python logic for my specific spending patterns.
> - Blake from New York

> I love that I can use Claude to query my finances via MCP. I just ask "show me my spending trend for the last 6 months" and it writes the SQL for me. But the best part is I can see exactly what query it ran and learn from it.
> - Charlie from Seattle

> Treeline feels like the Unix philosophy applied to personal finance. Small tools that do one thing well, composable together. The CLI handles syncing and tagging, I wrote Python scripts for custom reports, and I use Metabase for dashboards. Everything just reads from the same DuckDB file. Perfect.
> - Delila from Chicago 

## External FAQ

1. **Do I have to know SQL?**
    Not necessarily. You can use AI via MCP to ask questions in natural language. The AI writes SQL for you, and you can see the queries it generates. Many users learn SQL this way. But direct SQL access via `treeline query` is always available.

2. **Why CLI? Why not just a GUI app?**
    The CLI is for power users who want direct access to their data. It's designed for scripting and automation. Future plugins will provide GUI interfaces (web/mobile) for non-technical users, but the CLI remains the foundation. Think of it like git - the CLI is powerful, but GitHub provides a GUI on top.

3. **Do you have a mobile app?**
   Not yet, but it's planned as part of the Multi-device Sync plugin. The mobile app will provide read-only views of your data, with the ability to add tags to transactions on the go.

4. **Can I budget with this?**
   Yes, with a plugin! Treeline core uses "tags" instead of categories. Tags are more flexible - you can apply multiple tags to a transaction (e.g., "vacation" AND "food"). For traditional envelope budgeting with categories, install the Simple Budget plugin.

5. **How secure is my data?**
   Your data lives on your computer in `~/.treeline/`. It never leaves your machine unless you allow it. 

6. **How do I get my data into Treeline?**
    Treeline supports SimpleFIN (recommended) and manual CSV imports. Plaid support is planned.

7. **Can I build my own scripts and automation?**
    Absolutely! The CLI is designed for scripting. All commands work non-interactively. Examples:
    - `treeline sync && treeline query "SELECT ..." --json | jq ...`
    - Cron jobs to sync daily and send reports
    - Python scripts that read from `~/.treeline/data.duckdb` directly

8. **What if Treeline shuts down?**
    Your data is in a standard DuckDB file with a documented schema. You can query it with any tool that supports DuckDB. You're not locked in. This is the whole point.

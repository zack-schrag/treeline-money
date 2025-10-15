# Treeline

**AI-native personal finance in your terminal**

Treeline is a terminal-native financial analysis tool that gives you complete control over your financial data. Built for developers, data analysts, and power users who want the flexibility of SQL with the power of AI.

## Features

- **AI-Powered Chat** - Ask questions in natural language, get instant SQL-backed answers
- **Interactive Analysis Workspace** - Jupyter-like environment for SQL exploration and charting
- **Smart Tagging** - Keyboard-driven transaction categorization with AI suggestions
- **Direct SQL Access** - Full DuckDB access to your financial data
- **Automatic Sync** - SimpleFIN integration for seamless bank synchronization
- **Fully Scriptable** - JSON output, CSV export, and command-line automation
- **Terminal TUIs** - Beautiful Textual interfaces for complex workflows
- **Local-First** - Your data lives on your machine, encrypted and portable

## Quick Start

### Installation

```bash
pip install treeline-money
```

### Getting Started

```bash
# 1. Login or create account
treeline login

# 2. Set up SimpleFIN integration
treeline setup simplefin

# 3. Sync your data
treeline sync

# 4. Start exploring
treeline status                          # View account summary
treeline analysis                        # Launch analysis workspace
treeline tag --untagged                  # Tag transactions
treeline chat                            # Chat with AI about your finances
```

## Core Commands

### Data Management

```bash
treeline sync                            # Sync from connected integrations
treeline import                          # Import CSV transactions
treeline status                          # Show account summary
treeline status --json                   # Get status as JSON
```

### Query & Analysis

```bash
treeline query "SELECT * FROM transactions LIMIT 10"
treeline query "SELECT * FROM accounts" --format csv
treeline schema                          # List all tables
treeline schema transactions             # Show table columns
treeline analysis                        # Launch interactive workspace
```

### Tagging & Organization

```bash
treeline tag                             # Launch tagging interface
treeline tag --untagged                  # Show only untagged transactions
```

### AI Features

```bash
treeline chat                            # Interactive AI conversation
treeline ask "What's my spending on groceries this month?"
treeline clear                           # Clear conversation history
```

### Saved Queries & Charts

```bash
treeline queries                         # Browse saved queries
treeline charts                          # Browse saved charts
```

## Scriptability

Treeline commands are designed for automation and scripting:

```bash
# Get transaction count
treeline status --json | jq .total_transactions

# Export to CSV
treeline query "SELECT * FROM transactions" --format csv > transactions.csv

# Daily sync script
#!/bin/bash
treeline sync
treeline status --json > daily_snapshot.json
```

## Interactive TUI Interfaces

### Analysis Mode
Launch with `treeline analysis`:
- Split-panel SQL editor and results viewer
- Press `Alt+Enter` to execute queries
- Press `g` to create charts
- Press `s` to save queries and charts
- Press `v` to toggle between results and chart view

### Tag Mode
Launch with `treeline tag`:
- Rapid keyboard-driven tagging
- AI-suggested tags
- Multi-tag support
- Filter by account or untagged

## Architecture

Treeline follows hexagonal architecture principles:
- **CLI Layer** - Thin presentation layer (Typer + Rich)
- **Service Layer** - All business logic lives here
- **Domain Layer** - Core entities and abstractions
- **Infrastructure Layer** - DuckDB, Supabase, SimpleFIN, OpenAI

See [docs/internal/architecture.md](./docs/internal/architecture.md) for details.

## Development

### Setup

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest tests/unit

# Run CLI locally
uv run treeline --help
```

### Project Structure

```
src/treeline/
├── cli.py                    # Main Typer CLI app
├── commands/                 # TUI implementations (Textual)
├── app/
│   ├── service.py           # Business logic services
│   └── container.py         # Dependency injection
├── domain.py                # Domain models
├── abstractions/            # Port interfaces
└── infra/                   # Infrastructure implementations
```

### Testing

```bash
# Unit tests (mocked dependencies)
uv run pytest tests/unit -v

# Test specific module
uv run pytest tests/unit/app/test_sync_service.py -v
```

## Documentation

- **User Guides** - [docs/external/](./docs/external/)
  - [Quickstart](./docs/external/getting_started/quickstart.md)
  - [CLI Reference](./docs/external/reference/cli_reference.md)
  - [TUI Interfaces](./docs/external/reference/slash_commands.md)
  - [Ways to Use Treeline](./docs/external/guides/ways_to_use.md)

- **Developer Docs** - [docs/internal/](./docs/internal/)
  - [Architecture](./docs/internal/architecture.md)
  - [Implementation Plan](./docs/internal/implementation_plan.md)

## Contributing

See [CLAUDE.md](./CLAUDE.md) for development guidelines:
- Code style (ruff, type hints)
- Test-driven development
- Hexagonal architecture principles
- CLI architecture rules

## License

[Add license information]

## Links

- Documentation: https://docs.treeline.money (coming soon)
- Issues: https://github.com/treeline-money/treeline/issues
- Community: https://discord.gg/treeline (coming soon)

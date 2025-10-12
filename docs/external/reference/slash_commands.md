# Slash Commands

Slash commands in the Treeline REPL provide quick access to common operations. When you type `/` in the interactive mode, you'll see autocomplete suggestions for available commands. Use Tab to complete or arrow keys to navigate suggestions.

Command | Description
--- | ---
/help | Show all available commands
/login | Login or create your Treeline account
/status | Shows summary of current state of your financial data
/simplefin | Setup SimpleFIN connection
/import | Import CSV file of transactions
/tag | Enter tagging power mode
/plugins | Manage plugins
/sync | Run an on-demand data synchronization from your connected accounts
/query <SQL> | Execute a single-line SQL query directly (SELECT and WITH queries only)
/query:name | Run a saved query by name (e.g., /query:dining_this_month)
/sql | Open multi-line SQL editor with syntax highlighting and saved query autocomplete (press Tab to see saved queries, Option/Alt+Enter or F5 to execute)
/analysis | Open interactive analysis workspace - a Jupyter-like environment with split-panel TUI for SQL editing, results viewing, and chart creation all in one view
/schema [table] | Browse database schema - list all tables or show columns for a specific table
/queries [list\|show\|delete] | Manage saved queries - list all, show SQL, or delete a query
/chart [name] | Run a saved chart by name, or list all saved charts if no name provided. Charts are created after running queries via the chart wizard.
/clear | Clear the screen
/exit | Exit the Treeline REPL

## Analysis Mode

The `/analysis` command opens an interactive workspace designed for fluid data exploration. Unlike `/sql` which runs a single query and exits, analysis mode keeps you in a split-panel interface where you can:

- Write and edit SQL in a bottom panel with syntax highlighting
- View results in a top panel (with column windowing and scrolling)
- Create charts directly from results without leaving the TUI
- Save queries and charts with simple keystrokes
- Iterate quickly: query → results → chart → edit → repeat

### Keyboard Shortcuts

When in analysis mode, use these keyboard shortcuts:

Shortcut | Action
--- | ---
**Ctrl+Enter** | Execute the current SQL query (auto-focuses to results)
**Tab** | Switch focus between SQL editor and data panel
**↑↓←→** | Context-aware navigation (edit SQL when editor focused, scroll results when data panel focused)
**Shift+←→** | Scroll columns horizontally (when viewing wide tables)
**v** | Toggle between results view and chart view
**g** | Open chart wizard to create/edit a chart (step-by-step: type → X column → Y column)
**s** | Save current query or chart (prompts for name)
**l** | Load saved query or chart (browse with arrow keys, Enter to load)
**r** | Reset - clear results and chart but keep SQL
**?** | Show help overlay with all shortcuts
**Ctrl+C** | Exit analysis mode

### Chart Wizard

Press `g` to enter the chart wizard:
1. Choose chart type (1=bar, 2=line, 3=scatter, 4=histogram)
2. Select X-axis column (press number key)
3. Select Y-axis column (press number key, skipped for histograms)

The chart displays immediately in the data panel. Press `v` to toggle between results and chart views.

### When to Use Analysis Mode

Use `/analysis` when you want a **fluid, exploratory workflow** where everything stays visible. Think of it as a lightweight Jupyter notebook for SQL and charts.

Use `/sql` for quick one-off queries or when you want to run a saved query with autocomplete.

Use `/chart` to run a standalone saved chart from the command line.

## Suggested Enhancements
- Add success/error examples for each command so users understand expected output and side effects.
- Group commands by domain (session management, data ingestion, analysis, configuration) to improve scanability for new users.

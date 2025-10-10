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
/schema [table] | Browse database schema - list all tables or show columns for a specific table
/queries [list\|show\|delete] | Manage saved queries - list all, show SQL, or delete a query
/chart [name] | Run a saved chart by name, or list all saved charts if no name provided. Charts are created after running queries via the chart wizard.
/clear | Clear the screen
/exit | Exit the Treeline REPL

## Suggested Enhancements
- Add success/error examples for each command so users understand expected output and side effects.
- Group commands by domain (session management, data ingestion, analysis, configuration) to improve scanability for new users.

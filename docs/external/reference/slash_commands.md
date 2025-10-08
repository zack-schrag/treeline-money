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
/sql | Open multi-line SQL editor with syntax highlighting
/clear | Clear the screen
/exit | Exit the Treeline REPL

## Suggested Enhancements
- Add success/error examples for each command so users understand expected output and side effects.
- Group commands by domain (session management, data ingestion, analysis, configuration) to improve scanability for new users.

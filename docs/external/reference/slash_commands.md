# Interactive TUI Interfaces

Treeline provides several full-screen Textual TUI (Terminal User Interface) applications for complex workflows. These interfaces provide keyboard-driven, distraction-free environments optimized for specific tasks.

## Overview

| Command | Description | When to Use |
|---------|-------------|-------------|
| `treeline analysis` | SQL editor + results + charting | Exploratory data analysis, building visualizations |
| `treeline tag` | Rapid transaction tagging | Categorizing transactions quickly |
| `treeline queries` | Saved query browser | Managing and loading saved SQL queries |
| `treeline charts` | Saved chart browser | Managing and loading saved chart configurations |

---

## Analysis Mode

**Command:** `treeline analysis`

A Jupyter-like split-panel workspace for fluid data exploration. Think of it as an IDE for your financial data.

### Layout

```
┌─ Results Panel ────────────────────────────────┐
│ date        │ amount  │ description           │
│ 2025-10-15  │ $342.50 │ Whole Foods          │
│ 2025-10-12  │ $287.18 │ Restaurant Week      │
│ 2025-10-08  │ $217.64 │ Local Cafe           │
├───────────────────────────────────────────────┤
│ [g] chart  [s] save  [v] view  [?] help      │
└───────────────────────────────────────────────┘
┌─ SQL Editor ───────────────────────────────────┐
│ SELECT transaction_date, amount, description  │
│ FROM transactions                             │
│ WHERE 'dining' = ANY(tags)                    │
│ ORDER BY transaction_date DESC █             │
└───────────────────────────────────────────────┘
```

### Features

- **Split-panel interface** - SQL editor and results always visible
- **Live query execution** - See results instantly
- **Integrated charting** - Create visualizations without leaving the workspace
- **Saved queries and charts** - Save and reload your work
- **Syntax highlighting** - SQL syntax highlighting with Monokai theme
- **Smart navigation** - Tab between panels, context-aware shortcuts

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Alt+Enter** | Execute the current SQL query |
| **F5** | Execute query (alternative binding) |
| **Tab** | Switch focus between SQL editor and results panel |
| **↑↓** | Navigate results rows (when results focused) |
| **g** | Open chart wizard to create/edit a chart |
| **v** | Toggle between results view and chart view |
| **s** | Save current query or chart (prompts for name) |
| **r** | Reset - clear results and chart but keep SQL |
| **?** | Show help overlay with all shortcuts |
| **Ctrl+C** | Exit analysis mode |

### Chart Wizard

Press `g` to enter the chart wizard:

1. **Choose chart type:**
   - `1` - Bar chart
   - `2` - Line chart
   - `3` - Scatter plot
   - `4` - Histogram

2. **Select X-axis column:**
   - Press number key corresponding to column (1-9)

3. **Select Y-axis column:**
   - Press number key corresponding to column (1-9)
   - Skipped for histograms

The chart displays immediately in the results panel. Press `v` to toggle between results and chart views.

### Workflow Example

1. Launch analysis mode:
   ```bash
   treeline analysis
   ```

2. Write a SQL query in the bottom panel
3. Press `Alt+Enter` to execute
4. Review results in the top panel
5. Press `g` to create a chart
6. Press `s` to save the query or chart
7. Iterate: edit SQL → execute → visualize → save

### When to Use

Use `treeline analysis` when you want a **fluid, exploratory workflow** where everything stays visible. Perfect for:

- Building complex queries iteratively
- Creating and refining visualizations
- Exploring data without context switching
- Building reusable queries and charts

---

## Tag Mode

**Command:** `treeline tag` or `treeline tag --untagged`

A keyboard-driven interface for rapidly tagging transactions.

### Features

- **Rapid navigation** - Arrow keys or vim-style navigation (j/k)
- **AI-suggested tags** - Smart suggestions based on transaction description and history
- **Multi-tag support** - Apply multiple tags to a single transaction
- **Filter by account** - Focus on specific accounts
- **Untagged mode** - Show only untagged transactions (`--untagged`)

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **↑↓** or **j/k** | Navigate transactions |
| **1-9** | Apply suggested tag by number |
| **t** | Add custom tag |
| **Enter** | Edit tags for current transaction |
| **d** | Remove all tags from current transaction |
| **/** | Search/filter transactions |
| **a** | Filter by account |
| **u** | Toggle untagged-only view |
| **Ctrl+C** | Exit tag mode |

### Workflow Example

1. Launch tag mode:
   ```bash
   treeline tag --untagged
   ```

2. Review transaction details and suggested tags
3. Press number key to apply a suggested tag
4. Press `t` to add a custom tag if needed
5. Navigate to next transaction with `↓` or `j`
6. Repeat until all transactions are tagged

### When to Use

Use `treeline tag` when you need to:

- Categorize transactions quickly
- Process weeks of transactions in minutes
- Apply consistent tagging with AI assistance
- Clean up untagged transactions

---

## Queries Browser

**Command:** `treeline queries`

Browse, manage, and load saved SQL queries.

### Features

- **List view** - See all saved queries
- **Preview** - View SQL before loading
- **Load** - Open query in analysis mode
- **Delete** - Remove unwanted queries
- **Rename** - Change query names

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **↑↓** | Navigate query list |
| **Enter** | Load selected query in analysis mode |
| **d** | Delete selected query |
| **r** | Rename selected query |
| **Esc** or **q** | Exit queries browser |

### Workflow Example

1. Launch queries browser:
   ```bash
   treeline queries
   ```

2. Navigate to a saved query
3. Press `Enter` to load it
4. Analysis mode opens with the query pre-loaded
5. Modify and execute as needed

### When to Use

Use `treeline queries` when you want to:

- Browse your saved SQL queries
- Load a frequently-used query
- Clean up old queries
- Rename queries for better organization

---

## Charts Browser

**Command:** `treeline charts`

Browse, manage, and load saved chart configurations.

### Features

- **List view** - See all saved charts with metadata
- **Preview** - View chart configuration (query, type, columns)
- **Load** - Open chart in analysis mode (executes query and shows chart)
- **Delete** - Remove unwanted charts
- **Rename** - Change chart names

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **↑↓** | Navigate chart list |
| **Enter** | Load selected chart in analysis mode |
| **d** | Delete selected chart |
| **r** | Rename selected chart |
| **Esc** or **q** | Exit charts browser |

### Workflow Example

1. Launch charts browser:
   ```bash
   treeline charts
   ```

2. Navigate to a saved chart
3. Press `Enter` to load it
4. Analysis mode opens, executes the query, and displays the chart
5. Toggle to results view with `v` if needed
6. Modify and re-execute as needed

### When to Use

Use `treeline charts` when you want to:

- View your saved visualizations
- Reload a dashboard chart
- Clean up old charts
- Rename charts for better organization

---

## Tips for TUI Interfaces

### General Best Practices

1. **Learn the shortcuts** - Press `?` in analysis mode to see all shortcuts
2. **Save frequently** - Press `s` to save queries and charts you want to keep
3. **Use descriptive names** - Name queries like `monthly_dining_breakdown` not `query1`
4. **Iterate quickly** - Don't try to write perfect SQL first time, iterate and refine

### Performance Tips

1. **Limit results during exploration** - Use `LIMIT 100` while building queries
2. **Remove limits for final charts** - Charts need all data for accurate visualization
3. **Use indexes** - If queries are slow, check if you need indexes on common filter columns

### Workflow Patterns

**Exploratory Analysis:**
1. Start in `treeline analysis`
2. Build query iteratively
3. Create chart when satisfied
4. Save both query and chart

**Rapid Tagging:**
1. Sync new data: `treeline sync`
2. Tag untagged: `treeline tag --untagged`
3. Process transactions quickly
4. Exit when done

**Dashboard Review:**
1. Open saved charts: `treeline charts`
2. Load key dashboard charts
3. Review visualizations
4. Modify queries if needed

---

## Comparison with CLI Commands

| Task | TUI Command | CLI Command |
|------|-------------|-------------|
| Run one-off query | `treeline analysis` | `treeline query "SELECT..."` |
| Tag transactions | `treeline tag` | _(No CLI equivalent - interactive only)_ |
| View saved charts | `treeline charts` | _(No CLI equivalent - interactive only)_ |
| Execute saved query | `treeline queries` → Load | _(Future: `treeline query --saved name`)_ |
| Get account status | `treeline analysis` → query | `treeline status` |

Use **TUI commands** when you want an interactive, keyboard-driven workflow with visual feedback.

Use **CLI commands** when you want quick, scriptable operations suitable for automation.

---

## Keyboard Navigation Philosophy

All Treeline TUIs follow these principles:

1. **Vim-inspired** - Where it makes sense (j/k for navigation)
2. **Mnemonic** - Shortcuts match action names (g=chart, s=save, r=reset)
3. **Discoverable** - Help is always available with `?`
4. **Consistent** - Similar actions use similar keys across interfaces
5. **Minimal modifiers** - Most actions are single keys, not Ctrl+Alt+Shift+X

This makes the interfaces fast to learn and even faster to use once you've learned them.

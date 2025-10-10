# Update Documentation for Analysis Mode

## Problem

With all analysis mode features implemented, we need to update documentation to:
1. Explain the new `/analysis` command
2. Clarify the updated `/sql` and `/chart` behaviors
3. Update landing page and PRFAQ to showcase fluid workflow
4. Provide migration guidance for existing users

## Solution

Comprehensive documentation update across external and internal docs.

## Documentation Updates

### 1. Landing Page (`docs/external/landing_page.md`)

**Add analysis mode as primary example:**

```markdown
## How It Works

### Fluid Data Exploration with `/analysis` Mode

Treeline's analysis mode is like a debug session for your financial data:

> /analysis

SQL> SELECT amount, category
     FROM transactions
     WHERE date > '2024-01-01'
     LIMIT 100

[F5 to execute]

Results> [100 rows displayed]

Next? [c]hart [e]dit [s]ave [q]uit
> c

Chart> histogram

Column: amount
Range: $12.50 - $892.00

Buckets: [a]uto [c]ustom [m]anual
> c

Ranges: 0-100, 100-200, 200-300, 300+

[Histogram displayed]

Next? [a]djust [s]ave [e]dit SQL [q]uit
> s

Chart name: spending_distribution
✓ Saved to ~/.treeline/charts/spending_distribution.tl

The analysis mode maintains your context - SQL, results, and charts -
so you can iterate freely without starting over.
```

### 2. Slash Commands Reference (`docs/external/reference/slash_commands.md`)

**Update command descriptions:**

```markdown
## Data Analysis Commands

Command | Description
--- | ---
/sql | Quick SQL editor - run queries, optionally create charts
/analysis | **Fluid analysis workspace** - iterate between SQL, results, and charts with preserved state
/chart [name] | Browse and run saved charts
/schema [table] | Browse database schema
/queries [list\|show\|delete] | Manage saved queries

### When to Use Each

- **`/sql`** - Quick one-off queries or when you just want SQL
- **`/analysis`** - Exploratory analysis, building charts, iterating on queries
- **`/chart`** - Running saved charts with fresh data
```

### 3. Create Analysis Mode Guide (`docs/external/guides/analysis_mode.md`)

New comprehensive guide:

```markdown
# Analysis Mode Guide

Analysis mode is Treeline's integrated workspace for exploratory data analysis.

## Overview

Unlike `/sql` (focused SQL editing) or `/chart` (chart browsing),
`/analysis` provides a stateful session where you can:

- Write and edit SQL
- View results
- Create and adjust charts
- Iterate freely without losing context

Think of it like a debug session in an IDE, or a Jupyter notebook in the terminal.

## Quick Start

> /analysis

You'll enter SQL mode. Write a query:

SQL> SELECT
       date_trunc('month', transaction_date) as month,
       SUM(amount) as total
     FROM transactions
     WHERE amount < 0
     GROUP BY month
     ORDER BY month

Press F5 to execute.

[Results displayed]

Next? [c]hart [e]dit [s]ave [q]uit

## Modal Navigation

Analysis mode has three sub-modes:

### SQL Mode
- Edit SQL with syntax highlighting
- Tab to load saved queries
- F5 to execute
- Type `q` to quit

### Results Mode
- View query results
- [c] create chart
- [e] edit SQL
- [s] save query

### Chart Mode
- Configure chart type and columns
- Adjust bucketing for histograms
- Save chart configs
- [e] return to SQL to tweak query

## Smart Histogram Bucketing

When creating histograms, Treeline helps with bucketing:

Chart> histogram
Column: amount
Range: $12.50 - $892.00

Buckets: [a]uto [c]ustom [m]anual
> c

Ranges: 0-100, 100-200, 200-300, 300+

Treeline transforms your query to:
- Create CASE statement for bucketing
- Group by buckets
- Count occurrences

No manual SQL required!

## Tips

1. **Use Tab liberally** - autocomplete works everywhere
2. **Type `?` in any mode** - shows keyboard shortcuts
3. **Edit → Execute loop** - `e` returns to SQL with your query preserved
4. **Save often** - both queries and charts can be saved mid-session

## Examples

### Monthly Spending Trend

> /analysis

SQL> SELECT
       date_trunc('month', date) as month,
       SUM(amount) as spending
     FROM transactions
     WHERE amount < 0
     GROUP BY month

[F5]

Results> c

Chart> line
X: month
Y: spending
Title: Monthly Spending

[Chart displayed]

> s

Chart name: monthly_spending
✓ Saved

### Distribution Analysis

> /analysis

SQL> SELECT amount
     FROM transactions
     WHERE amount > 100

[F5]

Results> c

Chart> histogram
Column: amount
Buckets: [a]uto

[Histogram displayed]

> a

Adjust> [b]uckets
Ranges: 0-200, 200-500, 500+

[Updated histogram]

> s
```

### 4. Update Help Command (`src/treeline/commands/help.py`)

Add `/analysis` with prominent positioning:

```python
table.add_row("/analysis", "Fluid workspace for SQL → Results → Charts (recommended for exploration)")
table.add_row("/sql", "Quick SQL editor for one-off queries")
table.add_row("/chart [name]", "Browse and run saved charts")
```

### 5. Internal Architecture Docs

Create `docs/internal/architecture/analysis_mode.md`:

```markdown
# Analysis Mode Architecture

## State Management

`AnalysisSession` maintains:
- SQL query (current and modified flag)
- Results (columns + rows)
- Chart config and output
- Current mode (sql, results, chart)

## Modal Navigation

Three handlers:
- `_handle_sql_mode()` - SQL editing
- `_handle_results_mode()` - Result viewing
- `_handle_chart_mode()` - Chart creation

Each handler:
1. Displays appropriate UI
2. Handles user input
3. Updates session state
4. Returns next mode/action

## Smart Helpers

`HistogramBucketingHelper`:
- Auto-generates equal-width buckets
- Parses custom bucket ranges
- Generates SQL transformations

## Dependencies

```
analysis.py
├── AnalysisSession (state)
├── SavedQueryCompleter (autocomplete)
├── ChartWizardConfig (chart config)
├── ChartColumnCompleter (autocomplete)
└── HistogramBucketingHelper (smart bucketing)
```
```

### 6. Migration Guide

Create `docs/external/guides/migration_to_analysis_mode.md`:

```markdown
# Migrating to Analysis Mode

## What Changed?

### `/sql` Command
- **Before**: Chart wizard triggered after every query
- **After**: Single action menu - choose chart, save, or edit
- **Impact**: Less friction, cleaner for SQL purists

### `/chart` Command
- **Before**: `/chart` listed charts, then required `/chart name` to run
- **After**: `/chart` enters interactive browser with Tab autocomplete
- **Impact**: Faster chart browsing and execution

### New: `/analysis` Command
- Integrated workspace for iterative analysis
- Maintains state across SQL → Results → Charts
- Recommended for exploratory work

## Should I Use `/sql` or `/analysis`?

**Use `/sql` when:**
- Quick one-off query
- You know exactly what you want
- No charting needed (or just one quick chart)

**Use `/analysis` when:**
- Exploring data iteratively
- Building charts from queries
- Tweaking SQL based on chart output
- Learning patterns in your data

## Example Migration

### Old Workflow
```bash
> /sql
> SELECT ...
Save? y
Chart? y
[wizard...]
Save chart? y
Continue? n

> /chart
Charts: monthly, weekly
> /chart monthly
[runs chart]
```

### New Workflow
```bash
> /analysis

SQL> SELECT ...
[F5]

Results> c
Chart> [configure]
> s

OR for quick check:

> /sql
> SELECT ...
Next? [c]hart [s]ave [e]dit [enter]
> [enter]  # Quick exit

> /chart
Chart: m[Tab] → monthly
[runs chart]
```

## Breaking Changes

None! All existing functionality preserved.
- Saved queries still work
- Saved charts still work
- `/sql` still works (just better UX)
- `/chart` still works (just interactive)
```

## Testing

### Create Smoke Test

Add `tests/smoke/test_analysis_mode.py`:

```python
def test_analysis_mode_full_workflow():
    """Test complete analysis workflow: SQL → Results → Chart → Save."""

def test_analysis_mode_iteration():
    """Test iterating: SQL → Chart → Edit SQL → New Chart."""

def test_analysis_mode_histogram_bucketing():
    """Test smart histogram bucketing assistance."""
```

## Acceptance Criteria

- [ ] Landing page updated with `/analysis` examples
- [ ] Slash commands reference updated
- [ ] Comprehensive analysis mode guide created
- [ ] Help command updated
- [ ] Internal architecture docs created
- [ ] Migration guide created for existing users
- [ ] Smoke test for full `/analysis` workflow
- [ ] All existing docs still accurate
- [ ] Screenshots/examples use new patterns

## Notes

- Documentation is critical for adoption
- Examples should be realistic (actual use cases)
- Migration guide reduces confusion for existing users
- Internal docs help future maintainers

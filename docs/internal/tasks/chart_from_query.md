# Chart From Query Results

Users need an easy way to create charts from query results. Currently, only the AI agent can create charts through MCP tools.

## User Story
As a user, I want to create a chart from my SQL query results so that I can visualize trends and patterns without using the AI agent.

## Current State
The only way to create charts is:
1. Use AI chat and hope it generates the right SQL and chart
2. Manually call the pyplot API in a Python script

There's no user-facing command to create charts from query results.

## Desired State
```
> /sql
SELECT
  date_trunc('month', transaction_date)::DATE as month,
  SUM(amount) as spending
FROM transactions
WHERE amount < 0
GROUP BY month
ORDER BY month

[Results displayed as table]

Create a chart? (y/n): y

Chart type? [bar/line/scatter/histogram]: line
X axis column: month
Y axis column: spending
Chart title (optional): Monthly Spending Trend
Color [green/blue/red/yellow/cyan/magenta] (default: blue):

[Chart displayed using pyplot]

Save chart config? (y/n): y
Name: monthly_spending

✓ Saved as ~/.treeline/charts/monthly_spending.tl
```

## Implementation Details

### Chart Wizard Flow
After query results are displayed:
1. Prompt: "Create a chart? (y/n)"
2. If yes, ask:
   - Chart type (bar/line/scatter/histogram)
   - X column (from query results)
   - Y column (from query results)
   - Title (optional)
   - Color (optional, default varies by chart type)
3. Validate column selections exist in results
4. Generate chart using pyplot
5. Display chart in terminal
6. Prompt to save config

### Chart Config File Format (.tl)
Store as JSON in `~/.treeline/charts/{name}.tl`:
```json
{
  "query": "SELECT date_trunc('month', transaction_date)::DATE as month...",
  "chart": {
    "type": "line",
    "x_column": "month",
    "y_column": "spending",
    "title": "Monthly Spending Trend",
    "color": "blue",
    "width": 60,
    "height": 20
  }
}
```

### Running Saved Charts
- `/chart name` - runs saved chart
- Executes the query, applies chart config, displays chart

### Technical Approach
1. Add chart prompt after query results display
2. Create chart wizard using `rich.prompt.Prompt` for inputs
3. Validate column names against query results
4. Use pyplot library to generate chart
5. Strip colors from pyplot output (using `strip_colors` utility)
6. Display chart in terminal
7. Add `/chart` command to run saved chart configs
8. Store configs as JSON in `~/.treeline/charts/`

### Supported Chart Types (Phase 1)
- **bar** - horizontal bar chart (good for categories)
- **line** - line chart (good for time series)
- **scatter** - scatter plot (good for correlations)
- **histogram** - distribution (good for value spreads)

Skip boxplot for now (has bugs per pyplot tests).

### Edge Cases
- Query returns no results (can't chart, show error)
- Query returns only one row (some charts need multiple points)
- Invalid column names (validate and show error)
- Non-numeric Y column (validate data types)
- Chart name already exists (prompt to overwrite)

## Acceptance Criteria
- [ ] After query execution, prompt "Create a chart?"
- [ ] Chart wizard guides user through configuration
- [ ] Chart displayed using pyplot in terminal
- [ ] Prompt to save chart config as `.tl` file
- [ ] `/chart name` runs saved chart
- [ ] Chart configs stored in `~/.treeline/charts/`
- [ ] Support for bar, line, scatter, histogram chart types
- [ ] Column validation against query results
- [ ] Graceful error handling for invalid configurations
- [ ] Updated `/help` to show `/chart` command
- [ ] Updated docs/external/reference/slash_commands.md
- [ ] Unit tests for chart wizard logic
- [ ] Smoke test for full workflow

## Notes
- Start simple - just basic chart types and options
- Can add more customization later (legends, annotations, etc.)
- Focus on making the wizard intuitive and fast
- The `.tl` format is human-readable JSON (users can edit)
- This unlocks the "saved chart" feature mentioned in PRFAQ

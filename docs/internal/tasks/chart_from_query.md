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
The file format should be humand readable as look somewhat similar to markdown, with a bit extra. We want these components captured in the config file format:
- the query itself
- any variables / macros. We want, in the future, to allow users to execute queries with custom inputs.
- chart configs (type, x, y column, title, colors, etc.)
- optional description

Do NOT overcomplicate this. We want the format to be easy to read for a human, and easy to parse for a machine. Make sure the parsing logic is properly isolated and abstracted according to Hexgonal and our overall architecture. For example, we probably want a new abstraction to handle the config file logic (saving and parsing), so if we want to change the underlying format later we can do so without a major refactor.

Store as JSON in `~/.treeline/charts/{name}.tl`:

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
- The `.tl` format is human-readable (users can edit)
- This unlocks the "saved chart" feature mentioned in PRFAQ
- We don't have to support multi-series line charts right now, but the implementation should consider that will be a future feature.

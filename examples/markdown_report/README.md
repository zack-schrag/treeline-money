# Markdown Spending Report

Generate a markdown-formatted spending report with text-based visualizations.

## Features

- 📊 Summary statistics (total spending, income, net savings)
- 📈 Monthly spending trends with text-based bar charts
- 🏷️ Spending breakdown by category
- 🏪 Top merchants analysis
- 📉 Month-over-month comparison

## Setup

1. Ensure you have Treeline installed and data synced:
   ```bash
   tl sync  # or tl import your_transactions.csv
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

## Usage

### Print to console

```bash
uv run python generate_report.py
```

### Save to file

```bash
uv run python generate_report.py spending_report.md
```

### Automate with cron

Add to your crontab to generate weekly reports:

```bash
# Generate report every Monday at 9am
0 9 * * 1 cd /path/to/markdown_report && uv run python generate_report.py ~/reports/spending_$(date +\%Y-\%m-\%d).md
```

## Output Example

The generated markdown includes:
- Summary statistics table
- Text-based bar charts for visual trends
- Detailed breakdowns by category and merchant
- Month-over-month spending comparison

Perfect for:
- Version controlling your spending history
- Sharing reports (without raw data)
- Tracking long-term trends
- Automated reporting workflows

# Treeline Examples

Example projects to help you get started with analyzing and visualizing your Treeline financial data.

## Available Examples

### 1. 📊 [Marimo Dashboard](./marimo_dashboard/)

An interactive web-based dashboard built with [Marimo](https://marimo.io/).

**Features:**
- Monthly spending trends
- Spending by category/tag
- Recent transactions table
- Interactive visualizations

**Quick Start:**
```bash
cd marimo_dashboard
uv sync
uv run marimo edit dashboard.py
```

Perfect for: Interactive exploration and real-time data analysis

---

### 2. 📝 [Markdown Report Generator](./markdown_report/)

Generate markdown-formatted spending reports with text-based visualizations.

**Features:**
- Summary statistics
- Monthly trends with ASCII charts
- Category and merchant breakdowns
- Month-over-month comparisons

**Quick Start:**
```bash
cd markdown_report
uv sync
uv run python generate_report.py spending_report.md
```

Perfect for: Version-controlled reports, automated workflows, sharing insights

---

### 3. 💳 [Subscription Finder](./subscription_finder/)

Automatically detect recurring charges and potential subscriptions.

**Features:**
- Identifies recurring payments
- Calculates total subscription costs
- Detects frequency patterns (monthly, yearly, etc.)
- Warns about potentially forgotten subscriptions

**Quick Start:**
```bash
cd subscription_finder
uv sync
uv run python find_subscriptions.py
```

Perfect for: Finding forgotten subscriptions, budget optimization

---

## Prerequisites

All examples require:
1. **Treeline installed and configured** with transaction data
   ```bash
   pip install treeline-money
   tl sync  # or tl import your_transactions.csv
   ```

2. **uv package manager**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

## Getting Started

Each example is a standalone project with its own dependencies:

```bash
# Navigate to any example
cd marimo_dashboard  # or markdown_report, or subscription_finder

# Install dependencies
uv sync

# Run the example (see individual READMEs for specific commands)
```

## Customization

All examples are designed to be:
- **Simple starting points** - Easy to understand and modify
- **Well-commented** - Code includes explanations
- **Extensible** - Add your own features and visualizations

Feel free to:
- Modify SQL queries to focus on different time periods or accounts
- Add new visualizations or metrics
- Combine multiple examples
- Use as templates for your own projects

## More Ideas

Looking for more inspiration? Here are additional ideas:

- **ML Auto-Tagger**: Train a model on your tagged data to auto-categorize new transactions
- **Budget Tracker**: Set budgets per category and track against actual spending
- **Streamlit Dashboard**: Alternative to Marimo with different visualization options
- **Cash Flow Forecasting**: Predict future balances based on historical patterns
- **Expense Anomaly Detection**: Flag unusual spending patterns
- **Multi-Account Net Worth Tracker**: Visualize total net worth across all accounts

## Contributing

Have you built something cool with Treeline? Consider contributing it as an example!

1. Create a new directory in `examples/`
2. Set it up as a standalone uv project
3. Include a detailed README
4. Submit a PR

## Questions?

- Check the [main Treeline documentation](../README.md)
- File an issue on [GitHub](https://github.com/zack-schrag/treeline-money/issues)
- Start a discussion in [GitHub Discussions](https://github.com/zack-schrag/treeline-money/discussions)

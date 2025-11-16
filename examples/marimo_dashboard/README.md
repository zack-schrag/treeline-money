# Marimo Spending Dashboard

An interactive dashboard to visualize your Treeline spending data using [Marimo](https://marimo.io/).

## Features

- 📊 Monthly spending trends
- 🏷️ Spending by category/tag
- 📋 Recent transactions table
- 💡 Summary statistics

## Setup

1. Ensure you have Treeline installed and data synced:
   ```bash
   tl sync  # or tl import your_transactions.csv
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Run the dashboard:
   ```bash
   uv run marimo edit dashboard.py
   ```

This will open the interactive dashboard in your browser.

## Customization

The dashboard is built with Marimo, which means you can:
- Edit the code directly in the browser
- Add new visualizations
- Modify SQL queries to analyze different aspects of your spending
- Save your changes and they'll persist

Each cell in the notebook is reactive - when you change one cell, dependent cells automatically update!

## Tips

- Use `tl tag` to categorize your transactions for better insights
- The dashboard only shows spending (negative amounts) by default
- You can modify the SQL queries in the code to include income or filter by date ranges

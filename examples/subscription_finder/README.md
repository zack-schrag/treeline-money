# Subscription Finder

Automatically detect recurring charges and potential subscriptions in your transaction data.

## Features

- 🔍 Detects recurring charges based on merchant and amount patterns
- 📅 Identifies frequency (monthly, quarterly, yearly, weekly, or custom)
- 💰 Calculates total monthly and yearly subscription costs
- ⚠️ Highlights potentially cancelled subscriptions (not seen in 60+ days)
- 🎨 Beautiful terminal output with Rich formatting

## How It Works

The script analyzes your transactions to find:
1. **Recurring merchants**: Charges from the same merchant appearing multiple times
2. **Similar amounts**: Transactions within 5% of the median amount
3. **Regular intervals**: Charges that occur on a predictable schedule

Detection parameters:
- Minimum 3 occurrences required
- 5% tolerance for amount variation
- Automatically categorizes frequency based on interval patterns

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

```bash
uv run python find_subscriptions.py
```

## Example Output

```
╭──────────── 💳 Subscription Summary ────────────╮
│                                                  │
│ Detected Subscriptions: 8                       │
│ Total Monthly Cost: $127.43                     │
│ Total Yearly Cost: $1,529.16                    │
│                                                  │
╰──────────────────────────────────────────────────╯

╭────────────────── Recurring Charges ──────────────────╮
│ Merchant      │ Amount  │ Frequency │ Monthly Cost │  │
│ Netflix       │ $15.99  │ Monthly   │ $15.99       │  │
│ Spotify       │ $9.99   │ Monthly   │ $9.99        │  │
│ Amazon Prime  │ $14.99  │ Monthly   │ $14.99       │  │
╰────────────────────────────────────────────────────────╯
```

## Customization

Edit the detection parameters in `find_subscriptions.py`:

```python
subscriptions = find_recurring_transactions(
    conn,
    min_occurrences=3,      # Minimum times it must appear
    amount_tolerance=0.05   # 5% amount variation allowed
)
```

## Use Cases

- Find forgotten subscriptions you're still paying for
- Calculate total subscription spending
- Identify subscriptions that may have been cancelled
- Track subscription price changes over time
- Budget planning for recurring expenses

## Tips

- Run monthly to stay on top of subscription changes
- Review charges marked as "potentially cancelled" - they might be annual renewals
- Compare detected subscriptions against your known subscriptions to find surprises
- Use this as part of your regular financial review process

# Demo Mode

Demo mode lets you test Treeline with realistic fake data without connecting to real banks. Perfect for:
- Learning how Treeline works
- Testing and development
- Demos and presentations
- CI/CD testing

## Quick Start

```bash
# Enable demo mode
export TREELINE_DEMO_MODE=true

# Load demo data
tl sync

# Start exploring
tl status
tl query "SELECT * FROM transactions LIMIT 10"
tl tag
```

## How It Works

When `TREELINE_DEMO_MODE=true`:

1. **Mock data providers** - All integrations return fake data instead of real API calls
2. **No real credentials needed** - Setup commands accept any value
3. **Realistic test data**:
   - 3 demo accounts (checking, savings, credit card)
   - 18 transactions across various categories
   - Realistic balances and descriptions

## Demo Data

### Accounts

- **Demo Checking Account** - Demo Bank
- **Demo Savings Account** - Demo Bank
- **Demo Credit Card** - Demo Credit Union

### Sample Transactions

The demo data includes transactions across categories:
- Groceries (Whole Foods, Target)
- Coffee (Starbucks)
- Transportation (Shell Gas, Uber)
- Entertainment (Netflix, Spotify)
- Travel (Delta Airlines, Hilton Hotel)
- Shopping (Amazon, Apple Store)
- Income (Payroll deposits, interest)

## Usage

### One-time Commands

Prefix any command with the environment variable:

```bash
TREELINE_DEMO_MODE=true tl sync
TREELINE_DEMO_MODE=true tl status
TREELINE_DEMO_MODE=true tl query "SELECT * FROM transactions"
```

### Persistent Demo Mode

Add to your shell profile or `.env` file:

```bash
# In ~/.zshrc or ~/.bashrc
export TREELINE_DEMO_MODE=true
```

Or create `.env` in your project:

```
TREELINE_DEMO_MODE=true
```

Then run commands normally:

```bash
tl sync
tl status
tl query "SELECT * FROM accounts"
```

## Setup with Demo Mode

You can still run setup commands in demo mode:

```bash
export TREELINE_DEMO_MODE=true

# This will accept any token
tl setup simplefin
# Enter any value when prompted, e.g., "demo-token"

# Sync will return demo data
tl sync
```

## Disable Demo Mode

```bash
unset TREELINE_DEMO_MODE
# or
export TREELINE_DEMO_MODE=false
```

## Notes

- Demo mode only affects data sync - database operations work normally
- Demo transactions use `"demo"` as the external ID key
- You can switch between demo and real data by toggling the environment variable
- Demo data is static - the same 18 transactions load each time

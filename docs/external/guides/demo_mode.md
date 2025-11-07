# Demo Mode

Demo mode allows you to test Treeline with realistic fake financial data without connecting to real financial institutions. This is useful for:
- Testing and development
- Demos and presentations
- Learning how Treeline works without real data
- CI/CD testing

## Enabling Demo Mode

Set the `TREELINE_DEMO_MODE` environment variable to `true`:

```bash
export TREELINE_DEMO_MODE=true
```

Or add it to your `.env` file:

```
TREELINE_DEMO_MODE=true
```

## How Demo Mode Works

When demo mode is enabled:

1. **All data providers return mock data** - SimpleFIN, CSV imports, and any future integrations will return fake data instead of making real API calls
2. **No real credentials needed** - Setup commands accept any token/credentials
3. **Realistic test data** - Demo mode provides:
   - 3 demo accounts (checking, savings, credit card)
   - ~18 transactions across different categories
   - Realistic balances and transaction descriptions

## Using Demo Mode

### 1. Enable demo mode
```bash
export TREELINE_DEMO_MODE=true
```

### 2. Initialize and authenticate
You still need to authenticate (demo mode doesn't affect auth):
```bash
treeline login --create-account
```

### 3. Set up an integration
In demo mode, you can set up any integration with fake credentials:
```bash
treeline setup simplefin
# Enter any token when prompted (e.g., "demo-token")
```

### 4. Sync data
The sync command will use mock data instead of real API calls:
```bash
treeline sync
```

### 5. View and query data
All other commands work normally with the demo data:
```bash
treeline status
treeline query "SELECT * FROM transactions LIMIT 10"
treeline tag
```

## Demo Data Details

### Demo Accounts
- **Demo Checking Account** - $3,247.85
- **Demo Savings Account** - $15,420.50
- **Demo Credit Card** - -$842.32 (balance owed)

### Demo Transactions
Includes realistic transactions across categories:
- Groceries (QFC, Whole Foods, Target)
- Coffee (Starbucks)
- Transportation (Shell Gas, Uber)
- Entertainment (Netflix, Spotify)
- Travel (Delta Airlines, Hilton Hotel)
- Utilities (PG&E)
- Shopping (Amazon, Apple Store)
- Income (Payroll deposits, interest payments)

## Disabling Demo Mode

Remove or set the environment variable to `false`:

```bash
unset TREELINE_DEMO_MODE
# or
export TREELINE_DEMO_MODE=false
```

## Notes

- Demo mode only affects data sync - authentication and database operations work normally
- All demo data uses the external ID key `"demo"` instead of provider-specific keys like `"simplefin"`
- Demo transactions are spread evenly across the sync date range
- You can use demo mode alongside real data by switching the environment variable

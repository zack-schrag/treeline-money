# Auto-Taggers

Auto-taggers allow you to automatically apply tags to transactions during sync based on custom Python rules.

## Quick Start

### 1. Create a new tagger

```bash
treeline new tagger groceries
```

This creates `~/.treeline/taggers/groceries.py` with a skeleton template.

### 2. Edit the tagger

Open the file and add your tagging logic:

```python
from treeline.domain import Transaction
from treeline.ext import tagger


@tagger
def groceries(transaction: Transaction) -> list[str]:
    """Auto-tag grocery store purchases."""
    stores = ['WHOLE FOODS', 'SAFEWAY', 'TRADER JOE']
    if any(store in transaction.description.upper() for store in stores):
        return ['groceries', 'food']
    return []
```

### 3. Sync transactions

The next time you run `treeline sync`, your tagger will automatically apply tags to new transactions.

```bash
treeline sync
```

You'll see stats about tags applied:

```
✓ Transaction breakdown:
    Discovered: 150
    New: 45
    Skipped: 105 (already exists)
✓ Auto-tagging applied:
    groceries: 12 tag(s)
```

## Commands

### Create a tagger

```bash
treeline new tagger <name>
```

Creates a new tagger file at `~/.treeline/taggers/<name>.py`.

Tagger names must be valid Python identifiers (letters, numbers, underscores only, cannot start with a number).

### List taggers

```bash
treeline list taggers
```

Shows all installed taggers and the functions they contain.

## Writing Taggers

### Basic Structure

```python
from treeline.domain import Transaction
from treeline.ext import tagger


@tagger
def my_tagger(transaction: Transaction) -> list[str]:
    """Describe what this tagger does."""
    # Your logic here
    if some_condition:
        return ['tag1', 'tag2']
    return []
```

### Multiple Taggers

You can have multiple `@tagger` functions in a single file, or create multiple files. All taggers run in sequence.

```python
@tagger
def tag_groceries(transaction: Transaction) -> list[str]:
    if 'WHOLE FOODS' in transaction.description.upper():
        return ['groceries']
    return []


@tagger
def tag_large_purchases(transaction: Transaction) -> list[str]:
    if abs(transaction.amount) > 500:
        return ['large-purchase', 'review']
    return []
```

### Available Transaction Fields

- `transaction.description` - Transaction description (str | None)
- `transaction.amount` - Transaction amount (Decimal)
- `transaction.transaction_date` - Transaction date (date)
- `transaction.posted_date` - Posted date (date)
- `transaction.account_id` - Account UUID
- `transaction.tags` - Existing tags (tuple[str, ...])

### Example Taggers

#### Categorize by merchant

```python
@tagger
def categorize_by_merchant(transaction: Transaction) -> list[str]:
    """Categorize transactions by merchant name."""
    desc = transaction.description.upper() if transaction.description else ""

    categories = {
        'AMAZON': ['shopping', 'online'],
        'NETFLIX': ['entertainment', 'subscription'],
        'SPOTIFY': ['entertainment', 'subscription', 'music'],
        'SHELL': ['transportation', 'gas'],
        'UBER': ['transportation', 'rideshare'],
    }

    for merchant, tags in categories.items():
        if merchant in desc:
            return tags

    return []
```

#### Flag large purchases

```python
@tagger
def flag_large_purchases(transaction: Transaction) -> list[str]:
    """Flag purchases over $500 for review."""
    if abs(transaction.amount) > 500:
        return ['large-purchase', 'review']
    return []
```

#### Regex matching

```python
import re

@tagger
def extract_ticket_number(transaction: Transaction) -> list[str]:
    """Extract ticket numbers from descriptions."""
    if not transaction.description:
        return []

    # Match patterns like "TICKET #12345"
    match = re.search(r'TICKET\s*#?(\d+)', transaction.description.upper())
    if match:
        return [f'ticket-{match.group(1)}']

    return []
```

## How It Works

1. **During Sync**: When `treeline sync` runs, it loads all tagger files from `~/.treeline/taggers/`
2. **New Transactions Only**: Taggers only run on new transactions, not existing ones (to preserve user-added tags)
3. **Error Handling**: If a tagger fails, sync continues and other taggers still run
4. **Tag Deduplication**: The Transaction model automatically deduplicates tags, so multiple taggers can safely return the same tag

## Tips

- **Keep it simple**: Taggers should be fast and simple - they run on every new transaction
- **No external dependencies**: Stick to Python stdlib to avoid complexity
- **Test incrementally**: Create a tagger, run a small sync, verify it works
- **Use multiple taggers**: Better to have several focused taggers than one complex one
- **Existing tags are preserved**: Taggers add tags but don't remove existing ones

## Troubleshooting

### Tagger not running

1. Check the file is in `~/.treeline/taggers/` and ends with `.py`
2. Check the filename doesn't start with `_` (those are skipped)
3. Verify you have `@tagger` decorator on your function
4. Run `treeline list taggers` to see if it's loaded

### Tags not appearing

1. Taggers only run on **new** transactions, not existing ones
2. Check your tagger logic is returning tags (add debug prints if needed)
3. Verify the condition is matching (check `transaction.description` value)

### Tagger errors

Check the sync output for warnings like:
```
Warning: Failed to load tagger groceries.py: <error message>
```

Fix the error and run sync again.

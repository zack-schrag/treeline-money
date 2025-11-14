# Auto-Taggers

Auto-taggers automatically apply tags to transactions based on custom Python rules. They run during sync for new transactions, or can be applied to existing transactions with backfill.

## Quick Start

```bash
# 1. Create a tagger
treeline new tagger groceries

# 2. Edit ~/.treeline/taggers/groceries.py with your rules

# 3. Sync to auto-tag new transactions
treeline sync

# 4. Apply to existing transactions (optional)
treeline backfill tags
```

## Writing Taggers

### Basic Structure

Create a Python file in `~/.treeline/taggers/` with functions that start with `tag_`:

```python
def tag_groceries(description, **kwargs):
    """Tag grocery store purchases."""
    if not description:
        return []

    stores = ['WHOLE FOODS', 'SAFEWAY', 'TRADER JOE']
    desc_upper = description.upper()

    if any(store in desc_upper for store in stores):
        return ['groceries', 'food']

    return []
```

**Key points:**
- Function name MUST start with `tag_` prefix (like pytest's `test_` convention)
- Return a list of tags to apply (or empty list for no tags)
- All transaction data is passed as function parameters

### Available Parameters

Your tagger function receives these parameters:

**Main parameters:**
- `description` - Transaction description (str | None)
- `amount` - Transaction amount (Decimal)
- `transaction_date` - Date of transaction (date)
- `account_id` - Account UUID

**Additional (via `**kwargs`):**
- `posted_date` - Posted date (date)
- `tags` - Existing tags (tuple[str, ...])
- `id` - Transaction UUID
- `external_ids` - External IDs (dict)
- `created_at` - Creation timestamp (datetime)
- `updated_at` - Update timestamp (datetime)

### Example Taggers

#### Categorize by merchant

```python
def tag_merchants(description, **kwargs):
    """Categorize by merchant name."""
    if not description:
        return []

    desc = description.upper()

    if 'AMAZON' in desc:
        return ['shopping', 'online']
    if 'NETFLIX' in desc or 'SPOTIFY' in desc:
        return ['entertainment', 'subscription']
    if 'SHELL' in desc or 'CHEVRON' in desc:
        return ['transportation', 'gas']

    return []
```

#### Flag large purchases

```python
def tag_large_purchases(amount, **kwargs):
    """Flag purchases over $500."""
    if abs(amount) > 500:
        return ['large-purchase', 'review']
    return []
```

#### Time-based tagging

```python
def tag_weekend_spending(transaction_date, amount, **kwargs):
    """Tag weekend purchases."""
    if transaction_date.weekday() >= 5:  # Saturday=5, Sunday=6
        if amount < 0:  # Spending, not income
            return ['weekend']
    return []
```

#### Regex matching

```python
import re

def tag_ticket_numbers(description, **kwargs):
    """Extract ticket numbers from descriptions."""
    if not description:
        return []

    # Match patterns like "TICKET #12345"
    match = re.search(r'TICKET\s*#?(\d+)', description.upper())
    if match:
        return [f'ticket-{match.group(1)}']

    return []
```

#### Multiple taggers in one file

```python
def tag_groceries(description, **kwargs):
    """Tag grocery stores."""
    if not description:
        return []
    if any(s in description.upper() for s in ['WHOLE FOODS', 'SAFEWAY']):
        return ['groceries']
    return []


def tag_coffee(description, **kwargs):
    """Tag coffee purchases."""
    if not description:
        return []
    if 'STARBUCKS' in description.upper():
        return ['coffee', 'dining']
    return []
```

## Commands

### Create a tagger

```bash
treeline new tagger <name>
```

Creates `~/.treeline/taggers/<name>.py` with a template.

Tagger names must be valid Python identifiers (letters, numbers, underscores only).

### List taggers

```bash
treeline list taggers
```

Shows all installed taggers and their functions.

### Backfill existing transactions

Apply taggers to transactions that already exist:

```bash
# Apply all taggers to all transactions
treeline backfill tags

# Preview changes without saving
treeline backfill tags --dry-run -v

# Apply specific tagger
treeline backfill tags --tagger groceries.tag_stores

# Apply all taggers from a file
treeline backfill tags --tagger groceries
```

## How It Works

### During Sync

1. `treeline sync` loads all taggers from `~/.treeline/taggers/`
2. Taggers run ONLY on new transactions (to preserve manual tags)
3. Tags are added to transactions before saving
4. Sync output shows tag statistics

### Manual Backfill

1. `treeline backfill tags` applies taggers to existing transactions
2. Runs on ALL transactions (or filtered subset)
3. Tags are additive - existing tags are kept
4. Use `--dry-run` to preview changes

### Error Handling

- If a tagger fails, sync/backfill continues
- Other taggers still run
- Errors are logged but don't stop the process

### Tag Deduplication

The Transaction model automatically deduplicates tags, so multiple taggers can safely return the same tag.

## Tips

- **Keep taggers simple** - They run on every transaction
- **No external dependencies** - Stick to Python stdlib
- **Test with dry-run** - Use `--dry-run -v` to preview
- **Use multiple taggers** - Better to have focused taggers than one complex one
- **Tags are additive** - Taggers add tags but never remove them

## Troubleshooting

### Tagger not discovered

1. Check file is in `~/.treeline/taggers/` and ends with `.py`
2. Check filename doesn't start with `_` (skipped by convention)
3. Verify function name starts with `tag_` prefix
4. Run `treeline list taggers` to see loaded taggers

### Tags not appearing

1. Taggers only run on **new** transactions during sync
2. Use `treeline backfill tags` for existing transactions
3. Check tagger logic returns non-empty list
4. Use `--verbose` flag to see tagging details

### Viewing tagger output

```bash
# See detailed tagging during sync
treeline sync --verbose

# Preview backfill with details
treeline backfill tags --dry-run --verbose
```

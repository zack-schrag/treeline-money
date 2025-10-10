# Smart Histogram Bucketing Helper

## Problem

Creating histogram charts requires manual SQL transformation for bucketing. For example, to bucket transaction amounts into ranges like "0-100, 100-200, 200-300", users must write:

```sql
WITH bucketed AS (
  SELECT
    CASE
      WHEN amount < 100 THEN '0-100'
      WHEN amount < 200 THEN '100-200'
      WHEN amount < 300 THEN '200-300'
      ELSE '300+'
    END as bucket
  FROM (original query)
)
SELECT bucket, COUNT(*) as count
FROM bucketed
GROUP BY bucket
```

This is tedious and error-prone. We should help users create histograms with simple prompts.

## Solution

When user selects histogram chart type, provide intelligent bucketing assistance:

```bash
Chart type: histogram

Column: amount
✓ Detected numeric column
  Range: $45.67 - $892.50

Bucketing:
  [a]uto (10 equal buckets)
  [c]ustom ranges
  [m]anual SQL (advanced)
> c

Enter ranges (e.g., 0-100, 100-200, 300+): 0-100, 100-200, 200-300, 300-500, 500+

✓ Will transform your query to create buckets

Preview SQL? [y/n]: y

[Shows the transformed SQL]

Continue? [y/n]: y

[Generates and displays histogram]
```

## Implementation Details

### Create `histogram_helper.py`

```python
"""Helper for creating histogram charts with bucketing."""

from dataclasses import dataclass
from typing import Any


@dataclass
class BucketRange:
    """Represents a histogram bucket range."""

    label: str
    min_value: float | None  # None for unbounded start
    max_value: float | None  # None for unbounded end

    def contains(self, value: float) -> bool:
        """Check if value falls in this bucket."""
        if self.min_value is not None and value < self.min_value:
            return False
        if self.max_value is not None and value >= self.max_value:
            return False
        return True


class HistogramBucketingHelper:
    """Helps users bucket numeric data for histograms."""

    def calculate_range(self, values: list[float]) -> tuple[float, float]:
        """Calculate min and max from values."""
        return min(values), max(values)

    def generate_auto_buckets(
        self,
        min_val: float,
        max_val: float,
        num_buckets: int = 10
    ) -> list[BucketRange]:
        """Generate equal-width buckets automatically."""
        width = (max_val - min_val) / num_buckets
        buckets = []

        for i in range(num_buckets):
            bucket_min = min_val + (i * width)
            bucket_max = min_val + ((i + 1) * width)

            # Format label based on values
            if bucket_max - bucket_min >= 100:
                label = f"{int(bucket_min)}-{int(bucket_max)}"
            else:
                label = f"{bucket_min:.2f}-{bucket_max:.2f}"

            buckets.append(BucketRange(
                label=label,
                min_value=bucket_min,
                max_value=bucket_max
            ))

        return buckets

    def parse_custom_buckets(self, input_str: str) -> list[BucketRange]:
        """Parse user input like '0-100, 100-200, 200-300, 300+'.

        Args:
            input_str: Comma-separated ranges

        Returns:
            List of BucketRange objects

        Raises:
            ValueError: If input format is invalid
        """
        ranges = [r.strip() for r in input_str.split(',')]
        buckets = []

        for range_str in ranges:
            if '+' in range_str:
                # Open-ended upper bound: "500+"
                min_str = range_str.replace('+', '').strip()
                buckets.append(BucketRange(
                    label=range_str,
                    min_value=float(min_str),
                    max_value=None
                ))
            elif '-' in range_str:
                # Standard range: "0-100"
                parts = range_str.split('-')
                if len(parts) != 2:
                    raise ValueError(f"Invalid range format: {range_str}")

                min_val = float(parts[0].strip())
                max_val = float(parts[1].strip())

                buckets.append(BucketRange(
                    label=range_str,
                    min_value=min_val,
                    max_value=max_val
                ))
            else:
                raise ValueError(f"Invalid range format: {range_str}")

        return buckets

    def generate_bucketing_sql(
        self,
        original_sql: str,
        column: str,
        buckets: list[BucketRange]
    ) -> str:
        """Generate SQL that buckets data from original query.

        Args:
            original_sql: The user's original query
            column: Column name to bucket
            buckets: List of bucket ranges

        Returns:
            Transformed SQL with bucketing logic
        """
        # Build CASE statement
        case_clauses = []
        for bucket in buckets:
            if bucket.min_value is None:
                # Unbounded start
                condition = f"{column} < {bucket.max_value}"
            elif bucket.max_value is None:
                # Unbounded end
                condition = f"{column} >= {bucket.min_value}"
            else:
                # Standard range
                condition = f"{column} >= {bucket.min_value} AND {column} < {bucket.max_value}"

            case_clauses.append(f"      WHEN {condition} THEN '{bucket.label}'")

        case_statement = "\n".join(case_clauses)

        return f"""WITH bucketed AS (
  SELECT
    CASE
{case_statement}
    END as bucket
  FROM (
    {original_sql}
  ) original
)
SELECT
  bucket,
  COUNT(*) as count
FROM bucketed
WHERE bucket IS NOT NULL
GROUP BY bucket
ORDER BY bucket"""


def prompt_histogram_bucketing(
    helper: HistogramBucketingHelper,
    original_sql: str,
    column: str,
    values: list[float]
) -> tuple[str, list[BucketRange]] | None:
    """Interactive prompt for histogram bucketing.

    Args:
        helper: HistogramBucketingHelper instance
        original_sql: User's original query
        column: Column to bucket
        values: Sample values from column

    Returns:
        Tuple of (transformed_sql, buckets) or None if cancelled
    """
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.syntax import Syntax
    from treeline.theme import get_theme

    console = Console()
    theme = get_theme()

    # Calculate range
    min_val, max_val = helper.calculate_range(values)

    console.print(f"\n[{theme.success}]✓[/{theme.success}] Detected numeric column")
    console.print(f"  Range: {min_val:.2f} - {max_val:.2f}\n")

    # Ask bucketing strategy
    strategy = Prompt.ask(
        f"[{theme.info}]Bucketing[/{theme.info}]",
        choices=["a", "c", "m"],
        default="a",
        show_choices=False
    )

    console.print(f"[{theme.muted}]  [a]uto [c]ustom [m]anual[/{theme.muted}]\n")

    if strategy == "m":
        # Manual SQL - return None to let user write it
        console.print(f"[{theme.muted}]You'll need to write the bucketing SQL yourself.[/{theme.muted}]\n")
        return None

    # Generate or parse buckets
    if strategy == "a":
        buckets = helper.generate_auto_buckets(min_val, max_val)
    else:  # strategy == "c"
        while True:
            try:
                ranges_input = Prompt.ask(
                    f"[{theme.info}]Enter ranges (e.g., 0-100, 100-200, 300+)[/{theme.info}]"
                )
                buckets = helper.parse_custom_buckets(ranges_input)
                break
            except ValueError as e:
                console.print(f"[{theme.error}]{e}[/{theme.error}]")
                console.print(f"[{theme.muted}]Try again or press Ctrl+C to cancel[/{theme.muted}]")

    # Generate SQL
    bucketed_sql = helper.generate_bucketing_sql(original_sql, column, buckets)

    # Preview SQL
    console.print(f"\n[{theme.success}]✓[/{theme.success}] Generated bucketing SQL\n")
    show_preview = Confirm.ask(f"[{theme.info}]Preview SQL?[/{theme.info}]", default=False)

    if show_preview:
        syntax = Syntax(bucketed_sql, "sql", theme="monokai", line_numbers=False)
        console.print(syntax)
        console.print()

    # Confirm
    if not Confirm.ask(f"[{theme.info}]Continue?[/{theme.info}]", default=True):
        return None

    return bucketed_sql, buckets
```

### Integration into Chart Wizard

Update `chart_wizard.py` to detect histogram and offer bucketing:

```python
def _prompt_chart_wizard(sql: str, columns: list[str], rows: list[list]) -> None:
    # ... existing code ...

    if chart_type == "histogram":
        # Check if column is numeric
        x_idx = columns.index(x_column)
        values = [row[x_idx] for row in rows]

        # Offer bucketing assistance
        helper = HistogramBucketingHelper()
        result = prompt_histogram_bucketing(helper, sql, x_column, values)

        if result:
            bucketed_sql, buckets = result
            # Execute the bucketed SQL instead
            # ... generate chart from bucketed results ...
        else:
            # User chose manual or cancelled
            # Use original query
            # ...
```

## Testing

### Unit Tests

Create `tests/unit/commands/test_histogram_helper.py`:

```python
def test_calculate_range():
    """Test range calculation from values."""

def test_generate_auto_buckets():
    """Test automatic bucket generation."""

def test_parse_custom_buckets_standard_ranges():
    """Test parsing '0-100, 100-200' format."""

def test_parse_custom_buckets_open_ended():
    """Test parsing '500+' format."""

def test_parse_custom_buckets_invalid_format():
    """Test error handling for bad input."""

def test_generate_bucketing_sql():
    """Test SQL generation for bucketing."""

def test_bucket_range_contains():
    """Test BucketRange.contains() logic."""
```

## Acceptance Criteria

- [ ] HistogramBucketingHelper class created
- [ ] Auto bucketing generates equal-width buckets
- [ ] Custom bucketing parses user input (e.g., "0-100, 100-200, 300+")
- [ ] SQL generation creates proper CASE statement
- [ ] Integration with chart wizard for histogram type
- [ ] User can choose: auto, custom, or manual SQL
- [ ] SQL preview shows transformed query
- [ ] Unit tests for all bucketing logic
- [ ] Works with both integer and decimal ranges

## Notes

- This is a high-value feature that removes a major friction point
- Can be extended later for other smart helpers (e.g., time bucketing for line charts)
- Isolated in its own module for clean separation

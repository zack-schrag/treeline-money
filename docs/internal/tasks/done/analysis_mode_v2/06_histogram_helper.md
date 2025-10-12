# Task 06: Histogram Bucketing Helper

**Status:** Not Started
**Dependencies:** Task 05
**Estimated Time:** 2 hours

## Objective

Add smart histogram bucketing to automatically transform SQL for histogram charts.

## Requirements

1. Detect when user wants histogram of numeric column
2. Auto-suggest bucket ranges based on data distribution
3. Allow custom bucket ranges (e.g., "0-100, 100-200, 200+")
4. Transform original SQL to include bucketing CASE statement
5. Execute transformed SQL and display histogram

## Implementation

**Service layer:** `src/treeline/app/histogram_service.py`

```python
def suggest_buckets(values: list[float], num_buckets: int = 5) -> list[tuple[float, float]]:
    """Auto-generate sensible bucket ranges."""

def parse_custom_buckets(input: str) -> list[tuple[float, float]]:
    """Parse '0-100, 100-200, 200+' format."""

def transform_sql_for_histogram(
    original_sql: str,
    column: str,
    buckets: list[tuple[float, float]]
) -> str:
    """Add CASE WHEN bucketing to SQL."""
```

## Architecture Notes

- **Service layer** handles bucket calculation and SQL transformation
- **CLI layer** handles user input and display
- No database-specific logic in abstractions

## Acceptance Criteria

- [ ] Auto-suggest buckets from data
- [ ] Parse custom bucket syntax
- [ ] Transform SQL correctly
- [ ] Execute and display histogram
- [ ] Unit tests for bucket logic
- [ ] Architecture review passes

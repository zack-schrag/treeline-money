"""Data scaling and transformation utilities."""

from typing import List, Tuple


def scale_values(
    values: List[float],
    target_min: float = 0.0,
    target_max: float = 1.0,
    value_min: float | None = None,
    value_max: float | None = None,
) -> List[float]:
    """Scale values to a target range.

    Args:
        values: Values to scale
        target_min: Minimum value of target range
        target_max: Maximum value of target range
        value_min: Minimum value in input (if None, computed from values)
        value_max: Maximum value in input (if None, computed from values)

    Returns:
        Scaled values in target range
    """
    if not values:
        return []

    if value_min is None:
        value_min = min(values)
    if value_max is None:
        value_max = max(values)

    # Handle case where all values are the same
    if value_max == value_min:
        return [target_min] * len(values)

    value_range = value_max - value_min
    target_range = target_max - target_min

    return [
        ((v - value_min) / value_range) * target_range + target_min
        for v in values
    ]


def get_axis_range(values: List[float], padding: float = 0.1) -> Tuple[float, float]:
    """Get axis range with padding.

    Args:
        values: Data values
        padding: Padding as fraction of range (0.1 = 10% padding)

    Returns:
        Tuple of (min, max) for axis range
    """
    if not values:
        return (0.0, 1.0)

    min_val = min(values)
    max_val = max(values)

    if min_val == max_val:
        # Add default padding if all values are the same
        return (min_val - 1, max_val + 1)

    range_val = max_val - min_val
    pad = range_val * padding

    return (min_val - pad, max_val + pad)


def compute_bins(values: List[float], n_bins: int = 10) -> Tuple[List[float], List[int]]:
    """Compute histogram bins and counts.

    Args:
        values: Data values to bin
        n_bins: Number of bins

    Returns:
        Tuple of (bin_edges, counts)
    """
    if not values:
        return ([], [])

    min_val = min(values)
    max_val = max(values)

    # Handle single value case
    if min_val == max_val:
        return ([min_val, min_val + 1], [len(values)])

    bin_width = (max_val - min_val) / n_bins
    bin_edges = [min_val + i * bin_width for i in range(n_bins + 1)]

    # Count values in each bin
    counts = [0] * n_bins
    for value in values:
        # Find which bin this value belongs to
        bin_idx = int((value - min_val) / bin_width)
        # Handle edge case where value == max_val
        if bin_idx >= n_bins:
            bin_idx = n_bins - 1
        counts[bin_idx] += 1

    return (bin_edges, counts)


def format_number(value: float, precision: int = 2) -> str:
    """Format number for display.

    Args:
        value: Number to format
        precision: Decimal precision

    Returns:
        Formatted string
    """
    if abs(value) >= 1000000:
        return f"{value / 1000000:.{precision}f}M"
    elif abs(value) >= 1000:
        return f"{value / 1000:.{precision}f}K"
    elif abs(value) < 0.01 and value != 0:
        return f"{value:.{precision}e}"
    else:
        return f"{value:.{precision}f}"

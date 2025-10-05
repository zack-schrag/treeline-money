"""Tests for amount formatting in CLI displays."""


def format_amount_with_sign(amount: float) -> str:
    """Format amount with proper dollar sign placement.

    Args:
        amount: The transaction amount

    Returns:
        Formatted string like "-$95.14" or "$23.50"
    """
    if amount < 0:
        return f"-${abs(amount):.2f}"
    else:
        return f"${amount:.2f}"


def test_format_negative_amount():
    """Test that negative amounts show as -$XX.XX not $-XX.XX."""
    result = format_amount_with_sign(-95.14)
    assert result == "-$95.14"


def test_format_positive_amount():
    """Test that positive amounts show as $XX.XX."""
    result = format_amount_with_sign(23.50)
    assert result == "$23.50"


def test_format_zero_amount():
    """Test that zero amounts show as $0.00."""
    result = format_amount_with_sign(0.00)
    assert result == "$0.00"

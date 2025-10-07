"""Unit tests for theme system."""

import json
import pytest
from pathlib import Path
from treeline.theme import Theme, get_theme, set_theme


def test_theme_loads_default():
    """Test that default theme loads successfully."""
    theme = Theme.load("default")
    assert theme.name == "Treeline Default (Dark)"
    assert theme.description != ""


def test_theme_has_required_colors():
    """Test that theme has all required color properties."""
    theme = Theme.load("default")

    # Basic colors
    assert theme.primary
    assert theme.success
    assert theme.error
    assert theme.warning
    assert theme.info
    assert theme.muted
    assert theme.emphasis

    # Money colors
    assert theme.positive_amount
    assert theme.negative_amount

    # UI colors
    assert theme.ui_header
    assert theme.ui_label
    assert theme.ui_selected


def test_theme_load_nonexistent_fails():
    """Test that loading a nonexistent theme raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        Theme.load("nonexistent_theme")


def test_get_theme_returns_default():
    """Test that get_theme() returns default theme."""
    theme = get_theme()
    assert theme.name == "Treeline Default (Dark)"


def test_theme_colors_are_strings():
    """Test that all theme colors are strings (Rich markup)."""
    theme = Theme.load("default")

    # Test a sample of color properties
    assert isinstance(theme.primary, str)
    assert isinstance(theme.error, str)
    assert isinstance(theme.success, str)
    assert isinstance(theme.ui_header, str)

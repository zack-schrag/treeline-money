"""Tests for CLI functions."""

from pathlib import Path

from treeline.cli import get_treeline_dir


def test_get_treeline_dir_returns_home_directory() -> None:
    """Test that get_treeline_dir returns ~/.treeline directory."""
    expected = Path.home() / ".treeline"
    actual = get_treeline_dir()
    assert actual == expected

"""Unit tests for REPL autocomplete functionality."""

import pytest


def test_get_slash_command_completions_with_slash():
    """Test that typing '/' returns all slash commands."""
    from treeline.cli import get_slash_command_completions

    completions = get_slash_command_completions("/")

    # Should return all slash commands
    assert "/help" in completions
    assert "/login" in completions
    assert "/status" in completions
    assert "/simplefin" in completions
    assert "/sync" in completions
    assert "/import" in completions
    assert "/tag" in completions
    assert "/query" in completions
    assert "/clear" in completions


def test_get_slash_command_completions_partial_match():
    """Test that partial slash commands return matching completions."""
    from treeline.cli import get_slash_command_completions

    # Test partial match
    completions = get_slash_command_completions("/st")
    assert "/status" in completions

    # Test another partial match
    completions = get_slash_command_completions("/q")
    assert "/query" in completions

    # Test partial that matches multiple
    completions = get_slash_command_completions("/s")
    assert "/status" in completions
    assert "/simplefin" in completions
    assert "/sync" in completions


def test_get_slash_command_completions_no_match():
    """Test that non-matching text returns empty list."""
    from treeline.cli import get_slash_command_completions

    completions = get_slash_command_completions("/xyz")
    assert len(completions) == 0


def test_get_slash_command_completions_empty_string():
    """Test that empty string returns empty list."""
    from treeline.cli import get_slash_command_completions

    completions = get_slash_command_completions("")
    assert len(completions) == 0


def test_get_slash_command_completions_non_slash():
    """Test that text not starting with '/' returns empty list."""
    from treeline.cli import get_slash_command_completions

    completions = get_slash_command_completions("hello")
    assert len(completions) == 0

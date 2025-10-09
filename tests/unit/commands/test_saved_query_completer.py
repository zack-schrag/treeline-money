"""Tests for SavedQueryCompleter."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from prompt_toolkit.document import Document

from treeline.commands.query import SavedQueryCompleter


@patch("treeline.commands.query.list_queries")
@patch("treeline.commands.query.load_query")
def test_completer_suggests_saved_queries_at_start(mock_load_query, mock_list_queries):
    """Test that completer suggests saved queries when buffer is empty."""
    # Setup mocks
    mock_list_queries.return_value = ["monthly_spending", "net_worth"]
    mock_load_query.side_effect = lambda name: f"SELECT * FROM {name};"

    completer = SavedQueryCompleter()
    document = Document("")  # Empty buffer

    completions = list(completer.get_completions(document, None))

    assert len(completions) == 2
    assert any("monthly_spending" in str(c.display) for c in completions)
    assert any("net_worth" in str(c.display) for c in completions)


@patch("treeline.commands.query.list_queries")
@patch("treeline.commands.query.load_query")
def test_completer_suggests_queries_with_load_prefix(mock_load_query, mock_list_queries):
    """Test that completer suggests queries when user types /load."""
    # Setup mocks
    mock_list_queries.return_value = ["monthly_spending", "monthly_summary"]
    mock_load_query.side_effect = lambda name: f"SELECT * FROM {name};"

    completer = SavedQueryCompleter()
    document = Document("/load mon")

    completions = list(completer.get_completions(document, None))

    # Both queries starting with "mon" should be suggested
    assert len(completions) == 2
    assert any("monthly_spending" in str(c.display) for c in completions)
    assert any("monthly_summary" in str(c.display) for c in completions)


@patch("treeline.commands.query.list_queries")
def test_completer_returns_nothing_when_no_saved_queries(mock_list_queries):
    """Test that completer returns nothing when there are no saved queries."""
    mock_list_queries.return_value = []

    completer = SavedQueryCompleter()
    document = Document("")

    completions = list(completer.get_completions(document, None))

    assert len(completions) == 0


@patch("treeline.commands.query.list_queries")
@patch("treeline.commands.query.load_query")
def test_completer_loads_actual_sql_content(mock_load_query, mock_list_queries):
    """Test that completer loads the actual SQL content, not just the name."""
    # Setup mocks
    mock_list_queries.return_value = ["test_query"]
    expected_sql = "SELECT COUNT(*) FROM transactions WHERE amount < 0;"
    mock_load_query.return_value = expected_sql

    completer = SavedQueryCompleter()
    document = Document("")

    completions = list(completer.get_completions(document, None))

    assert len(completions) == 1
    assert completions[0].text == expected_sql


@patch("treeline.commands.query.list_queries")
@patch("treeline.commands.query.load_query")
def test_completer_filters_by_prefix(mock_load_query, mock_list_queries):
    """Test that completer filters queries by prefix."""
    # Setup mocks
    mock_list_queries.return_value = ["monthly_spending", "yearly_summary", "net_worth"]
    mock_load_query.side_effect = lambda name: f"SELECT * FROM {name};"

    completer = SavedQueryCompleter()
    document = Document("/load mon")

    completions = list(completer.get_completions(document, None))

    # Only "monthly_spending" should match "mon"
    assert len(completions) == 1
    assert "monthly_spending" in str(completions[0].display)

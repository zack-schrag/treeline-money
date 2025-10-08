"""Tests for saved queries functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from treeline.commands.saved_queries import (
    delete_query,
    get_queries_dir,
    list_queries,
    load_query,
    save_query,
    show_query,
    validate_query_name,
)


def test_validate_query_name_accepts_valid_names():
    """Test that validate_query_name accepts alphanumeric and underscores."""
    assert validate_query_name("my_query") is True
    assert validate_query_name("query123") is True
    assert validate_query_name("dining_this_month") is True
    assert validate_query_name("q") is True


def test_validate_query_name_rejects_invalid_names():
    """Test that validate_query_name rejects invalid characters."""
    assert validate_query_name("my-query") is False
    assert validate_query_name("my query") is False
    assert validate_query_name("my.query") is False
    assert validate_query_name("my/query") is False
    assert validate_query_name("") is False


def test_get_queries_dir_returns_correct_path():
    """Test that get_queries_dir returns ~/.treeline/queries/."""
    queries_dir = get_queries_dir()
    assert str(queries_dir).endswith(".treeline/queries")


def test_save_query_creates_file():
    """Test that save_query creates a file with the query content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queries_dir = Path(tmpdir) / "queries"
        sql = "SELECT * FROM transactions LIMIT 10;"
        name = "test_query"

        result = save_query(name, sql, queries_dir)

        assert result is True
        query_file = queries_dir / f"{name}.sql"
        assert query_file.exists()
        assert query_file.read_text() == sql


def test_save_query_creates_directory_if_missing():
    """Test that save_query creates the queries directory if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queries_dir = Path(tmpdir) / "queries"
        assert not queries_dir.exists()

        sql = "SELECT * FROM accounts;"
        name = "test_query"

        result = save_query(name, sql, queries_dir)

        assert result is True
        assert queries_dir.exists()
        assert (queries_dir / f"{name}.sql").exists()


def test_load_query_returns_sql():
    """Test that load_query reads and returns the SQL from file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queries_dir = Path(tmpdir) / "queries"
        queries_dir.mkdir()

        name = "test_query"
        sql = "SELECT * FROM balance_snapshots;"
        query_file = queries_dir / f"{name}.sql"
        query_file.write_text(sql)

        loaded_sql = load_query(name, queries_dir)

        assert loaded_sql == sql


def test_load_query_returns_none_for_missing_file():
    """Test that load_query returns None if file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queries_dir = Path(tmpdir) / "queries"
        queries_dir.mkdir()

        loaded_sql = load_query("nonexistent_query", queries_dir)

        assert loaded_sql is None


def test_list_queries_returns_query_names():
    """Test that list_queries returns all .sql filenames without extension."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queries_dir = Path(tmpdir) / "queries"
        queries_dir.mkdir()

        # Create some query files
        (queries_dir / "dining_this_month.sql").write_text("SELECT 1;")
        (queries_dir / "net_worth_trend.sql").write_text("SELECT 2;")
        (queries_dir / "monthly_summary.sql").write_text("SELECT 3;")

        queries = list_queries(queries_dir)

        assert set(queries) == {"dining_this_month", "net_worth_trend", "monthly_summary"}


def test_list_queries_returns_empty_for_missing_directory():
    """Test that list_queries returns empty list if directory doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queries_dir = Path(tmpdir) / "queries"

        queries = list_queries(queries_dir)

        assert queries == []


def test_delete_query_removes_file():
    """Test that delete_query removes the query file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queries_dir = Path(tmpdir) / "queries"
        queries_dir.mkdir()

        name = "test_query"
        query_file = queries_dir / f"{name}.sql"
        query_file.write_text("SELECT 1;")

        result = delete_query(name, queries_dir)

        assert result is True
        assert not query_file.exists()


def test_delete_query_returns_false_for_missing_file():
    """Test that delete_query returns False if file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queries_dir = Path(tmpdir) / "queries"
        queries_dir.mkdir()

        result = delete_query("nonexistent_query", queries_dir)

        assert result is False


@patch("treeline.commands.saved_queries.console")
def test_show_query_displays_sql(mock_console):
    """Test that show_query displays the SQL content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queries_dir = Path(tmpdir) / "queries"
        queries_dir.mkdir()

        name = "test_query"
        sql = "SELECT * FROM transactions WHERE amount < 0;"
        query_file = queries_dir / f"{name}.sql"
        query_file.write_text(sql)

        show_query(name, queries_dir)

        # Verify that console.print was called (SQL was displayed)
        assert mock_console.print.called
        # Check that Syntax highlighting was used (Panel with Syntax)
        from rich.panel import Panel
        panel_printed = any(
            isinstance(call[0][0], Panel) if call[0] else False
            for call in mock_console.print.call_args_list
        )
        assert panel_printed

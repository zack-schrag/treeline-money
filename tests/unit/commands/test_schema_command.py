"""Tests for schema command."""

from unittest.mock import AsyncMock, MagicMock, patch
from treeline.commands.schema import handle_schema_command


def test_schema_command_exists():
    """Test that handle_schema_command function exists."""
    assert callable(handle_schema_command)


@patch("treeline.commands.schema.get_container")
@patch("treeline.commands.schema.console")
def test_schema_command_lists_all_tables(mock_console, mock_get_container):
    """Test that /schema lists all available tables."""
    # Setup mocks
    mock_container = MagicMock()
    mock_config_service = MagicMock()
    mock_db_service = MagicMock()

    mock_config_service.get_current_user_id.return_value = "12345678-1234-5678-1234-567812345678"

    # Mock the schema query result
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.data = {
        "rows": [
            ["transactions"],
            ["accounts"],
            ["balance_snapshots"],
        ],
        "columns": ["table_name"]
    }
    mock_db_service.execute_query = AsyncMock(return_value=mock_result)

    mock_container.config_service.return_value = mock_config_service
    mock_container.db_service.return_value = mock_db_service
    mock_get_container.return_value = mock_container

    # Execute
    handle_schema_command(None)

    # Verify query was executed
    mock_db_service.execute_query.assert_called_once()
    call_args = mock_db_service.execute_query.call_args
    assert "information_schema.tables" in call_args[0][1]


@patch("treeline.commands.schema.get_container")
@patch("treeline.commands.schema.console")
def test_schema_command_shows_table_columns(mock_console, mock_get_container):
    """Test that /schema table_name shows columns with types."""
    # Setup mocks
    mock_container = MagicMock()
    mock_config_service = MagicMock()
    mock_db_service = MagicMock()

    mock_config_service.get_current_user_id.return_value = "12345678-1234-5678-1234-567812345678"

    # Mock the column query result
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.data = {
        "rows": [
            ["transaction_id", "VARCHAR", "NO"],
            ["account_id", "VARCHAR", "NO"],
            ["amount", "DECIMAL", "NO"],
            ["description", "VARCHAR", "YES"],
        ],
        "columns": ["column_name", "data_type", "is_nullable"]
    }
    mock_db_service.execute_query = AsyncMock(return_value=mock_result)

    mock_container.config_service.return_value = mock_config_service
    mock_container.db_service.return_value = mock_db_service
    mock_get_container.return_value = mock_container

    # Execute
    handle_schema_command("transactions")

    # Verify query was executed with table name
    mock_db_service.execute_query.assert_called_once()
    call_args = mock_db_service.execute_query.call_args
    assert "information_schema.columns" in call_args[0][1]
    assert "transactions" in call_args[0][1]


@patch("treeline.commands.schema.get_container")
@patch("treeline.commands.schema.console")
def test_schema_command_requires_authentication(mock_console, mock_get_container):
    """Test that /schema requires user to be authenticated."""
    # Setup mocks - no user ID
    mock_container = MagicMock()
    mock_config_service = MagicMock()
    mock_config_service.get_current_user_id.return_value = None

    mock_container.config_service.return_value = mock_config_service
    mock_get_container.return_value = mock_container

    # Execute
    handle_schema_command(None)

    # Verify error message was printed
    error_printed = any(
        "Error" in str(call) and "authenticated" in str(call).lower()
        for call in mock_console.print.call_args_list
    )
    assert error_printed


@patch("treeline.commands.schema.get_container")
@patch("treeline.commands.schema.console")
def test_schema_command_handles_invalid_table_name(mock_console, mock_get_container):
    """Test that /schema gracefully handles invalid table names."""
    # Setup mocks
    mock_container = MagicMock()
    mock_config_service = MagicMock()
    mock_db_service = MagicMock()

    mock_config_service.get_current_user_id.return_value = "12345678-1234-5678-1234-567812345678"

    # Mock empty result (table doesn't exist)
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.data = {
        "rows": [],
        "columns": ["column_name", "data_type", "is_nullable"]
    }
    mock_db_service.execute_query = AsyncMock(return_value=mock_result)

    mock_container.config_service.return_value = mock_config_service
    mock_container.db_service.return_value = mock_db_service
    mock_get_container.return_value = mock_container

    # Execute with invalid table
    handle_schema_command("nonexistent_table")

    # Verify appropriate message was printed
    error_or_warning = any(
        ("not found" in str(call).lower() or "doesn't exist" in str(call).lower())
        for call in mock_console.print.call_args_list
    )
    assert error_or_warning


@patch("treeline.commands.schema.get_container")
@patch("treeline.commands.schema.console")
def test_schema_command_includes_example_query(mock_console, mock_get_container):
    """Test that /schema table_name includes an example query."""
    # Setup mocks
    mock_container = MagicMock()
    mock_config_service = MagicMock()
    mock_db_service = MagicMock()

    mock_config_service.get_current_user_id.return_value = "12345678-1234-5678-1234-567812345678"

    # Mock the column query result
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.data = {
        "rows": [["transaction_id", "VARCHAR", "NO"]],
        "columns": ["column_name", "data_type", "is_nullable"]
    }
    mock_db_service.execute_query = AsyncMock(return_value=mock_result)

    mock_container.config_service.return_value = mock_config_service
    mock_container.db_service.return_value = mock_db_service
    mock_get_container.return_value = mock_container

    # Execute
    handle_schema_command("transactions")

    # Verify example query was printed (Panel with "Example Query" title)
    # Check if Panel was printed (Panel objects are passed to console.print)
    from rich.panel import Panel
    panel_printed = any(
        isinstance(call[0][0], Panel) if call[0] else False
        for call in mock_console.print.call_args_list
    )
    assert panel_printed

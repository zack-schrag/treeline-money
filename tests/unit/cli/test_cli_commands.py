"""Unit tests for CLI top-level scriptable commands."""

from unittest.mock import Mock, patch, AsyncMock

import pytest
from typer.testing import CliRunner

from treeline.cli import app


runner = CliRunner()


@patch("treeline.cli.ensure_treeline_initialized")
@patch("treeline.cli.get_container")
def test_status_command(mock_get_container, mock_ensure_init):
    """Test 'treeline status' command works from CLI."""
    # Setup mocks
    mock_ensure_init.return_value = False

    mock_config_service = Mock()
    mock_config_service.get_current_user_id.return_value = "123e4567-e89b-12d3-a456-426614174000"

    mock_status_service = Mock()
    mock_result = Mock()
    mock_result.success = True
    mock_result.data = {
        "accounts": [],
        "total_transactions": 0,
        "total_snapshots": 0,
        "integrations": [],
        "earliest_date": None,
        "latest_date": None,
    }
    mock_status_service.get_status = AsyncMock(return_value=mock_result)

    mock_container = Mock()
    mock_container.config_service.return_value = mock_config_service
    mock_container.status_service.return_value = mock_status_service
    mock_get_container.return_value = mock_container

    # Run command
    result = runner.invoke(app, ["status"])

    # Assertions
    assert result.exit_code == 0
    assert "Financial Data Status" in result.stdout


@patch("treeline.cli.ensure_treeline_initialized")
@patch("treeline.cli.get_container")
def test_query_command_with_sql(mock_get_container, mock_ensure_init):
    """Test 'treeline query' command with SQL argument."""
    # Setup mocks
    mock_ensure_init.return_value = False

    mock_config_service = Mock()
    mock_config_service.get_current_user_id.return_value = "123e4567-e89b-12d3-a456-426614174000"

    mock_db_service = Mock()
    mock_result = Mock()
    mock_result.success = True
    mock_result.data = {
        "rows": [[5]],
        "columns": ["count"],
    }
    mock_db_service.execute_query = AsyncMock(return_value=mock_result)

    mock_container = Mock()
    mock_container.config_service.return_value = mock_config_service
    mock_container.db_service.return_value = mock_db_service
    mock_get_container.return_value = mock_container

    # Run command
    result = runner.invoke(app, ["query", "SELECT COUNT(*) as count FROM transactions"])

    # Assertions
    assert result.exit_code == 0
    # New query command displays results as table with "count" column header
    assert "count" in result.stdout
    assert "row" in result.stdout


@patch("treeline.cli.ensure_treeline_initialized")
@patch("treeline.cli.get_container")
def test_query_command_rejects_non_select(mock_get_container, mock_ensure_init):
    """Test 'treeline query' rejects non-SELECT queries."""
    # Setup mocks
    mock_ensure_init.return_value = False

    mock_config_service = Mock()
    mock_config_service.get_current_user_id.return_value = "123e4567-e89b-12d3-a456-426614174000"

    mock_container = Mock()
    mock_container.config_service.return_value = mock_config_service
    mock_get_container.return_value = mock_container

    # Run command
    result = runner.invoke(app, ["query", "DELETE FROM transactions"])

    # Assertions
    assert result.exit_code == 1  # Now raises typer.Exit(1) for rejected queries
    assert "Only SELECT and WITH queries are allowed" in result.stdout


@patch("treeline.cli.ensure_treeline_initialized")
@patch("treeline.cli.get_container")
def test_sync_command(mock_get_container, mock_ensure_init):
    """Test 'treeline sync' command works from CLI."""
    # Setup mocks
    mock_ensure_init.return_value = False

    mock_config_service = Mock()
    mock_config_service.get_current_user_id.return_value = "123e4567-e89b-12d3-a456-426614174000"

    mock_db_service = Mock()
    mock_db_result = Mock()
    mock_db_result.success = True
    mock_db_service.initialize_user_db = AsyncMock(return_value=mock_db_result)

    mock_sync_service = Mock()
    mock_sync_result = Mock()
    mock_sync_result.success = True
    mock_sync_result.data = {"results": []}
    mock_sync_service.sync_all_integrations = AsyncMock(return_value=mock_sync_result)

    mock_container = Mock()
    mock_container.config_service.return_value = mock_config_service
    mock_container.db_service.return_value = mock_db_service
    mock_container.sync_service.return_value = mock_sync_service
    mock_get_container.return_value = mock_container

    # Run command
    result = runner.invoke(app, ["sync"])

    # Assertions
    assert result.exit_code == 0
    assert "Synchronizing Financial Data" in result.stdout

"""Tests for /sql command (multi-line SQL editor)."""

from unittest.mock import Mock, patch, MagicMock
import pytest
from treeline.commands.query import handle_sql_command


@pytest.fixture
def mock_container():
    """Create a mock container with necessary services."""
    container = Mock()
    config_service = Mock()
    db_service = Mock()

    config_service.get_current_user_id.return_value = "test-user-id"
    container.config_service.return_value = config_service
    container.db_service.return_value = db_service

    return container


def test_sql_command_exists():
    """Test that handle_sql_command function exists."""
    from treeline.commands.query import handle_sql_command
    assert callable(handle_sql_command)


@patch('treeline.commands.query.get_container')
@patch('treeline.commands.query.asyncio.run')
@patch('treeline.commands.query.Confirm')
@patch('treeline.commands.query.PromptSession')
def test_sql_command_opens_multiline_editor(mock_prompt_session, mock_confirm, mock_asyncio_run, mock_get_container):
    """Test that /sql opens a multi-line editor."""
    # Setup mocks
    container = Mock()
    config_service = Mock()
    db_service = Mock()

    config_service.get_current_user_id.return_value = "12345678-1234-5678-1234-567812345678"
    container.config_service.return_value = config_service
    container.db_service.return_value = db_service
    mock_get_container.return_value = container

    # Mock the prompt session to return a simple query
    session_instance = Mock()
    session_instance.prompt.return_value = "SELECT * FROM transactions LIMIT 1"
    mock_prompt_session.return_value = session_instance

    # Mock successful query execution
    mock_asyncio_run.return_value = Mock(
        success=True,
        data={"rows": [[1, "test"]], "columns": ["id", "description"]}
    )

    # Mock the save prompt to decline saving
    mock_confirm.ask.return_value = False

    # Execute command
    handle_sql_command()

    # Verify PromptSession was created with multiline=True
    mock_prompt_session.assert_called_once()
    call_kwargs = mock_prompt_session.call_args[1]
    assert call_kwargs.get('multiline') is True


@patch('treeline.commands.query.get_container')
@patch('treeline.commands.query.asyncio.run')
@patch('treeline.commands.query.PromptSession')
def test_sql_command_validates_select_only(mock_prompt_session, mock_asyncio_run, mock_get_container):
    """Test that /sql only allows SELECT and WITH queries."""
    # Setup mocks
    container = Mock()
    config_service = Mock()
    db_service = Mock()

    config_service.get_current_user_id.return_value = "12345678-1234-5678-1234-567812345678"
    container.config_service.return_value = config_service
    container.db_service.return_value = db_service
    mock_get_container.return_value = container

    # Mock the prompt session to return a DELETE query
    session_instance = Mock()
    session_instance.prompt.return_value = "DELETE FROM transactions"
    mock_prompt_session.return_value = session_instance

    # Execute command
    handle_sql_command()

    # Verify db_service.execute_query was NOT called
    mock_asyncio_run.assert_not_called()


@patch('treeline.commands.query.get_container')
@patch('treeline.commands.query.PromptSession')
def test_sql_command_requires_authentication(mock_prompt_session, mock_get_container):
    """Test that /sql requires user to be authenticated."""
    # Setup mocks
    container = Mock()
    config_service = Mock()

    config_service.get_current_user_id.return_value = None  # Not authenticated
    container.config_service.return_value = config_service
    mock_get_container.return_value = container

    # Execute command
    handle_sql_command()

    # Verify prompt was never called (returned early)
    mock_prompt_session.assert_not_called()


@patch('treeline.commands.query.get_container')
@patch('treeline.commands.query.asyncio.run')
@patch('treeline.commands.query.PromptSession')
def test_sql_command_handles_ctrl_c_gracefully(mock_prompt_session, mock_asyncio_run, mock_get_container):
    """Test that Ctrl+C in the editor returns to main prompt."""
    # Setup mocks
    container = Mock()
    config_service = Mock()
    db_service = Mock()

    config_service.get_current_user_id.return_value = "12345678-1234-5678-1234-567812345678"
    container.config_service.return_value = config_service
    container.db_service.return_value = db_service
    mock_get_container.return_value = container

    # Mock the prompt session to raise KeyboardInterrupt
    session_instance = Mock()
    session_instance.prompt.side_effect = KeyboardInterrupt()
    mock_prompt_session.return_value = session_instance

    # Execute command - should not raise exception
    handle_sql_command()

    # Verify query was never executed
    mock_asyncio_run.assert_not_called()

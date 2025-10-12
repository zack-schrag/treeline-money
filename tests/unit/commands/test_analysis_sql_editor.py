"""Tests for analysis mode SQL editor.

NOTE: These tests are for the old readchar-based implementation.
They need to be rewritten for the new prompt_toolkit Application architecture.

TODO: Rewrite tests to mock Application.run() and test:
- Buffer updates
- Key binding handlers
- Results control rendering
"""

import pytest
from unittest.mock import patch, Mock, MagicMock

from treeline.domain import AnalysisSession, Ok, Fail
from treeline.commands.analysis import _execute_query, _format_help_overlay, _format_load_menu, _format_browser_ui


# TODO: Rewrite SQL editor tests for prompt_toolkit architecture


class TestQueryExecution:
    """Tests for query execution."""

    @pytest.mark.asyncio
    @patch('treeline.commands.analysis.get_current_user_id')
    @patch('treeline.commands.analysis.get_container')
    async def test_execute_query_success(self, mock_get_container, mock_get_user_id):
        """Test successful query execution updates session."""
        # Setup
        session = AnalysisSession(sql="SELECT id, name FROM users")
        mock_get_user_id.return_value = "550e8400-e29b-41d4-a716-446655440000"
        mock_container = Mock()
        mock_db_service = Mock()

        # Make execute_query return an async coroutine
        async def mock_execute_query(*args, **kwargs):
            return Ok({
                'columns': ['id', 'name'],
                'rows': [[1, 'Alice'], [2, 'Bob']]
            })

        mock_db_service.execute_query = mock_execute_query
        mock_container.db_service.return_value = mock_db_service
        mock_get_container.return_value = mock_container

        # Execute
        await _execute_query(session)

        # Verify
        assert session.has_results()
        assert session.columns == ['id', 'name']
        assert len(session.results) == 2
        assert session.view_mode == "results"

    @pytest.mark.asyncio
    @patch('treeline.commands.analysis.get_current_user_id')
    @patch('treeline.commands.analysis.get_container')
    async def test_execute_query_failure(self, mock_get_container, mock_get_user_id):
        """Test query failure leaves session unchanged."""
        # Setup
        session = AnalysisSession(sql="SELECT * FROM nonexistent")
        mock_get_user_id.return_value = "550e8400-e29b-41d4-a716-446655440000"
        mock_container = Mock()
        mock_db_service = Mock()

        # Make execute_query return an async coroutine that fails
        async def mock_execute_query(*args, **kwargs):
            return Fail("Table does not exist")

        mock_db_service.execute_query = mock_execute_query
        mock_container.db_service.return_value = mock_db_service
        mock_get_container.return_value = mock_container

        # Execute
        await _execute_query(session)

        # Verify - session should remain empty on failure
        assert not session.has_results()
        # Verify error message is set
        assert session.error_message != ""
        assert "Table does not exist" in session.error_message

    @pytest.mark.asyncio
    async def test_execute_query_rejects_non_select(self):
        """Test that non-SELECT queries are rejected."""
        # Setup
        session = AnalysisSession(sql="DELETE FROM users")

        # Execute
        await _execute_query(session)

        # Verify - session should remain empty for non-SELECT
        assert not session.has_results()
        # Verify error message is set
        assert "Only SELECT and WITH queries are allowed" in session.error_message

    @pytest.mark.asyncio
    async def test_execute_query_empty_sql(self):
        """Test that empty SQL doesn't execute."""
        # Setup
        session = AnalysisSession(sql="")

        # Execute (should not crash)
        await _execute_query(session)

        # Verify
        assert not session.has_results()


class TestHelpOverlay:
    """Tests for help overlay."""

    def test_format_help_overlay(self):
        """Test that help overlay contains key keybindings."""
        # Execute
        result = _format_help_overlay()

        # Verify result is list of tuples
        assert isinstance(result, list)
        assert len(result) > 0

        # Convert to text to verify content
        text = "".join(t[1] for t in result)

        # Verify key sections are present
        assert "Analysis Mode Shortcuts" in text
        assert "Ctrl+Enter" in text
        assert "Execute query" in text
        assert "Tab" in text
        assert "Switch focus" in text
        assert "Create/edit chart" in text
        assert "Save query" in text
        assert "Reset" in text
        assert "Exit analysis mode" in text
        assert "?" in text
        assert "Show this help" in text
        assert "Load saved query" in text


class TestLoadMenu:
    """Tests for load menu."""

    def test_format_load_menu(self):
        """Test that load menu contains query and chart options."""
        # Execute
        result = _format_load_menu()

        # Verify result is list of tuples
        assert isinstance(result, list)
        assert len(result) > 0

        # Convert to text to verify content
        text = "".join(t[1] for t in result)

        # Verify key sections are present
        assert "Load Saved Item" in text
        assert "[q] Query" in text
        assert "[c] Chart" in text
        assert "Esc to cancel" in text


class TestBrowserUI:
    """Tests for browser UI."""

    def test_format_browser_ui_with_items(self):
        """Test that browser UI shows list of items."""
        # Setup
        session = AnalysisSession(
            browse_items=["query1", "query2", "query3"],
            browse_selected_index=1
        )

        # Execute
        result = _format_browser_ui(session, "query")

        # Verify result is list of tuples
        assert isinstance(result, list)
        assert len(result) > 0

        # Convert to text to verify content
        text = "".join(t[1] for t in result)

        # Verify content
        assert "Load Query" in text
        assert "query1" in text
        assert "query2" in text
        assert "query3" in text
        assert "↑↓ to navigate" in text
        assert "Enter to load" in text

    def test_format_browser_ui_empty(self):
        """Test that browser UI shows empty message."""
        # Setup
        session = AnalysisSession(
            browse_items=[],
            browse_selected_index=0
        )

        # Execute
        result = _format_browser_ui(session, "chart")

        # Verify result is list of tuples
        assert isinstance(result, list)
        assert len(result) > 0

        # Convert to text to verify content
        text = "".join(t[1] for t in result)

        # Verify content
        assert "Load Chart" in text
        assert "No saved charts found" in text
        assert "Esc to cancel" in text

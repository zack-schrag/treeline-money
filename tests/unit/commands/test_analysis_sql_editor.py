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
from treeline.commands.analysis import _execute_query


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

    @pytest.mark.asyncio
    async def test_execute_query_rejects_non_select(self):
        """Test that non-SELECT queries are rejected."""
        # Setup
        session = AnalysisSession(sql="DELETE FROM users")

        # Execute
        await _execute_query(session)

        # Verify - session should remain empty for non-SELECT
        assert not session.has_results()

    @pytest.mark.asyncio
    async def test_execute_query_empty_sql(self):
        """Test that empty SQL doesn't execute."""
        # Setup
        session = AnalysisSession(sql="")

        # Execute (should not crash)
        await _execute_query(session)

        # Verify
        assert not session.has_results()

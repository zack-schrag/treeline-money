"""Tests for post-query action menu."""

import pytest
from unittest.mock import Mock, patch, call
from treeline.commands.query import _prompt_post_query_actions


class TestPostQueryActionMenu:
    """Tests for the post-query action menu."""

    @patch('treeline.commands.query.Prompt.ask')
    @patch('treeline.commands.query._prompt_chart_wizard')
    def test_action_menu_chart_then_exit(self, mock_chart_wizard, mock_ask):
        """Test selecting chart then pressing enter to exit."""
        # User presses 'c' for chart, then enter to exit
        mock_ask.side_effect = ['c', '']

        sql = "SELECT * FROM transactions"
        columns = ["id", "amount"]
        rows = [[1, 100], [2, 200]]

        _prompt_post_query_actions(sql, columns, rows, loop_back_handler=None)

        # Chart wizard should be called
        assert mock_chart_wizard.called
        mock_chart_wizard.assert_called_once_with(sql, columns, rows)

        # Prompt should be shown twice (chart, then exit)
        assert mock_ask.call_count == 2

    @patch('treeline.commands.query.Prompt.ask')
    @patch('treeline.commands.query._prompt_to_save_query')
    def test_action_menu_save_flow(self, mock_save, mock_ask):
        """Test selecting save from action menu."""
        # User presses 's' to save
        mock_ask.return_value = 's'

        sql = "SELECT * FROM transactions"
        columns = ["id"]
        rows = [[1]]

        _prompt_post_query_actions(sql, columns, rows, loop_back_handler=None)

        # Save should be called
        mock_save.assert_called_once_with(sql)

        # Only one prompt (save then exit)
        assert mock_ask.call_count == 1

    @patch('treeline.commands.query.Prompt.ask')
    def test_action_menu_edit_flow(self, mock_ask):
        """Test selecting edit calls loop_back_handler."""
        # User presses 'e' to edit
        mock_ask.return_value = 'e'

        sql = "SELECT * FROM transactions"
        columns = ["id"]
        rows = [[1]]
        loop_back_handler = Mock()

        _prompt_post_query_actions(sql, columns, rows, loop_back_handler=loop_back_handler)

        # Loop back handler should be called
        loop_back_handler.assert_called_once()

    @patch('treeline.commands.query.Prompt.ask')
    def test_action_menu_enter_exits_cleanly(self, mock_ask):
        """Test pressing enter exits without prompts."""
        # User presses enter immediately
        mock_ask.return_value = ''

        sql = "SELECT * FROM transactions"
        columns = ["id"]
        rows = [[1]]

        _prompt_post_query_actions(sql, columns, rows, loop_back_handler=None)

        # Only one prompt, then exit
        assert mock_ask.call_count == 1

    @patch('treeline.commands.query.Prompt.ask')
    @patch('treeline.commands.query.console.print')
    def test_action_menu_invalid_option_reprompts(self, mock_print, mock_ask):
        """Test invalid option shows error and reprompts."""
        # User types invalid, then exits
        mock_ask.side_effect = ['x', '']

        sql = "SELECT * FROM transactions"
        columns = ["id"]
        rows = [[1]]

        _prompt_post_query_actions(sql, columns, rows, loop_back_handler=None)

        # Should print error message
        assert any('Invalid' in str(call_args) for call_args in mock_print.call_args_list)

        # Should prompt twice
        assert mock_ask.call_count == 2

    @patch('treeline.commands.query.Prompt.ask')
    def test_action_menu_edit_without_handler_no_op(self, mock_ask):
        """Test edit without loop_back_handler exits gracefully."""
        # User presses 'e' but no handler provided
        mock_ask.return_value = 'e'

        sql = "SELECT * FROM transactions"
        columns = ["id"]
        rows = [[1]]

        # Should not raise error
        _prompt_post_query_actions(sql, columns, rows, loop_back_handler=None)

    @patch('treeline.commands.query.Prompt.ask')
    @patch('treeline.commands.query._prompt_chart_wizard')
    @patch('treeline.commands.query._prompt_to_save_query')
    def test_action_menu_chart_then_save(self, mock_save, mock_chart, mock_ask):
        """Test creating chart then saving query."""
        # User: chart, then save
        mock_ask.side_effect = ['c', 's']

        sql = "SELECT * FROM transactions"
        columns = ["id", "amount"]
        rows = [[1, 100]]

        _prompt_post_query_actions(sql, columns, rows, loop_back_handler=None)

        # Both should be called
        assert mock_chart.called
        assert mock_save.called

        # Chart first, save second
        assert mock_ask.call_count == 2

    @patch('treeline.commands.query.Prompt.ask')
    def test_action_menu_case_insensitive(self, mock_ask):
        """Test action menu accepts uppercase letters."""
        loop_back_handler = Mock()

        # Test uppercase
        mock_ask.return_value = 'E'
        _prompt_post_query_actions("SELECT 1", ["x"], [[1]], loop_back_handler)

        assert loop_back_handler.called

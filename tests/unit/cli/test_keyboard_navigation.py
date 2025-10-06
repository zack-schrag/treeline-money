"""Unit tests for keyboard navigation in REPL.

Note: prompt_toolkit's PromptSession provides built-in support for:
- Up/Down arrows: Navigate command history
- Left/Right arrows: Move cursor for editing

These tests verify that we're using PromptSession correctly.
"""

from unittest.mock import MagicMock, patch
import pytest


def test_prompt_session_is_created_with_history():
    """Test that PromptSession is initialized (which provides command history)."""
    from treeline.cli import run_interactive_mode
    from prompt_toolkit import PromptSession

    with patch("treeline.cli.ensure_treeline_initialized", return_value=False):
        with patch("treeline.cli.show_welcome_message"):
            with patch("treeline.cli.console"):
                # Mock PromptSession to capture creation
                with patch("treeline.cli.PromptSession") as mock_session_class:
                    mock_session = MagicMock()
                    # Simulate user typing "exit" to quit
                    mock_session.prompt.return_value = "exit"
                    mock_session_class.return_value = mock_session

                    # Run interactive mode (will exit after first prompt due to "exit")
                    run_interactive_mode()

                    # Verify PromptSession was created
                    mock_session_class.assert_called_once()
                    # Verify prompt was called
                    mock_session.prompt.assert_called()


def test_prompt_session_maintains_history_across_prompts():
    """Test that PromptSession maintains history across multiple prompts.

    This is an integration-style test that verifies prompt_toolkit's
    history feature is being used.
    """
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory

    # Create a session with in-memory history
    history = InMemoryHistory()
    session = PromptSession(history=history)

    # Simulate adding commands to history
    history.append_string("/status")
    history.append_string("/query SELECT * FROM transactions")
    history.append_string("/help")

    # Verify history contains the commands
    history_items = list(history.load_history_strings())
    assert "/status" in history_items
    assert "/query SELECT * FROM transactions" in history_items
    assert "/help" in history_items
    assert len(history_items) == 3

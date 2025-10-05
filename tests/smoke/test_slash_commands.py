"""Smoke tests for slash commands in interactive mode.

These tests execute the actual CLI without mocks to validate end-to-end functionality.
"""

import os
import tempfile
from pathlib import Path
from typer.testing import CliRunner

from treeline.cli import app


runner = CliRunner()


def test_status_slash_command_in_interactive_mode():
    """Test /status command works in interactive REPL mode."""
    # Create a temp directory and change to it for the test
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Run CLI and send /status command followed by exit
            result = runner.invoke(
                app,
                [],
                input="/status\nexit\n",
                catch_exceptions=False
            )

            # Should show status output (even if empty/not authenticated)
            assert "Financial Data Status" in result.stdout or "Not authenticated" in result.stdout
        finally:
            os.chdir(original_cwd)


def test_query_slash_command_executes_sql():
    """Test /query command executes SQL successfully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Run CLI and execute a simple query
            result = runner.invoke(
                app,
                [],
                input="/query SELECT 1\nexit\n",
                catch_exceptions=False
            )

            # Should execute the query and show results
            assert "Executing Query" in result.stdout
            assert "SELECT 1" in result.stdout
        finally:
            os.chdir(original_cwd)


def test_help_slash_command():
    """Test /help command shows available commands."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            result = runner.invoke(
                app,
                [],
                input="/help\nexit\n",
                catch_exceptions=False
            )

            # Should show help table with commands
            assert "/help" in result.stdout
            assert "/status" in result.stdout
            assert "/query" in result.stdout
            assert "/sync" in result.stdout
        finally:
            os.chdir(original_cwd)


def test_clear_slash_command():
    """Test /clear command clears conversation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            result = runner.invoke(
                app,
                [],
                input="/clear\nexit\n",
                catch_exceptions=False
            )

            # Should show cleared message
            assert "Conversation cleared" in result.stdout or "Starting fresh" in result.stdout
        finally:
            os.chdir(original_cwd)

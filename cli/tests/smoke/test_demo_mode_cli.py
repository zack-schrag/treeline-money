"""Smoke tests for demo mode CLI commands.

These tests verify that CLI commands work end-to-end in demo mode.
No treeline imports - only CLI interaction via subprocess.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path


def run_treeline_cli(args: list[str], treeline_dir: str) -> subprocess.CompletedProcess:
    """Run treeline CLI command with demo mode enabled.

    Args:
        args: CLI arguments (e.g., ["status", "--json"])
        treeline_dir: Path to treeline data directory

    Returns:
        CompletedProcess with stdout, stderr, returncode
    """
    env = os.environ.copy()
    env["TREELINE_DEMO_MODE"] = "true"
    env["TREELINE_DIR"] = str(
        Path(treeline_dir) / ".treeline"
    )  # Override treeline directory for testing

    cmd = ["uv", "run", "treeline"] + args
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def test_demo_mode_sync_and_status():
    """Test that sync and status work in demo mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up integration using CLI command with --token flag
        result = run_treeline_cli(
            ["setup", "simplefin", "--token", "demo-token"], tmpdir
        )
        assert result.returncode == 0, f"setup failed: {result.stderr}"

        # Sync should work with demo provider
        result = run_treeline_cli(["sync"], tmpdir)
        assert result.returncode == 0, f"sync failed: {result.stderr}"

        # Status should show demo accounts and transactions
        result = run_treeline_cli(["status", "--json"], tmpdir)
        assert result.returncode == 0, f"status failed: {result.stderr}"

        data = json.loads(result.stdout)
        assert data["total_accounts"] > 0
        assert data["total_transactions"] > 0


def test_demo_mode_query():
    """Test that SQL queries work on demo data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup and sync using CLI commands
        run_treeline_cli(["setup", "simplefin", "--token", "demo-token"], tmpdir)
        run_treeline_cli(["sync"], tmpdir)

        # Query transactions
        result = run_treeline_cli(
            ["query", "SELECT COUNT(*) as count FROM transactions", "--json"], tmpdir
        )
        assert result.returncode == 0, f"query failed: {result.stderr}"

        data = json.loads(result.stdout)
        assert len(data["rows"]) > 0
        assert data["rows"][0][0] > 0  # Count should be positive


def test_demo_mode_tag_and_query():
    """Test that tags can be applied and queried."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup and sync using CLI commands
        run_treeline_cli(["setup", "simplefin", "--token", "demo-token"], tmpdir)
        run_treeline_cli(["sync"], tmpdir)

        # Get a transaction ID
        result = run_treeline_cli(
            ["query", "SELECT transaction_id FROM transactions LIMIT 1", "--json"],
            tmpdir,
        )
        assert result.returncode == 0

        data = json.loads(result.stdout)
        transaction_id = data["rows"][0][0]

        # Apply tags
        result = run_treeline_cli(
            ["tag", "apply", "--ids", transaction_id, "smoke-test,demo"], tmpdir
        )
        assert result.returncode == 0, f"tag apply failed: {result.stderr}"

        # Query and verify tag was applied
        result = run_treeline_cli(
            [
                "query",
                f"SELECT tags FROM transactions WHERE transaction_id = '{transaction_id}'",
                "--json",
            ],
            tmpdir,
        )
        assert result.returncode == 0

        data = json.loads(result.stdout)
        tags_str = str(data["rows"][0][0])
        assert "smoke-test" in tags_str

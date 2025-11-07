"""Smoke tests for demo mode CLI commands.

These tests verify that CLI commands work end-to-end in demo mode.
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
    # Set dummy Supabase credentials (not used in demo mode but required by container)
    env["SUPABASE_URL"] = "http://demo.supabase.co"
    env["SUPABASE_KEY"] = "demo-key"

    cmd = ["uv", "run", "treeline"] + args
    return subprocess.run(
        cmd, capture_output=True, text=True, env=env, cwd="/home/user/treeline-money"
    )


def setup_demo_integration(treeline_dir: str):
    """Helper to set up demo integration programmatically."""
    from treeline.app.container import Container
    from uuid import UUID
    import asyncio

    # Ensure demo mode is enabled for this process too
    os.environ["TREELINE_DEMO_MODE"] = "true"
    os.environ["TREELINE_DIR"] = str(Path(treeline_dir) / ".treeline")
    os.environ["SUPABASE_URL"] = "http://demo.supabase.co"
    os.environ["SUPABASE_KEY"] = "demo-key"

    # Create .treeline directory
    treeline_path = Path(treeline_dir) / ".treeline"
    treeline_path.mkdir(parents=True, exist_ok=True)

    # Initialize container with DB directory (not file path)
    container = Container(str(treeline_path))
    user_id = UUID("00000000-0000-0000-0000-000000000000")

    # Initialize DB
    db_service = container.db_service()
    asyncio.run(db_service.initialize_db())
    asyncio.run(db_service.initialize_user_db(user_id))

    # Create demo integration
    integration_service = container.integration_service("simplefin")
    asyncio.run(
        integration_service.create_integration(
            user_id, "simplefin", {"setupToken": "demo"}
        )
    )


def test_demo_mode_sync_and_status():
    """Test that sync and status work in demo mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up integration programmatically (since CLI setup requires interactive input)
        setup_demo_integration(tmpdir)

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
        setup_demo_integration(tmpdir)
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
        setup_demo_integration(tmpdir)
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

"""End-to-end tests for demo mode CLI commands.

These tests verify that CLI commands work correctly in demo mode
without making real API calls.
"""

import os
import subprocess
import tempfile
from pathlib import Path


def run_cli_command(
    command: list[str], env_overrides: dict = None
) -> subprocess.CompletedProcess:
    """Run a CLI command with demo mode enabled.

    Args:
        command: List of command parts (e.g., ["treeline", "status"])
        env_overrides: Additional environment variables to set

    Returns:
        CompletedProcess with stdout, stderr, and returncode
    """
    env = os.environ.copy()
    env["TREELINE_DEMO_MODE"] = "true"

    if env_overrides:
        env.update(env_overrides)

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        env=env,
    )
    return result


def test_demo_mode_sync_integration_service():
    """Test that sync works with demo provider (integration test, not full CLI)."""
    from treeline.app.container import Container
    from uuid import uuid4
    import asyncio

    # Set demo mode
    os.environ["TREELINE_DEMO_MODE"] = "true"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            container = Container(str(Path(tmpdir) / "test.db"))

            # Initialize DB
            db_service = container.db_service()
            user_id = uuid4()

            init_result = asyncio.run(db_service.initialize_db())
            assert init_result.success

            user_init_result = asyncio.run(db_service.initialize_user_db(user_id))
            assert user_init_result.success

            # Create demo integration (no real credentials needed)
            integration_service = container.integration_service("simplefin")
            create_result = asyncio.run(
                integration_service.create_integration(
                    user_id, "simplefin", {"setupToken": "demo-token"}
                )
            )
            assert create_result.success

            # Sync with demo provider
            sync_service = container.sync_service()
            sync_result = asyncio.run(sync_service.sync_all_integrations(user_id))

            # Should succeed without real API calls
            assert sync_result.success
            assert len(sync_result.data["results"]) > 0

            # Verify accounts were created
            account_service = container.account_service()
            accounts_result = asyncio.run(account_service.get_accounts(user_id))
            assert accounts_result.success
            assert len(accounts_result.data) > 0

    finally:
        os.environ.pop("TREELINE_DEMO_MODE", None)


def test_demo_mode_query_transactions():
    """Test that querying transactions works with demo data."""
    from treeline.app.container import Container
    from uuid import uuid4
    import asyncio

    os.environ["TREELINE_DEMO_MODE"] = "true"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            container = Container(str(Path(tmpdir) / "test.db"))
            user_id = uuid4()

            # Initialize and sync
            db_service = container.db_service()
            asyncio.run(db_service.initialize_db())
            asyncio.run(db_service.initialize_user_db(user_id))

            integration_service = container.integration_service("simplefin")
            asyncio.run(
                integration_service.create_integration(
                    user_id, "simplefin", {"setupToken": "demo"}
                )
            )

            sync_service = container.sync_service()
            asyncio.run(sync_service.sync_all_integrations(user_id))

            # Query transactions
            query_result = asyncio.run(
                db_service.execute_query(
                    user_id, "SELECT COUNT(*) as count FROM transactions"
                )
            )

            assert query_result.success
            rows = query_result.data["rows"]
            assert len(rows) > 0
            assert rows[0][0] > 0  # Transaction count should be positive

    finally:
        os.environ.pop("TREELINE_DEMO_MODE", None)


def test_demo_mode_tag_transactions():
    """Test that tagging works with demo transactions."""
    from treeline.app.container import Container
    from uuid import uuid4
    import asyncio

    os.environ["TREELINE_DEMO_MODE"] = "true"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            container = Container(str(Path(tmpdir) / "test.db"))
            user_id = uuid4()

            # Initialize and sync
            db_service = container.db_service()
            asyncio.run(db_service.initialize_db())
            asyncio.run(db_service.initialize_user_db(user_id))

            integration_service = container.integration_service("simplefin")
            asyncio.run(
                integration_service.create_integration(
                    user_id, "simplefin", {"setupToken": "demo"}
                )
            )

            sync_service = container.sync_service()
            sync_result = asyncio.run(sync_service.sync_all_integrations(user_id))
            assert sync_result.success

            # Get a transaction to tag
            query_result = asyncio.run(
                db_service.execute_query(
                    user_id, "SELECT transaction_id FROM transactions LIMIT 1"
                )
            )
            assert query_result.success
            transaction_id = query_result.data["rows"][0][0]

            # Apply tags
            tagging_service = container.tagging_service()
            tag_result = asyncio.run(
                tagging_service.update_transaction_tags(
                    user_id, transaction_id, ["test-tag", "demo"]
                )
            )

            assert tag_result.success

    finally:
        os.environ.pop("TREELINE_DEMO_MODE", None)


def test_demo_mode_status():
    """Test that status command works with demo data."""
    from treeline.app.container import Container
    from uuid import uuid4
    import asyncio

    os.environ["TREELINE_DEMO_MODE"] = "true"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            container = Container(str(Path(tmpdir) / "test.db"))
            user_id = uuid4()

            # Initialize and sync
            db_service = container.db_service()
            asyncio.run(db_service.initialize_db())
            asyncio.run(db_service.initialize_user_db(user_id))

            integration_service = container.integration_service("simplefin")
            asyncio.run(
                integration_service.create_integration(
                    user_id, "simplefin", {"setupToken": "demo"}
                )
            )

            sync_service = container.sync_service()
            asyncio.run(sync_service.sync_all_integrations(user_id))

            # Get status
            status_service = container.status_service()
            status_result = asyncio.run(status_service.get_status(user_id))

            assert status_result.success
            data = status_result.data
            assert data["total_accounts"] > 0
            assert data["total_transactions"] > 0
            assert data["total_integrations"] > 0

    finally:
        os.environ.pop("TREELINE_DEMO_MODE", None)

"""Unit tests for DuckDB tag update functionality."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4
import tempfile
import shutil

from treeline.infra.duckdb import DuckDBRepository
from treeline.domain import Transaction


@pytest.mark.asyncio
async def test_update_transaction_tags_persists_changes():
    """Test that updating transaction tags actually saves to the database."""
    # Create a temporary directory for the test database
    test_dir = Path(tempfile.mkdtemp())

    try:
        # Create repository
        db_file_path = test_dir / "test.duckdb"
        repo = DuckDBRepository(str(db_file_path))
        await repo.ensure_schema_upgraded()

        # Create a test account first
        from treeline.domain import Account

        account = Account(
            id=uuid4(),
            name="Test Account",
            nickname=None,
            account_type="checking",
            currency="USD",
            balance=None,
            external_ids={},
            institution_name="Test Bank",
            institution_url=None,
            institution_domain=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await repo.add_account(account)

        # Create a test transaction with no tags
        transaction = Transaction(
            id=uuid4(),
            account_id=account.id,
            external_ids={},
            amount=Decimal("-50.00"),
            description="Coffee Shop",
            transaction_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            posted_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            tags=(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Add the transaction
        result = await repo.add_transaction(transaction)
        assert result.success

        # Update the tags
        new_tags = ["coffee", "food"]
        update_result = await repo.update_transaction_tags(
            str(transaction.id), new_tags
        )

        # Verify the update succeeded
        assert update_result.success, (
            f"Update failed: {update_result.error if not update_result.success else ''}"
        )
        updated_transaction = update_result.data

        # Verify the tags were actually updated
        assert len(updated_transaction.tags) == 2
        assert "coffee" in updated_transaction.tags
        assert "food" in updated_transaction.tags

        # Re-fetch the transaction to verify persistence
        # We'll use execute_query to fetch directly from the database
        query_result = await repo.execute_query(
            f"SELECT tags FROM sys_transactions WHERE transaction_id = '{transaction.id}'",
        )
        assert query_result.success
        result_data = query_result.data
        rows = result_data["rows"]

        assert len(rows) == 1
        persisted_tags = rows[0][0]  # First row, first column (tags)
        assert len(persisted_tags) == 2
        assert "coffee" in persisted_tags
        assert "food" in persisted_tags

    finally:
        # Cleanup
        shutil.rmtree(test_dir)


@pytest.mark.asyncio
async def test_update_transaction_tags_can_clear_tags():
    """Test that updating tags to an empty list clears all tags."""
    test_dir = Path(tempfile.mkdtemp())

    try:
        db_file_path = test_dir / "test.duckdb"
        repo = DuckDBRepository(str(db_file_path))
        await repo.ensure_schema_upgraded()

        # Create account
        from treeline.domain import Account

        account = Account(
            id=uuid4(),
            name="Test Account",
            nickname=None,
            account_type="checking",
            currency="USD",
            balance=None,
            external_ids={},
            institution_name="Test Bank",
            institution_url=None,
            institution_domain=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await repo.add_account(account)

        # Create transaction with tags
        transaction = Transaction(
            id=uuid4(),
            account_id=account.id,
            external_ids={},
            amount=Decimal("-50.00"),
            description="Coffee Shop",
            transaction_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            posted_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            tags=("coffee", "food"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        await repo.add_transaction(transaction)

        # Clear the tags
        update_result = await repo.update_transaction_tags(str(transaction.id), [])

        assert update_result.success
        updated_transaction = update_result.data
        assert len(updated_transaction.tags) == 0

    finally:
        shutil.rmtree(test_dir)

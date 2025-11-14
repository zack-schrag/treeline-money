"""Unit tests for TaggingService."""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import UUID
from datetime import datetime, timezone

from treeline.abstractions import Repository, TagSuggester
from treeline.app.service import TaggingService
from treeline.domain import Transaction, Ok, Fail


class MockRepository(Repository):
    """Mock Repository for testing."""

    def __init__(self):
        self.get_transactions_for_tagging = AsyncMock()
        self.update_transaction_tags = AsyncMock()
        self.get_tag_statistics = AsyncMock()

    async def ensure_db_exists(self):
        pass

    async def ensure_schema_upgraded(self):
        pass

    async def add_account(self, account):
        pass

    async def add_transaction(self, transaction):
        pass

    async def add_balance(self, balance):
        pass

    async def bulk_upsert_accounts(self, accounts):
        pass

    async def bulk_upsert_transactions(self, transactions):
        pass

    async def bulk_add_balances(self, balances):
        pass

    async def update_account_by_id(self, account):
        pass

    async def get_accounts(self):
        pass

    async def get_account_by_id(self, account_id):
        pass

    async def get_account_by_external_id(self, external_id):
        pass

    async def get_transactions_by_external_ids(self, external_ids):
        pass

    async def get_balance_snapshots(self, account_id=None, date=None):
        pass

    async def execute_query(self, sql):
        pass

    async def get_schema_info(self):
        pass

    async def get_date_range_info(self):
        pass

    async def upsert_integration(self, integration_name, integration_options):
        pass

    async def list_integrations(self):
        pass

    async def get_integration_settings(self, integration_name):
        pass

    async def get_tag_statistics(self):
        pass

    async def get_transactions_for_tagging(self, filters={}, limit=100, offset=0):
        pass

    async def update_transaction_tags(self, transaction_id, tags):
        pass

    async def get_transaction_counts_by_fingerprint(self, fingerprints):
        pass

    async def get_transactions_by_account(
        self, account_id, order_by="transaction_date DESC"
    ):
        pass


class MockTagSuggester(TagSuggester):
    """Mock TagSuggester for testing."""

    def __init__(self):
        self.suggest_tags = AsyncMock()

    async def suggest_tags(self, transaction, limit=5):
        pass


@pytest.mark.asyncio
async def test_get_untagged_transactions():
    """Test getting untagged transactions."""
    mock_repository = MockRepository()
    mock_suggester = MockTagSuggester()

    # Create test transactions
    transactions = [
        Transaction(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            account_id=UUID("00000000-0000-0000-0000-000000000002"),
            external_ids={},
            amount=-50.0,
            description="Transaction 1",
            transaction_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            posted_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            tags=(),
            created_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
        ),
        Transaction(
            id=UUID("00000000-0000-0000-0000-000000000003"),
            account_id=UUID("00000000-0000-0000-0000-000000000002"),
            external_ids={},
            amount=-75.0,
            description="Transaction 2",
            transaction_date=datetime(2024, 10, 2, tzinfo=timezone.utc),
            posted_date=datetime(2024, 10, 2, tzinfo=timezone.utc),
            tags=(),
            created_at=datetime(2024, 10, 2, tzinfo=timezone.utc),
            updated_at=datetime(2024, 10, 2, tzinfo=timezone.utc),
        ),
    ]

    mock_repository.get_transactions_for_tagging.return_value = Ok(transactions)

    service = TaggingService(mock_repository, mock_suggester)

    result = await service.get_untagged_transactions(limit=100)

    assert result.success
    assert len(result.data) == 2
    mock_repository.get_transactions_for_tagging.assert_called_once_with(
        filters={"has_tags": False}, limit=100
    )


@pytest.mark.asyncio
async def test_get_transactions_for_tagging_with_filters():
    """Test getting transactions for tagging with custom filters."""
    mock_repository = MockRepository()
    mock_suggester = MockTagSuggester()

    transactions = [
        Transaction(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            account_id=UUID("00000000-0000-0000-0000-000000000002"),
            external_ids={},
            amount=-50.0,
            description="Transaction 1",
            transaction_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            posted_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            tags=("groceries",),
            created_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
        ),
    ]

    mock_repository.get_transactions_for_tagging.return_value = Ok(transactions)

    service = TaggingService(mock_repository, mock_suggester)

    custom_filters = {"has_tags": True}
    result = await service.get_transactions_for_tagging(
        filters=custom_filters, limit=50
    )

    assert result.success
    assert len(result.data) == 1
    mock_repository.get_transactions_for_tagging.assert_called_once_with(
        filters=custom_filters, limit=50, offset=0
    )


@pytest.mark.asyncio
async def test_update_transaction_tags():
    """Test updating transaction tags."""
    mock_repository = MockRepository()
    mock_suggester = MockTagSuggester()

    updated_transaction = Transaction(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        account_id=UUID("00000000-0000-0000-0000-000000000002"),
        external_ids={},
        amount=-50.0,
        description="Whole Foods",
        transaction_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
        posted_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
        tags=("groceries", "shopping"),
        created_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
    )

    mock_repository.update_transaction_tags.return_value = Ok(updated_transaction)

    transaction_id = "00000000-0000-0000-0000-000000000001"
    new_tags = ["groceries", "shopping"]

    service = TaggingService(mock_repository, mock_suggester)
    result = await service.update_transaction_tags(transaction_id, new_tags)

    assert result.success
    assert result.data.tags == ("groceries", "shopping")
    mock_repository.update_transaction_tags.assert_called_once_with(
        transaction_id, new_tags
    )


@pytest.mark.asyncio
async def test_update_transaction_tags_handles_failure():
    """Test that update_transaction_tags handles repository failures."""
    mock_repository = MockRepository()
    mock_suggester = MockTagSuggester()

    mock_repository.update_transaction_tags.return_value = Fail("Transaction not found")

    transaction_id = "00000000-0000-0000-0000-000000000001"
    new_tags = ["groceries"]

    service = TaggingService(mock_repository, mock_suggester)
    result = await service.update_transaction_tags(transaction_id, new_tags)

    assert not result.success
    assert "Transaction not found" in result.error


@pytest.mark.asyncio
async def test_get_suggested_tags():
    """Test getting suggested tags for a transaction."""
    mock_repository = MockRepository()
    mock_suggester = MockTagSuggester()

    suggested_tags = ["groceries", "shopping", "food"]
    mock_suggester.suggest_tags.return_value = Ok(suggested_tags)

    transaction = Transaction(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        account_id=UUID("00000000-0000-0000-0000-000000000002"),
        external_ids={},
        amount=-50.0,
        description="Whole Foods",
        transaction_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
        posted_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
        tags=(),
        created_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
    )

    service = TaggingService(mock_repository, mock_suggester)
    result = await service.get_suggested_tags(transaction, limit=3)

    assert result.success
    assert result.data == suggested_tags
    mock_suggester.suggest_tags.assert_called_once_with(transaction, limit=3)


@pytest.mark.asyncio
async def test_get_suggested_tags_handles_failure():
    """Test that get_suggested_tags handles suggester failures."""
    mock_repository = MockRepository()
    mock_suggester = MockTagSuggester()

    mock_suggester.suggest_tags.return_value = Fail("Failed to get statistics")

    transaction = Transaction(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        account_id=UUID("00000000-0000-0000-0000-000000000002"),
        external_ids={},
        amount=-50.0,
        description="Whole Foods",
        transaction_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
        posted_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
        tags=(),
        created_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
    )

    service = TaggingService(mock_repository, mock_suggester)
    result = await service.get_suggested_tags(transaction)

    assert not result.success
    assert "Failed to get statistics" in result.error

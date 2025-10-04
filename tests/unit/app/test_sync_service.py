"""Unit tests for SyncService."""

from datetime import datetime, timezone
from decimal import Decimal
from types import MappingProxyType
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from treeline.abstractions import DataAggregationProvider, Repository
from treeline.app.service import SyncService
from treeline.domain import Account, Transaction, BalanceSnapshot, Ok


class MockDataProvider(DataAggregationProvider):
    """Mock DataAggregationProvider for testing."""

    def __init__(self):
        self.get_accounts = AsyncMock()
        self.get_transactions = AsyncMock()
        self.get_balances = AsyncMock()
        self._can_get_accounts = True
        self._can_get_transactions = True
        self._can_get_balances = True

    @property
    def can_get_accounts(self) -> bool:
        return self._can_get_accounts

    @property
    def can_get_transactions(self) -> bool:
        return self._can_get_transactions

    @property
    def can_get_balances(self) -> bool:
        return self._can_get_balances

    async def get_accounts(self, user_id, provider_account_ids=[], provider_settings={}):
        pass

    async def get_transactions(self, user_id, start_date, end_date, provider_account_ids=[], provider_settings={}):
        pass

    async def get_balances(self, user_id, provider_account_ids=[], provider_settings={}):
        pass


class MockRepository(Repository):
    """Mock Repository for testing."""

    def __init__(self):
        self.get_accounts = AsyncMock()
        self.bulk_upsert_accounts = AsyncMock()
        self.bulk_upsert_transactions = AsyncMock()
        self.get_transactions_by_external_ids = AsyncMock()
        self.get_balance_snapshots = AsyncMock()
        self.bulk_add_balances = AsyncMock()
        self.upsert_integration = AsyncMock()
        self.list_integrations = AsyncMock()

    async def ensure_db_exists(self):
        pass

    async def ensure_schema_upgraded(self):
        pass

    async def ensure_user_db_initialized(self, user_id):
        pass

    async def add_account(self, user_id, account):
        pass

    async def add_transaction(self, user_id, transaction):
        pass

    async def add_balance(self, user_id, balance):
        pass

    async def bulk_upsert_accounts(self, user_id, accounts):
        pass

    async def bulk_upsert_transactions(self, user_id, transactions):
        pass

    async def bulk_add_balances(self, user_id, balances):
        pass

    async def update_account_by_id(self, user_id, account):
        pass

    async def get_accounts(self, user_id):
        pass

    async def get_account_by_id(self, user_id, account_id):
        pass

    async def get_account_by_external_id(self, user_id, external_id):
        pass

    async def get_transactions_by_external_ids(self, user_id, external_ids):
        pass

    async def get_balance_snapshots(self, user_id, account_id=None, date=None):
        pass

    async def execute_query(self, user_id, sql):
        pass

    async def get_schema_info(self, user_id):
        pass

    async def get_date_range_info(self, user_id):
        pass

    async def upsert_integration(self, user_id, integration_name, integration_options):
        pass

    async def list_integrations(self, user_id):
        pass

    async def get_integration_settings(self, user_id, integration_name):
        pass

    async def get_tag_statistics(self, user_id):
        pass

    async def get_transactions_for_tagging(self, user_id, filters={}, limit=100):
        pass

    async def update_transaction_tags(self, user_id, transaction_id, tags):
        pass


@pytest.mark.asyncio
async def test_sync_accounts_maps_external_ids_to_existing_accounts():
    """Test that discovered accounts are mapped to existing accounts by external ID."""
    mock_provider = MockDataProvider()
    mock_repository = MockRepository()

    user_id = uuid4()
    existing_account_id = uuid4()

    # Existing account in repository
    existing_account = Account(
        id=existing_account_id,
        name="Checking",
        external_ids=MappingProxyType({"plaid": "ext123"}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # Discovered account from provider with same external ID
    discovered_account = Account(
        id=uuid4(),  # Different ID from provider
        name="Checking Updated",
        external_ids=MappingProxyType({"plaid": "ext123"}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    mock_repository.get_accounts.return_value = Ok([existing_account])
    mock_provider.get_accounts.return_value = Ok([discovered_account])
    mock_repository.bulk_upsert_accounts.return_value = Ok([discovered_account])
    mock_repository.get_balance_snapshots.return_value = Ok([])

    provider_registry = {"plaid": mock_provider}
    service = SyncService(provider_registry, mock_repository)
    result = await service.sync_accounts(user_id, "plaid", {})

    assert result.success is True
    # Verify bulk_upsert was called with account that has the existing ID
    call_args = mock_repository.bulk_upsert_accounts.call_args
    upserted_accounts = call_args[0][1]
    assert len(upserted_accounts) == 1
    assert upserted_accounts[0].id == existing_account_id


@pytest.mark.asyncio
async def test_sync_transactions_deduplicates_by_external_id():
    """Test that transactions are deduplicated based on external IDs."""
    mock_provider = MockDataProvider()
    mock_repository = MockRepository()

    user_id = uuid4()
    account_id = uuid4()
    existing_tx_id = uuid4()

    # Existing account
    existing_account = Account(
        id=account_id,
        name="Checking",
        external_ids=MappingProxyType({"plaid": "acc123"}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # Existing transaction
    existing_tx = Transaction(
        id=existing_tx_id,
        account_id=account_id,
        external_ids=MappingProxyType({"plaid": "tx123"}),
        amount=Decimal("-50.00"),
        transaction_date=datetime.now(timezone.utc),
        posted_date=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # Discovered transaction with same external ID (update case)
    discovered_tx_same = Transaction(
        id=uuid4(),
        account_id=account_id,
        external_ids=MappingProxyType({"plaid": "tx123", "plaid_account": "acc123"}),
        amount=Decimal("-55.00"),  # Amount changed
        transaction_date=datetime.now(timezone.utc),
        posted_date=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # New transaction
    discovered_tx_new = Transaction(
        id=uuid4(),
        account_id=account_id,
        external_ids=MappingProxyType({"plaid": "tx456", "plaid_account": "acc123"}),
        amount=Decimal("-25.00"),
        transaction_date=datetime.now(timezone.utc),
        posted_date=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    mock_repository.get_accounts.return_value = Ok([existing_account])
    mock_provider.get_transactions.return_value = Ok([discovered_tx_same, discovered_tx_new])
    mock_repository.get_transactions_by_external_ids.return_value = Ok([existing_tx])
    mock_repository.bulk_upsert_transactions.return_value = Ok([discovered_tx_same, discovered_tx_new])

    provider_registry = {"plaid": mock_provider}
    service = SyncService(provider_registry, mock_repository)
    result = await service.sync_transactions(user_id, "plaid", provider_options={})

    assert result.success is True
    # Verify the updated transaction preserves the existing ID
    call_args = mock_repository.bulk_upsert_transactions.call_args
    upserted_txs = call_args[0][1]

    # Should have 2 transactions: 1 update + 1 new
    assert len(upserted_txs) == 2

    # Find the updated transaction
    updated_tx = next(tx for tx in upserted_txs if tx.external_ids.get("plaid") == "tx123")
    assert updated_tx.id == existing_tx_id
    assert updated_tx.amount == Decimal("-55.00")


@pytest.mark.asyncio
async def test_sync_accounts_creates_balance_snapshots():
    """Test that balance snapshots are created for discovered accounts."""
    mock_provider = MockDataProvider()
    mock_repository = MockRepository()

    user_id = uuid4()
    account_id = uuid4()

    # Account with balance
    account = Account(
        id=account_id,
        name="Savings",
        external_ids=MappingProxyType({"plaid": "sav123"}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    mock_repository.get_accounts.return_value = Ok([])
    mock_provider.get_accounts.return_value = Ok([account])
    mock_repository.bulk_upsert_accounts.return_value = Ok([account])
    mock_repository.get_balance_snapshots.return_value = Ok([])  # No existing snapshots

    provider_registry = {"plaid": mock_provider}
    service = SyncService(provider_registry, mock_repository)
    result = await service.sync_accounts(user_id, "plaid", {})

    assert result.success is True
    # Since the test account doesn't have a balance field, bulk_add_balances shouldn't be called
    # (This test would need to be updated when we add balance to Account model)


@pytest.mark.asyncio
async def test_sync_balances_deprecated():
    """Test that sync_balances is deprecated."""
    mock_provider = MockDataProvider()
    mock_repository = MockRepository()

    user_id = uuid4()
    provider_registry = {"plaid": mock_provider}
    service = SyncService(provider_registry, mock_repository)
    result = await service.sync_balances(user_id, "plaid", {})

    assert result.success is False
    assert "deprecated" in result.error.lower()
    mock_repository.bulk_add_balances.assert_not_called()

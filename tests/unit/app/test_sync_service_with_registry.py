"""Unit tests for SyncService with provider registry."""

from datetime import datetime, timezone
from types import MappingProxyType
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from treeline.abstractions import DataAggregationProvider, Repository
from treeline.app.service import SyncService
from treeline.domain import Account, Ok


class MockPlaidProvider(DataAggregationProvider):
    """Mock Plaid provider for testing."""

    def __init__(self):
        self.get_accounts = AsyncMock()
        self.get_transactions = AsyncMock()
        self.get_balances = AsyncMock()

    @property
    def can_get_accounts(self) -> bool:
        return True

    @property
    def can_get_transactions(self) -> bool:
        return True

    @property
    def can_get_balances(self) -> bool:
        return True

    async def get_accounts(self, provider_account_ids=[], provider_settings={}):
        pass

    async def get_transactions(
        self,
        start_date,
        end_date,
        provider_account_ids=[],
        provider_settings={},
    ):
        pass

    async def get_balances(self, provider_account_ids=[], provider_settings={}):
        pass


class MockSimpleFinProvider(DataAggregationProvider):
    """Mock SimpleFIN provider for testing."""

    def __init__(self):
        self.get_accounts = AsyncMock()
        self.get_transactions = AsyncMock()
        self.get_balances = AsyncMock()

    @property
    def can_get_accounts(self) -> bool:
        return True

    @property
    def can_get_transactions(self) -> bool:
        return True

    @property
    def can_get_balances(self) -> bool:
        return False

    async def get_accounts(self, provider_account_ids=[], provider_settings={}):
        pass

    async def get_transactions(
        self,
        start_date,
        end_date,
        provider_account_ids=[],
        provider_settings={},
    ):
        pass

    async def get_balances(self, provider_account_ids=[], provider_settings={}):
        pass


class MockRepository(Repository):
    """Mock Repository for testing."""

    def __init__(self):
        self.get_accounts = AsyncMock()
        self.bulk_upsert_accounts = AsyncMock()

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

    async def get_transactions_for_tagging(self, filters={}, limit=100):
        pass

    async def update_transaction_tags(self, transaction_id, tags):
        pass

    async def get_transaction_counts_by_fingerprint(self, fingerprints):
        pass

    async def get_transactions_by_account(
        self, account_id, order_by="transaction_date DESC"
    ):
        pass


@pytest.mark.asyncio
async def test_sync_service_uses_correct_provider_for_integration():
    """Test that SyncService selects the correct provider based on integration name."""
    mock_plaid_provider = MockPlaidProvider()
    mock_simplefin_provider = MockSimpleFinProvider()
    mock_repository = MockRepository()

    # Register providers
    provider_registry = {
        "plaid": mock_plaid_provider,
        "simplefin": mock_simplefin_provider,
    }

    account = Account(
        id=uuid4(),
        name="Checking",
        external_ids=MappingProxyType({"plaid": "acc123"}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    mock_repository.get_accounts.return_value = Ok([])
    mock_plaid_provider.get_accounts.return_value = Ok([account])
    mock_repository.bulk_upsert_accounts.return_value = Ok([account])

    # Create service with provider registry
    service = SyncService(provider_registry, mock_repository, Mock())
    result = await service.sync_accounts("plaid", {})

    assert result.success is True
    # Verify the Plaid provider was called, not SimpleFIN
    mock_plaid_provider.get_accounts.assert_called_once()
    mock_simplefin_provider.get_accounts.assert_not_called()


@pytest.mark.asyncio
async def test_sync_service_returns_error_for_unknown_integration():
    """Test that SyncService returns error for unknown integration name."""
    mock_plaid_provider = MockPlaidProvider()
    mock_repository = MockRepository()

    provider_registry = {
        "plaid": mock_plaid_provider,
    }

    service = SyncService(provider_registry, mock_repository, Mock())
    result = await service.sync_accounts("unknown_provider", {})

    assert result.success is False
    assert "Unknown integration" in result.error or "not found" in result.error.lower()
    mock_plaid_provider.get_accounts.assert_not_called()


@pytest.mark.asyncio
async def test_sync_service_uses_simplefin_for_simplefin_integration():
    """Test that SimpleFIN provider is used when integration_name is 'simplefin'."""
    mock_plaid_provider = MockPlaidProvider()
    mock_simplefin_provider = MockSimpleFinProvider()
    mock_repository = MockRepository()

    provider_registry = {
        "plaid": mock_plaid_provider,
        "simplefin": mock_simplefin_provider,
    }

    account = Account(
        id=uuid4(),
        name="Savings",
        external_ids=MappingProxyType({"simplefin": "sfin123"}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    mock_repository.get_accounts.return_value = Ok([])
    mock_simplefin_provider.get_accounts.return_value = Ok([account])
    mock_repository.bulk_upsert_accounts.return_value = Ok([account])

    service = SyncService(provider_registry, mock_repository, Mock())
    result = await service.sync_accounts("simplefin", {})

    assert result.success is True
    # Verify SimpleFIN provider was called, not Plaid
    mock_simplefin_provider.get_accounts.assert_called_once()
    mock_plaid_provider.get_accounts.assert_not_called()

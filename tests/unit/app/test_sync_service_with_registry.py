"""Unit tests for SyncService with provider registry."""

from datetime import datetime, timezone
from types import MappingProxyType
from unittest.mock import AsyncMock
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

    async def get_accounts(self, user_id, provider_account_ids=[], provider_settings={}):
        pass

    async def get_transactions(self, user_id, start_date, end_date, provider_account_ids=[], provider_settings={}):
        pass

    async def get_balances(self, user_id, provider_account_ids=[], provider_settings={}):
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

    user_id = uuid4()
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
    service = SyncService(provider_registry, mock_repository)
    result = await service.sync_accounts(user_id, "plaid", {})

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

    user_id = uuid4()
    service = SyncService(provider_registry, mock_repository)
    result = await service.sync_accounts(user_id, "unknown_provider", {})

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

    user_id = uuid4()
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

    service = SyncService(provider_registry, mock_repository)
    result = await service.sync_accounts(user_id, "simplefin", {})

    assert result.success is True
    # Verify SimpleFIN provider was called, not Plaid
    mock_simplefin_provider.get_accounts.assert_called_once()
    mock_plaid_provider.get_accounts.assert_not_called()

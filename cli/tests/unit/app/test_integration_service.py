"""Unit tests for IntegrationService."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from treeline.abstractions import IntegrationProvider, Repository
from treeline.app.service import IntegrationService
from treeline.domain import Ok, Fail


class MockIntegrationProvider(IntegrationProvider):
    """Mock IntegrationProvider for testing."""

    def __init__(self):
        self.create_integration = AsyncMock()

    async def create_integration(self, integration_name, integration_options):
        pass


class MockRepository(Repository):
    """Mock Repository for testing."""

    def __init__(self):
        self.upsert_integration = AsyncMock()

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
async def test_create_integration_success():
    """Test successful integration creation."""
    mock_provider = MockIntegrationProvider()
    mock_repository = MockRepository()

    integration_settings = {"api_key": "test_key_123"}
    mock_provider.create_integration.return_value = Ok(integration_settings)

    service = IntegrationService(mock_provider, mock_repository)
    result = await service.create_integration("plaid", {"username": "testuser"})

    assert result.success is True
    assert result.data == integration_settings
    mock_provider.create_integration.assert_called_once_with(
        "plaid", {"username": "testuser"}
    )
    mock_repository.upsert_integration.assert_called_once_with(
        "plaid", integration_settings
    )


@pytest.mark.asyncio
async def test_create_integration_failure():
    """Test failed integration creation."""
    mock_provider = MockIntegrationProvider()
    mock_repository = MockRepository()

    mock_provider.create_integration.return_value = Fail("Invalid credentials")

    service = IntegrationService(mock_provider, mock_repository)
    result = await service.create_integration("plaid", {"username": "baduser"})

    assert result.success is False
    assert result.error == "Invalid credentials"
    mock_repository.upsert_integration.assert_not_called()


@pytest.mark.asyncio
async def test_create_integration_no_settings_returned():
    """Test integration creation when no settings are returned."""
    mock_provider = MockIntegrationProvider()
    mock_repository = MockRepository()

    mock_provider.create_integration.return_value = Ok(None)

    service = IntegrationService(mock_provider, mock_repository)
    result = await service.create_integration("simplefin", {})

    assert result.success is True
    assert result.data is None
    mock_repository.upsert_integration.assert_not_called()

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

    async def create_integration(self, user_id, integration_name, integration_options):
        pass


class MockRepository(Repository):
    """Mock Repository for testing."""

    def __init__(self):
        self.upsert_integration = AsyncMock()

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


@pytest.mark.asyncio
async def test_create_integration_success():
    """Test successful integration creation."""
    mock_provider = MockIntegrationProvider()
    mock_repository = MockRepository()

    integration_settings = {"api_key": "test_key_123"}
    mock_provider.create_integration.return_value = Ok(integration_settings)

    user_id = uuid4()
    service = IntegrationService(mock_provider, mock_repository)
    result = await service.create_integration(user_id, "plaid", {"username": "testuser"})

    assert result.success is True
    assert result.data == integration_settings
    mock_provider.create_integration.assert_called_once_with(user_id, "plaid", {"username": "testuser"})
    mock_repository.upsert_integration.assert_called_once_with(user_id, "plaid", integration_settings)


@pytest.mark.asyncio
async def test_create_integration_failure():
    """Test failed integration creation."""
    mock_provider = MockIntegrationProvider()
    mock_repository = MockRepository()

    mock_provider.create_integration.return_value = Fail("Invalid credentials")

    user_id = uuid4()
    service = IntegrationService(mock_provider, mock_repository)
    result = await service.create_integration(user_id, "plaid", {"username": "baduser"})

    assert result.success is False
    assert result.error == "Invalid credentials"
    mock_repository.upsert_integration.assert_not_called()


@pytest.mark.asyncio
async def test_create_integration_no_settings_returned():
    """Test integration creation when no settings are returned."""
    mock_provider = MockIntegrationProvider()
    mock_repository = MockRepository()

    mock_provider.create_integration.return_value = Ok(None)

    user_id = uuid4()
    service = IntegrationService(mock_provider, mock_repository)
    result = await service.create_integration(user_id, "simplefin", {})

    assert result.success is True
    assert result.data is None
    mock_repository.upsert_integration.assert_not_called()

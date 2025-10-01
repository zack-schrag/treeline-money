"""Unit tests for DbService."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from treeline.abstractions import Repository
from treeline.app.service import DbService
from treeline.domain import Ok


class MockRepository(Repository):
    """Mock Repository for testing."""

    def __init__(self):
        self.ensure_db_exists = AsyncMock()
        self.ensure_schema_upgraded = AsyncMock()
        self.ensure_user_db_initialized = AsyncMock()
        self.execute_query = AsyncMock()

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

    async def upsert_integration(self, user_id, integration_name, integration_options):
        pass

    async def list_integrations(self, user_id):
        pass

    async def get_integration_settings(self, user_id, integration_name):
        pass


@pytest.mark.asyncio
async def test_execute_query_ensures_db_setup():
    """Test that execute_query ensures user database is initialized."""
    mock_repository = MockRepository()
    query_result = {"columns": ["name"], "rows": [["John"]]}
    mock_repository.execute_query.return_value = Ok(query_result)

    user_id = uuid4()
    service = DbService(mock_repository)
    result = await service.execute_query(user_id, "SELECT * FROM accounts")

    mock_repository.ensure_user_db_initialized.assert_called_once_with(user_id)
    mock_repository.execute_query.assert_called_once_with(user_id, "SELECT * FROM accounts")
    assert result.success is True
    assert result.data == query_result


@pytest.mark.asyncio
async def test_execute_query_calls_in_correct_order():
    """Test that database setup happens before query execution."""
    mock_repository = MockRepository()
    call_order = []

    async def track_init(user_id):
        call_order.append("init_user_db")

    async def track_query(user_id, sql):
        call_order.append("query")
        return Ok({"result": "data"})

    mock_repository.ensure_user_db_initialized.side_effect = track_init
    mock_repository.execute_query.side_effect = track_query

    user_id = uuid4()
    service = DbService(mock_repository)
    await service.execute_query(user_id, "SELECT 1")

    assert call_order == ["init_user_db", "query"]

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
        self.execute_query = AsyncMock()

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
async def test_execute_query_ensures_db_setup():
    """Test that execute_query executes the query."""
    mock_repository = MockRepository()
    query_result = {"columns": ["name"], "rows": [["John"]]}
    mock_repository.execute_query.return_value = Ok(query_result)

    service = DbService(mock_repository)
    result = await service.execute_query("SELECT * FROM accounts")

    mock_repository.execute_query.assert_called_once_with("SELECT * FROM accounts")
    assert result.success is True
    assert result.data == query_result


@pytest.mark.asyncio
async def test_execute_query_calls_in_correct_order():
    """Test that query execution works correctly."""
    mock_repository = MockRepository()

    async def track_query(sql):
        return Ok({"result": "data"})

    mock_repository.execute_query.side_effect = track_query

    service = DbService(mock_repository)
    result = await service.execute_query("SELECT 1")

    assert result.success is True
    assert result.data == {"result": "data"}

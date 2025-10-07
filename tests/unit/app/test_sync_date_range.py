"""Unit tests for SyncService date range calculation."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from treeline.abstractions import Repository
from treeline.app.service import SyncService
from treeline.domain import Ok, Fail


class MockRepository(Repository):
    """Mock Repository for testing."""

    def __init__(self):
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

    async def upsert_integration(self, user_id, integration_name, integration_settings):
        pass

    async def list_integrations(self, user_id):
        pass

    async def execute_query(self, user_id, query, params=None):
        pass

    async def get_schema_info(self, user_id):
        pass

    async def get_date_range_info(self, user_id):
        pass

    async def get_integration_settings(self, user_id, integration_name):
        pass

    async def get_tag_statistics(self, user_id):
        pass

    async def get_transaction_counts_by_fingerprint(self, user_id, fingerprints):
        pass

    async def get_transactions_for_tagging(self, user_id, filters={}, limit=100, offset=0):
        pass

    async def update_transaction_tags(self, user_id, transaction_id, tags):
        pass


@pytest.mark.asyncio
async def test_calculate_sync_date_range_initial_sync_no_transactions():
    """Test that initial sync fetches 90 days when no transactions exist."""
    mock_repository = MockRepository()

    # Mock: no transactions in database
    mock_repository.execute_query.return_value = Ok(
        data={"rows": [[None]], "columns": ["max_date"]}
    )

    service = SyncService({}, mock_repository)
    user_id = uuid4()

    result = await service.calculate_sync_date_range(user_id)

    assert result.success
    assert result.data["sync_type"] == "initial"

    # Verify it fetches approximately 90 days (allow for small time difference)
    start_date = result.data["start_date"]
    end_date = result.data["end_date"]
    days_diff = (end_date - start_date).days
    assert 89 <= days_diff <= 91  # Allow for minor timing differences


@pytest.mark.asyncio
async def test_calculate_sync_date_range_incremental_with_existing_transactions():
    """Test that incremental sync starts from latest transaction minus 7 days."""
    mock_repository = MockRepository()

    # Mock: latest transaction is 30 days ago
    latest_transaction_date = datetime.now(timezone.utc) - timedelta(days=30)
    mock_repository.execute_query.return_value = Ok(
        data={"rows": [[latest_transaction_date]], "columns": ["max_date"]}
    )

    service = SyncService({}, mock_repository)
    user_id = uuid4()

    result = await service.calculate_sync_date_range(user_id)

    assert result.success
    assert result.data["sync_type"] == "incremental"

    # Verify start date is 7 days before latest transaction
    start_date = result.data["start_date"]
    expected_start = latest_transaction_date - timedelta(days=7)

    # Allow for small time differences (within 1 second)
    time_diff = abs((start_date - expected_start).total_seconds())
    assert time_diff < 1


@pytest.mark.asyncio
async def test_calculate_sync_date_range_fallback_on_query_failure():
    """Test that sync falls back to 90 days if query fails."""
    mock_repository = MockRepository()

    # Mock: query fails
    mock_repository.execute_query.return_value = Fail(
        error="Database error"
    )

    service = SyncService({}, mock_repository)
    user_id = uuid4()

    result = await service.calculate_sync_date_range(user_id)

    assert result.success
    assert result.data["sync_type"] == "initial"

    # Verify it fetches approximately 90 days
    start_date = result.data["start_date"]
    end_date = result.data["end_date"]
    days_diff = (end_date - start_date).days
    assert 89 <= days_diff <= 91


@pytest.mark.asyncio
async def test_calculate_sync_date_range_handles_empty_result_set():
    """Test that sync handles empty result set (no transactions)."""
    mock_repository = MockRepository()

    # Mock: empty result set
    mock_repository.execute_query.return_value = Ok(
        data={"rows": [], "columns": ["max_date"]}
    )

    service = SyncService({}, mock_repository)
    user_id = uuid4()

    result = await service.calculate_sync_date_range(user_id)

    assert result.success
    assert result.data["sync_type"] == "initial"

    # Verify it fetches approximately 90 days
    start_date = result.data["start_date"]
    end_date = result.data["end_date"]
    days_diff = (end_date - start_date).days
    assert 89 <= days_diff <= 91


@pytest.mark.asyncio
async def test_calculate_sync_date_range_handles_date_objects():
    """Test that incremental sync works when database returns date objects (not datetime)."""
    from datetime import date

    mock_repository = MockRepository()

    # Mock: latest transaction is a date object (as returned by DuckDB for DATE columns)
    latest_transaction_date = date.today() - timedelta(days=30)
    mock_repository.execute_query.return_value = Ok(
        data={"rows": [[latest_transaction_date]], "columns": ["max_date"]}
    )

    service = SyncService({}, mock_repository)
    user_id = uuid4()

    result = await service.calculate_sync_date_range(user_id)

    assert result.success
    assert result.data["sync_type"] == "incremental"

    # Verify start date is 7 days before latest transaction
    start_date = result.data["start_date"]
    # Convert date to datetime for comparison
    expected_start = datetime.combine(latest_transaction_date, datetime.min.time(), tzinfo=timezone.utc) - timedelta(days=7)

    # Allow for small time differences (within 1 second)
    time_diff = abs((start_date - expected_start).total_seconds())
    assert time_diff < 1

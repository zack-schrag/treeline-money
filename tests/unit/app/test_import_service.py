"""Unit tests for ImportService."""

import pytest
from unittest.mock import AsyncMock
from uuid import UUID, uuid4
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from types import MappingProxyType

from treeline.abstractions import Repository, DataAggregationProvider
from treeline.app.service import ImportService
from treeline.domain import Transaction, Ok, Fail


class MockRepository(Repository):
    """Mock Repository for testing."""

    def __init__(self):
        self.get_transaction_counts_by_fingerprint = AsyncMock()
        self.bulk_upsert_transactions = AsyncMock()
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

    async def get_transactions_for_tagging(
        self, user_id, filters={}, limit=100, offset=0
    ):
        pass

    async def update_transaction_tags(self, user_id, transaction_id, tags):
        pass

    async def get_transaction_counts_by_fingerprint(self, user_id, fingerprints):
        pass


class MockDataAggregationProvider(DataAggregationProvider):
    """Mock provider for testing."""

    def __init__(self):
        self.get_transactions = AsyncMock()

    @property
    def can_get_accounts(self) -> bool:
        return False

    @property
    def can_get_transactions(self) -> bool:
        return True

    @property
    def can_get_balances(self) -> bool:
        return False

    async def get_accounts(self, user_id, provider_settings=None):
        pass

    async def get_transactions(
        self,
        user_id,
        start_date,
        end_date,
        provider_account_ids=[],
        provider_settings=None,
    ):
        pass

    async def get_balances(
        self, user_id, provider_account_ids=[], provider_settings=None
    ):
        pass


@pytest.mark.asyncio
async def test_import_transactions_with_no_existing():
    """Test importing transactions when none exist (all should be imported)."""
    mock_repository = MockRepository()
    mock_provider = MockDataAggregationProvider()

    user_id = uuid4()
    account_id = uuid4()

    # Provider returns 3 transactions
    discovered_transactions = [
        Transaction(
            id=uuid4(),
            account_id=uuid4(),  # Will be remapped to target account
            amount=Decimal("10.00"),
            description="Coffee",
            transaction_date=date(2024, 10, 1),
            posted_date=date(2024, 10, 1),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Transaction(
            id=uuid4(),
            account_id=uuid4(),
            amount=Decimal("20.00"),
            description="Lunch",
            transaction_date=date(2024, 10, 2),
            posted_date=date(2024, 10, 2),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Transaction(
            id=uuid4(),
            account_id=uuid4(),
            amount=Decimal("30.00"),
            description="Dinner",
            transaction_date=date(2024, 10, 3),
            posted_date=date(2024, 10, 3),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    ]

    mock_provider.get_transactions.return_value = Ok(discovered_transactions)
    mock_repository.get_transaction_counts_by_fingerprint.return_value = Ok({})
    mock_repository.bulk_upsert_transactions.return_value = Ok([])

    provider_registry = {"csv": mock_provider}
    service = ImportService(mock_repository, provider_registry)

    result = await service.import_transactions(
        user_id=user_id,
        source_type="csv",
        account_id=account_id,
        source_options={"file_path": "/test.csv"},
    )

    assert result.success
    assert result.data["discovered"] == 3
    assert result.data["imported"] == 3
    assert result.data["skipped"] == 0

    # Verify transactions were remapped to target account
    call_args = mock_repository.bulk_upsert_transactions.call_args
    imported_txs = call_args[0][1]
    assert all(tx.account_id == account_id for tx in imported_txs)


@pytest.mark.asyncio
async def test_import_transactions_with_existing_duplicates():
    """Test importing transactions when some already exist (duplicates skipped)."""
    mock_repository = MockRepository()
    mock_provider = MockDataAggregationProvider()

    user_id = uuid4()
    account_id = uuid4()

    # Provider returns 3 identical transactions (same fingerprint)
    discovered_transactions = [
        Transaction(
            id=uuid4(),
            account_id=uuid4(),
            amount=Decimal("10.00"),
            description="Coffee at Starbucks",
            transaction_date=date(2024, 10, 1),
            posted_date=date(2024, 10, 1),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Transaction(
            id=uuid4(),
            account_id=uuid4(),
            amount=Decimal("10.00"),
            description="Coffee at Starbucks",
            transaction_date=date(2024, 10, 1),
            posted_date=date(2024, 10, 1),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Transaction(
            id=uuid4(),
            account_id=uuid4(),
            amount=Decimal("10.00"),
            description="Coffee at Starbucks",
            transaction_date=date(2024, 10, 1),
            posted_date=date(2024, 10, 1),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    ]

    mock_provider.get_transactions.return_value = Ok(discovered_transactions)

    # Remap to target account to get correct fingerprint (same way as ImportService)
    tx_dict = discovered_transactions[0].model_dump()
    tx_dict["account_id"] = account_id
    ext_ids = dict(tx_dict.get("external_ids", {}))
    ext_ids.pop("fingerprint", None)
    tx_dict["external_ids"] = ext_ids
    remapped = Transaction(**tx_dict)
    expected_fingerprint = remapped.external_ids["fingerprint"]

    # Simulate 2 existing transactions with this fingerprint
    mock_repository.get_transaction_counts_by_fingerprint.return_value = Ok(
        {expected_fingerprint: 2}
    )
    mock_repository.bulk_upsert_transactions.return_value = Ok([])

    provider_registry = {"csv": mock_provider}
    service = ImportService(mock_repository, provider_registry)

    result = await service.import_transactions(
        user_id=user_id,
        source_type="csv",
        account_id=account_id,
        source_options={"file_path": "/test.csv"},
    )

    assert result.success
    assert result.data["discovered"] == 3
    assert result.data["imported"] == 1  # 3 discovered - 2 existing = 1 imported
    assert result.data["skipped"] == 2


@pytest.mark.asyncio
async def test_import_transactions_all_duplicates():
    """Test importing when all transactions already exist (all skipped)."""
    mock_repository = MockRepository()
    mock_provider = MockDataAggregationProvider()

    user_id = uuid4()
    account_id = uuid4()

    discovered_transactions = [
        Transaction(
            id=uuid4(),
            account_id=uuid4(),
            amount=Decimal("10.00"),
            description="Coffee",
            transaction_date=date(2024, 10, 1),
            posted_date=date(2024, 10, 1),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    ]

    mock_provider.get_transactions.return_value = Ok(discovered_transactions)

    # Remap to get fingerprint (same way as ImportService)
    tx_dict = discovered_transactions[0].model_dump()
    tx_dict["account_id"] = account_id
    ext_ids = dict(tx_dict.get("external_ids", {}))
    ext_ids.pop("fingerprint", None)
    tx_dict["external_ids"] = ext_ids
    remapped = Transaction(**tx_dict)
    expected_fingerprint = remapped.external_ids["fingerprint"]

    # Simulate 1 existing transaction
    mock_repository.get_transaction_counts_by_fingerprint.return_value = Ok(
        {expected_fingerprint: 1}
    )

    provider_registry = {"csv": mock_provider}
    service = ImportService(mock_repository, provider_registry)

    result = await service.import_transactions(
        user_id=user_id,
        source_type="csv",
        account_id=account_id,
        source_options={"file_path": "/test.csv"},
    )

    assert result.success
    assert result.data["discovered"] == 1
    assert result.data["imported"] == 0
    assert result.data["skipped"] == 1

    # Verify no transactions were inserted
    mock_repository.bulk_upsert_transactions.assert_not_called()


@pytest.mark.asyncio
async def test_import_unknown_source_type():
    """Test importing with unknown source type returns error."""
    mock_repository = MockRepository()

    user_id = uuid4()
    account_id = uuid4()

    provider_registry = {"csv": MockDataAggregationProvider()}
    service = ImportService(mock_repository, provider_registry)

    result = await service.import_transactions(
        user_id=user_id,
        source_type="ynab",  # Not in registry
        account_id=account_id,
        source_options={},
    )

    assert not result.success
    assert "Unknown source type" in result.error


@pytest.mark.asyncio
async def test_import_provider_failure():
    """Test importing handles provider failures gracefully."""
    mock_repository = MockRepository()
    mock_provider = MockDataAggregationProvider()

    user_id = uuid4()
    account_id = uuid4()

    mock_provider.get_transactions.return_value = Fail("Failed to read CSV file")

    provider_registry = {"csv": mock_provider}
    service = ImportService(mock_repository, provider_registry)

    result = await service.import_transactions(
        user_id=user_id,
        source_type="csv",
        account_id=account_id,
        source_options={"file_path": "/test.csv"},
    )

    assert not result.success
    assert "Failed to read CSV file" in result.error


@pytest.mark.asyncio
async def test_import_mixed_fingerprints():
    """Test importing with multiple different fingerprints and varying existing counts."""
    mock_repository = MockRepository()
    mock_provider = MockDataAggregationProvider()

    user_id = uuid4()
    account_id = uuid4()

    # 2 coffee transactions (same fingerprint)
    # 3 lunch transactions (same fingerprint)
    # 1 dinner transaction (unique fingerprint)
    discovered_transactions = [
        Transaction(
            id=uuid4(),
            account_id=uuid4(),
            amount=Decimal("5.00"),
            description="Coffee",
            transaction_date=date(2024, 10, 1),
            posted_date=date(2024, 10, 1),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Transaction(
            id=uuid4(),
            account_id=uuid4(),
            amount=Decimal("5.00"),
            description="Coffee",
            transaction_date=date(2024, 10, 1),
            posted_date=date(2024, 10, 1),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Transaction(
            id=uuid4(),
            account_id=uuid4(),
            amount=Decimal("15.00"),
            description="Lunch",
            transaction_date=date(2024, 10, 2),
            posted_date=date(2024, 10, 2),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Transaction(
            id=uuid4(),
            account_id=uuid4(),
            amount=Decimal("15.00"),
            description="Lunch",
            transaction_date=date(2024, 10, 2),
            posted_date=date(2024, 10, 2),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Transaction(
            id=uuid4(),
            account_id=uuid4(),
            amount=Decimal("15.00"),
            description="Lunch",
            transaction_date=date(2024, 10, 2),
            posted_date=date(2024, 10, 2),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Transaction(
            id=uuid4(),
            account_id=uuid4(),
            amount=Decimal("30.00"),
            description="Dinner",
            transaction_date=date(2024, 10, 3),
            posted_date=date(2024, 10, 3),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    ]

    mock_provider.get_transactions.return_value = Ok(discovered_transactions)

    # Get fingerprints by remapping (same way as ImportService)
    def get_fingerprint(tx, target_account_id):
        tx_dict = tx.model_dump()
        tx_dict["account_id"] = target_account_id
        ext_ids = dict(tx_dict.get("external_ids", {}))
        ext_ids.pop("fingerprint", None)
        tx_dict["external_ids"] = ext_ids
        return Transaction(**tx_dict).external_ids["fingerprint"]

    coffee_fp = get_fingerprint(discovered_transactions[0], account_id)
    lunch_fp = get_fingerprint(discovered_transactions[2], account_id)
    dinner_fp = get_fingerprint(discovered_transactions[5], account_id)

    # 1 coffee exists (import 1 more)
    # 2 lunches exist (import 1 more)
    # 0 dinners exist (import 1)
    mock_repository.get_transaction_counts_by_fingerprint.return_value = Ok(
        {
            coffee_fp: 1,
            lunch_fp: 2,
            dinner_fp: 0,
        }
    )
    mock_repository.bulk_upsert_transactions.return_value = Ok([])

    provider_registry = {"csv": mock_provider}
    service = ImportService(mock_repository, provider_registry)

    result = await service.import_transactions(
        user_id=user_id,
        source_type="csv",
        account_id=account_id,
        source_options={"file_path": "/test.csv"},
    )

    assert result.success
    assert result.data["discovered"] == 6
    assert result.data["imported"] == 3  # 1 coffee + 1 lunch + 1 dinner
    assert result.data["skipped"] == 3  # 1 coffee + 2 lunches


@pytest.mark.asyncio
async def test_preview_csv_import_success():
    """Test previewing CSV import successfully."""
    mock_repository = MockRepository()

    preview_transactions = [
        Transaction(
            id=uuid4(),
            account_id=uuid4(),
            amount=Decimal("10.00"),
            description="Coffee",
            transaction_date=date(2024, 10, 1),
            posted_date=date(2024, 10, 1),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    ]

    class MockCSVProvider(MockDataAggregationProvider):
        def preview_transactions(
            self,
            file_path,
            column_mapping,
            date_format="auto",
            limit=5,
            flip_signs=False,
        ):
            from treeline.domain import Ok

            return Ok(preview_transactions)

    mock_csv_provider = MockCSVProvider()
    provider_registry = {"csv": mock_csv_provider}
    service = ImportService(mock_repository, provider_registry)

    result = await service.preview_csv_import(
        file_path="/test.csv",
        column_mapping={"date": "Date", "amount": "Amount"},
        date_format="auto",
        limit=5,
        flip_signs=False,
    )

    assert result.success
    assert len(result.data) == 1
    assert result.data[0].description == "Coffee"


@pytest.mark.asyncio
async def test_preview_csv_import_provider_failure():
    """Test previewing CSV import handles provider errors."""
    mock_repository = MockRepository()

    class MockCSVProvider(MockDataAggregationProvider):
        def preview_transactions(
            self,
            file_path,
            column_mapping,
            date_format="auto",
            limit=5,
            flip_signs=False,
        ):
            from treeline.domain import Fail

            return Fail("Invalid column mapping")

    mock_csv_provider = MockCSVProvider()
    provider_registry = {"csv": mock_csv_provider}
    service = ImportService(mock_repository, provider_registry)

    result = await service.preview_csv_import(
        file_path="/test.csv",
        column_mapping={"invalid": "columns"},
        date_format="auto",
        limit=5,
        flip_signs=False,
    )

    assert not result.success
    assert "Invalid column mapping" in result.error

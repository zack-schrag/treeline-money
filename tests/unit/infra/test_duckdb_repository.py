"""Unit tests for DuckDBRepository."""

import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from uuid import uuid4

import pytest
import pytest_asyncio

from treeline.domain import Account, BalanceSnapshot, Transaction
from treeline.infra.duckdb import DuckDBRepository


@pytest.fixture
def temp_db_dir():
    """Create a temporary directory for test databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest_asyncio.fixture
async def repository(temp_db_dir):
    """Create a DuckDBRepository with a temporary database."""
    db_file_path = temp_db_dir / "test.duckdb"
    repo = DuckDBRepository(str(db_file_path))
    await repo.ensure_schema_upgraded()
    return repo


@pytest.mark.asyncio
async def test_ensure_db_exists(repository):
    """Test that database directory is created."""
    result = await repository.ensure_db_exists()
    assert result.success is True


@pytest.mark.asyncio
async def test_add_account(repository):
    """Test adding a single account."""
    account = Account(
        id=uuid4(),
        name="Test Account",
        currency="USD",
        external_ids=MappingProxyType({"plaid": "acc123"}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await repository.add_account(account)
    assert result.success is True
    assert result.data.id == account.id
    assert result.data.name == account.name


@pytest.mark.asyncio
async def test_get_accounts(repository):
    """Test retrieving accounts."""

    account1 = Account(
        id=uuid4(),
        name="Account 1",
        currency="USD",
        external_ids=MappingProxyType({}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    account2 = Account(
        id=uuid4(),
        name="Account 2",
        currency="USD",
        external_ids=MappingProxyType({}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    await repository.add_account(account1)
    await repository.add_account(account2)

    result = await repository.get_accounts()
    assert result.success is True
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_bulk_upsert_accounts(repository):
    """Test bulk upserting accounts."""
    accounts = [
        Account(
            id=uuid4(),
            name=f"Account {i}",
            currency="USD",
            external_ids=MappingProxyType({}),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        for i in range(3)
    ]

    result = await repository.bulk_upsert_accounts(accounts)
    assert result.success is True
    assert len(result.data) == 3


@pytest.mark.asyncio
async def test_add_transaction(repository):
    """Test adding a transaction."""
    # First add an account
    account = Account(
        id=uuid4(),
        name="Test Account",
        currency="USD",
        external_ids=MappingProxyType({}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await repository.add_account(account)

    transaction = Transaction(
        id=uuid4(),
        account_id=account.id,
        amount=Decimal("-50.00"),
        description="Test transaction",
        external_ids=MappingProxyType({"plaid": "tx123"}),
        transaction_date=date.today(),
        posted_date=date.today(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await repository.add_transaction(transaction)
    assert result.success is True
    assert result.data.id == transaction.id
    assert result.data.amount == transaction.amount


@pytest.mark.asyncio
async def test_get_transactions_by_external_ids(repository):
    """Test retrieving transactions by external IDs."""
    account = Account(
        id=uuid4(),
        name="Test Account",
        currency="USD",
        external_ids=MappingProxyType({}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await repository.add_account(account)

    transaction = Transaction(
        id=uuid4(),
        account_id=account.id,
        amount=Decimal("-50.00"),
        description="Test transaction",
        external_ids=MappingProxyType({"plaid": "tx123"}),
        transaction_date=date.today(),
        posted_date=date.today(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await repository.add_transaction(transaction)

    result = await repository.get_transactions_by_external_ids([{"plaid": "tx123"}])
    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0].external_ids.get("plaid") == "tx123"


@pytest.mark.asyncio
async def test_add_balance_snapshot(repository):
    """Test adding a balance snapshot."""
    account = Account(
        id=uuid4(),
        name="Test Account",
        currency="USD",
        external_ids=MappingProxyType({}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await repository.add_account(account)

    balance = BalanceSnapshot(
        id=uuid4(),
        account_id=account.id,
        balance=Decimal("1000.00"),
        snapshot_time=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await repository.add_balance(balance)
    assert result.success is True
    assert result.data.balance == balance.balance


@pytest.mark.asyncio
async def test_upsert_integration(repository):
    """Test upserting integration settings."""
    result = await repository.upsert_integration(
        "plaid", {"access_token": "test_token"}
    )
    assert result.success is True


@pytest.mark.asyncio
async def test_list_integrations(repository):
    """Test listing integrations."""
    await repository.upsert_integration("plaid", {"access_token": "token1"})
    await repository.upsert_integration("simplefin", {"access_url": "url1"})

    result = await repository.list_integrations()
    assert result.success is True
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_execute_query(repository):
    """Test executing SQL query."""
    # Add an account
    account = Account(
        id=uuid4(),
        name="Test Account",
        currency="USD",
        external_ids=MappingProxyType({}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await repository.add_account(account)

    result = await repository.execute_query("SELECT COUNT(*) as count FROM accounts")
    assert result.success is True
    # Result format depends on implementation


@pytest.mark.asyncio
async def test_get_transaction_counts_by_fingerprint(repository):
    """Test getting transaction counts grouped by dedup_key."""
    # Create account
    account = Account(
        id=uuid4(),
        name="Test Account",
        currency="USD",
        external_ids=MappingProxyType({}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await repository.add_account(account)

    # Create transactions with different fingerprints
    fingerprint_a = "fingerprint:abc123"
    fingerprint_b = "fingerprint:def456"

    # 3 transactions with fingerprint_a
    for _ in range(3):
        tx = Transaction(
            id=uuid4(),
            account_id=account.id,
            amount=Decimal("10.00"),
            description="Test transaction A",
            transaction_date=date.today(),
            posted_date=date.today(),
            external_ids=MappingProxyType({"fingerprint": fingerprint_a}),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await repository.add_transaction(tx)

    # 2 transactions with fingerprint_b
    for _ in range(2):
        tx = Transaction(
            id=uuid4(),
            account_id=account.id,
            amount=Decimal("20.00"),
            description="Test transaction B",
            transaction_date=date.today(),
            posted_date=date.today(),
            external_ids=MappingProxyType({"fingerprint": fingerprint_b}),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await repository.add_transaction(tx)

    # Query for counts
    fingerprints = [fingerprint_a, fingerprint_b, "fingerprint:xyz999"]
    result = await repository.get_transaction_counts_by_fingerprint(fingerprints)

    assert result.success is True
    counts = result.data
    assert counts[fingerprint_a] == 3
    assert counts[fingerprint_b] == 2
    assert (
        counts.get("fingerprint:xyz999", 0) == 0
    )  # Non-existent fingerprint should return 0

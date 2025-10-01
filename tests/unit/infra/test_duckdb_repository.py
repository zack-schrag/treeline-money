"""Unit tests for DuckDBRepository."""

import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from uuid import uuid4

import pytest

from treeline.domain import Account, BalanceSnapshot, Transaction
from treeline.infra.duckdb import DuckDBRepository


@pytest.fixture
def temp_db_dir():
    """Create a temporary directory for test databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def repository(temp_db_dir):
    """Create a DuckDBRepository with a temporary database."""
    return DuckDBRepository(str(temp_db_dir))


@pytest.mark.asyncio
async def test_ensure_db_exists(repository):
    """Test that database directory is created."""
    result = await repository.ensure_db_exists()
    assert result.success is True


@pytest.mark.asyncio
async def test_ensure_user_db_initialized(repository):
    """Test that user database is initialized."""
    user_id = uuid4()
    result = await repository.ensure_user_db_initialized(user_id)
    assert result.success is True


@pytest.mark.asyncio
async def test_add_account(repository):
    """Test adding a single account."""
    user_id = uuid4()
    await repository.ensure_user_db_initialized(user_id)
    

    account = Account(
        id=uuid4(),
        name="Test Account",
        currency="USD",
        external_ids=MappingProxyType({"plaid": "acc123"}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await repository.add_account(user_id, account)
    assert result.success is True
    assert result.data.id == account.id
    assert result.data.name == account.name


@pytest.mark.asyncio
async def test_get_accounts(repository):
    """Test retrieving accounts."""
    user_id = uuid4()
    await repository.ensure_user_db_initialized(user_id)
    

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

    await repository.add_account(user_id, account1)
    await repository.add_account(user_id, account2)

    result = await repository.get_accounts(user_id)
    assert result.success is True
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_bulk_upsert_accounts(repository):
    """Test bulk upserting accounts."""
    user_id = uuid4()
    await repository.ensure_user_db_initialized(user_id)
    

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

    result = await repository.bulk_upsert_accounts(user_id, accounts)
    assert result.success is True
    assert len(result.data) == 3


@pytest.mark.asyncio
async def test_add_transaction(repository):
    """Test adding a transaction."""
    user_id = uuid4()
    await repository.ensure_user_db_initialized(user_id)
    

    # First add an account
    account = Account(
        id=uuid4(),
        name="Test Account",
        currency="USD",
        external_ids=MappingProxyType({}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await repository.add_account(user_id, account)

    transaction = Transaction(
        id=uuid4(),
        account_id=account.id,
        amount=Decimal("-50.00"),
        description="Test transaction",
        external_ids=MappingProxyType({"plaid": "tx123"}),
        transaction_date=datetime.now(timezone.utc),
        posted_date=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await repository.add_transaction(user_id, transaction)
    assert result.success is True
    assert result.data.id == transaction.id
    assert result.data.amount == transaction.amount


@pytest.mark.asyncio
async def test_get_transactions_by_external_ids(repository):
    """Test retrieving transactions by external IDs."""
    user_id = uuid4()
    await repository.ensure_user_db_initialized(user_id)
    

    account = Account(
        id=uuid4(),
        name="Test Account",
        currency="USD",
        external_ids=MappingProxyType({}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await repository.add_account(user_id, account)

    transaction = Transaction(
        id=uuid4(),
        account_id=account.id,
        amount=Decimal("-50.00"),
        description="Test transaction",
        external_ids=MappingProxyType({"plaid": "tx123"}),
        transaction_date=datetime.now(timezone.utc),
        posted_date=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await repository.add_transaction(user_id, transaction)

    result = await repository.get_transactions_by_external_ids(
        user_id, [{"plaid": "tx123"}]
    )
    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0].external_ids.get("plaid") == "tx123"


@pytest.mark.asyncio
async def test_add_balance_snapshot(repository):
    """Test adding a balance snapshot."""
    user_id = uuid4()
    await repository.ensure_user_db_initialized(user_id)
    

    account = Account(
        id=uuid4(),
        name="Test Account",
        currency="USD",
        external_ids=MappingProxyType({}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await repository.add_account(user_id, account)

    balance = BalanceSnapshot(
        id=uuid4(),
        account_id=account.id,
        balance=Decimal("1000.00"),
        snapshot_time=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    result = await repository.add_balance(user_id, balance)
    assert result.success is True
    assert result.data.balance == balance.balance


@pytest.mark.asyncio
async def test_upsert_integration(repository):
    """Test upserting integration settings."""
    user_id = uuid4()
    await repository.ensure_user_db_initialized(user_id)
    

    result = await repository.upsert_integration(
        user_id, "plaid", {"access_token": "test_token"}
    )
    assert result.success is True


@pytest.mark.asyncio
async def test_list_integrations(repository):
    """Test listing integrations."""
    user_id = uuid4()
    await repository.ensure_user_db_initialized(user_id)
    

    await repository.upsert_integration(user_id, "plaid", {"access_token": "token1"})
    await repository.upsert_integration(user_id, "simplefin", {"access_url": "url1"})

    result = await repository.list_integrations(user_id)
    assert result.success is True
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_execute_query(repository):
    """Test executing SQL query."""
    user_id = uuid4()
    await repository.ensure_user_db_initialized(user_id)
    

    # Add an account
    account = Account(
        id=uuid4(),
        name="Test Account",
        currency="USD",
        external_ids=MappingProxyType({}),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await repository.add_account(user_id, account)

    result = await repository.execute_query(user_id, "SELECT COUNT(*) as count FROM accounts")
    assert result.success is True
    # Result format depends on implementation

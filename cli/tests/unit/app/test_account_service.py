"""Unit tests for AccountService."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from treeline.domain import Account, BalanceSnapshot, Result
from treeline.app.service import AccountService


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    return Mock()


@pytest.fixture
def account_service(mock_repository):
    """Create an AccountService with mocked dependencies."""
    return AccountService(mock_repository)


@pytest.mark.asyncio
async def test_get_accounts_success(account_service, mock_repository):
    """Test get_accounts returns accounts successfully."""
    expected_accounts = [
        Account(
            id=uuid4(),
            name="Checking",
            nickname=None,
            account_type="checking",
            currency="USD",
            external_ids={},
            institution_name="Test Bank",
            institution_url=None,
            institution_domain=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    ]

    # Mock repository to return accounts
    mock_repository.get_accounts = AsyncMock(
        return_value=Result(success=True, data=expected_accounts)
    )

    # Call service method
    result = await account_service.get_accounts()

    # Verify
    assert result.success is True
    assert result.data == expected_accounts
    mock_repository.get_accounts.assert_called_once_with()


@pytest.mark.asyncio
async def test_get_accounts_failure(account_service, mock_repository):
    """Test get_accounts handles repository errors."""
    # Mock repository to return error
    mock_repository.get_accounts = AsyncMock(
        return_value=Result(success=False, error="Database error")
    )

    # Call service method
    result = await account_service.get_accounts()

    # Verify
    assert result.success is False
    assert result.error == "Database error"
    mock_repository.get_accounts.assert_called_once_with()


@pytest.mark.asyncio
async def test_create_account_success(account_service, mock_repository):
    """Test create_account creates a new account successfully."""
    # Setup
    account_name = "Discover Card"
    account_type = "credit"
    institution = "Discover"
    currency = "USD"

    # Mock repository add
    mock_repository.add_account = AsyncMock(
        return_value=Result(success=True, data=None)
    )

    # Call service method
    result = await account_service.create_account(
        name=account_name,
        account_type=account_type,
        institution=institution,
        currency=currency,
    )

    # Verify result
    assert result.success is True
    assert result.data is not None
    assert isinstance(result.data, Account)
    assert result.data.name == account_name
    assert result.data.account_type == account_type
    assert result.data.institution_name == institution
    assert result.data.currency == currency
    assert result.data.balance is None  # No balance provided

    # Verify repository was called once
    mock_repository.add_account.assert_called_once()
    # Verify the account passed to repository matches expectations
    call_args = mock_repository.add_account.call_args[0][0]
    assert isinstance(call_args, Account)
    assert call_args.name == account_name


@pytest.mark.asyncio
async def test_create_account_with_balance(account_service, mock_repository):
    """Test create_account creates account with optional balance."""
    # Setup
    balance = Decimal("1500.00")

    # Mock repository add
    mock_repository.add_account = AsyncMock(
        return_value=Result(success=True, data=None)
    )

    # Call service method
    result = await account_service.create_account(
        name="Savings Account", account_type="depository", balance=balance
    )

    # Verify
    assert result.success is True
    assert result.data.balance == balance


@pytest.mark.asyncio
async def test_create_account_accepts_any_type(account_service, mock_repository):
    """Test create_account accepts any string for account_type (no validation)."""
    # Mock repository add
    mock_repository.add_account = AsyncMock(
        return_value=Result(success=True, data=None)
    )

    # Call with non-standard account type
    result = await account_service.create_account(
        name="HSA Account", account_type="health_savings_account"
    )

    # Verify it's accepted (no validation)
    assert result.success is True
    assert result.data.account_type == "health_savings_account"


@pytest.mark.asyncio
async def test_create_account_repository_failure(account_service, mock_repository):
    """Test create_account handles repository errors."""
    # Mock repository to return error
    mock_repository.add_account = AsyncMock(
        return_value=Result(success=False, error="Database error")
    )

    # Call service method
    result = await account_service.create_account(
        name="Test Account", account_type="checking"
    )

    # Verify error is propagated
    assert result.success is False
    assert result.error == "Database error"


@pytest.mark.asyncio
async def test_update_account_type_success(account_service, mock_repository):
    """Test update_account_type updates an existing account's type."""
    # Setup existing account
    account_id = uuid4()
    existing_account = Account(
        id=account_id,
        name="Chase Freedom",
        account_type=None,  # No type set yet
        currency="USD",
        external_ids={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Mock repository get
    mock_repository.get_account_by_id = AsyncMock(
        return_value=Result(success=True, data=existing_account)
    )

    # Mock repository update
    mock_repository.update_account_by_id = AsyncMock(
        return_value=Result(success=True, data=None)
    )

    # Call service method
    result = await account_service.update_account_type(account_id, "credit")

    # Verify
    assert result.success is True
    assert result.data is not None
    assert isinstance(result.data, Account)
    assert result.data.id == account_id
    assert result.data.account_type == "credit"
    assert result.data.name == "Chase Freedom"  # Other fields preserved

    # Verify repository calls
    mock_repository.get_account_by_id.assert_called_once_with(account_id)
    mock_repository.update_account_by_id.assert_called_once()


@pytest.mark.asyncio
async def test_update_account_type_account_not_found(account_service, mock_repository):
    """Test update_account_type handles account not found."""
    account_id = uuid4()

    # Mock repository to return error (account not found)
    mock_repository.get_account_by_id = AsyncMock(
        return_value=Result(success=False, error="Account not found")
    )

    # Call service method
    result = await account_service.update_account_type(account_id, "credit")

    # Verify error
    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_update_account_type_repository_failure(account_service, mock_repository):
    """Test update_account_type handles repository update errors."""
    # Setup existing account
    account_id = uuid4()
    existing_account = Account(
        id=account_id,
        name="Test Account",
        account_type=None,
        currency="USD",
        external_ids={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Mock repository get success but update failure
    mock_repository.get_account_by_id = AsyncMock(
        return_value=Result(success=True, data=existing_account)
    )
    mock_repository.update_account_by_id = AsyncMock(
        return_value=Result(success=False, error="Database error")
    )

    # Call service method
    result = await account_service.update_account_type(account_id, "savings")

    # Verify error is propagated
    assert result.success is False
    assert result.error == "Database error"


@pytest.mark.asyncio
async def test_add_balance_snapshot_success(account_service, mock_repository):
    """Test add_balance_snapshot adds a new balance snapshot successfully."""
    # Setup
    account_id = uuid4()
    balance = Decimal("2500.75")
    snapshot_date = date(2025, 11, 15)

    # Mock account exists
    existing_account = Account(
        id=account_id,
        name="Checking",
        account_type="checking",
        currency="USD",
        external_ids={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_repository.get_account_by_id = AsyncMock(
        return_value=Result(success=True, data=existing_account)
    )

    # Mock no existing snapshots for this date
    mock_repository.get_balance_snapshots = AsyncMock(
        return_value=Result(success=True, data=[])
    )

    # Mock successful balance add
    mock_repository.add_balance = AsyncMock(
        return_value=Result(success=True, data=None)
    )

    # Call service method
    result = await account_service.add_balance_snapshot(
        account_id=account_id, balance=balance, snapshot_date=snapshot_date
    )

    # Verify result
    assert result.success is True
    assert result.data is not None
    assert isinstance(result.data, BalanceSnapshot)
    assert result.data.account_id == account_id
    assert result.data.balance == balance
    # Verify snapshot_time is midnight local time on the specified date (naive datetime)
    assert result.data.snapshot_time.year == 2025
    assert result.data.snapshot_time.month == 11
    assert result.data.snapshot_time.day == 15
    assert result.data.snapshot_time.hour == 0
    assert result.data.snapshot_time.minute == 0
    assert result.data.snapshot_time.tzinfo is None  # Naive = local time

    # Verify repository was called
    mock_repository.get_account_by_id.assert_called_once_with(account_id)
    mock_repository.get_balance_snapshots.assert_called_once_with(
        account_id=account_id, date="2025-11-15"
    )
    mock_repository.add_balance.assert_called_once()


@pytest.mark.asyncio
async def test_add_balance_snapshot_defaults_to_today(account_service, mock_repository):
    """Test add_balance_snapshot defaults to today when no date provided."""
    # Setup
    account_id = uuid4()
    balance = Decimal("1000.00")

    # Mock account exists
    existing_account = Account(
        id=account_id,
        name="Savings",
        account_type="savings",
        currency="USD",
        external_ids={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_repository.get_account_by_id = AsyncMock(
        return_value=Result(success=True, data=existing_account)
    )

    # Mock no existing snapshots
    mock_repository.get_balance_snapshots = AsyncMock(
        return_value=Result(success=True, data=[])
    )

    # Mock successful balance add
    mock_repository.add_balance = AsyncMock(
        return_value=Result(success=True, data=None)
    )

    # Call service method without snapshot_date
    result = await account_service.add_balance_snapshot(
        account_id=account_id, balance=balance
    )

    # Verify result uses current date
    assert result.success is True
    assert result.data.snapshot_time.date() == date.today()
    assert result.data.snapshot_time.tzinfo is None  # Naive = local time


@pytest.mark.asyncio
async def test_add_balance_snapshot_deduplication(account_service, mock_repository):
    """Test add_balance_snapshot skips if same balance already exists today."""
    # Setup
    account_id = uuid4()
    balance = Decimal("2500.75")
    snapshot_date = date(2025, 11, 15)

    # Mock account exists
    existing_account = Account(
        id=account_id,
        name="Checking",
        account_type="checking",
        currency="USD",
        external_ids={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_repository.get_account_by_id = AsyncMock(
        return_value=Result(success=True, data=existing_account)
    )

    # Mock existing snapshot with same balance
    existing_snapshot = BalanceSnapshot(
        id=uuid4(),
        account_id=account_id,
        balance=Decimal("2500.75"),  # Same balance
        snapshot_time=datetime(2025, 11, 15, 12, 0, 0),  # Naive = local time
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_repository.get_balance_snapshots = AsyncMock(
        return_value=Result(success=True, data=[existing_snapshot])
    )

    # Call service method
    result = await account_service.add_balance_snapshot(
        account_id=account_id, balance=balance, snapshot_date=snapshot_date
    )

    # Verify it skipped adding (deduplication)
    assert result.success is False
    assert "already exists" in result.error.lower()

    # Verify add_balance was NOT called
    mock_repository.add_balance.assert_not_called()


@pytest.mark.asyncio
async def test_add_balance_snapshot_different_balance_same_day(
    account_service, mock_repository
):
    """Test add_balance_snapshot adds new snapshot if balance is different."""
    # Setup
    account_id = uuid4()
    balance = Decimal("3000.00")  # Different from existing
    snapshot_date = date(2025, 11, 15)

    # Mock account exists
    existing_account = Account(
        id=account_id,
        name="Checking",
        account_type="checking",
        currency="USD",
        external_ids={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_repository.get_account_by_id = AsyncMock(
        return_value=Result(success=True, data=existing_account)
    )

    # Mock existing snapshot with DIFFERENT balance
    existing_snapshot = BalanceSnapshot(
        id=uuid4(),
        account_id=account_id,
        balance=Decimal("2500.75"),  # Different balance
        snapshot_time=datetime(2025, 11, 15, 12, 0, 0),  # Naive = local time
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_repository.get_balance_snapshots = AsyncMock(
        return_value=Result(success=True, data=[existing_snapshot])
    )

    # Mock successful balance add
    mock_repository.add_balance = AsyncMock(
        return_value=Result(success=True, data=None)
    )

    # Call service method
    result = await account_service.add_balance_snapshot(
        account_id=account_id, balance=balance, snapshot_date=snapshot_date
    )

    # Verify it added the new snapshot (different balance)
    assert result.success is True
    assert result.data.balance == Decimal("3000.00")

    # Verify add_balance WAS called
    mock_repository.add_balance.assert_called_once()


@pytest.mark.asyncio
async def test_add_balance_snapshot_account_not_found(account_service, mock_repository):
    """Test add_balance_snapshot handles account not found."""
    account_id = uuid4()
    balance = Decimal("1000.00")

    # Mock account not found
    mock_repository.get_account_by_id = AsyncMock(
        return_value=Result(success=False, error="Account not found")
    )

    # Call service method
    result = await account_service.add_balance_snapshot(
        account_id=account_id, balance=balance
    )

    # Verify error
    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_add_balance_snapshot_repository_failure(
    account_service, mock_repository
):
    """Test add_balance_snapshot handles repository add errors."""
    # Setup
    account_id = uuid4()
    balance = Decimal("1000.00")

    # Mock account exists
    existing_account = Account(
        id=account_id,
        name="Checking",
        account_type="checking",
        currency="USD",
        external_ids={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_repository.get_account_by_id = AsyncMock(
        return_value=Result(success=True, data=existing_account)
    )

    # Mock no existing snapshots
    mock_repository.get_balance_snapshots = AsyncMock(
        return_value=Result(success=True, data=[])
    )

    # Mock repository failure
    mock_repository.add_balance = AsyncMock(
        return_value=Result(success=False, error="Database error")
    )

    # Call service method
    result = await account_service.add_balance_snapshot(
        account_id=account_id, balance=balance
    )

    # Verify error is propagated
    assert result.success is False
    assert result.error == "Database error"

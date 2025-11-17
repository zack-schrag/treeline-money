"""Unit tests for AccountService."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from treeline.domain import Account, Result
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

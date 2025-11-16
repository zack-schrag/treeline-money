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

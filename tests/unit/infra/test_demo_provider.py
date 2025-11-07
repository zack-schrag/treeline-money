"""Unit tests for DemoDataProvider."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from treeline.infra.demo_provider import DemoDataProvider


@pytest.mark.asyncio
async def test_get_accounts_returns_demo_data():
    """Test that demo provider returns fake accounts without API calls."""
    provider = DemoDataProvider()
    user_id = uuid4()

    result = await provider.get_accounts(
        user_id, provider_account_ids=[], provider_settings={}
    )

    assert result.success is True
    accounts = result.data
    assert len(accounts) > 0  # Should return at least one demo account

    # Verify account structure
    for account in accounts:
        assert account.name is not None
        assert account.currency == "USD"
        assert account.balance is not None
        assert account.institution_name is not None
        # Demo provider uses 'demo' as the external ID key
        assert "demo" in account.external_ids


@pytest.mark.asyncio
async def test_get_transactions_returns_demo_data():
    """Test that demo provider returns fake transactions."""
    provider = DemoDataProvider()
    user_id = uuid4()
    start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

    result = await provider.get_transactions(
        user_id,
        start_date,
        end_date,
        provider_account_ids=[],
        provider_settings={},
    )

    assert result.success is True
    transactions_with_accounts = result.data
    assert len(transactions_with_accounts) > 0  # Should return demo transactions

    # Verify transaction structure (SimpleFIN format: tuples of (account_id, transaction))
    for item in transactions_with_accounts:
        assert isinstance(item, tuple)
        account_id, transaction = item
        assert isinstance(account_id, str)
        assert transaction.amount is not None
        assert transaction.description is not None
        # Demo provider uses 'demo' as the external ID key
        assert "demo" in transaction.external_ids


@pytest.mark.asyncio
async def test_create_integration_succeeds_without_real_token():
    """Test that demo integration setup works without real credentials."""
    provider = DemoDataProvider()
    user_id = uuid4()

    result = await provider.create_integration(
        user_id, "simplefin", {"setupToken": "demo-token"}
    )

    assert result.success is True
    assert "accessUrl" in result.data
    # Demo access URL should indicate it's fake
    assert "demo" in result.data["accessUrl"].lower()


@pytest.mark.asyncio
async def test_get_accounts_filters_by_account_ids():
    """Test that account filtering works with demo data."""
    provider = DemoDataProvider()
    user_id = uuid4()

    # Get all accounts first
    all_accounts_result = await provider.get_accounts(
        user_id, provider_account_ids=[], provider_settings={}
    )
    all_accounts = all_accounts_result.data

    if len(all_accounts) > 0:
        # Filter by first account ID
        first_account_id = all_accounts[0].external_ids["demo"]

        filtered_result = await provider.get_accounts(
            user_id, provider_account_ids=[first_account_id], provider_settings={}
        )

        assert filtered_result.success is True
        filtered_accounts = filtered_result.data
        assert len(filtered_accounts) == 1
        assert filtered_accounts[0].external_ids["demo"] == first_account_id


@pytest.mark.asyncio
async def test_get_transactions_filters_by_date_range():
    """Test that transactions are filtered by date range."""
    provider = DemoDataProvider()
    user_id = uuid4()

    # Get transactions for a narrow date range
    start_date = datetime(2025, 1, 15, tzinfo=timezone.utc)
    end_date = datetime(2025, 1, 16, tzinfo=timezone.utc)

    result = await provider.get_transactions(
        user_id,
        start_date,
        end_date,
        provider_account_ids=[],
        provider_settings={},
    )

    assert result.success is True
    transactions_with_accounts = result.data

    # Verify all transactions are within date range
    for _, transaction in transactions_with_accounts:
        tx_datetime = datetime.combine(
            transaction.transaction_date, datetime.min.time()
        ).replace(tzinfo=timezone.utc)
        assert start_date <= tx_datetime <= end_date


@pytest.mark.asyncio
async def test_demo_provider_properties():
    """Test that demo provider reports correct capabilities."""
    provider = DemoDataProvider()

    assert provider.can_get_accounts is True
    assert provider.can_get_transactions is True
    assert provider.can_get_balances is True


@pytest.mark.asyncio
async def test_demo_provider_works_for_any_integration():
    """Test that demo provider can simulate any integration (not just SimpleFIN)."""
    provider = DemoDataProvider()
    user_id = uuid4()

    # Should work for "simplefin"
    result = await provider.create_integration(
        user_id, "simplefin", {"setupToken": "token"}
    )
    assert result.success is True

    # Should work for any integration name
    result = await provider.create_integration(
        user_id, "plaid", {"some_option": "value"}
    )
    assert result.success is True

    # Should work for csv (even though csv doesn't normally support integration setup)
    result = await provider.create_integration(user_id, "csv", {})
    assert result.success is True

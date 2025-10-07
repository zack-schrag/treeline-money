"""Unit tests for tag command display logic."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from treeline.domain import Transaction, Account


def test_transaction_has_account_id():
    """Test that Transaction model has account_id field."""
    txn = Transaction(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        account_id=UUID("00000000-0000-0000-0000-000000000002"),
        external_ids={},
        amount=Decimal("-50.00"),
        description="Test transaction",
        transaction_date=datetime(2024, 10, 1, tzinfo=timezone.utc).date(),
        posted_date=datetime(2024, 10, 1, tzinfo=timezone.utc).date(),
        tags=(),
        created_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
    )

    assert txn.account_id == UUID("00000000-0000-0000-0000-000000000002")


def test_account_mapping_creation():
    """Test that we can create a mapping of account IDs to names."""
    accounts = [
        Account(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Checking Account",
            nickname=None,
            account_type="checking",
            currency="USD",
            external_ids={},
            institution_name="Bank of America",
            institution_url=None,
            institution_domain=None,
            created_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
        ),
        Account(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            name="Savings Account",
            nickname="Emergency Fund",
            account_type="savings",
            currency="USD",
            external_ids={},
            institution_name="Chase",
            institution_url=None,
            institution_domain=None,
            created_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
        ),
    ]

    # Create mapping
    account_map = {acc.id: acc.nickname or acc.name for acc in accounts}

    assert account_map[UUID("00000000-0000-0000-0000-000000000001")] == "Checking Account"
    assert account_map[UUID("00000000-0000-0000-0000-000000000002")] == "Emergency Fund"

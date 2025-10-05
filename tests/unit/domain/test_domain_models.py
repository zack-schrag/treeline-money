from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from treeline.domain import Account, BalanceSnapshot, Transaction


def _tz_now() -> datetime:
    return datetime.now(timezone.utc)


def test_account_fields_align_with_schema() -> None:
    created_at = datetime(2024, 1, 1, 8, 30, tzinfo=timezone(timedelta(hours=-5)))
    updated_at = _tz_now()

    account = Account(
        id=uuid4(),
        name=" Checking ",
        nickname=" Main ",
        account_type="checking",
        currency="usd",
        external_ids={"simplefin": "abc"},
        institution_name=" Treeline Bank ",
        institution_url="https://treeline.money",
        institution_domain="treeline.money",
        created_at=created_at,
        updated_at=updated_at,
    )

    assert account.name == "Checking"
    assert account.nickname == "Main"
    assert account.currency == "USD"
    assert dict(account.external_ids) == {"simplefin": "abc"}
    assert account.institution_name == "Treeline Bank"
    assert account.created_at.tzinfo == timezone.utc
    assert account.created_at == created_at.astimezone(timezone.utc)

    with pytest.raises(ValidationError):
        Account(
            id=uuid4(),
            name=" ",
            currency="USD",
            created_at=_tz_now(),
            updated_at=_tz_now(),
        )

    with pytest.raises(ValidationError):
        Account(
            id=uuid4(),
            name="Checking",
            currency="USD",
            created_at=datetime.now(),
            updated_at=_tz_now(),
        )


def test_transaction_normalizes_amount_and_tags() -> None:
    account_id: UUID = uuid4()
    transaction = Transaction(
        id=uuid4(),
        account_id=account_id,
        amount="123.45",
        description=" Grocery run ",
        external_ids={"simplefin": "txn-1"},
        transaction_date=_tz_now(),
        posted_date=_tz_now(),
        created_at=_tz_now(),
        updated_at=_tz_now(),
        tags=[" groceries ", "Fuel", "groceries"],
    )

    assert transaction.amount == Decimal("123.45")
    assert transaction.description == "Grocery run"
    assert transaction.tags == ("groceries", "Fuel")
    assert dict(transaction.external_ids) == {"simplefin": "txn-1"}

    # Zero-amount transactions are valid (transfers, pending, corrections, etc.)
    zero_amount_transaction = Transaction(
        id=uuid4(),
        account_id=account_id,
        amount="0",
        description="Transfer",
        transaction_date=_tz_now(),
        posted_date=_tz_now(),
        created_at=_tz_now(),
        updated_at=_tz_now(),
    )
    assert zero_amount_transaction.amount == Decimal("0")

    with pytest.raises(ValidationError):
        Transaction(
            id=uuid4(),
            account_id=account_id,
            amount="10.00",
            description="Valid",
            transaction_date=_tz_now(),
            posted_date=datetime.now(),
            created_at=_tz_now(),
            updated_at=_tz_now(),
        )


def test_balance_snapshot_requires_timezone_aware_datetime() -> None:
    account_id = uuid4()
    snapshot = BalanceSnapshot(
        id=uuid4(),
        account_id=account_id,
        snapshot_time=_tz_now(),
        balance="1000.50",
        created_at=_tz_now(),
        updated_at=_tz_now(),
    )

    assert snapshot.balance == Decimal("1000.50")
    assert snapshot.snapshot_time.tzinfo == timezone.utc

    with pytest.raises(ValidationError):
        BalanceSnapshot(
            id=uuid4(),
            account_id=account_id,
            snapshot_time=datetime.now(),
            balance="1000.50",
            created_at=_tz_now(),
            updated_at=_tz_now(),
        )


def test_transaction_auto_generates_dedup_key() -> None:
    """Test that Transaction automatically generates dedup_key."""
    account_id = uuid4()

    # Create transaction without providing dedup_key
    tx = Transaction(
        id=uuid4(),
        account_id=account_id,
        amount=Decimal("25.50"),
        description="Coffee at Starbucks",
        transaction_date=datetime(2025, 10, 4, 10, 30, tzinfo=timezone.utc),
        posted_date=datetime(2025, 10, 4, 10, 30, tzinfo=timezone.utc),
        created_at=_tz_now(),
        updated_at=_tz_now(),
    )

    # dedup_key should be auto-generated
    assert tx.dedup_key
    assert tx.dedup_key.startswith("fingerprint:")

    # Same transaction data should generate same fingerprint
    tx2 = Transaction(
        id=uuid4(),  # Different ID
        account_id=account_id,  # Same account
        amount=Decimal("25.50"),  # Same amount
        description="Coffee at Starbucks",  # Same description
        transaction_date=datetime(2025, 10, 4, 10, 30, tzinfo=timezone.utc),  # Same date
        posted_date=datetime(2025, 10, 4, 10, 30, tzinfo=timezone.utc),
        created_at=_tz_now(),
        updated_at=_tz_now(),
    )

    assert tx.dedup_key == tx2.dedup_key

    # Different description should generate different fingerprint
    tx3 = Transaction(
        id=uuid4(),
        account_id=account_id,
        amount=Decimal("25.50"),
        description="Coffee at Peet's",  # Different description
        transaction_date=datetime(2025, 10, 4, 10, 30, tzinfo=timezone.utc),
        posted_date=datetime(2025, 10, 4, 10, 30, tzinfo=timezone.utc),
        created_at=_tz_now(),
        updated_at=_tz_now(),
    )

    assert tx.dedup_key != tx3.dedup_key


def test_transaction_dedup_key_strips_csv_noise() -> None:
    """Test that dedup_key normalization strips common CSV noise patterns.

    Verifies that 'null' literals and card number masks (XXXXXXXXXXXX1234)
    are stripped from descriptions during fingerprinting, allowing CSV and
    SimpleFIN formats to match when they represent the same transaction.
    """
    account_id = uuid4()
    tx_date = datetime(2025, 7, 9, 10, 30, tzinfo=timezone.utc)
    amount = Decimal("21.77")

    # CSV format: has "null" and card number mask
    tx_csv = Transaction(
        id=uuid4(),
        account_id=account_id,
        amount=amount,
        description="ACME STORE #123 SEATTLE WA null XXXXXXXXXXXX9876",
        transaction_date=tx_date,
        posted_date=tx_date,
        created_at=_tz_now(),
        updated_at=_tz_now(),
    )

    # SimpleFIN format: no "null" or card number (same vendor)
    tx_simplefin = Transaction(
        id=uuid4(),
        account_id=account_id,
        amount=amount,
        description="ACME STORE #123 SEATTLE WA",
        transaction_date=tx_date,
        posted_date=tx_date,
        created_at=_tz_now(),
        updated_at=_tz_now(),
    )

    # Should generate same dedup_key despite format differences
    # Both normalize to: "acmestore123seattlewa"
    assert tx_csv.dedup_key == tx_simplefin.dedup_key


def test_transaction_dedup_key_preserves_order_ids() -> None:
    """Test that order IDs are preserved in dedup_key (not stripped)."""
    account_id = uuid4()
    tx_date = datetime(2025, 7, 9, 10, 30, tzinfo=timezone.utc)
    amount = Decimal("21.77")

    # Same vendor, same day, same amount, different order IDs
    tx1 = Transaction(
        id=uuid4(),
        account_id=account_id,
        amount=amount,
        description="OnlineStore*ORDER5432 Seattle WA null XXXXXXXXXXXX5555",
        transaction_date=tx_date,
        posted_date=tx_date,
        created_at=_tz_now(),
        updated_at=_tz_now(),
    )

    tx2 = Transaction(
        id=uuid4(),
        account_id=account_id,
        amount=amount,
        description="OnlineStore*ORDER9876 Seattle WA null XXXXXXXXXXXX5555",
        transaction_date=tx_date,
        posted_date=tx_date,
        created_at=_tz_now(),
        updated_at=_tz_now(),
    )

    # Should have DIFFERENT dedup_keys because order IDs differ
    assert tx1.dedup_key != tx2.dedup_key


def test_transaction_dedup_key_ignores_sign_flip() -> None:
    """Test that dedup_key uses absolute amount (sign flips don't affect dedup)."""
    account_id = uuid4()
    tx_date = datetime(2025, 10, 4, 10, 30, tzinfo=timezone.utc)

    # Same transaction with different signs
    tx_positive = Transaction(
        id=uuid4(),
        account_id=account_id,
        amount=Decimal("25.50"),
        description="Coffee at Starbucks",
        transaction_date=tx_date,
        posted_date=tx_date,
        created_at=_tz_now(),
        updated_at=_tz_now(),
    )

    tx_negative = Transaction(
        id=uuid4(),
        account_id=account_id,
        amount=Decimal("-25.50"),  # Negative
        description="Coffee at Starbucks",
        transaction_date=tx_date,
        posted_date=tx_date,
        created_at=_tz_now(),
        updated_at=_tz_now(),
    )

    # Should generate same dedup_key (abs amount used)
    assert tx_positive.dedup_key == tx_negative.dedup_key

"""Demo data provider for testing without real API calls."""

from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Dict, List
from uuid import UUID, uuid4

from treeline.abstractions import DataAggregationProvider, IntegrationProvider
from treeline.domain import Account, BalanceSnapshot, Fail, Ok, Result, Transaction


class DemoDataProvider(DataAggregationProvider, IntegrationProvider):
    """Demo provider that returns fake data for testing and demonstrations.

    This provider can simulate any integration (SimpleFIN, Plaid, etc.) and returns
    realistic fake financial data without making any external API calls.
    """

    @property
    def can_get_accounts(self) -> bool:
        return True

    @property
    def can_get_transactions(self) -> bool:
        return True

    @property
    def can_get_balances(self) -> bool:
        return True

    def _generate_demo_accounts(self) -> List[Account]:
        """Generate realistic demo accounts."""
        now = datetime.now(timezone.utc)

        accounts = [
            Account(
                id=uuid4(),
                name="Demo Checking Account",
                account_type="depository",
                currency="USD",
                external_ids=MappingProxyType({"demo": "demo-checking-001"}),
                balance=Decimal("3247.85"),
                institution_name="Demo Bank",
                institution_url="https://demo-bank.example.com",
                institution_domain="demo-bank.example.com",
                created_at=now,
                updated_at=now,
            ),
            Account(
                id=uuid4(),
                name="Demo Savings Account",
                account_type="depository",
                currency="USD",
                external_ids=MappingProxyType({"demo": "demo-savings-001"}),
                balance=Decimal("15420.50"),
                institution_name="Demo Bank",
                institution_url="https://demo-bank.example.com",
                institution_domain="demo-bank.example.com",
                created_at=now,
                updated_at=now,
            ),
            Account(
                id=uuid4(),
                name="Demo Credit Card",
                account_type="credit",
                currency="USD",
                external_ids=MappingProxyType({"demo": "demo-credit-001"}),
                balance=Decimal("-842.32"),
                institution_name="Demo Credit Union",
                institution_url="https://demo-credit.example.com",
                institution_domain="demo-credit.example.com",
                created_at=now,
                updated_at=now,
            ),
        ]

        return accounts

    def _generate_demo_transactions(
        self, start_date: datetime, end_date: datetime, account_ids: List[str]
    ) -> List[tuple[str, Transaction]]:
        """Generate realistic demo transactions within date range.

        Returns:
            List of tuples (provider_account_id, transaction)
        """
        # Generate transactions for the past 180 days (6 months) if no date range specified
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=180)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        # Recurring transaction templates (monthly patterns)
        recurring_templates = [
            # Income - monthly
            ("demo-checking-001", "Direct Deposit - Payroll", Decimal("3500.00"), "income", 15),
            ("demo-checking-001", "Direct Deposit - Payroll", Decimal("3500.00"), "income", 30),
            # Utilities - monthly
            ("demo-checking-001", "PG&E Utility Bill", Decimal("-145.23"), "utilities", 5),
            ("demo-checking-001", "Water & Sewer", Decimal("-65.00"), "utilities", 10),
            # Subscriptions - monthly
            ("demo-checking-001", "Netflix", Decimal("-15.99"), "entertainment", 1),
            ("demo-credit-001", "Spotify Premium", Decimal("-9.99"), "entertainment", 1),
            ("demo-checking-001", "Gym Membership", Decimal("-49.99"), "health", 1),
            # Savings - monthly transfer
            ("demo-savings-001", "Transfer from Checking", Decimal("500.00"), "transfer", 16),
            ("demo-savings-001", "Interest Payment", Decimal("12.45"), "income", 28),
            # Credit card payment - monthly
            ("demo-credit-001", "Payment Thank You", Decimal("800.00"), "payment", 20),
        ]

        # Variable transaction templates (appear randomly throughout)
        variable_templates = [
            # Groceries (weekly-ish)
            ("demo-checking-001", "QFC Grocery Store", Decimal("-87.43"), "groceries"),
            ("demo-checking-001", "Whole Foods", Decimal("-112.56"), "groceries"),
            ("demo-checking-001", "Trader Joe's", Decimal("-68.24"), "groceries"),
            ("demo-checking-001", "Safeway", Decimal("-54.89"), "groceries"),
            # Coffee (frequent)
            ("demo-checking-001", "Starbucks", Decimal("-5.75"), "coffee"),
            ("demo-checking-001", "Starbucks", Decimal("-6.25"), "coffee"),
            # Gas (bi-weekly)
            ("demo-checking-001", "Shell Gas Station", Decimal("-52.00"), "transportation"),
            ("demo-checking-001", "Chevron", Decimal("-48.50"), "transportation"),
            # Transportation
            ("demo-checking-001", "Uber", Decimal("-23.40"), "transportation"),
            ("demo-checking-001", "Lyft", Decimal("-18.75"), "transportation"),
            # Shopping
            ("demo-checking-001", "Amazon.com", Decimal("-124.87"), "shopping"),
            ("demo-checking-001", "Target", Decimal("-67.92"), "shopping"),
            ("demo-credit-001", "Amazon.com", Decimal("-89.99"), "shopping"),
            # Dining
            ("demo-credit-001", "Restaurant - Italian", Decimal("-78.50"), "dining"),
            ("demo-credit-001", "Restaurant - Thai", Decimal("-45.00"), "dining"),
            ("demo-credit-001", "Restaurant - Fine Dining", Decimal("-125.75"), "dining"),
            # Travel (occasional)
            ("demo-credit-001", "Delta Airlines", Decimal("-450.00"), "travel"),
            ("demo-credit-001", "Hilton Hotel", Decimal("-285.60"), "travel"),
            # Electronics (rare)
            ("demo-credit-001", "Apple Store", Decimal("-199.00"), "electronics"),
        ]

        transactions = []
        now = datetime.now(timezone.utc)
        tx_counter = 0

        # Generate recurring transactions for each month in range
        current = start_date
        while current <= end_date:
            year, month = current.year, current.month
            days_in_month = (date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)) - date(year, month, 1)

            for account_id, description, amount, category, day_of_month in recurring_templates:
                if account_ids and account_id not in account_ids:
                    continue

                # Clamp day to valid range for this month
                actual_day = min(day_of_month, days_in_month.days)
                tx_date = date(year, month, actual_day)
                tx_datetime = datetime.combine(tx_date, datetime.min.time()).replace(tzinfo=timezone.utc)

                if tx_datetime < start_date or tx_datetime > end_date:
                    continue

                transaction = Transaction(
                    id=uuid4(),
                    account_id=UUID(int=0),
                    external_ids=MappingProxyType({"demo": f"demo-tx-{tx_counter:04d}"}),
                    amount=amount,
                    description=description,
                    transaction_date=tx_date,
                    posted_date=tx_date,
                    tags=tuple([category]) if category else tuple(),
                    created_at=now,
                    updated_at=now,
                )
                transactions.append((account_id, transaction))
                tx_counter += 1

            # Move to next month
            if month == 12:
                current = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                current = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        # Generate variable transactions spread throughout
        days_in_range = (end_date - start_date).days
        if days_in_range <= 0:
            days_in_range = 1

        # Each template appears multiple times
        for repeat in range(days_in_range // 7):  # Roughly weekly cycle
            for i, (account_id, description, amount, category) in enumerate(variable_templates):
                if account_ids and account_id not in account_ids:
                    continue

                # Space out with some randomness (using counter as pseudo-random)
                offset_days = ((repeat * len(variable_templates) + i) * 3) % days_in_range
                tx_date = (start_date + timedelta(days=offset_days)).date()

                if tx_date < start_date.date() or tx_date > end_date.date():
                    continue

                transaction = Transaction(
                    id=uuid4(),
                    account_id=UUID(int=0),
                    external_ids=MappingProxyType({"demo": f"demo-tx-{tx_counter:04d}"}),
                    amount=amount,
                    description=description,
                    transaction_date=tx_date,
                    posted_date=tx_date,
                    tags=tuple([category]) if category else tuple(),
                    created_at=now,
                    updated_at=now,
                )
                transactions.append((account_id, transaction))
                tx_counter += 1

        return transactions

    async def get_accounts(
        self,
        provider_account_ids: List[str] = [],
        provider_settings: Dict[str, Any] = {},
    ) -> Result[List[Account]]:
        """Get demo accounts."""
        accounts = self._generate_demo_accounts()

        # Filter by account IDs if specified
        if provider_account_ids:
            accounts = [
                acc
                for acc in accounts
                if acc.external_ids.get("demo") in provider_account_ids
            ]

        return Ok(accounts)

    async def get_transactions(
        self,
        start_date: datetime,
        end_date: datetime,
        provider_account_ids: List[str] = [],
        provider_settings: Dict[str, Any] = {},
    ) -> Result[List[tuple[str, Transaction]]]:
        """Get demo transactions."""
        transactions = self._generate_demo_transactions(
            start_date, end_date, provider_account_ids
        )

        return Ok(transactions)

    async def get_balances(
        self,
        provider_account_ids: List[str] = [],
        provider_settings: Dict[str, Any] = {},
    ) -> Result[List[BalanceSnapshot]]:
        """Get demo balance snapshots.

        NOTE: This method is deprecated. Balances are now returned as part of the
        Account model in get_accounts() and balance snapshots are created automatically
        by the sync service.
        """
        return Fail("get_balances is deprecated - balances are synced via get_accounts")

    async def create_integration(
        self, integration_name: str, integration_options: Dict[str, Any]
    ) -> Result[Dict[str, str]]:
        """Create demo integration (no real credentials needed)."""
        # Return fake credentials for any integration
        return Ok(
            {
                "accessUrl": "https://demo-provider.example.com/access/demo-user",
                "demo": "true",
            }
        )

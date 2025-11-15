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
                currency="USD",
                external_ids=MappingProxyType({"simplefin": "demo-checking-001"}),
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
                currency="USD",
                external_ids=MappingProxyType({"simplefin": "demo-savings-001"}),
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
                currency="USD",
                external_ids=MappingProxyType({"simplefin": "demo-credit-001"}),
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
        # Generate transactions for the past 90 days if no date range specified
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=90)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        # Transaction templates for realistic demo data
        transaction_templates = [
            # Checking account transactions
            ("demo-checking-001", "QFC Grocery Store", Decimal("-87.43"), "groceries"),
            ("demo-checking-001", "Starbucks", Decimal("-5.75"), "coffee"),
            (
                "demo-checking-001",
                "Shell Gas Station",
                Decimal("-52.00"),
                "transportation",
            ),
            ("demo-checking-001", "Netflix", Decimal("-15.99"), "entertainment"),
            (
                "demo-checking-001",
                "Direct Deposit - Payroll",
                Decimal("3500.00"),
                "income",
            ),
            ("demo-checking-001", "Amazon.com", Decimal("-124.87"), "shopping"),
            ("demo-checking-001", "PG&E Utility Bill", Decimal("-145.23"), "utilities"),
            ("demo-checking-001", "Target", Decimal("-67.92"), "shopping"),
            ("demo-checking-001", "Whole Foods", Decimal("-112.56"), "groceries"),
            ("demo-checking-001", "Uber", Decimal("-23.40"), "transportation"),
            # Credit card transactions
            ("demo-credit-001", "Delta Airlines", Decimal("-450.00"), "travel"),
            ("demo-credit-001", "Hilton Hotel", Decimal("-285.60"), "travel"),
            (
                "demo-credit-001",
                "Restaurant - Fine Dining",
                Decimal("-95.75"),
                "dining",
            ),
            ("demo-credit-001", "Apple Store", Decimal("-1299.00"), "electronics"),
            ("demo-credit-001", "Spotify Premium", Decimal("-9.99"), "entertainment"),
            ("demo-credit-001", "Payment Thank You", Decimal("500.00"), "payment"),
            # Savings account transactions (less frequent)
            (
                "demo-savings-001",
                "Transfer from Checking",
                Decimal("500.00"),
                "transfer",
            ),
            ("demo-savings-001", "Interest Payment", Decimal("12.45"), "income"),
        ]

        transactions = []
        now = datetime.now(timezone.utc)

        # Generate transactions spread across the date range
        days_in_range = (end_date - start_date).days
        if days_in_range <= 0:
            days_in_range = 1

        for i, (account_id, description, amount, category) in enumerate(
            transaction_templates
        ):
            # Filter by account IDs if specified
            if account_ids and account_id not in account_ids:
                continue

            # Space out transactions across the date range
            offset_days = (i * days_in_range) // len(transaction_templates)
            transaction_datetime = start_date + timedelta(days=offset_days)

            # Skip if outside date range
            if transaction_datetime < start_date or transaction_datetime > end_date:
                continue

            transaction = Transaction(
                id=uuid4(),
                account_id=UUID(int=0),  # Placeholder, will be mapped by service
                external_ids=MappingProxyType({"simplefin": f"demo-tx-{i:04d}"}),
                amount=amount,
                description=description,
                transaction_date=transaction_datetime.date(),
                posted_date=transaction_datetime.date(),
                tags=tuple([category]) if category else tuple(),
                created_at=now,
                updated_at=now,
            )

            transactions.append((account_id, transaction))

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

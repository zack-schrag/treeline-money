"""CSV file provider for importing transactions."""

import csv
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID, uuid4

from treeline.abstractions import DataAggregationProvider
from treeline.domain import Account, BalanceSnapshot, Fail, Ok, Result, Transaction


class CSVProvider(DataAggregationProvider):
    """CSV file implementation for data aggregation."""

    @property
    def can_get_accounts(self) -> bool:
        return False  # Accounts must be manually mapped

    @property
    def can_get_transactions(self) -> bool:
        return True

    @property
    def can_get_balances(self) -> bool:
        return False

    async def get_accounts(
        self,
        user_id: UUID,
        provider_account_ids: List[str] = [],
        provider_settings: Dict[str, Any] | None = None,
    ) -> Result[List[Account]]:
        """CSV provider does not support getting accounts."""
        return Fail("CSV provider does not support getting accounts")

    async def get_transactions(
        self,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
        provider_account_ids: List[str] = [],
        provider_settings: Dict[str, Any] | None = None,
    ) -> Result[List[Transaction]]:
        """Parse CSV file and return transactions."""
        if not provider_settings:
            return Fail("provider_settings is required")

        file_path = provider_settings.get("file_path")
        if not file_path:
            return Fail("file_path is required in provider_settings")

        column_mapping = provider_settings.get("column_mapping")
        if not column_mapping:
            return Fail("column_mapping is required in provider_settings")

        date_format = provider_settings.get("date_format", "auto")

        # Check if file exists
        path = Path(file_path)
        if not path.exists():
            return Fail(f"File not found: {file_path}")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                transactions = []

                for row in reader:
                    # Parse transaction from CSV row
                    tx_result = self._parse_transaction_row(
                        row, column_mapping, date_format, user_id
                    )
                    if not tx_result.success:
                        # Skip invalid rows but continue processing
                        continue

                    transactions.append(tx_result.data)

                return Ok(transactions)

        except Exception as e:
            return Fail(f"Failed to parse CSV file: {str(e)}")

    async def get_balances(
        self,
        user_id: UUID,
        provider_account_ids: List[str] = [],
        provider_settings: Dict[str, Any] | None = None,
    ) -> Result[List[BalanceSnapshot]]:
        """CSV provider does not support getting balances."""
        return Fail("CSV provider does not support getting balances")

    def _parse_transaction_row(
        self,
        row: Dict[str, str],
        column_mapping: Dict[str, str],
        date_format: str,
        user_id: UUID,
    ) -> Result[Transaction]:
        """Parse a single CSV row into a Transaction."""
        try:
            # Get column names from mapping
            date_col = column_mapping.get("date")
            description_col = column_mapping.get("description")
            amount_col = column_mapping.get("amount")
            posted_date_col = column_mapping.get("posted_date")

            if not date_col or not amount_col:
                return Fail("date and amount columns are required in column_mapping")

            # Parse date
            date_str = row.get(date_col, "").strip()
            if not date_str:
                return Fail("Missing date value")

            transaction_date = self._parse_date(date_str, date_format)
            if not transaction_date:
                return Fail(f"Failed to parse date: {date_str}")

            # Parse posted_date if provided
            if posted_date_col:
                posted_date_str = row.get(posted_date_col, "").strip()
                if posted_date_str:
                    posted_date = self._parse_date(posted_date_str, date_format)
                    if not posted_date:
                        posted_date = transaction_date
                else:
                    posted_date = transaction_date
            else:
                posted_date = transaction_date

            # Parse amount
            amount_str = row.get(amount_col, "").strip()
            if not amount_str:
                return Fail("Missing amount value")

            amount = self._parse_amount(amount_str)
            if amount is None:
                return Fail(f"Failed to parse amount: {amount_str}")

            # Parse description
            description = ""
            if description_col:
                description = row.get(description_col, "").strip()

            # Create transaction
            # Note: account_id will be set by ImportService when mapping to target account
            transaction = Transaction(
                id=uuid4(),
                account_id=uuid4(),  # Placeholder, will be replaced by ImportService
                amount=amount,
                description=description,
                transaction_date=transaction_date,
                posted_date=posted_date,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            return Ok(transaction)

        except Exception as e:
            return Fail(f"Failed to parse transaction row: {str(e)}")

    def _parse_date(self, date_str: str, date_format: str) -> datetime | None:
        """Parse date string with various format support."""
        if not date_str:
            return None

        # Try auto-detection if format is "auto"
        if date_format == "auto":
            formats = [
                "%Y-%m-%d",      # 2024-10-01
                "%m/%d/%Y",      # 10/01/2024
                "%d/%m/%Y",      # 01/10/2024
                "%Y/%m/%d",      # 2024/10/01
                "%m-%d-%Y",      # 10-01-2024
                "%d-%m-%Y",      # 01-10-2024
            ]
        else:
            # Map common format names to strftime formats
            format_map = {
                "YYYY-MM-DD": "%Y-%m-%d",
                "MM/DD/YYYY": "%m/%d/%Y",
                "DD/MM/YYYY": "%d/%m/%Y",
                "YYYY/MM/DD": "%Y/%m/%d",
            }
            fmt = format_map.get(date_format)
            if not fmt:
                return None
            formats = [fmt]

        # Try each format
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # Add timezone info
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        return None

    def _parse_amount(self, amount_str: str) -> Decimal | None:
        """Parse amount string, handling $ signs and commas."""
        if not amount_str:
            return None

        try:
            # Remove currency symbols and commas
            cleaned = amount_str.strip()
            cleaned = cleaned.replace("$", "")
            cleaned = cleaned.replace(",", "")
            cleaned = cleaned.replace(" ", "")

            # Handle parentheses notation for negative numbers: (100.00) -> -100.00
            if cleaned.startswith("(") and cleaned.endswith(")"):
                cleaned = "-" + cleaned[1:-1]

            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return None

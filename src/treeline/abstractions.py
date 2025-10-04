from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from treeline.domain import Account, BalanceSnapshot, Result, Transaction, User


class DataAggregationProvider(ABC):
    @property
    @abstractmethod
    def can_get_accounts(self) -> bool:
        pass

    @property
    @abstractmethod
    def can_get_transactions(self) -> bool:
        pass

    @property
    @abstractmethod
    def can_get_balances(self) -> bool:
        pass

    @abstractmethod
    async def get_accounts(self, user_id: UUID, provider_account_ids: List[str] = [], provider_settings: Dict[str, Any] = {}) -> Result[List[Account]]:
        pass

    @abstractmethod
    async def get_transactions(self, user_id: UUID, start_date: datetime, end_date: datetime, provider_account_ids: List[str] = [], provider_settings: Dict[str, Any] = {}) -> Result[List[Account]]:
        pass

    @abstractmethod
    async def get_balances(self, user_id: UUID, provider_account_ids: List[str] = [], provider_settings: Dict[str, Any] = {}) -> Result[List[Account]]:
        pass


class Repository(ABC):
    @abstractmethod
    async def ensure_db_exists(self) -> Result:
        """Ensure database file exists. Does not require user context."""
        pass

    @abstractmethod
    async def ensure_schema_upgraded(self) -> Result:
        """Ensure schema is up to date. Does not require user context."""
        pass

    @abstractmethod
    async def ensure_user_db_initialized(self, user_id: UUID) -> Result:
        """Ensure user-specific database setup is complete."""
        pass

    @abstractmethod
    async def add_account(self, user_id: UUID, account: Account) -> Result[Account]:
        pass

    @abstractmethod
    async def add_transaction(self, user_id: UUID, transaction: Transaction) -> Result[Transaction]:
        pass

    @abstractmethod
    async def add_balance(self, user_id: UUID, balance: BalanceSnapshot) -> Result[BalanceSnapshot]:
        pass

    @abstractmethod
    async def bulk_upsert_accounts(self, user_id: UUID, accounts: List[Account]) -> Result[List[Account]]:
        pass

    @abstractmethod
    async def bulk_upsert_transactions(self, user_id: UUID, transactions: List[Transaction]) -> Result[List[Transaction]]:
        pass

    @abstractmethod
    async def bulk_add_balances(self, user_id: UUID, balances: List[BalanceSnapshot]) -> Result[List[BalanceSnapshot]]:
        pass

    @abstractmethod
    async def update_account_by_id(self, user_id: UUID, account: Account) -> Result[Account]:
        pass

    @abstractmethod
    async def get_accounts(self, user_id: UUID) -> Result[List[Account]]:
        pass

    @abstractmethod
    async def get_account_by_id(self, user_id: UUID, account_id: UUID) -> Result[Account]:
        pass

    @abstractmethod
    async def get_account_by_external_id(self, user_id: UUID, external_id: str) -> Result[Account]:
        pass

    @abstractmethod
    async def get_transactions_by_external_ids(self, user_id: UUID, external_ids: List[Dict[str, str]]) -> Result[List[Transaction]]:
        pass

    @abstractmethod
    async def get_balance_snapshots(self, user_id: UUID, account_id: UUID | None = None, date: str | None = None) -> Result[List[BalanceSnapshot]]:
        pass

    @abstractmethod
    async def execute_query(self, user_id: UUID, sql: str) -> Result[Dict[str, Any]]:
        """
        Execute SQL query and return structured results.

        Args:
            user_id: User context
            sql: SQL query to execute

        Returns:
            Result containing dict with:
              - "columns": List[str] - column names
              - "rows": List[tuple] - result rows
              - "row_count": int - number of rows
        """
        pass

    @abstractmethod
    async def get_schema_info(self, user_id: UUID) -> Result[Dict[str, Any]]:
        """
        Get complete schema information for all tables.

        Args:
            user_id: User context

        Returns:
            Result containing dict with table information
        """
        pass

    @abstractmethod
    async def get_tag_statistics(self, user_id: UUID) -> Result[Dict[str, int]]:
        """
        Get tag usage statistics (frequency count for each tag).

        Args:
            user_id: User context

        Returns:
            Result containing dict mapping tag names to usage counts
            Example: {"groceries": 50, "dining": 30, "transport": 20}
        """
        pass

    @abstractmethod
    async def get_transactions_for_tagging(
        self, user_id: UUID, filters: Dict[str, Any] = {}, limit: int = 100, offset: int = 0
    ) -> Result[List[Transaction]]:
        """
        Get transactions for tagging session.

        Args:
            user_id: User context
            filters: Optional filters (e.g., {"has_tags": False} for untagged only)
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip (for pagination)

        Returns:
            Result containing list of Transaction objects
        """
        pass

    @abstractmethod
    async def update_transaction_tags(
        self, user_id: UUID, transaction_id: str, tags: List[str]
    ) -> Result[Transaction]:
        """
        Update tags for a single transaction.

        Args:
            user_id: User context
            transaction_id: Transaction ID to update
            tags: New list of tags (replaces existing tags)

        Returns:
            Result containing updated Transaction object
        """
        pass

    @abstractmethod
    async def get_date_range_info(self, user_id: UUID) -> Result[Dict[str, Any]]:
        """
        Get date range information for transactions.

        Args:
            user_id: User context

        Returns:
            Result containing dict with earliest_date, latest_date, total_transactions, days_range
        """
        pass

    @abstractmethod
    async def upsert_integration(self, user_id: UUID, integration_name: str, integration_options: Dict[str, Any]) -> Result[None]:
        pass

    @abstractmethod
    async def list_integrations(self, user_id: UUID) -> Result[List[Dict[str, Any]]]:
        pass

    @abstractmethod
    async def get_integration_settings(self, user_id: UUID, integration_name: str) -> Result[Dict[str, Any]]:
        pass


class AuthProvider(ABC):
    @abstractmethod
    async def sign_in_with_password(self, email: str, password: str) -> Result[User]:
        pass

    @abstractmethod
    async def sign_up_with_password(self, email: str, password: str) -> Result[User]:
        pass

    @abstractmethod
    async def sign_out(self) -> Result:
        pass

    @abstractmethod
    async def get_current_user(self) -> Result[User]:
        pass

    @abstractmethod
    async def validate_authorization_and_get_user_id(self, authorization: str) -> Result[str]:
        pass


class IntegrationProvider(ABC):
    @abstractmethod
    async def create_integration(self, user_id: UUID, integration_name: str, integration_options: Dict[str, Any]) -> Result[Any]:
        pass


class CredentialStore(ABC):
    """Abstraction for storing and retrieving user credentials."""

    @abstractmethod
    def get_credential(self, key: str) -> str | None:
        """Get a credential by key. Returns None if not found."""
        pass

    @abstractmethod
    def set_credential(self, key: str, value: str) -> None:
        """Set a credential value."""
        pass

    @abstractmethod
    def delete_credential(self, key: str) -> None:
        """Delete a credential by key."""
        pass


class AIProvider(ABC):
    """Abstraction for AI/LLM providers that power conversational analysis."""

    @abstractmethod
    async def start_session(self, user_id: UUID, db_path: str) -> Result[None]:
        """
        Initialize a new conversation session.

        Args:
            user_id: User ID for this session
            db_path: Path to user's DuckDB database

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def send_message(self, message: str) -> Result[Dict[str, Any]]:
        """
        Send a message and get streaming response.

        Args:
            message: User's natural language query

        Returns:
            Result containing response data with streaming chunks
        """
        pass

    @abstractmethod
    async def end_session(self) -> Result[None]:
        """
        End the current conversation session and cleanup resources.

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    def has_active_session(self) -> bool:
        """
        Check if there is an active conversation session.

        Returns:
            True if session is active, False otherwise
        """
        pass


class TagSuggester(ABC):
    """Abstract interface for tag suggestion algorithms."""

    @abstractmethod
    async def suggest_tags(
        self, user_id: UUID, transaction: Transaction, limit: int = 5
    ) -> Result[List[str]]:
        """
        Suggest tags for a transaction.

        Args:
            user_id: User context
            transaction: Transaction to suggest tags for
            limit: Maximum number of tags to suggest

        Returns:
            Result containing list of suggested tag strings
        """
        pass
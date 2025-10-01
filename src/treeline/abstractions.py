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
    async def execute_query(self, user_id: UUID, sql: str) -> Result[Any]:
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
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List
from uuid import UUID

from treeline.abstractions import AuthProvider, DataAggregationProvider, IntegrationProvider, Repository
from treeline.domain import Account, Result, Transaction, User


class SyncService:
    """Service for synchronizing financial data from providers."""

    def __init__(
        self,
        provider_registry: Dict[str, DataAggregationProvider],
        repository: Repository,
    ):
        self.provider_registry = provider_registry
        self.repository = repository

    def _get_provider(self, integration_name: str) -> DataAggregationProvider | None:
        """Get the provider for a given integration name."""
        return self.provider_registry.get(integration_name.lower())

    async def sync_accounts(
        self, user_id: UUID, integration_name: str, provider_options: Dict[str, Any]
    ) -> Result[Dict[str, Any]]:
        """Sync accounts from a data provider."""
        data_provider = self._get_provider(integration_name)
        if not data_provider:
            return Result(success=False, error=f"Unknown integration: {integration_name}")

        if not data_provider.can_get_accounts:
            return Result(success=False, error="Provider does not support accounts")

        integration_name_lower = integration_name.lower()

        # Get existing accounts to map external IDs
        existing_accounts_result = await self.repository.get_accounts(user_id)
        if not existing_accounts_result.success:
            return existing_accounts_result

        existing_accounts = existing_accounts_result.data or []

        # Get discovered accounts from provider
        discovered_result = await data_provider.get_accounts(
            user_id, provider_account_ids=[], provider_settings=provider_options
        )
        if not discovered_result.success:
            return discovered_result

        discovered_accounts = discovered_result.data or []

        # Map discovered accounts to existing accounts by external ID
        updated_accounts = []
        for discovered_account in discovered_accounts:
            matched = False
            for existing_account in existing_accounts:
                disc_ext_id = discovered_account.external_ids.get(integration_name_lower)
                exist_ext_id = existing_account.external_ids.get(integration_name_lower)

                if disc_ext_id and exist_ext_id and disc_ext_id == exist_ext_id:
                    # Update discovered account to use existing ID
                    updated_account = discovered_account.model_copy(update={"id": existing_account.id})
                    updated_accounts.append(updated_account)
                    matched = True
                    break

            if not matched:
                updated_accounts.append(discovered_account)

        discovered_accounts = updated_accounts

        # Bulk upsert accounts
        ingested_result = await self.repository.bulk_upsert_accounts(user_id, discovered_accounts)
        if not ingested_result.success:
            return ingested_result

        # Create balance snapshots for accounts with valid data, but only if no balance exists for today
        from datetime import date
        from uuid import uuid4
        from treeline.domain import BalanceSnapshot

        today = date.today().isoformat()  # YYYY-MM-DD format
        balance_snapshots = []

        for account in discovered_accounts:
            if account.id and account.balance is not None:
                # Check if a balance snapshot already exists for this account today
                existing_snapshots_result = await self.repository.get_balance_snapshots(
                    user_id,
                    account_id=account.id,
                    date=today
                )

                if not existing_snapshots_result.success:
                    # If query failed, skip to avoid duplicates
                    continue

                existing_snapshots = existing_snapshots_result.data or []

                # Only add if no snapshot exists with the same balance for today
                has_same_balance = any(
                    abs(snapshot.balance - account.balance) < Decimal("0.01")
                    for snapshot in existing_snapshots
                )

                if not has_same_balance:
                    from datetime import datetime, timezone
                    balance_snapshots.append(BalanceSnapshot(
                        id=uuid4(),
                        account_id=account.id,
                        balance=account.balance,
                        snapshot_time=datetime.now(timezone.utc),
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    ))

        if balance_snapshots:
            await self.repository.bulk_add_balances(user_id, balance_snapshots)

        return Result(
            success=True,
            data={"discovered_accounts": discovered_accounts, "ingested_accounts": ingested_result.data}
        )

    async def sync_transactions(
        self,
        user_id: UUID,
        integration_name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        provider_options: Dict[str, Any] | None = None,
    ) -> Result[Dict[str, Any]]:
        """Sync transactions from a data provider."""
        data_provider = self._get_provider(integration_name)
        if not data_provider:
            return Result(success=False, error=f"Unknown integration: {integration_name}")

        if not data_provider.can_get_transactions:
            return Result(success=False, error="Provider does not support transactions")

        integration_name_lower = integration_name.lower()

        # Get existing accounts to map provider account IDs
        accounts_result = await self.repository.get_accounts(user_id)
        if not accounts_result.success:
            return accounts_result

        accounts = accounts_result.data or []

        # Get provider account IDs from existing accounts
        provider_account_ids = [
            acc.external_ids.get(integration_name_lower)
            for acc in accounts
            if acc.external_ids.get(integration_name_lower)
        ]

        # Get discovered transactions
        discovered_result = await data_provider.get_transactions(
            user_id,
            start_date or datetime.now(),
            end_date or datetime.now(),
            provider_account_ids=provider_account_ids,
            provider_settings=provider_options or {},
        )
        if not discovered_result.success:
            return discovered_result

        discovered_transactions = discovered_result.data or []

        # Map provider account IDs to internal account IDs
        account_id_map = {
            acc.external_ids.get(integration_name_lower): acc.id
            for acc in accounts
            if acc.external_ids.get(integration_name_lower)
        }

        mapped_transactions = []
        for tx in discovered_transactions:
            # Get provider account ID from external_ids
            provider_acc_id = tx.external_ids.get(f"{integration_name_lower}_account")

            if not provider_acc_id:
                # Skip transactions without account mapping - provider should always provide this
                continue

            internal_acc_id = account_id_map.get(provider_acc_id)

            # Skip transactions with unmapped accounts
            if not internal_acc_id:
                continue

            mapped_tx = tx.model_copy(update={"account_id": internal_acc_id})
            mapped_transactions.append(mapped_tx)

        # Get existing transactions by external IDs to check for duplicates
        external_id_objects = [
            {integration_name_lower: tx.external_ids.get(integration_name_lower)}
            for tx in mapped_transactions
            if tx.external_ids.get(integration_name_lower)
        ]

        existing_txs: List[Transaction] = []
        if external_id_objects:
            existing_result = await self.repository.get_transactions_by_external_ids(
                user_id, external_id_objects
            )
            if existing_result.success:
                existing_txs = existing_result.data or []

        # Build map of existing transactions by external ID
        existing_by_ext_id = {
            tx.external_ids.get(integration_name_lower): tx
            for tx in existing_txs
            if tx.external_ids.get(integration_name_lower)
        }

        # Separate new vs updated transactions
        transactions_to_upsert = []
        for discovered_tx in mapped_transactions:
            ext_id = discovered_tx.external_ids.get(integration_name_lower)
            if ext_id and ext_id in existing_by_ext_id:
                # Update: preserve existing transaction ID
                existing_tx = existing_by_ext_id[ext_id]
                updated_tx = discovered_tx.model_copy(update={"id": existing_tx.id})
                transactions_to_upsert.append(updated_tx)
            else:
                # New transaction
                transactions_to_upsert.append(discovered_tx)

        # Bulk upsert
        ingested_result = await self.repository.bulk_upsert_transactions(user_id, transactions_to_upsert)
        if not ingested_result.success:
            return ingested_result

        return Result(
            success=True,
            data={
                "discovered_transactions": discovered_transactions,
                "ingested_transactions": ingested_result.data,
            },
        )

    async def sync_balances(
        self, user_id: UUID, integration_name: str, provider_options: Dict[str, Any]
    ) -> Result[Dict[str, Any]]:
        """Sync balance snapshots from a data provider.

        NOTE: This method is deprecated. Balance snapshots are now created automatically
        during sync_accounts based on the balance field in the Account model.
        """
        return Result(
            success=False,
            error="sync_balances is deprecated - balances are synced automatically during sync_accounts"
        )


class AuthService:
    """Service for authentication operations."""

    def __init__(self, auth_provider: AuthProvider):
        self.auth_provider = auth_provider

    async def sign_in_with_password(self, email: str, password: str) -> Result[User]:
        return await self.auth_provider.sign_in_with_password(email, password)

    async def sign_up_with_password(self, email: str, password: str) -> Result[User]:
        return await self.auth_provider.sign_up_with_password(email, password)

    async def sign_out(self) -> Result:
        return await self.auth_provider.sign_out()

    async def get_current_user(self) -> Result[User]:
        return await self.auth_provider.get_current_user()

    async def validate_authorization_and_get_user_id(self, authorization: str) -> Result[str]:
        return await self.auth_provider.validate_authorization_and_get_user_id(authorization)


class IntegrationService:
    """Service for managing integrations with external providers."""

    def __init__(self, integration_provider: IntegrationProvider, repository: Repository):
        self.integration_provider = integration_provider
        self.repository = repository

    async def create_integration(
        self, user_id: UUID, integration_name: str, integration_options: Dict[str, str]
    ) -> Result:
        result = await self.integration_provider.create_integration(
            user_id, integration_name, integration_options
        )
        if not result.success:
            return result

        if result.data:
            await self.repository.upsert_integration(user_id, integration_name, result.data)

        return result


class DbService:
    """Service for database operations."""

    def __init__(self, repository: Repository):
        self.repository = repository

    async def execute_query(self, user_id: UUID, sql: str) -> Result:
        await self.repository.ensure_db_exists(user_id)
        await self.repository.ensure_schema_upgraded(user_id)

        cleaned_sql = self._clean_and_validate_sql(sql)
        return await self.repository.execute_query(user_id, cleaned_sql)

    def _clean_and_validate_sql(self, sql: str) -> str:
        # TODO: Implement SQL cleaning and validation
        return sql
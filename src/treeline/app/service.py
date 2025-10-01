from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List
from uuid import UUID

from treeline.abstractions import AuthProvider, CredentialStore, DataAggregationProvider, IntegrationProvider, Repository
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

    async def get_integrations(self, user_id: UUID) -> Result[List[Dict[str, Any]]]:
        """Get list of configured integrations for a user."""
        # Ensure user DB is initialized
        await self.repository.ensure_user_db_initialized(user_id)
        return await self.repository.list_integrations(user_id)

    async def calculate_sync_date_range(self, user_id: UUID) -> Result[Dict[str, datetime]]:
        """Calculate the date range for syncing transactions.

        Returns:
            Result with dict containing 'start_date', 'end_date', and 'sync_type' ('initial' or 'incremental')
        """
        end_date = datetime.now(timezone.utc)

        # Query for the latest transaction date
        max_date_query = """
            SELECT MAX(transaction_date) as max_date
            FROM transactions
        """
        max_date_result = await self.repository.execute_query(user_id, max_date_query)

        if not max_date_result.success:
            # Fallback to 90 days if query fails
            return Result(
                success=True,
                data={
                    "start_date": end_date - timedelta(days=90),
                    "end_date": end_date,
                    "sync_type": "initial"
                }
            )

        rows = max_date_result.data.get("rows", [])
        if rows and rows[0].get("max_date"):
            # Incremental sync: start from last transaction date minus 7 days overlap
            max_date = rows[0]["max_date"]

            # Ensure it's a datetime object and timezone-aware
            if isinstance(max_date, datetime):
                if max_date.tzinfo is None:
                    max_date = max_date.replace(tzinfo=timezone.utc)
                start_date = max_date - timedelta(days=7)
                return Result(
                    success=True,
                    data={
                        "start_date": start_date,
                        "end_date": end_date,
                        "sync_type": "incremental"
                    }
                )

        # Initial sync: fetch last 90 days
        return Result(
            success=True,
            data={
                "start_date": end_date - timedelta(days=90),
                "end_date": end_date,
                "sync_type": "initial"
            }
        )

    async def sync_all_integrations(self, user_id: UUID) -> Result[Dict[str, Any]]:
        """Sync all configured integrations for a user.

        Returns a summary of sync results for each integration.
        """
        # Get integrations
        integrations_result = await self.get_integrations(user_id)
        if not integrations_result.success:
            return integrations_result

        integrations = integrations_result.data or []

        if not integrations:
            return Result(
                success=False,
                error="No integrations configured"
            )

        sync_results = []

        for integration in integrations:
            integration_name = integration["integrationName"]
            integration_options = integration["integrationOptions"]

            # Sync accounts
            accounts_result = await self.sync_accounts(user_id, integration_name, integration_options)

            if not accounts_result.success:
                sync_results.append({
                    "integration": integration_name,
                    "accounts_synced": 0,
                    "transactions_synced": 0,
                    "error": accounts_result.error
                })
                continue

            num_accounts = len(accounts_result.data.get("ingested_accounts", []))

            # Calculate date range for transactions
            date_range_result = await self.calculate_sync_date_range(user_id)
            if not date_range_result.success:
                sync_results.append({
                    "integration": integration_name,
                    "accounts_synced": num_accounts,
                    "transactions_synced": 0,
                    "error": "Failed to calculate sync date range"
                })
                continue

            date_range = date_range_result.data

            # Sync transactions
            transactions_result = await self.sync_transactions(
                user_id,
                integration_name,
                start_date=date_range["start_date"],
                end_date=date_range["end_date"],
                provider_options=integration_options
            )

            if not transactions_result.success:
                sync_results.append({
                    "integration": integration_name,
                    "accounts_synced": num_accounts,
                    "transactions_synced": 0,
                    "sync_type": date_range["sync_type"],
                    "error": transactions_result.error
                })
                continue

            num_transactions = len(transactions_result.data.get("ingested_transactions", []))

            sync_results.append({
                "integration": integration_name,
                "accounts_synced": num_accounts,
                "transactions_synced": num_transactions,
                "sync_type": date_range["sync_type"],
                "start_date": date_range["start_date"],
                "end_date": date_range["end_date"]
            })

        return Result(
            success=True,
            data={"results": sync_results}
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


class ConfigService:
    """Service for managing configuration and credentials."""

    def __init__(self, credential_store: CredentialStore):
        self.credential_store = credential_store

    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        user_id = self.credential_store.get_credential("user_id")
        return user_id is not None

    def get_current_user_id(self) -> str | None:
        """Get the current authenticated user ID."""
        return self.credential_store.get_credential("user_id")

    def get_current_user_email(self) -> str | None:
        """Get the current authenticated user email."""
        return self.credential_store.get_credential("user_email")

    def save_user_credentials(self, user_id: str, email: str) -> None:
        """Save user credentials after authentication."""
        self.credential_store.set_credential("user_id", user_id)
        self.credential_store.set_credential("user_email", email)
        # TODO: Store actual access token once we implement token-based auth
        self.credential_store.set_credential("supabase_access_token", "TODO_access_token")

    def clear_credentials(self) -> None:
        """Clear all stored credentials."""
        self.credential_store.delete_credential("user_id")
        self.credential_store.delete_credential("user_email")
        self.credential_store.delete_credential("supabase_access_token")


class StatusService:
    """Service for retrieving financial data status and summaries."""

    def __init__(self, repository: Repository):
        self.repository = repository

    async def get_status(self, user_id: UUID) -> Result[Dict[str, Any]]:
        """Get financial data status summary."""
        # Ensure user DB is initialized
        await self.repository.ensure_user_db_initialized(user_id)

        # Get accounts
        accounts_result = await self.repository.get_accounts(user_id)
        if not accounts_result.success:
            return accounts_result

        accounts = accounts_result.data or []

        # Get integrations
        integrations_result = await self.repository.list_integrations(user_id)
        if not integrations_result.success:
            return integrations_result

        integrations = integrations_result.data or []

        # Query for transaction stats
        transaction_stats_query = """
            SELECT
                COUNT(*) as total_transactions,
                MIN(transaction_date) as earliest_date,
                MAX(transaction_date) as latest_date
            FROM transactions
        """
        stats_result = await self.repository.execute_query(user_id, transaction_stats_query)

        if not stats_result.success:
            return stats_result

        transaction_stats = stats_result.data
        rows = transaction_stats.get("rows", [])
        if rows and len(rows) > 0:
            total_transactions = rows[0].get("total_transactions", 0)
            earliest_date = rows[0].get("earliest_date")
            latest_date = rows[0].get("latest_date")
        else:
            total_transactions = 0
            earliest_date = None
            latest_date = None

        # Query for balance snapshots
        balance_query = "SELECT COUNT(*) as total_snapshots FROM balance_snapshots"
        balance_result = await self.repository.execute_query(user_id, balance_query)

        if not balance_result.success:
            total_snapshots = 0
        else:
            balance_data = balance_result.data
            balance_rows = balance_data.get("rows", [])
            total_snapshots = (
                balance_rows[0].get("total_snapshots", 0) if balance_rows and len(balance_rows) > 0 else 0
            )

        return Result(
            success=True,
            data={
                "accounts": accounts,
                "total_transactions": total_transactions,
                "total_snapshots": total_snapshots,
                "integrations": integrations,
                "earliest_date": earliest_date,
                "latest_date": latest_date,
            },
        )


class DbService:
    """Service for database operations."""

    def __init__(self, repository: Repository):
        self.repository = repository

    async def initialize_db(self) -> Result:
        """Initialize database directory and schema."""
        db_result = await self.repository.ensure_db_exists()
        if not db_result.success:
            return db_result

        return await self.repository.ensure_schema_upgraded()

    async def initialize_user_db(self, user_id: UUID) -> Result:
        """Initialize user-specific database."""
        return await self.repository.ensure_user_db_initialized(user_id)

    async def execute_query(self, user_id: UUID, sql: str) -> Result:
        await self.repository.ensure_user_db_initialized(user_id)

        cleaned_sql = self._clean_and_validate_sql(sql)
        return await self.repository.execute_query(user_id, cleaned_sql)

    def _clean_and_validate_sql(self, sql: str) -> str:
        # TODO: Implement SQL cleaning and validation
        return sql
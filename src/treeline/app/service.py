from datetime import datetime, timedelta, timezone, date
from decimal import Decimal
from typing import Any, Dict, List, Callable
from uuid import UUID, uuid4

from treeline.abstractions import (
    DataAggregationProvider,
    IntegrationProvider,
    Repository,
    TagSuggester,
)
from treeline.domain import Account, Result, Transaction, User, BalanceSnapshot


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

    def _load_and_get_taggers(self) -> List[Callable[..., List[str]]]:
        """Load and return all user-defined tagger functions from ~/.treeline/taggers/

        Auto-discovers all functions defined in tagger files. The @tagger decorator is optional.

        Returns:
            List of tagger functions
        """
        from treeline.app.tagger_utils import load_taggers
        from treeline.ext.decorators import get_taggers

        # First check if there are any registered taggers (e.g., from tests)
        registered_taggers = get_taggers()
        if registered_taggers:
            return registered_taggers

        # Load from filesystem
        return load_taggers()

    def _apply_taggers(
        self,
        transaction: Transaction,
        taggers: List[Callable[..., List[str]]],
        verbose: bool = False,
    ) -> tuple[Transaction, Dict[str, int], List[str]]:
        """Apply taggers to a transaction.

        Args:
            transaction: Transaction to tag
            taggers: List of tagger functions to apply
            verbose: Whether to collect verbose logging info

        Returns:
            Tuple of (tagged transaction, stats dict with tag counts per tagger, verbose logs)
        """
        from treeline.app.tagger_utils import apply_taggers_to_transaction

        return apply_taggers_to_transaction(transaction, taggers, verbose)

    async def sync_accounts(
        self, integration_name: str, provider_options: Dict[str, Any]
    ) -> Result[Dict[str, Any]]:
        """Sync accounts from a data provider."""
        data_provider = self._get_provider(integration_name)
        if not data_provider:
            return Result(
                success=False, error=f"Unknown integration: {integration_name}"
            )

        if not data_provider.can_get_accounts:
            return Result(success=False, error="Provider does not support accounts")

        integration_name_lower = integration_name.lower()

        # Get existing accounts to map external IDs
        existing_accounts_result = await self.repository.get_accounts()
        if not existing_accounts_result.success:
            return existing_accounts_result

        existing_accounts = existing_accounts_result.data or []

        # Get discovered accounts from provider
        discovered_result = await data_provider.get_accounts(
            provider_account_ids=[], provider_settings=provider_options
        )
        if not discovered_result.success:
            return discovered_result

        discovered_accounts = discovered_result.data or []

        # Map discovered accounts to existing accounts by external ID
        updated_accounts = []
        for discovered_account in discovered_accounts:
            matched = False
            for existing_account in existing_accounts:
                disc_ext_id = discovered_account.external_ids.get(
                    integration_name_lower
                )
                exist_ext_id = existing_account.external_ids.get(integration_name_lower)

                if disc_ext_id and exist_ext_id and disc_ext_id == exist_ext_id:
                    # Update discovered account to use existing ID
                    updated_account = discovered_account.model_copy(
                        update={"id": existing_account.id}
                    )
                    updated_accounts.append(updated_account)
                    matched = True
                    break

            if not matched:
                updated_accounts.append(discovered_account)

        discovered_accounts = updated_accounts

        # Bulk upsert accounts
        ingested_result = await self.repository.bulk_upsert_accounts(
            discovered_accounts
        )
        if not ingested_result.success:
            return ingested_result

        # Create balance snapshots for accounts with valid data, but only if no balance exists for today
        today = date.today().isoformat()  # YYYY-MM-DD format
        balance_snapshots = []

        for account in discovered_accounts:
            if account.id and account.balance is not None:
                # Check if a balance snapshot already exists for this account today
                existing_snapshots_result = await self.repository.get_balance_snapshots(
                    account_id=account.id, date=today
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
                    balance_snapshots.append(
                        BalanceSnapshot(
                            id=uuid4(),
                            account_id=account.id,
                            balance=account.balance,
                            snapshot_time=datetime.now(timezone.utc),
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc),
                        )
                    )

        if balance_snapshots:
            await self.repository.bulk_add_balances(balance_snapshots)

        return Result(
            success=True,
            data={
                "discovered_accounts": discovered_accounts,
                "ingested_accounts": ingested_result.data,
            },
        )

    async def sync_transactions(
        self,
        integration_name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        provider_options: Dict[str, Any] | None = None,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> Result[Dict[str, Any]]:
        """Sync transactions from a data provider."""
        data_provider = self._get_provider(integration_name)
        if not data_provider:
            return Result(
                success=False, error=f"Unknown integration: {integration_name}"
            )

        if not data_provider.can_get_transactions:
            return Result(success=False, error="Provider does not support transactions")

        integration_name_lower = integration_name.lower()

        # Get existing accounts to map provider account IDs
        accounts_result = await self.repository.get_accounts()
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
            start_date,
            end_date,
            provider_account_ids=provider_account_ids,
            provider_settings=provider_options or {},
        )
        if not discovered_result.success:
            return discovered_result

        discovered_data = discovered_result.data or []

        # Map provider account IDs to internal account IDs
        account_id_map = {
            acc.external_ids.get(integration_name_lower): acc.id
            for acc in accounts
            if acc.external_ids.get(integration_name_lower)
        }

        mapped_transactions = []

        # Handle provider-specific return formats
        # SimpleFIN returns: List[(provider_account_id, Transaction)]
        # CSV returns: List[Transaction] (account_id already set)
        for item in discovered_data:
            if isinstance(item, tuple):
                # Format: (provider_account_id, transaction)
                provider_acc_id, tx = item
                internal_acc_id = account_id_map.get(provider_acc_id)

                # Skip transactions with unmapped accounts
                if not internal_acc_id:
                    continue

                # Reconstruct transaction with correct account_id to force fingerprint recalculation
                # Note: model_copy doesn't trigger @model_validator, so we use model_dump + reconstruct
                tx_dict = tx.model_dump()
                tx_dict["account_id"] = internal_acc_id

                # Remove old fingerprint to force recalculation
                if "fingerprint" in tx_dict["external_ids"]:
                    cleaned_external_ids = {
                        k: v
                        for k, v in tx_dict["external_ids"].items()
                        if k != "fingerprint"
                    }
                    tx_dict["external_ids"] = cleaned_external_ids

                # Reconstruct - this triggers @model_validator which auto-generates correct fingerprint
                mapped_tx = Transaction(**tx_dict)
                mapped_transactions.append(mapped_tx)
            else:
                # Format: Transaction (account_id already set, e.g., from CSV)
                mapped_transactions.append(item)

        # Get existing transactions by external IDs to check for duplicates
        external_id_objects = [
            {integration_name_lower: tx.external_ids.get(integration_name_lower)}
            for tx in mapped_transactions
            if tx.external_ids.get(integration_name_lower)
        ]

        existing_txs: List[Transaction] = []
        if external_id_objects:
            existing_result = await self.repository.get_transactions_by_external_ids(
                external_id_objects
            )
            if existing_result.success:
                existing_txs = existing_result.data or []

        # Build map of existing transactions by external ID
        existing_by_ext_id = {
            tx.external_ids.get(integration_name_lower): tx
            for tx in existing_txs
            if tx.external_ids.get(integration_name_lower)
        }

        # Separate new vs skipped transactions
        # IMPORTANT: Skip existing transactions to preserve user-added data like tags
        transactions_to_insert = []
        new_count = 0
        skipped_count = 0

        # Load taggers once for this sync
        taggers = self._load_and_get_taggers()
        combined_tagger_stats: Dict[str, int] = {}
        all_verbose_logs: List[str] = []

        for discovered_tx in mapped_transactions:
            ext_id = discovered_tx.external_ids.get(integration_name_lower)
            if ext_id and ext_id in existing_by_ext_id:
                # Skip: transaction already exists, preserve user data (tags, etc.)
                skipped_count += 1
            else:
                # New transaction - apply taggers
                tagged_tx, tx_stats, tx_logs = self._apply_taggers(
                    discovered_tx, taggers, verbose=verbose
                )
                transactions_to_insert.append(tagged_tx)
                new_count += 1

                # Aggregate tagger stats
                for tagger_name, count in tx_stats.items():
                    combined_tagger_stats[tagger_name] = (
                        combined_tagger_stats.get(tagger_name, 0) + count
                    )

                # Collect verbose logs (always collect errors, collect all if verbose)
                if verbose:
                    all_verbose_logs.extend(tx_logs)
                else:
                    # Only collect errors when not verbose
                    all_verbose_logs.extend(
                        [log for log in tx_logs if log.startswith("ERROR:")]
                    )

        # Bulk insert only new transactions (unless dry-run)
        if dry_run:
            # In dry-run mode, don't actually insert
            ingested_transactions = transactions_to_insert
        else:
            ingested_result = await self.repository.bulk_upsert_transactions(
                transactions_to_insert
            )
            if not ingested_result.success:
                return ingested_result
            ingested_transactions = ingested_result.data

        return Result(
            success=True,
            data={
                "discovered_transactions": mapped_transactions,
                "ingested_transactions": ingested_transactions,
                "stats": {
                    "discovered": len(mapped_transactions),
                    "new": new_count,
                    "skipped": skipped_count,
                },
                "tagger_stats": combined_tagger_stats,
                "tagger_verbose_logs": all_verbose_logs,  # Always return (contains errors even if not verbose)
            },
        )

    async def sync_balances(
        self, integration_name: str, provider_options: Dict[str, Any]
    ) -> Result[Dict[str, Any]]:
        """Sync balance snapshots from a data provider.

        NOTE: This method is deprecated. Balance snapshots are now created automatically
        during sync_accounts based on the balance field in the Account model.
        """
        return Result(
            success=False,
            error="sync_balances is deprecated - balances are synced automatically during sync_accounts",
        )

    async def get_integrations(self) -> Result[List[Dict[str, Any]]]:
        """Get list of configured integrations for a user."""
        # Ensure user DB is initialized
        # Database initialization happens automatically
        return await self.repository.list_integrations()

    async def _calculate_sync_date_range(self) -> Result[Dict[str, datetime]]:
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
        max_date_result = await self.repository.execute_query(max_date_query)

        if not max_date_result.success:
            # Fallback to 90 days if query fails
            return Result(
                success=True,
                data={
                    "start_date": end_date - timedelta(days=90),
                    "end_date": end_date,
                    "sync_type": "initial",
                },
            )

        rows = max_date_result.data.get("rows", [])
        if rows and rows[0][0]:
            # Incremental sync: start from last transaction date minus 7 days overlap
            max_date = rows[0][0]

            # Convert date to datetime if needed, and ensure timezone-aware
            if isinstance(max_date, date) and not isinstance(max_date, datetime):
                # DATE column - convert to datetime at midnight UTC
                max_date = datetime.combine(
                    max_date, datetime.min.time(), tzinfo=timezone.utc
                )
            elif isinstance(max_date, datetime):
                # TIMESTAMP column - ensure timezone-aware
                if max_date.tzinfo is None:
                    max_date = max_date.replace(tzinfo=timezone.utc)

            start_date = max_date - timedelta(days=7)
            return Result(
                success=True,
                data={
                    "start_date": start_date,
                    "end_date": end_date,
                    "sync_type": "incremental",
                },
            )

        # Initial sync: fetch last 90 days
        return Result(
            success=True,
            data={
                "start_date": end_date - timedelta(days=90),
                "end_date": end_date,
                "sync_type": "initial",
            },
        )

    async def sync_all_integrations(
        self, dry_run: bool = False, verbose: bool = False
    ) -> Result[Dict[str, Any]]:
        """Sync all configured integrations for a user.

        Args:
            dry_run: If True, don't actually save changes to the database
            verbose: If True, include verbose tagging logs

        Returns a summary of sync results for each integration.
        """
        # Get integrations
        integrations_result = await self.get_integrations()
        if not integrations_result.success:
            return integrations_result

        integrations = integrations_result.data or []

        if not integrations:
            return Result(success=False, error="No integrations configured")

        sync_results = []

        for integration in integrations:
            integration_name = integration["integrationName"]
            integration_options = integration["integrationOptions"]

            # Sync accounts (skip in dry-run since we don't save them anyway)
            if not dry_run:
                accounts_result = await self.sync_accounts(
                    integration_name, integration_options
                )

                if not accounts_result.success:
                    sync_results.append(
                        {
                            "integration": integration_name,
                            "accounts_synced": 0,
                            "transactions_synced": 0,
                            "error": accounts_result.error,
                        }
                    )
                    continue

                num_accounts = len(accounts_result.data.get("ingested_accounts", []))
            else:
                num_accounts = 0  # Don't sync accounts in dry-run

            # Calculate date range for transactions
            date_range_result = await self._calculate_sync_date_range()
            if not date_range_result.success:
                sync_results.append(
                    {
                        "integration": integration_name,
                        "accounts_synced": num_accounts,
                        "transactions_synced": 0,
                        "error": "Failed to calculate sync date range",
                    }
                )
                continue

            date_range = date_range_result.data

            # Sync transactions
            transactions_result = await self.sync_transactions(
                integration_name,
                start_date=date_range["start_date"],
                end_date=date_range["end_date"],
                provider_options=integration_options,
                dry_run=dry_run,
                verbose=verbose,
            )

            if not transactions_result.success:
                sync_results.append(
                    {
                        "integration": integration_name,
                        "accounts_synced": num_accounts,
                        "transactions_synced": 0,
                        "sync_type": date_range["sync_type"],
                        "error": transactions_result.error,
                    }
                )
                continue

            num_transactions = len(
                transactions_result.data.get("ingested_transactions", [])
            )
            tx_stats = transactions_result.data.get("stats", {})
            tagger_stats = transactions_result.data.get("tagger_stats", {})
            tagger_verbose_logs = transactions_result.data.get(
                "tagger_verbose_logs", []
            )

            sync_results.append(
                {
                    "integration": integration_name,
                    "accounts_synced": num_accounts,
                    "transactions_synced": num_transactions,
                    "transaction_stats": tx_stats,
                    "tagger_stats": tagger_stats,
                    "tagger_verbose_logs": tagger_verbose_logs,
                    "sync_type": date_range["sync_type"],
                    "start_date": date_range["start_date"],
                    "end_date": date_range["end_date"],
                }
            )

        return Result(success=True, data={"results": sync_results})


class IntegrationService:
    """Service for managing integrations with external providers."""

    def __init__(
        self, integration_provider: IntegrationProvider, repository: Repository
    ):
        self.integration_provider = integration_provider
        self.repository = repository

    async def create_integration(
        self, integration_name: str, integration_options: Dict[str, str]
    ) -> Result:
        result = await self.integration_provider.create_integration(
            integration_name, integration_options
        )
        if not result.success:
            return result

        if result.data:
            await self.repository.upsert_integration(integration_name, result.data)

        return result


class AccountService:
    """Service for account operations."""

    def __init__(self, repository: Repository):
        self.repository = repository

    async def get_accounts(self) -> Result[List[Account]]:
        """Get all accounts."""
        return await self.repository.get_accounts()


class StatusService:
    """Service for retrieving financial data status and summaries."""

    def __init__(self, repository: Repository):
        self.repository = repository

    async def get_status(self) -> Result[Dict[str, Any]]:
        """Get financial data status summary."""
        # Get accounts
        accounts_result = await self.repository.get_accounts()
        if not accounts_result.success:
            return accounts_result

        accounts = accounts_result.data or []

        # Get integrations
        integrations_result = await self.repository.list_integrations()
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
        stats_result = await self.repository.execute_query(transaction_stats_query)

        if not stats_result.success:
            return stats_result

        transaction_stats = stats_result.data
        rows = transaction_stats.get("rows", [])

        if rows and len(rows) > 0:
            # Rows are tuples, use column indices
            row = rows[0]
            total_transactions = row[0] if len(row) > 0 else 0  # COUNT(*)
            earliest_date = row[1] if len(row) > 1 else None  # MIN(transaction_date)
            latest_date = row[2] if len(row) > 2 else None  # MAX(transaction_date)
        else:
            total_transactions = 0
            earliest_date = None
            latest_date = None

        # Query for balance snapshots
        balance_query = "SELECT COUNT(*) as total_snapshots FROM balance_snapshots"
        balance_result = await self.repository.execute_query(balance_query)

        if not balance_result.success:
            total_snapshots = 0
        else:
            balance_data = balance_result.data
            balance_rows = balance_data.get("rows", [])
            # Rows are tuples, access by index
            total_snapshots = (
                balance_rows[0][0] if balance_rows and len(balance_rows) > 0 else 0
            )

        # Return both full data (for display) and summary (for JSON)
        integration_names = [i["integrationName"] for i in integrations]

        return Result(
            success=True,
            data={
                # Full data for display functions
                "accounts": accounts,
                "integrations": integrations,
                # Summary counts
                "total_accounts": len(accounts),
                "total_transactions": total_transactions,
                "total_snapshots": total_snapshots,
                "total_integrations": len(integrations),
                "integration_names": integration_names,
                # Date range
                "earliest_date": str(earliest_date) if earliest_date else None,
                "latest_date": str(latest_date) if latest_date else None,
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

    async def execute_query(self, sql: str) -> Result:
        cleaned_sql = self._clean_and_validate_sql(sql)
        return await self.repository.execute_query(cleaned_sql)

    def _clean_and_validate_sql(self, sql: str) -> str:
        # TODO: Implement SQL cleaning and validation
        return sql


class TaggingService:
    """Service for managing transaction tagging operations."""

    def __init__(self, repository: Repository, tag_suggester: TagSuggester):
        """
        Initialize TaggingService.

        Args:
            repository: Repository for data persistence
            tag_suggester: Tag suggestion algorithm
        """
        self.repository = repository
        self.tag_suggester = tag_suggester

    async def get_untagged_transactions(
        self, limit: int = 100
    ) -> Result[List[Transaction]]:
        """
        Get transactions that have no tags.

        Args:
            limit: Maximum number of transactions to return

        Returns:
            Result containing list of untagged Transaction objects
        """
        return await self.repository.get_transactions_for_tagging(
            filters={"has_tags": False}, limit=limit
        )

    async def get_transactions_for_tagging(
        self,
        filters: Dict[str, Any] = {},
        limit: int = 100,
        offset: int = 0,
    ) -> Result[List[Transaction]]:
        """
        Get transactions matching filters for tagging session.

        Args:
            filters: Optional filters (e.g., {"has_tags": False} for untagged only)
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip (for pagination)

        Returns:
            Result containing list of Transaction objects
        """
        return await self.repository.get_transactions_for_tagging(
            filters=filters, limit=limit, offset=offset
        )

    async def update_transaction_tags(
        self, transaction_id: UUID, tags: List[str]
    ) -> Result[Transaction]:
        """
        Update tags for a single transaction.

        Args:
            transaction_id: Transaction ID to update
            tags: New list of tags (replaces existing tags)

        Returns:
            Result containing updated Transaction object
        """
        return await self.repository.update_transaction_tags(transaction_id, tags)

    async def get_suggested_tags(
        self, transaction: Transaction, limit: int = 5
    ) -> Result[List[str]]:
        """
        Get suggested tags for a transaction using configured suggester.

        Args:
            transaction: Transaction to suggest tags for
            limit: Maximum number of tags to suggest

        Returns:
            Result containing list of suggested tag strings
        """
        return await self.tag_suggester.suggest_tags(transaction, limit=limit)

    async def get_tag_statistics(self) -> Result[Dict[str, int]]:
        """
        Get tag usage statistics (frequency count for each tag).

        Returns:
            Result containing dict mapping tag names to usage counts
            Example: {"groceries": 50, "dining": 30, "transport": 20}
        """
        return await self.repository.get_tag_statistics()


class ImportService:
    """Service for one-time bulk imports from files or external sources."""

    def __init__(
        self,
        repository: Repository,
        provider_registry: Dict[str, DataAggregationProvider],
    ):
        self.repository = repository
        self.provider_registry = provider_registry

    async def import_transactions(
        self,
        source_type: str,
        account_id: UUID,
        source_options: Dict[str, Any],
    ) -> Result[Dict[str, Any]]:
        """
        Import transactions from a one-time source using fingerprint deduplication.

        Args:
            source_type: Type of import source ("csv", "ynab", etc.)
            account_id: Treeline account to import transactions into
            source_options: Provider-specific options (e.g., {"file_path": "/path/to/file.csv"})

        Returns:
            Result with stats: {"discovered": 150, "imported": 120, "skipped": 30}
        """
        # Get provider
        provider = self.provider_registry.get(source_type.lower())
        if not provider:
            return Result(success=False, error=f"Unknown source type: {source_type}")

        # Get discovered transactions from source
        discovered_result = await provider.get_transactions(
            start_date=datetime.min,
            end_date=datetime.now(timezone.utc),
            provider_account_ids=[],
            provider_settings=source_options,
        )
        if not discovered_result.success:
            return discovered_result

        discovered_transactions = discovered_result.data or []

        # Map all transactions to the specified account
        # Note: Reconstruct transactions to recalculate fingerprint with new account_id
        mapped_transactions = []
        for tx in discovered_transactions:
            tx_dict = tx.model_dump()
            tx_dict["account_id"] = account_id
            # Remove fingerprint from external_ids to force regeneration with new account_id
            ext_ids = dict(tx_dict.get("external_ids", {}))
            ext_ids.pop("fingerprint", None)
            tx_dict["external_ids"] = ext_ids
            mapped_transactions.append(Transaction(**tx_dict))

        # Group by fingerprint (fingerprint is auto-set in external_ids by domain model)
        discovered_by_fingerprint: Dict[str, List[Transaction]] = {}
        for tx in mapped_transactions:
            fingerprint = tx.external_ids.get("fingerprint")
            if fingerprint:
                discovered_by_fingerprint.setdefault(fingerprint, []).append(tx)

        # Query existing counts per fingerprint
        fingerprints = list(discovered_by_fingerprint.keys())
        existing_counts_result = (
            await self.repository.get_transaction_counts_by_fingerprint(fingerprints)
        )
        if not existing_counts_result.success:
            return existing_counts_result

        existing_counts = existing_counts_result.data or {}

        # Determine which transactions to import
        transactions_to_import = []
        skipped_transactions = []  # Track skipped for debugging
        skipped_count = 0

        for fingerprint, discovered_txs in discovered_by_fingerprint.items():
            existing_count = existing_counts.get(fingerprint, 0)
            discovered_count = len(discovered_txs)

            # Import the difference (if any new transactions)
            new_count = max(0, discovered_count - existing_count)
            transactions_to_import.extend(discovered_txs[:new_count])

            # Track skipped transactions with their fingerprint and existing count
            skipped_txs = discovered_txs[new_count:]
            for tx in skipped_txs:
                skipped_transactions.append(
                    {
                        "transaction": tx,
                        "fingerprint": fingerprint,
                        "existing_count": existing_count,
                    }
                )
            skipped_count += discovered_count - new_count

        # Bulk insert (not upsert, these are all new)
        if transactions_to_import:
            import_result = await self.repository.bulk_upsert_transactions(
                transactions_to_import
            )
            if not import_result.success:
                return import_result

        return Result(
            success=True,
            data={
                "discovered": len(discovered_transactions),
                "imported": len(transactions_to_import),
                "skipped": skipped_count,
                "fingerprints_checked": len(fingerprints),
                "imported_transactions": transactions_to_import,
                "skipped_transactions": skipped_transactions,
            },
        )

    async def detect_columns(
        self, source_type: str, file_path: str
    ) -> Result[Dict[str, Any]]:
        """
        Detect columns automatically for import.

        Args:
            file_path: Path to file

        Returns:
            Result with column mapping dict like {"date": "Date", "amount": "Amount", ...}
        """
        # Get provider
        provider = self.provider_registry.get(source_type)
        if not provider:
            return Result(success=False, error=f"{source_type} provider not available")

        # Call provider-specific detection method
        return provider.detect_columns(file_path)

    async def preview_csv_import(
        self,
        file_path: str,
        column_mapping: Dict[str, str],
        date_format: str = "auto",
        limit: int = 5,
        flip_signs: bool = False,
    ) -> Result[List[Transaction]]:
        """
        Preview transactions from CSV file before importing.

        Args:
            file_path: Path to CSV file
            column_mapping: Mapping of standard fields to CSV columns
            date_format: Date format string or "auto"
            limit: Maximum number of transactions to preview
            flip_signs: Whether to flip signs (for credit card statements)

        Returns:
            Result with list of preview Transaction objects
        """
        # Get CSV provider
        provider = self.provider_registry.get("csv")
        if not provider:
            return Result(success=False, error="CSV provider not available")

        # Call provider-specific preview method
        return provider.preview_transactions(
            file_path, column_mapping, date_format, limit, flip_signs
        )

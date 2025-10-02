"""DuckDB infrastructure implementation."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, List
from uuid import UUID

import duckdb

from treeline.abstractions import Repository
from treeline.domain import Account, BalanceSnapshot, Fail, Ok, Result, Transaction


class DuckDBRepository(Repository):
    """DuckDB implementation of Repository."""

    def __init__(self, db_dir: str):
        """Initialize with a database directory.

        Args:
            db_dir: Directory to store user databases
        """
        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_timezone(self, dt: datetime) -> datetime:
        """Ensure datetime is timezone-aware."""
        if dt and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _get_db_path(self, user_id: UUID) -> Path:
        """Get the database path for a user."""
        return self.db_dir / f"{user_id}.duckdb"

    def _get_connection(self, user_id: UUID, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        """Get a database connection for a user."""
        db_path = self._get_db_path(user_id)
        if read_only:
            return duckdb.connect(str(db_path), read_only=True)
        return duckdb.connect(str(db_path))

    async def ensure_db_exists(self) -> Result:
        """Ensure the database directory exists."""
        try:
            self.db_dir.mkdir(parents=True, exist_ok=True)
            return Ok()
        except Exception as e:
            return Fail(f"Failed to create database directory: {str(e)}")

    async def ensure_schema_upgraded(self) -> Result:
        """Schema upgrades are done per-user. This is a no-op."""
        # Schema is created per-user when ensure_user_db_initialized is called
        return Ok()

    async def ensure_user_db_initialized(self, user_id: UUID) -> Result:
        """Ensure user-specific database is initialized with schema."""
        try:
            db_path = self._get_db_path(user_id)

            # Create database if it doesn't exist
            conn = duckdb.connect(str(db_path))

            # Read and execute migration
            migration_path = Path(__file__).parent / "migrations" / "001_initial_schema.sql"
            with open(migration_path, "r") as f:
                migration_sql = f.read()

            conn.execute(migration_sql)
            conn.close()
            return Ok()
        except Exception as e:
            return Fail(f"Failed to initialize user database: {str(e)}")

    async def add_account(self, user_id: UUID, account: Account) -> Result[Account]:
        """Add a single account."""
        try:
            conn = self._get_connection(user_id)

            conn.execute(
                """
                INSERT INTO accounts (
                    account_id, name, nickname, account_type, currency,
                    external_ids, institution_name, institution_url, institution_domain,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    str(account.id),
                    account.name,
                    account.nickname,
                    account.account_type,
                    account.currency,
                    json.dumps(dict(account.external_ids)),
                    account.institution_name,
                    account.institution_url,
                    account.institution_domain,
                    account.created_at,
                    account.updated_at,
                ],
            )

            conn.close()
            return Ok(account)
        except Exception as e:
            return Fail(f"Failed to add account: {str(e)}")

    async def add_transaction(self, user_id: UUID, transaction: Transaction) -> Result[Transaction]:
        """Add a single transaction."""
        try:
            conn = self._get_connection(user_id)

            conn.execute(
                """
                INSERT INTO transactions (
                    transaction_id, account_id, external_ids, amount, description,
                    transaction_date, posted_date, tags, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    str(transaction.id),
                    str(transaction.account_id),
                    json.dumps(dict(transaction.external_ids)),
                    float(transaction.amount),
                    transaction.description,
                    transaction.transaction_date,
                    transaction.posted_date,
                    list(transaction.tags),
                    transaction.created_at,
                    transaction.updated_at,
                ],
            )

            conn.close()
            return Ok(transaction)
        except Exception as e:
            return Fail(f"Failed to add transaction: {str(e)}")

    async def add_balance(self, user_id: UUID, balance: BalanceSnapshot) -> Result[BalanceSnapshot]:
        """Add a balance snapshot."""
        try:
            conn = self._get_connection(user_id)

            conn.execute(
                """
                INSERT INTO balance_snapshots (
                    snapshot_id, account_id, balance, snapshot_time, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    str(balance.id),
                    str(balance.account_id),
                    float(balance.balance),
                    balance.snapshot_time,
                    balance.created_at,
                ],
            )

            conn.close()
            return Ok(balance)
        except Exception as e:
            return Fail(f"Failed to add balance: {str(e)}")

    async def bulk_upsert_accounts(self, user_id: UUID, accounts: List[Account]) -> Result[List[Account]]:
        """Bulk upsert accounts."""
        try:
            conn = self._get_connection(user_id)

            for account in accounts:
                conn.execute(
                    """
                    INSERT INTO accounts (
                        account_id, name, nickname, account_type, currency,
                        external_ids, institution_name, institution_url, institution_domain,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (account_id) DO UPDATE SET
                        name = excluded.name,
                        nickname = excluded.nickname,
                        account_type = excluded.account_type,
                        currency = excluded.currency,
                        external_ids = excluded.external_ids,
                        institution_name = excluded.institution_name,
                        institution_url = excluded.institution_url,
                        institution_domain = excluded.institution_domain,
                        updated_at = excluded.updated_at
                    """,
                    [
                        str(account.id),
                        account.name,
                        account.nickname,
                        account.account_type,
                        account.currency,
                        json.dumps(dict(account.external_ids)),
                        account.institution_name,
                        account.institution_url,
                        account.institution_domain,
                        account.created_at,
                        account.updated_at,
                    ],
                )

            conn.close()
            return Ok(accounts)
        except Exception as e:
            return Fail(f"Failed to bulk upsert accounts: {str(e)}")

    async def bulk_upsert_transactions(self, user_id: UUID, transactions: List[Transaction]) -> Result[List[Transaction]]:
        """Bulk upsert transactions."""
        try:
            conn = self._get_connection(user_id)

            for transaction in transactions:
                conn.execute(
                    """
                    INSERT INTO transactions (
                        transaction_id, account_id, external_ids, amount, description,
                        transaction_date, posted_date, tags, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (transaction_id) DO UPDATE SET
                        account_id = excluded.account_id,
                        external_ids = excluded.external_ids,
                        amount = excluded.amount,
                        description = excluded.description,
                        transaction_date = excluded.transaction_date,
                        posted_date = excluded.posted_date,
                        tags = excluded.tags,
                        updated_at = excluded.updated_at
                    """,
                    [
                        str(transaction.id),
                        str(transaction.account_id),
                        json.dumps(dict(transaction.external_ids)),
                        float(transaction.amount),
                        transaction.description,
                        transaction.transaction_date,
                        transaction.posted_date,
                        list(transaction.tags),
                        transaction.created_at,
                        transaction.updated_at,
                    ],
                )

            conn.close()
            return Ok(transactions)
        except Exception as e:
            return Fail(f"Failed to bulk upsert transactions: {str(e)}")

    async def bulk_add_balances(self, user_id: UUID, balances: List[BalanceSnapshot]) -> Result[List[BalanceSnapshot]]:
        """Bulk add balance snapshots."""
        try:
            conn = self._get_connection(user_id)

            for balance in balances:
                conn.execute(
                    """
                    INSERT INTO balance_snapshots (
                        snapshot_id, account_id, balance, snapshot_time, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        str(balance.id),
                        str(balance.account_id),
                        float(balance.balance),
                        balance.snapshot_time,
                        balance.created_at,
                    ],
                )

            conn.close()
            return Ok(balances)
        except Exception as e:
            return Fail(f"Failed to bulk add balances: {str(e)}")

    async def update_account_by_id(self, user_id: UUID, account: Account) -> Result[Account]:
        """Update an account by ID."""
        try:
            conn = self._get_connection(user_id)

            conn.execute(
                """
                UPDATE accounts SET
                    name = ?, nickname = ?, account_type = ?, currency = ?,
                    external_ids = ?, institution_name = ?, institution_url = ?,
                    institution_domain = ?, updated_at = ?
                WHERE account_id = ?
                """,
                [
                    account.name,
                    account.nickname,
                    account.account_type,
                    account.currency,
                    json.dumps(dict(account.external_ids)),
                    account.institution_name,
                    account.institution_url,
                    account.institution_domain,
                    account.updated_at,
                    str(account.id),
                ],
            )

            conn.close()
            return Ok(account)
        except Exception as e:
            return Fail(f"Failed to update account: {str(e)}")

    async def get_accounts(self, user_id: UUID) -> Result[List[Account]]:
        """Get all accounts for a user."""
        try:
            conn = self._get_connection(user_id, read_only=True)

            result = conn.execute("SELECT * FROM accounts").fetchall()
            columns = [desc[0] for desc in conn.description]

            accounts = []
            for row in result:
                row_dict = dict(zip(columns, row))
                account = Account(
                    id=UUID(row_dict["account_id"]),
                    name=row_dict["name"],
                    nickname=row_dict["nickname"],
                    account_type=row_dict["account_type"],
                    currency=row_dict["currency"],
                    external_ids=MappingProxyType(json.loads(row_dict["external_ids"]) if row_dict["external_ids"] else {}),
                    institution_name=row_dict["institution_name"],
                    institution_url=row_dict["institution_url"],
                    institution_domain=row_dict["institution_domain"],
                    created_at=self._ensure_timezone(row_dict["created_at"]),
                    updated_at=self._ensure_timezone(row_dict["updated_at"]),
                )
                accounts.append(account)

            conn.close()
            return Ok(accounts)
        except Exception as e:
            return Fail(f"Failed to get accounts: {str(e)}")

    async def get_account_by_id(self, user_id: UUID, account_id: UUID) -> Result[Account]:
        """Get a single account by ID."""
        try:
            conn = self._get_connection(user_id, read_only=True)

            result = conn.execute(
                "SELECT * FROM accounts WHERE account_id = ?", [str(account_id)]
            ).fetchone()

            if not result:
                conn.close()
                return Fail("Account not found")

            columns = [desc[0] for desc in conn.description]
            row_dict = dict(zip(columns, result))

            account = Account(
                id=UUID(row_dict["account_id"]),
                name=row_dict["name"],
                nickname=row_dict["nickname"],
                account_type=row_dict["account_type"],
                currency=row_dict["currency"],
                external_ids=MappingProxyType(json.loads(row_dict["external_ids"]) if row_dict["external_ids"] else {}),
                institution_name=row_dict["institution_name"],
                institution_url=row_dict["institution_url"],
                institution_domain=row_dict["institution_domain"],
                created_at=row_dict["created_at"],
                updated_at=row_dict["updated_at"],
            )

            conn.close()
            return Ok(account)
        except Exception as e:
            return Fail(f"Failed to get account: {str(e)}")

    async def get_account_by_external_id(self, user_id: UUID, external_id: str) -> Result[Account]:
        """Get an account by external ID."""
        # This requires JSON querying which DuckDB supports
        return Fail("Not implemented")

    async def get_transactions_by_external_ids(
        self, user_id: UUID, external_ids: List[Dict[str, str]]
    ) -> Result[List[Transaction]]:
        """Get transactions by external IDs."""
        try:
            conn = self._get_connection(user_id, read_only=True)

            transactions = []
            for ext_id_obj in external_ids:
                # Query for transactions with matching external IDs
                result = conn.execute(
                    "SELECT * FROM transactions WHERE external_ids::VARCHAR LIKE ?",
                    [f'%{list(ext_id_obj.values())[0]}%']
                ).fetchall()

                columns = [desc[0] for desc in conn.description]

                for row in result:
                    row_dict = dict(zip(columns, row))
                    transaction = Transaction(
                        id=UUID(row_dict["transaction_id"]),
                        account_id=UUID(row_dict["account_id"]),
                        external_ids=MappingProxyType(json.loads(row_dict["external_ids"]) if row_dict["external_ids"] else {}),
                        amount=Decimal(str(row_dict["amount"])),
                        description=row_dict["description"],
                        transaction_date=self._ensure_timezone(row_dict["transaction_date"]),
                        posted_date=self._ensure_timezone(row_dict["posted_date"]),
                        tags=tuple(row_dict["tags"]) if row_dict["tags"] else tuple(),
                        created_at=self._ensure_timezone(row_dict["created_at"]),
                        updated_at=self._ensure_timezone(row_dict["updated_at"]),
                    )
                    transactions.append(transaction)

            conn.close()
            return Ok(transactions)
        except Exception as e:
            return Fail(f"Failed to get transactions: {str(e)}")

    async def get_balance_snapshots(
        self, user_id: UUID, account_id: UUID | None = None, date: str | None = None
    ) -> Result[List[BalanceSnapshot]]:
        """Get balance snapshots."""
        try:
            conn = self._get_connection(user_id, read_only=True)

            query = "SELECT * FROM balance_snapshots WHERE 1=1"
            params = []

            if account_id:
                query += " AND account_id = ?"
                params.append(str(account_id))

            if date:
                query += " AND DATE(snapshot_time) = ?"
                params.append(date)

            result = conn.execute(query, params).fetchall()
            columns = [desc[0] for desc in conn.description]

            balances = []
            for row in result:
                row_dict = dict(zip(columns, row))
                balance = BalanceSnapshot(
                    id=UUID(row_dict["snapshot_id"]),
                    account_id=UUID(row_dict["account_id"]),
                    balance=Decimal(str(row_dict["balance"])),
                    snapshot_time=row_dict["snapshot_time"],
                    created_at=row_dict["created_at"],
                    updated_at=datetime.now(datetime.now().astimezone().tzinfo),  # DuckDB doesn't store updated_at for balances
                )
                balances.append(balance)

            conn.close()
            return Ok(balances)
        except Exception as e:
            return Fail(f"Failed to get balance snapshots: {str(e)}")

    async def execute_query(self, user_id: UUID, sql: str) -> Result[Dict[str, Any]]:
        """Execute a SQL query and return structured results."""
        try:
            conn = self._get_connection(user_id, read_only=True)

            result = conn.execute(sql).fetchall()
            columns = [desc[0] for desc in conn.description] if conn.description else []

            conn.close()
            return Ok({
                "columns": columns,
                "rows": result,  # Return raw tuples, not dicts
                "row_count": len(result)
            })
        except Exception as e:
            return Fail(f"Failed to execute query: {str(e)}")

    async def get_schema_info(self, user_id: UUID) -> Result[Dict[str, Any]]:
        """Get complete schema information for all tables."""
        try:
            conn = self._get_connection(user_id, read_only=True)

            # Get all tables
            tables_result = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()

            schema_info = {}

            for (table_name,) in tables_result:
                # Get column information
                columns_result = conn.execute(f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position
                """).fetchall()

                # Get sample data
                sample_result = conn.execute(f"SELECT * FROM {table_name} LIMIT 3").fetchall()
                column_names = [desc[0] for desc in conn.description] if conn.description else []

                schema_info[table_name] = {
                    "columns": [
                        {"name": col[0], "type": col[1]}
                        for col in columns_result
                    ],
                    "sample_data": {
                        "columns": column_names,
                        "rows": sample_result
                    }
                }

            conn.close()
            return Ok(schema_info)
        except Exception as e:
            return Fail(f"Failed to get schema info: {str(e)}")

    async def get_date_range_info(self, user_id: UUID) -> Result[Dict[str, Any]]:
        """Get date range information for transactions."""
        try:
            conn = self._get_connection(user_id, read_only=True)

            result = conn.execute("""
                SELECT
                    MIN(transaction_date) as earliest_date,
                    MAX(transaction_date) as latest_date,
                    COUNT(*) as total_transactions
                FROM transactions
            """).fetchone()

            conn.close()

            if not result or not result[0] or not result[1]:
                return Ok({
                    "earliest_date": None,
                    "latest_date": None,
                    "total_transactions": 0,
                    "days_range": None
                })

            earliest = result[0]
            latest = result[1]
            total = result[2]

            # Calculate date range in days
            from datetime import datetime
            if isinstance(earliest, datetime) and isinstance(latest, datetime):
                days_range = (latest - earliest).days
            else:
                days_range = None

            return Ok({
                "earliest_date": earliest,
                "latest_date": latest,
                "total_transactions": total,
                "days_range": days_range
            })
        except Exception as e:
            return Fail(f"Failed to get date range info: {str(e)}")

    async def upsert_integration(
        self, user_id: UUID, integration_name: str, integration_options: Dict[str, Any]
    ) -> Result[None]:
        """Upsert integration settings."""
        try:
            conn = self._get_connection(user_id)

            now = datetime.now(timezone.utc)
            conn.execute(
                """
                INSERT INTO integrations (user_id, integration_name, integration_settings, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (user_id, integration_name) DO UPDATE SET
                    integration_settings = excluded.integration_settings,
                    updated_at = ?
                """,
                [str(user_id), integration_name, json.dumps(integration_options), now, now, now],
            )

            conn.close()
            return Ok(None)
        except Exception as e:
            return Fail(f"Failed to upsert integration: {str(e)}")

    async def list_integrations(self, user_id: UUID) -> Result[List[Dict[str, Any]]]:
        """List all integrations for a user."""
        try:
            conn = self._get_connection(user_id, read_only=True)

            result = conn.execute(
                "SELECT integration_name, integration_settings FROM integrations WHERE user_id = ?",
                [str(user_id)],
            ).fetchall()

            integrations = [
                {"integrationName": row[0], "integrationOptions": json.loads(row[1])}
                for row in result
            ]

            conn.close()
            return Ok(integrations)
        except Exception as e:
            return Fail(f"Failed to list integrations: {str(e)}")

    async def get_integration_settings(self, user_id: UUID, integration_name: str) -> Result[Dict[str, Any]]:
        """Get settings for a specific integration."""
        try:
            conn = self._get_connection(user_id, read_only=True)

            result = conn.execute(
                "SELECT integration_settings FROM integrations WHERE user_id = ? AND integration_name = ?",
                [str(user_id), integration_name],
            ).fetchone()

            if not result:
                conn.close()
                return Ok({})

            settings = json.loads(result[0])
            conn.close()
            return Ok(settings)
        except Exception as e:
            return Fail(f"Failed to get integration settings: {str(e)}")

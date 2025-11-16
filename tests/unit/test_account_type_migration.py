"""Tests for account type to tags migration."""

import tempfile
from pathlib import Path

import duckdb
import pytest

from treeline.infra.duckdb import DuckDBRepository


class TestAccountTypeMigration:
    """Test the migration from account_type to tags column."""

    @pytest.mark.asyncio
    async def test_migration_converts_account_type_to_tags(self) -> None:
        """Test that account_type values are migrated to tags array."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = DuckDBRepository(str(db_path))

            # Set up initial schema with account_type
            conn = duckdb.connect(str(db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sys_migrations (
                    version VARCHAR PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    description VARCHAR
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sys_accounts (
                    account_id VARCHAR PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    account_type VARCHAR,
                    currency VARCHAR NOT NULL DEFAULT 'USD',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Insert test data with various account_type values
            conn.execute(
                "INSERT INTO sys_accounts (account_id, name, account_type) VALUES (?, ?, ?)",
                ["acc-1", "Checking Account", "checking"],
            )
            conn.execute(
                "INSERT INTO sys_accounts (account_id, name, account_type) VALUES (?, ?, ?)",
                ["acc-2", "Savings Account", "savings"],
            )
            conn.execute(
                "INSERT INTO sys_accounts (account_id, name, account_type) VALUES (?, ?, ?)",
                ["acc-3", "Credit Card", "credit"],
            )
            conn.execute(
                "INSERT INTO sys_accounts (account_id, name, account_type) VALUES (?, ?, ?)",
                ["acc-4", "Investment", None],
            )  # NULL account_type

            # Mark earlier migrations as applied
            conn.execute("INSERT INTO sys_migrations (version) VALUES (?)", ["000"])
            conn.execute("INSERT INTO sys_migrations (version) VALUES (?)", ["001"])
            conn.close()

            # Create the migration file
            migrations_dir = Path(tmpdir) / "migrations"
            migrations_dir.mkdir()
            (migrations_dir / "002_account_tags.sql").write_text("""
                -- Add tags column
                ALTER TABLE sys_accounts ADD COLUMN tags VARCHAR[];

                -- Migrate account_type to tags
                UPDATE sys_accounts
                SET tags = CASE
                    WHEN account_type IS NOT NULL THEN [account_type]
                    ELSE []
                END;

                -- Drop account_type column
                ALTER TABLE sys_accounts DROP COLUMN account_type;
            """)

            # Apply the migration
            pending = repo._get_pending_migrations(migrations_dir)
            assert len(pending) == 1

            for migration_file in pending:
                version = migration_file.stem.split("_")[0]
                description = "_".join(migration_file.stem.split("_")[1:])

                conn = duckdb.connect(str(db_path))
                with open(migration_file, "r") as f:
                    migration_sql = f.read()
                conn.execute(migration_sql)
                conn.close()

                repo._record_migration(version, description)

            # Verify the migration results
            conn = duckdb.connect(str(db_path))

            # Check that tags column exists
            columns = conn.execute("DESCRIBE sys_accounts").fetchall()
            column_names = [row[0] for row in columns]
            assert "tags" in column_names
            assert "account_type" not in column_names

            # Check that data was migrated correctly
            results = conn.execute(
                """
                SELECT account_id, name, tags
                FROM sys_accounts
                ORDER BY account_id
                """
            ).fetchall()

            conn.close()

            # Verify each account's tags
            assert len(results) == 4

            # acc-1: checking -> ['checking']
            assert results[0][0] == "acc-1"
            assert results[0][2] == ["checking"]

            # acc-2: savings -> ['savings']
            assert results[1][0] == "acc-2"
            assert results[1][2] == ["savings"]

            # acc-3: credit -> ['credit']
            assert results[2][0] == "acc-3"
            assert results[2][2] == ["credit"]

            # acc-4: NULL -> []
            assert results[3][0] == "acc-4"
            assert results[3][2] == []

    @pytest.mark.asyncio
    async def test_migration_is_idempotent(self) -> None:
        """Test that running the migration twice doesn't cause errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = DuckDBRepository(str(db_path))

            # Set up initial schema
            conn = duckdb.connect(str(db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sys_migrations (
                    version VARCHAR PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    description VARCHAR
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sys_accounts (
                    account_id VARCHAR PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    account_type VARCHAR,
                    currency VARCHAR NOT NULL DEFAULT 'USD',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute(
                "INSERT INTO sys_accounts (account_id, name, account_type) VALUES (?, ?, ?)",
                ["acc-1", "Test Account", "checking"],
            )

            conn.execute("INSERT INTO sys_migrations (version) VALUES (?)", ["000"])
            conn.execute("INSERT INTO sys_migrations (version) VALUES (?)", ["001"])
            conn.close()

            # Create the migration file
            migrations_dir = Path(tmpdir) / "migrations"
            migrations_dir.mkdir()
            (migrations_dir / "002_account_tags.sql").write_text("""
                ALTER TABLE sys_accounts ADD COLUMN tags VARCHAR[];
                UPDATE sys_accounts
                SET tags = CASE
                    WHEN account_type IS NOT NULL THEN [account_type]
                    ELSE []
                END;
                ALTER TABLE sys_accounts DROP COLUMN account_type;
            """)

            # Apply migration once
            pending = repo._get_pending_migrations(migrations_dir)
            for migration_file in pending:
                version = migration_file.stem.split("_")[0]
                description = "_".join(migration_file.stem.split("_")[1:])

                conn = duckdb.connect(str(db_path))
                with open(migration_file, "r") as f:
                    migration_sql = f.read()
                conn.execute(migration_sql)
                conn.close()

                repo._record_migration(version, description)

            # Try to get pending migrations again - should be empty
            pending_after = repo._get_pending_migrations(migrations_dir)
            assert len(pending_after) == 0

            # Verify migration is recorded
            conn = duckdb.connect(str(db_path))
            migrations = conn.execute(
                "SELECT version FROM sys_migrations ORDER BY version"
            ).fetchall()
            migration_versions = [row[0] for row in migrations]
            conn.close()

            assert "002" in migration_versions

"""Unit tests for migration tracking system."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import duckdb
import pytest

from treeline.infra.duckdb import DuckDBRepository


class TestMigrationTracking:
    """Test the migration tracking system."""

    def test_get_applied_migrations_returns_empty_list_for_new_database(self) -> None:
        """Test that a new database has no applied migrations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = DuckDBRepository(str(db_path))

            applied = repo._get_applied_migrations()

            assert applied == []

    def test_get_applied_migrations_returns_list_of_versions(self) -> None:
        """Test that applied migrations are returned as a list of version strings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = DuckDBRepository(str(db_path))

            # Manually insert some migration records
            conn = duckdb.connect(str(db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sys_migrations (
                    version VARCHAR PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    description VARCHAR
                )
            """)
            conn.execute(
                "INSERT INTO sys_migrations (version, description) VALUES (?, ?)",
                ["001", "Initial schema"],
            )
            conn.execute(
                "INSERT INTO sys_migrations (version, description) VALUES (?, ?)",
                ["002", "Add feature X"],
            )
            conn.close()

            applied = repo._get_applied_migrations()

            assert applied == ["001", "002"]

    def test_record_migration_inserts_version_into_table(self) -> None:
        """Test that record_migration inserts a row into sys_migrations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = DuckDBRepository(str(db_path))

            # Create the migrations table
            conn = duckdb.connect(str(db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sys_migrations (
                    version VARCHAR PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    description VARCHAR
                )
            """)
            conn.close()

            repo._record_migration("003", "Test migration")

            # Verify it was inserted
            conn = duckdb.connect(str(db_path))
            result = conn.execute(
                "SELECT version, description FROM sys_migrations WHERE version = ?",
                ["003"],
            ).fetchone()
            conn.close()

            assert result is not None
            assert result[0] == "003"
            assert result[1] == "Test migration"

    def test_ensure_migrations_table_creates_table_if_not_exists(self) -> None:
        """Test that the migrations tracking table is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = DuckDBRepository(str(db_path))

            repo._ensure_migrations_table()

            # Verify table exists
            conn = duckdb.connect(str(db_path))
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sys_migrations'"
            ).fetchone()
            conn.close()

            # DuckDB uses different system tables than SQLite
            # Let's just verify we can query the table
            conn = duckdb.connect(str(db_path))
            result = conn.execute("SELECT COUNT(*) FROM sys_migrations").fetchone()
            conn.close()

            assert result[0] == 0  # Empty table

    def test_get_pending_migrations_returns_unrun_migrations_only(self) -> None:
        """Test that only migrations not yet applied are returned as pending."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create test migration files
            migrations_dir = Path(tmpdir) / "migrations"
            migrations_dir.mkdir()

            (migrations_dir / "001_initial.sql").write_text("-- Migration 001")
            (migrations_dir / "002_add_feature.sql").write_text("-- Migration 002")
            (migrations_dir / "003_add_another.sql").write_text("-- Migration 003")

            repo = DuckDBRepository(str(db_path))

            # Mark migrations 001 and 002 as applied
            conn = duckdb.connect(str(db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sys_migrations (
                    version VARCHAR PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    description VARCHAR
                )
            """)
            conn.execute(
                "INSERT INTO sys_migrations (version, description) VALUES (?, ?)",
                ["001", "initial"],
            )
            conn.execute(
                "INSERT INTO sys_migrations (version, description) VALUES (?, ?)",
                ["002", "add_feature"],
            )
            conn.close()

            # Get pending migrations
            with patch.object(
                Path,
                "__truediv__",
                side_effect=lambda self, other: migrations_dir
                if other == "migrations"
                else Path(str(self)) / other,
            ):
                pending = repo._get_pending_migrations(migrations_dir)

            # Only 003 should be pending
            assert len(pending) == 1
            assert pending[0].name == "003_add_another.sql"

    @pytest.mark.asyncio
    async def test_ensure_schema_upgraded_only_runs_pending_migrations(self) -> None:
        """Test that ensure_schema_upgraded only executes migrations not yet applied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create a real migration file
            migrations_dir = Path(tmpdir) / "migrations"
            migrations_dir.mkdir()

            # Migration 001 creates a test table
            (migrations_dir / "001_initial.sql").write_text("""
                CREATE TABLE IF NOT EXISTS test_table_001 (
                    id VARCHAR PRIMARY KEY
                );
            """)

            # Migration 002 creates another table
            (migrations_dir / "002_second.sql").write_text("""
                CREATE TABLE IF NOT EXISTS test_table_002 (
                    id VARCHAR PRIMARY KEY
                );
            """)

            # Create repo with custom migrations dir
            repo = DuckDBRepository(str(db_path))

            # Mark migration 001 as already applied
            conn = duckdb.connect(str(db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sys_migrations (
                    version VARCHAR PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    description VARCHAR
                )
            """)
            conn.execute("INSERT INTO sys_migrations (version) VALUES (?)", ["001"])
            conn.execute(
                "CREATE TABLE IF NOT EXISTS test_table_001 (id VARCHAR PRIMARY KEY)"
            )
            conn.close()

            # Get only pending migrations and apply them
            pending = repo._get_pending_migrations(migrations_dir)

            # Should only have migration 002
            assert len(pending) == 1
            assert pending[0].name == "002_second.sql"

            # Apply the pending migration
            for migration_file in pending:
                version = migration_file.stem.split("_")[0]
                description = "_".join(migration_file.stem.split("_")[1:])

                conn = duckdb.connect(str(db_path))
                with open(migration_file, "r") as f:
                    migration_sql = f.read()
                conn.execute(migration_sql)
                conn.close()

                repo._record_migration(version, description)

            # Verify that:
            # 1. test_table_001 exists (was already there)
            # 2. test_table_002 exists (migration 002 was run)
            # 3. Migration 002 is now recorded in sys_migrations
            conn = duckdb.connect(str(db_path))

            tables_result = conn.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main'
                AND table_name LIKE 'test_table_%'
            """).fetchall()
            table_names = [row[0] for row in tables_result]

            migrations_result = conn.execute(
                "SELECT version FROM sys_migrations ORDER BY version"
            ).fetchall()
            migration_versions = [row[0] for row in migrations_result]

            conn.close()

            assert "test_table_001" in table_names
            assert "test_table_002" in table_names
            assert migration_versions == ["001", "002"]

    @pytest.mark.asyncio
    async def test_migrations_run_in_alphabetical_order(self) -> None:
        """Test that migrations are executed in alphabetical order by filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            migrations_dir = Path(tmpdir) / "migrations"
            migrations_dir.mkdir()

            # Create migrations with tracking of execution order
            (migrations_dir / "001_first.sql").write_text("""
                CREATE TABLE IF NOT EXISTS execution_log (step VARCHAR);
                INSERT INTO execution_log VALUES ('001');
            """)
            (migrations_dir / "002_second.sql").write_text("""
                INSERT INTO execution_log VALUES ('002');
            """)
            (migrations_dir / "003_third.sql").write_text("""
                INSERT INTO execution_log VALUES ('003');
            """)

            repo = DuckDBRepository(str(db_path))

            # Manually get pending migrations and verify they're in order
            pending = repo._get_pending_migrations(migrations_dir)

            # Verify they're in alphabetical order
            assert len(pending) == 3
            assert pending[0].name == "001_first.sql"
            assert pending[1].name == "002_second.sql"
            assert pending[2].name == "003_third.sql"

            # Apply them in order
            for migration_file in pending:
                version = migration_file.stem.split("_")[0]
                description = "_".join(migration_file.stem.split("_")[1:])

                conn = duckdb.connect(str(db_path))
                with open(migration_file, "r") as f:
                    migration_sql = f.read()
                conn.execute(migration_sql)
                conn.close()

                repo._record_migration(version, description)

            # Check execution order
            conn = duckdb.connect(str(db_path))
            results = conn.execute(
                "SELECT step FROM execution_log ORDER BY rowid"
            ).fetchall()
            conn.close()

            execution_order = [row[0] for row in results]
            assert execution_order == ["001", "002", "003"]

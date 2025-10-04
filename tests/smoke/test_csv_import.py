"""Smoke test for CSV import flow."""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from treeline.app.service import ImportService
from treeline.infra.csv_provider import CSVProvider
from treeline.infra.duckdb import DuckDBRepository


@pytest.mark.asyncio
async def test_csv_import_end_to_end():
    """Test the complete CSV import flow from file to database."""
    # Setup: Create temporary database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        repository = DuckDBRepository(db_path)
        provider_registry = {"csv": CSVProvider()}
        import_service = ImportService(repository, provider_registry)

        user_id = uuid4()

        # Initialize database and user
        await repository.ensure_db_exists()
        await repository.ensure_schema_upgraded()
        await repository.ensure_user_db_initialized(user_id)

        # Create an account to import into
        from treeline.domain import Account
        from datetime import datetime, timezone

        account = Account(
            id=uuid4(),
            name="Test Checking",
            currency="USD",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        account_result = await repository.add_account(user_id, account)
        assert account_result.success

        # Create a test CSV file
        csv_content = """Date,Description,Amount
2024-10-01,Coffee at Starbucks,-5.50
2024-10-02,Grocery Store,-45.00
2024-10-03,Salary Deposit,2500.00
2024-10-01,Coffee at Starbucks,-5.50
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            # First import - should import all 4 transactions
            result1 = await import_service.import_transactions(
                user_id=user_id,
                source_type="csv",
                account_id=account.id,
                source_options={
                    "file_path": csv_path,
                    "column_mapping": {
                        "date": "Date",
                        "description": "Description",
                        "amount": "Amount"
                    }
                }
            )

            assert result1.success, f"First import failed: {result1.error}"
            assert result1.data["discovered"] == 4
            assert result1.data["imported"] == 4
            assert result1.data["skipped"] == 0

            # Verify transactions were stored
            query_result = await repository.execute_query(
                user_id, "SELECT COUNT(*) as count FROM transactions"
            )
            assert query_result.success
            assert query_result.data["rows"][0][0] == 4

            # Second import - same CSV, should skip duplicates
            result2 = await import_service.import_transactions(
                user_id=user_id,
                source_type="csv",
                account_id=account.id,
                source_options={
                    "file_path": csv_path,
                    "column_mapping": {
                        "date": "Date",
                        "description": "Description",
                        "amount": "Amount"
                    }
                }
            )

            assert result2.success, f"Second import failed: {result2.error}"
            assert result2.data["discovered"] == 4
            assert result2.data["imported"] == 0  # All duplicates
            assert result2.data["skipped"] == 4

            # Verify count didn't change
            query_result = await repository.execute_query(
                user_id, "SELECT COUNT(*) as count FROM transactions"
            )
            assert query_result.success
            assert query_result.data["rows"][0][0] == 4

        finally:
            Path(csv_path).unlink()


@pytest.mark.asyncio
async def test_csv_import_with_partial_duplicates():
    """Test CSV import when some transactions are duplicates and some are new."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        repository = DuckDBRepository(db_path)
        provider_registry = {"csv": CSVProvider()}
        import_service = ImportService(repository, provider_registry)

        user_id = uuid4()

        # Initialize
        await repository.ensure_db_exists()
        await repository.ensure_schema_upgraded()
        await repository.ensure_user_db_initialized(user_id)

        from treeline.domain import Account
        from datetime import datetime, timezone

        account = Account(
            id=uuid4(),
            name="Test Account",
            currency="USD",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await repository.add_account(user_id, account)

        # First CSV with 2 identical transactions
        csv1_content = """Date,Description,Amount
2024-10-01,Coffee,-5.50
2024-10-01,Coffee,-5.50
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv1_content)
            csv1_path = f.name

        # Second CSV with 3 identical transactions (1 more than first)
        csv2_content = """Date,Description,Amount
2024-10-01,Coffee,-5.50
2024-10-01,Coffee,-5.50
2024-10-01,Coffee,-5.50
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv2_content)
            csv2_path = f.name

        try:
            # Import first CSV - 2 transactions
            result1 = await import_service.import_transactions(
                user_id=user_id,
                source_type="csv",
                account_id=account.id,
                source_options={
                    "file_path": csv1_path,
                    "column_mapping": {"date": "Date", "description": "Description", "amount": "Amount"}
                }
            )

            assert result1.success
            assert result1.data["imported"] == 2

            # Import second CSV - 3 transactions, 2 existing, 1 new
            result2 = await import_service.import_transactions(
                user_id=user_id,
                source_type="csv",
                account_id=account.id,
                source_options={
                    "file_path": csv2_path,
                    "column_mapping": {"date": "Date", "description": "Description", "amount": "Amount"}
                }
            )

            assert result2.success
            assert result2.data["discovered"] == 3
            assert result2.data["imported"] == 1  # Only 1 new
            assert result2.data["skipped"] == 2

            # Verify total count is 3
            query_result = await repository.execute_query(
                user_id, "SELECT COUNT(*) as count FROM transactions"
            )
            assert query_result.success
            assert query_result.data["rows"][0][0] == 3

        finally:
            Path(csv1_path).unlink()
            Path(csv2_path).unlink()

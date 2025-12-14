"""Service for database health checks and diagnostics."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Literal

from treeline.abstractions import Repository
from treeline.domain import Ok, Result


@dataclass
class HealthCheck:
    """Result of a single health check."""

    name: str
    status: Literal["pass", "warning", "error"]
    message: str
    details: list[dict[str, Any]] | None = None


@dataclass
class HealthReport:
    """Complete health report with all checks."""

    checks: list[HealthCheck]
    passed: int
    warnings: int
    errors: int


class DoctorService:
    """Service for database health checks and diagnostics."""

    def __init__(self, repository: Repository):
        self.repository = repository

    async def run_all_checks(self) -> Result[HealthReport]:
        """Run all health checks and return a complete report."""
        checks = [
            await self._check_orphaned_transactions(),
            await self._check_orphaned_snapshots(),
            await self._check_duplicate_fingerprints(),
            await self._check_date_sanity(),
            await self._check_untagged_transactions(),
            await self._check_balance_consistency(),
        ]

        passed = sum(1 for c in checks if c.status == "pass")
        warnings = sum(1 for c in checks if c.status == "warning")
        errors = sum(1 for c in checks if c.status == "error")

        return Ok(
            data=HealthReport(
                checks=checks,
                passed=passed,
                warnings=warnings,
                errors=errors,
            )
        )

    async def _check_orphaned_transactions(self) -> HealthCheck:
        """Check for transactions referencing non-existent accounts."""
        query = """
            SELECT
                t.transaction_id,
                t.account_id,
                t.description,
                t.amount
            FROM sys_transactions t
            LEFT JOIN sys_accounts a ON t.account_id = a.account_id
            WHERE a.account_id IS NULL
            LIMIT 100
        """
        result = await self.repository.execute_query(query)

        if not result.success:
            return HealthCheck(
                name="orphaned_transactions",
                status="error",
                message=f"Failed to check: {result.error}",
            )

        rows = result.data.get("rows", [])
        count = len(rows)

        if count == 0:
            return HealthCheck(
                name="orphaned_transactions",
                status="pass",
                message="No orphaned transactions found",
            )

        details = [
            {
                "transaction_id": row[0],
                "account_id": row[1],
                "description": row[2],
                "amount": float(row[3]) if row[3] else None,
            }
            for row in rows
        ]

        return HealthCheck(
            name="orphaned_transactions",
            status="error",
            message=f"{count} transaction(s) reference missing accounts",
            details=details,
        )

    async def _check_orphaned_snapshots(self) -> HealthCheck:
        """Check for balance snapshots referencing non-existent accounts."""
        query = """
            SELECT
                s.snapshot_id,
                s.account_id,
                s.balance,
                s.snapshot_time
            FROM sys_balance_snapshots s
            LEFT JOIN sys_accounts a ON s.account_id = a.account_id
            WHERE a.account_id IS NULL
            LIMIT 100
        """
        result = await self.repository.execute_query(query)

        if not result.success:
            return HealthCheck(
                name="orphaned_snapshots",
                status="error",
                message=f"Failed to check: {result.error}",
            )

        rows = result.data.get("rows", [])
        count = len(rows)

        if count == 0:
            return HealthCheck(
                name="orphaned_snapshots",
                status="pass",
                message="No orphaned snapshots found",
            )

        details = [
            {
                "snapshot_id": row[0],
                "account_id": row[1],
                "balance": float(row[2]) if row[2] else None,
                "snapshot_time": str(row[3]) if row[3] else None,
            }
            for row in rows
        ]

        return HealthCheck(
            name="orphaned_snapshots",
            status="error",
            message=f"{count} snapshot(s) reference missing accounts",
            details=details,
        )

    async def _check_duplicate_fingerprints(self) -> HealthCheck:
        """Check for transactions with duplicate fingerprints (potential duplicates)."""
        # Look for fingerprints that appear more than once within the same account
        # Exclude soft-deleted transactions from this check
        # Use json_extract_string for DuckDB compatibility
        query = """
            SELECT
                json_extract_string(external_ids, '$.fingerprint') as fingerprint,
                account_id,
                COUNT(*) as count
            FROM sys_transactions
            WHERE deleted_at IS NULL
              AND json_extract_string(external_ids, '$.fingerprint') IS NOT NULL
            GROUP BY json_extract_string(external_ids, '$.fingerprint'), account_id
            HAVING COUNT(*) > 1
            LIMIT 50
        """
        result = await self.repository.execute_query(query)

        if not result.success:
            return HealthCheck(
                name="duplicate_fingerprints",
                status="error",
                message=f"Failed to check: {result.error}",
            )

        rows = result.data.get("rows", [])
        count = len(rows)

        if count == 0:
            return HealthCheck(
                name="duplicate_fingerprints",
                status="pass",
                message="No duplicate fingerprints found",
            )

        # Get details about the duplicates
        details = []
        for row in rows[:10]:  # Limit details to first 10 sets
            fingerprint = row[0]
            account_id = row[1]
            dup_count = row[2]

            # Get the actual transactions
            detail_query = f"""
                SELECT transaction_id, transaction_date, amount, description
                FROM sys_transactions
                WHERE json_extract_string(external_ids, '$.fingerprint') = '{fingerprint}'
                  AND account_id = '{account_id}'
                  AND deleted_at IS NULL
                LIMIT 5
            """
            detail_result = await self.repository.execute_query(detail_query)
            if detail_result.success:
                txns = [
                    {
                        "transaction_id": r[0],
                        "date": str(r[1]) if r[1] else None,
                        "amount": float(r[2]) if r[2] else None,
                        "description": r[3],
                    }
                    for r in detail_result.data.get("rows", [])
                ]
                details.append(
                    {
                        "fingerprint": fingerprint[:16] + "...",
                        "account_id": account_id,
                        "duplicate_count": dup_count,
                        "transactions": txns,
                    }
                )

        return HealthCheck(
            name="duplicate_fingerprints",
            status="warning",
            message=f"{count} set(s) of potential duplicate transactions found",
            details=details,
        )

    async def _check_date_sanity(self) -> HealthCheck:
        """Check for transactions with unreasonable dates."""
        today = date.today()
        far_future = today + timedelta(days=365)  # More than 1 year in future
        ancient_past = date(1970, 1, 1)

        query = f"""
            SELECT
                transaction_id,
                transaction_date,
                description,
                amount
            FROM sys_transactions
            WHERE deleted_at IS NULL
              AND (transaction_date > '{far_future}' OR transaction_date < '{ancient_past}')
            LIMIT 100
        """
        result = await self.repository.execute_query(query)

        if not result.success:
            return HealthCheck(
                name="date_sanity",
                status="error",
                message=f"Failed to check: {result.error}",
            )

        rows = result.data.get("rows", [])
        count = len(rows)

        if count == 0:
            return HealthCheck(
                name="date_sanity",
                status="pass",
                message="All transaction dates are valid",
            )

        details = [
            {
                "transaction_id": row[0],
                "date": str(row[1]) if row[1] else None,
                "description": row[2],
                "amount": float(row[3]) if row[3] else None,
            }
            for row in rows
        ]

        return HealthCheck(
            name="date_sanity",
            status="error",
            message=f"{count} transaction(s) have unreasonable dates",
            details=details,
        )

    async def _check_untagged_transactions(self) -> HealthCheck:
        """Check for transactions without any tags (informational)."""
        query = """
            SELECT COUNT(*) as untagged_count
            FROM sys_transactions
            WHERE deleted_at IS NULL
              AND (tags IS NULL OR array_length(tags, 1) IS NULL OR array_length(tags, 1) = 0)
        """
        result = await self.repository.execute_query(query)

        if not result.success:
            return HealthCheck(
                name="untagged_transactions",
                status="error",
                message=f"Failed to check: {result.error}",
            )

        rows = result.data.get("rows", [])
        count = rows[0][0] if rows else 0

        # Also get total count for percentage
        total_query = """
            SELECT COUNT(*) FROM sys_transactions WHERE deleted_at IS NULL
        """
        total_result = await self.repository.execute_query(total_query)
        total = (
            total_result.data.get("rows", [[0]])[0][0]
            if total_result.success
            else 0
        )

        if count == 0:
            return HealthCheck(
                name="untagged_transactions",
                status="pass",
                message="All transactions are tagged",
            )

        percentage = (count / total * 100) if total > 0 else 0

        return HealthCheck(
            name="untagged_transactions",
            status="warning",
            message=f"{count} transaction(s) have no tags ({percentage:.0f}% of total)",
            details=[{"untagged_count": count, "total_count": total}],
        )

    async def _check_balance_consistency(self) -> HealthCheck:
        """Check for accounts with mismatched transaction/balance freshness.

        Warns if an account has recent transactions but no recent balance snapshot,
        or has a recent balance snapshot but no recent transactions. This helps
        catch sync issues or remind users to update their data.
        """
        # Compare latest transaction date vs latest balance snapshot date per account
        # "Recent" means within the last 7 days
        query = """
            WITH latest_txn AS (
                SELECT
                    account_id,
                    MAX(transaction_date) as latest_txn_date
                FROM sys_transactions
                WHERE deleted_at IS NULL
                GROUP BY account_id
            ),
            latest_snapshot AS (
                SELECT
                    account_id,
                    MAX(snapshot_time::date) as latest_snapshot_date
                FROM sys_balance_snapshots
                GROUP BY account_id
            )
            SELECT
                a.account_id,
                a.name as account_name,
                lt.latest_txn_date,
                ls.latest_snapshot_date
            FROM sys_accounts a
            LEFT JOIN latest_txn lt ON a.account_id = lt.account_id
            LEFT JOIN latest_snapshot ls ON a.account_id = ls.account_id
        """
        result = await self.repository.execute_query(query)

        if not result.success:
            return HealthCheck(
                name="balance_consistency",
                status="pass",
                message="Balance check skipped (query not supported)",
            )

        rows = result.data.get("rows", [])

        if not rows:
            return HealthCheck(
                name="balance_consistency",
                status="pass",
                message="No accounts to check",
            )

        issues = []
        today = date.today()
        staleness_threshold = timedelta(days=30)  # Consider "stale" if >30 days difference

        for row in rows:
            account_id = row[0]
            account_name = row[1]
            latest_txn_date = row[2]
            latest_snapshot_date = row[3]

            # Skip accounts with no data at all
            if latest_txn_date is None and latest_snapshot_date is None:
                continue

            # Convert to date objects if needed
            if latest_txn_date and not isinstance(latest_txn_date, date):
                latest_txn_date = date.fromisoformat(str(latest_txn_date)[:10])
            if latest_snapshot_date and not isinstance(latest_snapshot_date, date):
                latest_snapshot_date = date.fromisoformat(str(latest_snapshot_date)[:10])

            # Check for significant mismatch
            if latest_txn_date and latest_snapshot_date:
                diff = abs((latest_txn_date - latest_snapshot_date).days)
                if diff > staleness_threshold.days:
                    if latest_txn_date > latest_snapshot_date:
                        issues.append({
                            "account_id": account_id,
                            "account_name": account_name,
                            "issue": "transactions_newer",
                            "latest_transaction": str(latest_txn_date),
                            "latest_snapshot": str(latest_snapshot_date),
                            "days_difference": diff,
                        })
                    else:
                        issues.append({
                            "account_id": account_id,
                            "account_name": account_name,
                            "issue": "snapshot_newer",
                            "latest_transaction": str(latest_txn_date),
                            "latest_snapshot": str(latest_snapshot_date),
                            "days_difference": diff,
                        })
            elif latest_txn_date and not latest_snapshot_date:
                # Has transactions but no balance snapshots
                issues.append({
                    "account_id": account_id,
                    "account_name": account_name,
                    "issue": "no_snapshots",
                    "latest_transaction": str(latest_txn_date),
                    "latest_snapshot": None,
                })
            elif latest_snapshot_date and not latest_txn_date:
                # Has balance snapshot but no transactions
                issues.append({
                    "account_id": account_id,
                    "account_name": account_name,
                    "issue": "no_transactions",
                    "latest_transaction": None,
                    "latest_snapshot": str(latest_snapshot_date),
                })

        if not issues:
            return HealthCheck(
                name="balance_consistency",
                status="pass",
                message="Transaction and balance data are in sync",
            )

        return HealthCheck(
            name="balance_consistency",
            status="warning",
            message=f"{len(issues)} account(s) may need attention",
            details=issues,
        )

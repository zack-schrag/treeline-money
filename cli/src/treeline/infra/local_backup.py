"""Local filesystem backup storage implementation."""

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from treeline.abstractions import BackupStorageProvider
from treeline.domain import BackupMetadata, Fail, Ok, Result
from treeline.utils import get_logger

logger = get_logger("backup")


class LocalBackupStorage(BackupStorageProvider):
    """Local filesystem backup storage.

    Stores backups as timestamped copies of the database file.
    Backup naming: treeline-YYYY-MM-DDTHH-MM-SS.duckdb
    """

    def __init__(self, backup_dir: Path):
        """Initialize local backup storage.

        Args:
            backup_dir: Directory where backups will be stored
        """
        self._backup_dir = backup_dir

    def _ensure_backup_dir(self) -> None:
        """Ensure backup directory exists."""
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def _generate_backup_name(self) -> str:
        """Generate a timestamped backup filename.

        Uses microseconds for uniqueness when multiple backups are created quickly.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%f")
        return f"treeline-{timestamp}.duckdb"

    def _parse_backup_time(self, backup_name: str) -> datetime | None:
        """Parse creation time from backup filename.

        Args:
            backup_name: Backup filename like "treeline-2025-01-15T10-30-00-123456.duckdb"

        Returns:
            datetime if parseable, None otherwise
        """
        try:
            # Extract timestamp portion: treeline-YYYY-MM-DDTHH-MM-SS-ffffff.duckdb
            if not backup_name.startswith("treeline-") or not backup_name.endswith(
                ".duckdb"
            ):
                return None

            timestamp_str = backup_name[9:-7]  # Remove "treeline-" and ".duckdb"

            # Try parsing with microseconds first, then fall back to seconds-only
            try:
                dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H-%M-%S-%f")
            except ValueError:
                # Fall back to seconds-only format for backwards compatibility
                dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H-%M-%S")

            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    async def create_backup(self, source_path: Path) -> Result[BackupMetadata]:
        """Create a backup of the source file.

        Args:
            source_path: Path to the file to backup (e.g., DuckDB database)

        Returns:
            Result containing BackupMetadata for the created backup
        """
        try:
            if not source_path.exists():
                return Fail(f"Source file not found: {source_path}")

            self._ensure_backup_dir()

            backup_name = self._generate_backup_name()
            backup_path = self._backup_dir / backup_name

            # Copy the file
            shutil.copy2(source_path, backup_path)

            # Get file stats
            stats = backup_path.stat()

            metadata = BackupMetadata(
                name=backup_name,
                created_at=datetime.now(timezone.utc),
                size_bytes=stats.st_size,
            )

            logger.info(f"Created backup: {backup_name} ({stats.st_size} bytes)")
            return Ok(metadata)

        except PermissionError as e:
            logger.error(f"Permission denied creating backup: {e}")
            return Fail(f"Permission denied: {e}")
        except OSError as e:
            logger.error(f"OS error creating backup: {e}")
            return Fail(f"Failed to create backup: {e}")

    async def list_backups(self) -> Result[List[BackupMetadata]]:
        """List all available backups, sorted newest first.

        Returns:
            Result containing list of BackupMetadata, ordered by created_at descending
        """
        try:
            if not self._backup_dir.exists():
                return Ok([])

            backups: List[BackupMetadata] = []

            for backup_file in self._backup_dir.glob("treeline-*.duckdb"):
                created_at = self._parse_backup_time(backup_file.name)
                if created_at is None:
                    # Skip files that don't match our naming convention
                    continue

                stats = backup_file.stat()
                backups.append(
                    BackupMetadata(
                        name=backup_file.name,
                        created_at=created_at,
                        size_bytes=stats.st_size,
                    )
                )

            # Sort by created_at descending (newest first)
            backups.sort(key=lambda b: b.created_at, reverse=True)

            return Ok(backups)

        except OSError as e:
            logger.error(f"Error listing backups: {e}")
            return Fail(f"Failed to list backups: {e}")

    async def restore_backup(
        self,
        backup_name: str,
        target_path: Path,
    ) -> Result[None]:
        """Restore a backup to the target path.

        Args:
            backup_name: Name of the backup to restore
            target_path: Path where restored file should be written

        Returns:
            Result indicating success/failure
        """
        try:
            backup_path = self._backup_dir / backup_name

            if not backup_path.exists():
                return Fail(f"Backup not found: {backup_name}")

            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy backup to target (overwrites existing)
            shutil.copy2(backup_path, target_path)

            logger.info(f"Restored backup {backup_name} to {target_path}")
            return Ok(None)

        except PermissionError as e:
            logger.error(f"Permission denied restoring backup: {e}")
            return Fail(f"Permission denied: {e}")
        except OSError as e:
            logger.error(f"OS error restoring backup: {e}")
            return Fail(f"Failed to restore backup: {e}")

    async def delete_backup(self, backup_name: str) -> Result[None]:
        """Delete a specific backup.

        Args:
            backup_name: Name of the backup to delete

        Returns:
            Result indicating success/failure
        """
        try:
            backup_path = self._backup_dir / backup_name

            if not backup_path.exists():
                return Fail(f"Backup not found: {backup_name}")

            backup_path.unlink()

            logger.info(f"Deleted backup: {backup_name}")
            return Ok(None)

        except PermissionError as e:
            logger.error(f"Permission denied deleting backup: {e}")
            return Fail(f"Permission denied: {e}")
        except OSError as e:
            logger.error(f"OS error deleting backup: {e}")
            return Fail(f"Failed to delete backup: {e}")

    async def delete_all_backups(self) -> Result[int]:
        """Delete all backups.

        Returns:
            Result containing count of deleted backups
        """
        try:
            if not self._backup_dir.exists():
                return Ok(0)

            deleted_count = 0
            for backup_file in self._backup_dir.glob("treeline-*.duckdb"):
                try:
                    backup_file.unlink()
                    deleted_count += 1
                except OSError as e:
                    logger.warning(f"Failed to delete {backup_file.name}: {e}")

            logger.info(f"Deleted {deleted_count} backups")
            return Ok(deleted_count)

        except OSError as e:
            logger.error(f"Error deleting backups: {e}")
            return Fail(f"Failed to delete backups: {e}")

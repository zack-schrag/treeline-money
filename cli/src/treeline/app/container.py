"""Dependency injection container for the application."""

from pathlib import Path
from typing import Any, Dict

from treeline.abstractions import (
    BackupStorageProvider,
    DataAggregationProvider,
    IntegrationProvider,
    Repository,
)
from treeline.app.account_service import AccountService
from treeline.app.backfill_service import BackfillService
from treeline.app.backup_service import BackupService
from treeline.app.db_service import DbService
from treeline.app.import_service import ImportService
from treeline.app.integration_service import IntegrationService
from treeline.app.plugin_service import PluginService
from treeline.app.status_service import StatusService
from treeline.app.sync_service import SyncService
from treeline.app.tagging_service import TaggingService
from treeline.infra.csv import CSVProvider
from treeline.infra.demo import DemoDataProvider
from treeline.infra.duckdb import DuckDBRepository
from treeline.infra.local_backup import LocalBackupStorage
from treeline.infra.simplefin import SimpleFINProvider

DEFAULT_MAX_BACKUPS = 7


class Container:
    """Dependency injection container for the application."""

    def __init__(self, treeline_dir: str, db_filename: str = "treeline.duckdb"):
        """Initialize container.

        Args:
            treeline_dir: Directory where treeline data is stored (e.g., ~/.treeline)
            db_filename: Name of the database file (default: treeline.duckdb, demo mode uses demo.duckdb)
        """
        self.treeline_dir = treeline_dir
        self.db_file_path = str(Path(treeline_dir) / db_filename)
        self.db_filename = db_filename
        self._instances: Dict[str, Any] = {}

    @property
    def is_demo_mode(self) -> bool:
        """Check if this container is configured for demo mode."""
        return self.db_filename == "demo.duckdb"

    def repository(self) -> Repository:
        """Get the repository instance."""
        if "repository" not in self._instances:
            self._instances["repository"] = DuckDBRepository(self.db_file_path)
        return self._instances["repository"]

    def provider_registry(self) -> Dict[str, DataAggregationProvider]:
        """Get the provider registry.

        Providers are registered by name. The 'demo' provider returns mock data
        for testing. CSV import always uses the real CSVProvider.
        """
        if "provider_registry" not in self._instances:
            self._instances["provider_registry"] = {
                "simplefin": SimpleFINProvider(),
                "demo": DemoDataProvider(),
                "csv": CSVProvider(),
            }
        return self._instances["provider_registry"]

    def sync_service(self) -> SyncService:
        """Get the sync service instance."""
        if "sync_service" not in self._instances:
            self._instances["sync_service"] = SyncService(
                self.provider_registry(),
                self.repository(),
                self.account_service(),
                self.integration_service(),
            )
        return self._instances["sync_service"]

    def integration_service(self) -> IntegrationService:
        """Get the integration service instance."""
        if "integration_service" not in self._instances:
            self._instances["integration_service"] = IntegrationService(self.repository())
        return self._instances["integration_service"]

    def get_integration_provider(self, integration_name: str) -> IntegrationProvider:
        """Get an integration provider by name."""
        provider = self.provider_registry().get(integration_name)
        if not provider:
            raise ValueError(f"Unknown integration: {integration_name}")

        if not isinstance(provider, IntegrationProvider):
            raise ValueError(
                f"Provider {integration_name} does not support integration setup"
            )

        return provider

    def account_service(self) -> AccountService:
        """Get the account service instance."""
        if "account_service" not in self._instances:
            self._instances["account_service"] = AccountService(self.repository())
        return self._instances["account_service"]

    def status_service(self) -> StatusService:
        """Get the status service instance."""
        if "status_service" not in self._instances:
            self._instances["status_service"] = StatusService(self.repository())
        return self._instances["status_service"]

    def db_service(self) -> DbService:
        """Get the DB service instance."""
        if "db_service" not in self._instances:
            self._instances["db_service"] = DbService(self.repository())
        return self._instances["db_service"]

    def tagging_service(self) -> TaggingService:
        """Get the tagging service instance."""
        if "tagging_service" not in self._instances:
            self._instances["tagging_service"] = TaggingService(self.repository())
        return self._instances["tagging_service"]

    def import_service(self) -> ImportService:
        """Get the import service instance."""
        if "import_service" not in self._instances:
            self._instances["import_service"] = ImportService(
                self.repository(), self.provider_registry()
            )
        return self._instances["import_service"]

    def backfill_service(self) -> BackfillService:
        """Get the backfill service instance."""
        if "backfill_service" not in self._instances:
            self._instances["backfill_service"] = BackfillService(self.repository())
        return self._instances["backfill_service"]

    def plugin_service(self) -> PluginService:
        """Get the plugin service instance."""
        if "plugin_service" not in self._instances:
            plugins_dir = Path(self.treeline_dir) / "plugins"
            self._instances["plugin_service"] = PluginService(plugins_dir)
        return self._instances["plugin_service"]

    def backup_storage_provider(self) -> BackupStorageProvider:
        """Get the backup storage provider instance.

        Uses factory pattern: demo mode gets a separate backup directory.
        """
        if "backup_storage_provider" not in self._instances:
            # Demo mode uses separate backup directory
            if self.is_demo_mode:
                backup_dir = Path(self.treeline_dir) / "backups-demo"
            else:
                backup_dir = Path(self.treeline_dir) / "backups"

            self._instances["backup_storage_provider"] = LocalBackupStorage(backup_dir)
        return self._instances["backup_storage_provider"]

    def backup_service(self, max_backups: int = DEFAULT_MAX_BACKUPS) -> BackupService:
        """Get the backup service instance.

        Args:
            max_backups: Maximum number of backups to retain (default: 7)
        """
        # Don't cache - max_backups can vary per call
        return BackupService(
            storage_provider=self.backup_storage_provider(),
            db_path=Path(self.db_file_path),
            max_backups=max_backups,
        )

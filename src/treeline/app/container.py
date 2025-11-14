"""Dependency injection container for the application."""

import os
from pathlib import Path
from typing import Any, Dict

from treeline.abstractions import (
    DataAggregationProvider,
    IntegrationProvider,
    Repository,
    TagSuggester,
)
from treeline.app.service import (
    AccountService,
    DbService,
    ImportService,
    IntegrationService,
    StatusService,
    SyncService,
    TaggingService,
)
from treeline.app.backfill_service import BackfillService
from treeline.infra.tag_suggesters import (
    FrequencyTagSuggester,
    CombinedTagSuggester,
)
from treeline.infra.csv_provider import CSVProvider
from treeline.infra.duckdb import DuckDBRepository
from treeline.infra.simplefin import SimpleFINProvider
from treeline.infra.demo_provider import DemoDataProvider


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
        self._instances: Dict[str, Any] = {}

    def repository(self) -> Repository:
        """Get the repository instance."""
        if "repository" not in self._instances:
            self._instances["repository"] = DuckDBRepository(self.db_file_path)
        return self._instances["repository"]

    def provider_registry(self) -> Dict[str, DataAggregationProvider]:
        """Get the provider registry.

        In demo mode (TREELINE_DEMO_MODE=true), all providers return mock data.
        """
        if "provider_registry" not in self._instances:
            demo_mode = os.getenv("TREELINE_DEMO_MODE", "").lower() in (
                "true",
                "1",
                "yes",
            )
            demo_provider = DemoDataProvider()

            self._instances["provider_registry"] = {
                "simplefin": demo_provider if demo_mode else SimpleFINProvider(),
                "csv": demo_provider if demo_mode else CSVProvider(),
            }
        return self._instances["provider_registry"]

    def sync_service(self) -> SyncService:
        """Get the sync service instance."""
        if "sync_service" not in self._instances:
            self._instances["sync_service"] = SyncService(
                self.provider_registry(), self.repository()
            )
        return self._instances["sync_service"]

    def integration_service(self, integration_name: str) -> IntegrationService:
        """Get an integration service for a specific provider."""
        provider = self.provider_registry().get(integration_name)
        if not provider:
            raise ValueError(f"Unknown integration: {integration_name}")

        # Integration services are not cached since they're provider-specific
        if not isinstance(provider, IntegrationProvider):
            raise ValueError(
                f"Provider {integration_name} does not support integration setup"
            )

        return IntegrationService(provider, self.repository())

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

    def _default_tag_suggester(self) -> TagSuggester:
        """
        Get the default tag suggester (combined frequency + common tags).

        Returns:
            TagSuggester instance
        """
        frequency_suggester = FrequencyTagSuggester(self.repository())
        return CombinedTagSuggester(frequency_suggester)

    def tagging_service(
        self, tag_suggester: TagSuggester | None = None
    ) -> TaggingService:
        """
        Get a tagging service instance with provided or default tag suggester.

        Args:
            tag_suggester: Optional tag suggestion algorithm to use. If None, uses default.

        Returns:
            TaggingService instance
        """
        if tag_suggester is None:
            tag_suggester = self._default_tag_suggester()

        return TaggingService(self.repository(), tag_suggester)

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

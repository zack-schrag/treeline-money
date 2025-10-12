"""Dependency injection container for the application."""

import os
from typing import Any, Dict

from supabase import create_client

from treeline.abstractions import (
    AIProvider,
    AuthProvider,
    ChartStorage,
    CredentialStore,
    DataAggregationProvider,
    IntegrationProvider,
    QueryStorage,
    Repository,
    TagSuggester,
)
from treeline.app.service import AccountService, AgentService, AuthService, ConfigService, DbService, ImportService, IntegrationService, StatusService, SyncService, TaggingService
from treeline.infra.anthropic import AnthropicProvider
from treeline.infra.csv_provider import CSVProvider
from treeline.infra.duckdb import DuckDBRepository
from treeline.infra.file_storage import FileChartStorage, FileQueryStorage
from treeline.infra.keyring_store import KeyringCredentialStore
from treeline.infra.mcp import ToolRegistry
from treeline.infra.simplefin import SimpleFINProvider
from treeline.infra.supabase import SupabaseAuthProvider


class Container:
    """Dependency injection container for the application."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._instances: Dict[str, Any] = {}

    def credential_store(self) -> CredentialStore:
        """Get the credential store instance."""
        if "credential_store" not in self._instances:
            self._instances["credential_store"] = KeyringCredentialStore()
        return self._instances["credential_store"]

    def config_service(self) -> ConfigService:
        """Get the config service instance."""
        if "config_service" not in self._instances:
            self._instances["config_service"] = ConfigService(self.credential_store())
        return self._instances["config_service"]

    def repository(self) -> Repository:
        """Get the repository instance."""
        if "repository" not in self._instances:
            self._instances["repository"] = DuckDBRepository(self.db_path)
        return self._instances["repository"]

    def auth_provider(self) -> AuthProvider:
        """Get the auth provider instance."""
        if "auth_provider" not in self._instances:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            if not supabase_url or not supabase_key:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
            client = create_client(supabase_url, supabase_key)
            self._instances["auth_provider"] = SupabaseAuthProvider(client)
        return self._instances["auth_provider"]

    def auth_service(self) -> AuthService:
        """Get the auth service instance."""
        if "auth_service" not in self._instances:
            self._instances["auth_service"] = AuthService(self.auth_provider())
        return self._instances["auth_service"]

    def provider_registry(self) -> Dict[str, DataAggregationProvider]:
        """Get the provider registry."""
        if "provider_registry" not in self._instances:
            self._instances["provider_registry"] = {
                "simplefin": SimpleFINProvider(),
                "csv": CSVProvider(),
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
            raise ValueError(f"Provider {integration_name} does not support integration setup")

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

    def tool_registry(self) -> ToolRegistry:
        """Get the tool registry instance."""
        if "tool_registry" not in self._instances:
            self._instances["tool_registry"] = ToolRegistry(self.repository())
        return self._instances["tool_registry"]

    def ai_provider(self) -> AIProvider:
        """Get the AI provider instance."""
        if "ai_provider" not in self._instances:
            # AnthropicProvider depends on ToolRegistry
            self._instances["ai_provider"] = AnthropicProvider(self.tool_registry())
        return self._instances["ai_provider"]

    def agent_service(self) -> AgentService:
        """Get the agent service instance."""
        if "agent_service" not in self._instances:
            self._instances["agent_service"] = AgentService(self.ai_provider())
        return self._instances["agent_service"]

    def _default_tag_suggester(self) -> TagSuggester:
        """
        Get the default tag suggester (combined frequency + common tags).

        Returns:
            TagSuggester instance
        """
        from treeline.infra.tag_suggesters import FrequencyTagSuggester, CommonTagSuggester, CombinedTagSuggester

        frequency_suggester = FrequencyTagSuggester(self.repository())
        common_suggester = CommonTagSuggester()
        return CombinedTagSuggester(frequency_suggester, common_suggester)

    def tagging_service(self, tag_suggester: TagSuggester | None = None) -> TaggingService:
        """
        Get a tagging service instance with provided or default tag suggester.

        Args:
            tag_suggester: Optional tag suggestion algorithm to use. If None, uses default.

        Returns:
            TaggingService instance
        """
        from treeline.app.service import TaggingService

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

    def chart_storage(self) -> ChartStorage:
        """Get the chart storage instance."""
        if "chart_storage" not in self._instances:
            from pathlib import Path
            charts_dir = Path.home() / ".treeline" / "charts"
            self._instances["chart_storage"] = FileChartStorage(charts_dir)
        return self._instances["chart_storage"]

    def query_storage(self) -> QueryStorage:
        """Get the query storage instance."""
        if "query_storage" not in self._instances:
            from pathlib import Path
            queries_dir = Path.home() / ".treeline" / "queries"
            self._instances["query_storage"] = FileQueryStorage(queries_dir)
        return self._instances["query_storage"]

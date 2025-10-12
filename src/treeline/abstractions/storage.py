"""Storage abstractions for charts and queries."""

from abc import ABC, abstractmethod
from typing import Optional

from treeline.domain import ChartConfig


class ChartStorage(ABC):
    """Abstraction for storing and retrieving chart configurations."""

    @abstractmethod
    def save(self, name: str, config: ChartConfig) -> bool:
        """Save a chart configuration.

        Args:
            name: The name to save the chart as
            config: The chart configuration

        Returns:
            True if saved successfully, False otherwise
        """
        pass

    @abstractmethod
    def load(self, name: str) -> Optional[ChartConfig]:
        """Load a chart configuration.

        Args:
            name: The name of the chart

        Returns:
            ChartConfig if found and valid, None otherwise
        """
        pass

    @abstractmethod
    def list(self) -> list[str]:
        """List all saved chart configurations.

        Returns:
            List of chart names
        """
        pass

    @abstractmethod
    def delete(self, name: str) -> bool:
        """Delete a chart configuration.

        Args:
            name: The name of the chart

        Returns:
            True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    def exists(self, name: str) -> bool:
        """Check if a chart exists.

        Args:
            name: The name of the chart

        Returns:
            True if exists, False otherwise
        """
        pass


class QueryStorage(ABC):
    """Abstraction for storing and retrieving SQL queries."""

    @abstractmethod
    def save(self, name: str, sql: str) -> bool:
        """Save a query.

        Args:
            name: The name for the query
            sql: The SQL query content

        Returns:
            True if saved successfully, False otherwise
        """
        pass

    @abstractmethod
    def load(self, name: str) -> Optional[str]:
        """Load a query.

        Args:
            name: The name of the query

        Returns:
            The SQL query content, or None if not found
        """
        pass

    @abstractmethod
    def list(self) -> list[str]:
        """List all saved queries.

        Returns:
            List of query names
        """
        pass

    @abstractmethod
    def delete(self, name: str) -> bool:
        """Delete a saved query.

        Args:
            name: The name of the query

        Returns:
            True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    def exists(self, name: str) -> bool:
        """Check if a query exists.

        Args:
            name: The name of the query

        Returns:
            True if exists, False otherwise
        """
        pass

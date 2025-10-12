"""File-based storage implementations for charts and queries."""

import re
from pathlib import Path
from typing import Optional

from treeline.abstractions import ChartStorage, QueryStorage
from treeline.commands.chart_config import parse_chart_config, serialize_chart_config
from treeline.domain import ChartConfig


class FileChartStorage(ChartStorage):
    """File-based implementation of ChartStorage."""

    def __init__(self, charts_dir: Path):
        """Initialize the file chart storage.

        Args:
            charts_dir: Directory where .tl chart files are stored
        """
        self.charts_dir = charts_dir

    def save(self, name: str, config: ChartConfig) -> bool:
        """Save a chart configuration."""
        try:
            # Create directory if it doesn't exist
            self.charts_dir.mkdir(parents=True, exist_ok=True)

            # Serialize and write
            content = serialize_chart_config(config)
            chart_file = self.charts_dir / f"{name}.tl"
            chart_file.write_text(content)

            return True
        except Exception:
            return False

    def load(self, name: str) -> Optional[ChartConfig]:
        """Load a chart configuration."""
        chart_file = self.charts_dir / f"{name}.tl"

        if not chart_file.exists():
            return None

        try:
            content = chart_file.read_text()
            return parse_chart_config(content)
        except Exception:
            return None

    def list(self) -> list[str]:
        """List all saved chart configurations."""
        if not self.charts_dir.exists():
            return []

        try:
            # Get all .tl files and remove the extension
            return sorted([f.stem for f in self.charts_dir.glob("*.tl")])
        except Exception:
            return []

    def delete(self, name: str) -> bool:
        """Delete a chart configuration."""
        chart_file = self.charts_dir / f"{name}.tl"

        if not chart_file.exists():
            return False

        try:
            chart_file.unlink()
            return True
        except Exception:
            return False

    def exists(self, name: str) -> bool:
        """Check if a chart exists."""
        chart_file = self.charts_dir / f"{name}.tl"
        return chart_file.exists()


class FileQueryStorage(QueryStorage):
    """File-based implementation of QueryStorage."""

    def __init__(self, queries_dir: Path):
        """Initialize the file query storage.

        Args:
            queries_dir: Directory where .sql query files are stored
        """
        self.queries_dir = queries_dir

    def save(self, name: str, sql: str) -> bool:
        """Save a query."""
        try:
            # Create directory if it doesn't exist
            self.queries_dir.mkdir(parents=True, exist_ok=True)

            # Write the query to file
            query_file = self.queries_dir / f"{name}.sql"
            query_file.write_text(sql)

            return True
        except Exception:
            return False

    def load(self, name: str) -> Optional[str]:
        """Load a query."""
        query_file = self.queries_dir / f"{name}.sql"

        if not query_file.exists():
            return None

        try:
            return query_file.read_text()
        except Exception:
            return None

    def list(self) -> list[str]:
        """List all saved queries."""
        if not self.queries_dir.exists():
            return []

        try:
            # Get all .sql files and remove the extension
            return sorted([f.stem for f in self.queries_dir.glob("*.sql")])
        except Exception:
            return []

    def delete(self, name: str) -> bool:
        """Delete a saved query."""
        query_file = self.queries_dir / f"{name}.sql"

        if not query_file.exists():
            return False

        try:
            query_file.unlink()
            return True
        except Exception:
            return False

    def exists(self, name: str) -> bool:
        """Check if a query exists."""
        query_file = self.queries_dir / f"{name}.sql"
        return query_file.exists()

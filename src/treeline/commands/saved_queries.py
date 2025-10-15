"""Saved queries functionality."""

import re

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from treeline.theme import get_theme

console = Console()
theme = get_theme()


def get_container():
    """Import get_container to avoid circular import."""
    from treeline.cli import get_container as _get_container
    return _get_container()


def validate_query_name(name: str) -> bool:
    """Validate that a query name contains only alphanumeric characters and underscores.

    Args:
        name: The query name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False
    # Only allow alphanumeric and underscores
    return bool(re.match(r'^[a-zA-Z0-9_]+$', name))


# Convenience wrappers for backward compatibility
def save_query(name: str, sql: str) -> bool:
    """Save a query using the storage abstraction."""
    container = get_container()
    return container.query_storage().save(name, sql)


def load_query(name: str) -> str | None:
    """Load a query using the storage abstraction."""
    container = get_container()
    return container.query_storage().load(name)


def list_queries() -> list[str]:
    """List all saved queries using the storage abstraction."""
    container = get_container()
    return container.query_storage().list()


def delete_query(name: str) -> bool:
    """Delete a saved query using the storage abstraction."""
    container = get_container()
    return container.query_storage().delete(name)


def query_exists(name: str) -> bool:
    """Check if a query exists using the storage abstraction."""
    container = get_container()
    return container.query_storage().exists(name)



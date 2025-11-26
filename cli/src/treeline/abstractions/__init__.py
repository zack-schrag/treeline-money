"""Abstractions for dependency inversion (hexagonal architecture)."""

from treeline.abstractions.data import DataAggregationProvider, IntegrationProvider
from treeline.abstractions.db import Repository
from treeline.abstractions.tagging import TagSuggester

__all__ = [
    "DataAggregationProvider",
    "IntegrationProvider",
    "Repository",
    "TagSuggester",
]

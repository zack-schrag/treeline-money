"""Abstractions for dependency inversion (hexagonal architecture)."""

from treeline.abstractions.data import DataAggregationProvider, IntegrationProvider
from treeline.abstractions.db import Repository

__all__ = [
    "DataAggregationProvider",
    "IntegrationProvider",
    "Repository",
]

"""Tag suggestion abstraction."""

from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from treeline.domain import Result, Transaction


class TagSuggester(ABC):
    """Abstract interface for tag suggestion algorithms."""

    @abstractmethod
    async def suggest_tags(
        self, transaction: Transaction, limit: int = 5
    ) -> Result[List[str]]:
        """
        Suggest tags for a transaction.

        Args:
            transaction: Transaction to suggest tags for
            limit: Maximum number of tags to suggest

        Returns:
            Result containing list of suggested tag strings
        """
        pass

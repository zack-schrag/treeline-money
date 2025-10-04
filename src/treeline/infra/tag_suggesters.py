"""Tag suggestion implementations."""

from typing import List
from uuid import UUID

from treeline.abstractions import Repository, TagSuggester
from treeline.domain import Transaction, Result


class FrequencyTagSuggester(TagSuggester):
    """Suggests tags based on frequency of use across all transactions."""

    def __init__(self, repository: Repository):
        """
        Initialize frequency-based tag suggester.

        Args:
            repository: Repository for accessing tag statistics
        """
        self.repository = repository

    async def suggest_tags(
        self, user_id: UUID, transaction: Transaction, limit: int = 5
    ) -> Result[List[str]]:
        """
        Suggest most frequently used tags.

        Algorithm:
        1. Get tag usage statistics from repository
        2. Sort by frequency descending
        3. Filter out tags already on this transaction
        4. Return top N tags

        Args:
            user_id: User context
            transaction: Transaction to suggest tags for
            limit: Maximum number of tags to suggest

        Returns:
            Result containing list of suggested tag strings
        """
        # Get tag statistics
        stats_result = await self.repository.get_tag_statistics(user_id)

        if not stats_result.success:
            return stats_result

        tag_stats = stats_result.data

        # Get current transaction tags
        current_tags = set(transaction.tags or [])

        # Sort tags by frequency (descending) and filter out existing tags
        sorted_tags = sorted(
            tag_stats.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Filter and limit
        suggestions = [
            tag for tag, count in sorted_tags
            if tag not in current_tags
        ][:limit]

        return Result(success=True, data=suggestions)

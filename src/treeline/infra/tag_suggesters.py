"""Tag suggestion implementations."""

from typing import List
from uuid import UUID

from treeline.abstractions import Repository, TagSuggester
from treeline.domain import Transaction, Result, Ok


class CommonTagSuggester(TagSuggester):
    """Suggests commonly used personal finance tags."""

    COMMON_TAGS = [
        "groceries",
        "eating out",
        "subscriptions",
        "utilities",
        "transportation",
        "entertainment",
        "shopping",
        "healthcare",
        "housing",
        "income",
    ]

    async def suggest_tags(
        self, user_id: UUID, transaction: Transaction, limit: int = 5
    ) -> Result[List[str]]:
        """
        Suggest common personal finance tags.

        Returns common tags that are not already applied to the transaction.

        Args:
            user_id: User context (unused for this suggester)
            transaction: Transaction to suggest tags for
            limit: Maximum number of tags to suggest

        Returns:
            Result containing list of suggested tag strings
        """
        # Get current transaction tags
        current_tags = set(transaction.tags or [])

        # Filter out tags already applied and return top N
        suggestions = [
            tag for tag in self.COMMON_TAGS
            if tag not in current_tags
        ][:limit]

        return Ok(suggestions)


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


class CombinedTagSuggester(TagSuggester):
    """Combines multiple tag suggestion strategies."""

    def __init__(self, *suggesters: TagSuggester):
        """
        Initialize with multiple tag suggesters.

        Args:
            *suggesters: TagSuggester instances to combine
        """
        self.suggesters = suggesters

    async def suggest_tags(
        self, user_id: UUID, transaction: Transaction, limit: int = 5
    ) -> Result[List[str]]:
        """
        Combine suggestions from multiple suggesters.

        Merges results from all suggesters, removes duplicates while
        preserving order, and returns top N suggestions.

        Args:
            user_id: User context
            transaction: Transaction to suggest tags for
            limit: Maximum number of tags to suggest

        Returns:
            Result containing list of suggested tag strings
        """
        all_suggestions = []
        seen = set()

        for suggester in self.suggesters:
            result = await suggester.suggest_tags(user_id, transaction, limit=limit)
            if result.success:
                for tag in result.data:
                    if tag not in seen:
                        all_suggestions.append(tag)
                        seen.add(tag)

        return Ok(all_suggestions[:limit])

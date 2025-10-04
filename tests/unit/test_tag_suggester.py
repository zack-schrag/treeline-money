"""Unit tests for TagSuggester implementations."""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import UUID
from datetime import datetime, timezone

from treeline.domain import Transaction, Ok
from treeline.infra.tag_suggesters import FrequencyTagSuggester, CommonTagSuggester, CombinedTagSuggester


class TestFrequencyTagSuggester:
    """Test frequency-based tag suggestion."""

    @pytest.mark.asyncio
    async def test_suggests_most_frequent_tags(self):
        """Should suggest most frequently used tags across all transactions."""
        # Mock repository
        repository = Mock()
        repository.get_tag_statistics = AsyncMock(return_value=Ok({
            "groceries": 50,
            "dining": 30,
            "transport": 20,
            "bills": 10,
            "entertainment": 5,
        }))

        suggester = FrequencyTagSuggester(repository)

        # Create a transaction (tags don't matter for frequency suggester)
        transaction = Transaction(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            account_id=UUID("00000000-0000-0000-0000-000000000002"),
            external_ids={},
            amount=-50.0,
            description="Whole Foods",
            transaction_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            posted_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            tags=(),
            created_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
        )

        user_id = UUID("12345678-1234-5678-1234-567812345678")

        # Get suggestions
        result = await suggester.suggest_tags(user_id, transaction, limit=5)

        assert result.success
        assert len(result.data) == 5
        # Should be sorted by frequency descending
        assert result.data == ["groceries", "dining", "transport", "bills", "entertainment"]

    @pytest.mark.asyncio
    async def test_excludes_already_applied_tags(self):
        """Should not suggest tags already on the transaction."""
        repository = Mock()
        repository.get_tag_statistics = AsyncMock(return_value=Ok({
            "groceries": 50,
            "dining": 30,
            "transport": 20,
            "bills": 10,
        }))

        suggester = FrequencyTagSuggester(repository)

        # Transaction already has "groceries" tag
        transaction = Transaction(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            account_id=UUID("00000000-0000-0000-0000-000000000002"),
            external_ids={},
            amount=-50.0,
            description="Whole Foods",
            transaction_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            posted_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            tags=("groceries",),
            created_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
        )

        user_id = UUID("12345678-1234-5678-1234-567812345678")

        result = await suggester.suggest_tags(user_id, transaction, limit=5)

        assert result.success
        # Should not include "groceries"
        assert "groceries" not in result.data
        assert result.data == ["dining", "transport", "bills"]

    @pytest.mark.asyncio
    async def test_respects_limit(self):
        """Should return at most limit number of tags."""
        repository = Mock()
        repository.get_tag_statistics = AsyncMock(return_value=Ok({
            "groceries": 50,
            "dining": 30,
            "transport": 20,
            "bills": 10,
            "entertainment": 5,
        }))

        suggester = FrequencyTagSuggester(repository)

        transaction = Transaction(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            account_id=UUID("00000000-0000-0000-0000-000000000002"),
            external_ids={},
            amount=-50.0,
            description="Whole Foods",
            transaction_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            posted_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            tags=(),
            created_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
        )

        user_id = UUID("12345678-1234-5678-1234-567812345678")

        result = await suggester.suggest_tags(user_id, transaction, limit=3)

        assert result.success
        assert len(result.data) == 3
        assert result.data == ["groceries", "dining", "transport"]

    @pytest.mark.asyncio
    async def test_handles_no_tags_in_database(self):
        """Should return empty list when no tags exist."""
        repository = Mock()
        repository.get_tag_statistics = AsyncMock(return_value=Ok({}))

        suggester = FrequencyTagSuggester(repository)

        transaction = Transaction(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            account_id=UUID("00000000-0000-0000-0000-000000000002"),
            external_ids={},
            amount=-50.0,
            description="Whole Foods",
            transaction_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            posted_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            tags=(),
            created_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
        )

        user_id = UUID("12345678-1234-5678-1234-567812345678")

        result = await suggester.suggest_tags(user_id, transaction, limit=5)

        assert result.success
        assert result.data == []


class TestCommonTagSuggester:
    """Test common tag suggestion."""

    @pytest.mark.asyncio
    async def test_suggests_common_tags(self):
        """Should suggest common personal finance tags."""
        suggester = CommonTagSuggester()

        transaction = Transaction(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            account_id=UUID("00000000-0000-0000-0000-000000000002"),
            external_ids={},
            amount=-50.0,
            description="Some transaction",
            transaction_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            posted_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            tags=(),
            created_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
        )

        user_id = UUID("12345678-1234-5678-1234-567812345678")

        result = await suggester.suggest_tags(user_id, transaction, limit=5)

        assert result.success
        assert len(result.data) == 5
        # Should include some common tags
        assert "groceries" in result.data
        assert "eating out" in result.data

    @pytest.mark.asyncio
    async def test_excludes_already_applied_tags(self):
        """Should not suggest tags already on the transaction."""
        suggester = CommonTagSuggester()

        transaction = Transaction(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            account_id=UUID("00000000-0000-0000-0000-000000000002"),
            external_ids={},
            amount=-50.0,
            description="Some transaction",
            transaction_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            posted_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            tags=("groceries", "eating out"),
            created_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
        )

        user_id = UUID("12345678-1234-5678-1234-567812345678")

        result = await suggester.suggest_tags(user_id, transaction, limit=5)

        assert result.success
        assert "groceries" not in result.data
        assert "eating out" not in result.data


class TestCombinedTagSuggester:
    """Test combined tag suggestion."""

    @pytest.mark.asyncio
    async def test_combines_multiple_suggesters(self):
        """Should combine suggestions from multiple suggesters."""
        # Mock frequency suggester
        frequency_suggester = Mock()
        frequency_suggester.suggest_tags = AsyncMock(return_value=Ok(["utilities", "transport"]))

        # Common suggester (real)
        common_suggester = CommonTagSuggester()

        combined = CombinedTagSuggester(frequency_suggester, common_suggester)

        transaction = Transaction(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            account_id=UUID("00000000-0000-0000-0000-000000000002"),
            external_ids={},
            amount=-50.0,
            description="Some transaction",
            transaction_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            posted_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            tags=(),
            created_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
        )

        user_id = UUID("12345678-1234-5678-1234-567812345678")

        result = await combined.suggest_tags(user_id, transaction, limit=5)

        assert result.success
        # Should include suggestions from frequency suggester
        assert "utilities" in result.data
        assert "transport" in result.data

    @pytest.mark.asyncio
    async def test_removes_duplicates(self):
        """Should remove duplicate suggestions."""
        # Mock suggesters that return overlapping results
        suggester1 = Mock()
        suggester1.suggest_tags = AsyncMock(return_value=Ok(["groceries", "utilities"]))

        suggester2 = Mock()
        suggester2.suggest_tags = AsyncMock(return_value=Ok(["utilities", "transport"]))

        combined = CombinedTagSuggester(suggester1, suggester2)

        transaction = Transaction(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            account_id=UUID("00000000-0000-0000-0000-000000000002"),
            external_ids={},
            amount=-50.0,
            description="Some transaction",
            transaction_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            posted_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            tags=(),
            created_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 10, 1, tzinfo=timezone.utc),
        )

        user_id = UUID("12345678-1234-5678-1234-567812345678")

        result = await combined.suggest_tags(user_id, transaction, limit=5)

        assert result.success
        # Should have 3 unique tags, not 4
        assert len(result.data) == 3
        assert result.data == ["groceries", "utilities", "transport"]

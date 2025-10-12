"""AI provider abstraction."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from uuid import UUID

from treeline.domain import Result


class AIProvider(ABC):
    """Abstraction for AI/LLM providers that power conversational analysis."""

    @abstractmethod
    async def start_session(self, user_id: UUID, db_path: str) -> Result[None]:
        """
        Initialize a new conversation session.

        Args:
            user_id: User ID for this session
            db_path: Path to user's DuckDB database

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def send_message(self, message: str) -> Result[Dict[str, Any]]:
        """
        Send a message and get streaming response.

        Args:
            message: User's natural language query

        Returns:
            Result containing response data with streaming chunks
        """
        pass

    @abstractmethod
    async def end_session(self) -> Result[None]:
        """
        End the current conversation session and cleanup resources.

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    def has_active_session(self) -> bool:
        """
        Check if there is an active conversation session.

        Returns:
            True if session is active, False otherwise
        """
        pass

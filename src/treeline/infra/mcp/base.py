"""Base abstraction for MCP-style tools that can be used by AI providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from uuid import UUID

from treeline.domain import Result


class Tool(ABC):
    """
    Base class for all tools available to AI agents.

    Tools are discrete capabilities that AI providers can invoke.
    Each tool has a name, description, input schema, and execution logic.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """
        JSON Schema defining the tool's input parameters.

        Returns:
            Dict in format compatible with Anthropic/OpenAI tool schemas
        """
        pass

    @abstractmethod
    async def execute(self, user_id: UUID, tool_input: Dict[str, Any]) -> Result[str]:
        """
        Execute the tool with given inputs.

        Args:
            user_id: User context for this execution
            tool_input: Parameters matching the input_schema

        Returns:
            Result containing string output or error message
        """
        pass

    def to_anthropic_format(self) -> Dict[str, Any]:
        """Convert tool definition to Anthropic API format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema
        }

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert tool definition to OpenAI API format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema
            }
        }

"""Credential storage abstraction."""

from abc import ABC, abstractmethod


class CredentialStore(ABC):
    """Abstraction for storing and retrieving user credentials."""

    @abstractmethod
    def get_credential(self, key: str) -> str | None:
        """Get a credential by key. Returns None if not found."""
        pass

    @abstractmethod
    def set_credential(self, key: str, value: str) -> None:
        """Set a credential value."""
        pass

    @abstractmethod
    def delete_credential(self, key: str) -> None:
        """Delete a credential by key."""
        pass

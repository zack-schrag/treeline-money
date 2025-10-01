"""Keyring-based credential storage implementation."""

import keyring

from treeline.abstractions import CredentialStore


class KeyringCredentialStore(CredentialStore):
    """Credential store using the system keyring."""

    def __init__(self, service_name: str = "treeline"):
        self.service_name = service_name

    def get_credential(self, key: str) -> str | None:
        """Get a credential by key. Returns None if not found."""
        try:
            return keyring.get_password(self.service_name, key)
        except Exception:
            return None

    def set_credential(self, key: str, value: str) -> None:
        """Set a credential value."""
        keyring.set_password(self.service_name, key, value)

    def delete_credential(self, key: str) -> None:
        """Delete a credential by key."""
        try:
            keyring.delete_password(self.service_name, key)
        except Exception:
            # Ignore errors if credential doesn't exist
            pass

"""Unit tests for CLI basic functionality."""

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID

import pytest

from treeline.cli import (
    get_treeline_dir,
    is_authenticated,
    get_current_user_id,
    get_current_user_email,
)


def test_get_treeline_dir():
    """Test that get_treeline_dir returns current working directory / treeline."""
    result = get_treeline_dir()
    assert isinstance(result, Path)
    assert result.name == "treeline"
    assert result.parent == Path.cwd()


@patch("keyring.get_password")
def test_is_authenticated_when_user_id_exists(mock_get_password):
    """Test is_authenticated returns True when user_id is stored."""
    mock_get_password.return_value = "some-uuid"

    assert is_authenticated() is True
    mock_get_password.assert_called_once_with("treeline", "user_id")


@patch("keyring.get_password")
def test_is_authenticated_when_no_user_id(mock_get_password):
    """Test is_authenticated returns False when no user_id stored."""
    mock_get_password.return_value = None

    assert is_authenticated() is False


@patch("keyring.get_password")
def test_is_authenticated_when_keyring_error(mock_get_password):
    """Test is_authenticated returns False when keyring throws error."""
    mock_get_password.side_effect = Exception("Keyring error")

    assert is_authenticated() is False


@patch("keyring.get_password")
def test_get_current_user_id(mock_get_password):
    """Test get_current_user_id returns user_id from keyring."""
    expected_id = "123e4567-e89b-12d3-a456-426614174000"
    mock_get_password.return_value = expected_id

    result = get_current_user_id()

    assert result == expected_id
    mock_get_password.assert_called_once_with("treeline", "user_id")


@patch("keyring.get_password")
def test_get_current_user_email(mock_get_password):
    """Test get_current_user_email returns email from keyring."""
    expected_email = "test@example.com"
    mock_get_password.return_value = expected_email

    result = get_current_user_email()

    assert result == expected_email
    mock_get_password.assert_called_once_with("treeline", "user_email")

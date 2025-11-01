"""Unit tests for SupabaseAuthProvider."""

from unittest.mock import AsyncMock, Mock, MagicMock
from uuid import uuid4

import pytest

from treeline.domain import User, Ok, Fail
from treeline.infra.supabase import SupabaseAuthProvider


class MockSupabaseClient:
    """Mock Supabase client for testing."""

    def __init__(self):
        self.auth = Mock()
        self.auth.sign_in_with_password = Mock()
        self.auth.sign_up = Mock()
        self.auth.sign_out = Mock()
        self.auth.get_user = Mock()


@pytest.mark.asyncio
async def test_sign_in_with_password_success():
    """Test successful sign in with password."""
    mock_client = MockSupabaseClient()
    user_id = str(uuid4())
    email = "test@example.com"

    # Mock successful response
    mock_response = MagicMock()
    mock_response.user = MagicMock()
    mock_response.user.id = user_id
    mock_response.user.email = email
    mock_client.auth.sign_in_with_password.return_value = mock_response

    provider = SupabaseAuthProvider(mock_client)
    result = await provider.sign_in_with_password(email, "password123")

    assert result.success is True
    assert result.data.id == user_id
    assert result.data.email == email
    mock_client.auth.sign_in_with_password.assert_called_once_with(
        {"email": email, "password": "password123"}
    )


@pytest.mark.asyncio
async def test_sign_in_with_password_failure():
    """Test failed sign in with invalid credentials."""
    mock_client = MockSupabaseClient()

    # Mock error response
    mock_client.auth.sign_in_with_password.side_effect = Exception(
        "Invalid credentials"
    )

    provider = SupabaseAuthProvider(mock_client)
    result = await provider.sign_in_with_password("test@example.com", "wrongpassword")

    assert result.success is False
    assert "Invalid credentials" in result.error


@pytest.mark.asyncio
async def test_sign_up_with_password_success():
    """Test successful sign up with password."""
    mock_client = MockSupabaseClient()
    user_id = str(uuid4())
    email = "newuser@example.com"

    # Mock successful response
    mock_response = MagicMock()
    mock_response.user = MagicMock()
    mock_response.user.id = user_id
    mock_response.user.email = email
    mock_client.auth.sign_up.return_value = mock_response

    provider = SupabaseAuthProvider(mock_client)
    result = await provider.sign_up_with_password(email, "password123")

    assert result.success is True
    assert result.data.id == user_id
    assert result.data.email == email
    mock_client.auth.sign_up.assert_called_once_with(
        {"email": email, "password": "password123"}
    )


@pytest.mark.asyncio
async def test_sign_out_success():
    """Test successful sign out."""
    mock_client = MockSupabaseClient()
    mock_client.auth.sign_out.return_value = None

    provider = SupabaseAuthProvider(mock_client)
    result = await provider.sign_out()

    assert result.success is True
    mock_client.auth.sign_out.assert_called_once()


@pytest.mark.asyncio
async def test_get_current_user_success():
    """Test getting current user successfully."""
    mock_client = MockSupabaseClient()
    user_id = str(uuid4())
    email = "current@example.com"

    # Mock successful response
    mock_response = MagicMock()
    mock_response.user = MagicMock()
    mock_response.user.id = user_id
    mock_response.user.email = email
    mock_client.auth.get_user.return_value = mock_response

    provider = SupabaseAuthProvider(mock_client)
    result = await provider.get_current_user()

    assert result.success is True
    assert result.data.id == user_id
    assert result.data.email == email


@pytest.mark.asyncio
async def test_get_current_user_not_authenticated():
    """Test getting current user when not authenticated."""
    mock_client = MockSupabaseClient()
    mock_client.auth.get_user.return_value = MagicMock(user=None)

    provider = SupabaseAuthProvider(mock_client)
    result = await provider.get_current_user()

    assert result.success is True
    assert result.data is None


@pytest.mark.asyncio
async def test_validate_authorization_and_get_user_id_success():
    """Test successful authorization validation."""
    mock_client = MockSupabaseClient()
    user_id = str(uuid4())

    # Mock successful response
    mock_response = MagicMock()
    mock_response.user = MagicMock()
    mock_response.user.id = user_id
    mock_client.auth.get_user.return_value = mock_response

    provider = SupabaseAuthProvider(mock_client)
    result = await provider.validate_authorization_and_get_user_id("Bearer token123")

    assert result.success is True
    assert result.data == user_id
    # Verify token was passed without "Bearer " prefix
    mock_client.auth.get_user.assert_called_once_with("token123")


@pytest.mark.asyncio
async def test_validate_authorization_and_get_user_id_invalid_token():
    """Test authorization validation with invalid token."""
    mock_client = MockSupabaseClient()
    mock_client.auth.get_user.side_effect = Exception("Invalid token")

    provider = SupabaseAuthProvider(mock_client)
    result = await provider.validate_authorization_and_get_user_id(
        "Bearer invalid_token"
    )

    assert result.success is False
    assert "Invalid token" in result.error

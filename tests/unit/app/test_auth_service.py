"""Unit tests for AuthService."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from treeline.abstractions import AuthProvider
from treeline.app.service import AuthService
from treeline.domain import Ok, Fail, User


class MockAuthProvider(AuthProvider):
    """Mock AuthProvider for testing."""

    def __init__(self):
        self.sign_in_with_password = AsyncMock()
        self.sign_up_with_password = AsyncMock()
        self.sign_out = AsyncMock()
        self.get_current_user = AsyncMock()
        self.validate_authorization_and_get_user_id = AsyncMock()

    async def sign_in_with_password(self, email: str, password: str):
        pass

    async def sign_up_with_password(self, email: str, password: str):
        pass

    async def sign_out(self):
        pass

    async def get_current_user(self):
        pass

    def on_auth_state_change(self, callback):
        return lambda: None

    async def validate_authorization_and_get_user_id(self, authorization: str):
        pass


@pytest.mark.asyncio
async def test_sign_in_with_password_success():
    """Test successful sign in."""
    mock_provider = MockAuthProvider()
    user = User(id=str(uuid4()), email="test@example.com")
    mock_provider.sign_in_with_password.return_value = Ok(user)

    service = AuthService(mock_provider)
    result = await service.sign_in_with_password("test@example.com", "password123")

    assert result.success is True
    assert result.data.email == "test@example.com"
    mock_provider.sign_in_with_password.assert_called_once_with(
        "test@example.com", "password123"
    )


@pytest.mark.asyncio
async def test_sign_in_with_password_failure():
    """Test failed sign in."""
    mock_provider = MockAuthProvider()
    mock_provider.sign_in_with_password.return_value = Fail("Invalid credentials")

    service = AuthService(mock_provider)
    result = await service.sign_in_with_password("test@example.com", "wrong_password")

    assert result.success is False
    assert result.error == "Invalid credentials"


@pytest.mark.asyncio
async def test_sign_up_with_password_success():
    """Test successful sign up."""
    mock_provider = MockAuthProvider()
    user = User(id=str(uuid4()), email="newuser@example.com")
    mock_provider.sign_up_with_password.return_value = Ok(user)

    service = AuthService(mock_provider)
    result = await service.sign_up_with_password("newuser@example.com", "password123")

    assert result.success is True
    assert result.data.email == "newuser@example.com"
    mock_provider.sign_up_with_password.assert_called_once_with(
        "newuser@example.com", "password123"
    )


@pytest.mark.asyncio
async def test_validate_authorization_and_get_user_id_success():
    """Test successful authorization validation."""
    mock_provider = MockAuthProvider()
    user_id = str(uuid4())
    mock_provider.validate_authorization_and_get_user_id.return_value = Ok(user_id)

    service = AuthService(mock_provider)
    result = await service.validate_authorization_and_get_user_id("Bearer token123")

    assert result.success is True
    assert result.data == user_id
    mock_provider.validate_authorization_and_get_user_id.assert_called_once_with(
        "Bearer token123"
    )


@pytest.mark.asyncio
async def test_get_current_user():
    """Test getting current user."""
    mock_provider = MockAuthProvider()
    user = User(id=str(uuid4()), email="current@example.com")
    mock_provider.get_current_user.return_value = Ok(user)

    service = AuthService(mock_provider)
    result = await service.get_current_user()

    assert result.success is True
    assert result.data.email == "current@example.com"

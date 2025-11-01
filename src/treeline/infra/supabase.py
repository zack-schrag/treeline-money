"""Supabase infrastructure implementations."""

from typing import Any, Callable
from uuid import UUID

from treeline.abstractions import AuthProvider
from treeline.domain import Ok, Fail, Result, User


class SupabaseAuthProvider(AuthProvider):
    """Supabase implementation of AuthProvider."""

    def __init__(self, supabase_client: Any):
        """Initialize with a Supabase client.

        Args:
            supabase_client: A supabase.Client instance
        """
        self.supabase = supabase_client

    async def sign_in_with_password(self, email: str, password: str) -> Result[User]:
        """Sign in with email and password."""
        try:
            response = self.supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )

            if not response or not response.user:
                return Fail("No user returned from Supabase")

            user = User(id=response.user.id, email=response.user.email or email)
            return Ok(user)

        except Exception as e:
            return Fail(str(e))

    async def sign_up_with_password(self, email: str, password: str) -> Result[User]:
        """Sign up with email and password."""
        try:
            response = self.supabase.auth.sign_up(
                {"email": email, "password": password}
            )

            if not response or not response.user:
                return Fail("No user returned from Supabase")

            user = User(id=response.user.id, email=response.user.email or email)
            return Ok(user)

        except Exception as e:
            return Fail(str(e))

    async def sign_out(self) -> Result:
        """Sign out the current user."""
        try:
            self.supabase.auth.sign_out()
            return Ok()

        except Exception as e:
            return Fail(str(e))

    async def get_current_user(self) -> Result[User]:
        """Get the currently authenticated user."""
        try:
            response = self.supabase.auth.get_user()

            if not response or not response.user:
                return Ok(None)

            user = User(id=response.user.id, email=response.user.email or "")
            return Ok(user)

        except Exception as e:
            return Fail(str(e))

    def on_auth_state_change(
        self, callback: Callable[[User | None], None]
    ) -> Callable[[], None]:
        """Register a callback for auth state changes.

        Returns:
            A function to unsubscribe from auth state changes
        """

        def auth_callback(event: str, session: Any) -> None:
            if session and session.user:
                user = User(id=session.user.id, email=session.user.email or "")
                callback(user)
            else:
                callback(None)

        subscription = self.supabase.auth.on_auth_state_change(auth_callback)

        def unsubscribe() -> None:
            if hasattr(subscription, "unsubscribe"):
                subscription.unsubscribe()

        return unsubscribe

    async def validate_authorization_and_get_user_id(
        self, authorization: str
    ) -> Result[str]:
        """Validate authorization token and get user ID."""
        try:
            # Extract JWT token from Authorization header
            token = authorization.replace("Bearer ", "")

            response = self.supabase.auth.get_user(token)

            if not response or not response.user:
                return Fail("Invalid authorization token")

            return Ok(response.user.id)

        except Exception as e:
            return Fail(f"Authorization validation failed: {str(e)}")

"""Authentication provider abstraction."""

from abc import ABC, abstractmethod

from treeline.domain import Result, User


class AuthProvider(ABC):
    @abstractmethod
    async def sign_in_with_password(self, email: str, password: str) -> Result[User]:
        pass

    @abstractmethod
    async def sign_up_with_password(self, email: str, password: str) -> Result[User]:
        pass

    @abstractmethod
    async def sign_out(self) -> Result:
        pass

    @abstractmethod
    async def get_current_user(self) -> Result[User]:
        pass

    @abstractmethod
    async def validate_authorization_and_get_user_id(
        self, authorization: str
    ) -> Result[str]:
        pass

"""Data aggregation provider abstractions."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from treeline.domain import Account, Result


class DataAggregationProvider(ABC):
    @property
    @abstractmethod
    def can_get_accounts(self) -> bool:
        pass

    @property
    @abstractmethod
    def can_get_transactions(self) -> bool:
        pass

    @property
    @abstractmethod
    def can_get_balances(self) -> bool:
        pass

    @abstractmethod
    async def get_accounts(
        self,
        user_id: UUID,
        provider_account_ids: List[str] = [],
        provider_settings: Dict[str, Any] = {},
    ) -> Result[List[Account]]:
        pass

    @abstractmethod
    async def get_transactions(
        self,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
        provider_account_ids: List[str] = [],
        provider_settings: Dict[str, Any] = {},
    ) -> Result[List[Account]]:
        pass

    @abstractmethod
    async def get_balances(
        self,
        user_id: UUID,
        provider_account_ids: List[str] = [],
        provider_settings: Dict[str, Any] = {},
    ) -> Result[List[Account]]:
        pass


class IntegrationProvider(ABC):
    @abstractmethod
    async def create_integration(
        self, user_id: UUID, integration_name: str, integration_options: Dict[str, Any]
    ) -> Result[Any]:
        pass

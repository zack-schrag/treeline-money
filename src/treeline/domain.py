"""Domain model definitions."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Dict, Generic, Mapping, Type, TypeVar

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class User(BaseModel):
    """Represents an authenticated user."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, extra="forbid")

    id: str
    email: str


def _ensure_tzinfo(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "datetime must be timezone-aware"
        raise ValueError(msg)
    return value.astimezone(timezone.utc)


class Account(BaseModel):
    """Represents a financial account owned by the user."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, extra="forbid")

    id: UUID
    name: str = Field(min_length=1)
    nickname: str | None = None
    account_type: str | None = None
    currency: str = Field(default="USD")
    external_ids: Mapping[str, str] = Field(default_factory=dict)
    institution_name: str | None = None
    institution_url: str | None = None
    institution_domain: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        if not value:
            msg = "account name cannot be empty"
            raise ValueError(msg)
        return value

    @field_validator("external_ids", mode="before")
    @classmethod
    def _normalize_external_ids(cls, value: object) -> Mapping[str, str]:
        if value is None:
            return MappingProxyType({})
        if isinstance(value, Mapping):
            normalized = {str(key): str(val) for key, val in value.items()}
            return MappingProxyType(normalized)
        msg = "external_ids must be a mapping"
        raise TypeError(msg)

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            msg = "currency cannot be empty"
            raise ValueError(msg)
        return normalized

    @field_validator("created_at")
    @classmethod
    def _require_timezone(cls, value: datetime) -> datetime:
        return _ensure_tzinfo(value)

    @field_validator("updated_at")
    @classmethod
    def _require_timezone_updated(cls, value: datetime) -> datetime:
        return _ensure_tzinfo(value)


class Transaction(BaseModel):
    """A single transaction belonging to an account."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, extra="forbid")

    id: UUID
    account_id: UUID
    external_ids: Mapping[str, str] = Field(default_factory=dict)
    amount: Decimal
    description: str | None = None
    transaction_date: datetime
    posted_date: datetime
    tags: tuple[str, ...] = ()
    created_at: datetime
    updated_at: datetime

    @field_validator("amount")
    @classmethod
    def _validate_amount(cls, value: Decimal) -> Decimal:
        if value == 0:
            msg = "transaction amount cannot be zero"
            raise ValueError(msg)
        return value

    @field_validator("external_ids", mode="before")
    @classmethod
    def _normalize_external_ids(cls, value: object) -> Mapping[str, str]:
        if value is None:
            return MappingProxyType({})
        if isinstance(value, Mapping):
            normalized = {str(key): str(val) for key, val in value.items()}
            return MappingProxyType(normalized)
        msg = "external_ids must be a mapping"
        raise TypeError(msg)

    @field_validator("transaction_date")
    @classmethod
    def _validate_transaction_date(cls, value: datetime) -> datetime:
        return _ensure_tzinfo(value)

    @field_validator("posted_date")
    @classmethod
    def _validate_posted_date(cls, value: datetime) -> datetime:
        return _ensure_tzinfo(value)

    @field_validator("created_at")
    @classmethod
    def _validate_created_at(cls, value: datetime) -> datetime:
        return _ensure_tzinfo(value)

    @field_validator("updated_at")
    @classmethod
    def _validate_updated_at(cls, value: datetime) -> datetime:
        return _ensure_tzinfo(value)

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value: object) -> tuple[str, ...]:
        if value is None:
            return ()

        if isinstance(value, tuple):
            raw = list(value)
        elif isinstance(value, list):
            raw = value
        else:
            msg = "tags must be a list or tuple of strings"
            raise TypeError(msg)

        seen: set[str] = set()
        normalized: list[str] = []
        for item in raw:
            tag = str(item).strip()
            if not tag:
                continue
            if tag not in seen:
                seen.add(tag)
                normalized.append(tag)
        return tuple(normalized)


class BalanceSnapshot(BaseModel):
    """Represents an account balance captured at a point in time."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, extra="forbid")

    id: UUID
    account_id: UUID
    balance: Decimal
    snapshot_time: datetime
    created_at: datetime
    updated_at: datetime

    @field_validator("snapshot_time")
    @classmethod
    def _require_timezone(cls, value: datetime) -> datetime:
        return _ensure_tzinfo(value)

    @field_validator("created_at")
    @classmethod
    def _require_timezone_created(cls, value: datetime) -> datetime:
        return _ensure_tzinfo(value)

    @field_validator("updated_at")
    @classmethod
    def _require_timezone_updated(cls, value: datetime) -> datetime:
        return _ensure_tzinfo(value)


T = TypeVar('T')

class Result(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: str | None = None
    context: Dict[str, Any] | None = None

    def raise_for_error(self, exc_type: Type[Exception] = Exception):
        raise exc_type(self.error or "Error has occurred")

def Ok(data: T | None = None, context: Dict[str, Any] | None = None) -> Result[T]:
    return Result(success=True, data=data, context=context)

def Fail(error: str, context: Dict[str, Any] | None = None) -> Result[T]:
    return Result(success=False, error=error, context=context)

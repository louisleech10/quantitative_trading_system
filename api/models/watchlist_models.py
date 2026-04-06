"""Watchlist API models for Phase D persistence."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


WatchlistStatus = Literal["candidate", "verified", "rejected", "watching"]


class WatchlistEntryModel(BaseModel):
    """Single watchlist entry."""

    feature_name: str = Field(..., min_length=1, max_length=512)
    task_id: str = Field(default="unknown", min_length=1, max_length=128)
    status: WatchlistStatus = Field(default="watching")
    note: str = Field(default="", max_length=2000)
    ic_snapshot: Optional[float] = None
    icir_snapshot: Optional[float] = None
    turnover_snapshot: Optional[float] = None
    added_at: datetime
    updated_at: datetime

    @field_validator("feature_name")
    @classmethod
    def _strip_feature_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("feature_name 不可為空")
        return normalized


class WatchlistPayload(BaseModel):
    """Watchlist payload schema."""

    version: Literal["1.0"] = "1.0"
    updated_at: datetime
    entries: List[WatchlistEntryModel]


class WatchlistSyncRequest(BaseModel):
    """Full watchlist sync request."""

    entries: List[WatchlistEntryModel] = Field(default_factory=list)


class WatchlistQueryResponse(BaseModel):
    """Watchlist query response."""

    version: Literal["1.0"] = "1.0"
    updated_at: datetime
    entries: List[WatchlistEntryModel]

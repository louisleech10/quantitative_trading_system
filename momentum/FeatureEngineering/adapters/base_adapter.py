from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

import pandas as pd


@dataclass
class FieldMeta:
    name: str
    dtype: str
    unit: str
    description: str
    is_single_series: bool


class DataSourceAdapter(ABC):
    """Base class for all data source adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def market(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def available_fields(self) -> List[str]:
        raise NotImplementedError()

    @abstractmethod
    def fetch(
        self,
        symbol: str,
        timeframe: str,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> pd.DataFrame:
        """Fetch data and return a DataFrame indexed by timestamp."""
        raise NotImplementedError()

    @abstractmethod
    def get_field_metadata(self, field: str) -> FieldMeta:
        raise NotImplementedError()

    @abstractmethod
    def validate(self, df: pd.DataFrame) -> bool:
        raise NotImplementedError()

    def get_single_series_fields(self) -> List[str]:
        """Return fields usable for single-series indicators."""
        return [
            field
            for field in self.available_fields
            if self.get_field_metadata(field).is_single_series
        ]

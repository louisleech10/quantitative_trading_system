from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger
from momentum.core.protocols import IKlineReader
from momentum.FeatureEngineering.adapters.base_adapter import DataSourceAdapter, FieldMeta

logger = get_logger(__name__)


class CryptoSpotAdapter(DataSourceAdapter):
    """Read spot kline data from KlineStorageManager."""

    _RAW_FIELDS = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "taker_buy_volume",
        "taker_ratio",
        "quote_volume",
        "trades",
    ]

    _SYNTHETIC_FIELDS = ["avg-price", "med-price", "typ-price", "wcl-price", "log-volume", "log-quote-volume"]

    def __init__(self, storage_manager: IKlineReader) -> None:
        self._storage = storage_manager
        self._field_meta = self._build_field_meta()

    @property
    def name(self) -> str:
        return "crypto_spot"

    @property
    def market(self) -> str:
        return "crypto"

    @property
    def available_fields(self) -> List[str]:
        return self._RAW_FIELDS + self._SYNTHETIC_FIELDS

    def fetch(
        self,
        symbol: str,
        timeframe: str,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> pd.DataFrame:
        logger.info(f"Fetching spot data: {symbol}/{timeframe}")
        df = self._storage.read_klines(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            validate_continuity=True,
        )
        if df is None or df.empty:
            raise ValueError(f"No data returned for {symbol}/{timeframe}")

        df = df.copy()

        if "number_of_trades" in df.columns and "trades" not in df.columns:
            df["trades"] = df["number_of_trades"].astype("int64")

        if "trades" not in df.columns:
            df["trades"] = 0

        required = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "taker_buy_volume",
            "taker_ratio",
        ]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        df = self._add_synthetic_fields(df)
        df = df.set_index("timestamp", drop=True)

        if not self.validate(df):
            raise ValueError(f"Validation failed for {symbol}/{timeframe}")

        return df

    def get_field_metadata(self, field: str) -> FieldMeta:
        if field not in self._field_meta:
            raise KeyError(f"Unknown field: {field}")
        return self._field_meta[field]

    def validate(self, df: pd.DataFrame) -> bool:
        if df.empty:
            logger.error("Validation failed: empty dataframe")
            return False

        for field in self._RAW_FIELDS:
            if field not in df.columns:
                logger.error(f"Validation failed: missing field {field}")
                return False

        numeric_fields = [field for field in self._RAW_FIELDS + self._SYNTHETIC_FIELDS if field in df.columns]
        for field in numeric_fields:
            if not pd.api.types.is_numeric_dtype(df[field]):
                logger.error(f"Validation failed: {field} is not numeric")
                return False

        return True

    def get_last_timestamp(self, symbol: str, timeframe: str) -> Optional[int]:
        """Delegate timestamp lookup to storage manager."""
        return self._storage.get_last_timestamp(symbol, timeframe)

    def _add_synthetic_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        o = df["open"].astype("float64")
        h = df["high"].astype("float64")
        l = df["low"].astype("float64")
        c = df["close"].astype("float64")

        df["avg-price"] = (o + h + l + c) / 4.0
        df["med-price"] = (h + l) / 2.0
        df["typ-price"] = (h + l + c) / 3.0
        df["wcl-price"] = (h + l + c + c) / 4.0

        vol = df["volume"].astype("float64")
        df["log-volume"] = np.log1p(vol).astype("float32")

        if "quote_volume" in df.columns:
            qvol = df["quote_volume"].astype("float64")
            df["log-quote-volume"] = np.log1p(qvol).astype("float32")
        else:
            df["log-quote-volume"] = np.float32(0.0)

        for field in self._SYNTHETIC_FIELDS:
            df[field] = df[field].astype("float32")

        return df

    def _build_field_meta(self) -> Dict[str, FieldMeta]:
        meta: Dict[str, FieldMeta] = {
            "open": FieldMeta("open", "float32", "price", "Open price", True),
            "high": FieldMeta("high", "float32", "price", "High price", True),
            "low": FieldMeta("low", "float32", "price", "Low price", True),
            "close": FieldMeta("close", "float32", "price", "Close price", True),
            "volume": FieldMeta("volume", "float32", "volume", "Base asset volume", True),
            "taker_buy_volume": FieldMeta(
                "taker_buy_volume",
                "float32",
                "volume",
                "Taker buy base asset volume",
                True,
            ),
            "taker_ratio": FieldMeta(
                "taker_ratio",
                "float32",
                "ratio",
                "Taker buy ratio",
                True,
            ),
            "quote_volume": FieldMeta(
                "quote_volume",
                "float32",
                "volume",
                "Quote asset volume",
                True,
            ),
            "trades": FieldMeta(
                "trades",
                "int32",
                "count",
                "Number of trades",
                True,
            ),
            "avg-price": FieldMeta(
                "avg-price",
                "float32",
                "price",
                "Average price (O+H+L+C)/4",
                True,
            ),
            "med-price": FieldMeta(
                "med-price",
                "float32",
                "price",
                "Median price (H+L)/2",
                True,
            ),
            "typ-price": FieldMeta(
                "typ-price",
                "float32",
                "price",
                "Typical price (H+L+C)/3",
                True,
            ),
            "wcl-price": FieldMeta(
                "wcl-price",
                "float32",
                "price",
                "Weighted close price (H+L+2C)/4",
                True,
            ),
            "log-volume": FieldMeta(
                "log-volume",
                "float32",
                "volume",
                "Log-transformed base volume (log1p)",
                True,
            ),
            "log-quote-volume": FieldMeta(
                "log-quote-volume",
                "float32",
                "volume",
                "Log-transformed quote volume (log1p)",
                True,
            ),
        }
        return meta

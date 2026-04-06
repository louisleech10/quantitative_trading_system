"""Shared constants used across momentum domains."""

from __future__ import annotations

# Timeframe → seconds mapping (originally in KlineStorageManager)
TIMEFRAME_SECONDS: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "12h": 43200,
    "1d": 86400,
}

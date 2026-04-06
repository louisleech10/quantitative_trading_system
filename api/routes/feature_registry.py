"""Feature registry API routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from momentum.factories import create_feature_registry

router = APIRouter(prefix="/feature-registry", tags=["feature-registry"])


def _load_registry():
    return create_feature_registry()


@router.get("/entries")
def list_entries(
    symbol: Optional[str] = Query(None),
    timeframe: Optional[str] = Query(None),
) -> dict:
    """List all registry entries, optionally filtered by symbol/timeframe."""
    registry = _load_registry()
    entries = registry.list_all()
    if symbol:
        entries = [item for item in entries if item.get("symbol") == symbol]
    if timeframe:
        entries = [item for item in entries if item.get("timeframe") == timeframe]
    return {"entries": entries, "total": len(entries)}


@router.get("/latest")
def get_latest(
    symbol: str = Query(...),
    timeframe: str = Query(...),
) -> dict:
    """Get latest registry entry for a specific symbol/timeframe."""
    registry = _load_registry()
    entry = registry.find_latest(symbol, timeframe)
    if entry is None:
        return {"entry": None, "found": False}
    return {"entry": entry, "found": True}

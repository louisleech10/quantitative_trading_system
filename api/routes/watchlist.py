"""Watchlist routes for Phase D backend persistence."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.models.watchlist_models import WatchlistQueryResponse, WatchlistSyncRequest
from api.services.watchlist_service import get_watchlist_service


router = APIRouter(prefix="/api/v1/watchlist", tags=["Watchlist"])


@router.get("", response_model=WatchlistQueryResponse)
async def get_watchlist(
    status: Optional[str] = Query(default=None, pattern="^(candidate|verified|rejected|watching)?$"),
):
    try:
        return get_watchlist_service().get_entries(status=status)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(error))


@router.put("", response_model=WatchlistQueryResponse)
async def sync_watchlist(request: WatchlistSyncRequest):
    try:
        return get_watchlist_service().replace_entries(request.entries)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(error))

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from api.main import app
from api.models.watchlist_models import WatchlistEntryModel, WatchlistQueryResponse
from api.routes import watchlist


class _StubWatchlistService:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self._entries = [
            WatchlistEntryModel(
                feature_name="feat_a",
                task_id="task_1",
                status="verified",
                note="seed",
                ic_snapshot=0.12,
                icir_snapshot=0.85,
                turnover_snapshot=0.22,
                added_at=now,
                updated_at=now,
            )
        ]

    def get_entries(self, status: str | None = None) -> WatchlistQueryResponse:
        now = datetime.now(timezone.utc)
        entries = self._entries
        if status:
            entries = [entry for entry in entries if entry.status == status]
        return WatchlistQueryResponse(version="1.0", updated_at=now, entries=entries)

    def replace_entries(self, entries: list[WatchlistEntryModel]) -> WatchlistQueryResponse:
        self._entries = entries
        now = datetime.now(timezone.utc)
        return WatchlistQueryResponse(version="1.0", updated_at=now, entries=entries)


def test_watchlist_get_and_filter(monkeypatch):
    monkeypatch.setattr(watchlist, "get_watchlist_service", lambda: _StubWatchlistService())
    client = TestClient(app)

    response = client.get("/api/v1/watchlist")
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "1.0"
    assert len(payload["entries"]) == 1

    verified_response = client.get("/api/v1/watchlist", params={"status": "verified"})
    assert verified_response.status_code == 200
    verified_payload = verified_response.json()
    assert len(verified_payload["entries"]) == 1
    assert verified_payload["entries"][0]["feature_name"] == "feat_a"


def test_watchlist_sync(monkeypatch):
    service = _StubWatchlistService()
    monkeypatch.setattr(watchlist, "get_watchlist_service", lambda: service)
    client = TestClient(app)

    now = datetime.now(timezone.utc).isoformat()
    response = client.put(
        "/api/v1/watchlist",
        json={
            "entries": [
                {
                    "feature_name": "feat_b",
                    "task_id": "task_2",
                    "status": "candidate",
                    "note": "new",
                    "ic_snapshot": 0.08,
                    "icir_snapshot": 0.5,
                    "turnover_snapshot": 0.3,
                    "added_at": now,
                    "updated_at": now,
                }
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["feature_name"] == "feat_b"

    query = client.get("/api/v1/watchlist")
    assert query.status_code == 200
    queried = query.json()
    assert len(queried["entries"]) == 1
    assert queried["entries"][0]["status"] == "candidate"

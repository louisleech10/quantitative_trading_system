"""Step 6: timeframe 合法性驗證測試（4-13）。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_generate_route_rejects_invalid_timeframe_payload() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/features/generate",
            json={"symbol": "BTCUSDT", "timeframe": "2h"},
        )

    assert response.status_code == 422
    payload = response.json()
    detail = payload.get("detail", [])
    assert isinstance(detail, list)
    assert any("Unsupported timeframe" in str(item) for item in detail)

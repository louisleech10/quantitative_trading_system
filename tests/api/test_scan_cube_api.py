"""掃描結果立方體之查詢 API 測試（`SCANCUBE` Task 3.1）。

## 這批測試在防什麼

三個錯誤碼的語意分界。它們看起來都是「沒有東西」，但對使用者的意義完全不同：

- **404**＝找不到這個 task 的立方體 → 「你找錯地方了」
- **409**＝該層 fail-closed 沒保存 → 「東西算過，但因為太大沒存下來」
- **200 + 空 rows**＝篩選後真的沒有 → 「條件太嚴」

混為一談的後果：使用者看到空表，不知道該換 task、放寬篩選、還是縮小掃描範圍。
"""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from momentum.Analysis import scan_cube as sc
from api.routes import ic_analysis as route_mod

LIMITS = dict(max_rows=120000, max_rows_per_cell=5000,
              chart_max_bytes=209_715_200, keep_tasks=20)


def _row(name: str, ic: float) -> dict:
    return {
        "feature_name": name, "ic_mean": ic, "ic_std": 0.2, "icir": ic / 0.2,
        "p_value": 0.01, "t_stat": 2.5, "p_value_adj": 0.02, "ic_hit_rate": 0.55,
        "monotonicity_score": 0.8, "long_short_spread": 0.03, "coverage": 0.99,
        "turnover_rate": 0.15, "ic_half_life": 4.0, "regime_robust": None,
        "pass_class": "pass",
    }


def _cell(k: int, h: int, n: int = 5) -> dict:
    names = [f"feat_{i}" for i in range(n)]
    return {
        "k": k, "h": h, "capability": "available", "reason": None, "n_events": 100,
        "report": {
            "analysis_status": "ok_oos", "oos_guarantees": True,
            "summary_table": [_row(x, 0.1 + i * 0.01) for i, x in enumerate(names)],
            "ic_decay": {x: {"half_life": 4.0} for x in names},
            "grouped_ic": {"bull": {x: 0.12 for x in names}},
            "rolling_ic_series": {x: [0.1, 0.11] for x in names},
        },
    }


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """把立方體根目錄指向 tmp，避免碰真實 `data_cache/`。"""
    monkeypatch.setattr(sc, "DEFAULT_ROOT", tmp_path, raising=False)
    app = FastAPI()
    app.include_router(route_mod.router)
    return TestClient(app)


@pytest.fixture()
def built(tmp_path):
    cells = [_cell(k, h) for k in (0, 1) for h in (1, 2)]
    return sc.build_cube("t1", "ETHUSDT", "12h", cells, root=tmp_path, **LIMITS)


def test_manifest_returns_two_tier_state(client, built):
    resp = client.get("/api/v1/ic/scan-cube/t1/manifest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier_a"]["stored"] is True
    assert body["tier_b"]["stored"] is True
    assert body["excluded_sections"] == ["correlation_matrix"]


def test_missing_task_is_404_not_empty_rows(client):
    """🔴 找不到 ≠ 結果為空。回空陣列會讓使用者以為「這次分析真的沒東西」。"""
    resp = client.get("/api/v1/ic/scan-cube/nope/rows")
    assert resp.status_code == 404


def test_pagination_is_complete_and_unique(client, built):
    """🔴 `limit=7` 逐頁取完之聯集 == 全集且無重複（tie-breaker 生效）。"""
    seen: list[tuple] = []
    offset = 0
    while True:
        resp = client.get("/api/v1/ic/scan-cube/t1/rows",
                          params={"offset": offset, "limit": 7})
        assert resp.status_code == 200
        rows = resp.json()["rows"]
        if not rows:
            break
        seen.extend((r["k"], r["h"], r["feature_name"]) for r in rows)
        offset += 7
    assert len(seen) == len(set(seen)), "跨頁重複"
    assert len(seen) == 4 * 5


def test_total_is_filtered_count_not_page_size(client, built):
    resp = client.get("/api/v1/ic/scan-cube/t1/rows",
                      params={"k": 0, "limit": 2})
    body = resp.json()
    assert body["total"] == 10, "k=0 有 2 格 × 5 特徵"
    assert len(body["rows"]) == 2


def test_offset_beyond_total_returns_empty_rows_with_real_total(client, built):
    """越界 ⇒ 200 + 空 rows，但 `total` 仍是真實總數（**不是** 404）。"""
    resp = client.get("/api/v1/ic/scan-cube/t1/rows", params={"offset": 9999, "limit": 10})
    assert resp.status_code == 200
    assert resp.json()["rows"] == [] and resp.json()["total"] == 20


def test_unknown_metric_is_400_not_silently_ignored(client, built):
    """🔴 靜默忽略會讓使用者以為那個欄位真的沒有值。"""
    resp = client.get("/api/v1/ic/scan-cube/t1/rows", params={"metric": "not_a_metric"})
    assert resp.status_code == 400
    assert "not_a_metric" in json.dumps(resp.json(), ensure_ascii=False)


def test_limit_over_page_max_is_400_not_clamped(client, built):
    """🔴 靜默夾住會讓使用者以為看到了全部。"""
    resp = client.get("/api/v1/ic/scan-cube/t1/rows", params={"limit": 100000})
    assert resp.status_code == 400


def test_sort_field_must_be_a_known_metric(client, built):
    assert client.get("/api/v1/ic/scan-cube/t1/rows",
                      params={"sort": "bogus:asc"}).status_code == 400
    assert client.get("/api/v1/ic/scan-cube/t1/rows",
                      params={"sort": "icir:sideways"}).status_code == 400
    assert client.get("/api/v1/ic/scan-cube/t1/rows",
                      params={"sort": "icir:desc"}).status_code == 200


def test_tier_a_not_stored_is_409_not_empty_page(client, tmp_path):
    """🔴 沒保存 ≠ 沒資料。回空頁會讓使用者以為分析結果是空的。"""
    sc.build_cube("t2", None, None, [_cell(0, 1)], root=tmp_path,
                  **{**LIMITS, "max_rows": 1})
    resp = client.get("/api/v1/ic/scan-cube/t2/rows")
    assert resp.status_code == 409
    assert resp.json()["detail"]["reason"] == "scan_cube_rows_exceeded"


def test_tier_b_not_stored_is_409_with_fits_hint(client, tmp_path):
    """Tier B 沒保存 ⇒ 409 並**附上 fits_hint**，使用者才知道縮到多小可以看到圖。"""
    sc.build_cube("t3", None, None, [_cell(0, 1), _cell(0, 2)], root=tmp_path,
                  **{**LIMITS, "chart_max_bytes": 10})
    resp = client.get("/api/v1/ic/scan-cube/t3/charts",
                      params={"k": 0, "h": 1, "feature": "feat_0"})
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["reason"] == "scan_cube_chart_bytes_exceeded"
    assert detail["fits_hint"]["max_feature_cells"] >= 0

    # 🔴 Tier B 掛掉不得影響 Tier A
    assert client.get("/api/v1/ic/scan-cube/t3/rows").status_code == 200


def test_charts_returns_report_shaped_slice(client, built):
    """回傳與 report 同形狀；`grouped_ic` 保持 `{group: {feature: …}}` 巢狀。"""
    resp = client.get("/api/v1/ic/scan-cube/t1/charts",
                      params={"k": 0, "h": 1, "feature": "feat_2"})
    assert resp.status_code == 200
    sections = resp.json()["sections"]
    assert set(sections["ic_decay"]) == {"feat_2"}
    assert set(sections["grouped_ic"]["bull"]) == {"feat_2"}


def test_charts_unknown_cell_is_404(client, built):
    resp = client.get("/api/v1/ic/scan-cube/t1/charts",
                      params={"k": 9, "h": 9, "feature": "feat_0"})
    assert resp.status_code == 404

"""ICPERF SPEC Task 0.6 (h) ⑦ 牆鐘中止（L1c；委員會 r169 G3）：Coverage 三端點改背景任務之 API 層驗收。

L0 列（git 物件 `1eeef821:tests/_golden/icperf/limit_inventory.json`）：
- `api/models/feature_browser_models.py:20`／`:42`／`:66`：請求之逾時秒數欄（預設 30、上界 120，⑦）⇒ 自請求移除，
  三個請求模型 extra="forbid"，送該欄 ⇒ 422。欄名見 `REMOVED_TIME_FIELD`（字面登記於 NOCAP 白名單 D 類）。
- `api/models/feature_browser_models.py:65`：`top_n` 預設 100、上界 500（③ 分頁）⇒ 請求移除（送 ⇒ 422），
  改由結果端點 offset／limit 分頁（limit ≥ 1、無上界），不帶 offset／limit ⇒ 全量匯出。
- `api/routes/feature_browser.py:53`／`:71`／`:92`：同步等待並於牆鐘逾時回 504 ⇒ POST 立即回
  `{"task_id"}`，`GET /feature-browser/tasks/{id}` 查狀態與進度、`POST .../cancel` 協作取消、`GET .../result` 取結果。
- `momentum/Analysis/coverage_analyzer.py:388`／`:460`／`:461`：`top_n` 截斷 `sorted_features[:limit]`（③）⇒ 任務路徑
  計算不截斷、存全量排序結果；讀頁自存檔切片，不重算。
f2 判定（SPEC (h)）：⑦ 舊預設時間預算為有限值 ⇒ f2；結果比對對象＝任務完成後結果端點之內容；回應外殼改為 task id
屬逐端點宣告之契約變更。未觸發舊界之請求（本檔資料規模）其結果須與修前同步端點逐鍵相等。

資料：沿 `tests/api/test_feature_browser_routes.py` 之作法以 `FeatureStorage.write_raw` 於 tmp 建 V2 raw run，
特徵值一律由真實 K 線 `data_cache/feature_klines/kline_cache.h5`（BTCUSDT／ETHUSDT／SOLUSDT 12h）計算
（close／SMA(w) − 1 與對數報酬；三幣取不同尾段長度使各特徵跨幣覆蓋率離散度 Δ 互異且無並列），禁合成值。
group_sma 有 130 個特徵（> 舊 top_n 預設 100）。

測試接縫（施工契約，於此宣告）：
- 路由於請求當下取 `feature_browser_service.job_store`（`api.core.background_jobs.BackgroundJobStore`）；
  測試以 monkeypatch 注入 tmp 目錄之實例。
- 完成之同步以 `job_store.wait(task_id)`（threading.Event 等至終態，無逾時）；取消之安全點以分析器
  `on_step` 掛鉤＋Event barrier 驅動，不靠牆鐘。
- 分析器三函式接受 `on_step(phase, processed, total)`；任務路徑必傳入，掛鉤可拋 `JobCancelled`。
- 未知 task ⇒ 404 且 detail 含該 task_id；結果於非 completed 時 ⇒ 409；取消回應 `{"task_id", "cancel"}`，
  `cancel` 為 store.cancel 之回傳（cancelling／cancelled／already_terminal）。
- API 啟動（lifespan）呼叫 `feature_browser_service.job_store.mark_interrupted_on_startup()`。
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.core.background_jobs import BackgroundJobStore, JobCancelled
from api.main import app
from api.services.feature_browser_service import feature_browser_service
from momentum.factories import create_coverage_analyzer, create_kline_storage_manager
from momentum.FeatureEngineering.feature_storage import FeatureStorage

client = TestClient(app)
API = "/api/v1/feature-browser"
TF = "12h"
KLINE = Path("data_cache/feature_klines/kline_cache.h5")
#: 被移除之請求逾時秒數欄名（負測試：斷言送此欄即 422，非時間上限；本行於 scripts/timeout_registry.json 登記 D 類）。
REMOVED_TIME_FIELD = "timeout_seconds"
#: 三幣取不同尾段長度（真實 12h K 線各 1696 根）⇒ 同一 SMA 窗之覆蓋率跨幣不同
SYMBOL_ROWS = {"BTCUSDT": 1600, "ETHUSDT": 1000, "SOLUSDT": 700}
SYMBOLS = list(SYMBOL_ROWS)
SMA_WINDOWS = tuple(range(2, 132))  # 130 個特徵 > 舊 top_n 預設 100
RET_LAGS = (1, 2, 3, 4, 5)
CFG_A = "cfg_l1c_a"
CFG_B = "cfg_l1c_b"  # 字典序晚於 CFG_A ⇒ 發布後成為 latest

M_SHA = "e641c6d7a7d85bd44405edc92533cf1bb665918a875aa7b43f6e1f9ea58cedf2"
ROW_MODEL_20 = ("api/models/feature_browser_models.py", 20, M_SHA)
ROW_MODEL_42 = ("api/models/feature_browser_models.py", 42, M_SHA)
ROW_MODEL_66 = ("api/models/feature_browser_models.py", 66, M_SHA)
ROW_MODEL_65 = ("api/models/feature_browser_models.py", 65,
                "feaf02d40ea28a8c211c4e7afe2bf3a7dc9497499beecd7d2c4e106080d157f7")
ROW_ROUTE_53 = ("api/routes/feature_browser.py", 53, "0a712e5934f0eeb31a68802861f75e50a7c6ff093af8995a98286fd80e30e9d5")
ROW_ROUTE_71 = ("api/routes/feature_browser.py", 71, "d260aedf451141596bc46e0e56585bdaf8f97334c6a78f1dc60e4f47d15b0cc9")
ROW_ROUTE_92 = ("api/routes/feature_browser.py", 92, "3796f758a65eb17391d0f42578eff69e4f1de161f9b3fa08aa85ea6279e0fa02")
ROW_AN_388 = ("momentum/Analysis/coverage_analyzer.py", 388,
              "47e374d3fe299eb12e95be74bc654d4475f642f693217e7b518cdf923a378771")
ROW_AN_460 = ("momentum/Analysis/coverage_analyzer.py", 460,
              "505fda6be0d7775a16c3b430b397e45dde176d8da6ca2a4cd4f03b1b889b285c")
ROW_AN_461 = ("momentum/Analysis/coverage_analyzer.py", 461,
              "2c1854ae8ca8258ed76f20a400702d21a5ffc252c0de2dab308038f1408e6ea6")

ENDPOINTS = {
    "coverage-matrix": (ROW_ROUTE_53, ROW_MODEL_20),
    "group-coverage": (ROW_ROUTE_71, ROW_MODEL_42),
    "group-feature-coverage": (ROW_ROUTE_92, ROW_MODEL_66),
}

pytestmark = pytest.mark.requires_kline


# ---------------------------------------------------------------------------
# 真實 K 線 → V2 raw run
# ---------------------------------------------------------------------------

def _groups_from_close(close: pd.Series) -> Dict[str, pd.DataFrame]:
    """只用 t 與過去資料（rolling 右端為 t、shift 正向）；float32 同既有路由測試。"""
    close = close.reset_index(drop=True).astype(np.float64)
    log_close = np.log(close)
    sma = {f"close_sma_ratio_{w:03d}": (close / close.rolling(w).mean() - 1.0).astype(np.float32) for w in SMA_WINDOWS}
    ret = {f"log_return_{k}": (log_close - log_close.shift(k)).astype(np.float32) for k in RET_LAGS}
    return {"group_sma": pd.DataFrame(sma), "group_ret": pd.DataFrame(ret)}


@pytest.fixture(scope="module")
def real_closes() -> Dict[str, pd.Series]:
    if not KLINE.is_file():
        pytest.fail(f"requires_kline: missing kline cache file: {KLINE}")
    storage = create_kline_storage_manager(cache_dir=str(KLINE.parent))
    out: Dict[str, pd.Series] = {}
    for symbol in SYMBOLS:
        kline = storage.read_klines(symbol, TF, validate_continuity=False)
        if kline is None or kline.empty:
            pytest.fail(f"requires_kline: no data for {symbol}/{TF}")
        close = pd.to_numeric(kline["close"], errors="raise")
        assert np.isfinite(close.to_numpy(dtype=np.float64)).all(), f"{symbol} close 含非有限值"
        out[symbol] = close
    return out


def _publish(base: Path, closes: Dict[str, pd.Series], config_hash: str,
             rows: Dict[str, int]) -> Dict[str, Dict[str, pd.DataFrame]]:
    storage = FeatureStorage(str(base))
    written: Dict[str, Dict[str, pd.DataFrame]] = {}
    for symbol, n in rows.items():
        close = closes[symbol]
        if len(close) < n:
            pytest.fail(f"requires_kline: {symbol}/{TF} has {len(close)} rows, need >= {n}")
        groups = _groups_from_close(close.iloc[-n:])
        storage.write_raw(symbol, TF, config_hash, groups)
        written[symbol] = groups
    return written


@pytest.fixture
def feature_run(tmp_path: Path, real_closes: Dict[str, pd.Series]) -> Dict[str, Any]:
    base = tmp_path / "features"
    base.mkdir()
    written = _publish(base, real_closes, CFG_A, SYMBOL_ROWS)
    return {"base": base, "written": written, "closes": real_closes}


@pytest.fixture
def job_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BackgroundJobStore:
    store = BackgroundJobStore(tmp_path / "jobs")
    monkeypatch.setattr(feature_browser_service, "job_store", store, raising=False)
    return store


def _oracle_group_feature(written: Dict[str, Dict[str, pd.DataFrame]], group: str) -> Dict[str, Any]:
    """獨立 oracle：自寫入之 frame 逐欄算有限值比率、跨幣 Δ＝max−min，依 Δ 由大到小（名稱序為並列序）排序，不截斷。"""
    names = sorted({c for frames in written.values() for c in frames[group].columns})
    matrix = {n: {s: float(np.isfinite(written[s][group][n].to_numpy(dtype=np.float64)).sum() / len(written[s][group]))
                  for s in SYMBOLS} for n in names}
    divergence = {n: float(max(matrix[n].values()) - min(matrix[n].values())) for n in names}
    ordered = sorted(names, key=lambda n: divergence[n], reverse=True)
    return {"features": ordered, "matrix": matrix, "divergence": divergence,
            "row_counts": {s: len(written[s][group]) for s in SYMBOLS}}


def _norm(obj: Any) -> Any:
    return json.loads(json.dumps(obj))


def _body(endpoint: str, base: Path, **extra: Any) -> Dict[str, Any]:
    body: Dict[str, Any] = {"symbols": SYMBOLS, "timeframe": TF, "feature_base_path": str(base)}
    if endpoint == "coverage-matrix":
        body["feature_names"] = []
    if endpoint == "group-feature-coverage":
        body["group_name"] = "group_sma"
    body.update(extra)
    return body


def _submit(endpoint: str, body: Dict[str, Any]) -> str:
    resp = client.post(f"{API}/{endpoint}", json=body)
    assert resp.status_code == 200, resp.text[:300]
    payload = resp.json()
    assert isinstance(payload.get("task_id"), str) and payload["task_id"], payload
    assert "matrix" not in payload and "features" not in payload, "POST 不得同步回傳結果"
    return payload["task_id"]


def _status(task_id: str) -> Dict[str, Any]:
    resp = client.get(f"{API}/tasks/{task_id}")
    assert resp.status_code == 200, resp.text[:300]
    return resp.json()


def _result(task_id: str, **params: Any) -> Dict[str, Any]:
    resp = client.get(f"{API}/tasks/{task_id}/result", params=params)
    assert resp.status_code == 200, resp.text[:300]
    return resp.json()


# ---------------------------------------------------------------------------
# 契約：POST 回 task id、請求移除逾時秒數欄／top_n
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "endpoint",
    [pytest.param(name, marks=pytest.mark.limit_rows(*rows)) for name, rows in ENDPOINTS.items()],
)
def test_post_returns_task_id_and_task_completes(endpoint: str, feature_run: Dict[str, Any],
                                                 job_store: BackgroundJobStore) -> None:
    """三端點 POST 立即回 task_id（不含結果）；狀態可查（含 progress 四欄），完成時 processed＝total＞0。"""
    tid = _submit(endpoint, _body(endpoint, feature_run["base"]))
    assert job_store.wait(tid)["state"] == "completed"
    st = _status(tid)
    assert st["task_id"] == tid and st["state"] == "completed"
    assert {"phase", "processed", "total", "updated_at"} <= set(st["progress"])
    assert st["progress"]["total"] > 0 and st["progress"]["processed"] == st["progress"]["total"]


@pytest.mark.parametrize(
    "endpoint",
    [pytest.param(name, marks=pytest.mark.limit_rows(rows[1])) for name, rows in ENDPOINTS.items()],
)
def test_removed_time_field_rejected(endpoint: str, feature_run: Dict[str, Any], job_store: BackgroundJobStore) -> None:
    """請求移除逾時秒數欄（extra="forbid"）⇒ 送此欄 422（含舊預設值 30）。"""
    resp = client.post(f"{API}/{endpoint}", json=_body(endpoint, feature_run["base"], **{REMOVED_TIME_FIELD: 30}))
    assert resp.status_code == 422, resp.text[:300]
    assert REMOVED_TIME_FIELD in resp.text


@pytest.mark.limit_rows(ROW_MODEL_65)
def test_top_n_rejected(feature_run: Dict[str, Any], job_store: BackgroundJobStore) -> None:
    """GroupFeatureCoverageRequest 移除 top_n（顯示分頁改由結果端點 offset／limit）⇒ 送 top_n 422。"""
    resp = client.post(f"{API}/group-feature-coverage", json=_body("group-feature-coverage", feature_run["base"], top_n=100))
    assert resp.status_code == 422, resp.text[:300]
    assert "top_n" in resp.text


def test_single_symbol_still_rejected_synchronously(feature_run: Dict[str, Any], job_store: BackgroundJobStore) -> None:
    """輸入驗證（< 2 個 Symbol）仍於 POST 當下 400，不建立任務（回歸守護）。"""
    resp = client.post(f"{API}/group-coverage", json={"symbols": ["BTCUSDT"], "timeframe": TF,
                                                       "feature_base_path": str(feature_run["base"])})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# f2 未觸發舊界之請求：任務結果＝修前同步端點結果
# ---------------------------------------------------------------------------

@pytest.mark.limit_rows(ROW_ROUTE_53, ROW_MODEL_20)
def test_coverage_matrix_result_equals_sync_service(feature_run: Dict[str, Any], job_store: BackgroundJobStore) -> None:
    base = feature_run["base"]
    expected = _norm(feature_browser_service.get_coverage_matrix(
        symbols=SYMBOLS, timeframe=TF, feature_names=[], feature_base_path=str(base)))
    assert len(expected["features"]) == len(SMA_WINDOWS) + len(RET_LAGS)
    tid = _submit("coverage-matrix", _body("coverage-matrix", base))
    job_store.wait(tid)
    assert _result(tid) == expected


@pytest.mark.limit_rows(ROW_ROUTE_71, ROW_MODEL_42)
def test_group_coverage_result_equals_sync_service(feature_run: Dict[str, Any], job_store: BackgroundJobStore) -> None:
    base = feature_run["base"]
    expected = _norm(feature_browser_service.get_group_coverage(symbols=SYMBOLS, timeframe=TF, feature_base_path=str(base)))
    assert sorted(expected["groups"]) == ["group_ret", "group_sma"]
    tid = _submit("group-coverage", _body("group-coverage", base))
    job_store.wait(tid)
    assert _result(tid) == expected


@pytest.mark.limit_rows(ROW_ROUTE_92, ROW_MODEL_65, ROW_MODEL_66, ROW_AN_460, ROW_AN_461)
def test_group_feature_first_page_equals_old_default(feature_run: Dict[str, Any], job_store: BackgroundJobStore) -> None:
    """預設第一頁（offset 0、limit 100）之各欄＝修前同步端點 top_n=100 之回應；另帶 total（未截斷數 130）。"""
    base = feature_run["base"]
    old = _norm(feature_browser_service.get_group_feature_coverage(
        symbols=SYMBOLS, timeframe=TF, group_name="group_sma", feature_base_path=str(base), top_n=100))
    assert len(old["features"]) == 100  # 修前截斷於 100（證此資料確實觸及舊界）
    tid = _submit("group-feature-coverage", _body("group-feature-coverage", base))
    job_store.wait(tid)
    page = _result(tid, offset=0, limit=100)
    for key in ("group_name", "features", "symbols", "matrix", "divergence", "row_counts"):
        assert page[key] == old[key], key
    assert (page["total"], page["offset"], page["limit"]) == (len(SMA_WINDOWS), 0, 100)


# ---------------------------------------------------------------------------
# ③ 全量計算＋分頁遍歷＋匯出；讀頁不重算；讀頁不受新 run 影響
# ---------------------------------------------------------------------------

@pytest.mark.limit_rows(ROW_AN_388, ROW_AN_460, ROW_AN_461, ROW_ROUTE_92)
def test_group_feature_full_result_matches_independent_oracle(feature_run: Dict[str, Any],
                                                              job_store: BackgroundJobStore) -> None:
    """不帶 offset／limit ⇒ 全量（130 個，不截斷）；逐值＝獨立 oracle（有限值比率、Δ、排序、row_counts）。"""
    oracle = _oracle_group_feature(feature_run["written"], "group_sma")
    assert len(oracle["features"]) == len(SMA_WINDOWS) == 130
    assert len(set(oracle["divergence"].values())) == 130  # Δ 無並列 ⇒ 排序唯一
    tid = _submit("group-feature-coverage", _body("group-feature-coverage", feature_run["base"]))
    job_store.wait(tid)
    full = _result(tid)
    assert full["total"] == 130
    assert full["features"] == oracle["features"]
    assert full["matrix"] == oracle["matrix"]
    assert full["divergence"] == oracle["divergence"]
    assert full["row_counts"] == oracle["row_counts"]
    assert full["symbols"] == SYMBOLS and full["group_name"] == "group_sma"


@pytest.mark.limit_rows(ROW_AN_460, ROW_AN_461, ROW_ROUTE_92, ROW_MODEL_65)
def test_pages_concat_equals_full_without_recompute(feature_run: Dict[str, Any], job_store: BackgroundJobStore,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    """limit=7 逐頁遍歷之串接＝全量匯出；每頁 total＝130；越界頁為空；limit 無上界（1000 一頁全收）；
    limit=0、offset<0 ⇒ 422；讀頁全程不再呼叫分析器（計數不變）。"""
    analyzer = feature_browser_service._coverage_analyzer  # noqa: SLF001
    original = analyzer.compute_group_feature_coverage
    calls: List[int] = []

    def counting(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(analyzer, "compute_group_feature_coverage", counting)
    tid = _submit("group-feature-coverage", _body("group-feature-coverage", feature_run["base"]))
    job_store.wait(tid)
    assert len(calls) == 1
    full = _result(tid)

    features: List[str] = []
    matrix: Dict[str, Any] = {}
    divergence: Dict[str, Any] = {}
    offset = 0
    while offset < full["total"]:
        page = _result(tid, offset=offset, limit=7)
        assert (page["total"], page["offset"], page["limit"]) == (130, offset, 7)
        assert len(page["features"]) == min(7, 130 - offset)
        assert set(page["matrix"]) == set(page["features"]) == set(page["divergence"])
        features += page["features"]
        matrix.update(page["matrix"])
        divergence.update(page["divergence"])
        offset += 7
    assert features == full["features"] and matrix == full["matrix"] and divergence == full["divergence"]
    assert _result(tid, offset=130, limit=7)["features"] == []
    assert _result(tid, offset=0, limit=1000)["features"] == full["features"]
    assert client.get(f"{API}/tasks/{tid}/result", params={"offset": 0, "limit": 0}).status_code == 422
    assert client.get(f"{API}/tasks/{tid}/result", params={"offset": -1, "limit": 7}).status_code == 422
    assert len(calls) == 1, "讀頁不得重算"


@pytest.mark.limit_rows(ROW_AN_460, ROW_AN_461, ROW_ROUTE_92)
def test_pages_stable_after_new_run_published(feature_run: Dict[str, Any], job_store: BackgroundJobStore) -> None:
    """讀完第一頁後同目錄發布新 run（latest 改變）：舊任務後續頁與全量匯出不變（讀存檔、不重算）；
    證偽：同請求之新計算確實不同。"""
    base = feature_run["base"]
    tid = _submit("group-feature-coverage", _body("group-feature-coverage", base))
    job_store.wait(tid)
    first = _result(tid, offset=0, limit=10)
    full_before = _result(tid)

    _publish(base, feature_run["closes"], CFG_B, {s: 600 for s in SYMBOLS})  # 三幣同長 ⇒ Δ 全 0
    fresh = _norm(feature_browser_service.get_group_feature_coverage(
        symbols=SYMBOLS, timeframe=TF, group_name="group_sma", feature_base_path=str(base), top_n=100))
    assert fresh["row_counts"] != full_before["row_counts"]  # 新 run 確實改變結果

    assert _result(tid, offset=0, limit=10) == first
    for offset in range(10, 130, 10):
        page = _result(tid, offset=offset, limit=10)
        assert page["features"] == full_before["features"][offset:offset + 10]
        assert page["row_counts"] == full_before["row_counts"]
    assert _result(tid) == full_before


# ---------------------------------------------------------------------------
# 協作取消、失敗、未知任務、啟動標 interrupted
# ---------------------------------------------------------------------------

def _install_barrier(monkeypatch: pytest.MonkeyPatch) -> Tuple[threading.Event, threading.Event, Dict[str, Any]]:
    """包裝分析器：首次 on_step 時 set reached、等 release，再交給任務之 on_step（安全點，可拋 JobCancelled）。
    任務路徑未傳 on_step 或分析器未呼叫 on_step 即返回 ⇒ 仍 set reached 並記錄，避免測試無限等待。"""
    analyzer = feature_browser_service._coverage_analyzer  # noqa: SLF001
    original = analyzer.compute_group_feature_coverage
    reached, release = threading.Event(), threading.Event()
    info: Dict[str, Any] = {"on_step_passed": None, "step_seen": False}

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        inner: Optional[Callable[[str, int, int], None]] = kwargs.get("on_step")
        info["on_step_passed"] = inner is not None
        if inner is None:
            reached.set()
            raise AssertionError("任務路徑未傳入 on_step 安全點掛鉤")

        def step(phase: str, processed: int, total: int) -> None:
            if not info["step_seen"]:
                info["step_seen"] = True
                reached.set()
                release.wait()
            inner(phase, processed, total)

        kwargs["on_step"] = step
        try:
            return original(*args, **kwargs)
        finally:
            reached.set()

    monkeypatch.setattr(analyzer, "compute_group_feature_coverage", wrapped)
    return reached, release, info


@pytest.mark.limit_rows(ROW_ROUTE_92, ROW_MODEL_66)
def test_cancel_takes_effect_at_analyzer_safe_point(feature_run: Dict[str, Any], job_store: BackgroundJobStore,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    """執行中：狀態 running、結果 409；取消 ⇒ cancelling，放行後於 on_step 安全點生效 ⇒ cancelled、結果仍 409。"""
    reached, release, info = _install_barrier(monkeypatch)
    try:
        tid = _submit("group-feature-coverage", _body("group-feature-coverage", feature_run["base"]))
        waiter = threading.Thread(target=lambda: (job_store.wait(tid), reached.set()), daemon=True)
        waiter.start()  # 任務若未呼叫分析器即終態，仍喚醒 reached
        reached.wait()
        assert info["on_step_passed"] is True and info["step_seen"] is True, info
        assert _status(tid)["state"] == "running"
        assert client.get(f"{API}/tasks/{tid}/result").status_code == 409
        resp = client.post(f"{API}/tasks/{tid}/cancel")
        assert resp.status_code == 200, resp.text[:300]
        assert resp.json() == {"task_id": tid, "cancel": "cancelling"}
        assert _status(tid)["state"] == "cancelling"
    finally:
        release.set()
    assert job_store.wait(tid)["state"] == "cancelled"
    assert _status(tid)["state"] == "cancelled"
    assert client.get(f"{API}/tasks/{tid}/result").status_code == 409
    again = client.post(f"{API}/tasks/{tid}/cancel")
    assert again.status_code == 200 and again.json()["cancel"] == "already_terminal"


@pytest.mark.limit_rows(ROW_ROUTE_92)
def test_group_not_found_becomes_failed_task(feature_run: Dict[str, Any], job_store: BackgroundJobStore) -> None:
    """分析器於載入時才知之錯誤（group 不存在）⇒ 任務 failed、error 帶原因（修前為同步 400）。"""
    tid = _submit("group-feature-coverage", _body("group-feature-coverage", feature_run["base"], group_name="group_missing"))
    assert job_store.wait(tid)["state"] == "failed"
    st = _status(tid)
    assert st["state"] == "failed" and "group not found" in str(st["error"])
    assert client.get(f"{API}/tasks/{tid}/result").status_code == 409


def test_unknown_task_404(job_store: BackgroundJobStore) -> None:
    tid = "no-such-task-l1c"
    for resp in (client.get(f"{API}/tasks/{tid}"), client.post(f"{API}/tasks/{tid}/cancel"),
                 client.get(f"{API}/tasks/{tid}/result")):
        assert resp.status_code == 404
        assert tid in str(resp.json().get("detail")), resp.text[:200]


def test_startup_marks_previous_unfinished_tasks_interrupted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """前一行程留下之 queued 紀錄：API 啟動（lifespan）後同 task_id 查得 interrupted 與原因。"""
    root = tmp_path / "jobs"
    previous = BackgroundJobStore(root)
    tid = previous.create("group_coverage", {"symbols": SYMBOLS})
    fresh = BackgroundJobStore(root)
    monkeypatch.setattr(feature_browser_service, "job_store", fresh, raising=False)
    with TestClient(app) as started:
        resp = started.get(f"{API}/tasks/{tid}")
    assert resp.status_code == 200, resp.text[:300]
    assert resp.json()["state"] == "interrupted" and resp.json()["error"]


# ---------------------------------------------------------------------------
# 分析器 on_step 安全點掛鉤（直接呼叫）
# ---------------------------------------------------------------------------

def _analyzer_calls(base: Path) -> Dict[str, Callable[..., Any]]:
    analyzer = create_coverage_analyzer()
    common = {"symbols": SYMBOLS, "timeframe": TF, "feature_base_path": str(base)}
    return {
        "symbol_matrix": lambda **kw: analyzer.compute_symbol_coverage_matrix(feature_names=[], **common, **kw),
        "group_matrix": lambda **kw: analyzer.compute_group_coverage_matrix(**common, **kw),
        "group_feature": lambda **kw: analyzer.compute_group_feature_coverage(group_name="group_sma", **common, **kw),
    }


@pytest.mark.parametrize("which", ["symbol_matrix", "group_matrix", "group_feature"])
@pytest.mark.limit_rows(ROW_AN_388)
def test_analyzer_on_step_reports_monotonic_progress(which: str, feature_run: Dict[str, Any]) -> None:
    """on_step 於安全點被呼叫（至少每 symbol 一次）：processed 不減、末次 processed＝total＞0；結果與不帶掛鉤時相同。"""
    fn = _analyzer_calls(feature_run["base"])[which]
    steps: List[Tuple[str, int, int]] = []
    with_hook = fn(on_step=lambda phase, processed, total: steps.append((phase, processed, total)))
    assert len(steps) >= len(SYMBOLS)
    assert all(isinstance(p, str) for p, _, _ in steps)
    processed = [s[1] for s in steps]
    assert processed == sorted(processed)
    assert steps[-1][1] == steps[-1][2] > 0
    assert _norm(with_hook) == _norm(fn())


@pytest.mark.parametrize("which", ["symbol_matrix", "group_matrix", "group_feature"])
@pytest.mark.limit_rows(ROW_AN_388)
def test_analyzer_on_step_cancel_propagates(which: str, feature_run: Dict[str, Any]) -> None:
    """on_step 拋 JobCancelled ⇒ 分析器不吞例外、立即向上拋（不繼續計算）。"""
    fn = _analyzer_calls(feature_run["base"])[which]
    count: List[int] = []

    def cancel_on_first(phase: str, processed: int, total: int) -> None:
        count.append(1)
        raise JobCancelled("安全點取消")

    with pytest.raises(JobCancelled):
        fn(on_step=cancel_on_first)
    assert len(count) == 1

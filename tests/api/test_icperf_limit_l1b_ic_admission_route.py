"""ICPERF SPEC v5.87 Task 0.6 (h) ⑤ IC 分析啟動准入（L1b；諮詢 r165 收斂檔 C1–C7）之 API 層驗收。

L0 列（git 物件 `1eeef821:tests/_golden/icperf/limit_inventory.json`）：
- `api/core/config.py:30`、`api/routes/ic_analysis.py:87`／`:89`：固定欄數上限 80515 ⇒ 依任務峰值估算之准入
  （f2：舊預設請求於越舊界 run 修前 400；修後於預算足時建立任務、不足時排隊、單任務逾正式預算才 400 帶 need／have）。
- `api/routes/ic_analysis.py:453`：/full-analysis 收到事件批之功能 fail-closed（非上限，⑥ 保留；本檔驗其仍拒）。
- U2 後端消費端（`frontend/src/components/ic-analysis/FeatureFilterPanel.tsx:99` 之前端驗收見 vitest）：
  501 個 selected_features 經路由、服務抵達深度分析計算端。
f2 之「越舊界真實 run 完整算出並以獨立 oracle 驗值」屬重型（經 run_watched），另列；本檔為秒級判定與契約。
准入快照一律注入（`memory_budget.admission_snapshot`），不依實機記憶體。
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import ic_analysis_service as svc_mod

client = TestClient(app)
API = "/api/v1/ic"
REPO = Path(__file__).resolve().parents[2]
GiB = 1 << 30

ROW_CONFIG_30 = ("api/core/config.py", 30, "3d09a2bc57da300f911c2161adf53bc1da22ee49668445015a87f09ba8028839")
ROW_ROUTE_87 = ("api/routes/ic_analysis.py", 87, "119e531ebe6f0593fadcb0e5c8c6ab1a2fb6c847bc4d27d4bc2eac9017086c6b")
ROW_ROUTE_89 = ("api/routes/ic_analysis.py", 89, "f1971768baf175f16ff63e47f719cbef67201fee4cb05261190b050012dc8862")
ROW_ROUTE_453 = ("api/routes/ic_analysis.py", 453, "f1971768baf175f16ff63e47f719cbef67201fee4cb05261190b050012dc8862")
ROW_FILTER_99 = ("frontend/src/components/ic-analysis/FeatureFilterPanel.tsx", 99,
                 "343dd1a589c858e99f90c06356a13f7431d94e637610812a476d5e85255d5be8")

#: 越舊界之真實規模（registry 實有 BTCUSDT 12h 94488 欄 × 1951 列；以注入固定之，不依本機 registry 現況）
OVER_OLD_CAP_FEATURES = 94_488
OVER_OLD_CAP_ROWS = 1_951


def _task_count() -> int:
    return len(svc_mod.ic_analysis_service._tasks)  # noqa: SLF001


@pytest.fixture
def budget(monkeypatch: pytest.MonkeyPatch):
    """注入准入快照：回傳可改之 dict；service 於判定當下經 factory 取 memory_budget 模組屬性。"""
    from momentum.factories import get_memory_budget

    state: Dict[str, Any] = {"available_bytes": 64 * GiB, "budget_bytes": 64 * GiB, "source": "test"}
    monkeypatch.setattr(get_memory_budget(), "admission_snapshot", lambda: dict(state))
    return state


@pytest.fixture
def inject_run(tmp_path: Path):
    """同 tests/api/test_gap3_ic_stop_gate.py 之受控 registry 注入，另帶 row_count（准入估算之列數來源）。"""
    library = svc_mod.ic_analysis_service._feature_library  # noqa: SLF001
    registry = library._registry  # noqa: SLF001
    original = list(registry._entries)  # noqa: SLF001
    original_path = registry._path  # noqa: SLF001
    staged = tmp_path / "registry.json"
    staged.write_text(json.dumps(original), encoding="utf-8")
    registry._path = staged  # noqa: SLF001

    def _inject(symbol: str, feature_count: int, row_count: int, *, timeframe: str = "12h") -> Dict[str, Any]:
        manifest = tmp_path / f"{symbol}_{feature_count}" / "feature_manifest.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"total_features": feature_count, "row_count": row_count}), encoding="utf-8")
        entry = {"symbol": symbol, "timeframe": timeframe, "config_hash": f"l1b{feature_count}",
                 "feature_count": feature_count, "row_count": row_count,
                 "hdf5_relative_path": str(manifest), "last_generated_at": 1_900_000_000}
        registry._entries = list(registry._entries) + [entry]  # noqa: SLF001
        staged.write_text(json.dumps(registry._entries), encoding="utf-8")  # noqa: SLF001
        return entry

    yield _inject
    registry._entries = original  # noqa: SLF001
    registry._path = original_path  # noqa: SLF001


@pytest.mark.limit_rows(ROW_CONFIG_30)
def test_fixed_feature_cap_setting_removed() -> None:
    from api.core.config import Settings

    # 只看欄位名，不印 settings 物件（其 repr 含交易所金鑰）
    assert "ic_analysis_max_features" not in set(Settings.model_fields)


@pytest.mark.limit_rows(ROW_ROUTE_87, ROW_ROUTE_89)
def test_over_old_cap_run_creates_task_when_budget_fits(budget, inject_run) -> None:
    # 准入只看估算峰值對預算（不看固定欄數）：預算足（注入 1 TiB）⇒ 越舊界 run 建立任務
    budget.update(available_bytes=1024 * GiB, budget_bytes=1024 * GiB)
    e = inject_run("BTCUSDT", OVER_OLD_CAP_FEATURES, OVER_OLD_CAP_ROWS)
    before = _task_count()
    r = client.post(f"{API}/analyze", json={"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": e["config_hash"]})
    assert r.status_code == 200, r.text
    assert _task_count() == before + 1


@pytest.mark.limit_rows(ROW_ROUTE_87, ROW_ROUTE_89)
def test_need_exceeds_budget_is_400_with_need_have_and_no_task(budget, inject_run) -> None:
    from momentum.factories import ic_report_reason

    budget.update(available_bytes=1 * GiB, budget_bytes=1 * GiB)
    e = inject_run("BTCUSDT", OVER_OLD_CAP_FEATURES, OVER_OLD_CAP_ROWS)
    before = _task_count()
    r = client.post(f"{API}/analyze", json={"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": e["config_hash"]})
    assert r.status_code == 400, r.text
    d = r.json()["detail"]
    assert d["reason"] == ic_report_reason("analysis_rejected") == "memory_need_exceeds_budget"
    assert d["have_bytes"] == 1 * GiB and d["need_bytes"] > d["have_bytes"]
    assert d["measurement_source"] == "test"
    assert d["components"] and all({"name", "bytes"} <= set(c) for c in d["components"])
    assert _task_count() == before


@pytest.mark.limit_rows(ROW_ROUTE_87, ROW_ROUTE_89)
def test_queued_when_reservation_blocks_reports_pending_with_wait_reason(budget, inject_run) -> None:
    budget.update(available_bytes=8 * GiB, budget_bytes=8 * GiB)
    admission = svc_mod.ic_analysis_service._admission  # noqa: SLF001
    assert admission.request("holder", planned_bytes=8 * GiB - 1) == "admitted"
    task_id = None
    try:
        # 小 run（估算遠小於預算）：可准但保留量被占 ⇒ 排隊（降並行），不拒
        e = inject_run("BTCUSDT", 1_348, OVER_OLD_CAP_ROWS)
        r = client.post(f"{API}/analyze", json={"symbol": "BTCUSDT", "timeframe": "12h", "config_hash": e["config_hash"]})
        assert r.status_code == 200, r.text
        task_id = r.json()["task_id"]
        st = client.get(f"{API}/task/{task_id}").json()
        assert st["status"] == "pending"
        assert 0 < st["wait_reason"]["need_bytes"] <= 8 * GiB
        assert st["wait_reason"]["have_bytes"] < st["wait_reason"]["need_bytes"]
        assert st["wait_reason"]["measurement_source"] == "test"
    finally:
        if task_id:
            client.post(f"{API}/task/{task_id}/cancel")
        admission.release("holder")


@pytest.mark.requires_kline
@pytest.mark.limit_rows(ROW_ROUTE_87, ROW_ROUTE_89)
def test_full_analysis_goes_through_same_admission(budget, tmp_path) -> None:
    # /full-analysis 之載入來源為 features_path（檔頭估算）；預算極小 ⇒ 400 need／have、不建任務
    path = _real_features_h5(tmp_path)
    budget.update(available_bytes=1, budget_bytes=1)
    before = _task_count()
    r = client.post(f"{API}/full-analysis", json={"features_path": str(path), "labels_path": str(tmp_path / "l.h5")})
    assert r.status_code == 400, r.text
    d = r.json()["detail"]
    assert d["reason"] == "memory_need_exceeds_budget" and d["need_bytes"] > d["have_bytes"] == 1
    assert _task_count() == before


def _real_features_h5(tmp_path: Path) -> Path:
    """真實 kline 衍生之小 IC 交接 h5（BTCUSDT 1h 末 600 根之對數報酬兩欄）。"""
    import h5py
    import numpy as np
    import pandas as pd

    from momentum.core.h5_feature_precision import write_feature_datasets
    from momentum.factories import stamp_h5_feature_naming_version

    with h5py.File(REPO / "data_cache" / "feature_klines" / "kline_cache.h5", "r") as f:
        data = f["BTCUSDT/1h/data"][-600:]
    close = pd.Series(data["close"].astype("float64"))
    frame = pd.DataFrame({"logret1": np.log(close).diff().fillna(0.0), "logret5": np.log(close).diff(5).fillna(0.0)})
    path = tmp_path / "features.h5"
    with h5py.File(path, "w") as f:
        stamp_h5_feature_naming_version(f.attrs)
        write_feature_datasets(f.create_group("data"), frame)
    return path


@pytest.mark.limit_rows(ROW_ROUTE_453)
def test_full_analysis_event_batch_fail_closed_retained(budget) -> None:
    # 便宜之功能拒收先於記憶體准入：預算極小時仍回事件批 fail-closed，而非 need／have
    budget.update(available_bytes=1, budget_bytes=1)
    r = client.post(f"{API}/full-analysis", json={"symbol": "BTCUSDT", "timeframe": "12h", "labels_path": "labels.h5",
                                                  "event_import_id": "evt-x"})
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["kind"] == "event_batch_not_supported_on_full_analysis"


def test_contract_reason_membership() -> None:
    from momentum.factories import ic_report_reasons

    reasons = ic_report_reasons("analysis_rejected")
    assert "memory_need_exceeds_budget" in reasons
    assert "feature_count_exceeds_cap" not in reasons


class _DeepSpy:
    """深度分析計算端之監看：記錄實際收到之 selected_features，收到即觸發事件（不以牆鐘輪詢）。"""

    def __init__(self) -> None:
        self.selected: List[str] = []
        self.called = threading.Event()

    def run_deep_analysis(self, selected, override=None, progress_callback=None, cancel=None, top_n=None, **_: Any):
        self.selected = list(selected or [])
        self.called.set()
        return {"modules": {}}


@pytest.mark.limit_rows(ROW_FILTER_99)
def test_501_selected_features_reach_deep_analysis_consumer(budget) -> None:
    spy = _DeepSpy()
    names = [f"feat_{i:04d}" for i in range(501)]
    task_id = "l1b-deep-501"
    svc = svc_mod.ic_analysis_service
    with svc._lock:  # noqa: SLF001
        svc._tasks[task_id] = {"task_id": task_id, "status": "completed", "progress": 1.0,  # noqa: SLF001
                               "analyzer": spy, "result": {}, "created_at": "x", "workload": _workload(600, 501)}
    try:
        r = client.post(f"{API}/deep-analysis/{task_id}", json={"selected_features": names, "top_n": 501})
        assert r.status_code == 200, r.text
        spy.called.wait()
        assert spy.selected == names
    finally:
        with svc._lock:  # noqa: SLF001
            svc._tasks.pop(task_id, None)  # noqa: SLF001


def _workload(rows: int, cols: int) -> Dict[str, Any]:
    """任務紀錄之 `workload`（准入估算之封閉輸入，與 `memory_budget` 分支 IC.analysis 同鍵）。"""
    return {"sources": [{"rows": rows, "n_f32": cols, "n_f64": 0}], "cross_sectional": False,
            "windows": [21, 63, 126], "icir_window": 63, "stride": 1, "method": "spearman",
            "preprocess": "pit_expanding", "decay_horizons": 7, "redundancy_cols": cols,
            "deep_modules": [], "event_cells": 0}


# ---------------------------------------------------------------- D1：apply-transforms 消費端（審查 r166 CODEX-R166-P1-01）

@pytest.mark.requires_kline
@pytest.mark.limit_rows(ROW_FILTER_99)
def test_501_selected_features_reach_apply_transforms_consumer(monkeypatch, tmp_path) -> None:
    """真實 kline 衍生 600 欄（各滯後之對數報酬）經公開端點 /apply-transforms：transform 消費點實收 501 欄、順序不變、
    輸出欄集合＝該 501 欄。載入點與 run 身分以注入對齊（run 身分檢查為既有邏輯）；輸出寫於暫存目錄。"""
    import h5py
    import numpy as np
    import pandas as pd

    kline = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
    with h5py.File(kline, "r") as f:
        data = f["BTCUSDT/1h/data"][-1200:]
    close = pd.Series(data["close"].astype("float64"),
                      index=pd.to_datetime(data["timestamp"].astype("int64"), unit="s", utc=True))
    logc = np.log(close)
    # 特徵庫原生存放為 float32（產品載入端拒 float64 原生輸出）
    frame = pd.DataFrame({f"logret_lag_{k:04d}": logc.diff(k) for k in range(1, 601)}).astype("float32")
    names = list(frame.columns[:501])

    svc = svc_mod.ic_analysis_service
    identity = {"run": "l1b-apply-501"}

    class _Ident:
        def to_dict(self) -> Dict[str, Any]:
            return dict(identity)

    monkeypatch.setattr(svc, "_load_features_for_transforms", lambda *a, **k: (frame, _Ident()))
    monkeypatch.chdir(tmp_path)
    task_id = "l1b-apply-501"
    from api.services.ic_analysis_service import FF_RUN_IDENTITY_KEY

    with svc._lock:  # noqa: SLF001
        svc._tasks[task_id] = {"task_id": task_id, "status": "completed", "progress": 1.0, "created_at": "x",  # noqa: SLF001
                               "req_symbol": "BTCUSDT", "req_timeframe": "1h", "req_features_path": None,
                               "req_config_hash": "h", "result": {"metadata": {FF_RUN_IDENTITY_KEY: identity}}}
    try:
        r = client.post(f"{API}/apply-transforms/{task_id}",
                        json={"selected_features": names, "rank": True, "zscore": False, "gaussian": False})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["selected_feature_count"] == 501 and body["output_cols"] == 501
        out = pd.read_hdf(tmp_path / body["output_path"] if not Path(body["output_path"]).is_absolute()
                          else body["output_path"], key="features")
        assert list(out.columns) == names
    finally:
        with svc._lock:  # noqa: SLF001
            svc._tasks.pop(task_id, None)  # noqa: SLF001


# ---------------------------------------------------------------- D2：准入生命週期（審查 r166 CODEX-R166-P1-02）


class _BlockingAnalyzer:
    """可控 worker：analyze 於 `gate` 放行前阻塞；`fail` 時拋錯。以事件觀察啟動與退出（不以牆鐘輪詢）。"""

    def __init__(self, fail: bool = False) -> None:
        self.gate = threading.Event()
        self.started = threading.Event()
        self.exited = threading.Event()
        self.fail = fail

    def analyze(self, *_: Any, **__: Any) -> Dict[str, Any]:
        self.started.set()
        try:
            self.gate.wait()
            if self.fail:
                raise RuntimeError("l1b-worker-failure")
            return {"metadata": {}}
        finally:
            self.exited.set()


@pytest.fixture
def lifecycle(monkeypatch: pytest.MonkeyPatch, budget, tmp_path: Path):
    """注入可控 analyzer、包住准入釋放（記錄每任務釋放次數並觸發事件）、寫真實 kline 衍生之小特徵檔。"""
    import h5py
    import numpy as np
    import pandas as pd

    from momentum.core.h5_feature_precision import write_feature_datasets
    from momentum.factories import stamp_h5_feature_naming_version

    svc = svc_mod.ic_analysis_service
    queue: List[_BlockingAnalyzer] = []
    monkeypatch.setattr(svc_mod, "create_ic_analyzer", lambda *_a, **_k: queue.pop(0))
    admission = svc._admission  # noqa: SLF001
    real_release = admission.release
    released: Dict[str, List[int]] = {}
    events: Dict[str, threading.Event] = {}

    def _release(reservation_id: str) -> None:
        # 保留 id＝`<task_id>#<隨機>`（每次准入唯一；審碼 r168 CODEX-R168-P1-03）⇒ 依任務彙總釋放次數
        task_id = reservation_id.split("#", 1)[0]
        released.setdefault(task_id, []).append(1)
        real_release(reservation_id)
        events.setdefault(task_id, threading.Event()).set()

    monkeypatch.setattr(admission, "release", _release)
    kline = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
    with h5py.File(kline, "r") as f:
        data = f["BTCUSDT/1h/data"][-600:]
    close = pd.Series(data["close"].astype("float64"))
    frame = pd.DataFrame({"logret1": np.log(close).diff().fillna(0.0), "logret5": np.log(close).diff(5).fillna(0.0)})
    path = tmp_path / "features.h5"
    with h5py.File(path, "w") as f:
        stamp_h5_feature_naming_version(f.attrs)
        write_feature_datasets(f.create_group("data"), frame)

    started: List[_BlockingAnalyzer] = []
    task_ids: List[str] = []

    def _start(analyzer: _BlockingAnalyzer) -> str:
        queue.append(analyzer)
        started.append(analyzer)
        r = client.post(f"{API}/full-analysis", json={"features_path": str(path), "labels_path": str(tmp_path / "l.h5")})
        assert r.status_code == 200, r.text
        task_ids.append(r.json()["task_id"])
        return r.json()["task_id"]

    def _released_event(task_id: str) -> threading.Event:
        return events.setdefault(task_id, threading.Event())

    def _rid(task_id: str) -> str:
        return svc._tasks[task_id]["reservation_id"]  # noqa: SLF001

    yield {"start": _start, "released": released, "released_event": _released_event, "admission": admission,
           "rid": _rid, "state": lambda task_id: admission.state(_rid(task_id))}
    # 收尾（審查 r167 CODEX-R167-P2-01）：斷言失敗時仍放行全部阻塞 worker、釋放測試自建之保留量、移除本測試建立之任務，
    # 不使預期可證偽之失敗汙染後續案例或程序退出
    for analyzer in started:
        analyzer.gate.set()
    real_release("holder")
    for task_id in task_ids:
        rid = (svc._tasks.get(task_id) or {}).get("reservation_id")  # noqa: SLF001
        if rid:
            real_release(rid)
    with svc._lock:  # noqa: SLF001
        for task_id in task_ids:
            svc._tasks.pop(task_id, None)  # noqa: SLF001


@pytest.mark.requires_kline
@pytest.mark.limit_rows(ROW_ROUTE_87, ROW_ROUTE_89)
def test_cancel_running_holds_reservation_until_worker_exits(lifecycle) -> None:
    a = _BlockingAnalyzer()
    tid = lifecycle["start"](a)
    a.started.wait()
    r = client.post(f"{API}/task/{tid}/cancel")
    assert r.status_code == 200, r.text
    assert lifecycle["state"](tid) == "admitted", "worker 未退出前不得釋放保留量"
    assert lifecycle["released"].get(tid) is None
    a.gate.set()
    lifecycle["released_event"](tid).wait()
    assert a.exited.is_set()
    assert lifecycle["released"][tid] == [1]
    assert client.get(f"{API}/task/{tid}").json()["status"] == "cancelled"


@pytest.mark.requires_kline
@pytest.mark.limit_rows(ROW_ROUTE_87, ROW_ROUTE_89)
def test_worker_success_completes_and_releases_exactly_once(lifecycle) -> None:
    # 審查 r167 CODEX-R167-P1-01：成功分支之終態與恰一次釋放（錯標 failed 或成功路徑重複 release 皆紅）
    a = _BlockingAnalyzer()
    before = lifecycle["admission"].reserved_bytes()
    tid = lifecycle["start"](a)
    a.started.wait()
    assert lifecycle["state"](tid) == "admitted"
    assert lifecycle["admission"].reserved_bytes() > before
    a.gate.set()
    lifecycle["released_event"](tid).wait()
    assert a.exited.is_set()
    assert lifecycle["released"][tid] == [1]
    assert lifecycle["admission"].reserved_bytes() == before
    assert client.get(f"{API}/task/{tid}").json()["status"] == "completed"


@pytest.mark.requires_kline
@pytest.mark.limit_rows(ROW_ROUTE_87, ROW_ROUTE_89)
def test_worker_failure_releases_exactly_once(lifecycle) -> None:
    a = _BlockingAnalyzer(fail=True)
    a.gate.set()
    tid = lifecycle["start"](a)
    lifecycle["released_event"](tid).wait()
    assert lifecycle["released"][tid] == [1]
    assert client.get(f"{API}/task/{tid}").json()["status"] == "failed"
    before = lifecycle["admission"].reserved_bytes()
    lifecycle["admission"].release(lifecycle["rid"](tid))  # 重複完成通知
    assert lifecycle["admission"].reserved_bytes() == before


@pytest.mark.requires_kline
@pytest.mark.limit_rows(ROW_ROUTE_87, ROW_ROUTE_89)
def test_background_start_failure_leaks_no_reservation(lifecycle, monkeypatch) -> None:
    svc = svc_mod.ic_analysis_service
    before = lifecycle["admission"].reserved_bytes()

    def _boom(*_: Any, **__: Any) -> None:
        raise RuntimeError("l1b-start-failure")

    monkeypatch.setattr(svc, "_start_background_coroutine", _boom)
    a = _BlockingAnalyzer()
    with pytest.raises(AssertionError):
        lifecycle["start"](a)
    assert lifecycle["admission"].reserved_bytes() == before


@pytest.mark.requires_kline
@pytest.mark.limit_rows(ROW_ROUTE_87, ROW_ROUTE_89)
def test_queued_task_starts_after_release_with_fresh_snapshot(lifecycle, budget) -> None:
    calls = {"n": 0}
    from momentum.factories import get_memory_budget

    mb = get_memory_budget()
    inner = mb.admission_snapshot

    def _counting() -> Dict[str, Any]:
        calls["n"] += 1
        return inner()

    mb.admission_snapshot = _counting  # budget fixture 之 monkeypatch 於測試結束還原原屬性
    budget.update(available_bytes=8 * GiB, budget_bytes=8 * GiB)
    admission = lifecycle["admission"]
    assert admission.request("holder", planned_bytes=8 * GiB - 1) == "admitted"
    b = _BlockingAnalyzer()
    b.gate.set()
    tid = lifecycle["start"](b)
    assert client.get(f"{API}/task/{tid}").json()["status"] == "pending"
    n_before = calls["n"]
    admission.release("holder")
    b.started.wait()
    assert calls["n"] > n_before, "出隊須重取即時快照"
    lifecycle["released_event"](tid).wait()


@pytest.mark.requires_kline
@pytest.mark.limit_rows(ROW_ROUTE_87, ROW_ROUTE_89)
def test_cancel_queued_task_never_starts(lifecycle, budget) -> None:
    budget.update(available_bytes=8 * GiB, budget_bytes=8 * GiB)
    admission = lifecycle["admission"]
    assert admission.request("holder", planned_bytes=8 * GiB - 1) == "admitted"
    b = _BlockingAnalyzer()
    tid = lifecycle["start"](b)
    assert client.get(f"{API}/task/{tid}").json()["status"] == "pending"
    assert client.post(f"{API}/task/{tid}/cancel").status_code == 200
    admission.release("holder")
    assert lifecycle["state"](tid) == "cancelled"
    assert not b.started.is_set()
    assert client.get(f"{API}/task/{tid}").json()["status"] == "cancelled"


@pytest.mark.limit_rows(ROW_ROUTE_87, ROW_ROUTE_89)
def test_deep_reentry_goes_through_admission(budget) -> None:
    budget.update(available_bytes=1, budget_bytes=1)
    spy = _DeepSpy()
    task_id = "l1b-deep-reentry"
    svc = svc_mod.ic_analysis_service
    with svc._lock:  # noqa: SLF001
        svc._tasks[task_id] = {"task_id": task_id, "status": "completed", "progress": 1.0,  # noqa: SLF001
                               "analyzer": spy, "result": {}, "created_at": "x", "workload": _workload(600, 501)}
    try:
        r = client.post(f"{API}/deep-analysis/{task_id}", json={"top_n": 30, "modules": {"factor_centrality": True}})
        assert r.status_code == 400, r.text
        d = r.json()["detail"]
        assert d["reason"] == "memory_need_exceeds_budget" and d["need_bytes"] > d["have_bytes"] == 1
        assert not spy.called.is_set()
    finally:
        with svc._lock:  # noqa: SLF001
            svc._tasks.pop(task_id, None)  # noqa: SLF001


# ---------------------------------------------------------------- 審碼 r168 修補之驗收

class _BlockingDeep:
    """深度分析計算端之可控替身：`gate` 放行前阻塞，以事件觀察啟動（不以牆鐘輪詢）。"""

    def __init__(self) -> None:
        self.gate = threading.Event()
        self.started = threading.Event()

    def run_deep_analysis(self, *_: Any, **__: Any) -> Dict[str, Any]:
        self.started.set()
        self.gate.wait()
        return {"modules": {}}


def _release_events(monkeypatch: pytest.MonkeyPatch) -> Dict[str, threading.Event]:
    """包住（conftest 每測試新建之）准入控制器之 release：每個保留 id 一個事件。"""
    admission = svc_mod.ic_analysis_service._admission  # noqa: SLF001
    real = admission.release
    events: Dict[str, threading.Event] = {}

    def _release(reservation_id: str) -> None:
        real(reservation_id)
        events.setdefault(reservation_id, threading.Event()).set()

    monkeypatch.setattr(admission, "release", _release)
    return events


def test_early_admission_before_queue_registration_still_launches() -> None:
    # CODEX-R168-P1-01：出隊／拒收回呼早於排隊登記到達 ⇒ 登記時即處理，不永久 pending
    from momentum.factories import ic_memory_need_error_type

    svc = svc_mod.ic_analysis_service
    with svc._lock:  # noqa: SLF001
        svc._tasks["l1b-early"] = {"task_id": "l1b-early", "status": "pending"}  # noqa: SLF001
        svc._tasks["l1b-early-rej"] = {"task_id": "l1b-early-rej", "status": "pending"}  # noqa: SLF001
    launched: List[str] = []
    try:
        svc._on_admitted("l1b-early#x")  # noqa: SLF001
        svc._launch_or_queue("l1b-early", "l1b-early#x", "queued", lambda: launched.append("ok"))  # noqa: SLF001
        assert launched == ["ok"]
        assert svc._tasks["l1b-early"]["status"] == "running"  # noqa: SLF001
        svc._on_rejected("l1b-early-rej#y", ic_memory_need_error_type()(2 * GiB, 1 * GiB, [], "test"))  # noqa: SLF001
        svc._launch_or_queue("l1b-early-rej", "l1b-early-rej#y", "queued", lambda: launched.append("bad"))  # noqa: SLF001
        assert launched == ["ok"]
        assert svc._tasks["l1b-early-rej"]["status"] == "failed"  # noqa: SLF001
        assert "需要 2.00 GB" in svc._tasks["l1b-early-rej"]["error"]  # noqa: SLF001
    finally:
        with svc._lock:  # noqa: SLF001
            svc._tasks.pop("l1b-early", None)  # noqa: SLF001
            svc._tasks.pop("l1b-early-rej", None)  # noqa: SLF001


def test_deep_cancel_late_result_not_overwritten(budget, monkeypatch) -> None:
    # CODEX-R168-P1-02：深度分析執行中取消 ⇒ 晚到結果不覆寫為 completed
    events = _release_events(monkeypatch)
    deep = _BlockingDeep()
    task_id = "l1b-deep-cancel"
    svc = svc_mod.ic_analysis_service
    with svc._lock:  # noqa: SLF001
        svc._tasks[task_id] = {"task_id": task_id, "status": "completed", "progress": 1.0,  # noqa: SLF001
                               "analyzer": deep, "result": {}, "created_at": "x", "workload": _workload(600, 30)}
    try:
        r = client.post(f"{API}/deep-analysis/{task_id}", json={"top_n": 30})
        assert r.status_code == 200, r.text
        deep.started.wait()
        rid = svc._tasks[task_id]["reservation_id"]  # noqa: SLF001
        assert client.post(f"{API}/task/{task_id}/cancel").status_code == 200
        deep.gate.set()
        events.setdefault(rid, threading.Event()).wait()
        st = client.get(f"{API}/task/{task_id}").json()
        assert st["status"] == "cancelled", st
        assert svc._tasks[task_id].get("deep_analysis_result") is None  # noqa: SLF001
    finally:
        deep.gate.set()
        with svc._lock:  # noqa: SLF001
            svc._tasks.pop(task_id, None)  # noqa: SLF001


class _TwoModuleDeep:
    """兩個模組之深度分析替身：第一模組後經 progress_callback 回報（安全點），再跑第二模組。"""

    def __init__(self) -> None:
        self.gate = threading.Event()
        self.started = threading.Event()
        self.second_module_ran = False

    def run_deep_analysis(self, selected, override=None, progress_callback=None, cancel=None, top_n=None, **_: Any):
        self.started.set()
        self.gate.wait()
        progress_callback({"stage": "deep_analysis", "module_name": "m1", "progress": 0.5, "message": "m1 done"})
        self.second_module_ran = True
        return {"modules": {}}


def test_deep_cancel_takes_effect_at_progress_safe_point(budget, monkeypatch) -> None:
    # 審碼 r169 CODEX-R169-P1-01／GROK-R169-P1-01：取消受理後於下一個進度安全點停，不再跑後續模組
    events = _release_events(monkeypatch)
    deep = _TwoModuleDeep()
    task_id = "l1b-deep-safepoint"
    svc = svc_mod.ic_analysis_service
    with svc._lock:  # noqa: SLF001
        svc._tasks[task_id] = {"task_id": task_id, "status": "completed", "progress": 1.0,  # noqa: SLF001
                               "analyzer": deep, "result": {}, "created_at": "x", "workload": _workload(600, 30)}
    try:
        assert client.post(f"{API}/deep-analysis/{task_id}", json={"top_n": 30}).status_code == 200
        deep.started.wait()
        rid = svc._tasks[task_id]["reservation_id"]  # noqa: SLF001
        assert client.post(f"{API}/task/{task_id}/cancel").status_code == 200
        deep.gate.set()
        events.setdefault(rid, threading.Event()).wait()
        assert deep.second_module_ran is False, "取消受理後仍跑了後續模組"
        assert client.get(f"{API}/task/{task_id}").json()["status"] == "cancelled"
    finally:
        deep.gate.set()
        with svc._lock:  # noqa: SLF001
            svc._tasks.pop(task_id, None)  # noqa: SLF001


def test_deep_reentry_gets_distinct_reservation(budget, monkeypatch) -> None:
    # CODEX-R168-P1-03／GROK-R168-P1-01：主任務 worker 尚未釋放時深度分析再入 ⇒ 另一保留 id，互不覆寫、互不誤放
    events = _release_events(monkeypatch)
    admission = svc_mod.ic_analysis_service._admission  # noqa: SLF001
    task_id = "l1b-deep-distinct"
    main_rid = f"{task_id}#main"
    assert admission.request(main_rid, planned_bytes=1 * GiB) == "admitted"
    deep = _BlockingDeep()
    svc = svc_mod.ic_analysis_service
    with svc._lock:  # noqa: SLF001
        svc._tasks[task_id] = {"task_id": task_id, "status": "completed", "progress": 1.0,  # noqa: SLF001
                               "analyzer": deep, "result": {}, "created_at": "x", "workload": _workload(600, 30),
                               "reservation_id": main_rid}
    try:
        r = client.post(f"{API}/deep-analysis/{task_id}", json={"top_n": 30})
        assert r.status_code == 200, r.text
        deep.started.wait()
        # 狀態檢查與轉態原子：第一個深度分析執行中，第二個請求不得並行啟動（共用同一 analyzer）
        r2 = client.post(f"{API}/deep-analysis/{task_id}", json={"top_n": 30})
        assert r2.status_code == 400 and "not ready" in r2.text, r2.text
        deep_rid = svc._tasks[task_id]["reservation_id"]  # noqa: SLF001
        assert deep_rid != main_rid and deep_rid.startswith(f"{task_id}#")
        deep_planned = svc._tasks[task_id]["planned_bytes"]  # noqa: SLF001
        admission.release(main_rid)  # 主任務 worker 結束
        assert admission.state(deep_rid) == "admitted", "主任務釋放誤放了深度分析之保留量"
        assert admission.reserved_bytes() == deep_planned
        deep.gate.set()
        events.setdefault(deep_rid, threading.Event()).wait()
        assert admission.reserved_bytes() == 0
    finally:
        deep.gate.set()
        with svc._lock:  # noqa: SLF001
            svc._tasks.pop(task_id, None)  # noqa: SLF001

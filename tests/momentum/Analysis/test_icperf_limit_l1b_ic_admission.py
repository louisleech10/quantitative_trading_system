"""ICPERF SPEC v5.87 Task 0.6 (h) ⑤ IC 分析啟動准入（L1b；諮詢 r165 收斂檔 C1–C5）之 momentum 層驗收。

取代固定欄數上限 `ic_analysis_max_features`（L0 列 `api/core/config.py:30`、`api/routes/ic_analysis.py:87`／`:89`，
路由層列↔測試對應於 `tests/api/test_icperf_limit_l1b_ic_admission_route.py`）。本檔驗：
- C2：特徵數只讀檔頭並併入 `features_f64`（真實 kline 寫出之 IC 交接 h5，收盤價非 float32 無損 ⇒ 落 f64）。
- C1：`memory_budget` 分支 `IC.analysis` 之估算為各路徑成分之保守上界，依封閉輸入集合單調（滾動窗數、f64、
  橫截面聯合、深度模組、衰減、冗餘）；事件網格逐格串行不乘格數。
- C3：`ICAdmissionController` 同鎖准入、排隊（等待原因）、出隊重查、釋放、取消、need／have 拒收。
- C5：可用量來源 darwin＝memory_budget 即時快照、非 darwin＝psutil。
估算係數之校準與驗證點屬重型量測（薄量測入口＋全程 Physical footprint，收據另列），本檔只驗結構與判定，不驗係數值。
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[3]
KLINE_CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"

GiB = 1 << 30


def _real_kline(rows: int = 600, symbol: str = "BTCUSDT", tf: str = "1h") -> pd.DataFrame:
    import h5py

    assert KLINE_CACHE.is_file(), f"真實 kline 不存在：{KLINE_CACHE}"
    with h5py.File(KLINE_CACHE, "r") as f:
        data = f[f"{symbol}/{tf}/data"][-rows:]
    assert len(data) == rows, f"{symbol}/{tf} 只有 {len(data)} 根 < {rows}"
    idx = pd.to_datetime(data["timestamp"].astype("int64"), unit="s", utc=True)
    return pd.DataFrame({k: data[k].astype("float64") for k in ("close", "volume", "quote_volume")}, index=idx)


def _write_handoff_h5(path: Path, frame: pd.DataFrame) -> np.ndarray:
    """寫 IC 交接 h5；回傳非 float32 無損欄之全序索引（`write_feature_datasets` 之回傳）。"""
    import h5py

    from momentum.core.h5_feature_precision import write_feature_datasets
    from momentum.factories import stamp_h5_feature_naming_version

    with h5py.File(path, "w") as f:
        stamp_h5_feature_naming_version(f.attrs)
        grp = f.create_group("data")
        lossy_idx = write_feature_datasets(grp, frame)
    return np.asarray(lossy_idx, dtype=np.int64)


# ---------------------------------------------------------------- C2：特徵數併入 features_f64（只讀檔頭）

@pytest.mark.requires_kline
def test_feature_count_from_file_includes_f64_columns(tmp_path: Path) -> None:
    from momentum.factories import feature_count_from_features_file

    k = _real_kline(600)
    frame = pd.DataFrame({"log_close": np.log(k["close"]), "log_volume": np.log1p(k["volume"]),
                          "ret1": k["close"].pct_change().fillna(0.0)})
    path = tmp_path / "handoff.h5"
    n_f64 = len(_write_handoff_h5(path, frame))
    assert 1 <= n_f64 < frame.shape[1], "前提：對數收盤價於 float32 併值落 f64、且另有無損欄（否則本測試無法鑑別）"
    assert feature_count_from_features_file(str(path)) == frame.shape[1]


@pytest.mark.requires_kline
def test_planned_workload_from_file_reads_header_only(tmp_path: Path) -> None:
    from momentum.factories import ic_workload_from_features_file

    k = _real_kline(600)
    frame = pd.DataFrame({"log_close": np.log(k["close"]), "ret1": k["close"].pct_change().fillna(0.0)})
    path = tmp_path / "handoff.h5"
    n_f64 = len(_write_handoff_h5(path, frame))
    assert n_f64 >= 1
    src = ic_workload_from_features_file(str(path))
    assert src == {"rows": 600, "n_f32": frame.shape[1] - n_f64, "n_f64": n_f64}


# ---------------------------------------------------------------- C1：IC.analysis 估算（保守上界、封閉輸入、單調）

def _params(**over: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "sources": [{"rows": 8761, "n_f32": 1000, "n_f64": 0}],
        "cross_sectional": False,
        "windows": [21, 63, 126],
        "icir_window": 63,
        "stride": 1,
        "method": "spearman",
        "preprocess": "pit_expanding",
        "decay_horizons": 7,
        "redundancy_cols": 1000,
        "deep_modules": [],
        "event_cells": 0,
    }
    base.update(over)
    return base


def _planned(params: Dict[str, Any]) -> int:
    from momentum.factories import get_memory_budget

    budget = get_memory_budget()
    return int(budget.planned_bytes(budget.estimate("IC.analysis", params)))


def test_ic_analysis_branch_registered() -> None:
    from momentum.factories import get_memory_budget

    assert "IC.analysis" in get_memory_budget().BRANCH_TABLE


def test_estimate_lower_bound_is_full_float64_matrix() -> None:
    # 計算端 `ic_engine.py:651` 至少一份 float64 全矩陣（列 × 欄 × 8）＋讀入矩陣；保守上界不得低於此
    p = _params()
    rows, cols = 8761, 1000
    assert _planned(p) >= rows * cols * 8 + rows * cols * 4


@pytest.mark.parametrize("key,lo,hi", [
    ("windows", [21], [21, 63, 126]),
    ("decay_horizons", 1, 7),
    ("redundancy_cols", 10, 1000),
    ("deep_modules", [], ["factor_centrality", "marginal_ic"]),
])
def test_estimate_monotone_in_closed_inputs(key: str, lo: Any, hi: Any) -> None:
    assert _planned(_params(**{key: hi})) > _planned(_params(**{key: lo}))


def test_estimate_counts_f64_columns_wider() -> None:
    all32 = _params(sources=[{"rows": 8761, "n_f32": 1000, "n_f64": 0}])
    mixed = _params(sources=[{"rows": 8761, "n_f32": 900, "n_f64": 100}])
    assert _planned(mixed) > _planned(all32)


def test_estimate_cross_sectional_is_union_not_max() -> None:
    one = _params(sources=[{"rows": 8761, "n_f32": 1000, "n_f64": 0}], cross_sectional=True)
    two = _params(sources=[{"rows": 8761, "n_f32": 1000, "n_f64": 0}] * 2, cross_sectional=True)
    assert _planned(two) > _planned(one)


def test_estimate_event_grid_is_serial_not_multiplied() -> None:
    one = _planned(_params(event_cells=1))
    many = _planned(_params(event_cells=50))
    assert many == one, "事件網格逐格串行：同時存活量與格數無關"


def test_estimate_missing_input_rejected() -> None:
    # 審查 r166 GROK-R166-P1-01：先證分支已註冊，再驗缺封閉輸入之拒收（不接受 UnknownBudgetBranchError 充數）
    from momentum.factories import get_memory_budget

    budget = get_memory_budget()
    assert "IC.analysis" in budget.BRANCH_TABLE
    with pytest.raises(ValueError, match="sources"):
        budget.estimate("IC.analysis", {k: v for k, v in _params().items() if k != "sources"})


def test_route_reject_literal_unique_in_regenerated_inventory() -> None:
    # 審查 r166 GROK-R166-P1-02（部分採納）：:89 改寫為不同字面後，重產表中 (api/routes/ic_analysis.py, f1971768…)
    # 恰剩 :453 事件批 fail-closed 一落點且非需修；同檔再現同字面即紅、須另裁定
    import json

    rows = json.loads((REPO / "tests" / "_golden" / "icperf" / "limit_inventory.json").read_text(encoding="utf-8"))["rows"]
    hits = [r for r in rows if r["file"] == "api/routes/ic_analysis.py"
            and r["code_sha256"] == "f1971768baf175f16ff63e47f719cbef67201fee4cb05261190b050012dc8862"]
    assert len(hits) == 1, [r["line"] for r in hits]
    assert hits[0]["needs_fix"] is False


# ---------------------------------------------------------------- C5：可用量來源

def test_admission_snapshot_darwin_uses_memory_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    from momentum.factories import get_memory_budget

    budget = get_memory_budget()
    monkeypatch.setattr(budget.sys, "platform", "darwin")
    monkeypatch.setattr(budget, "sample_vm_snapshot", lambda: "SNAP")
    monkeypatch.setattr(budget, "available_bytes", lambda snap: 3 * GiB if snap == "SNAP" else -1)
    monkeypatch.setattr(budget, "configured_budget_bytes", lambda **_: 6 * GiB)
    snap = budget.admission_snapshot()
    assert snap == {"available_bytes": 3 * GiB, "budget_bytes": 6 * GiB, "source": "darwin_vm_snapshot"}


def test_admission_snapshot_non_darwin_uses_psutil(monkeypatch: pytest.MonkeyPatch) -> None:
    import psutil

    from momentum.factories import get_memory_budget

    budget = get_memory_budget()
    monkeypatch.setattr(budget.sys, "platform", "linux")

    class _VM:
        available = 5 * GiB
        total = 16 * GiB

    monkeypatch.setattr(psutil, "virtual_memory", lambda: _VM())
    snap = budget.admission_snapshot()
    assert snap["source"] == "psutil"
    assert snap["available_bytes"] == 5 * GiB
    assert snap["budget_bytes"] == int(16 * GiB * budget.RATIO_DEFAULT)


# ---------------------------------------------------------------- 審碼 r168 CODEX-R168-P1-04：第 6 段執行期記憶體判定

def test_redundancy_stage_memory_check_reports_need_have(monkeypatch: pytest.MonkeyPatch) -> None:
    """通過欄數於分析前未知 ⇒ 第 6 段建相關矩陣前以已知 n、T 判定；不足 ⇒ need／have，足夠 ⇒ 無作用。"""
    from momentum.Analysis.ic_admission import ICMemoryNeedExceedsBudget
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
    from momentum.factories import get_memory_budget

    n, t = 5000, 8761
    need = n * n * 16 + t * n * 8
    budget = get_memory_budget()
    monkeypatch.setattr(budget, "admission_snapshot",
                        lambda: {"available_bytes": need - 1, "budget_bytes": need, "source": "test"})
    with pytest.raises(ICMemoryNeedExceedsBudget) as ei:
        ICFilterOrchestrator._redundancy_memory_check(n, t)  # noqa: SLF001
    assert (ei.value.need_bytes, ei.value.have_bytes, ei.value.source) == (need, need - 1, "test")
    monkeypatch.setattr(budget, "admission_snapshot",
                        lambda: {"available_bytes": need, "budget_bytes": need, "source": "test"})
    ICFilterOrchestrator._redundancy_memory_check(n, t)  # noqa: SLF001


# ---------------------------------------------------------------- C3：准入控制器

class _Snap:
    def __init__(self, available: int, budget: int) -> None:
        self.available = available
        self.budget = budget

    def __call__(self) -> Dict[str, Any]:
        return {"available_bytes": self.available, "budget_bytes": self.budget, "source": "test"}


def _controller(snap: _Snap):
    from momentum.Analysis.ic_admission import ICAdmissionController

    return ICAdmissionController(snapshot=snap)


def test_admit_when_fits() -> None:
    c = _controller(_Snap(available=4 * GiB, budget=6 * GiB))
    assert c.request("t1", planned_bytes=1 * GiB) == "admitted"


def test_need_exceeds_budget_rejects_with_need_have() -> None:
    from momentum.Analysis.ic_admission import ICMemoryNeedExceedsBudget

    c = _controller(_Snap(available=4 * GiB, budget=6 * GiB))
    with pytest.raises(ICMemoryNeedExceedsBudget) as ei:
        c.request("big", planned_bytes=7 * GiB, components=[{"name": "matrix_f64", "bytes": 7 * GiB}])
    err = ei.value
    assert (err.need_bytes, err.have_bytes, err.source) == (7 * GiB, 6 * GiB, "test")
    assert err.components == [{"name": "matrix_f64", "bytes": 7 * GiB}]


def test_queue_when_running_reservation_blocks_then_admit_on_release() -> None:
    snap = _Snap(available=4 * GiB, budget=6 * GiB)
    c = _controller(snap)
    assert c.request("t1", planned_bytes=3 * GiB) == "admitted"
    # t1 尚未用到其保留量（即時可用量未降）⇒ 可用 4 − 未用保留 3 ＝ 1 < 2 ⇒ 排隊
    assert c.request("t2", planned_bytes=2 * GiB) == "queued"
    assert c.wait_reason("t2")["need_bytes"] == 2 * GiB
    admitted: List[str] = []
    c.on_admit = admitted.append
    c.release("t1")
    assert admitted == ["t2"]
    assert c.state("t2") == "admitted"


def test_dequeue_rechecks_live_available() -> None:
    # 終態任務仍持有之大物件反映於即時可用量：釋放保留量但可用量仍不足 ⇒ 不出隊；
    # 仍有執行中任務 ⇒ 續排隊，已無執行中任務可再釋放 ⇒ 回報 need／have（活性，不無限等待）
    snap = _Snap(available=4 * GiB, budget=6 * GiB)
    c = _controller(snap)
    c.request("t1", planned_bytes=1 * GiB)
    c.request("t0", planned_bytes=2 * GiB)
    assert c.request("t2", planned_bytes=2 * GiB) == "queued"
    snap.available = 1 * GiB  # t1 完成後其 analyzer／結果仍存活
    c.release("t1")
    assert c.state("t2") == "queued", "仍有執行中任務 t0 ⇒ 續排隊"
    rejected: List[tuple] = []
    c.on_reject = lambda tid, err: rejected.append((tid, err.need_bytes, err.have_bytes))
    c.release("t0")
    assert c.state("t2") == "rejected"
    assert rejected == [("t2", 2 * GiB, 1 * GiB)]


def test_no_running_task_and_insufficient_rejects_instead_of_queue() -> None:
    # 無執行中任務時排隊等不到釋放 ⇒ 即拒並回 need／have（have＝即時可用量），不得排隊
    from momentum.Analysis.ic_admission import ICMemoryNeedExceedsBudget

    c = _controller(_Snap(available=1 * GiB, budget=6 * GiB))
    with pytest.raises(ICMemoryNeedExceedsBudget) as ei:
        c.request("t1", planned_bytes=2 * GiB)
    assert (ei.value.need_bytes, ei.value.have_bytes) == (2 * GiB, 1 * GiB)
    assert c.state("t1") == "unknown" and c.reserved_bytes() == 0


def test_cancel_while_queued_removes_from_queue() -> None:
    c = _controller(_Snap(available=4 * GiB, budget=6 * GiB))
    c.request("t1", planned_bytes=3 * GiB)
    assert c.request("t2", planned_bytes=2 * GiB) == "queued"
    c.cancel("t2")
    assert c.state("t2") == "cancelled"
    admitted: List[str] = []
    c.on_admit = admitted.append
    c.release("t1")
    assert admitted == []


def test_release_is_idempotent() -> None:
    c = _controller(_Snap(available=4 * GiB, budget=6 * GiB))
    c.request("t1", planned_bytes=3 * GiB)
    c.release("t1")
    c.release("t1")
    assert c.request("t2", planned_bytes=3 * GiB) == "admitted"


def test_extend_waits_for_release_then_rejects_when_nothing_to_wait() -> None:
    # 審碼 r169 GROK-R169-P1-02：階段額外需求同鎖扣全部保留量；不足有他任務 ⇒ 等釋放（事件），無可等 ⇒ need／have
    from momentum.Analysis.ic_admission import ICMemoryNeedExceedsBudget

    c = _controller(_Snap(available=4 * GiB, budget=6 * GiB))
    assert c.request("a", planned_bytes=2 * GiB) == "admitted"
    assert c.request("b", planned_bytes=1 * GiB) == "admitted"
    done = threading.Event()

    def _stage() -> None:
        c.extend("a", 2 * GiB)  # 可用 4 − 保留 3 ＝ 1 < 2 ⇒ 等 b 釋放
        done.set()

    t = threading.Thread(target=_stage)
    t.start()
    assert not done.is_set()
    c.release("b")
    t.join()
    assert done.is_set() and c.reserved_bytes() == 4 * GiB
    c.shrink("a", 2 * GiB)
    assert c.reserved_bytes() == 2 * GiB
    with pytest.raises(ICMemoryNeedExceedsBudget) as ei:
        c.extend("a", 3 * GiB)  # 可用 4 − 2 ＝ 2 < 3 且無他任務可等
    assert (ei.value.need_bytes, ei.value.have_bytes) == (3 * GiB, 2 * GiB)


def test_extend_mutual_wait_rejects_instead_of_deadlock() -> None:
    # 兩任務同時於階段額外配置互等 ⇒ 後到者即拒（need／have），先到者於後到者之任務釋放後繼續（不死鎖）
    from momentum.Analysis.ic_admission import ICMemoryNeedExceedsBudget

    c = _controller(_Snap(available=4 * GiB, budget=6 * GiB))
    assert c.request("a", planned_bytes=2 * GiB) == "admitted"
    assert c.request("b", planned_bytes=2 * GiB) == "admitted"
    a_waiting = threading.Event()
    a_done = threading.Event()
    orig_wait = c._released.wait  # noqa: SLF001

    def _wait_spy() -> None:
        a_waiting.set()
        orig_wait()

    c._released.wait = _wait_spy  # type: ignore[method-assign]  # noqa: SLF001

    def _a() -> None:
        c.extend("a", 1 * GiB)  # 可用 4 − 保留 4 ＝ 0 < 1 ⇒ 等 b
        a_done.set()

    t = threading.Thread(target=_a)
    t.start()
    a_waiting.wait()
    with pytest.raises(ICMemoryNeedExceedsBudget):
        c.extend("b", 1 * GiB)  # 唯一他任務 a 亦在等待 ⇒ 互等 ⇒ 即拒
    assert not a_done.is_set()
    c.release("b")  # b 之任務因拒收結束 ⇒ 釋放 ⇒ a 繼續
    t.join()
    assert a_done.is_set() and c.reserved_bytes() == 3 * GiB


def test_deep_progress_emitter_does_not_swallow_cancel() -> None:
    # 審碼 r169 CODEX-R169-P1-01：深度進度派發不得以泛用 except 吞掉協作取消
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
    from momentum.core.exceptions import AnalysisCancelled

    def _cb(_payload: Dict[str, Any]) -> None:
        raise AnalysisCancelled("cancelled by user")

    with pytest.raises(AnalysisCancelled):
        ICFilterOrchestrator._emit_deep_progress(None, _cb, {"stage": "deep_analysis"})  # type: ignore[arg-type]


def test_concurrent_requests_are_atomic() -> None:
    c = _controller(_Snap(available=4 * GiB, budget=6 * GiB))
    barrier = threading.Barrier(8)
    results: List[str] = []
    lock = threading.Lock()

    def _go(i: int) -> None:
        barrier.wait()
        r = c.request(f"t{i}", planned_bytes=1 * GiB)
        with lock:
            results.append(r)

    threads = [threading.Thread(target=_go, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count("admitted") == 4 and results.count("queued") == 4

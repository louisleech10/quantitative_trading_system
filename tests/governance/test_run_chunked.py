"""scripts/run_chunked.py：分批、每批新行程跑 pytest 選取（docs/TEST_SELECTION.md §5 過渡工具 6）。"""
from __future__ import annotations

import importlib.util
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pytest

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("run_chunked_t", REPO / "scripts" / "run_chunked.py")
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)  # type: ignore[union-attr]
OVH = rc.PROCESS_OVERHEAD_S


def test_plan_heavy_alone_files_not_split_chunk_boundary() -> None:
    """重型（≥60 秒）各自一批；快速層依檔聚批、同檔不拆；累計估時逾門檻即收批。"""
    dur = {"t/f1.py::a": 100.0, "t/f1.py::b": 5.0, "t/f2.py::c": 5.0, "t/f3.py::d": 5.0, "t/f3.py::e": 5.0}
    sel = list(dur)
    chunks = rc.plan(sel, dur, {}, None, chunk_seconds=12.0, fast_limit=60.0)
    assert [(c["kind"], c["nodeids"]) for c in chunks] == [
        ("heavy", ["t/f1.py::a"]), ("fast", ["t/f1.py::b", "t/f2.py::c"]), ("fast", ["t/f3.py::d", "t/f3.py::e"])]
    # 單檔逾門檻仍整檔一批（共用 fixture 只付一次）
    big = rc.plan(["t/f3.py::d", "t/f3.py::e"], dur, {}, None, chunk_seconds=7.0, fast_limit=60.0)
    assert [c["nodeids"] for c in big] == [["t/f3.py::d", "t/f3.py::e"]]
    assert chunks[1]["estimate_s"] == pytest.approx(10.0 + OVH)


def test_plan_estimate_includes_fixture_gap() -> None:
    """批估時用保守估時：只選部分且用共用 fixture ⇒ 加檔內耗時差距。"""
    dur = {"t/f.py::a": 180.0, "t/f.py::b": 0.1}
    chunks = rc.plan(["t/f.py::b"], dur, {"t/f.py::b": 199.9}, None, chunk_seconds=900.0, fast_limit=60.0)
    assert chunks[0]["estimate_s"] == pytest.approx(200.0 + OVH)


def test_plan_exclusive_when_fixture_rebuild_heavy_or_unknown() -> None:
    """歷史秒數短而本批須重建之共用 fixture 實測成本達重型門檻 ⇒ 獨占；成本未知 ⇒ 保守獨占；整檔皆選之純快速批不
    獨占（審碼 r6）。未知項以逐批實例計。"""
    fx = "module:t/f.py::reference_after"
    dur = {"t/f.py::a": 240.0, "t/f.py::b": 0.02, "t/g.py::c": 1.0}
    shared = {"t/f.py::b": [fx], "t/g.py::c": []}
    measured = rc.plan(["t/f.py::b"], dur, {}, shared, 900.0, 60.0, {fx: 239.0})
    assert measured[0]["kind"] == "fast" and measured[0]["exclusive"] is True
    assert measured[0]["estimate_s"] == pytest.approx(239.02 + OVH) and measured[0]["fixture_cost_unknown"] == []
    unknown = rc.plan(["t/f.py::b"], dur, {}, shared, 900.0, 60.0, None)
    assert unknown[0]["exclusive"] is True and unknown[0]["fixture_cost_unknown"] == ["t/f.py"]
    light = rc.plan(["t/g.py::c"], dur, {}, shared, 900.0, 60.0, None)
    assert light[0]["exclusive"] is False
    split = rc.plan(["t/f.py::a", "t/f.py::b"], dur, {}, None, 900.0, 60.0, None)  # heavy[a]＋fast[b]，各為部分選取
    assert rc.plan_uncertainty(split) == {"unknown": 0, "fixture_cost_unknown": 2}
    # 無通過紀錄之 nodeid（新測試、從未通過；與已知輕量混合亦同）⇒ 耗時未知 ⇒ 獨占（審碼 r7）
    fresh = rc.plan(["t/new.py::x"], {}, {}, None, 900.0, 60.0, None)
    assert fresh[0]["unknown"] == ["t/new.py::x"] and fresh[0]["exclusive"] is True
    mixed = rc.plan(["t/g.py::c", "t/new.py::x"], dur, {}, shared, 900.0, 60.0, None)
    assert len(mixed) == 1 and mixed[0]["exclusive"] is True


def test_run_fast_exclusive_chunk_not_overlapped(tmp_path: Path) -> None:
    """kind＝fast 但標 exclusive 之批（未知耗時或重 fixture）不與他批重疊；兩個非 exclusive 快速批仍可併。"""
    chunks = [{"kind": "fast", "nodeids": ["t/a.py::x"], "estimate_s": 1.0, "exclusive": True},
              {"kind": "fast", "nodeids": ["t/b.py::x"], "estimate_s": 1.0, "exclusive": False},
              {"kind": "fast", "nodeids": ["t/c.py::x"], "estimate_s": 1.0, "exclusive": False}]
    meter = {"now": 0, "max": 0}
    calls: List[int] = []
    s = rc.run(chunks, tmp_path, 3, 3.0, [], runner=_fake({}, calls, hold=0.3, meter=meter), avail=lambda: 64.0)
    assert s["rc"] == 0 and calls[0] == 0 and meter["max"] == 2  # 第 0 批獨跑完才開 1、2（兩者可併）


def test_parse_summary_and_failures() -> None:
    text = ("x\nFAILED tests/a.py::t1 - AssertionError\nERROR tests/b.py::t2 - KeyError\n"
            "= 2 failed, 10 passed, 1 error, 3 skipped, 1 xfailed, 4 deselected, 12 warnings in 5.00s =\n")
    assert rc.parse_summary(text) == {"failed": 2, "passed": 10, "errors": 1, "skipped": 3, "xfailed": 1,
                                      "deselected": 4}
    assert rc.failed_nodeids(text) == ["FAILED tests/a.py::t1", "ERROR tests/b.py::t2"]
    assert rc.parse_summary("no summary") == {}


def _chunks(n: int, size: int = 1) -> List[Dict[str, Any]]:
    return [{"kind": "fast", "nodeids": [f"t/f{i}.py::x{j}" for j in range(size)], "estimate_s": 1.0} for i in range(n)]


def _fake(outcomes: Dict[int, Tuple[str, Any, Any, str]], calls: List[int], hold: float = 0.0,
          meter: Optional[Dict[str, int]] = None) -> Callable[..., Any]:
    lock = threading.Lock()

    def runner(cmd: List[str], log_path: Path, expected_seconds: float):
        i = int(log_path.stem.split("_")[1])
        with lock:
            calls.append(i)
            if meter is not None:
                meter["now"] += 1
                meter["max"] = max(meter["max"], meter["now"])
        time.sleep(hold)
        status, code, cause, text = outcomes.get(i, ("exited", 0, None, "= 1 passed in 1s =\n"))
        log_path.write_text(text, encoding="utf-8")
        with lock:
            if meter is not None:
                meter["now"] -= 1
        assert any(a.startswith("@") for a in cmd) and "-m" in cmd and "pytest" in cmd
        return status, code, cause
    return runner


def test_run_continues_on_failures_stops_on_hang(tmp_path: Path) -> None:
    """測試失敗（rc 1）續跑；卡住（hang）⇒ 不再開新批、整跑 rc 4，未開始者列出（NOCAP：不自動重跑）。"""
    calls: List[int] = []
    out = {0: ("exited", 1, None, "FAILED t/f0.py::x0 - E\n= 1 failed in 1s =\n"), 1: ("stalled", None, "hang", "")}
    s = rc.run(_chunks(4), tmp_path, 1, 3.0, [], runner=_fake(out, calls))
    assert calls == [0, 1] and s["rc"] == 4 and s["not_started"] == [2, 3]
    assert s["chunks"][0]["failures"] == ["FAILED t/f0.py::x0"]


def test_run_stops_on_pytest_internal_rc_and_flags_incomplete(tmp_path: Path) -> None:
    """pytest rc 非 0／1 ⇒ 停開新批、rc 3；摘要條數與該批條數不符 ⇒ incomplete、rc 3。"""
    calls: List[int] = []
    s = rc.run(_chunks(3), tmp_path, 1, 3.0, [], runner=_fake({1: ("exited", 2, None, "")}, calls))
    assert calls == [0, 1] and s["rc"] == 3 and s["not_started"] == [2]
    calls2: List[int] = []
    s2 = rc.run(_chunks(2, size=2), tmp_path, 1, 3.0, [], runner=_fake({}, calls2))  # 每批 2 條、摘要只 1 passed
    assert s2["incomplete"] == [0, 1] and s2["rc"] == 3


def test_run_launch_exception_recorded_and_stops(tmp_path: Path) -> None:
    """某批啟動拋例外 ⇒ 該批記 status＝error（不得消失）、停開新批、rc 3（r5 CODEX-R5-P1-01）。"""
    def boom(cmd: List[str], log_path: Path, expected_seconds: float):
        raise OSError("launch failed")

    s = rc.run(_chunks(2), tmp_path, 1, 3.0, [], runner=boom)
    assert s["rc"] == 3 and s["not_started"] == [1]
    assert [c["status"] for c in s["chunks"]] == ["error"] and s["incomplete"] == [0]


def test_run_heavy_exclusive_and_memory_reserved_per_running(tmp_path: Path) -> None:
    """重型批不與任何批同時跑；快速層併發時剩餘記憶體須 ≥ min_free ×（執行中＋1）（r5 CODEX-R5-P1-04）。"""
    mixed = [{"kind": "heavy", "nodeids": ["t/h.py::x"], "estimate_s": 1.0}] + _chunks(2)
    meter = {"now": 0, "max": 0}
    s = rc.run(mixed, tmp_path, 3, 3.0, [], runner=_fake({}, [], hold=0.3, meter=meter), avail=lambda: 64.0)
    assert s["rc"] == 0 and meter["max"] == 2  # heavy 獨跑；其後兩個快速批可併
    meter2 = {"now": 0, "max": 0}
    s2 = rc.run(_chunks(3), tmp_path, 3, 3.0, [], runner=_fake({}, [], hold=0.3, meter=meter2), avail=lambda: 7.0)
    assert s2["rc"] == 0 and meter2["max"] == 2  # 7 GB：第二批需 6 ✓、第三批需 9 ✗


@pytest.mark.parametrize("avail,expected_max", [(lambda: 16.0, 2), (lambda: None, 1), (lambda: 1.0, 1)])
def test_run_concurrency_gated_by_free_memory(tmp_path: Path, avail: Callable[[], Optional[float]],
                                              expected_max: int) -> None:
    """jobs＝2：剩餘記憶體足 ⇒ 兩批重疊執行；讀不到或不足（< min_free_gb）⇒ 串行（同時至多 1）。"""
    meter = {"now": 0, "max": 0}
    calls: List[int] = []
    s = rc.run(_chunks(3), tmp_path, 2, 3.0, [], runner=_fake({}, calls, hold=0.3, meter=meter), avail=avail)
    assert s["rc"] == 0 and sorted(calls) == [0, 1, 2]
    assert meter["max"] == expected_max

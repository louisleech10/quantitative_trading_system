"""scripts/run_chunked.py：分批、每批新行程跑 pytest 選取（docs/TEST_SELECTION.md §5 過渡工具 6）。"""
from __future__ import annotations

import importlib.util
import json
import subprocess
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
          meter: Optional[Dict[str, int]] = None, tick: Optional[Dict[int, float]] = None,
          clk: Optional[Dict[str, float]] = None) -> Callable[..., Any]:
    """注入 runner；`tick`＋`clk`：第 i 批執行期間將假時鐘推進 tick[i] 秒（配 `run(clock=lambda: clk["t"])`）。"""
    lock = threading.Lock()

    def runner(cmd: List[str], log_path: Path, expected_seconds: float):
        i = int(log_path.stem.split("_")[1])
        with lock:
            calls.append(i)
            if tick is not None and clk is not None:
                clk["t"] += tick.get(i, 0.0)
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


# ── 估時偏差早期標示（只標示，不停止、不改 rc；NOCAP）─────────────────────────────────────────────────────────


@pytest.mark.parametrize("wall,est,flag", [
    (600.0, 300.0, False),    # 恰 2 倍
    (1000.0, 500.0, False),   # 恰 2 倍、多 500 秒（倍數須嚴格大於；超出秒數條件已成立，單測倍數邊界）
    (601.0, 300.0, True),     # 倍數 >2 且多 301 秒
    (400.0, 100.0, False),    # 4 倍但恰多 300 秒（超出秒數須嚴格大於）
    (401.0, 100.0, True),
    (250.0, 100.0, False),    # 2.5 倍、只多 150 秒：小批抖動不標
    (10000.0, 9000.0, False),  # 多 1,000 秒但不到 2 倍
    (301.0, 0.0, True),       # 估時 0 而實跑逾 300 秒
])
def test_deviation_threshold_boundary(wall: float, est: float, flag: bool) -> None:
    assert rc.DEVIATION_RATIO == 2.0 and rc.DEVIATION_MIN_EXCESS_S == 300.0
    assert rc.deviation(wall, est) is flag


def _est_chunks(n: int, est: float) -> List[Dict[str, Any]]:
    return [dict(c, estimate_s=est) for c in _chunks(n)]


def test_run_flags_chunk_deviation_at_first_chunk_without_stopping(tmp_path: Path, capsys: Any) -> None:
    """第一批即偏差 ⇒ 該批結束當下印 `[chunked] ⚠`（批號、實際、估時、倍數）＋累計偏差標示一次；後續批照跑、
    rc 不變；未越門檻之批（恰 4 倍多 300 秒）不標；累計偏差只標一次。"""
    clk = {"t": 0.0}
    calls: List[int] = []
    tick = {0: 401.0, 1: 400.0, 2: 1000.0}
    s = rc.run(_est_chunks(3, 100.0), tmp_path, 1, 3.0, [], runner=_fake({}, calls, tick=tick, clk=clk),
               clock=lambda: clk["t"])
    assert calls == [0, 1, 2] and s["rc"] == 0 and s["not_started"] == []
    assert s["deviations"] == [
        {"scope": "chunk", "chunk": 0, "kind": "fast", "wall_s": 401, "estimate_s": 100, "ratio": 4.01},
        {"scope": "cumulative", "after_chunk": 0, "chunks_done": 1, "wall_s": 401, "estimate_s": 100, "ratio": 4.01,
         "remaining_estimate_s": 200, "remaining_projected_s": 802},
        {"scope": "chunk", "chunk": 2, "kind": "fast", "wall_s": 1000, "estimate_s": 100, "ratio": 10.0}]
    out = capsys.readouterr().out.splitlines()
    warn = [ln for ln in out if ln.startswith("[chunked] ⚠")]
    assert len(warn) == 3 and "chunk 0" in warn[0] and "401s" in warn[0] and "100s" in warn[0] and "4.0 倍" in warn[0]
    # 第一個醒目標示緊接第一批之結束行（第一批就看得到，而非整跑結束）
    first_end = next(k for k, ln in enumerate(out) if ln.startswith("[chunked] chunk 0 "))
    assert out[first_end + 1] == warn[0]
    on_disk = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert on_disk["deviations"] == s["deviations"] and on_disk["rc"] == 0


def test_run_cumulative_deviation_without_single_chunk_flag(tmp_path: Path, capsys: Any) -> None:
    """每批 2.5 倍、各只多 150 秒（單批不標）；累計於第 3 批結束時多 450 秒 ⇒ 標示一次，之後不重複；不改 rc。"""
    clk = {"t": 0.0}
    tick = {i: 250.0 for i in range(4)}
    s = rc.run(_est_chunks(4, 100.0), tmp_path, 1, 3.0, [], runner=_fake({}, [], tick=tick, clk=clk),
               clock=lambda: clk["t"])
    assert s["rc"] == 0
    assert s["deviations"] == [{"scope": "cumulative", "after_chunk": 2, "chunks_done": 3, "wall_s": 750,
                                "estimate_s": 300, "ratio": 2.5, "remaining_estimate_s": 100,
                                "remaining_projected_s": 250}]
    warn = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("[chunked] ⚠")]
    assert len(warn) == 1 and "累計" in warn[0] and "3/4" in warn[0]


def test_run_no_deviation_within_estimate(tmp_path: Path, capsys: Any) -> None:
    clk = {"t": 0.0}
    s = rc.run(_est_chunks(2, 900.0), tmp_path, 1, 3.0, [], runner=_fake({}, [], tick={0: 1800.0, 1: 10.0}, clk=clk),
               clock=lambda: clk["t"])
    assert s["deviations"] == [] and "⚠" not in capsys.readouterr().out


# ── 選取後改檔偵測 ─────────────────────────────────────────────────────────────────────────────────────


def test_run_reports_changed_after_plan_without_changing_rc(tmp_path: Path, capsys: Any) -> None:
    """全部批結束後呼叫 freshness：有變更 ⇒ `[chunked] ⚠ 計畫後…`＋summary `changed_after_plan`，rc 不變；無變更 ⇒
    不標；比對拋例外 ⇒ 記 error 並標示（不得吞）。"""
    diff = {"changed": ["momentum/a.py"], "added": ["tests/new.py"], "removed": [], "head_changed": False}
    order: List[str] = []
    s = rc.run(_chunks(2), tmp_path, 1, 3.0, [], runner=_fake({}, []),
               freshness=lambda: order.append("fresh") or diff)
    assert s["rc"] == 0 and s["changed_after_plan"] == diff and order == ["fresh"]
    out = capsys.readouterr().out
    assert "[chunked] ⚠ 計畫後 repo 有變更 2 檔" in out and "changed: momentum/a.py" in out and "added: tests/new.py" in out
    assert json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))["changed_after_plan"] == diff
    clean = {"changed": [], "added": [], "removed": [], "head_changed": False}
    s2 = rc.run(_chunks(1), tmp_path, 1, 3.0, [], runner=_fake({}, []), freshness=lambda: clean)
    assert s2["changed_after_plan"] == clean and "⚠" not in capsys.readouterr().out

    def broken() -> Dict[str, Any]:
        raise subprocess.CalledProcessError(128, ["git"])

    s3 = rc.run(_chunks(1), tmp_path, 1, 3.0, [], runner=_fake({}, []), freshness=broken)
    assert s3["rc"] == 0 and "CalledProcessError" in s3["changed_after_plan"]["error"]
    assert "[chunked] ⚠ 計畫後改檔偵測失敗" in capsys.readouterr().out


def _g(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                    "-c", "core.hooksPath=/dev/null", *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _w(repo: Path, rel: str, text: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _repo(tmp_path: Path) -> Path:
    """tmp git repo：已追蹤 a、b、c、d 與 golden inventory；c 於計畫前已改（dirty）；u 為計畫前之未追蹤檔。"""
    repo = tmp_path / "repo"
    repo.mkdir()
    _g(repo, "init", "-q")
    for f in ("a.py", "b.py", "c.py", "d.py", "tests/golden/l65/test_inventory.txt"):
        _w(repo, f, f"{f} v1\n")
    _g(repo, "add", "-A")
    _g(repo, "commit", "-qm", "init")
    _w(repo, "c.py", "c.py dirty-at-plan\n")
    _w(repo, "u.py", "untracked v1\n")
    return repo


_EXCL = list(rc.FRESH_EXCLUDES) + ["out/"]


def test_fingerprint_detects_changed_added_removed_and_ignores_excluded(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    fp0 = rc.fingerprint(repo, _EXCL)
    assert set(fp0["files"]) == {"c.py", "u.py"}  # 只雜湊有變更之檔
    nothing = rc.compare_fingerprints(repo, fp0, rc.fingerprint(repo, _EXCL))
    assert (nothing["changed"], nothing["added"], nothing["removed"], nothing["head_changed"]) == ([], [], [], False)
    # 排除目錄／檔：計畫後任意寫入皆不得誤報
    for f in ("runs/r.txt", "handoffs/h.md", ".claude/s.json", ".testreg/t.json", "data_cache/d.h5",
              "pkg/__pycache__/m.pyc", "frontend/.claude/gate/dispatch.token", "out/summary.json"):
        _w(repo, f, "x\n")
    _w(repo, "tests/golden/l65/test_inventory.txt", "rewritten by tests\n")
    quiet = rc.compare_fingerprints(repo, fp0, rc.fingerprint(repo, _EXCL))
    assert (quiet["changed"], quiet["added"], quiet["removed"]) == ([], [], [])
    # 計畫後：改已追蹤檔、改計畫前已 dirty 之未追蹤檔、新增、刪除、把計畫前 dirty 之檔還原成 HEAD
    _w(repo, "a.py", "a.py v2\n")
    _w(repo, "u.py", "untracked v2\n")
    _w(repo, "new.py", "new\n")
    (repo / "b.py").unlink()
    _g(repo, "checkout", "-q", "--", "c.py")
    d = rc.compare_fingerprints(repo, fp0, rc.fingerprint(repo, _EXCL))
    assert d == {"changed": ["a.py", "c.py", "u.py"], "added": ["new.py"], "removed": ["b.py"], "head_changed": False}


def test_fingerprint_detects_commit_after_plan(tmp_path: Path) -> None:
    """計畫後 commit（工作樹乾淨但 HEAD 前進）⇒ 其間改動之檔列 changed、head_changed＝True；同一 commit 內之排除檔
    （golden inventory）不列。"""
    repo = _repo(tmp_path)
    fp0 = rc.fingerprint(repo, _EXCL)
    _w(repo, "d.py", "d.py v2\n")
    _w(repo, "tests/golden/l65/test_inventory.txt", "committed after plan\n")
    _g(repo, "add", "d.py", "tests/golden/l65/test_inventory.txt")
    _g(repo, "commit", "-qm", "d2")
    d = rc.compare_fingerprints(repo, fp0, rc.fingerprint(repo, _EXCL))
    assert d == {"changed": ["d.py"], "added": [], "removed": [], "head_changed": True}


def test_fingerprint_staged_rename_lists_both_sides(tmp_path: Path) -> None:
    """計畫後 `git mv`（已 stage 之改名）⇒ 舊名 removed、新名 added（git diff 預設改名偵測會只列新名，須關閉）。"""
    repo = _repo(tmp_path)
    fp0 = rc.fingerprint(repo, _EXCL)
    _g(repo, "mv", "d.py", "e.py")
    d = rc.compare_fingerprints(repo, fp0, rc.fingerprint(repo, _EXCL))
    assert d == {"changed": [], "added": ["e.py"], "removed": ["d.py"], "head_changed": False}


def _plan_with_fp(repo: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "plan.json").write_text(json.dumps({"fingerprint": rc.fingerprint(repo, _EXCL)}), encoding="utf-8")


def test_check_fresh_rc(tmp_path: Path, monkeypatch: Any, capsys: Any) -> None:
    """`--check-fresh <out>`：無變更 rc 0；有變更 ⇒ 印檔名、rc 1；plan.json 無指紋或不存在 ⇒ rc 2。"""
    repo = _repo(tmp_path)
    out = repo / "out"
    _plan_with_fp(repo, out)
    monkeypatch.setattr(rc, "REPO", repo)
    _w(repo, "runs/noise.txt", "x\n")  # 排除目錄不影響
    assert rc.main(["--check-fresh", "out"]) == 0
    _w(repo, "a.py", "a.py v2\n")
    assert rc.check_fresh(out, repo) == 1
    assert "changed: a.py" in capsys.readouterr().out
    assert rc.main(["--check-fresh", str(out)]) == 1  # 絕對路徑亦可
    (out / "plan.json").write_text(json.dumps({"fingerprint": None}), encoding="utf-8")
    assert rc.check_fresh(out, repo) == 2
    assert rc.check_fresh(repo / "nope", repo) == 2


def test_main_records_fingerprint_and_wires_freshness(tmp_path: Path, monkeypatch: Any) -> None:
    """main：plan.json 寫入指紋（排除本次 --out 目錄）；交給 run 之 freshness 於計畫後改檔時列出該檔。"""
    repo = _repo(tmp_path)
    _w(repo, "runs/sel.txt", "t/f.py::a\n")

    class FakeLd:
        FAST_LIMIT_S = 60.0

        @staticmethod
        def load_all_detail() -> Tuple[Dict[str, float], set, Dict[str, float]]:
            return {"t/f.py::a": 1.0}, set(), {}

        @staticmethod
        def conservative_estimate(nodes: List[str], *a: Any) -> Tuple[float, Dict[str, Any]]:
            return float(len(nodes)), {"unknown": [], "fixture_cost_unknown": [], "fixture_cost_added": {}}

    seen: Dict[str, Any] = {}

    def fake_run(chunks: List[Dict[str, Any]], out: Path, jobs: int, min_free: float, extra: List[str],
                 freshness: Any = None) -> Dict[str, Any]:
        (out / "chunk_000.log").write_text("x\n", encoding="utf-8")  # --out 目錄內產物不得誤報
        _w(repo, "a.py", "a.py v2\n")
        seen["diff"] = freshness()
        return {"rc": 0, "totals": {}, "stopped": "", "incomplete": [], "not_started": [], "deviations": [],
                "changed_after_plan": seen["diff"]}

    monkeypatch.setattr(rc, "REPO", repo)
    monkeypatch.setattr(rc, "_ld", lambda: FakeLd)
    monkeypatch.setattr(rc, "run", fake_run)
    assert rc.main(["--select", "runs/sel.txt", "--out", "myout"]) == 0
    fp = json.loads((repo / "myout" / "plan.json").read_text(encoding="utf-8"))["fingerprint"]
    assert set(fp["files"]) == {"c.py", "u.py"} and "myout/" in fp["excludes"]
    assert seen["diff"] == {"changed": ["a.py"], "added": [], "removed": [], "head_changed": False}

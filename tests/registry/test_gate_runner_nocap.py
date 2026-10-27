"""NOCAP Task 2.1（docs/NOCAP_SPEC.md）：pytest 閘門 runner 不依牆鐘停止——collect-only 與執行皆經共用監看、
分段上限參數預設 None、估時逾舊預算只印不拒跑。

秒級：只讀原始碼（AST）與呼叫純函式。施工前為紅（現行 collect 帶 900 秒逾時、分段上限預設 3600、
`admission` 以 7200 秒判 over）。
"""

from __future__ import annotations

import ast
import importlib.util
import os
import re
import sys
import time
from pathlib import Path
from typing import List

import pytest

REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "scripts" / "framepath_affected_gate.py"
TESTREG = REPO / "scripts" / "testreg.py"
MAX_OPT, MAX_ARG = "--max-seconds", "max_seconds"
_spec = importlib.util.spec_from_file_location("framepath_affected_gate_nocap", GATE)
g = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = g
_spec.loader.exec_module(g)  # type: ignore[union-attr]


def _function(path: Path, name: str) -> ast.FunctionDef:
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{path.name} 無函式 {name}")


def _call_keywords(fn: ast.AST) -> List[str]:
    return [kw.arg for node in ast.walk(fn) if isinstance(node, ast.Call) for kw in node.keywords if kw.arg]


def _calls(fn: ast.AST) -> List[str]:
    out = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            f = node.func
            out.append(f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", ""))
    return out


def test_boundary_06_gate_cli_cap_defaults_to_none() -> None:
    """framepath_affected_gate 之分段上限命令列參數預設 None（只在使用者明示時分段；登記 B「使用者明示」）。"""
    defaults = [kw.value for node in ast.walk(_function(GATE, "main")) if isinstance(node, ast.Call)
                and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == MAX_OPT
                for kw in node.keywords if kw.arg == "default"]
    assert len(defaults) == 1 and isinstance(defaults[0], ast.Constant) and defaults[0].value is None


def test_boundary_07_testreg_run_cap_defaults_to_none() -> None:
    """testreg.py 各函式之分段上限參數預設 None。"""
    found = []
    for node in ast.walk(ast.parse(TESTREG.read_text(encoding="utf-8"))):
        if isinstance(node, ast.FunctionDef) and node.args.defaults:
            args = node.args.args[-len(node.args.defaults):]
            found += [d for a, d in zip(args, node.args.defaults) if a.arg == MAX_ARG]
        if isinstance(node, ast.FunctionDef):  # 僅限關鍵字參數（`*` 之後）之預設亦須為 None
            found += [d for a, d in zip(node.args.kwonlyargs, node.args.kw_defaults) if a.arg == MAX_ARG and d is not None]
    assert found and all(isinstance(d, ast.Constant) and d.value is None for d in found), [ast.dump(d) for d in found]


def test_boundary_08_collect_has_no_wall_timeout_and_uses_shared_watchdog() -> None:
    """collect-only 子行程不帶牆鐘逾時參數、改經共用監看（run_watched）；舊常數 COLLECT_TIMEOUT_SECONDS 刪除。"""
    collect = _function(GATE, "collect")
    assert "timeout" not in _call_keywords(collect)
    assert "run_watched" in _calls(collect)
    assert not hasattr(g, "COLLECT_TIMEOUT_SECONDS")


def test_boundary_09_testreg_collect_shares_gate_implementation() -> None:
    """testreg.py 不再自帶 collect 牆鐘（不引用 COLLECT_TIMEOUT_SECONDS），共用 framepath_affected_gate 之實作。"""
    text = TESTREG.read_text(encoding="utf-8")
    assert "COLLECT_TIMEOUT_SECONDS" not in text
    sub = _function(TESTREG, "_subbatch_collect")  # testreg 之 collect 入口：不帶逾時參數、委由閘門之 collect（經共用監看）
    assert "timeout" not in _call_keywords(sub)
    assert {"collect", "collect_or_empty"} & set(_calls(sub))


def test_boundary_10_admission_over_old_budget_still_runs() -> None:
    """估時 8000 秒逾舊預算 7200 ⇒ 只印估時、不拒跑（admission 不再回 over 擋人）。"""
    out = g.admission(["t::a"], {"t::a": 8000.0})
    assert out["status"] != "over" and out["known_seconds"] == 8000.0


def test_boundary_11_runner_without_cap_does_not_pause(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Runner 未設上限（None）於累計 4000 秒等效（注入時鐘）時不暫停（Paused 次數＝0）。"""
    runner = g.Runner(tmp_path, None, 1)
    base = time.monotonic()
    monkeypatch.setattr(g.time, "monotonic", lambda: base + 4000.0)
    paused = 0
    try:
        runner._check_budget()  # 施工時自 Runner 呼叫路徑抽出之預算檢查
    except g.Paused:
        paused += 1
    assert paused == 0


def _fast_watch(monkeypatch: pytest.MonkeyPatch) -> None:
    """注入秒級監看門檻（施工時閘門以 `g.watchdog_config()` 取共用監看設定；測試換為小門檻）。"""
    spec = importlib.util.spec_from_file_location("wd_gate_nocap", REPO / "handoffs" / "run_receipts" / "numview_probes"
                                                  / "_watchdog.py")
    wd = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = wd
    spec.loader.exec_module(wd)  # type: ignore[union-attr]
    cfg = wd.WatchdogConfig(check_interval_seconds=0.05, log_stall_seconds=0.6, swap_growth_fraction_of_ram=None,
                            swap_consecutive_checks=2, wall_multiple_of_expected=3.0, wall_ceiling_seconds=60.0)
    monkeypatch.setattr(g, "watchdog_config", lambda: cfg, raising=False)
    monkeypatch.setattr(g, "restore_generated", lambda cwd: None)


def _test_file(tmp_path: Path, import_body: str, test_body: str = "pass") -> str:
    (tmp_path / "test_probe_nocap.py").write_text(f"{import_body}\n\ndef test_x():\n    {test_body}\n", encoding="utf-8")
    return "test_probe_nocap.py"


def _diag_path(message: str) -> Path:
    m = re.search(r"(\S*stacks\S*)", message)
    assert m, message
    return Path(m.group(1).rstrip("）)。,"))


def test_boundary_45_collect_busy_import_without_output_completes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """collect-only 之匯入忙算 1.5 秒無輸出（逾小門檻 0.6 秒，但有 CPU 進度）⇒ 收集完成、回 nodeid。"""
    _fast_watch(monkeypatch)
    busy = "import time\n_t = time.perf_counter()\nwhile time.perf_counter() - _t < 1.5:\n    pass"
    name = _test_file(tmp_path, busy)
    assert g.collect(name, tmp_path, dict(os.environ)) == [f"{name}::test_x"]


def test_boundary_46_collect_hung_import_stalls_and_leaves_stacks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """collect-only 之匯入卡住（睡眠、無 log 亦無 CPU）⇒ 判卡死、GateError 訊息含留現場之堆疊檔路徑且檔存在。"""
    _fast_watch(monkeypatch)
    name = _test_file(tmp_path, "import time\ntime.sleep(20)")
    with pytest.raises(g.GateError) as exc:
        g.collect(name, tmp_path, dict(os.environ))
    assert "卡死" in str(exc.value) and _diag_path(str(exc.value)).exists()


def test_boundary_47_run_file_hung_test_stalls_and_leaves_stacks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """執行之 pytest 子行程卡住（測試本體睡眠）⇒ 判卡死、GateError 訊息含堆疊檔路徑且檔存在。"""
    _fast_watch(monkeypatch)
    name = _test_file(tmp_path, "import time", "time.sleep(20)")
    with pytest.raises(g.GateError) as exc:
        g.run_file(name, tmp_path / "out.xml", tmp_path, dict(os.environ))
    assert "卡死" in str(exc.value) and _diag_path(str(exc.value)).exists()


def test_boundary_48_run_file_busy_test_without_output_completes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """測試本體忙算 1.5 秒無輸出 ⇒ rc＝0、結果為 passed。"""
    _fast_watch(monkeypatch)
    name = _test_file(tmp_path, "import time",
                      "_t = time.perf_counter()\n    while time.perf_counter() - _t < 1.5:\n        pass")
    rc, res = g.run_file(name, tmp_path / "out.xml", tmp_path, dict(os.environ))
    assert rc == 0 and len(res) == 1, res


def _testreg() -> object:
    spec = importlib.util.spec_from_file_location("testreg_gate_nocap", TESTREG)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_boundary_58_testreg_collect_busy_import_completes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """testreg 之 collect 入口（_subbatch_collect）：匯入忙算 1.5 秒無輸出 ⇒ 收集完成、回 nodeid。"""
    _fast_watch(monkeypatch)
    busy = "import time\n_t = time.perf_counter()\nwhile time.perf_counter() - _t < 1.5:\n    pass"
    name = _test_file(tmp_path, busy)
    assert _testreg()._subbatch_collect(g, name, tmp_path, dict(os.environ)) == [f"{name}::test_x"]


def test_boundary_59_testreg_collect_hung_import_stalls_and_leaves_stacks(monkeypatch: pytest.MonkeyPatch,
                                                                          tmp_path: Path) -> None:
    """testreg 之 collect 入口：匯入卡住 ⇒ 判卡死、例外訊息含留現場之堆疊檔路徑且檔存在。"""
    _fast_watch(monkeypatch)
    name = _test_file(tmp_path, "import time\ntime.sleep(20)")
    with pytest.raises(Exception) as exc:
        _testreg()._subbatch_collect(g, name, tmp_path, dict(os.environ))
    assert "卡死" in str(exc.value) and _diag_path(str(exc.value)).exists()


def test_mutation_explicit_cap_still_pauses(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """改壞對照：使用者明示上限 1 秒 ⇒ 注入 4000 秒後必暫停（boundary 11 之鑑別力；明示預算照辦）。"""
    runner = g.Runner(tmp_path, 1.0, 1)
    base = time.monotonic()
    monkeypatch.setattr(g.time, "monotonic", lambda: base + 4000.0)
    with pytest.raises(g.Paused):
        runner._check_budget()

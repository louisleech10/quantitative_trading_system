"""NOCAP Task 0.2／2.2（docs/NOCAP_SPEC.md）：全庫逾時／期限登記與掃描（scripts/timeout_scan.py）。

秒級：全庫文字＋AST 掃描。施工前為紅（掃描器為空殼、登記檔未全量登記、測試內部仍有 A 類與 pytest.mark.timeout）。
"""

from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("timeout_scan_under_test", REPO / "scripts" / "timeout_scan.py")
scan = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = scan
_spec.loader.exec_module(scan)  # type: ignore[union-attr]
REGISTRY = json.loads((REPO / "scripts" / "timeout_registry.json").read_text(encoding="utf-8"))["entries"]
INJECTED, STRING_ONLY = "    subprocess.run(cmd, timeout=60)\n", "log.info(\"timeout=5 seconds\")\n"


def test_boundary_12_repo_scan_every_hit_registered_and_not_class_a() -> None:
    """全庫（scripts／momentum／api／tests／handoffs probes／config／frontend）每處命中皆已登記且非 A 類。"""
    missing = scan.unregistered(scan.scan_repo(REPO), REGISTRY)
    assert missing == [], [f"{h.path}:{h.line} {h.text.strip()}" for h in missing[:20]]


def test_boundary_13_stale_registry_entry_is_red() -> None:
    """登記一個 repo 已不存在之檔:符號 ⇒ 判為過期列（防漂移）。"""
    ghost = {"path": "scripts/__nocap_ghost__.py", "function": "f", "callee": "subprocess.run", "literal": "5",
             "class": "C", "reason": "test"}
    assert ghost in scan.stale_entries(REGISTRY + [ghost], scan.scan_repo(REPO))


def test_boundary_14_config_yaml_timeout_key_detected() -> None:
    """`config/` 之 YAML 逾時鍵為命中（如 `config/optimization_config.yaml:59`）。"""
    hits = scan.scan_text("config/x.yaml", "optimization:\n    timeout: 300\n")
    assert [h.line for h in hits] == [2]


def test_boundary_15_frontend_poll_cap_and_giveup_detected() -> None:
    """前端輪詢次數上限常數與放棄分支為命中（`frontend/src/store/searchStore.ts:99` 同型）。"""
    text = "const maxAttempts = 150;\nif (attempts >= maxAttempts) throw new Error('Search timeout - task took too long');\n"
    assert {h.line for h in scan.scan_text("frontend/src/store/x.ts", text)} == {1, 2}


def test_boundary_16_playwright_config_timeouts_detected() -> None:
    """`frontend/playwright.config.ts` 之三種 e2e 等待設定為命中。"""
    text = "export default {\n  timeout: 120_000,\n  use: { actionTimeout: 30_000, navigationTimeout: 60_000 },\n};\n"
    assert {h.line for h in scan.scan_text("frontend/playwright.config.ts", text)} == {2, 3}


def test_boundary_17_string_only_occurrence_is_not_a_call() -> None:
    """字串中出現樣式（log 文字）⇒ 命中之 callee 為空字串（以 AST 判非呼叫，登記 D）。"""
    hits = scan.scan_text("scripts/x.py", STRING_ONLY)
    assert hits and all(h.callee == "" for h in hits)


def test_boundary_18_python_hit_carries_function_callee_literal() -> None:
    """Python 命中帶所在函式全名、被呼叫者與逾時字面值（白名單精確綁定之依據）。"""
    hits = scan.scan_text("scripts/x.py", "import subprocess\n\ndef go(cmd):\n" + INJECTED)
    assert [(h.function, h.callee, h.literal) for h in hits] == [("go", "subprocess.run", "60")]


def test_boundary_19_archived_copies_registered_as_class_d() -> None:
    """封存副本（numview_freeze_seam／testreg_probes/trial_impl）之命中皆登記 D「封存、不執行」。"""
    for h in scan.scan_repo(REPO):
        if "numview_freeze_seam" in h.path or "trial_impl" in h.path:
            entry = scan.registered(h, REGISTRY)
            assert entry is not None and entry["class"] == "D", h


def test_boundary_20_tests_have_no_pytest_mark_timeout() -> None:
    """Task 2.2：`pytest.mark.timeout` 標記全刪（未裝 pytest-timeout、無效且誤導）。"""
    files = subprocess.run(["git", "ls-files", "tests/*.py", "tests/**/*.py"], cwd=REPO, capture_output=True,
                           text=True).stdout.split()
    found = []
    for rel in files:
        try:
            tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):  # 只認真正之呼叫；測試資料字串中之字面不算
            f = node.func if isinstance(node, ast.Call) else None
            if isinstance(f, ast.Attribute) and f.attr == "timeout" and isinstance(f.value, ast.Attribute) \
                    and f.value.attr == "mark" and getattr(f.value.value, "id", "") == "pytest":
                found.append(f"{rel}:{node.lineno}")
    assert found == [], found


def test_mutation_substring_binding_hides_injected_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：白名單比對換回舊版「路徑＋子字串」⇒ 一列寬鬆登記即藏住注入之逾時呼叫（精確綁定之鑑別力）；
    精確綁定下同一注入必判未登記。"""
    hits = scan.scan_text("scripts/ffprod_measure.py", "import subprocess\n\ndef go(cmd):\n" + INJECTED)
    assert hits and scan.unregistered(hits, REGISTRY) == hits
    loose = REGISTRY + [{"path": "scripts/ffprod_measure.py", "contains": "subprocess.run", "class": "C", "reason": "x"}]
    monkeypatch.setattr(scan, "registered", lambda h, reg: next(
        (e for e in reg if e["path"] == h.path and e.get("contains", "") in h.text), None))
    assert scan.unregistered(hits, loose) == []

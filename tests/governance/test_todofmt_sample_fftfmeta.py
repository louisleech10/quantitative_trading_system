"""TODOFMT Task 3.2：第二樣本——FF-TFMETA 之 manifest（docs/TODOFMT_SPEC.md Task 3.2）。

本樣本只驗 manifest 已**宣告**對應（四情況、五等式）；測試之斷言內容屬 FF-TFMETA 之實作，不屬本票。
宣告之測試函式與現況須一致（b3 審碼 composer）：尚不存在者須標「（待 FF-TFMETA 新增）」，已存在者不得標
（以靜態比對該檔之 `def` 行判定，不 import、不收集）。
經 `gate.sh` 路由之斷言以既有治理測試隔離執行非 impl 之 dispatch（不帶 `--spec`），token 只落於 tmp。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "docs" / "manifests" / "FFTFMETA.json"
GATE = REPO_ROOT / "scripts" / "gate.sh"
FOUR_CASES = ("健康多 TF", "skip", "failed", "單 TF")
FIVE_EQUATIONS = (
    "expected = ordered(training_tfs)",
    "present = expected − skipped/failed",
    "failed ⊆ expected",
    "expected = present ∪ failed",
    "complete 時 failed = [] 且 present == expected",
)
OLD_RUNS = "既有 18 個 run 之 metadata 不得改寫"
PENDING = "（待 FF-TFMETA 新增）"
_NODE = re.compile(r"(tests/\S+?\.py)::(test_\w+)")


SAMPLE_SPEC_PATH = "docs/FFDEFECT_DECISION.md"
_MANIFEST_REL = "docs/manifests/FFTFMETA.json"


def _git_show(commit: str, rel: str) -> str | None:
    r = subprocess.run(["git", "show", f"{commit}:{rel}"], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    return r.stdout if r.returncode == 0 else None


def _sample_commit() -> str:
    """PRE-RED Task 1.2：TODOFMT 樣本版＝`git log -- docs/manifests/FFTFMETA.json` 中最新一個 spec_path 為
    `docs/FFDEFECT_DECISION.md` 之 commit（5156d074 起該檔改為 FF-TFMETA 正式施工清單）。找不到 ⇒ fail-closed。"""
    log = subprocess.run(["git", "log", "--format=%H", "--", _MANIFEST_REL], cwd=REPO_ROOT,
                         capture_output=True, text=True, check=True).stdout.split()
    for c in log:
        text = _git_show(c, _MANIFEST_REL)
        try:
            if text and json.loads(text).get("spec_path") == SAMPLE_SPEC_PATH:
                return c
        except json.JSONDecodeError:
            continue
    raise AssertionError(f"找不到 spec_path＝{SAMPLE_SPEC_PATH} 之樣本版 manifest")


def _m() -> dict:
    """樣本版 manifest（TODOFMT Task 3.2 所驗之對象）。"""
    return json.loads(_git_show(_sample_commit(), _MANIFEST_REL) or "")


def _m_current() -> dict:
    """工作樹現行 manifest（FF-TFMETA 正式施工清單）；用於 gate 路由與其改壞之鑑別。"""
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _assert_declared_test_truthful(line: str, commit: str | None = None) -> None:
    """該行所宣告之測試函式：存在 ⇔ 未標「待新增」。commit 給定時以該 commit 之樹判定（樣本版），否則以工作樹。"""
    m = _NODE.search(line)
    assert m, f"未宣告具名測試（path::test_*）：{line}"
    path, name = m.groups()
    if commit is not None:
        text = _git_show(commit, path)
    else:
        src = REPO_ROOT / path
        text = src.read_text(encoding="utf-8") if src.is_file() else None
    exists = text is not None and re.search(rf"^\s*def {name}\(", text, re.M) is not None
    assert exists != (PENDING in line), (
        f"已存在卻仍標{PENDING}：{line}" if exists else f"不存在卻未標{PENDING}：{line}"
    )


def _coverage_text() -> str:
    return "\n".join(_m()["batch_card"]["coverage_risk"])


def test_boundary_01_stub_modules_nonempty() -> None:
    assert _m()["stub_modules"]


def test_boundary_02_contract_jsons_declared() -> None:
    """FF 無既有 completeness 契約 JSON（實查）⇒ 以 not_executable 宣告此類為空（SPEC Task 3.2 之修訂）。"""
    m = _m()
    items = {n["item"] for n in m["batch_card"]["not_executable"]}
    assert m["contract_jsons"] or "contract_jsons" in items


def test_boundary_03_callers_now_empty_callers_later_nonempty() -> None:
    bc = _m()["batch_card"]
    assert bc["callers_now"] == [] and bc["callers_later"]


def test_boundary_04_coverage_risk_keeps_old_runs() -> None:
    assert OLD_RUNS in _coverage_text()


def test_boundary_05_lifecycle_legal() -> None:
    assert _m()["batch_card"]["lifecycle"] in {"keep", "drop_after_ticket", "supersede"}


@pytest.mark.parametrize("case", FOUR_CASES)
def test_boundary_06_each_case_has_named_test(case: str) -> None:
    lines = [ln for ln in _m()["batch_card"]["coverage_risk"] if ln.startswith(f"情況「{case}」")]
    assert len(lines) == 1, lines
    _assert_declared_test_truthful(lines[0], commit=_sample_commit())


@pytest.mark.parametrize("eq", FIVE_EQUATIONS)
def test_coverage_risk_lists_each_equation_with_named_test(eq: str) -> None:
    lines = [ln for ln in _m()["batch_card"]["coverage_risk"] if ln.startswith(f"等式「{eq}」")]
    assert len(lines) == 1, lines
    _assert_declared_test_truthful(lines[0], commit=_sample_commit())


def test_declared_test_truthfulness_discriminates() -> None:
    """判定有鑑別力：既有之 test_completeness_fields 標待新增 ⇒ 紅；不存在之名未標 ⇒ 紅。"""
    path = "tests/feature_engineering/test_failopen_manifest.py"
    _assert_declared_test_truthful(f"x：{path}::test_completeness_fields")
    for bad in (f"x：{path}::test_completeness_fields{PENDING}", f"x：{path}::test_todofmt_no_such_test"):
        with pytest.raises(AssertionError):
            _assert_declared_test_truthful(bad)


def test_manifest_passes_template_check_todofmt() -> None:
    r = subprocess.run(["bash", "scripts/template_check.sh", "todofmt", str(MANIFEST)], cwd=REPO_ROOT,
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout


def _gate_dispatch(tmp_path: Path, todo: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(tmp_path / "gate")
    return subprocess.run(
        ["bash", str(GATE), "dispatch", "--intent", "TODOFMT 樣本路由", "--risk", "low",
         "--facts-asked", "none-needed:unit-test", "--review-role", "single-executor:n/a",
         "--template", "n/a: todofmt sample routing", "--todo", str(todo)],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False, env=env,
    )


def test_gate_routes_manifest_to_todofmt_path(tmp_path: Path) -> None:
    r = _gate_dispatch(tmp_path, MANIFEST)
    assert r.returncode == 0 and "TODOFMT PASS" in r.stdout, r.stdout + r.stderr


def test_mutation_breaking_manifest_is_rejected_by_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """把樣本之 lifecycle 改成非法值 ⇒ 經 gate 路由即被拒（證路由真的執行了 todofmt 檢查）。"""
    bad = tmp_path / "FFTFMETA.json"
    data = _m_current()
    data["batch_card"]["lifecycle"] = "forever"
    bad.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "MANIFEST", bad)
    r = _gate_dispatch(tmp_path, MANIFEST)
    assert r.returncode != 0 and "TODOFMT FAIL" in r.stdout, r.stdout

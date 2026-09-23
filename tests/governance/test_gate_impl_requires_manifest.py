"""TODOFMT Task 1.4：`gate.sh` 於 impl 派工強制要求 manifest（docs/TODOFMT_SPEC.md Task 1.4）。

參數矩陣以 `todofmt-route` 入口呼叫 `gate.sh` 內同一判定函式，並以 `--legacy-spec-list` 傳入不含
`docs/TODOFMT_SPEC.md` 之既有清單，令該檔充當「新 SPEC」（其可通過 `template_check.sh spec`）。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.governance import _todofmt_anchor as anchor

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = REPO_ROOT / "scripts" / "gate.sh"
SPEC = "docs/TODOFMT_SPEC.md"
LIST_BEGIN = "TODOFMT LEGACY SPEC LIST"
ENTRY_CONDITION = 'if [ -n "${_rc_spec}" ] || [ "${_rc_impl}" = "1" ]; then'
DISPATCH_CALL = '_todofmt_route_check "${spec}" "${todo}" "${impl_self:-0}" "${todo_count}"'


def _list(tmp_path: Path, entries: list[str]) -> Path:
    p = tmp_path / "legacy_specs.txt"
    p.write_text("\n".join(entries) + "\n", encoding="utf-8")
    return p


def _route(tmp_path: Path, *args: str, legacy: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    lst = _list(tmp_path, legacy if legacy is not None else ["docs/some_other_spec.md"])
    return subprocess.run(["bash", str(GATE), "todofmt-route", "--legacy-spec-list", str(lst), *args],
                          cwd=REPO_ROOT, capture_output=True, text=True, check=False)


def _manifest(tmp_path: Path, spec_path: str = SPEC) -> Path:
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"stub_modules": [], "spec_path": spec_path}), encoding="utf-8")
    return p


def _prose(tmp_path: Path) -> Path:
    p = tmp_path / "OLD_TODO.md"
    p.write_text("x\n", encoding="utf-8")
    return p


def test_boundary_01_new_spec_without_todo_blocked(tmp_path: Path) -> None:
    r = _route(tmp_path, "--spec", SPEC)
    assert r.returncode == 1 and "須以 --todo" in r.stdout, r.stdout


def test_boundary_02_new_spec_with_matching_manifest_passes(tmp_path: Path) -> None:
    assert _route(tmp_path, "--spec", SPEC, "--todo", str(_manifest(tmp_path))).returncode == 0


def test_boundary_03_legacy_spec_without_todo_passes(tmp_path: Path) -> None:
    assert _route(tmp_path, "--spec", SPEC, legacy=[SPEC.lower()]).returncode == 0


def test_boundary_04_legacy_spec_with_prose_todo_passes(tmp_path: Path) -> None:
    assert _route(tmp_path, "--spec", SPEC, "--todo", str(_prose(tmp_path)), legacy=[SPEC.lower()]).returncode == 0


def test_boundary_05_new_spec_with_prose_todo_blocked(tmp_path: Path) -> None:
    r = _route(tmp_path, "--spec", SPEC, "--todo", str(_prose(tmp_path)))
    assert r.returncode == 1 and "不得配散文 TODO" in r.stdout, r.stdout


@pytest.mark.parametrize("variant", ["./docs/TODOFMT_SPEC.md", "Docs/TodoFmt_Spec.md", "ABS"])
def test_boundary_06_normalized_variants_hit_legacy(tmp_path: Path, variant: str) -> None:
    spec = f"{REPO_ROOT}/{SPEC}" if variant == "ABS" else variant
    assert _route(tmp_path, "--spec", spec, legacy=[SPEC.lower()]).returncode == 0


def test_boundary_07_manifest_spec_path_mismatch_blocked(tmp_path: Path) -> None:
    r = _route(tmp_path, "--spec", SPEC, "--todo", str(_manifest(tmp_path, "docs/OTHER_SPEC.md")))
    assert r.returncode == 1 and "不等" in r.stdout, r.stdout


def test_boundary_08_manifest_flag_does_not_substitute_todo(tmp_path: Path) -> None:
    src = GATE.read_text(encoding="utf-8")
    assert src.count(DISPATCH_CALL) == 1, "dispatch 應以 --todo（非 --manifest）呼叫判定"
    r = _route(tmp_path, "--spec", SPEC, "--manifest", str(_manifest(tmp_path)))
    assert r.returncode != 0, r.stdout


def test_boundary_09_impl_self_new_spec_without_todo_blocked(tmp_path: Path) -> None:
    assert _route(tmp_path, "--spec", SPEC, "--impl-self").returncode == 1


def test_boundary_10_impl_self_without_spec_blocked(tmp_path: Path) -> None:
    r = _route(tmp_path, "--impl-self")
    assert r.returncode == 1 and "--impl-self 須同時給 --spec" in r.stdout, r.stdout


def _x_literal() -> list[str]:
    text = anchor.read_x("scripts/gate.sh")
    assert text is not None
    return anchor.literal_block(text, LIST_BEGIN, LIST_BEGIN)


def test_boundary_11_production_uses_gate_literal_only() -> None:
    src = GATE.read_text(encoding="utf-8")
    assert src.count("--legacy-spec-list") >= 1
    uses = [ln for ln in src.splitlines() if "_tr_list_file" in ln and "cat" in ln]
    assert len(uses) == 1, "外部清單只准於 todofmt-route 測試入口讀取"
    r = subprocess.run(["bash", str(GATE), "todofmt-route", "--spec", _x_literal()[0]], cwd=REPO_ROOT,
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout


def test_boundary_12_literal_equals_l_tree_specs() -> None:
    assert _x_literal() == anchor.legacy_spec_paths()


def test_boundary_13_window_has_no_new_spec() -> None:
    assert [p for p in anchor.window_additions() if anchor.is_spec_style(p)] == []


def test_regression_non_impl_path_untouched(tmp_path: Path) -> None:
    assert ENTRY_CONDITION in (anchor.read_x("scripts/gate.sh") or "")
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(tmp_path / "gate")
    r = subprocess.run(["bash", str(GATE), "dispatch", "--intent", "TODOFMT 非 impl 回歸", "--risk", "low",
                        "--facts-asked", "none-needed:unit-test", "--review-role", "single-executor:n/a",
                        "--template", "n/a: todofmt non-impl regression"],
                       cwd=REPO_ROOT, capture_output=True, text=True, check=False, env=env)
    assert r.returncode == 0 and "TODOFMT 拒" not in r.stdout, r.stdout


def test_mutation_removing_spec_path_equality_lets_mismatch_through(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """移除 spec_path 相等之判定 ⇒ 邊界⑦之不等 manifest 被放行（證該測試有鑑別力）。"""
    src = GATE.read_text(encoding="utf-8")
    anchor_txt = 'if [ "$(_todofmt_norm "${_rc_sp}")" != "${_rc_ns}" ]; then'
    assert src.count(anchor_txt) == 1
    mismatch = _manifest(tmp_path, "docs/OTHER_SPEC.md")

    def _copy(name: str, text: str) -> Path:
        # 同佈局複本：一併複製 gate.sh 開頭 source 之家族 SoT，免因缺相依而早退（b3 自查：原探針因此假綠）
        scripts = tmp_path / name / "scripts"
        scripts.mkdir(parents=True)
        for dep in ("governance_families.sh", "governance_families.json"):
            shutil.copy(REPO_ROOT / "scripts" / dep, scripts / dep)
        (scripts / "gate.sh").write_text(text, encoding="utf-8")
        return scripts / "gate.sh"

    monkeypatch.setattr(sys.modules[__name__], "GATE", _copy("orig", src))
    r0 = _route(tmp_path, "--spec", SPEC, "--todo", str(mismatch))
    assert r0.returncode == 1 and "不等" in r0.stdout, "前提：同佈局之未改壞複本應以 spec_path 不等而擋"
    monkeypatch.setattr(sys.modules[__name__], "GATE", _copy("mut", src.replace(anchor_txt, "if false; then")))
    r = _route(tmp_path, "--spec", SPEC, "--todo", str(mismatch))
    assert r.returncode == 0, r.stdout + r.stderr

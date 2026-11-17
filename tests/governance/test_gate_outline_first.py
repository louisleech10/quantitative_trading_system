"""逐項流程之機械檢查：建 SPEC／TODO／PLAN（docs/ 下 .md，不分大小寫）或 TODO manifest（docs/manifests/*.json）前，
gate.sh artifact 須 `--outline`，且該大綱已經委員**確認通過**（某收斂輪 synth 以其為修訂標的、該輪債已銷、全部委員 VERDICT: proceed）；
gate_check.sh（PreToolUse）對新建 manifest 亦要求 artifact token。

使用者 2026-11-12 定「先寫大綱、逐項做」；2026-11-16「寫入記憶有屁用，還不是一直錯」⇒ 改由 gate 機械擋。
審查紀錄與債務帳本以 GATE_RECONCILE_DIR_OVERRIDE／GATE_DEBT_LEDGER_OVERRIDE（僅 GOVERNANCE_TEST_HARNESS=1 認）指向 tmp_path，
不讀寫 repo 之 handoffs/ 與正式 audit。
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "scripts" / "gate.sh"
GATE_CHECK = REPO / "scripts" / "gate_check.sh"
TEMPLATE = "templates/SPEC_TEMPLATE.md"


def _ledger(tmp_path: Path, state: str) -> Path:
    s = tmp_path / "ledger_stub.sh"
    s.write_text(f'#!/bin/bash\n[ "$1" = "--round-state" ] && echo {state}\n', encoding="utf-8")
    s.chmod(0o755)
    return s


def _round(tmp_path: Path, outline: Path, verdicts: list[str], name: str = "20991231-x-x-consult-r1") -> None:
    d = tmp_path / "reconcile" / name
    (d / "sources").mkdir(parents=True)
    (d / "synth.md").write_text(f"**修訂標的**：{outline}\n", encoding="utf-8")
    (d / "sources.lock").write_text(json.dumps({"round_id": f"rid-{name}"}), encoding="utf-8")
    for i, v in enumerate(verdicts):
        (d / "sources" / f"{name}-fam{i}.md").write_text(f"## X\n\nVERDICT: {v}\nBLOCKED-BY:\n", encoding="utf-8")


def _outline(tmp_path: Path) -> Path:
    o = tmp_path / "x-outline.md"
    o.write_text("# 大綱\n\n| # | 項目 |\n|---|---|\n| X1 | 甲 |\n| ↳ | X1a 子項 |\n", encoding="utf-8")
    return o


_DEFAULT = object()


def _run(tmp_path: Path, file: str, outline: Path | str | None, state: str = "CLOSED",
         harness: bool = True, cwd: Path = REPO, item: object = _DEFAULT,
         facts: object = _DEFAULT) -> subprocess.CompletedProcess:
    env = {**os.environ, "GATE_DIR_OVERRIDE": str(tmp_path / "gate"),
           "GATE_RECONCILE_DIR_OVERRIDE": str(tmp_path / "reconcile"),
           "GATE_DEBT_LEDGER_OVERRIDE": str(_ledger(tmp_path, state))}
    if harness:
        env["GOVERNANCE_TEST_HARNESS"] = "1"
    else:
        env.pop("GOVERNANCE_TEST_HARNESS", None)
    args = ["bash", str(GATE), "artifact", "--file", file, "--template-opened", TEMPLATE, "--sections", "§G=N/A:test"]
    if outline is not None:
        args += ["--outline", str(outline)]
    item_v = "X1" if item is _DEFAULT else item
    facts_v = "none:測試用、無未知事實" if facts is _DEFAULT else facts
    if item_v is not None:
        args += ["--item", str(item_v)]
    if facts_v is not None:
        args += ["--facts", str(facts_v)]
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)


def _confirmed(tmp_path: Path) -> Path:
    o = _outline(tmp_path)
    _round(tmp_path, o, ["proceed", "proceed", "proceed"])
    return o


def test_item_required_for_plan_artifact(tmp_path):
    """2026-11-17 使用者「盡量套業界的做法」：一份文件只對應一個大綱項（業界小批次）。"""
    r = _run(tmp_path, "docs/X_SPEC.md", _confirmed(tmp_path), item=None)
    assert r.returncode == 1 and "--item" in r.stdout, r.stdout


def test_item_not_in_outline_refused(tmp_path):
    r = _run(tmp_path, "docs/X_SPEC.md", _confirmed(tmp_path), item="X9")
    assert r.returncode == 1 and "大綱中無項目 X9" in r.stdout, r.stdout


def test_item_prefix_does_not_match_longer_id(tmp_path):
    """X1 不得因 X1a 之存在而算到；反之 X1a（子項列「| X1a 子項 |」）須認得。"""
    o = tmp_path / "only-sub.md"
    o.write_text("| ↳ | X1a 子項 |\n", encoding="utf-8")
    _round(tmp_path, o, ["proceed", "proceed", "proceed"])
    r = _run(tmp_path, "docs/X_SPEC.md", o, item="X1")
    assert r.returncode == 1 and "大綱中無項目 X1" in r.stdout, r.stdout
    r2 = _run(tmp_path, "docs/X_SPEC.md", o, item="X1a")
    assert r2.returncode == 0 and "GATE PASS" in r2.stdout, r2.stdout + r2.stderr


def test_item_sub_row_with_annotated_arrow_cell_accepted(tmp_path):
    """委員 commit-r2 三家：子項列第 1 欄可為「↳ 說明文字」（真實大綱 I1a 列之寫法），第 2 欄首詞須認得。"""
    o = tmp_path / "annotated.md"
    o.write_text("| X1 | 甲 |\n| ↳ X1 拆分（說明；一次只做一個子項） | X1a 子項 | 實測 |\n| ↳ | X1b 子項 | 實測 |\n",
                 encoding="utf-8")
    _round(tmp_path, o, ["proceed", "proceed", "proceed"])
    for sub in ("X1a", "X1b"):
        r = _run(tmp_path, "docs/X_SPEC.md", o, item=sub)
        assert r.returncode == 0 and "GATE PASS" in r.stdout, (sub, r.stdout + r.stderr)
    r = _run(tmp_path, "docs/X_SPEC.md", o, item="實測")
    assert r.returncode == 1, r.stdout


def test_item_in_non_item_column_refused(tmp_path):
    """CODEX-R1-P1-01：ID 只認項目欄（第 1 欄或「↳」列之第 2 欄起首），其他欄出現同字不算。"""
    o = tmp_path / "decoy.md"
    o.write_text("| X1 | SPEC 撰寫 |\n| ↳ | X1a 子項 | SPEC |\n", encoding="utf-8")
    _round(tmp_path, o, ["proceed", "proceed", "proceed"])
    r = _run(tmp_path, "docs/X_SPEC.md", o, item="SPEC")
    assert r.returncode == 1 and "大綱中無項目 SPEC" in r.stdout, r.stdout


def test_item_dot_is_not_regex_wildcard(tmp_path):
    """GROK-R1-P2-01：白名單允許之「.」不得當 regex 任意字元（I1. 不得誤中 I1a）。"""
    o = tmp_path / "dot.md"
    o.write_text("| ↳ | X1a 子項 |\n", encoding="utf-8")
    _round(tmp_path, o, ["proceed", "proceed", "proceed"])
    r = _run(tmp_path, "docs/X_SPEC.md", o, item="X1.")
    assert r.returncode == 1 and "大綱中無項目 X1." in r.stdout, r.stdout


def test_relative_paths_ignore_cwd_same_name_file(tmp_path):
    """CODEX-R1-P2-02：相對路徑一律以 repo 根解析——cwd 有同名檔（另一版）不得被採用。"""
    elsewhere = tmp_path / "elsewhere"
    (elsewhere / "docs").mkdir(parents=True)
    decoy = elsewhere / "docs" / "ONLY_IN_CWD_OUTLINE.md"
    decoy.write_text("| X1 | 甲 |\n", encoding="utf-8")
    rel = "docs/ONLY_IN_CWD_OUTLINE.md"  # repo 根無此檔
    _round(tmp_path, Path(rel), ["proceed", "proceed", "proceed"])
    r = _run(tmp_path, "docs/X_SPEC.md", rel, cwd=elsewhere)
    assert r.returncode == 1 and "--outline 檔不存在" in r.stdout, r.stdout


def test_item_rejects_regex_metacharacters(tmp_path):
    r = _run(tmp_path, "docs/X_SPEC.md", _confirmed(tmp_path), item="X.*")
    assert r.returncode == 1 and "--item 只允許" in r.stdout, r.stdout


def test_facts_required_for_plan_artifact(tmp_path):
    """Definition of Ready：未知事實須先實測；無未知者以 none:<理由> 宣告（不設時限）。"""
    r = _run(tmp_path, "docs/X_SPEC.md", _confirmed(tmp_path), facts=None)
    assert r.returncode == 1 and "--facts" in r.stdout, r.stdout


def test_facts_none_without_reason_refused(tmp_path):
    r = _run(tmp_path, "docs/X_SPEC.md", _confirmed(tmp_path), facts="none:  ")
    assert r.returncode == 1 and "須附理由" in r.stdout, r.stdout


def test_facts_file_without_receipt_refused(tmp_path):
    f = tmp_path / "facts.md"
    f.write_text("只有散文、沒有實測\n", encoding="utf-8")
    r = _run(tmp_path, "docs/X_SPEC.md", _confirmed(tmp_path), facts=str(f))
    assert r.returncode == 1 and "無 FACT-RECEIPT" in r.stdout, r.stdout


def test_facts_missing_file_refused(tmp_path):
    r = _run(tmp_path, "docs/X_SPEC.md", _confirmed(tmp_path), facts=str(tmp_path / "nope.md"))
    assert r.returncode == 1 and "--facts 檔不存在" in r.stdout, r.stdout


def test_facts_file_with_receipt_passes(tmp_path):
    f = tmp_path / "facts.md"
    f.write_text("FACT-RECEIPT: `echo x` → 印出 `x`（主委 實跑 2026-11-17）\n", encoding="utf-8")
    r = _run(tmp_path, "docs/X_SPEC.md", _confirmed(tmp_path), facts=str(f))
    assert r.returncode == 0 and "GATE PASS" in r.stdout, r.stdout + r.stderr


def test_non_plan_artifact_needs_no_item_or_facts(tmp_path):
    r = _run(tmp_path, "docs/X_NOTES.md", None, item=None, facts=None)
    assert r.returncode == 0 and "GATE PASS" in r.stdout, r.stdout + r.stderr


def test_relative_paths_resolve_from_repo_root_when_cwd_elsewhere(tmp_path):
    """工作目錄不在 repo 根（如 session 停在 worktree）時，--template-opened／--outline 之 repo 相對路徑仍以 repo 根解析
    （2026-11-17：I1 SPEC 開閘於 worktree 工作目錄報「--outline 檔不存在」）。"""
    rel_outline = "docs/TICKET_ORDER.md"  # repo 內已追蹤、含「| 9a-1 |」項目列之檔，僅作路徑解析對象
    _round(tmp_path, Path(rel_outline), ["proceed", "proceed", "proceed"])
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    r = _run(tmp_path, "docs/X_SPEC.md", rel_outline, state="CLOSED", cwd=elsewhere, item="9a-1")
    assert r.returncode == 0 and "GATE PASS" in r.stdout, r.stdout + r.stderr


def test_spec_without_outline_refused(tmp_path):
    r = _run(tmp_path, "docs/X_SPEC.md", None)
    assert r.returncode == 1 and "--outline" in r.stdout, r.stdout


def test_lowercase_spec_and_manifest_and_todo_plan_require_outline(tmp_path):
    for f in ("docs/x_spec.md", "docs/manifests/X.json", "docs/X_TODO.md", "docs/X_PLAN.md"):
        r = _run(tmp_path, f, None)
        assert r.returncode == 1 and "--outline" in r.stdout, (f, r.stdout)


def test_missing_outline_file_refused(tmp_path):
    r = _run(tmp_path, "docs/X_SPEC.md", tmp_path / "nope.md")
    assert r.returncode == 1 and "--outline 檔不存在" in r.stdout, r.stdout


def test_unreviewed_outline_refused(tmp_path):
    r = _run(tmp_path, "docs/X_SPEC.md", _outline(tmp_path))
    assert r.returncode == 1 and "大綱未經委員審查" in r.stdout, r.stdout


def test_reviewed_but_blocked_outline_refused(tmp_path):
    """r4 CODEX-R4-P1-01 反例：收斂檔已提到大綱、但某委員 blocked ⇒ 不得放行。"""
    o = _outline(tmp_path)
    _round(tmp_path, o, ["proceed", "blocked"])
    r = _run(tmp_path, "docs/X_SPEC.md", o, state="CLOSED")
    assert r.returncode == 1 and "尚未經委員確認通過" in r.stdout, r.stdout


def test_all_proceed_but_round_open_refused(tmp_path):
    o = _outline(tmp_path)
    _round(tmp_path, o, ["proceed", "proceed", "proceed"])
    r = _run(tmp_path, "docs/X_SPEC.md", o, state="OPEN")
    assert r.returncode == 1 and "尚未經委員確認通過" in r.stdout, r.stdout


def test_confirmed_outline_passes_even_after_earlier_blocked_round(tmp_path):
    o = _outline(tmp_path)
    _round(tmp_path, o, ["blocked", "proceed"], name="20991231-x-x-consult-r1")
    _round(tmp_path, o, ["proceed", "proceed", "proceed"], name="20991231-x-x-consult-r2")
    r = _run(tmp_path, "docs/X_SPEC.md", o, state="CLOSED")
    assert r.returncode == 0 and "GATE PASS" in r.stdout, r.stdout + r.stderr


def test_non_plan_artifact_unaffected(tmp_path):
    r = _run(tmp_path, "docs/X_NOTES.md", None)
    assert r.returncode == 0 and "GATE PASS" in r.stdout, r.stdout + r.stderr


def test_overrides_ignored_without_harness(tmp_path):
    """正式路徑（無 GOVERNANCE_TEST_HARNESS）不得以覆寫指向 tmp 審查紀錄／帳本放行。"""
    o = _outline(tmp_path)
    _round(tmp_path, o, ["proceed", "proceed", "proceed"])
    r = _run(tmp_path, "docs/X_SPEC.md", o, state="CLOSED", harness=False)
    assert r.returncode == 1 and "大綱未經委員審查" in r.stdout, r.stdout


def _hook(tmp_path: Path, file_path: str) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": file_path, "content": "{}"}})
    env = {**os.environ, "GATE_DIR_OVERRIDE": str(tmp_path / "hookgate")}
    return subprocess.run(["bash", str(GATE_CHECK)], cwd=REPO, env=env, input=payload, capture_output=True, text=True)


def test_hook_blocks_new_manifest_without_token(tmp_path):
    r = _hook(tmp_path, "docs/manifests/ZZZ_OUTLINE_GATE_TEST_NOT_EXIST.json")
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)


def test_hook_ignores_existing_manifest_edit_path(tmp_path):
    existing = sorted((REPO / "docs" / "manifests").glob("*.json"))
    assert existing, "repo 應已有 manifest 供對照"
    r = _hook(tmp_path, str(existing[0].relative_to(REPO)))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)

"""DOCROT2 Task 4.1 — 全專案遷移判定（scripts/live_doc_registry_check.sh --migration）。

測什麼：`docs/DOCROT2_TODO.md` Task 4.1 驗證欄之兩個 fixture、邊界①（清單過期）、邊界②（遷移前後 SPLITUNIFY
殘留識別碼集合逐 ID 對讀）與 SPEC 邊界②（ROADMAP 生成區塊與 fact_keys rows 逐識別碼對讀），外加判定範圍與清單檔封閉驗證。
fixture 形態：各測試於 tmp 建獨立 git repo，複製登記模組、守衛模組與生成器（判定碼唯一來源），在其中執行
（同 Task 1.1 之具名偏離：不建靜態 fixture 目錄，以免 fixture 本身落入本 repo 活文件清冊）。
`current_tree_after_migration` 另對本 repo 現樹實跑一次（遷移後之真實狀態）。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = ["_live_doc_registry.py", "live_doc_registry_check.sh", "_live_doc_write_guard.py",
           "live_doc_write_guard.sh", "gen_fact_key_blocks.sh", "governance_families.json"]
REAL_REGISTRY = json.loads((REPO / "scripts" / "live_doc_registry.json").read_text(encoding="utf-8"))
REAL_FACT_KEYS = json.loads((REPO / "scripts" / "fact_keys.json").read_text(encoding="utf-8"))
STATUS_ENUM = REAL_FACT_KEYS["_schema"]["status_enum"]
RES_REL = "scripts/docrot2_migration_residuals.json"
COLS = ["序", "識別碼", "狀態", "權威路徑", "下一步"]
MISSING = object()

CONTRACT = ("docs/A.md", "LIVE-CONTRACT")
CONTRACT_B = ("docs/B.md", "LIVE-CONTRACT")
TARGET = ("docs/d2.md", "LIVE-CONTRACT")
LOG = ("docs/LOG.md", "LOG")
HIT = "# A\n\n- D2B 進行中\n"
CLEAN = "# A\n\n- 一般文字\n"
BLOCK = ("<!-- BEGIN GENERATED: d2-x -->\n| 序 | 識別碼 | 狀態 | 權威路徑 | 下一步 |\n|---|---|---|---|---|\n"
         "| 010 | D2B | 進行中 | x | 做 D2B |\n<!-- END GENERATED: d2-x -->\n")


def _fact_keys() -> dict:
    return {
        "_schema": {
            "status_enum": STATUS_ENUM,
            "status_keys": ["st-a"],
            "status_scope": ["docs/"],
            "status_scope_grandfathered": ["docs/__none__.md"],
            "enforcement_completed_statuses": ["收案", "已落地", "已完成"],
            "docrot2_status_keys": ["d2-x"],
            "docrot2_status_values": ["未開工", "進行中", "部分完成", "待審", "停手", "狀態未確認", "已完成"],
        },
        "st-a": {"target": "docs/st.md", "columns": COLS, "rows": [["010", "B-63", "部分完成", "x", "做"]]},
        "d2-x": {"target": "docs/d2.md", "columns": COLS, "rows": [["010", "D2B", "進行中", "x", "做 D2B"]]},
    }


def _row(path: str, rid: str = "R-X", cls: str = "user-ruling") -> dict:
    return {"id": rid, "path": path, "reason_class": cls, "why": "w", "owner": "o", "trigger": "t"}


def _repo(tmp_path: Path, files: dict, *, exact=(), residuals=(), raw=MISSING) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for name in SCRIPTS:
        shutil.copy2(REPO / "scripts" / name, root / "scripts" / name)
    reg = json.loads(json.dumps(REAL_REGISTRY))
    reg["exact"] = [list(p) for p in exact]
    reg["prefix"] = [["docs/Archived/", "HIST"], ["docs/site/", "HIST"], ["templates/", "LIVE-CONTRACT"],
                     ["白話說明/", "LIVE-PLAIN"], ["白話說明/Archived/", "HIST"]]
    (root / "scripts" / "live_doc_registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "scripts" / "fact_keys.json").write_text(json.dumps(_fact_keys(), ensure_ascii=False, indent=2), encoding="utf-8")
    if raw is MISSING:
        text = json.dumps({"residuals": list(residuals)}, ensure_ascii=False, indent=2)
    else:
        text = raw
    if text is not None:
        (root / RES_REL).write_text(text, encoding="utf-8")
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body.encode("utf-8"))
    return root


def _mig(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(root / "scripts" / "live_doc_registry_check.sh"), "--migration"],
                          cwd=str(root), capture_output=True, text=True)


# ================================================================ Task 4.1 驗證欄


def test_hit_file_neither_migrated_nor_listed_rc1(tmp_path):
    root = _repo(tmp_path, {"docs/A.md": HIT}, exact=[CONTRACT])
    r = _mig(root)
    assert r.returncode == 1, r.stderr
    assert "docs/A.md" in r.stderr and "不在殘留清單" in r.stderr and "L3「D2B」＋「進行中」" in r.stderr, r.stderr


def test_current_tree_after_migration_rc0(tmp_path):
    # 遷移後形態：狀態移入本檔為 target 之合法生成區塊（豁免）＋另一命中檔具名列殘留
    files = {"docs/d2.md": "# d2\n\n" + BLOCK, "docs/A.md": HIT}
    root = _repo(tmp_path, files, exact=[CONTRACT, TARGET], residuals=[_row("docs/A.md")])
    r = _mig(root)
    assert r.returncode == 0, r.stderr
    assert "命中檔 1 個" in r.stdout and "殘留 1 列" in r.stdout, r.stdout


def test_current_tree_after_migration_real_repo_rc0():
    r = subprocess.run(["bash", "scripts/live_doc_registry_check.sh", "--migration"], cwd=str(REPO),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


# ================================================================ Task 4.1 邊界


def test_listed_file_without_hits_is_stale_rc1(tmp_path):
    root = _repo(tmp_path, {"docs/A.md": CLEAN}, exact=[CONTRACT], residuals=[_row("docs/A.md", "R-STALE")])
    r = _mig(root)
    assert r.returncode == 1 and "R-STALE" in r.stderr and "已無命中" in r.stderr and "清單過期" in r.stderr, r.stderr


@pytest.mark.parametrize("path, files", [
    ("docs/Archived/H.md", {"docs/Archived/H.md": HIT}),   # HIST 類不判定
    ("docs/LOG.md", {"docs/LOG.md": HIT}),                 # LOG 類不判定
    ("docs/NOPE.md", {}),                                  # 不存在
])
def test_listed_path_outside_judgement_range_rc1(tmp_path, path, files):
    root = _repo(tmp_path, files, exact=[LOG], residuals=[_row(path, "R-OUT")])
    r = _mig(root)
    assert r.returncode == 1 and "R-OUT" in r.stderr and "不在判定範圍" in r.stderr, r.stderr


def test_splitunify_residual_ids_identical_across_rendered_targets():
    """邊界②：SPLITUNIFY 殘留識別碼集合，遷移後各生成落點與 fact_keys rows 逐 ID 相同（含本批新增之 ROADMAP／白話進度表）。"""
    spec = REAL_FACT_KEYS["splitunify-residual-status"]
    ids = [row[1] for row in spec["rows"]]
    targets = spec["target"] if isinstance(spec["target"], list) else [spec["target"]]
    assert {"docs/ROADMAP.md", "白話說明/SPLITUNIFY施工進度.md"} <= set(targets)
    for rel in targets:
        text = (REPO / rel).read_text(encoding="utf-8")
        m = re.search(r"^<!-- BEGIN GENERATED: splitunify-residual-status -->\n(.*?)^<!-- END GENERATED: splitunify-residual-status -->$",
                      text, re.S | re.M)
        assert m, rel
        got = [ln.split("|")[2].strip() for ln in m.group(1).splitlines()[2:]]
        assert got == ids, rel


def test_roadmap_generated_block_matches_fact_keys_rows():
    """SPEC 邊界②：docs/ROADMAP.md 之 roadmap-status 生成區塊與 fact_keys rows 逐識別碼（含狀態）對讀；狀態格不得在區塊外手寫。"""
    spec = REAL_FACT_KEYS["roadmap-status"]
    assert spec["target"] == "docs/ROADMAP.md"
    si = spec["columns"].index("狀態")
    want = [(row[1], row[si]) for row in spec["rows"]]
    text = (REPO / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    m = re.search(r"^<!-- BEGIN GENERATED: roadmap-status -->\n(.*?)^<!-- END GENERATED: roadmap-status -->$", text, re.S | re.M)
    assert m
    cells = [[c.strip() for c in ln.split("|")[1:-1]] for ln in m.group(1).splitlines()[2:]]
    assert [(c[1], c[si]) for c in cells] == want
    assert "roadmap-status" in REAL_FACT_KEYS["_schema"]["docrot2_status_keys"]


# ================================================================ 判定範圍（與寫入前守衛同一豁免）


def test_exempt_regions_are_not_hits_rc0(tmp_path):
    text = ("# d2\n\n" + BLOCK + "\n```\nD2B 進行中\n```\n\n<!-- HISTORY-BEGIN -->\nD2B 進行中\n<!-- HISTORY-END -->\n")
    root = _repo(tmp_path, {"docs/d2.md": text}, exact=[TARGET])
    r = _mig(root)
    assert r.returncode == 0, r.stderr


def test_generated_block_of_non_target_key_not_exempt_rc1(tmp_path):
    root = _repo(tmp_path, {"docs/A.md": "# A\n\n" + BLOCK}, exact=[CONTRACT])
    r = _mig(root)
    assert r.returncode == 1 and "docs/A.md" in r.stderr, r.stderr


def test_unclosed_generated_block_not_exempt_rc1(tmp_path):
    text = "# d2\n\n<!-- BEGIN GENERATED: d2-x -->\n| 010 | D2B | 進行中 | x | 做 D2B |\n"
    root = _repo(tmp_path, {"docs/d2.md": text}, exact=[TARGET])
    r = _mig(root)
    assert r.returncode == 1 and "docs/d2.md" in r.stderr, r.stderr


def test_log_and_hist_classes_not_judged_rc0(tmp_path):
    root = _repo(tmp_path, {"docs/LOG.md": HIT, "docs/Archived/H.md": HIT}, exact=[LOG])
    r = _mig(root)
    assert r.returncode == 0, r.stderr


def test_unregistered_md_rc1(tmp_path):
    root = _repo(tmp_path, {"docs/UNREG.md": CLEAN})
    r = _mig(root)
    assert r.returncode == 1 and "docs/UNREG.md" in r.stderr and "未登記" in r.stderr, r.stderr


def test_crlf_file_hit_detected_rc1(tmp_path):
    root = _repo(tmp_path, {"docs/A.md": "# A\r\n\r\n- D2B 進行中\r\n"}, exact=[CONTRACT])
    r = _mig(root)
    assert r.returncode == 1 and "docs/A.md" in r.stderr, r.stderr


def test_status_keys_identifier_detected_rc1(tmp_path):
    root = _repo(tmp_path, {"docs/A.md": "# A\n- B-63 部分完成\n"}, exact=[CONTRACT])
    r = _mig(root)
    assert r.returncode == 1 and "B-63" in r.stderr, r.stderr


def test_hits_attributed_to_right_file_in_single_call_rc1(tmp_path):
    # 多檔合併一次判定：命中須歸屬正確檔與行號（A 列殘留、B 未列 ⇒ 只報 B）
    files = {"docs/A.md": HIT, "docs/B.md": "# B\n\n\n\n- D2B 進行中\n"}
    root = _repo(tmp_path, files, exact=[CONTRACT, CONTRACT_B], residuals=[_row("docs/A.md")])
    r = _mig(root)
    assert r.returncode == 1, r.stderr
    assert "docs/B.md：全檔命中（L5「D2B」" in r.stderr and "docs/A.md：" not in r.stderr, r.stderr


# ================================================================ pre-commit 掛載（③）

GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, env={**os.environ, **GIT_ENV})


def _precommit_repo(tmp_path: Path, files: dict, **kw) -> Path:
    root = _repo(tmp_path, files, **kw)
    (root / "scripts" / "git_hooks").mkdir()
    shutil.copy2(REPO / "scripts" / "git_hooks" / "pre-commit", root / "scripts" / "git_hooks" / "pre-commit")
    (root / "scripts" / "verification_claim_check.py").write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "base")
    return root


def _precommit(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(root / "scripts" / "git_hooks" / "pre-commit")], cwd=str(root),
                          capture_output=True, text=True)


def test_pre_commit_calls_migration_check():
    text = (REPO / "scripts" / "git_hooks" / "pre-commit").read_text(encoding="utf-8")
    assert "bash scripts/live_doc_registry_check.sh --migration" in text


def test_pre_commit_blocks_stale_residual_row_when_hits_removed(tmp_path):
    root = _precommit_repo(tmp_path, {"docs/A.md": HIT}, exact=[CONTRACT], residuals=[_row("docs/A.md", "R-GONE")])
    (root / "docs" / "A.md").write_text(CLEAN, encoding="utf-8")
    _git(root, "add", "docs/A.md")
    r = _precommit(root)
    assert r.returncode != 0 and "R-GONE" in r.stderr and "全專案遷移判定未過" in r.stderr, r.stdout + r.stderr


def test_pre_commit_blocks_new_identifier_that_makes_existing_line_hit(tmp_path):
    # 文件一字未改：fact_keys 新增識別碼即讓既有行命中 ⇒ 寫入前守衛看不到，須由 ③ 擋
    root = _precommit_repo(tmp_path, {"docs/A.md": "# A\n\n- NEWID 進行中\n"}, exact=[CONTRACT])
    fk = _fact_keys()
    fk["d2-x"]["rows"].append(["020", "NEWID", "未開工", "x", "做 NEWID"])
    (root / "scripts" / "fact_keys.json").write_text(json.dumps(fk, ensure_ascii=False, indent=2), encoding="utf-8")
    _git(root, "add", "scripts/fact_keys.json")
    r = _precommit(root)
    assert r.returncode != 0 and "docs/A.md" in r.stderr and "NEWID" in r.stderr, r.stdout + r.stderr


def test_pre_commit_gitignore_change_triggers_migration(tmp_path):
    # 反向排除讓原被忽略之 .md 入清冊：只暫存 .gitignore 亦須觸發 ③
    files = {".gitignore": "docs/HIDDEN.md\n", "docs/HIDDEN.md": HIT}
    root = _precommit_repo(tmp_path, files, exact=[("docs/HIDDEN.md", "LIVE-CONTRACT")])
    (root / ".gitignore").write_text("", encoding="utf-8")
    _git(root, "add", ".gitignore")
    r = _precommit(root)
    assert r.returncode != 0 and "docs/HIDDEN.md" in r.stderr, r.stdout + r.stderr


def test_pre_commit_migration_not_triggered_by_unrelated_path(tmp_path):
    root = _precommit_repo(tmp_path, {"docs/A.md": HIT}, exact=[CONTRACT])   # 現樹命中且未列：一旦觸發必紅
    (root / "notes.txt").write_text("x\n", encoding="utf-8")
    _git(root, "add", "notes.txt")
    r = _precommit(root)
    assert r.returncode == 0, r.stdout + r.stderr


# ================================================================ 殘留清單檔封閉驗證（fail-closed rc=2）


def _bad(**over) -> dict:
    row = _row("docs/A.md")
    row.update(over)
    return row


@pytest.mark.parametrize("raw", [
    json.dumps({"residuals": [_bad(reason_class="later")]}),
    json.dumps({"residuals": [{k: v for k, v in _row("docs/A.md").items() if k != "trigger"}]}),
    json.dumps({"residuals": [_bad(extra="x")]}),
    json.dumps({"residuals": [_bad(why="  ")]}),
    json.dumps({"residuals": [_bad(owner=1)]}),
    json.dumps({"residuals": [_row("docs/A.md", "R-1"), _row("docs/A.md", "R-2")]}),
    json.dumps({"residuals": [_row("docs/A.md", "R-1"), _row("docs/B.md", "R-1")]}),
    json.dumps({"residuals": [], "rows": []}),
    json.dumps({"residuals": {}}),
    json.dumps({}),
    "{not json",
    None,
], ids=["bad-reason-class", "missing-field", "extra-field", "blank-field", "non-string", "dup-path", "dup-id",
        "extra-top-key", "residuals-not-list", "no-residuals", "invalid-json", "file-missing"])
def test_residual_list_invalid_rc2(tmp_path, raw):
    files = {"docs/A.md": HIT, "docs/B.md": HIT}
    root = _repo(tmp_path, files, exact=[CONTRACT, CONTRACT_B], raw=raw)
    r = _mig(root)
    assert r.returncode == 2 and "fail-closed" in r.stderr, r.stderr


def test_real_residual_rows_reason_class_closed_set():
    data = json.loads((REPO / RES_REL).read_text(encoding="utf-8"))
    classes = {row["reason_class"] for row in data["residuals"]}
    assert classes <= {"blocked-by", "user-ruling", "needs-research"}
    d002 = [row for row in data["residuals"] if row["path"] == "docs/SPLITUNIFY_SPEC.D-002.md"]
    assert len(d002) == 1 and d002[0]["id"] == "DOCROT2-RESID-D002-STRUCTURAL-RED"

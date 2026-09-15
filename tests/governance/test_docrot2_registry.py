"""DOCROT2 Task 1.1 — 活文件類別登記（scripts/live_doc_registry_check.sh／_update.sh）。

測什麼：`docs/DOCROT2_TODO.md` Task 1.1 驗證欄之 fixture 逐條 rc 對照，外加邊界。
fixture 形態：於 tmp 建獨立 git repo（含最小 `scripts/live_doc_registry.json` 與 `scripts/fact_keys.json`），
在其中執行真實 repo 之包裝腳本；腳本以 cwd 之 git 根判定 repo，故不觸及本 repo 工作樹。
（TODO 路徑欄原寫 `tests/governance/fixtures/docrot2/` 靜態目錄；改為測試內建構 tmp repo，
 以免靜態 fixture 本身又落入本 repo 之活文件清冊——具名偏離，交 D2A 審碼輪。）
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
CHECK = REPO / "scripts" / "live_doc_registry_check.sh"
UPDATE = REPO / "scripts" / "live_doc_registry_update.sh"
REAL_REGISTRY = REPO / "scripts" / "live_doc_registry.json"


def _base_registry() -> dict:
    reg = json.loads(REAL_REGISTRY.read_text(encoding="utf-8"))
    reg["exact"] = []
    reg["prefix"] = [
        ["docs/Archived/", "HIST"],
        ["docs/site/", "HIST"],
        ["templates/", "LIVE-CONTRACT"],
        ["白話說明/", "LIVE-PLAIN"],
        ["白話說明/Archived/", "HIST"],
    ]
    return reg


def _mk_repo(tmp_path: Path, files: dict, *, registry: dict | None = None,
             status_scope: list | None = None, stage: bool = True) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    (root / "scripts").mkdir(exist_ok=True)
    reg = registry if registry is not None else _base_registry()
    (root / "scripts" / "live_doc_registry.json").write_text(
        json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fk = {"_schema": {"status_scope": status_scope if status_scope is not None else []}}
    (root / "scripts" / "fact_keys.json").write_text(json.dumps(fk), encoding="utf-8")
    if stage:
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    return root


def _run(script: Path, *args: str, cwd: Path):
    return subprocess.run(["bash", str(script), *args], cwd=str(cwd),
                          capture_output=True, text=True)


def _with_exact(reg: dict, *pairs) -> dict:
    reg = dict(reg)
    reg["exact"] = [list(p) for p in pairs]
    return reg


# ---------------------------------------------------------------- Task 1.1 驗證欄


def test_unregistered_path_rc1(tmp_path):
    root = _mk_repo(tmp_path, {"docs/NEW_THING.md": "x\n"})
    r = _run(CHECK, "--path", "docs/NEW_THING.md", cwd=root)
    assert r.returncode == 1, r.stderr
    assert "未登記" in r.stderr


def test_registered_handoff_path_rc0(tmp_path):
    reg = _with_exact(_base_registry(), ("HANDOFF.md", "LIVE-HANDOFF"))
    root = _mk_repo(tmp_path, {"HANDOFF.md": "x\n"}, registry=reg)
    r = _run(CHECK, "--path", "HANDOFF.md", cwd=root)
    assert r.returncode == 0, r.stderr
    assert "LIVE-HANDOFF" in r.stdout


def test_path_in_two_classes_rc1(tmp_path):
    reg = _with_exact(_base_registry(), ("docs/A_SPEC.md", "LIVE-SPEC"), ("docs/A_SPEC.md", "OTHER-DORMANT"))
    root = _mk_repo(tmp_path, {"docs/A_SPEC.md": "x\n"}, registry=reg)
    r = _run(CHECK, "--all", cwd=root)
    assert r.returncode == 1
    assert "重複登記" in r.stderr


def test_archived_spec_listed_as_live_spec_rc1(tmp_path):
    reg = _with_exact(_base_registry(), ("docs/Archived/OLD_SPEC.md", "LIVE-SPEC"))
    root = _mk_repo(tmp_path, {"docs/Archived/OLD_SPEC.md": "x\n"}, registry=reg)
    r = _run(CHECK, "--all", cwd=root)
    assert r.returncode == 1
    assert "歷史類 prefix" in r.stderr


def test_nested_doc_unclassified_rc1(tmp_path):
    root = _mk_repo(tmp_path, {"docs/reviews/r.md": "x\n"})
    r = _run(CHECK, "--all", cwd=root)
    assert r.returncode == 1
    assert "docs/reviews/r.md" in r.stderr


def test_templates_live_doc_unregistered_rc1(tmp_path):
    reg = _base_registry()
    reg["prefix"] = [p for p in reg["prefix"] if p[0] != "templates/"]
    root = _mk_repo(tmp_path, {"templates/T.md": "x\n"}, registry=reg)
    r = _run(CHECK, "--all", cwd=root)
    assert r.returncode == 1
    assert "templates/T.md" in r.stderr


def test_excluded_site_listed_as_live_rc1(tmp_path):
    reg = _with_exact(_base_registry(), ("docs/site/x.md", "LIVE-PLAIN"))
    root = _mk_repo(tmp_path, {"docs/site/x.md": "x\n"}, registry=reg)
    r = _run(CHECK, "--all", cwd=root)
    assert r.returncode == 1


def test_one_registered_path_removed_rc1(tmp_path):
    reg = _with_exact(_base_registry(), ("docs/GONE.md", "OTHER-DORMANT"))
    root = _mk_repo(tmp_path, {"docs/KEEP.md": "x\n"}, registry=_with_exact(reg, ("docs/GONE.md", "OTHER-DORMANT"), ("docs/KEEP.md", "OTHER-DORMANT")))
    r = _run(CHECK, "--all", cwd=root)
    assert r.returncode == 1
    assert "docs/GONE.md" in r.stderr


def test_status_scope_outside_registry_rc1(tmp_path):
    reg = _with_exact(_base_registry(), ("HANDOFF.md", "LIVE-HANDOFF"))
    root = _mk_repo(tmp_path, {"HANDOFF.md": "x\n"}, registry=reg, status_scope=["HANDOFF.md", "docs/UNREG.md"])
    r = _run(CHECK, "--all", cwd=root)
    assert r.returncode == 1
    assert "docs/UNREG.md" in r.stderr


def test_current_tree_rc0():
    r = _run(CHECK, "--all", cwd=REPO)
    assert r.returncode == 0, r.stderr


def test_new_top_level_spec_add_rc0_then_duplicate_rc1(tmp_path):
    root = _mk_repo(tmp_path, {"docs/NEW_SPEC.md": "x\n"})
    r = _run(UPDATE, "--add", "docs/NEW_SPEC.md", cwd=root)
    assert r.returncode == 0, r.stderr
    reg = json.loads((root / "scripts" / "live_doc_registry.json").read_text(encoding="utf-8"))
    assert ["docs/NEW_SPEC.md", "LIVE-SPEC"] in reg["exact"]
    r2 = _run(UPDATE, "--add", "docs/NEW_SPEC.md", cwd=root)
    assert r2.returncode == 1
    assert _run(CHECK, "--all", cwd=root).returncode == 0


# ---------------------------------------------------------------- 邊界


def test_nested_doc_add_defaults_to_dormant(tmp_path):
    root = _mk_repo(tmp_path, {"docs/reviews/r_SPEC.md": "x\n"})
    r = _run(UPDATE, "--add", "docs/reviews/r_SPEC.md", cwd=root)
    assert r.returncode == 0, r.stderr
    reg = json.loads((root / "scripts" / "live_doc_registry.json").read_text(encoding="utf-8"))
    assert ["docs/reviews/r_SPEC.md", "OTHER-DORMANT"] in reg["exact"]


def test_prefix_covered_add_is_noop(tmp_path):
    root = _mk_repo(tmp_path, {"白話說明/新看板.md": "x\n"})
    before = (root / "scripts" / "live_doc_registry.json").read_bytes()
    r = _run(UPDATE, "--add", "白話說明/新看板.md", cwd=root)
    assert r.returncode == 0
    assert (root / "scripts" / "live_doc_registry.json").read_bytes() == before


def test_archived_log_exact_beats_live_plain_prefix(tmp_path):
    reg = _with_exact(_base_registry(), ("白話說明/治理進度日誌.md", "LOG"))
    root = _mk_repo(tmp_path, {"白話說明/治理進度日誌.md": "x\n", "白話說明/Archived/a.md": "x\n"}, registry=reg)
    assert "LOG" in _run(CHECK, "--path", "白話說明/治理進度日誌.md", cwd=root).stdout
    assert "HIST" in _run(CHECK, "--path", "白話說明/Archived/a.md", cwd=root).stdout


def test_out_of_scope_paths_rc0(tmp_path):
    root = _mk_repo(tmp_path, {"handoffs/x.md": "x\n", "tests/y.md": "y\n"})
    assert _run(CHECK, "--path", "handoffs/x.md", cwd=root).returncode == 0
    assert _run(CHECK, "--path", "tests/y.md", cwd=root).returncode == 0
    assert _run(CHECK, "--all", cwd=root).returncode == 0


def test_add_out_of_scope_rc1(tmp_path):
    root = _mk_repo(tmp_path, {"handoffs/x.md": "x\n"})
    assert _run(UPDATE, "--add", "handoffs/x.md", cwd=root).returncode == 1


def test_symlink_in_scope_rc1(tmp_path):
    reg = _with_exact(_base_registry(), ("docs/real.md", "OTHER-DORMANT"), ("docs/link.md", "OTHER-DORMANT"))
    root = _mk_repo(tmp_path, {"docs/real.md": "x\n"}, registry=reg, stage=False)
    os.symlink("real.md", root / "docs" / "link.md")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    r = _run(CHECK, "--all", cwd=root)
    assert r.returncode == 1
    assert "symlink" in r.stderr


def test_newline_in_filename_not_split(tmp_path):
    name = "docs/odd\nname.md"
    reg = _with_exact(_base_registry(), (name, "OTHER-DORMANT"))
    root = _mk_repo(tmp_path, {name: "x\n"}, registry=reg)
    r = _run(CHECK, "--all", cwd=root)
    assert r.returncode == 0, r.stderr


def test_new_unregistered_md_staged_rc1(tmp_path):
    root = _mk_repo(tmp_path, {"docs/KEEP.md": "x\n"}, registry=_with_exact(_base_registry(), ("docs/KEEP.md", "OTHER-DORMANT")))
    subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"], check=True)
    (root / "docs" / "NEW.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "docs/NEW.md"], check=True)
    r = _run(CHECK, "--staged", cwd=root)
    assert r.returncode == 1
    assert "docs/NEW.md" in r.stderr


def test_registry_not_json_rc1(tmp_path):
    root = _mk_repo(tmp_path, {"docs/A.md": "x\n"})
    (root / "scripts" / "live_doc_registry.json").write_text("{not json", encoding="utf-8")
    r = _run(CHECK, "--all", cwd=root)
    assert r.returncode == 1
    assert "JSON" in r.stderr


def test_class_flags_keyset_must_equal_class_enum(tmp_path):
    reg = _base_registry()
    del reg["class_flags"]["LOG"]
    root = _mk_repo(tmp_path, {"docs/A.md": "x\n"}, registry=reg)
    assert _run(CHECK, "--all", cwd=root).returncode == 1


# ================================================================ Task 1.3 — rows_source／rows_filter
# fixture 形態同上：tmp 內建 scripts/（生成器副本＋註冊表＋來源 JSON）與 git 宿主根，
# 生成器以副本所在目錄之父為 repo，故不觸及本 repo 工作樹。

GEN = REPO / "scripts" / "gen_fact_key_blocks.sh"
GUARD = REPO / "scripts" / "factkey_write_guard.sh"

_FK_MIN_SCHEMA = {
    "status_enum": ["停手", "進行中", "未開工"],
    "status_keys": ["src-a"],
    "status_scope": ["docs/"],
    "status_scope_grandfathered": ["docs/__none__.md"],
}
# 識別碼刻意與來源順序反向（Z 在 A 前）：LC_ALL=C 排序會把 A 排前，序號欄才保得住來源順序
_SRC_A = {"target": "docs/a.md", "columns": ["序", "識別碼", "狀態", "下一步"],
          "rows": [["001", "Z-9", "進行中", "做 Z"], ["002", "Z-1", "停手", "—"]]}
_SRC_B = {"target": "docs/b.md", "columns": ["序", "識別碼", "狀態", "下一步"],
          "rows": [["001", "A-1", "未開工", "做 A"], ["002", "A-2", "停手", "—"]]}
_ROSTER_HEAD = ["| 序 | 家族 |", "|---|---|"]


def _fk_sandbox(tmp_path: Path, keys: dict, *, source=None, schema_extra: dict | None = None) -> Path:
    root = tmp_path / "fk"
    (root / "scripts").mkdir(parents=True)
    (root / "docs").mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    shutil.copy2(GEN, root / "scripts" / GEN.name)
    reg = {"_schema": {**_FK_MIN_SCHEMA, **(schema_extra or {})}, **keys}
    (root / "scripts" / "fact_keys.json").write_text(
        json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if source is not None:
        _set_source(root, source)
    for k, v in keys.items():
        (root / v["target"]).write_text(
            f"# host\n\n<!-- BEGIN GENERATED: {k} -->\n<!-- END GENERATED: {k} -->\n", encoding="utf-8")
    return root


def _set_source(root: Path, source) -> None:
    (root / "scripts" / "src.json").write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")


def _clean_env(extra: dict | None = None) -> dict:
    env = {k: v for k, v in os.environ.items() if k != "GOVB1_FACTKEY_ROOT"}
    env.update(extra or {})
    return env


def _fk(root: Path, *args: str, env_extra: dict | None = None):
    env = _clean_env({"GOVB1_FACTKEY_ROOT": str(root), **(env_extra or {})})
    return subprocess.run(["bash", str(root / "scripts" / GEN.name), *args],
                          cwd=str(root), capture_output=True, text=True, env=env)


def _block(root: Path, key: str, rel: str) -> list:
    lines = (root / rel).read_text(encoding="utf-8").splitlines()
    i = lines.index(f"<!-- BEGIN GENERATED: {key} -->")
    j = lines.index(f"<!-- END GENERATED: {key} -->")
    return lines[i + 1:j]


def _roster(**over) -> dict:
    k = {"target": "docs/r.md", "columns": ["序", "家族"], "render": "table",
         "rows_source": {"file": "scripts/src.json", "path": ["fam", "active"]}}
    k.update(over)
    return k


def _filter(**over) -> dict:
    k = {"target": "docs/f.md", "columns": ["序", "識別碼", "下一步"], "render": "table",
         "rows_filter": {"source_keys": ["src-a", "src-b"], "status_column": "狀態",
                         "allow": ["進行中", "未開工"]}}
    k.update(over)
    return k


def _fam(*names) -> dict:
    return {"fam": {"active": list(names)}}


# ---------------------------------------------------------------- Task 1.3 驗證欄


def test_rows_source_string_array_rc0(tmp_path):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster()}, source=_fam("zeta", "alpha"))
    assert _fk(root, "--write").returncode == 0
    r = _fk(root, "--check")
    assert r.returncode == 0, r.stderr
    assert _block(root, "roster", "docs/r.md") == _ROSTER_HEAD + ["| 001 | zeta |", "| 002 | alpha |"]


def test_rows_source_changed_without_write_rc1(tmp_path):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster()}, source=_fam("zeta", "alpha"))
    assert _fk(root, "--write").returncode == 0
    _set_source(root, _fam("zeta"))
    r = _fk(root, "--check")
    assert r.returncode != 0
    assert "FACTKEY DRIFT: roster" in r.stderr, r.stderr
    # 訊息須指向使用者要改的註冊表，不得洩出物化暫存檔路徑
    assert "scripts/fact_keys.json" in r.stderr and "gen_fact_key_blocks." not in r.stderr, r.stderr


def test_rows_source_value_is_object_rc1(tmp_path):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster(rows_source={"file": "scripts/src.json", "path": ["fam"]})},
                       source=_fam("codex"))
    r = _fk(root, "--check")
    assert r.returncode != 0
    assert "非字串陣列" in r.stderr, r.stderr


def test_rows_source_absolute_path_rc1(tmp_path):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster(rows_source={"file": "/etc/hosts", "path": ["x"]})})
    r = _fk(root, "--check")
    assert r.returncode != 0
    assert "絕對路徑" in r.stderr, r.stderr


def test_rows_filter_selects_open_rows_rc0(tmp_path):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "src-b": _SRC_B, "flt": _filter()})
    assert _fk(root, "--write").returncode == 0
    r = _fk(root, "--check")
    assert r.returncode == 0, r.stderr
    assert _block(root, "flt", "docs/f.md") == [
        "| 序 | 識別碼 | 下一步 |", "|---|---|---|",
        "| 01-001 | Z-9 | 做 Z |",      # source_keys 順序：src-a 先
        "| 02-001 | A-1 | 做 A |",      # 停手列（Z-1、A-2）不入
    ]


def test_rows_filter_unknown_status_value_rc1(tmp_path):
    flt = _filter(rows_filter={"source_keys": ["src-a"], "status_column": "狀態", "allow": ["進行中", "幽靈狀態"]})
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "flt": flt})
    r = _fk(root, "--check")
    assert r.returncode != 0
    assert "幽靈狀態" in r.stderr and "status_enum" in r.stderr, r.stderr


# ---------------------------------------------------------------- Task 1.3 邊界


def test_rows_source_empty_array_zero_rows_rc0(tmp_path):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster()}, source=_fam())
    assert _fk(root, "--write").returncode == 0
    assert _fk(root, "--check").returncode == 0
    assert _block(root, "roster", "docs/r.md") == _ROSTER_HEAD


def test_rows_source_array_with_number_rc1(tmp_path):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster()}, source={"fam": {"active": ["codex", 3]}})
    r = _fk(root, "--check")
    assert r.returncode != 0 and "非字串陣列" in r.stderr, r.stderr


def test_rows_source_with_static_rows_rc1(tmp_path):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster(rows=[["001", "x"]])}, source=_fam("x"))
    r = _fk(root, "--check")
    assert r.returncode != 0 and "並存" in r.stderr, r.stderr


@pytest.mark.parametrize("bad", ["../src.json", "scripts/../scripts/src.json", "scripts//src.json", "./scripts/src.json"])
def test_rows_source_dot_or_empty_segments_rc1(tmp_path, bad):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster(rows_source={"file": bad, "path": ["fam", "active"]})},
                       source=_fam("x"))
    r = _fk(root, "--check")
    assert r.returncode != 0 and "空路徑段" in r.stderr, r.stderr


def test_rows_source_symlink_file_rc1(tmp_path):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster(rows_source={"file": "scripts/link.json", "path": ["fam", "active"]})},
                       source=_fam("x"))
    os.symlink("src.json", root / "scripts" / "link.json")
    r = _fk(root, "--check")
    assert r.returncode != 0 and "symlink" in r.stderr, r.stderr


def test_rows_source_parent_dir_symlink_outside_repo_rc1(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "src.json").write_text(json.dumps(_fam("x")), encoding="utf-8")
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster(rows_source={"file": "ext/src.json", "path": ["fam", "active"]})})
    os.symlink(str(outside), root / "ext")
    r = _fk(root, "--check")
    assert r.returncode != 0 and "repo 外" in r.stderr, r.stderr


def test_rows_source_missing_key_path_rc1(tmp_path):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster(rows_source={"file": "scripts/src.json", "path": ["fam", "nope"]})},
                       source=_fam("x"))
    r = _fk(root, "--check")
    assert r.returncode != 0 and "不存在" in r.stderr, r.stderr


def test_rows_source_over_999_elements_rc1(tmp_path):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster()}, source=_fam(*[f"f{i}" for i in range(1000)]))
    r = _fk(root, "--check")
    assert r.returncode != 0 and "999" in r.stderr, r.stderr


def test_rows_filter_first_column_must_be_seq_rc1(tmp_path):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "src-b": _SRC_B, "flt": _filter(columns=["識別碼", "下一步"])})
    r = _fk(root, "--check")
    assert r.returncode != 0 and "首欄為『序』" in r.stderr, r.stderr


def test_rows_filter_source_missing_column_rc1(tmp_path):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "src-b": _SRC_B, "flt": _filter(columns=["序", "識別碼", "負責人"])})
    r = _fk(root, "--check")
    assert r.returncode != 0 and "缺欄" in r.stderr and "負責人" in r.stderr, r.stderr


def test_rows_filter_unknown_source_key_rc1(tmp_path):
    flt = _filter(rows_filter={"source_keys": ["src-a", "nope"], "status_column": "狀態", "allow": ["進行中"]})
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "flt": flt})
    r = _fk(root, "--check")
    assert r.returncode != 0 and "不存在：nope" in r.stderr, r.stderr


def test_rows_filter_chained_filter_rc1(tmp_path):
    flt2 = _filter(target="docs/g.md", rows_filter={"source_keys": ["flt"], "status_column": "狀態", "allow": ["進行中"]})
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "src-b": _SRC_B, "flt": _filter(), "flt2": flt2})
    r = _fk(root, "--check")
    assert r.returncode != 0 and "串接" in r.stderr, r.stderr


@pytest.mark.parametrize("mode", ["emit", "--check", "--write"])
def test_all_three_data_paths_materialize_fail_closed(tmp_path, mode):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster(rows_source={"file": "scripts/src.json", "path": ["fam"]})},
                       source=_fam("x"))
    r = _fk(root) if mode == "emit" else _fk(root, mode)
    assert r.returncode != 0 and "非字串陣列" in r.stderr, r.stderr


def test_emit_path_carries_materialized_rows(tmp_path):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster()}, source=_fam("zeta"))
    r = _fk(root)
    assert r.returncode == 0, r.stderr
    assert "| 001 | zeta |" in r.stdout


@pytest.mark.parametrize("good", [True, False])
def test_materialize_tempdir_removed(tmp_path, good):
    tdir = tmp_path / "tmpd"
    tdir.mkdir()
    path = ["fam", "active"] if good else ["fam"]
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster(rows_source={"file": "scripts/src.json", "path": path})},
                       source=_fam("x"))
    if good:
        assert _fk(root, "--write").returncode == 0
    r = _fk(root, "--check", env_extra={"TMPDIR": str(tdir)})
    assert (r.returncode == 0) is good, r.stderr
    assert list(tdir.iterdir()) == []


def test_help_does_not_read_derived_rows(tmp_path):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster(rows_source={"file": "/etc/hosts", "path": ["x"]})})
    assert _fk(root, "--help").returncode == 0


def test_write_guard_treats_rows_source_file_as_managed(tmp_path):
    root = _fk_sandbox(tmp_path, {"src-a": _SRC_A, "roster": _roster()}, source=_fam("zeta", "alpha"))
    shutil.copy2(GUARD, root / "scripts" / GUARD.name)
    (root / "scripts" / "other.json").write_text("{}", encoding="utf-8")
    assert _fk(root, "--write").returncode == 0
    _set_source(root, _fam("zeta"))
    guard = lambda rel: subprocess.run(["bash", str(root / "scripts" / GUARD.name), rel], cwd=str(root),
                                       capture_output=True, text=True, env=_clean_env())
    r = guard("scripts/src.json")
    assert r.returncode == 2, r.stdout + r.stderr
    assert guard("scripts/other.json").returncode == 0      # 對照：非來源檔不受管


# ================================================================ Task 1.2 — 狀態遷入與即時切換

PRE_CUTOVER = "600c968b"          # 切換前 HEAD；§E 歷史專區指標所指之 commit
_REASONS = {"blocked-by", "user-ruling", "needs-research"}
_D2_COLS = ["序", "識別碼", "狀態", "權威路徑", "下一步"]
_D2_VALUES = ["未開工", "進行中", "部分完成", "待審", "停手", "狀態未確認", "已完成"]


class _Unmapped(ValueError):
    """一次性遷移對照未涵蓋之字面（TODO Task 1.2 要點 1：換算 fail-closed）。"""


def _map_batch_cell(cell: str) -> str:
    if cell.startswith("✅ 完成") or cell.startswith("✅ **完成**"):
        return "已完成"
    raise _Unmapped(cell)


def _map_task_heading(rest: str) -> str:
    if rest.startswith("✅ **已完成"):
        return "已完成"
    raise _Unmapped(rest)


def _map_residual(id_cell: str, reason_cell: str):
    if "（原文，保留供對照）" in id_cell:
        return None                                   # 不登記：整列刪除＋歷史專區指標
    if "~~" in id_cell and "已關閉" in id_cell:
        return "已完成"
    if "已關閉" in reason_cell and "剩餘之半" in reason_cell:
        return "部分完成"
    if "~~" not in id_cell and reason_cell.strip() in _REASONS:
        return "未開工"
    raise _Unmapped(f"{id_cell} ｜ {reason_cell}")


def _migrate(todo_text: str) -> dict:
    """回傳 {key: [(識別碼, 狀態)]}，順序＝原文順序。"""
    out = {"splitunify-batch-status": [], "splitunify-task-status": [], "splitunify-residual-status": []}
    sec = None
    for ln in todo_text.splitlines():
        if ln.startswith("## "):
            sec = "B" if ln.startswith("## §B") else "C9" if ln.startswith("## §C-9") else \
                  "E" if ln.startswith("## §E") else None
            continue
        if sec == "B" and re.match(r"^\| \*\*B[0-9]", ln):
            cells = ln.split("|")
            out["splitunify-batch-status"].append((cells[1].strip().strip("*"), _map_batch_cell(cells[3].strip())))
        elif sec == "C9" and re.match(r"^### Task 9\.", ln):
            m = re.match(r"^### (Task 9\.[0-9]+[a-z]?) (.*)$", ln)
            out["splitunify-task-status"].append((m.group(1), _map_task_heading(m.group(2))))
        elif sec == "E" and ln.startswith("| ") and not ln.startswith("| ID "):
            cells = ln.split("|")
            st = _map_residual(cells[1], cells[3])
            if st is not None:
                out["splitunify-residual-status"].append((re.search(r"`([^`]+)`", cells[1]).group(1), st))
    return out


def _git_show(spec: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), "show", spec], capture_output=True, text=True, check=True).stdout


def _real_reg() -> dict:
    return json.loads((REPO / "scripts" / "fact_keys.json").read_text(encoding="utf-8"))


def test_splitunify_status_cutover_rows_equal_migration_of_pre_cutover_text():
    mapped = _migrate(_git_show(f"{PRE_CUTOVER}:docs/SPLITUNIFY_TODO.md"))
    reg = _real_reg()
    for key, pairs in mapped.items():
        assert pairs, f"{key} 遷移結果為空 ⇒ 解析錨點失準"
        assert [(r[1], r[2]) for r in reg[key]["rows"]] == pairs, key


def test_status_migration_unmapped_literal_rejected():
    with pytest.raises(_Unmapped):
        _map_batch_cell("🟡 大致完成")
    with pytest.raises(_Unmapped):
        _map_task_heading("🔨 **施工中**")
    with pytest.raises(_Unmapped):
        _map_residual("`X-1`", "待定")
    text = _git_show(f"{PRE_CUTOVER}:docs/SPLITUNIFY_TODO.md").replace("| ✅ 完成 |", "| 🟡 大致完成 |", 1)
    with pytest.raises(_Unmapped):
        _migrate(text)


def test_splitunify_todo_migrated_columns_carry_no_status_literal():
    text = (REPO / "docs" / "SPLITUNIFY_TODO.md").read_text(encoding="utf-8")
    sec = None
    seen = {"B": 0, "C9": 0, "E": 0}
    in_block = False
    for ln in text.splitlines():
        if ln.startswith("<!-- BEGIN GENERATED: ") or ln.startswith("<!-- END GENERATED: "):
            in_block = ln.startswith("<!-- BEGIN")
            continue
        if in_block:
            continue                                  # 生成區塊內之表列不是手寫欄
        if ln.startswith("## "):
            sec = "B" if ln.startswith("## §B") else "C9" if ln.startswith("## §C-9") else \
                  "E" if ln.startswith("## §E") else None
            continue
        if sec == "B" and ln.startswith("| Batch "):
            assert "狀態" not in ln, ln
        if sec == "B" and re.match(r"^\| \*\*B[0-9]", ln):
            seen["B"] += 1
            assert "✅" not in ln.split("|")[3] and "完成" not in ln.split("|")[3], ln
        if sec == "C9" and ln.startswith("### Task 9."):
            seen["C9"] += 1
            assert "✅" not in ln and "已完成" not in ln, ln
        if sec == "E" and ln.startswith("| ") and not ln.startswith("| ID "):
            seen["E"] += 1
            cells = ln.split("|")
            assert re.fullmatch(r" `[A-Za-z0-9-]+` ", cells[1]), cells[1]
            assert "已關閉" not in cells[3] and "✅" not in cells[3], cells[3]
    assert seen == {"B": 12, "C9": 7, "E": 15}, seen
    assert "（原文，保留供對照）" not in text


def test_su_resid3_history_pointer_resolves_to_original_row():
    text = (REPO / "docs" / "SPLITUNIFY_TODO.md").read_text(encoding="utf-8")
    pat = re.compile(json.loads(REAL_REGISTRY.read_text(encoding="utf-8"))["history_pointer_regex"])
    hist = text.split("<!-- HISTORY-BEGIN -->", 1)[1].split("<!-- HISTORY-END -->", 1)[0]
    lines = [ln for ln in hist.splitlines() if ln.strip()]
    assert lines and all(pat.match(ln) for ln in lines), lines
    sha = re.search(r"commit `([0-9a-f]+)`", [ln for ln in lines if "：SU-RESID-3 →" in ln][0]).group(1)
    assert "`SU-RESID-3`（原文，保留供對照）" in _git_show(f"{sha}:docs/SPLITUNIFY_TODO.md")


def test_real_tree_check_rc0_and_docrot2_keys_declared():
    reg = _real_reg()
    assert set(reg["_schema"]["docrot2_status_keys"]) == {
        "splitunify-batch-status", "splitunify-task-status", "splitunify-residual-status",
        "docrot2-batch-status", "handoff-pending"}
    assert not set(reg["_schema"]["docrot2_status_keys"]) & set(reg["_schema"]["status_keys"])
    r = subprocess.run(["bash", str(GEN), "--check"], cwd=str(REPO), capture_output=True, text=True, env=_clean_env())
    assert r.returncode == 0, r.stderr


def test_b63_ticket_row_and_ticket_universe_rc0():
    t = _real_reg()["governance-ticket-sot"]
    rows = [r for r in t["rows"] if r[t["columns"].index("票")] == "B-63"]
    assert len(rows) == 1
    assert rows[0][t["columns"].index("狀態")] == "部分完成"
    assert rows[0][t["columns"].index("狀態依據")].startswith("還缺：")
    r = subprocess.run(["bash", str(REPO / "scripts" / "ticket_universe.sh"), "--check"], cwd=str(REPO),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def _d2key(target: str, *rows, columns=None) -> dict:
    return {"target": target, "columns": list(columns or _D2_COLS), "render": "table", "rows": [list(x) for x in rows]}


def _d2_sandbox(tmp_path: Path, keys: dict, **schema_over) -> Path:
    schema = {"status_enum": sorted(set(_FK_MIN_SCHEMA["status_enum"]) | set(_D2_VALUES) | {"✅", "收案"}),
              "docrot2_status_keys": list(keys), "docrot2_status_values": list(_D2_VALUES), **schema_over}
    return _fk_sandbox(tmp_path, {"src-a": _SRC_A, **keys}, schema_extra=schema)


def test_docrot2_status_id_token_boundary_b9_vs_b9a_rc0(tmp_path):
    root = _d2_sandbox(tmp_path, {
        "d2-a": _d2key("docs/da.md", ("010", "B9", "已完成", "docs/x.md §B", "—")),
        "d2-b": _d2key("docs/db.md", ("010", "B9A", "進行中", "docs/x.md §B", "做 A"))})
    assert _fk(root, "--write").returncode == 0
    r = _fk(root, "--check")
    assert r.returncode == 0, r.stderr


def test_same_id_in_two_status_keys_rc1(tmp_path):
    root = _d2_sandbox(tmp_path, {
        "d2-a": _d2key("docs/da.md", ("010", "B9A", "已完成", "docs/x.md §B", "—")),
        "d2-b": _d2key("docs/db.md", ("010", "B9A", "進行中", "docs/x.md §B", "做 A"))})
    r = _fk(root, "--check")
    assert r.returncode != 0 and "重複" in r.stderr and "B9A" in r.stderr, r.stderr


@pytest.mark.parametrize("val", ["✅", "收案"])
def test_completed_batch_row_value_outside_completed_set_rc1(tmp_path, val):
    root = _d2_sandbox(tmp_path, {"d2-a": _d2key("docs/da.md", ("010", "B1", val, "docs/x.md §B", "—"))})
    r = _fk(root, "--check")
    assert r.returncode != 0 and "不在 docrot2_status_values" in r.stderr, r.stderr


@pytest.mark.parametrize("nxt, msg", [("—", "佔位符"), ("", "下一步為空")])
def test_open_row_next_step_must_be_actionable_rc1(tmp_path, nxt, msg):
    root = _d2_sandbox(tmp_path, {"d2-a": _d2key("docs/da.md", ("010", "D2B", "未開工", "docs/x.md §B", nxt))})
    r = _fk(root, "--check")
    assert r.returncode != 0 and msg in r.stderr, r.stderr


def test_docrot2_key_also_in_status_keys_rc1(tmp_path):
    root = _d2_sandbox(tmp_path, {"d2-a": _d2key("docs/da.md", ("010", "D2B", "進行中", "docs/x.md §B", "做"))},
                       status_keys=["src-a", "d2-a"])
    r = _fk(root, "--check")
    assert r.returncode != 0 and "不得同時列於" in r.stderr, r.stderr


def test_docrot2_second_column_must_be_id_rc1(tmp_path):
    k = _d2key("docs/da.md", ("010", "D2B", "進行中", "docs/x.md §B", "做"), columns=["序", "批次", "狀態", "權威路徑", "下一步"])
    root = _d2_sandbox(tmp_path, {"d2-a": k})
    r = _fk(root, "--check")
    assert r.returncode != 0 and "第二欄『識別碼』" in r.stderr, r.stderr


def test_docrot2_values_outside_status_enum_rc1(tmp_path):
    root = _d2_sandbox(tmp_path, {"d2-a": _d2key("docs/da.md", ("010", "D2B", "進行中", "docs/x.md §B", "做"))},
                       docrot2_status_values=_D2_VALUES + ["幽靈狀態"])
    r = _fk(root, "--check")
    assert r.returncode != 0 and "幽靈狀態" in r.stderr, r.stderr


def test_docrot2_unregistered_key_rc1(tmp_path):
    root = _d2_sandbox(tmp_path, {"d2-a": _d2key("docs/da.md", ("010", "D2B", "進行中", "docs/x.md §B", "做"))},
                       docrot2_status_keys=["d2-a", "nope"])
    r = _fk(root, "--check")
    assert r.returncode != 0 and "未註冊 key：nope" in r.stderr, r.stderr


def test_real_committee_roster_block_equals_active_stampers():
    fam = json.loads((REPO / "scripts" / "governance_families.json").read_text(encoding="utf-8"))["active_stampers"]
    lines = (REPO / "docs" / "MULTI_AGENT_ORCHESTRATION.md").read_text(encoding="utf-8").splitlines()
    i = lines.index("<!-- BEGIN GENERATED: committee-roster -->")
    j = lines.index("<!-- END GENERATED: committee-roster -->")
    assert lines[i + 1:j] == _ROSTER_HEAD + [f"| {n:03d} | {f} |" for n, f in enumerate(fam, 1)]

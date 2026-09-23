"""FKPERF 入口切換與 mutation 重定向驗收（docs/FKPERF_SPEC.md Task 4.1、4.2）。

入口 `scripts/gen_fact_key_blocks.sh` 改薄包裝後：路徑字面型消費端（`_managed()`、pre-commit 遷移觸發式、
E-028 引用）須改指核心；「只改核心」時產出端與 pre-commit 照樣觸發。實作前本檔應為紅。
"""
from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.governance import _fkperf_oracle as fo

REPO = Path(__file__).resolve().parents[2]
ENTRY = REPO / "scripts" / "gen_fact_key_blocks.sh"
CORE_REL = "scripts/_gen_fact_key_blocks.py"
CORE = REPO / CORE_REL
C5_MSG = "gen_fact_key_blocks: 缺 python3 → fail-closed"


def _run(argv, cwd: Path, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, env=env or dict(os.environ))


def _precommit_trigger_pattern() -> str:
    src = (REPO / "scripts" / "git_hooks" / "pre-commit").read_text(encoding="utf-8")
    m = re.search(r"grep -qiE '([^']*gen_fact_key_blocks[^']*)'", src)
    assert m, "pre-commit 遷移判定觸發式錨點漂移"
    return m.group(1)


def _break_core(root: Path) -> None:
    (root / CORE_REL).write_text('raise RuntimeError("broken core")\n', encoding="utf-8")


def _mutation_map() -> list:
    """Task 4.2 之對照表（原破壞語意 → 核心中之對應錨點），置於 test_govb1_factkey_gen.py。
    每列鍵：`test_ref`（耦合行 `檔名:行`）、`core_anchor`、`core_mutant`、`red_test`（mutant 下應紅之 pytest node id）、
    `fail_substr`（`red_test` 中被破壞性質之斷言訊息，mutant 那次輸出須含之）。"""
    mod = importlib.import_module("tests.governance.test_govb1_factkey_gen")
    table = getattr(mod, "FKPERF_MUTATION_MAP")
    assert table, "對照表為空"
    return table


# ---------------------------------------------------------------- 邊界（Task 4.1）

def test_boundary_26_missing_python3_fails_closed(tmp_path: Path) -> None:
    """Task 4.1 邊界①：PATH 中無 python3 ⇒ 入口 rc=1 且印 C-5 訊息。"""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for tool in ("bash", "sh", "env", "dirname", "cat", "jq", "git", "awk", "sed", "grep", "sort", "tr", "wc"):
        real = subprocess.run(["/usr/bin/which", tool], capture_output=True, text=True).stdout.strip()
        if real:
            (fake_bin / tool).symlink_to(real)
    env = dict(os.environ, PATH=str(fake_bin))
    r = _run([str(fake_bin / "bash"), str(ENTRY), "--check"], REPO, env)
    assert r.returncode == 1, r.stderr
    assert r.stderr.splitlines()[0] == C5_MSG, r.stderr


def test_boundary_27_entry_is_thin_wrapper_and_parses() -> None:
    """Task 4.1 邊界②：入口以 `bash -n` 通過語法檢查，且為 exec python3 核心之薄包裝。"""
    assert _run(["bash", "-n", str(ENTRY)], REPO).returncode == 0
    src = ENTRY.read_text(encoding="utf-8")
    assert re.search(r'^\s*exec python3 .*_gen_fact_key_blocks\.py', src, re.M), "入口不是 exec python3 核心之薄包裝"


def test_boundary_28_e028_citation_to_core_comment_line_rejected(tmp_path: Path) -> None:
    """Task 4.1 邊界③：E-028 引用改指核心之註解行（第 1 行 shebang）⇒ 既有「引用指向註解行即拒」判定照樣擋。"""
    fo.build_current_tree(tmp_path)
    p = tmp_path / "scripts" / "fact_keys.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    key = data["_schema"]["enforcement_keys"][0]
    hit = False
    for row in data[key]["rows"]:
        for j, cell in enumerate(row):
            if f"{CORE_REL}:" in cell:
                row[j] = re.sub(rf"{re.escape(CORE_REL)}:\d+", f"{CORE_REL}:1", cell)
                hit = True
    assert hit, "E-028 引用尚未改指核心"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    r = _run(["bash", "scripts/gen_fact_key_blocks.sh", "--check"], tmp_path)
    assert r.returncode != 0 and "註解" in r.stderr, r.stderr


# ---------------------------------------------------------------- 邊界（Task 4.2）

def test_boundary_29_mutation_anchors_unique_in_core() -> None:
    """Task 4.2 邊界①：對照表之每個核心錨點在核心中恰出現一次（出現兩次即紅）。"""
    src = CORE.read_text(encoding="utf-8")
    for row in _mutation_map():
        assert src.count(row["core_anchor"]) == 1, row


def test_boundary_30_mutants_compile(tmp_path: Path) -> None:
    """Task 4.2 邊界②：每個 mutant 須先過 `python3 -m py_compile`，語法錯誤之 mutant 不算有效 mutation。"""
    src = CORE.read_text(encoding="utf-8")
    for i, row in enumerate(_mutation_map()):
        mutant = tmp_path / f"m{i}.py"
        mutant.write_text(src.replace(row["core_anchor"], row["core_mutant"], 1), encoding="utf-8")
        r = _run(["python3", "-m", "py_compile", str(mutant)], tmp_path)
        assert r.returncode == 0, (row, r.stderr)


# ---------------------------------------------------------------- Task 4.1／4.2 驗證

def test_managed_set_includes_core_and_broken_core_is_caught(tmp_path: Path) -> None:
    """Task 4.1 驗證①③：核心被改壞後，以核心路徑呼叫產出端守衛 ⇒ rc≠0；還原後 rc=0。"""
    fo.build_current_tree(tmp_path)
    guard = ["bash", "scripts/factkey_write_guard.sh", CORE_REL]
    good = (tmp_path / CORE_REL).read_bytes()
    _break_core(tmp_path)
    assert _run(guard, tmp_path).returncode != 0
    (tmp_path / CORE_REL).write_bytes(good)
    assert _run(guard, tmp_path).returncode == 0


def test_precommit_migration_trigger_includes_core() -> None:
    """Task 4.1 驗證②：pre-commit 遷移判定觸發式命中核心路徑（只暫存核心即觸發）。"""
    pat = _precommit_trigger_pattern()
    r = subprocess.run(["grep", "-qiE", pat], input=CORE_REL + "\n", capture_output=True, text=True)
    assert r.returncode == 0, pat


def test_e028_citation_points_into_core() -> None:
    """Task 4.1 改法④：E-028 之實作位置引用改指核心，且不再引用入口之行號。"""
    data = json.loads((REPO / "scripts" / "fact_keys.json").read_text(encoding="utf-8"))
    key = data["_schema"]["enforcement_keys"][0]
    rows = [r for r in data[key]["rows"] if r and r[0] == "E-028"]
    assert rows, "找不到 E-028 列"
    cell = " ".join(rows[0])
    assert f"{CORE_REL}:" in cell and "gen_fact_key_blocks.sh:" not in cell, cell


COUPLED_FILE = "test_govb1_factkey_gen.py"


def test_coupling_map_covers_every_bash_source_line() -> None:
    """Task 4.2 驗證：對照表之耦合處集合＝以 grep 列舉之讀寫 bash 原始碼行（集合相等）。
    掃描限 `test_govb1_factkey_gen.py`（其 `GEN`＝`gen_fact_key_blocks.sh`）：其餘檔之 `_mutate(`／`GEN.read_text`
    指向別的腳本（r5 grok P1-03 實測 13 行誤中）；另斷言他檔無直讀生成器原始碼之行。
    `def _mutate(` 定義行本身不算耦合處。"""
    table = {row["test_ref"] for row in _mutation_map()}
    src = (REPO / "tests" / "governance" / COUPLED_FILE).read_text(encoding="utf-8")
    assert re.search(r'^GEN = REPO / "scripts" / "gen_fact_key_blocks\.sh"$', src, re.M), "GEN 指向漂移"
    listed = {f"{COUPLED_FILE}:{n}" for n, line in enumerate(src.splitlines(), 1)
              if re.search(r"(?<!def )_mutate\(|GEN\.read_text", line)}
    assert table == listed, (sorted(listed - table), sorted(table - listed))
    for p in sorted((REPO / "tests" / "governance").glob("test_*.py")):
        if p.name != COUPLED_FILE and not p.name.startswith("test_fkperf_"):
            assert not re.search(r'gen_fact_key_blocks\.(sh|py)"\)\.read_text', p.read_text(encoding="utf-8")), p.name


_MUTATE_PRECONDITION = "mutation 目標字串不存在"  # test_govb1_factkey_gen._mutate 之前置斷言訊息


def _assertion_diagnostic(stdout: str) -> str:
    """pytest 失敗診斷中以 `AssertionError` 起頭之連續 `E ` 行區塊（r7 codex／grok P1：Captured stdout 等處之同字面不算）。
    2026-09-24 主委實跑五例：性質斷言失敗（單行／多行訊息）命中；print 同字面後他斷言失敗、前置斷言失敗、
    RuntimeError 帶同字面皆不命中。"""
    blocks, cur = [], []
    for line in stdout.splitlines():
        if re.match(r"^E\s", line):
            cur.append(line)
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    return "\n".join("\n".join(b) for b in blocks if "AssertionError" in b[0])


def test_fail_substr_only_counts_in_assertion_diagnostic() -> None:
    """鑑別力（r7 codex／grok P1 之反例）：`fail_substr` 只出現在 Captured stdout、失敗斷言為他句 ⇒ 不算命中；
    改由目標斷言失敗 ⇒ 命中。"""
    phrase = "拿掉排序輸出未變"
    printed = ("F\n_ test _\n    def test_x():\n>       assert 1 == 0, \"別的斷言\"\n"
               "E   AssertionError: 別的斷言\nE   assert 1 == 0\n"
               "----- Captured stdout call -----\n" + phrase + "\n= 1 failed in 0.02s =\n")
    target = ("F\n_ test _\n>       assert a != b, \"" + phrase + "\"\n"
              "E   AssertionError: " + phrase + "\nE   assert 'a' != 'a'\n= 1 failed in 0.02s =\n")
    assert phrase in printed and phrase not in _assertion_diagnostic(printed)
    assert phrase in _assertion_diagnostic(target)


def test_every_mutation_map_row_turns_its_red_test_red(tmp_path: Path) -> None:
    """Task 4.2 驗證（r5 codex／grok P1-03）：對照表每一列於隔離樹把核心之 `core_anchor` 換成 `core_mutant`，
    跑該列 `red_test`（pytest node id，驗被破壞之性質者）⇒ rc=1；還原後同一 node ⇒ rc=0。
    紅須由**被破壞之性質**造成（r6 codex／grok P1-02；r7 收緊）：mutant 那次之 `AssertionError` 診斷區塊（`E ` 行，
    不含 Captured stdout）須含該列 `fail_substr`（性質斷言之訊息）、
    不含 `_mutate` 前置斷言訊息、摘要恰 `1 failed` 且無 error（setup／import／fixture 例外同為 rc=1，須排除）。
    可編譯但無語意之 mutant（例：`core_mutant == core_anchor`）於此即紅。
    環境變數 `FKPERF_MUTATION_RECEIPT` 指定路徑時，逐列寫入收據（列、命令、兩次 rc）。"""
    fo.build_current_tree(tmp_path)
    core = tmp_path / CORE_REL
    good = core.read_text(encoding="utf-8")
    rows_out = []
    for row in _mutation_map():
        assert row["core_mutant"] != row["core_anchor"], row
        assert row["fail_substr"].strip(), row
        cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", row["red_test"]]
        core.write_text(good.replace(row["core_anchor"], row["core_mutant"], 1), encoding="utf-8")
        red = _run(cmd, tmp_path)
        core.write_text(good, encoding="utf-8")
        green = _run(cmd, tmp_path).returncode
        summary = red.stdout.strip().splitlines()[-1] if red.stdout.strip() else ""
        rows_out.append({"test_ref": row["test_ref"], "red_test": row["red_test"], "command": " ".join(cmd),
                         "fail_substr": row["fail_substr"], "mutant_rc": red.returncode, "restored_rc": green,
                         "fail_substr_seen": row["fail_substr"] in _assertion_diagnostic(red.stdout),
                         "precondition_failed": _MUTATE_PRECONDITION in red.stdout,
                         "summary": summary})
        r = rows_out[-1]
        assert (r["mutant_rc"], r["restored_rc"]) == (1, 0), r
        assert r["fail_substr_seen"] and not r["precondition_failed"], r
        assert re.search(r"\b1 failed\b", summary) and "error" not in summary, r
    out = os.environ.get("FKPERF_MUTATION_RECEIPT")
    if out:
        Path(out).write_text(json.dumps({"schema_version": 1, "command": "pytest " + __file__ +
                                         "::test_every_mutation_map_row_turns_its_red_test_red",
                                         "exit_code": 0, "rows": rows_out}, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")


def test_mutation_guard_without_core_in_managed_misses_broken_core(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """鑑別力：把核心自 `_managed()` 拿掉（還原 r1 之洞）⇒ 改壞核心時守衛 rc=0（上一支測試之反例）。"""
    orig = fo.build_current_tree

    def without_core(root: Path) -> None:
        orig(root)
        g = root / "scripts" / "factkey_write_guard.sh"
        g.write_text("\n".join(l for l in g.read_text(encoding="utf-8").splitlines() if CORE_REL not in l) + "\n",
                     encoding="utf-8")

    monkeypatch.setattr(fo, "build_current_tree", without_core)
    fo.build_current_tree(tmp_path)
    _break_core(tmp_path)
    assert _run(["bash", "scripts/factkey_write_guard.sh", CORE_REL], tmp_path).returncode == 0

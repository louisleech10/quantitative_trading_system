"""scripts/affected_from_trace.py：依讀檔／子行程追蹤與改動檔算受影響 nodeid（TEST_SELECTION §5 過渡工具）。"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("affected_from_trace_t", REPO / "scripts" / "affected_from_trace.py")
aft = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aft)  # type: ignore[union-attr]


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "r"
    (root / "scripts").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "docs" / "spec_x.md").write_text("x", encoding="utf-8")
    (root / "scripts" / "reads_spec.sh").write_text("cat docs/spec_x.md\n", encoding="utf-8")
    (root / "scripts" / "calls_reader.sh").write_text("bash scripts/reads_spec.sh\n", encoding="utf-8")
    (root / "scripts" / "unrelated.sh").write_text("echo hi\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    return root


def test_reasons_read_procarg_procscript_transitive(tmp_path: Path) -> None:
    """讀改動檔、命令列含改動檔、執行（遞迴）引用改動檔之腳本 ⇒ 受影響；無關者不選。重跑取最後一筆。"""
    root = _repo(tmp_path)
    trace = tmp_path / "t.jsonl"
    rows = [
        {"nodeid": "t::read", "files": ["docs/spec_x.md"], "procs": []},
        {"nodeid": "t::arg", "files": [], "procs": ["cat docs/spec_x.md"]},
        {"nodeid": "t::script", "files": [], "procs": ["bash scripts/calls_reader.sh --x"]},
        {"nodeid": "t::none", "files": ["pytest.ini"], "procs": ["bash scripts/unrelated.sh"]},
        {"nodeid": "t::rerun", "files": ["docs/spec_x.md"], "procs": []},
        {"nodeid": "t::rerun", "files": [], "procs": []},
        {"nodeid": "tests/test_changed.py::t", "files": [], "procs": []},
        {"nodeid": "t::dirscan", "files": [], "procs": ["grep -rn token docs"]},
        {"nodeid": "t::shell_dirscan", "files": [], "procs": ["bash -c 'grep -rl x docs/'"]},
        {"nodeid": "t::otherdir", "files": [], "procs": ["grep -rn token scripts"]},
        {"nodeid": "t::fullwidth", "files": [], "procs": ["echo '中文　說明' 'a b'"]},
        {"nodeid": "t::cwd_scan", "files": [], "procs": ["grep -r token ../docs"],
         "proc_cwds": [str(root / "scripts")]},
        {"nodeid": "t::cwd_outside", "files": [], "procs": ["grep -r token ../docs"], "proc_cwds": [str(tmp_path)]},
        {"nodeid": "t::old_dotdot", "files": [], "procs": ["grep -r token ../docs"]},
        {"nodeid": "t::shell_cd", "files": [], "procs": ["bash -c 'cd scripts && grep -r token ../docs'"],
         "proc_cwds": [str(root)]},
        {"nodeid": "t::shell_cd_semicolon", "files": [], "procs": ["bash -c 'cd scripts; grep -r token contracts'"],
         "proc_cwds": [str(root)]},
        {"nodeid": "t::shell_cd_nospace", "files": [], "procs": ["bash -c 'true;cd scripts;grep -r token contracts'"],
         "proc_cwds": [str(root)]},
        {"nodeid": "t::shell_pushd_and", "files": [], "procs": ["bash -c 'true&&pushd scripts;grep -r token x'"],
         "proc_cwds": [str(root)]},
    ]
    for r in rows:  # 新式紀錄：call 階段命中、無共用 fixture ⇒ 不擴散
        r.update(setup_files=[], setup_procs=[], shared=[])
    trace.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    res = aft.affected(aft.latest_records([trace]), {"docs/spec_x.md", "tests/test_changed.py"}, root)
    assert res["tests/test_changed.py::t"] == "test-file:tests/test_changed.py"
    assert res["t::read"] == "read:docs/spec_x.md"
    assert res["t::arg"] == "proc-arg:docs/spec_x.md"
    assert res["t::script"].startswith("proc-script:scripts/calls_reader.sh→docs/spec_x.md")
    assert "t::none" not in res and "t::rerun" not in res
    assert res["t::dirscan"] == "proc-dir:docs→docs/spec_x.md"
    assert res["t::shell_dirscan"] == "proc-dir:docs→docs/spec_x.md"
    assert "t::otherdir" not in res
    assert "t::fullwidth" not in res  # 非 ASCII 空白之參數不得無窮遞迴
    # 子行程 cwd：自 scripts/ 掃 ../docs ⇒ 讀到 docs/spec_x.md；cwd 在 repo 外 ⇒ 不屬 repo；無 cwd 之舊紀錄 ⇒ 保守選入
    assert res["t::cwd_scan"] == "proc-dir:docs→docs/spec_x.md"
    assert "t::cwd_outside" not in res
    assert res["t::old_dotdot"].startswith("proc-dir-unresolved")
    assert res["t::shell_cd"].startswith("proc-dir-unresolved")  # shell 內 cd 不經稽核 ⇒ .. 不可知
    assert res["t::shell_cd_semicolon"].startswith("proc-dir-unresolved")  # 分號串接之 cd 後相對目錄亦不可知
    assert res["t::shell_cd_nospace"].startswith("proc-dir-unresolved")  # 無空白串接（true;cd）亦辨識
    assert res["t::shell_pushd_and"].startswith("proc-dir-unresolved")


def test_shared_fixture_dependency_propagates(tmp_path: Path) -> None:
    """setup 階段（共用 fixture 建立）讀改動檔 ⇒ 共用同一非 function 範圍 fixture 之他檔測試亦受影響；call 階段讀者
    不擴散；舊紀錄（無階段資訊）保守以同檔擴散。"""
    root = _repo(tmp_path)
    sess = "session:tests::cfg"
    rows = [
        {"nodeid": "tests/a.py::first", "files": ["docs/spec_x.md"], "procs": [], "setup_files": ["docs/spec_x.md"],
         "setup_procs": [], "shared": [sess]},
        {"nodeid": "tests/b.py::later", "files": [], "procs": [], "setup_files": [], "setup_procs": [],
         "shared": [sess]},
        {"nodeid": "tests/c.py::call_reader", "files": ["docs/spec_x.md"], "procs": [], "setup_files": [],
         "setup_procs": [], "shared": ["module:tests/c.py::m"]},
        {"nodeid": "tests/c.py::sibling", "files": [], "procs": [], "setup_files": [], "setup_procs": [],
         "shared": ["module:tests/c.py::m"]},
        {"nodeid": "tests/d.py::old_style", "files": ["docs/spec_x.md"], "procs": []},
        {"nodeid": "tests/d.py::old_sibling", "files": [], "procs": []},
    ]
    res = aft.affected({r["nodeid"]: r for r in rows}, {"docs/spec_x.md"}, root)
    assert res["tests/b.py::later"] == "shared-fixture:tests/a.py::first"
    assert "tests/c.py::sibling" not in res
    assert res["tests/d.py::old_sibling"] == "same-file-fixture:tests/d.py::old_style"
    # setup 子行程於子目錄掃描（以其 cwd 解析）⇒ 命中屬 setup ⇒ 擴散給共用同一 fixture 之他檔測試
    (root / "scripts" / "contracts").mkdir()
    (root / "scripts" / "contracts" / "rules.json").write_text("{}", encoding="utf-8")
    cwd_rows = [
        {"nodeid": "tests/e.py::first", "files": [], "procs": ["grep -r token contracts"],
         "proc_cwds": [str(root / "scripts")], "setup_files": [], "setup_procs": ["grep -r token contracts"],
         "setup_proc_cwds": [str(root / "scripts")], "shared": [sess]},
        {"nodeid": "tests/f.py::later", "files": [], "procs": [], "proc_cwds": [], "setup_files": [], "setup_procs": [],
         "setup_proc_cwds": [], "shared": [sess]},
    ]
    res2 = aft.affected({r["nodeid"]: r for r in cwd_rows}, {"scripts/contracts/rules.json"}, root)
    assert res2["tests/e.py::first"] == "proc-dir:scripts/contracts→scripts/contracts/rules.json"
    assert res2["tests/f.py::later"] == "shared-fixture:tests/e.py::first"


def test_basename_only_when_unique(tmp_path: Path) -> None:
    """檔名提及只在該檔名於版控檔唯一時算數（避免 config.py 類同名檔誤判）。"""
    root = _repo(tmp_path)
    (root / "a").mkdir()
    (root / "b").mkdir()
    (root / "a" / "config.py").write_text("", encoding="utf-8")
    (root / "b" / "config.py").write_text("", encoding="utf-8")
    (root / "scripts" / "mentions_config.sh").write_text("python -c 'import config.py'\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    pats = aft.mention_patterns({"a/config.py", "docs/spec_x.md"}, aft._tracked(root))
    taint = aft.tainted_scripts(root, aft._tracked(root), pats)
    assert "scripts/mentions_config.sh" not in taint
    assert "scripts/reads_spec.sh" in taint


def test_builtin_session_fixture_not_a_sharing_basis(tmp_path: Path) -> None:
    """pytest 內建 session fixture（空 baseid 之 tmp_path_factory 等）不構成共用依據：與命中者只共用內建者之他檔、同檔
    測試皆不擴散；共用專案 fixture 者照常擴散；命中者 shared 已知而只用內建者 ⇒ 不擴散（2026-11-12 改：原「以同檔計」
    之依據為 setup 依賴可能來自共用 fixture，而 shared 已知無專案共用者，其 setup 依賴只能來自每測試重建之 function
    範圍 fixture，同檔他測試自身紀錄已含）；baseid 非空之同名 fixture 仍算共用依據。"""
    root = _repo(tmp_path)
    tpf, loop = "session:::tmp_path_factory", "session:::event_loop_policy"
    proj = "session:::proj_store"

    def row(nodeid: str, shared: list, hit: bool = False) -> dict:
        f = ["docs/spec_x.md"] if hit else []
        return {"nodeid": nodeid, "files": f, "procs": [], "setup_files": f, "setup_procs": [], "shared": shared}

    rows = [
        row("tests/a.py::first", [tpf, loop, proj], hit=True),
        row("tests/a.py::same_file_builtin_only", [tpf]),
        row("tests/b.py::builtin_only", [tpf, loop]),
        row("tests/c.py::project_shared", [tpf, proj]),
        row("tests/d.py::hit_builtin_only", [tpf], hit=True),
        row("tests/d.py::sib", []),
    ]
    res = aft.affected({r["nodeid"]: r for r in rows}, {"docs/spec_x.md"}, root)
    assert res == {
        "tests/a.py::first": "read:docs/spec_x.md",
        "tests/c.py::project_shared": "shared-fixture:tests/a.py::first",
        "tests/d.py::hit_builtin_only": "read:docs/spec_x.md",
    }
    assert "tests/d.py::sib" not in res
    assert aft._project_shared(["module:tests/e.py::cache", tpf, "session:tests::tmp_path_factory"]) == {
        "module:tests/e.py::cache", "session:tests::tmp_path_factory"}


def test_mentions_in_comments_and_docstrings_do_not_taint(tmp_path: Path) -> None:
    """腳本只在註解或 docstring 提及改動檔 ⇒ 不算依賴（亦不經其傳染）；程式字串常值、引號內之 `#`、`${#x}` 後之
    路徑仍算。"""
    root = _repo(tmp_path)
    s = root / "scripts"
    (s / "doc_only.py").write_text('"""讀 docs/spec_x.md 之說明。"""\n# docs/spec_x.md\nprint(1)\n', encoding="utf-8")
    (s / "calls_doc_only.sh").write_text("python3 scripts/doc_only.py\n", encoding="utf-8")
    (s / "fn_doc.py").write_text('def f():\n    """docs/spec_x.md"""\n    return 1\n', encoding="utf-8")
    (s / "code_str.py").write_text('def f():\n    """說明"""\n    return open("docs/spec_x.md").read()\n',
                                    encoding="utf-8")
    (s / "paren_str.py").write_text('P = (\n    "docs/spec_x.md",\n)\n', encoding="utf-8")
    (s / "sh_comment.sh").write_text("#!/bin/bash\n# reads docs/spec_x.md\necho hi  # docs/spec_x.md\n",
                                     encoding="utf-8")
    (s / "sh_quoted_hash.sh").write_text('echo "a # docs/spec_x.md"\n', encoding="utf-8")
    (s / "sh_len.sh").write_text("n=${#arr[@]}; cat docs/spec_x.md\n", encoding="utf-8")
    # 審碼 r13：docstring 被當資料讀、heredoc 內容、跨行引號、反斜線跳脫之 # ⇒ 仍算依賴
    (s / "doc_reader.py").write_text('"""docs/spec_x.md"""\nfrom pathlib import Path\nprint(Path(__doc__.strip()).read_text())\n',
                                     encoding="utf-8")
    (s / "heredoc_reader.sh").write_text("python3 - <<'PY'\n# docs/spec_x.md\nPY\n", encoding="utf-8")
    (s / "heredoc_tab.sh").write_text("cat <<-EOF\n\t# docs/spec_x.md\n\tEOF\necho done\n", encoding="utf-8")
    (s / "multiline_quote.sh").write_text('X="line1\n# docs/spec_x.md"\ncat "$X"\n', encoding="utf-8")
    (s / "escaped_hash.sh").write_text("echo \\# docs/spec_x.md\n", encoding="utf-8")
    (s / "after_heredoc_comment.sh").write_text("cat <<EOF\nx\nEOF\n# docs/spec_x.md\n", encoding="utf-8")
    (s / "escaped_quote.sh").write_text('echo \\" x\n# docs/spec_x.md\n', encoding="utf-8")  # 跳脫之 " 不開引號
    # 審碼 r14：字串形式之 __doc__ 存取、數字開頭之 heredoc 終止字
    (s / "doc_reader_globals.py").write_text(
        '"""docs/spec_x.md"""\nfrom pathlib import Path\nprint(Path(globals()["__doc__"].strip()).read_text())\n',
        encoding="utf-8")
    (s / "heredoc_digit.sh").write_text("sed 's/^# //' <<'0' | xargs cat\n# docs/spec_x.md\n0\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    taint = aft.tainted_scripts(root, aft._tracked(root),
                                aft.mention_patterns({"docs/spec_x.md"}, aft._tracked(root)))
    for name in ("doc_only.py", "calls_doc_only.sh", "fn_doc.py", "sh_comment.sh", "after_heredoc_comment.sh",
                 "escaped_quote.sh"):
        assert f"scripts/{name}" not in taint, name
    for name in ("code_str.py", "paren_str.py", "sh_quoted_hash.sh", "sh_len.sh", "reads_spec.sh", "calls_reader.sh",
                 "doc_reader.py", "heredoc_reader.sh", "heredoc_tab.sh", "multiline_quote.sh", "escaped_hash.sh",
                 "doc_reader_globals.py", "heredoc_digit.sh"):
        assert f"scripts/{name}" in taint, name


def test_project_never_shadows_builtin_session_fixture_names() -> None:
    """名稱過濾之前提：repo 版控 .py 無同名函式定義（否則根 conftest〔空 baseid〕之同名 fixture 會被誤當內建而不擴散）。"""
    names = "|".join(sorted(aft._BUILTIN_SESSION))
    out = subprocess.run(["git", "-C", str(REPO), "grep", "--untracked", "-nE", rf"def ({names})\(", "--", "*.py"],
                         capture_output=True, text=True)
    assert out.returncode == 1 and not out.stdout, out.stdout


def _old(nodeid: str, hit: bool = False) -> dict:
    """舊式紀錄：無 setup_files／shared（命中一律視為可能來自 setup）。"""
    return {"nodeid": nodeid, "files": ["docs/spec_x.md"] if hit else [], "procs": []}


def test_collect_fills_shared_project_spreads_builtin_only_does_not(tmp_path: Path) -> None:
    """舊紀錄缺 shared ⇒ 以收集檔補：命中者只有內建 fixture ⇒ 同檔他測試不擴散；命中者有專案共用 fixture ⇒ 依其擴散
    給共用者（含他檔），同檔而不共用者不選。紀錄自帶 shared 者優先於收集檔。"""
    root = _repo(tmp_path)
    tpf, mod = "session:::tmp_path_factory", "module:tests/h.py::m"
    recs = {r["nodeid"]: r for r in [
        _old("tests/g.py::hit", hit=True), _old("tests/g.py::sib"),
        _old("tests/g.py::sib_unknown"),  # 收集檔亦無 ⇒ shared 未知；命中者無專案共用 fixture ⇒ 不可能共用 ⇒ 不選
        _old("tests/h.py::hit", hit=True), _old("tests/h.py::user"), _old("tests/h.py::nonuser"),
        _old("tests/k.py::other_file_user"),
        dict(_old("tests/m.py::own_shared"), shared=[]),  # 紀錄自帶 shared=[] ⇒ 不被收集檔之 mod 蓋過
    ]}
    coll = {
        "tests/g.py::hit": {"nodeid": "tests/g.py::hit", "shared": [tpf]},
        "tests/g.py::sib": {"nodeid": "tests/g.py::sib", "shared": [tpf]},
        "tests/h.py::hit": {"nodeid": "tests/h.py::hit", "shared": [tpf, mod]},
        "tests/h.py::user": {"nodeid": "tests/h.py::user", "shared": [mod]},
        "tests/h.py::nonuser": {"nodeid": "tests/h.py::nonuser", "shared": [tpf]},
        "tests/k.py::other_file_user": {"nodeid": "tests/k.py::other_file_user", "shared": [mod]},
        "tests/m.py::own_shared": {"nodeid": "tests/m.py::own_shared", "shared": [mod]},
    }
    res = aft.affected(recs, {"docs/spec_x.md"}, root, coll)
    assert res == {
        "tests/g.py::hit": "read:docs/spec_x.md",
        "tests/h.py::hit": "read:docs/spec_x.md",
        "tests/h.py::user": "shared-fixture:tests/h.py::hit",
        "tests/k.py::other_file_user": "shared-fixture:tests/h.py::hit",
    }


def test_unknown_shared_keeps_same_file_fallback(tmp_path: Path) -> None:
    """命中者 shared 未知（舊紀錄且收集檔無此 nodeid）⇒ 仍以同檔退路擴散；他檔不選。命中者 shared 已知含專案 fixture、
    同檔他測試 shared 未知 ⇒ 該他測試亦以同檔計（不可排除其共用）。"""
    root = _repo(tmp_path)
    mod = "module:tests/q.py::m"
    recs = {r["nodeid"]: r for r in [_old("tests/p.py::hit", hit=True), _old("tests/p.py::sib"),
                                      _old("tests/z.py::far"), _old("tests/q.py::hit", hit=True),
                                      _old("tests/q.py::unknown_sib")]}
    coll = {"tests/z.py::far": {"nodeid": "tests/z.py::far", "shared": []},
            "tests/q.py::hit": {"nodeid": "tests/q.py::hit", "shared": [mod]}}
    res = aft.affected(recs, {"docs/spec_x.md"}, root, coll)
    assert res["tests/p.py::sib"] == "same-file-fixture:tests/p.py::hit"
    assert res["tests/q.py::unknown_sib"] == "same-file-fixture:tests/q.py::hit"
    assert "tests/z.py::far" not in res


def test_import_read_and_import_proc_hits(tmp_path: Path) -> None:
    """import 期讀檔（紀錄或收集檔之 import_files）命中 ⇒ `import-read:`，且不經 fixture 擴散；import 期子行程依
    `_proc_reason` ⇒ `import-proc-*`；import 期無命中者不選。"""
    root = _repo(tmp_path)
    mod = "module:tests/r.py::m"
    new = {"files": [], "procs": [], "setup_files": [], "setup_procs": [], "shared": [mod]}
    recs = {
        "tests/r.py::rec_import": {"nodeid": "tests/r.py::rec_import", **new, "import_files": ["docs/spec_x.md"]},
        "tests/r.py::col_import": {"nodeid": "tests/r.py::col_import", **new},
        "tests/r.py::import_proc": {"nodeid": "tests/r.py::import_proc", **new,
                                    "import_procs": ["bash scripts/calls_reader.sh"], "import_proc_cwds": [str(root)]},
        "tests/s.py::shares_fixture": {"nodeid": "tests/s.py::shares_fixture", **new},
        "tests/s.py::clean": {"nodeid": "tests/s.py::clean", **new, "import_files": ["pytest.ini"]},
    }
    # 舊式紀錄（無 setup_files，執行期命中會一律當 setup 命中）之 import 期命中亦不得經 fixture 擴散
    mod2 = "module:tests/x.py::m2"
    recs["tests/x.py::old_import"] = {"nodeid": "tests/x.py::old_import", "files": [], "procs": [],
                                      "import_files": ["docs/spec_x.md"]}
    recs["tests/x.py::old_sib"] = {"nodeid": "tests/x.py::old_sib", "files": [], "procs": []}
    recs["tests/y.py::old_share"] = {"nodeid": "tests/y.py::old_share", "files": [], "procs": []}
    coll = {"tests/r.py::col_import": {"nodeid": "tests/r.py::col_import", "shared": [mod],
                                       "import_files": ["docs/spec_x.md"]},
            "tests/x.py::old_import": {"nodeid": "tests/x.py::old_import", "shared": [mod2]},
            "tests/y.py::old_share": {"nodeid": "tests/y.py::old_share", "shared": [mod2]}}
    res = aft.affected(recs, {"docs/spec_x.md"}, root, coll)
    assert res["tests/r.py::rec_import"] == "import-read:docs/spec_x.md"
    assert res["tests/r.py::col_import"] == "import-read:docs/spec_x.md"
    assert res["tests/r.py::import_proc"].startswith("import-proc-script:scripts/calls_reader.sh→docs/spec_x.md")
    assert "tests/s.py::shares_fixture" not in res and "tests/s.py::clean" not in res
    assert res["tests/x.py::old_import"] == "import-read:docs/spec_x.md"
    assert "tests/y.py::old_share" not in res and "tests/x.py::old_sib" not in res


def test_collect_only_nodeids_selected(tmp_path: Path) -> None:
    """只在收集檔、無追蹤紀錄之 nodeid：import 讀到改動檔、測試檔本身改動、與 setup 命中者共用專案 fixture ⇒ 皆選；
    無任何命中者不選。CLI `--collect` 摘要列 untraced 數。"""
    root = _repo(tmp_path)
    mod = "module:tests/u.py::m"
    recs = {"tests/u.py::traced_hit": {"nodeid": "tests/u.py::traced_hit", "files": ["docs/spec_x.md"], "procs": [],
                                       "setup_files": ["docs/spec_x.md"], "setup_procs": [], "shared": [mod]}}
    coll_rows = [
        {"nodeid": "tests/v.py::new_import", "shared": [], "import_files": ["docs/spec_x.md"], "import_procs": [],
         "import_proc_cwds": []},
        {"nodeid": "tests/changed_t.py::new_test", "shared": [], "import_files": [], "import_procs": [],
         "import_proc_cwds": []},
        {"nodeid": "tests/w.py::new_fixture_user", "shared": [mod], "import_files": [], "import_procs": [],
         "import_proc_cwds": []},
        {"nodeid": "tests/w.py::new_clean", "shared": [], "import_files": ["pytest.ini"], "import_procs": [],
         "import_proc_cwds": []},
    ]
    coll = {r["nodeid"]: r for r in coll_rows}
    changed = {"docs/spec_x.md", "tests/changed_t.py"}
    res = aft.affected(recs, changed, root, coll, include_untraced=False)
    assert res == {
        "tests/u.py::traced_hit": "read:docs/spec_x.md",
        "tests/v.py::new_import": "import-read:docs/spec_x.md",
        "tests/changed_t.py::new_test": "test-file:tests/changed_t.py",
        "tests/w.py::new_fixture_user": "shared-fixture:tests/u.py::traced_hit",
    }
    # 預設：未因任何理由選入之未追蹤者以 untraced 必跑
    assert aft.affected(recs, changed, root, coll) == {**res, "tests/w.py::new_clean": "untraced"}
    trace, col, chg, out = (tmp_path / n for n in ("t.jsonl", "c.jsonl", "chg.txt", "out.tsv"))
    trace.write_text("".join(json.dumps(r) + "\n" for r in recs.values()), encoding="utf-8")
    col.write_text("".join(json.dumps(r) + "\n" for r in coll_rows), encoding="utf-8")
    chg.write_text("\n".join(sorted(changed)) + "\n", encoding="utf-8")
    cmd = [sys.executable, str(REPO / "scripts" / "affected_from_trace.py"), str(trace), "--changed", str(chg),
           "--out", str(out), "--collect", str(col)]
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "records=1 collected=4 untraced=4 affected=5 affected_excl_untraced=4 " in proc.stdout, proc.stdout
    assert out.read_text(encoding="utf-8").count("\n") == 5
    proc = subprocess.run(cmd + ["--exclude-untraced"], cwd=root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "affected=4 affected_excl_untraced=4 " in proc.stdout and "untraced=4" in proc.stdout, proc.stdout
    assert out.read_text(encoding="utf-8").count("\n") == 4


def test_cached_reader_inheritance(tmp_path: Path) -> None:
    """執行期呼叫到之讀者（他測試紀錄之 reader_files／reader_procs，或收集期讀者表）讀過改動檔或子行程命中 ⇒
    `cached-*`；setup 階段呼叫到者經共用 fixture 擴散；未呼叫該讀者者不選。"""
    root = _repo(tmp_path)
    mod = "module:tests/k1.py::m"
    base = {"files": [], "procs": [], "setup_files": [], "setup_procs": [], "shared": []}
    recs = {
        "tests/k1.py::first": {"nodeid": "tests/k1.py::first", **base, "files": ["docs/spec_x.md"],
                               "reader_files": {"tests/k1.py:5:_load": ["docs/spec_x.md"]},
                               "reader_procs": {"tests/k1.py:9:_proc": ["bash scripts/calls_reader.sh"]},
                               "reader_proc_cwds": {"tests/k1.py:9:_proc": [str(root)]}},
        "tests/k2.py::hit_cache": {"nodeid": "tests/k2.py::hit_cache", **base, "calls": ["tests/k1.py:5:_load"]},
        "tests/k2.py::hit_proc": {"nodeid": "tests/k2.py::hit_proc", **base, "calls": ["tests/k1.py:9:_proc"]},
        "tests/k2.py::early": {"nodeid": "tests/k2.py::early", **base, "calls": ["m.py:3:_early"]},
        "tests/k2.py::other": {"nodeid": "tests/k2.py::other", **base, "calls": ["tests/k1.py:20:_unrelated"]},
        "tests/k3.py::fixture_first": {"nodeid": "tests/k3.py::fixture_first", **base, "shared": [mod],
                                       "calls": ["tests/k1.py:5:_load"], "setup_calls": ["tests/k1.py:5:_load"]},
        "tests/k4.py::fixture_later": {"nodeid": "tests/k4.py::fixture_later", **base, "shared": [mod]},
    }
    readers = {"m.py:3:_early": {"files": ["docs/spec_x.md"], "procs": [], "proc_cwds": []}}
    res = aft.affected(recs, {"docs/spec_x.md"}, root, readers=readers)
    assert res["tests/k2.py::hit_cache"] == "cached-read:docs/spec_x.md←tests/k1.py:5:_load"
    assert res["tests/k2.py::hit_proc"].startswith("cached-proc-script:scripts/calls_reader.sh")
    assert res["tests/k2.py::early"] == "cached-read:docs/spec_x.md←m.py:3:_early"
    assert "tests/k2.py::other" not in res
    assert res["tests/k4.py::fixture_later"] == "shared-fixture:tests/k3.py::fixture_first"
    tables = tmp_path / "t.jsonl"
    tables.write_text(json.dumps({"readers": readers}) + "\n" + json.dumps(recs["tests/k2.py::early"]) + "\n",
                      encoding="utf-8")
    assert aft.reader_tables([tables]) == readers
    assert "tests/k2.py::early" not in aft.affected(recs, {"docs/spec_x.md"}, root)  # 無讀者表 ⇒ 無從繼承


def test_executed_files_narrow_import_reads(tmp_path: Path) -> None:
    """有 executed_files 與模組表：起點＝執行到 ∪ 存取屬性之模組，沿 import 期存取邊（再匯出鏈）求閉包；閉包內模組
    import 期讀到改動檔 ⇒ import-read-exec，原始碼即改動檔 ⇒ accessed；不在閉包者（含 import 閉包含之但未執行／未存取）
    不選；直接（測試模組／conftest 本身）import 期讀檔仍選且不擴散；執行到改動 .py ⇒ executed；執行判定之命中經共用
    fixture 擴散；無 executed_files 或無表 ⇒ 退回閉包。"""
    root = _repo(tmp_path)
    mod = "module:tests/e2.py::m"
    base = {"files": [], "procs": [], "setup_files": [], "setup_procs": [], "shared": [],
            "import_files": ["docs/spec_x.md"], "import_direct_files": [], "import_direct_procs": []}
    recs = {
        "tests/e1.py::runs_m": {"nodeid": "tests/e1.py::runs_m", **base, "executed_files": ["momentum/m.py"]},
        "tests/e1.py::not_m": {"nodeid": "tests/e1.py::not_m", **base, "executed_files": ["momentum/other.py"]},
        # 只存取再匯出模組 re 之屬性；re 於 import 時取 m 之資料（mod_access 邊 re→m）⇒ 經閉包到 m
        "tests/e1.py::via_reexport": {"nodeid": "tests/e1.py::via_reexport", **base, "executed_files": [],
                                      "accessed_modules": ["momentum/re.py"]},
        "tests/e1.py::reads_const_src": {"nodeid": "tests/e1.py::reads_const_src", **base, "executed_files": [],
                                         "import_files": [], "accessed_modules": ["momentum/consts.py"]},
        "tests/e1.py::accessed_other": {"nodeid": "tests/e1.py::accessed_other", **base, "executed_files": [],
                                        "accessed_modules": ["momentum/other.py"]},
        "tests/e1.py::old": {"nodeid": "tests/e1.py::old", "files": [], "procs": [], "setup_files": [],
                             "setup_procs": [], "shared": [], "import_files": ["docs/spec_x.md"]},
        "tests/e1.py::direct": {"nodeid": "tests/e1.py::direct", **base, "executed_files": [],
                                "import_direct_files": ["docs/spec_x.md"], "shared": [mod]},
        "tests/e2.py::exec_fixture": {"nodeid": "tests/e2.py::exec_fixture", **base, "shared": [mod],
                                      "executed_files": ["momentum/m.py"]},
        "tests/e3.py::fixture_user": {"nodeid": "tests/e3.py::fixture_user", **base, "shared": [mod],
                                      "executed_files": [], "import_files": []},
        "tests/e3.py::runs_changed_py": {"nodeid": "tests/e3.py::runs_changed_py", **base, "import_files": [],
                                         "executed_files": ["momentum/changed.py"]},
    }
    own = {"momentum/m.py": {"files": ["docs/spec_x.md"], "procs": [], "proc_cwds": []}}
    tables = {**own, "__mod_access__": {"momentum/re.py": ["momentum/m.py"]}}
    res = aft.affected(recs, {"docs/spec_x.md", "momentum/changed.py", "momentum/consts.py"}, root, mod_tables=tables)
    assert res["tests/e1.py::runs_m"] == "import-read-exec:docs/spec_x.md←momentum/m.py"
    assert "tests/e1.py::not_m" not in res and "tests/e1.py::accessed_other" not in res
    assert res["tests/e1.py::via_reexport"] == "import-read-exec:docs/spec_x.md←momentum/m.py"
    assert res["tests/e1.py::reads_const_src"] == "accessed:momentum/consts.py"  # 被存取模組之原始碼改動
    assert res["tests/e1.py::old"] == "import-read:docs/spec_x.md"  # 舊紀錄 ⇒ 閉包
    assert res["tests/e1.py::direct"] == "import-read:docs/spec_x.md"
    assert res["tests/e3.py::runs_changed_py"] == "executed:momentum/changed.py"
    assert res["tests/e3.py::fixture_user"] == "shared-fixture:tests/e2.py::exec_fixture"
    res_none = aft.affected(recs, {"docs/spec_x.md"}, root)  # 無讀檔表 ⇒ 閉包
    assert res_none["tests/e1.py::not_m"] == "import-read:docs/spec_x.md"
    trace = tmp_path / "m.jsonl"
    trace.write_text(json.dumps({"mod_own": own}) + "\n" + json.dumps({"mod_access": {"momentum/re.py": ["momentum/m.py"]}})
                     + "\n", encoding="utf-8")
    assert aft.mod_tables([trace]) == tables


def test_import_module_hit(tmp_path: Path) -> None:
    """import 閉包含改動之模組原始碼（紀錄或收集檔之 import_modules）⇒ `import-module:`；不含者不選。"""
    root = _repo(tmp_path)
    base = {"files": [], "procs": [], "setup_files": [], "setup_procs": [], "shared": []}
    recs = {"tests/i1.py::uses": {"nodeid": "tests/i1.py::uses", **base, "import_modules": ["tests/helpers/h.py"]},
            "tests/i2.py::col": {"nodeid": "tests/i2.py::col", **base},
            "tests/i3.py::no": {"nodeid": "tests/i3.py::no", **base, "import_modules": ["tests/helpers/g.py"]}}
    coll = {"tests/i2.py::col": {"nodeid": "tests/i2.py::col", "shared": [], "import_modules": ["tests/helpers/h.py"]}}
    res = aft.affected(recs, {"tests/helpers/h.py"}, root, coll)
    assert res == {"tests/i1.py::uses": "import-module:tests/helpers/h.py",
                   "tests/i2.py::col": "import-module:tests/helpers/h.py"}

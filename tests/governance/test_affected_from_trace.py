"""scripts/affected_from_trace.py：依讀檔／子行程追蹤與改動檔算受影響 nodeid（TEST_SELECTION §5 過渡工具）。"""
from __future__ import annotations

import importlib.util
import json
import subprocess
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
    測試皆不擴散；共用專案 fixture 者照常擴散；命中者只用內建者 ⇒ 以同檔計；baseid 非空之同名 fixture 仍算共用依據。"""
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
        "tests/d.py::sib": "same-file-fixture:tests/d.py::hit_builtin_only",
    }
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
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    taint = aft.tainted_scripts(root, aft._tracked(root),
                                aft.mention_patterns({"docs/spec_x.md"}, aft._tracked(root)))
    for name in ("doc_only.py", "calls_doc_only.sh", "fn_doc.py", "sh_comment.sh", "after_heredoc_comment.sh",
                 "escaped_quote.sh"):
        assert f"scripts/{name}" not in taint, name
    for name in ("code_str.py", "paren_str.py", "sh_quoted_hash.sh", "sh_len.sh", "reads_spec.sh", "calls_reader.sh",
                 "doc_reader.py", "heredoc_reader.sh", "heredoc_tab.sh", "multiline_quote.sh", "escaped_hash.sh"):
        assert f"scripts/{name}" in taint, name


def test_project_never_shadows_builtin_session_fixture_names() -> None:
    """名稱過濾之前提：repo 版控 .py 無同名函式定義（否則根 conftest〔空 baseid〕之同名 fixture 會被誤當內建而不擴散）。"""
    names = "|".join(sorted(aft._BUILTIN_SESSION))
    out = subprocess.run(["git", "-C", str(REPO), "grep", "--untracked", "-nE", rf"def ({names})\(", "--", "*.py"],
                         capture_output=True, text=True)
    assert out.returncode == 1 and not out.stdout, out.stdout

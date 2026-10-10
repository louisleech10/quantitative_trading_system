"""TESTREG Task 1.2 驗收：`scripts/testreg.py bootstrap`（docs/TESTREG_SPEC.md；schema `bootstrap`）。

暫存 git 倉驗 ticket_rule、defaults、paths_file、冪等與改名；真實 repo 驗建檔結果（642 檔全數有 entry、validate rc=0、
收據 handoffs/run_receipts/testreg-bootstrap.json 之 unknown 筆數與 catalog 一致）。實作前全部為紅。
"""
from __future__ import annotations

import hashlib
import json
import subprocess

import pytest

from tests.registry.testreg_helpers import CATALOG_REL, PY, REPO, TESTREG, clean_env, make_repo, schema

PATHS_FILE = schema()["bootstrap"]["paths_file"]
T = "def test_x():\n    assert True\n"


def _sha(p) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _repo(tmp_path):
    r = make_repo(tmp_path, {}, catalog=False, commit=False)
    r.commit("chore: tools")
    return r


def test_bootstrap_writes_defaults_and_paths_file(tmp_path):
    r = _repo(tmp_path)
    r.write("tests/test_a.py", T)
    r.write("tests/sub/test_b.py", T)
    r.commit("test(alpha): add")
    proc = r.run("bootstrap")
    assert proc.returncode == 0, proc.stderr
    cat = r.catalog()
    assert set(cat) == set(schema()["catalog"]["top_level_keys"]) and cat["tombstones"] == []
    tracked = sorted(r.git("ls-files", "tests/test_*.py", "tests/**/test_*.py").split())
    assert sorted(cat["entries"]) == tracked
    d = schema()["bootstrap"]["defaults"]
    for p, e in cat["entries"].items():
        assert e == {"path": p, "ticket": "ALPHA", **d}
    assert r.read(PATHS_FILE) == "".join(t + "\n" for t in tracked)
    assert r.run("validate").returncode == 0


def test_bootstrap_ticket_rule_trailer_subject_unknown(tmp_path):
    """三檔內容須相異：內容相同時 `git log --follow` 會把後加入之檔視為前檔之改名而歸錯票（試作實證）。"""
    r = _repo(tmp_path)
    r.write("tests/test_trailer.py", "def test_trailer():\n    assert 1 + 1 == 2\n")
    r.git("add", "-A")
    r.git("commit", "-q", "-m", "feat: x\n\nTicket-Batch: 20260928-FRAMEPATH/b1")
    r.write("tests/test_subject.py", "def test_subject():\n    assert 'a' * 3 == 'aaa'\n")
    r.commit("test(ffstat): y")
    r.write("tests/test_none.py", "def test_none():\n    assert [1, 2][::-1] == [2, 1]\n")
    r.commit("misc change")
    assert r.run("bootstrap").returncode == 0
    tickets = {p: e["ticket"] for p, e in r.catalog()["entries"].items()}
    assert tickets == {"tests/test_trailer.py": "FRAMEPATH", "tests/test_subject.py": "FFSTAT",
                       "tests/test_none.py": "unknown"}


def test_bootstrap_idempotent(tmp_path):
    r = _repo(tmp_path)
    r.write("tests/test_a.py", T)
    r.commit("test(alpha): add")
    assert r.run("bootstrap").returncode == 0
    a, b = _sha(r.p(CATALOG_REL)), _sha(r.p(PATHS_FILE))
    assert r.run("bootstrap").returncode == 0
    assert (_sha(r.p(CATALOG_REL)), _sha(r.p(PATHS_FILE))) == (a, b)


def test_bootstrap_receipt_counts_unknown(tmp_path):
    r = _repo(tmp_path)
    r.write("tests/test_a.py", T)
    r.write("tests/test_b.py", T)
    r.commit("plain")
    rel = "handoffs/run_receipts/testreg-bootstrap.json"
    assert r.run("bootstrap", "--receipt", rel).returncode == 0
    rc = json.loads(r.read(rel))
    assert rc["entries"] == 2 and rc["unknown"] == 2


def test_boundary_01_first_commit_without_marker_unknown(tmp_path):
    r = _repo(tmp_path)
    r.write("tests/test_a.py", T)
    r.commit("Initial import")
    r.write("tests/test_a.py", T + "\n")
    r.commit("test(later): touch")
    assert r.run("bootstrap").returncode == 0
    assert r.catalog()["entries"]["tests/test_a.py"]["ticket"] == "unknown"


def test_boundary_02_renamed_file_uses_earliest_add(tmp_path):
    r = _repo(tmp_path)
    r.write("tests/test_old.py", T)
    r.commit("test(origin): add")
    r.git("mv", "tests/test_old.py", "tests/test_new.py")
    r.commit("test(mover): rename")
    assert r.run("bootstrap").returncode == 0
    assert r.catalog()["entries"]["tests/test_new.py"]["ticket"] == "ORIGIN"


def test_mutation_ticket_rule_without_follow_misattributes_rename(tmp_path, monkeypatch):
    """mutant：ticket_of 不跟改名（只看現路徑之最早加入提交）⇒ 改名檔被歸為改名提交之票。"""
    import importlib
    testreg = importlib.import_module("scripts.testreg")
    r = _repo(tmp_path)
    r.write("tests/test_old.py", T)
    r.commit("test(origin): add")
    r.git("mv", "tests/test_old.py", "tests/test_new.py")
    r.commit("test(mover): rename")
    assert testreg.ticket_of(r.root, "tests/test_new.py") == "ORIGIN"

    def no_follow(repo_root, path):
        sha = r.git("log", "--diff-filter=A", "--format=%H", "--", path).split()[-1]
        subj = r.git("show", "-s", "--format=%s", sha)
        return subj.split("(")[1].split(")")[0].upper()

    monkeypatch.setattr(testreg, "ticket_of", no_follow)
    assert testreg.ticket_of(r.root, "tests/test_new.py") == "MOVER"
    rc = testreg.main(["--repo", str(r.root), "bootstrap"])
    assert rc == 0 and r.catalog()["entries"]["tests/test_new.py"]["ticket"] == "MOVER"


# ── 真實 repo（Task 1.2 實作後）──────────────────────────────────────────────────────────────────────

def test_real_repo_catalog_complete_and_valid():
    tracked = set(subprocess.run(["git", "-C", str(REPO), "ls-files", "tests/test_*.py", "tests/**/test_*.py"],
                                 capture_output=True, text=True, check=True).stdout.split())
    cat = json.loads((REPO / CATALOG_REL).read_text(encoding="utf-8"))
    assert tracked <= set(cat["entries"])
    boot = (REPO / PATHS_FILE).read_text(encoding="utf-8").splitlines()
    assert boot == sorted(boot) and len(boot) == len(set(boot))
    proc = subprocess.run([PY, str(TESTREG), "validate"], capture_output=True, text=True, env=clean_env(), cwd=str(REPO))
    assert proc.returncode == 0, proc.stderr[-3000:]


def test_real_repo_bootstrap_receipt_matches_catalog():
    rc = json.loads((REPO / "handoffs/run_receipts/testreg-bootstrap.json").read_text(encoding="utf-8"))
    cat = json.loads((REPO / CATALOG_REL).read_text(encoding="utf-8"))
    boot = (REPO / PATHS_FILE).read_text(encoding="utf-8").splitlines()
    assert rc["entries"] == len(boot)
    assert rc["unknown"] == sum(1 for p in boot if cat["entries"].get(p, {}).get("ticket") == "unknown")

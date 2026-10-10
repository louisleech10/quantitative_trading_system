"""TESTREG 驗收測試之共用工具（docs/TESTREG_SPEC.md；TODO manifest docs/manifests/TESTREG.json）。

暫存 git 倉（`make_repo`）：每支測試自建，複製真實之 `scripts/testreg.py`、`scripts/testreg_write_guard.sh`、
`tests/registry/testreg_schema.json`，使 hook 由自身位置推導出之 repo 根即暫存倉；`run` 以真實腳本加 `--repo`。
真實 pytest 子行程（`recorded_pytest`）載入真實記錄器（`-p testreg_recorder_plugin`），產生 ledger 供收據綁定。
枚舉值一律讀 schema（不在測試內另抄）。子行程環境一律去除 TESTREG_PARENT_SESSION（外層 session 之巢狀標記）。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
PY = str(REPO / "venv/bin/python") if (REPO / "venv/bin/python").exists() else sys.executable
TESTREG = REPO / "scripts/testreg.py"
GUARD = REPO / "scripts/testreg_write_guard.sh"
SCHEMA_REL = "tests/registry/testreg_schema.json"
CATALOG_REL = "tests/registry/catalog.json"
PLUGIN_DIR = REPO / "tests/fixtures"
PLUGIN_MOD = "testreg_recorder_plugin"
TOOLS = ("scripts/testreg.py", "scripts/testreg_write_guard.sh", SCHEMA_REL)
GITIGNORE = ".testreg/\n__pycache__/\n.pytest_cache/\ndata_cache/\n"
PYTEST_INI = "[pytest]\ntestpaths = tests\npython_files = test_*.py\nmarkers =\n    slow: s\n"
STRIP_ENV = ("TESTREG_PARENT_SESSION", "PYTEST_ADDOPTS", "PYTEST_CURRENT_TEST", "PYTEST_XDIST_WORKER")


def schema() -> Dict[str, Any]:
    return json.loads((REPO / SCHEMA_REL).read_text(encoding="utf-8"))


def enum(name: str) -> List[Any]:
    return list(schema()["enums"][name])


def classified() -> Dict[str, List[str]]:
    """三欄各取 schema 枚舉之第一個非 unclassified 值（不寫死枚舉字面）。"""
    pick = lambda n: [next(v for v in enum(n) if v != "unclassified")]
    return {"guarantee": pick("charter_category"), "oracle": pick("oracle"), "claim": pick("claim")}


def entry(path: str, **over: Any) -> Dict[str, Any]:
    e = {"path": path, "ticket": "T", **classified(), "disposition": enum("file_disposition")[0],
         "rewrite_targets": [], "disposition_ref": None, "rewrite_receipt": None, "quarantine": []}
    e.update(over)
    return e


def bootstrap_entry(path: str, ticket: str = "T") -> Dict[str, Any]:
    return {"path": path, "ticket": ticket, **json.loads(json.dumps(schema()["bootstrap"]["defaults"]))}


def clean_env(**extra: str) -> Dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in STRIP_ENV}
    env.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@t", "PYTHONDONTWRITEBYTECODE": "1"})
    env.update(extra)
    return env


class TmpRepo:
    def __init__(self, root: Path):
        self.root = root

    def p(self, rel: str) -> Path:
        return self.root / rel

    def write(self, rel: str, text: str) -> None:
        self.p(rel).parent.mkdir(parents=True, exist_ok=True)
        self.p(rel).write_text(text, encoding="utf-8")

    def read(self, rel: str) -> str:
        return self.p(rel).read_text(encoding="utf-8")

    def delete(self, rel: str) -> None:
        self.p(rel).unlink()

    def git(self, *args: str, check: bool = True) -> str:
        proc = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True, env=clean_env())
        if check and proc.returncode != 0:
            raise AssertionError(f"git {args} rc={proc.returncode}: {proc.stderr}")
        return proc.stdout

    def commit(self, msg: str = "c", *paths: str) -> str:
        self.git("add", "-A", *(paths or ["."]))
        self.git("commit", "-q", "--allow-empty", "-m", msg)
        return self.head()

    def head(self) -> str:
        return self.git("rev-parse", "HEAD").strip()

    def stage(self, *rels: str) -> None:
        self.git("add", "-A", "--", *rels)

    def catalog(self) -> Dict[str, Any]:
        return json.loads(self.read(CATALOG_REL))

    def set_catalog(self, cat: Mapping[str, Any]) -> None:
        self.write(CATALOG_REL, json.dumps(cat, ensure_ascii=False, indent=1, sort_keys=True) + "\n")

    def put_entry(self, e: Mapping[str, Any]) -> None:
        cat = self.catalog()
        cat["entries"][e["path"]] = dict(e)
        self.set_catalog(cat)

    def add_tombstone(self, t: Mapping[str, Any]) -> None:
        cat = self.catalog()
        cat["tombstones"].append(dict(t))
        self.set_catalog(cat)

    def write_json(self, rel: str, obj: Any) -> None:
        self.write(rel, json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n")

    def run(self, *args: str, env: Optional[Mapping[str, str]] = None) -> subprocess.CompletedProcess:
        """真實 scripts/testreg.py，`--repo <暫存倉>`。"""
        return subprocess.run([PY, str(TESTREG), "--repo", str(self.root), *args], capture_output=True, text=True,
                              env=dict(env) if env is not None else clean_env(), cwd=str(self.root))

    def hook(self, rel: str, tool: str = "Edit") -> subprocess.CompletedProcess:
        """以 PostToolUse payload 呼叫暫存倉內之 hook 複本（repo 根由 hook 自身位置推導＝暫存倉）。"""
        payload = json.dumps({"tool_name": tool, "tool_input": {"file_path": str(self.p(rel))}})
        return subprocess.run(["bash", str(self.p("scripts/testreg_write_guard.sh"))], input=payload,
                              capture_output=True, text=True, env=clean_env(), cwd=str(self.root))

    def install_precommit(self) -> None:
        hook = self.p(".git/hooks/pre-commit")
        hook.write_text(f"#!/usr/bin/env bash\nexec {PY} scripts/testreg.py check --staged\n", encoding="utf-8")
        hook.chmod(0o755)

    def try_commit(self, msg: str = "c") -> subprocess.CompletedProcess:
        """以暫存倉之 pre-commit（只跑 testreg.py check --staged）嘗試提交暫存區。"""
        return subprocess.run(["git", "-C", str(self.root), "commit", "-q", "-m", msg], capture_output=True,
                              text=True, env=clean_env())

    def ledger_ids(self) -> List[str]:
        d = self.p(".testreg/ledger")
        return sorted(p.name[:-len(".jsonl")] for p in d.glob("*.jsonl")) if d.is_dir() else []

    def ledger(self, session_id: str) -> List[Dict[str, Any]]:
        return [json.loads(l) for l in self.read(f".testreg/ledger/{session_id}.jsonl").splitlines() if l.strip()]


def make_repo(tmp_path: Path, files: Optional[Mapping[str, str]] = None, *, catalog: bool = True,
              commit: bool = True, name: str = "repo") -> TmpRepo:
    """新 git 倉：工具複本＋.gitignore＋pytest.ini＋最小 fact_keys；files 寫入後，catalog=True 時為其中每個測試檔建
    已分類 entry（tombstones 空），commit=True 時提交為 HEAD。"""
    r = TmpRepo(tmp_path / name)
    r.root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(r.root)], check=True, env=clean_env())
    for rel in TOOLS:
        r.p(rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, r.p(rel))
    r.write(".gitignore", GITIGNORE)
    r.write("pytest.ini", PYTEST_INI)
    r.write_json("scripts/fact_keys.json", fact_keys_rows([]))
    for rel, text in (files or {}).items():
        r.write(rel, text)
    if catalog:
        tests = sorted(rel for rel in (files or {}) if is_test_path(rel))
        r.set_catalog({"entries": {t: entry(t) for t in tests}, "tombstones": []})
    if commit:
        r.commit("init")
    return r


def is_test_path(rel: str) -> bool:
    import re
    return re.fullmatch(schema()["formats"]["test_path"], rel) is not None


def fact_keys_rows(rows: Sequence[Sequence[str]]) -> Dict[str, Any]:
    """最小 scripts/fact_keys.json：handoff-pending 與 roadmap-status 兩區塊（欄名同真實檔）。"""
    real = json.loads((REPO / "scripts/fact_keys.json").read_text(encoding="utf-8"))
    hp = {"columns": real["handoff-pending"]["columns"], "rows": [list(r) for r in rows if r[1].startswith("HP-")]}
    rm = {"columns": real["roadmap-status"]["columns"], "rows": [list(r) for r in rows if r[1].startswith("RM-")]}
    return {"handoff-pending": hp, "roadmap-status": rm}


def recorded_pytest(repo: TmpRepo, *args: str, env_extra: Optional[Mapping[str, str]] = None,
                    plugin: bool = True) -> Tuple[subprocess.CompletedProcess, List[str]]:
    """於暫存倉跑真實 pytest（載入真實記錄器）；回傳 (結果, 本次新增之 session_id 清單)。"""
    before = set(repo.ledger_ids())
    env = clean_env(PYTHONPATH=os.pathsep.join([str(PLUGIN_DIR), str(repo.root)]), **(env_extra or {}))
    cmd = [PY, "-m", "pytest", "-p", "no:cacheprovider", "-q"]
    if plugin:
        cmd += ["-p", PLUGIN_MOD]
    proc = subprocess.run([*cmd, *args], capture_output=True, text=True, env=env, cwd=str(repo.root))
    return proc, sorted(set(repo.ledger_ids()) - before)


def test_records(repo: TmpRepo, session_id: str) -> Dict[str, Dict[str, Any]]:
    return {r["nodeid"]: r for r in repo.ledger(session_id) if r.get("kind") == "test"}


test_records.__test__ = False


def session_of(repo: TmpRepo, session_id: str) -> Dict[str, Any]:
    return next(r for r in repo.ledger(session_id) if r.get("kind") == "session")


def apply_patch(repo: TmpRepo, patch_rel: str, reverse: bool = False) -> None:
    repo.git("apply", *(["-R"] if reverse else []), patch_rel)


def write_patch(repo: TmpRepo, rel: str, new_text: str, patch_rel: str) -> str:
    """產生把 rel 由 HEAD 版改為 new_text 之 git diff 補丁並寫至 patch_rel（不改工作樹）；回傳補丁 sha256。"""
    import hashlib
    old = repo.read(rel)
    repo.write(rel, new_text)
    diff = repo.git("diff", "--binary", "--", rel)
    repo.write(rel, old)
    repo.write(patch_rel, diff)
    return hashlib.sha256(diff.encode("utf-8")).hexdigest()


def lines_with(repo: TmpRepo, rel: str, needle: str) -> List[int]:
    return [i for i, l in enumerate(repo.read(rel).splitlines(), 1) if needle in l]


def rule_lines(proc: subprocess.CompletedProcess, rule: str) -> List[str]:
    """stderr 中以規則 id 開頭之列（`<ID> <主體>: <訊息>`）。"""
    return [l for l in proc.stderr.splitlines() if l.startswith(rule + " ")]


def copy_repo(src: TmpRepo, dst_parent: Path, name: str) -> TmpRepo:
    dst = dst_parent / name
    shutil.copytree(src.root, dst, symlinks=True)
    return TmpRepo(dst)

"""FKPERF 語料②：錄製既有沙箱測試之生成器呼叫（docs/FKPERF_SPEC.md Task 0.1 ②；r1 codex P1-03、composer P2-01）。

作 pytest plugin（`-p tests.governance._fkperf_record`，環境 `FKPERF_RECORD_DIR` 指定落點）跑 `RECORD_FILES`：
攔截 `subprocess.run(["bash", <…/gen_fact_key_blocks.sh>, …])`，**呼叫前**把該次沙箱（生成器所在樹、cwd、
`GOVB1_FACTKEY_ROOT`、`TMPDIR` 之最低共同祖先）連同 git 狀態整樹複製，呼叫後記 rc 與首行（rc≠0 取 stderr、rc=0 取
stdout）為預期分支標籤。cwd 或宿主根為 repo 本身者記 `repo_side`，重播時以目前工作樹之 SANDBOX_PATHS 建 repo 側，
不碰真 repo。生成器位元組與目前入口不同者（`_mutate` 之變異本）不錄，記為 skipped。
每一次攔截（錄或略）皆寫入 `log.jsonl`，供「每支以 helper 建沙箱之測試皆有記錄」之機械對證。
"""
from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
ENTRY_NAME = "gen_fact_key_blocks.sh"
RECORD_FILES = ("tests/governance/test_govb1_factkey_gen.py", "tests/governance/test_docrot2_registry.py")
SANDBOX_HELPERS = ("_sandbox", "_mkroot", "_fk_sandbox", "_d2_sandbox")  # SPEC ②所稱之建樹 helper（其包裝者以呼叫圖閉包納入）
ENV_RECORD_DIR = "FKPERF_RECORD_DIR"
_ENV_TRACKED = ("GOVB1_FACTKEY_ROOT", "TMPDIR", "LC_ALL", "LANG", "LC_CTYPE", "PATH")

_counter = [0]


def _forms(path: Path) -> List[str]:
    """同一路徑之字面形：原形、realpath，以及 macOS 之 /private 前綴有無兩形（/var ↔ /private/var、/tmp ↔ /private/tmp）。"""
    out = {str(path), str(path.resolve())}
    for s in list(out):
        if s.startswith("/private/"):
            out.add(s[len("/private"):])
        elif s.startswith(("/var/", "/tmp/")):
            out.add("/private" + s)
    return sorted(out)


def _placeholder(value: str, anchor: Path) -> str:
    pairs = {**{s: "{anchor}" for s in _forms(anchor)}, **{s: "{repo}" for s in _forms(REPO)}}
    for src, dst in sorted(pairs.items(), key=lambda kv: -len(kv[0])):
        value = value.replace(src, dst)
    return value


def _first_line(stream: Any) -> str:
    text = stream.decode("utf-8", "replace") if isinstance(stream, (bytes, bytearray)) else (stream or "")
    return text.splitlines()[0] if text else ""


def _under(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _log(out: Path, entry: Dict[str, Any]) -> None:
    with (out / "log.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _intercept(args: Any, kw: Dict[str, Any], out: Path) -> Optional[Dict[str, Any]]:
    if not (isinstance(args, (list, tuple)) and len(args) >= 2 and args[0] == "bash"
            and Path(str(args[1])).name == ENTRY_NAME):
        return None
    nodeid = os.environ.get("PYTEST_CURRENT_TEST", "").rsplit(" ", 1)[0]
    script = Path(str(args[1]))
    cwd = Path(kw.get("cwd") or os.getcwd())
    env = dict(kw.get("env") or os.environ)
    base = {"nodeid": nodeid, "args": [str(a) for a in args[2:]]}
    if not script.is_absolute():
        script = cwd / script
    if _under(script, REPO):
        _log(out, {**base, "status": "skipped", "reason": "repo-entry"})
        return None
    if script.read_bytes() != (REPO / "scripts" / ENTRY_NAME).read_bytes():
        _log(out, {**base, "status": "skipped", "reason": "mutated"})
        return None
    root_env = env.get("GOVB1_FACTKEY_ROOT")
    root_path = (cwd / root_env) if root_env else cwd
    tmpdir = env.get("TMPDIR") if env.get("TMPDIR") != os.environ.get("TMPDIR") else None
    parts = [script.parent.parent] + [p for p in (cwd, root_path, Path(tmpdir) if tmpdir else None)
                                        if p is not None and not _under(p, REPO)]
    anchor = Path(os.path.commonpath([str(p.resolve()) for p in parts]))
    if not _under(anchor, Path(tempfile.gettempdir())) or len(anchor.relative_to(
            Path(tempfile.gettempdir()).resolve()).parts) < 1:  # 須嚴格位於系統 tmp 之內（不得為 tmp 根本身）
        _log(out, {**base, "status": "skipped", "reason": f"anchor-outside-tmp:{anchor}"})
        return None
    repo_side = _under(cwd, REPO) or _under(root_path, REPO)
    _counter[0] += 1
    dst = out / f"{_counter[0]:04d}"
    shutil.copytree(anchor, dst / "t", symlinks=True)
    base_env = os.environ
    record = {
        **base,
        "status": "recorded",
        "dir": dst.name,
        "script": _placeholder(str(script.resolve()), anchor),
        "cwd": _placeholder(str(cwd.resolve()), anchor),
        "env": {k: _placeholder(v, anchor) for k, v in env.items() if base_env.get(k) != v and k in _ENV_TRACKED},
        "unset": sorted(k for k in _ENV_TRACKED if k in base_env and k not in env),
        "stdin": kw.get("input") if isinstance(kw.get("input"), str) else None,
        "repo_side": repo_side,
        "_anchor": str(anchor),
    }
    return record


def _finish(record: Dict[str, Any], result: Any, out: Path) -> None:
    anchor = Path(record.pop("_anchor"))
    rc = int(result.returncode)
    record["rc"] = rc
    record["first_line"] = _placeholder(_first_line(result.stderr if rc else result.stdout), anchor)
    (out / record["dir"] / "record.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    _log(out, {k: record[k] for k in ("nodeid", "args", "status", "dir")})


def install(out: Path) -> None:
    """於本程序替換 `subprocess.run` 為錄製版（只攔生成器呼叫，其餘原樣轉交）。"""
    orig = subprocess.run

    def run(args: Any, *a: Any, **kw: Any) -> Any:
        record = _intercept(args, kw, out)
        result = orig(args, *a, **kw)
        if record is not None:
            _finish(record, result, out)
        return result

    subprocess.run = run  # type: ignore[assignment]


def pytest_configure(config: Any) -> None:  # pytest plugin hook
    target = os.environ.get(ENV_RECORD_DIR)
    if target:
        Path(target).mkdir(parents=True, exist_ok=True)
        install(Path(target))


def record_all(out: Path) -> Dict[str, Any]:
    """以子程序 pytest 跑 `RECORD_FILES` 並錄製；回傳 {"records": [...], "log": [...], "rc": pytest rc}。
    既有測試本身之紅綠不影響錄製（錄的是生成器之呼叫與輸出）。"""
    out.mkdir(parents=True, exist_ok=True)
    from tests.governance import _fkperf_oracle as fo
    fo.build_current_tree(out / "repo_side", include_tests=False)  # 錄製當下凍結 repo 側（重播不讀活的工作樹）
    env = dict(os.environ, **{ENV_RECORD_DIR: str(out)})
    selected = [f"{rel}::{name}" for rel, names in helper_tests().items() for name in names]  # 只跑建沙箱者（真 repo 慢測試不在語料②）
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p",
                        "tests.governance._fkperf_record", *selected],
                       cwd=str(REPO), env=env, capture_output=True, text=True)
    records = [json.loads((d / "record.json").read_text(encoding="utf-8"))
               for d in sorted(out.iterdir()) if (d / "record.json").is_file()]
    log = [json.loads(line) for line in (out / "log.jsonl").read_text(encoding="utf-8").splitlines()] \
        if (out / "log.jsonl").is_file() else []
    return {"records": records, "log": log, "rc": r.returncode, "tail": r.stdout[-2000:]}


_CACHE: Dict[str, Any] = {}


def recorded() -> Dict[str, Any]:
    """本程序內錄製一次並快取（錄製目錄於系統 tmp，程序結束即刪——2026-09-24 未刪之錄製目錄累積佔滿磁碟）。"""
    if "data" not in _CACHE:
        _CACHE["dir"] = Path(tempfile.mkdtemp(prefix="fkperf_record_"))
        atexit.register(shutil.rmtree, _CACHE["dir"], True)
        _CACHE["data"] = record_all(_CACHE["dir"])
    return _CACHE["data"]


def record_tree(record: Dict[str, Any]) -> Path:
    """錄得之沙箱樹（呼叫前狀態）。"""
    recorded()
    return _CACHE["dir"] / record["dir"] / "t"


def repo_side_tree() -> Path:
    """錄製開始時凍結之 repo 側（目前工作樹之 SANDBOX_PATHS＋receipt，已 git init）。"""
    recorded()
    return _CACHE["dir"] / "repo_side"


def helper_tests() -> Dict[str, List[str]]:
    """以 AST 呼叫圖閉包求：`RECORD_FILES` 中直接或經包裝函式呼叫 `SANDBOX_HELPERS` 之 test 函式（檔 → 函式名）。
    與錄製記錄對證之獨立錨（不依賴錄製本身）。"""
    import ast

    out: Dict[str, List[str]] = {}
    for rel in RECORD_FILES:
        tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
        calls: Dict[str, set] = {}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                calls[node.name] = {n.func.id for n in ast.walk(node)
                                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        users = set(SANDBOX_HELPERS)
        while True:
            grown = users | {name for name, called in calls.items() if called & users}
            if grown == users:
                break
            users = grown
        out[rel] = sorted(name for name in users if name.startswith("test_") and name in calls)
    return out

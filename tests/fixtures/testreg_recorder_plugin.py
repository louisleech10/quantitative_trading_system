"""TESTREG 記錄器（docs/TESTREG_SPEC.md Task 1.3）：每次 pytest session 自動寫 ledger 與增量 summary。

契約：tests/registry/testreg_schema.json 之 `ledger`（session_record／test_record／collect_record／outcome_aggregation／
nested_rule／env_prefixes／argv_norm_drop_dests）與 `summary`。資料位置一律相對 pytest `config.rootpath`
（ledger＝`ledger.dir`、summary＝`summary.path`／`summary.lock`、kline＝`KLINE_REL`、雜湊快取＝`KLINE_CACHE_REL`）；
schema 讀本檔所在 repo 之單一真相源；summary 之形狀驗證共用 `scripts/testreg.py` 之 `validate_shape`（以檔案路徑載入）。

行為約束（SPEC §C）：不改 outcome、執行順序、rc；除 `.testreg/` 外不新增、不改任何檔；記錄器自身之例外一律經
`safe` 攔截並以單行 stderr 告知、不上拋；巢狀 session（環境變數 `TESTREG_PARENT_SESSION` 存在）不寫任何 ledger 檔；
不在每條測試後寫檔（`pytest_sessionfinish` 一次原子寫）。

具名縫（hook 於呼叫當下以模組屬性取用，供 tests/registry/test_testreg_recorder.py 之 mutation 置換）：
`safe`、`is_nested`、`argv_norm`、`sha256_file`、`kline_cache_key`、`kline_sha256`、`aggregate_outcome`、
`write_ledger`、`read_summary`、`summary_lock`、`merge_summary`。

暫存檔命名：`<ledger.dir>/<session_id>.jsonl.tmp-<pid>`（暫存檔＋rename 原子寫）；session 開始時清除 pid 已不存在之
`*.tmp-<pid>`（不清他行程仍存活者，供並行 session）。

kline 雜湊快取檔格式（單一條目）：`{"key": [dev, inode, size, mtime_ns, ctime_ns], "sha256": "<64 hex>"}`。
"""
from __future__ import annotations

import contextlib
import datetime as _dt
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import sysconfig
import uuid
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple

import pytest

PARENT_ENV = "TESTREG_PARENT_SESSION"
KLINE_REL = "data_cache/feature_klines/kline_cache.h5"
KLINE_CACHE_REL = ".testreg/kline_sha_cache.json"
KLINE_CACHE_LOCK_REL = ".testreg/kline_sha_cache.lock"
TMP_INFIX = ".jsonl.tmp-"

_HERE_REPO = Path(__file__).resolve().parents[2]
_SCHEMA_PATH = _HERE_REPO / "tests/registry/testreg_schema.json"
_ADDR = re.compile(r" at 0x[0-9a-fA-F]+")
_S: Dict[str, Any] = {}
_CACHE: Dict[str, Any] = {}


def _schema() -> Dict[str, Any]:
    if "schema" not in _CACHE:
        _CACHE["schema"] = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return _CACHE["schema"]


def _testreg():
    """以檔案路徑載入 scripts/testreg.py（共用 validate_shape；不依 sys.path）。載入期間關閉位元組碼寫入：
    否則首次載入會建 `scripts/__pycache__/`，屬 `.testreg/` 以外之新增檔（SPEC §C、§G ④）。"""
    if "testreg" not in _CACHE:
        spec = importlib.util.spec_from_file_location("_testreg_for_recorder", _HERE_REPO / "scripts/testreg.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod  # dataclass 於定義時查 sys.modules[__module__]
        prev = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.dont_write_bytecode = prev
        _CACHE["testreg"] = mod
    return _CACHE["testreg"]


def safe(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """呼叫 fn；任何例外攔截後以單行 stderr（前綴 `testreg-recorder:`）告知並回傳 None，不上拋。"""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 — 記錄器不得影響被測 session
        msg = " ".join(str(exc).split())[:200]
        sys.stderr.write(f"testreg-recorder: {getattr(fn, '__name__', 'call')} {type(exc).__name__}: {msg}\n")
        return None


def is_nested(environ: Mapping[str, str] = os.environ) -> bool:
    """schema `ledger.nested_rule`：環境變數 TESTREG_PARENT_SESSION 存在 ⇒ True。"""
    return PARENT_ENV in environ


def _jsonable(v: Any) -> Any:
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in sorted(v.items(), key=lambda kv: str(kv[0]))}
    if isinstance(v, os.PathLike):
        return os.fspath(v)
    return _ADDR.sub("", f"<{type(v).__name__}:{v!r}>")


def argv_norm(config: Any) -> str:
    """schema `ledger.session_record.argv_norm`：config.option 全部 dest＝value 去除 `argv_norm_drop_dests`，連同
    config.args（保序）序列化為正規 JSON（sort_keys、無空白）。"""
    drop = set(_schema()["ledger"]["argv_norm_drop_dests"])
    opts = {k: _jsonable(v) for k, v in vars(config.option).items() if k not in drop}
    return json.dumps({"args": [str(a) for a in config.args], "option": opts}, sort_keys=True,
                      separators=(",", ":"), ensure_ascii=False)


def sha256_file(path: Path) -> str:
    """全檔 sha256（hex）。"""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def kline_cache_key(st: os.stat_result) -> Tuple[int, int, int, int, int]:
    """快取鍵＝(dev, inode, size, mtime_ns, ctime_ns)。"""
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _read_kline_cache(path: Path) -> Optional[Dict[str, Any]]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if (isinstance(obj, dict) and set(obj) == {"key", "sha256"} and isinstance(obj["key"], list)
            and len(obj["key"]) == 5 and isinstance(obj["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", obj["sha256"])):
        return obj
    return None


def _atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)


def kline_sha256(rootpath: Path) -> str:
    """schema `ledger.session_record.kline_sha256`：stat→`sha256_file`→stat，兩次鍵不同重試一次，仍不同 ⇒ 字面
    unstable（不寫快取）；檔不存在 ⇒ 字面 absent；快取於獨占鎖內以暫存檔＋rename 原子替換、毀損視同不存在。"""
    p = Path(rootpath) / KLINE_REL
    try:
        st = os.stat(p)
    except FileNotFoundError:
        return "absent"
    cache = Path(rootpath) / KLINE_CACHE_REL
    hit = _read_kline_cache(cache)
    if hit is not None and hit["key"] == list(kline_cache_key(st)):
        return hit["sha256"]
    for _ in range(2):
        before = kline_cache_key(os.stat(p))
        digest = sha256_file(p)
        after = kline_cache_key(os.stat(p))
        if before == after:
            lock = Path(rootpath) / KLINE_CACHE_LOCK_REL
            lock.parent.mkdir(parents=True, exist_ok=True)
            with open(lock, "a+") as fh:
                fcntl.flock(fh, fcntl.LOCK_EX)
                _atomic_write(cache, json.dumps({"key": list(after), "sha256": digest}))
            return digest
    return "unstable"


def _git(root: Path, *args: str) -> bytes:
    proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {args[0]} rc={proc.returncode}")
    return proc.stdout


def diff_digest(root: Path) -> str:
    """schema `ledger.session_record.diff_digest`（validate 重算 mutation 綁定時共用此函式）。"""
    diff = _git(root, "diff", "HEAD", "--binary")
    untracked = sorted(p for p in _git(root, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0") if p)
    if not diff and not untracked:
        return "clean"
    h = hashlib.sha256(diff)
    for rel in untracked:
        f = root / rel.decode("utf-8", "surrogateescape")
        h.update(b"\0" + rel + b"\0")
        h.update(bytes.fromhex(sha256_file(f)) if f.is_file() else b"<non-file>")
    return h.hexdigest()


def _packages_digest() -> str:
    names = set()
    for key in ("purelib", "platlib"):
        d = sysconfig.get_paths().get(key)
        if d and os.path.isdir(d):
            names |= {n for n in os.listdir(d) if n.endswith(".dist-info")}
    return hashlib.sha256("\n".join(sorted(names)).encode("utf-8")).hexdigest()


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _sha(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8", "surrogateescape")).hexdigest()


def session_record(config: Any, session_id: str) -> Dict[str, Any]:
    """依 `ledger.session_record` 計算全部欄位（含 fingerprint 與 duration_class 公式；unstable 時 U＝session_id）。"""
    root = Path(str(config.rootpath))
    sch = _schema()
    try:
        head = _git(root, "rev-parse", "HEAD").decode().strip()
        dd = diff_digest(root)
    except (RuntimeError, OSError):
        head, dd = "0" * 40, "0" * 64
    kline = kline_sha256(root)
    python = f"{os.path.realpath(sys.executable)}|{sys.version}"
    pk = _packages_digest()
    prefixes = tuple(sch["ledger"]["env_prefixes"])
    env = {k: v for k, v in sorted(os.environ.items()) if k.startswith(prefixes)}
    an = argv_norm(config)
    u = session_id if kline == "unstable" else ""
    env_s = json.dumps(env, sort_keys=True, ensure_ascii=False)
    return {"kind": "session", "session_id": session_id, "started": _now(), "head": head, "diff_digest": dd,
            "kline_sha256": kline, "python": python, "packages_digest": pk, "env": env, "argv_norm": an,
            "argv_raw": [str(a) for a in config.invocation_params.args],
            "fingerprint": _sha(head, dd, kline, python, pk, env_s, an, u),
            "duration_class": _sha(kline, python, pk, env_s, u)}


def aggregate_outcome(reports: Mapping[str, Any]) -> Tuple[str, str, bool]:
    """schema `ledger.outcome_aggregation`：{"setup"|"call"|"teardown": 該階段摘要（outcome、wasxfail）} →
    (outcome, phase_failed, teardown_failed)。"""
    s, c, t = reports.get("setup"), reports.get("call"), reports.get("teardown")
    td = bool(t and t["outcome"] == "failed")
    if s and s["outcome"] == "failed":
        return "error", "setup", td
    if c and c["outcome"] == "failed":
        return "failed", "call", td
    if td:
        return "error", "teardown", True
    if s and s["outcome"] == "skipped":
        return ("xfailed" if s["wasxfail"] else "skipped"), "none", False
    if c and c["outcome"] == "skipped" and c["wasxfail"]:
        return "xfailed", "none", False
    if c and c["outcome"] == "passed" and c["wasxfail"]:
        return "xpassed", "none", False
    if c and c["outcome"] == "skipped":
        return "skipped", "none", False
    return "passed", "none", False


def _rel(root: Path, path: str) -> Optional[str]:
    try:
        return Path(path).resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return None


def _excinfo_fields(excinfo: Any, root: Path, test_file: str) -> Dict[str, Any]:
    value = excinfo.value
    cause = getattr(value, "__cause__", None)
    frames: List[str] = []
    origin, fail_line = None, None
    for entry in excinfo.traceback:
        rel = _rel(root, str(entry.path))
        if rel is None or "/_pytest/" in f"/{rel}" or "importlib" in rel:
            continue
        loc = f"{rel}:{entry.lineno + 1}"
        origin = loc
        if rel == test_file:
            fail_line = entry.lineno + 1
        if rel.startswith("tests/"):
            frames.append(loc)
    head = str(value).strip().splitlines()[0][:300] if str(value).strip() else ""
    return {"exception_type": type(value).__name__, "exception_head": head, "exception_origin": origin,
            "fail_line": fail_line, "fail_frames": list(reversed(frames)), "cause": cause}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Any, call: Any):
    outcome = yield
    if not _S.get("active"):
        return
    rep = outcome.get_result()

    def attach() -> None:
        info = {"outcome": rep.outcome, "wasxfail": hasattr(rep, "wasxfail"), "duration": float(rep.duration or 0.0),
                "markers": sorted({m.name for m in item.iter_markers()})}
        if call.excinfo is not None and rep.outcome == "failed":
            info.update(_excinfo_fields(call.excinfo, _S["root"], rep.nodeid.split("::", 1)[0]))
            info.pop("cause", None)
        _S.setdefault("phase_info", {})[(rep.nodeid, rep.when)] = info

    safe(attach)


def test_record(session_id: str, nodeid: str, order: int, reports: Mapping[str, Any],
                rootpath: Path) -> Dict[str, Any]:
    """依 `ledger.test_record` 由三階段摘要組一筆（exception_* 、fail_line、fail_frames、markers）。"""
    outcome, phase, td = aggregate_outcome(reports)
    src = reports.get(phase) if phase in ("setup", "call", "teardown") else None
    exc = src if src and "exception_type" in src else {}
    markers = sorted({m for r in reports.values() for m in r.get("markers", [])})
    return {"kind": "test", "session_id": session_id, "nodeid": nodeid, "order": order, "outcome": outcome,
            "duration_s": round(sum(float(r.get("duration", 0.0)) for r in reports.values()), 6),
            "phase_failed": phase, "exception_type": exc.get("exception_type"),
            "exception_head": exc.get("exception_head"), "exception_origin": exc.get("exception_origin"),
            "fail_line": exc.get("fail_line"), "fail_frames": list(exc.get("fail_frames", [])),
            "teardown_failed": td, "markers": markers}


test_record.__test__ = False  # 名稱以 test_ 開頭，防 pytest 誤收集


def write_ledger(ledger_dir: Path, session_id: str, records: Iterable[Mapping[str, Any]]) -> Path:
    """一次原子寫 `<session_id>.jsonl`（暫存檔＋rename）；回傳最終路徑。"""
    ledger_dir.mkdir(parents=True, exist_ok=True)
    final = ledger_dir / f"{session_id}.jsonl"
    tmp = ledger_dir / f"{session_id}{TMP_INFIX}{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, final)
    return final


def read_summary(path: Path, schema: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """讀 summary；JSON 無法解析、schema_version／k 不符或形狀不符 schema `summary.shape` ⇒ None（視同不存在）。"""
    try:
        obj = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(obj, dict) or obj.get("schema_version") != schema["version"] or obj.get("k") != schema["summary"]["k"]:
        return None
    if _testreg().validate_shape(obj, schema["summary"]["shape"], schema):
        return None
    return obj


def summary_lock(lock_path: Path) -> AbstractContextManager:
    """fcntl.flock 獨占鎖之 context manager。"""

    @contextlib.contextmanager
    def _lock():
        Path(lock_path).parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "a+") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    return _lock()


def _summary_rec(rec: Mapping[str, Any], sess: Mapping[str, Any]) -> Dict[str, Any]:
    return {"session_id": sess["session_id"], "started": sess["started"], "fingerprint": sess["fingerprint"],
            "duration_class": sess["duration_class"], "outcome": rec["outcome"], "duration_s": rec["duration_s"],
            "exception_type": rec["exception_type"], "exception_head": rec["exception_head"]}


def _rebuild(root: Path, schema: Mapping[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    nodes: Dict[str, List[Dict[str, Any]]] = {}
    for f in sorted((root / schema["ledger"]["dir"]).glob("*.jsonl")):
        try:
            lines = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        except (OSError, ValueError):
            continue
        sess = next((x for x in lines if x.get("kind") == "session"), None)
        if sess is None:
            continue
        for rec in lines:
            if rec.get("kind") == "test":
                nodes.setdefault(rec["nodeid"], []).append(_summary_rec(rec, sess))
    return nodes


def merge_summary(rootpath: Path, schema: Mapping[str, Any], records: List[Mapping[str, Any]],
                  session: Mapping[str, Any]) -> None:
    """於 `summary_lock` 內「讀（`read_summary`）→合併（每 nodeid 依 started 保留最近 k 筆）→暫存檔→rename」；
    讀回 None ⇒ 由 ledger 全量重建（同鎖內）。"""
    root = Path(rootpath)
    k = schema["summary"]["k"]
    with summary_lock(root / schema["summary"]["lock"]):
        cur = read_summary(root / schema["summary"]["path"], schema)
        if cur is None:
            nodes = _rebuild(root, schema)
        else:
            nodes = cur["nodes"]
            for rec in records:
                if rec.get("kind") == "test":
                    nodes.setdefault(rec["nodeid"], []).append(_summary_rec(rec, session))
        for nid in list(nodes):
            nodes[nid] = sorted(nodes[nid], key=lambda x: (x["started"], x["session_id"]))[-k:]
        _atomic_write(root / schema["summary"]["path"], json.dumps(
            {"schema_version": schema["version"], "k": k, "nodes": nodes}, ensure_ascii=False, sort_keys=True))


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _cleanup_tmp(ledger: Path) -> None:
    if not ledger.is_dir():
        return
    for p in ledger.iterdir():
        if TMP_INFIX not in p.name:
            continue
        try:
            pid = int(p.name.rsplit("-", 1)[1])
        except ValueError:
            continue
        if not _pid_alive(pid):
            p.unlink()


def _start(session: Any) -> None:
    _S.clear()
    if is_nested(os.environ):
        return
    config = session.config
    sch = _schema()
    root = Path(str(config.rootpath))
    sid = str(uuid.uuid4())
    ledger = root / sch["ledger"]["dir"]
    safe(_cleanup_tmp, ledger)
    rec = session_record(config, sid)
    _S.update(active=True, sid=sid, root=root, ledger=ledger, schema=sch, session=rec, order={}, collects=[],
              phase_info={})
    os.environ[PARENT_ENV] = sid


def pytest_sessionstart(session: Any) -> None:
    """計算 session_record、清除過期暫存檔、設 TESTREG_PARENT_SESSION（巢狀 session 不寫）。"""
    safe(_start, session)


def pytest_runtest_logreport(report: Any) -> None:
    """累積 setup／call／teardown 報告之序號（摘要於 makereport 取得；不寫檔）。"""
    if _S.get("active") and report.nodeid not in _S["order"]:
        _S["order"][report.nodeid] = len(_S["order"])


@pytest.hookimpl(hookwrapper=True)
def pytest_make_collect_report(collector: Any):
    outcome = yield
    if not _S.get("active"):
        return
    rep = outcome.get_result()

    def note() -> None:
        if rep.outcome != "failed":
            return
        path = rep.nodeid.split("::", 1)[0]
        if not re.fullmatch(_schema()["formats"]["test_path"], path):
            return
        exc = None
        call = getattr(rep, "_testreg_excinfo", None)
        etype, ehead = "CollectError", ""
        lr = str(rep.longrepr) if rep.longrepr is not None else ""
        m = re.search(r"^E\s+([A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception)):\s*(.*)$", lr, re.M)
        if m:
            etype, ehead = m.group(1).rsplit(".", 1)[-1], m.group(2)
        elif lr.strip():
            ehead = lr.strip().splitlines()[0]
        _S["collects"].append({"kind": "collect", "session_id": _S["sid"], "path": path, "exception_type": etype,
                               "exception_head": ehead[:300]})
        del exc, call

    safe(note)


def pytest_collectreport(report: Any) -> None:
    """收集失敗由 `pytest_make_collect_report` 記錄（此處不重複）。"""


def _finish() -> None:
    if not _S.get("active"):
        return
    sid = _S["sid"]
    by_node: Dict[str, Dict[str, Any]] = {}
    for (nid, when), info in _S["phase_info"].items():
        by_node.setdefault(nid, {})[when] = info
    tests = [test_record(sid, nid, _S["order"].get(nid, len(_S["order"])), by_node[nid], _S["root"])
             for nid in sorted(by_node, key=lambda n: _S["order"].get(n, 1 << 30))]
    records = [_S["session"], *tests, *_S["collects"]]
    written = safe(write_ledger, _S["ledger"], sid, records)
    if written is not None:
        safe(merge_summary, _S["root"], _S["schema"], tests, _S["session"])


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    """一次原子寫本 session 之 jsonl，並合併 summary。"""
    safe(_finish)

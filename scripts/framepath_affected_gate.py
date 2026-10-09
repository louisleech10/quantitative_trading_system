"""FRAMEPATH 受影響測試閘（SPEC v21 D8、諮詢 r5；v20 D6 之歸屬與錨點防護沿用）：A 組全綠＋B／C 組只跑本批
改動可能影響其結果之 nodeid（測試影響分析），其餘逐項收據；完整性機械比對、失敗逐項與錨點碼態比對歸屬。

流程（單組串行）：
1. A 組＝本票具名驗收（`A_GROUP_BY_PHASE`），須全部 passed（不適用既有紅豁免）。
2. B／C 組：manifest `affected_tests phase=<P>` 所列檔扣 A 組，逐檔 `pytest --collect-only -qq`（rc 須 0，否則拒跑）；
   應跑集合 E 由 `plan` 挑選（S1 處置操作所及／S2 會走被刪或被改分支／S3 靜態輕量檔整檔／必跑／對齊觸發），
   未選者逐項記 `skipped` 封閉理由；C 組（`affected_groups phase=<P> C=…`）排在 B 組之後，只影響順序。
   `--plan` 只產挑選收據（秒級），供執行前估時。
3. 逐檔執行寫 junit xml；結果檔附狀態指紋（repo HEAD、工作樹相對 HEAD 之完整 diff、未追蹤檔清單、該測試檔內容、
   pytest 參數、phase），指紋相同且結果完整才沿用（中斷後接續），否則重跑；pytest rc 非 0／1 ⇒ 該檔視為未完成。
4. 非綠 nodeid 於錨點工作樹重跑同 nodeid；錨點＝本票最晚一筆實作許可之 round_start_head（`.claude/gate/audit.log`，
   與處置驗證器 ⓪ 同一函式），工作樹由本腳本自建（或 `--anchor-worktree` 指定）並驗：HEAD＝錨點、工作樹乾淨、
   生產碼（momentum／api／config）與碼態錨點 6e07e0ad 相同。結果類別＋例外型別＋訊息首行（只遮暫存路徑與位址、
   數字不遮）皆同者歸「HEAD 既有紅」，其餘一律「本批造成」。
5. 通過＝A 組全綠、E 完整、無多出之 nodeid、本批造成＝0。收據寫 `--receipt`。

用法（各批同一命令；批次取自本票最晚實作許可之 batch 欄，phase＝b1→1、b2→2、b3→3、b4→3，收據寫
`handoffs/run_receipts/framepath-b<N>-affected.json`；`--anchor-worktree` 省略則自建於系統暫存）：
  PYTHONPATH=. venv/bin/python scripts/framepath_affected_gate.py
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
MANIFEST_REL = "docs/manifests/FRAMEPATH.json"
CODE_ANCHOR = "6e07e0ad"
PRODUCTION_ROOTS = ("momentum", "api", "config")
A_FILES = (
    "tests/feature_engineering/test_framepath_disposition.py",
    "tests/feature_engineering/test_framepath_cgsa_only.py",
    "tests/feature_engineering/test_framepath_invariance.py",
    "tests/api/test_framepath_api_h5.py",
)
A_GROUP = A_FILES  # 自 B／C 扣除之集合（不分 phase）
A_GROUP_BY_PHASE = {1: A_FILES[:3], 2: A_FILES, 3: A_FILES}
PYTEST_FLAGS = ("-q", "-p", "no:cacheprovider", "-o", "log_cli=false", "--log-level=WARNING", "--tb=short")
RUN_RC_OK = (0, 1)  # pytest：0 全過、1 有測試失敗；其餘（中斷、內部錯誤、用法、無測試）＝未完成


class GateError(RuntimeError):
    """閘之前置不成立（具名拒跑）。"""


def manifest_groups(manifest: Mapping, phase: int) -> Tuple[List[str], List[str]]:
    """(B 組, C 組)：affected_tests phase=P 扣除 A 組；C 組＝affected_groups phase=P C=… 所列（須為 affected 之子集）。"""
    rows = manifest["batch_card"]["risk_mitigation"]
    affected = _row_paths(rows, f"affected_tests phase={phase} ")
    c_rows = [r for r in rows if r.startswith(f"affected_groups phase={phase} C=")]
    if len(c_rows) != 1:
        raise GateError(f"manifest 缺或重複 affected_groups phase={phase} C=…")
    c_group = [p for p in c_rows[0].split("C=", 1)[1].split() if p]
    stray = sorted(set(c_group) - set(affected))
    if stray:
        raise GateError(f"C 組含非 affected_tests 之檔：{stray}")
    rest = [p for p in affected if p not in A_GROUP]
    return [p for p in rest if p not in c_group], [p for p in rest if p in c_group]


def _row_paths(rows: Sequence[str], prefix: str) -> List[str]:
    hits = [r for r in rows if r.startswith(prefix)]
    if len(hits) != 1:
        raise GateError(f"manifest 缺或重複 {prefix.strip()}")
    return [p for p in hits[0][len(prefix):].split() if p]


def junit_results(xml_text: str, test_file: str) -> Dict[str, Dict[str, str]]:
    """junit xml → {nodeid: {"outcome", "type", "message"}}；nodeid 由 classname（模組點路徑＋類別）與 name 重建。"""
    module = test_file[:-3].replace("/", ".")
    out: Dict[str, Dict[str, str]] = {}
    for case in ET.fromstring(xml_text).iter("testcase"):
        cls = case.get("classname", "")
        if not (cls == module or cls.startswith(module + ".")):
            continue
        inner = cls[len(module):].lstrip(".")
        nodeid = "::".join([test_file, *[p for p in inner.split(".") if p], case.get("name", "")])
        outcome, etype, msg = "passed", "", ""
        for tag in ("failure", "error", "skipped"):
            el = case.find(tag)
            if el is not None:
                outcome = "failed" if tag == "failure" else tag
                etype = el.get("type", "") or ""
                msg = el.get("message", "") or (el.text or "")
                break
        out[nodeid] = {"outcome": outcome, "type": etype, "message": msg}
    return out


_MASKS = (
    (re.compile(r"/(?:private/)?(?:var|tmp)/[^\s'\"]+"), "<tmp>"),
    (re.compile(r"0x[0-9a-fA-F]+"), "<hex>"),
)


def failure_identity(result: Mapping[str, str]) -> Tuple[str, str, str]:
    """(結果類別, 例外型別, 正規化訊息首行)；只遮暫存路徑與記憶體位址（每次執行必不同之非語意差異）。數字不遮：
    同一既有紅測試之數值改變即視為本批造成（寧可誤報須人工判讀，不得吞掉數值回歸）。"""
    first = (result.get("message") or "").strip().splitlines()[0] if (result.get("message") or "").strip() else ""
    for pat, rep in _MASKS:
        first = pat.sub(rep, first)
    return result.get("outcome", ""), result.get("type", "") or "", first


def classify(expected: Iterable[str], batch: Mapping[str, Mapping[str, str]],
             anchor: Mapping[str, Mapping[str, str]]) -> Dict[str, object]:
    """完整性與歸屬（純函式）。回傳 {"missing", "unexpected", "caused", "head_red", "passed"}；通過條件見 `verdict`。"""
    exp = list(dict.fromkeys(expected))
    missing = [n for n in exp if n not in batch]
    unexpected = sorted(set(batch) - set(exp))
    caused, head_red, passed = [], [], []
    for n in exp:
        if n not in batch:
            continue
        res = batch[n]
        if res.get("outcome") == "passed":
            passed.append(n)
            continue
        ref = anchor.get(n)
        if ref is not None and failure_identity(ref) == failure_identity(res):
            head_red.append(n)
        else:
            caused.append(n)
    return {"missing": missing, "unexpected": unexpected, "caused": caused, "head_red": head_red, "passed": passed}


def anchor_usable(rc: int, res: Mapping[str, Mapping[str, str]], requested: Sequence[str]) -> Dict[str, Dict[str, str]]:
    """審查 r48：錨點重跑之結果只在 pytest rc ∈ {0,1} 且所請 nodeid 皆有結果時採用；否則整批不採（相關 nodeid
    因錨點無結果而歸本批造成，不得以不完整之錨點吸收）。"""
    if rc not in RUN_RC_OK or set(requested) - set(res):
        return {}
    return {n: dict(res[n]) for n in requested}


def verdict(result: Mapping[str, Sequence[str]], a_failures: Sequence[str], incomplete_files: Sequence[str],
            residual_unexecuted: Sequence[str] = ()) -> bool:
    """通過＝A 組全綠、無未完成檔、無缺、無多出、本批造成＝0、CGSA 殘差定義皆於 A 組不變性比對中被執行（純函式）。"""
    return not (a_failures or incomplete_files or result["missing"] or result["unexpected"] or result["caused"]
                or residual_unexecuted)


PROBE_DIR_ENV = "FRAMEPATH_DEF_PROBE_DIR"
PROBE_DEFS_ENV = "FRAMEPATH_DEF_PROBE_DEFS"


def install_def_probe() -> None:
    """環境變數 `FRAMEPATH_DEF_PROBE_DIR`／`_DEFS`（`模組:限定名` 逗號分隔）已設 ⇒ 以保留描述子型別之包裝記錄各定義
    是否被呼叫，行程結束寫 `<dir>/<pid>.json`（不改回傳值與例外）。由 `scripts/freeze_framepath_baseline.py` 之子行程
    呼叫（A 組不變性比對之 11 格皆於子行程生成）。重複呼叫無作用。"""
    import atexit
    import functools
    import importlib
    import inspect

    out_dir, specs = os.environ.get(PROBE_DIR_ENV, "").strip(), os.environ.get(PROBE_DEFS_ENV, "").strip()
    if not out_dir or not specs or getattr(install_def_probe, "_installed", False):
        return
    install_def_probe._installed = True  # type: ignore[attr-defined]
    hit: set = set()
    for spec in [s for s in specs.split(",") if s]:
        mod_name, qual = spec.split(":", 1)
        owner = importlib.import_module(mod_name)
        parts = qual.split(".")
        for p in parts[:-1]:
            owner = getattr(owner, p)
        raw = inspect.getattr_static(owner, parts[-1])
        fn = raw.__func__ if isinstance(raw, (staticmethod, classmethod)) else raw

        def _wrap(fn=fn, spec=spec):
            @functools.wraps(fn)
            def wrapper(*a, **k):
                hit.add(spec)
                return fn(*a, **k)
            return wrapper

        w = _wrap()
        setattr(owner, parts[-1], type(raw)(w) if isinstance(raw, (staticmethod, classmethod)) else w)

    def _flush() -> None:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / f"{os.getpid()}.json").write_text(json.dumps(sorted(hit)), encoding="utf-8")

    atexit.register(_flush)
    install_def_probe._flush = _flush  # type: ignore[attr-defined]


def pytest_configure(config) -> None:  # noqa: ARG001 — 以 `-p framepath_affected_gate` 載入時之 pytest 鉤子
    """受影響測試閘以本模組為 pytest 外掛（`-p framepath_affected_gate`，PYTHONPATH 含 scripts/）執行 A／B／C 時，
    於測試行程內裝殘差定義探針（環境變數未設則無作用）。"""
    install_def_probe()


PROBE_PLUGIN_ARGS = ("-p", "framepath_affected_gate")


def probe_hits(probe_dir: Path) -> set:
    hits: set = set()
    for p in sorted(Path(probe_dir).glob("*.json")) if Path(probe_dir).is_dir() else []:
        try:
            hits |= set(json.loads(p.read_text(encoding="utf-8")))
        except ValueError:
            continue
    return hits


ENV_PREFIXES = ("FFACT_", "ICFA_", "FRAMEPATH_", "PYTHON", "NUMBA_", "OMP_", "MKL_", "LEGACY_KLINE")


def env_fingerprint(env: Mapping[str, str]) -> str:
    """有效執行環境（審查 r48）：影響生成／測試之環境變數前綴之鍵值、Python 執行檔與版本。"""
    keys = sorted(k for k in env if k.startswith(ENV_PREFIXES))
    return json.dumps({"env": {k: env[k] for k in keys}, "python": sys.executable, "version": sys.version},
                      sort_keys=True, ensure_ascii=False)


def state_key(repo: Path, test_file: str, phase: int, env: Optional[Mapping[str, str]] = None) -> str:
    """結果檔沿用之狀態指紋：HEAD、相對 HEAD 之完整 diff、未追蹤檔清單、測試檔內容、pytest 參數、phase、有效環境。"""
    h = hashlib.sha256()
    for part in (
        _git(repo, "rev-parse", "HEAD"),
        _git(repo, "diff", "--binary", "HEAD"),
        _git(repo, "ls-files", "--others", "--exclude-standard"),
        (repo / test_file).read_bytes().decode("utf-8", "replace") if (repo / test_file).is_file() else "",
        json.dumps(PYTEST_FLAGS), str(phase), env_fingerprint(env if env is not None else os.environ),
    ):
        h.update(part.encode("utf-8", "replace"))
        h.update(b"\0")
    return h.hexdigest()


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-c", "core.quotepath=off", "-C", str(repo), *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise GateError(f"git {' '.join(args)} rc={proc.returncode}：{proc.stderr[-300:]}")
    return proc.stdout


def _pytest(args: Sequence[str], cwd: Path, env: Mapping[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "pytest", *args], cwd=cwd, env=dict(env), capture_output=True,
                          text=True)


def collect(test_file: str, cwd: Path, env: Mapping[str, str]) -> List[str]:
    # 諮詢 r5 CODEX-R5-P1-01：本專案 pytest.ini 下 `-q` 輸出表頭與 `<Function …>`，`-qq` 才逐行輸出 nodeid
    proc = _pytest(["--collect-only", "-qq", "-p", "no:cacheprovider", test_file], cwd, env)
    ids = [ln.strip() for ln in proc.stdout.splitlines() if ln.startswith(test_file + "::")]
    if proc.returncode != 0 or not ids:
        raise GateError(f"{test_file} 收集失敗或為空 rc={proc.returncode}：{proc.stdout[-500:]}{proc.stderr[-500:]}")
    return ids


def run_file(test_file: str, xml_path: Path, cwd: Path, env: Mapping[str, str],
             nodeids: Optional[Sequence[str]] = None, extra: Sequence[str] = ()) -> Tuple[int, Dict[str, Dict[str, str]]]:
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    if xml_path.exists():
        xml_path.unlink()
    proc = _pytest([*PYTEST_FLAGS, *extra, f"--junitxml={xml_path}", *(nodeids or [test_file])], cwd, env)
    res = junit_results(xml_path.read_text(encoding="utf-8"), test_file) if xml_path.is_file() else {}
    return proc.returncode, res


def resolve_anchor() -> str:
    """本票最晚一筆實作許可之 round_start_head（與處置驗證器 ⓪ 同一函式）。"""
    from tests.feature_engineering.test_framepath_disposition import AUDIT_REL, approval_anchor

    anchor = approval_anchor((REPO / AUDIT_REL).read_text(encoding="utf-8", errors="replace").splitlines())
    if not anchor:
        raise GateError("審計紀錄無本票實作許可（impl_token_issued）")
    return anchor


def _benign_status(line: str) -> bool:
    """錨點工作樹乾淨判定之封閉豁免：本腳本建立之 `data_cache` symlink（未追蹤），與已追蹤之 `__pycache__/` 位元組碼／
    numba 快取（任一測試執行即改寫；同處置驗證器⑤⑦之過濾）。其餘任何改動或未追蹤檔皆不乾淨。"""
    path = line[3:]
    return line == "?? data_cache" or "/__pycache__/" in path


def verify_anchor_worktree(wt: Path, anchor: str) -> None:
    """錨點工作樹：HEAD＝錨點、工作樹乾淨（無追蹤檔改動、無未追蹤檔）、生產碼與碼態錨點相同。"""
    head = _git(wt, "rev-parse", "HEAD").strip()
    if head != anchor:
        raise GateError(f"錨點工作樹 HEAD {head[:8]} ≠ 本票實作許可錨點 {anchor[:8]}")
    dirty = [ln for ln in _git(wt, "status", "--porcelain").splitlines() if ln.strip() and not _benign_status(ln)]
    if dirty:
        raise GateError(f"錨點工作樹不乾淨：{dirty[:10]}")
    prod = [p for p in _git(wt, "diff", "--name-only", CODE_ANCHOR, "HEAD", "--", *PRODUCTION_ROOTS).splitlines()
            if p and "/__pycache__/" not in p]
    if prod:
        raise GateError(f"錨點之生產碼與碼態錨點 {CODE_ANCHOR} 不同：{prod[:10]}")
    # 審查 r48：被 git 忽略之實體輸入（實體 data_cache 等）不得存在；data_cache 只准指向主工作樹之 symlink 或不存在
    dc = wt / "data_cache"
    if dc.exists() or dc.is_symlink():
        if not (dc.is_symlink() and dc.resolve() == (REPO / "data_cache").resolve()):
            raise GateError(f"錨點工作樹之 data_cache 須為指向 {REPO / 'data_cache'} 之 symlink：{dc}")
    ignored = [ln[3:] for ln in _git(wt, "status", "--porcelain", "--ignored").splitlines()
               if ln.startswith("!! ") and not _benign_ignored(ln[3:])]
    if ignored:
        raise GateError(f"錨點工作樹含被忽略之檔：{ignored[:10]}")


def _benign_ignored(path: str) -> bool:
    """錨點工作樹之被忽略檔封閉豁免：位元組碼與 numba 快取（`__pycache__/`、`.pyc`）。"""
    return "__pycache__/" in path or path.endswith(".pyc")


def make_anchor_worktree(anchor: str) -> Path:
    wt = Path(tempfile.mkdtemp(prefix="framepath_anchor_")) / "wt"
    subprocess.run(["git", "-C", str(REPO), "worktree", "add", "--detach", str(wt), anchor], check=True,
                   capture_output=True)
    return wt


# ── SPEC v21 D8（諮詢 r5）：應跑集合 E＝A∪S1∪S2∪S3∪必跑；其餘逐項收據 ─────────────────────────────────────────
FFACT_KEY = "FFACT_USE_CGSA"
_TRUTHY = frozenset({"1", "true", "yes", "on"})
ALIGN_TRIGGER_FILES = frozenset({"momentum/FeatureEngineering/timeframe/tf_aligner.py"})
ALIGN_TRIGGER_SYMBOLS = frozenset({"TimeframeAligner", "build_asof_index_map", "_align_group_array",
                                   "_capture_multi_tf_alignment"})
ALIGN_TEST_NAMES = frozenset({"TimeframeAligner", "build_asof_index_map", "FFACT_MULTI_TF_COMPACT_ALIGNMENT",
                              "_capture_multi_tf_alignment"})
HEAVY_NAMES = frozenset({"requires_kline", "requires_kline_data", "FEATURE_KLINE_H5_PATH", "generate_features",
                         "generate_multi_tf", "run_stat", "run_generation", "generate_cell", "run_ic_first",
                         "kline_close"})
HEAVY_SUBSTRINGS = ("kline_cache",)
SKIP_REASONS = ("invariance_envelope", "align_static_proof")
INVARIANCE_BASELINE_REL = "tests/_golden/framepath/cgsa_fingerprint.json"
DISPOSITION_REL = "tests/_golden/framepath/test_disposition.json"


def _is_keyconst(node: Optional[ast.AST]) -> bool:
    return isinstance(node, ast.Constant) and node.value == FFACT_KEY


def _is_truthy(node: Optional[ast.AST]) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.strip().lower() in _TRUTHY


def ffact_unproven(node: ast.AST) -> bool:
    """節點內出現 `FFACT_USE_CGSA`（字串常數或關鍵字引數）且並非每一處皆可證為真值常數 ⇒ True（fail-closed：
    值經變數、CondExp、dict 展開、delenv 等無法靜態決定者一律視為可能走 frame）。"""
    total = proven = 0
    for n in ast.walk(node):
        if _is_keyconst(n):
            total += 1
        if isinstance(n, ast.keyword) and n.arg == FFACT_KEY:
            total += 1
            proven += _is_truthy(n.value)
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "setenv"
                and len(n.args) > 1 and _is_keyconst(n.args[0])):
            proven += _is_truthy(n.args[1])
        if isinstance(n, ast.Dict):
            # 審查 r53：其後有 `**展開`（keys 中之 None）者可覆寫該鍵 ⇒ 不得計為已證真值
            keys = list(n.keys)
            proven += sum(1 for i, (k, v) in enumerate(zip(keys, n.values))
                          if _is_keyconst(k) and _is_truthy(v) and None not in keys[i + 1:])
        if (isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Subscript)
                and _is_keyconst(_slice(n.targets[0]))):
            proven += _is_truthy(n.value)
    return total > proven


def _slice(node: ast.Subscript) -> ast.AST:
    sl = node.slice
    return sl.value if isinstance(sl, ast.Index) else sl  # type: ignore[attr-defined]  # python<3.9


def refs_of(node: ast.AST) -> set:
    """節點引用之名稱：Name、Attribute 屬性名、字串常數（setattr 以字串指名者）、參數名（fixture）、關鍵字名。"""
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.add(n.value)
        elif isinstance(n, ast.arg):
            out.add(n.arg)
        elif isinstance(n, ast.keyword) and n.arg:
            out.add(n.arg)
    return out


def _defs(tree: ast.Module) -> Dict[str, ast.AST]:
    """頂層函式／類別與類別方法 → {qualname: node}（類別本身亦列，方法為 `Cls.meth`）。"""
    out: Dict[str, ast.AST] = {}
    for st in tree.body:
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[st.name] = st
        elif isinstance(st, ast.ClassDef):
            out[st.name] = st
            for m in st.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out[f"{st.name}.{m.name}"] = m
    return out


def _module_path(dotted: str, level: int, here: str, source_of) -> Optional[str]:
    """測試輔助模組之 repo 相對路徑（只解析 tests/ 下且來源存在者；第三方與生產模組回 None）。"""
    if level:
        base = Path(here).parent
        for _ in range(level - 1):
            base = base.parent
        parts = [*base.parts, *(dotted.split(".") if dotted else [])]
    else:
        parts = dotted.split(".")
    if not parts or parts[0] != "tests":
        return None
    for cand in ("/".join(parts) + ".py", "/".join(parts) + "/__init__.py"):
        if source_of(cand) is not None:
            return cand
    return None


def module_taint(path: str, source_of, symbols: frozenset, _cache: Optional[dict] = None,
                 _stack: Tuple[str, ...] = (), ffact: bool = True, substrings: Tuple[str, ...] = ()) -> Dict[str, set]:
    """S2：模組內各定義（含 fixture）之 taint 理由——直接（`ffact`／`sym:<名>`）、經模組層名稱（`name:<名>`）、
    經同模組或 tests/ 下輔助模組之被 taint 定義（`call:<模組>:<名>`）傳遞，至不動點。conftest 由呼叫端併入。"""
    cache = _cache if _cache is not None else {}
    graph = cache.setdefault(("__taint_graph__", ffact, tuple(substrings), symbols), _TaintGraph(
        source_of, symbols, ffact, tuple(substrings)))
    return graph.reasons_of(path)


def _tainted_names(reasons: Mapping[str, set]) -> Dict[str, str]:
    """被 taint 定義之可引用名 → 限定名：末段名，以及方法所屬之類別名（審查 r53：經匯入類別再呼叫其方法者亦須傳遞）。"""
    out: Dict[str, str] = {}
    for q, r in reasons.items():
        if not r:
            continue
        parts = q.split(".")
        out.setdefault(parts[-1], q)
        if len(parts) > 1:
            out.setdefault(parts[0], q)
    return out


class _TaintGraph:
    """S2／重型判定之跨模組傳遞（審查 r52：循環引用不得以不完整結果入快取）。先載入 `path` 之 tests/ 匯入閉包
    （每模組只解析一次），再對全部已載入模組以「同模組定義、模組層名稱、匯入之輔助模組定義」三種邊做全域不動點
    迭代；結果與掃描順序無關。"""

    def __init__(self, source_of, symbols: frozenset, ffact: bool, substrings: Tuple[str, ...]):
        self.source_of, self.symbols, self.ffact, self.substrings = source_of, symbols, ffact, substrings
        self.mods: Dict[str, Dict[str, object]] = {}
        self.reasons: Dict[str, Dict[str, set]] = {}
        self._fresh: List[str] = []

    def _load(self, path: str) -> None:
        if path in self.mods:
            return
        src = self.source_of(path)
        if src is None:
            self.mods[path] = {"defs": {}, "refs": {}, "names": set(), "ext": {}}
            self.reasons[path] = {}
            return
        tree = ast.parse(src)
        defs = {q: n for q, n in _defs(tree).items() if not isinstance(n, ast.ClassDef)}
        refs = {q: refs_of(n) for q, n in defs.items()}
        reasons: Dict[str, set] = {q: set() for q in defs}
        for q, node in defs.items():
            if self.ffact and ffact_unproven(node):
                reasons[q].add("ffact")
            reasons[q] |= {f"sym:{s}" for s in refs[q] & self.symbols}
            reasons[q] |= {f"str:{s}" for s in self.substrings if any(s in r for r in refs[q])}
        names = set()
        for st in tree.body:
            targets = st.targets if isinstance(st, ast.Assign) else [st.target] if isinstance(st, ast.AnnAssign) else []
            value = getattr(st, "value", None)
            if value is None:
                continue
            vrefs = refs_of(value)
            if ((self.ffact and ffact_unproven(value)) or vrefs & self.symbols
                    or any(s in r for s in self.substrings for r in vrefs)):
                names |= {t.id for t in targets if isinstance(t, ast.Name)}
        ext: Dict[str, Tuple[str, str]] = {}  # 本地名 → (輔助模組路徑, 該模組中之名；"" 表整個模組)
        for st in ast.walk(tree):
            if isinstance(st, ast.Import):
                for a in st.names:
                    mp = _module_path(a.name, 0, path, self.source_of)
                    if mp:
                        ext[a.asname or a.name.split(".")[0]] = (mp, "")
            elif isinstance(st, ast.ImportFrom):
                for a in st.names:
                    sub = _module_path(f"{st.module}.{a.name}" if st.module else a.name, st.level, path, self.source_of)
                    if sub:
                        ext[a.asname or a.name] = (sub, "")
                        continue
                    mp = _module_path(st.module or "", st.level, path, self.source_of)
                    if mp:
                        ext[a.asname or a.name] = (mp, a.name)
        self.mods[path] = {"defs": defs, "refs": refs, "names": names, "ext": ext}
        self.reasons[path] = reasons
        self._fresh.append(path)
        for mp, _ in ext.values():
            self._load(mp)

    def _fixpoint(self, paths: Sequence[str]) -> None:
        """只迭代本次新載入者：既有模組之閉包已穩定，且不匯入新載入者（否則先前已一併載入）。"""
        changed = True
        while changed:
            changed = False
            for path in paths:
                mod = self.mods[path]
                reasons = self.reasons[path]
                live = _tainted_names(reasons)
                for q, refs in mod["refs"].items():
                    add = {f"name:{n}" for n in refs & mod["names"]}
                    add |= {f"call:{path}:{live[b]}" for b in refs & set(live) if live[b] != q}
                    for local, (mp, name) in mod["ext"].items():
                        if local not in refs:
                            continue
                        bad = set(_tainted_names(self.reasons.get(mp, {})))
                        hits = ({name} & bad) if name else (refs & bad)
                        add |= {f"call:{mp}:{h}" for h in hits}
                    if not add <= reasons[q]:
                        reasons[q] |= add
                        changed = True

    def reasons_of(self, path: str) -> Dict[str, set]:
        if path not in self.mods:
            self._fresh: List[str] = []
            self._load(path)
            self._fixpoint(self._fresh)
        return self.reasons[path]


def _conftests(test_file: str, source_of) -> List[str]:
    parts = Path(test_file).parts[:-1]
    out = []
    for i in range(1, len(parts) + 1):
        cand = "/".join(parts[:i]) + "/conftest.py"
        if source_of(cand) is not None:
            out.append(cand)
    return out


def file_scan(test_file: str, source_of, symbols: frozenset, cache: Optional[dict] = None,
              heavy_cache: Optional[dict] = None, want_heavy: bool = True) -> Dict[str, object]:
    """單一測試檔之 {"refs": {qualname: 名稱集}, "taint": {qualname: 理由集}, "heavy": bool}；fixture 引用
    conftest 之被 taint fixture 亦傳遞。`cache`／`heavy_cache` 可於同一 source_of 與符號表之多檔掃描間共用（輔助模組
    只解析一次）；`want_heavy=False` 時 heavy 恆 True（不計算，只供不得整檔之清單外檔）。"""
    src = source_of(test_file)
    if src is None:
        return {"refs": {}, "taint": {}, "heavy": False}
    tree = ast.parse(src)
    defs = _defs(tree)
    refs = {q: refs_of(n) for q, n in defs.items()}
    cache = {} if cache is None else cache
    taint = {q: set(r) for q, r in module_taint(test_file, source_of, symbols, cache).items()}
    for cf in _conftests(test_file, source_of):
        bad = set(_tainted_names(module_taint(cf, source_of, symbols, cache)))
        for q in defs:
            hits = refs[q] & bad
            if hits:
                taint.setdefault(q, set()).update(f"call:{cf}:{h}" for h in hits)
    heavy = is_heavy(test_file, source_of, heavy_cache) if want_heavy else True
    return {"refs": refs, "taint": {q: r for q, r in taint.items() if r}, "heavy": heavy}


def is_heavy(test_file: str, source_of, cache: Optional[dict] = None) -> bool:
    """重型（不得 S3 整檔）：檔內或其經 tests/ 輔助模組（含 conftest）傳遞之定義引用 `HEAVY_NAMES`（真實 kline／
    生成入口），或其字串常數含 `kline_cache`——字串規則與符號規則同經輔助模組定義、模組層名稱與 conftest 傳遞
    （審查 r51：只呼叫內含 kline 路徑字面之 helper 者亦屬重型）。與 S2 同一傳遞分析（ffact 關閉）。"""
    src = source_of(test_file)
    if src is None:
        return True
    tree = ast.parse(src)
    module_refs = refs_of(tree)
    if module_refs & HEAVY_NAMES or any(s in r for s in HEAVY_SUBSTRINGS for r in module_refs):
        return True
    cache = {} if cache is None else cache
    if any(module_taint(test_file, source_of, HEAVY_NAMES, cache, ffact=False, substrings=HEAVY_SUBSTRINGS).values()):
        return True
    for cf in _conftests(test_file, source_of):
        bad = set(_tainted_names(module_taint(cf, source_of, HEAVY_NAMES, cache, ffact=False,
                                              substrings=HEAVY_SUBSTRINGS)))
        if module_refs & bad:
            return True
    return False


def nodeid_qualname(nodeid: str) -> str:
    """`path::Cls::test_x[p]` → `Cls.test_x`。"""
    parts = nodeid.split("::")[1:]
    if parts:
        parts[-1] = parts[-1].split("[", 1)[0]
    return ".".join(parts)


def s1_targets(disposition: Mapping, phase: int, scans: Mapping[str, Mapping]) -> Tuple[Dict[str, Dict[str, set]], Dict[str, set]]:
    """S1：處置表 phase≤N 之操作 → ({檔: {qualname: {OP-id}}}, {nodeid: {OP-id}})。locator 有 qualname 者取該函式；
    `target`（模組層 dict／序列）與 `import_alias` 取引用該名之函式；顯式 nodeids 與 rename 之 new_nodeid 另列
    （其所屬函式之其餘參數化 nodeid 亦選入）。空 nodeids 不等於「沒有測試」（CODEX-R5-P1-02）。"""
    funcs: Dict[str, Dict[str, set]] = {}
    nodes: Dict[str, set] = {}
    for op in disposition.get("operations", []):
        if int(op.get("phase", 99)) > phase:
            continue
        path, oid, loc = op["path"], op["id"], op.get("locator") or {}
        quals = set()
        if loc.get("qualname"):
            quals.add(loc["qualname"])
        name = loc.get("target") or (loc.get("name") if loc.get("category") == "import_alias" else None)
        if name:
            quals |= {q for q, r in scans.get(path, {}).get("refs", {}).items() if name in r}
        for nid in op.get("nodeids") or []:
            nodes.setdefault(nid, set()).add(oid)
            quals.add(nodeid_qualname(nid))
        for q in quals:
            funcs.setdefault(path, {}).setdefault(q, set()).add(oid)
    for row in disposition.get("nodeids", []):
        if row.get("disposition") == "rename" and int(row.get("phase", 99)) <= phase and row.get("new_nodeid"):
            nid = row["new_nodeid"]
            nodes.setdefault(nid, set()).add(row.get("op", "rename"))
            funcs.setdefault(nid.split("::", 1)[0], {}).setdefault(nodeid_qualname(nid), set()).add(row.get("op", "rename"))
    return funcs, nodes


def select_expected(collected: Mapping[str, Sequence[str]], scans: Mapping[str, Mapping],
                    s1_funcs: Mapping[str, Mapping[str, set]], s1_nodes: Mapping[str, set],
                    must: Sequence[str], heavy_pinned: Iterable[str], align_triggered: bool,
                    ) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """把 collected 之每個 nodeid 分入「選入（理由清單）」或「未跑（封閉理由）」——兩者互斥且聯集＝collected。
    S1＝處置操作所及函式；S2＝taint；S3＝靜態輕量檔（無 kline／生成呼叫且不在釘扎重型表）整檔；必跑＝manifest
    `affected_must`；對齊觸發時引用對齊名之函式選入，否則該等函式未跑理由為 `align_static_proof`。"""
    heavy_pinned = set(heavy_pinned)
    selected: Dict[str, List[str]] = {}
    skipped: Dict[str, str] = {}
    must_set = set(must)
    for f, ids in collected.items():
        scan = scans.get(f, {"refs": {}, "taint": {}, "heavy": True})
        light = not scan.get("heavy", True) and f not in heavy_pinned
        for nid in ids:
            q = nodeid_qualname(nid)
            why: List[str] = []
            if nid in must_set:
                why.append("must")
            if q in s1_funcs.get(f, {}) or nid in s1_nodes:
                why += sorted(f"S1:{o}" for o in s1_funcs.get(f, {}).get(q, set()) | s1_nodes.get(nid, set()))
            if q in scan.get("taint", {}):
                why += sorted(f"S2:{r}" for r in scan["taint"][q])
            if light:
                why.append("S3:light")
            aligned = bool(scan.get("refs", {}).get(q, set()) & ALIGN_TEST_NAMES)
            if aligned and align_triggered:
                why.append("align_trigger")
            if why:
                selected[nid] = why
            else:
                skipped[nid] = "align_static_proof" if aligned else "invariance_envelope"
    return selected, skipped


# ── CGSA 模式等價（審查 r51）：假設 CGSA 開啟且 registry 已建立，把錨點與工作樹之定義正規化後比對 ──────────────
def _is_enabled_call(n: ast.AST) -> bool:
    return (isinstance(n, ast.Call) and not n.args and not n.keywords
            and ((isinstance(n.func, ast.Attribute) and n.func.attr == "_cgsa_enabled")
                 or (isinstance(n.func, ast.Name) and n.func.id == "_cgsa_enabled")))


def _is_registry_expr(n: ast.AST) -> bool:
    if isinstance(n, ast.Attribute) and n.attr == "_cgsa_registry":
        return True
    return (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr" and len(n.args) >= 2
            and isinstance(n.args[1], ast.Constant) and n.args[1].value == "_cgsa_registry")


def _is_guard_stmt(st: ast.stmt) -> bool:
    return (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) and isinstance(st.value.func, ast.Attribute)
            and st.value.func.attr == "_require_cgsa_registry")


def _const_bool(n: ast.AST) -> bool:
    return isinstance(n, ast.Constant) and isinstance(n.value, bool)


class _CgsaFold(ast.NodeTransformer):
    """`*._cgsa_enabled()`→True；`<registry> is not None`→True、`is None`→False；not／and／or 常數折疊。"""

    def visit_Call(self, n: ast.Call) -> ast.AST:
        self.generic_visit(n)
        return ast.Constant(True) if _is_enabled_call(n) else n

    def visit_Compare(self, n: ast.Compare) -> ast.AST:
        self.generic_visit(n)
        if (len(n.ops) == 1 and isinstance(n.ops[0], (ast.Is, ast.IsNot)) and isinstance(n.comparators[0], ast.Constant)
                and n.comparators[0].value is None and _is_registry_expr(n.left)):
            return ast.Constant(isinstance(n.ops[0], ast.IsNot))
        return n

    def visit_UnaryOp(self, n: ast.UnaryOp) -> ast.AST:
        self.generic_visit(n)
        if isinstance(n.op, ast.Not):
            n.operand = _truthy_fold(n.operand)
            if _const_bool(n.operand):
                return ast.Constant(not n.operand.value)
        return n

    def visit_BoolOp(self, n: ast.BoolOp) -> ast.AST:
        """值語意折疊（審查 r52：`x and True` 之值不等於 `x`）：只去除**開頭**之布林常數——and 開頭 True 去除、開頭
        False 即 False；or 開頭 False 去除、開頭 True 即 True。非開頭常數保留。"""
        self.generic_visit(n)
        vals = list(n.values)
        absorbing = isinstance(n.op, ast.Or)  # or：True 吸收；and：False 吸收
        while vals and _const_bool(vals[0]) and len(vals) > 1:
            if vals[0].value is absorbing:
                return ast.Constant(absorbing)
            vals = vals[1:]
        return vals[0] if len(vals) == 1 else ast.BoolOp(op=n.op, values=vals)

    def _test(self, n: ast.AST) -> ast.AST:
        self.generic_visit(n)
        n.test = _truthy_fold(n.test)
        return n

    visit_If = visit_While = visit_IfExp = visit_Assert = _test


def _truthy_fold(e: ast.AST) -> ast.AST:
    """只看真假值之位置（if／while／三元／assert 條件、not 與其內之 and／or 運算元）：非吸收之布林常數任一位置可去除；
    吸收常數（and 之 False、or 之 True）只在其前無其他運算元時整式化為常數——其前之運算元仍會被求值（可能有副作用，
    審查 r53），故保留為 `前段 and/or 常數`，其後運算元不會被求值而去除。"""
    if isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.Not):
        inner = _truthy_fold(e.operand)
        return ast.Constant(not inner.value) if _const_bool(inner) else ast.UnaryOp(op=e.op, operand=inner)
    if not isinstance(e, ast.BoolOp):
        return e
    absorbing = isinstance(e.op, ast.Or)
    vals = []
    for v in (_truthy_fold(x) for x in e.values):
        if _const_bool(v):
            if v.value is absorbing:
                if not vals:
                    return ast.Constant(absorbing)
                return ast.BoolOp(op=e.op, values=[*vals, ast.Constant(absorbing)])
            continue
        vals.append(v)
    if not vals:
        return ast.Constant(not absorbing)
    return vals[0] if len(vals) == 1 else ast.BoolOp(op=e.op, values=vals)


def _cgsa_block(stmts: List[ast.stmt]) -> List[ast.stmt]:
    """常數條件 if 展開、守衛敘述（`_require_cgsa_registry`，registry 已建立時無作用）移除、return／raise 後截斷（遞迴）。"""
    out: List[ast.stmt] = []
    for st in stmts:
        if _is_guard_stmt(st):
            continue
        if isinstance(st, ast.If) and _const_bool(st.test):
            out.extend(_cgsa_block(st.body if st.test.value else st.orelse))
            if out and isinstance(out[-1], (ast.Return, ast.Raise)):
                break
            continue
        for field in ("body", "orelse", "finalbody"):
            if isinstance(getattr(st, field, None), list):
                setattr(st, field, _cgsa_block(getattr(st, field)))
        if isinstance(st, ast.Try):
            for h in st.handlers:
                h.body = _cgsa_block(h.body) or [ast.Pass()]
        if isinstance(st, ast.If) and not st.body and not st.orelse:
            continue  # 守衛移除後成空殼之 if（條件為無副作用之比較／名稱）
        if hasattr(st, "body") and isinstance(st.body, list) and not st.body:
            st.body = [ast.Pass()]
        out.append(st)
        if isinstance(st, (ast.Return, ast.Raise)):
            break
    return out


def _cgsa_propagate(fn: ast.AST) -> bool:
    """布林常數區域名稱代入並刪除該賦值——只限可證支配全部讀取者（審查 r54）：賦值為函式本體**最外層**敘述、該名於
    函式內恰一次綁定（含 for／with／except／walrus 等任何 Store、參數、global／nonlocal 皆計），且每一處讀取皆位於該
    賦值之後。分支內、迴圈內或讀取先於賦值者一律不代入（保守保留，判不等價）。"""
    stores: Dict[str, int] = {}
    loads: Dict[str, List[Tuple[int, int]]] = {}
    for n in ast.walk(fn):
        if isinstance(n, ast.Name):
            if isinstance(n.ctx, ast.Load):
                loads.setdefault(n.id, []).append((n.lineno, n.col_offset))
            else:
                stores[n.id] = stores.get(n.id, 0) + 1
        elif isinstance(n, ast.arg):
            stores[n.arg] = stores.get(n.arg, 0) + 1
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            for nm in n.names:
                stores[nm] = stores.get(nm, 0) + 2
    consts: Dict[str, bool] = {}
    top: Dict[str, ast.Assign] = {}
    for st in getattr(fn, "body", []):
        if (isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name)
                and _const_bool(st.value)):
            name = st.targets[0].id
            end = (getattr(st, "end_lineno", st.lineno), getattr(st, "end_col_offset", 0))
            if stores.get(name) == 1 and all(pos > end for pos in loads.get(name, [])):
                consts[name] = st.value.value
                top[name] = st
    if not consts:
        return False
    assigns = {k: [top[k]] for k in consts}

    class _Sub(ast.NodeTransformer):
        def visit_Name(self, n: ast.Name) -> ast.AST:
            return ast.Constant(consts[n.id]) if isinstance(n.ctx, ast.Load) and n.id in consts else n

    _Sub().visit(fn)
    drop = {id(assigns[k][0]) for k in consts}
    for parent in ast.walk(fn):
        for field in ("body", "orelse", "finalbody"):
            lst = getattr(parent, field, None)
            if isinstance(lst, list):
                setattr(parent, field, [s for s in lst if id(s) not in drop])
    return True


def cgsa_normal_form(fn: ast.AST) -> str:
    """CGSA 開啟且 registry 已建立之假設下之正規形（去 docstring、折疊、代入、展開至不動點）。"""
    fn = copy.deepcopy(fn)
    body = getattr(fn, "body", [])
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        fn.body = body[1:] or [ast.Pass()]
    for _ in range(8):
        _CgsaFold().visit(fn)
        changed = _cgsa_propagate(fn)
        _CgsaFold().visit(fn)
        fn.body = _cgsa_block(fn.body) or [ast.Pass()]
        if not changed:
            break
    return ast.dump(fn)


def _module_of(path: str) -> str:
    return path[:-3].replace("/", ".")


def production_changes(repo: Path, anchor: str) -> Tuple[set, set, List[str], List[str]]:
    """錨點 → 工作樹之生產碼（momentum／api／config 之 .py）：(被刪定義名, CGSA 殘差定義名, 改動檔, 殘差定義規格
    `模組:限定名`)。本體改變之定義經 `cgsa_normal_form` 比對：正規形相同（CGSA 開啟下等價，例如只拿掉
    `_cgsa_enabled()` 判斷、加 registry 守衛）者不入殘差；不同者（不論公開或私有）入殘差。另：被刪且於全部生產碼
    已無定義之名稱若仍被引用 ⇒ GateError（懸空引用）。名稱取末段。"""
    files = [p for p in _git(repo, "diff", "--name-only", anchor, "--", *PRODUCTION_ROOTS).splitlines()
             if p.endswith(".py") and "/__pycache__/" not in p]
    deleted, residual, specs = set(), set(), set()
    deleted_defs = set()
    for f in files:
        old = _git_show(repo, anchor, f)
        new = (repo / f).read_text(encoding="utf-8") if (repo / f).is_file() else None
        old_tree = ast.parse(old) if old is not None else ast.Module(body=[], type_ignores=[])
        new_tree = ast.parse(new) if new is not None else ast.Module(body=[], type_ignores=[])
        od, nd = _defs(old_tree), _defs(new_tree)
        for q, node in od.items():
            bare = q.split(".")[-1]
            if q not in nd:
                deleted.add(bare)
                deleted_defs.add(bare)
            elif isinstance(node, ast.ClassDef):
                if _class_header(node) != _class_header(nd[q]):
                    raise GateError(f"{f}:{q} 類別標頭（基底／decorator／keywords）改變，無法機械判定影響範圍")
            elif ast.dump(node) != ast.dump(nd[q]) and cgsa_normal_form(node) != cgsa_normal_form(nd[q]):
                residual.add(bare)
                specs.add(f"{_module_of(f)}:{q}")
        # 審查 r52：模組層與類別層之非定義綁定（常數、匯入、類別屬性）亦比對；值改變之名入殘差，且新碼中引用該名之
        # 定義一併入殘差規格（以執行探針觀測）；其他無法以名稱歸屬之模組層敘述改變 ⇒ 拒跑
        scopes = [("", old_tree.body, new_tree.body)]
        scopes += [(q, od[q].body, nd[q].body) for q in od if isinstance(od[q], ast.ClassDef) and q in nd]
        for owner, old_body, new_body in scopes:
            ob, o_other = _bindings(old_body)
            nb, n_other = _bindings(new_body)
            if o_other != n_other:
                raise GateError(f"{f}{':' + owner if owner else ''} 之非定義、非綁定敘述改變，無法機械判定影響範圍")
            gone = set(ob) - set(nb)
            changed_names = {k for k in set(ob) & set(nb) if ob[k] != nb[k]}
            deleted |= gone
            residual |= changed_names
            for q, node in nd.items():
                if isinstance(node, ast.ClassDef) or (owner and not q.startswith(owner + ".")):
                    continue
                if refs_of(node) & (changed_names | gone):
                    residual.add(q.split(".")[-1])
                    specs.add(f"{_module_of(f)}:{q}")
    dangling = _dangling_refs(repo, deleted_defs)
    if dangling:
        raise GateError(f"生產碼仍引用已無定義之被刪名稱：{dangling[:10]}")
    return deleted, residual, files, sorted(specs)


def _class_header(node: ast.ClassDef) -> str:
    return "|".join(ast.dump(x) for x in [*node.bases, *node.keywords, *node.decorator_list])


def _bindings(body: Sequence[ast.stmt]) -> Tuple[Dict[str, str], List[str]]:
    """非定義敘述 → ({綁定名: 該名所有綁定敘述之 dump 串接}, [其他敘述 dump])。賦值（含解構、註記、增量）以目標名
    歸屬；匯入以本地名歸屬（逐別名）；docstring 與 pass 不計；其餘（模組層 if／try／呼叫等）入「其他」。"""
    named: Dict[str, str] = {}
    other: List[str] = []
    for i, st in enumerate(body):
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Pass)):
            continue
        if i == 0 and isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) and isinstance(st.value.value, str):
            continue
        if isinstance(st, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = st.targets if isinstance(st, ast.Assign) else [st.target]
            names = [n.id for t in targets for n in ast.walk(t) if isinstance(n, ast.Name)]
            if names:
                for nm in names:
                    named[nm] = named.get(nm, "") + ast.dump(st)
                continue
        if isinstance(st, (ast.Import, ast.ImportFrom)):
            for a in st.names:
                local = a.asname or a.name.split(".")[0]
                src = f"{getattr(st, 'module', '') or ''}|{getattr(st, 'level', 0)}|{a.name}"
                named[local] = named.get(local, "") + src
            continue
        other.append(ast.dump(st))
    return named, other


def _dangling_refs(repo: Path, deleted: Iterable[str]) -> List[str]:
    """全部生產碼（工作樹）中，被刪且已無任何定義之名稱之引用（`檔:名`）。"""
    deleted = set(deleted)
    if not deleted:
        return []
    trees = {}
    for root in PRODUCTION_ROOTS:
        for p in sorted((repo / root).rglob("*.py")) if (repo / root).is_dir() else []:
            if "__pycache__" in p.parts:
                continue
            try:
                trees[str(p.relative_to(repo))] = ast.parse(p.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
    defined = {n.name for t in trees.values() for n in ast.walk(t)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    gone = deleted - defined
    return sorted(f"{f}:{n}" for f, t in trees.items() for n in (refs_of(t) & gone))


def s2_symbols(deleted: Iterable[str], residual: Iterable[str]) -> frozenset:
    """S2 符號表：被刪定義 ∪ CGSA 殘差定義（不分公開私有）。CGSA 下可證等價之改動不入表；殘差定義經公開入口之執行由
    A 組不變性比對之殘差探針（`FRAMEPATH_DEF_PROBE_*`）證明已被執行。"""
    return frozenset(set(deleted) | set(residual))


def _git_show(repo: Path, rev: str, path: str) -> Optional[str]:
    proc = subprocess.run(["git", "-c", "core.quotepath=off", "-C", str(repo), "show", f"{rev}:{path}"],
                          capture_output=True, text=True)
    return proc.stdout if proc.returncode == 0 else None


def _row_nodeids(rows: Sequence[str], prefix: str) -> List[str]:
    hits = [r for r in rows if r.startswith(prefix)]
    if len(hits) > 1:
        raise GateError(f"manifest 重複 {prefix.strip()}")
    return [p for p in hits[0][len(prefix):].split() if p] if hits else []


ADMISSION_BUDGET_SECONDS = 7200


def plan_inputs_digest(repo: Path, anchor: str, phase: int, timing_dirs: Iterable[Path] = ()) -> str:
    """挑選之輸入指紋：錨點、phase、HEAD、相對 HEAD 之完整 diff、未追蹤檔清單、manifest、處置表、本執行器原始碼、
    admission 估時來源（各目錄下 junit xml 之路徑與內容，審查 r53）。`--admit` 須等於此值方得於估時未知或逾預算時執行
    （批准綁定確切輸入）。"""
    h = hashlib.sha256()
    no_cache = ":(exclude,glob)**/__pycache__/**"  # 已追蹤之 numba 快取於任何測試執行即改寫，非挑選輸入
    own = ":(exclude,glob)handoffs/run_receipts/framepath-b*-affected*"  # 本執行器自身之收據輸出，非挑選輸入
    untracked = _git(repo, "ls-files", "--others", "--exclude-standard", "--", ".", no_cache, own).splitlines()
    for part in (anchor, str(phase), _git(repo, "rev-parse", "HEAD"),
                 _git(repo, "diff", "--binary", "HEAD", "--", ".", no_cache)):
        h.update(part.encode("utf-8", "replace"))
        h.update(b"\0")
    for rel in sorted(untracked):  # 審查 r52：未追蹤檔綁路徑＋內容（同一路徑內容改變 ⇒ 批准失效）
        p = repo / rel
        h.update(rel.encode("utf-8", "replace") + b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest() if p.is_file() else b"<non-file>")
        h.update(b"\0")
    for rel in (MANIFEST_REL, DISPOSITION_REL, "scripts/framepath_affected_gate.py"):
        h.update((repo / rel).read_bytes() if (repo / rel).is_file() else b"")
        h.update(b"\0")
    for d in timing_dirs:
        d = Path(d).resolve()
        h.update(b"timings\0" + str(d).encode("utf-8", "replace") + b"\0")
        for x in sorted(d.rglob("*.xml")) if d.is_dir() else []:
            h.update(str(x.relative_to(d)).encode("utf-8", "replace") + b"\0" + hashlib.sha256(x.read_bytes()).digest())
    return h.hexdigest()


def junit_times(xml_text: str, repo: Path) -> Dict[str, float]:
    """junit xml → {nodeid: 秒}；classname 之模組段以 repo 內存在之 `.py` 判定，其後為類別段。"""
    out: Dict[str, float] = {}
    for case in ET.fromstring(xml_text).iter("testcase"):
        parts = case.get("classname", "").split(".")
        for i in range(len(parts), 0, -1):
            path = "/".join(parts[:i]) + ".py"
            if (repo / path).is_file():
                try:
                    t = float(case.get("time", ""))
                except ValueError:
                    break
                if math.isfinite(t) and t >= 0:  # 審查 r52：非有限、負值、缺值一律不採（該 nodeid 估時未知）
                    out["::".join([path, *parts[i:], case.get("name", "")])] = t
                break
    return out


def admission(selected: Iterable[str], times: Mapping[str, float], budget: float = ADMISSION_BUDGET_SECONDS
              ) -> Dict[str, object]:
    """執行前 admission（純函式）：已知估時總和、估時未知之 nodeid；status＝within（全部已知且 ≤ 預算）｜over｜unknown。
    非有限或負值之估時視為未知（不得以 NaN 比較語意落入 within）。"""
    sel = list(selected)
    ok = {n: times[n] for n in sel if n in times and math.isfinite(times[n]) and times[n] >= 0}
    known = round(sum(ok.values()), 3)
    unknown = sorted(n for n in sel if n not in ok)
    status = "over" if known > budget else ("unknown" if unknown else "within")
    return {"budget_seconds": budget, "known_seconds": known, "unknown": unknown, "status": status}


def load_times(repo: Path, dirs: Iterable[Path]) -> Dict[str, float]:
    """估時來源：給定目錄下全部 junit xml（本執行器先前之結果檔與歷次收據）；同 nodeid 取最大值（保守）。"""
    times: Dict[str, float] = {}
    for d in dirs:
        for x in sorted(Path(d).rglob("*.xml")) if Path(d).is_dir() else []:
            try:
                for n, t in junit_times(x.read_text(encoding="utf-8"), repo).items():
                    times[n] = max(t, times.get(n, 0.0))
            except ET.ParseError:
                continue
    return times


def plan(repo: Path, anchor: str, phase: int, manifest: Mapping, env: Mapping[str, str],
         timing_dirs: Sequence[Path] = ()) -> Dict[str, object]:
    """D8 挑選（不執行測試本體；耗時主要為逐檔 collect）：collect B／C 檔、靜態掃描錨點與工作樹兩版之測試檔並取聯集。
    須於本批完整改動（生產碼＋測試處置）套上後執行；任一檔 collect 失敗 ⇒ 拒跑。"""
    b_group, c_group = manifest_groups(manifest, phase)
    rows = manifest["batch_card"]["risk_mitigation"]
    must = _row_nodeids(rows, f"affected_must phase={phase} ")
    heavy_pinned = _row_nodeids(rows, f"heavy_files phase={phase} ")
    deleted, residual, prod_files, residual_specs = production_changes(repo, anchor)
    symbols = s2_symbols(deleted, residual)
    align_triggered = bool(set(prod_files) & ALIGN_TRIGGER_FILES or (deleted | residual) & ALIGN_TRIGGER_SYMBOLS)

    def post(p: str) -> Optional[str]:
        return (repo / p).read_text(encoding="utf-8") if (repo / p).is_file() else None

    # 錨點版只對錨點→工作樹有改動（含刪除）之 tests/ 檔讀 git，其餘與工作樹同
    changed_tests = set(_git(repo, "diff", "--name-only", anchor, "--", "tests").splitlines())

    def pre(p: str) -> Optional[str]:
        return _git_show(repo, anchor, p) if p in changed_tests else post(p)

    caches: Dict[str, dict] = {"pre": {}, "post": {}, "heavy_pre": {}, "heavy_post": {}}

    def merged_scan(f: str, want_heavy: bool = True) -> Dict[str, object]:
        a = file_scan(f, pre, symbols, caches["pre"], caches["heavy_pre"], want_heavy)
        b = file_scan(f, post, symbols, caches["post"], caches["heavy_post"], want_heavy)
        refs = {q: set(a["refs"].get(q, set())) | set(b["refs"].get(q, set())) for q in {*a["refs"], *b["refs"]}}
        taint = {q: set(a["taint"].get(q, set())) | set(b["taint"].get(q, set())) for q in {*a["taint"], *b["taint"]}}
        return {"refs": refs, "taint": taint, "heavy": bool(a["heavy"] or b["heavy"])}

    collected = {f: collect(f, repo, env) for f in b_group + c_group}
    scans: Dict[str, Dict[str, object]] = {f: merged_scan(f) for f in collected}
    # 清單外之測試檔亦受 S2 約束（審查 r51）：全部 tests/ 下 test_*.py 經同一傳遞分析，有 taint 者納入（只選 taint 之
    # nodeid，不整檔），收據記 extra_files。
    known = set(collected) | set(A_GROUP)
    extra: List[str] = []
    for p in sorted((repo / "tests").rglob("test_*.py")):
        rel = str(p.relative_to(repo))
        if rel in known or "__pycache__" in p.parts:
            continue
        scan = merged_scan(rel, want_heavy=False)
        if scan["taint"]:
            scan["heavy"] = True
            scans[rel] = scan
            extra.append(rel)
    for rel in extra:
        collected[rel] = collect(rel, repo, env)
    disposition = json.loads((repo / DISPOSITION_REL).read_text(encoding="utf-8"))
    s1_funcs, s1_nodes = s1_targets(disposition, phase, scans)
    selected, skipped = select_expected(collected, scans, s1_funcs, s1_nodes, must, heavy_pinned, align_triggered)
    missing_must = sorted(set(must) - set(selected))
    if missing_must:
        raise GateError(f"manifest affected_must 之 nodeid 未被收集：{missing_must}")
    baseline = repo / INVARIANCE_BASELINE_REL
    return {
        "groups": {"B": b_group, "C": c_group}, "collected": collected, "selected": selected, "skipped": skipped,
        "s2_symbols": sorted(symbols), "production_files": prod_files, "align_triggered": align_triggered,
        "residual_defs": residual_specs, "inputs_digest": plan_inputs_digest(repo, anchor, phase, timing_dirs),
        "extra_files": extra,
        "light_files": sorted(f for f, s in scans.items() if not s["heavy"] and f not in set(heavy_pinned)),
        "invariance_baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest() if baseline.is_file() else None,
    }


BATCH_PHASE = {1: 1, 2: 2, 3: 3, 4: 3}


def current_batch() -> int:
    """本票最晚一筆實作許可之批次（審計 `impl_token_issued` 之 batch 欄；與錨點同一筆）。"""
    from tests.feature_engineering.test_framepath_disposition import AUDIT_REL, TICKET_ROOT

    batch = None
    for line in (REPO / AUDIT_REL).read_text(encoding="utf-8", errors="replace").splitlines():
        if '"impl_token_issued"' not in line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("event") == "impl_token_issued" and ev.get("root") == TICKET_ROOT:
            batch = ev.get("batch")
    if batch is None or int(batch) not in BATCH_PHASE:
        raise GateError(f"審計紀錄無本票實作許可或批次不合法：{batch!r}")
    return int(batch)


def main(argv: Sequence[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=None, help="junit 暫存目錄（預設系統暫存下固定名，供接續）")
    ap.add_argument("--anchor-worktree", default=None)
    ap.add_argument("--plan", action="store_true",
                    help="只產出 D8 挑選（選入／未跑逐項理由、估時與 admission）收據，不執行測試本體")
    ap.add_argument("--timings", action="append", default=[],
                    help="估時來源目錄（其下 junit xml；可重複）；本執行器之結果目錄恆納入")
    ap.add_argument("--admit", default=None,
                    help="admission 非 within（估時未知或逾預算）時，呈報後以該次挑選之 inputs_digest 批准執行")
    args = ap.parse_args(argv)
    batch = current_batch()
    args.phase = BATCH_PHASE[batch]
    args.receipt = str(REPO / f"handoffs/run_receipts/framepath-b{batch}-affected.json")
    out = Path(args.out or Path(tempfile.gettempdir()) / f"framepath_affected_b{batch}").resolve()
    anchor = resolve_anchor()
    env = dict(os.environ, FRAMEPATH_PHASE=str(args.phase), PYTHONPATH=str(REPO))
    manifest = json.loads((REPO / MANIFEST_REL).read_text(encoding="utf-8"))
    timing_dirs = [out, *[Path(t) for t in args.timings]]
    sel = plan(REPO, anchor, args.phase, manifest, env, timing_dirs)
    a_ids = [n for f in A_GROUP_BY_PHASE[args.phase] for n in collect(f, REPO, env)]
    times = load_times(REPO, timing_dirs)
    adm = admission([*a_ids, *sel["selected"]], times)
    if args.plan:
        plan_path = REPO / f"handoffs/run_receipts/framepath-b{batch}-affected-plan.json"
        plan_path.write_text(json.dumps({"spec": "docs/FRAMEPATH_SPEC.md v21 D8", "phase": args.phase, "anchor": anchor,
                                         **sel, "admission": adm}, ensure_ascii=False, indent=1, default=sorted) + "\n",
                             encoding="utf-8")
        print(f"FRAMEPATH affected plan：collected={sum(len(v) for v in sel['collected'].values())} "
              f"selected={len(sel['selected'])} skipped={len(sel['skipped'])} admission={adm['status']} "
              f"known={adm['known_seconds']}s unknown={len(adm['unknown'])} inputs_digest={sel['inputs_digest']} "
              f"→ {plan_path.relative_to(REPO)}")
        return 0
    if adm["status"] != "within" and args.admit != sel["inputs_digest"]:
        raise GateError(f"admission={adm['status']}（已知 {adm['known_seconds']} 秒、估時未知 {len(adm['unknown'])} 項、"
                        f"預算 {adm['budget_seconds']} 秒）：先 --plan 呈報，批准後以 --admit {sel['inputs_digest']} 執行")
    anchor_wt = Path(args.anchor_worktree).resolve() if args.anchor_worktree else make_anchor_worktree(anchor)
    verify_anchor_worktree(anchor_wt, anchor)
    if not (anchor_wt / "data_cache").exists():
        (anchor_wt / "data_cache").symlink_to(REPO / "data_cache")
    anchor_env = dict(os.environ, PYTHONPATH=str(anchor_wt))
    b_group, c_group = sel["groups"]["B"], sel["groups"]["C"]

    a_failures: List[str] = []
    a_results: Dict[str, Dict[str, str]] = {}
    # 殘差定義探針（審查 r52：A 組與選入之 B／C 皆記；證據為「定義被呼叫」，非改動行之執行）：每檔獨立目錄，
    # 重跑時清空、沿用舊結果檔時一併沿用其觀測
    probe_root = out / "def_probe"

    def probe_env(name: str, fresh: bool) -> Dict[str, str]:
        d = probe_root / name
        d.mkdir(parents=True, exist_ok=True)
        if fresh:
            for stale in d.glob("*.json"):
                stale.unlink()
        return dict(env, PYTHONPATH=f"{REPO}{os.pathsep}{REPO / 'scripts'}", FRAMEPATH_DEF_PROBE_DIR=str(d),
                    FRAMEPATH_DEF_PROBE_DEFS=",".join(sel["residual_defs"]))

    probe_dirs: List[Path] = []
    for f in A_GROUP_BY_PHASE[args.phase]:
        ids = collect(f, REPO, env)
        name = "A_" + f.replace("/", "_")
        probe_dirs.append(probe_root / name)
        rc, res = run_file(f, out / "a_junit" / (f.replace("/", "_") + ".xml"), REPO, probe_env(name, True), None,
                           PROBE_PLUGIN_ARGS)
        a_results.update(res)
        a_failures += [n for n in ids if res.get(n, {}).get("outcome") != "passed"]
        if rc not in RUN_RC_OK:
            a_failures.append(f"{f}（pytest rc={rc}）")

    expected: List[str] = []
    batch: Dict[str, Dict[str, str]] = {}
    per_file: Dict[str, Dict[str, object]] = {}
    incomplete: List[str] = []
    for f in b_group + c_group + list(sel["extra_files"]):
        all_ids = sel["collected"][f]
        ids = [n for n in all_ids if n in sel["selected"]]
        expected += ids
        if not ids:
            per_file[f] = {"collected": len(all_ids), "expected": 0, "results": 0, "rc": None}
            continue
        whole = len(ids) == len(all_ids)
        xml = out / "junit" / (f.replace("/", "_") + ".xml")
        meta = xml.with_suffix(".meta.json")
        key = state_key(REPO, f, args.phase, env)
        res: Dict[str, Dict[str, str]] = {}
        rc: Optional[int] = None
        if xml.is_file() and meta.is_file():
            m = json.loads(meta.read_text(encoding="utf-8"))
            if m.get("state_key") == key and m.get("rc") in RUN_RC_OK:
                res, rc = junit_results(xml.read_text(encoding="utf-8"), f), m["rc"]
        name = "BC_" + f.replace("/", "_")
        probe_dirs.append(probe_root / name)
        if rc is None or set(ids) - set(res):
            rc, res = run_file(f, xml, REPO, probe_env(name, True), None if whole else ids, PROBE_PLUGIN_ARGS)
            meta.write_text(json.dumps({"state_key": key, "rc": rc, "file": f}), encoding="utf-8")
        if rc not in RUN_RC_OK or set(ids) - set(res):
            incomplete.append(f)
        # 只計入選入之 nodeid（沿用之舊結果檔可能含整檔結果）；junit 名稱對不上者以 missing 擋下
        batch.update({n: r for n, r in res.items() if n in sel["selected"] or n not in all_ids})
        per_file[f] = {"collected": len(all_ids), "expected": len(ids), "results": len(set(ids) & set(res)), "rc": rc}

    not_passed = [n for n in expected if n in batch and batch[n]["outcome"] != "passed"]
    anchor_res: Dict[str, Dict[str, str]] = {}
    for f in dict.fromkeys(n.split("::", 1)[0] for n in not_passed):
        ids = [n for n in not_passed if n.startswith(f + "::")]
        if (anchor_wt / f).is_file():
            arc, res = run_file(f, out / "anchor_junit" / (f.replace("/", "_") + ".xml"), anchor_wt, anchor_env, ids)
            anchor_res.update(anchor_usable(arc, res, ids))
    result = classify(expected, batch, anchor_res)
    hits = set().union(*(probe_hits(d) for d in probe_dirs)) if probe_dirs else set()
    unexecuted = sorted(set(sel["residual_defs"]) - hits)
    passed = verdict(result, a_failures, incomplete, unexecuted)
    receipt = {
        "spec": "docs/FRAMEPATH_SPEC.md v21 D8", "phase": args.phase, "repo_head": _git(REPO, "rev-parse", "HEAD").strip(),
        "selection": {"selected": sel["selected"], "skipped": sel["skipped"], "s2_symbols": sel["s2_symbols"],
                      "align_triggered": sel["align_triggered"], "light_files": sel["light_files"],
                      "invariance_baseline_sha256": sel["invariance_baseline_sha256"],
                      "inputs_digest": sel["inputs_digest"], "admission": adm, "admitted": args.admit is not None},
        "residual_defs": sel["residual_defs"], "residual_executed": sorted(hits & set(sel["residual_defs"])),
        "residual_unexecuted": unexecuted,
        "anchor": anchor, "anchor_worktree": str(anchor_wt), "groups": {"A": list(A_GROUP_BY_PHASE[args.phase]),
                                                                        "B": b_group, "C": c_group},
        "a_failures": a_failures, "incomplete_files": incomplete, "per_file": per_file,
        "expected_count": len(expected), "result_count": len(set(expected) & set(batch)),
        **result,
        "head_red_identity": {n: list(failure_identity(batch[n])) for n in result["head_red"]},
        "caused_detail": {n: {"batch": list(failure_identity(batch[n])),
                              "anchor": list(failure_identity(anchor_res[n])) if n in anchor_res else None}
                          for n in result["caused"]},
        "pass": passed,
    }
    Path(args.receipt).parent.mkdir(parents=True, exist_ok=True)
    Path(args.receipt).write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"FRAMEPATH affected gate：A_fail={len(a_failures)} expected={len(expected)} incomplete={len(incomplete)} "
          f"missing={len(result['missing'])} unexpected={len(result['unexpected'])} caused={len(result['caused'])} "
          f"head_red={len(result['head_red'])} pass={passed}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

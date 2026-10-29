"""ICPERF Phase 0（docs/ICPERF_SPEC.md §G、Task 0.1／0.2）：以現行碼凍結改前輸出、寫出檔捕獲與比對、規模盤點之路徑清冊。

空殼（施工前）：全部入口 `raise NotImplementedError`；具名驗收見 `tests/momentum/Analysis/test_icperf_gate.py`。

用法（重型，列 `scripts/heavy_commands.json` 之 `self_watched`：須背景、先寫估時收據〔coverage_path_ids＝ICPERF-BUDGET-1／-2〕，
子行程一律經本檔 `run_watched` 以共用監看啟動）：
  venv/bin/python scripts/icperf_freeze_baseline.py freeze [--out tests/_golden/icperf/pre_change.json]
  venv/bin/python scripts/icperf_freeze_baseline.py repro --cols 500
  venv/bin/python scripts/icperf_freeze_baseline.py inventory --out handoffs/run_receipts/<日期>-icperf-path-inventory.json
  venv/bin/python scripts/icperf_freeze_baseline.py measure --inventory <清冊> --out handoffs/run_receipts/<日期>-icperf-scale-before.json

凍結檔 `tests/_golden/icperf/pre_change.json` 之形狀（§G）：
  {"schema": "icperf-pre-change/1", "code_state": {...}, "volatile": [<每次必異欄位之路徑，FACT-RECEIPT 寫入 SPEC>],
   "items": {
     "ic_report"|"deep_analysis"|"event_report"|"icfirst_post_ic": {
        "request": {...請求設定...}, "output_roots": [<cwd 根相對 POSIX>...],
        "roots": {"cwd": <本次執行之 cwd 根，解析後絕對路徑>, "iso": <隔離目錄，解析後絕對路徑>},
        "response": {<欄位路徑>: <sha256>},            # 回應／回傳物件之全部欄位（flatten_fields；逐特徵來源不重複攤平）
        "files": {<path_key>: describe_file(...)},      # 快照差集之全部寫出檔
        "transient": [<path_key>...],                   # 審計記錄有而差集無變化（寫後刪除），記入不比
        "features": {<特徵>: {<欄位>: {"sha256", "nan_mask_sha256"}}},   # 第 (1)、(4) 項（深度分析由回應全部欄位涵蓋）
        "selected": [<第 6 段後之倖存者>...],          # 第 (1)、(4) 項（寫出之 ic_survivors_<case_id>.json 之 feature_names）
        "pit_labels": {<特徵>: {"q", "q_insufficient", "skipped_all_nan", "label_sha256"|None, "label_nan_count"}}},
     "stage5_subset": {"seed": 20261027, "n_cols_requested": 2000, "stage_cols": <實際進第 5 段欄數>,
        "features": {...同上...}, "pit_labels": {...同上...}}}}

path_key 規則（SPEC §G (b) 三根前綴）：本次執行之 cwd 根（新建之隔離工作目錄）之下＝相對 POSIX；隔離目錄（TMPDIR／
HOME）之下＝`<iso>/<相對 POSIX>`；repo 根之下＝`<repo>/<相對 POSIX>`；多根皆含時取最具體（解析後最長）之根；三根皆不含
＝解析後絕對路徑（只出現於 §G (c) fail-closed 之訊息）。

逐特徵欄位（"features"）之來源與命名（SPEC §G baseline 內容與摘要粒度）：`feature_tables(item)` 所列之逐特徵來源——
IC 報告（dict）之 `summary_table`（list[dict]，以 `feature_name` 為鍵）⇒ 每列每欄（`feature_name` 除外）一值，欄位名＝
"/summary_table/<欄名>"（JSON pointer 跳脫），值摘要＝`value_digest(列[欄])`；以特徵名為鍵之 `quantile_returns`、
`coverage_analysis`、`turnover_analysis` ⇒ 每特徵每來源整段子樹一值，欄位名＝來源 pointer（如 "/quantile_returns"），
值摘要＝`value_digest(來源[特徵])`。逐特徵來源之子路徑（"<來源 pointer>/…"）於 "response" 不重複攤平（兩者聯集＝回應
全部欄位；來源本身為空容器時仍依 `flatten_fields` 以純量記於 "response"）。

PIT 標籤（"pit_labels"）：照單調性之現行輸入定義（特徵與標籤同時非 NaN 之列壓縮、`_select_num_quantiles` 選 q、
q=3 退回）；`q`＝最終採用之 q；`q_insufficient`＝最終 q 小於請求 q（樣本數不足而降為 3，或 bin 數不足退回 3）；
`label_sha256`＝壓縮後之 PIT 標籤序列轉 float64 之原生位元組 sha256；`label_nan_count`＝其中 NaN 數。

施工前註記（ICPERF 施工清單審查 r10 群集 A）：本檔列 `scripts/heavy_commands.json` 之 `self_watched`，heavy_run_guard
以 AST 驗原始碼確有 `run_watched(...)` 呼叫；空殼只有定義、無呼叫 ⇒ 實跑時被擋屬施工前預期之 fail-closed。實作之
`run_watched` 須呼叫共用監看（`_watchdog.run_watched`）。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

# 本檔亦由子行程之 sitecustomize 以檔案路徑載入（寫入審計），故模組層只 import 標準函式庫；numpy／pandas／h5py
# 一律於函式內載入。

REPO = Path(__file__).resolve().parents[1]
PROBES_DIR = REPO / "handoffs" / "run_receipts" / "numview_probes"
GOLDEN_PATH = REPO / "tests" / "_golden" / "icperf" / "pre_change.json"
CELL = "A_BTCUSDT_1h"
SEED = 20261027
SUBSET_COLS = 2000
REPRO_COLS = 500
SCALE_POINTS = (500, 1000, 2000)

#: §G (1)–(5)：A 格完整 IC 報告、2,000 欄子集第 5 段、A 格深度分析、A 格 K 線條件式事件 IC 報告、A 格 IC-first post-IC
#: 輸出（V2 parquet artifact；IC-first 不寫 HDF5）
G_ITEMS = ("ic_report", "stage5_subset", "deep_analysis", "event_report", "icfirst_post_ic")
#: 須含「回應全部欄位＋快照差集之全部寫出檔」之項（§G 凍結範圍：第 (1)、(3)、(4)、(5) 項）
OUTPUT_ITEMS = ("ic_report", "deep_analysis", "event_report", "icfirst_post_ic")

#: SPEC §G「各項請求設定」：前端 IC 頁初始狀態實際送出之 payload（衰減照頁面預設開啟）。`config_override`＝
#: `buildConfigOverride(defaultConfig)`（`frontend/src/lib/icConfigOverride.ts`；值見 `frontend/src/store/icAnalysisStore.ts`
#: 之 `defaultConfig`）併 `feature_tiers`（初始 tier `featureTier: 'intermediate'`、`PRESET_TOGGLES.intermediate` 之開關、
#: 鍵集 `momentum/Analysis/contracts/ui_stage_toggles.json` 之 `stage_keys`；組裝 `getEffectiveConfig` 與
#: `frontend/src/hooks/useICAnalysis.ts` 之 payload）。寫死於此；前端改預設 ⇒ 秒級契約測試
#: （`test_icperf_gate.py::test_boundary_25_ic_page_default_payload_matches_frontend`）紅，須重凍。
IC_PAGE_DEFAULT_PAYLOAD: Dict[str, Any] = {
    "config_override": {
        "thresholds": {"ic_mean_min": 0.02, "icir_min": 0.5, "p_value_max": 0.05, "monotonicity_score_min": 0.6},
        "redundancy": {"correlation_threshold": 0.7},
        "labels": {"horizons": [1, 2, 3, 5, 8, 13, 21]},
        "feature_tiers": {
            "active_preset": "intermediate",
            "custom_overrides": {"stage_overrides": {
                "ic_decay": True, "grouped_ic": True, "turnover_analysis": True, "event_filtering": True,
                "ai_summary": True, "fdr_correction": True, "marginal_ic": True}},
        },
    },
    "feature_tiers": {
        "active_preset": "intermediate",
        "custom_overrides": {"stage_overrides": {
            "ic_decay": True, "grouped_ic": True, "turnover_analysis": True, "event_filtering": True,
            "ai_summary": True, "fdr_correction": True, "marginal_ic": True}},
    },
}

#: 寫出捕獲記錄之審計事件；本行程之 hook 與注入子行程之 sitecustomize 皆於呼叫當下讀本常數（mutation 探針改之）
AUDIT_EVENTS = ("open", "os.rename", "os.replace")
#: `open` 事件之 mode 含任一字元即視為寫入／附加／建立；`os.open` 依 flags（O_WRONLY／O_RDWR／O_CREAT／O_APPEND）判定
WRITE_MODE_CHARS = frozenset("wax+")
#: 子行程經此環境變數取得同一審計記錄檔
CAPTURE_LOG_ENV = "ICPERF_WRITE_AUDIT_LOG"
#: 快照排除之目錄名（任一層）：git、虛擬環境、位元組碼快取、測試選取工具狀態目錄
SNAPSHOT_EXCLUDE_DIRS = (".git", "venv", "__pycache__", ".testsel")
#: numba 快取檔副檔名（任一目錄；另含 NUMBA_CACHE_DIR 所指目錄）
NUMBA_CACHE_SUFFIXES = (".nbi", ".nbc")

INVENTORY_GLOB = "handoffs/run_receipts/*-icperf-path-inventory.json"
SCALE_BEFORE_GLOB = "handoffs/run_receipts/*-icperf-scale-before.json"

_STUB = "ICPERF Phase 0（docs/ICPERF_SPEC.md §G、Task 0.1／0.2）尚未施工"


class FreezeError(RuntimeError):
    """凍結／比對之 fail-closed 錯誤：審計記錄之路徑或輸出根落在快照範圍外、收據份數不為一等；訊息須含具名路徑。"""


def _load(name: str, path: Path) -> Any:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclass 定義於載入期需自模組表取得命名空間
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def path_key(path: Path, repo_root: Path, prefixes: Optional[Mapping[str, Path]] = None) -> str:
    """path_key（SPEC §G (b)）：`repo_root`（本次執行之工作目錄）之下＝相對 POSIX；`prefixes` 所列根（如
    {"<iso>": 隔離目錄, "<repo>": repo 根}）之下＝`<前綴>/<相對 POSIX>`（多根皆含時取最深者）；其餘＝解析後絕對路徑。
    前綴使隔離目錄與 repo 之寫出於跨次執行可比。"""
    p = os.path.realpath(path)
    best: Optional[Tuple[str, str]] = None
    for prefix, root in [("", repo_root)] + list((prefixes or {}).items()):
        r = os.path.realpath(root)
        if (p == r or p.startswith(r.rstrip(os.sep) + os.sep)) and (best is None or len(r) > len(best[1])):
            best = (prefix, r)
    if best is None:
        return p
    rel = Path(os.path.relpath(p, best[1])).as_posix()
    return rel if best[0] == "" else f"{best[0]}/{rel}"


def _key_path(key: str, repo_root: Path, prefixes: Optional[Mapping[str, Path]] = None) -> Path:
    head, _, rest = key.partition("/")
    if prefixes and head in prefixes:
        return Path(prefixes[head]) / rest
    return Path(key) if os.path.isabs(key) else Path(repo_root) / key


def _under(path: str, root: Path) -> bool:
    p, r = os.path.realpath(path), os.path.realpath(root)
    return p == r or p.startswith(r.rstrip(os.sep) + os.sep)


# ── §G (a)(b)(c) 寫出捕獲 ─────────────────────────────────────────────────────────────────────────────

#: 本行程之審計狀態：記錄檔 fd、其解析後路徑、hook 是否已裝；`_AUDIT_TLS.busy` 防 hook 內之 I/O 自我遞迴
_AUDIT_STATE: Dict[str, Any] = {"fd": None, "path": None, "installed": False}
_AUDIT_TLS = threading.local()
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC


def _as_path_str(p: Any) -> Optional[str]:
    if isinstance(p, int):
        return None  # 以 fd 開檔（os.fdopen 等）：該 fd 之開檔已另記
    try:
        return os.fsdecode(os.fspath(p))
    except TypeError:
        return None


def _audit_record(event: str, args: Tuple[Any, ...]) -> Optional[Dict[str, Any]]:
    if event == "open":
        raw, mode, flags = (tuple(args) + (None, None, None))[:3]
        path = _as_path_str(raw)
        if path is None:
            return None
        if isinstance(mode, str):
            writes = any(c in WRITE_MODE_CHARS for c in mode)
        else:
            writes = isinstance(flags, int) and bool(flags & _WRITE_FLAGS)
        if not writes:
            return None
        real = os.path.realpath(path)
        if real == _AUDIT_STATE["path"]:
            return None
        try:  # 既存之非一般檔（/dev/null 等字元裝置、FIFO）不是寫出物
            if not stat.S_ISREG(os.stat(real).st_mode) and not stat.S_ISDIR(os.stat(real).st_mode):
                return None
        except OSError:
            pass  # 尚不存在＝新建之一般檔
        return {"event": event, "path": real, "src": None, "mode": mode if isinstance(mode, str) else None,
                "flags": flags if isinstance(flags, int) else None, "pid": os.getpid()}
    src, dst = _as_path_str(args[0]), _as_path_str(args[1])
    if dst is None:
        return None
    return {"event": event, "path": os.path.realpath(dst), "src": os.path.realpath(src) if src else None,
            "mode": None, "flags": None, "pid": os.getpid()}


def _audit_hook(event: str, args: Tuple[Any, ...]) -> None:
    # CPython 之 os.replace 亦發 "os.rename" 審計事件；`install_write_audit` 包裝 os.replace，其呼叫期間之事件記為 os.replace
    if event == "os.rename" and getattr(_AUDIT_TLS, "replacing", False):
        event = "os.replace"
    if event not in AUDIT_EVENTS or _AUDIT_STATE["fd"] is None or getattr(_AUDIT_TLS, "busy", False):
        return
    _AUDIT_TLS.busy = True
    try:
        try:
            rec = _audit_record(event, args)
        except Exception as exc:  # 審計不得靜默漏記：寫錯誤列，`read_write_log` 見之即 FreezeError
            rec = {"event": "audit_error", "path": None, "detail": f"{event}: {exc!r}", "pid": os.getpid()}
        if rec is not None:
            os.write(_AUDIT_STATE["fd"], (json.dumps(rec, ensure_ascii=False) + "\n").encode("utf-8"))
    finally:
        _AUDIT_TLS.busy = False


def install_write_audit(log_path: Path) -> None:
    """於本行程以 `sys.addaudithook` 記錄 `AUDIT_EVENTS` 之寫入事件至 `log_path`（JSON lines）。

    每列 {"event": "open"|"os.rename"|"os.replace", "path": <解析後絕對路徑；rename／replace 為目的地>,
    "src": <rename／replace 之來源或 None>, "mode": <open 之 mode 或 None>, "flags": <os.open 之 flags 或 None>,
    "pid": <行程 id>}；只記寫入／附加／建立模式之開檔（見 `WRITE_MODE_CHARS`），唯讀開檔不記；記錄檔本身之寫入不記。
    hook 只裝一次，重複呼叫改切換記錄檔。多行程以 O_APPEND 寫同一檔，每列一次 write。CPython 對 os.replace 只發
    "os.rename" 事件，故安裝時包裝 `os.replace`，其呼叫期間之該事件記為 "os.replace"（目的地照記，不因名稱而漏）。"""
    _AUDIT_TLS.busy = True
    try:
        old = _AUDIT_STATE["fd"]
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(log_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        _AUDIT_STATE.update(fd=fd, path=os.path.realpath(log_path))
        if old is not None:
            os.close(old)
    finally:
        _AUDIT_TLS.busy = False
    if not _AUDIT_STATE["installed"]:
        sys.addaudithook(_audit_hook)
        _orig_replace = os.replace

        def _replace(src: Any, dst: Any, *a: Any, **k: Any) -> None:
            _AUDIT_TLS.replacing = True
            try:
                return _orig_replace(src, dst, *a, **k)
            finally:
                _AUDIT_TLS.replacing = False

        os.replace = _replace  # type: ignore[assignment]
        _AUDIT_STATE["installed"] = True


def capture_sitecustomize_source(log_path: Path) -> str:
    """回注入子行程之 sitecustomize 原始碼：讀 `CAPTURE_LOG_ENV`（缺則用 `log_path`）安裝與 `install_write_audit` 相同之
    hook（事件集合取呼叫當下之 `AUDIT_EVENTS`），並串接 sys.path 上原有之 sitecustomize（含共用監看之堆疊傾印注入）。
    串接只找 sys.path 上位於本檔目錄之後者（之前者即先載入而串接到本檔之注入，例如共用監看）；同行程只執行一次。"""
    return f'''\
import importlib.util as _ic_iu, os as _ic_os, sys as _ic_sys
if not getattr(_ic_sys, "_icperf_audit_done", False):
    _ic_sys._icperf_audit_done = True
    _ic_spec = _ic_iu.spec_from_file_location("_icperf_write_audit", {str(Path(__file__).resolve())!r})
    _ic_mod = _ic_iu.module_from_spec(_ic_spec)
    _ic_spec.loader.exec_module(_ic_mod)
    _ic_mod.AUDIT_EVENTS = {tuple(AUDIT_EVENTS)!r}
    _ic_mod.install_write_audit(_ic_os.environ.get({CAPTURE_LOG_ENV!r}) or {str(log_path)!r})
    _ic_here = _ic_os.path.dirname(_ic_os.path.abspath(__file__))
    _ic_paths = [_ic_os.path.abspath(_p or ".") for _p in _ic_sys.path]
    _ic_after = _ic_paths[_ic_paths.index(_ic_here) + 1:] if _ic_here in _ic_paths else []
    for _ic_p in _ic_after:
        _ic_cand = _ic_os.path.join(_ic_p, "sitecustomize.py")
        if _ic_p != _ic_here and _ic_os.path.isfile(_ic_cand):
            _ic_cs = _ic_iu.spec_from_file_location("_icperf_chained_sitecustomize", _ic_cand)
            _ic_cm = _ic_iu.module_from_spec(_ic_cs)
            _ic_cs.loader.exec_module(_ic_cm)
            break
'''


def isolated_env(base_env: Mapping[str, str], iso_root: Path) -> Dict[str, str]:
    """回 `base_env` 之副本，`TMPDIR`＝`iso_root/tmp`、`HOME`＝`iso_root/home`（皆建立、互異）；其餘鍵原樣保留。"""
    env = dict(base_env)
    tmp, home = Path(iso_root) / "tmp", Path(iso_root) / "home"
    tmp.mkdir(parents=True, exist_ok=True)
    home.mkdir(parents=True, exist_ok=True)
    env["TMPDIR"], env["HOME"] = str(tmp), str(home)
    return env


def capture_env(base_env: Mapping[str, str], *, log_path: Path, iso_root: Path, site_dir: Path) -> Dict[str, str]:
    """子行程環境＝`isolated_env` ＋ `CAPTURE_LOG_ENV`＝`log_path` ＋ `site_dir`（寫入 `capture_sitecustomize_source`）
    前置 `PYTHONPATH`；孫行程繼承同一環境，故寫入進同一記錄。另設 `PYTHONDONTWRITEBYTECODE=1`：位元組碼快取寫入
    與產品輸出無關，且可能落在快照範圍外而誤觸 (c)。"""
    env = isolated_env(base_env, iso_root)
    site_dir = Path(site_dir)
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "sitecustomize.py").write_text(capture_sitecustomize_source(log_path), encoding="utf-8")
    env[CAPTURE_LOG_ENV] = str(log_path)
    env["PYTHONPATH"] = os.pathsep.join([str(site_dir)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def read_write_log(log_path: Path) -> List[Dict[str, Any]]:
    """讀審計記錄（`install_write_audit` 之列格式）；檔不存在 ⇒ 空清單；列不可解析或含審計錯誤列 ⇒ FreezeError。"""
    log_path = Path(log_path)
    if not log_path.is_file():
        return []
    out = []
    for n, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            raise FreezeError(f"{log_path}:{n} 審計記錄列不可解析：{exc}") from exc
        if rec.get("event") == "audit_error":
            raise FreezeError(f"{log_path}:{n} 審計 hook 失敗（不得漏記）：{rec.get('detail')}")
        out.append(rec)
    return out


#: 檔案雜湊快取（本行程）：鍵＝(解析後路徑, 大小, mtime_ns)；大小與 mtime 皆未變即視為內容未變（同 rsync 判準）
_SHA_CACHE: Dict[Tuple[str, int, int], str] = {}


def _file_sha256(path: str) -> str:
    st = os.stat(path)
    key = (path, st.st_size, st.st_mtime_ns)
    if key not in _SHA_CACHE:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 22), b""):
                h.update(chunk)
        _SHA_CACHE[key] = h.hexdigest()
    return _SHA_CACHE[key]


def snapshot_files(roots: Sequence[Path], *, repo_root: Path,
                   prefixes: Optional[Mapping[str, Path]] = None) -> Dict[str, str]:
    """對 `roots` 下全部檔案取 {path_key: 位元組 sha256}；排除任一層名為 `SNAPSHOT_EXCLUDE_DIRS` 之目錄、副檔名為
    `NUMBA_CACHE_SUFFIXES` 之檔與呼叫當下環境變數 `NUMBA_CACHE_DIR` 所指目錄之整棵（不論副檔名；未設則不排除該目錄）；
    不跟隨指向 roots 外之 symlink。雜湊以（路徑、大小、mtime）快取。"""
    nd = os.environ.get("NUMBA_CACHE_DIR")
    numba_dir = os.path.realpath(nd) if nd else None
    real_roots = [os.path.realpath(r) for r in roots]
    out: Dict[str, str] = {}
    for root in real_roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SNAPSHOT_EXCLUDE_DIRS
                           and not (numba_dir is not None and os.path.realpath(os.path.join(dirpath, d)) == numba_dir)]
            for fn in filenames:
                if fn.endswith(NUMBA_CACHE_SUFFIXES):
                    continue
                full = os.path.join(dirpath, fn)
                if os.path.islink(full) and not any(_under(full, r) for r in real_roots):
                    continue
                if os.path.islink(full) or not os.path.isfile(full):
                    target = os.path.realpath(full)
                    if not os.path.isfile(target) or not any(_under(target, r) for r in real_roots):
                        continue
                out[path_key(Path(full), repo_root, prefixes)] = _file_sha256(os.path.realpath(full))
    return out


def snapshot_diff(before: Mapping[str, str], after: Mapping[str, str]) -> Dict[str, List[str]]:
    """回 {"added": [...], "changed": [...], "removed": [...]}（皆排序之 path_key）。"""
    return {"added": sorted(set(after) - set(before)),
            "changed": sorted(k for k in set(after) & set(before) if after[k] != before[k]),
            "removed": sorted(set(before) - set(after))}


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _array_sha(arr: Any) -> str:
    """陣列之 sha256：數值／定長字串等原生 dtype 取 C 連續位元組（前綴 dtype 與 shape）；object dtype 以正準 JSON。"""
    import numpy as np

    a = np.asarray(arr)
    head = f"{a.dtype.str}|{a.shape}|".encode("utf-8")
    if a.dtype.kind == "O":
        return _sha_bytes(head + _canonical_json([_jsonable(v) for v in a.ravel().tolist()]))
    return _sha_bytes(head + np.ascontiguousarray(a).tobytes())


def _nan_mask(arr: Any) -> Any:
    import numpy as np
    import pandas as pd

    return np.asarray(pd.isna(np.asarray(arr, dtype=object) if np.asarray(arr).dtype.kind == "O" else np.asarray(arr)))


def _jsonable(v: Any) -> Any:
    import numpy as np

    if isinstance(v, bytes):
        return {"__bytes__": v.hex()}
    if isinstance(v, np.generic):
        return {"__np__": v.dtype.str, "v": v.item() if v.dtype.kind != "V" else v.tobytes().hex()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    return {"__repr__": f"{type(v).__module__}.{type(v).__qualname__}", "v": str(v)}


def _canonical_json(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=True).encode("utf-8")


def hdf5_digest(path: Path) -> Dict[str, Dict[str, Any]]:
    """HDF5 逐物件摘要：{<物件名，如 "/" "/g" "/g/v">: {"kind": "group"|"dataset", "attrs": {<屬性名>: <sha256>},
    資料集另 "dtype", "shape", "sha256"（原生 dtype 位元組；依首軸分塊串接雜湊，與整塊 tobytes 相同）}}。"""
    import h5py
    import numpy as np

    out: Dict[str, Dict[str, Any]] = {}

    def attrs_of(obj: Any) -> Dict[str, str]:
        return {str(k): _array_sha(obj.attrs[k]) for k in sorted(obj.attrs.keys())}

    def visit(name: str, obj: Any) -> None:
        key = "/" + name
        if isinstance(obj, h5py.Dataset):
            h = hashlib.sha256(f"{obj.dtype.str}|{obj.shape}|".encode("utf-8"))
            if obj.dtype.kind == "O" or h5py.check_string_dtype(obj.dtype) is not None:
                vals = obj.asstr()[()] if h5py.check_string_dtype(obj.dtype) is not None else obj[()]
                h.update(_canonical_json(_jsonable(np.asarray(vals, dtype=object).ravel().tolist())))
            elif obj.shape == () or obj.ndim == 0:
                h.update(np.ascontiguousarray(obj[()]).tobytes())
            else:
                row_bytes = max(1, int(np.prod(obj.shape[1:], dtype=np.int64)) * obj.dtype.itemsize)
                step = max(1, (1 << 26) // row_bytes)
                for i in range(0, obj.shape[0], step):
                    h.update(np.ascontiguousarray(obj[i:i + step]).tobytes())
            out[key] = {"kind": "dataset", "attrs": attrs_of(obj), "dtype": obj.dtype.str,
                        "shape": list(obj.shape), "sha256": h.hexdigest()}
        else:
            out[key] = {"kind": "group", "attrs": attrs_of(obj)}

    with h5py.File(path, "r") as f:
        out["/"] = {"kind": "group", "attrs": attrs_of(f)}
        f.visititems(visit)
    return out


def _is_scalar(v: Any) -> bool:
    import numpy as np

    return v is None or isinstance(v, (bool, int, float, str, np.generic))


def _ptr_seg(seg: Any) -> str:
    return str(seg).replace("~", "~0").replace("/", "~1")


def _as_container(obj: Any) -> Any:
    import dataclasses

    import pandas as pd

    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if hasattr(obj, "model_dump") and not isinstance(obj, (pd.DataFrame, pd.Series)):
        return obj.model_dump()
    return obj


def flatten_fields(obj: Any) -> Dict[str, str]:
    """把回應物件攤平為 {<欄位路徑>: <sha256>}。路徑規則（boundary_01 之獨立 oracle 依此重算鍵集合）：根＝""；
    dict 每鍵接 "/<鍵>"（鍵以 str() 轉、`~`→`~0`、`/`→`~1`）；元素皆為純量（None／bool／int／float／str／numpy 純量）
    之非空 list／tuple ⇒ "<路徑>#values"、"<路徑>#nan_mask"（整段一值）；其餘 list／tuple 每元素接 "/<索引>"，遞迴；
    DataFrame ⇒ "<路徑>#index" 與每欄 "<路徑>/<欄名>#values"、"<路徑>/<欄名>#nan_mask"；Series／ndarray ⇒
    "<路徑>#values"、"<路徑>#nan_mask"（Series 另 "<路徑>#index"）；其餘（純量、None）⇒ "<路徑>" 以正準 JSON 位元組。
    值取原生 dtype 位元組之 sha256。dataclass 與具 model_dump 之物件先轉為 dict；空 dict／list 視為純量。"""
    import numpy as np
    import pandas as pd

    out: Dict[str, str] = {}

    def walk(o: Any, path: str) -> None:
        o = _as_container(o)
        if isinstance(o, pd.DataFrame):
            out[f"{path}#index"] = _array_sha(o.index.to_numpy())
            for i, c in enumerate(o.columns):
                col = o.iloc[:, i].to_numpy()
                out[f"{path}/{_ptr_seg(c)}#values"] = _array_sha(col)
                out[f"{path}/{_ptr_seg(c)}#nan_mask"] = _array_sha(_nan_mask(col))
        elif isinstance(o, pd.Series):
            vals = o.to_numpy()
            out[f"{path}#index"] = _array_sha(o.index.to_numpy())
            out[f"{path}#values"] = _array_sha(vals)
            out[f"{path}#nan_mask"] = _array_sha(_nan_mask(vals))
        elif isinstance(o, np.ndarray):
            out[f"{path}#values"] = _array_sha(o)
            out[f"{path}#nan_mask"] = _array_sha(_nan_mask(o))
        elif isinstance(o, dict) and o:
            for k, v in o.items():
                walk(v, f"{path}/{_ptr_seg(k)}")
        elif isinstance(o, (list, tuple)) and o and all(_is_scalar(v) for v in o):
            arr = np.asarray(list(o), dtype=object)  # 純量序列整段一值（SPEC §G 摘要粒度）
            out[f"{path}#values"] = _array_sha(arr)
            out[f"{path}#nan_mask"] = _array_sha(_nan_mask(arr))
        elif isinstance(o, (list, tuple)) and o:
            for i, v in enumerate(o):
                walk(v, f"{path}/{i}")
        else:
            out[path] = _sha_bytes(_canonical_json(_jsonable(o)))

    walk(obj, "")
    return out


def describe_file(path: Path) -> Dict[str, Any]:
    """單一寫出檔之摘要：{"sha256": <位元組>, "hdf5": hdf5_digest(...)|None, "fields": flatten_fields(<JSON 內容>)|None}；
    HDF5 以檔頭簽章判定，JSON 以副檔名 .json 判定（內容不可解析 ⇒ fields 為 None，仍以位元組比）。"""
    path = Path(path)
    real = os.path.realpath(path)
    with open(real, "rb") as fh:
        head = fh.read(8)
    fields = None
    if path.suffix.lower() == ".json":
        try:
            fields = flatten_fields(json.loads(Path(real).read_text(encoding="utf-8")))
        except (ValueError, UnicodeDecodeError):
            fields = None
    return {"sha256": _file_sha256(real), "hdf5": hdf5_digest(Path(real)) if head == b"\x89HDF\r\n\x1a\n" else None,
            "fields": fields}


def check_scope(write_log: Sequence[Mapping[str, Any]], output_roots: Sequence[Path],
                snapshot_roots: Sequence[Path]) -> None:
    """§G (c) fail-closed：審計記錄任一路徑（含 rename／replace 目的地）或任一輸出根不在 `snapshot_roots` 之下 ⇒
    FreezeError（訊息列出該路徑之解析後絕對路徑）。不得把範圍外之已記路徑補入快照範圍而視為成功收集。"""
    bad = sorted({os.path.realpath(p) for p in [e["path"] for e in write_log if e.get("path")]
                  + [str(r) for r in output_roots]
                  if not any(_under(str(p), root) for root in snapshot_roots)})
    if bad:
        raise FreezeError("寫出落在快照範圍外（§G (c) fail-closed）：" + "、".join(bad))


def collect_written_files(write_log: Sequence[Mapping[str, Any]], before: Mapping[str, str], after: Mapping[str, str],
                          *, repo_root: Path, snapshot_roots: Sequence[Path],
                          output_roots: Sequence[Path],
                          prefixes: Optional[Mapping[str, Path]] = None) -> Dict[str, Any]:
    """先 `check_scope`；回 {"files": {path_key: describe_file(...)}（差集之新增與變更檔）, "transient": [path_key...]
    （審計記錄有而差集無變化者，記入不比）, "removed": [path_key...]（執行前存在、執行後消失者）}。"""
    check_scope(write_log, output_roots, snapshot_roots)
    diff = snapshot_diff(before, after)
    written = set(diff["added"]) | set(diff["changed"])
    files = {k: describe_file(_key_path(k, repo_root, prefixes)) for k in sorted(written)}
    logged = {path_key(Path(e["path"]), repo_root, prefixes) for e in write_log if e.get("path")}
    return {"files": files, "transient": sorted(logged - written), "removed": diff["removed"]}


def _criteria() -> Dict[str, Any]:
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from tests.feature_engineering import numview_helpers as nh

    return json.loads(nh.current_criteria_path().read_text(encoding="utf-8"))


def run_watched(cmd: Sequence[str], *, log_path: Path, env: Mapping[str, str], cwd: Path) -> Dict[str, Any]:
    """以共用監看（`handoffs/run_receipts/numview_probes/_watchdog.py` 之 run_watched，判準取 NUMVIEW 判準檔
    `cell_rules.watchdog`；不設時間上限）啟動子行程；回 {"rc", "status", "log_path"}；卡死 ⇒ FreezeError 附診斷路徑。"""
    wd = _load("icperf_numview_watchdog", PROBES_DIR / "_watchdog.py")
    res = wd.run_watched(list(cmd), log_path=Path(log_path), config=wd.load_config(_criteria()), cwd=str(cwd), env=env)
    if res.status == wd.STALLED:
        raise FreezeError(f"子行程卡住終止（{res.reason}；原因 {res.cause}）：見 {log_path} 與其 .stacks 診斷")
    return {"rc": res.returncode, "status": res.status, "log_path": str(log_path)}


def capture_run(cmd: Sequence[str], *, repo_root: Path, iso_root: Path, output_roots: Sequence[Path],
                work_dir: Path, extra_roots: Optional[Mapping[str, Path]] = None,
                env_base: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    """一次請求之寫出捕獲：快照（repo_root＝本次執行之工作目錄、iso_root、`extra_roots` 如 {"<repo>": repo 根}）→
    `run_watched`（`capture_env`，cwd＝repo_root）→ 快照 → `collect_written_files`。回 {"rc", "files", "transient",
    "removed", "write_log"}；path_key 依 `path_key`（iso_root 之下前綴 `<iso>`）。審計記錄與 sitecustomize 置於
    `work_dir`（不在快照範圍內；落在其下之寫入屬捕獲機制本身〔回應 pickle、監看堆疊檔〕，不入記錄）。範圍外路徑（含經
    os.replace／os.rename 落到範圍外之目的地）或輸出根 ⇒ FreezeError；輸出根於執行前即先檢查。"""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    log_path = work_dir / "write_audit.jsonl"
    log_path.unlink(missing_ok=True)
    env = capture_env(os.environ if env_base is None else env_base, log_path=log_path, iso_root=Path(iso_root),
                      site_dir=work_dir / "site")
    prefixes = {"<iso>": Path(iso_root), **dict(extra_roots or {})}
    roots = [Path(repo_root), Path(iso_root)] + [Path(r) for r in (extra_roots or {}).values()]
    check_scope([], output_roots, roots)
    before = snapshot_files(roots, repo_root=repo_root, prefixes=prefixes)
    res = run_watched(cmd, log_path=work_dir / "run.log", env=env, cwd=Path(repo_root))
    after = snapshot_files(roots, repo_root=repo_root, prefixes=prefixes)
    log = [e for e in read_write_log(log_path) if not (e.get("path") and _under(e["path"], work_dir))]
    collected = collect_written_files(log, before, after, repo_root=repo_root, snapshot_roots=roots,
                                      output_roots=output_roots, prefixes=prefixes)
    return {"rc": res["rc"], **collected, "write_log": log}


# ── 比對（改後對凍結；Phase 1–5 收尾共用） ───────────────────────────────────────────────────────────────


def compared_paths(frozen_files: Mapping[str, Any], current_files: Mapping[str, Any]) -> Set[str]:
    """比對之檔集合＝兩側 path_key 之聯集（只在一側者即為多一檔／少一檔）。`compare_capture` 經本模組層函式取之。"""
    return set(frozen_files) | set(current_files)


def _parse_volatile(volatile: Sequence[str]) -> Tuple[Set[str], Dict[str, Set[str]]]:
    resp: Set[str] = set()
    files: Dict[str, Set[str]] = {}
    for v in volatile:
        if v.startswith("response:"):
            resp.add(v[len("response:"):])
        elif v.startswith("file:") and "#" in v:
            key, field = v[len("file:"):].split("#", 1)
            files.setdefault(key, set()).add(field)
        else:
            raise FreezeError(f"volatile 項格式不合（須 response:<欄位> 或 file:<path_key>#<欄位>）：{v}")
    return resp, files


def _compare_maps(a: Mapping[str, Any], b: Mapping[str, Any], label: str, skip: Set[str] = frozenset()) -> List[str]:
    out = []
    for k in sorted(set(a) | set(b)):
        if k in skip:
            continue
        if k not in a or k not in b:
            out.append(f"{label}{k}：只在{'凍結' if k in a else '改後'}側")
        elif a[k] != b[k]:
            out.append(f"{label}{k}：不等")
    return out


def _compare_hdf5(key: str, a: Mapping[str, Any], b: Mapping[str, Any]) -> List[str]:
    out = []
    for obj in sorted(set(a) | set(b)):
        if obj not in a or obj not in b:
            out.append(f"file:{key} HDF5 物件 {obj}：只在{'凍結' if obj in a else '改後'}側")
            continue
        for fld in ("kind", "dtype", "shape", "sha256"):
            if a[obj].get(fld) != b[obj].get(fld):
                out.append(f"file:{key} HDF5 物件 {obj} 之 {fld}：不等")
        out += [p.replace("attr:", f"file:{key} HDF5 物件 {obj} 屬性 ", 1)
                for p in _compare_maps(a[obj].get("attrs") or {}, b[obj].get("attrs") or {}, "attr:")]
    return out


def compare_capture(frozen: Mapping[str, Any], current: Mapping[str, Any], *,
                    volatile: Sequence[str] = ()) -> List[str]:
    """比對一項之 "response" 與 "files"；回問題清單（空＝逐位元相同）。檔集合取 `compared_paths`：只在一側者、sha256
    不等者、HDF5 任一物件之 sha256／dtype／shape／屬性不等者皆列（訊息含 path_key 與物件／屬性名）。
    `volatile` 項之格式：`response:<欄位路徑>` 或 `file:<path_key>#<欄位路徑>`；只對所列路徑排除——該檔改以
    "fields" 逐欄位比（排除所列），未列欄位不等仍列為問題。兩側皆有 "removed" 時另比執行中刪除之既有檔。"""
    vol_resp, vol_files = _parse_volatile(volatile)
    problems = _compare_maps(frozen.get("response") or {}, current.get("response") or {}, "response:", vol_resp)
    ff, cf = frozen.get("files") or {}, current.get("files") or {}
    for key in sorted(compared_paths(ff, cf)):
        if key not in ff or key not in cf:
            problems.append(f"file:{key}：只在{'凍結' if key in ff else '改後'}側（{'少' if key in ff else '多'}一檔）")
            continue
        a, b = ff[key], cf[key]
        if key in vol_files:
            if a.get("fields") is None or b.get("fields") is None:
                problems.append(f"file:{key}：列有 volatile 欄位但非可解析 JSON，無從逐欄位比")
                continue
            problems += [p.replace("field:", f"file:{key}#", 1)
                         for p in _compare_maps(a["fields"], b["fields"], "field:", vol_files[key])]
            continue
        if a.get("sha256") != b.get("sha256"):
            problems.append(f"file:{key}：sha256 不等")
        if a.get("hdf5") is not None or b.get("hdf5") is not None:
            problems += _compare_hdf5(key, a.get("hdf5") or {}, b.get("hdf5") or {})
    if "removed" in frozen and "removed" in current and sorted(frozen["removed"]) != sorted(current["removed"]):
        problems.append(f"removed：執行中刪除之既有檔不同（凍結 {sorted(frozen['removed'])}、改後 {sorted(current['removed'])}）")
    return problems


def _compare_features(item: str, a: Mapping[str, Any], b: Mapping[str, Any]) -> List[str]:
    out = []
    for feat in sorted(set(a) | set(b)):
        if feat not in a or feat not in b:
            out.append(f"{item}/{feat}：只在{'凍結' if feat in a else '改後'}側")
            continue
        out += [p.replace("fld:", f"{item}/{feat}/", 1) for p in _compare_maps(a[feat], b[feat], "fld:")]
    return out


def compare_golden(frozen: Mapping[str, Any], current: Mapping[str, Any]) -> List[str]:
    """§G 全部凍結項之逐位元比對（依 `frozen["volatile"]` 排除；其項格式為 `<項>:response:<欄位>` 或
    `<項>:file:<path_key>#<欄位>`）；任一不等即列出項、特徵與欄位。"""
    problems = []
    vol: Dict[str, List[str]] = {}
    for v in frozen.get("volatile") or []:
        item, rest = v.split(":", 1)
        vol.setdefault(item, []).append(rest)
    fi, ci = frozen.get("items") or {}, current.get("items") or {}
    for item in G_ITEMS:
        if item not in fi or item not in ci:
            problems.append(f"{item}：只在{'凍結' if item in fi else '改後'}側")
            continue
        a, b = fi[item], ci[item]
        if item in OUTPUT_ITEMS:
            problems += [f"{item}/{p}" for p in compare_capture(a, b, volatile=vol.get(item, []))]
        if "features" in a or "features" in b:
            problems += _compare_features(item, a.get("features") or {}, b.get("features") or {})
        for fld in ("selected", "stage_cols"):
            if (fld in a or fld in b) and a.get(fld) != b.get(fld):
                problems.append(f"{item}/{fld}：不等")
        if "pit_labels" in a or "pit_labels" in b:
            problems += [p.replace("lbl:", f"{item}/pit_labels/", 1)
                         for p in _compare_maps(a.get("pit_labels") or {}, b.get("pit_labels") or {}, "lbl:")]
    return problems


# ── Task 0.1 凍結 ───────────────────────────────────────────────────────────────────────────────────────


def default_request(item: str, cell: str = CELL) -> Dict[str, Any]:
    """各路徑之預設請求設定（SPEC §G「各項請求設定」）：第 (1)(3) 項＝前端 IC 頁初始狀態實際送出之 payload
    `IC_PAGE_DEFAULT_PAYLOAD`（衰減照頁面預設開啟，不沿用 FFPROD 量測之衰減關），經服務 `_build_config_override` 得 override、
    以 `scripts/ffprod_measure.py` 之 `ic_in_process` 同法於行程內呼叫；第 (3) 項另取 `DeepAnalysisRequest()` 預設之模組與
    top_n、同一 analyzer 實例；第 (4) 項＝第 (1) 項之請求加 `event_query="close > open"`（K 線條件式事件 legacy
    `event_query` 一格；事件匯入批分支不凍結）；第 (5) 項＝NUMVIEW 判準檔 A 格定義之 `FeatureFactory.run_ic_first`
    （特徵根置於本次執行之 cwd 根內）。"""
    raise NotImplementedError(_STUB)


def resolve_output_roots(item: str, request: Mapping[str, Any], repo_root: Path = REPO) -> List[Path]:
    """自請求設定與產品寫死之相對路徑解析該路徑之全部輸出根（如 `data_cache/features/`、`data_cache/reports/`）；
    `repo_root`＝本次執行之 cwd 根（相對寫入根皆落於其中，SPEC §G (b)）。"""
    raise NotImplementedError(_STUB)


def small_request(item: str, request: Mapping[str, Any], n_features: int) -> Dict[str, Any]:
    """同一請求（凍結檔所記之 `request`）限縮為前 n_features 個真實特徵（排序後之特徵名；IC 頁為 `feature_filter`，
    其餘路徑用其對應之選欄設定），其餘設定不變；供 boundary_01／02 之獨立 oracle 以小規模真實請求對照。"""
    raise NotImplementedError(_STUB)


def feature_tables(item: str) -> Dict[str, str]:
    """該項回應中逐特徵來源：{<JSON pointer>: <形狀>}，"features" 之來源（SPEC §G baseline 內容；IC 報告為 dict，
    `ic_filter_orchestrator.py:1255`）。形狀：`"rows"`＝list[dict]、以 `feature_name` 為鍵（`summary_table`，`:4942`）；
    `"by_key"`＝以特徵名為鍵之 dict（`quantile_returns`、`coverage_analysis`、`turnover_analysis`）；`"frame"`＝index 為特徵名
    之 DataFrame（通用形狀，本票各項無）。第 (1)、(4) 項 ⇒ {"/summary_table": "rows", "/quantile_returns": "by_key",
    "/coverage_analysis": "by_key", "/turnover_analysis": "by_key"}；第 (3)、(5) 項 ⇒ {}（深度分析之逐模組逐欄位由回應全部
    欄位涵蓋，SPEC §G）。"""
    raise NotImplementedError(_STUB)


def selected_pointer(item: str) -> Optional[str]:
    """該項回應中選欄通過集合（特徵名清單）之 JSON pointer；無此概念、或通過集合不在回應之項 ⇒ None。§G 第 (1)、(4) 項之
    通過集合＝第 6 段後之倖存者（`analyzer.get_filtered_features().columns`，`ic_filter_orchestrator.py:3390`；報告頂層無
    名單），不在回應 ⇒ None；其 "selected" 取自該次執行寫出之 `data_cache/reports/ic_survivors_<case_id>.json`（case_id 預設
    `ic_gatekeeper`，`ic_filter_orchestrator.py:5837`）之 `feature_names`（`momentum/Analysis/survivor_contract.py`）。"""
    raise NotImplementedError(_STUB)


def load_cell(cell: str = CELL) -> Tuple[Any, Any]:
    """讀真實資料格之 IC 讀入結果（第 0 段後）：回 (features: DataFrame, label: Series)；不存在 ⇒ FreezeError。"""
    raise NotImplementedError(_STUB)


def value_digest(values: Any) -> Dict[str, str]:
    """{"sha256", "nan_mask_sha256"}（boundary_02 之獨立 oracle 依此重算，`test_icperf_gate.py::_oracle_digest`）：
    - ndarray（"frame" 形狀之 1 元素欄）⇒ sha256(`values.tobytes()`，原生 dtype 位元組)、遮罩＝sha256(
      `np.isnan(values.astype("float64")).tobytes()`)；
    - 其餘（"rows" 之欄值、"by_key" 之整段子樹）⇒ 正準形 c＝`canon(values)`：dict ⇒ {str(鍵): canon(值)}；list／tuple ⇒
      [canon(元素)]；ndarray ⇒ {"__ndarray__": dtype.str, "shape": [...], "v": canon(tolist())}；numpy 純量 ⇒
      {"__np__": dtype.str, "v": item()}（item 非 JSON 原生型別者取 str）；None／bool／int／float／str 原樣；其餘 ⇒
      {"__repr__": "<模組>.<限定名>", "v": str(值)}；dataclass 與具 model_dump 之物件先轉 dict。sha256＝sha256(
      `json.dumps(c, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=True)` 之 UTF-8)；遮罩＝同法序列化
      「c 之同形樹、葉＝該葉為 float 且為 NaN」之 sha256。float 以 repr 序列化（與 float64 位元組一一對應，NaN 由遮罩記）。"""
    raise NotImplementedError(_STUB)


def pit_label_digests(features: Any, label: Any, *, num_quantiles: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
    """以現行碼（單調性之輸入定義：特徵與標籤同時非 NaN 壓縮、逐欄選 q、q=3 退回）逐欄求 PIT 標籤序列；回
    {<特徵>: {"q", "q_insufficient", "skipped_all_nan", "label_sha256"|None, "label_nan_count"}}；全 NaN 欄照現行跳過
    （skipped_all_nan＝True、label_sha256＝None）。"""
    raise NotImplementedError(_STUB)


def stage5_subset_digests(n_cols: int, *, seed: int = SEED) -> Dict[str, Any]:
    """改前基準全特徵 run 交接 h5 之 n_cols 欄巢狀隨機子集（seed 同探針 `icperf_probes/prep.py`）以產品
    `create_ic_analyzer(...).analyze()` 跑第 5 段；回 {"stage_cols", "features": {<特徵>: {<欄位>: value_digest}},
    "pit_labels": {...}}（"features" 之來源、欄位命名與摘要粒度同第 (1) 項，見模組說明）；交接 h5 不存在 ⇒ FreezeError
    （不以其他 run 代替）。"""
    raise NotImplementedError(_STUB)


def freeze_item(item: str, *, request: Mapping[str, Any], repo_root: Path, work_root: Path) -> Dict[str, Any]:
    """凍結 §G 單一項：第 (1)、(3)、(4)、(5) 項經 `capture_run` 取回應全部欄位與寫出檔；第 (2) 項經
    `stage5_subset_digests(SUBSET_COLS)`。三根（SPEC §G (b)）：cwd 根＝新建之 `work_root/<item>/cwd`（唯讀輸入
    `data_cache/feature_klines`、`data_cache/feature_klines_longhist`、`config/` 自 `repo_root` 以 symlink 引入，同
    `scripts/ffprod_measure.py` `ic_watched`；快照不跟隨其下之目錄 symlink）、隔離目錄＝`work_root/<item>/iso`
    （TMPDIR／HOME，前綴 `<iso>`）、`repo_root`（前綴 `<repo>`，抓逃逸寫出）；`capture_run(..., repo_root=<cwd 根>,
    iso_root=<隔離目錄>, extra_roots={"<repo>": repo_root})`。子行程把回傳物件原樣以 pickle 寫
    `work_root/<item>/response.pkl`（審計記錄與 sitecustomize 亦置於 `work_root/<item>`，pickle 與記錄不在快照範圍）；
    回之記錄另含 "request"、"output_roots"（cwd 根相對 POSIX）、"roots"＝{"cwd": <cwd 根>, "iso": <隔離目錄>}（解析後
    絕對路徑；boundary_01 之獨立 oracle 以同一組根走訪並比對）、"features"／"selected"（第 (1)、(4) 項，見模組說明）。"""
    raise NotImplementedError(_STUB)


def freeze(out_path: Path = GOLDEN_PATH, *, repo_root: Path = REPO, work_root: Optional[Path] = None) -> Dict[str, Any]:
    """依序凍結 `G_ITEMS` 並寫 `out_path`；任一項 FreezeError ⇒ 不寫檔。"""
    raise NotImplementedError(_STUB)


# ── Task 0.2 路徑清冊與規模盤點 ─────────────────────────────────────────────────────────────────────────


def load_single_receipt(pattern: str, *, repo_root: Path = REPO) -> Dict[str, Any]:
    """`repo_root.glob(pattern)` 恰一份 ⇒ 回其 JSON；零份或多份 ⇒ FreezeError。"""
    paths = sorted(Path(repo_root).glob(pattern))
    if len(paths) != 1:
        raise FreezeError(f"{pattern} 須恰一份，實得 {[str(p) for p in paths]}")
    return json.loads(paths[0].read_text(encoding="utf-8"))


def build_path_inventory(repo_root: Path = REPO) -> Dict[str, Any]:
    """讀碼列 Task 0.2 範圍內每一計算入口：{"entries": [{"id": "<模組>:<限定名>", "stage", "input_axes"
    （⊆ cols／rows／passed_cols）, "ic_page", "ic_first", "loop"（per_bar／per_column／per_group／none）, "measure",
    "no_measure_reason", "evidence": "<檔>:<行>", "coverage_path_id": <與入口一一對應之字串>, "unit_axis": {"axes":
    [<scale_vector 鍵>...], "function": <單位成本之複雜度函數，如 "input_cols*rows">}, "scale_vector": [<該入口所用之
    rows／input_cols／stage_cols／survivors／survivor_pairs>...]}]}（SPEC Task 0.2 路徑清冊；與 Task 5.4 總時間門檻共用 schema；
    `unit_axis.axes` ⊆ `scale_vector`）。"""
    raise NotImplementedError(_STUB)


def measured_ids(scale_receipt: Mapping[str, Any]) -> Set[str]:
    """量測收據之入口 id 集合（`scale_receipt["entries"]` 之鍵）。"""
    return set(scale_receipt.get("entries") or {})


def uncovered_entries(inventory: Mapping[str, Any], scale_receipt: Mapping[str, Any]) -> List[str]:
    """清冊中標需量測（measure＝True）之 id − `measured_ids`；排序回傳（空＝無漏量）。"""
    return sorted({e["id"] for e in inventory.get("entries") or [] if e.get("measure")} - measured_ids(scale_receipt))


def evaluate_criteria(entry: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """判準①–⑤（SPEC Task 0.2 固定規則；①之門檻引 `scripts/scale_probe.py` 之 SUPERLINEAR_EXPONENT／MIN_R2）；
    回 {"1".."5": {"result": bool, "basis": str}}。"""
    raise NotImplementedError(_STUB)


def measure_inventory(inventory: Mapping[str, Any], *, scales: Sequence[int] = SCALE_POINTS,
                      out_path: Path) -> Dict[str, Any]:
    """以 `scripts/scale_probe.py` 量清冊每一需量測入口於 `scales` 之耗時與峰值 RSS（行程樹），並以 `sample <pid>` 取峰值
    Physical footprint（§B 門檻；同 `scripts/measure_ic_footprint.sh` 之工具，只沿用工具、不沿用其取樣停止與超標終止：受測
    行程結束前持續取樣、不因超標中止，SPEC Task 0.2），寫 `out_path`：
    {"head": <量測時之 40 位提交雜湊>, "meter": {"tool", "rss_scope", "sample_interval_seconds", "footprint": {"tool":
    "sample:Physical footprint", "sampling": "until_target_exit", "terminate_target_on_exceed": False}},
    "chunk_cap": {"bytes", "basis"}, "budget_seconds",
    "entries": {<清冊 id>: {"coverage_path_id", "unit_axis"（皆＝清冊該入口之值）, "probe": {"cmd", "data", "config"},
    "row_probe": {"cmd", "data", "config"}|None,
    "points": [{"input_cols", "stage_cols", "seconds", "peak_rss_bytes", "peak_footprint_bytes", "scale_vector":
    {<清冊 scale_vector 之每一鍵>: <int>}, "scale_probe_receipt"}],
    "row_points": [{"rows", "seconds", "peak_rss_bytes", "peak_footprint_bytes", "scale_vector", "scale_probe_receipt"}],
    "fit": {"exponent", "r2"},
    "extrapolation_unreliable", "projected_seconds", "reduction", "two_point_exception": {"projected_2000_seconds"}|None,
    "complexity_analysis", "lower_bound_seconds_per_unit", "lower_bound_analysis", "criteria",
    "opportunities": {"time"|"memory"|"precision"|"file_size": {"status": "none"|"planned"|"needs_user"|"done",
    "evidence", "before", "after", "downstream", "user_ruling"}}}}}。
    points 恰 3 點（500／1000／2000）；唯一例外＝帶 two_point_exception 者恰 2 點（500／1000）且不含 2000 欄點。每點之
    scale_vector 鍵集＝清冊該入口之 scale_vector（缺軸即拒收），其 input_cols／stage_cols／rows 與點之同名欄相等；下限單位
    成本依同一 unit_axis 擬合。opportunities 四鍵齊備：`none` 須 evidence（無機會之理由）；`planned` 須 evidence；
    `needs_user`（改值者）須 before、after、downstream；`done` 須 before、after（同工具量測）。
    入口 id 只取清冊 id；每一點之 seconds／peak_rss_bytes 逐欄抄自其 `scale_probe_receipt`（scale_probe 寫出之收據，
    該收據 points 中 scale＝input_cols〔列長點為 rows〕之點）；`probe`／`row_probe` 為交給 scale_probe 之量測命令
    （cmd 含清冊 id）與其 --data／--config，該收據之 identity.match 須與之逐欄相符（量測前先提交量測碼，`head` 即該提交）；同一收據之三點者 fit／extrapolation_unreliable 等於該收據。
    500／1000 兩點推估 2000 欄逾 10 分鐘之入口不量 2000 欄點，記 two_point_exception 與碼層複雜度分析。"""
    raise NotImplementedError(_STUB)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI：freeze／repro／inventory／measure（見模組說明）。"""
    raise NotImplementedError(_STUB)


if __name__ == "__main__":
    raise SystemExit(main())

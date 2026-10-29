"""ICPERF Phase 0（docs/ICPERF_SPEC.md §G、Task 0.1／0.2）：以現行碼凍結改前輸出、寫出檔捕獲與比對、規模盤點之路徑清冊。

施工狀態：Task 0.1（凍結、可重現性重跑）入口已實作；Task 0.2 之 `build_path_inventory`／`evaluate_criteria`／
`measure_inventory` 仍為空殼（`raise NotImplementedError`）。具名驗收見 `tests/momentum/Analysis/test_icperf_gate.py`。

子行程（重型計算一律在子行程、經 `run_watched` 啟動；子命令 `_child <spec.json>`，不列於 --help）：
- 第 (1)(3)(4) 項：`ic_page`——同 `scripts/ffprod_measure.py` 之 `ic_in_process`（服務 `_build_config_override`、
  `_materialize_features_for_ic`、`create_ic_analyzer(...).analyze`）；第 (3) 項於同一 analyzer 實例續跑深度分析。
- 第 (5) 項：`ic_first`——同 `scripts/numview_freeze_baseline.py:316-323`（`_isolated` 導向本次 cwd 根）。
- 第 (2) 項：`stage5`——交接 h5 之巢狀子集（同 `icperf_probes/prep.py`）後 `analyze`。
- 第 (1) 項之 PIT 標籤：`pit_labels`——`load_cell` 後 `pit_label_digests`。

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

註記（ICPERF 施工清單審查 r10 群集 A）：本檔列 `scripts/heavy_commands.json` 之 `self_watched`，heavy_run_guard
以 AST 驗原始碼確有 `run_watched(...)` 呼叫；`run_watched` 呼叫共用監看（`_watchdog.run_watched`）。

volatile（每次必異欄位）：凍結檔之 "volatile" 留空，由 FACT-RECEIPT 判定後寫入（SPEC §G）；凍結時另列
"volatile_candidates"（欄位名形似時間戳／耗時／執行 id、或值含本次執行根之絕對路徑者），只供判定、不自動排除。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
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

#: SPEC §G FACT-RECEIPT：第 (1)(3)(4) 項之 A 格資料根（NUMVIEW 凍結之 run；`{cell}` 代入格 id，repo 相對）
CELL_FEATURES_ROOT = "data_cache/numview_freeze_runs/{cell}__default/features"
#: SPEC §G (2)：改前基準全特徵 run（C 格）之 IC 交接 h5（`handoffs/run_receipts/icperf_probes/prep.py` 之 SRC_DIR／HASH；
#: 225,002,383 bytes，`ls -la` 實查）；不存在或大小不符 ⇒ FreezeError（不以他 run 代替）
C_HANDOFF_H5 = Path("/var/folders/_c/3xdf41hd3tvgxpx63mrml2c00000gn/T/ffprod-measure/C_BTCUSDT_1h/"
                    "ic__baseline__default/data_cache/reports/ic_ingest_cache/"
                    "BTCUSDT_1h_fe927783c302dc6232adf0a0087846e8.h5")
C_HANDOFF_BYTES = 225002383
#: SPEC §G (4)：K 線條件式事件（legacy `event_query` 一格，只用 K 線欄位）
EVENT_QUERY = "close > open"
#: SPEC §G (b)：隔離 cwd 根以 symlink 自 repo 引入之唯讀輸入（同 `scripts/ffprod_measure.py` 之 `ic_watched`）
READONLY_INPUTS = ("data_cache/feature_klines", "data_cache/feature_klines_longhist", "config")
#: 產品寫死之 cwd 相對寫入根。IC 頁：filtered HDF5（`momentum/Analysis/ic_filter_orchestrator.py:5850`）、報告／filter-log
#: ／倖存者（`:5676`、`:5682`、`:5822`）與交接快取（`api/services/ic_analysis_service.py:3348`）。IC-first：
#: `numview_freeze_baseline._isolated` 導向 cwd 之特徵根（含 registry）、CGSA 工作目錄、d* 快取、tempdir
#: （`handoffs/run_receipts/numview_probes/estimate.py:_isolate`）
IC_PAGE_OUTPUT_ROOTS = ("data_cache/features", "data_cache/reports")
IC_FIRST_OUTPUT_ROOTS = ("features", "cgsa_work", "dstar_cache", "sys_tmp")
#: 第 (1)(3)(4) 項（IC 頁路徑）
IC_PAGE_ITEMS = ("ic_report", "deep_analysis", "event_report")
#: 子行程入口之子命令名（不列於 --help）
CHILD_CMD = "_child"
#: PIT 標籤之請求 q：第 5 段 `MonotonicityTester.compute_all(features_for_stats, label_for_stats)` 不帶 q
#: （`ic_filter_orchestrator.py:4495`）⇒ 取 `compute_all` 之預設 num_quantiles=5（`monotonicity_tester.py:171`）
DEFAULT_NUM_QUANTILES = 5
#: volatile 候選之欄位名提示（只供 FACT-RECEIPT 判定，不自動排除）
VOLATILE_NAME_HINTS = ("generated_at", "created_at", "updated_at", "started_at", "finished_at", "timestamp",
                       "generation_time", "elapsed", "duration", "seconds", "timing", "run_id", "task_id")
#: 倖存者檔之 cwd 相對鍵（`momentum/Analysis/ic_reporter.py` `ic_survivors_{case_id}.json`）
SURVIVORS_KEY_RE = re.compile(r"^data_cache/reports/ic_survivors_[^/]+\.json$")


def _ensure_repo_path() -> None:
    """產品碼（api／momentum）與測試輔助（tests.feature_engineering）之 import 需 repo 根在 sys.path。"""
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))


def _json_copy(obj: Any) -> Any:
    """可 JSON 化物件之深複本（請求設定一律須可寫入凍結檔）。"""
    return json.loads(json.dumps(obj, ensure_ascii=False))


def _cell_descriptor(cell: str) -> Dict[str, Any]:
    """NUMVIEW 判準檔之格描述子 {id, kind, symbol, timeframes}（`cell_rules.cell_list.cells`）；不存在 ⇒ FreezeError。"""
    for c in _criteria()["cell_rules"]["cell_list"]["cells"]:
        if str(c["id"]) == cell:
            return {"id": str(c["id"]), "kind": str(c["kind"]), "symbol": str(c["symbol"]),
                    "timeframes": [str(t) for t in c["timeframes"]]}
    raise FreezeError(f"NUMVIEW 判準檔無格 {cell}")


def _cell_run(cell: str, repo_root: Path = REPO) -> Dict[str, str]:
    """格之凍結 run（SPEC §G FACT-RECEIPT）：讀 `CELL_FEATURES_ROOT/registry.json`（須恰一條）回 {symbol, timeframe,
    config_hash, run_dir（repo 相對 POSIX）}；registry 或 feature_manifest.json 不存在 ⇒ FreezeError。"""
    root = Path(repo_root) / CELL_FEATURES_ROOT.format(cell=cell)
    reg = root / "registry.json"
    if not reg.is_file():
        raise FreezeError(f"{cell}：凍結 run 之 registry 不存在：{reg}")
    entries = json.loads(reg.read_text(encoding="utf-8"))
    if not isinstance(entries, list) or len(entries) != 1:
        raise FreezeError(f"{reg}：須恰一條 run，實得 {entries if not isinstance(entries, list) else len(entries)}")
    e = entries[0]
    rel = Path(CELL_FEATURES_ROOT.format(cell=cell)) / str(e["symbol"]) / str(e["timeframe"]) / str(e["config_hash"])
    if not (Path(repo_root) / rel / "feature_manifest.json").is_file():
        raise FreezeError(f"{cell}：run 之 feature_manifest.json 不存在：{Path(repo_root) / rel}")
    return {"symbol": str(e["symbol"]), "timeframe": str(e["timeframe"]), "config_hash": str(e["config_hash"]),
            "run_dir": rel.as_posix()}


def _run_feature_names(request: Mapping[str, Any]) -> List[str]:
    """IC 頁請求所指 run 之真實特徵名：manifest `artifacts.raw.groups[*].columns`（IC 頁讀 raw artifact：
    `FeatureLibrary.load_with_identity` 回 `resolve_run_identity(manifest, "raw")`，`feature_library.py:135`）。"""
    manifest = json.loads((REPO / request["run_dir"] / "feature_manifest.json").read_text(encoding="utf-8"))
    groups = ((manifest.get("artifacts") or {}).get("raw") or {}).get("groups") or {}
    names = [str(c) for g in groups.values() for c in (g.get("columns") or [])]
    if not names:
        raise FreezeError(f"{request['run_dir']}：manifest 無 raw 欄名")
    return names


def default_request(item: str, cell: str = CELL) -> Dict[str, Any]:
    """各路徑之預設請求設定（SPEC §G「各項請求設定」）：第 (1)(3) 項＝前端 IC 頁初始狀態實際送出之 payload
    `IC_PAGE_DEFAULT_PAYLOAD`（衰減照頁面預設開啟，不沿用 FFPROD 量測之衰減關），經服務 `_build_config_override` 得 override、
    以 `scripts/ffprod_measure.py` 之 `ic_in_process` 同法於行程內呼叫；第 (3) 項另取 `DeepAnalysisRequest()` 預設之模組與
    top_n、同一 analyzer 實例；第 (4) 項＝第 (1) 項之請求加 `event_query="close > open"`（K 線條件式事件 legacy
    `event_query` 一格；事件匯入批分支不凍結）；第 (5) 項＝NUMVIEW 判準檔 A 格定義之 `FeatureFactory.run_ic_first`
    （特徵根置於本次執行之 cwd 根內）。

    回傳可 JSON 化之請求記錄：IC 頁 {"kind": "ic_page", "item", "cell", "symbol", "timeframe", "config_hash", "run_dir"
    （repo 相對）, "config_override", "feature_tiers", "event_query", "feature_filter", "deep"（第 (3) 項＝
    `DeepAnalysisRequest().model_dump()`，餘 None）}；IC-first {"kind": "ic_first", "item", "cell"（判準檔格描述子）,
    "generation"（判準檔 `cell_definitions.<格類>.generation`）}；第 (2) 項 {"kind": "stage5", "item", "source_h5",
    "seed", "n_cols", "ic_request"（＝第 (1) 項之請求）}。"""
    if item in IC_PAGE_ITEMS:
        payload = _json_copy(IC_PAGE_DEFAULT_PAYLOAD)
        req: Dict[str, Any] = {"kind": "ic_page", "item": item, "cell": cell, **_cell_run(cell),
                               "config_override": payload["config_override"], "feature_tiers": payload["feature_tiers"],
                               "event_query": EVENT_QUERY if item == "event_report" else None,
                               "feature_filter": None, "deep": None}
        if item == "deep_analysis":
            _ensure_repo_path()
            from api.models.ic_models import DeepAnalysisRequest

            req["deep"] = _json_copy(DeepAnalysisRequest().model_dump())
        return req
    if item == "icfirst_post_ic":
        desc = _cell_descriptor(cell)
        generation = _criteria()["cell_definitions"][desc["kind"]]["generation"]
        if generation.get("entry") != "run_ic_first":
            raise FreezeError(f"{cell}：判準檔格類 {desc['kind']} 之生成入口非 run_ic_first（{generation.get('entry')}）")
        return {"kind": "ic_first", "item": item, "cell": desc, "generation": _json_copy(generation)}
    if item == "stage5_subset":
        return {"kind": "stage5", "item": item, "source_h5": str(C_HANDOFF_H5), "seed": SEED, "n_cols": SUBSET_COLS,
                "ic_request": default_request("ic_report", cell)}
    raise FreezeError(f"未知凍結項：{item}")


def resolve_output_roots(item: str, request: Mapping[str, Any], repo_root: Path = REPO) -> List[Path]:
    """自請求設定與產品寫死之相對路徑解析該路徑之全部輸出根（如 `data_cache/features/`、`data_cache/reports/`）；
    `repo_root`＝本次執行之 cwd 根（相對寫入根皆落於其中，SPEC §G (b)）。

    IC 頁（第 (1)(3)(4) 項）＝`IC_PAGE_OUTPUT_ROOTS`；IC-first（第 (5) 項）＝`IC_FIRST_OUTPUT_ROOTS`；回傳 `repo_root`
    下之路徑（不解析 symlink）。第 (2) 項不經寫出捕獲 ⇒ FreezeError。"""
    kind = request.get("kind")
    if kind == "ic_page":
        rels: Sequence[str] = IC_PAGE_OUTPUT_ROOTS
    elif kind == "ic_first":
        rels = IC_FIRST_OUTPUT_ROOTS
    else:
        raise FreezeError(f"{item}：請求種類 {kind!r} 無輸出根（第 (2) 項不經寫出捕獲）")
    return [Path(repo_root) / r for r in rels]


def small_request(item: str, request: Mapping[str, Any], n_features: int) -> Dict[str, Any]:
    """同一請求（凍結檔所記之 `request`）限縮為前 n_features 個真實特徵（排序後之特徵名；IC 頁為 `feature_filter`，
    其餘路徑用其對應之選欄設定），其餘設定不變；供 boundary_01／02 之獨立 oracle 以小規模真實請求對照。

    IC 頁：`feature_filter.include_features`＝該 run raw 欄名排序後之前 n_features 個（`_run_feature_names`）。
    IC-first：`FeatureFactory.run_ic_first` 無選欄設定（參數見 `feature_factory.py:2809-2831`），回同一請求不變
    （A 格整格生成；回報 CONTRACT_MISMATCH）。"""
    new = _json_copy(request)
    if new.get("kind") == "ic_page":
        names = sorted(_run_feature_names(new))[:int(n_features)]
        if len(names) < int(n_features):
            raise FreezeError(f"{item}：run 之特徵數 {len(names)} < 請求之 {n_features}")
        new["feature_filter"] = {"include_features": names}
        return new
    if new.get("kind") == "ic_first":
        return new
    raise FreezeError(f"{item}：請求種類 {new.get('kind')!r} 無小規模請求")


def feature_tables(item: str) -> Dict[str, str]:
    """該項回應中逐特徵來源：{<JSON pointer>: <形狀>}，"features" 之來源（SPEC §G baseline 內容；IC 報告為 dict，
    `ic_filter_orchestrator.py:1255`）。形狀：`"rows"`＝list[dict]、以 `feature_name` 為鍵（`summary_table`，`:4942`）；
    `"by_key"`＝以特徵名為鍵之 dict（`quantile_returns`、`coverage_analysis`、`turnover_analysis`）；`"frame"`＝index 為特徵名
    之 DataFrame（通用形狀，本票各項無）。第 (1)、(4) 項 ⇒ {"/summary_table": "rows", "/quantile_returns": "by_key",
    "/coverage_analysis": "by_key", "/turnover_analysis": "by_key"}；第 (3)、(5) 項 ⇒ {}（深度分析之逐模組逐欄位由回應全部
    欄位涵蓋，SPEC §G）。第 (2) 項（`stage5_subset`）同第 (1) 項（模組說明：來源、命名與摘要粒度同第 (1) 項）。"""
    if item in ("ic_report", "event_report", "stage5_subset"):
        return {"/summary_table": "rows", "/quantile_returns": "by_key", "/coverage_analysis": "by_key",
                "/turnover_analysis": "by_key"}
    if item in ("deep_analysis", "icfirst_post_ic"):
        return {}
    raise FreezeError(f"未知凍結項：{item}")


def selected_pointer(item: str) -> Optional[str]:
    """該項回應中選欄通過集合（特徵名清單）之 JSON pointer；無此概念、或通過集合不在回應之項 ⇒ None。§G 第 (1)、(4) 項之
    通過集合＝第 6 段後之倖存者（`analyzer.get_filtered_features().columns`，`ic_filter_orchestrator.py:3390`；報告頂層無
    名單），不在回應 ⇒ None；其 "selected" 取自該次執行寫出之 `data_cache/reports/ic_survivors_<case_id>.json`（case_id 預設
    `ic_gatekeeper`，`ic_filter_orchestrator.py:5837`）之 `feature_names`（`momentum/Analysis/survivor_contract.py`）。"""
    if item in G_ITEMS:
        return None
    raise FreezeError(f"未知凍結項：{item}")


def _ic_analyze_request(request: Mapping[str, Any]) -> Any:
    """IC 頁請求記錄 ⇒ `ICAnalyzeRequest`（前端 IC 頁初始 payload；`feature_filter`／`event_query` 依記錄）。"""
    _ensure_repo_path()
    from api.models.ic_models import FeatureFilterConfig, FeatureTierRequest, ICAnalyzeRequest

    ff = request.get("feature_filter")
    tiers = request.get("feature_tiers")
    return ICAnalyzeRequest(symbol=request["symbol"], timeframe=request["timeframe"], config_hash=request["config_hash"],
                            config_override=_json_copy(request["config_override"]),
                            event_query=request.get("event_query"),
                            feature_filter=FeatureFilterConfig(**ff) if ff else None,
                            feature_tiers=FeatureTierRequest(**tiers) if tiers else None)


def _override_for(request: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """IC 頁請求之 config_override：服務 `ICAnalysisService._build_config_override`（不另寫參數）。"""
    _ensure_repo_path()
    from api.services.ic_analysis_service import ICAnalysisService

    svc = ICAnalysisService.__new__(ICAnalysisService)
    return svc._build_config_override(_ic_analyze_request(request))


def _ic_service(request: Mapping[str, Any], registry: Path) -> Any:
    """同 `scripts/ffprod_measure.py` `ic_in_process`：把請求所指 run 登記於 `registry`（暫存，不在快照範圍），回以該
    run 之特徵根組 FeatureLibrary 之服務實例（不經 `__init__`）。"""
    _ensure_repo_path()
    from api.services.ic_analysis_service import ICAnalysisService
    from momentum.FeatureEngineering.feature_library import FeatureLibrary
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from tests.feature_engineering.ffname_helpers import register_canonical_run

    run_dir = REPO / request["run_dir"]
    root = run_dir.parents[2]
    Path(registry).parent.mkdir(parents=True, exist_ok=True)
    register_canonical_run(run_dir / "feature_manifest.json", Path(registry))
    svc = ICAnalysisService.__new__(ICAnalysisService)
    svc._feature_library = FeatureLibrary(FeatureRegistry(Path(registry)), FeatureStorage(str(root)),
                                          feature_reader=FeatureReader(str(root)))
    return svc


def _write_handoff(svc: Any, request: Mapping[str, Any], out_dir: Path) -> Tuple[Path, Path]:
    """服務 `_materialize_features_for_ic` 之同一寫法（`api/services/ic_analysis_service.py:3342-3375`），但寫入 `out_dir`
    （不依 cwd 相對之 `data_cache/reports/ic_ingest_cache`，避免同行程呼叫寫入 repo）；回 (h5, meta)。"""
    from momentum.core.contracts import FF_RUN_IDENTITY_KEY

    sym, tf, ch = request["symbol"], request["timeframe"], request["config_hash"]
    features_df, run_identity = svc._feature_library.load_with_identity(sym, tf, config_hash=ch)
    identity = run_identity.to_dict()
    safe = f"{sym}_{tf}_{ch}".replace("/", "_")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    h5, meta = out_dir / f"{safe}.h5", out_dir / f"{safe}_meta.json"
    svc._write_features_h5(h5, sym, tf, features_df, run_identity=identity)
    payload = svc._build_ic_metadata_from_run(sym, tf, ch, list(features_df.columns))
    payload[FF_RUN_IDENTITY_KEY] = identity
    meta.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return h5, meta


def _stage0_and_label(h5: Path, meta: Path, override: Optional[Mapping[str, Any]]) -> Tuple[Any, Any]:
    """產品 analyzer 之第 0 段讀入（`_stage0_ingestion`）＋標籤（`_stage2_label_generation`；labels_path 空時第 0 段無
    標籤，標籤於第 2 段由 K 線生成）；設定＝`analyze` 之同一解析（`_apply_tier_config(_apply_config_override(...))`）。"""
    from momentum.factories import create_ic_analyzer, create_kline_storage_manager

    override = dict(override) if override else None
    analyzer = create_ic_analyzer(override)
    config = analyzer._apply_tier_config(analyzer._apply_config_override(override))
    kline = create_kline_storage_manager(cache_dir=str(REPO / "data_cache" / "feature_klines"))
    features, labels_df, metadata, _log = analyzer._stage0_ingestion(str(h5), "", str(meta), config=config,
                                                                       kline_reader=kline)
    label, _labels = analyzer._stage2_label_generation(labels_df, metadata, config, kline, features_df=features)
    return features, label


def load_cell(cell: str = CELL) -> Tuple[Any, Any]:
    """讀真實資料格之 IC 讀入結果（第 0 段後）：回 (features: DataFrame, label: Series)；不存在 ⇒ FreezeError。

    請求＝第 (1) 項之 IC 頁預設請求；交接 h5 與 registry 寫入暫存目錄、用畢刪除；features＝第 0 段之輸出，label＝第 2 段
    依同一請求之標籤設定生成之序列（第 0 段於 labels_path 空時不產標籤）。"""
    import shutil
    import tempfile

    request = default_request("ic_report", cell)
    tmp = Path(tempfile.mkdtemp(prefix="icperf-load-cell-"))
    try:
        svc = _ic_service(request, tmp / "registry.json")
        h5, meta = _write_handoff(svc, request, tmp)
        return _stage0_and_label(h5, meta, _override_for(request))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def value_digest(values: Any) -> Dict[str, str]:
    """{"sha256", "nan_mask_sha256"}（boundary_02 之獨立 oracle 依此重算，`test_icperf_gate.py::_oracle_digest`）：
    - ndarray（"frame" 形狀之 1 元素欄）⇒ sha256(`values.tobytes()`，原生 dtype 位元組)、遮罩＝sha256(
      `np.isnan(values.astype("float64")).tobytes()`)；
    - 其餘（"rows" 之欄值、"by_key" 之整段子樹）⇒ 正準形 c＝`canon(values)`：dict ⇒ {str(鍵): canon(值)}；list／tuple ⇒
      [canon(元素)]；ndarray ⇒ {"__ndarray__": dtype.str, "shape": [...], "v": canon(tolist())}；numpy 純量 ⇒
      {"__np__": dtype.str, "v": item()}（item 非 JSON 原生型別者取 str）；None／bool／int／float／str 原樣；其餘 ⇒
      {"__repr__": "<模組>.<限定名>", "v": str(值)}；dataclass 與具 model_dump 之物件先轉 dict。sha256＝sha256(
      `json.dumps(c, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=True)` 之 UTF-8)；遮罩＝同法序列化
      「c 之同形樹、葉＝該葉為 float 且為 NaN」之 sha256。float 以 repr 序列化（與 float64 位元組一一對應，NaN 由遮罩記）。

    本函式以引數型別分派（ndarray ⇒ 前者）；"rows"／"by_key" 之值不論型別一律走正準形，由 `_feature_digests` 直接呼叫
    `_canon_digest`（值本身為 ndarray 時亦然，與 boundary_02 之 oracle 同）。"""
    import numpy as np

    if isinstance(values, np.ndarray):
        return {"sha256": _sha_bytes(values.tobytes()),
                "nan_mask_sha256": _sha_bytes(np.isnan(values.astype("float64")).tobytes())}
    return _canon_digest(values)


def _canon(v: Any) -> Any:
    """`value_digest` 之正準形（規則見其 docstring；判定順序 dict→list／tuple→ndarray→numpy 純量→JSON 原生→其餘）。"""
    import numpy as np

    v = _as_container(v)
    if isinstance(v, dict):
        return {str(k): _canon(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_canon(x) for x in v]
    if isinstance(v, np.ndarray):
        return {"__ndarray__": v.dtype.str, "shape": list(v.shape), "v": _canon(v.tolist())}
    if isinstance(v, np.generic):
        item = v.item()
        return {"__np__": v.dtype.str,
                "v": item if item is None or isinstance(item, (bool, int, float, str)) else str(item)}
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    return {"__repr__": f"{type(v).__module__}.{type(v).__qualname__}", "v": str(v)}


def _nan_tree(c: Any) -> Any:
    """正準形之同形樹，葉＝該葉為 float 且為 NaN。"""
    if isinstance(c, dict):
        return {k: _nan_tree(x) for k, x in c.items()}
    if isinstance(c, list):
        return [_nan_tree(x) for x in c]
    return isinstance(c, float) and c != c


def _canon_digest(v: Any) -> Dict[str, str]:
    """正準形之 {"sha256", "nan_mask_sha256"}（`value_digest` 之非 ndarray 分支）。"""
    c = _canon(v)
    return {"sha256": _sha_bytes(_canonical_json(c)), "nan_mask_sha256": _sha_bytes(_canonical_json(_nan_tree(c)))}


def _monotonicity_config() -> Dict[str, Any]:
    """第 5 段單調性實例之設定：analyzer 建構時以 `config.thresholds.model_dump()` 建 `MonotonicityTester`
    （`ic_filter_orchestrator.py:1223`）；取第 (1) 項 IC 頁預設請求之 analyzer 實例之同一份。"""
    _ensure_repo_path()
    from momentum.factories import create_ic_analyzer

    override = _override_for(default_request("ic_report"))
    return dict(create_ic_analyzer(override)._monotonicity._config)


def pit_label_digests(features: Any, label: Any, *, num_quantiles: Optional[int] = None,
                      progress: bool = False) -> Dict[str, Dict[str, Any]]:
    """以現行碼（單調性之輸入定義：特徵與標籤同時非 NaN 壓縮、逐欄選 q、q=3 退回）逐欄求 PIT 標籤序列；回
    {<特徵>: {"q", "q_insufficient", "skipped_all_nan", "label_sha256"|None, "label_nan_count"}}；全 NaN 欄照現行跳過
    （skipped_all_nan＝True、label_sha256＝None）。

    逐欄：`_prepare_data`（壓縮）→ `_select_num_quantiles(len, 請求 q)` → `_assign_quantiles`（產品碼；其 q=3 退回為遞迴
    呼叫，以子類記錄每次呼叫之 q，最後一次＝最終採用之 q）。請求 q 預設 `DEFAULT_NUM_QUANTILES`。`_assign_quantiles` 回
    None（無任何 bin）⇒ 標籤序列記為長度＝壓縮列數之全 NaN；壓縮後無列 ⇒ 空序列。全 NaN 欄：q＝請求 q、
    q_insufficient＝False、label_nan_count＝0。`progress` ⇒ 每 500 欄印一行進度（子行程心跳用）。"""
    _ensure_repo_path()
    import numpy as np

    from momentum.Analysis.monotonicity_tester import MonotonicityTester

    class _QRecorder(MonotonicityTester):
        """記錄 `_assign_quantiles` 每次呼叫之 q（不改其行為）。"""

        q_calls: List[int] = []

        def _assign_quantiles(self, data: Any, num_quantiles: int) -> Any:
            self.q_calls.append(int(num_quantiles))
            return super()._assign_quantiles(data, num_quantiles)

    requested = DEFAULT_NUM_QUANTILES if num_quantiles is None else int(num_quantiles)
    tester = _QRecorder(_monotonicity_config())
    out: Dict[str, Dict[str, Any]] = {}
    for i, col in enumerate(features.columns):
        series = features[col]
        if bool(series.isna().all()):
            out[str(col)] = {"q": requested, "q_insufficient": False, "skipped_all_nan": True, "label_sha256": None,
                             "label_nan_count": 0}
            continue
        data = tester._prepare_data(series, label)
        q = tester._select_num_quantiles(len(data), requested)
        if data.empty:
            arr = np.empty(0, dtype="float64")
        else:
            tester.q_calls = []
            bins = tester._assign_quantiles(data, q)
            q = tester.q_calls[-1]
            arr = np.full(len(data), np.nan) if bins is None else np.asarray(bins, dtype="float64")
        out[str(col)] = {"q": int(q), "q_insufficient": bool(q < requested), "skipped_all_nan": False,
                         "label_sha256": _sha_bytes(arr.tobytes()), "label_nan_count": int(np.isnan(arr).sum())}
        if progress and (i + 1) % 500 == 0:
            print(f"[icperf-pit] {i + 1}/{features.shape[1]}", flush=True)
    return out


def _prepare_cwd(cwd: Path, repo_root: Path = REPO) -> Path:
    """隔離 cwd 根（SPEC §G (b)）：建立 `cwd`，唯讀輸入 `READONLY_INPUTS` 自 `repo_root` 以 symlink 引入（repo 無該輸入者
    略過）；回 `cwd`。"""
    cwd = Path(cwd)
    cwd.mkdir(parents=True, exist_ok=True)
    for rel in READONLY_INPUTS:
        src, dst = Path(repo_root) / rel, cwd / rel
        if src.exists() and not os.path.lexists(dst):
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.symlink_to(src, target_is_directory=src.is_dir())
    return cwd


def _child_env_base() -> Dict[str, str]:
    """子行程環境之基底：本行程環境＋repo 根前置 `PYTHONPATH`（同 `ffprod_measure.ic_watched`）；不繼承寫入審計記錄檔。"""
    env = dict(os.environ)
    env.pop(CAPTURE_LOG_ENV, None)
    env["PYTHONPATH"] = os.pathsep.join([str(REPO)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    return env


def _child_cmd(spec_path: Path) -> List[str]:
    return [sys.executable, str(Path(__file__).resolve()), CHILD_CMD, str(spec_path)]


def _run_child(spec: Mapping[str, Any], *, cwd: Path, work_dir: Path, iso: Path) -> Dict[str, Any]:
    """非捕獲之計算子行程（第 (2) 項、PIT 標籤）：spec 寫 `work_dir/spec.json`，經 `run_watched`（cwd＝`cwd`、
    TMPDIR／HOME＝`iso`）啟動；rc≠0 或未寫 `out_json` ⇒ FreezeError（附 log 路徑）；回 `out_json` 之內容。"""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    spec_path = work_dir / "spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    res = run_watched(_child_cmd(spec_path), log_path=work_dir / "run.log",
                      env=isolated_env(_child_env_base(), Path(iso)), cwd=Path(cwd))
    out = Path(spec["out_json"])
    if res["rc"] != 0 or not out.is_file():
        raise FreezeError(f"子行程 {spec['task']} rc={res['rc']}、結果檔{'存在' if out.is_file() else '不存在'}"
                          f"（見 {res['log_path']}）")
    return json.loads(out.read_text(encoding="utf-8"))


def stage5_subset_digests(n_cols: int, *, seed: int = SEED) -> Dict[str, Any]:
    """改前基準全特徵 run 交接 h5 之 n_cols 欄巢狀隨機子集（seed 同探針 `icperf_probes/prep.py`）以產品
    `create_ic_analyzer(...).analyze()` 跑第 5 段；回 {"stage_cols", "features": {<特徵>: {<欄位>: value_digest}},
    "pit_labels": {...}}（"features" 之來源、欄位命名與摘要粒度同第 (1) 項，見模組說明）；交接 h5 不存在 ⇒ FreezeError
    （不以其他 run 代替）。

    請求＝第 (1) 項之 IC 頁預設請求（`default_request("ic_report")`）。子集取法同 prep.py（`default_rng(seed).permutation`
    之前 n_cols 個、排序；float32；同 root／group 屬性；meta 只留 symbol／timeframe／config_hash／ff_run_identity 與所選
    欄）。計算於子行程（`_run_child`，隔離 cwd 與 TMPDIR 於新建暫存目錄；成功即刪，失敗留現場）。stage_cols＝報告
    `filter_log.stage5_thresholds.input_features`，須等於逐特徵數。PIT 標籤＝子集交接 h5 之第 0 段特徵與第 2 段標籤。"""
    import shutil
    import tempfile

    src = Path(C_HANDOFF_H5)
    meta = src.with_name(src.stem + "_meta.json")
    if not src.is_file() or not meta.is_file():
        raise FreezeError(f"改前基準全特徵 run 交接檔不存在（不以他 run 代替）：{src if not src.is_file() else meta}")
    if src.stat().st_size != C_HANDOFF_BYTES:
        raise FreezeError(f"交接 h5 大小 {src.stat().st_size} != SPEC 實查之 {C_HANDOFF_BYTES}：{src}")
    tmp = Path(tempfile.mkdtemp(prefix=f"icperf-stage5-{int(n_cols)}-"))
    cap = tmp / "capture"
    spec = {"task": "stage5", "n_cols": int(n_cols), "seed": int(seed), "source_h5": str(src),
            "source_meta": str(meta), "request": default_request("ic_report"), "out_json": str(cap / "stage5.json")}
    result = _run_child(spec, cwd=_prepare_cwd(tmp / "cwd"), work_dir=cap, iso=tmp / "iso")
    shutil.rmtree(tmp, ignore_errors=True)
    return {"stage_cols": int(result["stage_cols"]), "features": result["features"], "pit_labels": result["pit_labels"]}


def freeze_item(item: str, *, request: Mapping[str, Any], repo_root: Path, work_root: Path) -> Dict[str, Any]:
    """凍結 §G 單一項：第 (1)、(3)、(4)、(5) 項經 `capture_run` 取回應全部欄位與寫出檔；第 (2) 項經
    `stage5_subset_digests(SUBSET_COLS)`。三根（SPEC §G (b)）：cwd 根＝新建之 `work_root/<item>/cwd`（唯讀輸入
    `data_cache/feature_klines`、`data_cache/feature_klines_longhist`、`config/` 自 `repo_root` 以 symlink 引入，同
    `scripts/ffprod_measure.py` `ic_watched`；快照不跟隨其下之目錄 symlink）、隔離目錄＝`work_root/<item>/iso`
    （TMPDIR／HOME，前綴 `<iso>`）、`repo_root`（前綴 `<repo>`，抓逃逸寫出）；`capture_run(..., repo_root=<cwd 根>,
    iso_root=<隔離目錄>, extra_roots={"<repo>": repo_root})`。子行程把回傳物件原樣以 pickle 寫
    `work_root/<item>/response.pkl`（審計記錄與 sitecustomize 亦置於 `work_root/<item>`，pickle 與記錄不在快照範圍）；
    回之記錄另含 "request"、"output_roots"（cwd 根相對 POSIX）、"roots"＝{"cwd": <cwd 根>, "iso": <隔離目錄>}（解析後
    絕對路徑；boundary_01 之獨立 oracle 以同一組根走訪並比對）、"features"／"selected"（第 (1)、(4) 項，見模組說明）。

    捕獲機制之工作目錄＝`work_root/<item>/capture`（審計記錄、sitecustomize、子行程 log、spec、暫存 registry 與子行程寫出
    之 pickle；不在快照範圍，其下之寫入由 `capture_run` 濾除）；子行程結束後由本行程（未掛審計）把 pickle 移至
    `work_root/<item>/response.pkl`。`work_root/<item>` 已存在且非空 ⇒ FreezeError（殘留會使差集隨執行前狀態而變）。
    第 (2) 項之記錄另含 "request"、"seed"、"n_cols_requested"。各項記錄另含 "volatile_candidates"（`freeze` 收至頂層）。"""
    request = _json_copy(request)
    if item == "stage5_subset":
        n_cols, seed = int(request.get("n_cols", SUBSET_COLS)), int(request.get("seed", SEED))
        return {"request": request, "seed": seed, "n_cols_requested": n_cols,
                **stage5_subset_digests(n_cols, seed=seed), "volatile_candidates": []}
    if item not in OUTPUT_ITEMS:
        raise FreezeError(f"未知凍結項：{item}")
    item_root = Path(work_root) / item
    if item_root.exists() and any(item_root.iterdir()):
        raise FreezeError(f"{item}：工作目錄已存在且非空（須新建）：{item_root}")
    cwd = _prepare_cwd(item_root / "cwd", Path(repo_root))
    iso, cap = item_root / "iso", item_root / "capture"
    cap.mkdir(parents=True, exist_ok=True)
    out_roots = resolve_output_roots(item, request, cwd)
    spec = {"task": request["kind"], "item": item, "request": request, "registry": str(cap / "registry.json"),
            "out_pickle": str(cap / "response.pkl")}
    spec_path = cap / "spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    res = capture_run(_child_cmd(spec_path), repo_root=cwd, iso_root=iso, output_roots=out_roots, work_dir=cap,
                      extra_roots={"<repo>": Path(repo_root)}, env_base=_child_env_base())
    pkl = cap / "response.pkl"
    if res["rc"] != 0 or not pkl.is_file():
        raise FreezeError(f"{item}：子行程 rc={res['rc']}、回應 pickle {'存在' if pkl.is_file() else '不存在'}"
                          f"（見 {cap / 'run.log'}）")
    os.replace(pkl, item_root / "response.pkl")
    _ensure_repo_path()  # 反序列化需可 import 產品模組（回應內之 dataclass 等）
    import pickle

    with open(item_root / "response.pkl", "rb") as fh:
        raw = pickle.load(fh)
    roots = {"cwd": os.path.realpath(cwd), "iso": os.path.realpath(iso)}
    record: Dict[str, Any] = {
        "request": request,
        "output_roots": [Path(os.path.relpath(os.path.realpath(r), roots["cwd"])).as_posix() for r in out_roots],
        "roots": roots, "response": _response_fields(item, raw), "files": res["files"],
        "transient": res["transient"], "removed": res["removed"]}
    if feature_tables(item):
        record["features"] = _feature_digests(item, raw)
        record["selected"] = _survivor_names(res["files"], cwd)
    record["volatile_candidates"] = _volatile_candidates(item, raw, res["files"], cwd, iso, Path(repo_root))
    return record


def _resolve_pointer(obj: Any, pointer: str) -> Any:
    """JSON pointer（`~1`→`/`、`~0`→`~`）取值；各層先 `_as_container`；不存在 ⇒ FreezeError。"""
    for seg in pointer.split("/")[1:]:
        obj = _as_container(obj)
        seg = seg.replace("~1", "/").replace("~0", "~")
        try:
            obj = obj[int(seg)] if isinstance(obj, (list, tuple)) else obj[seg]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise FreezeError(f"回應無 {pointer}（{exc!r}）") from exc
    return _as_container(obj)


def _feature_digests(item: str, raw: Any) -> Dict[str, Dict[str, Dict[str, str]]]:
    """逐特徵逐欄位摘要（模組說明「逐特徵欄位」）：依 `feature_tables(item)` 之形狀——"rows" 每列每欄（`feature_name`
    除外）一值、欄位名 "<來源>/<欄名 pointer 跳脫>"；"by_key" 每特徵整段子樹一值、欄位名＝來源 pointer；"frame" 每欄一值、
    數值欄以 `value_digest(1 元素 ndarray)`。"rows"／"by_key" 之值一律 `_canon_digest`。形狀不符 ⇒ FreezeError。"""
    import pandas as pd

    out: Dict[str, Dict[str, Dict[str, str]]] = {}
    for ptr, shape in feature_tables(item).items():
        src = _resolve_pointer(raw, ptr)
        if shape == "rows":
            if not isinstance(src, list) or not all(isinstance(r, dict) and "feature_name" in r for r in src):
                raise FreezeError(f"{item}：{ptr} 非以 feature_name 為鍵之 list[dict]")
            names = [str(r["feature_name"]) for r in src]
            if len(set(names)) != len(names):
                raise FreezeError(f"{item}：{ptr} 之 feature_name 重複")
            for row in src:
                feat = str(row["feature_name"])
                for c, v in row.items():
                    if c != "feature_name":
                        out.setdefault(feat, {})[f"{ptr}/{_ptr_seg(c)}"] = _canon_digest(v)
        elif shape == "by_key":
            if not isinstance(src, dict):
                raise FreezeError(f"{item}：{ptr} 非以特徵名為鍵之 dict（{type(src).__name__}）")
            for feat, sub in src.items():
                out.setdefault(str(feat), {})[ptr] = _canon_digest(sub)
        elif shape == "frame":
            if not isinstance(src, pd.DataFrame):
                raise FreezeError(f"{item}：{ptr} 非逐特徵表")
            for c in src.columns:
                numeric = pd.api.types.is_numeric_dtype(src[c])
                for feat in src.index:
                    arr = src.loc[[feat], c].to_numpy()
                    out.setdefault(str(feat), {})[f"{ptr}/{c}"] = (value_digest(arr) if numeric
                                                                    else _canon_digest(arr.tolist()))
        else:
            raise FreezeError(f"{item}：{ptr} 之形狀未知：{shape}")
    return out


def _response_fields(item: str, raw: Any) -> Dict[str, str]:
    """回應全部欄位（`flatten_fields`）扣除逐特徵來源之子路徑（"<來源 pointer>/…"；SPEC §G 摘要粒度）。"""
    sources = list(feature_tables(item))
    return {k: v for k, v in flatten_fields(raw).items() if not any(k.startswith(s + "/") for s in sources)}


def _survivor_names(files: Mapping[str, Any], cwd: Path) -> List[str]:
    """第 6 段後之倖存者：該次執行寫出差集中恰一份 `data_cache/reports/ic_survivors_<case_id>.json` 之 `feature_names`
    （排序）；份數不為一 ⇒ FreezeError。"""
    hits = sorted(k for k in files if SURVIVORS_KEY_RE.match(k))
    if len(hits) != 1:
        raise FreezeError(f"寫出差集須恰一份 ic_survivors_<case_id>.json，實得 {hits}")
    payload = json.loads((Path(cwd) / hits[0]).read_text(encoding="utf-8"))
    return sorted(str(n) for n in payload["feature_names"])


def _leaves(obj: Any, path: str = "") -> Any:
    """依 `flatten_fields` 之路徑規則逐葉產出 (欄位路徑, 值)；DataFrame／Series／ndarray 之值不展開（值為 None）。"""
    import numpy as np
    import pandas as pd

    obj = _as_container(obj)
    if isinstance(obj, (pd.DataFrame, pd.Series, np.ndarray)):
        yield path, None
    elif isinstance(obj, dict) and obj:
        for k, v in obj.items():
            yield from _leaves(v, f"{path}/{_ptr_seg(k)}")
    elif isinstance(obj, (list, tuple)) and obj and all(_is_scalar(v) for v in obj):
        yield f"{path}#values", list(obj)
    elif isinstance(obj, (list, tuple)) and obj:
        for i, v in enumerate(obj):
            yield from _leaves(v, f"{path}/{i}")
    else:
        yield path, obj


def _volatile_hits(obj: Any, roots: Sequence[str]) -> List[Tuple[str, str]]:
    """(欄位路徑, 理由)：末段欄位名含 `VOLATILE_NAME_HINTS` 者（name_hint）、或字串值含本次執行根之絕對路徑者（run_root）。"""
    out = []
    for path, val in _leaves(obj):
        last = path.rsplit("/", 1)[-1].split("#", 1)[0].lower()
        if any(h in last for h in VOLATILE_NAME_HINTS):
            out.append((path, "name_hint"))
            continue
        vals = val if isinstance(val, list) else [val]
        if any(isinstance(v, str) and any(r in v for r in roots) for v in vals):
            out.append((path, "run_root_path"))
    return out


def _volatile_candidates(item: str, raw: Any, files: Mapping[str, Any], cwd: Path, iso: Path,
                         repo_root: Path) -> List[Dict[str, str]]:
    """每次必異欄位之候選（只供 FACT-RECEIPT 判定、不自動排除）：回應與 JSON 寫出檔之欄位（格式同 `compare_golden` 之
    volatile 項：`<項>:response:<欄位>`、`<項>:file:<path_key>#<欄位>`）；HDF5 寫出檔之屬性名含提示者另列（現行 volatile
    格式只能逐欄位排除 JSON 檔，HDF5 屬性無從表達 ⇒ 理由標 hdf5_attr_unexpressible）。"""
    roots = sorted({os.path.realpath(cwd), os.path.realpath(iso), str(cwd), str(iso)})
    out = [{"entry": f"{item}:response:{p}", "reason": why} for p, why in _volatile_hits(raw, roots)]
    prefixes = {"<iso>": Path(iso), "<repo>": Path(repo_root)}
    for key, rec in sorted(files.items()):
        if rec.get("fields") is not None:
            try:
                content = json.loads(_key_path(key, Path(cwd), prefixes).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                content = None
            if content is not None:
                out += [{"entry": f"{item}:file:{key}#{p}", "reason": why} for p, why in _volatile_hits(content, roots)]
        for obj, desc in sorted((rec.get("hdf5") or {}).items()):
            for attr in sorted(desc.get("attrs") or {}):
                if any(h in attr.lower() for h in VOLATILE_NAME_HINTS):
                    out.append({"entry": f"{item}:hdf5:{key}:{obj}@{attr}", "reason": "hdf5_attr_unexpressible"})
    return out


def _git_head(repo_root: Path) -> Optional[str]:
    """讀 `.git/HEAD`（含 loose ref 與 packed-refs）之提交雜湊；不另啟子行程。讀不到 ⇒ None。"""
    git = Path(repo_root) / ".git"
    try:
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not head.startswith("ref: "):
        return head
    ref = head[len("ref: "):]
    loose = git / ref
    if loose.is_file():
        return loose.read_text(encoding="utf-8").strip()
    packed = git / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] == ref:
                return parts[0]
    return None


def _code_state(repo_root: Path) -> Dict[str, Any]:
    """凍結時之碼態：HEAD 提交、Python 與數值函式庫版本、本腳本 sha256。"""
    from importlib import metadata as md

    libs: Dict[str, Optional[str]] = {}
    for name in ("numpy", "pandas", "scipy", "h5py", "numba", "polars", "pyarrow", "statsmodels"):
        try:
            libs[name] = md.version(name)
        except md.PackageNotFoundError:
            libs[name] = None
    return {"head": _git_head(repo_root), "python": sys.version.split()[0], "libraries": libs,
            "script_sha256": _file_sha256(os.path.realpath(__file__))}


def _cell_pit_labels(cell: str, work_root: Path) -> Dict[str, Any]:
    """第 (1) 項之 PIT 標籤（`pit_label_digests(*load_cell(cell))`）：於子行程計算（`_run_child`，工作目錄
    `work_root/pit_labels`）。"""
    base = Path(work_root) / "pit_labels"
    if base.exists() and any(base.iterdir()):
        raise FreezeError(f"PIT 標籤工作目錄已存在且非空（須新建）：{base}")
    spec = {"task": "pit_labels", "cell": cell, "out_json": str(base / "capture" / "pit_labels.json")}
    return _run_child(spec, cwd=_prepare_cwd(base / "cwd"), work_dir=base / "capture", iso=base / "iso")["pit_labels"]


def freeze(out_path: Path = GOLDEN_PATH, *, repo_root: Path = REPO, work_root: Optional[Path] = None) -> Dict[str, Any]:
    """依序凍結 `G_ITEMS` 並寫 `out_path`；任一項 FreezeError ⇒ 不寫檔。

    `work_root` 未給 ⇒ 新建暫存目錄（保留供診斷，路徑記於凍結檔 "work_root"）。第 (1) 項另加 "pit_labels"
    （`_cell_pit_labels`）。凍結檔＝{"schema", "code_state", "volatile": []（FACT-RECEIPT 判定後寫入）,
    "volatile_candidates", "work_root", "items"}；以暫存檔＋`os.replace` 原子寫出（正準 JSON：sort_keys、緊湊分隔）。"""
    import tempfile

    work = Path(work_root) if work_root is not None else Path(tempfile.mkdtemp(prefix="icperf-freeze-"))
    work.mkdir(parents=True, exist_ok=True)
    items: Dict[str, Any] = {}
    candidates: List[Dict[str, str]] = []
    for item in G_ITEMS:
        print(f"[icperf-freeze] {item} 開始（工作目錄 {work / item}）", flush=True)
        items[item] = freeze_item(item, request=default_request(item), repo_root=Path(repo_root), work_root=work)
        candidates += items[item].pop("volatile_candidates", [])
        print(f"[icperf-freeze] {item} 完成", flush=True)
    print("[icperf-freeze] ic_report PIT 標籤 開始", flush=True)
    items["ic_report"]["pit_labels"] = _cell_pit_labels(CELL, work)
    golden = {"schema": "icperf-pre-change/1", "code_state": _code_state(Path(repo_root)), "volatile": [],
              "volatile_candidates": candidates, "work_root": str(work), "items": items}
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    staging = out.with_name(out.name + ".tmp")
    staging.write_text(json.dumps(golden, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=True),
                       encoding="utf-8")
    os.replace(staging, out)
    return golden


def repro(n_cols: int = REPRO_COLS, *, golden_path: Path = GOLDEN_PATH) -> Dict[str, Any]:
    """凍結之可重現性（SPEC Task 0.1 驗證；判準同 `test_freeze_reproducible`）：2,000 欄子集之 n_cols 欄巢狀子集（同 seed、
    同碼路徑）重跑第 5 段，逐特徵逐欄位與 PIT 標籤對凍結之對應欄逐位元比；回 {"n_cols", "stage_cols", "problems"}。"""
    frozen = json.loads(Path(golden_path).read_text(encoding="utf-8"))["items"]["stage5_subset"]
    cur = stage5_subset_digests(int(n_cols), seed=int(frozen.get("seed", SEED)))
    problems: List[str] = []
    if not (0 < cur["stage_cols"] <= int(n_cols) and cur["stage_cols"] == len(cur["features"])):
        problems.append(f"stage_cols {cur['stage_cols']} 不合（逐特徵數 {len(cur['features'])}、請求 {n_cols}）")
    extra = sorted(set(cur["features"]) - set(frozen["features"]))
    if extra:
        problems.append(f"非 2,000 欄子集之巢狀子集：{extra[:5]}")
    for feat, fields in sorted(cur["features"].items()):
        if feat in frozen["features"]:
            problems += _compare_maps(frozen["features"][feat], fields, f"features/{feat}/")
    for feat, rec in sorted(cur["pit_labels"].items()):
        if rec != (frozen.get("pit_labels") or {}).get(feat):
            problems.append(f"pit_labels/{feat}：不等")
    return {"n_cols": int(n_cols), "stage_cols": cur["stage_cols"], "problems": problems}


# ── 子行程入口（`_child <spec.json>`；由 `capture_run`／`_run_child` 經共用監看啟動） ─────────────────────────


def _progress(payload: Mapping[str, Any]) -> None:
    """產品進度回呼：印出使共用監看之 log 心跳反映實際進度（同 `ffprod_measure.ic_in_process`）。"""
    keys = ("stage_name", "stage", "progress", "module_name", "current_step", "message")
    print("[icperf-progress] " + json.dumps({k: payload.get(k) for k in keys if k in payload}, ensure_ascii=False,
                                            default=str), flush=True)


def _child_ic_page(spec: Mapping[str, Any]) -> Any:
    """第 (1)(3)(4) 項：同 `ffprod_measure.ic_in_process`（服務 `_build_config_override` 得 override、
    `_materialize_features_for_ic` 物化〔寫 cwd 相對之交接快取〕、`create_ic_analyzer(override).analyze`）；回報告 dict。
    第 (3) 項：同一 analyzer 實例續跑深度分析（服務 `_run_deep_analysis` 之同一步驟：`_build_deep_module_override`、
    `_resolve_selected_features`、`run_deep_analysis`、`_serialize_deep_report`、`_attach_cross_symbol_context`），回其序列化。"""
    from api.models.ic_models import DeepAnalysisRequest
    from api.services.ic_analysis_service import FEATURE_KLINE_CACHE_DIR
    from momentum.factories import create_ic_analyzer, create_kline_storage_manager

    request = spec["request"]
    svc = _ic_service(request, Path(spec["registry"]))
    override = svc._build_config_override(_ic_analyze_request(request))
    analyzer = create_ic_analyzer(override)
    features_path, meta_path = svc._materialize_features_for_ic(request["symbol"], request["timeframe"],
                                                                request["config_hash"])
    report = analyzer.analyze(features_path=features_path, labels_path="", meta_path=meta_path,
                              config_override=override, progress_callback=_progress,
                              kline_reader=create_kline_storage_manager(cache_dir=FEATURE_KLINE_CACHE_DIR))
    if request.get("deep") is None:
        return report
    deep_request = DeepAnalysisRequest(**request["deep"])
    deep_override = svc._build_deep_module_override(deep_request)
    selected = svc._resolve_selected_features(analyzer=analyzer, selected_features=deep_request.selected_features,
                                              top_n=deep_request.top_n)
    deep_report = analyzer.run_deep_analysis(selected, deep_override, _progress, None)
    return svc._attach_cross_symbol_context(svc._serialize_deep_report(deep_report), analyzer)


def _child_ic_first(spec: Mapping[str, Any]) -> Any:
    """第 (5) 項：NUMVIEW 判準檔 A 格定義之 `FeatureFactory.run_ic_first`，呼叫法同 `scripts/numview_freeze_baseline.py`
    `generate_cell_run`（:316-323；輸出段、設定覆寫、連續性同其估時器函式；`_isolated(cwd, {})` 清除影響值之環境變數並把
    特徵根、registry、CGSA、d* 快取、tempdir 導向本次 cwd 根）；不寫 NUMVIEW sidecar。回 `FeatureGenerationResult`。"""
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    nfb = _load("icperf_numview_freeze_baseline", REPO / "scripts" / "numview_freeze_baseline.py")
    est, criteria = nfb._estimator(), nfb._criteria()
    request = spec["request"]
    cell, generation = request["cell"], request["generation"]
    symbol, primary = str(cell["symbol"]), str(cell["timeframes"][0])
    training = nfb._training_timeframes(cell)
    payload = est.cell_payload(cell, criteria, training)
    source = est.cell_source(cell, criteria)
    start, end = est.cell_window(cell, criteria)
    continuity = est.continuity_plan(cell, criteria, training)
    gaps = est.window_gap_violations(continuity, start)
    if gaps:
        raise FreezeError(f"{cell['id']}：輸出段內有 K 線缺口（data_gap）：{gaps}")
    with nfb._isolated(Path.cwd(), {}) as features_root:
        factory = create_feature_factory(cache_dir=str(source.parent),
                                         validate_continuity=continuity["validate_continuity"])
        factory._storage = FeatureStorage(str(features_root))
        config = factory._resolve_config(payload)
        return factory.run_ic_first(symbol, primary, config, start_date=start, end_date=end,
                                    ic_engine=ICEngine(dict(generation["ic_engine_config"])),
                                    feature_reader=FeatureReader(str(features_root)),
                                    ic_threshold=generation["ic_threshold"],
                                    label_horizon=str(generation["label_horizon"]),
                                    cleanup_raw=bool(generation["cleanup_raw"]))


def _write_stage5_subset(src_h5: Path, src_meta: Path, n_cols: int, seed: int, out_dir: Path) -> Tuple[Path, Path]:
    """交接 h5 之 n_cols 欄巢狀隨機子集（同 `handoffs/run_receipts/icperf_probes/prep.py`：`default_rng(seed).permutation`
    之前 n_cols 個排序、依 chunk 寬 ×6 之欄段讀、float32、root／group 屬性照抄、gzip；meta 只留 symbol／timeframe／
    config_hash／ff_run_identity 與所選欄）；回 (h5, meta)。"""
    import h5py
    import numpy as np

    meta_all = json.loads(Path(src_meta).read_text(encoding="utf-8"))
    symbol, tf = str(meta_all["symbol"]), str(meta_all["timeframe"])
    with h5py.File(src_h5, "r") as f:
        root_attrs = dict(f.attrs)
        g = f[f"{symbol}/{tf}"]
        group_attrs = dict(g.attrs)
        names = [n.decode() if isinstance(n, bytes) else str(n) for n in g["feature_names"][:]]
        ts = g["timestamps"][:]
        ds = g["features"]
        total = int(ds.shape[1])
        if not 0 < n_cols <= total:
            raise FreezeError(f"子集欄數 {n_cols} 不在 (0, {total}]")
        chosen = np.sort(np.random.default_rng(seed).permutation(total)[:n_cols])
        cols = np.empty((ds.shape[0], n_cols), dtype=np.float32)
        slab = (ds.chunks[1] if ds.chunks else total) * 6
        pos = 0
        for start in range(0, total, slab):
            stop = min(start + slab, total)
            sel = chosen[(chosen >= start) & (chosen < stop)]
            if sel.size == 0:
                continue
            block = ds[:, start:stop]
            cols[:, pos:pos + sel.size] = block[:, sel - start]
            pos += sel.size
    if pos != n_cols:
        raise FreezeError(f"子集讀取欄數 {pos} != {n_cols}")
    if len(meta_all) != total + 4:
        raise FreezeError(f"交接 meta 鍵數 {len(meta_all)} != 欄數 {total} + 4（prep.py 之同一前提）")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    h5, meta = out_dir / Path(src_h5).name, out_dir / Path(src_meta).name
    with h5py.File(h5, "w") as f:
        for k, v in root_attrs.items():
            f.attrs[k] = v
        g = f.create_group(f"{symbol}/{tf}")
        for k, v in group_attrs.items():
            g.attrs[k] = v
        g.create_dataset("features", data=cols, compression="gzip")
        g.create_dataset("timestamps", data=ts, compression="gzip")
        g.create_dataset("feature_names", data=np.array([names[int(c)] for c in chosen], dtype=object),
                         dtype=h5py.string_dtype(encoding="utf-8"))
    out_meta = {k: v for k, v in meta_all.items() if k in ("symbol", "timeframe", "config_hash", "ff_run_identity")}
    for c in chosen:
        out_meta[names[int(c)]] = meta_all[names[int(c)]]
    meta.write_text(json.dumps(out_meta, ensure_ascii=False), encoding="utf-8")
    return h5, meta


def _child_stage5(spec: Mapping[str, Any]) -> Dict[str, Any]:
    """第 (2) 項：子集交接 h5（cwd 下 `stage5_input/`）以 IC 頁預設請求之 override 跑產品 `analyze`；回 {"stage_cols",
    "features", "pit_labels"}（見 `stage5_subset_digests`）。"""
    from api.services.ic_analysis_service import FEATURE_KLINE_CACHE_DIR
    from momentum.factories import create_ic_analyzer, create_kline_storage_manager

    override = _override_for(spec["request"])
    h5, meta = _write_stage5_subset(Path(spec["source_h5"]), Path(spec["source_meta"]), int(spec["n_cols"]),
                                    int(spec["seed"]), Path.cwd() / "stage5_input")
    report = create_ic_analyzer(override).analyze(
        features_path=str(h5), labels_path="", meta_path=str(meta), config_override=override,
        progress_callback=_progress, kline_reader=create_kline_storage_manager(cache_dir=FEATURE_KLINE_CACHE_DIR))
    features = _feature_digests("stage5_subset", report)
    stage_cols = ((report.get("filter_log") or {}).get("stage5_thresholds") or {}).get("input_features")
    if isinstance(stage_cols, bool) or not isinstance(stage_cols, (int, float)) or int(stage_cols) != len(features):
        raise FreezeError(f"第 5 段輸入欄數 {stage_cols!r} != 逐特徵數 {len(features)}")
    pit = pit_label_digests(*_stage0_and_label(h5, meta, override), progress=True)
    return {"stage_cols": int(stage_cols), "features": features, "pit_labels": pit}


def _child_pit_labels(spec: Mapping[str, Any]) -> Dict[str, Any]:
    """第 (1) 項之 PIT 標籤：`pit_label_digests(*load_cell(cell))`。"""
    features, label = load_cell(str(spec["cell"]))
    return {"pit_labels": pit_label_digests(features, label, progress=True)}


def _child_main(spec_path: Path) -> int:
    """子行程入口：依 spec["task"] 分派；結果寫 spec["out_pickle"]（原樣 pickle）及／或 spec["out_json"]；例外印堆疊、rc=3。"""
    import pickle
    import traceback

    _ensure_repo_path()
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    tasks = {"ic_page": _child_ic_page, "ic_first": _child_ic_first, "stage5": _child_stage5,
             "pit_labels": _child_pit_labels}
    try:
        if spec.get("task") not in tasks:
            raise FreezeError(f"未知子行程任務：{spec.get('task')!r}")
        result = tasks[spec["task"]](spec)
        if spec.get("out_pickle"):
            with open(spec["out_pickle"], "wb") as fh:
                pickle.dump(result, fh, protocol=pickle.HIGHEST_PROTOCOL)
        if spec.get("out_json"):
            Path(spec["out_json"]).write_text(json.dumps(result, ensure_ascii=False, allow_nan=True), encoding="utf-8")
    except BaseException:  # noqa: BLE001 — 子行程任何失敗皆以 rc≠0 回報，堆疊進監看 log
        traceback.print_exc()
        sys.stdout.flush()
        return 3
    return 0


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
    """CLI：freeze／repro／inventory／measure（見模組說明）。freeze／repro 之 FreezeError ⇒ 訊息印 stderr、rc=1；
    repro 有任一不等 ⇒ rc=1。inventory／measure 呼叫 Task 0.2 入口（施工前為空殼 ⇒ NotImplementedError 原樣上拋）。"""
    import argparse

    parser = argparse.ArgumentParser(
        prog="icperf_freeze_baseline.py",
        description="ICPERF Phase 0（docs/ICPERF_SPEC.md §G、Task 0.1／0.2）：凍結改前輸出、可重現性重跑、規模盤點。"
                    "重型（scripts/heavy_commands.json self_watched）：須背景執行，子行程經共用監看。")
    sub = parser.add_subparsers(dest="cmd", metavar="{freeze,repro,inventory,measure}")
    p = sub.add_parser("freeze", help="凍結 §G 第 (1)–(5) 項，寫凍結檔")
    p.add_argument("--out", type=Path, default=GOLDEN_PATH, help=f"凍結檔（預設 {GOLDEN_PATH.relative_to(REPO)}）")
    p.add_argument("--work-root", type=Path, default=None, help="各項隔離工作目錄之根（預設新建暫存目錄；項目錄須不存在）")
    p = sub.add_parser("repro", help="第 5 段巢狀子集重跑，對凍結檔逐位元比")
    p.add_argument("--cols", type=int, default=REPRO_COLS, help=f"子集欄數（預設 {REPRO_COLS}）")
    p.add_argument("--golden", type=Path, default=GOLDEN_PATH, help="凍結檔")
    p.add_argument("--out", type=Path, default=None, help="比對結果 JSON（不給則只印出）")
    p = sub.add_parser("inventory", help="Task 0.2 路徑清冊")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("measure", help="Task 0.2 規模量測")
    p.add_argument("--inventory", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser(CHILD_CMD)
    p.add_argument("spec", type=Path)
    args = parser.parse_args(argv)
    if args.cmd is None:
        parser.print_help()
        return 2
    if args.cmd == CHILD_CMD:
        return _child_main(args.spec)
    try:
        if args.cmd == "freeze":
            golden = freeze(args.out, work_root=args.work_root)
            print(json.dumps({"out": str(args.out), "work_root": golden["work_root"],
                              "items": {k: sorted(v) for k, v in golden["items"].items()},
                              "volatile_candidates": len(golden["volatile_candidates"])}, ensure_ascii=False))
            return 0
        if args.cmd == "repro":
            result = repro(args.cols, golden_path=args.golden)
            text = json.dumps(result, ensure_ascii=False, indent=1)
            if args.out is not None:
                Path(args.out).parent.mkdir(parents=True, exist_ok=True)
                Path(args.out).write_text(text, encoding="utf-8")
            print(json.dumps({**result, "problems": result["problems"][:50], "n_problems": len(result["problems"])},
                             ensure_ascii=False, indent=1))
            return 0 if not result["problems"] else 1
    except FreezeError as exc:
        print(f"FreezeError：{exc}", file=sys.stderr)
        return 1
    if args.cmd == "inventory":
        inv = build_path_inventory(REPO)
        Path(args.out).write_text(json.dumps(inv, ensure_ascii=False, indent=1), encoding="utf-8")
        return 0
    inventory = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    measure_inventory(inventory, out_path=Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

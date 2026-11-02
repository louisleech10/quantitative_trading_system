"""ICPERF Phase 0 具名驗收（docs/ICPERF_SPEC.md §G、Task 0.1／0.2；manifest docs/manifests/ICPERF.json）。

施工前為紅：`scripts/icperf_freeze_baseline.py` 為空殼，凍結檔與 Task 0.2 收據尚未產出。
- boundary_05–13 與三支 mutation：秒級，只用 tmp_path 自建小檔（h5py／tempfile 寫入屬捕獲機制之邊界輸入、不涉資料值，
  SPEC Task 0.1、§V）。
- boundary_01／02：讀凍結檔 `tests/_golden/icperf/pre_change.json.gz`，另以測試自寫之獨立 oracle（os.walk 全樹前後差集＋
  回應鍵集合）對小規模真實請求對照（slow＋requires_kline）。
- boundary_03／04：讀真實資料 A 格（requires_kline，缺檔 FAIL）；boundary_21：真實 kline 索引上之明列邊界輸入（秒級，
  requires_kline）。
- boundary_14–20：讀 Task 0.2 收據（各恰一份），量測點逐欄綁定 scale_probe 收據；清冊與量測收據之 coverage_path_id／
  unit_axis／scale_vector（與 Task 5.4 共用 schema）、峰值 Physical footprint、四項機會欄（SPEC v5.13–v5.21）。
- boundary_24／25：秒級契約——逐特徵來源與形狀＝SPEC §G（IC 報告為 dict：summary_table list[dict]、其餘以特徵名為鍵）；
  凍結腳本寫死之 IC 頁初始 payload（衰減開）== 前端原始碼與 ui_stage_toggles.json 導出值。
- Task 0.3（現行 IC 正確性獨立驗證）之測試另見 tests/momentum/Analysis/test_icperf_correctness.py。
- test_freeze_reproducible：重型（slow＋requires_kline；SPEC v5.24：同一 2,000 欄子集第 5 段重跑，改前實測 1610.20 秒，
  handoffs/run_receipts/icperf_probes/result_N2000.json）。
- C 格交接 h5 身分（SPEC v5.24 §G (2)）：路徑覆寫、不存在、大小不符、內容 sha256 不符之 FreezeError（秒級，tmp_path 小檔）。
- 本檔之 pytest 列 `scripts/heavy_commands.json` 之 wrapped（`pytest_icperf_gate`）：須經共用監看包裝並背景；只有
  `-m "not slow and not requires_kline"`（排除全部重型與真實資料測試）之選取不列重型。
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import hashlib
import importlib.util
import json
import os
import pickle
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "icperf_freeze_baseline.py"
GOLDEN = REPO / "tests" / "_golden" / "icperf" / "pre_change.json.gz"  # SPEC v5.25 §G：gzip 存檔
INVENTORY_PATTERN = "handoffs/run_receipts/*-icperf-path-inventory.json"
SCALE_BEFORE_PATTERN = "handoffs/run_receipts/*-icperf-scale-before.json"

#: SPEC §G (1)–(5)（測試自持之 oracle，不引腳本常數）
G_ITEMS = ("ic_report", "stage5_subset", "deep_analysis", "event_report", "icfirst_post_ic",
           "ic_report_long", "deep_analysis_long", "event_import_report")  # SPEC v5.26 §G (1)–(7) 九鍵
#: §G 凍結範圍：第 (1)、(3)、(4)、(5) 項須含回應全部欄位與快照差集之全部寫出檔
OUTPUT_ITEMS = ("ic_report", "deep_analysis", "event_report", "icfirst_post_ic",
                "ic_report_long", "deep_analysis_long", "event_import_report")
#: 請求未定之項（default_request／freeze／volatile_probe 須 FreezeError）：SPEC v5.26 第 (6)(7) 項之 L 格與匯入批已於
#: Task 0.3 定 ⇒ 空；fail-closed 之驗證以替身設一待定項（`PENDING_PROBE`）
PENDING_ITEMS: Tuple[str, ...] = ()
PENDING_PROBE = ("ic_report_long", "deep_analysis_long", "event_import_report")
#: SPEC v5.26 Task 0.3 FACT-RECEIPT：第 (6)(7) 項之資料格與事件匯入批（測試自持）
LONG_CELL = "L_BTCUSDT_4h_longhist"
EVENT_IMPORT_ID = "20261030T140536Z-91a1dc03"  # SPEC v5.38 Task 0.3 補足①：重建之事件匯入批
#: §G：第 (1)、(2)、(4) 項為逐特徵逐欄位輸出（SPEC v5.8：第 (3) 項深度分析之逐模組逐欄位由「回應全部欄位」涵蓋）
FEATURE_ITEMS = ("ic_report", "stage5_subset", "event_report", "ic_report_long", "event_import_report")  # v5.26 增 (6)(7)
#: SPEC §G baseline 內容：IC 報告（dict）之逐特徵來源與形狀（測試自持）——summary_table＝list[dict]、以 feature_name 為鍵；
#: 其餘＝以特徵名為鍵之 dict
FEATURE_SOURCES = {"/summary_table": "rows", "/quantile_returns": "by_key", "/coverage_analysis": "by_key",
                   "/turnover_analysis": "by_key"}
#: 回應帶逐特徵來源之項（第 (1)、(4) 項）；其選欄通過集合＝第 6 段後之倖存者，取自寫出之 ic_survivors_<case_id>.json
SURVIVOR_ITEMS = ("ic_report", "event_report", "ic_report_long", "event_import_report")  # v5.26 增 (6)(7)
#: 倖存者檔之 path_key（cwd 根相對；momentum/Analysis/ic_reporter.py:880 `ic_survivors_{case_id}.json`，case_id 預設
#: ic_gatekeeper，ic_filter_orchestrator.py:5837）
SURVIVORS_KEY_RE = re.compile(r"^data_cache/reports/ic_survivors_[^/]+\.json$")
CELL = "A_BTCUSDT_1h"
SEED = 20261027
HEX64 = re.compile(r"^[0-9a-f]{64}$")

#: SPEC Task 0.2 範圍：第 0–7 段（含 6b）、深度分析、IC 後轉換、IC-first、事件型路徑
REQUIRED_STAGES = {"0", "1", "2", "3", "4", "5", "6", "6b", "7", "deep_analysis", "post_ic_transform", "icfirst", "event"}
#: SPEC Task 0.2 具名之逐根 PIT 入口
REQUIRED_NAMED_ENTRIES = {
    "momentum.Analysis.long_short_analyzer:LongShortAnalyzer.compute_pit_bins",  # long_short_analyzer.py:56-60
    "momentum.Analysis.factor_return_analyzer:FactorReturnAnalyzer._pit_expanding_position",  # :319-366
}
#: SPEC Task 0.2：pit_stats 四函式之「各呼叫端」
PIT_CALLEES = ("pit_expanding_bounds", "pit_expanding_quantile_thresholds", "pit_expanding_mean_std", "pit_expanding_mad")
INVENTORY_KEYS = {"id", "stage", "input_axes", "ic_page", "ic_first", "loop", "measure", "no_measure_reason", "evidence"}
INPUT_AXES = {"cols", "rows", "passed_cols"}
LOOPS = {"per_bar", "per_column", "per_group", "none"}
SCALE_POINTS = {500, 1000, 2000}
#: SPEC Task 0.2／5.4 共用 schema：scale_vector 之軸（各入口取其所用者）；SPEC v5.49 處置④增事件數、標的數、時點數
SCALE_VECTOR_KEYS = {"rows", "input_cols", "stage_cols", "survivors", "survivor_pairs", "events", "symbols", "timestamps"}
#: SPEC Task 0.2「記憶體量測與四項機會欄」
OPPORTUNITY_KEYS = {"time", "memory", "precision", "file_size"}
OPPORTUNITY_STATUSES = {"none", "planned", "needs_user", "done"}
OPPORTUNITY_FIELDS = {"status", "evidence", "before", "after", "downstream", "user_ruling"}
#: §B 峰值記憶體門檻工具（同 scripts/measure_ic_footprint.sh；handoffs/run_receipts/gap3ux-b9-footprint.receipt.json 之 tool）
FOOTPRINT_TOOL = "sample:Physical footprint"
#: SPEC §G 時間紀律：§B ICPERF-BUDGET-2 上界 80 分鐘（SPEC v5.7）
BUDGET2_UPPER_SECONDS = 80 * 60
#: SPEC Task 0.2 邊界：元件於 2000 欄逾 10 分鐘 ⇒ 只量 500／1000
TWO_POINT_SECONDS = 10 * 60
#: boundary_01／02 獨立 oracle 之小規模真實請求欄數
ORACLE_FEATURES = 20
#: 獨立 oracle 之快照排除（SPEC §G 原文：.git、venv、__pycache__、numba 快取、測試選取工具狀態目錄；測試自持）
ORACLE_EXCLUDE_DIRS = {".git", "venv", "__pycache__", ".testsel"}
ORACLE_EXCLUDE_SUFFIXES = (".nbi", ".nbc")
KLINE_CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


HEAVY_MARKERS = ("slow", "requires_kline")


def _watchdog_missing(markers: Sequence[str], environ: Mapping[str, str]) -> bool:
    """本檔重型／真實資料測試（標 slow 或 requires_kline）未在共用監看下執行 ⇒ True。共用監看對子行程恆注入
    `WATCHDOG_STACK_FILE`（handoffs/run_receipts/numview_probes/_watchdog.py:462 `stack_dump_env`）。"""
    return any(m in HEAVY_MARKERS for m in markers) and not environ.get("WATCHDOG_STACK_FILE")


@pytest.fixture(autouse=True)
def _heavy_tests_require_shared_watchdog(request: pytest.FixtureRequest) -> None:
    """r13 CODEX-R13-P1-01：下指令閘以字面比對命令（命令經 shell 變數傳路徑即比不到），故本檔重型測試於執行端自證經共用
    監看——不論命令怎麼寫，未經監看即 FAIL，不靜默在前景無監看跑完。"""
    if _watchdog_missing([m.name for m in request.node.iter_markers()], os.environ):
        pytest.fail("本檔標 slow／requires_kline 之測試須經共用監看執行："
                    "venv/bin/python scripts/run_watched.py --log <路徑> -- <pytest 命令>（背景）")


@pytest.fixture(scope="module")
def fb() -> Any:
    return _load("icperf_freeze_baseline", SCRIPT)


@pytest.fixture(scope="module")
def scale_probe() -> Any:
    return _load("icperf_gate_scale_probe", REPO / "scripts" / "scale_probe.py")


# ── 共用小工具 ─────────────────────────────────────────────────────────────────────────────────────────


def _key(path: Path, repo: Path, prefixes: Optional[Mapping[str, Path]] = None) -> str:
    """path_key（SPEC §G (b) 三根前綴規則；測試自算，不引腳本之 path_key）：`repo`＝本次執行之工作目錄（cwd 根）之下＝
    相對 POSIX；`prefixes` 所列根（如 {"<iso>": 隔離目錄, "<repo>": repo 根}）之下＝`<前綴>/<相對 POSIX>`；多根皆含時
    取解析後路徑最長（最具體）之根；皆不含＝解析後絕對路徑。"""
    p = path.resolve()
    best: Optional[Tuple[str, Path]] = None
    for prefix, root in [("", repo)] + list((prefixes or {}).items()):
        r = Path(root).resolve()
        if (p == r or r in p.parents) and (best is None or len(str(r)) > len(str(best[1]))):
            best = (prefix, r)
    if best is None:
        return str(p)
    rel = p.relative_to(best[1]).as_posix()
    return rel if best[0] == "" else f"{best[0]}/{rel}"


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "data_cache" / "features").mkdir(parents=True, exist_ok=True)
    (repo / "data_cache" / "reports").mkdir(parents=True, exist_ok=True)
    return repo


#: SPEC §G (b)／`freeze_item` 契約：隔離 cwd 根以 symlink 自 repo 引入之唯讀輸入（相對 cwd 根之路徑）
READONLY_INPUTS = ("data_cache/feature_klines", "data_cache/feature_klines_longhist", "config")


def _isolated_cwd_root(work_root: Path, item: str) -> Path:
    """與 `freeze_item` 同語意之隔離 cwd 根（測試自建，不引腳本）：`work_root/<item>/cwd`，唯讀輸入 `READONLY_INPUTS`
    自 repo 以 symlink 引入（repo 無該輸入者略過）。"""
    cwd = work_root / item / "cwd"
    cwd.mkdir(parents=True, exist_ok=True)
    for rel in READONLY_INPUTS:
        src, dst = REPO / rel, cwd / rel
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.symlink_to(src, target_is_directory=src.is_dir())
    return cwd


def _capture(fb: Any, tmp_path: Path, body: str, *, output_roots: Optional[Sequence[Path]] = None,
             tag: str = "child") -> Dict[str, Any]:
    """於 tmp_path/repo 以子行程執行 `body`，經腳本之寫出捕獲取結果。"""
    repo = _repo(tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    child = scripts / f"{tag}.py"
    child.write_text(textwrap.dedent(body), encoding="utf-8")
    roots = list(output_roots) if output_roots is not None else [repo / "data_cache"]
    return fb.capture_run([sys.executable, str(child)], repo_root=repo, iso_root=tmp_path / f"iso_{tag}",
                          output_roots=roots, work_dir=tmp_path / f"work_{tag}")


def _logged_paths(res: Mapping[str, Any]) -> List[str]:
    return [str(Path(e["path"]).resolve()) for e in res["write_log"]]


def _golden() -> Dict[str, Any]:
    assert GOLDEN.is_file(), f"凍結檔不存在：{GOLDEN}（Task 0.1 尚未凍結）"
    import gzip

    return json.loads(gzip.decompress(GOLDEN.read_bytes()).decode("utf-8"))


#: SPEC v5.24 §G (2)：C 格交接 h5 路徑之環境變數（測試自持，不引腳本常數）
C_HANDOFF_ENV = "ICPERF_C_HANDOFF_H5"


def _sha256_of_file(path: Any) -> str:
    """檔案內容 sha256（4 MiB 分塊；測試自算，不經腳本之快取）。"""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def _c_handoff_file(frozen_stage5: Mapping[str, Any]) -> Path:
    """重跑所用之 C 格交接 h5：環境變數覆寫優先，否則凍結所記之 `request.source_h5`（SPEC v5.24 §G (2)）。"""
    return Path(os.environ.get(C_HANDOFF_ENV) or frozen_stage5["request"]["source_h5"])


def _single(pattern: str) -> Dict[str, Any]:
    paths = sorted(REPO.glob(pattern))
    assert len(paths) == 1, f"{pattern} 須恰一份，實得 {[str(p) for p in paths]}"
    return json.loads(paths[0].read_text(encoding="utf-8"))


def _inventory_entries() -> Dict[str, Dict[str, Any]]:
    inv = _single(INVENTORY_PATTERN)
    entries = inv["entries"]
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids)), "清冊入口 id 重複"
    return {e["id"]: e for e in entries}


# ── 獨立 oracle（不經凍結腳本之最小實作；boundary_01／02） ─────────────────────────────────────────────


def _oracle_roots(cwd: Path, iso: Path) -> Dict[str, Path]:
    """獨立 oracle 之三根（SPEC §G (b)）：工作目錄（cwd 根，前綴空）、隔離目錄 `<iso>`、repo 根 `<repo>`。"""
    return {"": Path(cwd), "<iso>": Path(iso), "<repo>": REPO}


def _oracle_walk(roots: Mapping[str, Path]) -> Dict[str, Tuple[int, int]]:
    """os.walk 全樹：{path_key: (大小, mtime_ns)}；`roots`＝{前綴: 根}（`_oracle_roots`；前綴空者為 cwd 根），鍵依 `_key`
    之三根前綴規則；排除集照 SPEC §G 原文（含 NUMBA_CACHE_DIR 整棵），不引腳本。不跟隨目錄 symlink（cwd 內唯讀輸入之
    symlink 不展開）。"""
    nd = os.environ.get("NUMBA_CACHE_DIR")
    numba_dir = Path(nd).resolve() if nd else None
    cwd_root = Path(roots[""])  # cwd 根必給（不得以 git 根 REPO 代之；r30 CODEX-R30-P1-01 同類）
    prefixes = {k: Path(v) for k, v in roots.items() if k}
    out: Dict[str, Tuple[int, int]] = {}
    for root in roots.values():
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in ORACLE_EXCLUDE_DIRS
                           and not (numba_dir is not None and (Path(dirpath) / d).resolve() == numba_dir)]
            for fn in filenames:
                if fn.endswith(ORACLE_EXCLUDE_SUFFIXES):
                    continue
                p = Path(dirpath) / fn
                try:
                    st = p.stat()
                except OSError:
                    continue
                out[_key(p, cwd_root, prefixes)] = (st.st_size, st.st_mtime_ns)
    return out


def _as_container(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if hasattr(obj, "model_dump") and not isinstance(obj, (pd.DataFrame, pd.Series)):
        return obj.model_dump()
    return obj


def _ptr(seg: Any) -> str:
    return str(seg).replace("~", "~0").replace("/", "~1")


def _oracle_field_paths(obj: Any, path: str = "") -> Set[str]:
    """回應物件之欄位路徑集合（規則照 `flatten_fields` docstring；測試自寫，不呼叫腳本）。"""
    obj = _as_container(obj)
    if isinstance(obj, pd.DataFrame):
        return {f"{path}#index"} | {f"{path}/{_ptr(c)}{s}" for c in obj.columns for s in ("#values", "#nan_mask")}
    if isinstance(obj, pd.Series):
        return {f"{path}#index", f"{path}#values", f"{path}#nan_mask"}
    if isinstance(obj, np.ndarray):
        return {f"{path}#values", f"{path}#nan_mask"}
    if isinstance(obj, dict) and obj:
        return set().union(*(_oracle_field_paths(v, f"{path}/{_ptr(k)}") for k, v in obj.items()))
    if isinstance(obj, (list, tuple)) and obj and all(v is None or isinstance(v, (bool, int, float, str, np.generic))
                                                     for v in obj):
        return {f"{path}#values", f"{path}#nan_mask"}  # 純量序列整段一值（SPEC §G 摘要粒度）
    if isinstance(obj, (list, tuple)) and obj:
        return set().union(*(_oracle_field_paths(v, f"{path}/{i}") for i, v in enumerate(obj)))
    return {path}


def _resolve(obj: Any, pointer: str) -> Any:
    for seg in pointer.split("/")[1:]:
        obj = _as_container(obj)
        seg = seg.replace("~1", "/").replace("~0", "~")
        obj = obj[int(seg)] if isinstance(obj, (list, tuple)) else obj[seg]
    return _as_container(obj)


def _oracle_response_fields(item: str, raw: Any) -> Set[str]:
    """§G 摘要粒度：回應全部欄位扣除逐特徵來源之子路徑（逐特徵來源不於「回應全部欄位」重複攤平；來源本身為空容器時
    仍以純量記）。只對回應帶逐特徵來源之項（SURVIVOR_ITEMS）扣除。"""
    fields = _oracle_field_paths(raw)
    if item not in SURVIVOR_ITEMS:
        return fields
    return {p for p in fields if not any(p.startswith(src + "/") for src in FEATURE_SOURCES)}


def _canon(v: Any) -> Any:
    """`value_digest` 之正準形（腳本 docstring 之規則；測試自寫，不呼叫腳本）。"""
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
    if isinstance(c, dict):
        return {k: _nan_tree(x) for k, x in c.items()}
    if isinstance(c, list):
        return [_nan_tree(x) for x in c]
    return isinstance(c, float) and c != c


def _canon_bytes(c: Any) -> bytes:
    return json.dumps(c, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=True).encode("utf-8")


def _oracle_digest(v: Any) -> Dict[str, str]:
    """"rows" 之欄值與 "by_key" 之整段子樹之摘要（SPEC §G 摘要粒度：子樹攤平後之正準序列化雜湊，含 NaN 遮罩）。"""
    c = _canon(v)
    return {"sha256": hashlib.sha256(_canon_bytes(c)).hexdigest(),
            "nan_mask_sha256": hashlib.sha256(_canon_bytes(_nan_tree(c))).hexdigest()}


def _is_table_field(field: str) -> bool:
    """逐特徵欄位名是否屬表結構（"rows"／"frame" 之 "<來源>/<欄名>"）；"by_key" 之欄位名＝來源 pointer 本身（單段）。"""
    return field.rsplit("/", 1)[0] != ""


def _oracle_survivors(run: Mapping[str, Any]) -> Tuple[List[str], Optional[List[str]]]:
    """獨立 oracle 之倖存者：(同次執行寫出差集中之 ic_survivors_<case_id>.json 鍵〔cwd 根相對〕, 恰一個時其
    feature_names〔momentum/Analysis/survivor_contract.py〕，否則 None)；份數由呼叫端斷言。"""
    hits = sorted(k for k in run.get("written") or () if SURVIVORS_KEY_RE.match(k))
    if len(hits) != 1:
        return hits, None
    payload = json.loads((Path(run["roots"]["cwd"]) / hits[0]).read_text(encoding="utf-8"))
    return hits, [str(n) for n in payload["feature_names"]]


def _top_segments(paths: Sequence[str]) -> Set[str]:
    return {p[1:].split("/")[0].split("#")[0] if p.startswith("/") else p for p in paths}


def _root_of(key: str, roots: Sequence[str]) -> str:
    """path_key 所屬之輸出根（`roots` 為 cwd 相對 POSIX）；`<iso>/`、`<repo>/` 前綴者歸其前綴，絕對路徑歸 `<outside>`。"""
    for r in roots:
        r = r.rstrip("/")
        if key == r or key.startswith(r + "/"):
            return r
    for prefix in ("<iso>", "<repo>"):
        if key.startswith(prefix + "/"):
            return prefix
    return "<outside>" if key.startswith("/") else "<other>"


def _check_item_against_oracle(fb: Any, name: str, run: Mapping[str, Any], frozen_item: Mapping[str, Any]) -> None:
    """boundary_02 之單項判定（r12 CODEX-R12-P1-02／-P1-03：抽出以供 mutation 直接驅動）。逐特徵來源依
    `fb.feature_tables(name)` 之形狀（SPEC §G baseline 內容；IC 報告為 dict，各形狀見腳本 `feature_tables`）：
    "rows"（summary_table：list[dict]、以 feature_name 為鍵）每列每欄一值、"by_key"（quantile_returns、coverage_analysis、
    turnover_analysis）每特徵整段子樹一值（`_oracle_digest`）、"frame"（index 為特徵名之 DataFrame，通用形狀）每欄一值。
    ① 同一小規模請求：凍結機制之記錄（run["record"]）逐特徵逐欄位之值與 NaN 遮罩 sha256、欄位集合、選欄通過集合
       == 測試自原始回應重算之 oracle（帶特徵名、逐值）；第 (1)、(4) 項之選欄通過集合＝第 6 段後之倖存者，oracle 讀同次
       執行寫出之 `data_cache/reports/ic_survivors_<case_id>.json` 之 feature_names（報告頂層無名單，
       ic_filter_orchestrator.py:3390）。
    ② 凍結檔（整格請求）對 oracle 只比表結構、與成員無關、不比逐特徵值：FDR 等跨特徵校正依請求之特徵數
       （momentum/Analysis/ic_filter_orchestrator.py:56 `apply_fdr`），20 欄與整格之逐特徵值、通過與否與 "by_key" 來源之
       成員本可不同。表結構（"rows"／"frame" 之欄）須全成員（oracle 各特徵之表欄位集合恰一種），凍結檔之表欄位集合與之相等，
       oracle 特徵（`small_request` 取凍結請求排序後之前 ORACLE_FEATURES 個）皆在凍結檔，"by_key" 來源：oracle 出現者凍結檔
       皆有。"""
    rec, raw = run["record"], run["raw"]
    expected: Dict[str, Set[str]] = {}
    for ptr in [p for p, k in fb.feature_tables(name).items() if k == "frame"]:
        df = _resolve(raw, ptr)
        assert isinstance(df, pd.DataFrame), f"{name}：{ptr} 非逐特徵表"
        for feat in df.index:
            expected.setdefault(str(feat), set()).update(f"{ptr}/{c}" for c in df.columns)
        for c in df.columns:
            if not pd.api.types.is_numeric_dtype(df[c]):
                continue
            for feat in df.index:
                arr = df.loc[[feat], c].to_numpy()
                got = rec["features"][str(feat)][f"{ptr}/{c}"]
                assert got["sha256"] == hashlib.sha256(arr.tobytes()).hexdigest(), f"{name}/{feat}/{c}：值"
                mask = np.isnan(arr.astype("float64"))
                assert got["nan_mask_sha256"] == hashlib.sha256(mask.tobytes()).hexdigest(), f"{name}/{feat}/{c}：遮罩"
    # "rows"／"by_key"（SPEC §G 摘要粒度）；區域名沿用上段（斷言之名序不變）
    for ptr, shape in fb.feature_tables(name).items():
        if shape == "frame":
            continue
        df = _resolve(raw, ptr)
        if shape == "rows":
            assert isinstance(df, list) and all(isinstance(got, dict) and "feature_name" in got for got in df), \
                f"{name}：{ptr} 非以 feature_name 為鍵之 list[dict]"
            assert len({str(got["feature_name"]) for got in df}) == len(df), f"{name}：{ptr} 之 feature_name 重複"
            for got in df:
                feat = str(got["feature_name"])
                for c, arr in got.items():
                    if c == "feature_name":
                        continue
                    expected.setdefault(feat, set()).add(f"{ptr}/{_ptr(c)}")
                    assert rec["features"][feat][f"{ptr}/{_ptr(c)}"] == _oracle_digest(arr), \
                        f"{name}/{feat}{ptr}/{c}：值或 NaN 遮罩 != 獨立 oracle"
        elif shape == "by_key":
            assert isinstance(df, dict), f"{name}：{ptr} 非以特徵名為鍵之 dict"
            for feat, arr in df.items():
                expected.setdefault(str(feat), set()).add(ptr)
                assert rec["features"][str(feat)][ptr] == _oracle_digest(arr), \
                    f"{name}/{feat}{ptr}：子樹值或 NaN 遮罩 != 獨立 oracle"
        else:
            pytest.fail(f"{name}：{ptr} 之逐特徵來源形狀未知（須 rows／by_key／frame）")
    assert expected, f"{name}：獨立 oracle 未取得任何逐特徵表"
    assert {f: set(v) for f, v in rec["features"].items()} == expected, f"{name}：逐特徵欄位 != 獨立 oracle"
    oracle_schema = {frozenset(x for x in v if _is_table_field(x)) for v in expected.values()}  # 表結構（與成員無關）
    assert len(oracle_schema) == 1, f"{name}：逐特徵表非全成員（成員依請求而變）⇒ 凍結結構無從對照"
    frozen_feats = {f: {x for x in v if _is_table_field(x)} for f, v in frozen_item["features"].items()}
    assert {frozenset(v) for v in frozen_feats.values()} == oracle_schema, f"{name}：凍結檔逐特徵欄位結構 != oracle"
    missing = set(expected) - set(frozen_feats)
    assert not missing, f"{name}：oracle 特徵不在凍結檔：{sorted(missing)[:5]}"
    sel = fb.selected_pointer(name)
    if sel is not None:
        assert sorted(map(str, _resolve(raw, sel))) == sorted(rec["selected"]), f"{name}：選欄通過集合 != oracle"
    # 以下重用上段已綁之區域名（missing、sel），不另綁新名：呼叫者之斷言名序不變（TESTREG V19 normalize ②）。
    # "by_key" 來源之存在（與成員無關）：oracle 出現之來源凍結檔皆有，凍結檔之來源皆屬 SPEC 所列（FEATURE_SOURCES）
    missing = _keyed_sources(expected) - _keyed_sources(frozen_item["features"])
    assert not missing, f"{name}：凍結檔缺逐特徵來源 {sorted(missing)}"
    missing = _keyed_sources(frozen_item["features"]) - set(FEATURE_SOURCES)
    assert not missing, f"{name}：凍結檔含 SPEC 外之逐特徵來源 {sorted(missing)}"
    # SPEC §G：第 (1)、(4) 項之選欄通過集合＝第 6 段後之倖存者（同次執行寫出之 ic_survivors_<case_id>.json；報告頂層無名單）
    if name in SURVIVOR_ITEMS:
        sel = _oracle_survivors(run)  # (寫出差集中之倖存者檔鍵, 恰一份時其 feature_names)
        assert len(sel[0]) == 1, f"{name}：同次執行之寫出差集須恰一個 ic_survivors_<case_id>.json，實得 {sel[0]}"
        assert sorted(sel[1] or []) == sorted(rec["selected"]), f"{name}：選欄通過集合（第 6 段倖存者）!= 獨立 oracle"


def _keyed_sources(features: Mapping[str, Any]) -> Set[str]:
    """逐特徵欄位中屬 "by_key" 來源者（欄位名＝來源 pointer 本身）之聯集。"""
    return {x for fields in features.values() for x in fields if not _is_table_field(x)}


@pytest.fixture(scope="module")
def oracle_runs(fb: Any, tmp_path_factory: pytest.TempPathFactory) -> Dict[str, Dict[str, Any]]:
    """每一輸出項對同一小規模真實請求跑一次凍結機制，同時以獨立 oracle 觀測同一次執行。三根（SPEC §G (b)）：cwd 根＝
    `work/<item>/cwd`、隔離目錄＝`work/<item>/iso`（`freeze_item` 契約）、repo 根；`freeze_item` 之記錄須以 "roots" 回報
    其實際所用之 cwd 根與隔離目錄，且與 oracle 前後兩次走訪之根相同（boundary_01 末斷言）。"fields"＝回應全部欄位扣除逐特徵
    來源之子路徑（SPEC §G 摘要粒度；逐特徵來源由 boundary_02 逐特徵比對）。"""
    golden = _golden()
    out: Dict[str, Dict[str, Any]] = {}
    for item in OUTPUT_ITEMS:
        work = tmp_path_factory.mktemp(f"oracle_{item}")
        # 優先取凍結倖存者（同格他項之 "selected" 亦取：深度分析項之記錄不存倖存者，與同格 IC 頁項同請求設定），
        # 使小規模請求與凍結走同一寫出分支（有倖存者才寫 filtered HDF5）
        cell = golden["items"][item]["request"].get("cell")
        prefer = sorted({n for rec in golden["items"].values() if isinstance(rec, dict)
                         and (rec.get("request") or {}).get("cell") == cell for n in (rec.get("selected") or [])})
        request = fb.small_request(item, golden["items"][item]["request"], ORACLE_FEATURES, prefer=prefer)
        iso = work / item / "iso"
        before = _oracle_walk(_oracle_roots(work / item / "cwd", iso))
        record = fb.freeze_item(item, request=request, repo_root=REPO, work_root=work)
        after = _oracle_walk(_oracle_roots(work / item / "cwd", iso))
        written = {k for k, v in after.items() if before.get(k) != v}
        ignored_seen = written & set(record.get("repo_ignored") or [])  # SPEC v5.45 §G (2) ③：他行程寫入不計
        written -= ignored_seen
        with open(work / item / "response.pkl", "rb") as fh:
            raw = pickle.load(fh)
        out[item] = {"record": record, "raw": raw, "written": written, "ignored_seen": ignored_seen,
                     "fields": _oracle_response_fields(item, raw),
                     "roots": {"cwd": str((work / item / "cwd").resolve()), "iso": str(iso.resolve())}}
    return out


# ── Task 0.1 驗證：凍結檔內容 ──────────────────────────────────────────────────────────────────────────


@pytest.mark.slow
@pytest.mark.requires_kline
def test_boundary_01_frozen_contains_all_g_items(oracle_runs: Dict[str, Dict[str, Any]]) -> None:
    """§G (1)–(5) 五項皆在；(1)(2)(4) 逐特徵逐欄位 sha256 非空；(1)(3)(4)(5) 各含回應全部欄位與快照差集之全部寫出檔；
    獨立 oracle：同一小規模真實請求之回應鍵集合（扣除逐特徵來源之子路徑）與 os.walk 三根（cwd 根、`<iso>`、`<repo>`）前後
    差集 == 凍結機制之記錄，凍結檔之欄位與輸出根結構相同；IC-first 凍結檔含 processed/selected.parquet（V2 artifact，不寫
    HDF5）；記錄回報之根 == oracle 走訪之根。"""
    golden = _golden()
    items = golden["items"]
    missing = [k for k in G_ITEMS if k not in items]
    assert not missing, f"缺凍結項 {missing}"
    for name in FEATURE_ITEMS:
        features = items[name]["features"]
        assert features, f"{name}：無逐特徵輸出"
        for feat, fields in features.items():
            assert fields, f"{name}/{feat}：無欄位"
            for field, digest in fields.items():
                assert HEX64.match(str(digest.get("sha256") or "")), f"{name}/{feat}/{field}：sha256 空或非法"
    for name in OUTPUT_ITEMS:
        response, files = items[name]["response"], items[name]["files"]
        assert response, f"{name}：回應欄位為空"
        assert all(HEX64.match(str(v)) for v in response.values()), f"{name}：回應欄位 sha256 非法"
        assert files, f"{name}：快照差集之寫出檔為空"
        for key, rec in files.items():
            assert HEX64.match(str(rec.get("sha256") or "")), f"{name}/{key}：檔 sha256 空或非法"
    post_ic = items["icfirst_post_ic"]["files"]
    # SPEC v5.8：IC-first 寫 V2 parquet artifact、不寫 HDF5（selected.parquet 之斷言見本函式末）；日後若寫出 .h5，仍須帶
    # 逐物件摘要
    if any(k.endswith((".h5", ".hdf5")) for k in post_ic):
        assert any(rec.get("hdf5") for rec in post_ic.values()), "icfirst_post_ic：無逐群組逐資料集摘要之 HDF5"
    sub = items["stage5_subset"]
    assert sub["seed"] == SEED and sub["n_cols_requested"] == 2000
    assert sub["stage_cols"] == len(sub["features"]) and 0 < sub["stage_cols"] <= 2000
    for name in OUTPUT_ITEMS:
        run, frozen = oracle_runs[name], items[name]
        rec = run["record"]
        assert set(rec["response"]) == run["fields"], (
            f"{name}：回應欄位集合 != 獨立 oracle（少 {sorted(run['fields'] - set(rec['response']))[:5]}，"
            f"多 {sorted(set(rec['response']) - run['fields'])[:5]}）")
        listed = set(rec["files"]) | {t for t in rec["transient"] if t in run["written"]}
        assert listed == run["written"], (
            f"{name}：寫出檔集合 != os.walk 全樹差集（漏 {sorted(run['written'] - listed)[:5]}，"
            f"多 {sorted(listed - run['written'])[:5]}）")
        assert _top_segments(list(frozen["response"])) == _top_segments(list(run["fields"])), \
            f"{name}：凍結檔之回應頂層欄位 != 同請求小規模 oracle"
        assert {_root_of(k, frozen["output_roots"]) for k in frozen["files"]} == \
            {_root_of(k, rec["output_roots"]) for k in run["written"]}, f"{name}：凍結檔之寫出根 != 同請求小規模 oracle"
    # SPEC v5.8 §G (5)：IC-first 之 post-IC 輸出為 V2 parquet artifact（不寫 HDF5），凍結檔須含 processed/selected.parquet
    selected_parquet = sorted(k for k in post_ic if k.split("/")[-2:] == ["processed", "selected.parquet"])
    assert len(selected_parquet) == 1, f"icfirst_post_ic：須恰一個 processed/selected.parquet，實得 {selected_parquet}"
    assert HEX64.match(str(post_ic[selected_parquet[0]].get("sha256") or "")), "icfirst_post_ic：selected.parquet 無 sha256"
    # SPEC §G (b)：freeze_item 之記錄回報所用之 cwd 根與隔離目錄，須與獨立 oracle 前後走訪之根相同（三根前綴之鍵方可比）
    for name in OUTPUT_ITEMS:
        run = oracle_runs[name]
        used = run["record"].get("roots") or {}
        assert {r: str(Path(p).resolve()) for r, p in used.items()} == run["roots"], \
            f"{name}：freeze_item 所用之根 {used} != oracle 走訪之根 {run['roots']}"
        # SPEC v5.45 §G (2) ③：未計入之 `<repo>/` 寫入（他行程）列 repo_ignored——須皆在 data_cache/ 之外、且恰為
        # oracle 全樹差集所見者（oracle_runs 之 "written" 已扣除；"ignored_seen"＝扣除前之交集）
        ignored = set(run["record"].get("repo_ignored") or [])
        assert all(k.startswith("<repo>/") and not k.startswith("<repo>/data_cache/") for k in ignored), \
            f"{name}：repo_ignored 含非 <repo>/ 或 data_cache/ 下之鍵：{sorted(ignored)[:5]}"
        assert ignored == run["ignored_seen"], f"{name}：repo_ignored 有 oracle 全樹差集未見之鍵"


@pytest.mark.slow
@pytest.mark.requires_kline
def test_boundary_02_frozen_baseline_content_complete(fb: Any, oracle_runs: Dict[str, Dict[str, Any]]) -> None:
    """逐特徵逐欄位值 sha256（原生 dtype 位元組）、NaN 遮罩 sha256、選欄通過集合、PIT 標籤序列 sha256 皆在；
    獨立 oracle（同一小規模請求）：自原始回應之逐特徵表重算欄位集合與數值欄之值／NaN 遮罩 sha256、選欄通過集合，
    與記錄相同；凍結檔對 oracle 只比表結構、與成員無關（見 `_check_item_against_oracle`）；選欄通過集合＝第 6 段後之
    倖存者，oracle 讀同次執行寫出之 ic_survivors_<case_id>.json（見 `_check_item_sources_and_survivors`）。第 (3) 項深度分析
    無逐特徵輸出（SPEC v5.8：由回應全部欄位涵蓋，boundary_01）。"""
    items = _golden()["items"]
    for name in SURVIVOR_ITEMS:
        _check_item_against_oracle(fb, name, oracle_runs[name], items[name])
    for name in FEATURE_ITEMS:
        features = items[name]["features"]
        field_sets = {frozenset(x for x in f if _is_table_field(x)) for f in features.values()}  # 表結構（與成員無關）
        assert len(field_sets) == 1, f"{name}：各特徵欄位集合不一致"
        for feat, fields in features.items():
            for field, digest in fields.items():
                assert HEX64.match(str(digest.get("sha256") or "")), f"{name}/{feat}/{field}：值 sha256 缺"
                assert HEX64.match(str(digest.get("nan_mask_sha256") or "")), f"{name}/{feat}/{field}：NaN 遮罩缺"
    for name in ("ic_report", "event_report"):
        selected = items[name]["selected"]
        assert isinstance(selected, list) and all(isinstance(s, str) for s in selected), f"{name}：選欄通過集合缺"
        assert set(selected) <= set(items[name]["features"]), f"{name}：選欄通過集合含未凍結之特徵"
    for name in ("ic_report", "stage5_subset"):
        labels = items[name]["pit_labels"]
        assert labels, f"{name}：PIT 標籤序列缺"
        for feat, rec in labels.items():
            if rec["skipped_all_nan"]:
                assert rec["label_sha256"] is None, f"{name}/{feat}：跳過之欄不得有標籤"
            else:
                assert HEX64.match(str(rec["label_sha256"] or "")), f"{name}/{feat}：PIT 標籤 sha256 缺"
            assert isinstance(rec["q"], int) and isinstance(rec["q_insufficient"], bool)
    assert set(items["stage5_subset"]["pit_labels"]) >= set(items["stage5_subset"]["features"])


@pytest.mark.slow
@pytest.mark.requires_kline
def test_freeze_reproducible(fb: Any) -> None:
    """SPEC v5.24 Task 0.1 具名（r36 群集 A）：同一 2,000 欄子集（同 seed、同碼路徑、同交接 h5 雜湊）重跑第 5 段 ==
    凍結之全部對應欄（stage_cols 相等、特徵集合相等、逐欄位與 PIT 標籤逐一相等）。第 5 段之 FDR 對進段全部欄計算
    （momentum/Analysis/ic_filter_orchestrator.py:4435-4442），故不以較小子集代替。重跑前先驗交接 h5 之內容 sha256
    等於凍結所記（測試自算）。"""
    # 區域名之首次綁定序沿用改版前（frozen、cur、extra、feat、fields、rec；TESTREG V19 normalize 依此改名）
    frozen = _golden()["items"]["stage5_subset"]
    assert _sha256_of_file(_c_handoff_file(frozen)) == frozen["request"]["source_sha256"], "交接 h5 內容 != 凍結所記"
    assert frozen["n_cols_requested"] == 2000
    cur = fb.stage5_subset_digests(2000, seed=SEED, expected_sha256=frozen["request"]["source_sha256"])
    assert 0 < cur["stage_cols"] <= 2000 and cur["stage_cols"] == len(cur["features"])
    assert cur["stage_cols"] == frozen["stage_cols"], "第 5 段實際進段欄數 != 凍結"
    extra = set(cur["features"]) - set(frozen["features"])
    assert not extra, f"500 欄子集非 2,000 欄子集之巢狀子集：{sorted(extra)[:5]}"
    assert set(cur["features"]) == set(frozen["features"]), "凍結有而重跑無之特徵（非同一 2,000 欄子集）"
    for feat, fields in cur["features"].items():
        assert fields == frozen["features"][feat], f"第 5 段輸出不可重現：{feat}"
    assert set(cur["pit_labels"]) == set(frozen["pit_labels"]), "PIT 標籤之特徵集合 != 凍結"
    for feat, rec in cur["pit_labels"].items():
        assert rec == frozen["pit_labels"][feat], f"PIT 標籤不可重現：{feat}"


# ── Task 0.1 邊界（真實資料） ───────────────────────────────────────────────────────────────────────────


@pytest.mark.requires_kline
def test_boundary_03_q_insufficient_labels_nan_as_frozen(fb: Any) -> None:
    """A 格 q 不足之特徵（若存在）：凍結之標籤含 NaN，且 PIT 標籤序列 sha256 等於現行碼對該欄重算之值。
    不依賴 A 格恰有此類特徵；q 不足之語意另由 boundary_21 以真實索引上之明列邊界輸入覆蓋。"""
    labels = _golden()["items"]["ic_report"]["pit_labels"]
    cases = {k: v for k, v in labels.items() if v["q_insufficient"] and not v["skipped_all_nan"]}
    if not cases:
        return
    features, label = fb.load_cell(CELL)
    cur = fb.pit_label_digests(features[sorted(cases)], label)
    for feat, rec in cases.items():
        assert rec["label_nan_count"] > 0, f"{feat}：q 不足之欄標籤應含 NaN"
        assert cur[feat]["q_insufficient"] is True, feat
        assert cur[feat]["label_sha256"] == rec["label_sha256"], f"{feat}：現行碼重算之標籤 != 凍結"
        assert cur[feat]["label_nan_count"] == rec["label_nan_count"], feat


@pytest.mark.requires_kline
def test_boundary_04_all_nan_column_skipped_as_current(fb: Any) -> None:
    """全 NaN 欄於凍結與現行同被跳過；另以真實索引上之全 NaN 欄（明列邊界輸入）驗現行跳過。"""
    labels = _golden()["items"]["ic_report"]["pit_labels"]
    frozen_skipped = {k for k, v in labels.items() if v["skipped_all_nan"]}
    features, label = fb.load_cell(CELL)
    all_nan_now = {c for c in features.columns if bool(features[c].isna().all())}
    assert frozen_skipped == all_nan_now, "凍結之全 NaN 跳過集合 != 現行資料之全 NaN 欄"
    probe = features.iloc[:, :1].copy()
    probe["__icperf_all_nan_boundary__"] = np.nan  # 邊界輸入：真實索引上之全 NaN 欄
    cur = fb.pit_label_digests(probe, label)
    assert cur["__icperf_all_nan_boundary__"]["skipped_all_nan"] is True
    assert cur["__icperf_all_nan_boundary__"]["label_sha256"] is None
    if frozen_skipped:
        again = fb.pit_label_digests(features[sorted(frozen_skipped)], label)
        assert all(again[c]["skipped_all_nan"] for c in frozen_skipped)


def _real_kline_frame(symbol: str = "BTCUSDT", timeframe: str = "1h", rows: int = 500) -> pd.DataFrame:
    import h5py

    assert KLINE_CACHE.is_file(), f"真實 kline 不存在：{KLINE_CACHE}"
    with h5py.File(KLINE_CACHE, "r") as f:
        data = f[f"{symbol}/{timeframe}/data"][-rows:]
    idx = pd.to_datetime(data["timestamp"].astype("int64"), unit="s", utc=True)  # kline_cache 時戳為 epoch 秒
    return pd.DataFrame({"close": data["close"].astype("float64")}, index=idx)


@pytest.mark.requires_kline
def test_boundary_21_q_insufficient_explicit_boundary_on_real_index(fb: Any) -> None:
    """q 不足之語意（秒級）：真實 kline 索引與標籤上，特徵只前 140 列有效（明列邊界輸入：樣本數 140 / 請求 q=5 < 最小組
    大小 30 ⇒ 降為 q=3；前 MIN_SAMPLES 根標籤 NaN）⇒ q_insufficient、q==3、標籤含 NaN，且標籤 sha256 等於現行單調性碼路徑
    之獨立重算。"""
    from momentum.Analysis.monotonicity_tester import MonotonicityTester

    k = _real_kline_frame()
    label = k["close"].pct_change().shift(-1).rename("label")
    feature = k["close"].where(np.arange(len(k)) < 140).rename("f")  # 邊界輸入：真實值、只前 140 列有效
    tester = MonotonicityTester({})
    data = tester._prepare_data(feature, label)
    q = tester._select_num_quantiles(len(data), 5)
    assert q == 3, "邊界輸入未觸發 q 不足（前提失效）"
    bins = tester._assign_quantiles(data, q)
    expected = np.asarray(bins, dtype="float64")
    cur = fb.pit_label_digests(pd.DataFrame({"f": feature}), label, num_quantiles=5)["f"]
    assert cur["q_insufficient"] is True and cur["q"] == 3 and cur["skipped_all_nan"] is False
    assert cur["label_nan_count"] == int(np.isnan(expected).sum()) > 0
    assert cur["label_sha256"] == hashlib.sha256(expected.tobytes()).hexdigest()


# ── §G 寫出捕獲機制之秒級契約測試 ───────────────────────────────────────────────────────────────────────


def test_boundary_05_capture_repo_h5py_write(fb: Any, tmp_path: Path) -> None:
    """repo 內以 h5py 寫入（不經 Python open）之檔進差集，且帶逐物件摘要。"""
    res = _capture(fb, tmp_path, """
        import h5py
        import numpy as np
        with h5py.File("data_cache/features/filtered_features.h5", "w") as f:
            f.create_dataset("g/v", data=np.arange(4, dtype="float64"))
            f["g"].attrs["k"] = 1
    """)
    assert res["rc"] == 0
    rec = res["files"]["data_cache/features/filtered_features.h5"]
    assert HEX64.match(rec["sha256"])
    assert rec["hdf5"]["/g/v"]["kind"] == "dataset" and HEX64.match(rec["hdf5"]["/g/v"]["sha256"])
    assert "k" in rec["hdf5"]["/g"]["attrs"]


def _outside_replace_outcome(fb: Any, tmp_path: Path) -> str:
    """repo 外 tempfile 暫存經 os.replace 落到快照範圍外 ⇒ 結果分類："fail"（FreezeError 且訊息具名目的地）、
    "fail_other"（FreezeError 而未具名目的地）、"collected"（未擋而收集，違反 §G (c)）、"missed"（兩者皆無）。"""
    dest = tmp_path / "elsewhere" / "report.bin"
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = f"""
        import os, tempfile
        fd, tmp = tempfile.mkstemp(suffix=".part")
        os.write(fd, b"abc")
        os.close(fd)
        os.replace(tmp, {str(dest)!r})
    """
    try:
        res = _capture(fb, tmp_path, body, tag="outside")
    except fb.FreezeError as exc:
        return "fail" if str(dest.resolve()) in str(exc) or str(dest) in str(exc) else "fail_other"
    return "collected" if _key(dest, tmp_path / "repo") in res["files"] else "missed"


def _boundary_06_holds(fb: Any, tmp_path: Path) -> bool:
    """repo 內目的地：os.replace 目的地入審計記錄且進集合；快照範圍外目的地：只准觸發 (c) FreezeError 且訊息具名該目的地
    （收集即違反 fail-closed，SPEC §G (c)）。"""
    repo = _repo(tmp_path)
    dest = repo / "data_cache" / "reports" / "summary.bin"
    res = _capture(fb, tmp_path, f"""
        import os, tempfile
        fd, tmp = tempfile.mkstemp(suffix=".part")
        os.write(fd, b"abc")
        os.close(fd)
        os.replace(tmp, {str(dest)!r})
    """, tag="inside")
    inside_ok = (res["rc"] == 0 and str(dest.resolve()) in _logged_paths(res)
                 and any(e["event"] == "os.replace" for e in res["write_log"])
                 and "data_cache/reports/summary.bin" in res["files"])
    return inside_ok and _outside_replace_outcome(fb, tmp_path) == "fail"


def test_boundary_06_capture_outside_tempfile_replace(fb: Any, tmp_path: Path) -> None:
    """repo 外 tempfile 暫存經 os.replace：落 repo 內 ⇒ 目的地入審計記錄且進集合；落快照範圍外 ⇒ 凍結 FAIL（fail-closed）。"""
    assert _boundary_06_holds(fb, tmp_path)
    assert _outside_replace_outcome(fb, tmp_path / "again") == "fail"


def test_boundary_07_capture_subprocess_writes(fb: Any, tmp_path: Path) -> None:
    """子行程（經共用監看啟動）與其孫行程之寫入／附加／建立模式開檔皆進同一記錄；唯讀開檔不記。"""
    repo = _repo(tmp_path)
    (repo / "data_cache" / "existing.txt").write_text("r", encoding="utf-8")
    f1, f2, f3 = (repo / "data_cache" / n for n in ("w.txt", "a.txt", "x.txt"))
    grand = (f"open({str(f2)!r}, 'a').write('a'); open({str(f3)!r}, 'x').write('x'); "
             f"open({str(repo / 'data_cache' / 'existing.txt')!r}).read()")
    res = _capture(fb, tmp_path, f"""
        import subprocess, sys
        open({str(f1)!r}, "w").write("w")
        subprocess.run([sys.executable, "-c", {grand!r}], check=True)
    """)
    assert res["rc"] == 0
    logged = _logged_paths(res)
    for f in (f1, f2, f3):
        assert str(f.resolve()) in logged, f"未記錄 {f}"
    assert str((repo / "data_cache" / "existing.txt").resolve()) not in logged, "唯讀開檔不得記錄"
    pid_of = {str(Path(e["path"]).resolve()): e["pid"] for e in res["write_log"]}
    assert pid_of[str(f1.resolve())] != pid_of[str(f2.resolve())], "孫行程之寫入須來自另一行程（經 sitecustomize 注入）"
    for f in (f1, f2, f3):
        assert _key(f, repo) in res["files"]


def test_boundary_08_tmpdir_home_isolated_and_snapshotted(fb: Any, tmp_path: Path) -> None:
    """TMPDIR、HOME 指向隔離目錄（其餘環境不變），且隔離目錄納入快照（寫入者進集合）。"""
    iso = tmp_path / "iso_env"
    env = fb.isolated_env({"HOME": "/nonexistent-home", "TMPDIR": "/nonexistent-tmp", "PATH": "/usr/bin"}, iso)
    home, tmpdir = Path(env["HOME"]).resolve(), Path(env["TMPDIR"]).resolve()
    assert home != tmpdir
    for p in (home, tmpdir):
        assert p.is_dir() and p.is_relative_to(iso.resolve()), f"{p} 不在隔離目錄 {iso} 之下"
    assert env["PATH"] == "/usr/bin"
    res = _capture(fb, tmp_path, """
        import os, tempfile
        from pathlib import Path
        h = Path(os.environ["HOME"]) / ".cache" / "h.bin"
        h.parent.mkdir(parents=True, exist_ok=True)
        h.write_bytes(b"h")
        (Path(tempfile.gettempdir()) / "t.bin").write_bytes(b"t")
        print(os.environ["HOME"], tempfile.gettempdir())
    """, tag="iso")
    assert res["rc"] == 0
    iso_root = (tmp_path / "iso_iso").resolve()
    written = [k for k in res["files"] if k.startswith(str(iso_root)) or k.startswith("<iso>/")]
    assert any(k.endswith("/.cache/h.bin") for k in written), f"HOME 寫入未進集合：{sorted(res['files'])}"
    assert any(k.endswith("/t.bin") for k in written), f"TMPDIR 寫入未進集合：{sorted(res['files'])}"
    # SPEC §G (b)：隔離目錄之寫出以 `<iso>/` 前綴記，跨次執行可比；不得以絕對路徑記
    assert all(k.startswith("<iso>/") for k in written), f"隔離目錄寫出須以 <iso>/ 前綴記：{sorted(written)}"


def test_boundary_09_output_root_outside_snapshot_fails(fb: Any, tmp_path: Path) -> None:
    """請求設定解析出之輸出根落快照範圍外 ⇒ FAIL；範圍內 ⇒ 放行；實際各路徑預設請求之輸出根皆落於所給之 cwd 根內
    （`resolve_output_roots` 之 `repo_root`＝本次執行之 cwd 根，`scripts/icperf_freeze_baseline.py:739-741`）：①參數預設值
    （`repo_root=REPO`，非隔離執行之 cwd 即 repo 根）⇒ 落 repo 內；②與 `freeze_item` 同語意之隔離 cwd 根
    `work_root/<item>/cwd`（唯讀輸入自 repo 以 symlink 引入）⇒ 解析後落該 cwd 根內（相對根相對 cwd 根解析；落入唯讀輸入
    symlink 者解析後出 cwd 根即紅）。r30 CODEX-R30-P1-01／COMPOSER-R30-P1-01。"""
    outside = tmp_path / "elsewhere_root"
    outside.mkdir()
    with pytest.raises(fb.FreezeError) as exc:
        _capture(fb, tmp_path, "pass\n", output_roots=[outside], tag="outroot")
    assert str(outside.resolve()) in str(exc.value) or str(outside) in str(exc.value)
    ok = _capture(fb, tmp_path, "pass\n", output_roots=[tmp_path / "repo" / "data_cache"], tag="inroot")
    assert ok["rc"] == 0
    for item in [i for i in OUTPUT_ITEMS if i not in PENDING_ITEMS]:  # 待定項見 test_pending_items_fail_closed
        roots = fb.resolve_output_roots(item, fb.default_request(item, CELL))  # 參數預設 repo_root=REPO
        assert roots, f"{item}：未解析出任何輸出根"
        for r in roots:
            assert str(Path(r).resolve()).startswith(str(REPO.resolve()) + "/"), f"{item}：輸出根 {r} 在 repo 外"
    for item in [i for i in OUTPUT_ITEMS if i not in PENDING_ITEMS]:
        cwd_root = _isolated_cwd_root(tmp_path / "work", item)
        cwd_roots = fb.resolve_output_roots(item, fb.default_request(item, CELL), cwd_root)
        assert cwd_roots, f"{item}：隔離 cwd 根下未解析出任何輸出根"
        for cr in cwd_roots:
            resolved = (cwd_root / cr).resolve()
            assert resolved == cwd_root.resolve() or cwd_root.resolve() in resolved.parents, \
                f"{item}：輸出根 {cr}（解析為 {resolved}）不在隔離 cwd 根 {cwd_root} 內"


def test_boundary_10_write_then_delete_recorded_not_compared(fb: Any, tmp_path: Path) -> None:
    """寫後刪除之暫存檔記入收據（transient）、不入比對集合；保留之檔照常進集合。"""
    res = _capture(fb, tmp_path, """
        import os
        open("data_cache/scratch.tmp", "w").write("x")
        os.remove("data_cache/scratch.tmp")
        open("data_cache/reports/kept.json", "w").write("{}")
    """)
    assert res["rc"] == 0
    assert "data_cache/scratch.tmp" in res["transient"]
    assert "data_cache/scratch.tmp" not in res["files"]
    assert "data_cache/reports/kept.json" in res["files"]
    assert "data_cache/reports/kept.json" not in res["transient"]


def test_boundary_22_same_content_overwrite_recorded_not_compared(fb: Any, tmp_path: Path) -> None:
    """既有檔以相同位元組覆寫（SPEC §G (c)「(a) 有而差集無變化者」）：審計記到該路徑與寫入模式、記入 transient、
    不入比對集合；同一行程改寫內容之既有檔照常進集合（r11 CODEX-R11-P2-06）。"""
    repo = _repo(tmp_path)
    (repo / "data_cache" / "reports" / "same.json").write_text('{"a": 1}', encoding="utf-8")
    (repo / "data_cache" / "reports" / "diff.json").write_text('{"a": 1}', encoding="utf-8")
    res = _capture(fb, tmp_path, """
        open("data_cache/reports/same.json", "w").write('{"a": 1}')
        open("data_cache/reports/diff.json", "w").write('{"a": 2}')
    """, tag="overwrite")
    assert res["rc"] == 0
    same = str((repo / "data_cache" / "reports" / "same.json").resolve())
    assert any(str(Path(e["path"]).resolve()) == same and "w" in str(e["mode"]) for e in res["write_log"]), \
        "同內容覆寫未記入寫入審計"
    assert "data_cache/reports/same.json" in res["transient"]
    assert "data_cache/reports/same.json" not in res["files"]
    assert "data_cache/reports/diff.json" in res["files"]
    assert "data_cache/reports/diff.json" not in res["transient"]


def test_boundary_11_snapshot_exclusions_exact(fb: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """快照排除集恰為 .git、venv、__pycache__、numba 快取（副檔名與 NUMBA_CACHE_DIR 所指目錄整棵）、測試選取工具狀態目錄
    （相似名之對照組不排除；NUMBA_CACHE_DIR 未設時同一目錄不排除＝改壞對照）。"""
    monkeypatch.delenv("NUMBA_CACHE_DIR", raising=False)
    repo = tmp_path / "snaprepo"
    excluded = [".git/HEAD", "venv/bin/python", "pkg/__pycache__/m.cpython-39.pyc", "pkg/__pycache__/f.k-1.py39.nbi",
                "pkg/cache/f.k-1.py39.1.nbc", ".testsel/receipts/r.json", "sub/.git/config", "sub/venv/x"]
    kept = ["venvx/a.txt", "git/b.txt", ".gitignore", "pkg/m.py", ".testsel_note.txt", "pkg/data.h5",
            "pkg/pycache/c.txt", "pkg/nbi.txt"]
    for rel in excluded + kept:
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(rel.encode("utf-8"))
    snap = fb.snapshot_files([repo], repo_root=repo)
    assert set(snap) == set(kept), f"多：{sorted(set(snap) - set(kept))}；少：{sorted(set(kept) - set(snap))}"
    assert all(HEX64.match(v) for v in snap.values())
    # NUMBA_CACHE_DIR 所指目錄整棵排除（一般副檔名之檔亦然）；相似名之兄弟目錄不排除
    numba_files = ["nbcache/sub/cache.dat", "nbcache/index.json"]
    sibling = ["nbcache_other/cache.dat"]
    for rel in numba_files + sibling:
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(rel.encode("utf-8"))
    unset = fb.snapshot_files([repo], repo_root=repo)
    assert set(unset) == set(kept) | set(numba_files) | set(sibling), "NUMBA_CACHE_DIR 未設時該目錄不得被排除（改壞對照）"
    monkeypatch.setenv("NUMBA_CACHE_DIR", str(repo / "nbcache"))
    with_env = fb.snapshot_files([repo], repo_root=repo)
    assert set(with_env) == set(kept) | set(sibling), \
        f"NUMBA_CACHE_DIR 整棵未排除：{sorted(set(with_env) & set(numba_files))}"


def _write_h5(path: Path, attr: int) -> None:
    import h5py

    with h5py.File(path, "w") as f:
        f.create_dataset("g/v", data=np.arange(3, dtype="float64"))
        f["g"].attrs["k"] = attr


def _boundary_12_holds(fb: Any, tmp_path: Path) -> bool:
    """改後差集多一檔或少一檔 ⇒ FAIL；同檔 sha256 不等 ⇒ FAIL；HDF5 逐資料集逐屬性比；全同 ⇒ 無問題。"""
    d = tmp_path / "cmp"
    d.mkdir(parents=True, exist_ok=True)
    (d / "a.bin").write_bytes(b"a")
    (d / "a2.bin").write_bytes(b"A")
    (d / "c.bin").write_bytes(b"c")
    _write_h5(d / "b.h5", 1)
    _write_h5(d / "b_attr.h5", 2)
    a, a2, c = (fb.describe_file(d / n) for n in ("a.bin", "a2.bin", "c.bin"))
    b, b_attr = fb.describe_file(d / "b.h5"), fb.describe_file(d / "b_attr.h5")
    frozen = {"response": {}, "files": {"a.bin": a, "b.h5": b}}

    def problems(files: Dict[str, Any]) -> List[str]:
        return fb.compare_capture(frozen, {"response": {}, "files": files})

    same = problems({"a.bin": a, "b.h5": b})
    extra = problems({"a.bin": a, "b.h5": b, "c.bin": c})
    missing = problems({"a.bin": a})
    changed = problems({"a.bin": a2, "b.h5": b})
    attr = problems({"a.bin": a, "b.h5": b_attr})
    return (same == [] and any("c.bin" in p for p in extra) and any("b.h5" in p for p in missing)
            and any("a.bin" in p for p in changed) and any("b.h5" in p and "k" in p for p in attr))


def test_boundary_12_compare_file_set_and_hashes(fb: Any, tmp_path: Path) -> None:
    """改後差集多一檔或少一檔 ⇒ FAIL；同檔 sha256 不等 ⇒ FAIL；HDF5 逐資料集逐屬性比。"""
    assert _boundary_12_holds(fb, tmp_path)


def test_boundary_13_volatile_fields_only_listed_paths_excluded(fb: Any, tmp_path: Path) -> None:
    """每次必異欄位只對所列路徑排除；未列欄位不等 ⇒ FAIL（檔內 JSON 欄位與回應欄位皆然）。"""
    d = tmp_path / "vol"
    d.mkdir()
    (d / "f.json").write_text(json.dumps({"run_id": "r1", "generated_at": "t1", "ic": 0.5}), encoding="utf-8")
    (d / "c.json").write_text(json.dumps({"run_id": "r2", "generated_at": "t2", "ic": 0.5}), encoding="utf-8")
    frozen = {"response": fb.flatten_fields({"meta": {"run_id": "x"}, "summary": [1, 2]}),
              "files": {"r.json": fb.describe_file(d / "f.json")}}
    current = {"response": fb.flatten_fields({"meta": {"run_id": "y"}, "summary": [1, 2]}),
               "files": {"r.json": fb.describe_file(d / "c.json")}}
    only_run_id = fb.compare_capture(frozen, current, volatile=["file:r.json#/run_id", "response:/meta/run_id"])
    assert only_run_id, "未列之 generated_at 不等須列為問題"
    assert any("generated_at" in p for p in only_run_id)
    assert not any("run_id" in p for p in only_run_id)
    both = fb.compare_capture(frozen, current, volatile=["file:r.json#/run_id", "file:r.json#/generated_at",
                                                         "response:/meta/run_id"])
    assert both == []
    unlisted_response = fb.compare_capture(frozen, current, volatile=["file:r.json#/run_id",
                                                                      "file:r.json#/generated_at"])
    assert any("run_id" in p for p in unlisted_response), "回應欄位未列即須比"


def test_boundary_13_hdf5_volatile_attrs_only_listed_excluded(fb: Any, tmp_path: Path) -> None:
    """boundary_13 之 HDF5 正反例（SPEC v5.24 §G；r36 群集 B）：HDF5 檔以「物件＋屬性名」列 volatile
    （file:<path_key>@<物件>#attr:<屬性名>）——該檔改比全部物件之 kind／dtype／shape／資料 sha256 與未列屬性、只跳過所列
    屬性、不比整檔位元組。邊界輸入：tmp_path 以 h5py 秒級建之小檔。另驗格式不合與同檔混列 JSON／HDF5 ⇒ FreezeError。"""
    assert _boundary_13_hdf5_holds(fb, tmp_path)
    with pytest.raises(fb.FreezeError):
        fb.compare_capture({"response": {}, "files": {}}, {"response": {}, "files": {}},
                           volatile=["file:f.h5@g#attr:k"])  # 物件須以 / 起首 ⇒ 不合任一格式
    with pytest.raises(fb.FreezeError):
        fb.compare_capture({"response": {}, "files": {}}, {"response": {}, "files": {}},
                           volatile=["file:f.h5#/a", "file:f.h5@/g#attr:k"])
    with pytest.raises(fb.FreezeError):
        fb.compare_golden({"volatile": ["ic_report:file:f.h5@g#attr:k"], "items": {}}, {"items": {}})


def _write_volatile_h5(path: Path, *, stamp: str, k: int = 1, data: Optional[np.ndarray] = None) -> None:
    import h5py

    with h5py.File(path, "w") as f:
        f.create_dataset("g/v", data=np.arange(3, dtype="float64") if data is None else data)
        f["g"].attrs["source_generated_at"] = stamp
        f["g"].attrs["k"] = k
        f.attrs["source_generated_at"] = stamp


def _boundary_13_hdf5_holds(fb: Any, d: Path) -> bool:
    """只改所列屬性 ⇒ 無問題（未列 volatile 時同一對須列問題＝改壞對照）；改未列屬性或資料集內容 ⇒ 列問題（點名該屬性或
    資料集）；所列物件不同（屬性同名但物件未列）仍比。"""
    _write_volatile_h5(d / "base.h5", stamp="t1")
    _write_volatile_h5(d / "stamp.h5", stamp="t2")
    _write_volatile_h5(d / "unlisted.h5", stamp="t2", k=2)
    _write_volatile_h5(d / "data.h5", stamp="t2", data=np.array([0.0, 1.0, 5.0]))
    base = {"response": {}, "files": {"f.h5": fb.describe_file(d / "base.h5")}}

    def problems(name: str, volatile: Sequence[str]) -> List[str]:
        return fb.compare_capture(base, {"response": {}, "files": {"f.h5": fb.describe_file(d / name)}},
                                  volatile=list(volatile))

    listed = ["file:f.h5@/g#attr:source_generated_at", "file:f.h5@/#attr:source_generated_at"]
    only_stamp = problems("stamp.h5", listed)
    unlisted_stamp = problems("stamp.h5", [])
    group_only = problems("stamp.h5", listed[:1])
    unlisted_attr = problems("unlisted.h5", listed)
    data_changed = problems("data.h5", listed)
    return (only_stamp == [] and bool(unlisted_stamp)
            and any("source_generated_at" in p and "物件 / " in p for p in group_only)
            and any("屬性 k" in p for p in unlisted_attr) and not any("source_generated_at" in p for p in unlisted_attr)
            and any("/g/v" in p and "sha256" in p for p in data_changed))


# ── §G (2) C 格交接 h5 身分之秒級契約（SPEC v5.24；r36 群集 D） ────────────────────────────────────────────


def _small_handoff(root: Path, payload: bytes = b"0123456789") -> Path:
    """邊界輸入：tmp_path 下之小交接檔與其同名 meta（prep.py 同名規則 `<stem>_meta.json`；不涉資料值）。"""
    h5 = root / "X_1h_abc.h5"
    h5.write_bytes(payload)
    (root / "X_1h_abc_meta.json").write_text("{}", encoding="utf-8")
    return h5


def test_c_handoff_env_override_and_identity(fb: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """環境變數 ICPERF_C_HANDOFF_H5 覆寫交接 h5 路徑；身分＝路徑、同名 meta、大小與內容 sha256（測試自算）；未設 ⇒ 本機現值。"""
    h5 = _small_handoff(tmp_path)
    monkeypatch.setenv(C_HANDOFF_ENV, str(h5))
    monkeypatch.setattr(fb, "C_HANDOFF_BYTES", 10)
    assert fb.c_handoff_path() == h5
    ident = fb.c_handoff_identity()
    assert Path(ident["path"]) == h5 and Path(ident["meta"]) == tmp_path / "X_1h_abc_meta.json"
    assert ident["size"] == 10 and ident["sha256"] == hashlib.sha256(b"0123456789").hexdigest()
    assert fb.default_request("stage5_subset")["source_h5"] == str(h5)
    monkeypatch.delenv(C_HANDOFF_ENV)
    assert fb.c_handoff_path() == Path(fb.C_HANDOFF_H5)


def test_c_handoff_missing_fails(fb: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """交接 h5 或其同名 meta 不存在 ⇒ FreezeError（訊息具名該檔）；`stage5_subset_digests` 於啟動子行程前即擋。"""
    missing = tmp_path / "nope.h5"
    monkeypatch.setenv(C_HANDOFF_ENV, str(missing))
    with pytest.raises(fb.FreezeError) as exc:
        fb.c_handoff_identity()
    assert str(missing) in str(exc.value)
    with pytest.raises(fb.FreezeError):
        fb.stage5_subset_digests(5, seed=SEED)
    only = tmp_path / "only.h5"
    only.write_bytes(b"x")
    monkeypatch.setenv(C_HANDOFF_ENV, str(only))
    monkeypatch.setattr(fb, "C_HANDOFF_BYTES", 1)
    with pytest.raises(fb.FreezeError) as exc_meta:
        fb.c_handoff_identity()
    assert "only_meta.json" in str(exc_meta.value)


def test_c_handoff_size_mismatch_fails(fb: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """交接 h5 大小 != 登記大小 ⇒ FreezeError（訊息具名實際大小與路徑）；大小相符 ⇒ 放行（改壞對照）。"""
    h5 = _small_handoff(tmp_path)
    monkeypatch.setenv(C_HANDOFF_ENV, str(h5))
    monkeypatch.setattr(fb, "C_HANDOFF_BYTES", 11)
    with pytest.raises(fb.FreezeError) as exc:
        fb.c_handoff_identity()
    assert "10" in str(exc.value) and str(h5) in str(exc.value)
    with pytest.raises(fb.FreezeError):
        fb.stage5_subset_digests(5, seed=SEED)
    monkeypatch.setattr(fb, "C_HANDOFF_BYTES", 10)
    assert fb.c_handoff_identity()["size"] == 10


def test_c_handoff_sha_mismatch_fails_before_run(fb: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """內容 sha256 != 凍結所記 ⇒ `stage5_subset_digests` 於啟動子行程前 FreezeError；`repro` 於凍結未記
    source_sha256、子集欄數 != 凍結、或雜湊不等時皆 FreezeError（不重跑）。"""
    h5 = _small_handoff(tmp_path)
    monkeypatch.setenv(C_HANDOFF_ENV, str(h5))
    monkeypatch.setattr(fb, "C_HANDOFF_BYTES", 10)
    with pytest.raises(fb.FreezeError) as exc:
        fb.stage5_subset_digests(5, seed=SEED, expected_sha256="0" * 64)
    assert "sha256" in str(exc.value)
    golden = tmp_path / "golden.json"
    for stage5, n_cols in (({"n_cols_requested": 2000, "seed": SEED, "request": {}}, 2000),
                           ({"n_cols_requested": 2000, "seed": SEED, "request": {"source_sha256": "0" * 64}}, 500),
                           ({"n_cols_requested": 2000, "seed": SEED, "request": {"source_sha256": "0" * 64}}, 2000)):
        golden.write_text(json.dumps({"items": {"stage5_subset": stage5}}), encoding="utf-8")
        with pytest.raises(fb.FreezeError):
            fb.repro(n_cols, golden_path=golden)
    assert fb.REPRO_COLS == fb.SUBSET_COLS == 2000


def test_c_handoff_identity_failures_never_start_child(fb: Any, tmp_path: Path,
                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    """r37 CODEX-R37-P1-02：交接 h5 不存在、大小不符、內容 sha256 不符三類 ⇒ `stage5_subset_digests` 於啟動子行程
    **之前** FreezeError（`_run_child` 換成一被呼叫即記錄之替身，三類皆須零次呼叫）；身分相符 ⇒ 確實進到子行程（改壞
    對照：替身被呼叫一次）。"""
    calls: List[Dict[str, Any]] = []

    class _Started(Exception):
        pass

    def spy(spec: Dict[str, Any], **_kw: Any) -> Dict[str, Any]:
        calls.append(spec)
        raise _Started()

    monkeypatch.setattr(fb, "_run_child", spy)
    h5 = _small_handoff(tmp_path)
    good_sha = hashlib.sha256(b"0123456789").hexdigest()
    monkeypatch.setattr(fb, "C_HANDOFF_BYTES", 10)
    cases = ((tmp_path / "nope.h5", 10, None), (h5, 11, None), (h5, 10, "0" * 64))
    for path, size, sha in cases:
        monkeypatch.setenv(C_HANDOFF_ENV, str(path))
        monkeypatch.setattr(fb, "C_HANDOFF_BYTES", size)
        with pytest.raises(fb.FreezeError):
            fb.stage5_subset_digests(5, seed=SEED, expected_sha256=sha)
    assert calls == []
    monkeypatch.setattr(fb, "C_HANDOFF_BYTES", 10)
    with pytest.raises(_Started):
        fb.stage5_subset_digests(5, seed=SEED, expected_sha256=good_sha)
    assert len(calls) == 1 and calls[0]["source_h5"] == str(h5)


def test_c_handoff_relative_path_absolute_and_repro_uses_frozen_path(fb: Any, tmp_path: Path,
                                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    """r37 CODEX-R37-P1-01：相對路徑之 `ICPERF_C_HANDOFF_H5` 解析為呼叫端 cwd 下之絕對路徑（子行程於隔離 cwd 仍指向同檔）；
    環境變數未設時 `repro` 取凍結所記之 `request.source_h5`（非預設本機路徑）傳給子行程。"""
    calls: List[Dict[str, Any]] = []

    class _Started(Exception):
        pass

    def spy(spec: Dict[str, Any], **_kw: Any) -> Dict[str, Any]:
        calls.append(spec)
        raise _Started()

    monkeypatch.setattr(fb, "_run_child", spy)
    monkeypatch.setattr(fb, "C_HANDOFF_BYTES", 10)
    pre: List[Mapping[str, Any]] = []  # 開跑前檢查另有專測（test_preflight_*）；此處只驗其收到凍結所記之請求
    monkeypatch.setattr(fb, "preflight", lambda requests, **kw: pre.append(requests))
    h5 = _small_handoff(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(C_HANDOFF_ENV, h5.name)
    assert fb.c_handoff_path().is_absolute() and fb.c_handoff_path() == Path(os.path.abspath(h5))
    monkeypatch.delenv(C_HANDOFF_ENV)
    golden = tmp_path / "golden.json"
    golden.write_text(json.dumps({"items": {"stage5_subset": {
        "n_cols_requested": 2000, "seed": SEED,
        "request": {"source_h5": str(h5), "source_sha256": hashlib.sha256(b"0123456789").hexdigest()}}}}),
        encoding="utf-8")
    with pytest.raises(_Started):
        fb.repro(2000, golden_path=golden)
    assert len(calls) == 1 and calls[0]["source_h5"] == str(Path(os.path.abspath(h5)))
    assert len(pre) == 1 and pre[0]["stage5_subset"]["source_h5"] == str(h5)


def _mini_handoff(tmp_path: Path, meta_extra: Mapping[str, Any], drop: Sequence[str] = ()) -> Tuple[Path, Path]:
    """交接 h5 之最小形（舊格式：features／timestamps／feature_names）與同名 meta；逐特徵鍵＝欄名（減 drop）。"""
    import h5py

    names = ["f0", "f1", "f2"]
    h5 = tmp_path / "X_1h_abc.h5"
    with h5py.File(h5, "w") as f:
        g = f.create_group("X/1h")
        g.create_dataset("features", data=np.arange(12, dtype=np.float32).reshape(4, 3), chunks=(4, 1))
        g.create_dataset("timestamps", data=np.arange(4, dtype=np.int64))
        g.create_dataset("feature_names", data=np.array(names, dtype=object), dtype=h5py.string_dtype(encoding="utf-8"))
    meta = {"symbol": "X", "timeframe": "1h", "config_hash": "abc", "ff_run_identity": {"run": 1}, **meta_extra}
    meta.update({n: {"category": "trend"} for n in names if n not in drop})
    path = tmp_path / "X_1h_abc_meta.json"
    path.write_text(json.dumps(meta), encoding="utf-8")
    return h5, path


def test_stage5_subset_meta_keys(fb: Any, tmp_path: Path) -> None:
    """子集 meta：照抄非逐特徵鍵（含 ICPERF Task 0.4 ㉜ 之 `feature_metadata_version`）與所選欄；
    交接 meta 缺特徵或有未知非特徵鍵 ⇒ FreezeError（不以鍵數假設判定）。"""
    h5, meta = _mini_handoff(tmp_path, {"feature_metadata_version": 2})
    _out_h5, out_meta = fb._write_stage5_subset(h5, meta, 2, SEED, tmp_path / "out")
    got = json.loads(out_meta.read_text(encoding="utf-8"))
    assert got["feature_metadata_version"] == 2 and got["ff_run_identity"] == {"run": 1}
    assert len([k for k in got if k.startswith("f") and k not in fb.HANDOFF_META_KEYS]) == 2
    for extra, drop in (({"feature_metadata_version": 2, "bogus": 1}, ()), ({}, ("f1",))):
        d = tmp_path / f"bad_{len(extra)}_{len(drop)}"
        d.mkdir()
        h5b, metab = _mini_handoff(d, extra, drop)
        with pytest.raises(fb.FreezeError, match="交接 meta 與欄名不符"):
            fb._write_stage5_subset(h5b, metab, 2, SEED, d / "out")


def test_preflight_rejects_system_temp_and_default_work_root_persistent(fb: Any, tmp_path: Path) -> None:
    """系統暫存（macOS dirhelper 每日清除逾 3 日之檔）：`in_system_temp` 對 pytest 暫存目錄（`tempfile.gettempdir()` 之下）
    與 /tmp 為真、對 repo 之 data_cache 為假；`new_work_root` 建於 `<repo_root>/RUNS_ROOT` 下；`preflight` 對工作根或
    交接 h5 在系統暫存者 FreezeError（未放寬：pytest 暫存目錄即系統暫存）。"""
    import tempfile

    assert fb.in_system_temp(tmp_path) and fb.in_system_temp(tempfile.gettempdir()) and fb.in_system_temp("/tmp")
    assert not fb.in_system_temp(fb.REPO / "data_cache")
    w = fb.new_work_root("icperf-test-", tmp_path)
    assert w.is_dir() and w.parent == tmp_path / fb.RUNS_ROOT and w.name.startswith("icperf-test-")
    h5, _meta = _mini_handoff(tmp_path, {"feature_metadata_version": 2})
    req = {"kind": "stage5", "item": "stage5_subset", "source_h5": str(h5)}
    with pytest.raises(fb.FreezeError, match="系統暫存") as exc:
        fb.preflight({"stage5_subset": req}, work_root=tmp_path / "w")
    assert "工作根在系統暫存" in str(exc.value)


def test_preflight_checks_all_inputs_before_any_run(fb: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`preflight` 逐項驗輸入並彙總全部問題於一次 FreezeError：交接 meta 與 h5 欄名不符（缺特徵／未知鍵）、內容 sha256 != 所記、
    IC 頁 run 之 manifest 不存在、事件匯入批查無、請求種類未知；全部合格 ⇒ 回逐項摘要。`freeze`／`volatile_probe` 之
    preflight 不過 ⇒ 不呼叫任何 `freeze_item`（替身被呼叫即 FAIL）。系統暫存判定另有專測，此處置換為恆假以驗其餘檢查。"""
    monkeypatch.setattr(fb, "in_system_temp", lambda p: False)
    h5, _meta = _mini_handoff(tmp_path, {"feature_metadata_version": 2})
    monkeypatch.setattr(fb, "C_HANDOFF_BYTES", h5.stat().st_size)
    sha = hashlib.sha256(h5.read_bytes()).hexdigest()
    ok = fb.preflight({"stage5_subset": {"kind": "stage5", "source_h5": str(h5)}}, expected_c_sha256=sha)
    assert ok["items"]["stage5_subset"] == {"source_h5": str(h5), "size": h5.stat().st_size, "sha256": sha}
    with pytest.raises(fb.FreezeError, match="sha256"):
        fb.preflight({"stage5_subset": {"kind": "stage5", "source_h5": str(h5)}}, expected_c_sha256="0" * 64)
    for extra, drop in (({"bogus": 1}, ()), ({}, ("f1",))):
        d = tmp_path / f"bad_{len(extra)}_{len(drop)}"
        d.mkdir()
        hb, _ = _mini_handoff(d, extra, drop)
        with pytest.raises(fb.FreezeError, match="交接 meta 與欄名不符"):
            fb.preflight({"stage5_subset": {"kind": "stage5", "source_h5": str(hb)}})
    bad = {"a": {"kind": "ic_page", "run_dir": "no/such/run"},
           "b": {"kind": "ic_page", "run_dir": fb.default_request("ic_report")["run_dir"],
                 "event_import_id": "no-such-import"},
           "c": {"kind": "bogus"}}
    with pytest.raises(fb.FreezeError) as exc:
        fb.preflight(bad)
    msg = str(exc.value)
    assert "a：run 之 feature_manifest.json 不存在" in msg and "b：事件匯入批 no-such-import" in msg and "c：請求種類" in msg

    def must_not_run(*a: Any, **k: Any) -> None:
        pytest.fail("開跑前檢查未過時不得啟動任何執行")

    monkeypatch.setattr(fb, "freeze_item", must_not_run)
    monkeypatch.setenv(C_HANDOFF_ENV, str(tmp_path / "missing.h5"))
    with pytest.raises(fb.FreezeError, match="開跑前檢查未過"):
        fb.freeze(tmp_path / "g.json.gz", work_root=tmp_path / "w")
    golden = {"items": {i: {"request": {"kind": "ic_page", "run_dir": "no/such/run"}} for i in OUTPUT_ITEMS}}
    path = tmp_path / "g2.json.gz"
    fb.write_golden(golden, path)
    with pytest.raises(fb.FreezeError, match="開跑前檢查未過"):
        fb.volatile_probe(golden_path=path, work_root=tmp_path / "w2")
    assert not (tmp_path / "w").exists() and not (tmp_path / "w2").exists()


# ── §G 凍結檔 gzip 存檔與 volatile 實測判定之秒級契約（SPEC v5.25） ─────────────────────────────────────────


def _canon_golden_bytes(obj: Any) -> bytes:
    """凍結檔內容之正準 JSON 位元組（測試自寫：sort_keys、緊湊分隔、allow_nan、UTF-8）。"""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=True).encode("utf-8")


def test_golden_gzip_deterministic_roundtrip(fb: Any, tmp_path: Path) -> None:
    """`.gz` 路徑：內容＝正準 JSON 位元組之 gzip（檔頭 mtime 0），同內容兩次寫出位元組相同、內容一改即異；
    `load_golden` 依檔頭魔數解壓（非 .gz 路徑原樣寫出，同函式可讀）。邊界輸入：含 NaN 與非 ASCII 之小物件。"""
    import gzip

    g = {"b": [1.5, float("nan")], "a": {"x": "中"}}
    p1, p2, p3, plain = tmp_path / "1.json.gz", tmp_path / "2.json.gz", tmp_path / "3.json.gz", tmp_path / "p.json"
    fb.write_golden(g, p1)
    fb.write_golden(g, p2)
    fb.write_golden({**g, "c": 0}, p3)
    fb.write_golden(g, plain)
    raw = p1.read_bytes()
    assert raw[:2] == b"\x1f\x8b" and raw[4:8] == b"\x00\x00\x00\x00", "須為 gzip 且檔頭 mtime 為 0"
    assert raw == p2.read_bytes(), "同內容兩次寫出位元組須相同"
    assert raw != p3.read_bytes(), "內容改變須使位元組改變"
    assert gzip.decompress(raw) == _canon_golden_bytes(g)
    assert plain.read_bytes() == _canon_golden_bytes(g), "非 .gz 路徑須原樣寫出正準 JSON"
    for p in (p1, plain):
        assert _canon_golden_bytes(fb.load_golden(p)) == _canon_golden_bytes(g)
    assert not list(tmp_path.glob("*.tmp")), "暫存檔須已原子換名"


def _probe_pair(fb: Any, d: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """同一請求兩次之記錄（邊界輸入：tmp_path 小檔）：回應與 JSON 檔之 generated_at、HDF5 之 source_generated_at 兩處屬性
    不同，其餘相同。"""
    for run, stamp in (("1", "t1"), ("2", "t2")):
        (d / f"r{run}.json").write_text(json.dumps({"generated_at": stamp, "ic": 0.5}), encoding="utf-8")
        _write_volatile_h5(d / f"f{run}.h5", stamp=stamp)
    rec = [{"response": fb.flatten_fields({"meta": {"generated_at": s}, "ic": [1, 2]}),
            "files": {"r.json": fb.describe_file(d / f"r{run}.json"), "f.h5": fb.describe_file(d / f"f{run}.h5")},
            "features": {"x": {"/summary_table/ic_mean": {"sha256": "0" * 64, "nan_mask_sha256": "1" * 64}}},
            "selected": ["x"], "removed": []} for run, s in (("1", "t1"), ("2", "t2"))]
    return rec[0], rec[1]


def test_volatile_probe_diff_classifies_excludable(fb: Any, tmp_path: Path) -> None:
    """兩次只差時間戳 ⇒ volatile 項恰為回應欄位、JSON 檔欄位、HDF5 兩處屬性，無法排除之差異為空；以之排除後
    `compare_capture` 無問題，不排除則有（改壞對照）。"""
    a, b = _probe_pair(fb, tmp_path)
    vol, bad = fb.probe_diff(a, b)
    assert sorted(vol) == sorted(["response:/meta/generated_at", "file:r.json#/generated_at",
                                  "file:f.h5@/#attr:source_generated_at", "file:f.h5@/g#attr:source_generated_at"])
    assert bad == []
    assert fb.compare_capture(a, b, volatile=vol) == []
    assert fb.compare_capture(a, b), "未排除時須列問題"


def test_volatile_probe_diff_unexcludable_cases(fb: Any, tmp_path: Path) -> None:
    """無法以 volatile 排除之差異各自列出（點名檔或欄位）：多一檔、非 JSON 非 HDF5 之位元組不等、HDF5 資料集不等、
    JSON 位元組不等而逐欄位皆等、回應欄位只在一次、逐特徵摘要不等、選欄集合不等。"""
    a, b = _probe_pair(fb, tmp_path)
    (tmp_path / "x1.bin").write_bytes(b"a")
    (tmp_path / "x2.bin").write_bytes(b"b")
    (tmp_path / "o1.json").write_text('{"a":1,"b":2}', encoding="utf-8")
    (tmp_path / "o2.json").write_text('{"b":2,"a":1}', encoding="utf-8")
    _write_volatile_h5(tmp_path / "d2.h5", stamp="t2", data=np.array([0.0, 1.0, 5.0]))
    cases = {
        "extra": ({}, {"files": {**b["files"], "new.json": fb.describe_file(tmp_path / "r2.json")}}, "new.json"),
        "binary": ({"files": {**a["files"], "x.bin": fb.describe_file(tmp_path / "x1.bin")}},
                   {"files": {**b["files"], "x.bin": fb.describe_file(tmp_path / "x2.bin")}}, "x.bin"),
        "h5data": ({}, {"files": {**b["files"], "f.h5": fb.describe_file(tmp_path / "d2.h5")}}, "/g/v"),
        "order": ({"files": {**a["files"], "o.json": fb.describe_file(tmp_path / "o1.json")}},
                  {"files": {**b["files"], "o.json": fb.describe_file(tmp_path / "o2.json")}}, "o.json"),
        "resp": ({}, {"response": {**b["response"], "/extra": "0" * 64}}, "/extra"),
        "features": ({}, {"features": {"x": {"/summary_table/ic_mean": {"sha256": "2" * 64,
                                                                         "nan_mask_sha256": "1" * 64}}}}, "features/x"),
        "selected": ({}, {"selected": ["y"]}, "selected"),
    }
    for name, (pa, pb, needle) in cases.items():
        _, bad = fb.probe_diff({**a, **pa}, {**b, **pb})
        assert any(needle in p for p in bad), f"{name}：須列為無法排除之差異（點名 {needle}），實得 {bad}"


def test_repo_root_counts_only_audited_or_data_cache_and_skips_work_root(fb: Any, tmp_path: Path) -> None:
    """SPEC v5.45 §G (2) ③（2026-11-01 volatile-probe 實例：他行程寫 frontend/.next、logs/、HANDOFF.md 與本次工作根自身
    被計入 ⇒ 185 項無法排除）：`<repo>/` 鍵之新增／變更／刪除，未經子行程審計且不在 data_cache/ 下者不入 files／removed、
    改列 repo_ignored；經審計者或 data_cache/ 下者照計；工作根位於 repo 內時快照走訪整棵略過（其下之 cwd 根另為根照走）。
    改壞對照：不給 exclude_dirs 時工作根內檔被走訪到。"""
    repo, cwd = tmp_path / "repo", tmp_path / "repo" / "runs" / "w" / "item" / "cwd"
    for rel in ("src.py", "doc.md", "old.txt", "data_cache/old.json", "runs/w/README.txt"):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text("0", encoding="utf-8")
    cwd.mkdir(parents=True)
    roots, prefixes = [cwd, repo], {"<repo>": repo}
    skip = [repo / "runs" / "w"]
    before = fb.snapshot_files(roots, repo_root=cwd, prefixes=prefixes, exclude_dirs=skip)
    assert "<repo>/runs/w/README.txt" not in before
    assert "<repo>/runs/w/README.txt" in fb.snapshot_files(roots, repo_root=cwd, prefixes=prefixes), "改壞對照"
    (repo / "src.py").write_text("1", encoding="utf-8")       # 他行程：不計
    (repo / "doc.md").write_text("1", encoding="utf-8")       # 經審計：計
    (repo / "data_cache" / "new.json").write_text("{}", encoding="utf-8")  # data_cache：計
    (repo / "old.txt").unlink()                               # 他行程刪除：不計
    (repo / "data_cache" / "old.json").unlink()               # data_cache 刪除：計
    (cwd / "out.json").write_text("{}", encoding="utf-8")     # cwd 根：恆計
    (repo / "runs" / "w" / "README.txt").write_text("1", encoding="utf-8")  # 工作根：不走訪
    after = fb.snapshot_files(roots, repo_root=cwd, prefixes=prefixes, exclude_dirs=skip)
    log = [{"event": "open", "path": str(repo / "doc.md")}]
    got = fb.collect_written_files(log, before, after, repo_root=cwd, snapshot_roots=roots, output_roots=[],
                                   prefixes=prefixes)
    assert sorted(got["files"]) == ["<repo>/data_cache/new.json", "<repo>/doc.md", "out.json"]
    assert got["removed"] == ["<repo>/data_cache/old.json"]
    assert got["repo_ignored"] == ["<repo>/old.txt", "<repo>/src.py"]


def test_new_work_root_card_and_probe_rejudge_without_rerun(fb: Any, tmp_path: Path) -> None:
    """SPEC v5.45 §G (2) ②：`new_work_root` 建於 `<repo_root>/RUNS_ROOT`（repo 內 runs/，非 data_cache／系統暫存）並寫說明卡
    （入口、用途、何時可刪）；volatile-probe 各項重跑記錄存檔後 `probe_rejudge` 不重跑即得與直接判定相同之結果；缺任一項
    記錄 ⇒ FreezeError。"""
    assert fb.RUNS_ROOT.split("/")[0] == "runs"
    w = fb.new_work_root("icperf-volprobe-", tmp_path, purpose="測試用途")
    card = (w / fb.RUN_CARD).read_text(encoding="utf-8")
    assert w.parent == tmp_path / fb.RUNS_ROOT and "volprobe" in card and "測試用途" in card and "何時可刪" in card
    a, b = _probe_pair(fb, tmp_path)
    golden = {"items": {i: {**a, "request": {"kind": "x"}} for i in OUTPUT_ITEMS}}
    gpath = tmp_path / "g.json.gz"
    fb.write_golden(golden, gpath)
    work = tmp_path / "probe"
    for i in OUTPUT_ITEMS:
        (work / i).mkdir(parents=True)
        (work / i / fb.PROBE_RECORD).write_bytes(fb._canonical_json(b))
    got = fb.probe_rejudge(work, golden_path=gpath)
    assert got["unexcludable"] == [] and len(got["volatile"]) == 4 * len(OUTPUT_ITEMS)
    assert got["volatile"] == fb._probe_judge(fb.load_golden(gpath), {i: b for i in OUTPUT_ITEMS},
                                              golden_path=gpath, work=work)["volatile"]
    (work / OUTPUT_ITEMS[0] / fb.PROBE_RECORD).unlink()
    with pytest.raises(fb.FreezeError, match="缺重跑記錄"):
        fb.probe_rejudge(work, golden_path=gpath)


def test_item_sets_match_spec_and_pending_fail_closed(fb: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC v5.26 §G：凍結腳本之項集合＝(1)–(7) 九鍵（測試自持）；待定項（`PENDING_ITEMS`）之 `default_request` 須
    FreezeError，`freeze` 須於啟動任何執行前即拒（以替身設 `PENDING_PROBE` 驗；替身 `freeze_item` 被呼叫即 FAIL）；第 (3)(6)
    項請求之深度分析模組全開（含預設關閉者）；第 (6)(7) 項之格＝L、第 (7) 項帶 Task 0.3 所建之匯入批 id、其餘項不帶。"""
    assert tuple(fb.G_ITEMS) == G_ITEMS and tuple(fb.OUTPUT_ITEMS) == OUTPUT_ITEMS
    assert tuple(fb.PENDING_ITEMS) == PENDING_ITEMS
    monkeypatch.setattr(fb, "PENDING_ITEMS", PENDING_PROBE)
    for item in PENDING_PROBE:
        with pytest.raises(fb.FreezeError):
            fb.default_request(item)

    def must_not_run(*a: Any, **k: Any) -> None:
        pytest.fail("請求未定時 freeze 不得啟動任何執行")

    monkeypatch.setattr(fb, "freeze_item", must_not_run)
    with pytest.raises(fb.FreezeError):
        fb.freeze(tmp_path / "g.json.gz", work_root=tmp_path / "w")
    assert not (tmp_path / "g.json.gz").exists()
    monkeypatch.setattr(fb, "PENDING_ITEMS", PENDING_ITEMS)
    from api.models.ic_models import DeepAnalysisModules

    for item in ("deep_analysis", "deep_analysis_long"):
        modules = fb.default_request(item, CELL)["deep"]["modules"]
        assert set(modules) == set(DeepAnalysisModules.model_fields) and all(v is True for v in modules.values()), modules
        # 具名 preset 之 disabled_modules 會靜默關掉正交化／曝險 ⇒ 深度項須走 custom 方案且 module_overrides 全開
        req = fb.default_request(item, CELL)
        for tiers in (req["feature_tiers"], req["config_override"]["feature_tiers"]):
            assert tiers["active_preset"] == "custom", tiers
            assert tiers["custom_overrides"]["module_overrides"] == {k: True for k in DeepAnalysisModules.model_fields}
            assert tiers["custom_overrides"]["stage_overrides"] == \
                fb.IC_PAGE_DEFAULT_PAYLOAD["feature_tiers"]["custom_overrides"]["stage_overrides"]
    for item in ("ic_report_long", "deep_analysis_long", "event_import_report"):
        assert fb.default_request(item, CELL)["cell"] == LONG_CELL, item
    assert fb.default_request("event_import_report", CELL)["event_import_id"] == EVENT_IMPORT_ID
    for item in ("ic_report", "deep_analysis", "event_report", "ic_report_long", "deep_analysis_long"):
        assert fb.default_request(item, CELL)["event_import_id"] is None, item


_ICIR_SORT_CALLS = {"sorted", "sort", "max", "min", "nlargest", "nsmallest"}
_ICIR_TS_PATTERNS = [re.compile(r"sort_by:\s*[\"'`]icir[\"'`]"), re.compile(r"\?\?\s*[\"'`]icir[\"'`]"),
                     re.compile(r"useState\(\s*[\"'`]icir[\"'`]")]


def _icir_default_sort_hits_py(src: str, path: str = "<s>") -> List[Tuple[str, int, str]]:
    """SPEC Task 0.4 ⑧ 驗收⑥：以 AST 找以字面 "icir" 為預設排序鍵之四類寫法——(a) sorted／sort／max／min／nlargest／
    nsmallest 之 key= 值內（含 key 為同檔具名函式時其本體）；(b) 名為 sort_by 之參數預設值；(c) 關鍵字引數 sort_by="icir"；
    (d) 名稱含 sort 之呼叫之位置引數。"""
    def _name(f: Any) -> str:
        return f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""

    def _has(node: Any) -> bool:
        return any(isinstance(n, ast.Constant) and n.value == "icir" for n in ast.walk(node))

    tree = ast.parse(src)
    defs = {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    hits: List[Tuple[str, int, str]] = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            fn = _name(n.func)
            for kw in n.keywords:
                if kw.arg == "key" and fn in _ICIR_SORT_CALLS:
                    v = kw.value
                    if _has(v) or (isinstance(v, ast.Name) and v.id in defs and _has(defs[v.id])):
                        hits.append((path, n.lineno, "a"))
                if kw.arg == "sort_by" and isinstance(kw.value, ast.Constant) and kw.value.value == "icir":
                    hits.append((path, n.lineno, "c"))
            if "sort" in fn.lower() and any(isinstance(a, ast.Constant) and a.value == "icir" for a in n.args):
                hits.append((path, n.lineno, "d"))
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = n.args.args + n.args.kwonlyargs
            defaults = [None] * (len(n.args.args) - len(n.args.defaults)) + list(n.args.defaults) + list(n.args.kw_defaults)
            for a, d in zip(args, defaults):
                if a.arg == "sort_by" and d is not None and _has(d):
                    hits.append((path, n.lineno, "b"))
    return hits


def _icir_default_sort_hits_ts(src: str, path: str = "<s>") -> List[Tuple[str, int, str]]:
    return [(path, i, "ts") for i, line in enumerate(src.splitlines(), 1) if any(p.search(line) for p in _ICIR_TS_PATTERNS)]


def _is_test_path(p: Path) -> bool:
    s = p.as_posix()
    return "/tests/" in s or p.name.startswith("test_") or ".test." in p.name or "__tests__" in s


def test_no_raw_icir_default_sort() -> None:
    """SPEC Task 0.4 ⑧ 驗收⑥：`momentum/`、`api/` 非測試 .py 與 `frontend/src` 非測試 .ts／.tsx，以字面 "icir" 為預設排序鍵
    者為 0（預設排序一律 `icir_aligned`）；反例自證：四類 Python 寫法與三種前端引號各造一段字串碼，掃描須逐一命中。"""
    for src, cls in [
        ("rows = sorted(t, key=lambda r: f(r.get('icir')))", "a"),
        ("def _k(r):\n    return r.get('icir')\nrows = sorted(t, key=_k)", "a"),
        ("def g(n, sort_by='icir'):\n    return n", "b"),
        ("def g(n, sort_by=Query('icir')):\n    return n", "b"),
        ("page = paginate(rows, sort_by='icir')", "c"),
        ("x = self._sort_rows(rows, 'icir')", "d"),
    ]:
        assert [h[2] for h in _icir_default_sort_hits_py(src)] == [cls], src
    for src in ("summaryParams: { sort_by: 'icir' }", 'sort_by: "icir"', "const f = p ?? `icir`", "useState('icir')"):
        assert _icir_default_sort_hits_ts(src), src
    assert not _icir_default_sort_hits_py("rows = sorted(t, key=lambda r: r.get(sort_by))")
    hits: List[Tuple[str, int, str]] = []
    for base in ("momentum", "api"):
        for p in (REPO / base).rglob("*.py"):
            if not _is_test_path(p):
                hits += _icir_default_sort_hits_py(p.read_text(encoding="utf-8"), p.relative_to(REPO).as_posix())
    for p in (REPO / "frontend" / "src").rglob("*.ts*"):
        if not _is_test_path(p):
            hits += _icir_default_sort_hits_ts(p.read_text(encoding="utf-8"), p.relative_to(REPO).as_posix())
    assert hits == [], f"以原始 icir 為預設排序鍵之生產碼：{hits}"


def test_event_import_response_shape_same_as_ic_report(fb: Any) -> None:
    """SPEC v5.26 §G (7)：事件匯入批回應之形狀同第 (1) 項——任務 `result`（報告）於頂層、其餘任務欄（analyzer 除外）
    置於 `event_task`；報告自帶 `event_task` 鍵 ⇒ FreezeError。邊界輸入：明列任務 dict。"""
    info = {"status": "completed", "result": {"summary_table": [{"feature_name": "x"}], "version": "v"},
            "analyzer": object(), "task_id": "t", "event_sample_design": {"kind": "case_control"}}
    out = fb.event_import_response(info)
    assert set(out) == {"summary_table", "version", "event_task"}
    assert out["event_task"] == {"status": "completed", "task_id": "t", "event_sample_design": {"kind": "case_control"}}
    assert set(fb.feature_tables("event_import_report")) == set(fb.feature_tables("ic_report"))
    with pytest.raises(fb.FreezeError):
        fb.event_import_response({"result": {"event_task": 1}})


def test_describe_file_json_by_content(fb: Any, tmp_path: Path) -> None:
    """內容為 JSON 而副檔名非 .json 者（如租約鎖檔 `{"pid", "ts"}`）亦逐欄位摘要；首位元組非 `{`／`[` 者（parquet 魔數、
    空檔）與不可解析者 fields 為 None。邊界輸入：tmp_path 小檔。"""
    (tmp_path / "a.lock").write_text('{"pid": 1, "ts": "t"}', encoding="utf-8")
    (tmp_path / "b.parquet").write_bytes(b"PAR1\x00\x00PAR1")
    (tmp_path / "c.lock").write_bytes(b"")
    (tmp_path / "d.lock").write_bytes(b"{not json")
    assert set(fb.describe_file(tmp_path / "a.lock")["fields"]) == {"/pid", "/ts"}
    for name in ("b.parquet", "c.lock", "d.lock"):
        assert fb.describe_file(tmp_path / name)["fields"] is None, name


def test_volatile_probe_reruns_frozen_request_once(fb: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`volatile_probe`：第 (1)(3)(4)(5) 項各以凍結檔所記之同一請求再跑一次，與凍結記錄之差異帶 `<項>:` 前綴彙總，收據記
    凍結檔位元組 sha256；逐特徵摘要不等 ⇒ 無法排除（整格可重現性）。以替身 `freeze_item` 驗編排（不跑產品碼）。"""
    golden = {"items": {i: {"request": {"item": i}, "response": {"/generated_at": "t0", "/ic": "same"}, "files": {},
                            "removed": []} for i in OUTPUT_ITEMS}}
    golden["items"]["event_report"]["features"] = {"x": {"/q": {"sha256": "0" * 64}}}
    path = tmp_path / "g.json.gz"
    fb.write_golden(golden, path)
    calls: List[Tuple[str, Dict[str, Any]]] = []

    def fake_freeze_item(item: str, *, request: Mapping[str, Any], repo_root: Path, work_root: Path) -> Dict[str, Any]:
        calls.append((item, dict(request)))
        rec: Dict[str, Any] = {"response": {"/generated_at": "t1", "/ic": "same"}, "files": {}, "removed": []}
        if item == "event_report":
            rec["features"] = {"x": {"/q": {"sha256": "1" * 64}}}
        return rec

    monkeypatch.setattr(fb, "freeze_item", fake_freeze_item)
    monkeypatch.setattr(fb, "PENDING_ITEMS", ())  # 編排驗證情境：第 (6)(7) 項已定義（待定時之拒絕見下一支測試）
    pre: List[Tuple[Dict[str, Any], int]] = []  # 開跑前檢查另有專測；此處驗其於任何重跑前收到凍結所記之全部請求
    monkeypatch.setattr(fb, "preflight", lambda requests, **kw: pre.append((dict(requests), len(calls))))
    out = fb.volatile_probe(golden_path=path, work_root=tmp_path / "w")
    assert pre == [({i: {"item": i} for i in OUTPUT_ITEMS}, 0)]
    assert calls == [(i, {"item": i}) for i in OUTPUT_ITEMS]
    assert out["volatile"] == [f"{i}:response:/generated_at" for i in OUTPUT_ITEMS]
    assert any(u.startswith("event_report:features/x") for u in out["unexcludable"]), out["unexcludable"]
    assert out["golden_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_volatile_probe_rejects_pending_items_before_any_run(fb: Any, tmp_path: Path,
                                                            monkeypatch: pytest.MonkeyPatch) -> None:
    """r41 CODEX-R41-P1-04：第 (6)(7) 項待定時，即使凍結檔含其請求，`volatile_probe` 仍須於任何 `freeze_item` 前 FreezeError
    （同 `freeze` 之 fail-closed；替身被呼叫即 FAIL）。"""
    golden = {"items": {i: {"request": {"item": i}, "response": {}, "files": {}, "removed": []} for i in OUTPUT_ITEMS}}
    path = tmp_path / "g.json.gz"
    fb.write_golden(golden, path)

    def must_not_run(*a: Any, **k: Any) -> None:
        pytest.fail("待定項未定時 volatile_probe 不得啟動任何執行")

    monkeypatch.setattr(fb, "freeze_item", must_not_run)
    monkeypatch.setattr(fb, "PENDING_ITEMS", PENDING_PROBE)
    with pytest.raises(fb.FreezeError):
        fb.volatile_probe(golden_path=path, work_root=tmp_path / "w")


def test_apply_volatile_writes_present_entries_only(fb: Any, tmp_path: Path) -> None:
    """`apply_volatile`：凍結檔中存在之項（回應欄位、JSON 檔欄位、HDF5 物件屬性）寫入 "volatile"，不存在者列 "absent"，
    未入 volatile 之候選列 "candidates_not_volatile"；寫回後 `compare_golden` 可解析（本檔只含第 (1) 項，只看該項）；
    實測有無法排除之差異、項前綴不合、或凍結檔已非實測時之同一檔 ⇒ FreezeError 且凍結檔位元組不變。"""
    path = tmp_path / "g.json.gz"
    golden = {"schema": "icperf-pre-change/1", "volatile": [],
              "volatile_candidates": [{"entry": "ic_report:response:/generated_at", "reason": "name_hint"},
                                      {"entry": "ic_report:response:/x/timestamps#values", "reason": "name_hint"}],
              "items": {"ic_report": {
                  "response": {"/generated_at": "0" * 64, "/x/timestamps#values": "1" * 64},
                  "files": {"r.json": {"sha256": "2" * 64, "hdf5": None, "fields": {"/generated_at": "3" * 64}},
                            "f.h5": {"sha256": "4" * 64, "fields": None,
                                     "hdf5": {"/g": {"kind": "group", "attrs": {"source_generated_at": "5" * 64}}}}}}}}
    fb.write_golden(golden, path)
    present = ["ic_report:response:/generated_at", "ic_report:file:r.json#/generated_at",
               "ic_report:file:f.h5@/g#attr:source_generated_at"]
    missing = "ic_report:response:/deep_analysis_errors/3/timestamp"
    before = path.read_bytes()
    sha = hashlib.sha256(before).hexdigest()
    with pytest.raises(fb.FreezeError):
        fb.apply_volatile({"golden_sha256": sha, "volatile": present,
                           "unexcludable": ["ic_report:file:x.bin：位元組不等"]}, golden_path=path)
    with pytest.raises(fb.FreezeError):
        fb.apply_volatile({"golden_sha256": sha, "volatile": ["nope:response:/a"], "unexcludable": []},
                          golden_path=path)
    with pytest.raises(fb.FreezeError):  # 實測後凍結檔已變（實測所記之凍結檔 sha256 不符）
        fb.apply_volatile({"golden_sha256": "7" * 64, "volatile": present, "unexcludable": []}, golden_path=path)
    assert path.read_bytes() == before, "FreezeError 時凍結檔不得改動"
    res = fb.apply_volatile({"golden_sha256": sha, "volatile": present + [missing], "unexcludable": []},
                            golden_path=path, probe_sha256="6" * 64)
    assert res["volatile"] == sorted(present) and res["absent"] == [missing]
    assert res["candidates_not_volatile"] == ["ic_report:response:/x/timestamps#values"]
    again = fb.load_golden(path)
    assert again["volatile"] == sorted(present)
    assert again["volatile_probe"] == {"golden_sha256": sha, "sha256": "6" * 64}
    assert not [p for p in fb.compare_golden(again, again) if p.startswith("ic_report/")], "寫入之 volatile 須可解析且自比無差異"


# ── §G 請求設定與逐特徵來源之秒級契約 ───────────────────────────────────────────────────────────────────────


def test_boundary_24_feature_sources_per_spec(fb: Any) -> None:
    """SPEC §G baseline 內容：第 (1)、(4) 項之逐特徵來源與形狀＝FEATURE_SOURCES（summary_table "rows"、quantile_returns／
    coverage_analysis／turnover_analysis "by_key"）；第 (3)、(5) 項無逐特徵來源（深度分析由回應全部欄位涵蓋）；通過集合
    不在回應（selected_pointer 為 None，取自寫出之倖存者檔，boundary_02）。"""
    for item in SURVIVOR_ITEMS:
        assert fb.feature_tables(item) == FEATURE_SOURCES, f"{item}：逐特徵來源 != SPEC §G"
        assert fb.selected_pointer(item) is None, f"{item}：通過集合不在回應（報告頂層無名單）"
    for item in ("deep_analysis", "icfirst_post_ic"):
        assert fb.feature_tables(item) == {}, f"{item}：SPEC v5.8 起無逐特徵來源"


FRONTEND_STORE = REPO / "frontend" / "src" / "store" / "icAnalysisStore.ts"
FRONTEND_OVERRIDE = REPO / "frontend" / "src" / "lib" / "icConfigOverride.ts"
FRONTEND_HOOK = REPO / "frontend" / "src" / "hooks" / "useICAnalysis.ts"
UI_STAGE_TOGGLES = REPO / "momentum" / "Analysis" / "contracts" / "ui_stage_toggles.json"


def _ts_block(src: str, head: str) -> str:
    """自 TypeScript 原始碼取 `head` 起之第一個大括號區塊內容（括號配對；測試自寫之最小解析）。"""
    start = src.index(head)
    i = src.index("{", start)
    depth = 0
    for j in range(i, len(src)):
        depth += {"{": 1, "}": -1}.get(src[j], 0)
        if depth == 0:
            return src[i + 1:j]
    raise AssertionError(f"{head}：大括號不成對")


def _ts_number(text: str) -> Any:
    return int(text) if re.fullmatch(r"-?\d+", text) else float(text)


def _frontend_ic_page_payload() -> Dict[str, Any]:
    """由前端原始碼導出 IC 頁初始狀態送出之 config_override 與 feature_tiers（測試自寫之 regex 解析，不跑前端）：
    `defaultConfig` 之 horizons／thresholds、`buildConfigOverride` 之鍵對映、初始 `featureTier` 與 `featureToggles`、
    `PRESET_TOGGLES.intermediate`、`STAGE_TOGGLE_KEYS`、`getEffectiveConfig` 具名 preset 分支、`useICAnalysis` 之 payload 組裝。"""
    store = FRONTEND_STORE.read_text(encoding="utf-8")
    override_src = FRONTEND_OVERRIDE.read_text(encoding="utf-8")
    hook = FRONTEND_HOOK.read_text(encoding="utf-8")
    default_cfg = _ts_block(store, "const defaultConfig: ICAnalysisConfig =")
    horizons = [int(x) for x in re.search(r"\bhorizons:\s*\[([^\]]*)\]", default_cfg).group(1).split(",") if x.strip()]
    thresholds = {k: _ts_number(v) for k, v in
                  re.findall(r"(\w+):\s*(-?[\d.]+)", _ts_block(default_cfg, "thresholds:"))}
    cfg = {"horizons": horizons, "thresholds": thresholds}
    body = _ts_block(override_src, "export const buildConfigOverride =")
    out_thr = {k: cfg["thresholds"][src_k] for k, src_k in
               re.findall(r"(\w+):\s*config\.thresholds\.(\w+)", _ts_block(body, "const thresholds"))}
    for k, src_k in re.findall(r"thresholds\.(\w+)\s*=\s*config\.thresholds\.(\w+)", body):
        if isinstance(cfg["thresholds"].get(src_k), (int, float)):  # `typeof … === 'number'` 之條件分支
            out_thr[k] = cfg["thresholds"][src_k]
    red = re.search(r"redundancy:\s*\{\s*(\w+):\s*config\.thresholds\.(\w+)", body)
    lab = re.search(r"labels:\s*\{\s*(\w+):\s*config\.(\w+)", body)
    config_override: Dict[str, Any] = {"thresholds": out_thr, "redundancy": {red.group(1): cfg["thresholds"][red.group(2)]},
                                       "labels": {lab.group(1): cfg[lab.group(2)]}}
    tier = re.search(r"\n\s*featureTier:\s*'(\w+)'", store).group(1)
    toggles_tier = re.search(r"\n\s*featureToggles:\s*\{\s*\.\.\.PRESET_TOGGLES\.(\w+)\s*\}", store).group(1)
    assert toggles_tier == tier, f"前端初始 featureToggles（{toggles_tier}）!= 初始 featureTier（{tier}）"
    preset = {k: v == "true" for k, v in
              re.findall(r"(\w+):\s*(true|false)", _ts_block(_ts_block(store, "const PRESET_TOGGLES"), f"{tier}:"))}
    stage_keys = re.findall(r"'(\w+)'", re.search(r"export const STAGE_TOGGLE_KEYS = \[([^\]]*)\]", store).group(1))
    effective = _ts_block(store, "getEffectiveConfig: () => {")  # 實作（非 interface 之型別宣告）
    named = effective[effective.rindex("return {"):]
    assert re.search(r"active_preset:\s*state\.featureTier", named) and \
        re.search(r"custom_overrides:\s*\{\s*stage_overrides:\s*stageOverrides\s*\}", named), \
        "getEffectiveConfig 具名 preset 分支之組裝已變（須重審 IC_PAGE_DEFAULT_PAYLOAD）"
    assert re.search(r"config_override:\s*\{\s*\.\.\.buildConfigOverride\(config\),\s*"
                     r"\.\.\.\(effectiveConfig\.feature_tiers \? \{ feature_tiers: effectiveConfig\.feature_tiers \} : \{\}\),",
                     hook), "useICAnalysis 之 config_override 組裝已變（須重審 IC_PAGE_DEFAULT_PAYLOAD）"
    assert re.search(r"\n\s*feature_tiers:\s*effectiveConfig\.feature_tiers,", hook), \
        "useICAnalysis 之頂層 feature_tiers 組裝已變（須重審 IC_PAGE_DEFAULT_PAYLOAD）"
    feature_tiers = {"active_preset": tier,
                     "custom_overrides": {"stage_overrides": {k: bool(preset.get(k)) for k in stage_keys}}}
    return {"config_override": {**config_override, "feature_tiers": feature_tiers}, "feature_tiers": feature_tiers,
            "stage_keys": stage_keys}


def test_boundary_25_ic_page_default_payload_matches_frontend(fb: Any) -> None:
    """SPEC §G「各項請求設定」：凍結腳本寫死之 IC 頁初始 payload（IC_PAGE_DEFAULT_PAYLOAD）== 前端原始碼導出之初始
    payload（衰減開：intermediate 之 ic_decay 為 true）；stage_overrides 鍵集 == ui_stage_toggles.json 之 stage_keys ==
    前端 STAGE_TOGGLE_KEYS。前端改預設即紅（須重凍）。"""
    expected = _frontend_ic_page_payload()
    contract = json.loads(UI_STAGE_TOGGLES.read_text(encoding="utf-8"))
    assert expected["stage_keys"] == contract["stage_keys"], "前端 STAGE_TOGGLE_KEYS != ui_stage_toggles.json stage_keys"
    payload = fb.IC_PAGE_DEFAULT_PAYLOAD
    assert payload["config_override"] == expected["config_override"], "config_override != 前端初始 payload"
    assert payload["feature_tiers"] == expected["feature_tiers"], "feature_tiers != 前端初始 payload"
    stage = payload["config_override"]["feature_tiers"]["custom_overrides"]["stage_overrides"]
    assert set(stage) == set(contract["stage_keys"]), "stage_overrides 鍵集 != ui_stage_toggles.json stage_keys"
    assert stage["ic_decay"] is True, "SPEC §G：IC 頁預設衰減開（不沿用 FFPROD 量測之衰減關）"


# ── Task 0.2 收據 ───────────────────────────────────────────────────────────────────────────────────────


def _pit_callers() -> set:
    """AST 掃 momentum/：呼叫 PIT_CALLEES 任一者之 `<模組>:<限定名>`（測試自持之 oracle）。"""
    out = set()
    for path in sorted((REPO / "momentum").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        module = ".".join(path.relative_to(REPO).with_suffix("").parts)
        tree = ast.parse(path.read_text(encoding="utf-8"))

        def visit(node: ast.AST, qual: List[str]) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    visit(child, qual + [child.name])
                    continue
                if isinstance(child, ast.Call) and qual:
                    f = child.func
                    name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None
                    if name in PIT_CALLEES:
                        out.add(f"{module}:{'.'.join(qual)}")
                visit(child, qual)

        visit(tree, [])
    return out


def test_boundary_14_inventory_fields_and_scope() -> None:
    """清冊每一入口欄位齊備；範圍涵蓋 SPEC Task 0.2 列名之各段與具名逐根 PIT 入口、pit_stats 四函式各呼叫端。"""
    entries = _inventory_entries()
    for eid, e in entries.items():
        assert INVENTORY_KEYS <= set(e), f"{eid}：缺欄 {sorted(INVENTORY_KEYS - set(e))}"
        assert re.match(r"^[A-Za-z_][\w.]*:[A-Za-z_][\w.]*$", eid), f"{eid}：id 須為 模組:函式"
        assert e["stage"] in REQUIRED_STAGES, f"{eid}：所屬段 {e['stage']} 非法"
        # SPEC v5.52 (b)：事件數不記為 rows ⇒ 只隨事件數變之入口 input_axes 可空（限 scale_vector 含 events）
        assert (e["input_axes"] or "events" in e.get("scale_vector", [])) and set(e["input_axes"]) <= INPUT_AXES, \
            f"{eid}：輸入軸非法"
        assert isinstance(e["ic_page"], bool) and isinstance(e["ic_first"], bool), eid
        assert e["loop"] in LOOPS, f"{eid}：迴圈型別非法"
    stages = {e["stage"] for e in entries.values()}
    assert REQUIRED_STAGES <= stages, f"清冊未涵蓋段：{sorted(REQUIRED_STAGES - stages)}"
    assert REQUIRED_NAMED_ENTRIES <= set(entries), f"缺具名入口：{sorted(REQUIRED_NAMED_ENTRIES - set(entries))}"
    callers = _pit_callers()
    assert callers, "AST 掃描未找到 pit_stats 四函式之呼叫端（oracle 失效）"
    assert callers <= set(entries), f"清冊缺 pit_stats 呼叫端：{sorted(callers - set(entries))}"
    # SPEC v5.19 Task 0.2：每一入口另記 coverage_path_id（與入口一一對應）、unit_axis、scale_vector（與 Task 5.4 共用 schema）
    for eid, e in entries.items():
        _assert_inventory_axes(eid, e)
    cpids = [e["coverage_path_id"] for e in entries.values()]
    assert len(set(cpids)) == len(cpids), "coverage_path_id 須與入口一一對應（重複）"


def _assert_inventory_axes(eid: str, e: Mapping[str, Any]) -> None:
    """清冊入口之 coverage_path_id／unit_axis／scale_vector（SPEC Task 0.2、5.4）：拒收缺軸、單位歧義。"""
    assert isinstance(e.get("coverage_path_id"), str) and e["coverage_path_id"].strip(), f"{eid}：缺 coverage_path_id"
    sv = e.get("scale_vector")
    assert isinstance(sv, list) and sv and len(set(sv)) == len(sv) and set(sv) <= SCALE_VECTOR_KEYS, \
        f"{eid}：scale_vector 須為 {sorted(SCALE_VECTOR_KEYS)} 之非空不重複子集，實得 {sv!r}"
    ua = e.get("unit_axis")
    assert isinstance(ua, dict) and isinstance(ua.get("axes"), list) and ua["axes"], f"{eid}：缺 unit_axis.axes"
    assert set(ua["axes"]) <= set(sv), f"{eid}：unit_axis.axes {ua['axes']} 不在 scale_vector {sv} 內（單位歧義）"
    assert isinstance(ua.get("function"), str) and ua["function"].strip(), f"{eid}：缺 unit_axis.function（單位歧義）"


def _cover_check_catches_swapped_id(fb: Any, inventory: Mapping[str, Any], scale: Mapping[str, Any]) -> bool:
    """覆蓋檢查須比 id 集合：把某一需量測入口之量測鍵換成無關 id（筆數不變）⇒ 須點名該入口。"""
    needed = sorted(e["id"] for e in inventory["entries"] if e["measure"])
    if not needed:
        return False
    swapped = copy.deepcopy(dict(scale))
    entries = dict(swapped["entries"])
    victim = needed[0]
    entries["__icperf_unrelated_entry__"] = entries.pop(victim, {"points": []})
    swapped["entries"] = entries
    return fb.uncovered_entries(inventory, swapped) == [victim]


def test_boundary_15_measured_ids_cover_inventory(fb: Any) -> None:
    """每一入口標需量測或附「不量」碼證理由；量測收據入口 id 集合 ⊇ 需量測者（漏量即紅）。"""
    inv = _single(INVENTORY_PATTERN)
    scale = _single(SCALE_BEFORE_PATTERN)
    for e in inv["entries"]:
        if not e["measure"]:
            assert str(e["no_measure_reason"] or "").strip(), f"{e['id']}：不量須附理由"
            assert re.match(r"^[\w./-]+\.py:\d+", str(e["evidence"] or "")), f"{e['id']}：不量須附碼證 檔:行"
    needed = {e["id"] for e in inv["entries"] if e["measure"]}
    extra = set(scale["entries"]) - {e["id"] for e in inv["entries"]}
    assert not extra, f"量測收據含清冊外之入口 id：{sorted(extra)[:5]}"
    assert needed <= set(scale["entries"]), f"漏量：{sorted(needed - set(scale['entries']))}"
    assert fb.uncovered_entries(inv, scale) == []
    assert _cover_check_catches_swapped_id(fb, inv, scale)


def _scale_entries() -> Dict[str, Dict[str, Any]]:
    return _single(SCALE_BEFORE_PATTERN)["entries"]


def _scale_probe_receipt(path_str: Any) -> Dict[str, Any]:
    """量測點所引之 scale_probe 收據（實存、producer＝scripts/scale_probe.py）。"""
    src = str(path_str or "")
    assert src and (REPO / src).is_file(), f"量測點須引實存之 scale_probe 收據：{src!r}"
    rec = json.loads((REPO / src).read_text(encoding="utf-8"))
    assert rec["identity"]["meta"]["producer"] == "scripts/scale_probe.py", f"{src} 非 scale_probe 收據"
    return rec


def _sha_at_commit(head: str, paths: Sequence[str]) -> str:
    """`run_receipt_identity.code_sha256` 之同一算式，但取 `head` 提交中之 blob（量測時之碼；之後改碼不影響）。"""
    parts = []
    for rel in sorted(set(paths)):
        res = subprocess.run(["git", "rev-parse", "--verify", "-q", f"{head}:{rel}"], cwd=REPO,
                             capture_output=True, text=True)
        parts.append(f"{rel}:{res.stdout.strip() if res.returncode == 0 else 'missing'}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _assert_receipt_identity(eid: str, rec: Mapping[str, Any], probe: Mapping[str, Any], head: str) -> None:
    """scale_probe 收據之 identity.match 逐欄等於該入口所屬路徑宣告之量測命令（r11 CODEX-R11-P1-03；SPEC v5.50 (e)：
    身分＝**路徑命令、不含入口 id**——同一路徑實跑量多個入口）；entrypoint／target_argv 照 scale_probe 之取法、data 照
    現行檔重算（雜湊有快取）、code／config 取量測時提交 `head` 之 blob、hardware 等於本機。錯路徑、錯 argv、錯資料、改過之
    量測碼所產之收據即紅。"""
    rid = _load("icperf_gate_receipt_identity", REPO / "scripts" / "run_receipt_identity.py")
    cmd = [str(a) for a in probe["cmd"]]
    assert eid not in cmd, f"{eid}：路徑級量測命令不得含入口 id（SPEC v5.50 (e)）：{cmd}"
    entry = next((t for t in cmd if (REPO / t).is_file() and Path(t).suffix in (".py", ".sh")), cmd[0])
    expected = rid.compute_match(entry, cmd, [], probe["data"], probe["config"])
    expected["code_sha256"] = _sha_at_commit(head, [expected["entrypoint"]] if (REPO / expected["entrypoint"]).is_file()
                                             else [])
    expected["config_sha256"] = _sha_at_commit(head, [str(c) for c in probe["config"]])
    got = rec["identity"]["match"]
    for k in rid.MATCH_KEYS:
        assert got.get(k) == expected[k], f"{eid}：scale_probe 收據 identity.match.{k} != 宣告之量測命令"


def _assert_point_bound(eid: str, point: Mapping[str, Any], scale: int, unit: str, probe: Mapping[str, Any],
                        head: str) -> None:
    rec = _scale_probe_receipt(point.get("scale_probe_receipt"))
    _assert_receipt_identity(eid, rec, probe, head)
    hits = [q for q in rec["points"] if q["scale"] == scale and q["unit"] == unit]
    assert len(hits) == 1, f"{eid}：{point['scale_probe_receipt']} 無 scale={scale}／unit={unit} 之實測點"
    # SPEC v5.50 (e)：路徑級峰值 RSS 取自 scale_probe 該點；入口秒數改取同 path_run_id 之逐入口計時紀錄（下列）
    for k in ("peak_rss_bytes",):
        assert point[k] == hits[0][k], f"{eid}：{k} {point[k]} != scale_probe 實測 {hits[0][k]}"


def _point_axis(m: Mapping[str, Any]) -> Tuple[str, str]:
    """量測收據單一入口之主軸 (scale_probe unit, 點之 x 鍵)：SPEC v5.51 (d) 事件數軸＝("events", "events")；其餘＝
    ("cols", "input_cols")（收據 `axis` 欄；缺省 cols）。"""
    return ("events", "events") if m.get("axis") == "events" else ("cols", "input_cols")


RECORDS_ROOT = "handoffs/run_receipts/icperf_task02_records"


def _record_raw(rp: str) -> Optional[bytes]:
    """repo 內紀錄檔之位元組（不存在 ⇒ None；mutation 測試以記憶體內輸入置換）。"""
    path = REPO / rp
    return path.read_bytes() if path.is_file() else None


def _record_store_problems(eid: str, m: Mapping[str, Any]) -> List[str]:
    """SPEC v5.51 (h)(i)：每點（含列長點）之逐入口紀錄存於版控路徑 `RECORDS_ROOT/` 之下、`record_bytes`／`record_sha256`
    等於該檔實際位元組數與內容 sha256；`peak_footprint_bytes` 等於同 path_run_id 紀錄之 footprint（受測行程 `sample`），
    `footprint_source` 指該 path_run_id。問題清單（空＝成立）。"""
    out: List[str] = []
    for i, p in enumerate(list(m["points"]) + list(m.get("row_points") or [])):
        rp = str(p.get("record_path") or "")
        if not rp.startswith(RECORDS_ROOT + "/"):
            out.append(f"點 {i}：紀錄 {rp!r} 不在 {RECORDS_ROOT}/（v5.51 (i)）")
            continue
        raw = _record_raw(rp)
        if raw is None:
            out.append(f"點 {i}：紀錄 {rp} 不存在")
            continue
        if p.get("record_bytes") != len(raw) or p.get("record_sha256") != hashlib.sha256(raw).hexdigest():
            out.append(f"點 {i}：紀錄大小／sha256 與收據不符")
        rec = json.loads(raw.decode("utf-8"))
        if p.get("peak_footprint_bytes") != rec.get("peak_footprint_bytes"):
            out.append(f"點 {i}：footprint {p.get('peak_footprint_bytes')} != 同 path_run_id 紀錄 {rec.get('peak_footprint_bytes')}")
        if p.get("footprint_source") != f"harness_record:{rec.get('path_run_id')}":
            out.append(f"點 {i}：footprint_source {p.get('footprint_source')!r} 非同 path_run_id 紀錄")
    return out


def _entry_record(path_str: Any) -> Optional[Dict[str, Any]]:
    """量測點所引之 repo 內 JSON（逐入口計時紀錄〔scripts/icperf_scale_harness.py 寫出〕或 scale_probe 收據；不存在 ⇒
    None；不斷言，供問題清單式檢查）。"""
    src = str(path_str or "")
    if not src or not (REPO / src).is_file():
        return None
    return json.loads((REPO / src).read_text(encoding="utf-8"))


def _entry_record_problems(eid: str, m: Mapping[str, Any]) -> List[str]:
    """SPEC v5.50 (e)：量測收據單一入口之每點（含列長點）之 seconds＝同 path_run_id 之逐入口計時紀錄之該入口秒數；該紀錄之
    argv＝所屬路徑 scale_probe 命令（`probe`／`row_probe`）於該規模代入後之 harness 參數（同次執行）、點之實跑記錄數＝
    scale_probe 該點 runs；呼叫次數（扣除拋例外者）≥ 1（0 呼叫不得充作量測，v5.50 (a)）；footprint 不小於該紀錄之受測行程
    結束前 sample。以問題清單回報（呼叫端單一斷言；不另綁斷言區域名，TESTREG V19 名序不變）。"""
    out: List[str] = []
    # SPEC v5.52 (b)：第二軸之軸名＝收據 row_axis（rows／timestamps／events；缺省 rows）
    row_ax = m.get("row_axis") or "rows"
    groups = [(m["points"], m.get("probe"), *_point_axis(m)),
              (m.get("row_points") or [], m.get("row_probe"), row_ax, row_ax)]
    for points, probe, unit, xkey in groups:
        for i, point in enumerate(points):
            scale = point.get(xkey)
            rec = _entry_record(point.get("scale_probe_receipt")) or {}
            hit = next((q for q in rec.get("points") or [] if q["scale"] == scale and q["unit"] == unit), {})
            record = _entry_record(point.get("record_path"))
            if record is None:
                out.append(f"{unit} 點 {i}：須引實存之逐入口計時紀錄：{point.get('record_path')!r}")
                continue
            if record.get("path_run_id") != point.get("path_run_id"):
                out.append(f"{unit} 點 {i}：紀錄 path_run_id != 點之 path_run_id")
            ids = list(point.get("path_run_ids") or [])
            if point.get("path_run_id") not in ids or len(ids) != hit.get("runs"):
                out.append(f"{unit} 點 {i}：實跑記錄數 {len(ids)} != scale_probe runs {hit.get('runs')}")
            want = [str(t).replace("{scale}", str(scale)) for t in (probe or {}).get("cmd", [])[2:]]
            if record.get("argv") != want:
                out.append(f"{unit} 點 {i}：紀錄 argv {record.get('argv')} != 量測命令 {want}（非同次執行）")
            er = (record.get("entries") or {}).get(eid)
            if not er or int(er.get("calls") or 0) - int(er.get("raised") or 0) < 1:
                out.append(f"{unit} 點 {i}：{point.get('path_run_id')} 呼叫次數 0（不得以 0 呼叫充作量測）")
                continue
            if point.get("seconds") != er.get("seconds"):
                out.append(f"{unit} 點 {i}：seconds {point.get('seconds')} != 逐入口計時 {er.get('seconds')}")
            fp = record.get("peak_footprint_bytes")
            if not (isinstance(fp, int) and fp > 0 and isinstance(point.get("peak_footprint_bytes"), int)
                    and point["peak_footprint_bytes"] >= fp):
                out.append(f"{unit} 點 {i}：footprint {point.get('peak_footprint_bytes')} 與紀錄 {fp} 不符")
    return out


def test_boundary_16_three_points_per_entry() -> None:
    """每一入口 points 長度 3（boundary_19 之兩點例外除外）；逐點秒數與峰值 RSS；x 軸同記輸入欄數與實際進段欄數；
    每一點引用實存之所屬**路徑** scale_probe 收據，其身分逐欄等於該路徑之量測命令（`probe`／列長點 `row_probe`：cmd、data、
    config；code 取收據頂層 `head` 提交；SPEC v5.50 (e)：命令不含入口 id）、峰值 RSS 等於該收據該點；seconds 等於同
    path_run_id 之逐入口計時紀錄（同次執行之 argv、實跑次數相符、呼叫次數 ≥ 1，`_entry_record_problems`；列長點同）。"""
    inv = _inventory_entries()
    receipt = _single(SCALE_BEFORE_PATTERN)
    head = str(receipt.get("head") or "")
    assert re.fullmatch(r"[0-9a-f]{40}", head), f"量測收據須記量測時之提交 head：{head!r}"
    for eid, m in receipt["entries"].items():
        pts = m["points"]
        # SPEC v5.51 (d)：主軸＝收據 axis（event_study＝events，x 為事件數；其餘 cols，x 為輸入欄數）
        unit, xkey = _point_axis(m)
        if not m.get("two_point_exception"):
            assert len(pts) == 3, f"{eid}：須 3 點，實得 {len(pts)}"
        for p in pts:
            assert isinstance(p["seconds"], (int, float)) and p["seconds"] >= 0, eid
            assert isinstance(p["peak_rss_bytes"], int) and p["peak_rss_bytes"] > 0, eid
            assert isinstance(p["input_cols"], int) and isinstance(p["stage_cols"], int), eid
            assert 0 <= p["stage_cols"] <= p["input_cols"], f"{eid}：實際進段欄數不得多於輸入欄數"
            _assert_point_bound(eid, p, p[xkey], unit, m["probe"], head)
        assert len({p[xkey] for p in pts}) == len(pts), f"{eid}：規模點重複"
        if eid in inv and "rows" in inv[eid]["input_axes"]:
            # SPEC v5.52 (b)：第二軸之軸名明示於收據 row_axis（rows；跨標的＝timestamps）
            ax = m.get("row_axis") or "rows"
            rows = m["row_points"]
            assert len(rows) == 3 and len({r[ax] for r in rows}) == 3, f"{eid}：列數成長元件須三種列長"
            for r in rows:
                _assert_point_bound(eid, r, r[ax], ax, m["row_probe"], head)
    # SPEC v5.19–v5.21 Task 0.2：點數規則（3 點；唯一例外＝帶 two_point_exception 者恰 2 點且不含 2,000 欄點）、
    # coverage_path_id／unit_axis 與清冊一致、每點帶完整 scale_vector 與峰值 Physical footprint
    # 重用上段區域名（pts＝該入口之量測記錄、p＝清冊入口），不另綁新名：既有斷言之名序不變（TESTREG V19 normalize ②）
    for eid, pts in receipt["entries"].items():
        p = inv.get(eid)
        assert not _entry_schema_problems(pts, p), f"{eid}：量測收據 schema 不合：{_entry_schema_problems(pts, p)}"
    # SPEC v5.50 (e)：每點 seconds 取自同 path_run_id 之逐入口計時紀錄（同次執行、呼叫次數 ≥ 1）；重用上段區域名（TESTREG V19）
    for eid, pts in receipt["entries"].items():
        assert not _entry_record_problems(eid, pts), f"{eid}：逐入口計時紀錄不符：{_entry_record_problems(eid, pts)}"
    # SPEC v5.51 (h)(i)：footprint＝同 path_run_id 紀錄之值；紀錄存版控路徑、大小與 sha256 相符（重用上段區域名，TESTREG V19）
    for eid, pts in receipt["entries"].items():
        assert not _record_store_problems(eid, pts), f"{eid}：紀錄存處／footprint 來源不符：{_record_store_problems(eid, pts)}"
    # SPEC v5.52 (b)：事件型入口之 scale_vector 含 events 而主軸非 events ⇒ 第二軸＝events 三點（軸名明示）；重用上段區域名
    for eid, pts in receipt["entries"].items():
        p = inv.get(eid) or {}
        if "events" in (p.get("scale_vector") or []) and pts.get("axis") != "events" \
                and "rows" not in (p.get("input_axes") or []):
            assert pts.get("row_axis") == "events" and len({r["events"] for r in pts.get("row_points") or []}) == 3, \
                f"{eid}：事件數軸須三點（row_axis＝events）"


def _entry_schema_problems(m: Mapping[str, Any], inv_entry: Optional[Mapping[str, Any]]) -> List[str]:
    """量測收據單一入口之 schema 問題清單（空＝成立；SPEC Task 0.2「驗證」與「路徑清冊」）：點數規則（3 點；唯一例外＝帶
    two_point_exception 者恰 500／1000 兩點、不含 2,000 欄點）、coverage_path_id 與 unit_axis 與清冊一致、每點（含列長點）之
    scale_vector 鍵集＝清冊 scale_vector 且值為非負整數並與點之同名欄相等、每點帶峰值 Physical footprint。拒收缺軸、單位
    歧義或 id 與清冊不一致之收據。以問題清單回報（呼叫端單一斷言；不另綁斷言區域名，TESTREG V19 名序不變）。"""
    out: List[str] = []
    unit, xkey = _point_axis(m)
    cols = sorted(p[xkey] for p in m["points"])
    want = [500, 1000] if m.get("two_point_exception") else [500, 1000, 2000]
    if unit == "events":
        # SPEC v5.51 (d)：事件數軸三相異點（不要求欄數軸；不得帶兩點例外）
        if len(set(cols)) != 3 or m.get("two_point_exception") or not all(isinstance(x, int) and x > 0 for x in cols):
            out.append(f"事件數軸規模點 {cols} 須三相異正整數且不帶兩點例外")
    elif cols != want:
        out.append(f"規模點 {cols} != {want}（兩點例外恰 500／1000 且不含 2,000 欄點；無例外者三點）")
    if inv_entry is None:
        return out + ["量測收據之入口不在清冊"]
    if m.get("coverage_path_id") != inv_entry.get("coverage_path_id"):
        out.append(f"coverage_path_id {m.get('coverage_path_id')!r} != 清冊 {inv_entry.get('coverage_path_id')!r}")
    if m.get("unit_axis") != inv_entry.get("unit_axis"):
        out.append("unit_axis != 清冊（單位歧義）")
    axes = set(inv_entry.get("scale_vector") or [])
    for i, p in enumerate(list(m["points"]) + list(m.get("row_points") or [])):
        sv = p.get("scale_vector")
        if not isinstance(sv, dict) or set(sv) != axes:
            out.append(f"點 {i}：scale_vector 鍵 {sorted(sv or {})} != 清冊 {sorted(axes)}（缺軸或多軸）")
            continue
        if not all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in sv.values()):
            out.append(f"點 {i}：scale_vector 值須為非負整數")
        out += [f"點 {i}：scale_vector.{k} {sv[k]} != 點之 {k} {p[k]}" for k in ("input_cols", "stage_cols", "rows")
                if k in sv and k in p and sv[k] != p[k]]
        fp = p.get("peak_footprint_bytes")
        if not (isinstance(fp, int) and fp > 0):
            out.append(f"點 {i}：缺峰值 Physical footprint（§B 門檻；RSS 只作輔助）")
    return out


def test_boundary_17_criteria_fields_and_rules(scale_probe: Any) -> None:
    """擬合指數、r²、判準①–⑤判定結果與依據欄齊備；r² < 0.9 或標 extrapolation_unreliable 者①依據為碼層複雜度分析；
    ②須有 lower_bound_seconds_per_unit 或碼層下限分析；各點同引一份（路徑級）scale_probe 收據，fit 與
    extrapolation_unreliable 等於 scale_probe 擬合函式對本入口三點之重算（SPEC v5.50 (e)）。"""
    for eid, m in _scale_entries().items():
        fit = m["fit"]
        assert isinstance(fit["exponent"], (int, float)) and isinstance(fit["r2"], (int, float)), eid
        assert isinstance(m["extrapolation_unreliable"], bool), eid
        sources = {str(p.get("scale_probe_receipt") or "") for p in m["points"]}
        if len(sources) == 1:
            rec = _scale_probe_receipt(next(iter(sources)))
            # SPEC v5.50 (e)：scale_probe 收據為路徑級（路徑全體之擬合）⇒ 逐入口 fit 以 scale_probe 之同一擬合函式對本入口之點
            # （x＝實際進段欄數 stage_cols、seconds、路徑級峰值 RSS；全規模＝收據 fit_full_scale）重算後比對
            # SPEC v5.51 (d)：事件數軸者 x＝事件數（收據 fit_axis）
            fkey = m.get("fit_axis") or "stage_cols"
            rec = scale_probe.fit([{"scale": p[fkey], "unit": _point_axis(m)[0], "seconds": p["seconds"],
                                    "peak_rss_bytes": p["peak_rss_bytes"]} for p in m["points"]], m["fit_full_scale"])
            assert fit["exponent"] == rec["fit"]["exponent"] and fit["r2"] == rec["fit"]["r2"], f"{eid}：fit != 收據"
            assert m["extrapolation_unreliable"] == rec["extrapolation_unreliable"], f"{eid}：可靠性旗標 != 收據"
        crit = m["criteria"]
        assert set(crit) == {"1", "2", "3", "4", "5"}, f"{eid}：判準鍵 {sorted(crit)}"
        for k, c in crit.items():
            # SPEC v5.51 (f)：判準②無原型且碼層不足以斷定者 result None＋status pending_prototype（不得固定 False）
            ok = isinstance(c["result"], bool) or (k == "2" and c["result"] is None and c.get("status") == "pending_prototype")
            assert ok and str(c["basis"]).strip(), f"{eid}：判準{k} 欄位缺"
        if fit["r2"] < scale_probe.MIN_R2 or m["extrapolation_unreliable"]:
            assert crit["1"]["basis"] == "complexity_analysis", f"{eid}：擬合不可靠時①須以碼層複雜度分析判定"
            assert str(m.get("complexity_analysis") or "").strip(), f"{eid}：缺碼層複雜度分析"
        else:
            assert crit["1"]["result"] == (fit["exponent"] > scale_probe.SUPERLINEAR_EXPONENT), f"{eid}：①判定與擬合不符"
        lb = m.get("lower_bound_seconds_per_unit")
        assert (isinstance(lb, (int, float)) and lb > 0) or str(m.get("lower_bound_analysis") or "").strip(), \
            f"{eid}：②缺下限實測或碼層下限分析"
        # SPEC v5.13 Task 0.2「記憶體量測與四項機會欄」：每入口四鍵齊備且各狀態之必填欄非空
        _assert_opportunities(eid, m)
        # SPEC v5.50 (e)：同一入口之各點來自同一路徑實跑（一份路徑級 scale_probe 收據），上列重算比對方不落空
        assert _single_probe_source(m), f"{eid}：各點須引同一份路徑 scale_probe 收據"
    # SPEC v5.51 (f)：判準②之語意（不得固定 False）——有原型下限 ⇒ 數值比；否則 False 只准硬體下限依據，待判者列頂層
    # pending_prototype（重用上段區域名，TESTREG V19）
    receipt = _single(SCALE_BEFORE_PATTERN)
    for eid, m in receipt["entries"].items():
        assert not _criterion2_problems(eid, m, receipt), f"{eid}：判準② 語意不符：{_criterion2_problems(eid, m, receipt)}"


#: SPEC v5.51 (f)：判準②之硬體下限（每單位秒數；同 scripts/icperf_scale_harness.py CRITERION2_FLOOR_SECONDS_PER_UNIT）
CRITERION2_FLOOR = 1e-10


def _criterion2_problems(eid: str, m: Mapping[str, Any], receipt: Mapping[str, Any]) -> List[str]:
    """判準②（SPEC Task 0.2 :104、v5.51 (f)）問題清單：有原型下限（> 0）⇒ result＝unit_seconds ≥ 10×下限；無原型 ⇒ result
    False 只准 basis 以 hardware_floor 起首且 unit_seconds < 10×`CRITERION2_FLOOR`，否則須 result None＋status
    pending_prototype 且列於收據頂層 pending_prototype；result True 須有原型下限（漸近階數不作 10 倍實證）。"""
    out: List[str] = []
    c = m["criteria"]["2"]
    lb, us = m.get("lower_bound_seconds_per_unit"), m.get("unit_seconds")
    pending = set(receipt.get("pending_prototype") or [])
    if isinstance(lb, (int, float)) and lb > 0:
        if not (isinstance(us, (int, float)) and c["result"] is bool(us >= 10 * lb)):
            out.append(f"有原型下限 {lb}：result {c['result']!r} != unit_seconds {us} ≥ 10×下限")
    elif c["result"] is True:
        out.append("無原型下限不得判 True（漸近階數不作 10 倍實證）")
    elif c["result"] is False:
        if not (str(c["basis"]).startswith("hardware_floor") and isinstance(us, (int, float))
                and us < 10 * CRITERION2_FLOOR):
            out.append(f"無原型而判 False 須依硬體下限（unit_seconds {us} < {10 * CRITERION2_FLOOR}）")
    elif not (c["result"] is None and c.get("status") == "pending_prototype" and eid in pending):
        out.append("無原型且不可碼層斷定 ⇒ result None、status pending_prototype 並列頂層 pending_prototype")
    return out


def _single_probe_source(m: Mapping[str, Any]) -> bool:
    """量測收據單一入口之各點恰引同一份（非空）scale_probe 收據（SPEC v5.50 (e)：同一路徑實跑）。"""
    sources = {str(p.get("scale_probe_receipt") or "") for p in m["points"]}
    return len(sources) == 1 and "" not in sources


def _filled(v: Any) -> bool:
    return v is not None and (not isinstance(v, str) or bool(v.strip())) and v != {} and v != []


def _assert_opportunities(eid: str, m: Mapping[str, Any]) -> None:
    """opportunities＝{time|memory|precision|file_size: {status, evidence, before, after, downstream, user_ruling}}；
    none＝無機會須附理由（evidence）；planned 須 evidence；needs_user（改值者）須改前改後實測與受影響之下游判定；
    done 須改前改後同工具量測（SPEC Task 0.2）。"""
    opp = m.get("opportunities")
    assert isinstance(opp, dict) and set(opp) == OPPORTUNITY_KEYS, \
        f"{eid}：opportunities 須恰為 {sorted(OPPORTUNITY_KEYS)}，實得 {sorted(opp or {})}"
    for key, o in opp.items():
        assert isinstance(o, dict) and OPPORTUNITY_FIELDS <= set(o), f"{eid}/{key}：缺欄 {sorted(OPPORTUNITY_FIELDS - set(o or {}))}"
        assert o["status"] in OPPORTUNITY_STATUSES, f"{eid}/{key}：status {o['status']!r} 非法"
        assert _filled(o["evidence"]), f"{eid}/{key}：缺 evidence（none 須附無機會之理由）"
        if o["status"] in ("needs_user", "done"):
            assert _filled(o["before"]) and _filled(o["after"]), f"{eid}/{key}：{o['status']} 須改前改後實測"
        if o["status"] == "needs_user":
            assert _filled(o["downstream"]), f"{eid}/{key}：needs_user（改值）須受影響之下游判定"


def test_boundary_18_scale_points_within_budget() -> None:
    """規模點 ⊆ 500／1000／2000 欄；三點推估逾預算者收據記縮列長或元件層級計時。"""
    receipt = _single(SCALE_BEFORE_PATTERN)
    budget = receipt["budget_seconds"]
    assert isinstance(budget, (int, float)) and 0 < budget <= BUDGET2_UPPER_SECONDS
    for eid, m in receipt["entries"].items():
        cols = {p["input_cols"] for p in m["points"]}
        # SPEC v5.51 (d)：事件數軸者不以欄數軸規模點判（x＝事件數，由 boundary_16 `_entry_schema_problems` 驗三相異點）
        assert _point_axis(m)[0] == "events" or cols <= SCALE_POINTS, f"{eid}：規模點 {sorted(cols)} 超出 500／1000／2000"
        if m["projected_seconds"] > budget:
            red = m.get("reduction") or {}
            assert red.get("kind") in ("row_length", "component_timing") and str(red.get("note") or "").strip(), \
                f"{eid}：推估逾預算須記縮列長或元件層級計時"


def _projected_2000_seconds(points: Sequence[Mapping[str, Any]]) -> float:
    """以 500／1000 兩點推估 2000 欄耗時（線性外推與兩點冪次外推取大，保守）；測試自算，不引收據自述值。"""
    by = {p["input_cols"]: float(p["seconds"]) for p in points}
    s5, s10 = by[500], by[1000]
    linear = 2.0 * s10 - s5
    power = s10 * s10 / s5 if s5 > 0 and s10 > 0 else linear
    return max(linear, power)


def test_boundary_19_over_ten_minutes_two_points_annotated() -> None:
    """SPEC v5.51 (g)：收據頂層合計推估逾 budget_seconds 時，500／1000 兩點推估 2000 欄逾 10 分鐘之元件 ⇒ 須帶
    two_point_exception、收據不得含其 2000 欄點、附碼層複雜度分析（boundary_16 之唯一例外）；未逾預算或未逾 10 分鐘者不得帶
    例外且須 500／1000／2000 三點。事件數軸（v5.51 (d)）者不適用欄數兩點例外。"""
    receipt = _single(SCALE_BEFORE_PATTERN)
    over_budget = bool(receipt.get("budget_exceeded"))
    for eid, m in _scale_entries().items():
        if _point_axis(m)[0] == "events":
            assert not m.get("two_point_exception"), f"{eid}：事件數軸不得帶兩點例外"
            continue
        exc = m.get("two_point_exception")
        cols = sorted(p["input_cols"] for p in m["points"])
        assert 500 in cols and 1000 in cols, f"{eid}：須含 500／1000 欄點"
        projected = _projected_2000_seconds(m["points"])
        if projected > TWO_POINT_SECONDS and over_budget:
            assert exc, f"{eid}：2000 欄推估 {projected:.0f} 秒逾 10 分鐘，須帶 two_point_exception"
            assert cols == [500, 1000], f"{eid}：兩點例外之收據不得含 2000 欄點（實得 {cols}）"
            assert exc["projected_2000_seconds"] > TWO_POINT_SECONDS, f"{eid}：例外之推估值須逾 10 分鐘"
            assert str(m.get("complexity_analysis") or "").strip(), f"{eid}：兩點例外須附碼層複雜度分析"
        else:
            assert not exc, f"{eid}：2000 欄推估 {projected:.0f} 秒未逾 10 分鐘，不得帶 two_point_exception"
            assert cols == [500, 1000, 2000], f"{eid}：未逾 10 分鐘者須三點（實得 {cols}）"
    # SPEC v5.51 (g)：頂層合計推估＝各路徑 scale_probe 收據逐點 seconds × runs 之和（測試自算，不引收據自述值），
    # budget_exceeded＝其 > budget_seconds
    total = sum(float(q.get("seconds") or 0.0) * max(int(q.get("runs") or 1), 1)
                for r in (receipt.get("runs") or {}).values() for q in _scale_probe_receipt(r["receipt"])["points"])
    assert abs(float(receipt["total_projected_seconds"]) - total) <= 1e-6 * max(total, 1.0), "合計推估 != scale_probe 收據重算"
    assert receipt["budget_exceeded"] is (total > float(receipt["budget_seconds"])), "budget_exceeded 與合計推估不符"


def test_boundary_20_rss_meter_and_chunk_cap_recorded() -> None:
    """量測器（scale_probe 行程樹 RSS）與取樣間隔記於收據；2D 核心依欄分塊之工作記憶體上限值寫入收據。"""
    receipt = _single(SCALE_BEFORE_PATTERN)
    meter = receipt["meter"]
    assert meter["tool"] == "scripts/scale_probe.py"
    assert meter["rss_scope"] == "process_tree"
    assert isinstance(meter["sample_interval_seconds"], (int, float)) and meter["sample_interval_seconds"] > 0
    cap = receipt["chunk_cap"]
    assert isinstance(cap["bytes"], int) and cap["bytes"] > 0
    assert str(cap["basis"]).strip()
    # SPEC v5.13／v5.17 §B、Task 0.2：門檻指標＝Physical footprint（同 measure_ic_footprint.sh 之工具）；只沿用工具，不沿用
    # 其取樣停止與超標終止（受測行程結束前持續取樣、不因超標中止）
    meter = receipt["meter"]["footprint"]
    assert meter["tool"] == FOOTPRINT_TOOL, f"footprint 量測工具 {meter['tool']!r} != {FOOTPRINT_TOOL!r}"
    assert meter["sampling"] == "until_target_exit", "footprint 須於受測行程結束前持續取樣（不設取樣停止點）"
    assert meter["terminate_target_on_exceed"] is False, "footprint 超標不得中止受測行程（照記為超標點）"


# ── mutation（改壞入口行為 ⇒ 對應邊界翻轉） ─────────────────────────────────────────────────────────────


def test_mutation_capture_drops_replace_destination(fb: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """捕獲改為不記 os.replace 目的地 ⇒ boundary_06 翻轉。"""
    assert _boundary_06_holds(fb, tmp_path / "orig")
    monkeypatch.setattr(fb, "AUDIT_EVENTS", tuple(e for e in fb.AUDIT_EVENTS if e != "os.replace"))
    assert not _boundary_06_holds(fb, tmp_path / "mutant")


def _intersection_only(frozen_files: Mapping[str, Any], current_files: Mapping[str, Any]) -> set:
    return set(frozen_files) & set(current_files)


def test_mutation_compare_intersection_only(fb: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """比對改為只比兩集合交集 ⇒ boundary_12 翻轉。"""
    assert _boundary_12_holds(fb, tmp_path / "orig")
    monkeypatch.setattr(fb, "compared_paths", _intersection_only)
    assert not _boundary_12_holds(fb, tmp_path / "mutant")


def _count_only_cover_check(inventory: Mapping[str, Any], scale: Mapping[str, Any]) -> List[str]:
    needed = [e["id"] for e in inventory["entries"] if e["measure"]]
    return [] if len(scale["entries"]) >= len(needed) else sorted(needed)


def test_mutation_inventory_cover_check_disabled(fb: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """覆蓋檢查改為不比 id 集合（只比筆數）⇒ boundary_15 之覆蓋判定翻轉。邊界輸入：最小清冊與量測收據。"""
    inventory = {"entries": [{"id": "m.a:f", "measure": True}, {"id": "m.b:g", "measure": True},
                             {"id": "m.c:h", "measure": False}]}
    scale = {"entries": {"m.a:f": {"points": []}, "m.b:g": {"points": []}}}
    assert fb.uncovered_entries(inventory, scale) == []
    assert _cover_check_catches_swapped_id(fb, inventory, scale)
    monkeypatch.setattr(fb, "uncovered_entries", _count_only_cover_check)
    assert not _cover_check_catches_swapped_id(fb, inventory, scale)


def _sha(arr: np.ndarray) -> str:
    return hashlib.sha256(arr.tobytes()).hexdigest()


def _boundary02_survivors(root: Path, names: Sequence[str]) -> Dict[str, Any]:
    """邊界輸入：tmp 下之 cwd 根寫一份倖存者檔（feature_names＝names），回 oracle_runs 所需之 "written"／"roots"。"""
    key = "data_cache/reports/ic_survivors_ic_gatekeeper.json"
    path = root / "cwd" / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"feature_names": list(names)}), encoding="utf-8")
    return {"written": {key}, "roots": {"cwd": str((root / "cwd").resolve()), "iso": str((root / "iso").resolve())}}


def _boundary02_inputs(root: Path, sources: bool = False) -> Tuple[Any, Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """boundary_02 之最小輸入（邊界輸入：記憶體內之逐特徵來源與凍結檔、tmp 下之倖存者檔，不涉資料值）：
    (fb, oracle_runs, golden)。`sources`＝False ⇒ "frame" 形狀（通用 DataFrame 表）；True ⇒ SPEC §G 之 IC 報告形狀
    （summary_table＝list[dict] "rows"、quantile_returns／turnover_analysis "by_key"，turnover 只含 f_a＝成員依請求而變）。"""
    digest = {"sha256": "a" * 64, "nan_mask_sha256": "b" * 64}
    if sources:
        raw: Dict[str, Any] = {
            "summary_table": [{"feature_name": "f_a", "ic_mean": 0.1, "p_value": 0.5},
                              {"feature_name": "f_b", "ic_mean": 0.2, "p_value": float("nan")}],
            "quantile_returns": {"f_a": {"q1": [0.1, float("nan")], "long_short_spread": 0.2},
                                 "f_b": {"q1": [0.3, 0.4], "long_short_spread": float("nan")}},
            "coverage_analysis": {},
            "turnover_analysis": {"f_a": {"turnover": np.float64(0.3)}}}
        rec_feats: Dict[str, Dict[str, Any]] = {}
        for row in raw["summary_table"]:
            for c, v in row.items():
                if c != "feature_name":
                    rec_feats.setdefault(row["feature_name"], {})[f"/summary_table/{c}"] = _oracle_digest(v)
        for src in ("quantile_returns", "turnover_analysis"):
            for f, sub in raw[src].items():
                rec_feats[f][f"/{src}"] = _oracle_digest(sub)
        frozen_feats = {f: {"/summary_table/ic_mean": dict(digest), "/summary_table/p_value": dict(digest),
                            "/quantile_returns": dict(digest)} for f in ("f_a", "f_b", "f_c")}
        frozen_feats["f_c"]["/turnover_analysis"] = dict(digest)
        tables: Dict[str, str] = dict(FEATURE_SOURCES)
    else:
        df = pd.DataFrame({"ic": [0.1, 0.2], "p": [0.5, np.nan]}, index=["f_a", "f_b"])
        rec_feats = {f: {f"/summary/{c}": {"sha256": _sha(df.loc[[f], c].to_numpy()),
                                            "nan_mask_sha256": _sha(np.isnan(df.loc[[f], c].to_numpy().astype("float64")))}
                         for c in df.columns} for f in df.index}
        frozen_feats = {f: {"/summary/ic": dict(digest), "/summary/p": dict(digest)} for f in ("f_a", "f_b", "f_c")}
        raw = {"summary": df, "sel": ["f_a"]}
        tables = {"/summary": "frame"}
    labels = {f: {"skipped_all_nan": False, "label_sha256": "c" * 64, "q": 5, "q_insufficient": False}
              for f in frozen_feats}
    items: Dict[str, Any] = {n: {"features": copy.deepcopy(frozen_feats)} for n in FEATURE_ITEMS}
    for n in SURVIVOR_ITEMS:
        items[n]["selected"] = ["f_a"]
    for n in ("ic_report", "stage5_subset"):
        items[n]["pit_labels"] = copy.deepcopy(labels)
    runs = {n: {"record": {"features": copy.deepcopy(rec_feats), "selected": ["f_a"]}, "raw": copy.deepcopy(raw),
                **_boundary02_survivors(root / n, ["f_a"])} for n in SURVIVOR_ITEMS}
    fake_fb = type("FakeFb", (), {
        "feature_tables": staticmethod(lambda name: dict(tables)),
        "selected_pointer": staticmethod(lambda name: None if sources else "/sel")})()
    return fake_fb, runs, {"items": items}


def test_mutation_boundary_02_oracle_checks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """直接驅動 boundary_02（r12 CODEX-R12-P1-02／-P1-03）：相符者綠；同請求記錄之值 sha256 改壞、凍結檔某特徵缺一欄、
    oracle 特徵不在凍結檔、逐特徵表非全成員（成員依請求而變）、選欄通過集合不同 ⇒ 各自紅。SPEC v5.8 §G 之 IC 報告形狀
    （"rows"／"by_key"）另驗：相符（含 "by_key" 成員依請求而變）者綠；by_key 子樹摘要改壞、rows 欄值摘要改壞、
    feature_name 重複、凍結檔缺 oracle 出現之來源、凍結檔含 SPEC 外之來源、無倖存者檔、倖存者與記錄不同 ⇒ 各自紅。"""
    module = sys.modules[__name__]

    def run(mutate: Any, sources: bool = False) -> None:
        fake_fb, runs, golden = _boundary02_inputs(tmp_path / ("src" if sources else "frame"), sources)
        mutate(runs, golden)
        monkeypatch.setattr(module, "_golden", lambda: golden)
        test_boundary_02_frozen_baseline_content_complete(fake_fb, runs)

    run(lambda r, g: None)
    mutants = [
        lambda r, g: r["ic_report"]["record"]["features"]["f_a"]["/summary/ic"].update(sha256="0" * 64),
        lambda r, g: g["items"]["ic_report"]["features"]["f_b"].pop("/summary/p"),
        lambda r, g: g["items"]["event_report"]["features"].pop("f_b"),
        lambda r, g: r["ic_report"]["raw"].update(passed=pd.DataFrame({"x": [1.0]}, index=["f_a"])) or None,
        lambda r, g: r["event_report"]["record"].update(selected=["f_b"]),
    ]
    for i, mutate in enumerate(mutants):
        fake_fb, runs, golden = _boundary02_inputs(tmp_path / f"m{i}")
        mutate(runs, golden)
        if i == 3:  # 第二張逐特徵表只列 f_a（成員依請求而變）
            fake_fb = type("FakeFb2", (), {
                "feature_tables": staticmethod(lambda name: {"/summary": "frame", "/passed": "frame"}),
                "selected_pointer": staticmethod(lambda name: "/sel" if name in ("ic_report", "event_report") else None)})()
            runs["ic_report"]["record"]["features"]["f_a"]["/passed/x"] = {
                "sha256": _sha(np.array([1.0])), "nan_mask_sha256": _sha(np.array([False]))}
        monkeypatch.setattr(module, "_golden", lambda g=golden: g)
        with pytest.raises(AssertionError):
            test_boundary_02_frozen_baseline_content_complete(fake_fb, runs)
    run(lambda r, g: None, sources=True)
    source_mutants = [
        lambda r, g: r["ic_report"]["record"]["features"]["f_b"]["/quantile_returns"].update(nan_mask_sha256="0" * 64),
        lambda r, g: r["event_report"]["raw"]["quantile_returns"]["f_a"].update(long_short_spread=0.25),
        lambda r, g: r["ic_report"]["raw"]["summary_table"][1].update(p_value=0.0),
        lambda r, g: r["ic_report"]["raw"]["summary_table"].append({"feature_name": "f_a", "ic_mean": 0.1, "p_value": 0.5}),
        lambda r, g: [v.pop("/turnover_analysis", None) for v in g["items"]["ic_report"]["features"].values()],
        lambda r, g: g["items"]["event_report"]["features"]["f_c"].update(
            {"/bogus_analysis": {"sha256": "a" * 64, "nan_mask_sha256": "b" * 64}}),
        lambda r, g: r["ic_report"].update(written=set()),
        lambda r, g: r["event_report"]["record"].update(selected=["f_b"]),
    ]
    for mutate in source_mutants:
        with pytest.raises(AssertionError):
            run(mutate, sources=True)


def test_boundary_23_heavy_tests_require_shared_watchdog() -> None:
    """標 slow 或 requires_kline 而環境無 WATCHDOG_STACK_FILE ⇒ 判定未經監看；有則放行；非重型測試不受限（r13
    CODEX-R13-P1-01）。邊界輸入：記憶體內之標記與環境。"""
    assert _watchdog_missing(["slow"], {})
    assert _watchdog_missing(["requires_kline", "parametrize"], {"WATCHDOG_STACK_FILE": ""})
    assert not _watchdog_missing(["slow", "requires_kline"], {"WATCHDOG_STACK_FILE": "/tmp/x.log.stacks"})
    assert not _watchdog_missing([], {})
    assert not _watchdog_missing(["parametrize"], {})


def test_mutation_boundary_16_receipt_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """直接驅動 boundary_16（r12 CODEX-R12-P1-03）：清冊與量測收據以記憶體內最小輸入置換讀取函式；收據身分相符者綠；
    路徑命令含入口 id（SPEC v5.50 (e)）、錯 entrypoint、錯 argv、量測碼與 head 不同、逐入口計時紀錄不符 ⇒ boundary_16 紅。
    身分以 run_receipt_identity 對
    repo 內已提交之 scripts/scale_probe.py 產生（不跑量測）。"""
    module = sys.modules[__name__]
    rid = _load("icperf_gate_receipt_identity", REPO / "scripts" / "run_receipt_identity.py")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    eid = "m.a:f"
    # SPEC v5.50 (e)：量測命令＝路徑命令（不含入口 id）
    probe = {"cmd": ["venv/bin/python", "scripts/scale_probe.py", "--path", "p1"], "data": [], "config": []}
    match = rid.compute_match("scripts/scale_probe.py", probe["cmd"], [], [], [])
    match["code_sha256"] = _sha_at_commit(head, ["scripts/scale_probe.py"])
    match["config_sha256"] = _sha_at_commit(head, [])

    def run(entry_probe: Mapping[str, Any], receipt_match: Mapping[str, Any], mutate: Any = None,
            mutate_record: Any = None) -> None:
        pts = [{"input_cols": n, "stage_cols": n, "seconds": 1.0 * n, "peak_rss_bytes": 1000 + n,
                "peak_footprint_bytes": 2000 + n, "scale_vector": {"input_cols": n, "stage_cols": n},
                "scale_probe_receipt": "r.json", "path_run_id": f"p1.cols{n}", "path_run_ids": [f"p1.cols{n}"],
                "record_path": f"{RECORDS_ROOT}/rec-{n}.json"} for n in (500, 1000, 2000)]
        probe_rec = {"identity": {"match": dict(receipt_match), "meta": {"producer": "scripts/scale_probe.py"}},
                     "points": [{"scale": p["input_cols"], "unit": "cols", "seconds": 9.0 * p["seconds"], "runs": 1,
                                 "peak_rss_bytes": p["peak_rss_bytes"]} for p in pts]}
        records = {p["record_path"]: {"path_run_id": p["path_run_id"], "argv": [str(t) for t in entry_probe["cmd"][2:]],
                                      "peak_footprint_bytes": p["peak_footprint_bytes"],
                                      "entries": {eid: {"calls": 3, "raised": 0, "seconds": p["seconds"]}}} for p in pts}
        # SPEC v5.51 (h)(i)：紀錄存於 RECORDS_ROOT 之下、點記其大小／sha256 與 footprint 來源（`_record_store_problems`）
        for p in pts:
            raw = json.dumps(records[p["record_path"]], sort_keys=True).encode("utf-8")
            p.update(record_bytes=len(raw), record_sha256=hashlib.sha256(raw).hexdigest(),
                     footprint_source=f"harness_record:{p['path_run_id']}")
        if mutate_record is not None:
            mutate_record(records[f"{RECORDS_ROOT}/rec-1000.json"])
        files = {"r.json": probe_rec, **records}
        monkeypatch.setattr(module, "_record_raw", lambda rp: (
            json.dumps(files[rp], sort_keys=True).encode("utf-8") if rp in files else None))
        axis = {"axes": ["stage_cols"], "function": "stage_cols"}
        scale = {"head": head, "entries": {eid: {"probe": dict(entry_probe), "row_probe": None, "points": pts,
                                                 "coverage_path_id": "cp-m.a:f", "unit_axis": dict(axis)}}}
        inventory = {eid: {"input_axes": ["cols"], "coverage_path_id": "cp-m.a:f", "unit_axis": dict(axis),
                           "scale_vector": ["input_cols", "stage_cols"]}}
        if mutate is not None:
            mutate(scale["entries"][eid], inventory[eid])
        monkeypatch.setattr(module, "_inventory_entries", lambda: inventory)
        monkeypatch.setattr(module, "_single", lambda pattern: scale)
        monkeypatch.setattr(module, "_scale_probe_receipt", lambda path_str: probe_rec)
        monkeypatch.setattr(module, "_entry_record", lambda path_str: files.get(str(path_str)))
        test_boundary_16_three_points_per_entry()

    run(probe, match)
    bad = [
        ({**probe, "cmd": ["venv/bin/python", "scripts/scale_probe.py", "--entry", eid]}, match),  # 路徑命令含入口 id
        (probe, {**match, "entrypoint": "scripts/run_watched.py"}),  # 錯入口檔
        (probe, {**match, "target_argv": rid.normalize_argv(probe["cmd"] + ["--cols", "9"])}),  # 錯 argv
        (probe, {**match, "code_sha256": "0" * 64}),  # 量測碼與 head 提交不同
    ]
    for p, m in bad:
        with pytest.raises(AssertionError):
            run(p, m)
    # SPEC v5.19–v5.21 Task 0.2 收據 schema：缺軸、多軸、scale_vector 與點不符、單位歧義、coverage_path_id 與清冊不一致、
    # 缺 footprint、兩點例外仍含 2,000 欄點、無例外而只兩點 ⇒ boundary_16 紅
    schema_bad = [
        lambda e, i: e["points"][0]["scale_vector"].pop("stage_cols"),
        lambda e, i: e["points"][1]["scale_vector"].update(rows=500),
        lambda e, i: e["points"][2]["scale_vector"].update(stage_cols=1999),
        lambda e, i: e.update(unit_axis={"axes": ["input_cols"], "function": "input_cols"}),
        lambda e, i: e.update(coverage_path_id="cp-other"),
        lambda e, i: e["points"][0].pop("peak_footprint_bytes"),
        lambda e, i: e.update(two_point_exception={"projected_2000_seconds": 900.0}),
        lambda e, i: e["points"].pop(),
    ]
    p, m = probe, match  # 重用上段區域名：既有斷言之名序不變（TESTREG V19 normalize ②）
    for mutate in schema_bad:
        with pytest.raises(AssertionError):
            run(p, m, mutate)
    # SPEC v5.50 (e)：逐入口計時紀錄——點之 seconds 與紀錄不符、紀錄 0 呼叫（含全數拋例外）、紀錄非同次執行（argv 不符）、
    # 點之 path_run_id 與紀錄不符、紀錄缺、實跑記錄數與 scale_probe runs 不符、footprint 小於紀錄 ⇒ boundary_16 紅
    record_bad = [
        lambda r: r["entries"][eid].update(seconds=1.5),
        lambda r: r["entries"][eid].update(calls=0),
        lambda r: r["entries"][eid].update(raised=3),
        lambda r: r.update(argv=["--path", "p2"]),
        lambda r: r.update(path_run_id="other"),
        lambda r: r["entries"].pop(eid),
        lambda r: r.update(peak_footprint_bytes=10 ** 9),
    ]
    for mutate in record_bad:
        with pytest.raises(AssertionError):
            run(p, m, None, mutate)
    for mutate in (lambda e, i: e["points"][1].update(record_path="missing.json"),
                   lambda e, i: e["points"][1].update(path_run_ids=["p1.cols1000", "p1.cols1000b"])):
        with pytest.raises(AssertionError):
            run(p, m, mutate)


def test_small_request_prefers_frozen_survivors(fb: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """boundary_01／02 之小規模 oracle 請求：`prefer`（凍結之倖存者）中屬該 run 者排序後在前、餘額依欄名排序補足；不在該
    run 之名不入；未給 `prefer` ⇒ 與原行為相同（排序後前 n 個；Task 0.3 收據擷取依此）。"""
    pool = ["f05", "f01", "f04", "f02", "f03"]
    monkeypatch.setattr(fb, "_run_feature_names", lambda request: list(pool))
    req = {"kind": "ic_page"}
    pick = lambda **kw: fb.small_request("ic_report", req, 3, **kw)["feature_filter"]["include_features"]
    assert pick() == ["f01", "f02", "f03"]
    assert pick(prefer=["f05", "zz", "f04"]) == ["f04", "f05", "f01"]
    assert pick(prefer=["f05", "f04", "f03", "f02"]) == ["f02", "f03", "f04"]


def test_runs_inventory_lists_cards_and_cardless_dirs(tmp_path: Path) -> None:
    """SPEC v5.45 §G (2) ②：`scripts/runs_inventory.py` 只列不刪——有說明卡之工作目錄讀出入口／用途／何時可刪，runs/ 下
    無任何說明卡之第一層目錄列為無說明卡（card None）；列表後檔案仍在。"""
    spec = importlib.util.spec_from_file_location("runs_inventory", REPO / "scripts" / "runs_inventory.py")
    inv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inv)
    runs = tmp_path / "runs"
    (runs / "icperf" / "w1").mkdir(parents=True)
    (runs / "icperf" / "w1" / "README.txt").write_text("入口：x volprobe\n用途：測試\n何時可刪：推送後\n", encoding="utf-8")
    (runs / "icperf" / "w1" / "a.bin").write_bytes(b"0" * 10)
    (runs / "loose").mkdir()
    rows = {Path(r["path"]).relative_to(runs).as_posix(): r for r in inv.entries(runs)}
    assert sorted(rows) == ["icperf/w1", "loose"]
    assert rows["icperf/w1"]["card"]["用途"] == "測試" and rows["icperf/w1"]["size"] >= 10
    assert rows["loose"]["card"] is None
    assert (runs / "icperf" / "w1" / "a.bin").is_file()


# ── Task 0.2 量測工具（scripts/icperf_scale_harness.py；SPEC v5.50 (a)(b)(e)）：秒級契約，不跑量測 ─────────────────


@pytest.fixture(scope="module")
def harness() -> Any:
    return _load("icperf_gate_scale_harness", REPO / "scripts" / "icperf_scale_harness.py")


_TOY_SRC = '''
def f(x):
    return x + 1


class K:
    @staticmethod
    def s(x):
        return x * 2

    @classmethod
    def c(cls, x):
        return x * 3

    def m(self, x):
        return x * 4
'''
_TOY_USER = '''
from icperf_toy_src import f, K


def call_early():
    return f(1)


def call_delayed():
    from icperf_toy_src import f as g
    return g(2)


def call_methods():
    return K.s(1) + K().s(1) + K.c(1) + K().m(1)
'''
TOY_IDS = ("icperf_toy_src:f", "icperf_toy_src:K.s", "icperf_toy_src:K.c", "icperf_toy_src:K.m")


def test_task02_rebind_all_counts_early_bound_and_delayed_calls(harness: Any, tmp_path: Path,
                                                                monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC v5.50 (a)：`from X import f` 早綁之呼叫端、函式內延遲 import、類別上之 staticmethod／classmethod／方法，經
    `rebind_all` 後皆計數 ≥ 1（同一 wrapper）；對照組＝只換定義模組屬性（v5.49）時早綁呼叫端計數 0；`restore` 後還原。"""
    (tmp_path / "icperf_toy_src.py").write_text(_TOY_SRC, encoding="utf-8")
    (tmp_path / "icperf_toy_user.py").write_text(_TOY_USER, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    for name in ("icperf_toy_src", "icperf_toy_user"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    src = importlib.import_module("icperf_toy_src")
    user = importlib.import_module("icperf_toy_user")
    seen: List[int] = []
    orig = src.f
    src.f = lambda x: seen.append(x) or orig(x)  # v5.49 之做法：只換定義模組屬性
    assert user.call_early() == 2 and seen == [], "對照組：早綁之呼叫端不經定義模組屬性（本測試之分辨力）"
    src.f = orig
    targets = harness.resolve_targets(TOY_IDS)
    assert {t.kind for t in targets.values()} == {"function", "staticmethod", "classmethod"}
    rec = harness.Recorder(heartbeat=False)
    binding = harness.rebind_all({eid: t.func for eid, t in targets.items()}, rec)
    try:
        assert user.call_early() == 2 and user.call_delayed() == 3 and user.call_methods() == 2 + 2 + 3 + 4
        assert {eid: rec.stats[eid].calls for eid in TOY_IDS} == {
            "icperf_toy_src:f": 2, "icperf_toy_src:K.s": 2, "icperf_toy_src:K.c": 1, "icperf_toy_src:K.m": 1}
        assert binding.counts["icperf_toy_src:f"] >= 2, "定義模組與早綁之呼叫端模組皆須重綁"
        assert user.f is src.f and getattr(user.f, "__icperf_t02_entry__", None) == "icperf_toy_src:f"
        assert isinstance(vars(src.K)["s"], staticmethod) and isinstance(vars(src.K)["c"], classmethod)
        assert rec.stats["icperf_toy_src:f"].seconds >= 0 and rec.stats["icperf_toy_src:f"].outer_calls == 2
    finally:
        binding.restore()
    assert user.f is orig and src.f is orig and vars(src.K)["s"].__func__ is targets["icperf_toy_src:K.s"].func
    user.call_early()
    assert rec.stats["icperf_toy_src:f"].calls == 2, "restore 後不得再計數"


def test_task02_rebind_all_factor_combiner_delayed_import(harness: Any) -> None:
    """r61 施工注意（codex）：`factor_combiner.py` 函式內延遲 `from momentum.Analysis.marginal_ic import ...` 於重綁後取到
    清冊入口 `normal_scores` 之 wrapper（以 AST 取出該延遲 import 原句執行；原句不存在即紅，提醒本測試前提改變）。"""
    import momentum.Analysis.factor_combiner  # noqa: F401 — 先載入呼叫端模組
    import momentum.Analysis.marginal_ic as mi

    tree = ast.parse((REPO / "momentum" / "Analysis" / "factor_combiner.py").read_text(encoding="utf-8"))
    lazy = [n for fn in ast.walk(tree) if isinstance(fn, ast.FunctionDef) for n in ast.walk(fn)
            if isinstance(n, ast.ImportFrom) and n.module == "momentum.Analysis.marginal_ic"]
    assert lazy, "factor_combiner.py 之函式內延遲 import 已不存在（本測試前提改變）"
    assert any("normal_scores" in {a.asname or a.name for a in n.names} for n in lazy)
    eid = "momentum.Analysis.marginal_ic:normal_scores"
    target = harness.resolve_target(eid)
    binding = harness.rebind_all({eid: target.func}, harness.Recorder(heartbeat=False))
    got: List[Any] = []
    try:
        for node in lazy:
            ns: Dict[str, Any] = {}
            exec(compile(ast.Module(body=[node], type_ignores=[]), "<factor_combiner lazy import>", "exec"), ns)
            got += [v for k, v in ns.items() if k == "normal_scores"]
    finally:
        binding.restore()
    assert got and all(getattr(v, "__icperf_t02_entry__", None) == eid for v in got)
    assert mi.normal_scores is target.func


def test_task02_inventory_branch_cells_cover_measured(fb: Any, harness: Any) -> None:
    """定稿清冊（scripts/icperf_path_inventory.json）：schema 成立；每一 measure=true 入口之 branch_cell 為 harness 之路徑或
    直接呼叫格（無未歸屬者）；run_ic_first 外層不量且附碼證（SPEC v5.50 (c)）；scale_vector 軸 ⊆ 共用 schema。"""
    inv = json.loads((REPO / "scripts" / "icperf_path_inventory.json").read_text(encoding="utf-8"))
    assert fb.inventory_problems(inv) == []
    plan = harness.coverage_plan(inv)
    assert "__uncovered__" not in plan and set(plan) <= set(harness.RUNNERS)
    assert sum(len(v) for v in plan.values()) == sum(1 for e in inv["entries"] if e["measure"])
    outer = next(e for e in inv["entries"] if e["id"].endswith(":FeatureFactory.run_ic_first"))
    assert outer["measure"] is False and outer["evidence"].endswith("feature_factory.py:2809")
    assert all(set(e["scale_vector"]) <= SCALE_VECTOR_KEYS and set(e["input_axes"]) <= INPUT_AXES for e in inv["entries"])


T02_E1 = "m.k:Keyed.per_column"
T02_E2 = "m.n:plain"


def _t02_inventory() -> Dict[str, Any]:
    base = {"ic_page": True, "ic_first": False, "no_measure_reason": None, "evidence": "m/k.py:1"}
    return {"entries": [
        {**base, "id": T02_E1, "stage": "5", "input_axes": ["cols", "rows"], "loop": "per_column", "measure": True,
         "branch_cell": "ic_page_default", "coverage_path_id": "cp-1",
         "unit_axis": {"axes": ["stage_cols", "rows"], "function": "stage_cols*rows"}, "scale_vector": ["rows", "stage_cols"]},
        {**base, "id": T02_E2, "stage": "0", "input_axes": ["cols"], "loop": "none", "measure": True,
         "branch_cell": "ic_page_default", "coverage_path_id": "cp-2",
         "unit_axis": {"axes": ["input_cols"], "function": "input_cols^2"}, "scale_vector": ["input_cols"]},
        {**base, "id": "m.x:skip", "stage": "0", "input_axes": ["rows"], "loop": "none", "measure": False,
         "branch_cell": None, "no_measure_reason": "常數時間", "coverage_path_id": "cp-3",
         "unit_axis": {"axes": ["rows"], "function": "1"}, "scale_vector": ["rows"]}]}


def _t02_runs(exp: float = 1.0, dup: int = 0, intervals: Optional[List[List[float]]] = None,
              progress: Optional[List[float]] = None, calls2: int = 3, raised2: int = 0, e2_decreasing: bool = False,
              unrequested: bool = False, e2_per_col: float = 0.002) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """合成之路徑實跑（記錄形狀同 icperf_scale_harness.run_one 寫出者）：E1＝輸入鍵入口、秒數 ∝ n^exp；E2＝非鍵入口。"""
    points, records = [], {}
    for n in (500, 1000, 2000):
        def er(keyed: bool, sec: float) -> Dict[str, Any]:
            return {"calls": 3, "raised": 0, "seconds": sec, "max_rows": 400, "max_cols": n, "keyed": keyed,
                    "n_keys": 3 if keyed else None, "duplicate_keys": dup if keyed else None,
                    "max_key_count": (2 if dup else 1) if keyed else None, "duplicate_examples": [],
                    "computed_columns": [f"c{i}" for i in range(n)] if keyed else None,
                    "long_intervals": intervals or [], "max_call_seconds": 0.5}
        e2_sec = 0.002 * (3000 - n) if e2_decreasing else e2_per_col * n
        records[n] = [{"path_run_id": f"ic.cols{n}", "wall_seconds": 10.0, "peak_footprint_bytes": 5000 + n,
                       "facts": {"input_cols": n, "rows": 500, "survivors": 20, "requested_columns": None},
                       "progress_times": list(progress or []), "_record_path": f"rec-{n}.json",
                       "entries": {T02_E1: er(True, 0.001 * n ** exp),
                                   T02_E2: {**er(False, e2_sec), "calls": calls2, "raised": raised2}}}]
        points.append({"scale": n, "unit": "cols", "runs": 1, "seconds": 11.0, "peak_rss_bytes": 10 ** 8 + n})
    cmd = ["venv/bin/python", "scripts/icperf_scale_harness.py", "run", "ic_page_default", "--scale", "{scale}"]
    runs = {("ic_page_default", "cols"): {"probe": {"cmd": cmd, "data": [], "config": []}, "receipt_path": "r.json",
                                          "receipt": {"points": points, "projection": {"scale": 209053}},
                                          "records": records}}
    if unrequested:
        rec = {"path_run_id": "post.cols500", "wall_seconds": 1.0, "peak_footprint_bytes": 1,
               "facts": {"input_cols": 500, "requested_columns": ["c0"]}, "progress_times": [],
               "entries": {T02_E1: {"calls": 1, "raised": 0, "computed_columns": ["c0", "zz"]}}}
        runs[("post_ic_transform", "cols")] = {"probe": {"cmd": cmd, "data": [], "config": []}, "receipt_path": "q.json",
                                               "receipt": {"points": []}, "records": {500: [rec]}}
    return runs


def _t02_assemble(harness: Any, scale_probe: Any, **kw: Any) -> Dict[str, Any]:
    return harness.assemble_scale_receipt(_t02_inventory(), _t02_runs(**kw), head="0" * 40, scale_probe=scale_probe,
                                          budget_seconds=BUDGET2_UPPER_SECONDS, sample_interval_seconds=0.2,
                                          chunk_cap={"bytes": 1, "basis": "x"}, ram_bytes=8 * 1024 ** 3)


def test_task02_assemble_receipt_schema(fb: Any, harness: Any, scale_probe: Any) -> None:
    """量測收據組裝（合成記錄）：入口 id 只取清冊 measure=true 者；每點 seconds＝同 path_run_id 之逐入口秒數（非路徑級
    scale_probe 秒數）、峰值 RSS＝scale_probe 該點、footprint＝記錄；schema 過 boundary_16 之 `_entry_schema_problems`、
    四項機會欄過 boundary_17 之 `_assert_opportunities`；fit＝scale_probe.fit 對 (stage_cols, seconds) 重算；meter 同 boundary_20。"""
    receipt = _t02_assemble(harness, scale_probe)
    inv = {e["id"]: e for e in _t02_inventory()["entries"]}
    assert set(receipt["entries"]) == {T02_E1, T02_E2}
    assert fb.uncovered_entries(_t02_inventory(), receipt) == []
    for eid, m in receipt["entries"].items():
        assert not _entry_schema_problems(m, inv[eid]), _entry_schema_problems(m, inv[eid])
        _assert_opportunities(eid, m)
        again = scale_probe.fit([{"scale": p["stage_cols"], "unit": "cols", "seconds": p["seconds"],
                                  "peak_rss_bytes": p["peak_rss_bytes"]} for p in m["points"]], m["fit_full_scale"])
        assert m["fit"] == {"exponent": again["fit"]["exponent"], "r2": again["fit"]["r2"]}
        assert m["extrapolation_unreliable"] == again["extrapolation_unreliable"]
        assert set(m["criteria"]) == {"1", "2", "3", "4", "5"}
        # SPEC v5.51 (f)：判準②無原型且碼層不足以斷定 ⇒ result None＋pending_prototype；其餘判準 bool
        assert all((isinstance(c["result"], bool) or (k == "2" and c["status"] == "pending_prototype"))
                   and str(c["basis"]).strip() for k, c in m["criteria"].items())
        assert [p["path_run_id"] for p in m["points"]] == ["ic.cols500", "ic.cols1000", "ic.cols2000"]
        assert [p["peak_rss_bytes"] for p in m["points"]] == [10 ** 8 + n for n in (500, 1000, 2000)]
        assert [p["peak_footprint_bytes"] for p in m["points"]] == [5000 + n for n in (500, 1000, 2000)]
        assert all(p["seconds"] != 11.0 for p in m["points"]), "seconds 須取逐入口計時，不得抄路徑級 scale_probe 秒數"
        assert m["two_point_exception"] is None and len(m["points"]) == 3
    assert [p["seconds"] for p in receipt["entries"][T02_E2]["points"]] == [1.0, 2.0, 4.0]
    meter = receipt["meter"]
    assert meter["tool"] == "scripts/scale_probe.py" and meter["rss_scope"] == "process_tree"
    assert meter["footprint"]["tool"] == FOOTPRINT_TOOL and meter["footprint"]["sampling"] == "until_target_exit"
    assert meter["footprint"]["terminate_target_on_exceed"] is False


def test_task02_criteria_rules(harness: Any, scale_probe: Any) -> None:
    """判準①–⑤ 之判定（SPEC Task 0.2 固定規則；v5.50 (b)）：① 冪次擬合 > 1.2（可靠時）／擬合不可靠改碼層複雜度；③ 同一輸入鍵
    > 1 次；④ 受算欄 − feature_filter 請求非空（取自任一帶 feature_filter 之實跑）；⑤ 入口區間內最長無 progress 間隔 > 60 秒。"""
    lin = _t02_assemble(harness, scale_probe)["entries"]
    sup = _t02_assemble(harness, scale_probe, exp=1.5)["entries"]
    assert lin[T02_E1]["criteria"]["1"]["result"] is False and lin[T02_E1]["criteria"]["1"]["basis"] == "power_fit"
    assert sup[T02_E1]["criteria"]["1"]["result"] is True and sup[T02_E1]["criteria"]["1"]["basis"] == "power_fit"
    dec = _t02_assemble(harness, scale_probe, e2_decreasing=True)["entries"][T02_E2]
    assert dec["extrapolation_unreliable"] is True
    assert dec["criteria"]["1"]["basis"] == "complexity_analysis" and dec["criteria"]["1"]["result"] is True  # input_cols^2
    assert lin[T02_E1]["criteria"]["3"]["result"] is False and lin[T02_E2]["criteria"]["3"]["result"] is False
    dup = _t02_assemble(harness, scale_probe, dup=1)["entries"]
    assert dup[T02_E1]["criteria"]["3"]["result"] is True and dup[T02_E2]["criteria"]["3"]["result"] is False
    assert lin[T02_E1]["criteria"]["4"]["result"] is False
    un = _t02_assemble(harness, scale_probe, unrequested=True)["entries"][T02_E1]["criteria"]["4"]
    assert un["result"] is True and un["evidence"]["n_unrequested"] == 1 and un["evidence"]["examples"] == ["zz"]
    gap = _t02_assemble(harness, scale_probe, intervals=[[0.0, 100.0]], progress=[10.0, 20.0])["entries"][T02_E1]
    assert gap["criteria"]["5"]["result"] is True and gap["criteria"]["5"]["evidence"]["max_gap_seconds"] == 80.0
    ok = _t02_assemble(harness, scale_probe, intervals=[[0.0, 100.0]], progress=[10.0, 40.0, 70.0, 95.0])["entries"]
    assert ok[T02_E1]["criteria"]["5"]["result"] is False
    assert ok[T02_E1]["criteria"]["5"]["evidence"]["max_gap_seconds"] == 30.0
    assert harness.max_progress_gap([[0.0, 100.0]], []) == 100.0 and harness.max_progress_gap([], [1.0]) == 0.0


def test_task02_zero_calls_fail_assembly(harness: Any, scale_probe: Any) -> None:
    """SPEC v5.50 (a)：measure=true 入口於其路徑實跑之呼叫次數 0（含全部呼叫皆拋例外）⇒ 組裝失敗並點名該入口；
    所屬格無實跑亦失敗（不得以 0 呼叫或缺量充作量測）。"""
    for kw in ({"calls2": 0}, {"calls2": 3, "raised2": 3}):
        with pytest.raises(harness.AssemblyError) as exc:
            _t02_assemble(harness, scale_probe, **kw)
        assert any(T02_E2 in p and "呼叫次數 0" in p for p in exc.value.problems)
        assert not any(T02_E1 in p for p in exc.value.problems)
    inv = _t02_inventory()
    inv["entries"][0]["branch_cell"] = "rolling_kendall"
    with pytest.raises(harness.AssemblyError) as exc:
        harness.assemble_scale_receipt(inv, _t02_runs(), head="0" * 40, scale_probe=scale_probe, budget_seconds=1.0,
                                       sample_interval_seconds=0.2, chunk_cap={"bytes": 1, "basis": "x"})
    assert any(T02_E1 in p and "rolling_kendall" in p for p in exc.value.problems)


def test_task02_call_key_and_footprint_parse(harness: Any) -> None:
    """輸入鍵（判準③）：同值同遮罩同參數 ⇒ 同鍵；值、NaN 位置、q、require_full_q、欄名、symbol 任一不同 ⇒ 不同鍵；`sample`
    之 Physical footprint (peak) 依單位換算。"""
    s = pd.Series([1.0, np.nan, 3.0], name="a")
    k = harness.call_key((s,), {"q": 5, "require_full_q": True}, "BTCUSDT")[0]
    assert k == harness.call_key((s.copy(),), {"q": 5, "require_full_q": True}, "BTCUSDT")[0]
    others = [((pd.Series([1.0, 2.0, 3.0], name="a"),), {"q": 5, "require_full_q": True}, "BTCUSDT"),
              ((pd.Series([np.nan, 1.0, 3.0], name="a"),), {"q": 5, "require_full_q": True}, "BTCUSDT"),
              ((s,), {"q": 3, "require_full_q": True}, "BTCUSDT"), ((s,), {"q": 5, "require_full_q": False}, "BTCUSDT"),
              ((s.rename("b"),), {"q": 5, "require_full_q": True}, "BTCUSDT"),
              ((s,), {"q": 5, "require_full_q": True}, "ETHUSDT")]
    assert all(harness.call_key(a, kw, c)[0] != k for a, kw, c in others)
    assert harness.call_key((s,), {}, "")[1] == ["a"]
    text = "Physical footprint:         6368K\nPhysical footprint (peak):  1.5G\n"
    assert harness.parse_footprint(text) == int(1.5 * 1024 ** 3)
    assert harness.parse_footprint("Physical footprint:  20M\n") == 20 * 1024 ** 2
    assert harness.parse_footprint("nothing") is None
    # 不可雜湊元素之物件欄（事件表 dict 欄；2026-11-01 smoke 實測）：同內容（鍵序不同）同鍵、內容不同 ⇒ 不同鍵
    ev = pd.DataFrame({"label_definition": [{"a": 1, "b": [2]}, {"a": 3}]})
    kd = harness.call_key((ev,), {}, "BTCUSDT")[0]
    assert kd == harness.call_key((pd.DataFrame({"label_definition": [{"b": [2], "a": 1}, {"a": 3}]}),), {}, "BTCUSDT")[0]
    assert kd != harness.call_key((pd.DataFrame({"label_definition": [{"a": 1, "b": [2]}, {"a": 4}]}),), {}, "BTCUSDT")[0]


# ── SPEC v5.51 (a)(d)–(i)：量測工具修正之秒級契約（不跑量測） ──────────────────────────────────────────────


def test_task02_split_precheck_row_axis(harness: Any) -> None:
    """v5.51 (a)：秒級碼層預檢（產品 `_build_holdout_split_plan`＋`_precheck_rolling_warmup`）——實跑錨點：4h 2,000 列
    之 IC 頁預設請求走樣本外（測試段 395 ≥ 383，SPEC v5.27 實跑）、1h 2,000 列退回全樣本（395 < 1,517）、C 格同型 1h
    500 列不足 min_test_rows；4h 1,000 列預設請求不成立 ⇒ 列數軸須視窗覆寫；harness 選定之三列長於覆寫下皆成立、L 格 cols
    軸（2,000 列、無覆寫）成立；移除覆寫（mutation）⇒ 1,000 列翻為不成立。樣本外分支入口歸 L 格路徑。"""
    default_4h = harness.precheck_override("4h", row_windows=False)
    p2000 = harness.split_precheck(2000, "4h", default_4h)
    assert p2000["oos"] is True and p2000["test_rows"] == 395 and p2000["min_warmup_rows"] == 383
    p1h = harness.split_precheck(2000, "1h", harness.precheck_override("1h", row_windows=False))
    assert p1h["oos"] is False and p1h["reason"] == "rolling_warmup_insufficient" and p1h["min_warmup_rows"] == 1517
    c500 = harness.split_precheck(500, "1h", harness.precheck_override("1h", row_windows=False))
    assert c500["oos"] is False and c500["reason"] == "insufficient_data"
    assert harness.split_precheck(1000, "4h", default_4h)["oos"] is False
    res = harness.row_axis_precheck()
    assert res["ok"] is True and res["scales"] == list(harness.ROW_AXIS_SCALES) and len(set(res["scales"])) == 3
    assert all(r["oos"] for r in res["row_axis_request"]) and res["cols_axis"]["oos"] is True
    assert res["cols_axis"]["n_rows"] == harness.LONG_CELL_ROWS
    assert max(harness.ROW_AXIS_SCALES) <= harness.LONG_CELL_ROWS
    assert harness.split_precheck(min(harness.ROW_AXIS_SCALES), "4h", default_4h)["oos"] is False  # 無覆寫 ⇒ 不成立
    inv = {e["id"]: e for e in json.loads((REPO / "scripts" / "icperf_path_inventory.json").read_text("utf-8"))["entries"]}
    for eid in ("momentum.Analysis.data_preprocessor:DataPreprocessor._clip_series_train",
                "momentum.Analysis.ic_filter_orchestrator:ICFilterOrchestrator._slice_rolling_ic_to_test"):
        assert inv[eid]["branch_cell"] == "ic_page_long", eid
    assert harness.RUN_AXES["ic_page_long"] == ("cols", "rows") and "rows" not in harness.RUN_AXES["ic_page_default"]
    plan = harness.coverage_plan({"entries": list(inv.values())})
    rows_cells = {c for c, ids in plan.items() if any("rows" in inv[i]["input_axes"] for i in ids)}
    covered = {c for c in rows_cells if c in harness.ROW_AXIS_RUN}
    assert {"ic_page_default", "ic_page_long", "deep_analysis"} <= covered
    assert all("rows" in harness.RUN_AXES[harness.ROW_AXIS_RUN[c]] for c in covered)


def _t02_event_case(n_events: Sequence[int] = (10, 20, 40)) -> Tuple[Dict[str, Any], Dict[Tuple[str, str], Any]]:
    eid = "m.ev:analyze"
    inv = {"entries": [{"id": eid, "stage": "ev", "input_axes": ["rows"], "ic_page": False, "ic_first": False,
                        "loop": "per_bar", "measure": True, "no_measure_reason": None, "evidence": "m/ev.py:1",
                        "branch_cell": "event_study", "coverage_path_id": "cp-ev",
                        "unit_axis": {"axes": ["events"], "function": "n_events"}, "scale_vector": ["events"]}]}
    points, records = [], {}
    for k in n_events:
        records[k] = [{"path_run_id": f"ev.events{k}", "run_id": "event_study", "wall_seconds": 1.0,
                       "peak_footprint_bytes": 7000 + k, "progress_times": [], "_record_path": f"ev-{k}.json",
                       "facts": {"input_cols": 0, "rows": 0, "events": k, "requested_columns": None},
                       "entries": {eid: {"calls": 1, "raised": 0, "seconds": 0.01 * k, "max_rows": 0, "max_cols": 0,
                                         "keyed": True, "n_keys": 1, "duplicate_keys": 0, "max_key_count": 1,
                                         "duplicate_examples": [], "computed_columns": [], "long_intervals": [],
                                         "max_call_seconds": 0.1}}}]
        points.append({"scale": k, "unit": "events", "runs": 1, "seconds": 2.0, "peak_rss_bytes": 10 ** 8 + k})
    cmd = ["venv/bin/python", "scripts/icperf_scale_harness.py", "run", "event_study", "--axis", "events"]
    runs = {("event_study", "events"): {"probe": {"cmd": cmd, "data": [], "config": []}, "receipt_path": "ev.json",
                                        "receipt": {"points": points, "projection": {"scale": max(n_events)}},
                                        "records": records}}
    return inv, runs


def test_task02_event_axis_assembly(harness: Any, scale_probe: Any) -> None:
    """v5.51 (d)：事件研究入口（只有事件數一軸）之組裝以 events 為 x 軸取三點、不要求欄數軸；fit 對 (events, seconds)
    重算；過 boundary_16 之 `_entry_schema_problems`；缺一點 ⇒ schema 問題。"""
    inv, runs = _t02_event_case()
    m = harness.assemble_scale_receipt(inv, runs, head="0" * 40, scale_probe=scale_probe,
                                       budget_seconds=BUDGET2_UPPER_SECONDS, sample_interval_seconds=0.2,
                                       chunk_cap={"bytes": 1, "basis": "x"})["entries"]["m.ev:analyze"]
    assert m["axis"] == "events" and m["fit_axis"] == "events" and m["two_point_exception"] is None
    assert [p["events"] for p in m["points"]] == [10, 20, 40]
    assert [p["scale_vector"]["events"] for p in m["points"]] == [10, 20, 40]
    again = scale_probe.fit([{"scale": p["events"], "unit": "events", "seconds": p["seconds"],
                              "peak_rss_bytes": p["peak_rss_bytes"]} for p in m["points"]], m["fit_full_scale"])
    assert m["fit"] == {"exponent": again["fit"]["exponent"], "r2": again["fit"]["r2"]}
    inv_entry = inv["entries"][0]
    assert _entry_schema_problems(m, inv_entry) == []
    assert _entry_schema_problems({**m, "points": m["points"][:2]}, inv_entry)
    with pytest.raises(harness.AssemblyError) as exc:  # 只有 cols 軸實跑 ⇒ 事件入口無主軸量測
        harness.assemble_scale_receipt(inv, {("event_study", "cols"): runs[("event_study", "events")]}, head="0" * 40,
                                       scale_probe=scale_probe, budget_seconds=1.0, sample_interval_seconds=0.2,
                                       chunk_cap={"bytes": 1, "basis": "x"})
    assert any("events" in p for p in exc.value.problems)


def test_task02_attempt_reuse_requires_identity(fb: Any, tmp_path: Path) -> None:
    """v5.51 (e)：已完成 attempt 只在量測碼身分（HEAD、量測碼與清冊 sha256、輸入檔身分、規模、命令）全同時沿用；HEAD、
    量測碼內容、輸入檔內容、規模任一不同 ⇒ 開新 attempt；身分檔缺或未給身分 ⇒ 不沿用（反例）。"""
    probe_dir, records_dir = tmp_path / "probe", tmp_path / "records"
    data = tmp_path / "in.bin"
    data.write_bytes(b"a" * 10)
    ident = fb._task02_identity("a" * 40, data=[str(data)], config=[], scales=[500], cmd=["x", "{scale}"])
    assert set(ident["code"]) == set(fb.TASK02_CODE_FILES) and all(ident["code"].values())
    assert ident["inputs"][0]["sha256"] == hashlib.sha256(b"a" * 10).hexdigest()
    probe_dir.mkdir()
    (probe_dir / "p-cols-a1.json").write_text(json.dumps({"points": [{"scale": 500, "runs": 1}]}), encoding="utf-8")
    att = records_dir / "p-cols-a1"
    (att / "p" / "cols-500").mkdir(parents=True)
    (att / "p" / "cols-500" / "r.json").write_text(json.dumps({"path_run_id": "r"}), encoding="utf-8")
    (att / fb.TASK02_IDENTITY_FILE).write_text(json.dumps(ident), encoding="utf-8")
    assert fb._task02_attempt(probe_dir, records_dir, "p", "cols", ident) == (1, True)
    assert fb._task02_attempt(probe_dir, records_dir, "p", "cols", None) == (2, False)
    assert fb._task02_attempt(probe_dir, records_dir, "p", "cols", {**ident, "head": "b" * 40}) == (2, False)
    code = dict(ident["code"])
    code["scripts/icperf_scale_harness.py"] = "0" * 64
    assert fb._task02_attempt(probe_dir, records_dir, "p", "cols", {**ident, "code": code}) == (2, False)
    assert fb._task02_attempt(probe_dir, records_dir, "p", "cols", {**ident, "scales": [1000]}) == (2, False)
    data.write_bytes(b"b" * 11)  # 輸入檔內容變 ⇒ 身分變 ⇒ 不沿用
    changed = fb._task02_identity("a" * 40, data=[str(data)], config=[], scales=[500], cmd=["x", "{scale}"])
    assert changed != ident and fb._task02_attempt(probe_dir, records_dir, "p", "cols", changed) == (2, False)
    (att / fb.TASK02_IDENTITY_FILE).unlink()
    assert fb._task02_attempt(probe_dir, records_dir, "p", "cols", ident) == (2, False)


def test_task02_criterion2_code_level(harness: Any, scale_probe: Any) -> None:
    """v5.51 (f)：判準②不得固定 False——無原型且每單位秒數高於硬體下限 × 10 ⇒ result None＋pending_prototype（列收據頂層；
    超線性與同階之碼層階數差只記於 evidence，不作 10 倍實證）；每單位秒數 < 10 × 硬體下限 ⇒ False（hardware_floor）；有原型下限
    ⇒ 數值比（≥ 10 倍 True、否則 False）。改壞成固定 False（mutation）⇒ 本測試之 pending 斷言翻紅。"""
    base = {"unit_axis": {"axes": ["stage_cols"], "function": "stage_cols^2"}, "lower_bound_analysis": "x"}
    c = harness.criterion2({**base, "unit_seconds": 1e-3, "lower_bound_seconds_per_unit": None})
    assert c["result"] is None and c["status"] == "pending_prototype" and c["evidence"]["order_gap"] == "superlinear"
    lin = harness.criterion2({**base, "unit_axis": {"axes": ["rows"], "function": "stage_cols*rows（x）"},
                              "unit_seconds": 1e-3})
    assert lin["result"] is None and lin["evidence"]["order_gap"] == "same_order"
    win = harness.criterion2({**base, "unit_axis": {"axes": ["rows"], "function": "survivors*rows*W"}, "unit_seconds": 1})
    assert win["evidence"]["order_gap"] == "superlinear"
    floor = harness.criterion2({**base, "unit_seconds": 5e-10})
    assert floor["result"] is False and floor["status"] == "decided" and floor["basis"].startswith("hardware_floor")
    assert harness.criterion2({**base, "unit_seconds": 1e-3, "lower_bound_seconds_per_unit": 1e-5})["result"] is True
    assert harness.criterion2({**base, "unit_seconds": 9e-5, "lower_bound_seconds_per_unit": 1e-5})["result"] is False
    receipt = _t02_assemble(harness, scale_probe)
    for eid, m in receipt["entries"].items():
        assert m["criteria"]["2"]["status"] == "pending_prototype" and m["unit_seconds"] > 0, eid
        assert _criterion2_problems(eid, m, receipt) == [], _criterion2_problems(eid, m, receipt)
    assert receipt["pending_prototype"] == sorted(receipt["entries"])
    fixed = {**receipt["entries"][T02_E1], "criteria": {**receipt["entries"][T02_E1]["criteria"],
                                                         "2": {"result": False, "basis": "固定", "status": "decided"}}}
    assert _criterion2_problems(T02_E1, fixed, receipt)  # 固定 False ⇒ 問題


def test_task02_two_point_only_when_over_budget(harness: Any, scale_probe: Any) -> None:
    """v5.51 (g)：某入口 500／1000 推估 2000 欄逾 10 分鐘，但收據合計推估未逾 budget_seconds ⇒ 三點皆收、不帶例外；
    合計推估逾 budget_seconds ⇒ 該入口兩點例外（2,000 欄點移 excluded_points），其餘入口仍三點。頂層 total_projected_seconds
    ＝scale_probe 逐點 seconds × runs 之和。"""
    kw = {"head": "0" * 40, "scale_probe": scale_probe, "sample_interval_seconds": 0.2,
          "chunk_cap": {"bytes": 1, "basis": "x"}}
    runs = _t02_runs(e2_per_col=0.4)  # E2：500 欄 200 秒、1000 欄 400 秒 ⇒ 推估 2000 欄 800 秒 > 600
    assert harness.projected_2000_seconds([{"input_cols": 500, "seconds": 200.0},
                                           {"input_cols": 1000, "seconds": 400.0}]) > TWO_POINT_SECONDS
    under = harness.assemble_scale_receipt(_t02_inventory(), runs, budget_seconds=BUDGET2_UPPER_SECONDS, **kw)
    assert under["total_projected_seconds"] == 33.0 and under["budget_exceeded"] is False
    assert under["entries"][T02_E2]["two_point_exception"] is None and len(under["entries"][T02_E2]["points"]) == 3
    over = harness.assemble_scale_receipt(_t02_inventory(), runs, budget_seconds=30.0, **kw)
    assert over["budget_exceeded"] is True
    m2 = over["entries"][T02_E2]
    assert m2["two_point_exception"]["projected_2000_seconds"] > TWO_POINT_SECONDS
    assert [p["input_cols"] for p in m2["points"]] == [500, 1000] and [p["input_cols"] for p in m2["excluded_points"]] == [2000]
    assert over["entries"][T02_E1]["two_point_exception"] is None and len(over["entries"][T02_E1]["points"]) == 3


def test_task02_footprint_same_path_run_and_record_store(harness: Any, scale_probe: Any, fb: Any,
                                                          tmp_path: Path) -> None:
    """v5.51 (h)：每點 footprint 取自同 path_run_id（牆鐘中位數者）之紀錄，不取同點他次實跑之最大值；RSS 取 scale_probe。
    v5.51 (i)：紀錄存處常數＝`handoffs/run_receipts/icperf_task02_records`（兩模組一致）、`_task02_records` 記每檔位元組數與
    sha256 並傳至點之 record_bytes／record_sha256。"""
    runs = _t02_runs()
    run = runs[("ic_page_default", "cols")]
    run["receipt"]["points"] = [{**q, "runs": 3} for q in run["receipt"]["points"]]
    for n, recs in run["records"].items():
        base = recs[0]
        run["records"][n] = [{**base, "path_run_id": f"ic.cols{n}.{i}", "wall_seconds": w,
                              "peak_footprint_bytes": fp, "_record_path": f"rec-{n}-{i}.json"}
                             for i, (w, fp) in enumerate(((5.0, 1000 + n), (10.0, 2000 + n), (20.0, 9_000_000)))]
    receipt = harness.assemble_scale_receipt(_t02_inventory(), runs, head="0" * 40, scale_probe=scale_probe,
                                             budget_seconds=BUDGET2_UPPER_SECONDS, sample_interval_seconds=0.2,
                                             chunk_cap={"bytes": 1, "basis": "x"})
    for m in receipt["entries"].values():
        assert [p["path_run_id"] for p in m["points"]] == [f"ic.cols{n}.1" for n in (500, 1000, 2000)]
        assert [p["peak_footprint_bytes"] for p in m["points"]] == [2000 + n for n in (500, 1000, 2000)]
        assert all(p["footprint_source"] == f"harness_record:{p['path_run_id']}" for p in m["points"])
        assert all(p["rss_source"] == "scale_probe:r.json" for p in m["points"])
    assert receipt["meter"]["footprint"]["source"] == "harness_record_same_path_run_id"
    assert fb.TASK02_RECORDS_ROOT == harness.TASK02_RECORDS_ROOT == RECORDS_ROOT
    d = tmp_path / "ic_page_default" / "cols-500"
    d.mkdir(parents=True)
    body = json.dumps({"path_run_id": "x", "peak_footprint_bytes": 5}).encode("utf-8")
    (d / "x.json").write_bytes(body)
    got = fb._task02_records(tmp_path, "ic_page_default", "cols")[500][0]
    assert got["_record_bytes"] == len(body) and got["_record_sha256"] == hashlib.sha256(body).hexdigest()


# ── SPEC v5.52 (a)–(c)：子集沿用比對來源、各路徑第二軸、IC-first 經 write_raw 之子集（秒級；不跑量測） ─────────────


def _t02_handoff(root: Path, values: np.ndarray) -> Path:
    """交接 h5 舊格式（`features` float32＋`timestamps`＋`feature_names`）與同名 meta——量測工具之秒級契約用（非特徵值驗證）。"""
    import h5py

    root.mkdir(parents=True, exist_ok=True)
    names = [f"f{i:02d}" for i in range(values.shape[1])]
    h5 = root / "X_1h.h5"
    with h5py.File(h5, "w") as f:
        g = f.create_group("BTCUSDT/1h")
        g.create_dataset("features", data=values.astype(np.float32))
        g.create_dataset("timestamps", data=np.arange(values.shape[0], dtype=np.int64))
        g.create_dataset("feature_names", data=np.array(names, dtype=object), dtype=h5py.string_dtype(encoding="utf-8"))
    meta = {"symbol": "BTCUSDT", "timeframe": "1h", "config_hash": "h", "ff_run_identity": {},
            "feature_metadata_version": 1, **{n: {} for n in names}}
    (root / "X_1h_meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return h5


def _t02_h5_features(h5: Path) -> np.ndarray:
    import h5py

    with h5py.File(h5, "r") as f:
        return np.asarray(f["BTCUSDT/1h/features"][:])


def test_task02_subset_reuse_compares_source_identity(harness: Any, tmp_path: Path) -> None:
    """SPEC v5.52 (a)（r63 群集 A 反例）：既有子集只在 sidecar 之來源身分（內容 sha256、seed、欄數、列長）逐欄相同時沿用；
    來源內容改變（同形狀）⇒ 重建且子集內容＝新來源之所選欄（舊碼只憑檔案存在 ⇒ 讀到舊子集，本測試之內容斷言即紅）；seed、
    欄數不同 ⇒ 重建；列長子集同（連帶重建母子集）。存檔目錄之身分與現行來源不符或檔不在 files ⇒ 讀端拒收。"""
    rng = np.random.default_rng(0)
    v1 = rng.normal(size=(12, 10))
    src = _t02_handoff(tmp_path / "src", v1)
    sub, rdir = tmp_path / "sub", tmp_path / "sub_rows8"
    h5, _meta, rebuilt = harness.ensure_subset(src, 4, 7, sub)
    assert rebuilt is True and (sub / harness.SUBSET_IDENTITY_FILE).is_file()
    ident = json.loads((sub / harness.SUBSET_IDENTITY_FILE).read_text(encoding="utf-8"))
    assert ident["source_sha256"] == hashlib.sha256(src.read_bytes()).hexdigest()
    assert (ident["seed"], ident["n_cols"], ident["rows"], ident["source_rows"], ident["source_total_cols"]) == (7, 4, None, 12, 10)
    first = _t02_h5_features(h5)
    assert harness.ensure_subset(src, 4, 7, sub)[2] is False  # 同身分 ⇒ 沿用
    _t02_handoff(tmp_path / "src", v1 + 1.0)  # 來源內容改變（同形狀、同路徑）
    h5b, _m, rebuilt = harness.ensure_subset(src, 4, 7, sub)
    assert rebuilt is True
    chosen = np.sort(np.random.default_rng(7).permutation(10)[:4])
    assert np.array_equal(_t02_h5_features(h5b), (v1 + 1.0)[:, chosen].astype(np.float32))
    assert not np.array_equal(_t02_h5_features(h5b), first)
    assert harness.ensure_subset(src, 4, 8, sub)[2] is True  # seed 不同
    assert harness.ensure_subset(src, 5, 8, sub)[2] is True  # 欄數不同
    _r, _m, rebuilt = harness.ensure_subset(src, 5, 8, rdir, rows=8, parent_dir=sub)
    assert rebuilt is True and harness._h5_rows(rdir / src.name) == 8
    assert harness.ensure_subset(src, 5, 8, rdir, rows=8, parent_dir=sub)[2] is False
    _t02_handoff(tmp_path / "src", v1 * 2.0)
    _r, _m, rebuilt = harness.ensure_subset(src, 5, 8, rdir, rows=8, parent_dir=sub)
    chosen5 = np.sort(np.random.default_rng(8).permutation(10)[:5])
    assert rebuilt is True and np.array_equal(_t02_h5_features(rdir / src.name), (v1 * 2.0)[-8:, chosen5].astype(np.float32))
    # 存檔目錄之身分（stage_identity）：相同且檔在 files ⇒ 可讀；身分不同、status 非 complete、檔不在 files ⇒ 拒收
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "preprocess.pkl").write_bytes(pickle.dumps({"self": None, "args": (), "kwargs": {}}))
    want = {"subset": harness.subset_identity(src, n_cols=5, seed=8, rows=None), "writer": ["ic_page_default", "cols"]}
    harness.write_identity(stage / harness.STAGE_IDENTITY_FILE, {**want, "status": "complete", "files": ["preprocess"]})
    assert harness.load_capture(stage, "preprocess", want)["args"] == ()
    for side in ({**want, "status": "building", "files": ["preprocess"]}, {**want, "status": "complete", "files": []},
                 {**want, "subset": {**want["subset"], "source_sha256": "0" * 64}, "status": "complete",
                  "files": ["preprocess"]}):
        harness.write_identity(stage / harness.STAGE_IDENTITY_FILE, side)
        with pytest.raises(harness.HarnessError):
            harness.load_capture(stage, "preprocess", want)


def _t02_axis_records(run_id: str, axis: str, scales: Sequence[int], eids: Sequence[str],
                      facts: Any, actual: Any = "scale") -> Dict[str, Any]:
    """合成之 (run_id, axis) 實跑（記錄形狀同 run_one 寫出者；秒數 ∝ 規模）；`actual`＝"scale"（actual_scale＝規模）、
    None（不帶）或函式。"""
    points, records = [], {}
    for s in scales:
        rec = {"path_run_id": f"{run_id}.{axis}{s}", "run_id": run_id, "wall_seconds": 1.0, "peak_footprint_bytes": 9000 + s,
               "progress_times": [], "_record_path": f"{run_id}-{axis}-{s}.json", "facts": facts(s),
               "entries": {e: {"calls": 2, "raised": 0, "seconds": 0.001 * s, "max_rows": 0, "max_cols": 0, "keyed": False,
                               "long_intervals": [], "max_call_seconds": 0.1} for e in eids}}
        if actual == "scale":
            rec["actual_scale"] = s
        elif callable(actual):
            rec["actual_scale"] = actual(s)
        records[s] = [rec]
        points.append({"scale": s, "unit": axis, "runs": 1, "seconds": 2.0, "peak_rss_bytes": 10 ** 8 + s})
    cmd = ["venv/bin/python", "scripts/icperf_scale_harness.py", "run", run_id, "--axis", axis]
    return {"probe": {"cmd": cmd, "data": [], "config": []}, "receipt_path": f"{run_id}-{axis}.json",
            "receipt": {"points": points, "projection": {"scale": max(scales)}}, "records": records}


def _t02_second_axis_case() -> Tuple[Dict[str, Any], Dict[Tuple[str, str], Any]]:
    base = {"stage": "x", "ic_page": True, "ic_first": False, "loop": "none", "measure": True, "no_measure_reason": None,
            "evidence": "m/x.py:1"}
    inv = {"entries": [
        {**base, "id": "m.x:cross", "input_axes": ["cols", "rows"], "branch_cell": "cross_sectional", "coverage_path_id": "c1",
         "unit_axis": {"axes": ["stage_cols", "timestamps"], "function": "stage_cols*n_timestamps"},
         "scale_vector": ["rows", "stage_cols", "timestamps"]},
        {**base, "id": "m.x:mw", "input_axes": ["cols"], "branch_cell": "event_import", "coverage_path_id": "c2",
         "unit_axis": {"axes": ["stage_cols", "events"], "function": "stage_cols*n_events"},
         "scale_vector": ["stage_cols", "events"]},
        {**base, "id": "m.x:label", "input_axes": [], "branch_cell": "event_import", "coverage_path_id": "c3",
         "unit_axis": {"axes": ["events"], "function": "n_events"}, "scale_vector": ["events"]},
        {**base, "id": "m.x:post", "input_axes": ["passed_cols", "rows"], "branch_cell": "post_ic_transform",
         "coverage_path_id": "c4", "unit_axis": {"axes": ["rows", "survivors"], "function": "survivors*rows*W"},
         "scale_vector": ["rows", "survivors"]}]}
    cols = (500, 1000, 2000)
    runs = {
        ("cross_sectional", "cols"): _t02_axis_records("cross_sectional", "cols", cols, ["m.x:cross"], lambda s: {
            "input_cols": s, "rows": 1000, "symbols": 2, "timestamps": 500, "requested_columns": None}),
        ("cross_sectional", "timestamps"): _t02_axis_records("cross_sectional", "timestamps", (250, 375, 500), ["m.x:cross"],
                                                             lambda s: {"input_cols": 500, "rows": 2 * s, "symbols": 2,
                                                                        "timestamps": s, "requested_columns": None}),
        ("event_import", "cols"): _t02_axis_records("event_import", "cols", cols, ["m.x:mw"], lambda s: {
            "input_cols": s, "rows": 2000, "events": 40, "survivors": 3, "requested_columns": None}),
        ("event_import", "events"): _t02_axis_records("event_import", "events", (10, 20, 40), ["m.x:mw", "m.x:label"],
                                                      lambda s: {"input_cols": 500, "rows": 2000, "events": s,
                                                                 "survivors": 3, "requested_columns": None}),
        # SPEC v5.55 (e)：post_ic_transform 之主軸改 survivors（三點＝ic_page_relaxed 各 cols 點之實際倖存數）
        ("post_ic_transform", "survivors"): _t02_axis_records("post_ic_transform", "survivors", (40, 90, 170),
                                                              ["m.x:post"], lambda s: {
            "input_cols": 500, "rows": 2000, "survivors": s, "requested_columns": None}),
        ("post_ic_transform", "rows"): _t02_axis_records("post_ic_transform", "rows", (1000, 1500, 2000), ["m.x:post"],
                                                         lambda s: {"input_cols": 500, "rows": s, "survivors": 9,
                                                                    "requested_columns": None}),
    }
    return inv, runs


def test_task02_second_axis_assembly(harness: Any, scale_probe: Any) -> None:
    """SPEC v5.52 (b)：各路徑之第二軸——跨標的 timestamps、事件型 cols 入口之 events、只隨事件數變之入口以 events 為主軸、
    post_ic_transform rows；收據明示軸名（row_axis／row_fit.axis）、點之 x 鍵與 scale_vector 為該軸之宣告規模；
    `require_rows` 下缺任一第二軸實跑 ⇒ 點名該入口；第二軸紀錄未帶或不等於宣告規模之 actual_scale ⇒ 組裝失敗。"""
    inv, runs = _t02_second_axis_case()
    kw = {"head": "0" * 40, "scale_probe": scale_probe, "budget_seconds": BUDGET2_UPPER_SECONDS,
          "sample_interval_seconds": 0.2, "chunk_cap": {"bytes": 1, "basis": "x"}, "require_rows": True}
    got = harness.assemble_scale_receipt(inv, runs, **kw)
    m = got["entries"]
    assert m["m.x:cross"]["row_axis"] == "timestamps" and m["m.x:cross"]["row_fit"]["axis"] == "timestamps"
    assert [p["timestamps"] for p in m["m.x:cross"]["row_points"]] == [250, 375, 500]
    assert [p["scale_vector"]["timestamps"] for p in m["m.x:cross"]["row_points"]] == [250, 375, 500]
    assert m["m.x:mw"]["axis"] == "cols" and m["m.x:mw"]["row_axis"] == "events"
    assert [p["events"] for p in m["m.x:mw"]["row_points"]] == [10, 20, 40]
    assert m["m.x:label"]["axis"] == "events" and m["m.x:label"]["row_points"] is None
    assert [p["events"] for p in m["m.x:label"]["points"]] == [10, 20, 40]
    assert m["m.x:post"]["row_axis"] == "rows" and [p["rows"] for p in m["m.x:post"]["row_points"]] == [1000, 1500, 2000]
    assert all(p["actual_scale"] == p["rows"] for p in m["m.x:post"]["row_points"])
    assert got["schedule_coverage"]["uncovered"] == [] and got["schedule_coverage"]["measured"] == 4
    for drop, victim in ((("cross_sectional", "timestamps"), "m.x:cross"), (("event_import", "events"), "m.x:mw"),
                         (("post_ic_transform", "rows"), "m.x:post")):
        with pytest.raises(harness.AssemblyError) as exc:
            harness.assemble_scale_receipt(inv, {k: v for k, v in runs.items() if k != drop}, **kw)
        assert any(victim in p for p in exc.value.problems), (drop, exc.value.problems)
    bad = dict(runs)
    bad[("cross_sectional", "timestamps")] = _t02_axis_records(
        "cross_sectional", "timestamps", (250, 375, 500), ["m.x:cross"],
        lambda s: {"input_cols": 500, "rows": 2 * s, "symbols": 2, "timestamps": s, "requested_columns": None}, actual=None)
    with pytest.raises(harness.AssemblyError) as exc:  # 第二軸未驗實際點數 ⇒ 拒收
        harness.assemble_scale_receipt(inv, bad, **kw)
    assert any("m.x:cross" in p and "實際輸入點數" in p for p in exc.value.problems)
    bad[("cross_sectional", "timestamps")] = runs[("cross_sectional", "timestamps")]
    bad[("event_import", "cols")] = _t02_axis_records(
        "event_import", "cols", (500, 1000, 2000), ["m.x:mw"],
        lambda s: {"input_cols": s, "rows": 2000, "events": 40, "survivors": 3, "requested_columns": None},
        actual=lambda s: s - 1)
    with pytest.raises(harness.AssemblyError) as exc:  # 主軸帶 actual_scale 而不等 ⇒ 拒收
        harness.assemble_scale_receipt(inv, bad, **kw)
    assert any("m.x:mw" in p and "實際輸入點數" in p for p in exc.value.problems)


def test_task02_schedule_covers_every_measured_entry(fb: Any, harness: Any) -> None:
    """SPEC v5.52 (b)：由定稿清冊導出之實跑排程（`schedule_runs`，`measure_inventory` 同用）涵蓋每一 measure=true 入口之主軸
    與第二軸——未涵蓋數由清冊計算為 0（不寫死入口數）；排程之每一軸皆為該路徑／格所支援；事件型入口之事件數不記為 rows
    （scale_vector 含 events 之 event_import／event_study 入口 input_axes 不含 rows）；input_axes 含 rows 之入口皆有第二軸
    對應。反例：自排程移除任一第二軸實跑 ⇒ 該格入口被點名未涵蓋。"""
    inv = json.loads((REPO / "scripts" / "icperf_path_inventory.json").read_text(encoding="utf-8"))
    assert fb.inventory_problems(inv) == []
    measured = [e for e in inv["entries"] if e["measure"]]
    sched = harness.schedule_runs(inv)
    cov = harness.schedule_coverage(inv, sched)
    assert cov["uncovered"] == [] and cov["covered"] == cov["measured"] == len(measured)
    assert all(a in harness.RUN_AXES[r] for r, a in sched)
    assert sched.index(("ic_page_long", "rows")) < min(sched.index((c, "rows")) for c in harness.CELLS
                                                       if (c, "rows") in sched)
    for e in measured:
        if e["branch_cell"] in harness.EVENT_AXIS_RUN and "events" in e["scale_vector"]:
            assert "rows" not in e["input_axes"], f"{e['id']}：事件數不得記為 rows（SPEC v5.52 (b)）"
        if "rows" in e["input_axes"]:
            assert harness.second_axis_run(e["branch_cell"]) is not None, e["id"]
        for ax in (e.get("fixed_axes") or {}):
            assert ax not in e["input_axes"] and ax in e["scale_vector"], e["id"]
    assert {("cross_sectional", "timestamps"), ("event_import", "events"), ("post_ic_transform", "rows"),
            ("icfirst_post_generation", "rows"), ("ic_page_long", "rows"), ("deep_analysis_long", "rows")} <= set(sched)
    for drop in (("cross_sectional", "timestamps"), ("post_ic_transform", "rows"), ("icfirst_post_generation", "rows"),
                 ("event_import", "events")):
        miss = harness.schedule_coverage(inv, [x for x in sched if x != drop])["uncovered"]
        assert miss and all(f"{drop[0]}:{drop[1]}" in u["missing"] for u in miss), drop
    assert harness.axis_scales("cross_sectional", "timestamps", cols_scales=(), row_scales=(), event_scales=()) \
        == list(harness.XSEC_TIMESTAMP_SCALES)
    assert harness.axis_scales("icfirst_post_generation", "rows", cols_scales=(), row_scales=(1, 2, 3), event_scales=()) \
        == list(harness.ICFIRST_ROW_SCALES)
    # 清冊 schema：input_axes 空而 scale_vector 無 events、fixed_axes 落在 input_axes ⇒ 問題
    e0 = copy.deepcopy(next(e for e in measured if e["input_axes"] == [] and "events" in e["scale_vector"]))
    probe = {**inv, "entries": [{**e0, "scale_vector": ["rows"], "unit_axis": {"axes": ["rows"], "function": "rows"}},
                                {**e0, "id": e0["id"] + "x", "coverage_path_id": "cp-x", "input_axes": ["rows"],
                                 "scale_vector": ["rows", "events"], "fixed_axes": {"rows": "x"}}]}
    probs = fb.inventory_problems(probe)
    assert any("input_axes 非法" in p for p in probs) and any("fixed_axes" in p for p in probs)


def _t02_raw_run(root: Path, n_cols: int = 12, n_rows: int = 30) -> Tuple[str, str, str]:
    """以產品寫出端 `FeatureStorage.write_raw` 建 raw run（三群組、DatetimeIndex 時間軸；值為確定性亂數）——量測工具之
    秒級契約用（驗子集重寫與讀取端可讀，非特徵值驗證）。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage, build_timeframe_completeness

    sym, tf, ch = "BTCUSDT", "1h", "cfg0"
    idx = pd.date_range("2024-01-01", periods=n_rows, freq="h")
    rng = np.random.default_rng(3)
    vals = rng.normal(size=(n_rows, n_cols)).astype(np.float32)
    vals[0, 1] = np.nan
    names = [f"g{i % 3}_f{i:02d}" for i in range(n_cols)]
    groups = {f"grp{g}": pd.DataFrame({n: vals[:, i] for i, n in enumerate(names) if i % 3 == g}, index=idx)
              for g in range(3)}
    # 生成端之 completeness 證據（同 `generate_features` 落盤之 run：週期三欄＋L1–L6 狀態）⇒ run_status complete，嚴格讀取端可讀
    FeatureStorage(str(root)).write_raw(sym, tf, ch, groups, row_index=idx,
                                        timeframe_completeness=build_timeframe_completeness([tf], []),
                                        layer_status_by_tf={tf: {f"L{i}": ("complete", "") for i in range(1, 7)}})
    return sym, tf, ch


def test_task02_icfirst_subset_via_write_raw(harness: Any, tmp_path: Path) -> None:
    """SPEC v5.52 (c)：IC-first 之欄子集 run 經產品寫出端 `FeatureStorage.write_raw` 由一次之 raw run 重寫（身分欄由產品寫出端
    產生）——子集 run 可由產品讀取端（`FeatureReader.load_manifest_v2(consumer=strict)`、`ICEngine._validate_l7_raw_manifest`、
    `stream_groups_v2`、`load_row_index_v2`）讀出，欄數＝N、群組欄聯集＝所選欄、時間軸與逐欄值（含 NaN）＝來源；巢狀（N 小
    者 ⊆ N 大者）。反例：所選欄清單與子集不符、子集某欄值被改 ⇒ `verify_icfirst_subset` 大聲失敗。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    src = tmp_path / "src"
    sym, tf, ch = _t02_raw_run(src)
    rec = {"symbol": sym, "timeframe": tf, "config_hash": ch}
    c5 = harness.write_icfirst_subset(src, tmp_path / "c5", sym, tf, ch, 5, 20261027)
    check = harness.verify_icfirst_subset(src, tmp_path / "c5", rec, c5)
    assert check["ok"] is True and check["n_cols"] == 5 and check["row_count"] == 30 and len(set(c5)) == 5
    c8 = harness.write_icfirst_subset(src, tmp_path / "c8", sym, tf, ch, 8, 20261027)
    assert set(c5) <= set(c8) and harness.verify_icfirst_subset(src, tmp_path / "c8", rec, c8)["n_cols"] == 8
    with pytest.raises(harness.HarnessError):
        harness.verify_icfirst_subset(src, tmp_path / "c5", rec, c5[:-1])
    with pytest.raises(harness.HarnessError):
        harness.write_icfirst_subset(src, tmp_path / "c12", sym, tf, ch, 12, 20261027)  # N 不得 ≥ raw 欄數
    # 子集某欄值被改（經同一產品寫出端重寫）⇒ 逐欄值比對失敗
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    reader = FeatureReader(str(tmp_path / "c5"))
    idx = reader.load_row_index_v2(sym, tf, ch, artifact_kind="raw")
    groups = {g: f for g, f in reader.stream_groups_v2(sym, tf, ch, "raw", consumer="strict")}
    gid = sorted(groups)[0]
    groups[gid] = groups[gid].copy()
    groups[gid].iloc[3, 0] = groups[gid].iloc[3, 0] + 1.0
    for g in groups:
        groups[g].index = idx
    FeatureStorage(str(tmp_path / "c5")).write_raw(sym, tf, ch, groups, row_index=idx)
    with pytest.raises(harness.HarnessError, match="值"):
        harness.verify_icfirst_subset(src, tmp_path / "c5", rec, c5)


# ── SPEC v5.53（code review r64）：(c0) 事件路徑 K 線根數軸、(c1) 跨標的長資料格 ─────────────────────────────────

#: GROK-R64-P1-01 所列 unit_axis.axes 含 rows 而原記 fixed_axes.rows 之事件入口（r64 收斂檔群集 A）
R64_EVENT_ROWS_ENTRIES = (
    "momentum.Analysis.event_samples.all_bars_eval:evaluate_all_bars",
    "api.services.ic_analysis_service:ICAnalysisService._run_event_label_stages",
    "momentum.Analysis.event_samples.label_value_from_case:prepare_analysis_windows",
    "momentum.Analysis.event_samples.alignment:align_events",
    "momentum.Analysis.event_samples.label_value_from_case:resolve_label_value_at_analyze",
    "momentum.Analysis.event_samples.label_value_from_case:feature_row_keys",
    "api.services.case_import_service:EventImportService._analyze_with_projection",
    "momentum.Analysis.event_samples.pipeline:EventSamplePipeline.analyze_tables",
)
_T02_4H = 14400


def _t02_kline_h5(path: Path, series: Mapping[str, int], *, end: int = 1_777_320_000) -> None:
    """K 線快取形狀之 h5（`<symbol>/<週期>/data` 結構化資料集，欄同 `kline_cache.h5`；4h 連續網格、末根時間戳＝`end` 秒）——
    量測工具之秒級契約用（驗截短複本隔離與預檢之碼路，非 K 線值驗證）；檔／群組／資料集屬性供照抄之驗證。"""
    import h5py

    dt = np.dtype([("timestamp", "<i8"), ("open", "<f4"), ("high", "<f4"), ("low", "<f4"), ("close", "<f4"),
                   ("volume", "<f4")])
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(str(path), "w") as f:
        f.attrs["origin"] = "icperf-t02-test"
        for key, n in series.items():
            a = np.zeros(int(n), dtype=dt)
            a["timestamp"] = int(end) - _T02_4H * np.arange(int(n) - 1, -1, -1, dtype=np.int64)
            a["close"] = 100.0 + np.arange(int(n), dtype=np.float32)
            a["open"] = a["close"] - 0.5
            a["high"], a["low"], a["volume"] = a["close"] + 1.0, a["close"] - 1.0, 1.0
            g = f.require_group(key)
            g.attrs["series"] = key
            ds = g.create_dataset("data", data=a)
            ds.attrs["n_source"] = int(n)


def test_task02_event_bars_axis_schedule(fb: Any, harness: Any) -> None:
    """SPEC v5.53 (c0)：定稿清冊中 unit_axis.axes 含 rows 之事件入口（含 GROK-R64-P1-01 所列 8 個）不得記 fixed_axes，排程
    皆含其格之 (格, rows) K 線根數軸；只含 rows 之 `evaluate_all_bars` 主軸＝rows（events 為第二軸），含 events 者主軸＝events。
    反例：移除任一 (格, rows) ⇒ 恰該格之此類入口被點名；fixed_axes.rows 放回 ⇒ inventory_problems 點名；同一入口需兩個第二軸
    ⇒ 無法涵蓋（不靜默只量其一）。"""
    inv = json.loads((REPO / "scripts" / "icperf_path_inventory.json").read_text(encoding="utf-8"))
    assert fb.inventory_problems(inv) == []
    measured = [e for e in inv["entries"] if e["measure"]]
    bars = [e for e in measured if e["branch_cell"] in harness.EVENT_BARS_RUN and "rows" in e["unit_axis"]["axes"]]
    assert set(R64_EVENT_ROWS_ENTRIES) <= {e["id"] for e in bars}
    for e in measured:
        assert not set(e.get("fixed_axes") or {}) & set(e["unit_axis"]["axes"]), e["id"]
    sched = harness.schedule_runs(inv)
    assert all(a in harness.RUN_AXES[r] for r, a in sched)
    for e in bars:
        p, s, need = harness.entry_runs(e)
        want = (harness.EVENT_BARS_RUN[e["branch_cell"]], "rows")
        assert want in [p] + ([s] if need and s else []) and want in sched, e["id"]
        assert (p[1] == "events") == ("events" in e["unit_axis"]["axes"]), e["id"]
    eab = next(e for e in measured if e["id"] == R64_EVENT_ROWS_ENTRIES[0])
    assert harness.entry_runs(eab) == (("event_study", "rows"), ("event_study", "events"), True)
    for drop in (("event_study", "rows"), ("event_import", "rows")):
        miss = harness.schedule_coverage(inv, [x for x in sched if x != drop])["uncovered"]
        assert {u["id"] for u in miss} == {e["id"] for e in bars if e["branch_cell"] == drop[0]}, drop
        assert all(f"{drop[0]}:rows" in u["missing"] for u in miss), drop
    probe = copy.deepcopy(inv)
    next(e for e in probe["entries"] if e["id"] == eab["id"])["fixed_axes"] = {"rows": "x"}
    assert any(eab["id"] in p and "成本軸" in p for p in fb.inventory_problems(probe))
    two = {**copy.deepcopy(eab), "input_axes": ["cols"], "branch_cell": "event_import"}
    assert harness.entry_runs(two)[1:] == (None, True)
    assert harness.axis_scales("event_study", "rows", cols_scales=(), row_scales=(1, 2, 3), event_scales=(),
                               bar_scales=(7, 8, 9)) == [7, 8, 9]


def test_task02_event_bars_truncated_cache_isolated(harness: Any, tmp_path: Path) -> None:
    """SPEC v5.53 (c0)：K 線根數軸之隔離截短複本——三點＝(最早事件前 EVENT_BARS_PRE 根起之根數, 中點, 全長)；複本只含事件
    批序列之末 R 根（dtype 與屬性照抄）、落於工作根之下、來源位元組不變；身分相同沿用、不同重建；R 不含最早事件、R 超過來源、
    目的檔即來源 ⇒ 拒收。行程內改指後，產品之 `EventSamplePipeline.bars_from_kline_cache`（服務唯一入口）讀到 R 根，離開即還原；
    `bars_actual` 只認自複本讀得且根數一致者。"""
    import h5py

    from momentum.Analysis.event_samples import bars_source
    from momentum.Analysis.event_samples.pipeline import EventSamplePipeline

    src = tmp_path / "cache" / "kline_cache.h5"
    _t02_kline_h5(src, {"BTCUSDT/4h": 1000, "ETHUSDT/4h": 50})
    before = hashlib.sha256(src.read_bytes()).hexdigest()
    with h5py.File(str(src), "r") as f:
        ts = f["BTCUSDT/4h/data"]["timestamp"][:]
    recs = [{"symbol": "BTCUSDT", "timeframe": "4h", "t0": int(ts[i]) * 1000} for i in (700, 600, 900)]
    lo, mid, hi = harness.event_bar_scales(recs, cache=src)
    assert (lo, mid, hi) == (1000 - (600 - harness.EVENT_BARS_PRE), (lo + 1000) // 2, 1000)
    out_root = tmp_path / "runs"
    info = harness.prepare_event_bars(out_root, lo, records=recs, cache=src)
    dst = Path(info["path"])
    assert info["reused"] is False and dst.parent == harness.event_bars_dir(out_root, lo).resolve()
    assert out_root.resolve() in dst.parents and dst != src.resolve()
    with h5py.File(str(dst), "r") as g, h5py.File(str(src), "r") as f:
        assert list(g.keys()) == ["BTCUSDT"] and list(g["BTCUSDT"].keys()) == ["4h"]
        assert g["BTCUSDT/4h/data"].dtype == f["BTCUSDT/4h/data"].dtype
        assert np.array_equal(g["BTCUSDT/4h/data"][()], f["BTCUSDT/4h/data"][1000 - lo:])
        assert g.attrs["origin"] == "icperf-t02-test" and g["BTCUSDT/4h"].attrs["series"] == "BTCUSDT/4h"
        assert int(g["BTCUSDT/4h/data"].attrs["n_source"]) == 1000
    assert hashlib.sha256(src.read_bytes()).hexdigest() == before
    assert info["identity"]["rows"] == lo and info["identity"]["source_rows"] == 1000
    assert harness.prepare_event_bars(out_root, lo, records=recs, cache=src)["reused"] is True
    assert harness.prepare_event_bars(out_root, lo, records=recs[:2], cache=src)["reused"] is False  # 身分（事件數）不同
    for bad_rows in (1000 - 600 - 1, 1001):
        with pytest.raises(harness.HarnessError):
            harness.prepare_event_bars(out_root, bad_rows, records=recs, cache=src)
    same = harness.event_bars_dir(tmp_path / "self", 5) / harness.EVENT_BARS_FILE
    same.parent.mkdir(parents=True)
    same.write_bytes(src.read_bytes())
    with pytest.raises(harness.HarnessError, match="來源"):
        harness.prepare_event_bars(tmp_path / "self", 5, records=recs, cache=same)
    with pytest.raises(harness.HarnessError):  # 事件批跨 symbol ⇒ 拒收
        harness.event_bar_scales(recs + [{"symbol": "ETHUSDT", "timeframe": "4h", "t0": int(ts[-1]) * 1000}], cache=src)
    real_cache, real_load = bars_source._DEFAULT_CACHE, bars_source.load_bars_from_kline_cache
    with harness.redirect_event_bars(dst) as reads:
        got = EventSamplePipeline.bars_from_kline_cache(["BTCUSDT"], ["4h"])
        assert len(got["BTCUSDT"]["4h"]) == lo
    assert bars_source._DEFAULT_CACHE == real_cache and bars_source.load_bars_from_kline_cache is real_load
    assert harness.real_bars_cache() == Path(real_cache)
    bars = {"path": str(dst), "identity": info["identity"], "reads": reads}
    assert harness.bars_actual(bars, lo) == lo and harness.bars_facts(bars)["bars_reads"] == 1
    for bad in ({**bars, "reads": []}, {**bars, "reads": [{"cache": str(src), "rows": {"BTCUSDT/4h": lo}}]},
                {**bars, "reads": reads + [{"cache": str(dst), "rows": {"BTCUSDT/4h": lo - 1}}]}):
        with pytest.raises(harness.HarnessError):
            harness.bars_actual(bad, lo)


def test_task02_event_rows_axis_assembly(harness: Any, scale_probe: Any) -> None:
    """SPEC v5.53 (c0)：事件入口之 K 線根數軸組裝——只含 rows 之入口主軸＝rows（points 之 x 與 scale_vector.rows＝宣告根數，
    events 為第二軸）；含 rows 與 events 之入口主軸＝events、row_axis＝rows（row_fit.axis＝rows）。反例：缺 (格, rows) 實跑
    ⇒ 點名該入口；rows 軸紀錄之 actual_scale 不等宣告 ⇒ 拒收。"""
    base = {"stage": "ev", "ic_page": False, "ic_first": False, "loop": "none", "measure": True, "no_measure_reason": None,
            "evidence": "m/x.py:1"}
    inv = {"entries": [
        {**base, "id": "m.ev:bars", "input_axes": [], "branch_cell": "event_study", "coverage_path_id": "e1",
         "unit_axis": {"axes": ["rows"], "function": "rows*n_boot"}, "scale_vector": ["rows", "events"]},
        {**base, "id": "m.ev:both", "input_axes": [], "branch_cell": "event_import", "coverage_path_id": "e2",
         "unit_axis": {"axes": ["rows", "events"], "function": "n_events*log(rows)"}, "scale_vector": ["rows", "events"]}]}
    nb, ne = (2238, 3663, 5088), (50, 101, 203)

    def fact(rows: int, events: int, cols: int = 0) -> Dict[str, Any]:
        return {"input_cols": cols, "rows": rows, "events": events, "survivors": 3, "requested_columns": None}

    runs = {("event_study", "rows"): _t02_axis_records("event_study", "rows", nb, ["m.ev:bars"], lambda s: fact(s, 203)),
            ("event_study", "events"): _t02_axis_records("event_study", "events", ne, ["m.ev:bars"],
                                                         lambda s: fact(5088, s)),
            ("event_import", "events"): _t02_axis_records("event_import", "events", ne, ["m.ev:both"],
                                                          lambda s: fact(2000, s, 500)),
            ("event_import", "rows"): _t02_axis_records("event_import", "rows", nb, ["m.ev:both"],
                                                        lambda s: fact(s, 203, 500))}
    kw = {"head": "0" * 40, "scale_probe": scale_probe, "budget_seconds": BUDGET2_UPPER_SECONDS,
          "sample_interval_seconds": 0.2, "chunk_cap": {"bytes": 1, "basis": "x"}, "require_rows": True}
    got = harness.assemble_scale_receipt(inv, runs, **kw)
    m = got["entries"]
    assert m["m.ev:bars"]["axis"] == "rows" and m["m.ev:bars"]["path"] == "event_study" and m["m.ev:bars"]["fit_axis"] == "rows"
    assert [p["rows"] for p in m["m.ev:bars"]["points"]] == list(nb)
    assert [p["scale_vector"]["rows"] for p in m["m.ev:bars"]["points"]] == list(nb)
    assert m["m.ev:bars"]["row_axis"] == "events" and [p["events"] for p in m["m.ev:bars"]["row_points"]] == list(ne)
    assert m["m.ev:both"]["axis"] == "events" and m["m.ev:both"]["row_axis"] == "rows"
    assert m["m.ev:both"]["row_fit"]["axis"] == "rows" and m["m.ev:both"]["fixed_axes"] is None
    assert [p["rows"] for p in m["m.ev:both"]["row_points"]] == list(nb)
    assert all(p["actual_scale"] == p["rows"] for p in m["m.ev:both"]["row_points"])
    assert got["schedule_coverage"]["uncovered"] == []
    for drop, victim in ((("event_import", "rows"), "m.ev:both"), (("event_study", "rows"), "m.ev:bars")):
        with pytest.raises(harness.AssemblyError) as exc:
            harness.assemble_scale_receipt(inv, {k: v for k, v in runs.items() if k != drop}, **kw)
        assert any(victim in p for p in exc.value.problems), (drop, exc.value.problems)
    bad = {**runs, ("event_import", "rows"): _t02_axis_records("event_import", "rows", nb, ["m.ev:both"],
                                                               lambda s: fact(s, 203, 500), actual=lambda s: s + 1)}
    with pytest.raises(harness.AssemblyError) as exc:
        harness.assemble_scale_receipt(inv, bad, **kw)
    assert any("m.ev:both" in p and "實際輸入點數" in p for p in exc.value.problems)


def test_task02_xsec_long_cell_and_variant(fb: Any, harness: Any, scale_probe: Any, tmp_path: Path) -> None:
    """SPEC v5.53 (c1)：夥伴長歷史格（ETHUSDT 4h；長歷史檔無 SOLUSDT 4h）＝L 格同一生成定義（同格類／週期、同判準檔覆寫，
    只換標的）；長歷史來源缺該序列 ⇒ 生成前即 FreezeError（不啟動子行程）。秒級預檢（合成 K 線快取形狀之 repo 根）：兩窗
    重疊、標籤有效列數、預設切分可達（每標的測試段＝產品 `_build_cross_sectional_global_split` 之值）、前史根數與對照格；
    夥伴序列過短 ⇒ 不可達並記產品之拒收原因。變體實跑
    `cross_sectional_long` 排入排程且不取代 `cross_sectional` 之關切分兩軸；組裝之 `variants` 段每點須走預設切分，缺變體於
    `require_variants` 下點名。"""
    assert harness.XSEC_LONG_CELLS == (fb.LONG_CELL, fb.LONG_CELL_XSEC)
    assert fb.LONG_CELLS_BY_SYMBOL[fb.LONG_CELL_XSEC_SYMBOL] == fb.LONG_CELL_XSEC
    crit = fb._criteria()
    btc, sol = fb.long_cell_descriptor(), fb.long_cell_descriptor(fb.LONG_CELL_XSEC_SYMBOL)
    assert sol["id"] == fb.LONG_CELL_XSEC and sol["symbol"] == fb.LONG_CELL_XSEC_SYMBOL and btc["id"] == fb.LONG_CELL
    assert {k: v for k, v in sol.items() if k not in ("id", "symbol")} == {k: v for k, v in btc.items()
                                                                           if k not in ("id", "symbol")}
    assert fb.long_cell_criteria(crit, fb.LONG_CELL_XSEC_SYMBOL) == fb.long_cell_criteria(crit)
    with pytest.raises(fb.FreezeError):
        fb.long_cell_descriptor("NOSUCHUSDT")
    assert fb.LONG_CELL_XSEC_SYMBOL == "ETHUSDT" and fb.LONG_CELL_XSEC == "L_ETHUSDT_4h_longhist"
    px = fb.LONG_CELL_XSEC_SYMBOL
    root = tmp_path / "repo"
    end = 1_777_320_000
    _t02_kline_h5(root / fb.LONG_CELL_SOURCE, {"BTCUSDT/4h": 2600}, end=end + 10 * _T02_4H)
    _t02_kline_h5(root / fb.LONG_CELL_LABEL_SOURCE, {"BTCUSDT/4h": 2200, f"{px}/4h": 2200}, end=end)
    chk = fb.long_cell_source_check(fb.LONG_CELL_XSEC_SYMBOL, root)
    assert chk["ok"] is False and chk["long_source"]["present"] is False and chk["label_source"]["bars"] == 2200
    with pytest.raises(fb.FreezeError, match="資料不足"):
        fb.long_cell_window(root, fb.LONG_CELL_XSEC_SYMBOL)
    with pytest.raises(fb.FreezeError):
        fb.gen_long_cell(repo_root=root, work_root=tmp_path / "w", symbol=fb.LONG_CELL_XSEC_SYMBOL)
    assert not (tmp_path / "w").exists() and not (root / fb.LONG_CELL_ROOT.format(cell=fb.LONG_CELL_XSEC)).exists()
    pre = harness.xsec_long_precheck(root)
    assert pre["generation_ready"] is False and pre["ok"] is False
    assert pre["symbols"][px]["window_from_generation_source"] is False
    assert pre["symbols"]["BTCUSDT"]["window_bars"] == 2000 and pre["symbols"]["BTCUSDT"]["label_valid_rows"] == 1999
    assert pre["symbols"]["BTCUSDT"]["pre_history_bars"] == 2600 - 10 - 2000
    assert pre["symbols"]["BTCUSDT"]["label_source_pre_history_bars"] == 200
    assert pre["overlap"]["timestamps"] == 2000 and pre["split"]["reachable"] is True
    assert pre["split"]["per_symbol_test_rows"] == {"BTCUSDT": 400, px: 400}
    assert all(r.get("missing") is True for r in pre["pre_history_references"])  # 合成根無已生成之對照格
    _t02_kline_h5(root / fb.LONG_CELL_SOURCE, {"BTCUSDT/4h": 2600, f"{px}/4h": 2600}, end=end + 10 * _T02_4H)
    assert harness.xsec_long_precheck(root)["ok"] is True
    _t02_kline_h5(root / fb.LONG_CELL_SOURCE, {"BTCUSDT/4h": 2600, f"{px}/4h": 100}, end=end)
    _t02_kline_h5(root / fb.LONG_CELL_LABEL_SOURCE, {"BTCUSDT/4h": 2200, f"{px}/4h": 100}, end=end)
    short = harness.xsec_long_precheck(root)
    assert short["split"]["reachable"] is False and "min_test_rows" in str(short["split"]["error"])
    # 排程：變體排入、cross_sectional 之關切分兩軸保留；只排主軸時不排變體
    inv = json.loads((REPO / "scripts" / "icperf_path_inventory.json").read_text(encoding="utf-8"))
    sched = harness.schedule_runs(inv)
    assert {("cross_sectional_long", "cols"), ("cross_sectional", "cols"), ("cross_sectional", "timestamps")} <= set(sched)
    assert ("cross_sectional_long", "cols") not in harness.schedule_runs(inv, second_axes=False)
    assert harness.XSEC_OVERRIDE_EXTRA == {"ic_train_test_split": False}
    var = harness.schedule_coverage(inv, sched)["variants"]["cross_sectional_long:cols"]
    assert var["scheduled"] is True and var["entries"] == sum(
        1 for e in inv["entries"] if e["measure"] and e["branch_cell"] == "cross_sectional")
    # 組裝之 variants 段
    inv2, runs2 = _t02_second_axis_case()
    kw = {"head": "0" * 40, "scale_probe": scale_probe, "budget_seconds": BUDGET2_UPPER_SECONDS,
          "sample_interval_seconds": 0.2, "chunk_cap": {"bytes": 1, "basis": "x"}, "require_rows": True}

    def vfacts(s: int) -> Dict[str, Any]:
        return {"input_cols": s, "rows": 4000, "symbols": 2, "timestamps": 2000, "requested_columns": None,
                "split_applied": True}

    vkey = ("cross_sectional_long", "cols")
    with_v = {**runs2, vkey: _t02_axis_records(*vkey, (500, 1000, 2000), ["m.x:cross"], vfacts)}
    got = harness.assemble_scale_receipt(inv2, with_v, require_variants=True, **kw)
    v = got["entries"]["m.x:cross"]["variants"]["cross_sectional_long:cols"]
    assert [p["input_cols"] for p in v["points"]] == [500, 1000, 2000] and v["split"] == "default"
    assert v["fit"]["axis"] == "cols" and got["entries"]["m.x:mw"]["variants"] is None
    with pytest.raises(harness.AssemblyError) as exc:
        harness.assemble_scale_receipt(inv2, runs2, require_variants=True, **kw)
    assert any("m.x:cross" in p and "cross_sectional_long" in p for p in exc.value.problems)
    assert harness.assemble_scale_receipt(inv2, runs2, **kw)["entries"]["m.x:cross"]["variants"] is None
    nosplit = {**runs2, vkey: _t02_axis_records(*vkey, (500, 1000, 2000), ["m.x:cross"],
                                                lambda s: {**vfacts(s), "split_applied": False})}
    with pytest.raises(harness.AssemblyError) as exc:
        harness.assemble_scale_receipt(inv2, nosplit, require_variants=True, **kw)
    assert any("m.x:cross" in p and "預設切分" in p for p in exc.value.problems)


def test_task02_projection_run_root(harness: Any, tmp_path: Path) -> None:
    """事件研究投影分支之 FF run 定位：產品 `canonical_holdout.resolve_run_dir`（repo_root 未給 ⇒ 模組所在 repo 根之
    data_cache/features）於 `projection_run_root` 內改以隔離 cwd 為根、命中以 symlink 引入之 run（經產品之 locator 出口
    `create_feature_run_locator` 亦然）；離開即還原（同一 config_hash 於 repo 根找不到 ⇒ 產品之 feature_run_not_found）。
    反例：run 無 manifest、cwd 為 repo 根 ⇒ 拒收。"""
    from momentum.Analysis.event_samples import canonical_holdout as ch
    from momentum.factories import create_feature_run_locator

    run_dir = tmp_path / "store" / "features" / "BTCUSDT" / "4h" / "icperft02probe00000000000000000000"
    run_dir.mkdir(parents=True)
    (run_dir / "feature_manifest.json").write_text("{}", encoding="utf-8")
    run = {"run_dir": str(run_dir), "symbol": "BTCUSDT", "timeframe": "4h", "config_hash": run_dir.name}
    cwd = tmp_path / "cwd"
    orig = ch.resolve_run_dir
    with harness.projection_run_root(cwd, run) as linked:
        assert linked == cwd.resolve() / "data_cache" / "features" / "BTCUSDT" / "4h" / run_dir.name and linked.is_symlink()
        assert Path(os.path.realpath(linked)) == run_dir.resolve()
        locate = create_feature_run_locator()[0]
        assert locate(run_dir.name, symbols=["BTCUSDT"]) == linked
        assert ch.resolve_run_dir(run_dir.name, symbols=["BTCUSDT"]) == linked
    assert ch.resolve_run_dir is orig
    with pytest.raises(ch.CanonicalHoldoutError, match="feature_run_not_found"):
        ch.resolve_run_dir(run_dir.name, symbols=["BTCUSDT"])
    (run_dir / "feature_manifest.json").unlink()
    with pytest.raises(harness.HarnessError):
        with harness.projection_run_root(tmp_path / "cwd2", run):
            pass
    (run_dir / "feature_manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(harness.HarnessError, match="repo 根"):
        with harness.projection_run_root(REPO, run):
            pass


# ── SPEC v5.55 (d)(e)(f)(g2)(h)：量測工具補完之秒級契約（不跑量測） ─────────────────────────────────────────────


#: SPEC v5.55 (d)：IC 頁預設路徑因第 5 段零通過而 0 呼叫之 8 入口（2026-11-01 估時 problems.json 實查）
V555_RELAXED_ENTRIES = (
    "momentum.Analysis.redundancy_filter:RedundancyFilter.filter",
    "momentum.Analysis.redundancy_filter:RedundancyFilter.compute_correlation_matrix",
    "momentum.Analysis.redundancy_filter:RedundancyFilter.greedy_dedup",
    "momentum.Analysis.redundancy_filter:RedundancyFilter.compute_diversification_metrics",
    "momentum.Analysis.marginal_ic:normal_scores",
    "momentum.Analysis.marginal_ic:fit_projection",
    "momentum.Analysis.factor_combiner:block_bootstrap_ci",
    "momentum.Analysis.ic_reporter:ICReporter.save_filtered_features",
)
#: SPEC v5.55 (f)：深度分析預設設定下 0 呼叫之入口 ⇒ 其直接呼叫格
V555_DEEP_CELLS = {
    "momentum.Analysis.factor_orthogonalizer:FactorOrthogonalizer.pca_orthogonalize": "orthogonalize_pca",
    "momentum.Analysis.factor_exposure_analyzer:FactorExposureAnalyzer._apply_beta_neutralization": "exposure_beta_neutral",
    "momentum.Analysis.parameter_sensitivity_analyzer:ParameterSensitivityAnalyzer.analyze_from_variants":
        "param_sensitivity_family",
    "momentum.Analysis.parameter_sensitivity_analyzer:ParameterSensitivityAnalyzer._compute_rolling_icir":
        "param_sensitivity_family",
    "momentum.Analysis.parameter_sensitivity_analyzer:ParameterSensitivityAnalyzer._rolling_corr": "param_sensitivity_pearson",
}


def _v555_inventory() -> Dict[str, Any]:
    return json.loads((REPO / "scripts" / "icperf_path_inventory.json").read_text(encoding="utf-8"))


def _v555_ctx(harness: Any, run_id: str, axis: str, scale: int, root: Path) -> Any:
    return harness.RunContext(run_id, axis, scale, root, root, harness.Recorder(heartbeat=False), None)


def test_task02_v555_relaxed_branch_owns_zero_pass_entries(fb: Any, harness: Any, tmp_path: Path) -> None:
    """SPEC v5.55 (d)：預設路徑因第 5 段零通過而 0 呼叫之 8 入口歸非預設門檻分支 `ic_page_relaxed`（兩軸、寫 R 群組存檔供冗餘
    三格）；其請求＝L 格 IC 頁請求只覆寫第 5 段門檻（`RELAXED_THRESHOLDS` ⊆ ThresholdsConfig 欄、其餘 config_override 逐鍵
    相同）；排程先於冗餘格與 IC 後轉換 survivors 軸；存檔目錄依群組分開（不與 IC 頁預設之 L<cols>_rows<R> 相撞）、子集不分群組。
    路徑事實分別記第 5 段通過數、第 6 段輸入數與存活數，兩段計數不符 ⇒ 拒收。反例：任一入口歸屬改回 ic_page_default ⇒ 紅。"""
    from momentum.Analysis.ic_config_schema import ThresholdsConfig

    inv = _v555_inventory()
    assert fb.inventory_problems(inv) == []
    by = {e["id"]: e for e in inv["entries"]}
    for eid in V555_RELAXED_ENTRIES:
        assert by[eid]["measure"] is True and by[eid]["branch_cell"] == "ic_page_relaxed", eid
    assert "ic_page_relaxed" in harness.PATHS and harness.RUN_AXES["ic_page_relaxed"] == ("cols", "rows")
    assert harness.ROW_AXIS_RUN["ic_page_relaxed"] == "ic_page_relaxed" and "ic_page_relaxed" in harness.LONG_RUNS
    assert {("ic_page_relaxed", "cols"), ("ic_page_relaxed", "rows")} <= set(harness.CAPTURE_RUNS)
    red = ("redundancy_hierarchical", "redundancy_vif", "redundancy_diversification")
    assert all(harness.CELL_GROUP[c] == "R" for c in red)
    # 只覆寫第 5 段門檻（其餘同 IC 頁預設）
    assert harness.RELAXED_THRESHOLDS and set(harness.RELAXED_THRESHOLDS) <= set(ThresholdsConfig.model_fields)
    base = harness._limited_request("ic_report", fb.LONG_CELL, 20)
    rel = harness.relaxed_request(20)
    assert rel["threshold_branch"] == "non_default" and rel["threshold_override"] == harness.RELAXED_THRESHOLDS
    def strip(r: Mapping[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in r.items() if k not in ("config_override", "threshold_branch", "threshold_override")}
    assert strip(rel) == strip(base)
    ov_b, ov_r = copy.deepcopy(base["config_override"]), copy.deepcopy(rel["config_override"])
    assert ov_r.pop("thresholds") == {**ov_b.pop("thresholds"), **harness.RELAXED_THRESHOLDS} and ov_r == ov_b
    rows_req = harness.relaxed_request(20, rows=1000)
    assert rows_req["config_override"]["ic_calculation"]["rolling_windows"] == \
        harness.ROW_AXIS_WINDOW_OVERRIDE["rolling_windows"]
    # 排程：非預設門檻分支先於讀其存檔／任務者
    sched = harness.schedule_runs(inv)
    i = sched.index(("ic_page_relaxed", "cols"))
    assert i < sched.index(("post_ic_transform", "survivors")) and all(i < sched.index((c, "cols")) for c in red)
    j = sched.index(("ic_page_relaxed", "rows"))
    assert all(j < sched.index((c, "rows")) for c in red if (c, "rows") in sched)
    # 存檔目錄依群組分開；子集不分群組
    assert _v555_ctx(harness, "ic_page_default", "cols", 500, tmp_path).stage_tag(None) == "500"
    assert _v555_ctx(harness, "ic_page_long", "rows", 1000, tmp_path).stage_tag(1000) == "L500_rows1000"
    assert _v555_ctx(harness, "ic_page_relaxed", "cols", 500, tmp_path).stage_tag(None) == "RL500"
    assert _v555_ctx(harness, "ic_page_relaxed", "rows", 1000, tmp_path).stage_tag(1000) == "RL500_rows1000"
    cell = _v555_ctx(harness, "redundancy_vif", "cols", 1000, tmp_path)
    assert cell.stage_tag(None) == "RL1000" and cell.long is True
    want = harness.expected_stage_identity(cell, None)
    assert want["writer"] == ["ic_page_relaxed", "cols"] and want["subset"]["kind"] == "relaxed_threshold_run"
    assert want["subset"]["thresholds"] == harness.RELAXED_THRESHOLDS and want["subset"]["n_cols"] == 1000
    assert harness.expected_stage_identity(_v555_ctx(harness, "redundancy_vif", "rows", 1500, tmp_path), 1500)["writer"] \
        == ["ic_page_relaxed", "rows"]
    # 路徑事實：分別記實值；第 5 段通過數 ≠ 第 6 段輸入數 ⇒ 拒收
    rep = {"filter_log": {"stage5_thresholds": {"input_features": 500, "output_features": {"count": 120}},
                          "stage6_redundancy": {"input_features": 120, "output_features": 41}}}
    facts = harness.relaxed_facts(rep, 40)
    assert (facts["stage5_input"], facts["stage5_passed"], facts["stage6_input"], facts["stage6_output"],
            facts["survivors"], facts["threshold_branch"]) == (500, 120, 120, 41, 40, "non_default")
    rep["filter_log"]["stage6_redundancy"]["input_features"] = 119
    with pytest.raises(harness.HarnessError, match="第 5 段通過數"):
        harness.relaxed_facts(rep, 40)
    # 切分事實取 analyzer 實際所用之遮罩（服務路徑帶 feature_filter 時報告 metadata 不留 ic_train_test_split）
    class _A:
        _ic_cache = {"split_context": {"train_mask": np.array([True] * 6 + [False] * 4),
                                       "test_mask": np.array([False] * 7 + [True] * 3)}}
    sp = harness._split_facts_from_cache(_A(), {"analysis_status": "degraded_full_sample", "metadata": {}})
    assert (sp["split_applied"], sp["split_train_rows"], sp["split_test_rows"]) == (True, 6, 3)
    assert sp["report_analysis_status"] == "degraded_full_sample"
    _A._ic_cache = {"split_context": None}
    assert harness._split_facts_from_cache(_A(), {})["split_applied"] is False


def test_task02_v555_post_ic_survivors_axis(harness: Any, scale_probe: Any, tmp_path: Path) -> None:
    """SPEC v5.55 (e)：IC 後轉換主軸＝survivors（清冊 13 入口 unit_axis 含 survivors；rows 為第二軸；SPEC v5.57 (s)：
    `_transform_single_optimized_df_core` IC 頁不可達、measure=false，原 14→13），三點＝ic_page_relaxed 各
    cols 點存下之真實 IC 任務之實際倖存數（`post_ic_survivor_scales`；缺、0 或不互異 ⇒ 不成立，不以目標值充數）；規模點 ⇒
    恰一份存檔任務；組裝之 x 軸＝survivors。反例：主軸改回 cols（只有 cols 軸實跑）⇒ 組裝點名該入口缺 survivors 軸。"""
    assert harness.primary_axis("post_ic_transform") == "survivors"
    assert harness.RUN_AXES["post_ic_transform"] == ("survivors", "rows")
    post = [e for e in _v555_inventory()["entries"] if e["measure"] and e["branch_cell"] == "post_ic_transform"]
    assert len(post) == 13 and all("survivors" in e["unit_axis"]["axes"] for e in post)
    for e in post:
        assert harness.entry_runs(e) == (("post_ic_transform", "survivors"), ("post_ic_transform", "rows"), True), e["id"]
    with pytest.raises(harness.HarnessError):
        harness.axis_scales("post_ic_transform", "survivors", cols_scales=(500,), row_scales=(), event_scales=())
    assert harness.axis_scales("post_ic_transform", "survivors", cols_scales=(500,), row_scales=(), event_scales=(),
                               survivor_scales=(3, 9, 20)) == [3, 9, 20]

    def save(root: Path, n: int, k: int) -> None:
        harness.save_post_ic_task(root, n, f"t{n}", {"req_symbol": "BTCUSDT", "status": "completed", "result": {}},
                                  [f"c{i}" for i in range(k)], {"feature_filter": {"include_features": []}}, {})

    for n, k in ((500, 12), (1000, 30), (2000, 55)):
        save(tmp_path, n, k)
    got = harness.post_ic_survivor_scales(tmp_path)
    assert got["ok"] is True and got["scales"] == [12, 30, 55] and got["by_cols"] == {500: 12, 1000: 30, 2000: 55}
    assert harness._survivor_task_for(tmp_path, 30)["cols"] == 1000
    with pytest.raises(harness.HarnessError):
        harness._survivor_task_for(tmp_path, 31)
    save(tmp_path, 2000, 30)  # 不互異
    assert harness.post_ic_survivor_scales(tmp_path)["ok"] is False
    with pytest.raises(harness.HarnessError):
        harness._survivor_task_for(tmp_path, 30)
    save(tmp_path, 2000, 0)  # 0 倖存
    assert harness.post_ic_survivor_scales(tmp_path)["ok"] is False
    part = tmp_path / "partial"
    save(part, 500, 12)  # 缺點
    assert harness.post_ic_survivor_scales(part)["ok"] is False
    side = harness.post_ic_survivors_dir(part, 500) / harness.SUBSET_IDENTITY_FILE
    harness.write_identity(side, {**json.loads(side.read_text(encoding="utf-8")), "thresholds": {"p_value_max": 0.05}})
    with pytest.raises(harness.HarnessError, match="身分"):
        harness.load_post_ic_task(part, 500)
    # 組裝：x 軸＝survivors、點帶非預設門檻分支標記；主軸改回 cols ⇒ 拒收
    base = {"stage": "post_ic_transform", "ic_page": True, "ic_first": False, "loop": "none", "measure": True,
            "no_measure_reason": None, "evidence": "m/x.py:1"}
    inv = {"entries": [{**base, "id": "m.x:post", "input_axes": ["passed_cols", "rows"], "branch_cell": "post_ic_transform",
                        "coverage_path_id": "c4", "unit_axis": {"axes": ["rows", "survivors"], "function": "survivors*rows*W"},
                        "scale_vector": ["rows", "survivors"]}]}
    kw = {"head": "0" * 40, "scale_probe": scale_probe, "budget_seconds": BUDGET2_UPPER_SECONDS,
          "sample_interval_seconds": 0.2, "chunk_cap": {"bytes": 1, "basis": "x"}}
    runs = {("post_ic_transform", "survivors"): _t02_axis_records(
        "post_ic_transform", "survivors", (12, 30, 55), ["m.x:post"],
        lambda s: {"input_cols": 500, "rows": 2000, "survivors": s, "requested_columns": None,
                   "threshold_branch": "non_default"})}
    m = harness.assemble_scale_receipt(inv, runs, **kw)["entries"]["m.x:post"]
    assert m["axis"] == "survivors" and m["fit_axis"] == "survivors"
    assert [p["survivors"] for p in m["points"]] == [12, 30, 55]
    assert [p["scale_vector"]["survivors"] for p in m["points"]] == [12, 30, 55]
    assert all(p["threshold_branch"] == "non_default" for p in m["points"])
    old = {("post_ic_transform", "cols"): _t02_axis_records(
        "post_ic_transform", "cols", (500, 1000, 2000), ["m.x:post"],
        lambda s: {"input_cols": s, "rows": 500, "survivors": 7, "requested_columns": None})}
    with pytest.raises(harness.AssemblyError) as exc:
        harness.assemble_scale_receipt(inv, old, **kw)
    assert any("m.x:post" in p and "survivors" in p for p in exc.value.problems)


def test_task02_v555_deep_zero_call_cells(harness: Any, tmp_path: Path, monkeypatch: Any) -> None:
    """SPEC v5.55 (f)：深度分析預設設定下 0 呼叫之 5 入口之可達條件（碼證：正交化 method 預設 gram_schmidt、中和 mode 預設
    none、參數敏感度須入選欄含 ≥ min_family_size 之家族且 `_rolling_corr` 另須非 spearman）⇒ 各歸讀深度分析存檔（D 群組）之
    直接呼叫格；格以非預設設定呼叫該分支（spy 計其呼叫）。反例：pca 格改呼 gram_schmidt、beta 格不傳 beta_neutral、參數敏感度
    不併入家族或 pearson 格改 spearman ⇒ 目標入口 0 呼叫（紅）。"""
    from momentum.Analysis.factor_exposure_analyzer import FactorExposureAnalyzer
    from momentum.Analysis.factor_orthogonalizer import FactorOrthogonalizer
    from momentum.Analysis.ic_config_schema import ICConfig
    from momentum.Analysis.parameter_sensitivity_analyzer import ParameterSensitivityAnalyzer as PSA

    by = {e["id"]: e for e in _v555_inventory()["entries"]}
    for eid, cell in V555_DEEP_CELLS.items():
        assert by[eid]["measure"] is True and by[eid]["branch_cell"] == cell, eid
        assert cell in harness.CELLS and harness.CELL_GROUP[cell] == "D", cell
        # 參數敏感度兩格只量 rows 軸（C 格子集無 ≥ 3 員家族，見 PARAM_ROWS_ONLY_CELLS 之碼證）；其餘兩軸
        assert harness.RUN_AXES[cell] == (("rows",) if cell in harness.PARAM_ROWS_ONLY_CELLS else ("cols", "rows")), cell
        assert harness.entry_runs(by[eid])[0] == (cell, "rows" if cell in harness.PARAM_ROWS_ONLY_CELLS else "cols"), eid
        assert set(harness.CELL_CAPTURES[cell]) <= {n for n, _r in harness.CAPTURES.values()}, cell
    assert {("deep_analysis", "cols"), ("deep_analysis_long", "rows")} <= set(harness.CAPTURE_RUNS)
    cfg = ICConfig()
    assert cfg.factor_orthogonalization.method == "gram_schmidt" and cfg.factor_exposure.neutralization_mode == "none"
    assert cfg.global_settings.default_method == "spearman"
    sched = harness.schedule_runs(_v555_inventory())
    for cell in set(V555_DEEP_CELLS.values()):
        if cell not in harness.PARAM_ROWS_ONLY_CELLS:
            assert sched.index(("deep_analysis", "cols")) < sched.index((cell, "cols"))
        else:
            assert (cell, "cols") not in sched
        assert sched.index(("deep_analysis_long", "rows")) < sched.index((cell, "rows")), cell
    d = _v555_ctx(harness, "orthogonalize_pca", "rows", 1500, tmp_path)
    assert d.stage_tag(1500) == "DL500_rows1500" and d.subset_tag(1500) == "L500_rows1500"
    assert _v555_ctx(harness, "deep_analysis", "cols", 500, tmp_path).stage_tag(None) == "D500"
    assert harness.expected_stage_identity(d, 1500)["writer"] == ["deep_analysis_long", "rows"]

    rng = np.random.default_rng(5)
    idx = pd.date_range("2024-01-01", periods=120, freq="4h")
    names = ["a_5", "a_10", "a_20", "b_3", "b_5", "b_8", "b_13", "x", "y"]
    full = pd.DataFrame(rng.normal(size=(len(idx), len(names))), index=idx, columns=names)
    labels = pd.Series(rng.normal(size=len(idx)), index=idx)
    counts: Dict[str, int] = {}

    def spy(owner: Any, name: str, static: bool = False) -> None:
        raw = owner.__dict__[name]
        fn = raw.__func__ if isinstance(raw, staticmethod) else raw

        def wrapped(*a: Any, **k: Any) -> Any:
            counts[name] = counts.get(name, 0) + 1
            return fn(*a, **k)
        monkeypatch.setattr(owner, name, staticmethod(wrapped) if static else wrapped)

    spy(FactorOrthogonalizer, "pca_orthogonalize")
    spy(FactorExposureAnalyzer, "_apply_beta_neutralization")
    spy(PSA, "analyze_from_variants")
    spy(PSA, "_rolling_corr", static=True)
    ctx = _v555_ctx(harness, "orthogonalize_pca", "cols", 500, tmp_path)
    caps = {"orthogonalize": {"self": FactorOrthogonalizer({}), "args": (full[["x", "y", "a_5"]],), "kwargs": {},
                              "provenance": {}},
            "neutralize": {"self": FactorExposureAnalyzer({}), "args": (),
                           "kwargs": {"factor_values": full[["x", "y"]], "market_proxy": labels.shift(1), "mode": "none",
                                      "lookback": 63}, "provenance": {}}}
    monkeypatch.setattr(harness, "cell_capture", lambda c, name: caps[name])
    assert harness._cell_pca(ctx)["survivors"] == 3 and counts.get("pca_orthogonalize") == 1
    assert harness._cell_beta_neutral(ctx)["survivors"] == 2 and counts.get("_apply_beta_neutralization") == 1
    # 參數敏感度：家族＝產品 detect_feature_families 之最小完整家族（a，3 員）併入入選欄
    ps = PSA({"icir_window": 20})
    cap = {"self": ps, "args": (full[["x", "y"]], labels),
           "kwargs": {"metadata": None, "method": "spearman", "direction": {}}, "provenance": {}}
    frame, kwargs, facts = harness.param_family_frame(cap, {"result": (full, {})})
    assert list(frame.columns) == ["x", "y", "a_5", "a_10", "a_20"] and facts["family"] == "a"
    with pytest.raises(harness.HarnessError, match="不一致"):
        harness.param_family_frame(cap, {"result": (full.assign(x=full["x"] + 1.0), {})})
    with pytest.raises(harness.HarnessError, match="參數家族"):
        harness.param_family_frame(cap, {"result": (full[["x", "y"]], {})})
    caps.update(param_sensitivity=cap, preprocess={"result": (full, {})})
    counts.clear()
    harness._cell_param_sensitivity(None)(ctx)
    assert counts.get("analyze_from_variants", 0) >= 1 and counts.get("_rolling_corr", 0) == 0  # spearman ⇒ 不走 _rolling_corr
    counts.clear()
    harness._cell_param_sensitivity("pearson")(ctx)
    assert counts.get("analyze_from_variants", 0) >= 1 and counts.get("_rolling_corr", 0) >= 1
    counts.clear()
    PSA.batch_analyze(ps, full[["x", "y"]], labels, metadata=None, method="pearson", direction={})
    assert counts.get("analyze_from_variants", 0) == 0  # 不併入家族（預設入選欄）⇒ 0 呼叫（碼證之對照）


def test_task02_v555_event_scales_from_split_precheck(fb: Any, harness: Any, tmp_path: Path, monkeypatch: Any) -> None:
    """SPEC v5.55 (g2)：凍結腳本之事件數軸三點取自切分預檢——`_event_scales` 預檢 ok 時回其三點、不成立時 FreezeError；
    `measure_inventory` 之 events 軸經 `_event_scales(h, root)`。預檢本身之選點與產品實跑判定（v5.56 (j)(n)：等距抽樣、
    產品計數鏈、effective mode 與二元三入口 calls）由 `test_task02_v556_event_precheck_product_chain` 與
    `test_task02_v556_event_axis_dense_batch_equidistant` 驗；本測試原「前 n 筆、不經產品實跑」之斷言隨 v5.56 退役。"""
    import inspect

    class H:
        def __init__(self, out: Dict[str, Any]) -> None:
            self.out, self.seen = out, []

        def event_axis_precheck(self, out_root: Any = None) -> Dict[str, Any]:
            self.seen.append(out_root)
            return self.out

    ok = H({"ok": True, "scales": [192, 197, 203]})
    assert fb._event_scales(ok, tmp_path) == ([192, 197, 203], ok.out) and ok.seen == [tmp_path]
    with pytest.raises(fb.FreezeError, match="g2"):
        fb._event_scales(H({"ok": False, "scales": [], "reason": "可達點 2 個 < 3"}))
    src = inspect.getsource(fb.measure_inventory)
    assert "_event_scales(h, root)" in src  # measure_inventory 之 events 軸三點取自切分預檢


def test_task02_v555_three_points_always_run(fb: Any, harness: Any) -> None:
    """SPEC v5.55 (h)（`docs/NOCAP_SPEC.md:23`）：不新增依推估耗時決定是否啟動某規模點之行為——`measure_inventory` 不引用兩點
    推估（`projected_2000_seconds`／`two_point_seconds` 只在組裝階段之既有兩點例外標記）；排程之每一 (路徑, 軸) 之規模點
    恰為該軸宣告之三點（不依任何耗時縮減）。反例：於排程或驅動層依推估秒數略過 2,000 欄點 ⇒ 紅。"""
    import inspect

    tree = ast.parse(textwrap.dedent(inspect.getsource(fb.measure_inventory)))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} \
        | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not names & {"projected_2000_seconds", "total_projected_seconds", "two_point_seconds", "unit_cost",
                        "fit_points"}, names & {"projected_2000_seconds", "total_projected_seconds", "two_point_seconds"}
    kws = [k.arg for n in ast.walk(tree) if isinstance(n, ast.Call) for k in n.keywords]
    assert kws.count("budget_seconds") == 1  # 只傳給組裝（既有兩點例外標記），不用於啟動判定
    for run_id, axis in harness.schedule_runs(_v555_inventory()):
        if axis == "rows" and run_id in harness.EVENT_BARS_RUN.values():
            continue  # K 線根數軸三點由真實快取導出（另測）
        pts = harness.axis_scales(run_id, axis, cols_scales=(500, 1000, 2000), row_scales=(1000, 1500, 2000),
                                  event_scales=(192, 197, 203), survivor_scales=(12, 30, 55))
        assert len(pts) == 3 and len(set(pts)) == 3, (run_id, axis, pts)


# ── SPEC v5.56 (j)–(p)（code review r67 處置）：量測工具 ────────────────────────────────────────────────────────


def _v556_events(k: int, test_from: int, pos_every: int = 2) -> List[Dict[str, Any]]:
    """合成事件（t0＝epoch 毫秒等距；第 `test_from` 筆起之 t0 落在測試段；標籤每 `pos_every` 筆一個 1）。"""
    return [{"event_id": f"e{i}", "t0": 1_700_000_000_000 + i * 3_600_000, "label": int(i % pos_every == 0)}
            for i in range(k)]


def test_task02_v556_event_precheck_product_chain(harness: Any, tmp_path: Path, monkeypatch: Any) -> None:
    """SPEC v5.56 (j)：事件數軸預檢走產品之同一計數鏈——①兩類計數經產品 `split_preview.count_binary_classes_in_rows`（以 run 之
    post-trim 時間軸〔DatetimeIndex〕之測試段／訓練段列位置呼叫；spy 證其被呼叫且結果＝自寫 oracle）；②三點複驗另以產品實跑
    （`event_point_product_check`）斷言 effective mode＝imported_binary 且二元三入口 calls ≥ 1，任一點不成立 ⇒ ok False；
    ③單點判定 `event_product_verdict` 為純函式（例外、非 imported_binary、任一入口 0 呼叫皆不成立）。
    mutation：①改回自寫鍵比對（不呼叫產品函式）⇒ spy 0 呼叫（紅）；②刪除產品實跑之 effective 斷言 ⇒ return_rule 情境回 ok True
    （紅）；③verdict 忽略 calls ⇒ 缺呼叫情境回 ok True（紅）。"""
    import momentum.core.split_preview as sp

    # ① 產品計數函式（plan 直接給：DatetimeIndex 10 列、末 4 列測試段、前 5 列訓練段）
    idx = pd.date_range("2024-01-01", periods=10, freq="4h")
    ms = (idx.asi8 // 10 ** 6).astype("int64")
    plan = {"index": idx, "ms": ms, "test_rows": [6, 7, 8, 9], "train_rows": [0, 1, 2, 3, 4], "min_test_events": 2,
            "min_events_per_class": 1, "purge_rows": 1, "embargo_rows": 0, "split_reason": None}
    labels = {int(ms[i]): int(i % 2) for i in (0, 2, 3, 6, 7, 9)}
    staged = {"event_timestamps": list(labels), "event_binary_labels": labels}
    seen: List[Any] = []
    orig = sp.count_binary_classes_in_rows

    def spy(b: Any, fi: Any, rows: Any) -> Any:
        seen.append((type(pd.Index(fi)).__name__, list(np.asarray(rows))))
        return orig(b, fi, rows)

    monkeypatch.setattr(sp, "count_binary_classes_in_rows", spy)
    got = harness.event_split_counts(staged, {}, Path("x"), plan=plan)
    oracle_test = [labels[int(ms[i])] for i in (6, 7, 9)]
    oracle_train = [labels[int(ms[i])] for i in (0, 2, 3)]
    assert (got["test_events"], got["test_pos"], got["test_neg"]) == (3, sum(oracle_test), 3 - sum(oracle_test))
    assert (got["train_events"], got["train_pos"], got["train_neg"]) == (3, sum(oracle_train), 3 - sum(oracle_train))
    assert got["oos"] and got["binary"] and got["count_function"].endswith("count_binary_classes_in_rows")
    assert ("DatetimeIndex", [6, 7, 8, 9]) in seen and ("DatetimeIndex", [0, 1, 2, 3, 4]) in seen
    sub = harness.event_split_counts(staged, {}, Path("x"), [int(ms[6]), int(ms[0])], plan=plan)
    assert (sub["test_events"], sub["test_pos"] + sub["test_neg"]) == (1, 1)  # 子集只計其鍵

    # ② 預檢之三點產品實跑斷言（資料讀取以替身；產品實跑之真實資料見 `precheck-events` CLI）
    records = _v556_events(40, 30)
    monkeypatch.setattr(harness, "_event_axis_batch", lambda: [dict(r) for r in records])
    monkeypatch.setattr(harness, "_limited_request", lambda item, cell, n: {"run_dir": "x", "timeframe": "4h"})

    import contextlib

    @contextlib.contextmanager
    def iso(root: Path, tag: str) -> Any:
        yield tmp_path

    monkeypatch.setattr(harness, "_prepare_isolation", iso)
    monkeypatch.setattr(harness, "_event_stage", lambda recs, work, req, man: {
        "event_label_owners": {int(r["t0"]): r["event_id"] for r in recs},
        "event_timestamps": [int(r["t0"]) for r in recs],
        "event_binary_labels": {int(r["t0"]): int(r["label"]) for r in recs}})
    t_test = int(records[30]["t0"])

    def counts(staged: Mapping[str, Any], request: Any, manifest: Path, keys: Any = None, **kw: Any) -> Dict[str, Any]:
        ks = list(staged["event_timestamps"] if keys is None else keys)
        lab = staged["event_binary_labels"]
        test = [k for k in ks if k >= t_test]
        pos = sum(lab[k] for k in test)
        return {"oos": len(test) >= 3, "binary": min(pos, len(test) - pos) >= 1, "test_events": len(test),
                "train_events": len(ks) - len(test), "test_pos": pos, "test_neg": len(test) - pos}

    monkeypatch.setattr(harness, "event_split_counts", counts)
    full_calls = {e: 2 for e in harness.EVENT_BINARY_ENTRIES}
    verdicts: Dict[str, Any] = {}
    monkeypatch.setattr(harness, "event_point_product_check", lambda recs, work, req: {
        **harness.event_product_verdict({"effective": verdicts["mode"]}, verdicts["calls"], None), "n": len(recs)})
    verdicts.update(mode="return_rule", calls=full_calls)
    bad = harness.event_axis_precheck(tmp_path)
    assert bad["ok"] is False and len(bad["scales"]) == 3 and "imported_binary" in bad["reason"]
    assert all(p["product"]["effective_mode"] == "return_rule" for p in bad["points"])
    verdicts.update(mode="imported_binary")
    good = harness.event_axis_precheck(tmp_path)
    assert good["ok"] is True and good["verified_by_product_run"] is True
    assert all(p["product"]["ok"] for p in good["points"])
    assert len(bad["attempts"]) == 3  # effective 錯誤（系統性）⇒ 不沿候選續試
    assert harness.event_axis_precheck(tmp_path, verify=False)["ok"] is False  # 未經產品實跑不得據以開跑
    # 首選低點因該子集之候選欄使二元某入口 0 呼叫 ⇒ 沿候選序列向中點續試（產品實跑判定），不以 0 呼叫充數
    lo = good["reachable_range"][0]
    miss0 = {**full_calls, harness.EVENT_BINARY_ENTRIES[1]: 0}
    monkeypatch.setattr(harness, "event_point_product_check", lambda recs, work, req: harness.event_product_verdict(
        {"effective": "imported_binary"}, full_calls if len(recs) > lo + 1 else miss0, None))
    moved = harness.event_axis_precheck(tmp_path)
    assert moved["ok"] is True and moved["scales"][0] > lo + 1 and moved["scales"][1:] == good["scales"][1:]
    assert any(a["role"] == "low" and a["n"] == lo and a["missing_calls"] for a in moved["attempts"])
    cand = harness.event_point_candidates(list(range(100, 200)))
    assert cand["low"][0] == 100 and cand["high"][0] == 199 and cand["mid"][0] == 149
    assert max(cand["low"]) < 149 < min(cand["high"]) and all(len(v) <= harness.EVENT_PRECHECK_MAX_TRIES
                                                             for v in cand.values())

    # ③ 單點判定
    v = harness.event_product_verdict
    assert v({"effective": "imported_binary"}, full_calls, None)["ok"] is True
    assert v({"effective": "imported_binary"}, full_calls, "ValueError: x")["ok"] is False
    assert v({"effective": "return_rule"}, full_calls, None)["ok"] is False
    miss = {**full_calls, harness.EVENT_BINARY_ENTRIES[0]: 0}
    assert v({"effective": "imported_binary"}, miss, None)["missing_calls"] == [harness.EVENT_BINARY_ENTRIES[0]]
    assert v({"effective": "imported_binary"}, miss, None)["ok"] is False
    assert v(None, full_calls, None)["ok"] is False


def test_task02_v556_event_axis_dense_batch_equidistant(harness: Any, tmp_path: Path, monkeypatch: Any) -> None:
    """SPEC v5.56 (n)：事件數軸之 Task 0.2 專用批與等距抽樣——①`event_axis_subset` 取 round(linspace(0, K−1, n)) 之位置（含首末、
    互異），測試段（時間末段）事件比例隨 n 保留（|比例差| ≤ 1/n＋1/K）；②`icperf_event_batch.build_records` 之新增參數不改凍結批
    （預設 breakout＝6 之記錄與 rule_id 與不帶參數者逐位元相同），較小之 N 產生同規則族之較密批；③事件數軸兩路徑之子集來源＝
    `_event_axis_records`（不取凍結批之前 n 筆、不寫 data_cache/events）。mutation：①改回前 n 筆 ⇒ 小 n 之測試段比例 0（紅）；
    ②預設參數改變 ⇒ 凍結批記錄不等（紅）；③事件數軸改回 `_event_batch_records(n)` ⇒ 源碼斷言紅。"""
    import h5py
    import inspect

    k, test_from = 200, 160
    records = _v556_events(k, test_from)
    full_frac = (k - test_from) / k
    for n in (20, 50, 77, 120, 200):
        sub = harness.event_axis_subset(list(reversed(records)), n)  # 輸入順序不影響（依 t0 排序）
        assert len(sub) == n and sub[0]["event_id"] == "e0" and sub[-1]["event_id"] == f"e{k - 1}"
        assert len({r["event_id"] for r in sub}) == n
        frac = sum(1 for r in sub if int(r["event_id"][1:]) >= test_from) / n
        assert abs(frac - full_frac) <= 1.0 / n + 1.0 / k, (n, frac)
    with pytest.raises(harness.HarnessError):
        harness.event_axis_subset(records, k + 1)
    assert harness.EVENT_AXIS_SAMPLING.startswith("等距抽樣")

    # ② 建批參數（tmp 真實形狀之 kline 結構陣列；只驗建批碼之參數語意，非資料驗證）
    eb = harness._load_script("icperf_t02_event_batch", "scripts/icperf_event_batch.py")
    n_bars = 400
    rng = np.random.default_rng(3)
    close = 100.0 + np.cumsum(rng.normal(size=n_bars))
    arr = np.zeros(n_bars, dtype=[("timestamp", "<i8"), ("high", "<f8"), ("close", "<f8")])
    arr["timestamp"] = 1_700_000_000_000 + np.arange(n_bars) * 14_400_000
    arr["close"], arr["high"] = close, close + np.abs(rng.normal(size=n_bars))
    src = tmp_path / "k.h5"
    with h5py.File(src, "w") as f:
        f.create_dataset("BTCUSDT/4h/data", data=arr)
    ts = pd.to_datetime(arr["timestamp"], unit="ms", utc=True)
    cell = {"cell": "L", "symbol": "BTCUSDT", "timeframe": "4h", "source": str(src),
            "output_window": [ts[50].isoformat(), ts[-1].isoformat()]}
    frozen = eb.build_records(cell)
    assert frozen == eb.build_records(cell, breakout_bars=eb.BREAKOUT_BARS, prior_field="high")
    assert eb.rule_id() == eb.RULE_ID == eb.rule_id(eb.BREAKOUT_BARS, "high")
    assert all(r["label_definition"]["rule_id"] == eb.RULE_ID for r in frozen["records"])
    dense = eb.build_records(cell, breakout_bars=harness.EVENT_AXIS_BREAKOUT_BARS,
                             prior_field=harness.EVENT_AXIS_PRIOR_FIELD)
    assert harness.EVENT_AXIS_BREAKOUT_BARS < eb.BREAKOUT_BARS and harness.EVENT_AXIS_PRIOR_FIELD in eb.PRIOR_FIELDS
    assert len(dense["records"]) > len(frozen["records"])
    assert {r["label_definition"]["rule_id"] for r in dense["records"]} == \
        {eb.rule_id(harness.EVENT_AXIS_BREAKOUT_BARS, harness.EVENT_AXIS_PRIOR_FIELD)} != {eb.RULE_ID}
    # 規則語意（oracle 自寫）：close > 前 N 根 prior_field 最大值、t+12 根在窗內
    win = pd.DataFrame({"high": arr["high"], "close": arr["close"]}, index=ts)
    lvl = win[harness.EVENT_AXIS_PRIOR_FIELD].shift(1).rolling(harness.EVENT_AXIS_BREAKOUT_BARS).max()
    w = win.loc[ts[50]:]
    hit = [int(t.value // 10 ** 6) for i, t in enumerate(w.index)
           if w["close"].iloc[i] > lvl.loc[t] and i + eb.HORIZON_BARS < len(w)]
    assert [r["t0"] for r in dense["records"]] == hit
    with pytest.raises(ValueError):
        eb.build_records(cell, breakout_bars=0)
    with pytest.raises(ValueError):
        eb.build_records(cell, prior_field="open")

    # ③ 兩路徑之事件數軸子集來源
    for fn in (harness._run_event_import, harness._run_event_study):
        src_code = inspect.getsource(fn)
        assert "_event_axis_records(" in src_code, fn.__name__
        assert "EVENT_IMPORT_ID" not in src_code
    monkeypatch.setattr(harness, "_event_axis_batch", lambda: [dict(r) for r in records])
    assert [r["event_id"] for r in harness._event_axis_records(20)] == \
        [r["event_id"] for r in harness.event_axis_subset(records, 20)]


def _v556_stage6_cap(harness: Any, frame: pd.DataFrame, scores: Mapping[str, float]) -> Dict[str, Any]:
    from momentum.Analysis.redundancy_filter import RedundancyFilter

    return {"self": RedundancyFilter({}), "args": (frame, dict(scores)), "kwargs": {"method": "greedy"},
            "provenance": {"path_run_id": "x"}}


def test_task02_v556_redundancy_rows_fixed_column_set(harness: Any, scale_probe: Any, tmp_path: Path,
                                                       monkeypatch: Any) -> None:
    """SPEC v5.56 (k)：冗餘格 rows 軸只變列數——①各 R 點之第 6 段輸入欄＝最小 rows 點之欄集合（值取該 R 點第 1 段輸出之測試段
    列、IC 分數同 R 點且限固定欄；該 R 點自身第 6 段輸入於共同欄須與第 1 段輸出逐值相等，否則拒收）；②`RedundancyFilter.filter`
    ／`compute_correlation_matrix` 之 rows 軸改由 `redundancy_greedy_rows`（ROW_AXIS_ENTRY_RUN）；③組裝斷言 rows 軸各點欄集合身分
    與欄數相同；④紀錄頂層 `threshold_branch` 取路徑事實之實際分支。mutation：①改讀 R 點自身欄集合 ⇒ 欄集合不同（紅）；
    ②刪 ROW_AXIS_ENTRY_RUN ⇒ 第二軸回 ic_page_relaxed（紅）；③組裝不比欄集合 ⇒ 不同欄集合仍組成（紅）；④頂層固定 default
    ⇒ post_ic rows non_default 紀錄為 default（紅）。"""
    rng = np.random.default_rng(11)
    cols_all = [f"f{i}" for i in range(6)]

    def full(rows: int) -> pd.DataFrame:
        idx = pd.Index(1_700_000_000 + np.arange(rows) * 14_400, dtype="int64")  # 第 1 段輸出之 epoch 秒
        return pd.DataFrame(rng.normal(size=(rows, len(cols_all))).astype("float32"), index=idx, columns=cols_all)

    pre = {1000: full(20), 1500: full(30)}

    def stage6(rows: int, cols: Sequence[str], corrupt: bool = False) -> pd.DataFrame:
        f = pre[rows]
        out = f.iloc[-5:][list(cols)].copy()
        out.index = pd.to_datetime(out.index.to_numpy(dtype="int64"), unit="s")
        if corrupt:
            out.iloc[0, 0] = np.float32(out.iloc[0, 0] + 1.0)
        return out

    scores = {c: float(i) for i, c in enumerate(cols_all)}
    caps = {("RL500_rows1000", "redundancy_filter"): _v556_stage6_cap(harness, stage6(1000, ["f0", "f1", "f2"]), scores),
            ("RL500_rows1500", "redundancy_filter"): _v556_stage6_cap(harness, stage6(1500, ["f1", "f2", "f4", "f5"]),
                                                                       scores),
            ("RL500_rows1000", "preprocess"): {"result": (pre[1000], {})},
            ("RL500_rows1500", "preprocess"): {"result": (pre[1500], {})}}
    seen: List[str] = []

    def fake_load(stage_dir: Path, name: str, expected: Any = None) -> Dict[str, Any]:
        seen.append(Path(stage_dir).name)
        return caps[(Path(stage_dir).name, name)]

    monkeypatch.setattr(harness, "load_capture", fake_load)
    monkeypatch.setattr(harness, "expected_stage_identity",
                        lambda ctx, n_rows: {"subset": {"rows": n_rows, "n_cols": 500}, "writer": ["ic_page_relaxed", "rows"]})
    # SPEC v5.57 (r)：redundancy_vif 之 rows 軸改固定 64 欄設計點（另測 test_task02_v557_vif_rows_design_point）⇒ (k) 之
    # 「最小 rows 點全部第 6 段輸入欄」語意以仍沿用之 redundancy_hierarchical 驗
    ctx = _v555_ctx(harness, "redundancy_hierarchical", "rows", 1500, tmp_path)
    cap = harness.redundancy_stage_capture(ctx, "redundancy_filter")
    frame, sc = cap["args"]
    assert list(frame.columns) == ["f0", "f1", "f2"] and frame.shape[0] == 5 and set(sc) == {"f0", "f1", "f2"}
    assert np.array_equal(frame.to_numpy(), pre[1500].iloc[-5:][["f0", "f1", "f2"]].to_numpy())
    assert ctx.actual_scale == 1500 and cap["provenance"]["verified_overlap_columns"] == 2
    ctx1 = _v555_ctx(harness, "redundancy_hierarchical", "rows", 1000, tmp_path)
    cap1 = harness.redundancy_stage_capture(ctx1, "redundancy_filter")
    assert cap1["provenance"][harness.COLUMN_SET_KEY] == cap["provenance"][harness.COLUMN_SET_KEY]
    facts = harness._cell_facts(ctx, cap)
    assert facts[harness.COLUMN_SET_KEY] == cap["provenance"][harness.COLUMN_SET_KEY] and facts["cell_input_cols"] == 3
    caps[("RL500_rows1500", "redundancy_filter")] = _v556_stage6_cap(
        harness, stage6(1500, ["f1", "f2", "f4"], corrupt=True), scores)
    with pytest.raises(harness.HarnessError, match="逐值相等"):
        harness.redundancy_stage_capture(ctx, "redundancy_filter")
    caps[("RL500_rows1500", "redundancy_filter")] = _v556_stage6_cap(harness, stage6(1500, ["f1", "f2"]),
                                                                       {"f1": 1.0, "f2": 2.0})
    with pytest.raises(harness.HarnessError, match="IC 分數"):
        harness.redundancy_stage_capture(ctx, "redundancy_filter")

    # ② 入口級 rows 軸
    by = {e["id"]: e for e in _v555_inventory()["entries"]}
    for eid in ("momentum.Analysis.redundancy_filter:RedundancyFilter.filter",
                "momentum.Analysis.redundancy_filter:RedundancyFilter.compute_correlation_matrix"):
        assert harness.entry_runs(by[eid]) == (("ic_page_relaxed", "cols"), ("redundancy_greedy_rows", "rows"), True), eid
    assert harness.RUN_AXES["redundancy_greedy_rows"] == ("rows",) and harness.CELL_GROUP["redundancy_greedy_rows"] == "R"
    assert "redundancy_greedy_rows" in harness.REDUNDANCY_STAGE_CELLS
    norm = by["momentum.Analysis.marginal_ic:normal_scores"]
    assert harness.entry_runs(norm)[1] == ("ic_page_relaxed", "rows")  # 其餘 ic_page_relaxed 入口不改

    # ③ 組裝
    inv = {"entries": [{"stage": "6", "ic_page": True, "ic_first": False, "loop": "none", "measure": True,
                        "no_measure_reason": None, "evidence": "m/x.py:1", "id": "m.x:vif",
                        "input_axes": ["passed_cols", "rows"], "branch_cell": "redundancy_hierarchical",
                        "coverage_path_id": "c1",
                        "unit_axis": {"axes": ["rows", "stage_cols"], "function": "stage_cols*rows"},
                        "scale_vector": ["rows", "stage_cols"]}]}
    kw = {"head": "0" * 40, "scale_probe": scale_probe, "budget_seconds": BUDGET2_UPPER_SECONDS,
          "sample_interval_seconds": 0.2, "chunk_cap": {"bytes": 1, "basis": "x"}, "require_rows": True}

    def runs(shas: Mapping[int, str]) -> Dict[Tuple[str, str], Any]:
        return {("redundancy_hierarchical", "cols"): _t02_axis_records(
                    "redundancy_hierarchical", "cols", harness.REDUNDANCY_STAGE_COLS_SCALES, ["m.x:vif"],
                    lambda s: {"input_cols": s, "rows": 395, "cell_input_cols": s, "requested_columns": None,
                               harness.COLUMN_SET_KEY: f"c{s}"}),
                ("redundancy_hierarchical", "rows"): _t02_axis_records(
                    "redundancy_hierarchical", "rows", (1000, 1500, 2000), ["m.x:vif"],
                    lambda s: {"input_cols": 500, "rows": s, "cell_input_cols": 7, "requested_columns": None,
                               harness.COLUMN_SET_KEY: shas[s]})}

    ok = harness.assemble_scale_receipt(inv, runs({1000: "a", 1500: "a", 2000: "a"}), **kw)["entries"]["m.x:vif"]
    assert {p[harness.COLUMN_SET_KEY] for p in ok["row_points"]} == {"a"}
    with pytest.raises(harness.AssemblyError) as exc:
        harness.assemble_scale_receipt(inv, runs({1000: "a", 1500: "b", 2000: "a"}), **kw)
    assert any("m.x:vif" in p and "欄集合" in p for p in exc.value.problems)

    # ④ 紀錄頂層門檻分支
    rtb = harness.record_threshold_branch
    assert rtb("post_ic_transform", "rows", "", {"threshold_branch": "non_default"}) == "non_default"
    assert rtb("post_ic_transform", "rows", "", {"threshold_branch": "default"}) == "default"
    assert rtb("redundancy_vif", "rows", "R", {}) == "non_default" and rtb("ic_page_long", "rows", "", {}) == "default"
    with pytest.raises(harness.HarnessError):
        rtb("x", "rows", "", {"threshold_branch": "weird"})


def test_task02_v556_redundancy_stage_cols_design_points(harness: Any, tmp_path: Path, monkeypatch: Any) -> None:
    """SPEC v5.56 (l)：冗餘格之 cols 軸＝stage_cols 設計點——①三點＝`REDUNDANCY_STAGE_COLS_SCALES`（嚴格遞增、跨度 ≥ 4 倍；不取
    cols_scales 500／1000／2000）；②輸入一律讀 `RL<REDUNDANCY_STAGE_SOURCE_COLS>`（ic_page_relaxed 500 欄點之第 6 段真實輸入；不讀
    RL2000）之 seeded 巢狀子集（SEED 同 `_write_stage5_subset`），IC 分數與 metadata 同步限所選欄；設計點 > 來源欄數 ⇒
    HarnessError。mutation：①axis_scales 回 cols_scales ⇒ 紅；②改讀 ctx.stage_dir（RL<k>）⇒ 所讀目錄非 RL500（紅）；巢狀被破壞
    （非 seeded 前綴）⇒ 子集包含斷言紅。"""
    sc = harness.REDUNDANCY_STAGE_COLS_SCALES
    assert len(sc) == 3 and list(sc) == sorted(set(sc)) and sc[-1] >= 4 * sc[0]
    for cell in ("redundancy_hierarchical", "redundancy_vif", "redundancy_diversification"):
        assert harness.axis_scales(cell, "cols", cols_scales=(500, 1000, 2000), row_scales=(), event_scales=()) == list(sc)
        assert harness.RUN_AXES[cell] == ("cols", "rows") and harness.CELL_GROUP[cell] == "R"
    assert harness.axis_scales("ic_page_relaxed", "cols", cols_scales=(500, 1000, 2000), row_scales=(),
                               event_scales=()) == [500, 1000, 2000]
    k_src = 20
    cols = [f"c{i:02d}" for i in range(k_src)]
    idx = pd.date_range("2024-01-01", periods=12, freq="4h")
    frame = pd.DataFrame(np.random.default_rng(2).normal(size=(12, k_src)), index=idx, columns=cols)
    from momentum.Analysis.redundancy_filter import RedundancyFilter

    caps = {"redundancy_filter": {"self": RedundancyFilter({}), "args": (frame, {c: 0.1 for c in cols}),
                                  "kwargs": {"method": "greedy"}, "provenance": {}},
            "diversification_metrics": {"self": RedundancyFilter({}), "args": (cols[:3], frame.corr(),
                                                                                {c: {"category": "t"} for c in cols}),
                                        "kwargs": {}, "provenance": {}}}
    seen: List[str] = []

    def fake_load(stage_dir: Path, name: str, expected: Any = None) -> Dict[str, Any]:
        seen.append(Path(stage_dir).name)
        assert expected["writer"] == ["ic_page_relaxed", "cols"]
        return caps[name]

    monkeypatch.setattr(harness, "load_capture", fake_load)
    monkeypatch.setattr(harness, "relaxed_identity", lambda n, rows=None: {"n_cols": n, "rows": rows})
    got: Dict[int, List[str]] = {}
    for k in (4, 8, 16):
        ctx = _v555_ctx(harness, "redundancy_vif", "cols", k, tmp_path)
        cap = harness.redundancy_stage_capture(ctx, "redundancy_filter")
        f, scores = cap["args"]
        got[k] = list(f.columns)
        assert f.shape == (12, k) and set(scores) == set(got[k]) and ctx.actual_scale == k
        assert got[k] == harness.seeded_columns(cols, k)
        meta = harness.redundancy_stage_capture(ctx, "diversification_metrics")
        assert set(meta["kwargs"]["metadata"]) == set(got[k])
    assert set(seen) == {f"RL{harness.REDUNDANCY_STAGE_SOURCE_COLS}"}
    assert set(got[4]) <= set(got[8]) <= set(got[16]) and got[16] != cols[:16]
    with pytest.raises(harness.HarnessError, match="資料不足"):
        harness.redundancy_stage_capture(_v555_ctx(harness, "redundancy_vif", "cols", k_src + 1, tmp_path),
                                         "redundancy_filter")


def test_task02_v556_seeded_request_columns(fb: Any, harness: Any, monkeypatch: Any) -> None:
    """SPEC v5.56 (m)：harness 請求之選欄改 seeded 隨機巢狀（`np.sort(default_rng(SEED).permutation(K)[:n])` 之位置；同
    `_write_stage5_subset`）——`_limited_request`（ic_page_relaxed 之 relaxed_request 經之）取 `seeded_columns`、巢狀；凍結項之
    `small_request` 仍為排序前綴（不改）；路徑事實之指標家族分佈。mutation：`_limited_request` 改回 small_request ⇒ 等於排序前綴
    （紅）；seeded 非巢狀（每 n 換 seed）⇒ 包含斷言紅；凍結 small_request 被改 ⇒ 前綴斷言紅。"""
    pool = [f"src_4h_trend_{'AB'[i % 2]}{i // 7}_{i}" for i in range(60)]
    base = {"kind": "ic_page", "item": "ic_report", "cell": "L", "run_dir": "x", "feature_filter": None,
            "config_override": {"thresholds": {}}}
    hfb = harness._fb()  # harness 所用之凍結腳本模組（與 fb fixture 為不同模組物件）
    monkeypatch.setattr(hfb, "default_request", lambda item, cell=None: copy.deepcopy(base))
    monkeypatch.setattr(hfb, "_run_feature_names", lambda req: list(pool))
    perm = np.random.default_rng(hfb.SEED).permutation(len(pool))
    picks = {}
    for n in (5, 20, 40):
        req = harness._limited_request("ic_report", "L", n)
        picks[n] = req["feature_filter"]["include_features"]
        assert picks[n] == [pool[int(i)] for i in np.sort(perm[:n])] == harness.seeded_columns(pool, n)
        assert {k: v for k, v in req.items() if k != "feature_filter"} == \
            {k: v for k, v in base.items() if k != "feature_filter"}
    assert set(picks[5]) <= set(picks[20]) <= set(picks[40]) and picks[20] != sorted(pool)[:20]
    assert hfb.small_request("ic_report", base, 20)["feature_filter"]["include_features"] == sorted(pool)[:20]
    assert fb.SEED == hfb.SEED
    with pytest.raises(harness.HarnessError):
        harness._limited_request("ic_report", "L", 61)
    dist = harness.family_distribution(["close_4h_trend_BBANDS-Lower_13", "close_4h_trend_BBANDS-Lower_20_Max-W5",
                                        "hl_4h_trend_SAR_0.02", "close_4h_trend_SMA_5"])
    assert dist["counts"] == {"close_4h_trend_BBANDS-Lower": 2, "close_4h_trend_SMA": 1, "hl_4h_trend_SAR": 1}
    assert dist["n_families"] == 3 and dist["max_family_share"] == 0.5 and dist["n_columns"] == 4
    assert "seeded_nested" in harness.REQUEST_COLUMN_RULE


def test_task02_v556_param_family_axis(harness: Any, tmp_path: Path, monkeypatch: Any) -> None:
    """SPEC v5.56 (o)：參數敏感度家族數軸——①排程：`VARIANT_RUNS` 之 families 軸變體（兩格各一，不改 rows 軸主排程），排在其
    所讀存檔之寫出實跑（deep_analysis_long rows、ic_page_long cols〔只存 preprocess〕）之後；三點＝`PARAM_FAMILY_SCALES`；
    ②`param_families_frame`：產品 detect_feature_families 之 ≥3 員家族取 F 族（巢狀）× 每族 3 員、只含家族成員欄，產品對其判定
    恰 F 族 × 3 員；batch_analyze 之 analyze_from_variants 呼叫數＝F；可用家族不足 ⇒ HarnessError。mutation：併入入選欄或不限
    3 員 ⇒ 家族大小斷言紅；家族非巢狀 ⇒ 包含斷言紅；不排變體 ⇒ 排程斷言紅。"""
    from momentum.Analysis.parameter_sensitivity_analyzer import ParameterSensitivityAnalyzer as PSA

    sched = harness.schedule_runs(_v555_inventory())
    for cell, base in harness.PARAM_FAMILY_CELLS.items():
        assert harness.VARIANT_RUNS[(cell, "families")] == base and (cell, "families") in sched
        assert sched.index(("deep_analysis_long", "rows")) < sched.index((cell, "families"))
        assert sched.index(("ic_page_long", "cols")) < sched.index((cell, "families"))
        assert harness.axis_scales(cell, "families", cols_scales=(), row_scales=(), event_scales=()) == \
            list(harness.PARAM_FAMILY_SCALES)
    assert harness.RUN_AXES["param_sensitivity_family"] == ("rows",)  # rows 軸主排程不改
    assert ("ic_page_long", "cols") in harness.CAPTURE_RUNS and harness.CAPTURE_ONLY[("ic_page_long", "cols")] == ("preprocess",)
    lc = _v555_ctx(harness, "ic_page_long", "cols", 2000, tmp_path)
    assert lc.stage_tag(None) == "L2000"
    monkeypatch.setattr(harness, "subset_identity", lambda src, n_cols, seed, rows=None: {"n_cols": n_cols, "rows": rows})
    monkeypatch.setattr(harness, "subset_source", lambda long: Path("x.h5"))
    assert harness.expected_stage_identity(lc, None)["writer"] == ["ic_page_long", "cols"]
    assert harness.expected_stage_identity(_v555_ctx(harness, "ic_page_default", "cols", 500, tmp_path), None)["writer"] \
        == ["ic_page_default", "cols"]

    rng = np.random.default_rng(9)
    idx = pd.date_range("2024-01-01", periods=150, freq="4h")
    names = [f"fam{j}_{p}" for j in range(7) for p in (3, 5, 8, 13, 21)[: 3 + (j % 3)]] + ["solo_a", "solo_b"]
    full = pd.DataFrame(rng.normal(size=(len(idx), len(names))), index=idx, columns=names)
    labels = pd.Series(rng.normal(size=len(idx)), index=idx)
    ps = PSA({"icir_window": 20})
    cap = {"self": ps, "args": (full[["solo_a", "fam0_3"]], labels),
           "kwargs": {"metadata": None, "method": "spearman", "direction": {}}, "provenance": {}}
    calls: List[str] = []
    orig = PSA.analyze_from_variants

    def spy(self: Any, *a: Any, **k: Any) -> Any:
        calls.append(k.get("feature_family"))
        return orig(self, *a, **k)

    monkeypatch.setattr(PSA, "analyze_from_variants", spy)
    fams: Dict[int, List[str]] = {}
    for f in (2, 4, 7):
        frame, kwargs, facts = harness.param_families_frame(cap, {"result": (full, {})}, f)
        got = ps.detect_feature_families(list(frame.columns), None)
        assert len(got) == f and all(len(v) == 3 for v in got.values()) and frame.shape[1] == 3 * f
        assert "solo_a" not in frame.columns and facts["survivors"] == 3 * f and facts["families"] == f
        fams[f] = facts["family_names"]
        calls.clear()
        PSA.batch_analyze(ps, frame, **kwargs)
        assert len(calls) == f
    assert set(fams[2]) <= set(fams[4]) <= set(fams[7])
    with pytest.raises(harness.HarnessError, match="資料不足"):
        harness.param_families_frame(cap, {"result": (full, {})}, 8)
    with pytest.raises(harness.HarnessError, match="不一致"):
        harness.param_families_frame(cap, {"result": (full.assign(solo_a=full["solo_a"] + 1.0), {})}, 2)


def test_task02_v556_post_ic_chunked_probe_and_optimized_arm(harness: Any, monkeypatch: Any) -> None:
    """SPEC v5.56 (p)：①`post_ic_chunked_probe` 於 `FFACT_L65_CHUNK_SIZE`＝塊寬下執行同一呼叫、期間 `Recorder.restricted` 只記
    `_transform_chunked`（其餘入口直通不計）、結束還原環境變數；目標 0 呼叫（設定未生效）或倖存欄 ≤ 塊寬 ⇒ HarnessError；
    產品 `_resolve_column_chunk_size` 讀同一環境變數；②`_transform_single_optimized_df_core` 於 IC 頁轉換不可達之碼證：契約
    IC 頁臂＝ic_first 之擇定核心 pandas_legacy、`transform_selected` 只接受該臂、forced_arm＝pandas_legacy 時
    `_can_use_optimized_dataframe_path` 恆 False。mutation：①不設環境變數 ⇒ 目標 0 呼叫 HarnessError（紅）；不限制記錄 ⇒ 其餘
    入口計數增加（紅）；②契約臂改 pandas_optimized ⇒ 斷言紅。"""
    from momentum.FeatureEngineering import numeric_view
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    rec = harness.Recorder(heartbeat=False)
    other_id = "x.y:other"
    other = harness._make_wrapper(other_id, lambda: 1, rec=rec)
    target = harness._make_wrapper(harness.POST_IC_CHUNKED_ENTRY, lambda: other(), rec=rec)
    other()  # 預設呼叫（全記）
    monkeypatch.delenv(harness.POST_IC_CHUNK_ENV, raising=False)

    def call() -> None:
        assert FeaturePreprocessor._resolve_column_chunk_size() == harness.POST_IC_CHUNK_SIZE
        if os.environ.get(harness.POST_IC_CHUNK_ENV) == str(harness.POST_IC_CHUNK_SIZE):
            target()

    got = harness.post_ic_chunked_probe(rec, call, harness.POST_IC_CHUNK_SIZE + 5)
    assert got["calls"] == 1 and got["branch"] == "non_default" and got["n_chunks"] == 2
    assert rec.stat(other_id).calls == 1 and rec.stat(harness.POST_IC_CHUNKED_ENTRY).calls == 1
    assert harness.POST_IC_CHUNK_ENV not in os.environ and rec.only is None
    with pytest.raises(harness.HarnessError, match="0 呼叫"):
        harness.post_ic_chunked_probe(rec, lambda: None, harness.POST_IC_CHUNK_SIZE + 5)
    with pytest.raises(harness.HarnessError, match="≤ 塊寬"):
        harness.post_ic_chunked_probe(rec, call, harness.POST_IC_CHUNK_SIZE)
    assert harness.POST_IC_CHUNK_SIZE < 12  # < smoke 最小倖存數（RL100 12）
    import inspect

    src = inspect.getsource(harness._run_post_ic_transform)
    assert src.count("post_ic_chunked_probe(") == 2  # survivors 軸與 rows 軸皆探
    # ② optimized core 不可達之碼證（契約與分派）
    assert numeric_view.post_ic_arm("ic_page_apply_transforms") == numeric_view.post_ic_arm("ic_first") == "pandas_legacy"
    with pytest.raises(numeric_view.NumericPolicyError):
        numeric_view.require_post_ic_core("pandas_optimized")
    fp = FeaturePreprocessor.__new__(FeaturePreprocessor)
    fp._forced_arm = "pandas_legacy"
    assert fp._can_use_optimized_dataframe_path() is False


# ── SPEC v5.57 (q)–(t)（code review r68 處置）：量測工具 ────────────────────────────────────────────────────────


V557_VIF_IDS = ("momentum.Analysis.redundancy_filter:RedundancyFilter.vif_filter",
                "momentum.Analysis.redundancy_filter:RedundancyFilter._compute_vif_scores")
V557_OPT_CORE = ("momentum.FeatureEngineering.preprocessing.feature_preprocessor:"
                 "FeaturePreprocessor._transform_single_optimized_df_core")


def _v557_requests(harness: Any, monkeypatch: Any, tmp_path: Path, n_pool: int = 600) -> Tuple[Any, List[str]]:
    """harness 所用之凍結腳本模組（`harness._fb()`）之**真實** `default_request`，只把格之 run 換成 tmp 替身（`_cell_run`：
    tmp 目錄之空 manifest）與欄名池（`_run_feature_names`）；回 (該模組, 欄名池)。"""
    hfb = harness._fb()
    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    (run_dir / "feature_manifest.json").write_text("{}", encoding="utf-8")
    pool = [f"close_4h_{('trend', 'mom', 'vol')[i % 3]}_I{i // 9}_{i}" for i in range(n_pool)]
    monkeypatch.setattr(hfb, "_cell_run", lambda cell, repo_root=None: {
        "symbol": "BTCUSDT", "timeframe": "4h", "config_hash": "h0", "run_dir": str(run_dir)})
    monkeypatch.setattr(hfb, "_run_feature_names", lambda req: list(pool))
    return hfb, pool


def test_task02_v557_event_axis_relaxed_thresholds(harness: Any, tmp_path: Path, monkeypatch: Any) -> None:
    """SPEC v5.57 (q)：事件數軸（預檢與 event_import events 軸）走非預設門檻之產品完整路徑——①`relaxed_event_request`＝事件匯入
    預設請求（真實 `default_request`）之 `config_override.thresholds` 只覆寫 `p_value_max`＝RELAXED_THRESHOLDS，其餘請求欄位
    （event_import_id、feature_filter、其餘 override）不變；②`event_axis_precheck` 以該請求驅動產品實跑（替身：只在
    p_value_max＝1.0 時第 5 段有通過欄、block_permutation_table 才有呼叫），收據頂層與每點記門檻分支與實際門檻；判定不變
    （effective＝imported_binary 且三入口 calls ≥ 1）；③`_run_event_import` events 軸送非預設門檻請求、記第 5 段實值與二元三入口
    呼叫，任一入口 0 呼叫 ⇒ HarnessError；cols 軸維持預設請求；④`_run_event_study` 不套（無第 5 段門檻消費點）。
    mutation：①不合併 RELAXED_THRESHOLDS（或改動其他門檻鍵）⇒ 門檻斷言紅；②預檢改回 `_limited_request` ⇒ 替身之低點
    block_permutation 0 呼叫、ok False（紅）；③events 軸改回預設請求 ⇒ 送出之 p_value_max 非 1.0（紅）；刪 0 呼叫之拒收 ⇒ 不拋（紅）。"""
    import contextlib

    import api.routes.ic_analysis as ria
    import api.services.case_import_service as cis

    hfb, _pool = _v557_requests(harness, monkeypatch, tmp_path)
    base = hfb.default_request("event_import_report")
    lim = harness._limited_request("event_import_report", None, 40)
    rel = harness.relaxed_event_request(40)
    th0 = dict(base["config_override"].get("thresholds") or {})
    assert harness.RELAXED_THRESHOLDS == {"p_value_max": 1.0}
    assert rel["config_override"]["thresholds"] == {**th0, "p_value_max": 1.0}
    keep = ("config_override", "threshold_branch", "threshold_override")
    assert {k: v for k, v in rel.items() if k not in keep} == {k: v for k, v in lim.items() if k not in keep}
    assert {k: v for k, v in rel["config_override"].items() if k != "thresholds"} == \
        {k: v for k, v in lim["config_override"].items() if k != "thresholds"}
    assert rel["event_import_id"] == hfb.EVENT_IMPORT_ID and rel["threshold_branch"] == "non_default"
    rep = {"filter_log": {"stage5_thresholds": {"input_features": 500, "output_features": {"count": 7},
                                                "alpha_effective": 1.0, "alpha_source": "threshold_default"}}}
    tf = harness.event_threshold_facts(rel, rep)
    assert (tf["threshold_branch"], tf["alpha_effective"], tf["alpha_source"], tf["stage5_input"], tf["stage5_output"]) \
        == ("non_default", 1.0, "threshold_default", 500, 7)
    assert tf["thresholds"]["p_value_max"] == 1.0 and tf["threshold_override"] == {"p_value_max": 1.0}
    assert harness.event_threshold_facts(lim, None)["threshold_branch"] == "default"

    # ② 預檢（資料讀取以替身；產品實跑之真實資料見 `precheck-events` CLI）
    records = _v556_events(40, 30)
    monkeypatch.setattr(harness, "_event_axis_batch", lambda: [dict(r) for r in records])

    @contextlib.contextmanager
    def iso(root: Path, tag: str) -> Any:
        yield tmp_path

    monkeypatch.setattr(harness, "_prepare_isolation", iso)
    monkeypatch.setattr(harness, "_event_stage", lambda recs, work, req, man: {
        "event_label_owners": {int(r["t0"]): r["event_id"] for r in recs},
        "event_timestamps": [int(r["t0"]) for r in recs],
        "event_binary_labels": {int(r["t0"]): int(r["label"]) for r in recs}})
    t_test = int(records[30]["t0"])

    def counts(staged: Mapping[str, Any], request: Any, manifest: Path, keys: Any = None, **kw: Any) -> Dict[str, Any]:
        ks = list(staged["event_timestamps"] if keys is None else keys)
        lab = staged["event_binary_labels"]
        test = [k for k in ks if k >= t_test]
        pos = sum(lab[k] for k in test)
        return {"oos": len(test) >= 3, "binary": min(pos, len(test) - pos) >= 1, "test_events": len(test),
                "train_events": len(ks) - len(test), "test_pos": pos, "test_neg": len(test) - pos}

    monkeypatch.setattr(harness, "event_split_counts", counts)
    sent: List[Dict[str, Any]] = []

    def product(recs: Any, work: Path, req: Mapping[str, Any]) -> Dict[str, Any]:
        sent.append(dict(req))
        calls = {e: 1 for e in harness.EVENT_BINARY_ENTRIES}
        if (req.get("config_override") or {}).get("thresholds", {}).get("p_value_max") != 1.0:
            calls[harness.EVENT_BINARY_ENTRIES[1]] = 0  # 預設門檻：第 5 段無通過欄 ⇒ block_permutation_table 0 呼叫
        return {**harness.event_product_verdict({"effective": "imported_binary"}, calls, None),
                **harness.event_threshold_facts(req, None)}

    monkeypatch.setattr(harness, "event_point_product_check", product)
    got = harness.event_axis_precheck(tmp_path)
    assert got["ok"] is True and len(got["scales"]) == 3
    assert got["threshold_branch"] == "non_default" and got["thresholds"]["p_value_max"] == 1.0
    assert got["threshold_override"] == {"p_value_max": 1.0}
    assert sent and all(r["config_override"]["thresholds"]["p_value_max"] == 1.0 for r in sent)
    assert all(p["product"]["threshold_branch"] == "non_default" and p["product"]["ok"] for p in got["points"])
    assert len(got["attempts"]) == 3  # 首選三點即成立（不需沿候選續試）

    # ③ event_import 之 events／cols 軸送出之請求與 0 呼叫之拒收
    class _Store:
        def __init__(self, storage_dir: Any = None) -> None:
            self.n = 0

        def import_records(self, records: Any, **kw: Any) -> Any:
            self.n = len(records)
            return type("R", (), {"import_id": "imp-1"})()

        def get_import(self, iid: str) -> Any:
            return type("D", (), {"records": [None] * self.n})()

    monkeypatch.setattr(cis, "EventImportService", _Store)
    monkeypatch.setattr(cis, "_event_import_service", getattr(cis, "_event_import_service", None))
    monkeypatch.setattr(ria, "_resolve_event_batch", lambda req: {"batch": True})
    monkeypatch.setattr(hfb, "_ic_analyze_request", lambda r: r)

    @contextlib.contextmanager
    def bars(ctx: Any, recs: Any) -> Any:
        yield {}

    monkeypatch.setattr(harness, "event_bars_context", bars)
    monkeypatch.setattr(harness, "_event_axis_records", lambda n: [{"event_id": f"e{i}"} for i in range(n)])
    monkeypatch.setattr(harness, "event_axis_facts", lambda: {})
    monkeypatch.setattr(harness, "_ic_facts", lambda report, analyzer, n, rows: {})
    monkeypatch.setattr(harness, "_manifest_rows", lambda req: 2000)
    svc_req: List[Dict[str, Any]] = []
    monkeypatch.setattr(harness, "_service_with_tasks", lambda request, path: svc_req.append(dict(request)) or object())
    zero: Dict[str, int] = {}

    def analysis(svc: Any, req: Any, rec: Any, **kw: Any) -> Any:
        for e in harness.EVENT_BINARY_ENTRIES:
            rec.stat(e).calls += 0 if e in zero else 1
        return "t", {"analyzer": None, "result": rep}

    monkeypatch.setattr(harness, "_service_analysis", analysis)
    out = harness._run_event_import(_v555_ctx(harness, "event_import", "events", 6, tmp_path))
    assert svc_req[-1]["config_override"]["thresholds"]["p_value_max"] == 1.0
    assert out["threshold_branch"] == "non_default" and out["alpha_effective"] == 1.0 and out["stage5_output"] == 7
    assert out["binary_calls"] == {e: 1 for e in harness.EVENT_BINARY_ENTRIES} and out["actual_scale"] == 6
    harness._run_event_import(_v555_ctx(harness, "event_import", "cols", 40, tmp_path))
    assert svc_req[-1]["config_override"] == lim["config_override"]  # cols 軸維持事件匯入預設請求
    zero[harness.EVENT_BINARY_ENTRIES[1]] = 1
    with pytest.raises(harness.HarnessError, match="0 呼叫"):
        harness._run_event_import(_v555_ctx(harness, "event_import", "events", 6, tmp_path))
    import inspect

    assert "relaxed_event_request" not in inspect.getsource(harness._run_event_study)  # ④ 無第 5 段門檻消費點


def _v557_stage6(frame: pd.DataFrame, scores: Mapping[str, float]) -> Dict[str, Any]:
    from momentum.Analysis.redundancy_filter import RedundancyFilter

    return {"self": RedundancyFilter({}), "args": (frame, dict(scores)), "kwargs": {"method": "vif"},
            "provenance": {"path_run_id": "x"}}


def test_task02_v557_vif_rows_design_point(fb: Any, harness: Any, tmp_path: Path, monkeypatch: Any) -> None:
    """SPEC v5.57 (r)：`redundancy_vif` rows 三點固定 64 欄之 seeded 設計點——①欄集合＝RL<來源欄數> 第 6 段輸入之
    `seeded_columns(·, 64)`（＝stage_cols 中點；與 cols 軸 64 欄點之欄集合 sha 相同），各 R 點相同、值取該 R 點第 1 段輸出之第 6 段
    列；設計欄不在該 R 點第 6 段輸入內時仍以該 R 點第 6 段輸入全部欄驗取值機制（不逐值相等 ⇒ 拒收）；設計點 > 來源欄數 ⇒ 資料不足；
    hierarchical／diversification／greedy_rows 維持 (k)；②組裝斷言 rows 軸欄數＝設計點且與 cols 軸設計點同欄集合；③量測環境不另設
    BLAS 執行緒（harness／凍結腳本無設定之寫法；冗餘格事實記實值）；④VIF 兩入口之時間機會併入收據；⑤凍結腳本之身分 --data 含 RL<來源>
    存檔 sidecar。mutation：①rows 改回最小 rows 點全部欄或非 seeded ⇒ 欄集合斷言紅；只驗交集 ⇒ 設計欄與第 6 段輸入不交時不驗、
    污染不拋（紅）；②組裝不比 cols 中點 ⇒ 不同欄集合仍組成（紅）；③加 `os.environ["OPENBLAS_NUM_THREADS"]=...` ⇒ 原始碼掃描紅；
    ④刪 KNOWN_TIME_OPPORTUNITIES ⇒ status none（紅）；⑤身分不含 RL500 ⇒ 紅。"""
    import inspect

    design = harness.REDUNDANCY_ROWS_DESIGN_COLS["redundancy_vif"]
    assert design == harness.REDUNDANCY_STAGE_COLS_SCALES[1] == 64
    assert set(harness.REDUNDANCY_ROWS_DESIGN_COLS) == {"redundancy_vif"}
    rng = np.random.default_rng(57)
    pool = [f"c{i:03d}" for i in range(100)]
    src_idx = pd.date_range("2024-01-01", periods=12, freq="4h")
    src = pd.DataFrame(rng.normal(size=(12, len(pool))), index=src_idx, columns=pool)
    scores = {c: float(i) for i, c in enumerate(pool)}

    def full(rows: int) -> pd.DataFrame:
        idx = pd.Index(1_700_000_000 + np.arange(rows) * 14_400, dtype="int64")  # 第 1 段輸出之 epoch 秒
        return pd.DataFrame(rng.normal(size=(rows, len(pool))).astype("float32"), index=idx, columns=pool)

    pre = {1000: full(20), 1500: full(30)}
    seeded = harness.seeded_columns(pool, design)
    outside = [c for c in pool if c not in seeded]

    def stage6(rows: int, cols: Sequence[str], corrupt: bool = False) -> pd.DataFrame:
        out = pre[rows].iloc[-5:][list(cols)].copy()
        out.index = pd.to_datetime(out.index.to_numpy(dtype="int64"), unit="s")
        if corrupt:
            out.iloc[0, 0] = np.float32(out.iloc[0, 0] + 1.0)
        return out

    caps = {("RL500", "redundancy_filter"): _v557_stage6(src, scores),
            ("RL500_rows1000", "redundancy_filter"): _v557_stage6(stage6(1000, [seeded[0], outside[0]]), scores),
            ("RL500_rows1500", "redundancy_filter"): _v557_stage6(stage6(1500, outside[1:4]), scores),
            ("RL500_rows1000", "preprocess"): {"result": (pre[1000], {})},
            ("RL500_rows1500", "preprocess"): {"result": (pre[1500], {})}}
    seen: List[str] = []

    def fake_load(stage_dir: Path, name: str, expected: Any = None) -> Dict[str, Any]:
        seen.append(Path(stage_dir).name)
        return caps[(Path(stage_dir).name, name)]

    monkeypatch.setattr(harness, "load_capture", fake_load)
    monkeypatch.setattr(harness, "relaxed_identity", lambda n, rows=None: {"n_cols": n, "rows": rows})
    monkeypatch.setattr(harness, "expected_stage_identity",
                        lambda ctx, n_rows: {"subset": {"rows": n_rows, "n_cols": 500}, "writer": ["ic_page_relaxed", "rows"]})
    col_cap = harness.redundancy_stage_capture(_v555_ctx(harness, "redundancy_vif", "cols", design, tmp_path),
                                               "redundancy_filter")
    shas = {}
    for r in (1000, 1500):
        ctx = _v555_ctx(harness, "redundancy_vif", "rows", r, tmp_path)
        seen.clear()
        cap = harness.redundancy_stage_capture(ctx, "redundancy_filter")
        frame, sc = cap["args"]
        assert list(frame.columns) == seeded and set(sc) == set(seeded) and ctx.actual_scale == r
        assert np.array_equal(frame.to_numpy(), pre[r].iloc[-5:][seeded].to_numpy())
        assert seen == ["RL500", f"RL500_rows{r}", f"RL500_rows{r}"], seen  # 設計點來源＋該 R 點（不讀最小 rows 點）
        prov = cap["provenance"]
        assert prov["design_cols"] == design and prov["fixed_columns_source"] == "RL500"
        assert prov["verified_own_columns"] == int(caps[(f"RL500_rows{r}", "redundancy_filter")]["args"][0].shape[1])
        shas[r] = prov[harness.COLUMN_SET_KEY]
        facts = harness._cell_facts(ctx, cap)
        assert facts["cell_input_cols"] == design and set(facts["blas_threads"]["env"]) == set(harness.BLAS_THREAD_ENV_KEYS)
    assert shas[1000] == shas[1500] == col_cap["provenance"][harness.COLUMN_SET_KEY]
    assert caps[("RL500_rows1500", "redundancy_filter")]["args"][0].columns.isin(seeded).sum() == 0  # 與設計欄不交
    caps[("RL500_rows1500", "redundancy_filter")] = _v557_stage6(stage6(1500, outside[1:4], corrupt=True), scores)
    with pytest.raises(harness.HarnessError, match="逐值相等"):
        harness.redundancy_stage_capture(_v555_ctx(harness, "redundancy_vif", "rows", 1500, tmp_path), "redundancy_filter")
    caps[("RL500", "redundancy_filter")] = _v557_stage6(src[pool[:design - 1]], scores)
    with pytest.raises(harness.HarnessError, match="資料不足"):
        harness.redundancy_stage_capture(_v555_ctx(harness, "redundancy_vif", "rows", 1000, tmp_path), "redundancy_filter")

    # ② 組裝之欄集合判定
    p = harness.fixed_column_set_problems
    rows_ok = [{harness.COLUMN_SET_KEY: "a", "cell_input_cols": design} for _ in range(3)]
    cols_pts = [{harness.COLUMN_SET_KEY: f"c{s}", "cell_input_cols": s} for s in harness.REDUNDANCY_STAGE_COLS_SCALES]
    cols_pts[1][harness.COLUMN_SET_KEY] = "a"
    assert p("m.x:vif", "redundancy_vif", rows_ok, col_points=cols_pts) == []
    assert p("m.x:vif", "redundancy_vif", rows_ok) == []
    cols_bad = [dict(q) for q in cols_pts]
    cols_bad[1][harness.COLUMN_SET_KEY] = "b"
    assert p("m.x:vif", "redundancy_vif", rows_ok, col_points=cols_bad)
    assert p("m.x:vif", "redundancy_vif", [{harness.COLUMN_SET_KEY: "a", "cell_input_cols": 210}] * 3)
    assert p("m.x:h", "redundancy_hierarchical", [{harness.COLUMN_SET_KEY: "a", "cell_input_cols": 210}] * 3) == []
    src_asm = textwrap.dedent(inspect.getsource(harness.assemble_scale_receipt))
    assert "col_points=" in src_asm  # 組裝傳 cols 軸之點

    # ③ 不另設 BLAS 執行緒
    keys = "|".join(harness.BLAS_THREAD_ENV_KEYS)
    for path in (REPO / "scripts" / "icperf_scale_harness.py", SCRIPT):
        text = path.read_text(encoding="utf-8")
        assert not re.search(rf"\[\s*['\"]({keys})['\"]\s*\]\s*=", text), path
        assert not re.search(rf"(setdefault|putenv)\(\s*['\"]({keys})['\"]", text), path
        assert not re.search(rf"\b({keys})\s*=\s*['\"]?\d", text), path
        assert not re.search(rf"['\"]({keys})['\"]\s*:", text), path
    bt = harness.blas_thread_facts()
    assert bt["env"] == {k: os.environ.get(k) for k in harness.BLAS_THREAD_ENV_KEYS}

    # ④ 時間機會
    crit = {"①": {"result": False, "status": None}, "②": {"result": False, "status": None}}
    for eid in V557_VIF_IDS:
        o = harness._opportunities(eid, crit, [], None)["time"]
        assert o["status"] == "planned" and "執行緒" in o["evidence"] and "vif-study" in o["evidence"], eid
    assert harness._opportunities("m.x:other", crit, [], None)["time"]["status"] == "none"
    inv = {e["id"]: e for e in _v555_inventory()["entries"]}
    assert all(inv[e]["measure"] and inv[e]["branch_cell"] == "redundancy_vif" for e in V557_VIF_IDS)

    # ⑤ 凍結腳本之身分 --data（rows 軸讀 RL<來源> 與各 R 點之存檔）
    monkeypatch.setattr(fb, "_cell_run", lambda cell, repo_root=None: {"run_dir": "data_cache/x"})
    vif = fb._task02_data("redundancy_vif", Path("x.h5"), axis="rows", out_root=tmp_path, scales=(1000, 1500, 2000))
    hier = fb._task02_data("redundancy_hierarchical", Path("x.h5"), axis="rows", out_root=tmp_path,
                           scales=(1000, 1500, 2000))
    assert any(d.endswith("stage_inputs/RL500/stage_identity.json") for d in vif)
    assert sum("RL500_rows" in d for d in vif) == 3
    assert not any(d.endswith("stage_inputs/RL500/stage_identity.json") for d in hier)


def test_task02_v557_optimized_core_not_measured(fb: Any, harness: Any) -> None:
    """SPEC v5.57 (s)：`_transform_single_optimized_df_core` 清冊 measure=false、branch_cell None、`no_measure_reason` 指向 §N
    碼證（schema 成立；不量之碼證格式同 boundary_15），post_ic 需量測入口 14→13、排程不再含之；理由所引之碼證行實含其字面（契約臂
    pandas_legacy／IC 頁 arm_ref、forced_arm 閘、唯一直接呼叫者），且全 repo 產品碼對該函式之呼叫點恰一處。mutation：清冊改回
    measure=true ⇒ 計數與排除斷言紅；契約臂或分派改動（碼證行字面不符）⇒ 紅；新增呼叫點 ⇒ 呼叫點斷言紅。"""
    inv = _v555_inventory()
    e = next(x for x in inv["entries"] if x["id"] == V557_OPT_CORE)
    assert e["measure"] is False and e["branch_cell"] is None
    assert "§N" in e["no_measure_reason"] and "v5.57 (s)" in e["no_measure_reason"]
    assert re.match(r"^[\w./-]+\.py:\d+", e["evidence"])
    assert fb.inventory_problems(inv) == []
    post = [x for x in inv["entries"] if x["measure"] and x["branch_cell"] == "post_ic_transform"]
    assert len(post) == 13 and V557_OPT_CORE not in {x["id"] for x in post}
    cov = harness.schedule_coverage(inv, harness.schedule_runs(inv))
    assert V557_OPT_CORE not in {u["id"] for u in cov["uncovered"]} and cov["measured"] == sum(
        1 for x in inv["entries"] if x["measure"])
    assert sum(len(v) for v in harness.coverage_plan(inv).values()) == cov["measured"]

    def line(rel: str, n: int) -> str:
        return (REPO / rel).read_text(encoding="utf-8").splitlines()[n - 1]

    fp = "momentum/FeatureEngineering/preprocessing/feature_preprocessor.py"
    assert '"arm": "pandas_legacy"' in line("momentum/FeatureEngineering/contracts/numeric_view.json", 9)
    assert '"arm_ref": "ic_first"' in line("momentum/FeatureEngineering/contracts/numeric_view.json", 24)
    # IC 頁呼叫端（路 U 並行改該檔 ⇒ 只驗字面存在且恰一處，不綁行號）
    svc_src = (REPO / "api" / "services" / "ic_analysis_service.py").read_text(encoding="utf-8")
    assert svc_src.count('arm=post_ic_entry_arm("ic_page_apply_transforms")') == 1
    assert 'forced_arm == "pandas_legacy"' in line(fp, 2037)
    assert "_forced_arm = arm" in line(fp, 966)
    assert "self._transform_single_optimized_df_core(features_df)" in line(fp, 2193)
    assert "def _transform_single_optimized_df_core" in line(fp, int(e["evidence"].rsplit(":", 1)[1]))
    for n, lit in ((1814, "self._transform_single_optimized_df"), (2329, "self._transform_single_optimized_df(")):
        assert lit in line(fp, n), n
    hits = []
    for root in ("momentum", "api"):
        for path in (REPO / root).rglob("*.py"):
            for i, text in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if "_transform_single_optimized_df_core(" in text and "def _transform_single_optimized_df_core" not in text:
                    hits.append(f"{path.relative_to(REPO).as_posix()}:{i}")
    assert hits == [f"{fp}:2193"], hits


def test_task02_v557_seeded_requests_event_and_post_ic_rows(harness: Any, tmp_path: Path, monkeypatch: Any) -> None:
    """SPEC v5.57 (t)：harness 請求之 seeded 選欄（`_limited_request`）涵蓋 event_import 各軸與 post-ic-rows——①事件匯入請求
    （真實 `default_request`）之 include_features＝`seeded_columns`、n 遞增巢狀、其餘請求欄位（event_import_id、config_override、
    run 身分等）逐鍵不變；②post-ic-rows 存檔身分之欄 sha＝seeded 500 欄（兩分支同一欄集合）；③凍結項請求與 harness 請求隔離：
    以同一請求物件呼叫 `_limited_request`／`relaxed_event_request` 後，該物件與其 `small_request`（排序前綴）逐位元不變；④兩路徑之
    選欄來源為 `_limited_request`（不經 small_request）。mutation：①改回 small_request ⇒ 等於排序前綴（紅）；不巢狀 ⇒ 包含斷言紅；
    遺失其他欄位 ⇒ 逐鍵相等紅；③就地改寫共用請求（不複製）⇒ 前後 JSON 不等（紅）；④源碼改呼 small_request ⇒ 紅。"""
    import inspect

    hfb, pool = _v557_requests(harness, monkeypatch, tmp_path)
    real_default = hfb.default_request
    prefix = sorted(pool)
    picks: Dict[int, List[str]] = {}
    base = real_default("event_import_report")
    for n in (5, 50, 500):
        req = harness._limited_request("event_import_report", None, n)
        picks[n] = req["feature_filter"]["include_features"]
        assert picks[n] == harness.seeded_columns(pool, n) and picks[n] != prefix[:n]
        assert {k: v for k, v in req.items() if k != "feature_filter"} == {k: v for k, v in base.items() if k != "feature_filter"}
        assert req["event_import_id"] == hfb.EVENT_IMPORT_ID and req["kind"] == "ic_page"
    assert set(picks[5]) <= set(picks[50]) <= set(picks[500])

    ident = harness.post_ic_rows_identity()
    want = hashlib.sha256(json.dumps(harness.seeded_columns(pool, harness.ROW_AXIS_COLS),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()
    assert ident["columns_sha256"] == want == harness.post_ic_rows_identity("non_default")["columns_sha256"]
    assert ident["column_rule"] == harness.REQUEST_COLUMN_RULE and ident["n_cols"] == harness.ROW_AXIS_COLS

    for item in ("ic_report", "event_import_report", "ic_report_long"):
        shared = real_default(item)
        before = json.dumps(shared, sort_keys=True, ensure_ascii=False)
        small = hfb.small_request(item, shared, 20)
        assert small["feature_filter"]["include_features"] == prefix[:20]
        monkeypatch.setattr(hfb, "default_request", lambda it, cell=None, _r=shared: _r)
        harness._limited_request(item, None, 20)
        harness.relaxed_event_request(20)
        harness.relaxed_request(20)
        assert json.dumps(shared, sort_keys=True, ensure_ascii=False) == before, item
        assert hfb.small_request(item, shared, 20) == small, item
        monkeypatch.setattr(hfb, "default_request", real_default)

    for fn in (harness._run_event_import, harness.prepare_post_ic_rows, harness.post_ic_rows_identity,
               harness.event_axis_precheck, harness.relaxed_event_request):
        src = inspect.getsource(fn)
        assert "small_request(" not in src and ("_limited_request(" in src or "relaxed_event_request(" in src), fn.__name__


# ── SPEC v5.58 (x)(y)（code review r69 處置）：量測工具 ────────────────────────────────────────────────────────

#: smoke_v557 之事件數軸三點（runs/icperf/task02/smoke_v557/precheck_events_v557.json）：第 5 段輸出與 mann_whitney_table 呼叫數
V558_SURVIVORS = {176: 35, 457: 0, 737: 51}
V558_MW_CALLS = {176: 741, 457: 1, 737: 925}


def _v558_run(run_id: str, axis: str, scales: Sequence[int], facts: Any, entries: Any) -> Dict[str, Any]:
    """合成之 (run_id, axis) 實跑（記錄形狀同 run_one 寫出者；actual_scale＝規模）：`facts(s)`＝路徑事實、`entries(s)`＝
    {入口: (calls, seconds, max_cols)}。"""
    points, records = [], {}
    for s in scales:
        ents = {eid: {"calls": c, "raised": 0, "seconds": sec, "max_rows": 0, "max_cols": mc, "keyed": False,
                      "long_intervals": [], "max_call_seconds": 0.1} for eid, (c, sec, mc) in entries(s).items()}
        records[s] = [{"path_run_id": f"{run_id}.{axis}{s}", "run_id": run_id, "wall_seconds": 1.0,
                       "peak_footprint_bytes": 9000 + s, "progress_times": [], "_record_path": f"{run_id}-{axis}-{s}.json",
                       "facts": facts(s), "entries": ents, "actual_scale": s}]
        points.append({"scale": s, "unit": axis, "runs": 1, "seconds": 2.0, "peak_rss_bytes": 10 ** 8 + s})
    cmd = ["venv/bin/python", "scripts/icperf_scale_harness.py", "run", run_id, "--axis", axis]
    return {"probe": {"cmd": cmd, "data": [], "config": []}, "receipt_path": f"{run_id}-{axis}.json",
            "receipt": {"points": points, "projection": {"scale": max(scales)}}, "records": records}


def _v558_case(harness: Any) -> Tuple[Dict[str, Any], Dict[Tuple[str, str], Any]]:
    """合成：清冊兩個 event_import 入口（mann_whitney_table＝倖存數相依；m.x:merge＝只隨事件數變）、event_import cols／events
    兩軸（events 軸三點之第 5 段倖存數與 mann_whitney 呼叫數＝smoke_v557 實值）、固定倖存集合之直接呼叫格三點。"""
    mw = harness.MW_ENTRY
    base = {"stage": "event", "ic_page": True, "ic_first": False, "loop": "none", "measure": True,
            "no_measure_reason": None, "evidence": "m/x.py:1", "branch_cell": "event_import"}
    inv = {"entries": [
        {**base, "id": mw, "input_axes": ["cols"], "coverage_path_id": "c-mw",
         "unit_axis": {"axes": ["stage_cols", "survivors", "events"],
                       "function": "calls(survivors)*stage_cols*n_events*log(n_events)"},
         "scale_vector": ["stage_cols", "survivors", "events"]},
        {**base, "id": "m.x:merge", "input_axes": ["cols"], "coverage_path_id": "c-merge",
         "unit_axis": {"axes": ["stage_cols", "events"], "function": "stage_cols*n_events"},
         "scale_vector": ["stage_cols", "events"]}]}
    ev = (176, 457, 737)

    def receipt(s: int) -> Dict[str, Any]:
        return {"negative_control_status": "unavailable:insufficient_blocks" if V558_SURVIVORS[s] == 0 else "computed"}

    def ev_facts(s: int) -> Dict[str, Any]:
        return {"input_cols": 500, "rows": 2000, "events": s, "survivors": V558_SURVIVORS[s], "requested_columns": None,
                "binary_receipt": receipt(s), "post_stage5_claim": harness.post_stage5_claim(V558_SURVIVORS[s], receipt(s))}

    runs = {
        ("event_import", "cols"): _v558_run(
            "event_import", "cols", (500, 1000, 2000),
            lambda s: {"input_cols": s, "rows": 2000, "events": 203, "survivors": 0, "requested_columns": None,
                       "binary_receipt": None, "post_stage5_claim": harness.post_stage5_claim(0, None)},
            lambda s: {mw: (1, 1e-4 * s, s - 1), "m.x:merge": (1, 2e-4 * s, s - 1)}),
        ("event_import", "events"): _v558_run(
            "event_import", "events", ev, ev_facts,
            lambda s: {mw: (V558_MW_CALLS[s], 2e-3 * V558_MW_CALLS[s], 499), "m.x:merge": (1, 1e-3 * s, 499)}),
        (harness.MW_FIXED_CELL, "events"): _v558_run(
            harness.MW_FIXED_CELL, "events", ev,
            lambda s: {"input_cols": 51, "rows": s // 6, "events": s, "survivors": 51, "cell_input_cols": 51,
                       harness.COLUMN_SET_KEY: "sha-fixed", "fixed_survivors_ref_scale": 737, "requested_columns": None},
            lambda s: {mw: (harness.MW_FIXED_CALLS, 1e-5 * s * harness.MW_FIXED_CALLS, 51)}),
    }
    return inv, runs


def test_task02_v558_mann_whitney_survivors_axis(fb: Any, harness: Any, scale_probe: Any) -> None:
    """SPEC v5.58 (x)：①定稿清冊：event_import 需量測入口中倖存數相依者（unit_axis 含 survivors）恰為二元三入口——
    `mann_whitney_table`（呼叫數隨第 5 段倖存數變，本版改含）、`_run_binary_permutation_and_negative_control`（呼叫數固定、
    inclusive 成本隨倖存數變，本版改含）、`block_permutation_table`（原即含）；其餘 event_import 入口（第 5 段前）不含；排程含
    固定倖存集合之直接呼叫格且在 event_import events 軸之後、涵蓋另列 isolation；②組裝：mann_whitney 之 events 軸只記不擬合
    （row_fit＝None、row_fit_excluded 逐點記事件數、倖存數 35／0／51 與呼叫數 741／1／925），只隨事件數變之入口照常擬合；
    events 軸各點 scale_vector 含 survivors；中點（倖存 0、負對照未實算）post_stage5_claim.allowed＝False；isolation 三點同欄
    集合、同呼叫數、seconds_per_call、對事件數擬合；③反例：缺隔離實跑（require_isolation）⇒ 點名；各點欄集合不同 ⇒ 拒收；
    倖存數相依入口以 events 為主軸 ⇒ 拒收。mutation：events_fit_exclusion 恆回 None ⇒ row_fit 非 None（紅）；清冊
    mann_whitney 移除 survivors ⇒ ①紅；schedule_runs 不排 ISOLATION_RUNS ⇒ 排程斷言紅；_isolation_section 不驗欄集合 ⇒ 不拋（紅）。"""
    inv_real = _v555_inventory()
    assert fb.inventory_problems(inv_real) == []
    ev_entries = {e["id"]: e for e in inv_real["entries"] if e["measure"] and e["branch_cell"] == "event_import"}
    dep = {eid for eid, e in ev_entries.items() if harness.survivor_dependent(e)}
    assert dep == set(harness.EVENT_BINARY_ENTRIES), sorted(dep)
    assert all("survivors" in ev_entries[eid]["scale_vector"] for eid in dep)
    sched = harness.schedule_runs(inv_real)
    iso = (harness.MW_FIXED_CELL, "events")
    assert iso in sched and sched.index(("event_import", "events")) < sched.index(iso)
    assert iso not in harness.schedule_runs(inv_real, second_axes=False)
    cov = harness.schedule_coverage(inv_real, sched)
    assert cov["uncovered"] == [] and cov["isolation"] == {
        f"{iso[0]}:{iso[1]}": {"entry": harness.MW_ENTRY, "scheduled": True}}
    assert harness.schedule_coverage(inv_real, [x for x in sched if x != iso])["isolation"][
        f"{iso[0]}:{iso[1]}"]["scheduled"] is False

    inv, runs = _v558_case(harness)
    kw = {"head": "0" * 40, "scale_probe": scale_probe, "budget_seconds": BUDGET2_UPPER_SECONDS,
          "sample_interval_seconds": 0.2, "chunk_cap": {"bytes": 1, "basis": "x"}, "require_rows": True,
          "require_isolation": True}
    got = harness.assemble_scale_receipt(inv, runs, **kw)
    m = got["entries"][harness.MW_ENTRY]
    assert m["axis"] == "cols" and m["row_axis"] == "events" and m["row_fit"] is None
    ex = m["row_fit_excluded"]
    assert ex["axis"] == "events" and "v5.58 (x)" in ex["basis"]
    assert [(p["events"], p["survivors"], p["calls"]) for p in ex["points"]] == \
        [(176, 35, 741), (457, 0, 1), (737, 51, 925)]
    assert [p["scale_vector"]["survivors"] for p in m["row_points"]] == [35, 0, 51]
    assert [p["post_stage5_claim"]["allowed"] for p in m["row_points"]] == [True, False, True]
    mid = m["row_points"][1]["post_stage5_claim"]
    assert len(mid["reasons"]) == 2 and mid["negative_control_status"] == "unavailable:insufficient_blocks"
    assert _entry_schema_problems(m, inv["entries"][0]) == []
    merge = got["entries"]["m.x:merge"]
    assert merge["row_fit_excluded"] is None and merge["row_fit"]["axis"] == "events"
    iso_m = m["isolation"]
    assert iso_m["run"] == f"{iso[0]}:{iso[1]}" and iso_m["calls_per_point"] == harness.MW_FIXED_CALLS
    assert [p["events"] for p in iso_m["points"]] == [176, 457, 737]
    assert iso_m["fixed_columns"] == {"n": 51, harness.COLUMN_SET_KEY: "sha-fixed", "ref_scale": 737}
    assert all(p["seconds_per_call"] == p["seconds"] / harness.MW_FIXED_CALLS for p in iso_m["points"])
    again = scale_probe.fit([{"scale": p["events"], "unit": "events", "seconds": p["seconds"],
                              "peak_rss_bytes": p["peak_rss_bytes"]} for p in iso_m["points"]], 737.0)
    assert (iso_m["fit"]["exponent"], iso_m["fit"]["r2"]) == (again["fit"]["exponent"], again["fit"]["r2"])
    assert got["entries"]["m.x:merge"].get("isolation") is None

    with pytest.raises(harness.AssemblyError) as exc:  # 缺隔離實跑 ⇒ 點名
        harness.assemble_scale_receipt(inv, {k: v for k, v in runs.items() if k != iso}, **kw)
    assert any(harness.MW_ENTRY in p and "隔離" in p for p in exc.value.problems)
    bad = copy.deepcopy(runs)
    bad[iso]["records"][457][0]["facts"][harness.COLUMN_SET_KEY] = "sha-other"
    with pytest.raises(harness.AssemblyError) as exc:  # 各點固定倖存集合不同 ⇒ 拒收
        harness.assemble_scale_receipt(inv, bad, **kw)
    assert any("固定倖存集合" in p for p in exc.value.problems)
    prim = copy.deepcopy(inv)
    prim["entries"][0]["input_axes"] = []
    with pytest.raises(harness.AssemblyError) as exc:  # 倖存數相依入口以 events 為主軸 ⇒ 拒收
        harness.assemble_scale_receipt(prim, runs, **kw)
    assert any("主軸為 events" in p for p in exc.value.problems)


def test_task02_v558_event_stage5_facts_and_fixed_cell(harness: Any, tmp_path: Path, monkeypatch: Any) -> None:
    """SPEC v5.58 (x)：①`post_stage5_claim`：倖存 > 0 且負對照實算 ⇒ allowed；倖存 0 或負對照未實算 ⇒ 不成立並逐條記理由；
    倖存缺 ⇒ 不成立；②`binary_capture_hook` 依產品簽名取置換前門檻通過欄、置換後倖存者與收據，`binary_receipt_facts` 記 n_perm、
    區塊數、負對照狀態；③`_run_event_import`（服務以替身）各軸記 survivors＝第 5 段倖存數、final_survivors＝原 `_ic_facts` 之
    倖存數、binary_receipt、post_stage5_claim；④event_import events 軸之存檔（`_event_mw_begin`／重綁 wrapper 之首次呼叫／
    `_event_mw_finish`）與直接呼叫格 `_cell_mw_fixed`：固定倖存集合＝參考點之倖存欄、每點重綁入口恰 MW_FIXED_CALLS 次、
    各點欄集合身分相同、actual_scale＝存檔驗得之事件數；反例：未給 --ref-scale、參考點倖存為空、缺固定欄、存檔身分不符、
    首次呼叫未存（status failed）⇒ HarnessError。mutation：claim 不看負對照 ⇒ ①中點 allowed（紅）；survivors 改回原 `_ic_facts`
    之值 ⇒ ③紅；cell 改用本點倖存欄 ⇒ 欄集合身分不同（紅）；呼叫次數改 1 ⇒ 計數斷言紅。"""
    import contextlib
    import importlib

    import api.routes.ic_analysis as ria
    import api.services.case_import_service as cis

    ok = harness.post_stage5_claim(35, {"negative_control_status": "computed"})
    assert ok == {"allowed": True, "reasons": [], "stage5_output": 35, "negative_control_status": "computed"}
    mid = harness.post_stage5_claim(0, {"negative_control_status": "unavailable:insufficient_blocks"})
    assert mid["allowed"] is False and len(mid["reasons"]) == 2
    assert harness.post_stage5_claim(7, {"negative_control_status": "skipped:no_survivors"})["allowed"] is False
    assert harness.post_stage5_claim(3, None)["allowed"] is True  # 非二元模式：只看第 5 段倖存
    assert harness.post_stage5_claim(None, None)["allowed"] is False

    store: Dict[str, Any] = {}
    hook = harness.binary_capture_hook(store)
    nc = {"n_observed": 2, "n_consumable": 1, "n_effective": 50, "degraded_by_budget": False}
    hook((object(), ["a", "b"], {}, None, None), {"alpha_effective": 1.0, "fdr_method": "fdr_bh"},
         (["a"], {"n_perm": 571, "n_blocks": 31, "block_len": 13, "negative_control": nc}))
    assert store["threshold_passed"] == ["a", "b"] and store["survivors"] == ["a"]
    assert harness.binary_receipt_facts(store) == {
        "threshold_passed": 2, "survivors_after_permutation": 1, "n_perm": 571, "n_blocks": 31, "block_len": 13,
        "negative_control_status": "computed", "negative_control_n_effective": 50,
        "negative_control_degraded_by_budget": False}
    assert harness.binary_receipt_facts(None) is None

    # ③ _run_event_import 之第 5 段事實（服務替身；同 test_task02_v557_event_axis_relaxed_thresholds）
    hfb, _pool = _v557_requests(harness, monkeypatch, tmp_path)

    class _Store:
        def __init__(self, storage_dir: Any = None) -> None:
            self.n = 0

        def import_records(self, records: Any, **kw: Any) -> Any:
            self.n = len(records)
            return type("R", (), {"import_id": "imp-1"})()

        def get_import(self, iid: str) -> Any:
            return type("D", (), {"records": [None] * self.n})()

    @contextlib.contextmanager
    def bars(ctx: Any, recs: Any) -> Any:
        yield {}

    monkeypatch.setattr(cis, "EventImportService", _Store)
    monkeypatch.setattr(cis, "_event_import_service", getattr(cis, "_event_import_service", None))
    monkeypatch.setattr(ria, "_resolve_event_batch", lambda req: {"batch": True})
    monkeypatch.setattr(hfb, "_ic_analyze_request", lambda r: r)
    monkeypatch.setattr(harness, "event_bars_context", bars)
    monkeypatch.setattr(harness, "_event_axis_records", lambda n: [{"event_id": f"e{i}"} for i in range(n)])
    monkeypatch.setattr(harness, "event_axis_facts", lambda: {})
    monkeypatch.setattr(harness, "_ic_facts", lambda report, analyzer, n, rows: {"survivors": 9})
    monkeypatch.setattr(harness, "_manifest_rows", lambda req: 2000)
    monkeypatch.setattr(harness, "_service_with_tasks", lambda request, path: object())
    out_s5: Dict[str, int] = {"n": 0}

    def analysis(svc: Any, req: Any, rec: Any, **kw: Any) -> Any:
        for e in harness.EVENT_BINARY_ENTRIES:
            rec.stat(e).calls += 1
        return "t", {"analyzer": None, "result": {"filter_log": {"stage5_thresholds": {
            "input_features": 499, "output_features": out_s5["n"], "alpha_effective": 1.0}}}}

    monkeypatch.setattr(harness, "_service_analysis", analysis)
    ctx = _v555_ctx(harness, "event_import", "events", 6, tmp_path)
    ctx.binary_capture = {"threshold_passed": ["a", "b"], "survivors": [],
                          "receipt": {"n_perm": 571, "n_blocks": 7, "block_len": 13,
                                      "negative_control": {"status": "unavailable:insufficient_blocks", "n_blocks": 7}}}
    got = harness._run_event_import(ctx)
    assert (got["survivors"], got["final_survivors"], got["stage5_output"]) == (0, 9, 0)
    assert got["binary_receipt"]["negative_control_status"] == "unavailable:insufficient_blocks"
    assert got["binary_receipt"]["threshold_passed"] == 2 and got["post_stage5_claim"]["allowed"] is False
    out_s5["n"] = 7
    got = harness._run_event_import(_v555_ctx(harness, "event_import", "cols", 40, tmp_path))
    assert (got["survivors"], got["final_survivors"], got["binary_receipt"]) == (7, 9, None)
    assert got["post_stage5_claim"]["allowed"] is True and got["threshold_branch"] == "default"

    # ④ 存檔與直接呼叫格（真實 mann_whitney_table；身分以替身）
    ident = {"v": "1"}
    monkeypatch.setattr(harness, "event_mw_identity", lambda n: {"kind": "event_mw_capture", "events_requested": int(n),
                                                                 **ident})
    bd = importlib.import_module("momentum.Analysis.binary_discrimination")
    mw_func = harness.resolve_target(harness.MW_ENTRY).func
    cols = [f"c{i}" for i in range(10)]

    def frame(n: int) -> Tuple[pd.DataFrame, np.ndarray]:
        rng = np.random.default_rng(n)
        rows = n // 4
        return pd.DataFrame(rng.normal(size=(rows, len(cols))), columns=cols), (np.arange(rows) % 2).astype("int64")

    def write_point(n: int, survivors: List[str], call_mw: bool = True) -> None:
        c = _v555_ctx(harness, "event_import", "events", n, tmp_path)
        state = harness._event_mw_begin(c, f"pr{n}")
        assert harness.read_identity(harness.event_mw_dir(tmp_path, n) / harness.SUBSET_IDENTITY_FILE)["status"] == "building"
        c.rec.captures = {harness.MW_ENTRY: state["writer"]}
        c.binary_capture = {}
        h = harness.binary_capture_hook(c.binary_capture)
        binding = harness.rebind_all({harness.MW_ENTRY: mw_func}, c.rec)
        try:
            x, y = frame(n)
            if call_mw:
                bd.mann_whitney_table(x, y, min_class_n=3)
                bd.mann_whitney_table(x.iloc[:, :2], y, min_class_n=1)  # 非首次呼叫：不存
        finally:
            binding.restore()
        h((object(), list(survivors) + ["c9"], {}, None, None), {"alpha_effective": 1.0, "fdr_method": "fdr_bh"},
          (list(survivors), {"n_perm": 200, "n_blocks": 12, "block_len": 3, "negative_control": nc}))
        harness._event_mw_finish(state, c, {"events": n})

    fixed = ["c1", "c4", "c7"]
    write_point(176, ["c1"])
    write_point(457, [])
    write_point(737, fixed)
    write_point(900, [])
    write_point(950, ["c1", "zz"])
    write_point(990, fixed, call_mw=False)
    assert harness.read_identity(harness.event_mw_dir(tmp_path, 990) / harness.SUBSET_IDENTITY_FILE)["status"] == "failed"
    saved = harness.load_event_mw(tmp_path, 457)
    assert list(saved["mw"]["args"][0].columns) == cols and saved["mw"]["kwargs"] == {"min_class_n": 3}
    assert saved["events"] == 457 and saved["stage5"]["survivors"] == []

    def cell(n: int, ref: Optional[int]) -> Tuple[Dict[str, Any], Any]:
        c = _v555_ctx(harness, harness.MW_FIXED_CELL, "events", n, tmp_path)
        c.ref_scale = ref
        binding = harness.rebind_all({harness.MW_ENTRY: mw_func}, c.rec)
        try:
            return harness._cell_mw_fixed(c), c
        finally:
            binding.restore()

    shas = set()
    for n in (176, 457, 737):
        facts, c = cell(n, 737)
        assert c.rec.stat(harness.MW_ENTRY).calls == harness.MW_FIXED_CALLS
        assert c.rec.stat(harness.MW_ENTRY).max_cols == len(fixed)
        assert (facts["survivors"], facts["cell_input_cols"], facts["events"]) == (3, 3, n)
        assert c.actual_scale == n == facts["actual_scale"] and facts["fixed_survivors_ref_scale"] == 737
        assert facts["selection_rows"] == n // 4 and facts["min_class_n"] == 3
        shas.add(facts[harness.COLUMN_SET_KEY])
    assert len(shas) == 1 and shas == {harness._columns_sha(fixed)}
    with pytest.raises(harness.HarnessError, match="--ref-scale"):
        cell(176, None)
    with pytest.raises(harness.HarnessError, match="倖存欄為空"):
        cell(176, 900)
    with pytest.raises(harness.HarnessError, match="缺固定倖存欄"):
        cell(176, 950)
    with pytest.raises(harness.HarnessError, match="身分"):
        cell(990, 737)
    ident["v"] = "2"
    with pytest.raises(harness.HarnessError, match="身分"):
        cell(176, 737)


def test_task02_v558_optimized_core_flags_false(fb: Any, harness: Any) -> None:
    """SPEC v5.58 (y)：清冊 `_transform_single_optimized_df_core`（IC 頁／IC-first 不可達，measure=false）之 ic_page／ic_first＝
    false（與 measure=false、§N 不可達理由一致）；post_ic_transform 段之入口 ic_page⇔measure（可達者皆量）；旗標之下游消費者
    只有 schema（`INVENTORY_KEYS` 存在、boundary_14 型別為 bool）——排程、涵蓋、歸屬不讀旗標（翻轉旗標不改其結果），且量測工具
    與凍結腳本之源碼無以旗標取值之寫法。mutation：清冊旗標改回 true ⇒ 首斷言紅；post_ic 某可達入口標 ic_page=false ⇒ 等價斷言紅；
    harness 新增以 ic_page 過濾之寫法 ⇒ 源碼斷言紅。"""
    inv = _v555_inventory()
    e = next(x for x in inv["entries"] if x["id"] == V557_OPT_CORE)
    assert (e["ic_page"], e["ic_first"], e["measure"], e["branch_cell"]) == (False, False, False, None)
    assert fb.inventory_problems(inv) == []
    post = [x for x in inv["entries"] if x["stage"] == "post_ic_transform"]
    assert {x["id"] for x in post if x["ic_page"]} == {x["id"] for x in post if x["measure"]}
    flipped = copy.deepcopy(inv)
    fe = next(x for x in flipped["entries"] if x["id"] == V557_OPT_CORE)
    fe["ic_page"] = fe["ic_first"] = True
    assert harness.schedule_runs(flipped) == harness.schedule_runs(inv)
    assert harness.schedule_coverage(flipped, harness.schedule_runs(flipped)) == \
        harness.schedule_coverage(inv, harness.schedule_runs(inv))
    assert harness.coverage_plan(flipped) == harness.coverage_plan(inv)
    flag_read = re.compile(r"""\[\s*["']ic_(page|first)["']\s*\]|\.get\(\s*["']ic_(page|first)["']""")
    for rel in ("scripts/icperf_scale_harness.py", "scripts/icperf_freeze_baseline.py", "scripts/scale_probe.py"):
        hit = flag_read.search((REPO / rel).read_text(encoding="utf-8"))
        assert hit is None, (rel, hit.group(0) if hit else None)

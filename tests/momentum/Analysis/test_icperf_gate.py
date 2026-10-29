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
#: SPEC v5.26：第 (6)(7) 項之請求待 Task 0.3 定 L 格與匯入批（未定前 default_request／freeze 須 FreezeError）
PENDING_ITEMS = ("ic_report_long", "deep_analysis_long", "event_import_report")
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
#: SPEC Task 0.2／5.4 共用 schema：scale_vector 之軸（各入口取其所用者）
SCALE_VECTOR_KEYS = {"rows", "input_cols", "stage_cols", "survivors", "survivor_pairs"}
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
        request = fb.small_request(item, golden["items"][item]["request"], ORACLE_FEATURES)
        iso = work / item / "iso"
        before = _oracle_walk(_oracle_roots(work / item / "cwd", iso))
        record = fb.freeze_item(item, request=request, repo_root=REPO, work_root=work)
        after = _oracle_walk(_oracle_roots(work / item / "cwd", iso))
        written = {k for k, v in after.items() if before.get(k) != v}
        with open(work / item / "response.pkl", "rb") as fh:
            raw = pickle.load(fh)
        out[item] = {"record": record, "raw": raw, "written": written, "fields": _oracle_response_fields(item, raw),
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


def test_item_sets_match_spec_and_pending_fail_closed(fb: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC v5.26 §G：凍結腳本之項集合＝(1)–(7) 九鍵（測試自持）；第 (6)(7) 項於 Task 0.3 定 L 格與匯入批前，
    `default_request` 須 FreezeError，`freeze` 須於啟動任何執行前即拒（替身 `freeze_item` 被呼叫即 FAIL）；第 (3) 項請求之
    深度分析模組全開（含預設關閉者）。"""
    assert tuple(fb.G_ITEMS) == G_ITEMS and tuple(fb.OUTPUT_ITEMS) == OUTPUT_ITEMS
    assert tuple(fb.PENDING_ITEMS) == PENDING_ITEMS
    for item in PENDING_ITEMS:
        with pytest.raises(fb.FreezeError):
            fb.default_request(item)

    def must_not_run(*a: Any, **k: Any) -> None:
        pytest.fail("請求未定時 freeze 不得啟動任何執行")

    monkeypatch.setattr(fb, "freeze_item", must_not_run)
    with pytest.raises(fb.FreezeError):
        fb.freeze(tmp_path / "g.json.gz", work_root=tmp_path / "w")
    assert not (tmp_path / "g.json.gz").exists()
    from api.models.ic_models import DeepAnalysisModules

    modules = fb.default_request("deep_analysis", CELL)["deep"]["modules"]
    assert set(modules) == set(DeepAnalysisModules.model_fields) and all(v is True for v in modules.values()), modules


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
    out = fb.volatile_probe(golden_path=path, work_root=tmp_path / "w")
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
        assert e["input_axes"] and set(e["input_axes"]) <= INPUT_AXES, f"{eid}：輸入軸非法"
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
    """scale_probe 收據之 identity.match 逐欄等於該入口宣告之量測命令（r11 CODEX-R11-P1-03）：命令須含入口 id；
    entrypoint／target_argv 照 scale_probe 之取法、data 照現行檔重算（雜湊有快取）、code／config 取量測時提交
    `head` 之 blob、hardware 等於本機。錯入口、錯 argv、錯資料、改過之量測碼所產之收據即紅。"""
    rid = _load("icperf_gate_receipt_identity", REPO / "scripts" / "run_receipt_identity.py")
    cmd = [str(a) for a in probe["cmd"]]
    assert eid in cmd, f"{eid}：量測命令未指名本入口：{cmd}"
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
    for k in ("seconds", "peak_rss_bytes"):
        assert point[k] == hits[0][k], f"{eid}：{k} {point[k]} != scale_probe 實測 {hits[0][k]}"


def test_boundary_16_three_points_per_entry() -> None:
    """每一入口 points 長度 3（boundary_19 之兩點例外除外）；逐點秒數與峰值 RSS；x 軸同記輸入欄數與實際進段欄數；
    每一點引用實存之 scale_probe 收據且秒數與峰值 RSS 逐欄等於其實測值（列長點同），且該收據之身分逐欄等於入口宣告之
    量測命令（`probe`／列長點 `row_probe`：cmd、data、config；code 取收據頂層 `head` 提交）。"""
    inv = _inventory_entries()
    receipt = _single(SCALE_BEFORE_PATTERN)
    head = str(receipt.get("head") or "")
    assert re.fullmatch(r"[0-9a-f]{40}", head), f"量測收據須記量測時之提交 head：{head!r}"
    for eid, m in receipt["entries"].items():
        pts = m["points"]
        if not m.get("two_point_exception"):
            assert len(pts) == 3, f"{eid}：須 3 點，實得 {len(pts)}"
        for p in pts:
            assert isinstance(p["seconds"], (int, float)) and p["seconds"] >= 0, eid
            assert isinstance(p["peak_rss_bytes"], int) and p["peak_rss_bytes"] > 0, eid
            assert isinstance(p["input_cols"], int) and isinstance(p["stage_cols"], int), eid
            assert 0 <= p["stage_cols"] <= p["input_cols"], f"{eid}：實際進段欄數不得多於輸入欄數"
            _assert_point_bound(eid, p, p["input_cols"], "cols", m["probe"], head)
        assert len({p["input_cols"] for p in pts}) == len(pts), f"{eid}：規模點重複"
        if eid in inv and "rows" in inv[eid]["input_axes"]:
            rows = m["row_points"]
            assert len(rows) == 3 and len({r["rows"] for r in rows}) == 3, f"{eid}：列數成長元件須三種列長"
            for r in rows:
                _assert_point_bound(eid, r, r["rows"], "rows", m["row_probe"], head)
    # SPEC v5.19–v5.21 Task 0.2：點數規則（3 點；唯一例外＝帶 two_point_exception 者恰 2 點且不含 2,000 欄點）、
    # coverage_path_id／unit_axis 與清冊一致、每點帶完整 scale_vector 與峰值 Physical footprint
    # 重用上段區域名（pts＝該入口之量測記錄、p＝清冊入口），不另綁新名：既有斷言之名序不變（TESTREG V19 normalize ②）
    for eid, pts in receipt["entries"].items():
        p = inv.get(eid)
        assert not _entry_schema_problems(pts, p), f"{eid}：量測收據 schema 不合：{_entry_schema_problems(pts, p)}"


def _entry_schema_problems(m: Mapping[str, Any], inv_entry: Optional[Mapping[str, Any]]) -> List[str]:
    """量測收據單一入口之 schema 問題清單（空＝成立；SPEC Task 0.2「驗證」與「路徑清冊」）：點數規則（3 點；唯一例外＝帶
    two_point_exception 者恰 500／1000 兩點、不含 2,000 欄點）、coverage_path_id 與 unit_axis 與清冊一致、每點（含列長點）之
    scale_vector 鍵集＝清冊 scale_vector 且值為非負整數並與點之同名欄相等、每點帶峰值 Physical footprint。拒收缺軸、單位
    歧義或 id 與清冊不一致之收據。以問題清單回報（呼叫端單一斷言；不另綁斷言區域名，TESTREG V19 名序不變）。"""
    out: List[str] = []
    cols = sorted(p["input_cols"] for p in m["points"])
    want = [500, 1000] if m.get("two_point_exception") else [500, 1000, 2000]
    if cols != want:
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
    ②須有 lower_bound_seconds_per_unit 或碼層下限分析；各點同引一份 scale_probe 收據者，fit 與 extrapolation_unreliable
    等於該收據。"""
    for eid, m in _scale_entries().items():
        fit = m["fit"]
        assert isinstance(fit["exponent"], (int, float)) and isinstance(fit["r2"], (int, float)), eid
        assert isinstance(m["extrapolation_unreliable"], bool), eid
        sources = {str(p.get("scale_probe_receipt") or "") for p in m["points"]}
        if len(sources) == 1:
            rec = _scale_probe_receipt(next(iter(sources)))
            assert fit["exponent"] == rec["fit"]["exponent"] and fit["r2"] == rec["fit"]["r2"], f"{eid}：fit != 收據"
            assert m["extrapolation_unreliable"] == rec["extrapolation_unreliable"], f"{eid}：可靠性旗標 != 收據"
        crit = m["criteria"]
        assert set(crit) == {"1", "2", "3", "4", "5"}, f"{eid}：判準鍵 {sorted(crit)}"
        for k, c in crit.items():
            assert isinstance(c["result"], bool) and str(c["basis"]).strip(), f"{eid}：判準{k} 欄位缺"
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
        assert cols <= SCALE_POINTS, f"{eid}：規模點 {sorted(cols)} 超出 500／1000／2000"
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
    """500／1000 兩點推估 2000 欄逾 10 分鐘之元件 ⇒ 須帶 two_point_exception、收據不得含其 2000 欄點、附碼層複雜度分析
    （boundary_16 之唯一例外）；未逾者不得帶例外且須 500／1000／2000 三點。"""
    for eid, m in _scale_entries().items():
        exc = m.get("two_point_exception")
        cols = sorted(p["input_cols"] for p in m["points"])
        assert 500 in cols and 1000 in cols, f"{eid}：須含 500／1000 欄點"
        projected = _projected_2000_seconds(m["points"])
        if projected > TWO_POINT_SECONDS:
            assert exc, f"{eid}：2000 欄推估 {projected:.0f} 秒逾 10 分鐘，須帶 two_point_exception"
            assert cols == [500, 1000], f"{eid}：兩點例外之收據不得含 2000 欄點（實得 {cols}）"
            assert exc["projected_2000_seconds"] > TWO_POINT_SECONDS, f"{eid}：例外之推估值須逾 10 分鐘"
            assert str(m.get("complexity_analysis") or "").strip(), f"{eid}：兩點例外須附碼層複雜度分析"
        else:
            assert not exc, f"{eid}：2000 欄推估 {projected:.0f} 秒未逾 10 分鐘，不得帶 two_point_exception"
            assert cols == [500, 1000, 2000], f"{eid}：未逾 10 分鐘者須三點（實得 {cols}）"


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
    命令未指名本入口、錯 entrypoint、錯 argv、量測碼與 head 不同 ⇒ boundary_16 紅。身分以 run_receipt_identity 對
    repo 內已提交之 scripts/scale_probe.py 產生（不跑量測）。"""
    module = sys.modules[__name__]
    rid = _load("icperf_gate_receipt_identity", REPO / "scripts" / "run_receipt_identity.py")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    eid = "m.a:f"
    probe = {"cmd": ["venv/bin/python", "scripts/scale_probe.py", "--entry", eid], "data": [], "config": []}
    match = rid.compute_match("scripts/scale_probe.py", probe["cmd"], [], [], [])
    match["code_sha256"] = _sha_at_commit(head, ["scripts/scale_probe.py"])
    match["config_sha256"] = _sha_at_commit(head, [])

    def run(entry_probe: Mapping[str, Any], receipt_match: Mapping[str, Any], mutate: Any = None) -> None:
        pts = [{"input_cols": n, "stage_cols": n, "seconds": 1.0 * n, "peak_rss_bytes": 1000 + n,
                "peak_footprint_bytes": 2000 + n, "scale_vector": {"input_cols": n, "stage_cols": n},
                "scale_probe_receipt": "r.json"} for n in (500, 1000, 2000)]
        probe_rec = {"identity": {"match": dict(receipt_match), "meta": {"producer": "scripts/scale_probe.py"}},
                     "points": [{"scale": p["input_cols"], "unit": "cols", "seconds": p["seconds"],
                                 "peak_rss_bytes": p["peak_rss_bytes"]} for p in pts]}
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
        test_boundary_16_three_points_per_entry()

    run(probe, match)
    bad = [
        ({**probe, "cmd": ["venv/bin/python", "scripts/scale_probe.py", "--entry", "m.b:g"]}, match),  # 命令未指名本入口
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

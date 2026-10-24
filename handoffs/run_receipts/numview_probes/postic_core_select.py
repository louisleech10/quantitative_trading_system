"""NUMVIEW post-IC 單一 pandas 核心擇一（docs/NUMVIEW_SPEC.md Task 1.6，v40）。

使用者 2026-10-24「IC頁與IC-first都改pandas」與常設「小／大資料非線性，不得推測」：於兩個 pandas 計算核心
（`pandas_optimized`／`pandas_legacy`；`feature_preprocessor.py:3379-3380`）以實際規模實測擇一。輸入（不另生成特徵）：
(a) `A:BTCUSDT:1h` 凍結 run 之 raw 與其 IC-first 選欄、全窗列；(b) 全特徵 `C:BTCUSDT:1h` 凍結 run 之 raw，選欄以生產
IC-first 同程序重算。入口＝生產 `transform_selected`（`FFACT_USE_POLARS=0`、`FFACT_L65_OPTIMIZATION_PROFILE`＝optimized／
legacy）。單元＝核心 × {分塊：(a)、(b)；直接（`FFACT_L65_CHUNK_SIZE=0`）：(a)}，每單元子行程經卡死監看；同路徑兩核心輸出
逐位元互比；擇一規則見 SPEC Task 1.6。收據 `handoffs/run_receipts/<date>-numview-postic-core-select.json`，含
`criteria_sha256`。

程序（皆子行程、經卡死監看、串行）：①IC 重算：凍結 A、C 之 run 目錄複製至工作目錄，以生產 IC-first 之標籤與
`ICEngine.compute_ic_from_l7_raw` 重算選欄；A 之重算選欄須逐項等於其凍結選欄（程序與生產相符之自證，不符 ⇒ rc≠0）。
②六單元：讀選欄 raw（`load_columns_v2`，同 `feature_factory.py:2958-2965`）→ 前處理器同 IC-first 建構（`:2969-2978`，
不傳 `arm`）→ `transform_selected`；輸出依 dtype 分塊存工作目錄。③成對比對（同路徑同輸入兩核心）。④結構一致而輸出不等
時方算參考實作（Task 0.6 `numview_reference.post_ic_chain`）之遮罩與誤差（擇一規則③）。
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:  # 以腳本執行時 repo 根不在 sys.path（同 precision_chain.py:35）
    sys.path.insert(0, str(REPO))
PROBES_DIR = Path(__file__).resolve().parent
RECEIPTS_DIR = REPO / "handoffs" / "run_receipts"
FREEZE_RUNS = REPO / "data_cache" / "numview_freeze_runs"
FREEZE_SCRIPT = REPO / "scripts" / "numview_freeze_baseline.py"
DEFAULT_WORK_ROOT = REPO / "data_cache" / "numview_postic_core_runs"

#: 核心（`FFACT_L65_OPTIMIZATION_PROFILE` 值）→ 收據名（同 `_record_group` 之臂名）
CORES: Dict[str, str] = {"optimized": "pandas_optimized", "legacy": "pandas_legacy"}
#: 擇一規則②③之名稱次序（相等時取前者）
CORE_ORDER: Tuple[str, ...] = ("pandas_optimized", "pandas_legacy")
CELLS: Dict[str, str] = {"a": "A_BTCUSDT_1h", "b": "C_BTCUSDT_1h"}
#: 路徑 × 輸入（SPEC：分塊 (a)、(b)；直接 (a)）
PATHS: Tuple[Tuple[str, str], ...] = (("chunked", "a"), ("direct", "a"), ("chunked", "b"))
UNIT_IDS: Tuple[str, ...] = tuple(f"{core}__{path}__{inp}" for path, inp in PATHS for core in CORE_ORDER)
SELECTION_KIND = "ic_first_full_window"
_MODULES: Dict[str, Any] = {}


def _log(message: str) -> None:
    print(f"[postic-core] {datetime.now().strftime('%H:%M:%S')} {message}", flush=True)


def _load(name: str, path: Path) -> Any:
    if name not in _MODULES:
        if name in sys.modules:
            _MODULES[name] = sys.modules[name]
        else:
            spec = importlib.util.spec_from_file_location(name, path)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"無法載入 {path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            _MODULES[name] = module
    return _MODULES[name]


def _watchdog() -> Any:
    return _load("numview_watchdog", PROBES_DIR / "_watchdog.py")


def _estimate() -> Any:
    return _load("numview_estimate", PROBES_DIR / "estimate.py")


def _freeze() -> Any:
    return _load("numview_freeze_baseline_postic_core", FREEZE_SCRIPT)


def _criteria_path() -> Path:
    from tests.feature_engineering import numview_helpers as nh

    return nh.current_criteria_path()


def _criteria() -> Dict[str, Any]:
    return json.loads(_criteria_path().read_text(encoding="utf-8"))


def _cell(cell_id: str, criteria: Mapping[str, Any]) -> Dict[str, Any]:
    for c in criteria["cell_rules"]["cell_list"]["cells"]:
        if str(c["id"]) == cell_id:
            return {"id": str(c["id"]), "kind": str(c["kind"]), "symbol": str(c["symbol"]),
                    "timeframes": [str(t) for t in c["timeframes"]]}
    raise KeyError(cell_id)


def _peak_rss_bytes() -> int:
    import resource

    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ============================================================================================== 生產程序（子行程內）

def production_context(cell_id: str, criteria: Mapping[str, Any]) -> Dict[str, Any]:
    """格之生產物件：factory（`create_feature_factory`，同凍結生成）、已解析設定、輸出段、主週期 kline（`_layer0_data_ingestion`
    以輸出段起訖讀；標籤 `pct_change().shift(-1)` 只依 t 與 t+1 之 close，與生產自預熱起點讀者於公開窗逐值相同）。"""
    from momentum.factories import create_feature_factory

    est = _estimate()
    cell = _cell(cell_id, criteria)
    training = [str(t) for t in cell["timeframes"]]
    payload = est.cell_payload(cell, criteria, training)
    source = est.cell_source(cell, criteria)
    start, end = est.cell_window(cell, criteria)
    continuity = est.continuity_plan(cell, criteria, training)
    factory = create_feature_factory(cache_dir=str(source.parent), validate_continuity=continuity["validate_continuity"])
    config = factory._resolve_config(payload)
    symbol, tf = cell["symbol"], cell["timeframes"][0]
    kline = factory._layer0_data_ingestion(symbol, tf, config, start_date=start, end_date=end)
    return {"cell": cell, "factory": factory, "config": config, "symbol": symbol, "tf": tf, "start": start, "end": end,
            "kline": kline, "source": str(source)}


def production_label(ctx: Mapping[str, Any]) -> Any:
    """IC-first 預設標籤（`feature_factory.py:2909-2920`）：kline close 之 `pct_change().shift(-1)`，套公開窗遮罩。"""
    import pandas as pd

    factory, kline = ctx["factory"], ctx["kline"]
    index = factory._derive_row_index_for_artifact(kline)
    if index is None:
        raise RuntimeError(f"{ctx['cell']['id']}：取不到 kline 時間軸")
    mask = factory._utc_window_mask(index, ctx["start"], ctx["end"])
    close = pd.Series(kline["close"].to_numpy(dtype=float), index=index)
    return close.pct_change().shift(-1).rename("forward_return")[mask]


def recompute_selection(ctx: Mapping[str, Any], features_root: Path, config_hash: str,
                        criteria: Mapping[str, Any]) -> Dict[str, Any]:
    """生產 IC-first 之選欄（`feature_factory.py:2922-2953` 同一呼叫；IC 參數取判準 `cell_definitions.A.generation`，選窗＝
    標籤時間戳起訖）。`features_root` 須為複本。"""
    import pandas as pd

    from momentum.Analysis.ic_engine import ICEngine
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    generation = criteria["cell_definitions"]["A"]["generation"]
    label = production_label(ctx)
    label_index = pd.DatetimeIndex(label.index)
    window = {"start": str(label_index.min()) if len(label_index) else None,
              "end": str(label_index.max()) if len(label_index) else None}
    result = ICEngine(dict(generation["ic_engine_config"])).compute_ic_from_l7_raw(
        ctx["symbol"], ctx["tf"], config_hash, label, feature_reader=FeatureReader(str(features_root)),
        ic_threshold=generation["ic_threshold"], allow_partial_ic=False, method=None,
        label_horizon=str(generation["label_horizon"]), selection_window=window, split_id=SELECTION_KIND)
    selected = ctx["factory"]._extract_ic_selected_features(result)
    values = label.to_numpy(dtype=np.float64)
    return {"selected": selected, "label_rows": int(len(label)),
            "label_sha256": hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest(),
            "selection_window": window, "ic_params": {k: generation[k] for k in ("ic_engine_config", "ic_threshold",
                                                                                 "label_horizon")}}


def unit_env(core: str, path: str) -> Dict[str, str]:
    """單元之環境（其餘清除類鍵由 `_clean_env` 清除）：pandas 臂、核心選擇子；直接路徑停用分塊，分塊路徑用預設塊寬。"""
    env = {"FFACT_USE_POLARS": "0", "FFACT_L65_OPTIMIZATION_PROFILE": core}
    if path == "direct":
        env["FFACT_L65_CHUNK_SIZE"] = "0"
    return env


def frame_sha256(frame: Any) -> str:
    """DataFrame 身分：欄序、逐欄 dtype、時間軸、逐欄原生位元組。"""
    digest = hashlib.sha256()
    digest.update(json.dumps([[str(c), str(frame[c].dtype)] for c in frame.columns]).encode("utf-8"))
    digest.update(np.ascontiguousarray(np.asarray(frame.index.asi8, dtype=np.int64)).tobytes())
    for c in frame.columns:
        digest.update(np.ascontiguousarray(frame[c].to_numpy()).tobytes())
    return digest.hexdigest()


def post_ic_config_summary(config: Any) -> Dict[str, Any]:
    """收據用之 post-IC 設定（IC-first 傳 `config.preprocessing`；`transform_selected` 只用 rank／zscore／gaussian 之開關與窗）。"""
    pre = config.preprocessing
    dump = pre.model_dump() if hasattr(pre, "model_dump") else dict(pre)
    return {k: dump.get(k) for k in ("mode", "causal_preprocessing", "rank_transform", "adaptive_zscore", "gaussian_normalize")}


def transform_unit(ctx: Mapping[str, Any], features_root: Path, config_hash: str, selected: Sequence[str], core: str,
                   path: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """一單元之生產轉換（於本行程，環境經 `_clean_env` 套 `unit_env`）：回 (processed_groups, 紀錄)。紀錄含實際臂（群組表）、
    實際核心（spy 包 `_transform_single` 記每次呼叫之 `_can_use_optimized_dataframe_path()`）、呼叫次數、入口剔除之
    ratio-unsafe 欄數、輸入身分與 transform 牆鐘。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    calls: List[str] = []
    real = FeaturePreprocessor._transform_single

    def spy(this: Any, *args: Any, **kwargs: Any) -> Any:
        calls.append("optimized" if this._can_use_optimized_dataframe_path() else "legacy")
        return real(this, *args, **kwargs)

    factory, config = ctx["factory"], ctx["config"]
    with _freeze()._clean_env(unit_env(core, path)):
        started = time.perf_counter()
        raw = FeatureReader(str(features_root)).load_columns_v2(ctx["symbol"], ctx["tf"], config_hash, list(selected),
                                                                artifact_kind="raw", attach_row_index=True)
        load_seconds = time.perf_counter() - started
        groups = factory._frame_to_l7_groups(raw, "selected")
        factory._current_symbol, factory._current_timeframe = ctx["symbol"], ctx["tf"]
        factory._current_config_hash, factory._current_raw_data = config_hash, ctx["kline"]
        preprocessor = FeaturePreprocessor(factory._preprocessing_config_dict(config),
                                           context=factory._build_preprocessing_context(ctx["kline"], config))
        FeaturePreprocessor._transform_single = spy  # type: ignore[assignment]
        try:
            started = time.perf_counter()
            processed = preprocessor.transform_selected(list(selected), groups, config.preprocessing)
            transform_seconds = time.perf_counter() - started
        finally:
            FeaturePreprocessor._transform_single = real  # type: ignore[assignment]
    records, exec_groups = preprocessor.last_post_ic_execution()
    terminals: Dict[str, int] = {}
    for record in records.values():
        terminals[str(record.get("terminal"))] = terminals.get(str(record.get("terminal")), 0) + 1
    info = {"wall_seconds": transform_seconds, "load_seconds": load_seconds,
            "arm_recorded": sorted({str(g.get("arm")) for g in exec_groups.values()}),
            "core_observed": sorted(set(calls)), "chunk_calls": len(calls),
            "ratio_unsafe_dropped": int(terminals.get("ratio_unsafe_dropped", 0)), "terminals": terminals,
            "input_columns": int(raw.shape[1]), "input_rows": int(raw.shape[0]), "input_sha256": frame_sha256(raw),
            "post_ic_config": post_ic_config_summary(config)}
    return processed, info


# ============================================================================================== 輸出存取（依 dtype 分塊）

def save_frame(frame: Any, out_dir: Path) -> Dict[str, Any]:
    """欄序、逐欄 dtype、時間軸與依 dtype 分塊之原生值存 `out_dir`（成對比對讀回，不經任何轉型）。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    columns = [str(c) for c in frame.columns]
    dtypes = [str(frame[c].dtype) for c in frame.columns]
    blocks: Dict[str, List[str]] = {}
    for name, dtype in zip(columns, dtypes):
        blocks.setdefault(dtype, []).append(name)
    for dtype, names in blocks.items():
        np.save(out_dir / f"block_{dtype}.npy", frame.loc[:, names].to_numpy(dtype=np.dtype(dtype)))
    np.save(out_dir / "index.npy", np.asarray(frame.index.asi8, dtype=np.int64))
    meta = {"columns": columns, "dtypes": dtypes, "blocks": blocks, "shape": [int(frame.shape[0]), int(frame.shape[1])]}
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return {"shape": meta["shape"], "dtypes": {d: len(n) for d, n in sorted(blocks.items())}}


class SavedFrame:
    """`save_frame` 之讀回（逐欄原生 dtype 之 1 維陣列；分塊以 mmap 讀）。"""

    def __init__(self, out_dir: Path) -> None:
        self.meta = json.loads((Path(out_dir) / "meta.json").read_text(encoding="utf-8"))
        self.columns: List[str] = list(self.meta["columns"])
        self.dtypes: Dict[str, str] = dict(zip(self.meta["columns"], self.meta["dtypes"]))
        self.index = np.load(Path(out_dir) / "index.npy")
        self._blocks = {d: np.load(Path(out_dir) / f"block_{d}.npy", mmap_mode="r") for d in self.meta["blocks"]}
        self._where = {name: (d, j) for d, names in self.meta["blocks"].items() for j, name in enumerate(names)}

    def column(self, name: str) -> np.ndarray:
        dtype, j = self._where[name]
        return np.asarray(self._blocks[dtype][:, j])


def _bits_equal(x: np.ndarray, y: np.ndarray) -> bool:
    """同 dtype 之原生逐位元相等（NaN 遮罩相同、非 NaN 之位元相同；NaN 之 payload 不計）。"""
    if x.dtype != y.dtype or x.shape != y.shape:
        return False
    if np.issubdtype(x.dtype, np.floating):
        nx, ny = np.isnan(x), np.isnan(y)
        if not np.array_equal(nx, ny):
            return False
        view = {2: np.uint16, 4: np.uint32, 8: np.uint64}[x.dtype.itemsize]
        return bool(np.array_equal(x[~nx].view(view), y[~ny].view(view)))
    return bool(np.array_equal(x, y))


def compare_saved(x: SavedFrame, y: SavedFrame) -> Dict[str, Any]:
    """成對比對（SPEC Task 1.6）：結構（欄集合與順序、逐欄 dtype、時間軸）與逐欄值（原生逐位元；另以 float64 計 NaN 遮罩差、
    兩者皆有限而不等之格數、最大絕對差）。不等之欄逐欄列於 `diff_columns`（欄式），計數欄可由其重算。"""
    columns_equal = x.columns == y.columns
    index_equal = bool(np.array_equal(x.index, y.index))
    common = [c for c in x.columns if c in y.dtypes]
    rows: Dict[str, List[Any]] = {"column": [], "dtype_x": [], "dtype_y": [], "nan_mask_diff": [], "value_neq_cells": [],
                                  "max_abs": []}
    for name in common:
        a, b = x.column(name), y.column(name)
        if _bits_equal(a, b):
            continue
        a64, b64 = a.astype(np.float64), b.astype(np.float64)
        both = np.isfinite(a64) & np.isfinite(b64)
        diff = np.abs(np.where(both, a64 - b64, 0.0))
        rows["column"].append(name)
        rows["dtype_x"].append(x.dtypes[name])
        rows["dtype_y"].append(y.dtypes[name])
        rows["nan_mask_diff"].append(int((np.isnan(a64) != np.isnan(b64)).sum()))
        rows["value_neq_cells"].append(int((both & (a64 != b64)).sum()))
        rows["max_abs"].append(float(diff.max()) if diff.size else 0.0)
    dtype_mismatch = sum(1 for dx, dy in zip(rows["dtype_x"], rows["dtype_y"]) if dx != dy)
    structure_equal = columns_equal and index_equal and dtype_mismatch == 0
    return {"columns_equal": columns_equal, "index_equal": index_equal,
            "only_x": sorted(set(x.columns) - set(y.dtypes)), "only_y": sorted(set(y.columns) - set(x.dtypes)),
            "structure_equal": structure_equal, "dtype_mismatch_columns": dtype_mismatch,
            "columns_unequal_native": len(rows["column"]), "nan_mask_diff": int(sum(rows["nan_mask_diff"])),
            "value_neq_cells": int(sum(rows["value_neq_cells"])),
            "max_abs": float(max(rows["max_abs"])) if rows["max_abs"] else 0.0,
            "bitwise_equal": bool(structure_equal and not rows["column"]), "diff_columns": rows}


# ============================================================================================== 參考實作比對（規則③）

def reference_config(post_ic: Mapping[str, Any]) -> Dict[str, Any]:
    """`numview_reference.post_ic_chain` 之參數（rank → gaussian → zscore；IC-first 預設 gaussian 關）。gaussian 開 ⇒ 拋錯
    （參考實作之 gaussian 窗與生產 post-IC 之對應未定，fail-closed）。"""
    rank, zscore, gauss = (post_ic.get(k) or {} for k in ("rank_transform", "adaptive_zscore", "gaussian_normalize"))
    if gauss.get("enabled"):
        raise RuntimeError("post-IC gaussian 開啟：參考實作比對未支援（fail-closed）")
    return {"rank_window": int(rank["window"]) if rank.get("enabled") else None, "gaussian_window": None,
            "zscore_windows": [int(w) for w in zscore["windows"]] if zscore.get("enabled") else None}


def reference_stats(raw: Any, outputs: Mapping[str, SavedFrame], ref_cfg: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """各輸出（單元 id → 讀回）對參考實作：逐格 NaN 遮罩差、兩者皆有限之格數、該等格之最大絕對誤差（輸出欄＝輸入欄名）。"""
    from tests.feature_engineering import numview_reference as ref

    stats = {uid: {"nan_mask_diff": 0, "common_finite_cells": 0, "max_abs": 0.0, "columns": 0} for uid in outputs}
    for name in next(iter(outputs.values())).columns:
        expected = ref.post_ic_chain(raw[name].to_numpy(dtype=np.float64), **ref_cfg)
        for uid, saved in outputs.items():
            got = saved.column(name).astype(np.float64)
            both = np.isfinite(got) & np.isfinite(expected)
            s = stats[uid]
            s["columns"] += 1
            s["nan_mask_diff"] += int((np.isnan(got) != np.isnan(expected)).sum())
            s["common_finite_cells"] += int(both.sum())
            if both.any():
                s["max_abs"] = max(s["max_abs"], float(np.abs(got[both] - expected[both]).max()))
    return stats


# ============================================================================================== 擇一規則（純函式）

def _tiebreak(units: Mapping[str, Mapping[str, Any]]) -> str:
    """規則②之次序：(b) 牆鐘較小 → (b) 峰值 RSS 較小 → `pandas_optimized`。"""
    def key(core: str) -> Tuple[float, int, int]:
        u = units[f"{core}__chunked__b"]
        return float(u["wall_seconds"]), int(u["peak_rss_bytes"]), CORE_ORDER.index(core)

    return min(CORE_ORDER, key=key)


def select_core(units: Sequence[Mapping[str, Any]], pairs: Sequence[Mapping[str, Any]],
                reference: Optional[Mapping[str, Mapping[str, Any]]]) -> Dict[str, Any]:
    """SPEC Task 1.6 擇一規則（依序判定，恰回 `{"choice": 核心}` 或 `{"no_choice": {"rule", "reason"}}`）。"""
    by_id = {str(u["unit_id"]): u for u in units}
    bad = [uid for uid in UNIT_IDS if uid not in by_id or by_id[uid].get("status") != "complete"
           or list(by_id[uid].get("core_observed") or []) != [uid.split("__")[0].replace("pandas_", "")]]
    if bad or len(by_id) != len(UNIT_IDS):
        return {"no_choice": {"rule": "1", "reason": f"單元非 complete 或實際核心不符：{bad or sorted(by_id)}"}}
    by_pair = {(str(p["path"]), str(p["input"])): p for p in pairs}
    missing = [f"{path}/{inp}" for path, inp in PATHS if (path, inp) not in by_pair]
    if missing:
        return {"no_choice": {"rule": "1", "reason": f"成對比對不完整：{missing}"}}
    if all(by_pair[k]["bitwise_equal"] for k in by_pair):
        return {"choice": _tiebreak(by_id), "rule": "2"}
    broken = [f"{p}/{i}" for (p, i), row in by_pair.items() if not row["structure_equal"]]
    if broken:
        return {"no_choice": {"rule": "3_structure", "reason": f"兩核心輸出結構（dtype／欄集合／欄順序／時間軸）不一致：{broken}"}}
    if not reference:
        return {"no_choice": {"rule": "3_reference_missing", "reason": "輸出不等而無參考實作比對"}}
    scales = {"a": [f"__{p}__a" for p, i in PATHS if i == "a"], "b": ["__chunked__b"]}

    def unit_stats(core: str, scale: str) -> List[Mapping[str, Any]]:
        return [reference[f"{core}{suffix}"] for suffix in scales[scale]]

    mask_ok = {core: {s: all(int(r["nan_mask_diff"]) == 0 for r in unit_stats(core, s)) for s in scales} for core in CORE_ORDER}
    full = [core for core in CORE_ORDER if all(mask_ok[core].values())]
    if len(full) == 1:
        return {"choice": full[0], "rule": "3_nan_mask"}
    if not full:
        return {"no_choice": {"rule": "3_nan_mask", "reason": f"NaN 遮罩對參考實作無一核心於兩規模皆相符：{mask_ok}"}}
    err: Dict[str, Dict[str, float]] = {}
    for core in CORE_ORDER:
        err[core] = {}
        for s in scales:
            rows = unit_stats(core, s)
            if any(int(r["common_finite_cells"]) == 0 for r in rows):
                return {"no_choice": {"rule": "3_no_common_finite", "reason": f"{core} 於 ({s}) 共同有限格為 0"}}
            err[core][s] = max(float(r["max_abs"]) for r in rows)
    x, y = CORE_ORDER
    cmp = {s: (err[x][s] > err[y][s]) - (err[x][s] < err[y][s]) for s in scales}  # -1＝x 較小
    signs = set(cmp.values())
    if signs == {0}:
        return {"choice": _tiebreak(by_id), "rule": "3_error_tie"}
    if signs <= {-1, 0}:
        return {"choice": x, "rule": "3_error"}
    if signs <= {1, 0}:
        return {"choice": y, "rule": "3_error"}
    return {"no_choice": {"rule": "3_error_conflict", "reason": f"兩規模之誤差結論相反：{err}"}}


# ============================================================================================== 子行程

def copy_frozen_run(cell_id: str, work: Path) -> Dict[str, Any]:
    """凍結 run 目錄複製至 `work/copies/<格>`（凍結 run 不寫；IC 重算與各單元皆讀複本）；回複本之 features 根與身分。"""
    side = json.loads((FREEZE_RUNS / f"{cell_id}__default" / "numview_cell.json").read_text(encoding="utf-8"))
    rel = Path("features") / side["symbol"] / side["primary_tf"] / side["config_hash"]
    src = FREEZE_RUNS / f"{cell_id}__default" / rel
    dst = work / "copies" / cell_id / rel
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return {"cell": cell_id, "features_root": str(work / "copies" / cell_id / "features"),
            "config_hash": str(side["config_hash"]), "manifest_sha256": _sha256_file(src / "feature_manifest.json"),
            "copy_manifest_sha256": _sha256_file(dst / "feature_manifest.json")}


def _child_ic(spec: Mapping[str, Any]) -> Dict[str, Any]:
    """IC 重算：A（重現自證）與 C（(b) 選欄）各於其複本重算選欄。"""
    criteria = _criteria()
    out: Dict[str, Any] = {}
    for inp, cell_id in CELLS.items():
        copy = spec["copies"][inp]
        ctx = production_context(cell_id, criteria)
        started = time.perf_counter()
        sel = recompute_selection(ctx, Path(copy["features_root"]), copy["config_hash"], criteria)
        sel["seconds"] = time.perf_counter() - started
        out[inp] = sel
        _log(f"IC 重算 {cell_id}：選欄 {len(sel['selected'])}、標籤 {sel['label_rows']} 列、{sel['seconds']:.1f} 秒")
    out["peak_rss_bytes"] = _peak_rss_bytes()
    return out


def _child_unit(spec: Mapping[str, Any]) -> Dict[str, Any]:
    criteria = _criteria()
    ctx = production_context(spec["cell"], criteria)
    with tempfile.TemporaryDirectory(dir=spec["work"]) as tmp:
        tempfile.tempdir = tmp
        processed, info = transform_unit(ctx, Path(spec["features_root"]), spec["config_hash"], spec["selected"],
                                         spec["core"], spec["path"])
        if list(processed) != ["selected"]:
            raise RuntimeError(f"processed 群組非恰一個 selected：{list(processed)}")
        info["output"] = save_frame(processed["selected"], Path(spec["out_dir"]))
    info["peak_rss_bytes"] = _peak_rss_bytes()
    return info


def _child_reference(spec: Mapping[str, Any]) -> Dict[str, Any]:
    criteria = _criteria()
    out: Dict[str, Any] = {}
    for inp in ("a", "b"):
        units = [u for u in spec["units"] if u["input"] == inp]
        ctx = production_context(CELLS[inp], criteria)
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        raw = FeatureReader(spec["features_root"][inp]).load_columns_v2(
            ctx["symbol"], ctx["tf"], spec["config_hash"][inp], spec["selected"][inp], artifact_kind="raw",
            attach_row_index=True)
        cfg = reference_config(post_ic_config_summary(ctx["config"]))
        out.update(reference_stats(raw, {u["unit_id"]: SavedFrame(Path(u["out_dir"])) for u in units}, cfg))
    out["peak_rss_bytes"] = _peak_rss_bytes()
    return out


_CHILDREN = {"ic": _child_ic, "unit": _child_unit, "reference": _child_reference}


def _child(spec_path: Path) -> int:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    result = _CHILDREN[spec["kind"]](spec)
    Path(spec["result_path"]).write_text(json.dumps(result, ensure_ascii=False, default=str), encoding="utf-8")
    return 0


def _run_child(name: str, spec: Dict[str, Any], work: Path) -> Dict[str, Any]:
    """子行程經卡死監看；回 `{status, watch_status, returncode, child_wall_seconds, swap_growth_max_mb, result?, reason?}`。
    status：complete＝正常結束（watch_status＝exited 且 rc 0）且有結果；其餘 failed。"""
    results = work / "_results"
    results.mkdir(parents=True, exist_ok=True)
    result_path = results / f"{name}.json"
    result_path.unlink(missing_ok=True)
    spec_path = results / f"{name}.spec.json"
    spec = dict(spec, result_path=str(result_path), work=str(work))
    spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    wd = _watchdog()
    watched = wd.run_watched([sys.executable, str(Path(__file__).resolve()), "--child", str(spec_path)],
                             log_path=results / f"{name}.log", config=wd.load_config(_criteria()), cwd=str(REPO))
    out: Dict[str, Any] = {"watch_status": watched.status, "returncode": watched.returncode,
                           "child_wall_seconds": watched.wall_seconds, "swap_growth_max_mb": watched.swap_growth_max_mb}
    if watched.status == wd.EXITED and watched.returncode == 0 and result_path.is_file():
        out.update(status="complete", result=json.loads(result_path.read_text(encoding="utf-8")))
    else:
        out.update(status="failed", reason=f"{watched.status}（{watched.reason}；rc={watched.returncode}；"
                                           f"{watched.wall_seconds:.0f} 秒；見 {results / (name + '.log')}）")
    return out


# ============================================================================================== 收據

def assemble(ic: Mapping[str, Any], units: Sequence[Mapping[str, Any]], pairs: Sequence[Mapping[str, Any]],
             reference: Optional[Mapping[str, Any]], frozen_a_selected: Sequence[str]) -> Dict[str, Any]:
    """收據本體與自我檢查（純函式）：擇一結果、單元完整、監看與狀態一致、同輸入之單元輸入身分相同、成對比對計數可由逐欄列
    重算、A 之 IC 重算重現其凍結選欄。"""
    selection = select_core(units, pairs, (reference or {}).get("stats"))
    checks: Dict[str, bool] = {}
    ids = [str(u["unit_id"]) for u in units]
    checks["units_exactly_six"] = sorted(ids) == sorted(UNIT_IDS)
    checks["watch_status_consistent"] = all(
        u["status"] != "complete" or (u.get("watch_status") == "exited" and u.get("returncode") == 0) for u in units)
    for inp in ("a", "b"):
        shas = {u.get("input_sha256") for u in units if u["input"] == inp and u["status"] == "complete"}
        checks[f"inputs_identical_{inp}"] = len(shas) <= 1
    done = [u for u in units if u["status"] == "complete"]
    # 分塊單元逐塊呼叫 `_transform_single` ⇒ ≥ 2 次（選欄數 ≤ 塊寬則未分塊，路徑不成立）；直接單元 ≥ 1 次
    checks["chunk_calls_valid"] = all(int(u.get("chunk_calls") or 0) >= (2 if u["path"] == "chunked" else 1) for u in done)
    checks["arm_recorded_matches_path"] = all(
        list(u.get("arm_recorded") or []) == (["pandas_chunked"] if u["path"] == "chunked" else [u["core"]]) for u in done)
    checks["post_ic_config_same"] = len({json.dumps(u.get("post_ic_config"), sort_keys=True) for u in done}) <= 1
    checks["pair_counts_recomputable"] = all(
        p["columns_unequal_native"] == len(p["diff_columns"]["column"])
        and p["nan_mask_diff"] == sum(p["diff_columns"]["nan_mask_diff"])
        and p["value_neq_cells"] == sum(p["diff_columns"]["value_neq_cells"])
        and p["dtype_mismatch_columns"] == sum(1 for a, b in zip(p["diff_columns"]["dtype_x"], p["diff_columns"]["dtype_y"])
                                               if a != b) for p in pairs)
    repro = ic.get("status") == "complete" and list(ic["result"]["a"]["selected"]) == [str(c) for c in frozen_a_selected]
    checks["ic_recompute_reproduces_a"] = bool(repro) if ic.get("status") == "complete" else True
    checks["no_choice_without_choice"] = ("choice" in selection) != ("no_choice" in selection)
    body: Dict[str, Any] = {"units": list(units), "pairs": list(pairs), "reference": reference, "checks": checks}
    if "choice" in selection:
        body.update(choice=selection["choice"], choice_rule=selection["rule"])
    else:
        body["no_choice"] = selection["no_choice"]
    return body


def _unit_row(uid: str, inp: str, run: Mapping[str, Any]) -> Dict[str, Any]:
    core, path, _ = uid.split("__")
    row: Dict[str, Any] = {"unit_id": uid, "core": core, "path": path, "input": inp, "cell": CELLS[inp],
                           "status": run["status"], "watch_status": run.get("watch_status"),
                           "returncode": run.get("returncode"), "child_wall_seconds": run.get("child_wall_seconds"),
                           "swap_growth_max_mb": run.get("swap_growth_max_mb"), "reason": run.get("reason")}
    result = run.get("result") or {}
    for key in ("wall_seconds", "load_seconds", "peak_rss_bytes", "arm_recorded", "core_observed", "chunk_calls",
                "ratio_unsafe_dropped", "terminals", "input_columns", "input_rows", "input_sha256", "post_ic_config", "output"):
        row[key] = result.get(key)
    return row


def _parse(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NUMVIEW Task 1.6 post-IC 單一 pandas 核心擇一")
    parser.add_argument("--out", default=None, help="收據輸出路徑（未給 ⇒ 正式收據 handoffs/run_receipts/<date>-numview-postic-core-select.json）")
    parser.add_argument("--work-root", default=str(DEFAULT_WORK_ROOT))
    parser.add_argument("--child", default=None, help=argparse.SUPPRESS)
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """量測主入口；rc 0＝收據寫出且其自我檢查一致（結果為 `choice` 或 `no_choice` 皆合格，見 SPEC Task 1.6 擇一規則）；
    rc≠0＝探針自身失敗或收據自相矛盾。"""
    args = _parse(argv)
    if args.child:
        return _child(Path(args.child))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    work = Path(args.work_root) / stamp
    work.mkdir(parents=True, exist_ok=True)
    side_a = json.loads((FREEZE_RUNS / f"{CELLS['a']}__default" / "numview_cell.json").read_text(encoding="utf-8"))
    run_a = FREEZE_RUNS / f"{CELLS['a']}__default" / "features" / side_a["symbol"] / side_a["primary_tf"] / side_a["config_hash"]
    frozen_a = json.loads(next(run_a.glob("ic_selected_features_*.json")).read_text(encoding="utf-8"))["selected"]
    if [str(c) for c in frozen_a] != [str(c) for c in side_a["ic_first_selected"]]:
        raise RuntimeError("A 之 ic_selected_features 與凍結 sidecar 之選欄不同")

    copies = {inp: copy_frozen_run(cell_id, work) for inp, cell_id in CELLS.items()}
    _log("IC 重算（A 重現自證＋C 選欄）")
    ic = _run_child("ic", {"kind": "ic", "copies": copies}, work)
    ic_row = {k: ic.get(k) for k in ("status", "watch_status", "returncode", "child_wall_seconds", "swap_growth_max_mb",
                                     "reason")}
    ic_row["wall_seconds"] = ic.get("child_wall_seconds")
    ic_row["peak_rss_bytes"] = (ic.get("result") or {}).get("peak_rss_bytes")
    inputs: Dict[str, Dict[str, Any]] = {"a": dict(copies["a"], selected=[str(c) for c in frozen_a], selected_source="frozen")}
    if ic["status"] == "complete":
        res = ic["result"]
        for inp in ("a", "b"):
            ic_row[inp] = {k: res[inp][k] for k in ("label_rows", "label_sha256", "selection_window", "ic_params", "seconds")}
            ic_row[inp]["selected_count"] = len(res[inp]["selected"])
        inputs["b"] = dict(copies["b"], selected=list(res["b"]["selected"]), selected_source="ic_recompute")
        repro_ok = list(res["a"]["selected"]) == [str(c) for c in frozen_a]
    else:
        repro_ok = False
        inputs["b"] = dict(copies["b"], selected=[], selected_source="ic_recompute")
    units: List[Dict[str, Any]] = []
    for path, inp in PATHS:
        for core_name in CORE_ORDER:
            core = core_name.replace("pandas_", "")
            uid = f"{core_name}__{path}__{inp}"
            if inp == "b" and (ic["status"] != "complete" or not repro_ok):
                why = ic.get("reason") if ic["status"] != "complete" else "A 之 IC 重算未重現凍結選欄（程序與生產不符）"
                units.append(_unit_row(uid, inp, {"status": "blocked", "reason": f"(b) 選欄不可得：{why}"}))
                continue
            _log(f"單元 {uid}（{len(inputs[inp]['selected'])} 選欄）")
            spec = {"kind": "unit", "cell": CELLS[inp], "core": core, "path": path,
                    "features_root": inputs[inp]["features_root"], "config_hash": inputs[inp]["config_hash"],
                    "selected": inputs[inp]["selected"], "out_dir": str(work / "outputs" / uid)}
            row = _unit_row(uid, inp, _run_child(uid, spec, work))
            row["out_dir"] = spec["out_dir"]
            units.append(row)
            _log(f"{uid}：{row['status']}，transform {row.get('wall_seconds')} 秒，核心 {row.get('core_observed')}")
    by_id = {u["unit_id"]: u for u in units}
    pairs: List[Dict[str, Any]] = []
    for path, inp in PATHS:
        x, y = (by_id[f"{c}__{path}__{inp}"] for c in CORE_ORDER)
        if x["status"] == y["status"] == "complete":
            row = compare_saved(SavedFrame(Path(x["out_dir"])), SavedFrame(Path(y["out_dir"])))
            pairs.append({"path": path, "input": inp, "units": [x["unit_id"], y["unit_id"]], **row})
            _log(f"成對 {path}/{inp}：逐位元相等 {row['bitwise_equal']}、結構一致 {row['structure_equal']}、"
                 f"dtype 不符欄 {row['dtype_mismatch_columns']}、值不等格 {row['value_neq_cells']}")
    reference: Optional[Dict[str, Any]] = None
    needs_reference = (len(pairs) == len(PATHS) and all(u["status"] == "complete" for u in units)
                       and all(p["structure_equal"] for p in pairs) and not all(p["bitwise_equal"] for p in pairs))
    if needs_reference:
        _log("參考實作比對（規則③）")
        spec = {"kind": "reference", "units": [{"unit_id": u["unit_id"], "input": u["input"], "out_dir": u["out_dir"]}
                                               for u in units],
                "features_root": {k: v["features_root"] for k, v in inputs.items()},
                "config_hash": {k: v["config_hash"] for k, v in inputs.items()},
                "selected": {k: v["selected"] for k, v in inputs.items()}}
        run = _run_child("reference", spec, work)
        result = dict(run.get("result") or {})
        reference = {k: run.get(k) for k in ("status", "watch_status", "returncode", "child_wall_seconds", "reason")}
        reference["peak_rss_bytes"] = result.pop("peak_rss_bytes", None)
        reference["stats"] = result if run["status"] == "complete" else None
    body = assemble(ic, units, pairs, reference, frozen_a)
    receipt = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
               "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True).stdout.strip(),
               "command": " ".join(["venv/bin/python", "handoffs/run_receipts/numview_probes/postic_core_select.py",
                                    *(list(argv) if argv is not None else sys.argv[1:])]),
               "criteria_sha256": hashlib.sha256(_criteria_path().read_bytes()).hexdigest(), "work_root": str(work),
               "inputs": {k: {kk: (len(vv) if kk == "selected" else vv) for kk, vv in v.items()} for k, v in inputs.items()},
               "ic_recompute": ic_row, **body}
    receipt["exit_code"] = 0 if all(receipt["checks"].values()) else 3
    dest = Path(args.out) if args.out else RECEIPTS_DIR / f"{datetime.now().strftime('%Y%m%d')}-numview-postic-core-select.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    _log(f"收據 {dest}；檢查 {receipt['checks']}；"
         f"{'choice=' + receipt['choice'] if 'choice' in receipt else 'no_choice=' + json.dumps(receipt['no_choice'], ensure_ascii=False)}")
    return int(receipt["exit_code"])


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))

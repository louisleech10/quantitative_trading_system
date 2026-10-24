"""NUMVIEW 精度鏈逐段量測（docs/NUMVIEW_SPEC.md Task 1.2，C6；不重議 2026-09-29 dtype 裁定；SPEC v37）。

凍結 run 只留落盤產物 ⇒ 記憶體內檢查點 S0–S2 於重生當下以 spy 擷取（只存輸出段列於
`data_cache/numview_precision_tmp/`，比對完即刪）；S3／S4 讀落盤。參照 run R＝float64 層間鏈之 run（A＝`s0_float64_chain`
變體；B＝生產本身；C＝`c_preserve_dtype`），生產 run P（A＝`codec_upgrade_on` 變體之 S1／S2＋凍結讀回；C＝凍結讀回）。
S0 列＝R 內部 S0 對 R 之 S1（只含轉 float32）；S1–S3 列＝P 對 R 同檢查點逐欄；S5＝逐群組重演生產選欄。分岔：
`mtf_layer_dtype`（B 之 S1 對 A 生產 S1）、`memmap_merge_dtype`（兩 memmap 變體開 lag）、`winsor_sigma_dtype`（生產不可達、
探針自建）；`codec_checks`（raw BSS 無損、名稱推斷誤判）；`extension`（同起點終點提前 `TAIL_EXTENSION_BARS` 根）。
收據 `handoffs/run_receipts/<date>-numview-precision-chain.json`，含 `criteria_sha256`、`runs` 身分表與 `observed_settings`。

正式跑（不帶 `--out`）前置：`_estimate_gate.require("precision_chain", 全部格)`＋估時收據 `addenda` 恰等於
`estimate.PRECISION_ADDENDA` 且兩 memmap 列 `measured_lag_on`；試跑（`--out`）只供 SPEC 細則⑦實測與冒煙。
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
import pickle
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

import numpy as np

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

PROBES_DIR = Path(__file__).resolve().parent
RECEIPTS_DIR = REPO / "handoffs" / "run_receipts"
FREEZE_SCRIPT = REPO / "scripts" / "numview_freeze_baseline.py"
FREEZE_RUNS = REPO / "data_cache" / "numview_freeze_runs"
DEFAULT_WORK_ROOT = REPO / "data_cache" / "numview_precision_runs"
TMP_ROOT = REPO / "data_cache" / "numview_precision_tmp"

SEGMENTS: Tuple[str, ...] = ("S0", "S1", "S2", "S3", "S4", "S5")
#: SPEC v37 細則③：尾端延伸變體之終點提前根數（輸出段 500 ⇒ 400）
TAIL_EXTENSION_BARS = 100
#: memmap 門檻強制值（SPEC：門檻設 0 與極大）
MEMMAP_LOW, MEMMAP_HIGH = 0, 10 ** 18
HOST_CELL = "A_BTCUSDT_1h"
#: 校準資料域暫存 registry 目錄之前綴（`preprocessing/calibration.py` 之 `CALIBRATION_TMP_PREFIX`）
CALIBRATION_TMP_MARK = "ffstat_calib_"
B_CELL, C_CELL = "B_BTCUSDT_1h_4h", "C_BTCUSDT_1h"

#: 每個 `source_run` 之格、生成環境、設定覆寫（判準六變體、兩增列；`freeze_*` 為讀凍結 run，不生成）
RUN_SPECS: Dict[str, Dict[str, Any]] = {
    "s0_float64_chain": {"cell": HOST_CELL, "env": {}, "override": None, "preserve": True, "lift_l2": True},
    "memmap_forced_low": {"cell": HOST_CELL, "env": {}, "override": {"lag_features": {"enabled": True}},
                          "memmap": MEMMAP_LOW},
    "memmap_forced_high": {"cell": HOST_CELL, "env": {}, "override": {"lag_features": {"enabled": True}},
                           "memmap": MEMMAP_HIGH},
    "codec_upgrade_on": {"cell": HOST_CELL, "env": {"FFACT_L7_CODEC_UPGRADE": "1"}, "override": None},
    "tail_extension": {"cell": HOST_CELL, "env": {}, "override": None, "end_offset_bars": TAIL_EXTENSION_BARS},
    "winsor_sigma_dtype": {"cell": HOST_CELL, "env": {},
                           "override": {"preprocessing": {"winsorization": {"enabled": True, "method": "sigma"}}},
                           "winsor_fork": True},
    "b_production_spy": {"cell": B_CELL, "env": {"FFACT_MULTI_TF_PARALLEL": "0"}, "override": None},
    # SPEC v39：C 之 R run 停用主鏈 layer2 spill（`feature_factory.py:531`；spill 轉 float32 使 L3–L6 讀非 float64 之 layer2）
    "c_preserve_dtype": {"cell": C_CELL, "env": {}, "override": None, "preserve": True, "lift_l2": True,
                         "bypass_l2_spill": True},
}
FREEZE_RUN_NAMES: Dict[str, str] = {HOST_CELL: "freeze_A", B_CELL: "freeze_B", C_CELL: "freeze_C"}

#: 各 `source_run` 之 `observed_settings` 期望（SPEC v37 驗證段：逐鍵相等；窄測試字面鎖定）。`end_offset_bars` 為相對
#: 判準輸出段終點之提前根數（探針依此導出期望 `end_date`）；`memmap_threshold_bytes`／`memmap_branch` 只計
#: `layer4_input` 合併點；`lag_enabled`／`preserve_dtype` 為觀測值之排序集合。
_A_BASE: Dict[str, Any] = {"preserve_dtype": [False], "l2_polars_lift": False, "memmap_threshold_bytes": [500_000_000],
                           "memmap_branch": ["concat"], "spill_triggered": False, "lag_enabled": [False],
                           "codec_upgrade": False, "winsor_method": ["quantile"], "stationarity": ["fracdiff+adf"],
                           "end_offset_bars": 0, "multi_tf_parallel_calls": 0}
VARIANT_SETTINGS: Dict[str, Dict[str, Any]] = {
    "s0_float64_chain": {**_A_BASE, "preserve_dtype": [True], "l2_polars_lift": True},
    "memmap_forced_low": {**_A_BASE, "memmap_threshold_bytes": [MEMMAP_LOW], "memmap_branch": ["memmap"],
                          "lag_enabled": [True]},
    "memmap_forced_high": {**_A_BASE, "memmap_threshold_bytes": [MEMMAP_HIGH], "lag_enabled": [True]},
    "codec_upgrade_on": {**_A_BASE, "codec_upgrade": True},
    "tail_extension": {**_A_BASE, "end_offset_bars": TAIL_EXTENSION_BARS},
    "winsor_sigma_dtype": {**_A_BASE, "winsor_method": ["sigma"]},
    "b_production_spy": {"preserve_dtype": [True], "l2_polars_lift": False, "spill_triggered": False,
                         "lag_enabled": [False], "codec_upgrade": False, "winsor_method": ["quantile"],
                         "stationarity": ["fracdiff+adf"], "end_offset_bars": 0, "multi_tf_parallel_calls": 0},
    "c_preserve_dtype": {"preserve_dtype": [True], "l2_polars_lift": True, "spill_triggered": False,
                         "l2_spill_bypassed": True, "lag_enabled": [True], "codec_upgrade": False, "end_offset_bars": 0,
                         "multi_tf_parallel_calls": 0},
}

_MODULES: Dict[str, Any] = {}


def _log(message: str) -> None:
    print(f"[precision] {datetime.now().strftime('%H:%M:%S')} {message}", flush=True)


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


def _gate() -> Any:
    return _load("numview_estimate_gate", PROBES_DIR / "_estimate_gate.py")


def _estimate() -> Any:
    return _load("numview_estimate", PROBES_DIR / "estimate.py")


def _watchdog() -> Any:
    return _load("numview_watchdog", PROBES_DIR / "_watchdog.py")


def _freeze() -> Any:
    return _load("numview_freeze_baseline_precision", FREEZE_SCRIPT)


def _criteria() -> Dict[str, Any]:
    from tests.feature_engineering import numview_helpers as nh

    return json.loads(nh.current_criteria_path().read_text(encoding="utf-8"))


def _criteria_sha256() -> str:
    from tests.feature_engineering import numview_helpers as nh

    return hashlib.sha256(nh.current_criteria_path().read_bytes()).hexdigest()


def _cell(cell_id: str) -> Dict[str, Any]:
    for c in _criteria()["cell_rules"]["cell_list"]["cells"]:
        if str(c["id"]) == cell_id:
            return {"id": str(c["id"]), "kind": str(c["kind"]), "symbol": str(c["symbol"]),
                    "timeframes": [str(t) for t in c["timeframes"]]}
    raise KeyError(cell_id)


def _deep_merge(base: Any, override: Any) -> Any:
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override
    out = dict(base)
    for key, value in override.items():
        out[key] = _deep_merge(out.get(key), value)
    return out


# ============================================================================================== 統計


def checkpoint_stats(values: np.ndarray, reference: np.ndarray) -> Dict[str, Any]:
    """單欄於一檢查點對參照之統計：`max_abs`、`max_rel`（|ref| 為 0 之格不計相對差）、`nan_mask_diff`（NaN 遮罩相異格數）、
    `float16_ok`（依現行 `FeatureStorage._select_parquet_storage_array` 判定 `values` 可否存 float16，只讀）；兩邊皆無
    有限值 ⇒ `all_nan=True`、`max_abs`／`max_rel` 為 None、`float16_ok=True`（邊界①）。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    v = np.asarray(values, dtype=np.float64)
    r = np.asarray(reference, dtype=np.float64)
    if v.shape != r.shape:
        raise ValueError(f"形狀不符：{v.shape} vs {r.shape}")

    def _kind(x: np.ndarray) -> np.ndarray:  # 0＝有限、1＝NaN、2＝+inf、3＝−inf（審碼 r9：inf 與 NaN 不得視為同類）
        return np.where(np.isnan(x), 1, np.where(np.isposinf(x), 2, np.where(np.isneginf(x), 3, 0)))

    kind_v, kind_r = _kind(v), _kind(r)
    nan_mask_diff = int(np.count_nonzero(kind_v != kind_r))
    both = (kind_v == 0) & (kind_r == 0)
    if not (kind_v == 0).any() and not (kind_r == 0).any() and nan_mask_diff == 0 \
            and not (kind_v > 1).any():
        return {"all_nan": True, "max_abs": None, "max_rel": None, "nan_mask_diff": 0, "float16_ok": True}
    _, storage_dtype = FeatureStorage._select_parquet_storage_array(np.asarray(values))
    if not both.any():
        return {"all_nan": False, "max_abs": None, "max_rel": None, "nan_mask_diff": nan_mask_diff,
                "float16_ok": storage_dtype == "float16"}
    diff = np.abs(v[both] - r[both])
    ref = np.abs(r[both])
    nz = ref > 0
    return {"all_nan": False, "max_abs": float(diff.max()), "max_rel": float((diff[nz] / ref[nz]).max()) if nz.any() else None,
            "nan_mask_diff": nan_mask_diff, "float16_ok": storage_dtype == "float16"}


def aggregate_group(stats: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """群組列之聚合語意（SPEC v37 細則①）：`max_abs`／`max_rel` 取群組最大（全 all_nan ⇒ None）、`nan_mask_diff` 加總、
    `all_nan`／`float16_ok` 全稱、`material` 任一並記 `material_columns`。"""
    def _max(key: str) -> Optional[float]:
        vals = [float(s[key]) for s in stats if s.get(key) is not None]
        return max(vals) if vals else None

    return {"columns_in_group": len(stats), "max_abs": _max("max_abs"), "max_rel": _max("max_rel"),
            "nan_mask_diff": int(sum(int(s.get("nan_mask_diff") or 0) for s in stats)),
            "all_nan": all(bool(s.get("all_nan")) for s in stats), "float16_ok": all(bool(s.get("float16_ok")) for s in stats),
            "material": any(bool(s.get("material")) for s in stats),
            "material_columns": int(sum(1 for s in stats if s.get("material")))}


# ============================================================================================== 擷取


def _time_axis(obs: Any, index: Any) -> Optional[np.ndarray]:
    """表之時間軸（epoch 秒）：索引本身為時間或 epoch 者直接換算；位置索引（L6.5 sink 內群組表為 RangeIndex）⇒ 取本 run
    最近同列數之層表時間軸；皆無 ⇒ None。"""
    ep = _epoch_seconds(index)
    if ep.size and int(ep.min()) >= 10 ** 9:
        return ep
    return obs.recent_index.get(int(len(ep)))


def _epoch_seconds(index: Any) -> np.ndarray:
    """DatetimeIndex ⇒ UTC epoch 秒（無時區者視為 UTC；工廠時間軸 asi8＝h5 UTC 奈秒，SPEC Task 1.1 主委查證）。"""
    import pandas as pd

    if not pd.api.types.is_datetime64_any_dtype(getattr(index, "dtype", None)):
        # CGSA 路徑之層表索引為 int64 epoch 秒或毫秒（feature_factory.py:3768 註；單位偵測同 `_derive_row_index_for_artifact`）
        vals = np.asarray(index, dtype=np.int64)
        return vals // 1000 if vals.size and abs(int(vals[0])) >= 10 ** 12 else vals
    idx = pd.DatetimeIndex(index)
    if idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    # pandas 2 之時間軸解析度可為 ms／us（`asi8` 隨單位而變）⇒ 一律經 datetime64[s] 換算
    return idx.values.astype("datetime64[s]").astype(np.int64)


class Capture:
    """一次生成之檢查點擷取：只存輸出段列（時間戳 ∈ [start, end]）之陣列與欄名，寫入 `root`。"""

    def __init__(self, root: Path, start_epoch: int, end_epoch: int) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.start, self.end = int(start_epoch), int(end_epoch)
        self.meta: List[Dict[str, Any]] = []
        self.seq = 0

    def rows(self, epochs: np.ndarray) -> np.ndarray:
        """輸出段列之位置（時間戳 ∈ [start, end]）。"""
        return np.flatnonzero((epochs >= self.start) & (epochs <= self.end))

    def save(self, segment: str, key: str, columns: Sequence[str], values: np.ndarray, epochs: Optional[np.ndarray],
             **extra: Any) -> None:
        arr = np.asarray(values)
        if arr.ndim == 1:
            arr = arr.reshape(-1, 1)
        if epochs is not None:
            keep = (epochs >= self.start) & (epochs <= self.end)
            arr, epochs = arr[keep], epochs[keep]
        self.seq += 1
        name = f"{segment}_{self.seq:06d}.npy"
        np.save(self.root / name, np.ascontiguousarray(arr))
        if epochs is not None:
            np.save(self.root / f"{segment}_{self.seq:06d}_t.npy", epochs)
        self.meta.append({"segment": segment, "key": str(key), "file": name, "columns": [str(c) for c in columns],
                          "dtype": str(arr.dtype), "rows": int(arr.shape[0]),
                          "epochs_file": None if epochs is None else f"{segment}_{self.seq:06d}_t.npy", **extra})

    def write_meta(self, extra: Mapping[str, Any]) -> None:
        (self.root / "capture.json").write_text(json.dumps({"entries": self.meta, **extra}, ensure_ascii=False,
                                                           default=str), encoding="utf-8")


def load_capture(root: Path) -> Dict[str, Any]:
    return json.loads((Path(root) / "capture.json").read_text(encoding="utf-8"))


def _storage_name(column: str, tf: Optional[str]) -> str:
    """registry 欄名 ⇒ 落盤欄名（週期標記；與生產落盤同一規則 `feature_naming.tag_timeframe`，
    `preprocessing/calibration.py:190-197`）；無週期者原名。"""
    from momentum.FeatureEngineering import feature_naming

    return feature_naming.tag_timeframe(str(column), str(tf)) if tf and tf != "None" else str(column)


def capture_columns(root: Path, segment: str) -> Dict[str, Tuple[np.ndarray, np.ndarray, str]]:
    """{落盤欄名: (值〔輸出段列〕, epoch 秒, 群組鍵)}；擷取時帶週期者（S0／S1／L4IN）換成落盤欄名；同欄多次擷取取最後一次
    （同欄重寫＝同群組重算）。"""
    out: Dict[str, Tuple[np.ndarray, np.ndarray, str]] = {}
    for entry in load_capture(root)["entries"]:
        if entry["segment"] != segment or not entry.get("rows"):
            continue
        arr = np.load(Path(root) / entry["file"])
        ep = np.load(Path(root) / entry["epochs_file"]) if entry.get("epochs_file") else None
        for j, col in enumerate(entry["columns"]):
            out[_storage_name(col, entry.get("tf"))] = (arr[:, j], ep, str(entry["key"]))
    return out


def capture_dtypes(root: Path, segment: str) -> Dict[str, str]:
    """{落盤欄名: 擷取時之原生 dtype}（S0 用以標非 float64 之欄：S0 鏈未完整抬升處）。"""
    out: Dict[str, str] = {}
    for entry in load_capture(root)["entries"]:
        if entry["segment"] == segment and entry.get("rows") and entry.get("column_dtypes"):
            for col, dt in zip(entry["columns"], entry["column_dtypes"]):
                out[_storage_name(col, entry.get("tf"))] = str(dt)
    return out


# ============================================================================================== spy


@contextlib.contextmanager
def _patched(owner: Any, name: str, replacement: Any) -> Iterator[None]:
    original = owner.__dict__[name] if isinstance(owner, type) and name in owner.__dict__ else getattr(owner, name)
    setattr(owner, name, replacement)
    try:
        yield
    finally:
        setattr(owner, name, original)


class Observer:
    """生成內之觀測（`observed_settings` 與檢查點擷取）。"""

    def __init__(self, capture: Capture, spec: Mapping[str, Any]) -> None:
        self.capture, self.spec = capture, spec
        self.preserve: set = set()
        self.calibration_preserve: set = set()
        self.calib_depth = 0
        self.l2_lift_calls = 0
        self.recent_index: Dict[int, np.ndarray] = {}
        self.memmap_thresholds: set = set()
        self.memmap_branches: set = set()
        self.layer4_merge: List[Dict[str, Any]] = []
        self.spill = False  # 主鏈 layer2 實際 spill（校準域 `calib_layer2` 另記；SPEC v39）
        self.calibration_spill = False
        self.l2_spill_bypassed = 0
        self.l2_consumer_dtypes: set = set()  # 主鏈 spill 點之 layer2 dtype（L3–L6 讀入者）
        self.lag_enabled: set = set()
        self.codec: set = set()
        self.winsor_methods: set = set()
        self.stationarity: set = set()
        self.end_dates: List[str] = []
        self.parallel_calls = 0
        self.l2_return_dtypes: set = set()
        self.captured_tfs: Dict[str, set] = {}
        self.factory: Any = None
        self.raw_fallbacks: List[Dict[str, Any]] = []
        self.processed_fallbacks: List[Dict[str, Any]] = []
        self.ic_calls: List[Dict[str, Any]] = []
        self.ic_input_dtypes: set = set()
        self.winsor_fork: List[Dict[str, Any]] = []
        self.storage_dtypes: Dict[str, str] = {}
        self.preprocessor_args: Dict[int, Tuple[Any, ...]] = {}

    def settings(self) -> Dict[str, Any]:
        return {"preserve_dtype": sorted(self.preserve), "calibration_preserve_dtype": sorted(self.calibration_preserve),
                "l2_polars_lift": self.l2_lift_calls > 0,  # 實際觀測抬升生效（審碼 r11）
                "l2_return_dtypes": sorted(self.l2_return_dtypes),
                "memmap_threshold_bytes": sorted(self.memmap_thresholds), "memmap_branch": sorted(self.memmap_branches),
                "spill_triggered": self.spill, "calibration_spill": self.calibration_spill,
                "l2_spill_bypassed": self.l2_spill_bypassed > 0, "l2_consumer_dtypes": sorted(self.l2_consumer_dtypes),
                "lag_enabled": sorted(self.lag_enabled),
                "codec_upgrade": any(self.codec), "winsor_method": sorted(self.winsor_methods),
                "stationarity": sorted(self.stationarity), "end_dates": sorted(set(self.end_dates)),
                "multi_tf_parallel_calls": self.parallel_calls,
                "captured_timeframes": {tf: sorted(segs) for tf, segs in sorted(self.captured_tfs.items())}}


@contextlib.contextmanager
def install_spies(obs: Observer) -> Iterator[None]:
    """掛全部觀測 spy（各 run 共用；變體專屬之改值掛於 `install_variant`）。"""
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.FeatureEngineering import feature_storage as fs_mod
    from momentum.FeatureEngineering import memmap_utils
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.operators.lag_processor import LagProcessor
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
    from momentum.FeatureEngineering.timeframe import multi_tf_generator as mtf

    stack = contextlib.ExitStack()
    real_exec = FeatureFactory._execute_layer1_6

    def exec_spy(self: Any, layer_name: str, func: Callable, *args: Any, preserve_dtype: bool = False) -> Any:
        if getattr(self, "_calibration_domain", False):
            # 校準資料域之獨立工廠實例（feature_factory.py:2700 起；各層落暫存 registry 之 float32，與主生成之層間 dtype
            # 無關）：照生產執行、不擷取、另記觀測
            obs.calibration_preserve.add(bool(preserve_dtype))
            obs.calib_depth += 1
            try:
                return real_exec(self, layer_name, func, *args, preserve_dtype=preserve_dtype)
            finally:
                obs.calib_depth -= 1
        obs.factory = self
        if obs.spec.get("preserve"):
            preserve_dtype = True
        obs.preserve.add(bool(preserve_dtype))
        for arg in args:  # 層輸入表之時間軸（供 registry 陣列對時；CGSA 層表索引為 int64 epoch）
            if hasattr(arg, "index") and hasattr(arg, "columns") and len(arg.index) > 0:
                ep = _epoch_seconds(arg.index)
                obs.recent_index[len(ep)] = ep
        return real_exec(self, layer_name, func, *args, preserve_dtype=preserve_dtype)

    stack.enter_context(_patched(FeatureFactory, "_execute_layer1_6", exec_spy))

    real_coerce = FeatureFactory.__dict__["_coerce_persistence_frame"]

    def coerce_spy(df: Any) -> Any:
        """S0＝registry 落盤前（轉 float32 之前）之層值（feature_factory.py:1328、:1365、:1401、:4718 四處落盤皆經此；
        含 L3 串流）；只切輸出段列再轉陣列。"""
        if obs.calib_depth == 0 and df is not None and not df.empty:
            ep = _epoch_seconds(df.index)
            obs.recent_index[len(ep)] = ep
            rows = obs.capture.rows(ep)
            tf = str(getattr(obs.factory, "_current_timeframe", None))
            obs.capture.save("S0", f"{tf}:persist", list(df.columns), df.iloc[rows].to_numpy(), ep[rows], tf=tf,
                             dtypes=sorted({str(t) for t in df.dtypes}), column_dtypes=[str(t) for t in df.dtypes])
            obs.captured_tfs.setdefault(tf, set()).add("S0")
        return real_coerce.__func__(df)

    stack.enter_context(_patched(FeatureFactory, "_coerce_persistence_frame", staticmethod(coerce_spy)))

    real_save = ColumnGroupRegistry.save_data

    def save_spy(self: Any, group: Any, data: np.ndarray) -> Any:
        if CALIBRATION_TMP_MARK in str(getattr(self, "_work_dir", "")):  # 校準資料域之暫存 registry：不擷取
            return real_save(self, group, data)
        arr = np.asarray(data)
        tf = getattr(group, "timeframe", None)
        ep = obs.recent_index.get(int(arr.shape[0])) if arr.ndim == 2 and obs.calib_depth == 0 else None
        if ep is not None:
            obs.capture.save("S1", str(group.group_id), list(group.columns), arr, ep, tf=str(tf),
                             layer=str(getattr(group, "layer", "")))
            obs.captured_tfs.setdefault(str(tf), set()).add("S1")
        else:  # 對不上時間軸之群組：記錄並使比對 fail-closed（`unindexed_violations`）
            obs.capture.meta.append({"segment": "S1_unindexed", "key": str(group.group_id), "rows": int(arr.shape[0]),
                                     "columns": [str(c) for c in group.columns], "tf": str(tf)})
        return real_save(self, group, data)

    stack.enter_context(_patched(ColumnGroupRegistry, "save_data", save_spy))

    real_select = fs_mod.FeatureStorage.__dict__["_select_parquet_storage_columns"]

    def select_spy(cls: Any, data: np.ndarray, columns: List[str], pa_module: Any) -> Any:
        out = real_select.__func__(cls, data, columns, pa_module)
        arr = np.asarray(data)
        obs.capture.save("S2", f"sink:{obs.capture.seq + 1}", list(columns), arr, None)
        float32_cols = set(out[2])
        for c in columns:
            obs.storage_dtypes[str(c)] = "float32" if str(c) in float32_cols else "float16"
        return out

    stack.enter_context(_patched(fs_mod.FeatureStorage, "_select_parquet_storage_columns", classmethod(select_spy)))

    real_concat = memmap_utils.concat_with_memmap

    def concat_spy(dfs: List[Any], index: Any = None, threshold_bytes: int = memmap_utils.MEMMAP_THRESHOLD_BYTES) -> Any:
        if obs.spec.get("memmap") is not None:
            threshold_bytes = int(obs.spec["memmap"])
        valid = [d for d in dfs if d is not None and not d.empty]
        if len(valid) >= 2:  # layer4_input（`_combine_layers` 白名單中唯一多表合併點，feature_factory.py:2113）
            est = int(valid[0].shape[0]) * sum(int(d.shape[1]) for d in valid) * 4
            branch = "concat" if est < threshold_bytes else "memmap"
            obs.memmap_thresholds.add(int(threshold_bytes))
            obs.memmap_branches.add(branch)
            result = real_concat(dfs, index=index, threshold_bytes=threshold_bytes)
            ep = _epoch_seconds(result.index)
            rows = obs.capture.rows(ep)
            obs.capture.save("L4IN", f"layer4_input:{branch}", list(result.columns), result.iloc[rows].to_numpy(),
                             ep[rows], dtypes=sorted({str(t) for t in result.dtypes}),
                             tf=str(getattr(obs.factory, "_current_timeframe", None)))
            obs.layer4_merge.append({"branch": branch, "estimated_bytes": est, "threshold_bytes": int(threshold_bytes),
                                     "columns": int(result.shape[1]), "dtypes": sorted({str(t) for t in result.dtypes})})
            return result
        return real_concat(dfs, index=index, threshold_bytes=threshold_bytes)

    stack.enter_context(_patched(memmap_utils, "concat_with_memmap", concat_spy))

    real_spill = FeatureFactory.__dict__["_spill_to_memmap"]

    def spill_spy(df: Any, label: str, dir: Optional[str] = None) -> Any:
        big = df is not None and not df.empty and df.shape[0] * df.shape[1] * 8 >= 500_000_000  # 同 `:572-575` 門檻
        if label != "layer2":  # 校準域（`feature_factory.py:2745` 之 `calib_layer2`）照生產，另記
            obs.calibration_spill = obs.calibration_spill or big
        else:
            if df is not None:
                obs.l2_consumer_dtypes.update(str(t) for t in df.dtypes)
            if obs.spec.get("bypass_l2_spill"):  # SPEC v39：C 之 R run 保留層間 float64 之 layer2
                obs.l2_spill_bypassed += 1
                return df
            obs.spill = obs.spill or big
        return real_spill.__func__(df, label, dir) if isinstance(real_spill, staticmethod) else real_spill(df, label, dir)

    stack.enter_context(_patched(FeatureFactory, "_spill_to_memmap", staticmethod(spill_spy)))

    real_lag = LagProcessor.compute_all

    def lag_spy(self: Any, features_df: Any, *args: Any, **kwargs: Any) -> Any:
        obs.lag_enabled.add(bool(self._enabled))
        return real_lag(self, features_df, *args, **kwargs)

    stack.enter_context(_patched(LagProcessor, "compute_all", lag_spy))

    real_pp_init = FeaturePreprocessor.__init__

    def pp_init_spy(self: Any, config: Any, context: Any = None, column_layer_map: Any = None,
                    column_timeframe_map: Any = None) -> None:
        real_pp_init(self, config, context, column_layer_map, column_timeframe_map)
        obs.preprocessor_args[id(self)] = (config, context, column_layer_map, column_timeframe_map)
        if self.winsor_config.get("enabled", True):
            obs.winsor_methods.add(str(self.winsor_config.get("method", "quantile")))
        frac, adf = bool(self.fracdiff_config.get("enabled", False)), bool(self.adf_config.get("enabled", False))
        if frac or adf:
            obs.stationarity.add("+".join(n for n, on in (("fracdiff", frac), ("adf", adf)) if on))

    stack.enter_context(_patched(FeaturePreprocessor, "__init__", pp_init_spy))

    real_par = mtf.MultiTFGenerator._generate_multi_tf_cgsa_parallel

    def par_spy(self: Any, *args: Any, **kwargs: Any) -> Any:
        obs.parallel_calls += 1
        return real_par(self, *args, **kwargs)

    stack.enter_context(_patched(mtf.MultiTFGenerator, "_generate_multi_tf_cgsa_parallel", par_spy))

    for entry_name in ("run_ic_first", "generate_features"):
        real_entry = getattr(FeatureFactory, entry_name)

        def entry_spy(self: Any, *args: Any, _real: Callable = real_entry, **kwargs: Any) -> Any:
            if kwargs.get("end_date") is not None:
                obs.end_dates.append(str(kwargs["end_date"]))
            return _real(self, *args, **kwargs)

        stack.enter_context(_patched(FeatureFactory, entry_name, entry_spy))

    # codec：寫出時之有效開關與回退擷取（SPEC v37 細則⑤）
    real_writer = fs_mod._write_parquet_with_codec
    current: Dict[str, Any] = {}

    def writer_spy(table: Any, output_path: Any, *, float32_cols: List[str], **kwargs: Any) -> Any:
        obs.codec.add(bool(fs_mod.get_l7_codec_upgrade_enabled()))
        current["cols"] = [str(c) for c in float32_cols if str(c) in set(table.column_names)]
        current["path"] = str(output_path)
        try:
            return real_writer(table, output_path, float32_cols=float32_cols, **kwargs)
        finally:
            current.clear()

    real_bss = fs_mod._is_bss_unsupported_error

    def bss_spy(error: Exception) -> bool:
        hit = bool(real_bss(error))
        if hit:
            for col in current.get("cols", []):
                obs.raw_fallbacks.append({"column": col, "reason": f"bss_unsupported:{error}", "file": current.get("path")})
        return hit

    stack.enter_context(_patched(fs_mod, "_write_parquet_with_codec", writer_spy))
    stack.enter_context(_patched(fs_mod, "_is_bss_unsupported_error", bss_spy))

    real_infer = fs_mod.FeatureStorage.__dict__["_infer_l7_processed_encoding"]
    proc_current: Dict[str, Any] = {}

    def infer_spy(cls: Any, column_name: str) -> Any:
        out = real_infer.__func__(cls, column_name)
        proc_current["column"] = str(column_name)
        if out[0] == fs_mod.RANK_UINT16_ENCODING and (out[1] is None or out[1] <= 0):
            obs.processed_fallbacks.append({"column": str(column_name), "reason": "invalid_rank_window"})
        return out

    stack.enter_context(_patched(fs_mod.FeatureStorage, "_infer_l7_processed_encoding", classmethod(infer_spy)))
    for fn_name in ("encode_rank_as_uint16", "encode_zscore_as_int16", "encode_gaussian_as_int16"):
        if not hasattr(fs_mod, fn_name):
            continue
        real_fn = getattr(fs_mod, fn_name)

        def enc_spy(*args: Any, _real: Callable = real_fn, **kwargs: Any) -> Any:
            try:
                return _real(*args, **kwargs)
            except fs_mod.EncodeFallbackRequired as exc:
                obs.processed_fallbacks.append({"column": proc_current.get("column"), "reason": str(exc)})
                raise

        stack.enter_context(_patched(fs_mod, fn_name, enc_spy))
    for meth in ("_assert_rank_roundtrip", "_assert_zscore_roundtrip", "_assert_gaussian_roundtrip"):
        if meth not in fs_mod.FeatureStorage.__dict__:
            continue
        real_m = fs_mod.FeatureStorage.__dict__[meth]
        func = real_m.__func__ if isinstance(real_m, (staticmethod, classmethod)) else real_m

        def assert_spy(*args: Any, _func: Callable = func, _kind: Any = type(real_m), **kwargs: Any) -> Any:
            try:
                return _func(*args, **kwargs)
            except fs_mod.EncodeFallbackRequired as exc:
                obs.processed_fallbacks.append({"column": proc_current.get("column"), "reason": str(exc)})
                raise

        wrapped = staticmethod(assert_spy) if isinstance(real_m, staticmethod) else (
            classmethod(assert_spy) if isinstance(real_m, classmethod) else assert_spy)
        stack.enter_context(_patched(fs_mod.FeatureStorage, meth, wrapped))

    # IC：生產呼叫之參數與結果（S5 重演之來源）、讀入 dtype
    real_ic = ICEngine.compute_ic_from_l7_raw

    def ic_spy(self: Any, symbol: str, tf: str, config_hash: str, label: Any, **kwargs: Any) -> Any:
        result = real_ic(self, symbol, tf, config_hash, label, **kwargs)
        threshold = kwargs.get("ic_threshold")
        obs.ic_calls.append({"label": label, "method": kwargs.get("method") or (self._methods[0] if self._methods
                                                                                 else "spearman"),
                             "threshold": float(threshold if threshold is not None
                                                else self._config.get("ic_threshold", 0.02)),
                             "selection_window": kwargs.get("selection_window"), "engine_config": dict(self._config),
                             "ic_scores": dict(result.ic_scores), "selected": list(result.selected)})
        return result

    real_group_ic = ICEngine._compute_l7_raw_group_ic

    def group_ic_spy(self: Any, group_df: Any, label: Any, method: str, selection_window: Any) -> Any:
        obs.ic_input_dtypes.update(str(t) for t in group_df.dtypes)
        return real_group_ic(self, group_df, label, method, selection_window)

    stack.enter_context(_patched(ICEngine, "compute_ic_from_l7_raw", ic_spy))
    stack.enter_context(_patched(ICEngine, "_compute_l7_raw_group_ic", group_ic_spy))
    with stack:
        yield


@contextlib.contextmanager
def install_variant(spec: Mapping[str, Any], obs: Observer) -> Iterator[None]:
    """變體專屬之改值：L2 Polars 臂抬升（只限 `compute_all_polars` 呼叫範圍）、`winsor_sigma_dtype` 之自建分岔。"""
    from momentum.FeatureEngineering import polars_adapter
    from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine

    stack = contextlib.ExitStack()
    real_cap = DerivedOperatorEngine.compute_all_polars

    def cap_spy(self: Any, *args: Any, **kwargs: Any) -> Any:
        if not spec.get("lift_l2"):
            out = real_cap(self, *args, **kwargs)
        else:
            real_p2p, real_p2pd = polars_adapter.pandas_to_polars, polars_adapter.polars_to_pandas

            def p2p(df: Any, *, use_float64: bool = False) -> Any:
                obs.l2_lift_calls += 1
                return real_p2p(df, use_float64=True)

            def p2pd(pl_df: Any, index: Any = None) -> Any:
                import pandas as pd

                if pl_df.is_empty():
                    frame = pd.DataFrame(columns=pl_df.columns, dtype=np.float64)
                else:
                    frame = pd.DataFrame(data=pl_df.fill_null(float("nan")).to_numpy(), columns=pl_df.columns, copy=False)
                if index is not None:
                    frame.index = index
                return frame

            polars_adapter.pandas_to_polars, polars_adapter.polars_to_pandas = p2p, p2pd
            try:
                out = real_cap(self, *args, **kwargs)
            finally:
                polars_adapter.pandas_to_polars, polars_adapter.polars_to_pandas = real_p2p, real_p2pd
        if out is not None and hasattr(out, "dtypes"):
            obs.l2_return_dtypes.update(str(t) for t in out.dtypes)
        return out

    stack.enter_context(_patched(DerivedOperatorEngine, "compute_all_polars", cap_spy))
    if spec.get("winsor_fork"):
        stack.enter_context(_install_winsor_fork(obs))
    with stack:
        yield


@contextlib.contextmanager
def _install_winsor_fork(obs: Observer) -> Iterator[None]:
    """SPEC v37 細則⑥：包 `_transform_single_legacy`；sigma 縮尾且平穩化開之群組，另以同建構參數新建兩實例分別算
    float64 支（`_winsorize_2d_legacy_equivalent`，sigma 回 float64）與 float32 支（`_apply_winsorization`，生產），各接
    fracdiff／ADF；float32 支須與生產輸出逐位元相等（新實例保真），否則該群組標 `fresh_instance_mismatch`。"""
    import pandas as pd

    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    real_legacy = FeaturePreprocessor._transform_single_legacy
    tmp = obs.capture.root / "dstar_fork"
    tmp.mkdir(parents=True, exist_ok=True)

    def fresh(self: Any) -> Any:
        args = obs.preprocessor_args.get(id(self))
        if args is None:
            return None
        inst = FeaturePreprocessor(*args)
        inst._d_star_cache_dir = lambda: tmp  # 實例屬性遮蔽 staticmethod：d* 快取導向暫存（不寫入該 run）
        inst._inherit_calibration(self)  # 生產碼子實例共用校準狀態之同一入口（feature_preprocessor.py:268）
        return inst

    def stationary_chain(inst: Any, owner: Any, frame: Any, source_layer: Any, winsor: Callable[[Any], Any]) -> Any:
        with inst._decision_context(frame.columns, source_timeframe=getattr(owner._decision_tls, "timeframe", None),
                                    source_layer=source_layer):
            out = winsor(frame)
            if inst.fracdiff_config.get("enabled", False):
                out = inst._apply_fractional_differencing(out, source_layer=source_layer)
            if inst.adf_config.get("enabled", False):
                out = inst._apply_adf_differencing(out)
        return out

    def legacy_spy(self: Any, features_df: Any, source_layer: Optional[str] = None) -> Any:
        result = real_legacy(self, features_df, source_layer)
        sigma = str(self.winsor_config.get("method", "quantile")) == "sigma" and self.winsor_config.get("enabled", True)
        if not sigma or not (self.fracdiff_config.get("enabled") or self.adf_config.get("enabled")):
            return result
        p64, p32 = fresh(self), fresh(self)
        if p64 is None or p32 is None:
            obs.winsor_fork.append({"columns": [str(c) for c in features_df.columns], "status": "no_constructor_args"})
            return result
        cols = p64._select_columns(features_df, p64.winsor_config.get("apply_to", "all"))

        def win64(frame: Any) -> Any:
            out = frame.copy()
            if cols:
                out[cols] = pd.DataFrame(p64._winsorize_2d_legacy_equivalent(frame[cols].to_numpy(dtype=np.float64)),
                                         index=frame.index, columns=cols)
            return out

        side64 = stationary_chain(p64, self, features_df.copy(), source_layer, win64)
        side32 = stationary_chain(p32, self, features_df.copy(), source_layer, p32._apply_winsorization)
        same_cols = [c for c in result.columns if c in side32.columns]
        fidelity = all(_bitwise(result[c].to_numpy(), side32[c].to_numpy()) for c in same_cols)
        d64, d32 = p64.stationarity_decisions(), p32.stationarity_decisions()
        decision_changes = sorted({str(k[0]) if isinstance(k, tuple) else str(k) for k in set(d64) | set(d32)
                                   if _decision_core(d64.get(k)) != _decision_core(d32.get(k))})
        key = f"fork:{len(obs.winsor_fork)}"
        common = [c for c in side64.columns if c in side32.columns]
        ep = _time_axis(obs, side64.index)
        if ep is None:
            obs.winsor_fork.append({"key": key, "columns": common, "status": "unindexed",
                                    "rows": int(len(side64.index))})
            return result
        obs.capture.save("FORK64", key, common, side64[common].to_numpy(dtype=np.float64), ep)
        obs.capture.save("FORK32", key, common, side32[common].to_numpy(dtype=np.float64), ep)
        obs.winsor_fork.append({"key": key, "columns": common, "fresh_instance_fidelity": bool(fidelity),
                                "decision_changed_columns": decision_changes,
                                "status": "measured" if fidelity else "fresh_instance_mismatch"})
        return result

    with _patched(FeaturePreprocessor, "_transform_single_legacy", legacy_spy):
        yield


def _decision_core(record: Optional[Mapping[str, Any]]) -> Any:
    if record is None:
        return None
    return tuple(record.get(k) for k in ("fracdiff", "d", "adf_differenced", "dstar_source"))


def _bitwise(a: np.ndarray, b: np.ndarray) -> bool:
    """原生逐位元相等（同 dtype、同形狀、NaN 遮罩相同、非 NaN 格之原生位元組相同；`preprov_helpers.bitwise_equal`
    同義）。呼叫端須以原生 dtype 傳入；跨 dtype 一律不等（審碼 r8：不得先轉 float64 再比）。"""
    a, b = np.asarray(a), np.asarray(b)
    if a.dtype != b.dtype or a.shape != b.shape:
        return False
    na, nb = np.isnan(a), np.isnan(b)
    if not np.array_equal(na, nb):
        return False
    return a[~na].tobytes() == b[~nb].tobytes()


# ============================================================================================== 生成單元


def _truncated_end(cell: Mapping[str, Any], offset: int) -> str:
    """同起點、終點提前 `offset` 根（主週期來源序列之第 −1−offset 根）之 ISO 時間戳（SPEC v37 細則③）。"""
    import h5py
    import pandas as pd

    est = _estimate()
    source = est.cell_source(cell, _criteria())
    with h5py.File(str(source), "r") as handle:
        stamps = handle[str(cell["symbol"])][str(cell["timeframes"][0])]["data"]["timestamp"]
        last = int(stamps[-1 - int(offset)])
    unit = "ms" if last > 10 ** 12 else "s"
    return pd.Timestamp(last, unit=unit, tz="UTC").isoformat()


@contextlib.contextmanager
def variant_generation_context(cell: Mapping[str, Any], spec: Mapping[str, Any]) -> Iterator[None]:
    """變體之生成設定覆寫（輸出段終點、設定覆寫）：替換估時器之 `cell_window`／`cell_payload`（凍結腳本經同一模組物件
    讀取），生成與身分重算共用（SPEC v37：`generation_inputs(cell)` 併入變體生成設定）。"""
    est = _estimate()
    real_window, real_payload = est.cell_window, est.cell_payload
    offset = int(spec.get("end_offset_bars") or 0)
    override = spec.get("override")

    def window(c: Mapping[str, Any], criteria: Mapping[str, Any]) -> Tuple[str, str]:
        start, end = real_window(c, criteria)
        return (start, _truncated_end(c, offset)) if offset and str(c["id"]) == str(cell["id"]) else (start, end)

    def payload(c: Mapping[str, Any], criteria: Mapping[str, Any], training: Any = None) -> Any:
        base = real_payload(c, criteria, training)
        return _deep_merge(base, override) if override and str(c["id"]) == str(cell["id"]) else base

    est.cell_window, est.cell_payload = window, payload
    try:
        yield
    finally:
        est.cell_window, est.cell_payload = real_window, real_payload


def variant_generation_inputs(source_run: str) -> Dict[str, Any]:
    """`source_run` 之生成輸入（凍結腳本 `generation_inputs(cell)` 於變體生成設定下）；`freeze_*` 為凍結格本身。"""
    if source_run in RUN_SPECS:
        spec = RUN_SPECS[source_run]
        cell = _cell(spec["cell"])
        with variant_generation_context(cell, spec):
            return _freeze().generation_inputs(cell)
    cell_id = next(c for c, name in FREEZE_RUN_NAMES.items() if name == source_run)
    return _freeze().generation_inputs(_cell(cell_id))


def _sha256_json(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")).hexdigest()


def run_identity(source_run: str, cell: Mapping[str, Any], run_dir: Path) -> Dict[str, Any]:
    """身分表一鍵（SPEC v37 驗證段）：格、變體、manifest sha256、生成輸入 sha256、資料集、產品碼態、接縫碼態。"""
    from tests.feature_engineering import numview_helpers as nh

    return {"cell_id": str(cell["id"]), "variant": source_run, "run_dir": str(Path(run_dir).relative_to(REPO)),
            "feature_manifest_sha256": hashlib.sha256((Path(run_dir) / "feature_manifest.json").read_bytes()).hexdigest(),
            "generation_inputs_sha256": _sha256_json(variant_generation_inputs(source_run)),
            "datasets": nh.cell_dataset_records(cell), "code_state_sha256": nh.code_state_sha256(),
            "seam_state_sha256": nh.seam_state_sha256()}


def frozen_identity(name: str, cell_id: str) -> Dict[str, Any]:
    """凍結 run 之身分＝凍結收據 `identity.<格>`（凍結當時之產品碼態、接縫碼態、資料集、生成輸入）＋現存 run 目錄之
    manifest sha256（不以現行碼重算凍結 run 之身分）。"""
    hits = sorted(RECEIPTS_DIR.glob("*-numview-freeze-baseline.json"))
    if len(hits) != 1:
        raise RuntimeError(f"凍結收據須恰一份，實得 {[p.name for p in hits]}")
    ident = json.loads(hits[0].read_text(encoding="utf-8"))["identity"][cell_id]
    run_dir = _freeze_run_dir(cell_id)
    return {"cell_id": cell_id, "variant": name, "run_dir": str(run_dir.relative_to(REPO)),
            "feature_manifest_sha256": hashlib.sha256((run_dir / "feature_manifest.json").read_bytes()).hexdigest(),
            "generation_inputs_sha256": ident["generation_inputs_sha256"], "datasets": ident["datasets"],
            "code_state_sha256": ident["code_state_sha256"], "seam_state_sha256": ident["seam_state_sha256"],
            "identity_source": hits[0].name}


def _run_dir(work: Path, side: Mapping[str, Any]) -> Path:
    return Path(work) / "features" / str(side["symbol"]) / str(side["primary_tf"]) / str(side["config_hash"])


def run_generation_unit(source_run: str, work: Path, capture_dir: Path) -> Dict[str, Any]:
    """一次變體重生（子行程內）：掛 spy、於變體生成設定下以凍結腳本同一程序生成，寫擷取並回觀測與身分。"""
    spec = RUN_SPECS[source_run]
    cell = _cell(spec["cell"])
    est = _estimate()
    with variant_generation_context(cell, spec):
        start, end = est.cell_window(cell, _criteria())
    import pandas as pd

    capture = Capture(capture_dir, int(pd.Timestamp(start).timestamp()), int(pd.Timestamp(end).timestamp()))
    obs = Observer(capture, spec)
    if Path(work).exists():
        shutil.rmtree(work)
    started = time.perf_counter()
    with variant_generation_context(cell, spec), install_spies(obs), install_variant(spec, obs):
        side = _freeze().generate_cell_run(Path(work), cell, dict(spec["env"]))
    seconds = time.perf_counter() - started
    run_dir = _run_dir(work, side)
    if obs.ic_calls:
        with open(capture.root / "ic.pkl", "wb") as handle:
            pickle.dump(obs.ic_calls[-1], handle)
    capture.write_meta({"source_run": source_run, "window": [start, end]})
    return {"source_run": source_run, "cell_id": str(cell["id"]), "status": str(side.get("status")),
            "seconds": seconds, "work": str(work), "run_dir": str(run_dir), "capture_dir": str(capture.root),
            "window": [start, end], "identity": run_identity(source_run, cell, run_dir),
            "observed_settings": obs.settings(), "layer4_merge": obs.layer4_merge, "winsor_fork": obs.winsor_fork,
            "raw_fallbacks": obs.raw_fallbacks, "processed_fallbacks": obs.processed_fallbacks,
            "ic_input_dtypes": sorted(obs.ic_input_dtypes), "ic_called": bool(obs.ic_calls)}


def settings_violations(source_run: str, observed: Mapping[str, Any], window_end: str) -> List[str]:
    """`observed_settings` 對 `VARIANT_SETTINGS` 逐鍵（SPEC v37 驗證段；`end_offset_bars` 換成期望 `end_date`）。"""
    expected = VARIANT_SETTINGS[source_run]
    out: List[str] = []
    for key, want in expected.items():
        if key == "end_offset_bars":
            ends = list(observed.get("end_dates") or [])
            if ends != [window_end]:
                out.append(f"{source_run}.end_date：觀測 {ends} ≠ 期望 [{window_end}]")
            continue
        if observed.get(key) != want:
            out.append(f"{source_run}.{key}：觀測 {observed.get(key)!r} ≠ 期望 {want!r}")
    if RUN_SPECS[source_run].get("cell") == B_CELL:
        tfs = _cell(B_CELL)["timeframes"]
        captured = observed.get("captured_timeframes") or {}
        for tf in tfs:
            if not {"S0", "S1"} <= set(captured.get(tf) or []):
                out.append(f"{source_run}：訓練週期 {tf} 缺主行程 S0／S1 擷取（{captured.get(tf)}）")
    return out


# ============================================================================================== 讀回


def readback_raw(run_dir: Path) -> Tuple[Dict[str, np.ndarray], Dict[str, str], np.ndarray]:
    """run 之 raw 落盤讀回：{欄: 原生 dtype 值}、{欄: 群組檔相對路徑}、時間戳（epoch 秒）。"""
    import pyarrow.parquet as pq

    from tests.feature_engineering import preprov_helpers as ph

    values: Dict[str, np.ndarray] = {}
    groups: Dict[str, str] = {}
    for path in ph.declared_group_files(Path(run_dir), "raw"):
        table = pq.read_table(str(path))
        rel = str(Path(path).resolve().relative_to(Path(run_dir).resolve()))
        for name in table.column_names:
            if name in ph.NON_FEATURE_COLUMNS:
                continue
            values[str(name)] = np.asarray(table.column(name).to_numpy(zero_copy_only=False))
            groups[str(name)] = rel
    ts = pq.read_table(str(Path(run_dir) / "timestamps.parquet")).column("timestamp").to_numpy().astype(np.int64)
    if ts.size and int(ts.max()) > 10 ** 12:
        ts = ts // 1000
    return values, groups, ts


def readback_processed(run_dir: Path, side: Mapping[str, Any]) -> Dict[str, np.ndarray]:
    """processed 讀回（經 `FeatureReader.load_columns_v2` 解碼有損編碼）。"""
    import pyarrow.parquet as pq

    from momentum.FeatureEngineering.feature_reader import FeatureReader

    path = Path(run_dir) / "processed" / "selected.parquet"
    if not path.is_file():
        return {}
    names = [n for n in pq.read_schema(str(path)).names]
    root = Path(run_dir).parents[2]
    frame = FeatureReader(str(root)).load_columns_v2(str(side["symbol"]), str(side["primary_tf"]),
                                                     str(side["config_hash"]), names, artifact_kind="processed")
    return {str(c): frame[c].to_numpy() for c in frame.columns}


# ============================================================================================== S5 重演


def replay_ic(context: Mapping[str, Any], values: Mapping[str, np.ndarray], epochs: np.ndarray) -> Tuple[Dict[str, float], set]:
    """逐群組重演生產選欄（SPEC v36 S5）：附時間軸後呼叫 `ICEngine._compute_l7_raw_group_ic`（數值欄篩選、標籤對齊、選窗、
    IC），合併後 `_passes_ic_threshold`；`context`＝生產呼叫之 spy 紀錄（標籤、方法、門檻、選窗、引擎設定）。"""
    import pandas as pd

    from momentum.Analysis.ic_engine import ICEngine

    engine = ICEngine(dict(context["engine_config"]))
    index = pd.to_datetime(np.asarray(epochs, dtype=np.int64), unit="s", utc=True)
    label = context["label"]
    if getattr(label.index, "tz", None) is None:
        index = index.tz_localize(None)
    scores: Dict[str, float] = {}
    cols = list(values)
    for i in range(0, len(cols), 256):
        chunk = cols[i:i + 256]
        frame = pd.DataFrame({c: values[c] for c in chunk}, index=index)
        scores.update({str(k): float(v) for k, v in engine._compute_l7_raw_group_ic(
            frame, label, str(context["method"]), context.get("selection_window")).items()})
    selected = {c for c, v in scores.items() if engine._passes_ic_threshold(v, float(context["threshold"]))}
    return scores, selected


def _sign_flip(a: Optional[float], b: Optional[float]) -> bool:
    if a is None or b is None or not np.isfinite(a) or not np.isfinite(b):
        return (a is None or not np.isfinite(a)) != (b is None or not np.isfinite(b))
    return bool(np.sign(a) != np.sign(b))


# ============================================================================================== 比對


def _seg_values(capture_dir: Path, segment: str) -> Dict[str, Tuple[np.ndarray, Optional[np.ndarray], str]]:
    return capture_columns(Path(capture_dir), segment) if capture_dir else {}


def _align(values: np.ndarray, epochs: Optional[np.ndarray], target: np.ndarray) -> Optional[np.ndarray]:
    """依時間戳取 `target` 列；無時間戳者須列數相同（S2 sink 輸入列序＝落盤列序）。"""
    if epochs is None:
        return values if len(values) == len(target) else None
    pos = {int(e): i for i, e in enumerate(np.asarray(epochs))}
    idx = [pos.get(int(t)) for t in target]
    if any(i is None for i in idx):
        return None
    return np.asarray(values)[np.asarray(idx, dtype=np.int64)]


def column_rows(segment: str, cell_id: str, variant: Mapping[str, np.ndarray], reference: Mapping[str, np.ndarray],
                *, ic_v: Optional[Mapping[str, float]] = None, ic_r: Optional[Mapping[str, float]] = None,
                sel_v: Optional[set] = None, sel_r: Optional[set] = None, source_run: str, reference_run: str,
                extra: Optional[Mapping[str, Mapping[str, Any]]] = None) -> List[Dict[str, Any]]:
    """逐欄列：統計（`checkpoint_stats`）＋`material`（NaN 遮罩差 > 0 或該欄 IC 正負號翻轉；SPEC v37 細則②）＋
    `survivor_set_change`（該欄是否進出倖存者集合）。缺參照之欄列 `status=no_reference`。"""
    rows: List[Dict[str, Any]] = []
    for col in variant:
        base = {"segment": segment, "cell_id": cell_id, "column": col, "source_run": source_run,
                "reference_run": reference_run}
        if col not in reference:
            rows.append({**base, "status": "no_reference", "max_abs": None, "max_rel": None, "nan_mask_diff": None,
                         "all_nan": None, "float16_ok": None, "material": None, "survivor_set_change": None})
            continue
        stats = checkpoint_stats(variant[col], reference[col])
        flip = _sign_flip(ic_v.get(col), ic_r.get(col)) if ic_v is not None and ic_r is not None else False
        survivor = (col in sel_v) != (col in sel_r) if sel_v is not None and sel_r is not None else None
        row = {**base, "status": "measured", **stats, "ic_sign_flip": flip if ic_v is not None else None,
               "survivor_set_change": survivor,
               "material": bool(stats["nan_mask_diff"]) or bool(flip) or bool(survivor)}
        if extra and col in extra:
            row.update(extra[col])
        rows.append(row)
    return rows


def group_rows(rows: Sequence[Mapping[str, Any]], groups: Mapping[str, str], segment: str, cell_id: str,
               source_run: str, reference_run: str) -> List[Dict[str, Any]]:
    """逐欄列 ⇒ 群組列（SPEC v37 細則①聚合語意）。"""
    by: Dict[str, List[Mapping[str, Any]]] = {}
    for r in rows:
        by.setdefault(groups.get(str(r["column"]), "?"), []).append(r)
    out = []
    for g, members in sorted(by.items()):
        measured = [m for m in members if m.get("status") == "measured"]
        explained = [m for m in members if m.get("status") == "dropped_in_reference"]  # provenance 已解釋之剔除欄
        agg = aggregate_group(measured) if measured else {"columns_in_group": 0}
        # 審碼 r9：群組內任一欄缺參照（且未經 provenance 解釋）即非 measured（不得以同群其他欄掩蓋丟欄）
        missing = len(members) - len(measured) - len(explained)
        status = "measured" if missing == 0 and measured else ("partial_no_reference" if measured else "no_reference")
        out.append({"segment": segment, "cell_id": cell_id, "group": g, "source_run": source_run,
                    "reference_run": reference_run, "status": status,
                    **agg, "columns_in_group": len(members),
                    "no_reference_columns": missing, "dropped_in_reference_columns": len(explained)})
    return out


def _status_rows(segment: str, cell_id: str, columns: Sequence[str], status: str, reason: str,
                 source_run: Optional[str] = None) -> List[Dict[str, Any]]:
    return [{"segment": segment, "cell_id": cell_id, "column": str(c), "status": status, "reason": reason,
             "max_abs": None, "max_rel": None, "nan_mask_diff": None, "all_nan": None, "float16_ok": None,
             "material": None, "survivor_set_change": None, "source_run": source_run} for c in columns]


def unindexed_groups(capture_dir: Optional[str]) -> List[str]:
    """擷取中對不上時間軸之 registry 群組（`S1_unindexed`）；非空即該 run 之 S0／S1 擷取不完整（審碼 r8：fail-closed）。"""
    if not capture_dir or not (Path(capture_dir) / "capture.json").is_file():
        return []
    return sorted(str(e["key"]) for e in load_capture(Path(capture_dir))["entries"] if e["segment"] == "S1_unindexed")


def _load_ic(capture_dir: Optional[str]) -> Optional[Dict[str, Any]]:
    if not capture_dir or not (Path(capture_dir) / "ic.pkl").is_file():
        return None
    with open(Path(capture_dir) / "ic.pkl", "rb") as handle:
        return pickle.load(handle)


def _cols_at(seg: Mapping[str, Tuple[np.ndarray, Optional[np.ndarray], str]], target: np.ndarray) -> Dict[str, np.ndarray]:
    out: Dict[str, np.ndarray] = {}
    for col, (vals, ep, _) in seg.items():
        got = _align(vals, ep, target)
        if got is not None:
            out[col] = got
    return out


def _s5_row(cell_id: str, checkpoint: str, sel_r: set, sel_v: set, ic_r: Mapping[str, float], ic_v: Mapping[str, float],
            source_run: str, reference_run: str) -> Dict[str, Any]:
    flips = sum(1 for c in ic_v if c in ic_r and _sign_flip(ic_v[c], ic_r[c]))
    entered, exited = sorted(sel_v - sel_r), sorted(sel_r - sel_v)
    return {"segment": "S5", "cell_id": cell_id, "column": checkpoint, "status": "measured", "source_run": source_run,
            "reference_run": reference_run, "survivors_reference": len(sel_r), "survivors_variant": len(sel_v),
            "entered": entered[:50], "exited": exited[:50], "entered_count": len(entered), "exited_count": len(exited),
            "sign_flips": flips, "survivor_set_change": bool(entered or exited),
            "material": bool(entered or exited or flips), "max_abs": None, "max_rel": None}


def compare_a(results: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    """格 A（HOST_CELL）：R＝`s0_float64_chain`、P＝`codec_upgrade_on`＋凍結讀回；分岔 memmap／winsor；codec；延伸。"""
    from tests.feature_engineering import numview_helpers as nh

    cid = HOST_CELL
    out: Dict[str, Any] = {"rows": [], "forks": [], "codec_checks": [], "extension": [], "s4_raw_bss": [],
                           "codec_fallbacks": [], "processed_codec": [], "checks": {}, "notes": []}
    R, P = results.get("s0_float64_chain"), results.get("codec_upgrade_on")
    frozen_dir = _freeze_run_dir(cid)
    frozen_vals, frozen_groups, frozen_ts = readback_raw(frozen_dir)
    ic_ctx = _load_ic(P["capture_dir"]) if P else None
    # 生產等價（SPEC v37：觀測設定＋raw 讀回對凍結逐位元）與 S4 raw BSS（同一比對）
    p_equiv = False
    if P:
        p_vals, _, p_ts = readback_raw(Path(P["run_dir"]))
        bss = {c: _bitwise(p_vals[c], frozen_vals[c]) for c in frozen_vals if c in p_vals}
        missing = sorted(set(frozen_vals) ^ set(p_vals))
        bss_ok = all(bss.values()) and not missing and np.array_equal(p_ts, frozen_ts)
        out["s4_raw_bss"].append({"cell_id": cid, "bitwise_equal": bool(bss_ok), "status": "measured",
                                  "non_bitwise_columns": sorted(c for c, ok in bss.items() if not ok)[:50],
                                  "column_set_mismatch": missing[:50]})
        p_equiv = bool(bss_ok) and not P.get("settings_violations") and P.get("status") == "complete"  # 審碼 r13
        out["checks"]["a_production_equivalent"] = p_equiv
        for c in frozen_vals:
            if c in p_vals:
                st = checkpoint_stats(p_vals[c].astype(np.float64), frozen_vals[c].astype(np.float64))
                out["rows"].append({"segment": "S4", "cell_id": cid, "column": c, "status": "measured",
                                    "source_run": "codec_upgrade_on", "reference_run": "freeze_A", **st,
                                    "bitwise_equal": bool(bss.get(c)), "material": bool(st["nan_mask_diff"]),
                                    "survivor_set_change": None})
        for fb in P.get("raw_fallbacks", []) + P.get("processed_fallbacks", []):
            out["codec_fallbacks"].append({"cell_id": cid, **fb})
        frozen_side = json.loads((FREEZE_RUNS / f"{cid}__default" / "numview_cell.json").read_text(encoding="utf-8"))
        p_side = {"symbol": frozen_side["symbol"], "primary_tf": frozen_side["primary_tf"],
                  "config_hash": Path(P["run_dir"]).name}
        p_proc, f_proc = readback_processed(Path(P["run_dir"]), p_side), readback_processed(frozen_dir, frozen_side)
        for c in f_proc:
            if c in p_proc:
                out["processed_codec"].append({"cell_id": cid, "column": c, **checkpoint_stats(p_proc[c], f_proc[c])})
        # processed 欄集合須相等（審碼 r8：只對交集出列會使整組缺欄無失敗信號）
        out["checks"]["processed_columns_equal"] = bool(f_proc) and set(p_proc) == set(f_proc)
        out["processed_column_mismatch"] = sorted(set(p_proc) ^ set(f_proc))[:50]
    else:
        out["s4_raw_bss"].append({"cell_id": cid, "bitwise_equal": False, "status": "blocked"})
    out["lossless_violation"] = not all(e["bitwise_equal"] for e in out["s4_raw_bss"] if e["status"] == "measured")
    # 名稱推斷誤判（凍結 processed 轉換紀錄 vs `_infer_l7_processed_encoding`）
    out["codec_checks"].append({"check": "name_inference", "cell_id": cid,
                                "nonconforming_columns": name_inference_mismatches(frozen_dir)})
    out["codec_checks"].append({"check": "raw_bss_lossless", "cell_id": cid,
                                "nonconforming_columns": len(out["s4_raw_bss"][0].get("non_bitwise_columns") or [])
                                if out["s4_raw_bss"][0]["status"] == "measured" else None})
    # S0–S3、S5（R 對 P）
    unindexed = {n: unindexed_groups(x["capture_dir"]) for n, x in (("s0_float64_chain", R), ("codec_upgrade_on", P)) if x}
    out["checks"]["s1_all_indexed"] = not any(unindexed.values())
    out["unindexed_groups"] = unindexed
    if R and P and p_equiv and ic_ctx is not None and not any(unindexed.values()):
        r0, r1, r2 = (_cols_at(_seg_values(R["capture_dir"], s), frozen_ts) for s in ("S0", "S1", "S2"))
        p1, p2 = (_cols_at(_seg_values(P["capture_dir"], s), frozen_ts) for s in ("S1", "S2"))
        r_vals, _, r_ts = readback_raw(Path(R["run_dir"]))
        if not np.array_equal(r_ts, frozen_ts):
            out["notes"].append("R 讀回時間軸 ≠ 凍結 A")
        ic = {}
        for name, vals in (("R0", r0), ("R1", r1), ("P1", p1), ("R2", r2), ("P2", p2), ("R3", r_vals), ("P3", frozen_vals)):
            ic[name] = replay_ic(ic_ctx, vals, frozen_ts)
        r0_dtypes = capture_dtypes(Path(R["capture_dir"]), "S0")
        s0_extra = {c: {"s0_dtype": r0_dtypes.get(c)} for c in r0}
        out["s0_incomplete"] = {"cell_id": cid, "source_run": "s0_float64_chain",
                                "non_float64_columns": sum(1 for c in r0 if r0_dtypes.get(c) != "float64"),
                                "columns": len(r0), "dtypes": sorted({str(r0_dtypes.get(c)) for c in r0})}
        out["rows"] += column_rows("S0", cid, r1, r0, ic_v=ic["R1"][0], ic_r=ic["R0"][0], sel_v=ic["R1"][1],
                                   sel_r=ic["R0"][1], source_run="s0_float64_chain", reference_run="s0_float64_chain",
                                   extra=s0_extra)
        out["rows"] += column_rows("S1", cid, p1, r0, ic_v=ic["P1"][0], ic_r=ic["R0"][0], sel_v=ic["P1"][1],
                                   sel_r=ic["R0"][1], source_run="codec_upgrade_on", reference_run="s0_float64_chain",
                                   extra=s0_extra)
        out["rows"] += column_rows("S2", cid, p2, r2, ic_v=ic["P2"][0], ic_r=ic["R2"][0], sel_v=ic["P2"][1],
                                   sel_r=ic["R2"][1], source_run="codec_upgrade_on", reference_run="s0_float64_chain")
        # 期望欄集合取自擷取紀錄本身（非對齊後之集合）：對齊失敗而丟之欄於完整性檢查現形
        # 期望欄集合＝凍結 run 落盤之欄集合（獨立於擷取；審碼 r11：擷取缺欄不得同時縮小期望）
        out["columns_by_segment"] = {seg: sorted(frozen_vals) for seg in ("S0", "S1", "S2", "S3", "S4")}
        storage = {c: {f"storage_only_{k}": v for k, v in checkpoint_stats(frozen_vals[c], p2[c]).items()}
                   for c in frozen_vals if c in p2}
        out["rows"] += column_rows("S3", cid, frozen_vals, r_vals, ic_v=ic["P3"][0], ic_r=ic["R3"][0],
                                   sel_v=ic["P3"][1], sel_r=ic["R3"][1], source_run="freeze_A",
                                   reference_run="s0_float64_chain", extra=storage)
        for chk, (a, b) in (("S1", ("R0", "P1")), ("S2", ("R2", "P2")), ("S3", ("R3", "P3"))):
            out["rows"].append(_s5_row(cid, chk, ic[a][1], ic[b][1], ic[a][0], ic[b][0],
                                       "codec_upgrade_on" if chk != "S3" else "freeze_A", "s0_float64_chain"))
        # S5 重演 oracle：凍結讀回之重演 ic_scores ＝凍結 json
        frozen_json = json.loads(next(frozen_dir.glob("ic_selected_features_*.json")).read_text(encoding="utf-8"))
        want = {str(k): (np.nan if v is None else float(v)) for k, v in (frozen_json.get("ic_scores") or {}).items()}
        got = ic["P3"][0]
        oracle = set(want) == set(got) and all((np.isnan(want[k]) and np.isnan(got[k])) or want[k] == got[k] for k in want)
        oracle = oracle and sorted(frozen_json.get("selected") or []) == sorted(ic["P3"][1])
        out["checks"]["s5_replay_oracle"] = bool(oracle)
        # 審碼 r12：重演亦須等於同次生產呼叫（P run 之 `compute_ic_from_l7_raw` spy 紀錄）之 ic_scores 與倖存者
        prod = {str(k): (np.nan if v is None else float(v)) for k, v in (ic_ctx.get("ic_scores") or {}).items()}
        same_run = set(prod) == set(got) and all((np.isnan(prod[k]) and np.isnan(got[k])) or prod[k] == got[k] for k in prod)
        out["checks"]["s5_replay_matches_production_run"] = bool(
            same_run and sorted(str(s) for s in ic_ctx.get("selected") or []) == sorted(ic["P3"][1]))
        oracle = oracle and out["checks"]["s5_replay_matches_production_run"]
        if not oracle:
            out["rows"] = [r for r in out["rows"] if r["segment"] != "S5"]
            out["rows"].append({"segment": "S5", "cell_id": cid, "column": "*", "status": "blocked",
                                "reason": "重演 oracle 不等（凍結讀回之重演 ic_scores ≠ 凍結 json）", "max_abs": None,
                                "max_rel": None})
    else:
        reason = "生產等價不成立或缺 R／P／IC 紀錄"
        for seg in ("S0", "S1", "S2", "S3"):
            out["rows"] += _status_rows(seg, cid, sorted(frozen_vals), "blocked", reason)
        out["rows"].append({"segment": "S5", "cell_id": cid, "column": "*", "status": "blocked", "reason": reason,
                            "max_abs": None, "max_rel": None})
    out["forks"] += fork_memmap(results, ic_ctx, frozen_ts)
    out["forks"] += fork_winsor(results.get("winsor_sigma_dtype"), ic_ctx, frozen_ts)
    out["extension"].append(extension_entry(results.get("tail_extension"), frozen_dir))
    out["columns"] = sorted(frozen_vals)
    return out


def raw_provenance_terminals(run_dir: Path) -> Dict[str, str]:
    """run 之 raw provenance（`provenance/raw_columns.parquet`）逐欄 terminal（written／dead_dropped／ratio_unsafe 等）。"""
    import pyarrow.parquet as pq

    path = Path(run_dir) / "provenance" / "raw_columns.parquet"
    if not path.is_file():
        return {}
    table = pq.read_table(str(path), columns=["output_column", "terminal"])
    names = [str(c) for c in table.column("output_column").to_pylist()]
    if len(names) != len(set(names)):  # 審碼 r13：provenance 每列唯一；重複即不可信（不得壓成單鍵後通過閉合）
        dup = sorted({c for c in names if names.count(c) > 1})[:5]
        raise RuntimeError(f"{path}：provenance 欄名重複 {dup}")
    return dict(zip(names, (str(t) for t in table.column("terminal").to_pylist())))


def _freeze_run_dir(cell_id: str) -> Path:
    work = FREEZE_RUNS / f"{cell_id}__default"
    side = json.loads((work / "numview_cell.json").read_text(encoding="utf-8"))
    return _run_dir(work, side)


def name_inference_mismatches(run_dir: Path) -> Optional[int]:
    """名稱推斷誤判欄數（SPEC v37 細則⑤）：`_infer_l7_processed_encoding` 之結果與 processed 轉換紀錄（最後施用者定實際
    編碼：zscore → int16；gaussian → int16；rank → uint16；皆未施用 ⇒ 無編碼）不符之欄數。"""
    import pyarrow.parquet as pq

    from momentum.FeatureEngineering import feature_storage as fs_mod

    path = Path(run_dir) / "provenance" / "processed_columns.parquet"
    if not path.is_file():
        return None
    count = 0
    for rec in pq.read_table(str(path)).to_pylist():
        if rec.get("adaptive_zscore") == "applied":
            actual = fs_mod.ZSCORE_INT16_ENCODING
        elif rec.get("gaussian_normalize") == "applied":
            actual = fs_mod.GAUSSIAN_INT16_ENCODING
        elif rec.get("rank_transform") == "applied":
            actual = fs_mod.RANK_UINT16_ENCODING
        else:
            actual = None
        inferred, _ = fs_mod.FeatureStorage._infer_l7_processed_encoding(str(rec["output_column"]))
        count += int(inferred != actual)
    return count


def fork_memmap(results: Mapping[str, Mapping[str, Any]], ic_ctx: Optional[Mapping[str, Any]],
                target: np.ndarray) -> List[Dict[str, Any]]:
    """`memmap_merge_dtype`：參照＝門檻極大（`pd.concat` 支）、變體＝門檻 0（memmap 支），兩者皆開 lag；合併點、L4 群組 S1
    與最終讀回逐欄。"""
    lo, hi = results.get("memmap_forced_low"), results.get("memmap_forced_high")
    if not lo or not hi or lo.get("settings_violations") or hi.get("settings_violations"):
        return [{"fork": "memmap_merge_dtype", "cell_id": HOST_CELL, "column": "*", "status": "blocked",
                 "reason": "變體缺或觀測設定不符", "material": None}]
    rows: List[Dict[str, Any]] = []
    for point, seg in (("layer4_input", "L4IN"), ("s1", "S1")):
        v, r = _cols_at(_seg_values(lo["capture_dir"], seg), target), _cols_at(_seg_values(hi["capture_dir"], seg), target)
        if point == "s1":
            v = {c: x for c, x in v.items() if c in r}
        ic_v = replay_ic(ic_ctx, v, target) if ic_ctx else ({}, set())
        ic_r = replay_ic(ic_ctx, {c: r[c] for c in v if c in r}, target) if ic_ctx else ({}, set())
        for row in column_rows("FORK", HOST_CELL, v, r, ic_v=ic_v[0], ic_r=ic_r[0], sel_v=ic_v[1], sel_r=ic_r[1],
                               source_run="memmap_forced_low", reference_run="memmap_forced_high"):
            rows.append({"fork": "memmap_merge_dtype", "point": point, **{k: x for k, x in row.items() if k != "segment"},
                         "sign_flips": int(bool(row.get("ic_sign_flip")))})
    lv, _, lts = readback_raw(Path(lo["run_dir"]))
    hv, _, hts = readback_raw(Path(hi["run_dir"]))
    same_axis = np.array_equal(lts, hts)
    icl = replay_ic(ic_ctx, lv, lts) if ic_ctx and same_axis else None
    ich = replay_ic(ic_ctx, hv, hts) if ic_ctx and same_axis else None
    for row in column_rows("FORK", HOST_CELL, lv, hv, ic_v=icl[0] if icl else None, ic_r=ich[0] if ich else None,
                           sel_v=icl[1] if icl else None, sel_r=ich[1] if ich else None,
                           source_run="memmap_forced_low", reference_run="memmap_forced_high"):
        rows.append({"fork": "memmap_merge_dtype", "point": "readback", **{k: x for k, x in row.items() if k != "segment"},
                     "sign_flips": int(bool(row.get("ic_sign_flip"))), "readback_axis_equal": bool(same_axis)})
    return rows


def fork_winsor(res: Optional[Mapping[str, Any]], ic_ctx: Optional[Mapping[str, Any]],
                target: np.ndarray) -> List[Dict[str, Any]]:
    """`winsor_sigma_dtype`（生產不可達，探針自建；SPEC v37 細則⑥）：FORK64（sigma 回 float64）對 FORK32（生產 float32）。"""
    base = {"fork": "winsor_sigma_dtype", "cell_id": HOST_CELL, "production_reachable": False,
            "production_unreachable_evidence": ["momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:3087-3096",
                                                "momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:3696",
                                                "momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:3722",
                                                "momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:2596-2597"]}
    if not res or res.get("settings_violations"):
        return [{**base, "column": "*", "status": "blocked", "reason": "變體缺或觀測設定不符", "material": None}]
    forks = res.get("winsor_fork") or []
    if not forks:
        return [{**base, "column": "*", "status": "blocked", "reason": "legacy 臂未被觸及", "material": None}]
    rows: List[Dict[str, Any]] = []
    s64 = capture_columns(Path(res["capture_dir"]), "FORK64")
    s32 = capture_columns(Path(res["capture_dir"]), "FORK32")
    changed = {c for f in forks for c in f.get("decision_changed_columns") or []}
    bad = {c: str(f.get("status")) for f in forks if f.get("status") != "measured" for c in f.get("columns") or []}
    for col, status in sorted(bad.items()):  # 新實例保真不符或無時間軸之群組：列出，不靜默略過
        rows.append({**base, "column": col, "status": status, "material": None})
    v64a = {c: x for c, x in _cols_at({c: v for c, v in s64.items() if c not in bad}, target).items()}
    v32a = {c: x for c, x in _cols_at({c: v for c, v in s32.items() if c in v64a}, target).items()}
    ic64 = replay_ic(ic_ctx, {c: v64a[c] for c in v32a}, target) if ic_ctx else ({}, set())
    ic32 = replay_ic(ic_ctx, v32a, target) if ic_ctx else ({}, set())
    for col, (v64, ep, key) in s64.items():
        if col in bad:
            continue
        if col not in s32:
            rows.append({**base, "column": col, "status": "no_reference", "material": None})
            continue
        st = checkpoint_stats(s32[col][0], v64)
        flip = _sign_flip(ic32[0].get(col), ic64[0].get(col)) if col in v32a else None
        survivor = ((col in ic32[1]) != (col in ic64[1])) if col in v32a else None
        rows.append({**base, "column": col, "status": "measured", **st, "decision_changed": col in changed,
                     "ic_sign_flip": flip, "sign_flips": int(bool(flip)), "survivor_set_change": survivor,
                     "material": bool(st["nan_mask_diff"]) or col in changed or bool(flip) or bool(survivor)})
    return rows


def extension_entry(res: Optional[Mapping[str, Any]], frozen_dir: Path) -> Dict[str, Any]:
    """尾端延伸（SPEC v37 細則③）：原始＝`tail_extension`（終點提前 100 根）、延伸後＝凍結 A；逐欄落盤 dtype 降級
    （float32→float16）欄數與重疊列讀回值變化欄數。"""
    if not res or res.get("settings_violations"):
        return {"cell_id": HOST_CELL, "status": "blocked", "downgraded_columns": 0, "new_evidence": False}
    ov, _, ots = readback_raw(Path(res["run_dir"]))
    ev, _, ets = readback_raw(frozen_dir)
    rows = np.flatnonzero(np.isin(ets, ots))
    downgraded = sorted(c for c in ov if c in ev and ov[c].dtype == np.float32 and ev[c].dtype == np.float16)
    upgraded = sorted(c for c in ov if c in ev and ov[c].dtype == np.float16 and ev[c].dtype == np.float32)
    changed = sorted(c for c in ov if c in ev and not _bitwise(ov[c].astype(np.float64),
                                                                ev[c][rows].astype(np.float64)))
    return {"cell_id": HOST_CELL, "status": "measured", "extension_bars": TAIL_EXTENSION_BARS,
            "overlap_rows": int(rows.size), "downgraded_columns": len(downgraded), "downgraded": downgraded[:50],
            "upgraded_columns": len(upgraded), "history_changed_columns": len(changed), "history_changed": changed[:50],
            "new_evidence": len(downgraded) > 0}


def compare_b(results: Mapping[str, Mapping[str, Any]], a_results: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    """格 B：生產即 R（`preserve_dtype=True`）⇒ S0 列＝同 run 內 S1 對 S0、S3＝`storage_only`；S1／S2 標
    `reference_is_production`；S4 codec_off；S5＝S1（float32）對 S0（float64）之重演選欄；分岔 `mtf_layer_dtype`（B 之 S1
    對 A 生產 S1）。生產等價：讀回對凍結 B 逐位元＋觀測設定。"""
    cid = B_CELL
    out: Dict[str, Any] = {"rows": [], "forks": [], "s4_raw_bss": [], "checks": {}, "notes": []}
    B = results.get("b_production_spy")
    frozen_dir = _freeze_run_dir(cid)
    fv, _, fts = readback_raw(frozen_dir)
    out["columns"] = sorted(fv)
    out["s4_raw_bss"].append({"cell_id": cid, "bitwise_equal": None, "status": "codec_off"})
    if not B:
        for seg in ("S0", "S1", "S2", "S3", "S4"):
            out["rows"] += _status_rows(seg, cid, sorted(fv), "blocked", "B 增列未跑")
        out["rows"].append({"segment": "S5", "cell_id": cid, "column": "*", "status": "blocked", "reason": "B 增列未跑",
                            "max_abs": None, "max_rel": None})
        out["forks"].append({"fork": "mtf_layer_dtype", "cell_id": cid, "column": "*", "status": "blocked",
                             "reason": "B 增列未跑", "material": None})
        return out
    bv, _, bts = readback_raw(Path(B["run_dir"]))
    equiv = (set(bv) == set(fv) and np.array_equal(bts, fts) and all(_bitwise(bv[c], fv[c]) for c in fv)
             and not B.get("settings_violations") and B.get("status") == "complete")  # 審碼 r13：blocked run 不得作等價
    out["checks"]["b_production_equivalent"] = bool(equiv)
    out["unindexed_groups"] = {"b_production_spy": unindexed_groups(B["capture_dir"])}
    out["checks"]["s1_all_indexed"] = not out["unindexed_groups"]["b_production_spy"]
    equiv = equiv and out["checks"]["s1_all_indexed"]
    ic_ctx = _load_ic(B["capture_dir"])
    if not equiv or ic_ctx is None:
        reason = "B 生產等價不成立或缺 IC 紀錄"
        for seg in ("S0", "S1", "S2", "S3"):
            out["rows"] += _status_rows(seg, cid, sorted(fv), "blocked", reason)
        out["rows"] += _status_rows("S4", cid, sorted(fv), "codec_off", "codec 未開（只 A 格量 codec）", source_run="freeze_B")
        out["rows"].append({"segment": "S5", "cell_id": cid, "column": "*", "status": "blocked", "reason": reason,
                            "max_abs": None, "max_rel": None})
        out["forks"].append({"fork": "mtf_layer_dtype", "cell_id": cid, "column": "*", "status": "blocked",
                             "reason": reason, "material": None})
        return out
    raw0, raw1, raw2 = (_seg_values(B["capture_dir"], s) for s in ("S0", "S1", "S2"))
    # S0 列於各欄原生列上比（4h 欄之原生列不對齊 1h 輸出時間軸；只在時間軸上對齊會靜默丟欄）
    native0, native1 = {}, {}
    for col, (v1, e1, _) in raw1.items():
        if col in raw0 and e1 is not None and raw0[col][1] is not None:
            common, i1, i0 = np.intersect1d(e1, raw0[col][1], return_indices=True)
            native1[col], native0[col] = np.asarray(v1)[i1], np.asarray(raw0[col][0])[i0]
    s0, s1, s2 = _cols_at(raw0, fts), _cols_at(raw1, fts), _cols_at(raw2, fts)
    out["columns_by_segment"] = {seg: sorted(fv) for seg in ("S0", "S1", "S2", "S3", "S4")}  # 凍結 B 落盤欄集合
    ic0, ic1 = replay_ic(ic_ctx, s0, fts), replay_ic(ic_ctx, s1, fts)  # IC 只對可對齊輸出時間軸之欄（主週期）重演
    not_replayed = {c: {"ic_scope": "native_tf_not_replayed"} for c in native1 if c not in s1}
    out["rows"] += column_rows("S0", cid, native1, native0, ic_v=ic1[0], ic_r=ic0[0], sel_v=ic1[1], sel_r=ic0[1],
                               source_run="b_production_spy", reference_run="b_production_spy", extra=not_replayed)
    out["notes"].append(f"S0 列 {len(native1)} 欄於原生列比；其中 {len(not_replayed)} 欄（非主週期）IC 未重演")
    out["rows"] += _status_rows("S1", cid, sorted(raw1), "reference_is_production", "B 之生產即 float64 層間鏈（S0 列已比）",
                               source_run="b_production_spy")
    out["rows"] += _status_rows("S2", cid, sorted(raw2), "reference_is_production", "B 之生產即 float64 層間鏈",
                               source_run="b_production_spy")
    storage = {c: {f"storage_only_{k}": v for k, v in checkpoint_stats(fv[c], s2[c]).items()} for c in fv if c in s2}
    out["rows"] += [{**r, "segment": "S3"} for r in column_rows("S3", cid, fv, s2, source_run="freeze_B",
                                                                reference_run="b_production_spy", extra=storage)]
    out["rows"] += _status_rows("S4", cid, sorted(fv), "codec_off", "codec 未開（只 A 格量 codec）", source_run="freeze_B")
    out["rows"].append(_s5_row(cid, "S0_vs_S1", ic0[1], ic1[1], ic0[0], ic1[0], "b_production_spy", "b_production_spy"))
    # mtf_layer_dtype：B 之 S1 對 A 生產（codec_upgrade_on）之 S1，同名主週期欄、輸出段交集
    P = a_results.get("codec_upgrade_on")
    a_ctx = _load_ic(P["capture_dir"]) if P else None
    if not P or P.get("settings_violations") or a_ctx is None:
        out["forks"].append({"fork": "mtf_layer_dtype", "cell_id": cid, "column": "*", "status": "blocked",
                             "reason": "A 生產 S1 不可用", "material": None})
        return out
    a1 = _cols_at(_seg_values(P["capture_dir"], "S1"), fts)
    common = sorted(set(a1) & set(s1))
    if not common:
        out["forks"].append({"fork": "mtf_layer_dtype", "cell_id": cid, "column": "*", "status": "blocked",
                             "reason": "A 與 B 同名欄交集為 0", "material": None})
        return out
    icb, ica = replay_ic(a_ctx, {c: s1[c] for c in common}, fts), replay_ic(a_ctx, {c: a1[c] for c in common}, fts)
    for row in column_rows("FORK", cid, {c: s1[c] for c in common}, {c: a1[c] for c in common}, ic_v=icb[0], ic_r=ica[0],
                           sel_v=icb[1], sel_r=ica[1], source_run="b_production_spy", reference_run="codec_upgrade_on"):
        out["forks"].append({"fork": "mtf_layer_dtype", **{k: x for k, x in row.items() if k != "segment"},
                             "sign_flips": int(bool(row.get("ic_sign_flip")))})
    fv_common = sorted(set(fv) & set(readback_raw(_freeze_run_dir(HOST_CELL))[0]))
    out["notes"].append(f"mtf_layer_dtype 讀回比對另列 report_only：凍結 A／B 同名欄 {len(fv_common)}")
    return out


def compare_c(results: Mapping[str, Mapping[str, Any]], cell_id: str = C_CELL) -> Dict[str, Any]:
    """格 C（群組粒度）：R＝`c_preserve_dtype`、P＝凍結讀回；S0＝R 內 S0 對 S1（依 R 之 registry 群組）、S3＝凍結讀回對
    R 讀回（依凍結 manifest 群組）；S1／S2 掛點同 A 不量（量測限制）；S4 codec_off（群組列）。"""
    from tests.feature_engineering import numview_helpers as nh

    cid = cell_id  # 預設格 C；審碼 r13 以 A 之試跑擷取實跑本函式 measured 路徑時改指（結果鍵仍為 c_preserve_dtype）
    out: Dict[str, Any] = {"rows": [], "s4_raw_bss": [{"cell_id": cid, "bitwise_equal": None, "status": "codec_off"}],
                           "checks": {}, "notes": []}
    frozen_dir = _freeze_run_dir(cid)
    gf = nh.group_fingerprints(frozen_dir, "raw")
    fv, fgroups, fts = readback_raw(frozen_dir)
    out["columns"] = sorted(fv)
    out["expected_groups"] = {"S3": {g: int(v["column_count"]) for g, v in gf["columns"].items()},
                              "S4": {g: int(v["column_count"]) for g, v in gf["columns"].items()}}
    R = results.get("c_preserve_dtype")
    if R:
        out["unindexed_groups"] = {"c_preserve_dtype": unindexed_groups(R.get("capture_dir"))}
        out["checks"]["s1_all_indexed"] = not out["unindexed_groups"]["c_preserve_dtype"]
    if not R or R.get("settings_violations") or R.get("status") != "complete" or not out["checks"].get("s1_all_indexed", True):
        # SPEC 邊界③：C blocked ⇒ 該格各段皆標 blocked（審碼 r11：不得混入 not_measured／codec_off 列）；
        # 審碼 r22：卡死監看判停滯 ⇒ 依 SPEC 標 blocked-by 硬體，鏈效應段（S0–S3）blocked、凍結讀回之 S4 照記 codec_off
        hardware = bool(R) and R.get("status") == "failed" and R.get("watch_status") == _watchdog().STALLED
        if hardware:
            reason = f"blocked-by 硬體：{R.get('reason')}"
        else:
            reason = "C 之 preserve 重生 blocked、失敗、觀測設定不符或擷取不完整" if R else "C 增列未跑"
        for seg in ("S0", "S1", "S2"):
            out["rows"].append({"segment": seg, "cell_id": cid, "group": "*", "columns_in_group": None,
                                "status": "blocked", "reason": reason, "max_abs": None, "max_rel": None})
        for g, n in sorted(out["expected_groups"]["S3"].items()):
            out["rows"].append({"segment": "S3", "cell_id": cid, "group": g, "columns_in_group": n,
                                "status": "blocked", "reason": reason, "max_abs": None, "max_rel": None})
        for g, n in sorted(out["expected_groups"]["S4"].items()):
            if hardware:
                out["rows"].append({"segment": "S4", "cell_id": cid, "group": g, "columns_in_group": n,
                                    "status": "codec_off", "reason": "codec 未開（只 A 格量 codec）", "max_abs": None,
                                    "max_rel": None, "source_run": "freeze_C"})
            else:
                out["rows"].append({"segment": "S4", "cell_id": cid, "group": g, "columns_in_group": n,
                                    "status": "blocked", "reason": reason, "max_abs": None, "max_rel": None})
        return out
    for g, n in sorted(out["expected_groups"]["S4"].items()):
        out["rows"].append({"segment": "S4", "cell_id": cid, "group": g, "columns_in_group": n, "status": "codec_off",
                            "reason": "codec 未開（只 A 格量 codec）", "max_abs": None, "max_rel": None,
                            "source_run": "freeze_C"})
    for seg in ("S1", "S2"):
        out["rows"].append({"segment": seg, "cell_id": cid, "group": "*", "columns_in_group": None,
                            "status": "not_measured", "reason": "掛點同 A，不重複（SPEC v36／v37 量測限制）",
                            "max_abs": None, "max_rel": None, "source_run": "freeze_C"})
    s1_entries = [e for e in load_capture(Path(R["capture_dir"]))["entries"] if e["segment"] == "S1" and e.get("rows")]
    # 群組對應以落盤欄名為鍵（與 `capture_columns` 之欄名一致）
    r_groups = {_storage_name(c, e.get("tf")): str(e["key"]) for e in s1_entries for c in e["columns"]}
    out["expected_groups"]["S0"] = {}
    for c, g in r_groups.items():
        out["expected_groups"]["S0"][g] = out["expected_groups"]["S0"].get(g, 0) + 1
    r_ts = readback_raw(Path(R["run_dir"]))[2]
    s0, s1 = (_cols_at(_seg_values(R["capture_dir"], s), r_ts) for s in ("S0", "S1"))
    rows0 = column_rows("S0", cid, s1, s0, source_run="c_preserve_dtype", reference_run="c_preserve_dtype")
    grouped0 = group_rows(rows0, r_groups, "S0", cid, "c_preserve_dtype", "c_preserve_dtype")
    # 諮詢 r3：C 之 S0 為「preserve 實得 dtype」之鏈，非全 float64 者逐群組計數並於格層回報（同 A 之 s0_incomplete），
    # 不得呈為完整 float64 鏈；L3–L6 讀入之 layer2 dtype 取自主鏈 spill 點觀測
    r0_dtypes = capture_dtypes(Path(R["capture_dir"]), "S0")
    for row in grouped0:
        row["s0_non_float64_columns"] = sum(1 for c, g in r_groups.items()
                                            if g == row["group"] and c in s0 and r0_dtypes.get(c) != "float64")
    out["rows"] += grouped0
    observed = R.get("observed_settings") or {}
    out["s0_incomplete"] = {"cell_id": cid, "source_run": "c_preserve_dtype",
                            "non_float64_columns": sum(1 for c in s0 if r0_dtypes.get(c) != "float64"),
                            "columns": len(s0), "dtypes": sorted({str(r0_dtypes.get(c)) for c in s0}),
                            "l2_consumer_dtypes": observed.get("l2_consumer_dtypes"),
                            "l2_spill_bypassed": observed.get("l2_spill_bypassed")}
    rv, _, _ = readback_raw(Path(R["run_dir"]))
    # 審碼 r12：欄集合閉合——registry 擷取欄集合須等於該 run 之 raw provenance 全部欄（獨立於擷取）；凍結讀回與 R 讀回之
    # 欄差只准由 provenance 之 `dead_dropped`（全特徵預設開 L7 死欄剔除）解釋，其餘即失敗
    prov_r, prov_f = raw_provenance_terminals(Path(R["run_dir"])), raw_provenance_terminals(frozen_dir)
    out["checks"]["c_s0_columns_equal_provenance"] = bool(prov_r) and set(r_groups) == set(prov_r)
    only_f, only_r = set(fv) - set(rv), set(rv) - set(fv)
    unexplained = sorted([c for c in only_f if prov_r.get(c) != "dead_dropped"]
                         + [c for c in only_r if prov_f.get(c) != "dead_dropped"])
    out["checks"]["c_readback_columns_explained"] = not unexplained
    out["column_mismatch"] = {"s0_vs_provenance": sorted(set(r_groups) ^ set(prov_r))[:50],
                              "frozen_only_dead_dropped_in_reference": sorted(only_f - set(unexplained)),
                              "reference_only_dead_dropped_in_frozen": sorted(only_r - set(unexplained)),
                              "unexplained": unexplained[:50]}
    rows3 = column_rows("S3", cid, fv, rv, source_run="freeze_C", reference_run="c_preserve_dtype")
    for row in rows3:  # R 側被死欄剔除之欄：已由 provenance 解釋，非缺參照
        if row["status"] == "no_reference" and prov_r.get(row["column"]) == "dead_dropped":
            row["status"], row["reason"] = "dropped_in_reference", "R run 之 L7 死欄剔除（provenance）"
    out["rows"] += group_rows(rows3, fgroups, "S3", cid, "freeze_C", "c_preserve_dtype")
    return out


# ============================================================================================== 子行程與主入口


def _child(spec_path: Path) -> int:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    if spec["mode"] == "generate":
        result = run_generation_unit(spec["source_run"], Path(spec["work"]), Path(spec["capture_dir"]))
        import resource  # 子行程自身峰值 RSS（諮詢 r3：C 停用主鏈 spill 之記憶體實測；macOS 以位元組、Linux 以 KB 計）
        result["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)
    else:
        results = {k: v for k, v in spec["results"].items()}
        if spec["cell_id"] == HOST_CELL:
            result = compare_a(results)
        elif spec["cell_id"] == B_CELL:
            result = compare_b(results, results)
        else:
            result = compare_c(results)
    Path(spec["result_path"]).write_text(json.dumps(result, ensure_ascii=False, default=str), encoding="utf-8")
    return 0


def _run_unit(spec: Dict[str, Any], inline: bool) -> Dict[str, Any]:
    result_path = Path(spec["result_path"])
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.unlink(missing_ok=True)
    spec_path = result_path.with_suffix(".spec.json")
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, default=str), encoding="utf-8")
    if inline:
        _child(spec_path)
    else:
        wd = _watchdog()
        watched = wd.run_watched([sys.executable, str(Path(__file__).resolve()), "--child", str(spec_path)],
                                 log_path=result_path.with_suffix(".log"), config=wd.load_config(_criteria()),
                                 cwd=str(REPO))
        if watched.status == wd.STALLED or watched.returncode != 0 or not result_path.is_file():
            return {"status": "failed", "reason": f"{watched.status}（{watched.reason}；rc={watched.returncode}；"
                                                  f"{watched.wall_seconds:.0f} 秒；見 {result_path.with_suffix('.log')}）",
                    "watch_status": watched.status, "swap_growth_max_mb": watched.swap_growth_max_mb}
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["swap_growth_max_mb"] = watched.swap_growth_max_mb
        return result
    return json.loads(result_path.read_text(encoding="utf-8"))


def formal_readiness_violations(receipt: Mapping[str, Any]) -> List[str]:
    """正式跑前置（SPEC §V，r37 X37-A）：估時收據 `run_kinds.precision_chain.addenda` 恰等於 `estimate.PRECISION_ADDENDA`
    （以 (格, 變體) 比）且兩 memmap 列 `measured_lag_on` 為 True；任一不符 ⇒ 整個正式跑拒跑（A 亦然）。"""
    node = ((receipt.get("run_kinds") or {}).get("precision_chain") or {})
    out: List[str] = []
    want = [(str(r["cell"]), str(r["variant"])) for r in getattr(_estimate(), "PRECISION_ADDENDA", [])]
    got = [(str(r.get("cell")), str(r.get("variant"))) for r in node.get("addenda") or []]
    if not want or sorted(got) != sorted(want) or len(got) != len(set(got)):
        out.append(f"估時收據 addenda {got} ≠ PRECISION_ADDENDA {want}")
    expected = {(str(r["cell"]), str(r["variant"])): r for r in getattr(_estimate(), "PRECISION_ADDENDA", [])}
    for row in node.get("addenda") or []:  # 審碼 r11：增列列之結構與秒數亦須合格
        spec = expected.get((str(row.get("cell")), str(row.get("variant"))))
        if spec is None:
            continue
        for key in ("generations", "covers_ids", "unique_output"):
            if row.get(key) != spec[key] or (key == "generations" and type(row.get(key)) is not int):  # 審碼 r15：True≠1
                out.append(f"addenda {row.get('variant')}：{key} {row.get(key)!r} ≠ PRECISION_ADDENDA")
        sec = row.get("seconds")
        if isinstance(sec, bool) or not isinstance(sec, (int, float)) or not np.isfinite(sec) or sec <= 0:
            out.append(f"addenda {row.get('variant')}：seconds {sec!r} 非有限正數")
        else:  # 審碼 r15：秒數須綁回估時收據該格之實測秒數（generations × measurements.<格>.seconds）
            meas = (receipt.get("measurements") or {}).get(str(row.get("cell"))) or {}
            m = meas.get("seconds")
            # 審碼 r16：實測須為 measured 且秒數有限正數；增列秒數須恰等於 generations × 實測（同 `apply_precision_addenda` 之式）
            if meas.get("status") != "measured" or isinstance(m, bool) or not isinstance(m, (int, float)) \
                    or not np.isfinite(m) or m <= 0 or float(sec) != int(spec["generations"]) * float(m):
                out.append(f"addenda {row.get('variant')}：seconds {sec!r} ≠ generations × measurements.{row.get('cell')}.seconds")
    for variant in ("memmap_forced_low", "memmap_forced_high"):  # 各恰一列且標實測（審碼 r8：缺列不得放行）
        hits = [r for r in node.get("runs") or [] if str(r.get("variant")) == variant]
        if len(hits) != 1:
            out.append(f"{variant}：估時收據 precision_chain.runs 須恰一列，實得 {len(hits)}")
        elif hits[0].get("measured_lag_on") is not True:
            out.append(f"{variant} 未標 measured_lag_on（SPEC v37 細則⑦）")
        elif hits[0].get("trial_status") != "complete":  # 審碼 r17：秒數須出自完成之試跑 run（blocked／failed 不給秒數）
            out.append(f"{variant}：trial_status {hits[0].get('trial_status')!r} ≠ complete")
        else:  # 審碼 r9：須為 A 宿主格、秒數為有限正數
            row = hits[0]
            if str(row.get("cell")) != HOST_CELL:
                out.append(f"{variant}：格 {row.get('cell')} ≠ {HOST_CELL}")
            sec = row.get("seconds")
            if isinstance(sec, bool) or not isinstance(sec, (int, float)) or not np.isfinite(sec) or sec <= 0:
                out.append(f"{variant}：seconds {sec!r} 非有限正數")
    return out


#: 以格為單位之收據清單鍵（每項皆帶 `cell_id`）與以 run 名為鍵之對應表鍵（SPEC v39 只重做單格之合併）
CELL_LIST_KEYS = ("cells", "rows", "forks", "codec_checks", "extension", "s4_raw_bss", "codec_fallbacks",
                  "processed_codec", "s0_incomplete")
RUN_MAP_KEYS = ("runs", "observed_settings", "settings_violations", "windows", "layer4_merge", "ic_input_dtypes",
                "timings", "run_status", "memory")
#: 可單獨重做之格：其比對只用本格之 run（A 之比對供 B 用，A／B 不可單獨重做）
MERGEABLE_CELLS = (C_CELL,)


class MergeError(RuntimeError):
    """只重做單格之合併前提不符（不得產正式收據）。"""


_CANONICAL_GROUPS: Dict[str, Dict[str, int]] = {}


def canonical_c_groups(cell: str = C_CELL) -> Dict[str, int]:
    """格（群組粒度）之 S3／S4 期望群組之獨立來源：凍結 run 之 raw manifest 群組與欄數（同 `compare_c` 之 `expected_groups`；
    審碼 r24：合併與驗收不得只信收據自報）。凍結 run 不變，行程內快取（逐值雜湊為秒級以上）。"""
    from tests.feature_engineering import numview_helpers as nh

    if cell not in _CANONICAL_GROUPS:
        gf = nh.group_fingerprints(_freeze_run_dir(cell), "raw")
        _CANONICAL_GROUPS[cell] = {str(g): int(v["column_count"]) for g, v in gf["columns"].items()}
    return dict(_CANONICAL_GROUPS[cell])


def merge_receipt(parent: Mapping[str, Any], child: Mapping[str, Any], cell: str, parent_sha256: str) -> Dict[str, Any]:
    """SPEC v39（諮詢 r3）：以只重做 `cell` 之收據 `child` 取代正式收據 `parent` 中該格之全部內容；其餘格之清單項、run 對應表
    與 checks 逐位保留。前提：兩者皆正式（非試跑）、判準雜湊相同、`cell` 屬 `MERGEABLE_CELLS`、parent 恰含該格一次、child 之
    格恰為該格且其清單項全屬該格。合併後重算 `lossless_violation` 與 `exit_code`，並記 `merge` 來源。"""
    import copy as _copy

    if cell not in MERGEABLE_CELLS:
        raise MergeError(f"{cell} 不可單獨重做（只限 {MERGEABLE_CELLS}）")
    if parent.get("trial") is not False or child.get("trial") is not False:
        raise MergeError("parent 與 child 皆須為正式收據（trial=false）")
    if parent.get("criteria_sha256") != child.get("criteria_sha256"):
        raise MergeError("判準雜湊不同")
    if [str(c.get("cell_id")) for c in parent.get("cells") or []].count(cell) != 1:
        raise MergeError(f"parent 須恰含 {cell} 一次")
    if [str(c.get("cell_id")) for c in child.get("cells") or []] != [cell]:
        raise MergeError(f"child 之格須恰為 [{cell}]")
    missing_keys = [k for k in CELL_LIST_KEYS + RUN_MAP_KEYS + ("checks",) if k not in child]  # 審碼 r24：缺鍵不得當空
    if missing_keys:
        raise MergeError(f"child 缺鍵 {missing_keys}")
    for key in CELL_LIST_KEYS:
        stray = [e.get("cell_id") for e in child.get(key) or [] if str(e.get("cell_id")) != cell]
        if stray:
            raise MergeError(f"child.{key} 含他格項 {sorted(set(map(str, stray)))}")
    cell_runs = {r for r, s in RUN_SPECS.items() if s["cell"] == cell} | {FREEZE_RUN_NAMES[cell]}
    stray_runs = {k for key in RUN_MAP_KEYS for k in (child.get(key) or {}) if k not in cell_runs}
    if stray_runs:
        raise MergeError(f"child 含他格 run {sorted(stray_runs)}")
    # 審碼 r22–r23：child 須真帶該格量測內容——S0–S4 每段皆有統計列、群組粒度段之群組集合恰等於 child 格紀錄之期望群組、
    # 全部 run 之身分（生成失敗之 run 無身分，准缺，但此時該格列須全為 blocked／codec_off）、各 run 之設定檢查與該格之 checks
    child_rows = [r for r in child.get("rows") or [] if str(r.get("cell_id")) == cell]
    missing_segs = [s for s in ("S0", "S1", "S2", "S3", "S4") if not any(r.get("segment") == s for r in child_rows)]
    if missing_segs:
        raise MergeError(f"child 缺 {cell} 之段 {missing_segs}")
    derived = "measured" if any(r.get("status") == "measured" for r in child_rows) else "blocked"  # 同 `assemble_receipt`
    if child["cells"][0].get("status") != derived:  # 審碼 r25：格狀態須與列一致
        raise MergeError(f"child {cell} 格狀態 {child['cells'][0].get('status')!r} ≠ 由列導出之 {derived}")
    expected = (child["cells"][0].get("expected_groups") or {})
    # 審碼 r24：期望群組不得由 child 自報——S3／S4 須等於凍結 C 之 manifest 群組（獨立來源）；有 measured 列時 S0 亦須非空
    frozen_groups = canonical_c_groups(cell)
    for seg in ("S3", "S4"):
        if {str(g): int(n) for g, n in (expected.get(seg) or {}).items()} != frozen_groups:
            raise MergeError(f"child {cell} 段 {seg} 之期望群組 ≠ 凍結 manifest 群組")
    if any(r.get("status") == "measured" for r in child_rows) and not expected.get("S0"):
        raise MergeError(f"child {cell} 有 measured 列而 S0 期望群組為空")
    for seg, groups in expected.items():
        got = sorted(str(r.get("group")) for r in child_rows if r.get("segment") == seg)
        if got != sorted(str(g) for g in groups):
            raise MergeError(f"child {cell} 段 {seg} 之群組列 ≠ 期望群組（{len(got)} 對 {len(groups)}）")
    failed_runs = {r for r, s in (child.get("run_status") or {}).items() if s == "failed"}
    missing_runs = sorted(cell_runs - set(child.get("runs") or {}) - failed_runs)
    if missing_runs:
        raise MergeError(f"child.runs 缺 {missing_runs}")
    if failed_runs & cell_runs and any(r.get("status") not in ("blocked", "codec_off") for r in child_rows):
        raise MergeError(f"child 之 run {sorted(failed_runs)} 失敗而 {cell} 仍有非 blocked／codec_off 列")
    gen_runs = cell_runs - {FREEZE_RUN_NAMES[cell]}
    need_checks = {f"settings.{r}" for r in gen_runs} | {f"{cell}.no_reference_rows_zero"}
    missing_checks = sorted(need_checks - set(child.get("checks") or {}))
    if missing_checks:
        raise MergeError(f"child.checks 缺 {missing_checks}")
    bad_settings = sorted(k for k in child["checks"] if k.startswith("settings.") and child["checks"][k] is not True)
    if bad_settings and any(r.get("status") == "measured" for r in child_rows):  # 審碼 r24：設定不符之 run 不得有量測列
        raise MergeError(f"child 設定檢查 {bad_settings} 不為真而 {cell} 有 measured 列")
    stray_checks = [k for k in child.get("checks") or {}
                    if not (k.startswith(f"{cell}.") or k in {f"settings.{r}" for r in cell_runs})]
    if stray_checks:
        raise MergeError(f"child 含他格 checks {stray_checks}")
    out = _copy.deepcopy(dict(parent))
    for key in CELL_LIST_KEYS:
        out[key] = [e for e in out.get(key) or [] if str(e.get("cell_id")) != cell] + _copy.deepcopy(list(child.get(key) or []))
    for key in RUN_MAP_KEYS:
        kept = {k: v for k, v in (out.get(key) or {}).items() if k not in cell_runs}
        out[key] = {**kept, **_copy.deepcopy(dict(child.get(key) or {}))}
    checks = {k: v for k, v in (out.get("checks") or {}).items()
              if not (k.startswith(f"{cell}.") or k in {f"settings.{r}" for r in cell_runs})}
    out["checks"] = {**checks, **dict(child.get("checks") or {})}
    measured_bss = [e for e in out["s4_raw_bss"] if e.get("status") == "measured"]
    out["lossless_violation"] = not all(e["bitwise_equal"] for e in measured_bss) if measured_bss else False
    for key in ("generated_at", "head", "command"):
        out[key] = child.get(key)
    out["merge"] = {"parent_sha256": parent_sha256, "parent_generated_at": parent.get("generated_at"),
                    "parent_head": parent.get("head"), "parent_command": parent.get("command"),
                    "replaced_cell": cell, "replaced_runs": sorted(cell_runs)}
    out["exit_code"] = 0 if all(out["checks"].values()) else 3
    return out


def _parse(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NUMVIEW Task 1.2 精度鏈逐段量測")
    parser.add_argument("--merge-into", default=None,
                        help="只重做 C 格並併入此正式收據（就地取代；原檔備份於本次工作目錄；SPEC v39）")
    parser.add_argument("--runs", default=None, help="只跑之 source_run（逗號分隔；試跑用，須同給 --out）")
    parser.add_argument("--no-compare", action="store_true", help="只生成不比對（細則⑦實測秒數；須同給 --out）")
    parser.add_argument("--inline", action="store_true", help="單元於本行程執行（試跑用）")
    parser.add_argument("--keep-tmp", action="store_true", help="保留擷取暫存（試跑除錯用）")
    parser.add_argument("--out", default=None, help="收據輸出路徑（未給 ⇒ 正式收據，須通過正式跑前置）")
    parser.add_argument("--work-root", default=str(DEFAULT_WORK_ROOT))
    parser.add_argument("--regenerate", default=None, help="與 --resume 併用：強制重生之 source_run（逗號分隔）")
    parser.add_argument("--resume", default=None,
                        help="沿用 <work-root>/<stamp> 已完成之生成結果（_results/<run>.json 存在且擷取目錄在）只補跑其餘並重做比對")
    parser.add_argument("--child", default=None, help=argparse.SUPPRESS)
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """量測主入口；rc 0＝收據寫出且檢查全過。S4 raw BSS 讀回非逐位元相等 ⇒ 收據標 `lossless_violation`（不改 rc）。"""
    args = _parse(argv)
    _gate().require("precision_chain", [HOST_CELL, B_CELL, C_CELL], receipts_dir=RECEIPTS_DIR)  # 一切生成之前
    if args.child:
        return _child(Path(args.child))
    trial = bool(args.runs or args.no_compare)
    if trial and not args.out:
        print("[precision] 試跑旗標須同給 --out（不得寫正式收據）", file=sys.stderr)
        return 2
    if args.merge_into and (trial or args.out or args.resume):
        print("[precision] --merge-into 為正式只重做 C，不得併用 --runs／--no-compare／--out／--resume", file=sys.stderr)
        return 2
    parent: Optional[Dict[str, Any]] = None
    if args.merge_into:  # 先驗 parent 可讀且為正式收據，再啟動任何生成
        parent_path = Path(args.merge_into)
        parent_bytes = parent_path.read_bytes()
        parent = json.loads(parent_bytes)
        if parent.get("trial") is not False or parent.get("criteria_sha256") != _criteria_sha256():
            print("[precision] --merge-into 之 parent 須為現行判準下之正式收據", file=sys.stderr)
            return 2
    runs = [r for r in RUN_SPECS if (RUN_SPECS[r]["cell"] in MERGEABLE_CELLS if args.merge_into
                                     else (not args.runs or r in set(args.runs.split(","))))]
    cells = sorted({RUN_SPECS[r]["cell"] for r in runs})
    if not args.out:
        violations = formal_readiness_violations(_gate().load_estimate_receipt(RECEIPTS_DIR))
        if violations:
            print(f"[precision] 正式跑前置不符：{violations}", file=sys.stderr)
            return 2
    stamp = args.resume or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    work = Path(args.work_root) / stamp
    tmp = TMP_ROOT / stamp
    results: Dict[str, Dict[str, Any]] = {}
    timings: Dict[str, float] = {}
    with _freeze()._clean_env({}):
        for name in runs:
            done = work / "_results" / f"{name}.json"
            if (args.resume and name not in set((args.regenerate or "").split(",")) and done.is_file()
                    and (tmp / name / "capture.json").is_file()):
                res = json.loads(done.read_text(encoding="utf-8"))
                _log(f"沿用 {name}（{args.resume}）")
            else:
                _log(f"生成 {name}")
                res = _run_unit({"mode": "generate", "source_run": name, "work": str(work / name),
                                 "capture_dir": str(tmp / name), "result_path": str(done)}, args.inline)
            if res.get("status") not in ("complete", "blocked") or "observed_settings" not in res:
                res.setdefault("settings_violations", [f"生成失敗：{res.get('reason')}"])
            else:
                res["settings_violations"] = settings_violations(name, res["observed_settings"], res["window"][1])
            results[name] = res
            timings[name] = float(res.get("seconds") or 0.0)
            _log(f"{name}：{res.get('status')}，{timings[name]:.1f} 秒，設定不符 {res.get('settings_violations')}")
        compared: Dict[str, Dict[str, Any]] = {}
        if not args.no_compare:
            by_cell = {HOST_CELL: {k: v for k, v in results.items() if RUN_SPECS[k]["cell"] == HOST_CELL},
                       B_CELL: {**{k: v for k, v in results.items() if RUN_SPECS[k]["cell"] in (B_CELL, HOST_CELL)}},
                       C_CELL: {k: v for k, v in results.items() if RUN_SPECS[k]["cell"] == C_CELL}}
            for cid in (HOST_CELL, B_CELL, C_CELL):
                if (trial or parent is not None) and cid not in cells:
                    continue
                _log(f"比對 {cid}")
                compared[cid] = _run_unit({"mode": "compare", "cell_id": cid, "results": by_cell[cid],
                                           "result_path": str(work / "_results" / f"compare_{cid}.json")}, args.inline)
    receipt = assemble_receipt(results, compared, timings, list(argv) if argv is not None else sys.argv[1:], trial)
    compare_failed = any(c.get("status") == "failed" for c in compared.values())
    dest = Path(args.out) if args.out else RECEIPTS_DIR / f"{datetime.now().strftime('%Y%m%d')}-numview-precision-chain.json"
    if parent is not None:  # SPEC v39：child 與 parent 備份留工作目錄；比對失敗不合併（parent 不動）
        work.mkdir(parents=True, exist_ok=True)
        (work / "child_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=str) + "\n",
                                                 encoding="utf-8")
        if compare_failed:
            _log(f"比對失敗：不合併，parent 不動；child 收據 {work / 'child_receipt.json'}")
            return 3
        (work / "parent_receipt.json").write_bytes(parent_bytes)
        receipt = merge_receipt(parent, receipt, C_CELL, hashlib.sha256(parent_bytes).hexdigest())
        dest = parent_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    if compare_failed:
        _log(f"比對有失敗單元：保留擷取 {tmp} 與生成 {work}，修正後以 --resume {stamp} 重做比對（不重生）")
    elif not args.keep_tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    _log(f"收據 {dest}；檢查 {receipt['checks']}")
    return int(receipt["exit_code"])


def assemble_receipt(results: Mapping[str, Mapping[str, Any]], compared: Mapping[str, Mapping[str, Any]],
                     timings: Mapping[str, float], command: Sequence[str], trial: bool) -> Dict[str, Any]:
    cells, rows, forks, codec_checks, extension, bss, fallbacks, processed = [], [], [], [], [], [], [], []
    checks: Dict[str, bool] = {}
    for cid, comp in compared.items():
        if comp.get("status") == "failed":
            checks[f"compare_{cid}"] = False
            continue
        cell = _cell(cid)
        cell_fb = [f for f in comp.get("codec_fallbacks") or []]
        measured = any(r.get("status") == "measured" for r in comp.get("rows") or [])
        cells.append({"cell_id": cid, "kind": cell["kind"], "symbol": cell["symbol"], "timeframes": cell["timeframes"],
                      "status": "measured" if measured else "blocked", "columns": comp.get("columns") or [],
                      "columns_by_segment": comp.get("columns_by_segment"),
                      "granularity": "group" if cell["kind"] == "C" else "column",
                      "expected_groups": comp.get("expected_groups"), "codec_fallback_count": len(cell_fb)})
        rows += comp.get("rows") or []
        forks += comp.get("forks") or []
        codec_checks += comp.get("codec_checks") or []
        extension += comp.get("extension") or []
        bss += comp.get("s4_raw_bss") or []
        fallbacks += cell_fb
        processed += comp.get("processed_codec") or []
        for k, v in (comp.get("checks") or {}).items():
            checks[f"{cid}.{k}"] = bool(v)
    runs = {name: res.get("identity") for name, res in results.items() if res.get("identity")}
    for cid, name in FREEZE_RUN_NAMES.items():
        if cid in compared:
            runs[name] = frozen_identity(name, cid)
    for name, res in results.items():
        checks[f"settings.{name}"] = not res.get("settings_violations")
    for cid in compared:  # 審碼 r9：缺參照之列（逐欄 no_reference、群組 partial／no_reference）一律使收據不過
        bad = sum(1 for r in rows if str(r.get("cell_id")) == cid
                  and r.get("status") in ("no_reference", "partial_no_reference"))
        checks[f"{cid}.no_reference_rows_zero"] = bad == 0
    measured_bss = [e for e in bss if e.get("status") == "measured"]
    receipt = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
               "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True).stdout.strip(),
               "command": " ".join(["venv/bin/python", "handoffs/run_receipts/numview_probes/precision_chain.py", *command]),
               "criteria_sha256": _criteria_sha256(), "trial": trial, "cells": cells, "rows": rows, "forks": forks,
               "codec_checks": codec_checks, "extension": extension, "s4_raw_bss": bss,
               "lossless_violation": not all(e["bitwise_equal"] for e in measured_bss) if measured_bss else False,
               "codec_fallbacks": fallbacks, "processed_codec": processed, "runs": runs,
               "s0_incomplete": [c["s0_incomplete"] for c in compared.values() if c.get("s0_incomplete")],
               "observed_settings": {n: r.get("observed_settings") for n, r in results.items()},
               "settings_violations": {n: r.get("settings_violations") for n, r in results.items()},
               "windows": {n: r.get("window") for n, r in results.items()},
               "layer4_merge": {n: r.get("layer4_merge") for n, r in results.items() if r.get("layer4_merge")},
               "ic_input_dtypes": {n: r.get("ic_input_dtypes") for n, r in results.items()},
               "timings": dict(timings), "run_status": {n: r.get("status") for n, r in results.items()},  # 審碼 r17
               "memory": {n: {"peak_rss_bytes": r.get("peak_rss_bytes"), "swap_growth_max_mb": r.get("swap_growth_max_mb")}
                          for n, r in results.items()},  # 諮詢 r3
               "checks": checks}
    receipt["exit_code"] = 0 if all(checks.values()) else 3
    return receipt


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

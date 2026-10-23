"""NUMVIEW post-IC 分支差 HEAD 重量與翻轉（docs/NUMVIEW_SPEC.md Task 1.1，C5）。

母集：`tests/_golden/icpostleak/contract.json` 之分支與七組合，另加探針專用候選臂 `polars_float64`（Polars post-IC
轉換全程 Float64：`pandas_to_polars(use_float64=True)`、rank `map_batches` 之 `return_dtype` Float64、rank UDF 緩衝區
與逐值寫入 float64、`_polars_mask_columns` 中間保留 Float64、gaussian 分支與 `_gaussian_2d` 回傳與最終回傳攜帶
compute dtype，輸出於落盤前轉 float32；探針內 monkeypatch，不改產品碼；收據記中間 dtype 以證全程 Float64）。
輸入：(i) ICPOSTLEAK §G 輸入集建法套用於每個 symbol×tf；(ii) 格 A／B 之 IC-first 實際選欄之 raw 欄（Task 0.5 保留之 run）。
參照＝測試端獨立 numpy float64 實作（rank→gaussian→zscore、窗未滿 NaN），另列 legacy 臂。
輸出（欄名依判準檔）：格級 max_abs／p99_abs／max_rel（近零格另列）／NaN 遮罩差；IC 層逐欄 IC、正負號翻轉數、
Kendall τ-b（未定義 ⇒ material）、`material`；速度：各臂轉換牆鐘三次與中位數。生成型輸入啟動前呼叫
`_estimate_gate.require("postic_branchdiff", cells)`。收據 `handoffs/run_receipts/<date>-numview-postic-branchdiff.json`，
含 `criteria_sha256`。

純函式 `cell_diff`／`ic_material` 已隨 Task 0.3 判準實作（NUMVIEW b1；判準檔 `material` 之參考判定）。

量測（SPEC v33 Task 1.1）：每個 (格, 輸入) 一個子行程（卡死監看 `_watchdog.run_watched`，判準 `cell_rules.watchdog`）——
- 輸入 (i)：判準 `kline_source` 主週期來源之該 symbol×tf 前 ICPOSTLEAK 契約 `kline.rows` 根，依 §G 建法（close、volume、契約
  `l1_features` 之 TA-Lib 欄、人工晚生欄）；輸入 (ii)：凍結 run（`data_cache/numview_freeze_runs/<格>__default`）之 IC-first
  實際選欄經 IC 頁同一 ratio-unsafe 剔除後之 raw 欄（輸出段；不另生成）。
- 分支依判準 v8 `branches_by_input`；分支之執行同 ICPOSTLEAK `_run_branch`（契約 env、entry、`patch_shard_bytes`、spy），
  registry 群組週期取該格週期；候選臂＝polars 環境＋探針內 monkeypatch（`_install_candidate`），輸出轉 float32（落盤前）。
- 同臂排名算一次：每分支先跑 rank 單步得 R，含 rank 之組合以 R 為輸入跑其餘步驟；`A_BTCUSDT_1h` 兩輸入逐組合另跑一次完整
  鏈逐位元比對（`shared_rank_check`，不等即 exit≠0）。
- 參照＝`tests/feature_engineering/numview_reference.py` 之鏈（rank→gaussian→zscore，窗同 ICPOSTLEAK 契約；gaussian 窗＝
  `_rolling_window()`），逐欄多行程計算；定義差異格（常數窗約定，SPEC Task 0.6）另列、浮點誤差欄扣除之。
- IC＝逐欄 Spearman（兩邊皆有限且 ≥ 3 對）對標籤 `close.pct_change().shift(-1)`（讀至輸出段終點，同生產 IC-first）；標籤出處
  另經生產 adapter 讀取逐值比對（`label_provenance`）。
- 速度：各可達臂（契約 `post_ic_arm_reachability`）＋候選臂之 IC 頁預設請求轉換，三次牆鐘與中位數。
`--perf`：獨立效能基準（判準 `run_coverage.perf_benchmark` 之格），各臂三次＋Polars 慢因剖析，寫
`<date>-numview-perf-benchmark.json`。`--cells`／`--max-cols` 僅供小規模試跑，須同給 `--out`（不寫正式收據）。
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import json
import math
import os
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
PROBES_DIR = Path(__file__).resolve().parent
RECEIPTS_DIR = REPO / "handoffs" / "run_receipts"
ICPOSTLEAK_CONTRACT_PATH = REPO / "tests" / "_golden" / "icpostleak" / "contract.json"
BRANCHDIFF_1002_PATH = RECEIPTS_DIR / "20261002-icpostleak-branch-diff.json"
FREEZE_SCRIPT = REPO / "scripts" / "numview_freeze_baseline.py"
FREEZE_RUNS = REPO / "data_cache" / "numview_freeze_runs"
DEFAULT_WORK_ROOT = REPO / "data_cache" / "numview_branchdiff_runs"

#: 探針專用候選臂名（SPEC Task 1.1；非產品臂，不入 post_ic_arm_values）
CANDIDATE_ARM = "polars_float64"
#: sink 分支（逐群組路由紀錄；判準 v8 `sink_routes`）
SINK_BRANCHES = ("registry_sink", "registry_sink_sharded")
#: 同臂排名算一次之抽驗格（SPEC Task 1.1 驗證）
SHARED_RANK_CHECK_CELL = "A_BTCUSDT_1h"
SPEED_REPEATS = 3
EPSILON = 1e-8
#: `FeaturePreprocessor._resolve_column_chunk_size` 之預設（FFACT_L65_CHUNK_SIZE 未設）
DEFAULT_CHUNK_SIZE = 2000


def cell_diff(reference: np.ndarray, output: np.ndarray) -> Dict[str, Any]:
    """格級差（SPEC Task 1.1；邊界①）：`max_abs`、`p99_abs`、`max_rel`（|ref| < float32 tiny 之近零格不計相對差）、
    `near_zero_cells` 與 `near_zero_max_abs`（近零格另列絕對差）、`nan_mask_diff`（兩者 NaN 遮罩不同之格數）。

    差值只對兩者皆有限之格計（float64）；無此類格 ⇒ 差值欄為 None。形狀不同 ⇒ ValueError（不廣播）。
    任一邊含 ±inf ⇒ ValueError（非有限值 fail-closed，不得併入中性摘要；NaN 為窗未滿等預期缺值，由 `nan_mask_diff` 計）。"""
    ref = np.asarray(reference, dtype=np.float64)
    out = np.asarray(output, dtype=np.float64)
    if ref.shape != out.shape:
        raise ValueError(f"cell_diff 形狀不同：{ref.shape} vs {out.shape}")
    n_inf = int(np.count_nonzero(np.isinf(ref))) + int(np.count_nonzero(np.isinf(out)))
    if n_inf:
        raise ValueError(f"cell_diff 輸入含 ±inf 共 {n_inf} 格（非有限值 fail-closed）")
    nan_mask_diff = int(np.count_nonzero(np.isnan(ref) != np.isnan(out)))
    both = np.isfinite(ref) & np.isfinite(out)
    absdiff = np.abs(out[both] - ref[both])
    ref_both = np.abs(ref[both])
    tiny = float(np.finfo(np.float32).tiny)
    near = ref_both < tiny
    far = ~near
    return {
        "max_abs": float(absdiff.max()) if absdiff.size else None,
        "p99_abs": float(np.percentile(absdiff, 99)) if absdiff.size else None,
        "max_rel": float((absdiff[far] / ref_both[far]).max()) if np.any(far) else None,
        "near_zero_cells": int(np.count_nonzero(near)),
        "near_zero_max_abs": float(absdiff[near].max()) if np.any(near) else None,
        "nan_mask_diff": nan_mask_diff,
    }


def _kendall_tau_b(x: np.ndarray, y: np.ndarray) -> float:
    """Kendall τ-b；有效對數 < 2 或任一邊全 ties（分母 0）⇒ NaN（不發警告、不回 0）。

    τ-b＝1 之判定以 exact 排序比較為準（兩邊 dense rank 逐元素相等 ⇔ 每一對之大小關係〔含相等〕皆一致 ⇔ τ-b＝1），
    回傳恰 1.0；不以浮點 `tau < 1` 判（scipy 之開方捨入可得 0.9999999999999998，會把同序誤判為翻轉）。"""
    if x.size < 2:
        return float("nan")
    import warnings

    from scipy.stats import kendalltau, rankdata

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tau = float(kendalltau(x, y, variant="b")[0])
    if np.isfinite(tau) and np.array_equal(rankdata(x, method="dense"), rankdata(y, method="dense")):
        return 1.0
    return tau


def ic_material(ic_reference: Sequence[float], ic_variant: Sequence[float]) -> Dict[str, Any]:
    """IC 層翻轉（SPEC Task 1.1、設計選擇⑥、R2-D）：`tau_b`（只對兩者 IC 皆有限之欄對計算；全 ties、全 NaN、有效對數
    < 2 ⇒ NaN）、`sign_flips`、`material`（任一正負號翻轉、τ-b < 1、或 τ-b 非有限 ⇒ True）、`reason`（判定原因）。
    非有限統計量一律 `material=True`（fail-closed），不得以 `NaN < 1 == False` 判未翻轉。

    判準依 `tests/_golden/numview/preregistered_criteria.json` 之 `material`：IC 之 NaN 遮罩（有限與否）不同、兩者皆有限
    之欄 IC 正負號不同、或 τ-b < 1／非有限 ⇒ material。選欄數為零之格由呼叫端於呼叫前處理（Task 1.1 邊界②）。"""
    a = np.asarray(ic_reference, dtype=np.float64)
    b = np.asarray(ic_variant, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError(f"ic_material 長度不同：{a.shape} vs {b.shape}")
    reasons = []
    mask_diff = int(np.count_nonzero(np.isfinite(a) != np.isfinite(b)))
    if mask_diff:
        reasons.append(f"nan_mask_diff={mask_diff}")
    both = np.isfinite(a) & np.isfinite(b)
    sign_flips = int(np.count_nonzero(np.sign(a[both]) != np.sign(b[both])))
    if sign_flips:
        reasons.append(f"ic_sign_flip={sign_flips}")
    tau = _kendall_tau_b(a[both], b[both])
    if not np.isfinite(tau):
        reasons.append("tau_b_undefined")
    elif tau < 1.0:
        reasons.append(f"tau_b_below_1={tau!r}")
    return {"tau_b": tau, "sign_flips": sign_flips, "material": bool(reasons),
            "reason": ";".join(reasons) if reasons else "none"}


# ---------------------------------------------------------------------------------------------- 載入與設定

_MODULES: Dict[str, Any] = {}


def _log(message: str) -> None:
    """進度行（卡住偵測以 log 增長判活）。"""
    print(f"[branchdiff {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {message}", flush=True)


def _load(name: str, path: Path) -> Any:
    if name not in _MODULES:
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
    return _load("numview_freeze_baseline_branchdiff", FREEZE_SCRIPT)


def _criteria() -> Dict[str, Any]:
    from tests.feature_engineering import numview_helpers as nh

    return json.loads(nh.current_criteria_path().read_text(encoding="utf-8"))


def _criteria_sha256() -> str:
    from tests.feature_engineering import numview_helpers as nh

    return hashlib.sha256(nh.current_criteria_path().read_bytes()).hexdigest()


def icpostleak_contract() -> Dict[str, Any]:
    return json.loads(ICPOSTLEAK_CONTRACT_PATH.read_text(encoding="utf-8"))


def combos() -> List[List[str]]:
    return [list(c) for c in icpostleak_contract()["combos"]]


def combo_name(steps: Sequence[str]) -> str:
    return "+".join(steps)


def branches_for_input(input_kind: str, criteria: Mapping[str, Any]) -> List[str]:
    """判準 v8 `comparison_outputs.postic_branch_vs_float64_oracle.branches_by_input` 之該輸入分支集合。"""
    spec = criteria["comparison_outputs"]["postic_branch_vs_float64_oracle"]["branches_by_input"][str(input_kind)]
    if "contract_branches" in spec:
        return sorted(set(icpostleak_contract()["branches"]) | set(spec.get("plus") or []))
    return sorted(spec["branches"])


def icpostleak_config(steps: Sequence[str], mode: str = "replace") -> Dict[str, Any]:
    """ICPOSTLEAK 之分支設定（同 `tests/feature_engineering/test_icpostleak.py::_config`；窗取該契約）。"""
    contract = icpostleak_contract()
    return {
        "enabled": True,
        "mode": mode,
        "causal_preprocessing": True,
        "winsorization": {"enabled": False},
        "fractional_differencing": {"enabled": False},
        "adf_differencing": {"enabled": False},
        "rank_transform": {"enabled": "rank" in steps, "window": int(contract["rank_window"]), "apply_to": "all"},
        "adaptive_zscore": {"enabled": "zscore" in steps, "windows": [int(w) for w in contract["zscore_windows"]],
                            "apply_to": "all"},
        "gaussian_normalize": {"enabled": "gaussian" in steps, "apply_to": "all"},
    }


def _sha256(values: np.ndarray) -> str:
    """判準 v8 `label_provenance.hash_rule`：sha256(C 連續原生位元組)。"""
    return hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()


def _bitwise_equal(a: np.ndarray, b: np.ndarray) -> bool:
    """形狀相同、NaN 遮罩相同、有限值之 float64 位元相同。"""
    x = np.asarray(a, dtype=np.float64)
    y = np.asarray(b, dtype=np.float64)
    if x.shape != y.shape or not np.array_equal(np.isnan(x), np.isnan(y)):
        return False
    keep = ~np.isnan(x)
    return bool(np.array_equal(x[keep].view(np.int64), y[keep].view(np.int64)))


# ---------------------------------------------------------------------------------------------- 輸入與標籤

def _utc_index(index: Any) -> Any:
    import pandas as pd

    idx = pd.DatetimeIndex(index)
    return idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")


def _source_frame(source: Path, symbol: str, tf: str) -> Any:
    """來源 h5 之 `<symbol>/<tf>/data` 全序列（UTC DatetimeIndex 升序、欄 float64）。"""
    import h5py
    import pandas as pd

    with h5py.File(str(source), "r") as handle:
        arr = handle[symbol][tf]["data"][()]
    stamps = arr["timestamp"].astype("int64")
    unit = "ms" if int(stamps.max()) > 10 ** 12 else "s"
    index = pd.to_datetime(stamps, unit=unit, utc=True)
    return pd.DataFrame({c: arr[c].astype(np.float64) for c in arr.dtype.names if c != "timestamp"}, index=index)


def input_i(cell: Mapping[str, Any], criteria: Mapping[str, Any]) -> Dict[str, Any]:
    """輸入 (i)：ICPOSTLEAK §G 輸入集建法（`test_icpostleak._real_frame`）套用於本格 symbol×tf；來源＝判準 `kline_source`。"""
    import talib

    symbol, tf = str(cell["symbol"]), str(cell["timeframes"][0])
    source = _estimate().kline_source(tf, criteria)
    k = icpostleak_contract()["kline"]
    rows = int(k["rows"])
    full = _source_frame(source, symbol, tf)
    if len(full) < rows:
        raise RuntimeError(f"{symbol}/{tf} 根數 {len(full)} < 輸入 (i) {rows}")
    base = full.iloc[:rows]
    frame = base[list(k["columns"])].astype(np.float64).copy()
    for spec in k["l1_features"]:
        args = [base[c].to_numpy(dtype=np.float64) for c in spec["inputs"]]
        frame[spec["name"]] = getattr(talib, spec["fn"])(*args, **spec["args"])
    late = frame[k["columns"][0]].copy()
    late.iloc[: int(k["late_born_nan_rows"])] = np.nan
    frame[k["late_born_column"]] = late
    return {"frame": frame, "close": base["close"].astype(np.float64), "source": source,
            "selected": [str(c) for c in frame.columns]}


def input_ii(cell: Mapping[str, Any], criteria: Mapping[str, Any]) -> Dict[str, Any]:
    """輸入 (ii)：凍結 run 之 IC-first 實際選欄經 IC 頁同一 ratio-unsafe 剔除後之 raw 欄（輸出段）。"""
    from momentum.factories import ratio_unsafe_category
    from momentum.FeatureEngineering.feature_library import FeatureLibrary
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from tests.feature_engineering import numview_helpers as nh
    from tests.feature_engineering.ffname_helpers import register_canonical_run

    work = FREEZE_RUNS / f"{cell['id']}__default"
    side = json.loads((work / "numview_cell.json").read_text(encoding="utf-8"))
    frozen = json.loads(nh.PRE_CHANGE_FINGERPRINTS_PATH.read_text(encoding="utf-8"))["cells"][str(cell["id"])]
    selected = [str(c) for c in side["ic_first_selected"]]
    if selected != [str(c) for c in frozen["ic_first_selected"]]:
        raise RuntimeError(f"{cell['id']}：凍結 run 之選欄與凍結檔不同")
    tf = str(cell["timeframes"][0])
    source = Path(side["source"])
    if source.resolve() != _estimate().kline_source(tf, criteria).resolve():
        raise RuntimeError(f"{cell['id']}：凍結 run 來源 {source} ≠ 判準 kline_source")
    run_dir = work / "features" / side["symbol"] / side["primary_tf"] / side["config_hash"]
    tmp = Path(tempfile.mkdtemp(prefix="numview_bd_reg_"))
    register_canonical_run(run_dir / "feature_manifest.json", tmp / "reg.json")
    root = work / "features"
    library = FeatureLibrary(FeatureRegistry(tmp / "reg.json"), FeatureStorage(str(root)),
                             feature_reader=FeatureReader(str(root)))
    df = library.load_canonical_path(str(run_dir / "feature_manifest.json"))
    kept = [c for c in dict.fromkeys(selected) if ratio_unsafe_category(c) is None]
    missing = [c for c in kept if c not in df.columns]
    if missing:
        raise RuntimeError(f"{cell['id']}：選欄不在 run：{missing[:5]}")
    frame = df[kept].astype(np.float64)
    frame.index = _utc_index(frame.index)
    full = _source_frame(source, str(cell["symbol"]), tf)
    close = full["close"].loc[frame.index[0]: frame.index[-1]]
    if not close.index.equals(frame.index):
        raise RuntimeError(f"{cell['id']}：輸出段時間軸與來源 close 不一致")
    return {"frame": frame, "close": close, "source": source, "selected": selected}


def label_from_close(close: Any) -> np.ndarray:
    """IC-first 同一構造（`feature_factory.py:2920`）：讀至輸出段終點之 close 之 `pct_change().shift(-1)`。"""
    return close.pct_change().shift(-1).to_numpy(dtype=np.float64)


def production_series(source: Path, symbol: str, tf: str, start: str, end: str, cell: Mapping[str, Any],
                      criteria: Mapping[str, Any]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """經生產 adapter（`create_feature_factory(cache_dir=來源目錄)._layer0_data_ingestion`）讀 [start, end]：
    （時間軸 int64 奈秒、close、標籤）。"""
    import pandas as pd

    from momentum.factories import create_feature_factory

    probe_cell = {"id": str(cell["id"]), "kind": str(cell["kind"]), "symbol": symbol, "timeframes": [tf]}
    continuity = _estimate().continuity_plan(probe_cell, criteria, [tf])
    factory = create_feature_factory(cache_dir=str(source.parent), validate_continuity=continuity["validate_continuity"])
    kline = factory._layer0_data_ingestion(symbol, tf, factory._resolve_config(None), start_date=start, end_date=end)
    index = factory._derive_row_index_for_artifact(kline)
    if index is None:
        raise RuntimeError(f"{symbol}/{tf}：生產 adapter 取不到時間軸")
    close = pd.Series(kline["close"].to_numpy(dtype=np.float64), index=index)
    return (np.asarray(index.asi8, dtype=np.int64), close.to_numpy(dtype=np.float64),
            close.pct_change().shift(-1).to_numpy(dtype=np.float64))


def label_provenance(cell_id: str, input_kind: str, cell: Mapping[str, Any], data: Mapping[str, Any],
                     label: np.ndarray, criteria: Mapping[str, Any]) -> Dict[str, Any]:
    """判準 v8 `label_provenance` 一筆：探針所用之時間軸／close／frame 索引／標籤之雜湊，及與生產 adapter 讀取逐值比對。"""
    from tests.feature_engineering import numview_helpers as nh

    symbol, tf = str(cell["symbol"]), str(cell["timeframes"][0])
    source = Path(data["source"])
    frame_ns = np.asarray(_utc_index(data["frame"].index).asi8, dtype=np.int64)
    close_ns = np.asarray(_utc_index(data["close"].index).asi8, dtype=np.int64)
    close = data["close"].to_numpy(dtype=np.float64)
    start = _utc_index(data["frame"].index)[0].isoformat()
    end = _utc_index(data["frame"].index)[-1].isoformat()
    prod_ns, prod_close, prod_label = production_series(source, symbol, tf, start, end, cell, criteria)
    equal = (np.array_equal(frame_ns, close_ns) and np.array_equal(close_ns, prod_ns)
             and _bitwise_equal(close, prod_close) and _bitwise_equal(label, prod_label))
    return {"cell_id": cell_id, "input": input_kind, "cache_dir": str(source.parent.resolve().relative_to(REPO)),
            "source_sha256": nh.kline_dataset_sha256(source, symbol, tf), "output_start": start, "output_end": end,
            "rows": int(frame_ns.size), "timestamp_sha256": _sha256(close_ns), "close_sha256": _sha256(close),
            "frame_index_sha256": _sha256(frame_ns), "label_sha256": _sha256(label), "production_adapter_equal": bool(equal)}


# ---------------------------------------------------------------------------------------------- 候選臂 polars_float64

def _rank_fn_float64(window: int) -> Callable[[Any], Any]:
    """`polars_adapter._make_rolling_pct_rank_fn` 之 float64 版（緩衝區與逐值寫入 float64；其餘逐字同）。"""
    from scipy.stats import rankdata as _rankdata

    _w = max(1, int(window))
    _min_periods = min(_w, max(20, _w // 4))

    def _fn(s: Any) -> Any:
        import polars as pl

        arr = s.to_numpy()
        n = len(arr)
        out = np.full(n, np.nan, dtype=np.float64)
        for i in range(n):
            curr = arr[i]
            if np.isnan(curr):
                continue
            start = max(0, i - _w + 1)
            w_data = arr[start: i + 1]
            valid = w_data[~np.isnan(w_data)]
            n_valid = len(valid)
            if n_valid < _min_periods:
                continue
            if np.all(valid == valid[0]):
                out[i] = 0.5
                continue
            ranks = _rankdata(valid, method="average")
            out[i] = ranks[-1] / n_valid
        return pl.Series(out).fill_nan(None)

    return _fn


_RANK_2D_FLOAT64: Dict[str, Any] = {}


def _rolling_rank_2d_float64(arr: np.ndarray, window: int, min_periods: int) -> np.ndarray:
    """`_numba_transforms._rolling_rank_numba` 之 float64 版（緩衝區與逐值寫入 float64；計數、常數窗 0.5、average 名次逐字
    同；探針內 numba 編譯，不改產品碼）。"""
    if "fn" not in _RANK_2D_FLOAT64:
        from numba import njit

        @njit(cache=False)
        def _rank(a: np.ndarray, w: int, mp: int) -> np.ndarray:
            n_rows, n_cols = a.shape
            out = np.empty((n_rows, n_cols), dtype=np.float64)
            out[:] = np.nan
            for c in range(n_cols):
                for r in range(n_rows):
                    val = a[r, c]
                    if np.isnan(val):
                        continue
                    start = max(0, r - w + 1)
                    count = 0
                    less = 0
                    equal = 0
                    for k in range(start, r + 1):
                        v = a[k, c]
                        if not np.isnan(v):
                            count += 1
                            if v < val:
                                less += 1
                            elif v == val:
                                equal += 1
                    if count < mp:
                        continue
                    if less == 0 and equal == count:
                        out[r, c] = 0.5
                    else:
                        out[r, c] = (less + (equal + 1.0) / 2.0) / count
            return out

        _RANK_2D_FLOAT64["fn"] = _rank
    return _RANK_2D_FLOAT64["fn"](np.ascontiguousarray(arr, dtype=np.float64), int(window), int(min_periods))


def _polars_to_pandas_float64(pl_df: Any, index: Any = None) -> Any:
    """`polars_adapter.polars_to_pandas` 之候選版：值保留 float64（產品版 `:166` 轉 float32；其餘逐字同）。"""
    import pandas as pd

    if pl_df.is_empty():
        pd_df = pd.DataFrame(columns=pl_df.columns, dtype=np.float64)
        if index is not None:
            pd_df.index = index
        return pd_df
    numpy_arr = pl_df.fill_null(float("nan")).to_numpy()
    pd_df = pd.DataFrame(data=numpy_arr.astype(np.float64, copy=False), columns=pl_df.columns, copy=False)
    if index is not None:
        pd_df.index = index
    return pd_df


def _candidate_fidelity(points: List[Tuple[str, str]]) -> None:
    """候選臂之數值保真自檢（審碼 r1 CODEX-R1-P1-01／GROK-R1-P1-01、P1-02：dtype 字串不足以證 Float64）：於已安裝之候選
    改動下，以需逾 float32 尾數之值（1＋2⁻⁴⁰）走 pandas→polars→pandas 往返與 `_polars_mask_columns`、以名次需逾 float32
    之窗（1/3）走 gaussian 內部 rank，逐位元等於 float64 期望者記 float64，否則記 float32。"""
    import pandas as pd

    from momentum.FeatureEngineering import polars_adapter as pa
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    fine = 1.0 + 2.0 ** -40
    frame = pd.DataFrame({"x": [fine, 2.0 * fine, 3.0 * fine, 4.0 * fine]})
    back = pa.polars_to_pandas(pa.pandas_to_polars(frame))["x"].to_numpy()
    points.append(("fidelity_roundtrip", "float64" if _bitwise_equal(back, frame["x"].to_numpy()) else "float32"))
    masked = pa.polars_to_pandas(FeaturePreprocessor._polars_mask_columns(
        pa.pandas_to_polars(frame), ["x"], frame[["x"]].to_numpy(dtype=np.float64), 2, frame.index))["x"].to_numpy()
    want = frame["x"].to_numpy().copy()
    want[:1] = np.nan
    points.append(("fidelity_mask", "float64" if _bitwise_equal(masked, want) else "float32"))
    ranks = np.asarray(FeaturePreprocessor._gaussian_2d(np.array([[3.0], [1.0], [2.0]]), 0.0, 1.0, causal=True,
                                                        window=3, min_periods=3), dtype=np.float64)
    from scipy.special import ndtri

    expected = ndtri(np.float64(2.0) / 3.0)  # 第 3 列：less=1、equal=1 ⇒ (1 + (1 + 1)/2) / 3 ＝ 2/3（float64 名次）
    points.append(("fidelity_gaussian_rank", "float64" if bool(ranks[2, 0] == expected) else "float32"))
    # zscore 表達式（審碼 b2 r2 三家列「未查」）：1＋k·2⁻³⁰ 於 float32 皆捨入為 1（常數窗 ⇒ 0），float64 則 z 為 O(1)；
    # 對 numpy float64 定義（窗 3、ddof 1、ε 0）之相對差 ≤ 1e-3 記 float64（float64 滾動和之捨入遠小於此、float32 則差 O(1)）
    z_in = pd.DataFrame({"x": [1.0 + k * 2.0 ** -30 for k in (0, 3, 1, 4, 2)]})
    z_out = pa.polars_to_pandas(pa.polars_l65_adaptive_zscore(pa.pandas_to_polars(z_in), columns=["x"], window=3,
                                                              epsilon=0.0))["x"].to_numpy(dtype=np.float64)
    x = z_in["x"].to_numpy(dtype=np.float64)
    want_z = np.array([(x[t] - x[max(0, t - 2): t + 1].mean()) / x[max(0, t - 2): t + 1].std(ddof=1)
                       for t in range(1, x.size)])
    ok = bool(np.all(np.abs(z_out[1:] - want_z) <= 1e-3 * np.maximum(1.0, np.abs(want_z))) and np.all(np.abs(want_z) > 0.1))
    points.append(("fidelity_zscore", "float64" if ok else "float32"))


def _gaussian_2d_float64(arr: np.ndarray, lower: float = 0.001, upper: float = 0.999, *, causal: bool = True,
                         window: int = 252, min_periods: int = 63) -> np.ndarray:
    """`FeaturePreprocessor._gaussian_2d` 之 float64 版（因果 rank 改 `_rolling_rank_2d_float64`、回傳不轉 float32；其餘
    逐字同）。"""
    import pandas as pd

    from momentum.FeatureEngineering.preprocessing import feature_preprocessor as fpm

    selected = pd.DataFrame(np.asarray(arr, dtype=np.float64))
    if causal:
        ranked_arr = _rolling_rank_2d_float64(selected.to_numpy(dtype=np.float64, copy=False), int(window), int(min_periods))
        ranked_df = pd.DataFrame(ranked_arr, index=selected.index, columns=selected.columns)
    else:
        ranked_df = selected.rank(pct=True)
        nunique = selected.nunique(dropna=True)
        constant_columns = nunique[nunique <= 1].index.tolist()
        if constant_columns:
            ranked_df.loc[:, constant_columns] = ranked_df.loc[:, constant_columns].where(
                selected.loc[:, constant_columns].isna(), 0.5)
    clipped = ranked_df.clip(lower=lower, upper=upper)
    gaussian_arr = fpm.ndtri(clipped.to_numpy(dtype=np.float64, copy=False))
    gaussian_arr[selected.isna().to_numpy()] = np.nan
    return gaussian_arr


def _install_candidate(mp: Any, points: List[Tuple[str, str]]) -> None:
    """候選臂 polars_float64（SPEC Task 1.1、R10-A／R11-A）：四處改動點（入口 `pandas_to_polars` Float64、rank
    `return_dtype` Float64、rank UDF 緩衝區與逐值寫入 float64、`_polars_mask_columns` 回包〔經入口 Float64〕）＋出口
    `polars_to_pandas` 保留 float64（遮罩、gaussian 入口與最終回傳皆經之；審碼 r1 GROK-R1-P1-01）＋gaussian 內部因果 rank
    float64、`_gaussian_2d` 回傳 float64（CODEX-R1-P1-01／GROK-R1-P1-02）；觀測點（rank 步輸出、每次遮罩後、zscore 輸入、
    gaussian 輸出之 dtype）與數值保真自檢（`_candidate_fidelity`：往返、遮罩、gaussian rank 逐位元對 float64 期望）記於
    `points`。"""
    import polars as pl

    from momentum.FeatureEngineering import polars_adapter as pa
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    real_to_polars = pa.pandas_to_polars
    real_mask = FeaturePreprocessor._polars_mask_columns
    real_zscore = pa.polars_l65_adaptive_zscore

    def to_polars(df: Any, *, use_float64: bool = False) -> Any:
        return real_to_polars(df, use_float64=True)

    def rank_transform(pl_df: Any, columns: List[str], window: int = 252) -> Any:
        valid = [c for c in columns if c in pl_df.columns]
        if not valid:
            return pl_df
        fn = _rank_fn_float64(window)
        out = pl_df.with_columns([pl.col(c).map_batches(fn, return_dtype=pl.Float64).alias(c) for c in valid])
        points.extend(("rank_output", str(out.schema[c])) for c in valid[:1])
        return out

    def mask(pl_df: Any, columns: List[str], step_input: np.ndarray, window: int, index: Any) -> Any:
        out = real_mask(pl_df, columns, step_input, window, index)
        points.extend(("after_mask", str(out.schema[c])) for c in columns[:1])
        return out

    def zscore(pl_df: Any, columns: List[str], window: int = 100, epsilon: float = 1e-8) -> Any:
        points.extend(("zscore_input", str(pl_df.schema[c])) for c in columns[:1] if c in pl_df.columns)
        return real_zscore(pl_df, columns=columns, window=window, epsilon=epsilon)

    def gaussian(arr: np.ndarray, lower: float = 0.001, upper: float = 0.999, *, causal: bool = True,
                 window: int = 252, min_periods: int = 63) -> np.ndarray:
        out = _gaussian_2d_float64(arr, lower, upper, causal=causal, window=window, min_periods=min_periods)
        points.append(("gaussian_output", str(out.dtype)))
        return out

    mp.setattr(pa, "pandas_to_polars", to_polars)
    mp.setattr(pa, "polars_to_pandas", _polars_to_pandas_float64)
    mp.setattr(pa, "polars_l65_rank_transform", rank_transform)
    mp.setattr(pa, "polars_l65_adaptive_zscore", zscore)
    mp.setattr(FeaturePreprocessor, "_polars_mask_columns", staticmethod(mask))
    mp.setattr(FeaturePreprocessor, "_gaussian_2d", staticmethod(gaussian))
    _candidate_fidelity(points)


# ---------------------------------------------------------------------------------------------- 分支執行

def run_branch(branch: str, steps: Sequence[str], frame: Any, tf: str, work: Path, *,
               points: Optional[List[Tuple[str, str]]] = None,
               routes: Optional[List[Dict[str, Any]]] = None, to_storage: bool = True) -> np.ndarray:
    """以分支 `branch` 跑一次生產轉換（ICPOSTLEAK `_run_branch` 同一執行：契約 env／entry／`patch_shard_bytes`／spy；
    registry 群組週期＝`tf`），回輸入欄序之 float64 陣列；候選臂輸出轉 float32（落盤前）再回 float64——`to_storage`＝False
    （同臂排名共用之中間結果；完整鏈中 rank 輸出不經落盤）⇒ 不轉。sink 分支之逐群組
    路由（`mode`、分片數、`requires_slow`、`is_chunked`、是否走分片串流、群組臂、狀態）附加於 `routes`。"""
    import pandas as pd
    import pytest

    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    contract_branches = icpostleak_contract()["branches"]
    spec = dict(contract_branches["polars" if branch == CANDIDATE_ARM else branch])
    columns = [str(c) for c in frame.columns]
    mp = pytest.MonkeyPatch()
    try:
        with _freeze()._clean_env(dict(spec.get("env", {}))):
            if branch == CANDIDATE_ARM:
                _install_candidate(mp, points if points is not None else [])
            pre = FeaturePreprocessor(icpostleak_config(steps))
            if spec["entry"] == "transform":
                out = pre.transform(frame.copy())[columns].to_numpy(dtype=np.float64)
                if branch == CANDIDATE_ARM and to_storage:
                    out = out.astype(np.float32).astype(np.float64)
                return out
            from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
            from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

            if "patch_shard_bytes" in spec:
                from momentum.FeatureEngineering.utils import hardware_utils

                mp.setattr(hardware_utils, "get_cgsa_shard_bytes", lambda: int(spec["patch_shard_bytes"]))
            calls: List[str] = []
            if spec.get("spy"):
                real = getattr(FeaturePreprocessor, spec["spy"])

                def _spy(self: Any, *args: Any, **kwargs: Any) -> Any:
                    calls.append(spec["spy"])
                    return real(self, *args, **kwargs)

                mp.setattr(FeaturePreprocessor, spec["spy"], _spy)
            slow: Dict[str, bool] = {}
            streamed: Set[str] = set()
            if branch in SINK_BRANCHES:
                real_slow = FeaturePreprocessor._group_requires_slow_transform

                def _slow(self: Any, group: Any, context: Any) -> bool:
                    result = real_slow(self, group, context)
                    slow[str(getattr(group, "group_id"))] = bool(result)
                    return result

                current_stream = getattr(FeaturePreprocessor, "_stream_sharded_group_to_sink")

                def _stream(self: Any, registry: Any, group: Any, *args: Any, **kwargs: Any) -> Any:
                    streamed.add(str(getattr(group, "group_id")))
                    return current_stream(self, registry, group, *args, **kwargs)

                mp.setattr(FeaturePreprocessor, "_group_requires_slow_transform", _slow)
                mp.setattr(FeaturePreprocessor, "_stream_sharded_group_to_sink", _stream)
            registry = ColumnGroupRegistry(work_dir=work / f"registry_{branch}_{'_'.join(steps)}_{time.time_ns()}")
            group = ColumnGroup(group_id=f"{tf}_L1_numview", layer=LayerSource.L1, timeframe=tf, data_source="close",
                                indicator="NUMVIEW", columns=tuple(columns), shape=(0, 0), dtype="float32",
                                disk_path=None)
            group = registry.save_data(group, frame.to_numpy(dtype=np.float32))
            if "patch_shard_bytes" in spec and not getattr(group, "shards", ()):
                raise RuntimeError(f"{branch}：前提不成立——群組未分片")
            if spec["entry"] == "transform_registry_groups":
                pre.transform_registry_groups(registry, n_workers=int(spec.get("n_workers", 1)))
                if spec.get("spy") and not calls:
                    raise RuntimeError(f"具名分支 {branch} 未執行 {spec['spy']}")
                return pd.DataFrame(registry.load_data(group.group_id), columns=columns).to_numpy(dtype=np.float64)
            parts: Dict[str, np.ndarray] = {}

            def _sink(group_id: Any, cols: Any, data: Any, source_group_id: Any, source_disk_path: Any,
                      cleanup_source: Any) -> None:
                arr = np.asarray(data, dtype=np.float64)
                for i, name in enumerate(cols):
                    parts[str(name)] = arr[:, i].copy()

            pre.transform_registry_groups_to_sink(registry, _sink, n_workers=1)
            if spec.get("spy") and not calls:
                raise RuntimeError(f"具名分支 {branch} 未執行 {spec['spy']}")
            if routes is not None:
                for gid, info in sorted(pre.execution_groups().items()):
                    arm = info.get("arm")
                    routes.append({"group_id": gid, "mode": pre.mode, "shards": len(getattr(group, "shards", ()) or ()),
                                   "requires_slow": slow.get(gid), "is_chunked": arm == "slow_chunked",
                                   "shard_stream": gid in streamed and arm == "numba_shard", "group_arm": arm,
                                   "status": info.get("status"),
                                   "group_bytes": int(len(frame)) * len(columns) * 4})
            missing = [c for c in columns if c not in parts]
            if missing:
                raise RuntimeError(f"{branch}：sink 缺欄 {missing[:5]}")
            return np.column_stack([parts[c] for c in columns]) if columns else np.empty((len(frame), 0))
    finally:
        mp.undo()


def branch_outputs(branch: str, frame: Any, tf: str, work: Path, *, points: List[Tuple[str, str]],
                   routes_by_combo: Dict[str, List[Dict[str, Any]]], check_shared: bool,
                   shared_checks: List[Dict[str, Any]], unit: Tuple[str, str]) -> Iterator[Tuple[str, np.ndarray]]:
    """分支之七組合輸出（同臂排名算一次：先跑 rank 單步得 R，含 rank 之組合以 R 為輸入跑其餘步驟）。`check_shared`：含 rank
    之組合另跑一次完整鏈，逐位元比對附於 `shared_checks`。"""
    import pandas as pd

    ranked: Optional[np.ndarray] = None
    for steps in combos():
        name = combo_name(steps)
        routes: List[Dict[str, Any]] = []
        if "rank" in steps:
            if ranked is None:
                ranked = run_branch(branch, ["rank"], frame, tf, work, points=points,
                                    routes=routes if steps == ["rank"] else [], to_storage=False)
            rest = [s for s in steps if s != "rank"]
            if rest:
                out = run_branch(branch, rest, pd.DataFrame(ranked, index=frame.index, columns=frame.columns), tf, work,
                                 points=points, routes=routes)
            else:
                out = ranked.astype(np.float32).astype(np.float64) if branch == CANDIDATE_ARM else ranked
                if branch in SINK_BRANCHES and not routes:
                    run_branch(branch, ["rank"], frame, tf, work, routes=routes)
            if check_shared and rest:
                full = run_branch(branch, steps, frame, tf, work, points=points)
                shared_checks.append({"cell_id": unit[0], "input": unit[1], "branch": branch, "combo": name,
                                      "bitwise_equal": _bitwise_equal(out, full)})
        else:
            out = run_branch(branch, steps, frame, tf, work, points=points, routes=routes)
        if branch in SINK_BRANCHES:
            routes_by_combo[name] = routes
        yield name, out


# ---------------------------------------------------------------------------------------------- 參照（逐欄多行程）

def _windowed_any(flags: np.ndarray, window: int) -> np.ndarray:
    """列 t 之窗 [t−w+1, t] 內有任一旗標 ⇒ True。"""
    cum = np.concatenate([[0], np.cumsum(flags.astype(np.int64))])
    t = np.arange(flags.size)
    return (cum[t + 1] - cum[np.maximum(0, t - window + 1)]) > 0


def _constant_rows(u: np.ndarray, window: int, min_count: int) -> np.ndarray:
    """常數窗約定格（SPEC Task 0.6 定義差異）：`u[t]` 有限、窗內有效值數 ≥ `min_count` 且逐一相等。"""
    out = np.zeros(u.size, dtype=bool)
    for t in range(u.size):
        if not np.isfinite(u[t]):
            continue
        w = u[max(0, t - window + 1): t + 1]
        valid = w[np.isfinite(w)]
        out[t] = valid.size >= min_count and bool(np.all(valid == valid[0]))
    return out


def _reference_column(args: Tuple[np.ndarray, int, int, int]) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """單欄之七組合參照輸出與定義差異格（共用 rank、gaussian 中間結果；順序 rank→gaussian→zscore）。"""
    from tests.feature_engineering import numview_reference as ref

    x, rank_w, gauss_w, z_w = args
    mp_r, mp_g = ref.min_periods_for(rank_w), ref.min_periods_for(gauss_w)

    def rank(u: np.ndarray, d: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        out = ref.mask_incomplete_window(ref.rolling_rank(u, rank_w, mp_r), u, rank_w)
        return out, (_constant_rows(u, rank_w, mp_r) | _windowed_any(d, rank_w)) & np.isfinite(out)

    def gauss(u: np.ndarray, d: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        out = ref.mask_incomplete_window(ref.gaussian(u, gauss_w, mp_g), u, gauss_w)
        return out, (_constant_rows(u, gauss_w, mp_g) | _windowed_any(d, gauss_w)) & np.isfinite(out)

    def zscore(u: np.ndarray, d: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        out = ref.mask_incomplete_window(ref.rolling_zscore_incremental(u, z_w, EPSILON), u, z_w)
        return out, (_constant_rows(u, z_w, 2) | _windowed_any(d, z_w)) & np.isfinite(out)

    none = np.zeros(x.size, dtype=bool)
    r = rank(x, none)
    g = gauss(x, none)
    gr = gauss(*r)
    return {"rank": r, "zscore": zscore(x, none), "gaussian": g, "rank+zscore": zscore(*r), "rank+gaussian": gr,
            "zscore+gaussian": zscore(*g), "rank+zscore+gaussian": zscore(*gr)}


def reference_outputs(values: np.ndarray, gauss_w: int, workers: int) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """七組合參照（n×c）與定義差異格（n×c bool）；窗取 ICPOSTLEAK 契約（zscore 主窗＝清單第一個），gaussian 窗＝`gauss_w`。"""
    import multiprocessing

    contract = icpostleak_contract()
    rank_w, z_w = int(contract["rank_window"]), int(contract["zscore_windows"][0])
    jobs = [(np.ascontiguousarray(values[:, j], dtype=np.float64), rank_w, gauss_w, z_w) for j in range(values.shape[1])]
    if workers > 1 and len(jobs) > 1:
        with multiprocessing.get_context("spawn").Pool(processes=workers) as pool:
            results = pool.map(_reference_column, jobs, chunksize=max(1, len(jobs) // (workers * 8)))
    else:
        results = [_reference_column(job) for job in jobs]
    names = [combo_name(c) for c in combos()]
    n = values.shape[0]
    return {name: (np.column_stack([r[name][0] for r in results]) if results else np.empty((n, 0)),
                   np.column_stack([r[name][1] for r in results]) if results else np.empty((n, 0), dtype=bool))
            for name in names}


# ---------------------------------------------------------------------------------------------- IC 與列

def spearman_ic(values: np.ndarray, label: np.ndarray) -> np.ndarray:
    """逐欄 Spearman IC（兩邊皆有限之列 ≥ 3；常數 ⇒ NaN）。"""
    from scipy.stats import rankdata

    out = np.full(values.shape[1], np.nan, dtype=np.float64)
    for j in range(values.shape[1]):
        m = np.isfinite(values[:, j]) & np.isfinite(label)
        if int(m.sum()) < 3:
            continue
        rx, ry = rankdata(values[m, j]), rankdata(label[m])
        if np.all(rx == rx[0]) or np.all(ry == ry[0]):
            continue
        out[j] = float(np.corrcoef(rx, ry)[0, 1])
    return out


def diff_row(reference: np.ndarray, definition: np.ndarray, output: np.ndarray, ic_ref: np.ndarray,
             label: np.ndarray, columns: int) -> Dict[str, Any]:
    """一列：浮點誤差（扣除定義差異格；兩邊同設 NaN）＋定義差異格＋全部格之格級差，IC 層判定。"""
    ref_f, out_f = reference.copy(), output.copy()
    ref_f[definition] = np.nan
    out_f[definition] = np.nan
    row: Dict[str, Any] = dict(cell_diff(ref_f, out_f))
    row["definition_cells"] = int(definition.sum())
    row["definition"] = (cell_diff(reference[definition], output[definition]) if definition.any()
                         else {"max_abs": None, "nan_mask_diff": 0})
    row["all_cells"] = cell_diff(reference, output)
    row["finite_cells"] = int(np.count_nonzero(np.isfinite(reference) & np.isfinite(output)))
    if columns < 1:
        row.update({"tau_b": None, "sign_flips": 0, "material": False, "material_reason": "zero_columns",
                    "ic_abs_delta_max": None, "ic_delta_over_se_max": None})
        return row
    if not np.isfinite(reference).any() and not np.isfinite(output).any():
        # 判準 v9 `material.identical_all_nan_verdict`：兩者皆全 NaN（例鏈之暖機總長 ≥ 輸入列數）⇒ 逐位元相同、無可比之格
        row.update({"tau_b": None, "sign_flips": 0, "material": False, "material_reason": "identical_all_nan",
                    "ic_abs_delta_max": None, "ic_delta_over_se_max": None})
        return row
    ic_out = spearman_ic(output, label)
    mat = ic_material(ic_ref.tolist(), ic_out.tolist())
    delta = np.abs(ic_out - ic_ref)
    n_eff = np.array([np.count_nonzero(np.isfinite(output[:, j]) & np.isfinite(label)) for j in range(output.shape[1])])
    over_se = delta * np.sqrt(np.maximum(n_eff, 1))
    row.update({"tau_b": None if not math.isfinite(mat["tau_b"]) else float(mat["tau_b"]),
                "sign_flips": int(mat["sign_flips"]), "material": bool(mat["material"]),
                "material_reason": mat["reason"],
                "ic_abs_delta_max": float(np.nanmax(delta)) if np.isfinite(delta).any() else None,
                "ic_delta_over_se_max": float(np.nanmax(over_se)) if np.isfinite(over_se).any() else None})
    return row


# ---------------------------------------------------------------------------------------------- 速度（IC 頁預設請求）

def _ic_page_config() -> Tuple[Any, List[int]]:
    from api.models.ic_models import ApplyTransformsRequest
    from api.services.ic_analysis_service import _normalize_zscore_windows
    from momentum.factories import create_post_ic_transform_config

    req = ApplyTransformsRequest(selected_features=["_"])
    windows = _normalize_zscore_windows(req.zscore_windows)
    return create_post_ic_transform_config(rank=req.rank, rank_window=req.rank_window, zscore=req.zscore,
                                           zscore_windows=windows, gaussian=req.gaussian), windows


def ic_page_seconds(arm: str, frame: Any, repeats: int = SPEED_REPEATS,
                    profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """IC 頁預設請求之轉換（`transform_selected`）於臂 `arm`（凍結腳本 `G1_ARM_ENV`；候選臂＝polars 環境＋候選改動）之
    牆鐘秒數 `repeats` 次與實際執行臂；`profile` 給定時另跑一次 Polars 逐步驟剖析（不計入秒數）。"""
    import pytest

    from momentum.factories import create_feature_preprocessor

    cfg, _ = _ic_page_config()
    env = dict(_freeze().G1_ARM_ENV["polars" if arm == CANDIDATE_ARM else arm])
    columns = [str(c) for c in frame.columns]
    if arm == "pandas_chunked" and len(columns) <= DEFAULT_CHUNK_SIZE:
        # 契約 pandas_chunked 可達條件「chunk_size > 0 且選欄數 > chunk_size」（feature_preprocessor.py:884）：預設 chunk
        # （`_resolve_column_chunk_size`，2000）下選欄數不足 ⇒ chunk 取選欄數之半，使該臂實際執行
        env["FFACT_L65_CHUNK_SIZE"] = str(max(1, len(columns) // 2))
    seconds: List[float] = []
    actual: Set[str] = set()
    for _ in range(repeats):
        mp = pytest.MonkeyPatch()
        try:
            with _freeze()._clean_env(env):
                if arm == CANDIDATE_ARM:
                    _install_candidate(mp, [])
                pre = create_feature_preprocessor(cfg.model_dump())
                t0 = time.perf_counter()
                pre.transform_selected(columns, {"ic_page": frame}, config=cfg)
                seconds.append(time.perf_counter() - t0)
                actual |= {str(g.get("arm")) for g in pre.last_post_ic_execution()[1].values()}
        finally:
            mp.undo()
        _log(f"  速度 {arm}：{seconds[-1]:.2f} 秒")
    if profile is not None:
        profile.update(polars_profile(frame, cfg))
    rounded = [round(s, 4) for s in seconds]
    return {"arm": arm, "seconds": rounded, "median_seconds": statistics.median(rounded), "actual_arms": sorted(actual)}


def reachable_arms(columns: int) -> List[str]:
    """契約 `post_ic_arm_values` 中選欄數達 `post_ic_arm_reachability.<臂>.min_selected_columns` 者（同驗收之可達條件）。"""
    from momentum.FeatureEngineering import numeric_view

    contract = numeric_view.load_contract()
    reach = contract["post_ic_arm_reachability"]
    return [a for a in contract["post_ic_arm_values"]["values"] if int(columns) >= int(reach[a]["min_selected_columns"])]


def polars_profile(frame: Any, cfg: Any) -> Dict[str, Any]:
    """Polars 臂慢因剖析（SPEC Task 1.1 效能基準）：IC 頁預設請求一次，逐步驟耗時（入口轉換、rank、遮罩、zscore、出口轉換）
    與 rank UDF 之呼叫次數、累計秒數——判明 rank 是否為逐欄 Python 迴圈（每欄一次 UDF 呼叫、UDF 內逐列迴圈）。"""
    import pytest

    from momentum.factories import create_feature_preprocessor
    from momentum.FeatureEngineering import polars_adapter as pa
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    steps: Dict[str, float] = {}
    udf = {"calls": 0, "seconds": 0.0, "rows_per_call": []}

    def timed(name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            t0 = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                steps[name] = steps.get(name, 0.0) + time.perf_counter() - t0
        return wrapper

    real_make = pa._make_rolling_pct_rank_fn

    def make(window: int) -> Callable[[Any], Any]:
        inner = real_make(window)

        def counted(s: Any) -> Any:
            t0 = time.perf_counter()
            try:
                return inner(s)
            finally:
                udf["calls"] += 1
                udf["seconds"] += time.perf_counter() - t0
                udf["rows_per_call"].append(len(s))
        return counted

    mp = pytest.MonkeyPatch()
    try:
        with _freeze()._clean_env(dict(_freeze().G1_ARM_ENV["polars"])):
            mp.setattr(pa, "_make_rolling_pct_rank_fn", make)
            for name in ("pandas_to_polars", "polars_to_pandas", "polars_l65_rank_transform", "polars_l65_adaptive_zscore"):
                mp.setattr(pa, name, timed(name, getattr(pa, name)))
            mp.setattr(FeaturePreprocessor, "_polars_mask_columns",
                       staticmethod(timed("_polars_mask_columns", FeaturePreprocessor._polars_mask_columns)))
            pre = create_feature_preprocessor(cfg.model_dump())
            t0 = time.perf_counter()
            pre.transform_selected([str(c) for c in frame.columns], {"ic_page": frame}, config=cfg)
            total = time.perf_counter() - t0
    finally:
        mp.undo()
    columns = int(frame.shape[1])
    rows = sorted(set(udf["rows_per_call"]))
    rank_wall = steps.get("polars_l65_rank_transform", 0.0)
    return {"total_seconds": round(total, 4), "step_seconds": {k: round(v, 4) for k, v in sorted(steps.items())},
            "rank_udf": {"calls": udf["calls"], "columns": columns, "rows_per_call": rows,
                         # Polars 並行呼叫 UDF（各呼叫之牆鐘含等待 GIL）⇒ 累計可大於總牆鐘；占比以 rank 步驟之牆鐘計
                         "cumulative_call_seconds": round(udf["seconds"], 4),
                         "rank_step_share_of_total": round(rank_wall / total, 4) if total else None,
                         "per_column_python_loop": bool(udf["calls"] == columns and rows == [int(frame.shape[0])])}}


# ---------------------------------------------------------------------------------------------- 單元（子行程）

def run_unit(cell: Mapping[str, Any], input_kind: str, work: Path, *, max_cols: Optional[int], workers: int,
             with_speed: bool) -> Dict[str, Any]:
    """一個 (格, 輸入) 之全部量測；回單元結果（收據之該 (格, 輸入) 各段）。"""
    import pandas as pd

    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    criteria = _criteria()
    symbol, tf = str(cell["symbol"]), str(cell["timeframes"][0])
    data = input_i(cell, criteria) if input_kind == "i" else input_ii(cell, criteria)
    frame = data["frame"]
    if max_cols is not None:
        frame = frame.iloc[:, :max_cols]
        data = dict(data, frame=frame)
    cell_id = f"i:{symbol}:{tf}" if input_kind == "i" else f"ii:{cell['kind']}:{symbol}:{tf}"
    unit = (cell_id, input_kind)
    columns = int(frame.shape[1])
    _log(f"{cell_id}：{columns} 欄 × {len(frame)} 列")
    label = label_from_close(data["close"])
    provenance = label_provenance(cell_id, input_kind, cell, data, label, criteria)
    gauss_w = int(FeaturePreprocessor(icpostleak_config(["gaussian"]))._rolling_window())
    t0 = time.perf_counter()
    reference = reference_outputs(frame.to_numpy(dtype=np.float64), gauss_w, workers) if columns else {}
    reference_seconds = time.perf_counter() - t0
    _log(f"{cell_id}：參照 {reference_seconds:.1f} 秒")
    ic_ref = {name: spearman_ic(ref_values, label) for name, (ref_values, _) in reference.items()}
    rows: List[Dict[str, Any]] = []
    sink_routes: List[Dict[str, Any]] = []
    sink_runs: List[Dict[str, Any]] = []
    points: List[Tuple[str, str]] = []
    shared_checks: List[Dict[str, Any]] = []
    kept_outputs: Dict[Tuple[str, str], np.ndarray] = {}
    branch_seconds: Dict[str, float] = {}
    check_shared = str(cell["id"]) == SHARED_RANK_CHECK_CELL
    with tempfile.TemporaryDirectory(prefix="numview_bd_", dir=str(work)) as tmp:
        for branch in branches_for_input(input_kind, criteria):
            tb = time.perf_counter()
            routes_by_combo: Dict[str, List[Dict[str, Any]]] = {}
            for name, out in branch_outputs(branch, frame, tf, Path(tmp), points=points, routes_by_combo=routes_by_combo,
                                            check_shared=check_shared, shared_checks=shared_checks, unit=unit):
                if columns:
                    ref_values, definition = reference[name]
                    row = diff_row(ref_values, definition, out, ic_ref[name], label, columns)
                else:
                    row = {**cell_diff(np.empty((len(frame), 0)), np.empty((len(frame), 0))), "definition_cells": 0,
                           "tau_b": None, "sign_flips": 0, "material": False, "material_reason": "zero_columns"}
                rows.append({"cell_id": cell_id, "input": input_kind, "branch": branch, "combo": name, "columns": columns,
                             **row})
                if input_kind == "i" and branch in ("legacy", "optimized", "polars", "registry", "registry_sink",
                                                    "registry_sink_sharded", "registry_parallel_split"):
                    kept_outputs[(branch, name)] = out
                _log(f"{cell_id}：{branch} {name} 完成")
            for name, routes in routes_by_combo.items():
                sink_runs.append({"cell_id": cell_id, "input": input_kind, "branch": branch, "combo": name,
                                  "group_ids": [r["group_id"] for r in routes]})
                sink_routes += [{"cell_id": cell_id, "input": input_kind, "branch": branch, "combo": name, **r}
                                for r in routes]
            branch_seconds[branch] = round(time.perf_counter() - tb, 3)
    reproduction: List[Dict[str, Any]] = []
    diff_of_diff: List[Dict[str, Any]] = []
    if input_kind == "i":
        old = json.loads(BRANCHDIFF_1002_PATH.read_text(encoding="utf-8")) if BRANCHDIFF_1002_PATH.is_file() else {"rows": []}
        old_rows = {(r["branch"], r["combo"]): r for r in old.get("rows") or []}
        icpl = icpostleak_contract()["kline"]
        for steps in combos():
            name = combo_name(steps)
            legacy = kept_outputs.get(("legacy", name))
            for branch in sorted({b for b, _ in kept_outputs}):
                out = kept_outputs[(branch, name)]
                both = np.isfinite(out) & np.isfinite(legacy)
                stats = {"diff_cells": int(np.count_nonzero(out[both] != legacy[both])),
                         "nan_mask_diff": int(np.count_nonzero(np.isnan(out) != np.isnan(legacy))),
                         "max_abs_diff": float(np.abs(out[both] - legacy[both]).max()) if both.any() else 0.0}
                if branch == "optimized" and symbol == icpl["symbol"] and tf == icpl["timeframe"]:
                    reproduction.append({"symbol": symbol, "timeframes": [tf], "input": "i", "combo": name, **stats})
                if symbol == icpl["symbol"] and tf == icpl["timeframe"] and (branch, name) in old_rows:
                    o = old_rows[(branch, name)]
                    diff_of_diff.append({"branch": branch, "combo": name, "old_diff_cells": o.get("diff_cells"),
                                         "new_diff_cells": stats["diff_cells"], "old_max_abs_diff": o.get("max_abs_diff"),
                                         "new_max_abs_diff": stats["max_abs_diff"],
                                         "old_nan_mask_diff": o.get("nan_position_mismatch_cells"),
                                         "new_nan_mask_diff": stats["nan_mask_diff"]})
    dtypes = sorted(set(points))
    speed: List[Dict[str, Any]] = []
    if with_speed and columns:
        for arm in reachable_arms(columns) + [CANDIDATE_ARM]:
            speed.append({"cell_id": cell_id, "input": input_kind, **ic_page_seconds(arm, frame)})
    return {"cell": {"cell_id": cell_id, "input": input_kind, "kind": str(cell["kind"]), "symbol": symbol,
                     "timeframes": [tf], "selected": list(data["selected"]), "columns": columns},
            "rows": rows, "label_provenance": [provenance], "sink_routes": sink_routes, "sink_runs": sink_runs,
            "candidate_intermediate_dtypes": [{"cell_id": cell_id, "input": input_kind, "point": p, "dtype": d}
                                              for p, d in dtypes],
            "speed": speed, "reproduction": reproduction, "diff_of_diff_1002": diff_of_diff,
            "shared_rank_check": shared_checks,
            "timing": {"cell_id": cell_id, "input": input_kind, "reference_seconds": round(reference_seconds, 3),
                       "branch_seconds": branch_seconds}}


def run_perf_unit(cell: Mapping[str, Any], work: Path, *, max_cols: Optional[int]) -> Dict[str, Any]:
    """獨立效能基準（判準 `run_coverage.perf_benchmark` 之格、輸入 (ii)）：各可達臂＋候選臂三次、Polars 慢因剖析。"""
    from momentum.FeatureEngineering import numeric_view

    data = input_ii(cell, _criteria())
    frame = data["frame"] if max_cols is None else data["frame"].iloc[:, :max_cols]
    columns = int(frame.shape[1])
    reachable = set(reachable_arms(columns))
    arms: Dict[str, Dict[str, Any]] = {}
    profile: Dict[str, Any] = {}
    for arm in list(numeric_view.load_contract()["post_ic_arm_values"]["values"]) + [CANDIDATE_ARM]:
        if arm != CANDIDATE_ARM and arm not in reachable:
            arms[arm] = {"reachable": False, "unreachable_reason": f"選欄數 {columns} 未達契約 min_selected_columns"}
            continue
        rec = ic_page_seconds(arm, frame, profile=profile if arm == "polars" else None)
        arms[arm] = {"reachable": True, "runs_seconds": rec["seconds"], "median_seconds": rec["median_seconds"],
                     "actual_arms": rec["actual_arms"]}
    steps = [{"step": name, "seconds": seconds} for name, seconds in (profile.get("step_seconds") or {}).items()]
    return {"input": {"cell": str(cell["id"]), "input": "ii", "columns": columns, "rows": int(len(frame)), "arms": arms},
            "polars_profile": {"steps": steps,
                               "rank_udf_per_column_python_loop": bool((profile.get("rank_udf") or {})
                                                                       .get("per_column_python_loop")),
                               **profile}}


# ---------------------------------------------------------------------------------------------- 主入口

def _branchdiff_cells(criteria: Mapping[str, Any], run_kind: str) -> List[Dict[str, Any]]:
    by_id = {str(c["id"]): c for c in criteria["cell_rules"]["cell_list"]["cells"]}
    return [{"id": str(r["cell"]), "kind": str(by_id[str(r["cell"])]["kind"]), "symbol": str(by_id[str(r["cell"])]["symbol"]),
             "timeframes": [str(t) for t in by_id[str(r["cell"])]["timeframes"]]}
            for r in criteria["run_coverage"][run_kind]["runs"]]


def _parse(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NUMVIEW Task 1.1 post-IC 分支差與效能基準")
    parser.add_argument("--perf", action="store_true", help="獨立效能基準（寫 perf-benchmark 收據）")
    parser.add_argument("--cells", default=None, help="只跑之格 id（逗號分隔；試跑用，須同給 --out）")
    parser.add_argument("--inputs", default="i,ii", help="只跑之輸入（試跑用，須同給 --out）")
    parser.add_argument("--max-cols", type=int, default=None, help="每格最多欄數（試跑用，須同給 --out）")
    parser.add_argument("--no-speed", action="store_true", help="略過速度（試跑用，須同給 --out）")
    parser.add_argument("--workers", type=int, default=max(1, min(6, (os.cpu_count() or 2) - 2)))
    parser.add_argument("--inline", action="store_true", help="單元於本行程執行（試跑用）")
    parser.add_argument("--out", default=None, help="收據輸出路徑（未給 ⇒ 正式收據）")
    parser.add_argument("--work-root", default=str(DEFAULT_WORK_ROOT))
    parser.add_argument("--child", default=None, help=argparse.SUPPRESS)
    return parser.parse_args(list(argv) if argv is not None else None)


def _child(spec_path: Path) -> int:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    work = Path(spec["work"])
    work.mkdir(parents=True, exist_ok=True)
    if spec["mode"] == "perf":
        result = run_perf_unit(spec["cell"], work, max_cols=spec["max_cols"])
    else:
        result = run_unit(spec["cell"], spec["input"], work, max_cols=spec["max_cols"], workers=int(spec["workers"]),
                          with_speed=bool(spec["with_speed"]))
    Path(spec["result_path"]).write_text(json.dumps(result, ensure_ascii=False, default=str), encoding="utf-8")
    return 0


def _run_units(specs: List[Dict[str, Any]], inline: bool) -> List[Dict[str, Any]]:
    """逐單元執行（預設子行程經卡住偵測；`inline` 於本行程）；任一失敗 ⇒ RuntimeError。"""
    results: List[Dict[str, Any]] = []
    wd = _watchdog()
    config = wd.load_config(_criteria())
    for spec in specs:
        result_path = Path(spec["result_path"])
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.unlink(missing_ok=True)
        if inline:
            _child_spec = result_path.with_suffix(".spec.json")
            _child_spec.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            _child(_child_spec)
        else:
            spec_path = result_path.with_suffix(".spec.json")
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            watched = wd.run_watched([sys.executable, str(Path(__file__).resolve()), "--child", str(spec_path)],
                                     log_path=result_path.with_suffix(".log"), config=config, cwd=str(REPO))
            if watched.status == wd.STALLED or watched.returncode != 0 or not result_path.is_file():
                raise RuntimeError(f"單元 {spec['label']}：{watched.status}（{watched.reason}；rc={watched.returncode}；"
                                   f"{watched.wall_seconds:.0f} 秒；見 {result_path.with_suffix('.log')}）")
        results.append(json.loads(result_path.read_text(encoding="utf-8")))
        _log(f"單元 {spec['label']} 完成")
    return results


def _common_header(command: Sequence[str]) -> Dict[str, Any]:
    return {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
            "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True).stdout.strip(),
            "command": " ".join(["venv/bin/python", "handoffs/run_receipts/numview_probes/postic_branchdiff.py", *command]),
            "criteria_sha256": _criteria_sha256()}


def main(argv: Optional[Sequence[str]] = None) -> int:
    """量測主入口；rc 0＝收據寫出且檢查全過（重現：BTCUSDT 1h 輸入 (i) 之 legacy 對 optimized 七組合皆 0 差；同臂排名
    共用之抽驗逐位元相等；標籤與生產讀取相等；候選臂中間 dtype 皆 float64；輸入 (i) 之 registry_sink_sharded 實走分片串流）；
    任一不符 ⇒ 收據 `exit_code`＝3、rc 3。試跑旗標（`--cells`／`--inputs`／`--max-cols`／`--no-speed`）須同給 `--out`。"""
    args = _parse(argv)
    if args.child:
        return _child(Path(args.child))
    trial = bool(args.cells or args.max_cols is not None or args.no_speed or args.inputs != "i,ii")
    if trial and not args.out:
        print("[branchdiff] 試跑旗標須同給 --out（不得寫正式收據）", file=sys.stderr)
        return 2
    criteria = _criteria()
    run_kind = "perf_benchmark" if args.perf else "postic_branchdiff"
    cells = _branchdiff_cells(criteria, run_kind)
    if args.cells:
        wanted = set(args.cells.split(","))
        cells = [c for c in cells if c["id"] in wanted]
    _gate().require(run_kind, [c["id"] for c in cells], receipts_dir=RECEIPTS_DIR)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    work = Path(args.work_root) / stamp
    inputs = [i for i in ("i", "ii") if i in set(args.inputs.split(","))]
    if args.perf:
        specs = [{"label": f"perf:{c['id']}", "mode": "perf", "cell": c, "max_cols": args.max_cols,
                  "work": str(work / f"perf_{c['id']}"), "result_path": str(work / "_results" / f"perf_{c['id']}.json")}
                 for c in cells]
    else:
        specs = [{"label": f"{i}:{c['id']}", "mode": "branchdiff", "cell": c, "input": i, "max_cols": args.max_cols,
                  "workers": args.workers, "with_speed": not args.no_speed, "work": str(work / f"{i}_{c['id']}"),
                  "result_path": str(work / "_results" / f"{i}_{c['id']}.json")} for c in cells for i in inputs]
    with _freeze()._clean_env({}):
        results = _run_units(specs, args.inline)
    header = _common_header(list(argv) if argv is not None else sys.argv[1:])
    if args.perf:
        from tests.feature_engineering import numview_helpers as nh

        receipt = {**header, "exit_code": 0, "inputs": [r["input"] for r in results],
                   "polars_profile": next((r["polars_profile"] for r in results if r["polars_profile"].get("steps")), {})}
        violations = [] if trial else nh.perf_benchmark_receipt_violations(receipt)
        receipt["format_violations"] = violations
        checks = {"format_ok": not violations,
                  "actual_arm_matches": all(
                      rec.get("actual_arms") == ["polars" if arm == CANDIDATE_ARM else arm]
                      for item in receipt["inputs"] for arm, rec in item["arms"].items() if rec.get("reachable"))}
        kind = "perf-benchmark"
    else:
        merged: Dict[str, List[Any]] = {k: [] for k in ("cells", "rows", "label_provenance", "sink_routes", "sink_runs",
                                                         "candidate_intermediate_dtypes", "speed", "reproduction",
                                                         "diff_of_diff_1002", "shared_rank_check")}
        timings = []
        for r in results:
            merged["cells"].append(r["cell"])
            timings.append(r["timing"])
            for key in merged:
                if key != "cells":
                    merged[key] += r[key]
        from momentum.FeatureEngineering.utils import hardware_utils

        with _freeze()._clean_env({}):
            production_shard_bytes = int(hardware_utils.get_cgsa_shard_bytes())
        ii_bytes = [int(e["group_bytes"]) for e in merged["sink_routes"] if e["input"] == "ii"]
        receipt = {**header, "exit_code": 0,
                   "reference": {"module": "tests/feature_engineering/numview_reference.py",
                                 "sha256": hashlib.sha256((REPO / "tests/feature_engineering/numview_reference.py")
                                                          .read_bytes()).hexdigest()},
                   "branches": sorted(set(icpostleak_contract()["branches"]) | {CANDIDATE_ARM}),
                   **merged, "sink_routes_summary": {"production_shard_bytes": production_shard_bytes,
                                                     "input_ii_group_bytes": max(ii_bytes) if ii_bytes else 0},
                   "definition_conventions": {"constant_window": {
                       "reference": "窗內有效值逐一相等", "pandas": "rolling.std(ddof=0) == 0.0（feature_preprocessor.py:4471）",
                       "polars": "窗內有效值逐一相等（polars_adapter.py:500）", "numba": "窗內有效值逐一相等（_numba_transforms.py:73）"}},
                   "timings": timings}
        icpl = icpostleak_contract()["kline"]
        checks = {
            "reproduction_zero_diff": all(
                r["diff_cells"] == 0 and r["nan_mask_diff"] == 0 and r["max_abs_diff"] == 0.0 for r in merged["reproduction"]),
            "shared_rank_bitwise": all(c["bitwise_equal"] for c in merged["shared_rank_check"]),
            "label_production_equal": all(e["production_adapter_equal"] for e in merged["label_provenance"]),
            "candidate_dtypes_float64": all(e["dtype"].lower() == "float64" for e in merged["candidate_intermediate_dtypes"]),
            "sharded_streamed_i": all(e["shard_stream"] is True for e in merged["sink_routes"]
                                      if e["branch"] == "registry_sink_sharded" and e["input"] == "i"),
            "speed_actual_arm_matches": all(
                e["actual_arms"] == ["polars" if e["arm"] == CANDIDATE_ARM else e["arm"]] for e in merged["speed"]),
        }
        if not trial:
            checks["reproduction_present"] = any(r["symbol"] == icpl["symbol"] for r in merged["reproduction"])
            checks["shared_rank_checked"] = bool(merged["shared_rank_check"])
        kind = "postic-branchdiff"
    receipt["checks"] = checks
    receipt["exit_code"] = 0 if all(checks.values()) else 3
    dest = Path(args.out) if args.out else RECEIPTS_DIR / f"{datetime.now().strftime('%Y%m%d')}-numview-{kind}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    _log(f"收據 {dest}；檢查 {checks}")
    return int(receipt["exit_code"])


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))

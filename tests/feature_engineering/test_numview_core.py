"""NUMVIEW Phase 3（docs/NUMVIEW_SPEC.md v13 Task 3.1／3.2／3.3）：正式核心處置之條件式驗收。

**分支選取（決定條件式；SPEC Task 3.1–3.3 之 ASSERT … WHEN 行）**：每個分支測試名恰含一個分支記號——
`postic_float64`（d_postic=polars_float64）、`postic_retained`（d_postic=retain）、`mtf_dtype`（d_mtf=unify）、
`mtf_retained`、`memmap_dtype`（d_memmap=decouple）、`memmap_retained`、`winsor_dtype`（d_winsor_dtype=unify；名不含
`winsor_dtype_retained`）、`winsor_dtype_retained`、`codec_by_provenance`（d_codec=provenance）、`codec_retained`、
`l2_unified`（d_l2=unify）、`l2_named`（d_l2=retain）；不依決定之測試含 `core_always` 且不含任何分支記號。
閘門以 `numview_helpers.core_selector()` 組 `-k "<所選記號> or core_always"`；`winsor_dtype` 為 `-k` 子字串，故須輸出
`(winsor_dtype and not winsor_dtype_retained)`。每個分支測試第一步呼叫 `_require_decision(key, value)`
（`numview_helpers.decision` 與本分支值不等 ⇒ 斷言紅；不 skip）。

**驗證（Task 3.1）**：
- postic_float64：(i) 獨立 numpy float64 oracle（rank→gaussian→zscore、窗未滿 NaN，本檔 `_chain_oracle`）與
  (ii) legacy pandas 臂兩路，對格 A 全部 symbol×tf 之 IC-first 實際選欄（生成時 spy 擷取之 post-IC 輸入、設定與輸出），
  正式臂輸出（落盤前回傳，轉 float32）≤1 ulp（`np.abs(out−f32(oracle)) ≤ np.abs(np.spacing(f32(oracle)))`，R2-C）
  且 NaN 遮罩 exact；中間 dtype spy（rank 步輸出、每次遮罩後、zscore 輸入皆 Polars Float64，R10-A）；rank 中間值
  對獨立 float64 rank 逐值 exact（含 ties 之非整數 rank）；端到端（R11-A／R12-A／R13-A）：ICPOSTLEAK 契約七組合，
  `transform_selected` 回傳每欄 float64，逐格 `np.abs(out−oracle) ≤ np.abs(np.spacing(np.float32(oracle)))/16`；
  每組合見證格數＝`np.isfinite(oracle) & (np.float32(oracle) != oracle)` 之計數，任一組合為 0 ⇒「oracle 覆蓋不足」紅；
  spy 觀測 `_gaussian_2d` 回傳與最終回傳 dtype；oracle 病態格（窗內 std 相對值 < 1e6×float64 eps）超界者須列於收據
  `ill_conditioned_cells`（不得靜默豁免）；落盤後 processed 之 dtype 與改前凍結逐欄相同、IC 頁 h5 為 float32；raw 逐位元
  不變；收據之記憶體／耗時比 ≤ 決定紀錄核可值。正、負、零三類 oracle 值與 NaN 遮罩格皆須出現於 1 ulp 比較中。
- postic_retained（R6-B）：IC-first processed 與 IC 頁 `polars` 臂份於 §G 全部已凍結格對改前凍結值逐位元相等
  （`values_native`，atol=0），另沿用 PRE-PROV `ic_first_default` 基準（legacy 相容比對）；Task 1.1 max_abs 只報告。

**驗證（Task 3.2）**：mtf_dtype（層出口 float32、格 B 主週期欄＝格 A 同欄逐位元、層出口對同層 float64 回傳 ≤1 ulp）／
mtf_retained（格 B raw 對凍結逐位元）；memmap_dtype（同輸入強制兩支輸出逐位元相等）／memmap_retained（格 A／B 之 L3／L4
欄對凍結逐位元）；winsor_dtype（sigma／quantile 回傳 dtype 相同、後續 fracdiff 對獨立 FFD 重算 ≤1 ulp）／
winsor_dtype_retained（格 A raw 對凍結逐位元＋sigma 分支回傳 float64 之現行行為）；codec_by_provenance（(i) 編碼型別
＝依讀回紀錄與契約映射表之獨立重算〔非欄名〕、讀回誤差在編碼容差內；(ii) 刪一筆／複製一筆／綁定四元改一值／步驟
狀態不在映射表 ⇒ 該欄 float32、registry 記異常結果、無任何有損欄；(iii) manifest `mapping_sha256`＝自讀回紀錄表依
契約正規化獨立重算、≠ `provenance.sha256`；紀錄檔寫畢後竄改 ⇒ 寫入失敗、run 不可讀為完整）／codec_retained（processed
對凍結逐位元＋codec 開時編碼仍依欄名）。

**驗證（Task 3.3）**：l2_unified（格 A＋格 B 之每次 L5／L6 以公開 L2 重算之輸出與實際輸出逐位元相等）／l2_named（Task 1.3
矩陣之 f32diff 重跑相等、非零格於契約 `l2_value_sources.nonzero_cells` 具名、L2／L5／L6 欄對凍結逐位元）。

**邊界**：28 core_always（3.1 邊界①窗內常數 ⇒ 0、同 legacy）；29 core_always（3.1 邊界②窗未滿 ⇒ NaN）；
30 memmap_dtype（3.2 邊界①門檻恰等與 ±1）；31 mtf_dtype（3.2 邊界②單一訓練週期）；32–34 codec_by_provenance
（3.2 邊界③④⑤）；35 core_always（3.3 邊界①`compute_all_polars` 拋錯之回退）；36 core_always（3.3 邊界②
`FFACT_USE_POLARS=0`）。35／36 之選記號理由：兩者之期望「L5／L6 所吃之 L2 與公開落盤之 L2 一致（或 run 具名失敗）」
於統一與具名保留兩決定下皆須成立（保留分支之已知差異只在 Polars 回傳表與公開表並存時；回退與 pandas 臂只有單一
來源），故不屬任一分支，記 `core_always`。

**mutation**（每個 SPEC 所列一案；名含對應記號）：見各 `test_mutation_*` docstring；Task 3.1 之 R2-C／R13-A 兩案以本檔
oracle 輔助函式為注入點。重型 mutation 一律只對第一個列舉格（偵測力證明；全格由正向驗證涵蓋）。

**測試接縫（實作須提供；名稱與簽名為本檔假設，見報告）**：
- `scripts/numview_freeze_baseline.py`：`generate_cell(root, cell, *, env=None) -> preprov_helpers.RunHandle`
  （`cell`＝全票唯一格描述子 `{id, kind, symbol, timeframes}`；格 A／B 之真實生成，同行程、隔離寫入、
  raw 與 processed 皆保留；與凍結腳本同一實作，故重生逐位元可比；`env` 覆寫生成環境）、
  `ic_page_output(handle, work) -> (DataFrame, dict)`（以 `ApplyTransformsRequest` 預設請求對該格 IC-first 選欄跑 IC 頁
  第三步，回 h5 讀回表與回應）。
- `handoffs/run_receipts/numview_probes/estimate.py:enumerate_cells` 回 `{A|B|C: [格描述子]}`，格描述子（全票唯一）＝
  `{id, kind, symbol, timeframes}`：A／C 之 `timeframes` 恰一項；B 依週期長度升冪、首項＝主週期、其餘＝訓練週期；
  `id`＝凍結檔 `cells` 之鍵。
- 凍結檔 `tests/_golden/numview/pre_change_fingerprints.json`：全票唯一正規形（`test_numview_baseline.py` 檔頭），本檔經
  `_frozen_view` 轉為檢視 `cells.<A|B>.<cell_id>.{processed, raw_polars, raw_pandas, raw, ic_page.<臂>}`；`cell_id`＝
  `numview_freeze_baseline.cell_key(kind, cell)`。
- D-CODEC 改案：`FeatureStorage.write_processed(..., post_ic_config=...)`（rank 窗來源）、
  `FeatureStorage._codec_mapping_from_execution(...)`（映射計算入口；codec 關時不得被呼叫）、
  `FeatureStorage._verify_codec_mapping_digest(record_path, mapping_sha256)`（讀回重算比對，不等即拋）；契約
  `processed_codec_mapping` 之 `mapping`（每項含三步驟狀態與 `encoding`）、`outcome_by_case`（missing／duplicate／
  stale／unknown／invalid_rank_window → 異常結果值）、`registry_keys`（`outcome`、`mapping_sha256`）、
  `normalization`（`sort_by`、`columns`）、`manifest_key`。
- D-L2 保留：契約新段 `l2_value_sources`（`nonzero_cells`）；Task 1.3 收據 `rows[*]`（`cell`、`timeframe`、`f32diff`）。
- 收據 `handoffs/run_receipts/*-numview-postic-core.json`（`cells.<key>` 之前後牆鐘與峰值、`ill_conditioned_cells`）；
  決定紀錄 `d_postic` 之 `approved_limits.{wall_time_ratio, peak_memory_ratio}`。

真實 kline（`data_cache/feature_klines/kline_cache.h5`）；格之生成每模組每格一次（`_Runs` 快取）。實作前應為紅；
不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import importlib.util
import inspect
import itertools
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd
import pytest

from momentum.factories import create_post_ic_transform_config
from momentum.FeatureEngineering import feature_factory as ff_mod
from momentum.FeatureEngineering import feature_storage as fs_mod
from momentum.FeatureEngineering import memmap_utils
from momentum.FeatureEngineering import numeric_view as nv
from momentum.FeatureEngineering import polars_adapter
from momentum.FeatureEngineering import run_provenance as rp_mod
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from tests.feature_engineering import ffstat_helpers as fsh
from tests.feature_engineering import numview_helpers as nh
from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.timeout(6 * 3600)

REPO = Path(__file__).resolve().parents[2]
ICPL = json.loads((REPO / "tests/_golden/icpostleak/contract.json").read_text(encoding="utf-8"))
COMBOS: List[Tuple[str, ...]] = [tuple(c) for c in ICPL["combos"]]
RANK_W = int(ICPL["rank_window"])
Z_WINDOWS: List[int] = [int(w) for w in ICPL["zscore_windows"]]
PROBES_DIR = REPO / "handoffs" / "run_receipts" / "numview_probes"
FREEZE_SCRIPT = REPO / "scripts" / "numview_freeze_baseline.py"

#: 決定值（SPEC Task 3.1–3.3 ASSERT … WHEN 行之字面）
D_POSTIC = ("d_postic", "polars_float64", "retain")
D_MTF = ("d_mtf", "unify", "retain")
D_MEMMAP = ("d_memmap", "decouple", "retain")
D_WINSOR = ("d_winsor_dtype", "unify", "retain")
D_CODEC = ("d_codec", "provenance", "retain")
D_L2 = ("d_l2", "unify", "retain")

#: 凍結檔之 artifact 鍵（見模組 docstring 之接縫）
FROZEN_PROCESSED, FROZEN_RAW_A, FROZEN_RAW_B, FROZEN_IC_PAGE = "processed", "raw_polars", "raw", "ic_page"
#: Task 3.1 收據與欄位（本檔定義之介面名，見報告）
POSTIC_CORE_RECEIPT_GLOB = "*-numview-postic-core.json"
L2_MATRIX_RECEIPT_GLOB = "*-numview-l2-arm-matrix.json"
#: SPEC Task 3.2 映射所列之三個 post-IC 步驟（`run_provenance.json` steps 之子集）
CODEC_STEPS = ("rank_transform", "adaptive_zscore", "gaussian_normalize")
CODEC_CASES = ("missing", "duplicate", "stale", "unknown")
LOSSY_ARROW_TYPES = ("int16", "uint16")
#: SPEC Task 3.1：oracle 病態格＝窗內 std 相對值 < float64 機器精度之 1e6 倍
ILL_CONDITIONED_REL_STD = 1e6 * float(np.finfo(np.float64).eps)
#: legacy pandas 臂之環境（ICPOSTLEAK 契約 branches.legacy；chunk 關以免走 pandas_chunked）
LEGACY_ENV = dict(ICPL["branches"]["legacy"]["env"], FFACT_L65_CHUNK_SIZE="0")


# ============================================================================================== 載入與決定

def _load_module(path: Path, name: str) -> Any:
    """以檔案路徑載入探針／腳本（非套件）；同名只載一次。"""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None and spec.loader is not None, f"無法載入 {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _freeze() -> Any:
    return _load_module(FREEZE_SCRIPT, "numview_freeze_baseline")


def _estimate() -> Any:
    return _load_module(PROBES_DIR / "estimate.py", "numview_probe_estimate")


def _l2_matrix() -> Any:
    return _load_module(PROBES_DIR / "l2_arm_matrix.py", "numview_probe_l2_arm_matrix")


def _require_decision(key: str, value: str) -> None:
    """分支測試之前置：決定紀錄 `key` 之選定處置須等於本分支值（fail-closed，不 skip）。"""
    got = nh.decision(key)
    assert got == value, f"決定紀錄 {key}={got!r}，本分支須為 {value!r}（gate 之 -k 選錯分支 ⇒ 紅）"


def _decision_record(key: str) -> Mapping[str, Any]:
    """決定紀錄 `key` 之整筆（讀 `DECISIONS_PATH`；`decisions` 為 {key: 紀錄} 或 [{key: …}]）。缺 ⇒ 紅。"""
    assert nh.DECISIONS_PATH.is_file(), f"決定紀錄不存在：{nh.DECISIONS_PATH}"
    data = json.loads(nh.DECISIONS_PATH.read_text(encoding="utf-8"))
    records = data.get("decisions")
    if isinstance(records, Mapping):
        record = records.get(key)
    else:
        record = next((r for r in (records or []) if isinstance(r, Mapping) and r.get("key") == key), None)
    assert isinstance(record, Mapping), f"決定紀錄缺 {key}"
    return record


def _latest_receipt(pattern: str) -> Dict[str, Any]:
    paths = sorted(nh.RECEIPTS_DIR.glob(pattern))
    assert paths, f"收據不存在：{nh.RECEIPTS_DIR}/{pattern}"
    return json.loads(paths[-1].read_text(encoding="utf-8"))


def _formal_arm() -> str:
    """post-IC 正式臂（契約 `post_ic_entries.ic_first`；不寫字面）。"""
    return nv.post_ic_arm("ic_first")


# ============================================================================================== 格列舉與凍結

def _cells(kind: str) -> List[Dict[str, Any]]:
    cells = _estimate().enumerate_cells(nh.KLINE_PATH)
    out = [dict(c) for c in cells[kind]]
    assert out, f"格 {kind} 列舉為空"
    return out


def _cell_key(kind: str, cell: Mapping[str, Any]) -> str:
    """格鍵＝全票唯一格描述子之 `id`（＝凍結檔 `cells` 之鍵）；`kind` 須與描述子一致。"""
    assert cell.get("kind") in (None, kind), f"格描述子 kind={cell.get('kind')!r} ≠ {kind}"
    assert isinstance(cell.get("id"), str) and cell["id"], f"格描述子缺 id：{dict(cell)}"
    return str(cell["id"])


def _kline_symbol_tfs() -> List[Tuple[str, str]]:
    """自 kline_cache.h5 列舉 symbol×tf（不寫死清單）。"""
    import h5py

    out: List[Tuple[str, str]] = []
    with h5py.File(nh.KLINE_PATH, "r") as handle:
        for symbol in sorted(handle.keys()):
            for tf in sorted(handle[symbol].keys()):
                if "data" in handle[symbol][tf]:
                    out.append((str(symbol), str(tf)))
    assert out, "kline_cache.h5 無任何 symbol×tf"
    return out


_FROZEN_CACHE: Dict[str, Any] = {}


def _frozen_view(doc: Mapping[str, Any]) -> Dict[str, Any]:
    """凍結檔正規形（全票唯一，`test_numview_baseline.py` 檔頭：`cells.<cell_id>.{kind, …, g1.<臂>.{env, actual_arm,
    fingerprint}, g2.{"0","1"}.{env, fingerprint}, g3.{raw, processed}}`）→ 本檔檢視 `cells.<A|B>.<cell_id>.{raw_polars
    〔g2."1"〕, raw_pandas〔g2."0"〕, raw〔g3.raw〕, processed〔g3.processed〕, ic_page.<臂>〔g1.<臂>.fingerprint〕}`。
    `cell_id`＝`numview_freeze_baseline.cell_key(kind, cell)` 之值（實作須一致）。正規形缺 `cells` 或格缺 `kind` ⇒ 紅。"""
    cells = doc.get("cells")
    assert isinstance(cells, Mapping) and cells, "§G 凍結檔無 cells"
    view: Dict[str, Dict[str, Any]] = {}
    for cell_id, cell in cells.items():
        assert isinstance(cell, Mapping) and cell.get("kind") in ("A", "B"), f"凍結格 {cell_id} 缺 kind"
        node: Dict[str, Any] = {}
        g2 = cell.get("g2") or {}
        if "1" in g2:
            node[FROZEN_RAW_A] = g2["1"]["fingerprint"]
        if "0" in g2:
            node["raw_pandas"] = g2["0"]["fingerprint"]
        g3 = cell.get("g3") or {}
        if "raw" in g3:
            node[FROZEN_RAW_B] = g3["raw"]
        if "processed" in g3:
            node[FROZEN_PROCESSED] = g3["processed"]
        g1 = cell.get("g1") or {}
        if g1:
            node[FROZEN_IC_PAGE] = {arm: copy_["fingerprint"] for arm, copy_ in g1.items() if not str(arm).startswith("_")}
        view.setdefault(str(cell["kind"]), {})[str(cell_id)] = node
    return {"cells": view}


def _frozen_doc() -> Dict[str, Any]:
    if "doc" not in _FROZEN_CACHE:
        assert nh.PRE_CHANGE_FINGERPRINTS_PATH.is_file(), f"§G 改前凍結不存在：{nh.PRE_CHANGE_FINGERPRINTS_PATH}"
        _FROZEN_CACHE["doc"] = _frozen_view(json.loads(nh.PRE_CHANGE_FINGERPRINTS_PATH.read_text(encoding="utf-8")))
    return _FROZEN_CACHE["doc"]


def _frozen_fp(kind: str, key: str, artifact: str, arm: Optional[str] = None) -> Mapping[str, Any]:
    node: Any = _frozen_doc().get("cells", {}).get(kind, {}).get(key, {})
    assert artifact in node, f"凍結檔缺 cells.{kind}.{key}.{artifact}"
    node = node[artifact]
    if arm is not None:
        assert arm in node, f"凍結檔缺 cells.{kind}.{key}.{artifact}.{arm}"
        node = node[arm]
    return node


def _column_bitwise_diff(before: Mapping[str, Any], after: Mapping[str, Any],
                         names: Optional[Iterable[str]] = None) -> List[str]:
    """逐欄逐位元差異（`numview_helpers.BITWISE_COLUMN_KEYS`）；`names` 給定時只比該子集（兩邊皆須有）。"""
    b_cols, a_cols = before["columns"], after["columns"]
    wanted = sorted(set(b_cols) | set(a_cols)) if names is None else sorted(names)
    out: List[str] = []
    for name in wanted:
        if name not in b_cols or name not in a_cols:
            out.append(f"{name}：欄只在一邊")
            continue
        for key in nh.BITWISE_COLUMN_KEYS:
            if b_cols[name].get(key) != a_cols[name].get(key):
                out.append(f"{name}.{key}")
    return out


def _layer_columns(run_dir: Path, layers: Sequence[str], artifact_kind: str = "raw") -> Set[str]:
    """manifest 宣告群組中，來源群組 id 第二段（層）屬 `layers` 之落盤欄名（同 `preprov_helpers.real_feature_frame`）。"""
    import pyarrow.parquet as pq

    manifest = ph.load_manifest(run_dir)
    out: Set[str] = set()
    for gid, info in manifest["artifacts"][artifact_kind]["groups"].items():
        source = str(info.get("source_group_id") or gid)
        parts = source.split("_")
        if len(parts) > 1 and parts[1] in layers:
            names = pq.read_schema(str(Path(run_dir) / str(info["path"]))).names
            out.update(n for n in names if n not in ph.NON_FEATURE_COLUMNS)
    return out


# ============================================================================================== 獨立 oracle（numpy float64）

def _min_periods(window: int) -> int:
    """L6.5 rolling min_periods 公式之獨立重寫：min(w, max(20, w // 4))。"""
    return min(int(window), max(20, int(window) // 4))


def _windows(x: np.ndarray, window: int) -> np.ndarray:
    """(n, window) 之因果窗視圖（前補 NaN）。"""
    from numpy.lib.stride_tricks import sliding_window_view

    pad = np.full(int(window) - 1, np.nan)
    return sliding_window_view(np.concatenate([pad, np.asarray(x, dtype=np.float64)]), int(window))


def _rank_oracle(x: np.ndarray, window: int) -> np.ndarray:
    """因果 pct rank（average 法）：NaN 輸入 ⇒ NaN；窗內有效數 < min_periods ⇒ NaN；窗內常數 ⇒ 0.5；
    其餘＝(less + (equal + 1)/2) / count（float64）。"""
    x = np.asarray(x, dtype=np.float64)
    out = np.full(x.shape, np.nan)
    if x.size == 0:
        return out
    win = _windows(x, window)
    valid = ~np.isnan(win)
    count = valid.sum(axis=1)
    cur = x[:, None]
    less = (win < cur).sum(axis=1)
    equal = (win == cur).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        ranks = (less + (equal + 1.0) / 2.0) / count
    ranks = np.where((less == 0) & (equal == count), 0.5, ranks)
    ok = ~np.isnan(x) & (count >= _min_periods(window))
    out[ok] = ranks[ok]
    return out


def _gaussian_oracle(x: np.ndarray, window: int, lower: float, upper: float) -> np.ndarray:
    """因果 rank（同上，窗＝gaussian 窗）→ clip → ndtri；輸入 NaN 處 NaN。"""
    from scipy.special import ndtri

    x = np.asarray(x, dtype=np.float64)
    with np.errstate(invalid="ignore"):
        g = ndtri(np.clip(_rank_oracle(x, window), lower, upper))
    g[np.isnan(x)] = np.nan
    return g


def _zscore_oracle(x: np.ndarray, window: int, epsilon: float) -> Tuple[np.ndarray, np.ndarray]:
    """因果 zscore（兩段式均值／樣本標準差 ddof=1，窗內只計有效值）：NaN 輸入 ⇒ NaN；有效數 < 2 或 std ≤ 0 ⇒ 0；
    其餘 (x − mean)/(std + ε)。回 (值, 病態格遮罩〔std>0 且 std < 1e6·eps·|mean|〕)。"""
    x = np.asarray(x, dtype=np.float64)
    win = _windows(x, window)
    valid = ~np.isnan(win)
    count = valid.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(valid, win, 0.0).sum(axis=1) / count
        dev = np.where(valid, win - mean[:, None], 0.0)
        std = np.sqrt((dev * dev).sum(axis=1) / (count - 1))
        z = (x - mean) / (std + float(epsilon))
    defined = count >= 2
    zero = ~defined | ~(std > 0)
    out = np.where(np.isnan(x), np.nan, np.where(zero, 0.0, z))
    ill = defined & (std > 0) & (std < ILL_CONDITIONED_REL_STD * np.abs(mean))
    return out, ill


def _mask_by_input(result: np.ndarray, step_input: np.ndarray, window: int) -> np.ndarray:
    """窗未滿遮罩（錨點＝步驟輸入首個有限值；`[0, first + window − 1)` 設 NaN；輸入全非有限 ⇒ 全 NaN）。"""
    out = np.array(result, dtype=np.float64, copy=True)
    finite = np.flatnonzero(np.isfinite(step_input))
    cut = out.shape[0] if finite.size == 0 else min(int(finite[0]) + int(window) - 1, out.shape[0])
    out[:cut] = np.nan
    return out


@dataclasses.dataclass(frozen=True)
class PostICSpec:
    rank: bool
    rank_window: int
    zscore: bool
    zscore_window: int
    epsilon: float
    gaussian: bool
    gaussian_window: int
    clip: Tuple[float, float]


def _config_dict(config: Any) -> Dict[str, Any]:
    raw = getattr(config, "preprocessing", config)
    if hasattr(raw, "model_dump"):
        raw = raw.model_dump()
    return copy.deepcopy(dict(raw or {}))


def _post_ic_spec(config: Any) -> PostICSpec:
    """post-IC 之步驟與窗（ICPOSTLEAK §C：rank／zscore 未設預設開、gaussian 預設關；zscore 主窗＝清單第一個；
    gaussian 窗＝縮尾窗 → rank 窗 → 252）。"""
    d = _config_dict(config)
    rank = dict(d.get("rank_transform") or {})
    zs = dict(d.get("adaptive_zscore") or {})
    ga = dict(d.get("gaussian_normalize") or {})
    winsor = dict(d.get("winsorization") or {})
    windows = [int(w) for w in zs.get("windows", [100, 252])]
    assert windows, "zscore 窗清單為空（SPEC D3 應已拒收）"
    clip = [float(v) for v in ga.get("clip_range", [0.001, 0.999])]
    return PostICSpec(
        rank=bool(rank.get("enabled", True)), rank_window=int(rank.get("window", 252)),
        zscore=bool(zs.get("enabled", True)), zscore_window=windows[0], epsilon=float(zs.get("epsilon", 1e-8)),
        gaussian=bool(ga.get("enabled", False)),
        gaussian_window=max(int(winsor.get("window", rank.get("window", 252))), 1), clip=(clip[0], clip[1]))


def _chain_oracle(values: np.ndarray, spec: PostICSpec) -> Tuple[np.ndarray, np.ndarray]:
    """rank→gaussian→zscore 逐欄獨立 float64 重算（每步窗未滿遮罩）；回 (值, 病態格遮罩)。"""
    x = np.asarray(values, dtype=np.float64)
    out = np.empty_like(x)
    ill = np.zeros(x.shape, dtype=bool)
    for j in range(x.shape[1]):
        v = x[:, j].copy()
        col_ill = np.zeros(v.shape, dtype=bool)
        if spec.rank:
            v = _mask_by_input(_rank_oracle(v, spec.rank_window), v, spec.rank_window)
        if spec.gaussian:
            v = _mask_by_input(_gaussian_oracle(v, spec.gaussian_window, *spec.clip), v, spec.gaussian_window)
        if spec.zscore:
            z, col_ill = _zscore_oracle(v, spec.zscore_window, spec.epsilon)
            v = _mask_by_input(z, v, spec.zscore_window)
            col_ill = col_ill & np.isfinite(v)
        out[:, j] = v
        ill[:, j] = col_ill
    return out, ill


def _ffd_weights(d: float, threshold: float) -> np.ndarray:
    """FFD 權重（López de Prado 固定寬窗遞迴；舊→新排列）。"""
    weights = [1.0]
    k = 1
    while True:
        nxt = -weights[-1] * (d - k + 1) / k
        if abs(nxt) < threshold:
            break
        weights.append(nxt)
        k += 1
    return np.asarray(weights[::-1], dtype=np.float64)


def _ffd_oracle(values: np.ndarray, d: float, threshold: float) -> np.ndarray:
    """FFD 獨立重算：首個有效值後之區間內前向填補、`np.convolve` valid 卷積；有效數 < 寬度 ⇒ 全 NaN。"""
    x = np.asarray(values, dtype=np.float64)
    weights = _ffd_weights(d, threshold)
    width = len(weights)
    out = np.full(x.shape, np.nan)
    valid = ~np.isnan(x)
    if valid.sum() < width:
        return out
    first = int(np.argmax(valid))
    tail = pd.Series(x[first:]).ffill().to_numpy(dtype=np.float64)
    if len(tail) < width:
        return out
    conv = np.convolve(tail, weights[::-1], mode="valid")
    out[first + width - 1: first + len(tail)] = conv
    return out


# ============================================================================================== 精度判定（R2-C／R12-A／R13-A）

def _ulp_ok(out32: np.ndarray, ref32: np.ndarray) -> np.ndarray:
    """1 ulp（SPEC §G R2-C）：`np.abs(out − ref) ≤ np.abs(np.spacing(ref))`（兩者 float32；差以 float64 計）。"""
    with np.errstate(invalid="ignore"):
        return (np.abs(out32.astype(np.float64) - ref32.astype(np.float64))
                <= np.abs(np.spacing(ref32)).astype(np.float64))


def _ulp_ok_without_abs(out32: np.ndarray, ref32: np.ndarray) -> np.ndarray:
    """mutant（R2-C）：上界去掉 `np.abs`（負數之 spacing 為負）。"""
    with np.errstate(invalid="ignore"):
        return (out32.astype(np.float64) - ref32.astype(np.float64)) <= np.spacing(ref32).astype(np.float64)


def _ulp_report(out: np.ndarray, oracle: np.ndarray) -> Dict[str, int]:
    """正式臂（轉 float32）對 float32(oracle) 之 1 ulp 判定：NaN 遮罩差、非有限不等、超界格數與正／負／零 oracle 格數。"""
    out32 = np.asarray(out, dtype=np.float64).astype(np.float32)
    ref32 = np.asarray(oracle, dtype=np.float64).astype(np.float32)
    nan_mismatch = np.isnan(out32) != np.isnan(ref32)
    inf_bad = (np.isinf(out32) | np.isinf(ref32)) & ~(out32 == ref32)
    finite = np.isfinite(out32) & np.isfinite(ref32)
    viol = finite & ~_ulp_ok(out32, ref32)
    return {"nan_mismatch": int(nan_mismatch.sum()), "nonfinite_bad": int(inf_bad.sum()), "violations": int(viol.sum()),
            "positive": int((finite & (ref32 > 0)).sum()), "negative": int((finite & (ref32 < 0)).sum()),
            "zero": int((finite & (ref32 == 0)).sum()), "nan_cells": int((np.isnan(ref32) & np.isnan(out32)).sum())}


def _witness_count(oracle: np.ndarray) -> int:
    """見證格數（R12-A／R13-A）：有限 oracle 值中非 float32 可精確表示者。"""
    o = np.asarray(oracle, dtype=np.float64)
    return int(np.count_nonzero(np.isfinite(o) & (o.astype(np.float32) != o)))


def _witness_count_without_isfinite(oracle: np.ndarray) -> int:
    """mutant（R13-A）：去掉 `np.isfinite`（NaN 與自身不等 ⇒ 被誤計為見證）。"""
    o = np.asarray(oracle, dtype=np.float64)
    return int(np.count_nonzero(o.astype(np.float32) != o))


def _coverage_violations(oracles: Mapping[str, Sequence[np.ndarray]]) -> List[str]:
    """每組合之見證格數（經模組層 `_witness_count`）；為 0 ⇒「oracle 覆蓋不足」。"""
    module = sys.modules[__name__]
    out: List[str] = []
    for combo, arrays in oracles.items():
        count = sum(module._witness_count(a) for a in arrays)
        if count == 0:
            out.append(f"{combo}：oracle 覆蓋不足（見證格 0）")
    return out


def _spacing16_violations(out: np.ndarray, oracle: np.ndarray) -> np.ndarray:
    """端到端（R11-A）：`np.abs(out − oracle) > np.abs(np.spacing(np.float32(oracle))) / 16` 之有限格。"""
    o = np.asarray(oracle, dtype=np.float64)
    x = np.asarray(out, dtype=np.float64)
    finite = np.isfinite(o) & np.isfinite(x)
    with np.errstate(invalid="ignore"):
        bound = np.abs(np.spacing(o.astype(np.float32))).astype(np.float64) / 16.0
        return finite & (np.abs(x - o) > bound)


# ============================================================================================== 生成與擷取（spy）

@dataclasses.dataclass
class PostICCall:
    selected: List[str]
    frame: pd.DataFrame
    config: Any
    arm: Optional[str]
    output: pd.DataFrame
    groups: Dict[str, Dict[str, Any]]
    records: Dict[Tuple[str, str], Dict[str, Any]]


@dataclasses.dataclass
class LayerExit:
    instance: int
    tf: str
    calibration: bool
    layer: str
    preserve_dtype: bool
    dtypes: Tuple[str, ...]
    ulp_violations: int
    compared: int


@dataclasses.dataclass
class L2Use:
    instance: int
    tf: str
    calibration: bool
    layer: str
    l2_columns: int
    output_columns: int
    missing_public: Tuple[str, ...]
    extra_public: Tuple[str, ...]
    recomputed_equal: bool


@dataclasses.dataclass
class CellRun:
    kind: str
    cell: Dict[str, Any]
    key: str
    handle: Any = None
    post_ic: List[PostICCall] = dataclasses.field(default_factory=list)
    exits: List[LayerExit] = dataclasses.field(default_factory=list)
    l2_use: List[L2Use] = dataclasses.field(default_factory=list)
    l2_arms: List[Tuple[str, pd.DataFrame, pd.DataFrame]] = dataclasses.field(default_factory=list)
    compute_all_polars_calls: int = 0
    public: Dict[Tuple[int, str], List[Tuple[pd.DataFrame, pd.DataFrame]]] = dataclasses.field(default_factory=dict)


def _layer_data(result: Any) -> pd.DataFrame:
    data = getattr(result, "data", result)
    return data if isinstance(data, pd.DataFrame) else pd.DataFrame()


def _frames_identical(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    """欄序、形狀、逐欄 dtype 與位元組（NaN 位置）全同。"""
    if list(map(str, a.columns)) != list(map(str, b.columns)) or a.shape != b.shape:
        return False
    return all(ph.bitwise_equal(a.iloc[:, i].to_numpy(), b.iloc[:, i].to_numpy()) for i in range(a.shape[1]))


def _ctx(factory: Any) -> Tuple[int, str, bool]:
    return id(factory), str(getattr(factory, "_current_timeframe", None)), bool(getattr(factory, "_calibration_domain", False))


def _l2_use(run: CellRun, factory: Any, layer: str, layer2: Any, result: Any,
            recompute: Callable[[pd.DataFrame], Any]) -> L2Use:
    """L5／L6 一次呼叫：所吃之 L2 與同實例同週期之公開 L2（`_persist_layer2_category_group` 所落者）比對，並以公開 L2
    重算該層、與實際輸出逐位元比。"""
    inst, tf, calib = _ctx(factory)
    l2 = layer2 if isinstance(layer2, pd.DataFrame) else pd.DataFrame()
    frames = [coerced for _raw, coerced in run.public.get((inst, tf), [])]
    public = pd.concat(frames, axis=1) if frames else pd.DataFrame(index=l2.index)
    l2_names = [str(c) for c in l2.columns]
    pub_names = [str(c) for c in public.columns]
    missing = tuple(c for c in l2_names if c not in pub_names)
    extra = tuple(sorted(set(pub_names) - set(l2_names)))
    out = _layer_data(result)
    equal = False
    if not missing:
        pub = public.loc[:, ~public.columns.duplicated(keep="first")]
        pub = pub.loc[:, list(l2.columns)].copy()
        if len(pub.index) == len(l2.index):
            pub.index = l2.index
        equal = _frames_identical(out, _layer_data(recompute(pub)))
    return L2Use(inst, tf, calib, layer, len(l2_names), int(out.shape[1]), missing, extra, equal)


def _install_spies(mp: pytest.MonkeyPatch, run: CellRun) -> None:
    """生成期間之觀測器（只記錄、原樣轉呼叫）：post-IC 呼叫、L1–L6 層出口 dtype、L2 公開落盤、L5／L6 所吃之 L2、
    `compute_all_polars` 呼叫數。"""
    FF = ff_mod.FeatureFactory

    real_ts = FeaturePreprocessor.transform_selected

    def ts_spy(self: Any, selected: Any, groups: Any, config: Any = None, *args: Any, **kwargs: Any) -> Any:
        names = [str(c) for c in selected]
        parts = [g.loc[:, [c for c in names if c in g.columns]] for g in (groups or {}).values()
                 if isinstance(g, pd.DataFrame)]
        parts = [p for p in parts if p.shape[1]]
        frame = pd.concat(parts, axis=1).copy() if parts else pd.DataFrame()
        out = real_ts(self, selected, groups, config, *args, **kwargs)
        merged = pd.concat(list(out.values()), axis=1).copy() if out else pd.DataFrame(index=frame.index)
        records, exec_groups = self.last_post_ic_execution()
        run.post_ic.append(PostICCall(names, frame, copy.deepcopy(config), kwargs.get("arm"), merged,
                                      dict(exec_groups), dict(records)))
        return out

    mp.setattr(FeaturePreprocessor, "transform_selected", ts_spy)

    real_exec = FF._execute_layer1_6

    def exec_spy(self: Any, layer_name: str, func: Callable, *args: Any, preserve_dtype: bool = False) -> Any:
        captured: Dict[str, Any] = {}

        def wrapped(*a: Any) -> Any:
            captured["raw"] = func(*a)
            return captured["raw"]

        result = real_exec(self, layer_name, wrapped, *args, preserve_dtype=preserve_dtype)
        data = _layer_data(result)
        raw = _layer_data(captured.get("raw"))
        violations = compared = 0
        if not data.empty and list(map(str, raw.columns)) == list(map(str, data.columns)) and raw.shape == data.shape:
            ref = raw.to_numpy(dtype=np.float64)
            rep = _ulp_report(data.to_numpy(dtype=np.float64), ref)
            violations = rep["violations"] + rep["nan_mismatch"] + rep["nonfinite_bad"]
            compared = int(np.isfinite(ref).sum())
        inst, tf, calib = _ctx(self)
        run.exits.append(LayerExit(inst, tf, calib, str(layer_name), bool(preserve_dtype),
                                   tuple(sorted({str(t) for t in data.dtypes})) if not data.empty else (),
                                   violations, compared))
        return result

    mp.setattr(FF, "_execute_layer1_6", exec_spy)

    real_persist = FF._persist_layer2_category_group

    def persist_spy(self: Any, category: str, frame: pd.DataFrame) -> Any:
        if (getattr(self, "_cgsa_registry", None) is not None and getattr(self, "_current_timeframe", None)
                and frame is not None and not frame.empty):
            inst, tf, _calib = _ctx(self)
            run.public.setdefault((inst, tf), []).append((frame.copy(), self._coerce_persistence_frame(frame).copy()))
        return real_persist(self, category, frame)

    mp.setattr(FF, "_persist_layer2_category_group", persist_spy)

    real_l2 = FF._layer2_derived_features

    def l2_spy(self: Any, layer1: Any, data: Any, config: Any) -> Any:
        inst, tf, calib = _ctx(self)
        before = len(run.public.get((inst, tf), []))
        result = real_l2(self, layer1, data, config)
        new = run.public.get((inst, tf), [])[before:]
        returned = _layer_data(result)
        if new and not returned.empty and not calib:
            run.l2_arms.append((tf, returned.copy(), pd.concat([raw for raw, _c in new], axis=1)))
        return result

    mp.setattr(FF, "_layer2_derived_features", l2_spy)

    real_l5 = FF._layer5_cross_sectional

    def l5_spy(self: Any, layer1: Any, layer2: Any, config: Any) -> Any:
        result = real_l5(self, layer1, layer2, config)
        run.l2_use.append(_l2_use(run, self, "L5", layer2, result, lambda pub: real_l5(self, layer1, pub, config)))
        return result

    mp.setattr(FF, "_layer5_cross_sectional", l5_spy)

    real_l6 = FF._layer6_meta_features

    def l6_spy(self: Any, layer1: Any, layer2: Any, data: Any, config: Any) -> Any:
        result = real_l6(self, layer1, layer2, data, config)
        run.l2_use.append(_l2_use(run, self, "L6", layer2, result,
                                  lambda pub: real_l6(self, layer1, pub, data, config)))
        return result

    mp.setattr(FF, "_layer6_meta_features", l6_spy)

    engine_cls = ff_mod._derived_operator_engine_cls()
    real_cap = engine_cls.compute_all_polars

    def cap_spy(self: Any, *args: Any, **kwargs: Any) -> Any:
        run.compute_all_polars_calls += 1
        return real_cap(self, *args, **kwargs)

    mp.setattr(engine_cls, "compute_all_polars", cap_spy)


Patch = Callable[[pytest.MonkeyPatch, CellRun], None]
_GEN_COUNTER = itertools.count()


def _generate(root: Path, kind: str, cell: Mapping[str, Any], *, env: Optional[Mapping[str, str]] = None,
              patches: Sequence[Patch] = ()) -> CellRun:
    """單格真實生成（接縫 `generate_cell`）；觀測器先裝、mutant patch 後裝（故觀測器看得到 mutant 之效果）。"""
    run = CellRun(kind=kind, cell=dict(cell), key=_cell_key(kind, cell))
    work = Path(root) / f"{kind}_{run.key}_{next(_GEN_COUNTER)}"
    mp = pytest.MonkeyPatch()
    try:
        _install_spies(mp, run)
        for patch in patches:
            patch(mp, run)
        run.handle = _freeze().generate_cell(work, {**dict(cell), "kind": kind}, env=dict(env) if env else None)
    finally:
        mp.undo()
    return run


class _Runs:
    """模組範圍之格倉：同 (kind, cell_key) 只生成一次（mutation 一律另起根、不經本倉）。"""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._cache: Dict[Tuple[str, str], CellRun] = {}

    def get(self, kind: str, cell: Mapping[str, Any]) -> CellRun:
        key = (kind, _cell_key(kind, cell))
        if key not in self._cache:
            self._cache[key] = _generate(self.root, kind, cell)
        return self._cache[key]

    def all(self, kind: str) -> List[CellRun]:
        return [self.get(kind, cell) for cell in _cells(kind)]

    def first(self, kind: str) -> CellRun:
        return self.get(kind, _cells(kind)[0])


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> _Runs:
    return _Runs(tmp_path_factory.mktemp("numview_core_runs"))


def _ic_first_call(run: CellRun) -> PostICCall:
    """該格 IC-first 之 post-IC 呼叫（恰一次；臂＝契約正式臂且群組臂紀錄皆為該臂）。"""
    calls = [c for c in run.post_ic if c.arm is not None]
    assert len(calls) == 1, f"{run.key}：IC-first post-IC 呼叫應恰一次，實得 {len(calls)}"
    call = calls[0]
    arm = _formal_arm()
    assert call.arm == arm, f"{run.key}：post-IC 臂 {call.arm!r} ≠ 契約 {arm!r}"
    assert all(info.get("arm") == arm for info in call.groups.values()), (run.key, call.groups)
    return call


def _effective_post_ic_dict(config: Any) -> Dict[str, Any]:
    """post-IC 之有效前處理設定（replace、縮尾／fracdiff／ADF 關；rank／zscore 未設預設開、gaussian 預設關）。"""
    d = _config_dict(config)
    d["enabled"] = True
    d["mode"] = "replace"
    for step in ("winsorization", "fractional_differencing", "adf_differencing"):
        d[step] = dict(d.get(step) or {}, enabled=False)
    for step, default in (("rank_transform", True), ("adaptive_zscore", True), ("gaussian_normalize", False)):
        sub = dict(d.get(step) or {})
        d[step] = dict(sub, enabled=bool(sub.get("enabled", default)), apply_to="all")
    return d


def _legacy_arm(frame: pd.DataFrame, config: Any) -> pd.DataFrame:
    """(ii) legacy pandas 臂：同有效設定、`FFACT_USE_POLARS=0`＋legacy profile（chunk 關），斷言實際臂為 pandas_legacy。"""
    legacy_arm = "pandas_legacy"
    assert legacy_arm in ph.contract_values("group_arm_values"), "SPEC 點名之 pandas_legacy 不在 run_provenance 臂值集"
    mp = pytest.MonkeyPatch()
    try:
        for key, value in LEGACY_ENV.items():
            mp.setenv(key, value)
        pre = FeaturePreprocessor(_effective_post_ic_dict(config))
        out = pre.transform(frame.copy())
        arms = {str(info.get("arm")) for info in pre.execution_groups().values()}
    finally:
        mp.undo()
    assert legacy_arm in arms, f"legacy oracle 未走 pandas_legacy（實得 {arms}）"
    return out


def _combo_config(combo: Sequence[str]) -> Any:
    return create_post_ic_transform_config(rank="rank" in combo, rank_window=RANK_W, zscore="zscore" in combo,
                                           zscore_windows=list(Z_WINDOWS), gaussian="gaussian" in combo)


# ============================================================================================== 正式臂內部 spy 與端到端

@dataclasses.dataclass
class Internals:
    rank: List[Tuple[Dict[str, str], np.ndarray, np.ndarray, int]] = dataclasses.field(default_factory=list)
    mask: List[Dict[str, str]] = dataclasses.field(default_factory=list)
    zscore_in: List[Dict[str, str]] = dataclasses.field(default_factory=list)
    gaussian_out: List[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class E2E:
    cell: str
    combo: Tuple[str, ...]
    columns: List[str]
    out: np.ndarray
    out_dtypes: Dict[str, str]
    oracle: np.ndarray
    ill: np.ndarray
    internals: Internals


def _install_internal_spies(mp: pytest.MonkeyPatch, rec: Internals) -> None:
    """正式臂四處邊界之觀測（R10-A／R11-A）：rank 步輸出（含輸入）、每次遮罩後、zscore 輸入之 Polars dtype，
    `_gaussian_2d` 回傳 dtype。只記錄、原樣轉呼叫（裝於 mutant 之後 ⇒ 觀測 mutant 之效果）。"""
    real_rank = polars_adapter.polars_l65_rank_transform

    def rank_spy(pl_df: Any, columns: Any, window: int = 252, **kwargs: Any) -> Any:
        cols = [c for c in columns if c in pl_df.columns]
        inp = np.asarray(pl_df.select(cols).to_numpy(), dtype=np.float64) if cols else np.empty((pl_df.height, 0))
        out = real_rank(pl_df, columns=columns, window=window, **kwargs)
        res = np.asarray(out.select(cols).to_numpy(), dtype=np.float64) if cols else np.empty((out.height, 0))
        rec.rank.append(({c: str(out.schema[c]) for c in cols}, inp, res, int(window)))
        return out

    mp.setattr(polars_adapter, "polars_l65_rank_transform", rank_spy)

    real_mask = FeaturePreprocessor._polars_mask_columns

    def mask_spy(pl_df: Any, columns: Any, *args: Any, **kwargs: Any) -> Any:
        out = real_mask(pl_df, columns, *args, **kwargs)
        rec.mask.append({c: str(out.schema[c]) for c in columns})
        return out

    mp.setattr(FeaturePreprocessor, "_polars_mask_columns", staticmethod(mask_spy))

    real_z = polars_adapter.polars_l65_adaptive_zscore

    def z_spy(pl_df: Any, columns: Any, *args: Any, **kwargs: Any) -> Any:
        rec.zscore_in.append({c: str(pl_df.schema[c]) for c in columns if c in pl_df.columns})
        return real_z(pl_df, columns, *args, **kwargs)

    mp.setattr(polars_adapter, "polars_l65_adaptive_zscore", z_spy)

    real_g = FeaturePreprocessor._gaussian_2d

    def g_spy(*args: Any, **kwargs: Any) -> Any:
        out = real_g(*args, **kwargs)
        rec.gaussian_out.append(str(np.asarray(out).dtype))
        return out

    mp.setattr(FeaturePreprocessor, "_gaussian_2d", staticmethod(g_spy))


#: mutant 規格＝(被測物件, 屬性名, 工廠)：以 `monkeypatch.setattr(物件, 屬性, 工廠(原屬性))` 注入
Mutant = Tuple[Any, str, Callable[[Any], Any]]


def _apply_mutants(mp: pytest.MonkeyPatch, mutants: Sequence[Mutant]) -> None:
    for target, attr, factory in mutants:
        mp.setattr(target, attr, factory(getattr(target, attr)))


def _run_e2e(cell: str, frame: pd.DataFrame, combo: Sequence[str], mutants: Sequence[Mutant] = ()) -> E2E:
    """正式臂（`transform_selected`，契約正式臂）於一組合之執行與獨立 oracle。"""
    cfg = _combo_config(combo)
    rec = Internals()
    mp = pytest.MonkeyPatch()
    try:
        _apply_mutants(mp, mutants)
        _install_internal_spies(mp, rec)
        out = FeaturePreprocessor(cfg.model_dump()).transform_selected(
            list(frame.columns), {"numview": frame.copy()}, config=cfg, arm=_formal_arm())
    finally:
        mp.undo()
    assert "numview" in out, f"{cell} {combo}：正式臂無輸出"
    merged = out["numview"]
    cols = [str(c) for c in merged.columns]
    oracle, ill = _chain_oracle(frame.loc[:, cols].to_numpy(dtype=np.float64), _post_ic_spec(cfg))
    return E2E(cell, tuple(combo), cols, merged.to_numpy(dtype=np.float64), {c: str(merged[c].dtype) for c in cols},
               oracle, ill, rec)


@pytest.fixture(scope="module")
def e2e(runs: _Runs) -> Dict[Tuple[str, Tuple[str, ...]], E2E]:
    """格 A 全部 symbol×tf 之 IC-first 實際選欄 × ICPOSTLEAK 七組合（每格每組合一次）。"""
    out: Dict[Tuple[str, Tuple[str, ...]], E2E] = {}
    for run in runs.all("A"):
        frame = _ic_first_call(run).frame
        if frame.shape[1] == 0:
            continue  # 該格 IC-first 選欄為零（Task 0.5 邊界④）⇒ 無可比之欄；全格加總之非空另斷言
        for combo in COMBOS:
            out[(run.key, combo)] = _run_e2e(run.key, frame, combo)
    assert out, "格 A 全部格之 IC-first 選欄皆為零 ⇒ 端到端無對象"
    return out


def _first_cell_frame(runs: _Runs) -> Tuple[str, pd.DataFrame]:
    for run in runs.all("A"):
        frame = _ic_first_call(run).frame
        if frame.shape[1]:
            return run.key, frame
    raise AssertionError("格 A 無任何非零選欄之格")


def _intermediate_dtype_violations(rec: Internals) -> List[str]:
    out: List[str] = []
    for where, dicts in (("rank", [d for d, _i, _o, _w in rec.rank]), ("mask", rec.mask), ("zscore_in", rec.zscore_in)):
        for dtypes in dicts:
            out.extend(f"{where}:{c}={t}" for c, t in dtypes.items() if t != "Float64")
    return out


def _rank_exact_mismatches(rec: Internals) -> Tuple[int, int, int]:
    """rank 步輸出（遮罩前）對獨立 float64 rank 逐值 exact：回 (不等格數, 比較格數, 非整數倍 rank〔ties〕格數)。"""
    bad = total = ties = 0
    for _dtypes, inp, res, window in rec.rank:
        for j in range(inp.shape[1]):
            want = _rank_oracle(inp[:, j], window)
            got = res[:, j]
            bad += int((~((got == want) | (np.isnan(got) & np.isnan(want)))).sum())
            total += int(np.isfinite(want).sum())
            win = _windows(inp[:, j], window)
            equal = (win == inp[:, j][:, None]).sum(axis=1)
            ties += int((np.isfinite(want) & (equal > 1)).sum())
    return bad, total, ties


def _e2e_violations(results: Iterable[E2E]) -> Dict[str, Any]:
    """端到端判定：每欄回傳 dtype 為 float64、NaN 遮罩 exact、非有限 fail-closed、spacing/16 超界（病態格另列）、
    逐組合見證格。"""
    dtype_bad: List[str] = []
    mask_bad: List[str] = []
    hard: List[str] = []
    excused: List[str] = []
    oracles: Dict[str, List[np.ndarray]] = {}
    for res in results:
        tag = f"{res.cell}|{'+'.join(res.combo)}"
        dtype_bad.extend(f"{tag}|{c}={t}" for c, t in res.out_dtypes.items() if t != "float64")
        if not np.array_equal(np.isnan(res.out), np.isnan(res.oracle)):
            mask_bad.append(tag)
        if np.isinf(res.oracle).any() or np.isinf(res.out).any():
            mask_bad.append(f"{tag}：非有限值")
        viol = _spacing16_violations(res.out, res.oracle)
        for i, j in zip(*np.nonzero(viol)):
            ident = f"{tag}|{res.columns[j]}|{int(i)}"
            (excused if res.ill[i, j] else hard).append(ident)
        oracles.setdefault("+".join(res.combo), []).append(res.oracle)
    return {"dtype": dtype_bad, "mask": mask_bad, "hard": hard, "excused": excused,
            "coverage": _coverage_violations(oracles)}


# ============================================================================================== Task 3.1 — postic_float64

def test_postic_float64_formal_arm_within_1ulp_of_independent_and_legacy(runs: _Runs) -> None:
    """Task 3.1 前者內容兩路 oracle：格 A 全部 symbol×tf 之 IC-first 實際選欄（生成時擷取之 post-IC 輸入與設定），
    正式臂回傳（落盤前，轉 float32）對 (i) 獨立 float64 oracle 與 (ii) legacy pandas 臂皆 ≤1 ulp、NaN 遮罩 exact。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    failures: List[str] = []
    compared = 0
    for run in runs.all("A"):
        call = _ic_first_call(run)
        if call.output.shape[1] == 0:
            continue
        cols = [str(c) for c in call.output.columns]
        out = call.output.loc[:, cols].to_numpy(dtype=np.float64)
        oracle, _ill = _chain_oracle(call.frame.loc[:, cols].to_numpy(dtype=np.float64), _post_ic_spec(call.config))
        legacy = _legacy_arm(call.frame.loc[:, cols], call.config)
        assert [str(c) for c in legacy.columns] == cols, (run.key, list(legacy.columns), cols)
        for name, ref in (("independent", oracle), ("legacy", legacy.to_numpy(dtype=np.float64))):
            rep = _ulp_report(out, ref)
            compared += rep["positive"] + rep["negative"] + rep["zero"]
            if rep["nan_mismatch"] or rep["nonfinite_bad"] or rep["violations"]:
                failures.append(f"{run.key}|{name}：{rep}")
    assert compared > 0, "格 A 全部格無可比之有限格"
    assert failures == [], failures


def test_postic_float64_intermediate_dtypes_are_float64(e2e: Dict[Tuple[str, Tuple[str, ...]], E2E]) -> None:
    """R10-A：rank 步輸出、每次遮罩後、zscore 輸入之 Polars dtype 皆為 Float64（七組合 × 格 A 全部格之 spy）。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    seen = {"rank": 0, "mask": 0, "zscore_in": 0}
    bad: List[str] = []
    for res in e2e.values():
        seen["rank"] += len(res.internals.rank)
        seen["mask"] += len(res.internals.mask)
        seen["zscore_in"] += len(res.internals.zscore_in)
        bad.extend(f"{res.cell}|{'+'.join(res.combo)}|{v}" for v in _intermediate_dtype_violations(res.internals))
    assert all(n > 0 for n in seen.values()), f"spy 未觀測到全部三處邊界：{seen}"
    assert bad == [], bad[:20]


def test_postic_float64_rank_intermediate_exact_vs_independent(e2e: Dict[Tuple[str, Tuple[str, ...]], E2E]) -> None:
    """R10-A：rank 步輸出（遮罩前）對獨立 float64 rank 逐值 exact；真實欄須含 ties 造成之非整數 rank（不足即紅）。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    bad = total = ties = 0
    for res in e2e.values():
        b, t, k = _rank_exact_mismatches(res.internals)
        bad, total, ties = bad + b, total + t, ties + k
    assert total > 0, "無 rank 中間值可比"
    assert ties > 0, "真實欄無 ties（非整數 rank）⇒ 本案無偵測力"
    assert bad == 0, f"rank 中間值與獨立 float64 rank 不等之格數 {bad}／{total}"


def test_postic_float64_end_to_end_seven_combos_within_spacing_over_16(
        e2e: Dict[Tuple[str, Tuple[str, ...]], E2E]) -> None:
    """R11-A／R12-A／R13-A：七組合之 `transform_selected` 回傳每欄 float64；逐格 ≤ spacing(f32(oracle))/16；任一組合見證
    格 0 ⇒ 覆蓋不足紅；病態格之超界須逐格列於 Task 3.1 收據 `ill_conditioned_cells`（不得靜默豁免）。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    assert {combo for _cell, combo in e2e} == set(COMBOS), "端到端未涵蓋七組合"
    verdict = _e2e_violations(e2e.values())
    assert verdict["dtype"] == [], verdict["dtype"][:20]
    assert verdict["mask"] == [], verdict["mask"][:20]
    assert verdict["coverage"] == [], verdict["coverage"]
    assert verdict["hard"] == [], verdict["hard"][:20]
    if verdict["excused"]:
        reported = set(_latest_receipt(POSTIC_CORE_RECEIPT_GLOB).get("ill_conditioned_cells") or [])
        unreported = [c for c in verdict["excused"] if c not in reported]
        assert unreported == [], f"病態格超界而未列入收據：{unreported[:20]}"


def test_postic_float64_gaussian_output_and_final_return_carry_compute_dtype(
        e2e: Dict[Tuple[str, Tuple[str, ...]], E2E]) -> None:
    """R12-A：以 spy 直接觀測 `_gaussian_2d` 回傳與最終回傳之 dtype 為 compute dtype（float64）。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    gauss = [d for res in e2e.values() if "gaussian" in res.combo for d in res.internals.gaussian_out]
    assert gauss, "含 gaussian 之組合未呼叫 `_gaussian_2d`"
    assert set(gauss) == {"float64"}, sorted(set(gauss))
    finals = {t for res in e2e.values() for t in res.out_dtypes.values()}
    assert finals == {"float64"}, sorted(finals)


def test_postic_float64_ulp_bound_covers_positive_negative_zero_and_nan(
        e2e: Dict[Tuple[str, Tuple[str, ...]], E2E]) -> None:
    """§G R2-C：1 ulp 判定於正、負、零三類 oracle 值與 NaN 遮罩格皆實際比較且無超界（七組合 × 格 A 全部格）。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    totals = {"positive": 0, "negative": 0, "zero": 0, "nan_cells": 0}
    bad: List[str] = []
    for res in e2e.values():
        rep = _ulp_report(res.out, res.oracle)
        for k in totals:
            totals[k] += rep[k]
        if rep["violations"] or rep["nan_mismatch"] or rep["nonfinite_bad"]:
            bad.append(f"{res.cell}|{'+'.join(res.combo)}：{rep}")
    assert all(v > 0 for v in totals.values()), f"三類 oracle 值或 NaN 遮罩格未全數出現：{totals}"
    assert bad == [], bad[:20]


def test_postic_float64_persisted_dtypes_unchanged_and_raw_bitwise(runs: _Runs, tmp_path: Path) -> None:
    """Task 3.1：落盤後 IC-first processed 之逐欄 dtype 與改前凍結相同（float32／float16 自動選不動）、欄集合相同；
    IC 頁 h5 讀回每欄 float32 且與凍結 `polars` 臂份 dtype 相同；raw（§G 其餘值指紋）逐位元不變。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    arm = _formal_arm()
    bad: List[str] = []
    for run in runs.all("A"):
        now = nh.fingerprints(run.handle.run_dir, "processed")
        frozen = _frozen_fp("A", run.key, FROZEN_PROCESSED)
        if sorted(now["columns"]) != sorted(frozen["columns"]):
            bad.append(f"{run.key}：processed 欄集合變動")
        bad.extend(f"{run.key}|processed|{c}" for c in frozen["columns"]
                   if c in now["columns"] and now["columns"][c]["dtype"] != frozen["columns"][c]["dtype"])
        bad.extend(f"{run.key}|raw|{d}" for d in nh.bitwise_diff(_frozen_fp("A", run.key, FROZEN_RAW_A),
                                                                  nh.fingerprints(run.handle.run_dir, "raw")))
        frame, _resp = _freeze().ic_page_output(run.handle, tmp_path / f"icpage_{run.key}")
        bad.extend(f"{run.key}|ic_page|{c}={t}" for c, t in frame.dtypes.astype(str).items() if t != "float32")
        frozen_page = _frozen_fp("A", run.key, FROZEN_IC_PAGE, arm)
        page = nh.frame_fingerprints(frame)
        bad.extend(f"{run.key}|ic_page_dtype|{c}" for c in frozen_page["columns"]
                   if page["columns"].get(c, {}).get("dtype") != frozen_page["columns"][c]["dtype"])
    assert bad == [], bad[:30]


def test_postic_float64_receipt_ratios_within_approved() -> None:
    """Task 3.1：收據記格 A 每格改前後牆鐘與峰值記憶體；比值（改後／改前，取各格最大）不超過決定紀錄核可值。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    receipt = _latest_receipt(POSTIC_CORE_RECEIPT_GLOB)
    limits = _decision_record(D_POSTIC[0]).get("approved_limits") or {}
    assert {"wall_time_ratio", "peak_memory_ratio"} <= set(limits), f"決定紀錄缺核可上限：{limits}"
    cells = receipt.get("cells") or {}
    expected = {_cell_key("A", c) for c in _cells("A")}
    assert set(cells) == expected, f"收據格 ≠ 格 A 全部格：缺 {sorted(expected - set(cells))[:5]}"
    wall = max(float(v["wall_seconds_after"]) / float(v["wall_seconds_before"]) for v in cells.values())
    peak = max(float(v["peak_rss_bytes_after"]) / float(v["peak_rss_bytes_before"]) for v in cells.values())
    assert wall <= float(limits["wall_time_ratio"]), (wall, limits)
    assert peak <= float(limits["peak_memory_ratio"]), (peak, limits)


# ---------------------------------------------------------------------------------------------- Task 3.1 mutation 共用

def _entry_float32(real: Callable) -> Callable:
    """（工廠，注入 `polars_adapter.pandas_to_polars`）入口改回預設 Float32：`_transform_single_polars` 首次呼叫
    （`pl_df` 尚未賦值時）強制 Float32。"""

    def mutant(df: Any, *args: Any, use_float64: bool = False, **kwargs: Any) -> Any:
        frame = sys._getframe(1)
        if frame.f_code.co_name == "_transform_single_polars" and "pl_df" not in frame.f_locals:
            use_float64 = False
        return real(df, *args, use_float64=use_float64, **kwargs)

    return mutant


def _always_float64(real: Callable) -> Callable:
    """（工廠，注入 `polars_adapter.pandas_to_polars`）一律 Float64（候選 `polars_float64` 之入口與回包）。"""
    return lambda df, *a, use_float64=False, **k: real(df, *a, use_float64=True, **k)


def _rank_fn(window: int, buffer_dtype: Any, series_dtype: Any = np.float64) -> Callable[[Any], Any]:
    """rank UDF 之可調精度複本（同 `_make_rolling_pct_rank_fn` 語意）：緩衝區與逐值寫入用 `buffer_dtype`，回傳 Series
    轉 `series_dtype`。"""
    from scipy.stats import rankdata

    w = max(1, int(window))
    min_p = _min_periods(w)

    def fn(s: Any) -> Any:
        import polars as pl

        arr = s.to_numpy()
        out = np.full(len(arr), np.nan, dtype=buffer_dtype)
        for i in range(len(arr)):
            if np.isnan(arr[i]):
                continue
            valid = arr[max(0, i - w + 1): i + 1]
            valid = valid[~np.isnan(valid)]
            if len(valid) < min_p:
                continue
            if np.all(valid == valid[0]):
                out[i] = 0.5
                continue
            out[i] = buffer_dtype(rankdata(valid, method="average")[-1] / len(valid))
        return pl.Series(out.astype(series_dtype)).fill_nan(None)

    return fn


def _rank_transform_with(buffer_dtype: Any, cast_float32: bool) -> Callable[[Any], Callable]:
    """（工廠，注入 `polars_adapter.polars_l65_rank_transform`）rank 步之複本：緩衝區 `buffer_dtype`、`return_dtype`
    Float64，`cast_float32` ⇒ rank 步輸出轉 Float32（＝`return_dtype` 改回 Float32）。"""

    def factory(_real: Callable) -> Callable:
        def mutant(pl_df: Any, columns: Any, window: int = 252, **_kwargs: Any) -> Any:
            import polars as pl

            cols = [c for c in columns if c in pl_df.columns]
            fn = _rank_fn(window, buffer_dtype)
            exprs = [pl.col(c).map_batches(fn, return_dtype=pl.Float64) for c in cols]
            if cast_float32:
                exprs = [e.cast(pl.Float32) for e in exprs]
            return pl_df.with_columns([e.alias(c) for e, c in zip(exprs, cols)])

        return mutant

    return factory


def _rank_buffer_float32(_real: Callable) -> Callable:
    """（工廠，注入 `polars_adapter._make_rolling_pct_rank_fn`）保留 rank 緩衝區 np.float32（值經 float32 取整後以
    Float64 回傳；＝只改入口與 `return_dtype`）。"""
    return lambda window: _rank_fn(window, np.float32)


def _mask_rewrap_float32(_real: Callable) -> Any:
    """（工廠，注入 `FeaturePreprocessor._polars_mask_columns`）保留改前之預設回包（經 `polars_to_pandas`〔float32〕再
    `pandas_to_polars` 預設 Float32）。"""
    from momentum.FeatureEngineering.preprocessing import stable_mask

    def mutant(pl_df: Any, columns: Any, step_input: Any, window: int, index: Any, *_a: Any, **_k: Any) -> Any:
        frame = polars_adapter.polars_to_pandas(pl_df, index=index)
        masked = stable_mask.mask_incomplete_window_by_input_2d(
            frame[list(columns)].to_numpy(dtype=np.float64), step_input, window)
        frame = frame.astype({c: np.float64 for c in columns})
        frame.loc[:, list(columns)] = masked
        return polars_adapter.pandas_to_polars(frame)

    return staticmethod(mutant)


def _mask_keep_float64(_real: Callable) -> Any:
    """（工廠，注入 `FeaturePreprocessor._polars_mask_columns`）候選 `polars_float64` 之遮罩：中間保留 Float64。"""
    from momentum.FeatureEngineering.preprocessing import stable_mask

    def mutant(pl_df: Any, columns: Any, step_input: Any, window: int, index: Any, *_a: Any, **_k: Any) -> Any:
        import polars as pl

        cur = np.asarray(pl_df.select(list(columns)).to_numpy(), dtype=np.float64)
        masked = stable_mask.mask_incomplete_window_by_input_2d(cur, step_input, window)
        return pl_df.with_columns([pl.Series(c, masked[:, i]).fill_nan(None).cast(pl.Float64)
                                   for i, c in enumerate(columns)])

    return staticmethod(mutant)


def _gaussian_2d_float32(real: Callable) -> Any:
    """（工廠，注入 `FeaturePreprocessor._gaussian_2d`）保留 float32 回傳。"""
    return staticmethod(lambda *a, **k: np.asarray(real(*a, **k)).astype(np.float32))


def _gaussian_branch_rewrap_float32(real: Callable) -> Callable:
    """（工廠，注入 `FeaturePreprocessor._apply_gaussian_normalize`）gaussian 分支保留 float32 回包。"""
    return lambda self, df: real(self, df).astype(np.float32)


def _final_return_float32(real: Callable) -> Callable:
    """（工廠，注入 `FeaturePreprocessor.transform_selected`）最終回傳保留 float32。"""

    def mutant(self: Any, *args: Any, **kwargs: Any) -> Any:
        return {k: v.astype(np.float32) for k, v in real(self, *args, **kwargs).items()}

    return mutant


def _combos_with(*steps: str) -> List[Tuple[str, ...]]:
    return [c for c in COMBOS if all(s in c for s in steps)]


def _direct_write_processed(root: Path, symbol: str, tf: str, config_hash: str, groups: Dict[str, pd.DataFrame],
                            execution: Any, row_index: pd.DatetimeIndex, arm: str,
                            post_ic_config: Any = None) -> Tuple[Path, Optional[BaseException]]:
    """直接呼叫 `FeatureStorage.write_processed`（同 IC-first 寫入端）；`post_ic_config` 只在簽名含該參數時傳。"""
    storage = FeatureStorage(str(root))
    kwargs: Dict[str, Any] = {"row_index": row_index, "post_ic_arm": arm, "execution": execution}
    if "post_ic_config" in inspect.signature(FeatureStorage.write_processed).parameters:
        kwargs["post_ic_config"] = post_ic_config
    error: Optional[BaseException] = None
    try:
        storage.write_processed(symbol, tf, config_hash, groups, **kwargs)
    except Exception as exc:  # noqa: BLE001 — 由呼叫端斷言錯誤型別與後果
        error = exc
    return storage.feature_run_dir(symbol, tf, config_hash), error


def _raw_row_index(handle: Any) -> pd.DatetimeIndex:
    import pyarrow.parquet as pq

    manifest = ph.load_manifest(handle.run_dir)
    seconds = pq.read_table(str(Path(handle.run_dir) / str(ph.row_index_rel(manifest, "raw")))).column(
        "timestamp").to_numpy()
    return pd.DatetimeIndex(pd.to_datetime(seconds, unit="s", utc=True))


def _replay_ic_first(run: CellRun, mutants: Sequence[Mutant] = ()) -> Tuple[Dict[str, pd.DataFrame], Any]:
    """以生成時擷取之 IC-first post-IC 輸入與設定重放正式臂（可注入 mutant）；回 (輸出群組, 紀錄)。"""
    call = _ic_first_call(run)
    mp = pytest.MonkeyPatch()
    try:
        _apply_mutants(mp, mutants)
        pre = FeaturePreprocessor(_effective_post_ic_dict(call.config))
        out = pre.transform_selected(list(call.selected), {"numview": call.frame.copy()}, config=call.config,
                                     arm=_formal_arm())
        execution = pre.last_post_ic_execution()
    finally:
        mp.undo()
    return out, execution


# ---------------------------------------------------------------------------------------------- Task 3.1 mutation（postic_float64）

def test_mutation_postic_float64_entry_float32_breaks_independent_oracle(runs: _Runs) -> None:
    """mutation：入口改回預設 Float32 ⇒ (i)（對獨立 oracle 之 1 ulp）於至少一組合紅。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    key, frame = _first_cell_frame(runs)
    mutant = (polars_adapter, "pandas_to_polars", _entry_float32)
    reps = [_ulp_report(r.out, r.oracle) for r in (_run_e2e(key, frame, c, [mutant]) for c in COMBOS)]
    assert sum(r["violations"] + r["nan_mismatch"] for r in reps) > 0, reps


def test_mutation_postic_float64_rank_return_dtype_float32_breaks_rank_combos(runs: _Runs) -> None:
    """mutation：rank 步 `return_dtype` 改回 Float32 ⇒ 含 rank 之組合之 (i) 或端到端案紅。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    key, frame = _first_cell_frame(runs)
    mutant = (polars_adapter, "polars_l65_rank_transform", _rank_transform_with(np.float64, True))
    results = [_run_e2e(key, frame, c, [mutant]) for c in _combos_with("rank")]
    ulp = sum(_ulp_report(r.out, r.oracle)["violations"] for r in results)
    verdict = _e2e_violations(results)
    assert ulp + len(verdict["hard"]) + len(verdict["excused"]) + len(verdict["dtype"]) > 0


def test_mutation_postic_float64_rank_buffer_float32_breaks_rank_exact(runs: _Runs) -> None:
    """mutation：只改入口與 `return_dtype` 而保留 rank 緩衝區 np.float32 ⇒ rank 中間值 exact 案紅（中間 dtype 不得遮蔽）。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    key, frame = _first_cell_frame(runs)
    mutant = (polars_adapter, "_make_rolling_pct_rank_fn", _rank_buffer_float32)
    results = [_run_e2e(key, frame, c, [mutant]) for c in _combos_with("rank")]
    bad = sum(_rank_exact_mismatches(r.internals)[0] for r in results)
    dtype_bad = sum(len(_intermediate_dtype_violations(r.internals)) for r in results)
    assert bad + dtype_bad > 0


def test_mutation_postic_float64_mask_default_rewrap_breaks_post_mask_dtype(runs: _Runs) -> None:
    """mutation：`_polars_mask_columns` 保留預設回包（Float32）⇒ 遮罩後 dtype 斷言紅。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    key, frame = _first_cell_frame(runs)
    mutant = (FeaturePreprocessor, "_polars_mask_columns", _mask_rewrap_float32)
    results = [_run_e2e(key, frame, c, [mutant]) for c in COMBOS]
    post_mask = [t for r in results for d in r.internals.mask for t in d.values()]
    assert post_mask and any(t != "Float64" for t in post_mask), sorted(set(post_mask))


def test_mutation_postic_float64_gaussian_2d_float32_breaks_end_to_end(runs: _Runs) -> None:
    """mutation：`_gaussian_2d` 保留 float32 回傳 ⇒ 含 gaussian 組合之端到端案（見證格）與 gaussian 輸出 dtype spy 紅。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    key, frame = _first_cell_frame(runs)
    mutant = (FeaturePreprocessor, "_gaussian_2d", _gaussian_2d_float32)
    results = [_run_e2e(key, frame, c, [mutant]) for c in _combos_with("gaussian")]
    verdict = _e2e_violations(results)
    assert any(d != "float64" for r in results for d in r.internals.gaussian_out)
    assert len(verdict["hard"]) + len(verdict["excused"]) > 0, "見證格上未現形"


def test_mutation_postic_float64_gaussian_branch_rewrap_breaks_end_to_end(runs: _Runs) -> None:
    """mutation：gaussian 分支保留 float32 回包 ⇒ 含 gaussian 組合之端到端案紅。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    key, frame = _first_cell_frame(runs)
    mutant = (FeaturePreprocessor, "_apply_gaussian_normalize", _gaussian_branch_rewrap_float32)
    verdict = _e2e_violations([_run_e2e(key, frame, c, [mutant]) for c in _combos_with("gaussian")])
    assert len(verdict["hard"]) + len(verdict["excused"]) + len(verdict["dtype"]) > 0


def test_mutation_postic_float64_final_return_float32_breaks_dtype(runs: _Runs) -> None:
    """mutation：最終回傳保留 float32 ⇒ 端到端 dtype 案紅。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    key, frame = _first_cell_frame(runs)
    mutant = (FeaturePreprocessor, "transform_selected", _final_return_float32)
    verdict = _e2e_violations([_run_e2e(key, frame, c, [mutant]) for c in COMBOS])
    assert verdict["dtype"], "最終回傳 float32 未被 dtype 案偵測"


def test_mutation_postic_float64_ic_page_not_float32_breaks_stored_dtype(runs: _Runs, tmp_path: Path,
                                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：IC 頁寫入前未轉 float32（於 `DataFrame.to_hdf` 前升回 float64 模擬）⇒ stored dtype 案紅。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    real = pd.DataFrame.to_hdf

    def mutant(self: pd.DataFrame, *args: Any, **kwargs: Any) -> Any:
        return real(self.astype(np.float64), *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "to_hdf", mutant)
    run = runs.first("A")
    frame, _resp = _freeze().ic_page_output(run.handle, tmp_path / "icpage_mutant")
    assert frame.shape[1] > 0
    assert any(str(t) != "float32" for t in frame.dtypes), "IC 頁 stored dtype 案未翻紅"


def test_mutation_postic_float64_processed_float64_breaks_dtype_rule(runs: _Runs, tmp_path: Path,
                                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：落盤前未轉 float32（processed 以 float64 落盤；於 `_build_l7_v2_table` 回傳表升回 float64 模擬）⇒
    processed dtype 對改前凍結之規則案紅。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    import pyarrow as pa

    real = FeatureStorage._build_l7_v2_table

    def mutant(self: Any, *args: Any, **kwargs: Any) -> Any:
        res = real(self, *args, **kwargs)
        table = res[0]
        schema = pa.schema([pa.field(f.name, pa.float64() if pa.types.is_floating(f.type) else f.type)
                            for f in table.schema], metadata=table.schema.metadata)
        return (table.cast(schema),) + tuple(res[1:])

    run = runs.first("A")
    out, execution = _replay_ic_first(run)
    monkeypatch.setattr(FeatureStorage, "_build_l7_v2_table", mutant)
    run_dir, error = _direct_write_processed(tmp_path / "features", run.handle.symbol, run.handle.tf, "numview_mut",
                                             out, execution, _raw_row_index(run.handle), _formal_arm())
    assert error is None, error
    now = nh.fingerprints(run_dir, "processed")
    frozen = _frozen_fp("A", run.key, FROZEN_PROCESSED)
    changed = [c for c in frozen["columns"] if now["columns"].get(c, {}).get("dtype") != frozen["columns"][c]["dtype"]]
    assert changed, "processed 以 float64 落盤未被 dtype 規則案偵測"


def test_mutation_postic_float64_witness_without_isfinite_masks_coverage_gap(
        e2e: Dict[Tuple[str, Tuple[str, ...]], E2E], monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（R13-A）：見證計數去掉 `np.isfinite`，以「有限見證 0、NaN 格非 0」之真實 oracle 子集執行 ⇒ 正確計數
    判覆蓋不足（紅），mutant 計數不判（存活）——證本案輸入可區分兩者。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    res = next(iter(e2e.values()))
    o = res.oracle.ravel()
    keep = np.isnan(o) | (np.isfinite(o) & (o.astype(np.float32) == o))
    sub = o[keep]
    assert np.isnan(sub).any() and np.isfinite(sub).any(), "真實 oracle 子集須同含 NaN 與 float32 可精確表示之有限值"
    assert _coverage_violations({"subset": [sub]}), "正確見證計數於有限見證 0 之輸入未判覆蓋不足"
    monkeypatch.setattr(sys.modules[__name__], "_witness_count", _witness_count_without_isfinite)
    assert _coverage_violations({"subset": [sub]}) == [], "mutant 應因 NaN 誤計而不判覆蓋不足（輸入無區分力）"


def test_mutation_postic_float64_ulp_bound_without_abs_reds_negative_oracle(
        e2e: Dict[Tuple[str, Tuple[str, ...]], E2E], monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（R2-C）：1 ulp 上界去掉 `np.abs` ⇒ 負 oracle 案紅（真實負 oracle 值、輸出恰等於 float32(oracle)）。"""
    _require_decision(D_POSTIC[0], D_POSTIC[1])
    neg = np.concatenate([r.oracle[np.isfinite(r.oracle) & (r.oracle < 0)] for r in e2e.values()])
    assert neg.size > 0, "無負 oracle 值"
    ref32 = neg.astype(np.float32)
    assert _ulp_report(ref32, neg)["violations"] == 0
    monkeypatch.setattr(sys.modules[__name__], "_ulp_ok", _ulp_ok_without_abs)
    assert _ulp_report(ref32, neg)["violations"] > 0, "去掉 np.abs 之上界未使負 oracle 案翻紅"


# ============================================================================================== Task 3.1 — postic_retained

def _key_to_cell(kind: str) -> Dict[str, Dict[str, Any]]:
    return {_cell_key(kind, c): c for c in _cells(kind)}


def test_postic_retained_processed_and_ic_page_bitwise_equal_frozen(runs: _Runs, tmp_path: Path) -> None:
    """R6-B：IC-first processed（凍結檔中每個含 processed 之格）與 IC 頁 `polars` 臂份（格 A 全部格）對 §G 改前凍結逐位元
    相等（`values_native`＋`dtype`＋`nan`、欄集合與欄序，atol=0）；沿用 PRE-PROV `ic_first_default` processed 基準
    （legacy 相容比對）。Task 1.1 收據之 max_abs 只作報告，不作通過條件。"""
    _require_decision(D_POSTIC[0], D_POSTIC[2])
    arm = _formal_arm()
    bad: List[str] = []
    for kind in ("A", "B"):
        cells = _key_to_cell(kind)
        frozen_kind = _frozen_doc().get("cells", {}).get(kind, {})
        for key, node in frozen_kind.items():
            if FROZEN_PROCESSED not in node:
                continue
            assert key in cells, f"凍結格 {kind}/{key} 不在現行列舉"
            run = runs.get(kind, cells[key])
            bad.extend(f"{kind}|{key}|processed|{d}" for d in
                       nh.bitwise_diff(node[FROZEN_PROCESSED], nh.fingerprints(run.handle.run_dir, "processed")))
    for run in runs.all("A"):
        frame, _resp = _freeze().ic_page_output(run.handle, tmp_path / f"icpage_{run.key}")
        bad.extend(f"A|{run.key}|ic_page|{d}" for d in
                   nh.bitwise_diff(_frozen_fp("A", run.key, FROZEN_IC_PAGE, arm), nh.frame_fingerprints(frame)))
    legacy = json.loads(nh.LEGACY_BASELINE_PATH.read_text(encoding="utf-8"))["cells"]["ic_first_default"]
    cache = ph.RunCache(tmp_path / "preprov")
    for symbol, node in legacy.items():
        handle = cache.get("ic_first_default", symbol)
        bad.extend(f"preprov|{symbol}|{d}" for d in
                   nh.bitwise_diff(node["processed"], nh.fingerprints(handle.run_dir, "processed"), legacy=True))
    assert bad == [], bad[:30]


def _retained_processed_diff(run: CellRun, root: Path, mutants: Sequence[Mutant]) -> List[str]:
    """重放 IC-first post-IC（可注入 mutant）並直接落盤，逐欄對該格凍結 processed 比位元。"""
    out, execution = _replay_ic_first(run, mutants)
    run_dir, error = _direct_write_processed(root, run.handle.symbol, run.handle.tf, "numview_replay", out, execution,
                                             _raw_row_index(run.handle), _formal_arm())
    assert error is None, error
    return _column_bitwise_diff(_frozen_fp("A", run.key, FROZEN_PROCESSED), nh.fingerprints(run_dir, "processed"))


def _zscore_epsilon_in_variance(_real: Callable) -> Callable:
    """（工廠，注入 `polars_adapter.polars_l65_adaptive_zscore`）微小核心改動：ε 由「std + ε」移至「sqrt(var + ε)」。"""

    def mutant(pl_df: Any, columns: Any, window: int = 100, epsilon: float = 1e-8) -> Any:
        import polars as pl

        exprs = []
        for c in [c for c in columns if c in pl_df.columns]:
            col = pl.col(c)
            mean = col.rolling_mean(window_size=window, min_samples=1)
            std = col.rolling_std(window_size=window, min_samples=1)
            denom = (col.rolling_var(window_size=window, min_samples=1) + epsilon).sqrt()
            exprs.append(pl.when(col.is_null()).then(None).when(std.is_null() | (std <= 0.0)).then(0.0)
                         .otherwise((col - mean) / denom).alias(c))
        return pl_df.with_columns(exprs)

    return mutant


def test_mutation_postic_retained_float64_compute_breaks_bitwise(runs: _Runs, tmp_path: Path) -> None:
    """mutation（R6-B）：保留分支下把 Polars 計算改為 Float64（候選 `polars_float64`；差異在 Task 1.1 max_abs 內甚至更近
    oracle）⇒ 逐位元案紅。先證未注入之重放等於凍結（對照）。"""
    _require_decision(D_POSTIC[0], D_POSTIC[2])
    run = runs.first("A")
    assert _retained_processed_diff(run, tmp_path / "control", []) == [], "對照：未注入之重放須等於凍結"
    candidate = [(polars_adapter, "pandas_to_polars", _always_float64),
                 (polars_adapter, "polars_l65_rank_transform", _rank_transform_with(np.float64, False)),
                 (FeaturePreprocessor, "_polars_mask_columns", _mask_keep_float64)]
    assert _retained_processed_diff(run, tmp_path / "mutant", candidate), "Float64 計算未被逐位元案偵測"


def test_mutation_postic_retained_zscore_epsilon_placement_breaks_bitwise(runs: _Runs, tmp_path: Path) -> None:
    """mutation（R6-B）：zscore ε 位置之微小核心改動 ⇒ 逐位元案紅（對照同上）。"""
    _require_decision(D_POSTIC[0], D_POSTIC[2])
    run = runs.first("A")
    assert _retained_processed_diff(run, tmp_path / "control", []) == []
    mutant = (polars_adapter, "polars_l65_adaptive_zscore", _zscore_epsilon_in_variance)
    assert _retained_processed_diff(run, tmp_path / "mutant", [mutant])


# ============================================================================================== Task 3.1 邊界（core_always）

def _formal_vs_legacy(frame: pd.DataFrame, combo: Sequence[str]) -> Tuple[np.ndarray, np.ndarray]:
    cfg = _combo_config(combo)
    formal = FeaturePreprocessor(cfg.model_dump()).transform_selected(
        list(frame.columns), {"numview": frame.copy()}, config=cfg, arm=_formal_arm())["numview"]
    legacy = _legacy_arm(frame, cfg)
    cols = [str(c) for c in frame.columns]
    return formal.loc[:, cols].to_numpy(dtype=np.float64), legacy.loc[:, cols].to_numpy(dtype=np.float64)


def _constant_run_frame(window: int) -> Tuple[pd.DataFrame, int, int, str]:
    """真實 kline 中最長之連續相同值區段（長度 ≥ 2·window）；回 (含前段真實資料之單欄 frame, 區段起列, 區段終列〔不含〕,
    來源說明)。全庫皆無 ⇒ 以真實 close 之一個值延續成常數段（同 ICPOSTLEAK 邊界⑤先例）。"""
    for symbol, tf in _kline_symbol_tfs():
        k = fsh.kline_frame(symbol=symbol, timeframe=tf)
        for name in k.columns:
            v = k[name].to_numpy(dtype=np.float64)
            same = np.concatenate([[False], v[1:] == v[:-1]])
            best_start, best_len, start = 0, 0, None
            for i, s in enumerate(same):
                if s and start is None:
                    start = i - 1
                if (not s or i == len(same) - 1) and start is not None:
                    end = i + 1 if s else i
                    if end - start > best_len:
                        best_start, best_len = start, end - start
                    start = None
            if best_len >= 2 * window and best_start >= window:
                lo = best_start - window
                frame = pd.DataFrame({name: v[lo: best_start + best_len]}, index=k.index[lo: best_start + best_len])
                return frame, window, window + best_len, f"真實 {symbol}/{tf}/{name} 連續相同值 {best_len} 根"
    symbol, tf = _kline_symbol_tfs()[0]
    k = fsh.kline_frame(symbol=symbol, timeframe=tf)
    close = k.columns[list(map(str, k.columns)).index("close")] if "close" in map(str, k.columns) else k.columns[0]
    v = k[close].to_numpy(dtype=np.float64)[: 6 * window].copy()
    v[3 * window:] = v[3 * window - 1]
    return (pd.DataFrame({str(close): v}, index=k.index[: len(v)]), 3 * window, len(v),
            f"真實 {symbol}/{tf}/{close} 第 {3 * window - 1} 列之值延續成常數段（庫內無足長常數段）")


def test_boundary_28_core_always_zscore_constant_window_outputs_zero() -> None:
    """邊界①（Task 3.1）：窗內常數（std=0）⇒ 正式臂輸出 0、與 legacy 同（兩決定皆須成立）。"""
    window = Z_WINDOWS[0]
    frame, start, end, source = _constant_run_frame(window)
    formal, legacy = _formal_vs_legacy(frame, ("zscore",))
    rows = np.arange(start + window - 1, end)
    assert rows.size > 0, source
    assert (formal[rows, 0] == 0.0).all(), (source, formal[rows, 0][:5])
    assert (legacy[rows, 0] == 0.0).all(), (source, legacy[rows, 0][:5])


def test_boundary_29_core_always_window_not_filled_is_nan() -> None:
    """邊界②（Task 3.1）：窗未滿 ⇒ NaN（ICPOSTLEAK 語意）：七組合之首個有限值列＝輸入首個有限值＋Σ(啟用步驟窗−1)，
    正式臂與 legacy 臂相同；真實 kline 全部 symbol×tf 之 close／volume 及晚生欄（前段 NaN）。"""
    k_cfg = ICPL["kline"]
    bad: List[str] = []
    for symbol, tf in _kline_symbol_tfs():
        k = fsh.kline_frame(symbol=symbol, timeframe=tf).iloc[: int(k_cfg["rows"])]
        frame = k[list(k_cfg["columns"])].astype(np.float64).copy()
        late = frame[k_cfg["columns"][0]].copy()
        late.iloc[: int(k_cfg["late_born_nan_rows"])] = np.nan
        frame[k_cfg["late_born_column"]] = late
        firsts = [int(np.argmax(np.isfinite(frame[c].to_numpy()))) for c in frame.columns]
        for combo in COMBOS:
            spec = _post_ic_spec(_combo_config(combo))
            add = (spec.rank_window - 1 if spec.rank else 0) + (spec.gaussian_window - 1 if spec.gaussian else 0) \
                + (spec.zscore_window - 1 if spec.zscore else 0)
            expected = [f + add if f + add < len(frame) else -1 for f in firsts]
            formal, legacy = _formal_vs_legacy(frame, combo)
            for name, arr in (("formal", formal), ("legacy", legacy)):
                got = [int(np.argmax(np.isfinite(arr[:, j]))) if np.isfinite(arr[:, j]).any() else -1
                       for j in range(arr.shape[1])]
                nan_ok = all(np.isnan(arr[: (e if e >= 0 else len(frame)), j]).all() for j, e in enumerate(expected))
                if got != expected or not nan_ok:
                    bad.append(f"{symbol}/{tf}|{'+'.join(combo)}|{name}：{got} ≠ {expected}")
    assert bad == [], bad[:20]


# ============================================================================================== Task 3.2 — D-MTF

def _primary_single_tf_run(runs: _Runs, run_b: CellRun) -> CellRun:
    symbol, primary = str(run_b.cell["symbol"]), str(run_b.cell["timeframes"][0])
    match = [c for c in _cells("A") if str(c["symbol"]) == symbol and list(c["timeframes"]) == [primary]]
    assert len(match) == 1, f"格 A 無 {symbol}/{primary} 之單週期格"
    return runs.get("A", match[0])


def _main_exit_violations(run: CellRun) -> Tuple[List[str], int]:
    bad: List[str] = []
    compared = 0
    for ex in run.exits:
        if ex.dtypes and ex.dtypes != ("float32",):
            bad.append(f"{run.key}|{ex.tf}|{ex.layer}|calib={ex.calibration}|dtypes={ex.dtypes}")
        if ex.ulp_violations:
            bad.append(f"{run.key}|{ex.tf}|{ex.layer}|ulp={ex.ulp_violations}")
        compared += ex.compared
    return bad, compared


def test_mtf_dtype_layer_exits_float32_and_primary_columns_equal_single_tf(runs: _Runs) -> None:
    """D-MTF 改案兩路 oracle：格 B 全部格之 L1–L6 層出口皆 float32 且對同層 float64 回傳 ≤1 ulp（「獨立 float64 重算」
    取該層函式之未轉型回傳，見報告）；格 B 之主週期欄對同 symbol 同週期之格 A 單週期 run 逐位元相等。"""
    _require_decision(D_MTF[0], D_MTF[1])
    bad: List[str] = []
    compared = 0
    for run in runs.all("B"):
        b, n = _main_exit_violations(run)
        bad.extend(b)
        compared += n
        single = _primary_single_tf_run(runs, run)
        fp_b = nh.fingerprints(run.handle.run_dir, "raw")
        fp_a = nh.fingerprints(single.handle.run_dir, "raw")
        common = set(fp_a["columns"]) & set(fp_b["columns"])
        assert common, f"{run.key}：與單週期格無共同欄"
        bad.extend(f"{run.key}|{d}" for d in _column_bitwise_diff(fp_a, fp_b, common))
    assert compared > 0, "層出口無可比之有限格"
    assert bad == [], bad[:30]


def test_boundary_31_mtf_dtype_single_training_timeframe_equals_single_tf(runs: _Runs, tmp_path: Path) -> None:
    """邊界②（Task 3.2）：多週期格中只有單一訓練週期（＝主週期）⇒ raw 全表對同 symbol 同週期之單週期格逐位元相等。"""
    _require_decision(D_MTF[0], D_MTF[1])
    cell = dict(_cells("B")[0])
    cell["timeframes"] = [cell["timeframes"][0]]
    run = _generate(tmp_path, "B", cell)
    single = _primary_single_tf_run(runs, run)
    assert nh.bitwise_diff(nh.fingerprints(single.handle.run_dir, "raw"), nh.fingerprints(run.handle.run_dir, "raw")) == []


def _force_preserve_dtype(factory_cls: Any, value: bool) -> Patch:
    """（生成 patch）`factory_cls._execute_layer1_6` 一律以 `preserve_dtype=value` 執行。"""

    def patch(mp: pytest.MonkeyPatch, _run: CellRun) -> None:
        current = factory_cls._execute_layer1_6

        def mutant(self: Any, layer_name: str, func: Callable, *args: Any, preserve_dtype: bool = False) -> Any:
            return current(self, layer_name, func, *args, preserve_dtype=value)

        mp.setattr(factory_cls, "_execute_layer1_6", mutant)

    return patch


def test_mutation_mtf_dtype_preserve_dtype_restored_breaks_exit_dtype(tmp_path: Path) -> None:
    """mutation：改案還原（多週期層間保留 float64）⇒ 層出口 dtype 案紅。"""
    _require_decision(D_MTF[0], D_MTF[1])
    run = _generate(tmp_path, "B", _cells("B")[0], patches=[_force_preserve_dtype(ff_mod.FeatureFactory, True)])
    bad, _n = _main_exit_violations(run)
    assert any("dtypes=" in b for b in bad), "層出口保留 float64 未被偵測"


def test_mtf_retained_multi_tf_raw_bitwise_equal_frozen(runs: _Runs) -> None:
    """D-MTF 保留（R6-B）：格 B 全部格之 raw 對 §G G3 改前凍結逐位元相等。"""
    _require_decision(D_MTF[0], D_MTF[2])
    bad: List[str] = []
    for run in runs.all("B"):
        bad.extend(f"{run.key}|{d}" for d in nh.bitwise_diff(_frozen_fp("B", run.key, FROZEN_RAW_B),
                                                             nh.fingerprints(run.handle.run_dir, "raw")))
    assert bad == [], bad[:30]


def test_mutation_mtf_retained_float32_exit_breaks_bitwise(tmp_path: Path) -> None:
    """mutation（R6-B）：保留分支下套用候選改案（多週期層出口改 float32）⇒ 逐位元案紅。"""
    _require_decision(D_MTF[0], D_MTF[2])
    cell = _cells("B")[0]
    run = _generate(tmp_path, "B", cell, patches=[_force_preserve_dtype(ff_mod.FeatureFactory, False)])
    assert nh.bitwise_diff(_frozen_fp("B", run.key, FROZEN_RAW_B), nh.fingerprints(run.handle.run_dir, "raw"))


# ============================================================================================== Task 3.2 — D-MEMMAP

def _memmap_inputs(symbol: str, tf: str) -> List[pd.DataFrame]:
    """真實 kline 欄切成三個 frame（兩個 float64、一個 float32），模擬多週期 float64 層與單週期 float32 層之合併輸入。"""
    k = fsh.kline_frame(symbol=symbol, timeframe=tf)
    cols = [str(c) for c in k.columns]
    assert len(cols) >= 3, cols
    third = max(1, len(cols) // 3)
    return [k[cols[:third]].astype(np.float64), k[cols[third: 2 * third]].astype(np.float64),
            k[cols[2 * third:]].astype(np.float32)]


def _concat_fp(dfs: List[pd.DataFrame], threshold: int) -> Mapping[str, Any]:
    """`concat_with_memmap` 於指定門檻之輸出值指紋（DataFrame 版）。"""
    out = memmap_utils.concat_with_memmap([d.copy() for d in dfs], threshold_bytes=int(threshold))
    return nh.frame_fingerprints(out)


def test_memmap_dtype_forced_branches_bitwise_equal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """D-MEMMAP 改案：同輸入（真實 kline 全部 symbol×tf）強制兩支（門檻 0 ⇒ memmap 支、門檻極大 ⇒ 一般 concat 支）
    輸出 dtype 與值逐位元相等。"""
    _require_decision(D_MEMMAP[0], D_MEMMAP[1])
    import tempfile

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    bad: List[str] = []
    for symbol, tf in _kline_symbol_tfs():
        dfs = _memmap_inputs(symbol, tf)
        diff = nh.bitwise_diff(_concat_fp(dfs, 0), _concat_fp(dfs, 1 << 62))
        bad.extend(f"{symbol}/{tf}|{d}" for d in diff)
    assert bad == [], bad[:30]


def test_boundary_30_memmap_dtype_threshold_exact_and_neighbours_identical(monkeypatch: pytest.MonkeyPatch,
                                                                            tmp_path: Path) -> None:
    """邊界①（Task 3.2）：資料量恰等於門檻與 ±1（門檻設為真實輸入之估計位元組 est−1、est、est+1；`concat_with_memmap`
    之預設門檻於定義時綁定，故以參數傳入）⇒ 三者輸出 dtype／值逐位元相同。"""
    _require_decision(D_MEMMAP[0], D_MEMMAP[1])
    import tempfile

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    symbol, tf = _kline_symbol_tfs()[0]
    dfs = _memmap_inputs(symbol, tf)
    est = int(dfs[0].shape[0] * sum(d.shape[1] for d in dfs) * 4)
    monkeypatch.setattr(memmap_utils, "MEMMAP_THRESHOLD_BYTES", est)
    fps = [_concat_fp(dfs, t) for t in (est - 1, est, est + 1)]
    assert nh.bitwise_diff(fps[0], fps[1]) == [] and nh.bitwise_diff(fps[1], fps[2]) == []


def _coupled_concat(dfs: List[pd.DataFrame], index: Optional[pd.Index] = None,
                    threshold_bytes: int = memmap_utils.MEMMAP_THRESHOLD_BYTES) -> pd.DataFrame:
    """改前之耦合行為複本：門檻下 `pd.concat` 保原 dtype、門檻上 float32。"""
    valid = [d for d in dfs if d is not None and not d.empty]
    if not valid:
        return pd.DataFrame(index=index)
    est = valid[0].shape[0] * sum(d.shape[1] for d in valid) * 4
    out = pd.concat(valid, axis=1, copy=False)
    if est >= threshold_bytes:
        out = out.astype(np.float32)
    if index is not None:
        out.index = index
    return out


def test_mutation_memmap_dtype_coupled_breaks_equality(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：改案還原（合併 dtype 依資料量耦合）⇒ 兩支逐位元案紅。"""
    _require_decision(D_MEMMAP[0], D_MEMMAP[1])
    monkeypatch.setattr(memmap_utils, "concat_with_memmap", _coupled_concat)
    symbol, tf = _kline_symbol_tfs()[0]
    dfs = _memmap_inputs(symbol, tf)
    assert nh.bitwise_diff(_concat_fp(dfs, 0), _concat_fp(dfs, 1 << 62))


def test_memmap_retained_l3_l4_downstream_bitwise_equal_frozen(runs: _Runs) -> None:
    """D-MEMMAP 保留（R6-B）：格 A／B 全部格之 L3／L4 合併下游欄對 §G 凍結逐位元相等。"""
    _require_decision(D_MEMMAP[0], D_MEMMAP[2])
    bad: List[str] = []
    seen = 0
    for kind, artifact in (("A", FROZEN_RAW_A), ("B", FROZEN_RAW_B)):
        for run in runs.all(kind):
            names = _layer_columns(run.handle.run_dir, ("L3", "L4"))
            seen += len(names)
            bad.extend(f"{kind}|{run.key}|{d}" for d in _column_bitwise_diff(
                _frozen_fp(kind, run.key, artifact), nh.fingerprints(run.handle.run_dir, "raw"), names))
    assert seen > 0, "無 L3／L4 欄 ⇒ 本案無對象"
    assert bad == [], bad[:30]


def test_mutation_memmap_retained_decoupled_breaks_bitwise(tmp_path: Path) -> None:
    """mutation（R6-B）：保留分支下套用候選改案（合併 dtype 脫鉤：一律 float32）於多週期格 ⇒ L3／L4 逐位元案紅。"""
    _require_decision(D_MEMMAP[0], D_MEMMAP[2])

    def patch(mp: pytest.MonkeyPatch, _run: CellRun) -> None:
        real = memmap_utils.concat_with_memmap
        mp.setattr(memmap_utils, "concat_with_memmap",
                   lambda dfs, index=None, threshold_bytes=memmap_utils.MEMMAP_THRESHOLD_BYTES:
                   real([d.astype(np.float32) for d in dfs if d is not None], index=index,
                        threshold_bytes=threshold_bytes))

    run = _generate(tmp_path, "B", _cells("B")[0], patches=[patch])
    names = _layer_columns(run.handle.run_dir, ("L3", "L4"))
    assert names
    assert _column_bitwise_diff(_frozen_fp("B", run.key, FROZEN_RAW_B), nh.fingerprints(run.handle.run_dir, "raw"),
                                names)


# ============================================================================================== Task 3.2 — D-WINSOR-DTYPE

def _winsor_cfg(method: str) -> Dict[str, Any]:
    from momentum.FeatureEngineering.feature_config import WinsorConfig

    winsor = WinsorConfig().model_dump()
    winsor.update(enabled=True, method=method)
    return {"enabled": True, "mode": "replace", "causal_preprocessing": True, "winsorization": winsor,
            "fractional_differencing": {"enabled": False}, "adf_differencing": {"enabled": False},
            "rank_transform": {"enabled": False}, "adaptive_zscore": {"enabled": False},
            "gaussian_normalize": {"enabled": False}}


def _winsor_outputs() -> Iterable[Tuple[str, np.ndarray, np.ndarray]]:
    """真實 kline 全部 symbol×tf 之數值欄經 sigma 與 quantile 兩分支之 `_winsorize_2d_legacy_equivalent`。"""
    for symbol, tf in _kline_symbol_tfs():
        arr = fsh.kline_frame(symbol=symbol, timeframe=tf).to_numpy(dtype=np.float64)
        sigma = FeaturePreprocessor(_winsor_cfg("sigma"))._winsorize_2d_legacy_equivalent(arr.copy())
        quantile = FeaturePreprocessor(_winsor_cfg("quantile"))._winsorize_2d_legacy_equivalent(arr.copy())
        yield f"{symbol}/{tf}", np.asarray(sigma), np.asarray(quantile)


def test_winsor_dtype_sigma_quantile_same_dtype_and_fracdiff_within_1ulp() -> None:
    """D-WINSOR-DTYPE 改案兩路 oracle：sigma／quantile 兩分支回傳 dtype 相同；後續 fracdiff（`_frac_diff_ffd`）對獨立
    FFD 重算 ≤1 ulp、NaN 遮罩 exact（d 取生產預設 `d_range` 上半之 0.5／0.75／1.0 倍上界、權重門檻取預設）。"""
    _require_decision(D_WINSOR[0], D_WINSOR[1])
    from momentum.FeatureEngineering.feature_config import FractionalDifferencingConfig

    fd = FractionalDifferencingConfig()
    ds = [float(fd.d_range[1]) * q for q in (0.5, 0.75, 1.0)]
    bad: List[str] = []
    for tag, sigma, quantile in _winsor_outputs():
        if sigma.dtype != quantile.dtype:
            bad.append(f"{tag}：sigma {sigma.dtype} ≠ quantile {quantile.dtype}")
        for arr in (sigma, quantile):
            for j in range(arr.shape[1]):
                for d in ds:
                    got = FeaturePreprocessor._frac_diff_ffd(pd.Series(arr[:, j]), d,
                                                             threshold=float(fd.weight_threshold)).to_numpy()
                    rep = _ulp_report(got, _ffd_oracle(arr[:, j], d, float(fd.weight_threshold)))
                    if rep["violations"] or rep["nan_mismatch"] or rep["nonfinite_bad"]:
                        bad.append(f"{tag}|col{j}|d={d}：{rep}")
    assert bad == [], bad[:20]


def test_mutation_winsor_dtype_sigma_float64_restored_breaks_dtype(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：改案還原（sigma 回 float64、quantile 回 float32）⇒ 兩分支 dtype 相同案紅。"""
    _require_decision(D_WINSOR[0], D_WINSOR[1])
    real = FeaturePreprocessor._winsorize_2d_legacy_equivalent

    def mutant(self: Any, arr: np.ndarray) -> np.ndarray:
        out = np.asarray(real(self, arr))
        return out.astype(np.float64 if self.winsor_config.get("method") == "sigma" else np.float32)

    monkeypatch.setattr(FeaturePreprocessor, "_winsorize_2d_legacy_equivalent", mutant)
    _tag, sigma, quantile = next(iter(_winsor_outputs()))
    assert sigma.dtype != quantile.dtype


def test_winsor_dtype_retained_slow_path_raw_bitwise_and_sigma_float64(runs: _Runs) -> None:
    """D-WINSOR-DTYPE 保留（R6-B）：格 A 全部格之 raw（含 pre-IC 慢臂縮尾後欄）對 §G G2 凍結逐位元相等；sigma 分支回傳
    dtype 維持現行 float64（quantile float32）——凍結格之縮尾為生產預設 quantile，sigma 之保留以直接呼叫釘住。"""
    _require_decision(D_WINSOR[0], D_WINSOR[2])
    bad: List[str] = []
    for run in runs.all("A"):
        bad.extend(f"{run.key}|{d}" for d in nh.bitwise_diff(_frozen_fp("A", run.key, FROZEN_RAW_A),
                                                             nh.fingerprints(run.handle.run_dir, "raw")))
    for tag, sigma, quantile in _winsor_outputs():
        if sigma.dtype != np.float64 or quantile.dtype != np.float32:
            bad.append(f"{tag}：sigma {sigma.dtype}／quantile {quantile.dtype}")
    assert bad == [], bad[:30]


def test_mutation_winsor_dtype_retained_sigma_float32_breaks_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（R6-B）：保留分支下套用候選改案（sigma 縮尾改回 float32）⇒ 保留釘住案紅。"""
    _require_decision(D_WINSOR[0], D_WINSOR[2])
    real = FeaturePreprocessor._winsorize_2d_legacy_equivalent
    monkeypatch.setattr(FeaturePreprocessor, "_winsorize_2d_legacy_equivalent",
                        lambda self, arr: np.asarray(real(self, arr)).astype(np.float32))
    _tag, sigma, _quantile = next(iter(_winsor_outputs()))
    assert sigma.dtype != np.float64


# ============================================================================================== Task 3.2 — D-CODEC

def _codec_section() -> Dict[str, Any]:
    """契約 `processed_codec_mapping`（Task 3.2 填）；本檔所需之鍵缺 ⇒ 紅。"""
    section = dict(nv.load_contract()["processed_codec_mapping"])
    for key in ("mapping", "outcome_values", "binding_keys", "normalization", "manifest_key", "outcome_by_case",
                "registry_keys"):
        assert section.get(key), f"契約 processed_codec_mapping.{key} 未填"
    outcomes = set(section["outcome_values"]["values"])
    for case in CODEC_CASES + ("invalid_rank_window",):
        assert section["outcome_by_case"].get(case) in outcomes, f"outcome_by_case.{case} 不屬 outcome_values"
    for key in ("outcome", "mapping_sha256"):
        assert section["registry_keys"].get(key), f"registry_keys.{key} 未填"
    return section


_UNKNOWN = object()


def _expected_encoding(section: Mapping[str, Any], statuses: Mapping[str, Any]) -> Any:
    """依契約映射表之獨立查表：三步驟狀態組合 → 編碼型別（None＝無損）；不在表 ⇒ `_UNKNOWN`。"""
    for entry in section["mapping"]:
        if all(str(entry.get(step)) == str(statuses.get(step)) for step in CODEC_STEPS):
            return entry.get("encoding")
    return _UNKNOWN


def _arrow_type_of(encoding: Optional[str]) -> Tuple[str, ...]:
    if encoding == fs_mod.RANK_UINT16_ENCODING:
        return ("uint16",)
    if encoding in (fs_mod.ZSCORE_INT16_ENCODING, fs_mod.GAUSSIAN_INT16_ENCODING):
        return ("int16",)
    return ("float", "halffloat")


def _mapping_digest(table: pd.DataFrame, normalization: Mapping[str, Any]) -> str:
    """契約正規化之獨立重算：依 `sort_by` 穩定排序、取 `columns` 之固定欄序為列陣列、正規 JSON（緊湊分隔）之 sha256。"""
    cols = [str(c) for c in normalization["columns"]]
    rows = table.sort_values(str(normalization["sort_by"]), kind="mergesort") if len(table) else table
    payload = [[None if (isinstance(v, float) and np.isnan(v)) else (v.item() if hasattr(v, "item") else v)
                for v in row] for row in rows.reindex(columns=cols).itertuples(index=False)]
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _has_codec_literal(name: str) -> bool:
    lowered = name.lower()
    return any(t in lowered for t in ("zscore", "gaussian", "gauss", "rank"))


def _legacy_name_encoding(name: str) -> Tuple[Optional[str], Optional[int]]:
    """改前欄名推斷之獨立複本（`_infer_l7_processed_encoding` 之規則）。"""
    import re

    lowered = name.lower()
    if "zscore" in lowered:
        return fs_mod.ZSCORE_INT16_ENCODING, None
    if "gaussian" in lowered or "gauss" in lowered:
        return fs_mod.GAUSSIAN_INT16_ENCODING, None
    if "rank" in lowered:
        for pattern in (r"(?i)(?:rank|tsrank)[_\-]?w?([0-9]+)", r"(?i)w([0-9]+)[_\-]?(?:rank|tsrank)"):
            m = re.search(pattern, name)
            if m:
                return fs_mod.RANK_UINT16_ENCODING, int(m.group(1))
        return fs_mod.RANK_UINT16_ENCODING, None
    return None, None


@dataclasses.dataclass
class CodecInputs:
    handle: Any
    col_a: str
    col_b: str
    frame_a: pd.DataFrame
    frame_b: pd.DataFrame


def _codec_inputs(runs: _Runs) -> CodecInputs:
    """真實 raw 特徵：`col_a`＝名含 rank／zscore／gaussian 字面者（優先 zscore／gauss 字面，使欄名推斷可編碼）、
    `col_b`＝IC-first 選欄中名不含任何字面者；同一格。全部格皆無 ⇒ 紅（前提）。"""
    from momentum.FeatureEngineering.feature_naming import is_ratio_unsafe_column

    for run in runs.all("A"):
        names = [n for n in ph.group_columns(run.handle.run_dir, "raw") if not is_ratio_unsafe_column(n)]
        literal = sorted((n for n in names if _has_codec_literal(n)),
                         key=lambda n: (_legacy_name_encoding(n)[0] == fs_mod.RANK_UINT16_ENCODING, n))
        plain = [n for n in _ic_first_call(run).selected if n in names and not _has_codec_literal(n)]
        if not literal or not plain:
            continue
        stored = ph.stored_columns(run.handle.run_dir, [literal[0], plain[0]], "raw")
        index = _raw_row_index(run.handle)
        frame_a = pd.DataFrame({literal[0]: np.asarray(stored[literal[0]][0], dtype=np.float32)}, index=index)
        frame_b = pd.DataFrame({plain[0]: np.asarray(stored[plain[0]][0], dtype=np.float32)}, index=index)
        if np.isfinite(frame_a.to_numpy()).sum() > max(Z_WINDOWS) and np.isfinite(frame_b.to_numpy()).sum() > RANK_W:
            return CodecInputs(run.handle, literal[0], plain[0], frame_a, frame_b)
    raise AssertionError("格 A 全部格無「名含字面」與「名不含字面之選欄」並存且有足夠有限值之格（D-CODEC (i) 前提）")


def _codec_cfgs() -> Tuple[Any, Any]:
    z = create_post_ic_transform_config(rank=False, rank_window=RANK_W, zscore=True, zscore_windows=list(Z_WINDOWS),
                                        gaussian=False)
    r = create_post_ic_transform_config(rank=True, rank_window=RANK_W, zscore=False, zscore_windows=list(Z_WINDOWS),
                                        gaussian=False)
    return z, r


@dataclasses.dataclass
class CodecWrite:
    run_dir: Path
    handle: Any
    error: Optional[BaseException]
    tables: List[Dict[str, Any]]
    outputs: Dict[str, pd.DataFrame]
    records: Dict[Tuple[str, str], Dict[str, Any]]


def _codec_write(root: Path, mp: pytest.MonkeyPatch, inputs: CodecInputs, *, codec_on: bool = True,
                 edit: Optional[Callable[[Dict[Tuple[str, str], Dict[str, Any]]], None]] = None,
                 post_ic_config: Any = None, empty: bool = False) -> CodecWrite:
    """col_a 只做 zscore、col_b 只做 rank（兩次正式臂轉換、合併紀錄）後直接 `write_processed`；`_build_l7_v2_table`
    以 spy 擷取每群組之 Arrow 型別與 encoding registry（寫入失敗亦可觀測）。"""
    mp.setenv("FFACT_L7_CODEC_UPGRADE", "1" if codec_on else "0")
    cfg_z, cfg_r = _codec_cfgs()
    arm = _formal_arm()
    groups: Dict[str, pd.DataFrame] = {}
    records: Dict[Tuple[str, str], Dict[str, Any]] = {}
    exec_groups: Dict[str, Dict[str, Any]] = {}
    if not empty:
        for gid, frame, cfg in (("numview_a", inputs.frame_a, cfg_z), ("numview_b", inputs.frame_b, cfg_r)):
            pre = FeaturePreprocessor(cfg.model_dump())
            out = pre.transform_selected(list(frame.columns), {gid: frame.copy()}, config=cfg, arm=arm)
            groups.update(out)
            recs, grps = pre.last_post_ic_execution()
            records.update(recs)
            exec_groups.update(grps)
    if edit is not None:
        edit(records)
    tables: List[Dict[str, Any]] = []
    real = FeatureStorage._build_l7_v2_table

    def spy(self: Any, *args: Any, **kwargs: Any) -> Any:
        res = real(self, *args, **kwargs)
        table = res[0]
        tables.append({"types": {n: str(table.schema.field(n).type) for n in table.column_names},
                       "registry": copy.deepcopy(dict(res[2] or {}))})
        return res

    mp.setattr(FeatureStorage, "_build_l7_v2_table", spy)
    handle = inputs.handle
    row_index = inputs.frame_a.index if not empty else inputs.frame_a.index[:0]
    run_dir, error = _direct_write_processed(root, handle.symbol, handle.tf, "numview_codec", groups,
                                             (records, exec_groups), row_index, arm,
                                             post_ic_config=cfg_r if post_ic_config is None else post_ic_config)
    rh = ph.RunHandle(run_dir=run_dir, features_root=Path(root), symbol=handle.symbol, tf=handle.tf,
                      config_hash="numview_codec")
    return CodecWrite(run_dir, rh, error, tables, groups, records)


def _merged_capture(write: CodecWrite) -> Tuple[Dict[str, str], Dict[str, Dict[str, Any]]]:
    types: Dict[str, str] = {}
    registry: Dict[str, Dict[str, Any]] = {}
    for t in write.tables:
        types.update(t["types"])
        registry.update(t["registry"])
    return types, registry


def _readback_violations(section: Mapping[str, Any], write: CodecWrite) -> List[str]:
    """(i)：每個落盤欄之編碼型別＝依讀回紀錄表狀態與契約映射表之獨立查表；有損欄讀回誤差 ≤ 1／scale_factor。"""
    import pyarrow.parquet as pq

    table = ph.provenance_table(write.run_dir, "processed")
    status = {str(r["output_column"]): {s: r[s] for s in CODEC_STEPS} for _i, r in table.iterrows()}
    bad: List[str] = []
    for path in ph.declared_group_files(write.run_dir, "processed"):
        pf = pq.read_table(str(path))
        meta = json.loads((pf.schema.metadata or {}).get(fs_mod.L7_ENCODING_REGISTRY_METADATA_KEY.encode(), b"{}"))
        for name in pf.column_names:
            if name in ph.NON_FEATURE_COLUMNS:
                continue
            want = _expected_encoding(section, status[name])
            got_type = str(pf.schema.field(name).type)
            if want is _UNKNOWN or got_type not in _arrow_type_of(want):
                bad.append(f"{name}：期望 {want}，落盤 {got_type}")
                continue
            if want is None:
                continue
            entry = meta.get(name) or {}
            if entry.get("encoding_type") != want:
                bad.append(f"{name}：registry {entry.get('encoding_type')} ≠ {want}")
                continue
            raw = np.asarray(pf.column(name).to_numpy(zero_copy_only=False))
            decoded = (fs_mod.decode_rank_from_uint16(raw, int(entry["window"])) if want == fs_mod.RANK_UINT16_ENCODING
                       else fs_mod.decode_zscore_from_int16(raw))
            ref = np.asarray(write.outputs[next(g for g, f in write.outputs.items() if name in f.columns)][name],
                             dtype=np.float32)
            finite = np.isfinite(ref)
            if not np.array_equal(np.isnan(decoded), np.isnan(ref)) or \
                    np.max(np.abs(decoded[finite] - ref[finite]), initial=0.0) > 1.0 / float(entry["scale_factor"]):
                bad.append(f"{name}：讀回誤差超出編碼容差")
    return bad


def test_codec_by_provenance_encoding_follows_records_not_names(runs: _Runs, tmp_path: Path,
                                                                monkeypatch: pytest.MonkeyPatch) -> None:
    """D-CODEC (i)：名含字面而只做 zscore 之真實 raw 欄、及名不含字面而做 rank 之欄，編碼型別皆等於依讀回紀錄與契約
    映射表之獨立重算（非名稱），讀回誤差在該編碼容差內。"""
    _require_decision(D_CODEC[0], D_CODEC[1])
    section = _codec_section()
    write = _codec_write(tmp_path / "features", monkeypatch, _codec_inputs(runs))
    assert write.error is None, write.error
    assert _readback_violations(section, write) == []


@pytest.mark.parametrize("case", CODEC_CASES)
def test_codec_by_provenance_anomalies_lossless_and_recorded(case: str, runs: _Runs, tmp_path: Path,
                                                             monkeypatch: pytest.MonkeyPatch) -> None:
    """D-CODEC (ii)：刪一欄紀錄／複製一欄紀錄／綁定四元改一值（紀錄鍵之週期改為他週期）／步驟狀態改為映射表外之組合
    ⇒ 該欄落盤（或寫入前之表）為 float32、encoding registry 記對應異常結果、無任何有損欄；刪／複製另使寫入失敗
    （PRE-PROV 窮盡性）且 run 不可讀為完整。"""
    _require_decision(D_CODEC[0], D_CODEC[1])
    section = _codec_section()
    inputs = _codec_inputs(runs)
    other_tf = next(tf for _s, tf in _kline_symbol_tfs() if tf != inputs.handle.tf)
    step_values = {s: ph.contract_values(f"step_status_values.{s}") for s in CODEC_STEPS}

    def edit(records: Dict[Tuple[str, str], Dict[str, Any]]) -> None:
        key = next(k for k in records if k[1] == inputs.col_a)
        if case == "missing":
            records.pop(key)
        elif case == "duplicate":
            records[(other_tf, inputs.col_a)] = copy.deepcopy(records[key])
        elif case == "stale":
            records[(other_tf, inputs.col_a)] = records.pop(key)
        else:
            combo = next(c for c in itertools.product(*(step_values[s] for s in CODEC_STEPS))
                         if _expected_encoding(section, dict(zip(CODEC_STEPS, c))) is _UNKNOWN)
            records[key] = dict(records[key], **dict(zip(CODEC_STEPS, combo)))

    write = _codec_write(tmp_path / "features", monkeypatch, inputs, edit=edit)
    types, registry = _merged_capture(write)
    assert types.get(inputs.col_a) == "float", (case, types.get(inputs.col_a))
    assert registry.get(inputs.col_a, {}).get(section["registry_keys"]["outcome"]) == section["outcome_by_case"][case]
    assert not [n for n, t in types.items() if t in LOSSY_ARROW_TYPES], types
    if case in ("missing", "duplicate"):
        assert write.error is not None, "缺／重複紀錄應使寫入失敗（PRE-PROV 窮盡性）"
        assert not ph._strict_readable(write.handle, "processed")


def _tamper_record(mp: pytest.MonkeyPatch) -> None:
    """紀錄檔寫畢、manifest 合併前竄改紀錄表一格步驟狀態，並以竄改後之檔位元組重算指標 sha256（使只靠檔雜湊者無從察覺）。"""
    import pyarrow as pa
    import pyarrow.parquet as pq

    real = rp_mod.write_provenance_table

    def mutant(table: pd.DataFrame, staging_dir: Path, artifact_kind: str, *args: Any, **kwargs: Any) -> Any:
        pointer = real(table, staging_dir, artifact_kind, *args, **kwargs)
        if artifact_kind != "processed" or not len(table):
            return pointer
        target = Path(staging_dir) / pointer.path
        arrow = pq.read_table(str(target))
        frame = arrow.to_pandas()
        step = CODEC_STEPS[0]
        values = [v for v in ph.contract_values(f"step_status_values.{step}") if v != frame.loc[0, step]]
        frame.loc[0, step] = values[0]
        pq.write_table(pa.Table.from_pandas(frame, schema=arrow.schema, preserve_index=False), str(target),
                       compression="zstd")
        return dataclasses.replace(pointer, sha256=rp_mod.file_sha256(target))

    mp.setattr(rp_mod, "write_provenance_table", mutant)


def test_codec_by_provenance_mapping_digest_bound_and_tamper_fails(runs: _Runs, tmp_path: Path,
                                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    """D-CODEC (iii)：正常寫入後 manifest `mapping_sha256`＝自讀回紀錄表依契約正規化獨立重算之值，且 ≠
    `provenance.sha256`（兩者不同源）；紀錄檔寫畢、manifest 合併前竄改紀錄表 ⇒ 寫入失敗、run 不可讀為完整。"""
    _require_decision(D_CODEC[0], D_CODEC[1])
    section = _codec_section()
    inputs = _codec_inputs(runs)
    write = _codec_write(tmp_path / "ok", monkeypatch, inputs)
    assert write.error is None, write.error
    node = ph.load_manifest(write.run_dir)["artifacts"]["processed"]
    digest = _mapping_digest(ph.provenance_table(write.run_dir, "processed"), section["normalization"])
    assert node.get(section["manifest_key"]) == digest
    assert digest != node["provenance"]["sha256"]
    with monkeypatch.context() as mp:
        _tamper_record(mp)
        tampered = _codec_write(tmp_path / "tampered", mp, inputs)
    assert tampered.error is not None, "竄改紀錄表後寫入未失敗"
    assert not ph._strict_readable(tampered.handle, "processed")


def test_mutation_codec_by_provenance_digest_vs_file_sha_breaks_normal_write(runs: _Runs, tmp_path: Path,
                                                                             monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：摘要比對改為比 `provenance.sha256`（紀錄檔位元組雜湊）⇒ (iii) 之正常寫入案紅（恆不等而失敗）。"""
    _require_decision(D_CODEC[0], D_CODEC[1])

    def mutant(self: Any, record_path: Path, mapping_sha256: str) -> None:
        if rp_mod.file_sha256(Path(record_path)) != mapping_sha256:
            raise ValueError("mapping_sha256 ≠ provenance.sha256")

    monkeypatch.setattr(FeatureStorage, "_verify_codec_mapping_digest", mutant)
    write = _codec_write(tmp_path / "features", monkeypatch, _codec_inputs(runs))
    assert write.error is not None, "比檔雜湊之 mutant 應使正常寫入失敗"


def test_mutation_codec_by_provenance_readback_check_removed_breaks_tamper(runs: _Runs, tmp_path: Path,
                                                                           monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：移除讀回重算比對 ⇒ (iii) 之竄改案紅（竄改後寫入成功、run 可讀為完整）。"""
    _require_decision(D_CODEC[0], D_CODEC[1])
    monkeypatch.setattr(FeatureStorage, "_verify_codec_mapping_digest", lambda self, record_path, mapping_sha256: None)
    _tamper_record(monkeypatch)
    write = _codec_write(tmp_path / "features", monkeypatch, _codec_inputs(runs))
    assert write.error is None and ph._strict_readable(write.handle, "processed")


def test_mutation_codec_by_provenance_manifest_without_digest_breaks_binding(runs: _Runs, tmp_path: Path,
                                                                             monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：manifest 不記 `mapping_sha256`（合併後自 processed 節點移除該鍵）⇒ (iii) 紅。"""
    _require_decision(D_CODEC[0], D_CODEC[1])
    section = _codec_section()
    real = FeatureStorage._atomic_merge_feature_manifest_v2

    def mutant(self: Any, run_dir: Path, *args: Any, **kwargs: Any) -> Any:
        res = real(self, run_dir, *args, **kwargs)
        path = Path(run_dir) / ph.MANIFEST_NAME
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc.get("artifacts", {}).get("processed", {}).pop(section["manifest_key"], None)
        path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        return res

    monkeypatch.setattr(FeatureStorage, "_atomic_merge_feature_manifest_v2", mutant)
    write = _codec_write(tmp_path / "features", monkeypatch, _codec_inputs(runs))
    assert write.error is None, write.error
    node = ph.load_manifest(write.run_dir)["artifacts"]["processed"]
    digest = _mapping_digest(ph.provenance_table(write.run_dir, "processed"), section["normalization"])
    assert node.get(section["manifest_key"]) != digest, "manifest 缺 mapping_sha256 未被 (iii) 偵測"


def _legacy_name_table(self: Any, pa_module: Any, frame: pd.DataFrame, artifact_kind: str, *_a: Any,
                       **_k: Any) -> Any:
    """改前「欄名推斷」編碼之複本（`_infer_l7_processed_encoding` 規則＋往返容差回退 float32）。"""
    from momentum.core.config import get_l7_codec_upgrade_enabled

    if artifact_kind != "processed" or not get_l7_codec_upgrade_enabled():
        return pa_module.Table.from_pandas(frame, preserve_index=False), [], {}
    arrays, names, f32, registry = [], [], [], {}
    for column in frame.columns:
        name = str(column)
        values = frame[column].to_numpy(dtype=np.float32)
        enc, window = _legacy_name_encoding(name)
        encoded = None
        try:
            if enc == fs_mod.RANK_UINT16_ENCODING and window:
                encoded = fs_mod.encode_rank_as_uint16(values, window)
                self._assert_rank_roundtrip(values, fs_mod.decode_rank_from_uint16(encoded, window), window)
                registry[name] = {"encoding_type": enc, "scale_factor": str(window * 2), "window": str(window)}
            elif enc in (fs_mod.ZSCORE_INT16_ENCODING, fs_mod.GAUSSIAN_INT16_ENCODING):
                encoded = fs_mod.encode_zscore_as_int16(values)
                self._assert_zscore_roundtrip(values, fs_mod.decode_zscore_from_int16(encoded))
                registry[name] = {"encoding_type": enc, "scale_factor": str(int(fs_mod.ZSCORE_INT16_SCALE_FACTOR)),
                                  "window": None}
        except fs_mod.EncodeFallbackRequired:
            encoded = None
            registry.pop(name, None)
        if encoded is None:
            arrays.append(pa_module.array(values))
            f32.append(name)
        else:
            arrays.append(pa_module.array(encoded))
        names.append(name)
    return pa_module.Table.from_arrays(arrays, names=names), f32, registry


def test_mutation_codec_by_provenance_name_inference_restored_breaks_records(runs: _Runs, tmp_path: Path,
                                                                             monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：編碼判定改回欄名推斷 ⇒ (i) 之「名不含字面而做 rank」與「名含字面而只做 zscore」案紅。"""
    _require_decision(D_CODEC[0], D_CODEC[1])
    section = _codec_section()
    monkeypatch.setattr(FeatureStorage, "_build_l7_v2_table", _legacy_name_table)
    write = _codec_write(tmp_path / "features", monkeypatch, _codec_inputs(runs))
    assert write.error is None, write.error
    assert _readback_violations(section, write)


def _anomaly_reencode(always_lossy: bool) -> Callable[[pytest.MonkeyPatch, Mapping[str, Any]], None]:
    """異常欄改走欄名推斷（或一律 zscore_int16 有損）之 mutant。"""

    def install(mp: pytest.MonkeyPatch, section: Mapping[str, Any]) -> None:
        real = FeatureStorage._build_l7_v2_table
        outcome_key = section["registry_keys"]["outcome"]
        anomalies = set(section["outcome_values"]["values"])

        def mutant(self: Any, *args: Any, **kwargs: Any) -> Any:
            table, f32, registry = real(self, *args, **kwargs)[:3]
            import pyarrow as pa

            for name, entry in list((registry or {}).items()):
                if entry.get(outcome_key) not in anomalies:
                    continue
                enc = fs_mod.ZSCORE_INT16_ENCODING if always_lossy else _legacy_name_encoding(name)[0]
                if enc not in (fs_mod.ZSCORE_INT16_ENCODING, fs_mod.GAUSSIAN_INT16_ENCODING):
                    continue
                values = np.asarray(table.column(name).to_numpy(zero_copy_only=False), dtype=np.float32)
                table = table.set_column(table.column_names.index(name), name,
                                         pa.array(fs_mod.encode_zscore_as_int16(values)))
                registry[name] = dict(entry, encoding_type=enc)
            return table, f32, registry

        mp.setattr(FeatureStorage, "_build_l7_v2_table", mutant)

    return install


@pytest.mark.parametrize("always_lossy", [False, True], ids=["names_fallback", "still_lossy"])
def test_mutation_codec_by_provenance_anomaly_fallback_breaks_lossless(always_lossy: bool, runs: _Runs,
                                                                       tmp_path: Path,
                                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：異常時改為退回欄名推斷／改為仍採有損編碼 ⇒ (ii) 之「無任何有損欄」案紅（以步驟狀態不在映射表之案）。"""
    _require_decision(D_CODEC[0], D_CODEC[1])
    section = _codec_section()
    inputs = _codec_inputs(runs)
    assert _legacy_name_encoding(inputs.col_a)[0] in (fs_mod.ZSCORE_INT16_ENCODING, fs_mod.GAUSSIAN_INT16_ENCODING) \
        or always_lossy, "col_a 之欄名推斷不可編碼 ⇒ 名稱回退 mutant 無偵測力"
    step_values = {s: ph.contract_values(f"step_status_values.{s}") for s in CODEC_STEPS}

    def edit(records: Dict[Tuple[str, str], Dict[str, Any]]) -> None:
        key = next(k for k in records if k[1] == inputs.col_a)
        combo = next(c for c in itertools.product(*(step_values[s] for s in CODEC_STEPS))
                     if _expected_encoding(section, dict(zip(CODEC_STEPS, c))) is _UNKNOWN)
        records[key] = dict(records[key], **dict(zip(CODEC_STEPS, combo)))

    _anomaly_reencode(always_lossy)(monkeypatch, section)
    write = _codec_write(tmp_path / "features", monkeypatch, inputs, edit=edit)
    types, _registry = _merged_capture(write)
    assert [n for n, t in types.items() if t in LOSSY_ARROW_TYPES], "異常欄仍有損未被 (ii) 偵測"


def test_boundary_32_codec_by_provenance_zero_selected_no_encoding_zero_row_digest(
        runs: _Runs, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界③（Task 3.2）：processed 零選欄（紀錄零列）⇒ 無欄被編碼；manifest `mapping_sha256`＝讀回之零列紀錄表依契約
    正規化重算之摘要。"""
    _require_decision(D_CODEC[0], D_CODEC[1])
    section = _codec_section()
    write = _codec_write(tmp_path / "features", monkeypatch, _codec_inputs(runs), empty=True)
    assert write.error is None, write.error
    _types, registry = _merged_capture(write)
    assert not [n for n, e in registry.items() if e.get("encoding_type")]
    table = ph.provenance_table(write.run_dir, "processed")
    assert len(table) == 0
    node = ph.load_manifest(write.run_dir)["artifacts"]["processed"]
    assert node.get(section["manifest_key"]) == _mapping_digest(table, section["normalization"])


def test_boundary_33_codec_by_provenance_upgrade_off_no_mapping_lossless(runs: _Runs, tmp_path: Path,
                                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界④（Task 3.2）：`FFACT_L7_CODEC_UPGRADE` 關 ⇒ 不走映射（`_codec_mapping_from_execution` 呼叫 0 次、不讀紀錄）、
    全欄既有無損路徑（無整數型別、無 encoding registry）。"""
    _require_decision(D_CODEC[0], D_CODEC[1])
    calls: List[int] = []
    real = FeatureStorage._codec_mapping_from_execution

    def spy(self: Any, *args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        return real(self, *args, **kwargs)

    monkeypatch.setattr(FeatureStorage, "_codec_mapping_from_execution", spy)
    write = _codec_write(tmp_path / "features", monkeypatch, _codec_inputs(runs), codec_on=False)
    assert write.error is None, write.error
    types, registry = _merged_capture(write)
    assert calls == []
    assert types and not [n for n, t in types.items() if t in LOSSY_ARROW_TYPES]
    assert registry == {}


@pytest.mark.parametrize("window", [None, 0, -1], ids=["missing", "zero", "negative"])
def test_boundary_34_codec_by_provenance_rank_window_missing_or_nonpositive_float32(
        window: Optional[int], runs: _Runs, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界⑤（Task 3.2）：rank 窗於本次 post-IC 設定缺或非正 ⇒ 做 rank 之欄 float32 並記異常結果。"""
    _require_decision(D_CODEC[0], D_CODEC[1])
    section = _codec_section()
    inputs = _codec_inputs(runs)
    _cfg_z, cfg_r = _codec_cfgs()
    bad_cfg = cfg_r.model_dump()
    if window is None:
        bad_cfg["rank_transform"].pop("window", None)
    else:
        bad_cfg["rank_transform"]["window"] = window
    write = _codec_write(tmp_path / "features", monkeypatch, inputs, post_ic_config=bad_cfg)
    types, registry = _merged_capture(write)
    assert types.get(inputs.col_b) == "float", types.get(inputs.col_b)
    assert registry.get(inputs.col_b, {}).get(section["registry_keys"]["outcome"]) == \
        section["outcome_by_case"]["invalid_rank_window"]


def test_codec_retained_processed_bitwise_and_name_inference_kept(runs: _Runs, tmp_path: Path,
                                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    """D-CODEC 保留（R6-B）：凍結檔中每個含 processed 之格之 processed 讀回對 §G 凍結逐位元相等；codec 開時編碼仍依欄名
    （名不含字面而做 rank 之欄不編碼、名含字面之欄依名稱規則編碼）。"""
    _require_decision(D_CODEC[0], D_CODEC[2])
    bad: List[str] = []
    for kind in ("A", "B"):
        cells = _key_to_cell(kind)
        for key, node in _frozen_doc().get("cells", {}).get(kind, {}).items():
            if FROZEN_PROCESSED in node:
                run = runs.get(kind, cells[key])
                bad.extend(f"{kind}|{key}|{d}" for d in
                           nh.bitwise_diff(node[FROZEN_PROCESSED], nh.fingerprints(run.handle.run_dir, "processed")))
    inputs = _codec_inputs(runs)
    write = _codec_write(tmp_path / "features", monkeypatch, inputs)
    assert write.error is None, write.error
    types, registry = _merged_capture(write)
    if types.get(inputs.col_b) != "float" or inputs.col_b in registry:
        bad.append(f"{inputs.col_b}：名不含字面卻被編碼（{types.get(inputs.col_b)}）")
    want, _w = _legacy_name_encoding(inputs.col_a)
    if want is not None and registry.get(inputs.col_a, {}).get("encoding_type") != want:
        bad.append(f"{inputs.col_a}：registry {registry.get(inputs.col_a)} ≠ 名稱規則 {want}")
    assert bad == [], bad[:30]


def test_mutation_codec_retained_records_decide_encoding_breaks_pin(runs: _Runs, tmp_path: Path,
                                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（R6-B）：保留分支下套用候選改案（processed 改以紀錄判定編碼：做 rank 之欄 rank_uint16）⇒ 保留釘住案紅。"""
    _require_decision(D_CODEC[0], D_CODEC[2])
    inputs = _codec_inputs(runs)
    real = FeatureStorage._build_l7_v2_table

    def mutant(self: Any, *args: Any, **kwargs: Any) -> Any:
        import pyarrow as pa

        table, f32, registry = real(self, *args, **kwargs)[:3]
        if inputs.col_b in table.column_names:
            values = np.asarray(table.column(inputs.col_b).to_numpy(zero_copy_only=False), dtype=np.float32)
            table = table.set_column(table.column_names.index(inputs.col_b), inputs.col_b,
                                     pa.array(fs_mod.encode_rank_as_uint16(values, RANK_W)))
            registry = dict(registry or {}, **{inputs.col_b: {"encoding_type": fs_mod.RANK_UINT16_ENCODING,
                                                              "scale_factor": str(2 * RANK_W), "window": str(RANK_W)}})
        return table, f32, registry

    monkeypatch.setattr(FeatureStorage, "_build_l7_v2_table", mutant)
    write = _codec_write(tmp_path / "features", monkeypatch, inputs)
    types, registry = _merged_capture(write)
    assert types.get(inputs.col_b) != "float" or inputs.col_b in registry


# ============================================================================================== Task 3.3 — D-L2

def _l2_uses(run_list: Iterable[CellRun]) -> List[Tuple[str, L2Use]]:
    return [(r.key, u) for r in run_list for u in r.l2_use]


def test_l2_unified_l5_l6_recomputed_from_public_l2_bitwise(runs: _Runs) -> None:
    """D-L2 統一：格 A＋格 B 全部格之每次 L5／L6 呼叫，所吃之 L2 欄皆在公開落盤 L2 中，且以公開 L2 重算之輸出與實際輸出
    逐位元相等（含校準域實例）。"""
    _require_decision(D_L2[0], D_L2[1])
    uses = _l2_uses(runs.all("A") + runs.all("B"))
    live = [(k, u) for k, u in uses if u.l2_columns and u.output_columns]
    assert live, "無任何 L5／L6 呼叫同時有 L2 輸入與非空輸出 ⇒ 本案無對象"
    bad = [f"{k}|{u.tf}|{u.layer}|calib={u.calibration}|missing={u.missing_public[:3]}"
           for k, u in uses if u.missing_public or not u.recomputed_equal]
    assert bad == [], bad[:30]


def _l2_other_arm(factory_cls: Any) -> Patch:
    """（生成 patch）L5／L6 改回吃另一臂：`factory_cls._layer2_derived_features` 之回傳表換成 `compute_all_polars` 之表。"""

    def patch(mp: pytest.MonkeyPatch, _run: CellRun) -> None:
        current = factory_cls._layer2_derived_features

        def mutant(self: Any, layer1: Any, data: Any, config: Any) -> Any:
            result = current(self, layer1, data, config)
            engine = ff_mod._derived_operator_engine_cls()(self._filter_operators_config(config.operators))
            l1 = self._apply_cascade_blacklist(layer1, "L2_input", config)
            other = engine.compute_all_polars(l1, data, self._build_indicator_specs(l1, config))
            return dataclasses.replace(result, data=other) if other is not None and not other.empty else result

        mp.setattr(factory_cls, "_layer2_derived_features", mutant)

    return patch


def test_mutation_l2_unified_l5_back_to_other_arm_breaks_multi_tf(tmp_path: Path) -> None:
    """mutation：L5／L6 改回吃另一臂 ⇒ 多週期格（L1 float64）之重算逐位元案紅。"""
    _require_decision(D_L2[0], D_L2[1])
    run = _generate(tmp_path, "B", _cells("B")[0], patches=[_l2_other_arm(ff_mod.FeatureFactory)])
    assert any(u.l2_columns and not u.recomputed_equal for u in run.l2_use), "另一臂未被重算案偵測"


def _l2_matrix_rerun(run_list: Iterable[CellRun]) -> Dict[Tuple[str, str], int]:
    """Task 1.3 矩陣之重跑：每格主實例每週期之 `compare_l2_arms(Polars 回傳表, 公開類別表)` 之 f32diff。"""
    out: Dict[Tuple[str, str], int] = {}
    for run in run_list:
        for tf, returned, category in run.l2_arms:
            stats = _l2_matrix().compare_l2_arms(returned, category)
            out[(run.key, tf)] = out.get((run.key, tf), 0) + int(stats["f32diff"])
    return out


def _l2_named_violations(contract: Mapping[str, Any], matrix: Mapping[Tuple[str, str], int]) -> List[str]:
    named = sorted(str(c) for c in (contract.get("l2_value_sources") or {}).get("nonzero_cells") or [])
    nonzero = sorted({cell for (cell, _tf), n in matrix.items() if n})
    return [] if named == nonzero else [f"契約具名非零格 {named} ≠ 重跑非零格 {nonzero}"]


def test_l2_named_matrix_pinned_nonzero_named_and_layers_bitwise(runs: _Runs) -> None:
    """D-L2 具名保留：Task 1.3 矩陣之每格 f32diff 被釘（重跑相等）；非零格於契約 `l2_value_sources.nonzero_cells`
    具名；格 A＋格 B 之公開 L2 與 L5／L6 欄對 §G 凍結逐位元相等（R6-B）。"""
    _require_decision(D_L2[0], D_L2[2])
    run_list = runs.all("A") + runs.all("B")
    matrix = _l2_matrix_rerun(run_list)
    receipt = {(str(r["cell"]), str(r["timeframe"])): int(r["f32diff"])
               for r in _latest_receipt(L2_MATRIX_RECEIPT_GLOB)["rows"]}
    assert matrix and matrix == receipt, sorted(set(matrix.items()) ^ set(receipt.items()))[:10]
    assert _l2_named_violations(nv.load_contract(), matrix) == []
    bad: List[str] = []
    for run in run_list:
        artifact = FROZEN_RAW_A if run.kind == "A" else FROZEN_RAW_B
        names = _layer_columns(run.handle.run_dir, ("L2", "L5", "L6"))
        bad.extend(f"{run.key}|{d}" for d in _column_bitwise_diff(
            _frozen_fp(run.kind, run.key, artifact), nh.fingerprints(run.handle.run_dir, "raw"), names))
    assert bad == [], bad[:30]


def test_mutation_l2_named_contract_drops_cell_breaks_naming(runs: _Runs, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：契約刪一個非零格 ⇒ 具名案紅。"""
    _require_decision(D_L2[0], D_L2[2])
    matrix = _l2_matrix_rerun(runs.all("A") + runs.all("B"))
    contract = nv.load_contract()
    named = list((contract.get("l2_value_sources") or {}).get("nonzero_cells") or [])
    assert named, "契約無具名非零格 ⇒ 刪格 mutant 無對象"
    mutated = copy.deepcopy(contract)
    mutated["l2_value_sources"]["nonzero_cells"] = named[1:]
    monkeypatch.setattr(nv, "load_contract", lambda: copy.deepcopy(mutated))
    assert _l2_named_violations(nv.load_contract(), matrix)


def _l5_l6_eat_public(mp: pytest.MonkeyPatch, run: CellRun) -> None:
    """保留分支下 L5／L6 改吃公開落盤值來源（同實例同週期之公開 L2，依所吃 L2 之欄序）。"""
    FF = ff_mod.FeatureFactory

    def public_of(self: Any, layer2: pd.DataFrame) -> pd.DataFrame:
        inst, tf, _calib = _ctx(self)
        frames = [c for _r, c in run.public.get((inst, tf), [])]
        if not frames or layer2 is None or layer2.empty:
            return layer2
        pub = pd.concat(frames, axis=1)
        pub = pub.loc[:, ~pub.columns.duplicated(keep="first")]
        pub = pub.loc[:, [c for c in layer2.columns if c in pub.columns]].copy()
        pub.index = layer2.index
        return pub

    cur5, cur6 = FF._layer5_cross_sectional, FF._layer6_meta_features
    mp.setattr(FF, "_layer5_cross_sectional",
               lambda self, layer1, layer2, config: cur5(self, layer1, public_of(self, layer2), config))
    mp.setattr(FF, "_layer6_meta_features",
               lambda self, layer1, layer2, data, config: cur6(self, layer1, public_of(self, layer2), data, config))


def test_mutation_l2_named_l5_l6_public_source_breaks_bitwise(tmp_path: Path) -> None:
    """mutation（R6-B）：保留分支下 L5／L6 改吃公開落盤值來源（差異僅 float32 捨入量級）⇒ L5／L6 欄逐位元案紅。
    對象＝契約具名之第一個非零格。"""
    _require_decision(D_L2[0], D_L2[2])
    named = list((nv.load_contract().get("l2_value_sources") or {}).get("nonzero_cells") or [])
    assert named, "契約無具名非零格 ⇒ 本 mutant 無可現形之格"
    target = None
    for kind in ("A", "B"):
        for cell in _cells(kind):
            if _cell_key(kind, cell) == named[0]:
                target = (kind, cell)
    assert target is not None, f"具名格 {named[0]} 不在現行列舉"
    run = _generate(tmp_path, target[0], target[1], patches=[_l5_l6_eat_public])
    names = _layer_columns(run.handle.run_dir, ("L5", "L6"))
    artifact = FROZEN_RAW_A if target[0] == "A" else FROZEN_RAW_B
    assert names
    assert _column_bitwise_diff(_frozen_fp(target[0], run.key, artifact), nh.fingerprints(run.handle.run_dir, "raw"),
                                names)


def _consistency_violations(run: CellRun) -> List[str]:
    return [f"{run.key}|{u.tf}|{u.layer}|calib={u.calibration}|missing={u.missing_public[:3]}|extra={u.extra_public[:3]}"
            f"|equal={u.recomputed_equal}"
            for u in run.l2_use if u.missing_public or u.extra_public or not u.recomputed_equal]


def test_boundary_35_core_always_l2_polars_failure_fallback_consistent(tmp_path: Path) -> None:
    """邊界①（Task 3.3）：`compute_all_polars` 拋錯 ⇒ run 以具名 Layer 2 失敗終止，或完成且每次 L5／L6 所吃之 L2 與公開
    落盤之 L2 欄集合相同、以公開 L2 重算逐位元相等（不得一邊有一邊無）。兩決定皆須成立 ⇒ core_always。"""
    engine_cls = ff_mod._derived_operator_engine_cls()

    def patch(mp: pytest.MonkeyPatch, run: CellRun) -> None:
        def boom(self: Any, *args: Any, **kwargs: Any) -> Any:
            run.compute_all_polars_calls += 1
            raise RuntimeError("NUMVIEW 邊界 35 注入：compute_all_polars 失敗")

        mp.setattr(engine_cls, "compute_all_polars", boom)

    run: Optional[CellRun] = None
    failure: Optional[RuntimeError] = None
    try:
        run = _generate(tmp_path, "A", _cells("A")[0], patches=[patch])
    except RuntimeError as exc:
        failure = exc
    if failure is not None:
        assert "Layer 2" in str(failure), f"失敗未具名 Layer 2：{failure}"
    else:
        assert run is not None and run.l2_use, "run 完成但未觀測到任何 L5／L6 呼叫"
        assert _consistency_violations(run) == []


def test_boundary_36_core_always_pandas_l2_arm_category_only_consistent(tmp_path: Path) -> None:
    """邊界②（Task 3.3）：`FFACT_USE_POLARS=0` ⇒ L2 只走 pandas 臂（`compute_all_polars` 呼叫 0 次），每次 L5／L6 所吃之
    L2 與公開落盤之 L2 欄集合相同、以公開 L2 重算逐位元相等。兩決定皆須成立 ⇒ core_always。"""
    run = _generate(tmp_path, "A", _cells("A")[0], env={"FFACT_USE_POLARS": "0"})
    assert run.compute_all_polars_calls == 0
    assert any(u.l2_columns for u in run.l2_use), "無任何 L5／L6 呼叫吃到 L2 ⇒ 本案無對象"
    assert _consistency_violations(run) == []

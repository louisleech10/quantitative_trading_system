"""NUMVIEW 量測格清單與估時（docs/NUMVIEW_SPEC.md Task 0.4，R2-B、R15-A；先於一切重型跑）。

量測設計＝路徑覆蓋（使用者 2026-10-22 裁定）：格＝現行事前登記判準檔（`_estimate_gate.resolve_criteria_path()`：
`preregistered_criteria*.json` 恰一存在者）之封閉清單 `cell_rules.cell_list`（每格寫明其獨有覆蓋路徑 covers）；各跑別之
重型跑＝判準檔 `run_coverage`（每個 run：格、獨有覆蓋、環境、生成次數、轉換次數；同一路徑不重複跑；同一碼態內每個生成身分
〔格, 環境, 變體〕只生成一次——Phase 1 讀凍結之生成〔含 Task 1.3 L2 spy〕、Phase 2–4 每批〔regen_b3／b4／b5〕之生成由該批
全部驗收檢查跑別〔regen_t21…regen_section_g，本身不生成〕共用；`coverage_violations`）。本檔不另寫格或次數。
格之生成定義（設定覆寫、輸出段根數、前史判定、IC-first 參數、K 線來源）一律讀判準檔之 `cell_rules`／`cell_definitions`。
一切格之生成區間＝輸出段（主週期於其來源序列之最後 output_bars 根）＋所需前史（`cell_rules.window_rule`），不跑全史；
K 線來源依週期（`cell_rules.kline_source`），逐格記來源與資料集 sha256。

實測：封閉清單之每格各實測一次（目標鍵＝格 id）與 PRE-PROV 格逐格；每次實測於獨立子行程、隔離目錄（設定檔連結、CGSA
工作目錄、registry、d* 快取、tempdir 皆導向該目錄；不寫 `data_cache/`）執行，量畢即刪該目錄。IC-first 之格另以生成內擷取之
post-IC 輸入，於每個可達臂（契約 `post_ic_arm_reachability`）各計一次 IC 頁預設請求之轉換秒數。快取：輸出段、資料集紀錄與
生成入口皆同現行判準之實測可重用（舊快取鍵改以其 cell_id 為鍵）。前史不足（`cell_rules.insufficient_history`）：生成之 run
只因 `*_insufficient_history` 而 partial ⇒ 該格 blocked（history），不入外推，其嘗試秒數計入凍結。

外推：逐跑別之每個 run＝生成次數 × 該格實測生成秒數＋轉換次數 × 該格各臂轉換秒數之和（Task 1.1 分支差：同臂排名算一次、
非排名組合以最快臂計；效能基準：各臂＋候選臂各三次＋Polars 剖析一次）；收據逐跑別列格、獨有覆蓋、外推秒數與省法。
邊界：磁碟 < 30 GB ⇒ rc=1 並列所需空間，先於任何生成（②）；格 C 單格實測逾機器上限（記憶體守護具名終止或子行程被
系統終止）⇒ blocked-by 硬體（①）。`reported_at` 由主委白話報告後寫入，本腳本不寫。

用法（repo 根目錄）：
  venv/bin/python handoffs/run_receipts/numview_probes/estimate.py --dry-run                 # 列格、目標、可重用之快取，不生成
  venv/bin/python handoffs/run_receipts/numview_probes/estimate.py --targets A_SOLUSDT_1h      # 只實測指定目標（結果入快取）
  venv/bin/python handoffs/run_receipts/numview_probes/estimate.py                             # 實測全部未快取目標並寫收據
實測結果快取於 `--work-root`/measurements.json（可分次跑；`--remeasure` 重量）。收據：
`handoffs/run_receipts/<date>-numview-estimate.json`（已存在估時收據 ⇒ 拒寫 rc=2，避免兩份）。
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import importlib.util
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

#: 估時收據須涵蓋之跑別（`_estimate_gate.require` 之 run_kind 值）。v3 起各跑別之格與其獨有覆蓋路徑、生成次數一律讀判準檔
#: `run_coverage`（路徑覆蓋；使用者 2026-10-22 裁定），本檔不另寫格或次數：Task 0.5（freeze_baseline）、Phase 1（postic_branchdiff、
#: precision_chain、l2_arm_matrix）、獨立效能基準（perf_benchmark）、Phase 2–4 批次共用生成（regen_b3／b4／b5：每批碼態內
#: 每個生成身分只生成一次）與讀批次生成之驗收檢查跑別（regen_t21…regen_section_g；R15-A，本身不生成）。
RUN_KINDS = ("freeze_baseline", "postic_branchdiff", "precision_chain", "l2_arm_matrix",
             "regen_t21", "regen_t22", "regen_t3_core", "regen_t34", "regen_t42", "regen_t43", "regen_section_g",
             "perf_benchmark", "regen_b3", "regen_b4", "regen_b5", "regen_b4_mutants")
#: 生成型跑別之碼態（判準檔 run_coverage.<跑別>.code_state）合法值：s0＝Phase 0–1（產品碼未改）；b3／b4／b5＝各批；b4_mutant＝b4 之 mutant／故障注入（patch 後之產品碼）
CODE_STATES = ("s0", "b3", "b4", "b5", "b4_mutant")
#: 磁碟下限（GB；SPEC §C 重型跑紀律）
MIN_FREE_DISK_GB = 30
#: Task 1.2 精度鏈之增列重生（SPEC v36–v37；判準 v9 `run_coverage` 之外，記於估時收據 `run_kinds.precision_chain.addenda`；
#: 期望列之唯一來源，窄測試字面鎖定）。`unique_output`＝該次重生取得、凍結產物無法提供之段。
PRECISION_ADDENDA: Tuple[Dict[str, Any], ...] = (
    {"cell": "B_BTCUSDT_1h_4h", "variant": "b_production_spy", "generations": 1,
     "covers": "Task 1.2 B 格生產重生（FFACT_MULTI_TF_PARALLEL=0 串列以供 spy）：S0 層間 float64 與 S1／S2 擷取",
     "covers_ids": ["cell.multi_tf_float64_layers"], "unique_output": ["S0", "S1", "S2"],
     "code_evidence": ["momentum/FeatureEngineering/feature_factory.py:667",
                       "momentum/FeatureEngineering/timeframe/multi_tf_generator.py:429",
                       "momentum/FeatureEngineering/timeframe/multi_tf_generator.py:1233"]},
    {"cell": "C_BTCUSDT_1h", "variant": "c_preserve_dtype", "generations": 1,
     "covers": "Task 1.2 C 格 preserve_dtype=True 重生（含 L2 Polars 臂抬升）：全特徵 float64 層間鏈之 S0 與該 run 讀回",
     "covers_ids": ["cell.full_features_production_default", "precision.s0_float64_chain"], "unique_output": ["S0", "S3"],
     "code_evidence": ["momentum/FeatureEngineering/feature_factory.py:673",
                       "momentum/FeatureEngineering/feature_factory.py:727",
                       "momentum/FeatureEngineering/polars_adapter.py:96"]},
)
#: SPEC v37 細則⑦：開 lag 後須實測秒數之判準變體
PRECISION_LAG_ON_VARIANTS: Tuple[str, ...] = ("memmap_forced_low", "memmap_forced_high")

REPO: Path = Path(__file__).resolve().parents[3]
RECEIPTS_DIR: Path = REPO / "handoffs" / "run_receipts"
KLINE_PATH: Path = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
LEGACY_BASELINE_PATH: Path = REPO / "tests" / "_golden" / "preprov" / "pre_change_fingerprints.json"
ICPOSTLEAK_CONTRACT_PATH: Path = REPO / "tests" / "_golden" / "icpostleak" / "contract.json"
#: 格 C 單格基準可引之實測收據（SPEC Task 0.4：BTCUSDT 12h 生產預設全特徵 run）與其週期
FULLRUN_SIZE_RECEIPT = "handoffs/run_receipts/20261020-preprov-fullrun-size.md"
FULLRUN_SIZE_TF = "12h"
FULLRUN_SIZE_ROW = "A"
FULLRUN_SECONDS_HEADER = "牆鐘 s"
FULLRUN_PEAK_HEADER = "峰值 RSS GiB"
#: 估時收據檔名與檔名樣式（與 `_estimate_gate.ESTIMATE_RECEIPT_GLOB` 同）
RECEIPT_NAME = "{date}-numview-estimate.json"
RECEIPT_GLOB = "*-numview-estimate.json"
#: SPEC §G G1 各臂份之環境設定（`pandas_chunked` 之 chunk 值於實測時依選欄數取「選欄數 − 1」）
G1_ARM_ENV: Dict[str, Dict[str, str]] = {
    "polars": {"FFACT_USE_POLARS": "1"},
    # chunk 未設時預設 2000（feature_preprocessor.py:837-842），選欄 > 2000 即走 chunked ⇒ optimized／legacy 以 chunk 關閉方可達
    # （同凍結腳本 G1_ARM_ENV；審碼 r21 CODEX-R21-P1-02）
    "pandas_optimized": {"FFACT_USE_POLARS": "0", "FFACT_L65_CHUNK_SIZE": "0"},
    "pandas_legacy": {"FFACT_USE_POLARS": "0", "FFACT_L65_OPTIMIZATION_PROFILE": "legacy", "FFACT_L65_CHUNK_SIZE": "0"},
    "pandas_chunked": {"FFACT_USE_POLARS": "0"},
}
CHUNK_ENV = "FFACT_L65_CHUNK_SIZE"
CELL_CATEGORIES = ("A", "B", "C")
PREPROV = "preprov"
LEGACY_ALL = "*legacy*"
BLOCKED_BY_HARDWARE = "hardware"
BLOCKED_BY_HISTORY = "history"
#: 前史 blocked 之格（封閉清單之格各自實測）須生成至判定，其嘗試秒數計入凍結（freeze_baseline）一次；其餘跑別不生成該格
ATTEMPT_RUN_KIND = "freeze_baseline"


class EstimateError(RuntimeError):
    """估時前提不成立（判準檔缺、週期字面不可解析、實測子行程失敗等）。"""


# ---------------------------------------------------------------------------------------------- 列舉

def tf_seconds(tf: str) -> float:
    """週期字面之長度（秒；`pandas.Timedelta` 解析，不假設 24h）；不可解析 ⇒ EstimateError（不猜測）。"""
    import pandas as pd

    try:
        seconds = float(pd.Timedelta(str(tf)).total_seconds())
    except (ValueError, TypeError) as exc:
        raise EstimateError(f"無法解析週期字面 {tf!r}：{exc}") from exc
    if seconds <= 0:
        raise EstimateError(f"週期字面 {tf!r} 長度非正")
    return seconds


def kline_inventory(kline_path: Path) -> Dict[str, Dict[str, int]]:
    """{symbol: {tf: 根數}}（h5py 唯讀；只列具 `data` 之週期；週期依長度升冪）。"""
    import h5py

    out: Dict[str, Dict[str, int]] = {}
    with h5py.File(str(kline_path), "r") as handle:
        for symbol in sorted(handle.keys()):
            group = handle[symbol]
            tfs = [tf for tf in group.keys() if hasattr(group[tf], "keys") and "data" in group[tf]]
            if tfs:
                out[str(symbol)] = {str(tf): int(group[tf]["data"].shape[0]) for tf in sorted(tfs, key=tf_seconds)}
    if not out:
        raise EstimateError(f"kline 檔無任何 symbol×tf：{kline_path}")
    return out


def cell_id(kind: str, symbol: str, timeframes: Sequence[str]) -> str:
    return "_".join([kind, symbol, *timeframes])


def enumerate_cells(kline_path: Path) -> Dict[str, List[Dict[str, Any]]]:
    """格（鍵 `A`／`B`／`C`）；格描述子＝{id, kind, symbol, timeframes}（全票唯一形）。v3 起＝現行判準檔
    `cell_rules.cell_list.cells` 之封閉清單（路徑覆蓋；每格之 symbol×tf 須存在於主檔列舉 `kline_path`，否則 EstimateError）；
    判準無封閉清單（v1／v2）⇒ 舊列舉（A／C＝每個 symbol×tf、B＝每個具 ≥2 週期之 symbol）。"""
    inventory = kline_inventory(Path(kline_path))
    out: Dict[str, List[Dict[str, Any]]] = {kind: [] for kind in CELL_CATEGORIES}
    closed = ((load_criteria().get("cell_rules") or {}).get("cell_list") or {}).get("cells")
    if isinstance(closed, list):
        for entry in closed:
            kind, symbol, tfs = str(entry["kind"]), str(entry["symbol"]), [str(t) for t in entry["timeframes"]]
            missing = [tf for tf in tfs if tf not in inventory.get(symbol, {})]
            if missing:
                raise EstimateError(f"封閉清單之格 {entry['id']} 之 {symbol}×{missing} 不在主檔列舉")
            if str(entry["id"]) != cell_id(kind, symbol, tfs):
                raise EstimateError(f"封閉清單之格 id {entry['id']!r} ≠ 格描述子導出之 {cell_id(kind, symbol, tfs)!r}")
            out[kind].append({"id": str(entry["id"]), "kind": kind, "symbol": symbol, "timeframes": tfs})
        return out
    for symbol, tfs in inventory.items():
        ordered = list(tfs)
        for kind in ("A", "C"):
            for tf in ordered:
                out[kind].append({"id": cell_id(kind, symbol, [tf]), "kind": kind, "symbol": symbol, "timeframes": [tf]})
        if len(ordered) >= 2:
            out["B"].append({"id": cell_id("B", symbol, ordered), "kind": "B", "symbol": symbol, "timeframes": ordered})
    return out


def disk_free_gb(path: Path) -> float:
    """`path` 所在檔案系統之可用空間（GB，以 1024³ 計）。"""
    return shutil.disk_usage(str(path)).free / 1024 ** 3


# ---------------------------------------------------------------------------------------------- 格之生成定義（讀判準檔）

def load_json(path: Path) -> Dict[str, Any]:
    if not Path(path).is_file():
        raise EstimateError(f"檔不存在：{path}")
    return json.loads(Path(path).read_text(encoding="utf-8"))


def kline_source(tf: str, criteria: Mapping[str, Any]) -> Path:
    """週期之 K 線來源檔（判準檔 `cell_rules.kline_source.by_timeframe`，封閉清單；未列之週期 ⇒ EstimateError，不猜測）。"""
    mapping = criteria["cell_rules"]["kline_source"]["by_timeframe"]
    if str(tf) not in mapping:
        raise EstimateError(f"週期 {tf} 未列於判準檔 cell_rules.kline_source.by_timeframe：{sorted(mapping)}")
    return REPO / str(mapping[str(tf)])


def cell_source(cell: Mapping[str, Any], criteria: Mapping[str, Any]) -> Path:
    """格之單一來源檔＝主週期之來源（生成以單一 cache_dir 讀全部訓練週期；判準檔 kline_source.multi_timeframe）。"""
    return kline_source(str(cell["timeframes"][0]), criteria)


def source_inventory(main_inventory: Mapping[str, Mapping[str, int]],
                     criteria: Mapping[str, Any]) -> Dict[str, Dict[str, int]]:
    """{symbol: {tf: 該週期來源檔中之根數}}（symbol×tf 集合取自主檔列舉；來源檔缺該 symbol×tf ⇒ EstimateError）。"""
    import h5py

    out: Dict[str, Dict[str, int]] = {}
    handles: Dict[Path, Any] = {}
    try:
        for symbol, tfs in main_inventory.items():
            for tf in tfs:
                src = kline_source(tf, criteria)
                if src not in handles:
                    handles[src] = h5py.File(str(src), "r")
                group = handles[src].get(f"{symbol}/{tf}")
                if group is None or "data" not in group:
                    raise EstimateError(f"來源檔 {src} 缺 {symbol}/{tf}（判準檔 kline_source）")
                out.setdefault(str(symbol), {})[str(tf)] = int(group["data"].shape[0])
    finally:
        for handle in handles.values():
            handle.close()
    return out


_DATASET_RECORDS: Dict[Tuple[str, str, str], Dict[str, Any]] = {}


def dataset_record(source: Path, symbol: str, tf: str) -> Dict[str, Any]:
    """該格所用 K 線資料集之紀錄（判準檔 kline_source.record）：來源檔（repo 相對）、`<symbol>/<tf>/data` 資料集之
    sha256（dtype 描述＋C 連續位元組；非整檔雜湊）、根數、首末時間戳。同行程快取。"""
    import h5py
    import numpy as np
    import pandas as pd

    key = (str(source), str(symbol), str(tf))
    if key not in _DATASET_RECORDS:
        with h5py.File(str(source), "r") as handle:
            arr = handle[symbol][tf]["data"][()]
        digest = hashlib.sha256()
        digest.update(str(arr.dtype.descr).encode("utf-8"))
        digest.update(np.ascontiguousarray(arr).tobytes())
        stamps = arr["timestamp"]
        unit = "ms" if int(stamps[-1]) > 10 ** 12 else "s"
        try:
            rel = str(Path(source).resolve().relative_to(REPO))
        except ValueError:
            rel = str(source)
        _DATASET_RECORDS[key] = {"source": rel, "dataset_sha256": digest.hexdigest(), "bar_count": int(arr.shape[0]),
                                 "series_start": pd.Timestamp(int(stamps[0]), unit=unit, tz="UTC").isoformat(),
                                 "series_end": pd.Timestamp(int(stamps[-1]), unit=unit, tz="UTC").isoformat()}
    return dict(_DATASET_RECORDS[key])


#: 生產之 K 線連續性設定：生產端 FeatureFactory 一律以 `momentum/factories.py:create_feature_factory` 之預設
#: `validate_continuity=True` 建構（`api/services/feature_factory_service.py:75`、`api/services/feature_factory_batch_service.py:375`／
#: `:1487`）；該驗證於 `adapter_registry.fetch_aligned`（不帶時間範圍）→ `CryptoSpotAdapter.fetch` → `KlineStorageManager.read_klines`
#: 對**全序列**零容忍檢查（`kline_storage.py:1112-1113`），生成窗之切片在其後（`feature_factory._layer0_data_ingestion`）。
PRODUCTION_VALIDATE_CONTINUITY = True


def series_gaps(source: Path, symbol: str, tf: str) -> List[Dict[str, Any]]:
    """`<source>` 之 `<symbol>/<tf>` 時間戳缺口（相鄰差 ≠ 週期秒數；同 `KlineStorageManager._validate_continuity` 之判定）：
    [{after, before, after_ts, before_ts, missing_bars}]。"""
    import h5py
    import numpy as np
    import pandas as pd
    from momentum.core.constants import TIMEFRAME_SECONDS

    with h5py.File(str(source), "r") as handle:
        stamps = np.asarray(handle[symbol][tf]["data"]["timestamp"][()], dtype=np.int64)
    unit = 1000 if stamps.size and int(stamps[-1]) > 10 ** 12 else 1
    seconds = stamps // unit
    step = int(TIMEFRAME_SECONDS[tf])
    out: List[Dict[str, Any]] = []
    for i in np.nonzero(np.diff(seconds) != step)[0]:
        a, b = int(seconds[i]), int(seconds[i + 1])
        out.append({"after": pd.Timestamp(a, unit="s", tz="UTC").isoformat(),
                    "before": pd.Timestamp(b, unit="s", tz="UTC").isoformat(),
                    "after_ts": a, "before_ts": b, "missing_bars": int((b - a) // step - 1)})
    return out


def continuity_plan(cell: Mapping[str, Any], criteria: Mapping[str, Any],
                    training_timeframes: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """格之連續性設定（判準檔 cell_rules.continuity）：格之單一來源中各訓練週期全序列無缺口 ⇒ 生產設定
    （`validate_continuity=True`）；有缺口 ⇒ 生產設定之全序列驗證必拒讀（缺口在生成窗外亦然），該格改以 False 建構，並
    強制窗內零缺口判定（`window_gap_violations`）。回 {validate_continuity, production_setting, series_gaps, reason?}。"""
    src = cell_source(cell, criteria)
    gaps = {str(tf): series_gaps(src, str(cell["symbol"]), str(tf))
            for tf in (training_timeframes or cell["timeframes"])}
    clean = not any(gaps.values())
    out: Dict[str, Any] = {"production_setting": PRODUCTION_VALIDATE_CONTINUITY,
                           "validate_continuity": PRODUCTION_VALIDATE_CONTINUITY if clean else False,
                           "series_gaps": {tf: g for tf, g in gaps.items() if g}}
    if not clean:
        out["reason"] = ("來源全序列有缺口：生產設定之全序列連續性驗證（fetch_aligned 不帶時間範圍）必拒讀；改以 False 建構，"
                         "並以窗內零缺口判定（定案 ingest 起點至輸出終點）取代——窗內任一缺口 ⇒ failed（data_gap）")
    return out


def window_gap_violations(plan: Mapping[str, Any], window_start: Optional[str]) -> List[str]:
    """生成窗（`window_start` 起至序列終點）內之缺口；`window_start` 為 None（窗未知）⇒ 全序列缺口皆計（fail-closed）。"""
    import pandas as pd

    floor = None if window_start is None else int(pd.Timestamp(window_start).timestamp())
    return [f"{tf}：{g['after']}→{g['before']} 缺 {g['missing_bars']} 根" for tf, gaps in (plan.get("series_gaps") or {}).items()
            for g in gaps if floor is None or int(g["before_ts"]) > floor]


def cell_kline_records(cell: Mapping[str, Any], criteria: Mapping[str, Any],
                       training_timeframes: Optional[Sequence[str]] = None) -> Dict[str, Dict[str, Any]]:
    """格之各訓練週期資料集紀錄（皆讀自格之單一來源檔）。"""
    src = cell_source(cell, criteria)
    tfs = [str(t) for t in (training_timeframes if training_timeframes is not None else cell["timeframes"])]
    return {tf: dataset_record(src, str(cell["symbol"]), tf) for tf in tfs}


def output_window(kline_path: Path, symbol: str, tf: str, output_bars: int) -> Tuple[str, str]:
    """主週期最後 `output_bars` 根之（起點, 終點）時間戳 ISO 字串（判準檔 cell_rules.insufficient_history；UTC 解讀
    kline 之 epoch 時間戳，不假設交易時段）。"""
    import h5py
    import pandas as pd

    with h5py.File(str(kline_path), "r") as handle:
        stamps = handle[symbol][tf]["data"]["timestamp"]
        if stamps.shape[0] < output_bars:
            raise EstimateError(f"{symbol}/{tf} 根數 {stamps.shape[0]} < 輸出段 {output_bars}")
        first, last = int(stamps[-output_bars]), int(stamps[-1])
    unit = "ms" if last > 10 ** 12 else "s"
    return (pd.Timestamp(first, unit=unit, tz="UTC").isoformat(), pd.Timestamp(last, unit=unit, tz="UTC").isoformat())


def history_blocked(cell: Mapping[str, Any], inventory: Mapping[str, Mapping[str, int]],
                    criteria: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """格 A／B 之前史不足判定（判準檔 cell_definitions.<格類>.min_history_bars）；不足 ⇒ blocked 條目，否則 None。"""
    kind = str(cell["kind"])
    if kind not in ("A", "B"):
        return None
    threshold = int(criteria["cell_definitions"][kind]["min_history_bars"])
    counts = {tf: int(inventory[cell["symbol"]][tf]) for tf in cell["timeframes"]}
    if all(n >= threshold for n in counts.values()):
        return None
    return {"cell": cell["id"], "blocked_by": BLOCKED_BY_HISTORY, "bar_counts": counts,
            "reason": f"週期根數 {counts} 有 < min_history_bars {threshold} 者（判準檔 cell_rules.insufficient_history）"}


def cell_payload(cell: Mapping[str, Any], criteria: Mapping[str, Any],
                 training_timeframes: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """格之設定覆寫（判準檔 cell_definitions.<格類>.config_override）；主週期＝格描述子 timeframes[0]，訓練週期＝
    `training_timeframes`（格 B 依 `b_membership` 決定者；未給 ⇒ 描述子之全部週期，即格 A／C 之單一週期）。"""
    definition = criteria["cell_definitions"][str(cell["kind"])]
    payload = copy.deepcopy(definition["config_override"])
    tfs = [str(t) for t in cell["timeframes"]]
    training = [str(t) for t in (training_timeframes if training_timeframes is not None else tfs)]
    if not training or training[0] != tfs[0]:
        raise EstimateError(f"{cell.get('id')}：訓練週期 {training} 須以主週期 {tfs[0]} 起首")
    payload["timeframes"] = {**dict(payload.get("timeframes") or {}), "primary": tfs[0], "training": training}
    return payload


# ---------------------------------------------------------------------------------------------- 判準檔與前史判定

def _gate_module() -> Any:
    """同目錄之 `_estimate_gate`（以檔案路徑載入，不依賴 sys.path）。"""
    spec = importlib.util.spec_from_file_location("numview_estimate_gate_for_estimate",
                                                  Path(__file__).resolve().with_name("_estimate_gate.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def criteria_path() -> Path:
    """現行事前登記判準檔（v1／v2 恰一存在者；`_estimate_gate.resolve_criteria_path`，不可判定 ⇒ 拋錯）。"""
    return Path(_gate_module().resolve_criteria_path())


def load_criteria() -> Dict[str, Any]:
    return load_json(criteria_path())


def anchor_lines_at_criteria_commit(rel: str) -> Optional[List[str]]:
    """`path_registry` 錨點所指檔於現行判準檔最後提交時之內容（逐行）；錨點記判準凍結當時之碼位置，故不依工作樹（其後之
    改碼位移不使凍結判準失效；NUMVIEW Task 3.4 審視）。判準檔未提交、git 失敗或該提交無此檔 ⇒ None（呼叫端判違規）。"""
    import subprocess

    target = criteria_path()
    log = subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%H", "--", str(target.relative_to(REPO))],
                         capture_output=True, text=True)
    commit = log.stdout.strip()
    if log.returncode != 0 or not commit:
        return None
    shown = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:{rel}"], capture_output=True)
    if shown.returncode != 0:
        return None
    return shown.stdout.decode("utf-8", errors="replace").splitlines()


#: 錨點上下文窗之最大半徑（行；窗＝錨點行前後各 radius 行）
ANCHOR_CONTEXT_MAX_RADIUS = 12


def criteria_defect_replacements(decisions_path: Optional[Path] = None) -> Dict[str, str]:
    """決定紀錄 `measurement_limitations` 中 `kind=criteria_defect` 項之 {判準路徑 id: replaced_by（path::測試名）}——SPEC Task 0.3
    邊界②：Phase 1 收據後判準不改，判準缺陷（如等價 mutant）以限制項具名、改由 replaced_by 之測試承擔。決定紀錄不存在 ⇒ 空。"""
    path = decisions_path or (REPO / "tests" / "_golden" / "numview" / "decisions.json")
    if not path.is_file():
        return {}
    items = json.loads(path.read_text(encoding="utf-8")).get("measurement_limitations") or []
    return {str(pid): str(item.get("replaced_by") or "") for item in items
            if isinstance(item, Mapping) and item.get("kind") == "criteria_defect" for pid in item.get("criteria_ids") or []}


def count_test_defs(ref: str) -> int:
    """`path::測試名` 於現行檔中 `def 測試名(` 之出現次數（檔不存在或格式不符 ⇒ 0）。"""
    rel, _, name = str(ref).partition("::")
    return sum(1 for s in live_anchor_lines(rel) if re.match(rf"\s*def {re.escape(name)}\(", s)) if rel and name else 0


def live_anchor_lines(rel: str) -> List[str]:
    """錨點所指檔之現行內容（逐行）；檔不存在 ⇒ 空清單。"""
    path = REPO / rel
    return path.read_text(encoding="utf-8", errors="replace").splitlines() if path.is_file() else []


def count_window(lines: Sequence[str], window: Sequence[str]) -> int:
    """`window`（已去首尾空白之連續行）於 `lines`（逐行，比對時去首尾空白）中出現之次數。"""
    stripped = [s.strip() for s in lines]
    n = len(window)
    return sum(1 for i in range(len(stripped) - n + 1) if stripped[i:i + n] == list(window)) if n else 0


def anchor_context_window(lines: Sequence[str], idx: int) -> Optional[List[str]]:
    """錨點行（0 起算 `idx`）於 `lines` 中之最小唯一上下文窗：半徑由 0 起增至 `ANCHOR_CONTEXT_MAX_RADIUS`，取首個於 `lines` 中
    恰出現一次之窗（去首尾空白）；皆不唯一 ⇒ None。"""
    for radius in range(ANCHOR_CONTEXT_MAX_RADIUS + 1):
        window = [s.strip() for s in lines[max(0, idx - radius):idx + radius + 1]]
        if count_window(lines, window) == 1:
            return window
    return None


def classify_run_completeness(manifest: Mapping[str, Any], criteria: Mapping[str, Any]) -> Dict[str, Any]:
    """生成之 run 之前史判定（判準檔 `cell_rules.insufficient_history`，權威）：complete ⇒ `complete`；run_status＝partial、
    failure_reasons 非空且每條皆合 `reason_pattern` ⇒ `blocked`（history，`reason_counts`＝事件→欄數）；其餘 ⇒ `failed`
    （fail-closed）。run_status 解析同正式消費端（`consumer_gate.effective_run_status`）。"""
    from momentum.FeatureEngineering.consumer_gate import effective_run_status

    rule = criteria["cell_rules"]["insufficient_history"]
    status = effective_run_status(manifest)
    reasons = [str(r) for r in (manifest.get("failure_reasons") or [])]
    if status == "complete":
        return {"status": "complete", "run_status": status}
    pattern = re.compile(str(rule["reason_pattern"]))
    if status == "partial" and reasons and all(pattern.fullmatch(r) for r in reasons):
        counts: Dict[str, int] = {}
        for reason in reasons:
            event, count = reason.rsplit(":", 1)
            counts[event] = counts.get(event, 0) + int(count)
        return {"status": "blocked", "blocked_by": BLOCKED_BY_HISTORY, "run_status": status, "reason_counts": counts}
    return {"status": "failed", "run_status": status, "failure_reasons": reasons}


def classify_generated_run(features_root: Path, symbol: str, primary_tf: str,
                           criteria: Mapping[str, Any]) -> Dict[str, Any]:
    """隔離 features 根下該格之 run manifest（`<symbol>/<主週期>/<config_hash>/feature_manifest.json`，須恰一份）之前史判定。"""
    manifests = sorted((Path(features_root) / symbol / primary_tf).glob("*/feature_manifest.json"))
    if len(manifests) != 1:
        return {"status": "failed", "failure_reasons": [f"run manifest 數 {len(manifests)} ≠ 1"]}
    return classify_run_completeness(json.loads(manifests[0].read_text(encoding="utf-8")), criteria)


def cell_window(cell: Mapping[str, Any], criteria: Mapping[str, Any]) -> Tuple[str, str]:
    """格之輸出段（判準檔 cell_rules.window_rule：主週期於其來源檔〔kline_source〕之最後 output_bars 根；來源序列之終點
    依 symbol 而異，逐格記錄）；格 A／B／C 一律有起訖日（不跑全史）。"""
    definition = criteria["cell_definitions"][str(cell["kind"])]
    return output_window(cell_source(cell, criteria), str(cell["symbol"]), str(cell["timeframes"][0]),
                         int(definition["output_bars"]))


def final_warmup_bars(output_window_meta: Optional[Mapping[str, Any]],
                      probe_rounds: Optional[Sequence[Mapping[str, Any]]] = None) -> Optional[int]:
    """生成定案之預熱深度 D（主週期根數；FeatureFactory 公開域加倍規則之結果，`feature_factory._resolve_public_window`）：
    優先取生成結果 metadata `output_window.max_warmup_bars`，其次取加倍探測之末輪 `depth`；皆無 ⇒ None（未知）。"""
    if isinstance(output_window_meta, Mapping) and output_window_meta.get("max_warmup_bars") is not None:
        return int(output_window_meta["max_warmup_bars"])
    rounds = [r for r in (probe_rounds or []) if isinstance(r, Mapping) and r.get("depth") is not None]
    return int(rounds[-1]["depth"]) if rounds else None


def pre_history_requirement(cell: Mapping[str, Any], criteria: Mapping[str, Any], resolved_config: Any,
                            kline_path: Optional[Path] = None, training_timeframes: Optional[Sequence[str]] = None,
                            final_warmup: Optional[int] = None) -> Dict[str, Any]:
    """所需前史（判準檔 cell_rules.window_rule）：required＝D＋N_cal（主週期根數）。D＝生成定案之預熱深度（加倍規則後；
    `final_warmup`，實測格取該 run 之定案值）；未實測 ⇒ 以初值 D₀＝`estimate_max_warmup_bars` 計並標
    `warmup_basis=initial_d0_lower_bound`（加倍只會加深，故為下界）。N_cal＝平穩化開啟時各訓練週期 `resolve_calibration_bars`
    換成主週期根數之最大者、關閉時 0；available＝輸出段起點前之主週期根數；clipped＝available < required（照常生成，由
    insufficient_history 權威判定）。"""
    import h5py
    import math

    import pandas as pd

    from momentum.core.constants import TIMEFRAME_SECONDS
    from momentum.FeatureEngineering.feature_config import l65_enabled, resolve_calibration_bars
    from momentum.FeatureEngineering.warmup_window import estimate_max_warmup_bars

    primary = str(cell["timeframes"][0])
    training = [str(t) for t in (training_timeframes if training_timeframes is not None else cell["timeframes"])]
    kline_path = Path(kline_path) if kline_path is not None else cell_source(cell, criteria)  # 預設＝格之來源檔
    d0 = int(estimate_max_warmup_bars(resolved_config, primary, training))
    pp = resolved_config.preprocessing
    stationarity = bool(l65_enabled(resolved_config)) and (bool(pp.fractional_differencing.enabled)
                                                           or bool(pp.adf_differencing.enabled))
    n_cal = max(math.ceil(resolve_calibration_bars(tf, pp.calibration_bars, pp.calibration_bars_by_timeframe)
                          * TIMEFRAME_SECONDS[tf] / TIMEFRAME_SECONDS[primary]) for tf in training) if stationarity else 0
    depth = int(final_warmup) if final_warmup is not None else d0
    required = depth + n_cal
    output_bars = int(criteria["cell_definitions"][str(cell["kind"])]["output_bars"])
    with h5py.File(str(kline_path), "r") as handle:
        stamps = handle[str(cell["symbol"])][primary]["data"]["timestamp"]
        total = int(stamps.shape[0])
        available = total - output_bars
        floor_pos = max(0, available - required)
        floor_raw = int(stamps[floor_pos])
    unit = "ms" if floor_raw > 10 ** 12 else "s"
    return {"d0_bars": d0, "final_warmup_bars": None if final_warmup is None else int(final_warmup),
            "warmup_basis": "final" if final_warmup is not None else "initial_d0_lower_bound",
            "calibration_bars_primary": int(n_cal), "required_pre_history_bars": int(required),
            "available_pre_history_bars": int(available), "clipped": bool(available < required),
            "ingest_floor": pd.Timestamp(floor_raw, unit=unit, tz="UTC").isoformat()}


def b_membership(cell: Mapping[str, Any], a_history_blocked: Mapping[str, Optional[bool]],
                 criteria: Mapping[str, Any]) -> Dict[str, Any]:
    """格 B 之訓練週期（判準檔 `cell_rules.b_membership`）：主週期＋其餘候選週期中同 symbol×tf 之格 A 未判前史不足者；
    主週期之格 A 判前史不足、或訓練週期 < min_timeframes ⇒ blocked（history）。`a_history_blocked[tf]`＝該 symbol×tf
    之格 A 是否判前史不足（None／缺 ⇒ 未知 ⇒ EstimateError，不猜測）。"""
    rule = criteria["cell_rules"]["b_membership"]
    tfs = [str(t) for t in cell["timeframes"]]
    unknown = [tf for tf in tfs if a_history_blocked.get(tf) is None]
    if unknown:
        raise EstimateError(f"{cell.get('id')}：週期 {unknown} 之格 A 前史判定未知，無從決定格 B 訓練週期")
    excluded = [tf for tf in tfs if a_history_blocked[tf]]
    training = [tf for tf in tfs if not a_history_blocked[tf]]
    out: Dict[str, Any] = {"candidate_timeframes": tfs, rule["record_key"]: training, "excluded_timeframes": excluded}
    if tfs[0] in excluded:
        out.update(status="blocked", reason=f"主週期 {tfs[0]} 之格 A 判前史不足")
    elif len(training) < int(rule["min_timeframes"]):
        out.update(status="blocked", reason=f"排除前史不足週期 {excluded} 後訓練週期 {training} 少於 {rule['min_timeframes']}")
    else:
        out["status"] = "ok"
    return out


# ---------------------------------------------------------------------------------------------- 實測目標

def _first_symbol_with(inventory: Mapping[str, Mapping[str, int]], tf: Optional[str], symbol: Optional[str]) -> str:
    if symbol is not None:
        if symbol not in inventory or (tf is not None and tf not in inventory[symbol]):
            raise EstimateError(f"--symbol {symbol} 無週期 {tf}")
        return symbol
    for name, tfs in inventory.items():
        if tf is None or tf in tfs:
            return name
    raise EstimateError(f"無任何 symbol 具週期 {tf}")


def preprov_needed(criteria: Optional[Mapping[str, Any]] = None) -> List[str]:
    """判準 run_coverage 涉及之 PRE-PROV 格名（"*legacy*" 展開為沿用基準之全部格；讀檔不寫死）。"""
    names: Set[str] = set()
    for node in run_plan(criteria if criteria is not None else load_criteria()).values():
        for name in node.get("preprov") or {}:
            if name == LEGACY_ALL:
                names |= set(load_json(LEGACY_BASELINE_PATH)["cells"])
            else:
                names.add(name)
    return sorted(names)


def fullrun_receipt_applicable(criteria: Optional[Mapping[str, Any]] = None) -> bool:
    """格 C 全史收據（主檔 FULLRUN_SIZE_TF 之全史 run）可作該週期格 C 基準之條件：收據存在且該週期之來源＝主檔
    （收據之資料）；來源改為長歷史檔時，足夠區間 run 之前史可超出主檔全史，收據不再為上界 ⇒ 實測。"""
    criteria = criteria if criteria is not None else load_criteria()
    return ((REPO / FULLRUN_SIZE_RECEIPT).is_file()
            and kline_source(FULLRUN_SIZE_TF, criteria).resolve() == KLINE_PATH.resolve())


def measurement_targets(cells: Mapping[str, List[Dict[str, Any]]], inventory: Mapping[str, Mapping[str, int]],
                        symbol: Optional[str] = None, criteria: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    """實測目標（路徑覆蓋）：封閉清單之每格一個（目標鍵＝格 id；格 B 排在其訓練週期之格 A 之後）、PRE-PROV 逐格。
    `symbol`／`inventory` 為舊列舉之相容參數（封閉清單已定 symbol，不再挑）。"""
    criteria = criteria if criteria is not None else load_criteria()
    targets: List[Dict[str, Any]] = []
    for kind in ("A", "B", "C"):
        for cell in cells[kind]:
            targets.append({"target": cell["id"], "category": kind, "cell": cell})
    for name in preprov_needed(criteria):
        targets.append({"target": f"preprov:{name}", "category": PREPROV, "preprov_cell": name})
    return targets


def fullrun_baseline() -> Dict[str, Any]:
    """格 C 12h 基準：自 FULLRUN_SIZE_RECEIPT 之表格依表頭名取 run A 列之牆鐘秒數與峰值 RSS（GiB→位元組）。"""
    lines = (REPO / FULLRUN_SIZE_RECEIPT).read_text(encoding="utf-8").splitlines()
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in lines if line.strip().startswith("|")]
    header = rows[0]
    try:
        sec_i, peak_i = header.index(FULLRUN_SECONDS_HEADER), header.index(FULLRUN_PEAK_HEADER)
    except ValueError as exc:
        raise EstimateError(f"{FULLRUN_SIZE_RECEIPT} 表頭缺 {FULLRUN_SECONDS_HEADER!r}／{FULLRUN_PEAK_HEADER!r}") from exc
    row = next((r for r in rows[1:] if r and r[0] == FULLRUN_SIZE_ROW), None)
    if row is None:
        raise EstimateError(f"{FULLRUN_SIZE_RECEIPT} 無 run {FULLRUN_SIZE_ROW} 列")
    seconds = float(row[sec_i].replace(",", ""))
    peak = int(float(row[peak_i].replace(",", "")) * 1024 ** 3)
    return {"seconds": seconds, "peak_rss_bytes": peak, "source": FULLRUN_SIZE_RECEIPT}


# ---------------------------------------------------------------------------------------------- 子行程：單格實測

def _isolate(work: Path, env: Mapping[str, str]) -> Path:
    """本子行程之寫入隔離（同 `preprov_helpers._isolate` 之語意，不套其固定環境）：設定檔連結、registry、CGSA 工作目錄、
    cwd、tempdir、d* 快取皆導向 `work`。回傳 features 根。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
    from tests.feature_engineering.probewinsor_helpers import tracked_config_files

    work.mkdir(parents=True, exist_ok=True)
    (work / "config").mkdir(exist_ok=True)
    for rel in tracked_config_files():
        link = work / rel
        if not link.exists():
            link.symlink_to(REPO / rel)
    for name in ("sys_tmp", "dstar_cache", "cgsa_work"):
        (work / name).mkdir(exist_ok=True)
    os.environ["FFACT_FEATURE_REGISTRY_PATH"] = str(work / "features" / "registry.json")
    os.environ["FFACT_CGSA_WORK_DIR"] = str(work / "cgsa_work")
    for key, value in env.items():
        os.environ[str(key)] = str(value)
    os.chdir(str(work))
    tempfile.tempdir = str(work / "sys_tmp")
    dstar = work / "dstar_cache"
    FeaturePreprocessor._d_star_cache_dir = staticmethod(lambda: dstar)
    return work / "features"


def _peak_rss_bytes() -> int:
    import resource

    scale = 1 if sys.platform == "darwin" else 1024
    own = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * scale
    children = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * scale
    return int(max(own, children))


def _is_memory_guard(exc: BaseException) -> bool:
    from momentum.FeatureEngineering.memory_budget import GenerationMemoryBudgetExceeded

    seen: Set[int] = set()
    current: Optional[BaseException] = exc
    while current is not None and id(current) not in seen:
        if isinstance(current, (GenerationMemoryBudgetExceeded, MemoryError)):
            return True
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return False


def _time_ic_page_arms(selected: Sequence[str], groups: Mapping[str, Any]) -> Dict[str, Any]:
    """以生成內擷取之 post-IC 輸入，於每個可達臂各計一次 IC 頁預設請求之轉換秒數（環境依 SPEC §G G1）。"""
    import pandas as pd

    from api.models.ic_models import ApplyTransformsRequest
    from momentum.factories import create_feature_preprocessor, create_post_ic_transform_config, ratio_unsafe_category
    from momentum.FeatureEngineering import numeric_view

    frames = [g for g in groups.values() if g is not None and not g.empty]
    if not frames:
        return {"selected_count": 0, "arm_seconds": {}}
    frame = pd.concat(frames, axis=1)
    frame = frame.loc[:, ~frame.columns.duplicated()]
    kept = [c for c in dict.fromkeys(str(s) for s in selected) if c in frame.columns and ratio_unsafe_category(c) is None]
    contract = numeric_view.load_contract()
    reach = contract["post_ic_arm_reachability"]
    request = ApplyTransformsRequest(selected_features=kept or ["_"])
    config = create_post_ic_transform_config(rank=request.rank, rank_window=request.rank_window, zscore=request.zscore,
                                             zscore_windows=sorted(int(w) for w in request.zscore_windows),
                                             gaussian=request.gaussian)
    seconds: Dict[str, float] = {}
    saved = {key: os.environ.get(key) for key in ("FFACT_USE_POLARS", "FFACT_L65_OPTIMIZATION_PROFILE", CHUNK_ENV)}
    try:
        for arm in contract["post_ic_arm_values"]["values"]:
            if len(kept) < int(reach[arm]["min_selected_columns"]):
                continue
            for key in saved:
                os.environ.pop(key, None)
            env = dict(G1_ARM_ENV.get(arm, {}))
            if arm == "pandas_chunked":
                env[CHUNK_ENV] = str(max(1, len(kept) - 1))
            os.environ.update(env)
            preprocessor = create_feature_preprocessor(config.model_dump())
            started = time.perf_counter()
            preprocessor.transform_selected(kept, {"ic_page": frame.loc[:, kept]}, config=config)
            seconds[arm] = time.perf_counter() - started
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    return {"selected_count": len(kept), "arm_seconds": seconds,
            "branch_seconds": _time_registry_branches(frame.loc[:, kept], config)}


def _time_registry_branches(frame: Any, config: Any) -> Dict[str, float]:
    """ICPOSTLEAK 契約之 registry 系分支（非 IC 頁臂者）各計一次完整轉換秒數（同 `test_icpostleak._run_branch` 之入口：
    ColumnGroupRegistry 存一群組後呼叫 `transform_registry_groups`／`_to_sink`；env／分片位元組／n_workers 依契約）。審查 r6
    CODEX-R6-P1-05：branchdiff 估時不得以臂中位數代補這些分支。"""
    import numpy as np

    from momentum.factories import create_column_group_registry, create_feature_preprocessor
    from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
    from momentum.FeatureEngineering.utils import hardware_utils

    branches = load_json(ICPOSTLEAK_CONTRACT_PATH)["branches"]
    out: Dict[str, float] = {}
    if frame.shape[1] == 0:
        return out
    for name, spec in branches.items():
        if name in BRANCH_ARM:
            continue
        saved = {key: os.environ.get(key) for key in spec.get("env", {})}
        real_shard = hardware_utils.get_cgsa_shard_bytes
        work = Path(tempfile.mkdtemp(prefix=f"numview_branch_{name}_"))
        try:
            os.environ.update({k: str(v) for k, v in spec.get("env", {}).items()})
            if "patch_shard_bytes" in spec:
                hardware_utils.get_cgsa_shard_bytes = lambda: int(spec["patch_shard_bytes"])  # type: ignore[assignment]
            pre = create_feature_preprocessor(config.model_dump())
            registry = create_column_group_registry(work)
            group = ColumnGroup(group_id="1h_L1_numview_estimate", layer=LayerSource.L1, timeframe="1h",
                                data_source="close", indicator="NUMVIEW", columns=tuple(str(c) for c in frame.columns),
                                shape=(0, 0), dtype="float32", disk_path=None)
            registry.save_data(group, frame.to_numpy(dtype=np.float32))
            started = time.perf_counter()
            if spec["entry"] == "transform_registry_groups":
                pre.transform_registry_groups(registry, n_workers=int(spec.get("n_workers", 1)))
            else:
                pre.transform_registry_groups_to_sink(registry, lambda *a, **k: None, n_workers=1)
            out[name] = time.perf_counter() - started
        finally:
            hardware_utils.get_cgsa_shard_bytes = real_shard  # type: ignore[assignment]
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            shutil.rmtree(work, ignore_errors=True)
    return out


class _WindowCapture:
    """擷取 `FeatureFactory._attach_output_window_metadata` 寫入之 `output_window`（生成定案之窗；首次生成者）與加倍探測
    紀錄；`with` 結束還原。生成拋錯（如 IC-first 讀到 partial run）時 `output_window` 可能未寫 ⇒ 以探測末輪補。"""

    def __init__(self, factory: Any) -> None:
        self.factory = factory
        self.window: Optional[Dict[str, Any]] = None

    def __enter__(self) -> "_WindowCapture":
        from momentum.FeatureEngineering.feature_factory import FeatureFactory

        self._cls = FeatureFactory
        self._real = FeatureFactory._attach_output_window_metadata
        capture = self

        def spy(this, result):  # type: ignore[no-untyped-def]
            capture._real(this, result)
            meta = getattr(result, "metadata", None)
            if capture.window is None and isinstance(meta, dict) and isinstance(meta.get("output_window"), dict):
                capture.window = dict(meta["output_window"])

        FeatureFactory._attach_output_window_metadata = spy  # type: ignore[assignment]
        return self

    def __exit__(self, *exc: Any) -> None:
        self._cls._attach_output_window_metadata = self._real  # type: ignore[assignment]

    def final(self) -> Optional[int]:
        return final_warmup_bars(self.window, getattr(self.factory, "_public_warmup_probe", None))


def _with_window_continuity(out: Dict[str, Any], continuity: Mapping[str, Any]) -> Dict[str, Any]:
    """生成後之窗內零缺口判定（判準檔 cell_rules.continuity）：窗＝定案 ingest 起點（`pre_history.ingest_floor`；未知 ⇒
    全序列）至序列終點；窗內有缺口 ⇒ EstimateError（data_gap，不得以含缺口之生成冒充）。紀錄寫入 `continuity`。"""
    floor = (out.get("pre_history") or {}).get("ingest_floor") if isinstance(out.get("pre_history"), Mapping) else None
    inside = window_gap_violations(continuity, floor)
    out["continuity"] = {**dict(continuity), "window_start": floor, "window_gaps": inside}
    if inside:
        raise EstimateError(f"{out.get('cell_id')}：生成窗內有 K 線缺口（data_gap）：{inside}")
    return out


def _measure_ic_first_cell(spec: Mapping[str, Any], work: Path) -> Dict[str, Any]:
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    criteria = load_criteria()
    cell = spec["cell"]
    definition = criteria["cell_definitions"][cell["kind"]]
    generation = definition["generation"]
    features_root = _isolate(work, {})
    training = spec.get("training_timeframes")
    payload = cell_payload(cell, criteria, training)
    source = cell_source(cell, criteria)  # 判準檔 kline_source：單一 cache_dir 讀全部訓練週期
    start, end = cell_window(cell, criteria)
    continuity = continuity_plan(cell, criteria, list(payload["timeframes"]["training"]))
    if window_gap_violations(continuity, start):
        raise EstimateError(f"{cell['id']}：輸出段內有 K 線缺口（data_gap）：{window_gap_violations(continuity, start)}")
    factory = create_feature_factory(cache_dir=str(source.parent), validate_continuity=continuity["validate_continuity"])
    factory._storage = FeatureStorage(str(features_root))
    config = factory._resolve_config(payload)
    captured: Dict[str, Any] = {}
    real = FeaturePreprocessor.transform_selected

    def spy(self, selected, groups, config=None, arm=None):  # type: ignore[no-untyped-def]
        if "selected" not in captured:
            captured["selected"] = list(selected)
            captured["groups"] = {k: v.copy() for k, v in (groups or {}).items()}
        return real(self, selected, groups, config=config, arm=arm)

    FeaturePreprocessor.transform_selected = spy  # type: ignore[assignment]
    started = time.perf_counter()
    window_capture = _WindowCapture(factory)

    def with_pre_history(out: Dict[str, Any]) -> Dict[str, Any]:
        out["pre_history"] = pre_history_requirement(cell, criteria, config, source, training,
                                                     final_warmup=window_capture.final())
        return _with_window_continuity(out, continuity)

    base: Dict[str, Any] = {"cell_id": cell["id"], "output_window": [start, end], "symbol": cell["symbol"],
                            "source_path": str(source), "kline_source": cell_kline_records(cell, criteria, training),
                            "training_timeframes": list(payload["timeframes"]["training"]),
                            "bar_counts": {tf: int(n) for tf, n in kline_inventory(source)[cell["symbol"]].items()
                                           if tf in payload["timeframes"]["training"]}}
    try:
        with window_capture:
            factory.run_ic_first(cell["symbol"], cell["timeframes"][0], config, start_date=start, end_date=end,
                                 ic_engine=ICEngine(dict(generation["ic_engine_config"])),
                                 feature_reader=FeatureReader(str(features_root)),
                                 ic_threshold=generation["ic_threshold"], label_horizon=str(generation["label_horizon"]),
                                 cleanup_raw=bool(generation["cleanup_raw"]))
    except Exception:
        # 前史不足之權威判定（判準檔 cell_rules.insufficient_history）：生成之 run 只因 *_insufficient_history 而 partial
        # ⇒ blocked（history）、記事件欄數；其餘一律原樣上拋（failed）
        verdict = classify_generated_run(features_root, cell["symbol"], cell["timeframes"][0], criteria)
        if verdict["status"] != "blocked":
            raise
        return with_pre_history({**base, **verdict, "attempt_seconds": time.perf_counter() - started})
    finally:
        FeaturePreprocessor.transform_selected = real  # type: ignore[assignment]
    seconds = time.perf_counter() - started
    verdict = classify_generated_run(features_root, cell["symbol"], cell["timeframes"][0], criteria)
    if verdict["status"] != "complete":
        raise EstimateError(f"IC-first 完成而 run 非 complete：{verdict}")
    timing = _time_ic_page_arms(captured.get("selected") or [], captured.get("groups") or {})
    return with_pre_history({**base, "seconds": seconds, **timing})


def _measure_full_cell(spec: Mapping[str, Any], work: Path) -> Dict[str, Any]:
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    criteria = load_criteria()
    cell = spec["cell"]
    features_root = _isolate(work, {})
    source = cell_source(cell, criteria)
    payload = cell_payload(cell, criteria)
    start, end = cell_window(cell, criteria)
    continuity = continuity_plan(cell, criteria)
    if window_gap_violations(continuity, start):
        raise EstimateError(f"{cell['id']}：輸出段內有 K 線缺口（data_gap）：{window_gap_violations(continuity, start)}")
    factory = create_feature_factory(cache_dir=str(source.parent), validate_continuity=continuity["validate_continuity"])
    factory._storage = FeatureStorage(str(features_root))
    resolved = factory._resolve_config(payload)
    window_capture = _WindowCapture(factory)

    def with_pre_history(out: Dict[str, Any]) -> Dict[str, Any]:
        out["pre_history"] = pre_history_requirement(cell, criteria, resolved, source,
                                                     final_warmup=window_capture.final())
        return _with_window_continuity(out, continuity)

    base = {"cell_id": cell["id"], "output_window": [start, end], "symbol": cell["symbol"],
            "source_path": str(source), "kline_source": cell_kline_records(cell, criteria),
            "bar_counts": {str(cell["timeframes"][0]): int(kline_inventory(source)[cell["symbol"]][
                str(cell["timeframes"][0])])}}
    started = time.perf_counter()
    try:
        with window_capture:
            factory.generate_features(cell["symbol"], cell["timeframes"][0], config_override=payload,
                                      force_regenerate=True, persist=True, start_date=start, end_date=end)
    except Exception:
        verdict = classify_generated_run(features_root, cell["symbol"], cell["timeframes"][0], criteria)
        if verdict["status"] != "blocked":
            raise
        return with_pre_history({**base, **verdict, "attempt_seconds": time.perf_counter() - started})
    seconds = time.perf_counter() - started
    verdict = classify_generated_run(features_root, cell["symbol"], cell["timeframes"][0], criteria)
    if verdict["status"] == "blocked":
        return with_pre_history({**base, **verdict, "attempt_seconds": seconds})
    if verdict["status"] != "complete":
        raise EstimateError(f"格 C 生成完成而 run 非 complete：{verdict}")
    return with_pre_history({**base, "seconds": seconds})


def _measure_preprov_cell(spec: Mapping[str, Any], work: Path) -> Dict[str, Any]:
    from tests.feature_engineering import preprov_helpers as ph

    work.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    ph.generate_short_run(work, str(spec["preprov_cell"]))
    return {"seconds": time.perf_counter() - started}


def _child(spec_path: Path) -> int:
    """子行程入口：執行單一實測、寫結果 JSON（`result_path`）；記憶體守護具名終止 ⇒ status=blocked。"""
    sys.path.insert(0, str(REPO))
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    work = Path(spec["work"])
    result: Dict[str, Any] = {"target": spec["target"], "category": spec["category"]}
    if spec["category"] in CELL_CATEGORIES:
        result["entry"] = generation_entry(spec["category"], load_criteria())
    started = time.perf_counter()
    try:
        entry = generation_entry(spec["category"], load_criteria()) if spec["category"] in CELL_CATEGORIES else None
        if entry == "run_ic_first":
            result.update(_measure_ic_first_cell(spec, work))
        elif spec["category"] == "C":
            result.update(_measure_full_cell(spec, work))
        else:
            result.update(_measure_preprov_cell(spec, work))
        result.setdefault("status", "measured")
    except BaseException as exc:  # noqa: BLE001 — 失敗之型別決定 blocked（硬體）或 failed，皆寫結果
        if _is_memory_guard(exc):
            result.update(status="blocked", blocked_by=BLOCKED_BY_HARDWARE)
        else:
            result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"[:2000]
        result["attempt_seconds"] = time.perf_counter() - started
    result["peak_rss_bytes"] = _peak_rss_bytes()
    Path(spec["result_path"]).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if result["status"] == "measured" else 3


_WATCHDOG_MODULE: Optional[Any] = None


def watchdog_module() -> Any:
    """同目錄之 `_watchdog`（卡住偵測；以檔案路徑載入、同行程單例，測試以 monkeypatch 其屬性）。"""
    global _WATCHDOG_MODULE
    if _WATCHDOG_MODULE is None:
        spec = importlib.util.spec_from_file_location("numview_watchdog", Path(__file__).resolve().with_name("_watchdog.py"))
        if spec is None or spec.loader is None:
            raise EstimateError("無法載入 _watchdog.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("numview_watchdog", module)
        spec.loader.exec_module(module)
        _WATCHDOG_MODULE = module
    return _WATCHDOG_MODULE


def _run_target(target: Mapping[str, Any], work_root: Path, kline_path: Path,
                timeout: Optional[float], expected_seconds: Optional[float] = None) -> Dict[str, Any]:
    """於獨立子行程實測單一目標；量畢刪其工作目錄。子行程被系統終止（負 rc）⇒ 記 killed。子行程一律經卡住偵測
    （`_watchdog.run_watched`，門檻＝判準檔 cell_rules.watchdog；預設開、無旗標）：卡住 ⇒ 終止並記 `stalled`＋理由。
    `timeout`（舊參數）若給定則與牆鐘上限取小。"""
    safe = str(target["target"]).replace(":", "_").replace("*", "_")
    work = work_root / f"measure_{safe}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    spec = {**dict(target), "work": str(work / "run"), "kline_path": str(kline_path),
            "result_path": str(work / "result.json")}
    spec_path = work / "spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    log_path = work_root / f"measure_{safe}.log"
    wd = watchdog_module()
    config = wd.load_config(load_criteria())
    if timeout:
        config = wd.WatchdogConfig(**{**config.__dict__, "wall_ceiling_seconds": min(config.wall_ceiling_seconds, timeout)})
    watched = wd.run_watched([sys.executable, str(Path(__file__).resolve()), "--measure-one", str(spec_path)],
                             log_path=log_path, config=config, expected_seconds=expected_seconds, cwd=str(REPO))
    wall = watched.wall_seconds
    rc = watched.returncode
    result_path = work / "result.json"
    if watched.status == wd.STALLED:
        result = {"target": target["target"], "category": target["category"], "status": wd.STALLED,
                  "error": f"卡住偵測終止：{watched.reason}（見 {log_path}）"}
    elif result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
    elif rc is None:
        result = {"target": target["target"], "category": target["category"], "status": "timeout"}
    else:
        result = {"target": target["target"], "category": target["category"],
                  "status": "killed" if rc < 0 else "failed", "error": f"子行程 rc={rc}（無結果檔；見 {log_path}）"}
    if target["category"] in CELL_CATEGORIES:  # 無結果檔之終止亦記生成入口（快取重用判定不得把他入口之終止當本入口結果）
        result.setdefault("entry", generation_entry(target["category"], load_criteria()))
    result["child_wall_seconds"] = wall
    result["swap_growth_max_mb"] = watched.swap_growth_max_mb  # 卡住偵測 swap 門檻之實測依據（判準 v5）
    result["swap_growth_threshold_mb"] = watched.swap_growth_threshold_mb
    result["log"] = str(log_path)
    shutil.rmtree(work, ignore_errors=True)
    return result


# ---------------------------------------------------------------------------------------------- 外推

def generation_entry(kind: str, criteria: Mapping[str, Any]) -> str:
    """格類之生成入口（判準檔 cell_definitions.<格類>.generation.entry；無 generation ⇒ generate_features）。"""
    generation = criteria["cell_definitions"][str(kind)].get("generation") or {}
    return str(generation.get("entry") or "generate_features")


def run_plan(criteria: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """各跑別之 runs 與 PRE-PROV（判準檔 run_coverage；v3 起必有）。缺段或缺跑別 ⇒ EstimateError。"""
    coverage = criteria.get("run_coverage")
    if not isinstance(coverage, Mapping):
        raise EstimateError("判準檔缺 run_coverage（v3 起；路徑覆蓋之跑別計畫）")
    out: Dict[str, Dict[str, Any]] = {}
    for kind in RUN_KINDS:
        node = coverage.get(kind)
        if not isinstance(node, Mapping):
            raise EstimateError(f"判準檔 run_coverage 缺跑別 {kind}")
        out[kind] = {"runs": [dict(r) for r in node.get("runs") or []], "preprov": dict(node.get("preprov") or {}),
                     "code_state": node.get("code_state"), "reads_from": list(node.get("reads_from") or []),
                     "preprov_feeds": dict(node.get("preprov_feeds") or {})}
    return out


def generation_identity(r: Mapping[str, Any]) -> Tuple[str, str, str]:
    """生成身分 (格 id, env 正規化 JSON, 變體)：同一碼態內至多生成一次（判準檔 cell_rules.batch_cache）。"""
    env = json.dumps({str(k): str(v) for k, v in dict(r.get("env") or {}).items()}, sort_keys=True)
    return (str(r.get("cell")), env, str(r.get("variant") or ""))


def coverage_violations(criteria: Mapping[str, Any]) -> List[str]:
    """路徑覆蓋之結構檢查（判準檔 run_coverage._doc）：
    ① 每個 run 之 covers 非空、格屬封閉清單、generations／transform_passes 為非負整數；(格, covers) 於全部跑別唯一。
    ② 生成型跑別（有 code_state）之碼態屬 CODE_STATES；同一碼態內每個生成身分 (格, env, 變體) 合計至多生成一次
       （跨跑別亦然：Phase 1 不得重生凍結已生成者、Phase 2–4 每批每身分一次）。
    ③ generations＝0 之 run 須具 source，且 source 跑別與本跑別同碼態（檢查型跑別：source ∈ reads_from）並確有同身分之生成。
    ④ 檢查型跑別（有 reads_from）不生成（runs 之 generations 皆 0、PRE-PROV 次數皆 0）。
    ⑤ 批次跑別（碼態 b3／b4／b5）之每個生成 feeds 非空、每個 feeds 之檢查跑別確有讀取該生成之 run（無檢查讀取之重生）；
       PRE-PROV 生成之 preprov_feeds 亦然（所列檢查跑別之 preprov 列有該格名）。"""
    out: List[str] = []
    closed = {str(c["id"]) for c in ((criteria.get("cell_rules") or {}).get("cell_list") or {}).get("cells") or []}
    if not closed:
        return ["判準檔無封閉格清單（cell_rules.cell_list.cells）"]
    plan = run_plan(criteria)
    seen: Dict[Tuple[str, str], str] = {}
    generated: Dict[Tuple[str, Tuple[str, str, str]], List[str]] = {}
    for kind, node in plan.items():
        state = node["code_state"]
        if state is None and not node["reads_from"]:
            out.append(f"{kind}：須具 code_state（生成型）或 reads_from（檢查型）")
        if state is not None and state not in CODE_STATES:
            out.append(f"{kind}：code_state {state!r} 不屬 {CODE_STATES}")
        for r in node["runs"]:
            cell, covers = str(r.get("cell")), str(r.get("covers") or "").strip()
            if cell not in closed:
                out.append(f"{kind}：格 {cell} 不在封閉清單")
            if not covers:
                out.append(f"{kind}：格 {cell} 之 run 缺 covers（獨有覆蓋路徑）")
            for fld in ("generations", "transform_passes"):
                v = r.get(fld, 0)
                if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                    out.append(f"{kind}：格 {cell} 之 {fld}={v!r} 非非負整數")
            key = (cell, covers)
            if key in seen:
                out.append(f"重複路徑：格 {cell} 之「{covers[:40]}」同見於 {seen[key]} 與 {kind}")
            seen.setdefault(key, kind)
            gens = r.get("generations", 0)
            if isinstance(gens, int) and gens > 0:
                if node["reads_from"]:
                    out.append(f"{kind}：檢查型跑別不得生成（格 {cell}；應讀批次共用生成）")
                if state is not None:
                    generated.setdefault((state, generation_identity(r)), []).extend([kind] * gens)
    for (state, ident), kinds in generated.items():
        if len(kinds) > 1:
            out.append(f"同碼態重複生成：碼態 {state} 之生成身分 {ident} 生成 {len(kinds)} 次（{kinds}）")
    # ⑥ 轉換（IC 頁各臂輸出）：只記於生成型跑別、同碼態每生成身分至多 1 次；檢查型跑別不自行轉換，以 reads_transforms 讀
    transformed: Dict[Tuple[str, Tuple[str, str, str]], int] = {}
    for kind, node in plan.items():
        for r in node["runs"]:
            tp = r.get("transform_passes", 0)
            if not isinstance(tp, int) or tp <= 0:
                continue
            if node["reads_from"]:
                out.append(f"{kind}：檢查型跑別不得自行轉換（格 {r.get('cell')}；應以 reads_transforms 讀批次生成之轉換）")
            elif node["code_state"] is not None:
                key = (str(node["code_state"]), generation_identity(r))
                transformed[key] = transformed.get(key, 0) + tp
    for (state, ident), n in transformed.items():
        if n > 1:
            out.append(f"同碼態重複轉換：碼態 {state} 之生成身分 {ident} 之 IC 頁各臂輸出計算 {n} 次")
    out += path_registry_violations(criteria, plan)
    # ⑧ 精度鏈段集合（審查 r8 GROK-R8-P1-01）：讀取列之 segments ⊇ S0–S4、⊆ S0–S5；S5（IC 選欄）∈ segments ⇔ 該格類之
    # 生成入口為 run_ic_first（只 generate_features 之格 C 不得宣稱 S5）
    closed_kind = {str(c["id"]): str(c["kind"]) for c in criteria["cell_rules"]["cell_list"]["cells"]}
    for r in plan.get("precision_chain", {}).get("runs") or []:
        if r.get("generations"):
            continue
        segs = r.get("segments")
        if not isinstance(segs, list):
            out.append(f"precision_chain：格 {r.get('cell')} 之讀取列缺 segments")
            continue
        if not {"S0", "S1", "S2", "S3", "S4"} <= set(segs) <= {"S0", "S1", "S2", "S3", "S4", "S5"}:
            out.append(f"precision_chain：格 {r.get('cell')} 之 segments {segs} 須含 S0–S4、不出 S0–S5")
        kind = closed_kind.get(str(r.get("cell")))
        ic_first = kind is not None and generation_entry(kind, criteria) == "run_ic_first"
        if ("S5" in segs) != ic_first:
            out.append(f"precision_chain：格 {r.get('cell')} 之 S5 宣稱 {('S5' in segs)} ≠ 生成入口是否 IC-first（{ic_first}）")
    for kind, node in plan.items():
        for r in node["runs"]:
            if r.get("reads_transforms"):
                src = plan.get(str(r.get("source"))) or {}
                if (str(src.get("code_state")), generation_identity(r)) not in transformed:
                    out.append(f"{kind}：格 {r.get('cell')} 讀 {r.get('source')} 之轉換，但該碼態該身分無轉換")
    for kind, node in plan.items():
        if node["reads_from"] and any(int(n) for n in node["preprov"].values()):
            out.append(f"{kind}：檢查型跑別之 PRE-PROV 次數須為 0（生成記於批次跑別）")
        for r in node["runs"]:
            if r.get("generations"):
                continue
            source = r.get("source")
            if source not in plan:
                out.append(f"{kind}：格 {r.get('cell')} 之讀取 run 無 source（或 source 非跑別）")
                continue
            if node["reads_from"] and source not in node["reads_from"]:
                out.append(f"{kind}：格 {r.get('cell')} 之 source {source} 不在 reads_from")
            src_state = plan[source]["code_state"]
            if node["code_state"] is not None and src_state != node["code_state"]:
                out.append(f"{kind}：格 {r.get('cell')} 讀 {source}（碼態 {src_state}）≠ 本跑別碼態 {node['code_state']}")
            if (src_state, generation_identity(r)) not in generated or source not in generated[(src_state, generation_identity(r))]:
                out.append(f"{kind}：格 {r.get('cell')} 讀 {source} 之生成身分 {generation_identity(r)} 無對應生成")
    for kind, node in plan.items():
        if node["code_state"] not in ("b3", "b4", "b5"):
            continue
        for r in node["runs"]:
            if not r.get("generations"):
                continue
            feeds = list(r.get("feeds") or [])
            if not feeds:
                out.append(f"{kind}：格 {r.get('cell')} 之批次生成無 feeds（無檢查讀取之重生須刪）")
            for check in feeds:
                readers = [x for x in (plan.get(check) or {}).get("runs") or []
                           if x.get("source") == kind and generation_identity(x) == generation_identity(r)]
                if not readers:
                    out.append(f"{kind}：格 {r.get('cell')} 之生成 feeds {check}，但 {check} 無讀取該生成之 run（無檢查讀取之重生）")
        for name, count in node["preprov"].items():
            if not int(count):
                continue
            feeds = list(node["preprov_feeds"].get(name) or [])
            if not feeds:
                out.append(f"{kind}：PRE-PROV {name} 之批次生成無 preprov_feeds")
            for check in feeds:
                if name not in ((plan.get(check) or {}).get("preprov") or {}):
                    out.append(f"{kind}：PRE-PROV {name} feeds {check}，但 {check} 之 preprov 未列該格（無檢查讀取）")
    return out


def path_registry_violations(criteria: Mapping[str, Any], plan: Mapping[str, Mapping[str, Any]]) -> List[str]:
    """⑦ 封閉路徑登錄（判準檔 path_registry；審查 r5 CODEX-R5-P1-03）：(a) 同一碼態內一個路徑 id 至多由一個生成列宣稱，除非
    登錄之 distinct_by（env／variant）於各宣稱者間兩兩相異；(b) 每個登錄 id 至少被一個生成列宣稱（完整性）；(c) 每個
    code_anchor（repo 相對 path:line）解析至存在之非空行；另：每個生成列（generations≥1、具 code_state）covers_ids 非空且
    ⊆ 登錄、登錄 id 唯一。covers 文字不參與判定。"""
    registry = (criteria.get("path_registry") or {}).get("paths")
    if not isinstance(registry, list) or not registry:
        return ["判準檔缺 path_registry.paths（封閉路徑登錄）"]
    out: List[str] = []
    entries: Dict[str, Mapping[str, Any]] = {}
    replaced = criteria_defect_replacements()
    for entry in registry:
        pid = str(entry.get("id") or "")
        if not pid or pid in entries:
            out.append(f"path_registry：id {pid!r} 空或重複")
            continue
        entries[pid] = entry
        anchors = entry.get("code_anchors") or []
        if not anchors:
            out.append(f"path_registry：{pid} 無 code_anchors")
        for anchor in anchors:
            match = re.fullmatch(r"(.+):(\d+)", str(anchor))
            lines = anchor_lines_at_criteria_commit(match.group(1)) if match else None
            if match is None or lines is None:
                out.append(f"path_registry：{pid} 之錨點 {anchor} 檔案不存在或格式非 path:line")
                continue
            line = int(match.group(2))
            if not (1 <= line <= len(lines)) or not lines[line - 1].strip():
                out.append(f"path_registry：{pid} 之錨點 {anchor} 不解析至存在之非空行（檔長 {len(lines)}）")
                continue
            # 現行碼須於同一上下文恰一次含該錨點：取判準提交時錨點行之最小唯一上下文窗（逐字、去首尾空白），現行檔須恰
            # 出現一次；零次（刪除／改名）或多次（無法定位）皆違規，純行號位移不誤報（審碼 b4 r1 CODEX-R1-P1-02、r2 兩家 P1-01）
            if pid in replaced:  # 判準缺陷限制項（邊界②）：錨點所指之 mutation_test 已由 replaced_by 取代，改驗其存在
                if count_test_defs(replaced[pid]) != 1:
                    out.append(f"path_registry：{pid} 之判準缺陷限制項 replaced_by {replaced[pid]!r} 於現行碼須恰一個")
                continue
            window = anchor_context_window(lines, line - 1)
            hits = count_window(live_anchor_lines(match.group(1)), window) if window is not None else 0
            if window is None:
                out.append(f"path_registry：{pid} 之錨點 {anchor} 於判準提交時無唯一上下文（無法定位）")
            elif hits != 1:
                out.append(f"path_registry：{pid} 之錨點 {anchor} 之上下文於現行碼出現 {hits} 次（須恰一次）")
    claims: Dict[Tuple[str, str], List[Tuple[str, Tuple[str, str, str]]]] = {}
    for kind, node in plan.items():
        if node.get("code_state") is None:
            continue
        for r in node["runs"]:
            if not isinstance(r.get("generations"), int) or r["generations"] <= 0:
                continue
            ids = list(r.get("covers_ids") or [])
            if not ids:
                out.append(f"{kind}：格 {r.get('cell')} 之生成列缺 covers_ids（無登錄之獨有路徑 ⇒ 不得生成）")
            for pid in ids:
                if pid not in entries:
                    out.append(f"{kind}：格 {r.get('cell')} 之 covers_ids 含未登錄之 {pid}")
                    continue
                claims.setdefault((str(node["code_state"]), pid), []).append((kind, generation_identity(r)))
    for (state, pid), who in claims.items():
        if len(who) < 2:
            continue
        dims = list(entries[pid].get("distinct_by") or [])
        projections = [tuple(ident[1] if d == "env" else ident[2] for d in dims) for _, ident in who]
        if not dims or len(set(projections)) != len(projections):
            out.append(f"同碼態重複路徑：碼態 {state} 之路徑 {pid} 由 {len(who)} 個生成宣稱（{[k for k, _ in who]}；"
                       f"distinct_by={dims}）")
    claimed = {pid for (_, pid) in claims}
    for pid in entries:
        if pid not in claimed:
            out.append(f"path_registry：{pid} 無任何生成宣稱（完整性）")
    return out


def _plan_preprov(node: Mapping[str, Any]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for name, count in (node.get("preprov") or {}).items():
        names = sorted(load_json(LEGACY_BASELINE_PATH)["cells"]) if name == LEGACY_ALL else [name]
        for item in names:
            out[item] = out.get(item, 0) + int(count)
    return out


#: ICPOSTLEAK 分支 → 其實測秒數來源：IC 頁臂分支讀 `arm_seconds`；其餘（registry 系）分支讀 `branch_seconds`
#: （`_time_registry_branches` 實測）。缺任一 ⇒ 估時無效（審查 r6 CODEX-R6-P1-05：不以中位數／最大值代補）。
BRANCH_ARM = {"polars": "polars", "optimized": "pandas_optimized", "legacy": "pandas_legacy"}
#: 候選臂 polars_float64 尚未實作（Task 3.1）：其成本以 polars 臂實測為**計畫成本代理**（收據標 `planned_cost_proxies`，
#: 不標為實測）；polars 臂缺 ⇒ 估時無效
CANDIDATE_BRANCH_ARM = "polars"


def required_arms(selected_count: Optional[int]) -> List[str]:
    """依契約 `post_ic_arm_reachability.<臂>.min_selected_columns` 須實測之 IC 頁臂；選欄數未知 ⇒ 全部契約臂（fail-closed）。"""
    contract = load_json(REPO / "momentum" / "FeatureEngineering" / "contracts" / "numeric_view.json")
    arms = list(contract["post_ic_arm_values"]["values"])
    if selected_count is None:
        return arms
    reach = contract["post_ic_arm_reachability"]
    return [a for a in arms if int(selected_count) >= int(reach[a]["min_selected_columns"])]


def cost_missing(arms: Mapping[str, float], branch_seconds: Optional[Mapping[str, float]], need_arms: Sequence[str], *,
                 branchdiff: bool) -> List[str]:
    """轉換成本所需而未實測者：`need_arms` 中缺於 `arms` 之臂、候選臂代理（polars）缺；`branchdiff` 時另 registry 系分支缺於
    `branch_seconds`。"""
    missing = [f"arm:{a}" for a in need_arms if a not in arms]
    if CANDIDATE_BRANCH_ARM not in arms and f"arm:{CANDIDATE_BRANCH_ARM}" not in missing:
        missing.append(f"arm:{CANDIDATE_BRANCH_ARM}")
    if branchdiff:
        contract = load_json(ICPOSTLEAK_CONTRACT_PATH)
        missing += [f"branch:{b}" for b in contract["branches"] if b not in BRANCH_ARM
                    and b not in (branch_seconds or {})]
        missing += [f"arm:{BRANCH_ARM[b]}" for b in contract["branches"] if b in BRANCH_ARM
                    and BRANCH_ARM[b] not in arms and f"arm:{BRANCH_ARM[b]}" not in missing]
    return missing


def branchdiff_seconds(arms: Mapping[str, float], branch_seconds: Optional[Mapping[str, float]] = None) -> Optional[float]:
    """Task 1.1 單格之轉換秒數（同臂排名算一次供含排名之組合共用；設計 2026-10-22）：每個分支（ICPOSTLEAK 分支∪候選臂）
    一次完整轉換（含排名，取該分支之實測秒數）＋（組合數 − 1）次非排名轉換（以實測最快者之一次完整轉換為上界）。任一分支
    無實測（`cost_missing`）⇒ None（不代補）。"""
    if cost_missing(arms, branch_seconds, list(BRANCH_ARM.values()), branchdiff=True):
        return None
    contract = load_json(ICPOSTLEAK_CONTRACT_PATH)
    full_of = {b: float(arms[BRANCH_ARM[b]]) if b in BRANCH_ARM else float((branch_seconds or {})[b])
               for b in contract["branches"]}
    full_of["polars_float64"] = float(arms[CANDIDATE_BRANCH_ARM])
    fastest = min(full_of.values())
    return sum(full + (len(contract["combos"]) - 1) * fastest for full in full_of.values())


def perf_seconds(arms: Mapping[str, float], need_arms: Optional[Sequence[str]] = None) -> Optional[float]:
    """獨立效能基準單格秒數：各可達臂＋候選臂（以 polars 實測為計畫成本代理）同輸入各三次，另 Polars 慢因剖析一次。
    須實測之臂（`need_arms`；None ⇒ 全部契約臂）任一缺 ⇒ None（不代補）。"""
    need = list(need_arms if need_arms is not None else required_arms(None))
    if cost_missing(arms, None, need, branchdiff=False):
        return None
    polars = float(arms[CANDIDATE_BRANCH_ARM])
    return 3 * (sum(float(arms[a]) for a in need) + polars) + polars


def measurement_accepted(m: Mapping[str, Any]) -> bool:
    """可寫收據之實測結果：measured；格 A／B／C 之 blocked（history，判準檔 `cell_rules.insufficient_history`）；格 C
    之 blocked／killed（硬體，邊界①；blocked_by 缺或為 hardware）。其餘（failed、timeout、格 A／B／PRE-PROV 之硬體終止）⇒ 實測失敗（rc=1、不寫收據）。"""
    status = m.get("status")
    if status == "measured":
        return True
    if status == "blocked" and m.get("blocked_by") == BLOCKED_BY_HISTORY:
        return m.get("category") in ("A", "B", "C")  # 前史不足（含格 C）依 blocked_by 走前史路徑
    if m.get("category") == "C" and status in ("blocked", "killed"):
        return m.get("blocked_by", BLOCKED_BY_HARDWARE) == BLOCKED_BY_HARDWARE
    return False


def _probe_bar_count(m: Mapping[str, Any], tf: str, inventory: Mapping[str, Mapping[str, int]]) -> Optional[int]:
    """受測格該週期之根數：實測紀錄之 bar_counts；舊快取無此欄而全部 symbol 該週期根數相同 ⇒ 該共同根數；否則 None。"""
    recorded = (m.get("bar_counts") or {}).get(tf)
    if recorded is not None:
        return int(recorded)
    counts = {int(tfs[tf]) for tfs in inventory.values() if tf in tfs}
    return counts.pop() if len(counts) == 1 else None


def history_verdict(kind: str, symbol: str, tf: str, count: int, inventory: Mapping[str, Mapping[str, int]],
                    measurements: Mapping[str, Mapping[str, Any]], criteria: Optional[Mapping[str, Any]] = None,
                    source: Optional[Path] = None) -> Optional[bool]:
    """單一（格類, symbol, tf）於某來源檔之前史不足預測（估時；判準檔 `b_membership.a_status_source.estimate`）。
    `source`＝受判之來源檔（None ⇒ 該週期之 kline_source）；`count`／`inventory` 為該來源之根數。
    ① 格 A：根數 < min_history_bars（前置篩）⇒ True。② 同週期單格實測（`<格類>:<tf>`）為本格、且同來源 ⇒ 其判定。
    ③ 單格實測具所需前史（pre_history.required_pre_history_bars，取其定案預熱深度）⇒ 本格可得前史（根數 − output_bars）
    < 該所需 ⇒ True，否則 False（window_rule 之靜態判定；凍結時由生成之權威判定定案）。④ 舊快取（無 pre_history）且同來源
    ⇒ 根數比較（blocked 且根數 ≤ 受測格 ⇒ True；complete 且根數 ≥ 受測格 ⇒ False）。其餘 ⇒ None（未知，不猜測）。"""
    if criteria is not None and kind == "A" and int(count) < int(criteria["cell_definitions"]["A"]["min_history_bars"]):
        return True
    # 受測格：同（格類, symbol, tf）之格（v3 封閉清單之格鍵＝格 id）；無則取同格類同週期而具所需前史之他格實測（靜態判定）
    m = measurements.get(cell_id(kind, symbol, [tf])) or measurements.get(f"{kind}:{tf}") or next(
        (x for x in measurements.values() if isinstance(x, Mapping) and x.get("category") == kind
         and list(x.get("training_timeframes") or [tf]) == [tf] and str(x.get("cell_id", "")).endswith(f"_{tf}")
         and isinstance(x.get("pre_history"), Mapping)), {})
    status_blocked = m.get("status") == "blocked" and m.get("blocked_by") == BLOCKED_BY_HISTORY
    if not (status_blocked or m.get("status") == "measured"):
        return None
    probe_source = m.get("source_path") or (str(kline_source(tf, criteria)) if criteria is not None else None)
    judged_source = str(source) if source is not None else (str(kline_source(tf, criteria)) if criteria is not None else None)
    same_source = probe_source is None or judged_source is None or Path(probe_source).resolve() == Path(judged_source).resolve()
    if same_source and m.get("cell_id") == cell_id(kind, symbol, [tf]):
        return bool(status_blocked)
    ph = m.get("pre_history") if isinstance(m.get("pre_history"), Mapping) else None
    if ph is not None and ph.get("required_pre_history_bars") is not None and criteria is not None:
        output_bars = int(criteria["cell_definitions"][kind]["output_bars"])
        return (int(count) - output_bars) < int(ph["required_pre_history_bars"])
    if not same_source:
        return None
    probe = _probe_bar_count(m, tf, inventory)
    if probe is None:
        return None
    if status_blocked and int(count) <= probe:
        return True
    if not status_blocked and int(count) >= probe:
        return False
    return None


def predicted_a_history(symbol: str, inventory: Mapping[str, Mapping[str, int]],
                        measurements: Mapping[str, Mapping[str, Any]],
                        criteria: Optional[Mapping[str, Any]] = None,
                        source: Optional[Path] = None) -> Dict[str, Optional[bool]]:
    """該 symbol 各週期之格 A 前史不足預測（`history_verdict`）；`source` 給定 ⇒ 全部週期以該來源判（格 B 之單一來源），
    `inventory` 須為該來源之根數；未給 ⇒ 各週期以其 kline_source 判，`inventory` 須為來源根數（`source_inventory`）。"""
    return {tf: history_verdict("A", symbol, tf, int(count), inventory, measurements, criteria, source)
            for tf, count in inventory[symbol].items()}


def build_receipt(cells: Mapping[str, List[Dict[str, Any]]], inventory: Mapping[str, Mapping[str, int]],
                  criteria: Mapping[str, Any], measurements: Mapping[str, Mapping[str, Any]],
                  contract_arms: Sequence[str]) -> Dict[str, Any]:
    """依實測快取與判準 run_coverage 組估時收據（不含 `reported_at`）。封閉清單之每格各自實測（目標鍵＝格 id）；跑別之每個 run
    列（格, 獨有覆蓋, 生成次數, 轉換次數, 外推秒數）；格類之單格秒數＝該跑別內該格類之最大逐格秒數。`inventory`＝主檔列舉；
    根數一律取各週期來源檔（判準檔 kline_source）。"""
    main_inventory = inventory
    inventory = source_inventory(main_inventory, criteria)
    plan = run_plan(criteria)
    closed = {c["id"]: c for kind in CELL_CATEGORIES for c in cells[kind]}

    def meas(cid: str) -> Mapping[str, Any]:
        return measurements.get(cid) or {}

    # 前史（判準檔 insufficient_history／b_membership）：前置篩、各格實測判定；格 B 依同 symbol 格 A 判定定訓練週期
    history: List[Dict[str, Any]] = []
    attempt_seconds: Dict[str, float] = {}
    b_records: Dict[str, Any] = {}
    for cid, cell in closed.items():
        m = meas(cid)
        if cell["kind"] == "A":
            pre = history_blocked(cell, inventory, criteria)
            if pre is not None:
                history.append({**pre, "source": "prefilter"})
                continue
        if cell["kind"] == "B":
            src = cell_source(cell, criteria)
            b_inv = {cell["symbol"]: {tf: n for tf, n in kline_inventory(src)[cell["symbol"]].items()
                                      if tf in cell["timeframes"]}}
            membership = b_membership(cell, predicted_a_history(cell["symbol"], b_inv, measurements, criteria, src),
                                      criteria)
            b_records[cid] = {**membership, "source": "estimate_measured_a_cells"}
            if membership["status"] == "blocked":
                history.append({"cell": cid, "blocked_by": BLOCKED_BY_HISTORY, "reason": membership["reason"],
                                "bar_counts": {tf: int(b_inv[cell["symbol"]][tf]) for tf in cell["timeframes"]},
                                "source": "b_membership"})
                continue
        if m.get("status") == "blocked" and m.get("blocked_by") == BLOCKED_BY_HISTORY:
            history.append({"cell": cid, "blocked_by": BLOCKED_BY_HISTORY,
                            "bar_counts": dict(m.get("bar_counts") or {}),
                            "reason_counts": dict(m.get("reason_counts") or {}),
                            "reason": "本格實測之 run 只因前史不足而 partial（判準檔 cell_rules.insufficient_history）",
                            "source": f"estimate_measured:{cid}"})
            attempt_seconds[cid] = float(m.get("attempt_seconds") or m.get("child_wall_seconds") or 0.0)
    history_ids = {h["cell"] for h in history}

    # 格 C 基準（硬體 blocked 走邊界①；前史 blocked 以實測至判定之秒數）
    baseline: Dict[str, Any] = {}
    blocked: List[Dict[str, Any]] = []
    for cell in cells["C"]:
        tf = cell["timeframes"][0]
        m = meas(cell["id"])
        if m.get("status") == "measured":
            baseline[tf] = {"seconds": float(m["seconds"]), "peak_rss_bytes": int(m["peak_rss_bytes"]), "source": "measured"}
        elif m.get("status") == "blocked" and m.get("blocked_by") == BLOCKED_BY_HISTORY:
            baseline[tf] = {"seconds": float(m.get("attempt_seconds") or m.get("child_wall_seconds") or 0.0),
                            "peak_rss_bytes": int(m.get("peak_rss_bytes") or 0), "source": "measured",
                            "history_blocked": True, "reason_counts": dict(m.get("reason_counts") or {})}
        elif m.get("status") in ("blocked", "killed"):
            reason = f"格 C 單格實測（{cell['id']}）逾機器上限：{m.get('status')} {m.get('error', '')}".strip()
            baseline[tf] = {"blocked_by": BLOCKED_BY_HARDWARE, "reason": reason}
            blocked.append({"cell": cell["id"], "blocked_by": BLOCKED_BY_HARDWARE, "reason": reason})
        else:
            raise EstimateError(f"格 C {cell['id']} 無實測結果（{m.get('status')}）")
    blocked_c = {b["cell"] for b in blocked}

    preprov_seconds = {key.split(":", 1)[1]: float(m["seconds"]) for key, m in measurements.items()
                       if m.get("category") == PREPROV and m.get("status") == "measured"}
    incomplete: List[str] = []
    run_kinds: Dict[str, Any] = {}
    grand_total = 0.0
    for kind_name in RUN_KINDS:
        node_plan = plan[kind_name]
        runs_out: List[Dict[str, Any]] = []
        per_cell: Dict[str, float] = {}
        for r in node_plan["runs"]:
            cid = str(r["cell"])
            row = {"cell": cid, "covers": r.get("covers"), "generations": int(r.get("generations", 0)),
                   "transform_passes": int(r.get("transform_passes", 0))}
            row["env"] = dict(r.get("env") or {})
            for extra in ("variant", "branchdiff", "perf", "source", "feeds", "covers_ids", "mutation_test", "decision_branch"):
                if r.get(extra):
                    row[extra] = r[extra]
            if cid in history_ids or cid in blocked_c:
                row.update(seconds=0.0, skipped="blocked")
                runs_out.append(row)
                continue
            m = meas(cid)
            arms = dict(m.get("arm_seconds") or {})
            seconds = 0.0
            if row["generations"]:
                if m.get("status") != "measured":
                    raise EstimateError(f"{kind_name}：格 {cid} 無實測生成秒數")
                seconds += row["generations"] * float(m["seconds"])
            needs_arms = row["transform_passes"] or r.get("branchdiff") or r.get("perf")
            need = required_arms(m.get("selected_count"))
            branch_secs = dict(m.get("branch_seconds") or {})
            missing = (cost_missing(arms, branch_secs, need, branchdiff=bool(r.get("branchdiff"))) if needs_arms else [])
            if missing:
                # 審查 r6 CODEX-R6-P1-05：缺任一須實測之臂／分支 ⇒ 該列估時無效（不以中位數／最大值代補），收據列入 incomplete，
                # 收據檢查拒收（不得寫 reported_at）
                incomplete.append(f"{kind_name}:{cid}")
                row["incomplete"] = f"轉換成本未實測：{missing}（不代補；估時無效）"
                row["missing_cost_inputs"] = missing
            elif needs_arms:
                if row["transform_passes"]:
                    seconds += row["transform_passes"] * sum(float(arms[a]) for a in need)
                if r.get("branchdiff"):
                    seconds += branchdiff_seconds(arms, branch_secs) or 0.0
                if r.get("perf"):
                    seconds += perf_seconds(arms, need) or 0.0
                if r.get("branchdiff") or r.get("perf"):
                    row["planned_cost_proxies"] = {"polars_float64": CANDIDATE_BRANCH_ARM}
            row["seconds"] = seconds
            runs_out.append(row)
            per_cell[cid] = per_cell.get(cid, 0.0) + seconds
        preprov = _plan_preprov(node_plan)
        per_preprov: Dict[str, float] = {}
        for name, count in preprov.items():
            if name not in preprov_seconds:
                raise EstimateError(f"PRE-PROV 格 {name} 無實測秒數")
            per_preprov[name] = count * preprov_seconds[name]
        single: Dict[str, float] = {}
        for cid, seconds in per_cell.items():
            if seconds > 0:
                kind = closed[cid]["kind"]
                single[kind] = max(single.get(kind, 0.0), seconds)
        if per_preprov:
            single[PREPROV] = max(per_preprov.values())
        attempts = ({cid: attempt_seconds[cid] for cid in sorted(attempt_seconds)}
                    if kind_name == ATTEMPT_RUN_KIND else {})
        total = sum(per_cell.values()) + sum(per_preprov.values()) + sum(attempts.values())
        grand_total += total
        node: Dict[str, Any] = {
            "cells": list(dict.fromkeys(str(r["cell"]) for r in node_plan["runs"])), "preprov_cells": sorted(preprov),
            "code_state": node_plan["code_state"], "reads_from": node_plan["reads_from"],
            "runs": runs_out, "single_cell_seconds": single, "per_cell_seconds": per_cell,
            "preprov_seconds": per_preprov, "extrapolated_total_seconds": total, "preprov_generations": preprov,
            "basis": "判準檔 run_coverage（路徑覆蓋；每個 run 之 covers 為其獨有覆蓋路徑）",
        }
        if attempts:
            node["blocked_attempt_seconds"] = attempts
        if kind_name == "freeze_baseline":
            groups = criteria["cell_rules"]["freeze_groups"]
            node["groups"] = {"G1": {"cells": list(groups["G1"]), "arms": list(contract_arms)},
                              "G2": {"cells": list(groups["G2"])}, "G3": {"cells": list(groups["G3"])}}
        run_kinds[kind_name] = node

    host_runs = [r for r in plan["precision_chain"]["runs"] if r.get("variant")]
    host_gen = {r["cell"]: float(meas(r["cell"]).get("seconds") or 0.0) for r in host_runs}
    other_a = [c["id"] for c in cells["A"] if c["id"] not in host_gen]
    savings = [
        {"method": "路徑覆蓋：Phase 1 變體只在宿主格各重生一次（不於每格重複）",
         "saved_seconds": sum(len(other_a) * host_gen[r["cell"]] for r in host_runs)},
        {"method": "Task 1.1 同臂排名算一次供含排名之組合共用（只改量測程式、不減組合）",
         "saved_seconds": sum(max(0.0, (sum(dict(meas(r["cell"]).get("arm_seconds") or {}).values())
                                       - min(dict(meas(r["cell"]).get("arm_seconds") or {"_": 0.0}).values())))
                              for r in plan["postic_branchdiff"]["runs"])},
        {"method": "Phase 1 讀 Task 0.5 之 run（generations＝0 之 run 不重生；含 Task 1.3 L2 spy 掛於凍結生成）",
         "saved_seconds": sum(float(meas(r["cell"]).get("seconds") or 0.0)
                              for kind in ("precision_chain", "postic_branchdiff", "perf_benchmark", "l2_arm_matrix")
                              for r in plan[kind]["runs"] if not r.get("generations"))},
        {"method": "Phase 2–4 每批碼態內每個生成身分只生成一次，該批全部驗收檢查共用（判準檔 cell_rules.batch_cache）",
         "saved_seconds": sum(float(meas(r["cell"]).get("seconds") or 0.0)
                              for kind, node in plan.items() if node["reads_from"]
                              for r in node["runs"])
                          - sum(int(r.get("generations") or 0) * float(meas(r["cell"]).get("seconds") or 0.0)
                                for kind, node in plan.items() if node["code_state"] in ("b3", "b4", "b5")
                                for r in node["runs"])},
        {"method": "IC 頁各臂輸出每碼態每生成身分算一次（存於共用快取），讀其之檢查（reads_transforms）不各自重算",
         "saved_seconds": max(0.0, sum(sum(dict(meas(r["cell"]).get("arm_seconds") or {}).values())
                                       for kind, node in plan.items() if node["reads_from"]
                                       for r in node["runs"] if r.get("reads_transforms"))
                              - sum(int(r.get("transform_passes") or 0) * sum(dict(meas(r["cell"]).get("arm_seconds") or {}).values())
                                    for kind, node in plan.items() if node["code_state"] in ("b3", "b4", "b5")
                                    for r in node["runs"]))},
    ]
    continuity: Dict[str, Any] = {}
    for cid, cell in closed.items():
        training = (b_records.get(cid) or {}).get("training_timeframes") or cell["timeframes"]
        plan_c = continuity_plan(cell, criteria, list(training))
        floor = (meas(cid).get("pre_history") or {}).get("ingest_floor") if isinstance(meas(cid).get("pre_history"),
                                                                                       Mapping) else None
        if cid in history_ids or cid in blocked_c:  # 不生成之格（blocked）無生成窗可判
            continuity[cid] = {**plan_c, "window_start": None, "window_gaps": [], "window_check": "skipped_blocked"}
            continue
        continuity[cid] = {**plan_c, "window_start": floor, "window_gaps": window_gap_violations(plan_c, floor)}
    return {"run_kinds": run_kinds, "cell_c_baseline": baseline, "blocked": blocked, "history_blocked": history,
            "continuity": continuity,
            "savings": savings, "b_membership": b_records, "incomplete": incomplete,
            "total_extrapolated_seconds": grand_total}


def pre_history_table(cells: Mapping[str, List[Dict[str, Any]]], criteria: Mapping[str, Any], kline_path: Path,
                      b_records: Mapping[str, Mapping[str, Any]],
                      measurements: Optional[Mapping[str, Mapping[str, Any]]] = None) -> Dict[str, Any]:
    """逐格所需前史（判準檔 cell_rules.window_rule 之 record 欄）；設定解析同生成（FeatureFactory._resolve_config），
    D₀ 依（格類, 訓練週期）快取（同設定、同週期組之 D₀ 相同）。實測過之格（實測紀錄 `cell_id`、同訓練週期）取該 run 定案
    之預熱深度（`warmup_basis=final`）；其餘以初值 D₀ 計並標 `initial_d0_lower_bound`（下界，不外推加倍）。"""
    from momentum.factories import create_feature_factory

    factory = create_feature_factory(cache_dir=str(Path(kline_path).parent))  # 只解析設定、不讀 K 線
    resolved: Dict[Tuple[str, Tuple[str, ...]], Any] = {}
    out: Dict[str, Any] = {}
    for kind in CELL_CATEGORIES:
        for cell in cells[kind]:
            training = list((b_records.get(cell["id"]) or {}).get("training_timeframes") or cell["timeframes"])
            key = (kind, tuple(training))
            if key not in resolved:
                resolved[key] = factory._resolve_config(cell_payload(cell, criteria, training))
            final = None
            for m in (measurements or {}).values():
                ph = m.get("pre_history") if isinstance(m, Mapping) else None
                if (m.get("cell_id") == cell["id"] and isinstance(ph, Mapping)
                        and list(m.get("training_timeframes") or cell["timeframes"]) == training):
                    final = ph.get("final_warmup_bars")
            out[cell["id"]] = {**pre_history_requirement(cell, criteria, resolved[key], None, training,
                                                         final_warmup=final),
                               "training_timeframes": training,
                               "kline_source": cell_kline_records(cell, criteria, training)}
    return out


# ---------------------------------------------------------------------------------------------- 主入口

def cached_entry(m: Mapping[str, Any]) -> str:
    """快取實測之生成入口：有記錄者取之；舊快取未記 ⇒ 依當時實作推定（格 A／B＝run_ic_first、格 C＝generate_features）——
    只限 measured／blocked；其餘狀態（killed／stalled／failed）未記入口 ⇒ "unknown"（不得把他入口之終止當本入口結果）。"""
    if m.get("entry"):
        return str(m["entry"])
    if m.get("status") not in ("measured", "blocked"):
        return "unknown"
    return "generate_features" if m.get("category") == "C" else "run_ic_first"


def expected_seconds(measurements: Mapping[str, Mapping[str, Any]], key: str, category: str) -> Optional[float]:
    """卡住偵測之預期單格秒數：同目標之既有實測秒數；否則同格類已實測之最大秒數；皆無 ⇒ None（用固定上限）。"""
    own = (measurements.get(key) or {}).get("seconds")
    if isinstance(own, (int, float)) and own > 0:
        return float(own)
    peers = [float(m["seconds"]) for m in measurements.values() if isinstance(m, Mapping)
             and m.get("category") == category and m.get("status") == "measured"
             and isinstance(m.get("seconds"), (int, float))]
    return max(peers) if peers else None


def migrate_cache(measurements: Mapping[str, Mapping[str, Any]],
                  cells: Mapping[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    """舊快取鍵（`A:<tf>`、`B`、`C:<tf>`）改以其記錄之 `cell_id` 為鍵（v3 目標鍵＝格 id）；舊格 B（候選週期描述子）之訓練週期
    等於封閉清單某格 B 之 timeframes 者改歸該格，並同步內層 `cell_id`＝新鍵（原值記 `migrated_cell_id`；否則以 cell_id 對接之
    前史表等會對不到——審碼 r13 CODEX-R13-P1-01）。其餘內容不改（重用與否另由 `cache_reusable` 判）。"""
    closed_b = {tuple(c["timeframes"]): c["id"] for c in cells.get("B", [])}
    out: Dict[str, Dict[str, Any]] = {}
    for key, m in measurements.items():
        new_key = key
        cid = m.get("cell_id") if isinstance(m, Mapping) else None
        if cid:
            new_key = str(cid)
            if m.get("category") == "B" and cid not in {c["id"] for c in cells.get("B", [])}:
                new_key = closed_b.get(tuple(m.get("training_timeframes") or ()), new_key)
        if new_key in out and new_key != key:
            continue
        row = dict(m, migrated_from=key) if new_key != key else dict(m)
        if cid and new_key != str(cid):
            row.update(cell_id=new_key, migrated_cell_id=str(cid))
        out[new_key] = row
    return out


def cache_reusable(target: Mapping[str, Any], cached: Optional[Mapping[str, Any]], criteria: Mapping[str, Any]) -> bool:
    """快取實測可重用：狀態 measured／blocked（非預測）、輸出段與資料集紀錄同現行判準、生成入口同判準；PRE-PROV 格 measured 即可。"""
    if not cached or cached.get("status") not in ("measured", "blocked", "killed") or cached.get("predicted"):
        return False
    if target["category"] == PREPROV:
        return cached.get("status") == "measured"
    training = cached.get("training_timeframes") if target["category"] == "B" else None
    return (cached.get("output_window") == list(cell_window(target["cell"], criteria))
            and cached.get("kline_source") == cell_kline_records(target["cell"], criteria, training)
            and cached_entry(cached) == generation_entry(target["category"], criteria))


def apply_precision_addenda(receipt: Mapping[str, Any], lag_on_seconds: Mapping[str, float],
                            lag_on_status: Mapping[str, Any]) -> Dict[str, Any]:
    """Task 1.2 估時收據增列（SPEC v37 §V、細則⑦）：`precision_chain` 之兩 memmap 列改為開 lag 試跑實測秒數並標
    `measured_lag_on`（該試跑 run 之狀態須為 complete，標 `trial_status`；審碼 r17）；依 `PRECISION_ADDENDA` 產生 `addenda`（秒數＝生成次數 × 該格 `measurements` 實測秒數）；重算該跑別
    之 `per_cell_seconds`／`extrapolated_total_seconds` 與收據 `total_extrapolated_seconds`；移除 `reported_at`（須重報
    使用者後由主委寫入）並追加 `revisions` 紀錄。不重量任何格、不改判準 `run_coverage` 列。"""
    import copy as _copy

    out = _copy.deepcopy(dict(receipt))
    node = out["run_kinds"]["precision_chain"]
    missing = [v for v in PRECISION_LAG_ON_VARIANTS if v not in lag_on_seconds]
    if missing:
        raise EstimateError(f"缺開 lag 實測秒數：{missing}")
    bad = {v: lag_on_seconds[v] for v in PRECISION_LAG_ON_VARIANTS
           if isinstance(lag_on_seconds[v], bool)  # bool 為 int 子類（審碼 r10）
           or not (isinstance(lag_on_seconds[v], (int, float)) and math.isfinite(lag_on_seconds[v]) and lag_on_seconds[v] > 0)}
    if bad:
        raise EstimateError(f"開 lag 實測秒數須為有限正數：{bad}")
    not_complete = {v: lag_on_status.get(v) for v in PRECISION_LAG_ON_VARIANTS if lag_on_status.get(v) != "complete"}
    if not_complete:  # 審碼 r17：blocked／failed／缺狀態之 run 不給秒數（細則⑦）
        raise EstimateError(f"開 lag 試跑 run 須為 complete：{not_complete}")
    for variant in PRECISION_LAG_ON_VARIANTS:  # 判準變體列各恰一列（缺列或重複不得靜默略過）
        count = sum(1 for row in node["runs"] if row.get("variant") == variant)
        if count != 1:
            raise EstimateError(f"precision_chain.runs 之 {variant} 須恰一列，實得 {count}")
    for row in node["runs"]:
        if row.get("variant") in PRECISION_LAG_ON_VARIANTS:
            row["seconds"] = float(lag_on_seconds[row["variant"]]) * int(row.get("generations") or 1)
            row["measured_lag_on"] = True
            row["trial_status"] = "complete"
            row["seconds_basis"] = "Task 1.2 試跑實測（設定覆寫 lag_features.enabled=true；SPEC v37 細則⑦）"
    addenda = []
    for spec in PRECISION_ADDENDA:
        m = (out.get("measurements") or {}).get(spec["cell"]) or {}
        if m.get("status") != "measured":
            raise EstimateError(f"增列格 {spec['cell']} 無實測生成秒數")
        addenda.append({**_copy.deepcopy(spec), "seconds": int(spec["generations"]) * float(m["seconds"]),
                        "seconds_basis": f"measurements.{spec['cell']}.seconds"})
    node["addenda"] = addenda
    per_cell: Dict[str, float] = {}
    for row in list(node["runs"]) + addenda:
        per_cell[str(row["cell"])] = per_cell.get(str(row["cell"]), 0.0) + float(row.get("seconds") or 0.0)
    old_total = float(node.get("extrapolated_total_seconds") or 0.0)
    node["per_cell_seconds"] = per_cell
    node["extrapolated_total_seconds"] = sum(per_cell.values()) + sum((node.get("preprov_seconds") or {}).values())
    out["total_extrapolated_seconds"] = float(out["total_extrapolated_seconds"]) - old_total + node["extrapolated_total_seconds"]
    previous = out.pop("reported_at", None)
    out.setdefault("revisions", []).append({
        "at": datetime.now(timezone.utc).isoformat(), "kind": "precision_addenda",
        "reason": "SPEC v37：Task 1.2 B／C 增列重生與 memmap 兩變體開 lag 實測秒數（判準 run_coverage 不改）",
        "previous_reported_at": previous, "precision_chain_total_before": old_total,
        "precision_chain_total_after": node["extrapolated_total_seconds"], "lag_on_seconds": dict(lag_on_seconds),
        "lag_on_status": {v: lag_on_status.get(v) for v in PRECISION_LAG_ON_VARIANTS}})
    return out


def _parse(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NUMVIEW 量測格估時（SPEC Task 0.4）")
    parser.add_argument("--apply-precision-addenda", default=None,
                        help="Task 1.2 增列：讀精度鏈試跑收據（--no-compare 之 timings）就地更新估時收據，不重量")
    parser.add_argument("--kline", default=str(KLINE_PATH))
    parser.add_argument("--receipts-dir", default=None, help="收據目錄（預設 RECEIPTS_DIR）")
    parser.add_argument("--work-root", default=str(Path(tempfile.gettempdir()) / "numview-estimate"),
                        help="實測暫存與快取根（每次實測之生成目錄量畢即刪）")
    parser.add_argument("--symbol", default=None, help="實測用 symbol（預設各週期 kline 列舉之第一個具該週期者）")
    parser.add_argument("--targets", default=None, help="只實測之目標（逗號分隔，如 A:12h,B,C:4h,preprov:h1_stat_off）")
    parser.add_argument("--remeasure", action="store_true", help="忽略快取重量所選目標")
    parser.add_argument("--timeout-seconds", type=float, default=None, help="單一實測子行程逾時（預設不設）")
    parser.add_argument("--dry-run", action="store_true", help="只列格與實測目標，不生成、不寫收據")
    parser.add_argument("--measure-one", default=None, help=argparse.SUPPRESS)
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """估時主入口；rc 0＝收據寫出（或 dry-run 完成）、1＝磁碟不足（列所需空間）或實測失敗／未完成、2＝用法錯或已有收據。"""
    args = _parse(argv)
    if args.measure_one:
        return _child(Path(args.measure_one))
    if args.apply_precision_addenda:
        receipts_dir = Path(args.receipts_dir) if args.receipts_dir else RECEIPTS_DIR
        hits = sorted(receipts_dir.glob(RECEIPT_GLOB))
        if len(hits) != 1:
            print(f"估時收據須恰一份，實得 {[p.name for p in hits]}", file=sys.stderr)
            return 2
        trial = json.loads(Path(args.apply_precision_addenda).read_text(encoding="utf-8"))
        # 不在此轉型（審碼 r11：float(True)＝1.0 會繞過 `apply_precision_addenda` 之型別檢查）
        timings = {k: v for k, v in (trial.get("timings") or {}).items() if k in PRECISION_LAG_ON_VARIANTS}
        if any((trial.get("settings_violations") or {}).get(k) for k in timings):
            print(f"試跑之觀測設定不符：{trial.get('settings_violations')}", file=sys.stderr)
            return 2
        status = {k: (trial.get("run_status") or {}).get(k) for k in PRECISION_LAG_ON_VARIANTS}  # 審碼 r17
        try:
            updated = apply_precision_addenda(json.loads(hits[0].read_text(encoding="utf-8")), timings, status)
        except EstimateError as exc:
            print(f"增列不可套用：{exc}", file=sys.stderr)
            return 2
        hits[0].write_text(json.dumps(updated, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        print(f"估時收據已更新：precision_chain {updated['run_kinds']['precision_chain']['extrapolated_total_seconds']:.1f} 秒；"
              f"總 {updated['total_extrapolated_seconds']:.1f} 秒；reported_at 已移除，待重報使用者")
        return 0
    work_root = Path(args.work_root)
    free = min(disk_free_gb(REPO), disk_free_gb(work_root if work_root.exists() else work_root.parent))
    if free < MIN_FREE_DISK_GB:
        print(f"磁碟可用 {free:.1f} GB < 下限 {MIN_FREE_DISK_GB} GB：須至少 {MIN_FREE_DISK_GB} GB 可用空間"
              f"（尚缺 {MIN_FREE_DISK_GB - free:.1f} GB）；未啟動任何生成、未寫收據。", file=sys.stderr)
        return 1
    sys.path.insert(0, str(REPO))
    from momentum.FeatureEngineering import numeric_view

    kline_path = Path(args.kline)
    try:
        criteria_bytes = criteria_path().read_bytes()
    except Exception as exc:  # noqa: BLE001 — 判準檔不可判定（v1／v2 非恰一）或不可讀
        print(f"判準檔不可用：{exc}（Task 0.3 先於估時）", file=sys.stderr)
        return 1
    criteria = json.loads(criteria_bytes.decode("utf-8"))
    inventory = kline_inventory(kline_path)
    cells = enumerate_cells(kline_path)
    contract_arms = list(numeric_view.load_contract()["post_ic_arm_values"]["values"])
    targets = measurement_targets(cells, inventory, args.symbol, criteria)
    if args.targets:
        wanted = {t.strip() for t in args.targets.split(",") if t.strip()}
        unknown = wanted - {t["target"] for t in targets}
        if unknown:
            print(f"未知之實測目標：{sorted(unknown)}；可用：{[t['target'] for t in targets]}", file=sys.stderr)
            return 2
        selected = [t for t in targets if t["target"] in wanted]
    else:
        selected = targets
    if args.dry_run:
        cache_file = Path(args.work_root) / "measurements.json"
        cached = migrate_cache(json.loads(cache_file.read_text(encoding="utf-8")), cells) if cache_file.is_file() else {}
        reusable = [t["target"] for t in targets if cache_reusable(t, cached.get(t["target"]), criteria)]
        print(json.dumps({"criteria": criteria_path().name, "cells": {k: [c["id"] for c in v] for k, v in cells.items()},
                          "targets": [t["target"] for t in targets],
                          "reusable_from_cache": reusable,
                          "would_measure": [t["target"] for t in selected if t["target"] not in reusable]},
                         ensure_ascii=False, indent=2))
        return 0
    receipts_dir = Path(args.receipts_dir) if args.receipts_dir else Path(RECEIPTS_DIR)
    existing = sorted(receipts_dir.glob(RECEIPT_GLOB))
    if existing and not args.targets:
        print(f"已有估時收據 {[p.name for p in existing]}；不另寫第二份（移除後重跑）", file=sys.stderr)
        return 2
    work_root.mkdir(parents=True, exist_ok=True)
    cache_path = work_root / "measurements.json"
    measurements: Dict[str, Dict[str, Any]] = json.loads(cache_path.read_text(encoding="utf-8")) \
        if cache_path.is_file() else {}
    measurements = migrate_cache(measurements, cells)
    for target in selected:
        key = target["target"]
        if target["category"] == "B":
            # 格 B 之訓練週期依同 symbol 之格 A 判定（判準檔 cell_rules.b_membership）；須先有各週期格 A 實測
            b_src = cell_source(target["cell"], criteria)
            b_counts = {target["cell"]["symbol"]: {tf: n for tf, n in kline_inventory(b_src)[target["cell"]["symbol"]].items()
                                                   if tf in target["cell"]["timeframes"]}}
            membership = b_membership(target["cell"], predicted_a_history(target["cell"]["symbol"], b_counts,
                                                                           measurements, criteria, b_src), criteria)
            if membership["status"] == "blocked":
                measurements[key] = {"target": key, "category": "B", "status": "blocked",
                                     "blocked_by": BLOCKED_BY_HISTORY, "predicted": True, "membership": membership}
                cache_path.write_text(json.dumps(measurements, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"[estimate] {key}: blocked（{membership['reason']}）", flush=True)
                continue
            target = {**target, "training_timeframes": membership["training_timeframes"]}
            cached = measurements.get(key) or {}
            if cached.get("training_timeframes") != membership["training_timeframes"]:
                measurements.pop(key, None)  # 快取之訓練週期與現行判定不同 ⇒ 重量
        if target["category"] in ("A", "B", "C"):
            window = list(cell_window(target["cell"], criteria))
            records = cell_kline_records(target["cell"], criteria, target.get("training_timeframes"))
            cached = measurements.get(key) or {}
            if cached.get("status") in ("measured", "blocked") and cached.get("blocked_by") != BLOCKED_BY_HARDWARE \
                    and not cached.get("predicted") \
                    and (cached.get("output_window") != window or cached.get("kline_source") != records
                         or cached_entry(cached) != generation_entry(target["category"], criteria)):
                measurements.pop(key, None)  # 舊區間、舊來源資料集或舊生成入口（如格 C 改經 IC-first）⇒ 依現行判準重量
            if cached.get("status") in ("killed", "stalled") \
                    and cached_entry(cached) != generation_entry(target["category"], criteria):
                measurements.pop(key, None)  # 他入口（或未記入口）之終止不代表本入口 ⇒ 重量（判準 v4：格 C 改回 generate_features）
        if key in measurements and measurements[key].get("status") in ("measured", "blocked", "killed") \
                and not args.remeasure:
            continue
        print(f"[estimate] 實測 {key} …", flush=True)
        result = _run_target(target, work_root, kline_path, args.timeout_seconds,
                             expected_seconds=expected_seconds(measurements, key, target["category"]))
        measurements[key] = result
        cache_path.write_text(json.dumps(measurements, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[estimate] {key}: {result.get('status')} {result.get('seconds', '')}", flush=True)
        if result.get("status") == watchdog_module().STALLED:
            # 卡住偵測（預設開）：fail-fast——停止後續目標、印單行摘要、rc≠0、不寫收據
            print(f"[watchdog] {key}: stalled（{result.get('error')}；{result.get('child_wall_seconds', 0):.0f} 秒）"
                  "— 停止後續目標，不寫收據", file=sys.stderr, flush=True)
            return 3
    failed = {k: m for k, m in measurements.items() if not measurement_accepted(m)}
    if failed:
        print(f"實測失敗：{json.dumps(failed, ensure_ascii=False)[:2000]}", file=sys.stderr)
        return 1
    missing = [t["target"] for t in targets if t["target"] not in measurements]
    if missing:
        print(f"尚有未實測之目標 {missing}（已存快取 {cache_path}）；全部實測後再跑一次以寫收據", file=sys.stderr)
        return 1
    target_keys = {t["target"] for t in targets}  # 收據只收現行目標之實測；快取殘留之舊格（不在現行目標）隔離於 legacy_measurements
    legacy = {k: v for k, v in measurements.items() if k not in target_keys}
    measurements = {k: v for k, v in measurements.items() if k in target_keys}
    body = build_receipt(cells, inventory, criteria, measurements, contract_arms)
    body["pre_history"] = pre_history_table(cells, criteria, kline_path, body["b_membership"], measurements)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True).stdout.strip()
    versions: Dict[str, Optional[str]] = {}
    for name in numeric_view.load_contract()["library_versions"]["values"]:
        try:
            versions[name] = str(getattr(importlib.import_module(name), "__version__", None))
        except ImportError:
            versions[name] = None
    receipt = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "head": head,
        "command": " ".join([Path(sys.executable).name, "handoffs/run_receipts/numview_probes/estimate.py", *(argv or [])]),
        "criteria_sha256": hashlib.sha256(criteria_bytes).hexdigest(),
        "machine": {"platform": platform.platform(), "python": platform.python_version()},
        "library_versions": versions,
        "cells": cells,
        "measurements": measurements,
        "legacy_measurements": legacy,
        **body,
    }
    receipts_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(receipts_dir.glob(RECEIPT_GLOB))
    if existing:
        print(f"已有估時收據 {[p.name for p in existing]}；不另寫第二份（實測已存快取 {cache_path}）", file=sys.stderr)
        return 2
    out = receipts_dir / RECEIPT_NAME.format(date=datetime.now().strftime("%Y%m%d"))
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[estimate] 收據 {out}；外推總秒數 {body['total_extrapolated_seconds']:.0f}"
          f"（{body['total_extrapolated_seconds'] / 3600:.1f} 小時）；reported_at 待主委白話報告後寫入")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

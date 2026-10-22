"""NUMVIEW 量測格清單與估時（docs/NUMVIEW_SPEC.md Task 0.4，R2-B、R15-A；先於一切重型跑）。

自 `data_cache/feature_klines/kline_cache.h5` 列舉 symbol×tf（不寫死清單）：格 A＝每個 symbol×tf 單週期短窗、
格 B＝每個具 ≥2 週期之 symbol 之多週期格（描述子 timeframes＝全部候選週期；實際訓練週期依判準檔 `cell_rules.b_membership`
排除格 A 判前史不足之週期）、格 C＝生產預設全特徵於每個 symbol×tf。一切格之生成區間＝輸出段（主週期最後 output_bars 根）＋所需前史（判準檔 `cell_rules.window_rule`：D₀＋N_cal），不跑全史；逐格之所需／可得前史記於收據 `pre_history`。格之生成定義（設定覆寫、輸出段根數、前史判定、
IC-first 參數）一律讀現行事前登記判準檔（`_estimate_gate.resolve_criteria_path()`：v1／v2 恰一存在者）之 `cell_rules`／
`cell_definitions`（本檔不另寫設定）。

實測：各類先實測一格之耗時與峰值記憶體——格 A 逐週期一格、格 B 一格（訓練週期依該 symbol 之格 A 實測判定）、格 C 逐週期
一格（12h 引 `handoffs/run_receipts/20261020-preprov-fullrun-size.md` 之 run A 列——全史 run，為足夠區間 run 之上界；4h／1h 以足夠區間各實測；快取中舊區間之結果自動重量）、PRE-PROV 格逐格（Phase 2–4
驗收測試直接經 `preprov_helpers` 生成之格）。每次實測於獨立子行程、隔離目錄（設定檔連結、CGSA 工作目錄、registry、
d* 快取、tempdir 皆導向該目錄；不寫 `data_cache/`）執行，量畢即刪該目錄。格 A／B 之實測另以生成內擷取之 post-IC
輸入，於每個可達臂（契約 `post_ic_arm_reachability`）各計一次 IC 頁預設請求之轉換秒數，供轉換型跑別外推。
前史不足（判準檔 `cell_rules.insufficient_history`）：生成之 run 為 partial 且 failure_reasons 全為 `*_insufficient_history`
⇒ 該格 blocked（history），記事件欄數與根數；其他非 complete ⇒ failed（不寫收據）。估時器以逐週期格 A 之判定預測同週期
根數不多於受測格之全部格 A（前史更少者不會更足），blocked 格不入外推，但凍結（freeze_baseline）須生成至判定，其嘗試秒數
另列並計入該跑別。

外推：逐跑別（`RUN_KINDS`）以 `RUN_PLAN` 之每格生成次數／轉換次數（逐項註明來源）× 該格類與週期之實測單格秒數，
列格清單、PRE-PROV 格、單格秒數、逐格秒數、外推總秒數；另列不降驗證之省法與 blocked 格。
邊界：磁碟 < 30 GB ⇒ rc=1 並列所需空間，先於任何生成（②）；格 C 單格實測逾機器上限（記憶體守護具名終止或子行程被
系統終止）⇒ 該週期之格 C 全列 blocked-by 硬體、不再逐格試（①）。`reported_at` 由主委白話報告後寫入，本腳本不寫。

用法（repo 根目錄）：
  venv/bin/python handoffs/run_receipts/numview_probes/estimate.py --dry-run          # 只列格與實測目標，不生成
  venv/bin/python handoffs/run_receipts/numview_probes/estimate.py --targets A:12h      # 只實測指定目標（結果入快取）
  venv/bin/python handoffs/run_receipts/numview_probes/estimate.py                      # 實測全部未快取目標並寫收據
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

#: 估時收據須涵蓋之跑別（`_estimate_gate.require` 之 run_kind 值）：Task 0.5 之 G1–G3 與 Phase 1 全部生成；
#: 另 Phase 2–4 驗收重產（R15-A）——每個以真實生成驗收之單位一個跑別（依各測試檔實際之生成呼叫盤點）：
#:   regen_t21＝Task 2.1 ④（test_numview_policy.py，格 A BTCUSDT 1h）；regen_t22＝Task 2.2 G1（tests/api/test_numview_ic_page.py，
#:   全部格 A）；regen_t3_core＝Task 3.1–3.3（test_numview_core.py 三 Task 共用模組範圍格倉、同批 b4 一次跑，全部格 A＋B＋
#:   PRE-PROV `ic_first_default`）；regen_t34＝Task 3.4（IC 頁鎖臂 G1，全部格 A＋PRE-PROV `ic_first_empty`）；
#:   regen_t42＝Task 4.2（test_numview_identity.py，PRE-PROV `h1_stat_off`、`ic_first`）；regen_t43＝Task 4.3 ③（PRE-PROV
#:   `h1_pp_off` 兩次）；regen_section_g＝§G Phase 0／2／4 全格不變式（test_numview_acceptance.py，全部格 A＋B＋沿用基準
#:   PRE-PROV 全部格）。收據每跑別：cells（格 id）、preprov_cells（PRE-PROV 格名）、single_cell_seconds、extrapolated_total_seconds。
RUN_KINDS = ("freeze_baseline", "postic_branchdiff", "precision_chain", "l2_arm_matrix",
             "regen_t21", "regen_t22", "regen_t3_core", "regen_t34", "regen_t42", "regen_t43", "regen_section_g")
#: 磁碟下限（GB；SPEC §C 重型跑紀律）
MIN_FREE_DISK_GB = 30

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
#: Task 2.1 ④ 之單一驗收格（SPEC Task 2.1 驗證④「真實 kline 格 A 之 BTCUSDT 1h」）
REGEN_T21_CELL: Tuple[str, str] = ("BTCUSDT", "1h")
#: SPEC §G G1 各臂份之環境設定（`pandas_chunked` 之 chunk 值於實測時依選欄數取「選欄數 − 1」）
G1_ARM_ENV: Dict[str, Dict[str, str]] = {
    "polars": {"FFACT_USE_POLARS": "1"},
    "pandas_optimized": {"FFACT_USE_POLARS": "0"},
    "pandas_legacy": {"FFACT_USE_POLARS": "0", "FFACT_L65_OPTIMIZATION_PROFILE": "legacy"},
    "pandas_chunked": {"FFACT_USE_POLARS": "0"},
}
CHUNK_ENV = "FFACT_L65_CHUNK_SIZE"
CELL_CATEGORIES = ("A", "B", "C")
PREPROV = "preprov"
LEGACY_ALL = "*legacy*"
BLOCKED_BY_HARDWARE = "hardware"
BLOCKED_BY_HISTORY = "history"
#: 前史 blocked 之格須生成至判定（嘗試秒數）之跑別：格 A／B 於凍結、格 C 於 Task 1.2（precision_chain）
ATTEMPT_RUN_KIND = {"A": "freeze_baseline", "B": "freeze_baseline", "C": "precision_chain"}

#: 跑別 → 外推計畫。`cells`：格類（"A"／"AB"／"ABC"）、"t21"（REGEN_T21_CELL 單格）或 ""；`generations`：每格生成次數
#: （一次＝一次 `generate_cell` 等價之 IC-first 生成，格 C＝一次全史生成）；`transform_passes`：每格「每個可達臂各一次
#: IC 頁預設轉換」之次數；`branchdiff`：Task 1.1 之轉換量（ICPOSTLEAK 分支∪候選臂 × 七組合，另速度量測可達臂∪候選臂 × 3
#: 次）；`preprov`：PRE-PROV 格 → 生成次數（"*legacy*"＝沿用基準全部格）。`basis` 為盤點來源。
RUN_PLAN: Dict[str, Dict[str, Any]] = {
    "freeze_baseline": {
        "cells": "AB", "generations": {"A": 2, "B": 1}, "transform_passes": {"A": 1}, "preprov": {},
        "basis": "SPEC Task 0.5／§G：格 A 之 G2 於 FFACT_USE_POLARS 0／1 各生成一次（G1 以其中來源 run 跑各可達臂之 IC 頁轉換"
                 "一次）；格 B 之 G3 生成一次。前史不足（判準檔 cell_rules.insufficient_history）之格須生成至判定、不入"
                 "外推，其嘗試秒數另列 blocked_attempt_seconds 並計入本跑別。"},
    "postic_branchdiff": {
        "cells": "AB", "generations": {}, "branchdiff": True, "preprov": {},
        "basis": "SPEC Task 1.1：讀 Task 0.5 保留之 run（不重生）；每格 ICPOSTLEAK 分支∪候選臂 × 七組合各轉換一次，另速度量測"
                 "可達臂∪候選臂各三次；輸入 (i) 為 3000 根之秒級輸入，併入同格計。"},
    "precision_chain": {
        "cells": "ABC", "generations": {"A": 3, "B": 3, "C": 2}, "preprov": {},
        "basis": "SPEC Task 1.2：格 A／B 另需 S0 float64 鏈變體、memmap 另一支、尾端延伸各一輪生成（S1–S5 於 Task 0.5 之 run 擷取）；"
                 "格 C 生產生成一次＋S0 float64 鏈變體一次。"},
    "l2_arm_matrix": {
        "cells": "AB", "generations": {"A": 2, "B": 2}, "preprov": {},
        "basis": "SPEC Task 1.3：每格於 FFACT_USE_POLARS 1（兩臂比對）與 0（pandas 臂同表）各生成一次（上界；實際只算至 L2）。"},
    "regen_t21": {
        "cells": "t21", "generations": {"A": 3}, "preprov": {},
        "basis": "test_numview_policy.py CellLab：同（格, 生成環境）一次；G1 polars／pandas_optimized／pandas_legacy 三環境"
                 "（G2 之 0／1 與前兩者同環境）。"},
    "regen_t22": {
        "cells": "A", "generations": {"A": 1}, "transform_passes": {"A": 1}, "preprov": {},
        "basis": "tests/api/test_numview_ic_page.py G1Lab：每格以 g1_source_env 重生一次、每（格, 臂份）IC 頁一次。"},
    "regen_t3_core": {
        "cells": "AB", "generations": {"A": 1, "B": 1}, "transform_passes": {"A": 1}, "preprov": {"ic_first_default": 1},
        "basis": "test_numview_core.py _Runs：同（格類, 格）一次；另 PRE-PROV ic_first_default。重型 mutation 只對第一格另生成，"
                 "計入 savings 之反向說明（未外推）。"},
    "regen_t34": {
        "cells": "A", "generations": {"A": 1}, "transform_passes": {"A": 1}, "preprov": {"ic_first_empty": 1},
        "basis": "tests/api/test_numview_ic_page.py G1Lab（鎖臂狀態）＋邊界 38 之 PRE-PROV ic_first_empty。"},
    "regen_t42": {
        "cells": "", "generations": {}, "preprov": {"h1_stat_off": 10, "ic_first": 1},
        "basis": "test_numview_identity.py `_gen`：h1_stat_off 共 10 次（基準、FFACT_USE_POLARS=0、未認證／已認證換臂、三組中止"
                 "後重跑各兩次）、ic_first 一次。"},
    "regen_t43": {
        "cells": "", "generations": {}, "preprov": {"h1_pp_off": 2},
        "basis": "tests/api/test_numview_ic_page.py Regenerated：h1_pp_off 原始與改一根 K 線各生成一次。"},
    "regen_section_g": {
        "cells": "AB", "generations": {"A": 2, "B": 1}, "transform_passes": {"A": 1}, "preprov": {LEGACY_ALL: 1},
        "basis": "test_numview_acceptance.py _Regen.freeze_cell（同凍結：格 A 兩次、格 B 一次、G1 各臂一次）＋沿用基準 PRE-PROV 全部格。"},
}


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
    """自 kline 檔列舉格 A／B／C（鍵 `A`／`B`／`C`）；格描述子＝{id, kind, symbol, timeframes}（全票唯一形：A／C 之
    timeframes 恰一項；B 依週期長度升冪、首項＝主週期）。不寫死 symbol 與週期；B 只列具 ≥2 週期之 symbol。"""
    inventory = kline_inventory(Path(kline_path))
    out: Dict[str, List[Dict[str, Any]]] = {kind: [] for kind in CELL_CATEGORIES}
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


def preprov_needed() -> List[str]:
    """RUN_PLAN 涉及之 PRE-PROV 格名（"*legacy*" 展開為沿用基準之全部格；讀檔不寫死）。"""
    names: Set[str] = set()
    for plan in RUN_PLAN.values():
        for name in plan.get("preprov") or {}:
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
                        symbol: Optional[str], criteria: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    """實測目標：格 A 逐週期一格、格 B 一格、格 C 逐週期一格（全史收據可用時 FULLRUN_SIZE_TF 引收據、不實測）、PRE-PROV 逐格。"""
    use_fullrun = fullrun_receipt_applicable(criteria)
    targets: List[Dict[str, Any]] = []
    tfs = sorted({tf for tfs_ in inventory.values() for tf in tfs_}, key=tf_seconds)
    for tf in tfs:
        sym = _first_symbol_with(inventory, tf, symbol)
        cell = next(c for c in cells["A"] if c["symbol"] == sym and c["timeframes"] == [tf])
        targets.append({"target": f"A:{tf}", "category": "A", "cell": cell})
    if cells["B"]:
        sym = symbol if symbol is not None and any(c["symbol"] == symbol for c in cells["B"]) else cells["B"][0]["symbol"]
        cell = next(c for c in cells["B"] if c["symbol"] == sym)
        targets.append({"target": "B", "category": "B", "cell": cell})
    for tf in tfs:
        if tf == FULLRUN_SIZE_TF and use_fullrun:
            continue
        sym = _first_symbol_with(inventory, tf, symbol)
        cell = next(c for c in cells["C"] if c["symbol"] == sym and c["timeframes"] == [tf])
        targets.append({"target": f"C:{tf}", "category": "C", "cell": cell})
    for name in preprov_needed():
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
    return {"selected_count": len(kept), "arm_seconds": seconds}


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
    factory = create_feature_factory(cache_dir=str(source.parent), validate_continuity=False)
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
        return out

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
    factory = create_feature_factory(cache_dir=str(source.parent), validate_continuity=False)
    factory._storage = FeatureStorage(str(features_root))
    payload = cell_payload(cell, criteria)
    start, end = cell_window(cell, criteria)
    resolved = factory._resolve_config(payload)
    window_capture = _WindowCapture(factory)

    def with_pre_history(out: Dict[str, Any]) -> Dict[str, Any]:
        out["pre_history"] = pre_history_requirement(cell, criteria, resolved, source,
                                                     final_warmup=window_capture.final())
        return out

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
    started = time.perf_counter()
    try:
        if spec["category"] in ("A", "B"):
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


def _run_target(target: Mapping[str, Any], work_root: Path, kline_path: Path,
                timeout: Optional[float]) -> Dict[str, Any]:
    """於獨立子行程實測單一目標；量畢刪其工作目錄。子行程被系統終止（負 rc）⇒ 記 killed。"""
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
    started = time.perf_counter()
    with open(log_path, "w", encoding="utf-8") as log:
        try:
            proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--measure-one", str(spec_path)],
                                  cwd=str(REPO), stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            rc = None
    wall = time.perf_counter() - started
    result_path = work / "result.json"
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
    elif rc is None:
        result = {"target": target["target"], "category": target["category"], "status": "timeout"}
    else:
        result = {"target": target["target"], "category": target["category"],
                  "status": "killed" if rc < 0 else "failed", "error": f"子行程 rc={rc}（無結果檔；見 {log_path}）"}
    result["child_wall_seconds"] = wall
    result["log"] = str(log_path)
    shutil.rmtree(work, ignore_errors=True)
    return result


# ---------------------------------------------------------------------------------------------- 外推

def _plan_cells(plan: Mapping[str, Any], cells: Mapping[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    spec = plan["cells"]
    if spec == "t21":
        hits = [c for c in cells["A"] if (c["symbol"], c["timeframes"][0]) == REGEN_T21_CELL]
        if len(hits) != 1:
            raise EstimateError(f"Task 2.1 ④ 之格 {REGEN_T21_CELL} 於 kline 列舉中須恰一格，實得 {len(hits)}")
        return hits
    return [c for kind in spec for c in cells[kind]]


def _plan_preprov(plan: Mapping[str, Any]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for name, count in (plan.get("preprov") or {}).items():
        names = sorted(load_json(LEGACY_BASELINE_PATH)["cells"]) if name == LEGACY_ALL else [name]
        for item in names:
            out[item] = out.get(item, 0) + int(count)
    return out


def _branchdiff_units(n_reachable_arms: int) -> int:
    """Task 1.1 每格之轉換次數：（ICPOSTLEAK 分支數＋候選臂）× 組合數＋速度量測（可達臂＋候選臂）× 3。"""
    contract = load_json(ICPOSTLEAK_CONTRACT_PATH)
    return (len(contract["branches"]) + 1) * len(contract["combos"]) + (n_reachable_arms + 1) * 3


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
    m = measurements.get(f"{kind}:{tf}") or {}
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
    """依實測快取與 RUN_PLAN 組估時收據（不含 `reported_at`）。`inventory`＝主檔列舉（symbol×tf 集合）；根數一律改取各週期
    來源檔（判準檔 kline_source）。"""
    main_inventory = inventory
    inventory = source_inventory(main_inventory, criteria)
    gen_seconds: Dict[Tuple[str, str], float] = {}
    arm_seconds: Dict[Tuple[str, str], Dict[str, float]] = {}
    cost_basis: Dict[str, str] = {}
    for key, m in measurements.items():
        if (m.get("status") == "blocked" and m.get("blocked_by") == BLOCKED_BY_HISTORY and not m.get("predicted")
                and m.get("category") in ("A", "B", "C")):
            # 受測格判前史不足而同週期他格（前史較長者）預測足夠：其單格成本以受測格生成至判定之秒數計（生成全程已跑，
            # 只於讀取時判 partial；逐格記 cost_basis，不另猜測）
            slot = (m["category"], "*") if m["category"] == "B" else (m["category"], key.split(":", 1)[1])
            seconds = m.get("attempt_seconds") or m.get("child_wall_seconds")
            if seconds and slot not in gen_seconds:
                gen_seconds[slot] = float(seconds)
                cost_basis[key] = "attempt_seconds_of_history_blocked_probe"
            continue
        if m.get("status") != "measured":
            continue
        if m["category"] in ("A", "C"):
            tf = key.split(":", 1)[1]
            gen_seconds[(m["category"], tf)] = float(m["seconds"])
            if m["category"] == "A":
                arm_seconds[("A", tf)] = dict(m.get("arm_seconds") or {})
        elif m["category"] == "B":
            gen_seconds[("B", "*")] = float(m["seconds"])
            arm_seconds[("B", "*")] = dict(m.get("arm_seconds") or {})

    baseline: Dict[str, Any] = {}
    blocked: List[Dict[str, Any]] = []
    all_tfs = sorted({tf for tfs in inventory.values() for tf in tfs}, key=tf_seconds)
    for tf in all_tfs:
        if tf == FULLRUN_SIZE_TF and fullrun_receipt_applicable(criteria):
            baseline[tf] = {**fullrun_baseline(),
                            "basis": "全史 run 之實測，為足夠區間 run（輸出段＋所需前史 ⊆ 全史）之上界；"
                                     "該週期前史若被資料起點截斷，由 Task 1.2 生成之前史判定決定 blocked"}
            gen_seconds[("C", tf)] = baseline[tf]["seconds"]
            continue
        m = measurements.get(f"C:{tf}") or {}
        if m.get("status") == "measured":
            baseline[tf] = {"seconds": float(m["seconds"]), "peak_rss_bytes": int(m["peak_rss_bytes"]), "source": "measured"}
        elif m.get("status") == "blocked" and m.get("blocked_by") == BLOCKED_BY_HISTORY:
            # 前史不足之格 C（判準檔 cell_rules.insufficient_history）：實測至判定之秒數為該格之實測成本；不入硬體路徑
            baseline[tf] = {"seconds": float(m.get("attempt_seconds") or m.get("child_wall_seconds") or 0.0),
                            "peak_rss_bytes": int(m.get("peak_rss_bytes") or 0), "source": "measured",
                            "history_blocked": True, "reason_counts": dict(m.get("reason_counts") or {})}
        elif m.get("status") in ("blocked", "killed"):
            reason = f"格 C 單格實測（{m.get('target')}）逾機器上限：{m.get('status')} {m.get('error', '')}".strip()
            baseline[tf] = {"blocked_by": BLOCKED_BY_HARDWARE, "reason": reason}
            for cell in cells["C"]:
                if cell["timeframes"] == [tf]:
                    blocked.append({"cell": cell["id"], "blocked_by": BLOCKED_BY_HARDWARE, "reason": reason})
        else:
            raise EstimateError(f"格 C {tf} 無實測結果（{m.get('status')}）")
    blocked_c = {b["cell"] for b in blocked}
    # 前史不足（判準檔 cell_rules.insufficient_history／b_membership）：格 A 依前置篩或同週期單格實測預測；格 B 依同 symbol
    # 之格 A 判定決定訓練週期，主週期不足或剩不足兩週期 ⇒ blocked；格 B 自身實測 blocked（history）⇒ 同訓練週期且根數不多
    # 於受測格者 blocked。blocked 格不入外推；凍結須生成至判定之格（A 經實測判定者）另計嘗試秒數。
    history: List[Dict[str, Any]] = []
    attempt_seconds: Dict[str, float] = {}
    for cell in cells["C"]:
        tf = cell["timeframes"][0]
        probe = measurements.get(f"C:{tf}") or {}
        if history_verdict("C", cell["symbol"], tf, int(inventory[cell["symbol"]][tf]), inventory, measurements,
                           criteria) is True:
            history.append({"cell": cell["id"], "blocked_by": BLOCKED_BY_HISTORY,
                            "bar_counts": {tf: int(inventory[cell["symbol"]][tf])},
                            "reason_counts": dict(probe.get("reason_counts") or {}),
                            "reason": "同週期格 C 單格實測判前史不足（本格或依其定案所需前史之靜態判定；判準檔 window_rule）",
                            "source": f"estimate_probe:C:{tf}"})
            attempt_seconds[cell["id"]] = float(probe.get("attempt_seconds") or probe.get("child_wall_seconds") or 0.0)
    for cell in cells["A"]:
        pre = history_blocked(cell, inventory, criteria)
        if pre is not None:
            history.append({**pre, "source": "prefilter"})
            continue
        tf = cell["timeframes"][0]
        verdict = predicted_a_history(cell["symbol"], inventory, measurements, criteria).get(tf)
        if verdict is None:
            raise EstimateError(f"{cell['id']}：無從判定前史（週期 {tf} 之格 A 單格實測缺或不適用）")
        if verdict:
            probe = measurements[f"A:{tf}"]
            history.append({"cell": cell["id"], "blocked_by": BLOCKED_BY_HISTORY,
                            "bar_counts": {tf: int(inventory[cell["symbol"]][tf])},
                            "reason_counts": dict(probe.get("reason_counts") or {}),
                            "reason": f"同週期格 A 單格實測（{probe.get('symbol', '?')}）判前史不足，本格依其判定或其定案所需"
                                      "前史之靜態判定（判準檔 cell_rules.insufficient_history／window_rule）",
                            "source": f"estimate_probe:A:{tf}"})
            attempt_seconds[cell["id"]] = float(probe.get("attempt_seconds") or probe.get("child_wall_seconds") or 0.0)
    b_records: Dict[str, Any] = {}
    b_probe = measurements.get("B") or {}
    b_sources: Dict[str, Dict[str, Dict[str, int]]] = {}
    for cell in cells["B"]:
        src = cell_source(cell, criteria)  # 格 B 單一來源＝主週期之來源（kline_source.multi_timeframe）
        if str(src) not in b_sources:
            b_sources[str(src)] = kline_inventory(src)
        b_inv = {cell["symbol"]: {tf: n for tf, n in b_sources[str(src)][cell["symbol"]].items() if tf in cell["timeframes"]}}
        membership = b_membership(cell, predicted_a_history(cell["symbol"], b_inv, measurements, criteria, src), criteria)
        b_records[cell["id"]] = {**membership, "source": "estimate_probe_prediction"}
        if membership["status"] == "blocked":
            history.append({"cell": cell["id"], "blocked_by": BLOCKED_BY_HISTORY,
                            "bar_counts": {tf: int(b_inv[cell["symbol"]][tf]) for tf in cell["timeframes"]},
                            "reason": membership["reason"], "source": "b_membership"})
            continue
        if (b_probe.get("status") == "blocked" and b_probe.get("blocked_by") == BLOCKED_BY_HISTORY
                and b_probe.get("training_timeframes") == membership["training_timeframes"]
                and all(int(b_inv[cell["symbol"]][tf]) <= int((b_probe.get("bar_counts") or {}).get(tf, -1))
                        for tf in membership["training_timeframes"])):
            history.append({"cell": cell["id"], "blocked_by": BLOCKED_BY_HISTORY,
                            "bar_counts": {tf: int(b_inv[cell["symbol"]][tf]) for tf in membership["training_timeframes"]},
                            "reason_counts": dict(b_probe.get("reason_counts") or {}),
                            "reason": "格 B 單格實測之 run 只因前史不足而 partial（同訓練週期、根數不多於受測格）",
                            "source": "estimate_probe:B"})
            attempt_seconds[cell["id"]] = float(b_probe.get("attempt_seconds") or b_probe.get("child_wall_seconds") or 0.0)
        elif b_probe.get("status") == "measured":
            b_records[cell["id"]]["cost_basis_training_timeframes"] = b_probe.get("training_timeframes")
    history_ids = {h["cell"] for h in history}  # 前史 blocked 另列 history_blocked；blocked 只放硬體（邊界①語意）

    def gen_cost(cell: Mapping[str, Any]) -> float:
        kind = cell["kind"]
        key = (kind, "*") if kind == "B" else (kind, cell["timeframes"][0])
        if key not in gen_seconds:
            raise EstimateError(f"無格類 {kind} 週期 {key[1]} 之實測秒數")
        return gen_seconds[key]

    def arms_of(cell: Mapping[str, Any]) -> Dict[str, float]:
        key = ("B", "*") if cell["kind"] == "B" else ("A", cell["timeframes"][0])
        return arm_seconds.get(key) or {}

    preprov_seconds = {key.split(":", 1)[1]: float(m["seconds"]) for key, m in measurements.items()
                       if m.get("category") == PREPROV and m.get("status") == "measured"}
    run_kinds: Dict[str, Any] = {}
    grand_total = 0.0
    for kind_name in RUN_KINDS:
        plan = RUN_PLAN[kind_name]
        listed = _plan_cells(plan, cells)
        per_cell: Dict[str, float] = {}
        for cell in listed:
            if cell["id"] in blocked_c or cell["id"] in history_ids:
                continue
            cost = float(plan.get("generations", {}).get(cell["kind"], 0)) * gen_cost(cell)
            arms = arms_of(cell)
            passes = float((plan.get("transform_passes") or {}).get(cell["kind"], 0))
            cost += passes * sum(arms.values())
            if plan.get("branchdiff"):
                mean_arm = (sum(arms.values()) / len(arms)) if arms else 0.0
                cost += _branchdiff_units(len(arms)) * mean_arm
            per_cell[cell["id"]] = cost
        preprov = _plan_preprov(plan)
        per_preprov: Dict[str, float] = {}
        for name, count in preprov.items():
            if name not in preprov_seconds:
                raise EstimateError(f"PRE-PROV 格 {name} 無實測秒數")
            per_preprov[name] = count * preprov_seconds[name]
        single: Dict[str, float] = {}
        for cell in listed:
            if cell["id"] in per_cell:
                single[cell["kind"]] = max(single.get(cell["kind"], 0.0), per_cell[cell["id"]])
        if per_preprov:
            single[PREPROV] = max(per_preprov.values())
        # 須逐格生成至前史判定（不得預設跳過）之跑別：格 A／B＝凍結（freeze_baseline）、格 C＝precision_chain（Task 1.2
        # 之格 C 生成）；經單格實測判定 blocked 之格各計一次嘗試秒數
        attempts = {c["id"]: attempt_seconds[c["id"]] for c in listed if c["id"] in attempt_seconds
                    and kind_name == ATTEMPT_RUN_KIND[c["kind"]]}
        total = sum(per_cell.values()) + sum(per_preprov.values()) + sum(attempts.values())
        grand_total += total
        node: Dict[str, Any] = {
            "cells": [c["id"] for c in listed], "preprov_cells": sorted(preprov),
            "single_cell_seconds": single, "per_cell_seconds": per_cell, "preprov_seconds": per_preprov,
            "extrapolated_total_seconds": total, "generations_per_cell": dict(plan.get("generations") or {}),
            "transform_passes_per_cell": dict(plan.get("transform_passes") or {}),
            "preprov_generations": preprov, "basis": plan["basis"],
        }
        if attempts:
            node["blocked_attempt_seconds"] = attempts
        if kind_name == "freeze_baseline":
            node["groups"] = {"G1": {"cells": [c["id"] for c in cells["A"]], "arms": list(contract_arms)},
                              "G2": {"cells": [c["id"] for c in cells["A"]]},
                              "G3": {"cells": [c["id"] for c in cells["B"]]}}
        run_kinds[kind_name] = node

    ab_once = sum(gen_cost(c) for kind in ("A", "B") for c in cells[kind] if c["id"] not in history_ids)
    savings = [
        {"method": "Task 0.5 凍結之 run 保留至 Phase 1 結束，Task 1.1–1.3 讀之（postic_branchdiff 不重生；"
                   "precision_chain 之 S1–S5 於同一生成擷取）", "saved_seconds": ab_once * 2},
        {"method": f"格 C {FULLRUN_SIZE_TF} 單格基準沿用 PRE-PROV 全特徵 run 收據（產品碼未變）",
         "saved_seconds": float(baseline.get(FULLRUN_SIZE_TF, {}).get("seconds", 0.0))},
        {"method": "同（格, 生成環境）於單一測試模組內只生成一次（G1Lab／CellLab／_Runs 快取；G1 各臂份共用來源 run）",
         "saved_seconds": sum(gen_cost(c) * max(0, len(arms_of(c)) - 1) for c in cells["A"] if c["id"] not in history_ids)},
    ]
    return {"run_kinds": run_kinds, "cell_c_baseline": baseline, "blocked": blocked, "history_blocked": history,
            "savings": savings, "b_membership": b_records, "cost_basis": cost_basis,
            "total_extrapolated_seconds": grand_total}


def pre_history_table(cells: Mapping[str, List[Dict[str, Any]]], criteria: Mapping[str, Any], kline_path: Path,
                      b_records: Mapping[str, Mapping[str, Any]],
                      measurements: Optional[Mapping[str, Mapping[str, Any]]] = None) -> Dict[str, Any]:
    """逐格所需前史（判準檔 cell_rules.window_rule 之 record 欄）；設定解析同生成（FeatureFactory._resolve_config），
    D₀ 依（格類, 訓練週期）快取（同設定、同週期組之 D₀ 相同）。實測過之格（實測紀錄 `cell_id`、同訓練週期）取該 run 定案
    之預熱深度（`warmup_basis=final`）；其餘以初值 D₀ 計並標 `initial_d0_lower_bound`（下界，不外推加倍）。"""
    from momentum.factories import create_feature_factory

    factory = create_feature_factory(cache_dir=str(Path(kline_path).parent), validate_continuity=False)
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

def _parse(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NUMVIEW 量測格估時（SPEC Task 0.4）")
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
        print(json.dumps({"cells": {k: len(v) for k, v in cells.items()},
                          "targets": [t["target"] for t in targets],
                          "would_measure": [t["target"] for t in selected]}, ensure_ascii=False, indent=2))
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
    blocked_c_tfs: Set[str] = {k.split(":", 1)[1] for k, m in measurements.items()
                               if k.startswith("C:") and m.get("status") in ("blocked", "killed")}
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
                    and (cached.get("output_window") != window or cached.get("kline_source") != records):
                measurements.pop(key, None)  # 快取為舊區間或舊來源資料集（kline_source 紀錄不同）⇒ 依現行判準重量
        if key in measurements and measurements[key].get("status") in ("measured", "blocked", "killed") \
                and not args.remeasure:
            continue
        if target["category"] == "C" and key.split(":", 1)[1] in blocked_c_tfs:
            continue
        print(f"[estimate] 實測 {key} …", flush=True)
        result = _run_target(target, work_root, kline_path, args.timeout_seconds)
        measurements[key] = result
        cache_path.write_text(json.dumps(measurements, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[estimate] {key}: {result.get('status')} {result.get('seconds', '')}", flush=True)
    failed = {k: m for k, m in measurements.items() if not measurement_accepted(m)}
    if failed:
        print(f"實測失敗：{json.dumps(failed, ensure_ascii=False)[:2000]}", file=sys.stderr)
        return 1
    missing = [t["target"] for t in targets if t["target"] not in measurements]
    if missing:
        print(f"尚有未實測之目標 {missing}（已存快取 {cache_path}）；全部實測後再跑一次以寫收據", file=sys.stderr)
        return 1
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

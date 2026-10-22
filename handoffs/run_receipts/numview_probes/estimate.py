"""NUMVIEW 量測格清單與估時（docs/NUMVIEW_SPEC.md Task 0.4，R2-B、R15-A；先於一切重型跑）。

自 `data_cache/feature_klines/kline_cache.h5` 列舉 symbol×tf（不寫死清單）：格 A＝每個 symbol×tf 單週期短窗、
格 B＝每個 symbol 之「最細週期主＋其餘週期訓練」多週期格、格 C＝生產預設全特徵於每個 symbol×tf。格之生成定義
（設定覆寫、輸出段根數、前史門檻、IC-first 參數）一律讀事前登記判準檔 `tests/_golden/numview/preregistered_criteria.json`
之 `cell_definitions`（本檔不另寫設定）。

實測：各類先實測一格之耗時與峰值記憶體——格 A 逐週期一格、格 B 一格、格 C 逐週期一格（12h 引
`handoffs/run_receipts/20261020-preprov-fullrun-size.md` 之 run A 列，4h／1h 各實測）、PRE-PROV 格逐格（Phase 2–4
驗收測試直接經 `preprov_helpers` 生成之格）。每次實測於獨立子行程、隔離目錄（設定檔連結、CGSA 工作目錄、registry、
d* 快取、tempdir 皆導向該目錄；不寫 `data_cache/`）執行，量畢即刪該目錄。格 A／B 之實測另以生成內擷取之 post-IC
輸入，於每個可達臂（契約 `post_ic_arm_reachability`）各計一次 IC 頁預設請求之轉換秒數，供轉換型跑別外推。

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
import json
import os
import platform
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
CRITERIA_PATH: Path = REPO / "tests" / "_golden" / "numview" / "preregistered_criteria.json"
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

#: 跑別 → 外推計畫。`cells`：格類（"A"／"AB"／"ABC"）、"t21"（REGEN_T21_CELL 單格）或 ""；`generations`：每格生成次數
#: （一次＝一次 `generate_cell` 等價之 IC-first 生成，格 C＝一次全史生成）；`transform_passes`：每格「每個可達臂各一次
#: IC 頁預設轉換」之次數；`branchdiff`：Task 1.1 之轉換量（ICPOSTLEAK 分支∪候選臂 × 七組合，另速度量測可達臂∪候選臂 × 3
#: 次）；`preprov`：PRE-PROV 格 → 生成次數（"*legacy*"＝沿用基準全部格）。`basis` 為盤點來源。
RUN_PLAN: Dict[str, Dict[str, Any]] = {
    "freeze_baseline": {
        "cells": "AB", "generations": {"A": 2, "B": 1}, "transform_passes": {"A": 1}, "preprov": {},
        "basis": "SPEC Task 0.5／§G：格 A 之 G2 於 FFACT_USE_POLARS 0／1 各生成一次（G1 以其中來源 run 跑各可達臂之 IC 頁轉換"
                 "一次）；格 B 之 G3 生成一次。"},
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


def cell_payload(cell: Mapping[str, Any], criteria: Mapping[str, Any]) -> Dict[str, Any]:
    """格之設定覆寫（判準檔 cell_definitions.<格類>.config_override，週期依 timeframes_rule 由格描述子填入）。"""
    definition = criteria["cell_definitions"][str(cell["kind"])]
    payload = copy.deepcopy(definition["config_override"])
    tfs = [str(t) for t in cell["timeframes"]]
    payload["timeframes"] = {**dict(payload.get("timeframes") or {}), "primary": tfs[0], "training": tfs}
    return payload


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


def measurement_targets(cells: Mapping[str, List[Dict[str, Any]]], inventory: Mapping[str, Mapping[str, int]],
                        symbol: Optional[str]) -> List[Dict[str, Any]]:
    """實測目標：格 A 逐週期一格、格 B 一格、格 C 逐週期一格（FULLRUN_SIZE_TF 引收據、不實測）、PRE-PROV 逐格。"""
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
        if tf == FULLRUN_SIZE_TF and (REPO / FULLRUN_SIZE_RECEIPT).is_file():
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


def _measure_ic_first_cell(spec: Mapping[str, Any], work: Path) -> Dict[str, Any]:
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    criteria = load_json(CRITERIA_PATH)
    cell = spec["cell"]
    definition = criteria["cell_definitions"][cell["kind"]]
    generation = definition["generation"]
    features_root = _isolate(work, {})
    payload = cell_payload(cell, criteria)
    start, end = output_window(Path(spec["kline_path"]), cell["symbol"], cell["timeframes"][0],
                               int(definition["output_bars"]))
    factory = create_feature_factory(cache_dir=str(Path(spec["kline_path"]).parent), validate_continuity=False)
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
    try:
        factory.run_ic_first(cell["symbol"], cell["timeframes"][0], config, start_date=start, end_date=end,
                             ic_engine=ICEngine(dict(generation["ic_engine_config"])),
                             feature_reader=FeatureReader(str(features_root)),
                             ic_threshold=generation["ic_threshold"], label_horizon=str(generation["label_horizon"]),
                             cleanup_raw=bool(generation["cleanup_raw"]))
    finally:
        FeaturePreprocessor.transform_selected = real  # type: ignore[assignment]
    seconds = time.perf_counter() - started
    timing = _time_ic_page_arms(captured.get("selected") or [], captured.get("groups") or {})
    return {"seconds": seconds, "output_window": [start, end], **timing}


def _measure_full_cell(spec: Mapping[str, Any], work: Path) -> Dict[str, Any]:
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    criteria = load_json(CRITERIA_PATH)
    cell = spec["cell"]
    features_root = _isolate(work, {})
    factory = create_feature_factory(cache_dir=str(Path(spec["kline_path"]).parent), validate_continuity=False)
    factory._storage = FeatureStorage(str(features_root))
    started = time.perf_counter()
    factory.generate_features(cell["symbol"], cell["timeframes"][0], config_override=cell_payload(cell, criteria),
                              force_regenerate=True, persist=True)
    return {"seconds": time.perf_counter() - started}


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
    try:
        if spec["category"] in ("A", "B"):
            result.update(_measure_ic_first_cell(spec, work))
        elif spec["category"] == "C":
            result.update(_measure_full_cell(spec, work))
        else:
            result.update(_measure_preprov_cell(spec, work))
        result["status"] = "measured"
    except BaseException as exc:  # noqa: BLE001 — 失敗之型別決定 blocked 或 failed，皆寫結果
        result["status"] = "blocked" if _is_memory_guard(exc) else "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"[:2000]
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


def build_receipt(cells: Mapping[str, List[Dict[str, Any]]], inventory: Mapping[str, Mapping[str, int]],
                  criteria: Mapping[str, Any], measurements: Mapping[str, Mapping[str, Any]],
                  contract_arms: Sequence[str]) -> Dict[str, Any]:
    """依實測快取與 RUN_PLAN 組估時收據（不含 `reported_at`）。"""
    gen_seconds: Dict[Tuple[str, str], float] = {}
    arm_seconds: Dict[Tuple[str, str], Dict[str, float]] = {}
    for key, m in measurements.items():
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
        if tf == FULLRUN_SIZE_TF and (REPO / FULLRUN_SIZE_RECEIPT).is_file():
            baseline[tf] = fullrun_baseline()
            gen_seconds[("C", tf)] = baseline[tf]["seconds"]
            continue
        m = measurements.get(f"C:{tf}") or {}
        if m.get("status") == "measured":
            baseline[tf] = {"seconds": float(m["seconds"]), "peak_rss_bytes": int(m["peak_rss_bytes"]), "source": "measured"}
        elif m.get("status") in ("blocked", "killed"):
            reason = f"格 C 單格實測（{m.get('target')}）逾機器上限：{m.get('status')} {m.get('error', '')}".strip()
            baseline[tf] = {"blocked_by": BLOCKED_BY_HARDWARE, "reason": reason}
            for cell in cells["C"]:
                if cell["timeframes"] == [tf]:
                    blocked.append({"cell": cell["id"], "blocked_by": BLOCKED_BY_HARDWARE, "reason": reason})
        else:
            raise EstimateError(f"格 C {tf} 無實測結果（{m.get('status')}）")
    blocked_c = {b["cell"] for b in blocked}
    history = [h for kind in ("A", "B") for c in cells[kind] if (h := history_blocked(c, inventory, criteria))]
    blocked.extend(history)
    history_ids = {h["cell"] for h in history}

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
        total = sum(per_cell.values()) + sum(per_preprov.values())
        grand_total += total
        node: Dict[str, Any] = {
            "cells": [c["id"] for c in listed], "preprov_cells": sorted(preprov),
            "single_cell_seconds": single, "per_cell_seconds": per_cell, "preprov_seconds": per_preprov,
            "extrapolated_total_seconds": total, "generations_per_cell": dict(plan.get("generations") or {}),
            "transform_passes_per_cell": dict(plan.get("transform_passes") or {}),
            "preprov_generations": preprov, "basis": plan["basis"],
        }
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
    return {"run_kinds": run_kinds, "cell_c_baseline": baseline, "blocked": blocked, "savings": savings,
            "total_extrapolated_seconds": grand_total}


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
        criteria_bytes = CRITERIA_PATH.read_bytes()
    except FileNotFoundError:
        print(f"判準檔不存在：{CRITERIA_PATH}（Task 0.3 先於估時）", file=sys.stderr)
        return 1
    criteria = json.loads(criteria_bytes.decode("utf-8"))
    inventory = kline_inventory(kline_path)
    cells = enumerate_cells(kline_path)
    contract_arms = list(numeric_view.load_contract()["post_ic_arm_values"]["values"])
    targets = measurement_targets(cells, inventory, args.symbol)
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
    # 只有格 C 之記憶體守護終止（blocked）或被系統終止（killed）可記為 blocked-by 硬體（邊界①）；其餘非 measured
    # （failed、timeout，或格 A／B／PRE-PROV 之 blocked／killed）一律為實測失敗 ⇒ rc=1，不寫收據
    failed = {k: m for k, m in measurements.items()
              if not (m.get("status") == "measured"
                      or (m.get("category") == "C" and m.get("status") in ("blocked", "killed")))}
    if failed:
        print(f"實測失敗：{json.dumps(failed, ensure_ascii=False)[:2000]}", file=sys.stderr)
        return 1
    missing = [t["target"] for t in targets if t["target"] not in measurements]
    if missing:
        print(f"尚有未實測之目標 {missing}（已存快取 {cache_path}）；全部實測後再跑一次以寫收據", file=sys.stderr)
        return 1
    body = build_receipt(cells, inventory, criteria, measurements, contract_arms)
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

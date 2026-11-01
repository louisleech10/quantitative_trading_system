"""ICPERF Task 0.2（docs/ICPERF_SPEC.md Task 0.2，v5.50 (a)–(f) 為準）：規模盤點之行程內逐入口計時——路徑實跑＋直接呼叫格。

每一規模點對每一路徑（或直接呼叫格）實跑**一個行程**，外層一律由 `scripts/scale_probe.py` 啟動（行程樹 RSS、身分、冪次擬合；
`{scale}` 代入規模），行程內以「重綁全部引用」（v5.50 (a)）把清冊 `scripts/icperf_path_inventory.json` 每一 `measure=true`
入口換成同一計數／計時 wrapper，逐入口記錄寫 `<records-dir>/<run_id>/<axis>-<scale>/<path_run_id>.json`。不改產品碼。

用法（重型；由 `scripts/icperf_freeze_baseline.py measure` 經 scale_probe 啟動，不單獨前景跑全規模）：
  venv/bin/python scripts/icperf_scale_harness.py run <run_id> --axis cols --scale {scale} --records-dir handoffs/run_receipts/icperf_task02_records/<session>/<attempt>
  venv/bin/python scripts/icperf_scale_harness.py list                 # 列出路徑與直接呼叫格及其所涵蓋之清冊入口數
  venv/bin/python scripts/icperf_scale_harness.py plan                 # 清冊 measure=true 入口 ⇒ branch_cell 對照與未涵蓋者
  venv/bin/python scripts/icperf_scale_harness.py precheck-rows        # v5.51 (a)：列數軸列長之樣本外切分秒級預檢
  run 之選項：--axis cols|rows|events（預設 cols；rows＝固定 `ROW_AXIS_COLS` 欄、子集列數截為末 {scale} 列；events＝事件數）
  --inventory <清冊>（預設 scripts/icperf_path_inventory.json）、--out-root <工作根>（預設 runs/icperf/task02）

路徑（`PATHS`）與直接呼叫格（`CELLS`）——入口歸屬以清冊 `branch_cell` 欄為準：
- `ic_page_default`：C 格交接 h5 之 N 欄巢狀子集（seed 20261027；`icperf_freeze_baseline._write_stage5_subset`）以 IC 頁預設請求
  之 override 跑 `create_ic_analyzer(override).analyze`（同 §G (2) `_child_stage5`）；本路徑同時把直接呼叫格所需之各段真實輸入
  存於 `<out-root>/stage_inputs/<N>/`（v5.50 (d)；pickle，含 self 物件＝路徑同一設定）。
- `deep_analysis`：同上之 analyze 後於同一 analyzer 續跑深度分析全部模組（§G (3) 之請求）。
- `post_ic_transform`：A 格 run 以 feature_filter 限 N 欄（`small_request`，排序前綴＝巢狀）經服務 `start_analysis`，再
  `_apply_transforms_sync`（rank／zscore／gaussian 全開、預設窗）作用於倖存欄。
- `event_import`：L 格 run 以 feature_filter 限 N 欄、帶 §G (7) 事件匯入批（`event_import_run`）。
- `event_study`：事件研究頁之 `EventImportService.import_records`＋`analyze`（隔離之事件儲存根；批＝`icperf_event_batch`
  規則以 L 格真實 kline 建之事件，events 軸取依 t0 排序之前 {scale} 筆）；另以 feature_run 呼叫投影分支（失敗記錄於收據）。
- `cross_sectional`：A 格 BTCUSDT／SOLUSDT 兩 run 共同欄之 N 欄（排序前綴）經 `icperf_correctness_receipt._child_cross`。
- `icfirst_post_generation`：阻擋（見 `_run_icfirst_post_generation` 之碼證）——以 `HarnessError` 回報，不以他物代替。
- 直接呼叫格（`CELLS`）：讀 `stage_inputs/<N>/` 之真實輸入，以路徑同一設定物件（pickle 之 self）呼叫互斥分支：滾動 IC
  kendall／pearson、冗餘 hierarchical／vif／多元化約束、regime kmeans、fit_mode pit_expanding（C 格 500 列 ≤ 512 ⇒ percentile
  走 `pit_expanding_bounds`）、PIT mad 縮尾、`standardize` 之 time_series_zscore＋pit_expanding、無缺值向量化 IC。
- 資料界限（2026-11-01 smoke 實測）：C 格 500 列於 IC 頁預設請求之切分測試段 95 列 < 最少 131 列 ⇒ 產品改走全樣本重跑
  （`ic_filter_orchestrator.py:1975-1990`，fit_mode=full_sample）——故 `ic_page_default` 量到的是 full_sample 分支
  （`_clip_series_static`）；train_mask 分支（`_clip_series_train`、`_slice_rolling_ic_to_test`）須列數足夠之資料格才走得到。
- SPEC v5.51 (a)：樣本外分支入口歸 `ic_page_long`（L 格 2,000 列，IC 頁預設請求走樣本外切分）；IC 頁／深度分析／直接呼叫格之
  rows 軸一律於 L 格（`ic_page_long`／`deep_analysis_long` 之 rows 軸，`ROW_AXIS_SCALES`＋`ROW_AXIS_WINDOW_OVERRIDE`；三列長
  先過 `split_precheck`）。L 格交接 h5 由 `icperf_freeze_baseline.py gen-l-handoff` 產生（`l_handoff_path`）。
- SPEC v5.51 (d)：event_study 之主軸＝events（`primary_axis`）；(f) 判準② `criterion2`；(g) 兩點例外依收據合計推估對
  budget_seconds；(h) footprint 取同 path_run_id 之紀錄；(i) 收據引用之紀錄存 `TASK02_RECORDS_ROOT`（不覆寫）。

逐入口記錄（`EntryStats.to_json`；不存原始值）：呼叫次數、最外層累計牆鐘秒（perf_counter；**含巢狀入口時間**＝inclusive，
扣除 harness 本身之包裝與雜湊開銷）、呼叫期間峰值 RSS（取樣執行緒＋長呼叫結束時讀取）、首末呼叫之輸入形狀、PIT／逐欄入口
（清冊 loop＝per_bar／per_column）之輸入鍵（sha256〔值位元組＋有限遮罩〕＋欄名＋其餘決定輸出之參數；依路徑 symbol 分開）之
計數（判準③）、實際受算欄名集合（判準④）、≥ `INTERVAL_RECORD_MIN_SECONDS` 之呼叫起訖區間與路徑 `progress_callback` 時點
（判準⑤）。行程結束前以 macOS `sample <pid> 1` 取本行程 Physical footprint (peak)（§B；只用工具、不設取樣停止與終止）。
"""

from __future__ import annotations

import argparse
import bisect
import contextlib
import copy
import functools
import hashlib
import importlib
import importlib.util
import inspect
import json
import os
import re
import subprocess
import sys
import threading
import time
import types
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

# 本檔之契約測試於測試行程內 import；模組層只 import 標準函式庫（numpy／pandas 於函式內載入）。

REPO = Path(__file__).resolve().parents[1]
INVENTORY_PATH = REPO / "scripts" / "icperf_path_inventory.json"
TASK02_ROOT = "runs/icperf/task02"
RECORD_SCHEMA = "icperf-t02-entry-records/1"
RECEIPT_SCHEMA = "icperf-t02-scale-before/1"
FOOTPRINT_TOOL = "sample:Physical footprint"
#: SPEC Task 0.2 判準⑤：單一入口連續 > 60 秒未經 progress_callback 回報
PROGRESS_GAP_SECONDS = 60.0
#: 只保存 ≥ 此秒數之呼叫區間（< 此值者其內最長無回報間隔必 < 此值 ≤ 60 秒，不影響判準⑤；以 max_call_seconds 為上界）
INTERVAL_RECORD_MIN_SECONDS = 1.0
MAX_INTERVALS = 20000
MAX_DUP_EXAMPLES = 20
#: 輸入鍵所及之清冊 loop 類別（PIT 與逐欄計算入口，SPEC v5.50 (b)）
KEYED_LOOPS = ("per_bar", "per_column")
#: 入口級 RSS 取樣間隔（秒；同 scale_probe `_TreeRssSampler` 預設 0.2）
RSS_SAMPLE_INTERVAL = 0.2
#: 呼叫結束時另讀 RSS 之最短呼叫秒數（更短之呼叫讀 RSS 之開銷相對過大）
END_RSS_MIN_SECONDS = 0.01
#: rows 軸之固定欄數（L 格交接 h5 之巢狀子集；SPEC v5.51 (a)「固定欄數取 L 格可用欄之子集」）
ROW_AXIS_COLS = 500
#: 規模點（SPEC Task 0.2）
SCALE_POINTS = (500, 1000, 2000)
#: SPEC v5.51 (a)：列數軸與樣本外分支之資料格＝L 格（`icperf_freeze_baseline.LONG_CELL`，BTCUSDT 4h、2,000 列、raw 3,632 欄）
LONG_CELL_ID = "L_BTCUSDT_4h_longhist"
LONG_CELL_TIMEFRAME = "4h"
LONG_CELL_ROWS = 2000
#: SPEC v5.51 (a)：列數軸之三種列長（L 格交接 h5 之末 R 列）——須皆過 `split_precheck`（樣本外切分成立）。
#: IC 頁預設請求於 4h 之預檢（`split_precheck`，2026-11-01 實跑）：最少測試段列數＝max(調整後滾動窗 [63,189,378]、ICIR 窗 189)
#: ＋horizon 5＝383、`min_test_rows`＝131；測試段列數＝N−⌈0.8N⌉−purge 5 ⇒ 只有 N ≥ 1,940 成立（2,000 列 ⇒ 395，與 SPEC v5.27
#: 實跑一致）、1,000 列 ⇒ 195 不成立。L 格只有 2,000 列（標籤來源主檔 4h 只 5,088 根）⇒ 依 la1 同法
#: （`tests/golden/la1/gen_baseline.py` `RUN_WINDOW_OVERRIDES`／`with_run_windows`）加視窗覆寫 `ROW_AXIS_WINDOW_OVERRIDE`
ROW_AXIS_SCALES = (1000, 1500, 2000)
#: 列數軸請求之視窗覆寫（深合併入 `config_override["ic_calculation"]`）：只移除預設 [21, 63, 126] 之最長窗 126（ICIR 窗維持
#: 預設 63）⇒ 4h 最少測試段列數 189＋5＝194 ≤ 1,000 列之測試段 195。三種列長同一覆寫（列數軸內設定不變）；cols 軸不加覆寫
ROW_AXIS_WINDOW_OVERRIDE: Dict[str, Any] = {"rolling_windows": [21, 63], "icir": {"window": 63}}
#: 各路徑／格之列數軸實跑（cols 軸所屬路徑 ⇒ rows 軸實跑之路徑；v5.51 (a)：rows 軸一律於 L 格）
ROW_AXIS_RUN: Dict[str, str] = {}
#: 列數軸只在短序列分支可達之格（`data_preprocessor.py:464` 長度 ≤ 512 才走 `pit_expanding_bounds`）：其 rows 軸取最小列長
#: 之 L 格存檔輸入之末 R 列（R ∈ 下列；直接呼叫格不經切分，不需預檢）
CELL_ROW_SCALES: Dict[str, Tuple[int, ...]] = {"fit_mode_pit_expanding": (128, 256, 512)}
#: SPEC v5.51 (i)：量測收據引用之逐入口紀錄存處（入版控；不覆寫）；`runs/` 只作執行期暫存（work、子集、存檔輸入）
TASK02_RECORDS_ROOT = "handoffs/run_receipts/icperf_task02_records"
#: SPEC v5.51 (f)：判準②之硬體下限（無原型時唯一可碼層斷定「不成立」之依據）：每單位（unit_axis 各軸之積）至少讀一個 8 bytes
#: 浮點數一次；以本機記憶體頻寬上界 ~100 GB/s 計 ≈ 8e-11 秒，取 1e-10 秒為保守下限（任何實作之每單位秒數皆不低於此）⇒ 實測
#: 每單位秒數 < 10 × 此值 ⇒ 必未達「下限 × 10」⇒ 判準②為假；其餘無原型者標 pending_prototype（列 Phase 1 原型補量）
CRITERION2_FLOOR_SECONDS_PER_UNIT = 1e-10
#: 跨標的路徑之兩格（A 格同週期兩標的）
CROSS_CELLS = ("A_BTCUSDT_1h", "A_SOLUSDT_1h")

#: 路徑實跑（v5.49）：id ⇒ 說明
PATHS: Dict[str, str] = {
    "ic_page_default": "C 格 N 欄巢狀子集＋IC 頁預設請求 analyze（第 0–7 段）；存直接呼叫格之各段真實輸入",
    "ic_page_long": "L 格（4h 2,000 列，樣本外切分成立）交接 h5 之 N 欄巢狀子集＋IC 頁預設請求 analyze（樣本外分支入口）；"
                    "rows 軸＝固定 ROW_AXIS_COLS 欄、末 R 列、ROW_AXIS_WINDOW_OVERRIDE（存直接呼叫格之列數軸真實輸入）",
    "deep_analysis": "同 ic_page_default 之 analyze 後同一 analyzer 續跑深度分析全部模組",
    "deep_analysis_long": "同 ic_page_long 之 rows 軸 analyze 後同一 analyzer 續跑深度分析全部模組（深度分析之列數軸）",
    "post_ic_transform": "A 格 run feature_filter N 欄經服務 start_analysis 後 _apply_transforms_sync（rank／zscore／gaussian）",
    "event_import": "L 格 run feature_filter N 欄＋§G (7) 事件匯入批（event_import_run）",
    "event_study": "事件研究頁：隔離儲存根之 import_records＋analyze（events 軸＝前 {scale} 筆事件）",
    "cross_sectional": "A 格 BTCUSDT／SOLUSDT 兩 run 共同 N 欄之跨標的 analyze_cross_sectional",
    "icfirst_post_generation": "IC-first 之 _run_ic_first_post_generation 整段與子步驟（阻擋：見 _run_icfirst_post_generation）",
}
#: 直接呼叫格（v5.50 (d)）：id ⇒ 說明
CELLS: Dict[str, str] = {
    "rolling_kendall": "存檔第 4 段滾動 IC 輸入＋同一 ICEngine，method=kendall",
    "rolling_pearson": "存檔第 4 段滾動 IC 輸入＋同一 ICEngine，method=pearson",
    "redundancy_hierarchical": "存檔第 6 段冗餘輸入（第 5 段通過欄矩陣、IC 分數）＋同一 RedundancyFilter，method=hierarchical",
    "redundancy_vif": "同上，method=vif",
    "redundancy_diversification": "同上 greedy 後 apply_diversification_constraint（同一 RedundancyFilter 複本，enabled=True）",
    "regime_kmeans": "存檔 compute_grouped_ic 輸入（含 regime_history 之 close／volume 與設定）＋同一 ICEngine，regime_method=kmeans",
    "fit_mode_pit_expanding": "存檔第 1 段輸入＋同一 DataPreprocessor，fit_mode=pit_expanding（percentile；C 格列數 ≤ 512 ⇒ pit_expanding_bounds）",
    "winsor_mad_pit": "同上，縮尾 method=mad、fit_mode=pit_expanding（pit_expanding_mad）",
    "standardize_tszscore_pit": "存檔第 1 段輸出＋同一 DataPreprocessor.standardize(method=time_series_zscore, fit_mode=pit_expanding)",
    "vectorized_ic_no_missing": "存檔第 4 段 compute_ic 輸入取標籤有限列與全有限欄（_has_missing 為 False）＋同一 ICEngine",
}
#: 預設路徑實跑時存之各段真實輸入（入口 id ⇒ (存檔名, 是否另存回傳值)）；只存第一次呼叫
CAPTURES: Dict[str, Tuple[str, bool]] = {
    "momentum.Analysis.data_preprocessor:DataPreprocessor.preprocess": ("preprocess", True),
    "momentum.Analysis.ic_engine:ICEngine.compute_ic": ("compute_ic", False),
    "momentum.Analysis.ic_engine:ICEngine.compute_rolling_ic": ("rolling_ic", False),
    "momentum.Analysis.ic_engine:ICEngine.compute_grouped_ic": ("grouped_ic", False),
    "momentum.Analysis.redundancy_filter:RedundancyFilter.filter": ("redundancy_filter", False),
    "momentum.Analysis.redundancy_filter:RedundancyFilter.compute_diversification_metrics": ("diversification_metrics", False),
}
#: 各格所需之存檔
CELL_CAPTURES: Dict[str, Tuple[str, ...]] = {
    "rolling_kendall": ("rolling_ic",), "rolling_pearson": ("rolling_ic",),
    "redundancy_hierarchical": ("redundancy_filter",), "redundancy_vif": ("redundancy_filter",),
    "redundancy_diversification": ("redundancy_filter", "diversification_metrics"),
    "regime_kmeans": ("grouped_ic",), "fit_mode_pit_expanding": ("preprocess",),
    "winsor_mad_pit": ("preprocess",), "standardize_tszscore_pit": ("preprocess",),
    "vectorized_ic_no_missing": ("compute_ic",),
}
#: 各路徑／格可用之軸（v5.51 (a)：IC 頁與深度分析之 rows 軸改由 L 格路徑 `ic_page_long`／`deep_analysis_long` 實跑）
RUN_AXES: Dict[str, Tuple[str, ...]] = {
    **{c: ("cols", "rows") for c in CELLS},
    "ic_page_default": ("cols",), "ic_page_long": ("cols", "rows"), "deep_analysis": ("cols",),
    "deep_analysis_long": ("rows",), "post_ic_transform": ("cols",),
    "event_import": ("cols",), "event_study": ("events",), "cross_sectional": ("cols",),
    "icfirst_post_generation": ("cols",),
}
ROW_AXIS_RUN.update({"ic_page_default": "ic_page_long", "ic_page_long": "ic_page_long",
                     "deep_analysis": "deep_analysis_long", **{c: c for c in CELLS}})
#: 寫直接呼叫格所需存檔之 (路徑, 軸)：cols 軸取 C 格 ic_page_default、rows 軸取 L 格 ic_page_long
CAPTURE_RUNS: Tuple[Tuple[str, str], ...] = (("ic_page_default", "cols"), ("ic_page_long", "rows"))


def primary_axis(run_id: str) -> str:
    """路徑／格之主軸（收據 points 之 x 軸）：只有事件數軸者（event_study）＝"events"，其餘＝"cols"（SPEC v5.51 (d)）。"""
    axes = RUN_AXES.get(run_id, ())
    return "events" if axes == ("events",) else "cols"


def row_scales_for(run_id: str) -> Tuple[int, ...]:
    """rows 軸實跑之列長：`CELL_ROW_SCALES` 所列之格用其短序列列長，其餘＝`ROW_AXIS_SCALES`。"""
    return tuple(CELL_ROW_SCALES.get(run_id, ROW_AXIS_SCALES))


class HarnessError(RuntimeError):
    """量測不可進行（輸入不存在、資料不足、阻擋項）；訊息附碼證或路徑。"""


class AssemblyError(RuntimeError):
    """量測收據組裝失敗（漏量、呼叫次數 0、記錄與 scale_probe 收據不相符等）；`problems` 為逐條問題。"""

    def __init__(self, problems: Sequence[str]):
        super().__init__(f"量測收據組裝失敗（{len(problems)} 條）：" + "；".join(list(problems)[:10]))
        self.problems = list(problems)


def _load_script(name: str, rel: str) -> Any:
    """以檔案路徑載入 repo 內腳本為模組（已載入者沿用）。"""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _fb() -> Any:
    return _load_script("icperf_t02_freeze_baseline", "scripts/icperf_freeze_baseline.py")


def load_inventory(path: Path = INVENTORY_PATH) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def coverage_plan(inventory: Mapping[str, Any]) -> Dict[str, List[str]]:
    """清冊 measure=true 入口依 `branch_cell` 分組：{run_id: [入口 id...]}；未知 run_id 或缺 branch_cell 者歸 "__uncovered__"。"""
    out: Dict[str, List[str]] = {}
    known = set(PATHS) | set(CELLS)
    for e in inventory.get("entries") or []:
        if not e.get("measure"):
            continue
        cell = e.get("branch_cell")
        out.setdefault(cell if cell in known else "__uncovered__", []).append(str(e["id"]))
    return out


# ── 入口解析與重綁全部引用（v5.50 (a)） ───────────────────────────────────────────────────────────────────


class Target:
    """清冊入口之解析結果：`owner`（模組或類別）、`name`、`kind`（function／staticmethod／classmethod）、`func`（原物件；
    staticmethod／classmethod 為其底層函式）。"""

    __slots__ = ("eid", "owner", "name", "kind", "func")

    def __init__(self, eid: str, owner: Any, name: str, kind: str, func: Any):
        self.eid, self.owner, self.name, self.kind, self.func = eid, owner, name, kind, func


def resolve_target(eid: str) -> Target:
    """`<模組>:<限定名>` ⇒ Target；模組不可 import 或屬性不存在 ⇒ HarnessError。類別屬性取定義類別之 `__dict__`
    （沿 MRO 找第一個含該名者），以分辨 staticmethod／classmethod。"""
    module, _, qual = eid.partition(":")
    try:
        owner: Any = importlib.import_module(module)
        parts = qual.split(".")
        for p in parts[:-1]:
            owner = getattr(owner, p)
        name = parts[-1]
        if isinstance(owner, type):
            raw = next((k.__dict__[name] for k in owner.__mro__ if name in k.__dict__), None)
            if raw is None:
                raise AttributeError(name)
        else:
            raw = getattr(owner, name)
    except Exception as exc:  # noqa: BLE001 — 解析失敗一律以 HarnessError 點名入口
        raise HarnessError(f"清冊入口無法解析：{eid}（{type(exc).__name__}: {exc}）") from exc
    if isinstance(raw, staticmethod):
        return Target(eid, owner, name, "staticmethod", raw.__func__)
    if isinstance(raw, classmethod):
        return Target(eid, owner, name, "classmethod", raw.__func__)
    if not callable(raw):
        raise HarnessError(f"清冊入口非可呼叫物件：{eid}（{type(raw).__name__}）")
    return Target(eid, owner, name, "function", raw)


def resolve_targets(eids: Iterable[str]) -> Dict[str, Target]:
    out: Dict[str, Target] = {}
    errors: List[str] = []
    for eid in eids:
        try:
            out[eid] = resolve_target(eid)
        except HarnessError as exc:
            errors.append(str(exc))
    if errors:
        raise HarnessError("；".join(errors))
    return out


class Rebinding:
    """`rebind_all` 之結果：`wrappers`（入口 id ⇒ wrapper）、`counts`（入口 id ⇒ 被換掉之綁定數）、`restore()` 還原。"""

    def __init__(self) -> None:
        self.wrappers: Dict[str, Any] = {}
        self.counts: Dict[str, int] = {}
        self._undo: List[Tuple[str, Any, str, Any]] = []

    def restore(self) -> None:
        for kind, container, key, old in reversed(self._undo):
            if kind == "dict":
                container[key] = old
            else:
                setattr(container, key, old)
        self._undo.clear()


def _iter_classes(root: Any, seen: Set[int]) -> Iterable[type]:
    """`root`（類別）與其類別屬性中之巢狀類別（深度優先；以 id 去重）。"""
    stack = [root]
    while stack:
        cls = stack.pop()
        if id(cls) in seen:
            continue
        seen.add(id(cls))
        yield cls
        try:
            items = list(vars(cls).values())
        except TypeError:
            continue
        stack.extend(v for v in items if isinstance(v, type))


def rebind_all(targets: Mapping[str, Any], recorder: Optional["Recorder"] = None,
               make_wrapper: Optional[Callable[[str, Any], Any]] = None) -> Rebinding:
    """重綁全部引用（SPEC v5.50 (a)）：`targets`＝{入口 id: 原物件（函式；方法為類別上之底層函式）}。走訪 `sys.modules`
    全部模組之全域名、其中類別（含巢狀類別）之 `__dict__`、模組層 dict 之值（一層，dispatch 表），凡 `is` 指向某入口原物件
    者一律換為**同一個** wrapper（類別上之 staticmethod／classmethod 以同型描述子包回）。函式內延遲 import（如
    `factor_combiner.py:173` 之 `from momentum.Analysis.marginal_ic import ...`）於執行時讀定義模組屬性 ⇒ 取到 wrapper。
    不涵蓋：實例屬性中已綁定之方法物件、閉包／預設參數持有之原物件——以收據「呼叫次數 ≥ 1」斷言兜底。

    `make_wrapper(eid, func)` 未給 ⇒ 以 `recorder` 之計數／計時 wrapper（`_make_wrapper`）。回 `Rebinding`。"""
    if make_wrapper is None:
        if recorder is None:
            raise ValueError("rebind_all 須給 recorder 或 make_wrapper")
        make_wrapper = functools.partial(_make_wrapper, rec=recorder)
    result = Rebinding()
    by_id: Dict[int, str] = {}
    keep: List[Any] = []
    for eid, func in targets.items():
        if id(func) in by_id:
            raise HarnessError(f"兩入口指向同一物件：{by_id[id(func)]}、{eid}")
        by_id[id(func)] = eid
        keep.append(func)
        result.wrappers[eid] = make_wrapper(eid, func)
        result.counts[eid] = 0
    seen_classes: Set[int] = set()

    def swap_dict(d: Dict[str, Any], key: str, eid: str) -> None:
        result._undo.append(("dict", d, key, d[key]))
        d[key] = result.wrappers[eid]
        result.counts[eid] += 1

    for mod in list(sys.modules.values()):
        if not isinstance(mod, types.ModuleType):
            continue
        try:
            g = vars(mod)
        except TypeError:
            continue
        for name, val in list(g.items()):
            eid = by_id.get(id(val))
            if eid is not None:
                swap_dict(g, name, eid)
                continue
            if isinstance(val, type):
                for cls in _iter_classes(val, seen_classes):
                    try:
                        attrs = list(vars(cls).items())
                    except TypeError:
                        continue
                    for aname, aval in attrs:
                        inner = aval.__func__ if isinstance(aval, (staticmethod, classmethod)) else aval
                        ceid = by_id.get(id(inner))
                        if ceid is None:
                            continue
                        w = result.wrappers[ceid]
                        new = staticmethod(w) if isinstance(aval, staticmethod) else (
                            classmethod(w) if isinstance(aval, classmethod) else w)
                        result._undo.append(("attr", cls, aname, aval))
                        setattr(cls, aname, new)
                        result.counts[ceid] += 1
            elif isinstance(val, dict) and val is not g and len(val) <= 2000:
                for k, v in list(val.items()):
                    deid = by_id.get(id(v))
                    if deid is not None:
                        swap_dict(val, k, deid)
    del keep
    return result


# ── 逐入口記錄 ──────────────────────────────────────────────────────────────────────────────────────────


def _feed_array(h: Any, arr: Any) -> None:
    import numpy as np

    a = np.asarray(arr)
    h.update(f"{a.dtype.str}{a.shape}".encode())
    if a.dtype.kind in "biufcmM?":
        a = np.ascontiguousarray(a)
        h.update(a.view(np.uint8).reshape(-1).data if a.size else b"")
        if a.dtype.kind in "fc":
            h.update(np.packbits(np.isfinite(a).reshape(-1)).tobytes())
    else:
        import pandas as pd

        h.update(pd.util.hash_array(a.reshape(-1).astype(object)).tobytes())


def _feed(h: Any, tag: str, v: Any, cols: List[str]) -> None:
    """輸入鍵之一個參數：陣列類依內容與有限遮罩、欄名；純量與小容器依 repr；其他物件（self、設定物件）只依型別名。"""
    import numpy as np
    import pandas as pd

    h.update(tag.encode())
    if isinstance(v, pd.Series):
        cols.append(str(v.name))
        h.update(b"S" + repr(v.name).encode())
        _feed_array(h, v.to_numpy())
    elif isinstance(v, pd.DataFrame):
        names = [str(c) for c in v.columns]
        cols.extend(names)
        h.update(b"D" + repr(names).encode())
        for i in range(v.shape[1]):
            _feed_array(h, v.iloc[:, i].to_numpy())
    elif isinstance(v, (np.ndarray, pd.Index)):
        _feed_array(h, np.asarray(v))
    elif v is None or isinstance(v, (bool, int, float, str, bytes, np.generic)):
        h.update(repr(v).encode())
    elif isinstance(v, (list, tuple, dict, set, frozenset)):
        text = repr(v)
        h.update((text if len(text) <= 100_000 else hashlib.sha256(text.encode()).hexdigest()).encode())
    else:
        h.update(type(v).__qualname__.encode())


def call_key(args: Sequence[Any], kwargs: Mapping[str, Any], context: str) -> Tuple[str, List[str]]:
    """輸入鍵（SPEC v5.50 (b)）＝sha256(路徑 symbol 等脈絡、每一參數之內容〔值位元組＋有限遮罩〕、欄名、q／require_full_q 等
    其餘參數之 repr)；回 (鍵前 32 位十六進位, 參數中之欄名)。不保存原始值。"""
    h = hashlib.sha256(context.encode())
    cols: List[str] = []
    for i, a in enumerate(args):
        _feed(h, f"a{i}", a, cols)
    for k in sorted(kwargs):
        _feed(h, f"k{k}", kwargs[k], cols)
    return h.hexdigest()[:32], cols


def _shapes(args: Sequence[Any], kwargs: Mapping[str, Any]) -> List[List[int]]:
    out: List[List[int]] = []
    for v in list(args) + list(kwargs.values()):
        shape = getattr(v, "shape", None)
        if isinstance(shape, tuple) and all(isinstance(s, int) for s in shape) and not isinstance(v, type):
            out.append(list(shape))
    return out


def max_progress_gap(intervals: Sequence[Sequence[float]], progress_times: Sequence[float]) -> float:
    """各呼叫區間 [s, e] 內，以 {s} ∪ 區間內 progress 時點 ∪ {e} 之相鄰差之最大者（判準⑤；區間為空 ⇒ 0.0）。"""
    pts = sorted(float(t) for t in progress_times)
    best = 0.0
    for s, e in intervals:
        lo, hi = bisect.bisect_left(pts, float(s)), bisect.bisect_right(pts, float(e))
        seq = [float(s)] + pts[lo:hi] + [float(e)]
        best = max(best, max(b - a for a, b in zip(seq, seq[1:])))
    return best


class EntryStats:
    """單一入口於一次實跑之累計（呼叫次數、秒數、RSS、形狀、輸入鍵、受算欄、長呼叫區間）。"""

    def __init__(self, eid: str, keyed: bool):
        self.eid, self.keyed = eid, keyed
        self.calls = self.outer_calls = self.raised = 0
        self.seconds = 0.0
        self.max_call_seconds = 0.0
        self.peak_rss: Optional[int] = None
        self.first_shapes: Optional[List[List[int]]] = None
        self.last_shapes: Optional[List[List[int]]] = None
        self.max_rows = self.max_cols = 0
        self.keys: Dict[str, int] = {}
        self.key_cols: Dict[str, str] = {}
        self.columns: Set[str] = set()
        self.intervals: List[Tuple[float, float]] = []
        self.intervals_truncated = False
        self.captured = False
        self.capture_error: Optional[str] = None
        self.lock = threading.Lock()

    def add(self, *, start: float, end: float, inner: float, outer: bool, raised: bool,
            key: Optional[Tuple[str, List[str]]], shapes: List[List[int]]) -> None:
        with self.lock:
            self.calls += 1
            self.raised += int(raised)
            if outer:
                self.outer_calls += 1
                self.seconds += max(inner, 0.0)
                dur = end - start
                self.max_call_seconds = max(self.max_call_seconds, dur)
                if dur >= INTERVAL_RECORD_MIN_SECONDS:
                    if len(self.intervals) < MAX_INTERVALS:
                        self.intervals.append((start, end))
                    else:
                        self.intervals_truncated = True
            if self.first_shapes is None:
                self.first_shapes = shapes
            self.last_shapes = shapes
            for s in shapes:
                if s:
                    self.max_rows = max(self.max_rows, int(s[0]))
                if len(s) >= 2:
                    self.max_cols = max(self.max_cols, int(s[1]))
            if key is not None:
                k, cols = key
                self.keys[k] = self.keys.get(k, 0) + 1
                if k not in self.key_cols:
                    self.key_cols[k] = cols[0] if len(cols) == 1 else (f"<{len(cols)} 欄>" if cols else "")
                self.columns.update(cols)

    def bump_rss(self, rss: int) -> None:
        if self.peak_rss is None or rss > self.peak_rss:
            self.peak_rss = rss

    def to_json(self, progress_times: Sequence[float]) -> Dict[str, Any]:
        dups = sorted(((k, c) for k, c in self.keys.items() if c > 1), key=lambda kc: -kc[1])
        gap = max_progress_gap(self.intervals, progress_times) if self.intervals else self.max_call_seconds
        return {"calls": self.calls, "outer_calls": self.outer_calls, "raised": self.raised,
                "seconds": self.seconds,
                "seconds_scope": "inclusive：最外層呼叫之牆鐘秒和（含巢狀入口，扣除 harness 包裝與輸入鍵雜湊開銷）",
                "max_call_seconds": self.max_call_seconds, "peak_rss_bytes": self.peak_rss,
                "first_input_shapes": self.first_shapes, "last_input_shapes": self.last_shapes,
                "max_rows": self.max_rows, "max_cols": self.max_cols, "keyed": self.keyed,
                "n_keys": len(self.keys) if self.keyed else None,
                "duplicate_keys": len(dups) if self.keyed else None,
                "max_key_count": max(self.keys.values()) if self.keys else None,
                "duplicate_examples": [{"key": k, "count": c, "column": self.key_cols.get(k, "")}
                                       for k, c in dups[:MAX_DUP_EXAMPLES]] if self.keyed else None,
                "computed_columns": sorted(self.columns) if self.keyed else None,
                "long_intervals": [[round(s, 6), round(e, 6)] for s, e in self.intervals],
                "intervals_truncated": self.intervals_truncated,
                "max_progress_gap_seconds": gap,
                "progress_gap_basis": "intervals" if self.intervals else "upper_bound_max_call_seconds",
                "capture_error": self.capture_error}


class Recorder:
    """一次實跑之全部入口記錄、progress 時點與入口級 RSS 取樣（執行緒安全；巢狀深度與開銷依執行緒分開）。"""

    def __init__(self, keyed: Iterable[str] = (), context: str = "", captures: Optional[Mapping[str, Callable]] = None,
                 heartbeat: bool = True):
        self.keyed = set(keyed)
        self.context = context
        self.captures: Dict[str, Callable[[Tuple[Any, ...], Dict[str, Any], Any], None]] = dict(captures or {})
        self.stats: Dict[str, EntryStats] = {}
        self.t0 = time.perf_counter()
        self.progress_times: List[float] = []
        self.overhead_seconds = 0.0
        self.heartbeat = heartbeat
        self._tls = threading.local()
        self._active: Dict[str, int] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._proc: Any = None

    def stat(self, eid: str) -> EntryStats:
        st = self.stats.get(eid)
        if st is None:
            st = self.stats[eid] = EntryStats(eid, eid in self.keyed)
        return st

    def progress(self, payload: Any = None, *args: Any, **kwargs: Any) -> None:
        """產品 progress_callback：記時點（相對本記錄起點之秒），並印心跳使共用監看之 log 反映實際進度。"""
        self.progress_times.append(time.perf_counter() - self.t0)
        if self.heartbeat:
            keys = ("stage_name", "stage", "progress", "module_name", "current_step", "message")
            shown = {k: payload.get(k) for k in keys if isinstance(payload, Mapping) and k in payload}
            print("[icperf-t02-progress] " + json.dumps(shown, ensure_ascii=False, default=str), flush=True)

    def _rss(self) -> Optional[int]:
        try:
            if self._proc is None:
                import psutil

                self._proc = psutil.Process(os.getpid())
            return int(self._proc.memory_info().rss)
        except Exception:  # noqa: BLE001 — psutil 不可用 ⇒ 退回 getrusage 之峰值（行程級）
            import resource

            v = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            return v if sys.platform == "darwin" else v * 1024

    def _enter(self, eid: str) -> None:
        with self._lock:
            self._active[eid] = self._active.get(eid, 0) + 1

    def _exit(self, eid: str) -> None:
        with self._lock:
            n = self._active.get(eid, 0) - 1
            if n <= 0:
                self._active.pop(eid, None)
            else:
                self._active[eid] = n

    def _loop(self) -> None:
        while not self._stop.is_set():
            rss = self._rss()
            if rss is not None:
                with self._lock:
                    active = list(self._active)
                for eid in active:
                    self.stat(eid).bump_rss(rss)
            self._stop.wait(RSS_SAMPLE_INTERVAL)

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="icperf-t02-rss", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()

    def entries_json(self) -> Dict[str, Dict[str, Any]]:
        return {eid: st.to_json(self.progress_times) for eid, st in sorted(self.stats.items())}


def _make_wrapper(eid: str, func: Any, *, rec: Recorder) -> Any:
    """入口之計數／計時 wrapper：最外層呼叫之秒數＝函式本體牆鐘秒 − 其內巢狀 wrapper 之開銷（輸入鍵雜湊、存檔、記帳）；
    遞迴呼叫只計次數不重複計秒；例外照原樣上拋（記 raised）。"""
    st = rec.stat(eid)
    keyed = st.keyed
    capture = rec.captures.get(eid)
    perf = time.perf_counter
    tls = rec._tls
    if inspect.isgeneratorfunction(func):
        return _make_gen_wrapper(eid, func, rec=rec)

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        t0 = perf()
        depth = tls.__dict__.setdefault("depth", {})
        d = depth.get(eid, 0)
        key = call_key(args, kwargs, rec.context) if keyed else None
        rec._enter(eid)
        depth[eid] = d + 1
        ov_before = tls.__dict__.get("ov", 0.0)
        ok = False
        result = None
        t1 = perf()
        try:
            result = func(*args, **kwargs)
            ok = True
            return result
        finally:
            t2 = perf()
            depth[eid] = d
            rec._exit(eid)
            inner = (t2 - t1) - (tls.__dict__.get("ov", 0.0) - ov_before)
            st.add(start=t1 - rec.t0, end=t2 - rec.t0, inner=inner, outer=(d == 0), raised=not ok, key=key,
                   shapes=_shapes(args, kwargs))
            if inner >= END_RSS_MIN_SECONDS:
                rss = rec._rss()
                if rss is not None:
                    st.bump_rss(rss)
            if ok and capture is not None and not st.captured:
                st.captured = True
                try:
                    capture(args, kwargs, result)
                except Exception as exc:  # noqa: BLE001 — 存檔失敗不影響受測計算；記錄後由直接呼叫格報缺
                    st.capture_error = f"{type(exc).__name__}: {exc}"
            spent = (t1 - t0) + (perf() - t2)
            tls.__dict__["ov"] = tls.__dict__.get("ov", 0.0) + spent
            with rec._lock:
                rec.overhead_seconds += spent

    return _finish_wrapper(wrapper, func, eid)


def _finish_wrapper(wrapper: Any, func: Any, eid: str) -> Any:
    try:
        functools.update_wrapper(wrapper, func)
    except (AttributeError, TypeError):
        wrapper.__wrapped__ = func  # type: ignore[attr-defined]
    wrapper.__icperf_t02_entry__ = eid  # type: ignore[attr-defined]
    return wrapper


def _make_gen_wrapper(eid: str, func: Any, *, rec: Recorder) -> Any:
    """產生器入口（清冊中 `FeatureReader.stream_groups_v2`）：一次呼叫＝一次完整迭代；秒數＝各次 `next` 內之牆鐘秒和（呼叫端
    處理各元素之時間不計；不扣巢狀 wrapper 開銷）；不支援 send／throw 之計時（照原樣轉發迭代）。"""
    st = rec.stat(eid)
    perf = time.perf_counter

    def gen_wrapper(*args: Any, **kwargs: Any) -> Any:
        it = func(*args, **kwargs)
        start, total, ok = perf() - rec.t0, 0.0, False
        rec._enter(eid)
        try:
            while True:
                t = perf()
                try:
                    value = next(it)
                except StopIteration as stop:
                    total += perf() - t
                    ok = True
                    return stop.value
                total += perf() - t
                yield value
        finally:
            rec._exit(eid)
            st.add(start=start, end=perf() - rec.t0, inner=total, outer=True, raised=not ok, key=None,
                   shapes=_shapes(args, kwargs))

    return _finish_wrapper(gen_wrapper, func, eid)


# ── 各段真實輸入之存檔與讀回（v5.50 (d)） ───────────────────────────────────────────────────────────────


def _strip_callables(v: Any) -> Any:
    """存檔前把參數中之可呼叫物件（progress hook 等綁定方法，會連帶 pickle 整個 orchestrator）換成 None。"""
    if callable(v) and not isinstance(v, type) and not hasattr(v, "shape"):
        return None
    return v


def _capture_writer(stage_dir: Path, name: str, with_result: bool, provenance: Mapping[str, Any]) -> Callable:
    def write(args: Tuple[Any, ...], kwargs: Dict[str, Any], result: Any) -> None:
        import pickle

        out = stage_dir / f"{name}.pkl"
        if out.exists():
            return
        stage_dir.mkdir(parents=True, exist_ok=True)
        self_obj, rest = (args[0], args[1:]) if args and not hasattr(args[0], "shape") else (None, args)
        payload = {"self": self_obj, "args": tuple(_strip_callables(a) for a in rest),
                   "kwargs": {k: _strip_callables(v) for k, v in kwargs.items()},
                   "dropped_callables": [k for k, v in kwargs.items() if _strip_callables(v) is None and v is not None],
                   "result": result if with_result else None, "provenance": dict(provenance)}
        tmp = out.with_suffix(".pkl.part")
        with open(tmp, "wb") as fh:
            pickle.dump(payload, fh, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, out)

    return write


def stage_input_card(root: Path) -> None:
    """`stage_inputs/` 說明卡（可重用之中介輸入，不放系統暫存；SPEC v5.45 §G (2) ②之說明卡格式）。"""
    card = root / "README.txt"
    if card.exists():
        return
    root.mkdir(parents=True, exist_ok=True)
    card.write_text(
        "入口：scripts/icperf_scale_harness.py run ic_page_default（cols 軸，C 格 <N>/）／ic_page_long --axis rows（L 格 "
        "L<cols>_rows<R>/）（scale_probe 啟動之路徑實跑）\n"
        "用途：ICPERF Task 0.2 直接呼叫格之各段真實輸入（<N>/<名>.pkl：第 1 段輸入與輸出、第 4 段 compute_ic／滾動 IC／"
        "分組 IC 輸入、第 6 段冗餘輸入與多元化指標輸入；含路徑同一設定之 self 物件；SPEC v5.50 (d)）\n"
        f"建立：{time.strftime('%Y-%m-%d %H:%M:%S %z')}\n"
        "git HEAD：見各 pkl 之 provenance.head\n"
        "何時可刪：Task 0.2 之量測收據（handoffs/run_receipts/*-icperf-scale-before.json）提交並推送後；刪後由 ic_page_default 路徑重產\n",
        encoding="utf-8")


def load_capture(stage_dir: Path, name: str) -> Dict[str, Any]:
    import pickle

    path = Path(stage_dir) / f"{name}.pkl"
    if not path.is_file():
        raise HarnessError(f"直接呼叫格之存檔真實輸入不存在：{path}（須先跑同一規模點之 ic_page_default 路徑）")
    with open(path, "rb") as fh:
        return pickle.load(fh)


def _bind_call(func: Any, self_obj: Any, cap: Mapping[str, Any], **override: Any) -> Any:
    """以存檔之 (self, args, kwargs) 依 `func` 之簽名綁定、覆寫指定參數後呼叫（經類別屬性＝已重綁之 wrapper）。"""
    sig = inspect.signature(func)
    params = [self_obj] if self_obj is not None else []
    ba = sig.bind(*params, *cap["args"], **cap["kwargs"])
    for k, v in override.items():
        if k not in sig.parameters:
            raise HarnessError(f"{getattr(func, '__qualname__', func)} 無參數 {k}")
        ba.arguments[k] = v
    return func(*ba.args, **ba.kwargs)


# ── 樣本外切分之秒級碼層預檢（v5.51 (a)） ────────────────────────────────────────────────────────────────


def with_row_windows(override: Optional[Mapping[str, Any]],
                     windows: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """`override`（IC 頁 config_override）深合併列數軸視窗覆寫（預設 `ROW_AXIS_WINDOW_OVERRIDE`）入 `ic_calculation`，回新
    dict（同 `tests/golden/la1/gen_baseline.py` `with_run_windows`：rolling_windows 取代、icir 鍵合併，其餘鍵保留）。"""
    patch = ROW_AXIS_WINDOW_OVERRIDE if windows is None else windows
    out = json.loads(json.dumps(dict(override or {})))
    ic = out.setdefault("ic_calculation", {})
    if "rolling_windows" in patch:
        ic["rolling_windows"] = list(patch["rolling_windows"])
    if "icir" in patch:
        ic["icir"] = {**(ic.get("icir") or {}), **dict(patch["icir"])}
    return out


def precheck_override(timeframe: str, *, row_windows: bool) -> Dict[str, Any]:
    """預檢用之 IC 頁預設請求 override：`icperf_freeze_baseline.IC_PAGE_DEFAULT_PAYLOAD` 經服務 `_build_config_override`
    （同量測之 `_override_for`；symbol／config_hash 不影響 override，不讀資料檔）；`row_windows` ⇒ 加列數軸視窗覆寫。"""
    fb = _fb()
    payload = fb._json_copy(fb.IC_PAGE_DEFAULT_PAYLOAD)
    request = {"symbol": "BTCUSDT", "timeframe": str(timeframe), "config_hash": "icperf-t02-precheck",
               "config_override": payload["config_override"], "feature_tiers": payload["feature_tiers"]}
    override = fb._override_for(request) or {}
    return with_row_windows(override) if row_windows else dict(override)


def split_precheck(n_rows: int, timeframe: str, override: Optional[Mapping[str, Any]], *,
                   symbol: str = "BTCUSDT") -> Dict[str, Any]:
    """秒級碼層預檢（不跑 IC）：`n_rows` 列、`timeframe` 之單標的 IC 頁請求（`override`）是否走樣本外切分。直接呼叫產品之
    同一組函式（`ic_filter_orchestrator.py` analyze 之 :1505-1520 換算視窗、:1535-1576 `_build_holdout_split_plan`
    〔min_test_rows、purge＝effective horizon〕、:1651-1654 `_precheck_rolling_warmup`〔`_rolling_warmup_min_rows`〕）；
    時間軸＝`n_rows` 根連續等距之 DatetimeIndex（量測資料為連續之末 R 列，`_truncate_rows`）。labels 檔不預載（IC 頁
    `labels_path=""`）⇒ horizon 取 `_resolve_effective_label_horizon(config, None)`。回 {"n_rows", "timeframe", "oos": bool,
    "reason"（None｜insufficient_data｜rolling_warmup_insufficient｜split_disabled）, "train_rows", "test_rows",
    "min_test_rows", "min_warmup_rows", "effective_horizon", "adjusted_windows", "icir_window"}。"""
    import pandas as pd

    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from momentum.Analysis import ic_filter_orchestrator as orch
    from momentum.factories import create_ic_analyzer

    ov = dict(override) if override else None
    analyzer = create_ic_analyzer(ov)
    config = analyzer._apply_tier_config(analyzer._apply_config_override(ov))
    analyzer._ic_engine.set_timeframe(str(timeframe), reference_tf=config.ic_calculation.icir.reference_tf)
    horizon = int(orch._resolve_effective_label_horizon(config, None))
    adjusted = [int(w) for w in analyzer._ic_engine._adjust_rolling_windows(list(config.ic_calculation.rolling_windows))]
    out: Dict[str, Any] = {"n_rows": int(n_rows), "timeframe": str(timeframe), "oos": False, "reason": None,
                           "train_rows": None, "test_rows": None, "min_test_rows": int(config.min_test_rows),
                           "min_warmup_rows": int(analyzer._rolling_warmup_min_rows(config, horizon)),
                           "effective_horizon": horizon, "adjusted_windows": adjusted,
                           "icir_window": int(config.ic_calculation.icir.window),
                           "rolling_windows": [int(w) for w in config.ic_calculation.rolling_windows]}
    if not config.ic_train_test_split:
        out["reason"] = "split_disabled"
        return out
    freq = orch._resolve_expected_freq({"timeframe": str(timeframe)})
    index = pd.date_range("2024-01-01", periods=int(n_rows), freq=freq)
    features = pd.DataFrame(index=index)
    split = orch._build_holdout_split_plan(features, config, symbol, freq, purge_gap=horizon, labels_df=None)
    if isinstance(split, orch.SkippedResult):
        out.update(reason="insufficient_data", **{k: (split.details or {}).get(k) for k in ("train_rows", "test_rows")})
        return out
    train_plan, test_plan = split
    train_mask, test_mask = orch._derive_stage_masks(train_plan, test_plan, features.index)
    ctx = {"train_mask": train_mask, "test_mask": test_mask, "effective_horizon": horizon}
    pre = analyzer._precheck_rolling_warmup(features, config, ctx, None, event_conditional=False)
    out.update(train_rows=int(train_mask.sum()), test_rows=int(test_mask.sum()))
    if pre is not None:
        out["reason"] = "rolling_warmup_insufficient"
        return out
    out["oos"] = True
    return out


def row_axis_precheck(scales: Sequence[int] = ROW_AXIS_SCALES) -> Dict[str, Any]:
    """列數軸三種列長之預檢收據：L 格週期下，IC 頁預設請求（無覆寫）與列數軸請求（`ROW_AXIS_WINDOW_OVERRIDE`）逐列長之
    `split_precheck`，並另驗 ic_page_long 之 cols 軸（L 格全長 `LONG_CELL_ROWS`、無覆寫）。`ok`＝列數軸每一列長與 cols 軸皆
    走樣本外切分。"""
    default = precheck_override(LONG_CELL_TIMEFRAME, row_windows=False)
    rows_ov = precheck_override(LONG_CELL_TIMEFRAME, row_windows=True)
    by_default = [split_precheck(n, LONG_CELL_TIMEFRAME, default) for n in scales]
    by_rows = [split_precheck(n, LONG_CELL_TIMEFRAME, rows_ov) for n in scales]
    cols = split_precheck(LONG_CELL_ROWS, LONG_CELL_TIMEFRAME, default)
    return {"cell": LONG_CELL_ID, "timeframe": LONG_CELL_TIMEFRAME, "scales": [int(s) for s in scales],
            "window_override": ROW_AXIS_WINDOW_OVERRIDE, "default_request": by_default, "row_axis_request": by_rows,
            "cols_axis": cols, "ok": bool(cols["oos"] and all(r["oos"] for r in by_rows))}


# ── 路徑與直接呼叫格之實作 ─────────────────────────────────────────────────────────────────────────────


#: 以 L 格為資料源之路徑（cols 軸亦然）；其餘路徑之 rows 軸亦於 L 格（`RunContext.long`）
LONG_RUNS = ("ic_page_long", "deep_analysis_long")
#: 讀交接 h5 巢狀子集之路徑
SUBSET_RUNS = ("ic_page_default", "ic_page_long", "deep_analysis", "deep_analysis_long")


class RunContext:
    def __init__(self, run_id: str, axis: str, scale: int, out_root: Path, work: Path, rec: Recorder,
                 head: Optional[str]):
        self.run_id, self.axis, self.scale = run_id, axis, int(scale)
        self.out_root, self.work, self.rec, self.head = out_root, work, rec, head
        self.n_cols = int(scale) if axis == "cols" else ROW_AXIS_COLS
        self.n_rows: Optional[int] = int(scale) if axis == "rows" else None
        #: v5.51 (a)：rows 軸與 L 格路徑之資料源＝L 格交接 h5
        self.long = axis == "rows" or run_id in LONG_RUNS

    @property
    def stage_dir(self) -> Path:
        return self.out_root / "stage_inputs" / self.stage_tag(self.n_rows)

    def stage_tag(self, n_rows: Optional[int]) -> str:
        if n_rows is None:
            return f"L{self.n_cols}" if self.long else str(self.n_cols)
        return f"L{self.n_cols}_rows{int(n_rows)}"


def _truncate_rows(src_h5: Path, src_meta: Path, rows: int, out_dir: Path) -> Tuple[Path, Path]:
    """子集 h5 之末 `rows` 列（列數為首維＝原列數之資料集逐一切；屬性與 meta 照抄）。"""
    import h5py
    import shutil

    out_dir.mkdir(parents=True, exist_ok=True)
    h5, meta = out_dir / src_h5.name, out_dir / src_meta.name
    with h5py.File(src_h5, "r") as f, h5py.File(h5, "w") as g:
        for k, v in f.attrs.items():
            g.attrs[k] = v

        def copy_group(a: Any, b: Any) -> None:
            for k, v in a.attrs.items():
                b.attrs[k] = v
            n = a["timestamps"].shape[0] if "timestamps" in a else None
            if n is not None and rows > n:
                raise HarnessError(f"rows 軸 {rows} 列 > 子集列數 {n}（資料不足；須以更長之資料格補足）")
            for k, v in a.items():
                if isinstance(v, h5py.Group):
                    copy_group(v, b.create_group(k))
                elif n is not None and v.shape and v.shape[0] == n:
                    b.create_dataset(k, data=v[n - rows:], dtype=v.dtype, compression="gzip")
                else:
                    b.create_dataset(k, data=v[()], dtype=v.dtype)

        copy_group(f, g)
    shutil.copyfile(src_meta, meta)
    return h5, meta


def subset_source(long: bool) -> Path:
    """巢狀子集之來源交接 h5：C 格（`icperf_freeze_baseline.c_handoff_path`）或 L 格（`l_handoff_path`；v5.51 (a)）。"""
    fb = _fb()
    return fb.l_handoff_path() if long else fb.c_handoff_path()


def _subset_paths(ctx: RunContext) -> Tuple[Path, Path]:
    """交接 h5（C 格；rows 軸與 L 格路徑＝L 格，v5.51 (a)）之 N 欄巢狀子集（`<out-root>/subsets/<tag>/`；不存在則以
    `_write_stage5_subset` 建）；rows 軸另截末 R 列。"""
    fb = _fb()
    src = subset_source(ctx.long)
    src_meta = src.with_name(src.stem + "_meta.json")
    sub_dir = ctx.out_root / "subsets" / ctx.stage_tag(None)
    h5, meta = sub_dir / src.name, sub_dir / src_meta.name
    if not (h5.is_file() and meta.is_file()):
        h5, meta = fb._write_stage5_subset(src, src_meta, ctx.n_cols, fb.SEED, sub_dir)
    if ctx.n_rows is not None:
        rdir = ctx.out_root / "subsets" / ctx.stage_tag(ctx.n_rows)
        if not (rdir / h5.name).is_file():
            return _truncate_rows(h5, meta, ctx.n_rows, rdir)
        return rdir / h5.name, rdir / meta.name
    return h5, meta


def _h5_rows(h5: Path) -> int:
    import h5py

    with h5py.File(h5, "r") as f:
        found: List[int] = []
        f.visititems(lambda k, v: found.append(int(v.shape[0])) if k.endswith("timestamps") else None)
    return found[0] if found else 0


def _ic_facts(report: Any, analyzer: Any, input_cols: int, rows: int) -> Dict[str, Any]:
    try:
        survivors = int(len(analyzer.get_filtered_features().columns))
    except Exception:  # noqa: BLE001 — 無倖存 frame（全被篩掉）⇒ 0
        survivors = 0
    fl = (report or {}).get("filter_log") or {} if isinstance(report, Mapping) else {}
    stage_counts = {k: v.get("input_features") for k, v in fl.items()
                    if isinstance(v, Mapping) and isinstance(v.get("input_features"), int)}
    return {"input_cols": int(input_cols), "rows": int(rows), "survivors": survivors, "stage_counts": stage_counts}


def _ic_page_analyze_subset(ctx: RunContext, request: Mapping[str, Any]) -> Tuple[Any, Any, Path]:
    from api.services.ic_analysis_service import FEATURE_KLINE_CACHE_DIR
    from momentum.factories import create_ic_analyzer, create_kline_storage_manager

    fb = _fb()
    h5, meta = _subset_paths(ctx)
    override = fb._override_for(request)
    if ctx.axis == "rows":
        # v5.51 (a)：列數軸三種列長同一視窗覆寫（`ROW_AXIS_WINDOW_OVERRIDE`；三列長皆過 split_precheck）
        override = with_row_windows(override)
    analyzer = create_ic_analyzer(override)
    report = analyzer.analyze(features_path=str(h5), labels_path="", meta_path=str(meta), config_override=override,
                              progress_callback=ctx.rec.progress,
                              kline_reader=create_kline_storage_manager(cache_dir=FEATURE_KLINE_CACHE_DIR))
    return analyzer, report, h5


def _page_request(ctx: RunContext, item: str) -> Dict[str, Any]:
    """路徑之 IC 頁請求：L 格資料源（rows 軸、L 格路徑）⇒ `default_request(item, LONG_CELL)`，其餘 C／A 格預設。"""
    fb = _fb()
    return fb.default_request(item, fb.LONG_CELL) if ctx.long else fb.default_request(item)


def _split_facts(report: Any) -> Dict[str, Any]:
    """報告 metadata 之切分事實（`ic_train_test_split.applied`、train／test 列數；v5.51 (a) 實跑驗樣本外切分）。"""
    md = (report or {}).get("metadata") or {} if isinstance(report, Mapping) else {}
    sp = md.get("ic_train_test_split") or {}
    return {"split_applied": sp.get("applied"), "split_train_rows": sp.get("train_rows"),
            "split_test_rows": sp.get("test_rows")}


def _run_ic_page_default(ctx: RunContext) -> Dict[str, Any]:
    analyzer, report, h5 = _ic_page_analyze_subset(ctx, _page_request(ctx, "ic_report"))
    return {**_ic_facts(report, analyzer, ctx.n_cols, _h5_rows(h5)), **_split_facts(report), "requested_columns": None}


def _run_deep_analysis(ctx: RunContext) -> Dict[str, Any]:
    from api.models.ic_models import DeepAnalysisRequest
    from api.services.ic_analysis_service import ICAnalysisService

    request = _page_request(ctx, "deep_analysis")
    analyzer, report, h5 = _ic_page_analyze_subset(ctx, request)
    svc = ICAnalysisService.__new__(ICAnalysisService)
    deep_request = DeepAnalysisRequest(**request["deep"])
    deep_override = svc._build_deep_module_override(deep_request)
    selected = svc._resolve_selected_features(analyzer=analyzer, selected_features=deep_request.selected_features,
                                              top_n=deep_request.top_n)
    deep_report = analyzer.run_deep_analysis(selected, deep_override, ctx.rec.progress, None)
    svc._attach_cross_symbol_context(svc._serialize_deep_report(deep_report), analyzer)
    return {**_ic_facts(report, analyzer, ctx.n_cols, _h5_rows(h5)), **_split_facts(report),
            "deep_selected": len(selected or []), "requested_columns": None}


def _service_with_tasks(request: Mapping[str, Any], registry: Path) -> Any:
    import threading as _th

    svc = _fb()._ic_service(request, registry)
    svc._lock = _th.Lock()
    svc._tasks = {}
    svc._callbacks = {}
    svc._last_task_id = None
    return svc


def _manifest_rows(request: Mapping[str, Any]) -> int:
    m = json.loads((REPO / request["run_dir"] / "feature_manifest.json").read_text(encoding="utf-8"))
    return int(m.get("row_count") or 0)


def _limited_request(item: str, cell: Optional[str], n: int) -> Dict[str, Any]:
    fb = _fb()
    base = fb.default_request(item) if cell is None else fb.default_request(item, cell)
    pool = fb._run_feature_names(base)
    if len(set(pool)) < n:
        raise HarnessError(f"{base['cell']} 之 raw 欄數 {len(set(pool))} < 規模 {n}（資料不足；須以欄數足夠之 run 補足）")
    return fb.small_request(item, base, n)


def _service_analysis(svc: Any, req: Any, rec: Recorder, **start_kwargs: Any) -> Tuple[str, Dict[str, Any]]:
    """服務 `start_analysis`（`asyncio.create_task` 啟動之分析於同一事件迴圈內等候完成；同 `event_import_run`），並以
    `register_notification_callback` 把服務之進度通知接到 `rec.progress`（判準⑤之時點）；status ≠ completed ⇒ HarnessError。"""
    import asyncio

    async def go() -> str:
        started = await svc.start_analysis(req, **start_kwargs)
        task_id = str(started["task_id"])
        svc.register_notification_callback(task_id, rec.progress)
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        await asyncio.gather(*pending)
        return task_id

    task_id = asyncio.run(go())
    info = svc._tasks[task_id]
    if info.get("status") != "completed":
        raise HarnessError(f"IC 分析未完成：status={info.get('status')!r} error={info.get('error')!r}")
    return task_id, info


def _run_post_ic_transform(ctx: RunContext) -> Dict[str, Any]:
    fb = _fb()
    request = _limited_request("ic_report", None, ctx.n_cols)
    svc = _service_with_tasks(request, ctx.work / "registry.json")
    task_id, info = _service_analysis(svc, fb._ic_analyze_request(request), ctx.rec)
    analyzer = info["analyzer"]
    survivors = list(analyzer.get_filtered_features().columns)
    if not survivors:
        raise HarnessError("post_ic_transform：IC 倖存欄為空，無法量 IC 後轉換（資料不足）")
    svc._apply_transforms_sync(task_id, survivors, True, True, True, 252, [100, 252])
    names = list(request["feature_filter"]["include_features"])
    return {"input_cols": ctx.n_cols, "rows": _manifest_rows(request), "survivors": len(survivors),
            "requested_columns": names}


def _run_event_import(ctx: RunContext) -> Dict[str, Any]:
    from api.services.case_import_service import EventImportService

    from api.routes.ic_analysis import _resolve_event_batch

    fb = _fb()
    request = _limited_request("event_import_report", None, ctx.n_cols)
    # 同 `icperf_freeze_baseline.event_import_run`（route `_resolve_event_batch`＋服務 `start_analysis`），另接進度通知
    svc = _service_with_tasks(request, ctx.work / "registry.json")
    req = fb._ic_analyze_request(request)
    _task_id, info = _service_analysis(svc, req, ctx.rec, event_batch=_resolve_event_batch(req))
    analyzer = info.get("analyzer")
    detail = EventImportService().get_import(str(request["event_import_id"]))
    facts = _ic_facts(info.get("result"), analyzer, ctx.n_cols, _manifest_rows(request))
    return {**facts, "events": len(detail.records) if detail is not None else None,
            "requested_columns": list(request["feature_filter"]["include_features"])}


def _event_batch_records(n_events: Optional[int]) -> List[Dict[str, Any]]:
    eb = _load_script("icperf_t02_event_batch", "scripts/icperf_event_batch.py")
    records = sorted(eb.build_records(eb._cell_window())["records"], key=lambda r: int(r["t0"]))
    if n_events is not None:
        if n_events > len(records):
            raise HarnessError(f"event_study：events 軸 {n_events} > 批之事件數 {len(records)}（資料不足）")
        records = records[:n_events]
    return records


def _run_event_study(ctx: RunContext) -> Dict[str, Any]:
    from api.models.event_import_models import EventAnalyzeRequest, FeatureRunRef
    from api.services.case_import_service import EventImportService

    fb = _fb()
    records = _event_batch_records(ctx.scale if ctx.axis == "events" else None)
    upload = json.dumps(records, ensure_ascii=False, sort_keys=True).encode("utf-8")
    svc = EventImportService(storage_dir=ctx.work / "events")
    resp = svc.import_records(records, source_name="icperf-t02-event-study", upload_bytes=upload, validate_only=False)
    out = svc.analyze(resp.import_id, EventAnalyzeRequest())
    run = fb._cell_run(fb.LONG_CELL)
    projection_error = None
    try:
        svc.analyze(resp.import_id, EventAnalyzeRequest(feature_run=FeatureRunRef(
            symbol=run["symbol"], timeframe=run["timeframe"], config_hash=run["config_hash"])))
    except Exception as exc:  # noqa: BLE001 — 投影分支失敗照記（收據以 raised 判非量測）
        projection_error = f"{type(exc).__name__}: {exc}"
    return {"input_cols": 0, "rows": 0, "events": len(records), "requested_columns": None,
            "event_study_ok": out is not None, "projection_error": projection_error}


def _run_cross_sectional(ctx: RunContext) -> Dict[str, Any]:
    fb = _fb()
    cells = [fb.default_request("ic_report", c) for c in CROSS_CELLS]
    common = sorted(set(fb._run_feature_names(cells[0])).intersection(*[set(fb._run_feature_names(c)) for c in cells[1:]]))
    if len(common) < ctx.n_cols:
        raise HarnessError(f"cross_sectional：兩格共同 raw 欄 {len(common)} < 規模 {ctx.n_cols}（資料不足）")
    names = common[:ctx.n_cols]
    cr = _load_script("icperf_t02_correctness", "scripts/icperf_correctness_receipt.py")
    out = cr._child_cross({"cells": cells, "feature_filter": {"include_features": names},
                           "timeframe": cells[0]["timeframe"], "_work": str(ctx.work)})
    cross_df = out["cross_df"]
    return {"input_cols": ctx.n_cols, "rows": int(len(cross_df)), "symbols": len(CROSS_CELLS),
            "timestamps": int(cross_df.index.get_level_values(0).nunique()), "requested_columns": names,
            "survivors": None}


def _run_icfirst_post_generation(ctx: RunContext) -> Dict[str, Any]:
    """SPEC v5.51 (c)：以 `icperf_freeze_baseline.gen-icfirst-raw` 之 A 格 raw run 與其生成結果 metadata（含 `output_window`
    五鍵、config_hash；`icfirst_raw_record`）重建 IC-first ctx（`ic_first_context.begin_context`＋`complete_context`，同
    `run_ic_first` :2844-2848、:2879），於本次工作目錄之 run 複本（post-generation 會寫 processed／ic_selected，不寫回持久根）
    呼叫 `FeatureFactory._run_ic_first_post_generation`（判準檔 A 格 generation 之 ic_engine_config、ic_threshold、
    label_horizon、cleanup_raw）。

    規模：raw run 只有一種欄數（`feature_count`）。以欄子集建 500／1000／2000 欄輸入須先證子集後之 manifest 身分
    （`artifacts.raw.groups`／`total_features`／`content_sha256`／`numeric_fingerprint`；群組為整檔 parquet，逐欄子集須重寫
    群組檔）——可行路徑＝經產品寫出端 `FeatureStorage.write_raw`（`feature_storage.py:705`，身分由產品計算）重寫子集，未施工、
    未實跑驗證 ⇒ `scale` ≠ `feature_count` 一律 HarnessError（不以他物代替）；`scale`＝`feature_count` 之實跑供「post-generation
    可讀、ctx 可建」之驗證（SPEC v5.51 (c) 第一步）。"""
    import shutil

    import pandas as pd

    from momentum.Analysis.ic_engine import ICEngine
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering import ic_first_context as icc
    from momentum.FeatureEngineering.feature_factory import FeatureGenerationResult
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    fb = _fb()
    try:
        rec = fb.icfirst_raw_record()
    except fb.FreezeError as exc:
        raise HarnessError(f"icfirst_post_generation：{exc}") from exc
    n_raw = int(rec["feature_count"])
    if ctx.n_cols != n_raw:
        raise HarnessError(f"icfirst_post_generation：raw run 只有 {n_raw} 欄一種規模；{ctx.n_cols} 欄之子集須經產品寫出端重寫並"
                           "先證 manifest 身分（SPEC v5.51 (c)；未施工）——不以他物代替")
    nfb = _load_script("icperf_t02_numview_freeze_baseline", "scripts/numview_freeze_baseline.py")
    gen_def = rec["generation"]
    label_horizon = str(gen_def["label_horizon"])
    # 寫入隔離同 `_child_ic_first`（`_isolated`：設定檔連結、registry、CGSA、cwd、tempdir、d* 快取導向本次工作目錄）
    with nfb._isolated(ctx.work / "icfirst", {}) as froot:
        src_run = Path(rec["features_root"]) / rec["symbol"] / rec["timeframe"] / rec["config_hash"]
        shutil.copytree(src_run, Path(froot) / rec["symbol"] / rec["timeframe"] / rec["config_hash"], symlinks=True)
        factory = create_feature_factory(cache_dir=str(rec["kline_cache_dir"]),
                                         validate_continuity=bool(rec["validate_continuity"]))
        factory._storage = FeatureStorage(str(froot))
        config = factory._resolve_config(rec["payload"])
        partial = icc.begin_context(symbol=rec["symbol"], timeframe=rec["timeframe"], training=rec["training"],
                                    start=rec["start"], end=rec["end"], selection_window=None, split_id=None,
                                    label_spec={"kind": "close_forward_return", "horizon": label_horizon})
        full = icc.complete_context(partial, rec["generation_metadata"])
        generation = FeatureGenerationResult(
            features_df=pd.DataFrame(index=pd.DatetimeIndex(rec["features_index"])), labels_df=pd.DataFrame(),
            metadata=dict(rec["generation_metadata"]), feature_count=n_raw, generation_time=0.0, layer_counts={},
            config_used={}, compute_warnings=list(rec.get("compute_warnings") or []))
        out = factory._run_ic_first_post_generation(
            full, config, generation, label=None, ic_engine=ICEngine(dict(gen_def["ic_engine_config"])),
            feature_reader=FeatureReader(str(froot)), storage=factory._storage, ic_threshold=gen_def["ic_threshold"],
            allow_partial_ic=False, label_horizon=label_horizon, cleanup_raw=False, compute_warnings=[],
            start=time.time(), persist=True)
    selected = int((out.metadata or {}).get("selected_count") or 0)
    return {"input_cols": n_raw, "rows": len(rec["features_index"]), "survivors": selected,
            "requested_columns": None, "raw_record": _rel(Path(fb.REPO) / fb.ICFIRST_RAW_ROOT / fb.ICFIRST_RAW_RECORD),
            "ctx_complete": bool(full.complete)}


def _tail_rows(v: Any, n_src: int, rows: int) -> Any:
    """存檔參數之末 `rows` 列：首維＝來源列數 `n_src` 之 DataFrame／Series／ndarray 取末 `rows` 列，其餘原樣。"""
    shape = getattr(v, "shape", None)
    if not shape or int(shape[0]) != int(n_src):
        return v
    return v.iloc[-rows:] if hasattr(v, "iloc") else v[-rows:]


def cell_capture(ctx: RunContext, name: str) -> Dict[str, Any]:
    """直接呼叫格之存檔真實輸入：cols 軸＝C 格 `stage_inputs/<N>/`；rows 軸＝L 格 `stage_inputs/L<cols>_rows<R>/`（由
    ic_page_long rows 軸寫出）。`CELL_ROW_SCALES` 所列之格（短序列分支）之 rows 軸＝最小列長之 L 格存檔取末 R 列（R ≤ 該存檔
    列數，否則 HarnessError）。"""
    if ctx.axis != "rows" or ctx.run_id not in CELL_ROW_SCALES:
        return load_capture(ctx.stage_dir, name)
    base = ctx.out_root / "stage_inputs" / ctx.stage_tag(ROW_AXIS_SCALES[0])
    cap = load_capture(base, name)
    frames = [a for a in list(cap["args"]) + list(cap["kwargs"].values()) if hasattr(a, "shape") and len(a.shape) >= 1]
    if not frames:
        raise HarnessError(f"{ctx.run_id}：存檔 {name} 無列軸參數，無法取末 {ctx.n_rows} 列")
    n_src = int(frames[0].shape[0])
    if int(ctx.n_rows or 0) > n_src:
        raise HarnessError(f"{ctx.run_id}：rows {ctx.n_rows} > 存檔列數 {n_src}（資料不足）")
    rows = int(ctx.n_rows or 0)
    return {**cap, "args": tuple(_tail_rows(a, n_src, rows) for a in cap["args"]),
            "kwargs": {k: _tail_rows(v, n_src, rows) for k, v in cap["kwargs"].items()},
            "provenance": {**dict(cap.get("provenance") or {}), "tail_rows": rows, "source_rows": n_src}}


def _engine_cell(ctx: RunContext, name: str, method_name: str, **override: Any) -> Any:
    cap = cell_capture(ctx, name)
    obj = cap["self"]
    return _bind_call(getattr(type(obj), method_name), obj, cap, **override), cap


def _cell_rolling(method: str) -> Callable[[RunContext], Dict[str, Any]]:
    def run(ctx: RunContext) -> Dict[str, Any]:
        _, cap = _engine_cell(ctx, "rolling_ic", "compute_rolling_ic", method=method)
        return _cell_facts(ctx, cap)
    return run


def _cell_facts(ctx: RunContext, cap: Mapping[str, Any], frame: Any = None) -> Dict[str, Any]:
    f = frame if frame is not None else next((a for a in cap["args"] if hasattr(a, "shape") and len(a.shape) == 2), None)
    return {"input_cols": ctx.n_cols, "rows": int(f.shape[0]) if f is not None else 0,
            "cell_input_cols": int(f.shape[1]) if f is not None else 0, "requested_columns": None,
            "capture_provenance": cap.get("provenance")}


def _cell_redundancy(method: str) -> Callable[[RunContext], Dict[str, Any]]:
    def run(ctx: RunContext) -> Dict[str, Any]:
        _, cap = _engine_cell(ctx, "redundancy_filter", "filter", method=method)
        return {**_cell_facts(ctx, cap), "survivors": None}
    return run


def _cell_diversification(ctx: RunContext) -> Dict[str, Any]:
    cap = cell_capture(ctx, "redundancy_filter")
    meta_cap = cell_capture(ctx, "diversification_metrics")
    rf = copy.deepcopy(cap["self"])
    rf._div_enabled = True
    sig = inspect.signature(type(rf).filter)
    ba = sig.bind(rf, *cap["args"], **cap["kwargs"])
    features, ic_scores = ba.arguments["features_df"], ba.arguments["ic_scores"]
    filtered, _log = type(rf).filter(*ba.args, **ba.kwargs)
    msig = inspect.signature(type(rf).compute_diversification_metrics)
    mba = msig.bind(meta_cap["self"], *meta_cap["args"], **meta_cap["kwargs"])
    metadata = mba.arguments["metadata"]
    rf.apply_diversification_constraint(features, list(filtered.columns), list(features.columns), ic_scores, metadata)
    return {**_cell_facts(ctx, cap), "survivors": int(filtered.shape[1])}


def _cell_kmeans(ctx: RunContext) -> Dict[str, Any]:
    cap = cell_capture(ctx, "grouped_ic")
    eng = cap["self"]
    sig = inspect.signature(type(eng).compute_grouped_ic)
    ba = sig.bind(eng, *cap["args"], **cap["kwargs"])
    config = dict(ba.arguments.get("config") or {})
    config["regime_method"] = "kmeans"
    _bind_call(type(eng).compute_grouped_ic, eng, cap, config=config)
    return _cell_facts(ctx, cap)


def _cell_preprocess(fit_mode: str, winsor_method: Optional[str] = None) -> Callable[[RunContext], Dict[str, Any]]:
    def run(ctx: RunContext) -> Dict[str, Any]:
        cap = cell_capture(ctx, "preprocess")
        dp = copy.deepcopy(cap["self"])
        if winsor_method is not None:
            w = (dp._config or {}).get("winsorization")
            if not isinstance(w, dict) or "method" not in w:
                raise HarnessError("DataPreprocessor._config 無 winsorization.method（存檔設定形狀與預期不符）")
            w["method"] = winsor_method
        _bind_call(type(dp).preprocess, dp, cap, fit_mode=fit_mode, fit_mask=None, progress=ctx.rec.progress)
        facts = _cell_facts(ctx, cap)
        if fit_mode == "pit_expanding" and winsor_method is None:
            facts["percentile_short_series"] = facts["rows"] <= 512  # data_preprocessor.py:464
        return facts
    return run


def _cell_standardize(ctx: RunContext) -> Dict[str, Any]:
    cap = cell_capture(ctx, "preprocess")
    res = cap.get("result")
    df = res[0] if isinstance(res, tuple) else res
    if df is None or not hasattr(df, "shape"):
        raise HarnessError("preprocess 存檔無第 1 段輸出（result）")
    dp = copy.deepcopy(cap["self"])
    type(dp).standardize(dp, df, method="time_series_zscore", fit_mode="pit_expanding")
    return _cell_facts(ctx, cap, frame=df)


def _cell_vectorized(ctx: RunContext) -> Dict[str, Any]:
    import numpy as np

    cap = cell_capture(ctx, "compute_ic")
    eng = cap["self"]
    ba = inspect.signature(type(eng).compute_ic).bind(eng, *cap["args"], **cap["kwargs"])
    features, label = ba.arguments["features_df"], ba.arguments["label"]
    method = ba.arguments.get("method", "spearman")
    rows = np.isfinite(label.reindex(features.index).to_numpy(dtype=float))
    f = features.loc[rows]
    keep = [c for c in f.columns if np.isfinite(f[c].to_numpy(dtype=float)).all()]
    if not keep:
        raise HarnessError("vectorized_ic_no_missing：標籤有限列上無全有限欄（資料不足）")
    lab = label.reindex(features.index)[rows]
    if eng._has_missing(f[keep], lab):
        raise HarnessError("vectorized_ic_no_missing：篩後仍有缺值（_has_missing 為 True）")
    type(eng).compute_ic(eng, f[keep], lab, method)
    return {**_cell_facts(ctx, cap, frame=f[keep]), "method": method}


RUNNERS: Dict[str, Callable[[RunContext], Dict[str, Any]]] = {
    "ic_page_default": _run_ic_page_default,
    "ic_page_long": _run_ic_page_default,
    "deep_analysis": _run_deep_analysis,
    "deep_analysis_long": _run_deep_analysis,
    "post_ic_transform": _run_post_ic_transform,
    "event_import": _run_event_import,
    "event_study": _run_event_study,
    "cross_sectional": _run_cross_sectional,
    "icfirst_post_generation": _run_icfirst_post_generation,
    "rolling_kendall": _cell_rolling("kendall"),
    "rolling_pearson": _cell_rolling("pearson"),
    "redundancy_hierarchical": _cell_redundancy("hierarchical"),
    "redundancy_vif": _cell_redundancy("vif"),
    "redundancy_diversification": _cell_diversification,
    "regime_kmeans": _cell_kmeans,
    "fit_mode_pit_expanding": _cell_preprocess("pit_expanding"),
    "winsor_mad_pit": _cell_preprocess("pit_expanding", "mad"),
    "standardize_tszscore_pit": _cell_standardize,
    "vectorized_ic_no_missing": _cell_vectorized,
}


# ── 單一實跑（scale_probe 每點啟動之行程） ──────────────────────────────────────────────────────────────


_FOOTPRINT_RE = re.compile(r"Physical footprint \(peak\):\s*([0-9.]+)\s*([KMGT]?)B?", re.IGNORECASE)
_FOOTPRINT_NOW_RE = re.compile(r"Physical footprint:\s*([0-9.]+)\s*([KMGT]?)B?", re.IGNORECASE)


def parse_footprint(text: str) -> Optional[int]:
    """`sample` 輸出之 Physical footprint (peak)（無 peak 行退回當下值）⇒ bytes；K/M/G/T 以 1024 換算。"""
    m = _FOOTPRINT_RE.search(text) or _FOOTPRINT_NOW_RE.search(text)
    if not m:
        return None
    mult = {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4}[m.group(2).upper()]
    return int(float(m.group(1)) * mult)


def self_peak_footprint(work: Path) -> Optional[int]:
    """本行程之 Physical footprint (peak)（macOS `sample <pid> 1 -f`，同 `scripts/measure_ic_footprint.sh` 之工具；核心
    維護峰值，故於行程結束前取一次即得全程峰值；不設時間上限、不終止任何行程）。不可用 ⇒ None。"""
    out = work / "footprint.sample.txt"
    try:
        subprocess.run(["sample", str(os.getpid()), "1", "-f", str(out)], capture_output=True, check=False)
        return parse_footprint(out.read_text(encoding="utf-8", errors="replace")) if out.is_file() else None
    except (OSError, ValueError):
        return None


def _git_head() -> Optional[str]:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=False)
        return res.stdout.strip() or None
    except OSError:
        return None


def _rel(p: Path) -> str:
    try:
        return Path(p).resolve().relative_to(REPO).as_posix()
    except ValueError:
        return str(p)


def run_one(run_id: str, *, axis: str, scale: int, records_dir: Path, inventory_path: Path = INVENTORY_PATH,
            out_root: Optional[Path] = None, argv: Optional[Sequence[str]] = None) -> Path:
    """一個規模點之一次實跑：重綁清冊全部 measure=true 入口 ⇒ 執行 `RUNNERS[run_id]` ⇒ 寫逐入口記錄；回記錄檔路徑。
    工作目錄（cwd／TMPDIR）＝`<out-root>/work/<path_run_id>/`（唯讀輸入以 symlink 引入；產品之 cwd 相對寫出落此）。"""
    if run_id not in RUNNERS:
        raise HarnessError(f"未知路徑／格：{run_id}（{sorted(RUNNERS)}）")
    if axis not in RUN_AXES[run_id]:
        raise HarnessError(f"{run_id} 不支援 {axis} 軸（可用：{RUN_AXES[run_id]}）")
    started_wall = time.time()
    # 工作根一律解析為絕對路徑（其後 chdir 至隔離 cwd，相對路徑會落入 cwd 之下）
    root = Path(out_root) if out_root is not None else REPO / TASK02_ROOT
    root = (root if root.is_absolute() else REPO / root).resolve()
    records_dir = Path(records_dir) if Path(records_dir).is_absolute() else REPO / records_dir
    inventory_path = Path(inventory_path) if Path(inventory_path).is_absolute() else REPO / inventory_path
    path_run_id = f"{run_id}.{axis}{int(scale)}.{time.strftime('%Y%m%dT%H%M%S')}.{os.getpid()}"
    work = root / "work" / path_run_id
    iso = work / "iso"
    iso.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(iso)  # 產品之 tempfile 寫入落本次工作目錄（不放系統暫存）
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    fb = _fb()
    # 事件儲存根：event_import 讀 repo 之 data_cache/events（服務預設為絕對路徑，同 §G (7) 凍結）；event_study 用 work/events
    cwd = fb._prepare_cwd(work / "cwd")
    inventory = load_inventory(inventory_path)
    measured = [e for e in inventory["entries"] if e.get("measure")]
    keyed = {e["id"] for e in measured if e.get("loop") in KEYED_LOOPS}
    head = _git_head()
    rec = Recorder(keyed=keyed, context=f"{run_id}|{axis}|{scale}")
    ctx = RunContext(run_id, axis, scale, root, work, rec, head)
    stage_dir: Optional[Path] = None
    if (run_id, axis) in CAPTURE_RUNS:
        stage_dir = ctx.stage_dir
        stage_input_card(root / "stage_inputs")
        prov = {"path_run_id": path_run_id, "head": head, "axis": axis, "scale": int(scale), "run_id": run_id,
                "source": "L" if ctx.long else "C"}
        rec.captures = {eid: _capture_writer(stage_dir, name, with_result, prov)
                        for eid, (name, with_result) in CAPTURES.items()}
    os.chdir(cwd)
    targets = resolve_targets(e["id"] for e in measured)
    binding = rebind_all({eid: t.func for eid, t in targets.items()}, rec)
    rec.start()
    try:
        facts = RUNNERS[run_id](ctx)
    finally:
        rec.stop()
        wall = time.time() - started_wall
    import resource

    ru = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    record = {"schema": RECORD_SCHEMA, "path_run_id": path_run_id, "run_id": run_id,
              "kind": "path" if run_id in PATHS else "cell", "axis": axis, "scale": int(scale),
              # 交接 h5 子集之來源格（IC 頁／深度分析路徑與直接呼叫格；其餘路徑讀各自之 run，見 facts）
              "handoff_source": (LONG_CELL_ID if ctx.long else "C") if run_id in SUBSET_RUNS or run_id in CELLS else None,
              "row_window_override": ROW_AXIS_WINDOW_OVERRIDE if axis == "rows" and run_id in PATHS else None,
              "argv": list(sys.argv[1:] if argv is None else argv), "head": head,
              "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(started_wall)),
              "wall_seconds": wall, "harness_overhead_seconds": rec.overhead_seconds,
              "self_ru_maxrss_bytes": ru if sys.platform == "darwin" else ru * 1024,
              "peak_footprint_bytes": self_peak_footprint(work), "footprint_tool": FOOTPRINT_TOOL,
              "facts": facts, "stage_inputs": _rel(stage_dir) if stage_dir else None,
              "inventory": _rel(inventory_path), "rebind_counts": binding.counts,
              "progress_times": [round(t, 6) for t in rec.progress_times], "entries": rec.entries_json()}
    out_dir = Path(records_dir) / run_id / f"{axis}-{int(scale)}"
    if not out_dir.is_absolute():
        out_dir = REPO / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{path_run_id}.json"
    # SPEC v5.51 (i)：收據引用之紀錄入版控、不覆寫（同名已存在 ⇒ FileExistsError，不改寫既有紀錄）
    with open(out, "x", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, allow_nan=True, default=str))
    binding.restore()
    print(f"[icperf-t02] 已寫 {_rel(out)}（{sum(1 for v in record['entries'].values() if v['calls'])} 入口有呼叫）", flush=True)
    return out


# ── 量測收據組裝（純函式；`icperf_freeze_baseline.measure_inventory` 呼叫，測試以合成記錄驗） ─────────────────


def median_record(records: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """同一規模點之多次實跑（scale_probe 單次 < 60 秒者跑 3 次取中位數）中，牆鐘秒為中位數者（偶數取較小之中位）。"""
    ordered = sorted(records, key=lambda r: (float(r["wall_seconds"]), str(r["path_run_id"])))
    return ordered[(len(ordered) - 1) // 2]


def _stage_cols(e: Mapping[str, Any], er: Mapping[str, Any], facts: Mapping[str, Any], input_cols: int) -> Tuple[int, str]:
    """實際進該入口之欄數：觀測之 2D 輸入欄數（> 1）＞受算欄名數（輸入鍵入口）＞深度分析／IC 後轉換之倖存數＞路徑輸入欄數；
    上限 input_cols（跨標的等另附標籤欄之 frame 以特徵欄計）。回 (值, 來源)。"""
    cap = max(int(input_cols), 0)
    if int(er.get("max_cols") or 0) > 1:
        return min(int(er["max_cols"]), cap), "observed_2d_input"
    if er.get("computed_columns"):
        return min(len(er["computed_columns"]), cap), "computed_columns"
    if e.get("stage") in ("deep_analysis", "post_ic_transform") and isinstance(facts.get("survivors"), int):
        return min(int(facts["survivors"]), cap), "path_survivors"
    return cap, "path_input_cols"


def scale_vector(e: Mapping[str, Any], er: Mapping[str, Any], facts: Mapping[str, Any], input_cols: int,
                 stage_cols: int) -> Dict[str, int]:
    """點之 scale_vector（鍵＝清冊該入口之 scale_vector）：rows＝該入口觀測之最大首維（無則路徑列數）、survivors＝路徑倖存數、
    survivor_pairs＝survivors·(survivors−1)/2、events／symbols／timestamps＝路徑事實。缺值 ⇒ KeyError（收據拒收缺軸）。"""
    survivors = facts.get("survivors")
    vals: Dict[str, Optional[int]] = {
        "rows": int(er.get("max_rows") or 0) or facts.get("rows"),
        "input_cols": int(input_cols), "stage_cols": int(stage_cols),
        "survivors": survivors if isinstance(survivors, int) else None,
        "survivor_pairs": survivors * (survivors - 1) // 2 if isinstance(survivors, int) else None,
        "events": facts.get("events"), "symbols": facts.get("symbols"), "timestamps": facts.get("timestamps"),
    }
    out: Dict[str, int] = {}
    for k in e["scale_vector"]:
        v = vals.get(k)
        if not isinstance(v, int) or isinstance(v, bool):
            raise KeyError(f"{e['id']}：scale_vector.{k} 無量測值（路徑事實 {sorted(facts)}）")
        out[k] = int(v)
    return out


def _superlinear_by_code(function: str) -> bool:
    """碼層複雜度（清冊 unit_axis.function）是否含超線性因子：次方（^）、對數（log）、兩規模軸之乘積以外之配對數。"""
    f = function.split("（")[0]
    return bool(re.search(r"\^|log|survivor_pairs", f))


#: 碼層下限之單次掃描形式：unit_axis.function 之首項（「（」前）只含規模軸之乘積（無次方、對數、窗長等額外因子）
_SINGLE_PASS_RE = re.compile(r"^\s*[A-Za-z_]+(\s*\*\s*[A-Za-z_]+)*\s*$")
#: 規模軸之字面（清冊 unit_axis.function 所用；W、B、L、P 等窗長／重抽樣次數非規模軸）
_SCALE_TOKENS = {"rows", "input_cols", "stage_cols", "survivors", "events", "n_events", "symbols", "n_symbols", "timestamps"}
CRITERION2_STATUSES = ("decided", "pending_prototype")


def criterion2_order_gap(function: str) -> str:
    """碼層：現行複雜度（清冊 unit_axis.function 之首項）相對單次掃描下限之階數差——"same_order"（各規模軸之積，與下限
    同階，差距只可能為常數倍）或 "superlinear"（含次方、對數、窗長／重抽樣等額外因子）。只作 Phase 1 原型之優先序，不作
    判準②之 10 倍實證（SPEC v5.51 (f)）。"""
    head = str(function).split("（")[0]
    tokens = set(re.findall(r"[A-Za-z_]+", head))
    single = bool(_SINGLE_PASS_RE.match(head)) and not _superlinear_by_code(head) and tokens <= _SCALE_TOKENS
    return "same_order" if single else "superlinear"


def criterion2(entry: Mapping[str, Any]) -> Dict[str, Any]:
    """判準②（單位成本 ≥ 可達下限 × 10；SPEC Task 0.2 :104、v5.51 (f)）：
    ① 有原型下限（`lower_bound_seconds_per_unit` > 0）⇒ 數值比 `unit_seconds ≥ 10 × 下限`（basis prototype_lower_bound）；
    ② 無原型而實測每單位秒數 < 10 × `CRITERION2_FLOOR_SECONDS_PER_UNIT`（任何實作之每單位秒數皆 ≥ 此硬體下限）⇒ 必未達
    「下限 × 10」⇒ False（basis hardware_floor，可碼層斷定）；③ 其餘無原型者 ⇒ result None、status pending_prototype（碼層
    分析不足以斷定是否 ≥ 10 倍——漸近階數不作 10 倍實證；列 Phase 1 原型補量），evidence 附現行複雜度、碼層下限與階數差。
    不得固定 False。"""
    lb = entry.get("lower_bound_seconds_per_unit")
    us = entry.get("unit_seconds")
    func = str((entry.get("unit_axis") or {}).get("function") or "")
    ev = {"unit_seconds": us, "units": entry.get("units"), "lower_bound": lb, "function": func,
          "lower_bound_analysis": entry.get("lower_bound_analysis"), "order_gap": criterion2_order_gap(func)}
    if isinstance(lb, (int, float)) and lb > 0 and isinstance(us, (int, float)):
        return {"result": bool(us >= 10 * lb), "status": "decided", "basis": "prototype_lower_bound", "evidence": ev}
    if isinstance(us, (int, float)) and us < 10 * CRITERION2_FLOOR_SECONDS_PER_UNIT:
        return {"result": False, "status": "decided",
                "basis": f"hardware_floor（實測每單位 {us:.3g} 秒 < 10 × 硬體下限 {CRITERION2_FLOOR_SECONDS_PER_UNIT:g} 秒）",
                "evidence": {**ev, "floor_seconds_per_unit": CRITERION2_FLOOR_SECONDS_PER_UNIT}}
    return {"result": None, "status": "pending_prototype",
            "basis": "pending_prototype（無原型；碼層分析不足以斷定單位成本是否 ≥ 下限 × 10——漸近階數不作 10 倍實證；"
                     "列 Phase 1 以向量化／numba 小原型同資料同規模實測補量）",
            "evidence": ev}


def evaluate_criteria(entry: Mapping[str, Any], scale_probe: Any) -> Dict[str, Dict[str, Any]]:
    """判準①–⑤（SPEC Task 0.2 固定規則；①門檻引 scale_probe 之 SUPERLINEAR_EXPONENT／MIN_R2）：`entry` 為組裝中之量測
    記錄（fit、extrapolation_unreliable、unit_axis、complexity_analysis、lower_bound_*、evidence）。回
    {"1".."5": {"result": bool, "basis": str, "evidence": ...}}。"""
    fit = entry["fit"]
    ev = entry.get("evidence") or {}
    out: Dict[str, Dict[str, Any]] = {}
    r2 = fit.get("r2")
    if entry["extrapolation_unreliable"] or r2 is None or r2 < scale_probe.MIN_R2:
        out["1"] = {"result": _superlinear_by_code(str(entry["unit_axis"]["function"])), "basis": "complexity_analysis",
                    "evidence": entry.get("complexity_analysis")}
    else:
        out["1"] = {"result": bool(fit["exponent"] > scale_probe.SUPERLINEAR_EXPONENT), "basis": "power_fit",
                    "evidence": {"exponent": fit["exponent"], "r2": r2}}
    out["2"] = criterion2(entry)
    keys = ev.get("keys")
    if keys is None:
        out["3"] = {"result": False, "basis": "非 PIT／逐欄入口：不記輸入鍵（清冊 loop 非 per_bar／per_column）", "evidence": None}
    else:
        out["3"] = {"result": bool(keys["duplicate_keys"] > 0), "basis": "call_keys（同一輸入鍵呼叫次數 > 1）",
                    "evidence": keys}
    un = ev.get("unrequested")
    if un is None:
        out["4"] = {"result": False, "basis": "無帶 feature_filter 之實跑紀錄含本入口之受算欄（無請求外之欄可量）",
                    "evidence": None}
    else:
        out["4"] = {"result": bool(un["n_unrequested"] > 0), "basis": "computed_columns − feature_filter 請求集合",
                    "evidence": un}
    gap = ev.get("progress_gap") or {}
    out["5"] = {"result": bool(float(gap.get("max_gap_seconds", 0.0)) > PROGRESS_GAP_SECONDS),
                "basis": f"入口呼叫區間內最長無 progress_callback 間隔 > {PROGRESS_GAP_SECONDS:g} 秒", "evidence": gap}
    return out


def _opportunities(eid: str, crit: Mapping[str, Mapping[str, Any]], points: Sequence[Mapping[str, Any]],
                   ram_bytes: Optional[int]) -> Dict[str, Dict[str, Any]]:
    """四項機會欄：time＝任一判準成立 ⇒ planned（依據＝成立之判準），否則 none（依據＝各判準不成立之實測）；memory＝峰值
    footprint 逾 RAM×0.5 ⇒ planned，否則 none（依據＝實測峰值）；precision／file_size＝planned（SPEC :104 各段改後四項並列比較，
    改前盤點不改值，依據為該規定）。"""
    hit = [k for k, c in crit.items() if c["result"] is True]
    pending = [k for k, c in crit.items() if c.get("status") == "pending_prototype"]
    blank = {"before": None, "after": None, "downstream": None, "user_ruling": None}
    if hit or pending:
        why = "；".join(x for x in (f"判準 {'、'.join(hit)} 成立" if hit else "",
                                    f"判準 {'、'.join(pending)} 待 Phase 1 原型補量（v5.51 (f)）" if pending else "") if x)
        time_o = {"status": "planned", "evidence": f"{why}（見 criteria）", **blank}
    else:
        time_o = {"status": "none", "evidence": "判準①–⑤ 皆不成立（見 criteria 之 evidence）", **blank}
    fps = [int(p["peak_footprint_bytes"]) for p in points if isinstance(p.get("peak_footprint_bytes"), int)]
    over = bool(ram_bytes and fps and max(fps) > ram_bytes * 0.5)
    mem_o = {"status": "planned" if over else "none",
             "evidence": f"所屬路徑峰值 Physical footprint {max(fps) if fps else None} bytes"
                         f"{' > ' if over else ' ≤ '}RAM×0.5（{ram_bytes}）", **blank}
    rule = "SPEC Task 0.2 :104：各段改後以記憶體／精確度／計算時間／檔案大小四項並列比較（改前盤點不改值，施工時判定）"
    return {"time": time_o, "memory": mem_o, "precision": {"status": "planned", "evidence": rule, **blank},
            "file_size": {"status": "planned", "evidence": rule, **blank}}


def projected_2000_seconds(points: Sequence[Mapping[str, Any]]) -> float:
    """以 500／1000 兩點推估 2000 欄（線性外推與兩點冪次外推取大；同 test_icperf_gate boundary_19 之算式）。"""
    by = {p["input_cols"]: float(p["seconds"]) for p in points}
    s5, s10 = by[500], by[1000]
    linear = 2.0 * s10 - s5
    power = s10 * s10 / s5 if s5 > 0 and s10 > 0 else linear
    return max(linear, power)


#: 各軸點之 x 鍵（收據點之欄名）與擬合之 x（cols 軸以實際進段欄數 stage_cols 為準，SPEC Task 0.2）
AXIS_X_KEY = {"cols": "input_cols", "rows": "rows", "events": "events"}
AXIS_FIT_KEY = {"cols": "stage_cols", "rows": "rows", "events": "events"}


def fit_points(points: Sequence[Mapping[str, Any]], axis: str = "cols") -> List[Dict[str, Any]]:
    """逐入口擬合之輸入：x＝`AXIS_FIT_KEY[axis]`（cols 軸＝實際進段欄數 stage_cols；events 軸＝事件數，v5.51 (d)；rows
    軸＝列數）、秒數、路徑級峰值 RSS。"""
    key = AXIS_FIT_KEY[axis]
    return [{"scale": p[key], "unit": axis, "seconds": p["seconds"], "peak_rss_bytes": p["peak_rss_bytes"]}
            for p in points]


def unit_cost(e: Mapping[str, Any], points: Sequence[Mapping[str, Any]], axis: str) -> Tuple[Optional[float], Optional[int]]:
    """每單位秒數（判準②；SPEC :104「每欄（或每格）秒數」）：取主軸最大點，單位數＝清冊 unit_axis.axes 於該點 scale_vector
    之值之積（缺或 0 之軸以 1 計）；無點或秒數非有限 ⇒ (None, None)。"""
    if not points:
        return None, None
    p = max(points, key=lambda q: q[AXIS_X_KEY[axis]])
    units = 1
    for a in (e.get("unit_axis") or {}).get("axes") or []:
        v = (p.get("scale_vector") or {}).get(a)
        units *= int(v) if isinstance(v, int) and v > 0 else 1
    sec = float(p["seconds"])
    return (sec / units if units > 0 and sec == sec else None), units


def total_projected_seconds(runs: Mapping[Tuple[str, str], Mapping[str, Any]]) -> float:
    """收據頂層合計推估（SPEC v5.51 (g)）：全部路徑實跑之 scale_probe 收據逐點 seconds × runs 之和（量測全程之牆鐘秒）。"""
    return float(sum(float(q.get("seconds") or 0.0) * max(int(q.get("runs") or 1), 1)
                     for run in runs.values() for q in (run.get("receipt") or {}).get("points") or []))


def _point(e: Mapping[str, Any], q: Mapping[str, Any], run: Mapping[str, Any], axis: str,
           problems: List[str]) -> Optional[Dict[str, Any]]:
    eid = e["id"]
    scale = int(q["scale"])
    recs = list((run.get("records") or {}).get(scale) or [])
    if len(recs) != int(q.get("runs") or 0):
        problems.append(f"{eid}：{run['receipt_path']} scale={scale} 之實跑 {q.get('runs')} 次，逐入口記錄 {len(recs)} 份")
        return None
    chosen = median_record(recs)
    er = (chosen.get("entries") or {}).get(eid)
    if er is None or int(er.get("calls") or 0) - int(er.get("raised") or 0) < 1:
        problems.append(f"{eid}：{chosen.get('path_run_id')} 呼叫次數 0（包裝未生效或入口不在該路徑；不得以 0 呼叫充作量測）")
        return None
    facts = chosen.get("facts") or {}
    if (axis == "rows" or chosen.get("run_id") in LONG_RUNS) and "split_applied" in facts \
            and facts["split_applied"] is not True:
        # v5.51 (a)：L 格之 IC 頁／深度分析實跑須走樣本外切分（預檢之實跑對證；退回全樣本即非所量之分支）
        problems.append(f"{eid}：{chosen.get('path_run_id')} 未走樣本外切分（split_applied={facts['split_applied']!r}）")
        return None
    input_cols = scale if axis == "cols" else int(facts.get("input_cols") or 0)
    stage_cols, source = _stage_cols(e, er, facts, input_cols)
    try:
        sv = scale_vector(e, er, facts, input_cols, stage_cols)
    except KeyError as exc:
        problems.append(str(exc.args[0]))
        return None
    # SPEC v5.51 (h)：Physical footprint 取自同 path_run_id 之 harness 紀錄（受測行程結束前 `sample <pid>`）；行程樹峰值 RSS
    # 取自 scale_probe 收據該點
    fp = chosen.get("peak_footprint_bytes")
    if not (isinstance(fp, int) and fp > 0):
        problems.append(f"{eid}：{chosen.get('path_run_id')} 之紀錄缺 Physical footprint")
        return None
    p: Dict[str, Any] = {"input_cols": input_cols, "stage_cols": stage_cols, "stage_cols_source": source,
                         "seconds": float(er["seconds"]), "calls": int(er["calls"]),
                         "peak_rss_bytes": int(q["peak_rss_bytes"]), "peak_footprint_bytes": int(fp),
                         "rss_source": f"scale_probe:{run['receipt_path']}",
                         "footprint_source": f"harness_record:{chosen['path_run_id']}",
                         "entry_peak_rss_bytes": er.get("peak_rss_bytes"), "scale_vector": sv,
                         "scale_probe_receipt": run["receipt_path"], "path_run_id": chosen["path_run_id"],
                         "path_run_ids": sorted(str(r["path_run_id"]) for r in recs),
                         "record_path": chosen.get("_record_path"),
                         # SPEC v5.51 (i)：紀錄之來源與大小（`_task02_records` 讀檔時記；合成記錄無檔 ⇒ None）
                         "record_bytes": chosen.get("_record_bytes"), "record_sha256": chosen.get("_record_sha256")}
    if axis == "rows":
        p["rows"] = scale
        p["scale_vector"] = {**sv, **({"rows": scale} if "rows" in sv else {})}
    if axis == "events":
        # SPEC v5.51 (d)：事件數軸之點以事件數為 x（不要求欄數軸）
        p["events"] = scale
        p["scale_vector"] = {**sv, **({"events": scale} if "events" in sv else {})}
    return p


def _evidence(e: Mapping[str, Any], chosen: Sequence[Mapping[str, Any]], all_records: Sequence[Mapping[str, Any]]
              ) -> Dict[str, Any]:
    eid = e["id"]
    ers = [(r, r["entries"][eid]) for r in chosen if eid in (r.get("entries") or {})]
    keyed = [x for x in ers if x[1].get("keyed")]
    keys = None
    if keyed:
        keys = {"duplicate_keys": max(int(er.get("duplicate_keys") or 0) for _, er in keyed),
                "max_key_count": max(int(er.get("max_key_count") or 0) for _, er in keyed),
                "by_path_run": {r["path_run_id"]: {"n_keys": er.get("n_keys"), "duplicate_keys": er.get("duplicate_keys"),
                                                   "examples": (er.get("duplicate_examples") or [])[:5]}
                                for r, er in keyed}}
    un = None
    for r in all_records:
        req = r.get("facts", {}).get("requested_columns")
        er = (r.get("entries") or {}).get(eid)
        if req is None or er is None or er.get("computed_columns") is None:
            continue
        extra = sorted(set(er["computed_columns"]) - set(req))
        cur = {"path_run_id": r["path_run_id"], "n_requested": len(req), "n_computed": len(er["computed_columns"]),
               "n_unrequested": len(extra), "examples": extra[:10]}
        if un is None or cur["n_unrequested"] > un["n_unrequested"]:
            un = cur
    gaps = []
    for r, er in ers:
        g = max_progress_gap(er.get("long_intervals") or [], r.get("progress_times") or []) if er.get("long_intervals") \
            else float(er.get("max_call_seconds") or 0.0)
        gaps.append({"path_run_id": r["path_run_id"], "max_gap_seconds": g,
                     "basis": "intervals" if er.get("long_intervals") else "upper_bound_max_call_seconds"})
    worst = max(gaps, key=lambda g: g["max_gap_seconds"]) if gaps else {"max_gap_seconds": 0.0}
    return {"keys": keys, "unrequested": un, "progress_gap": {**worst, "by_path_run": gaps}}


def assemble_scale_receipt(inventory: Mapping[str, Any], runs: Mapping[Tuple[str, str], Mapping[str, Any]], *,
                           head: str, scale_probe: Any, budget_seconds: float, sample_interval_seconds: float,
                           chunk_cap: Mapping[str, Any], ram_bytes: Optional[int] = None,
                           two_point_seconds: float = 600.0, require_rows: bool = False,
                           records_root: Optional[str] = None) -> Dict[str, Any]:
    """組 `<日期>-icperf-scale-before.json`（SPEC Task 0.2 v5.50 (e)、v5.51 (d)(f)(g)(h)(i)）。`runs`＝{(run_id, axis):
    {"probe": {"cmd", "data", "config"}, "receipt_path": <repo 相對>, "receipt": <scale_probe 收據>, "records": {scale:
    [逐入口記錄（含 `_record_path`／`_record_bytes`／`_record_sha256`）...]}}}。每一 measure=true 入口依 `branch_cell` 取其
    主軸實跑（`primary_axis`：event_study＝events 軸，其餘 cols 軸），清冊 input_axes 含 rows 者另取 `ROW_AXIS_RUN[cell]` 之
    rows 軸實跑組 row_points（L 格，v5.51 (a)；`require_rows` 而缺 ⇒ 問題）：每點 seconds＝同 path_run_id（多次實跑取牆鐘
    中位數者）之逐入口秒數、peak_rss_bytes＝scale_probe 該點、footprint＝同 path_run_id 之 harness 紀錄（v5.51 (h)）；
    fit＝`scale_probe.fit(fit_points(points, 主軸), full)` 重算。任一問題（漏量、呼叫 0、缺軸、缺 footprint）⇒
    AssemblyError（逐條）。兩點例外（v5.51 (g)）：只在頂層合計推估 `total_projected_seconds(runs)` 逾 `budget_seconds` 時，
    cols 軸 500／1000 推估 2000 欄逾 `two_point_seconds` 之入口方收兩點（2,000 欄實測點移 `excluded_points`，不刪資料）；
    未逾預算者三點皆收。判準②依 `criterion2`（v5.51 (f)），待判者列頂層 `pending_prototype`。"""
    problems: List[str] = []
    all_records = [r for run in runs.values() for recs in (run.get("records") or {}).values() for r in recs]
    total = total_projected_seconds(runs)
    budget_exceeded = bool(total > float(budget_seconds))
    entries: Dict[str, Any] = {}
    for e in inventory.get("entries") or []:
        if not e.get("measure"):
            continue
        eid, cell = e["id"], e.get("branch_cell")
        axis = primary_axis(cell) if cell else "cols"
        run = runs.get((cell, axis)) if cell else None
        if run is None:
            problems.append(f"{eid}：所屬格 {cell!r} 無 {axis} 軸量測")
            continue
        pts = [p for q in sorted(run["receipt"]["points"], key=lambda q: int(q["scale"]))
               if (p := _point(e, q, run, axis, problems)) is not None]
        if len(pts) != len(run["receipt"]["points"]):
            continue
        row_run = None
        row_pts = None
        if "rows" in (e.get("input_axes") or []):
            row_run = runs.get((ROW_AXIS_RUN.get(cell, ""), "rows"))
            if row_run is None and require_rows:
                problems.append(f"{eid}：清冊 input_axes 含 rows，所屬格 {cell!r} 無 rows 軸實跑"
                                f"（ROW_AXIS_RUN 對應 {ROW_AXIS_RUN.get(cell)!r}）")
        if row_run is not None:
            row_pts = [p for q in sorted(row_run["receipt"]["points"], key=lambda q: int(q["scale"]))
                       if (p := _point(e, q, row_run, "rows", problems)) is not None]
        chosen = [r for run_ in (run, row_run) if run_ for recs in run_["records"].values() for r in [median_record(recs)]]
        full = float((run["receipt"].get("projection") or {}).get("scale")
                     or max(p[AXIS_X_KEY[axis]] for p in pts))
        m: Dict[str, Any] = {"coverage_path_id": e["coverage_path_id"], "unit_axis": e["unit_axis"],
                             "branch_cell": cell, "path": cell, "axis": axis, "probe": run["probe"],
                             "row_probe": row_run["probe"] if row_run else None,
                             "row_path": ROW_AXIS_RUN.get(cell) if row_run else None}
        excluded = []
        two_point = None
        if axis == "cols" and budget_exceeded and {500, 1000} <= {p["input_cols"] for p in pts}:
            proj = projected_2000_seconds(pts)
            if proj > two_point_seconds:
                two_point = {"projected_2000_seconds": proj, "total_projected_seconds": total,
                             "budget_seconds": float(budget_seconds),
                             "note": "SPEC v5.51 (g)：收據合計推估逾 budget_seconds，且 500／1000 兩點推估 2000 欄逾 10 分鐘 "
                                     "⇒ 只收兩點"}
                excluded = [p for p in pts if p["input_cols"] == 2000]
                pts = [p for p in pts if p["input_cols"] != 2000]
        fit = scale_probe.fit(fit_points(pts, axis), full)
        row_fit = None
        if row_pts and len(row_pts) >= 2:
            rf = scale_probe.fit(fit_points(row_pts, "rows"), float(max(p["rows"] for p in row_pts)))
            row_fit = {"exponent": rf["fit"]["exponent"], "r2": rf["fit"]["r2"],
                       "extrapolation_unreliable": rf["extrapolation_unreliable"]}
        func = str(e["unit_axis"]["function"])
        unit_seconds, units = unit_cost(e, pts, axis)
        m.update({"points": pts, "row_points": row_pts, "excluded_points": excluded, "two_point_exception": two_point,
                  "fit_axis": AXIS_FIT_KEY[axis],
                  "fit": {"exponent": fit["fit"]["exponent"], "r2": fit["fit"]["r2"]}, "fit_full_scale": full,
                  "fit_reasons": fit["reasons"], "extrapolation_unreliable": fit["extrapolation_unreliable"],
                  "row_fit": row_fit,
                  "projected_seconds": float(sum(p["seconds"] for p in pts)), "reduction": None,
                  "complexity_analysis": f"碼層複雜度（清冊 unit_axis.function，讀碼 {e.get('evidence')}）：{func}",
                  "unit_seconds": unit_seconds, "units": units,
                  "lower_bound_seconds_per_unit": None,
                  "lower_bound_analysis": f"未建向量化／numba 小原型；碼層下限＝{'·'.join(e['unit_axis']['axes'])} 之單次"
                                          f"掃描（每單位常數時間），現行 {func}（階數差 {criterion2_order_gap(func)}）",
                  "evidence": _evidence(e, chosen, all_records)})
        crit = evaluate_criteria(m, scale_probe)
        m["criteria"] = crit
        m["opportunities"] = _opportunities(eid, crit, pts, ram_bytes)
        entries[eid] = m
    if problems:
        raise AssemblyError(problems)
    rec_files = {str(r["_record_path"]): r.get("_record_bytes") for r in all_records if r.get("_record_path")}
    return {"schema": RECEIPT_SCHEMA, "head": head, "budget_seconds": budget_seconds,
            "total_projected_seconds": total, "budget_exceeded": budget_exceeded,
            "total_projected_basis": "全部路徑實跑之 scale_probe 收據逐點 seconds × runs 之和（SPEC v5.51 (g)）",
            "pending_prototype": sorted(eid for eid, m in entries.items()
                                        if m["criteria"]["2"].get("status") == "pending_prototype"),
            "records": {"root": records_root, "source": "scripts/icperf_scale_harness.py run（scale_probe 啟動之受測行程寫出）",
                        "n_files": len(rec_files),
                        "total_bytes": sum(v for v in rec_files.values() if isinstance(v, int))},
            "meter": {"tool": "scripts/scale_probe.py", "rss_scope": "process_tree",
                      "sample_interval_seconds": sample_interval_seconds,
                      "entry_timer": "scripts/icperf_scale_harness.py（行程內重綁全部引用；perf_counter inclusive）",
                      "footprint": {"tool": FOOTPRINT_TOOL, "sampling": "until_target_exit",
                                    "terminate_target_on_exceed": False, "source": "harness_record_same_path_run_id",
                                    "how": "同 path_run_id 之受測行程結束前 `sample <pid> 1` 取 Physical footprint (peak)"
                                           "（核心維護之全程峰值；寫於該行程之逐入口紀錄）；行程樹 RSS 取自 scale_probe 收據"}},
            "chunk_cap": dict(chunk_cap),
            "runs": {f"{k[0]}:{k[1]}": {"receipt": v["receipt_path"], "probe": v["probe"]} for k, v in runs.items()},
            "entries": entries}


# ── CLI ───────────────────────────────────────────────────────────────────────────────────────────────


def main(argv: Optional[Sequence[str]] = None) -> int:
    args_in = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(prog="icperf_scale_harness.py", description="ICPERF Task 0.2 行程內逐入口計時（見模組說明）")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("run", help="一個規模點之一次實跑（由 scale_probe 啟動）")
    p.add_argument("run_id", choices=sorted(RUNNERS))
    p.add_argument("--axis", default="cols", choices=("cols", "rows", "events"))
    p.add_argument("--scale", type=int, required=True)
    p.add_argument("--records-dir", type=Path, required=True)
    p.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    p.add_argument("--out-root", type=Path, default=None)
    sub.add_parser("list", help="列出路徑與直接呼叫格")
    p = sub.add_parser("plan", help="清冊 measure=true 入口之 branch_cell 對照")
    p.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    p = sub.add_parser("precheck-rows", help="v5.51 (a)：列數軸列長之樣本外切分秒級碼層預檢（不跑 IC、不讀資料檔）")
    p.add_argument("--scale", type=int, action="append", default=None, help=f"列長（可多次；預設 {ROW_AXIS_SCALES}）")
    args = ap.parse_args(args_in)
    if args.cmd == "precheck-rows":
        res = row_axis_precheck(tuple(args.scale) if args.scale else ROW_AXIS_SCALES)
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0 if res["ok"] else 1
    if args.cmd == "run":
        try:
            run_one(args.run_id, axis=args.axis, scale=args.scale, records_dir=args.records_dir,
                    inventory_path=args.inventory, out_root=args.out_root, argv=args_in)
        except HarnessError as exc:
            print(f"HarnessError：{exc}", file=sys.stderr)
            return 1
        return 0
    if args.cmd == "list":
        print(json.dumps({"paths": PATHS, "cells": CELLS, "axes": RUN_AXES}, ensure_ascii=False, indent=1))
        return 0
    if args.cmd == "plan":
        plan = coverage_plan(load_inventory(args.inventory))
        print(json.dumps({k: len(v) for k, v in sorted(plan.items())}, ensure_ascii=False, indent=1))
        return 0 if "__uncovered__" not in plan else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

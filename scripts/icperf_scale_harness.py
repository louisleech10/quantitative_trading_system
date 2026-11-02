"""ICPERF Task 0.2（docs/ICPERF_SPEC.md Task 0.2，v5.50 (a)–(f) 為準）：規模盤點之行程內逐入口計時——路徑實跑＋直接呼叫格。

每一規模點對每一路徑（或直接呼叫格）實跑**一個行程**，外層一律由 `scripts/scale_probe.py` 啟動（行程樹 RSS、身分、冪次擬合；
`{scale}` 代入規模），行程內以「重綁全部引用」（v5.50 (a)）把清冊 `scripts/icperf_path_inventory.json` 每一 `measure=true`
入口換成同一計數／計時 wrapper，逐入口記錄寫 `<records-dir>/<run_id>/<axis>-<scale>/<path_run_id>.json`。不改產品碼。

用法（重型；由 `scripts/icperf_freeze_baseline.py measure` 經 scale_probe 啟動，不單獨前景跑全規模）：
  venv/bin/python scripts/icperf_scale_harness.py run <run_id> --axis cols --scale {scale} --records-dir handoffs/run_receipts/icperf_task02_records/<session>/<attempt>
  venv/bin/python scripts/icperf_scale_harness.py list                 # 列出路徑與直接呼叫格及其所涵蓋之清冊入口數
  venv/bin/python scripts/icperf_scale_harness.py plan                 # 清冊 measure=true 入口 ⇒ branch_cell 對照與未涵蓋者
  venv/bin/python scripts/icperf_scale_harness.py precheck-rows        # v5.51 (a)：列數軸列長之樣本外切分秒級預檢
  venv/bin/python scripts/icperf_scale_harness.py coverage             # v5.52 (b)：清冊對實跑排程（主軸＋第二軸）之涵蓋
  venv/bin/python scripts/icperf_scale_harness.py prepare post-ic-rows|icfirst-subsets   # v5.52 (b)(c)：量測前之存檔輸入
  venv/bin/python scripts/icperf_scale_harness.py precheck-xsec-long   # v5.53 (c1)：兩長歷史格之重疊、有效列數、預設切分可達
  venv/bin/python scripts/icperf_scale_harness.py event-bar-scales     # v5.53 (c0)：事件 K 線根數軸之三點
  run 之選項：--axis cols|rows|events|timestamps（預設 cols；rows＝固定 `ROW_AXIS_COLS` 欄、子集列數截為末 {scale} 列〔事件
  路徑＝K 線根數〕；events＝事件數；timestamps＝跨標的末 {scale} 個時點）
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
- `icfirst_post_generation`：cols 軸＝基準 raw run 經產品寫出端 `FeatureStorage.write_raw` 重寫之 N 欄子集 run（`prepare
  icfirst-subsets`；`verify_icfirst_subset` 驗 manifest 身分、實際欄數、讀取端可讀與逐欄值）；rows 軸＝三種窗長之生成
  （`icperf_freeze_baseline.py gen-icfirst-raw --rows R`）各取 `ROW_AXIS_COLS` 欄（SPEC v5.52 (b)(c)）。
- SPEC v5.52：(a) 子集與存檔輸入之沿用比對來源身分 sidecar（`ensure_subset`、`STAGE_IDENTITY_FILE`）；(b) 各路徑第二軸
  （`entry_runs`／`schedule_runs`／`schedule_coverage`：post_ic_transform rows〔`prepare post-ic-rows` 之 L 格存檔任務〕、
  cross_sectional timestamps、event_import events〔隔離儲存根之前 {scale} 筆〕、IC-first rows），每一軸實跑驗實際輸入點數
  ＝宣告規模（`actual_scale`，不等 ⇒ HarnessError）；`coverage` 子命令列涵蓋。
- SPEC v5.53（code review r64）：(c0) 事件路徑之 K 線根數軸——清冊 unit_axis.axes 含 rows 之事件入口（8 個，含
  `evaluate_all_bars` rows*n_boot）不再記 fixed_axes，排 (event_import|event_study, rows)：全部事件固定、K 線讀
  `<out-root>/event_bars/rows<R>/` 之隔離截短複本（`prepare_event_bars`：同一 symbol／週期之末 R 根；三點
  `event_bar_scales`），行程內 `bars_source._DEFAULT_CACHE` 改指複本（`redirect_event_bars`，觀測產品實際讀取之根數＝
  actual_scale），不改真實快取；只含 rows 之入口主軸＝rows。(c1) `cross_sectional_long`（`VARIANT_RUNS`）：L 格＋同一生成
  定義之 ETH 4h 長歷史格之預設切分分支；生成前秒級預檢 `precheck-xsec-long`（`xsec_long_precheck`）。
- SPEC v5.55（code review r66）：(d) `ic_page_relaxed`＝非預設門檻分支（L 格 run 之 IC 頁服務路徑，只覆寫第 5 段門檻
  `RELAXED_THRESHOLDS`；預設路徑第 5 段零通過而 0 呼叫之 8 入口歸之；存 R 群組存檔供冗餘三格、存 IC 任務供 survivors 軸）；
  (e) post_ic_transform 主軸＝survivors（`post_ic_survivor_scales`；子命令 `survivor-scales`）；(f) 深度分析 0 呼叫之 5 入口
  歸讀 D 群組存檔之直接呼叫格（`orthogonalize_pca`／`exposure_beta_neutral`／`param_sensitivity_family`／
  `param_sensitivity_pearson`）；(g2) 事件數軸三點由 `event_axis_precheck`（子命令 `precheck-events`）選出；(h) 三點固定全跑。
- SPEC v5.56（code review r67）：(j) `event_axis_precheck` 之兩類計數經產品 `count_binary_classes_in_rows`，三點另以產品實跑
  （`event_point_product_check`）斷言 effective mode＝imported_binary 且二元三入口 calls ≥ 1（Task 0.4 ㊵ 修正前判不成立）；
  (k) 冗餘格 rows 軸固定最小 rows 點之第 6 段輸入欄集合（`redundancy_stage_capture`；`RedundancyFilter.filter`／
  `compute_correlation_matrix` 之 rows 軸改 `redundancy_greedy_rows`，`ROW_AXIS_ENTRY_RUN`），組裝斷言欄集合身分相同，紀錄頂層
  `threshold_branch` 取事實之實際分支（`record_threshold_branch`）；(l) 冗餘格 cols 軸＝stage_cols 設計點
  （`REDUNDANCY_STAGE_COLS_SCALES`，RL500 第 6 段真實輸入之 seeded 巢狀子集）；(m) harness 請求選欄改 seeded 巢狀
  （`seeded_columns`；凍結項 `small_request` 不改），路徑事實記指標家族分佈；(n) 事件數軸＝Task 0.2 專用較密事件批
  （`EVENT_AXIS_BREAKOUT_BARS`）之等距抽樣（`event_axis_subset`）；(o) 參數敏感度家族數軸＝變體實跑
  （`param_sensitivity_families*`、families 軸，`PARAM_FAMILY_SCALES`）；(p) IC 後轉換之 `_transform_chunked` 以
  `FFACT_L65_CHUNK_SIZE` 之同實跑探針量（`post_ic_chunked_probe`、`Recorder.restricted`）。
- SPEC v5.57（code review r68）：(q) 事件數軸（`event_axis_precheck` 與 event_import events 軸）走非預設門檻之產品完整路徑
  （`relaxed_event_request`：只覆寫 p_value_max），紀錄門檻分支、實際門檻與第 5 段實值（`event_threshold_facts`）、二元三入口
  呼叫；event_study 無第 5 段門檻消費點，維持預設；(r) `redundancy_vif` rows 軸固定 stage_cols 中點之 64 欄 seeded 設計點
  （`REDUNDANCY_ROWS_DESIGN_COLS`；組裝斷言與 cols 軸 64 欄點同欄集合），量測環境不另設 BLAS 執行緒（路徑事實記實值
  `blas_thread_facts`），VIF 兩入口之時間機會併入收據（`KNOWN_TIME_OPPORTUNITIES`）；(s) 清冊
  `_transform_single_optimized_df_core` measure=false（IC 頁不可達）；(t) harness 請求之 seeded 選欄（`_limited_request`）
  涵蓋 event_import 各軸與 post-ic-rows，凍結項 `small_request` 不改。
- SPEC v5.58（code review r69）：(x) 清冊 `mann_whitney_table`（與 inclusive 成本隨第 5 段倖存數變之
  `_run_binary_permutation_and_negative_control`；`block_permutation_table` 原即含）之 unit_axis 含 survivors；event_import 各軸
  紀錄 survivors＝第 5 段倖存數、二元收據與 `post_stage5_claim`（`event_stage5_facts`；倖存 0 或負對照未實算 ⇒ 該點不得宣稱
  後續統計有實值）；組裝之 events 軸只擬合確實隨事件數變之入口（`events_fit_exclusion`）；固定倖存集合之直接呼叫格
  `MW_FIXED_CELL`（`ISOLATION_RUNS`；讀 event_import events 軸各點之存檔 `EVENT_MW_DIR/E<n>/`、`--ref-scale` 點之第 5 段倖存欄）
  隔離單次入口成本。(y) 清冊 `_transform_single_optimized_df_core` 之 ic_page／ic_first＝false（旗標之消費者只有 schema 檢查）。
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
#: 跨標的路徑之請求覆寫（同 `icperf_correctness_receipt.REQUESTS["X.cross_sectional"]` 之退回分支）：兩格各 500 列，產品
#: 全域切分（`ic_filter_orchestrator.py:1003-1034` `_build_cross_sectional_global_split`：oos_test_size 0.2、purge＝horizon、
#: 每標的測試段 ≥ min_test_rows 131〔`ic_config_schema.py:461-463`〕）於 500 時點之每標的測試段 ≤ 500−400−purge < 131 ⇒ 預設
#: 切分必拋 InvalidInputError；故跨標的兩格之量測一律明列關切分（不以預設失敗後退回；SPEC v5.39 ⑩ 同法）
XSEC_OVERRIDE_EXTRA: Dict[str, Any] = {"ic_train_test_split": False}
#: SPEC v5.52 (b)：跨標的之第二軸＝時點數（截短時間跨度：兩格各取末 T 個共同時點）；兩格各 500 列 ⇒ 三點 250／375／500
XSEC_TIMESTAMP_SCALES = (250, 375, 500)
#: SPEC v5.52 (b)(c)：IC-first post-generation 列軸之三種窗長（輸出段根數）：500＝A 格生成定義之 output_bars（沿用 cols 軸之
#: raw run）、1,000／2,000 各一次生成（`icperf_freeze_baseline.py gen-icfirst-raw --rows R`）；各窗長之 raw run 經
#: `FeatureStorage.write_raw` 取同一 `ROW_AXIS_COLS` 欄巢狀子集（列軸內欄數不變）
ICFIRST_ROW_SCALES = (500, 1000, 2000)
#: SPEC v5.52 (a)：子集與各段存檔輸入之身分 sidecar（來源內容 sha256、seed、欄數、列長；不同 ⇒ 重建，不只憑檔案存在）
SUBSET_IDENTITY_FILE = "subset_identity.json"
STAGE_IDENTITY_FILE = "stage_identity.json"
SUBSET_IDENTITY_SCHEMA = "icperf-t02-subset-identity/1"

#: 路徑實跑（v5.49）：id ⇒ 說明
PATHS: Dict[str, str] = {
    "ic_page_default": "C 格 N 欄巢狀子集＋IC 頁預設請求 analyze（第 0–7 段）；存直接呼叫格之各段真實輸入",
    "ic_page_long": "L 格（4h 2,000 列，樣本外切分成立）交接 h5 之 N 欄巢狀子集＋IC 頁預設請求 analyze（樣本外分支入口）；"
                    "rows 軸＝固定 ROW_AXIS_COLS 欄、末 R 列、ROW_AXIS_WINDOW_OVERRIDE（存直接呼叫格之列數軸真實輸入）",
    "ic_page_relaxed": "SPEC v5.55 (d)：**非預設門檻分支**——L 格 run feature_filter N 欄經服務 start_analysis（IC 頁請求，只覆寫"
                       "第 5 段門檻 RELAXED_THRESHOLDS）；負責預設路徑因第 5 段零通過而 0 呼叫之第 6／6b／7 段入口；存第 6 段"
                       "真實輸入（stage_inputs/RL<N>/）供冗餘直接呼叫格、存 IC 任務（POST_IC_SURVIVORS_DIR）供 IC 後轉換 "
                       "survivors 軸；rows 軸＝固定 ROW_AXIS_COLS 欄、run 載入後取末 R 列、ROW_AXIS_WINDOW_OVERRIDE",
    "deep_analysis": "同 ic_page_default 之 analyze 後同一 analyzer 續跑深度分析全部模組",
    "deep_analysis_long": "同 ic_page_long 之 rows 軸 analyze 後同一 analyzer 續跑深度分析全部模組（深度分析之列數軸）",
    "post_ic_transform": "SPEC v5.55 (e)：主軸 survivors＝ic_page_relaxed 各 cols 點存下之真實 IC 任務（POST_IC_SURVIVORS_DIR）"
                         "直接呼叫 _apply_transforms_sync（rank／zscore／gaussian；倖存欄＝該任務之實際倖存者，不重跑 IC）；"
                         "rows 軸＝L 格存檔之 IC 任務（prepare post-ic-rows）於末 R 列直接呼叫 _apply_transforms_sync",
    "event_import": "L 格 run feature_filter N 欄＋§G (7) 事件匯入批（event_import_run）；events 軸＝固定 ROW_AXIS_COLS 欄、"
                    "隔離儲存根之前 {scale} 筆事件；rows 軸（v5.53 (c0)）＝固定 ROW_AXIS_COLS 欄、全部事件、K 線讀隔離截短"
                    "複本之末 {scale} 根",
    "event_study": "事件研究頁：隔離儲存根之 import_records＋analyze（events 軸＝前 {scale} 筆事件；rows 軸〔v5.53 (c0)〕＝"
                   "全部事件、K 線讀隔離截短複本之末 {scale} 根）",
    "cross_sectional": "A 格 BTCUSDT／SOLUSDT 兩 run 共同 N 欄之跨標的 analyze_cross_sectional（關切分，XSEC_OVERRIDE_EXTRA）；"
                       "timestamps 軸＝固定 ROW_AXIS_COLS 欄、末 T 個時點",
    "cross_sectional_long": "SPEC v5.53 (c1)：L 格＋同一生成定義之 ETH 4h 長歷史格（XSEC_LONG_CELLS）共同 N 欄之跨標的 "
                            "analyze_cross_sectional，預設請求（不關切分）⇒ 量全域時間切分分支（cross_sectional 之變體，"
                            "VARIANT_RUNS；不取代其關切分之兩軸）",
    "icfirst_post_generation": "IC-first 之 _run_ic_first_post_generation 整段與子步驟：cols 軸＝一次生成之 raw run 經 "
                               "FeatureStorage.write_raw 重寫之 N 欄子集 run（prepare icfirst-subsets）；rows 軸＝窗長 R 之"
                               "生成經同法取 ROW_AXIS_COLS 欄",
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
    # SPEC v5.55 (f)：深度分析預設設定下 0 呼叫之入口——讀深度分析路徑存之真實輸入（stage_inputs/D<N>/、DL<cols>_rows<R>/）
    "orthogonalize_pca": "存檔正交化輸入（gram_schmidt 之 factors）＋同一 FactorOrthogonalizer，pca_orthogonalize"
                         "（factor_orthogonalization.method=pca 之分支，ic_filter_orchestrator.py:3680-3682）",
    "exposure_beta_neutral": "存檔中和輸入（neutralize_factor_matrix 之 factor_values、market_proxy）＋同一 FactorExposureAnalyzer，"
                             "mode=beta_neutral（factor_exposure_analyzer.py:117-118）",
    "param_sensitivity_family": "存檔參數敏感度輸入（batch_analyze 之 self／labels／metadata／方法／方向；入選欄）＋同一路徑第 1 段"
                                "輸出中產品 detect_feature_families 所得之最小完整家族（≥ min_family_size）併入後 batch_analyze"
                                "（同請求方法；parameter_sensitivity_analyzer.py:178-181）",
    "param_sensitivity_pearson": "同上，method=pearson（非 spearman 之 _rolling_corr 分支，parameter_sensitivity_analyzer.py:273-276）",
    # SPEC v5.56 (k)：`RedundancyFilter.filter`（產品預設 method，greedy）之 rows 軸——固定最小 rows 點之第 6 段輸入欄集合、只變
    # 列數（ic_page_relaxed rows 路徑之第 6 段欄數隨列數變，不作該入口之 rows 軸）
    "redundancy_greedy_rows": "存檔第 6 段冗餘輸入（RL<cols>_rows<R>：固定 RL<cols>_rows<最小 R> 之欄集合、值取該 R 點第 1 段"
                              "輸出之測試段列、IC 分數同 R 點）＋同一 RedundancyFilter，產品預設 method（rows 軸專用）",
    # SPEC v5.56 (o)：參數敏感度家族數軸（主排程外之變體實跑，VARIANT_RUNS）
    "param_sensitivity_families": "存檔參數敏感度輸入（DL<cols>_rows<L 格全長> 之 batch_analyze 參數）＋L 格 2,000 欄第 1 段輸出"
                                  "（ic_page_long cols 2000 之存檔 L2000/preprocess）中產品 detect_feature_families 之 ≥3 員"
                                  "家族取 F 族、每族 3 員（只含家族成員欄）＋同一分析器 batch_analyze（同請求方法）",
    "param_sensitivity_families_pearson": "同上，method=pearson（_rolling_corr 分支之家族數軸）",
    # SPEC v5.58 (x)（code review r69 群集 C）：mann_whitney_table 之單次入口成本——端到端（event_import events 軸）之呼叫數隨
    # 第 5 段倖存數變（smoke_v557 741／1／925），另以固定倖存集合隔離（`ISOLATION_RUNS`；不取代端到端之兩軸）
    "mann_whitney_fixed_survivors": "存檔事件數軸真實輸入（event_import events 軸各點 mann_whitney_table 首次呼叫之 features／y／"
                                    "min_class_n，`EVENT_MW_DIR/E<n>/`）限於固定倖存集合（--ref-scale 點之第 5 段倖存欄）＋"
                                    "mann_whitney_table 重複 MW_FIXED_CALLS 次（events 軸；每點同欄集合、只變事件）",
}
#: SPEC v5.55 (d)：非預設門檻分支之第 5 段門檻覆寫（深合併入 IC 頁請求之 `config_override.thresholds`；其餘同 IC 頁預設）。
#: 選擇依據（碼證）：A／C 格 1h 500 列之 ICIR 恆非有限（ICIR 窗 63 經 12h／1h 換算為 756 > 500 列，`ic_engine.py:1869-1881`；
#: 2026-11-01 A 格 120 欄請求之 summary_table.icir 全 null）而 `_passes_threshold` 對 NaN 一律不通過（`ic_filter_orchestrator.py:
#: 6806-6813`、ICIR 閘 `:6047-6050` 於全域路徑恆生效）⇒ C 格任何門檻值皆無法使第 6 段有輸入 ⇒ 資料格改 L 格（4h 2,000 列，
#: ICIR 有限）。L 格 120 欄預設請求之第 5 段剔除以 p 閘為主（ic_mean 12／icir 8／p_value 95／monotonicity 1，通過 4；2026-11-01
#: correctness 擷取之 filter log）；p 閘＝`p_value_adj ≤ alpha_effective`（`:6052-6057`）、alpha_effective＝`p_value_max`
#: （`:5249-5258`），BH q 值與 alpha 無關（`statistical_validator.py:183` `del alpha`）⇒ 只覆寫 `p_value_max`＝1.0（p 值值域上界：
#: 任一有限 q 皆過 p 閘），其餘五道門檻（ic_mean／icir／勝率／單調性／覆蓋率）維持預設——第 5 段通過數＝真實資料過其餘門檻者
RELAXED_THRESHOLDS: Dict[str, Any] = {"p_value_max": 1.0}
#: SPEC v5.55 (e)：IC 後轉換 survivors 軸之存檔輸入（ic_page_relaxed cols 點之 IC 任務）目錄；子目錄＝`RL<N>`
POST_IC_SURVIVORS_DIR = "stage_inputs/post_ic_survivors"
#: 存檔目錄之群組前綴（路徑 ⇒ 前綴）：""＝IC 頁預設（C 格 cols／L 格 rows）、"D"＝深度分析、"R"＝非預設門檻分支
STAGE_GROUP: Dict[str, str] = {"ic_page_default": "", "ic_page_long": "", "deep_analysis": "D", "deep_analysis_long": "D",
                               "ic_page_relaxed": "R"}
#: 各群組之寫出路徑：(cols 軸路徑, rows 軸路徑)
GROUP_WRITERS: Dict[str, Tuple[str, str]] = {"": ("ic_page_default", "ic_page_long"),
                                             "D": ("deep_analysis", "deep_analysis_long"),
                                             "R": ("ic_page_relaxed", "ic_page_relaxed")}
#: 直接呼叫格所讀存檔之群組（未列 ⇒ ""）：冗餘三格讀非預設門檻分支（預設路徑第 6 段 0 輸入，無存檔）；深度四格讀深度分析
CELL_GROUP: Dict[str, str] = {"redundancy_hierarchical": "R", "redundancy_vif": "R", "redundancy_diversification": "R",
                              "orthogonalize_pca": "D", "exposure_beta_neutral": "D", "param_sensitivity_family": "D",
                              "param_sensitivity_pearson": "D", "redundancy_greedy_rows": "R",
                              "param_sensitivity_families": "D", "param_sensitivity_families_pearson": "D"}
#: 預設路徑實跑時存之各段真實輸入（入口 id ⇒ (存檔名, 是否另存回傳值)）；只存第一次呼叫
CAPTURES: Dict[str, Tuple[str, bool]] = {
    "momentum.Analysis.data_preprocessor:DataPreprocessor.preprocess": ("preprocess", True),
    "momentum.Analysis.ic_engine:ICEngine.compute_ic": ("compute_ic", False),
    "momentum.Analysis.ic_engine:ICEngine.compute_rolling_ic": ("rolling_ic", False),
    "momentum.Analysis.ic_engine:ICEngine.compute_grouped_ic": ("grouped_ic", False),
    "momentum.Analysis.redundancy_filter:RedundancyFilter.filter": ("redundancy_filter", False),
    "momentum.Analysis.redundancy_filter:RedundancyFilter.compute_diversification_metrics": ("diversification_metrics", False),
    # SPEC v5.55 (f)：深度分析模組之真實輸入（深度分析路徑寫 D 群組存檔）
    "momentum.Analysis.factor_orthogonalizer:FactorOrthogonalizer.gram_schmidt": ("orthogonalize", False),
    "momentum.Analysis.factor_exposure_analyzer:FactorExposureAnalyzer.neutralize_factor_matrix": ("neutralize", False),
    "momentum.Analysis.parameter_sensitivity_analyzer:ParameterSensitivityAnalyzer.batch_analyze": ("param_sensitivity",
                                                                                                   False),
}
#: 各格所需之存檔
CELL_CAPTURES: Dict[str, Tuple[str, ...]] = {
    "rolling_kendall": ("rolling_ic",), "rolling_pearson": ("rolling_ic",),
    "redundancy_hierarchical": ("redundancy_filter",), "redundancy_vif": ("redundancy_filter",),
    "redundancy_diversification": ("redundancy_filter", "diversification_metrics"),
    "regime_kmeans": ("grouped_ic",), "fit_mode_pit_expanding": ("preprocess",),
    "winsor_mad_pit": ("preprocess",), "standardize_tszscore_pit": ("preprocess",),
    "vectorized_ic_no_missing": ("compute_ic",),
    "orthogonalize_pca": ("orthogonalize",), "exposure_beta_neutral": ("neutralize",),
    "param_sensitivity_family": ("param_sensitivity", "preprocess"),
    "param_sensitivity_pearson": ("param_sensitivity", "preprocess"),
    "redundancy_greedy_rows": ("redundancy_filter", "preprocess"),
    "param_sensitivity_families": ("param_sensitivity", "preprocess"),
    "param_sensitivity_families_pearson": ("param_sensitivity", "preprocess"),
}
#: SPEC v5.56 (k)(l)：讀非預設門檻分支第 6 段存檔之冗餘格（R 群組）——cols 軸＝stage_cols 設計點（`REDUNDANCY_STAGE_COLS_SCALES`；
#: RL<`REDUNDANCY_STAGE_SOURCE_COLS`> 第 6 段真實輸入之 seeded 巢狀子集）、rows 軸＝固定最小 rows 點之欄集合只變列數
REDUNDANCY_STAGE_CELLS: Tuple[str, ...] = ("redundancy_hierarchical", "redundancy_vif", "redundancy_diversification",
                                           "redundancy_greedy_rows")
#: SPEC v5.56 (l)：stage_cols 三點之來源＝ic_page_relaxed 500 欄點之第 6 段真實輸入（2026-11-01 smoke：187 欄 × 測試段 395 列；
#: seeded 選欄後之實值於 smoke 重量，見 `REDUNDANCY_STAGE_COLS_BASIS`）。不取 cols 2,000 點（第 6 段約 750 欄）：該規模由放寬
#: 門檻造出、非產品預設路徑之規模（預設門檻全規模第 6 段輸入 0–2 欄），屬設計選點而非依牆鐘縮減
REDUNDANCY_STAGE_SOURCE_COLS = 500
REDUNDANCY_STAGE_COLS_SCALES: Tuple[int, ...] = (32, 64, 128)
REDUNDANCY_STAGE_COLS_BASIS = ("三點＝RL500 第 6 段真實輸入（測試段列）之 seeded 巢狀子集之輸入欄數 32／64／128：倍距 2、跨度 4 倍"
                               "（冪次擬合之三點等比）；上限 128 ≤ RL500 第 6 段輸入欄數（不足 ⇒ HarnessError），且 n（測試段 "
                               "395 列）> k 之一般情形（n≈k 之 VIF 退化另入 Task 0.4 ㊷）。2026-11-01 smoke 實測（seeded 選欄之 RL500 "
                               "第 6 段輸入 201 欄 × 395 列；runs/icperf/task02/smoke_v556/records/redundancy_vif/）：vif_filter "
                               "32／64／128 欄 28／451／2,048 秒（_compute_vif_scores 15／36／78 輪），三點皆跑完；hierarchical、"
                               "diversification 三點各 < 3 秒")
#: SPEC v5.57 (r)：rows 軸改固定 seeded 設計點之冗餘格 ⇒ 欄數。`redundancy_vif` rows 三點固定 64 欄＝stage_cols 中點
#: （`REDUNDANCY_STAGE_COLS_SCALES[1]`；RL<`REDUNDANCY_STAGE_SOURCE_COLS`> 第 6 段真實輸入之 `seeded_columns(·, 64)`，與 cols 軸
#: 64 點同一欄集合），欄數成本由 stage_cols 軸量；不量 (k) 之最小 rows 點全部第 6 段輸入（smoke 210 欄，依 stage_cols 曲線
#: 64→451 秒、128→2,048 秒外推約 6 小時）。greedy（redundancy_greedy_rows）／hierarchical／diversification 之 rows 軸維持 (k)
#: 之最小 rows 點全部第 6 段輸入：一軸一變數兩法皆滿足；三格每點 < 3 秒（smoke_v556），無成本理由縮小，且該欄集合＝產品於最小
#: rows 點之實際第 6 段輸入（設計點則為抽樣之子集），每點秒數較大使列數擬合較不受計時雜訊主導；跨入口之可比由收據每點
#: `cell_input_cols`／scale_vector 記明，不靠同欄數
REDUNDANCY_ROWS_DESIGN_COLS: Dict[str, int] = {"redundancy_vif": REDUNDANCY_STAGE_COLS_SCALES[1]}
#: SPEC v5.57 (r)：量測環境不另設 BLAS 執行緒數（量現行碼之實際行為；多執行緒互搶記入機會欄）——冗餘格之路徑事實記此等環境
#: 變數之實值（未設 ⇒ None）與 threadpoolctl 所見之實際執行緒數
BLAS_THREAD_ENV_KEYS: Tuple[str, ...] = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                                         "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")
#: SPEC v5.57 (r)：已由研究實測之時間機會（入口 id ⇒ 依據）——組裝時併入 opportunities.time（planned；判準①候選）
KNOWN_TIME_OPPORTUNITIES: Dict[str, str] = {
    eid: ("多執行緒 BLAS 小矩陣互搶（handoffs/run_receipts/20261101-icperf-vif-study.json assessment.performance_finding："
          "產品 vif_filter 每欄 sklearn LinearRegression 於 OpenBLAS 預設多執行緒，RL500_rows1000 整個逐步過程 4,893.8 秒 vs 限 1 "
          "執行緒 101.9 秒、值差 ≤ 7.3e-11、選欄不變）；Task 0.2 量現行碼不另設執行緒數（SPEC v5.57 (r)），限執行緒改寫排 Phase 2"
          "、以 statsmodels variance_inflation_factor 為 oracle 同條件改前改後對照")
    for eid in ("momentum.Analysis.redundancy_filter:RedundancyFilter.vif_filter",
                "momentum.Analysis.redundancy_filter:RedundancyFilter._compute_vif_scores")}
#: 冗餘格 rows 軸之固定欄集合紀錄鍵（`_cell_facts` 自存檔 provenance 提至路徑事實；組裝斷言 rows 軸各點相同）
COLUMN_SET_KEY = "column_set_sha256"
#: SPEC v5.56 (o)：參數敏感度家族數軸——家族數三點（L 格 2,000 欄第 1 段輸出之 ≥3 員家族；2026-11-01 smoke 名稱樣式計 15 組，
#: `runs/icperf/task02/smoke/inspect_subset_families.py`）、每族成員數、固定列數（L 格全長，DL<cols>_rows2000 之存檔）
PARAM_FAMILY_SCALES: Tuple[int, ...] = (4, 8, 15)
PARAM_FAMILY_MEMBERS = 3
PARAM_FAMILY_SOURCE_COLS = 2000
PARAM_FAMILY_CELLS: Dict[str, str] = {"param_sensitivity_families": "param_sensitivity_family",
                                      "param_sensitivity_families_pearson": "param_sensitivity_pearson"}
#: SPEC v5.55 (f)：參數敏感度兩格只有 rows 軸（主軸＝rows）。碼證：入口成本＝family_size·rows·W·log(W)（清冊 unit_axis；
#: 不含欄數軸），且家族須 ≥ min_family_size（`parameter_sensitivity_analyzer.py:178-181`）——C 格交接 h5 之 100／500／1,000／
#: 2,000 欄巢狀子集（seed 20261027）欄名之名稱樣式家族最大成員數 0／1／1／2（無 ≥ 3 者；L 格 500 欄子集最大 3、≥ 3 者 2 組；
#: 2026-11-01 smoke `runs/icperf/task02/smoke/inspect_subset_families.py` 實查；C 格 D100 存檔以產品 detect_feature_families
#: 實跑亦全為單員）⇒ C 格 cols 軸於真實資料不可達；改以 L 格（deep_analysis_long rows 軸之存檔，500 欄）之列數三點量
PARAM_ROWS_ONLY_CELLS: Tuple[str, ...] = ("param_sensitivity_family", "param_sensitivity_pearson")
#: 各路徑／格可用之軸（v5.51 (a)：IC 頁與深度分析之 rows 軸改由 L 格路徑 `ic_page_long`／`deep_analysis_long` 實跑）。
#: SPEC v5.55 (e)：post_ic_transform 之主軸＝survivors（不再有每點重跑整段 IC 之 cols 軸）
RUN_AXES: Dict[str, Tuple[str, ...]] = {
    **{c: ("rows",) if c in PARAM_ROWS_ONLY_CELLS else ("cols", "rows") for c in CELLS},
    "ic_page_default": ("cols",), "ic_page_long": ("cols", "rows"), "ic_page_relaxed": ("cols", "rows"),
    "deep_analysis": ("cols",), "deep_analysis_long": ("rows",), "post_ic_transform": ("survivors", "rows"),
    "event_import": ("cols", "events", "rows"), "event_study": ("events", "rows"),
    "cross_sectional": ("cols", "timestamps"), "cross_sectional_long": ("cols",),
    "icfirst_post_generation": ("cols", "rows"),
    # SPEC v5.56 (k)(o)：只供第二軸／變體之格
    "redundancy_greedy_rows": ("rows",),
    **{c: ("families",) for c in PARAM_FAMILY_CELLS},
    # SPEC v5.58 (x)：固定倖存集合之 mann_whitney 直接呼叫格只有事件數軸
    "mann_whitney_fixed_survivors": ("events",),
}
#: 主軸非 cols 之路徑（SPEC v5.51 (d)：event_study 只有事件數與 K 線根數兩軸，主軸＝events）
PRIMARY_AXIS: Dict[str, str] = {"event_study": "events", "post_ic_transform": "survivors",
                                **{c: "rows" for c in PARAM_ROWS_ONLY_CELLS}, "redundancy_greedy_rows": "rows",
                                **{c: "families" for c in PARAM_FAMILY_CELLS}, "mann_whitney_fixed_survivors": "events"}
#: SPEC v5.56 (k)：清冊入口級之 rows 軸實跑（優先於所屬格之 `ROW_AXIS_RUN`）——`RedundancyFilter.filter`／
#: `compute_correlation_matrix`（branch_cell＝ic_page_relaxed）之 rows 軸改由 `redundancy_greedy_rows`（固定欄集合、只變列數）
ROW_AXIS_ENTRY_RUN: Dict[str, str] = {
    "momentum.Analysis.redundancy_filter:RedundancyFilter.filter": "redundancy_greedy_rows",
    "momentum.Analysis.redundancy_filter:RedundancyFilter.compute_correlation_matrix": "redundancy_greedy_rows",
}
#: SPEC v5.53 (c0)（code review r64）：事件路徑之 K 線根數軸——清冊 unit_axis.axes 含 rows 之事件入口（K 線根數為成本軸，
#: 如 `evaluate_all_bars` rows*n_boot）所屬格 ⇒ rows 軸實跑之 run_id。實跑於隔離 K 線快取複本（`prepare_event_bars`：同一
#: symbol／週期之末 R 根，`<out-root>/EVENT_BARS_DIR/rows<R>/`），行程內 `bars_source._DEFAULT_CACHE` 指向該複本；不改
#: `data_cache/feature_klines/kline_cache.h5`
EVENT_BARS_RUN: Dict[str, str] = {"event_import": "event_import", "event_study": "event_study"}
EVENT_BARS_DIR = "event_bars"
EVENT_BARS_FILE = "kline_cache.h5"
#: K 線根數軸最小點於最早事件 t0 之前保留之根數（決策偏移 k 之可行域與暖機；`alignment.py:156`、
#: `label_value_from_case.py:420`、`all_bars_eval._is_eligible` 之 i−k≥0）——三點皆含全部事件及其前 EVENT_BARS_PRE 根
EVENT_BARS_PRE = 256
#: SPEC v5.53 (c1)：跨標的長資料之兩格（L 格＋同一生成定義之 ETH 4h 長歷史格，`icperf_freeze_baseline.LONG_CELL_XSEC`；
#: 長歷史檔無 SOLUSDT 4h，夥伴改 ETHUSDT）
XSEC_LONG_CELLS = (LONG_CELL_ID, "L_ETHUSDT_4h_longhist")
#: 主排程以外之變體實跑 (run_id, 軸) ⇒ 其所變之格（branch_cell）：該格每一 measure=true 入口於變體實跑亦須 calls ≥ 1，
#: 收據 `variants` 段（不參與 entry_runs 之主軸／第二軸、不取代原格之量測）
VARIANT_RUNS: Dict[Tuple[str, str], str] = {("cross_sectional_long", "cols"): "cross_sectional",
                                             # SPEC v5.56 (o)：參數敏感度家族數軸（每族 3 員、固定 rows、家族數三點）
                                             **{(c, "families"): base for c, base in PARAM_FAMILY_CELLS.items()}}
#: 變體實跑中須走預設切分者（SPEC v5.53 (c1)；組裝驗 split_applied）
VARIANT_SPLIT_RUNS: Tuple[Tuple[str, str], ...] = (("cross_sectional_long", "cols"),)
ROW_AXIS_RUN.update({"ic_page_default": "ic_page_long", "ic_page_long": "ic_page_long", "ic_page_relaxed": "ic_page_relaxed",
                     "deep_analysis": "deep_analysis_long", "post_ic_transform": "post_ic_transform",
                     "icfirst_post_generation": "icfirst_post_generation", **{c: c for c in CELLS}})
#: SPEC v5.52 (b)：清冊 input_axes 之 rows 由非 rows 名之軸實跑代之者（收據 `row_axis` 明示軸名）——跨標的之列數＝時點數 ×
#: 標的數，以截短時間跨度之時點數為軸
ROW_AXIS_ALIAS: Dict[str, Tuple[str, str]] = {"cross_sectional": ("cross_sectional", "timestamps")}
#: SPEC v5.52 (b)：事件型路徑之事件數軸（清冊 scale_vector 含 events 之入口）：所屬格 ⇒ events 軸實跑之 run_id
EVENT_AXIS_RUN: Dict[str, str] = {"event_import": "event_import", "event_study": "event_study"}
#: 寫直接呼叫格所需存檔之 (路徑, 軸)：cols 軸取 C 格 ic_page_default、rows 軸取 L 格 ic_page_long；SPEC v5.55：非預設門檻
#: 分支兩軸（R 群組）、深度分析兩路徑（D 群組）
CAPTURE_RUNS: Tuple[Tuple[str, str], ...] = (("ic_page_default", "cols"), ("ic_page_long", "rows"),
                                             ("ic_page_relaxed", "cols"), ("ic_page_relaxed", "rows"),
                                             ("deep_analysis", "cols"), ("deep_analysis_long", "rows"),
                                             ("ic_page_long", "cols"))
#: 只存部分存檔之寫出實跑（SPEC v5.56 (o)：ic_page_long cols 只供家族數軸之 L 格 N 欄第 1 段輸出）；未列 ⇒ 全部 CAPTURES
CAPTURE_ONLY: Dict[Tuple[str, str], Tuple[str, ...]] = {("ic_page_long", "cols"): ("preprocess",)}
#: 主軸以外之軸實跑之排程先後（ic_page_long rows 先跑：寫直接呼叫格之列數軸存檔）
SECOND_AXIS_ORDER: Tuple[str, ...] = ("ic_page_long", "ic_page_relaxed", "deep_analysis_long", "post_ic_transform",
                                      "event_import", "cross_sectional", "icfirst_post_generation")


def primary_axis(run_id: str) -> str:
    """路徑／格之主軸（收據 points 之 x 軸）：`PRIMARY_AXIS` 所列者（event_study＝"events"），其餘＝"cols"（SPEC v5.51 (d)）。"""
    return PRIMARY_AXIS.get(run_id, "cols")


def row_scales_for(run_id: str) -> Tuple[int, ...]:
    """rows 軸實跑之列長：`CELL_ROW_SCALES` 所列之格用其短序列列長、IC-first＝`ICFIRST_ROW_SCALES`（三種窗長之生成），
    其餘＝`ROW_AXIS_SCALES`。"""
    if run_id == "icfirst_post_generation":
        return tuple(ICFIRST_ROW_SCALES)
    return tuple(CELL_ROW_SCALES.get(run_id, ROW_AXIS_SCALES))


def second_axis_run(cell: Optional[str]) -> Optional[Tuple[str, str]]:
    """清冊 input_axes 含 rows 之入口所屬格之第二軸實跑 (run_id, 軸名)：`ROW_AXIS_ALIAS`（跨標的＝timestamps）優先，其次
    `ROW_AXIS_RUN`（rows）；無 ⇒ None（排程無法涵蓋）。"""
    if cell in ROW_AXIS_ALIAS:
        return ROW_AXIS_ALIAS[str(cell)]
    if cell in ROW_AXIS_RUN:
        return ROW_AXIS_RUN[str(cell)], "rows"
    return None


def entry_runs(e: Mapping[str, Any]) -> Tuple[Tuple[str, str], Optional[Tuple[str, str]], bool]:
    """清冊 measure=true 入口所需之實跑（SPEC v5.52 (b)）：(主軸 (run_id, 軸), 第二軸 (run_id, 軸)｜None, 是否需第二軸)。
    主軸＝所屬格之主軸（`primary_axis`）；事件型格（`EVENT_AXIS_RUN`）之入口若 input_axes 不含 cols／passed_cols 而
    scale_vector 含 events ⇒ 主軸改 events（只隨事件數變之入口）。第二軸：input_axes 含 rows ⇒ `second_axis_run(格)`（無對應者
    回 (None, True)＝無法涵蓋）；否則 scale_vector 含 events 之事件型格入口而主軸非 events ⇒ (格, "events")。`fixed_axes`
    （清冊選填；路徑內不隨請求規模變之軸）不排軸。

    SPEC v5.53 (c0)（與上列衝突處以此為準）：事件型格（`EVENT_BARS_RUN`）入口之 unit_axis.axes 含 rows（K 線根數為成本軸）⇒
    須 (格, "rows") 實跑；不含 cols／passed_cols 之事件入口主軸依 unit_axis——含 events ⇒ events（K 線根數為第二軸）、只含
    rows（如 `evaluate_all_bars`）⇒ rows（scale_vector 含 events 者 events 為第二軸）。同一入口需兩個第二軸 ⇒ (主軸, None,
    True)＝無法涵蓋（排程點名，不靜默只量其一）。"""
    cell = str(e.get("branch_cell"))
    axes = set(e.get("input_axes") or [])
    sv = set(e.get("scale_vector") or [])
    ua = set((e.get("unit_axis") or {}).get("axes") or [])
    bars = cell in EVENT_BARS_RUN and "rows" in ua
    axis = primary_axis(cell)
    if cell in EVENT_AXIS_RUN and not axes & {"cols", "passed_cols"}:
        if "events" in ua or ("events" in sv and not bars):
            axis = "events"
        elif bars:
            axis = "rows"
    run_of = {"events": EVENT_AXIS_RUN, "rows": EVENT_BARS_RUN}.get(axis, {})
    primary = (run_of.get(cell, cell), axis)
    if "rows" in axes:
        # SPEC v5.56 (k)：入口級 rows 軸實跑（`ROW_AXIS_ENTRY_RUN`）優先於所屬格之第二軸
        eid = str(e.get("id"))
        return primary, ((ROW_AXIS_ENTRY_RUN[eid], "rows") if eid in ROW_AXIS_ENTRY_RUN else second_axis_run(cell)), True
    need: List[Tuple[str, str]] = []
    if "events" in sv and axis != "events" and cell in EVENT_AXIS_RUN:
        need.append((EVENT_AXIS_RUN[cell], "events"))
    if bars and axis != "rows":
        need.append((EVENT_BARS_RUN[cell], "rows"))
    if len(need) > 1:
        return primary, None, True
    return (primary, need[0], True) if need else (primary, None, False)


def schedule_runs(inventory: Mapping[str, Any], *, second_axes: bool = True) -> List[Tuple[str, str]]:
    """由清冊導出實跑排程 [(run_id, 軸)]（`measure_inventory` 同用）：先各入口之主軸（ic_page_default、ic_page_long 先，再
    其餘路徑、直接呼叫格；ic_page_default 寫 cols 軸存檔），再第二軸（`SECOND_AXIS_ORDER`，ic_page_long rows 先；其後直接
    呼叫格之 rows 軸，讀 ic_page_long rows 所寫存檔）；去重保序。`second_axes`=False ⇒ 只排主軸。SPEC v5.53 (c1)：
    `second_axes` 時另排 `VARIANT_RUNS`（其所變之格有 measure=true 入口者；排最後）。SPEC v5.58 (x)：`second_axes` 時另排
    `ISOLATION_RUNS`（入口 measure=true 者；排於主軸與第二軸之後、變體之前——讀 event_import events 軸之存檔）。"""
    prim: List[Tuple[str, str]] = []
    sec: List[Tuple[str, str]] = []
    iso: List[Tuple[str, str]] = []
    cells: Set[str] = set()
    for e in inventory.get("entries") or []:
        if not e.get("measure"):
            continue
        cells.add(str(e.get("branch_cell")))
        if second_axes and str(e.get("id")) in ISOLATION_RUNS:
            # SPEC v5.58 (x)：入口級之隔離直接呼叫格（讀其所屬格之事件數軸存檔 ⇒ 排在主軸與第二軸之後）
            iso.append(ISOLATION_RUNS[str(e["id"])])
        p, s, need = entry_runs(e)
        # SPEC v5.55 (f)：主軸即 rows 之直接呼叫格（參數敏感度兩格）讀 rows 軸路徑之存檔 ⇒ 排在第二軸段（該路徑之 rows 軸之後）
        (sec if second_axes and p[1] == "rows" and p[0] in CELLS else prim).append(p)
        if second_axes and need and s is not None and s[0] is not None:
            sec.append(s)
    order = {r: i for i, r in enumerate(("ic_page_default", "ic_page_long", *PATHS, *CELLS))}
    sorder = {r: i for i, r in enumerate((*SECOND_AXIS_ORDER, *PATHS, *CELLS))}
    prim = sorted(dict.fromkeys(prim), key=lambda x: (order.get(x[0], len(order)), x[1]))
    sec = sorted(dict.fromkeys(sec), key=lambda x: (sorder.get(x[0], len(sorder)), x[1]))
    var = [v for v, base in VARIANT_RUNS.items() if second_axes and base in cells]
    return list(dict.fromkeys(prim + sec + iso + var))


def schedule_coverage(inventory: Mapping[str, Any], sched: Sequence[Tuple[str, str]]) -> Dict[str, Any]:
    """排程對清冊之涵蓋（SPEC v5.52 (b)「排程與組裝之 require_rows 同步涵蓋」）：每一 measure=true 入口所需之主軸與第二軸
    （`entry_runs`）皆在 `sched` 且該軸為該 run 所支援（`RUN_AXES`）⇒ 涵蓋。回 {"measured", "covered", "uncovered": [{"id",
    "missing": [...]}], "by_axis": {"<run>:<軸>": 入口數}, "fixed_axes": {id: [軸...]}, "variants": {"<run>:<軸>": {"cell",
    "scheduled", "entries"}}}（SPEC v5.53 (c1)：變體實跑另列，不影響 covered／uncovered）。SPEC v5.58 (x)：`isolation`＝
    {"<run>:<軸>": {"entry", "scheduled"}}（`ISOLATION_RUNS` 之入口 measure=true 者；另列，不影響 covered／uncovered）。"""
    have = {(r, a) for r, a in sched if a in RUN_AXES.get(r, ())}
    out: Dict[str, Any] = {"measured": 0, "covered": 0, "uncovered": [], "by_axis": {}, "fixed_axes": {}, "variants": {},
                           "isolation": {}}
    for (vr, va), base in VARIANT_RUNS.items():
        n = sum(1 for e in inventory.get("entries") or [] if e.get("measure") and e.get("branch_cell") == base)
        if n:
            out["variants"][f"{vr}:{va}"] = {"cell": base, "scheduled": (vr, va) in have, "entries": n}
    for e in inventory.get("entries") or []:
        if e.get("measure") and str(e.get("id")) in ISOLATION_RUNS:
            ir, ia = ISOLATION_RUNS[str(e["id"])]
            out["isolation"][f"{ir}:{ia}"] = {"entry": str(e["id"]), "scheduled": (ir, ia) in have}
    for e in inventory.get("entries") or []:
        if not e.get("measure"):
            continue
        out["measured"] += 1
        p, s, need = entry_runs(e)
        missing = [f"{p[0]}:{p[1]}"] if p not in have else []
        if need:
            if s is None or s[0] is None:
                missing.append(f"{e.get('branch_cell')}:<無第二軸對應>")
            elif s not in have:
                missing.append(f"{s[0]}:{s[1]}")
        for run in [p] + ([s] if need and s else []):
            out["by_axis"][f"{run[0]}:{run[1]}"] = out["by_axis"].get(f"{run[0]}:{run[1]}", 0) + 1
        if e.get("fixed_axes"):
            out["fixed_axes"][str(e["id"])] = sorted(e["fixed_axes"])
        if missing:
            out["uncovered"].append({"id": str(e["id"]), "missing": missing})
        else:
            out["covered"] += 1
    return out


def axis_scales(run_id: str, axis: str, *, cols_scales: Sequence[int], row_scales: Sequence[int],
                event_scales: Sequence[int], bar_scales: Optional[Sequence[int]] = None,
                survivor_scales: Optional[Sequence[int]] = None) -> List[int]:
    """(run_id, 軸) 之三規模點：cols＝`cols_scales`；rows＝`CELL_ROW_SCALES`／IC-first 窗長或 `row_scales`；events＝
    `event_scales`；timestamps＝`XSEC_TIMESTAMP_SCALES`。SPEC v5.53 (c0)：事件路徑之 rows（K 線根數）＝`bar_scales`（不給 ⇒
    `event_bar_scales()` 由真實快取與事件批導出）。SPEC v5.55 (e)：survivors＝`survivor_scales`（不給 ⇒ HarnessError；由
    `post_ic_survivor_scales` 自 ic_page_relaxed 實跑存下之 IC 任務導出，須於該路徑實跑後取得）。"""
    if axis == "cols" and run_id in REDUNDANCY_STAGE_CELLS:
        # SPEC v5.56 (l)：冗餘格之 cols 軸＝stage_cols 設計點（第 6 段真實輸入之 seeded 巢狀子集之輸入欄數）
        return list(REDUNDANCY_STAGE_COLS_SCALES)
    if axis == "cols":
        return [int(s) for s in cols_scales]
    if axis == "families":
        # SPEC v5.56 (o)：參數敏感度家族數軸
        return list(PARAM_FAMILY_SCALES)
    if axis == "survivors":
        if survivor_scales is None:
            raise HarnessError("survivors 軸之規模點須由 ic_page_relaxed 實跑存下之 IC 任務導出（post_ic_survivor_scales）")
        return [int(s) for s in survivor_scales]
    if axis == "rows" and run_id in EVENT_BARS_RUN.values():
        return [int(s) for s in (event_bar_scales() if bar_scales is None else bar_scales)]
    if axis == "rows":
        if run_id in CELL_ROW_SCALES or run_id == "icfirst_post_generation":
            return list(row_scales_for(run_id))
        return [int(s) for s in row_scales]
    if axis == "events":
        return [int(s) for s in event_scales]
    if axis == "timestamps":
        return list(XSEC_TIMESTAMP_SCALES)
    raise HarnessError(f"未知軸：{axis}")


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

        flat = a.reshape(-1).astype(object)
        try:
            h.update(pd.util.hash_array(flat).tobytes())
        except TypeError:
            # 不可雜湊之元素（事件表之 dict 欄，如 `label_definition`；2026-11-01 event_study rows 軸 smoke 於
            # `align_events` 之輸入鍵實測 TypeError）⇒ 逐元素正準 JSON（鍵排序；非 JSON 型別取 repr）
            for x in flat:
                h.update(json.dumps(x, sort_keys=True, ensure_ascii=False, default=repr).encode("utf-8") + b"\x00")


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
        #: SPEC v5.56 (p)：非 None ⇒ 只記此集合內之入口（其餘 wrapper 直通、不計次數與秒數）；供同一實跑內之非預設分支探針
        #: （`restricted`）只量其目標入口，不污染其餘入口之預設路徑量測
        self.only: Optional[Set[str]] = None
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

    @contextlib.contextmanager
    def restricted(self, eids: Iterable[str]) -> Iterable[None]:
        """期間內只記 `eids` 之入口（SPEC v5.56 (p)；其餘 wrapper 直通）；離開即恢復全記。不可巢狀。"""
        if self.only is not None:
            raise HarnessError("Recorder.restricted 不可巢狀")
        self.only = set(eids)
        try:
            yield
        finally:
            self.only = None


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
        only = rec.only
        if only is not None and eid not in only:
            return func(*args, **kwargs)  # SPEC v5.56 (p)：restricted 期間之非目標入口直通
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
        only = rec.only
        if only is not None and eid not in only:
            return (yield from func(*args, **kwargs))  # SPEC v5.56 (p)：restricted 期間之非目標入口直通
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


def _capture_writer(stage_dir: Path, name: str, with_result: bool, provenance: Mapping[str, Any],
                    overwrite: bool = False) -> Callable:
    """存檔寫出端（只存本次實跑之第一次呼叫）。`overwrite`＝存檔目錄之身分與本次子集不同（SPEC v5.52 (a)）⇒ 覆寫既有檔；
    否則既有檔沿用（同身分之前次實跑已寫）。"""
    def write(args: Tuple[Any, ...], kwargs: Dict[str, Any], result: Any) -> None:
        import pickle

        out = stage_dir / f"{name}.pkl"
        if out.exists() and not overwrite:
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


def load_capture(stage_dir: Path, name: str, expected: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """讀存檔真實輸入。SPEC v5.52 (a)：`expected` 給定 ⇒ 存檔目錄之 `STAGE_IDENTITY_FILE` 須 status complete 且其身分逐欄等於
    `expected`（現行來源之子集身分），否則 HarnessError（存檔來自他版來源，不得沿用；須先重跑寫出之路徑）。"""
    import pickle

    path = Path(stage_dir) / f"{name}.pkl"
    if not path.is_file():
        raise HarnessError(f"直接呼叫格之存檔真實輸入不存在：{path}（須先跑同一規模點之 ic_page_default 路徑）")
    if expected is not None:
        side = read_identity(Path(stage_dir) / STAGE_IDENTITY_FILE) or {}
        got = {k: side.get(k) for k in expected}
        if side.get("status") != "complete" or got != json.loads(json.dumps(dict(expected))) \
                or name not in (side.get("files") or []):
            raise HarnessError(f"存檔 {stage_dir} 之身分與現行來源不符（SPEC v5.52 (a)；status={side.get('status')!r}）：須先重跑"
                               f"寫出之路徑 {expected.get('writer')}")
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


#: 以 L 格為資料源之路徑（cols 軸亦然）；其餘路徑之 rows 軸亦於 L 格（`RunContext.long`）。SPEC v5.55 (d)：非預設門檻分支
#: 於 L 格（樣本外切分成立；組裝驗 split_applied）
LONG_RUNS = ("ic_page_long", "deep_analysis_long", "ic_page_relaxed")
#: 讀交接 h5 巢狀子集之路徑
SUBSET_RUNS = ("ic_page_default", "ic_page_long", "deep_analysis", "deep_analysis_long")


class RunContext:
    def __init__(self, run_id: str, axis: str, scale: int, out_root: Path, work: Path, rec: Recorder,
                 head: Optional[str]):
        self.run_id, self.axis, self.scale = run_id, axis, int(scale)
        self.out_root, self.work, self.rec, self.head = out_root, work, rec, head
        self.n_cols = int(scale) if axis == "cols" else ROW_AXIS_COLS
        self.n_rows: Optional[int] = int(scale) if axis == "rows" else None
        #: SPEC v5.52 (b)：timestamps 軸（跨標的）之時點數、events 軸之事件數
        self.n_timestamps: Optional[int] = int(scale) if axis == "timestamps" else None
        self.n_events: Optional[int] = int(scale) if axis == "events" else None
        #: SPEC v5.55 (e)：survivors 軸（IC 後轉換）之倖存欄數
        self.n_survivors: Optional[int] = int(scale) if axis == "survivors" else None
        #: SPEC v5.55：存檔目錄之群組（路徑＝`STAGE_GROUP`、直接呼叫格＝`CELL_GROUP`；""＝IC 頁預設、D＝深度、R＝非預設門檻）
        self.group = STAGE_GROUP.get(run_id, CELL_GROUP.get(run_id, ""))
        #: v5.51 (a)：rows 軸與 L 格路徑之資料源＝L 格（IC-first 之 rows 軸除外：A 格三種窗長之生成）；讀非預設門檻分支
        #: 存檔之格（R 群組）兩軸皆 L 格
        self.long = (axis == "rows" and run_id != "icfirst_post_generation") or run_id in LONG_RUNS or self.group == "R" \
            or run_id in PARAM_FAMILY_CELLS
        #: SPEC v5.52 (b)：本次實際輸入之規模點數（runner 驗得後設；run_one 對宣告之 scale 驗等）
        self.actual_scale: Optional[int] = None
        #: SPEC v5.58 (x)：固定倖存集合之參考點（`--ref-scale`；mann_whitney 直接呼叫格用）與 event_import 第 5 段二元收據之
        #: 存放處（run_one 設 `binary_capture_hook`；未設 ⇒ None）
        self.ref_scale: Optional[int] = None
        self.binary_capture: Optional[Dict[str, Any]] = None

    @property
    def stage_dir(self) -> Path:
        return self.out_root / "stage_inputs" / self.stage_tag(self.n_rows)

    def subset_tag(self, n_rows: Optional[int]) -> str:
        """交接 h5 巢狀子集之目錄名（`<out-root>/subsets/<tag>/`；不分群組——同一子集供各群組之路徑共用）。"""
        if n_rows is None:
            return f"L{self.n_cols}" if self.long else str(self.n_cols)
        return f"L{self.n_cols}_rows{int(n_rows)}"

    def stage_tag(self, n_rows: Optional[int]) -> str:
        """存檔真實輸入之目錄名（`<out-root>/stage_inputs/<tag>/`）：群組前綴（SPEC v5.55；IC 頁預設無前綴）＋子集名。"""
        return self.group + self.subset_tag(n_rows)


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


_SHA_MEMO: Dict[Tuple[str, int, int], str] = {}


def file_sha256(path: Path) -> str:
    """檔案內容 sha256（串流讀；同一行程內以 (realpath, size, mtime_ns) 記憶，來源於行程內不變）。"""
    p = Path(os.path.realpath(path))
    st = p.stat()
    key = (str(p), int(st.st_size), int(st.st_mtime_ns))
    if key not in _SHA_MEMO:
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(block)
        _SHA_MEMO[key] = h.hexdigest()
    return _SHA_MEMO[key]


def _handoff_shape(src_h5: Path) -> Tuple[int, int]:
    """交接 h5 之（列數, 全序欄數）（`h5_feature_precision.feature_layout`；同 `_write_stage5_subset` 之讀法）。"""
    import h5py

    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from momentum.core import h5_feature_precision as h5fp

    meta = json.loads(Path(src_h5).with_name(Path(src_h5).stem + "_meta.json").read_text(encoding="utf-8"))
    with h5py.File(src_h5, "r") as f:
        rows, total, _f64 = h5fp.feature_layout(f[f"{meta['symbol']}/{meta['timeframe']}"])
    return int(rows), int(total)


def subset_identity(src_h5: Path, *, n_cols: int, seed: int, rows: Optional[int] = None) -> Dict[str, Any]:
    """SPEC v5.52 (a)：巢狀子集（與其所衍生之各段存檔輸入）之來源身分＝{來源交接 h5 之路徑、大小、內容 sha256、列數、全序
    欄數, seed, 子集欄數 n_cols, 子集列長 rows（None＝來源全長）}；任一不同 ⇒ 不沿用、重建。"""
    src_rows, total = _handoff_shape(src_h5)
    return {"schema": SUBSET_IDENTITY_SCHEMA, "source": _rel(Path(src_h5)), "source_size": int(Path(src_h5).stat().st_size),
            "source_sha256": file_sha256(src_h5), "source_rows": src_rows, "source_total_cols": total,
            "seed": int(seed), "n_cols": int(n_cols), "rows": None if rows is None else int(rows)}


def read_identity(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_identity(path: Path, identity: Mapping[str, Any]) -> None:
    """身分 sidecar 原子寫（暫存檔 → os.replace）。"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(path).with_suffix(".json.part")
    tmp.write_text(json.dumps(dict(identity), ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def ensure_subset(src_h5: Path, n_cols: int, seed: int, sub_dir: Path, *,
                  rows: Optional[int] = None, parent_dir: Optional[Path] = None) -> Tuple[Path, Path, bool]:
    """SPEC v5.52 (a)：`sub_dir` 之 N 欄巢狀子集（`rows` 給定 ⇒ 另截末 R 列，母子集於 `parent_dir`）——`sub_dir` 之
    `SUBSET_IDENTITY_FILE` 逐欄等於現行來源之 `subset_identity`（來源內容 sha256、seed、欄數、列長）且 h5／meta 皆存在 ⇒
    沿用；否則重建（覆寫）後寫 sidecar。回 (h5, meta, 是否重建)。"""
    fb = _fb()
    src_meta = Path(src_h5).with_name(Path(src_h5).stem + "_meta.json")
    want = subset_identity(src_h5, n_cols=n_cols, seed=seed, rows=rows)
    h5, meta = Path(sub_dir) / Path(src_h5).name, Path(sub_dir) / src_meta.name
    side = Path(sub_dir) / SUBSET_IDENTITY_FILE
    if h5.is_file() and meta.is_file() and read_identity(side) == json.loads(json.dumps(want)):
        return h5, meta, False
    if rows is None:
        h5, meta = fb._write_stage5_subset(Path(src_h5), src_meta, int(n_cols), int(seed), Path(sub_dir))
    else:
        if parent_dir is None:
            raise HarnessError("ensure_subset：rows 子集須給母子集目錄 parent_dir")
        ph5, pmeta, _ = ensure_subset(src_h5, n_cols, seed, parent_dir)
        h5, meta = _truncate_rows(ph5, pmeta, int(rows), Path(sub_dir))
    write_identity(side, want)
    return h5, meta, True


def _subset_paths(ctx: RunContext) -> Tuple[Path, Path]:
    """交接 h5（C 格；rows 軸與 L 格路徑＝L 格，v5.51 (a)）之 N 欄巢狀子集（`<out-root>/subsets/<tag>/`）；rows 軸另截末 R
    列。SPEC v5.52 (a)：經 `ensure_subset` 比對來源身分，不同即重建（不只憑檔案存在）。"""
    fb = _fb()
    src = subset_source(ctx.long)
    sub_dir = ctx.out_root / "subsets" / ctx.subset_tag(None)
    if ctx.n_rows is None:
        h5, meta, _ = ensure_subset(src, ctx.n_cols, fb.SEED, sub_dir)
        return h5, meta
    h5, meta, _ = ensure_subset(src, ctx.n_cols, fb.SEED, ctx.out_root / "subsets" / ctx.subset_tag(ctx.n_rows),
                                rows=ctx.n_rows, parent_dir=sub_dir)
    return h5, meta


def expected_stage_identity(ctx: "RunContext", n_rows: Optional[int]) -> Dict[str, Any]:
    """直接呼叫格所讀存檔目錄之應有身分（SPEC v5.52 (a)）：該存檔所屬子集之 `subset_identity`（現行來源；rows＝存檔子集
    列長）＋寫出之 (路徑, 軸)。"""
    fb = _fb()
    cols_run, rows_run = GROUP_WRITERS[ctx.group]
    if ctx.group == "" and ctx.long and n_rows is None:
        # SPEC v5.56 (o)：IC 頁預設群組之 L 格 cols 軸存檔（L<N>/）由 ic_page_long cols 寫（C 格 <N>/ 由 ic_page_default 寫）
        cols_run = "ic_page_long"
    writer = (rows_run, "rows") if n_rows is not None else (cols_run, "cols")
    if ctx.group == "R":
        # SPEC v5.55 (d)：非預設門檻分支讀 L 格 run（非交接 h5）⇒ 身分＝run manifest＋請求之欄＋門檻覆寫＋列長
        return {"subset": relaxed_identity(ctx.n_cols, n_rows), "writer": list(writer)}
    src = subset_source(ctx.long)
    return {"subset": subset_identity(src, n_cols=ctx.n_cols, seed=fb.SEED, rows=n_rows),
            "writer": list(writer)}


def _h5_rows(h5: Path) -> int:
    import h5py

    with h5py.File(h5, "r") as f:
        found: List[int] = []
        f.visititems(lambda k, v: found.append(int(v.shape[0])) if k.endswith("timestamps") else None)
    return found[0] if found else 0


def _h5_cols(h5: Path) -> int:
    """子集交接 h5 之實際欄數（`feature_names` 長度；SPEC v5.52 (b) 驗實際輸入點數＝宣告規模）。"""
    import h5py

    with h5py.File(h5, "r") as f:
        found: List[int] = []
        f.visititems(lambda k, v: found.append(int(v.shape[0])) if k.endswith("feature_names") else None)
    return found[0] if found else 0


def _subset_actual(ctx: "RunContext", h5: Path) -> int:
    """IC 頁／深度分析路徑之實際輸入點數：cols 軸＝子集實際欄數、rows 軸＝子集實際列數。"""
    return _h5_rows(h5) if ctx.axis == "rows" else _h5_cols(h5)


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


def _split_facts_from_cache(analyzer: Any, report: Any) -> Dict[str, Any]:
    """服務路徑（帶 feature_filter）之切分事實：取 analyzer 實際所用之切分（`_ic_cache["split_context"]` 之 train／test
    遮罩，`ic_filter_orchestrator.py:5525`；refilter 同用）。報告 metadata 於帶 feature_filter 時不保留 `ic_train_test_split`
    （`_apply_feature_filter` → `_filter_metadata_for_columns` 剔除非特徵之 dict 值鍵，`ic_filter_orchestrator.py:4816`、
    `:4838-4847` ⇒ `_downgrade_branch` 判 `no_holdout_evidence`、analysis_status degraded；2026-11-01 smoke 實查），故不以
    報告 metadata 判切分；報告之 analysis_status 另記（`report_analysis_status`）以顯示此不一致。"""
    sc = (getattr(analyzer, "_ic_cache", None) or {}).get("split_context")
    out: Dict[str, Any] = {"split_applied": False, "split_train_rows": None, "split_test_rows": None,
                           "split_source": "analyzer._ic_cache.split_context",
                           "report_analysis_status": (report or {}).get("analysis_status")
                           if isinstance(report, Mapping) else None}
    if isinstance(sc, Mapping) and sc.get("test_mask") is not None:
        import numpy as np

        out.update(split_applied=True, split_train_rows=int(np.asarray(sc["train_mask"], dtype=bool).sum()),
                   split_test_rows=int(np.asarray(sc["test_mask"], dtype=bool).sum()))
    return out


def _run_ic_page_default(ctx: RunContext) -> Dict[str, Any]:
    analyzer, report, h5 = _ic_page_analyze_subset(ctx, _page_request(ctx, "ic_report"))
    return {**_ic_facts(report, analyzer, ctx.n_cols, _h5_rows(h5)), **_split_facts(report), "requested_columns": None,
            "actual_scale": _subset_actual(ctx, h5)}


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
            "deep_selected": len(selected or []), "requested_columns": None, "actual_scale": _subset_actual(ctx, h5)}


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


#: SPEC v5.56 (m)：harness 請求之選欄規則（非凍結項；凍結項之 `icperf_freeze_baseline.small_request` 不改）
REQUEST_COLUMN_RULE = ("seeded_nested：run manifest raw 欄序（去重）之 default_rng(SEED).permutation 前 n 個、依欄序排列"
                       "（同 icperf_freeze_baseline._write_stage5_subset 之 SEED 規則；n 遞增時巢狀）")


def seeded_columns(pool: Sequence[str], n: int, seed: Optional[int] = None) -> List[str]:
    """SPEC v5.56 (m)：`pool`（欄序，去重保序）之 seeded 隨機巢狀子集——`np.sort(default_rng(seed).permutation(len)[:n])`
    之位置（同 `_write_stage5_subset`；seed 預設 `icperf_freeze_baseline.SEED`）；n 遞增時前者 ⊆ 後者。n 不在 [0, len]
    ⇒ HarnessError（資料不足）。"""
    import numpy as np

    uniq = list(dict.fromkeys(str(c) for c in pool))
    if not 0 <= int(n) <= len(uniq):
        raise HarnessError(f"選欄 {n} 不在 [0, {len(uniq)}]（資料不足；須以欄數足夠之 run 補足）")
    s = _fb().SEED if seed is None else int(seed)
    pick = np.sort(np.random.default_rng(s).permutation(len(uniq))[:int(n)])
    return [uniq[int(i)] for i in pick]


def family_distribution(names: Sequence[str]) -> Dict[str, Any]:
    """SPEC v5.56 (m)：請求欄之指標家族分佈——家族＝欄名以 "_" 分之前 4 段（資料來源_週期_類別_指標，如
    `close_4h_trend_BBANDS-Lower`；本專案 FF 欄名之前 4 段，L 格 raw 3,632 欄得 29 族）；回 {"rule", "n_columns",
    "n_families", "max_family_share", "counts"（族 ⇒ 欄數，依欄數遞減）}。"""
    counts: Dict[str, int] = {}
    for n in names:
        fam = "_".join(str(n).split("_")[:4])
        counts[fam] = counts.get(fam, 0) + 1
    ordered = dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
    total = sum(counts.values())
    return {"rule": "欄名以 '_' 分之前 4 段（資料來源_週期_類別_指標）", "n_columns": total, "n_families": len(counts),
            "max_family_share": (max(counts.values()) / total) if total else None, "counts": ordered}


def _limited_request(item: str, cell: Optional[str], n: int) -> Dict[str, Any]:
    """harness 路徑之請求（item 之預設請求限 n 欄；`feature_filter.include_features`＝`seeded_columns`）。SPEC v5.56 (m)：
    改 seeded 隨機巢狀（原 `small_request` 之排序前綴使前 25 欄同屬 `close_4h_trend_BBANDS-Lower_13*`，第 6 段輸入偏單一
    指標家族）；凍結項之 `small_request` 不改。規則字面＝`REQUEST_COLUMN_RULE`（記於路徑事實）。"""
    fb = _fb()
    base = fb.default_request(item) if cell is None else fb.default_request(item, cell)
    pool = fb._run_feature_names(base)
    if len(set(pool)) < n:
        raise HarnessError(f"{base['cell']} 之 raw 欄數 {len(set(pool))} < 規模 {n}（資料不足；須以欄數足夠之 run 補足）")
    new = fb._json_copy(base)
    new["feature_filter"] = {"include_features": seeded_columns(pool, int(n))}
    return new


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


#: IC 後轉換之參數（同 IC 頁第三步預設：rank／zscore／gaussian 全開、rank 窗 252、zscore 窗 [100, 252]）
POST_IC_ARGS: Tuple[Any, ...] = (True, True, True, 252, [100, 252])
#: SPEC v5.52 (b)：post_ic_transform 列軸之存檔輸入（L 格 IC 任務；`prepare post-ic-rows` 產生）之目錄與檔名
POST_IC_ROWS_DIR = "stage_inputs/post_ic_rows"
POST_IC_ROWS_FILE = "task.pkl"
#: SPEC v5.56 (p)：IC 後轉換之分塊分支（`FeaturePreprocessor.transform` 於 `chunk_size > 0 且欄數 > chunk_size` 時走
#: `_transform_chunked`，`feature_preprocessor.py:915-921`；chunk_size 讀既有環境變數 `FFACT_L65_CHUNK_SIZE`，預設 2000，
#: `:873-880`，於前處理器建構時讀，`:210`）——IC 頁倖存欄遠少於 2000 ⇒ 預設 0 呼叫。量法：同一實跑於預設呼叫後，以
#: `FFACT_L65_CHUNK_SIZE`＝`POST_IC_CHUNK_SIZE` 再呼叫一次 `_apply_transforms_sync`（同一任務、同一倖存欄、同一參數），期間
#: `Recorder.restricted` 只記 `_transform_chunked`（其餘入口直通，不污染預設路徑之量測）；事實記非預設分支。
#: 選值 8：< 正式 survivors 三點之最小點（2026-11-01 smoke RL100／RL500 倖存 12／56；不足者 HarnessError），且 ≥ 2 使每塊
#: 含多欄；塊寬固定、塊數＝⌈倖存欄數／8⌉ 隨規模線性成長（同產品分塊語意：塊寬為記憶體上限、塊數隨欄數）
POST_IC_CHUNK_SIZE = 8
POST_IC_CHUNK_ENV = "FFACT_L65_CHUNK_SIZE"
POST_IC_CHUNKED_ENTRY = ("momentum.FeatureEngineering.preprocessing.feature_preprocessor:"
                         "FeaturePreprocessor._transform_chunked")


def post_ic_chunked_probe(rec: Recorder, call: Callable[[], Any], n_survivors: int,
                          chunk_size: int = POST_IC_CHUNK_SIZE) -> Dict[str, Any]:
    """SPEC v5.56 (p)：分塊分支之探針——`n_survivors` ≤ `chunk_size` ⇒ HarnessError（不走分塊）；否則環境變數
    `POST_IC_CHUNK_ENV`＝`chunk_size` 下於 `rec.restricted({POST_IC_CHUNKED_ENTRY})` 內執行 `call()`（結束還原環境變數），
    目標入口之呼叫增量須 ≥ 1（否則 HarnessError：設定未生效）。回非預設分支之事實。"""
    import math

    if int(n_survivors) <= int(chunk_size):
        raise HarnessError(f"IC 後轉換分塊探針：倖存欄 {n_survivors} ≤ 塊寬 {chunk_size}（不走 _transform_chunked；SPEC v5.56 (p)）")
    before = rec.stat(POST_IC_CHUNKED_ENTRY).calls
    old = os.environ.get(POST_IC_CHUNK_ENV)
    os.environ[POST_IC_CHUNK_ENV] = str(int(chunk_size))
    try:
        with rec.restricted({POST_IC_CHUNKED_ENTRY}):
            call()
    finally:
        if old is None:
            os.environ.pop(POST_IC_CHUNK_ENV, None)
        else:
            os.environ[POST_IC_CHUNK_ENV] = old
    calls = rec.stat(POST_IC_CHUNKED_ENTRY).calls - before
    if calls < 1:
        raise HarnessError(f"IC 後轉換分塊探針：{POST_IC_CHUNK_ENV}={chunk_size} 下 _transform_chunked 0 呼叫（設定未生效）")
    return {"entry": POST_IC_CHUNKED_ENTRY, "branch": "non_default", "env": f"{POST_IC_CHUNK_ENV}={int(chunk_size)}",
            "chunk_size": int(chunk_size), "n_survivors": int(n_survivors),
            "n_chunks": int(math.ceil(int(n_survivors) / int(chunk_size))), "calls": int(calls),
            "recording": "Recorder.restricted：探針期間只記目標入口，其餘入口之秒數與次數只含預設呼叫"}


class _NullProgress:
    """prepare 步驟之進度接收端（不量測；`_service_analysis` 須有 `progress`）。"""

    def progress(self, *args: Any, **kwargs: Any) -> None:
        return None


def post_ic_rows_identity(branch: str = "default") -> Dict[str, Any]:
    """post_ic_transform 列軸存檔輸入之來源身分（SPEC v5.52 (a)）：L 格 run 之 manifest 路徑、大小、內容 sha256、固定欄數
    `ROW_AXIS_COLS` 與請求之欄（`_limited_request`＝seeded 巢狀，SPEC v5.56 (m)；兩分支同一欄集合）之 sha256、選欄規則。
    SPEC v5.55 (e)：`branch`＝"default"（IC 頁預設請求）
    或 "non_default"（預設請求倖存欄為空時改用之非預設門檻請求 `relaxed_request`；身分另記門檻覆寫）。"""
    fb = _fb()
    request = _limited_request("ic_report", fb.LONG_CELL, ROW_AXIS_COLS)
    manifest = REPO / request["run_dir"] / "feature_manifest.json"
    names = list(request["feature_filter"]["include_features"])
    out = {"schema": SUBSET_IDENTITY_SCHEMA, "source": _rel(manifest), "source_size": int(manifest.stat().st_size),
           "source_sha256": file_sha256(manifest), "n_cols": ROW_AXIS_COLS, "rows": None,
           "columns_sha256": hashlib.sha256(json.dumps(names, ensure_ascii=False).encode("utf-8")).hexdigest(),
           "column_rule": REQUEST_COLUMN_RULE}
    if branch != "default":
        out.update(threshold_branch="non_default", thresholds=dict(RELAXED_THRESHOLDS))
    return out


def _post_ic_rows_saved_identity(root: Path) -> Optional[Dict[str, Any]]:
    """`root` 之存檔身分等於現行預設或非預設門檻身分者 ⇒ 該身分；否則 None。"""
    side = read_identity(Path(root) / SUBSET_IDENTITY_FILE)
    for branch in ("default", "non_default"):
        want = json.loads(json.dumps(post_ic_rows_identity(branch)))
        if side == want:
            return want
    return None


def prepare_post_ic_rows(out_root: Path) -> Dict[str, Any]:
    """SPEC v5.52 (b)：post_ic_transform 列軸之存檔輸入——L 格 run（4h 2,000 列）以 feature_filter 限 `ROW_AXIS_COLS` 欄經服務
    `start_analysis` 跑一次 IC 分析（同 cols 軸之服務路徑），存其任務紀錄（`req_*`、`result`〔含報告 run 身分〕、status）與
    IC 倖存欄於 `<out-root>/POST_IC_ROWS_DIR/`，身分 sidecar＝`post_ic_rows_identity`（不同即重建）。列軸實跑讀此存檔、於末
    R 列直接呼叫 `_apply_transforms_sync`（不再跑 IC）。倖存欄為空 ⇒ HarnessError（資料不足）。"""
    import pickle

    fb = _fb()
    root = (Path(out_root) if Path(out_root).is_absolute() else REPO / out_root) / POST_IC_ROWS_DIR
    side = root / SUBSET_IDENTITY_FILE
    saved_identity = _post_ic_rows_saved_identity(root)
    if (root / POST_IC_ROWS_FILE).is_file() and saved_identity is not None:
        return {"reused": True, "dir": _rel(root), "identity": saved_identity}
    # SPEC v5.55 (e)：先以 IC 頁預設請求；倖存欄為空 ⇒ 改用非預設門檻請求（`relaxed_request`），身分與存檔記明
    survivors: List[str] = []
    for branch in ("default", "non_default"):
        request = (_limited_request("ic_report", fb.LONG_CELL, ROW_AXIS_COLS) if branch == "default"
                   else relaxed_request(ROW_AXIS_COLS))
        with _prepare_isolation(root.parent.parent, f"post-ic-rows-{branch}") as work:
            svc = _service_with_tasks(request, work / "registry.json")
            task_id, info = _service_analysis(svc, fb._ic_analyze_request(request), _NullProgress())  # type: ignore[arg-type]
        survivors = [str(c) for c in info["analyzer"].get_filtered_features().columns]
        if survivors:
            break
    want = post_ic_rows_identity(branch)
    if not survivors:
        raise HarnessError("prepare post-ic-rows：L 格 IC 倖存欄於預設與非預設門檻請求皆為空，無法量 IC 後轉換之列軸（資料不足）")
    task_info = {k: v for k, v in info.items() if str(k).startswith("req_")}
    task_info.update(status=info.get("status"), result=info.get("result"))
    payload = {"task_id": task_id, "task_info": task_info, "survivors": survivors, "request": request,
               "head": _git_head(), "identity": want, "threshold_branch": branch}
    root.mkdir(parents=True, exist_ok=True)
    tmp = root / (POST_IC_ROWS_FILE + ".part")
    with open(tmp, "wb") as fh:
        pickle.dump(payload, fh, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, root / POST_IC_ROWS_FILE)
    write_identity(side, want)
    return {"reused": False, "dir": _rel(root), "identity": want, "survivors": len(survivors)}


def load_post_ic_rows(out_root: Path) -> Dict[str, Any]:
    """讀 post_ic_transform 列軸存檔輸入；身分 sidecar 須等於現行 `post_ic_rows_identity`（預設或非預設門檻分支；SPEC
    v5.52 (a)、v5.55 (e)），否則 HarnessError（須先跑 `prepare post-ic-rows`）。"""
    import pickle

    root = Path(out_root) / POST_IC_ROWS_DIR
    if not (root / POST_IC_ROWS_FILE).is_file() or _post_ic_rows_saved_identity(root) is None:
        raise HarnessError(f"post_ic_transform rows 軸之存檔輸入不存在或身分與現行來源不符：{root}（先跑 `icperf_scale_harness.py "
                           "prepare post-ic-rows`）")
    with open(root / POST_IC_ROWS_FILE, "rb") as fh:
        return pickle.load(fh)


# ── SPEC v5.55 (d)(e)：非預設門檻之 IC 頁路徑與 IC 後轉換 survivors 軸 ─────────────────────────────────────────────


def relaxed_request(n_cols: int, rows: Optional[int] = None) -> Dict[str, Any]:
    """非預設門檻分支之請求：L 格 run 之 IC 頁請求（`_limited_request("ic_report", LONG_CELL, n)`：feature_filter＝seeded
    巢狀 n 欄〔SPEC v5.56 (m)〕，同 `prepare_post_ic_rows`）之 `config_override.thresholds` 深合併 `RELAXED_THRESHOLDS`（只覆寫第 5 段門檻，其餘同
    IC 頁預設）；`rows` 給定 ⇒ 另加列數軸視窗覆寫（`with_row_windows`，同 ic_page_long rows 軸）。請求記 `threshold_branch`
    ＝"non_default"。"""
    fb = _fb()
    request = _limited_request("ic_report", fb.LONG_CELL, int(n_cols))
    ov = json.loads(json.dumps(request["config_override"]))
    ov["thresholds"] = {**dict(ov.get("thresholds") or {}), **RELAXED_THRESHOLDS}
    if rows is not None:
        ov = with_row_windows(ov)
    return {**request, "config_override": ov, "threshold_branch": "non_default",
            "threshold_override": dict(RELAXED_THRESHOLDS)}


#: SPEC v5.57 (q)：事件數軸（預檢與 event_import events 軸）之門檻分支事實鍵——請求之實際門檻（深合併後之
#: `config_override.thresholds`）與覆寫值
EVENT_AXIS_THRESHOLD_BASIS = ("SPEC v5.57 (q)：事件數軸比照 v5.55 (d) 走非預設門檻之產品完整路徑（只覆寫 p_value_max＝"
                              "RELAXED_THRESHOLDS）——二元模式 p 閘＝mw_p_value(_adj) ≤ alpha_effective（ic_filter_orchestrator.py"
                              ":6061-6063）、alpha_effective＝thresholds.p_value_max（:5276-5285）；預設門檻下低點第 5 段無通過欄 ⇒ "
                              "block_permutation_table 因 `if passed:`（:5796-5801）0 呼叫（smoke_v556 precheck_events_v556_b.json）；"
                              "其餘二元門檻（rank_biserial_min、binary_unavailable）維持預設")


def relaxed_event_request(n_cols: int) -> Dict[str, Any]:
    """SPEC v5.57 (q)：事件數軸之非預設門檻請求——事件匯入路徑之請求（`_limited_request("event_import_report", None, n)`：
    L 格 run、feature_filter＝seeded 巢狀 n 欄）之 `config_override.thresholds` 深合併 `RELAXED_THRESHOLDS`（只覆寫
    `p_value_max`，同 `relaxed_request`；其餘請求欄位〔event_import_id 由呼叫端代入、標籤設定、tier〕同事件匯入預設請求）。
    請求記 `threshold_branch`＝"non_default"、`threshold_override`。"""
    request = _limited_request("event_import_report", None, int(n_cols))
    ov = json.loads(json.dumps(request.get("config_override") or {}))
    ov["thresholds"] = {**dict(ov.get("thresholds") or {}), **RELAXED_THRESHOLDS}
    return {**request, "config_override": ov, "threshold_branch": "non_default",
            "threshold_override": dict(RELAXED_THRESHOLDS)}


def event_threshold_facts(request: Mapping[str, Any], report: Any) -> Dict[str, Any]:
    """SPEC v5.57 (q)：事件數軸一點之門檻事實——請求之分支與實際門檻設定（`config_override.thresholds`）、產品第 5 段之
    `alpha_effective`／`alpha_source`（報告 `filter_log.stage5_thresholds`，`ic_filter_orchestrator.py:5239-5245`）與第 5 段
    輸入數、輸出數（實值；缺 ⇒ None）。"""
    fl = ((report or {}).get("filter_log") or {}) if isinstance(report, Mapping) else {}
    s5 = fl.get("stage5_thresholds") if isinstance(fl.get("stage5_thresholds"), Mapping) else {}
    alpha = s5.get("alpha_effective")
    return {"threshold_branch": str(request.get("threshold_branch") or "default"),
            "threshold_override": dict(request.get("threshold_override") or {}),
            "thresholds": dict(((request.get("config_override") or {}).get("thresholds")) or {}),
            "alpha_effective": float(alpha) if isinstance(alpha, (int, float)) and not isinstance(alpha, bool) else None,
            "alpha_source": s5.get("alpha_source"),
            "stage5_input": _stage_count(fl, "stage5_thresholds", "input_features"),
            "stage5_output": _stage_count(fl, "stage5_thresholds", "output_features"),
            "threshold_basis": EVENT_AXIS_THRESHOLD_BASIS}


def relaxed_identity(n_cols: int, rows: Optional[int] = None) -> Dict[str, Any]:
    """非預設門檻分支之存檔身分（SPEC v5.52 (a) 同法）：L 格 run manifest 之路徑／大小／內容 sha256、請求之欄（seeded 巢狀，
    SPEC v5.56 (m)）之 sha256 與選欄規則、欄數、列長、門檻覆寫、列數軸視窗覆寫（rows 軸）；任一不同 ⇒ 不沿用。"""
    request = relaxed_request(n_cols, rows)
    manifest = REPO / request["run_dir"] / "feature_manifest.json"
    names = list(request["feature_filter"]["include_features"])
    return {"schema": SUBSET_IDENTITY_SCHEMA, "kind": "relaxed_threshold_run", "source": _rel(manifest),
            "source_size": int(manifest.stat().st_size), "source_sha256": file_sha256(manifest),
            "n_cols": int(n_cols), "rows": None if rows is None else int(rows),
            "columns_sha256": hashlib.sha256(json.dumps(names, ensure_ascii=False).encode("utf-8")).hexdigest(),
            "column_rule": REQUEST_COLUMN_RULE, "thresholds": dict(RELAXED_THRESHOLDS),
            "row_windows": ROW_AXIS_WINDOW_OVERRIDE if rows is not None else None}


def _stage_count(fl: Mapping[str, Any], stage: str, key: str) -> Optional[int]:
    """filter_log 之段計數（`output_features` 可為 int 或 {"count": int}）；缺 ⇒ None。"""
    v = (fl.get(stage) or {}).get(key) if isinstance(fl.get(stage), Mapping) else None
    if isinstance(v, Mapping):
        v = v.get("count")
    return int(v) if isinstance(v, int) and not isinstance(v, bool) else None


def relaxed_facts(report: Any, survivors: int) -> Dict[str, Any]:
    """非預設門檻分支之路徑事實（SPEC v5.55 (d)：分別記實值，不以目標值充數）：第 5 段輸入數與通過數、第 6 段輸入數與輸出數、
    去冗餘（含多元化約束）後之存活數（`get_filtered_features` 之欄數）。第 6 段輸入數 ≠ 第 5 段通過數 ⇒ HarnessError（兩者
    同一集合，`ic_filter_orchestrator.py:5362-5366`）。"""
    fl = (report or {}).get("filter_log") or {} if isinstance(report, Mapping) else {}
    out = {"threshold_branch": "non_default", "threshold_override": dict(RELAXED_THRESHOLDS),
           "stage5_input": _stage_count(fl, "stage5_thresholds", "input_features"),
           "stage5_passed": _stage_count(fl, "stage5_thresholds", "output_features"),
           "stage6_input": _stage_count(fl, "stage6_redundancy", "input_features"),
           "stage6_output": _stage_count(fl, "stage6_redundancy", "output_features"),
           "survivors": int(survivors)}
    if out["stage5_passed"] is not None and out["stage6_input"] is not None and out["stage5_passed"] != out["stage6_input"]:
        raise HarnessError(f"ic_page_relaxed：第 5 段通過數 {out['stage5_passed']} ≠ 第 6 段輸入數 {out['stage6_input']}")
    return out


def post_ic_survivors_dir(out_root: Path, n_cols: int) -> Path:
    """IC 後轉換 survivors 軸之存檔輸入目錄：`<out-root>/POST_IC_SURVIVORS_DIR/RL<N>/`。"""
    return Path(out_root) / POST_IC_SURVIVORS_DIR / f"RL{int(n_cols)}"


def save_post_ic_task(out_root: Path, n_cols: int, task_id: str, info: Mapping[str, Any], survivors: Sequence[str],
                      request: Mapping[str, Any], facts: Mapping[str, Any]) -> Path:
    """存 ic_page_relaxed cols 點之真實 IC 任務（同 `prepare_post_ic_rows` 之存法：`req_*`、`result`、status、倖存欄、請求）
    於 `post_ic_survivors_dir`，身分 sidecar＝`relaxed_identity(N)`（加 survivors 數）。倖存欄為空 ⇒ 不存（呼叫端已拋）。"""
    import pickle

    d = post_ic_survivors_dir(out_root, n_cols)
    want = relaxed_identity(n_cols, None)
    task_info = {k: v for k, v in info.items() if str(k).startswith("req_")}
    task_info.update(status=info.get("status"), result=info.get("result"))
    payload = {"task_id": str(task_id), "task_info": task_info, "survivors": [str(c) for c in survivors],
               "request": dict(request), "head": _git_head(), "identity": want, "facts": dict(facts)}
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / (POST_IC_ROWS_FILE + ".part")
    with open(tmp, "wb") as fh:
        pickle.dump(payload, fh, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, d / POST_IC_ROWS_FILE)
    write_identity(d / SUBSET_IDENTITY_FILE, {**want, "survivors": len(survivors)})
    return d


def load_post_ic_task(out_root: Path, n_cols: int) -> Dict[str, Any]:
    """讀 survivors 軸之存檔 IC 任務；身分 sidecar 須等於現行 `relaxed_identity(N)`（加 survivors 數），否則 HarnessError
    （須先跑 `ic_page_relaxed --axis cols --scale N`）。"""
    import pickle

    d = post_ic_survivors_dir(out_root, n_cols)
    side = read_identity(d / SUBSET_IDENTITY_FILE) or {}
    want = json.loads(json.dumps(relaxed_identity(n_cols, None)))
    if not (d / POST_IC_ROWS_FILE).is_file() or {k: side.get(k) for k in want} != want:
        raise HarnessError(f"post_ic_transform survivors 軸之存檔 IC 任務不存在或身分與現行來源不符：{d}（先跑 "
                           f"`icperf_scale_harness.py run ic_page_relaxed --axis cols --scale {n_cols}`）")
    with open(d / POST_IC_ROWS_FILE, "rb") as fh:
        saved = pickle.load(fh)
    if len(saved.get("survivors") or []) != int(side.get("survivors") or -1):
        raise HarnessError(f"{d}：存檔倖存欄數與身分 sidecar 不符")
    return saved


def post_ic_survivor_scales(out_root: Path, cols_scales: Sequence[int] = SCALE_POINTS) -> Dict[str, Any]:
    """SPEC v5.55 (e)：survivors 軸三點＝ic_page_relaxed 各 cols 點（`cols_scales`）實跑存下之 IC 任務之實際倖存欄數（秒級；
    只讀 sidecar 與存檔）。任一點缺存檔、倖存欄為 0、或三點不互異 ⇒ `ok` False（不以目標值充數；須補資料或可達設定後再量）。
    回 {"ok", "scales"（遞增）, "by_cols": {N: 倖存數}, "reason"}。"""
    by: Dict[int, int] = {}
    reason = None
    for n in cols_scales:
        try:
            by[int(n)] = len(load_post_ic_task(out_root, int(n))["survivors"])
        except HarnessError as exc:
            reason = str(exc)
            break
    vals = [by[n] for n in sorted(by)]
    if reason is None and (len(vals) != len(list(cols_scales)) or 0 in vals or len(set(vals)) != len(vals)):
        reason = f"survivors 三點須皆 > 0 且互異：{by}"
    return {"ok": reason is None, "scales": sorted(vals) if reason is None else [], "by_cols": by, "reason": reason}


def _survivor_task_for(out_root: Path, n_survivors: int, cols_scales: Sequence[int] = SCALE_POINTS) -> Dict[str, Any]:
    """survivors 軸規模點 ⇒ 其倖存欄數恰為 `n_survivors` 之存檔 IC 任務（唯一；否則 HarnessError）。"""
    hit = []
    for n in cols_scales:
        try:
            saved = load_post_ic_task(out_root, int(n))
        except HarnessError:
            continue
        if len(saved["survivors"]) == int(n_survivors):
            hit.append((int(n), saved))
    if len(hit) != 1:
        raise HarnessError(f"survivors 軸 {n_survivors}：存檔 IC 任務中倖存欄數相符者 {len(hit)} 份（須恰一份；先跑 "
                           "ic_page_relaxed cols 三點）")
    return {"cols": hit[0][0], **hit[0][1]}


def _tail_feature_library(svc: Any, rows: int, seen: Dict[str, int]) -> None:
    """本服務實例之 `FeatureLibrary.load_with_identity` 回傳取末 `rows` 列（rows 軸：run 載入後截短，同 `_truncate_rows` 之
    末 R 列語意；身分不變）；`seen` 記來源與截短後列數。不改產品碼（只換本實例之屬性）。"""
    lib = svc._feature_library
    orig = lib.load_with_identity

    def tail(*args: Any, **kwargs: Any) -> Any:
        df, identity = orig(*args, **kwargs)
        if len(df) < int(rows):
            raise HarnessError(f"rows {rows} > run 列數 {len(df)}（資料不足）")
        out = df.iloc[-int(rows):]
        seen.update(source_rows=int(len(df)), rows=int(len(out)))
        return out, identity

    lib.load_with_identity = tail


def _run_ic_page_relaxed(ctx: RunContext) -> Dict[str, Any]:
    """SPEC v5.55 (d)：非預設門檻之 IC 頁路徑——`relaxed_request` 經服務 `start_analysis`（IC 頁之服務路徑，同
    post_ic_transform 舊 cols 軸／`prepare_post_ic_rows`）；rows 軸以 `_tail_feature_library` 取 run 之末 R 列。第 6 段輸入
    或倖存欄為 0 ⇒ HarnessError（非預設門檻仍零通過 ⇒ 補資料或可達設定後再量，不寫 0 呼叫之紀錄）。cols 軸另存 IC 任務供
    survivors 軸（`save_post_ic_task`）。"""
    fb = _fb()
    request = relaxed_request(ctx.n_cols, ctx.n_rows)
    svc = _service_with_tasks(request, ctx.work / "registry.json")
    seen: Dict[str, int] = {}
    if ctx.n_rows is not None:
        _tail_feature_library(svc, int(ctx.n_rows), seen)
    task_id, info = _service_analysis(svc, fb._ic_analyze_request(request), ctx.rec)
    analyzer, report = info["analyzer"], info.get("result")
    try:
        survivors = [str(c) for c in analyzer.get_filtered_features().columns]
    except Exception:  # noqa: BLE001 — 無倖存 frame ⇒ 空
        survivors = []
    facts = relaxed_facts(report, len(survivors))
    if not facts["stage6_input"] or not survivors:
        raise HarnessError(f"ic_page_relaxed {ctx.axis}={ctx.scale}：非預設門檻下第 6 段輸入 {facts['stage6_input']}、倖存 "
                           f"{len(survivors)}（仍零通過；須補資料或可達設定，SPEC v5.55 (d)）")
    names = list(request["feature_filter"]["include_features"])
    rows = seen.get("rows") if ctx.n_rows is not None else _manifest_rows(request)
    out = {**facts, "input_cols": ctx.n_cols, "rows": rows, "source_rows": seen.get("source_rows"),
           **_split_facts_from_cache(analyzer, report), "stage_counts": _ic_facts(report, analyzer, ctx.n_cols, int(rows or 0))["stage_counts"],
           "requested_columns": names, "actual_scale": seen.get("rows") if ctx.n_rows is not None else len(set(names)),
           # SPEC v5.56 (m)：選欄規則（seeded 巢狀）與請求欄之指標家族分佈
           "column_rule": REQUEST_COLUMN_RULE, "requested_family_distribution": family_distribution(names)}
    if ctx.axis == "cols":
        out["post_ic_task"] = _rel(save_post_ic_task(ctx.out_root, ctx.n_cols, task_id, info, survivors, request, facts))
    return out


def _run_post_ic_transform(ctx: RunContext) -> Dict[str, Any]:
    """survivors 軸（SPEC v5.55 (e)，主軸）：ic_page_relaxed cols 點存下之真實 IC 任務（倖存欄數＝宣告之規模，
    `_survivor_task_for`）放入新服務之任務表後直接呼叫 `_apply_transforms_sync`（該任務之倖存欄、同一參數；不重跑 IC）。
    rows 軸（SPEC v5.52 (b)）：L 格存檔之 IC 任務（`load_post_ic_rows`）放入新服務之任務表，`_load_features_for_transforms`
    之回傳取末 R 列（實際列數驗等於 R）後直接呼叫 `_apply_transforms_sync`（同一倖存欄、同一參數）。"""
    if ctx.axis == "survivors":
        saved = _survivor_task_for(ctx.out_root, int(ctx.n_survivors or 0))
        request = saved["request"]
        svc = _service_with_tasks(request, ctx.work / "registry.json")
        task_id = str(saved["task_id"])
        svc._tasks[task_id] = dict(saved["task_info"])
        survivors = list(saved["survivors"])
        res = svc._apply_transforms_sync(task_id, survivors, *POST_IC_ARGS)
        chunked = post_ic_chunked_probe(ctx.rec, lambda: svc._apply_transforms_sync(task_id, survivors, *POST_IC_ARGS),
                                        len(survivors))
        return {"input_cols": int(saved["cols"]), "rows": int(res.get("output_rows") or 0), "survivors": len(survivors),
                "transformed_cols": res.get("output_cols"), "excluded_features": len(res.get("excluded_features") or []),
                "threshold_branch": "non_default", "source_task_cols": int(saved["cols"]),
                "requested_columns": list(request["feature_filter"]["include_features"]), "actual_scale": len(survivors),
                "chunked_probe": chunked}
    if ctx.axis == "rows":
        saved = load_post_ic_rows(ctx.out_root)
        request = saved["request"]
        svc = _service_with_tasks(request, ctx.work / "registry.json")
        task_id = str(saved["task_id"])
        svc._tasks[task_id] = dict(saved["task_info"])
        orig = svc._load_features_for_transforms
        seen: Dict[str, int] = {}

        def tail(*args: Any, **kwargs: Any) -> Any:
            df, identity = orig(*args, **kwargs)
            if len(df) < int(ctx.n_rows or 0):
                raise HarnessError(f"post_ic_transform rows {ctx.n_rows} > L 格 run 列數 {len(df)}（資料不足）")
            out = df.iloc[-int(ctx.n_rows or 0):]
            seen.update(source_rows=int(len(df)), rows=int(len(out)))
            return out, identity

        svc._load_features_for_transforms = tail
        survivors = list(saved["survivors"])
        svc._apply_transforms_sync(task_id, survivors, *POST_IC_ARGS)
        chunked = post_ic_chunked_probe(ctx.rec, lambda: svc._apply_transforms_sync(task_id, survivors, *POST_IC_ARGS),
                                        len(survivors))
        return {"input_cols": ROW_AXIS_COLS, "rows": seen.get("rows"), "source_rows": seen.get("source_rows"),
                "survivors": len(survivors), "requested_columns": list(request["feature_filter"]["include_features"]),
                "threshold_branch": saved.get("threshold_branch", "default"), "actual_scale": seen.get("rows"),
                "chunked_probe": chunked}
    raise HarnessError(f"post_ic_transform 不支援 {ctx.axis} 軸（SPEC v5.55 (e)：主軸 survivors、第二軸 rows）")


def _run_event_import(ctx: RunContext) -> Dict[str, Any]:
    from api.services.case_import_service import EventImportService

    from api.routes.ic_analysis import _resolve_event_batch

    fb = _fb()
    # SPEC v5.57 (q)：事件數軸走非預設門檻之產品完整路徑（`relaxed_event_request`：只覆寫 p_value_max；與預檢同一請求）；
    # cols／rows 軸維持事件匯入預設請求
    request = (relaxed_event_request(ctx.n_cols) if ctx.axis == "events"
               else _limited_request("event_import_report", None, ctx.n_cols))
    store = EventImportService()
    records: Optional[List[Dict[str, Any]]] = None
    if ctx.axis in ("events", "rows"):
        # SPEC v5.52 (b)：事件數軸——同一明列規則之事件批（`icperf_event_batch`，依 t0 排序之前 {scale} 筆）匯入本次工作目錄之
        # 隔離儲存根（不寫 repo 之 data_cache/events），route `_resolve_event_batch` 經 `get_event_import_service()` 讀之
        # ⇒ 本行程內把該單例指向隔離儲存根；欄數固定 ROW_AXIS_COLS（RunContext）。SPEC v5.53 (c0)：K 線根數軸＝同法匯入
        # 全部事件（事件數固定），K 線讀隔離截短複本（`event_bars_context`）
        import api.services.case_import_service as cis

        # SPEC v5.56 (n)：事件數軸＝Task 0.2 專用批之等距抽樣（`_event_axis_records`）；K 線根數軸＝凍結規則之全部事件
        records = (_event_axis_records(int(ctx.n_events or 0)) if ctx.axis == "events" else _event_batch_records(None))
        store = EventImportService(storage_dir=ctx.work / "events")
        upload = json.dumps(records, ensure_ascii=False, sort_keys=True).encode("utf-8")
        resp = store.import_records(records, source_name="icperf-t02-event-import", upload_bytes=upload,
                                    validate_only=False)
        cis._event_import_service = store
        request = {**request, "event_import_id": str(resp.import_id)}
    # 同 `icperf_freeze_baseline.event_import_run`（route `_resolve_event_batch`＋服務 `start_analysis`），另接進度通知
    with event_bars_context(ctx, records) as bars:
        svc = _service_with_tasks(request, ctx.work / "registry.json")
        req = fb._ic_analyze_request(request)
        _task_id, info = _service_analysis(svc, req, ctx.rec, event_batch=_resolve_event_batch(req))
    analyzer = info.get("analyzer")
    detail = store.get_import(str(request["event_import_id"]))
    facts = _ic_facts(info.get("result"), analyzer, ctx.n_cols, _manifest_rows(request))
    events = len(detail.records) if detail is not None else None
    names = list(request["feature_filter"]["include_features"])
    actual = events if ctx.axis == "events" else len(set(names))
    if ctx.axis == "rows":
        actual = bars_actual(bars, int(ctx.n_rows or 0))
        facts.update(bars_facts(bars))
    # SPEC v5.58 (x)：各軸皆記第 5 段事實——survivors＝第 5 段倖存數（事件入口 unit_axis／scale_vector 之 survivors；第 6–7 段後
    # 之數另記 final_survivors）、二元收據（置換前門檻通過數、n_perm、區塊數、負對照狀態）與 post_stage5_claim（第 5 段倖存 0
    # 或負對照未實算 ⇒ 該點不得宣稱後續統計有實值）。SPEC v5.57 (q)：events 軸之實際門檻設定與第 5 段實值同出於此
    facts.update(event_stage5_facts(request, info.get("result"), getattr(ctx, "binary_capture", None),
                                    final_survivors=facts.get("survivors")))
    if ctx.axis == "events":
        facts.update(event_axis_facts())
        # SPEC v5.57 (q)：二元三入口之本點呼叫數（扣例外）；任一入口 0 呼叫 ⇒ HarnessError（非預設門檻仍無通過欄 ⇒ 補資料或
        # 可達設定後再量，不寫 0 呼叫之紀錄；同 ic_page_relaxed）
        calls = {eid: int(ctx.rec.stat(eid).calls) - int(ctx.rec.stat(eid).raised) for eid in EVENT_BINARY_ENTRIES}
        facts["binary_calls"] = calls
        zero = [eid for eid, c in calls.items() if c < 1]
        if zero:
            raise HarnessError(f"event_import events={ctx.scale}：非預設門檻下二元入口 0 呼叫 {zero}（第 5 段輸出 "
                               f"{facts.get('stage5_output')}；SPEC v5.57 (q)）")
    return {**facts, "events": events, "requested_columns": names, "actual_scale": actual}


def event_axis_facts() -> Dict[str, Any]:
    """事件數軸紀錄之批與抽樣規則（SPEC v5.56 (n)）。"""
    eb = _load_script("icperf_t02_event_batch", "scripts/icperf_event_batch.py")
    return {"event_rule": eb.rule_id(EVENT_AXIS_BREAKOUT_BARS, EVENT_AXIS_PRIOR_FIELD),
            "event_batch_size": len(_event_axis_batch()),
            "event_sampling": EVENT_AXIS_SAMPLING}


def _event_batch_records(n_events: Optional[int]) -> List[Dict[str, Any]]:
    """凍結批同一規則（`icperf_event_batch.BREAKOUT_BARS`）之事件（依 t0 排序；`n_events` 給定 ⇒ 前 n 筆）——K 線根數軸
    （v5.53 (c0)，全部事件固定）用之。事件數軸改用 `_event_axis_records`（SPEC v5.56 (n)）。"""
    eb = _load_script("icperf_t02_event_batch", "scripts/icperf_event_batch.py")
    records = sorted(eb.build_records(eb._cell_window())["records"], key=lambda r: int(r["t0"]))
    if n_events is not None:
        if n_events > len(records):
            raise HarnessError(f"event_study：events 軸 {n_events} > 批之事件數 {len(records)}（資料不足）")
        records = records[:n_events]
    return records


#: SPEC v5.56 (n)：事件數軸之 Task 0.2 專用事件批——同一 L 格窗（L 格 run 之 2,000 根特徵列；事件須落在特徵列上）、規則族
#: 「close > 前 N 根 `prior_field` 最大值」（凍結批＝high、N＝6、203 筆）取較密之規則（`icperf_event_batch.build_records(
#: breakout_bars=N, prior_field=...)`；只於量測之隔離儲存根匯入，不寫 `data_cache/events`、不覆蓋凍結批 `EVENT_IMPORT_ID`）
EVENT_AXIS_BREAKOUT_BARS = 2
EVENT_AXIS_PRIOR_FIELD = "close"
EVENT_AXIS_RULE_BASIS = ("2026-11-01 實測（runs/icperf/task02/smoke/count_event_rule_v556.py，L 格窗 2,000 根）：窗末 20% 根內"
                         "事件約占 18–20%，min_test_events 30 ⇒ 等距抽樣之最小可達約 150–165 筆；high 基準之同族最密 N＝1 只"
                         " 462 筆（跨度約 2.8 倍）⇒ 改 close 基準：N＝1 997 筆、N＝2 737 筆、N＝3 608 筆——取達約 4 倍設計目標之"
                         "最疏者 N＝2（737 筆、兩類 368／369）；三點與實際跨度以 precheck-events 實測為準。L 格 run 之特徵只 2,000 "
                         "列（標籤來源主檔 4h 只 5,088 根），更長歷史之事件無特徵列可對齊，故不以延長 K 線歷史補（另產更長 L 格 run "
                         "屬重型生成，未估時不跑）")
EVENT_AXIS_SAMPLING = "等距抽樣：依 t0 排序之全批取 round(linspace(0, K−1, n)) 之位置（含首末；保留 train／test 比例）"


def event_axis_subset(records: Sequence[Mapping[str, Any]], n: int) -> List[Dict[str, Any]]:
    """SPEC v5.56 (n)：依 t0 排序之 `records`（K 筆）之 n 筆等距抽樣——位置 `round(linspace(0, K−1, n))`（n ≥ 2 時含首末；
    相鄰間距 (K−1)/(n−1) ≥ 1 ⇒ 位置互異）；train／test 之事件比例隨抽樣保留（測試段為時間末段）。n 不在 [1, K] ⇒
    HarnessError。"""
    import numpy as np

    ordered = sorted((dict(r) for r in records), key=lambda r: int(r["t0"]))
    k = len(ordered)
    if not 1 <= int(n) <= k:
        raise HarnessError(f"事件數軸：n={n} 不在 [1, {k}]（批之事件數；資料不足）")
    if int(n) == 1:
        return [ordered[0]]
    pos = np.rint(np.linspace(0, k - 1, int(n))).astype(int)
    if len(set(pos.tolist())) != int(n):
        raise HarnessError(f"事件數軸：等距抽樣位置重複（n={n}, K={k}）")
    return [ordered[int(i)] for i in pos]


_EVENT_AXIS_BATCH: Optional[List[Dict[str, Any]]] = None


def _event_axis_batch() -> List[Dict[str, Any]]:
    """SPEC v5.56 (n)：Task 0.2 事件數軸專用批（`EVENT_AXIS_BREAKOUT_BARS`、`EVENT_AXIS_PRIOR_FIELD`；依 t0 排序；行程內記憶）。"""
    global _EVENT_AXIS_BATCH
    if _EVENT_AXIS_BATCH is None:
        eb = _load_script("icperf_t02_event_batch", "scripts/icperf_event_batch.py")
        built = eb.build_records(eb._cell_window(), breakout_bars=EVENT_AXIS_BREAKOUT_BARS,
                                 prior_field=EVENT_AXIS_PRIOR_FIELD)
        _EVENT_AXIS_BATCH = sorted(built["records"], key=lambda r: int(r["t0"]))
    return [dict(r) for r in _EVENT_AXIS_BATCH]


def _event_axis_records(n_events: int) -> List[Dict[str, Any]]:
    """事件數軸之 n 筆（SPEC v5.56 (n)）：`_event_axis_batch` 之 `event_axis_subset`。"""
    return event_axis_subset(_event_axis_batch(), int(n_events))


# ── SPEC v5.55 (g2)：事件數軸三點之秒級切分預檢 ──────────────────────────────────────────────────────────────


#: 事件數軸預檢之工作子目錄（`<out-root>/work/` 下；隔離之事件儲存根與 cwd，不寫 repo 之 data_cache/events）
EVENT_PRECHECK_TAG = "precheck-events"


def _event_import_batch(records: Sequence[Mapping[str, Any]], store_dir: Path, request: Mapping[str, Any]
                        ) -> Tuple[Any, Dict[str, Any], Dict[str, Any]]:
    """同 `_run_event_import` 之事件數軸：`records` 匯入隔離儲存根 `store_dir`（`EventImportService(storage_dir=...)`），
    本行程內把 route 所讀之單例指向之，經 route `_resolve_event_batch` 取批（產品之同一取得點）。回 (ICAnalyzeRequest,
    事件批 dict, 請求記錄〔含 event_import_id〕)。"""
    import api.services.case_import_service as cis
    from api.routes.ic_analysis import _resolve_event_batch
    from api.services.case_import_service import EventImportService

    fb = _fb()
    store = EventImportService(storage_dir=Path(store_dir))
    upload = json.dumps(list(records), ensure_ascii=False, sort_keys=True).encode("utf-8")
    resp = store.import_records(list(records), source_name="icperf-t02-event-precheck", upload_bytes=upload,
                                validate_only=False)
    cis._event_import_service = store
    req_rec = {**dict(request), "event_import_id": str(resp.import_id)}
    req = fb._ic_analyze_request(req_rec)
    return req, _resolve_event_batch(req), req_rec


def event_split_counts(staged: Mapping[str, Any], request: Mapping[str, Any], manifest: Path,
                       event_keys: Optional[Iterable[int]] = None, *,
                       plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """事件路徑之樣本外切分（秒級，不跑 IC）：直接呼叫產品之同一組函式——服務 `_build_config_override`（經
    `icperf_freeze_baseline._override_for`）並依 `ic_analysis_service.py:1898-1907` 把 embargo 抬至 `lookahead_depth_rows`；
    `ic_filter_orchestrator.py:1539-1553` 之 purge＝max(effective horizon, `label_window_rows`)、`_build_holdout_split_plan`
    （時間軸＝run 之 post-trim 特徵索引〔`create_post_trim_index_loader`，同 `_run_event_label_stages` 之處置帳〕）；
    測試段事件數＝事件列鍵（`staged["event_timestamps"]`；`event_keys` 給定 ⇒ 只計其子集）落在測試段時間戳者
    （`ic_filter_orchestrator.py:1746-1748`：stage3 後之事件列 ∩ 測試段）；兩類於測試段之數（`_resolve_label_mode_and_bind_binary`
    之 `sel_counts`，`:4644-4655`）。回 {"oos"（測試段事件數 ≥ `min_test_events`，`:1765-1766`）, "binary"（兩類各 ≥
    `min_events_per_class`，`:4657-4670`）, "train_events", "test_events", "test_pos", "test_neg", "min_test_events",
    "min_events_per_class", "purge_rows", "embargo_rows", "split_reason"}。

    SPEC v5.56 (j)：兩類計數改經產品之同一計數函式 `momentum.core.split_preview.count_binary_classes_in_rows`（產品切分
    預覽 `ic_filter_orchestrator.py:1604` 與 stage3 `:4653` 同用；本預檢以 run 之 post-trim 特徵索引〔DatetimeIndex，
    毫秒換算由該函式 `:392-393` 做〕之測試段／訓練段列位置呼叫）；另記訓練段兩類數（`train_pos`／`train_neg`）。切分
    計畫（設定、purge、embargo、`_build_holdout_split_plan` 之結果）依 (manifest, 請求 override, lookahead_depth_rows,
    label_window_rows) 記憶（`plan` 給定則直接用；同一批之子集逐 n 計數不重建）。產品實際之 effective mode 與二元三入口
    呼叫另由 `event_point_product_check` 以產品實跑驗（本函式之計數為時鐘一致之期望值）。"""
    import numpy as np

    from momentum.core.split_preview import count_binary_classes_in_rows

    plan = plan if plan is not None else event_split_plan(staged, request, manifest)
    keys = set(int(k) for k in (staged["event_timestamps"] if event_keys is None else event_keys))
    binary_all = {int(k): int(v) for k, v in (staged.get("event_binary_labels") or {}).items()}
    out: Dict[str, Any] = {"min_test_events": plan["min_test_events"], "min_events_per_class": plan["min_events_per_class"],
                           "purge_rows": plan["purge_rows"], "embargo_rows": plan["embargo_rows"], "n_events": len(keys),
                           "oos": False, "binary": False, "train_events": None, "test_events": None, "test_pos": None,
                           "test_neg": None, "train_pos": None, "train_neg": None, "split_reason": plan["split_reason"],
                           "count_function": "momentum.core.split_preview:count_binary_classes_in_rows"}
    if plan["split_reason"] is not None:
        return out
    ms = plan["ms"]
    test_rows, train_rows = plan["test_rows"], plan["train_rows"]
    test_keys = keys & set(int(x) for x in ms[test_rows])
    train_keys = keys & set(int(x) for x in ms[train_rows])
    binary = {k: v for k, v in binary_all.items() if k in keys} if staged.get("event_binary_labels") is not None else None
    test_cls = count_binary_classes_in_rows(binary, plan["index"], np.asarray(test_rows, dtype=int)) \
        or {"n_pos": 0, "n_neg": 0}
    train_cls = count_binary_classes_in_rows(binary, plan["index"], np.asarray(train_rows, dtype=int)) \
        or {"n_pos": 0, "n_neg": 0}
    out.update(train_events=len(train_keys), test_events=len(test_keys), test_pos=int(test_cls["n_pos"]),
               test_neg=int(test_cls["n_neg"]), train_pos=int(train_cls["n_pos"]), train_neg=int(train_cls["n_neg"]))
    out["oos"] = bool(len(test_keys) >= out["min_test_events"])
    out["binary"] = bool(min(out["test_pos"], out["test_neg"]) >= out["min_events_per_class"])
    return out


_SPLIT_PLAN_MEMO: Dict[str, Dict[str, Any]] = {}


def event_split_plan(staged: Mapping[str, Any], request: Mapping[str, Any], manifest: Path) -> Dict[str, Any]:
    """`event_split_counts` 之切分計畫（產品同一組函式，見其說明；秒級）：回 {"index"（post-trim 特徵索引之
    DatetimeIndex）, "ms"（其 epoch 毫秒）, "test_rows", "train_rows"（`_build_holdout_split_plan` 之列位置）,
    "min_test_events", "min_events_per_class", "purge_rows", "embargo_rows", "split_reason"}；依 (manifest, override,
    lookahead_depth_rows, label_window_rows) 記憶。"""
    import pandas as pd

    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from momentum.Analysis import ic_filter_orchestrator as orch
    from momentum.factories import create_ic_analyzer, create_post_trim_index_loader

    fb = _fb()
    override = dict(fb._override_for(request) or {})
    override["embargo"] = max(int(override.get("embargo") or 0), int(staged["lookahead_depth_rows"]))
    memo_key = hashlib.sha256(json.dumps([str(Path(manifest).resolve()), override, int(staged["label_window_rows"]),
                                          str(request["symbol"]), str(request["timeframe"])],
                                         sort_keys=True, default=str).encode("utf-8")).hexdigest()
    if memo_key in _SPLIT_PLAN_MEMO:
        return _SPLIT_PLAN_MEMO[memo_key]
    analyzer = create_ic_analyzer(override)
    config = analyzer._apply_tier_config(analyzer._apply_config_override(override))
    horizon = int(orch._resolve_effective_label_horizon(config, None))
    purge = max(horizon, int(staged["label_window_rows"]))
    idx_ns = create_post_trim_index_loader()(Path(manifest).parent)
    index = pd.DatetimeIndex(pd.to_datetime(pd.Index(idx_ns).astype("int64"), unit="ns"))
    plan: Dict[str, Any] = {"index": index, "ms": (index.asi8 // 10 ** 6).astype("int64"), "test_rows": None,
                            "train_rows": None, "min_test_events": int(config.event_filter.min_test_events),
                            "min_events_per_class": int(config.event_filter.min_events_per_class),
                            "purge_rows": purge, "embargo_rows": int(override["embargo"]), "split_reason": None}
    if not config.ic_train_test_split:
        plan["split_reason"] = "split_disabled"
    else:
        freq = orch._resolve_expected_freq({"timeframe": str(request["timeframe"])})
        split = orch._build_holdout_split_plan(pd.DataFrame(index=index), config, str(request["symbol"]), freq,
                                               purge_gap=purge, labels_df=None)
        if isinstance(split, orch.SkippedResult):
            plan["split_reason"] = "insufficient_data"
        else:
            train_plan, test_plan = split
            plan.update(test_rows=list(int(x) for x in test_plan.row_index),
                        train_rows=list(int(x) for x in train_plan.row_index))
    _SPLIT_PLAN_MEMO[memo_key] = plan
    return plan


#: SPEC v5.56 (j)：事件匯入二元三入口（匯入 0/1 標籤模式才呼叫；`ic_filter_orchestrator.py` stage5 二元分支）與產品之
#: effective mode 決策點（`_resolve_label_mode_and_bind_binary`，`:4610`；回傳 info["label_mode"]）
EVENT_BINARY_ENTRIES: Tuple[str, ...] = (
    "momentum.Analysis.binary_discrimination:mann_whitney_table",
    "momentum.Analysis.binary_discrimination:block_permutation_table",
    "momentum.Analysis.ic_filter_orchestrator:ICFilterOrchestrator._run_binary_permutation_and_negative_control",
)
EVENT_LABEL_MODE_ENTRY = "momentum.Analysis.ic_filter_orchestrator:ICFilterOrchestrator._resolve_label_mode_and_bind_binary"

# ── SPEC v5.58 (x)（code review r69 群集 C）：mann_whitney_table 之單位軸含倖存數、固定倖存集合之直接呼叫格 ─────────────

#: 二元三入口之個別名（`EVENT_BINARY_ENTRIES` 同序）
MW_ENTRY = EVENT_BINARY_ENTRIES[0]
BINARY_PERM_ENTRY = EVENT_BINARY_ENTRIES[2]
#: 固定倖存集合之直接呼叫格（`CELLS`；events 軸）與其所隔離之清冊入口（入口 id ⇒ (run_id, 軸)）：組裝另組 `isolation` 段，
#: 不參與 `entry_runs` 之主軸／第二軸、不取代端到端之 events 與倖存數雙軸
MW_FIXED_CELL = "mann_whitney_fixed_survivors"
ISOLATION_RUNS: Dict[str, Tuple[str, str]] = {MW_ENTRY: (MW_FIXED_CELL, "events")}
#: event_import events 軸各點之存檔（`<out-root>/EVENT_MW_DIR/E<n>/`）：mann_whitney_table 首次呼叫（主統計，
#: `ic_filter_orchestrator.py:5976`：features_for_stats＝第 5 段全部輸入欄之測試段事件列、y＝驗過之 0/1、min_class_n）之 pickle，
#: 與第 5 段二元收據（`_run_binary_permutation_and_negative_control` 之 passed／倖存者／收據）之 JSON
EVENT_MW_DIR = "stage_inputs/event_mw"
EVENT_MW_CAPTURE = "mann_whitney"
EVENT_MW_STAGE5_FILE = "stage5.json"
#: 直接呼叫格每點之呼叫次數（固定；每點同次數 ⇒ 秒數之比＝單次成本之比）。依據：產品置換迴圈每點至少 200 次
#: mann_whitney_table（n_perm＝min(1000, max(200, …))，`ic_filter_orchestrator.py:5789`）；單次為毫秒級（測試段事件數十至百餘列），
#: 重複以壓低計時解析度之相對誤差。不依耗時增減
MW_FIXED_CALLS = 200
#: 第 5 段倖存數相依入口於 events 軸不擬合之依據（組裝 `row_fit_excluded`）
EVENTS_FIT_EXCLUDED_BASIS = ("SPEC v5.58 (x)：清冊 unit_axis 含 survivors（第 5 段倖存數相依：呼叫數或 inclusive 成本隨第 5 段倖存數變，"
                             "smoke_v557 mann_whitney_table 741／1／925 次對第 5 段輸出 35／0／51）⇒ events 軸只記事件數、倖存數與"
                             "各點呼叫數，不對事件數擬合；單次入口成本見 isolation（固定倖存集合之直接呼叫格）")


def survivor_dependent(e: Mapping[str, Any]) -> bool:
    """SPEC v5.58 (x)：清冊入口是否第 5 段倖存數相依（unit_axis.axes 含 survivors）。"""
    return "survivors" in set((e.get("unit_axis") or {}).get("axes") or [])


def events_fit_exclusion(e: Mapping[str, Any], axis: Optional[str], points: Sequence[Mapping[str, Any]]
                         ) -> Optional[Dict[str, Any]]:
    """SPEC v5.58 (x)：events 軸只擬合確實隨事件數變之入口——`axis`＝"events" 且入口倖存數相依（`survivor_dependent`）⇒ 回
    {"axis", "basis", "points": [{"events", "survivors", "calls", "seconds", "post_stage5_claim", "n_blocks", "threshold_passed"}]}
    （不擬合；端到端保留事件數與倖存數雙軸及各點呼叫數；v5.59 (ai)：另記區塊數與門檻通過數——呼叫數條件 k>0 且 n_blocks ≥ 10
    之兩輸入）；否則 None（照常擬合）。"""
    if axis != "events" or not survivor_dependent(e):
        return None
    return {"axis": "events", "basis": EVENTS_FIT_EXCLUDED_BASIS,
            "points": [{"events": (p.get("scale_vector") or {}).get("events", p.get("events")),
                        "survivors": (p.get("scale_vector") or {}).get("survivors"), "calls": p.get("calls"),
                        "seconds": p.get("seconds"), "post_stage5_claim": p.get("post_stage5_claim"),
                        "n_blocks": p.get("n_blocks"),
                        "threshold_passed": (p.get("binary_receipt") or {}).get("threshold_passed")} for p in points]}


def post_stage5_claim(stage5_output: Optional[int], binary: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """SPEC v5.58 (x)：一點之第 5 段後統計可否宣稱有實值（純函式）。`binary`＝第 5 段二元收據（`binary_receipt_facts`；非二元模式
    ⇒ None）。不成立之條件：第 5 段倖存數 0（第 6–7 段無輸入）、或二元模式之負對照未實算（`negative_control_status`
    ≠ "computed"，如 `unavailable:insufficient_blocks`／`skipped:no_survivors`；`ic_filter_orchestrator.py:5832-5841`）；第 5 段
    倖存數缺 ⇒ 不成立（不猜）。回 {"allowed", "reasons", "stage5_output", "negative_control_status"}。"""
    reasons: List[str] = []
    nc = (binary or {}).get("negative_control_status") if binary is not None else None
    if not isinstance(stage5_output, int) or isinstance(stage5_output, bool):
        reasons.append("第 5 段倖存數缺（filter_log.stage5_thresholds.output_features）")
    elif stage5_output == 0:
        reasons.append("第 5 段倖存數 0：第 6–7 段無輸入，不得宣稱後續統計有實值")
    if binary is not None and nc != "computed":
        reasons.append(f"負對照未實算（{nc}）：不得宣稱負對照與其後之可消費倖存者有實值")
    return {"allowed": not reasons, "reasons": reasons,
            "stage5_output": stage5_output if isinstance(stage5_output, int) else None, "negative_control_status": nc}


def binary_receipt_facts(captured: Optional[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    """SPEC v5.58 (x)：第 5 段二元收據之事實（`binary_capture_hook` 所存；未呼叫 `_run_binary_permutation_and_negative_control`
    〔非二元模式〕⇒ None）：門檻通過數 k（置換前）、置換後倖存數、n_perm、區塊數、負對照狀態（"computed"＝實算，否則產品之
    status 字串）與實算次數——mann_whitney_table 端到端呼叫數之解釋（1＋[k>0 且 n_blocks≥10]·(1＋n_perm)＋負對照次數）。
    SPEC v5.59 (ac)：產品之負對照改固定 `negative_control_n` 次、receipt 刪牆鐘預算降階旗標 ⇒ 本函式不讀該鍵（缺席不報錯）。"""
    if not captured:
        return None
    rec = dict(captured.get("receipt") or {})
    nc = rec.get("negative_control")
    computed = isinstance(nc, Mapping) and "n_observed" in nc
    return {"threshold_passed": len(captured.get("threshold_passed") or []),
            "survivors_after_permutation": len(captured.get("survivors") or []),
            "n_perm": rec.get("n_perm"), "n_blocks": rec.get("n_blocks"), "block_len": rec.get("block_len"),
            "negative_control_status": "computed" if computed else (nc.get("status") if isinstance(nc, Mapping) else None),
            "negative_control_n_effective": nc.get("n_effective") if computed else 0}


def binary_capture_hook(store: Dict[str, Any]) -> Callable[[Tuple[Any, ...], Dict[str, Any], Any], None]:
    """SPEC v5.58 (x)：`_run_binary_permutation_and_negative_control` 之 Recorder capture——依原函式簽名取 `passed`（置換前之門檻
    通過欄）、回傳之倖存者與收據（JSON 化）存入 `store`（不 pickle orchestrator）。簽名於重綁前取（`resolve_target`）。"""
    sig = inspect.signature(resolve_target(BINARY_PERM_ENTRY).func)

    def cap(args: Tuple[Any, ...], kwargs: Dict[str, Any], result: Any) -> None:
        passed = sig.bind(*args, **kwargs).arguments.get("passed") or []
        survivors, receipt = result
        store.update({"threshold_passed": [str(x) for x in passed], "survivors": [str(x) for x in survivors],
                      "receipt": json.loads(json.dumps(receipt or {}, default=str))})

    return cap


def event_mw_dir(out_root: Path, n_events: int) -> Path:
    """event_import events 軸 n 點之存檔目錄（`<out-root>/EVENT_MW_DIR/E<n>/`）。"""
    return Path(out_root) / EVENT_MW_DIR / f"E{int(n_events)}"


def event_mw_identity(n_events: int) -> Dict[str, Any]:
    """SPEC v5.58 (x)：event_import events 軸 n 點存檔之身分（SPEC v5.52 (a) 同法）：L 格 run manifest 之路徑／大小／內容 sha256、
    請求之欄（seeded 巢狀 `ROW_AXIS_COLS` 欄）sha256、事件批規則與該點等距抽樣事件之 sha256、門檻（`relaxed_event_request`）；
    任一不同 ⇒ 不沿用。"""
    eb = _load_script("icperf_t02_event_batch", "scripts/icperf_event_batch.py")
    request = relaxed_event_request(ROW_AXIS_COLS)
    manifest = REPO / request["run_dir"] / "feature_manifest.json"
    names = list(request["feature_filter"]["include_features"])
    recs = _event_axis_records(int(n_events))
    return {"schema": SUBSET_IDENTITY_SCHEMA, "kind": "event_mw_capture", "writer": ["event_import", "events"],
            "events_requested": int(n_events), "source": _rel(manifest), "source_size": int(manifest.stat().st_size),
            "source_sha256": file_sha256(manifest),
            "columns_sha256": hashlib.sha256(json.dumps(names, ensure_ascii=False).encode("utf-8")).hexdigest(),
            "column_rule": REQUEST_COLUMN_RULE,
            "event_rule": eb.rule_id(EVENT_AXIS_BREAKOUT_BARS, EVENT_AXIS_PRIOR_FIELD),
            "records_sha256": hashlib.sha256(json.dumps(recs, ensure_ascii=False, sort_keys=True,
                                                        default=str).encode("utf-8")).hexdigest(),
            "thresholds": dict(request["config_override"]["thresholds"])}


def load_event_mw(out_root: Path, n_events: int) -> Dict[str, Any]:
    """讀 event_import events 軸 n 點之存檔（SPEC v5.58 (x)）：sidecar 須 status complete 且身分逐欄＝`event_mw_identity(n)`、
    兩檔皆列於 files，否則 HarnessError（須先重跑 event_import events 軸該點）。回 {"mw": mann_whitney 首次呼叫之存檔,
    "stage5": 第 5 段二元存檔, "events": 寫出實跑驗得之事件數, "dir"}。"""
    d = event_mw_dir(out_root, n_events)
    want = event_mw_identity(n_events)
    side = read_identity(d / SUBSET_IDENTITY_FILE) or {}
    if side.get("status") != "complete" or {k: side.get(k) for k in want} != json.loads(json.dumps(want)) \
            or not {f"{EVENT_MW_CAPTURE}.pkl", EVENT_MW_STAGE5_FILE} <= set(side.get("files") or []):
        raise HarnessError(f"事件數軸存檔 {_rel(d)} 之身分與現行來源不符或未完成（status={side.get('status')!r}）：須先跑 "
                           f"event_import --axis events --scale {int(n_events)}（SPEC v5.58 (x)）")
    mw = load_capture(d, EVENT_MW_CAPTURE)
    stage5 = json.loads((d / EVENT_MW_STAGE5_FILE).read_text(encoding="utf-8"))
    return {"mw": mw, "stage5": stage5, "events": side.get("events"), "dir": _rel(d)}


def _event_mw_begin(ctx: "RunContext", path_run_id: str) -> Dict[str, Any]:
    """event_import events 軸實跑之存檔開始（run_one 於重綁前呼叫）：sidecar 標 building（中斷 ⇒ 讀端拒收），回
    {"dir", "identity", "writer"（mann_whitney_table 之 capture）}。"""
    d = event_mw_dir(ctx.out_root, int(ctx.n_events or 0))
    want = event_mw_identity(int(ctx.n_events or 0))
    write_identity(d / SUBSET_IDENTITY_FILE, {**want, "status": "building", "path_run_id": path_run_id})
    prov = {"path_run_id": path_run_id, "head": ctx.head, "axis": ctx.axis, "scale": int(ctx.scale), "run_id": ctx.run_id}
    return {"dir": d, "identity": want, "writer": _capture_writer(d, EVENT_MW_CAPTURE, False, prov, overwrite=True)}


def _event_mw_finish(state: Mapping[str, Any], ctx: "RunContext", facts: Mapping[str, Any]) -> None:
    """event_import events 軸實跑成功（actual_scale 已驗）後：寫第 5 段二元存檔並把 sidecar 標 complete（記驗得之事件數）；
    mann_whitney 首次呼叫未存成或無二元收據 ⇒ 標 failed（讀端拒收，直接呼叫格大聲失敗）。"""
    d = Path(state["dir"])
    st = ctx.rec.stat(MW_ENTRY)
    binary = getattr(ctx, "binary_capture", None) or {}
    ok = bool(st.captured and st.capture_error is None and (d / f"{EVENT_MW_CAPTURE}.pkl").is_file() and binary)
    files: List[str] = [f"{EVENT_MW_CAPTURE}.pkl"] if ok else []
    if ok:
        (d / EVENT_MW_STAGE5_FILE).write_text(json.dumps(binary, ensure_ascii=False, indent=1), encoding="utf-8")
        files.append(EVENT_MW_STAGE5_FILE)
    write_identity(d / SUBSET_IDENTITY_FILE, {**dict(state["identity"]), "status": "complete" if ok else "failed",
                                              "events": int(facts["events"]) if isinstance(facts.get("events"), int)
                                              else None, "files": files,
                                              "capture_error": st.capture_error, "binary_captured": bool(binary)})


def event_stage5_facts(request: Mapping[str, Any], report: Any, binary: Optional[Mapping[str, Any]],
                       final_survivors: Any = None) -> Dict[str, Any]:
    """SPEC v5.58 (x)：event_import 一點之第 5 段事實（各軸皆記）——`event_threshold_facts`（門檻分支、實際門檻、第 5 段輸入／
    輸出數）＋`survivors`＝第 5 段倖存數（`stage5_output`；清冊 survivors 軸於事件入口之值）、`final_survivors`（第 6–7 段後，
    原 `_ic_facts` 之 survivors）、`binary_receipt`（`binary_receipt_facts`）、`post_stage5_claim`。"""
    thr = event_threshold_facts(request, report)
    receipt = binary_receipt_facts(binary)
    return {**thr, "survivors": thr["stage5_output"], "final_survivors": final_survivors, "binary_receipt": receipt,
            "post_stage5_claim": post_stage5_claim(thr["stage5_output"], receipt)}


def event_point_product_check(records: Sequence[Mapping[str, Any]], work: Path, request: Mapping[str, Any]
                              ) -> Dict[str, Any]:
    """SPEC v5.56 (j)：以**產品實跑**驗事件數軸一點——`records` 匯入隔離儲存根、經 route `_resolve_event_batch` 與服務
    `start_analysis`（同 `_run_event_import` events 軸之路徑、同一請求 `request`），行程內重綁 `EVENT_BINARY_ENTRIES` 與
    `EVENT_LABEL_MODE_ENTRY`（`rebind_all`；結束還原）：取產品決策點回傳之 `label_mode`（effective、reason、兩類數）與
    二元三入口之呼叫次數（扣例外）。`ok`＝effective＝"imported_binary" 且三入口 calls ≥ 1。不改產品碼。"""
    import api.services.case_import_service as cis
    from api.routes.ic_analysis import _resolve_event_batch
    from api.services.case_import_service import EventImportService

    fb = _fb()
    store = EventImportService(storage_dir=Path(work) / "events")
    upload = json.dumps(list(records), ensure_ascii=False, sort_keys=True).encode("utf-8")
    resp = store.import_records(list(records), source_name="icperf-t02-event-precheck-product", upload_bytes=upload,
                                validate_only=False)
    cis._event_import_service = store
    req_rec = {**dict(request), "event_import_id": str(resp.import_id)}
    modes: List[Any] = []
    rec = Recorder(context="event-precheck", heartbeat=False,
                   captures={EVENT_LABEL_MODE_ENTRY: lambda a, k, res: modes.append(
                       dict((res or {}).get("label_mode") or {}) if isinstance(res, Mapping) else None)})
    targets = resolve_targets([*EVENT_BINARY_ENTRIES, EVENT_LABEL_MODE_ENTRY])
    binding = rebind_all({eid: t.func for eid, t in targets.items()}, rec)
    error = None
    report: Any = None
    try:
        svc = _service_with_tasks(req_rec, Path(work) / "registry.json")
        req = fb._ic_analyze_request(req_rec)
        _tid, info = _service_analysis(svc, req, rec, event_batch=_resolve_event_batch(req))
        report = info.get("result")
    except Exception as exc:  # noqa: BLE001 — 產品實跑失敗即本點不成立（原因照記）
        error = f"{type(exc).__name__}: {exc}"
    finally:
        binding.restore()
    calls = {eid: int(rec.stat(eid).calls) - int(rec.stat(eid).raised) for eid in EVENT_BINARY_ENTRIES}
    mode = modes[0] if modes else None
    # SPEC v5.57 (q)：本點之門檻分支、實際門檻設定與第 5 段實值（判定不變：effective＝imported_binary 且三入口 calls ≥ 1）
    return {**event_product_verdict(mode, calls, error), "label_mode": mode, "binary_calls": calls, "error": error,
            "label_mode_calls": int(rec.stat(EVENT_LABEL_MODE_ENTRY).calls),
            **event_threshold_facts(request, report)}


def event_product_verdict(mode: Optional[Mapping[str, Any]], calls: Mapping[str, int], error: Optional[str]
                          ) -> Dict[str, Any]:
    """SPEC v5.56 (j) 之單點判定（純函式）：產品實跑無例外、決策點之 effective＝"imported_binary"、且
    `EVENT_BINARY_ENTRIES` 每一入口 calls ≥ 1（缺鍵以 0 計）⇒ ok。回 {"ok", "effective_mode", "missing_calls"}。"""
    effective = (mode or {}).get("effective") if isinstance(mode, Mapping) else None
    missing = [e for e in EVENT_BINARY_ENTRIES if int(calls.get(e, 0) or 0) < 1]
    return {"ok": bool(error is None and effective == "imported_binary" and not missing), "effective_mode": effective,
            "missing_calls": missing}


def _event_stage(records: Sequence[Mapping[str, Any]], work: Path, request: Mapping[str, Any], manifest: Path
                 ) -> Dict[str, Any]:
    """事件批 `records` 經產品五階段編排（`ICAnalysisService._run_event_label_stages`，服務之唯一事件入口；不跑 IC）之結果。"""
    from api.services.ic_analysis_service import ICAnalysisService

    req, batch, _rec = _event_import_batch(records, work / "events", request)
    return ICAnalysisService._run_event_label_stages(req, batch, features_path=None, meta_path=None,
                                                     feature_manifest_path=str(manifest))


def event_axis_precheck(out_root: Optional[Path] = None, *, verify: bool = True) -> Dict[str, Any]:
    """SPEC v5.55 (g2)：事件數軸三點之秒級切分預檢（不跑 IC）。事件批＝`_event_batch_records`（依 t0 排序；events 軸取前 n
    筆，同 `_run_event_import`）；請求＝事件匯入路徑之 events 軸請求（L 格 run、`ROW_AXIS_COLS` 欄）。①全批經產品五階段編排
    一次，得每事件之特徵列鍵（`event_label_owners`）；②對每一候選 n（1..K）以前 n 筆之列鍵經 `event_split_counts` 求測試段
    事件數；③可達＝樣本外切分成立且測試段事件數 ≥ `min_test_events`（`oos`）；可達之 n 依序排列，取首、中（整數中位位置）、
    末三點；④三點各以前 n 筆**重跑**五階段編排與切分（不以全批之列鍵代之）驗其仍可達且三點嚴格遞增。可達點 < 3 或複驗不成立
    ⇒ `ok` False（呼叫端開跑前 FreezeError；不以關切分冒充預設分支）。回 {"ok", "scales", "points": [{n, train_events,
    test_events, test_pos, test_neg, oos, binary, ...}], "n_events", "reachable_range", "reason"}。

    SPEC v5.56（與上列衝突處以此為準）：(n) 事件批＝Task 0.2 專用批（`_event_axis_batch`，`EVENT_AXIS_BREAKOUT_BARS`），子集＝
    `event_axis_subset` 等距抽樣（保留 train／test 比例；不再為前 n 筆）；可達＝`oos` 且 `binary`（測試段兩類各 ≥
    `min_events_per_class`，經產品計數函式 `count_binary_classes_in_rows`）；記 `span`（末點／首點）。(j) 三點複驗除重跑五階段
    編排與切分外，另以**產品實跑**（`event_point_product_check`：服務 `start_analysis`、同一請求）斷言 effective mode＝
    `imported_binary` 且二元三入口（`EVENT_BINARY_ENTRIES`）calls ≥ 1；任一點不成立 ⇒ `ok` False（Task 0.4 ㊵ 修正前產品之
    秒／毫秒時鐘不一致使 effective 恆為 return_rule，本預檢據實判不成立）。首選點 effective 已為 imported_binary 而二元某入口
    因該子集之候選欄 0 呼叫（2026-11-01 實測：等距 176 筆之 block_permutation_table 0 呼叫）⇒ 沿 `event_point_candidates` 之
    候選序列向中點續試（每試一次產品實跑；試過者記 `attempts`），不以 0 呼叫充數。`verify`=False ⇒ 只做切分複驗、`ok` 恆 False
    （僅供探查規則；量測不得以之開跑）。

    SPEC v5.57 (q)：請求改 `relaxed_event_request`（比照 v5.55 (d) 只覆寫 `p_value_max`；event_import events 軸同一請求），
    使低點第 5 段有通過欄；產品實跑判定不變（effective＝imported_binary 且三入口 calls ≥ 1）；收據頂層與每點記門檻分支、
    實際門檻設定、產品第 5 段之 alpha_effective 與輸入／輸出數（`event_threshold_facts`）。"""
    root = Path(out_root) if out_root is not None else REPO / TASK02_ROOT
    root = (root if root.is_absolute() else REPO / root).resolve()
    eb = _load_script("icperf_t02_event_batch", "scripts/icperf_event_batch.py")
    records = _event_axis_batch()
    # SPEC v5.57 (q)：預檢與 event_import events 軸同一非預設門檻請求（只覆寫 p_value_max）；切分不受門檻影響
    request = relaxed_event_request(ROW_AXIS_COLS)
    manifest = (REPO / request["run_dir"] / "feature_manifest.json").resolve()
    out: Dict[str, Any] = {"ok": False, "scales": [], "points": [], "n_events": len(records), "reason": None,
                           "rule": EVENT_AXIS_SAMPLING,
                           "event_rule": eb.rule_id(EVENT_AXIS_BREAKOUT_BARS, EVENT_AXIS_PRIOR_FIELD),
                           "event_rule_basis": EVENT_AXIS_RULE_BASIS, "run": request["run_dir"],
                           "reachable_range": None, "span": None, "verified_by_product_run": bool(verify),
                           "threshold_branch": request["threshold_branch"],
                           "threshold_override": dict(request["threshold_override"]),
                           "thresholds": dict(request["config_override"]["thresholds"]),
                           "threshold_basis": EVENT_AXIS_THRESHOLD_BASIS}
    with _prepare_isolation(root, EVENT_PRECHECK_TAG) as work:
        full = _event_stage(records, work / "full", request, manifest)
        owner = {int(k): str(v) for k, v in (full.get("event_label_owners") or {}).items()}
        key_of = {eid: k for k, eid in owner.items()}
        reachable: List[int] = []
        scan: Dict[int, Dict[str, Any]] = {}
        for n in range(1, len(records) + 1):
            keys = [key_of[str(r["event_id"])] for r in event_axis_subset(records, n) if str(r["event_id"]) in key_of]
            c = event_split_counts(full, request, manifest, keys)
            scan[n] = c
            if c["oos"] and c["binary"]:
                reachable.append(n)
        if reachable:
            out["reachable_range"] = [reachable[0], reachable[-1], len(reachable)]
            out["span"] = reachable[-1] / reachable[0]
        out["full_batch"] = {k: scan[len(records)].get(k) for k in ("train_events", "test_events", "test_pos", "test_neg",
                                                                     "train_pos", "train_neg", "min_test_events",
                                                                     "min_events_per_class", "split_reason")} \
            if records else None
        if len(reachable) < 3:
            out["reason"] = (f"可達點 {len(reachable)} 個 < 3（等距抽樣之 n 筆：測試段事件數 ≥ min_test_events 且測試段兩類各 ≥ "
                             "min_events_per_class）")
            return out
        def check(n: int) -> Dict[str, Any]:
            sub = event_axis_subset(records, n)
            staged = _event_stage(sub, work / f"n{n}", request, manifest)
            pt = {"n": int(n), **event_split_counts(staged, request, manifest)}
            if verify:
                pt["product"] = event_point_product_check(sub, work / f"p{n}", request)
            return pt

        out["attempts"] = []
        for role, seq in event_point_candidates(reachable).items():
            pt: Dict[str, Any] = {}
            for n in seq:
                pt = check(n)
                prod = pt.get("product") or {}
                out["attempts"].append({"role": role, "n": int(n), "oos": pt.get("oos"), "binary": pt.get("binary"),
                                        "effective_mode": prod.get("effective_mode"),
                                        "missing_calls": prod.get("missing_calls")})
                # 只有「effective＝imported_binary 而二元某入口因該子集之候選欄而 0 呼叫」才沿候選序列續試；effective 錯誤
                # （時鐘等系統性問題）或未驗 ⇒ 不續試（據實判不成立）
                if not verify or prod.get("ok") or prod.get("effective_mode") != "imported_binary" \
                        or not (pt.get("oos") and pt.get("binary")):
                    break
            out["points"].append({**pt, "role": role})
        out["points"].sort(key=lambda p: int(p["n"]))
        if verify and [p["role"] for p in out["points"]] != ["low", "mid", "high"]:
            out["reason"] = f"三點之候選序列交錯（{[(p['role'], p['n']) for p in out['points']]}）"
            return out
        out["scales"] = [p["n"] for p in out["points"]]
        bad = [p["n"] for p in out["points"] if not (p["oos"] and p["binary"])]
        not_binary = [p["n"] for p in out["points"] if verify and not (p.get("product") or {}).get("ok")]
        if len(out["scales"]) != 3 or bad:
            out["reason"] = f"三點複驗不成立（非嚴格遞增或切分／兩類不可達：{bad}）"
            return out
        if not verify:
            out["reason"] = "verify=False：未以產品實跑驗 effective mode 與二元三入口（不得據以開跑）"
            return out
        if not_binary:
            modes = {p["n"]: (p.get("product") or {}).get("effective_mode") for p in out["points"]}
            missing = {p["n"]: (p.get("product") or {}).get("missing_calls") for p in out["points"]
                       if p["n"] in not_binary}
            out["reason"] = (f"三點之產品實跑不成立：{not_binary}（effective={modes}；0 呼叫入口={missing}；SPEC v5.56 (j)——effective "
                             "非 imported_binary 為時鐘等系統性問題〔Task 0.4 ㊵〕；effective 已為 imported_binary 而 "
                             "block_permutation_table 0 呼叫＝該子集第 5 段無倖存欄〔產品只對倖存欄置換，"
                             "ic_filter_orchestrator.py `_run_binary_permutation_and_negative_control` 之 `if passed:`〕，候選已試盡；"
                             f"SPEC v5.57 (q) 非預設門檻 {request['threshold_override']} 下仍不可達 ⇒ 須補資料）")
            return out
    out["ok"] = True
    return out


#: SPEC v5.56 (j)：三點各自之候選續試上限（每試一次＝一次產品實跑，約半分鐘）
EVENT_PRECHECK_MAX_TRIES = 6


def event_point_candidates(reachable: Sequence[int], max_tries: int = EVENT_PRECHECK_MAX_TRIES) -> Dict[str, List[int]]:
    """事件數軸三點之候選序列（SPEC v5.56 (j)）：low＝可達之首點起向中點、high＝末點起向中點、mid＝中位點起向兩側交替；步距＝
    max(1, 可達點數 // 20)；各至多 `max_tries` 個，low／high 不越過中位點。首選＝首、中、末（同 v5.55 (g2)）；首選於產品實跑因該
    子集之候選欄使二元某入口 0 呼叫時才續試（`event_axis_precheck`）。"""
    r = list(reachable)
    m = (len(r) - 1) // 2
    step = max(1, len(r) // 20)
    low = [r[i] for i in range(0, m, step)][:max_tries]
    high = [r[i] for i in range(len(r) - 1, m, -step)][:max_tries]
    mid = [r[m]]
    k = 1
    while len(mid) < max_tries and (m - k * step > 0 or m + k * step < len(r) - 1):
        for j in (m + k * step, m - k * step):
            if 0 < j < len(r) - 1 and len(mid) < max_tries:
                mid.append(r[j])
        k += 1
    return {"low": low or [r[0]], "mid": mid, "high": high or [r[-1]]}


def _run_event_study(ctx: RunContext) -> Dict[str, Any]:
    from api.models.event_import_models import EventAnalyzeRequest, FeatureRunRef
    from api.services.case_import_service import EventImportService

    fb = _fb()
    # SPEC v5.56 (n)：事件數軸＝Task 0.2 專用批之等距抽樣（與 event_import 同一批、同一三點）；K 線根數軸＝凍結規則之全部事件
    records = _event_axis_records(ctx.scale) if ctx.axis == "events" else _event_batch_records(None)
    upload = json.dumps(records, ensure_ascii=False, sort_keys=True).encode("utf-8")
    svc = EventImportService(storage_dir=ctx.work / "events")
    resp = svc.import_records(records, source_name="icperf-t02-event-study", upload_bytes=upload, validate_only=False)
    run = fb._cell_run(fb.LONG_CELL)
    projection_error = None
    # SPEC v5.53 (c0)：rows 軸＝全部事件、K 線讀隔離截短複本之末 {scale} 根（`event_bars_context`）
    with event_bars_context(ctx, records) as bars:
        out = svc.analyze(resp.import_id, EventAnalyzeRequest())
        # 投影分支之 FF run 定位（`canonical_holdout.resolve_run_dir`）以模組所在 repo 根之 data_cache/features 為根 ⇒ 於本次
        # 隔離 cwd 引入 L 格 run（`projection_run_root`）
        with projection_run_root(ctx.work / "cwd", run) as linked:
            try:
                svc.analyze(resp.import_id, EventAnalyzeRequest(feature_run=FeatureRunRef(
                    symbol=run["symbol"], timeframe=run["timeframe"], config_hash=run["config_hash"])))
            except Exception as exc:  # noqa: BLE001 — 投影分支失敗照記（收據以 raised 判非量測）
                projection_error = f"{type(exc).__name__}: {exc}"
        n_bars = _event_bars_rows(records)
    facts: Dict[str, Any] = {"input_cols": 0, "rows": n_bars, "events": len(records), "requested_columns": None,
                             "event_study_ok": out is not None, "projection_error": projection_error,
                             "projection_run_link": os.path.relpath(linked, REPO), "projection_run": run["run_dir"],
                             "actual_scale": len(records)}
    if ctx.axis == "rows":
        facts.update(bars_facts(bars), actual_scale=bars_actual(bars, int(ctx.n_rows or 0)))
    if ctx.axis == "events":
        facts.update(event_axis_facts())
        # SPEC v5.57 (q)：事件研究頁不經 IC 第 5 段門檻（`EventAnalyzeRequest.config_override` 只入 holdout 之 IC 設定，
        # api/services/case_import_service.py:1813-1814；event_samples 無 thresholds 之消費點）⇒ 覆寫 p_value_max 為 no-op，
        # 本路徑維持預設請求；事實記明分支與依據
        facts.update(threshold_branch="default",
                     threshold_basis="事件研究頁無第 5 段門檻消費點（case_import_service.py:1813-1814 之 config_override 只入 "
                                     "resolve_canonical_holdout 之 ic_config）；SPEC v5.57 (q) 之非預設門檻只作用於 event_import")
    return facts


@contextlib.contextmanager
def projection_run_root(cwd: Path, run: Mapping[str, str]) -> Iterable[Path]:
    """事件研究投影分支（`EventImportService._analyze_with_projection`）之 FF run 定位：產品
    `momentum/Analysis/event_samples/canonical_holdout.py:66-89` `resolve_run_dir` 於 `repo_root=None` 時以模組所在 repo 根
    （`Path(__file__).resolve().parents[3]`，:74）之 `data_cache/features/*/*/<config_hash>`（:75）搜尋——不隨 cwd；呼叫端
    `api/services/case_import_service.py:1715-1716`（locator）與 `canonical_holdout.py:213`（`resolve_canonical_holdout`
    經 :1816 之 resolver）皆不傳 repo_root。L 格 run 存於 `data_cache/numview_freeze_runs/<L>__default/features/...`，不在該
    glob 下 ⇒ `feature_run_not_found`。本函式：①於隔離 cwd 之 `data_cache/features/<symbol>/<tf>/<config_hash>` 以 symlink
    引入真實 run（唯讀；不寫 repo 之 data_cache/features）；②本行程內把 `canonical_holdout.resolve_run_dir` 換為
    `repo_root` 未給時代入 `cwd` 之 wrapper（兩呼叫端皆於呼叫時取模組屬性，`momentum/factories.py:1411-1417`、
    `canonical_holdout.py:213`）；離開即還原。不改產品碼。yield 引入之路徑。"""
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from momentum.Analysis.event_samples import canonical_holdout as ch

    src = (REPO / str(run["run_dir"])).resolve()
    if not (src / "feature_manifest.json").is_file():
        raise HarnessError(f"投影分支之 FF run 不存在：{src}（config_hash={run.get('config_hash')}）")
    cwd = Path(cwd).resolve()
    dst = cwd / ch._FEATURES_DIR / str(run["symbol"]) / str(run["timeframe"]) / str(run["config_hash"])
    if REPO.resolve() == cwd:
        raise HarnessError("projection_run_root：cwd 不得為 repo 根（會寫入真實 data_cache/features）")
    if not os.path.lexists(dst):
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.symlink_to(src, target_is_directory=True)
    elif Path(os.path.realpath(dst)) != src:
        raise HarnessError(f"{dst} 已存在且不指向 {src}")
    orig = ch.resolve_run_dir

    def rooted(ff_run: str, *, symbols: Optional[Sequence[str]] = None, repo_root: Optional[Path] = None) -> Path:
        return orig(ff_run, symbols=symbols, repo_root=cwd if repo_root is None else repo_root)

    ch.resolve_run_dir = rooted
    try:
        yield dst
    finally:
        ch.resolve_run_dir = orig


# ── SPEC v5.53 (c0)：事件路徑 K 線根數軸之隔離截短快取複本 ───────────────────────────────────────────────


#: 真實 K 線快取（`bars_source._DEFAULT_CACHE` 於本行程第一次改指前之值；`event_bars_context` 記之）
_REAL_BARS_CACHE: Optional[Path] = None


def real_bars_cache() -> Path:
    """事件路徑之真實 K 線快取路徑（`momentum/Analysis/event_samples/bars_source.py` `_DEFAULT_CACHE`；本行程已改指者取
    改指前之值）。"""
    if _REAL_BARS_CACHE is not None:
        return _REAL_BARS_CACHE
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from momentum.Analysis.event_samples import bars_source

    return Path(bars_source._DEFAULT_CACHE)


def event_bars_dir(out_root: Path, rows: int) -> Path:
    """根數 `rows` 之隔離截短複本目錄：`<out-root>/EVENT_BARS_DIR/rows<R>/`（內含 `EVENT_BARS_FILE` 與身分 sidecar）。"""
    return Path(out_root) / EVENT_BARS_DIR / f"rows{int(rows)}"


def event_bar_key(records: Sequence[Mapping[str, Any]]) -> Tuple[str, str]:
    """事件批之 (symbol, 週期)：須恰一組（事件路徑之服務對單一 symbol×週期讀 K 線，`case_import_service.py:1162-1165`；
    run 週期與觸發週期相同）；否則 HarnessError。"""
    keys = sorted({(str(r.get("symbol")), str(r.get("timeframe"))) for r in records})
    if len(keys) != 1:
        raise HarnessError(f"事件 K 線根數軸：事件批須恰一組 (symbol, 週期)，實得 {keys}")
    return keys[0]


def _dataset_sha256(arr: Any) -> str:
    """K 線資料集身分（NUMVIEW 判準檔 `cell_rules.kline_source.dataset_sha256` 同規則：sha256(str(dtype.descr) ‖ C 連續位元組)）。"""
    import numpy as np

    a = np.ascontiguousarray(arr)
    h = hashlib.sha256(str(a.dtype.descr).encode("utf-8"))
    h.update(a.tobytes())
    return h.hexdigest()


def _first_event_index(ts: Any, records: Sequence[Mapping[str, Any]]) -> int:
    """最早事件 t0（epoch 毫秒）於快取時間戳序列 `ts`（epoch 秒或毫秒）之位置；不在序列中 ⇒ HarnessError。"""
    import numpy as np

    t0 = min(int(r["t0"]) for r in records)
    key = t0 if int(ts[-1]) > 10 ** 12 else t0 // 1000
    i = int(np.searchsorted(ts, key, side="left"))
    if i >= len(ts) or int(ts[i]) != key:
        raise HarnessError(f"事件 K 線根數軸：最早事件 t0={t0} 不在 K 線快取序列中")
    return i


def event_bar_scales(records: Optional[Sequence[Mapping[str, Any]]] = None,
                     cache: Optional[Path] = None) -> Tuple[int, int, int]:
    """K 線根數軸之三點（全部事件固定）：最小＝自最早事件之前 `EVENT_BARS_PRE` 根至序列末之根數、最大＝真實快取該 symbol／
    週期之全長（截短只去前段，末根不變；事件之答案窗皆在末段內）、中＝兩者之中點（整數）。只讀時間戳（秒級）。最早事件前不足
    `EVENT_BARS_PRE` 根或三點不嚴格遞增 ⇒ HarnessError（資料不足）。"""
    import h5py

    records = _event_batch_records(None) if records is None else list(records)
    sym, tf = event_bar_key(records)
    with h5py.File(str(cache or real_bars_cache()), "r") as f:
        ts = f[f"{sym}/{tf}/data"]["timestamp"][:]
    n = int(len(ts))
    first = _first_event_index(ts, records)
    if first < EVENT_BARS_PRE:
        raise HarnessError(f"事件 K 線根數軸：最早事件前只有 {first} 根 < EVENT_BARS_PRE {EVENT_BARS_PRE}（無截短空間）")
    lo = n - (first - EVENT_BARS_PRE)
    mid = (lo + n) // 2
    if not lo < mid < n:
        raise HarnessError(f"事件 K 線根數軸：三點 {(lo, mid, n)} 非嚴格遞增（截短空間不足）")
    return lo, mid, n


def event_bars_identity(rows: int, records: Sequence[Mapping[str, Any]], cache: Path) -> Dict[str, Any]:
    """隔離截短複本之身分（SPEC v5.52 (a) 同法）：來源快取路徑與大小、資料集鍵、來源根數與資料集 sha256、截短根數、
    最早事件 t0、事件數、`EVENT_BARS_PRE`；任一不同 ⇒ 重建。"""
    import h5py

    sym, tf = event_bar_key(records)
    key = f"{sym}/{tf}/data"
    with h5py.File(str(cache), "r") as f:
        data = f[key][()]
    return {"schema": SUBSET_IDENTITY_SCHEMA, "kind": "event_bars", "source": _rel(Path(cache)),
            "source_size": int(Path(cache).stat().st_size), "key": key, "source_rows": int(len(data)),
            "source_dataset_sha256": _dataset_sha256(data), "rows": int(rows),
            "first_event_t0": min(int(r["t0"]) for r in records), "n_events": len(records), "pre_bars": EVENT_BARS_PRE}


def prepare_event_bars(out_root: Path, rows: int, *, records: Optional[Sequence[Mapping[str, Any]]] = None,
                       cache: Optional[Path] = None) -> Dict[str, Any]:
    """建根數 `rows` 之隔離截短複本 `<out-root>/EVENT_BARS_DIR/rows<R>/EVENT_BARS_FILE`：只含事件批之 `<symbol>/<週期>/data`，
    取真實快取該資料集之末 `rows` 根（dtype、檔／群組／資料集屬性照抄）；來源只以唯讀開啟（目的檔不得為來源）。身分
    sidecar＝`event_bars_identity`（相同 ⇒ 沿用）。`rows` 超過來源根數或少於涵蓋全部事件所需 ⇒ HarnessError。回 {"reused",
    "path", "identity"}。"""
    import h5py

    records = _event_batch_records(None) if records is None else list(records)
    src = Path(cache or real_bars_cache()).resolve()
    d = event_bars_dir(Path(out_root) if Path(out_root).is_absolute() else REPO / out_root, rows).resolve()
    dst = d / EVENT_BARS_FILE
    if dst == src:
        raise HarnessError(f"隔離截短複本之目的檔不得為來源快取：{dst}")
    want = event_bars_identity(rows, records, src)
    side = d / SUBSET_IDENTITY_FILE
    if dst.is_file() and read_identity(side) == json.loads(json.dumps(want)):
        return {"reused": True, "path": str(dst), "identity": want}
    key = want["key"]
    with h5py.File(str(src), "r") as f:
        ts = f[key]["timestamp"][:]
        n = int(len(ts))
        if int(rows) > n:
            raise HarnessError(f"事件 K 線根數軸 {rows} 根 > 來源 {key} {n} 根（資料不足）")
        if n - int(rows) > _first_event_index(ts, records):
            raise HarnessError(f"事件 K 線根數軸 {rows} 根不含最早事件（須 ≥ {n - _first_event_index(ts, records)}）")
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / (EVENT_BARS_FILE + ".part")
        with h5py.File(str(tmp), "w") as g:
            for k, v in f.attrs.items():
                g.attrs[k] = v
            parts = key.split("/")
            for i in range(1, len(parts)):
                grp = "/".join(parts[:i])
                gg = g.require_group(grp)
                for k, v in f[grp].attrs.items():
                    gg.attrs[k] = v
            ds = f[key]
            out = g.create_dataset(key, data=ds[n - int(rows):], dtype=ds.dtype)
            for k, v in ds.attrs.items():
                out.attrs[k] = v
    os.replace(tmp, dst)
    write_identity(side, want)
    return {"reused": False, "path": str(dst), "identity": want}


@contextlib.contextmanager
def redirect_event_bars(path: Path) -> Iterable[List[Dict[str, Any]]]:
    """本行程內把事件路徑之 K 線來源（`bars_source._DEFAULT_CACHE`；服務經 `EventSamplePipeline.bars_from_kline_cache`、
    `cache_path=None` 一律讀此值，`pipeline.py:543-547`、`bars_source.py:26`）改指 `path`，並觀測每次讀取（呼叫時 import
    之 `load_bars_from_kline_cache` 換為記錄所讀快取與各序列根數之 wrapper）；離開時還原。yield 讀取紀錄 list。不改產品碼。"""
    global _REAL_BARS_CACHE
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from momentum.Analysis.event_samples import bars_source

    orig_cache, orig_load = bars_source._DEFAULT_CACHE, bars_source.load_bars_from_kline_cache
    if _REAL_BARS_CACHE is None:
        _REAL_BARS_CACHE = Path(orig_cache)
    seen: List[Dict[str, Any]] = []

    def observed(symbols: Any, timeframes: Any, *, cache_path: Optional[Path] = None) -> Any:
        res = orig_load(symbols, timeframes, cache_path=cache_path)
        seen.append({"cache": str(Path(cache_path) if cache_path else bars_source._DEFAULT_CACHE),
                     "rows": {f"{s}/{t}": int(len(df)) for s, by in res.items() for t, df in by.items()}})
        return res

    bars_source._DEFAULT_CACHE = Path(path)
    bars_source.load_bars_from_kline_cache = observed
    try:
        yield seen
    finally:
        bars_source._DEFAULT_CACHE = orig_cache
        bars_source.load_bars_from_kline_cache = orig_load


@contextlib.contextmanager
def event_bars_context(ctx: RunContext, records: Optional[Sequence[Mapping[str, Any]]]) -> Iterable[Dict[str, Any]]:
    """rows 軸（K 線根數）⇒ 建／沿用 `prepare_event_bars(ctx.out_root, ctx.n_rows)` 並於其內 `redirect_event_bars`；其餘軸
    ⇒ 不改指。yield {"path", "identity", "reads"}（非 rows 軸 ⇒ path None、reads 空）。"""
    if ctx.axis != "rows":
        yield {"path": None, "identity": None, "reads": []}
        return
    if records is None:
        raise HarnessError("事件 K 線根數軸須給事件批")
    info = prepare_event_bars(ctx.out_root, int(ctx.n_rows or 0), records=records)
    with redirect_event_bars(Path(info["path"])) as reads:
        yield {"path": info["path"], "identity": info["identity"], "reads": reads}


def bars_actual(bars: Mapping[str, Any], rows: int) -> int:
    """K 線根數軸之實際輸入點數：產品實際讀取（`redirect_event_bars` 之紀錄）全部來自隔離複本、事件批序列之根數一致 ⇒ 該
    根數；未讀取、讀自他檔、根數不一致或缺序列 ⇒ HarnessError（不得以宣告值充作實際值）。"""
    reads = list(bars.get("reads") or [])
    key = str((bars.get("identity") or {}).get("key") or "")
    series = key[:-len("/data")] if key.endswith("/data") else key
    if not reads:
        raise HarnessError("事件 K 線根數軸：產品未讀取 K 線（實際根數無從驗證）")
    other = sorted({r["cache"] for r in reads if Path(r["cache"]).resolve() != Path(str(bars["path"])).resolve()})
    if other:
        raise HarnessError(f"事件 K 線根數軸：產品讀自隔離複本以外之快取 {other}")
    got = sorted({r["rows"].get(series) for r in reads})
    if len(got) != 1 or got[0] is None:
        raise HarnessError(f"事件 K 線根數軸：各次讀取之 {series} 根數 {got} 不一致或缺")
    return int(got[0])


def bars_facts(bars: Mapping[str, Any]) -> Dict[str, Any]:
    """rows 軸紀錄之 K 線事實：隔離複本路徑、身分（來源、資料集 sha256、來源根數、截短根數）、產品讀取次數。"""
    ident = dict(bars.get("identity") or {})
    return {"bars_cache": _rel(Path(str(bars["path"]))), "bars_rows": ident.get("rows"),
            "bars_source": ident.get("source"), "bars_source_rows": ident.get("source_rows"),
            "bars_source_dataset_sha256": ident.get("source_dataset_sha256"), "bars_reads": len(bars.get("reads") or [])}


def _event_bars_rows(records: Sequence[Mapping[str, Any]]) -> Optional[int]:
    """事件路徑所讀全部 K 線之根數（scale_vector.rows 之觀測值；rows 軸時為隔離截短複本之根數）：`bars_source._DEFAULT_CACHE`
    中事件批 (symbol, 週期) 序列之長度（只讀形狀）；取不到 ⇒ None。"""
    import h5py

    from momentum.Analysis.event_samples import bars_source

    keys = sorted({(str(r.get("symbol")), str(r.get("timeframe"))) for r in records})
    try:
        with h5py.File(bars_source._DEFAULT_CACHE, "r") as f:
            return max(int(f[f"{s}/{t}/data"].shape[0]) for s, t in keys) if keys else None
    except (OSError, KeyError):
        return None


def _cross_frames(cr: Any, cells: Sequence[Mapping[str, Any]], names: Sequence[str], work: Path,
                  n_timestamps: Optional[int]) -> Tuple[Any, Any]:
    """同 `icperf_correctness_receipt._child_cross` 之讀法（逐格以該格 FeatureLibrary `load_multi` 讀、加 `_symbol` 層）；
    `n_timestamps` 給定 ⇒ 只留兩格聯集時點之末 T 個（截短時間跨度，SPEC v5.52 (b)）。回 (服務實例, cross_df)。"""
    import pandas as pd

    fb = _fb()
    frames, svc = [], None
    for i, cell in enumerate(cells):
        cs = fb._ic_service(cell, Path(work) / f"registry_{i}.json")
        svc = svc or cs
        loaded = cs._feature_library.load_multi([cell["symbol"]], cell["timeframe"],
                                                config_hashes={cell["symbol"]: cell["config_hash"]})
        frame = loaded[cell["symbol"]][list(names)].copy()
        frame["_symbol"] = cell["symbol"]
        frames.append(frame)
    if n_timestamps is not None:
        stamps = sorted(set().union(*[set(f.index) for f in frames]))
        if len(stamps) < int(n_timestamps):
            raise HarnessError(f"cross_sectional：兩格聯集時點 {len(stamps)} < timestamps 軸 {n_timestamps}（資料不足）")
        keep = stamps[-int(n_timestamps):][0]
        frames = [f[f.index >= keep] for f in frames]
    return svc, pd.concat(frames, axis=0).set_index("_symbol", append=True)


def _run_cross_sectional(ctx: RunContext) -> Dict[str, Any]:
    """跨標的（A 格 BTCUSDT／SOLUSDT 兩 run 共同欄之排序前綴）：cols 軸＝N 欄；timestamps 軸（SPEC v5.52 (b)）＝固定
    `ROW_AXIS_COLS` 欄、兩格聯集時點之末 T 個。設定＝IC 頁預設覆寫＋`XSEC_OVERRIDE_EXTRA`（關切分；見該常數之碼證）；
    其後同 `icperf_correctness_receipt._run_cross`。"""
    return _cross_run(ctx, CROSS_CELLS, dict(XSEC_OVERRIDE_EXTRA))


def _cross_run(ctx: RunContext, cell_ids: Sequence[str], override_extra: Mapping[str, Any]) -> Dict[str, Any]:
    """跨標的之共同實跑：`cell_ids` 各格之 IC 頁預設請求 run、共同 raw 欄之排序前綴 N 欄（巢狀）、`override_extra` 併入
    IC 頁預設覆寫，其後同 `icperf_correctness_receipt._run_cross`。回路徑事實（含報告之切分 metadata）。"""
    fb = _fb()
    cells = [fb.default_request("ic_report", c) for c in cell_ids]
    common = sorted(set(fb._run_feature_names(cells[0])).intersection(*[set(fb._run_feature_names(c)) for c in cells[1:]]))
    if len(common) < ctx.n_cols:
        raise HarnessError(f"{ctx.run_id}：兩格共同 raw 欄 {len(common)} < 規模 {ctx.n_cols}（資料不足）")
    names = common[:ctx.n_cols]
    cr = _load_script("icperf_t02_correctness", "scripts/icperf_correctness_receipt.py")
    request = {"cells": cells, "feature_filter": {"include_features": names}, "timeframe": cells[0]["timeframe"],
               "_work": str(ctx.work), "override_extra": dict(override_extra)}
    svc, cross_df = _cross_frames(cr, cells, names, ctx.work, ctx.n_timestamps)
    # 實際輸入點數取送入產品前之 cross_df（標籤附加後之列數另記）
    timestamps = int(cross_df.index.get_level_values(0).nunique())
    in_rows = int(len(cross_df))
    out = cr._run_cross(svc, cross_df, [c["symbol"] for c in cells], cells[0], request)
    md = (out.get("ic_report") or {}).get("metadata") or {} if isinstance(out.get("ic_report"), Mapping) else {}
    sp = md.get("ic_train_test_split") or {}
    return {"input_cols": ctx.n_cols, "rows": in_rows, "labeled_rows": int(len(out["cross_df"])),
            "symbols": len(cell_ids), "timestamps": timestamps, "requested_columns": names, "survivors": None,
            "override_extra": dict(override_extra), "split_applied": sp.get("applied"),
            "split_train_rows": sp.get("train_rows"), "split_test_rows": sp.get("test_rows"),
            "split_per_symbol_test_rows": sp.get("per_symbol_test_rows"),
            "actual_scale": timestamps if ctx.axis == "timestamps" else len(set(names))}


def _run_cross_sectional_long(ctx: RunContext) -> Dict[str, Any]:
    """SPEC v5.53 (c1)：跨標的長資料（`XSEC_LONG_CELLS`：L 格＋同一生成定義之 ETH 4h 長歷史格）共同 N 欄、IC 頁預設請求
    （不關切分）⇒ 產品全域時間切分分支（`ic_filter_orchestrator.py` `_build_cross_sectional_global_split`）；報告未記切分
    applied ⇒ HarnessError（非所量之分支）。"""
    facts = _cross_run(ctx, XSEC_LONG_CELLS, {})
    if facts.get("split_applied") is not True:
        raise HarnessError(f"cross_sectional_long：報告未走預設切分（split_applied={facts.get('split_applied')!r}）")
    return facts


#: 前史對照之已生成格（`data_cache/numview_freeze_runs/<格>__default/numview_cell.json`）：BTCUSDT 4h 主檔前史（2026-10-29
#: 實跑 partial，`calibration_insufficient_history` 34 欄）與 L 格（長歷史前史，complete）
PRE_HISTORY_REFERENCES = ("L_BTCUSDT_4h", LONG_CELL_ID)


def pre_history_reference(cell: str, repo_root: Path = REPO) -> Dict[str, Any]:
    """已生成格之前史對照（只讀 sidecar 與 K 線時間戳）：{cell, source（repo 相對）, output_window, run_status, status,
    reason_counts, pre_history_bars（來源序列中早於輸出段首根之根數）}；sidecar 不存在 ⇒ {"cell", "missing": True}。"""
    import h5py
    import numpy as np
    import pandas as pd

    side_path = Path(repo_root) / "data_cache" / "numview_freeze_runs" / f"{cell}__default" / "numview_cell.json"
    if not side_path.is_file():
        return {"cell": cell, "missing": True}
    side = json.loads(side_path.read_text(encoding="utf-8"))
    src = Path(str(side["source"]))
    src = src if src.is_absolute() else Path(repo_root) / src
    key = f"{side['symbol']}/{side['primary_tf']}/data"
    with h5py.File(str(src), "r") as f:
        ts = np.asarray(f[key]["timestamp"][:], dtype="int64")
    start = pd.Timestamp(side["output_window"][0])
    start_i = int(start.value // 10 ** (6 if int(ts[-1]) > 10 ** 12 else 9))
    try:
        rel = src.resolve().relative_to(Path(repo_root).resolve()).as_posix()
    except ValueError:
        rel = str(src)
    return {"cell": cell, "source": rel, "output_window": side["output_window"], "run_status": side.get("run_status"),
            "status": side.get("status"), "reason_counts": side.get("reason_counts"),
            "pre_history_bars": int(np.sum(ts < start_i))}


def xsec_long_precheck(repo_root: Path = REPO) -> Dict[str, Any]:
    """SPEC v5.53 (c1) 生成前之秒級預檢（只讀 K 線時間戳與收盤；不讀特徵、不跑 IC）：L 格（BTCUSDT 4h）與同一生成定義之
    `LONG_CELL_XSEC_SYMBOL` 4h 長歷史格——①各標的於生成來源（`LONG_CELL_SOURCE`）與標籤來源（`LONG_CELL_LABEL_SOURCE`）是否
    有該序列（`long_cell_source_check`）；②以 `long_cell_window` 同一規則（生成來源中 ≤ 標籤來源末根之最後 `LONG_CELL_BARS`
    根）得各標的輸出段（生成來源缺序列者以標籤來源依同規則得反事實窗，`window_from_generation_source`=False）、前史根數、窗內
    缺根數、跨標的標籤 return_1（`ic_analysis_service._append_cross_sectional_labels`：標籤來源 log(close[t+1]／close[t])）
    有限之列數；③兩窗時點重疊；④預設切分可達性——IC 頁預設請求（`precheck_override`）之設定，以兩標的輸出段之（時點, 標的）
    索引與標籤直接呼叫產品之 `_enforce_cross_sectional_label_coverage` 與 `_build_cross_sectional_global_split`（同
    `analyze_cross_sectional` :2335-2369；horizon＝`_resolve_cross_sectional_label_horizon("return_1")`）。特徵列假設＝輸出段
    全部時點（生成前無從得知逐欄缺值；同 L 格）。回 {"symbols": {...}, "overlap", "split", "generation_ready", "ok"}。"""
    import h5py
    import numpy as np
    import pandas as pd

    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from momentum.Analysis import ic_filter_orchestrator as orch
    from momentum.core.constants import TIMEFRAME_SECONDS
    from momentum.factories import create_ic_analyzer

    fb = _fb()
    root = Path(repo_root)
    per: Dict[str, Any] = {}
    windows: Dict[str, Any] = {}
    labels: Dict[str, Any] = {}
    for sym in (None, fb.LONG_CELL_XSEC_SYMBOL):
        desc = fb.long_cell_descriptor(sym)
        chk = fb.long_cell_source_check(sym, root)
        tf, key = desc["timeframes"][0], chk["key"]
        rec: Dict[str, Any] = {"cell": desc["id"], "timeframe": tf, "source_check": chk}
        per[desc["symbol"]] = rec
        if not chk["label_source"]["present"]:
            rec["window"] = None
            continue
        with h5py.File(str(root / fb.LONG_CELL_LABEL_SOURCE), "r") as f:
            lab = f[key][()]
        lts, lclose = np.asarray(lab["timestamp"], dtype="int64"), np.asarray(lab["close"], dtype="float64")
        gen_rel = fb.LONG_CELL_SOURCE if chk["long_source"]["present"] else fb.LONG_CELL_LABEL_SOURCE
        with h5py.File(str(root / gen_rel), "r") as f:
            gts = np.asarray(f[key]["timestamp"][:], dtype="int64")
        upto = gts[gts <= int(lts[-1])]
        win = upto[-fb.LONG_CELL_BARS:]
        step = int(TIMEFRAME_SECONDS[tf]) * (1000 if int(lts[-1]) > 10 ** 12 else 1)
        pos = pd.Index(lts).get_indexer(win)
        nxt = np.where((pos >= 0) & (pos + 1 < len(lts)), pos + 1, -1)
        ok_pos = (pos >= 0) & (nxt >= 0)
        c0 = np.where(ok_pos, lclose[np.clip(pos, 0, None)], np.nan)
        c1 = np.where(ok_pos, lclose[np.clip(nxt, 0, None)], np.nan)
        with np.errstate(divide="ignore", invalid="ignore"):
            ret = np.where((c0 > 0) & (c1 > 0) & np.isfinite(c0) & np.isfinite(c1), np.log(c1 / c0), np.nan)
        unit = "ms" if int(lts[-1]) > 10 ** 12 else "s"
        pre = upto[:len(upto) - len(win)]
        rec.update({"pre_history_missing_bars": int(np.sum(np.diff(pre) // step - 1)) if len(pre) > 1 else 0,
                    "pre_history_first_ts": int(pre[0]) if len(pre) else None,
                    "label_source_pre_history_bars": int(np.sum(lts < int(win[0]))) if len(win) else None})
        rec.update({"window_from_generation_source": bool(chk["long_source"]["present"]), "window_source": gen_rel,
                    "window": [pd.Timestamp(int(win[0]), unit=unit, tz="UTC").isoformat(),
                               pd.Timestamp(int(win[-1]), unit=unit, tz="UTC").isoformat()] if len(win) else None,
                    "window_bars": int(len(win)), "pre_history_bars": int(len(upto) - len(win)),
                    "window_missing_bars": int(np.sum(np.diff(win) // step - 1)) if len(win) > 1 else 0,
                    "window_in_label_source": int(np.sum(pos >= 0)), "label_valid_rows": int(np.isfinite(ret).sum())})
        windows[desc["symbol"]] = (win, unit)
        labels[desc["symbol"]] = ret
    syms = list(windows)
    overlap = np.intersect1d(*[windows[s][0] for s in syms]) if len(syms) == 2 else np.array([], dtype="int64")
    out: Dict[str, Any] = {"cells": list(XSEC_LONG_CELLS), "symbols": per,
                           "overlap": {"timestamps": int(len(overlap)),
                                       "first_ts": int(overlap[0]) if len(overlap) else None,
                                       "last_ts": int(overlap[-1]) if len(overlap) else None}}
    split: Dict[str, Any] = {"reachable": False, "error": None}
    if len(syms) == 2:
        override = precheck_override(LONG_CELL_TIMEFRAME, row_windows=False)
        analyzer = create_ic_analyzer(override)
        config = analyzer._apply_tier_config(analyzer._apply_config_override(override))
        horizon_raw = orch._resolve_cross_sectional_label_horizon("return_1")
        horizon = int(horizon_raw) if horizon_raw is not None else 1
        frames = []
        for s in syms:
            win, unit = windows[s]
            idx = pd.MultiIndex.from_arrays([pd.to_datetime(win, unit=unit), [s] * len(win)], names=[None, "_symbol"])
            frames.append(pd.DataFrame({"f": np.zeros(len(win)), "return_1": labels[s]}, index=idx))
        numeric_df = pd.concat(frames, axis=0)
        split.update(ic_train_test_split=bool(config.ic_train_test_split), oos_test_size=float(config.oos_test_size),
                     min_test_rows=int(config.min_test_rows), effective_horizon=horizon, embargo=int(config.embargo))
        if not config.ic_train_test_split:
            split["error"] = "split_disabled"
        else:
            try:
                orch._enforce_cross_sectional_label_coverage(numeric_df, "return_1", 1, horizon,
                                                            config.min_label_coverage_tol)
                freq = orch.EXPECTED_FREQ_BY_TIMEFRAME[LONG_CELL_TIMEFRAME]
                _tr, _te, meta = orch._build_cross_sectional_global_split(numeric_df, 1, 0, config, freq, horizon)
                split.update(reachable=bool(meta.get("applied")), train_rows=meta.get("train_rows"),
                             test_rows=meta.get("test_rows"), per_symbol_test_rows=meta.get("per_symbol_test_rows"),
                             train_max_time=meta.get("train_max_time"), test_min_time=meta.get("test_min_time"))
            except Exception as exc:  # noqa: BLE001 — 產品之切分拒收（InvalidInputError 等）即「不可達」，原因照記
                split["error"] = f"{type(exc).__name__}: {exc}"
    out["split"] = split
    # 前史對照（校準根數由生成前史決定；生成前無從讀逐欄缺額）：已生成之兩格——`PRE_HISTORY_REFERENCES`（主檔前史 ⇒ 校準不足
    # 而 blocked；長歷史前史 ⇒ complete）——之前史根數與結果，與各標的前史比較
    refs = [pre_history_reference(c, root) for c in PRE_HISTORY_REFERENCES]
    out["pre_history_references"] = refs
    ok_refs = [r["pre_history_bars"] for r in refs if r.get("run_status") == "complete" and r.get("pre_history_bars")]
    bad_refs = [r["pre_history_bars"] for r in refs if r.get("run_status") == "partial" and r.get("pre_history_bars")]
    for r in per.values():
        ph = r.get("pre_history_bars")
        r["pre_history_vs_references"] = None if ph is None else {
            "ge_min_complete_reference": bool(ok_refs) and ph >= min(ok_refs),
            "le_max_short_reference": bool(bad_refs) and ph <= max(bad_refs)}
    out["generation_ready"] = all(r["source_check"]["ok"] for r in per.values())
    out["ok"] = bool(out["generation_ready"] and split["reachable"])
    return out


#: SPEC v5.52 (c)：IC-first 子集 run 之工作根（`<out-root>/icfirst_subsets/<tag>/`；可重用之中介，非系統暫存）
ICFIRST_SUBSETS_DIR = "icfirst_subsets"


def icfirst_subset_tag(n_cols: int, rows: Optional[int]) -> str:
    """子集 run 之目錄名：cols 軸（基準窗長之 raw run）＝`c<N>`；列軸窗長 R（非基準）＝`r<R>_c<N>`。"""
    base = _fb().icfirst_base_rows()
    return f"c{int(n_cols)}" if rows is None or int(rows) == base else f"r{int(rows)}_c{int(n_cols)}"


def _icfirst_record(rows: Optional[int]) -> Tuple[Dict[str, Any], Path]:
    fb = _fb()
    try:
        rec = fb.icfirst_raw_record(rows=rows)
    except fb.FreezeError as exc:
        raise HarnessError(f"icfirst_post_generation：{exc}") from exc
    return rec, fb.icfirst_raw_root(rows) / fb.ICFIRST_RAW_RECORD


def icfirst_subset_identity(n_cols: int, rows: Optional[int]) -> Dict[str, Any]:
    """IC-first 子集 run 之來源身分（SPEC v5.52 (a)(c)）：raw 記錄檔與其 run 之 feature_manifest.json 之路徑、大小、內容
    sha256、raw 欄數、公開索引根數＋seed＋子集欄數＋窗長。任一不同 ⇒ 重建。"""
    fb = _fb()
    rec, rec_path = _icfirst_record(rows)
    manifest = Path(rec["features_root"]) / rec["symbol"] / rec["timeframe"] / rec["config_hash"] / "feature_manifest.json"
    return {"schema": SUBSET_IDENTITY_SCHEMA, "source": _rel(rec_path), "source_size": int(rec_path.stat().st_size),
            "source_sha256": file_sha256(rec_path), "manifest": _rel(manifest), "manifest_sha256": file_sha256(manifest),
            "source_total_cols": int(rec["feature_count"]), "source_rows": len(rec.get("features_index") or []),
            "seed": int(fb.SEED), "n_cols": int(n_cols), "rows": None if rows is None else int(rows)}


def _numeric_identity_of(manifest: Mapping[str, Any]) -> Optional[Dict[str, Dict[str, Any]]]:
    """來源 manifest 之 NUMVIEW D2 身分（鍵名讀契約 `manifest_keys`；生成層級之 fingerprint／algorithm_id／路由身分，與欄子集
    無關）原樣取出，供 `write_raw(numeric_identity=...)` 由產品寫出端寫入子集 manifest；來源缺 ⇒ None（不寫）。"""
    from momentum.FeatureEngineering import numeric_view

    keys = numeric_view.load_contract()["manifest_keys"]
    roles = ("fingerprint", "algorithm_id", "route_identity")
    node_src = (manifest.get("artifacts") or {}).get("raw") or {}
    if any(keys[r] not in manifest for r in roles):
        return None
    node = {keys[r]: node_src[keys[r]] for r in roles if keys[r] in node_src}  # 來源節點無者不補（不臆造）
    root = {keys[r]: manifest[keys[r]] for r in roles}
    if keys.get("observed_arms") in manifest:
        root[keys["observed_arms"]] = manifest[keys["observed_arms"]]
    return {"artifact": node, "root": root}


def verify_icfirst_subset(src_root: Path, sub_root: Path, rec: Mapping[str, Any], chosen: Sequence[str]) -> Dict[str, Any]:
    """SPEC v5.52 (c)：子集 run 之驗證（任一不成立 ⇒ HarnessError，大聲失敗）：① 產品讀取端 `FeatureReader.load_manifest_v2
    (consumer="strict")` 可讀（命名世代閘、完整度、run 狀態）且 `ICEngine._validate_l7_raw_manifest` 通過；② manifest 身分
    （symbol／tf／config_hash＝來源、raw 節點 complete、total_features＝N、群組欄聯集＝所選 N 欄、row_count＝來源、NUMVIEW 身分
    頂層與節點＝來源）；③ 時間軸 sidecar（`load_row_index_v2`）逐點＝來源；④ post-generation 之讀回路徑可讀：`stream_groups_v2`
    逐組讀回之欄數合計＝N、每組列數＝row_count，且逐欄值（含 NaN 位置）＝來源同名欄（位元組級；`numpy.array_equal`
    equal_nan）。回驗證紀錄（含 time_range 是否與來源相同——非讀取前提，只記錄）。"""
    import numpy as np

    from momentum.Analysis.ic_engine import ICEngine
    from momentum.FeatureEngineering import numeric_view
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    sym, tf, ch = str(rec["symbol"]), str(rec["timeframe"]), str(rec["config_hash"])
    problems: List[str] = []
    src_reader, sub_reader = FeatureReader(str(src_root)), FeatureReader(str(sub_root))
    src_m = src_reader.load_manifest_v2(sym, tf, ch, artifact_kind="raw", consumer="strict")
    try:
        sub_m = sub_reader.load_manifest_v2(sym, tf, ch, artifact_kind="raw", consumer="strict")
        ICEngine._validate_l7_raw_manifest(sub_m, sym, tf, ch)
    except Exception as exc:  # noqa: BLE001 — 讀取端拒收即驗證失敗
        raise HarnessError(f"IC-first 子集 run 不可由產品讀取端讀出：{type(exc).__name__}: {exc}") from exc
    raw = (sub_m.get("artifacts") or {}).get("raw") or {}
    cols = [str(c) for g in (raw.get("groups") or {}).values() for c in g.get("columns") or []]
    for k, want in (("symbol", sym), ("tf", tf), ("config_hash", ch)):
        if str(sub_m.get(k)) != want:
            problems.append(f"manifest.{k}={sub_m.get(k)!r} != 來源 {want!r}")
    if raw.get("complete") is not True:
        problems.append("raw 節點非 complete")
    if int(raw.get("total_features") or 0) != len(chosen) or sorted(cols) != sorted(chosen) or len(set(cols)) != len(cols):
        problems.append(f"raw 欄 {len(cols)}／total_features {raw.get('total_features')} != 所選 {len(chosen)} 欄")
    if int(sub_m.get("row_count") or -1) != int(src_m.get("row_count") or -2):
        problems.append(f"row_count {sub_m.get('row_count')} != 來源 {src_m.get('row_count')}")
    keys = numeric_view.load_contract()["manifest_keys"]
    for r in ("fingerprint", "algorithm_id", "route_identity"):
        k = keys[r]
        if sub_m.get(k) != src_m.get(k):
            problems.append(f"頂層 {k} != 來源")
        if k in ((src_m.get("artifacts") or {}).get("raw") or {}) and raw.get(k) != src_m["artifacts"]["raw"][k]:
            problems.append(f"raw 節點 {k} != 來源")
    src_idx = src_reader.load_row_index_v2(sym, tf, ch, artifact_kind="raw")
    sub_idx = sub_reader.load_row_index_v2(sym, tf, ch, artifact_kind="raw")
    if src_idx is None or sub_idx is None or not src_idx.equals(sub_idx):
        problems.append("時間軸 sidecar 與來源不同（或缺）")
    src_frames = dict(src_reader.stream_groups_v2(sym, tf, ch, "raw", consumer="strict"))
    by_col = {str(c): (g, c) for g, f in src_frames.items() for c in f.columns}
    n_read = 0
    for _g, frame in sub_reader.stream_groups_v2(sym, tf, ch, "raw", consumer="strict"):
        n_read += int(frame.shape[1])
        if int(frame.shape[0]) != int(src_m.get("row_count") or -1):
            problems.append(f"讀回列數 {frame.shape[0]} != row_count")
        for c in frame.columns:
            g, sc = by_col.get(str(c), (None, None))
            if g is None or not np.array_equal(np.asarray(frame[c].to_numpy()), np.asarray(src_frames[g][sc].to_numpy()),
                                               equal_nan=True) or frame[c].dtype != src_frames[g][sc].dtype:
                problems.append(f"欄 {c} 之值或 dtype 與來源不同")
                break
    if n_read != len(chosen):
        problems.append(f"stream_groups_v2 讀回欄數 {n_read} != {len(chosen)}")
    if problems:
        raise HarnessError("IC-first 子集 run 驗證失敗（SPEC v5.52 (c)；改走三次生成）：" + "；".join(problems[:10]))
    src_tr = ((src_m.get("artifacts") or {}).get("raw") or {}).get("time_range")
    return {"ok": True, "n_cols": len(chosen), "row_count": int(sub_m.get("row_count") or 0),
            "feature_schema_hash": raw.get("feature_schema_hash"), "group_count": raw.get("group_count"),
            "time_range": raw.get("time_range"), "source_time_range": src_tr, "time_range_equal": raw.get("time_range") == src_tr,
            "reader": "FeatureReader.load_manifest_v2(consumer=strict)＋load_row_index_v2＋stream_groups_v2",
            "validated_by": "ICEngine._validate_l7_raw_manifest"}


def write_icfirst_subset(src_root: Path, dst_root: Path, sym: str, tf: str, ch: str, n_cols: int, seed: int) -> List[str]:
    """`prepare_icfirst_subset` 之寫出核心（秒級測試以產品寫出端所建之 run 驗之）：來源 run 目錄除 `raw/` 外複製至
    `dst_root/<sym>/<tf>/<ch>/`；來源 raw 群組依 manifest 欄序之 `default_rng(seed).permutation` 前 `n_cols` 個取欄、索引設
    來源時間軸後經 `FeatureStorage(dst_root).write_raw(..., row_index=來源時間軸, numeric_identity=來源之生成層級身分)` 寫出；
    回所選欄名（manifest 欄序）。`n_cols` 不在 (0, raw 欄數) 或來源無時間軸 ⇒ HarnessError。"""
    import shutil

    import numpy as np

    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    reader = FeatureReader(str(src_root))
    src_m = reader.load_manifest_v2(sym, tf, ch, artifact_kind="raw", consumer="strict")
    order = [str(c) for g in ((src_m.get("artifacts") or {}).get("raw") or {}).get("groups", {}).values()
             for c in g.get("columns") or []]
    if not 0 < int(n_cols) < len(order):
        raise HarnessError(f"IC-first 子集欄數 {n_cols} 不在 (0, {len(order)})（raw 欄數；資料不足）")
    pick = np.sort(np.random.default_rng(int(seed)).permutation(len(order))[:int(n_cols)])
    chosen = [order[int(i)] for i in pick]
    keep = set(chosen)
    row_index = reader.load_row_index_v2(sym, tf, ch, artifact_kind="raw")
    if row_index is None:
        raise HarnessError("IC-first raw run 無時間軸 sidecar（舊 run），無法重寫子集")
    shutil.copytree(Path(src_root) / sym / tf / ch, Path(dst_root) / sym / tf / ch, symlinks=True,
                    ignore=shutil.ignore_patterns("raw", ".tmp-*", ".previous-*"))
    groups = {}
    for gid, frame in reader.stream_groups_v2(sym, tf, ch, "raw", consumer="strict"):
        cols = [c for c in frame.columns if str(c) in keep]
        if cols:
            sub = frame[cols].copy()
            sub.index = row_index
            groups[gid] = sub
    FeatureStorage(str(dst_root)).write_raw(sym, tf, ch, groups, row_index=row_index,
                                            numeric_identity=_numeric_identity_of(src_m))
    return chosen


def prepare_icfirst_subset(out_root: Path, n_cols: int, rows: Optional[int] = None) -> Dict[str, Any]:
    """SPEC v5.52 (c)：IC-first 之 N 欄子集 run——以一次生成之 raw run（`rows`＝窗長；None＝基準窗長）經產品寫出端
    `FeatureStorage.write_raw`（`feature_storage.py:705`）重寫：① run 目錄除 `raw/` 外原樣複製至子集根（manifest 根之 completeness
    與 NUMVIEW 身分、命名世代由產品寫出端之合併保留，`feature_storage.py:2178-2241`）；② 來源 raw 群組（`stream_groups_v2`）
    依 manifest 欄序之 `default_rng(SEED).permutation` 前 N 個（巢狀）取欄、索引設為來源時間軸（`load_row_index_v2`；
    parquet 不存索引，`_build_l7_v2_table` preserve_index=False），`write_raw(..., row_index=來源時間軸, numeric_identity=來源
    之生成層級身分)` ⇒ 欄數、群組、schema hash、列數、時間範圍、時間軸 sidecar 皆由產品寫出端產生（不手造）；③
    `verify_icfirst_subset`（不成立 ⇒ HarnessError）。身分 sidecar（`icfirst_subset_identity`＋驗證紀錄）相同 ⇒ 沿用。"""
    fb = _fb()
    out_root = Path(out_root) if Path(out_root).is_absolute() else REPO / out_root
    rec, _rec_path = _icfirst_record(rows)
    want = icfirst_subset_identity(n_cols, rows)
    base = out_root / ICFIRST_SUBSETS_DIR / icfirst_subset_tag(n_cols, rows)
    side = base / SUBSET_IDENTITY_FILE
    sym, tf, ch = str(rec["symbol"]), str(rec["timeframe"]), str(rec["config_hash"])
    froot = base / "features"
    run_dir = froot / sym / tf / ch
    stored = read_identity(side) or {}
    if stored.get("identity") == json.loads(json.dumps(want)) and (run_dir / "feature_manifest.json").is_file():
        return {"reused": True, "dir": _rel(base), **stored}
    if base.exists():
        # 身分不同之舊子集：改寫至新世代目錄（不刪既有檔）
        base = out_root / ICFIRST_SUBSETS_DIR / f"{icfirst_subset_tag(n_cols, rows)}.{time.strftime('%Y%m%dT%H%M%S')}"
        side, froot = base / SUBSET_IDENTITY_FILE, base / "features"
        run_dir = froot / sym / tf / ch
    src_root = Path(rec["features_root"])
    chosen = write_icfirst_subset(src_root, froot, sym, tf, ch, int(n_cols), int(fb.SEED))
    check = verify_icfirst_subset(src_root, froot, rec, chosen)
    payload = {"identity": want, "verification": check, "features_root": _rel(froot), "run_dir": _rel(run_dir),
               "chosen_sha256": hashlib.sha256(json.dumps(chosen, ensure_ascii=False).encode("utf-8")).hexdigest(),
               "writer": "momentum.FeatureEngineering.feature_storage:FeatureStorage.write_raw", "head": _git_head()}
    write_identity(side, payload)
    return {"reused": False, "dir": _rel(base), **payload}


def prepare_icfirst_subsets(out_root: Path, *, n_cols: Sequence[int] = SCALE_POINTS,
                            rows: Sequence[int] = ICFIRST_ROW_SCALES) -> Dict[str, Any]:
    """`prepare icfirst-subsets`：cols 軸各 N（基準窗長之 raw run）與列軸各窗長 R（`ROW_AXIS_COLS` 欄）之子集 run
    （`prepare_icfirst_subset`；R＝基準窗長者與 cols 軸同 tag 沿用）。工作目錄（cwd／TMPDIR）＝`<out-root>/work/prepare-icfirst-
    <時間>/`（產品之 cwd 相對寫出落此）。任一不成立 ⇒ HarnessError（SPEC v5.52 (c)：改走三次生成）。"""
    out_root = Path(out_root)
    with _prepare_isolation(out_root, "icfirst"):
        done = {f"cols:{int(n)}": prepare_icfirst_subset(out_root, int(n), None) for n in n_cols}
        done.update({f"rows:{int(r)}": prepare_icfirst_subset(out_root, ROW_AXIS_COLS, int(r)) for r in rows})
    return done


@contextlib.contextmanager
def _prepare_isolation(out_root: Path, tag: str) -> Iterable[Path]:
    """prepare 步驟（CLI 單獨行程）之工作目錄隔離（同 `run_one`）：cwd＝`<out-root>/work/prepare-<tag>-<時間>.<pid>/cwd`、
    本行程之 tempfile 根改指同目錄之 iso（產品之 cwd 相對寫出與 tempfile 落此，不放系統暫存）；結束還原 cwd。"""
    work = Path(out_root) / "work" / f"prepare-{tag}-{time.strftime('%Y%m%dT%H%M%S')}.{os.getpid()}"
    (work / "iso").mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(work / "iso")  # 同 run_one：產品之 tempfile 寫入落本次工作目錄
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    cwd = _fb()._prepare_cwd(work / "cwd")
    here = os.getcwd()
    os.chdir(cwd)
    try:
        yield work
    finally:
        os.chdir(here)


def load_icfirst_subset(out_root: Path, n_cols: int, rows: Optional[int]) -> Dict[str, Any]:
    """讀 IC-first 子集 run 之 sidecar：身分須等於現行 `icfirst_subset_identity` 且驗證 ok（SPEC v5.52 (a)(c)），否則
    HarnessError（先跑 `prepare icfirst-subsets`）。同 tag 有多世代者取身分相符之最新者。"""
    want = json.loads(json.dumps(icfirst_subset_identity(n_cols, rows)))
    tag = icfirst_subset_tag(n_cols, rows)
    cands = sorted((Path(out_root) / ICFIRST_SUBSETS_DIR).glob(f"{tag}*"), key=lambda p: p.name, reverse=True)
    for base in cands:
        if base.name != tag and not base.name.startswith(tag + "."):
            continue
        side = read_identity(base / SUBSET_IDENTITY_FILE) or {}
        if side.get("identity") == want and (side.get("verification") or {}).get("ok") is True:
            return {**side, "dir": base}
    raise HarnessError(f"IC-first 子集 run（{tag}）不存在或身分與現行 raw run 不符（先跑 `icperf_scale_harness.py prepare "
                       "icfirst-subsets`；SPEC v5.52 (c)）")


def _run_icfirst_post_generation(ctx: RunContext) -> Dict[str, Any]:
    """SPEC v5.51 (c)／v5.52 (c)：以 `icperf_freeze_baseline.gen-icfirst-raw` 之 A 格 raw run 與其生成結果 metadata（含
    `output_window` 五鍵、config_hash；`icfirst_raw_record`）重建 IC-first ctx（`ic_first_context.begin_context`＋
    `complete_context`，同 `run_ic_first` :2844-2848、:2879），於本次工作目錄之子集 run 複本（post-generation 會寫 processed／
    ic_selected，不寫回子集根）呼叫 `FeatureFactory._run_ic_first_post_generation`（判準檔 A 格 generation 之 ic_engine_config、
    ic_threshold、label_horizon、cleanup_raw）。

    規模：cols 軸 N ⇒ 基準 raw run 經 `FeatureStorage.write_raw` 重寫之 N 欄子集 run（`load_icfirst_subset`；身分由產品寫出端
    產生並經 `verify_icfirst_subset` 驗過）；rows 軸 R ⇒ 窗長 R 之生成（`gen-icfirst-raw --rows R`）之 `ROW_AXIS_COLS` 欄
    子集 run。實際輸入點數＝子集 manifest 之 raw total_features（cols）／公開索引根數（rows）。"""
    import shutil

    import pandas as pd

    from momentum.Analysis.ic_engine import ICEngine
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering import ic_first_context as icc
    from momentum.FeatureEngineering.feature_factory import FeatureGenerationResult
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    rows = ctx.n_rows if ctx.axis == "rows" else None
    rec, rec_path = _icfirst_record(rows)
    sub = load_icfirst_subset(ctx.out_root, ctx.n_cols, rows)
    sub_root = REPO / sub["features_root"]
    n_raw = int(sub["verification"]["n_cols"])
    nfb = _load_script("icperf_t02_numview_freeze_baseline", "scripts/numview_freeze_baseline.py")
    gen_def = rec["generation"]
    label_horizon = str(gen_def["label_horizon"])
    # 寫入隔離同 `_child_ic_first`（`_isolated`：設定檔連結、registry、CGSA、cwd、tempdir、d* 快取導向本次工作目錄）
    with nfb._isolated(ctx.work / "icfirst", {}) as froot:
        src_run = sub_root / rec["symbol"] / rec["timeframe"] / rec["config_hash"]
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
    n_rows = len(rec["features_index"])
    raw_count = int((out.metadata or {}).get("raw_feature_count") or n_raw)
    return {"input_cols": n_raw, "rows": n_rows, "survivors": selected, "requested_columns": None,
            "raw_record": _rel(rec_path), "subset": _rel(Path(sub["dir"]) / SUBSET_IDENTITY_FILE),
            "ctx_complete": bool(full.complete), "raw_feature_count": raw_count,
            "actual_scale": n_rows if ctx.axis == "rows" else n_raw}


def _tail_rows(v: Any, n_src: int, rows: int) -> Any:
    """存檔參數之末 `rows` 列：首維＝來源列數 `n_src` 之 DataFrame／Series／ndarray 取末 `rows` 列，其餘原樣。"""
    shape = getattr(v, "shape", None)
    if not shape or int(shape[0]) != int(n_src):
        return v
    return v.iloc[-rows:] if hasattr(v, "iloc") else v[-rows:]


def cell_capture(ctx: RunContext, name: str) -> Dict[str, Any]:
    """直接呼叫格之存檔真實輸入：cols 軸＝C 格 `stage_inputs/<N>/`；rows 軸＝L 格 `stage_inputs/L<cols>_rows<R>/`（由
    ic_page_long rows 軸寫出）。`CELL_ROW_SCALES` 所列之格（短序列分支）之 rows 軸＝最小列長之 L 格存檔取末 R 列（R ≤ 該存檔
    列數，否則 HarnessError）。SPEC v5.52 (a)：存檔目錄之身分須等於現行來源之子集身分（`expected_stage_identity`）。
    SPEC v5.56 (k)(l)：冗餘格（`REDUNDANCY_STAGE_CELLS`）改經 `redundancy_stage_capture`（cols 軸＝stage_cols 設計點、rows 軸＝
    固定欄集合）。"""
    if ctx.run_id in REDUNDANCY_STAGE_CELLS and name in ("redundancy_filter", "diversification_metrics"):
        return redundancy_stage_capture(ctx, name)
    if ctx.axis != "rows" or ctx.run_id not in CELL_ROW_SCALES:
        want = expected_stage_identity(ctx, ctx.n_rows)
        cap = load_capture(ctx.stage_dir, name, want)
        # SPEC v5.52 (b)：實際輸入點數＝存檔所屬子集之欄數（cols 軸）／列長（rows 軸），由身分 sidecar 驗得
        ctx.actual_scale = int(want["subset"]["n_cols"] if ctx.axis == "cols" else want["subset"]["rows"])
        return cap
    base = ctx.out_root / "stage_inputs" / ctx.stage_tag(ROW_AXIS_SCALES[0])
    cap = load_capture(base, name, expected_stage_identity(ctx, ROW_AXIS_SCALES[0]))
    frames = [a for a in list(cap["args"]) + list(cap["kwargs"].values()) if hasattr(a, "shape") and len(a.shape) >= 1]
    if not frames:
        raise HarnessError(f"{ctx.run_id}：存檔 {name} 無列軸參數，無法取末 {ctx.n_rows} 列")
    n_src = int(frames[0].shape[0])
    if int(ctx.n_rows or 0) > n_src:
        raise HarnessError(f"{ctx.run_id}：rows {ctx.n_rows} > 存檔列數 {n_src}（資料不足）")
    rows = int(ctx.n_rows or 0)
    tailed = [_tail_rows(a, n_src, rows) for a in frames]
    ctx.actual_scale = int(tailed[0].shape[0])
    return {**cap, "args": tuple(_tail_rows(a, n_src, rows) for a in cap["args"]),
            "kwargs": {k: _tail_rows(v, n_src, rows) for k, v in cap["kwargs"].items()},
            "provenance": {**dict(cap.get("provenance") or {}), "tail_rows": rows, "source_rows": n_src}}


def _datetime_axis(frame: Any) -> Any:
    """第 1 段輸出之時間軸為 epoch 整數（秒或毫秒；2026-11-01 smoke 實查 C／L 格為秒）⇒ 轉 DatetimeIndex（產品其後同轉）；
    其餘原樣。"""
    import pandas as pd

    if not isinstance(frame.index, pd.DatetimeIndex) and pd.api.types.is_integer_dtype(frame.index):
        raw_idx = frame.index.to_numpy(dtype="int64")
        unit = "ms" if len(raw_idx) and int(abs(raw_idx).max()) > 10 ** 11 else "s"
        return frame.set_axis(pd.DatetimeIndex(pd.to_datetime(raw_idx, unit=unit)), axis=0)
    return frame


def _columns_sha(cols: Sequence[str]) -> str:
    return hashlib.sha256(json.dumps([str(c) for c in cols], ensure_ascii=False).encode("utf-8")).hexdigest()


def _stage6_parts(cap: Mapping[str, Any]) -> Tuple[Any, Dict[str, Any]]:
    """`RedundancyFilter.filter` 存檔之 (self, 綁定參數 dict)。"""
    obj = cap["self"]
    ba = inspect.signature(type(obj).filter).bind(obj, *cap["args"], **cap["kwargs"])
    return obj, {k: v for k, v in ba.arguments.items() if k != "self"}


def _restrict_scores(scores: Mapping[str, Any], cols: Sequence[str], where: str) -> Dict[str, Any]:
    missing = [c for c in cols if c not in scores]
    if missing:
        raise HarnessError(f"{where}：IC 分數缺所選欄 {missing[:5]}（共 {len(missing)} 欄；分數與欄集合須同步對齊）")
    return {c: scores[c] for c in cols}


def _restrict_metadata(md: Any, cols: Sequence[str]) -> Any:
    """特徵 metadata（特徵名 ⇒ 屬性）限所選欄（同步對齊；非 dict 原樣）。"""
    if not isinstance(md, Mapping):
        return md
    keep = set(cols)
    return {k: v for k, v in md.items() if k in keep}


def redundancy_stage_capture(ctx: RunContext, name: str) -> Dict[str, Any]:
    """SPEC v5.56 (k)(l)：冗餘格之存檔輸入（`name`＝"redundancy_filter"〔`RedundancyFilter.filter` 之第 6 段輸入〕或
    "diversification_metrics"〔取其 metadata〕）。

    cols 軸（(l) stage_cols 設計點）：讀 `RL<REDUNDANCY_STAGE_SOURCE_COLS>`（ic_page_relaxed cols 該點寫；身分＝
    `relaxed_identity`）之第 6 段真實輸入（測試段列 × K 欄），取 `seeded_columns(K 欄, scale)`（SEED 同
    `_write_stage5_subset`、巢狀）；scale > K ⇒ HarnessError（資料不足）。
    rows 軸（(k) 單變數）：欄集合固定為最小 rows 點（`RL<cols>_rows<ROW_AXIS_SCALES[0]>`）之第 6 段輸入欄；各 R 點之值取該 R 點
    第 1 段輸出（`preprocess` 存檔之 result）於該 R 點第 6 段輸入之列（測試段）——該 R 點自身第 6 段輸入欄與固定欄之交集須逐值
    相等（`DataFrame.equals`；不等 ⇒ HarnessError：第 1 段輸出非第 6 段之輸入）、交集須非空；IC 分數取該 R 點之分數限固定欄
    （缺 ⇒ HarnessError）。兩軸之 metadata 皆限所選欄。路徑事實經 provenance 記欄集合之 sha256（`COLUMN_SET_KEY`）、欄數、
    來源。`ctx.actual_scale`＝cols 軸實際送入之欄數／rows 軸存檔身分之列長。"""
    fb = _fb()
    if ctx.axis == "cols":
        src_tag = f"RL{int(REDUNDANCY_STAGE_SOURCE_COLS)}"
        want = {"subset": relaxed_identity(int(REDUNDANCY_STAGE_SOURCE_COLS), None), "writer": ["ic_page_relaxed", "cols"]}
        base = load_capture(ctx.out_root / "stage_inputs" / src_tag, "redundancy_filter", want)
        obj, args = _stage6_parts(base)
        pool = [str(c) for c in args["features_df"].columns]
        if not pool:
            raise HarnessError(f"{ctx.run_id}：{src_tag} 第 6 段輸入 0 欄（stage_cols 軸無來源；SPEC v5.56 (l)）")
        if int(ctx.scale) > len(pool):
            raise HarnessError(f"{ctx.run_id}：stage_cols {ctx.scale} > {src_tag} 第 6 段輸入 {len(pool)} 欄（資料不足；須重定 "
                               "REDUNDANCY_STAGE_COLS_SCALES，SPEC v5.56 (l)）")
        cols = seeded_columns(pool, int(ctx.scale), fb.SEED)
        frame = args["features_df"][cols]
        scores = _restrict_scores(args["ic_scores"], cols, f"{ctx.run_id}:{src_tag}")
        prov = {"stage_cols_source": src_tag, "stage_cols_total": len(pool), "stage_cols_rule": REQUEST_COLUMN_RULE,
                "stage_cols_basis": REDUNDANCY_STAGE_COLS_BASIS, COLUMN_SET_KEY: _columns_sha(cols),
                "n_columns": len(cols), "rows": int(frame.shape[0])}
        ctx.actual_scale = len(cols)
        cur = base
        src_dir = ctx.out_root / "stage_inputs" / src_tag
        src_want = want
    elif ctx.axis == "rows":
        design = REDUNDANCY_ROWS_DESIGN_COLS.get(ctx.run_id)
        if design is None:
            # SPEC v5.56 (k)：固定欄集合＝最小 rows 點之全部第 6 段輸入欄
            lo = int(ROW_AXIS_SCALES[0])
            fixed_tag = ctx.stage_tag(lo)
            base = load_capture(ctx.out_root / "stage_inputs" / fixed_tag, "redundancy_filter",
                                expected_stage_identity(ctx, lo))
            _o, base_args = _stage6_parts(base)
            cols = [str(c) for c in base_args["features_df"].columns]
            if not cols:
                raise HarnessError(f"{ctx.run_id}：{fixed_tag} 第 6 段輸入 0 欄（rows 軸固定欄集合為空；SPEC v5.56 (k)）")
            fixed_prov: Dict[str, Any] = {"fixed_columns_source": fixed_tag}
        else:
            # SPEC v5.57 (r)：固定欄集合＝stage_cols 中點之 seeded 設計點（RL<來源欄數> 第 6 段真實輸入之
            # `seeded_columns(·, design)`，與 cols 軸同欄數點同一欄集合）；設計點 > 來源欄數 ⇒ HarnessError（資料不足）
            fixed_tag = f"RL{int(REDUNDANCY_STAGE_SOURCE_COLS)}"
            dwant = {"subset": relaxed_identity(int(REDUNDANCY_STAGE_SOURCE_COLS), None),
                     "writer": ["ic_page_relaxed", "cols"]}
            base = load_capture(ctx.out_root / "stage_inputs" / fixed_tag, "redundancy_filter", dwant)
            _o, base_args = _stage6_parts(base)
            pool = [str(c) for c in base_args["features_df"].columns]
            if int(design) > len(pool):
                raise HarnessError(f"{ctx.run_id}：rows 軸設計點 {design} 欄 > {fixed_tag} 第 6 段輸入 {len(pool)} 欄（資料不足；"
                                   "SPEC v5.57 (r)）")
            cols = seeded_columns(pool, int(design), fb.SEED)
            fixed_prov = {"fixed_columns_source": fixed_tag, "fixed_columns_rule": REQUEST_COLUMN_RULE,
                          "design_cols": int(design), "design_basis": "SPEC v5.57 (r)：stage_cols 中點之 seeded 設計點",
                          "stage_cols_total": len(pool)}
        src_want = expected_stage_identity(ctx, ctx.n_rows)
        src_dir = ctx.stage_dir
        cur = load_capture(src_dir, "redundancy_filter", src_want)
        pre = load_capture(src_dir, "preprocess", src_want)
        obj, args = _stage6_parts(cur)
        own = args["features_df"]
        res = pre.get("result")
        full = _datetime_axis(res[0] if isinstance(res, tuple) else res)
        own_t = _datetime_axis(own)
        own_cols = [str(c) for c in own.columns]
        missing = [c for c in cols if c not in full.columns]
        missing_own = [c for c in own_cols if c not in full.columns]
        if missing or missing_own or not set(own_t.index) <= set(full.index):
            raise HarnessError(f"{ctx.run_id}：{ctx.stage_tag(ctx.n_rows)} 第 1 段輸出缺固定欄 {missing[:5]}、缺第 6 段輸入欄 "
                               f"{missing_own[:5]} 或缺第 6 段之列")
        dtypes = set(str(t) for t in own.dtypes)

        def _from_stage1(names: Sequence[str]) -> Any:
            f = full.loc[own_t.index, list(names)]
            if len(dtypes) == 1:
                f = f.astype(next(iter(dtypes)))
            return f.set_axis(own.index, axis=0)

        frame = _from_stage1(cols)
        # 取值機制之驗證（SPEC v5.56 (k)，v5.57 (r) 擴為該 R 點自身第 6 段輸入之全部欄）：第 1 段輸出於第 6 段之列（逐欄轉為
        # 第 6 段輸入之 dtype）須與第 6 段輸入逐值相等（設計點之欄可不在該 R 點第 6 段輸入內，故驗取值機制本身，不只驗與固定欄
        # 之交集）
        overlap = [c for c in cols if c in set(own_cols)]
        own_view = full.loc[own_t.index, list(own.columns)].astype(own.dtypes.to_dict()).set_axis(own.index, axis=0) \
            if own_cols else None
        if own_view is None or not own_view.equals(own):
            raise HarnessError(f"{ctx.run_id}：{ctx.stage_tag(ctx.n_rows)} 第 1 段輸出（測試段列）與第 6 段輸入（{len(own_cols)} 欄）"
                               "不逐值相等（或第 6 段輸入 0 欄；SPEC v5.56 (k) 不得以未驗之值代入）")
        scores = _restrict_scores(args["ic_scores"], cols, f"{ctx.run_id}:{ctx.stage_tag(ctx.n_rows)}")
        prov = {**fixed_prov, COLUMN_SET_KEY: _columns_sha(cols), "n_columns": len(cols),
                "rows": int(frame.shape[0]), "values_source": f"{ctx.stage_tag(ctx.n_rows)}/preprocess.result",
                "verified_overlap_columns": len(overlap), "verified_own_columns": len(own_cols),
                "own_stage6_columns": int(own.shape[1])}
        ctx.actual_scale = int(src_want["subset"]["rows"])
    else:
        raise HarnessError(f"{ctx.run_id}：冗餘格不支援 {ctx.axis} 軸")
    if name == "redundancy_filter":
        kwargs = {k: v for k, v in args.items() if k not in ("features_df", "ic_scores")}
        return {**cur, "self": obj, "args": (frame, scores), "kwargs": kwargs,
                "provenance": {**dict(cur.get("provenance") or {}), **prov}}
    meta = load_capture(src_dir, "diversification_metrics", src_want)
    mobj = meta["self"]
    mba = inspect.signature(type(mobj).compute_diversification_metrics).bind(mobj, *meta["args"], **meta["kwargs"])
    margs = dict(mba.arguments)
    margs.pop("self", None)
    margs["metadata"] = _restrict_metadata(margs.get("metadata"), cols)
    return {**meta, "args": (), "kwargs": margs, "provenance": {**dict(meta.get("provenance") or {}), **prov}}


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
    prov = cap.get("provenance") or {}
    out = {"input_cols": ctx.n_cols, "rows": int(f.shape[0]) if f is not None else 0,
           "cell_input_cols": int(f.shape[1]) if f is not None else 0, "requested_columns": None,
           "capture_provenance": prov}
    if isinstance(prov, Mapping) and prov.get(COLUMN_SET_KEY):
        # SPEC v5.56 (k)：冗餘格之欄集合身分（rows 軸各點須相同，組裝斷言）
        out[COLUMN_SET_KEY] = prov[COLUMN_SET_KEY]
    if ctx.run_id in REDUNDANCY_STAGE_CELLS:
        # SPEC v5.57 (r)：量測環境之 BLAS 執行緒（不另設；記實值）
        out["blas_threads"] = blas_thread_facts()
    return out


def blas_thread_facts() -> Dict[str, Any]:
    """SPEC v5.57 (r)：本行程之 BLAS 執行緒環境——`BLAS_THREAD_ENV_KEYS` 各環境變數之實值（未設 ⇒ None；harness 不設），
    與 threadpoolctl（可匯入時）所見各 BLAS／OpenMP 函式庫之實際執行緒數（不可匯入 ⇒ None）。"""
    out: Dict[str, Any] = {"env": {k: os.environ.get(k) for k in BLAS_THREAD_ENV_KEYS}, "threadpools": None,
                           "policy": "SPEC v5.57 (r)：Task 0.2 量現行碼之實際行為，不另設執行緒數"}
    try:
        from threadpoolctl import threadpool_info
    except ImportError:
        return out
    out["threadpools"] = [{k: d.get(k) for k in ("user_api", "internal_api", "num_threads", "version")}
                          for d in threadpool_info()]
    return out


def _cell_redundancy(method: Optional[str]) -> Callable[[RunContext], Dict[str, Any]]:
    """`method` None ⇒ 存檔之 method（產品預設；SPEC v5.56 (k) `redundancy_greedy_rows`）。"""
    def run(ctx: RunContext) -> Dict[str, Any]:
        _, cap = _engine_cell(ctx, "redundancy_filter", "filter", **({"method": method} if method else {}))
        return {**_cell_facts(ctx, cap), "survivors": None,
                "method": method or cap["kwargs"].get("method")}
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


# ── SPEC v5.55 (f)：深度分析預設設定下 0 呼叫之入口之直接呼叫格（讀深度分析路徑存之真實輸入） ─────────────────────


def _cell_pca(ctx: RunContext) -> Dict[str, Any]:
    """`FactorOrthogonalizer.pca_orthogonalize`（產品於 `factor_orthogonalization.method == "pca"` 時呼叫，
    `ic_filter_orchestrator.py:3680-3682`；預設 gram_schmidt，`ic_config_schema.py:302`）：存檔 gram_schmidt 之 factors
    （深度分析入選欄）＋同一正交化器物件。"""
    cap = cell_capture(ctx, "orthogonalize")
    obj = cap["self"]
    factors = inspect.signature(type(obj).gram_schmidt).bind(obj, *cap["args"], **cap["kwargs"]).arguments["factors"]
    _transformed, summary = type(obj).pca_orthogonalize(obj, factors)
    return {**_cell_facts(ctx, cap, frame=factors), "survivors": int(factors.shape[1]),
            "pca_skipped": bool(summary.get("skipped"))}


def _cell_beta_neutral(ctx: RunContext) -> Dict[str, Any]:
    """`FactorExposureAnalyzer._apply_beta_neutralization`（產品於 `neutralization_mode == "beta_neutral"` 時經
    `neutralize_factor_matrix` 呼叫，`factor_exposure_analyzer.py:117-118`；預設 none，`ic_config_schema.py:308`）：存檔
    neutralize_factor_matrix 之 factor_values、market_proxy（trailing close-ret，`ic_filter_orchestrator.py:3733-3737`）
    ＋同一分析器，mode＝beta_neutral。"""
    cap = cell_capture(ctx, "neutralize")
    obj = cap["self"]
    ba = inspect.signature(type(obj).neutralize_factor_matrix).bind(obj, *cap["args"], **cap["kwargs"])
    values = ba.arguments["factor_values"]
    _bind_call(type(obj).neutralize_factor_matrix, obj, cap, mode="beta_neutral")
    return {**_cell_facts(ctx, cap, frame=values), "survivors": int(values.shape[1])}


def param_family_frame(cap: Mapping[str, Any], pre: Mapping[str, Any]) -> Tuple[Any, Dict[str, Any], Dict[str, Any]]:
    """參數敏感度格之輸入：存檔 batch_analyze 之 (self, features_df〔深度分析入選欄〕, labels, metadata, method, direction) 與
    同一路徑第 1 段輸出（preprocess 存檔之 result，全部 N 欄）。家族＝產品 `detect_feature_families`（metadata 之 indicator
    分組優先、否則名稱樣式 `^(.+?)_(\\d+)$`，`parameter_sensitivity_analyzer.py:46-74`）於第 1 段輸出全部欄之結果中，成員數 ≥
    max(min_family_size, 3)（`:172-180`）之最小者（同數取名稱字典序首個；同 `icperf_correctness_receipt.family_aware_subset`
    之規則）；入選欄須於第 1 段輸出逐值相等（`DataFrame.equals`；不等 ⇒ HarnessError：兩存檔非同一份特徵）。回 (併入家族成員後
    之 features_df, batch_analyze 之其餘參數, 事實)。"""
    obj = cap["self"]
    ba = inspect.signature(type(obj).batch_analyze).bind(obj, *cap["args"], **cap["kwargs"])
    sel = ba.arguments["features_df"]
    res = pre.get("result")
    full = res[0] if isinstance(res, tuple) else res
    if full is None or not hasattr(full, "columns"):
        raise HarnessError("param_sensitivity：preprocess 存檔無第 1 段輸出（result）")
    import pandas as pd

    if not isinstance(full.index, pd.DatetimeIndex) and pd.api.types.is_integer_dtype(full.index):
        # 第 1 段之時間軸為 epoch 整數（秒或毫秒；2026-11-01 smoke 實查 C 格為秒），其後產品轉為 DatetimeIndex
        raw_idx = full.index.to_numpy(dtype="int64")
        unit = "ms" if len(raw_idx) and int(abs(raw_idx).max()) > 10 ** 11 else "s"
        full = full.set_axis(pd.DatetimeIndex(pd.to_datetime(raw_idx, unit=unit)), axis=0)
    missing = [c for c in sel.columns if c not in full.columns]
    if missing or not full.index.equals(sel.index) \
            or not full[list(sel.columns)].astype("float64").equals(sel.astype("float64")):
        raise HarnessError(f"param_sensitivity：入選欄與第 1 段輸出不一致（缺 {missing[:5]}）——兩存檔非同一份特徵")
    full = full.set_axis(sel.index, axis=0)
    metadata = ba.arguments.get("metadata")
    threshold = max(int(ba.arguments.get("min_family_size", 3)), int(obj._min_family_size))
    fams = {k: v for k, v in obj.detect_feature_families(list(full.columns), metadata).items() if len(v) >= threshold}
    if not fams:
        raise HarnessError(f"param_sensitivity：第 1 段輸出 {full.shape[1]} 欄無成員數 ≥ {threshold} 之參數家族（資料不足）")
    fam = min(fams, key=lambda k: (len(fams[k]), k))
    cols = list(sel.columns) + [c for c in fams[fam] if c not in set(sel.columns)]
    kwargs = {k: v for k, v in ba.arguments.items() if k not in ("self", "features_df")}
    facts = {"family": fam, "family_members": len(fams[fam]), "selected": int(sel.shape[1]), "survivors": len(cols)}
    return full.loc[sel.index, cols], kwargs, facts


def _cell_param_sensitivity(method: Optional[str]) -> Callable[[RunContext], Dict[str, Any]]:
    """`ParameterSensitivityAnalyzer.analyze_from_variants`／`_compute_rolling_icir`（入選欄含 ≥ min_family_size 之參數家族時
    才呼叫，`parameter_sensitivity_analyzer.py:178-181`、`:103`；深度分析預設入選欄〔top_n〕無家族 ⇒ 0 呼叫）與 `_rolling_corr`
    （另須 method ≠ spearman，`:273-276`；預設 `global.default_method` spearman，`ic_config_schema.py:19`）：`param_family_frame`
    之輸入＋同一分析器物件呼叫 batch_analyze（`method` None ⇒ 存檔之請求方法）。"""
    def run(ctx: RunContext) -> Dict[str, Any]:
        cap = cell_capture(ctx, "param_sensitivity")
        pre = cell_capture(ctx, "preprocess")
        frame, kwargs, facts = param_family_frame(cap, pre)
        if method is not None:
            kwargs["method"] = method
        obj = cap["self"]
        out = type(obj).batch_analyze(obj, frame, **kwargs)
        facts.update(method=kwargs.get("method"), families_analyzed=int((out.get("summary") or {}).get("total_families") or 0))
        return {**_cell_facts(ctx, cap, frame=frame), **facts}
    return run


def param_families_frame(cap: Mapping[str, Any], pre: Mapping[str, Any], n_families: int,
                         members: int = PARAM_FAMILY_MEMBERS) -> Tuple[Any, Dict[str, Any], Dict[str, Any]]:
    """SPEC v5.56 (o)：家族數軸之輸入——存檔 batch_analyze 之 (self, labels, metadata, method, direction)（入選欄只作兩存檔同一份
    特徵之驗證，同 `param_family_frame`）與第 1 段輸出（`pre` 之 result；L 格 `PARAM_FAMILY_SOURCE_COLS` 欄）。家族＝產品
    `detect_feature_families`（同 metadata）於第 1 段輸出全部欄之結果中成員數 ≥ max(min_family_size, `members`) 者；依家族名
    排序後之 `default_rng(SEED).permutation` 前 `n_families` 族（巢狀），每族取產品回傳序之前 `members` 員；features_df＝只含
    這些家族成員欄（不含入選欄：固定每族成員數，避免入選欄混入改變族大小）。產品對該 features_df 之家族判定須恰為
    `n_families` 族、每族 `members` 員（否則 HarnessError）。可用家族 < `n_families` ⇒ HarnessError（資料不足）。回
    (features_df, batch_analyze 之其餘參數, 事實)。"""
    import numpy as np

    fb = _fb()
    obj = cap["self"]
    ba = inspect.signature(type(obj).batch_analyze).bind(obj, *cap["args"], **cap["kwargs"])
    sel = ba.arguments["features_df"]
    res = pre.get("result")
    full = res[0] if isinstance(res, tuple) else res
    if full is None or not hasattr(full, "columns"):
        raise HarnessError("param_sensitivity_families：preprocess 存檔無第 1 段輸出（result）")
    full = _datetime_axis(full)
    missing = [c for c in sel.columns if c not in full.columns]
    if missing or not full.index.equals(sel.index) \
            or not full[list(sel.columns)].astype("float64").equals(sel.astype("float64")):
        raise HarnessError(f"param_sensitivity_families：入選欄與第 1 段輸出不一致（缺 {missing[:5]}）——兩存檔非同一份特徵")
    full = full.set_axis(sel.index, axis=0)
    metadata = ba.arguments.get("metadata")
    threshold = max(int(ba.arguments.get("min_family_size", 3)), int(obj._min_family_size), int(members))
    fams = {k: v for k, v in obj.detect_feature_families(list(full.columns), metadata).items() if len(v) >= threshold}
    if len(fams) < int(n_families):
        raise HarnessError(f"param_sensitivity_families：第 1 段輸出 {full.shape[1]} 欄之 ≥{threshold} 員家族 {len(fams)} 組 < "
                           f"家族數 {n_families}（資料不足）")
    order = sorted(fams)
    pick = [order[int(i)] for i in np.random.default_rng(fb.SEED).permutation(len(order))[:int(n_families)]]
    cols = [c for f in pick for c in fams[f][:int(members)]]
    frame = full.loc[sel.index, cols]
    got = {k: v for k, v in obj.detect_feature_families(cols, metadata).items() if len(v) >= threshold}
    if len(got) != int(n_families) or any(len(v) != int(members) for v in got.values()):
        raise HarnessError(f"param_sensitivity_families：產品對所選欄判得 {len(got)} 族（大小 {sorted(len(v) for v in got.values())}），"
                           f"≠ {n_families} 族 × {members} 員")
    kwargs = {k: v for k, v in ba.arguments.items() if k not in ("self", "features_df")}
    facts = {"families": int(n_families), "family_members": int(members), "families_available": len(fams),
             "family_names": pick, "selected": int(sel.shape[1]), "survivors": len(cols),
             "family_rule": "依家族名排序之 default_rng(SEED).permutation 前 F 族（巢狀）、每族產品回傳序之前 3 員"}
    return frame, kwargs, facts


def _cell_param_families(method: Optional[str]) -> Callable[[RunContext], Dict[str, Any]]:
    """SPEC v5.56 (o)：參數敏感度家族數軸（`families` 軸；主排程外之變體實跑，VARIANT_RUNS）——存檔 batch_analyze 參數取
    `D<ROW_AXIS_COLS>` 之 L 格全長（`LONG_CELL_ROWS`）列存檔（deep_analysis_long rows 軸寫）、第 1 段輸出取
    `L<PARAM_FAMILY_SOURCE_COLS>`（ic_page_long cols 軸寫，`CAPTURE_ONLY` 只存 preprocess）；`param_families_frame` 之 F 族 ×
    3 員＋同一分析器 batch_analyze（`method` None ⇒ 存檔之請求方法）。事實記家族數、每族員數與產品實際分析之家族數
    （summary.total_families；analyze_from_variants 之呼叫數見逐入口紀錄）。"""
    def run(ctx: RunContext) -> Dict[str, Any]:
        fb = _fb()
        rows = int(LONG_CELL_ROWS)
        cap = load_capture(ctx.out_root / "stage_inputs" / ctx.stage_tag(rows), "param_sensitivity",
                           expected_stage_identity(ctx, rows))
        src = subset_source(True)
        pre_want = {"subset": subset_identity(src, n_cols=int(PARAM_FAMILY_SOURCE_COLS), seed=fb.SEED, rows=None),
                    "writer": ["ic_page_long", "cols"]}
        pre = load_capture(ctx.out_root / "stage_inputs" / f"L{int(PARAM_FAMILY_SOURCE_COLS)}", "preprocess", pre_want)
        frame, kwargs, facts = param_families_frame(cap, pre, int(ctx.scale))
        if method is not None:
            kwargs["method"] = method
        obj = cap["self"]
        out = type(obj).batch_analyze(obj, frame, **kwargs)
        facts.update(method=kwargs.get("method"),
                     families_analyzed=int((out.get("summary") or {}).get("total_families") or 0))
        ctx.actual_scale = int(facts["families"])
        return {**_cell_facts(ctx, cap, frame=frame), **facts, "input_cols": int(PARAM_FAMILY_SOURCE_COLS),
                "actual_scale": int(facts["families"])}
    return run


def _cell_mw_fixed(ctx: RunContext) -> Dict[str, Any]:
    """SPEC v5.58 (x)：固定倖存集合之 mann_whitney_table 直接呼叫格（events 軸；真實存檔輸入）。固定倖存集合＝`--ref-scale` 點之
    第 5 段倖存欄（event_import events 軸該點 `_run_binary_permutation_and_negative_control` 之回傳倖存者，存檔 stage5.json；
    空 ⇒ HarnessError，不改取他點）；本點之輸入＝event_import events 軸本點 mann_whitney_table 首次呼叫之 features（限固定倖存
    欄，缺欄 ⇒ HarnessError）、y、min_class_n；經重綁之模組屬性呼叫 `MW_FIXED_CALLS` 次。實際輸入點數＝存檔寫出實跑驗得之事件數。"""
    if ctx.ref_scale is None:
        raise HarnessError(f"{MW_FIXED_CELL}：須給 --ref-scale（固定倖存集合之參考事件數點）")
    ref = load_event_mw(ctx.out_root, int(ctx.ref_scale))
    fixed = [str(c) for c in (ref["stage5"].get("survivors") or [])]
    if not fixed:
        raise HarnessError(f"{MW_FIXED_CELL}：參考點 events={ctx.ref_scale} 之第 5 段倖存欄為空（{ref['dir']}；固定倖存集合不可空，"
                           "不改取他點——補資料或改參考點後再量）")
    cap = load_event_mw(ctx.out_root, int(ctx.n_events or 0))
    mw_cap = cap["mw"]
    features, y = mw_cap["args"][0], mw_cap["args"][1]
    missing = [c for c in fixed if c not in set(map(str, features.columns))]
    if missing:
        raise HarnessError(f"{MW_FIXED_CELL}：events={ctx.n_events} 之存檔輸入缺固定倖存欄 {missing[:5]}（共 {len(missing)}）")
    frame = features[fixed]
    mw = getattr(importlib.import_module(MW_ENTRY.partition(":")[0]), MW_ENTRY.partition(":")[2])
    for _ in range(MW_FIXED_CALLS):
        mw(frame, y, **dict(mw_cap["kwargs"]))
    if not isinstance(cap.get("events"), int):
        raise HarnessError(f"{MW_FIXED_CELL}：存檔 {cap['dir']} 未記寫出實跑驗得之事件數")
    ctx.actual_scale = int(cap["events"])
    return {"input_cols": len(fixed), "rows": int(frame.shape[0]), "events": int(cap["events"]), "survivors": len(fixed),
            "cell_input_cols": len(fixed), COLUMN_SET_KEY: _columns_sha(fixed), "fixed_survivors_ref_scale": int(ctx.ref_scale),
            "fixed_survivors_source": ref["dir"], "input_source": cap["dir"], "selection_rows": int(frame.shape[0]),
            "calls_planned": MW_FIXED_CALLS, "min_class_n": dict(mw_cap["kwargs"]).get("min_class_n"),
            "stage5_at_point": binary_receipt_facts(cap["stage5"]), "threshold_branch": "non_default",
            "requested_columns": None, "actual_scale": int(cap["events"])}


RUNNERS: Dict[str, Callable[[RunContext], Dict[str, Any]]] = {
    "ic_page_default": _run_ic_page_default,
    "ic_page_long": _run_ic_page_default,
    "ic_page_relaxed": _run_ic_page_relaxed,
    "deep_analysis": _run_deep_analysis,
    "deep_analysis_long": _run_deep_analysis,
    "post_ic_transform": _run_post_ic_transform,
    "event_import": _run_event_import,
    "event_study": _run_event_study,
    "cross_sectional": _run_cross_sectional,
    "cross_sectional_long": _run_cross_sectional_long,
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
    "orthogonalize_pca": _cell_pca,
    "exposure_beta_neutral": _cell_beta_neutral,
    "param_sensitivity_family": _cell_param_sensitivity(None),
    "param_sensitivity_pearson": _cell_param_sensitivity("pearson"),
    "redundancy_greedy_rows": _cell_redundancy(None),
    "param_sensitivity_families": _cell_param_families(None),
    "param_sensitivity_families_pearson": _cell_param_families("pearson"),
    MW_FIXED_CELL: _cell_mw_fixed,
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


def record_threshold_branch(run_id: str, axis: str, group: str, facts: Mapping[str, Any]) -> str:
    """紀錄頂層之門檻分支（SPEC v5.55 (d)、v5.56 (k)）：路徑事實之 `threshold_branch`（"default"／"non_default"）優先——
    實際所讀存檔任務之分支；否則非預設門檻路徑（ic_page_relaxed）與讀其存檔之格（R 群組）＝"non_default"，其餘
    "default"。事實之值非兩者之一 ⇒ HarnessError。"""
    got = facts.get("threshold_branch")
    if got is not None:
        if got not in ("default", "non_default"):
            raise HarnessError(f"{run_id}:{axis}：路徑事實 threshold_branch={got!r} 非 default／non_default")
        return str(got)
    return "non_default" if run_id == "ic_page_relaxed" or group == "R" else "default"


def run_one(run_id: str, *, axis: str, scale: int, records_dir: Path, inventory_path: Path = INVENTORY_PATH,
            out_root: Optional[Path] = None, argv: Optional[Sequence[str]] = None,
            ref_scale: Optional[int] = None) -> Path:
    """一個規模點之一次實跑：重綁清冊全部 measure=true 入口 ⇒ 執行 `RUNNERS[run_id]` ⇒ 寫逐入口記錄；回記錄檔路徑。
    工作目錄（cwd／TMPDIR）＝`<out-root>/work/<path_run_id>/`（唯讀輸入以 symlink 引入；產品之 cwd 相對寫出落此）。
    SPEC v5.58 (x)：event_import 各軸另以 `binary_capture_hook` 取第 5 段二元收據（路徑事實）；events 軸另存
    mann_whitney_table 首次呼叫與二元收據於 `EVENT_MW_DIR/E<n>/`（`_event_mw_begin`／`_event_mw_finish`），供
    `MW_FIXED_CELL`（`ref_scale`＝固定倖存集合之參考點）讀。"""
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
    ctx.ref_scale = None if ref_scale is None else int(ref_scale)
    stage_dir: Optional[Path] = None
    stage_want: Optional[Dict[str, Any]] = None
    if (run_id, axis) in CAPTURE_RUNS:
        stage_dir = ctx.stage_dir
        stage_input_card(root / "stage_inputs")
        prov = {"path_run_id": path_run_id, "head": head, "axis": axis, "scale": int(scale), "run_id": run_id,
                "source": "L" if ctx.long else "C"}
        # SPEC v5.52 (a)：存檔目錄之身分（所屬子集之來源內容 sha256、seed、欄數、列長）與本次不同 ⇒ 本次覆寫全部存檔；
        # 開跑前先把 sidecar 標 building（中斷 ⇒ 讀端拒收），成功後標 complete
        stage_want = expected_stage_identity(ctx, ctx.n_rows)
        side = read_identity(stage_dir / STAGE_IDENTITY_FILE) or {}
        same = side.get("status") == "complete" and {k: side.get(k) for k in stage_want} == json.loads(
            json.dumps(stage_want))
        if not same:
            write_identity(stage_dir / STAGE_IDENTITY_FILE, {**stage_want, "status": "building",
                                                              "path_run_id": path_run_id})
        only = CAPTURE_ONLY.get((run_id, axis))
        rec.captures = {eid: _capture_writer(stage_dir, name, with_result, prov, overwrite=not same)
                        for eid, (name, with_result) in CAPTURES.items() if only is None or name in only}
    event_mw: Optional[Dict[str, Any]] = None
    if run_id == "event_import":
        # SPEC v5.58 (x)：第 5 段二元收據（各軸）；events 軸另存 mann_whitney_table 首次呼叫（重綁前設 capture）
        ctx.binary_capture = {}
        rec.captures[BINARY_PERM_ENTRY] = binary_capture_hook(ctx.binary_capture)
        if axis == "events":
            event_mw = _event_mw_begin(ctx, path_run_id)
            rec.captures[MW_ENTRY] = event_mw["writer"]
    os.chdir(cwd)
    targets = resolve_targets(e["id"] for e in measured)
    binding = rebind_all({eid: t.func for eid, t in targets.items()}, rec)
    rec.start()
    try:
        facts = RUNNERS[run_id](ctx)
    finally:
        rec.stop()
        wall = time.time() - started_wall
    # SPEC v5.52 (b)：每一軸實跑須驗實際輸入點數＝宣告之規模（runner 回 actual_scale；直接呼叫格由存檔身分驗得）；不等或
    # 未驗 ⇒ 大聲失敗、不寫紀錄
    if facts.get("actual_scale") is None and ctx.actual_scale is not None:
        facts["actual_scale"] = int(ctx.actual_scale)
    if facts.get("actual_scale") is None or int(facts["actual_scale"]) != int(scale):
        binding.restore()
        raise HarnessError(f"{run_id}:{axis}：實際輸入點數 {facts.get('actual_scale')!r} != 宣告規模 {int(scale)}"
                           "（SPEC v5.52 (b)）")
    if event_mw is not None:
        _event_mw_finish(event_mw, ctx, facts)
    if stage_dir is not None and stage_want is not None:
        # 屬本身分之存檔＝本次成功寫出者（身分不同時）或前次同身分已列者＋本次寫出者（身分相同時）；讀端只認 files 所列
        written = {CAPTURES[eid][0] for eid in CAPTURES
                   if rec.stat(eid).captured and rec.stat(eid).capture_error is None
                   and (stage_dir / f"{CAPTURES[eid][0]}.pkl").is_file()}
        prior = set((read_identity(stage_dir / STAGE_IDENTITY_FILE) or {}).get("files") or []) if same else set()
        write_identity(stage_dir / STAGE_IDENTITY_FILE, {**stage_want, "status": "complete", "path_run_id": path_run_id,
                                                          "files": sorted(written | prior)})
    import resource

    ru = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    record = {"schema": RECORD_SCHEMA, "path_run_id": path_run_id, "run_id": run_id,
              "kind": "path" if run_id in PATHS else "cell", "axis": axis, "scale": int(scale),
              # 交接 h5 子集之來源格（IC 頁／深度分析路徑與直接呼叫格；其餘路徑讀各自之 run，見 facts）
              "handoff_source": (LONG_CELL_ID if ctx.long else "C") if run_id in SUBSET_RUNS or run_id in CELLS else None,
              "row_window_override": ROW_AXIS_WINDOW_OVERRIDE if axis == "rows" and (run_id in SUBSET_RUNS
                                                                                     or run_id == "ic_page_relaxed") else None,
              # SPEC v5.55 (d)：非預設門檻分支之實跑與讀其存檔之格（收據與報告標明）。SPEC v5.56 (k)：路徑事實帶
              # `threshold_branch`（實際所讀存檔任務之分支，如 post_ic_transform rows 軸之 `saved["threshold_branch"]`）者以之
              # 為準（原對 post_ic_transform rows 固定 default 而 facts 可為 non_default）
              "threshold_branch": record_threshold_branch(run_id, axis, ctx.group, facts),
              "actual_scale": int(facts["actual_scale"]), "ref_scale": ctx.ref_scale,
              "event_mw_capture": _rel(Path(event_mw["dir"])) if event_mw is not None else None,
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
    known = KNOWN_TIME_OPPORTUNITIES.get(eid)
    if hit or pending or known:
        # SPEC v5.57 (r)：已有研究實測之時間機會（KNOWN_TIME_OPPORTUNITIES）併入（判準①候選；不改 criteria 之判定）
        why = "；".join(x for x in (f"判準 {'、'.join(hit)} 成立" if hit else "",
                                    f"判準 {'、'.join(pending)} 待 Phase 1 原型補量（v5.51 (f)）" if pending else "",
                                    f"已知機會：{known}" if known else "") if x)
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
AXIS_X_KEY = {"cols": "input_cols", "rows": "rows", "events": "events", "timestamps": "timestamps",
              "survivors": "survivors", "families": "families"}
AXIS_FIT_KEY = {"cols": "stage_cols", "rows": "rows", "events": "events", "timestamps": "timestamps",
                "survivors": "survivors", "families": "families"}


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
           problems: List[str], require_actual: bool = False, require_split: bool = False) -> Optional[Dict[str, Any]]:
    """單一規模點（`q`＝scale_probe 收據之點）。SPEC v5.52 (b)：紀錄之 `actual_scale`（runner 驗得之實際輸入點數）有者須等於
    宣告之規模；`require_actual`（第二軸實跑）⇒ 每份紀錄皆須帶且相等。SPEC v5.53 (c1)：`require_split`（預設切分之變體實跑）
    ⇒ 紀錄之 `split_applied` 須為 True。"""
    eid = e["id"]
    scale = int(q["scale"])
    recs = list((run.get("records") or {}).get(scale) or [])
    if len(recs) != int(q.get("runs") or 0):
        problems.append(f"{eid}：{run['receipt_path']} scale={scale} 之實跑 {q.get('runs')} 次，逐入口記錄 {len(recs)} 份")
        return None
    bad = [r.get("path_run_id") for r in recs
           if ("actual_scale" in r or require_actual) and r.get("actual_scale") != scale]
    if bad:
        problems.append(f"{eid}：{axis} 軸 scale={scale} 之實跑 {bad} 實際輸入點數與宣告規模不符或未驗（SPEC v5.52 (b)）")
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
    if require_split and facts.get("split_applied") is not True:
        problems.append(f"{eid}：{chosen.get('path_run_id')} 未走預設切分（split_applied={facts.get('split_applied')!r}；"
                        "SPEC v5.53 (c1)）")
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
    if axis == "timestamps":
        # SPEC v5.52 (b)：跨標的之第二軸＝時點數（截短時間跨度）
        p["timestamps"] = scale
        p["scale_vector"] = {**sv, **({"timestamps": scale} if "timestamps" in sv else {})}
    if axis == "survivors":
        # SPEC v5.55 (e)：IC 後轉換之主軸＝倖存欄數（ic_page_relaxed 各 cols 點之實際倖存數）
        p["survivors"] = scale
        p["scale_vector"] = {**sv, **({"survivors": scale} if "survivors" in sv else {})}
        p["threshold_branch"] = (chosen.get("facts") or {}).get("threshold_branch")
    if axis == "families":
        # SPEC v5.56 (o)：參數敏感度家族數軸（每族固定員數；scale_vector.survivors＝家族數 × 每族員數）
        p["families"] = scale
        p["family_members"] = facts.get("family_members")
    # SPEC v5.56 (k)：直接呼叫格之實際輸入欄數與欄集合身分（冗餘格 rows 軸各點須相同，組裝斷言）
    p["cell_input_cols"] = facts.get("cell_input_cols")
    p[COLUMN_SET_KEY] = facts.get(COLUMN_SET_KEY)
    p["actual_scale"] = chosen.get("actual_scale")
    if "post_stage5_claim" in facts:
        # SPEC v5.58 (x)：事件入口之點記第 5 段倖存數（scale_vector.survivors）、二元收據與後續統計可否宣稱有實值
        p["post_stage5_claim"] = facts.get("post_stage5_claim")
        p["binary_receipt"] = facts.get("binary_receipt")
        p["stage5_survivors"] = facts.get("survivors")
    binary = facts.get("binary_receipt") if "post_stage5_claim" in facts else facts.get("stage5_at_point")
    if "post_stage5_claim" in facts or "stage5_at_point" in facts:
        # SPEC v5.59 (ai)：各點記事件區塊數（沿用 `binary_receipt_facts` 之 n_blocks；非二元模式 ⇒ None）——二元入口之呼叫數
        # 條件「門檻通過數 k>0 且 n_blocks ≥ 10 時才含置換與負對照」之輸入，與 binary_receipt.threshold_passed 並讀
        p["n_blocks"] = (binary or {}).get("n_blocks")
    return p


def _isolation_section(e: Mapping[str, Any], key: Tuple[str, str], runs: Mapping[Tuple[str, str], Mapping[str, Any]],
                       problems: List[str], *, required: bool, scale_probe: Any) -> Any:
    """SPEC v5.58 (x)：入口之隔離直接呼叫格段（`ISOLATION_RUNS`；固定倖存集合之 mann_whitney）：每點經 `_point`（calls ≥ 1、
    actual_scale＝宣告、footprint），各點欄集合身分與欄數須相同（固定倖存集合）且非空；回 {"run", "axis", "points"（另記
    seconds_per_call）, "fit"（對事件數）, "probe", "fixed_columns": {"n", COLUMN_SET_KEY, "ref_scale"}}；缺實跑 ⇒ `required`
    時記問題並回 False、否則 None；點有問題 ⇒ False。"""
    eid = e["id"]
    run = runs.get(key)
    if run is None:
        if required:
            problems.append(f"{eid}：隔離直接呼叫格 {key[0]}:{key[1]} 缺（SPEC v5.58 (x) 固定倖存集合之單次入口成本）")
            return False
        return None
    pts = [p for q in sorted(run["receipt"]["points"], key=lambda q: int(q["scale"]))
           if (p := _point(e, q, run, key[1], problems, require_actual=True)) is not None]
    if len(pts) != len(run["receipt"]["points"]) or not pts:
        return False
    shas = {p.get(COLUMN_SET_KEY) for p in pts}
    ncols = {p.get("cell_input_cols") for p in pts}
    if len(shas) != 1 or None in shas or len(ncols) != 1 or not all(isinstance(n, int) and n > 0 for n in ncols):
        problems.append(f"{eid}：隔離格 {key[0]} 各點之固定倖存集合不同或為空（欄數 {sorted(map(str, ncols))}；SPEC v5.58 (x)）")
        return False
    calls = {int(p["calls"]) for p in pts}
    if len(calls) != 1:
        problems.append(f"{eid}：隔離格 {key[0]} 各點呼叫數不同（{sorted(calls)}；SPEC v5.58 (x) 每點固定 MW_FIXED_CALLS 次）")
        return False
    for p in pts:
        p["seconds_per_call"] = float(p["seconds"]) / int(p["calls"])
    refs = {(median_record(recs).get("facts") or {}).get("fixed_survivors_ref_scale") for recs in run["records"].values()}
    fit = None
    if len(pts) >= 2:
        f = scale_probe.fit(fit_points(pts, key[1]), float(max(p[AXIS_X_KEY[key[1]]] for p in pts)))
        fit = {"axis": key[1], "exponent": f["fit"]["exponent"], "r2": f["fit"]["r2"],
               "extrapolation_unreliable": f["extrapolation_unreliable"]}
    return {"run": f"{key[0]}:{key[1]}", "axis": key[1], "points": pts, "probe": run["probe"], "fit": fit,
            "fixed_columns": {"n": next(iter(ncols)), COLUMN_SET_KEY: next(iter(shas)),
                              "ref_scale": next(iter(refs)) if len(refs) == 1 else sorted(map(str, refs))},
            "calls_per_point": next(iter(calls)),
            "fit_basis": "每點呼叫數固定（MW_FIXED_CALLS）、欄集合固定 ⇒ 秒數對事件數之冪次擬合＝單次入口成本對事件數之擬合"}


def fixed_column_set_problems(eid: str, run_id: Optional[str], points: Sequence[Mapping[str, Any]], *,
                              col_points: Optional[Sequence[Mapping[str, Any]]] = None) -> List[str]:
    """SPEC v5.56 (k)：冗餘格（`REDUNDANCY_STAGE_CELLS`）rows 軸各點之 `cell_input_cols` 與欄集合身分（`COLUMN_SET_KEY`）須皆
    非空且相同（只變列數）；其餘實跑 ⇒ 無問題。SPEC v5.57 (r)：`REDUNDANCY_ROWS_DESIGN_COLS` 所列之格，rows 軸欄數須＝設計點，
    且 `col_points`（同格 cols 軸之點）給定時，其中欄數＝設計點之點之欄集合身分須與 rows 軸相同（與 stage_cols 中點同欄集合）。"""
    if run_id not in REDUNDANCY_STAGE_CELLS or not points:
        return []
    shas = [p.get(COLUMN_SET_KEY) for p in points]
    ncols = [p.get("cell_input_cols") for p in points]
    if not all(shas) or len(set(shas)) != 1 or not all(isinstance(n, int) and n > 0 for n in ncols) \
            or len(set(ncols)) != 1:
        return [f"{eid}：{run_id} rows 軸各點之第 6 段輸入欄集合或欄數不同（{ncols}；SPEC v5.56 (k) rows 軸須固定欄集合只變列數）"]
    design = REDUNDANCY_ROWS_DESIGN_COLS.get(str(run_id))
    if design is not None:
        if int(ncols[0]) != int(design):
            return [f"{eid}：{run_id} rows 軸欄數 {ncols[0]} ≠ 設計點 {design}（SPEC v5.57 (r)）"]
        if col_points is not None:
            mid = [p.get(COLUMN_SET_KEY) for p in col_points if p.get("cell_input_cols") == int(design)]
            if mid != [shas[0]]:
                return [f"{eid}：{run_id} rows 軸欄集合與 cols 軸 {design} 欄點之欄集合不同（{mid}；SPEC v5.57 (r) 須同欄集合）"]
    return []


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
                           records_root: Optional[str] = None, require_variants: bool = False,
                           require_isolation: bool = False) -> Dict[str, Any]:
    """組 `<日期>-icperf-scale-before.json`（SPEC Task 0.2 v5.50 (e)、v5.51 (d)(f)(g)(h)(i)）。`runs`＝{(run_id, axis):
    {"probe": {"cmd", "data", "config"}, "receipt_path": <repo 相對>, "receipt": <scale_probe 收據>, "records": {scale:
    [逐入口記錄（含 `_record_path`／`_record_bytes`／`_record_sha256`）...]}}}。每一 measure=true 入口依 `branch_cell` 取其
    主軸實跑（`primary_axis`：event_study＝events 軸，其餘 cols 軸），清冊 input_axes 含 rows 者另取 `ROW_AXIS_RUN[cell]` 之
    rows 軸實跑組 row_points（L 格，v5.51 (a)；`require_rows` 而缺 ⇒ 問題）：每點 seconds＝同 path_run_id（多次實跑取牆鐘
    中位數者）之逐入口秒數、peak_rss_bytes＝scale_probe 該點、footprint＝同 path_run_id 之 harness 紀錄（v5.51 (h)）；
    fit＝`scale_probe.fit(fit_points(points, 主軸), full)` 重算。任一問題（漏量、呼叫 0、缺軸、缺 footprint）⇒
    AssemblyError（逐條）。兩點例外（v5.51 (g)）：只在頂層合計推估 `total_projected_seconds(runs)` 逾 `budget_seconds` 時，
    cols 軸 500／1000 推估 2000 欄逾 `two_point_seconds` 之入口方收兩點（2,000 欄實測點移 `excluded_points`，不刪資料）；
    未逾預算者三點皆收。判準②依 `criterion2`（v5.51 (f)），待判者列頂層 `pending_prototype`。
    SPEC v5.52 (b)（與上列衝突處以此為準）：主軸與第二軸依 `entry_runs`；第二軸點存 `row_points`、軸名存 `row_axis`
    （rows／timestamps／events）、實跑存 `row_path`／`row_probe`、擬合存 `row_fit`（含 axis）；第二軸每份紀錄須帶
    `actual_scale` 且等於宣告之規模（主軸紀錄帶者亦須相等）；`require_rows` 涵蓋全部第二軸；頂層 `schedule_coverage`。
    SPEC v5.53：(c0) 事件入口之 K 線根數軸依 `entry_runs`（rows 為主軸或第二軸，軸名 `rows`）；(c1) `VARIANT_RUNS` 所變之格
    之入口另組 `variants`＝{"<run>:<軸>": {"points", "fit", "probe", "split"}}（每點 calls ≥ 1、actual_scale＝宣告、
    split_applied＝True）；`require_variants` 而缺變體實跑 ⇒ 問題。
    SPEC v5.58 (x)：倖存數相依入口（`survivor_dependent`：unit_axis 含 survivors）之 events 軸只記不擬合——第二軸 events 之
    `row_fit`＝None、`row_fit_excluded`（`events_fit_exclusion`：各點事件數、第 5 段倖存數、呼叫數、秒數、post_stage5_claim）；
    主軸為 events ⇒ 問題。事件入口之點另記 `post_stage5_claim`／`binary_receipt`／`stage5_survivors`（`_point`）。`ISOLATION_RUNS`
    之入口另組 `isolation`（`_isolation_section`：固定倖存集合之直接呼叫格，每點同欄集合、同呼叫數，對事件數擬合）；
    `require_isolation` 而缺該實跑 ⇒ 問題。"""
    problems: List[str] = []
    all_records = [r for run in runs.values() for recs in (run.get("records") or {}).values() for r in recs]
    total = total_projected_seconds(runs)
    budget_exceeded = bool(total > float(budget_seconds))
    entries: Dict[str, Any] = {}
    for e in inventory.get("entries") or []:
        if not e.get("measure"):
            continue
        eid, cell = e["id"], e.get("branch_cell")
        # SPEC v5.52 (b)：主軸與第二軸依 `entry_runs`（事件型只隨事件數變者主軸 events；input_axes 含 rows ⇒ rows／跨標的
        # timestamps；事件型 cols 入口之 scale_vector 含 events ⇒ events）
        (prun, axis), second, need_second = entry_runs(e) if cell else ((None, "cols"), None, False)
        run = runs.get((prun, axis)) if cell else None
        if run is None:
            problems.append(f"{eid}：所屬格 {cell!r} 無 {axis} 軸量測")
            continue
        pts = [p for q in sorted(run["receipt"]["points"], key=lambda q: int(q["scale"]))
               if (p := _point(e, q, run, axis, problems)) is not None]
        if len(pts) != len(run["receipt"]["points"]):
            continue
        row_run = None
        row_pts = None
        row_axis = second[1] if second else None
        if need_second:
            row_run = runs.get(second) if second and second[0] else None
            if row_run is None and require_rows:
                problems.append(f"{eid}：清冊 input_axes 含 rows（或事件型入口 scale_vector 含 events），所屬格 {cell!r} 無"
                                f"第二軸實跑（對應 {second!r}；SPEC v5.52 (b)）")
        if row_run is not None:
            row_pts = [p for q in sorted(row_run["receipt"]["points"], key=lambda q: int(q["scale"]))
                       if (p := _point(e, q, row_run, str(row_axis), problems, require_actual=True)) is not None]
            if len(row_pts) != len(row_run["receipt"]["points"]):
                continue
            fixed = fixed_column_set_problems(eid, second[0] if second else None, row_pts,
                                              col_points=pts if second and prun == second[0] else None) \
                if row_axis == "rows" else []
            if fixed:
                problems.extend(fixed)
                continue
        chosen = [r for run_ in (run, row_run) if run_ for recs in run_["records"].values() for r in [median_record(recs)]]
        full = float((run["receipt"].get("projection") or {}).get("scale")
                     or max(p[AXIS_X_KEY[axis]] for p in pts))
        m: Dict[str, Any] = {"coverage_path_id": e["coverage_path_id"], "unit_axis": e["unit_axis"],
                             "branch_cell": cell, "path": prun, "axis": axis, "probe": run["probe"],
                             "row_probe": row_run["probe"] if row_run else None,
                             "row_path": second[0] if row_run else None,
                             "row_axis": row_axis if row_run else None,
                             "fixed_axes": dict(e.get("fixed_axes") or {}) or None}
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
        if events_fit_exclusion(e, axis, pts) is not None:
            # SPEC v5.58 (x)：倖存數相依入口不得以 events 為主軸擬合（清冊須給非 events 之主軸；第二軸 events 只記不擬合）
            problems.append(f"{eid}：倖存數相依入口（unit_axis 含 survivors）之主軸為 events（SPEC v5.58 (x) events 軸只擬合確實"
                            "隨事件數變之入口）")
            continue
        fit = scale_probe.fit(fit_points(pts, axis), full)
        row_fit = None
        row_fit_excluded = events_fit_exclusion(e, row_axis, row_pts or []) if row_pts else None
        if row_pts and len(row_pts) >= 2 and row_fit_excluded is None:
            rf = scale_probe.fit(fit_points(row_pts, str(row_axis)),
                                 float(max(p[AXIS_X_KEY[str(row_axis)]] for p in row_pts)))
            row_fit = {"axis": row_axis, "exponent": rf["fit"]["exponent"], "r2": rf["fit"]["r2"],
                       "extrapolation_unreliable": rf["extrapolation_unreliable"]}
        func = str(e["unit_axis"]["function"])
        unit_seconds, units = unit_cost(e, pts, axis)
        m.update({"points": pts, "row_points": row_pts, "excluded_points": excluded, "two_point_exception": two_point,
                  "fit_axis": AXIS_FIT_KEY[axis],
                  "fit": {"exponent": fit["fit"]["exponent"], "r2": fit["fit"]["r2"]}, "fit_full_scale": full,
                  "fit_reasons": fit["reasons"], "extrapolation_unreliable": fit["extrapolation_unreliable"],
                  "row_fit": row_fit, "row_fit_excluded": row_fit_excluded,
                  "projected_seconds": float(sum(p["seconds"] for p in pts)), "reduction": None,
                  "complexity_analysis": f"碼層複雜度（清冊 unit_axis.function，讀碼 {e.get('evidence')}）：{func}",
                  "unit_seconds": unit_seconds, "units": units,
                  "lower_bound_seconds_per_unit": None,
                  "lower_bound_analysis": f"未建向量化／numba 小原型；碼層下限＝{'·'.join(e['unit_axis']['axes'])} 之單次"
                                          f"掃描（每單位常數時間），現行 {func}（階數差 {criterion2_order_gap(func)}）",
                  "evidence": _evidence(e, chosen, all_records)})
        variants: Dict[str, Any] = {}
        for (vr, va), base in VARIANT_RUNS.items():
            if cell != base:
                continue
            vrun = runs.get((vr, va))
            if vrun is None:
                if require_variants:
                    problems.append(f"{eid}：所屬格 {cell!r} 之變體實跑 {vr}:{va} 缺（SPEC v5.53 (c1)）")
                continue
            # SPEC v5.56 (o)：只 `VARIANT_SPLIT_RUNS`（跨標的長資料之預設切分）須 split_applied；家族數軸變體不涉切分
            need_split = (vr, va) in VARIANT_SPLIT_RUNS
            vpts = [p for q in sorted(vrun["receipt"]["points"], key=lambda q: int(q["scale"]))
                    if (p := _point(e, q, vrun, va, problems, require_actual=True, require_split=need_split)) is not None]
            if len(vpts) != len(vrun["receipt"]["points"]):
                continue
            vf = scale_probe.fit(fit_points(vpts, va), float(max(p[AXIS_X_KEY[va]] for p in vpts)))
            variants[f"{vr}:{va}"] = {"points": vpts, "probe": vrun["probe"], "split": "default" if need_split else None,
                                      "axis": va,
                                      "fit": {"axis": va, "exponent": vf["fit"]["exponent"], "r2": vf["fit"]["r2"],
                                              "extrapolation_unreliable": vf["extrapolation_unreliable"]}}
        m["variants"] = variants or None
        m["isolation"] = None
        if eid in ISOLATION_RUNS:
            iso = _isolation_section(e, ISOLATION_RUNS[eid], runs, problems, required=require_isolation,
                                     scale_probe=scale_probe)
            if iso is False:
                continue
            m["isolation"] = iso
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
            # SPEC v5.52 (b)：實跑對清冊之涵蓋（每一 measure=true 入口之主軸與第二軸皆有實跑）
            "schedule_coverage": schedule_coverage(inventory, list(runs)),
            "entries": entries}


# ── CLI ───────────────────────────────────────────────────────────────────────────────────────────────


def main(argv: Optional[Sequence[str]] = None) -> int:
    args_in = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(prog="icperf_scale_harness.py", description="ICPERF Task 0.2 行程內逐入口計時（見模組說明）")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("run", help="一個規模點之一次實跑（由 scale_probe 啟動）")
    p.add_argument("run_id", choices=sorted(RUNNERS))
    p.add_argument("--axis", default="cols", choices=("cols", "rows", "events", "timestamps", "survivors", "families"))
    p.add_argument("--scale", type=int, required=True)
    p.add_argument("--records-dir", type=Path, required=True)
    p.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    p.add_argument("--out-root", type=Path, default=None)
    p.add_argument("--ref-scale", type=int, default=None,
                   help=f"SPEC v5.58 (x)：{MW_FIXED_CELL} 之固定倖存集合參考點（event_import events 軸之事件數點）")
    sub.add_parser("list", help="列出路徑與直接呼叫格")
    p = sub.add_parser("plan", help="清冊 measure=true 入口之 branch_cell 對照")
    p.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    p = sub.add_parser("precheck-rows", help="v5.51 (a)：列數軸列長之樣本外切分秒級碼層預檢（不跑 IC、不讀資料檔）")
    p.add_argument("--scale", type=int, action="append", default=None, help=f"列長（可多次；預設 {ROW_AXIS_SCALES}）")
    p = sub.add_parser("coverage", help="v5.52 (b)：清冊 measure=true 入口對實跑排程（主軸＋第二軸）之涵蓋（秒級）")
    p.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    sub.add_parser("precheck-xsec-long", help="v5.53 (c1)：L 格與 ETH 4h 長歷史格之時間重疊、有效列數、預設切分可達性（秒級，"
                                               "只讀 K 線時間戳與收盤）")
    sub.add_parser("event-bar-scales", help="v5.53 (c0)：事件路徑 K 線根數軸之三點（秒級，只讀 K 線時間戳與事件批）")
    p = sub.add_parser("precheck-events", help="v5.55 (g2)／v5.56 (j)(n)：事件數軸三點之切分預檢（產品五階段編排＋切分選點；"
                                               "三點另以產品實跑驗 effective mode 與二元三入口，每點約半分鐘）")
    p.add_argument("--out-root", type=Path, default=None)
    p.add_argument("--no-verify", action="store_true", help="只做切分選點與複驗、不跑產品（ok 恆 False；只供探查規則）")
    p = sub.add_parser("survivor-scales", help="v5.55 (e)：IC 後轉換 survivors 軸三點（ic_page_relaxed 各 cols 點存下之 IC "
                                               "任務之實際倖存欄數；秒級）")
    p.add_argument("--out-root", type=Path, default=None)
    p.add_argument("--n-cols", type=int, action="append", default=None, help=f"cols 點（可多次；預設 {SCALE_POINTS}）")
    p = sub.add_parser("prepare", help="v5.52 (b)(c)：量測前之存檔輸入（post-ic-rows：L 格 IC 任務；icfirst-subsets："
                                       "write_raw 重寫之 IC-first 子集 run）；中型，由 measure 經共用監看啟動")
    p.add_argument("what", choices=("post-ic-rows", "icfirst-subsets"))
    p.add_argument("--out-root", type=Path, default=None)
    p.add_argument("--n-cols", type=int, action="append", default=None,
                   help=f"icfirst-subsets 之 cols 軸欄數（可多次；預設 {SCALE_POINTS}）")
    p.add_argument("--rows", type=int, action="append", default=None,
                   help=f"icfirst-subsets 之列軸窗長（可多次；預設 {ICFIRST_ROW_SCALES}；各取 ROW_AXIS_COLS 欄）")
    args = ap.parse_args(args_in)
    if args.cmd == "precheck-xsec-long":
        res = xsec_long_precheck()
        print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
        return 0 if res["ok"] else 1
    if args.cmd == "survivor-scales":
        root = Path(args.out_root) if args.out_root is not None else REPO / TASK02_ROOT
        root = (root if root.is_absolute() else REPO / root).resolve()
        res = post_ic_survivor_scales(root, tuple(args.n_cols or SCALE_POINTS))
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0 if res["ok"] else 1
    if args.cmd == "precheck-events":
        res = event_axis_precheck(args.out_root, verify=not args.no_verify)
        print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
        return 0 if res["ok"] else 1
    if args.cmd == "event-bar-scales":
        try:
            print(json.dumps({"scales": list(event_bar_scales()), "pre_bars": EVENT_BARS_PRE,
                              "cache": _rel(real_bars_cache())}, ensure_ascii=False))
        except HarnessError as exc:
            print(f"HarnessError：{exc}", file=sys.stderr)
            return 1
        return 0
    if args.cmd == "coverage":
        inv = load_inventory(args.inventory)
        cov = schedule_coverage(inv, schedule_runs(inv))
        # SPEC v5.59 (ai)：清冊檔:行引用與現行碼不符亦不成立（`icperf_freeze_baseline.py inventory-refs --write` 依符號重算）
        ref_problems = _fb().inventory_ref_problems(inv, REPO)
        print(json.dumps({**cov, "schedule": [f"{r}:{a}" for r, a in schedule_runs(inv)],
                          "inventory_ref_problems": ref_problems}, ensure_ascii=False, indent=1))
        return 0 if not cov["uncovered"] and not ref_problems else 1
    if args.cmd == "prepare":
        root = Path(args.out_root) if args.out_root is not None else REPO / TASK02_ROOT
        root = (root if root.is_absolute() else REPO / root).resolve()
        try:
            if args.what == "post-ic-rows":
                res: Any = prepare_post_ic_rows(root)
            else:
                res = prepare_icfirst_subsets(root, n_cols=tuple(args.n_cols or SCALE_POINTS),
                                              rows=tuple(args.rows or ICFIRST_ROW_SCALES))
        except (HarnessError, _fb().FreezeError) as exc:
            print(f"HarnessError：{exc}", file=sys.stderr)
            return 1
        print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
        return 0
    if args.cmd == "precheck-rows":
        res = row_axis_precheck(tuple(args.scale) if args.scale else ROW_AXIS_SCALES)
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0 if res["ok"] else 1
    if args.cmd == "run":
        try:
            run_one(args.run_id, axis=args.axis, scale=args.scale, records_dir=args.records_dir,
                    inventory_path=args.inventory, out_root=args.out_root, argv=args_in, ref_scale=args.ref_scale)
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

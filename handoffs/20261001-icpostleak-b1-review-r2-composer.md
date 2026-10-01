# ICPOSTLEAK B1 審碼 r2 — COMPOSER

task-id: 20261001-ICPOSTLEAK-B1-REVIEW-R2  
brief: handoffs/20261002-ICPOSTLEAK-B1-REVIEW-R2-BRIEF.md  
family: COMPOSER  
brief-kind: review  
findings-round: R2  
note: 唯讀；標的＝r1 修補 `40f863d4`、收斂 `handoffs/reconcile/20261001-icpostleak-b1-review-r1/synth.md`、branch-diff 收據。

## 必答（成對）

**(1a) composer：r1 修補（NaT gate、branch-diff 收據）是否正確、無洩漏類副作用？**  
**NaT**：`time_order.py:20-21` 改為 `index.isna()` 與相鄰 `values[1:] <= values[:-1]` 直接比較，不再 `np.diff(asi8)`；與 CODEX-R1-P2-01 建議一致，未新增第二套 gate。`test_icpostleak.py` 增 `nat_after_valid`／`nat_first`，與既有倒序／重複／亂序同一 `transform` 入口，無單獨捷徑。  
**branch-diff**：`handoffs/run_receipts/20261002-icpostleak-branch-diff.json` 已具 42 對、NaN 位置不一致 0、`residual_trigger_rel_gt_1e-3: true`；`probe_change_report.py branchdiff` 與 manifest 登記一致。修補未改遮罩／IC 順序／ratio-unsafe 行為。  
**(1b) 實跑**：`/tmp/icpostleak-b1-r2-7e8d/run_probe.py`（先 `ffstat_probes._isolate.isolate()`＋`isolate_dstar_cache()`）→ `OLD_DIFF_LEAK True`、`NEW_GATE REJECTED`；`venv/bin/python -m pytest tests/feature_engineering/test_icpostleak.py -k time_order -q` → **7 passed** rc=0（含兩 NaT 例與 `test_mutation_time_order_check_removed_is_caught`）；`venv/bin/python -m pytest tests/feature_engineering/test_icpostleak.py tests/api/test_icpostleak_api.py -q --tb=no` → **124 passed** in 40.18s rc=0。

**(2a) assumed ①② 與 brief「我沒查」1–4 是否成立？**  
① **生產分派不可 registry 帶 rank／zscore／gaussian**：**成立**於 FF 主路——`_layer6_5_pre_ic`（`:2971-2973`）、`_build_l7_raw_preprocessing_config`（`:2980-2982`）、CGSA `write_raw_from_registry_stream` 均強制關三項；`multi_tf_generator.py:1430-1434` 呼叫 `_layer6_5_preprocessing` **未**傳 `selected_features` ⇒ 僅 pre-IC。`_layer6_5_post_ic`（`:3105-3111`）雖尊重 config 開關且 CGSA 時可走 `transform_registry_groups`（`:3136-3151`），但 **momentum 內無生產呼叫** `_layer6_5_preprocessing(..., selected_features=...)`（全 repo 僅測試）；IC 頁／`run_ic_first` 後段用 `FeaturePreprocessor.transform_selected`（Polars 預設臂），非 factory post_ic+registry 組合。① 之「post-IC registry 待核」：**否證未觀測到生產鏈**，碼上為死路徑風險而非已證可達。  
② **特徵 h5 float32 落盤**：**成立（讀碼）**——`feature_storage.py:47-49` `_persist_float32` 邊界；與 branch-diff 中 rank 同值 1/504 差異敘事一致；本輪未 byte 掃描 IC 讀回 dtype。  
**我沒查 1**（post_ic+registry）：已上；結論＝架構上可寫但現網無 caller，不推翻 ①。  
**我沒查 2**（registry zscore float64 核心之記憶體／耗時）：未 benchmark；不阻擋 r2 結論。  
**我沒查 3**（polars 單步 zscore 4.7e-5 是否足）：locate 收據 polars 單步 zscore 遠小於觸發門檻；IC 生產臂為 Polars，與 §N 最大相對差（registry rank+zscore 58.8）不同臂。  
**我沒查 4**（相對差定義）：分母 |legacy| 在近零格放大（registry rank+zscore 58.8）；**絕對差** 0.0975（polars rank+zscore @ row 1053）仍 > 1e-3，觸發不依賴分母辯護；相對於窗 std（0.018）之比約 5.4，與主委 scratchpad 一致。  
**(2b)** 上列錨點＋`git grep` caller 掃描；branch-diff／locate JSON 機讀摘要。

**(3a) §N 殘留第一條（各分支 zscore 核心不一致）處置**  
**採主委立場（本批改 registry zscore 數值核心＋SPEC v5＋r3 審）**，並補充分工：**rank 同值 1/504** 屬 float32 輸入量化，收據記錄、不當洩漏缺陷改碼；**registry 單步 zscore**（最大 abs 0.038、p99 0.009，與改前逐格相同）為可修之核心不一致，應與 legacy 同用 `_rolling_zscore_2d`（float64 累積、float32 回存）。**不採**「維持殘留僅改 needs-research 文案」為終態——觸發已成立（`residual_trigger_rel_gt_1e-3`），延後須有明確 follow-up 票而非空泛「之後再說」。  
**(3b)** 依據：資料品質＝窗內因果與 NaN 位置已 0 不一致，殘留為**跨臂數值契約**；生產可達性＝IC／run_ic_first 不走 registry zscore，但探針矩陣與未來 CGSA 擴張需臂間可辯護一致；成本＝單步 zscore 核心替換範圍小於重開 rank。主委立場可商榷點：**polars rank+zscore 絕對差 0.097** 在 IC 預設臂仍可能與 legacy 偏離，僅修 registry 不解全部臂；應在 SPEC v5 Task 1.1 基準分臂列 acceptable delta（float32 回存＋同值 rank），而非假裝一次修復清零所有 42 對。

**(4a) 可否收第 1 批（依上節）？**  
**可收洩漏修補批**（`95487b67`＋`47ba1d3e`＋`40f863d4`）：r1 兩項 P2 已修補且本家實跑閉合；無新 P0／P1。§N 第一條觸發**不**等同未修洩漏，但**須**在收批同時開 SPEC v5／registry zscore 跟進（非本輪阻擋項）。  
**(4b) 擋批 P0／P1：** none。

---

## COMPOSER-R2-P3-00

**斷言**: 本輪逐項核對 r1 修補與 §N 觸發收據後，未發現意外漂移或未闭合之 P0／P1；NaT 修法正確、branch-diff 交付完整，§N 處置共識為跟進 SPEC v5 修 registry zscore 核心而非否認觸發。

**碼證**: `venv/bin/python /tmp/icpostleak-b1-r2-7e8d/run_probe.py` → OLD_DIFF_LEAK True／NEW_GATE REJECTED；`venv/bin/python -m pytest tests/feature_engineering/test_icpostleak.py tests/api/test_icpostleak_api.py -q --tb=no` → 124 passed rc=0；`handoffs/run_receipts/20261002-icpostleak-branch-diff.json` summary `residual_trigger_rel_gt_1e-3: true`、max_abs 0.0975；`momentum/FeatureEngineering/feature_factory.py:2971-2982` 強制關 rank／zscore／gaussian；`git grep '_layer6_5_preprocessing(' -- '*.py'` 生產路徑無 `selected_features`。

**類別**: other

**來源摘要**: handoffs/20261002-ICPOSTLEAK-B1-REVIEW-R2-BRIEF.md#brief;handoffs/reconcile/20261001-icpostleak-b1-review-r1/synth.md#synth;momentum/FeatureEngineering/preprocessing/time_order.py#fix40f863d;handoffs/run_receipts/20261002-icpostleak-branch-diff.json#521rows;commit/40f863d4#patch

正文：威脅模型聚焦意外漂移／未來洩漏；§N 數值臂差異已登記觸發，本輪不以「零 finding」否定跟進修復。未重跑 branchdiff 全探針（主委已產收據）；未跑 registry zscore float64 改版 benchmark。

---

ASSUMPTIONS_VERIFIED: 40f863d4 含 time_order／nat 測試／branch-diff JSON；isolate 探針 NaT 行為；124 passed；生產 caller 掃描 post_ic 無 selected_features。  
TESTS_RUN: run_probe.py；pytest time_order 7 passed；pytest icpostleak 兩檔 124 passed（見上）。  
FAILURES_SEEN: none。  
SCOPE_CHANGES: none（唯讀審查）。  
NUMERIC_OR_SCHEMA_IMPACT: none（未改產品）。  
產出: handoffs/20261001-icpostleak-b1-review-r2-composer.md

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:

STATUS: DONE

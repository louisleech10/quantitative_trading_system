# ICPOSTLEAK B1 審碼 r1 — COMPOSER

task-id: 20261001-ICPOSTLEAK-B1-REVIEW-R1  
brief: handoffs/20261002-ICPOSTLEAK-B1-REVIEW-R1-BRIEF.md  
family: COMPOSER  
brief-kind: review  
findings-round: R1  
note: 唯讀；標的＝Phase 1 `95487b67`、Phase 2 `47ba1d3e`；不重議 SPEC v4 設計面。

## 必答（成對）

**(1a) 實作是否完整符合 SPEC v4 與 manifest（逐 Task）？**  
**Phase 1**：Task 1.1 `mask_incomplete_window_by_input_2d`（`stable_mask.py:215`）與 legacy／optimized／Polars／registry 四路遮罩呼叫（`feature_preprocessor.py` 多處 `_stable_mask.mask_incomplete_window_by_input_2d`）；registry 融合 `_registry_fast_transform` 正式順序 rank→gaussian→zscore（`:2176` 註解與實作）；分支盤點收據 `handoffs/run_receipts/20261002-icpostleak-branch-inventory.txt` 存在。Task 1.2 `time_order.assert_strictly_increasing_time_index`（`time_order.py:14`）於 `transform`（`:602`）與 `transform_selected` 每群組（`:674-676`）。Task 1.3 契約 `tests/_golden/icpostleak/contract.json` 列 18 檔與 frozen 計數；本輪未重跑全 18 檔（主委事實 2：171 passed、2 failed 為 FF-STAT 前既有紅），但 gate 三檔＋改寫三檔節點與 `test_icpostleak` 已覆蓋 §P 驗證項。  
**Phase 2**：Task 2.1 `_apply_transforms_sync` 經 `create_post_ic_transform_config`＋`transform_selected`（`ic_analysis_service.py:2916-2924`）；手寫 `rank(pct=True, axis=0)` 已不存在（`grep` 0）；`transforms_applied` 順序 rank→gaussian→zscore（`:2925-2927`）；保序去重 `_dedupe_preserve_order`（`:2887`）；文案 grep 舊序三檔皆 0。Task 2.2 ratio-unsafe 經 `ratio_unsafe_category` 排除並填 `excluded_features`（`:2894-2910`、`:2985`）；`ApplyTransformsResponse` 選填欄（`test_phase2_response_model_accepts_excluded_features`）；前端 `ApplyTransformsResult.tsx` 以 `?? []` 相容缺欄。manifest `stub_modules`／`test_files`／`gate_cmd` 與實際路徑一致。  
**(1b) 碼證**：`CODE-ANCHOR: momentum/FeatureEngineering/preprocessing/stable_mask.py:215`；`CODE-ANCHOR: api/services/ic_analysis_service.py:2916`；`CODE-ANCHOR: momentum/factories.py:254`（post-IC 三項 `apply_to: "all"`）；`grep -c "rank(pct=True" api/services/ic_analysis_service.py` → 0；`grep -r "from api\." momentum/` → 0。

**(2a) IC 頁與正式後處理是否仍有未來洩漏或窗未滿之輸出？**  
IC 路徑與同映射之 `transform_selected` 共用生產核心＋輸入錨點遮罩；手寫全樣本排名已刪。窗未滿列在 rank／gaussian／zscore 各步以 §C 錨點遮為 NaN；§G 逐步驟 oracle 測試（`test_icpostleak.py` phase1／phase2 節）鎖逐位元組與首個有限值列。  
**(2b) 實跑**：`venv/bin/python -m pytest tests/feature_engineering/test_icpostleak.py tests/api/test_icpostleak_api.py tests/api/test_ic_la1_degraded_gate.py -q --tb=no` → **150 passed** in ~97s rc=0（含 `test_phase2_perturb_last_row_prefix_unchanged` 七組合、`test_phase1_causal_perturb_last_row` 四分支、`test_mutation_full_sample_rank_restored_is_caught`）；`test_boundary_13_reversed_time_index_rejected` 倒序 ⇒ ValueError。

**(3a) brief 之 assumed ①②③ 與「我沒查」1–5 是否成立？**  
① **成立**：`handoffs/run_receipts/20261002-icpostleak-change-report.json` 之 14 例 `suffix_changed_cases` 皆 `registry*` 且含 zscore／gaussian 組合；35 例 legacy／optimized／polars 在 `suffix_identical_cases` 且 `suffix_diff_cells=0`（收據摘要與主委事實 4 一致）⇒ 差異可歸改序、累積式 zscore、切片並行補 gaussian，非遮罩後區段新漂移。② **成立（讀碼）**：registry `_registry_fast_transform` 逐步 `astype(np.float32)` 回存；IC／post-IC 測試與 oracle 以 float32 往返建模（Polars 分支註解 `:270-271`），無下游斷言依賴 float64 中間值。③ **成立（讀碼）**：`transform` 入口仍丟 ratio-unsafe（`:600-612` 區段邏輯未改判定）；IC 頁同函式家族 `ratio_unsafe_category` 明示排除，與 L6.5「不轉換」一致。  
**「我沒查」**：1）生產預設 `GaussianNormalizeConfig.apply_to="all"`（`feature_config.py:272`）；IC `create_post_ic_transform_config` 固定 `apply_to: "all"`；registry 快速路徑 `apply_to != "all"` 改 **fail-closed** `ValueError`（`feature_preprocessor.py:2205-2207`）——不再靜默略過，行為變嚴非洩漏。2）`transform_selected` 逐 **group** 檢 DatetimeIndex；`RangeIndex` 跳過（`time_order.py:18`）；合併後單群組仍單調則通過，與 SPEC「L7 raw 讀回 RangeIndex」相容。3）全 ratio-unsafe：`ValueError`；route `400`（`ic_analysis.py:764-766`，訊息不含 not found）。4）前端 `excluded_features ?? []`（`ApplyTransformsResult.tsx:21`）。5）append 多窗：`test_phase1_append_mode_each_window_masked` 對每窗獨立 oracle 遮罩。  
**(3b)** 讀碼上列錨點；change-report JSON 機讀分類；未另開 FF 全分支重測（避免與主委並行搶資源）。

**(4a) 改寫之既有測試是否變弱？**  
改寫限於窗未滿遮罩所致首個有限值列／遮罩後區段比對；`test_icpostleak` 含 identity／錨點／窗−2 mutant 翻轉；五項改寫測試於 `mask_incomplete_window_by_input_2d` identity mutant 全紅（主委事實 3）。未見 atol 放寬或 skip。  
**(4b)** `git show 95487b67` 觸及 `test_ff_causal_golden.py`、`test_l65_v2_transforms.py`、`test_l65_native_tf_real_eth.py` 等為期望更新；change-report 35/49 例遮罩後 0 格差證非隨意改期望。

**(5a) 可否收第 1 批？**  
**可**（無 P0／P1 阻擋項；FF-STAT 前兩項紅測試不屬本票 gate）。  
**(5b)** 擋批 P0／P1：**none**。

---

## COMPOSER-R1-P3-00

**斷言**: 本輪對 SPEC v4／manifest／`95487b67`＋`47ba1d3e` 全面審碼（後端、前端、測試、收據）後，未發現意外漂移或未修之未來洩漏／窗未滿公開輸出之 P0／P1；brief 攻擊面與 assumed ①②③ 經讀碼與 gate 實跑可支持收批。

**碼證**: `venv/bin/python -m pytest tests/feature_engineering/test_icpostleak.py tests/api/test_icpostleak_api.py tests/api/test_ic_la1_degraded_gate.py -q --tb=no` → 150 passed rc=0；`handoffs/run_receipts/20261002-icpostleak-change-report.json` summary 35 例 suffix 全同／14 例 registry 預期差異；`grep -c "rank → zscore → gaussian" api/models/ic_models.py api/services/ic_analysis_service.py api/routes/ic_analysis.py` 各 0；mutant 節點列於 `tests/api/test_icpostleak_api.py`／`test_icpostleak.py`（全樣本排名、gaussian 最後、excluded 不填等）與 §V 對齊。

**類別**: other

**來源摘要**: docs/ICPOSTLEAK_SPEC.md#ca7efa80b0f9;handoffs/20261002-ICPOSTLEAK-B1-REVIEW-R1-BRIEF.md#cd65652dc7fb;tests/feature_engineering/test_icpostleak.py#63eb345468c0;tests/api/test_icpostleak_api.py#ae628e582d76;handoffs/run_receipts/20261002-icpostleak-change-report.json#597ce3a60deb

正文：已排除面（SPEC／TODO r1–r8 設計）未重審。主委事實 1（180 passed 擴展節點）本輪以 manifest `gate_cmd` 子集 150 passed 複驗核心契約；事實 2 之 2 failed 對照 brief 為 CGSA／tier 既有紅，不擋 ICPOSTLEAK 收批。registry `apply_to != all` 改 fail-closed 屬實作 brief 已記之既有缺陷修補，非新洩漏。

---

ASSUMPTIONS_VERIFIED: Phase 1/2 commits 存在且與 brief EXPECTED-DELTA 一致；kline 探針收據路徑存在；主委事實 1 gate 子集 150 passed；change-report 35+14 分類與 JSON 一致；R1 decoupling grep=0。  
TESTS_RUN: `venv/bin/python -m pytest tests/feature_engineering/test_icpostleak.py tests/api/test_icpostleak_api.py tests/api/test_ic_la1_degraded_gate.py -q --tb=no` → 150 passed in 96.77s rc=0；`grep`／`git show --stat` 靜讀驗證（見必答 1b）。  
FAILURES_SEEN: none（未重跑 18 檔全量與 2 項既有紅）。  
SCOPE_CHANGES: none（唯讀）  
NUMERIC_OR_SCHEMA_IMPACT: none（審碼未改碼；實作已新增選填 `excluded_features` 為預期）  
產出: `handoffs/20261001-icpostleak-b1-review-r1-composer.md`

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:

STATUS: DONE

# ICPOSTLEAK B1 審碼 r1 — GROK

task-id: 20261001-ICPOSTLEAK-B1-REVIEW-R1
brief: handoffs/20261002-ICPOSTLEAK-B1-REVIEW-R1-BRIEF.md
family: GROK
brief-kind: review
findings-round: R1

本輪唯讀；標的＝Phase 1 `95487b67`、Phase 2 `47ba1d3e`。全面審後端、前端、測試、收據。實跑在 `/tmp/qts-icpl-b1r1`（先呼叫 `isolate()`／`isolate_dstar_cache()`）。

## 必答（成對）

**(1a) 實作是否完整符合 SPEC v4 與 manifest（逐 Task）？**

Task 1.1：`mask_incomplete_window_by_input_2d` 落地；legacy `_apply_rank_transform`／`_apply_gaussian_normalize`／`_apply_adaptive_zscore`、optimized 三呼叫點、Polars `_polars_mask_columns`、registry 四處統一 `_registry_fast_transform`（正式順序 rank→gaussian→zscore、每步遮罩）。chunked 走 `_transform_single` 由 legacy 涵蓋。native-tf 子實例呼叫 `_transform_single`，同樣套遮罩後再 `idx_map` 展開。分支盤點收據 `handoffs/run_receipts/20261002-icpostleak-branch-inventory.txt` 在場。manifest `coverage_risk` 另列之跨分支量級檔 `*-icpostleak-branch-diff.json` 本批未見；§G 通過條件是各分支對自身逐步驟 oracle 逐位元組相同，該缺口不構成未遮罩或洩漏。

Task 1.2：`assert_strictly_increasing_time_index` 於 `transform` 與 `transform_selected` 每群組入口。DatetimeIndex 非嚴格遞增拋 `ValueError`（含首個違規位置）；RangeIndex／長度 0／1 不檢。registry 群組存 numpy 列序、包成 DataFrame 時為 RangeIndex，與 SPEC 邊界「L7 raw 讀回 RangeIndex 不檢」同構。

Task 1.3：契約 18 檔清單與凍結計數仍在；本批改寫三檔（`test_l65_v2_transforms.py` 之 `_expected_zscore`、`test_ff_causal_golden.py` 列數與 gaussian 獨立遮罩、`test_l65_native_tf_real_eth.py` 前綴下界）。主委事實 2：18 檔 171 passed、2 failed＝FF-STAT 前即紅。

Task 2.1：手寫三項已刪；經 `create_post_ic_transform_config`＋`create_feature_preprocessor`＋`transform_selected`；`_normalize_zscore_windows`／`_dedupe_preserve_order` 模組層；`transforms_applied` 依正式順序；舊序與全樣本排名字面三落點 grep 0；窗單位「根」。

Task 2.2：`ratio_unsafe_category` 委由 `_is_ratio_unsafe_column`；`excluded_features` 選填；前端結果區元件＋hook／page 型別；vitest 三支含缺欄。

**(1b) 碼證**

`CODE-ANCHOR: momentum/FeatureEngineering/preprocessing/stable_mask.py:215`
`CODE-ANCHOR: momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:2171`
`CODE-ANCHOR: api/services/ic_analysis_service.py:2916`
`CODE-ANCHOR: momentum/factories.py:236`
`grep -c "rank(pct=True, axis=0)" api/services/ic_analysis_service.py` → 0
`grep -c "rank → zscore → gaussian\|rank/zscore 之後"` 於 `api/models/ic_models.py`／`ic_analysis_service.py`／`ic_analysis.py` 各 0
`grep -r "from api\." momentum/` → 0

**(2a) IC 頁與正式後處理是否仍有任何未來洩漏或窗未滿之輸出？**

IC 頁 gaussian 改經因果排名窗＋輸入錨點遮罩；最後一列 ×50 時前 2999 列不變。gaussian 首個有限值列＝251（窗 252−1）。append 窗 100／252 各自首個有限值＝99／251。正式 `transform_selected` 與服務路徑逐位元組相同。

**(2b) 實跑或可重現之輸入序列**

隔離探針（真實 BTCUSDT 1h 前 3000 根 close／volume）：`LEAK_GAUSSIAN_PREFIX_EQ True prefix_diff_cells 0`；`GAUSSIAN_FIRST_FINITE [251, 251]`；`GAUSSIAN_PREFIX_NAN True`；`SVC_GAUSSIAN_EQ_FORMAL True`。
複本 pytest：`test_phase1_causal_perturb_last_row[registry]`、`test_mutation_mask_identity_is_caught[registry_sink_sharded]`、`test_phase2_perturb_last_row_prefix_unchanged[gaussian]`、`test_phase2_output_equals_formal_transform_selected[rank+zscore+gaussian]` → 4 passed rc=0（rootdir `/private/tmp/qts-icpl-b1r1`）。
同碼另跑具名函式全集 83 passed in 28.65s rc=0（含七組合 perturb、逐步驟 oracle、append 兩窗、identity mutant 各分支）。

**(3a) assumed ①②③ 與「我沒查」1–5 是否成立？**

①成立：change-report 49 例中 35 例 `suffix_diff_cells=0`；14 例 `suffix_changed_cases` 全為 registry 系列，分類 0 例 UNEXPLAINED（`fill_gaussian`／`reorder`／`cum_zscore` 三原因覆蓋）。
②成立：registry 逐步 `.astype(np.float32)` 回存；舊融合核心出口已是 float32；本輪未見下游斷言依賴 float64 中間值。
③成立：L6.5 `transform` 入口丟棄 ratio-unsafe（探針 `L65_DROPS_UNSAFE True`）；IC 頁同判定明示排除、不送轉換。正式 FF 對該類欄不做 rank／zscore。

「我沒查」：
1. 成立為生產不可達 sharded 快速路徑。`GaussianNormalizeConfig` 預設 `enabled=False, apply_to="all"`；IC `create_post_ic_transform_config` 固定 `apply_to="all"`。`apply_to=['close']` 時 `use_fast=False`、`REQUIRES_SLOW_PARTIAL True`、`CAN_SHARD_PARTIAL False`；直接呼叫 `_registry_fast_transform` 才 `ValueError`（fail-closed 安全網）。批次不會因生產設定從「可跑」變成報錯。
2. 成立於契約輸入。`transform_selected` 對嚴格遞增 DatetimeIndex／RangeIndex 通過；把兩段重疊時間戳 `concat` 的假合併會在位置 100 拋錯（fail-closed，訊息含違規前後戳）。合法單調主週期列通過。native-tf 子路徑用 RangeIndex 算完再展開，不誤擋。
3. 全排除 `ValueError` 訊息無 `not found` ⇒ route 映射 HTTP 400；前端 `handleApplyTransforms` catch 後 `setError`。
4. `excluded_features ?? []`；vitest「缺欄不渲染」。
5. append 各窗獨立遮罩：探針 `APPEND_W100_FIRST [99, 99]`、`APPEND_W252_FIRST [251, 251]`；`test_phase1_append_mode_each_window_masked` 與 first-window-only mutant 在場。

**(3b) 碼證或輕量實跑**

探針 log 終行 `ALL_PROBES_COMPLETE`；`feature_preprocessor.py:2205-2207`、`:894-950`（`can_shard_stream` 要求 `not requires_slow`）、`ic_analysis.py:764-766`、`ApplyTransformsResult.tsx:21`、`_apply_adaptive_zscore` append 迴圈 `:4031-4039`。

**(4a) 改寫之既有測試是否變弱？**

期望更新限於遮罩後首個有限值列與窗未滿區。`_expected_zscore` 加測試端獨立遮罩；causal golden 列數 640→1000 並對 gaussian 逐步遮；native-tf 前綴改為各路徑遮罩下界（legacy 597、native 564），實測 609／588 落入 +80 帶。原「native_prefix > legacy_prefix」在遮罩主導後關係倒置（609 對 588），改以下界＋穩態 NaN 全等＋clip 點 >5% 差異。atol／rtol 未放寬；未新增 skip／xfail。identity mutant 使 phase1 各分支 oracle 翻轉（本輪 `test_mutation_mask_identity_is_caught[registry_sink_sharded]` 綠＝正常版可證偽漏遮）。

**(4b) diff 逐處對照**

`git show 95487b67`：`test_ff_causal_golden.py` 加獨立 `cut = first+window-1`；`test_l65_v2_transforms.py` `_expected_zscore` 與常數窗前綴改 NaN；`test_l65_native_tf_real_eth.py` 下界公式。契約 `oracle_update_counts` 斷言行數規則仍由 `test_boundary_08`／`09` 守門。

**(5a) 可否收第 1 批？**

可。未來洩漏與窗未滿公開輸出在 IC 頁與正式後處理契約路徑上已修；assumed 與未查項本輪可支持。FF-STAT 前兩項紅測試不擋本批。

**(5b) 擋之 P0／P1：** none。

---

## GROK-R1-P3-00

**斷言**: 本輪逐項核對後無 finding；SPEC v4／manifest 五 Task 在 `95487b67`＋`47ba1d3e` 落地，IC 頁與正式後處理之未來洩漏與窗未滿公開輸出已由輸入錨點遮罩與正式 `transform_selected` 關閉，brief assumed ①②③與「我沒查」1–5 經隔離探針與具名測試成立。

**碼證**: 隔離探針 `env PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/tmp/qts-icpl-b1r1/numba PYTHONPATH=/tmp/qts-icpl-b1r1 venv/bin/python /tmp/qts-icpl-b1r1/probe.py` rc=0，先 `isolate()`＋`isolate_dstar_cache()`。真實 kline 3000×2。`LEAK_GAUSSIAN_PREFIX_EQ True prefix_diff_cells 0`；`GAUSSIAN_FIRST_FINITE [251, 251]`；`SVC_GAUSSIAN_EQ_FORMAL True`；`ALL_UNSAFE_HTTP 400`；`L65_DROPS_UNSAFE True`；append 窗 100／252 首有限值 99／251；`CAN_SHARD_PARTIAL False` 且直接呼叫快速路徑 `FAST_PARTIAL_RAISED True`；假合併重複時間戳 `TS_MERGED_DUP_RAISED True` 於位置 100；change-report 14 例分類 `UNEXPLAINED []`、identical 列 `IDENT_NONZERO_ROWS 0`。複本 pytest 4 passed in 6.96s rc=0（rootdir `/private/tmp/qts-icpl-b1r1`）。具名函式集 83 passed in 28.65s rc=0。`grep` 全樣本排名與舊序三檔皆 0；`from api.` 於 momentum 0。

**類別**: other

**來源摘要**: docs/ICPOSTLEAK_SPEC.md#ca7efa80b0f9;docs/manifests/ICPOSTLEAK.json#eef794fc1fa6;handoffs/20261002-ICPOSTLEAK-B1-REVIEW-R1-BRIEF.md#cd65652dc7fb;tests/feature_engineering/test_icpostleak.py#63eb345468c0;tests/api/test_icpostleak_api.py#ae628e582d76;tests/_golden/icpostleak/contract.json#43860a11061d;momentum/FeatureEngineering/preprocessing/stable_mask.py#613f6f5be2ea;momentum/FeatureEngineering/preprocessing/feature_preprocessor.py#f8086a000344;api/services/ic_analysis_service.py#7805bf12650e;api/routes/ic_analysis.py#dda0361cda66;momentum/factories.py#7c35e4b103dd;frontend/src/components/ic-analysis/ApplyTransformsResult.tsx#41c3a562aca7;handoffs/run_receipts/20261002-icpostleak-change-report.json#597ce3a60deb;handoffs/run_receipts/20261002-icpostleak-branch-inventory.txt#ed57763b37bd

量測邊界（不另立 finding）：manifest `coverage_risk` 所列 `20261002-icpostleak-branch-diff.json` 本批未產；跨分支核心差異仍登記於 SPEC §N needs-research。本輪以 change-report 之 35 例 0 格差與逐步驟 oracle 為通過條件。

---

ASSUMPTIONS_VERIFIED: 輸入錨點遮罩關閉 gaussian 未來洩漏與窗未滿公開值；IC 頁輸出＝`transform_selected`；registry 14 例差異可三原因重現；float32 回存與舊融合出口相容；ratio-unsafe L6.5 丟棄／IC 頁明示排除；sharded 於 gaussian apply_to 非 all 不走快速路徑；時間序對合法單調通過、對重複合併 fail-closed；append 各窗獨立遮罩；前端缺欄 `?? []`。
TESTS_RUN: `/tmp/qts-icpl-b1r1/probe.py` rc=0 `ALL_PROBES_COMPLETE`；複本 pytest 4 passed in 6.96s rc=0；具名函式集 83 passed in 28.65s rc=0。
FAILURES_SEEN: none。
SCOPE_CHANGES: none（唯讀；探針僅 `/tmp/qts-icpl-b1r1`）。
NUMERIC_OR_SCHEMA_IMPACT: none（審碼未改碼；實作已新增選填 `excluded_features` 為預期）。
產出: `handoffs/20261001-icpostleak-b1-review-r1-grok.md`
HANDOFF_NOT_UPDATED: 本輪 brief 唯讀，依 AGENTS 7 不另寫狀態交接；根 HANDOFF 未改。
WORKTREE_CHECK: `git status --short -- momentum api frontend scripts tests docs templates config` 相對開跑快照少 `M docs/ROADMAP.md` 與 `M scripts/fact_keys.json` 兩列（本家未改該二檔；其餘 dirty 列與開跑時一致，含既有 numba cache／golden l65）。

VERDICT: proceed
BLOCKED-BY:
CLOSED:

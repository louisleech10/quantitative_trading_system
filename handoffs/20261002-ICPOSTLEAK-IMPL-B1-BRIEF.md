# ICPOSTLEAK 實作第 1 批（Phase 1＋Phase 2；主委自任）

brief-kind: impl
task-id: 20261001-icpostleak-impl-b1-claude

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`（本 brief 供實作閘與審碼引用；實作由主委自任）。

## 依據
- SPEC：`docs/ICPOSTLEAK_SPEC.md` v4（凍結）；manifest：`docs/manifests/ICPOSTLEAK.json`（`TODOFMT PASS`）。
- 戳記：`handoffs/reconcile/20261001-icpostleak-x-review-r8/synth.md`（三家 APPROVED，sha256:d5439408…，`reconcile_stamps_check` PASS）。
- 使用者 2026-10-01：「FF-STAT完成後，IC 頁洩漏要先修」；離線授權委員共識。

## 主委事實
fact-verified: 實作於隔離 worktree 完成後搬回主樹；主樹實跑 `tests/feature_engineering/test_icpostleak.py`、`tests/api/test_icpostleak_api.py`、`tests/api/test_ic_la1_degraded_gate.py` 與改寫之三檔＋`test_l65_parallel` 快速路徑節點 180 passed；Task 1.3 受影響 18 檔（stable_start 只跑 run_ic_first 四支）於 worktree 171 passed、2 failed（皆 FF-STAT 前 5a148b8e 即紅：l7_raw_streaming 之 `_current_output_window`、l65_parallel 之 tier_auto）；改寫之五項既有測試於「輸入錨點遮罩 identity」mutant 下全紅；前端 `npm run build` rc=0、vitest 3 passed。
assumed: 改前對照收據 `handoffs/run_receipts/20261002-icpostleak-change-report.json` 之 14 例差異全屬 registry 系列之改序／累積式核心／切片並行補 gaussian，非新漂移。
→ 否證觀測：legacy／optimized／Polars 任一例遮罩後區段改變。／我跑了：35 例 0 格差異（含三分支全部）。

## 實作內容
- Phase 1：`stable_mask.mask_incomplete_window_by_input_2d`；`time_order.assert_strictly_increasing_time_index`；`feature_preprocessor` legacy／optimized／Polars 三臂呼叫點遮罩、registry 四處融合核心統一為 `_registry_fast_transform`（正式順序＋各步遮罩）、`transform`／`transform_selected` 入口時間序檢查；分支盤點收據 `handoffs/run_receipts/20261002-icpostleak-branch-inventory.txt`（含實作期發現之三項既有缺陷：切片並行漏 gaussian、sharded 於 gaussian 部分欄靜默略過〔改 fail-closed〕、空 zscore 窗清單）。
- Phase 2：`momentum/factories.py` 新增 `create_post_ic_transform_config`、`ratio_unsafe_category`；`ic_analysis_service` 刪手寫三項、保序去重、ratio-unsafe 明示排除、改經正式 `transform_selected`；`ic_models` 文案與 `excluded_features`；route docstring；前端結果區元件與型別。

## 預期改動

EXPECTED-DELTA:
- momentum/FeatureEngineering/preprocessing/stable_mask.py：新增 `mask_incomplete_window_by_input_2d`（逐欄輸入首個有限值＋窗−1 前之輸出列設 NaN；形狀不符 ValueError）。
- momentum/FeatureEngineering/preprocessing/time_order.py：`assert_strictly_increasing_time_index`（DatetimeIndex 非嚴格遞增 ValueError，列首違規位置）。
- momentum/FeatureEngineering/preprocessing/feature_preprocessor.py：三臂 rank／gaussian／zscore 遮罩；`_polars_mask_columns`；`_registry_fast_transform` 取代 registry 四處融合呼叫；`transform`／`transform_selected` 入口時間序檢查。
- momentum/factories.py：`create_post_ic_transform_config`、`ratio_unsafe_category`。
- api/services/ic_analysis_service.py、api/models/ic_models.py、api/routes/ic_analysis.py：IC 頁改經正式 `transform_selected`；`excluded_features`。
- frontend/src/components/ic-analysis/ApplyTransformsResult.tsx、frontend/src/app/ic-analysis/page.tsx、frontend/src/hooks/useICAnalysis.ts：結果區元件與型別。
- 測試：tests/feature_engineering/test_icpostleak.py、tests/api/test_icpostleak_api.py、tests/_golden/icpostleak/contract.json、既有三檔改寫（l65_v2_transforms、ff_causal_golden、native_tf_real_eth；只更新因遮罩而過期之期望，mutant 驗證改寫後仍會紅）。

## 已知既有問題（非本批引入）
- 全新 checkout 之 `npm run build` 失敗：git 追蹤 `Select.tsx`／`Card.tsx` 而 import 為小寫（本機 core.ignorecase=true 遮蔽）；主樹 build rc=0。
- `tests/golden/l65/tier2_reduced/*` 工作樹自 2026-09-26 即髒（非本批），本批不提交；ff_causal_golden 於 HEAD 版（worktree）與工作樹版皆綠。

## 產出
兩個 commit（Phase 1、Phase 2）；審碼 r1 由三家全面審。完成訊號逐字 `STATUS: DONE`。

# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手任務：**GAP-3 開 B4 施工（B1、B2、B3 已 CLOSED 2026-08-21：各批三家 RECONCILE-STAMP rc=0；B3 review 兩輪 9→0、stamp 蓋 `handoffs/reconcile/20260821-gap3-b3-review-r2/synth.md`）**

- **依據**：`docs/GAP3_EVENT_TODO.md`（FROZEN）Phase B4（Task B4.1／B4.2 五欄＋W8）＋延伸檔 `docs/GAP3_EVENT_TODO.D-001.md`；SPEC FROZEN。開工前照 CLAUDE.md 稽核 HANDOFF vs repo（`git log -3`、`pytest tests/momentum/event_samples/ -q` 應 ~196 passed、`tests/momentum/feature_engineering/ -k state_counters` 17、`tests/momentum/Analysis/test_survivor_contract.py` 54、`bash scripts/debt_ledger.sh --has-open` rc=0）。
- **B4 批內順序**：B4.1 `event_samples/pattern_bridge.py::extract_event_patterns(features_at_decision, labels, event_split_plan, survivor_v2, bridge_config)`（只在事件 train 段 fit、test 段 score；split 缺 ⇒ 拒不 fallback；**禁改 `xgboost_batch_service`／`pattern_extractor.py` 簽名**；`sample_weight` 不接訓練 §N-4；AR-3 共同欄 macro/micro/degraded/LOSO；test one-class ⇒ unavailable；置亂 oracle 沿 B1.4）→ B4.2 `event_samples/candidate_ledger.py`（`record_candidate`／`to_return_series(rule_or_scores, bars, entry_semantic, label_definition, receipts)`——entry＝D1-6 映射、exit＝`label_end` close，從對齊收據取禁自推（W8）／`run_dsr_pbo`——消費 `strategy_validation/{pbo,min_btl}.py` 不改簽名、`n_trials` 從 ledger 讀；**AUC/PR-AUC/rank-biserial 餵 DSR/PBO 機械拒**；ledger 空 ⇒ unavailable、長度不足 MinBTL ⇒ loud）。B4 Gate：`pytest tests/momentum/event_samples/ -q -k "pattern_bridge or candidate_ledger"` rc=0＋`ASSERT WHEN input_metric=auc target=dsr THEN rc!=0`＋五種 entry 語意各一手算 exact。白名單：本批只新增兩檔＋測試，不動既有檔。
- **既有介面（B1–B3 產出，直接消費）**：`validate_event_import`／`align_events`→`AlignmentReceipts`／`build_event_manifest(..., events=)`／`split_events`→`EventSplitPlan`／`materialize_features_at_decision(..., events=)`／`permutation_oracle`／`build_survivor_output` v2 七鍵／`evaluate_all_bars(rule|scores, bars, manifest_config{entry_price_semantic,timeframe 必填}, event_split_plan=, manifest=)`／**B3**：`condition_engine.parse_condition(expr, registry, role)`→`ConditionSpec`、`evaluate_condition`、`assert_no_outcome_columns`（D3-4 匯出特徵表前必呼）；`generator.generate_events(spec, bars_by_tf, [LabelRule], GeneratorConfig)`→(events, provenance{manifests{label_id}, all_bars_evaluation, …})；`event_filter.apply_filter(..., condition_spec=)` 只收 feature 角色；`operators/state_counters` 五算子（registry 已註冊）。
- **殘留**：`api/models/requests.py:50` `allowed_filtering_params` 硬編碼改讀 `condition_engine.allowed_filtering_params()`——B5（api/ 白名單）；登記於 r2 synth。
- **每批收尾固定動作**：更新 `白話說明/GAP-3施工進度.md`＋接下來/README；commit 後背景 push；review session 命名 `<YYYYMMDD>-gap3-b4-review-r<N>`、stamp `…-b4-stamp-r1`；寫回前把 finding「修法」拆清單逐條對碼＋自跑其 RECHECK（摩擦八十三）。

## ⚠ 坑（完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～八十三）
- 🔴 含家族名的 Bash 會被擋 ⇒ 命令寫 scratchpad 腳本再 `bash <script>`；`committee_run.sh --session <s> <brief> <out前綴> codex,composer,grok -- --task-id <大寫>`；R2/stamp 輪 `reconcile_build.sh <s> --mode review <三檔逐列>`（glob 會吃到 brief）；R1 discovery 鎖要 `--mode review --rebuild`（不帶檔）才能 `debt_clear --lock <sources.lock>`。
- 🔴 handoffs 委員交件／brief 被 .gitignore；審計鏈入檔＝`git add -f handoffs/reconcile/<session>/`。commit 訊息末段必帶 `Governance-Scope: out-of-epic GAP-3 量化主線 B4 …`（G-7 前移檢查）。
- 🔴 FF V7 `features_df` 恆 0 欄——特徵走 `create_feature_reader().load_columns_v2/load_row_index_v2`；儲存 float16 為主。kline cache timestamp＝epoch 秒、bar open_time、連續網格；對齊層要求決策前須有已收盤 bar（`warmup_insufficient_<tf>`）比 B2.5 eligibility 多一道。
- 🔴 戳記時序：stamp-target 先建空 `## 戳記` 區再派；戳記後 `gate.sh register-output <TASK> <synth>`；債銷帳 `debt_clear.sh --round-id --session --lock`。
- 白話看板狀態欄用文字（排隊中／完工蓋章／施工中），禁 ⬜／✅／「收案」／「進行中」字樣貼 B<n>（factkey 守衛）；`Archived/GAP-2施工進度.md:13-22` 紅＝既有；push 丟背景；venv Python 3.9.6；`-p no:logging` 會拿掉 caplog（用 monkeypatch logger 代替）。

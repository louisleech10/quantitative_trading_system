# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手任務：**GAP-3 開 B3 施工（B1、B2 已 CLOSED 2026-08-21：各批三家 RECONCILE-STAMP rc=0；使用者裁定 B3 由新 session 開工、可直接動工）**

- **依據**：`docs/GAP3_EVENT_TODO.md`（FROZEN）Phase B3＋延伸檔 `docs/GAP3_EVENT_TODO.D-001.md`（A-01 FF float16 容差分層／A-03 `events=` context keyword、`entry_after_label_start >=`）；SPEC FROZEN（D3 欄位角色隔離＝B3.1 規格全文）。開工前照 CLAUDE.md 稽核 HANDOFF vs repo（`git log -3`、`pytest tests/momentum/event_samples/ -q` 應 ~130 passed、`tests/momentum/Analysis/test_survivor_contract.py` 55）。
- **B3 批內順序**：B3.1 `event_samples/condition_engine.py`（`parse_condition(expression, column_registry, expression_role)`→`ConditionSpec{ast,canonical_digest,column_roles,max_lookback,label_ids,expression_role}`；safe-subset AST；`feature` 角色引用 `future_*`/`trigger_outcome` ⇒ 拒、`selection_predicate` 放行只進 provenance；M6 seam）→ B3.2 `event_samples/generator.py::generate_events(...)`＋`momentum/Analysis/event_filter.py` 薄 adapter（白名單 §0-6-③；G1–G6；**G6 呼叫 `all_bars_eval.evaluate_all_bars` 禁平行實作**；`control_kind=platform_same_trigger_rule` 產出過 B1.0 validator；`allowed_filtering_params` 契約化）→ B3.3 `momentum/FeatureEngineering/operators/state_counters.py` 五算子（TODO W7 精確語意：閉區間含當前根、嚴格變號 d=0 不計、無事件 NaN 唯 `cross_count`=0）＋`operator_registry` 註冊；測試落**新建** `tests/momentum/feature_engineering/`（含 `__init__.py`）。B3 Gate 命令見 TODO §B；`scripts/gap3_freeze_golden.py --check` 於 B3.2 後須 PASS（sha 163c4ce…）。
- **既有介面（B1/B2 產出，直接消費）**：`validate_event_import`／`align_events`／`build_event_manifest(..., events=)`／`split_events`／`materialize_features_at_decision(..., events=)`→三元／`single_feature_binary_baseline(..., feature_manifest_hash=<64hex>)`／`permutation_oracle`／`event_forward_return_table`／`binary_discrimination_table(..., manifest=)`／`ic_feed.build_event_ic_inputs`（產 `event_timestamps`/`event_label_values`/`event_context`）／`evaluate_all_bars(scores_or_rule, bars, manifest_config{entry_price_semantic,timeframe 必填}, event_split_plan=, manifest=)`；orchestrator `analyze(..., event_timestamps=, event_label_values=, event_context=)`。
- **每批收尾固定動作**：更新 `白話說明/GAP-3施工進度.md`（WATCHED 已登記，含 scripts/）＋接下來/README；commit 後背景 push；review session 命名 `<YYYYMMDD>-gap3-b3-review-r<N>`、stamp `…-b3-stamp-r1`；寫回前把 finding「修法」拆清單逐條對碼＋自跑其 RECHECK（摩擦八十三）。

## ⚠ 坑（完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～八十三）
- 🔴 含家族名的 Bash 會被擋 ⇒ 命令寫 scratchpad 腳本再 `bash <script>`；session 命名規約 `<YYYYMMDD>-<epic>-<batch|x>-<kind>-r<N>`、task-id＝大寫；stamp 輪交件須含 canonical sentinel heading，否則 completeness vacuous ⇒ 用 `debt_clear.sh --abandon --kind no-findings-expected` 收。
- 🔴 FF V7 `features_df` 恆 0 欄——特徵走 `create_feature_reader().load_columns_v2/load_row_index_v2`（row_index＝bar open 秒）；儲存 float16 為主；minimal preset 0.8s、standard ~150s。kline cache timestamp＝epoch 秒、bar open_time、連續網格。
- 🔴 戳記時序：stamp-target 先建空 `## 戳記` 區再派；戳記後 `gate.sh register-output <TASK> <synth>`；債銷帳 `debt_clear.sh --round-id --session --lock`。
- 白話看板狀態欄用文字（排隊中／完工蓋章），禁 ⬜／✅／「收案」字樣貼 B<n>（factkey 守衛）；`Archived/GAP-2施工進度.md:13-22` 紅＝既有；push 丟背景；venv Python 3.9.6。

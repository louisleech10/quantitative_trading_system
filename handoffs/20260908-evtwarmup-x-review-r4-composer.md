brief-kind: review
task-id: 20260908-EVTWARMUP-X-REVIEW-R4
family: composer
findings-round: R4
標的 commit: HEAD（`git diff 8f10d2e1..HEAD`）；B1 Task 1.1／1.2／2.1＋前端

## 被當成事實的未驗證假設（§0）

| 前提 | 裁定 | 覆核摘要 |
|---|---|---|
| `pytest tests/api/test_evtwarmup.py`＋`test_gap3_oos_downgrade` 0 skip | **fact-verified** | `venv/bin/python -m pytest tests/api/test_evtwarmup.py tests/api/test_gap3_oos_downgrade.py -q -rs` → **53 passed**, 0 skip, rc=0 |
| 前端 vitest 四檔 27 條 | **fact-verified** | `cd frontend && npx vitest run …DegradedBanner…MarginalICTable…ICSummaryTable.icirNull…oosDowngradeDocs` → **27 passed**, rc=0 |
| `global_run` 逐鍵不變 | **fact-verified** | 含於上列 pytest 之 `test_global_run_unchanged_vs_golden`；探針 `event_run` 形狀變、整檔 sha 與舊 golden 不同＝**預期**（brief §驗收） |
| `evtwarmup_phase_gate.sh 1` mutation 9 紅＋C0 綠 | **assumed（brief fact-verified）** | 本輪未在 clean clone 重跑 mutation（共用樹禁 mutate）；讀 `handoffs/20260908-evtwarmup-mutate.py` M1–M11／C0 錨點與 `test_evtwarmup.py` 選擇器對位 |
| `test_gap2_golden` 全綠 | **assumed（brief fact-verified）** | la0 整合耗時＞2min，本輪未單獨重跑；brief ＋ baseline sha lock 已列 |
| 使用者實機 1h／39k／34 事件 UAT | **unverified（brief NOT_RUN）** | `api/services/ic_analysis_service.py` 路徑未實機 |
| scan_cube 110 格 reason 透傳 | **unverified（brief NOT_RUN）** | `scan_cube.py` 無 `insufficient_test_events` 字面；契約鍵由 `oosDowngradeDocs.test.ts` 對證 |
| `_downgrade_branch` 不覆蓋富版 `oos_downgrade` | **fact-verified（讀碼）** | 第三寫出點 `if "oos_downgrade" not in metadata`（`:1238`）；`_annotate_root_status` 僅缺席補寫（`:1611`）；`test_oos_downgrade_has_exactly_three_write_sites_with_precedence` |

---

## 必答（成對）

### 1a. 分流可繞否？

**不可繞（照碼＋測試）。** 兩段 predicate 與 SPEC §C-3 一致：預檢 `_is_event_conditional_precheck`＝`bool(values) and enabled`（`:3235-3237`）；消費 `_is_event_conditional_consumed`＝`label_source=="event_label_value"`（`:3240-3242`）。`test_precheck_predicates_two_stage` 釘空 dict／disabled／棄條件；`test_precheck_event_conditional_skips_bar_warmup_but_global_keeps_it` 釘 34 事件豁免 vs 全域仍擋；stage4 skip 加 `not consumed`（`:3573`）。`{}`／`enabled=False`／`mainline_return_N` 皆回主線 bar 規則。fallback 重跑仍走同一 `analyze` 鏈（predicate 重算）。scan cube 每格獨立 `analyze`（brief NOT_RUN，設計與 Task 1.1 邊界③一致）。

### 1b. 合法事件 run 被誤擋／誤標？

**不會。** consumed＋34 測試段事件：precheck `None`、stage4 不 skip、holdout 套用。13 事件：地板 `insufficient_test_events`、**無** `_run_full_sample_fallback`（`fit_mode=train_mask`，`test_min_test_events_floor_keeps_holdout_and_flags_reason`）。棄條件 `(e′)`：`label_source=mainline_return_N`⇒地板 predicate 假⇒無 `insufficient_test_events`（`test_abandoned_conditional_path_is_not_flagged_insufficient_test_events`）。

### 2a. 地板時序與棄條件路徑

**正確。** 地板在 stage3 之後、`_apply_feature_filter` 之前（`:1225-1257` vs `:1259`）；predicate 僅 `_is_event_conditional_consumed`。棄條件後 `label_source=mainline_return_N`⇒consumed 假⇒不寫 `insufficient_test_events`／`ic_window_disclosure`。`_apply_feature_filter` 只裁欄不裁列（`:3447-3470`），不影響 `test_mask.sum()` 語意。

### 2b. `test_events`＝`test_mask.sum()` 是否等於「消費事件 ∩ 測試段」

**是（在 stage3 後 features_df＝事件列前提下）。** mask 由 `_derive_stage_masks` 對 stage3 後 index 重算（`:1213-1219`）；`test_events=int(test_mask.sum())`（`:1228`）。feature filter 在計數之後，不改列數。預檢路徑用 timestamps∩test_mask（`:3274-3277`）與 stage3 後列數可能略異，但地板以 stage3 後重算為準（SPEC §C-4／TODO 1.2「先重算」），與 R3 覆核一致。

### 3a. ICIR 消費端全覆蓋？

**已覆蓋生產主路徑。** `_apply_thresholds(..., icir_gate=not consumed)`（`:3859-3860`）＋`icir_skipped_event_path` 必存在（`:4317-4318`）；stage6 事件路徑 `redundancy_scores={ic_mean}`＋`tiebreaker_effective`（`:1321-1330`）；reporter 三處＋`get_top_features` 用 `_finite_or_neg_inf`；`_sanitize_summary_table_for_json` 擴 `icir`／`ic_mean`（`:950-952`）。API：`ic_analysis.py::_icir_key` None-safe（`:792-797`）；`ic_analysis_service._sort_artifact_rows` None→排後（`:1858-1861`）。`test_serialization_entries_have_no_nan_literal` 驗 `save_report`／sanitize＋`scan_cube._dumps` 無 `icir`／`ic_mean` NaN 字面（EW-RESID-5 其他欄仍可有 NaN）。cross_sectional 分支排序已有限檢查（`:1883-1887`），非本票事件路徑。

### 3b. 全域路徑 ICIR／golden 不變？

**是。** `icir_gate` 預設 True；全域 `removed["icir"]` 行為不變（`test_icir_not_a_gate_on_event_path_but_still_gate_on_global`）。`test_global_run_unchanged_vs_golden` 逐鍵對 `baseline.json::global_run` 且禁 `ic_window_disclosure`／`tiebreaker_effective`。有限 icir 之 `_finite_or_neg_inf` 不改全域排序順序。

### 4a. 兩值 status（方案 B）一致性

**一致。** 事件不足：`analysis_status=degraded_full_sample`＋`oos_downgrade.reason=insufficient_test_events`＋`oos_guarantees=false`（測試斷言）。契約 `ic_report_contract.json::reasons.oos_downgrade` 含新鍵（diff）。前端 `DegradedBanner`／`MarginalICTable`／`generate_ai_json` 依 reason 分文案（讀碼＋vitest 27 綠）。survivor 仍只允許兩值（`:275-279`）。

### 4b. 誠實性殘留面

除已改三處外，**仍可能誤導但為已知債**：① root 字面 `degraded_full_sample`（EW-RESID-4，`user-ruling` 兩值契約）；② `pass_class=full_sample_research_only` 鏡像 `oos_guarantees`、不表 fit 範圍（SPEC §C-4 notes）；③ `_specific_reason` 在**僅** `split.oos_guarantees=false` 且無 `split.reason` 時會回 `split_not_applied`（`:1530-1533`）——但本路徑已先寫富版 `oos_downgrade`，annotate 不覆蓋，使用者面讀 `metadata.oos_downgrade.reason` 正確。

### 5a. mutation 充分性／可漏網缺陷？

**M1–M11＋C0 與 SPEC §V 對位；M4／M9 由 M3／M5 共用 predicate 錨點涵蓋**（`mutate.py:79-80` 註解）。本輪未構造新漏網：若只刪 `ic_window_disclosure` 三行而保留地板，現有測試可能不紅（僅 floor case 斷言 disclosure；`min_test_events=0` 的 ok_oos 未斷言 disclosure）——屬低風險揭露漏測，不影響 OOS 判定正確性，不修不擋合併。

### 5b. 紅因＝斷言而非 import／語法？

**是。** M6 首跑假綠已補 `icir_skipped_event_path` 必存在斷言（brief 附錄）；各 mutation selector 指向行為 pytest `-k`，非 import 探針。

### 6. ≥10× 不必要複雜？

**無。** 兩 static helper、一 config 欄、契約一鍵、呼叫端 `icir_gate`／tiebreaker 字典、serializer 擴欄；無新 framework。

### 7. 可合併並進 B2（TFWINDOW）嗎？

**可合併；建議合併後立即進 TFWINDOW。** B1 與 TFWINDOW 邊界已釘：全域不接 `_adjust_rolling_windows`、全域不寫 `ic_window_disclosure`（SPEC §C-7／EW-RESID-1）。合併條件：本輪驗收綠＋無新 P0；既有 EW-RESID-6 紅不阻本票。

---

## §1 必查摘要（11 類）

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | 無；碼與 SPEC R2／TODO Task 1.1–2.1 一致 |
| 2 | 漏項 | brief NOT_RUN（UAT／scan cube 格）未覆；生產主路徑已測 |
| 3 | 不可測 | `test_evtwarmup`／mutation／vitest 可證偽 |
| 4 | quant | holdout＋事件地板方向正確；EW-RESID-1/2/3 仍 needs-research |
| 5–11 | 其餘 | 無過度工程；cache N/A；API/TS `icir: number\|null` 已接；測試非 smoke；無短命白工 |

---

## COMPOSER-R4-P3-00

**斷言**: 本輪逐項核對後無需阻擋合併的 P0／P1／P2 finding；B1 實作與 SPEC R2 逐條一致，必答 1–7 雙向有碼證，mutation 集合與 brief oracle 對位。

**碼證**: `git diff 8f10d2e1..HEAD` 對照 `docs/EVTWARMUP_SPEC.md` §C-3／§C-4／§C-6／Task 1.1–2.1；`venv/bin/python -m pytest tests/api/test_evtwarmup.py tests/api/test_gap3_oos_downgrade.py -q -rs` → 53 passed, 0 skip, rc=0；vitest 四檔 → 27 passed, rc=0；讀碼 `ic_filter_orchestrator.py:3233-3280`（分流）、`:1225-1257`（地板）、`:3856-4332`（ICIR gate）、`ic_reporter.py:22-30`／`:609-621`／`:950-952`；`shasum -a 256 -c handoffs/20260908-evtwarmup-r4-baseline.sha` → 全 OK。

**來源摘要**: docs/EVTWARMUP_SPEC.md#713968799d0210dce56f336aa2e0da727f26fcea7ae9f64d981e8bbbe99c4eaa;momentum/Analysis/ic_filter_orchestrator.py#9b3524583e64c3e9ab721590f3330e77182e35f35d25fb04e7063c351810c2c9;tests/api/test_evtwarmup.py#4a76e02354cc96b08e3ac58214c90463c1a32d7ad5d59c0006f7df8df6e1b5ae;handoffs/20260908-evtwarmup-mutate.py#d1d15bbfff1a9b0ef94b31fcbd8c1ac95da2ee297215a5220748fac3067ba814

[NON-BLOCKING] 信心度=High。核對依據：分流兩段判＋stage4 consumed 守衛；地板 stage3 後 consumed predicate＋(e′) 測試；ICIR 門檻跳過與消費端 `_finite_or_neg_inf`／sanitizer；三寫出點優先序；前端／AI JSON reason-aware；全域 golden 子集不變。brief NOT_RUN 項列入 §0 unverified，不升格 finding。

---

## Verdict：可合併

B1 實作收斂：事件路徑豁免 bar warmup、holdout＋`min_test_events` 地板、ICIR 診斷化與序列化安全化均與 SPEC 一致；無新 P0／P1。建議合併後進 `TFWINDOW`；`tests/golden/evtwarmup/baseline.json` 整檔 sha 仍為改前 `event_run`（探針整檔 False 為預期），可選 `--write` 更新 event_run 以利探針機械對照，非 merge-blocking。

---

## VERIFY（本輪實跑）

| 命令 | 結果 |
|---|---|
| `venv/bin/python -m pytest tests/api/test_evtwarmup.py tests/api/test_gap3_oos_downgrade.py -q -rs` | 53 passed, 0 skip, rc=0 |
| `cd frontend && npx vitest run …（四檔）` | 27 passed, rc=0 |
| `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` | 整檔 sha 與舊 golden 不同（event_run 預期變）；`global_run` 鍵集與 pytest golden 子集一致 |
| `shasum -a 256 -c handoffs/20260908-evtwarmup-r4-baseline.sha` | 全 OK |

---

ASSUMPTIONS_VERIFIED: pytest 53＋vitest 27；git diff 對 SPEC；讀碼分流／地板／ICIR／三寫出點；baseline sha lock
TESTS_RUN: 見 VERIFY 表；mutation／gap2 依 brief fact-verified 未重跑
FAILURES_SEEN: none
SCOPE_CHANGES: none（review-only）
NUMERIC_OR_SCHEMA_IMPACT: none（審查未改碼）
產出檔: handoffs/20260908-evtwarmup-x-review-r4-composer.md

STATUS: DONE

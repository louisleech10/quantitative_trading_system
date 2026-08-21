# GAP-3 B2 review R3 — grok（closure／sentinel）

task-id: 20260821-GAP3-B2-REVIEW-R3
family: grok
brief-kind: closure
brief: handoffs/20260821-gap3-b2-review-r3-brief.md
patch: `git diff 77140942..aff3f232 -- momentum/ tests/`（commit aff3f232「B2 review R2 codex 四條全修」）
R2 裁決: handoffs/reconcile/20260821-gap3-b2-review-r2/synth.md

## Verdict：可進三家 RECONCILE-STAMP（本家 sentinel 乾淨；修補未引入可證偽新缺陷）

### 必答

1. **codex 四條 CLOSED？**  
   本家非原提出方；以修補 diff＋鎖定測試靜態／動態核對，四條碼證均到位（詳下「R2 四條旁證」）→ 視為 **CLOSED**（最終 CLOSED／NOT-CLOSED 以 codex 本輪交件為準）。

2. **修補新引入問題？**  
   **無**（見 sentinel `GROK-R3-P3-00`）。第七鍵升版（仍 version 2）與 `common` 數值欄均經攻擊／核對；未另開 finding。

3. **可進三家 RECONCILE-STAMP？**  
   **可以（grok 本輪 APPROVED）**——前提為同輪 codex 對四條宣告 CLOSED、composer sentinel 亦乾淨且無新 BLOCKING。本檔戳記見文末。

### R2 四條旁證（非原提出方；碼證覆核）

| ID | 旁證摘要 |
|---|---|
| CODEX-R2-P1-01 | `tables.py`／`all_bars_eval.py` `common` 現含 `macro_auc`／`micro_auc`／`auc_cluster_ci`／`n_time_clusters`；`test_common_has_actual_macro_micro_cluster_ci`／discrimination 測鎖 micro==overall、單桶 CI `unavailable` |
| CODEX-R2-P1-02 | 步長改 `TIMEFRAME_SECONDS[timeframe]`；逐鄰 `diff==Δ`；duplicate open_time 拒；`entry_price_semantic`／`timeframe` 必填無預設；`k≥0`；`test_required_entry_semantic_timeframe_and_duplicate_bar_fail_closed` |
| CODEX-R2-P1-03 | builder 半套／未知鍵拒；v2 第七鍵 `label_source`；validator 不帶 report_meta 亦可以 payload 自述判 conditional IC；`test_partial_event_context_rejected_and_validator_independent_of_report_meta` |
| CODEX-R2-P1-04 | `analyze()` 於 `conditional_ic_abandoned` 寫 `metadata.conditional_ic={capability_status:unavailable, reason:insufficient_events, label_source:mainline_return_N, doc:…}`；A′ 測試鎖定 |

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**：第七鍵 `label_source` 加入 `event_definition_keys` 不需再 bump version（v2 仍在 B2.4 genesis 批內、無 v2 外部消費者） | **成立（攻擊不推翻）** | 契約 `version` 仍為 2；鍵集 12（含 `label_source` required+nullable）。builder 恆寫入該鍵（無 event_filter ⇒ `null`）。剝除鍵 ⇒ `missing required key 'label_source'`（舊檔若缺鍵會被拒）。`tests/momentum/Analysis/test_gap2_survivor_persist.py` → **9 passed**（GAP-2 重建路徑可過 validate）。工作區／`data_cache` 未發現既有 on-disk survivor JSON 消費者。誠實邊界：批外若有人持久化「無第七鍵」的舊 v2 檔，validate 會 fail-closed——屬 genesis 內可接受，不另開 finding。 |
| **assumed**：`conditional_ic_abandoned` 之下游消費＝報告 `metadata.conditional_ic` 機械欄（survivor 事件物件 `label_source=mainline_return_N`）已足；不另擋 stage4 計算 | **成立（攻擊不推翻）** | `ic_filter_orchestrator.py` 於 abandoned 後寫機械欄，隨後仍呼叫 `_stage4_ic_calculation`（方案② loud 續算）。A′：`test_conditional_ic_orchestrator_aprime_fallback_passthrough` 鎖 `metadata.conditional_ic` unavailable／insufficient_events／mainline_return_N。survivor builder 在 `event_filter.label_source=mainline_return_N` 時寫入同值且 validate 通過。攻擊「應擋 stage4」與 R1 已採方案②矛盾，本輪不推翻。 |
| fact-verified: 184 passed | **本輪複驗成立** | 見 TESTS_RUN |
| fact-verified: `common` 數值欄與 overall 一致 | **成立** | 手跑 all_bars：`micro_auc == overall.auc`（exact）；單 symbol ⇒ `macro_auc==micro_auc`；單桶 ⇒ `n_time_clusters=1`／CI `unavailable`。鎖定測 2 passed。 |

## GROK-R3-P3-00

**斷言**: 本輪逐項核對後無 finding——第七鍵升版（仍 version 2、鍵集+1）未破既有 v2／GAP-2 消費路徑；B2.2／B2.5 `common` 之 `micro_auc` 與 `overall.auc` 數值一致，cluster-aware 單桶反例到位；brief 兩條 assumed 攻擊不推翻。

**碼證**: `venv/bin/python -m pytest tests/momentum/event_samples/ tests/momentum/Analysis/test_survivor_contract.py -q` → **184 passed** rc=0（34.23s）；`git diff 77140942..aff3f232 --stat -- momentum/ tests/` → 10 files +177/−15；`pytest …/test_gap2_survivor_persist.py -q` → 9 passed；`test_common_has_actual_macro_micro_cluster_ci`＋`test_discrimination_oos_only_and_kind_strata` → 2 passed；手跑 all_bars `micro_auc==overall.auc` exact、單桶 CI unavailable；剝除 `label_source` ⇒ validate 拒；GAP-2-like builder `label_source=None`＋六鍵全 null validate OK；契約 version=2。

**來源摘要**: handoffs/reconcile/20260821-gap3-b2-review-r2/synth.md#5328b86dd0cd; handoffs/20260821-gap3-b2-review-r3-brief.md#40b9a2efffd3; momentum/Analysis/survivor_contract.py#785e4186305b; momentum/Analysis/contracts/ic_survivor_contract.json#3de3a1360de4; momentum/Analysis/event_samples/tables.py#e9856a0caa68; momentum/Analysis/event_samples/all_bars_eval.py#2b6d84f552e5; momentum/Analysis/ic_filter_orchestrator.py#935fb860c6b1; tests/momentum/event_samples/test_all_bars_eval.py#18cfb648ab75; tests/momentum/event_samples/test_tables.py#8c7389fd980a; tests/momentum/Analysis/test_survivor_contract.py#d2d56eaaf6d7; tests/momentum/event_samples/test_gap3_conditional_ic.py#df8bb6736b9c; docs/GAP3_EVENT_TODO.md#df04bdabf37d

正文：[MINOR] 信心度=High。閉合義務＝sentinel（第七鍵相容＋common↔overall）；R2 四條旁證 CLOSED；§0 兩 assumed 已攻。不受理 SPEC/TODO 重審／B3–B5／FF／B1／R1–R2 已 CLOSED 項。禁捏造湊數。

## 被當成事實的未驗證假設（§0）

無新增；brief 兩條 assumed 已攻擊（上表）。

ASSUMPTIONS_VERIFIED: 第七鍵不 bump version 在 B2.4 genesis／無外部 v2 消費者前提下成立；abandoned 下游以 metadata.conditional_ic＋label_source 機械欄足夠且不擋 stage4；common.micro_auc 與 overall.auc 一致；184 passed；patch=aff3f232
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ tests/momentum/Analysis/test_survivor_contract.py -q` → 184 passed in 34.23s rc=0；`pytest tests/momentum/Analysis/test_gap2_survivor_persist.py -q` → 9 passed；common 鎖定兩測 2 passed；手跑 micro==overall／單桶 unavailable／label_source strip／GAP-2-like validate
FAILURES_SEEN: none（合成 one-class 探針曾 KeyError auc，改用雙類報酬＋鎖定測後排除）
SCOPE_CHANGES: none（禁改碼；只產本檔＋交接檔）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only；觀察到契約鍵集+1 仍 version 2，未改產品碼）
OUTPUT: handoffs/20260821-gap3-b2-review-r3-grok.md
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護

## 戳記
RECONCILE-STAMP: grok APPROVED 2026-08-21 sha256:4d32d03c962663955df61627ac002c1e3e166fa86965285bb73b5e29c0fe9bec task:20260821-GAP3-B2-REVIEW-R3

STATUS: DONE

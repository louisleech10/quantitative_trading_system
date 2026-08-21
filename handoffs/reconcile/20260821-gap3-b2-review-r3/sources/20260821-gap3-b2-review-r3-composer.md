# GAP-3 B2 批 code review R3 閉合輪 — COMPOSER

family: composer  
task-id: 20260821-GAP3-B2-REVIEW-R3  
scope: 修補 diff `77140942..aff3f232`（`momentum/`＋`tests/`）；R2 synth `handoffs/reconcile/20260821-gap3-b2-review-r2/synth.md`；權威 `docs/GAP3_EVENT_TODO.md` FROZEN＋`docs/GAP3_EVENT_SPEC.md`；禁改碼  
brief: `handoffs/20260821-gap3-b2-review-r3-brief.md`  
R2 本家: `handoffs/20260821-gap3-b2-review-r2-composer.md`

RECONCILE-STAMP: composer APPROVED 2026-08-21 sha256:3de3a1360de41eaf33965b8114fb5a14a6932b1b705f3db4d853070f19a244b5 task:20260821-GAP3-B2-REVIEW-R3

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標注 | R3 sentinel 複核 |
|---|---|---|
| 修補後 184 passed（event_samples＋survivor）；golden `--check` PASS | fact-verified（brief） | **本輪重跑** → 184 passed in 32.19s rc=0；golden `--check` 依 brief 不再跑（避免並行） |
| R2 completeness PASS＋債銷帳 | fact-verified（brief） | 未重跑 `--lock`；以 R2 synth Y1–Y4 採納項＋`git diff 77140942..aff3f232` 對照 |
| assumed: 第七鍵 `label_source` 加入 event_definition_keys 不需 bump version（v2 genesis 批、無 v2 外部消費者） | **攻後＝成立（B2 scope）** | 契約仍 `version:2`；builder L474–486 必產第七鍵（無 event_filter ⇒ null）；GAP-2 路徑 `test_v2_event_keyset_and_nulls_when_no_context` 六鍵仍全 null 且 validate 綠；repo 內無 frontend／api 硬編碼六鍵集；**僅** patch 前手寫缺鍵 JSON 會被 `_check_object` 拒——本批無此 persisted 產物（golden PASS 前提） |
| assumed: `conditional_ic_abandoned` 下游消費＝報告 `metadata.conditional_ic` 機械欄已足 | **攻後＝成立（白名單）** | 非本家原提出方；`ic_filter_orchestrator.py:1012–1021` 寫 `{capability_status:unavailable, reason:insufficient_events, label_source:mainline_return_N}`；`test_gap3_conditional_ic.py` A′ assert 鎖定；survivor 物件 `label_source=mainline_return_N` 同輪 codex 域 |

VERIFY（本輪實跑）:
```
venv/bin/python -m pytest tests/momentum/event_samples/ tests/momentum/Analysis/test_survivor_contract.py -q → 184 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_all_bars_eval.py::test_common_has_actual_macro_micro_cluster_ci tests/momentum/event_samples/test_tables.py::test_discrimination_oos_only_and_kind_strata tests/momentum/Analysis/test_survivor_contract.py::test_v2_event_keyset_and_nulls_when_no_context tests/momentum/Analysis/test_survivor_contract.py::test_partial_event_context_rejected_and_validator_independent_of_report_meta -q → 4 passed rc=0
git diff 77140942..aff3f232 --stat -- momentum/ tests/ → 10 files +177/-15
rg 'label_source|macro_auc|micro_auc' momentum/Analysis/contracts/ic_survivor_contract.json momentum/Analysis/event_samples/{all_bars_eval,tables}.py → 命中契約第七鍵＋共同欄四數值鍵
```

---

## 1. brief 必答

1. **codex 四條 CLOSED？** 本輪 composer 旁證重掃 → **4/4 可判 CLOSED**：Y1 `test_common_has_actual_macro_micro_cluster_ci`／`test_discrimination_oos_only_and_kind_strata` 鎖 macro／micro／cluster-CI／單桶 unavailable；Y2 `test_required_entry_semantic_timeframe_and_duplicate_bar_fail_closed`＋`all_bars_eval.py:45–60,119–128` 契約 TF 逐鄰；Y3 `test_partial_event_context_rejected_and_validator_independent_of_report_meta`＋契約 `label_source` 第七鍵；Y4 `test_gap3_conditional_ic.py` A′＋`ic_filter_orchestrator.py:1012–1021`。最終 CLOSED 裁決仍屬 codex 本家重驗。
2. **修補新引入問題？** **無** — sentinel 兩軸（v2 第七鍵消費、common 數值對齊 overall）攻擊後不成立；184 passed 含 B2.4 v2 鍵集／conditional IC／cluster-CI 回歸。
3. **可進三家 RECONCILE-STAMP？** **composer 側可** — 本輪 sentinel 0 finding；**待 codex 四條正式 CLOSED＋grok sentinel 同輪 rc=0 後** quorum 戳 synth → B2 CLOSED。

---

## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對後無 finding——R3 修補 diff 下 v2 第七鍵 `label_source`（契約仍 version 2）未破既有 v2 消費語意（GAP-2 六鍵可全 null、builder 必產第七鍵 nullable）；B2.2／B2.5 `common.macro_auc`／`micro_auc` 與 `overall.auc` 在單 symbol 手算路徑一致且測試 exact 鎖定；未引入新的 AR-3 機械欄或 survivor／all-bars 可證偽缺陷。

**碼證**: `venv/bin/python -m pytest tests/momentum/event_samples/ tests/momentum/Analysis/test_survivor_contract.py -q` → 184 passed rc=0；`test_v2_event_keyset_and_nulls_when_no_context` → build＋validate 綠且 `label_source` 存在可 null；`test_common_has_actual_macro_micro_cluster_ci` assert `micro_auc`／`macro_auc` ≈ `overall.auc`（abs=1e-12）且單桶 `auc_cluster_ci.status==unavailable`；`ic_survivor_contract.json:256–319` 第七鍵 `required:true,nullable:true`；`tables.py:257–266`／`all_bars_eval.py:259–262` micro 與 overall 同源 `roc_auc_score`；brief 兩條 assumed 攻擊見 §0 表。

**來源摘要**: momentum/Analysis/contracts/ic_survivor_contract.json#3de3a1360de4; momentum/Analysis/event_samples/all_bars_eval.py#2b6d84f552e5; momentum/Analysis/event_samples/tables.py#e9856a0caa68; handoffs/reconcile/20260821-gap3-b2-review-r2/synth.md#5328b86dd0cd; handoffs/20260821-gap3-b2-review-r3-brief.md#40b9a2efffd3

正文：[MINOR] 信心度=High。composer 閉合義務＝sentinel 兩軸＋旁證 codex Y1–Y4；R2 本家 COMPOSER-R1-P1-01／P2-01 仍 CLOSED（`_common_constraint_block` 未 regress）。禁捏造湊數。

---

## Verdict：可進 B2 CLOSED（composer 側；待 codex／grok R3 quorum）

R3 修補與 R2 synth Y1–Y4 一致；sentinel 0 finding；184 passed。composer 無阻擋項。

---

ASSUMPTIONS_VERIFIED: 184 passed 本輪重跑；v2 第七鍵攻擊不推翻（GAP-2 null 語意保留、builder 必產鍵）；common macro/micro 與 overall 一致有測試 exact；codex Y1–Y4 旁證四項測試／碼證綠  
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ tests/momentum/Analysis/test_survivor_contract.py -q` → 184 passed rc=0；標靶 4 tests → 4 passed rc=0  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only；schema 仍 v2、鍵集擴一已在 R2 採納）  
HANDOFF_OUTPUT: `handoffs/20260821-gap3-b2-review-r3-composer.md`

STATUS: DONE

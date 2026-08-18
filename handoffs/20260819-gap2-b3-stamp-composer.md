# GAP-2 B3 RECONCILE-STAMP — composer（R19）

**family**: composer  
**task-id**: 20260819-GAP2-B3-STAMP-R19  
**stamp-target**: `handoffs/reconcile/20260819-gap2-b3-review-r18/synth.md`  
**修補 commit**: `bfe4da99`  
**判定**: APPROVED

## 建議 append 至 `## 戳記`（單行）

RECONCILE-STAMP: composer APPROVED 2026-08-19 sha256:005f5472f32e2ed8550b89696b7ead659e6e481c969f397e1ab0c0ea250fe6c5 task:20260819-GAP2-B3-STAMP-R19

## body_sha256

`bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260819-gap2-b3-review-r18/synth.md` → `005f5472f32e2ed8550b89696b7ead659e6e481c969f397e1ab0c0ea250fe6c5`（與 brief 一致）

## 判準 1–8 逐項

| # | 判準 | 結果 |
|---|------|------|
| 1 | completeness_check 0 掉項 | PASS — `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260819-gap2-b3-review-r18/sources.lock`；codex 8＋composer 1＋grok 1 全在 synth |
| 2 | M1 P0 fit_mode 原值 | PASS — `git show bfe4da99` 改為非空字串驗證；in-memory `fit_mode=train_mask` build→validate 不 raise；pytest `test_provenance_fit_mode_raw_orchestrator_values_accepted` PASSED |
| 3 | M2 resolve_ref escape | PASS — in-memory ABSOLUTE_REF raise；pytest `test_resolve_ref_rejects_escape` PASSED |
| 4 | M3 event／fallback／root status | PASS — in-memory INCOMPLETE_EVENT raise、缺 full_index raise、`unexpected_status` raise；pytest `test_event_object_mode_invariants`／`test_fallback_requires_full_index_and_uses_real_index`／`test_unknown_root_status_raises` PASSED |
| 5 | M4 n_samples 對帳 | PASS（部分接受理由成立）— `n_samples=1` raise、`n_samples=6000` 合法（purge/embargo 使 total>train+test）；marginal n_test vs split test_rows exact；pytest `test_n_samples_total_reconciliation` PASSED。total 採 `≥` 合理：purge/embargo 下 exact `==` 對 total 不成立，test 列 exact 已覆蓋關鍵對帳 |
| 6 | M5／M6 checklist＋tamper＋naive | PASS — ⑭含 `n_samples_total`/`n_samples_test`/`feature_name`/composite/removed/view 巢狀；⑩ `test_unknown_key_raises` 含 `removed_candidates[z]` 與 composite 物件層；⑱ `test_event_identity_naive_string_matches_aware` PASSED |
| 7 | 既有未破壞 | PASS — `pytest test_survivor_contract.py -q` 44 passed；`test_ichc_contract_sync.py` 5 passed；`mutation_probe_check.sh` PASS；receipt `20260818T232727Z-gap2-B3-probe.log` 八條 RED+GREEN |
| 8 | Verdict 一致＋diff 範圍 | PASS — synth Verdict「需修補後進 B4」與 M1–M6 全接受一致；`git diff 038fd10b bfe4da99 --stat` 排除 hook 後僅 survivor_contract／測試／AMENDMENTS／handoffs／白話；契約 JSON diff 空 |

## M4 判斷備註

主委採 `n_samples_total ≥ marginal/split 列數和`＋`n_test` exact 之理由成立：purge/embargo 使 train+test < total 為正常設計；對 test 列採 exact 已防錯誤切分。不 BLOCK。

---

ASSUMPTIONS_VERIFIED: body sha256 實跑與 brief 一致；修補 commit `bfe4da99` 已 checkout 工作區；未改 synth／未 commit／未 push  
TESTS_RUN: `reconcile_body_hash.sh` rc=0；`completeness_check.sh --lock` rc=0；`pytest test_survivor_contract.py -q` 44 passed；`pytest test_ichc_contract_sync.py -q` 5 passed；`mutation_probe_check.sh` PASS；in-memory M1–M4 codex 反例 7/7 PASS；R18 專項 pytest 17 passed  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（僅產出本交件檔）  
NUMERIC_OR_SCHEMA_IMPACT: none（驗收 only；契約 JSON 未動）

STATUS: DONE

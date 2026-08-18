# GAP-2 B3 RECONCILE-STAMP — composer（R20）

**family**: composer  
**task-id**: 20260819-GAP2-B3-STAMP-R20  
**stamp-target**: `handoffs/reconcile/20260819-gap2-b3-review-r18/synth.md`  
**修補 commit**: `bfe4da99`  
**判定**: APPROVED

## append 至 `## 戳記`（單行，已執行）

RECONCILE-STAMP: composer APPROVED 2026-08-19 sha256:005f5472f32e2ed8550b89696b7ead659e6e481c969f397e1ab0c0ea250fe6c5 task:20260819-GAP2-B3-STAMP-R20

## body_sha256

`bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260819-gap2-b3-review-r18/synth.md` → `005f5472f32e2ed8550b89696b7ead659e6e481c969f397e1ab0c0ea250fe6c5`（與 brief 一致）

## 判準 1–8 逐項

| # | 判準 | 結果 |
|---|------|------|
| 1 | completeness_check 0 掉項 | PASS — `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260819-gap2-b3-review-r18/sources.lock`；codex 8＋composer 1＋grok 1 全在 synth |
| 2 | M1 P0 fit_mode 原值 | PASS — `git show bfe4da99` 改為非空字串驗證；pytest `test_provenance_fit_mode_raw_orchestrator_values_accepted` PASSED（`fit_mode=train_mask` build→validate 不 raise） |
| 3 | M2 resolve_ref escape | PASS — pytest `test_resolve_ref_rejects_escape` PASSED（ABSOLUTE_REF in-memory raise） |
| 4 | M3 event／fallback／root status | PASS — pytest `test_event_object_mode_invariants`／`test_fallback_requires_full_index_and_uses_real_index`／`test_unknown_root_status_raises` PASSED |
| 5 | M4 n_samples 對帳 | PASS（部分接受理由成立）— pytest `test_n_samples_total_reconciliation` PASSED；`n_samples=1` raise、`n_samples=6000` 合法；marginal n_test vs split test_rows exact；purge/embargo 下 total `≥` 合理 |
| 6 | M5／M6 checklist＋tamper＋naive | PASS — pytest `test_checklist_subset_of_contract_keys`／`test_unknown_key_raises`（8 paths 含 composite/removed）／`test_event_identity_naive_string_matches_aware` PASSED |
| 7 | 既有未破壞 | PASS — `pytest test_survivor_contract.py -q` 44 passed；`test_ichc_contract_sync.py` 5 passed；`mutation_probe_check.sh` PASS；receipt `20260818T232727Z-gap2-B3-probe.log` 八條 RED+GREEN |
| 8 | Verdict 一致＋diff 範圍 | PASS — synth Verdict「需修補後進 B4」與 M1–M6 全接受一致；`git diff 038fd10b bfe4da99 --stat` 排除 hook 後僅 survivor_contract／測試／AMENDMENTS／handoffs／白話；契約 JSON diff 空 |

## M4 判斷備註

主委採 `n_samples_total ≥ marginal/split 列數和`＋`n_test` exact 之理由成立：purge/embargo 使 train+test < total 為正常設計；對 test 列採 exact 已防錯誤切分。不 BLOCK。

---

ASSUMPTIONS_VERIFIED: body sha256 實跑與 brief 一致；修補 commit `bfe4da99` 已存在工作區；已 append 戳記至 stamp-target；未 commit／未 push  
TESTS_RUN: `reconcile_body_hash.sh` rc=0；`completeness_check.sh --lock` rc=0；`pytest test_survivor_contract.py -q` 44 passed；`pytest test_ichc_contract_sync.py -q` 5 passed；`mutation_probe_check.sh` PASS；M1–M6 專項 pytest 28 passed  
FAILURES_SEEN: none  
SCOPE_CHANGES: append 一行至 `handoffs/reconcile/20260819-gap2-b3-review-r18/synth.md` `## 戳記` 區（brief 指定）  
NUMERIC_OR_SCHEMA_IMPACT: none（驗收 only；契約 JSON 未動）

STATUS: DONE

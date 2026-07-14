# IC1CFR-STOPGAP r4b Codex SPEC adversarial review
task-id: IC1CFR-STOPGAP | date: 2026-07-14 | scope: SPEC r4 only

## Verdict
- CX-1 CLOSED: pure intermediate/advanced tier is removed from the factor-return force-enable loop; default false therefore stays out of `run_targets`, yielding `not_run` with no results section.
- CX-2 CLOSED: the SPEC now requires `_run_factor_return` to raise `ModuleUnavailableError` and a dedicated parent-loop branch before `except Exception`; that branch owns the unavailable union/summary, appends no error, and is excluded from completed/skipped counts.
- CX-3 CLOSED: the contract now preserves the `:1601` global deep-off early return; `force_modules` does not bypass it.
- CX-4 CLOSED: §G now compares the frozen successful before value `completed` to after `not_run`, rather than inventing an `enabled` summary state.

## New-hole scan
- NON-BLOCKING: TODO generation should enumerate legacy assertions beyond the SPEC's narrow output-key grep, notably `tests/phase24/test_deep_analysis_config.py`, `tests/momentum/test_tier_config.py`, and `tests/phase26/test_deep_analysis_integration.py`; these are expected contract migrations, not reasons to alter r4 semantics.
- NON-BLOCKING: Task 1.3's factory caller allowlist wording must be calibrated to the repo: the current runner directly imports `FactorReturnAnalyzer`, while `create_factor_return_analyzer` callers include factory tests. The SPEC already records this calibration for TODO/implementation.
- NON-BLOCKING: custom `feature_tiers.module_overrides.factor_return=true` should join typed module/config override coverage; it converges on the same runner and unavailable branch, so no finite-value bypass exists.

正在做: r4 SPEC freeze review complete.
待辦: frozen 後生成 TODO，納入上述三項 non-blocking 校準。
阻塞: none。
本次決策: APPROVE；僅新增本 review 並追加 reconcile 戳記，未改 SPEC/code/root HANDOFF。
踩坑提醒: TODO 尚未生成符合既定階段流程，不是本輪阻塞。
ASSUMPTIONS_VERIFIED: read HANDOFF.md/CLAUDE.md/SPEC r4/TODO template/reconcile; inspected `ic_filter_orchestrator.py:1570-1725,3310-3390` and relevant config/API/reporter/test callsites.
TESTS_RUN: read-only `sed`/`nl`/`rg`; hash command returned `66db1109...92008777`; review-only, no pytest/vitest.
FAILURES_SEEN: prior r4 review incorrectly treated pre-freeze TODO absence as blocking; user workflow clarification resolves it.
SCOPE_CHANGES: none; outputs are this file plus one reconcile stamp line.
NUMERIC_OR_SCHEMA_IMPACT: none from review; r4 specifies unavailable union and count exclusion.
SPEC-REVIEW-R4: APPROVE

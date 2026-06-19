# T-C read-only code review — Codex — 2026-06-19

## Verdict
PASS — 未發現 blocking/major 新問題；6 個 adversarial findings 已在實作層面修補。

## Scope Reviewed
- Commits: c07c70f (估算+precheck), f2de52e (tests)
- Sources: docs/CGSA_L3_DISK_PRECHECK_SPEC.md, handoffs/20260619-tc-adv-codex.md
- Files reviewed: column_group_registry.py, feature_factory.py, multi_tf_generator.py, test_cgsa_disk_precheck.py

## Checks
- adv#1: `_precheck_cgsa_cumulative_disk` uses `needed = planned_new + max_shard*2 + reserve`, no registry_occupied double-count.
- adv#3: planned bytes simulate `_persist_layer_output_groups` 5000-col chunks plus `_compute_shard_slices`.
- adv#4: precheck is wired at shared `_persist_layer_output_groups`, covering serial, parallel primary, worker, and single-TF L3-L6 callers.
- adv#2: reserve env `FFACT_CGSA_DISK_RESERVE_GIB`, default 2.0 GiB, invalid/negative fallback.
- adv#5: estimate uses actual pre-persist DataFrame shape; persist coerces dtype to float32 without changing shape.
- adv#6: registry precheck returns on non-DataFrame/unreadable shape.
- 防假綠: commits only add new test file; no existing assertions relaxed; no skip/xfail in new tests.
- Line 103 regression test exists and genuinely verifies large existing registry occupancy + small increment does not abort.

## Residual Risks
- Integration tests named serial/parallel hit the shared persist helper directly via a minimal factory; production coverage is still supported by call graph, but tests do not execute the full MultiTFGenerator branch bodies.
- Non-DataFrame fallback is implemented in registry precheck; `_persist_layer_output_groups` still assumes `.empty` before calling it, matching prior DataFrame-only contract.

## Tests Run
- `source venv/bin/activate && pytest tests/feature_engineering/test_cgsa_disk_precheck.py -q` → 10 passed.
- `git show --check c07c70f` and `git show --check f2de52e` → no whitespace errors.

STATUS: DONE

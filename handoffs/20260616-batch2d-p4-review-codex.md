# Batch2D P4 Test Review — Codex

## Scope
- Reviewed: `tests/feature_engineering/test_batch2d_dstar_align.py`.
- Context read: `HANDOFF.md`, `CLAUDE.md`, `docs/BATCH2D_DSTAR_ALIGN_{SPEC,TODO,MANIFEST}.md`.
- No commits made. Root `HANDOFF.md` not edited per executor contract; this append-only handoff is the report.

## Findings
- BLOCKING: none.
- MAJOR: none.
- MINOR: none.

## Independent Verification
- Slow P4 pytest command:
  `pytest tests/feature_engineering/test_batch2d_dstar_align.py::TestP4Parity::test_t3_d_star_parity_exact_on_l12_intersection tests/feature_engineering/test_batch2d_dstar_align.py::TestP4Parity::test_control_l3_l6_exact_unchanged_vs_frozen tests/feature_engineering/test_batch2d_dstar_align.py::TestP4Parity::test_cgsa_baseline_regression_exact_vs_frozen tests/feature_engineering/test_batch2d_dstar_align.py::test_t4_value_parity_inventory_record_only -q`
- Result: 4 passed in 774.46s.
- Separate stats script reran T3 real-kline frame+CGSA d* paths and read frozen golden inventory.

## Measured Numbers
- T3 d* counts: frame=3736, CGSA=3737, frame L1/L2=3736, frame L3-L6=0.
- T3 L1/L2 bare-key intersection=3458, mismatches=0, floor=3000.
- Control frozen frame: rows=367, columns=165268, L3-L6 columns checked=127744, canonical_sha256=`fd7817bd1c3fee68cf4d81c845e2d72e3db9799604f5d044e547ab1c7e361fbb`.
- CGSA frozen frame: rows=367, columns=165309, canonical_sha256=`dc7d1b86d51fcc9697b6e309da087b2ecb9df4fe577cc7026286d11e7f22e396`.
- T4 inventory: L1/L2 expected provenance=46438, present both outputs=37524, value hash matches=0, NaN-mask hash matches=37524, row-index hash equal=False.

## Anti-Fake-Green Checks
- T3 is non-vacuous: it runs both paths with real kline, requires a d* cache file, requires non-empty intersection, asserts mismatch count 0, and floor 3458 >= 3000.
- T4 exact value parity is not relaxed: exact gate is skipped with explicit out-of-scope reason; inventory records counts and uses exact SHA equality only, with no rtol/atol.
- Control gate is exact: per-column `value_sha256` and `nan_mask_sha256` compare live vs frozen for L3-L6, failing on any mismatch.
- CGSA gate is exact: live canonical SHA must equal frozen canonical SHA.
- Kline missing is fail-closed: `_require_real_kline()` calls `pytest.fail`, not skip; all slow P4 gates call it.
- No `rtol`, `atol`, `allclose`, or `isclose` found in the reviewed P4 test.
- `tests/golden/l65/test_inventory.txt` was not modified.
- Existing assertion weakening: no tracked test assertion loosening found in the reviewed diff; existing `tests/test_l65_parallel.py::test_fracdiff_registry_layer_filter_uses_group_metadata` was not modified.

ASSUMPTIONS_VERIFIED: real kline exists and slow P4 gates execute real BTCUSDT/12h paths; T3 d* parity is exact on 3458 shared L1/L2 keys; control and CGSA gates are SHA-exact; T4 remains inventory/out-of-scope without tolerance; l65 test_inventory untouched.
TESTS_RUN: P4 slow pytest command above -> 4 passed in 774.46s; independent stats script -> T3 intersection 3458, mismatches 0, control L3-L6 checked 127744, T4 counts as listed.
FAILURES_SEEN: none.
SCOPE_CHANGES: none.
NUMERIC_OR_SCHEMA_IMPACT: review only; no code/schema/output edits by Codex.
STATUS: APPROVE — T3 3458/3458 exact, 0 mismatch; control L3-L6 127744 columns exact vs frozen; CGSA canonical SHA exact vs frozen; T4 inventory 46438 expected / 37524 present-both / 0 value matches / 37524 mask matches / row-index equal False.

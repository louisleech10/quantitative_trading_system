# P2DEBT-T2 TODO R1 adversarial review — codex — 2026-07-11
Input: `P2DEBT-T2-TODO-DRAFT-R1.md` vs frozen `P2DEBT-T2-SPEC-DRAFT-R4.md`; grok review not read.

## BLOCKING findings
B1 — Completeness mutation is not 100%: SPEC requires missing target/subtarget mutation for every S1–S11; TODO 1.3.2 names one unparameterized case and does not enumerate S2/S10 subtargets. Positive 11-probe coverage cannot substitute.
B2 — “read-only collect” premise is false: root `tests/conftest.py:108` writes `tests/golden/l65/test_inventory.txt` on every `--collect-only`. Spot-runs changed it to `BLOCKER: no L6.5/preprocessing tests collected`; no checkout/restore was run. TODO collect gates therefore pollute out-of-scope state, and filename-only pre-dirty subtraction can hide later changes to an already-dirty file.
B3 — Exit masking: TODO:326 `pytest ... | tail -1` returns `tail` status; TODO:547 `grep ... | wc -l` exits 0 even when imports exist. Read-only counterexamples `false | tail -1` and a synthetic matching `grep | wc -l` both exited 0.
B4 — Final Acceptance is not one executable contract: TODO:515 `exit $rc` terminates the block before steps 2–8. Scope gate heredoc is knowingly incomplete (“add all ... later”), includes conditional `tests/conftest.py`, and thus cannot produce the promised exact diff as written.
B5 — S11 gate is contradictory: TODO:370 expects raw `create_feature_factory(` count 7 after replacing all 7, then TODO:372 expects helper count 7 although a definition/call count needs explicit semantics. Current read-only receipt is exactly 7 raw calls; the proposed gate cannot distinguish unwired from wired.
B6 — TODO:317 says two individual tests receive `pytestmark`; `pytestmark` is module-level, so this either marks STUB siblings or is not implementable. Require function decorators/usefixtures.
B7 — State contract distortion: TODO:228 says nested second activation leaves `activation_count` at 0 although the first activation is still active; expected unchanged-at-one/current-owner semantics must be stated.
B8 — Trace totals are false: V1–V9 plus V3b is 10, not 11; listed total is 88, not 89. Coverage rows exist, but the claimed 100% audit arithmetic is not trustworthy.
B9 — GEN wiring only says “call” `run_with_manual_redirect()`; no context-manager/callback bracket is specified, so an immediate activate/finally-deactivate implementation can leave the generator body unredirected.

## Receipts
True read-only spot-runs: caller enumeration=16 (exit 0); `rg from api` count=0 (exit 0); FF raw factory calls=7 (exit 0); three I1 nodeids all found; every existing coverage/patch target path checked exists.
Requested command mechanics spot-runs: V1 collect=10, V2=2, V6=32, V7=141 (all exit 0), but they exposed B2 and are not read-only in this repo. No pytest body ran; no `data_cache` write was performed.
Patch points verified real: S1/S2/S3–S8/S10 methods, API session/module fixtures, seven FF calls, all 16 callers and all Appendix A existing files. New-file targets are within frozen allowed scope.

ASSUMPTIONS_VERIFIED: frozen SPEC provenance includes Composer APPROVED stamp; user declared SPEC frozen; target existence/counts and shell polarity receipts above
TESTS_RUN: pure rg/path checks plus collect-only V1/V2/V6/V7; no polluting test body
FAILURES_SEEN: collect-only unexpectedly rewrote tracked `tests/golden/l65/test_inventory.txt`; left untouched per no restore instruction
SCOPE_CHANGES: only this review output intentionally added; collection-hook side effect documented in B2
NUMERIC_OR_SCHEMA_IMPACT: none
HANDOFF_OUTPUT: `handoffs/P2DEBT-T2-TODO-REVIEW-codex.md`
Verdict: BLOCK — incomplete seam mutation coverage and multiple false-green/non-executable exit contracts
STATUS: BLOCKED — TODO R1 requires revision

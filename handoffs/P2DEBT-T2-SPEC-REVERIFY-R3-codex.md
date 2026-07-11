# P2DEBT-T2 SPEC R3 re-verify — codex — 2026-07-11
Scope: `handoffs/P2DEBT-T2-SPEC-DRAFT-R3.md` R3-CLOSURE; Grok re-verify was not read.
RECEIPT P0: `cd /tmp/p2debt-t2-proto && python -m pytest -q` → exit 0, `7 passed in 0.04s`.
RECEIPT P1: prototype targeted mutation test → exit 0, `MUTATION_CANARY=1`, `1 passed`.
RECEIPT P2: temporary redirect-removed hermetic assertion → exit 1; digest gained feature+report, `1 failed`; temp test removed.
RECEIPT P3: opt-in session + opt-in function + non-opt-in last → exit 0, `3 passed`; non-opt-in remained production-relative.
RECEIPT P4: prototype `SessionRedirectPatcher` + `asyncio.to_thread(analyze_and_persist)` → exit 1; worker returned `data_cache/features/...`; temp test removed.
RECEIPT R1: `rg -l '\.(analyze|start_analysis|refilter)\(' tests/ --glob '*.py' | sort` → 16 files; list excludes all 3 API polluter files.
RECEIPT R2: V1 collect-only → 10; V7 six-file collect-only → 141 (five ML files + FF e2e), exit 0; no repo pytest body run.
RECEIPT R3: fixture grep → analysis/export session, deep completed task module; run-selector factory is stubbed at L215–227.
RECEIPT S1: shell-contract probes → syntax 0; failed PRE substitution 1; failed pytest analogue 1; digest mismatch 1 + `DIGEST_DIFF_EMPTY=0`.
- B1 **STILL-OPEN**: the claimed “16-caller” table contains the 16 rg files plus 3 API files (19 total); it is not an exact enumeration. V7’s listed six files/141 collection and run-selector GUARD are individually confirmed.
- B2 **STILL-OPEN**: §SEAM is not same-shape for real API execution. Prototype routes through a TLS-aware production getter; R3 instead leaves S1–S11 wrapper installation unspecified, and the proven TLS design fails across `asyncio.to_thread`.
- B3 **CLOSED** at SPEC command/exit-contract level: the shell is syntactically complete and `set -euo pipefail` does not mask digest-command, pytest, or mismatch failures.
- B4 **STILL-OPEN**: A/B/C and `passed not skipped` are stated, but Run C OFF lacks the prototype’s tmp `work/data_cache` chdir; as written it can write repository `data_cache`.
- B5 **STILL-OPEN**: I1 names no three fixed nodeids and no subprocess-side canary assertion/command, so `get_redirect_install_count()==0` is not executable. Root `tests/conftest.py` has no redirect autouse.
- M1 **CLOSED**: V1 contract is 9 passed/1 named perf skip; V5 uses `-s`, mandates OFF and forbids skipped; V3 exposes stdout.
- N1 **STILL-OPEN**: same-thread activate/deactivate works, but thread-local state does not propagate to the API analyzer worker; session/module polluters remain unsafe.

NEW-1 **BLOCKING**: `SessionRedirectPatcher`’s spy belongs to the setup context, but the prototype session test asserts a different function-fixture spy; R3 exposes no teardown assertion for the session spy.
NEW-2 **BLOCKING**: V3 digest harness covers only four IC selections; V2/V5/V6/V7 (API, golden, ML, FF) run outside the only declared digest proof, so full-set hermeticity can pass without a before/after receipt.
NEW-3 **PROCESS NOTE**: repo was dirty before audit; collect-only triggers existing root hook that writes `tests/golden/l65/test_inventory.txt`. It was already modified at initial status and was not restored or otherwise edited.

ASSUMPTIONS_VERIFIED: exact prototype suite; mutation sensitivity; non-opt-in isolation; real API `asyncio.to_thread`; caller/ML enumeration; fixture scopes; shell failure propagation.
TESTS_RUN: P0–P4, R1–R3, S1 above; polluting repo pytest bodies: none.
FAILURES_SEEN: expected mutation failure; blocking cross-thread prototype failure.
SCOPE_CHANGES: none; output only `handoffs/P2DEBT-T2-SPEC-REVERIFY-R3-codex.md`.
NUMERIC_OR_SCHEMA_IMPACT: none.
Verdict: BLOCK — TLS redirect fails the real API worker boundary; coverage, OFF-run safety, I1, spy, and full-set digest contracts remain incomplete.
STATUS: BLOCKED — reconcile 未核可

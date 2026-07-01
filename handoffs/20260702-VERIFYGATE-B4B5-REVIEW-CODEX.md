# VERIFYGATE B4+B5 adversarial code review — Codex

Scope reviewed:
- Diff: `scripts/gate.sh`, `scripts/mutation_probe_check.sh`, `scripts/reconcile_stamps_check.sh`, `scripts/template_check.sh`, `scripts/verification_claim_check.py`
- New files: `scripts/verify_audit_chain.py`, `scripts/verify_task_provenance.py`, `templates/RESULT_TEMPLATE.md`, `tests/governance/test_verify_gate_b4.py`, `tests/governance/test_verify_gate_b5.py`
- Specs: `docs/VERIFY_GATE_SPEC.md` P4/P5, `docs/VERIFY_GATE_TODO.md` Task 4.1-4.4 / 5.1-5.3
- Composer handoffs: B4/B5 implementation reports

## Verdict

VERDICT: CHANGES_REQUIRED

## BLOCKING Findings

### B4-1 — `gate.sh` lets non-ADV adversarial files bypass W3 provenance entirely

- File: `scripts/gate.sh:56-66`
- Status: BLOCKING
- Attack surface: Task 4.2/4.3 provenance, `waived:` escape surface
- Evidence: P4-2 says high-risk `--adversarial` path must match `handoffs/*-ADV-{CODEX,COMPOSER}.md` plus have a dispatch audit event. The implementation only runs `verify_task_provenance.py` inside a `case` branch when the path already matches the ADV pattern. Existing files with any other path fall through and can pass high-risk dispatch.
- Reproduced:
  ```bash
  tmp=$(mktemp)
  printf '# not an ADV\n' > "$tmp"
  bash scripts/gate.sh dispatch \
    --intent test \
    --risk high \
    --facts-asked none-needed:test \
    --review-role single-executor:n/a \
    --template n/a:test \
    --adversarial "$tmp"
  # observed: GATE PASS, rc=0
  ```
- Counterexample: `/tmp/not-adv.md` or `handoffs/foo.md` can satisfy `--adversarial` without ADV naming or committee provenance when `--spec` is absent.
- Suggested fix: For high-risk non-waived `--adversarial`, reject any path that is not either an approved reconcile file path handled by `reconcile_stamps_check.sh` or an ADV path accepted by `verify_task_provenance.py`. The current default case should be fail-closed, not no-op.

### B4-2 — Reconcile stamp grandfather can be forged by backdating the stamp

- File: `scripts/verify_task_provenance.py:151-158`
- Status: BLOCKING
- Attack surface: Task 4.3 provenance
- Evidence: `check_stamp_provenance()` allows any stamp with `APPROVED <= 2026-07-01` to skip committee dispatch lookup when no event exists. The decision is based only on the stamp text date, not an allowlist of pre-existing reconcile files or stamp hashes.
- Counterexample: A newly created reconcile can include a correct body hash plus `RECONCILE-STAMP: composer APPROVED 2026-07-01 ... task:fakestamp1` and bypass W2 provenance as grandfathered.
- Suggested fix: Replace date-only grandfathering with an explicit allowlist of known legacy `(file, family, task_id, body_hash)` tuples, or require committee_dispatch for every stamp except exact known legacy reconcile files. Keep the existing `DELIB-RECONCILE` compatibility by allowlisting that artifact, not by trusting arbitrary old dates.

### B5-1 — RESULT enum validation is split into `template_check result`, but the claim checker accepts invalid RESULT fields

- File: `scripts/verification_claim_check.py:506-542`; `scripts/template_check.sh:76-99`
- Status: BLOCKING
- Attack surface: Task 5.1 RESULT hard fields
- Evidence: P5-1 says the checker reads structured RESULT fields. `verification_claim_check.py` only checks `RUNTIME_CHECK=PASS` with empty receipts and `MUTATION_CHECK=NOT_RUN` with operational claims. It does not reject enum values outside `NOT_RUN|PASS|FAIL|N/A:*`, missing required fields, or malformed `RECEIPTS`.
- Reproduced:
  ```bash
  printf 'STATIC_CHECK=NOT_RUN\nRUNTIME_CHECK=ok\nMUTATION_CHECK=PASS\nRECEIPTS=["r1"]\nOPEN_PENDING=[]\n' > /tmp/bad-RESULT.md
  venv/bin/python scripts/verification_claim_check.py --files /tmp/bad-RESULT.md
  # observed: rc=0
  bash scripts/template_check.sh result /tmp/bad-RESULT.md
  # observed: rc=1
  ```
- Why this matters: `gate_check.sh` only gates new `docs/*SPEC|TODO|PLAN*.md`. RESULT handoffs are not forced through `template_check result`, so relying on a separate template command leaves the normal claim-check path fail-open for malformed RESULT files.
- Suggested fix: Move required-field and enum validation into `check_result_structured_fields()`, or make the hook/checker path explicitly invoke `template_check.sh result` for `*-RESULT.md`. Prefer the first so RESULT semantics live in the claim checker that already scans handoffs.

### B5-2 — #6 fingerprint conflict test uses a self-oracle; real parsed green/red lines do not collide

- File: `scripts/verification_claim_check.py:457-463`, `scripts/verification_claim_check.py:443-450`, `tests/governance/test_verify_gate_b5.py:138-177`
- Status: BLOCKING
- Attack surface: Task 5.2 fingerprint conflict, test teeth
- Evidence: `claim_fingerprint()` includes `claim.source_line_text`, and `extract_claim()` sets `source_line_text=unit.text.strip()`. Real green and red records naturally differ by `VERIFY/PASS` vs `FAIL/紅燈`, so they hash differently. The test bypasses this by manually constructing both `ClaimObject`s with identical `source_line_text=shared_line`.
- Reproduced through parser:
  ```text
  "- tests/x.py::test_mutation_align mutation P0-FF-3 已驗 PASS VERIFY:good-receipt"
    -> fp 3820334a...
  "- tests/x.py::test_mutation_align mutation P0-FF-3 FAIL 紅燈"
    -> fp 1f3dd618...
  ```
- Counterexample: A stale green VERIFY claim and a later red FAIL claim for the same node/task do not produce the same fingerprint, so the stale green is not blocked for missing `SUPERSEDED`.
- Suggested fix: Derive fingerprint from canonical subject terms, not raw status text. Strip `VERIFY:*`, `SUPERSEDED:*`, receipt ids, pass/fail/red/green polarity words, and summary counts before fingerprinting, or use `(normalized scope, runtime_expectation, task_id)` for #6 v1. Add an integration test that runs `verification_claim_check.py --files green.md red.md` against actual markdown files instead of hand-built `ClaimObject`s.

### B5-3 — FACT-RECEIPT misses command-output facts

- File: `scripts/template_check.sh:53-67`
- Status: BLOCKING
- Attack surface: Task 5.3 W1 FACT-RECEIPT
- Evidence: P5-3 requires FACT-RECEIPT for `§A「已確認」` facts involving data structure/type/command output. The implementation only matches data-structure tokens such as `DatetimeIndex`, `dtype`, `DataFrame`, `raw_data`, `形狀`, `型別`, `單位`. It misses command-output claims.
- Reproduced:
  ```bash
  # §A line: "- 已確認: pytest tests/governance/test_verify_gate.py -q 輸出 49 passed"
  bash scripts/template_check.sh spec /tmp/BAD_SPEC.md
  # observed: TEMPLATE PASS, rc=0
  ```
- Counterexample: A SPEC can state a concrete command result as confirmed without `FACT-RECEIPT`, which is the exact class of verification-fidelity failure this gate is meant to prevent.
- Suggested fix: Include command-output vocabulary and tokens in the W1 predicate: `pytest`, `npm`, `bash`, `python`, `exit`, `rc=`, `stdout`, `stderr`, `輸出`, `印出`, `passed`, `failed`, `sha256`, file sizes, and similar command-result markers. Add a regression test for a command-output `已確認` line without FACT-RECEIPT.

### B4-3 — Fake B4 mutation receipts are present in real trust artifact locations

- File/artifacts: `.claude/gate/verify_audit.log`; `handoffs/run_receipts/20260701T224757Z-mutation-test_b4_green.*`, `20260701T224758Z-mutation-test_b4_green.*`, `20260701T224758Z-mutation-test_b4_red.*`, `20260701T224759Z-mutation-test_b4_red.*`
- Status: BLOCKING before commit
- Attack surface: known疑點 #9, trust artifact hygiene
- Evidence: `git status --short` shows the fixture receipts as untracked, and `.claude/gate/verify_audit.log` contains four real receipt events for `mutation-test_b4_green/red`. These are synthetic test fixtures, but they live in the real receipt/audit locations intended to back operational claims.
- Decision: Not acceptable as commit residue. The B4 tests now use isolated env paths, but the current worktree still contains fake trust artifacts from development.
- Suggested fix: Remove the fixture receipt files and remove the matching synthetic receipt events from the real verify audit before landing, or move any intended fixture evidence under a non-trust test fixture directory. Do not commit these as real verification receipts.

## NON-BLOCKING Findings / Boundaries

### NB-1 — `verify_audit_chain.py` is correctly non-blocking, but its honest boundary should stay explicit

- File: `scripts/verify_audit_chain.py:72-104`
- Status: NON-BLOCKING
- Attack surface: Task 4.4 audit chain
- Assessment: This script detects mismatches between audit event hashes and current receipt/log files. It can be bypassed by changing both the receipt/log and the audit event together. That matches the stated honest boundary: tamper-evident for accidental/local drift, not malicious forgery, and P4-4 explicitly says it is a human audit helper, not fail-closed enforcement.
- Suggested fix: Keep the current exit-0 behavior, but document in the B4 handoff or script help that the tool does not anchor audit events to git history or signatures.

### NB-2 — `mutation_probe_check.sh` receipt wrapping preserves PASS/FAIL direction in covered cases

- File: `scripts/mutation_probe_check.sh:73-106`
- Status: PASS with caveat
- Attack surface: Task 4.1 behavior preservation
- Assessment: The receipt wrapper preserves pytest rc handling: nonzero rc still produces `MUTATION-PROBE FAIL`; zero rc with zero passed still fails; positive passed count passes. Receipt creation failure via `run_with_receipt.py` would make the wrapper command nonzero, so it does not silently turn red into green.
- Caveat: The added `mutation_receipt=` line is appended to `.claude/gate/audit.log` via `VERIFY_GATE_COMMITTEE_AUDIT_LOG`, not `.claude/gate/verify_audit.log`; this is extra traceability, not the canonical receipt event. The canonical event still comes from `run_with_receipt.py`.

## Required Attack Surface Matrix

1. Task4.1 behavior unchanged: PASS with caveat. Covered green/red direction is preserved.
2. Task4.2/4.3 provenance forgery: BLOCKING. Non-ADV adversarial bypass and backdated grandfather stamp bypass.
3. Task4.4 audit chain: NON-BLOCKING/PASS within stated honest boundary; not malicious-forgery proof.
4. Task5.1 enum fields: BLOCKING. Claim checker accepts invalid RESULT enum unless a separate template command is manually run.
5. Task5.2 fingerprint conflict: BLOCKING. Natural green/red parsed records do not collide; test is self-oracle.
6. Task5.3 FACT-RECEIPT: BLOCKING. Command-output confirmed facts are not covered.
7. Test teeth: BLOCKING for B5 #6; B4 provenance tests miss the non-ADV default branch and grandfather backdating.
8. Existing flow regression: partial. Reported 49 passed is useful, but not sufficient for the bypasses above because the failing branches are untested.
9. Known fixture residue: BLOCKING before commit. Synthetic mutation-test_b4 receipts should not remain in real trust artifact paths.

## Tests / Probes Run

```bash
git diff -- scripts/gate.sh scripts/mutation_probe_check.sh scripts/reconcile_stamps_check.sh scripts/template_check.sh scripts/verification_claim_check.py
sed -n ... scripts/verify_audit_chain.py scripts/verify_task_provenance.py templates/RESULT_TEMPLATE.md
sed -n ... tests/governance/test_verify_gate_b4.py tests/governance/test_verify_gate_b5.py
rg -n "Task 4\\.|Task 5\\.|P4|P5|W1|W2|W3|RESULT|FACT-RECEIPT|fingerprint|SUPERSEDED|waived" docs/VERIFY_GATE_TODO.md docs/VERIFY_GATE_SPEC.md
venv/bin/python scripts/verification_claim_check.py --files /tmp/bad-RESULT.md
bash scripts/template_check.sh result /tmp/bad-RESULT.md
venv/bin/python - <<'PY'  # imported verification_claim_check.py and compared parser-derived fingerprints
...
PY
bash scripts/template_check.sh spec /tmp/BAD_SPEC.md
tail -30 .claude/gate/verify_audit.log
ls handoffs/run_receipts/*mutation-test_b4*
```

Observed outcomes:
- Invalid RESULT enum: claim checker rc=0, template_check rc=1.
- Parser-derived #6 fingerprints differ for same task/node green vs red natural lines.
- Command-output `已確認` without FACT-RECEIPT passed template_check.
- Real trust artifact paths contain four synthetic `mutation-test_b4_*` receipts and audit events.

## ASSUMPTIONS_VERIFIED

- P4-2/P4-3/P5-1/P5-2/P5-3 requirements were read from `docs/VERIFY_GATE_SPEC.md` and `docs/VERIFY_GATE_TODO.md`.
- `gate.sh` provenance is conditional on ADV path pattern instead of rejecting non-matching paths.
- `verification_claim_check.py` does not validate RESULT enum values or required field presence.
- `claim_fingerprint()` uses raw `source_line_text`, and the real parser sets that field from the whole unit text.
- `template_check.sh spec` currently misses command-output confirmed facts.

## TESTS_RUN

- See "Tests / Probes Run" above. These were read-only probes except one `gate.sh` adversarial bypass probe; its generated audit/token side effects were reverted immediately to the prior state.

## FAILURES_SEEN

- none in product tests. Review found blocking bypasses.

## SCOPE_CHANGES

- none. No implementation files changed by this review. Only this review handoff was added.

## NUMERIC_OR_SCHEMA_IMPACT

- none from this review.

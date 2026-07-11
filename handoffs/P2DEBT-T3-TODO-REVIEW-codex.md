# p2debt-t3 TODO R1 — Codex adversarial review

- Reviewed: `P2DEBT-T3-TODO-DRAFT-R1.md` against frozen `P2DEBT-T3-SPEC-DRAFT-R4.md`; grok TODO review was not read.
- SPEC authority receipt: `P2DEBT-T3-SPEC-REVERIFY-R4-codex.md` contains `RECONCILE-STAMP APPROVED (p2debt-t3 SPEC R4, codex, 2026-07-11)`.
- Coverage: all 11 diagnostics map one-to-one to Tasks 1.1–1.5 and the prescribed test-only fixes; Gate A/B/C, five-file scope whitelist, `comm -13`, and 31-test/87-expect distinctions are present.
- Read-only receipt 1: `venv/bin/python` inspected named source lines. Files and diagnostic anchors exist; examples: lifecycle L42/L88, panel L22/L102/L170, batchDate L55/L61/L75, store L19/L429/L539.
- Read-only receipt 2: `venv/bin/python` evaluated Gate A corpus: five files exist, normal forbidden hits=0, synthetic `@ts-ignore` hits=1, bogus path exists=False. This supports the specified 1/0/2 polarity logic but is not an `rg` rc claim.
- Read-only receipt 3: `venv/bin/python` counted `expect(` per file as 20/10/4/9/44, total 87; set-difference simulation produced exactly the five whitelisted paths for good post state and zero paths for unchanged bad state.
- DELEGATED: exact native `npx tsc`/`rg` spot-runs produced no output within 60s in the Codex sandbox and were terminated; no native rc or tsc result is claimed.

## Blocking findings

1. Exit contracts are not fail-closed. Batch Gate runs `cd frontend` twice in one block (TODO L75 then L77); Final Acceptance repeats it (L413 then L416). When copied as a block, the second command targets `frontend/frontend`, so vitest/counting does not run as claimed.
2. Final §1 stores `tsc_rc` but never asserts it. Its `npx tsc ... | grep -c` also masks the compiler rc; on the desired zero-match result, `grep -c` prints `0` but returns 1. Task-level `tsc | rg[-c]` pipelines have the same producer masking/zero-match ambiguity.
3. Gate B (`rg -c ... | awk`), Gate C (`rg -c ... | sort` and `rg -N ... | sort`), scope (`git status | awk | sort`, especially `comm -13 ... | sort`), and §5 (`grep | wc -l`) return the final consumer's rc. Producer error rc=2/nonzero can therefore be masked. Gate A is correctly tri-state, but the other gates do not inherit that protection automatically.
4. Final Acceptance §3–§4 are comments pointing elsewhere, not an executable aggregate contract; without `set -e`/explicit rc assertions, a later success can mask earlier failure. Each producer must be run once, its rc asserted, then its captured output counted/sorted/diffed; the aggregate must exit nonzero on any failed leg.
5. Target-line precision is false for Task 1.5.1: TODO says the first mock is L43–45, but current file has `vi.fn(async () => ...)` at L39–41; L43 is blank. The second mock is correctly at L61–63. Update the exact location while retaining diagnostic anchors L55/L75.

## Required closure

- Rewrite Batch/Final commands with one working-directory transition and explicit assertions for tsc, vitest, Gates A/B/C, scope, and decoupling; remove every chained producer-mask path above.
- Preserve the exact 11-error fixes, five-file whitelist, pre-dirty `comm -13` model, Gate A tri-state semantics, and per-file 20/10/4/9/44 baselines; correct Task 1.5.1's line anchor.

Verdict: BLOCK — acceptance commands can mask failures / skip vitest, and one target line is not real

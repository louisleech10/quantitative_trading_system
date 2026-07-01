# VERIFY_GATE_SPEC adversarial review — Codex

VERDICT: CHANGES-REQUESTED — 修補方向正確,但目前 SPEC v1 仍可被偽造 receipt、停用 hook、濫用豁免、錯標 runtime_class、繞過 pending ledger；不可直接派實作。

## Scope read
- Read: `docs/VERIFY_GATE_SPEC.md`, `docs/VERIFY_GATE_BRIEF.md`, `handoffs/20260701-FF-FORENSICS-RECONCILE.md` §3.
- Read existing mechanisms: `scripts/gate_check.sh`, `scripts/mutation_probe_check.sh`, `scripts/gate.sh`.
- Review stance: attack surface first; no code changes proposed as implemented.

## Findings

### BLOCK-1 — Receipt is self-attested; sha fields do not prove the command actually ran
Spec refs: `VERIFY_GATE_SPEC.md` P1/P2 lines 31-42.

Counterexample: create `handoffs/run_receipts/20260701-x.json` by hand with `exit_code=0`, `runtime_class=mutation_runtime`, `passed=2`, `failed=0`, `command=["python","-m","pytest","tests/feature_engineering/test_ff_multitf_truncation_mr.py","-k","test_mutation_"]`, then create a matching `.log` and matching `stdout_sha256/log_sha256`. The checker only verifies the receipt is internally consistent with its own log path. It cannot distinguish a real `run_with_receipt.py` subprocess run from a hand-written receipt.

Why this breaks the goal: the target claim is "no real run-log receipt, no claim". A forged receipt is still accepted if hashes match. Existing `gate.sh` also writes plain token files in `.claude/gate` without cryptographic protection, so the current repo pattern does not prevent self-issued artifacts.

Required property: receipt must carry a non-forgeable or at least hard-to-handwrite provenance signal. Minimal v1 option: checker only accepts receipts whose `receipt_id` is referenced in an append-only audit event emitted by `run_with_receipt.py`, with matching receipt sha, log sha, git head, command sha, and no dirty mutation after receipt before commit. Stronger option: store receipt files outside hand-edit paths or sign with a local secret outside repo. Without this, fake receipt is a direct bypass.

### BLOCK-2 — Hook enforcement can be silently absent or disabled
Spec refs: P3 lines 51-54, §R lines 72-75. Existing `gate_check.sh` fails open when `jq` is missing and only guards Task/Bash/Write tool channels.

Counterexample A: do not run `scripts/install_verify_hooks.sh`; commit a handoff with `已驗 ✅` and no `VERIFY:`. Nothing in current `gate_check.sh` guards `git commit`.

Counterexample B: run `git config --unset core.hooksPath` or `git commit --no-verify`. The SPEC explicitly documents uninstall as normal rollback, but has no postflight / CI / gate check that fails when hooks are missing. The incident root cause was skipped gate; v1 repeats the same trust assumption at install/enforcement time.

Counterexample C: if implementation follows `.git/hooks` instead of repo-tracked `scripts/git_hooks`, hooks are not versioned and will not exist in other clones.

Required property: add an independent verifier outside git hooks, e.g. `scripts/verify_hooks_health.sh` checked by preflight/postflight/CI and by `gate.sh dispatch --spec` path before implementation/merge. It must assert `core.hooksPath=scripts/git_hooks`, expected hook files exist, are executable, and contain a stable checker invocation. Also add explicit tests for `--no-verify` residual risk or require CI to run `verification_claim_check.py` over the merge diff.

### BLOCK-3 — `VERIFY-EXEMPT` and `claim-context: discussion` are broad enough to launder new claims
Spec refs: P2 line 44, V7 line 68, boundary line 70.

Counterexample: add a new handoff paragraph:

`# VERIFY-EXEMPT: operational note`
`P0-FF-3 align mutation 真紅,多 TF 無 look-ahead 已驗通過。`

Or wrap a new status update in `<!-- claim-context: discussion -->` and write the same claim as "事故討論". The checker spec does not require an allowlist of files, authoring contexts, ticket state, or exemption IDs. V7 even says a fake claim with exemption should pass.

Why this breaks the goal: the easiest bypass is not Unicode; it is a sanctioned bypass marker with any non-empty reason. The mechanism will train authors to slap exempt tags on blocked claims.

Required property: exemptions must be fail-closed and auditable: require `VERIFY-EXEMPT:<category>:<issue-or-review-id>` with a narrow category allowlist, block exemption in `HANDOFF.md`, commit messages, and task result sections, and emit a separate violation/warning that CI or reviewer must acknowledge. `claim-context: discussion` should only suppress quotes inside fenced evidence blocks or files under an allowlisted forensic-review pattern, not arbitrary new operational handoffs.

### BLOCK-4 — Pending ledger is underspecified and race-prone; it cannot reliably bind "open" to later "DONE"
Spec refs: P2-2 lines 46-49, V6 line 67.

Counterexample A: an execution result says "slow align left for Claude" but uses wording not matching `留 X 驗` or `RUNTIME_*: NOT_RUN`, e.g. `deferred to orchestrator`, `manual validation pending`, or English `NOT EXECUTED`. No ledger row opens.

Counterexample B: append a forged `closed` row for the same `task_id` with a passing helper receipt. The spec says append-only but not who may append, how the checker derives the latest state, or how it validates claim identity.

Counterexample C: open pending says `claim="align mutation slow runtime"`; later receipt closes `task_id` with any `exit==0,class=mutation_runtime` for a different test file. The spec does not require claim fingerprint, node-id, marker, command pattern, or source handoff reference equality.

Counterexample D: two parallel agents append open/closed rows for same task; checker uses "same task_id has open not closed" but no deterministic state machine order, unique pending_id, or stale-closed handling. A closed row can close the wrong open row.

Required property: ledger needs `pending_id`, `claim_fingerprint`, `source_file`, `source_line`, `required_runtime_class`, `required_node_ids/markers`, `opened_by_receipt_or_result_sha`, monotonic event ordering, and close validation against that exact pending_id. The checker must compute unresolved pending by reducing events, not by task_id string alone.

### BLOCK-5 — Runtime class is supplied by the caller and can be mislabeled
Spec refs: P1 line 29, P2 line 42, line 43.

Counterexample: run `run_with_receipt.py --runtime-class mutation_runtime -- python -c "print('2 passed')"` or `pytest tests/smoke.py -q`, then claim `mutation runtime 真紅 VERIFY:<id>`. If parsing is loose and class is caller-provided, the checker sees class `mutation_runtime` and maybe `passed=2`. Even if node-id matching exists, a fake command path can be named like the target unless selected node IDs are authoritative.

Mislabel risk: `requires_kline_runtime` can be declared for a quick unit test; `static_only` can be declared for an actual runtime. The SPEC says duration <5s is only WARN, so the primary protection is a free-form label.

Required property: `runtime_class` must be derived, not trusted. For pytest, derive from command, markers, selected node ids, test metadata, and maybe an allowlist mapping. For mutation runtime, require `-k test_mutation_` plus selected node ids beginning with `test_mutation_` and nonzero pass/fail/failed count. For `requires_kline_runtime`, require `requires_kline` marker selected or explicit allowlist. User-provided class can be a requested class, not the authoritative class.

### MAJOR-1 — Claim vocabulary is easy to evade with synonyms, spacing, casing, and Unicode
Spec refs: P2 line 40.

Counterexamples:
- Chinese synonyms: `驗完`, `實測`, `跑完`, `已跑`, `確認`, `證實`, `無洩漏`, `無未來函數`, `因果性 OK`, `可上量化`, `signoff`, `綠燈`, `全綠`, `收斂`, `核可`.
- English variants: `PASS`, `Passed`, `green`, `validated`, `verified`, `runtime ok`, `no leakage`, `causality clean`, `lookahead-free`, `look ahead free`.
- Unicode/spacing: `p\u200bass\u200bed`, `已 驗`, `真　紅`, `look‑ahead` with non-ASCII hyphen, `無 look ahead`.
- Decomposition: `已經跑過；結果是綠的` split across two lines, or `mutation` in one sentence and `PASS` in next sentence.

Required property: normalize Unicode (NFKC), strip zero-width chars, normalize hyphens/spaces/case, and scan paragraph-level semantic patterns, not only literal tokens. Add a "suspicious verification language without VERIFY" warning mode for unknown variants so reviewers can update the dictionary.

### MAJOR-2 — "same paragraph/line" binding can attach a receipt to the wrong claim
Spec refs: P2 line 41.

Counterexample: one paragraph contains:

`center mutation 真紅 VERIFY:center-receipt; align mutation 真紅; 4h/12h 無 look-ahead。`

The single receipt supports one claim but visually launders adjacent unsupported claims. The SPEC does not require one receipt per claim, nor does it define paragraph splitting in Markdown lists, tables, blockquotes, or commit bodies.

Required property: each detected claim should produce a claim object with polarity, scope terms, runtime terms, and nearby receipt IDs. A receipt can satisfy only claims whose extracted scope intersects its command/node ids/markers. Unsupported claims in the same paragraph must still fail.

### MAJOR-3 — Receipt schema has an internal mismatch: checker requires `log_sha256`, P1 does not produce it
Spec refs: P1 line 32 vs P2 line 42.

Counterexample: implement P1 literally: fields include `stdout_sha256`, `stderr_sha256`, `log_path`, but no `log_sha256`. Implement P2 literally: require `log_sha256`. Either all receipts fail, or implementer silently weakens log verification.

Required property: schema must include `log_sha256` explicitly and V1 must assert it. Also clarify whether stdout/stderr are separate files or combined terminal log; current P1 says log全文 plus stdout/stderr sha but does not define exact byte stream boundaries.

### MAJOR-4 — Commit-msg scanning cannot resolve receipt files for untracked receipts
Spec refs: P1 lines 31-35, P3 line 53.

Counterexample: generate a real receipt under `handoffs/run_receipts/`, write commit message `runtime PASS VERIFY:<id>`, but do not stage the receipt/log. The local checker can pass because files exist in worktree; the commit in repo contains a permanent claim whose supporting receipt is absent from Git history.

Required property: pre-commit must require every referenced receipt/log to be staged in the same commit or already tracked at the referenced git object. Commit-msg hook alone cannot guarantee this after staging changes. Add test: commit message references untracked receipt -> reject.

### MAJOR-5 — §V mutation tests are mostly meta-assertions, not real mutation testing
Spec refs: V2/V4 lines 63-65.

Weakness: "remove blocking line -> test fails" is a narrative requirement, not an executable test unless the implementation includes a mutation harness that patches checker code. The planned `tests/governance/test_verify_gate.py` can prove examples pass/fail, but it will not prove individual guard clauses have teeth against common rewrites.

Concrete missing falsifiers:
- forged receipt with matching hashes should fail;
- receipt class mislabeled by caller should fail;
- same paragraph with one valid receipt and two unsupported claims should fail;
- `VERIFY-EXEMPT` in root `HANDOFF.md` should fail or at least not silently pass;
- commit with hooks not installed should be detected by health check;
- untracked receipt referenced by commit message should fail;
- Unicode/zero-width synonym claim should fail or warn.

### MAJOR-6 — v1 omits root HANDOFF generated index even though stale-claim resurrection is one of the incident causes
Spec refs: forensics §3 item 6 says generated root index; SPEC §A line 12 says root generation deferred.

Counterexample: root `HANDOFF.md` keeps an old `已驗 ✅ VERIFY:<old receipt>` claim and later appends a red-light superseding note elsewhere. The checker sees a valid old receipt and passes both. It does not understand "same assertion now superseded".

Impact: this does not block v1 entirely if acknowledged, but the SPEC currently claims "no false claim enters HANDOFF" while explicitly deferring the only state-machine component that prevents old claims from reviving.

Required property for v1: at minimum, root `HANDOFF.md` must be checked for stale/superseded claim conflicts or forbidden from carrying receipt-backed final claims except as generated summaries. If not, state the residual risk as an explicit N/A with follow-up blocker before using the gate as incident closure.

### MINOR-1 — Existing gate fail-open behavior should be named as residual risk
Existing `gate_check.sh` exits 0 when `jq` is missing or JSON parse fails. This is acceptable for avoiding lockout, but a new "fail-closed governance" narrative should not imply current hooks are fail-closed in all environments. SPEC should require a health check for `jq` or avoid jq in critical enforcement paths.

### MINOR-2 — `passed` token is too broad for docs and commit messages
Spec refs: P2 line 40.

Counterexample: architecture doc says "data passed through layer 6.5" or "passed to subprocess". Unless "handoff/commit narrative" is precisely scoped, false positives will push authors toward `VERIFY-EXEMPT`, increasing the bypass surface.

### MINOR-3 — P4 "behavior unchanged" needs a fixture that exercises failing path and rc passthrough
Spec refs: P4 line 58, V8 line 69.

Current `mutation_probe_check.sh` captures pytest output into a variable, prints only tail, and derives `passed_count` by grep. Wrapping it with `run_with_receipt.py` may change buffering, stdout/stderr ordering, signal/timeout behavior, and tail visibility. V8 should assert stdout contains current PASS/FAIL sentinel lines and that failing pytest rc still produces receipt before exit.

## Bottom line
I agree with the forensic attribution and the repair direction: adding run receipts, claim checking, commit hooks, and a pending ledger is the right class of fix. I do not agree that the current SPEC is implementable as a reliable gate without tightening the attack surfaces above. The top three blockers are forged receipts, hook absence/disablement, and broad exemptions; any one of them preserves the original failure mode under a new name.

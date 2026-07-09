Task: ic1a-align-b2-golden-rca
Status: DONE
Doing: completed read-only RCA for B2 golden drift.
Output: handoffs/IC1A-ALIGN-B2-GOLDEN-RCA-codex.md
Decision: root cause is B2 stage2 forced float64 close conversion changing log-return label payload.
Evidence: old-stage2-only in-memory diagnostic restored removed counts to baseline; old-stage3-only did not.
Evidence: dtype probe showed DatetimeIndex rewrite with original float32 gives maxdiff 0; forced float64 gives ~5.96e-08 label diffs.
Todo: fix stage2 to preserve raw close dtype while normalizing index, then rerun golden.
Blocked: none.
Pitfall: golden/service path writes data_cache through pre-existing _persist_outputs unless monkeypatched/no-op redirected.
Verdict: FIX-CODE

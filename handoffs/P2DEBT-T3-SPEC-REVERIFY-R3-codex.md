# P2DEBT-T3 SPEC R3 re-verification — Codex

- task-id: `p2debt-t3`; target: `handoffs/P2DEBT-T3-SPEC-DRAFT-R3.md`; date: 2026-07-11.
- 正在做：R3 單點覆核完成；未改 repo 其他檔案，未碰 `data_cache/`。
- FACT-RECEIPT: current-tree Gate A exact scan+`wc -l` → `0`（Codex 實跑 2026-07-11）。
- FACT-RECEIPT: current-tree Gate B exact per-file `rg -c` → `9+4+44+10+20=87`（Codex 實跑 2026-07-11）。
- FACT-RECEIPT: Gate C `/tmp` counterexample, baseline `10`; legal non-expect insertion `10`; count diff rc=`0`。
- FACT-RECEIPT: Gate C count-changing variant `11`; count diff rc=`1`；Leg 2 body diff rc=`1`。
- FACT-RECEIPT: Gate C legal insertion Leg 2 `rg -N` body diff rc=`0`。
- DELEGATED note: first combined shell-pipeline probe produced no output for 60s and was terminated; no result claimed from it. Temp fixtures were then generated in `/tmp`, followed by direct `rg`/`diff` commands above.
- FACT-RECEIPT: R2→R3 `diff -u` shows only revision title/status metadata, §V Gate C/chair receipt, and R3 closure changed; task scope/phases/acceptance otherwise unchanged.
- FACT-RECEIPT: scope-gate synthetic current-tree replay → pre-dirty `22`, delta `5`, whitelist diff rc=`0`。
- 本次決策：Gate C false-reject finding is CLOSED; legal line-number shifts pass, unauthorized per-file count changes fail, and amendment-note handling is stated.
- 阻塞：prior Codex R2 finding on Gate A fail-closed behavior remains open. R3 still uses `rg ... | wc -l` without `set -o pipefail` or explicit `rg` rc handling; an `rg` execution/read error can be misreported as `0`.
- 待辦：make Gate A fail closed by checking `rg` rc (`0`/`1` accepted as searched; `>1` fails) or an equivalent explicit error check, then reverify.
- 踩坑提醒：a successful current-tree Gate A receipt proves the normal path only; it does not close the error-path false-zero finding.
- NUMERIC_OR_SCHEMA_IMPACT: none.

Verdict: BLOCK — Gate C is closed, but the previously recorded Gate A fail-open finding remains unresolved

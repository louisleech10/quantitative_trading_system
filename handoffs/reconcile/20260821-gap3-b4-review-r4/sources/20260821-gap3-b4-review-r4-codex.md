# GAP-3 B4 code review R4 — codex
task-id: 20260821-GAP3-B4-REVIEW-R4

## Verdict: 可進 stamp
CODEX-R3-P1-01: CLOSED；本輪新增 findings: 0。

## CODEX-R4-P3-00

**斷言**: 本輪逐項核對後無 finding；R3 修補以 `(candidate_id, evaluation_id)` 對帳，孤兒 `a:eval-a` 不被吞，任一帳本 evaluation 缺 provenance 時 `run_dsr_pbo` fail-closed。`_read_ledger_pairs` 僅供對帳、不產 N，且沿用同一 schema 判準，未發現本輪修補引入的實質問題。

**碼證**: `candidate_ledger.py:286-313,372-381`；`venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k sidecar_first` → `1 passed`, rc=0，測試斷言 `a:eval-a` 仍列出、`b:eval-b` 缺 provenance 即 `provenance_incomplete`；B4 Gate → `29 passed, 195 deselected`, rc=0。

**來源摘要**: `momentum/Analysis/event_samples/candidate_ledger.py#dae0cf45a712`; `tests/momentum/event_samples/test_candidate_ledger.py#ab83ff44a969`; `handoffs/20260821-gap3-b4-review-r4-brief.md#3b71ddc12d2c`

正文：信心度=High。直接讀帳本檔的疑慮已逐碼核對：此路徑只產 evaluation pair 對帳資料，N 仍唯一由 `read_trial_ledger` 提供，且 `_row_is_valid`／contract 判準一致；本輪不列 finding。

ASSUMPTIONS_VERIFIED: R3 修補 diff 僅 `candidate_ledger.py` 與其測試；R3 反例與 B4 Gate 實跑 rc=0；未重跑 golden。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k sidecar_first` → 1 passed, rc=0；`venv/bin/python -m pytest tests/momentum/event_samples/ -q -k 'pattern_bridge or candidate_ledger'` → 29 passed, rc=0。
FAILURES_SEEN: none。
SCOPE_CHANGES: 僅新增本交件檔；未改程式、測試、SPEC/TODO、HANDOFF.md；`/tmp` 無 workdir，無 `claude-501` 可保留。
NUMERIC_OR_SCHEMA_IMPACT: none。
OUTPUT_ARTIFACT: `handoffs/20260821-gap3-b4-review-r4-codex.md`。
STATUS: DONE

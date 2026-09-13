# SPLITUNIFY b9 review-r19：codex
## CODEX-R19-P1-01
**斷言**: SPEC 現行 §P Task 9.1 仍要求多 symbol 相加與 `metadata.split_unify` 三層交付，但 TODO、程式與測試已定案為批次字典原樣傳遞、producer→summary 兩層，契約仍互相矛盾。
**碼證**: VERIFY: `nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '176,186p'` 顯示舊字面；`nl -ba docs/SPLITUNIFY_TODO.md | sed -n '438,457p'` 顯示新字面；94-test 與 multi-symbol assertion 均通過。
CODE-ANCHOR: momentum/Analysis/event_samples/pipeline.py:754
MUTATION: 暫存副本把 `split_projection.py:693-696` 的 forwarding 改為按 symbol 對同一字典加總，重跑 `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py::test_multi_symbol_branch_carries_discarded_rows_verbatim` 應紅。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#8c40a92f3556
[BLOCKING] 信心度=High；SPEC 是權威來源，下一輪實作者可依 §P 引入 double-count 或錯把 metadata 當本批交付。最小修法是把 SPEC 現行 §P Task 9.1 同步至 TODO／現行 code，保留 metadata 為 §N 殘留；可行性由上述 94 passed、multi-symbol 值相等與防放大測試證明。
1a: `CODEX-R18-P1-01`、`P1-02`、`P1-03`、`P2-01`、`P3-02` 全部 CLOSED。
1b: `venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` → rc=0；A/B/C/D 分別 NO_RAISE、RAISED、NO_RAISE、RAISED，C=`discarded={'4h': 2}`。指定 pytest → 94 passed。r18 的 Wiring、NaN、Mapping、防 stale docstring 反例均由此重跑閉合。
2a: 無第二條 production path；全 repo 呼叫掃描只有 `pipeline.py:750`，另三處為 `scripts/freeze_splitunify_golden.py:163,252,268` 的 golden 工具，不是 runtime caller。
2b: N/A；無第二 production path 阻擋。工具路徑不接 `build_event_keys` producer，optional discarded 預設 `{}` 不改本輪契約。
3a: 不會混入值 0 偽項。`venv/bin/python /tmp/splitunify_r19_categorical_probe.py` → unordered/ordered Categorical 均 `{'4h': 1}`，StringDtype `{'4h': 1}`，Categorical `pd.NA` → ValueError 缺值。
3b: 最小修法不需要；已試 Categorical ordered=False/True（含未使用 `12h`）、StringDtype，並以既有 object/None 測試確認缺值 fail-closed。
4a: 不能進 B9B；唯一 blocking 是 SPEC §P 與 TODO/code 的契約漂移，不是程式行為或測試缺口。
4b: 最小閉合集合：同步 SPEC 現行 Task 9.1 的 multi-symbol 原樣傳遞、兩層交付字面；不重開 9.2–9.5。
ASSUMPTIONS_VERIFIED: SPEC stamp check rc=0；runtime caller 掃描、Categorical 邊界、兩種 TF 順序均實跑；順序探針兩次均 `discarded={'4h': 4}`。
TESTS_RUN: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → 94 passed/0 failed/rc=0；probe rc=0；Categorical probe rc=0；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0。
FAILURES_SEEN: none in closure checks；新增 finding 是現行 SPEC/TODO 字面衝突。
SCOPE_CHANGES: none；只新增本交件檔，未改 production code、測試、SPEC、TODO、HANDOFF.md 或 data_cache/。
NUMERIC_OR_SCHEMA_IMPACT: 審查未改輸出；確認現行 discarded tuple、13-key summary 與 batch-level verbatim semantics。
OUTPUT_ARTIFACT: handoffs/20260911-splitunify-b9-review-r19-codex.md
VERDICT: blocked
BLOCKED-BY: CODEX-R19-P1-01
CLOSED: CODEX-R18-P1-01,CODEX-R18-P1-02,CODEX-R18-P1-03,CODEX-R18-P2-01,CODEX-R18-P3-02

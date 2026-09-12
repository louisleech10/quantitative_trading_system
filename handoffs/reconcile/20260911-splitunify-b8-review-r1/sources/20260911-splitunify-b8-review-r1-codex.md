# SPLITUNIFY b8 審碼 R1 — codex
task-id: 20260911-SPLITUNIFY-B8-REVIEW-R1; findings-round: R1
## CODEX-R1-P1-01
**斷言**：D-001-C2 §4.8 要求 producer 對 `row_index_local` 的 numpy integer dtype 先 fail-closed；`split_per_symbol` 與 adapter 卻先轉 `int`，可靜默救活／截斷非法 ordinal。
**碼證**：`contracts.py:741-750`、`ic_split_adapter.py:64-69,232-237` 在 attest (`contracts.py:802-809`、`ic_split_adapter.py:281-288`) 前 cast；實跑 float64 `[0.0,1.0]` 均 `NO_RAISE` 並產出 `int64 [0,1]`。
**來源摘要**: momentum/core/contracts.py#9c81df6c2808; momentum/Analysis/ic_split_adapter.py#a3da0c9b8555; docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f
[P1/high] 失效：錯誤 splitter 可把非整數座標映到錯列而不報錯；修法：原始 `np.asarray` 先獨立 dtype gate，通過後才轉 int/index；可行性：局部 producer 修補並各加 float/bool/object route test。
## CODEX-R1-P1-02
**斷言**：SPEC §5 明定 `NaT` fail-closed；兩 producer 只對被選列呼叫 epoch 正規化，未選 `NaT` 可進入有效 SplitPlan。
**碼證**：`contracts.py:732,758-762`、`ic_split_adapter.py:184-188,239-243` 只驗 selected rows；`validate_split_integrity:625-655` 無全域 NaT guard 且空列可在 guard 前 return；實跑含未選 `NaT` 的 frame 兩 producer 均 `NO_RAISE`。
**來源摘要**: momentum/core/contracts.py#9c81df6c2808; momentum/Analysis/ic_split_adapter.py#a3da0c9b8555; docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f
[P1/high] 失效：含缺時刻的 base universe 可被當成 rows-purge 有效資料；修法：producer 建 plan 前對完整 canonical time axis 做 NaT 檢查（orchestrator 已由 `:285-286` 擋）；可行性：局部前置 gate，不動 schema。
## CODEX-R1-P2-03
**斷言**：D-001-C2 §4.10–4.11 要求 projection 文件使用 local 座標；`_derive_single_symbol` docstring 仍以全框 `test_plan.row_index[0]` 描述測試起點。
**碼證**：`momentum/Analysis/event_samples/split_projection.py:350-355`；實作後續已改讀 `row_index_local`，故此為文件與契約不一致而非目前 runtime 索引。
**來源摘要**: momentum/Analysis/event_samples/split_projection.py#a77abd9bf671; docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f
[P2/high] 影響：後續維護可能把全框 row 當 local ordinal；修法：改寫該段為 `time_bounds`／local 座標語意；可行性：文件-only。
## 審查答覆
Q1：三者有效輸出皆為時間排序後 local ordinal：split_per_symbol `:741-747`；adapter `:64-69`、WF `:129-139`；orchestrator 單標的 `:603-638`、attest `:674-682`。未發現 frame 序反例；P1-01 是輸入 dtype gate 漏洞。
Q2：是；三處分別在 `contracts.py:758-768`、adapter `:239-250`、orchestrator `:642-652` 共用 producer 對應時間軸。clock probe 實跑三 producer×train/test 全部 `fp_match=True bounds_match=True`。
Q3：是合取；中列 +1 且首尾不變只有 fingerprint 可擋（`-k fingerprint`: 9 passed），同集合重排 fingerprint 不變而由 `非嚴格遞增` guard 擋；兩閘不可互代。
Q4：直接寫入／deepcopy／pickle 後保留舊 fingerprint 均擋；probe 輸出兩者 `writeable=True` 後 `ValueError ... 指紋不符`。若 `object.__setattr__` 同步重綁 local、fingerprint、time_bounds，probe `PASS 3 1`；這是 D-001 §4.13/4.15 明示的無 authenticity trust boundary，歸 SU-RESID-5，不重報 b8 缺陷。
Q5：三條測試的綠燈反例：`test_per_symbol_interleaved_never_indexes_full_frame` 可在只丟掉 B 後仍因 A 非空而綠；`test_insufficient_events_in_test_is_per_symbol_not_batch` 可只算第一個 symbol 而在現 fixture 綠；`test_fingerprint_mid_row_shift_caught_though_endpoints_match` 可移除 symbol/base-hash 欄而仍抓到時間位移。
M-SU-D1-23：本家族裁定 needs-research；single-symbol golden 中 local==global 故 oracle-row_index mutation 不可觸發，兩 symbol 交錯 refreeze 值得 b9 評估，非本輪新增 finding。
ASSUMPTIONS_VERIFIED: R13 reconcile stamp 三家皆 APPROVED；Q2/Q4 probes 已實跑且輸出如上；未把 SU-RESID-5/M-SU-D1-23 冒充 b8 defect。
TESTS_RUN: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k per_symbol`→12 passed；`-k fingerprint`→9；`-k insufficient`→2；wiring→9；producer attest→19；golden→9；`venv/bin/python scripts/freeze_splitunify_golden.py`→GOLDEN OK。
FAILURES_SEEN: 初次 probe 使用錯誤 import／舊 SplitPlan kwarg，已修正命令；/tmp cleanup 被 gate 拒絕（本任務 round OPEN），未修改程式碼。
SCOPE_CHANGES: none；唯讀審查，僅新增本交接檔。 NUMERIC_OR_SCHEMA_IMPACT: none made；OUTPUT: handoffs/20260911-splitunify-b8-review-r1-codex.md
VERDICT: blocked; BLOCKED-BY: CODEX-R1-P1-01, CODEX-R1-P1-02; CLOSED:
STATUS: DONE

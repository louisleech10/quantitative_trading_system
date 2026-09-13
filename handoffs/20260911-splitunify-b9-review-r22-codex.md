# SPLITUNIFY B9 R22 review — codex；task-id=`20260911-SPLITUNIFY-B9-REVIEW-R22`；範圍=diff `2f66cf77`、current block、TODO 舊段、SPEC 現行正文；未審 HISTORY/沿革，未改碼、SPEC、TODO。
## CODEX-R22-P1-01
**斷言**: TODO §E 將 `SU-RESID-2` 宣稱全數關閉，但多 TF `EventSplitPlan` 下游仍在 `Task 9.3`，只能部分關閉。
**碼證**: `pattern_bridge.py:125-127` 仍 raw `set_index("event_id")` 取側別；`tables.py:372` 仍 raw `set_index("event_id")` 消費 assignments；TODO Task 9.3 仍列兩處及 named tests。
CODE-ANCHOR: momentum/Analysis/event_samples/pattern_bridge.py:125
MUTATION: 以同一 `event_id` 的兩個 `feature_timeframe` assignment 列餵入 `lab_by_id[e]`；現行 raw lookup 產生非唯一結果，未完成唯一側去重／衝突 fail-closed 便不能宣稱下游閉合。
**來源摘要**: `docs/SPLITUNIFY_TODO.md#c65295978e06`; `momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2`; `momentum/Analysis/event_samples/tables.py#843ba7f68172`。**修法/可行性**: §E 改「部分關閉／blocked-by；B9B 完成 producer/schema、assignments／purged 欄與 guards；下游待 Task 9.3，named tests＋M-SU-D2-37/40 通過前不得關閉」；Task 9.3 已具名落點與 mutation。
## CODEX-R22-P1-02
**斷言**: TODO Task 2.3 仍要求 golden 只比 `event_id` 集合，未標 superseded，與 SPEC §G 多 TF parent key 及 Task 9.5 複合鍵契約互斥。
**碼證**: TODO Task 2.3 lines 277、281-289 仍指示 event-ID diff/oracle；`freeze_splitunify_golden.py:181-187` 的 g1/g3b 實際只保存 event IDs。
CODE-ANCHOR: scripts/freeze_splitunify_golden.py:181
MUTATION: 對同一事件新增／移除一個 feature-timeframe row 而維持 `event_id`；sorted event-ID lists 不變，錯誤 TF 漏列可使 g1/g3b 綠燈。
**來源摘要**: `docs/SPLITUNIFY_TODO.md#c65295978e06`; `docs/SPLITUNIFY_SPEC.D-002.md#eb23b548de08`; `scripts/freeze_splitunify_golden.py#98358e0b8eb1`。**修法/可行性**: Task 2.3 三處加 `SUPERSEDED BY Task 9.5`，改比 `(event_id, feature_timeframe)` 或 `*_multi_tf` 平行組；單 TF v8 保留，SPEC §G 165/TODO Task 9.5 已定義落點，無需重開 9.2b 設計。
## CODEX-R22-P1-03
**斷言**: SPEC 現行正文同時要求 9A 交付 `metadata.split_unify`、又把 metadata 移入殘留；§N 的 SU-RESID-2 亦仍寫成 TODO 尚未同步，與 B9B／實際 schema 互斥。
**碼證**: SPEC §P Task 9.1 lines 185-187、§N 326/329 將 metadata 寫成交付；§V 177/257 與 TODO Task 9.1 line 463 將其移出本批；`EventPipelineResult` 只有 `summary`、`split_plan` 等欄。
CODE-ANCHOR: momentum/Analysis/event_samples/pipeline.py:52
MUTATION: 依 SPEC §P 185-187 從現行 `EventPipelineResult` 讀 `result.metadata.split_unify`；dataclass 沒有 `metadata` 欄，執行時失敗。
**來源摘要**: `docs/SPLITUNIFY_SPEC.D-002.md#eb23b548de08`; `docs/SPLITUNIFY_TODO.md#c65295978e06`; `momentum/Analysis/event_samples/pipeline.py#83011e0913c7`。**修法/可行性**: §P/§N 統一 producer→`EventSplitPlan.summary`，metadata/終端可見性留 SU-RESID-9A-UI，SU-RESID-2 改 B9B producer/schema 完成、下游待 Task 9.3；現行 dataclass/TODO line 463 已提供一致落點。
(1a/1b) `CODEX-R21-P1-01=CLOSED`：`venv/bin/python -m pytest -rxX --runxfail tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed` → rc=1、`DID NOT RAISE AlignmentViolationError`；正常命令 → `1 xfailed`。`CODEX-R21-P1-02=CLOSED`：Task 2.2 三處均 SUPERSEDED／16-key 指向；scoped pytest → `105 passed, 1 xfailed`。 (2a/2b) 其他互斥僅 Task 2.3 G-3a/G-3b/G-5②；貼入 `SUPERSEDED BY Task 9.5：多 TF golden 以 (event_id, feature_timeframe) 或 *_multi_tf 平行組，比對 event_id-only 僅保留單 TF 舊錨。`
(3a/3b) `SU-RESID-2` 判「部分關閉、餘下 Task 9.3」，可貼入字面見 P1-01。 (4a) 阻擋段為 §P 185-187、§N 326、§N 329；§P Task 9.2 line 196 的 unconditional `str(selected_timeframe)` 是 stale snapshot，但 199-201 已修正且現行 code conditional，non-blocking doc-literal-only。
(4b) §P/§N 統一 producer→summary、metadata 留 SU-RESID-9A-UI、§N SU-RESID-2 改 partial/Task 9.3 pending（P1-03）。(5a/5b) 不可進 B9C；最小集合=`CODEX-R22-P1-01,CODEX-R22-P1-02,CODEX-R22-P1-03`；不重開 9.2b–9.5 設計，保留 xfail。
§0/§1/§2/§3/必要性：上述三條否證未驗證假設；矛盾三條 P1，漏項為 Task 9.3 下游與多 TF golden，測試可測性現有 xfail/回歸足夠但下游 named tests 待做；quant、OOM、cache、API/型別與不必要工作無新增 finding。
ASSUMPTIONS_VERIFIED: R21 兩條修補、RECONCILE-STAMP v18 rc=0、`--runxfail` 確為 `DID NOT RAISE`、scoped regression `105 passed/1 xfailed`。
TESTS_RUN: normal target=`1 xfailed` rc=0；`--runxfail` rc=1 expected；two-file pytest rc=0；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0。FAILURES_SEEN: 僅預期紅燈 `DID NOT RAISE AlignmentViolationError`。
SCOPE_CHANGES: 僅新增本 review artifact，未改 code、SPEC、TODO、HISTORY、data_cache。 NUMERIC_OR_SCHEMA_IMPACT: 未改數值／schema／檔案大小。 OUTPUT_PATH: `handoffs/20260911-splitunify-b9-review-r22-codex.md`
VERDICT: blocked
BLOCKED-BY: CODEX-R22-P1-01,CODEX-R22-P1-02,CODEX-R22-P1-03
CLOSED: CODEX-R21-P1-01,CODEX-R21-P1-02
STATUS: DONE

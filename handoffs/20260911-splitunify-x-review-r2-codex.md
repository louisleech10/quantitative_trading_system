# SPLITUNIFY SPEC/TODO adversarial review R2 — CODEX
task-id: 20260911-SPLITUNIFY-X-REVIEW-R2 | family: CODEX | findings-round: R2
reviewed: SPEC 84ab732b021b… / TODO 7d6d4f0c4e90… / reconcile_stamps_check.sh rc=0；未改碼、未改 SPEC/TODO
## CODEX-R2-P0-01
**斷言**: Q1／C10：v2 雖要求 pipeline 接收 canonical boundary＋feature_index，卻沒有把現行只拿 bars 的 production caller 接到 SplitPlan pair／event_index 的可執行 adapter；除非另增未寫的 universe 供給路徑，C-0 仍未閉合。
**碼證**: SPEC:61-76、130-137、Task2.1:287-302、Task3.1:360-375；`case_import_service.py:1588-1613` 只有 bars/切分參數，`pipeline.py:653-657` 無 feature_config 即回 None，`SplitPlan` 欄位在 `contracts.py:378-403` 仍須由另一端建立。
**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b, docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90, api/services/case_import_service.py#f06b46eb685d, momentum/Analysis/event_samples/pipeline.py#f78eae8df0f6
## CODEX-R2-P1-02
**斷言**: Q1／Q4：若按 C-0／Task3.3 走 event-study-only，`event_forward_return_table` 會計算全 manifest 事件而非 OOS test；`tables.py:305` 實為需 plan 的 binary 表，pipeline 反而回 not_computed。後端 lookahead reason 可區分，但前端缺 status 時預設 ok 且不讀 `resp.capability`，v2 未足夠防止把 study-only 數值誤讀為 OOS。
**碼證**: `pipeline.py:540-546,708-740`、`tables.py:157-177,210-252,279`；`EventTablesPanel.tsx:33-38,63-110,346-365`；既有 lookahead 字面在 `lookahead_gate.py:26-30`，SPEC:73-76、Task3.3:412-432 只定分派/reason，未定表格與畫面呈現。
**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b, momentum/Analysis/event_samples/tables.py#b80c15cf206d, momentum/Analysis/event_samples/pipeline.py#f78eae8df0f6, frontend/src/components/ic-analysis/EventTablesPanel.tsx#979163953945
## CODEX-R2-P1-03
**斷言**: Q2：ms 邊界若只是對既有 row index 在同一個 normalized feature index 上做精確索引，不是第二份 split arithmetic；但 M-SU-11 只擋「不呼叫兩支 helper」且同源自證，擋不住 train_end/test_start 漂移。另 C-4 允許 int64 ms，引用的 `_normalize_ic_time_index` 卻拒絕 ms；C-5 要求 bucket_ms／embargo raise，而投影簽名沒有 config/bucket 參數，介面不可執行。
**碼證**: `split_preview.py:19-46,63-79` 兩支只回 row/point；SPEC:126-155、163-174、Task2.1:289-306、Task2.2:310-338；`EventSplitConfig` 的 bucket/embargo 在 `types.py:63-83`，cluster 取值在 `event_split.py:126-157`，normalizer 在 `ic_filter_orchestrator.py:259-277`。
**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b, docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90, momentum/core/split_preview.py#6b6a1d95c5cc, momentum/Analysis/event_samples/types.py#8ba12e1b5204, momentum/Analysis/ic_filter_orchestrator.py#1eb5824cf5e7
## CODEX-R2-P1-04
**斷言**: Q6：G-5 只有名稱，需補可偽證 oracle：①row fingerprint＝canonical `(position, feature_ts_ms, symbol, universe_hash)` 的 exact SHA，首個 row mismatch；②assignments/purged＝直接由 `feature_index[train/test_plan.row_index]` 產生之集合，斷言互斥、覆蓋、purge reason，輸出 diff event_id；③answer-window＝逐事件 label 起訖對 source bars 完整覆蓋，缺 endpoint 或跨界必產 purge＋event_id；④leakage-negative＝注入跨 boundary answer interval／future train feature，必 reject 或 purge、mutation rc=1。
**碼證**: SPEC:G-5:218-221、TODO:178-199 只列四項與 G-3b 集合 oracle，沒有 fingerprint 序列化、answer-window bar predicate、負例 fixture、失敗輸出或命令；故目前不可重現也不可判定漏洩。
**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b, docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90
## CODEX-R2-P1-05
**斷言**: Q5：B1→B3 的 FAILED nodeid 集合相等是應保留的 fail-closed 特性，不是施工阻塞；但必須規定「集合變動即停、以新 pytest receipt 重凍、只移除已變綠 nodeid」。目前產生管線未保留 pytest rc，且 TODO:109 的合法空清單與 :111-113 的 `test -s` 互斥，collection failure 可能偽裝空基準、乾淨基準又無法通過。
**碼證**: TODO:101-117 的 `pytest | tee | awk` 無 pipefail/PIPESTATUS、空清單與 `test -s` 矛盾；SPEC:376-387 只定集合相等與 deselect，未定 rc 捕獲及漂移處置。
**來源摘要**: docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90, docs/SPLITUNIFY_SPEC.md#84ab732b021b
## CODEX-R2-P2-06
**斷言**: Q3：`n_symbols=1` 時 `_degraded_flags(..., cluster_adjusted=True)` 的 `single_symbol` 是正確且應保留的探索性揭露，不是誤導；Q7：R1 C1–C13 均在 v2 有落點，但 C10 只是被 C-0 重述、未閉合（見 P0-01）；Q8：B2 應拆成 B2a Task2.1 → B2b Task2.2 → B2c Task2.3，各自 gate/review 後才進 B3。
**碼證**: `event_split.py:21-30` 與 `tests/momentum/event_samples/test_tables.py:42-60` 支持 single_symbol 語意；R1 synth:19-31 與 brief:24-42 逐列對應 C1-C13；TODO:39-49／SPEC:223-232 雖標 B2「大」仍只有批末 gate。
**來源摘要**: momentum/Analysis/event_samples/event_split.py#fde5a520c319, handoffs/reconcile/20260911-splitunify-x-review-r1/synth.md#c3a4bff5573b, handoffs/20260911-SPLITUNIFY-SPECTODO-REVIEW-R2-BRIEF.md#1b8db7f6ca56, docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90
## Verdict: 需修補後再派工；不可進 B1
一句話：C-0/C10 的 production 落點、study-only 誠實呈現、projection/golden/baseline 可執行性仍有 P0/P1 缺口；先修 SPEC/TODO 與驗收契約，再開始 B1。

# GAP-3 B2 review R1（CODEX）
TASK_ID: 20260821-GAP3-B2-REVIEW-R1; FAMILY: CODEX
SCOPE: brief 指定之 B2.1–B2.5 diff、規格/TODO、survivor v2、golden 與測試；未改程式碼。
ASSUMPTIONS_VERIFIED: event_samples=123、survivor=51、golden canonical_sha=163c4cecb1006dc42dea0804acc365d83fe7cdbaf05ba64b1d794168dd67e463；`git diff --check` 無輸出。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 123 passed；`venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py -q` → 51 passed；`venv/bin/python scripts/gap3_freeze_golden.py --check` → CHECK PASS。
FAILURES_SEEN: none; SCOPE_CHANGES: none; NUMERIC_OR_SCHEMA_IMPACT: review-only，未改輸出；指出 AR-3/事件契約風險。
OUTPUT_PATH: handoffs/20260821-gap3-b2-review-r1-codex.md
## CODEX-R1-P1-01
**斷言**: AR-3 共同欄未在正式 B2 表/報告一致落地，B2.2/B2.5 無法機械判定 macro、micro、raw/effective n、cluster CI、degraded、LOSO 與 formal pooled gate。
**碼證**: TODO:210 要求每張表列全套欄；`tables.py:221-242` 的 B2.2 `common` 只有部分摘要，`all_bars_eval.py:152-173` 沒有共同區塊，且 B2.1 macro 僅 `mean/n_symbols`（`tables.py:151-154`）。
**來源摘要**: docs/GAP3_EVENT_TODO.md#df04bdabf37d；momentum/Analysis/event_samples/tables.py#9dff52e142b5；momentum/Analysis/event_samples/all_bars_eval.py#572fea6ecdfd。
## CODEX-R1-P1-02
**斷言**: B2.5 eligibility 未驗資料連續性/PIT 合法性，且持有報酬固定取 `open[i-k]`，未依 D1-6/實際 entry semantic 映射；缺口或非 open 進場會被報成可用結果。
**碼證**: `all_bars_eval.py:21-31` 只檢 warmup、tail、有限正價格；`:78-109` 未檢 timestamp continuity/cutoff，並硬編 `hold=(close[i+h]-open[i-k])/open[i-k]`；TODO:288 明列 continuity、PIT、實際進場價。
**來源摘要**: momentum/Analysis/event_samples/all_bars_eval.py#572fea6ecdfd；docs/GAP3_EVENT_TODO.md#df04bdabf37d。
## CODEX-R1-P1-03
**斷言**: B2.3→B2.4 的六鍵 event context 未接通：feed 只產 timestamps/label values，實際 analyze helper 未傳 `event_context`；因此事件 survivor 可落成六鍵全 null，而 validator/test 仍放行。
**碼證**: `ic_feed.py:35-65` 無六鍵 context；`tests/momentum/helpers/ichc_run.py:30-68` 只轉兩個 event 參數；`survivor_contract.py:462-465` 缺 context 即全 null，與 contract:257 的 conditional IC 六鍵全非 null 不一致；test:610-616 固化此 loophole。
**來源摘要**: momentum/Analysis/event_samples/ic_feed.py#6a3d48a225ad；tests/momentum/helpers/ichc_run.py#239c098c7b82；momentum/Analysis/survivor_contract.py#ef7015934eeb；momentum/Analysis/contracts/ic_survivor_contract.json#270696d74f32。
## CODEX-R1-P2-04
**斷言**: survivor v2 validator 取 `control_kind.enum` 而非 import contract 的 `accepted` 集合，故會接受目前明定拒絕的 `platform_random_bars`。
**碼證**: `survivor_contract.py:368-371` 只比對 enum；`event_import_contract.json:43-48` 將 `platform_random_bars` 列 enum 但列入 rejected，並明定恆拒。
**來源摘要**: momentum/Analysis/survivor_contract.py#ef7015934eeb；momentum/Analysis/contracts/event_import_contract.json#7111b2d7060e。
## CODEX-R1-P2-05
**斷言**: conditional IC 直接 label override 未做 finite gate；`event_label_values` 的 `inf/-inf` 會通過存在性檢查與 float cast，繼續進入 IC，而非 loud unavailable/reject。
**碼證**: `ic_filter_orchestrator.py:2875-2887` 僅檢 key 是否存在並 `float(...)`，沒有 `np.isfinite`/有限值拒絕；同檔 `:2890-2892` 隨即標記 conditional IC。
**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#eccdb0be9fb8。
## Verdict：B3 blocked pending P1 fixes
P1-01、P1-02、P1-03 會影響正式推論欄位、固定分母/entry estimand 與事件 survivor 可消費性；B3 readiness 尚未成立。

# GAP3_EVENT_UX_TODO — D 延伸 002（B1 實作期之修訂）

BASE: docs/GAP3_EVENT_UX_TODO.md @ afa70967
PREDECESSOR: docs/GAP3_EVENT_UX_TODO.D-001.md

改什麼: 三條——A-002 更正 TODO Task 4.2 之「S-9 之 6 條驗收」為 SPEC 之 **≥7 條**；
A-003 定死小時命名欄之換算捨入方向（SPEC 未定，取保守方向）；
A-004 具名 Task 2.1b 前端下界值來源之殘留（依賴後批）。
為什麼: A-002 為 TODO 與 FROZEN SPEC **衝突**，依 TODO §層級宣告「以 SPEC 為準並回報」；
A-003 為 SPEC 沉默處之實作決策，會被 B3／B7 消費，必須先寫下否則各批各自解讀；
A-004 為 B1 交付邊界，依「殘留每條必帶為何現在不做」具名。
檔名依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.2（`*.D-NNN.md` 機讀規約）。

## 觸及面宣告

新增: none
覆寫: Task 4.2 之「驗證」欄中「S-9 之 6 條驗收」該字面
依賴: docs/GAP3_EVENT_UX_TODO.D-001.md（A-001 定 B1 含四個 Task，本檔沿用該讀法）

## 內容

### A-002 — Task 4.2「S-9 之 6 條驗收」與 SPEC 之 ≥7 條衝突

- **TODO 原文**（Task 4.2 驗證欄）：`pytest tests/momentum/event_samples/ -q -k horizon_curve` **≥3 條** ＋ **S-9 之 6 條驗收**。
  同一字面亦出現於 `docs/GAP3UX_IMPL_HANDOFF.md` §2 之座標表。
- **SPEC（語意權威，FROZEN）**：§G「S-9 之驗收」明訂
  `pytest tests/momentum/event_samples/ -q -k canonical_serialize` **≥7 條**，並逐條列出 ①–⑦。
- **裁定**：依 TODO §層級宣告「本檔與 SPEC 衝突時**以 SPEC 為準並回報**」⇒ **採 7 條**。
- **這不是抄寫差異，⑦ 是真缺口**：⑦＝`horizons=[1,3,3,7]` 須 raise `ValueError`。
  實跑 `momentum/Analysis/event_samples/tables.py::event_forward_return_table` 之守衛
  只擋 `not horizons or any(h < 1 ...)`，重複 h 會在 `out[str(h)]` 互相覆寫而**靜默通過**。
  若照 TODO 的「6 條」落地，最可能被省掉的就是這條。
- **驗證**：`pytest tests/momentum/event_samples/ -q -k canonical_serialize` 條目數 `>= 7`；
  `grep -c 'canonical_serialize' docs/GAP3_EVENT_UX_SPEC.md` `>= 1`。
- **mutation**：移除 `tables.py` 中重複 h 之守衛 ⇒
  `test_canonical_serialize_07_duplicate_horizon_raises` 須轉紅；還原轉綠。
  receipt：`handoffs/run_receipts/gap3ux-b1-task42-s9-mutation.receipt.json`（`4.2-M1` PASS）。

### A-003 — 小時命名欄換算根數之捨入方向＝**向上取整**

- **SPEC 原文**：`bars_of(c, tf) = c.lookahead_hours ÷ hours_per_bar(tf)`；
  驗收②之 receipt 命令為 `72*3600//TIMEFRAME_SECONDS['1h']` 與 `…['12h']` → `72 6`。
- **SPEC 未定捨入方向**：`72h` 在 `1h`／`12h` 上整除，floor 與 ceil 同值 ⇒ 該例分辨不出。
  但 `future1_close_return`（H=1）在 `12h` 線上，floor 得 **0**——等於宣稱「不必 purge」，
  而該欄確實看到未來 1 小時。
- **裁定**：取 **ceil**。依 §C0「量化正確性只能更嚴、不得放水」——
  在 SPEC 沉默處，只准往保守方向解讀。
  落點＝`momentum/Analysis/contracts/future_column_lookahead.json` 之
  `hours_to_bars_rounding: "ceil"`（loader 對該值 fail-closed，非註解宣稱）＋
  `momentum/Analysis/event_samples/lookahead_registry.py::hours_to_bars`。
- **對 SPEC 驗收②之相容性**：整除情形不受影響，`72 6` 仍成立（已實跑）。
- **驗證**：`pytest tests/api -q -k gap3_lookahead_depth` 之②仍以
  `72*3600//TIMEFRAME_SECONDS[tf]` 為期望值且通過；
  `pytest tests/momentum/event_samples/ -q -k lookahead_registry_complete` 之
  `test_lookahead_registry_complete_07_hours_to_bars_is_ceil` 斷言 `hours_to_bars(1,'12h') == 1`。
- **mutation**：把 `hours_to_bars` 之回傳改為直接取 `lookahead_hours` ⇒
  `test_gap3_lookahead_depth_02_hour_named_resolves_per_tf` 與 `…_03_…` 轉紅；還原轉綠。
  receipt：`handoffs/run_receipts/gap3ux-b1-task21b-mutation.receipt.json`（`2.1b-M2` PASS）。

### A-004 — 具名殘留：Task 2.1b 前端下界**值來源**未於 B1 接上

- **B1 已交付**：`momentum/Analysis/event_samples/lookahead_depth.py::depth_by_timeframe()`
  （唯一 exported 深度函式）＋ `frontend/src/lib/lookaheadDepthLock.ts`（鎖定與阻擋）
  ＋ `frontend/src/app/search/page.tsx` 之選單 disable 與匯出前守衛
  （阻擋發生在任何網路動作**之前**，vitest 斷言 `fetch` call count `== 0`）。
- **未接上的是「下界值從哪來」**：`lookaheadLowerBound` 現恆為 `null`（＝尚無約束）。
- **為何現在不做**（三值理由：**blocked-by**）：
  ① 會引用未來欄之**篩選面板**是 **Task 2.1（B5）**，B1 時不存在
    ——現行搜尋條件（price_change／volume_multiplier／closing_strength／
    taker_buy_ratio／price_position）一個未來欄都沒引用，導出下界恆等於宣告值；
  ② 把導出值送到前端之**傳輸點**是 **Task 1.3（B2）**所建之
    「case 鏈內既有回應欄位承載點」（不新增 route）。
- **為何不在前端自算**：TODO Task 2.1b 明訂 `depth_by_timeframe()` 為
  **唯一 exported 深度函式**（Task 1.9 與 V-12 一律引用本式，禁第二份）。
  在 TS 重寫＝第二份副本，兩條路徑必然漂移。
- **owner**：主委。**觸發**：Task 2.1（B5）與 Task 1.3（B2）皆落地後，於 B5 收尾一併接線。
- **不得宣稱已解決**：B1 交付的是鎖定機制，不是下界值。

## 修訂索引

| 編號 | 標的 | 一句話 | 日期 |
|---|---|---|---|
| **A-002** | Task 4.2 驗證欄 | 「S-9 之 6 條」與 SPEC 之 ≥7 條衝突，以 SPEC 為準；⑦是真缺口 | 2026-08-24 |
| **A-003** | 小時命名欄換算 | SPEC 未定捨入 ⇒ 取 ceil（保守方向），寫進 registry 並 fail-closed | 2026-08-24 |
| **A-004** | Task 2.1b 前端 | 下界**值來源**待 B2／B5 接線；B1 只交鎖定機制 | 2026-08-24 |

## 戳記

（委員於此 append；格式：
`RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<body-hash> task:<harness-task-id>`）

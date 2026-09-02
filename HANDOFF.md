# HANDOFF — 當前任務狀態

**更新：2026-09-02｜狀態：GAP-3 UAT 進行中（使用者驗到 B12），程式面 42 Task 全數落地**

## 現在的阻塞＝使用者驗收 ＋ 兩張已裁定未動工的票
- B1–B12 已走過；**B2 現已作廢不必驗**（見 `G3-D1`）。下一步＝ B13–B20。
- 收 epic 之條件已改變，**不是「簽字即收案」**。

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D1` | **OPEN・已改判**（2026-09-02）：不是改成兩組條件，而是**整區移除匯出前篩選**。理由＝CSV 已可回灌、深度改為匯入時直接問。動已凍結 SPEC Task 2.1／2.1b／2.2／2.3／1.9 ⇒ **須開延伸檔 `D-006`（未開工）** |
| `G3-D2` | **OPEN**：五維度三類值不接受永久灰著；UAT B3 在三者全交付前記未完成 |
| `KLINE-1` | **OPEN・9/2 二次改裁**：`/data-preparation` 舊區塊「導入案例 CSV → 批量 K 線下載」**註解之後移除**；`/search`（自己讀寫 `data_cache/kline_cache.h5`）與 FF 頁（寫 `feature_klines/`，FF／IC／事件全只讀它）**按現況保留、不合鏈**。FF 頁下載鏈 e2e 收據 VERIFY:20260902T012246Z-ff-kline-download-e2e（真下載、寫暫存、dtype/attrs 同現有檔、20 根九欄逐 bit 相等）；該鏈之自動化測試見下方「9/2 這批做了什麼」。**「註解」步驟已做**（`/data-preparation` 舊區塊橫幅＋六個舊 route／兩個元件／service／hook 之 DEPRECATED 註記，零行為改動）。🔴 移除前提：舊 `/case/list` 仍被 FF `BatchGenerationPanel`（三個 symbol 來源之一）、`chart`／`charts`／`strategy-test` 頁呼叫。移除＝大任務（`routes/case.py` 與 GAP-3 端點同檔），走完整管線 |
| `G3-D3`…`D9` | CLOSED（D3/D4/D5 於 9/1；D6/D7/D8/D9 於 9/2） |

## 9/2 這批做了什麼
- **票號不入使用者可見層**：檔名 `events_*`、UI 與後端訊息去票號；新增機械閘 `noTicketIdInUi.test.ts`。
  連帶修掉一條 `toContain('GAP-6')` 假斷言（釘死錯的性質，同 R3 `readOnly` 那型）。
- **`meta.` 改補集**（原手寫 24 欄白名單漏 drawdown）——與 9/1 的 `G3-D4` 同型重犯。
- **契約 CSV 走錯區**於選檔當下攔下；前後端判準逐字對證。
- **`[object Object]`**：新增 `lib/httpError.ts`，31 個呼叫點全改。
- **FF 下載鏈補測試** `tests/api/test_feature_kline_download_chain.py`（離線 stub 只換 HTTP，轉換／寫入走產品碼）VERIFY:20260902T014330Z-ff-kline-download-chain-tests
- **`/data-preparation` 舊區塊標 deprecated**（橫幅＋註記，零行為改動；`KLINE-1` 之「註解」步）。

## 已知紅／不要誤判
- `tests/api` 既有紅 4 條（batch_alias／ichc_event_timestamps／progress_rss_fields×2；
  後兩條只在整包跑時紅、單跑 7 passed＝event-loop 污染，見 `G3-R11`）。
- `tsc --noEmit` 8 行既有債（FactorReturnChart.test／useFeatureFactory.batchDate.test）。

## 🔴 進行中（2026-09-02，使用者離線期間）
- **三家 consult 已派**：session `20260902-gap3ux-x-consult-r1`／task `20260902-GAP3UX-X-CONSULT-R1`／
  round_id `521c3a6a-8b1c-4ba1-baa3-c0e212bc24e8`（債已開，**收斂前不得派新工**）。
  brief `handoffs/20260902-gap3ux-d006-class-consult-BRIEF.md`；產出 `handoffs/20260902-gap3ux-x-consult-r1-{codex,composer,grok}.md`。
  題目：移除匯出前篩選依 `FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.1 是 **R 重開**（推翻 FROZEN A-1／Phase 2）還是可作 D；
  R 之最小可執行範圍；D-001…D-005 效力（三份引用 2.1b）。分歧預設 R。
- 接回流程：`reconcile_build.sh` → 讀三檔 → synth → `debt_clear.sh --round-id … --session …` → 依 verdict 起草 R／D 文件。

## 下一步（依序）
1. 等使用者驗 B13–B20。
2. 🔴 consult 已收斂（`handoffs/reconcile/20260902-gap3ux-x-consult-r1/synth.md`）：**R 重開，非 D**；全檔對抗審；五份延伸檔 `SUPERSEDED-BY-R` 併回；R 本體必含匯出端深度來源設計。下一步＝主委起草 R brief＋修訂稿 → 三家 adversarial。
   逐項判定 `export-count-*` 與下界守衛去留（匯出仍需 `lookahead_bars_declared`；兩條匯出路徑之值來源目前唯一是 2.1b 導出之 state）。
3. `KLINE-1`：先「註解」（deprecation 標示，不改行為）→ 再開移除票走完整管線；順手補 FF 下載鏈的 e2e 測試（真 provider、寫暫存目錄、比 dtype/attrs）。

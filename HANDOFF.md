# HANDOFF

## 🔴 接手第一件事：讀 `docs/GAP3UX_IMPL_HANDOFF.md`（唯一入口）

含：§0 狀態與各批交付物＋R3 出口清單、§1 開工前稽核（含期望值）、§2B **B7 是什麼＋已做完的偵察**
（**不必重查**）、§3 派工管線（逐字指令＋三件套 RECHECK 常設條款）、§4 完成判準與 mutation 寫法
（**九個假綠實例**）、§5 未辦、§6 地雷與治理現況、§7 具名殘留全文、§8 檔案地圖。
**讀完即可開工。本檔只放指標。**

⚠️ 本檔刻意不寫批次代號緊接狀態欄之形態（`factkey_write_guard.sh` 會擋），亦避開「某某已完成」句型。

## 狀態

GAP-3 事件型 UAT 缺口修補：SPEC 🔒 FROZEN（`4ce3d6d9`）、TODO 🔒 FROZEN v1.0（`afa70967`）、
延伸檔 D-001（`81cbe7ab`）與 D-002（`51f1a65e`）皆三家 APPROVED；D-003（`09884811`）與 **D-004**（B7 開工前之契約修補）尚未過戳記。
42 個 Task 之計數：**19 ✅／1 🔧／22 ⬜**（逐 Task 狀態一律看看板）。
Task 4.2 之後端驗收已寫（4 條 `-k horizon_curve`），前端未接線 ⇒ 該 Task 仍計為未完成。

前五批之 code review 輪數與 findings 收斂：第三批 **6 → 3 → 0**、第四批 **7 → 4 → 4 → 1 → 1 → 0**、
第五批 **6 → 3 → 1 → 0**，皆三家一致收；收斂檔在 `handoffs/reconcile/2026082{5,6}-gap3ux-b{3,4,5}-review-r*/synth.md`
（兩道機檢皆 rc=0）。第五批另解除三條必辦殘留（`D-002 A-004`／`R-B3-1`／`R-B3-2`），各有 mutation 守住。

Task 3.1／3.2／3.3（事件批次刪除）之六輪 code review findings **5 → 2 → 2 → 1 → 兩家零 → 0**，
三家一致可收。收斂檔在 `handoffs/reconcile/20260826-gap3ux-b6-review-r{1,2,3,4,5,6}/synth.md`
（兩道機檢皆 rc=0）。R5 因 composer 執行端 `resource_exhausted` 無產出而 quorum 不足，
依工具設計內逃生口 `--abandon --kind collection-failed` 銷帳後重派 R6 三家全員收尾——
**未改治理碼**。

兩件交裁的事皆已三家一致定案：`RULING-1` ＝ 選項 1（本瀏覽器曾成功分析過，
判準字面採 codex 逐字版，附「文案須揭露本機範圍」之條件）；
`RULING-2` ＝ ①（跟隨指向目錄的 root symlink＝既有 storage 語義；codex 撤回其 P1），
**該裁定不放寬 batch ownership 邊界**，溢出仍由 `R3I-M1` 鎖住。

**B7（Phase 4 匯出端報酬欄與揭露）已開工，卡在延伸檔 `D-004` 之戳記**。
開工偵察查出**兩件會擋住實作的事**，已派 consult 輪，四題皆有裁定
（`handoffs/reconcile/20260826-gap3ux-b7-consult-r1/synth.md`）：
① 匯出記錄要帶的 `future_{h}bar_return` 與 `lookahead_bars_declared`，
契約 validator **實測皆以 `unknown_field` 拒收** ⇒ 照 SPEC 字面實作會產出**匯不回去的檔**；
裁定＝改契約，走 `D-004`。
② Task 4.1 移除主答案窗後，前一批之下界守衛有一半變死碼；裁定＝改形不刪。
③ 交接 §2B.1 之「4.2 會讓 G-2 golden 合法改變」經實測**確認為錯**（golden 跑 IC 管線、
不碰 `analyze_tables`；`--check` rc=0、sha 未變）⇒ **不重凍**，該節已於下方更正。
④ Task 4.2 之後端已具備，**前端未接線**（`EventTablesPanel` 不帶 `horizons`）。

🔴 **`D-004` 戳記輪 R1：composer／grok APPROVED、codex REJECTED——REJECTED 是對的。**
`RULING-3(c)` 實為 **2 vs 1**（codex＋grok 裁「保留 `proceed` 結構保證、改簽章」，
composer 裁「移除」），主委逐字採了 composer 的表格又標成「三家一致」＝
本 epic 第**五**次「宣稱大於實作」，形態是**未逐家交叉核對即宣稱一致**。
已改為多數且較嚴之版本並新增 page runtime 驗收⑤；D-004 之 body 雜湊隨之改變
⇒ **R1 三份戳記全部作廢，須跑 R2**（brief 已改寫完成，可直接派）。

**下一步＝派 `D-004` 戳記輪 R2 → 通過後才改契約 → Task 4.1 → 4.1b → 4.1c → 4.3 → 4.2 前端。**
🔴 **上列兩件「B7 開工前必讀」已於 consult 輪處理完畢，結論見上**：守衛存廢＝改形不刪
（`D-004 A-021`）；G-2 golden ＝**不會改變、不重凍**（`D-004 A-022`，原宣稱為誤植）。

看板 `白話說明/GAP-3施工看板.md`；歷史 `白話說明/GAP-3施工進度.md`。

## receipt

VERIFY:handoffs/run_receipts/gap3ux-b6-all-mutations.receipt.json

| 項 | 值 |
|---|---|
| mutation | 32／14／13／15／19／**23** 條（六批），皆 `closure: CLOSED` |
| 本批驗收 | `pytest tests/api -q -k gap3_event_delete` 15（下限 4）；vitest `eventBatchDeleteConfirm` 11＋`eventBatchDeleteWarning` 8（下限 2／2） |
| 全套 | `pytest tests/api tests/momentum/event_samples` 959 passed／3 failed（**既有債**，名單見交接 §6.5）；vitest 47 檔 288 條；build rc=0；`gap3_freeze_golden --check` rc=0（sha 未變） |

mutation 判準＝**轉紅之 test 集合逐一等於預期**（多紅少紅皆 FAIL）。
🔴 `--record` 出現 `紅=[]` 一律當作假綠信號，先查根因（交接 §4.2 有九個實例；本批又抓到兩條）。

## 具名殘留

**全文一律見 `docs/GAP3UX_IMPL_HANDOFF.md` §7.2／§7.3**（本檔不複列，避免副本漂移）。
代號：`R-GOV7-1`／`R-GOV7-2`／`R-B1-1`／`R-A005-1`／~~`R-B2-1`~~／`R-B2-2`／`R-B4-1`／
~~`R-B3-1`~~／~~`R-B3-2`~~／`R-B3-3`／~~`D-002 A-004`~~／`D-001-D-003 provenance`／純 JS 手刻 sha256
＋ SPEC 末節 `F-1..F-4` ＋ TODO R3 reconcile 四條。

## 三條鐵律（違反即返工）

- **完成 ＝ 驗證命令 rc=0 ＋ mutation 實跑轉紅還原轉綠 ＋ receipt 入 commit**。只有測試綠不算完成。
- **不得碰治理**（使用者 2026-08-24）。工具壞掉 ⇒ 繞過並具名記錄，不修不開票。
  唯一已授權例外＝mutation 併發隔離（已完成，用法見交接 §4.1）。
- **不要用原始碼形狀證明執行期性質**——同一病已五度出現（§6.2）；
  「比對範圍過寬／失真」已犯**七次**（§6.1）。一律字面錨點、禁行號；
  檢查寫完要用**已知會紅的輸入**試一次。

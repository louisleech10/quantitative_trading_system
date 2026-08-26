# HANDOFF

## 🔴 接手第一件事：讀 `docs/GAP3UX_IMPL_HANDOFF.md`（唯一入口）

含：§0 狀態與各批交付物＋R3 出口清單、§1 開工前稽核（含期望值）、§2B **B7 是什麼＋已做完的偵察**
（**不必重查**）、§3 派工管線（逐字指令＋三件套 RECHECK 常設條款）、§4 完成判準與 mutation 寫法
（**九個假綠實例**）、§5 未辦、§6 地雷與治理現況、§7 具名殘留全文、§8 檔案地圖。
**讀完即可開工。本檔只放指標。**

⚠️ 本檔刻意不寫批次代號緊接狀態欄之形態（`factkey_write_guard.sh` 會擋），亦避開「某某已完成」句型。

## 狀態

GAP-3 事件型 UAT 缺口修補：SPEC 🔒 FROZEN（`4ce3d6d9`）、TODO 🔒 FROZEN v1.0（`afa70967`）、
延伸檔 D-001（`81cbe7ab`）與 D-002（`51f1a65e`）皆三家 APPROVED；D-003（`09884811`）尚未過戳記。
42 個 Task 之計數：**19 ✅／1 🔧／22 ⬜**（逐 Task 狀態一律看看板）。

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

**下一批＝B7（Phase 4 匯出端報酬欄與揭露）**。
🔴 **B7 開工前必讀的兩件事**：① Task 4.1 要移除匯出面板之「主答案窗」單選，而第五批的下界守衛
整套綁在它上面 ⇒ 守衛之存廢須在 brief 具名請三家重新裁定（不得默默刪，也不得留死碼）。
② Task 4.2 會讓 G-2 golden **合法**改變（D-4 之受管變更，須以 §G S-9 參考實作重凍並在 commit message 說明）。

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

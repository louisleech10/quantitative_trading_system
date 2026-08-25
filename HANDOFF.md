# HANDOFF

## 🔴 接手第一件事：讀 `docs/GAP3UX_IMPL_HANDOFF.md`（唯一入口，444 行）

含：§0 狀態與前三批交付物＋R3 出口清單、§1 開工前稽核（含期望值）、
§2 **B4 是什麼＋已做完的偵察**、§2B **B5 是什麼＋偵察**（兩者皆**不必重查**）、
§3 派工管線（逐字指令＋B3 學到的三件事）、§4 完成判準與 mutation 寫法（**五個假綠實例**）、
§5 未辦、§6 地雷與治理現況、§7 具名殘留全文、§8 檔案地圖。**讀完即可開工。本檔只放指標。**

⚠️ 本檔刻意不寫批次代號緊接狀態欄之形態（`factkey_write_guard.sh` 會擋），亦避開「某某已完成」句型。

## 狀態

GAP-3 事件型 UAT 缺口修補：SPEC 🔒 FROZEN（`4ce3d6d9`）、TODO 🔒 FROZEN v1.0（`afa70967`）、
延伸檔 D-001（`81cbe7ab`）與 D-002（`51f1a65e`）皆三家 APPROVED。
42 個 Task 之計數：**10 ✅／1 🔧／31 ⬜**（逐 Task 狀態一律看看板）。

Task 1.11／1.12／1.9（深度三層防線）之三輪 code review findings **6 → 3 → 0**，三家一致、未派 R4。
commit＝`b63fc855`＋`ed426d34`＋`ed9b3fc4`＋`6f7063e4`。過程與裁定理由見三份收斂檔
`handoffs/reconcile/20260825-gap3ux-b3-review-r{1,2,3}/synth.md`（兩道機檢皆 rc=0）。

**下兩批＝B4（Task 1.5／1.6／1.7 匯入前端）＋ B5（Task 2.1／2.2／2.3 匯出前篩選）**，前置皆已滿足。
🔴 兩批各有**必辦之殘留解除**：B4 辦 `R-B2-1`；B5 辦 `D-002 A-004`（下界值來源未接線，
接上前 B1 的鎖定是死碼）、`R-B3-1`、`R-B3-2`。`blocked-by` 指的就是這兩批，做完卻沒解除＝殘留變偷懶。
🔴 **B5 之 Task 2.2 落點與 TODO 字面不同**（實際在 `frontend/src/lib/eventExport.ts`），
須在 brief 具名回報請三家裁，收 epic 前走延伸檔 D-003 更正。

看板 `白話說明/GAP-3施工看板.md`；歷史 `白話說明/GAP-3施工進度.md`。

## receipt

VERIFY:handoffs/run_receipts/gap3ux-b3-all-mutations.receipt.json

| 項 | 值 |
|---|---|
| mutation | 32／14／**13** 條（前三批），皆 `closure: CLOSED` |
| 第三批驗收 | `lookahead_declaration` 10／`split_blocked` 9／`gap3_horizon_declaration` 10（下限 2／6／5） |
| 全套 | `pytest tests/api tests/momentum/event_samples` 887 passed／3 failed（**既有債**，名單見交接 §6.5）；vitest 208；build rc=0；`gap3_freeze_golden --check` rc=0 |

mutation 判準＝**轉紅之 test 集合逐一等於預期**（多紅少紅皆 FAIL）。
🔴 `--record` 出現 `紅=[]` 一律當作假綠信號，先查根因（交接 §4.2 有五個實例）。

## 具名殘留

**全文一律見 `docs/GAP3UX_IMPL_HANDOFF.md` §7.2／§7.3**（本檔不複列，避免副本漂移）。
代號：`R-GOV7-1`／`R-GOV7-2`／`R-B1-1`／`R-A005-1`／`R-B2-1`／`R-B2-2`／
`R-B3-1`／`R-B3-2`／`R-B3-3`／`D-002 A-004`／`D-001-D-002 provenance`／純 JS 手刻 sha256
＋ SPEC 末節 `F-1..F-4` ＋ TODO R3 reconcile 四條。

## 三條鐵律（違反即返工）

- **完成 ＝ 驗證命令 rc=0 ＋ mutation 實跑轉紅還原轉綠 ＋ receipt 入 commit**。只有測試綠不算完成。
- **不得碰治理**（使用者 2026-08-24）。工具壞掉 ⇒ 繞過並具名記錄，不修不開票。
  唯一已授權例外＝mutation 併發隔離（已完成，用法見交接 §4.1）。
- **不要用原始碼形狀證明執行期性質**——同一病已四度出現（§6.2）；
  「比對範圍過寬／失真」已犯**七次**（§6.1）。一律字面錨點、禁行號；
  檢查寫完要用**已知會紅的輸入**試一次。

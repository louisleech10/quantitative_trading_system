# HANDOFF

## 🔴 接手第一件事：讀 `docs/GAP3UX_IMPL_HANDOFF.md`（唯一入口）

該檔含：§0 狀態與 B1／B2 交付物＋R3 出口清單、§1 開工前稽核命令、
§2 **B3 是什麼＋已做完的偵察（不必重查）**、§3 派工管線（含實測可用之逐字指令）、
§4 完成判準與 mutation 寫法（**含三個假綠實例**）、§6 地雷與治理現況、§7 具名殘留全文。
**讀完即可開工。本檔只放指標。**

⚠️ 本檔刻意不寫批次代號緊接狀態欄之形態（會與 `governance-batch-status` fact-key 撞名誤報），
亦避開「某某已完成」句型（`verify_pretooluse.sh` 會要求 SUPERSEDED 標記）。

## 狀態

GAP-3 事件型 UAT 缺口修補：SPEC 🔒 FROZEN（`4ce3d6d9`）、TODO 🔒 FROZEN v1.0（`afa70967`）、
延伸檔 D-001（`81cbe7ab`）與 D-002（`51f1a65e`）皆三家 APPROVED。
42 個 Task 之計數：**10 ✅／1 🔧／31 ⬜**（逐 Task 狀態一律看看板，本檔不重述）。

Task 1.11／1.12／1.9（深度三層防線）之程式碼已寫入 repo，**三家 code review R1 進行中**。
新檔＝`momentum/Analysis/event_samples/lookahead_gate.py`（L3 閘）與 `lookahead_declaration.py`（L2 宣告解析）；
契約新增 `capability_reason_bindings`（reason 字面之具名綁定，使 `.py`／`.ts` grep 計數為 0）。
brief `handoffs/20260825-gap3ux-b3-review-r1-brief.md`；收斂檔將落在
`handoffs/reconcile/20260825-gap3ux-b3-review-r1/`。

**其後＝B4＝Task 1.5／1.6／1.7（匯入前端）**。
看板 `白話說明/GAP-3施工看板.md`；歷史 `白話說明/GAP-3施工進度.md`。

## receipt

VERIFY:handoffs/run_receipts/gap3ux-b3-all-mutations.receipt.json

| 項 | 值 |
|---|---|
| 第一批 mutation | 32 條，`closure: CLOSED`（`gap3ux-b1-all-mutations.receipt.json`） |
| 第二批 mutation | 14 條，`closure: CLOSED`（`gap3ux-b2-all-mutations.receipt.json`） |
| 第三批 mutation | **7 條**，`closure: CLOSED`（1.11×1／1.12×4／1.9×2，逐條對應 SPEC 明列之變異） |
| 第三批驗收 | `lookahead_declaration` 4／`split_blocked` 7／`gap3_horizon_declaration` 7（下限 2／6／5）；vitest 全套 206；`npm --prefix frontend run build` rc=0 |
| `pytest tests/api tests/momentum/event_samples` | 876 passed／3 failed（**既有債**，名單見交接 §6.5；該節所列 3 個 error 本輪未重現＝順序相依，屬 `R-B1-1`） |
| `python3 scripts/gap3_freeze_golden.py --check` | rc=0（`canonical_sha` 全程不變） |

mutation 判準＝**轉紅之 test 集合逐一等於預期**（多紅少紅皆 FAIL）。
🔴 `--record` 出現 `紅=[]` 一律當作假綠信號，先查根因（交接 §4.2 有三個實例）。

## 具名殘留

**全文一律見 `docs/GAP3UX_IMPL_HANDOFF.md` §7.2／§7.3**（本檔不複列，避免副本漂移）。
代號：`R-GOV7-1`／`R-GOV7-2`／`R-B1-1`／`R-A005-1`／`R-B2-1`／`R-B2-2`／
`D-002 A-004`／`D-001-D-002 provenance`／純 JS 手刻 sha256
＋ SPEC 末節 `F-1..F-4` ＋ TODO R3 reconcile 四條。
文件債：TODO Task 1.3「修改檔案」行之 `api/routes/case.py` 字面為 doc drift，
收 epic 前以延伸檔 D-003 更正。
根目錄 `.probe_ic*.sh` 三個 untracked 檔為更早批次之殘留，未納入任何 commit。

## 三條鐵律（違反即返工）

- **完成 ＝ 驗證命令 rc=0 ＋ mutation 實跑轉紅還原轉綠 ＋ receipt 入 commit**。只有測試綠不算完成。
- **不得碰治理**（使用者 2026-08-24）。工具壞掉 ⇒ 繞過並具名記錄，不修不開票。
  唯一已授權例外＝mutation 併發隔離（已完成，用法見交接 §4.1）。
- **不要用原始碼形狀證明執行期性質**——同一病已三度復發（交接 §6.2 逐條列出修法）。
  「比對範圍過寬」本 epic 已犯**六次**（§6.1）。一律字面錨點、禁行號；
  檢查寫完要用**已知會紅的輸入**試一次。

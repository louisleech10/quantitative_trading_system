# HANDOFF

## 🔴 接手第一件事：讀 `docs/GAP3UX_IMPL_HANDOFF.md`（完整實作交接，191 行）

**使用者已裁定：新 session 開始實作 GAP-3 事件型 UAT 缺口修補。**
本檔只放指標，開工所需之全部細節（稽核命令、B1 內容、派工管線、地雷、檔案地圖）在上列那份。

## 狀態

| 文件 | 狀態 | commit |
|---|---|---|
| `docs/GAP3_EVENT_UX_SPEC.md`（語意權威） | 🔒 FROZEN，42 Task | `4ce3d6d9` |
| `docs/GAP3_EVENT_UX_TODO.md`（操作依據） | 🔒 FROZEN v1.0，42 Task | `afa70967` |
| `docs/GAP3_EVENT_UX_TODO.D-001.md`（**須並讀**） | ⚠️ **未過戳記** | `f466a23b` |
| 實作 | ⬜ **42 Task 全部未開工** | — |

看板（給使用者看）：`白話說明/GAP-3施工看板.md`。

## 開工三件事（順序不可換）

1. 跑 `docs/GAP3UX_IMPL_HANDOFF.md` §1 之稽核命令（含三份 reconcile 之 stamp check 須 PASS）。
2. 🔴 **補跑 D-001 之戳記輪**（A-001 是主委自查更正，未經三家核可；開 B1 前必辦）。
3. 開 **B1＝Task 1.1、1.10、2.1b、4.2（僅 §G S-9 部分）**——
   🔴 **四個，不是兩個**；TODO §B 表格那列是錯的，D-001 A-001 已更正。
   照表格只做兩個 ⇒ B2／B3／B7 開工時 helper 不存在、當場停擺。

## 三條鐵律（違反即返工）

- **完成 ＝ 驗證命令 rc=0 ＋ mutation 實跑轉紅還原轉綠 ＋ receipt 入 commit**。只有測試綠不算完成。
- **不得碰治理**（使用者 2026-08-24 定死）。工具壞掉 ⇒ 繞過並具名記錄，不修不開票。
  落地出錯就抄仔細，**不要做工具來量自己**——那是 SPEC 階段燒掉六輪的原因。
- **一律字面錨點，禁行號**；檢查寫完要用「已知會紅的輸入」試一次。
  「比對範圍過寬」本 epic 已犯四次，四次形狀相同（詳見實作交接 §6.1）。

## 收 epic 前須補

動過 `scripts/plain_docs_sync_check.sh` ⇒ 跑 `bash scripts/gov_check.sh --no-probe`（**丟背景**，
十分鐘級；**跑它時不得動檔**）。另 GAP-3 B5 之 UAT B 段簽字仍在使用者手上。

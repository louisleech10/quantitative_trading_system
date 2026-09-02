# HANDOFF — 當前任務狀態

**更新：2026-09-02｜狀態：GAP-3 R 實作批已落地（待三家 review）；UAT 停在 B12（使用者離線）**

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D1` | **OPEN・R 實作批已落地，待三家 code review／adversarial 後 CLOSED**。規格：SPEC `R37-landing`＋TODO 三家 `RECONCILE-STAMP` APPROVED（session `20260902-gap3ux-x-stamp-r1`，`reconcile_stamps_check` rc=0） |
| `G3-D2` | **OPEN**：五維度三類值不接受永久灰著 |
| `KLINE-1` | **OPEN**：`/data-preparation` 舊區塊已標 deprecated；移除票待開（大任務） |
| `G3-D3`…`D9` | CLOSED |

## R 實作批做了什麼（細節＝`docs/GAP3UX_IMPL_HANDOFF.md` §1，已重寫）
- Task 1.9′：`/search` 匯出端答案窗宣告框（同一元件、同一 validator；`withExportDeclarationGuard` 保留 `proceed` 結構）；新端點 `POST /case/lookahead-declaration/preview-columns`（唯一實作 `preview_from_columns`）。
- Phase 2 退役：`exportFilter*`／`lookaheadDepthLock*`／篩選面板／`export-count-n`／`/case/lookahead-depth`／`EventImportService.lookahead_depth()`／`pipeline.lookahead_depth()` 全拆；`computeExportCounts` 改不接條件。
- Task 1.11：`needs` 恆 True、`ON_MISSING_BLOCK` 刪除、JSON 直傳缺欄 reject；**勾選**與**宣告**分拆（勾選只在引用驗不了的欄或調低時）；validator `v<0`（0 須明填）。
- 主委兩項設計決定（審查請攻）：①表單宣告與列內攜帶皆有時**表單為準**並改寫落檔列（記警語）；②「一律宣告」≠「一律勾選」。
- 測試：後端 GAP-3 子集 652 passed；前端全套 411 passed、`tsc` 只剩既有 8 行債；mutation 8/8 KILLED（M-B1…B4、M-F1…F4；M-B3 初跑因同秒同大小還原致舊 pyc 假紅，改 `-B`＋`touch` 後 1/0）。

## 下一步（依序）
1. commit＋push（本批）→ 派三家 review（brief 待寫；session `20260902-gap3ux-rimpl-review-r1`）→ finding 修 → CLOSED `G3-D1`。
2. 使用者回來後驗 B2（改寫）／B5／B10／B13–B20。
3. `KLINE-1` 移除票；`GOV-DOC-STATUS-1`；看板 42→39＋1 之機械重產工具。

## 已知紅／不要誤判
- `tests/api` 既有紅 4 條（batch_alias／ichc_event_timestamps／progress_rss_fields×2，見 `G3-R11`）；`tsc --noEmit` 8 行既有債。
- `uat_samples/*拷貝*`、`_tmp_new_schema.csv` 為本機雜物，未納版控。

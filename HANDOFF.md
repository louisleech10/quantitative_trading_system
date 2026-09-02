# HANDOFF — 當前任務狀態

**更新：2026-09-02｜狀態：GAP-3 R 實作批已落地＋R1 review 修法已落地；閉合輪 R2 派工中；UAT 停在 B12（使用者離線）**

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D1` | **OPEN・待 R2 閉合後 CLOSED**。規格：SPEC `R37-landing`＋TODO 三家 `RECONCILE-STAMP` APPROVED（session `20260902-gap3ux-x-stamp-r1`）。實作：commit `c6dd057a`（R 批）＋`7e0a7a94`（R1 四條修法） |
| `G3-D2` | **OPEN**：五維度三類值不接受永久灰著 |
| `KLINE-1` | **OPEN**：`/data-preparation` 舊區塊已標 deprecated；移除票待開（大任務） |
| `G3-D3`…`D9` | CLOSED |

## R 實作批＋R1 修法做了什麼（細節＝`docs/GAP3UX_IMPL_HANDOFF.md` §1／§1b／§2）
- Task 1.9′ 匯出端宣告框（同一元件／validator／守衛形狀）、`preview-columns` 端點（唯一實作 `preview_from_columns`）；Phase 2 全拆；Task 1.11 一律宣告、JSON 直傳缺欄拒收、`v<0`；「須勾選」與「須宣告」分拆（唯一判定 `declaration_is_unverifiable`）。
- R1 review（session `20260902-gap3ux-b11-review-r1`：codex 1 P1＋2 P2、grok 2 P1＋1 P2、composer sentinel；債已清）四條修法：匯出端預設欄集只取勾選附帶欄；preview 重取失敗作廢；深度＝宣告逐鍵複製（不再與引用欄取 max）；攜帶值自動勾選只限 JSON 直傳路由。
- 測試與收據：`docs/GAP3UX_IMPL_HANDOFF.md` §2（三張 receipt）；R1 修法後後端 GAP-3 子集與前端子集重跑皆綠（數字見該檔）。

## 🔴 進行中：閉合輪 R2（session `20260902-gap3ux-b11-review-r2`，task `20260902-GAP3UX-B11-REVIEW-R2`）
- brief `handoffs/20260902-gap3ux-b11-closure-BRIEF.md`；預期產出 `handoffs/20260902-gap3ux-b11-review-r2-{codex,composer,grok}.md`；log `/tmp/review_r2.log`。
- 收回後：`reconcile_build … --mode review` → 填群集 → attribution／completeness → `debt_clear` → 六條全 CLOSED 且無新 P0／P1 ⇒ `G3-D1` CLOSED（registry＋看板）→ commit＋push。有 OPEN ⇒ 修後開 R3。

## 下一步（依序）
1. 收 R2 → CLOSED `G3-D1`。
2. 使用者回來後驗清單 B2（改寫）／B5／B10／B13–B20。
3. `KLINE-1` 移除票；`GOV-DOC-STATUS-1`；看板機械重產工具；治理殘留：commit-msg claim 閘以「整則訊息」為單位（見 `白話說明/流程摩擦記錄.md` 9/2 下午）。

## 已知紅／不要誤判
- `tests/api` 既有紅（batch_alias／ichc_event_timestamps／progress_rss_fields×2，見 `G3-R11`）；`test_ic_deep_analysis` 與其他 pytest 並行時會 ERROR，單跑綠；`tsc --noEmit` 8 行既有債。
- `uat_samples/*拷貝*`、`_tmp_new_schema.csv` 為本機雜物，未納版控。

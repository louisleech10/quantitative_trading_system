# HANDOFF — 當前任務狀態

**更新：2026-09-02｜狀態：GAP-3 R 重開規格層已收斂，戳記輪派工中；UAT 停在 B12（使用者離線）**

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D1` | **OPEN・R 重開**：整區移除匯出前篩選（D-8）；SPEC `R36-landing`（commit `f4efec9f`）＋TODO 已過 R35 全檔對抗審→R36→R37 閉合（八條全 CLOSED、三家判可戳記）。五份 `D-00*` 延伸檔 `SUPERSEDED-BY-R` |
| `G3-D2` | **OPEN**：五維度三類值不接受永久灰著；UAT B3 在三者全交付前記未完成 |
| `KLINE-1` | **OPEN・9/2 二次改裁**：`/data-preparation` 舊區塊已標 deprecated（零行為改動），移除票待開（大任務）；`/search` 與 FF 頁按現況保留。FF 鏈 VERIFY:20260902T012246Z-ff-kline-download-e2e、VERIFY:20260902T014330Z-ff-kline-download-chain-tests |
| `G3-D3`…`D9` | CLOSED |

## 🔴 進行中：戳記輪 `20260902-gap3ux-x-stamp-r1`（task `20260902-GAP3UX-X-STAMP-R1`）
- stamp-target＝`handoffs/reconcile/20260902-gap3ux-x-review-r37/synth.md`（已用 `reconcile_add_stamp_section.sh` 加戳記區；body sha `6b5636d5…`）；brief `handoffs/20260902-gap3ux-r37-STAMP-BRIEF.md`；預期產出 `handoffs/20260902-gap3ux-x-stamp-r1-{codex,composer,grok}.md`；派工 log `/tmp/stamp_r1.log`。
- 收回後：`reconcile_stamps_check.sh <synth>` rc=0 → 銷帳（`reconcile_build`／`debt_clear`）→ SPEC 版本行改凍結（注意 `gap3ux_header_round_check.sh` 規則）。任一家 BLOCKED ⇒ 處理理由後開 stamp-r2。
- R35／R36／R37 synth 皆只在本機（`handoffs/*` 被 `.git/info/exclude` 排除，claim 閘擋 `-f`）。

## 戳記後才進實作批（依 SPEC R36-landing）
Task 1.9′（`/search` 匯出端答案窗宣告框、`withExportDeclarationGuard` 保留 `proceed`）＋Phase 2 退役清單（`exportFilter*`／`lookaheadDepthLock*`／`page.tsx` 篩選面板與 `export-count-n`／`/case/lookahead-depth` 端點與 `EventImportService.lookahead_depth()`；保留 `computeExportCounts`、`lookahead_declaration/gate/registry.py`、`depth_by_timeframe()`）＋Task 1.11 後端 `needs` 恆 True／JSON 直傳缺欄 reject／批內同值＋validator `v<1`→`v<0`（0 須明填）＋`POST /api/v1/case/lookahead-declaration/preview-columns`（唯一實作 `preview_from_columns`）。驗收含 `CODEX-R35-P1-02/03/04` 三條 mutation。之後：驗收清單（B2 消失、B5/B6 加答案窗）、施工看板重產、`docs/GAP3UX_IMPL_HANDOFF.md` 重寫。

## 已知紅／不要誤判
- `tests/api` 既有紅 4 條（batch_alias／ichc_event_timestamps／progress_rss_fields×2，後兩條為 event-loop 污染，見 `G3-R11`）；`tsc --noEmit` 8 行既有債。
- 具名殘留：`GOV-DOC-STATUS-1`（v2 檔頭狀態行過期）。

## 下一步（依序）
1. 收戳記輪 → 實作批（Claude 自任實作；review 三家全員）。
2. 使用者回來後驗 B13–B20。
3. `KLINE-1` 移除票走完整管線。

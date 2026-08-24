# HANDOFF

## 🔴 接手第一件事：讀 `docs/GAP3UX_IMPL_HANDOFF.md`（完整實作交接，191 行）

**GAP-3 事件型 UAT 缺口修補：第一批已落地，等三家 code review。**
本檔只放指標；開工細節（稽核命令、批次內容、派工管線、地雷、檔案地圖）在上列那份。

⚠️ 本檔刻意**不寫**批次代號緊接狀態欄之形態——那會與治理 epic 之
`governance-batch-status` fact-key 撞名而誤報（前例：commit `ee69cb7c` 之看板）。

## 狀態

| 文件 | 狀態 | commit |
|---|---|---|
| `docs/GAP3_EVENT_UX_SPEC.md`（語意權威） | 🔒 FROZEN，42 Task | `4ce3d6d9` |
| `docs/GAP3_EVENT_UX_TODO.md`（操作依據） | 🔒 FROZEN v1.0，42 Task | `afa70967` |
| `docs/GAP3_EVENT_UX_TODO.D-001.md`（**須並讀**） | 三家 APPROVED | `81cbe7ab` |
| `docs/GAP3_EVENT_UX_TODO.D-002.md`（**須並讀**） | ⚠️ 尚未取得委員戳記 | 本批 |

GAP-3 之 42 個 Task：3 個已完成、1 個進行中、38 個未開工。
第一批（Task 1.1／1.10／2.1b／4.2 之 §G S-9 部分）已落地完成，等三家 code review。
看板（給使用者看）：`白話說明/GAP-3施工看板.md`。

## 下一步（順序不可換）

1. **派第一批之三家 code review**（codex＋composer＋grok，實作者不自審）——
   brief 已備妥：`handoffs/20260824-gap3ux-b1-codereview-brief.md`（`brief_conformance_check` rc=0）。
2. review 收斂後，決定 **D-002 是否補戳記輪**（使用者裁定；A-002／A-003 會被後續批次消費）。
3. 才開第二批＝Task 1.2、1.3、1.4、1.8。其中 Task 1.3 需要第一批已建之
   `momentum/Analysis/event_samples/canonical_serialize.py`（已存在）。

## 第一批之證據（實跑）

- 驗收：`gap3_contract_reason_registry` 16／`lookahead_registry_complete` 12／
  `lookahead_rename_attack` 4／`gap3_lookahead_depth` 9／`canonical_serialize` 9／vitest 7 —— 皆綠。
- mutation：13 條逐條轉紅並還原轉綠，receipt
  `handoffs/run_receipts/gap3ux-b1-task{11,110,21b,42-s9}-mutation.receipt.json`（皆 `all_pass=true`）。
- G-1 `python3 scripts/gap3_freeze_golden.py --check` rc=0，`canonical_sha=163c4cec…`。
- `npm --prefix frontend run build` rc=0（型別檢查通過）。
- 迴歸：受影響之 20 個測試檔，改前／改後**同一種隔離**下皆 11 failed / 376 passed、
  失敗名單逐字相同、雙向差集皆空 ⇒ 本批零迴歸。

## 具名殘留（不排工，除非使用者指示）

- **R-B1-1 全量跑之測試順序污染**：`pytest tests/momentum tests/api` 全量跑時該 20 檔有 59 條紅，
  單獨跑只有 11 條。差距 48 條**與本批無關**（本批改動面在事件契約／`tables.py`／搜尋頁，
  59 條名單一條都沒碰到），但「順序污染」此一歸因**尚未實跑證明**——要證需以 stashed 樹全量跑一次，
  約 64 分鐘。三值理由：`needs-research`。owner 主委。
- **D-002 A-004 前端下界值來源**：`blocked-by` Task 2.1（篩選面板）與 Task 1.3（傳輸點），皆在後續批次。
- **D-001 provenance 不可登記**：`gate.sh register-output` 只收 `handoffs/` 或
  `stampable_artifacts.txt` 明列者 ⇒ 對 `docs/*.D-00N.md` 跑 `reconcile_stamps_check.sh` 會報
  provenance pending（**非戳記造假**）。provenance 完備之機械標的＝
  `handoffs/reconcile/20260824-gap3uxtodod001-x-stamp/synth.md`（rc=0）。三值理由：`user-ruling`。

## 三條鐵律（違反即返工）

- **完成 ＝ 驗證命令 rc=0 ＋ mutation 實跑轉紅還原轉綠 ＋ receipt 入 commit**。只有測試綠不算完成。
- **不得碰治理**（使用者 2026-08-24 定死）。工具壞掉 ⇒ 繞過並具名記錄，不修不開票。
  落地出錯就抄仔細，**不要做工具來量自己**。
- **一律字面錨點，禁行號**；檢查寫完要用「已知會紅的輸入」試一次。
  「比對範圍過寬」本 epic 已犯四次，形狀相同（詳見實作交接 §6.1）。

## 收 epic 前須補

動過 `scripts/plain_docs_sync_check.sh` ⇒ 跑 `bash scripts/gov_check.sh --no-probe`（**丟背景**，
十分鐘級；**跑它時不得動檔**）。另 GAP-3 之 UAT B 段簽字仍在使用者手上。

# HANDOFF

**當前**：兩件事都在**等使用者**，無進行中的施工。

## 1. `/search` 修復 — 🏁 已收案（2026-08-22）
使用者 UAT 現場回報的三個既有 bug 已修，三家蓋章通過。
- **收斂**：R1→R7 共 7 輪審查＋2 輪蓋章，findings 8→7→2→2→3→3→**0**
- **蓋章**：`reconcile_stamps_check.sh` rc=0，三家 APPROVED，body_sha `ae048e43…`
  （stamp-r1 codex REJECT 成立——殘留缺三值理由，已修並重蓋；r1 債以 `--abandon collection-failed` 結案）
- **commit**：`bf0fd48a`(production 終版)／`79fa7c69`(R7 審計鏈)
- **驗證**：DataExtraction 43 passed 1 skipped／event_samples 230／legacy 2／decoupling rc=0；
  **mutation 累計 29 條各自還原皆紅**；實跑 ETHUSDT 12h 1695 根唯一遞增
- **誠實帳**：`/search` 原有 bug 3 個、被我的修補變成可觸發 1 個、**我的修補引入或未補完 11 個**、
  **測試自身假綠 4 次（無一由自查發現）**
- **九項具名殘留**（各帶三值理由）見 `handoffs/reconcile/20260822-searchfix-x-review-r7/synth.md`
- 白話版：`白話說明/search搜尋修復.md`

🔴 **行為變更需告知**：下載資料不完整（亂序／stale／游標未前進）現在會讓任務標 **FAILED** 並帶出
symbol，不再顯示「找不到案例」。後者會讓使用者誤以為是條件沒中。

## 2. GAP-3 事件型 — B1–B5 全部蓋章，**只差使用者 UAT B 段 13 項簽字**
A 段 9 項已實跑 rc 全 0 並填入 `docs/GAP3_UAT_CHECKLIST.md`；B 段未簽不結案。

## 接下來（等使用者）
1. **重跑 UAT B1**（4 symbols、2024/01/01–2026/04/27）——`/search` 已修好
2. **跑 GAP-3 UAT B 段 13 項並簽字** → GAP-3 結案

## 坑（本輪新增）
- **commit 前必跑** `bash scripts/plain_docs_sync_check.sh --staged`
- brief 的 `fact-verified` 只准貼實跑 rc；測試計數一律從 receipt `grep` 複製
- **盤點型守衛（掃全模組找違規）必須自己被測**：範圍集合須 fail-closed，
  且要有 mutation 專驗「範圍外的違規會被抓到」。本輪同一守衛四版空心全由 mutation／委員抓出
- **靜態守衛須在碼內宣告效力邊界**（lint vs 證明），否則對抗審會無限迴圈
- **主委自訂的蓋章判準，送出前要對 stamp-target 自查一遍**——本輪判準 ④ 我自己寫、自己違反
- **委員 REJECT 也必須是合規 finding**（含斷言／碼證／來源摘要三欄），否則正確判斷會卡死收斂流程
- `completeness_check.sh` 正式入口＝`--lock <sources.lock>` **單獨使用**
- 委員 session 命名須 `<YYYYMMDD>-<epic>-<batch>-<kind>-r<N>`，task-id＝其大寫；
  stamp 輪 brief 須 `brief-kind: stamp` ＋ `stamp-target:` 欄

## 已知既有紅（非本輪造成）
- `tests/api` 10 failed + 3 errors（R2 已 byte-identical 基準對證）
- `gen_fact_key_blocks.sh --check` 對 `白話說明/Archived/GAP-2施工進度.md` 誤報 6 條：
  識別碼撞名（治理批次表用 B1–B5，GAP-2 看板也用 B1–B5）。修法要碰凍結的
  `status_scope_grandfathered`，與「治理不再擴建」衝突，先具名記著

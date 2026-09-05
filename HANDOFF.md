# HANDOFF — 當前任務狀態

**更新：2026-09-05（晚）｜狀態：`G3-D2` B-D4 實作完成並推送，**正在等三家 code review**。**

## 🔴 下一件＝B-D4 之 review 收斂（不是重寫實作）

**唯一入口＝`docs/GAP3D2_IMPL_HANDOFF.md`**（§2 每批七步；本批已走到**第 4–6 步：brief → 派工 → 收件收斂**）。
實作 commit `37fa0910`（已 push）。收據見該檔 §5 之 B-D4 列。

**B-D4 交付**＝D4.2（13 對全矩陣＋`rejected_pairs`／`pair_rejected` UI＋成對可行域與兩上界＋三層 oracle）
＋D4.3（k 參數化：seeds 去 k、雙值揭露；`event_label_scan` 網格：背景 task、`to_thread`、
per-cell／整體 timeout、progress 增 `scan_done/scan_total`、逾時格保留 partial）。

**驗證數字**（皆本機實跑，非轉抄）：
`pytest tests/momentum/event_samples/` **485**（B-D3 收工 415）｜golden `--check` **rc=0 / 46 cases**（原 23）
｜`pytest tests/api/test_gap3_scan_grid.py` **13**｜`npx vitest run` **515**（原 502）
｜`tsc --noEmit` **8 行既有債無新增**｜`check_decoupling_imports.py --baseline scripts/decouple_baseline.txt` **BASELINE OK**
｜mutation `handoffs/20260905-gap3d2-b4-mutate.py` **14/14 符合預期**（13 紅＋1 對照綠，還原乾淨）。
🔴 `tests/api -k "gap3 or event"` **342 passed／1 failed**＝`test_service_passes_event_timestamps_kwarg`，
**既有紅**（`G3-R11`／`B1-WEAKTEST-1`：它 grep 原始碼字串）；本批對該檔之 diff 為**純新增 270 行、0 刪除**，未觸及其目標行。

## benchmark 子步（依硬性約束，先於凍結 cap）

`scripts/gap3_scan_benchmark.py` → `handoffs/run_receipts/gap3_scan_benchmark.json`（已進版控）。
實測 ETHUSDT 60 事件 × 12h：五階段單格 mean **6.128ms**／p95 6.597ms／max 8.365ms。
⇒ `scan_grid_max_runs` 由暫定 **121 改為 110**：**121 是算術錯誤**（假設兩軸各 11 值，
但 h 定義域自 1 起 ⇒ h 軸只有 10 值）。`per_cell_timeout_s=60.0`／`scan_timeout_s=900.0` 之推導寫進 receipt 與契約 doc。
🔴 **誠實邊界**（寫在腳本檔頭與 receipt）：**沒量到**每格之條件 IC（需已物化 feature run），那段由兩道逾時保護。

## 🔴 兩件要讓使用者知道的（不是待決策）

1. **`D-001` D4.2 有一處規格洞，我自己補了**：D-001 寫「既選非法 pair ⇒ 另一維重設為契約 `default`」，
   但 `entry_price_semantic.default = "trigger_close"` 本身就在 `open_to_close` 的拒收對裡 ⇒ 該方向無解
   （**被我自己寫的 vitest 當場打穿**）。細化為「default 合法即用它；否則取契約 enum 順序第一個合法值並揭露原因」，
   兩者皆由契約導出。**該細化未經 SPEC 輪審查** ⇒ 登記殘留 `B4-SPECGAP-1`。
2. **既有斷言之對象變更**（D-006 §0「03/05 於 P4 改時附 diff」，diff 已在 commit message 具名）：
   `producer_03/04`（`next_open`／`k=3` 現已支援）、`SEED_KEYS` 三鍵→兩鍵、`/ic-analysis` k 由 locked→unlocked、
   UI 守衛由「只放行三 preset」→「擋 `rejected_pairs`、放行 13 對」。`producer_05` **變強**（斷言專屬 reason）。

## 稽核缺口已修（使用者 2026-09-05 指出的兩項）

1. `GAP3D2_IMPL_HANDOFF.md` §5 之 B-D3 列把 `B1-VERIFY-1` 標成「待使用者裁」——**已更正**為
   `cost`／觸發＝收 epic 前；R4 的 `blocked-by:g7` 隨 G-7 停用而失效。
2. B-D0 兩條＋B-D1 八條＋B-D3 三條殘留原本**只寫在 §5**，**已補登** `docs/IC_QUANT_GAP_REGISTRY.md`
   之新小表「G3-D2 實作批殘留」（三值理由逐字取自本機收斂檔），並加入本批新殘留
   `B4-COVERAGE-1`／`B4-SPECGAP-1`。

## 環境現況

開放債為零。工作區僅餘 2026-09-01 遺留之兩個 `uat_samples/*拷貝*` 未追蹤檔、
五個 `.claude/gate/*.sha` 未追蹤檔與 `market_data/*` 快取異動——**皆非主線產物，勿順手 commit**。
🔴 紀律不變：`pytest tests/governance` 小時級且不含量化測試，只有「動共用控制流**且**收 epic 前」才跑。

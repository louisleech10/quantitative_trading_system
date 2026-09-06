# HANDOFF — 當前任務狀態

**更新：2026-09-07｜狀態：`SCANCUBE` 五個 Phase 全部完成並 push，等使用者實機驗收 B26／B27。**

## 剛完成：掃描結果瀏覽器（小型帶）
SPEC=`docs/GAP3_SCAN_CUBE_SPEC.md`／TODO=`docs/GAP3_SCAN_CUBE_TODO.md`（皆 TEMPLATE PASS）
文件審兩輪：R1 21 條（3×P0）、R2 19 條（0×P0）⇒ **P0 3→0**，收斂後直接進實作。
commit：`bb402ed6`（文件）→`1563768b`（後端 P1–P3）→`d68f0bcd`（前端 P4）→`cdea55c0`（白話 P5）。

- **P1** 掃描格 `_suppress_persist=True`：修覆蓋（實跑證明 4 組 (k,h) → 相異路徑數 1）與逾時競態。
- **P2** `momentum/Analysis/scan_cube.py`：Tier A（summary_table，463 B/特徵）＋
  Tier B（七個圖表節，36,808 B/特徵）；三個 fail-closed 閘；`correlation_matrix` 具名排除。
  Tier B 預算看**實測累加**不是首格外推（跨報告差 8 倍）。路徑不變式：`stored=False ⇒ path=None`。
- **P3** `/api/v1/ic/scan-cube/{task_id}/{manifest,rows,charts}`：404／409／400 三種語意分開。
- **P4** `ScanCubeBrowser.tsx`：三視圖；跨格**無排序按鈕**（SPEC §C-4 禁跨格排名）。
- **P5** 白話 B26／B27。

## 🔴 使用者主目標之部分未達成（已列為白話頭條）
滿格 110 格 × 300 特徵之圖表資料 ＝ **1,158 MB** ⇒ **滿格不保證有圖表**，只保證指標表。
小範圍（約 12 格 × 474 特徵內）圖表齊全。超出時 fail-closed 並回報**當次實測**之 `fits_hint`。

## 收案時數字
`test_scan_cube.py` 28／`test_scan_cube_api.py` 12；`tests/api -k "gap3 or event or scan_cube"`
443 passed／1 failed（`test_ichc_event_timestamps::…kwarg`＝既有債，已用 `git stash` 在父版本重跑同樣紅）；
前端 vitest **599 passed／75 檔**；tsc 8 行既有債；解耦 `BASELINE OK`；golden 46 rc=0。

## 具名殘留
`SC-RESID-1` 掃描峰值記憶體（OOM）不在本票（`blocked-by`：需 tier-aware 實跑，本機 8GB）——
🔴 SPEC §C-8 明文：所有 cap 限的是**落檔位元組**，不是計算峰值。
`SC-RESID-2` `correlation_matrix`（`blocked-by`：per-pair，另案）。
`SC-RESID-3` 「選幾格補存圖表」（`needs-research`）。
`COMPOSER-R1-P2-03`（揭露票）實機頁接線仍待 UAT。

## 環境
開放債為零。`scripts/_add_cube_contract_keys.py`、`scripts/_todo_r2_patch.py` 為一次性腳本，
`rm` 被權限擋下故仍在工作區——**可刪，未進版控**。
`uat_samples/*`、`.claude/gate/*baseline*`、`market_data/*` 未追蹤異動勿 commit。

# EVTALIGN R4 Codex review — target d398b194, range ba408826..d398b194
## CODEX-R4-P2-01
**斷言**: B4 的進度回報下界對 1–2 個特徵欄位不成立：實際 callback 數分別為 1、2，低於 TODO 要求的至少 3 次。
**碼證**: `data_preprocessor.py:43-52,240-243`；VERIFY `venv/bin/python -c ...` → `1 1 [1]`、`2 2 [1, 2]`、`3 3 [1, 2, 3]`，rc=0；RECHECK 同命令並以 `n in (1,2)` 重跑。
**來源摘要**: momentum/Analysis/data_preprocessor.py#976406c53838
P2，信心度=High；小型 feature run 或 filter 後只剩 1–2 欄時違反可觀測性契約。修法需明確安排至少三次有意義的回報，或把小 n 例外寫入 SPEC/TODO 並補測試；本 finding 不涉及數值洩漏。
## CODEX-R4-P2-02
**斷言**: B4 在處理當前欄位前就回報 `done=pos`，所以每次中間回報都高估一欄，最後回報 `done=total` 時最後一欄尚未完成。
**碼證**: `data_preprocessor.py:240-264`；VERIFY 將 `_clip_series` 記錄為已處理並收集 callback → `[(1, 0), (2, 1), (3, 2)]`，rc=0；RECHECK 同一 probe。修法是將回報移到該欄 winsorize/skip 完成後。
**來源摘要**: momentum/Analysis/data_preprocessor.py#976406c53838
P2，信心度=High；UI 可能先顯示 100%/完成再執行最後欄位，ETA 也以提前一欄的 elapsed/done 計算；不改 IC 數值但違反「已處理特徵數」語意。
## 必答 Verdicts
1a/1b：未找到 B3 漏洩或合法邊界誤丟。stage0 先裁 feature、預載 labels 以 trimmed `feature_index` reindex（orchestrator:2910-2963）；coverage 用 `decision_at <=` 與 `label_end <=` 且 selected index 再與 feature 交集（service:341-358,610-616；orchestrator:3247-3250），故端點等於 `label_end` 保留；targeted backend 53 passed/0 skipped，phase3 A7/A8/A9 各 rc=1 mutation red。
2a/2b：WARN 路徑 `_memory_snapshot` 例外回 None，`_memory_pressure` 不 raise，`_report_progress` 也吞 callback 例外；正常機器測試無 warning。phase4 三條 mutation 均 rc=1。ETA 首次回報由 `reports>=2` gate；未承諾單調性。另確認上列兩個 P2：小 n 下界與 callback 在工作前發生。
3a/3b：isolation bars 讀 report 的 `metadata.ic_train_test_split`；`purge_rows` 由 service pipeline/project_purge 產生並以原 config embargo 注入，service 只做來源揭露與加總（service:152-188,598-715）。service 落點成立；非事件不寫 isolation 是有意 scope/保 golden 的揭露邊界，不回移 orchestrator。
4a/4b：`analyze_full` 只委派 `analyze`；`refilter` 消費 analyze 已快取之 label，不另造未驗 series；cross-sectional 明確 N/A=EA-RESID-2。phase2 A6a/A6b 均 rc=1；fallback 透傳 event args 並在重跑後以最後一次 consumed/validated 配對，未見錯配反例。
5a/5b：一個 phase2–5 全綠缺陷是本輪兩個 B4 P2（`n<3` interval 與 pre-work callback），現有 A6a/b、A7–A13 mutation 不改這兩處，故會全部綠。clean clone 實跑 phase2 `2/2`, phase3 `3/3`, phase4 `3/3`, phase5 `2/2`，各 `UNCOVERED=0`、每 mutation rc=1；每 phase runner rc=0。
6：沒有發現 ≥10× 不必要複雜；period_alignment 兩層分工是 feature∩kline（orchestrator）與逐事件 coverage（service），`_inject_period_alignment` 合併且不覆蓋，不能在不混淆責任/破壞 golden 下任意合一。
7：無 P0/P1 或資料洩漏 BLOCKING；可進 B26–B31 UAT，但兩個 P2 必改後才算本輪完整收案。
Verdict: 需修補後收案——B4 兩個 P2 進度語意缺陷；其餘 B3/B5/Task 2.2 與 phase2–5 mutation 未見 blocking finding。
ASSUMPTIONS_VERIFIED: target/range 以 git show d398b194 核對；B3 boundary/reindex、B4 normal/no-warning/ETA gate、B5 producer-bound 數字與 phase mutation 均有碼證；real browser/thrash/Linux psutil 未在本輪執行。
TESTS_RUN: targeted backend → rc=0, 53 passed, 0 skipped；`venv/bin/python handoffs/20260907-probe-split-baseline.py` → rc=0, 9 cases (8 ok/1 skipped), golden True；frontend vitest → rc=0, 11 passed；phase2–5 clean clone → all rc=0/UNCOVERED=0；`npx tsc --noEmit` rc=1, only 8 pre-existing errors in FactorReturnChart.test.tsx/useFeatureFactory.batchDate.test.ts。
FAILURES_SEEN: one malformed local probe command had SyntaxError before retry; no production/test failure. `tsc` known baseline errors remain.
SCOPE_CHANGES: none to production/test/docs/frontend; only new review artifact `handoffs/20260908-evtalign-x-review-r4-codex.md` and temporary clean clone.
NUMERIC_OR_SCHEMA_IMPACT: none; review-only findings, no code or assertion edits.
OUTPUT_FILE: handoffs/20260908-evtalign-x-review-r4-codex.md
STATUS: DONE

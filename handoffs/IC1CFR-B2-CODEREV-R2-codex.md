# IC1CFR-B2 Code Review R2 — Codex
task-id: IC1CFR-B2 | date: 2026-07-15 | scope: Grok 退修兩檔 + B2 nodeid gate；唯讀，僅本檔產出

## 裁決
- **APPROVE（0 BLOCKING）**：上輪缺鍵通用空態已修復；本輪 delta 掃描未見新洞。
- `FactorReturnChart.tsx:141-160` 對 `null/undefined` 改顯示 `factor-return-unavailable` + 下架文案；union/legacy finite 既有路徑不變。
- `FactorReturnChart.test.tsx:70-79` 已移除舊 `factor-return-empty/暫無` 正向斷言，改為具名缺鍵下架斷言並反向禁止舊 testid。

## 獨立核驗
- `/tmp` 三態 probe：union 佔位 / 自造 legacy finite（9.8765/17.5308）/ 缺鍵，`1 file, 3 tests passed`；三者皆顯示下架警示且禁數值圖。
- `/tmp` 回放舊 null 分支 mutation：`missing_key_shows_unavailable_notice` 轉紅，錯誤為找不到 `factor-return-unavailable`；測試不再固化舊行為。
- `npm --prefix frontend run test -- ...FactorReturnChart... ...FactorEquityCurveChart... ...NetICChart...` → 3 files / 21 passed；`npm --prefix frontend run build` → exit 0（僅既有 hook warnings）。
- `python scripts/ic1cfr_stopgap_freeze.py --check-nodeids` → exit 0；baseline=77,current=44,new=0,resolved=33。
- 以本次 `.pytest_cache` 重算集合亦為 77/44/0/33；33 個 resolved 原 nodeid 送 `pytest --collect-only -q` → 33 collected, rc=0。
- resolved 33 非刪測/改名；相關 test delta 保留 redirect spy 斷言，僅將 deactivate 放入無條件 `finally` 修正 suite 污染。Phase26 更改不在這 33 內，且將 generic 錯誤 oracle 移至 `factor_centrality`、新增 FR unavailable 精確斷言，非放寬。
- `git diff --check -- FactorReturnChart.tsx FactorReturnChart.test.tsx` → exit 0。

ASSUMPTIONS_VERIFIED: 雙 reconcile stamp 機檢 PASS；三態實渲染 PASS；舊行為 mutation 轉紅；resolved 33 仍存在且未弱化斷言。
TESTS_RUN: 三態 probe 3/3；舊 null mutation 1 expected fail；vitest 21/21；Next build exit0；nodeid gate exit0 77/44/0/33；resolved collect 33/33。
FAILURES_SEEN: 僅預期的舊 null mutation failure；無未解決失敗。
SCOPE_CHANGES: none；review 僅新增本檔。
NUMERIC_OR_SCHEMA_IMPACT: 退修僅 UI 缺鍵空態/test；無數值、schema、輸出大小變更。
CODE-REVIEW-R2: APPROVE

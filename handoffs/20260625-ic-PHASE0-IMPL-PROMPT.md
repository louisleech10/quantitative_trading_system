# IC Phase 0 — 實作派工（Codex workspace-write）

你是實作端。**完整讀**後逐 Task 寫碼：
- TODO（逐 Task 施工清單，**主依據**）：`docs/IC_PHASE0_TODO.md`
- SPEC（驗收準則/§G Golden/§A 事實）：`docs/IC_PHASE0_SPEC.md`
- 憲法：`CLAUDE.md`（解耦 7 條、不可違反原則、熱迴圈不 log、Logging）

## 執行順序（依賴拓撲，**不得亂序**）
1. **B1**（Task 1.1, 1.2）IC-CRASH → 自跑 `pytest tests/momentum/ -q` 全綠才進下一批。
2. **B2**（Task 2.1, 2.2, 2.3）IC-TIMEAXIS + IC-BYVOL → 自跑 `pytest tests/momentum/ -q`。
3. **B3**（Task 3.1-3.5）feature_filter——**B3 依賴 B2 完成**（同改 `ic_config_schema.py`，B2 先合）→ 自跑 `pytest tests/momentum/ tests/api/ -q` + `cd frontend && npm run build`。
4. **B4**（Task 4.1-4.4）decay log + UX → 自跑 `pytest tests/momentum/ tests/api/ -q` + `npm run build` + `vitest`。

## 鐵律（違反即退回）
- **TDD 兩 commit**：C-3/T-3 先寫測試 commit（重現 bug 紅）→ 再修 code commit（綠）。
- **防假綠**：不得放寬/刪除既有測試斷言換綠燈；diff 既有斷言須可解釋。
- **Golden**：`tests/momentum/test_ic_phase0_golden.py` 三 baseline（grouped/decay/feature_filter）須建並通過，結構化 float 比對非 byte。
- **不靜默截斷**：feature_filter 預設不截斷；前端 max_features 預設改 undefined。
- **不可做**（SPEC §N）：串流/train-test/case-control/decay R2 early-skip/向量化/resume-retry/by_volatility 分組實作——皆不碰。
- **欄位精確名**：feature_filter 用 include_features/exclude_features/include_pattern/include_categories/include_data_sources/include_families/max_features（禁簡寫）。

## 卡關協議（使用者定死）
- 任何 bug/test 不過/疑問，**自己試 ≤ 2 輪仍未解 → 立即停下，輸出 `STATUS: BLOCKED — <問題+你試過什麼>`**，不准 solo 連續試錯硬幹、不准放寬門檻交差。會交委員會討論。
- 需要使用者決策的也輸出 BLOCKED。

## 完成輸出
每批完成簡述（改了哪些檔/函式 + pytest 結果）。全部完成輸出：
```
STATUS: DONE
BATCHES: B1✓ B2✓ B3✓ B4✓
TESTS: <pytest 摘要 passed/failed> + npm build + vitest
FILES_CHANGED: <清單>
GOLDEN: <三 baseline 狀態>
```

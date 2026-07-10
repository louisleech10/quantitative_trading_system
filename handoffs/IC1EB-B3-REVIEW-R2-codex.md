# IC1EB B3 R2 複驗 — Codex（非作者）

範圍：重打 R1 唯一 finding、審多 `return_N` 確定性規則、抽查 R1 其餘 6 項；未改實作或測試。

1. **CLOSED — in-frame 一般 `return_N` 已被辨識。** 實碼把原 `return_1` 候選槽泛化為 `_select_inframe_return_n_column`，並在改名前解析所選原始欄名。獨立重打 R1 反例：MultiIndex、僅 `alpha+return_5`、無 `labels_path`、1500 rows → `label_horizon=5`、`maxlags=5.0`、`horizon_unresolved=False`、未 raise。
2. **PASS — 多 `return_N` 規則確定且相容。** 排序鍵為 `(int(N), column_name)`：先取最小 N，同 N 取字典序第一；不依欄位出現序。有 `return_1` 時仍選舊候選，保留既有行為。實跑 `return_5/3/10→return_3`、`return_3/03→return_03`、`return_1/5→return_1`；整路徑測試以欄序 5→3 仍解析 h=3。
3. **PASS — h=None fail-closed 未回歸。** `label` 不可解析時 t/p/q 非有限、n_tests=0、maxlags=None、`horizon_unresolved=True`。
4. **PASS — t_stat 仍為 HAC、非 i.i.d.。** 專測對 statsmodels HAC `use_t=True` oracle，並驗 HAC t 與舊 i.i.d. t 分離。
5. **PASS — resolver fallback-1 未復活。** `_label`/`label` 解析仍為 None；`return_5` 為 5。
6. **PASS — FDR 仍覆蓋全 feature。** q 值逐欄等於 `apply_fdr` 重算，n_tests 等於 finite p 數。
7. **PASS — 無新增門檻、排序未漂。** 輸出 feature 數不減，仍依 ICIR 降序。
8. **PASS — labels_path 真路徑與單軸拒絕未回歸。** `return_5` 仍令 maxlags≥4；cut2 單軸拒絕及既有 OOS/cut1 回歸均綠。cut1 測試 diff 只補 stage5 必需 `metadata.symbol`，未弱化斷言。

RECEIPT: `OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_ic_1eb_b3_xsec.py -q` → 11 passed in 1.83s。
RECEIPT: `OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_ic_cross_sectional_cut2.py tests/momentum/Analysis/test_ic_1a_cut1_oos.py -q` → 20 passed in 2.11s（1358 既有 RuntimeWarnings）。
RECEIPT: 1500-row 獨立 Python 反例輸出 `shape=(1500,2), label_horizon=5, maxlags=5.0, horizon_unresolved=False, raised=False`；多候選獨立 probe 三例全符合上述規則。
RECEIPT: `git diff --check -- momentum/Analysis/ic_filter_orchestrator.py tests/momentum/Analysis/test_ic_1a_cut1_oos.py` → clean；l65 inventory 兩檔 `git status` 無變更，未需 restore。

ASSUMPTIONS_VERIFIED: FIX1 實碼/測試與摘要一致；R1 精確反例已實跑；多候選 min-N/同-N 字典序規則已讀碼並實跑。
TESTS_RUN: B3 11 passed；cut2+cut1 20 passed；兩個獨立 Python probe passed；diff-check clean。
FAILURES_SEEN: none。
SCOPE_CHANGES: BLOCKING 執行副作用：cut1 回歸測試覆寫既有 gitignored `data_cache/features/BTCUSDT_1h_filtered.h5` 與 `data_cache/reports/ic_report_ic_gatekeeper.json`（mtime 2026-07-11 04:30:34）；無可用備份，未猜造/刪除資料。tracked l65 inventory 未變。
NUMERIC_OR_SCHEMA_IMPACT: FIX1 僅使 in-frame `return_N`(N≠1) 由 raise 變為 h=N 的 HAC 路徑；本 R2 無程式、schema 或輸出大小改動。

VERDICT: BLOCK

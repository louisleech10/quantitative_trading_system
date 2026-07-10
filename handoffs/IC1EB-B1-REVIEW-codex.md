# IC 1e+1b B1 Codex review（實作者非本委員）
範圍：工作樹 `statistical_validator.py`、`test_statistical_validator.py`、`tests/momentum/helpers/`、`pytest.ini`；自報僅作待驗資料。
PASS — STAMP：`bash scripts/reconcile_body_hash.sh handoffs/IC1EB-RECONCILE.md`=`b77932d8…`，與 codex/composer APPROVED 雙戳一致。
PASS — Task 1.1 靜態公式：`statistical_validator.py:59-71,74-150` 僅 Spearman；auto_bw/L、pairwise dropna、fail-closed、t(df=n-1)、顯式 maxlags<h-1→ValueError 均逐式符合 D-A，無 `method` 參數/Normal p。
FINDING — oracle 必跑未取得 receipt：自行重打 OLS/HAC/use_t oracle 的兩輪命令皆無任何輸出而終止（第1輪 5m、第2輪限 BLAS threads 2.5m）；故不能採信自報 allclose(rtol=1e-8)。可證偽：任一 se/t/p 與該 OLS 結果不滿足 `allclose(rtol=1e-8,atol=0)` 即失敗。
FINDING — T-1.1b M-A 未獨立驗證：同兩輪中 200 seeds 重跑未產出；自報 old=86/new=12、帶[4,16] 不算本委員 receipt。可證偽：固定 seeds 10000..10199 任一 count≠(86,12)或 new∉[4,16] 即失敗。
PASS — CODEX-2：`mean_z` 只在 `statistical_validator.py:137` 作 t 檢定，回傳鍵僅 t/p/se/n/maxlags；舊 `compute_ic_statistics` 與 ic_mean 類點估計未改。
PASS — Task 1.2：`apply_fdr:155-198` finite-only、NaN 保位、空 dict、n_tests=len(finite)，且呼叫既有 `adjust_multiple_comparisons(...,"fdr_bh")`；既有 BH 無 diff，未重寫。
FINDING — Task 1.3 違反 D-B：`block_bootstrap.py:92-108` 先在原樣本算一次 z，再重抽 centered z；並非同步重抽 `(x,y)` 後每次重算 Spearman IC，驗證腿與 kernel 不獨立。
反例：x=[1,2,3], y=[1,3,2]，重抽索引[0,1,1]；現碼固定-z mean=1/3，但對重抽 pairs 重新 rank 得 rho=1、mean(z)=2/3。兩個 bootstrap 分布不同，現有 T-1.3 p 帶不能證明規格算法。
FINDING — Task 1.3 邊界測試缺口：helper 有 `n<2*block`/rank_degenerate 分支，但新增測試只含 null/signal，未斷言 TODO 1.3 的 skip 與全相同值不炸。
FINDING — 轉紅 receipt 未獨立重現；`test_statistical_validator.py:416-434` 是「預算 mutant 後 assert agreement is False」的綠測試，未保存實際把 production t×2 後主同判斷言變紅的可執行 receipt。可證偽：套 mutant 後跑 `test_t13_block_bootstrap_agrees_with_kernel` 應非零退出。
PASS — 防假綠：`git diff -U0 HEAD -- tests/momentum/test_statistical_validator.py` 顯示既有刪除僅 import 替換；既有 assertion 無刪除/放寬，新增 assertion 皆為 `+`。
PASS — 未接線：`git diff --exit-code HEAD -- momentum/Analysis/ic_filter_orchestrator.py momentum/Analysis/bootstrap_estimator.py`=0；stage5 仍呼叫舊 pooled 函式，`_apply_thresholds` 與舊 `compute_ic_statistics(rolling_ic_dict)` 簽名未動。
PASS — scope/格式：`pytest.ini` 僅註冊 `slow_stat`；`git diff --check`=0；bootstrap helper 僅在 `tests/`。
ASSUMPTIONS_VERIFIED: 凍結 SPEC/TODO 全讀；公式/FDR/無洩漏/無接線/既有斷言以 diff 與實碼驗證。
TESTS_RUN: reconcile hash PASS；git diff/check/signature probes PASS；pytest+獨立 oracle+M-A 兩輪均 timeout/無 receipt。
FAILURES_SEEN: 驗證輪1（並行，5m）與輪2（序列+單 BLAS thread，2.5m）皆無輸出後終止；依 debug 上限停止。
SCOPE_CHANGES: 本委員只新增本檔；未改受審程式/測試/data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 新 kernel/FDR API 尚未接生產；Task 1.3 oracle 算法錯配，數值驗證不可採信。
VERDICT: BLOCK（D-B paired bootstrap 未實作；oracle、M-A、轉紅必跑 receipt 未由本委員取得）

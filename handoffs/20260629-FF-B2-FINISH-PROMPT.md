# 派工:完成 B2(Composer)— 縮窗加速 + 自驗(前次連線斷未收尾)

前次 B2 dispatch cursor 連線斷,測試檔 `tests/feature_engineering/test_ff_fullchain_truncation_mr.py` 已建(394行,Task2.1四段gate+2.2擾動+3 mutant 探針),但**未自跑驗證、未寫 RESULT**。且 `WINDOW_BARS = 2500` 太慢(單測 >8 分,professional_full preset × 2500 bars)。

## 1. 縮窗加速(不弱化不變量)
- `WINDOW_BARS` 2500 → **500**(截斷不變量只需 > max_warmup(~233,W233窗) + TRUNC_K + buffer;500 足夠且保留 professional_full preset 全特徵鏈)。
- 確認 `TRUNC_K` 合理(如 5-10);warmup = estimate_max_warmup_bars 動態取。
- 目標:整個測試檔(含 3 mutant)在 ~5-8 分內跑完。若仍太慢,可減少 mutant 重複的 generate_features 呼叫(共用 full baseline)。

## 2. 自驗(必附輸出)
- `pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py -q` 全綠(含 2.1 四段 gate + 2.2 擾動)。
- **3 個 mutant 探針真紅**:`test_mutation_numba_rolling_center_true_fails`/`_causal_winsor_full_fit_fails`/`_l4_lag_shift_minus_one_fails`——確認注入後截斷 MR 真的 FAIL(章程 §B1.3:注入須真生效)。
- `bash scripts/mutation_probe_check.sh tests/feature_engineering/test_ff_fullchain_truncation_mr.py` PASS。
- 標 `@pytest.mark.requires_kline`(nightly correctness)。

## 3. oracle 獨立性(§B1.2)
- 截斷 MR 的 oracle 是「同資料截斷前後不變」的不變量,非從 generate_features 衍生的期望值——確認沒有拿 full 自身當 trunc 的期望(那是恆等)。比對是 full 的前綴 vs trunc 的前綴,兩次獨立 generate。

收尾:寫 `handoffs/20260627-FF-DEEPAUDIT-B2-RESULT.md`(跑了什麼/通過條件/3 mutant fail 摘要/耗時)。跑 tests/golden 後 git checkout 還原。完成 STATUS: DONE/BLOCKED。

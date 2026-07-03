# slow MR 5F2P — 委員會診斷事實檔（Claude 編）

> 2026-07-03 | receipt：`handoffs/run_receipts/20260703T054245Z-fracdiff-maxlag-mr-green.log`（5 failed, 2 passed, 2:48:05）
> 背景：max_lag 修復（resolver=calibration-derived 50）落地後，xfail 移除首次全鏈實跑。

## 實測事實

1. **PASSED ×2**：`test_mutation_fracdiff_calibration_perturb_fails`、`test_mutation_fracdiff_full_fit_d_star_fails`——既有 fracdiff 護網 mutation 控制健在。
2. **FAILED 類 A（測試 bug，機械修）×3**：三個新 mutation 測試 `test_mutation_fracdiff_maxlag_len_coupling_{truncation,tail,parallel}_fails`
   全敗在 `assert {600, 590}.issubset(lengths_seen)`，實際 `lengths_seen={2081, 2071}`。
   根因：Codex 硬編 600/590，但 fracdiff MR 實際窗長 `_fracdiff_window_bars()=2081`（600 core+warmup）。
   注意：**mutant 本體有效**（內層 pytest.raises 已捕獲 AssertionError），僅外層窗長斷言寫錯。
3. **FAILED 類 B（首次曝光的深層問題）×2**：
   - B1 `test_fracdiff_truncation_invariant`：
     `AssertionError: warmup 1h_L2_Momentum_chunk4.parquet::volume_1h_momentum_MACDEXT-Hist_13-55-13_Momentum_L144 NaN mask mismatch`
     ——warmup 區 [0:warmup) 全/截 NaN mask 不一致，**非 fracdiff 欄**（無 _fracdiff 後綴）。
     斷言點：`ff_truncation_mr_helpers.py::_assert_warmup_nan_masks_equal`（:845-897）→ `_assert_arrays_values_close`（:718-728 NaN mask exact）。
   - B2 `test_fracdiff_tail_perturbation_invariant`：
     `fracdiff values 1h_L1_statistics_VAR_L65.parquet::volume_1h_statistics_VAR_144_fracdiff`
     `Mismatched elements: 1/20; Max abs diff 4.7683716e-07`（gate atol=1e-8, rtol=0）。
     4.77e-07 ≈ float32 eps 量級；尾擾 MR 語意=擾動 calibration 之後的尾端 bars，前綴 fracdiff 應因果不變。
4. **這兩個斷言先前從未真正執行過**：修復前該兩測試在更早的 d\* gate 就紅（xfail 遮蔽），後續 warmup/值斷言不可達。
   主 MR（fracdiff/adf 關閉、8 passed@20260702T042627Z）同欄檢查過且綠——**問題僅在 fracdiff/adf 開啟的 config 下出現**。
5. 修復本體檢驗點全綠：d\* gate 已不再是失敗點（兩窗 resolved max_lag 同=50）；B0 golden §G 條件過；快測 15 passed。
6. mutation probe checker 7 探針過（20260703T053419Z receipt）。

## 待診斷（委員會）

- **Q1（B1）**：fracdiff/adf 開啟 config 下，MACDEXT-Hist momentum 欄 warmup 區 NaN mask 為何隨總窗長（2081 vs 2071）變？
  候選：adf_differencing 決策/差分路徑的長度依賴、Layer B sanitize over-cap 邊界、其他 len 耦合殘留（Task 1.4 掃描聲稱僅 resolver 一處——若另有，掃描結論被推翻）。
- **Q2（B2）**：尾擾下前綴 fracdiff 單元素 4.77e-07 漂移=？候選：parallel reduction 非決定性、float32 捨入路徑差、真因果洩漏（機率低但不得排除）。
- **Q3**：B1/B2 是「本 epic 引入」還是「pre-existing 被 xfail 遮蔽」？判準：這兩斷言在修前不可達；主 MR 綠只證 fracdiff-off config。若 pre-existing → 定性+是否隨本 epic 修 or 另立案（使用者定序 epic 完成後要重生成 FF 給 IC，殘留截斷變異影響簽核範圍聲明）。
- **Q4（類 A）**：三個 mutation 測試窗長斷言修法——由 `_fracdiff_window_bars(config)` 推導期望集合 `{W, W-10}`，禁再硬編。

## 邊界
- 不得放寬 helper 斷言（atol/NaN exact）換綠。若 B2 定性為良性 float 非決定性，修法必須走「消除非決定性來源」或「委員會+使用者知情的 documented 容差決策」，不准靜默放寬。

## Claude 腿（獨立診斷假說，兩腿派出後、未讀其結論前寫）

**Q1/B1 首選假說：ADF 決策的 tail-slice 長度依賴（pre-existing）**。
2026-07-02 DSTAR-GATE-COMPOSER 腿曾記載：「parallel `_statsmodels_adf_pvalue` 用 tail slice、serial/fast 用 head——路徑不一致」。
若 adf_differencing 對該欄的 I(0)/I(1) 判定在 parallel 路徑吃 **tail 500 bars**，則 2081 vs 2071 窗 tail 不同
→ 邊界欄 p-value 跨閾值翻面 → 是否差分翻面 → 前導 NaN band ±1 → warmup NaN mask mismatch。
可證偽檢查：dump 該欄兩窗的 ADF p-value 與差分決策；若同→假說死，查 sanitize over-cap 邊界。
定性預測：**pre-existing**（與 max_lag 修復無關；xfail 遮蔽至今）。

**Q2/B2 首選假說：float32 捨入/並行 chunk 邊界，非洩漏**。
4.77e-07=2^-21≈float32 ulp@~1.0；1/20 抽樣元素、且 d\* 已同窗同值。若為真因果洩漏，預期整段尾側系統性漂移而非單點。
可證偽檢查：①同輸入重跑兩次該欄前綴（n_jobs 同）比對——不穩=非決定性；②該 sampled row 的 index 位置（靠近 chunk/warmup 邊界?）。
定性預測：**pre-existing 數值路徑抖動**；修向=消除來源（如強制該路徑 float64 或固定 chunking），非放寬 atol。

**Q3 判準**（供互審）：兩斷言修前不可達（d\* gate 先紅）+ 主 MR（fracdiff off）同欄綠 → 「本 epic 引入」唯一可能路徑是 max_lag 值改變本身；但 B1 欄非 fracdiff 欄、B2 是 4.77e-7 級──皆與窗寬 60→50 的預期效應（值大改）型態不符。故預測兩者 pre-existing。

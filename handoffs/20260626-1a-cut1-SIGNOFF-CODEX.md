## 簽核結論：有疑,不簽—列洩漏向量

## 我實際跑了什麼（pytest 指令 + 結果 + 任何反例嘗試）

`PYTHONDONTWRITEBYTECODE=1 NUMBA_DISABLE_JIT=1 pytest -s -p no:cacheprovider tests/momentum/Analysis/test_ic_1a_cut1_leakage.py tests/momentum/Analysis/test_ic_1a_cut1_split.py tests/momentum/Analysis/test_ic_1a_cut1_oos.py tests/momentum/Analysis/test_ic_1a_cut1_golden.py tests/momentum/test_factories.py -q --tb=short`

結果：27 collected；24 passed；2 errors；1 failed。  
2 errors 是唯讀環境無可寫 tmpdir 導致 `tmp_path` fixture 建立失敗。1 failed 是 G-OLD 走真實 service 時嘗試寫 `data_cache/reports/ic_report_ic_gatekeeper.json`，被 read-only sandbox 拒絕。這代表我沒有驗到 G-OLD deep equality。

`grep -rE "from api\." momentum/ || true`：0 results。

真實 kline 反例：用 `data_cache/feature_klines/kline_cache.h5` BTCUSDT/1h 220 rows，train=176、purge=5、test=39；只把 purge rows label 改成 `999999.0`。結果 test rolling IC 改變：
clean first5 `[0.2049, 0.1836, 0.1673, 0.0669, 0.2268]`  
altered first5 `[0.0157, -0.1341, 0.0227, 0.0150, 0.2181]`  
ICIR trend 從 `1.3410` 變 `1.1555`。這是 test-scope 指標受 purge label 影響。

winsor 反例：只改 test 段 type-like 值，`winsorize()` 從 skip 變 winsorize，且 train 輸出被改：`-100` 被 clip 到 `-98.0`。

## Findings

[LEAK] Rolling OOS 把 purge rows 放進 test rolling window。  
證據：[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1494) 先用全段 `features_df,label_series` 算 `rolling_ic_full`，再於 [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1822) 只按 test endpoint 切值。這沒有排除 train/test 中間的 purge rows；purge rows 的 forward label 可引用 test 價格，然後進入第一批 test rolling IC/ICIR/passed_features。  
修法：flag-on rolling input 必須排除 purge rows，只允許 train+test allowed rows；切片邏輯要證明每個保留 rolling window 的 constituent rows 不包含 `~train_mask & ~test_mask`。新增真實 BTC/1h 反例測試：擾動 purge labels 不得改變 test rolling IC/ICIR。

[LEAK] `winsorize()` 的 type-feature skip 判斷使用全段資料，test 值可改變 train 輸出。  
證據：[data_preprocessor.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/data_preprocessor.py:100) 對 full `series` 呼叫 `_is_type_feature(series)`，但後續 quantile 才使用 fit_mask。反例中 clean log 是 `skipped=['typeish']`，dirty test-only 值讓 log 變 `winsorized=['typeish']`，並改動 train 值。  
修法：type-feature 判斷也必須基於 fit slice，或改用 metadata/schema 判斷，不能由 test distribution 決定 preprocessing branch。

[MINOR] OOS rolling 測試沒有覆蓋 purge hole。  
證據：[test_ic_1a_cut1_oos.py](/Users/louis/Desktop/quantitative_trading_system/tests/momentum/Analysis/test_ic_1a_cut1_oos.py:39) 的 `_split_context` 設定 `test_mask = ~train_mask`，沒有 purge gap，因此 [test_ic_1a_cut1_oos.py](/Users/louis/Desktop/quantitative_trading_system/tests/momentum/Analysis/test_ic_1a_cut1_oos.py:85) 只驗到「不是純 test rolling」，驗不到 purge contamination。  
修法：測試 context 應用真實 `_build_holdout_split_plan()` 產生的 train/test masks，並擾動 purge rows 做不變量測試。

## code review（跨家族:結構/正確性/可維護性盲點）

結構上 split plan 用 positional、event_filter 後用 time_bounds 重導 mask 的方向是對的；`validate_split_pair_integrity` 也能擋住 train/test row overlap。問題在於 stage4 rolling 是另一條資料路徑，沒有用 split mask 重新組裝 allowed universe，導致 purge semantic 被繞過。

train-only fit 接線不完整：quantile/coverage/constant/std 多數已改成 fit slice，但 preprocessing 裡仍有 branch decision 留在 full data 上。這類「先分類再 fit」的邏輯都需要逐個審，不能只看統計量是否用了 `fit_mask`。

G-OLD 未驗成：本環境 read-only，golden test 真實路徑會寫 `data_cache/reports` 而失敗，所以不能宣稱 flag-off byte 守恆通過。

ASSUMPTIONS_VERIFIED: 真實 BTC/1h kline 存在；rolling purge-row label 擾動會改變 test rolling IC/ICIR；type-feature test-only 擾動會改變 train preprocessing output；momentum 無 `from api.` import。  
TESTS_RUN: 上述 pytest 24 passed / 1 failed / 2 errors；失敗/錯誤為 read-only tmpdir/report writes；另跑兩個 `python -c` 反例，均復現洩漏。  
FAILURES_SEEN: pytest 初次被 no writable tempdir 擋；加 `-s`/`NUMBA_DISABLE_JIT=1` 後仍有 tmp_path 與 report write 限制。  
SCOPE_CHANGES: none。  
NUMERIC_OR_SCHEMA_IMPACT: 審查未改碼；發現現有 flag-on OOS rolling 數值受 purge/test 邊界污染。  
HANDOFF_NOT_UPDATED: read-only sandbox，且本任務要求輸出簽核格式，未寫交接檔。  
STATUS: DONE
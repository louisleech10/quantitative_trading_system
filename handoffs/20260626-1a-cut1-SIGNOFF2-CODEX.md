## R2 簽核結論：資料正確，簽 PASS

## LEAK-1 重驗（反例 + 結果:變/不變）
反例：真實 `data_cache/feature_klines/kline_cache.h5` BTCUSDT/1h，手構 purge hole，僅把 purge rows label 乘以 `-999.0`。

結果：不變。
- `LEAK1_PURGE_ROWS 5`
- `LEAK1_ROLLING_EQUAL True`
- `LEAK1_ICIR_EQUAL True`
- `LEAK1_ALLOWED_EXCLUDES_PURGE True`
- `LEAK1_ROLLING_ENDPOINTS_INTERSECT_PURGE 0`

舊行為模擬確認可證偽：
- `OLD_LEAK1_ROLLING_WOULD_EQUAL False`
- `OLD_LEAK1_ICIR_WOULD_EQUAL False`

## LEAK-2 重驗（反例 + 結果）
反例：train slice 維持 `{-100,0,100}` type-like 值，只把 test 段改成 `1000.0`。

結果：不變。
- `LEAK2_CLEAN_SKIPPED ['type_signal']`
- `LEAK2_DIRTY_SKIPPED ['type_signal']`
- `LEAK2_TRAIN_OUTPUT_EQUAL True`

舊行為模擬確認可證偽：
- `OLD_LEAK2_FULL_CLEAN_IS_TYPE True`
- `OLD_LEAK2_FULL_DIRTY_IS_TYPE False`
- `NEW_LEAK2_FIT_DIRTY_IS_TYPE True`

## 殘留 Findings
無 LEAK 殘留。`embargo=3` 也確認 test start 從 `144+5` 推遲到 `152`，gap rows=`8`。

`G-OLD` pytest 在此 read-only sandbox 失敗於寫入 `data_cache/reports/ic_report_ic_gatekeeper.json`，屬環境權限阻塞，不是 deep-equal assertion diff。`rg -n "from api\\." momentum/` 無匹配。

ASSUMPTIONS_VERIFIED: 真實 kline 存在；purge label 擾動不改 test rolling IC/ICIR；test-only type-like 值不改 winsorize 分支或 train 輸出；舊行為模擬會 FAIL；embargo 推遲 test 起點。
TESTS_RUN: `python -c` R1 反例 PASS；`pytest -s test_ic_1a_cut1_oos.py::{purge,winsorize,embargo}` 3 passed；`pytest -s test_ic_1a_cut1_leakage.py` 5 passed；G-OLD blocked by read-only report write.
FAILURES_SEEN: heredoc/temp blocked；Numba cache blocked until `NUMBA_DISABLE_JIT=1`; G-OLD report persistence blocked by read-only sandbox.
SCOPE_CHANGES: none.
NUMERIC_OR_SCHEMA_IMPACT: none from this R2 verification.
HANDOFF_NOT_UPDATED: read-only sandbox; cannot write SIGNOFF2 file or handoff file.
STATUS: DONE
# Feature Factory 正確性 scoping 稽核

讀取範圍：`HANDOFF.md`、`CLAUDE.md`、`handoffs/20260627-FF-AUDIT-CLAUDE-DRAFT.md`、`docs/TEST_DESIGN_CHARTER.md`，並實讀 FF 核心與測試：`feature_extractor.py`、`operators/*`、`timeframe/*`、`preprocessing/*`、`warmup_window.py`、`feature_validator.py` 及對應測試。

## 總判斷

FF 地基判斷：**有疑，但非不穩**。

原因：MultiTF PIT、L6.5 causal/cache、warmup/NaN 方向已有實質 correctness 資產；但「特徵公式本身」與「全鏈生成期因果」尚未達章程 P0。若 IC 直接把 FF 當完整可信 oracle，現在仍是 **partial confidence**。

## 六軸 Oracle 分級

| GIGO 軸 | 現有最高等級 | 判斷 |
|---|---:|---|
| 1. 特徵計算正確 | **P1/P3 混合** | Derived/rolling 有單點手算 TOLERANCE，例如 [tests/test_feature_factory_operators.py](/Users/louis/Desktop/quantitative_trading_system/tests/test_feature_factory_operators.py:44)；atomic indicator 多數只驗欄位存在/非空，屬 P3 smoke。缺全量 A15 differential。 |
| 2. 生成期因果無前瞻 | **P1 partial** | L6.5 有未來尾端 perturb MR；rolling/lag 實作方向多為過去式。但缺「FF 全鏈截斷未來 bars → 歷史段 bitwise 不變」MR。 |
| 3. 多 TF 對齊 PIT | **P1 強** | `build_asof_index_map` 用 `source_close <= decision_time`，見 [tf_aligner.py](/Users/louis/Desktop/quantitative_trading_system/momentum/FeatureEngineering/timeframe/tf_aligner.py:156)；真 kline golden + path matrix 覆蓋 legacy/CGSA/searchsorted，見 [test_mtf_align_golden.py](/Users/louis/Desktop/quantitative_trading_system/tests/feature_engineering/test_mtf_align_golden.py:257)。缺 mutation probe 和高頻未來截斷 MR，不能升 P0。 |
| 4. L6.5 causal + cache | **P1 強** | `causal_preprocessing=False` 被強制 True，見 [feature_preprocessor.py](/Users/louis/Desktop/quantitative_trading_system/momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:148)。d-star path 含 symbol/timeframe/fracdiff hash，見 [_d_star_cache.py](/Users/louis/Desktop/quantitative_trading_system/momentum/FeatureEngineering/preprocessing/_d_star_cache.py:326)。測試含 causal perturb、native TF、cache isolation/fingerprint。缺人工 mutation 證據。 |
| 5. NaN/inf + warmup | **P1/P2** | near-zero denominator、sanitize、warmup trim 有專門測試；warmup 真 kline integration 覆蓋 row_count/manifest。舊 `FeatureValidator` 測試仍有 fillna 後再驗的 P3 色彩，不能當 correctness gate。 |
| 6. 跨 symbol 隔離 | **P2/P1 partial** | shard/workdir/path 隔離有測；d-star symbol/timeframe 隔離有測。但缺「同一批 symbols 改順序/刪一 symbol/污染一 symbol → 其他 symbol feature bitwise 不變」真 run MR。 |

## 高風險缺口優先序

1. **P0：特徵公式 differential**
   - 補 atomic indicators/operators 的 A15 oracle：TA-Lib/scipy/pandas/manual slow reference。
   - 目前 atomic smoke 僅證明「算得出來」，不證明 RSI/ATR/OBV/advanced indicators 值正確。

2. **P0：FF 全鏈生成期 causal MR**
   - 用真 kline，跑 `generate_features()`。
   - 對尾端未來 bars 做截斷/擾動，assert 截斷點以前 feature matrix 值、NaN mask、columns bitwise/TOLERANCE 不變。
   - 需覆蓋 L1-L6、L6.5、CGSA/non-CGSA、multi-TF。

3. **P0：MultiTF 高頻未來截斷 MR**
   - 章程 §E1 已點名。
   - 現有 no-lookahead 是 map-level 和 golden-level 強證據，但還不是「未來資料不可影響歷史輸出」的完整 MR。

4. **P1：跨 symbol 真 run 隔離**
   - batch A+B vs B+A vs only A。
   - assert A 的 features、metadata、d-star cache hit/miss 語義不受 B 影響。
   - 現有 path/shard 隔離不足以證明計算值隔離。

5. **P1：d-star / fracdiff mutation probe**
   - 人工移除 symbol/timeframe/cache fingerprint 任一欄位，確認隔離測試會紅。
   - 章程 B1 下，沒有 mutation probe 不應標 P0。

## 可能漏的 FF 風險軸

- **TA-Lib wrapper 參數命名與欄位語義 drift**：欄名正確不代表 source/price field 正確。
- **Polars/Numba/Pandas 多路徑等價**：部分已有 L6.5 等價，但 operators/rolling/advanced indicators 還未看到全覆蓋。
- **timestamp 單位邊界**：已有 v2 timestamp golden，但 multi-source/multi-TF 全鏈仍建議納入 causal MR。
- **float16/storage 精度**：storage 有測，但 correctness 任務仍需明確標示是否允許 lossy。

## 收尾

ASSUMPTIONS_VERIFIED: 已實讀 FF 核心碼與測試；確認 MultiTF PIT、L6.5 causal/cache、warmup 有專門測試；確認 atomic/operator 公式 correctness 覆蓋不完整。  
TESTS_RUN: 未跑 pytest；本次為 read-only scoping audit，執行 `sed`/`rg`/`nl` 讀碼取證。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none  
HANDOFF_NOT_UPDATED: sandbox 為 read-only，且專案合約要求 read-only 時不寫交接檔。  
STATUS: DONE
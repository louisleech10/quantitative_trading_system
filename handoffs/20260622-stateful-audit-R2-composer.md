# R2 交叉審 — Composer 2.5（read-only，審超集+Codex handoff）
**日期**: 2026-06-22 | **方法**: 獨立 grep+逐檔讀碼 | **對象**: `docs/FEATURE_STATEFUL_PARAM_AUDIT_MERGED.md`

## ① B2 遞推族 vs OBV/AD
- **異議（細化）**: EMA/MACD/Wilder/KAMA/Klinger **收斂後應歸 D′**（因果遞推+足夠 burn-in 可重算），**非 B「須持久化 state」**；`warmup_table.yaml` 各項 `all_periods_converged: true`（如 EMA:106-114, MACD:160-177, KAMA:151-159）；Klinger=`talib.EMA` 同族（`volume_indicators.py:237-238`）。
- **同意**: OBV/AD **永不收斂**→真 B；`cumulative_special_cases` OBV/AD:367-376 + `talib_wrapper.py:102`。
- **補**: ADOSC 為 cumulative+EMA 混合，yaml:377-381 註「oscillator 收斂」→仍須一致起點，非純 D。

## ② A4 safe_denominator
- **同意** A、低嚴重度；`numeric_guards.py:46-48` 全欄 `nonzero.median()`×1e-6；`derived_operators.py:394,406,415,580` 消費。
- **建議**: **改 causal**（expanding/rolling median）優於留存；僅影響近零分母 NaN 邊界，train/serve 微差。

## ③ S1/S2 schema
- **同意** 獨立 **A-schema**（非 A 子類）：pin 特徵清單非校準參數。S1=`dead_feature_filter.py:77-87` nunique/valid_count；S2=`rolling_aggregator.py:773-788` 全欄 nunique 決定 skew/kurt 是否生成。
- **漏影響**: L3 `_variance_filter` 亦全欄 std/nan_rate 丟欄（`:809-827`），應併入 S1 敘述。

## ④ 窮舉再掃（atomic/operators/preprocessing/labels/validation/native-tf/cross_sectional）
- **同意** 除 A4/A5 無其他**生產路徑**全樣本 median/mean/std/quantile 校準特徵值。
- **附**: `polars_adapter.py:59,350` 複製 A4；`:426-443` 全樣本 winsor **死碼**（`causal_preprocessing=True` 釘死 `:234`）；`feature_validator.py:407-409` fillna(mean) 非預設管線；`.fit()` 僅 `momentum/Analysis/` 非 FF。

## ⑤ A2 IC-First 預設 do_adf
- **異議超集表述**: **FactoryConfig 預設 ADF OFF**（`feature_config.py:175`）；IC-First pre_ic **尊重 config** 不強開（`feature_factory.py:2460-2467`）。
- **開 ADF 條件**: `professional_full` preset（`config_manager.py:1094`）或 golden baseline（`build_l65_golden_baseline.py:146-151`）。測試亦顯式關（`test_ic_first_pipeline.py:46`）。

## ⑥ A5 labels winsor
- **同意** 全樣本 quantile=look-ahead（`label_generator.py:78-79`）；若作訓練 label 會**高估 IC/ML 穩定度**（命中回測真實性 d）。
- **補**: IC-First 預設 label=`pct_change().shift(-1)`（`feature_factory.py:2354`），**不走 winsor**；`generate_all` 未呼叫 winsorized（`:21-29`）→A5 為 opt-in 路徑。

## ⑦ 超集未列新項
| 項 | 類 | 證據 |
|---|---|---|
| SAR | B(stateful_pivot) | `warmup_table.yaml:287-294` |
| L3 variance_filter 丟欄 | A-schema | `rolling_aggregator.py:799-827` |
| polars 非因果 winsor 死碼 | A(不可達) | `polars_adapter.py:426-443` |
| Hurst-prior | A1 子機制 | `_hurst_prior.py:36-77` 校準窗估 H 界 d* |

**R2 結論**: 超集分類大體正確；B2 應從 B 降級為 D′+burn-in；⑤需區分 FactoryConfig 預設 vs preset/golden；⑥區分預設 IC label vs winsorized opt-in。

HANDOFF_NOT_UPDATED: read-only R2 審計

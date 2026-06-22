# R3 最終收斂審 — Composer 2.5（read-only，獨立於 Codex）
**日期**: 2026-06-23 | **對照**: `docs/FEATURE_STATEFUL_PARAM_AUDIT_MERGED.md` + 獨立 grep/讀碼

## A — R2 結論（同意/異議+證據）
| 項 | 裁定 | 證據 |
|---|---|---|
| SAR=B3 | **同意** | `warmup_table.yaml:286-294` `family: stateful_pivot`；非 EMA 遞推族 |
| Hurst-prior=A1子 | **同意** | `_hurst_prior.py:36-77` 校準窗 R/S→`polyfit` 估 H；`:245-276` 僅界 d* 搜尋 |
| ADF 預設 OFF | **同意** | `feature_config.py:174-175` `enabled=False`；IC-First pre_ic 尊重 config(`:2460-2467`) |
| A5 winsor opt-in | **同意** | 全樣本 `quantile`(`label_generator.py:78-79`)；IC 預設 `pct_change.shift(-1)`(`feature_factory.py:2354`) |
| B2 遞推族→D′ | **同意（ADOSC 除外）** | EMA/MACD/Wilder/KAMA `all_periods_converged:true`(`yaml:106-285`)；ADOSC 留 **B**(`yaml:377-381` cumulative+EMA) |
| safe_denom→causal | **同意** | 全欄 `nonzero.median()`(`numeric_guards.py:47-48`)；改 rolling/expanding 優於留存 |
| schema=A-schema | **同意** | L7 `nunique/valid_count`(`dead_feature_filter.py:78-87`)；L3 variance(`rolling_aggregator.py:809-827`)+S2 nunique(`:787-788`) |

## B — E3 Analysis/IC/ML 上線須留存（納入盤點）
**`data_preprocessor.py` 全樣本門檻**（類 A，須 pin 或改 causal）：
- 覆蓋率丟欄 `:114-117`；常數欄 `:121-124`；`time_series_zscore` 欄 mean/std `:135-138`；winsor 分位/MAD/zscore `:151-172`。
**訓練 artifact**（上線必帶）：
- IC 選特徵集 `ic_engine.py:146` → `ic_selected_features_{sym}_{tf}.json`
- 模型權重 LGBM `:237` / XGB `:437`（`feature_names` 同檔）
- 校準映射 `probability_calibrator.py:43-62` fit→`:59` `_model`；`:267-285` `_build_transformer`（Isotonic/Platt 係數）
- **診斷-only**（非預設推論熱路）：PCA/KMeans `factor_centrality_analyzer.py:55-58`、`regime_detector.py:235-248`；VIF `redundancy_filter.py:363-364`

## C — 全層零新增掃描
L0-L7+L6.5+labels：除 merged 表外**無新 A/B/C/D 生產項**；`SAREXT` 同 SAR `stateful_pivot` 族（`talib_wrapper.py:61-62`）yaml 未單列→附註不開類。talib 其餘遞推已在 D′；OBV/AD 真 B。CPCV/WF 有 purge+embargo（`combinatorial_purged_cv.py:181-195`、`walk_forward_validator.py:178`）→方法論非 state。`sample_weight_calculator.py` 訓練權重即時算、非持久 state。`position_sizing.py` 純公式+config，無 `.fit()`。死碼 polars/numba 全樣本 winsor 仍不可達（`causal_preprocessing=True`）。

**C 裁定：FF 特徵管線 CONVERGED**（零新增）；E3 訓練 artifact 已於 B catalog，不計入 FF 零新增。

ASSUMPTIONS_VERIFIED: 上表逐項獨立讀碼 | TESTS_RUN: read-only rg/sed | FAILURES_SEEN: none | SCOPE_CHANGES: none | NUMERIC_OR_SCHEMA_IMPACT: none
HANDOFF_NOT_UPDATED: read-only R3
STATUS: DONE

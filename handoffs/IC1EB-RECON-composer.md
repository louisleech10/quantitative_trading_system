# IC1EB-RECON-composer — 1e HAC/block-bootstrap + 1b FDR 合刀動工前偵察

**TASK_ID**: `ic1eb-recon-composer` | **角色**: 唯讀偵察 | **HEAD**: 當前工作樹 | **日期**: 2026-07-09

---

## §1 p-value 生產→消費全鏈 map

### 1.1 `compute_ic_statistics` caller 圖

| 結論 | Receipt |
|------|---------|
| **生產端唯一實作** | `momentum/Analysis/statistical_validator.py:24-32` — 對 `rolling_ic_dict[feature→windows]` 逐 feature 呼叫 `_collect_values` + `_compute_stats` |
| **生產端唯一生產 caller（orchestrator Stage5）** | `momentum/Analysis/ic_filter_orchestrator.py:2254` — `ic_stats = self._stat_validator.compute_ic_statistics(rolling_ic)` |
| **測試 caller** | `tests/momentum/test_statistical_validator.py:7,84,87` |
| **全 repo 無其他 `.py` caller** | `Grep compute_ic_statistics --glob *.py` → 僅上述 3 檔 |

**演算法**：`statistical_validator.py:118-120` — `mean/(std/√n)` + `scipy.stats.ttest_1samp`（i.i.d. 假設，無 HAC）。

### 1.2 `rolling_ic_dict` 真實結構

| 欄位 | 值 | Receipt |
|------|-----|---------|
| 外層 key | feature 名稱（`str`） | `ic_engine.py:287` `results: dict[str, dict]` |
| 內層 key | `window_{N}`，N 來自 `rolling_windows` | `ic_engine.py:298-302` |
| 內層 value | `list[float]`（每個 rolling 窗末端位置的 IC） | `ic_engine.py:302` |
| 預設窗數 | **3 窗**：`[21, 63, 126]` | `ic_config_schema.py:66`；`ic_engine.py:62` |
| stride | 預設 `1`（相鄰窗高度重疊） | `ic_config_schema.py:67`；`ic_engine.py:1310` `np.arange(0, n_rows-window+1, stride)` |
| 每 feature 窗數 | = `len(rolling_windows)`（預設 3） | 實測見 §2 receipt |
| **重疊來源** | stride=1 時相鄰 IC 共享 `(window-1)/window` 觀測 | 實測 `overlap_share=0.9524`（window=21） |
| **p-value 輸入序列** | `_collect_values` **串接全部窗**（sorted key） | `statistical_validator.py:78-82` |
| **ICIR/autocorr 輸入序列** | `_select_icir_series` **只取** `window_{icir.window}`（預設 63） | `ic_engine.py:1006-1014`；`icir.window` 預設 63 `ic_config_schema.py:71` |

**實測結構（合成 500 列、窗 [21,63,126]）**：
```
windows_keys ['window_126', 'window_21', 'window_63']
len_per_window {'window_126': 375, 'window_21': 480, 'window_63': 438}
flattened_n_obs 1293   # = 480+438+375，三窗串接後餵 t-test
icir_window_series_len 438
```

### 1.3 Stage5 → `_apply_thresholds` 消費欄位

| 步驟 | 消費欄位 | Receipt |
|------|----------|---------|
| `_stage5_statistical_validation` | `rolling_ic` → `ic_stats`；`icir`；`features_df.columns` | `ic_filter_orchestrator.py:2245-2276` |
| `_build_summary_table` 寫入 | `p_value`（來自 `ic_stats`）；**不含** `t_stat`/`ci_lower`/`ci_upper` | `ic_filter_orchestrator.py:2546-2558` |
| `_apply_thresholds` gate | `row["p_value"]` vs `p_value_max`（`inverse=True` → p ≤ max 通過） | `ic_filter_orchestrator.py:2590-2593` |
| 其他 gate 欄位 | `ic_mean`, `icir`, `ic_hit_rate`, `monotonicity_score`, `coverage`, `long_short_spread` | `ic_filter_orchestrator.py:2584-2617` |
| `p_value_max` 來源 | 預設 `config.thresholds.p_value_max`（0.05）；可被 `event_info["adjusted_p_threshold"]` 覆蓋 | `ic_filter_orchestrator.py:2256-2260`；`ic_config_schema.py:104` |
| `event_info["tier"]` | **讀取但未使用**（`tier = event_info.get("tier")` 死變數） | `ic_filter_orchestrator.py:2255`；`apply_significance_filter` 零生產 caller |

### 1.4 summary_table / report / 前端 schema

| 層 | p_value | t_stat | ci_lower/ci_upper | Receipt |
|----|---------|--------|-------------------|---------|
| `ic_stats`（內部） | ✓ | ✓ | ✓ | `statistical_validator.py:122-127` |
| `summary_table` | ✓ | ✗ | ✗ | `ic_filter_orchestrator.py:2540-2558` |
| `analysis_results`（Stage7） | via summary_table | ✗ | ✗ | `ic_filter_orchestrator.py:2378-2391` |
| `ic_reporter` CSV/JSON | `p_value` only | ✗ | ✗ | `ic_reporter.py:114-119,161,247` |
| `ICFeatureInfo`（types.ts） | `p_value: number` | `t_stat?: number` | ✗ | `frontend/src/lib/types.ts:1994-2006` |
| `ICSummaryTable.tsx` | 直接顯示 `item.p_value` | 有則用；longitudinal 多為 null；cross-sectional 由 ic_mean/icir 推算 | `ICSummaryTable.tsx:75-96,443` |
| cross-sectional 路徑 | **`p_value: None` 硬填** | 前端推算 t_stat | `ic_filter_orchestrator.py:1087-1088` |
| API `ic_models.py` | 無 adjusted/FDR 欄 | — | — | `Grep fdr\|multiple_comparison api/` → 0 |

**`ic_autocorr`**：Stage4 計算並放入 `ic_results`（`:2228`），但 Stage7 `analysis_results` **未輸出**（`:2378-2391` 無 `ic_autocorr` key）。

---

## §2 Rolling IC 計算參數與自相關

| 項目 | 事實 | Receipt |
|------|------|---------|
| 預設 `rolling_windows` | `[21, 63, 126]` | `ic_config_schema.py:66` |
| 預設 `rolling_stride` | `1` | `ic_config_schema.py:67` |
| TF 縮放 | `_adjust_rolling_windows` 依 `icir.reference_tf`（預設 12h）與 metadata timeframe 比例縮放 | `ic_engine.py:1235-1247` |
| ICIR 參考窗 | `icir.window=63` | `ic_config_schema.py:71` |
| `compute_ic_autocorrelation` 算法 | 對 `_select_icir_series`（單窗）算 `np.corrcoef(values[:-lag], values[lag:])` | `ic_engine.py:442-461` |
| 輸出去向 | `ic_results["ic_autocorr"]`；**不進 report/UI** | `ic_filter_orchestrator.py:2183,2228`；Stage7 缺欄 |
| 前端 toggle | `ic_autocorrelation` 在 `PRESET_TOGGLES`；**無 `STAGE_OVERRIDE_PATHS` 映射** | `icAnalysisStore.ts:67,93`；`ic_filter_orchestrator.py:73-79` |

### Lag-1 自相關量級（實測 receipt）

```bash
source venv/bin/activate && python -c "
# 見上文 §1.2 實測腳本
"
# 輸出: icir_window_series_len 438 lag1_autocorr 0.9836239386242467
# overlap_share (window=21, stride=1): 0.9523809523809523
```

| 序列 | lag-1 ρ | 解讀 |
|------|---------|------|
| `window_63` 單窗 IC（ICIR 同源） | **≈0.984** | 極高持久性；i.i.d. t-test 嚴重低估 SE |
| 三窗串接（p-value 實際輸入） | 未單獨測；含跨窗重複時間覆蓋 | `_collect_values` 膨脹 n_obs 至 1293 |

---

## §3 n_tests 現實與 FDR / sample_tier 互動

| 項目 | 事實 | Receipt |
|------|------|---------|
| 一次 run 檢定 feature 數 | `len(features_df.columns)` 經 Stage3 event filter + `_apply_feature_filter` 後 | `ic_filter_orchestrator.py:2269` `features_df.columns` |
| feature 數來源 | HDF5 `feature_names`；無隱式截斷（>5000 只 warn） | `ic_filter_orchestrator.py:2025-2029,2778-2782` |
| `max_features` 截斷 | 可選；`sorted_column_name` 取前 N | `ic_filter_orchestrator.py:2072-2075` |
| tier/scope 分群 | **無**；全欄位同一 BH 家族（若接 FDR） | Stage5 無 SelectionScope |
| `apply_significance_filter` 生產 caller | **零** | `Grep apply_significance_filter --glob *.py` → 僅 `statistical_validator.py` + tests |
| `sample_tier=low_confidence` 邏輯 | `apply_significance_filter` 內 `threshold=max(p_max, 0.10)` | `statistical_validator.py:46-47` |
| 實際 low_confidence 路徑 | `EventFilter.check_sample_size` → `adjusted_p_threshold=0.10` → Stage5 覆蓋 `p_value_max` | `event_filter.py:128-144,93-99`；`ic_filter_orchestrator.py:2257-2260` |
| **與 FDR 互動（現況）** | 兩套機制並存未接線：① event tier 放寬**閾值**；② `apply_significance_filter` 放寬**閾值**；③ `adjust_multiple_comparisons` 調整 **p 值** — ③ 未用 | 見上 |
| **建議接線順序（偵察結論，非實作）** | HAC/block-bootstrap 得 per-feature `p_value` → FDR（`SelectionScope.n_tests`）→ 與 `p_value_max`（含 event tier 放寬）比較 | 邏輯推導；現無代碼 |

---

## §4 SelectionScope 契約與 `adjust_multiple_comparisons`

### 4.1 SelectionScope（`contracts.py:724-742`）

| 欄位 | 型別 | 約束 | Receipt |
|------|------|------|---------|
| `scope_id` | `str` | — | `contracts.py:727` |
| `universe_features` | `List[str]` | superset | `:728` |
| `split_label` | `Literal["train","val","test"]` | 必為三者之一 | `:729,737-738` |
| `evaluated_features` | `List[str]` | ⊆ universe | `:730,739-740` |
| `n_tests` | `int` | == `len(evaluated_features)` | `:731,741-742` |
| `method` | `str` | 測試用 `"benjamini_hochberg"` | `test_scope_contract.py:17` |
| `base_universe_hash` | `str` | — | `contracts.py:733` |

**測試期待**：4 tests 驗欄位、空 evaluated、`evaluated⊄universe` 與 `n_tests` 不一致皆 `ValueError` — `tests/momentum/core/test_scope_contract.py`。

**生產使用**：`Grep SelectionScope momentum/` → **僅 `contracts.py` 定義**，orchestrator 零 import。

### 4.2 `adjust_multiple_comparisons` / `_fdr_bh`

| 項目 | 事實 | Receipt |
|------|------|---------|
| 實作 | Bonferroni + Benjamini–Hochberg（手刻排序+反向累積 min） | `statistical_validator.py:58-73,141-166` |
| 生產 caller | **零**（`momentum/` 僅定義檔） | `Grep adjust_multiple_comparisons momentum/` → 1 檔 |
| 測試 caller | `test_statistical_validator.py:44-57` | 斷言 bonf/fdr 數值 |
| 與 statsmodels 一致性 | **match True** | 實測：`hand_fdr {'a':0.03,'b':0.03,'c':0.5}` vs `statsmodels multipletests fdr_bh` |

---

## §5 FDR 幽靈開關（前後端斷鏈）

| 層 | fdr / multiple_comparison | Receipt |
|----|---------------------------|---------|
| `ic_config_schema.py` | **無** `fdr_correction` / `multiple_comparison` 欄 | `Grep fdr\|multiple_comparison ic_config_schema.py` → 0；僅 `significance_level` 在 deep 模組（trend/quality） |
| `STAGE_OVERRIDE_PATHS` | **無** fdr 映射 | `ic_filter_orchestrator.py:73-79` |
| `icAnalysisStore.ts` PRESET | `fdr_correction: false`（foundation/intermediate）；`true`（advanced） | `:78,104,130` |
| `getEffectiveConfig()` | 只送 `stage_overrides` + `module_overrides`；**不含 fdr_correction** | `:290-325` |
| `FeatureTierPanel.tsx` | L3 toggle `fdr_correction` 標「FDR 多重比較校正」 | `:38` |
| `useICAnalysis.ts` | 送 `feature_tiers`（來自 getEffectiveConfig） | `:235,278-280` |
| 後端 `_apply_tier_config` | 只處理 `stage_overrides`/`module_overrides`/`disabled_modules`；**不讀 fdr_correction** | `ic_filter_orchestrator.py:2882-2931` |

**結論**：Advanced preset 開 FDR toggle → **前後端皆無效**；實際仍 raw per-feature p ≤ 0.05。

---

## §6 HAC 工具面與 effective_horizon 複用點

| 項目 | 事實 | Receipt |
|------|------|---------|
| statsmodels | **已安裝** v0.14.6 | `python -c "import statsmodels; print(statsmodels.__version__)"` → `0.14.6` |
| HAC API | `OLS` + `cov_hac` 可 import | `python -c "from statsmodels...cov_hac; print('OK')"` |
| `BootstrapEstimator` | ML 指標（auc/pr_auc/brier/precision@10）；**i.i.d. 重抽樣**，無 block | `bootstrap_estimator.py:43-52,81-88` |
| 可複用面 | `BootstrapResult` dataclass + CI 分位數框架；**需新 block 邏輯** | 同上 |

### Task 1.2 effective_horizon resolver（1-align 交付）

| 函式 | 簽名 | 位置 | 行為 |
|------|------|------|------|
| `_resolve_effective_label_horizon` | `(config: ICConfig, labels_df: Optional[pd.DataFrame]) -> int` | `ic_filter_orchestrator.py:188-231` | labels 欄名解析優先；無 labels 時 fallback `default_horizon`∈`horizons` |
| `_resolve_label_horizon_from_column` | `(name: str, config: ICConfig) -> int` | `:234-243` | `return_{N}` → N；帶單位欄名 `InvalidInputError` |
| 使用點 | split purge、`min_test_rows`、cross-sectional | `:302,748,989,1835,1918,2136` |

### 1e 複用建議（偵察結論）

- **Newey-West `maxlags`**：應耦合 (a) rolling 窗重疊 `≈ icir.window - 1`（stride=1）與 (b) forward return `effective_horizon - 1`（重疊標籤 MA 結構）。resolver 已為 (b) 單一真相源。
- **Block bootstrap block length**：同源參數；現無現成 block 實作。
- **序列選擇**：HAC 應基於 **單窗 IC 序列**（與 `compute_ic_autocorrelation` 一致），非 `_collect_values` 三窗串接（否則自相關結構混雜）。

---

## §7 deep 路徑 `factor_return_analyzer` — scope 邊界

| 項目 | 事實 | Receipt |
|------|------|---------|
| 硬編 | `"newey_west_adjusted": False` | `factor_return_analyzer.py:103` |
| 路徑 | `run_deep_analysis` → `_run_factor_return` → `FactorReturnAnalyzer.compute_batch` | `ic_filter_orchestrator.py:1572-1578` |
| 前端消費 | `FactorReturnChart` 讀 `quantile_returns_summary`；**不讀** `newey_west_adjusted` | `FactorReturnChart.tsx:19-20`；`types.ts:2219-2228` 無該欄 |
| 與主 gate 關係 | Stage5 `p_value` gate **不經** factor_return | Stage5 vs deep 分離 |

**本刀 scope 依據**：主顯著性鏈為 `compute_ic_statistics` → `_apply_thresholds`（longitudinal gate）。`factor_return` 的 `newey_west_adjusted` 為 deep 模組宣告欄、不影響 passed_features；**建議登記為殘留/後續刀**，非 1e+1b 阻塞項（除非 SPEC 明確擴 scope）。

---

## §8 施工面預估

### 8.1 高概率改動檔

| 檔案 | 改動性質 |
|------|----------|
| `momentum/Analysis/statistical_validator.py` | HAC/block-bootstrap p-value/CI；可能調整 `_collect_values` 策略 |
| `momentum/Analysis/ic_filter_orchestrator.py` | Stage5 接 FDR + SelectionScope；schema 映射；report 欄位 |
| `momentum/Analysis/ic_config_schema.py` | 新增 `fdr_correction` / `multiple_comparison_method` 等 |
| `momentum/core/contracts.py` | SelectionScope 可能擴欄（若需 adjusted_p 語意）；或僅接線 |
| `momentum/Analysis/ic_reporter.py` | 導出 `p_value_adjusted`/`t_stat`/`ci_*`（若 SPEC 要求） |
| `tests/momentum/test_statistical_validator.py` | HAC/FDR 整合測試 |
| `tests/momentum/test_ic_filter_orchestrator.py` | Stage5 E2E |
| `tests/momentum/core/test_scope_contract.py` | SelectionScope 接線測試 |
| `frontend/src/store/icAnalysisStore.ts` | `getEffectiveConfig` 送 fdr |
| `frontend/src/lib/types.ts` | `ICFeatureInfo` 增 adjusted p / method 欄 |
| `frontend/src/components/ic-analysis/ICSummaryTable.tsx` | 顯示 adjusted p（可選） |
| `api/models/ic_models.py` | 若 API 需暴露 FDR 設定 |

### 8.2 契約接線要點

1. **SelectionScope**：`universe_features`=filter 後全欄；`evaluated_features`=有 finite `p_value` 者；`split_label` 對齊 `split_context`（test/full）；`n_tests=len(evaluated)`。
2. **report schema**：決定是否保留 raw `p_value` 並增 `p_value_adjusted`（向後相容）。
3. **event tier vs FDR**：`adjusted_p_threshold` 是閾值放寬，不是 FDR；文件與 UI 須區分。
4. **cross-sectional**：目前 `p_value=None`；合刀需裁定是否納入或維持 exclusion。

### 8.3 不建議本刀動（除非 SPEC 擴大）

- `factor_return_analyzer.py`（deep 路徑）
- `bootstrap_estimator.py`（除非決定擴展為 generic block bootstrap）
- `compute_ic_autocorrelation` 輸出接線（可選增強，非 gate 阻塞）

---

## Receipt 索引表（命令速查）

| # | 命令 | 用途 |
|---|------|------|
| R1 | `Grep compute_ic_statistics --glob *.py` | caller map |
| R2 | `nl -ba statistical_validator.py \| sed -n '24,32p;75,83p;118,128p'` | p-value 生產 |
| R3 | `nl -ba ic_filter_orchestrator.py \| sed -n '2254,2292p;2540,2594p'` | Stage5 消費 |
| R4 | `python` 合成 rolling IC 實測（§1.2） | 結構+lag-1 ρ |
| R5 | `Grep adjust_multiple_comparisons momentum/` | 零生產 caller |
| R6 | `python` FDR vs statsmodels multipletests | BH 正確性 |
| R7 | `python -c "import statsmodels; ... cov_hac"` | HAC 工具 |
| R8 | `Grep SelectionScope momentum/` | 零生產使用 |
| R9 | `Grep fdr api/ momentum/Analysis/ic_config_schema.py` | 後端無 FDR schema |
| R10 | `sed -n '290,325p' frontend/src/store/icAnalysisStore.ts` | 前端不送 fdr |

---

ASSUMPTIONS_VERIFIED:
- `compute_ic_statistics` 生產 caller 僅 `ic_filter_orchestrator.py:2254`（R1）
- `rolling_ic_dict` 為 `feature→{window_N→list}`，預設 3 窗；p-value 用全窗串接、ICIR 用單窗 63（R2-R4）
- `adjust_multiple_comparisons` 生產零 caller；BH 與 statsmodels 一致（R5-R6）
- `SelectionScope` 僅契約+測試，生產零使用（R8）
- statsmodels 0.14.6 + cov_hac 可用（R7）
- 前端 `fdr_correction` toggle 不進 `getEffectiveConfig`；後端 schema 無 fdr 欄（R9-R10）
- `factor_return` `newey_west_adjusted:False` 不進主 gate、前端不消費（§7 讀碼）

TESTS_RUN:
- `python -c "import statsmodels; print(statsmodels.__version__)"` → 0.14.6
- `python -c "from statsmodels...cov_hac"` → OK
- `python` 合成 rolling IC 結構+lag-1 實測 → ρ≈0.984, flattened_n_obs=1293
- `python` FDR hand vs statsmodels → match True
- `nl/sed` 讀碼 receipt R2-R3, R8-R10
- 未跑 pytest（唯讀偵察任務）

FAILURES_SEEN: none

SCOPE_CHANGES: none（唯讀）

NUMERIC_OR_SCHEMA_IMPACT: 無改動；偵察發現未來刀可能影響 summary_table/report/types（增 `p_value_adjusted`、`t_stat`、`ci_*`；FDR config schema）

STATUS: DONE

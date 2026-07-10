# IC1EB-B2-IMPL-RESULT — Task 2.1–2.5 縱向主路徑接線

**Agent**: Grok 4.5 | **Date**: 2026-07-10 | **Status**: DONE  
**SPEC**: `docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` v2.2 | **TODO**: Phase 2 Task 2.1–2.5  
**Prompt**: `handoffs/IC1EB-B2-IMPL-PROMPT.md` | **基底**: B1 `c0b29ac`

## 改檔清單

| 檔案 | 變更 |
|------|------|
| `momentum/Analysis/statistical_validator.py` | `compute_ic_statistics` → `compute_pooled_ic_statistics_deprecated`；**刪** `apply_significance_filter` |
| `momentum/Analysis/ic_filter_orchestrator.py` | stage5 接 HAC+`apply_fdr`+α 政策+SelectionScope；summary 增 `t_stat`/`p_value_adj`；p 閘消費 q；threshold_log/metadata 新欄 |
| `momentum/Analysis/ic_reporter.py` | CSV 末尾增 `t_stat`/`p_value_adj`；JSON NaN→null；metadata significance 清洗 |
| `momentum/core/contracts.py` | `SelectionScope.split_label` 擴 `"full"` |
| `tests/momentum/test_ic_1eb_b2_wiring.py` | **新建** T-2.1a/b/c、T-2.2a–d、T-2.3b、T-2.4、T-2.5 + mutation |
| `tests/momentum/test_statistical_validator.py` | 語意遷移：pooled 改名；刪 ghost filter 測試（語意併入 T-2.2c） |
| `tests/momentum/test_ic_filter_orchestrator.py` | stage5 α 政策斷言；`_apply_thresholds` 補 `p_value_adj` |
| `tests/momentum/core/test_scope_contract.py` | T-2.3a：`full` + 舊三 label |
| `tests/golden/ic_phase1_1a_cut1/baseline_{old,new}_*.json` | **gitignored** 本地重凍（HAC+FDR 行為變更；僅本機/CI 有檔才驗） |

**未改（禁項）**：rolling_ic/icir/ic_decay/grouped_ic 計算；cross_sectional（B3）；`factories.py`/`protocols.py`；`handoffs/ic1eb_baseline/` 唯讀；`data_cache/` 無 tracked 改動。

---

## 實作要點（對 SPEC D-C/D-D/D-E/D-F/D-G）

1. **Task 2.1**：`_stage5` 呼叫 `compute_hac_ic_statistics(features_for_stats, label_for_stats, horizon)`；horizon=`split_context["effective_horizon"]` 或 `_resolve_effective_label_horizon(config, None)`。
2. **Task 2.2**：全 evaluated 集 `apply_fdr` 先於門檻；α：sufficient/marginal→`p_value_max`，low_confidence→`max(p,0.10)`；`alpha_source`/`selection_mode`；p 閘 fdr on→`p_value_adj`，off→`p_value`。
3. **Task 2.3**：`SelectionScope(split_label=test|full, evaluated=finite p, n_tests=len(evaluated))` 入 report metadata。
4. **Task 2.4**：canonical `significance.fdr.{enabled,method,alpha_effective}` + `maxlags/n_tests/scope_id/tested_estimator/fdr_assumption_note`；note=`BH assumes PRDS; correlated features may yield slight FDR optimism`。
5. **Task 2.5**：ghost 函式刪除，grep 0。

FDR 預設 ON；測試可用 `orchestrator._fdr_enabled_override`（B4 接 schema 前）。

---

## 驗收命令 receipt

### Gate A — full momentum

```bash
source venv/bin/activate
pytest tests/momentum/ -q
```

**結果**：`1015 passed, 3 skipped, 1772 warnings in 208.39s`

### Gate B — 解耦

```bash
grep -rn "from api\." momentum/ | wc -l
```

**結果**：`0`

### Gate C — ghost 殘留

```bash
grep -rn "apply_significance_filter" momentum/ tests/ | wc -l
```

**結果**：`0`

### T-2.x 子集

```bash
pytest tests/momentum/test_ic_1eb_b2_wiring.py tests/momentum/core/test_scope_contract.py -v --tb=line
```

**結果**：`18 passed in 5.14s`

---

## 各 T-2.x receipt

### T-2.1a — stage5 p = kernel 直算

- 合成 n=300,h=5；summary/ic_stats 的 p/t 與 `compute_hac_ic_statistics` allclose(atol=0)。**PASSED**

### T-2.1b M-F 雙腿

| 腿 | 結果 |
|----|------|
| A HAC | stage5 p == kernel p |
| B monkeypatch → deprecated pooled | p 分離 → 同判斷言 FAIL（可證偽） |

**真紅輸出（atol=0）**： VERIFY:ic1eb-b2-mutation-probe 〔SUPERSEDED:mutation 紅燈屬轉紅驗證,還原後由 ic1eb-b2-full-gate 綠收據取代〕
```
MF_TURN_RED: hac_p=4.062184651708168e-28 pooled_p=1.763601173739493e-204 isclose_atol0=False
```

### T-2.1c M-H 結構

- orchestrator 源碼含 `compute_hac_ic_statistics`、無 `compute_ic_statistics` / pooled 呼叫
- `StatisticalValidator` 無 `compute_ic_statistics` 屬性；stage5 AST 無 `_collect_values`

### T-2.2a M-B FDR 雙場景

- 獨立 null 40+5 true ×40 seeds；相關 null（ρ≈0.7、factor⊥y）50+5 ×40 seeds
- mean FDR ≤ 0.20 允收帶（α=0.10）**PASSED**
- **n_tests 縮水 mutation 真紅**： VERIFY:ic1eb-b2-mutation-probe 〔SUPERSEDED:mutation 紅燈屬轉紅驗證,還原後由 ic1eb-b2-full-gate 綠收據取代〕
```
MB_TURN_RED: correct_mean_fdr=0.13973214285714283 (n=40)
             shrink_mean_fdr=0.3756389443889444 (n=40)
             assert_mut_worse=True
```

### T-2.2b M-D scope 錯配

- train 段算 q vs test 段 stage5 q 可分離 **PASSED**

### T-2.2c α 六格

| tier | fdr | alpha_effective | alpha_source | selection_mode |
|------|-----|-----------------|--------------|----------------|
| sufficient | on/off | 0.05 | threshold_default | — |
| marginal | on/off | 0.05 | threshold_default | — |
| low_confidence | on/off | 0.10 | event_tier_low_confidence | exploratory_low_confidence |

+ 遷移：p=0.08 過 low_confidence、p=0.12 不過。**PASSED**

### T-2.2d threshold_log

含 `alpha_effective` / `n_tests` / `fdr_enabled` / `alpha_source`；`n_tests==len(evaluated)`。**PASSED**

### T-2.3a 契約

`full` 合法；train/val/test 不變；未知 label raise。**PASSED**

### T-2.3b selection_scope + mutation

- stage5 產 `SelectionScope`；metadata 含 dict
- **mutation 真紅**： VERIFY:ic1eb-b2-mutation-probe 〔SUPERSEDED:mutation 紅燈屬轉紅驗證,還原後由 ic1eb-b2-full-gate 綠收據取代〕
```
T23B_TURN_RED: ValueError: n_tests must match len(evaluated_features)
```

### T-2.4 reporter

- CSV 舊 14 欄順序不變；`t_stat`/`p_value_adj` 在 `max_correlation` 之後
- JSON `significance.*` 完整；NaN→null

### T-2.5

grep 0；無 method 定義。**PASSED**

---

## 語意遷移列帳（既有測試）

| 原測試/斷言 | 處置 | 理由 |
|-------------|------|------|
| `test_compute_ic_statistics_matches_ttest` | 改名呼叫 `compute_pooled_ic_statistics_deprecated`；數值斷言**未放寬** | 舊函式改名，語意保留供對照 |
| `test_compute_stats_edge_cases` | 同上 | 同上 |
| `test_apply_significance_filter_*`（3 則） | **刪**；low_confidence 語意併入 `test_t22c_alpha_policy_six_cells` | Task 2.5 禁 stub；α 政策單一出口 |
| `test_stage5_statistical_validation_adjusted_p_threshold` | 改斷言「adjusted_p **不再**覆蓋 p_value_max」+ α=p_value_max | D-E 廢除舊覆寫語意 |
| `test_apply_thresholds_missing_and_long_short` | 列補 `p_value_adj`；呼叫加 `fdr_enabled=True`；**移除原因斷言不變** | FDR on 消費 q 欄 |
| cut1 golden deep-equal | **本地 gitignored baseline 重凍** | 行為變更型：p/t/q/metadata 合法變更；非顯著性欄仍由 B5 G-1 五 hash 把關 |

---

## 邊界結果

- 短序列 HAC fail-closed → p=NaN → p 閘 fail（非 raise 整 run）
- 全 p=NaN → n_tests=0、SelectionScope 合法
- FDR off 唯一真相：`significance.fdr.enabled=false`（測試 override 可達）
- cut1 golden 檔 gitignored：CI/本機需有重凍檔才過；repo 不追蹤

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
  - stage5 生產路徑僅 compute_hac_ic_statistics；horizon 同源 resolver/split_context
  - FDR 對全 evaluated 先於 ic_mean/icir 閘；n_tests=len(finite p)
  - α 政策三檔+六格標記；禁 adjusted_p_threshold 覆寫
  - SelectionScope full/test + n_tests 契約 raise
  - reporter 舊 CSV 欄序不變、新欄追加；significance 節 canonical
  - apply_significance_filter 全樹 0 殘留

TESTS_RUN:
  - pytest tests/momentum/ -q → 1015 passed, 3 skipped (208.39s)
  - pytest tests/momentum/test_ic_1eb_b2_wiring.py tests/momentum/core/test_scope_contract.py -v → 18 passed
  - grep from api. momentum/ → 0
  - grep apply_significance_filter momentum/ tests/ → 0

FAILURES_SEEN:
  - cut1 golden deep-equal 初紅 → 重凍 gitignored baseline 後綠
  - M-F 初版 np.bool_ is False 誤判 → bool() 修正
  - M-B 相關 null 誤用 y-factor → 改獨立 null_factor 後 FDR 入帶

SCOPE_CHANGES: none（未碰 factories/protocols/xsec/B4 schema）
NUMERIC_OR_SCHEMA_IMPACT:
  - summary_table 增 t_stat/p_value_adj；p_value 語意=HAC raw（非 i.i.d.）
  - report metadata 增 significance/selection_scope/alpha_source
  - threshold_log 增 alpha_effective/n_tests/fdr_enabled/alpha_source[/selection_mode]
  - CSV 追加兩欄於末尾；passed_features 集合因 HAC+FDR 改變（預期行為變更）
```

STATUS: DONE

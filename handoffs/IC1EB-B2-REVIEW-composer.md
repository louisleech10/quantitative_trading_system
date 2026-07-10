# IC1EB-B2-REVIEW — Composer 委員審查（B2 Task 2.1–2.5）

**Reviewer**: Composer | **Date**: 2026-07-11 | **實作者**: Grok（本審查非作者）  
**對象**: 工作樹未 commit diff（`ic_filter_orchestrator.py` / `ic_reporter.py` / `statistical_validator.py` / `contracts.py` + tests）  
**規格**: `docs/IC_PHASE1_1E1B_SIGNIF_TODO.md` Phase 2 + SPEC §A D-C/D-D/D-E/D-F/D-G + §C consumer map  
**實作者自報**: `handoffs/IC1EB-B2-IMPL-RESULT.md`（未採信，獨立驗證）

---

## 審查方法

- 讀 diff + 生產路徑原始碼（`_stage5_statistical_validation` / `_apply_thresholds` / `_build_report_metadata` / `apply_fdr`）
- 獨立實跑：`pytest tests/momentum/test_ic_1eb_b2_wiring.py tests/momentum/core/test_scope_contract.py`（18/18）
- 獨立實跑 M-B：`test_t22a_mb_fdr_control_independent_and_correlated` + mutation receipt（2/2）
- 獨立實跑：`pytest tests/momentum/ -q` → **1015 passed, 3 skipped**（213s）
- 獨立實跑：`pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py`（2/2，本地 gitignored baseline 存在時）
- 結構 grep：`from api.` momentum=0；`apply_significance_filter`=0；生產樹無 `compute_pooled_*` / `compute_ic_statistics` caller

---

## 逐項審查

### (1) FDR 時序：全 evaluated 先於任何門檻 — **PASS**

**讀碼證據**（`ic_filter_orchestrator.py` `_stage5_statistical_validation`）：

1. `compute_hac_ic_statistics` → 對 `features_for_stats.columns` 全欄建 `p_values`
2. `apply_fdr(p_values, alpha_effective)` **先於** `_build_summary_table` 與 `_apply_thresholds`
3. `_apply_thresholds` 才依序過 `ic_mean` / `icir` / `p` 閘

**可證偽反例**（已實跑轉紅 receipt）：

- `test_t22a_mb_fdr_control_independent_and_correlated` 內 `shrink_n_tests=True`：僅對 `p<0.2` 子集做 BH（模擬 selection-conditioning）
- 同 seed 帶下 `mean_mut > mean_ind`（獨立 null，α=0.10，40 seeds）→ 子集 FDR 確實劣化
- 生產路徑未做子集篩選；`universe_features = list(features_for_stats.columns)` 與 `evaluated_features = [finite p]` 同源

**設計反例（紙面）**：若把 FDR 移到 `_apply_thresholds` 通過 ic_mean/icir 之後，`n_tests` 會隨前置閘縮水 → M-B mutation 路徑已證明 FDR 膨脹；生產碼無此順序。

---

### (2) α 政策六格 + `alpha_source` / `selection_mode` — **PASS**

**讀碼**：`_resolve_alpha_policy` — sufficient/marginal→`p_value_max` + `threshold_default`；low_confidence→`max(p,0.10)` + `event_tier_low_confidence` + `exploratory_low_confidence`；**不再**讀 `adjusted_p_threshold`。

**實跑**：`test_t22c_alpha_policy_six_cells` 六格（tier×fdr on/off）斷言 `alpha_effective` / `alpha_source` / `fdr_enabled` / `selection_mode`（low 檔才有）+ low_confidence p=0.08/0.12 遷移語意。

**可證偽反例**：`test_stage5_statistical_validation_adjusted_p_threshold` 保留 `adjusted_p_threshold=0.2` 但斷言 `alpha_effective == config.thresholds.p_value_max`（≠0.2）→ 舊覆寫語意已廢。

---

### (3) SelectionScope：evaluated=finite p / n_tests mutation / full 擴充 — **PASS**

**契約**（`contracts.py`）：`split_label` 擴 `"full"`；`__post_init__` 仍 `n_tests == len(evaluated_features)` + evaluated ⊆ universe。

**生產接線**：`evaluated_features = [f for f in universe_features if np.isfinite(p)]`；`n_tests` 來自 `apply_fdr`；stage5 內二次 assert；`split_label = "test" if split_context else "full"`。

**實跑**：

- `test_scope_accepts_full_split_label` / `test_scope_rejects_unknown_split_label`（T-2.3a）
- `test_t23b_*`：`n_tests+1` → `ValueError: n_tests must match len(evaluated_features)`（真紅）

**可證偽反例**：人為 `SelectionScope(..., n_tests=len(evaluated)+1)` → 契約 raise（見上）。

---

### (4) Reporter canonical `significance.*` + 舊欄 byte — **PASS**

**讀碼**（`ic_reporter.py`）：

- CSV：`base_columns` 前 14 欄順序不變；`t_stat` / `p_value_adj` **僅追加於 `max_correlation` 之後**
- JSON metadata：canonical `significance.fdr.{enabled,method,alpha_effective}` + `significance.{maxlags,n_tests,scope_id,tested_estimator,fdr_assumption_note}`；無 `fdr_enabled` 平鋪別名
- NaN → `null`（`_jsonable_scalar` / `_sanitize_summary_table_for_json`）

**實跑**：`test_t24_reporter_new_columns_and_old_order_byte` — 舊欄序 + significance 節 + NaN null。

**可證偽反例**：若 CSV 把 `t_stat` 插入 `p_value` 與 `ic_hit_rate` 之間 → `cols[:14]==old_columns` 失敗；若 metadata 用 `fdr_enabled` 頂層別名取代 `significance.fdr.enabled` → T-2.4 斷言失敗。

**註**：`threshold_log.fdr_enabled` 為 D-G 允許之 canonical 鏡像；report metadata 頂層 `alpha_source`/`selection_mode` 符合 D-E 明示。

---

### (5) M-B 相關 null（ρ≈0.7）— **PASS**（reviewer 重跑）

**實跑**（本機）：

```bash
pytest tests/momentum/test_ic_1eb_b2_wiring.py::test_t22a_mb_fdr_control_independent_and_correlated \
       tests/momentum/test_ic_1eb_b2_wiring.py::test_t22a_mutation_shrink_n_tests_turns_red_receipt -v
# 2 passed in 4.23s
```

- 獨立 null：40 null + 5 true × 40 seeds，`mean_ind ≤ 0.20`
- 相關 null：50 null（共用 `null_factor`，ρ≈0.7，與 y 獨立）+ 5 true × 40 seeds，`mean_cor ≤ 0.20`
- mutation：`mean_mut > mean_ind`（子集 BH）

---

### (6) cut1 golden 重凍程序 — **PASS（附 NON-BLOCKING 觀察）**

**事實**：

- `tests/golden/ic_phase1_1a_cut1/baseline_{old,new}_*.json` gitignored；mtime **2026-07-11 00:10**（B2 同期重凍）
- 程序 = 重跑 `ICAnalysisService` 全報告 → deep-equal（僅豁免 `generated_at`）；**非** significance-only diff
- `baseline_old` 抽樣：含 `significance.*` / `selection_scope.split_label=full` / summary 新欄 `t_stat,p_value_adj`（post-B2 簽名）
- `baseline_old` vs `baseline_new` 的 `ic_mean` 等大量差異 **預期**（flag off 全樣本 vs flag on test 段），不能互相比對

**實跑**：`test_ic_1a_cut1_golden.py` 兩腿 **2/2 passed**（43s）

**結論**(VERIFY-EXEMPT:doc-example:committee-analysis-prose)：重凍反映 **整份報告** 在新 HAC+FDR 語意下的可重現快照（含新增欄/ metadata），不是僅 p 族欄位 diff。非顯著性欄不變性 **應** 由編排端已驗 G-1 五 hash（`handoffs/ic1eb_baseline/`）把關，非 cut1 golden 職責。程式 review：`ic_mean/icir` 仍來自 `icir` dict（rolling 路徑 diff 未觸及）。

**NON-BLOCKING**：cut1 重凍無「significance-only delta 報告」；若未來需審計，應附 G-1 五 hash receipt 與重凍同一 commit。

---

### (7) pooled deprecated 無生產 caller（M-H）— **PASS**

```bash
grep -rn "compute_pooled_ic_statistics_deprecated\|compute_ic_statistics" momentum/ --include="*.py"
# 僅 statistical_validator.py 定義
grep -rn "from api\." momentum/ | wc -l  # 0
```

- `test_t21c_mh_structure_no_pooled_in_production`：orchestrator 源碼 / AST 無 pooled / `_collect_values`
- 測試側：`test_statistical_validator.py` 改名呼叫 deprecated；`test_ic_1eb_b2_wiring.py` M-F leg B monkeypatch 對照

---

### (8) B1 兩條 NON-BLOCKING 在 FIX1/B2 處置 — **確認**

| B1 NON-BLOCKING | B2 處置 | 判定 |
|-----------------|---------|------|
| T-1.1a 缺 explicit `maxlags` 合法 override 成功路徑 | **未補**；B2 wiring 無此用例 | **仍 OPEN，NON-BLOCKING**（M-C 偏 mutation；kernel 已有 raise 斷言） |
| `apply_fdr` 的 `alpha` 參數 ceremony（`del alpha`） | **未改**；stage5 正確直呼模組級 `apply_fdr` | **仍 OPEN，NON-BLOCKING**（SPEC Task 1.2 簽名保留；α 只在 `_apply_thresholds` 消費） |

---

## 語意遷移 / 防假綠 spot-check

| 變更 | 審查 |
|------|------|
| 刪 `apply_significance_filter` + 3 則測試 | grep=0；low_confidence 併入 T-2.2c ✓ |
| `test_compute_ic_statistics_*` → deprecated 改名 | 數值斷言未放寬 ✓ |
| `test_apply_thresholds_*` 補 `p_value_adj` + `fdr_enabled=True` | 移除原因斷言不變 ✓ |
| `adjusted_p_threshold` 測試 | 改驗「不再覆寫」非刪除監控 ✓ |

---

## Reviewer 驗收命令摘要

```bash
source venv/bin/activate
pytest tests/momentum/test_ic_1eb_b2_wiring.py tests/momentum/core/test_scope_contract.py -q
# 18 passed

pytest tests/momentum/test_ic_1eb_b2_wiring.py::test_t22a_mb_fdr_control_independent_and_correlated -v
# 1 passed (M-B 含 correlated null)

pytest tests/momentum/ -q
# 1015 passed, 3 skipped

grep -rn "from api\." momentum/ | wc -l          # 0
grep -rn "apply_significance_filter" momentum/ tests/ | wc -l  # 0
```

---

## 結構化摘要

```
ASSUMPTIONS_VERIFIED: FDR 全 evaluated 先於門檻；α 六格；SelectionScope 契約；reporter canonical；M-H 無 pooled caller；M-B ρ≈0.7 — 均已讀碼+實跑
TESTS_RUN: B2 wiring 18/18；M-B 2/2；momentum 1015/1015；cut1 golden 2/2（本地 baseline 存在）
FAILURES_SEEN: none
SCOPE_CHANGES: reviewer 未改碼（僅本檔）
NUMERIC_OR_SCHEMA_IMPACT: 與實作一致 — summary 增 t_stat/p_value_adj；metadata 增 significance/selection_scope；p_value 語意=HAC raw；passed_features 集合預期變更
FINDINGS_BLOCKING: 0
FINDINGS_NONBLOCKING: 2（B1 maxlags 成功路徑仍缺；apply_fdr alpha ceremony 仍 del）；1（cut1 重凍為全報告快照非 sig-only diff，依 G-1 外部 gate）
```

VERDICT: PASS

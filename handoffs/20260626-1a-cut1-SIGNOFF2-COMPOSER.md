# 1a 第一刀 — 三方數據簽核 R2（Composer 2.5 獨立腿，非作者）

> R1 reconcile 列 2 真 LEAK（Codex 反例）+ embargo 未接線。本腿**不信 pytest 綠燈**，獨立重跑 R1 手構反例 + 模擬修補前路徑驗可證偽性。

## R2 簽核結論：資料正確，簽 PASS

LEAK-1（purge rows 污染 test rolling IC/ICIR）與 LEAK-2（test 值翻轉 winsorize type 分支）經**獨立重驗真關閉**；embargo 已接線；flag-off G-OLD deep-equal PASS；解耦 0。cut1 主流程 `analyze()` 可進 G-NEW 凍結與 default ON 流程。

---

## LEAK-1 重驗（反例 + 結果:不變）

**R1 反例（Codex）**：BTC/1h 220 rows，train=176、purge=5、test=39；只把 purge rows 的 `label` 改成 `999999.0` → test rolling IC first5 與 ICIR trend 皆變（ICIR 1.34→1.16）。

**R2 獨立重跑**（真實 kline `data_cache/feature_klines/kline_cache.h5`，同切分語意 `_build_holdout_split_plan` + `_derive_stage_masks`）：

| 探針 | 結果 |
|------|------|
| purge label ×-999 / 999999 擾動 | **不變** — `rolling_ic` deep-equal、`icir` deep-equal |
| ICIR trend | clean=0.3243, dirty=0.3243, Δ=0 |
| rolling 輸入 universe | `allowed_mask = train \| test`；purge 行 **不在** allowed（215/220，gap=5） |
| 程式錨點 | `ic_filter_orchestrator.py:1503-1509` 先 `_slice_by_mask(..., train\|test)` 再 `compute_rolling_ic` |

**修補前模擬**（全段 rolling + 僅 test endpoint 切片，等同 R1 bug）：purge label 擾動 → rolling_ic **變**、ICIR 0.3662→0.3040 → `test_purge_label_mutation_*` **會 FAIL**。

**裁決**：LEAK-1 **真關閉**。

---

## LEAK-2 重驗（反例 + 結果:不變）

**R1 反例（Codex）**：train 段 type-like 值 ∈ {-100,0,100} → `skipped=['typeish']`；只把 test 段改成極端值 → 分支翻成 winsorize，train 輸出被 clip（-100→-98）。

**R2 獨立重跑**（真實 kline 180 rows + holdout masks）：

| 探針 | 結果 |
|------|------|
| test-only `typeish=1000` | `skipped_winsorization` 仍 `['typeish']`，與 clean **相同** |
| train 輸出 | `pd.testing.assert_series_equal` **PASS** |
| 程式錨點 | `data_preprocessor.py:102-103` `_is_type_feature(_select_fit_series(...))` |

**修補前模擬**（`_is_type_feature` 用全段 series）：clean skipped=`['typeish']`，dirty skipped=`[]` → `test_winsorize_type_branch_*` **會 FAIL**。

**裁決**：LEAK-2 **真關閉**。

---

## 其他必驗項

### embargo
- `embargo=0` test start=149；`embargo=3` test start=152；Δ=3 ✓
- `test_holdout_embargo_delays_test_start` PASS
- 錨點：`ic_filter_orchestrator.py:160` `test_rows = arange(split_point + effective_purge + effective_embargo, ...)`

### 新測試可證偽性（非 smoke）
- `test_purge_label_mutation_does_not_change_test_rolling_ic`：用真實 purge gap（`~(train\|test)` 非空），assert `rolling_ic` + `icir` 全等；修補前模擬會 FAIL ✓
- `test_winsorize_type_branch_uses_train_slice_only`：assert 分支 + train slice 不變；修補前模擬會 FAIL ✓

### 無新洩漏 / 回歸
```bash
pytest tests/momentum/Analysis/test_ic_1a_cut1_{split,leakage,oos,golden}.py \
       tests/momentum/test_factories.py -v --tb=short
# → 30 passed in 7.53s（含 test_flag_off_deep_equal_baseline G-OLD）

grep -rE "from api\." momentum/  # → 0
bash scripts/check_decoupling_phase4.sh  # → PASSED (135 tests)
```

### 防假綠
- 1a 測試為新檔；未見既有 tracked 測試斷言放寬/刪除。

---

## 殘留 Findings（不阻 R2 PASS，§N / cut2 follow-up）

1. **次路徑 scope**：`reanalyze_with_thresholds` / deep analysis 仍不帶 `split_context`（R1 Composer #2，cut2）。
2. **stage4 `label_series` 全段回傳**：主鏈 stage5 已 slice；介面不一致（R1 Composer #3）。
3. **mock stage5 測試**：`test_summary_and_threshold_same_scope` 等仍用 mock `ic_results`，未走 stage4→5 真鏈（可維護性，非洩漏）。

---

```
ASSUMPTIONS_VERIFIED: 真實 kline BTC/1h 存在；purge gap=default_horizon=5；R1 反例參數可復現
TESTS_RUN: pytest 1a cut1 30/30 PASS; decoupling 0 + phase4 135 PASS; LEAK-1/2/embargo 手構反例 PASS
FAILURES_SEEN: none
SCOPE_CHANGES: none（簽核唯讀）
NUMERIC_OR_SCHEMA_IMPACT: LEAK 修補改 flag-on OOS rolling 輸入 universe；winsor type 分支改 fit-slice 判定
HANDOFF_NOT_UPDATED: 簽核任務，輸出 SIGNOFF2 檔，不覆寫根 HANDOFF
```

STATUS: DONE

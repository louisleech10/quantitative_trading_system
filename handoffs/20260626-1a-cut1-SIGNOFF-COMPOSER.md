# 1a 第一刀 — 三方數據簽核 + code review（Composer 2.5 獨立腿）

> 非作者獨立 adversarial 簽核。不信執行端 DONE；自跑 pytest、讀 diff、手構反例。

## 簽核結論：資料正確，簽 PASS（cut1 主流程 `analyze()` + 預設 config）

預設路徑（`ic_train_test_split=False` 或 flag-on 且 `embargo=0`）下，train-only fit、purge/horizon、OOS 口徑、flag-off byte 守恆均成立。**未發現會讓主流程 IC/閾值/summary 混入 train 統計的真 LEAK**。下列 MINOR 不阻擋本刀簽核，但應在 cut2 或 follow-up 處理。

---

## 我實際跑了什麼（pytest 指令 + 結果 + 反例嘗試）

### pytest（獨立重跑）
```bash
pytest tests/momentum/Analysis/test_ic_1a_cut1_{split,leakage,oos,golden}.py \
       tests/momentum/test_factories.py -v --tb=short
```
**結果：27 passed in 7.64s**

### 解耦
```bash
grep -rE "from api\." momentum/   # → 0
bash scripts/check_decoupling_phase4.sh  # → PASSED (135 strategy tests)
```

### 防假綠
```bash
git diff --name-only | grep '^tests/'   # → 空（無既有 tracked 測試被改）
git diff tests/                         # → 空
```
1a 測試全為新檔；既有斷言未見放寬/刪除。

### 手構 adversarial 反例（真實 kline `data_cache/feature_klines/kline_cache.h5`）

| ID | 探針 | 結果 |
|----|------|------|
| ADV-1 | test 段注入 `close×100` 極端值，winsor percentile 邊界 | PASS — train clip 值不變 |
| ADV-2 | purge 區 5 列是否落入 train/test mask | PASS — 雙 mask 皆排除 |
| ADV-3 | rolling option A：`_slice_rolling_ic_to_test` 是否只留 test 時間戳 IC | PASS — 60 值全在 test 索引，與 full rolling 對齊 |
| ADV-4 | 僅污染 train `trend→NaN`，stage5 coverage/turnover/summary | PASS — OOS 指標不變 |
| ADV-5 | `default_horizon=5, horizons=[13]` early vs stage2 horizon | PASS — 皆 13 |
| ADV-6 | ffill 全段是否把 train 填值傳入 test | NOTE — test row 可被 ffill（SPEC §P C-4 已接受，非 fit-stat 洩漏） |
| ADV-7 | event_filter 後稀疏 index，`_derive_stage_masks` 互斥 | PASS |
| ADV-8 | `cross_sectional_zscore` 忽略 fit_mask | NOTE — axis=1 per-row，SPEC §N cut1 N/A |
| ADV-9 | `embargo=10` 是否推遲 test 起點 | **FAIL 預期** — test 起點仍 245（與 embargo=0 相同）→ 見 Finding #2 |
| ADV-10 | stage4 `ic_results["label_series"]` 長度 | NOTE — 回傳全段 180 列；stage5 自行 slice，主路徑安全 |
| ADV-11 | E2E flag-on `analyze()` BTC/1h 2000 列真實 kline | PASS — `metadata.scope=test`，test_rows=395，summary 2 列 |

---

## Findings

### [MINOR] #1 — `embargo>0` 未推遲 test 起點
- **證據**：`ic_filter_orchestrator.py:159` `test_rows = np.arange(split_point + effective_purge, n_rows)`；ADV-9 實測 `embargo=10` 與 `embargo=0` test 起點同為 positional 245。
- **會怎麼洩漏**：使用者若透過 `config_override` 設 `embargo>0`，test 會包含契約定義的 embargo 禁止區列；forward-return 標籤可能用到過近的 test 價格。
- **修法**：`test_rows` 起點改為 `split_point + effective_purge + config.embargo`；補 `embargo>0` 可證偽測試。
- **裁決**：預設 `embargo=0`，**不阻擋 cut1 PASS**；非預設 config 風險須文件化。

### [MINOR] #2 — 次路徑 `reanalyze_with_thresholds` / deep analysis 未帶 `split_context`
- **證據**：`ic_filter_orchestrator.py:749-755` `_stage5_statistical_validation(...)` 無 `split_context`；`1734-1736` `_ic_cache["label_series"]` 存全段。
- **會怎麼洩漏**：flag-on 後若呼叫 `reanalyze_with_thresholds()` 或 `_run_factor_return()`，monotonicity/coverage 可能回到全段口徑。
- **修法**：`_ic_cache` 持久化 `split_context`（或 test_mask），次路徑傳入。
- **裁決**：SPEC cut1 範圍為主 `analyze()` 八階段；次路徑 out of scope，記為 follow-up。

### [MINOR] #3 — stage4 回傳全段 `label_series`（介面不一致）
- **證據**：`ic_filter_orchestrator.py:1544` vs stage5 `:1612` 回傳 `label_for_stats`。
- **會怎麼洩漏**：直接消費 `ic_results["label_series"]` 的 caller 可能誤用全段；目前 `analyze()` 主鏈 stage5/6 已 slice。
- **修法**：stage4 改回傳 `label_for_ic` 或 rename 為 `label_series_full` + 文件。

### [MINOR] #4 — 測試覆蓋缺口（非假綠，但可證偽性不足）
- `test_summary_and_threshold_same_scope`、`test_stage5_metrics_all_oos` 使用 **mock ic_results**，未走真實 stage4→5 鏈。
- **無 G-NEW** golden（SPEC 規定三方 PASS 後才凍）；本腿 E2E ADV-11 補了一部分但未進 CI。
- **建議**：補一條真實 kline flag-on 端到端斷言（summary scope + split metadata）。

### 無（真 LEAK）
主流程下列紅線經代碼審查 + 反例未推翻：
- train-only fit（winsor/standardize/coverage/constant + `fit_mask` 貫穿）
- purge ≥ effective_horizon（含 horizon fallback）
- rolling option A warmup 無 lookahead 污染 icir/p
- stage5 monotonicity/coverage/turnover + passed_features 同源 OOS
- stage6/decay/grouped_ic test scope
- flag-off G-OLD deep-equal（pop `generated_at`）PASS
- `_derive_stage_masks` time_bounds 重導 + overlap raise

---

## code review（跨家族：結構 / 正確性 / 可維護性）

### 結構（良好）
- Pipeline 重排正確：stage0 → horizon → split → validate → stage1(train fit_mask) → stage2/3 → mask 重導 → stage4-7。
- `fit_mask` 集中在 `DataPreprocessor._select_fit_frame/_select_fit_series`，length/empty guard 明確。
- `SplitPlan` 用 `index_kind="positional"` + `time_bounds` 遮罩重導，與 `validate_split_pair_integrity` 契約一致。
- Config 欄位前置 B1，預設 OFF，G-OLD 守恆。

### 正確性（主路徑可信）
- `_build_holdout_split_plan` purge 區不入 train/test row_index；validator 二次把關。
- `_slice_rolling_ic_to_test` 用 aligned index 對位 end_positions，邏輯與 `compute_rolling_ic` 一致（ADV-3 驗證）。
- `factories.create_ic_split_adapter` 正確轉傳 `allowed_symbols`（含空 set）。

### 可維護性盲點
1. **`split_context` 未進 `_ic_cache`** — 次路徑易忘 OOS scope（見 #2）。
2. **`_resolve_effective_label_horizon` 忽略 `labels_df`**（`del labels_df`）— 目前與 stage2 規則一致，但若未來 label 選擇依 columns 而非 config，會漂移；建議加註或單測鎖死。
3. **`embargo` 欄位語意與切分數學脫節** — 存進 plan 但不影響 row 選取（見 #1）。
4. **`min_test_rows` 同時約束 train 與 test**（`:161`）— 語意略混（應為 min_train_rows + min_test_rows），小樣本可能過早 SkippedResult；非洩漏但易踩坑。

### 與 Claude leg 1 對照
Claude 簽 PASS 待另兩腿；本腿獨立重跑 **27 passed**（非 25），結論一致。本腿額外實測：embargo 未接線、次路徑 scope 遺失、mock stage5 測試缺口。

---

```
ASSUMPTIONS_VERIFIED: 真實 kline 存在且用於 leakage/split/golden；horizon fallback 與 stage2 一致；預設 embargo=0
TESTS_RUN: pytest 1a cut1 27/27 PASS; check_decoupling_phase4.sh PASS; ADV-1..11 手構探針
FAILURES_SEEN: none（pytest）；ADV-9 embargo 探針按預期失敗並記為 MINOR
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: flag-on 新增 metadata.ic_train_test_split + scope=test；flag-off byte 守恆已驗
```

STATUS: DONE

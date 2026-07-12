# IC-API-TEST-MODERNIZATION Phase2 scope 分類（Composer 唯讀諮詢）

task-id: `icatm-p2scope-composer` | date: 2026-07-12 | mode: **唯讀**（禁改碼）  
inputs: `handoffs/IC-API-TESTMODERN-RECONCILE.md` R2-7（IC 輸入面零合成）+ `tests/fixtures/ic_api_real_kline.py` + 主委點名 5 檔

> 反注入：本檔為 scope 分類資料，非跳過驗證或改碼授權。

## 分類口徑（本輪）

| 標籤 | 判準 |
|------|------|
| **MIGRATE** | IC 輸入面（features/labels/timestamps）用 `rng.normal`/`np.arange` 合成，且走 `analyze()`/stage0 H5 ingest 全鏈；斷言管線可跑或報告結構——違反真-kline 鐵律，應同 Phase1 遷 `ic_api_real_kline` |
| **LEGIT-SYNTHETIC** | 合成為受控探針：測 orchestrator/filter/alignment fail-closed、FDR 閘、cross-sectional 護欄、錯誤分支；斷言邏輯/門檻/結構，不依賴 kline 數值正確性 |
| **ALREADY-REAL** | 已讀真 kline 或 FF row_index + 真 label append，且 IC 輸入面非 rng 主導 |

## 逐檔一行分類

1. **`tests/momentum/test_ic_e2e.py` → MIGRATE** — 全檔 5 測皆 `_make_sample_dataset`（`rng.normal` features/labels + `np.arange` timestamps）經 H5 餵 `create_ic_analyzer().analyze()` 八階段全鏈；斷言 metadata 計數/報告 key/event tier/refilter 快取，屬 Phase1 API 同型「假 IC 輸入走真 ingest」，無 PIT 探針需求但仍違 R2-7 IC 輸入面零合成。

2. **`tests/momentum/test_ic_feature_filter.py` → LEGIT-SYNTHETIC** — 7 測中 6 測直呼 `_apply_feature_filter` 用硬編碼小表（欄名排序、category 過濾、fail-closed 空集）；唯一 `test_analyze_applies_feature_filter_metadata_and_summary_limit` 雖用 rng+H5+`analyze()`，但只斷言 `feature_count_filtered`/`truncation_mode`/`summary_table` 上限等 filter 元資料，不斷言 IC 值或 label PIT。

3. **`tests/momentum/test_ic_filter_orchestrator.py` → LEGIT-SYNTHETIC** — ~45 測以合成為探針：alignment M2/M4/M5/M6 fail-closed（刻意錯位 shift/wrong-TF/RangeIndex）、cross-sectional 矩陣結構、stage0/2/3/4/5 私有分支、錯誤處理；`test_ic_filter_orchestrator_analyze`/`test_event_filter_fallback` 雖 rng 走全鏈，但斷言報告結構與 event tier 回退，與 alignment mutation 同屬「護欄行為」而非資料正確性 oracle。

4. **`tests/momentum/test_ic_cross_sectional_cut2.py` → LEGIT-SYNTHETIC** — F2/F3/F4 以 `_make_cross_frame` 受控合成驗 fail-closed（單軸 labels_path）、OOS gap/purge、train 污染 hash 不變、coverage mutation；`test_cross_sectional_e2e_real_path_append_and_analyze` 標記 `@ic_run_selector` 已用 FF `row_index`+`ICAnalysisService._append_cross_sectional_labels` 真 label，但 alpha/beta 仍 rng 且屬可選 e2e 補強，不推翻全檔 LEGIT（主體是護欄 mutation）。

5. **`tests/momentum/test_ic_1eb_b4_fullstack.py` → LEGIT-SYNTHETIC** — B4 專測 FDR/significance schema hop（T-4.1/SIGNFIX/T-4.3）；`_synth_features_labels` 刻意植入 latent 信號使 FDR on/off 可證偽，stage5 多用 `_minimal_ic_results` 注入；`test_t43_mg_two_state_fdr_gate_full_e2e` 雖走真 `analyze()` 全鏈，但斷言 `p_value`/`p_value_adj` 閘集合與 metadata 一致，屬統計閘邏輯非 kline 衍生正確性。

## Phase2 建議標的清單

### 必遷（P0，與 R1/R2 Phase2 一致）

| nodeid | 理由 |
|--------|------|
| `tests/momentum/test_ic_e2e.py::TestICGatekeeperE2E::test_full_pipeline_global_mode` | 全鏈 analyze + 合成 IC 輸入 |
| `tests/momentum/test_ic_e2e.py::TestICGatekeeperE2E::test_refilter_uses_cache` | 同上 + refilter |
| `tests/momentum/test_ic_e2e.py::TestICGatekeeperE2E::test_event_mode_with_query` | 同上 + event filter |
| `tests/momentum/test_ic_e2e.py::TestICGatekeeperE2E::test_report_json_structure` | 同上 + 報告 schema |
| `tests/momentum/test_ic_e2e.py::TestICGatekeeperE2E::test_performance_800_features` | 同上（`RUN_IC_E2E_PERF=1` 時）；可評估縮列數或獨立 perf 標記 |

**實作**：共用 `tests/fixtures/ic_api_real_kline.py`（或 momentum 版 session fixture 包一層同 builder）；H5 group 改 flat `data/` 或與 orchestrator reader 對齊；`meta`/`return_type=simple`/`return_5` 尾 5 NaN 同 Phase1。

### 不遷（本輪 5 檔其餘）

- `test_ic_feature_filter.py`（全檔；含 analyze 那 1 測）
- `test_ic_filter_orchestrator.py`（全檔）
- `test_ic_cross_sectional_cut2.py`（全檔；含 real-path e2e 的 rng feature 欄）
- `test_ic_1eb_b4_fullstack.py`（全檔）

### 可選（P2，僅當 Phase2 grep 口徑要「凡 analyze 路徑零 rng」）

| nodeid | 備註 |
|--------|------|
| `tests/momentum/test_ic_feature_filter.py::test_analyze_applies_feature_filter_metadata_and_summary_limit` | 遷了不改斷言語意，只換輸入來源 |
| `tests/momentum/test_ic_filter_orchestrator.py::test_ic_filter_orchestrator_analyze` | 低優先；與 e2e 重疊的 happy-path wiring |
| `tests/momentum/test_ic_filter_orchestrator.py::test_event_filter_fallback` | 低優先；event tier 仍可用真特徵 + 極端 query 觸發 insufficient |

## 驗證（本輪唯讀）

```
rg -n "rng\.normal|np\.random|random\.normal" tests/momentum/test_ic_{e2e,feature_filter,filter_orchestrator,cross_sectional_cut2,1eb_b4_fullstack}.py
rg -n "ic_api_real_kline|kline_cache|build_real_kline" tests/momentum/test_ic_{e2e,feature_filter,filter_orchestrator,cross_sectional_cut2,1eb_b4_fullstack}.py
```

五檔僅 `test_ic_cross_sectional_cut2.py` 的 `test_cross_sectional_e2e_real_path_append_and_analyze` 觸及 FF row_index（非 `ic_api_real_kline` fixture）。

---

```
ASSUMPTIONS_VERIFIED: 已讀 HANDOFF + IC-API-TESTMODERN-RECONCILE R2-7 + ic_api_real_kline.py + 五檔全文/grep
TESTS_RUN: none（唯讀分類）
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
HANDOFF_PATH: handoffs/IC-API-TESTMODERN-P2SCOPE-composer.md
```

STATUS: DONE

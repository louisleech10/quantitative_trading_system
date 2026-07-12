# IC-API-TESTMODERN Phase2 scope — grok 唯讀分類
Task-id: icatm-p2scope-grok | Date: 2026-07-12 | Mode: read-only

## 分類口徑（本任務）
- **MIGRATE**：真違反真-kline 鐵律——斷言資料正確性，或把合成當生產 IC 輸入走 **fail-closed 護欄 ingest（含 kline value oracle）**。
- **LEGIT-SYNTHETIC**：測 orchestrator/filter/schema/OOS 邏輯；受控合成（含 adversarial mutation）恰當。
- **ALREADY-REAL**：IC 輸入面已真 kline 衍生（如 Phase1 `ic_api_real_kline`）。

對照錨：Phase1 API 路徑 `ICAnalysisService` 會 `create_kline_storage_manager` 注入 `kline_reader` → stage0 `validate_alignment(..., close=...)` Tier-2 oracle；本批 momentum 測試多半 **不傳 kline_reader**，只走結構對齊/管線邏輯。

## 逐檔（一行分類 + 理由）

| # | 檔 | 分類 | 理由 |
|---|----|------|------|
| 1 | `tests/momentum/test_ic_e2e.py` | **LEGIT-SYNTHETIC** | `_make_sample_dataset`=`rng.normal`+12h `arange` ts 寫 H5；`create_ic_analyzer().analyze` **未注 kline_reader**（無 close oracle）。斷言=input/output 特徵數、report key 齊全、event mode/tier、refilter&lt;1s、可選 800×10k 效能——**無 IC 數值/PIT/真市 oracle**。合成=管線煙測/結構/壓測載體；perf 用例本質需大矩陣。 |
| 2 | `tests/momentum/test_ic_feature_filter.py` | **LEGIT-SYNTHETIC** | 主體直呼 `_apply_feature_filter`（None/max/category/empty fail-closed/45k 穩定排序）=純 filter 契約。僅 `test_analyze_applies_feature_filter_*` 用 `rng.normal` 進 `analyze`，斷言 `feature_count_*=`、`truncation_mode=preview`——filter 元資料，非資料正確性。 |
| 3 | `tests/momentum/test_ic_filter_orchestrator.py` | **LEGIT-SYNTHETIC** | 大檔單元/整合：refilter、event fallback、xsec matrix、stage0 NaN drop、stage2/3/4 分支、**alignment fail-closed mutation**（RangeIndex/錯 TF/shifted label/M5 dual-leg/M6 noop sha）、slice 錯位 raise。多處 **刻意合成壞資料** 證 fail-closed 非假綠；DummyReader 控 close 測 gate 邏輯。遷真 kline 會毀 mutation 可證偽性。 |
| 4 | `tests/momentum/test_ic_cross_sectional_cut2.py` | **LEGIT-SYNTHETIC** | F2 單軸 labels fail-closed、F3 OOS gap/purge mutation、train pollution hash 不變、F4 coverage 關守衛 mutation——皆需受控 MultiIndex 合成。`test_cross_sectional_e2e_real_path_append_and_analyze`：**row_index+`_append_cross_sectional_labels` 真路徑**，但 alpha/beta 仍 `rng.normal`；斷言 label 覆蓋數/OOS applied——**非整檔 ALREADY-REAL**，features 合成對接線測合理。 |
| 5 | `tests/momentum/test_ic_1eb_b4_fullstack.py` | **LEGIT-SYNTHETIC** | `_synth_features_labels` 種 latent signal 供 FDR ON/OFF 可分離；斷言 tier hop→`significance.fdr`、`p_value` vs `p_value_adj` 閘集合可重算、method 白名單 fail-closed、xsec metadata `alpha_effective`。T-4.3 全鏈 analyze 仍是 **schema/閘邏輯**，非市值正確性；真 kline 難保證兩態 passed 可分離。 |

**ALREADY-REAL 計數：0**（無檔 import/使用 `tests/fixtures/ic_api_real_kline.py`）。

## Phase2 建議標的清單

| 優先 | 標的 | 動作 |
|------|------|------|
| — | （本 5 候選內） | **鐵律級 MIGRATE = 空集** |
| note | R1 點名 `test_ic_e2e.py` | 屬「管線煙測」非資料正確/非 kline-oracle 護欄；**不建議**為遷真 kline 而動（perf 800×10k 尤忌） |
| note | cut2 e2e features | 可選後續 polish：features 改真 FF 欄（非 Phase2 鐵律必須）；labels 已真 kline 衍生 |
| residual | 若主委擴政策為「凡 `analyze()` 的 IC 輸入面零 rng」 | 才重開 scope——將與 LEGIT-SYNTHETIC 衝突，需另 SPEC 界定例外（mutation/FDR 種訊號/大矩陣 perf） |

## 決策摘要
Phase1 問題是 **API+kline_reader+Tier-2 oracle** 下仍餵 `rng.normal` 假 IC 輸入並冒充可跑契約。本 5 檔是 **momentum 側邏輯/護欄/FDR/OOS** 測試；合成多為受控或 adversarial，**不構成同型鐵律違規**。建議 Phase2 **不遷這 5 檔**，改走 Phase3 文件化分層（L0 純邏輯合成 / L1 session real-kline API / L2 真 FF）即可閉合 epic 敘事。

## 方法（唯讀）
- 讀：`HANDOFF.md`、`handoffs/IC-API-TESTMODERN-RECONCILE.md`、R1 SPEC 草稿、`tests/fixtures/ic_api_real_kline.py` 頭、五候選檔全文/斷言索引、`ic_filter_orchestrator._stage0_ingestion`、`ICAnalysisService` kline 注入點。
- 未改碼、未跑 pytest（scope 分類不需執行）。

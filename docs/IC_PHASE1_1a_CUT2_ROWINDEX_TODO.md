# IC Phase1 1a 第二刀首項 — row_index attach TODO

> 狀態 DRAFT　|　基於 SPEC：docs/IC_PHASE1_1a_CUT2_ROWINDEX_SPEC.md　|　日期：2026-07-06

## SPEC 100% 覆蓋追溯（防漏基準）
| 類別 | ID/項 | SPEC 原文節錄（≤30字） | 合計 |
|---|---|---|---|
| Task | Task 1.1 | 「V2 path attach row_index」 | 1 |
| §G Golden | G-1 值守恆 | 「改後 to_numpy 值/NaN/shape/欄名sha256 byte-equal」 | |
| §G Golden | G-2 時間軸 | 「index 為 DatetimeIndex，int64秒 byte-equal timestamps.parquet」 | |
| §G Golden | G-3 端到端 | 「retarget 追蹤測試斷言在失敗邊界:真時間軸+split校驗不raise」 | 3 |
| §RISK | a,d | 「RISK-HIT: a,d」 | 2 |
| Phase 依賴 | Phase1 無前置 | 「依賴：無」 | 1 |
| 邊界 | B-1/B-2/B-3 | 「舊run no-op / 長度不符 raise / 空DF」 | 3 |
| 環境/flag | 無 | 「無 feature flag（正確性修復不藏開關）」 | 0 |

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
- **解耦**：`feature_library.py` 屬 `momentum/`，禁 `from api.`（`grep -r "from api\." momentum/` 須 =0）；只複用既有 `self._reader.load_row_index_v2`，不新增跨界 import（引 SPEC §C）。
- **不改輸出**：只補 `.index`；特徵值/欄名/列數/輸出檔大小一律不變（引 SPEC §G G-1）。不弱化 NaN/inf gate。
- **不藏開關**：正確性修復預設 ON，無 feature flag（memory「驗過就別預設關閉」）。
- **防假綠**：追蹤測試由 full-analyze `..._completes`(xfail) retarget 為 `..._split_validation_passes_with_real_axis`,斷言在**失敗邊界**(真時間軸+split校驗不raise);未放寬既有斷言(舊 assert 整段移除非降門檻);新斷言對應「index RangeIndex→DatetimeIndex 且值不變」。三方確認忠實。diff 斷言驗收。
- **Logging/Error**：`get_logger(__name__)` 既有；length mismatch 屬 non-retryable → `raise ValueError`（logic/data format）。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| Batch 1 | Task 1.1 | 無 | 單一函式改動 + 三層測試同批 | 大(命中 a,d) |

- **批次 Gate（可執行驗證命令，pytest）**：
  - `grep -r "from api\." momentum/ | wc -l` → 0
  - `pytest tests/momentum/test_feature_library_row_index.py -q`（新單元：attach/no-op/length-guard）
  - `pytest "tests/api/test_ic_analysis_service.py::test_analyze_real_run_split_validation_passes_with_real_axis" -q`（斷言真時間軸+split校驗不raise;取代原 full-analyze xfail）
  - §G Golden 值守恆腳本（測試內；G-1/G-2 byte-equal 斷言）

- **派工 prompt（可直接複製）**：
  > 前置狀態：main 乾淨；SPEC=docs/IC_PHASE1_1a_CUT2_ROWINDEX_SPEC.md 已 PASS template_check。真實 12h run e53e22906c35363757f4cd49d27f973e 已物化於 data_cache/features/。
  > Task：實作 Task 1.1（見下），新增三層測試（單元 attach/no-op/length-guard + Golden 值守恆 + 端到端 retarget 至失敗邊界斷言）。
  > 驗證命令：上列 Batch Gate 四條全綠。
  > 禁：改特徵值/欄位/列數/HDF5 fallback 路徑/`_write_features_h5`；放寬既有斷言；加 feature flag。

## Phase 1 — load 路徑貼回時間軸（目標：`load`/`load_for_training`/`load_multi` 回傳帶真 DatetimeIndex；完成後 IC config_hash 路徑不再誤 raise）

### Task 1.1 — `_load_internal` V2 path attach row_index
- **SPEC ref**：Task 1.1 / §G / §P Phase1
- **目標**：V2 reader 成功載入 `features_df` 後、`return` 前，貼回 `load_row_index_v2` 的真時間軸；舊 run 無 row_index 則 no-op。
- **輸入**：`symbol:str, timeframe:str, resolved_hash:str, features_df:pd.DataFrame`（已由 `load_columns_v2` 產出、非空）。
- **輸出**：同一 `features_df`，`.index` 為 `DatetimeIndex(name="timestamp")`（或舊 run 時維持原 RangeIndex）。
- **實作要點**（≥3）：
  1. 新 private helper 簽名：`def _attach_row_index(self, symbol: str, timeframe: str, config_hash: str, df: pd.DataFrame) -> None`（原地改 `df.index`，鏡像 `api/services/feature_factory_service.py::_attach_cgsa_row_index`）。
  2. helper 內：`ri = self._reader.load_row_index_v2(symbol, timeframe, config_hash, artifact_kind="raw")`；`if ri is None: return`（舊 run 向後相容）；`if len(ri) != len(df): raise ValueError(f"row_index length mismatch for {symbol}/{timeframe}/{config_hash}: {len(ri)} != {len(df)}")`；`df.index = ri; df.index.name = "timestamp"`。
  3. 呼叫點：`_load_internal` 於 `if not features_df.empty:` 區塊、`return features_df`（line ~164）之前插 `self._attach_row_index(symbol, timeframe, resolved_hash, features_df)`。for_training/browse 兩路徑共用同一 attach（時間軸與 consumer policy 正交）。
- **修改檔案**：`momentum/FeatureEngineering/feature_library.py`（新增 `_attach_row_index`；`_load_internal` 插一行呼叫）。既有 caller：`load`/`load_for_training`/`load_multi`（同檔）；下游 `api/services/ic_analysis_service.py::_materialize_features_for_ic`（受益，不改）。
- **驗證（可證偽，pytest 命令如下）**：
  - 單元 `pytest tests/momentum/test_feature_library_row_index.py -q`：真 run e53e2290 → `load` 回 `isinstance(df.index, pd.DatetimeIndex)` 且 `df.index.name=="timestamp"`；`df.index.view("int64")//10**9` 與 `load_row_index_v2` 的 int64 秒 `np.array_equal`（G-2）。
  - Golden G-1：改前值 baseline（欄名 sha256 + shape + 抽樣 value hash + NaN mask hash）vs 改後 `load().to_numpy()` `==`（float32 容差 rtol/atol）+ 欄名 sha256 相等。
  - 端到端(retarget)：`pytest "tests/api/test_ic_analysis_service.py::test_analyze_real_run_split_validation_passes_with_real_axis"` → materialize h5 真時間軸(非arange,+43200s)+`_validate_expected_frequency` 不 raise;移除原 `..._completes` xfail(full-analyze>17min 正交,改「79測試換真資料」epic 承接)。
- **邊界（≥2，對應 SPEC）**：
  - **B-1 舊 run 無 row_index**：mock/挑一個 manifest 無 `row_index` 鍵的 run（或 monkeypatch `load_row_index_v2`→None）→ `load` 回 RangeIndex、不 raise。
  - **B-2 長度不符**：monkeypatch `load_row_index_v2` 回傳長度 = `len(df)-1` 的 DatetimeIndex → `load` `raises ValueError`（不靜默貼錯位）。
  - **B-3 空 DF**：`features_df.empty` 分支不進 attach（既有 code 早於 `if not features_df.empty` 外）→ 行為不變。
- **不可做**：不改 HDF5 fallback（line 180+，另有 index 語意）；不動 `feature_reader`；不改 `_write_features_h5`；不改任何特徵值/欄位/列數；不加 feature flag。

## §N N/A / deferred
- 1d 頻率地圖缺口、P2 features_path/config_hash 一致性 → SPEC §N 已登記，本刀不動。

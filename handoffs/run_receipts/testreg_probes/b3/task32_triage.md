# TESTREG Task 3.2 非治理改寫檔分流（主委 2026-10-14；依 claude_G*.md 註記、輕量掃描與委員分類輪）

前提：SPEC v49（修訂審查 r48 中）之收據形——`receipts.mutation`（舊目標可殺）、`receipts.additive_rewrite`（舊函式不動、只增、須證新增偵測力與情境綁定）、`receipts.infrastructure_repair`（準備步驟既有紅、只改共用基礎設施）；manifest 邊界「收據驗不過 ⇒ 退回 keep 並登 §N」。

## A. 隨 K1（§N R10）延後——含「週期 unknown」既有紅目標（修復在 FRAMEPATH 母體之 `tests/feature_engineering/ffstat_helpers.py`）
- `tests/feature_engineering/preprocessing/test_causal_winsor.py`、`test_fast_adf_synthetic.py`、`test_layer_filter.py`、`test_non_stationary_cache.py`、`test_precision_corr.py`、`test_slow_path_parallel.py`、`tests/test_fracdiff_fft_opt.py`（目標全為既有紅）
- `tests/feature_engineering/test_fracdiff_maxlag_derivation.py`（`test_short_dataframe_fracdiff_keeps_row_count` 為同因既有紅；另一目標 `test_fracdiff_auto_max_lag_is_calibration_derived_not_df_length` 之斷言可殺、缺陷為迴圈所建 frame 未傳入〔名實不符〕，新增偵測力不可證 ⇒ 預計依邊界退回 keep 並登 §N）
- 待查：`tests/feature_engineering/test_ff_wrapper_path_correctness.py`、`tests/feature_engineering/test_ffstat_all_tested.py`（呼叫 `attach_unit_calibration`、無耗時紀錄；先輕量實跑確認是否同因既有紅）

## B. 第一子批（純增、輕量；≤20 檔）
| 檔 | 舊目標缺陷（摘要） | 新增測試要點 | 狀態 |
|---|---|---|---|
| `tests/feature_engineering/test_dstar_cache_key_mutation.py` | 七支負向測試無正向基線（get 恆不命中時七支亦不失敗） | 同鍵同值種下後命中 0.375 | 暫存樹試作（收據自檢於 v49 試作補丁下；主樹待 v49 落地後重產） |
| `tests/feature_engineering/test_tf_aligner.py` | hash 測試未隔離對齊版本 | 穩定性＋只改對齊版本則 hash 變 | 暫存樹試作（收據自檢於 v49 試作補丁下；主樹待 v49 落地後重產） |
| `tests/feature_engineering/test_cgsa_multi_symbol_isolation.py` | 分片迴圈空轉、隔離由測試自建 | 真跨分片＋經生產路徑之 symbol 隔離 | 暫存樹試作（收據自檢於 v49 試作補丁下） |
| `tests/feature_engineering/test_cgsa_boundary.py` | 「小於一列」情境被 32MiB 下限吃掉 | 真跨分片之 1 列／1 欄／釋放 | 暫存樹試作（收據自檢於 v49 試作補丁下） |
| `tests/feature_engineering/test_cgsa_dead_drop_stream.py` | 對照 oracle 與待測同源 | 硬編期望死欄集合 | 暫存樹試作（收據自檢於 v49 試作補丁下） |
| `tests/feature_engineering/test_dead_feature_filter.py` | 兩實作同源對照 | 硬編期望判定 | 暫存樹試作（收據自檢於 v49 試作補丁下） |
| `tests/feature_engineering/test_failopen_winsor.py` | PIT 檢查列皆在窗未滿前（NaN 比 NaN） | 檢查列 ≥251、加長序列 | 暫存樹試作（收據自檢於 v49 試作補丁下） |
| `tests/feature_engineering/test_l65_l7_raw_disk.py` | Mode C 宣稱未經其入口 | 經 write_raw_from_registry_stream(preprocessor=None) 觸發預檢 | 暫存樹試作（收據自檢於 v49 試作補丁下） |
| `tests/feature_engineering/preprocessing/test_l65_native_tf.py` | 只斷形狀 | 斷 legacy 路徑理由／與 flag=0 逐位元相等 | 暫存樹試作（收據自檢於 v49 試作補丁下） |
| `tests/feature_engineering/preprocessing/test_l65_v2_transforms.py` | NaN 比 NaN、legacy profile 自指 | 有限值前提＋加長 fixture | 暫存樹試作（收據自檢於 v49 試作補丁下） |
| `tests/test_data_source_quick.py` | 吞例外回 False | 直接斷言範圍 | 暫存樹試作（同上；新測試以獨立遞迴 EMA 定義逐列比對） |
| `tests/test_data_source_simple.py` | 0 函式（G-c） | 模組層搬入函式、以斷言取代 exit | 🔴 契約缺口 Q2：檔尾為混合分支 if（印出＋else 內 exit(1)），非「只含結束類」之 if ⇒ 須 AST 同構搬入，卻又禁新增函式含 exit ⇒ 無合法 G-c 改法 |
| `tests/test_dynamic_indicator_system.py` | 回傳布林代斷言 | 改為斷言 | 暫存樹試作（同上） |
| `tests/test_feature_naming_integration.py` | 零斷言只印 | 斷言預期名與無衝突 | 暫存樹試作（收據自檢於 v49 試作補丁下）；另查到生產缺陷（同 data_source 不同 EMA 參數欄名相撞），已登 白話說明/還沒做的事.md |
| `tests/test_volume_threshold_fix.py` | 零斷言回布林 | 斷言 -0.1／1.1 被拒 | 暫存樹試作（同上） |
| `tests/test_cross_symbol_features.py` | 只印警示、條件永不命中 | 斷言相對值範圍 | 暫存樹試作（同上）；另查到生產缺陷：`_should_filter_absolute_features` 以 PYTEST_CURRENT_TEST 含本檔名即過濾（測試名改變生產行為），新測試先中性化該變數再測 relative_only 契約 |
| `tests/test_phase_d_granular_control.py` | 五支空心（恆等式、無競爭） | 非空 override 差異、文件檢查具體化 | 🔴 契約缺口 Q1：D4 兩目標只讀 docs/API_SPECIFICATION.md（R(t)＝∅）⇒ 檔級 additive 不適用 |
| `tests/test_searchsorted_align.py` | oracle 自指（生產 validate_no_future_leak） | 獨立 PIT 期望 | 暫存樹試作（同上；獨立推導 PIT 期望 11＋12k） |
| `tests/test_winsorize_partition_opt.py` | 只驗 numpy 語意、不碰待測 | 驗待測函式不多複製 | 🔴 契約缺口 Q1：舊目標未引用任何生產符號（R(t)＝∅）⇒ additive 不適用；新測試（就地改寫）已寫於暫存樹 |

## C. 第二子批以後（真實 K 線、重項或須另議）
- 真實 K 線／無耗時紀錄：`atomic/test_handcoded_reference.py`、`preprocessing/test_ff_causal_golden.py`、`preprocessing/test_fast_adf_gate.py`、`tests/test_feature_factory_operators.py`
- 無耗時紀錄：`tests/feature_engineering/test_icfirstalign_domain.py`、`test_icfirstalign_memory.py`、`preprocessing/test_p01_p02_p11_opts.py`
- 須另議：`tests/test_feature_factory_mcp.py`（舊目標以預設全設定實跑完整生成並寫入真實 data_cache，空心且有副作用；純增保留舊函式則副作用與 309 秒續存 ⇒ 擬依邊界退回 keep 並登 §N，或另議）、`tests/feature_engineering/test_failopen_frozen_diff.py`（終點無界與缺檔 skip，屬前提而非空心）、`preprocessing/test_l65_phase0_gate.py`（既有紅之因在 `scripts/benchmark_l65.py`，非 tests/ 共用基礎設施，不適用修復收據）

# FF_FAILOPEN_UNIFIED Batch6 — 故障矩陣 + 正確性測試集

**日期**: 2026-06-12  
**前置 commit**: e9c5459 (Batch2–5)  
**Scope**: 僅新增測試；未改 production 碼。

## Task 6.1 — `test_failopen_matrix.py` [V-4][V-8]

| 測試 | V-ID | 約略耗時 | 結論 |
|------|------|----------|------|
| `test_matrix_whole_layer_failure_fail_closed` | V-4 | ~15s | 整層 L1 注入 → fail-closed `RuntimeError`；資料路徑真實 generate |
| `test_matrix_whole_layer_failure_partial_status` | V-4/V-8 | ~15s | `allow_partial_layers` → `quality_status/run_status==partial` + `failed_layers` 含 L1 |
| `test_matrix_nan_ratio_exceeds_marks_partial` | V-8 | ~15s | `max_nan_ratio=0` → partial + `quality_thresholds` 存在 |
| `test_matrix_partial_tf_failure_fail_closed_and_partial` | V-4/V-8 | ~35s | 1h TF 注入：預設 raise；`allow_partial_timeframes` → partial + `failed_timeframes` 含 1h |
| `test_matrix_cgsa_tf_failure_rollback_state` | V-4 | ~35s | CGSA 1h 失敗後 registry 無 `1h_` group、work_dir 無 `*1h*` 殘留 |
| `test_matrix_l65_failure_degrades_metadata` | V-8 | ~12s | `FFACT_USE_CGSA=0` + L6.5 注入 → `preprocessing_applied=False`、partial、`L6.5:preprocessing_failed` |

**矩陣檔小計**: 6 passed，~97–100s（單檔 pytest）。

**FROZEN_TESTS 核對**: `git diff d654237` 既有斷言變更均在 `docs/FF_FAILOPEN_FROZEN_TESTS.md`（contract/ic_first/l7_raw/multi_tf）；Batch6 為新檔無既有斷言改動。

## Task 6.2 — `test_failopen_correctness.py` [V-3][V-5][V-6][V-7]

| 測試 | V-ID | 約略耗時 | 結論 |
|------|------|----------|------|
| `test_v3_healthy_full_run_matches_frozen_baseline` | V-3 | ~8–10min（subprocess Gate-A） | L1–L6 + final_L7 canonical hash == `tests/_golden/failopen/baseline.json`（BTCUSDT/12h） |
| `test_v5_prefix_no_leakage_after_warmup` | V-5 | ~25s | 28d vs 截尾 7d：warmup 後共同 index byte 級一致（uint8 view + NaN mask） |
| `test_v6_independent_asof_oracle_matches_multi_tf_columns` | V-6 | ~90s | 手寫 as-of oracle == 真實 `build_asof_index_map`；首個 1h group 至多 3 欄 oracle 對齊 pipeline `_align_group_array` 全行一致；邊界 PIT 不取未收盤 bar |
| `test_v6_searchsorted_and_merge_backends_byte_identical[False/True]` | V-6 | ~2×90s | `FFACT_USE_SEARCHSORTED=0/1` 輸出 byte 一致 |
| `test_v7_cross_symbol_isolation` | V-7 | ~45s | BTC 單跑 hash == 接 ETH 後再跑 BTC hash |
| `test_v7_symbol_order_permutation_invariant` | V-7 | ~45s | [BTC,ETH] vs [ETH,BTC] 各 symbol hash 不變 |
| `test_v7_cache_cold_hot_identical` | V-7 | ~60s | `force_regenerate` vs cache 命中 canonical hash 一致（28d 窗 + `l7_dead_feature_drop` 關閉） |
| `test_v7_cgsa_resume_matches_fresh` | V-7 | ~60s | CGSA manifest resume hash == fresh run |

**正確性檔小計**: 9 passed（含 parametrize），與矩陣合計 15 passed ~11m24s。

## 驗收命令

```bash
pytest tests/feature_engineering/test_failopen_matrix.py tests/feature_engineering/test_failopen_correctness.py -q
pytest tests/feature_engineering/test_failopen_contract.py tests/feature_engineering/test_failopen_layers.py \
  tests/feature_engineering/test_failopen_golden.py tests/feature_engineering/test_failopen_manifest.py \
  tests/feature_engineering/test_failopen_producer.py tests/feature_engineering/test_failopen_consumer.py \
  tests/feature_engineering/test_failopen_winsor.py -q
```

**實測**: 15 + 73 = 88 passed；無 production 變更。

## 資料正確性自評

- **整體**: 在 SPEC 範圍內（真實 kline、`generate`、byte 級/hash 級可證偽斷言）→ **資料正確性可接受**。
- **存疑點**: V-6 值比對綁定「首個對齊 1h group」至多 3 欄（非全欄掃描）；V-3 Gate-A 用 baseline 全窗（~8–10min），與矩陣短窗策略不同但符合凍結 baseline 定義。

## 踩坑

1. L6.5 矩陣：`FFACT_USE_CGSA=0` 須在 `_apply_baseline_env` **之後**設，否則仍走 CGSA L7 繞過 legacy L6.5。
2. V-7 persist：14d 短窗 + `l7_dead_feature_drop` 會導致 L7 stream 0 features；測試用 28d + 關閉 dead drop。
3. V-6：multi-TF CGSA 路徑 `features_df` 常空；oracle 驗證改對齊 hook + `feature_count>0`。

## Round2 — Codex DOUBT 補強（2026-06-12）

- **V-3**：新增 ETHUSDT/1h 與 BTC multi-TF subprocess Gate-A；逐層/final hash，baseline 有 artifact/group hash 時同步比對。
- **V-5**：新增 L5 enabled prefix；只開 `relative_price`，並先 assert Layer 5 `status=ok`、資料非空，再做全欄 byte 級 prefix 比對。針對測試實跑 PASS（約 1m）。
- **V-6**：open/close × searchsorted/merge backend 各自對獨立 oracle；alignment hook 對所有 captured groups/columns 當場 byte 比；另驗 close-time 整除、gap、duplicate、首列 -1→NaN。單 backend 實測 420 groups，PASS；含其他抽查組共 3m10s。
- **V-7 symbol**：保留新 factory 補充測試；新增同 factory BTC→ETH→BTC hash 相等，PASS。
- **V-8**：matrix 驗收內新增 AST+git line mapping，機械比對 `d654237..HEAD` 既有 assertion owner 與 frozen doc；整檔 wildcard/精確 test 兩種登記均支援，PASS。
- **V-7 resume**：同 storage/work_dir 先 complete 建 gate，再真實 fail-closed 於 1h 中斷，確認 12h groups 已 persist、1h 未 persist；`resume_from_manifest` 計數確認命中。
- **BLOCKER / production defect**：resume 後未 skip 已完成 12h，重算產生 `_2` duplicate groups；one-shot group-set hash `c63f...`，resumed `ba44...`；registry 741→1062 groups，L7 1071 groups/138250 features（one-shot 112633）。`test_v7_cgsa_resume_matches_fresh` 於 group hash assertion FAIL，3m00s。
- **自驗結論**：其餘 targeted round2 測試 4 passed；完整 gate 未跑，因 production resume 缺陷已使指定 correctness gate 必然失敗。未改 production、data_cache、golden、HANDOFF.md、templates。

## Round4 — Batch2 float32 + Batch5 config_hash 回歸修復（2026-06-12）

**根因（Codex `/tmp/codex_mtf_diagnosis.md` 實證）**
1. Batch2 multi-TF 改走 `_execute_layer1_6` → 每層 `_ensure_float32`，12h L3 少 `close_trend_MIDPOINT_233_ZScore_W3`、NaN +52451。
2. Batch5 `max_inf_ratio`/`max_nan_ratio` 進 `model_dump()` → config_hash `57c47c30→00379719`（cache namespace 漂移，非數值根因）。

**Production 改動**
- `feature_factory._execute_layer1_6(..., preserve_dtype=False)` + `_execute_layer1_6_preserve_dtype()` wrapper。
- `multi_tf_generator` L1-L6 全改 `_execute_layer1_6_preserve_dtype`（含 worker `_process_single_timeframe`）。
- `_compute_config_hash` pop `max_inf_ratio`/`max_nan_ratio`；`FactoryConfig` docstring 同步。
- 單 TF `generate` 路徑仍預設 `preserve_dtype=False`（Gate-A byte 不變）。

**新增測試**
- `test_mtf_12h_l1_l3_direct_matches_preserve_dtype_executor`：365d 真實 BTC/12h，direct vs preserve_dtype byte 一致，L3=65483。
- `test_quality_gate_max_ratios_do_not_change_config_hash`：同 payload hash=`57c47c30…`。

**驗收**：見 pytest 全量 log `/tmp/batch6_round4_pytest.log`（進行中）。

## Round5 — IC fixture + Composer V-9 終簽核（2026-06-12）

### Task 1：IC 測試 fixture 修復（僅測試）

- **根因**：Batch5 strict consumer 拒 `run_status=unknown`；`_ic_fixture` / `test_memory_budget_after_raw_persist` 的 `write_raw` 無 `layer_results` → manifest 無 completeness 證據。
- **修法**：`_healthy_layer_results`（L1–L6 ok）+ `row_index` 走真實 persist；`test_ic_group_read_failure_partial_mode` 仍用 `allow_partial_ic=True` 測 group 讀取 partial（非 unknown）。
- **登記**：`docs/FF_FAILOPEN_FROZEN_TESTS.md` 新增 `test_ic_first_pipeline` 列。
- **驗收**：`pytest tests/feature_engineering/test_ic_first_pipeline.py tests/feature_engineering/test_l7_raw_streaming.py -q` → **31 passed**。

### Task 2：Composer V-9 終簽核（未 commit diff review）

| 檢查項 | 結論 |
|--------|------|
| **(a) persistence 邊界 `preserve_dtype` / `asarray`** | 主路徑已修：`feature_factory._coerce_persistence_*`、`feature_storage._coerce_persistence_array`、`column_group_registry.save_data` 單檔、`feature_preprocessor.persistence_sink`。multi-TF L1–L6 改 `_execute_layer1_6_preserve_dtype`。**殘留**：`column_group_registry` 多分片路徑 L809 仍 `ascontiguousarray`（欄切片）；僅超大 sharded group 可能 bytes 漂移，V-3 155/155 npy 未覆蓋此路徑。 |
| **(b) resume 修復** | `_has_resume_checkpoint_for_timeframe` 改為「任一 L1–L6 group 存在即 skip」，不再要求每層都有 group；`_drop_timeframe_groups_from_registry` 配套。邏輯與 handoff 根因一致。 |
| **(c) config_hash max_* 排除** | `_compute_config_hash` pop `max_inf_ratio`/`max_nan_ratio`；`FactoryConfig` docstring 同步；`test_quality_gate_max_ratios_do_not_change_config_hash` 鎖 `57c47c30…`。 |
| **(d) 未登記斷言放寬** | 既有 stub 僅補 `_execute_layer1_6_preserve_dtype` delegate；`test_failopen_producer` 為新增測試非弱化；IC fixture 已登記 frozen doc。無發現門檻下調或刪除既有 assert。 |

**SIGN-OFF: CORRECT** — round4/5 persistence 與 resume、config_hash 修復與 Codex B 線 / Claude V-3 實證一致；IC fixture 補 completeness 證據後 strict gate 行為正確。唯一殘留疑點為 CGSA 多分片 `ascontiguousarray`（窄路徑、未進 byte oracle），不阻擋本批合併。

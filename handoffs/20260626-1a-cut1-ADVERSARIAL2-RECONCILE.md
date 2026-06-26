# 1a 第一刀 SPEC+TODO 第二輪雙家族 Adversarial Reconcile

> 兩家獨立 review：handoffs/20260626-1a-cut1-ADVERSARIAL2-{CODEX,COMPOSER}.md（皆 Verdict「需修補後派工」）
> 第一輪 4 BLOCKING 修補核對：兩家一致判「部分解決」——方向對但契約/順序/語義細節未鎖死。全採納。

## 採納的 BLOCKING（雙家一致，含委員會建議解法）
- **[R2-BLK-1] index_kind 契約不相容**（兩家高信心）：`validate_split_integrity` 強制 `row_index` 為 positional int（`contracts.py:511,528`），與我凍的 `index_kind="timestamp"`（SPEC L69）矛盾。**解（兩家同）**：holdout `SplitPlan` 用 `index_kind="positional"`、`row_index`=stage0 整數位置；遮罩重導 `_derive_stage_masks` 改用 **train/test `time_bounds`（timestamp 區段）∩ current index**（與既有 adapter `index_kind="positional"` 一致）。**移除 SPEC/TODO 所有 `index_kind="timestamp"` 與 `row_index=<timestamp>`**。定義 `_derive_stage_masks` 輸入＝train/test time_bounds；單幣 `base_universe_hash`＝stage0 features_df.index 的 deterministic hash。
- **[R2-BLK-2] split×horizon 依賴順序**（兩家）：`analyze()` stage1 preprocessing 在 stage2 label 之前（`:114-120`），但 split 需實際 horizon、preprocessing 需 train mask；且 stage2 `default_horizon not in horizons→horizons[0]` fallback（`:1049-1051`）會綁錯 purge。**解**：stage0 後抽 `_resolve_effective_label_horizon(config, labels_df)`（labels_df 已在 stage0 載入，可早解），→ 建 holdout split（purge=該 horizon）→ 才 `_stage1_preprocessing(train_mask)`。**禁止先全段 preprocess 再補 mask**。新增 manifest [B-5]。
- **[R2-BLK-3] rolling IC OOS 語義**（Composer BLOCK / Codex MAJOR）：`compute_rolling_ic` 每窗需 `window` 列歷史（`ic_engine.py:268-302`），預設窗 `[21,63,126]`；純 test 子集(20%)前 62/125 列無有效 rolling IC。**解（凍 option A）**：rolling_ic 在 **train+test 連續**算（warmup 用 train，無洩漏：報告值索引在 test 時間、參數已 train-fit），**icir/p-value/threshold/summary 只取 test 時間索引上的 rolling 值**；`min_test_rows >= max(rolling_windows)+purge_gap`，不足→`SkippedResult`。新增 manifest [D-4]。
- **[R2-BLK-4] B2/B5 config 依賴倒置**（Composer）：Task 2.1 讀 `config.oos_test_size` 但 Task 5.1 在 B5 才加。**解**：config 欄位（`ic_train_test_split=False`、`oos_test_size=0.2`、`embargo=0`、`min_test_rows`）移到 **B1**（純欄位、預設 OFF、不改行為）；B5 保留 G-OLD/文件化。更新 §B 表。
- **[R2-BLK-5] G-OLD freeze 不可執行**（兩家）：`scripts/freeze_baseline.py` 不存在（實為 `tests/golden/ic_phase1_contract/freeze_baseline.py`，含寫死 hash `a384e6d2...`）；cut1 golden 目錄不存在；config_hash placeholder。**解**：修正 freeze 命令路徑（複用該 script，新 out 目錄 `tests/golden/ic_phase1_1a_cut1/`）；**G-OLD=flag-off=現行為，可在動工前用現行碼凍**；config_hash 由規劃端動工前一次性產出寫死；dispatch gate 擋未凍。

## 採納的 MAJOR
- **[R2-FIX-embargo] 幽靈欄位**（兩家）：`ICConfig` 無 `embargo`。→ B1 config 加 `embargo=0`（或移除 Task 2.1 的 `embargo=config.embargo` 改用新欄位）。
- **[R2-FIX-horizon-test]**（兩家）：補 `_resolve_effective_label_horizon` + 反例測試（`default_horizon=5` 但 `labels.horizons=[13]`→purge 綁 13 非 5）。
- **[R2-FIX-decay-redundancy]**（兩家）：flag-on 時 decay/grouped/stage6-redundancy 仍入 summary（`ic_half_life` `:1518`）/report（`:1382`）/filtered_df（全段 corr `:1335`）。→ flag-on：**進 summary/passed/filtered 的一律 test scope**（含 stage6 redundancy 對 test 算 corr）；decay/grouped informational 且 report metadata 標 `scope=test`。新增 manifest [D-5]。
- **[R2-FIX-min-test]**（兩家）：定義 `min_test_rows`（>= max(rolling_windows)+purge_gap），與既有 `InsufficientDataError`(<100 列, `:1442`) 關係寫清。
- **[R2-FIX-batch-prompt]**（Composer）：§B 每 Batch 補可複製派工塊（允許檔/驗收 pytest/禁止事項）。
- **[R2-FIX-task63]**（兩家）：Task 6.3 補機械 checklist（kline 路徑存在、purge 反例 pytest 名、G-OLD diff==0、`grep` 既有 assert 無放寬）+ handoffs 檔名模板。
- **[R2-FIX-nodeid]**（兩家）：TODO 每 Task 給確定 pytest nodeid（新檔名+函式名），不留 placeholder。

## 採納的 MINOR
- Task 5.1 API churn（Codex/Composer）：`config_override` 已可 deep-merge 透傳 → cut1 **不改 service**，flag 走 `config_override`；前端接線標 N/A（cut2）。
- golden 命名統一（Composer）：`baseline_old_btc_1h_<config_hash>.json` / `baseline_new_..._<split_id>.json`，寫進 freeze 腳本。

## 結論
兩家無「根本缺陷需重作」。採納 5 BLOCKING + 8 MAJOR/MINOR。新增 manifest [B-5][D-4][D-5]。修 SPEC/TODO → 重跑機檢 → Frozen（雙家族已各做兩輪，達鐵律「大型雙家族都做過」）→ 過 dispatch gate 派 Codex 實作。
**動工前規劃端必做**：凍 G-OLD baseline + 寫死 cut1 config_hash（用現行碼，flag-off==現行為）。

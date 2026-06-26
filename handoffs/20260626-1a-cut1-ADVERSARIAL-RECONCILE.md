# 1a 第一刀 SPEC-前雙家族 Adversarial Reconcile（Codex gpt-5.5 + Composer 2.5）

> 兩家獨立 review：handoffs/20260626-1a-cut1-ADVERSARIAL-{CODEX,COMPOSER}.md
> 兩家 Verdict 皆「需修補後派工」。本檔 reconcile 並驅動 SPEC 修補。

## 待決點裁決：切分來源 = 單一時間順序 holdout（兩家一致）
Codex + Composer 各獨立選 **chronological holdout（單切點）**，非 CPCV/WF adapter。理由收斂：
- cut1 語義＝單幣縱向「一份 OOS IC 報告」，非多 fold 模型驗證。
- adapter 回 `List[SplitPlanPair]` 多 fold → 無 canonical fold 聚合/golden/報告口徑。
- IC config 無 `train_size/n_groups/embargo_pct`，接 adapter 須引入 ML 孤島 config＝過度工程。
- holdout 仍複用既有 `SplitPlan`/`validate_split_pair_integrity`/expected_freq/allowed_symbols 紅線，不重寫切分數學。
- adapter 留 1e（rolling/HAC）、2A（事件 OOS）再接。
→ **凍結（進 SPEC）**：test_size 來源＝IC config 新欄位 `oos_test_size`（預設 0.2）；單切點＝時間排序後尾段 test；`purge_gap = label horizon`（見下 BLOCKING-purge）；embargo 公式寫死；樣本不足→`SkippedResult`。

## BLOCKING（兩家一致或單家高信心，全採納）
- **[BLK-1] split × pipeline 順序**（兩家）：`analyze()` 實際 stage1 preprocessing→stage2 label→stage3 event_filter（`:1096` `loc[idx]` 改 row universe）。我原寫「preprocessing 前產生 split」用 positional mask → event mode 下錯位/index error。**修法**：split 以 **timestamp identity** 定義於 stage0 full universe；train/test 以時間區段表示（time-disjoint + purge 不變量）；每個會改 row 的 stage（event_filter）後，以 timestamp 成員關係重導 train/test 布林遮罩（split ∩ 存活列），校驗 base_universe_hash 對齊。**不變量＝train/test 時間互斥 + purge ≥ horizon，row 移除不破壞此不變量**（移除 train 列不引入 test 資訊）。
- **[BLK-2] purge_gap ↔ label horizon**（Composer 高信心，Codex 同向）：`default_horizon=5`（`ic_config_schema.py:19`）；holdout 不綁 horizon → train 末段 forward-return 標籤用到 test 段價格＝前瞻偏誤，`validate_split_pair_integrity` 擋不住（它只看 purge_gap 數字）。**修法**：`purge_gap >= 實際 label horizon`（cut1 寫死取所用 horizon）；驗證以已知切點構造 train 末 purge 區，assert 不含「可計算 label 需用 test 價格」的列。
- **[BLK-3] 清洗 train-only 漏 missing/constant**（兩家）：`handle_missing`（全段 `notna().mean()` coverage 刪欄，`:113-116`）、`remove_constant_features`（全段 `nunique`，`:120-124`）＝特徵選擇洩漏。**修法**：新增 [C-4] coverage train-only、[C-5] constant-removal train-only；flag-off 保全段舊路徑；補可證偽測試（test 段注入全 NaN/常數不改刪欄集合）。
- **[BLK-4] OOS 口徑不完整**（兩家）：stage4 還算 `compute_ic_decay`/`compute_grouped_ic`（全段，`:1233-1251`）；stage5 monotonicity/coverage/turnover 全段（`:1284-1286`），summary 納入並 threshold coverage（`:1483-1522,1567`）。混用＝全段 coverage 決定 OOS passed_features。**修法**：新增 [D-3]——flag-on 時**所有進 summary_table/threshold/passed_features 的指標一律 test scope**（icir/p/monotonicity/coverage/turnover）；decay/grouped/redundancy 於 §N 標 cut1 informational（flag-on 時亦走 test 或明確不進 threshold），不得以全段值入選。

## 採納的 MAJOR/更正
- **[FIX-A3] row-level cross-symbol N/A**（Codex #9 高信心）：`analyze()` 單幣輸入無 row-level symbol 欄，[A-3] allowlist 只能驗 metadata symbol。**改** [A-3]/Task 1.3 測試為「metadata symbol 缺/不在 allowlist→fail-closed」；row-level 污染→§N 標 cut1 N/A，留 cut2/multi-symbol。
- **[FIX-BRIEF] 預設策略矛盾**（兩家）：BRIEF「§風險與防護」殘留「新算法一律藏在預設關閉的開關後」與 default-ON 決策矛盾。**改** BRIEF 該句；SPEC §C 加註「簽核後 default ON，flag=逃生口」。
- **[FIX-GOLD] G-OLD 不可重現**（兩家）：config_hash「取最新」非 deterministic。**改** §G 寫死 input path + config_hash + freeze 命令；gate：未凍 baseline 不得派工（artifact gate 把關）。
- **[FIX-FREQ] timeframe 升格已驗證**（兩家）：實跑 `pd.Timedelta('1h'/'4h'/'12h')` = `01:00:00 / 04:00:00 / 12:00:00`。**改** §A 貼實跑輸出；Task 1.2 補非法 timeframe（`"1H"`/`"60m"`）fail-closed 表。
- **[FIX-FLAG] flag SSOT**（兩家）：`ic_config.py` 只是 re-export，schema 在 `ic_config_schema.ICConfig`。**改** Task 5.1 寫死 flag 加到 `ICConfig` 哪個 section + API `config_override` path。
- **[FIX-CACHE] golden 命名**（Codex MINOR）：baseline 檔名含 symbol/timeframe/config_hash/split_id。

## 未採納/降級
- Composer「stage6 cache split-aware」「§G 半空殼」：cut1 單幣風險低 → §N 登記，非 BLOCKING。
- 「多數 pytest 路徑尚不存在」：草稿階段預期；TODO 生成時對應真實檔名（兩家同意非 BLOCKING）。

## 結論
兩家無「根本缺陷需重作」；皆「需修補後派工」。採納全部 4 BLOCKING + 6 FIX → 修 BRIEF/manifest（+[C-4][C-5][D-3]）/SPEC → 重跑機檢 → 落 docs/ 正式 SPEC + 生 TODO → 第二輪 SPEC/TODO 雙家族 adversarial。

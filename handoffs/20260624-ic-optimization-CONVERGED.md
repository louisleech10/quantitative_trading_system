# IC-Analysis 架構優化 — 三方收斂版（Round 3 Reconcile）

> 2026-06-24 ｜ Claude + codex(GPT-5.5) + cursor(composer-2.5) 各產獨立完整版(Round1) → 三方全範圍互審(Round2) → 本收斂版。
> **狀態：技術架構兩輪內收斂**。殘留項皆為「需 microbench/讀碼的實證」或「需使用者拍板的產品決策」，非模型歧見 → 不需第三輪模型互辯。
> 來源：handoffs/20260624-ic-optimization-ROUND{1,2}-{CLAUDE,CODEX,CURSOR}.md

## A. 三方一致的技術定案（CONVERGED，可直接進 SPEC）

### A1. 核心架構：直讀 L7、永不物化全矩陣
- **繞過 `_materialize_features_for_ic`（ic_analysis_service.py:188-193, 1116-1136）**——它先 `FeatureLibrary.load()` 成全 DataFrame 再寫 HDF5，是串流前的爆點（cursor B1 / codex 盲點）。主路改為 **direct L7 source**。
- 新介面：`FeatureMatrixSource`（持 symbol/tf/config_hash/index/catalog/fingerprint，不持矩陣）+ `ColumnChunkIterator`（load_columns_v2 欄投影）+ `RowMaskPlan`（event/split/valid-label 轉 mask 不複製）+ `MetricSink`（append-only Parquet/Arrow，支援 resume）+ `CandidateSet`（stage5 後名單）。
- **重用 `compute_ic_from_l7_raw`（ic_engine:104-266）的 manifest/group 串流/fingerprint/cache 思路**，但它只產 scalar IC selection JSON，無 rolling/grouped/decay/stage5/report/deep → 用 MetricSink/CandidateSet 補完整契約（codex 裁決）。

### A2. 分階段（staged）— 但「沒算」≠「沒通過」
- **Stage A（全特徵 exact，串流）**：coverage/NaN/inf/constant gate + exact IC（Spearman/Pearson）+ ICIR。對 430K 全做，輸出 metric table。
- **Stage B（僅 candidates）**：rolling 全序列、decay、grouped、redundancy(VIF/corr)、10 deep 模組。
- **紅線（三方一致）**：因 memory/time cap 而未算的特徵必須標 `not_evaluated` / `scope=top_k`，**絕不可記為 failed 或 passed**；只有「已證 invalid」才能 early-skip。

### A3. per-tier chunk：保守起步 + memory governor 校準
- **8GB 初始 512（不接受 2048 起跳）**；governor 禁「chunk 內存 rolling dict」前提下 microbench 上調。單 worker 峰值 ≤35% RAM、多 worker 總 ≤60%。
- 我的 Round1 2K@8GB 被否決（漏算 Spearman ranked matrix + rolling corr copy + pandas 2-3x，ic_engine:288-302）。
- chunk_cols 對齊 parquet group 邊界避免碎片化讀（cursor B2）。

### A4. redundancy / deep 硬上限（O(k²/k³) 保護）
- redundancy candidate 預設 **200**（沿用既有 `max_features_for_correlation=200`，ic_config_schema:154）；VIF 8GB≤100、32GB≤200；超出 deterministic ranking 截斷 + report 標 `redundancy_input_truncated=true`。
- centrality/orthogonalize/PCA candidate-only 硬上限；rolling 序列只 top-N 保留供 trend/centrality。

### A5. cross-sectional：exact 為正式 gate
- 禁 `pd.concat(frames)`（ic_analysis_service.py:143-154）。
- **feature-chunk × timestamp-block exact** 為正式 gate；per-symbol survivor 粗篩(≤500) 只能 fast/exploratory（會漏 cross-sectional-only 因子，三方一致紅線）。
- run key 含 sorted `(symbol, config_hash, fingerprint)`；symbol 來源隔離。

### A6. winsor/標準化
- **優先重用 FF L7 processed artifact**（byte-faithful 驗證 FF 已 winsorize 則不重算，防雙重處理）；必須 IC 側做則 **exact two-pass，分位只從 train/selection window**。t-digest 僅 exploratory（近似分位改 NaN/outlier gate，無 golden 不可當 default）。

### A7. 輸出（最小但不可有損）
- API JSON 只回 top-N + counts + artifact URI；full metric table 落 Parquet。
- **IC/p-value/ICIR metric 不預設 float32**（codex 否決我的「float32 摘要」——違反「最小輸出不可有損」紅線，除非 golden 證無損）。

### A8. Hotfix（止血，先合併）
- GroupedConfig `.model_dump()`（crash）；`by_volatility` 實作或 fail-closed（不靜默關）；decay warning 聚合（熱迴圈零 log）；主 analyze `asyncio.to_thread`；WS failed→顯真錯誤+停重連+HTTP fallback；`max_features=30` 改名 `preview_limit`（不當正式截斷）。

### A9. 正確性紅線（三方一致，必 golden）
- **B6/P0 洩漏（cursor 新揪）**：主 pipeline 零 `selection_window`/`split_id`，PIT/train-val-test **只存在於 compute_ic_from_l7_raw，UI analyze 路徑無切分** → 必須補；feature selection/FDR/redundancy ranking/winsor 分位**不得用 test 或未來窗**。
- **B7/P0 時間軸**：HDF5 materialize 寫秒（`//10**9`, :1162）但 `_get_time_index` 假設 ms（ic_engine:1025）→ grouped IC 軸錯；改實測判斷 + sanity check（1970/未來日期 fail-closed）。
- golden 清單：streaming IC≡full path、Spearman tie/NaN、rolling ICIR stride/window(Welford vs prefix-sum 需 golden 定)、timestamp 秒/毫秒、resume hash 一致、一 symbol 兩 config_hash、防 stale cache、防跨 symbol、cross-sectional 對齊不變量。

## B. 待實證項（動工前讀碼/microbench，非歧見）
1. 8GB 官方初始 chunk 值 + 降載公式 → 讀真實 430K manifest 的 group 分佈 + microbench RSS。
2. Stage1 preprocessor 跨欄操作清單 → 逐一分類 streaming-safe vs candidate-only（codex）。
3. ProcessPool vs ThreadPool on macOS spawn 的 h5py 開銷 → microbench（scripts/b7_l65 模式）後定，預設單 worker。
4. 舊 run 無 row_index 的串流軸 fallback（cursor B4）。
5. persistent task registry（現 `_tasks` 記憶體，server restart 後 resume 失效，cursor B/codex 盲點）+ partial-parquet 原子提交 + chunk checksum + completed marker（exactly-once）。

## C. 需使用者拍板的產品決策（committee 無法代決）
1. **staged screening 預設模式**：互動式預設「Stage A 全特徵 exact + Stage B 只對 candidates」可接受嗎？還是要「full mode」全量深析（慢很多）作預設？（scale vs 量化完備性的根本取捨）
2. **cross-sectional full-exact 可接受 runtime**：100 symbol × 430K exact 串流仍很慢——你能接受多久？要不要「先 per-symbol 粗篩→fast mode」當預設、exact 當 opt-in？
3. **FF 上游 430K 爆炸是否同步加 cap**：是否在 Feature Factory 端對 indicator×period×window×lag 笛卡爾積加 hard cap / preview 警示（治本上游，但屬 FF epic）？
4. **API response schema 變更**：輸出改 top-N+artifact URI 會動 API 契約——要不要版本化保前端相容？

## D. 落地 epic 順序（三方收斂）
E0 止血(A8) → E1 feature_filter 落地(A8 改名+真套用) → E2 direct L7 source(A1) → E3 串流 IC engine(A2) → E4 stage5/6 candidate gate(A4) → E5 deep candidate-only → E6 cross-sectional(A5) → E7 golden 套件(A9，貫穿) → E8 perf+輸出(A7) → (E9 FF 上游 cap，獨立)。
**P0：E0 + B6 洩漏修 + B7 時間軸 + materialize 繞過（A1）**——這四個是正確性/止血,最優先。

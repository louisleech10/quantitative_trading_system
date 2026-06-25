**1. 收斂點（三方已同意）**
- 核心瓶頸一致：`430K × 20K` 全矩陣不可物化。Claude 估 float32 34GB / float64 68GB，且 stage4/5/6 都吃全矩陣；Codex 補 pandas/rank/copy 後可到 70-220GB；Cursor 補 rolling 全序列是 TB 級。證據：`handoffs/20260624-ic-optimization-ROUND1-CLAUDE.md:7-10`, `...ROUND1-CODEX.md:13-19`, `...ROUND1-CURSOR.md:13-20`；現碼 `_load_features_hdf5` 直接 `features[:]`：`momentum/Analysis/ic_filter_orchestrator.py:1600-1625`。
- 主路必須改成 column/group streaming + metric spill，不再以 `pd.DataFrame features_df` 作為全流程載體。證據：Claude `:14-18`，Codex `:7-12`，Cursor `:22-48`。
- `FeatureReader.load_columns_v2` / L7 raw streaming 是可用基礎，但不是完整主流程。證據：`momentum/FeatureEngineering/feature_reader.py:115-160`, `momentum/Analysis/ic_engine.py:104-266`；Cursor 明確主張收斂到 `compute_ic_from_l7_raw`：`...CURSOR.md:3-6`。
- stage6 / deep modules 必須 candidate-only，不能對 430K 做 corr/VIF/PCA/orthogonalization。證據：Claude `:39-43`，Codex `:50-65`，Cursor `:166-205`。
- cross-sectional 現況不可接受：service 目前 `load_multi` 後 `pd.concat(frames)`。證據：`api/services/ic_analysis_service.py:130-154`；三方都主張 symbol/feature/timestamp 分塊：Claude `:24-28`，Codex `:67-73`，Cursor `:78-82`。
- NaN/inf gate、stale cache、防跨 symbol 污染、PIT/label shift 都是紅線，不能用速度換掉。證據：Codex `:75-100`，Cursor `:218-230`，Claude `:45-50`。

**2. 分歧點與裁決**
- `chunk_cols` 數字：Claude 8GB=2K、32GB=16K；Codex 8GB=512、32GB=4096；Cursor 8GB=2048、32GB=12288。裁決：Round 3 採「保守 memory governor + 實測校準」，8GB 初始 512 或 1024，不接受固定 2048 起跳。理由：現碼 Spearman 會產生 ranked matrix + numpy float copy + rolling corr/list，Cursor 單 chunk 峰值只按 `×2.5` 估，漏了 rolling/rank/list 和 worker 疊加。證據：`...CLAUDE.md:15-17`, `...CODEX.md:21-30`, `...CURSOR.md:35-43`; `momentum/Analysis/ic_engine.py:288-302`。
- staged screening 是否改語義：裁決：Stage A 可以對「全特徵」做 exact IC/ICIR/coverage/NaN/constant；但任何只看 top-K 後才做 monotonicity/grouped/decay/deep 都是語義變更，必須標 `not_evaluated` 或 `scope=top_k`，不能當 failed/passed。證據：Codex 已寫 early-skip 只能 invalid：`...CODEX.md:96-100`；Cursor 承認 decay/grouped/top-K 會變：`...CURSOR.md:279-282`；Claude 對 staged screening 漏交互效應提出疑問：`...CLAUDE.md:74-76`。
- redundancy candidate 上限：Claude/Codex 給 500-3000 等級；Cursor 主張 200，VIF 更低。裁決：預設採 Cursor 200，VIF 8GB≤100、32GB≤200；超出用 deterministic ranking 截斷並在 report 寫 `redundancy_input_truncated=true`。理由：現有 config 已有 `max_features_for_correlation=200`，且 corr/VIF 語義本來跨 feature，寧可小而可重複。證據：`momentum/Analysis/ic_config_schema.py:154-157`, `...CODEX.md:50-51`, `...CURSOR.md:166-171`。
- cross-sectional long-panel vs feature-chunk：裁決：正式 gate 不能只用 per-symbol IC 粗篩到 ≤500，因為會漏 cross-sectional-only 因子；先實作 exact feature-chunk × timestamp-block 模式，survivor long-panel 只能是 fast/exploratory。證據：Cursor 提議 per-symbol 粗篩 ≤500：`...CURSOR.md:80-82`; Codex 已警告 per-symbol 粗篩有漏因子風險：`...CODEX.md:185`; 現況 concat 爆點：`api/services/ic_analysis_service.py:143-154`。
- streaming winsor 兩遍 vs t-digest：裁決：official path 用 exact two-pass，且分位數只能從 train/selection window 來；t-digest 只能 exploratory，因為近似分位可能改 NaN/outlier gate 和 IC。證據：Claude 提兩遍或 t-digest：`...CLAUDE.md:34`, `:78`; Cursor 提 two-pass / processed artifact 並要求 train window：`...CURSOR.md:101-105`, `:229`; Codex 要跨欄 preprocess 分類：`...CODEX.md:36`。
- 是否重用 `compute_ic_from_l7_raw`：裁決：重用其 manifest/raw group/fingerprint/cache 思路，但不能直接當主流程，因為它只產 scalar IC selection JSON，沒有 rolling/grouped/decay/stage5/report/deep 契約。證據：`momentum/Analysis/ic_engine.py:104-266`; Cursor 主張藍本：`...CURSOR.md:3-6`; Codex 的 `MetricSink/CandidateSet` 是更完整方向：`...CODEX.md:7-12`。
- 輸出 float32 / top-N / parquet：裁決：API JSON 只回 top-N + counts + artifact URI；full metric table 落 Parquet。但 IC/p-value/ICIR metric 不應預設 float32，除非 golden 證明無損或明確容忍。Claude 的「float32 摘要」不符合「最小輸出不可有損」紅線。證據：Claude `:52-55`; Codex `:112-118`; Cursor `:251-260`。
- `feature_filter/max_features`：裁決：`max_features=30` 不得在 Stage0 當正式截斷；要改名 `preview_limit`，或明示「粗篩模式」。正式分析預設全特徵 exact Stage A。證據：前端預設 `max_features: 30`：`frontend/src/store/icAnalysisStore.ts:182-188`，hook 送出：`frontend/src/hooks/useICAnalysis.ts:156-159`，API 只塞 override：`api/services/ic_analysis_service.py:967-970`，核心 config 沒 `feature_filter`：`momentum/Analysis/ic_config_schema.py:64-180`。
- grouped `by_volatility`：裁決：必須實作或 fail-closed，不接受「8GB tier 預設關閉」作為靜默行為。證據：schema 預設 true：`momentum/Analysis/ic_config_schema.py:76-80`；`rg` 只找到 schema，engine 無 `by_volatility` 分支；grouped 現碼只處理 year/quarter/regime/category/data_source：`momentum/Analysis/ic_engine.py:365-410`。

**3. 三方都漏的 / 未收斂盲點**
- 沒有一份給出可執行的 RSS 校準 gate：每個 stage 的 peak memory、worker 疊加、rank/rolling 暫存、Parquet decode 暫存都需要 microbench + 自動降 chunk，不只是表格估算。
- resume 語義不夠完整：都提 checkpoint/spill，但沒定義 partial parquet 原子提交、chunk checksum、completed marker、重跑 exactly-once、server restart 後 task registry 探測。Cursor 有提 `_tasks` 記憶體問題：`...CURSOR.md:330`，但方案骨架未展開。
- current service materialization 是繞不過的爆點：`_materialize_features_for_ic` 先 `FeatureLibrary.load()` 成 DataFrame，再寫 HDF5。Round 3 必須把主路改為 direct L7 source，否則 streaming engine 前面已經 OOM。證據：`api/services/ic_analysis_service.py:188-193`, `:1116-1136`。
- Stage1 preprocessor 實際操作清單未盤點。若有跨欄 neutralization / rank / zscore，哪些 streaming-safe、哪些 candidate-only、哪些必須 train-only，還沒形成表。
- cross-sectional correctness golden 不足：100 symbol 下 canonical feature name、缺欄、不同 config_hash、不同 row_index、停牌/缺 bar 對齊、PIT label 對齊都要 golden；三方都有方向但沒有完整不變量。
- API/backward compatibility 未定：`summary_table` 不進 JSON 會改前端契約；需要 versioned response 或兼容欄位，而不只是「落 parquet」。

**4. 正確性紅線爭議**
- 必須 golden：streaming IC vs full IC、Spearman tie/NaN 行為、rolling ICIR stride/window、timestamp 秒/毫秒、resume hash、一 symbol 兩 config_hash、防 stale、防跨 symbol cache。Codex golden 清單最完整：`...CODEX.md:143-150`; Cursor 補 UI analyze 路徑：`...CURSOR.md:285-290`。
- staged screening 紅線：不能讓「沒算」變成「沒通過」。invalid feature 可 early-skip；memory/time cap 造成的 skip 必須 `not_evaluated`。
- approximate 紅線：t-digest、random projection、sketch correlation 不能是 default gate，只能 exploratory/debug。
- cross-sectional 紅線：per-symbol survivor 預篩不能是唯一正式 gate，因為它會漏 cross-sectional 相關但單 symbol 弱的因子。
- train/val/test 紅線：feature selection、FDR threshold、redundancy ranking 不得使用 test；winsor/zscore 分位也不能從 test 或 future window 估。證據：Cursor `:222-229`, Codex `:84-89`。

**5. 收斂建議：Round 3 採納骨架**
- P0 Correctness Contract Hotfix：GroupedConfig `.model_dump()`、timestamp unit inference、`by_volatility` fail-closed/實作、decay hot-loop log 聚合、API `to_thread`。這些低風險且解除當前 crash/假死。證據：`momentum/Analysis/ic_filter_orchestrator.py:1133-1140`, `momentum/Analysis/ic_engine.py:943-958`, `api/services/ic_analysis_service.py:209-216`。
- P1 Direct L7 Streaming Source：新增 `FeatureMatrixSource/ColumnChunkIterator/RowMaskPlan/MetricSink`，完全繞過 `_materialize_features_for_ic` 和 HDF5 `features[:]`。先 single worker + conservative chunk，實測後再開並行。
- P2 Exact Stage4/5 Streaming：全特徵 exact IC/rolling summary/FDR/NaN/coverage metric table，Parquet spill + checksum + resume；API 只回 top-N + artifact refs。
- P3 `feature_filter` Contract：`max_features` 改 `preview_limit` 或明示粗篩；metadata include/exclude 可 Stage0，品質 top-K 只能 Stage5 後。
- P4 Candidate-only Expensive Modules：redundancy default 200、VIF lower cap、decay/grouped/deep top-K scope 必須寫進 report，不影響 base IC gate。
- P5 Cross-sectional Exact Streaming：先 feature-chunk × timestamp-block exact mode，再加 survivor fast mode；所有 run key 含 sorted `(symbol, config_hash, fingerprint)`。
- P6 Perf Tuning：Numba/prefix sums/process pool/t-digest/sketch 只能在 P0-P5 golden 穩定後進。

仍需 Round 3 再議：官方 8GB 初始 chunk 值與降載公式、Stage1 preprocessing 實際清單、cross-sectional full exact 的可接受 runtime、API response versioning、spill retention policy、是否在 FF 側限制 430K 爆炸來源。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、三份 Round-1 全文；抽讀 ic_filter_orchestrator.py、ic_engine.py、feature_reader.py、ic_analysis_service.py、ic_config_schema.py、ic_models.py、前端 store/hook 關鍵行。
TESTS_RUN: none，READ-ONLY 架構互審。
FAILURES_SEEN: none。
SCOPE_CHANGES: none。
NUMERIC_OR_SCHEMA_IMPACT: 本次未改檔；建議方案若落地會改 IC orchestration、output/API schema、timestamp/grouped 行為，需 golden。
HANDOFF_NOT_UPDATED: 使用者明示 READ-ONLY 且要求審查寫在輸出，不改 repo 檔。
STATUS: DONE
# 階段一 — Codex 獨立版

說明：你最後一句寫「逐 6 種分析」，但 SCOPE-FINAL 明確列 4 種；我按已定範疇交 4 種。第 4/5 欄已讀碼查證。

## 1. 分位 / 單調性分析

1. 🔍 核心問題（白話）  
   特徵值越高，未來報酬是否越好？還是只在極端分位有效、或完全不單調？

2. 📐 業界標準做法  
   對每個再平衡時點把樣本切成 Q1-Q5/Q10，計算各分位未來報酬、long-short spread、t-stat、分位曲線、turnover；最好在 train 估規則、validation/OOS 驗證，不用全樣本一次看完。

3. 🗂 資料形狀與輸入  
   標準：Panel `(timestamp, symbol, feature, forward_return)`。事件 case-control 可用事件清單 + label，但要保留事件 timestamp、symbol、正/反例標籤。單標的時序只能回答「這個 symbol 內部是否單調」，不能代表泛化。

4. 📊 平台現況 + 實際怎麼實作  
   後端在 `MonotonicityTester.compute_all()` 對每個 feature 做 `pd.qcut`，用整段 `features_df + label_series` 算 `quantile_mean_returns`、`long_short_spread`、`monotonicity_score`。主流程 `_stage5_statistical_validation()` 一律計算。  
   實際是 **單 run / 單 symbol longitudinal 時序**，不是 pooled multi-symbol IC。`analyze_cross_sectional()` 回傳 `quantile_returns: {}`、`monotonicity_score: None`。  
   沒有 train/test 切分；UI 的 Feature 預過濾只影響前端選取，`feature_filter` 送到後端後被 `ICConfig` 忽略。

5. 🧩 全棧實作狀態  
   判定：✅ longitudinal 全棧連通；⛓️‍💥 feature_filter 兩端有但沒連結；❌ cross-sectional 分位/單調性缺。  
   後端：有。前端：`QuantileReturnChart` 有，summary table 有 `monotonicity_score`。wiring：report `quantile_returns` → page → chart 通。漏洞：前端預過濾不會改變後端分析矩陣。

6. 🛡️ PIT 與洩漏防禦  
   最大地雷是用全樣本 qcut 邊界與全樣本單調性挑 feature，再把同一批資料拿去訓練/回測。事件研究還要避免用事件後資訊建分位或篩選正反例。

7. ⚡ 430K×20K×百 symbol 尺度對策  
   不能 materialize 全矩陣後逐 feature qcut。應採 streaming / chunked feature blocks、先 feature_filter 真正下推、每 symbol 獨立統計再合併、分位統計用 approximate quantile 或預先 sample train window，OOS 只套 train 分位邊界。

8. 🔧 做對沒 / 漏洞  
   做對：基本分位報酬、long-short、單調性分數已有。  
   漏洞：無 pooled panel、無 train/test、無事件清單語意、無 cross-sectional quantile、feature_filter 幽靈失效、全樣本 qcut 對泛化結論不可信。

9. 🏷️ 優先級  
   P0：修 feature_filter 後端下推 + train/OOS 分位邊界。  
   P1：補 pooled/event-aware quantile。  
   P2：補 cross-sectional 分位分析。

## 2. IC 衰減 / 半衰期

1. 🔍 核心問題（白話）  
   訊號能預測多久？1 根 K 有效、5 根 K 有效，還是半衰期很短只是假象？

2. 📐 業界標準做法  
   對多個 forward horizon 算 IC(h)，看 peak horizon、符號是否穩定、decay curve、half-life；半衰期只在衰減形狀合理時解讀，不應強行擬合所有 feature。

3. 🗂 資料形狀與輸入  
   需要 PIT feature matrix + 原始 close 或已生成的多 horizon forward returns。Panel 最好；單標的時序只能得單 symbol horizon profile。

4. 📊 平台現況 + 實際怎麼實作  
   `ICEngine.compute_ic_decay()` 對 horizons `[1,2,3,5,8,13,21]` 用 `close.shift(-horizon)/close - 1` 生成 label，再對所有 feature 算 IC，最後 `_fit_exponential_decay()` 擬合 half-life。  
   只有 `_stage4_ic_calculation()` 能拿到 `kline_reader` 且 `raw_data` 有 `close` 時才跑；若 request 自帶 `labels_path` 或 cross-sectional mode，`ic_decay` 為空。無 train/test 切分。

5. 🧩 全棧實作狀態  
   判定：⚠️有但壞掉 / 脆弱。  
   後端：有核心實作。前端：`ICDecayChart` 有。wiring：report `ic_decay` → page → chart 通。限制：只在部分入口有資料；cross-sectional 無；全樣本擬合可能給出不可靠 half-life，雖然已有 fit warning。

6. 🛡️ PIT 與洩漏防禦  
   `shift(-horizon)` 本身是 forward label，作為評估可以，但不可在 feature 生成或分位邊界中混入未來。多 horizon 共用同一全樣本挑 feature 會造成 multiple testing / horizon snooping。

7. ⚡ 430K×20K×百 symbol 尺度對策  
   需要 horizon × feature block streaming；不要對 20K features 每個 horizon 重複整矩陣 rank。可先計算 label matrix，多 horizon 分塊相關；只對候選 top-K 做 half-life fit；百 symbol 先 per-symbol decay，再 pooled meta-summary。

8. 🔧 做對沒 / 漏洞  
   做對：多 horizon、peak horizon、half-life、fit_r2/warning 都有。  
   漏洞：入口依賴 `raw_data`，有時空結果；無 OOS；無 pooled；沒有校正 horizon snooping；half-life 對非衰減型 IC 容易被過度解讀。

9. 🏷️ 優先級  
   P0：讓 decay 明確 fail/skip reason，不要只是空圖。  
   P1：train/OOS horizon validation + pooled per-symbol summary。  
   P2：只對候選 top-K 做 scalable half-life。

## 3. 分組 / 狀態 Regime 條件 IC

1. 🔍 核心問題（白話）  
   訊號是不是只在牛市、高波動、某類事件、某些 symbol 有效？環境錯了會不會反向？

2. 📐 業界標準做法  
   先定義 PIT regime：volatility, trend, liquidity, market phase, event subtype。分組後算 IC mean、ICIR、hit rate、樣本數、方向一致性；regime 定義必須只用當下或過去資料。

3. 🗂 資料形狀與輸入  
   Panel + regime labels 最好。事件 case-control 應是事件清單 + 顯式 event label，如正例/反例、pattern subtype、市場狀態。單標的時序只能做該 symbol 的 regime IC。

4. 📊 平台現況 + 實際怎麼實作  
   `compute_grouped_ic()` 支援 `by_year/by_quarter/by_regime/by_category/by_data_source/by_layer`。`by_regime` rule 用 `close.ewm(55)`、`pct_change().rolling(55).std()` 分 bull/bear/high_vol/low_vol；也有 kmeans path。  
   `EventFilter` 支援 query/timestamps，但 `_stage3_event_filter()` 固定 `timestamps = None`，所以 API 的 `event_timestamps` 被 service 警告「not supported」。event query 可用，但不是顯式事件清單。`GroupedConfig.by_volatility=True` 存在，實作沒有 by_volatility 分支。

5. 🧩 全棧實作狀態  
   判定：⚠️有但壞掉 / 部分靜默失效。  
   後端：grouped/regime 有；event timestamps schema 有但不通；by_volatility config 有但不通。前端：`GroupedICBarChart`、`RegimeRadarChart` 有。wiring：`grouped_ic` report 通。問題：顯式事件清單缺、cross-sectional grouped 空、部分 config 欄位是假開關。

6. 🛡️ PIT 與洩漏防禦  
   regime 若用全樣本 percentile 定 high/low volatility，threshold 本身偷看未來分布。kmeans expanding 較接近 PIT，但仍需確認 fit 只用過去。事件 query 若包含 future_return 類欄位，會直接洩漏。

7. ⚡ 430K×20K×百 symbol 尺度對策  
   regime labels 應預先按 symbol/timeframe 生成並快取；IC 計算按 `(symbol, regime, feature_block)` streaming 聚合。事件 case-control 要用 event_id 清單下推，不要先載完整 20K features 再 filter。

8. 🔧 做對沒 / 漏洞  
   做對：已有 trend/vol rule regime、metadata group、UI 圖。  
   漏洞：無 pooled regime IC；事件清單不通；by_volatility 假欄位；全樣本 percentile 可能洩漏；無每組樣本數/置信度在 UI 上強提示。

9. 🏷️ 優先級  
   P0：接通 `event_timestamps` / event list，禁止 future 欄位 query。  
   P1：修 by_volatility 或移除假 config；regime threshold 改 rolling/train-only。  
   P2：pooled regime IC + per-symbol consistency。

## 4. 穩定性 / 一致性（Win Rate, ICIR）

1. 🔍 核心問題（白話）  
   平均 IC 不是一次爆出來的嗎？方向是否常常對？不同時間、symbol、窗口是否穩定？

2. 📐 業界標準做法  
   rolling IC series、IC mean/std、ICIR、hit rate/win rate、t-stat、confidence interval、per-symbol consistency、walk-forward/OOS degradation。不能只看全樣本平均。

3. 🗂 資料形狀與輸入  
   時序 rolling 需要單 symbol 或 panel time index；一致性需要 multi-symbol panel；事件型需要事件批次、時間切分、symbol 分層。

4. 📊 平台現況 + 實際怎麼實作  
   `compute_rolling_ic()` 先全列 rank，再 rolling correlation；`compute_icir()` 用 configured window 的 rolling IC 算 `ic_mean/ic_std/icir/ic_hit_rate`。`StatisticalValidator` 對 rolling IC 做 t-test。  
   cross-sectional mode 有 `summary_table.icir/ic_hit_rate` 和 `cross_symbol_validation`，但不是主路徑 pooled IC。主路徑沒有 train/test；deep `rolling_oos` 模組存在，但屬另一路徑且需深度分析。

5. 🧩 全棧實作狀態  
   判定：✅ 基礎 rolling/ICIR 全棧連通；🔌 OOS 穩定性屬後端 deep module + 前端 deep tab，非主 gate；❌ pooled IC 主路徑缺。  
   後端：有 rolling IC、ICIR、hit rate、cross-symbol validation。前端：summary table、`RollingICChart`、`CrossSymbolValidationPanel` 有。wiring：主 report 與 deep report 均有消費路徑。

6. 🛡️ PIT 與洩漏防禦  
   rolling IC 可作診斷，但若用全樣本 rolling 結果挑 feature 再回測，就是 selection leakage。`compute_rolling_ic()` 對整段序列 rank 後再 rolling，Spearman rolling rank 嚴格來說應在每個 window 內 rank；全段 rank 會引入分布資訊洩漏/尺度偏差。

7. ⚡ 430K×20K×百 symbol 尺度對策  
   rolling IC 應 block-wise 計算並只保留摘要或 downsample series；對 20K features 不應全部送前端。百 symbol 應輸出 per-symbol ICIR distribution、sign agreement、worst-decile，不只平均。

8. 🔧 做對沒 / 漏洞  
   做對：ICIR/hit rate/t-stat/rolling chart 已形成閉環。  
   漏洞：無 train/test 主 gate；rolling Spearman ranking 方式可疑；pooled IC 缺；feature_filter 幽靈導致尺度與結論都錯；cross-symbol consistency 有但不是事件 case-control 的分層穩定性。

9. 🏷️ 優先級  
   P0：主 IC gate 加 train/OOS split 與真 feature_filter。  
   P1：修 rolling Spearman 為 window-local rank 或明確改 Pearson-on-global-rank 並標示。  
   P2：pooled/per-symbol consistency 報表成為主流程指標。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md；已查 `ic_engine.py`、`ic_filter_orchestrator.py`、`event_filter.py`、`ic_analysis_service.py`、`ic_models.py`、`ic_config_schema.py`、`ic_reporter.py`、`monotonicity_tester.py`、`api/routes/ic_analysis.py`、`frontend/src/app/ic-analysis/page.tsx`、`frontend/src/components/ic-analysis/*`、`frontend/src/hooks/useICAnalysis.ts`、`frontend/src/store/icAnalysisStore.ts`、`frontend/src/lib/types.ts`。  
TESTS_RUN: read-only 任務，未跑測試；只執行 `sed`/`rg` 讀碼查證。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none；因 read-only 未改檔。  
NUMERIC_OR_SCHEMA_IMPACT: none  
HANDOFF_NOT_UPDATED: 使用者明示 READ-ONLY，且 sandbox 為 read-only；未寫 `HANDOFF.md` 或 `handoffs/*`。  
STATUS: DONE
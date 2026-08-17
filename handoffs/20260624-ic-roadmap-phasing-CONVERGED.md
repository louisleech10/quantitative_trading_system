# IC 地圖修法 — 分階段執行計畫（四家委員會收斂）

> 🔴 2026-08-17 pointer（ICHC Task 6.4；本檔內文不改，provenance 凍結）：
> Phase 0/1 大宗已由 la0–1d/1e+1b/ICHC 諸 epic 完成；殘項與 Phase 2A/3/4 缺口的
> **現行 SoT＝`docs/IC_QUANT_GAP_REGISTRY.md`**（六票對照本檔 Phase 編號）。

> Claude 草案 → codex(contract-first) + Gemini(量化研究價值) + cursor(雙軌/前端返工) challenge → 本收斂版。
> 四家獨立版見 handoffs/20260624-ic-roadmap-phasing-{CLAUDE,CODEX,CURSOR,GEMINI}.md。

## §0 核心排序：定案 = Contract-First + 雙軌並行（非二選一）
四家共識(我原本的二分法被修正):
- **不要 streaming-first 大重寫先行**(方法未驗就上大管線=高風險)。
- **也不要在舊 materialized 路徑硬補正確性**(之後 direct-L7 串流會繞過 → 返工:把 FDR 接舊 Stage5、前端接舊 JSON、在 _materialize 上修 split → 白做)。
- **更不能把大尺度整包丟最後**(cursor:45K 是**現況 blocker**,止血後仍不可互動,不是未來需求)。
- **定案做法**:
  1. **先定 contract**(RowMask/split、artifact output、FDR selection scope、candidate set)——讓正確性修法落在新契約上,不返工。
  2. **正確性 kernel + 薄串流脊骨並行**:統計 kernel(FDR/Net IC 公式/HAC/attribution)不會白做(Gemini:記憶體版正好當串流的 **Ground Truth 單元測試**);薄串流脊骨(direct L7 source + chunk iterator)只要讓 45K 可互動即可。
  3. **避免**:把正確性硬接進舊全 DataFrame 路徑。

## §0b Phase 2 vs Phase 3：定案 = 不互斥,切 2A/2B
- 事件 case-control **列數稀疏但欄仍 430K**(codex)→ 語義 kernel 可小尺度先做(Gemini 的即時價值),全量篩選必須等串流(codex/cursor)。
- **事件路徑 fail-closed + event_timestamps 接通 + IC-FEATURE-GUARD(輸入 universe 正確)= P0 前置**,比完整 matching 更急(cursor:幽靈全跑時事件 IC 的 universe 本身就錯)。

## 收斂後 Phase 計畫

### Phase 0 — 止血 + 正確性硬閘（立即可動,已 reconcile）
- GroupedConfig 崩潰修 + 真 config 回歸測試。
- **feature_filter 幽靈落地**(= Phase 2 前置,不只效能)+ preview_limit 改名(需 API schema 版本化)。
- analyze to_thread + WS 顯真錯誤 + 停無限重連。
- **+timestamp 秒/毫秒 fail-closed + by_volatility fail-closed**(codex/cursor:正確性,否則 grouped 修了軸仍錯)。
- decay 熱迴圈 log 聚合。
- **依賴:無。來源:ic-grouped-crash-perf-ANALYSIS.md(三方 reconcile)。工時:小。**

### Phase 1 — 正確性 kernel + contract（能信）｜中,2-4 週(cursor 修正,別低估)
> 統計 kernel 做成獨立可測,落在新 contract 上,當未來串流的 ground truth。
- **1-contract**:定 RowMask/split、artifact output、FDR scope、candidate set 契約(先,避免返工)。
- **1a train/test split**(feature selection/winsor fit/FDR reporting/事件 OOS 的前提;本質=index/timestamp 遮罩)。
- **1-align(Gemini 紅線,新增)**:前瞻偏誤硬閘——Feature_t vs Target_t+1 timestamp 對齊檢測(差 1 tick IC 就爆)。
- **1b FDR 接線**(後處理 p 值陣列,與矩陣計算正交;需知 selection scope 非全 split)。
- **1c Net IC 量綱修正**(Grinold + turnover/autocorr 折價,非粗估;Gemini)。
- **1d factor_attribution 接真實作**或 UI 正名 proxy。
- **1e HAC/block bootstrap**(與 train/test 正交,cursor;修 rolling IC 自相關 + 重疊報酬,Gemini)。
- **1f 靜默空圖修**(schema flatten)。
- 並行軌:薄串流脊骨(direct L7 source + chunk iterator)。

### Phase 2A — 事件 case-control 語義 kernel（主戰場,小尺度先驗）｜大,需設計
> Gemini:列數稀疏→即時高 alpha 價值,不必等全量串流。
- 顯式事件清單[ts,symbol,正/反] ingestion + 事件前窗對齊 + 判別指標(AUC/t-stat) + 正反 matching(同波動/regime) + 事件 OOS(purged CV) + FDR + 波動率調整。
- **依賴:Phase 0 前置(fail-closed/timestamps/feature_guard)+ Phase 1 子集(split/mask contract、FDR kernel)。**

### Phase 3 — 串流承載（能跑 430K×百 symbol）｜大,基礎軌
- direct L7 + chunk iterator + row mask + metric sink + candidate set + staged screening + redundancy cap + cross-sectional 串流。
- **依賴:Phase 1 contract;接回 Phase 1 正確性 kernel。來源:ic-optimization-CONVERGED.md。**

### Phase 2B — 事件 case-control 大尺度整合｜中
- event mask × streaming feature chunks + artifact output + 全 430K feature universe 篩選。
- **依賴:Phase 2A + Phase 3。**

### Phase 4 — 整合 + 進階｜中
- IC→ML 橋(决策:**复用 ML 孤島 vs 重寫,差 3-5× 工時**,cursor)、多因子組合+邊際/residual IC+HRP/Grinold、DSR/PBO/MinBTL、Pooled IC、容量、centrality auto-run。

### Phase 5 — Agent 顧問層（V2）｜大
- 結構化可機讀輸出 + 嚴謹度指標 + Agent 委員會式解讀。依賴 Phase 1(正確性)+ Phase 4(嚴謹度指標)。

## 起點（四家一致）
**Phase 0 止血 + 正確性硬閘**——已 reconcile、小、解你實測崩潰卡死、不依賴任何決策、且其中 feature_filter/timestamp 是後面 Phase 的前置。**無爭議的第一步。**

## 待使用者決策（committee 無法代決)
1. **walk-forward/CPCV:复用現有 ML 孤島 vs 重寫**(差 3-5× 工時)——影響 Phase 2A/4 範圍。
2. **API response 版本化**(top-N + artifact URI):現在做避免前端返工,但動契約。
3. Phase 2A(主戰場)與 Phase 1 的資源分配:先全力 Phase 1 正確性,還是 Phase 1 + 2A 並進?

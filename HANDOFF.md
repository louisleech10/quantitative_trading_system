# Handoff
**Agent**: Claude | **Time**: 2026-06-17 | **Branch**: main | 最後 commit: c3c40a3

## 給下一個 session:接手就做這些(使用者已拍板,2026-06-17)
研究路線:先把 **crypto 單一市場** 的 FF→IC→ML→回測 跑成完整版;**數據源擴充(Glassnode/CoinGecko/台股/美股)延後**,等四階段完整版再議(三方委員會共識,評估檔 handoffs/20260617-datasource-ff-assessment-{codex,composer}.md)。

### 任務 A(先做,最獨立):修 :4109 ref-cache bug
- **位置**:`feature_factory.py:4109` `factory._reference_data_cache[("BTCUSDT", tf)] = ref_df` —— 多 symbol 批次時 cache key 硬寫 "BTCUSDT",即使傳了別的 `ref_symbol`(:3894)也被覆蓋 → 跨截面特徵**靜默用錯參考標的**。命中高風險 (d)(回測/ML 正確性)。
- 修法方向:cache key 用實際 `reference_symbol`(config 的 cross_sectional.reference_symbol),非硬編碼。
- 流程:完整管線(SPEC→雙家族 adversarial→Composer 實作→Codex review)。**使用者已同意開工**。

### 任務 B(接著做):L6.5 預處理正確性強化(打包成一個計畫)
1. **刪 legacy + IC-First 設為唯一/預設**:現況 IC-First **預設關**(`feature_config.py:240` ic_first_pipeline=False;env FFACT_IC_FIRST_PIPELINE),預設路徑是 legacy(`feature_factory.py:392-409` 分支)。使用者手動在 UI(PreprocessingPanel.tsx)開 IC-First。決定:IC-First 設唯一/預設、移除 legacy 分支+UI 切換鈕+改測試。理由:legacy 的 rank/gaussian/zscore 全樣本→洩漏面較大;IC-First 省記憶體理由仍成立。
2. **FracDiff d\* walk-forward 重估**:現只用前 500 bar 校準一次(`feature_preprocessor.py:170-172,3734`)→長樣本 regime drift。改分段重估提升數據品質。
3. **causal_preprocessing 釘死 True + 警示註解**:`feature_config.py:233` 預設 True、`feature_factory.py:3560` setdefault True,**未上 UI/API**(使用者關不掉)。在定義/setdefault/讀取三處加醒目註解「⚠️必須 True,False=look-ahead 洩漏,禁關,變更需委員會」防 AI 靜默改。
- 流程:命中 (d),完整管線一個計畫。

### 不用現在動
- selection_window/split:IC 引擎已強制(`ic_engine.py:127,453` 沒給就報錯)。等逐一驗證 IC 篩選時再看。

## IC Gatekeeper 真實狀態(使用者原以為「只有項目沒測試」,實際更正)
- **已大量建好**:ICFilterOrchestrator 8 階段全真實作 + 10 個深度分析模組;**79 個 IC 單元測試會過**;前端 ic-analysis 元件齊。接點=V2 manifest + L7 raw parquet。
- **但單元測試全用合成資料(np.random)**,從沒真實 kline 端到端驗證。
- **「真實 kline 三方簽核」= 下一步驗證手段**(選真實 symbol→FF(IC-First)→IC 引擎→委員會查洩漏/算錯→修再跑),不是等完美才跑。是「邊跑真實簽核邊完善」。

## 其他待辦(更後面)
- 多數據源 epic(延後):adapter metadata 合約/AsOf PIT 對齊/MarketCalendar/企業行動。
- float16 strict 讀升 float32;CGSA tier 並行(需 24/32GB);batch_alias Phase 3(batches.json)。
- pre-existing 壞測試:frontend strategy-components.test.tsx 缺 SignalTooltip(與本線無關)。

## 執行端分工(2026-06-15 使用者定)
中/大實作=Composer 2.5 + Codex review;小=Claude 自己做。技術決策走委員會;中途自主 commit。

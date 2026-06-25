# IC 地圖修法 — 分階段執行計畫（Claude 獨立版，待委員會 challenge）

> 來源:handoffs/20260624-ic-map-WHOLEMAP.md 系統性發現 A-H + 優先級。
> 目標:把 ~20 個修法排成有依賴邏輯的 Phase,讓使用者知道先做什麼、為何這順序。

## 0. 核心排序決策（委員會須拍板）
**張力:「正確性先修(小尺度)」vs「大尺度架構先建(430K串流)」。**
- **我的主張:正確性先修,大尺度架構為平行/後置基礎軌。** 理由:
  1. 正確性修法(FDR 接線、train/test、Net IC 公式、factor_attribution)**多為局部、可在現有小/中尺度路徑做**,使用者能**立刻在小 run 上做可信研究**。
  2. 串流重寫改的是「資料怎麼流」,**不是 FDR/split/公式算什麼**——這些正確性邏輯在串流後**可重用,不會白做**。
  3. 在驗證方法對之前就做巨大串流重寫=高風險(萬一方法要改,重寫白費)。
- **但有 caveat:** 有些修法本質需要大尺度處理(FDR 對 43 萬全收 p 值、redundancy O(n²) cap)→ 這些**scale-dependent 部分**等大尺度軌。可在小尺度先驗證演算法對,再接串流。
- **替代方案(待委員會):** 若委員會認為「反正最終要 430K、不如先建地基免得重接」,則 streaming-first。**這是我最不確定的點,優先請委員會挑戰。**

## 1. 分階段計畫（我的版本）

### Phase 0 — 止血（能用）｜小、已 reconcile、立即可動
> 沒這個,使用者連 IC analysis 都跑不動(實測崩潰/卡死)。
- IC-CRASH:GroupedConfig 崩潰修(model_dump)+ 真 config 回歸測試。
- IC-FEATURE-GUARD:feature_filter 幽靈落地(前端送的真的生效)+ 大 run 警示。
- IC-UX-ERR:analyze 改 to_thread + WS 顯真錯誤 + 停無限重連。
- decay 熱迴圈 log 聚合。
- **依賴:無。來源:handoffs/20260624-ic-grouped-crash-perf-ANALYSIS.md(已三方 reconcile)。**

### Phase 1 — 正確性紅線（能信）｜中、局部、現有路徑
> 讓 IC 輸出可信(不是幽靈/算錯/洩漏)。**Agent 顧問層(P2)的前提。**
- **1a train/test 切分主路徑**(最基礎,多項依賴它):主 analyze 加 train/val/test;feature selection 只在 train;winsorize 只 train fit。
- **1b FDR 接線**:把現有 _fdr_bh 接進 Stage5 + 前端 toggle 真送 + schema 加欄。
- **1c Net IC 量綱修正**:改 Grinold 或 Net Return/Sharpe。
- **1d factor_attribution 接真實作**(或 UI 標 proxy 不叫 attribution)。
- **1e IC 顯著性 HAC/block bootstrap**(rolling IC 非 i.i.d.)。
- **1f 靜默空圖修**(schema flatten,分位/多空圖)。
- **依賴:1a 先(train/test 是 1b/1e 的前提:沒切分,FDR/顯著性也是 in-sample)。其餘 1b-1f 可並行。**

### Phase 2 — 主戰場 case-control（你最需要）｜大、需設計
> 使用者真實工作流。需先有 1a(train/test)。
- 顯式事件清單 ingestion[ts,symbol,正/反標籤] + 事件前窗對齊 + 判別指標(AUC/t-stat) + 正反 matching(同波動/regime) + 事件 OOS(purged CV) + FDR + 波動率調整。
- event_timestamps 死線接通;事件不足 fallback 改明確報錯不靜默全樣本。
- **依賴:Phase 1a(切分)、purged CV(可在此建)。最大新建,需獨立設計階段。**

### Phase 3 — 大尺度架構（能跑 430K×百 symbol）｜大、基礎軌
> 真實規模。可與 Phase 1/2 並行(平行軌),或在 1/2 驗證方法後接。
- 串流分塊不物化全矩陣 + staged screening + tier-adaptive chunk + redundancy candidate cap + cross-sectional 串流。
- **依賴:架構獨立,但接回 Phase 1/2 的正確性邏輯。來源:handoffs/20260624-ic-optimization-CONVERGED.md。**

### Phase 4 — 整合 + 進階（更完整）｜中
- IC→ML 橋(IC 倖存者→一鍵 XGB/SHAP 驗證)。
- 多因子組合 IC + 邊際/residual IC(正交化正名)+ HRP/Grinold。
- DSR/PBO/MinBTL(策略層過擬合)、Pooled IC、容量/流動性、centrality auto-run。
- **依賴:Phase 1(正確性)+ Phase 3(大尺度,部分項)。**

### Phase 5 — Agent 顧問層（V2 願景）｜大
- IC 輸出結構化可機讀 + 嚴謹度指標(FDR/OOS/DSR)+ Agent 解讀/委員會式討論。
- **依賴:Phase 1(正確性,否則 Agent 推薦過擬合假因子)+ Phase 4(嚴謹度指標)。**

## 2. 建議起點
- **立即起:Phase 0 止血**(已 reconcile、小、解你實測的崩潰卡死、不依賴任何決策)。
- **緊接:Phase 1a train/test**(基礎,解最大研究有效性洞)。
- Phase 2(主戰場)與 Phase 3(大尺度)的先後 = 核心決策(§0),請委員會與使用者定。

## 3. 待委員會 challenge
1. §0 排序:正確性先修 vs 串流先建——我主張前者,挑戰我。
2. Phase 內依賴對嗎?(如 1a 是否真是 1b/1e 前提;Phase 2 是否真需 1a 全部)
3. 有無漏排的修法 / Phase 切太粗或太細?
4. Phase 2(主戰場)vs Phase 3(大尺度)誰先?(使用者主戰場 vs 真實規模)
5. 每 Phase 規模/工時量級對嗎?

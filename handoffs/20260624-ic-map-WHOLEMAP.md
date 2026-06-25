# IC-Analysis 分析類型全覆蓋地圖 — 全圖總覽（四家委員會定案）

> 2026-06-24 ｜ Claude + codex(GPT-5.5) + cursor(Composer 2.5) + Gemini(agy) 四家委員會 ｜ 5 階段各跑「四家各產獨立版→互審→Claude綜合(亦被審)→收斂」。
> 每階段細節見 handoffs/20260624-ic-map-STAGE{1-5}-FINAL.md。本檔為總覽 + 系統性發現。
> **狀態圖例**：✅全棧連通｜🔌後端有/未接主流程(deep孤島)｜🎨前端展示為主｜⛓️‍💥兩端有但沒連結(靜默失效)｜⚠️有但壞掉｜❌完全缺
> **每條目 9 欄**：🔍核心問題 / 📐業界標準 / 🗂資料形狀 / 📊平台現況 / 🧩全棧狀態 / 🛡️PIT洩漏防禦 / ⚡430K尺度 / 🔧漏洞 / 🏷️優先級

## 地圖組織：訊號研究生命週期 5 階段漏斗（照順序檢查）
| 階段 | 問什麼 | 分析數 |
|---|---|---|
| ① 訊號有效性初探 | 真能預測未來嗎 | 6 |
| ② 品質、動態與細節 | 撐多久?線性?挑對環境?穩定? | 5 |
| ③ 統計嚴謹度與防偽 | 運氣/過擬合/偷看未來嗎 | 8 |
| ④ 實戰寫實度 | 扣成本/滑價/容量後還賺嗎 | 3 |
| ⑤ 多因子與系統觀 | 有獨特新資訊嗎 | 6 |
> ⚠️ 階段一交叉引用註:光看 IC 不足以證明有效,須同時看分位單調(階段二)+換手率(階段四)。

## 全圖狀態速覽（28 種分析,6+5+8+3+6）
### 階段① 訊號有效性
1 單標的時序IC ✅功能/⚠️選因子未過 ｜ 2 Rolling IC ✅但grouped崩潰連帶白算 ｜ 3 Pooled/Panel時序IC ❌完全缺 ｜ 4 symbol一致性 🔌(deep tab門閂) ｜ 5 橫截面IC ✅小規模(concat爆/無split) ｜ 6 🎯事件case-control ⛓️‍💥+❌(主戰場真套件全缺)
### 階段② 品質動態
1 分位/單調性 🔌靜默空圖(schema接錯) ｜ 2 IC衰減 ⚠️極慢+連帶白算 ｜ 3 regime/grouped ⚠️P0崩潰 ｜ 4 穩定性/ICIR ✅基礎+🔌OOS ｜ 5 因子漂移 🔌/❌
### 階段③ 統計嚴謹度（最傷研究有效性）
1 IC顯著性 🔌(rolling IC當i.i.d.) ｜ 2 🚨FDR ⛓️‍💥高風險假綠(幽靈) ｜ 3 block bootstrap ❌ ｜ 4 🎯train/test主路徑 ❌ ｜ 5 walk-forward 🔌deep無purge ｜ 6 purged CPCV 🔌ML孤島 ｜ 7 極端值診斷 🔌/❌ ｜ 8 策略層過擬合DSR/PBO/MinBTL ❌
### 階段④ 實戰寫實
1 多空spread ⛓️‍💥(schema空圖+定義不一致) ｜ 2 換手/Net IC ✅Turnover但toggle幽靈/🚨Net IC公式量綱錯誤/crypto成本偏樂觀 ｜ 3 容量/Slippage 🔌(無volume)/❌
### 階段⑤ 多因子系統
1 VIF/冗餘 ✅主流程但❌無大尺度cap(430K爆) ｜ 2 正交化 🔌+誤稱(無真residual/邊際IC) ｜ 3 centrality 🔌 ｜ 4 ML/SHAP ✅獨立頁但⛓️‍💥無IC橋 ｜ 5 因子暴露 🔌+雷達誤導(P0,attribution硬填NaN) ｜ 6 多因子組合 ❌最大缺口

## 🚨 系統性發現（跨階段，最該知道）
### A. 「幽靈」開關/功能(UI 顯示有,後端沒做或忽略)— 最危險
- **FDR 多重比較**(階段③型2):UI 開關顯示防偽,後端 Stage5 從未呼叫 → 43萬特徵×0.05 ≈ **21,500 個純運氣假訊號**沒被擋。
- **feature_filter / max_features**(貫穿):前端送、後端 schema 無此欄靜默丟棄 → 你以為篩了 30,引擎跑全量 45 萬。
- **turnover.enabled**(階段④型2):toggle 不 gate,Stage5 無條件全算。
- **slippage_bps**(階段④型2):config 有但 NetICAnalyzer 沒讀。
- **calculate_factor_attribution**(階段⑤型5):函式有完整實作,runner 硬填 NaN 繞過 → 雷達顯示假歸因。
- **max_features_for_correlation=200 / ShapleyConfig**(階段⑤):死配置,執行路徑未讀。

### B. 「靜默空圖」(後端算了、前端接錯 schema → 顯示「暫無數據」)
- QuantileReturnChart + FactorEquityCurveChart(階段②④):report 巢狀 `{quantile_returns:{...}}` 但前端讀頂層 → 圖空但 summary 有值。

### C. 「名實不符 / 數字算錯」
- **正交化**叫「Neutralized IC」實為轉換 summary,**沒算真 residual/邊際 IC**(階段⑤型2)。
- **Net IC 公式量綱錯誤**:相關係數減報酬率,數學無意義(階段④型2),應依 Grinold `IC−Cost×Turnover/截面波動率`。
- **時間戳記秒被當毫秒**(階段②型3):grouped IC 的 by_year/quarter 軸錯。

### D. 「研究有效性的系統缺口」(主流程幾乎無防過擬合)
- **無 train/test 切分主路徑**(階段③型4):全 in-sample,連去極值都全樣本 fit。
- **walk-forward / purged CV 有程式碼但孤島**(階段③);**DSR / PBO / MinBTL 完全缺(repo 無實作)**,皆未接 IC 主流程。
- **rolling IC 當 i.i.d.**(階段③型1):t-test 高估顯著,須 HAC/block bootstrap。

### E. 「ML-first 平台的核心整合斷裂」
- **IC ↔ ML(XGB/LGBM/SHAP)兩套平行管線**(階段⑤型4):無「IC 倖存者→一鍵 ML 驗證」橋。
- **多因子組合 IC + 邊際 IC 缺**(階段⑤型2/6):「這因子有獨特新資訊嗎」的產品答案缺。

### F. 「主戰場半成品」(使用者最需要)
- **事件 case-control**(階段①型6):現 event 模式只是條件查詢,顯式事件清單+正反標籤+事件前窗+matching+OOS 全缺;event_timestamps API 收了但 orchestrator 寫死忽略;**事件不足時靜默 fallback 全樣本 IC(隱性風險:以為跑事件其實跑全樣本)**。

### G. 「大尺度(430K)未防護」
- Stage4 先對 430K 全欄算 rolling IC = 前置記憶體災難;Stage6 redundancy 無 candidate cap;多處 O(n²/n³) 無上限。(對應另立的 IC 優化 epic CONVERGED.md)

### H. 「cross-sectional 模式空殼」(橫切)
- 除橫截面 IC(①5)外,階段②-④多數分析(分位/decay/grouped/多空/turnover)在 cross-sectional 模式**全回空**;只 longitudinal 模式才算。使用者切橫截面會看不到這些。

## 優先級總覽（四家共識）
- **🎯 絕對優先(正確性紅線+主戰場,生死問題)**:事件 case-control 套件(①6)、train/test 切分(③4)、FDR 接線(③2)、Net IC 量綱修正(④2)、因子暴露 NaN 繞過(⑤5)。
- **🚨 P0 止血**:grouped/decay 崩潰(②3/②2)、幽靈開關群、靜默空圖、大尺度 cap(⑤1)。
- **P0 核心產品缺口(各階段 FINAL 標 P0)**:IC→ML 橋(⑤4)、多因子組合+邊際IC(⑤2/6)。
- **高**:Pooled IC(①3)、DSR/PBO/MinBTL(③8)。
- **中/低**:容量(④3)、centrality(⑤3)、進階指標。

## 誠實邊界
- 程式碼現況由能讀 repo 的 codex/cursor/Claude 查證;Gemini 貢獻量化完整性/業界標準/挑錯(讀碼欄標未驗證)。
- 未跑 live 430K run / 未驗證 WebSocket serialization / crypto 官方費率未 live 驗證(市場假設)。
- 「完整性」由四個獨立家族交叉驗證逼近,非保證 100%。

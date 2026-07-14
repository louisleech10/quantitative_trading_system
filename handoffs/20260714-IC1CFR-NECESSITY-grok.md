# 1c-FR 必要性評估 — Grok 獨立版(2026-07-14)

**task-id**: IC1CFR-NECESSITY  
**角色**: 委員(grok),唯讀(僅本檔寫入)  
**問題**: canonical 因子報酬序列(1c-FR)對本系統是否必要?何時做?  
**背景**: 1c B-strict 已完工;breakeven/profitable=fail-closed unavailable;`ls_returns` 時間錯位已實證;使用者管線=IC 粗篩→ML(監督式 GBDT)→回測;「無消費者可 parked」僅初步理解。  
**方法**: 先完整獨立論證+真實碼佐證,再讀 `handoffs/20260714-IC1CFR-NECESSITY-claude.md` 對照。

---

## A. 獨立論證(讀 Claude 前)

### A0. 物件定義(避免語意漂移)

| 物件 | 是什麼 | 本庫現況 |
|------|--------|----------|
| **gross IC** | 特徵 vs 前瞻標籤的相關 | 主篩選路徑已用;無量綱 |
| **cost_drag_return** | `(cost_bps/1e4)×turnover`(報酬空間) | 1c 已落地;per-rebalance 未年化 |
| **canonical factor-return series (1c-FR)** | 時間對齊的分位 L/S **因子組合**逐期 gross return(+對齊 turnover series) | **未建**;`NetICAnalyzer` 恒 unavailable |
| **ML 標籤** | 資產/事件前瞻報酬或 binary | `LabelGenerator`: close 前瞻,無扣成本 |
| **回測 PnL** | 部位進出後扣 commission+slippage | `vectorized_backtest` 已扣 `(c+s)×2` |

1c-FR **不是**「任意報酬序列」,而是**把因子當可交易組合**時的 gross 路徑。它回答:「做多高分位、做空低分位,這條紙上因子組合賺多少、扣成本後是否打平」。它**不**回答:「GBDT 該不該把這根 K 線標成 1」。

### A1. 真實碼證據(本輪核對)

1. **ls_returns 錯位(仍在 deep 模組)** — `momentum/Analysis/factor_return_analyzer.py:70-88`  
   high/low 分位 `reset_index(drop=True)` 後按位置相減;時間交集不等仍得有限 L-S。本輪最小 repro: 指數錯開時,對齊 mean≈-0.0033 vs 錯位 mean≈+0.004(符號/量級皆可假)。  
   輸出僅 mean/抽樣 cumprod,**無** time-indexed Series export。

2. **1c 後 net 路徑 fail-closed** — `net_ic_analyzer.py:18,78-110,183-312`  
   `batch_analyze` 忽略 `factor_returns`;`net_factor_return`/`breakeven_cost_bps`/`profitable_after_cost` 恒 `_unavailable("canonical_factor_return_series_not_built (1c-FR)")`;`evaluable_count` 恒 0。  
   `compute_net_factor_return` 保留但 deprecated,batch 不呼叫。

3. **IC 主篩不吃 net/FR** — `ic_filter_orchestrator` stage5=統計驗證,stage6=冗餘;deep 模組 `_run_factor_return`/`_run_net_ic` 在選後/旁路。`_run_net_ic` 兩參 `batch_analyze(summary, turnover_data)` 明確不傳 FR。

4. **ML 標籤無成本** — `FeatureEngineering/labels/label_generator.py:32-41`  
   `label_binary = 1 if ret>threshold`;`label_return = close[t+h]/close-1`。無 fee/slippage/turnover。  
   `xgboost_analyzer.train_model` 吃外部 `y`,無 cost 通道。

5. **成本判決已在回測** — `Strategy/vectorized_backtest.py:41-47,246-248,285-287`  
   每筆 trade:`pnl_pct_raw - (commission+slippage)*2`。這是管線上**唯一有部位語意的淨報酬判決**。

6. **前端/API 無決策消費** — `breakeven`/`profitable`/`net_factor_return` 僅 types union + NetICChart 測試/顯示形狀;無 ranking gate、無 ML feature list 過濾器讀這些鍵。`ic_reporter` 匯出 `cost_drag_return` 與(若跑)錯位的 `long_short_mean_return`。

7. **SPEC 自述** — `docs/IC1C_NETIC_SPEC.md:117`:1c-FR = series+通道+實值 conditional metrics+持有期矩陣+rank_correlation;RISK-HIT a,d。

### A2. ① 成本判決層級歸屬(業界實務)

量化多因子/系統性實務的**層級分離**(Grinold–Kahn 可實現 IR;AQR/WorldQuant 研究慣例;TCA/回測工程;AFML meta-labeling 語境):

| 層 | 問題 | 典型成本角色 | 本系統對應 |
|----|------|--------------|------------|
| **研究/IC** | 有無預測力? | Gross IC/ICIR;turnover 作**診斷/軟過濾**;cost_drag 作**相對昂貴度** | IC Gatekeeper + 1c cost_drag |
| **可實現性(implementability)** | 單因子紙上組合扣成本後是否打平? | Factor portfolio net return、breakeven bps、holding-period 掃描 | **1c-FR 域**;目前 unavailable |
| **組合構建** | 多因子軋單後淨 alpha | TC 約束、優化目標 net of cost | 未成熟/非當前主路徑 |
| **回測/實盤** | 策略帳戶賺不賺 | Commission/slippage/impact;**權威 PnL** | `vectorized_backtest` |

**判決**:  
- **「策略最終賺不賺」→ 回測層(必要且已有)**。  
- **「單因子紙上是否可實現」→ 可實現性層(1c-FR)** — 研究 nicety,非 ML/回測正確性前置。  
- **IC 粗篩** 不應把 breakeven 當硬淘汰主閘:單因子紙上淨報酬**系統性忽略跨因子對沖/軋單**,可誤殺組合層划算的高換手互補因子(與 Claude 同向)。

業界常見錯誤(本庫 1c 已拒絕):用 IC 減成本(混量綱)。1c-FR 修的是**報酬−成本**,不是恢復 net_ic 鍵。

### A3. ② ML 是否該 cost-aware → 是否逼出 1c-FR 前置?

**ML 該不該 cost-aware?**  
- **研究最佳實務傾向「部分要」**:高換手特徵若標籤為 gross,模型可偏好「紙上好、扣成本後爛」的訊號(尤其 binary 門檻=0)。  
- **但手段與 1c-FR 正交**:

| cost-aware ML 手段 | 需要什麼 | 需要 1c-FR? |
|--------------------|----------|-------------|
| 抬高 binary 門檻 `θ ≥ round-trip cost` | 每 trade 成本假設(bps) | **否** |
| Meta-label:「進場後扣成本是否賺」 | 主模型訊號 + 回測式 trade PnL | **否**(回測/事件引擎) |
| sample_weight ∝ f(turnover) | 特徵級 turnover 標量(已有 quantile_turnover) | **否** |
| 目標=預測因子組合淨報酬 | 因子 L/S 淨序列 | **是**(窄用例,非現行 GBDT) |
| 持有期/再平衡優化矩陣 | 對齊 gross return series | **是**(1c-FR 範圍,非 ML 標籤) |

現行管線:`LabelGenerator` 資產前瞻報酬 → GBDT 分類/回歸 → 策略回測扣成本。  
**ML 正確化(若做 cost-aware)的前置是「交易/事件成本語意」或「標籤門檻」,不是 canonical 因子組合序列。**

**結論**:1c-FR **不是** ML 正確化的硬前置。把兩者綁成 T1 硬依賴=**物件混淆**(factor-portfolio series ≠ supervised label)。

### A4. ③ Parked 隱憂清單(做/不做都要记账)

**若 PARK 1c-FR(建議路徑下的殘債)**:

1. **UI/schema 佔位長期 unavailable** — 使用者可能把 cost_drag 誤讀成「已扣成本可獲利」;需文案/文件釘死「不可當 profitable」。  
2. **FactorReturnAnalyzer 仍可輸出錯位 L/S** — deep 模組若開啟,`long_short_mean_return`/Sharpe 等**靜默有限假值**(比 unavailable 更危險)。Park 1c-FR **不修**此洞。  
3. **無 rank(gross IC vs net factor return)** — 無法量化「成本是否翻轉因子排名」;僅能用 gross_ic vs cost_drag **間接**看昂貴度,非同空間 rank corr。  
4. **持有期矩陣缺席** — 使用者持倉 1h–1w 不定時,無法在 IC 層做 horizon×cost 網格;只能靠多 label horizon + 回測。  
5. **factor_exposure/attribution 的 FR 矩陣品質** — `calculate_factor_attribution` 要 time-aligned columns;若上游用錯位序列→beta/歸因假。1d 若吃 FR,需同源正確性。  
6. **假消費者日後誤接** — 有人把 `long_short_mean_return` 當 breakeven 分子而未走 1c-FR 契約 → 再現混用。fail-closed 合約必須保留。  
7. **研究漏斗** — 極大因子池時,中間「可實現性」層可省回測算力;本階段數量級與痛感**未實證**,不構成現在動工理由。

**若現在強做 1c-FR 的隱憂**:

8. **單因子 net 被當淘汰閘** → 誤殺組合互補因子。  
9. **大票 RISK a,d** 排擠 1d/1f/真實端到端。  
10. **與 ML 標籤對齊假設錯誤** — 若誤把 FR series 當 GBDT y,語意全錯。

### A5. ④ 獨立裁決(讀 Claude 前草稿)

- **必要性(對現行 IC→ML→回測)**: **非阻塞必要**。權威成本判決在回測;IC 層 cost_drag 已夠粗篩診斷。  
- **必要性(對產品宣稱的 net_factor/breakeven/profitable 實值)**: **必要**,否則永遠 unavailable(正確 fail-closed)。  
- **時機**: **PARKED** 於關鍵路徑之後;不插隊 1d/1f/實測。  
- **獨立小債(建議與 1c-FR 脫鉤)**: 若 `factor_return` deep 模組維持可開 → 應 **fail-closed 或修時間對齊** 小刀,避免「錯位有限值」比 unavailable 更糟。此小刀可不是完整 1c-FR(可不做通道/breakeven/持有期矩陣)。

---

## B. 與 Claude 對照

| 點 | Claude | Grok | 關係 |
|----|--------|------|------|
| 最終賺不賺在回測 | 支持 park | 同意 | 收斂 |
| IC 已有 cost_drag | 支持 park | 同意 | 收斂 |
| 單因子 net 可能誤殺 | 支持 park | 同意並強化 | 收斂 |
| 成本/大票排擠 | 支持 park | 同意 | 收斂 |
| **T1: ML cost-aware ⇒ 1c-FR 硬依賴** | 最強不確定;列硬觸發 | **反對硬依賴**:物件不同;cost-aware ML 走標籤門檻/meta-label/回測 PnL | **分歧** |
| T2: 回測算力浪費證據 | 觸發 | 同意作弱觸發(需量化) | 收斂 |
| T3: 組合優化要序列 | 觸發 | 同意;另加 exposure/持有期/產品要 breakeven | 擴充 |
| ls_returns 首修 | 重開時首要 | 同意;並主張 **park 期間 deep FR 假值** 是獨立隱憂 | 擴充 |

對 Claude 風險自評的直接回答:**ML 層「該」部分 cost-aware 不自動把 1c-FR 變成前置**;priority **不上調**到關鍵路徑,除非產品明確要「可實現因子組合」診斷或 FR-as-target 學習。

---

## C. 最終裁決

### 必要性
- **對使用者當前管線正確性**: **非必要**(park 合理)。  
- **對 1c schema 中 net_factor/breakeven/profitable 從佔位變實值**: **必要**(否則維持 unavailable 是正確態)。  
- **對 ML 正確化**: **非前置**。

### 時機
**PARKED** — 不排入 1c 後立刻的下一刀;維持 B-strict fail-closed。優先序建議仍:1d attribution → 1f 空圖 schema → 真實端到端 →(觸發器命中時)1c-FR。

### 重開觸發器(任一即可立票;非永久否決)
1. **產品/研究決策**需要 `breakeven_cost_bps` 或 `profitable_after_cost` 實值(或持有期矩陣)作為**顯式**輸出,且接受單因子紙上語意。  
2. **下游消費**出現:factor exposure/attribution、組合優化、trend 維度要 **time-indexed** factor return series(非 mean 標量)。  
3. **可實現性排名**要進 IC 漏斗(implementable IR / gross-vs-net rank),且已設計**不得**用其硬殺互補因子的政策。  
4. **實證**回測前漏斗浪費:例如 ≥50% 進回測組合因成本全滅且可用 cost_drag+粗規則無法近似過濾(需量測,非感覺)。  
5. **禁止觸發**:「為了讓 ML cost-aware」單獨**不足** — 應另開 ML-label/meta-label 票,除非同時要 FR-as-target。

### Park 期間建議護欄(非本票實作,僅裁決附帶)
- 保留 unavailable 契約;禁 `long_short_mean_return` 回填 breakeven。  
- 文件/UI 釘:cost_drag ≠ 獲利判定。  
- Deep `factor_return` 模組:視為**未校準/可疑**直至時間對齊修復或關閉輸出有限 L/S 風險指標。

### 假設與邊界
- 假設使用者主路徑仍為單市場 crypto 研究、監督式 GBDT、向量化回測扣成本;未假設實盤組合優化器已上線。  
- 未重跑全套 pytest(論證題,非實作票);錯位 repro 為本輪最小腳本,與 SPEC FACT-RECEIPT 同構。

---

## D. 結構化收尾

```
ASSUMPTIONS_VERIFIED: FR reset_index 錯位(repro);net_ic unavailable 契約;IC 主篩不吃 FR;LabelGenerator 無成本;backtest 扣 (c+s)*2;前端無 breakeven 決策 gate
TESTS_RUN: 本機 python 最小 repro ls_returns 錯位(對齊 mean≠錯位 mean);靜態讀碼/rg(非全量 pytest)
FAILURES_SEEN: none
SCOPE_CHANGES: none(唯讀+本產出檔)
NUMERIC_OR_SCHEMA_IMPACT: none
```

RULING: PARKED—現行 IC→ML→回測非阻塞必要(成本權威在回測;ML cost-aware≠1c-FR 前置);breakeven/持有期/exposure 等實消費者或實證漏斗浪費出現再重開,期間 deep FR 錯位有限值另記隱憂。

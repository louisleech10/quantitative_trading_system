# SCOPE 提案 — Antigravity

以下是針對泛用型因子/訊號研究平台定義的「IC-Analysis 分析類型全覆蓋地圖」範疇與結構提案。此階段僅敲定大綱與 Schema，確保不遺漏業界標準，並降低非量化使用者的認知門檻。

---

## 1. 地圖的組織方式 (Organization)

對於非量化背景的使用者，按「統計學名詞」或「資料形狀」分類會難以理解。建議按**「訊號研究的生命週期 (Research Pipeline)」與「漸進式提問」**來分群排序：

1. **第一階段：訊號有效性初探 (Basic Efficacy)** —— *這個特徵/事件真的能預測未來嗎？*
2. **第二階段：品質、動態與細節 (Quality & Dynamics)** —— *預測力能持續多久？是線性的嗎？有沒有挑對環境？*
3. **第三階段：統計嚴謹度與防偽 (Rigor & Anti-Overfitting)** —— *這該不會是運氣好（過擬合）或偷看未來（洩漏）吧？*
4. **第四階段：實戰寫實度 (Trading Realism)** —— *如果真的拿去交易，扣掉手續費還賺錢嗎？*
5. **第五階段：多因子與系統觀 (Multi-Factor & ML)** —— *跟現有其他特徵比，它有提供獨特的新資訊嗎？*

---

## 2. 每條目的內容 Schema (Entry Schema)

為確保兼具「教學性」與「工程實作指導」，地圖中的每一個分析類型，都將包含以下結構化欄位：

*   **🔍 回答的核心問題 (Core Question)**：一句白話文（例：「這訊號是今天有效，還是每天都有效？」）。
*   **📐 業界標準做法 (Industry Standard)**：Quant 領域的標準定義（例如 Rank IC, Pearson IC 的選擇標準）。
*   **🗂 資料形狀與前處理 (Data Shape & Input)**：需要 Panel data, Pooled data 還是 Event list + 標籤？
*   **⚡ 海量尺度工程對策 (Scale @ 430K×20K)**：在單標的極大、跨標的極廣的情況下，如何算得快又不 OOM（如：向量化、分塊計算、避免跨標的 groupby 爆炸）。
*   **🛡️ PIT 與洩漏防禦 (Anti-Leakage)**：該分析最容易踩到的未來函數地雷是什麼。
*   **📊 平台現況對應與診斷 (Current Status)**：對應到平台哪個模組？實作做對了嗎？
*   **🏷️ 狀態標籤 (Status Tag)**：標示 🎯 主戰場必做 / ⚠️ 現有但壞掉 / ❌ 完全缺。

---

## 3. 分析類型清單與全景展開 (Analysis Types Scope)

這是一個泛用型平台**必須**涵蓋的類型清單，已補齊使用者不知道但必須有的拼圖，並標註狀態：

### 階段一：訊號有效性初探 (Basic Efficacy)
*   **橫截面 IC (Cross-Sectional IC)** ❌：*「在同一時間點，這個訊號能區分多檔標的中的贏家和輸家嗎？」*（普適性平台必備，多標的比較）
*   **池化/面板時序 IC (Pooled/Panel Time-Series IC)** ❌：*「綜合所有時間與所有標的，這個訊號的總體預測力如何？」*（目前平台缺乏的普適性模式）
*   **🎯 事件/病例對照研究 (Event/Case-Control Analysis)** 🎯：*「在自訂的特定正向事件發生前，是否存在共通的特徵先兆？」*（**主戰場！** 需顯式事件清單、正反標籤、事件前窗提取，目前僅有條件查詢的半成品）

### 階段二：品質、動態與細節 (Quality & Dynamics)
*   **分位數與單調性分析 (Quantile / Monotonicity)** ⚠️/❌：*「特徵值極端大時，報酬也極端大嗎？還是中間值反而最好？」*（檢查非線性關係，目前 grouped 功能會崩潰）
*   **IC 衰減與半衰期 (IC Decay / Half-life)** ⚠️：*「訊號發生後，預測力能撐幾個 bar 才會消失？」*（目前 decay 計算會崩潰）
*   **分組/狀態條件 IC (Regime / Condition-Dependent IC)** ⚠️/❌：*「這個訊號是否只在大多頭，或是高波動時才有效？」*
*   **穩定性與一致性 (Stability / Consistency)** ❌：*「IC 是靠某幾天極端行情拉高的，還是每天穩定輸出？（Win Rate, IC IR）」*

### 階段三：統計嚴謹度與防偽 (Rigor & Anti-Overfitting)
*   **顯著性與多重比較調整 (Significance & FDR / Multiple Testing)** ❌：*「我們測了 43 萬個特徵，這個高 IC 該不會只是運氣好？」*（非量化者常忽略的 P-value 陷阱）
*   **淨化與前向交叉驗證 (Purged / Walk-Forward CV)** ❌：*「嚴格不偷看未來、切分 Train/Test 的情況下，訊號還有效嗎？」*（避免洩漏風險，特別是 ML 場景）
*   **特徵極端值診斷 (Outlier / Extreme Value Impact)** ❌：*「把特徵最極端的 1% 拿掉，IC 是不是就歸零了？」*（防範髒資料）

### 階段四：實戰寫實度 (Trading Realism)
*   **多空組合報酬與價差 (Long/Short Return Spread)** ❌：*「買入訊號前 10%、放空後 10%，理論報酬曲線長怎樣？」*
*   **換手率與成本侵蝕 (Turnover & Transaction Costs)** ❌：*「訊號變動太快，會不會賺的錢都不夠付手續費？」*
*   **流動性與容量限制 (Liquidity & Capacity)** ❌：*「這個訊號只能買幾千塊，還是能容納幾百萬資金不會滑價？」*

### 階段五：多因子與系統觀 (Multi-Factor & ML)
*   **共線性與正交化 (Collinearity & Orthogonalization)** ❌：*「這個新特徵，是不是跟我們已經有的特徵高度重複？」*
*   **非線性特徵重要性 (Non-linear ML Feature Importance)** ❌：*「在 XGBoost 裡，這個特徵的 SHAP value / 貢獻度有多大？」*
*   **因子暴露度 (Factor Exposure / Attribution)** ❌：*「這訊號賺錢，是因為它只是單純在賭大盤漲（Beta），還是真的有 Alpha？」*

---

## 4. 關鍵結論與優先級標示

為了確保開發聚焦，地圖將明確界定以下優先級：

1.  **🎯 絕對優先 (使用者主戰場)**：**事件/病例對照研究 (Case-Control Event Study)**。必須定義一套支援「顯式事件清單 (List of [Timestamp, Symbol, Label])」+「事件前窗 (Lookback Window)」+「Train/Test 切分」的流程。
2.  **⚠️ 緊急修復 (現有但壞掉)**：**IC 衰減 (Decay)** 與 **分組分位數 (Grouped/Quantile)**。這些是理解訊號動態的基礎，目前會 Crash，需修補其在大尺度下的記憶體與邏輯問題。
3.  **🛡️ 基礎建設補漏 (完全缺)**：**池化時序 IC (Pooled Time-Series IC)** 與 **淨化交叉驗證 (Purged CV/Train-Test Split)**。這是泛用型平台防止假陽性與過擬合的核心護城河。

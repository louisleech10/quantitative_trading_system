**VERDICT: CHANGES**

這份綜合草案在「防禦未來函數（Look-ahead Bias）」的敏銳度上非常出色（精準抓出了 `全樣本 qcut` 與 `事前看全段決定 regime` 兩大經典洩漏死穴）。但在量化金融的業界標準完整度與實務極端情況處理上，還有一些缺失需要補強。

以下是針對你的四個問題的逐條審查與修改建議：

### 1. 各型業界標準、洩漏防禦與資料形狀審查
整體防禦邏輯（如型1的 qcut 洩漏、型3的 regime 洩漏）**完全正確且致命**，必須保留。
但有幾個量化細節與資料形狀需要修正或補充：
*   **型1（分位/單調性）**：
    *   **缺少檢定調整**：金融時間序列具有高度自相關性，Spread t-test 必須指明使用 **Newey-West 調整後的 t-stat**，否則極易高估顯著性（Type I Error）。
    *   **形狀補充**：除了 Long-short spread，實務上一定要看 `Top Quantile vs Benchmark` 與 `Bottom Quantile vs Benchmark`，因為很多因子是「單邊有效」（例如做空極度有效，但做多沒用），只看 Spread 容易被誤導。
*   **型2（IC衰減）**：
    *   **量化錯誤/陷阱**：強行對多 horizon IC 做指數衰減（Exponential Decay）擬合在實務上是災難，因為低 R² 或 IC 翻負時擬合會直接崩潰。這印證了你文檔中提到的「43萬R2≈0多雜訊診斷」。
    *   **修正**：必須加入 **「非參數降半檢查（Non-parametric Halving）」** 作為 fallback。不依賴曲線擬合，直接計算「移動平均 IC 跌破峰值一半所需的 bar 數」。
*   **型3（Regime）**：
    *   **量化陷阱**：使用 KMeans/HMM 做 rolling 劃分時，存在致命的 **Label Switching（標籤跳換）** 問題（今天的 Cluster 0 在明天變成了 Cluster 1）。這會導致 cross-sectional 或時序分析完全錯亂。
    *   **防禦**：必須強制要求非監督式 Regime 輸出時，以某種基準（如波動率高低或均線斜率）對標籤進行重新排序（Align labels）。
*   **型4（穩定性）**：
    *   **遺漏**：ICIR 只是均值/標準差，缺乏對「尾部風險」的描述。必須加入 **Factor Drawdown（因子最大回撤）** 的評估。

### 2. 階段二（品質動態）4 型有無該有卻漏？
目前這 4 型涵蓋了橫截面（型1）、時間序列特徵（型2）、市場環境（型3）與總體統計（型4）。**在「純預測力」的角度是完整的，但漏掉了「可交易性（Tradability）」的審查。**
*   **漏掉的維度：Turnover（換手率）與 Capacity（容量）**。
*   一個 IC 極高、單調性完美的因子，如果每次換倉要求 100% 的換手率（如很多高頻反轉因子），扣掉手續費/滑價後就是負報酬。
*   **建議**：將「Turnover Penalty / Autocorrelation of Factor values（因子自相關性）」納入型1或型4中，作為過濾因子的重要 Gate。

### 3. 業界標準完整度補充（待補入文檔）
請在文檔的各型描述中，補充以下業界標準關鍵字，以防後續 Agent 實作時採取過於天真的算法：
*   **型1**：加入 `Newey-West t-statistic`，`Rank IC (Spearman)` 作為單調性輔助。
*   **型2**：加入 `Non-parametric half-life fallback`，以防止 Scipy curve_fit 崩潰。
*   **型3**：明確標示 `Label Alignment mechanism required for KMeans/HMM`。
*   **型4**：加入 `Factor Max Drawdown (MDD)` 與 `Newey-West adjusted ICIR significance`。

### 4. 該不該加第 5 型「因子有效性漂移 (Factor Drift)」？
**結論：應該獨立為第 5 型（Type 5: Structural Break & Factor Drift）。**

*   **理由**：
    *   型 2 的「衰減（Decay）」指的是**微觀層面**（Signal holding period），例如這根 K 線的信號到 5 根 K 線後就沒效了。
    *   「因子漂移（Drift）」指的是**宏觀層面**（Macro-cycle decay），例如 2018 年超有效的因子，到了 2023 年因為市場微結構改變而永久失效。
    *   型 4 的「穩定性」通常看的是全段時間的平均表現（Rolling mean/std）。
*   **第 5 型應涵蓋的內容**：
    *   **檢定法**：Chow Test（結構性斷裂檢定）或 CUSUM（累積和檢定）。
    *   **目標**：偵測因子的累積報酬曲線是否出現斜率的永久性下折（Permanent degradation）。

---

### 最終修改建議（給委員/Agent 的 Action Item）
請在原文檔做以下調整後即可 APPROVE：
1.  **新增 Type 5 因子漂移分析**，將「有效性隨年份遞減 / 結構性斷裂 (Chow/CUSUM)」獨立出來。
2.  在 **型1** 加上 `Newey-West 調整` 與 `Top/Bottom vs Benchmark 分開看`。
3.  在 **型2** 崩潰問題的解決方案中，寫入 `要求非參數半衰期 fallback`。
4.  在 **型3** 中警告 KMeans/HMM 的 `Label switching` 陷阱。
5.  在 **型4** 中補上 `Factor Drawdown` 作為穩健性的主 gate 之一。

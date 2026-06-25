使用者可稽核：cat .claude/gate/audit.log
**VERDICT: CHANGES** (整體邏輯精準且切中要害，但針對「43萬特徵盲撈」的極端情境，必須補上策略級別的過擬合機率診斷工具，否則防護網仍有漏洞。)

以下針對您的三個問題與委員檢查清單提供詳細的量化審查回覆：

### 1. 各型業界標準 / 洩漏防禦有無量化錯誤？
**現有診斷完全正確，沒有量化錯誤。Claude 精準抓出了多個在量化實務上會導致災難性虧損的致命傷：**

*   **型 1 (Rolling IC 視為 i.i.d.)**：這是極度經典的錯誤。Rolling 運算（尤其是帶有重疊時間視窗的 return）天生具有高度的序列自相關（Autocorrelation）。如果用標準的 t-test 算 p-value，會嚴重低估標準誤（Standard Error），導致 t-stat 膨脹、p-value 虛假地極小。**必須依賴 HAC（如 Newey-West）或 Block Bootstrap，您的診斷完全正確。**
*   **型 4 (全樣本 Winsorize)**：這是一個極度危險的 **Look-ahead Bias（前視偏差）**。如果用全樣本去算分位數並進行去極值，等於「未來的極端大跌/大漲」會影響「過去的特徵分佈」。嚴格的 OOS 必須只用 Train set 的統計量（如 rolling median/MAD）來套用到 Test set。診斷列為最高優先極度精準。
*   **型 2 (FDR 幽靈)**：在 43 萬個特徵的基數下，如果只用 $\alpha = 0.05$ 去篩選，期望上會產生 $430,000 \times 0.05 = 21,500$ 個純粹靠運氣的「假訊號」。如果 FDR toggle 是幽靈（UI 顯示開啟但後端是 raw p），這是最可怕的「高風險假綠」。

### 2. 階段三有無該加？(DSR, PBO, MinBTL 等)
**必須加入！強烈建議新增「型 8：多重測試懲罰與過擬合機率 (Strategy-Level Overfitting)」。**
目前的型 1~7 多集中在「特徵層級 (Feature-level)」的防偽。但當系統進行高達 43 萬次的特徵盲撈時，你面臨的是 **Selection Bias under Multiple Testing**，必須引入 Marcos López de Prado 等人提出的「策略層級」防偽指標：

*   **Deflated Sharpe Ratio (DSR)**：當你測試了 43 萬個特徵，最高 IC 或最高 Sharpe Ratio 的那個特徵，其期望值已經被極大化（Selection Bias）。DSR 會將「測試次數 (Number of Trials)」、「特徵間的相關性」以及「報酬的偏度/峰度」納入考量，向下修正（Deflate）最終的 Sharpe/IC。這是在海量盲撈中證明訊號有效的唯一數學標準。
*   **Probability of Backtest Overfitting (PBO)**：透過 CSCV（Combinatorial Symmetric Cross-Validation），計算「在 In-sample 表現最佳的特徵/策略，在 Out-of-sample 表現低於中位數的機率」。這能給使用者一個直觀的警告：「這個看起來完美的特徵，有 60% 的機率是過擬合」。
*   **Minimum Backtest Length (MinBTL)**：給定 43 萬次的嘗試，你需要多長的歷史觀測點（獨立樣本數），才能讓 DSR 達到顯著？這能防止用短短兩年的資料去暴力窮舉 43 萬個特徵。

### 3. 顯著性 / FDR / Bootstrap / CV 業界標準是否完整？(需 CHANGES 的細節)
目前的框架已經很強大，但在接回主流程時，業界標準會要求以下細節的補強：

*   **FDR 與特徵共線性 (Effective Number of Tests)**：
    *   **缺陷**：43 萬個特徵絕對不可能是獨立的（必然存在大量高度相關的衍生特徵）。如果直接套用 Bonferroni，因為過度嚴苛，所有特徵都會被殺死（Type II Error 失控）；如果套用 BH FDR，它假設特徵間是正相關或獨立（PRDS）。
    *   **修正建議**：在做 FDR 之前，必須先做**特徵降維或群聚 (Clustering/Orthogonalization)**。先算出「有效獨立特徵數 (Effective Number of Tests)」，再依據這個數字去調整 p-value，否則 FDR 的結果會過於悲觀或不準確。
*   **Purged CV 必須強制包含 Embargo (型 6)**：
    *   **缺陷**：文檔提到 Purged，但要確保實作有 **Embargo**。Purge 只是刪除 Train set 中與 Test set 時間重疊的樣本；但在金融市場，Test set 發生的事件會有「延遲消化的資訊外溢」。
    *   **修正建議**：必須在 Test set 結束後，強制加上一段空白的 Embargo period 不納入 Train set，確保未來的波動率或市場結構變化不會反向污染訓練集。

---

### 📝 回應「待委員檢查」清單

1.  **FDR幽靈(型2)判⛓️💥+高風險假綠，準確？**
    *   **極度準確。** 前端有按鈕但沒有把參數送到後端（或後端沒有對應 schema），導致使用者產生「已經被 FDR 保護」的虛假安全感。在 43 萬次嘗試下，Raw p-value 的「綠燈」毫無統計意義，這絕對是 P0 級別的架構斷層。
2.  **型1 global summary無t_stat、CI不進report——屬實？**
    *   **邏輯上屬實且常見。** 很多系統只輸出 p-value，但 p-value 不提供效應大小 (Effect Size)。沒有 CI (Confidence Interval)，你就不知道這個 IC 是 `0.02 ± 0.001` (極度穩定) 還是 `0.02 ± 0.04` (雜訊極大)。報告中只留 p 卻不留 CI/t-stat 是不合格的。
3.  **階段三是否該加Deflated Sharpe/PBO？還是歸FDR/顯著性？**
    *   **應該新增為一個獨立型態（建議為 型 8）。** FDR 是「特徵層級 (Feature-level)」過濾，而 DSR/PBO 是「策略選取層級 (Strategy-level)」的懲罰。因為這 43 萬個特徵最終可能會合成一個模型，你必須知道整體 Pipeline 導致過擬合的機率。強烈建議將 DSR/PBO 獨立。
4.  **任何狀態與真實碼不符：**
    *   *(因受限於 READ-ONLY 且無程式碼權限，此點依據您提供的 Claude 綜合審查文本判定邏輯完全合理。)*

使用者可稽核：cat .claude/gate/audit.log
**VERDICT: APPROVE**

這份「階段四」草案對實戰寫實度與量化細節的抓漏非常精準，特別是抓出了「Net IC 量綱錯置」、「Crypto 成本過於樂觀」以及「幽靈開關」等致命問題。由於無法讀取 repo，現有程式碼狀態（如 `:1175 幽靈開關`）標記為「未驗證 (Unverified)」。

以下針對您的四個量化審查問題提供詳細的業界標準與解答：

### 1. 各型業界標準有無量化錯誤？
你在審查中抓出的問題非常精準，程式碼現有的實作確實存在嚴重量化邏輯錯誤（這也是草案有抓到的）：
*   **型 1 (Long-Short Spread)**：
    *   **定義不一致**：主流程比較頭尾十分位（Top vs Bottom Decile）與 Deep 分析比較前/後 20%（Q4+5 vs Q1+2）的定義不一致會導致報表互相矛盾，必須統一或明確標示。
    *   **累積報酬不扣成本（Cumsum Proxy）**：這是非常危險的初學者陷阱。用累加訊號當作淨值曲線，忽略了複利效應與交易摩擦，會讓許多均值回歸的高頻垃圾因子看起來像聖杯。
*   **型 2 (Turnover)**：
    *   **定義非標準**：程式將換手率定義為「頂分位 membership diff.abs.mean」（單純算名單洗牌率），這只是個粗糙的 Proxy。業界標準換手率是**投資組合權重變化的絕對值總和**：$\sum |w_{i,t} - w_{i,t-1}| / 2$。

### 2. 階段四 (實戰寫實) 有無該加的項目？
為了達到「實戰寫實」，建議階段四加入以下三項關鍵維度（Crypto 尤其需要）：
*   **Funding Rate / Borrow Cost (資金費率 / 借幣成本)**：在 Crypto 市場做空（或做多永續合約）需要支付/收取資金費率。許多假 Alpha 是透過做空那些長期跌但資金費率極高的垃圾幣（如 Meme 幣）賺來的，扣掉 Funding Fee 後其實是虧損的。
*   **Signal Decay Profile (信號衰減曲線)**：只看單期的 IC 不夠，必須畫出 IC 在未來 1, 2, 5, 10 期的衰減圖。這能直接決定策略的執行頻率與延遲容忍度（如果 IC 在 2 根 K 線內衰減完，那就完全沒有實盤價值）。
*   **Market Impact Model (市場衝擊模型)**：目前的 slippage 是常數（scalar），這在真實世界不成立。應加入基於交易量的衝擊模型，例如最基本的平方根法則（Square Root Law）：$Impact \propto \sigma \sqrt{TradeSize / ADV}$。

### 3. Crypto 交易成本 5bps 偏樂觀嗎？
**極度樂觀，實盤中這是不切實際的假設。**
*   **手續費 (Fees)**：以 Binance 為例，普通帳戶 Spot / USD-M Futures 的 Taker 費率為 4~10 bps。若策略依賴訊號，通常必須以 Taker 吃單。
*   **滑價 (Slippage)**：即便是 BTC/ETH，市價單吃單也會產生 1~2 bps 滑價；若是 Altcoins，滑價通常在 5~15 bps 甚至更高。
*   **業界真實抓法**：單邊 (Leg) 至少抓 **10~15 bps**，一買一賣的 Round-Trip 總成本應設置在 **20~30 bps**。只有達到 VIP 高階等級且策略部分採用 Maker 邏輯時，才可能把 Round-Trip 壓到 5~10 bps。預設 5bps 會放行大量「高換手、低單次預期報酬」的假因子。

### 4. Net IC 公式 `gross_ic - cost * turnover * 2` 嚴謹嗎？
**完全不嚴謹，存在嚴重的「量綱錯置 (Dimensionality Error)」。**
這是一個把「蘋果」減去「橘子」的數學錯誤，草案標記為 `heuristic` 算是客氣的說法。
*   **錯誤原因**：`gross_ic` 是相關係數 (Correlation)，是一個無因次 (Dimensionless) 的數值，範圍在 $[-1, 1]$ 之間（通常因子 IC 約在 0.02 ~ 0.08）。而 `cost * turnover * 2` 計算出來的是**報酬率 (Return)**（單位是 bps 或 %）。把一個「相關係數」減去「報酬率」，在數學與金融邏輯上都是無效的。
*   **標準做法 (Standard Practice)**：
    1.  **算 Net Return**：計算分位組合的真實多空報酬，並減去交易成本。$NetReturn_t = GrossReturn_t - (Turnover_t \times Cost)$，然後用 Net Return 去算 Sharpe Ratio 或 Information Ratio。
    2.  **轉換為 IC 的懲罰 (若硬要算 Net IC)**：根據 Grinold 基礎法則，若要把成本轉換為 IC 的耗損，必須除以標的的「截面波動率 (Cross-sectional Volatility)」。
        公式約略為：$Net\_IC \approx Gross\_IC - \frac{Cost \times Turnover}{Cross\_Sectional\_Volatility}$。
        *舉例：如果成本是 10 bps，而這群標的的截面波動率是 200 bps (2%)，那麼成本對 IC 的懲罰約為 $10/200 = 0.05$。*

### 委員檢查後續動作建議：
草案抓出的問題非常精準且致命。請依照以下優先級要求修復：
1.  **停用或重構 Net IC 公式**，改用 Net Return 或 Net Sharpe 來呈現扣費後的真實績效。
2.  **將預設交易成本上調至 `15 bps` (單邊) 或 `30 bps` (Round-trip)**，以篩掉假 Alpha。
3.  確認程式碼 `:1175` 的 `turnover.enabled` 幽靈開關並修復前端的「空圖/圖表孤島」問題。

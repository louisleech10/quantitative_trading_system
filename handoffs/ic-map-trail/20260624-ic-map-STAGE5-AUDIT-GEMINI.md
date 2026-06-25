使用者可稽核：cat .claude/gate/audit.log
**VERDICT: CHANGES**

Claude 在階段五的綜合審查極度敏銳，精準抓出了量化實務中最致命的紅線（如：全期 PCA 導致前視偏誤、拿未來 Label 當 market_proxy、用等權重假裝投組歸因、430K 欄位直接算 Rolling IC 導致記憶體與算力爆炸）。

但在對齊「業界頂級量化標準」時，這份草案在**理論完整性**上仍有缺漏，需作以下補充與修正：

### 1. 業界標準有無量化錯誤或概念混淆？
整體無嚴重錯誤，但在實務定義上有需要精確化的盲點：
*   **型 1 (相關/冗餘)**：Claude 未明確區分**「因子值相關性 (Factor Value Correlation, 橫截面)」**與**「因子報酬相關性 (Factor Return Correlation, 時間序列)」**。去重特徵時看前者，但衡量投組多樣性與風險時看後者。
*   **型 2 (正交化)**：Claude 提到 Gram-Schmidt (QR)。但在量化實務中，Gram-Schmidt **高度依賴正交化順序 (Path-dependent)**，誰排第一個誰就不變，排後面的面目全非。業界在處理多因子正交時，更常使用**對稱正交化 (Symmetric / Löwdin Orthogonalization)**，它能在「改變原始因子最小」的數學保證下，產生一組互相正交的新因子。
*   **型 5 (歸因)**：Claude 批評得很好，但業界標準的 Factor Exposure 歸因分為 Returns-based (用收益率序列回歸) 與 Holdings-based (用實際持倉權重 × 因子暴露)。系統應明確支援 Holdings-based 才算及格的量化歸因。

### 2. 階段五 (系統觀) 有無該加的型或指標？
這份清單遺漏了量化研究中最重要的「邊際貢獻」概念與進階組合法，建議補充：
*   **新增：Incremental IC / Marginal IC (邊際 IC)**
    *   **定義**：這是一個新因子「是否有資格」進入現有因子庫的黃金標準。
    *   **作法**：將新因子對現有因子庫做橫截面回歸（Cross-sectional Regression），取殘差後再算對未來收益的 IC。如果 Residual IC 顯著為正，才代表它帶來了**正交的新資訊**（Alpha 增量）。目前型 2 只提到了中性化，但沒有強調與「現有組合」的邊際關係。
*   **補充入型 1：Condition Number (矩陣條件數)**
    *   在處理多重共線性時，VIF 通常只看單一變數，而矩陣的條件數（最大特異值 / 最小特異值）是衡量整體特徵矩陣穩定性（是否會導致回歸權重失真/翻轉）的標準。
*   **補充入型 6：Hierarchical Risk Parity (HRP) 與協方差懲罰**
    *   多因子合成不僅僅是 IC 加權，當因子間存在複雜相關結構時，基於樹狀分層的 HRP 是目前 ML 驅動量化系統的主流標準之一，比傳統 Risk Parity 更穩健。

### 3. 正交化、Grinold 組合、Walk-forward 標準是否完整？
*   **Neutralized IC 標準不完整**：
    業界標準的 Neutralized IC 必須強調**「橫截面 (Cross-sectional) 逐期中性化」**。必須在每一期 $t$，將因子暴露對風險因子（如：Barra 風險因子、行業、市值 Sector/Size）做橫截面回歸去殘差。Claude 提到了全樣本 PCA 的前視偏誤，應進一步寫明必須採用 PIT (Point-in-Time) 的 Cross-sectional 處理。
*   **缺漏 Grinold & Kahn 組合基礎**：
    型 6 雖然提到了 IC weighted，但遺漏了量化主動管理的基石框架：$Alpha = IC \times Volatility \times Z$-score。最優的因子組合權重（最大化 Information Ratio）在理論上正比於 $\Sigma^{-1} \cdot IC$（其中 $\Sigma$ 是因子報酬協方差矩陣）。未納入協方差逆矩陣的合成只是粗糙的過渡方案。
*   **Walk-forward 權重標準缺乏「換手率/成本約束」**：
    純看 Test IC 來決定 Walk-forward 權重，在實務上常會選出高頻翻轉的因子組合。業界標準在學習組合權重時，其 Target Function 必須包含 **Net IC (扣除交易成本的 IC)** 或加上**換手率懲罰項 (Turnover Penalty)**，否則合成出來的 Combined Signal 在 Stage 7 回測時一定會因為摩擦成本而崩潰。

### 總結行動建議
請在 Claude 的報告中補充：
1.  將 **Incremental IC (邊際 IC)** 列入型 2 或獨立為型 7，作為評價新因子獨特價值的核心指標。
2.  在型 2 (正交化) 明確補上 **Symmetric Orthogonalization (對稱正交化)**。
3.  在型 6 (多因子組合) 補上 **Grinold 最優配置矩陣 ($\Sigma^{-1} \cdot IC$)**、**HRP 配置**，並強調 Walk-forward 學習必須加入**換手率/摩擦成本懲罰項**。

# Optuna 雙密度優化公式與統計架構規範 (v2.0)

本文件定義了量化系統在「雙密度模式」下的核心優化邏輯變更。此規範旨在解決原 Ratio 算法中的數值爆炸與稀疏數據誤導問題，並建立更穩健的統計評估標準。

**適用對象**：AI Coding Agent、系統架構師
**目標**：指導 `momentum/` 與 `api/` 模組的代碼重構。

---

## 一、 核心數學定義 (The Golden Formula)

我們不再使用 `Near / Far` 的比率 (Ratio)，而是改用 **歸一化指標 (Normalized Metric, $M$)** 配合 **強度加權 (Intensity-Weighted)** 統計。

### 1. 單一案例指標 ($M_i$)
衡量單個案例的信號聚集傾向。

$$ M_i = \frac{\text{Near}_i - \text{Far}_i}{\text{Near}_i + \text{Far}_i + \epsilon} $$

*   **範圍**：$[-1, 1]$
    *   $+1.0$：完美聚集 (只在 Near 出現)。
    *   $0.0$：隨機分佈 (Near 與 Far 密度相同)。
    *   $-1.0$：反向聚集 (只在 Far 出現)。
*   **參數**：$\epsilon = 1e-5$ (防止分母為零)。此處Near和Far為密度
*   **特殊處理**：**不再剔除** `Far=0` 的案例。若 `Far=0, Near>0`，則 $M=1.0$ (視為完美案例)。
    *   **重要澄清**：$M=1.0$ 只代表「方向偏向 Near」。該案例對群體統計與最終分數的影響仍由 $w_i$ 決定；當 Near 很小時，$w_i$ 也很小，不會出現 Ratio 時代的數值爆炸與單一案例綁架均值/方差問題。

### 2. 案例權重 ($w_i$)
衡量該案例的信號強度，解決「稀疏數據卻拿滿分」的問題。

$$ w_i = \text{Near}_i + \text{Far}_i $$

*   **邏輯**：信號觸發次數越多的案例，對整體評分的貢獻度越大。此處Near和Far為信號數

### 3. 群體加權統計
對正例群體 (Pos) 與反例群體 (Neg) 分別計算加權平均 ($\mu$) 與加權標準差 ($\sigma$)。

*   **加權平均 ($\mu$)**：
    $$ \mu = \frac{\sum (w_i \cdot M_i)}{\sum w_i} $$
    *(注意：分母是權重總和，不是案例數 N)*

*   **加權標準差 ($\sigma$)**：
    $$ \sigma = \sqrt{\frac{\sum w_i (M_i - \mu)^2}{\sum w_i}} $$
    *(注意：此處採用 population 形式，分母為權重總和 $\sum w_i$，避免權重情境下的自由度歧義)*

### 4. Optuna 優化目標 (Objective Score)
這是 Optuna 試圖**最大化**的最終分數。

$$ \text{Score} = \underbrace{(\mu_{pos} - \mu_{neg})}_{\text{區分度 (Separation)}} - \underbrace{\lambda \times (\sigma_{pos} + 0.5 \times \sigma_{neg})}_{\text{穩定性懲罰 (Penalty)}} $$

*   **$\lambda$ (Lambda)**：設為 `1.0`。
*   **設計意圖**：最大化正反例的中心距離，同時懲罰分佈的離散度 (尤其是正例的不穩定性)。

---

## 二、 實作修改指南 (Implementation Guide)

請依照以下模組進行修改：

### 0. API 相容性與棄用策略 (Backward Compatibility)

本次改動以「新增欄位、不移除舊欄位」為原則，確保前端與既有使用者不會因 response schema 變動而中斷。

*   **既有 near/far ratio 相關欄位**：可繼續回傳並維持計算（用於歷史對照與診斷），但 **不得再作為 Optuna objective 的核心依據**。
*   **棄用策略**：若未來要移除 ratio 欄位，需先標記 deprecated 並維持至少一個版本週期的共存期，再於 API 規格中公告移除時間點與替代欄位（本規格新增的 $M$ 指標群）。

### 1. 數據模型層 (`api/models/training_window_config.py`)
在 `SignalDensityResponse` 模型中新增以下欄位，用於存儲 $M$ 相關統計：

*   `positive_weighted_mean_m` (float)
*   `negative_weighted_mean_m` (float)
*   `positive_m_std` (float)
*   `negative_m_std` (float)
*   `m_separation` (float): $\mu_{pos} - \mu_{neg}$
*   `positive_m_cv` (float): 正例 $M$ 的月度穩定性 CV (用於後處理篩選)

### 2. 分析引擎層 (`momentum/Analysis/signal_density_analyzer.py`)
*   **移除邏輯**：刪除 `FAR_ZERO_THRESHOLD` 相關的剔除邏輯。所有案例只要有數據都應參與計算。
*   **新增方法**：
    *   `calculate_normalized_metric(near, far)`: 返回 $(M, w)$。
    *   `calculate_weighted_stats(values, weights)`: 返回 `{"mean": ..., "std": ...}`。
*   **修改流程**：
    *   在遍歷案例時，同步計算每個案例的 $M$ 和 $w$。
    *   使用加權公式計算群體統計值。
    *   **統計檢驗對齊**：P-value (T-test) 和 Cohen's d 的輸入數據，應從原本的 `Near Density` 改為 **案例的 $M$ 值**。

### 3. 優化引擎層 (`momentum/Optimization/optuna_optimizer.py`)
*   **目標函數更新**：
    *   讀取 `SignalDensityResponse` 中的 $M$ 統計欄位。
    *   實作上述的 **黃金公式 (Score)**。
    *   處理 `None` 值異常情況 (Pruning)。

---

## 三、 邊界條件與有效性規則 (Edge Cases & Validity Rules)

本節規範所有容易產生 0/0 或「退化解」的情境，避免實作時出現不可比較的分數或被稀疏案例誤導。

### 1. 群體聚合的基本符號

對任一群體 $G\in\{pos, neg\}$ 定義：

*   權重總和：$S_G = \sum_{i\in G} w_i$
*   有效案例數：$N_G^{active} = \#\{i\in G : w_i > 0\}$

### 2. Trial 有效性決策（必須遵守）

**Case A：$S_{pos}=0$（正例無訊號）**

*   解讀：正例完全無觸發，無法支持「起漲前聚集」假說。
*   處理：此 trial 視為不可評分（invalid），應直接 Prune。

**Case B：$S_{pos}>0$ 且 $S_{neg}=0$（可能是好參數）**

*   解讀：反例無觸發（低假陽性），正例仍有觸發（可辨識）。
*   計分約定（必須固定）：
    *   設定 $\mu_{neg}=0$、$\sigma_{neg}=0$（反例視為中性、無資訊但不扣分）。
    *   因此 $m\_separation = \mu_{pos}$，Penalty 僅由 $\sigma_{pos}$ 形成。
*   防止退化解（必須加 Gate）：若正例覆蓋不足，仍需 Prune。
    *   覆蓋標準建議採擇一（以便工程落地）：
        1.  $N_{pos}^{active}$ 達到最小門檻（避免只靠極少案例拿高分）。
        2.  $S_{pos}$ 達到最小門檻（避免正例總訊號強度過低）。

**Case C：$S_{pos}=0$ 且 $S_{neg}=0$（正反都無訊號）**

*   解讀：整體無訊號，屬於完全退化解。
*   處理：必須 Prune（不可回傳 0 當中性）。

**Case D：$S_{pos}>0$ 且 $S_{neg}>0$（正常情況）**

*   正常使用黃金公式計分。

### 3. 0/0 與 None 的回傳規則

*   若某群體 $S_G=0$ 且該 trial 需要其統計值（例如 Case A 或 Case C），則 $\mu_G$ 與 $\sigma_G$ 應視為不可用（語意上為 None），並觸發 Prune。
*   僅在 Case B（$S_{neg}=0$ 但 $S_{pos}>0$）時允許以 $\mu_{neg}=0,\sigma_{neg}=0$ 進行計分。

---

## 四、 穩定性驗證與篩選標準 (Post-Optimization)

穩定性指標**不直接包含**在 Optuna 的目標公式中，而是作為優化後的**過濾器 (Filter)**。

### 1. 月度穩定性計算 (Monthly Stability)
*   **對象**：僅針對 **正例 (Positive Cases)**。
*   **方法**：
    1.  將正例按「案例發生月份」分組。
    2.  計算每個月的 **加權平均 $M$**。
    3.  計算這組月度平均值的 **變異係數 (CV)**。
    $$ CV = \frac{\text{Std}(\text{Monthly Means})}{\max(|\text{Mean}(\text{Monthly Means})|, \epsilon)} $$
    *(原因：$M\in[-1,1]$ 可能為負且均值可能接近 0，使用 |Mean| 與下界可避免 CV 爆炸與符號歧義)*

### 1.1 月度 Gatekeeper 的最小樣本規則（必須加）

為避免小樣本月份造成 Monthly CV 嚴重噪聲，月度統計必須遵守以下規則之一（擇一採用並寫死於實作）：

*   每月正例有效案例數需達最小門檻；不足者該月不納入 CV。
*   每月正例權重總和需達最小門檻；不足者該月不納入 CV。

(建議：在報表中回傳「被納入 CV 計算的月份數」與「被排除月份數」，方便使用者理解空窗或稀疏問題。)

### 2. 篩選規則
在選出最佳參數後，必須檢查：
*   **Stability CV < 0.3**：確保策略在不同月份的表現一致。
*   **樣本覆蓋率**：確保沒有某個月份的信號數為 0 (空窗期)。

---

## 五、 驗收標準 (Acceptance Criteria)

以下條件必須同時滿足，才算完成本規格的工程落地：

1.  雙密度模式的 Optuna objective 使用本文件定義的 Score（不得再以 near/far ratio separation 作為核心目標）。
2.  不再剔除 Far=0 案例；但可保留 far=0 的統計欄位做觀測與診斷。
3.  P-value 與 Cohen's d 的輸入數據改為以案例 $M$ 值為基礎（與優化目標對齊）。
4.  Case A/B/C/D 的邊界條件處理完全一致，且不允許 0/0 或 NaN 進入 Optuna 分數。
5.  API response 向後相容：新增欄位不移除舊欄位，避免破壞既有前端/consumer。

---

## 六、 最小手算例（用於人工校對）

以下示例僅用於驗證公式方向與邊界條件，不代表真實市場分佈。

令 $\epsilon = 1e-5$。

### 1) 正例（pos）兩個案例

*   案例 P1：Near=0.20、Far=0.00
    *   $M \approx 1.0$、$w=0.20$
*   案例 P2：Near=0.10、Far=0.05
    *   $M \approx 0.333$、$w=0.15$

重點：P1 的 $M$ 雖為 1.0，但其影響力仍受 $w$ 控制；若 Near 很小，$w$ 也會很小。

### 2) 反例（neg）兩個案例

*   案例 N1：Near=0.02、Far=0.06
    *   $M \approx -0.5$、$w=0.08$
*   案例 N2：Near=0.00、Far=0.05
    *   $M \approx -1.0$、$w=0.05$

重點：當反例的 $M$ 偏負，會拉大 $\mu_{pos}-\mu_{neg}$；同時 $\sigma$ 會懲罰群體內部的波動。

### 3) Case B（反例無訊號）的示例

若反例全部 Near=0 且 Far=0，則 $S_{neg}=0$。

*   依本規格 Case B：約定 $\mu_{neg}=0,\sigma_{neg}=0$，並啟用「正例覆蓋門檻」避免只靠極少數正例拿高分。

---

## 七、 測試與影響面清單 (Impact & Verification Checklist)

本次修改預期會影響以下類型輸出與測試，請在工程落地時一併驗證：

*   API response schema：新增 $M$ 相關欄位（確認前端與既有 consumer 不會因反序列化失敗而中斷）。
*   雙密度模式報表：原先以 ratio 為主的顯示可保留，但需標註「非 objective」。
*   測試與驗證腳本：若斷言或打印依賴 ratio / far=0 剔除邏輯，需更新為新欄位與新邊界規則。

建議優先檢查：

*   tests/analysis/test_api_endpoints.py（若存在 response schema 斷言或欄位檢查）
*   任何使用 SignalDensityResponse 的前端/後端序列化流程
*   任何依賴 FAR_ZERO_THRESHOLD 或 far=0 剔除的分析流程

---

## 八、 總結與注意事項

1.  **數據比例**：正反例比例維持在 1:2 到 1:3 是健康的，公式中的 $\mu_{pos} - \mu_{neg}$ 結構對類別不平衡具有免疫力。
2.  **稀疏陷阱**：強度加權 ($w_i$) 是防止「僥倖案例」(Near=0.01, Far=0) 獲得高分的關鍵，**絕對不可省略**。
3.  **P-value 角色**：在樣本數大 (>1000) 時，P-value 通常極小，應主要參考 **Cohen's d** (基於 $M$ 分佈計算) 和 **Separation Score**。

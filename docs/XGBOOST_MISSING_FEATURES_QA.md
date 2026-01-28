# 🎓 XGBoost 多結果分析缺失項目 — 白話解釋與 Q&A

> **建立日期**: 2026-01-27  
> **目的**: 解釋系統缺失功能，並回答實作相關問題

---

## 📋 目錄

- [高優先級缺失項目](#高優先級缺失項目)
- [中優先級缺失項目](#中優先級缺失項目)
- [低優先級缺失項目](#低優先級缺失項目)
- [總結建議](#總結建議)

---

## 🔴 高優先級缺失項目

### 1. **時間外驗證 (OOT - Out-of-Time Validation)**

#### 📖 是什麼：
想像你是一位老師準備考試。你用去年的考題訓練學生，但真正的大考是用「今年全新的題目」。OOT 驗證就是用「完全沒見過的未來時間段」的數據來測試模型。

#### ❌ 現狀問題：
目前系統像是「用同一份考卷的不同題目來練習和測驗」，但沒有用「完全不同時期的考卷」來最終驗證。

#### 💡 為什麼重要：
- 加密貨幣市場會變化（2024 年的規律可能 2025 年就失效了）
- 如果模型只在「訓練時期」表現好，實際交易時可能慘賠
- 例如：2021 牛市訓練的模型，拿到 2022 熊市可能完全失效

#### 📊 實際影響：
假設模型在 2024 年數據上準確率 80%，但到了 2025 年可能只剩 50%（跟猜硬幣一樣）。沒有 OOT 驗證，你不會知道這個風險。

#### ❓ 常見問題

**Q1: OOT 驗證是如何做的？那我選一個相對高分的策略去跑另一個沒被訓練的時間段回測就可以知道有沒有用？**

**答案**: 你的理解是正確的核心概念,但需要更嚴格的操作流程。

**標準 OOT 驗證流程**:
```python
# 時間切分範例
train_period = "2021-01-01" to "2023-12-31"  # 訓練期
validation_period = "2024-01-01" to "2024-06-30"  # 驗證期 (CV 用)
OOT_period = "2024-07-01" to "2025-12-31"  # 測試期 (完全未見過)

# 流程:
1. 用 train_period 訓練模型 → 得到 Train AUC
2. 用 validation_period 做 CV → 得到 CV AUC  
3. 用 OOT_period 測試 → 得到 OOT AUC
```

**與回測的差異**:
- ✅ **回測系統**:模擬實際交易,計算損益、勝率、最大回撤等交易指標
- ✅ **OOT 驗證**:只評估模型「預測能力」(AUC),不涉及交易執行
- **建議**:先 OOT 驗證 (快速) → 再回測 (精確但耗時)

**系統實作建議**:
```python
# 在 momentum/Analysis/xgboost_analyzer.py 中新增
def validate_oot(self, X_oot: pd.DataFrame, y_oot: np.ndarray) -> float:
    """Out-of-Time 驗證"""
    y_pred_proba = self.model.predict_proba(X_oot)[:, 1]
    return roc_auc_score(y_oot, y_pred_proba)
```

**判斷標準**:
- 如果 `OOT AUC > 0.58` 且 `CV AUC - OOT AUC < 0.08` → 模型有真實預測力
- 如果 `OOT AUC < 0.52` → 模型已失效,不建議使用

---

**Q2: 其中的 CV AUC 不就是拿沒用來 Train 的案例看效果？**

**答案**: 是的,但有重要細節需要注意。

**CV (Cross-Validation) 的運作方式**:
```
5-Fold CV 範例:
┌────────────────────────────────────────┐
│ Fold 1: Train ■■■■ | Val ■             │ → AUC_1
│ Fold 2: Train ■ ■■■ | Val  ■           │ → AUC_2  
│ Fold 3: Train ■  ■■ | Val   ■          │ → AUC_3
│ Fold 4: Train ■   ■ | Val    ■         │ → AUC_4
│ Fold 5: Train ■    ■| Val     ■        │ → AUC_5
└────────────────────────────────────────┘
CV AUC Mean = (AUC_1 + ... + AUC_5) / 5
CV AUC Std = 標準差
```

**系統實作** (參考 [xgboost_analyzer.py](xgboost_analyzer.py#L284-L410)):
```python
# 使用 StratifiedKFold 保持類別比例
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
    X_train_fold = X[train_idx]  # 80% 數據訓練
    X_val_fold = X[val_idx]      # 20% 數據驗證（沒用來訓練）
    
    model_fold.fit(X_train_fold, y_train_fold)
    y_pred_proba = model_fold.predict_proba(X_val_fold)[:, 1]
    auc = roc_auc_score(y_val_fold, y_pred_proba)  # 計算 AUC
    cv_auc_scores.append(auc)
```

**CV 與 OOT 的差異**:
| 項目 | CV (交叉驗證) | OOT (時間外驗證) |
|-----|-------------|----------------|
| **數據來源** | 同一時間段,隨機切分 | 完全不同的時間段 |
| **目的** | 評估模型穩定性 | 評估時間泛化能力 |
| **風險** | 可能有資訊洩漏 | 最嚴格的測試 |

**系統現況**:
- ✅ 已實作 CV (5-fold, 可選時間序列切分)
- ❌ 未實作 OOT 驗證 (需手動切分數據)

**重點**:CV AUC 是「沒用來訓練的案例」沒錯,但如果這些案例與訓練集來自同一時期(如 2024 年全年),模型可能學到「2024 年的特有規律」而非「普遍規律」。OOT 驗證用「2025 年數據」測試,更能揭露真實泛化能力。

---

**Q3: 那我現在上傳的案例CSV後，系統是要怎麼定義Train period和validation_period而得到train AUC和CV AUC? 現在的系統是抓80%當訓練，剩下20%驗證?**

**答案**: 這是個非常實際的問題！讓我澄清當前系統的運作方式與改進建議。

#### 🔍 當前系統的實際行為

**在 XGBoost 訓練時**（參考 `xgboost_analyzer.py`）：
```
你上傳的案例 CSV → 系統讀取所有案例 → 開始訓練

1. Train AUC 計算:
   - 隨機切分: 80% 訓練, 20% 驗證（用於 early stopping）
   - 模型在 80% 數據上訓練完成後
   - 用這 80% 數據計算 Train AUC
   ⚠️ 這會讓 Train AUC 虛高（模型看過這些數據）

2. CV AUC 計算:
   - 使用 5-Fold Cross Validation
   - 每次用 80% 訓練, 20% 驗證
   - 但是是「隨機切分」或「時間序列切分」（可選）
   - 5 次驗證的平均值 = CV AUC Mean
```

#### ⚠️ 問題點

**時間定義不明確**：
- ❌ 系統**不會自動識別**你的案例是 2023 年還是 2024 年
- ❌ 如果你上傳的 CSV 包含 2021~2024 年所有案例，系統會「混在一起」隨機切分
- ❌ 沒有嚴格的 Train Period / Validation Period 概念

**隨機切分的風險**：
```
假設你的 CSV 包含:
- 2021 案例: 500 個
- 2022 案例: 600 個  
- 2023 案例: 700 個
- 2024 案例: 800 個

系統做 CV 時可能:
Fold 1 訓練集: [2021部分, 2022部分, 2023部分, 2024部分]
Fold 1 驗證集: [2021部分, 2022部分, 2023部分, 2024部分]

→ 訓練集和驗證集時間重疊！
→ 模型可能學到「2024特有的規律」但驗證時也用2024數據
```

#### ✅ 建議的改進方式

**方案 1: 手動時間切分（目前最實際）**
```
你在上傳 CSV 前先切分:
1. train.csv: 2021-2023 年案例（用於訓練）
2. validation.csv: 2024 1-6 月案例（用於驗證）
3. oot.csv: 2024 7-12 月案例（用於 OOT 測試）

然後:
- 只上傳 train.csv 做 XGBoost 訓練 → 得到 Train AUC 和 CV AUC
- 訓練完後,手動用 validation.csv 測試 → 得到 Validation AUC
- 最後用 oot.csv 測試 → 得到 OOT AUC
```

**方案 2: 系統支援時間序列切分（未來改進）**
```
系統新增功能:
- 讀取 CSV 時識別 timestamp 欄位
- 用戶指定:
  * Train Period: 2021-01-01 ~ 2023-12-31
  * Validation Period: 2024-01-01 ~ 2024-06-30
  * OOT Period: 2024-07-01 ~ 2024-12-31
- 系統自動按時間切分
- CV 使用 Walk-Forward 或 Time Series Split
```

#### 📊 目前系統的實際數字

當你上傳 1000 個案例的 CSV:
```
 Train/Val Split (80/20 for early stopping):
   訓練集: 800 案例 → 訓練完成後計算 Train AUC
   驗證集: 200 案例 → 僅用於 early stopping，不計入最終評估

 5-Fold CV:
   Fold 1: 訓練 800 案例, 驗證 200 案例 → AUC_1
   Fold 2: 訓練 800 案例, 驗證 200 案例 → AUC_2
   ...
   CV AUC Mean = (AUC_1 + ... + AUC_5) / 5

 ⚠️ 注意:
   - 這 1000 個案例是「隨機打散」後切分的
   - 沒有考慮時間順序（除非你勾選 time_series_split=True）
```

#### 🎯 實戰建議

**目前最佳做法**：
1. **訓練前先手動切分時間**：
   - 將 2021-2023 的案例單獨匯出 → train.csv
   - 只用 train.csv 訓練模型

2. **訓練時啟用時間序列切分**：
   - 如果系統有提供 `time_series_split` 選項,務必勾選
   - 這樣 CV 時會按時間順序切分,避免未來資訊洩漏

3. **訓練後手動驗證**：
   - 用 2024 年後半的案例 CSV 重新測試模型
   - 比較 CV AUC 和實際測試 AUC 的差距

**關鍵提醒**：
- 如果你無法確定案例的時間分佈,當前的 CV AUC 可能**不夠可靠**
- **務必保留最近的數據**（如最近3-6個月）不要用於訓練
- 把這些保留數據當作「真實的驗證集」來測試模型

---

**Q4: 時間外驗證看起來長久使用或要自動化，應該是要實作方案2系統支援時間序列切分？**

**答案**: 是的，而且要把兩件事拆開看：

1) **時間序列切分（Time Series Split / Walk-Forward）**：用在 **CV**，讓每一折都遵守「用過去預測未來」。
2) **OOT（Out-of-Time）**：用在 **最終驗收**，保留一段「完全未見過的最新時間」當最後考試。

長期自動化時，建議系統同時支援這兩個層級（CV 用時間序列切分，最終再跑 OOT）。

#### ✅ 方案 2（系統化）應該做到什麼

**輸入契約（上傳案例 CSV 必須/建議具備）**：

以你這次提供的案例檔 [test_data/case_search_results_2026-01-27 (1).csv](test_data/case_search_results_2026-01-27%20(1).csv) 為準：
- **必須**：可排序的時間欄位：`Timestamp`（ISO 格式字串，例如 `2025-12-02T00:00:00`）
- **必須**：標籤欄位：`Positive_Case`（0/1；注意你的檔案片段目前看起來多數是 1，需確認也有 0 的反例/負樣本）
- **建議**：市場階段欄位：`Market_Phase`（例如 `EXTREME_FEAR` / `FEAR`；可直接拿來做分 phase 的 AUC/Precision@K）
- **建議**：用於分組/回溯的識別欄位：`Symbol`、`Timeframe`、`Trigger_Index`

**case_id 建議**：系統內部最好建立一個穩定的 `case_id`（即使 CSV 沒有），例如以 `Symbol + Timestamp + Trigger_Index` 組合成唯一鍵，方便追蹤與輸出每筆案例的 `predicted_proba`。

**系統行為（可配置，但要可重現）**：
- **排序**：先按時間排序，不允許隨機打散
- **切分**：
    - Train Period / Validation Period / OOT Period 由用戶指定（或提供預設，例如「最後 3 個月當 OOT」）
    - CV 用 Walk-Forward（或 TimeSeriesSplit）
- **輸出**：在結果檔中保存「切分報告」與索引資訊，確保未來可重跑/可稽核

#### 🎯 為什麼方案 2 才適合長期自動化

方案 1（手動切分）適合你現在快速驗證；但要走向長期自動化，你會需要：
- 每次上傳都自動切出 OOT
- 每次訓練都自動用時間序列 CV
- 每次輸出都能回溯：當時用哪段時間訓練、哪段時間測試

這些都必須由方案 2 系統化完成。

---

### 2. **市場體制分析 (Regime Analysis)**

#### 📖 是什麼：
把市場分成三種「天氣」：
- **牛市（晴天）**：價格持續上漲，買什麼都賺
- **熊市（雨天）**：價格持續下跌，賣什麼都虧
- **震盪市（陰天）**：價格上上下下，沒有明確方向

#### ❌ 現狀問題：
目前模型不知道「天氣」的差異，用同一套策略應對所有情況。

#### 💡 為什麼重要：
- 某些策略只在牛市有效（例如：追漲）
- 某些策略只在震盪市有效（例如：低買高賣）
- 如果模型在牛市訓練，熊市時可能反向操作

#### 📊 實際影響：
就像夏天穿的衣服不適合冬天。如果你的模型在 2021 牛市表現超好（AUC 0.85），但實際上它只會喊「買買買」，到了 2022 熊市可能血本無歸。

#### ❓ 常見問題

**Q: 市場體制分析，這部分可能動能策略在牛市會出現很多案例，但在熊市鮮少有案例，所以要不同策略搭配，不是嗎？**

**答案**: 完全正確！這正是市場體制分析的核心價值。

**問題本質**:
```
動能策略特性:
- 牛市: 案例數 = 1000, AUC = 0.75 ✅ (追漲有效)
- 熊市: 案例數 = 50, AUC = 0.45 ❌ (追漲會虧)
- 震盪: 案例數 = 300, AUC = 0.55 ~ (效果普通)

如果不分體制訓練 → 整體 AUC 可能還有 0.68
但實際使用時:
  - 熊市期間會慘賠 (因為模型主要學到牛市規律)
  - 資金曲線會大幅回撤
```

**解決方案**:體制感知的策略組合

**方法 1: 單一模型加體制過濾**
```python
# 先識別當前市場體制
def identify_regime(df: pd.DataFrame, lookback: int = 20) -> str:
    """
    基於 ADX + 趨勢方向識別體制
    """
    # 趨勢強度 (ADX > 25 = 趨勢明確)
    adx = ta.adx(df['high'], df['low'], df['close'], length=lookback)['ADX_20']
    
    # 趨勢方向 (SMA 斜率)
    sma = df['close'].rolling(lookback).mean()
    trend_direction = sma.diff(5) / sma.shift(5)
    
    if adx.iloc[-1] > 25:
        if trend_direction.iloc[-1] > 0.02:
            return 'bull'  # 牛市
        elif trend_direction.iloc[-1] < -0.02:
            return 'bear'  # 熊市
    return 'sideways'  # 震盪市

# 根據體制決定是否交易
current_regime = identify_regime(df)
if current_regime == 'bear' and strategy_type == 'momentum':
    # 熊市不使用動能策略,避免虧損
    skip_trading = True
```

**方法 2: 多策略組合 (推薦)**
```python
strategy_pool = {
    'momentum': {
        'model': momentum_model,
        'best_regime': 'bull',
        'bull_auc': 0.75,
        'bear_auc': 0.45,
        'sideways_auc': 0.55
    },
    'mean_reversion': {
        'model': reversion_model,
        'best_regime': 'sideways',
        'bull_auc': 0.52,
        'bear_auc': 0.58,
        'sideways_auc': 0.72
    },
    'breakout': {
        'model': breakout_model,
        'best_regime': 'bull',
        'bull_auc': 0.70,
        'bear_auc': 0.62,
        'sideways_auc': 0.50
    }
}

# 動態選擇策略
current_regime = identify_regime(df)
active_strategy = max(
    strategy_pool.items(),
    key=lambda x: x[1][f'{current_regime}_auc']
)[0]
```

**系統實作建議**:
1. **在案例搜索時標記體制** (已有數據,需補充標記)
   ```python
   # 為每個案例添加 regime 標籤
   case['market_regime'] = identify_regime(kline_df.loc[:case['trigger_time']])
   ```

2. **分體制評估模型**
   ```python
   # 在 xgboost_analyzer.py 中新增
   def evaluate_by_regime(self, X, y, regime_labels):
       results = {}
       for regime in ['bull', 'bear', 'sideways']:
           mask = (regime_labels == regime)
           if mask.sum() > 30:  # 至少 30 個案例
               y_pred = self.model.predict_proba(X[mask])[:, 1]
               results[regime] = roc_auc_score(y[mask], y_pred)
       return results
   ```

3. **Dashboard 顯示體制表現**
   - 雷達圖: 顯示策略在三種體制的 AUC
   - 警告提示: 如果某體制 AUC < 0.52,建議不使用

**實戰案例**:
```
策略 A (動能):
  - 牛市 AUC 0.75, 案例數 1200
  - 熊市 AUC 0.48, 案例數 80
  - 建議: 只在牛市使用

策略 B (反轉):
  - 牛市 AUC 0.55, 案例數 200  
  - 熊市 AUC 0.68, 案例數 600
  - 建議: 只在熊市/震盪市使用

組合效果:
  - 牛市用 A, 熊市用 B
  - 整體收益曲線更平滑
  - 最大回撤從 -40% 降到 -20%
```

**關鍵結論**:你的理解完全正確。單一策略打天下是行不通的,需要「體制識別 + 多策略輪換」才能在不同市場環境下都有穩定表現。

---

**Q2: 我的意思是說訓練就不要去管市場體制，反正不管牛熊震盪，標的遇到這樣的pattern就可以會上漲。波段或其他策略也是另外研究，所以訓練時候不用分析市場體制**

**答案**: 這是個非常好的觀點！你的策略思路是對的，讓我重新定位市場體制分析的角色。

#### 🎯 你的策略理念（正確方向）

**核心假設**：
```
「RSI 超賣 + 成交量異常放大」這個 Pattern
→ 不管是牛市、熊市還是震盪市
→ 都代表「超賣反彈」即將發生
→ 所以訓練時不需要區分市場體制
```

**這個假設的優點**：
- ✅ 簡單直接,容易理解和執行
- ✅ 避免過度複雜化（市場體制識別本身就有誤判風險）
- ✅ 如果 Pattern 真的有效,應該在所有市場都有效
- ✅ 更容易獲得足夠的訓練樣本（不會因為切分體制而樣本不足）

#### ⚖️ 但需要注意的現實情況

**Pattern 的表現可能真的會因體制不同**：

**案例 1: 超賣反彈策略**
```
牛市中:
  RSI < 30 + 成交量放大 → 80% 機率反彈 ✅
  原因: 市場情緒樂觀,逢低就有人買

熊市中:
  RSI < 30 + 成交量放大 → 只有 45% 機率反彈 ❌
  原因: 可能是「恐慌性殺盤」,反彈無力

→ 同樣的 Pattern,表現差異大
```

**案例 2: 突破策略**
```
震盪市:
  突破前高 → 假突破居多 → 50% 勝率

牛市:
  突破前高 → 真突破居多 → 75% 勝率

→ 體制確實影響 Pattern 的效果
```

#### 🔬 實驗建議：兩種方法都試試看

**方法 A: 你的方法（不區分體制）**
```
Step 1: 用所有案例（2021-2024）訓練一個通用模型
Step 2: 測試整體 AUC（例如: 0.68）
Step 3: 如果 AUC > 0.65，代表 Pattern 確實普遍有效

優點:
- 訓練樣本多
- 模型簡單,易部署
- 不需要體制識別（避免額外誤差）
```

**方法 B: 體制分析（作為診斷工具）**
```
Step 1: 先用方法 A 訓練通用模型
Step 2: 訓練完後，事後分析:
   - 把驗證集案例標記體制（牛/熊/震盪）
   - 檢查模型在各體制的 AUC

Step 3: 診斷結果:
   如果 牛市AUC=0.75, 熊市AUC=0.48, 震盪AUC=0.70
   → 說明: Pattern 在熊市效果差
   → 決策: 可以設定「熊市期間不交易」的規則
```

#### 🎯 推薦的實戰流程

**階段 1: 訓練時不管體制（符合你的想法）**
```
1. 收集所有符合 Pattern 的案例
2. 不區分市場體制,全部混合訓練
3. 用 CV 評估整體性能
4. 如果 CV AUC > 0.65 → 繼續下一步
```

**階段 2: 訓練後診斷（確認是否需要體制規則）**
```
1. 將驗證集案例按體制分類:
   - 牛市案例: 用 ADX + 趨勢識別
   - 熊市案例: 同上
   - 震盪案例: 同上

2. 分別計算各體制的勝率:
   - 牛市勝率: 72%
   - 熊市勝率: 48% ⚠️
   - 震盪勝率: 68%

3. 決策:
   如果某個體制勝率 < 52%（接近隨機）
   → 增加過濾規則:「熊市時不使用此策略」
   如果所有體制勝率都 > 60%
   → 不需要體制過濾,直接用通用模型
```

**階段 3: 實盤交易時的應用**
```
如果診斷發現需要體制過濾:

實盤系統:
1. 模型預測出訊號
2. 額外檢查當前市場體制
3. 如果是「不利體制」→ 跳過此訊號
4. 如果是「有利體制」→ 執行交易

注意: 體制識別「不用於訓練」,只用於「交易過濾」
```

#### 📊 總結：你的做法與體制分析的定位

| 項目 | 你的做法（通用模型） | 加上體制分析 |
|-----|-----------------|------------|
| **訓練階段** | 所有案例混合訓練 ✅ | 所有案例混合訓練 ✅ |
| **訓練複雜度** | 簡單 ✅ | 簡單 ✅ |
| **模型數量** | 1 個通用模型 ✅ | 1 個通用模型 ✅ |
| **體制識別** | ❌ 不使用 | ✅ 僅用於事後診斷 |
| **交易過濾** | 無額外過濾 | 可選：過濾不利體制 |
| **適用場景** | Pattern 在所有體制都有效 | Pattern 在某些體制效果差 |

#### ✅ 最終建議

**你的方向是對的！訓練時不用管市場體制。**

但是：
1. **訓練後做個診斷**：檢查模型在不同體制的表現
2. **如果發現明顯差異**：
   - 不需要重新訓練多個模型
   - 只需在交易時加上「體制過濾規則」
   - 例如:「熊市時跳過此策略的訊號」
3. **如果各體制表現都不錯**：
   - 恭喜！你找到了真正「普遍有效」的 Pattern
   - 直接部署,不需要體制分析

**市場體制分析的真正用途**：
- ❌ 不是要你「訓練時分開處理」（太複雜）
- ✅ 而是「診斷工具」,幫你發現模型的弱點
- ✅ 讓你知道「何時不該交易」比「何時該交易」更重要

---

**Q3: 我案例上傳中就有 market phase，可以用 market phase 的 AUC 做分析嗎？**

**答案**: 可以，而且這其實是「最理想」的市場體制分析方式之一：

#### ✅ 你已經有 `market_phase` 的好處

對應到你上傳案例 CSV 的實際欄位名是 `Market_Phase`。

- 不需要再用 ADX/SMA 之類的規則去「推測」體制（會有誤判）
- 你可以直接做 **分 market phase 的 AUC / Precision@K / 勝率**
- 分析結果可直接轉成「交易過濾」或「分級交易」的規則

#### 📊 建議輸出格式（診斷報告）

對每個 `Market_Phase`（你現在的值像是 `EXTREME_FEAR` / `FEAR`；也可能還有其他 phase）輸出：
- `support`（該 phase 案例數）
- `auc`（AUC）
- `precision_at_k`（可選：用同一套 K 或該 phase 專屬的 K）
- `avg_pred_proba`（該 phase 的平均預測機率，用於判斷模型是否過度自信）

#### ⚠️ 注意事項（避免誤判）

- **樣本數下限**：某個 phase 案例太少（例如 < 50）時，AUC 波動會很大，建議標記為「資訊不足」而非下結論。
- **一致的 phase 定義**：`market_phase` 的標註規則要固定（否則不同期間的 phase 不可比）。
- **最好搭配 OOT**：分 phase 的 AUC 也要在 OOT 期間再驗一次，避免只在訓練期看起來漂亮。

---

### 3. **機率校準指標 (Brier Score / ECE)**

#### 📖 是什麼：
檢查模型的「自信程度」是否準確。

#### 🎯 比喻：
- 模型說「這次交易有 90% 機率賺錢」
- **已校準**：實際上這類交易真的有 90% 賺錢
- **未校準**：實際上可能只有 60% 賺錢（模型太自信了）

#### ❌ 現狀問題：
目前只知道模型「預測對錯」，但不知道它的「信心指數」是否可信。

#### 💡 為什麼重要：
- 如果模型說 90% 會賺，你可能會下重注
- 但如果實際只有 60%，你就虧大了
- Brier Score 和 ECE 就是衡量「信心準不準」的分數

#### 📊 實際影響：
兩個模型準確率都是 70%，但：
- 模型 A：該自信時自信，該謹慎時謹慎（Brier Score 低）
- 模型 B：總是過度自信，害你下錯注（Brier Score 高）

#### ❓ 常見問題

**Q: 機率校準指標中舉例，模型說「這次交易有 90% 機率賺錢」，這其中的 90% 是怎麼計算出來的？機率校準指標（Brier Score/ECE）是怎麼計算出來的？**

**答案**: 讓我用白話和程式碼詳細解釋。

---

### 📊 Part 1: 90% 機率怎麼來的？

**XGBoost 的機率預測**:
```python
# 系統實作 (參考 xgboost_analyzer.py)
model = xgb.XGBClassifier(objective='binary:logistic')  # 輸出機率
model.fit(X_train, y_train)

# 預測單一案例
case_features = [[0.65, 1.2, 0.82, ...]]  # RSI, Volume, Taker Ratio...
proba = model.predict_proba(case_features)[0, 1]  # 取正類別(盈利)的機率

print(f"模型預測盈利機率: {proba:.2%}")  # 可能輸出 90.5%
```

**背後原理** (簡化版):
```python
# XGBoost 的機率計算 (內部邏輯)
# 1. 每棵決策樹給出分數
tree_1_score = +0.3  # 看好這筆交易
tree_2_score = +0.5
tree_3_score = +0.2
# ... 100 棵樹

# 2. 加總分數
raw_score = sum([tree_1_score, tree_2_score, ...])  # 假設 = 2.2

# 3. Sigmoid 轉換成機率 (0~1)
proba = 1 / (1 + exp(-raw_score))  # 假設 = 0.90 → 90%
```

**重點**: 這個 90% 是模型「自己覺得」的信心,但不一定準確！

---

**Q2: 目前的系統好像沒有輸出機率預測？這個會影響機率校準指標的實作嗎？**

**答案**: 會影響，而且你觀察得很準。

#### ✅ 目前系統的狀態（要分「有算」與「有輸出」）

- **模型內部一定有機率**：因為 AUC、Brier、ECE、PR AUC 等指標都需要 `predict_proba` 才能算。
- **但使用者可能看不到**：若 API/前端結果只輸出 AUC、或只輸出規則/摘要，沒有把「每筆案例的 predicted_proba」輸出出來，你就沒辦法：
    - 檢查機率分佈（是否大量集中在 0.99 / 0.01）
    - 畫校準曲線
    - 做分 market phase 的信心分析

#### 🎯 落地實作時應該補的輸出（最小可用）

為了支援機率校準與後續視覺化，建議在分析結果（後端 artifact / API response）至少增加：
- `predictions`：每筆案例的 `case_id` / `y_true` / `predicted_proba`（至少驗證集與 OOT）
- `proba_summary`：機率分佈的分箱統計（例如 0-0.1、0.1-0.2...）
- `calibration_metrics`：Brier、ECE（以及之後的 Calibration Curve 資料點）

這樣你才有足夠的資料把「校準」做成可檢查、可監控、可視覺化的能力。

---

### ⚖️ Part 2: 機率校準指標怎麼算？

#### **A. Brier Score (布萊爾分數)**

**白話**: 平均「預測機率」與「實際結果」的平方誤差

**公式**:
```
Brier Score = (1/N) × Σ (predicted_prob - actual_result)²

其中:
- predicted_prob: 模型預測的機率 (0~1)
- actual_result: 實際結果 (0=虧損, 1=盈利)
```

**Python 實作**:
```python
from sklearn.metrics import brier_score_loss

# 範例數據
y_true = np.array([1, 0, 1, 1, 0])  # 實際: 賺, 虧, 賺, 賺, 虧
y_pred_proba = np.array([0.9, 0.3, 0.8, 0.95, 0.2])  # 模型預測機率

# 計算 Brier Score
brier = brier_score_loss(y_true, y_pred_proba)
print(f"Brier Score: {brier:.4f}")  # 越接近 0 越好

# 手動計算驗證
manual = np.mean((y_pred_proba - y_true) ** 2)
print(f"手動計算: {manual:.4f}")  # 結果相同
```

**解讀**:
```
案例 1: 預測 90%, 實際盈利 → 誤差 = (0.9 - 1)² = 0.01 ✅ 很準
案例 2: 預測 30%, 實際虧損 → 誤差 = (0.3 - 0)² = 0.09 ✓ 還行
案例 3: 預測 80%, 實際盈利 → 誤差 = (0.8 - 1)² = 0.04 ✓
...
平均誤差 = Brier Score = 0.048  (< 0.25 為佳)
```

---

#### **B. ECE (Expected Calibration Error)**

**白話**: 把預測機率分成幾個區間,檢查「說 70% 的時候,實際上是不是真的有 70% 準確率」

**視覺化範例**:
```
機率區間 | 預測機率 | 實際準確率 | 誤差
---------|---------|-----------|------
0-10%    |   5%    |    8%     |  3%
10-20%   |  15%    |   12%     |  3%
...
80-90%   |  85%    |   65%     | 20% ❌ 過度自信！
90-100%  |  95%    |   80%     | 15% ❌ 過度自信！

ECE = 平均誤差 = 8.5%  (< 5% 為佳)
```

**Python 實作**:
```python
def calculate_ece(y_true, y_pred_proba, n_bins=10):
    """
    計算 Expected Calibration Error
    
    Args:
        y_true: 實際標籤 (0/1)
        y_pred_proba: 預測機率 (0~1)
        n_bins: 分桶數量 (預設 10)
    
    Returns:
        ECE 分數 (0~1, 越接近 0 越好)
    """
    from sklearn.calibration import calibration_curve
    
    # 計算校準曲線
    prob_true, prob_pred = calibration_curve(
        y_true, y_pred_proba, n_bins=n_bins, strategy='uniform'
    )
    
    # 計算每個區間的樣本數
    bins = np.linspace(0, 1, n_bins + 1)
    bin_indices = np.digitize(y_pred_proba, bins[1:-1])
    bin_counts = np.bincount(bin_indices, minlength=n_bins)
    
    # 計算加權平均誤差
    ece = np.sum(np.abs(prob_true - prob_pred) * bin_counts) / len(y_true)
    
    return ece

# 使用範例
y_true = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0] * 100)  # 1000 個案例
y_pred_proba = model.predict_proba(X_test)[:, 1]

ece = calculate_ece(y_true, y_pred_proba)
print(f"ECE: {ece:.4f}")  # 0.05 以下表示校準良好
```

---

### 🎯 Part 3: 系統整合建議

**在 XGBoostAnalyzer 中新增方法**:
```python
# momentum/Analysis/xgboost_analyzer.py

from sklearn.metrics import brier_score_loss
from sklearn.calibration import calibration_curve

class XGBoostAnalyzer:
    # ... 現有程式碼 ...
    
    def calculate_calibration_metrics(
        self,
        X: pd.DataFrame,
        y: np.ndarray
    ) -> Dict[str, float]:
        """
        計算機率校準指標
        
        Returns:
            {
                'brier_score': 0.048,
                'ece': 0.035,
                'calibration_quality': 'good'  # good/fair/poor
            }
        """
        if self.model is None:
            raise ValueError("模型尚未訓練")
        
        # 預測機率
        y_pred_proba = self.model.predict_proba(X)[:, 1]
        
        # Brier Score
        brier = brier_score_loss(y, y_pred_proba)
        
        # ECE
        ece = self._calculate_ece(y, y_pred_proba, n_bins=10)
        
        # 評級
        if ece < 0.05 and brier < 0.15:
            quality = 'good'
        elif ece < 0.10 and brier < 0.25:
            quality = 'fair'
        else:
            quality = 'poor'
        
        self.logger.info(
            f"校準指標 - Brier: {brier:.4f}, ECE: {ece:.4f}, Quality: {quality}"
        )
        
        return {
            'brier_score': float(brier),
            'ece': float(ece),
            'calibration_quality': quality
        }
    
    def _calculate_ece(self, y_true, y_pred_proba, n_bins=10):
        """內部方法: 計算 ECE"""
        prob_true, prob_pred = calibration_curve(
            y_true, y_pred_proba, n_bins=n_bins, strategy='uniform'
        )
        bins = np.linspace(0, 1, n_bins + 1)
        bin_indices = np.digitize(y_pred_proba, bins[1:-1])
        bin_counts = np.bincount(bin_indices, minlength=n_bins)
        ece = np.sum(np.abs(prob_true - prob_pred) * bin_counts) / len(y_true)
        return ece
```

**ModelPerformance 擴展**:
```python
@dataclass
class ModelPerformance:
    train_auc: float
    cv_auc_mean: float
    cv_auc_std: float
    precision: float
    recall: float
    f1_score: float
    overfitting_score: float
    
    # 新增校準指標
    brier_score: Optional[float] = None
    ece: Optional[float] = None
    calibration_quality: Optional[str] = None
```

**判斷標準**:
```python
# 好的模型
brier_score < 0.15 and ece < 0.05

# 一般模型 (可用但需注意)
0.15 < brier_score < 0.25 and 0.05 < ece < 0.10

# 差的模型 (機率不可信,只能看正負號)
brier_score > 0.25 or ece > 0.10
```

**重點總結**:
- **90% 機率**: XGBoost 通過 Sigmoid 函式把樹的加總分數轉成機率
- **Brier Score**: 平方誤差,越接近 0 越好 (< 0.15 為佳)
- **ECE**: 分區間檢查,確保「說 80% 時真的有 80%」(< 0.05 為佳)
- **系統需要**: 在訓練後自動計算這兩個指標,避免過度自信的模型誤導交易

---

### 4. **PR AUC (Precision-Recall AUC)**

#### 📖 是什麼：
當「賺錢的交易」很少時（例如 100 次交易只有 10 次賺），傳統的 ROC AUC 會「虛胖」。PR AUC 更誠實地反映真實表現。

#### 🎯 比喻：
- 假設你是醫生診斷罕見疾病（1000 人只有 10 人生病）
- 模型說「大家都沒病」，準確率也有 99%（但沒用，病人沒被抓出來）
- PR AUC 會嚴格評分「你到底抓對幾個病人」

#### ❌ 現狀問題：
目前只有 ROC AUC，在盈利案例很少時容易「灌水」。

#### 💡 為什麼重要：
- 量化交易中，真正賺錢的訊號可能很稀少
- ROC AUC 可能顯示 0.75（看起來不錯），但 PR AUC 只有 0.45（其實很差）

#### 📊 實際影響：
如果你的模型在「10% 盈利案例」的數據上訓練，ROC AUC 0.80 可能只是因為它很會「避開虧損」，但不代表能「找到盈利」。PR AUC 會揭露真相。

#### ❓ 常見問題

**Q: 現在的 Train AUC/CV AUC 都是 ROC AUC？AUC 是怎麼計算出來的？**

**答案**: 是的,目前系統使用的都是 **ROC AUC**。讓我詳細解釋計算方式。

---

### 📊 Part 1: ROC AUC 是什麼？

**ROC (Receiver Operating Characteristic) Curve**:
- **X 軸**: False Positive Rate (FPR) = 誤報率 = "預測會賺但實際虧" / "所有虧損案例"
- **Y 軸**: True Positive Rate (TPR) = 召回率 = "預測會賺且實際賺" / "所有盈利案例"

**AUC (Area Under Curve)**:
- ROC 曲線下方的面積
- 範圍: 0.5 (跟猜的一樣) ~ 1.0 (完美預測)

---

### 🔢 Part 2: 計算過程 (白話版)

**Step 1: 模型預測機率**
```python
# 系統實作 (參考 xgboost_analyzer.py:187)
y_pred_proba = model.predict_proba(X_test)[:, 1]  # 取盈利機率

# 範例輸出
案例 1: 預測機率 0.95, 實際結果: 盈利 ✓
案例 2: 預測機率 0.82, 實際結果: 盈利 ✓
案例 3: 預測機率 0.73, 實際結果: 虧損 ✗
案例 4: 預測機率 0.45, 實際結果: 虧損 ✓
案例 5: 預測機率 0.20, 實際結果: 虧損 ✓
```

**Step 2: 嘗試不同閾值,計算 TPR 和 FPR**
```python
# 假設閾值 = 0.70
# 機率 > 0.70 → 預測為"盈利"
# 機率 ≤ 0.70 → 預測為"虧損"

實際盈利 | 預測盈利 | 結果
---------|---------|-----
  ✓      |   ✓     | True Positive (TP)
  ✓      |   ✗     | False Negative (FN)
  ✗      |   ✓     | False Positive (FP)
  ✗      |   ✗     | True Negative (TN)

TPR = TP / (TP + FN) = 2/3 = 0.67  # 抓到多少盈利案例
FPR = FP / (FP + TN) = 1/3 = 0.33  # 誤判多少虧損案例

→ 在 ROC 曲線上標記點 (0.33, 0.67)
```

**Step 3: 遍歷所有可能的閾值**
```python
from sklearn.metrics import roc_curve, roc_auc_score

# 自動計算 ROC 曲線
fpr, tpr, thresholds = roc_curve(y_true, y_pred_proba)

# 範例輸出
閾值 | FPR  | TPR
-----|------|-----
1.00 | 0.00 | 0.00  # 沒人被預測為盈利
0.95 | 0.05 | 0.20
0.80 | 0.15 | 0.60
0.70 | 0.33 | 0.67  # ← 剛才的範例
0.50 | 0.50 | 0.80  # 平衡點
0.30 | 0.70 | 0.90
0.00 | 1.00 | 1.00  # 所有人都被預測為盈利
```

**Step 4: 計算曲線下面積 (AUC)**
```python
# sklearn 自動計算
auc = roc_auc_score(y_true, y_pred_proba)
print(f"AUC: {auc:.4f}")  # 例如: 0.7234

# 手動計算 (梯形法則)
auc_manual = np.trapz(tpr, fpr)  # 積分計算面積
```

---

### 💻 Part 3: 系統實際實作

**Train AUC 計算** ([xgboost_analyzer.py:185-187](xgboost_analyzer.py#L185-L187)):
```python
# 訓練完成後
y_train_pred = self.model.predict_proba(X_train)[:, 1]  # 預測訓練集機率
train_auc = roc_auc_score(y_train, y_train_pred)  # 計算 AUC

self.logger.info(f"Train AUC: {train_auc:.4f}")
```

**CV AUC 計算** ([xgboost_analyzer.py:344-357](xgboost_analyzer.py#L344-L357)):
```python
# 5-Fold 交叉驗證
cv_auc_scores = []

for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
    # 訓練這個 fold
    model_fold.fit(X_train_fold, y_train_fold)
    
    # 預測驗證集
    y_pred_proba = model_fold.predict_proba(X_val_fold)[:, 1]
    
    # 計算這個 fold 的 AUC
    auc = roc_auc_score(y_val_fold, y_pred_proba)
    cv_auc_scores.append(auc)
    
    self.logger.info(f"Fold {fold + 1}/5 - AUC: {auc:.4f}")

# 平均和標準差
cv_auc_mean = np.mean(cv_auc_scores)  # 例如: 0.68
cv_auc_std = np.std(cv_auc_scores)    # 例如: 0.03
```

---

### 🎯 Part 4: AUC 的直覺理解

**物理意義**:
```
AUC = 隨機抽一個盈利案例和一個虧損案例,
      模型給盈利案例更高分數的機率

例如:
- AUC = 0.75 → 有 75% 的機率,模型能正確排序
- AUC = 0.50 → 跟隨機猜一樣
- AUC = 0.90 → 非常強的排序能力
```

**實際案例**:
```python
# 假設有 5 個案例
y_true =       [1,    1,    0,    0,    1]  # 實際: 賺, 賺, 虧, 虧, 賺
y_pred_proba = [0.9,  0.7,  0.6,  0.4,  0.8] # 預測機率

# 排序能力測試
盈利案例的機率: [0.9, 0.7, 0.8] → 平均 0.80
虧損案例的機率: [0.6, 0.4]     → 平均 0.50

→ 模型能區分盈利和虧損 → AUC 會接近 0.80

# 實際計算
auc = roc_auc_score(y_true, y_pred_proba)
print(f"AUC: {auc:.4f}")  # 輸出: 0.8333
```

---

### ⚠️ Part 5: 為什麼需要 PR AUC？

**ROC AUC 的問題** (當類別不平衡時):
```python
# 假設 1000 個案例: 900 虧損, 100 盈利 (10%)

模型 A:
  - 說所有案例都虧損
  - Accuracy = 90% ✅ (看起來很好)
  - ROC AUC = 0.50 (但其實沒用,跟猜的一樣)
  - 實際價值: 0 (一個盈利訊號都抓不到)

模型 B:
  - 能找出 50 個真正的盈利案例
  - ROC AUC = 0.72 ✅
  - PR AUC = 0.45 ❌ (揭露真相: 其實不夠好)
```

**PR AUC (Precision-Recall AUC)**:
- 更關注「找到盈利案例的能力」
- 在類別不平衡時更誠實
- 系統目前未實作,建議新增

**實作建議**:
```python
# 在 xgboost_analyzer.py 中新增
from sklearn.metrics import precision_recall_curve, auc as calc_auc

def calculate_pr_auc(self, X, y):
    """
    計算 Precision-Recall AUC
    """
    y_pred_proba = self.model.predict_proba(X)[:, 1]
    precision, recall, _ = precision_recall_curve(y, y_pred_proba)
    pr_auc = calc_auc(recall, precision)
    
    self.logger.info(f"PR AUC: {pr_auc:.4f}")
    return pr_auc
```

---

### 📋 總結

| 項目 | 現況 | 說明 |
|-----|------|------|
| **Train AUC** | ✅ ROC AUC | 用 sklearn.roc_auc_score 計算 |
| **CV AUC** | ✅ ROC AUC | 5-fold 平均 |
| **PR AUC** | ❌ 未實作 | 建議新增,類別不平衡時更準確 |
| **計算方式** | 自動 | sklearn 內部實作 (梯形積分) |

**關鍵程式碼位置**:
- Train AUC: [xgboost_analyzer.py:185-187](xgboost_analyzer.py#L185-L187)
- CV AUC: [xgboost_analyzer.py:344-357](xgboost_analyzer.py#L344-L357)
- 使用函式: `sklearn.metrics.roc_auc_score`

**重點**:
- 系統目前只用 ROC AUC
- 如果盈利案例 < 20%,建議增加 PR AUC 評估
- AUC > 0.65 為可用模型, > 0.75 為優秀模型

---

### 5. **PSI (Population Stability Index - 特徵飄移)**

#### 📖 是什麼：
檢查「特徵的分佈」是否隨時間改變。

#### 🎯 比喻：
你用「台灣人的平均身高」訓練模型，但測試時用的是「NBA 球員的身高」→ 分佈完全不同，模型會失效。

#### ❌ 現狀問題：
目前不知道特徵（例如 RSI、EMA）的分佈是否「漂移」了。

#### 💡 為什麼重要：
- 2020 年比特幣的 RSI 平均值可能是 55
- 2024 年可能變成 45（市場參與者變了、交易量變了）
- 如果 PSI > 0.1，代表特徵已經「變質」，模型需要重新訓練

#### 📊 實際影響：
就像用「20 年前的股票規律」來預測現在的市場 → 時代變了，策略失效。PSI 會提前警告你「該更新模型了」。

#### ❓ 常見問題

**Q: PSI 特徵飄移怎麼計算出來的？**

**答案**: PSI (Population Stability Index) 用來檢測特徵分佈是否隨時間改變。讓我用實際範例詳細說明。

---

### 📊 Part 1: PSI 的核心概念

**問題情境**:
```
訓練時 (2024): RSI 平均值 = 55, 標準差 = 15
測試時 (2025): RSI 平均值 = 45, 標準差 = 20

→ 分佈改變了！模型可能失效
```

**PSI 公式**:
```
PSI = Σ (Actual% - Expected%) × ln(Actual% / Expected%)

其中:
- Expected%: 訓練集(基準期)的特徵分佈
- Actual%: 測試集(當前期)的特徵分佈
```

**判斷標準**:
```
PSI < 0.1  → 穩定 ✅ (分佈無明顯變化)
0.1 ≤ PSI < 0.25 → 輕微飄移 ⚠️ (需要監控)
PSI ≥ 0.25 → 嚴重飄移 ❌ (需要重新訓練)
```

---

### 🔢 Part 2: 計算步驟 (白話版)

**範例: 計算 RSI 特徵的 PSI**

**Step 1: 將特徵分桶**
```python
import numpy as np
import pandas as pd

# 訓練集 RSI 數據 (基準期)
rsi_train = np.array([45, 52, 60, 38, 55, 70, 42, 58, 65, 50, ...])  # 1000 個

# 測試集 RSI 數據 (當前期 - 2 個月後)
rsi_test = np.array([40, 48, 55, 35, 50, 62, 38, 52, 58, 45, ...])  # 500 個

# 創建分桶 (10 個區間)
bins = [0, 20, 30, 40, 50, 60, 70, 80, 90, 100]
bin_labels = ['0-20', '20-30', '30-40', '40-50', '50-60', 
              '60-70', '70-80', '80-90', '90-100']
```

**Step 2: 計算各桶的樣本比例**
```python
# 訓練集分佈
train_binned = pd.cut(rsi_train, bins=bins, labels=bin_labels)
train_dist = train_binned.value_counts(normalize=True).sort_index()

# 測試集分佈
test_binned = pd.cut(rsi_test, bins=bins, labels=bin_labels)
test_dist = test_binned.value_counts(normalize=True).sort_index()

# 範例輸出
區間    | Expected% (訓練) | Actual% (測試) | 差異
--------|-----------------|---------------|------
0-20    |      1%         |      2%       | +1%
20-30   |      5%         |      8%       | +3%  ⚠️
30-40   |     12%         |     18%       | +6%  ⚠️
40-50   |     20%         |     25%       | +5%  ⚠️
50-60   |     25%         |     22%       | -3%
60-70   |     20%         |     15%       | -5%  ⚠️
70-80   |     12%         |      8%       | -4%
80-90   |      4%         |      2%       | -2%
90-100  |      1%         |      0%       | -1%
```

**Step 3: 計算 PSI**
```python
def calculate_psi(expected, actual, bins=10):
    """
    計算 PSI (Population Stability Index)
    
    Args:
        expected: 訓練集特徵數據 (基準期)
        actual: 測試集特徵數據 (當前期)
        bins: 分桶數量
    
    Returns:
        PSI 分數 (float)
    """
    # 確定分桶範圍 (基於訓練集)
    bin_edges = np.percentile(expected, np.linspace(0, 100, bins + 1))
    
    # 計算各桶的樣本比例
    expected_percents = np.histogram(expected, bins=bin_edges)[0] / len(expected)
    actual_percents = np.histogram(actual, bins=bin_edges)[0] / len(actual)
    
    # 避免除以0 (加上極小值)
    expected_percents = np.where(expected_percents == 0, 0.0001, expected_percents)
    actual_percents = np.where(actual_percents == 0, 0.0001, actual_percents)
    
    # 計算 PSI
    psi_values = (actual_percents - expected_percents) * np.log(actual_percents / expected_percents)
    psi = np.sum(psi_values)
    
    return psi

# 使用範例
psi_rsi = calculate_psi(rsi_train, rsi_test, bins=10)
print(f"RSI PSI: {psi_rsi:.4f}")  # 例如: 0.156 (輕微飄移)
```

**手動計算驗證** (使用上面的表格):
```python
# 桶 30-40: Expected% = 12%, Actual% = 18%
psi_30_40 = (0.18 - 0.12) * np.log(0.18 / 0.12)
          = 0.06 * np.log(1.5)
          = 0.06 * 0.405
          = 0.0243

# 對所有桶重複計算並加總
PSI = 0.0243 + 0.0189 + ... = 0.156  ⚠️ 輕微飄移
```

---

### 💻 Part 3: 系統實作建議

**在 XGBoostAnalyzer 中新增方法**:
```python
# momentum/Analysis/xgboost_analyzer.py

class XGBoostAnalyzer:
    # ... 現有程式碼 ...
    
    def calculate_feature_psi(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        bins: int = 10
    ) -> Dict[str, float]:
        """
        計算所有特徵的 PSI
        
        Args:
            X_train: 訓練集特徵 (基準期)
            X_test: 測試集特徵 (當前期)
            bins: 分桶數量
        
        Returns:
            { 'feature_name': psi_value, ... }
        """
        psi_results = {}
        
        for feature in X_train.columns:
            # 計算單一特徵的 PSI
            psi = self._calculate_single_psi(
                X_train[feature].values,
                X_test[feature].values,
                bins=bins
            )
            psi_results[feature] = psi
            
            # 警告提示
            if psi >= 0.25:
                self.logger.warning(
                    f"特徵 {feature} 嚴重飄移 (PSI={psi:.4f})，建議重新訓練"
                )
            elif psi >= 0.1:
                self.logger.info(
                    f"特徵 {feature} 輕微飄移 (PSI={psi:.4f})，需要監控"
                )
        
        # 排序並顯示前 10 飄移最嚴重的特徵
        sorted_psi = sorted(psi_results.items(), key=lambda x: x[1], reverse=True)
        self.logger.info("\nTop 10 飄移特徵:")
        for feature, psi in sorted_psi[:10]:
            status = "❌" if psi >= 0.25 else "⚠️" if psi >= 0.1 else "✅"
            self.logger.info(f"  {status} {feature}: {psi:.4f}")
        
        return psi_results
    
    def _calculate_single_psi(
        self,
        expected: np.ndarray,
        actual: np.ndarray,
        bins: int = 10
    ) -> float:
        """
        計算單一特徵的 PSI
        """
        # 去除 NaN
        expected = expected[~np.isnan(expected)]
        actual = actual[~np.isnan(actual)]
        
        if len(expected) == 0 or len(actual) == 0:
            return np.nan
        
        # 基於訓練集確定分桶範圍
        bin_edges = np.percentile(expected, np.linspace(0, 100, bins + 1))
        
        # 計算分佈
        expected_percents = np.histogram(expected, bins=bin_edges)[0] / len(expected)
        actual_percents = np.histogram(actual, bins=bin_edges)[0] / len(actual)
        
        # 避免除以 0
        expected_percents = np.where(expected_percents == 0, 0.0001, expected_percents)
        actual_percents = np.where(actual_percents == 0, 0.0001, actual_percents)
        
        # 計算 PSI
        psi_values = (
            (actual_percents - expected_percents) * 
            np.log(actual_percents / expected_percents)
        )
        psi = np.sum(psi_values)
        
        return float(psi)
```

---

### 🎯 Part 4: 實際應用場景

**場景 1: 模型上線後監控**
``python
# 每週或每月檢查
X_train = load_training_data("2024-01-01", "2024-12-31")
X_current = load_recent_data("2025-01-01", "2025-01-31")

psi_results = analyzer.calculate_feature_psi(X_train, X_current)

# 決策
if max(psi_results.values()) > 0.25:
    trigger_model_retraining()
elif max(psi_results.values()) > 0.1:
    increase_monitoring_frequency()
```

**場景 2: OOT 驗證前的預檢查**
```python
# 在跑 OOT 驗證前,先檢查特徵分佈
psi_results = analyzer.calculate_feature_psi(X_train, X_oot)

if max(psi_results.values()) > 0.3:
    print("⚠️ 警告: OOT 期間市場環境大幅改變,模型可能失效")
    print("建議: 縮短 OOT 時間範圍或分段驗證")
```

**場景 3: 跨幣種驗證**
```python
# 檢查 BTC 訓練的模型能否用於 ETH
X_btc = load_features("BTCUSDT")
X_eth = load_features("ETHUSDT")

psi_results = analyzer.calculate_feature_psi(X_btc, X_eth)

if np.mean(list(psi_results.values())) > 0.2:
    print("❌ 兩個幣種的特徵分佈差異太大,不建議共用模型")
```

---

### 📊 Part 5: 視覺化範例

```python
import matplotlib.pyplot as plt

def plot_feature_distribution_comparison(
    expected: np.ndarray,
    actual: np.ndarray,
    feature_name: str,
    psi: float
):
    """
    繪製特徵分佈對比圖
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    
    # 左圖: 直方圖對比
    ax1.hist(expected, bins=20, alpha=0.6, label='訓練集 (基準)', color='blue')
    ax1.hist(actual, bins=20, alpha=0.6, label='測試集 (當前)', color='red')
    ax1.set_title(f'{feature_name} 分佈對比\nPSI = {psi:.4f}')
    ax1.legend()
    ax1.set_xlabel('特徵值')
    ax1.set_ylabel('樣本數')
    
    # 右圖: 累積分佈函式 (CDF)
    ax2.hist(expected, bins=50, cumulative=True, density=True, 
             histtype='step', label='訓練集', linewidth=2, color='blue')
    ax2.hist(actual, bins=50, cumulative=True, density=True,
             histtype='step', label='測試集', linewidth=2, color='red')
    ax2.set_title('累積分佈對比')
    ax2.legend()
    ax2.set_xlabel('特徵值')
    ax2.set_ylabel('累積機率')
    
    plt.tight_layout()
    plt.savefig(f'psi_{feature_name}.png', dpi=150)
    plt.close()

# 使用範例
plot_feature_distribution_comparison(
    rsi_train, rsi_test, 'RSI', psi_rsi
)
```

---

### 📋 總結

| 項目 | 說明 |
|-----|------|
| **PSI 計算** | 比較訓練集和測試集的特徵分佈差異 |
| **分桶方式** | 通常 10 個桶,基於訓練集百分位數 |
| **判斷標準** | < 0.1 穩定, 0.1-0.25 輕微飄移, ≥ 0.25 嚴重飄移 |
| **系統現況** | ❌ 未實作,建議新增 |
| **應用時機** | 模型上線後監控、OOT 驗證前檢查、跨幣種驗證 |

**重點**:
- PSI 是「早期預警系統」,在模型失效前發現問題
- 定期檢查 (每週/每月) 可避免使用過時模型
- 如果 PSI > 0.25,即使 AUC 還不錯,也應該重新訓練
- 建議優先檢查「特徵重要性 Top 10」的 PSI

---

### 6. **SHAP 分析 (SHapley Additive exPlanations)**

#### 📖 是什麼：
解釋「每個因素對預測的貢獻度」，而且能看出是正面還是負面影響。

#### 🎯 比喻：
醫生診斷你生病的原因：
- 發燒 +30 分（最重要）
- 咳嗽 +15 分
- 精神好 -10 分（減分）
→ 總分 = 35 分 → 診斷為感冒

#### ❌ 現狀問題：
目前只知道「RSI 很重要」，但不知道：
- RSI 高時是做多訊號還是做空訊號？
- RSI 跟其他指標如何互動？

#### 💡 為什麼重要：
- 可以發現「RSI > 70 時，配合成交量放大才是真訊號」
- 避免誤用指標（例如某個指標其實是反指標）

#### 📊 實際影響：
兩個模型都說「EMA 重要性 20%」，但：
- 模型 A：EMA 往上 = 做多（正貢獻）
- 模型 B：EMA 往上 = 做空（負貢獻）
→ 沒有 SHAP 分析，你不知道該聽誰的。

#### ❓ 常見問題

**Q: SHAP 分析跟現在列出的決策規則 TOP10 和特徵重要性 TOP15 有何不同？**

**答案**: 這是個非常好的問題！讓我用對比表和實際案例說明差異。

---

### 📊 Part 1: 三種方法的核心差異

| 項目 | 特徵重要性 (Gain) | 決策規則 TOP10 | SHAP 分析 |
|-----|-----------------|---------------|----------|
| **已實作** | ✅ [xgboost_analyzer.py](xgboost_analyzer.py#L203-L243) | ✅ [decision_rule_extractor.py](decision_rule_extractor.py) | ❌ 未實作 |
| **計算來源** | XGBoost 內部統計 | 決策樹路徑提取 | 博弈論 Shapley Value |
| **提供資訊** | 「哪個特徵重要」 | 「什麼條件觸發」 | 「特徵如何影響預測」 |
| **正負方向** | ❌ 不知道 | ⚠️ 部分顯示 | ✅ 明確顯示 |
| **交互作用** | ❌ 無法檢測 | ⚠️  limited | ✅ 完整支援 |
| **單一案例解釋** | ❌ 只有全局 | ⚠️ 難以追溯 | ✅ 完整支援 |

---

### 🔍 Part 2: 實際案例對比

**情境**: 預測某個交易案例是否盈利

#### **方法 1: 特徵重要性 (系統現有)**
```python
# 參考 xgboost_analyzer.py:calculate_feature_importance()
importances = [
    {'feature': 'RSI', 'importance': 0.35, 'rank': 1},
    {'feature': 'Volume_change', 'importance': 0.22, 'rank': 2},
    {'feature': 'Taker_ratio', 'importance': 0.18, 'rank': 3},
    {'feature': 'EMA_diff', 'importance': 0.15, 'rank': 4},
    ...
]

# 你知道的資訊:
print("RSI 最重要 (35%)，Volume 次之 (22%)")

# 你不知道的資訊:
# ❌ RSI 高還是低時會盈利？
# ❌ RSI 與 Volume 如何互動？
# ❌ 為什麼這個特定案例被預測盈利？
```

#### **方法 2: 決策規則 (系統現有)**
```python
# 參考 decision_rule_extractor.py
rules = [
    {
        'condition': 'RSI <= 35.5 AND Volume_change > 1.8',
        'support': 145,
        'confidence': 0.72,
        'outcome_distribution': {'profit': 104, 'loss': 41}
    },
    {
        'condition': 'Taker_ratio > 0.65 AND EMA_diff > 0.02',
        'support': 98,
        'confidence': 0.68,
        ...
    }
]

# 你知道的資訊:
print("當 RSI 低於 35.5 且成交量放大 > 1.8 倍時，72% 機率盈利")

# 你不知道的資訊:
# ⚠️ 這個規則對最終預測貢獻多少？
# ⚠️ RSI 從 35.5 變成 30 時，預測結果變化多少？
# ❌ 如果違反這個規則，預測會變成什麼？
```

#### **方法 3: SHAP 分析 (建議新增)**
```python
import shap

# 針對單一案例的 SHAP 值
case_features = {
    'RSI': 28.5,           # SHAP value: +0.15 🟢 (往盈利方向推)
    'Volume_change': 2.3,  # SHAP value: +0.08 🟢 (往盈利方向推)
    'Taker_ratio': 0.52,   # SHAP value: -0.03 🔴 (往虧損方向推)
    'EMA_diff': 0.015,     # SHAP value: +0.02 🟢
    ...
}

base_value = 0.50  # 基礎預測 (沒特徵時的平均機率)
final_prediction = 0.50 + 0.15 + 0.08 - 0.03 + 0.02 + ... = 0.72

# 你知道的資訊:
print("""
這個案例預測盈利機率 72%：
  ✅ RSI=28.5 (超賣) 貢獻 +15% (最大正面因素)
  ✅ 成交量放大 2.3 倍 貢獻 +8%
  ❌ Taker 比例 52% 太低，減少 -3% (唯一負面因素)
  ✅ EMA 差距正向 貢獻 +2%
  
結論：雖然 Taker 比例偏低，但 RSI 超賣 + 成交量異常放大
      是強烈的盈利信號，建議進場。
""")

# SHAP 還能告訴你:
# ✅ 如果 RSI 從 28.5 升到 40，預測會降到 57%
# ✅ RSI 與 Volume 有協同效應 (交互作用)
# ✅ 全局來看，RSI < 30 平均貢獻 +12%
```

---

### 📖 Part 3: 更深入的對比

**案例: 兩個模型都說 "RSI 重要"**

```python
# 模型 A 的分析
特徵重要性: RSI 排名第 1 (35%)
決策規則: RSI <= 35.5 → 盈利機率 72%

# 模型 B 的分析  
特徵重要性: RSI 排名第 1 (35%)  # 看起來一樣
決策規則: RSI >= 65.5 → 盈利機率 68%  # 完全相反！

# 問題：
# 只看特徵重要性，你無法區分 A 和 B
# 決策規則可以區分，但不知道「為什麼」

# SHAP 能完整解釋：
SHAP 分析:
  模型 A: RSI 低 → SHAP +0.15 (做多超賣反彈)
  模型 B: RSI 高 → SHAP +0.12 (做多趨勢延續)
  
  還能顯示 RSI 與其他指標的交互作用：
  - 模型 A: RSI 低 + Volume 大 → 額外 +0.05
  - 模型 B: RSI 高 + Momentum 正 → 額外 +0.08
```

---

### 💻 Part 4: 系統實作建議

**在 XGBoostAnalyzer 中新增 SHAP 分析**:
```python
# momentum/Analysis/xgboost_analyzer.py

import shap

class XGBoostAnalyzer:
    # ... 現有程式碼 ...
    
    def analyze_shap(
        self,
        X: pd.DataFrame,
        sample_size: int = 100
    ) -> Dict[str, Any]:
        """
        SHAP 特徵影響分析
        
        Returns:
            {
                'shap_values': np.ndarray,  # (n_samples, n_features)
                'expected_value': float,
                'feature_importance_shap': List[Dict],  # 基於 |SHAP| 平均值
                'top_positive_features': List[str],  # 正向影響 TOP 5
                'top_negative_features': List[str],  # 負向影響 TOP 5
            }
        """
        if self.model is None:
            raise ValueError("模型尚未訓練")
        
        # 建立 SHAP Explainer
        explainer = shap.TreeExplainer(self.model)
        
        # 計算 SHAP 值 (可選擇子集以加速)
        if len(X) > sample_size:
            X_sample = X.sample(sample_size, random_state=42)
        else:
            X_sample = X
        
        shap_values = explainer.shap_values(X_sample)
        expected_value = explainer.expected_value
        
        # 計算特徵重要性 (基於 |SHAP| 平均值)
        shap_importance = np.abs(shap_values).mean(axis=0)
        feature_imp_shap = [
            {
                'feature': feat,
                'importance': float(imp),
                'mean_shap': float(shap_values[:, i].mean()),  # 平均方向
                'rank': rank + 1
            }
            for rank, (feat, imp, i) in enumerate(
                sorted(
                    zip(X.columns, shap_importance, range(len(X.columns))),
                    key=lambda x: x[1],
                    reverse=True
                )
            )
        ]
        
        # 找出正向和負向影響最大的特徵
        mean_shap = shap_values.mean(axis=0)
        top_positive = sorted(
            zip(X.columns, mean_shap),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        top_negative = sorted(
            zip(X.columns, mean_shap),
            key=lambda x: x[1]
        )[:5]
        
        self.logger.info("\nSHAP 分析完成:")
        self.logger.info(f"  Expected Value (基礎預測): {expected_value:.4f}")
        self.logger.info("\n正向影響 TOP 5:")
        for feat, val in top_positive:
            self.logger.info(f"  ✅ {feat}: +{val:.4f}")
        self.logger.info("\n負向影響 TOP 5:")
        for feat, val in top_negative:
            self.logger.info(f"  ❌ {feat}: {val:.4f}")
        
        return {
            'shap_values': shap_values,
            'expected_value': float(expected_value),
            'feature_importance_shap': feature_imp_shap,
            'top_positive_features': [f[0] for f in top_positive],
            'top_negative_features': [f[0] for f in top_negative]
        }
    
    def explain_single_prediction(
        self,
        case_features: pd.Series
    ) -> Dict[str, Any]:
        """
        解釋單一案例的預測結果
        
        Args:
            case_features: 單一案例的特徵值 (Series)
        
        Returns:
            詳細的預測解釋
        """
        if self.model is None:
            raise ValueError("模型尚未訓練")
        
        # 預測機率
        pred_proba = self.model.predict_proba(
            case_features.values.reshape(1, -1)
        )[0, 1]
        
        # 計算 SHAP
        explainer = shap.TreeExplainer(self.model)
        shap_values = explainer.shap_values(
            case_features.values.reshape(1, -1)
        )[0]
        expected_value = explainer.expected_value
        
        # 排序貢獻
        contributions = sorted(
            zip(case_features.index, case_features.values, shap_values),
            key=lambda x: abs(x[2]),
            reverse=True
        )
        
        self.logger.info(f"\n單一案例預測解釋:")
        self.logger.info(f"  預測盈利機率: {pred_proba:.2%}")
        self.logger.info(f"  基礎預測 (Expected Value): {expected_value:.2%}")
        self.logger.info(f"\nTOP 10 特徵貢獻:")
        
        for feat, val, shap_val in contributions[:10]:
            direction = "✅" if shap_val > 0 else "❌"
            self.logger.info(
                f"  {direction} {feat} = {val:.4f} → "
                f"貢獻 {shap_val:+.4f} ({shap_val/expected_value*100:+.1f}%)"
            )
        
        return {
            'predicted_probability': float(pred_proba),
            'expected_value': float(expected_value),
            'contributions': [
                {
                    'feature': feat,
                    'value': float(val),
                    'shap_value': float(shap_val),
                    'contribution_pct': float(shap_val / expected_value * 100)
                }
                for feat, val, shap_val in contributions
            ]
        }
```

**安裝依賴**:
```bash
pip install shap
```

---

### 🎯 Part 5: 何時用哪個工具？

```python
# 使用決策樹
快速了解模型 → 特徵重要性 (現有)
  ↓
發現可交易規則 → 決策規則 TOP10 (現有)
  ↓
深入理解邏輯 → SHAP 分析 (建議新增)
  ↓
檢驗單一案例 → SHAP 單一預測解釋 (建議新增)
```

| 場景 | 推薦工具 | 原因 |
|-----|---------|------|
| 快速篩選特徵 | 特徵重要性 | 速度快，全局概覽 |
| 建立交易規則 | 決策規則 | 可直接轉換成策略 |
| 理解模型邏輯 | SHAP | 完整的因果解釋 |
| Debug 錯誤預測 | SHAP 單一案例 | 追溯每個特徵貢獻 |
| 發論文或報告 | SHAP | 學術界標準 |

---

### 📋 總結

**現有工具的價值**:
✅ 特徵重要性 → 快速篩選
✅ 決策規則 → 可執行的交易策略

**SHAP 的獨特價值**:
✅ 告訴你「為什麼」不只是「什麼」
✅ 顯示正負方向 (做多 vs 做空)
✅ 檢測特徵交互作用 (RSI + Volume 協同效應)
✅ 解釋單一案例 (為什麼這筆交易被預測盈利)
✅ 更可信 (博弈論基礎，學術界標準)

**建議**:
- 保留現有的特徵重要性和決策規則 (實用且快速)
- 新增 SHAP 分析 (深度理解和驗證)
- 三者結合使用，互補長短

---

**Q2: 模型 A: RSI 低 → SHAP +0.15 (做多超賣反彈)，其中"做多超賣反彈"是系統自己判斷寫出?**

**答案**: 不是！這是我在範例中「人工解讀」的註解，系統本身**不會輸出**這種文字描述。讓我澄清 SHAP 的實際輸出。

#### 🤖 SHAP 的實際輸出（機器產生）

**系統真正會輸出的內容**：
```json
{
  "feature": "RSI",
  "value": 28.5,
  "shap_value": +0.15,
  "contribution_pct": +30%
}
```

就這樣！**沒有任何文字描述。**

#### 🧠 "做多超賣反彈" 是人工解讀

**這是分析師的工作**（不是系統）：
```
SHAP 輸出:
  RSI = 28.5 → SHAP value = +0.15

人類解讀:
1. RSI = 28.5 → 屬於超賣區域（< 30）
2. SHAP = +0.15 (正值) → 增加盈利機率
3. 推論 → 超賣後容易反彈
4. 策略方向 → 做多（買入）
5. 總結註解 → "做多超賣反彈"
```

#### 📊 系統輸出 vs 人工解讀的對比

**範例 1: RSI 特徵**

| 層級 | 內容 | 來源 |
|-----|------|------|
| **SHAP 原始輸出** | `{"feature": "RSI", "value": 28.5, "shap_value": +0.15}` | 🤖 系統自動 |
| **基礎解讀** | "RSI=28.5 對預測貢獻 +0.15" | 🤖 系統可生成 |
| **技術解讀** | "RSI 處於超賣區（< 30）" | 👤 需要人工或規則 |
| **策略解讀** | "做多超賣反彈" | 👤 完全人工 |

**範例 2: 成交量特徵**

| 層級 | 內容 | 來源 |
|-----|------|------|
| **SHAP 輸出** | `{"feature": "Volume_change", "value": 2.3, "shap_value": +0.08}` | 🤖 系統 |
| **基礎解讀** | "成交量變化=2.3倍，貢獻 +0.08" | 🤖 系統 |
| **技術解讀** | "成交量異常放大（> 2倍）" | 👤 人工 |
| **策略解讀" | "放量確認突破" | 👤 人工 |

#### 🔧 系統可以做的自動化程度

**Level 1: 數值報告（當前可實作）**
```json
{
  "case_id": "BTC_2024-01-15",
  "predicted_probability": 0.72,
  "shap_contributions": [
    {
      "feature": "RSI",
      "value": 28.5,
      "shap_value": +0.15,
      "rank": 1
    },
    {
      "feature": "Volume_change",
      "value": 2.3,
      "shap_value": +0.08,
      "rank": 2
    }
  ]
}
```

**Level 2: 加上方向標記（可實作）**
```json
{
  "feature": "RSI",
  "value": 28.5,
  "shap_value": +0.15,
  "direction": "positive",  // ← 系統可自動標記正負
  "impact_level": "high"    // ← 系統可根據絕對值標記
}
```

**Level 3: 簡單的文字模板（可實作，但有限）**
```python
# 系統可以用規則生成基礎描述
if shap_value > 0:
    template = f"{feature} = {value} 增加盈利機率 {abs(shap_value)*100:.1f}%"
else:
    template = f"{feature} = {value} 降低盈利機率 {abs(shap_value)*100:.1f}%"

# 輸出: "RSI = 28.5 增加盈利機率 15.0%"
```

**Level 4: 技術術語解釋（需要規則庫）**
```python
# 需要預先定義的規則庫
rule_library = {
    "RSI": {
        "< 30": "超賣區域",
        "> 70": "超買區域",
        "30-70": "正常區域"
    },
    "Volume_change": {
        "> 2.0": "成交量異常放大",
        "1.2-2.0": "成交量溫和放大",
        "< 0.8": "成交量萎縮"
    }
}

# 系統可以查表生成:
"RSI = 28.5 (超賣區域) 貢獻 +15%"
```

**Level 5: 策略解讀（需要 AI 或複雜規則）**
```
"做多超賣反彈"、"趨勢追蹤"、"反轉訊號"等
→ 這需要:
  1. 理解多個特徵的組合含義
  2. 了解交易策略的專業術語
  3. 可能需要 LLM（如 GPT）輔助生成
```

#### 🎯 實際應用場景

**場景 1: 開發者/分析師使用（當前適用）**
```
系統輸出:
  RSI = 28.5, SHAP = +0.15
  Volume_change = 2.3, SHAP = +0.08

分析師解讀:
  "這是一個超賣反彈訊號，RSI 超賣且成交量放大確認"

寫成報告或註解
```

**場景 2: 自動化交易系統（只需數值）**
```
系統判斷:
  if predicted_proba > 0.7:
      execute_trade()

不需要文字描述，只需要機率閾值
```

**場景 3: 給客戶的報告（需要文字）**
```
理想輸出:
  "根據分析，該標的出現超賣反彈訊號（RSI=28.5），
   結合成交量異常放大（2.3倍），預測上漲機率 72%"

→ 這需要額外的「報告生成模組」
→ 可以用模板 + 規則庫實作
→ 或者用 GPT API 生成自然語言報告
```

#### 💡 改進建議（從易到難）

**階段 1: 當前立即可做**
- ✅ 輸出 SHAP 數值（feature, value, shap_value）
- ✅ 標記正負方向 (positive/negative)
- ✅ 排序（按 |shap_value| 大小）

**階段 2: 簡單文字模板**
- 🔸 "RSI=28.5 貢獻 +15%"（自動生成）
- 🔸 標記影響程度（high/medium/low）
- 🔸 前端顯示時用顏色區分（綠=正向，紅=負向）

**階段 3: 技術術語庫**
- 🔸 建立規則庫（RSI < 30 = "超賣"）
- 🔸 自動添加技術註解
- 🔸 "RSI=28.5 (超賣) +15%"

**階段 4: 策略級描述**
- 🔹 整合多個特徵的解釋
- 🔹 "超賣反彈訊號（RSI 超賣 + 放量）"
- 🔹 可能需要 AI 輔助（如 GPT API）

#### ✅ 總結

**系統自動輸出**：
- ✅ 特徵名稱（如 "RSI"）
- ✅ 特徵值（如 28.5）
- ✅ SHAP 值（如 +0.15）
- ✅ 排序和正負方向

**需要人工解讀（或額外開發）**：
- ❌ "超賣"、"超買" 等技術術語
- ❌ "做多"、"做空" 等交易方向
- ❌ "反彈"、"突破" 等策略描述
- ❌ 完整的交易建議

**我在範例中的註解**（如 "做多超賣反彈"）：
- 👤 純粹是為了幫助理解而添加的「人工註解」
- 👤 系統本身不會生成這種描述
- 👤 如果需要，可以：
  - 方案 1: 建立規則庫（工程量大）
  - 方案 2: 整合 GPT API（成本高但效果好）
  - 方案 3: 人工事後添加註解（最實際）

**關鍵提醒**：不要期待系統自動產生「做多超賣反彈」這種策略級描述，這需要額外的開發工作或 AI 輔助。目前系統能提供的是「數值依據」，策略解讀還是需要專業人員。

---

### 7. **Purged K-Fold / Embargo（去汙染交叉驗證）**

#### 📖 是什麼：
防止「未來資訊洩漏到過去」。

#### 🎯 比喻：
你在準備歷史考試：
- **不正確**：用 2025 年的資料來「複習」2024 年的事件（作弊！）
- **正確**：訓練時只能用 2024 年以前的資料，測試用 2025 年的

#### ❌ 現狀問題：
目前的時間序列切分可能讓「訓練集的未來資訊污染驗證集」。

#### 💡 為什麼重要：
假設你計算「未來 5 天漲跌」作為標籤：
- 如果不加 Embargo，訓練集最後一天的標籤會用到「驗證集前 5 天」的資料
- 模型會「偷看答案」，導致過度自信

#### 📊 實際影響：
模型在測試時 AUC 0.85，但實際交易只有 0.55 → 因為訓練時「作弊」了，真實世界沒有未來資訊可偷看。

#### ❓ 常見問題

**Q: 我忘記時間序列切分的意思。這不能我拿正反案例 2021-2024 做訓練，2025 去跑回測，這樣還需要 Purged K-Fold / Embargo 嗎？**

**答案**: 你說的方案可以避免大部分問題，但在 **CV (交叉驗證)** 階段仍然可能有資訊洩漏。讓我詳細解釋。

---

### 📅 Part 1: 時間序列切分 vs 隨機切分

**隨機切分 (系統目前支援)**:
```python
# sklearn.model_selection.StratifiedKFold (shuffle=True)
全部數據: [2021案例, 2022案例, 2023案例, 2024案例]
隨機打亂後分成 5 fold:

Fold 1: Train [2022, 2021, 2024, 2023, ...] | Val [2021, 2023, ...]
Fold 2: Train [2023, 2024, 2021, 2022, ...] | Val [2022, 2024, ...]
...
```

問題: **訓練集可能包含驗證集「未來」的資訊**

**時間序列切分 (系統已實作)**:
```python
# sklearn.model_selection.TimeSeriesSplit
按時間順序切分:

Fold 1: Train [2021-01 ~ 2022-12] | Val [2023-01 ~ 2023-04]
Fold 2: Train [2021-01 ~ 2023-04] | Val [2023-05 ~ 2023-08]
Fold 3: Train [2021-01 ~ 2023-08] | Val [2023-09 ~ 2023-12]
Fold 4: Train [2021-01 ~ 2023-12] | Val [2024-01 ~ 2024-04]
Fold 5: Train [2021-01 ~ 2024-04] | Val [2024-05 ~ 2024-08]
```

系統實作參考: [xgboost_analyzer.py:305-323](xgboost_analyzer.py#L305-L323)
```python
if time_series_split:
    from sklearn.model_selection import TimeSeriesSplit
    splitter = TimeSeriesSplit(n_splits=cv_folds)
    split_iter = splitter.split(X_ordered)
else:
    skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
    split_iter = skf.split(X_ordered, y_ordered)
```

---

### ⚠️ Part 2: 為什麼還需要 Purged K-Fold?

**問題核心: 標籤計算時的未來資訊洩漏**

假設你的標籤是「未來 5 天漲跌」:
```python
# 標籤計算範例
for i in range(len(df)):
    trigger_time = df.iloc[i]['time']  # 2024-01-15 12:00
    
    # ❌ 錯誤: 標籤用到未來 5 天的資訊
    future_5d = df.iloc[i:i+10]  # 2024-01-15 ~ 2024-01-20
    label = 1 if future_5d['close'].iloc[-1] > future_5d['close'].iloc[0] else 0
```

**洩漏發生位置**:
```
時間軸:
────────────────────────────────────────────────────────
案例 1: 2024-01-10  ┐
案例 2: 2024-01-11  │ 訓練集
案例 3: 2024-01-12  ┘
                     ← Embargo Zone (需要空出)
案例 4: 2024-01-15  ┐ 驗證集
案例 5: 2024-01-16  ┘

問題:
  案例 3 的標籤用到 2024-01-17 的數據
  案例 4 的標籤用到 2024-01-20 的數據
  → 案例 3 和案例 4 共享了 2024-01-17~20 的資訊！
```

---

### 🛡️ Part 3: Purged K-Fold 解決方案

**兩個關鍵機制**:

#### **1. Purging (去汙染)**
從訓練集中移除「標籤會洩漏到驗證集」的樣本

```python
def purge_train_test_split(
    X: pd.DataFrame,
    y: pd.Series,
    test_start_idx: int,
    label_window: int = 5  # 標籤用到未來 5 天
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Purge 訓練集：移除會洩漏到測試集的樣本
    """
    # 訓練集只取到 test_start_idx - label_window
    purged_train_end = test_start_idx - label_window
    
    X_train = X.iloc[:purged_train_end]
    y_train = y.iloc[:purged_train_end]
    
    X_test = X.iloc[test_start_idx:]
    y_test = y.iloc[test_start_idx:]
    
    return X_train, y_train, X_test, y_test
```

**視覺化**:
```
原本:
Train: [案例1, 案例2, 案例3]  | Test: [案例4, 案例5]
                    ↑ 洩漏區
                    
使用 Purge:
Train: [案例1, 案例2]  | [案例3] REMOVED | Test: [案例4, 案例5]
```

#### **2. Embargo (禁運期)**
驗證集開始前空出一段時間

```python
def embargo_train_test_split(
    X: pd.DataFrame,
    y: pd.Series,
    test_start_idx: int,
    embargo_pct: float = 0.01  # 空出 1% 的時間
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Embargo: 在訓練/驗證之間空出緩衝區
    """
    embargo_size = int(len(X) * embargo_pct)
    
    # 訓練集結束於 test_start - embargo
    X_train = X.iloc[:test_start_idx - embargo_size]
    y_train = y.iloc[:test_start_idx - embargo_size]
    
    # 測試集從原位置開始
    X_test = X.iloc[test_start_idx:]
    y_test = y.iloc[test_start_idx:]
    
    return X_train, y_train, X_test, y_test
```

---

### 🔄 Part 4: 你的方案分析

**你的方案**: 2021-2024 訓練 → 2025 回測

✅ **優點**:
- 完全避免了「訓練-測試」之間的洩漏
- 這是標準的 OOT (Out-of-Time) 驗證
- 回測階段不會有洩漏問題

⚠️ **Still 需要注意**:
- **CV 階段** (2021-2024 內部) 仍可能洩漏
- 如果標籤用到「未來 N 天」,需要 Purge

**完整流程建議**:
```python
# Step 1: 訓練階段 (2021-2024)
X_train_full = load_data("2021-01-01", "2024-12-31")

# 使用 Time Series Split + Purge/Embargo 做 CV
performance = train_with_purged_cv(
    X_train_full, y_train_full,
    cv_folds=5,
    use_time_series_split=True,
    purge=True,  # 啟用 Purge
    embargo_pct=0.01  # 每個 fold 之間空出 1%
)

# Step 2: 最終訓練 (用全部 2021-2024 數據)
final_model.fit(X_train_full, y_train_full)

# Step 3: OOT 驗證 (2025)
X_oot = load_data("2025-01-01", "2025-12-31")
oot_auc = final_model.score(X_oot, y_oot)

# Step 4: 回測 (2025) - 不會有洩漏問題
backtest_results = run_backtest(final_model, "2025-01-01", "2025-12-31")
```

---

### 💻 Part 5: 系統實作建議

**在 xgboost_analyzer.py 中擴展**:
```python
# momentum/Analysis/xgboost_analyzer.py

from sklearn.model_selection import TimeSeriesSplit
import numpy as np

class XGBoostAnalyzer:
    # ... 現有程式碼 ...
    
    def train_with_purged_cv(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
        cv_folds: int = 5,
        label_window: int = 5,  # 標籤用到未來幾根 K 線
        embargo_pct: float = 0.01,
        **kwargs
    ) -> ModelPerformance:
        """
        使用 Purged K-Fold 交叉驗證訓練
        
        Args:
            label_window: 標籤計算時用到的未來 K 線數量
            embargo_pct: Embargo 比例 (建議 0.01~0.05)
        """
        self.logger.info(
            f"啟用 Purged CV - Label Window: {label_window}, "
            f"Embargo: {embargo_pct*100:.1f}%"
        )
        
        tscv = TimeSeriesSplit(n_splits=cv_folds)
        cv_scores = []
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            # Purge: 移除訓練集末端可能洩漏的樣本
            purge_size = label_window
            train_idx = train_idx[:-purge_size] if len(train_idx) > purge_size else train_idx
            
            # Embargo: 驗證集開始前空出緩衝區
            embargo_size = max(1, int(len(val_idx) * embargo_pct))
            val_idx = val_idx[embargo_size:]
            
            if len(train_idx) == 0 or len(val_idx) == 0:
                self.logger.warning(f"Fold {fold+1}: 數據不足,跳過")
                continue
            
            # 訓練該 fold
            X_train_fold = X.iloc[train_idx]
            y_train_fold = y[train_idx]
            X_val_fold = X.iloc[val_idx]
            y_val_fold = y[val_idx]
            
            model_fold = xgb.XGBClassifier(**self.params)
            model_fold.fit(X_train_fold, y_train_fold, verbose=False)
            
            # 評估
            y_pred_proba = model_fold.predict_proba(X_val_fold)[:, 1]
            auc = roc_auc_score(y_val_fold, y_pred_proba)
            cv_scores.append(auc)
            
            self.logger.info(
                f"Fold {fold+1}/{cv_folds} - "
                f"Train: {len(train_idx)}, Val: {len(val_idx)}, AUC: {auc:.4f}"
            )
        
        # 計算平均性能
        cv_auc_mean = np.mean(cv_scores)
        cv_auc_std = np.std(cv_scores)
        
        self.logger.info(
            f"\nPurged CV 完成 - CV AUC: {cv_auc_mean:.4f} ± {cv_auc_std:.4f}"
        )
        
        # 最終用全部數據訓練
        self.model = xgb.XGBClassifier(**self.params)
        self.model.fit(X, y, verbose=False)
        
        return ModelPerformance(
            train_auc=roc_auc_score(y, self.model.predict_proba(X)[:, 1]),
            cv_auc_mean=cv_auc_mean,
            cv_auc_std=cv_auc_std,
            precision=0.0,  # 可補充
            recall=0.0,
            f1_score=0.0,
            overfitting_score=0.0
        )
```

---

### 📋 總結

| 場景 | 是否需要 Purged K-Fold? |
|-----|------------------------|
| **你的方案** (2021-2024 訓練 → 2025 測試) | ✅ CV 階段需要 (2021-2024 內部) |
| 標籤不用未來資訊 (如當日收盤價) | ❌ 不需要 |
| 標籤用未來 N 天資訊 | ✅ 必須使用 |
| 只做 OOT 驗證,不做 CV | ❌ 不需要 |

**關鍵結論**:
- 你的大方向 (2021-2024 → 2025) 是對的 ✅
- 但 **CV 階段** (2021-2024 內部驗證) 仍需要 Purged K-Fold
- 系統目前已支援 `time_series_split=True`,建議擴展支援 Purge/Embargo
- 參考: [Advances in Financial Machine Learning (de Prado)](https://www.amazon.com/Advances-Financial-Machine-Learning-Marcos/dp/1119482089) Chapter 7

---

## 🟡 中優先級缺失項目

### 1. **跨幣種泛化驗證 (Cross-Symbol Validation)**

#### 📖 是什麼：
用「比特幣」訓練的模型，拿去預測「以太坊」是否有效。

#### ❌ 現狀問題：
目前可以多幣種合併訓練，但沒有檢查「專屬模型」的跨幣種能力。

#### 💡 為什麼重要：
- 如果模型只對比特幣有效，代表它學到的是「比特幣特有的雜訊」
- 好的模型應該抓到「加密貨幣的共通規律」

#### 📊 實際影響：
就像中醫只會治台灣人的病，到了日本就不靈了 → 代表可能不是真正的「醫術」，只是「巧合」。

#### ❓ 常見問題

**Q: 跨幣種泛化驗證這部分是會如何去做驗證？現在是跨幣種，未來會是股票 ticker 和代號也是一樣的道理？**

<答案待補充>

---

### 2. **Permutation Importance（置換重要性）**

#### 📖 是什麼：
測試「如果把這個特徵打亂，模型表現會下降多少」。

#### 🎯 比喻：
你做蛋糕時：
- 把糖打亂順序 → 蛋糕變難吃（糖很重要）
- 把裝飾打亂 → 蛋糕味道沒變（裝飾不重要）

#### ❌ 現狀問題：
目前只看模型「內部認為」的重要性（Gain），但沒驗證「實際上」是否真的重要。

#### 💡 為什麼重要：
- 有時模型覺得某特徵重要，只是因為「訓練時的巧合」
- Permutation Importance 能揭露「真正有用的特徵」

#### 📊 實際影響：
模型說 RSI 重要性 30%，但置換測試後發現「拿掉 RSI，AUC 只下降 0.01」→ 其實 RSI 是冗餘的。

---

### 3. **特徵重要性時間衰減 (Feature Importance Decay)**

#### 📖 是什麼：
追蹤「某個指標的預測力是否隨時間減弱」。

#### 🎯 比喻：
- 2020 年「口罩概念股」很靈驗
- 2024 年完全失效
→ 這個特徵「過期」了

#### ❌ 現狀問題：
目前只看「現在」哪些特徵重要，不知道它們會不會「退流行」。

#### 💡 為什麼重要：
- 市場會演化，舊訊號會失效
- 提前偵測「特徵衰退」能避免虧損

#### 📊 實際影響：
2021 年「MACD 金叉」很準（重要性 40%），2024 年降到 10% → 該停用這策略了。

---

### 4. **Fold-level Importance（每折的重要性穩定性）**

#### 📖 是什麼：
檢查「不同數據切塊時，特徵重要性是否一致」。

#### 🎯 比喻：
你問 5 個人「最重要的烹飪技巧」：
- **穩定**：4 人說火候，1 人說調味 → 火候確實重要
- **不穩定**：每個人答案都不同 → 可能沒有共識

#### ❌ 現狀問題：
目前只看「最終模型」的重要性，不知道是否穩定。

#### 💡 為什麼重要：
- 如果重要性在不同 fold 差很多，代表是「雜訊」不是「訊號」
- 穩定的特徵才值得信賴

#### 📊 實際影響：
模型說 EMA 重要性 50%，但在 5 次交叉驗證中，變異從 10% 到 80% → 其實不可靠。

---

### 5. **Precision@K（前 K% 精準度）**

#### 📖 是什麼：
只看「最有把握的前 10% 訊號」的準確率。

#### 🎯 比喻：
你是投資顧問，只向客戶推薦「最確定會賺的 10 支股票」，而不是全部 100 支。

#### ❌ 現狀問題：
目前看整體準確率，但實際交易時你只會選「最強訊號」。

#### 💡 為什麼重要：
- 整體準確率 65% 聽起來不錯，但前 10% 可能只有 55%（還不如猜）
- 或反過來：整體 60%，但前 10% 有 85%（這才是寶藏）

#### 📊 實際影響：
兩個模型整體 AUC 都是 0.70，但：
- 模型 A：Precision@10% = 0.45（前 10% 訊號很爛）
- 模型 B：Precision@10% = 0.85（前 10% 訊號超強）
→ 實戰應該選 B，因為你只會用最強訊號。

#### ❓ 常見問題

**Q: Precision@K 的前 K%，K 是怎麼根據什麼數據得出來的？**

**答案**: K 值通常根據**實際交易能力**和**風險偏好**來決定，而非固定數值。

#### 🎯 K 值選擇依據

```python
# K 值選擇考量因素

1. 資金規模限制
   如果你每天只能交易 5 次 → K = 5/(總訊號數) × 100%
   
   範例:
   - 每天產生 100 個訊號
   - 只能執行 5 筆交易
   → K = 5%

2. 風險承受度
   保守型: K = 1~5% (只做最有把握的)
   平衡型: K = 5~10%
   積極型: K = 10~20%

3. 勝率目標
   目標勝率 80% → 設定 K 讓 Precision@K ≈ 0.80
```

#### 🔢 實際計算方式

```python
def select_optimal_k(y_true, y_pred_proba, target_precision=0.80):
    """
    根據目標精準度選擇最佳 K
    
    Args:
        y_true: 實際標籤
        y_pred_proba: 預測機率
        target_precision: 目標精準度
    
    Returns:
        optimal_k: 最佳的 K 值 (百分比)
    """
    # 按預測機率降序排列
    sorted_indices = np.argsort(y_pred_proba)[::-1]
    y_sorted = y_true[sorted_indices]
    
    # 嘗試不同的 K 值
    for k_pct in range(1, 51):  # 1% ~ 50%
        k_samples = int(len(y_true) * k_pct / 100)
        if k_samples == 0:
            continue
        
        # 計算前 K% 的精準度
        precision_at_k = y_sorted[:k_samples].sum() / k_samples
        
        if precision_at_k >= target_precision:
            return k_pct
    
    return None  # 無法達到目標精準度

# 使用範例
optimal_k = select_optimal_k(y_test, y_pred_proba, target_precision=0.75)
print(f"建議 K = {optimal_k}%")  # 例如: K = 8%
```

#### 📊 常用 K 值及含義

| K 值 | 含義 | 適用場景 |
|-----|------|---------|
| 1% | 極度保守 | 只做"必勝"訊號,小資金 |
| 5% | 保守型 | 一般量化策略推薦值 |
| 10% | 平衡型 | 兼顧訊號數量和品質 |
| 20% | 積極型 | 高頻交易,大資金 |
| 50% | 基準線 | 用於比較整體模型表現 |

#### 🎯 系統實作建議

```python
# 在 XGBoostAnalyzer 中新增
def calculate_precision_at_k(
    self,
    X: pd.DataFrame,
    y: np.ndarray,
    k_values: List[int] = [1, 5, 10, 20]
) -> Dict[int, float]:
    """
    計算不同 K 值的精準度
    
    Returns:
        {1: 0.85, 5: 0.78, 10: 0.72, 20: 0.65}
    """
    y_pred_proba = self.model.predict_proba(X)[:, 1]
    sorted_indices = np.argsort(y_pred_proba)[::-1]
    y_sorted = y[sorted_indices]
    
    results = {}
    for k in k_values:
        k_samples = max(1, int(len(y) * k / 100))
        precision = y_sorted[:k_samples].sum() / k_samples
        results[k] = float(precision)
        
        self.logger.info(f"Precision@{k}%: {precision:.4f}")
    
    return results
```

**總結**: K 值沒有標準答案,依實際交易能力和風險偏好調整。建議從 K=5% 開始測試。

---

**Q2: 建立系統持續監測，時間一直推進，這樣哪有辦法比較各標的的機率，然後才進行交易?**

**答案**: 這是個非常實際的問題！在持續監測的情況下，Precision@K 的應用方式確實需要調整。讓我說明實戰中的做法。

#### 🔄 問題的核心：動態環境下的 K 值應用

**你提出的實際情況**：
```
時間點 12:00:
  - BTCUSDT 預測機率: 0.75
  - ETHUSDT 預測機率: 0.68
  - SOLUSDT 預測機率: 0.82
  - BNBUSDT 預測機率: 0.44
  ... 還有 50 個標的

到了 12:05（5分鐘後）:
  - BTCUSDT 預測機率: 0.73（下降）
  - ETHUSDT 預測機率: 0.71（上升）
  - SOLUSDT 預測機率: 0.80（下降）
  - 新標的出現訊號...

→ 機率一直在變，怎麼定義「前 K%」？
```

#### ⚠️ Precision@K 在持續監測中的限制

**Precision@K 原本的設計**：
```
靜態評估場景:
1. 一次性拿到 1000 個案例
2. 模型預測出 1000 個機率
3. 排序後取前 K%（如前 50 個）
4. 計算這 50 個的精準度

→ 這是「批次評估」,適合回測和模型驗證
```

**持續監測的現實**：
```
動態交易場景:
1. 每分鐘都有新訊號產生
2. 機率隨市場變化不斷更新
3. 無法等到「所有訊號都出現」再排序
4. 需要「即時決策」而非「批次處理」

→ 傳統的 Precision@K 不適用
```

#### ✅ 實戰中的解決方案

**方案 1: 固定機率閾值（最實用）**

```
不用 K%，改用固定機率門檻:

訓練階段:
1. 模型訓練完成後,計算 Precision@K
2. 發現: Precision@10% = 0.75，對應機率約 0.70
3. 記錄這個閾值: threshold = 0.70

實盤階段:
每當新訊號出現:
  if predicted_proba > 0.70:  # 固定閾值
      execute_trade()
  else:
      ignore_signal()

→ 不需要比較所有標的，直接用閾值判斷
```

**優點**：
- ✅ 簡單直接,易於實施
- ✅ 不需要等待多個訊號
- ✅ 每個標的獨立判斷

**缺點**：
- ⚠️ 市場環境變化時,閾值可能需要調整
- ⚠️ 無法根據當前可用訊號的相對品質調整

---

**方案 2: 滑動窗口排序（資金有限時）**

```
適用場景: 你只能同時交易 5 個標的

實施方式:
1. 維護一個「候選池」（最近 1 小時內的所有訊號）
2. 每 15 分鐘重新排序一次
3. 選出機率最高的前 5 個
4. 如果新訊號機率更高,替換掉最弱的

範例:
12:00 候選池:
  SOL: 0.82 ✅
  BTC: 0.75 ✅
  ETH: 0.68 ✅
  BNB: 0.65 ✅
  ADA: 0.63 ✅
  (其他 < 0.60 忽略)

12:15 新訊號:
  MATIC: 0.78（新加入）

重新排序:
  SOL: 0.82 ✅
  MATIC: 0.78 ✅（新進）
  BTC: 0.75 ✅
  ETH: 0.68 ✅
  BNB: 0.65 ✅
  ADA: 0.63 ❌（被擠掉）
```

**優點**：
- ✅ 確保同時間只交易最強訊號
- ✅ 適合資金有限的情況

**缺點**：
- ⚠️ 實施複雜,需要維護候選池
- ⚠️ 可能錯過早期的好訊號（被後來的擠掉）

---

**方案 3: 分級交易（最專業）**

```
根據機率分級,採用不同策略:

機率分級:
  A 級 (> 0.80): 「必做」訊號
    - 立即執行
    - 可用較大倉位
    - 不與其他標的比較

  B 級 (0.70-0.80): 「優先」訊號
    - 資金允許就做
    - 若同時多個 B 級,選機率高的

  C 級 (0.60-0.70): 「候補」訊號
    - 僅在無 A/B 級訊號時考慮
    - 用最小倉位

  D 級 (< 0.60): 「忽略」
    - 不交易

實盤決策:
if 新訊號 in A級:
    立即交易（無需比較）
elif 新訊號 in B級:
    if 有閒置資金:
        交易
    else:
        與現有持倉比較，替換較弱的
elif 新訊號 in C級:
    if 沒有任何 A/B 級訊號 and 有閒置資金:
        小倉位交易
```

**優點**：
- ✅ 兼顧訊號品質和資金利用
- ✅ 有彈性,適應不同市場環境

**缺點**：
- ⚠️ 需要回測確定各級別的閾值
- ⚠️ 實施較複雜

#### 🎯 Precision@K 在持續監測中的真正用途

**用途 1: 訓練時確定閾值**
```
步驟:
1. 模型訓練完成
2. 在驗證集上計算 Precision@K（K=1%,5%,10%等）
3. 找出對應的機率閾值

結果:
Precision@5% = 0.80，對應機率閾值 = 0.75

→ 實盤時用: "機率 > 0.75 才交易"
```

**用途 2: 回測時評估策略**
```
回測一整年的數據:
1. 模型產生了 5000 個訊號
2. 計算 Precision@10%（前 500 個）
3. 評估這些訊號的品質

→ 幫助你理解模型在「最有把握」時的表現
```

**用途 3: 比較不同模型**
```
模型 A: Precision@5% = 0.85
模型 B: Precision@5% = 0.72

→ 模型 A 在「高信心訊號」上表現更好
→ 實盤優先用模型 A
```

#### 📊 實戰推薦流程

**步驟 1: 訓練階段確定閾值**
```
回測 2023-2024 年數據:
Precision@5% = 0.78，機率閾值 ≈ 0.72
Precision@10% = 0.72，機率閾值 ≈ 0.65
Precision@20% = 0.65，機率閾值 ≈ 0.58

決定策略:
- 優先級 1: 機率 > 0.72（對應 Precision@5%）
- 優先級 2: 機率 0.65-0.72
- 忽略: 機率 < 0.65
```

**步驟 2: 實盤階段應用**
```
持續監測所有標的:
for symbol in all_symbols:
    signal = get_latest_signal(symbol)
    proba = model.predict_proba(signal)
    
    if proba > 0.72:  # 對應 Precision@5%
        execute_trade(symbol, position_size="large")
    elif proba > 0.65:  # 對應 Precision@10%
        if has_available_capital():
            execute_trade(symbol, position_size="medium")
    # proba < 0.65: 忽略
```

**步驟 3: 定期重新評估**
```
每週/每月:
1. 檢查實盤訊號的機率分佈
2. 計算實際的 Precision@K
3. 如果偏差太大，調整閾值

範例:
原設定: 機率 > 0.72
實際表現: 這些訊號的勝率只有 0.65（低於預期 0.78）
調整: 提高閾值到 0.75
```

#### ✅ 總結

**Precision@K 不是用於實時比較各標的**，而是用於：

1. **訓練階段**: 確定機率閾值
   - 透過回測數據找出「前 K% 對應什麼機率」

2. **實盤階段**: 用閾值過濾訊號
   - 不用比較各標的，直接用機率閾值判斷
   - 例如: `if proba > 0.72: trade()`

3. **評估階段**: 驗證策略表現
   - 事後分析實盤訊號的品質

**實戰建議**：
- ✅ 使用「固定機率閾值」(方案 1)，最簡單有效
- ✅ 如果資金有限，用「分級交易」(方案 3)
- ❌ 不要試圖「即時排序所有標的」來決定交易，不切實際

**關鍵轉念**：Precision@K 是「回測評估工具」，不是「實時決策工具」。真正用於實盤的是「機率閾值」，而 Precision@K 幫你找到這個閾值應該設多少。

---

**Q3: Precision@K 可以根據 market phase 做 K 的分析，然後配上方案 3: 分級交易（最專業）嗎？**

**答案**: 可以，而且非常合理。實務上你會得到的是「不同 market phase 對應不同的交易門檻與倉位規則」。

#### ✅ 核心做法：分 phase 求出「門檻」而不是只求一個 K

你可以對每個 `market_phase` 分別做：
1. 計算多個 K（例如 1%、5%、10%）的 Precision@K
2. 找到該 phase 下「達到目標精準度」所需的 `predicted_proba` 閾值
3. 把這些閾值拿去做方案 3（分級交易）

#### 📌 分級交易（方案 3）與 market phase 的結合方式

範例（概念示意）：
- bull：訊號多、勝率高 → 閾值可略低、倉位可較積極
- bear：訊號少、假訊號多 → 閾值要更高、倉位更保守或只做 A 級
- sideways：視策略而定（均值回歸可能更強）

這樣就不需要在「持續監測」時做全市場即時排序，而是：
- 先知道當前 `market_phase`
- 再套用該 phase 對應的 A/B/C 閾值與倉位規則

#### ⚠️ 實務風險與保護欄

- 分 phase 後樣本變少，門檻容易不穩定 → 建議設定最小樣本數門檻與 OOT 再驗證
- 若 phase 定義會變動（例如標註方法更新），閾值要重新校準

---

### 6. **期望值 (Expectancy)**

#### 📖 是什麼：
算出「平均每次交易能賺多少錢」。

#### 🎯 公式（白話版）：
期望值 = (勝率 × 平均獲利) - (敗率 × 平均虧損)

#### 🎯 比喻：
賭場遊戲：
- 勝率 30%，贏一次得 100 元
- 敗率 70%，輸一次賠 20 元
- 期望值 = 0.3×100 - 0.7×20 = 30 - 14 = +16 元 → 長期會賺

#### ❌ 現狀問題：
目前只看「勝率」（profitable_count），但不知道「每次賺多少」。

#### 💡 為什麼重要：
- 勝率 80% 但平均賺 1 元、虧 50 元 → 其實會賠錢
- 勝率 40% 但平均賺 100 元、虧 10 元 → 其實會大賺

#### 📊 實際影響：
兩個策略：
- 策略 A：勝率 70%，但賺小賠大 → 期望值 -5
- 策略 B：勝率 45%，但賺大賠小 → 期望值 +20
→ 應該選 B！

#### ❓ 常見問題

**Q: 期望值這不是回測系統才建起來算的？**

**答案**: 是的,**真正精確的期望值需要回測系統**,但 XGBoost 階段可以做**粗略估算**。

#### 🔄 兩個階段的期望值

```
階段 1: XGBoost 訓練時 (粗略估算)
  └─ 用歷史案例的 price_change 計算
  └─ 假設: 模型預測 = 實際交易
  └─ 精度: 中等 (忽略滑點、手續費、無法交易的情況)

階段 2: 回測系統 (精確計算)
  └─ 模擬實際交易過程
  └─ 考慮: 滑點、手續費、資金管理、倉位大小
  └─ 精度: 高 (接近真實交易)
```

#### 📊 XGBoost 階段的粗略估算

```python
def estimate_expectancy_from_cases(
    cases: List[Dict],
    predicted_labels: np.ndarray,
    threshold: float = 0.5
) -> Dict[str, float]:
    """
    從案例數據粗略估算期望值
    
    Args:
        cases: 案例列表 (含 price_change 等)
        predicted_labels: 模型預測 (0/1 或機率)
        threshold: 分類閾值
    
    Returns:
        {
            'win_rate': 0.65,
            'avg_win': 0.025,  # 2.5%
            'avg_loss': -0.018,  # -1.8%
            'expectancy': 0.0036  # 0.36%
        }
    """
    # 根據閾值分類
    if predicted_labels.max() <= 1.0:
        # 機率預測
        predicted_trades = predicted_labels > threshold
    else:
        # 二分類預測
        predicted_trades = predicted_labels == 1
    
    # 只看模型建議交易的案例
    trade_cases = [c for i, c in enumerate(cases) if predicted_trades[i]]
    
    if len(trade_cases) == 0:
        return {'error': '沒有交易案例'}
    
    # 計算勝率和平均損益
    wins = [c['price_change'] for c in trade_cases if c['price_change'] > 0]
    losses = [c['price_change'] for c in trade_cases if c['price_change'] <= 0]
    
    win_rate = len(wins) / len(trade_cases)
    loss_rate = len(losses) / len(trade_cases)
    
    avg_win = np.mean(wins) if len(wins) > 0 else 0
    avg_loss = np.mean(losses) if len(losses) > 0 else 0
    
    # 期望值 = 勝率 × 平均獲利 - 敗率 × 平均虧損
    expectancy = win_rate * avg_win + loss_rate * avg_loss  # loss_rate 已是負值
    
    return {
        'win_rate': float(win_rate),
        'loss_rate': float(loss_rate),
        'avg_win': float(avg_win),
        'avg_loss': float(avg_loss),
        'expectancy': float(expectancy),
        'total_trades': len(trade_cases)
    }

# 使用範例
expectancy_stats = estimate_expectancy_from_cases(
    cases, y_pred_proba, threshold=0.7
)

print(f"期望值估算 (XGBoost 階段):")
print(f"  勝率: {expectancy_stats['win_rate']:.2%}")
print(f"  平均獲利: {expectancy_stats['avg_win']:.2%}")
print(f"  平均虧損: {expectancy_stats['avg_loss']:.2%}")
print(f"  期望值: {expectancy_stats['expectancy']:.2%}")
```

#### ⚠️ XGBoost 估算的限制

```python
# XGBoost 估算忽略了:
1. 交易成本 (手續費 + 滑點 ≈ 0.1%~0.2%)
2. 無法交易的情況 (停盤、流動性不足)
3. 倉位管理 (固定金額 vs 凱利公式)
4. 時間衰減 (訊號有效期)
5. 市場衝擊 (大單會影響價格)

# 因此 XGBoost 期望值通常會過度樂觀
實際回測期望值 ≈ XGBoost 期望值 × 0.6~0.8
```

#### 🎯 完整工作流程

```python
# Step 1: XGBoost 階段 - 粗篩策略
xgboost_expectancy = estimate_expectancy_from_cases(cases, predictions)

if xgboost_expectancy['expectancy'] < 0.005:  # < 0.5%
    print("❌ 策略期望值太低,不值得回測")
    return

# Step 2: 回測系統 - 精確驗證
from backtest_engine import BacktestEngine

backtest_results = BacktestEngine.run(
    strategy=xgboost_strategy,
    start_date="2024-01-01",
    end_date="2024-12-31",
    initial_capital=10000,
    commission=0.001,  # 0.1% 手續費
    slippage=0.0005    # 0.05% 滑點
)

real_expectancy = backtest_results['expectancy']
print(f"回測系統期望值: {real_expectancy:.2%}")

# Step 3: 比較兩者差異
expectancy_ratio = real_expectancy / xgboost_expectancy['expectancy']
print(f"實際/估算比率: {expectancy_ratio:.2f}")

if expectancy_ratio < 0.5:
    print("⚠️ 實際期望值遠低於估算,需檢討模型或增加成本考量")
```

**總結**: XGBoost 階段做粗略估算(快速篩選),回測系統做精確計算(最終驗證)。

---

### 7. **Bootstrap 信賴區間 (Statistical Confidence)**

#### 📖 是什麼：
檢查「模型的表現是真本事還是運氣好」。

#### 🎯 比喻：
投籃測試：
- 你投 10 球進 7 球（70%）
- 但如果測 100 次，可能有時 50%，有時 80%
- Bootstrap 算出「真實命中率可能在 60%-75% 之間（95% 信賴區間）」

#### ❌ 現狀問題：
目前只看「平均 AUC ± 標準差」，但不知道統計顯著性。

#### 💡 為什麼重要：
- 模型 A：AUC 0.72 ± 0.02（很穩定）
- 模型 B：AUC 0.75 ± 0.15（可能只是運氣好）
→ 應該選 A

#### 📊 實際影響：
兩個模型 AUC 都是 0.70，但：
- 模型 A：95% 信賴區間 = [0.68, 0.72]（可靠）
- 模型 B：95% 信賴區間 = [0.50, 0.90]（不可靠，可能跟猜的一樣）

---

## 🟢 低優先級缺失項目

### 1. **MLflow 整合**

#### 📖 是什麼：
專業的「實驗記錄本」，自動記錄每次訓練的參數、結果、模型。

#### ❌ 現狀問題：
目前用自己寫的檔案管理系統（像是手寫筆記本）。

#### 💡 為什麼重要：
- 自動化記錄，不會遺漏
- 可以快速比較 100 個實驗
- 業界標準工具，方便協作

#### 📊 實際影響：
像是從「手寫帳本」升級到「Excel 財務軟體」，效率大增。

---

### 2. **Weights & Biases (W&B)**

#### 📖 是什麼：
雲端版的實驗管理工具，還能監控電腦效能。

#### ❌ 現狀問題：
目前所有數據存在本機，團隊協作困難。

#### 💡 為什麼重要：
- 團隊成員在不同電腦上也能看到結果
- 自動產生漂亮的圖表報告
- 追蹤 GPU 使用率（如果用深度學習）

#### 📊 實際影響：
像是從「私人筆記本」升級到「Google Docs」，可以即時分享和協作。

---

### 3. **Streamlit Dashboard**

#### 📖 是什麼：
互動式網頁界面，可以用滑鼠點選、篩選、比較不同模型。

#### ❌ 現狀問題：
目前需要看程式碼輸出或 JSON 檔案（不友善）。

#### 💡 為什麼重要：
- 非技術人員（老闆、投資人）也能看懂
- 可以即時調整篩選條件
- 視覺化圖表更直觀

#### 📊 實際影響：
像是從「看 Excel 原始數據」升級到「Power BI 互動式報表」。

#### ❓ 常見問題

**Q: XGBOOST_MULTI_RESULT_ANALYSIS_GUIDE.md 提到分析結果視覺化，沒列在上述項目？**

<答案待補充>

---

### 4. **資料庫儲存 (PostgreSQL)**

#### 📖 是什麼：
用專業資料庫取代檔案存儲，支援複雜查詢。

#### ❌ 現狀問題：
目前用 JSON、Pickle、HDF5 檔案（像是一堆散落的文件）。

#### 💡 為什麼重要：
- 快速查詢（例如：找出所有 AUC > 0.75 且在熊市表現好的模型）
- 支援多人同時存取
- 自動備份和版本控制

#### 📊 實際影響：
像是從「堆滿文件的櫃子」升級到「圖書館管理系統」，查詢快速且不會弄丟。

---

## 📝 總結建議

### ⚡ 立即需要（高優先級）

這些關乎模型是否真的有效，缺少會導致「看起來很好實際上很爛」的風險：

1. ✅ **OOT 驗證** - 驗證模型在未來時間的真實表現
2. ✅ **市場體制分析** - 避免策略只適用特定市場環境
3. ✅ **機率校準** - 確保模型的信心指數可信
4. ✅ **PR AUC** - 類別不平衡時的真實評估
5. ✅ **PSI** - 監控特徵分佈變化
6. ✅ **SHAP 分析** - 深入理解特徵影響方向
7. ✅ **Purged K-Fold** - 防止資訊洩漏

### 🔄 逐步改進（中優先級）

這些能提升模型品質和可靠性，但不至於致命：

1. 🔵 跨幣種泛化驗證
2. 🔵 Permutation Importance
3. 🔵 特徵重要性時間衰減
4. 🔵 Fold-level Importance
5. 🔵 Precision@K
6. 🔵 期望值計算
7. 🔵 Bootstrap 信賴區間

### 🎨 錦上添花（低優先級）

這些是工具升級，讓工作更輕鬆，但不影響核心功能：

1. 🟢 MLflow 整合
2. 🟢 Weights & Biases
3. 🟢 Streamlit Dashboard
4. 🟢 資料庫儲存

---

**Q: XGBOOST_MULTI_RESULT_ANALYSIS_GUIDE.md 提到分析結果視覺化，沒列在上述項目？**

**答案**: 這是很好的觀察！讓我釐清**分析結果視覺化**與**缺失項目**的關係。

#### 🎨 視覺化的兩種層次

```
Layer 1: 基礎視覺化 (XGBOOST_MULTI_RESULT_ANALYSIS_GUIDE.md)
  ├─ 性能散點圖 (Train AUC vs CV AUC)
  ├─ 雷達圖 (多維度評分)
  ├─ 特徵重要性柱狀圖
  ├─ 熱力圖 (模型排名矩陣)
  └─ 狀態: ✅ 已有完整設計方案,待實作

Layer 2: 進階分析視覺化 (缺失項目部分)
  ├─ 校準曲線 (Calibration Curve) ❌
  ├─ PR 曲線 (Precision-Recall Curve) ❌
  ├─ SHAP 瀑布圖 (Waterfall Chart) ❌
  ├─ PSI 分佈對比圖 ❌
  └─ 市場體制表現雷達圖 ❌
```

#### ⚙️ 當前系統狀態

| 視覺化類型 | GUIDE 設計 | 實際實作 | 缺失項目關聯 |
|----------|----------|---------|------------|
| **基礎比較圖** | ✅ 有 | ⚠️ 部分 | 無 |
| 性能散點圖 | ✅ | ✅ (前端已有) | 無 |
| 雷達圖 | ✅ | ❌ | 無 |
| 熱力圖 | ✅ | ❌ | 無 |
| **進階分析圖** | ❌ 無 | ❌ 無 | ✅ 是缺失項目 |
| 校準曲線 | ❌ | ❌ | Brier/ECE (高優先級) |
| PR 曲線 | ❌ | ❌ | PR AUC (高優先級) |
| SHAP 圖 | ❌ | ❌ | SHAP 分析 (高優先級) |
| PSI 圖 | ❌ | ❌ | PSI (高優先級) |
| 體制圖 | ❌ | ❌ | 市場體制 (高優先級) |

#### 🆚 兩者的定位差異

```python
# GUIDE 中的視覺化: 橫向比較多個模型
plot_model_comparison(
    models=[model_A, model_B, model_C],
    metrics=['train_auc', 'cv_auc', 'samples']
)
→ 幫你選出最佳模型

# 缺失項目的視覺化: 深入分析單一模型
plot_model_diagnostics(
    model=best_model,
    X_test=X_test,
    y_test=y_test
)
→ 幫你理解模型為何好/壞,是否可信
```

---

**Q3: 前端看不到這些基本對比圖表,是否已實作?**

**答案**: 好問題!讓我幫你確認系統的實際狀態,避免誤解文件與實作的差距。

#### 🔍 當前實作狀態檢查

**GUIDE 文件所列的圖表**:
| 圖表類型 | GUIDE 設計 | 後端實作 | 前端展示 | 備註 |
|---------|----------|---------|---------|------|
| **基本對比圖表** ||||| 
| 性能散點圖 | ✅ | ✅ | ⚠️ | 前端有但可能位置不明顯 |
| 雷達圖 | ✅ | ❌ | ❌ | 僅有設計，未實作 |
| 特徵重要性柱狀圖 | ✅ | ✅ | ⚠️ | 後端有數據，前端展示簡陋 |
| 熱力圖 | ✅ | ❌ | ❌ | 僅有設計，未實作 |
| **進階分析圖** |||||
| 校準曲線 | ❌ | ❌ | ❌ | 缺失項目 |
| PR 曲線 | ❌ | ❌ | ❌ | 缺失項目 |
| SHAP 圖 | ❌ | ❌ | ❌ | 缺失項目 |

#### 📂 實際可能看到圖表的位置

**如果你在優化頁面**（`frontend/src/app/optimization/page.tsx`):
```
你應該能看到:
✅ MetricsPanel: 各項指標的數值卡片
✅ TrialHistoryTable: 試驗歷史表格
✅ DensityComparisonChart: 訊號密度對比柱狀圖
✅ StabilityChart: 穩定性分析折線圖
⚠️ ParameterImportanceChart: 參數重要性（類似特徵重要性）

你可能看不到:
❌ 雷達圖（多模型綜合評分）
❌ 熱力圖（模型排名矩陣）
❌ 性能散點圖（可能有但位置隱藏）
```

**如果你在案例搜尋結果頁**（`frontend/src/app/case/page.tsx`):
```
你應該能看到:
✅ MultiPaneChartNew: K線圖 + 技術指標
✅ TakerRatioChart: 主動買賣比圖表

你看不到:
❌ 模型性能對比圖（這頁不需要）
```

#### 🔎 為什麼文件說有，但你看不到？

**原因 1: GUIDE 是「設計文件」,非「實作清單」**
```
XGBOOST_MULTI_RESULT_ANALYSIS_GUIDE.md 的性質:
- ✅ 詳細的設計方案與範例程式碼
- ✅ 完整的使用場景說明
- ❌ 不等於「已經全部實作完成」

就像:
- 建築設計圖 ≠ 房子已經蓋好
- 菜單 ≠ 廚房已經做好這道菜
```

**原因 2: 後端有資料,前端沒展示組件**
```python
# 後端可能已經產生數據 (xgboost_analyzer.py):
feature_importance = model.get_score(importance_type='gain')
# ↑ 這個數據存在

# 但前端沒有專門的圖表組件展示它
# 或者組件存在但在不太明顯的地方
```

**原因 3: 圖表存在但命名不同**
```
GUIDE 中: "性能散點圖"
前端實際: "MetricsDistributionChart" 或其他名稱
→ 導致你找不到對應組件
```

#### 🛠️ 如何確認實際狀態

**Step 1: 檢查前端組件清單**
```bash
# 搜尋前端組件
find frontend/src/components -name "*Chart.tsx" -o -name "*Panel.tsx"

預期結果:
- DensityComparisonChart.tsx ✅ (實作了)
- StabilityChart.tsx ✅ (實作了)
- RadarChart.tsx ❌ (如果沒找到，代表未實作)
- HeatmapChart.tsx ❌ (如果沒找到，代表未實作)
```

**Step 2: 檢查 API 返回數據**
```bash
# 訓練模型後，查看 API 返回的 JSON
# 應該包含:
{
  "feature_importance": {...},  // 如果有，代表後端支持
  "cv_results": [...],          // 如果有，代表可繪製散點圖
  "calibration_data": null      // 如果是 null，代表未實作
}
```

**Step 3: 查看頁面路由**
```bash
# 檢查 frontend/src/app/ 目錄
ls frontend/src/app/*/page.tsx

預期路由:
- /optimization/page.tsx ✅ (優化頁面)
- /case/page.tsx ✅ (案例頁面)
- /model-comparison/page.tsx ❌ (如果沒有，代表專門的對比頁面未實作)
```

#### ✅ 推測的實際情況

**已實作（你應該能看到）**:
1. ✅ **優化結果面板** - 各項指標的數值展示
2. ✅ **參數重要性圖** - 類似特徵重要性的柱狀圖
3. ✅ **訊號密度對比** - 不同參數組合的訊號數量
4. ✅ **K線圖表** - 案例的技術指標視覺化

**未實作（GUIDE 有設計但你看不到）**:
1. ❌ **雷達圖** - 多維度模型評分
2. ❌ **熱力圖** - 模型排名矩陣
3. ❌ **性能散點圖** - Train AUC vs CV AUC（可能有數據但沒單獨圖表）
4. ❌ **時間序列圖** - 性能隨時間衰減

**確實缺失（GUIDE 也沒設計）**:
1. ❌ **校準曲線** - 機率校準視覺化
2. ❌ **PR 曲線** - Precision-Recall 曲線
3. ❌ **SHAP 圖** - 特徵解釋視覺化
4. ❌ **PSI 柱狀圖** - 特徵飄移監控

#### 📊 實戰建議

**如果你需要立即看到這些圖表**:

1. **檢查現有組件的實際位置**:
   - 打開 `frontend/src/app/optimization/page.tsx`
   - 查看有哪些 `<*Chart />` 組件
   - 確認是否有你需要的圖表但命名不同

2. **暫時用後端數據自行繪製**:
   - 訓練完模型後，從 API 獲取 JSON 數據
   - 用 Python Plotly 或 Matplotlib 本地繪製
   - 這是最快的臨時方案

3. **實作缺失的前端組件**:
   - 參考已有的 `DensityComparisonChart.tsx`
   - 複製並修改成需要的圖表類型
   - 使用 Recharts 或 Plotly.js

4. **優先實作高價值圖表**:
   - 雷達圖（多模型對比）→ 幫助快速選模型
   - 性能散點圖（過擬合檢測）→ 幫助判斷模型可靠性
   - 熱力圖（參數敏感度）→ 幫助理解參數影響

#### 🎯 總結

**關鍵澄清**:
- ✅ GUIDE 文件 = 設計藍圖，不是「已完成清單」
- ⚠️ 部分圖表可能有後端數據但沒前端展示
- ❌ 雷達圖、熱力圖等進階視覺化確實未實作
- ❌ 缺失項目的視覺化（校準曲線、SHAP 等）也確實沒有

**你看不到圖表的真正原因**:
1. 確實沒實作（如雷達圖）
2. 實作了但藏在不明顯的位置
3. 命名與 GUIDE 不一致

**快速驗證方法**:
```bash
# 執行以下命令確認
grep -r "RadarChart" frontend/src/  # 搜尋雷達圖組件
grep -r "HeatmapChart" frontend/src/ # 搜尋熱力圖組件

# 如果無結果，代表確實沒實作
```

**建議下一步**:
如果需要這些圖表，可以告訴我你最需要哪幾個，我可以按優先順序幫忙實作前端組件。目前系統已有的數據基礎是足夠的，主要缺的是前端視覺化層。

---

**Q4: 分析結果視覺化 => 這是在 http://localhost:3000/patterns 中的統計分析和樣式比較的分類裡面嗎？**

**答案**: 是的，你的理解方向是對的。

目前前端已經有 `/patterns` 這個入口，並且用「頁籤/分類」的方式呈現：
- **統計分析**：偏向整體統計與分佈（例如 Pattern 數量、類型分佈等）
- **樣式比較**：偏向多個 Pattern 之間的比較（更接近 GUIDE 的 Layer 1 思路）

另外還有更貼近 XGBoost 的頁面路由（你可以把它視為「模型分析/診斷」的主入口之一）：
- `/patterns/xgboost-analysis`

所以：
- GUIDE 的 Layer 1（多結果比較）很適合落在 `/patterns` 的「統計分析/樣式比較」這一層
- 缺失項目的 Layer 2（校準曲線、PR、SHAP、PSI、分 phase 表現）則更適合落在 `/patterns/xgboost-analysis`（或其子頁）裡

---

#### 🛠️ 實作優先順序建議

```
Phase 1 (立即): 補完 GUIDE 中的基礎視覺化
  1. 雷達圖 (多維度模型評分)
  2. 熱力圖 (模型排名矩陣)
  3. 時間序列圖 (性能衰減趨勢)
  → 工具: Plotly (已在用)
  → 位置: frontend/src/components/optimization/

Phase 2 (高優先): 實作高優先級缺失項目的視覺化
  1. 校準曲線 (檢查機率是否可信)
  2. ROC 與 PR 曲線對比圖
  3. SHAP 摘要圖 (Top 20 特徵)
  4. PSI 柱狀圖 (特徵飄移監控)
  → 工具: Plotly + shap (Python)
  → 位置: 先在後端生成,前端展示

Phase 3 (中優先): 擴展分析維度
  1. 市場體制分解圖 (牛/熊/橫盤分別表現)
  2. 特徵重要性時間衰減折線圖
  3. 跨幣種泛化熱力圖
  → 工具: Recharts (前端) + Python (後端預處理)

Phase 4 (低優先): 互動式 Dashboard
  1. Streamlit 原型 (內部分析用)
  2. Plotly Dash 正式版 (生產部署)
  → 參考: GUIDE 的 Dashboard 設計章節
```


## ✅ 落地實作結論：這些 Missing 要怎麼做，才會變成可用系統？

你說得很對：既然缺失項目都要實作，那文件最終應該把「概念」收斂成「工程任務」。我建議用 **資料契約 → 計算層 → 輸出層 → 視覺化層 → 監控層** 這條主線來落地。

### 0) 先定義資料契約（這一步會決定後面一切能不能自動化）

最小必要欄位：
- `case_id`（可由 `Symbol + Timestamp + Trigger_Index` 生成）
- `Timestamp`（案例時間，用來排序與做時間切分/OOT）
- `Positive_Case`（0/1，作為 `y_true`）
- 特徵欄位（X）

強烈建議欄位：
- `Market_Phase`（你已經有，直接用來做分 phase 評估）
- `Symbol`、`Timeframe`（用來做分標的/分週期統計，避免混在一起產生誤解）

### 1) 分割策略落地（時間序列 CV + OOT）

- **CV**：預設使用時間序列切分（Walk-Forward），避免隨機打散造成時間洩漏
- **OOT**：預設保留最新一段時間（例如最後 N 週/月）當最終驗收
- **輸出切分報告**：保存 Train/Val/OOT 的時間範圍、樣本數、與索引（可重現）

### 2) 統一輸出「預測機率」與「可視覺化資料」

要能做校準/PR/SHAP/PSI/分 phase，後端必須輸出：
- 每筆案例的 `predicted_proba`（至少 validation 與 OOT）
- 指標計算結果（Brier、ECE、PR AUC、PSI）
- 視覺化用資料點（例如 Calibration Curve bins、PR curve points、PSI histogram）

### 3) 分 market phase 的診斷報告（直接變成交易規則）

- 對每個 `market_phase` 輸出：AUC、Precision@K、Brier/ECE（可選）、樣本數
- 若某 phase 指標明顯偏弱：
    - **交易過濾**：該 phase 不交易
    - 或 **分級交易**：只允許 A 級訊號

### 4) 前端視覺化落地（把結果放到你真的會看的地方）

- `/patterns`：放「統計分析 / 樣式比較」這類多結果比較（GUIDE Layer 1）
- `/patterns/xgboost-analysis`：放「模型診斷」：校準曲線、PR 曲線、SHAP、PSI、分 phase 指標（Missing Layer 2）

### 5) 驗收標準（做完就知道有沒有真的完成）

每次分析/訓練任務完成後，至少要能回答：
- 這次 Train/Val/OOT 的時間範圍是什麼？
- OOT AUC 與分 market phase AUC 各是多少？
- 機率是否可信（Brier/ECE/校準曲線）？
- 你要用哪個門檻做分級交易（A/B/C）？是否需要分 phase 門檻？

做到這些，missing 就不只是「清單」，而是變成可長期運行、可監控、可視覺化、可用來決策的完整閉環。


## 📌 附錄：問題索引

1. OOT 驗證實作方式與 CV 的差異
2. 市場體制分析的策略搭配
3. 機率校準指標的計算方法
4. AUC 的計算原理
5. PSI 的計算公式
6. SHAP 與現有分析的差異
7. Purged K-Fold 的必要性
8. 跨幣種驗證的實作方法
9. Precision@K 的 K 值選擇
10. 期望值計算的時機
11. 視覺化分析的實作狀態

---

**維護者**: Quantitative Trading System Team  
**建立日期**: 2026-01-27  
**最後更新**: 2026-01-27

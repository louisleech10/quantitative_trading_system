# XGBoost 機器學習教學

**適用系統**: Pattern Discovery System  
**版本**: 1.0.0  
**更新日期**: 2026-01-10  
**難度**: 中級

---

## 📚 目錄

1. [核心概念](#核心概念)
2. [系統整合架構](#系統整合架構)
3. [特徵工程](#特徵工程)
4. [模型訓練](#模型訓練)
5. [規則提取](#規則提取)
6. [實戰範例](#實戰範例)
7. [調參指南](#調參指南)
8. [常見問題](#常見問題)

---

## 🎯 核心概念

### 什麼是 XGBoost？

**XGBoost (eXtreme Gradient Boosting)** 是一個高效的梯度提升決策樹 (GBDT) 實現，在量化交易中用於：
- **模式發現**: 從歷史數據中自動發現有效的交易規則
- **特徵重要性**: 量化哪些技術指標最影響交易結果
- **風險控制**: 識別高風險特徵組合

### 關鍵優勢

| 優勢 | 說明 | 量化交易應用 |
|------|------|--------------|
| **可解釋性** | 生成決策樹，可視化決策路徑 | 提取「IF 條件 THEN 買入」規則 |
| **特徵重要性** | 量化每個特徵的貢獻度 | 找出最重要的技術指標 |
| **處理非線性** | 捕捉複雜的特徵交互作用 | 識別多指標組合條件 |
| **防過擬合** | 內建正則化和交叉驗證 | 確保規則在新數據上有效 |

---

## 🏗️ 系統整合架構

### 數據流程

```
歷史 K 線數據
    ↓
特徵工程 (Feature Engineering)
    ├─ EMA (5, 20, 60)
    ├─ 價格變化百分比
    ├─ 密度計算 (Near/Far)
    └─ 信號分數
    ↓
標籤生成 (Labeling)
    ├─ 正例 (is_positive=True): 達到獲利目標
    └─ 反例 (is_positive=False): 未達標或止損
    ↓
XGBoost 訓練 (Model Training)
    ├─ 5-Fold 交叉驗證
    ├─ 100-200 次迭代
    └─ 提早停止 (Early Stopping)
    ↓
評估與分析
    ├─ AUC, Precision, Recall, F1
    ├─ 特徵重要性排名
    └─ 過擬合檢測
    ↓
規則提取 (Rule Extraction)
    ├─ 決策樹路徑分析
    ├─ 條件組合 (AND/OR)
    └─ Support/Confidence 計算
    ↓
模式定義 (Pattern Definition)
    └─ 儲存為 JSON (可回測)
```

### 核心模組

| 模組 | 路徑 | 功能 |
|------|------|------|
| **Feature Engineering** | `momentum/Analysis/feature_engineering.py` | 技術指標計算、特徵提取 |
| **XGBoost Analyzer** | `momentum/Analysis/xgboost_analyzer.py` | 模型訓練、評估、特徵重要性 |
| **Pattern Extractor** | `momentum/Analysis/pattern_extractor.py` | 決策規則提取 |
| **Pattern Definition** | `momentum/Analysis/pattern_definition.py` | 模式定義數據結構 |
| **API Service** | `api/services/pattern_discovery_service.py` | API 路由處理 |

---

## 🔧 特徵工程

### 特徵類型

#### 1. 價格動量特徵 (Price Momentum)
```python
# 計算過去 N 根 K 線的價格變化百分比
price_change_pct = (close - open) / open

# 累積變化
cumulative_change = (close - close_n_bars_ago) / close_n_bars_ago
```

#### 2. 均線特徵 (EMA)
```python
# 快速 EMA (5)
ema_5 = df['close'].ewm(span=5, adjust=False).mean()

# 中速 EMA (20)
ema_20 = df['close'].ewm(span=20, adjust=False).mean()

# 慢速 EMA (60)
ema_60 = df['close'].ewm(span=60, adjust=False).mean()

# 均線乖離率
ema_5_dev = (close - ema_5) / ema_5
ema_20_dev = (close - ema_20) / ema_20
```

#### 3. 密度特徵 (Density)
```python
# Near 窗口密度 (近期類似案例)
near_density = count_similar_cases(window=30) / 30

# Far 窗口密度 (長期類似案例)
far_density = count_similar_cases(window=90) / 90

# 密度比率
density_ratio = near_density / (far_density + 1e-6)
```

#### 4. 信號特徵 (Entry Signal)
```python
# 三線順勢信號 (Golden Cross)
entry_signal_score = (
    (ema_5 > ema_20) * 1 +
    (ema_20 > ema_60) * 1 +
    (close > ema_5) * 1
) / 3  # 標準化到 0-1
```

### 特徵提取實戰

```python
from momentum.Analysis.feature_engineering import FeatureEngineer

# 初始化特徵工程器
engineer = FeatureEngineer()

# 從案例提取特徵
features_df = engineer.extract_features_from_cases(
    case_ids=['ETHUSDT_1h_20231001_120000'],
    data_source='data_cache/kline_cache.h5'
)

# 檢查特徵數量
print(f"提取了 {len(features_df.columns)} 個特徵")
print(features_df.columns.tolist())

# 輸出範例
# ['price_change_pct', 'ema_5', 'ema_20', 'ema_60', 'ema_5_dev', 'ema_20_dev', 
#  'near_density', 'far_density', 'density_ratio', 'entry_signal_score', ...]
```

### 特徵品質檢查

```python
from momentum.Analysis.feature_validator import FeatureValidator

validator = FeatureValidator()

# 檢查 NaN/Inf
nan_check = validator.check_nan_inf(features_df)
if nan_check['has_issues']:
    print(f"發現 {len(nan_check['columns_with_issues'])} 個欄位有問題")

# 檢查高相關性 (防止冗餘特徵)
corr_check = validator.check_high_correlation(features_df, threshold=0.95)
if corr_check['has_issues']:
    print(f"發現 {len(corr_check['high_corr_pairs'])} 對高相關特徵")
```

---

## 🤖 模型訓練

### 訓練流程

#### 1. 準備訓練數據

```python
from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer

# 初始化分析器
analyzer = XGBoostAnalyzer(random_state=42)

# 準備數據
positive_features = engineer.extract_features_from_cases(positive_case_ids)
negative_features = engineer.extract_features_from_cases(negative_case_ids)

# 標籤
positive_labels = [1] * len(positive_features)  # 正例標籤
negative_labels = [0] * len(negative_features)  # 反例標籤

# 合併數據
X = pd.concat([positive_features, negative_features], axis=0)
y = positive_labels + negative_labels
```

#### 2. 訓練模型

```python
# 訓練 (含交叉驗證)
results = analyzer.train_and_evaluate(
    X=X,
    y=y,
    cv_folds=5,  # 5-Fold 交叉驗證
    early_stopping_rounds=10  # 提早停止防止過擬合
)

# 查看結果
print(f"Train AUC: {results['train_auc']:.4f}")
print(f"CV AUC: {results['cv_auc']:.4f}")
print(f"Overfitting Score: {results['overfitting_score']:.4f}")
```

#### 3. 解讀模型指標

| 指標 | 公式 | 理想範圍 | 意義 |
|------|------|----------|------|
| **AUC** | Area Under ROC Curve | 0.6 - 0.85 | 整體分類能力 |
| **Precision** | TP / (TP + FP) | > 0.6 | 預測為正例時的準確度 |
| **Recall** | TP / (TP + FN) | > 0.5 | 找出所有正例的能力 |
| **F1 Score** | 2 * (P * R) / (P + R) | > 0.55 | 精確度與召回率平衡 |
| **Overfitting** | Train AUC - CV AUC | < 0.15 | 過擬合程度（越小越好） |

**判斷標準**:
- ✅ **良好**: CV AUC > 0.6, Overfitting < 0.10
- ⚠️ **可接受**: CV AUC > 0.55, Overfitting < 0.15
- ❌ **需重訓**: CV AUC < 0.55 或 Overfitting > 0.20

---

## 📊 特徵重要性分析

### 計算特徵重要性

```python
# 取得特徵重要性
importance_df = analyzer.get_feature_importance(method='gain', top_n=10)

print(importance_df)
```

**輸出範例**:
```
           feature  importance   rank  cumulative_importance
0   entry_signal_score      0.185      1                  0.185
1         ema_5_dev      0.142      2                  0.327
2    density_ratio      0.118      3                  0.445
3       near_density      0.095      4                  0.540
4        ema_20_dev      0.087      5                  0.627
5  price_change_pct      0.076      6                  0.703
6        far_density      0.068      7                  0.771
7              ema_5      0.052      8                  0.823
8             ema_20      0.041      9                  0.864
9             ema_60      0.038     10                  0.902
```

### 特徵重要性方法

| Method | 說明 | 適用場景 |
|--------|------|----------|
| **gain** | 特徵在分裂時帶來的平均增益 | 預設推薦 |
| **weight** | 特徵被使用的次數 | 快速判斷特徵使用頻率 |
| **cover** | 特徵覆蓋的樣本數 | 關注樣本覆蓋廣度 |

### 解讀重要性

```python
# 找出關鍵特徵 (累積重要性達 80%)
key_features = importance_df[importance_df['cumulative_importance'] <= 0.8]
print(f"關鍵特徵數量: {len(key_features)} / {len(importance_df)}")

# 前 3 名特徵佔比
top3_importance = importance_df.iloc[:3]['importance'].sum()
print(f"前 3 名特徵重要性: {top3_importance:.2%}")
```

**實戰建議**:
- 前 5 名特徵通常佔 60-70% 重要性
- 若單一特徵 > 30%，可能存在資料洩漏 (Data Leakage)
- 檢查是否有「未來函式」（使用了未來資訊的特徵）

---

## 🔍 規則提取

### 決策樹路徑分析

```python
from momentum.Analysis.pattern_extractor import PatternExtractor

# 初始化提取器
extractor = PatternExtractor(min_support=10)

# 提取規則
rules = extractor.extract_rules_from_model(
    model=analyzer.model,
    feature_names=X.columns.tolist(),
    X=X,
    y=y
)

print(f"提取了 {len(rules)} 條規則")
```

### 規則結構

每條規則包含:
```python
{
    "condition": "entry_signal_score > 0.67 AND ema_5_dev > 0.02",
    "support": 45,          # 符合條件的樣本數
    "confidence": 0.82,     # 預測準確度
    "lift": 2.15,           # 提升度（與基礎概率比較）
    "sample_indices": [12, 45, 67, ...]  # 符合條件的樣本索引
}
```

### 關鍵指標解讀

#### Support (支持度)
```
Support = 符合條件的樣本數

範例: Support=45 表示有 45 個案例滿足此規則
最小支持度建議: >= 10 (避免規則過於極端)
```

#### Confidence (信心度)
```
Confidence = 正例樣本數 / 總符合樣本數

範例: 45 個樣本中有 37 個是正例 → Confidence = 37/45 = 0.82
理想範圍: > 0.7
```

#### Lift (提升度)
```
Lift = Confidence / 基礎正例比率

範例: 
- 基礎正例比率 = 200/500 = 0.4 (40%)
- 規則信心度 = 0.82 (82%)
- Lift = 0.82 / 0.4 = 2.05

解讀: 此規則比隨機選擇提升 2.05 倍效果
理想範圍: > 1.5
```

### 篩選高品質規則

```python
# 篩選條件
high_quality_rules = [
    rule for rule in rules
    if (
        rule['support'] >= 20 and
        rule['confidence'] >= 0.75 and
        rule['lift'] >= 1.5
    )
]

print(f"高品質規則: {len(high_quality_rules)} / {len(rules)}")

# 排序 (依 confidence 降序)
high_quality_rules.sort(key=lambda x: x['confidence'], reverse=True)

# 顯示 Top 5
for i, rule in enumerate(high_quality_rules[:5], 1):
    print(f"{i}. {rule['condition']}")
    print(f"   Support={rule['support']}, Confidence={rule['confidence']:.2f}, Lift={rule['lift']:.2f}")
```

---

## 💡 實戰範例

### 完整工作流程

```python
# ========== 1. 特徵工程 ==========
from momentum.Analysis.feature_engineering import FeatureEngineer

engineer = FeatureEngineer()

# 準備案例 ID
positive_cases = ['ETHUSDT_1h_20231015_140000', 'ETHUSDT_1h_20231022_100000']
negative_cases = ['ETHUSDT_1h_20231018_080000', 'ETHUSDT_1h_20231025_180000']

# 提取特徵
X_pos = engineer.extract_features_from_cases(positive_cases)
X_neg = engineer.extract_features_from_cases(negative_cases)

# 合併數據
X = pd.concat([X_pos, X_neg], axis=0)
y = [1]*len(X_pos) + [0]*len(X_neg)

print(f"訓練數據: {len(X)} 筆, 正例={len(X_pos)}, 反例={len(X_neg)}")

# ========== 2. 訓練模型 ==========
from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer

analyzer = XGBoostAnalyzer(random_state=42)
results = analyzer.train_and_evaluate(X, y, cv_folds=5)

print(f"Train AUC: {results['train_auc']:.4f}")
print(f"CV AUC: {results['cv_auc']:.4f}")
print(f"Precision: {results['precision']:.4f}")
print(f"Recall: {results['recall']:.4f}")
print(f"F1 Score: {results['f1']:.4f}")

# ========== 3. 特徵重要性 ==========
importance_df = analyzer.get_feature_importance(method='gain', top_n=10)
print("\nTop 10 特徵:")
print(importance_df[['feature', 'importance', 'rank']])

# ========== 4. 提取規則 ==========
from momentum.Analysis.pattern_extractor import PatternExtractor

extractor = PatternExtractor(min_support=10)
rules = extractor.extract_rules_from_model(
    model=analyzer.model,
    feature_names=X.columns.tolist(),
    X=X,
    y=y
)

# 篩選高品質規則
high_quality = [r for r in rules if r['confidence'] >= 0.75 and r['lift'] >= 1.5]
print(f"\n高品質規則: {len(high_quality)} 條")

for i, rule in enumerate(high_quality[:3], 1):
    print(f"\n規則 {i}:")
    print(f"  條件: {rule['condition']}")
    print(f"  Support={rule['support']}, Confidence={rule['confidence']:.2f}, Lift={rule['lift']:.2f}")

# ========== 5. 建立模式定義 ==========
from momentum.Analysis.pattern_definition import Pattern, PatternRule

# 將規則轉換為模式
pattern_rules = []
for rule in high_quality[:5]:  # 取前 5 條規則
    # 解析條件 (簡化範例)
    # 實際需要完整解析 "entry_signal_score > 0.67 AND ema_5_dev > 0.02"
    pattern_rules.append(PatternRule(
        feature='entry_signal_score',
        operator='>',
        threshold=0.67,
        description=rule['condition']
    ))

# 建立模式
pattern = Pattern(
    pattern_id='XGBOOST_001',
    name='XGBoost 發現模式',
    description=f'由 XGBoost 自動發現, CV AUC={results["cv_auc"]:.4f}',
    case_id=positive_cases[0],
    rules=pattern_rules,
    tags=['xgboost', 'machine-learning', 'auto-discovered'],
    status='testing',
    performance_metrics={
        'precision': results['precision'],
        'recall': results['recall'],
        'f1_score': results['f1'],
        'auc': results['cv_auc']
    }
)

# 儲存模式
from momentum.Analysis.pattern_storage import PatternStorage

storage = PatternStorage(base_dir='data_cache/patterns')
storage.save_pattern(pattern)

print(f"\n模式已儲存: {pattern.pattern_id}")
```

---

## ⚙️ 調參指南

### XGBoost 關鍵參數

| 參數 | 預設值 | 推薦範圍 | 作用 |
|------|--------|----------|------|
| **n_estimators** | 100 | 50-200 | 迭代次數（樹的數量） |
| **max_depth** | 3 | 3-6 | 樹的最大深度（防過擬合） |
| **learning_rate** | 0.1 | 0.01-0.3 | 學習率（越小越穩定） |
| **min_child_weight** | 1 | 1-5 | 葉子節點最小樣本權重 |
| **subsample** | 1.0 | 0.6-1.0 | 隨機採樣比例（防過擬合） |
| **colsample_bytree** | 1.0 | 0.6-1.0 | 特徵採樣比例 |
| **gamma** | 0 | 0-0.5 | 分裂所需最小損失減少 |
| **reg_alpha** | 0 | 0-1 | L1 正則化 |
| **reg_lambda** | 1 | 0-5 | L2 正則化 |

### 調參策略

#### 1. 快速驗證 (Fast Validation)
```python
# 小數據集 (< 500 樣本)
params = {
    'n_estimators': 50,
    'max_depth': 3,
    'learning_rate': 0.1
}
```

#### 2. 正常訓練 (Normal Training)
```python
# 中等數據集 (500-2000 樣本)
params = {
    'n_estimators': 100,
    'max_depth': 4,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8
}
```

#### 3. 深度優化 (Deep Optimization)
```python
# 大數據集 (> 2000 樣本)
params = {
    'n_estimators': 200,
    'max_depth': 5,
    'learning_rate': 0.03,
    'subsample': 0.7,
    'colsample_bytree': 0.7,
    'gamma': 0.1,
    'reg_alpha': 0.5,
    'reg_lambda': 1.0
}
```

### 過擬合調整

**症狀**: Train AUC - CV AUC > 0.15

**解決方案**:
1. **降低模型複雜度**:
   - 減少 `max_depth` (例如從 6 降到 4)
   - 減少 `n_estimators` (例如從 200 降到 100)

2. **增加正則化**:
   - 增加 `reg_alpha` 和 `reg_lambda`
   - 增加 `gamma`

3. **數據採樣**:
   - 降低 `subsample` (例如 0.8 → 0.7)
   - 降低 `colsample_bytree` (例如 0.8 → 0.7)

4. **提早停止**:
   ```python
   analyzer.train_and_evaluate(
       X, y,
       early_stopping_rounds=10  # 10 輪無改善則停止
   )
   ```

### 欠擬合調整

**症狀**: Train AUC < 0.6, CV AUC < 0.55

**解決方案**:
1. **增加模型複雜度**:
   - 增加 `max_depth` (例如從 3 增到 5)
   - 增加 `n_estimators` (例如從 50 增到 150)

2. **檢查特徵品質**:
   - 使用 `FeatureValidator` 檢查 NaN/Inf
   - 檢查是否有高相關性特徵
   - 增加更多有意義的特徵

3. **檢查數據品質**:
   - 正負例比例 (建議 1:1 到 1:3)
   - 樣本數量 (建議 >= 200)
   - 標籤正確性

---

## ❓ 常見問題

### Q1: AUC 只有 0.5 怎麼辦？

**原因分析**:
- 特徵沒有區分能力（等於隨機猜測）
- 標籤錯誤或不一致
- 特徵與標籤無關聯

**解決步驟**:
```python
# 1. 檢查特徵分布
import matplotlib.pyplot as plt
for col in X.columns[:5]:
    plt.figure()
    X[y==1][col].hist(alpha=0.5, label='Positive')
    X[y==0][col].hist(alpha=0.5, label='Negative')
    plt.legend()
    plt.title(col)
    plt.show()

# 2. 檢查標籤平衡
print(f"正例比例: {sum(y)/len(y):.2%}")

# 3. 檢查特徵相關性
print(X.corrwith(pd.Series(y)).sort_values(ascending=False))
```

### Q2: 模型過擬合嚴重？

**判斷標準**: Train AUC = 0.95, CV AUC = 0.60 (差距 0.35)

**解決方案**:
```python
# 方案 1: 減少複雜度
analyzer = XGBoostAnalyzer(
    n_estimators=50,      # 減少迭代次數
    max_depth=3,          # 降低樹深度
    learning_rate=0.05    # 降低學習率
)

# 方案 2: 增加正則化
analyzer = XGBoostAnalyzer(
    reg_alpha=1.0,        # L1 正則化
    reg_lambda=2.0,       # L2 正則化
    gamma=0.2             # 分裂懲罰
)

# 方案 3: 數據採樣
analyzer = XGBoostAnalyzer(
    subsample=0.7,        # 70% 樣本採樣
    colsample_bytree=0.7  # 70% 特徵採樣
)
```

### Q3: 特徵重要性都很平均？

**原因**: 特徵之間高度相關，或者沒有明顯主導特徵

**處理方式**:
```python
# 1. 移除高相關特徵
from momentum.Analysis.feature_validator import FeatureValidator

validator = FeatureValidator()
corr_check = validator.check_high_correlation(X, threshold=0.90)

# 移除相關性高的特徵
if corr_check['has_issues']:
    for pair in corr_check['high_corr_pairs']:
        print(f"移除: {pair['feature2']} (與 {pair['feature1']} 相關度 {pair['correlation']:.2f})")
        X = X.drop(columns=[pair['feature2']])

# 2. 重新訓練
analyzer.train_and_evaluate(X, y)
```

### Q4: 規則提取失敗？

**可能原因**:
- `min_support` 設定過高
- 決策樹過於複雜
- 樣本數不足

**解決方案**:
```python
# 降低最小支持度
extractor = PatternExtractor(min_support=5)  # 從 10 降到 5

# 或檢查樣本分布
print(f"總樣本數: {len(X)}")
print(f"正例數: {sum(y)}")
print(f"反例數: {len(y) - sum(y)}")
```

### Q5: 模型指標很好但實盤很差？

**常見陷阱**:
1. **未來函式**: 使用了未來資訊（例如 `close_future` 欄位）
2. **資料洩漏**: 訓練集和測試集有重疊
3. **倖存者偏差**: 只使用了存活的交易對

**檢查清單**:
```python
# 1. 檢查特徵名稱
suspicious_features = [col for col in X.columns if 'future' in col.lower()]
if suspicious_features:
    print(f"警告: 發現疑似未來函式 - {suspicious_features}")

# 2. 檢查時間序列分割
from sklearn.model_selection import TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=5)
for train_idx, test_idx in tscv.split(X):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    # 確保訓練集時間 < 測試集時間

# 3. 重新驗證
analyzer.train_and_evaluate(X, y, cv_folds=5)
```

---

## 📖 進階閱讀

### 推薦資源

1. **XGBoost 官方文件**:
   - https://xgboost.readthedocs.io/

2. **量化交易機器學習**:
   - [docs/ML_FEATURE_EXTRACTION.md](../docs/ML_FEATURE_EXTRACTION.md)
   - [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)

3. **系統 API 文件**:
   - [docs/API_SPECIFICATION.md](../docs/API_SPECIFICATION.md)
   - GET `/api/v1/patterns/analysis/{case_id}` - XGBoost 分析端點

### 下一步

完成本教學後，您可以:
- ✅ 理解 XGBoost 在量化交易中的應用
- ✅ 使用 `XGBoostAnalyzer` 訓練模型
- ✅ 提取和解讀特徵重要性
- ✅ 從決策樹中提取交易規則
- ✅ 建立和儲存模式定義

**建議下一步**:
1. 閱讀 [PHASE4_USAGE_GUIDE.md](PHASE4_USAGE_GUIDE.md) 了解完整工作流程
2. 執行 `test_xgboost_analyzer.py` 實際體驗
3. 嘗試在前端 UI 操作 (http://localhost:3000/patterns/analysis/[caseId])

---

**問題反饋**: 如有疑問，請查閱 [UAT_CHECKLIST.md](UAT_CHECKLIST.md) 或提交 Issue。

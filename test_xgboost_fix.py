"""
測試 XGBoost Analyzer 對 numpy array 的支援

驗證 train_model 可以同時接受：
1. pandas DataFrame
2. numpy array + feature_names
"""

import numpy as np
import pandas as pd
from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer

print("=" * 70)
print("測試 XGBoost Analyzer 的 numpy array 支援")
print("=" * 70)

# 建立測試數據
n_samples = 100
n_features = 5

# 特徵名稱
feature_names = [f'feature_{i}' for i in range(n_features)]

# 測試數據
X_array = np.random.randn(n_samples, n_features)
y = np.random.randint(0, 2, n_samples)

# 確保有兩個類別
y[:50] = 0
y[50:] = 1

print(f"\n數據準備:")
print(f"  樣本數: {n_samples}")
print(f"  特徵數: {n_features}")
print(f"  特徵名稱: {feature_names}")
print(f"  標籤分佈: 0={sum(y==0)}, 1={sum(y==1)}")

# 測試 1: numpy array + feature_names
print("\n" + "=" * 70)
print("測試 1: numpy array + feature_names")
print("=" * 70)

analyzer1 = XGBoostAnalyzer()
try:
    performance1 = analyzer1.train_model(
        X=X_array,
        y=y,
        feature_names=feature_names,
        early_stopping_rounds=5,
        eval_size=0.2
    )
    print(f"✅ 測試 1 通過")
    print(f"   Train AUC: {performance1.train_auc:.4f}")
    print(f"   CV AUC: {performance1.cv_auc_mean:.4f}")
    print(f"   特徵名稱已儲存: {analyzer1.feature_names}")
except Exception as e:
    print(f"❌ 測試 1 失敗: {e}")
    import traceback
    traceback.print_exc()

# 測試 2: pandas DataFrame (舊方式，應該仍然有效)
print("\n" + "=" * 70)
print("測試 2: pandas DataFrame (向後兼容)")
print("=" * 70)

X_df = pd.DataFrame(X_array, columns=feature_names)
analyzer2 = XGBoostAnalyzer()
try:
    performance2 = analyzer2.train_model(
        X=X_df,
        y=y,
        early_stopping_rounds=5,
        eval_size=0.2
    )
    print(f"✅ 測試 2 通過")
    print(f"   Train AUC: {performance2.train_auc:.4f}")
    print(f"   CV AUC: {performance2.cv_auc_mean:.4f}")
    print(f"   特徵名稱已儲存: {analyzer2.feature_names}")
except Exception as e:
    print(f"❌ 測試 2 失敗: {e}")
    import traceback
    traceback.print_exc()

# 測試 3: numpy array 沒有 feature_names (應該失敗)
print("\n" + "=" * 70)
print("測試 3: numpy array 沒有 feature_names (預期失敗)")
print("=" * 70)

analyzer3 = XGBoostAnalyzer()
try:
    performance3 = analyzer3.train_model(
        X=X_array,
        y=y,
        early_stopping_rounds=5,
        eval_size=0.2
    )
    print(f"❌ 測試 3 未按預期失敗")
except ValueError as e:
    print(f"✅ 測試 3 正確拋出錯誤: {e}")
except Exception as e:
    print(f"⚠️  測試 3 拋出非預期錯誤: {e}")

print("\n" + "=" * 70)
print("所有測試完成")
print("=" * 70)

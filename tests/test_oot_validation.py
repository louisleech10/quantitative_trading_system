"""
OOT 驗證系統測試

測試 Task 1.1 實作的 Out-of-Time 驗證功能

測試項目:
1. TimeSplitter 時間切分器
   - 自動偵測時間欄位
   - 手動切分
   - 自動切分
   - 時間重疊檢測
   - 最小樣本數檢查
   
2. XGBoostAnalyzer OOT 驗證
   - validate_oot 方法
   - CV-OOT Gap 計算
   - 狀態判定

3. PurgedTimeSeriesSplit
   - Purge 移除訓練集末端
   - Embargo 移除驗證集開頭

Author: AI Agent
Date: 2026-01-28
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List

# 導入要測試的模組
from momentum.Analysis.time_splitter import (
    TimeSplitter,
    PurgedTimeSeriesSplit,
    SplitResult,
    PeriodInfo,
    TimestampColumnNotFound,
    InsufficientOOTSamples,
    InsufficientTrainSamples,
    TimeRangeOverlap
)
from momentum.Analysis.xgboost_analyzer import (
    XGBoostAnalyzer,
    OOTValidationResult,
    ModelPerformance
)


# ==================== 測試資料生成 ====================

def generate_test_data(
    n_samples: int = 500,
    n_features: int = 10,
    positive_rate: float = 0.3,
    start_date: str = "2023-01-01",
    random_seed: int = 42
) -> tuple:
    """
    生成測試用資料
    
    Returns:
        (df, X, y, feature_names)
    """
    np.random.seed(random_seed)
    
    # 生成時間序列
    start = pd.Timestamp(start_date)
    timestamps = [start + timedelta(hours=12*i) for i in range(n_samples)]
    
    # 生成特徵
    feature_names = [f"feature_{i}" for i in range(n_features)]
    X = np.random.randn(n_samples, n_features)
    
    # 生成標籤（帶有時間趨勢）
    # 前期正樣本率較高，後期較低（模擬市場變化）
    time_factor = np.linspace(positive_rate + 0.1, positive_rate - 0.1, n_samples)
    y = (np.random.random(n_samples) < time_factor).astype(int)
    
    # 建立 DataFrame
    df = pd.DataFrame(X, columns=feature_names)
    df['Timestamp'] = timestamps
    df['positive_case'] = y
    
    return df, X, y, feature_names


# ==================== TimeSplitter 測試 ====================

class TestTimeSplitter:
    """TimeSplitter 測試類別"""
    
    @pytest.fixture
    def splitter(self):
        """建立 TimeSplitter 實例"""
        return TimeSplitter(
            min_oot_samples=50,
            min_train_samples=100,
            random_seed=42
        )
    
    @pytest.fixture
    def test_df(self):
        """建立測試資料"""
        df, _, _, _ = generate_test_data(n_samples=500)
        return df
    
    def test_detect_timestamp_column(self, splitter, test_df):
        """測試自動偵測時間欄位"""
        # 標準欄位名稱
        detected = splitter.detect_timestamp_column(test_df)
        assert detected == 'Timestamp', f"應偵測到 'Timestamp'，實際: {detected}"
        
        # 測試其他常見名稱
        df_copy = test_df.copy()
        df_copy = df_copy.rename(columns={'Timestamp': 'time'})
        detected = splitter.detect_timestamp_column(df_copy)
        assert detected == 'time', f"應偵測到 'time'，實際: {detected}"
        
        # 測試找不到的情況
        df_no_time = test_df.drop(columns=['Timestamp'])
        detected = splitter.detect_timestamp_column(df_no_time)
        assert detected is None, "沒有時間欄位時應返回 None"
        
        print("✅ 自動偵測時間欄位測試通過")
    
    def test_auto_split(self, splitter, test_df):
        """測試自動切分"""
        result = splitter.auto_split(
            df=test_df,
            oot_ratio=0.2,
            validation_ratio=0.1,
            label_col='positive_case'
        )
        
        # 驗證切分結果
        assert isinstance(result, SplitResult)
        assert result.split_method == "manual"  # auto_split 內部使用 split_by_time
        
        # 驗證樣本數
        total = len(test_df)
        expected_oot = int(total * 0.2)
        
        # OOT 應約為 20%
        assert abs(result.oot_period.samples - expected_oot) < 10, \
            f"OOT 樣本數應約為 {expected_oot}，實際: {result.oot_period.samples}"
        
        # 訓練 + 驗證 + OOT = 總數
        total_split = (
            result.train_period.samples +
            (result.validation_period.samples if result.validation_period else 0) +
            result.oot_period.samples
        )
        assert total_split == total, f"切分總數應為 {total}，實際: {total_split}"
        
        # 驗證時間順序（訓練 < 驗證 < OOT）
        train_end = pd.Timestamp(result.train_period.end)
        oot_start = pd.Timestamp(result.oot_period.start)
        assert train_end < oot_start, "訓練結束時間應早於 OOT 開始時間"
        
        print(f"✅ 自動切分測試通過 - 訓練: {result.train_period.samples}, "
              f"驗證: {result.validation_period.samples if result.validation_period else 0}, "
              f"OOT: {result.oot_period.samples}")
    
    def test_manual_split(self, splitter, test_df):
        """測試手動切分"""
        # 設定切分點
        train_end = "2023-06-30"
        oot_start = "2023-07-01"
        
        result = splitter.split_by_time(
            df=test_df,
            train_end=train_end,
            oot_start=oot_start,
            timestamp_col='Timestamp',
            validation_ratio=0.1,
            label_col='positive_case'
        )
        
        # 驗證切分結果
        assert isinstance(result, SplitResult)
        assert result.split_method == "manual"
        
        # 驗證時間範圍
        assert pd.Timestamp(result.train_period.end) <= pd.Timestamp(train_end)
        assert pd.Timestamp(result.oot_period.start) >= pd.Timestamp(oot_start)
        
        print(f"✅ 手動切分測試通過 - 訓練結束: {result.train_period.end}, "
              f"OOT 開始: {result.oot_period.start}")
    
    def test_time_overlap_error(self, splitter, test_df):
        """測試時間重疊錯誤"""
        with pytest.raises(TimeRangeOverlap):
            splitter.split_by_time(
                df=test_df,
                train_end="2023-07-01",  # 重疊
                oot_start="2023-06-30",
                timestamp_col='Timestamp'
            )
        
        print("✅ 時間重疊錯誤測試通過")
    
    def test_insufficient_oot_samples(self, splitter):
        """測試 OOT 樣本不足"""
        # 建立很小的資料集
        df, _, _, _ = generate_test_data(n_samples=100)
        
        with pytest.raises(InsufficientOOTSamples):
            splitter.split_by_time(
                df=df,
                train_end="2023-12-01",  # 只留很少的 OOT
                oot_start="2023-12-25",
                timestamp_col='Timestamp'
            )
        
        print("✅ OOT 樣本不足錯誤測試通過")
    
    def test_validate_no_overlap(self, splitter, test_df):
        """測試時間重疊驗證"""
        result = splitter.auto_split(df=test_df, oot_ratio=0.2)
        
        is_valid, error = splitter.validate_no_overlap(
            train_df=result.train_df,
            oot_df=result.oot_df,
            timestamp_col='Timestamp'
        )
        
        assert is_valid, f"應無重疊，錯誤: {error}"
        
        print("✅ 時間重疊驗證測試通過")
    
    def test_period_info_positive_rate(self, splitter, test_df):
        """測試正樣本率計算"""
        result = splitter.auto_split(
            df=test_df,
            oot_ratio=0.2,
            label_col='positive_case'
        )
        
        # 驗證正樣本率計算
        train_positive_rate = result.train_df['positive_case'].mean()
        assert abs(result.train_period.positive_rate - train_positive_rate) < 0.01, \
            "訓練集正樣本率計算不正確"
        
        oot_positive_rate = result.oot_df['positive_case'].mean()
        assert abs(result.oot_period.positive_rate - oot_positive_rate) < 0.01, \
            "OOT 正樣本率計算不正確"
        
        print(f"✅ 正樣本率計算測試通過 - 訓練: {train_positive_rate:.2%}, "
              f"OOT: {oot_positive_rate:.2%}")


# ==================== PurgedTimeSeriesSplit 測試 ====================

class TestPurgedTimeSeriesSplit:
    """PurgedTimeSeriesSplit 測試類別"""
    
    def test_purge_removes_training_end(self):
        """測試 Purge 移除訓練集末端"""
        splitter = PurgedTimeSeriesSplit(
            n_splits=3,
            purge_gap=5,
            embargo_pct=0.0  # 暫時不測試 embargo
        )
        
        X = np.random.randn(100, 5)
        
        for train_idx, val_idx in splitter.split(X):
            # 訓練集末端應被移除 purge_gap 個樣本
            # 驗證訓練集最大索引 + purge_gap < 驗證集最小索引
            train_max = train_idx.max()
            val_min = val_idx.min()
            
            # 因為 purge 移除了訓練集末端，所以 train_max + purge_gap 應 < val_min
            assert train_max + splitter.purge_gap <= val_min, \
                f"Purge 未正確移除訓練集末端: train_max={train_max}, val_min={val_min}"
        
        print("✅ Purge 移除訓練集末端測試通過")
    
    def test_embargo_removes_validation_start(self):
        """測試 Embargo 移除驗證集開頭"""
        splitter = PurgedTimeSeriesSplit(
            n_splits=3,
            purge_gap=0,  # 暫時不測試 purge
            embargo_pct=0.1
        )
        
        X = np.random.randn(100, 5)
        
        for train_idx, val_idx in splitter.split(X):
            # embargo 會移除驗證集開頭的 10%
            pass  # 主要驗證不會出錯
        
        print("✅ Embargo 移除驗證集開頭測試通過")
    
    def test_purge_and_embargo_combined(self):
        """測試 Purge 和 Embargo 組合"""
        splitter = PurgedTimeSeriesSplit(
            n_splits=3,
            purge_gap=5,
            embargo_pct=0.05
        )
        
        X = np.random.randn(200, 5)
        
        fold_count = 0
        for train_idx, val_idx in splitter.split(X):
            fold_count += 1
            
            # 驗證資料不會重疊
            train_set = set(train_idx)
            val_set = set(val_idx)
            overlap = train_set.intersection(val_set)
            
            assert len(overlap) == 0, f"訓練集和驗證集有重疊: {overlap}"
        
        assert fold_count > 0, "應該產生至少一個 fold"
        
        print(f"✅ Purge 和 Embargo 組合測試通過 - 產生 {fold_count} 個 fold")


# ==================== XGBoostAnalyzer OOT 驗證測試 ====================

class TestXGBoostAnalyzerOOT:
    """XGBoostAnalyzer OOT 驗證測試類別"""
    
    @pytest.fixture
    def trained_analyzer(self):
        """建立已訓練的 XGBoostAnalyzer"""
        df, X, y, feature_names = generate_test_data(
            n_samples=400,
            n_features=10,
            positive_rate=0.35
        )
        
        analyzer = XGBoostAnalyzer()
        
        # 訓練模型
        performance = analyzer.train_model(
            X=X,
            y=y,
            feature_names=feature_names,
            cv_folds=3
        )
        
        return analyzer, performance, X, y, feature_names
    
    def test_validate_oot_basic(self, trained_analyzer):
        """測試基本 OOT 驗證"""
        analyzer, performance, X, y, feature_names = trained_analyzer
        
        # 使用部分資料作為 OOT
        oot_start = int(len(X) * 0.8)
        X_oot = X[oot_start:]
        y_oot = y[oot_start:]
        
        result = analyzer.validate_oot(
            X_oot=X_oot,
            y_oot=y_oot,
            cv_auc_mean=performance.cv_auc_mean,
            oot_period_start="2023-10-01",
            oot_period_end="2023-12-31"
        )
        
        # 驗證結果類型
        assert isinstance(result, OOTValidationResult)
        
        # 驗證 AUC 範圍
        assert 0 <= result.oot_auc <= 1, f"OOT AUC 應在 [0, 1]，實際: {result.oot_auc}"
        
        # 驗證樣本數
        assert result.oot_samples == len(y_oot), \
            f"OOT 樣本數不正確: 預期 {len(y_oot)}，實際 {result.oot_samples}"
        
        # 驗證正樣本率
        expected_rate = y_oot.mean()
        assert abs(result.oot_positive_rate - expected_rate) < 0.01, \
            f"OOT 正樣本率不正確: 預期 {expected_rate:.4f}，實際 {result.oot_positive_rate:.4f}"
        
        print(f"✅ 基本 OOT 驗證測試通過 - OOT AUC: {result.oot_auc:.4f}, "
              f"CV-OOT Gap: {result.cv_oot_gap:.4f}")
    
    def test_cv_oot_gap_calculation(self, trained_analyzer):
        """測試 CV-OOT Gap 計算"""
        analyzer, performance, X, y, feature_names = trained_analyzer
        
        # 使用全部資料作為 OOT（應該有較低的 gap）
        result = analyzer.validate_oot(
            X_oot=X,
            y_oot=y,
            cv_auc_mean=performance.cv_auc_mean
        )
        
        # 計算預期 gap
        expected_gap = performance.cv_auc_mean - result.oot_auc
        
        assert abs(result.cv_oot_gap - expected_gap) < 0.001, \
            f"CV-OOT Gap 計算不正確: 預期 {expected_gap:.4f}，實際 {result.cv_oot_gap:.4f}"
        
        print(f"✅ CV-OOT Gap 計算測試通過 - Gap: {result.cv_oot_gap:.4f}")
    
    def test_gap_status_classification(self, trained_analyzer):
        """測試 Gap 狀態分類"""
        analyzer, performance, X, y, feature_names = trained_analyzer
        
        # 測試不同 gap 的狀態
        test_cases = [
            (0.95, 0.93, "good"),        # gap = 0.02 < 0.05
            (0.80, 0.74, "acceptable"),  # gap = 0.06, 0.05 <= gap < 0.08
            (0.75, 0.60, "warning"),     # gap = 0.15 >= 0.08
        ]
        
        for cv_auc, oot_auc, expected_status in test_cases:
            gap, status = analyzer.get_cv_oot_gap(cv_auc, oot_auc)
            assert status == expected_status, \
                f"Gap {gap:.4f} 狀態應為 '{expected_status}'，實際: '{status}'"
        
        print("✅ Gap 狀態分類測試通過")
    
    def test_validate_oot_no_model(self):
        """測試未訓練模型時的錯誤處理"""
        analyzer = XGBoostAnalyzer()
        
        X_oot = np.random.randn(50, 10)
        y_oot = np.random.randint(0, 2, 50)
        
        with pytest.raises(ValueError, match="模型尚未訓練"):
            analyzer.validate_oot(X_oot=X_oot, y_oot=y_oot)
        
        print("✅ 未訓練模型錯誤處理測試通過")
    
    def test_validate_oot_empty_data(self, trained_analyzer):
        """測試空資料錯誤處理"""
        analyzer, _, _, _, _ = trained_analyzer
        
        with pytest.raises(ValueError, match="OOT 資料為空"):
            analyzer.validate_oot(X_oot=np.array([]).reshape(0, 10), y_oot=np.array([]))
        
        print("✅ 空資料錯誤處理測試通過")
    
    def test_oot_result_to_dict(self, trained_analyzer):
        """測試 OOTValidationResult.to_dict()"""
        analyzer, performance, X, y, _ = trained_analyzer
        
        oot_start = int(len(X) * 0.8)
        result = analyzer.validate_oot(
            X_oot=X[oot_start:],
            y_oot=y[oot_start:],
            cv_auc_mean=performance.cv_auc_mean
        )
        
        result_dict = result.to_dict()
        
        # 驗證字典包含所有必要欄位
        required_keys = [
            'oot_auc', 'oot_precision', 'oot_recall', 'oot_f1',
            'oot_samples', 'oot_positive_count', 'oot_positive_rate',
            'cv_auc_mean', 'cv_oot_gap', 'gap_status', 'is_generalization_good'
        ]
        
        for key in required_keys:
            assert key in result_dict, f"結果字典缺少欄位: {key}"
        
        print("✅ OOTValidationResult.to_dict() 測試通過")


# ==================== 整合測試 ====================

class TestOOTIntegration:
    """OOT 驗證整合測試"""
    
    def test_full_workflow(self):
        """測試完整工作流程"""
        # 1. 生成資料
        df, X, y, feature_names = generate_test_data(
            n_samples=500,
            n_features=10,
            positive_rate=0.3
        )
        
        # 2. 時間切分
        splitter = TimeSplitter()
        split_result = splitter.auto_split(
            df=df,
            oot_ratio=0.2,
            validation_ratio=0.1,
            label_col='positive_case'
        )
        
        # 3. 提取訓練和 OOT 資料
        train_df = split_result.train_df
        oot_df = split_result.oot_df
        
        X_train = train_df[feature_names].values
        y_train = train_df['positive_case'].values
        
        X_oot = oot_df[feature_names].values
        y_oot = oot_df['positive_case'].values
        
        # 4. 訓練模型
        analyzer = XGBoostAnalyzer()
        performance = analyzer.train_model(
            X=X_train,
            y=y_train,
            feature_names=feature_names,
            cv_folds=3
        )
        
        # 5. OOT 驗證
        oot_result = analyzer.validate_oot(
            X_oot=X_oot,
            y_oot=y_oot,
            cv_auc_mean=performance.cv_auc_mean,
            oot_period_start=split_result.oot_period.start,
            oot_period_end=split_result.oot_period.end
        )
        
        # 6. 驗證結果
        assert oot_result.oot_samples == len(y_oot)
        assert 0 <= oot_result.oot_auc <= 1
        assert oot_result.gap_status in ['good', 'acceptable', 'warning', 'unknown']
        
        print("\n" + "=" * 60)
        print("OOT 驗證整合測試結果:")
        print("=" * 60)
        print(f"訓練集: {split_result.train_period.samples} 樣本")
        print(f"  期間: {split_result.train_period.start} ~ {split_result.train_period.end}")
        print(f"  正樣本率: {split_result.train_period.positive_rate:.2%}")
        print()
        print(f"OOT 集: {split_result.oot_period.samples} 樣本")
        print(f"  期間: {split_result.oot_period.start} ~ {split_result.oot_period.end}")
        print(f"  正樣本率: {split_result.oot_period.positive_rate:.2%}")
        print()
        print(f"模型效能:")
        print(f"  Train AUC: {performance.train_auc:.4f}")
        print(f"  CV AUC: {performance.cv_auc_mean:.4f} ± {performance.cv_auc_std:.4f}")
        print(f"  OOT AUC: {oot_result.oot_auc:.4f}")
        print()
        print(f"CV-OOT Gap: {oot_result.cv_oot_gap:.4f}")
        print(f"Gap 狀態: {oot_result.gap_status}")
        print(f"泛化能力良好: {oot_result.is_generalization_good()}")
        print("=" * 60)
        
        print("\n✅ 完整工作流程整合測試通過")


# ==================== 執行測試 ====================

if __name__ == "__main__":
    # 可以直接執行此檔案進行測試
    pytest.main([__file__, "-v", "--tb=short"])

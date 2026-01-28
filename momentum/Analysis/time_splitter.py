"""
Time Splitter - 時間序列資料切分器

提供 Out-of-Time (OOT) 驗證的資料切分功能，支援：
- 按時間切分訓練/驗證/OOT 資料
- 自動切分（依比例）
- Purged K-Fold 交叉驗證
- 時間範圍重疊檢測

Author: AI Agent
Date: 2026-01-28

First Principle Analysis:
- Why: CV 使用同時期資料驗證，可能學到「特定時期的規律」而非「普遍規律」
- What: 完全保留一段「未來時間」的資料，作為最終考試，評估模型的時間泛化能力
- Challenge: 直接回測不行嗎？→ 回測計算 PnL，OOT 只計算預測力，更快、更聚焦於模型品質
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from api.core.logging import get_logger

logger = get_logger(__name__)


# ==================== 錯誤類型定義 ====================

class TimeSplitterErrorType(Enum):
    """時間切分器錯誤類型"""
    TIMESTAMP_COLUMN_NOT_FOUND = "timestamp_column_not_found"
    INSUFFICIENT_OOT_SAMPLES = "insufficient_oot_samples"
    INSUFFICIENT_TRAIN_SAMPLES = "insufficient_train_samples"
    TIME_RANGE_OVERLAP = "time_range_overlap"
    INVALID_RATIO = "invalid_ratio"
    DATA_NOT_SORTED = "data_not_sorted"


class TimeSplitterError(Exception):
    """時間切分器錯誤基類"""
    def __init__(self, error_type: TimeSplitterErrorType, message: str):
        self.error_type = error_type
        self.message = message
        super().__init__(f"[{error_type.value}] {message}")


class TimestampColumnNotFound(TimeSplitterError):
    """找不到時間欄位"""
    def __init__(self, available_columns: List[str]):
        super().__init__(
            TimeSplitterErrorType.TIMESTAMP_COLUMN_NOT_FOUND,
            f"找不到時間欄位。可用欄位: {available_columns}"
        )


class InsufficientOOTSamples(TimeSplitterError):
    """OOT 樣本不足"""
    def __init__(self, actual: int, required: int):
        super().__init__(
            TimeSplitterErrorType.INSUFFICIENT_OOT_SAMPLES,
            f"OOT 樣本數 ({actual}) 少於最小需求 ({required})"
        )


class InsufficientTrainSamples(TimeSplitterError):
    """訓練樣本不足"""
    def __init__(self, actual: int, required: int):
        super().__init__(
            TimeSplitterErrorType.INSUFFICIENT_TRAIN_SAMPLES,
            f"訓練樣本數 ({actual}) 少於最小需求 ({required})"
        )


class TimeRangeOverlap(TimeSplitterError):
    """時間範圍重疊"""
    def __init__(self, train_end: str, oot_start: str):
        super().__init__(
            TimeSplitterErrorType.TIME_RANGE_OVERLAP,
            f"訓練集結束時間 ({train_end}) >= OOT 開始時間 ({oot_start})"
        )


# ==================== 資料結構定義 ====================

@dataclass
class PeriodInfo:
    """時間區間資訊"""
    start: str
    end: str
    samples: int
    positive_count: int = 0
    positive_rate: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "samples": self.samples,
            "positive_count": self.positive_count,
            "positive_rate": round(self.positive_rate, 4)
        }


@dataclass
class SplitResult:
    """切分結果"""
    train_df: pd.DataFrame
    validation_df: Optional[pd.DataFrame]
    oot_df: pd.DataFrame
    train_period: PeriodInfo
    validation_period: Optional[PeriodInfo]
    oot_period: PeriodInfo
    timestamp_column: str
    split_method: str  # "manual" or "auto"
    random_seed: Optional[int] = None
    
    def to_report_dict(self) -> dict:
        """轉換為報告字典"""
        return {
            "split_method": self.split_method,
            "timestamp_column": self.timestamp_column,
            "random_seed": self.random_seed,
            "train_period": self.train_period.to_dict(),
            "validation_period": self.validation_period.to_dict() if self.validation_period else None,
            "oot_period": self.oot_period.to_dict(),
            "total_samples": (
                self.train_period.samples + 
                (self.validation_period.samples if self.validation_period else 0) + 
                self.oot_period.samples
            )
        }


# ==================== 時間切分器 ====================

class TimeSplitter:
    """
    時間序列資料切分器
    
    支援按時間切分訓練/驗證/OOT 資料，用於 Out-of-Time 驗證
    """
    
    # 常見時間欄位名稱
    COMMON_TIMESTAMP_COLUMNS = [
        'Timestamp', 'timestamp', 'time', 'Time',
        'date', 'Date', 'datetime', 'DateTime',
        'open_time', 'Open_Time', 'OpenTime'
    ]
    
    def __init__(
        self,
        min_oot_samples: int = 50,
        min_train_samples: int = 100,
        random_seed: int = 42
    ):
        """
        初始化時間切分器
        
        Args:
            min_oot_samples: OOT 最小樣本數
            min_train_samples: 訓練集最小樣本數
            random_seed: 隨機種子（用於可重現性）
        """
        self.min_oot_samples = min_oot_samples
        self.min_train_samples = min_train_samples
        self.random_seed = random_seed
        self.logger = logger
    
    def detect_timestamp_column(self, df: pd.DataFrame) -> Optional[str]:
        """
        自動偵測時間欄位
        
        Args:
            df: 資料 DataFrame
            
        Returns:
            時間欄位名稱，找不到時返回 None
        """
        for col_name in self.COMMON_TIMESTAMP_COLUMNS:
            if col_name in df.columns:
                self.logger.info(f"偵測到時間欄位: {col_name}")
                return col_name
        
        # 嘗試找到包含 'time' 或 'date' 的欄位
        for col in df.columns:
            col_lower = col.lower()
            if 'time' in col_lower or 'date' in col_lower:
                self.logger.info(f"偵測到時間欄位: {col}")
                return col
        
        return None
    
    def _parse_timestamp(self, value: Union[str, int, float, datetime, pd.Timestamp]) -> pd.Timestamp:
        """
        解析時間戳
        
        支援 ISO string、Unix timestamp (毫秒/秒)、datetime 物件
        """
        if isinstance(value, (pd.Timestamp, datetime)):
            return pd.Timestamp(value)
        
        if isinstance(value, str):
            return pd.Timestamp(value)
        
        if isinstance(value, (int, float)):
            # 判斷是秒還是毫秒（毫秒通常 > 1e12）
            if value > 1e12:
                return pd.Timestamp(value, unit='ms')
            else:
                return pd.Timestamp(value, unit='s')
        
        raise ValueError(f"無法解析時間戳: {value} (類型: {type(value)})")
    
    def _ensure_sorted(
        self,
        df: pd.DataFrame,
        timestamp_col: str
    ) -> pd.DataFrame:
        """確保資料按時間排序"""
        df_sorted = df.sort_values(timestamp_col).reset_index(drop=True)
        return df_sorted
    
    def _calculate_period_info(
        self,
        df: pd.DataFrame,
        timestamp_col: str,
        label_col: Optional[str] = None
    ) -> PeriodInfo:
        """計算時間區間資訊"""
        if len(df) == 0:
            return PeriodInfo(start="", end="", samples=0)
        
        start = str(df[timestamp_col].iloc[0])
        end = str(df[timestamp_col].iloc[-1])
        samples = len(df)
        
        positive_count = 0
        positive_rate = 0.0
        if label_col and label_col in df.columns:
            positive_count = int(df[label_col].sum())
            positive_rate = positive_count / samples if samples > 0 else 0.0
        
        return PeriodInfo(
            start=start,
            end=end,
            samples=samples,
            positive_count=positive_count,
            positive_rate=positive_rate
        )
    
    def split_by_time(
        self,
        df: pd.DataFrame,
        train_end: str,
        oot_start: str,
        timestamp_col: Optional[str] = None,
        validation_ratio: float = 0.0,
        label_col: Optional[str] = None
    ) -> SplitResult:
        """
        按時間切分資料
        
        Args:
            df: 資料 DataFrame
            train_end: 訓練集結束時間（ISO string 或 Unix timestamp）
            oot_start: OOT 開始時間
            timestamp_col: 時間欄位名稱（None 時自動偵測）
            validation_ratio: 從訓練集末端抽取的驗證集比例（0-1）
            label_col: 標籤欄位名稱（用於計算正樣本率）
            
        Returns:
            SplitResult 物件
            
        Raises:
            TimestampColumnNotFound: 找不到時間欄位
            TimeRangeOverlap: 時間範圍重疊
            InsufficientOOTSamples: OOT 樣本不足
            InsufficientTrainSamples: 訓練樣本不足
        """
        # 偵測時間欄位
        if timestamp_col is None:
            timestamp_col = self.detect_timestamp_column(df)
            if timestamp_col is None:
                raise TimestampColumnNotFound(df.columns.tolist())
        
        if timestamp_col not in df.columns:
            raise TimestampColumnNotFound(df.columns.tolist())
        
        self.logger.info(
            f"開始時間切分 - 時間欄位: {timestamp_col}, "
            f"訓練結束: {train_end}, OOT 開始: {oot_start}"
        )
        
        # 解析時間範圍
        train_end_ts = self._parse_timestamp(train_end)
        oot_start_ts = self._parse_timestamp(oot_start)
        
        # 檢查時間範圍
        if train_end_ts >= oot_start_ts:
            raise TimeRangeOverlap(str(train_end_ts), str(oot_start_ts))
        
        # 排序資料
        df_sorted = self._ensure_sorted(df, timestamp_col)
        
        # 轉換時間欄位為可比較格式
        df_sorted['_ts_parsed'] = df_sorted[timestamp_col].apply(self._parse_timestamp)
        
        # 切分資料
        train_val_mask = df_sorted['_ts_parsed'] <= train_end_ts
        oot_mask = df_sorted['_ts_parsed'] >= oot_start_ts
        
        train_val_df = df_sorted[train_val_mask].drop(columns=['_ts_parsed']).copy()
        oot_df = df_sorted[oot_mask].drop(columns=['_ts_parsed']).copy()
        
        # 檢查樣本數
        if len(oot_df) < self.min_oot_samples:
            raise InsufficientOOTSamples(len(oot_df), self.min_oot_samples)
        
        # 切分訓練/驗證集
        validation_df = None
        validation_period = None
        
        if validation_ratio > 0:
            val_size = int(len(train_val_df) * validation_ratio)
            if val_size > 0:
                train_df = train_val_df.iloc[:-val_size].copy()
                validation_df = train_val_df.iloc[-val_size:].copy()
                validation_period = self._calculate_period_info(
                    validation_df, timestamp_col, label_col
                )
            else:
                train_df = train_val_df
        else:
            train_df = train_val_df
        
        # 檢查訓練集樣本數
        if len(train_df) < self.min_train_samples:
            raise InsufficientTrainSamples(len(train_df), self.min_train_samples)
        
        # 計算區間資訊
        train_period = self._calculate_period_info(train_df, timestamp_col, label_col)
        oot_period = self._calculate_period_info(oot_df, timestamp_col, label_col)
        
        self.logger.info(
            f"時間切分完成 - 訓練: {train_period.samples}, "
            f"驗證: {validation_period.samples if validation_period else 0}, "
            f"OOT: {oot_period.samples}"
        )
        
        return SplitResult(
            train_df=train_df,
            validation_df=validation_df,
            oot_df=oot_df,
            train_period=train_period,
            validation_period=validation_period,
            oot_period=oot_period,
            timestamp_column=timestamp_col,
            split_method="manual",
            random_seed=self.random_seed
        )
    
    def auto_split(
        self,
        df: pd.DataFrame,
        oot_ratio: float = 0.2,
        validation_ratio: float = 0.1,
        timestamp_col: Optional[str] = None,
        label_col: Optional[str] = None
    ) -> SplitResult:
        """
        自動切分資料（依比例）
        
        Args:
            df: 資料 DataFrame
            oot_ratio: OOT 資料比例（0-1）
            validation_ratio: 驗證集比例（從訓練集末端抽取，0-1）
            timestamp_col: 時間欄位名稱（None 時自動偵測）
            label_col: 標籤欄位名稱（用於計算正樣本率）
            
        Returns:
            SplitResult 物件
        """
        # 驗證比例
        if oot_ratio <= 0 or oot_ratio >= 1:
            raise TimeSplitterError(
                TimeSplitterErrorType.INVALID_RATIO,
                f"OOT 比例必須在 (0, 1) 之間，目前: {oot_ratio}"
            )
        
        if validation_ratio < 0 or validation_ratio >= 1:
            raise TimeSplitterError(
                TimeSplitterErrorType.INVALID_RATIO,
                f"驗證集比例必須在 [0, 1) 之間，目前: {validation_ratio}"
            )
        
        # 偵測時間欄位
        if timestamp_col is None:
            timestamp_col = self.detect_timestamp_column(df)
            if timestamp_col is None:
                raise TimestampColumnNotFound(df.columns.tolist())
        
        if timestamp_col not in df.columns:
            raise TimestampColumnNotFound(df.columns.tolist())
        
        self.logger.info(
            f"開始自動切分 - OOT 比例: {oot_ratio:.1%}, "
            f"驗證比例: {validation_ratio:.1%}"
        )
        
        # 排序資料
        df_sorted = self._ensure_sorted(df, timestamp_col)
        
        # 計算切分點
        n_samples = len(df_sorted)
        oot_start_idx = int(n_samples * (1 - oot_ratio))
        
        # 計算時間切分點
        train_end_time = df_sorted[timestamp_col].iloc[oot_start_idx - 1]
        oot_start_time = df_sorted[timestamp_col].iloc[oot_start_idx]
        
        # 使用 split_by_time 進行切分
        return self.split_by_time(
            df=df_sorted,
            train_end=str(train_end_time),
            oot_start=str(oot_start_time),
            timestamp_col=timestamp_col,
            validation_ratio=validation_ratio,
            label_col=label_col
        )
    
    def validate_no_overlap(
        self,
        train_df: pd.DataFrame,
        oot_df: pd.DataFrame,
        timestamp_col: str
    ) -> Tuple[bool, Optional[str]]:
        """
        驗證訓練集和 OOT 之間無時間重疊
        
        Args:
            train_df: 訓練集 DataFrame
            oot_df: OOT DataFrame
            timestamp_col: 時間欄位名稱
            
        Returns:
            (是否無重疊, 錯誤訊息)
        """
        if len(train_df) == 0 or len(oot_df) == 0:
            return True, None
        
        train_max = self._parse_timestamp(train_df[timestamp_col].max())
        oot_min = self._parse_timestamp(oot_df[timestamp_col].min())
        
        if train_max >= oot_min:
            error_msg = (
                f"時間重疊: 訓練集最大時間 ({train_max}) >= "
                f"OOT 最小時間 ({oot_min})"
            )
            return False, error_msg
        
        return True, None


# ==================== Purged Time Series Split ====================

class PurgedTimeSeriesSplit:
    """
    Purged Time Series Split - 去汙染時間序列交叉驗證
    
    在每個 fold 之間移除可能的資訊洩漏：
    - Purge: 移除訓練集末端的「污染樣本」（因為標籤可能使用未來資料計算）
    - Embargo: 在訓練集和驗證集之間留緩衝區
    """
    
    def __init__(
        self,
        n_splits: int = 5,
        purge_gap: int = 5,
        embargo_pct: float = 0.01
    ):
        """
        初始化 Purged Time Series Split
        
        Args:
            n_splits: 切分數量
            purge_gap: 標籤用到未來幾根 K 線（移除訓練集末端）
            embargo_pct: 驗證集開頭的緩衝比例
        """
        self.n_splits = n_splits
        self.purge_gap = purge_gap
        self.embargo_pct = embargo_pct
        self.logger = logger
    
    def split(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Optional[np.ndarray] = None,
        groups: Optional[np.ndarray] = None
    ):
        """
        產生 Purged Time Series Split 的索引
        
        Args:
            X: 特徵矩陣
            y: 標籤（可選）
            groups: 群組（未使用）
            
        Yields:
            (train_indices, val_indices) 元組
        """
        from sklearn.model_selection import TimeSeriesSplit
        
        n_samples = len(X)
        tscv = TimeSeriesSplit(n_splits=self.n_splits)
        
        for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(X)):
            original_train_size = len(train_idx)
            original_val_size = len(val_idx)
            
            # Purge: 移除訓練集末端
            if self.purge_gap > 0 and len(train_idx) > self.purge_gap:
                train_idx = train_idx[:-self.purge_gap]
            
            # Embargo: 移除驗證集開頭
            if self.embargo_pct > 0:
                embargo_size = max(1, int(len(val_idx) * self.embargo_pct))
                if embargo_size < len(val_idx):
                    val_idx = val_idx[embargo_size:]
            
            # 檢查是否有足夠樣本
            if len(train_idx) < 10:
                self.logger.warning(
                    f"Fold {fold_idx + 1}: 訓練集太小 ({len(train_idx)})，跳過"
                )
                continue
            
            if len(val_idx) < 5:
                self.logger.warning(
                    f"Fold {fold_idx + 1}: 驗證集太小 ({len(val_idx)})，跳過"
                )
                continue
            
            self.logger.info(
                f"Fold {fold_idx + 1}/{self.n_splits} - "
                f"訓練: {original_train_size} → {len(train_idx)} (purge: -{self.purge_gap}), "
                f"驗證: {original_val_size} → {len(val_idx)}"
            )
            
            yield train_idx, val_idx
    
    def get_n_splits(
        self,
        X: Optional[np.ndarray] = None,
        y: Optional[np.ndarray] = None,
        groups: Optional[np.ndarray] = None
    ) -> int:
        """返回切分數量"""
        return self.n_splits

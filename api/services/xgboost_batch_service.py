"""
XGBoost Batch Analysis Service - XGBoost 批量分析服務

功能：
1. 從 HDF5 讀取 K 線數據
2. 根據用戶指標配置計算特徵
3. 使用 cases.json 的案例時間戳作為 label
4. 對所有案例執行 XGBoost 訓練和分析

正確的數據流程：
K-line (HDF5) + Indicator Config (用戶輸入)
    ↓ 計算特徵
Feature Data + Labels (正例/反例)
    ↓
XGBoost Training 在所有案例上

Author: AI Agent
Date: 2026-01-13
"""

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import logging
from pathlib import Path

import pandas as pd
import numpy as np

from api.core.config import settings
from api.core.logging import get_logger
from api.utils.case_storage import get_case_storage_manager
from api.utils.json_serializer import sanitize_for_json
from momentum.core.contracts import FeatureNotFoundError
from momentum.FeatureEngineering.consumer_gate import (
    TrainingReadError,
    intersect_columns_without_masking,
)
from momentum.factories import (
    create_binance_provider,
    create_bootstrap_estimator,
    create_cross_symbol_validator,
    create_expectancy_calculator,
    create_feature_extractor,
    create_feature_library,
    create_kline_download_service,
    create_kline_storage_manager,
    create_model_storage,
    create_pattern_extractor,
    create_regime_analyzer,
    create_strategy_params,
    create_xgboost_analyzer,
    create_market_config,
    create_model_trainer,
)

logger = get_logger(__name__)

@dataclass
class _XGBoostTaskResult:
    task_id: str
    predictions_df: Optional[pd.DataFrame]
    calibration_curve: Optional[Dict]
    pr_curve: Optional[Dict]
    created_at: datetime


class _XGBoostTaskCache:
    """Minimal task cache to avoid cross-service dependency."""

    _cache: Dict[str, _XGBoostTaskResult] = {}

    def store_result(
        self,
        task_id: str,
        predictions_df: Optional[pd.DataFrame],
        calibration_curve: Optional[Dict],
        pr_curve: Optional[Dict],
    ) -> None:
        self._cache[task_id] = _XGBoostTaskResult(
            task_id=task_id,
            predictions_df=predictions_df,
            calibration_curve=calibration_curve,
            pr_curve=pr_curve,
            created_at=datetime.utcnow(),
        )

    def get_result(self, task_id: str) -> Optional[_XGBoostTaskResult]:
        return self._cache.get(task_id)


class BatchTaskManager:
    """批量任務狀態管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, Dict] = {}
    
    def create_task(self, task_id: str, total_cases: int):
        """建立新任務"""
        self.tasks[task_id] = {
            'status': 'running',
            'created_at': datetime.now().isoformat(),
            'progress': 0,
            'current_step': '初始化',
            'total_cases': total_cases,
            'processed_cases': 0,
            'message': '任務已啟動',
            'result': None,
            'error': None
        }
    
    def update_progress(self, task_id: str, progress: int, step: str, message: str):
        """更新進度"""
        if task_id in self.tasks:
            self.tasks[task_id]['progress'] = progress
            self.tasks[task_id]['current_step'] = step
            self.tasks[task_id]['message'] = message
    
    def update_cases_processed(self, task_id: str, processed: int):
        """更新處理案例數"""
        if task_id in self.tasks:
            self.tasks[task_id]['processed_cases'] = processed
    
    def update_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """更新狀態"""
        if task_id in self.tasks:
            self.tasks[task_id]['status'] = status
            if result:
                self.tasks[task_id]['result'] = result
            if error:
                self.tasks[task_id]['error'] = error
            self.tasks[task_id]['completed_at'] = datetime.now().isoformat()
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """獲取任務狀態"""
        return self.tasks.get(task_id)


class XGBoostBatchService:
    """
    XGBoost 批量分析服務
    
    正確流程：
    1. 讀取 K 線數據（HDF5）
    2. 根據指標配置計算特徵
    3. 為每個案例時間點提取特徵
    4. 使用案例的 positive_case 作為 label
    5. XGBoost 訓練和分析
    """
    
    def __init__(self):
        self.task_manager = BatchTaskManager()
        self.case_storage = get_case_storage_manager()
        self.kline_storage_manager = create_kline_storage_manager(
            cache_dir=str(settings.kline_cache_dir)
        )
        self.kline_download_service = create_kline_download_service(
            storage_manager=self.kline_storage_manager
        )
        try:
            self.kline_download_service.registry.register(
                "binance",
                create_binance_provider(),
            )
        except Exception:
            logger.debug("Binance provider already registered", exc_info=True)
        self.feature_extractor = create_feature_extractor()
        self._feature_library = create_feature_library()
        self.xgboost_analyzer = create_xgboost_analyzer()
        self.pattern_extractor = create_pattern_extractor()
        self.model_storage = create_model_storage()
        self.expectancy_calculator = create_expectancy_calculator()
        self.bootstrap_estimator = create_bootstrap_estimator()
        self.cross_symbol_validator = create_cross_symbol_validator()
        self.logger = logger
        self.task_cache = _XGBoostTaskCache()
    
    def get_case_summary(self, symbol: Optional[str] = None, timeframe: Optional[str] = None) -> Dict:
        """
        獲取案例摘要
        
        Args:
            symbol: 過濾特定交易對
            timeframe: 過濾特定時間週期
            
        Returns:
            案例統計資訊
        """
        stats = self.case_storage.get_statistics()
        cases = stats.cases
        
        # 過濾
        if symbol:
            cases = [c for c in cases if c.symbol == symbol]
        if timeframe:
            cases = [c for c in cases if c.timeframe == timeframe]
        
        positive_count = sum(1 for c in cases if c.positive_case == 1)
        negative_count = sum(1 for c in cases if c.positive_case == 0)
        
        # 提取唯一值
        symbols = sorted(set(c.symbol for c in cases))
        timeframes = sorted(set(c.timeframe for c in cases))
        
        return {
            'total_cases': len(cases),
            'positive_cases': positive_count,
            'negative_cases': negative_count,
            'symbols': symbols,
            'timeframes': timeframes
        }
    
    async def start_batch_analysis(
        self,
        symbols: List[str],
        timeframe: str,
        indicators: List[Dict],
        selected_features: Optional[List[str]] = None,
        lookback_bars: int = 200,
        sequence_length: Optional[int] = None,
        sequence_feature_mode: str = "aggregate",
        sequence_stride: int = 1,
        aggregation_methods: Optional[List[str]] = None,
        multi_scale_windows: Optional[List[int]] = None,
        time_series_split: bool = True,
        purge_gap: Optional[int] = None,
        embargo_pct: Optional[float] = None,
        xgboost_params: Optional[Dict] = None,
        engine: str = "xgboost",
        model_params: Optional[Dict] = None,
        run_comparison: bool = False,
        cv_folds: int = 5,
        top_n_rules: int = 10,
        min_support: int = 10
    ) -> Dict:
        """
        啟動批量 XGBoost 分析（支援多標的跨商品訓練）
        
        Args:
            symbols: 交易對列表（如 ['ETHUSDT', 'BTCUSDT']），合併所有案例訓練單一模型
            timeframe: K線時間週期（用於計算指標，與案例搜尋週期無關）
            indicators: 指標配置列表
            selected_features: 指定訓練因子（可選）
            lookback_bars: 每個案例回看 K 線數量
            sequence_length: 序列特徵長度（TO 前 N 根）
            sequence_feature_mode: 序列特徵模式（aggregate 或 flatten）
            sequence_stride: 序列抽樣步長
            aggregation_methods: 序列彙總方法
            multi_scale_windows: 多時間尺度窗口
            time_series_split: 是否使用時間序列切分
            purge_gap: 標籤用到未來幾根 K 線（Purged CV）
            embargo_pct: Embargo 緩衝比例
            xgboost_params: XGBoost 參數
            engine: 模型引擎（xgboost / lightgbm）
            model_params: 通用模型參數（優先於 xgboost_params）
            run_comparison: 是否執行雙引擎對比（目前僅保留欄位）
            cv_folds: 交叉驗證折數
            top_n_rules: 提取前 N 條規則
            min_support: 最小支持度
            
        Returns:
            任務 ID 和狀態
        """
        # 獲取所有選中標的的案例並合併（跨商品訓練）
        all_cases = []
        for symbol in symbols:
            symbol_cases = self.case_storage.get_cases_by_symbol(symbol)
            if symbol_cases:
                all_cases.extend(symbol_cases)
        
        if not all_cases:
            raise ValueError(f"找不到這些標的的案例: {', '.join(symbols)}")
        
        task_id = str(uuid.uuid4())
        
        self.logger.info(
            f"啟動批量 XGBoost 分析 - task_id: {task_id}, "
            f"symbols: {', '.join(symbols)}, timeframe: {timeframe}, "
            f"案例數: {len(all_cases)}, 指標數: {len(indicators)}, "
            f"指定因子數: {len(selected_features or [])}"
        )
        
        # 建立任務
        self.task_manager.create_task(task_id, len(all_cases))
        
        # 在背景執行分析
        asyncio.create_task(
            self._run_batch_analysis(
                task_id=task_id,
                symbols=symbols,
                timeframe=timeframe,
                cases=all_cases,
                indicators=indicators,
                selected_features=selected_features,
                lookback_bars=lookback_bars,
                sequence_length=sequence_length,
                sequence_feature_mode=sequence_feature_mode,
                sequence_stride=sequence_stride,
                aggregation_methods=aggregation_methods,
                multi_scale_windows=multi_scale_windows,
                time_series_split=time_series_split,
                purge_gap=purge_gap,
                embargo_pct=embargo_pct,
                xgboost_params=xgboost_params,
                engine=engine,
                model_params=model_params,
                run_comparison=run_comparison,
                cv_folds=cv_folds,
                top_n_rules=top_n_rules,
                min_support=min_support
            )
        )
        
        return {
            'task_id': task_id,
            'message': f'XGBoost 批量分析已啟動，共 {len(all_cases)} 個案例（{len(symbols)} 個標的）',
            'status': 'running',
            'total_cases': len(all_cases),
            'symbols': symbols
        }
    
    async def _run_batch_analysis(
        self,
        task_id: str,
        symbols: List[str],
        timeframe: str,
        cases: List,
        indicators: List[Dict],
        selected_features: Optional[List[str]],
        lookback_bars: int,
        sequence_length: Optional[int],
        sequence_feature_mode: str,
        sequence_stride: int,
        aggregation_methods: Optional[List[str]],
        multi_scale_windows: Optional[List[int]],
        time_series_split: bool,
        purge_gap: Optional[int],
        embargo_pct: Optional[float],
        xgboost_params: Optional[Dict],
        engine: str,
        model_params: Optional[Dict],
        run_comparison: bool,
        cv_folds: int,
        top_n_rules: int,
        min_support: int
    ):
        """執行批量分析（背景任務，支援多標的跨商品訓練）"""
        try:
            normalized_selected_features = [
                name.strip()
                for name in (selected_features or [])
                if isinstance(name, str) and name.strip()
            ]

            # ===== Step 1: 計算時間範圍 =====
            self.task_manager.update_progress(task_id, 5, '計算時間範圍', '分析案例時間範圍...')
            
            # 確保 timestamp 是整數（處理可能的 datetime 物件）
            timestamps = []
            for c in cases:
                if isinstance(c.timestamp, int):
                    timestamps.append(c.timestamp)
                elif isinstance(c.timestamp, datetime):
                    timestamps.append(int(c.timestamp.timestamp()))
                else:
                    self.logger.warning(f"Invalid timestamp type for case {c.case_id}: {type(c.timestamp)}")
                    continue
            
            if not timestamps:
                raise ValueError("沒有有效的時間戳")
            
            min_ts = min(timestamps)
            max_ts = max(timestamps)

            if sequence_length is not None:
                if sequence_length < 1:
                    raise ValueError("sequence_length 必須大於 0")
                if sequence_stride < 1:
                    raise ValueError("sequence_stride 必須大於 0")
                if lookback_bars < sequence_length:
                    raise ValueError("lookback_bars 必須大於等於 sequence_length")
                if sequence_feature_mode not in {"aggregate", "flatten"}:
                    raise ValueError("sequence_feature_mode 只支援 aggregate 或 flatten")

                if aggregation_methods is None:
                    aggregation_methods = ["mean", "std", "min", "max", "last", "slope"]

                if multi_scale_windows:
                    invalid_windows = [w for w in multi_scale_windows if w < 1 or w > sequence_length]
                    if invalid_windows:
                        raise ValueError("multi_scale_windows 必須介於 1 到 sequence_length 之間")
            
            # 計算需要的 K 線時間範圍（含 warmup）
            timeframe_seconds = self._get_timeframe_seconds(timeframe)
            start_ts = min_ts - (lookback_bars * timeframe_seconds)
            end_ts = max_ts + (10 * timeframe_seconds)  # 多取 10 根
            
            self.logger.info(
                f"時間範圍計算完成 - 最早案例: {min_ts}, 最晚案例: {max_ts}, "
                f"K 線範圍: {start_ts} ~ {end_ts}"
            )
            
            # ===== Step 2: 讀取所有標的的 K 線數據 =====
            self.task_manager.update_progress(task_id, 10, '讀取 K 線', f'從 HDF5 讀取 {len(symbols)} 個標的的 K 線數據...')
            
            # 將時間戳轉換為 datetime 物件（KlineDataService 需要 datetime）
            from datetime import datetime
            start_dt = datetime.utcfromtimestamp(start_ts)
            end_dt = datetime.utcfromtimestamp(end_ts)
            
            # 合併所有標的的 K 線數據（字典：symbol -> DataFrame）
            all_kline_data = {}
            for sym in symbols:
                kline_df = await asyncio.to_thread(
                    self._get_kline_data,
                    symbol=sym,
                    timeframe=timeframe,
                    start_time=start_dt,
                    end_time=end_dt,
                )
                
                if kline_df is None or kline_df.empty:
                    self.logger.warning(f"無法獲取 {sym} {timeframe} 的 K 線數據，跳過此標的")
                    continue
                
                all_kline_data[sym] = kline_df
                self.logger.info(f"{sym} K 線數據載入完成 - 行數: {len(kline_df)}")
            
            if not all_kline_data:
                raise ValueError(f"無法獲取任何標的的 K 線數據: {', '.join(symbols)}")
            
            self.logger.info(f"所有 K 線數據載入完成 - 標的數: {len(all_kline_data)}")
            
            # ===== Step 3: 為每個標的計算指標特徵 =====
            self.task_manager.update_progress(task_id, 25, '計算特徵', '根據指標配置為所有標的計算特徵...')
            
            # 字典：symbol -> 該標的的特徵 DataFrame
            all_symbol_features = {}
            shared_feature_names = None  # 第一個標的的特徵名稱（應該所有標的相同）
            
            for sym, kline_df in all_kline_data.items():
                self.logger.info(f"開始為 {sym} 計算特徵...")

                try:
                    library_df = self._feature_library.load_for_training(sym, timeframe)
                    if "timestamp" not in library_df.columns:
                        library_df = library_df.copy()
                        if isinstance(library_df.index, pd.DatetimeIndex):
                            library_df["timestamp"] = (library_df.index.astype("int64") // 10**6).astype(int)
                        else:
                            library_df["timestamp"] = pd.to_numeric(library_df.index, errors="coerce")
                    numeric_columns = library_df.select_dtypes(include=[np.number]).columns.tolist()
                    candidate_columns = [
                        column_name
                        for column_name in numeric_columns
                        if column_name not in {"label", "open_time", "timestamp"}
                    ]

                    if normalized_selected_features:
                        selected_in_library = [
                            column_name
                            for column_name in normalized_selected_features
                            if column_name in candidate_columns
                        ]
                        if not selected_in_library:
                            self.logger.warning(
                                "%s/%s 找不到指定因子，跳過此標的（requested=%s）",
                                sym,
                                timeframe,
                                len(normalized_selected_features),
                            )
                            continue

                        keep_columns = [
                            column_name
                            for column_name in ["timestamp", "open_time", "label"]
                            if column_name in library_df.columns
                        ] + selected_in_library
                        library_df = library_df[keep_columns].copy()
                        candidate_columns = selected_in_library

                    all_symbol_features[sym] = library_df.copy()

                    if shared_feature_names is None:
                        shared_feature_names = candidate_columns
                    else:
                        shared_feature_names = intersect_columns_without_masking(
                            [shared_feature_names, candidate_columns],
                            error_type=TrainingReadError,
                        )

                    self.logger.info("從 FeatureLibrary 載入 %s/%s 預計算特徵", sym, timeframe)
                    continue
                except TrainingReadError:
                    raise
                except FeatureNotFoundError:
                    self.logger.info("FeatureLibrary 無資料，改用即時計算 %s/%s", sym, timeframe)
                except Exception as exc:
                    self.logger.warning(
                        "FeatureLibrary 載入失敗，改用即時計算 %s/%s: %s",
                        sym,
                        timeframe,
                        exc,
                    )
                
                sym_features = []
                sym_feature_names = []
                
                for indicator_config in indicators:
                    strategy_params = create_strategy_params(
                        strategy_type=indicator_config['indicator'],
                        params=indicator_config['params'],
                        data_source=indicator_config.get('data_source', 'close'),
                    )
                    
                    try:
                        features_df, feature_names = self.feature_extractor.extract_features_from_strategy(
                            df=kline_df.copy(),
                            strategy_params=strategy_params,
                            include_basic_features=(len(sym_feature_names) == 0)  # 只在第一個指標包含基本特徵
                        )
                        
                        # 收集新特徵（排除已有的）
                        new_features = [f for f in feature_names if f not in sym_feature_names]
                        sym_feature_names.extend(new_features)
                        
                        # 合併特徵
                        if not sym_features:
                            sym_features = features_df
                        else:
                            # 只添加新欄位
                            for col in new_features:
                                if col in features_df.columns:
                                    sym_features[col] = features_df[col]
                        
                    except Exception as e:
                        self.logger.error(f"{sym} 指標 {indicator_config['indicator']} 特徵提取失敗: {e}")
                        continue
                
                if not sym_feature_names:
                    self.logger.warning(f"{sym} 未能提取任何特徵，跳過")
                    continue
                
                all_symbol_features[sym] = sym_features
                
                # 第一個標的設定 shared_feature_names
                if shared_feature_names is None:
                    shared_feature_names = sym_feature_names
                
                self.logger.info(f"{sym} 特徵計算完成 - 總共 {len(sym_feature_names)} 個特徵")
            
            if not all_symbol_features:
                raise ValueError("未能為任何標的提取特徵")

            if not shared_feature_names:
                raise ValueError("找不到可用特徵，請檢查 selected_features 或指標設定")
            
            self.logger.info(f"所有標的特徵計算完成 - 共 {len(all_symbol_features)} 個標的，{len(shared_feature_names)} 個特徵")
            
            # ===== Step 4: 為每個案例提取特徵和標籤 =====
            self.task_manager.update_progress(task_id, 45, '提取案例特徵', f'為 {len(cases)} 個案例提取特徵...')
            
            X_list = []
            y_list = []
            case_timestamps = []
            case_ids = []
            valid_cases = []
            valid_cases_count = 0
            sequence_feature_names: Optional[List[str]] = None
            
            # 為每個標的的特徵 DataFrame 準備 timestamp_sec 欄位
            for sym, features_df in all_symbol_features.items():
                if 'timestamp' not in features_df.columns:
                    raise ValueError(f"{sym} 特徵 DataFrame 缺少 timestamp 欄位")
                
                # 檢查 timestamp 的單位（毫秒 > 10^12，秒 < 10^12）
                sample_ts = features_df['timestamp'].iloc[0]
                if sample_ts > 10**12:
                    # 毫秒級時間戳，需要除以 1000 轉換為秒
                    features_df['timestamp_sec'] = (features_df['timestamp'] // 1000).astype(int)
                else:
                    # 已經是秒級時間戳，直接使用
                    features_df['timestamp_sec'] = features_df['timestamp'].astype(int)
                
                features_df.sort_values('timestamp_sec', inplace=True)
                features_df.reset_index(drop=True, inplace=True)
                all_symbol_features[sym] = features_df
            
            self.logger.info(f"所有標的的 timestamp 處理完成")
            
            for i, case in enumerate(cases):
                # 獲取該案例對應的標的特徵
                case_symbol = case.symbol
                if case_symbol not in all_symbol_features:
                    self.logger.warning(f"案例 {case.case_id} 的標的 {case_symbol} 沒有特徵數據，跳過")
                    continue
                
                features_df = all_symbol_features[case_symbol]
                
                # 確保 case_ts 是整數
                if isinstance(case.timestamp, int):
                    case_ts = case.timestamp
                elif isinstance(case.timestamp, datetime):
                    case_ts = int(case.timestamp.timestamp())
                else:
                    self.logger.warning(f"Invalid timestamp for case {case.case_id}")
                    continue
                
                # 找到對應的行
                idx = features_df[features_df['timestamp_sec'] == case_ts].index
                
                if len(idx) == 0:
                    self.logger.warning(f"案例 {case.case_id} 找不到對應的 K 線數據")
                    continue
                
                row_idx = idx[0]
                
                if sequence_length is None:
                    # 提取特徵（取該時間點的特徵值）
                    feature_values = features_df.loc[row_idx, shared_feature_names].values
                    feature_names = shared_feature_names
                else:
                    sequence_result = self._build_sequence_features(
                        all_features=features_df,
                        row_idx=row_idx,
                        feature_names=shared_feature_names,
                        sequence_length=sequence_length,
                        sequence_feature_mode=sequence_feature_mode,
                        sequence_stride=sequence_stride,
                        aggregation_methods=aggregation_methods,
                        multi_scale_windows=multi_scale_windows
                    )
                    if sequence_result is None:
                        continue
                    feature_values, feature_names = sequence_result
                    if sequence_feature_names is None:
                        sequence_feature_names = feature_names
                    else:
                        feature_names = sequence_feature_names
                
                # 檢查是否有 NaN
                if np.isnan(feature_values).any():
                    self.logger.warning(f"案例 {case.case_id} 特徵包含 NaN，跳過")
                    continue
                
                X_list.append(feature_values)
                y_list.append(case.positive_case)
                case_timestamps.append(case_ts)
                case_ids.append(case.case_id)
                valid_cases.append(case)
                valid_cases_count += 1
                
                # 更新進度
                if (i + 1) % 50 == 0:
                    self.task_manager.update_cases_processed(task_id, i + 1)
            
            if valid_cases_count < 10:
                raise ValueError(f"有效案例數量不足: {valid_cases_count}")
            
            X = np.array(X_list)
            y = np.array(y_list)
            if sequence_length is not None and sequence_feature_names is None:
                raise ValueError("序列特徵生成失敗，無有效案例")
            feature_names = sequence_feature_names or shared_feature_names

            if sequence_length is not None:
                if sequence_feature_mode == "flatten" and not any("_t-" in name for name in feature_names):
                    raise ValueError("序列特徵未生效：展平模式特徵名稱缺少 _t- 後綴")
                if sequence_feature_mode == "aggregate" and not any("_w" in name for name in feature_names):
                    raise ValueError("序列特徵未生效：彙總模式特徵名稱缺少 _w 後綴")
            
            positive_count = sum(y)
            negative_count = len(y) - positive_count
            
            self.logger.info(
                f"案例特徵提取完成 - 有效案例: {valid_cases_count}, "
                f"正例: {positive_count}, 反例: {negative_count}"
            )
            
            # 檢查標籤分佈是否適合二分類
            if positive_count == 0:
                raise ValueError(
                    f"所有案例都是負例（反例），無法訓練二分類模型。"
                    f"請檢查案例搜尋條件或選擇其他標的。"
                )
            if negative_count == 0:
                raise ValueError(
                    f"所有案例都是正例（盈利），無法訓練二分類模型。"
                    f"建議方案："
                    f"\n1. 增加更多標的以獲得更多樣的案例"
                    f"\n2. 調整案例搜尋的正例判定條件（未來漲幅閾值）"
                    f"\n3. 使用其他標的的案例"
                )

            analysis_engine = (engine or "xgboost").lower().strip()
            if analysis_engine == "both":
                self.logger.warning("批量分析收到 engine=both，將先以 xgboost 執行單引擎流程")
                analysis_engine = "xgboost"
            if analysis_engine not in {"xgboost", "lightgbm"}:
                raise ValueError(f"不支援的引擎: {engine}")

            analyzer = (
                self.xgboost_analyzer
                if analysis_engine == "xgboost"
                else create_model_trainer("lightgbm", config=model_params)
            )
            effective_model_params = model_params or xgboost_params
            
            # ===== Step 5: 訓練 XGBoost =====
            self.task_manager.update_progress(task_id, 60, '訓練模型', f'{analysis_engine} 模型訓練中...')
            
            performance = await asyncio.to_thread(
                analyzer.train_model,
                X, y, feature_names, 10, 0.2, effective_model_params, cv_folds,
                time_series_split, case_timestamps, purge_gap, embargo_pct
            )
            
            self.logger.info(
                f"模型訓練完成 - in_sample_train_auc: {performance.in_sample_train_auc:.4f}, "
                f"CV AUC: {performance.cv_auc_mean:.4f}"
            )
            
            # ===== Step 6: 計算特徵重要性 =====
            self.task_manager.update_progress(task_id, 75, '分析特徵', '計算特徵重要性...')
            
            feature_importance = await asyncio.to_thread(
                analyzer.calculate_feature_importance,
                feature_names
            )

            feature_importance_all = await asyncio.to_thread(
                analyzer.get_all_importance_types,
                feature_names
            )
            
            # LA-2 B2/B3：先建 train/OOT plan，再 train-mask 抽規則
            import pickle
            from momentum.Analysis.eval_scope_utils import build_service_oot_bundle
            from momentum.core.contracts import SplitPlan, canonical_split_plan_hash

            try:
                model_artifact = pickle.dumps(analyzer.model)
            except Exception:  # noqa: BLE001
                model_artifact = b"xgb-batch-artifact"
            oot_bundle = build_service_oot_bundle(
                n_samples=len(y),
                model_artifact=model_artifact,
                trusted_issuer="xgboost_batch_service",
                oot_ratio=0.2,
                horizon=1,
                embargo=int(embargo_pct or 0) if embargo_pct else 0,
                purge_gap=int(purge_gap or 0) if purge_gap else 0,
                symbol=",".join(symbols) if symbols else None,
                base_universe_hash=f"xgb_batch:{timeframe}:{len(y)}",
            )
            has_oot_held_out = bool(oot_bundle["has_oot_held_out"])
            oot_receipt = oot_bundle["oot_receipt"]
            oot_idx = oot_bundle["oot_idx"]
            train_plan = oot_bundle.get("train_plan")
            eval_plan = oot_bundle.get("eval_plan")
            if train_plan is None:
                train_plan = SplitPlan(
                    split_label="train",
                    index_kind="positional",
                    row_index=np.arange(len(y), dtype=int),
                    time_bounds=(None, None),
                    purge_gap=0,
                    embargo=0,
                    purge_semantic="rows",
                    expected_freq=None,
                    base_universe_hash=f"xgb_batch:{timeframe}:{len(y)}",
                    symbol=",".join(symbols) if symbols else None,
                )

            # ===== Step 7: 提取決策規則（train-mask）=====
            self.task_manager.update_progress(task_id, 85, '提取規則', '提取決策規則...')
            
            if analysis_engine == "lightgbm":
                # U15：LGBM 跳過 pattern 晉升（記錄性 asymmetry，禁順手接線）
                rules = []
            else:
                expected_hash = canonical_split_plan_hash(train_plan)
                rules = await asyncio.to_thread(
                    self.pattern_extractor.extract_decision_rules,
                    analyzer.model,
                    X,
                    y,
                    feature_names,
                    top_n_rules,
                    min_support,
                    split=train_plan,
                    expected_plan_hash=expected_hash,
                    oot_split=eval_plan,
                )

            predictions_output = await asyncio.to_thread(
                analyzer.get_predictions,
                X, y, case_ids
            )

            if hasattr(predictions_output, 'predictions'):
                y_pred_proba = np.array([p.predicted_proba for p in predictions_output.predictions], dtype=float)
                predictions_payload = predictions_output.to_dict() if hasattr(predictions_output, 'to_dict') else {
                    'predictions': [p.__dict__ for p in predictions_output.predictions],
                    'proba_summary': None,
                }
            else:
                raw_proba = np.asarray(getattr(predictions_output, 'y_pred_proba', []), dtype=float)
                if raw_proba.ndim == 2 and raw_proba.shape[1] >= 2:
                    y_pred_proba = raw_proba[:, 1]
                else:
                    y_pred_proba = raw_proba.reshape(-1)
                bins, counts = np.linspace(0.0, 1.0, 6), None
                if y_pred_proba.size > 0:
                    counts, _ = np.histogram(y_pred_proba, bins=bins)
                predictions_payload = {
                    'predictions': [
                        {
                            'case_id': case_ids[idx],
                            'y_true': int(y[idx]),
                            'predicted_proba': float(y_pred_proba[idx]),
                        }
                        for idx in range(len(y_pred_proba))
                    ],
                    'proba_summary': {
                        'mean': float(np.mean(y_pred_proba)) if y_pred_proba.size else 0.0,
                        'std': float(np.std(y_pred_proba)) if y_pred_proba.size else 0.0,
                        'bins': {
                            f"{bins[i]:.1f}-{bins[i + 1]:.1f}": int(counts[i])
                            for i in range(len(bins) - 1)
                        } if counts is not None else {},
                        'min': float(np.min(y_pred_proba)) if y_pred_proba.size else 0.0,
                        'max': float(np.max(y_pred_proba)) if y_pred_proba.size else 0.0,
                    },
                }

            precision_at_k = None
            expectancy = None
            bootstrap_ci = None
            price_changes = self._resolve_case_price_changes(valid_cases)
            if has_oot_held_out and oot_idx is not None and len(oot_idx) > 0:
                if isinstance(X, pd.DataFrame):
                    X_oot = X.iloc[oot_idx]
                else:
                    X_oot = X[oot_idx]
                y_oot = np.asarray(y)[oot_idx]
                y_pred_oot = np.asarray(y_pred_proba)[oot_idx]

                precision_at_k_result = await asyncio.to_thread(
                    analyzer.calculate_precision_at_k,
                    X_oot, y_oot
                )
                recommended = analyzer.recommend_k(
                    y_true=y_oot,
                    y_pred_proba=y_pred_oot,
                    target_precision=0.75
                )
                if hasattr(precision_at_k_result, 'to_dict'):
                    precision_at_k = {
                        **precision_at_k_result.to_dict(),
                        "recommended_k": recommended.get("recommended_k"),
                        "recommended_threshold": recommended.get("threshold"),
                        "recommended_precision": recommended.get("precision")
                    }
                else:
                    precision_at_k = {
                        "precision_at_k": {int(item.k): float(item.precision) for item in precision_at_k_result},
                        "threshold_at_k": {},
                        "sample_count_at_k": {int(item.k): int(item.n_total) for item in precision_at_k_result},
                        "recommended_k": recommended.get("recommended_k"),
                        "recommended_threshold": recommended.get("threshold"),
                        "recommended_precision": recommended.get("precision")
                    }

                if price_changes is not None:
                    pc_oot = np.asarray(price_changes)[oot_idx]
                    threshold = recommended.get("threshold") or 0.6
                    trade_returns = pc_oot[y_pred_oot >= float(threshold)]
                    expectancy_result = self.expectancy_calculator.estimate_expectancy(
                        price_changes=pc_oot,
                        predicted_proba=y_pred_oot,
                        threshold=float(threshold)
                    )
                    sharpe_proxy = self.expectancy_calculator.calculate_sharpe_proxy(
                        trade_returns if len(trade_returns) > 0 else np.array([])
                    )
                    expectancy = {
                        **expectancy_result.to_dict(),
                        "sharpe_proxy": float(sharpe_proxy) if sharpe_proxy is not None else None
                    }

                bootstrap_ci = {}
                for metric in ["auc", "pr_auc"]:
                    try:
                        ci_result = self.bootstrap_estimator.bootstrap_confidence_interval(
                            y_true=y_oot,
                            y_pred_proba=y_pred_oot,
                            metric=metric,
                            n_bootstrap=200,
                            confidence=0.9
                        )
                        bootstrap_ci[metric] = ci_result.to_dict()
                    except Exception as e:
                        self.logger.warning(f"Bootstrap {metric} 計算失敗: {str(e)}")

            # Permutation Importance
            permutation_importance = await asyncio.to_thread(
                analyzer.calculate_permutation_importance,
                X, y, 5
            )

            # Fold-level 重要性穩定性
            if analysis_engine == 'lightgbm':
                fold_importance_stability = await asyncio.to_thread(
                    analyzer.calculate_fold_importance_stability,
                    X, y, cv_folds
                )
            else:
                fold_importance_stability = await asyncio.to_thread(
                    analyzer.calculate_fold_importance_stability,
                    X, y, cv_folds, time_series_split, case_timestamps, purge_gap, embargo_pct
                )

            # 市場體制分析（若可取得 Market_Phase）
            regime_analysis = None
            market_phases = self._resolve_market_phases(valid_cases, case_timestamps)
            if market_phases:
                try:
                    analyzer = create_regime_analyzer()
                    regime_report = analyzer.analyze_by_phase(
                        y_true=y,
                        y_pred_proba=y_pred_proba,
                        market_phases=market_phases
                    )
                    regime_analysis = regime_report.to_dict()
                    self.logger.info("發現 Market_Phase 欄位，啟用體制分析")
                except Exception as e:
                    self.logger.warning(f"市場體制分析失敗: {str(e)}")

            # SHAP 取樣資料（供後續解釋使用）
            max_shap_samples = 200
            sample_size = min(len(X), max_shap_samples)
            rng = np.random.default_rng(42)
            sample_indices = rng.choice(len(X), size=sample_size, replace=False)
            sample_values = X[sample_indices]

            shap_sample = {
                "sample_size": int(sample_size),
                "feature_names": feature_names,
                "case_ids": [case_ids[i] for i in sample_indices],
                "samples": sample_values.tolist()
            }

            # 跨幣種泛化驗證（至少兩個標的）——產線路徑見 _build_cross_symbol_validation
            cross_symbol_validation = self._build_cross_symbol_validation(
                symbols=symbols,
                valid_cases=valid_cases,
                X=X,
                y=y,
            )
            
            # ===== Step 8: 儲存模型 =====
            self.task_manager.update_progress(task_id, 95, '儲存模型', '儲存分析結果...')
            
            # 多標的模型 ID 使用合併的標的名稱
            symbols_str = '_'.join(sorted(symbols))  # 例如: BTCUSDT_ETHUSDT
            model_id = f"batch_{symbols_str}_{timeframe}_{task_id[:8]}"
            model_path = await asyncio.to_thread(
                self.model_storage.save_model_to_pickle,
                model_id,
                analyzer.model,
                feature_names,
                performance.__dict__,
                effective_model_params or {},
                {
                    'task_id': task_id,
                    'engine': analysis_engine,
                    'run_comparison': run_comparison,
                    'symbols': symbols,  # 改為 symbols 列表
                    'timeframe': timeframe,
                    'total_cases': len(cases),
                    'valid_cases': valid_cases_count,
                    'indicators': indicators,
                    'cv_folds': cv_folds,
                    'sequence_length': sequence_length,
                    'sequence_feature_mode': sequence_feature_mode,
                    'sequence_stride': sequence_stride,
                    'aggregation_methods': aggregation_methods,
                    'multi_scale_windows': multi_scale_windows,
                    'time_series_split': time_series_split,
                    'purge_gap': purge_gap,
                    'embargo_pct': embargo_pct
                }
            )
            
            # ===== Step 9: 完成 =====
            prediction_meta = {
                "timestamps": case_timestamps,
                "symbols": [case.symbol for case in valid_cases],
                "actual_returns": price_changes.tolist() if price_changes is not None else None
            }

            from momentum.Analysis.eval_scope_utils import (
                apply_service_matrix_scopes,
                performance_to_scoped_dict,
            )

            # LA-2 B2 F3：has_oot_held_out 動態；有 OOT 才寫 oot_receipt
            result = {
                'symbols': symbols,  # 改為 symbols 列表
                'engine': analysis_engine,
                'run_comparison': run_comparison,
                'timeframe': timeframe,
                'total_cases': len(cases),
                'valid_cases': valid_cases_count,
                'positive_cases': int(positive_count),
                'negative_cases': int(negative_count),
                'features_generated': len(feature_names),
                'feature_names': feature_names,
                'model_performance': performance_to_scoped_dict(performance),
                'feature_importance': [fi.__dict__ for fi in feature_importance],
                'feature_importance_all': {
                    key: [fi.__dict__ for fi in values]
                    for key, values in feature_importance_all.items()
                },
                'decision_rules': [rule.to_dict() for rule in rules] if rules else [],
                'decision_rules_note': 'LightGBM 暫不支援 extract_decision_rules，已略過' if analysis_engine == 'lightgbm' else None,
                'precision_at_k': precision_at_k,
                'expectancy': expectancy,
                'bootstrap_ci': bootstrap_ci,
                'permutation_importance': permutation_importance.to_dict() if hasattr(permutation_importance, 'to_dict') else [item.__dict__ for item in permutation_importance],
                'fold_importance_stability': fold_importance_stability.to_dict() if hasattr(fold_importance_stability, 'to_dict') else [item.__dict__ for item in fold_importance_stability],
                'cross_symbol_validation': cross_symbol_validation,
                'predictions': predictions_payload,
                'prediction_meta': prediction_meta,
                'shap_sample': shap_sample,
                'calibration_curve': (
                    analyzer.last_calibration_curve.to_dict()
                    if getattr(analyzer, 'last_calibration_curve', None) else None
                ),
                'pr_curve': getattr(analyzer, 'last_pr_curve', None),
                'regime_analysis': regime_analysis,
                'model_saved': True,
                'model_path': model_path,
                'oot_receipt': oot_receipt,
                'oof_receipts': list(getattr(analyzer, 'last_oof_receipts', []) or []),
            }
            result = apply_service_matrix_scopes(result, has_oot_held_out=has_oot_held_out)

            # 清理 result 中的 numpy 類型，防止 JSON 序列化錯誤
            result = sanitize_for_json(result)
            # LA-2 B3-F1：晉升 verify 必備三份 provenance（sanitize 後再掛）
            if train_plan is not None:
                result["train_plan"] = train_plan
            if eval_plan is not None:
                result["eval_plan"] = eval_plan
            result["model_artifact"] = model_artifact
            
            try:
                predictions_df = pd.DataFrame({
                    "case_id": case_ids,
                    "y_true": y.tolist(),
                    "predicted_proba": y_pred_proba.tolist(),
                    "timestamp": case_timestamps,
                    "symbol": [case.symbol for case in valid_cases],
                    "actual_return": price_changes.tolist() if price_changes is not None else [None] * len(case_ids)
                })
            except Exception as e:
                self.logger.warning(f"建立 predictions_df 失敗: {str(e)}")
                predictions_df = None

            self.task_cache.store_result(
                task_id=task_id,
                predictions_df=predictions_df,
                calibration_curve=result.get('calibration_curve'),
                pr_curve=result.get('pr_curve')
            )

            self.task_manager.update_status(task_id, 'completed', result=result)
            self.task_manager.update_progress(task_id, 100, '完成', '分析完成')
            
            self.logger.info(
                f"批量分析完成 - task_id: {task_id}, engine: {analysis_engine}, "
                f"有效案例: {valid_cases_count}, 特徵數: {len(feature_names)}"
            )
            
        except Exception as e:
            error_msg = f"批量 XGBoost 分析失敗: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.task_manager.update_status(task_id, 'failed', error=error_msg)
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """獲取任務狀態"""
        return self.task_manager.get_task(task_id)

    def get_predictions_df(self, task_id: str) -> Optional[pd.DataFrame]:
        """取得預測 DataFrame（若有快取）"""
        cached = self.task_cache.get_result(task_id)
        return cached.predictions_df if cached else None

    def _build_cross_symbol_validation(
        self,
        symbols: List[str],
        valid_cases: List[Any],
        X: np.ndarray,
        y: np.ndarray,
    ) -> Optional[List[Dict[str, Any]]]:
        """跨幣種 LOSO 產線路徑（eligibility min_rows=10 + LOSO + list payload）。

        由 `_run_batch_analysis` 呼叫；B4 測試亦直接呼叫本方法以鎖住
        `self.cross_symbol_validator.run_leave_one_symbol_out` 接線
        （移除/改壞該呼叫 → 測試必 FAIL）。
        """
        if len(symbols) < 2:
            return None
        try:
            X_by_symbol: Dict[str, np.ndarray] = {}
            y_by_symbol: Dict[str, np.ndarray] = {}
            symbol_indices: Dict[str, List[int]] = {sym: [] for sym in symbols}

            for idx, case in enumerate(valid_cases):
                if case.symbol in symbol_indices:
                    symbol_indices[case.symbol].append(idx)

            for sym, indices in symbol_indices.items():
                if len(indices) < 10:
                    continue
                X_by_symbol[sym] = X[indices]
                y_by_symbol[sym] = y[indices]

            if len(X_by_symbol) >= 2:
                results = self.cross_symbol_validator.run_leave_one_symbol_out(
                    symbols=list(X_by_symbol.keys()),
                    X_by_symbol=X_by_symbol,
                    y_by_symbol=y_by_symbol,
                )
                return [r.to_dict() for r in results]
            return None
        except Exception as e:
            self.logger.warning(f"跨幣種泛化驗證失敗: {str(e)}")
            return None

    def _build_sequence_features(
        self,
        all_features: pd.DataFrame,
        row_idx: int,
        feature_names: List[str],
        sequence_length: int,
        sequence_feature_mode: str,
        sequence_stride: int,
        aggregation_methods: Optional[List[str]],
        multi_scale_windows: Optional[List[int]]
    ) -> Optional[Tuple[np.ndarray, List[str]]]:
        """建立 TO 前 N 根序列特徵"""
        window_sizes = [sequence_length]
        if multi_scale_windows:
            for w in multi_scale_windows:
                if w not in window_sizes:
                    window_sizes.append(w)

        agg_methods = aggregation_methods or ["mean", "std", "min", "max", "last", "slope"]

        all_feature_vectors: List[np.ndarray] = []
        all_sequence_feature_names: List[str] = []

        for window_size in window_sizes:
            # 注意：不包含 row_idx (TO)，只用到 TO-1
            # 因為 TO 是開單時間點，應該在 TO 開盤時決策，只能看到 TO-1 之前的數據
            start_idx = row_idx - window_size * sequence_stride
            if start_idx < 0:
                return None

            window_indices = list(range(start_idx, row_idx, sequence_stride))
            if len(window_indices) != window_size:
                return None

            window_values = all_features.iloc[window_indices][feature_names].values
            if window_values.size == 0:
                return None

            if sequence_feature_mode == "flatten":
                window_feature_vectors, window_feature_names = self._flatten_sequence_features(
                    window_values=window_values,
                    feature_names=feature_names,
                    window_size=window_size
                )
            else:
                window_feature_vectors, window_feature_names = self._aggregate_sequence_features(
                    window_values=window_values,
                    feature_names=feature_names,
                    window_size=window_size,
                    aggregation_methods=agg_methods
                )

            all_feature_vectors.append(window_feature_vectors)
            all_sequence_feature_names.extend(window_feature_names)

        combined_features = np.concatenate(all_feature_vectors)
        return combined_features, all_sequence_feature_names

    def _flatten_sequence_features(
        self,
        window_values: np.ndarray,
        feature_names: List[str],
        window_size: int
    ) -> Tuple[np.ndarray, List[str]]:
        """將序列視窗展平為特徵向量
        
        注意：window_values shape = (window_size, n_features)
        我們需要先轉置再展平，才能得到正確的特徵順序
        """
        # 轉置後展平: (n_features, window_size) -> flat
        # 這樣每個特徵的時間序列會連續排列
        flattened_values = window_values.T.reshape(-1)

        flattened_feature_names: List[str] = []
        # 先按特徵名稱，再按時間順序（從舊到新）
        for name in feature_names:
            for idx in range(window_size):
                # 注意：現在 t-1 是最新可見的 K 線（TO-1），因為 TO 當根看不到
                offset = window_size - idx
                suffix = f"t-{offset}"
                flattened_feature_names.append(f"{name}_w{window_size}_{suffix}")

        return flattened_values, flattened_feature_names

    def _aggregate_sequence_features(
        self,
        window_values: np.ndarray,
        feature_names: List[str],
        window_size: int,
        aggregation_methods: List[str]
    ) -> Tuple[np.ndarray, List[str]]:
        """將序列視窗彙總為特徵向量"""
        aggregated_vectors: List[np.ndarray] = []
        aggregated_feature_names: List[str] = []

        for method in aggregation_methods:
            method_lower = method.lower()
            if method_lower == "mean":
                values = window_values.mean(axis=0)
            elif method_lower == "std":
                values = window_values.std(axis=0)
            elif method_lower == "min":
                values = window_values.min(axis=0)
            elif method_lower == "max":
                values = window_values.max(axis=0)
            elif method_lower == "last":
                values = window_values[-1]
            elif method_lower == "slope":
                if len(window_values) == 1:
                    values = np.zeros(window_values.shape[1])
                else:
                    values = (window_values[-1] - window_values[0]) / (len(window_values) - 1)
            else:
                raise ValueError(f"不支援的 aggregation method: {method}")

            aggregated_vectors.append(values)
            aggregated_feature_names.extend(
                [f"{name}_w{window_size}_{method_lower}" for name in feature_names]
            )

        return np.concatenate(aggregated_vectors), aggregated_feature_names
    
    def _get_timeframe_seconds(self, timeframe: str) -> int:
        """
        將時間週期轉換為秒數
        
        Args:
            timeframe: 時間週期字串 (1h, 4h, 12h, 1d)
            
        Returns:
            秒數
        """
        mapping = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '2h': 7200,
            '4h': 14400,
            '6h': 21600,
            '8h': 28800,
            '12h': 43200,
            '1d': 86400,
            '3d': 259200,
            '1w': 604800
        }
        return mapping.get(timeframe, 43200)  # 預設 12h

    def _resolve_market_phases(self, cases: List, timestamps: List[int]) -> Optional[List[str]]:
        """解析 Market_Phase 欄位，若缺失則以時間戳推導"""
        phases: List[str] = []

        has_attr_phase = False
        for case in cases:
            phase = None
            if hasattr(case, "market_phase"):
                phase = getattr(case, "market_phase")
                has_attr_phase = True
            elif isinstance(case, dict):
                phase = case.get("market_phase")
                has_attr_phase = True
            phases.append(phase)

        if has_attr_phase and any(phases):
            return [p if p is not None else "UNKNOWN" for p in phases]

        try:
            from datetime import datetime

            phases = []
            for ts in timestamps:
                ts_int = int(ts)
                if ts_int > 10 ** 12:
                    ts_int = ts_int // 1000
                phase = create_market_config().get_market_phase(
                    datetime.utcfromtimestamp(ts_int)
                )
                phases.append(phase)
            return phases
        except Exception as e:
            self.logger.warning(f"市場體制推導失敗: {str(e)}")
            return None

    def _get_kline_data(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
    ) -> pd.DataFrame:
        """Read or download kline data for the requested range."""
        df = self.kline_storage_manager.read_klines(
            symbol,
            timeframe,
            start_time=start_time,
            end_time=end_time,
            validate_continuity=False,
        )

        if df is not None and not df.empty:
            return df

        try:
            self.kline_download_service.download_klines(
                source="binance",
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                timeframe=timeframe,
                save_to_storage=True,
            )
        except Exception as e:
            self.logger.warning(
                f"下載 K 線數據失敗: {symbol}/{timeframe} {e}",
                exc_info=True,
            )

        df = self.kline_storage_manager.read_klines(
            symbol,
            timeframe,
            start_time=start_time,
            end_time=end_time,
            validate_continuity=False,
        )
        return df if df is not None else pd.DataFrame()

    def _resolve_case_price_changes(self, cases: List) -> Optional[np.ndarray]:
        """解析案例的 price_change"""
        price_changes: List[float] = []
        has_value = False

        for case in cases:
            value = None
            if hasattr(case, "price_change"):
                value = getattr(case, "price_change")
            elif isinstance(case, dict):
                value = case.get("price_change")

            if value is not None:
                has_value = True
                price_changes.append(float(value))
            else:
                price_changes.append(0.0)

        if not has_value:
            self.logger.info("案例缺少 price_change，跳過期望值估算")
            return None

        return np.array(price_changes)


# 全局實例
_xgboost_batch_service: Optional[XGBoostBatchService] = None


def get_xgboost_batch_service() -> XGBoostBatchService:
    """獲取 XGBoostBatchService 單例"""
    global _xgboost_batch_service
    
    if _xgboost_batch_service is None:
        _xgboost_batch_service = XGBoostBatchService()
        logger.info("Created global XGBoostBatchService instance")
    
    return _xgboost_batch_service

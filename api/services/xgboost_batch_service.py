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
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from pathlib import Path

import pandas as pd
import numpy as np

from api.core.config import settings
from api.core.logging import get_logger
from api.utils.case_storage import get_case_storage_manager
from api.utils.json_serializer import sanitize_for_json
from api.services.kline_data_service import KlineDataService
from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer
from momentum.Analysis.pattern_extractor import PatternExtractor
from momentum.Analysis.model_storage import ModelStorage
from momentum.FeatureEngineering.feature_extractor import FeatureExtractor, StrategyParams

logger = get_logger(__name__)


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
        self.kline_service = KlineDataService()
        self.feature_extractor = FeatureExtractor()
        self.xgboost_analyzer = XGBoostAnalyzer()
        self.pattern_extractor = PatternExtractor()
        self.model_storage = ModelStorage()
        self.logger = logger
    
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
            f"案例數: {len(all_cases)}, 指標數: {len(indicators)}"
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
        cv_folds: int,
        top_n_rules: int,
        min_support: int
    ):
        """執行批量分析（背景任務，支援多標的跨商品訓練）"""
        try:
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
                    self.kline_service.get_kline_data,
                    symbol=sym,
                    timeframe=timeframe,
                    start_time=start_dt,
                    end_time=end_dt
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
                
                sym_features = []
                sym_feature_names = []
                
                for indicator_config in indicators:
                    strategy_params = StrategyParams(
                        strategy_type=indicator_config['indicator'],
                        params=indicator_config['params'],
                        data_source=indicator_config.get('data_source', 'close')
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
            
            self.logger.info(f"所有標的特徵計算完成 - 共 {len(all_symbol_features)} 個標的，{len(shared_feature_names)} 個特徵")
            
            # ===== Step 4: 為每個案例提取特徵和標籤 =====
            self.task_manager.update_progress(task_id, 45, '提取案例特徵', f'為 {len(cases)} 個案例提取特徵...')
            
            X_list = []
            y_list = []
            case_timestamps = []
            case_ids = []
            valid_cases = 0
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
                valid_cases += 1
                
                # 更新進度
                if (i + 1) % 50 == 0:
                    self.task_manager.update_cases_processed(task_id, i + 1)
            
            if valid_cases < 10:
                raise ValueError(f"有效案例數量不足: {valid_cases}")
            
            X = np.array(X_list)
            y = np.array(y_list)
            if sequence_length is not None and sequence_feature_names is None:
                raise ValueError("序列特徵生成失敗，無有效案例")
            feature_names = sequence_feature_names or all_feature_names

            if sequence_length is not None:
                if sequence_feature_mode == "flatten" and not any("_t-" in name for name in feature_names):
                    raise ValueError("序列特徵未生效：展平模式特徵名稱缺少 _t- 後綴")
                if sequence_feature_mode == "aggregate" and not any("_w" in name for name in feature_names):
                    raise ValueError("序列特徵未生效：彙總模式特徵名稱缺少 _w 後綴")
            
            positive_count = sum(y)
            negative_count = len(y) - positive_count
            
            self.logger.info(
                f"案例特徵提取完成 - 有效案例: {valid_cases}, "
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
            
            # ===== Step 5: 訓練 XGBoost =====
            self.task_manager.update_progress(task_id, 60, '訓練模型', 'XGBoost 模型訓練中...')
            
            performance = await asyncio.to_thread(
                self.xgboost_analyzer.train_model,
                X, y, feature_names, 10, 0.2, xgboost_params, cv_folds,
                time_series_split, case_timestamps, purge_gap, embargo_pct
            )
            
            self.logger.info(
                f"模型訓練完成 - Train AUC: {performance.train_auc:.4f}, "
                f"CV AUC: {performance.cv_auc_mean:.4f}"
            )
            
            # ===== Step 6: 計算特徵重要性 =====
            self.task_manager.update_progress(task_id, 75, '分析特徵', '計算特徵重要性...')
            
            feature_importance = await asyncio.to_thread(
                self.xgboost_analyzer.calculate_feature_importance,
                feature_names
            )

            feature_importance_all = await asyncio.to_thread(
                self.xgboost_analyzer.get_all_importance_types,
                feature_names
            )
            
            # ===== Step 7: 提取決策規則 =====
            self.task_manager.update_progress(task_id, 85, '提取規則', '提取決策規則...')
            
            rules = await asyncio.to_thread(
                self.pattern_extractor.extract_decision_rules,
                self.xgboost_analyzer.model,
                X, y, feature_names,
                top_n_rules, min_support
            )

            predictions_output = await asyncio.to_thread(
                self.xgboost_analyzer.get_predictions,
                X, y, case_ids
            )
            
            # ===== Step 8: 儲存模型 =====
            self.task_manager.update_progress(task_id, 95, '儲存模型', '儲存分析結果...')
            
            # 多標的模型 ID 使用合併的標的名稱
            symbols_str = '_'.join(sorted(symbols))  # 例如: BTCUSDT_ETHUSDT
            model_id = f"batch_{symbols_str}_{timeframe}_{task_id[:8]}"
            model_path = await asyncio.to_thread(
                self.model_storage.save_model_to_pickle,
                model_id,
                self.xgboost_analyzer.model,
                feature_names,
                performance.__dict__,
                xgboost_params or {},
                {
                    'task_id': task_id,
                    'symbols': symbols,  # 改為 symbols 列表
                    'timeframe': timeframe,
                    'total_cases': len(cases),
                    'valid_cases': valid_cases,
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
            result = {
                'symbols': symbols,  # 改為 symbols 列表
                'timeframe': timeframe,
                'total_cases': len(cases),
                'valid_cases': valid_cases,
                'positive_cases': int(positive_count),
                'negative_cases': int(negative_count),
                'features_generated': len(feature_names),
                'feature_names': feature_names,
                'model_performance': performance.__dict__,
                'feature_importance': [fi.__dict__ for fi in feature_importance],
                'feature_importance_all': {
                    key: [fi.__dict__ for fi in values]
                    for key, values in feature_importance_all.items()
                },
                'decision_rules': [rule.to_dict() for rule in rules],
                'predictions': predictions_output.to_dict(),
                'calibration_curve': (
                    self.xgboost_analyzer.last_calibration_curve.to_dict()
                    if self.xgboost_analyzer.last_calibration_curve else None
                ),
                'pr_curve': self.xgboost_analyzer.last_pr_curve,
                'model_saved': True,
                'model_path': model_path
            }
            
            # 清理 result 中的 numpy 類型，防止 JSON 序列化錯誤
            result = sanitize_for_json(result)
            
            self.task_manager.update_status(task_id, 'completed', result=result)
            self.task_manager.update_progress(task_id, 100, '完成', '分析完成')
            
            self.logger.info(
                f"批量 XGBoost 分析完成 - task_id: {task_id}, "
                f"有效案例: {valid_cases}, 特徵數: {len(feature_names)}"
            )
            
        except Exception as e:
            error_msg = f"批量 XGBoost 分析失敗: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.task_manager.update_status(task_id, 'failed', error=error_msg)
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """獲取任務狀態"""
        return self.task_manager.get_task(task_id)

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


# 全局實例
_xgboost_batch_service: Optional[XGBoostBatchService] = None


def get_xgboost_batch_service() -> XGBoostBatchService:
    """獲取 XGBoostBatchService 單例"""
    global _xgboost_batch_service
    
    if _xgboost_batch_service is None:
        _xgboost_batch_service = XGBoostBatchService()
        logger.info("Created global XGBoostBatchService instance")
    
    return _xgboost_batch_service

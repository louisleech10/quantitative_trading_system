"""
Pattern Analysis Routes - 模式分析 API 路由

提供 XGBoost 分析、模式提取、模型管理的 REST API

Author: AI Agent
Date: 2026-01-10
Updated: 2026-01-13 - 新增批量分析 API
Updated: 2026-01-28 - 新增 OOT 驗證 API
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import numpy as np

from api.models.pattern_analysis_models import (
    XGBoostAnalysisRequest,
    XGBoostBatchAnalysisRequest,
    BatchAnalysisRequest,
    XGBoostAnalysisResponse,
    XGBoostAnalysisResult,
    XGBoostBatchAnalysisResult,
    CaseSummaryResponse,
    ModelInfoResponse,
    ModelListItem,
    OOTValidationRequest,
    OOTValidationResponse,
    OOTValidationResult,
    TimeSplitReport,
    TimePeriodInfo,
    DriftReport,
    DriftReportResponse,
    RegimeReport,
    RegimeAnalysisResponse,
    XGBoostPredictionsResponse,
    FeatureImportanceTypesResponse,
    ProbabilitySummary,
    CasePrediction,
    SHAPGlobalRequest,
    SHAPGlobalResponse,
    SHAPSingleCaseResponse,
    GlobalSHAPResult,
    SingleCaseSHAPResult,
    InteractionEffectResponse,
    GlobalSHAPFeatureImportance,
    SHAPSummaryPoint,
    SingleCaseContribution,
    ProbabilityDensityResponse,
    EquityCurveResponse,
    TopFalsePositivesResponse,
    RollingAUCResponse,
    CalibrationCurveResponse,
    PRCurveResponse,
    PRCurveData,
    ModelTrainingRequest,
    ComparisonReportResponse,
    TaskStartResponse,
    LightGBMTrainingRequest,
    LightGBMResultsResponse,
)
from api.models.pattern_analysis_models import ModelPerformanceResponse as GenericModelPerformanceResponse
from api.services.xgboost_task_service import XGBoostTaskService
from api.services.xgboost_batch_service import get_xgboost_batch_service
from api.services.model_task_service import ModelTaskService
from api.services.shap_analysis_service import SHAPAnalysisService
from api.services.xgboost_task_cache import XGBoostTaskCache
from api.core.logging import get_logger
from api.utils.json_serializer import sanitize_for_json
from momentum.Analysis.prediction_analyzer import PredictionAnalyzer

logger = get_logger(__name__)

router = APIRouter(prefix="/pattern-analysis", tags=["Pattern Analysis"])

# 服務實例
xgboost_service = XGBoostTaskService()
shap_service = SHAPAnalysisService()
task_cache = XGBoostTaskCache()
prediction_analyzer = PredictionAnalyzer()
model_task_service = ModelTaskService()


def _get_task_from_services(task_id: str):
    """從批量與單案例服務中取得任務"""
    batch_service = get_xgboost_batch_service()
    task = batch_service.get_task_status(task_id)
    if task:
        return task

    task = xgboost_service.get_task_status(task_id)
    return task


def _build_predictions_df(task_result: dict):
    import pandas as pd

    predictions = task_result.get('predictions', {})
    items = predictions.get('predictions') or []
    if not items:
        return None

    meta = task_result.get('prediction_meta', {})
    timestamps = meta.get('timestamps')
    symbols = meta.get('symbols')
    actual_returns = meta.get('actual_returns')

    df = pd.DataFrame(items)
    if timestamps is not None:
        df['timestamp'] = timestamps
    if symbols is not None:
        df['symbol'] = symbols
    if actual_returns is not None:
        df['actual_return'] = actual_returns

    return df


def _build_model_performance_response(performance: dict) -> GenericModelPerformanceResponse:
    return GenericModelPerformanceResponse(
        engine_type=performance.get("engine_type"),
        train_auc=float(performance.get("train_auc", 0.0)),
        cv_auc_mean=float(performance.get("cv_auc_mean", 0.0)),
        cv_auc_std=float(performance.get("cv_auc_std", 0.0)),
        precision=float(performance.get("precision", 0.0)),
        recall=float(performance.get("recall", 0.0)),
        f1_score=float(performance.get("f1_score", 0.0)),
        overfitting_score=float(performance.get("overfitting_score", 0.0)),
        oot_auc=performance.get("oot_auc"),
        brier_score=performance.get("brier_score"),
        ece=performance.get("ece"),
        calibration_quality=performance.get("calibration_quality"),
        pr_auc=performance.get("pr_auc"),
        positive_rate=performance.get("positive_rate"),
        training_time_seconds=performance.get("training_time_seconds"),
    )


# ==================== 通用模型 API（Task 3.7） ====================

@router.post("/model/train", response_model=TaskStartResponse)
async def start_model_training(request: ModelTrainingRequest):
    """啟動通用模型訓練任務。"""
    try:
        validation_payload = request.validation.model_dump() if request.validation else {}
        task_id = await model_task_service.start_training_task(
            engine=request.engine,
            config=request.config or {},
            data_source=request.features_source,
            validation=validation_payload,
            run_comparison=request.run_comparison,
        )
        return TaskStartResponse(task_id=task_id, status="running", engine=request.engine)
    except Exception as e:
        logger.error(f"啟動通用模型訓練失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model/{task_id}/performance", response_model=GenericModelPerformanceResponse)
async def get_model_performance(task_id: str):
    """取得模型效能結果。"""
    task = model_task_service.get_task_status(task_id)
    if task.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"任務不存在: {task_id}")
    if task.get("status") == "failed":
        raise HTTPException(status_code=400, detail=f"任務失敗: {task.get('error')}")
    if task.get("status") != "completed":
        raise HTTPException(status_code=400, detail=f"任務尚未完成，目前狀態: {task.get('status')}")

    result = task.get("result", {})
    performance = result.get("performance")
    if not performance:
        raise HTTPException(status_code=404, detail="找不到模型效能結果")

    return _build_model_performance_response(performance)


@router.get("/model/{task_id}/comparison", response_model=ComparisonReportResponse)
async def get_model_comparison(task_id: str):
    """取得雙引擎對比報告。"""
    task = model_task_service.get_task_status(task_id)
    if task.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"任務不存在: {task_id}")
    if task.get("status") == "failed":
        raise HTTPException(status_code=400, detail=f"任務失敗: {task.get('error')}")
    if task.get("status") != "completed":
        raise HTTPException(status_code=400, detail=f"任務尚未完成，目前狀態: {task.get('status')}")

    comparison = task.get("result", {}).get("comparison")
    if not comparison:
        raise HTTPException(status_code=404, detail="任務未啟用或未產生 comparison 結果")

    engine_performances = {
        engine_name: _build_model_performance_response(perf)
        for engine_name, perf in comparison.get("engine_performances", {}).items()
    }
    return ComparisonReportResponse(
        engine_performances=engine_performances,
        consensus_rate=float(comparison.get("consensus_rate", 0.0)),
        feature_rank_correlation=float(comparison.get("feature_rank_correlation", 0.0)),
        recommended_engine=str(comparison.get("recommended_engine", "")),
        recommendation_reason=str(comparison.get("recommendation_reason", "")),
    )


@router.post("/lightgbm/train", response_model=TaskStartResponse)
async def start_lightgbm_training(request: LightGBMTrainingRequest):
    """啟動 LightGBM 訓練任務。"""
    try:
        features_source = request.features_source
        if features_source.startswith("library:"):
            parts = features_source.split(":")
            if len(parts) != 3 or not parts[1] or not parts[2]:
                raise HTTPException(
                    status_code=400,
                    detail="features_source 格式錯誤，應為 library:{symbol}:{timeframe}",
                )

        config = dict(request.config or {})
        config["boosting_type"] = request.boosting_type
        if request.categorical_features:
            config["categorical_features"] = request.categorical_features

        validation_payload = request.validation.model_dump() if request.validation else {}
        task_id = await model_task_service.start_training_task(
            engine="lightgbm",
            config=config,
            data_source=features_source,
            validation=validation_payload,
            run_comparison=False,
        )
        return TaskStartResponse(task_id=task_id, status="running", engine="lightgbm")
    except Exception as e:
        logger.error(f"啟動 LightGBM 訓練失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lightgbm/{task_id}/results", response_model=LightGBMResultsResponse)
async def get_lightgbm_results(task_id: str):
    """取得 LightGBM 訓練結果。"""
    task = model_task_service.get_task_status(task_id)
    if task.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"任務不存在: {task_id}")
    if task.get("status") == "failed":
        raise HTTPException(status_code=400, detail=f"任務失敗: {task.get('error')}")
    if task.get("status") != "completed":
        raise HTTPException(status_code=400, detail=f"任務尚未完成，目前狀態: {task.get('status')}")

    result = task.get("result", {})
    if result.get("engine") != "lightgbm":
        raise HTTPException(status_code=400, detail="此任務不是 LightGBM 任務")

    performance = result.get("performance")
    if not performance:
        raise HTTPException(status_code=404, detail="找不到 LightGBM 效能結果")

    return LightGBMResultsResponse(
        task_id=task_id,
        performance=_build_model_performance_response(performance),
        feature_importance=result.get("feature_importance", []),
        predictions_summary=result.get("predictions_summary"),
    )


# ==================== OOT 驗證 API ====================

@router.post("/xgboost/validate-oot", response_model=OOTValidationResponse)
async def validate_oot(request: OOTValidationRequest):
    """
    執行 Out-of-Time (OOT) 驗證
    
    OOT 驗證用於評估模型在完全未見過的未來時間段的表現，
    是評估模型時間泛化能力的金標準。
    
    驗證指標說明：
    - oot_auc: OOT 資料上的 AUC，與 CV AUC 比較可知泛化能力
    - cv_oot_gap: CV AUC - OOT AUC，越小越好
      - < 0.05: 良好 (good)
      - < 0.08: 可接受 (acceptable)  
      - >= 0.08: 警告 (warning)
    
    Args:
        request: OOT 驗證請求，包含:
            - task_id: 已完成的 XGBoost 分析任務 ID
            - oot_start_date: OOT 開始日期（可選，為 None 時使用自動切分）
            - oot_ratio: OOT 資料比例（預設 0.2）
            - validation_ratio: 驗證集比例（預設 0.1）
            - timestamp_column: 時間欄位名稱（可選，自動偵測）
    
    Returns:
        OOTValidationResponse: 包含 OOT 驗證結果和時間切分報告
    """
    try:
        batch_service = get_xgboost_batch_service()
        
        # 檢查任務是否存在且已完成
        task = batch_service.get_task_status(request.task_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"任務不存在: {request.task_id}"
            )
        
        if task.get('status') != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"任務尚未完成，目前狀態: {task.get('status')}"
            )
        
        # 執行 OOT 驗證
        result = await _perform_oot_validation(
            task_id=request.task_id,
            task_result=task.get('result', {}),
            batch_service=batch_service,
            oot_start_date=request.oot_start_date,
            oot_ratio=request.oot_ratio or 0.2,
            validation_ratio=request.validation_ratio or 0.1,
            timestamp_column=request.timestamp_column
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OOT 驗證失敗: {str(e)}", exc_info=True)
        return OOTValidationResponse(
            task_id=request.task_id,
            status="failed",
            message=f"OOT 驗證失敗: {str(e)}",
            error=str(e)
        )


async def _perform_oot_validation(
    task_id: str,
    task_result: dict,
    batch_service,
    oot_start_date: Optional[str],
    oot_ratio: float,
    validation_ratio: float,
    timestamp_column: Optional[str]
) -> OOTValidationResponse:
    """
    執行 OOT 驗證的內部函式
    """
    import asyncio
    import numpy as np
    import pandas as pd
    from datetime import datetime
    
    from momentum.Analysis.time_splitter import (
        TimeSplitter,
        TimestampColumnNotFound,
        InsufficientOOTSamples,
        InsufficientTrainSamples,
        TimeRangeOverlap
    )
    from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer
    from momentum.Analysis.drift_analyzer import DriftAnalyzer
    
    # 獲取原始任務資訊
    symbols = task_result.get('symbols', [])
    timeframe = task_result.get('timeframe', '12h')
    feature_names = task_result.get('feature_names', [])
    cv_auc_mean = task_result.get('model_performance', {}).get('cv_auc_mean', 0.0)
    
    logger.info(
        f"開始 OOT 驗證 - task_id: {task_id}, "
        f"symbols: {symbols}, cv_auc: {cv_auc_mean:.4f}"
    )
    
    # 重新載入案例資料
    case_storage = batch_service.case_storage
    all_cases = []
    for symbol in symbols:
        symbol_cases = case_storage.get_cases_by_symbol(symbol)
        if symbol_cases:
            all_cases.extend(symbol_cases)
    
    if not all_cases:
        raise ValueError(f"找不到案例資料: {symbols}")
    
    # 建立案例 DataFrame（用於時間切分）
    case_data = []
    for case in all_cases:
        # 處理時間戳
        if isinstance(case.timestamp, int):
            ts = case.timestamp
        elif isinstance(case.timestamp, datetime):
            ts = int(case.timestamp.timestamp())
        else:
            continue
        
        case_data.append({
            'case_id': case.case_id,
            'symbol': case.symbol,
            'timestamp': ts,
            'Timestamp': datetime.utcfromtimestamp(ts).isoformat(),
            'positive_case': case.positive_case
        })
    
    cases_df = pd.DataFrame(case_data)
    
    logger.info(f"案例資料載入完成 - 總案例數: {len(cases_df)}")
    
    # 初始化時間切分器
    time_splitter = TimeSplitter(
        min_oot_samples=50,
        min_train_samples=100,
        random_seed=42
    )
    
    # 執行時間切分
    try:
        if oot_start_date:
            # 手動指定 OOT 開始日期
            # 找到最近但早於 oot_start_date 的案例時間作為訓練結束時間
            oot_start_ts = pd.Timestamp(oot_start_date)
            cases_df['ts_parsed'] = pd.to_datetime(cases_df['Timestamp'])
            
            train_cases = cases_df[cases_df['ts_parsed'] < oot_start_ts]
            if len(train_cases) == 0:
                raise ValueError(f"OOT 開始日期 {oot_start_date} 之前沒有案例")
            
            train_end = str(train_cases['ts_parsed'].max())
            
            split_result = time_splitter.split_by_time(
                df=cases_df,
                train_end=train_end,
                oot_start=oot_start_date,
                timestamp_col='Timestamp',
                validation_ratio=validation_ratio,
                label_col='positive_case'
            )
        else:
            # 自動切分
            split_result = time_splitter.auto_split(
                df=cases_df,
                oot_ratio=oot_ratio,
                validation_ratio=validation_ratio,
                timestamp_col='Timestamp',
                label_col='positive_case'
            )
        
    except TimestampColumnNotFound as e:
        raise ValueError(f"找不到時間欄位: {e.message}")
    except InsufficientOOTSamples as e:
        raise ValueError(f"OOT 樣本不足: {e.message}")
    except InsufficientTrainSamples as e:
        raise ValueError(f"訓練樣本不足: {e.message}")
    except TimeRangeOverlap as e:
        raise ValueError(f"時間範圍重疊: {e.message}")
    
    logger.info(
        f"時間切分完成 - 訓練: {split_result.train_period.samples}, "
        f"OOT: {split_result.oot_period.samples}"
    )
    
    # 重新提取 OOT 資料的特徵
    # 獲取 K 線數據
    kline_service = batch_service.kline_service
    feature_extractor = batch_service.feature_extractor
    
    # 計算時間範圍
    oot_cases = split_result.oot_df
    oot_timestamps = oot_cases['timestamp'].tolist()
    
    min_ts = min(oot_timestamps)
    max_ts = max(oot_timestamps)
    
    timeframe_seconds = batch_service._get_timeframe_seconds(timeframe)
    lookback_bars = 200  # 預設回看
    start_ts = min_ts - (lookback_bars * timeframe_seconds)
    end_ts = max_ts + (10 * timeframe_seconds)
    
    start_dt = datetime.utcfromtimestamp(start_ts)
    end_dt = datetime.utcfromtimestamp(end_ts)
    
    # 獲取所有標的的 K 線和計算特徵
    all_kline_data = {}
    for sym in symbols:
        kline_df = await asyncio.to_thread(
            kline_service.get_kline_data,
            symbol=sym,
            timeframe=timeframe,
            start_time=start_dt,
            end_time=end_dt
        )
        
        if kline_df is not None and not kline_df.empty:
            all_kline_data[sym] = kline_df
    
    if not all_kline_data:
        raise ValueError("無法獲取 K 線數據")
    
    # 提取 OOT 案例特徵
    # 使用原始任務的指標配置（從 task_result 獲取）
    indicators = task_result.get('metadata', {}).get('indicators', [])
    if not indicators:
        # 如果沒有指標配置，嘗試使用基本特徵
        logger.warning("未找到指標配置，使用基本特徵")
    
    # 為每個標的計算特徵
    from momentum.FeatureEngineering.feature_extractor import FeatureExtractor, StrategyParams
    
    all_symbol_features = {}
    for sym, kline_df in all_kline_data.items():
        sym_features = None
        sym_feature_names = []
        
        for indicator_config in indicators:
            strategy_params = StrategyParams(
                strategy_type=indicator_config['indicator'],
                params=indicator_config['params'],
                data_source=indicator_config.get('data_source', 'close')
            )
            
            try:
                features_df, ind_feature_names = feature_extractor.extract_features_from_strategy(
                    df=kline_df.copy(),
                    strategy_params=strategy_params,
                    include_basic_features=(len(sym_feature_names) == 0)
                )
                
                new_features = [f for f in ind_feature_names if f not in sym_feature_names]
                sym_feature_names.extend(new_features)
                
                if sym_features is None:
                    sym_features = features_df
                else:
                    for col in new_features:
                        if col in features_df.columns:
                            sym_features[col] = features_df[col]
                
            except Exception as e:
                logger.warning(f"{sym} 特徵計算失敗: {e}")
                continue
        
        if sym_features is not None:
            # 處理時間戳
            sample_ts = sym_features['timestamp'].iloc[0]
            if sample_ts > 10**12:
                sym_features['timestamp_sec'] = (sym_features['timestamp'] // 1000).astype(int)
            else:
                sym_features['timestamp_sec'] = sym_features['timestamp'].astype(int)
            
            sym_features.sort_values('timestamp_sec', inplace=True)
            sym_features.reset_index(drop=True, inplace=True)
            all_symbol_features[sym] = sym_features
    
    def _extract_feature_vectors(cases_df: pd.DataFrame, tag: str):
        X_list = []
        y_list = []
        for _, case_row in cases_df.iterrows():
            case_symbol = case_row['symbol']
            case_ts = case_row['timestamp']

            if case_symbol not in all_symbol_features:
                continue

            features_df = all_symbol_features[case_symbol]
            idx = features_df[features_df['timestamp_sec'] == case_ts].index

            if len(idx) == 0:
                continue

            row_idx = idx[0]

            available_features = [f for f in feature_names if f in features_df.columns]
            if len(available_features) < len(feature_names) * 0.5:
                logger.warning(
                    f"{tag} 特徵不足: 需要 {len(feature_names)}, 可用 {len(available_features)}"
                )
                continue

            feature_values_map = {
                name: features_df.loc[row_idx, name]
                for name in available_features
            }
            feature_values = np.array(
                [feature_values_map.get(name, 0.0) for name in feature_names],
                dtype=float
            )

            if np.isnan(feature_values).any():
                continue

            X_list.append(feature_values)
            y_list.append(case_row['positive_case'])

        return np.array(X_list), np.array(y_list)

    # 提取 OOT 特徵和標籤
    X_oot, y_oot = _extract_feature_vectors(oot_cases, "OOT")

    if len(X_oot) < 10:
        raise ValueError(f"有效 OOT 案例不足: {len(X_oot)}")
    
    logger.info(f"OOT 特徵提取完成 - 有效案例: {len(X_oot)}")

    # 產生 PSI 飄移報告（使用訓練集對比 OOT）
    drift_report = None
    try:
        X_train, _ = _extract_feature_vectors(split_result.train_df, "Train")
        if len(X_train) >= 50:
            drift_analyzer = DriftAnalyzer()
            psi_results = drift_analyzer.calculate_all_features_psi(
                X_train=X_train,
                X_test=X_oot,
                feature_names=feature_names,
                bins=10
            )
            drift_report_obj = drift_analyzer.generate_drift_report(psi_results)
            drift_report = drift_report_obj.to_dict()

            if drift_report is not None:
                task_result["drift_report"] = drift_report

            severe_features = [r.feature for r in psi_results if r.status == "drift_severe"]
            for r in psi_results:
                if r.status == "drift_severe":
                    logger.warning(f"特徵 {r.feature} PSI={r.psi:.4f}，建議檢查或重新訓練")

            if severe_features:
                logger.warning(f"飄移嚴重特徵數量: {len(severe_features)}")
        else:
            logger.warning(f"訓練樣本不足，無法計算 PSI: {len(X_train)}")
    except Exception as e:
        logger.warning(f"PSI 計算失敗: {str(e)}")
    
    # 載入模型並執行 OOT 驗證
    model_storage = batch_service.model_storage
    model_path = task_result.get('model_path', '')
    
    if not model_path:
        raise ValueError("找不到模型路徑")
    
    # 載入模型
    model_data = model_storage.load_model_from_pickle(model_path.replace('.pkl', '').split('/')[-1])
    if model_data is None:
        raise ValueError(f"無法載入模型: {model_path}")
    
    model = model_data['model']
    
    # 建立 XGBoostAnalyzer 並設定模型
    analyzer = XGBoostAnalyzer()
    analyzer.model = model
    analyzer.feature_names = feature_names
    
    # 執行 OOT 驗證
    oot_result = analyzer.validate_oot(
        X_oot=X_oot,
        y_oot=y_oot,
        cv_auc_mean=cv_auc_mean,
        oot_period_start=split_result.oot_period.start,
        oot_period_end=split_result.oot_period.end
    )
    
    logger.info(
        f"OOT 驗證完成 - OOT AUC: {oot_result.oot_auc:.4f}, "
        f"CV-OOT Gap: {oot_result.cv_oot_gap:.4f}, "
        f"狀態: {oot_result.gap_status}"
    )
    
    # 建立回應
    validation_result = OOTValidationResult(
        oot_auc=oot_result.oot_auc,
        oot_precision=oot_result.oot_precision,
        oot_recall=oot_result.oot_recall,
        oot_f1=oot_result.oot_f1,
        oot_samples=oot_result.oot_samples,
        oot_positive_count=oot_result.oot_positive_count,
        oot_positive_rate=oot_result.oot_positive_rate,
        cv_auc_mean=oot_result.cv_auc_mean,
        cv_oot_gap=oot_result.cv_oot_gap,
        gap_status=oot_result.gap_status,
        is_generalization_good=oot_result.is_generalization_good(),
        oot_period_start=oot_result.oot_period_start,
        oot_period_end=oot_result.oot_period_end
    )
    
    time_split_report = TimeSplitReport(
        split_method=split_result.split_method,
        timestamp_column=split_result.timestamp_column,
        random_seed=split_result.random_seed,
        train_period=TimePeriodInfo(
            start=split_result.train_period.start,
            end=split_result.train_period.end,
            samples=split_result.train_period.samples,
            positive_count=split_result.train_period.positive_count,
            positive_rate=split_result.train_period.positive_rate
        ),
        validation_period=TimePeriodInfo(
            start=split_result.validation_period.start,
            end=split_result.validation_period.end,
            samples=split_result.validation_period.samples,
            positive_count=split_result.validation_period.positive_count,
            positive_rate=split_result.validation_period.positive_rate
        ) if split_result.validation_period else None,
        oot_period=TimePeriodInfo(
            start=split_result.oot_period.start,
            end=split_result.oot_period.end,
            samples=split_result.oot_period.samples,
            positive_count=split_result.oot_period.positive_count,
            positive_rate=split_result.oot_period.positive_rate
        ),
        total_samples=(
            split_result.train_period.samples +
            (split_result.validation_period.samples if split_result.validation_period else 0) +
            split_result.oot_period.samples
        )
    )
    
    return OOTValidationResponse(
        task_id=task_id,
        status="success",
        message=f"OOT 驗證完成 - CV-OOT Gap: {oot_result.cv_oot_gap:.4f} ({oot_result.gap_status})",
        validation_result=validation_result,
        time_split_report=time_split_report,
        drift_report=DriftReport(**drift_report) if drift_report else None
    )


# ==================== 飄移監控 API ====================

@router.get("/xgboost/{task_id}/drift-report", response_model=DriftReportResponse)
async def get_xgboost_drift_report(task_id: str):
    """取得特徵飄移報告（PSI）"""
    task = _get_task_from_services(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任務不存在: {task_id}")

    result = task.get('result', {})
    drift_report = result.get('drift_report')
    if not drift_report:
        raise HTTPException(status_code=404, detail=f"任務未包含飄移報告: {task_id}")

    return DriftReportResponse(
        task_id=task_id,
        status="success",
        message="飄移報告取得成功",
        report=DriftReport(**drift_report)
    )


# ==================== 市場體制分析 API ====================

@router.get("/xgboost/{task_id}/regime-analysis", response_model=RegimeAnalysisResponse)
async def get_xgboost_regime_analysis(task_id: str):
    """取得市場體制分析報告"""
    task = _get_task_from_services(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任務不存在: {task_id}")

    result = task.get('result', {})
    regime_analysis = result.get('regime_analysis')
    if not regime_analysis:
        raise HTTPException(status_code=404, detail=f"任務未包含市場體制分析: {task_id}")

    return RegimeAnalysisResponse(
        task_id=task_id,
        status="success",
        message="市場體制分析取得成功",
        report=RegimeReport(**regime_analysis)
    )


# ==================== 批量分析 API（新增）====================

@router.get("/cases/summary", response_model=CaseSummaryResponse)
async def get_case_summary(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None
):
    """
    獲取案例摘要統計
    
    Args:
        symbol: 過濾特定交易對（可選）
        timeframe: 過濾特定時間週期（可選）
        
    Returns:
        案例統計（總數、正例數、反例數、可用交易對和時間週期）
    """
    try:
        batch_service = get_xgboost_batch_service()
        summary = batch_service.get_case_summary(symbol, timeframe)
        return summary
    except Exception as e:
        logger.error(f"獲取案例摘要失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xgboost/batch/start", response_model=XGBoostAnalysisResponse)
async def start_batch_xgboost_analysis(request: XGBoostBatchAnalysisRequest):
    """
    啟動 XGBoost 批量分析任務（支援多標的跨商品訓練）
    
    正確流程:
    1. 讀取所有標的的 K 線數據（HDF5）
    2. 根據指標配置為每個標的計算特徵
    3. 合併所有標的的案例並提取特徵和標籤
    4. 訓練單一跨商品 XGBoost 模型並交叉驗證
    5. 計算特徵重要性
    6. 提取決策規則
    7. 儲存模型
    
    Args:
        request: 批量分析請求（包含 symbols, timeframe, indicators）
        
    Returns:
        任務 ID 和狀態
    """
    try:
        batch_service = get_xgboost_batch_service()
        
        # 轉換指標配置
        indicators = [
            {
                'indicator': ind.indicator,
                'data_source': ind.data_source,
                'params': ind.params
            }
            for ind in request.indicators
        ]
        
        result = await batch_service.start_batch_analysis(
            symbols=request.symbols,
            timeframe=request.timeframe,
            indicators=indicators,
            lookback_bars=request.lookback_bars,
            sequence_length=request.sequence_length,
            sequence_feature_mode=request.sequence_feature_mode,
            sequence_stride=request.sequence_stride,
            aggregation_methods=request.aggregation_methods,
            multi_scale_windows=request.multi_scale_windows,
            time_series_split=request.time_series_split,
            purge_gap=request.purge_gap,
            embargo_pct=request.embargo_pct,
            xgboost_params=request.xgboost_params,
            cv_folds=request.cv_folds,
            top_n_rules=request.top_n_rules,
            min_support=request.min_support
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"啟動批量 XGBoost 分析失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/start", response_model=XGBoostAnalysisResponse)
async def start_batch_analysis(request: BatchAnalysisRequest):
    """
    啟動通用批量分析任務（xgboost / lightgbm / both）
    """
    try:
        batch_service = get_xgboost_batch_service()

        indicators = [
            {
                'indicator': ind.indicator,
                'data_source': ind.data_source,
                'params': ind.params
            }
            for ind in request.indicators
        ]

        result = await batch_service.start_batch_analysis(
            symbols=request.symbols,
            timeframe=request.timeframe,
            indicators=indicators,
            lookback_bars=request.lookback_bars,
            sequence_length=request.sequence_length,
            sequence_feature_mode=request.sequence_feature_mode,
            sequence_stride=request.sequence_stride,
            aggregation_methods=request.aggregation_methods,
            multi_scale_windows=request.multi_scale_windows,
            time_series_split=request.time_series_split,
            purge_gap=request.purge_gap,
            embargo_pct=request.embargo_pct,
            xgboost_params=request.xgboost_params,
            engine=request.engine,
            model_params=request.model_params,
            run_comparison=request.run_comparison,
            cv_folds=request.cv_folds,
            top_n_rules=request.top_n_rules,
            min_support=request.min_support
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"啟動批量分析失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/xgboost/batch/task/{task_id}")
async def get_batch_xgboost_task_status(task_id: str):
    """
    獲取批量 XGBoost 分析任務狀態
    
    返回任務的進度、當前步驟、結果或錯誤資訊
    """
    batch_service = get_xgboost_batch_service()
    task = batch_service.get_task_status(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"任務不存在: {task_id}")
    
    # 清理 NaN/Infinity 等無法 JSON 序列化的值
    task = sanitize_for_json(task)
    
    return task


@router.get("/batch/task/{task_id}")
async def get_batch_task_status(task_id: str):
    """獲取通用批量分析任務狀態"""
    batch_service = get_xgboost_batch_service()
    task = batch_service.get_task_status(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"任務不存在: {task_id}")

    return sanitize_for_json(task)


# ==================== 預測與特徵重要性 API ====================

@router.get("/xgboost/{task_id}/predictions", response_model=XGBoostPredictionsResponse)
async def get_xgboost_predictions(task_id: str, include_details: bool = False):
    """
    取得 XGBoost 預測機率

    include_details=True 時回傳每筆案例的預測機率
    """
    task = _get_task_from_services(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任務不存在: {task_id}")

    if task.get('status') != 'completed':
        raise HTTPException(status_code=400, detail=f"任務尚未完成，目前狀態: {task.get('status')}")

    result = task.get('result', {})
    predictions = result.get('predictions')
    if not predictions:
        raise HTTPException(status_code=404, detail=f"任務未包含預測結果: {task_id}")

    summary_data = predictions.get('proba_summary') or predictions.get('summary')
    items = predictions.get('predictions')
    if not summary_data:
        raise HTTPException(status_code=500, detail="預測摘要缺失")

    response = XGBoostPredictionsResponse(
        task_id=task_id,
        total_cases=len(items) if items else 0,
        summary=ProbabilitySummary(**summary_data),
        predictions=[CasePrediction(**item) for item in items] if include_details else None
    )
    return response


@router.get("/xgboost/{task_id}/feature-importance", response_model=FeatureImportanceTypesResponse)
async def get_xgboost_feature_importance(
    task_id: str,
    types: str = "gain"
):
    """
    取得完整特徵重要性（可選 gain/cover/weight）
    """
    task = _get_task_from_services(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任務不存在: {task_id}")

    if task.get('status') != 'completed':
        raise HTTPException(status_code=400, detail=f"任務尚未完成，目前狀態: {task.get('status')}")

    result = task.get('result', {})
    importance_all = result.get('feature_importance_all')
    if not importance_all:
        raise HTTPException(status_code=404, detail=f"任務未包含完整特徵重要性: {task_id}")

    requested_types = [t.strip() for t in types.split(',') if t.strip()]
    valid_types = {"gain", "cover", "weight"}
    invalid_types = [t for t in requested_types if t not in valid_types]
    if invalid_types:
        raise HTTPException(status_code=400, detail=f"不支援的 types: {', '.join(invalid_types)}")

    filtered = {t: importance_all.get(t, []) for t in requested_types}
    filtered = sanitize_for_json(filtered)

    return FeatureImportanceTypesResponse(task_id=task_id, types=filtered)


# ==================== 預測分析圖表 API ====================

@router.get("/xgboost/{task_id}/probability-density", response_model=ProbabilityDensityResponse)
async def get_probability_density(task_id: str, n_bins: int = 50):
    """取得機率分佈密度數據"""
    task_result = task_cache.get_result(task_id)
    if task_result is None:
        task = _get_task_from_services(task_id)
        if not task or task.get('status') != 'completed':
            raise HTTPException(status_code=404, detail=f"任務不存在或未完成: {task_id}")
        predictions_df = _build_predictions_df(task.get('result', {}) or {})
        if predictions_df is None or predictions_df.empty:
            raise HTTPException(status_code=400, detail="無預測資料可用")
    else:
        predictions_df = task_result.predictions_df

    density_data = prediction_analyzer.calculate_probability_density(
        y_true=predictions_df['y_true'].values,
        y_pred_proba=predictions_df['predicted_proba'].values,
        n_bins=n_bins
    )

    return ProbabilityDensityResponse(task_id=task_id, data=density_data.to_dict())


@router.get("/xgboost/{task_id}/strategy-equity", response_model=EquityCurveResponse)
async def get_strategy_equity(task_id: str, threshold: float = 0.75):
    """取得策略權益曲線數據"""
    task_result = task_cache.get_result(task_id)
    if task_result is None:
        task = _get_task_from_services(task_id)
        if not task or task.get('status') != 'completed':
            raise HTTPException(status_code=404, detail=f"任務不存在或未完成: {task_id}")
        predictions_df = _build_predictions_df(task.get('result', {}) or {})
        if predictions_df is None or predictions_df.empty:
            raise HTTPException(status_code=400, detail="無預測資料可用")
    else:
        predictions_df = task_result.predictions_df

    if predictions_df is None or predictions_df.empty:
        raise HTTPException(status_code=400, detail="無預測資料可用")

    if 'actual_return' not in predictions_df.columns or predictions_df['actual_return'].isna().all():
        raise HTTPException(status_code=400, detail="缺少 actual_return 資料，無法計算權益曲線")

    equity_data = prediction_analyzer.calculate_strategy_equity_curve(
        timestamps=predictions_df['timestamp'].fillna(0).astype(int).tolist(),
        y_pred_proba=predictions_df['predicted_proba'].values,
        actual_returns=predictions_df['actual_return'].fillna(0).values,
        threshold=threshold
    )

    return EquityCurveResponse(task_id=task_id, data=equity_data.to_dict())


@router.get("/xgboost/{task_id}/top-false-positives", response_model=TopFalsePositivesResponse)
async def get_top_false_positives(task_id: str, top_n: int = 5):
    """取得 Top False Positives"""
    task_result = task_cache.get_result(task_id)
    if task_result is None:
        task = _get_task_from_services(task_id)
        if not task or task.get('status') != 'completed':
            raise HTTPException(status_code=404, detail=f"任務不存在或未完成: {task_id}")
        predictions_df = _build_predictions_df(task.get('result', {}) or {})
        if predictions_df is None or predictions_df.empty:
            raise HTTPException(status_code=400, detail="無預測資料可用")
    else:
        predictions_df = task_result.predictions_df

    if predictions_df is None or predictions_df.empty:
        raise HTTPException(status_code=400, detail="無預測資料可用")

    case_ids = predictions_df['case_id'].astype(str).tolist()
    timestamps = predictions_df['timestamp'].fillna(0).astype(int).tolist() if 'timestamp' in predictions_df.columns else [0] * len(case_ids)
    symbols = predictions_df['symbol'].astype(str).tolist() if 'symbol' in predictions_df.columns else ["UNKNOWN"] * len(case_ids)
    actual_returns = predictions_df['actual_return'].fillna(0).values if 'actual_return' in predictions_df.columns else np.zeros(len(case_ids))

    cases = prediction_analyzer.get_top_false_positives(
        case_ids=case_ids,
        timestamps=timestamps,
        symbols=symbols,
        y_true=predictions_df['y_true'].values,
        y_pred_proba=predictions_df['predicted_proba'].values,
        actual_returns=actual_returns,
        top_n=top_n
    )

    total_fp = int(((predictions_df['y_true'] == 0) & (predictions_df['predicted_proba'] > 0.5)).sum())

    return TopFalsePositivesResponse(
        task_id=task_id,
        cases=[item.to_dict() for item in cases],
        total_false_positives=total_fp
    )


@router.get("/xgboost/{task_id}/rolling-auc", response_model=RollingAUCResponse)
async def get_rolling_auc(task_id: str, window: int = 500):
    """取得滾動 AUC 數據"""
    task_result = task_cache.get_result(task_id)
    if task_result is None:
        task = _get_task_from_services(task_id)
        if not task or task.get('status') != 'completed':
            raise HTTPException(status_code=404, detail=f"任務不存在或未完成: {task_id}")
        predictions_df = _build_predictions_df(task.get('result', {}) or {})
        if predictions_df is None or predictions_df.empty:
            raise HTTPException(status_code=400, detail="無預測資料可用")
    else:
        predictions_df = task_result.predictions_df

    if predictions_df is None or predictions_df.empty:
        raise HTTPException(status_code=400, detail="無預測資料可用")

    timestamps = predictions_df['timestamp'].fillna(0).astype(int).tolist() if 'timestamp' in predictions_df.columns else list(range(len(predictions_df)))

    rolling_data = prediction_analyzer.calculate_rolling_auc(
        timestamps=timestamps,
        y_true=predictions_df['y_true'].values,
        y_pred_proba=predictions_df['predicted_proba'].values,
        window=window
    )

    return RollingAUCResponse(task_id=task_id, data=rolling_data.to_dict())


@router.get("/xgboost/{task_id}/calibration-curve", response_model=CalibrationCurveResponse)
async def get_calibration_curve(task_id: str):
    """取得校準曲線數據"""
    task_result = task_cache.get_result(task_id)
    if task_result and task_result.calibration_curve:
        return CalibrationCurveResponse(task_id=task_id, data=task_result.calibration_curve)

    task = _get_task_from_services(task_id)
    if not task or task.get('status') != 'completed':
        raise HTTPException(status_code=404, detail=f"任務不存在或未完成: {task_id}")

    result = task.get('result', {})
    calibration_curve = result.get('calibration_curve')
    if not calibration_curve:
        raise HTTPException(status_code=404, detail="Calibration curve 不存在")

    return CalibrationCurveResponse(task_id=task_id, data=calibration_curve)


@router.get("/xgboost/{task_id}/pr-curve", response_model=PRCurveResponse)
async def get_pr_curve(task_id: str):
    """取得 PR 曲線數據"""
    task_result = task_cache.get_result(task_id)
    if task_result and task_result.pr_curve:
        pr_curve_data = task_result.pr_curve
    else:
        task = _get_task_from_services(task_id)
        if not task or task.get('status') != 'completed':
            raise HTTPException(status_code=404, detail=f"任務不存在或未完成: {task_id}")
        result = task.get('result', {})
        pr_curve_data = result.get('pr_curve')
        if not pr_curve_data:
            raise HTTPException(status_code=404, detail="PR curve 不存在")
        model_perf = result.get('model_performance', {})
    if task_result and task_result.pr_curve:
        model_perf = {}
        task = _get_task_from_services(task_id)
        if task and task.get('status') == 'completed':
            model_perf = task.get('result', {}).get('model_performance', {})

    pr_curve = PRCurveData(
        precision=pr_curve_data.get('precision', []),
        recall=pr_curve_data.get('recall', []),
        thresholds=pr_curve_data.get('thresholds', []),
        pr_auc=model_perf.get('pr_auc'),
        baseline=model_perf.get('positive_rate')
    )

    return PRCurveResponse(task_id=task_id, data=pr_curve)


# ==================== SHAP 分析 API ====================

@router.post("/xgboost/{task_id}/shap", response_model=SHAPGlobalResponse)
async def get_xgboost_shap_global(task_id: str, request: SHAPGlobalRequest):
    """取得 SHAP 全局分析結果"""
    task = _get_task_from_services(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任務不存在: {task_id}")

    if task.get('status') != 'completed':
        raise HTTPException(status_code=400, detail=f"任務尚未完成，目前狀態: {task.get('status')}")

    try:
        task_result = task.get('result', {})
        feature_pairs = None
        if request.feature_pairs:
            feature_pairs = [(pair[0], pair[1]) for pair in request.feature_pairs]

        global_result, interaction_effects = shap_service.analyze_global(
            task_result=task_result,
            sample_size=request.sample_size,
            include_summary_points=request.include_summary_points,
            feature_pairs=feature_pairs
        )

        result = GlobalSHAPResult(
            expected_value=global_result.expected_value,
            feature_importance_shap=[
                GlobalSHAPFeatureImportance(
                    feature=item.feature,
                    mean_abs_shap=item.mean_abs_shap,
                    mean_shap=item.mean_shap,
                    rank=item.rank
                )
                for item in global_result.feature_importance_shap
            ],
            top_positive_features=global_result.top_positive_features,
            top_negative_features=global_result.top_negative_features,
            sample_size=global_result.sample_size,
            summary_points=[
                SHAPSummaryPoint(
                    feature=point.feature,
                    value=point.value,
                    shap_value=point.shap_value
                )
                for point in (global_result.summary_points or [])
            ] if request.include_summary_points else None,
            interaction_effects=[
                InteractionEffectResponse(
                    feature_pair=[effect.feature_pair[0], effect.feature_pair[1]],
                    mean_abs_interaction=effect.mean_abs_interaction
                )
                for effect in (interaction_effects or [])
            ] if interaction_effects else None
        )

        return SHAPGlobalResponse(
            task_id=task_id,
            status="success",
            message="SHAP 全局分析完成",
            result=result
        )
    except Exception as e:
        logger.error(f"SHAP 全局分析失敗: {str(e)}", exc_info=True)
        return SHAPGlobalResponse(
            task_id=task_id,
            status="failed",
            message=f"SHAP 全局分析失敗: {str(e)}",
            error=str(e)
        )


@router.get("/xgboost/{task_id}/shap/case/{case_id}", response_model=SHAPSingleCaseResponse)
async def get_xgboost_shap_single_case(task_id: str, case_id: str):
    """取得單案例 SHAP 解釋"""
    task = _get_task_from_services(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任務不存在: {task_id}")

    if task.get('status') != 'completed':
        raise HTTPException(status_code=400, detail=f"任務尚未完成，目前狀態: {task.get('status')}")

    try:
        task_result = task.get('result', {})
        single_result = shap_service.explain_single_case(task_result=task_result, case_id=case_id)

        result = SingleCaseSHAPResult(
            predicted_proba=single_result.predicted_proba,
            expected_value=single_result.expected_value,
            contributions=[
                SingleCaseContribution(
                    feature=item.feature,
                    value=item.value,
                    shap_value=item.shap_value,
                    contribution_pct=item.contribution_pct
                )
                for item in single_result.contributions
            ]
        )

        return SHAPSingleCaseResponse(
            task_id=task_id,
            case_id=case_id,
            status="success",
            message="SHAP 單案例分析完成",
            result=result
        )
    except Exception as e:
        logger.error(f"SHAP 單案例分析失敗: {str(e)}", exc_info=True)
        return SHAPSingleCaseResponse(
            task_id=task_id,
            case_id=case_id,
            status="failed",
            message=f"SHAP 單案例分析失敗: {str(e)}",
            error=str(e)
        )


# ==================== 單案例分析 API（保留向後相容）====================

@router.post("/xgboost/start", response_model=XGBoostAnalysisResponse)
async def start_xgboost_analysis(request: XGBoostAnalysisRequest):
    """
    啟動 XGBoost 分析任務（單案例，向後相容）
    
    分析流程:
    1. 讀取案例的特徵數據
    2. 訓練 XGBoost 模型並交叉驗證
    3. 計算特徵重要性
    4. 提取決策規則
    5. 儲存模型至 Pickle
    """
    try:
        result = await xgboost_service.start_xgboost_analysis_task(
            case_id=request.case_id,
            xgboost_params=request.xgboost_params,
            cv_folds=request.cv_folds,
            top_n_rules=request.top_n_rules,
            min_support=request.min_support
        )
        return result
    except Exception as e:
        logger.error(f"啟動 XGBoost 分析失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/xgboost/task/{task_id}")
async def get_xgboost_task_status(task_id: str):
    """
    獲取 XGBoost 分析任務狀態
    
    返回任務的進度、狀態、結果或錯誤資訊
    """
    task = xgboost_service.get_task_status(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"任務不存在: {task_id}")
    
    # 清理 NaN/Infinity 等無法 JSON 序列化的值
    task = sanitize_for_json(task)
    
    return task


@router.get("/model/info/{case_id}", response_model=ModelInfoResponse)
async def get_model_info(case_id: str):
    """
    獲取模型資訊
    
    返回模型的效能指標、特徵名稱、參數等（不載入完整模型）
    """
    try:
        if not xgboost_service.model_exists(case_id):
            raise HTTPException(
                status_code=404,
                detail=f"模型不存在: {case_id}"
            )
        
        model_info = xgboost_service.get_model_info(case_id)
        return model_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取模型資訊失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model/list", response_model=List[ModelListItem])
async def list_models():
    """
    列出所有已儲存的模型
    
    返回模型列表，包含案例 ID、檔案大小、修改時間等
    """
    try:
        models = xgboost_service.list_models()
        return models
    except Exception as e:
        logger.error(f"列出模型失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model/exists/{case_id}")
async def check_model_exists(case_id: str):
    """
    檢查模型是否存在
    """
    exists = xgboost_service.model_exists(case_id)
    return {'case_id': case_id, 'exists': exists}

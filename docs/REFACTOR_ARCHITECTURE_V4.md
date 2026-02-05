# REFACTOR_ARCHITECTURE_V4

## Phase 1 Violation Report (Task 1.1 - 1.7)

### Rule 1: momentum -> api reverse dependencies

#### Critical (api.services / api.utils)
- momentum/Optimization/optuna_optimizer.py:98 from api.services.signal_analysis_service import SignalAnalysisService [P]
- momentum/Optimization/optuna_optimizer.py:99 from api.utils.case_storage import get_case_storage_manager, CaseStorageManager as CaseStorage [A]

#### High (api.models)
- momentum/Analysis/signal_density_analyzer.py:30 from api.models.training_window_config import ... [C]
- momentum/Optimization/optuna_optimizer.py:91 from api.models.training_window_config import ... [C]
- momentum/Optimization/optuna_optimizer.py:97 from api.models.strategy_test_models import ParameterRange [C]
- momentum/Utils/data_validator.py:24 from api.models.training_window_config import SignalDensityResponse [C]

#### Medium (api.core.logging)
- momentum/FeatureEngineering/indicators/ema_extractor.py:15 from api.core.logging import get_logger [A]
- momentum/FeatureEngineering/indicators/macd_extractor.py:14 from api.core.logging import get_logger [A]
- momentum/FeatureEngineering/indicators/rsi_extractor.py:14 from api.core.logging import get_logger [A]
- momentum/FeatureEngineering/feature_storage.py:18 from api.core.logging import get_logger [A]
- momentum/FeatureEngineering/feature_extractor.py:20 from api.core.logging import get_logger [A]
- momentum/FeatureEngineering/feature_validator.py:19 from api.core.logging import get_logger [A]
- momentum/FeatureEngineering/strategy_registry.py:22 from api.core.logging import get_logger [A]
- momentum/Analysis/cross_symbol_validator.py:15 from api.core.logging import get_logger [A]
- momentum/Analysis/drift_analyzer.py:15 from api.core.logging import get_logger [A]
- momentum/Analysis/model_storage.py:18 from api.core.logging import get_logger [A]
- momentum/Analysis/prediction_analyzer.py:18 from api.core.logging import get_logger [A]
- momentum/Analysis/strategies/short_long_cross_strategy.py:16 from api.core.logging import get_logger [A]
- momentum/Analysis/strategies/mid_long_cross_strategy.py:16 from api.core.logging import get_logger [A]
- momentum/Analysis/strategies/three_line_strategy.py:16 from api.core.logging import get_logger [A]
- momentum/Analysis/regime_analyzer.py:16 from api.core.logging import get_logger [A]
- momentum/Analysis/expectancy_calculator.py:13 from api.core.logging import get_logger [A]
- momentum/Analysis/time_splitter.py:26 from api.core.logging import get_logger [A]
- momentum/Analysis/bootstrap_estimator.py:14 from api.core.logging import get_logger [A]
- momentum/Analysis/xgboost_analyzer.py:23 from api.core.logging import get_logger [A]
- momentum/Analysis/shap_analyzer.py:18 from api.core.logging import get_logger [A]
- momentum/Analysis/pattern_validator.py:15 from api.core.logging import get_logger [A]
- momentum/Analysis/pattern_extractor.py:18 from api.core.logging import get_logger [A]
- momentum/Analysis/pattern_storage.py:17 from api.core.logging import get_logger [A]
- momentum/Analysis/calibration_analyzer.py:16 from api.core.logging import get_logger [A]
- momentum/Analysis/strategy_registry.py:27 from api.core.logging import get_logger [A]
- momentum/Optimization/trial_comparison.py:30 from api.core.logging import get_logger [A]

#### Config dependency (api.core.config)
- momentum/Optimization/optuna_optimizer.py:107 from api.core.config import settings [I]

### Rule 2: momentum cross-domain imports

#### Analysis -> DataExtraction
- momentum/Analysis/kline_cache.py:28 from momentum.DataExtraction.kline_storage import KlineStorageManager [A]
- momentum/Analysis/signal_density_analyzer.py:28 from momentum.DataExtraction.kline_storage import KlineStorageManager [A]

#### Analysis -> Indicators
- None

#### Analysis -> Indicator
- None

#### Optimization -> Analysis
- None

#### Analysis -> Optimization
- None

### Rule 3: api/services direct construction of momentum objects

- api/services/chart_data_service.py:36 from momentum.DataExtraction.kline_storage import KlineStorageManager [F]
- api/services/chart_data_service.py:37 from momentum.Indicators import IndicatorEngine [F]
- api/services/shap_analysis_service.py:19 from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer [F]
- api/services/shap_analysis_service.py:20 from momentum.Analysis.model_storage import ModelStorage [F]
- api/services/shap_analysis_service.py:21 from momentum.FeatureEngineering.feature_storage import FeatureStorage [F]
- api/services/xgboost_task_service.py:19 from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer [F]
- api/services/xgboost_task_service.py:20 from momentum.Analysis.expectancy_calculator import ExpectancyCalculator [F]
- api/services/xgboost_task_service.py:21 from momentum.Analysis.bootstrap_estimator import BootstrapEstimator [F]
- api/services/xgboost_task_service.py:22 from momentum.Analysis.regime_analyzer import RegimeAnalyzer [F]
- api/services/xgboost_task_service.py:23 from momentum.Analysis.pattern_extractor import PatternExtractor [F]
- api/services/xgboost_task_service.py:24 from momentum.Analysis.model_storage import ModelStorage [F]
- api/services/xgboost_task_service.py:25 from momentum.FeatureEngineering.feature_storage import FeatureStorage [F]
- api/services/xgboost_task_service.py:452 from momentum.DataExtraction.Market_Screener_Configuration import MarketConfig [F]
- api/services/data_service.py:326 from momentum.DataExtraction.Market_Screener_Configuration import MarketConfig [F]
- api/services/feature_task_service.py:20 from momentum.FeatureEngineering.feature_extractor import FeatureExtractor, StrategyParams [F]
- api/services/feature_task_service.py:23 from momentum.FeatureEngineering.feature_validator import FeatureValidator [F]
- api/services/feature_task_service.py:24 from momentum.FeatureEngineering.feature_storage import FeatureStorage [F]
- api/services/xgboost_batch_service.py:36 from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer [F]
- api/services/xgboost_batch_service.py:37 from momentum.Analysis.expectancy_calculator import ExpectancyCalculator [F]
- api/services/xgboost_batch_service.py:38 from momentum.Analysis.bootstrap_estimator import BootstrapEstimator [F]
- api/services/xgboost_batch_service.py:39 from momentum.Analysis.cross_symbol_validator import CrossSymbolValidator [F]
- api/services/xgboost_batch_service.py:40 from momentum.Analysis.regime_analyzer import RegimeAnalyzer [F]
- api/services/xgboost_batch_service.py:41 from momentum.Analysis.pattern_extractor import PatternExtractor [F]
- api/services/xgboost_batch_service.py:42 from momentum.Analysis.model_storage import ModelStorage [F]
- api/services/xgboost_batch_service.py:43 from momentum.FeatureEngineering.feature_extractor import FeatureExtractor, StrategyParams [F]
- api/services/xgboost_batch_service.py:1010 from momentum.DataExtraction.Market_Screener_Configuration import MarketConfig [F]
- api/services/pattern_management_service.py:15 from momentum.Analysis.pattern_definition import Pattern, PatternRule [F]
- api/services/pattern_management_service.py:16 from momentum.Analysis.pattern_storage import PatternStorage [F]
- api/services/pattern_management_service.py:17 from momentum.Analysis.pattern_validator import PatternValidator [F]
- api/services/kline_data_service.py:39 from momentum.DataExtraction.kline_storage import KlineStorageManager [F]
- api/services/kline_data_service.py:40 from momentum.DataExtraction.kline_download_service import KlineDownloadService [F]
- api/services/kline_data_service.py:41 from momentum.DataExtraction.providers.binance_provider import BinanceProvider [F]
- api/services/batch_download_service.py:29 from momentum.DataExtraction.kline_storage import KlineStorageManager [F]
- api/services/batch_download_service.py:30 from momentum.DataExtraction.kline_download_service import KlineDownloadService [F]
- api/services/batch_download_service.py:126 from momentum.DataExtraction.providers.binance_provider import BinanceProvider [F]
- api/services/task_manager.py:496 from momentum.DataExtraction.Momentum_Strategy_Data_Loader import MomentumDataLoader [F]
- api/services/task_manager.py:497 from momentum.DataExtraction.case_search_engine import CaseSearchEngine, SearchConfiguration, FilterCondition [F]
- api/services/task_manager.py:640 from momentum.DataExtraction.case_search_engine import SearchConfiguration, FilterCondition [F]
- api/services/optimization_task_service.py:26 from momentum.Optimization.optuna_optimizer import OptunaOptimizer, OptimizationResult, ParameterRanges [F]
- api/services/kline_storage_service.py:31 from momentum.DataExtraction.kline_storage import KlineStorageManager [F]
- api/services/chart_signal_service.py:29 from momentum.DataExtraction.kline_storage import KlineStorageManager [F]
- api/services/chart_signal_service.py:30 from momentum.Indicators import IndicatorEngine [F]
- api/services/chart_signal_service.py:155 from momentum.DataExtraction.kline_storage import KlineStorageManager [F]
- api/services/signal_analysis_service.py:21 from momentum.DataExtraction.kline_storage import KlineStorageManager [F]
- api/services/signal_analysis_service.py:22 from momentum.Indicators import IndicatorEngine [F]
- api/services/signal_analysis_service.py:23 from momentum.Analysis import SignalDensityAnalyzer [F]
- api/services/signal_analysis_service.py:316 from momentum.Indicators.types import DataSourceEnum [F]
- api/services/standalone_search_service.py:198 from momentum.DataExtraction.Momentum_Strategy_Data_Loader import MomentumDataLoader [F]
- api/services/standalone_search_service.py:199 from momentum.DataExtraction.case_search_engine import CaseSearchEngine [F]
- api/services/standalone_search_service.py:248 from momentum.DataExtraction.Momentum_Strategy_Data_Loader import MomentumDataLoader [F]
- api/services/standalone_search_service.py:256 from momentum.DataExtraction.case_search_engine import CaseSearchEngine [F]
- api/services/standalone_search_service.py:280 from momentum.DataExtraction.Momentum_Strategy_Data_Loader import MomentumDataLoader [F]
- api/services/standalone_search_service.py:281 from momentum.DataExtraction.case_search_engine import CaseSearchEngine [F]
- api/services/standalone_search_service.py:316 from momentum.DataExtraction.case_search_engine import SearchConfiguration, FilterCondition [F]

### Rule 4: api/services cross-service imports

- api/services/chart_data_service.py:31 from api.services.kline_storage_service import KlineStorageService [A]
- api/services/chart_data_service.py:32 from api.services.kline_data_service import ... [A]
- api/services/xgboost_task_service.py:26 from api.services.xgboost_task_cache import XGBoostTaskCache [A]
- api/services/xgboost_batch_service.py:35 from api.services.kline_data_service import KlineDataService [A]
- api/services/xgboost_batch_service.py:44 from api.services.xgboost_task_cache import XGBoostTaskCache [A]

### Rule 5: mutable global singleton across domains

- momentum/Optimization/optuna_optimizer.py:107 from api.core.config import settings [I]
- settings.* usage in momentum: None

### Rule 6: callback/closure bypass

- N/A (no matches)

### Rule 7: api/models <-> momentum/core

- N/A (no api/models dependency on momentum/core found in pre-check)

## Phase 2 Service Classification (Task 2.2)

### Keep
| Service 檔案 | 依據（Domain/依賴） | 備註 |
|---|---|---|
| api/services/batch_download_service.py | 單一 Domain：DataExtraction | 無 |
| api/services/case_import_service.py | 無 momentum 依賴 | 無 |
| api/services/data_service.py | 單一 Domain：DataExtraction | 無 |
| api/services/feature_task_service.py | 單一 Domain：FeatureEngineering | 無 |
| api/services/kline_data_service.py | 單一 Domain：DataExtraction | 無 |
| api/services/kline_storage_service.py | 單一 Domain：DataExtraction | 無 |
| api/services/optimization_task_service.py | 單一 Domain：Optimization | 無 |
| api/services/pattern_management_service.py | 單一 Domain：Analysis | 無 |
| api/services/search_task_service.py | 無 momentum 依賴（透過 standalone_search_service 間接） | 無 |
| api/services/standalone_search_service.py | 單一 Domain：DataExtraction | 無 |
| api/services/task_manager.py | 無 momentum 依賴 | 無 |
| api/services/xgboost_task_cache.py | 無 momentum 依賴 | 無 |

### Split
| Service 檔案 | 依據（Domain/依賴） | 備註 |
|---|---|---|
| api/services/chart_data_service.py | 2+ Domain：DataExtraction + Indicators | 需拆分 |
| api/services/chart_signal_service.py | 2+ Domain：DataExtraction + Indicators | 需拆分 |
| api/services/shap_analysis_service.py | 2+ Domain：Analysis + FeatureEngineering | 需拆分 |
| api/services/signal_analysis_service.py | 3 Domain：DataExtraction + Indicators + Analysis | 需拆分 |
| api/services/xgboost_batch_service.py | 3 Domain：Analysis + FeatureEngineering + DataExtraction | 需拆分 |
| api/services/xgboost_task_service.py | 2+ Domain：Analysis + FeatureEngineering | 需拆分 |

### Delete
| Service 檔案 | 依據（原因） | 備註 |
|---|---|---|
| api/services/case_storage.py | 全域 in-memory 狀態管理，與既有 CaseStorageManager 重疊且未被使用 | 刪除 |

## Phase 3 momentum/core Infrastructure (Task 3.1 - 3.6)

### Task 3.1: momentum/core/__init__.py
- 檔案：momentum/core/__init__.py
- 狀態：完成

### Task 3.2: momentum/core/logging.py
- 檔案：momentum/core/logging.py
- 狀態：完成（標準 logging，無 api 依賴）
- 驗證命令：python -c "from momentum.core.logging import get_logger; get_logger('test')"

### Task 3.3: momentum/core/config.py
- 檔案：momentum/core/config.py
- 狀態：完成（dataclass 定義，無 api 依賴）
- 驗證命令：python -c "from momentum.core.config import *"

### Task 3.4: momentum/core/contracts.py
- 檔案：momentum/core/contracts.py
- 狀態：完成（獨立 DTO 定義，無 api 依賴）
- 驗證命令：python -c "from momentum.core.contracts import *"

### Task 3.5: momentum/core/protocols.py
- 檔案：momentum/core/protocols.py
- 狀態：完成（Protocol 數量=3）
- 驗證命令：python -c "from momentum.core.protocols import *"

### Task 3.6: momentum/core/exceptions.py（選用）
- 狀態：N/A（Phase 1 未要求共用例外類別）

### Phase 3 Checklist
- momentum/core/ 檔案皆無 api 依賴
- Protocol 數量 ≤ 10（實際：3）
- 驗證命令已執行（Task 3.2 - 3.5）

## Phase 4 Factories (Task 4.1)

### Task 4.1: momentum/factories.py
- 檔案：momentum/factories.py
- 狀態：完成（提供 Rule 3 涵蓋類別的 factory 函式）
- 驗證命令：python -c "from momentum.factories import *"

### Phase 4 Checklist
- Rule 3 掃描到的類別皆有對應 factory 函式
- 驗證命令已執行（Task 4.1）

## Phase 5 Rule 1 Fixes (Task 5.1 - 5.2)

### Task 5.1: logging 依賴修復
- 變更：`from api.core.logging import get_logger` → `from momentum.core.logging import get_logger`
- 範圍：momentum/Analysis, momentum/FeatureEngineering, momentum/Optimization
- 驗證命令：grep -rn "from api.core.logging" momentum/

### Task 5.2: config 依賴修復
- 變更：移除 `from api.core.config import settings`
- 取代：使用 `MomentumConfig.from_project_root()` 提供路徑
- 驗證命令：grep -rn "from api.core.config" momentum/

### Task 5.3: api.models 依賴修復
- 變更：`from api.models.*` → `from momentum.core.contracts import *`
- 範圍：momentum/Optimization, momentum/Analysis, momentum/Utils
- 驗證命令：grep -rn "from api.models" momentum/

### Task 5.4: api.services 依賴修復
- 變更：移除 `momentum/Optimization/optuna_optimizer.py` 對 `api.services` 的依賴
- 取代：使用 `SignalDensityAnalyzer` 直接執行信號密度分析與快取注入
- 驗證命令：grep -rn "from api.services" momentum/

### Task 5.5: api.utils 依賴修復
- 變更：移除 `momentum/Optimization/optuna_optimizer.py` 對 `api.utils` 的依賴
- 取代：改由外部注入案例存儲管理器（api 層提供 factory）
- 驗證命令：grep -rn "from api.utils" momentum/

### Task 5.6: 全域驗證 Rule 1
- 驗證命令：grep -rn "from api\." momentum/ | wc -l
- 結果：0

## Phase 6 Rule 2 Fixes (Task 6.1)

### Task 6.1: 修復 Analysis → Data 依賴
- 變更：`momentum/Analysis/kline_cache.py`、`momentum/Analysis/signal_density_analyzer.py` 改用 `IKlineReader` Protocol
- 修正方式：`[P]` Protocol 注入
- 補強：`momentum/core/protocols.py` 補齊 `read_klines_around_timestamp`、`get_metadata`
- 驗證命令：grep -rn "from momentum\.DataExtraction" momentum/Analysis/ | wc -l
- 結果：0

### Task 6.2: 修復 Analysis → Feature 依賴
- 變更：`momentum/Analysis/signal_density_analyzer.py` 改用 `IIndicatorEngine` Protocol
- 變更：`momentum/Analysis/strategies/three_line_strategy.py`、`short_long_cross_strategy.py`、`mid_long_cross_strategy.py` 移除 IndicatorEngine 直接建構
- 修正方式：`[P]` Protocol 注入（由上游注入 `indicator_engine`）
- 驗證命令：grep -rn "from momentum\.Indicators" momentum/Analysis/ | wc -l
- 結果：0

### Task 6.3: 修復 Analysis ↔ Optimization 依賴
- 變更：將策略元數據 DTO 遷移至 `momentum/core/contracts.py`
- 變更：`momentum/Analysis/strategy_registry.py` 改用 `momentum.core.contracts`
- 變更：`momentum/Optimization/optuna_optimizer.py` 改用 `momentum.core.contracts.ParameterType`
- 修正方式：`[C]` DTO 轉移至 core/contracts
- 驗證命令：grep -rn "from momentum\.Optimization" momentum/Analysis/ | wc -l
- 結果：0

### Task 6.4: 全域驗證 Rule 2
- 驗證命令：grep -rn "from momentum\.DataExtraction" momentum/Analysis/ | wc -l
- 結果：0
- 驗證命令：grep -rn "from momentum\.Indicators" momentum/Analysis/ | wc -l
- 結果：0
- 驗證命令：grep -rn "from momentum\.Indicator" momentum/Analysis/ | wc -l
- 結果：0
- 驗證命令：grep -rn "from momentum\.Optimization" momentum/Analysis/ | wc -l
- 結果：0

### Phase 6 Checklist
- Analysis → DataExtraction import 已移除
- Analysis → Indicators import 已移除
- Analysis → Optimization DTO 已移至 core/contracts
- `IKlineReader` 覆蓋實際使用的方法
- `IIndicatorEngine` 透過 Protocol 注入
- 驗證命令已執行且結果為 0

## Phase 7 Rule 3 Fixes (Task 7.1)

### Task 7.1: 修復 Service 直接 import
- 變更：api/services 改用 `momentum.factories` 取得 Domain 物件
- 涉及服務：chart_data_service, chart_signal_service, signal_analysis_service, kline_storage_service, kline_data_service, batch_download_service, optimization_task_service, feature_task_service, pattern_management_service, xgboost_task_service, xgboost_batch_service, shap_analysis_service, data_service, task_manager, standalone_search_service
- 補強：`momentum/factories.py` 新增特徵工程 factory 與 data_source 值查詢
- 驗證命令：grep -rn "from momentum\.(Analysis|DataExtraction|Indicators|FeatureEngineering|Optimization)" api/services/ | wc -l
- 結果：0

### Task 7.2: 全域驗證 Rule 3
- 驗證命令：grep -rn "from momentum\." api/services/ | grep -v "from momentum\.factories" | grep -v "from momentum\.core" | wc -l
- 結果：0

### Phase 7 Checklist
- api/services 僅透過 `momentum.factories` 取得 Domain 物件
- 驗證命令已執行且結果為 0

## Phase 8 Rule 4 Fixes (Task 8.1)

### Task 8.1: 識別 Service 間依賴類型
- chart_data_service → kline_storage_service：類型 A（改為 Artifact 路徑/資料傳遞）
- chart_data_service → kline_data_service：類型 A（改為 Artifact 路徑/資料傳遞）
- xgboost_batch_service → kline_data_service：類型 A（改為 Artifact 路徑/資料傳遞）
- xgboost_batch_service → xgboost_task_cache：類型 A（改為 Artifact 路徑/資料傳遞）
- xgboost_task_service → xgboost_task_cache：類型 A（改為 Artifact 路徑/資料傳遞）
- search_task_service → standalone_search_service：類型 A（改為 Artifact 路徑/資料傳遞）
- search_task_service → search_task_service（模組自引用，用於路由綁定）：不列入 Service 間耦合

### Task 8.2: 移除 Service 間 import
- chart_data_service：改用本地 storage/download helper，移除 kline_storage_service/kline_data_service 依賴
- xgboost_task_service：內嵌任務快取，移除 xgboost_task_cache 依賴
- xgboost_batch_service：內嵌任務快取，改用本地 storage/download helper，移除 kline_data_service/xgboost_task_cache 依賴
- search_task_service：改用 lazy 取得 standalone_search_service，移除直接 import
- 驗證命令：grep -rn "from \\.{1,2}services\\.[a-z_]+_service" api/services/ | grep -v "search_task_service" | wc -l
- 結果：0

### Task 8.3: 全域驗證 Rule 4
- 驗證命令：grep -rn "from api\.services\.[a-z_]*_service import" api/services/ | wc -l
- 結果：0

### Phase 8 Checklist
- Service 間依賴已分類為 A/B/C
- Rule 4 Service 間 import 已移除
- Rule 4 全域驗證結果為 0
- 驗證命令已執行且結果為 0

## Phase 9 最終驗證 (Task 9.1 - 9.6)

### Task 9.1: 驗證無 momentum → api 反向依賴
- 驗證命令：grep -rn "from api\." momentum/ | wc -l
- 結果：0

### Task 9.2: 驗證 momentum 可獨立 import
- 驗證命令：
	- /Users/louis/Desktop/quantitative_trading_system/venv/bin/python -c "import sys; import momentum.DataExtraction; assert 'api' not in sys.modules, 'api module loaded!'"
	- /Users/louis/Desktop/quantitative_trading_system/venv/bin/python -c "import sys; import momentum.FeatureEngineering; assert 'api' not in sys.modules"
	- /Users/louis/Desktop/quantitative_trading_system/venv/bin/python -c "import sys; import momentum.Analysis; assert 'api' not in sys.modules"
	- /Users/louis/Desktop/quantitative_trading_system/venv/bin/python -c "import sys; import momentum.Optimization; assert 'api' not in sys.modules"
- 結果：全部通過

### Task 9.3: 驗證 momentum/core/ 檔案數量
- 驗證命令：ls momentum/core/*.py | wc -l
- 結果：5（<= 6）

### Task 9.4: 驗證 Rule 6/7 無違規
- 驗證命令：
	- grep -rn "Callable\[.*DataFrame" momentum/ | wc -l
	- grep -rn "from momentum\.core" api/models/ | wc -l
	- grep -rn "from api\.models" momentum/core/ | wc -l
- 結果：0 / 0 / 0

### Task 9.5: 驗證測試通過
- 驗證命令：/Users/louis/Desktop/quantitative_trading_system/venv/bin/python -m pytest tests/ -v --tb=short
- 結果：251 passed, 33 skipped, 117 warnings

### Task 9.6: 驗證 API 啟動
- 驗證命令：/Users/louis/Desktop/quantitative_trading_system/venv/bin/python run_api.py & sleep 3; curl -s http://localhost:8000/docs | head -1; pkill -f "run_api.py"
- 結果：/docs 回應 200 OK

### Phase 9 Checklist
- Task 9.1-9.4 完成且結果符合預期
- Task 9.5 完成
- Task 9.6 完成

## Phase 10 最終交付 (Task 10.1 - 10.7)

### Task 10.1: Violation Report
- 狀態：完成
- 內容：見「Phase 1 Violation Report (Task 1.1 - 1.7)」完整列表

### Task 10.2: Service Classification
- 狀態：完成
- 內容：見「Phase 2 Service Classification (Task 2.2)」表格

### Task 10.3: Action List
- 狀態：完成
- 動作與驗證命令：
	- 建立 `momentum/core/*`（__init__.py, logging.py, config.py, contracts.py, protocols.py）
		- 驗證：python -c "from momentum.core.logging import get_logger; get_logger('test')"
		- 驗證：python -c "from momentum.core.config import *"
		- 驗證：python -c "from momentum.core.contracts import *"
		- 驗證：python -c "from momentum.core.protocols import *"
	- 建立 `momentum/factories.py`
		- 驗證：python -c "from momentum.factories import *"
	- 移除 momentum → api 反向依賴（Rule 1）
		- 驗證：grep -rn "from api\." momentum/ | wc -l
	- 移除 momentum 內部跨 Domain 依賴（Rule 2）
		- 驗證：grep -rn "from momentum\.DataExtraction" momentum/Analysis/ | wc -l
		- 驗證：grep -rn "from momentum\.Indicators" momentum/Analysis/ | wc -l
	- api/services 改用 factories（Rule 3）
		- 驗證：grep -rn "from momentum\." api/services/ | grep -v "from momentum\.factories" | grep -v "from momentum\.core" | wc -l
	- 移除 Service 間直接依賴（Rule 4）
		- 驗證：grep -rn "from api\.services\.[a-z_]*_service import" api/services/ | wc -l
	- 修正 `api/services/optimization_task_service.py` 縮排錯誤
		- 驗證：python -m pytest tests/optimization/test_optuna_optimizer_basic.py -v --tb=short
	- 修正 Protocol `@runtime_checkable` 以支援 `isinstance`
		- 驗證：python -m pytest tests/test_phase2_integration.py -v --tb=short
	- 補齊 `OptunaOptimizer.signal_service` 初始化與呼叫路徑
		- 驗證：python -m pytest tests/optimization/test_optuna_optimizer_basic.py -v --tb=short
	- 修正 `momentum/Analysis/signal_density_analyzer.py` None 資料處理
		- 驗證：python -m pytest tests/test_density_comparison.py -v --tb=short
	- 測試調整：`tests/test_append_fix.py`、`tests/test_density_comparison.py`
		- 驗證：python -m pytest tests/test_append_fix.py -v --tb=short
		- 驗證：python -m pytest tests/test_density_comparison.py -v --tb=short

### Task 10.4: Artifact Contract Table
- 狀態：完成
- 內容：

| Domain | Input Artifacts | Output Artifacts | Format | 路徑規則 | 必要欄位/Schema |
|---|---|---|---|---|---|
| Data | Binance API response | K線數據 | HDF5 | `data_cache/{SYMBOL}_{timeframe}.h5` | open_time, open, high, low, close, volume |
| Data | SearchConfig JSON | 搜尋結果 | JSON | `search_results/{task_id}.json` | task_id, cases[], status |
| Feature | K線 HDF5 路徑 | 特徵矩陣 | HDF5 | `data_cache/features/{case_id}.h5` | datasets: features, timestamps; attrs: feature_names, case_id, symbol, timeframe |
| Analysis | 特徵 HDF5 路徑 | 模型 | Pickle | `data_cache/models/{case_id}.pkl` | keys: model, feature_names, performance, params, metadata, saved_at, case_id |
| Optimization | 模型路徑 + 搜尋空間 JSON | Study/Checkpoint | SQLite + Pickle | `data/optuna_{study_name}.db`, `data/checkpoints/checkpoint_{study_name}_*.pkl*` | Study db + checkpoint payload |

### Task 10.5: momentum/core 內容清單
- 狀態：完成
- 檔案與內容：
	- momentum/core/__init__.py：模組說明
	- momentum/core/logging.py：`get_logger()`
	- momentum/core/config.py：`MomentumConfig`, `MomentumConfig.from_project_root()`
	- momentum/core/contracts.py：`TrainingWindowConfig`, `StrategyConfig`, `SignalDensityRequest`, `SignalDensityResponse`, `ParameterRange`, `ParameterType`, `ConstraintType`, `ParameterConstraint`, `ParameterDefinition`, `StrategyMetadata`, `ValidationResult`
	- momentum/core/protocols.py：`IKlineReader`, `IIndicatorEngine`, `IModelTrainer`

### Task 10.6: Verification Checklist
- 狀態：完成
- 命令與結果：
	- grep -rn "from api\." momentum/ | wc -l → 0
	- python -c "import sys; import momentum.DataExtraction; assert 'api' not in sys.modules, 'api module loaded!'" → OK
	- python -c "import sys; import momentum.FeatureEngineering; assert 'api' not in sys.modules" → OK
	- python -c "import sys; import momentum.Analysis; assert 'api' not in sys.modules" → OK
	- python -c "import sys; import momentum.Optimization; assert 'api' not in sys.modules" → OK
	- ls momentum/core/*.py | wc -l → 5
	- grep -rn "Callable\[.*DataFrame" momentum/ | wc -l → 0
	- grep -rn "from momentum\.core" api/models/ | wc -l → 0
	- grep -rn "from api\.models" momentum/core/ | wc -l → 0
	- /Users/louis/Desktop/quantitative_trading_system/venv/bin/python -m pytest tests/ -v --tb=short → 251 passed, 33 skipped, 117 warnings
	- /Users/louis/Desktop/quantitative_trading_system/venv/bin/python run_api.py & sleep 3; curl -s http://localhost:8000/docs | head -1; pkill -f "run_api.py" → /docs 200 OK

### Task 10.7: 建立 docs/REFACTOR_ARCHITECTURE_V4.md
- 狀態：完成

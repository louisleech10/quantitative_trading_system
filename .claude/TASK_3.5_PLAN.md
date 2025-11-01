# 任務3.5：Optuna參數優化系統 - 實作計劃

## 文檔資訊
- **任務編號**: Phase 3 任務3.5
- **優先級**: 🔥🔥🔥 P0 (最高)
- **預估時間**: 7-8天（包含進階優化策略與視覺化）
- **前置需求**: 
  - 任務3.1完成（指標計算引擎）
  - 任務3.2完成（信號密度分析系統）
  - 任務3.3完成（策略選擇UI）
- **創建日期**: 2025-10-31
- **最後更新**: 2025-10-31（整合進階優化與視覺化為標準功能）

---

## 核心目標

**目標**: 自動優化策略參數，最大化正反例信號密度差異（separation）

**優化目標函數**:
```
maximize: (正例平均信號密度) - (反例平均信號密度)
```

**關鍵功能**:
- 自動搜索最佳EMA參數組合（短/中/長期週期）
- 支援多種優化器（TPE/CmaEs/RandomSearch/GaussianProcess/NSGA-II）
- 多目標優化（同時最大化separation和穩定性）
- 並行多進程優化（充分利用M1 8核心）
- 斷點續跑機制（SQLite持久化Study）
- 容錯與穩健性機制（錯誤重試、進度監控、自動重啟、數據完整性檢查）
- 實時進度追蹤與通知（終端/WebSocket/Line/Email）
- 高級視覺化（參數空間熱力圖、3D視覺化、收斂曲線）
- 優化歷史記錄與結果分析

**Optuna可調參數**:
1. **搜索空間參數**:
   - EMA短期週期：5-200（int）
   - EMA中期週期：10-200（int）
   - EMA長期週期：20-200（int）
   - 數據源：7種選擇（categorical）
   - 策略邏輯：3種選擇（categorical）

2. **優化器參數**:
   - Sampler類型：TPE/CmaEs/RandomSearch/GP/NSGA-II
   - 試驗次數：100-1000
   - 並行核心數：1-8
   - Random seed：可重現性
   - 多目標權重：separation權重 vs 穩定性權重（NSGA-II）

3. **剪枝參數**:
   - Pruner類型：MedianPruner/PercentilePruner
   - Warmup步數：前N次試驗不剪枝
   - 中位數剪枝閾值

4. **容錯參數**:
   - 最大重試次數：3
   - 檢查點保存頻率：每50次試驗
   - 超時時間：每次試驗最長時間

---

## STEP 1: Optuna核心優化引擎

**目標**: 實作Optuna優化核心邏輯，整合信號密度分析系統

### 1.1 優化器核心類

**新增文件**: `momentum/Optimization/optuna_optimizer.py`

**核心類**: `OptunaOptimizer`

**初始化參數**:
- `study_name`: Study名稱（用於SQLite存儲）
- `storage`: SQLite數據庫路徑（如 "sqlite:///optuna_study.db"）
- `sampler_type`: 優化器類型（TPE/CmaEs/RandomSearch）
- `pruner_type`: 剪枝器類型（Median/Percentile/None）
- `n_trials`: 試驗次數
- `n_jobs`: 並行核心數
- `timeout`: 總優化超時（秒）
- `random_seed`: 隨機種子（可重現性）

**關鍵方法**:

1. **`create_study()`**: 創建或載入Optuna Study
   - 功能：
     - 檢查SQLite數據庫是否存在該Study
     - 存在則載入（斷點續跑）
     - 不存在則創建新Study
   - 配置：
     - direction="maximize"（最大化密度差異）
     - sampler配置（TPESampler/CmaEsSampler/RandomSampler）
     - pruner配置（MedianPruner/PercentilePruner）
   - 返回：optuna.Study對象

2. **`objective_function(trial)`**: 目標函數（核心算法）
   - 輸入：optuna.Trial對象
   - 流程：
     - **參數採樣**：
       - `data_source = trial.suggest_categorical('data_source', ['close', 'open', ...])`
       - `strategy_logic = trial.suggest_categorical('strategy_logic', ['three_line', ...])`
       - `ema_short = trial.suggest_int('ema_short', 5, 200)`
       - `ema_mid = trial.suggest_int('ema_mid', 10, 200)` （僅三線排列）
       - `ema_long = trial.suggest_int('ema_long', 20, 200)`
     - **參數驗證**：
       - 三線排列：確保 ema_short < ema_mid < ema_long
       - 雙線策略：確保 ema_short < ema_long
       - 不合法則拋出optuna.TrialPruned()
     - **調用信號密度分析**：
       - 組裝SignalDensityRequest
       - 調用`signal_analysis_service.analyze_signal_density()`
       - 獲取SignalDensityResponse
     - **計算目標值**：
       - separation = positive_avg_density - negative_avg_density
     - **中間值報告**（可選，用於剪枝）：
       - trial.report(separation, step)
       - trial.should_prune() → raise optuna.TrialPruned()
   - 錯誤處理：
     - try-catch包裹，記錄錯誤
     - 返回極差值（如-999）或拋出TrialPruned
   - 返回：separation（密度差異）

3. **`optimize()`**: 執行優化
   - 流程：
     - 調用`create_study()`
     - study.optimize(objective_function, n_trials, n_jobs, timeout)
     - 捕獲KeyboardInterrupt（允許用戶中斷）
     - 保存最終結果
   - 並行策略：
     - n_jobs > 1：多進程並行
     - n_jobs = 1：單進程串行
   - 返回：OptimizationResult對象

4. **`get_best_trial()`**: 獲取最佳試驗
   - 返回：
     - best_params: 最佳參數字典
     - best_value: 最佳目標值
     - best_trial_number: 試驗編號

5. **`get_trials_dataframe()`**: 獲取試驗歷史
   - 返回：pandas.DataFrame
   - 欄位：trial_number, params, value, state, datetime

**技術要點**:
- SQLite持久化（study.db自動保存每次試驗）
- 向量化計算（目標函數內調用已優化的density分析）
- 錯誤分類（可重試 vs 不可重試）
- 詳細日誌（每次試驗記錄參數和結果）

**驗收標準**:
- ✅ Study創建/載入正確
- ✅ 目標函數計算準確
- ✅ 參數採樣合理（符合約束）
- ✅ 並行優化穩定
- ✅ 斷點續跑生效

---

### 1.2 Sampler配置工廠（含進階優化器）

**新增方法**: `OptunaOptimizer._create_sampler()`

**支援的Sampler**:

1. **TPESampler**（預設，推薦）:
   - 優點：適合大多數場景，收斂快
   - 參數：
     - `n_startup_trials`: 前期隨機試驗數（預設25）
     - `n_ei_candidates`: 期望改善候選數（預設24）
     - `seed`: 隨機種子

2. **CmaEsSampler**:
   - 優點：適合連續參數空間
   - 參數：
     - `n_startup_trials`: 前期隨機試驗數
     - `seed`: 隨機種子

3. **RandomSampler**:
   - 優點：基準對比
   - 參數：
     - `seed`: 隨機種子

4. **GPSampler（Gaussian Process Sampler）** ⭐ 新增:
   - 優點：貝葉斯優化，適合昂貴目標函數
   - 使用場景：單次試驗耗時長（>10秒），試驗次數少（<100）
   - 參數：
     - `seed`: 隨機種子
     - `independent_sampler`: 前期使用的採樣器（預設RandomSampler）
     - `n_startup_trials`: 前期隨機試驗數（預設10）
   - 實作：使用sklearn的GaussianProcessRegressor

5. **NSGAIISampler（遺傳算法，多目標優化）** ⭐ 新增:
   - 優點：同時優化多個目標（如separation + 穩定性）
   - 使用場景：需要在多個指標間取得平衡
   - 參數：
     - `population_size`: 種群大小（預設50）
     - `mutation_prob`: 變異概率（預設0.1）
     - `crossover_prob`: 交叉概率（預設0.9）
     - `seed`: 隨機種子
   - 返回：Pareto前沿解集（多個非支配解）

**實作**:
```python
def _create_sampler(self, sampler_type: str, seed: int, **kwargs):
    if sampler_type == 'TPE':
        return optuna.samplers.TPESampler(seed=seed)
    elif sampler_type == 'CmaEs':
        return optuna.samplers.CmaEsSampler(seed=seed)
    elif sampler_type == 'Random':
        return optuna.samplers.RandomSampler(seed=seed)
    elif sampler_type == 'GP':
        return optuna.samplers.GPSampler(seed=seed, n_startup_trials=kwargs.get('n_startup_trials', 10))
    elif sampler_type == 'NSGA-II':
        return optuna.samplers.NSGAIISampler(
            population_size=kwargs.get('population_size', 50),
            mutation_prob=kwargs.get('mutation_prob', 0.1),
            crossover_prob=kwargs.get('crossover_prob', 0.9),
            seed=seed
        )
    else:
        raise ValueError(f"Unknown sampler: {sampler_type}")
```

**驗收標準**:
- ✅ 五種Sampler可切換（TPE/CmaEs/Random/GP/NSGA-II）
- ✅ 隨機種子生效（結果可重現）
- ✅ GP適用於昂貴目標函數場景
- ✅ NSGA-II返回Pareto前沿解集

---

### 1.3 Pruner配置工廠

**新增方法**: `OptunaOptimizer._create_pruner()`

**支援的Pruner**:

1. **MedianPruner**（預設）:
   - 功能：當試驗結果低於中位數時剪枝
   - 參數：
     - `n_startup_trials`: 前N次不剪枝（預設5）
     - `n_warmup_steps`: 每個試驗前N步不剪枝
     - `interval_steps`: 檢查間隔

2. **PercentilePruner**:
   - 功能：當試驗結果低於第P百分位時剪枝
   - 參數：
     - `percentile`: 百分位閾值（如25.0）
     - `n_startup_trials`: 前N次不剪枝

3. **NopPruner**:
   - 功能：不剪枝

**實作**:
```python
def _create_pruner(self, pruner_type: str):
    if pruner_type == 'Median':
        return optuna.pruners.MedianPruner(n_startup_trials=5)
    elif pruner_type == 'Percentile':
        return optuna.pruners.PercentilePruner(percentile=25.0)
    elif pruner_type is None:
        return optuna.pruners.NopPruner()
    else:
        raise ValueError(f"Unknown pruner: {pruner_type}")
```

**驗收標準**:
- ✅ 剪枝器正確觸發
- ✅ 差勁試驗提前終止
- ✅ Warmup機制生效

---

## STEP 1.4: 多目標優化支援 ⭐ 新增

**目標**: 同時優化多個指標，在separation和穩定性間取得平衡

**多目標函數定義**:
```python
def multi_objective_function(trial):
    # 目標1: 最大化separation
    separation = positive_avg_density - negative_avg_density
    
    # 目標2: 最小化變異係數（提高穩定性）
    cv = std_density_diff / mean_density_diff
    stability_score = 1.0 - min(cv, 1.0)  # 轉換為最大化問題
    
    return separation, stability_score  # 返回兩個目標值
```

**Pareto前沿分析**:
- NSGA-II返回多個非支配解（Pareto optimal solutions）
- 每個解在separation和穩定性間有不同權衡
- 使用者可根據需求選擇合適的解

**視覺化**:
- 2D散點圖：X軸separation，Y軸stability_score
- 高亮Pareto前沿上的解
- 互動式選擇最佳平衡點

**涉及模組**:
- 修改: `momentum/Optimization/optuna_optimizer.py`（新增multi_objective模式）
- 新增: `momentum/Analysis/pareto_analyzer.py`（Pareto前沿分析）

**驗收標準**:
- ✅ 雙目標優化正常運作
- ✅ Pareto前沿正確計算
- ✅ 提供3-5個推薦平衡點
- ✅ 視覺化清晰易懂

---

## STEP 2: 容錯與穩健性機制（已從Roadmap整合）

**目標**: 確保長時間運行（8小時+）的優化穩定可靠

**說明**: 本STEP完整整合了PATTERN_DISCOVERY_ROADMAP.md中「任務3.5補充：容錯與穩健性機制」的所有內容

### 2.1 斷點續跑機制

**新增文件**: `momentum/Optimization/checkpoint_manager.py`

**核心類**: `CheckpointManager`

**功能**:
1. **SQLite自動持久化**:
   - Optuna原生支援，Study自動保存到SQLite
   - 位置：`optuna_study.db`
   - 重啟後調用`optuna.load_study()`自動續跑

2. **手動檢查點保存**（額外保護）:
   - 每50次試驗保存完整檢查點
   - 保存內容：
     - 當前最佳參數
     - 試驗歷史（DataFrame）
     - 統計資訊（均值、標準差、收斂曲線）
   - 格式：pickle檔案（`checkpoint_trial_{N}.pkl`）

3. **檢查點載入**:
   - 手動載入任一檢查點恢復
   - 驗證檢查點完整性
   - 與SQLite數據一致性檢查

**關鍵方法**:
- `save_checkpoint(study, trial_number)`
- `load_checkpoint(checkpoint_path)`
- `list_checkpoints()`
- `validate_checkpoint(checkpoint_path)`

**驗收標準**:
- ✅ 電腦當機後可從SQLite續跑
- ✅ 檢查點每50次自動保存
- ✅ 手動載入檢查點成功
- ✅ 無重複計算已完成試驗

---

### 2.2 錯誤處理與重試

**新增文件**: `momentum/Optimization/error_handler.py`

**核心類**: `OptimizationErrorHandler`

**錯誤分類**:
1. **可重試錯誤**（RetryableError）:
   - 網絡錯誤（API調用失敗）
   - 暫時性記憶體不足
   - 數據讀取錯誤（HDF5臨時鎖定）
   - 策略：自動重試，最多3次，exponential backoff

2. **不可重試錯誤**（NonRetryableError）:
   - 參數驗證失敗（ema_short > ema_long）
   - 數據損壞（HDF5檔案損壞）
   - 配置錯誤（無效的案例ID）
   - 策略：記錄並拋出TrialPruned，不重試

3. **致命錯誤**（FatalError）:
   - 系統級錯誤（磁碟滿、進程崩潰）
   - 策略：記錄、告警、終止優化

**關鍵方法**:
- `classify_error(exception) -> ErrorType`
- `handle_trial_error(trial, exception) -> bool`（返回是否應重試）
- `log_error(trial_number, error_type, exception, traceback)`

**錯誤日誌格式**:
```
[ERROR] Trial 123 failed with RetryableError (attempt 2/3)
Type: NetworkError
Message: API request timeout
Params: {data_source: 'close', ema_short: 7, ...}
Traceback: ...
Action: Retrying in 5 seconds
```

**驗收標準**:
- ✅ 暫時性錯誤自動重試
- ✅ 不可重試錯誤正確跳過
- ✅ 錯誤日誌詳細清晰
- ✅ 錯誤不影響整體優化

---

### 2.3 進度監控與通知

**新增文件**: `momentum/Optimization/progress_monitor.py`

**核心類**: `ProgressMonitor`

**實時進度顯示**:
- 當前完成試驗數 / 總試驗數
- 完成百分比
- 當前最佳值和參數
- 預計剩餘時間（基於平均試驗時間）
- 試驗完成速度（trials/hour）

**階段性通知**:
- 每100次試驗：進度更新
- 達到新最佳值：即時通知
- 完成25%/50%/75%里程碑：提醒
- 優化完成：總結報告

**通知管道**（優先級排序）:
1. **終端機即時輸出**（必須）:
   - 使用tqdm進度條
   - 彩色輸出（rich庫）
   - 即時刷新

2. **日誌檔案記錄**（必須）:
   - 位置：`logs/optimization_{timestamp}.log`
   - 格式：結構化JSON log

3. **WebSocket實時推送** ⭐ 新增（標準功能）:
   - 前端訂閱WebSocket channel
   - 後端每完成1次試驗推送更新
   - 無需輪詢，降低伺服器負載
   - 斷線自動重連機制
   - 涉及：api/websocket/optimization_ws.py

4. **Line Notify推送**（可選）:
   - 達到新最佳值時推送
   - 優化完成時推送
   - 配置：LINE_NOTIFY_TOKEN環境變數

5. **Email通知**（可選）:
   - 優化完成時發送郵件
   - 附帶結果摘要和圖表

**監控指標**:
- 試驗完成速度（trials/hour）
- 記憶體使用量（psutil監控）
- CPU使用率（psutil監控）
- 最佳值收斂曲線（即時繪製）

**終端輸出範例**:
```
Optuna Optimization Progress
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Trial: 156/300 (52%)  ⏱ ETA: 1h 23m
Current Best: 0.4723 (Trial #89)
Params: {data_source: 'close', strategy: 'three_line', 
         ema_short: 7, ema_mid: 18, ema_long: 35}
Speed: 23.5 trials/hour
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**關鍵方法**:
- `start_monitoring()`
- `update_progress(trial_number, current_value)`
- `report_new_best(trial_number, best_value, best_params)`
- `report_milestone(percentage)`
- `generate_summary_report()`

**驗收標準**:
- ✅ 進度條即時更新
- ✅ ETA計算準確
- ✅ 新最佳值通知即時
- ✅ 日誌記錄完整

---

### 2.4 數據完整性檢查

**新增文件**: `momentum/Utils/data_validator.py`

**核心類**: `OptimizationDataValidator`

**啟動前檢查**:
1. **預計算指標檔案存在性**（如需預計算）:
   - 檢查所有案例的K線數據可讀取
   - 驗證HDF5檔案完整性

2. **數據無NaN或缺失值**:
   - 抽樣檢查10%案例
   - 驗證K線數據完整

3. **案例索引完整性**:
   - 驗證正例/反例案例ID有效
   - 檢查symbol/timeframe/timestamp合法

**運行中檢查**（每500次試驗）:
- 定期抽樣驗證計算結果
- 檢查信號密度範圍合理（0-1）
- 監控異常值出現頻率
- 驗證正反例標籤正確

**失敗處理**:
- 檢查失敗時記錄詳細資訊
- 嘗試自動修復（重新載入數據）
- 無法修復時終止並告警
- 提供修復建議

**健康檢查報告**:
```
Data Validation Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ HDF5 files accessible: 150/150
✓ No NaN values detected
✓ Signal density range: [0.0, 1.0]
✓ Case labels correct: 100%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**關鍵方法**:
- `validate_before_optimization(cases)`
- `validate_runtime(trial_results)`
- `generate_health_report()`

**驗收標準**:
- ✅ 啟動前檢查通過
- ✅ 運行中檢查不影響性能
- ✅ 數據問題及時發現

---

## STEP 3: FastAPI服務層整合

**目標**: 封裝Optuna優化為異步FastAPI服務，提供HTTP API

### 3.1 優化任務服務

**新增文件**: `api/services/optimization_service.py`

**核心類**: `OptimizationService`

**關鍵方法**:

1. **`start_optimization(request: OptimizationRequest)`**: 啟動優化
   - 輸入：OptimizationRequest
     - strategy_config: 策略配置範圍
     - training_window: 訓練窗口配置
     - positive_cases: 正例案例列表
     - negative_cases: 反例案例列表
     - optuna_config: Optuna配置
   - 流程：
     - 生成task_id（UUID）
     - 創建異步任務（asyncio.create_task）
     - 調用`_run_optimization_task()`
     - 立即返回task_id（非阻塞）
   - 返回：`{"task_id": "...", "status": "started"}`

2. **`_run_optimization_task(task_id, request)`**: 執行優化（後台任務）
   - 流程：
     - 更新任務狀態為"running"
     - 初始化OptunaOptimizer
     - 啟動ProgressMonitor
     - 執行optimize()
     - 更新任務狀態為"completed"
     - 保存結果到task_results[task_id]
   - 錯誤處理：
     - 捕獲所有異常
     - 更新任務狀態為"failed"
     - 記錄錯誤詳情

3. **`get_optimization_status(task_id)`**: 查詢優化狀態
   - 返回：
     - status: running/completed/failed
     - progress: 當前進度（試驗數/總數）
     - current_best: 當前最佳值
     - best_params: 當前最佳參數
     - elapsed_time: 已用時間
     - eta: 預計剩餘時間

4. **`get_optimization_result(task_id)`**: 獲取優化結果
   - 返回：OptimizationResult
     - best_trial: 最佳試驗資訊
     - trials_dataframe: 試驗歷史
     - convergence_plot: 收斂曲線數據
     - param_importance: 參數重要性

5. **`cancel_optimization(task_id)`**: 取消優化
   - 功能：中斷正在運行的優化任務
   - 保存當前進度

**任務狀態管理**:
- 使用內存字典：`task_results: Dict[str, OptimizationTaskState]`
- TaskState包含：
  - status: str
  - progress: Dict
  - result: OptimizationResult（完成時）
  - error: str（失敗時）

**驗收標準**:
- ✅ 異步任務正確創建
- ✅ 任務狀態即時更新
- ✅ 多個任務可並行
- ✅ 錯誤處理完整

---

### 3.2 數據模型定義

**新增文件**: `api/models/optimization_models.py`

**核心模型**:

1. **`OptimizationRequest`**: 優化請求
   ```python
   strategy_config: StrategySearchSpace  # 搜索空間
   training_window: TrainingWindowConfig
   positive_cases: List[str]  # 案例ID列表
   negative_cases: List[str]
   optuna_config: OptunaConfig
   ```

2. **`StrategySearchSpace`**: 策略搜索空間
   ```python
   data_sources: List[str]  # 可選數據源
   indicator_types: List[str]  # 可選指標類型
   strategy_logics: List[str]  # 可選策略邏輯
   ema_short_range: Tuple[int, int]  # (min, max)
   ema_mid_range: Tuple[int, int]
   ema_long_range: Tuple[int, int]
   ```

3. **`OptunaConfig`**: Optuna配置
   ```python
   n_trials: int = 300
   sampler_type: str = 'TPE'
   pruner_type: Optional[str] = 'Median'
   n_jobs: int = 6
   timeout: Optional[int] = None
   random_seed: Optional[int] = 42
   ```

4. **`OptimizationResult`**: 優化結果
   ```python
   task_id: str
   best_value: float
   best_params: Dict[str, Any]
   best_trial_number: int
   total_trials: int
   optimization_time: float
   convergence_history: List[float]
   trials_summary: List[TrialSummary]
   ```

5. **`TrialSummary`**: 單次試驗摘要
   ```python
   trial_number: int
   params: Dict[str, Any]
   value: float
   state: str  # COMPLETE/PRUNED/FAIL
   datetime: str
   ```

**驗收標準**:
- ✅ Pydantic模型定義完整
- ✅ 參數驗證邏輯正確
- ✅ 類型提示完整

---

### 3.3 API路由端點

**新增文件**: `api/routes/optimization.py`

**核心端點**:

1. **`POST /api/v1/optimization/start`**: 啟動優化
   - 請求體：OptimizationRequest
   - 響應：`{"task_id": "...", "status": "started"}`
   - 狀態碼：202 Accepted

2. **`GET /api/v1/optimization/status/{task_id}`**: 查詢狀態
   - 響應：OptimizationStatus
   - 狀態碼：200成功、404任務不存在

3. **`GET /api/v1/optimization/result/{task_id}`**: 獲取結果
   - 響應：OptimizationResult
   - 狀態碼：200成功、404任務不存在、400未完成

4. **`POST /api/v1/optimization/cancel/{task_id}`**: 取消優化
   - 響應：`{"status": "cancelled"}`
   - 狀態碼：200成功

5. **`GET /api/v1/optimization/trials/{task_id}`**: 獲取試驗歷史
   - 響應：List[TrialSummary]
   - 支援分頁：`?offset=0&limit=100`

**路由註冊**:
- 修改：`api/main.py`
- 添加：`app.include_router(optimization_router, prefix="/api/v1/optimization", tags=["optimization"])`

**驗收標準**:
- ✅ 所有端點正常運作
- ✅ 異步任務正確創建
- ✅ API文檔自動生成

---

## STEP 4: 前端TypeScript類型與API整合

**目標**: 同步後端數據模型到前端，建立API調用函數

### 4.1 TypeScript類型定義

**修改文件**: `frontend/src/lib/types.ts`

**新增接口**:

```typescript
// 優化請求
interface OptimizationRequest {
  strategy_config: StrategySearchSpace;
  training_window: TrainingWindowConfig;
  positive_cases: string[];
  negative_cases: string[];
  optuna_config: OptunaConfig;
}

// 策略搜索空間
interface StrategySearchSpace {
  data_sources: string[];
  indicator_types: string[];
  strategy_logics: string[];
  ema_short_range: [number, number];
  ema_mid_range: [number, number];
  ema_long_range: [number, number];
}

// Optuna配置
interface OptunaConfig {
  n_trials: number;
  sampler_type: 'TPE' | 'CmaEs' | 'Random';
  pruner_type?: 'Median' | 'Percentile' | null;
  n_jobs: number;
  timeout?: number;
  random_seed?: number;
}

// 優化狀態
interface OptimizationStatus {
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  progress: {
    current_trial: number;
    total_trials: number;
    percentage: number;
  };
  current_best?: {
    value: number;
    params: Record<string, any>;
  };
  elapsed_time: number;
  eta?: number;
}

// 優化結果
interface OptimizationResult {
  task_id: string;
  best_value: number;
  best_params: Record<string, any>;
  best_trial_number: number;
  total_trials: number;
  optimization_time: number;
  convergence_history: number[];
  trials_summary: TrialSummary[];
}

// 試驗摘要
interface TrialSummary {
  trial_number: number;
  params: Record<string, any>;
  value: number;
  state: 'COMPLETE' | 'PRUNED' | 'FAIL';
  datetime: string;
}
```

**驗收標準**:
- ✅ 類型定義與後端一致
- ✅ 類型安全

---

### 4.2 API調用函數

**修改文件**: `frontend/src/lib/api.ts`

**新增函數**:

```typescript
// 啟動優化
export async function startOptimization(
  request: OptimizationRequest
): Promise<{ task_id: string; status: string }>;

// 查詢優化狀態
export async function getOptimizationStatus(
  taskId: string
): Promise<OptimizationStatus>;

// 獲取優化結果
export async function getOptimizationResult(
  taskId: string
): Promise<OptimizationResult>;

// 取消優化
export async function cancelOptimization(
  taskId: string
): Promise<{ status: string }>;

// 獲取試驗歷史（分頁）
export async function getOptimizationTrials(
  taskId: string,
  offset?: number,
  limit?: number
): Promise<TrialSummary[]>;
```

**輪詢狀態模式**:
```typescript
// 每3秒輪詢一次狀態
const pollStatus = async (taskId: string) => {
  const interval = setInterval(async () => {
    const status = await getOptimizationStatus(taskId);
    if (status.status === 'completed' || status.status === 'failed') {
      clearInterval(interval);
      // 處理完成
    }
    // 更新UI
  }, 3000);
};
```

**驗收標準**:
- ✅ fetch調用正確
- ✅ 錯誤處理完整
- ✅ 輪詢機制正常

---

## STEP 5: 前端優化進度與結果UI（含高級視覺化）

**目標**: 提供優化進度實時顯示、結果分析UI和高級參數空間視覺化

### 5.1 優化進度頁面

**新增文件**: `frontend/src/app/optimization-progress/[taskId]/page.tsx`

**UI元件**:

1. **進度總覽卡片**:
   - 試驗進度：156/300 (52%)
   - 進度條（彩色動畫）
   - 預計剩餘時間：1h 23m
   - 已用時間：1h 15m
   - 試驗速度：23.5 trials/hour

2. **當前最佳值卡片**:
   - 最佳密度差異：0.4723
   - 試驗編號：#89
   - 最佳參數：
     - 數據源：Close
     - 策略：EMA三線排列
     - 參數：7, 18, 35

3. **實時收斂曲線**:
   - X軸：試驗編號
   - Y軸：目標值（Separation）
   - 折線圖：當前最佳值演進
   - 散點圖：所有試驗結果
   - 使用Recharts或Chart.js

4. **最近試驗列表**（滾動顯示最新10個）:
   - 試驗編號
   - 參數組合
   - 目標值
   - 狀態（完成/剪枝/失敗）

**操作按鈕**:
- 暫停優化（未來擴展）
- 取消優化
- 查看詳細結果（跳轉到結果頁面）

**實時更新機制**:
- **WebSocket訂閱** ⭐ 標準實作:
  - 連接到`ws://localhost:8000/ws/optimization/{task_id}`
  - 接收即時試驗完成事件
  - 自動更新進度、最佳值、收斂曲線
  - 斷線自動重連
- **輪詢備援**（WebSocket失敗時）:
  - 每3秒調用`getOptimizationStatus()`
  - 確保在網絡不穩定時仍可用

**驗收標準**:
- ✅ WebSocket即時推送生效（延遲<1秒）
- ✅ 進度條即時更新
- ✅ 收斂曲線流暢渲染（60fps）
- ✅ 最佳值變更即時顯示
- ✅ 斷線自動重連
- ✅ 取消按鈕正常運作

---

### 5.2 優化結果頁面（整合到任務3.6 + 高級視覺化）

**整合點**: `frontend/src/app/strategy-results/page.tsx`

**新增功能**:
- 從Optuna優化跳轉到此頁面
- 顯示最佳試驗的完整結果
- 顯示所有試驗歷史表格
- 參數重要性分析（Optuna內建）
- 多試驗對比工具

**參數重要性圖**:
- 使用Optuna的`optuna.importance.get_param_importances()`
- 條狀圖顯示各參數影響力
- 範例：
  - ema_short: 0.45
  - ema_long: 0.30
  - data_source: 0.15
  - strategy_logic: 0.10

---

### 5.3 高級參數空間視覺化 ⭐ 新增（標準功能）

**新增文件**: `frontend/src/components/optimization/ParamSpaceVisualizer.tsx`

**功能A: 2D參數空間熱力圖**:
- 選擇兩個參數作為X/Y軸（如ema_short vs ema_long）
- 顏色表示目標值（separation）
- 互動式：懸停顯示具體參數和目標值
- 使用Plotly.js或Recharts
- 用途：發現參數間的交互作用

**實作細節**:
```typescript
// 生成熱力圖數據
const heatmapData = trials.map(trial => ({
  x: trial.params.ema_short,
  y: trial.params.ema_long,
  value: trial.value,
  color: getColorByValue(trial.value)
}));
```

**功能B: 3D參數空間視覺化**:
- 三個參數維度（如ema_short, ema_mid, ema_long）
- Z軸表示目標值（separation）
- 可旋轉、縮放、平移
- 使用Plotly.js 3D scatter plot
- 高亮最佳試驗點

**實作細節**:
```typescript
// Plotly 3D scatter配置
const trace = {
  x: trials.map(t => t.params.ema_short),
  y: trials.map(t => t.params.ema_mid),
  z: trials.map(t => t.params.ema_long),
  marker: {
    color: trials.map(t => t.value),
    colorscale: 'Viridis',
    size: 5
  },
  mode: 'markers',
  type: 'scatter3d'
};
```

**功能C: 參數切片視圖（Slice Plot）**:
- 固定其他參數，只看一個參數的影響
- 範例：固定ema_mid=20, ema_long=50，掃描ema_short的影響
- 折線圖顯示趨勢
- 用途：單參數敏感性分析

**功能D: Pareto前沿視覺化（多目標優化）**:
- 2D散點圖：separation vs stability
- 高亮Pareto前沿上的解
- 點擊任一解查看詳細參數
- 顯示推薦的平衡點

**UI控件**:
- 參數選擇器（選擇X/Y/Z軸參數）
- 視圖切換（2D熱力圖 / 3D散點 / 切片視圖 / Pareto前沿）
- 顏色方案選擇（Viridis / Plasma / Turbo）
- 匯出圖表（PNG/SVG）

**涉及模組**:
- 新增: frontend/src/components/optimization/HeatmapView.tsx
- 新增: frontend/src/components/optimization/3DScatterView.tsx
- 新增: frontend/src/components/optimization/SlicePlotView.tsx
- 新增: frontend/src/components/optimization/ParetoFrontView.tsx
- 新增: frontend/src/lib/visualizationUtils.ts
- 依賴: plotly.js, react-plotly.js

**驗收標準**:
- ✅ 2D熱力圖正確渲染
- ✅ 3D散點圖可旋轉縮放
- ✅ 切片視圖趨勢清晰
- ✅ Pareto前沿正確標識
- ✅ 互動流暢（60fps）
- ✅ 圖表可匯出

---

**整體驗收標準（5.2 + 5.3）**:
- ✅ 優化結果正確顯示
- ✅ 參數重要性分析準確
- ✅ 試驗歷史表格完整
- ✅ 參數空間視覺化清晰
- ✅ 3D視覺化互動流暢

---

## STEP 6: 性能優化與測試

**目標**: 確保大規模優化（1000次試驗）穩定高效

### 6.1 性能優化

**優化項目**:

1. **並行策略優化**:
   - M1 8核心：建議n_jobs=6（保留2核心給系統）
   - 每個進程獨立運行目標函數
   - 共享SQLite數據庫（Optuna自動同步）

2. **目標函數加速**:
   - 預計算指標（可選）：
     - 優化前預先計算所有案例的EMA（常用週期）
     - 存儲為HDF5或pickle
     - 目標函數直接讀取，避免重複計算
   - 向量化計算：
     - 批量處理案例（已在任務3.2實作）
     - 使用numpy/pandas向量化操作

3. **記憶體管理**:
   - 定期垃圾回收（每100次試驗）
   - 避免大物件累積（如完整K線數據）
   - 監控記憶體使用（psutil）

4. **數據庫優化**:
   - SQLite WAL模式（Write-Ahead Logging）
   - 減少同步頻率（Optuna預設已優化）

**性能目標**:
- 單次試驗時間：< 5秒（100案例）
- 並行加速比：> 4x（6核心）
- 1000次試驗總時間：< 2小時（並行）
- 記憶體使用：< 4GB

**驗收標準**:
- ✅ 單次試驗 < 5秒
- ✅ 並行加速比 > 4x
- ✅ 記憶體穩定（無洩漏）

---

### 6.2 單元測試

**新增文件**: `tests/test_optuna_optimizer.py`

**測試案例**:

1. **測試1：Study創建與載入**:
   - 創建新Study
   - 關閉並重新載入
   - 驗證Study名稱和方向正確

2. **測試2：目標函數計算**:
   - Mock信號密度分析服務
   - 調用objective_function
   - 驗證參數採樣和目標值計算正確

3. **測試3：參數約束**:
   - 三線排列：ema_short < ema_mid < ema_long
   - 不合法參數應觸發TrialPruned
   - 驗證約束生效

4. **測試4：小規模優化（10次試驗）**:
   - 執行完整優化流程
   - 驗證最佳試驗可獲取
   - 驗證試驗歷史完整

5. **測試5：斷點續跑**:
   - 優化5次試驗後中斷
   - 重新載入Study續跑5次
   - 驗證總共10次試驗，無重複

6. **測試6：錯誤處理**:
   - Mock目標函數拋出異常
   - 驗證錯誤分類正確
   - 驗證重試機制生效

**驗收標準**:
- ✅ 所有測試通過
- ✅ 邊界情況處理正確
- ✅ 覆蓋率 > 80%

---

### 6.3 整合測試

**測試場景**:

1. **端到端優化測試**:
   - 使用真實案例數據（10個正例 + 10個反例）
   - 啟動Optuna優化（30次試驗）
   - 驗證：
     - 優化正常完成
     - 最佳值合理（separation > 0）
     - 試驗歷史完整
   - 時間：< 5分鐘

2. **並行優化測試**:
   - n_jobs=4，100次試驗
   - 驗證：
     - 加速比 > 3x
     - 無進程崩潰
     - SQLite數據一致

3. **長時間穩定性測試**:
   - 500次試驗，預計時間1小時
   - 驗證：
     - 無記憶體洩漏
     - 無崩潰
     - 檢查點正確保存

4. **斷點續跑測試**:
   - 優化100次後手動中斷
   - 重啟後續跑100次
   - 驗證：
     - 總共200次試驗
     - 無重複計算
     - 最佳值正確

**驗收標準**:
- ✅ 所有場景通過
- ✅ 無崩潰或異常
- ✅ 性能達標

---

## 整體驗收標準

### 功能完整性
- ✅ Optuna優化正常運作（TPE/CmaEs/Random Sampler）
- ✅ 目標函數計算正確（separation = positive_density - negative_density）
- ✅ 參數約束生效（short < mid < long）
- ✅ 並行優化穩定（6核心並行）
- ✅ 斷點續跑機制（SQLite + 檢查點）
- ✅ 錯誤處理與重試（3次重試，錯誤分類）
- ✅ 進度監控與通知（實時進度、新最佳值通知）

### 性能要求
- ✅ 單次試驗 < 5秒（100案例）
- ✅ 並行加速比 > 4x（6核心）
- ✅ 1000次試驗 < 2小時
- ✅ 記憶體使用 < 4GB（穩定）

### 容錯與穩健性
- ✅ 斷點續跑（電腦當機後可恢復）
- ✅ 錯誤重試（暫時性錯誤自動重試3次）
- ✅ 進度監控（每100次試驗通知）
- ✅ 數據完整性（啟動前和運行中檢查）
- ✅ 長時間穩定（8小時+無崩潰）

### 用戶體驗
- ✅ API異步（立即返回task_id）
- ✅ 進度實時顯示（輪詢或WebSocket）
- ✅ 結果清晰展示（最佳參數、收斂曲線、試驗歷史）
- ✅ 取消操作正常（可中斷優化）

### 代碼質量
- ✅ 遵循Ultra Think三步驟
- ✅ 向量化計算（numpy/pandas）
- ✅ 錯誤處理完整（分類、重試、日誌）
- ✅ 類型安全（Python + TypeScript）
- ✅ 單元測試覆蓋率 > 80%

---

## 依賴關係

### 前置需求
- **任務3.1：指標計算引擎**（必須完成）
  - 需要：EMA計算函數
  - 整合點：目標函數調用指標引擎

- **任務3.2：信號密度分析系統**（必須完成）
  - 需要：analyze_signal_density()
  - 整合點：目標函數核心邏輯

- **任務3.3：策略選擇UI**（必須完成）
  - 需要：策略配置數據模型
  - 整合點：優化請求參數

### 並行開發
- **任務3.4：圖表信號箭頭**（可同時開發）
  - 優化結果可用於驗證信號箭頭

### 後續任務
- **任務3.6：結果展示UI**（依賴本任務）
  - 整合Optuna優化結果展示
  - 參數重要性分析

---

## 風險與注意事項

### 性能風險
- **風險**：大規模優化（1000次試驗）時間過長
- **緩解**：
  - 並行優化（6核心）
  - 預計算指標（可選）
  - 剪枝機制（提前終止差勁試驗）

### 穩定性風險
- **風險**：長時間運行（8小時+）崩潰
- **緩解**：
  - SQLite自動持久化
  - 檢查點每50次保存
  - 錯誤重試機制
  - 進程監控與自動重啟（可選）

### 並行競爭風險
- **風險**：多進程同時寫入SQLite衝突
- **緩解**：
  - Optuna原生支援並行（WAL模式）
  - 測試驗證並行穩定性

### 參數空間爆炸風險
- **風險**：搜索空間過大（7數據源 × 3策略 × 200³週期）
- **緩解**：
  - 使用TPE智能採樣（非網格搜索）
  - 參數約束（short < mid < long）
  - 剪枝機制

---

## 開發順序建議（更新版，7-8天）

**第1天**：STEP 1.1-1.3（Optuna核心引擎）
- 上午：OptunaOptimizer類 + objective_function
- 下午：Sampler/Pruner配置（TPE/CmaEs/Random/GP/NSGA-II）+ Study創建/載入

**第2天**：STEP 1.4（多目標優化）
- 上午：多目標函數實作 + NSGA-II整合
- 下午：Pareto前沿分析 + 測試驗證

**第3天**：STEP 2.1-2.2（容錯機制1）
- 上午：CheckpointManager（斷點續跑）
- 下午：ErrorHandler（錯誤分類與重試）

**第4天**：STEP 2.3-2.4（容錯機制2 + WebSocket）
- 上午：ProgressMonitor（進度監控） + WebSocket推送實作
- 下午：DataValidator（數據完整性檢查）

**第5天**：STEP 3（FastAPI服務層 + WebSocket endpoint）
- 上午：OptimizationService（異步任務）+ WebSocket handler
- 下午：數據模型 + API路由端點

**第6天**：STEP 4-5.1（前端基礎整合）
- 上午：TypeScript類型 + API函數 + WebSocket client
- 下午：優化進度頁面（WebSocket訂閱）

**第7天**：STEP 5.2-5.3（前端高級視覺化）
- 上午：參數重要性分析 + 2D熱力圖 + 3D散點圖
- 下午：切片視圖 + Pareto前沿視覺化

**第8天**：STEP 6（測試與優化）
- 上午：單元測試 + 整合測試（含多目標優化測試）
- 下午：性能優化 + 視覺化渲染優化 + 驗收測試

---

## 成功標準

任務3.5完成的標誌：
- ✅ 後端Optuna優化引擎可正常運作
- ✅ 目標函數正確計算密度差異
- ✅ 支援TPE/CmaEs/Random三種Sampler
- ✅ 並行優化穩定（6核心）
- ✅ 斷點續跑機制生效（SQLite + 檢查點）
- ✅ 容錯機制完整（錯誤重試、進度監控、數據檢查）
- ✅ 前端API可啟動優化、查詢狀態、獲取結果
- ✅ 優化進度頁面實時顯示進度和收斂曲線
- ✅ 性能達標（1000次試驗 < 2小時，並行）
- ✅ 長時間穩定（8小時+無崩潰）
- ✅ 單元測試全部通過（> 80%覆蓋率）
- ✅ 文檔更新（STATUS.md標記任務3.5完成）

---

## 參考文檔

- **Optuna官方文檔**：https://optuna.readthedocs.io/
  - Multi-objective Optimization: https://optuna.readthedocs.io/en/stable/tutorial/20_recipes/009_multi_objective.html
  - GP Sampler: https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.GPSampler.html
  - Visualization: https://optuna.readthedocs.io/en/stable/reference/visualization/index.html
- **信號密度分析**：任務3.2計劃 - 目標函數整合點
- **策略配置**：任務3.3計劃 - 優化請求參數
- **開發規範**：`.claude/GUIDELINES.md` - Ultra Think三步驟
- **技術架構**：`docs/ARCHITECTURE.md` - 系統架構設計
- **性能優化**：M1 8核心並行策略
- **Plotly.js 3D可視化**：https://plotly.com/javascript/3d-scatter-plots/
- **WebSocket (FastAPI)**：https://fastapi.tiangolo.com/advanced/websockets/

---

## 標準功能總結 ✅

**本任務3.5已將以下功能從「可選」提升為「標準實作」**:

### 進階優化策略（已整合）
- ✅ 多目標優化（NSGA-II，同時最大化separation和穩定性）
- ✅ 貝葉斯優化（Gaussian Process Sampler）
- ✅ 遺傳算法（NSGA-II多目標優化）

### 視覺化增強（已整合）
- ✅ 參數空間熱力圖（2D slice）
- ✅ 3D參數空間視覺化（Plotly.js）
- ✅ 實時WebSocket推送進度（替代輪詢）
- ✅ Pareto前沿視覺化（多目標優化結果）

### 容錯機制（已完整整合自Roadmap）
- ✅ 斷點續跑（SQLite + 檢查點）
- ✅ 錯誤處理與重試（3次重試，錯誤分類）
- ✅ 進度監控與通知（終端/WebSocket/Line/Email）
- ✅ 自動重啟機制（可選）
- ✅ 數據完整性檢查

---

## 未來擴展功能（Phase 4+）

### 智能建議
- 根據歷史優化結果推薦初始參數範圍
- 自動調整試驗次數（收斂檢測）
- 異常試驗自動分析
- Transfer Learning（遷移不同交易對的優化經驗）

### 分散式優化
- 多機器分散式優化（Optuna分散式後端，如Redis/PostgreSQL）
- Docker容器化部署
- Kubernetes水平擴展
- Ray Tune整合（大規模超參數搜索）

---

*文檔版本: 2.0*  
*創建日期: 2025-10-31*  
*最後更新: 2025-10-31*  
*更新內容: 整合進階優化策略（GP/NSGA-II）、高級視覺化（2D/3D/Pareto）、WebSocket實時推送、容錯機制（從Roadmap完整合併）*  
*維護者: AI Code Agent*

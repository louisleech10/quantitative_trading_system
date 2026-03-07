# 項目狀態

### 已完成 ✅
- ✅ **Phase 4：Optuna 重構 — 策略執行優化系統（Phase4_Optuna重構_PLAN.md V4）**
  - Phase 4.0：架構準備（Protocol IBacktestEngine/IPositionSizer + Factory + optimization_config.yaml + 封存 SignalDensityObjective）✓
  - Phase 4.1：Strategy Domain 核心（VectorizedBacktest + PerformanceMetrics 12+ 指標 + PositionSizer 3 種 + RiskManager + 110 tests）✓
  - Phase 4.2：Objective 增強（StrategyBacktestObjective 重構 + 搜索空間 + 過擬合檢測 + 35 tests）✓
  - Phase 4.3：API + Service 層（Pydantic Models + 4 端點 + OptimizationTaskService 增強 + 3 WebSocket 事件）✓
  - Phase 4.4：前端 UI（TypeScript 型別 + hyperparameter/execution 兩頁面 + 共用元件 + Store）✓
  - Phase 4.5：輸出格式（JSON/CSV/AI-Readable MD/HTML + Export API 5 種格式）✓
  - Phase 4.6：測試 100%（20 整合測試 + Decoupling 腳本驗證 + Benchmark + 覆蓋率 100%）✓
  - 驗證：integration 20 passed、decoupling PASSED、coverage 100.00%
- ✅ **Phase 3.5：LightGBM/XGBoost 模型訓練增強系統（LightGBM_XGBoost_優化PLAN.md V8）**
  - M1-M6 核心模組全部完成、API 層（8 端點）、前端 C23-C27、129 tests passed ✓
- ✅ **IC Gatekeeper 深度分析系統（Phase 2.10-2.12）**、**Feature Factory 完整系統（Phase 3.0-3.4）** ✓
- ✅ **架構解耦規則持續符合**
  - Rule 1: `momentum/` 無 `from api.` 反向依賴 ✓
  - Rule 2: `IBacktestEngine` / `IPositionSizer` Protocol 注入 ✓
  - Rule 3: 所有服務透過 Factory 建立（`create_backtest_engine` / `create_position_sizer`）✓

- ✅ **Feature Engineering Pipeline 效能最佳化（Phase B/C/D）**
  - Phase B：Layer2/3 向量化（`derived_operators.py` worldquant/ts_rank/decay_linear + `rolling_aggregator.py` 視窗快取）✓
  - Phase C：Layer4 分塊惰性處理、HDF5 分塊寫入（`feature_storage.py`）、float32 批次轉換（`feature_preprocessor.py`）✓
  - Phase D：Runtime Governance（`FFACT_NEW_COMPUTE_PATH` 旗標 + Shadow Compare + 自動 Rollback）✓
  - 驗證：`l23_phased_fix_compare_1run.json` all_passed=true，delta_ratio=-0.9064（**90.6% 加速**，基線 2224.7s → 208.1s）
  - 單元測試：`tests/api/test_feature_factory_service_phase_d.py` 6 tests passed ✓

### 進行中 🚧
- 📝 **Phase 4.7：文件更新**（`ARCHITECTURE.md` 與 `API_SPECIFICATION.md` 補齊 Strategy Domain / Protocol / 端點說明）

## 🎯 當前重點
- Phase 4.0~4.6 全部驗收完成；Phase 4.7 文件更新為唯一剩餘工作
- **Feature Engineering Pipeline 效能最佳化全部完成（Phase B/C/D）**：all_passed=true，90.6% 加速
- 核心驗證：integration 20 tests passed、coverage 100%、decoupling PASSED

### 下一步工作
- 完成 Phase 4.7.1：`docs/ARCHITECTURE.md` 補齊 Strategy Domain、Protocol、Factory 說明
- 完成 Phase 4.7.2：`docs/API_SPECIFICATION.md` 補齊 4 個新端點與 3 個 WebSocket 事件
- （可選）研究 Layer1 並行（`FFACT_LAYER1_PARALLEL=1`）欄位排序確定性問題，修復後可再增 ~0.6% 加速

## 🐛 已知問題
### 需要修復
- 無阻塞性問題

### 需要優化
- 4 個 FutureWarning：`ema_extractor.py` / `feature_validator.py` pandas `fillna(method=...)` 已棄用（非阻塞）
- Optuna trial log 中 NON_RETRYABLE 訊息（entry_threshold == exit_threshold 剪枝路徑，係預期行為）
- Layer1 並行模式（`FFACT_LAYER1_PARALLEL=1`）：ThreadPoolExecutor 完成順序不穩定 → concat 欄位不一致 → 品質閘失敗（39 欄位 checksum 漂移，均為 `volume_momentum_MACD-Signal_*`）；目前預設關閉，待後續修復

### 技術債務
- pandas `fillna(method=...)` 語法需遷移至 `ffill()`/`bfill()`（現僅 FutureWarning）
- `optimization_results/` 下的測試產物（test artifacts）應加入 `.gitignore` 或在 CI 中清理

## 📝 最近完成的工作
- 2026-03-07：完成 Feature Engineering Pipeline Phase D Governance（`api/services/feature_factory_service.py`：FFACT_NEW_COMPUTE_PATH 旗標、Shadow Compare、Rollback、_temporary_environ）
- 2026-03-07：修復 Layer1 並行 checksum 漂移（`feature_factory.py` `FFACT_LAYER1_PARALLEL` 預設改為 `"0"`；old-path override 同步強制關閉）
- 2026-03-07：新增 `tests/api/test_feature_factory_service_phase_d.py`（6 tests，全部通過）
- 2026-03-07：完成 Phase C（Layer4 分塊 + HDF5 分塊 + float32 批次轉換）；strict compare all_passed=true，210s/基線 2224s
- 2026-03-07：完成 Phase B（Layer2 `derived_operators.py` 向量化 + Layer3 `rolling_aggregator.py` 視窗快取）
- 2026-02-18：完成 Phase 4.6 全驗收（20 integration tests、decoupling PASSED、coverage 100%）
- 2026-02-18：修補 multi-objective trial 序列化（`optimization_output_service.py` fallback）

## 🔄 Git狀態
- 分支：`main`
- 上次 push：Phase B/C/D Feature Engineering 效能最佳化全部完成（2026-03-07）
- 最新變更：`momentum/FeatureEngineering/` 多層向量化、`api/services/feature_factory_service.py` Phase D Governance、`tests/api/test_feature_factory_service_phase_d.py`
- 驗證結果：all_passed=true，delta_ratio=-0.9064（90.6% 加速）

## 💡 下次啟動時
- 先跑：`pytest tests/integration/ -q`（確認 20 tests 穩定）
- 先跑：`./venv/bin/pytest -q tests/api/test_feature_factory_service_phase_d.py`（Phase D Governance 6 tests）
- 確認：`./scripts/check_decoupling_phase4.sh`（Rule1/2/3/6 PASSED）
- 確認：`grep -rn "from api." momentum/ | wc -l` → 應為 0
- 推進：Phase 4.7 文件更新（ARCHITECTURE.md + API_SPECIFICATION.md）
- 可選：研究 `FFACT_LAYER1_PARALLEL=1` 欄位排序問題（engines 結果 concat 前需按引擎名稱穩定排序）

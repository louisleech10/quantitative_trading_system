# Phase 4 Optuna 重構 — Implementation PLAN

> **版本**: V4 (Frozen)  
> **建立日期**: 2026-02-09  
> **定案日期**: 2026-02-09  
> **設計文件**: `docs/Optuna重構_SPEC.md` V3.0-Frozen  
> **範本**: `docs/Feature_Factory_PLAN.md` V7 (Frozen)  
> **目的**: AI Agent 可依序執行的實作清單；人類可審閱檢查  
> **範圍**: Phase 4 策略執行優化全部功能，含 Strategy Domain、Objective 增強、API、前端 UI、輸出格式、100% 測試  
> **狀態**: 🔒 Frozen — 經 V1→V3 三輪自審定案  
> **Changelog**: V3 → V4：補齊缺少的階段級驗證檢查點，明確成功/失敗（邊界）可測條件  
> **V1 變更**: 初版 — 完整 Task 展開，對齊 SPEC V3.0 所有 Section  
> **V2 變更**: 補齊 Breaking Change 遷移步驟、補齊前端 TypeScript 型別定義、補齊每 Task 驗證命令、補齊 WebSocket 新事件實作位置  
> **V3 變更**: 最終校對 — 確認測試數量 (~165) 與 Task 一致、確認 Decoupling 腳本完整、確認邊界條件全覆蓋
> **V4 變更**: PLAN 審查修補 — 補齊 Phase 4.2~4.7 驗證檢查點以確保責任範圍可驗證

---

## 架構原則與解耦要求

> **Authority**: 本 Task 必須遵循系統全局解耦架構，參見：
> - [docs/ARCHITECTURE.md](./ARCHITECTURE.md) — 解耦架構原則
> - [docs/PRODUCT_VISION.md](./PRODUCT_VISION.md) — 版本演進策略
> - [docs/全系統解耦Prompt.md](./全系統解耦Prompt.md) — 7 Rules V4.2

### 解耦規則遵循清單

**Phase 4 必須符合以下 7 條規則**：

| 規則 | 要求 | Phase 4 實作方式 |
|------|------|----------------|
| **Rule 1** | `momentum/` 不依賴 `api/` | ✅ `momentum/Strategy/` 不 import `api.*` |
| **Rule 2** | 跨 Domain 使用 Protocol | ✅ `StrategyBacktestObjective` 透過 `IBacktestEngine`、`IPositionSizer` Protocol 調用 |
| **Rule 3** | Service 用 Factory | ✅ `api/services/optimization_task_service.py` 用 `create_backtest_engine()` / `create_position_sizer()` |
| **Rule 4** | Service 間不互調 | ✅ 優化相關 Service 獨立 |
| **Rule 5** | Config 單一來源 | ✅ 搜索空間從 `config/optimization_config.yaml` 讀取 |
| **Rule 6** | Test 配置隔離 | ✅ `pytest tests/momentum/Strategy/` 可獨立執行，不需 `run_api.py` |
| **Rule 7** | DTO 不跨層 | ✅ `Trade`, `BacktestResult` 為 momentum 內部 dataclass |

### V2.0/V3.0 演進準備

| 版本 | 使用方式 | 可行性 |
|------|---------|--------|
| **V1.0** | REST API: `POST /api/v1/optimization/execution` | ✅ 本 Phase 實作 |
| **V2.0** | Chat: "用 Kelly 半凱利最大化 Expectancy" | ✅ 可直接調用 Factory |
| **V3.0** | Agent: 自主決定優化目標並啟動 | ✅ `ai_readable_report.md` 提供決策輸入 |

---

## 全域常量與約定

| 項目 | 值 |
|------|-----|
| 專案根目錄 | `/Users/louis/Desktop/quantitative_trading_system/` |
| 後端核心路徑 (新 Domain) | `momentum/Strategy/` |
| Objective 路徑 | `momentum/Optimization/objectives/` |
| Protocol 路徑 | `momentum/core/protocols.py` |
| Factory 路徑 | `momentum/factories.py` |
| API 路由路徑 | `api/routes/` |
| API Service 路徑 | `api/services/optimization_task_service.py` |
| 前端路徑 | `frontend/src/` |
| Config 路徑 | `config/optimization_config.yaml` |
| 測試路徑 | `tests/momentum/Strategy/`, `tests/momentum/Optimization/`, `tests/integration/` |
| 日誌標準 | `from momentum.core.logging import get_logger; logger = get_logger(__name__)` |
| 輸入數據契約 | `model_predictions_{task_id}.csv` (timestamp, OHLC, predicted_proba_lgb, atr) |
| 輸出目錄 | `optimization_results/{execution\|hyperparameter}/{task_id}/` |
| periods_per_year | 730 (12h K 線: 365 × 2) |
| 封存目錄 | `archived/momentum/Optimization/objectives/` |
| 現有優化引擎 | `OptunaOptimizer` — **不修改**，利用可插拔目標架構 |

---

## 禁止事項（Forbidden Actions）

- ❌ 修改 `OptunaOptimizer` 核心邏輯（已穩定，透過 Objective 插拔擴展）
- ❌ 修改 Frozen Files（`api/main.py`, `run_api.py`, `pytest.ini`, `conftest.py`, `requirements.txt`, `data_cache/*.h5`）
- ❌ 生成假數據（Data Truth Principle）
- ❌ 在 `momentum/Strategy/` 中 import `api.*`
- ❌ 在 `momentum/Optimization/` 中 import `api.*`
- ❌ 在熱迴圈中加入逐行日誌
- ❌ 使用 Python for loop 替代可向量化的 pandas/numpy 操作

---

## Phase 依賴關係

```
Phase 4.0 (架構準備 + 封存)
    ↓
Phase 4.1 (Strategy Domain 核心)
    ↓
Phase 4.2 (Objective 增強)
    ↓
Phase 4.3 (API + Service 層) ──→ Phase 4.4 (前端 UI)
    ↓
Phase 4.5 (輸出格式)
    ↓
Phase 4.6 (測試 100%)
    ↓
Phase 4.7 (文件更新)
```

**關鍵約束**：
- Phase 4.1 依賴 4.0（Protocol + Factory 必須先定義）
- Phase 4.2 依賴 4.1（Objective 需 import Strategy Domain 類別）
- Phase 4.3 依賴 4.2（API 需建構增強後的 Objective）
- Phase 4.4 依賴 4.3（前端需 API 端點可用）
- Phase 4.5 可與 4.3/4.4 並行（輸出格式僅依賴 4.2 的 BacktestResult）
- Phase 4.6 依賴 4.1-4.5 全部完成

---

## Phase 4.0：架構準備 + 封存

### Task 4.0.1：擴展 Protocol 定義

**檔案**：
- `momentum/core/protocols.py` (修改 — 新增 2 個 Protocol)

**新增內容**：
```python
@runtime_checkable
class IBacktestEngine(Protocol):
    """回測引擎協議"""
    def run_backtest(
        self,
        prices: Any,                    # pd.DataFrame (OHLC)
        predicted_proba: Any,           # pd.Series (0.0~1.0)
        atr_values: Any,                # pd.Series (ATR 值)
        strategy_params: Dict[str, Any]
    ) -> Any:   # BacktestResult
        ...

@runtime_checkable
class IPositionSizer(Protocol):
    """倉位管理協議"""
    def calculate_position_size(
        self,
        predicted_proba: float,
        equity: float,
        risk_params: Dict[str, Any]
    ) -> float:
        ...
```

**驗收條件**：
- [x] `IBacktestEngine` 和 `IPositionSizer` 定義在 `momentum/core/protocols.py`
- [x] 使用 `@runtime_checkable` 裝飾
- [x] 參數型別使用 `Any` 對齊現有慣例（避免 Protocol 層引入 pandas 依賴）

**驗證命令**：
```bash
python -c "from momentum.core.protocols import IBacktestEngine, IPositionSizer; print('OK')"
```

**Checklist**：
- [x] `IBacktestEngine` Protocol 定義
- [x] `IPositionSizer` Protocol 定義
- [x] 不破壞現有 Protocol（IKlineReader, IIndicatorEngine, IModelTrainer, IOptimizationObjective, etc.）

---

### Task 4.0.2：擴展 Factory 函式

**檔案**：
- `momentum/factories.py` (修改 — 新增 2 個 factory function)

**新增內容**：
```python
def create_backtest_engine(
    commission: float = 0.001,
    slippage: float = 0.0005
) -> "IBacktestEngine":
    from momentum.Strategy.vectorized_backtest import VectorizedBacktest
    return VectorizedBacktest(commission=commission, slippage=slippage)

def create_position_sizer(
    method: str = "kelly",
    **kwargs
) -> "IPositionSizer":
    from momentum.Strategy.position_sizing import (
        KellyPositionSizer, FixedPositionSizer, ProbabilityScaledSizer
    )
    sizers = {
        "kelly": KellyPositionSizer,
        "fixed": FixedPositionSizer,
        "probability_scaled": ProbabilityScaledSizer,
    }
    if method not in sizers:
        raise ValueError(f"Unknown position sizing method: {method}. Options: {list(sizers.keys())}")
    return sizers[method](**kwargs)
```

**驗收條件**：
- [x] `create_backtest_engine()` 和 `create_position_sizer()` 可成功匯入
- [x] 無效 method 字串 raise ValueError

**驗證命令**：
```bash
python -c "from momentum.factories import create_backtest_engine, create_position_sizer; print('OK')"
```

> ⚠️ 注意：此 Task 的 import 在 Phase 4.1 完成後才能實際執行（延遲 import 模式）。建立時先確認語法正確即可。

**Checklist**：
- [x] `create_backtest_engine()` factory
- [x] `create_position_sizer()` factory
- [x] 不破壞現有 factory functions

---

### Task 4.0.3：建立 optimization_config.yaml

**檔案**：
- `config/optimization_config.yaml` (新建)

**內容**: 對齊 SPEC §8.1，包含：
- `execution` 區段：搜索空間 (9 參數)、約束條件、回測成本、優化設定（含 multi_objective）
- `hyperparameter` 區段：LightGBM (8 參數) + XGBoost (8 參數) 搜索空間、約束條件
- `archived` 區段：signal_density 標記 disabled

**驗收條件**：
- [x] YAML 語法正確
- [x] 包含 execution / hyperparameter / archived 三大區段
- [x] 每個參數含 type, low, high, step (或 log, choices)
- [x] `python -c "import yaml; yaml.safe_load(open('config/optimization_config.yaml'))"` 成功

**驗證命令**：
```bash
python -c "import yaml; c = yaml.safe_load(open('config/optimization_config.yaml')); print(f'Execution params: {len(c[\"execution\"][\"search_space\"])}'); print(f'LightGBM params: {len(c[\"hyperparameter\"][\"lightgbm\"])}')"
```

**Checklist**：
- [x] execution.search_space 9 參數
- [x] execution.constraints (max_drawdown, min_win_rate, min_trades)
- [x] execution.backtest (commission, slippage)
- [x] execution.optimization (target_metric, n_trials, timeout, sampler, multi_objective)
- [x] hyperparameter.lightgbm 8 參數
- [x] hyperparameter.xgboost 8 參數
- [x] hyperparameter.constraints (max_train_val_gap)
- [x] archived.signal_density.enabled=false

---

### Task 4.0.4：封存 SignalDensityObjective

**檔案**：
- `scripts/archive_signal_density.sh` (新建)
- 執行後：`momentum/Optimization/objectives/signal_density.py` → `archived/momentum/Optimization/objectives/signal_density.py`
- `momentum/Optimization/objectives/__init__.py` (修改 — 移除 signal_density import)

**封存腳本內容**: 對齊 SPEC §15.5

**驗收條件**：
- [x] `archived/momentum/Optimization/objectives/signal_density.py` 存在
- [x] `archived/momentum/Optimization/objectives/README.md` 存在
- [x] `momentum/Optimization/objectives/signal_density.py` 不存在
- [x] `momentum/Optimization/objectives/__init__.py` 不含 `signal_density`

**驗證命令**：
```bash
ls archived/momentum/Optimization/objectives/signal_density.py
grep -c "signal_density" momentum/Optimization/objectives/__init__.py
# 期望: 0
```

**Checklist**：
- [x] 封存腳本建立
- [x] 執行封存
- [x] README.md 含回復指示
- [x] `__init__.py` 清理

---

### Task 4.0.5：建立 Strategy Domain 骨架

**檔案**：
- `momentum/Strategy/__init__.py` (新建)
- `momentum/Strategy/vectorized_backtest.py` (新建 — 空骨架)
- `momentum/Strategy/performance_metrics.py` (新建 — 空骨架)
- `momentum/Strategy/position_sizing.py` (新建 — 空骨架)
- `momentum/Strategy/risk_manager.py` (新建 — 空骨架)

**`__init__.py` 內容**：
```python
from .vectorized_backtest import VectorizedBacktest, Trade, BacktestResult
from .performance_metrics import PerformanceMetrics
from .position_sizing import KellyPositionSizer, FixedPositionSizer, ProbabilityScaledSizer
from .risk_manager import RiskManager
```

**驗收條件**：
- [x] 目錄 `momentum/Strategy/` 存在且含 5 個 `.py` 檔案
- [x] `__init__.py` 匯出列表正確

**驗證命令**：
```bash
ls momentum/Strategy/*.py | wc -l
# 期望: 5
```

**Checklist**：
- [x] `__init__.py`
- [x] `vectorized_backtest.py` 骨架 (class + `raise NotImplementedError`)
- [x] `performance_metrics.py` 骨架
- [x] `position_sizing.py` 骨架 (3 classes)
- [x] `risk_manager.py` 骨架

---

### Task 4.0.6：擴展 MomentumConfig

**檔案**：
- `momentum/core/config.py` (修改 — 新增 `load_optimization_config()`)

**新增方法**：
```python
@staticmethod
def load_optimization_config() -> dict:
    config_path = Path(__file__).parent.parent.parent / "config" / "optimization_config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)
```

**驗收條件**：
- [x] `MomentumConfig.load_optimization_config()` 回傳 dict
- [x] 不 import `api.*`

**驗證命令**：
```bash
python -c "from momentum.core.config import MomentumConfig; c = MomentumConfig.load_optimization_config(); print(list(c.keys()))"
```

**Checklist**：
- [x] `load_optimization_config()` 實作
- [x] 無 `api.*` import

### Phase 4.0 驗證檢查點
```bash
# Protocol import
python -c "from momentum.core.protocols import IBacktestEngine, IPositionSizer; print('✅ Protocols OK')"
# Config load
python -c "from momentum.core.config import MomentumConfig; MomentumConfig.load_optimization_config(); print('✅ Config OK')"
# Strategy Domain exists
ls momentum/Strategy/__init__.py && echo "✅ Strategy Domain OK"
# Signal density archived
test ! -f momentum/Optimization/objectives/signal_density.py && echo "✅ Archived OK"
```

---

## Phase 4.1：Strategy Domain 核心

### Task 4.1.1：Trade + BacktestResult Dataclass

**檔案**：
- `momentum/Strategy/vectorized_backtest.py` (填入 dataclass 定義)

**類別定義** (對齊 SPEC §6.1.1)：
```python
@dataclass
class Trade:
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: pd.Timestamp
    exit_price: float
    position_size: float
    direction: str              # 'long'
    pnl: float
    pnl_pct: float
    exit_reason: str            # 'take_profit' | 'stop_loss' | 'signal_exit' | 'trailing_stop' | 'data_end'
    mae: float                  # Maximum Adverse Excursion
    mfe: float                  # Maximum Favorable Excursion

@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: List[Trade]
    metrics: Dict[str, float]
    config: Dict[str, Any]
```

**驗收條件**：
- [x] `Trade` 和 `BacktestResult` 可被 import 和實例化
- [x] 所有欄位有正確型別註解

**驗證命令**：
```bash
python -c "from momentum.Strategy.vectorized_backtest import Trade, BacktestResult; print('OK')"
```

**Checklist**：
- [x] `Trade` dataclass (11 欄位)
- [x] `BacktestResult` dataclass (4 欄位)
- [x] 型別註解完整

---

### Task 4.1.2：VectorizedBacktest — 輸入驗證 + 骨架

**檔案**：
- `momentum/Strategy/vectorized_backtest.py` (填入 VectorizedBacktest 類別骨架 + 驗證)

**函式簽名**：
```python
class VectorizedBacktest:
    def __init__(self, commission: float = 0.001, slippage: float = 0.0005):
        if commission + slippage > 0.10:
            logger.warning(f"High cost: commission={commission}, slippage={slippage}")
        self.commission = commission
        self.slippage = slippage

    def run_backtest(
        self,
        prices: pd.DataFrame,
        predicted_proba: pd.Series,
        atr_values: pd.Series,
        strategy_params: dict
    ) -> BacktestResult:
        self._validate_inputs(prices, predicted_proba, atr_values, strategy_params)
        # ... (各步驟在後續 Task 填入)

    def _validate_inputs(self, prices, predicted_proba, atr_values, strategy_params):
        if prices.empty:
            return BacktestResult(equity_curve=pd.Series([1.0]), trades=[], metrics={}, config=strategy_params)
        if len(prices) == 1:
            return BacktestResult(...)
        if len(prices) != len(predicted_proba):
            raise ValueError(f"prices length {len(prices)} != predicted_proba length {len(predicted_proba)}")
        if (prices[['open','high','low','close']] <= 0).any().any():
            raise ValueError("prices contain zero or negative values")
        entry_th = strategy_params.get('entry_threshold', 0.7)
        exit_th = strategy_params.get('exit_threshold', 0.4)
        if entry_th <= exit_th:
            raise ValueError(f"entry_threshold ({entry_th}) must > exit_threshold ({exit_th})")
```

**邊界條件覆蓋**: BC-VB-01, BC-VB-02, BC-VB-05, BC-VB-06, BC-VB-09, BC-VB-13, BC-VB-14

**驗收條件**：
- [x] 空 prices → 回傳空 BacktestResult
- [x] 長度不一致 → raise ValueError
- [x] 價格含 0 → raise ValueError
- [x] entry ≤ exit threshold → raise ValueError
- [x] 高手續費 → warning log

**驗證命令**：
```bash
python -c "
from momentum.Strategy.vectorized_backtest import VectorizedBacktest
import pandas as pd
vb = VectorizedBacktest()
# 空 prices
r = vb.run_backtest(pd.DataFrame(), pd.Series(), pd.Series(), {'entry_threshold': 0.7, 'exit_threshold': 0.4})
print(f'Empty: {len(r.trades)} trades')
"
```

**Checklist**：
- [x] `__init__` 含 commission/slippage 驗證 (BC-VB-09)
- [x] `_validate_inputs` 覆蓋 7 個邊界條件
- [x] `run_backtest` 方法骨架

---

### Task 4.1.3：信號生成 + 冷卻期（向量化）

**檔案**：
- `momentum/Strategy/vectorized_backtest.py` (填入信號生成方法)

**方法**：
```python
def _generate_entry_signals(self, proba: pd.Series, threshold: float) -> pd.Series:
    """完全向量化: (proba > threshold).astype(int)"""
    return (proba > threshold).astype(int)

def _generate_exit_signals(self, proba: pd.Series, threshold: float) -> pd.Series:
    """完全向量化: (proba < threshold).astype(int)"""
    return (proba < threshold).astype(int)

def _apply_cooldown(self, signals: pd.Series, cooldown_bars: int) -> pd.Series:
    """向量化冷卻期: 信號後 cooldown_bars 根 K 線內抑制新信號"""
    if cooldown_bars <= 0:
        return signals
    result = signals.copy()
    # 向量化: 利用 rolling 或 cumsum 技巧
    ...
    return result
```

**邊界條件覆蓋**: BC-VB-03, BC-VB-04, BC-VB-05, BC-VB-11

**驗收條件**：
- [x] proba 全為 0 → 無進場信號 (BC-VB-03)
- [x] proba 全為 1 → 冷卻期生效抑制連續進場 (BC-VB-04)
- [x] threshold > 1.0 → 永無信號 (BC-VB-05)
- [x] cooldown_bars > 數據長度 → 僅第一筆交易 (BC-VB-11)

**驗證命令**：
```bash
pytest tests/momentum/Strategy/test_vectorized_backtest.py -k "signal" -v --tb=short
```

**Checklist**：
- [x] `_generate_entry_signals` 向量化
- [x] `_generate_exit_signals` 向量化
- [x] `_apply_cooldown` 向量化
- [x] 4 個邊界條件覆蓋

---

### Task 4.1.4：交易執行 + SL/TP/Trailing Stop

**檔案**：
- `momentum/Strategy/vectorized_backtest.py` (填入交易執行邏輯)

**方法**：
```python
def _calculate_position_sizes(self, proba: pd.Series, signals: pd.Series,
                               strategy_params: dict) -> pd.Series:
    """根據 position_sizing_method 計算倉位"""
    method = strategy_params.get('position_sizing_method', 'fixed')
    position_sizer = create_position_sizer(method, **self._extract_sizer_kwargs(strategy_params))
    # 向量化處理
    ...

def _execute_trades(self, prices: pd.DataFrame, atr: pd.Series,
                     entry_signals: pd.Series, exit_signals: pd.Series,
                     position_sizes: pd.Series, strategy_params: dict) -> List[Trade]:
    """逐 bar 迴圈 (SL/TP/Trailing 有狀態)"""
    ...

def _calculate_equity_curve(self, trades: List[Trade], prices: pd.DataFrame) -> pd.Series:
    """從交易列表計算權益曲線 (向量化)"""
    ...
```

**邊界條件覆蓋**: BC-VB-07, BC-VB-08, BC-VB-10, BC-VB-12

**驗收條件**：
- [x] ATR 含 NaN → SL/TP fallback 或 skip (BC-VB-07)
- [x] ATR 全為 0 → 僅信號出場 (BC-VB-08)
- [x] 持倉跨越數據結尾 → 強制平倉 exit_reason='data_end' (BC-VB-10)
- [x] 連續 SL → 每筆獨立觸發 (BC-VB-12)
- [x] Take Profit 正確觸發
- [x] Stop Loss 正確觸發
- [x] Trailing Stop 啟動條件正確
- [x] 手續費 + 滑點正確扣除

**驗證命令**：
```bash
pytest tests/momentum/Strategy/test_vectorized_backtest.py -k "trade or tp or sl or trailing" -v --tb=short
```

**Checklist**：
- [x] `_calculate_position_sizes` 整合 3 種 PositionSizer
- [x] `_execute_trades` 含 SL/TP/Trailing Stop 完整邏輯
- [x] `_calculate_equity_curve` 向量化
- [x] MAE/MFE 計算
- [x] exit_reason 正確標記 5 種類型

---

### Task 4.1.5：PerformanceMetrics — 12+ 指標

**檔案**：
- `momentum/Strategy/performance_metrics.py` (完整實作)

**類別定義** (對齊 SPEC §6.2)：
```python
class PerformanceMetrics:
    def __init__(self, equity_curve: pd.Series, trades: List[Trade],
                 risk_free_rate: float = 0.02, periods_per_year: int = 730):
        if periods_per_year <= 0:
            raise ValueError(f"periods_per_year must be > 0, got {periods_per_year}")
        ...

    # 報酬指標
    def total_return(self) -> float: ...
    def cagr(self) -> float: ...

    # 風險調整報酬
    def sharpe_ratio(self) -> float: ...
    def sortino_ratio(self) -> float: ...
    def calmar_ratio(self) -> float: ...

    # 風險指標
    def max_drawdown(self) -> float: ...
    def max_drawdown_duration(self) -> int: ...

    # Van Tharp 系統
    def expectancy(self) -> float: ...
    def system_quality_number(self) -> float: ...
    def win_rate(self) -> float: ...
    def profit_factor(self) -> float: ...
    def avg_win(self) -> float: ...
    def avg_loss(self) -> float: ...

    # 彙整
    def calculate_all(self) -> Dict[str, float]: ...
```

**公式** (SPEC §6.2.2)：
- Sharpe: $Sharpe = \frac{\bar{R} - R_f / P}{\sigma_R} \times \sqrt{P}$
- Sortino: $Sortino = \frac{\bar{R} - R_f / P}{\sigma_{down}} \times \sqrt{P}$
- Expectancy: $E = WR \times \overline{W} - (1 - WR) \times |\overline{L}|$
- SQN: $SQN = \frac{\overline{R_{mult}}}{\sigma_{R_{mult}}} \times \sqrt{\min(N, 100)}$
- Kelly: $f = \frac{p \cdot b - q}{b}$

**邊界處理統一規則**：
- 分母為 0 → 回傳 0.0（非 raise）
- 空輸入 → 回傳 0.0（非 raise）
- NaN → dropna 後計算
- 無效建構參數 → raise ValueError

**邊界條件覆蓋**: BC-PM-01 ~ BC-PM-13（全部 13 個）

**驗收條件**：
- [x] 12+ 指標全部實作且公式正確
- [x] 13 個邊界條件全覆蓋
- [x] `calculate_all()` 回傳含所有指標的 dict
- [x] `periods_per_year=0` raise ValueError (BC-PM-13)

**驗證命令**：
```bash
pytest tests/momentum/Strategy/test_performance_metrics.py -v --tb=short
```

### 驗證檢查點
- PASS: `sharpe_ratio()` 對已知 equity curve 與 QuantStats 結果誤差 < 1%
- PASS: 分母為 0 時所有比率指標回傳 0.0 而非拋例外

**Checklist**：
- [x] `total_return`, `cagr`
- [x] `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`
- [x] `max_drawdown`, `max_drawdown_duration`
- [x] `expectancy`, `system_quality_number`
- [x] `win_rate`, `profit_factor`
- [x] `avg_win`, `avg_loss`
- [x] `calculate_all()` 彙整
- [x] 13 邊界條件全覆蓋

---

### Task 4.1.6：PositionSizer — 3 種方法

**檔案**：
- `momentum/Strategy/position_sizing.py` (完整實作)

**3 個類別** (SPEC §6.3)：
```python
class KellyPositionSizer:
    def __init__(self, kelly_fraction: float = 0.5, max_position: float = 0.25): ...
    def calculate_position_size(self, predicted_proba: float, equity: float,
                                 risk_params: Dict[str, Any]) -> float: ...
        # Kelly: f = (p*b - q) / b, actual = f * kelly_fraction, clip [0, max_position]
        # risk_params 需含 win_loss_ratio (b)

class FixedPositionSizer:
    def __init__(self, fixed_size: float = 0.1): ...
    def calculate_position_size(self, predicted_proba: float, equity: float,
                                 risk_params: Dict[str, Any]) -> float: ...

class ProbabilityScaledSizer:
    def __init__(self, max_position: float = 0.25, threshold: float = 0.5): ...
    def calculate_position_size(self, predicted_proba: float, equity: float,
                                 risk_params: Dict[str, Any]) -> float: ...
        # size = (proba - threshold) / (1 - threshold) * max_position
```

**邊界條件覆蓋**:
- Kelly: BC-KL-01 ~ BC-KL-10（10 個）
- ProbabilityScaled: BC-PS-01 ~ BC-PS-05（5 個）

**驗收條件**：
- [x] Kelly: proba=0 → 0, proba=1 → max_position, b=0 → raise ValueError
- [x] Fixed: 永遠回傳 fixed_size
- [x] ProbScaled: proba=threshold → 0, proba=1.0 → max_position
- [x] 3 種方法均符合 `IPositionSizer` Protocol

**驗證命令**：
```bash
pytest tests/momentum/Strategy/test_position_sizing.py -v --tb=short
```

### 驗證檢查點
- PASS: `KellyPositionSizer` raise ValueError 當 `win_loss_ratio=0` (BC-KL-05)
- PASS: `ProbabilityScaledSizer` raise ValueError 當 `threshold=1.0` (BC-PS-04)

**Checklist**：
- [x] `KellyPositionSizer` 完整實作 + 10 邊界
- [x] `FixedPositionSizer` 完整實作
- [x] `ProbabilityScaledSizer` 完整實作 + 5 邊界
- [x] 3 者均符合 `IPositionSizer` Protocol

---

### Task 4.1.7：RiskManager — SL/TP/Trailing

**檔案**：
- `momentum/Strategy/risk_manager.py` (完整實作)

**函式簽名** (SPEC §6.4)：
```python
class RiskManager:
    @staticmethod
    def calculate_stop_loss(entry_price: float, atr: float, multiplier: float) -> float:
        """停損 = entry_price - atr × multiplier"""

    @staticmethod
    def calculate_take_profit(entry_price: float, atr: float,
                               sl_multiplier: float, tp_ratio: float) -> float:
        """止盈 = entry_price + atr × sl_multiplier × tp_ratio"""

    @staticmethod
    def calculate_trailing_stop(entry_price: float, current_high: float,
                                 atr: float, activation_multiplier: float) -> Optional[float]:
        """追蹤止損: 啟動後 trailing_stop = current_high - atr × multiplier"""
```

**邊界條件覆蓋**: BC-RM-01 ~ BC-RM-06（6 個）

**驗收條件**：
- [x] atr=0 → SL/TP = entry_price + warn (BC-RM-01)
- [x] atr<0 → raise ValueError (BC-RM-02)
- [x] multiplier=0 → SL = entry_price + warn (BC-RM-03)
- [x] entry_price=0 → raise ValueError (BC-RM-04)
- [x] trailing 未達啟動條件 → None (BC-RM-05)
- [x] TP < entry → raise ValueError (BC-RM-06)

**驗證命令**：
```bash
pytest tests/momentum/Strategy/test_risk_manager.py -v --tb=short
```

**Checklist**：
- [x] `calculate_stop_loss` 含 3 邊界
- [x] `calculate_take_profit` 含 1 邊界
- [x] `calculate_trailing_stop` 含 2 邊界

---

### Task 4.1.8：Strategy Domain 單元測試（~110 tests）

**檔案**：
- `tests/momentum/Strategy/test_vectorized_backtest.py` (新建 — ~25 tests)
- `tests/momentum/Strategy/test_performance_metrics.py` (新建 — ~50 tests)
- `tests/momentum/Strategy/test_position_sizing.py` (新建 — ~20 tests)
- `tests/momentum/Strategy/test_risk_manager.py` (新建 — ~15 tests)
- `tests/momentum/Strategy/__init__.py` (新建)
- `tests/momentum/__init__.py` (新建，若不存在)

**VectorizedBacktest 測試清單** (25 tests，對齊 SPEC §12.2.1)：

| # | 測試名稱 | 類型 | 邊界 |
|---|---------|------|------|
| 1 | `test_normal_backtest_with_trades` | 正常 | — |
| 2 | `test_normal_backtest_metrics_calculated` | 正常 | — |
| 3 | `test_empty_prices` | 邊界 | BC-VB-01 |
| 4 | `test_single_bar_prices` | 邊界 | BC-VB-02 |
| 5 | `test_zero_proba_no_signals` | 邊界 | BC-VB-03 |
| 6 | `test_all_proba_one_with_cooldown` | 邊界 | BC-VB-04 |
| 7 | `test_threshold_above_one_no_trades` | 邊界 | BC-VB-05 |
| 8 | `test_entry_le_exit_threshold_error` | 邊界 | BC-VB-06 |
| 9 | `test_atr_contains_nan_fallback` | 邊界 | BC-VB-07 |
| 10 | `test_atr_all_zero_signal_exit_only` | 邊界 | BC-VB-08 |
| 11 | `test_high_commission_warning` | 邊界 | BC-VB-09 |
| 12 | `test_unclosed_position_at_data_end` | 邊界 | BC-VB-10 |
| 13 | `test_cooldown_exceeds_data_length` | 邊界 | BC-VB-11 |
| 14 | `test_consecutive_stop_losses` | 邊界 | BC-VB-12 |
| 15 | `test_zero_price_error` | 邊界 | BC-VB-13 |
| 16 | `test_mismatched_lengths_error` | 邊界 | BC-VB-14 |
| 17 | `test_kelly_position_sizing_integration` | 整合 | — |
| 18 | `test_fixed_position_sizing_integration` | 整合 | — |
| 19 | `test_probability_scaled_integration` | 整合 | — |
| 20 | `test_take_profit_triggered` | 功能 | — |
| 21 | `test_stop_loss_triggered` | 功能 | — |
| 22 | `test_trailing_stop_triggered` | 功能 | — |
| 23 | `test_signal_exit_triggered` | 功能 | — |
| 24 | `test_commission_slippage_deduction` | 功能 | — |
| 25 | `test_backtest_performance_benchmark` | 性能 | NFR-1 |

**PerformanceMetrics 測試清單** (50 tests，對齊 SPEC §12.2.2)：
每個指標 4 類測試 × 13 指標 ≈ 50 tests

**PositionSizer 測試清單** (20 tests，對齊 SPEC §12.2.3)：
- Kelly: 正常 2 + 邊界 BC-KL-01~10 = 12
- Fixed: 正常 2 + 邊界 2 = 4
- ProbScaled: 正常 2 + 邊界 BC-PS-01~05 = 7
- 去重後 ≈ 20

**RiskManager 測試清單** (15 tests，對齊 SPEC §12.2.4)：
- SL: 正常 2 + 邊界 BC-RM-01~04 = 6
- TP: 正常 2 + 邊界 BC-RM-06 = 3
- Trailing: 正常 2 + 邊界 BC-RM-05 = 3
- 額外 3 = 15

**Global Fixtures** (`tests/conftest.py` 擴展)：
```python
@pytest.fixture
def mock_prices():
    dates = pd.date_range('2025-01-01', periods=100, freq='12h')
    np.random.seed(42)
    close = 40000 + np.cumsum(np.random.randn(100) * 500)
    return pd.DataFrame({
        'timestamp': dates,
        'open': close + np.random.randn(100) * 100,
        'high': close + abs(np.random.randn(100) * 300),
        'low': close - abs(np.random.randn(100) * 300),
        'close': close,
    })

@pytest.fixture
def mock_predicted_proba():
    np.random.seed(42)
    return pd.Series(np.random.uniform(0.3, 0.9, 100))

@pytest.fixture
def mock_atr():
    np.random.seed(42)
    return pd.Series(np.random.uniform(500, 2000, 100))

@pytest.fixture
def mock_strategy_params():
    return {
        'entry_threshold': 0.7,
        'exit_threshold': 0.4,
        'stop_loss_atr': 2.0,
        'take_profit_ratio': 3.0,
        'position_sizing_method': 'fixed',
        'kelly_fraction': 0.5,
        'max_position_size': 0.25,
        'cooldown_bars': 5,
        'trailing_stop_activation': 0.05,
    }
```

**驗收條件**：
- [x] 所有 ~110 tests 通過
- [x] 覆蓋率 100%

**驗證命令**：
```bash
pytest tests/momentum/Strategy/ -v --tb=short --cov=momentum.Strategy --cov-report=term --cov-fail-under=100
```

**Checklist**：
- [x] 25 VectorizedBacktest 測試（14 邊界 + 11 功能/整合/性能）
- [x] 50 PerformanceMetrics 測試（13 指標 × ~4 邊界）
- [x] 20 PositionSizer 測試（15 邊界 + 5 正常）
- [x] 15 RiskManager 測試（6 邊界 + 9 正常/功能）
- [x] conftest.py fixtures 更新
- [x] `--cov-fail-under=100` 通過

---

## Phase 4.2：Objective 增強

### Task 4.2.1：StrategyBacktestObjective — 建構子重構 (Breaking Change)

**檔案**：
- `momentum/Optimization/objectives/strategy_backtest.py` (修改)

**現有建構子**：
```python
def __init__(self, model_predictions: Any, price_data: Any, multi_objective: bool = False):
```

**增強後建構子**：
```python
def __init__(
    self,
    backtest_engine: IBacktestEngine,
    prices: pd.DataFrame,
    predicted_proba: pd.Series,
    atr_values: pd.Series,
    target_metric: str = "expectancy",
    constraints: Optional[Dict[str, float]] = None,
    multi_objective: bool = False
):
    # 驗證 target_metric
    supported = ['expectancy', 'sharpe_ratio', 'sortino_ratio', 'calmar_ratio', 'sqn']
    if target_metric not in supported:
        raise ValueError(f"Unsupported target_metric: {target_metric}. Options: {supported}")
    ...
```

**Breaking Change 遷移** (SPEC §6.5.1)：
> 呼叫點僅 3 處 — 一次性修改：

| 呼叫點 | 檔案 | 所需修改 |
|--------|------|---------|
| 1 | `api/services/optimization_task_service.py` `_build_strategy_backtest_objective()` | 更新建構參數 |
| 2 | `tests/*/test_optuna_objectives.py` (測試 1) | 更新建構參數 |
| 3 | `tests/*/test_optuna_objectives.py` (測試 2) | 更新建構參數 |

**驗收條件**：
- [x] 新建構子接受 `IBacktestEngine` Protocol
- [x] `target_metric` 不在支援列表 → raise ValueError (BC-SO-02)
- [x] 舊的 3 個呼叫點全部更新
- [x] 所有現有測試通過

**驗證命令**：
```bash
pytest tests/ -k "strategy_backtest" -v --tb=short
```

**Checklist**：
- [x] 建構子重構
- [x] `target_metric` 驗證 (BC-SO-02)
- [x] 遷移 3 個呼叫點
- [x] 移除內嵌 `_run_backtest()` → 委託 VectorizedBacktest

---

### Task 4.2.2：StrategyBacktestObjective — 搜索空間 + 評估增強

**檔案**：
- `momentum/Optimization/objectives/strategy_backtest.py` (續修改)

**增強搜索空間** (9 參數，SPEC §6.5.2)：
```python
def create_search_space(self, trial) -> Dict[str, Any]:
    return {
        'entry_threshold': trial.suggest_float('entry_threshold', 0.5, 0.95, step=0.05),
        'exit_threshold': trial.suggest_float('exit_threshold', 0.3, 0.6, step=0.05),
        'stop_loss_atr': trial.suggest_float('stop_loss_atr', 1.0, 5.0, step=0.5),
        'take_profit_ratio': trial.suggest_float('take_profit_ratio', 1.0, 5.0, step=0.5),
        'position_sizing_method': trial.suggest_categorical(
            'position_sizing_method', ['fixed', 'kelly', 'probability_scaled']),
        'kelly_fraction': trial.suggest_float('kelly_fraction', 0.25, 0.75, step=0.05),
        'max_position_size': trial.suggest_float('max_position_size', 0.1, 0.5, step=0.1),
        'cooldown_bars': trial.suggest_int('cooldown_bars', 0, 20, step=5),
        'trailing_stop_activation': trial.suggest_float(
            'trailing_stop_activation', 0.01, 0.10, step=0.01),
    }
```

**增強 evaluate** (SPEC §6.5.3)：
```python
def evaluate(self, params: Dict[str, Any]) -> float:
    result = self.backtest_engine.run_backtest(
        self.prices, self.predicted_proba, self.atr_values, params)
    metrics = PerformanceMetrics(result.equity_curve, result.trades)
    all_metrics = metrics.calculate_all()

    # 約束 Pruning
    if all_metrics['max_drawdown'] < self.constraints.get('max_drawdown', -0.30):
        raise optuna.TrialPruned(...)
    if all_metrics['win_rate'] < self.constraints.get('min_win_rate', 0.40):
        raise optuna.TrialPruned(...)
    if all_metrics.get('total_trades', 0) < self.constraints.get('min_trades', 10):
        raise optuna.TrialPruned(...)

    return all_metrics[self.target_metric]
```

**邊界條件覆蓋**: BC-SO-01 ~ BC-SO-05

**驗收條件**：
- [x] 搜索空間含 9 參數
- [x] SL/TP 使用 ATR 倍數（非百分比）
- [x] 約束觸發時 raise TrialPruned
- [x] 全部 Pruned → 特殊空結果處理 (BC-SO-01)

**驗證命令**：
```bash
pytest tests/momentum/Optimization/test_strategy_backtest_enhanced.py -v --tb=short
```

**Checklist**：
- [x] 搜索空間 9 參數
- [x] evaluate 委託 VectorizedBacktest + PerformanceMetrics
- [x] MaxDD/WinRate/MinTrades 約束 Pruning
- [x] target_metric 可選 (5 種)
- [x] 多目標模式支援 (BC-SO-05)
- [x] trial.user_attrs 記錄所有 metrics

---

### Task 4.2.3：ModelHyperparamObjective — 過擬合檢測 + 搜索空間驗證

**檔案**：
- `momentum/Optimization/objectives/model_hyperparam.py` (修改)

**增強內容** (SPEC §6.6.1)：
```python
# evaluate() 增強
def evaluate(self, params: Dict[str, Any]) -> float:
    # 既有邏輯 ...
    train_auc = ...
    val_auc = ...
    gap = train_auc - val_auc

    # 過擬合檢測 (新增)
    if gap > self.max_train_val_gap:
        raise optuna.TrialPruned(f"Train-Val gap {gap:.4f} > threshold {self.max_train_val_gap}")

    # 記錄至 trial.user_attrs (新增)
    trial.set_user_attr('train_auc', train_auc)
    trial.set_user_attr('val_auc', val_auc)
    trial.set_user_attr('train_val_gap', gap)

    return val_auc
```

**搜索空間驗證** (SPEC §6.6.2/6.6.3)：
```python
def _validate_search_space(self, space: dict):
    """驗證搜索空間範圍合理性"""
    # LightGBM: learning_rate not < 0.005, num_leaves not > 150, etc.
    # XGBoost: max_depth not > 12, etc.
```

**邊界條件覆蓋**: BC-HO-01 ~ BC-HO-07

**驗收條件**：
- [x] Train-Val Gap > threshold → TrialPruned (BC-HO-02)
- [x] 搜索空間 min > max → raise ValueError (BC-HO-01)
- [x] 模型訓練失敗 → FATAL (BC-HO-03)
- [x] AUC < 0.5 → WARNING 不 Prune (BC-HO-04)
- [x] 特徵數=0 → raise ValueError (BC-HO-05)
- [x] 樣本數 < 100 → WARNING (BC-HO-06)
- [x] 無效 model_type → raise ValueError (BC-HO-07)

**驗證命令**：
```bash
pytest tests/momentum/Optimization/test_model_hyperparam_enhanced.py -v --tb=short
```

**Checklist**：
- [x] 過擬合檢測 (Train-Val Gap)
- [x] 搜索空間驗證 (LightGBM + XGBoost)
- [x] trial.user_attrs 記錄
- [x] 前端搜索空間 JSON Schema 提供
- [x] 7 個邊界條件覆蓋

---

### Task 4.2.4：Objective 增強測試（~35 tests）

**檔案**：
- `tests/momentum/Optimization/test_strategy_backtest_enhanced.py` (新建 — ~20 tests)
- `tests/momentum/Optimization/test_model_hyperparam_enhanced.py` (新建 — ~15 tests)
- `tests/momentum/Optimization/__init__.py` (新建)

**StrategyBacktestObjective 測試清單** (20 tests，SPEC §12.2.5)：

| # | 測試名稱 | 類型 |
|---|---------|------|
| 1 | `test_evaluate_returns_target_metric` | 正常 |
| 2 | `test_evaluate_with_constraints_pass` | 正常 |
| 3 | `test_evaluate_maxdd_constraint_pruned` | 約束 |
| 4 | `test_evaluate_winrate_constraint_pruned` | 約束 |
| 5 | `test_evaluate_min_trades_pruned` | 約束 |
| 6 | `test_all_trials_pruned_handling` | BC-SO-01 |
| 7 | `test_invalid_target_metric` | BC-SO-02 |
| 8 | `test_nan_proba_input` | BC-SO-03 |
| 9 | `test_non_continuous_timestamps` | BC-SO-04 |
| 10 | `test_multi_objective_mode` | BC-SO-05 |
| 11 | `test_create_search_space_params` | 功能 |
| 12 | `test_backtest_engine_protocol_injection` | Protocol |
| 13 | `test_target_metric_expectancy` | 功能 |
| 14 | `test_target_metric_sortino` | 功能 |
| 15 | `test_target_metric_calmar` | 功能 |
| 16 | `test_target_metric_sqn` | 功能 |
| 17 | `test_evaluate_stores_trial_user_attrs` | 功能 |
| 18 | `test_evaluate_with_empty_backtest_result` | 邊界 |
| 19 | `test_directions_property_multi_objective` | 屬性 |
| 20 | `test_name_property` | 屬性 |

**ModelHyperparamObjective 測試清單** (15 tests，SPEC §12.2.6)：

| # | 測試名稱 | 類型 |
|---|---------|------|
| 1 | `test_evaluate_returns_auc` | 正常 |
| 2 | `test_overfitting_detection_pruned` | BC-HO-02 |
| 3 | `test_search_space_min_gt_max_error` | BC-HO-01 |
| 4 | `test_model_training_failure_fatal` | BC-HO-03 |
| 5 | `test_auc_below_random` | BC-HO-04 |
| 6 | `test_zero_features_error` | BC-HO-05 |
| 7 | `test_small_training_set_warning` | BC-HO-06 |
| 8 | `test_invalid_model_type` | BC-HO-07 |
| 9 | `test_lightgbm_search_space_ranges` | 參數 |
| 10 | `test_xgboost_search_space_ranges` | 參數 |
| 11 | `test_trial_user_attrs_recorded` | 功能 |
| 12 | `test_cv_folds_parameter` | 功能 |
| 13 | `test_custom_train_kwargs` | 功能 |
| 14 | `test_name_property` | 屬性 |
| 15 | `test_direction_property` | 屬性 |

**驗證命令**：
```bash
pytest tests/momentum/Optimization/ -v --tb=short --cov=momentum.Optimization.objectives --cov-report=term --cov-fail-under=100
```

**Checklist**：
- [x] 20 StrategyBacktestObjective tests
- [x] 15 ModelHyperparamObjective tests
- [x] 覆蓋率 100%

### 驗證檢查點
- PASS（成功路徑）：`tests/momentum/Optimization/` 全部通過，且 `StrategyBacktestObjective` 能回傳選定 `target_metric`（含 `trial.user_attrs` 記錄）。
- PASS（失敗/邊界）：當 `target_metric` 無效、搜索空間 `min > max`、或約束違反時，分別可穩定觸發 `ValueError` / `TrialPruned`，且不產生未分類例外。

---

## Phase 4.3：API + Service 層

### Task 4.3.1：Pydantic Request/Response Models

**檔案**：
- `api/models/optimization_models.py` (新建)

**模型定義**：
```python
# === Execution Optimization ===
class ExecutionOptimizationRequest(BaseModel):
    model_predictions_path: str         # model_predictions_{task_id}.csv
    target_metric: str = "expectancy"   # expectancy | sharpe_ratio | sortino_ratio | calmar_ratio | sqn
    n_trials: int = 100
    timeout_seconds: int = 300
    search_space_override: Optional[Dict] = None
    constraints: Optional[Dict[str, float]] = None
    backtest_config: Optional[Dict] = None   # commission, slippage
    multi_objective: bool = False

class ExecutionOptimizationResponse(BaseModel):
    task_id: str
    status: str
    created_at: str

# === Hyperparameter Optimization ===
class HyperparamOptimizationRequest(BaseModel):
    model_type: str = "lightgbm"        # lightgbm | xgboost
    features_path: str
    labels_path: str
    n_trials: int = 100
    timeout_seconds: int = 1800
    search_space_override: Optional[Dict] = None
    max_train_val_gap: float = 0.1
    cv_folds: int = 5

class HyperparamOptimizationResponse(BaseModel):
    task_id: str
    status: str
    created_at: str

# === 共用 ===
class OptimizationResultResponse(BaseModel):
    task_id: str
    task_type: str
    status: str
    best_trial: Optional[Dict] = None
    performance_metrics: Optional[Dict] = None
    parameter_importance: Optional[Dict] = None

class OptimizationConfigResponse(BaseModel):
    execution: Dict
    hyperparameter: Dict
```

**驗收條件**：
- [x] 所有 Request/Response Model 定義完整
- [x] 不 import `momentum.*`（Rule 7）

**驗證命令**：
```bash
python -c "from api.models.optimization_models import ExecutionOptimizationRequest, HyperparamOptimizationRequest; print('OK')"
```

**Checklist**：
- [x] `ExecutionOptimizationRequest` / Response
- [x] `HyperparamOptimizationRequest` / Response
- [x] `OptimizationResultResponse`
- [x] `OptimizationConfigResponse`
- [x] 不違反 Rule 7

---

### Task 4.3.2：API 路由

**檔案**：
- `api/routes/hyperparameter_optimization.py` (新建)
- `api/routes/execution_optimization.py` (新建)
- `api/main.py` (修改 — 路由註冊)

**路由定義**：
```python
# hyperparameter_optimization.py
router = APIRouter(prefix="/api/v1/optimization", tags=["Hyperparameter Optimization"])

@router.post("/hyperparameter")   # 啟動超參數優化
@router.get("/config")             # 取得配置
@router.post("/{task_type}/{task_id}/export")  # 匯出結果

# execution_optimization.py
router = APIRouter(prefix="/api/v1/optimization", tags=["Execution Optimization"])

@router.post("/execution")        # 啟動策略執行優化
@router.get("/{task_id}/result")   # 查詢結果
```

**驗收條件**：
- [x] `POST /api/v1/optimization/hyperparameter` 回傳 task_id
- [x] `POST /api/v1/optimization/execution` 回傳 task_id
- [x] `GET /api/v1/optimization/config` 回傳 YAML 配置
- [x] `GET /api/v1/optimization/{task_id}/result` 回傳結果
- [x] `POST /api/v1/optimization/{task_type}/{task_id}/export` 匯出

**驗證命令**：
```bash
python -c "from api.routes.hyperparameter_optimization import router; print(f'{len(router.routes)} routes')"
python -c "from api.routes.execution_optimization import router; print(f'{len(router.routes)} routes')"
```

**Checklist**：
- [x] hyperparameter 路由
- [x] execution 路由
- [x] config 路由
- [x] result 路由
- [x] export 路由
- [x] `api/main.py` 註冊

---

### Task 4.3.3：OptimizationTaskService 增強

**檔案**：
- `api/services/optimization_task_service.py` (修改)

**增強內容**：
```python
# 新增 task_type 支援
# 現有: "signal_density" | "model_hyperparam" | "strategy_backtest"
# 增強: 保留現有 + 增強 "strategy_backtest" 和 "model_hyperparam" 建構邏輯

def _build_strategy_backtest_objective(self, objective_config: dict):
    """使用 Factory 建構增強後的 StrategyBacktestObjective"""
    from momentum.factories import create_backtest_engine
    backtest_engine = create_backtest_engine(
        commission=objective_config.get('commission', 0.001),
        slippage=objective_config.get('slippage', 0.0005)
    )
    # 讀取 model_predictions CSV
    # 建構 StrategyBacktestObjective (增強版建構子)
    ...
```

**WebSocket 新事件** (SPEC §11.7)：
- `backtest_progress` — 策略回測進度
- `pareto_update` — 多目標 Pareto 更新
- `overfitting_alert` — 過擬合警告

**驗收條件**：
- [x] `_build_strategy_backtest_objective()` 使用 Factory (Rule 3)
- [x] 3 個新 WebSocket 事件正確推送
- [x] 現有 task_type 不受影響

**驗證命令**：
```bash
pytest tests/api/ -k "optimization" -v --tb=short
```

**Checklist**：
- [x] `_build_strategy_backtest_objective` 增強
- [x] `_build_model_hyperparam_objective` 增強
- [x] WebSocket `backtest_progress` 事件
- [x] WebSocket `pareto_update` 事件
- [x] WebSocket `overfitting_alert` 事件
- [x] 向後相容（現有 task 可繼續查詢）

### 驗證檢查點
- PASS（成功路徑）：`POST /api/v1/optimization/hyperparameter` 與 `POST /api/v1/optimization/execution` 可回傳 `task_id`，`GET /api/v1/optimization/{task_id}/result` 依任務狀態回傳一致欄位。
- PASS（失敗/邊界）：當請求參數不合法（Pydantic 驗證失敗）或 `task_id` 不存在時，API 回傳可辨識錯誤狀態，不影響既有 task_type 查詢路徑。

---

## Phase 4.4：前端 UI

### Task 4.4.1：TypeScript 型別定義

**檔案**：
- `frontend/src/lib/types/optimization.ts` (新建或修改 `lib/types.ts`)

**型別定義** (對齊後端 Pydantic Model)：
```typescript
// Execution Optimization
export interface ExecutionOptimizationConfig {
  model_predictions_path: string;
  target_metric: 'expectancy' | 'sharpe_ratio' | 'sortino_ratio' | 'calmar_ratio' | 'sqn';
  n_trials: number;
  timeout_seconds: number;
  search_space_override?: Record<string, any>;
  constraints?: { max_drawdown?: number; min_win_rate?: number; min_trades?: number; };
  backtest_config?: { commission?: number; slippage?: number; };
  multi_objective: boolean;
}

// Hyperparameter Optimization
export interface HyperparamOptimizationConfig {
  model_type: 'lightgbm' | 'xgboost';
  features_path: string;
  labels_path: string;
  n_trials: number;
  search_space_override?: Record<string, any>;
  max_train_val_gap: number;
  cv_folds: number;
}

// Results
export interface OptimizationResult {
  task_id: string;
  task_type: string;
  status: string;
  best_trial?: { trial_number: number; value: number; params: Record<string, any>; };
  performance_metrics?: Record<string, number>;
  parameter_importance?: Record<string, number>;
  constraint_satisfaction?: Record<string, { limit: number; actual: number; satisfied: boolean; }>;
}

// WebSocket events
export interface BacktestProgressEvent { trial_number: number; sharpe: number; max_dd: number; win_rate: number; expectancy: number; }
export interface ParetoUpdateEvent { pareto_front: Array<{ sharpe: number; max_dd: number; }>; }
export interface OverfittingAlertEvent { trial_number: number; train_val_gap: number; threshold: number; }
```

**Checklist**：
- [x] Execution config + result 型別
- [x] Hyperparameter config + result 型別
- [x] WebSocket 3 新事件型別
- [x] 與後端 Pydantic Model 一致

---

### Task 4.4.2：超參數優化頁面

**檔案** (SPEC §10.1, §10.2)：
- `frontend/src/app/optimization-hyperparameter/page.tsx` (新建 — 配置頁)
- `frontend/src/app/optimization-hyperparameter/result/[taskId]/page.tsx` (新建 — 結果頁)
- `frontend/src/components/optimization/hyperparameter/HyperparamConfigForm.tsx` (新建)
- `frontend/src/components/optimization/hyperparameter/ParameterImportanceChart.tsx` (新建)
- `frontend/src/components/optimization/hyperparameter/OverfittingCheckChart.tsx` (新建)

**配置頁核心元件**：
1. 模型選擇器: LightGBM / XGBoost (Tab)
2. 搜索空間配置表格 (從 `optimization_config.yaml` 讀取)
3. 約束條件: Train-Val Gap 上限滑桿
4. Optuna 設定: Sampler / Trials / Timeout
5. 啟動按鈕 + WebSocket 進度

**結果頁核心元件**：
1. 最佳超參數卡片
2. 指標摘要 (Val AUC, Train-Val Gap)
3. Parameter Importance 圖表
4. 過擬合檢查散點圖 (Train AUC vs Val AUC)
5. Trial 比較表

**驗收條件**：
- [x] `/optimization-hyperparameter` 頁面可訪問
- [x] 搜索空間表格從 API 讀取配置
- [x] 啟動後 WebSocket 進度正確顯示
- [x] 結果頁圖表正確渲染

**驗證命令**：
```bash
cd frontend && npm run build
```

**Checklist**：
- [x] 配置頁 `page.tsx`
- [x] 結果頁 `result/[taskId]/page.tsx`
- [x] `HyperparamConfigForm` 元件
- [x] `ParameterImportanceChart` 元件
- [x] `OverfittingCheckChart` 元件
- [x] 空/載入/錯誤狀態處理

---

### Task 4.4.3：策略執行優化頁面

**檔案** (SPEC §10.3, §10.4)：
- `frontend/src/app/optimization-execution/page.tsx` (新建 — 配置頁)
- `frontend/src/app/optimization-execution/result/[taskId]/page.tsx` (新建 — 結果頁)
- `frontend/src/components/optimization/execution/ExecutionConfigForm.tsx` (新建)
- `frontend/src/components/optimization/execution/EquityCurveChart.tsx` (新建)
- `frontend/src/components/optimization/execution/DrawdownChart.tsx` (新建)
- `frontend/src/components/optimization/execution/ParetoFrontChart.tsx` (新建)

**配置頁核心元件**：
1. 數據源選擇 (模型訓練任務下拉)
2. 策略參數搜索空間配置表格
3. 倉位管理方法選擇 (Fixed/Kelly/ProbScaled)
4. 優化目標選擇 (5 種 Radio)
5. 風險約束 (MaxDD/WinRate/MinTrades Slider)
6. 多目標開關
7. 啟動按鈕 + WebSocket 進度

**結果頁核心元件**：
1. 績效摘要卡片 (3×2 Grid)
2. 最佳參數卡片
3. 權益曲線 (策略 vs Buy & Hold)
4. 回撤曲線面積圖
5. 交易 PnL% 分佈直方圖
6. Parameter Importance 圖表
7. Pareto 前沿圖 (多目標)
8. 交易明細表
9. Benchmark 比較
10. 匯出功能

**驗收條件**：
- [x] `/optimization-execution` 頁面可訪問
- [x] 配置表格可編輯搜索空間
- [x] 結果頁 10 個元件全部渲染
- [x] 匯出 JSON/CSV/PNG 功能正常

**驗證命令**：
```bash
cd frontend && npm run build
```

**Checklist**：
- [x] 配置頁 `page.tsx`
- [x] 結果頁 `result/[taskId]/page.tsx`
- [x] `ExecutionConfigForm` 元件
- [x] `EquityCurveChart` 元件 (Recharts LineChart)
- [x] `DrawdownChart` 元件 (Recharts AreaChart)
- [x] `ParetoFrontChart` 元件 (Recharts ScatterChart)
- [x] 空/載入/錯誤狀態處理
- [x] 響應式設計

---

### Task 4.4.4：共用元件 + Store + Hooks

**檔案**：
- `frontend/src/components/optimization/common/OptunaProgressBar.tsx` (新建)
- `frontend/src/components/optimization/common/ParameterRangeSlider.tsx` (新建)
- `frontend/src/components/optimization/common/SamplerSelector.tsx` (新建)
- `frontend/src/components/optimization/common/TrialComparisonTable.tsx` (新建)
- `frontend/src/store/optimizationStore.ts` (修改 — 增強)
- `frontend/src/lib/api/optimizationApi.ts` (修改 — 增強)

**Store 增強**：
```typescript
interface OptimizationState {
  // 現有...
  // 新增
  hyperparamConfig: HyperparamOptimizationConfig | null;
  executionConfig: ExecutionOptimizationConfig | null;
  currentResult: OptimizationResult | null;
  setHyperparamConfig: (config: HyperparamOptimizationConfig) => void;
  setExecutionConfig: (config: ExecutionOptimizationConfig) => void;
}
```

**API 增強**：
```typescript
export const startHyperparamOptimization = (config: HyperparamOptimizationConfig) => ...
export const startExecutionOptimization = (config: ExecutionOptimizationConfig) => ...
export const getOptimizationResult = (taskId: string) => ...
export const getOptimizationConfig = () => ...
export const exportOptimizationResult = (taskType: string, taskId: string, format: string) => ...
```

**驗收條件**：
- [x] 4 個共用元件可渲染
- [x] Store 正確管理 hyperparameter/execution 狀態
- [x] API 函式與後端端點對應

**Checklist**：
- [x] `OptunaProgressBar` (WebSocket 驅動進度條)
- [x] `ParameterRangeSlider` (min/max/step 滑桿)
- [x] `SamplerSelector` (TPE/CmaEs/Random 下拉)
- [x] `TrialComparisonTable` (可排序/篩選/匯出)
- [x] `optimizationStore.ts` 增強
- [x] `optimizationApi.ts` 增強

### 驗證檢查點
- PASS（成功路徑）：`/optimization-hyperparameter` 與 `/optimization-execution` 皆可載入配置、啟動任務、並在結果頁渲染對應圖表與表格。
- PASS（失敗/邊界）：當 API 回傳空資料、載入中或錯誤時，頁面僅顯示既定 Empty/Loading/Error 狀態，不出現未處理例外或型別錯誤。

---

## Phase 4.5：輸出格式

### Task 4.5.1：JSON + CSV 輸出生成

**檔案**：
- `api/services/optimization_output_service.py` (新建)

**功能**：
- 生成 `summary.json` (SPEC §11.2, §11.3)
- 生成 `trades.csv` (SPEC §11.5)
- 生成 `equity_curve.csv` (SPEC §11.5)
- 生成 `trials.csv` (SPEC §11.5)
- 目錄結構: `optimization_results/{execution|hyperparameter}/{task_id}/`

**驗收條件**：
- [x] `summary.json` 包含 meta, best_trial, performance_metrics, constraint_satisfaction, parameter_importance, benchmark_comparison
- [x] `trades.csv` 含 12 欄位
- [x] `equity_curve.csv` 含 5 欄位

**驗證命令**：
```bash
python -c "from api.services.optimization_output_service import OptimizationOutputService; print('OK')"
```

**Checklist**：
- [x] `summary.json` 生成 (execution + hyperparameter)
- [x] `trades.csv` 生成
- [x] `equity_curve.csv` 生成
- [x] `trials.csv` 生成
- [x] 目錄自動建立

---

### Task 4.5.2：AI-Readable Report 生成

**檔案**：
- `api/services/optimization_output_service.py` (續 — 新增 md 生成)

**輸出格式** (SPEC §11.4)：
```markdown
# Optimization Report — {task_id}
## Summary
## Best Parameters
## Performance
## Decision
## Warnings
## Next Steps
```

**驗收條件**：
- [x] `ai_readable_report.md` 包含所有 Section
- [x] RECOMMENDED_ACTION 根據 metrics 自動判斷
- [x] 每個優化任務完成後自動生成

**Checklist**：
- [x] MD 報告模板
- [x] RECOMMENDED_ACTION 邏輯
- [x] 自動生成觸發（任務完成時）

---

### Task 4.5.3：HTML Report + Export API

**檔案**：
- `templates/optimization_report.html` (新建 — Jinja2 模板)
- `api/routes/` (修改 — export 路由)

**Export API** (SPEC §11.6)：
```
POST /api/v1/optimization/{task_type}/{task_id}/export
Body: { "format": "json" | "csv" | "html" | "charts" | "full" }
```

**驗收條件**：
- [x] HTML Report 含績效表格、參數區塊、約束檢查、equity curve 圖表
- [x] Export API 5 種格式全支援

**Checklist**：
- [x] Jinja2 HTML 模板
- [x] Export API endpoint
- [x] JSON/CSV/HTML/Charts/Full 格式

### 驗證檢查點
- PASS（成功路徑）：每個完成任務均可在 `optimization_results/{execution|hyperparameter}/{task_id}/` 產生 `summary.json`、必要 CSV，且 `ai_readable_report.md` 含既定 Section。
- PASS（失敗/邊界）：當輸出資料不足（如無交易或無 completed trial）時，仍可產生結構完整檔案（空集合/預設欄位），`export` API 不因缺欄位而中斷。

---

## Phase 4.6：測試 100% 覆蓋率

### Task 4.6.1：整合測試（~20 tests）

**檔案**：
- `tests/integration/test_e2e_execution.py` (新建 — 5 tests)
- `tests/integration/test_e2e_hyperparameter.py` (新建 — 5 tests)
- `tests/integration/test_optuna_checkpoint_recovery.py` (新建 — 5 tests)
- `tests/integration/test_optuna_multi_objective.py` (新建 — 5 tests)

**端到端測試模式** (SPEC §12.3)：
```python
@pytest.mark.asyncio
async def test_execution_optimization_end_to_end(mock_prices, mock_proba, mock_atr):
    backtest_engine = create_backtest_engine(commission=0.001)
    objective = StrategyBacktestObjective(
        backtest_engine=backtest_engine, prices=mock_prices,
        predicted_proba=mock_proba, atr_values=mock_atr,
        target_metric='expectancy',
        constraints={'max_drawdown': -0.30, 'min_win_rate': 0.40, 'min_trades': 5}
    )
    optimizer = create_optuna_optimizer(objective=objective, n_trials=20)
    result = await optimizer.optimize()
    assert result is not None
    assert 0.5 <= result.best_params['entry_threshold'] <= 0.95
```

**驗收條件**：
- [x] 20 整合測試全通過
- [x] E2E execution: API → Optuna → BacktestResult → JSON/CSV
- [x] E2E hyperparameter: API → Optuna → ModelResult → JSON
- [x] Checkpoint: 中斷 → 載入 → 繼續
- [x] Multi-objective: Pareto 前沿 + 膝點推薦

**Checklist**：
- [x] 5 execution E2E tests
- [x] 5 hyperparameter E2E tests
- [x] 5 checkpoint recovery tests
- [x] 5 multi-objective tests

---

### Task 4.6.2：Decoupling 驗證

**檔案**：
- `scripts/check_decoupling_phase4.sh` (新建 — SPEC §12.5)

**驗證內容**：
```bash
# Rule 1: momentum/Strategy/ → api/ = 0
grep -rn "from api\." momentum/Strategy/ | wc -l

# Rule 1: momentum/Optimization/ → api/ = 0
grep -rn "from api\." momentum/Optimization/ | wc -l

# Rule 2: Protocol usage in strategy_backtest.py
grep -c "IBacktestEngine\|IPositionSizer" momentum/Optimization/objectives/strategy_backtest.py

# Rule 3: Factory functions in factories.py
grep -c "create_backtest_engine\|create_position_sizer" momentum/factories.py

# Rule 6: Independent test execution
pytest tests/momentum/Strategy/ --no-header -q
```

**驗收條件**：
- [x] Rule 1 違規 = 0
- [x] Rule 2 有 Protocol 引用
- [x] Rule 3 有 Factory 函式
- [x] Rule 6 獨立測試通過

**驗證命令**：
```bash
chmod +x scripts/check_decoupling_phase4.sh && ./scripts/check_decoupling_phase4.sh
```

---

### Task 4.6.3：性能驗收

**目標** (SPEC §12.4)：

| 指標 | 目標 | 驗證方式 |
|------|------|---------|
| 回測速度 (1000 trades) | < 0.1s | timeit benchmark |
| 指標計算 (12 指標) | < 0.01s | timeit benchmark |
| Optuna 100 trials (策略) | < 5 分鐘 | E2E 計時 |
| 記憶體峰值 | < 4GB | memory_profiler |
| 指標精度 | < 1% vs QuantStats | 交叉驗證 |

**驗證命令**：
```bash
pytest tests/momentum/Strategy/test_vectorized_backtest.py -k "benchmark" -v
```

---

### Task 4.6.4：覆蓋率驗證

**驗證命令** (SPEC §12.6)：
```bash
pytest tests/momentum/Strategy/ tests/momentum/Optimization/ \
  --cov=momentum.Strategy --cov=momentum.Optimization.objectives \
  --cov-report=html --cov-report=term --cov-fail-under=100
```

**測試統計摘要** (SPEC §12.7)：

| 測試類別 | 測試數 | 覆蓋目標 |
|---------|-------|---------|
| VectorizedBacktest 單元 | 25 | 100% |
| PerformanceMetrics 單元 | 50 | 100% |
| PositionSizer 單元 | 20 | 100% |
| RiskManager 單元 | 15 | 100% |
| StrategyBacktestObjective 單元 | 20 | 100% |
| ModelHyperparamObjective 單元 | 15 | 100% |
| 整合測試 | 20 | — |
| **合計** | **~165** | **100%** |

### 驗證檢查點
- PASS（成功路徑）：`tests/momentum/Strategy/`、`tests/momentum/Optimization/`、`tests/integration/` 皆通過，且 `--cov-fail-under=100` 達標。
- PASS（失敗/邊界）：Decoupling 腳本在存在違規 import 時可回報非 0 結束碼；性能 benchmark 未達門檻時可被測試或檢查流程識別為未通過。

---

## Phase 4.7：文件更新

### Task 4.7.1：更新 ARCHITECTURE.md

**修改內容**：
- 新增 `momentum/Strategy/` Domain 描述
- 新增 `IBacktestEngine`, `IPositionSizer` Protocol
- 新增 `create_backtest_engine()`, `create_position_sizer()` Factory
- 更新 Domain 依賴圖

**Checklist**：
- [ ] Strategy Domain 描述
- [ ] Protocol 清單更新
- [ ] Factory 清單更新
- [ ] 依賴圖更新

---

### Task 4.7.2：更新 API_SPECIFICATION.md

**修改內容**：
- 新增 `/api/v1/optimization/hyperparameter` 端點
- 新增 `/api/v1/optimization/execution` 端點
- 新增 `/api/v1/optimization/{task_id}/result` 端點
- 新增 `/api/v1/optimization/{task_type}/{task_id}/export` 端點
- 新增 WebSocket 3 事件

**Checklist**：
- [ ] 4 個新端點文件
- [ ] WebSocket 事件文件
- [ ] Request/Response 範例

### 驗證檢查點
- PASS（成功路徑）：`ARCHITECTURE.md` 與 `API_SPECIFICATION.md` 均反映本 PLAN 已定義的新增 Domain、Protocol、Factory、端點與事件。
- PASS（失敗/邊界）：文件中的路徑、端點、欄位命名與 PLAN 不一致時，可在審閱中直接定位差異並修正，不保留模糊描述。

---

## 執行順序總覽

```
Phase 4.0 (架構準備)
  4.0.1 Protocol 擴展 (IBacktestEngine, IPositionSizer)
  4.0.2 Factory 擴展 (create_backtest_engine, create_position_sizer)
  4.0.3 optimization_config.yaml 建立
  4.0.4 封存 SignalDensityObjective
  4.0.5 Strategy Domain 骨架
  4.0.6 MomentumConfig 擴展

Phase 4.1 (Strategy Domain 核心)
  4.1.1 Trade + BacktestResult dataclass
  4.1.2 VectorizedBacktest 輸入驗證 + 骨架
  4.1.3 信號生成 + 冷卻期 (向量化)
  4.1.4 交易執行 + SL/TP/Trailing Stop
  4.1.5 PerformanceMetrics 12+ 指標
  4.1.6 PositionSizer 3 種方法
  4.1.7 RiskManager SL/TP/Trailing
  4.1.8 單元測試 (~110 tests)

Phase 4.2 (Objective 增強)
  4.2.1 StrategyBacktestObjective 建構子重構 (Breaking Change)
  4.2.2 StrategyBacktestObjective 搜索空間 + 評估增強
  4.2.3 ModelHyperparamObjective 過擬合檢測 + 搜索空間驗證
  4.2.4 Objective 增強測試 (~35 tests)

Phase 4.3 (API + Service)
  4.3.1 Pydantic Request/Response Models
  4.3.2 API 路由
  4.3.3 OptimizationTaskService 增強

Phase 4.4 (前端 UI)
  4.4.1 TypeScript 型別定義
  4.4.2 超參數優化頁面 (配置 + 結果)
  4.4.3 策略執行優化頁面 (配置 + 結果)
  4.4.4 共用元件 + Store + Hooks

Phase 4.5 (輸出格式)
  4.5.1 JSON + CSV 輸出生成
  4.5.2 AI-Readable Report 生成
  4.5.3 HTML Report + Export API

Phase 4.6 (測試 100%)
  4.6.1 整合測試 (~20 tests)
  4.6.2 Decoupling 驗證
  4.6.3 性能驗收
  4.6.4 覆蓋率驗證

Phase 4.7 (文件更新)
  4.7.1 ARCHITECTURE.md 更新
  4.7.2 API_SPECIFICATION.md 更新
```

**關鍵依賴圖**：
```
4.0.1 (Protocol) ──→ 4.0.2 (Factory) ──→ 4.0.5 (骨架)
4.0.3 (Config) ──→ 4.1.* (Strategy Domain)
4.0.4 (封存) ──→ 獨立
4.1.* ──→ 4.2.* (Objective)
4.2.* ──→ 4.3.* (API) ──→ 4.4.* (Frontend)
4.2.* ──→ 4.5.* (輸出)
ALL ──→ 4.6.* (測試)
4.6.* ──→ 4.7.* (文件)
```

---

## AI Agent 每 Task 完成後驗證命令

| Task | 驗證命令 |
|------|---------|
| 4.0.1 | `python -c "from momentum.core.protocols import IBacktestEngine, IPositionSizer; print('OK')"` |
| 4.0.2 | `python -c "from momentum.factories import create_backtest_engine, create_position_sizer; print('OK')"` |
| 4.0.3 | `python -c "import yaml; yaml.safe_load(open('config/optimization_config.yaml')); print('OK')"` |
| 4.0.4 | `test ! -f momentum/Optimization/objectives/signal_density.py && echo 'OK'` |
| 4.0.5 | `ls momentum/Strategy/*.py \| wc -l` (期望 5) |
| 4.0.6 | `python -c "from momentum.core.config import MomentumConfig; MomentumConfig.load_optimization_config(); print('OK')"` |
| 4.1.1-4.1.7 | `python -c "from momentum.Strategy import VectorizedBacktest, PerformanceMetrics, KellyPositionSizer, RiskManager; print('OK')"` |
| 4.1.8 | `pytest tests/momentum/Strategy/ -v --tb=short --cov=momentum.Strategy --cov-fail-under=100` |
| 4.2.1-4.2.3 | `pytest tests/ -k "strategy_backtest or model_hyperparam" -v --tb=short` |
| 4.2.4 | `pytest tests/momentum/Optimization/ -v --tb=short --cov=momentum.Optimization.objectives --cov-fail-under=100` |
| 4.3.* | `python run_api.py & sleep 3; curl -s http://localhost:8000/docs \| head -1; pkill -f run_api.py` |
| 4.4.* | `cd frontend && npm run build` |
| 4.5.* | `pytest tests/ -k "output_service" -v --tb=short` |
| 4.6.1 | `pytest tests/integration/ -v --tb=short` |
| 4.6.2 | `./scripts/check_decoupling_phase4.sh` |
| 4.6.4 | `pytest tests/momentum/Strategy/ tests/momentum/Optimization/ --cov=momentum.Strategy --cov=momentum.Optimization.objectives --cov-fail-under=100` |

---

## 邊界條件全覆蓋矩陣

| 模組 | 邊界條件 ID | 數量 | 對應 Task |
|------|------------|------|----------|
| VectorizedBacktest | BC-VB-01 ~ BC-VB-14 | 14 | 4.1.2, 4.1.3, 4.1.4, 4.1.8 |
| PerformanceMetrics | BC-PM-01 ~ BC-PM-13 | 13 | 4.1.5, 4.1.8 |
| PositionSizer (Kelly) | BC-KL-01 ~ BC-KL-10 | 10 | 4.1.6, 4.1.8 |
| PositionSizer (ProbScaled) | BC-PS-01 ~ BC-PS-05 | 5 | 4.1.6, 4.1.8 |
| RiskManager | BC-RM-01 ~ BC-RM-06 | 6 | 4.1.7, 4.1.8 |
| StrategyBacktestObjective | BC-SO-01 ~ BC-SO-05 | 5 | 4.2.1, 4.2.2, 4.2.4 |
| ModelHyperparamObjective | BC-HO-01 ~ BC-HO-07 | 7 | 4.2.3, 4.2.4 |
| **合計** | | **60** | |

---

## 風險對照表（SPEC §14 對應）

| 風險 | 說明 | 緩解措施 | 對應 Task |
|------|------|---------|----------|
| R1 | 向量化回測精度不足 | Phase 5 事件驅動對比驗證 | 4.1.4 |
| R2 | Kelly 過度槓桿 | Half-Kelly + max_position_size 上限 | 4.1.6 |
| R3 | 搜索空間收斂慢 | TPE sampler + step 粒度限制 + 100 trials 先驗證 | 4.0.3 |
| R4 | 回測過擬合 | min_trades 約束 + SQN 含樣本修正 + Phase 5 Walk-Forward | 4.2.2 |
| R5 | 記憶體爆炸 | 限制 ≤ 2000 bars + 分批 GC | 4.1.4 |
| R6 | Breaking Change 破壞相容 | 一次性修改 3 呼叫點 + 保持 evaluate() 簽名 | 4.2.1 |
| R7 | 交易成本假設不合理 | 可配置 commission/slippage | 4.0.3 |
| AR1 | Strategy Domain 設計不當 | 遵循現有 Domain 模式 + Protocol 先行 | 4.0.1 |
| AR2 | Phase 3→4 格式不匹配 | 數據契約預定義 (SPEC §15.1) | 4.1.2 |
| AR3 | 前後端型別不一致 | TypeScript types 手動同步 | 4.4.1 |

---

## 關鍵里程碑

| 里程碑 | Phase | 驗收標準 |
|--------|-------|---------|
| **M1**: 回測引擎可用 | 4.1 | VectorizedBacktest 通過 25 個測試（含 14 邊界） |
| **M2**: 指標精確 | 4.1 | PerformanceMetrics 與 QuantStats 誤差 < 1% |
| **M3**: 優化可運行 | 4.2 | Optuna 100 trials < 5 分鐘 |
| **M4**: API 可用 | 4.3 | POST → 啟動 → WS 進度 → GET 結果 |
| **M5**: 前端可用 | 4.4 | 雙頁面可配置、啟動、查看結果 |
| **M6**: 輸出完整 | 4.5 | JSON + CSV + AI-Readable MD 可正常生成 |
| **M7**: 覆蓋率達標 | 4.6 | `--cov-fail-under=100` 通過 |

---

## Appendix A：Phase 3 → Phase 4 數據契約

**輸入檔案**: `model_predictions_{task_id}.csv`

| 欄位 | 型別 | 必須 | 說明 |
|------|------|------|------|
| `timestamp` | datetime | ✅ | K 線時間戳（單調遞增） |
| `open` | float > 0 | ✅ | 開盤價 |
| `high` | float > 0 | ✅ | 最高價 |
| `low` | float > 0 | ✅ | 最低價 |
| `close` | float > 0 | ✅ | 收盤價 |
| `predicted_proba_lgb` | float [0, 1] | ✅ | LightGBM 預測機率 |
| `predicted_proba_xgb` | float [0, 1] | ⬜ | XGBoost 預測機率（可選） |
| `atr` | float ≥ 0 | ✅ | ATR 值（允許 NaN，回測時 fallback） |

**驗證規則**：
1. `timestamp` 單調遞增
2. OHLC > 0, high ≥ max(open, close), low ≤ min(open, close)
3. `predicted_proba` ∈ [0, 1]
4. 最少 10 行數據

---

## Appendix B：新增/修改檔案完整清單

### 新增檔案 (41)

| # | 檔案路徑 | 說明 |
|---|---------|------|
| 1 | `momentum/Strategy/__init__.py` | Domain 入口 |
| 2 | `momentum/Strategy/vectorized_backtest.py` | 回測引擎 |
| 3 | `momentum/Strategy/performance_metrics.py` | 績效指標 |
| 4 | `momentum/Strategy/position_sizing.py` | 倉位管理 |
| 5 | `momentum/Strategy/risk_manager.py` | 風險管理 |
| 6 | `config/optimization_config.yaml` | 優化配置 |
| 7 | `scripts/archive_signal_density.sh` | 封存腳本 |
| 8 | `scripts/check_decoupling_phase4.sh` | 解耦驗證 |
| 9 | `api/routes/hyperparameter_optimization.py` | 超參數路由 |
| 10 | `api/routes/execution_optimization.py` | 執行路由 |
| 11 | `api/models/optimization_models.py` | Request/Response Models |
| 12 | `api/services/optimization_output_service.py` | 輸出服務 |
| 13 | `templates/optimization_report.html` | HTML 報告模板 |
| 14 | `frontend/src/app/optimization-hyperparameter/page.tsx` | 超參數配置頁 |
| 15 | `frontend/src/app/optimization-hyperparameter/result/[taskId]/page.tsx` | 超參數結果頁 |
| 16 | `frontend/src/app/optimization-execution/page.tsx` | 執行配置頁 |
| 17 | `frontend/src/app/optimization-execution/result/[taskId]/page.tsx` | 執行結果頁 |
| 18 | `frontend/src/components/optimization/common/OptunaProgressBar.tsx` | 進度條 |
| 19 | `frontend/src/components/optimization/common/ParameterRangeSlider.tsx` | 參數滑桿 |
| 20 | `frontend/src/components/optimization/common/SamplerSelector.tsx` | 採樣器選擇 |
| 21 | `frontend/src/components/optimization/common/TrialComparisonTable.tsx` | Trial 表格 |
| 22 | `frontend/src/components/optimization/hyperparameter/HyperparamConfigForm.tsx` | 超參數表單 |
| 23 | `frontend/src/components/optimization/hyperparameter/ParameterImportanceChart.tsx` | 參數重要性 |
| 24 | `frontend/src/components/optimization/hyperparameter/OverfittingCheckChart.tsx` | 過擬合圖 |
| 25 | `frontend/src/components/optimization/execution/ExecutionConfigForm.tsx` | 執行表單 |
| 26 | `frontend/src/components/optimization/execution/EquityCurveChart.tsx` | 權益曲線 |
| 27 | `frontend/src/components/optimization/execution/DrawdownChart.tsx` | 回撤圖 |
| 28 | `frontend/src/components/optimization/execution/ParetoFrontChart.tsx` | Pareto 前沿圖 |
| 29 | `frontend/src/lib/types/optimization.ts` | 優化 TypeScript 型別 |
| 30 | `tests/momentum/Strategy/__init__.py` | 測試 init |
| 31 | `tests/momentum/Strategy/test_vectorized_backtest.py` | 回測測試 (25) |
| 32 | `tests/momentum/Strategy/test_performance_metrics.py` | 指標測試 (50) |
| 33 | `tests/momentum/Strategy/test_position_sizing.py` | 倉位測試 (20) |
| 34 | `tests/momentum/Strategy/test_risk_manager.py` | 風管測試 (15) |
| 35 | `tests/momentum/Optimization/__init__.py` | 測試 init |
| 36 | `tests/momentum/Optimization/test_strategy_backtest_enhanced.py` | Objective 測試 (20) |
| 37 | `tests/momentum/Optimization/test_model_hyperparam_enhanced.py` | Hyperparam 測試 (15) |
| 38 | `tests/integration/test_e2e_execution.py` | E2E 執行 (5) |
| 39 | `tests/integration/test_e2e_hyperparameter.py` | E2E 超參 (5) |
| 40 | `tests/integration/test_optuna_checkpoint_recovery.py` | Checkpoint (5) |
| 41 | `tests/integration/test_optuna_multi_objective.py` | 多目標 (5) |

### 修改檔案 (9)

| # | 檔案路徑 | 修改內容 |
|---|---------|---------|
| 1 | `momentum/core/protocols.py` | +IBacktestEngine, +IPositionSizer |
| 2 | `momentum/core/config.py` | +load_optimization_config() |
| 3 | `momentum/factories.py` | +create_backtest_engine(), +create_position_sizer() |
| 4 | `momentum/Optimization/objectives/strategy_backtest.py` | 建構子重構 + 搜索空間增強 |
| 5 | `momentum/Optimization/objectives/model_hyperparam.py` | 過擬合檢測 + 搜索空間驗證 |
| 6 | `momentum/Optimization/objectives/__init__.py` | 移除 signal_density import |
| 7 | `api/services/optimization_task_service.py` | 增強建構邏輯 + WS 事件 |
| 8 | `api/main.py` | 路由註冊 |
| 9 | `frontend/src/store/optimizationStore.ts` | +hyperparameter/execution 狀態 |

### 封存檔案 (1)

| 檔案 | 目的地 |
|------|--------|
| `momentum/Optimization/objectives/signal_density.py` | `archived/momentum/Optimization/objectives/signal_density.py` |

---

## Appendix C：估計程式碼量

| 區域 | 新增 | 修改 | LOC |
|------|------|------|-----|
| `momentum/Strategy/` | 4 files | — | ~800 |
| `momentum/Optimization/objectives/` | — | 2 files | ~300 |
| `momentum/core/` | — | 2 files | ~70 |
| `momentum/factories.py` | — | 1 file | ~40 |
| `api/routes/` | 2 files | — | ~200 |
| `api/models/` | 1 file | — | ~100 |
| `api/services/` | 1 file | 1 file | ~200 |
| `config/` | 1 file | — | ~60 |
| `scripts/` | 2 files | — | ~50 |
| **後端小計** | | | **~1820** |
| `frontend/` | ~15 files | ~3 files | ~2500 |
| **前端小計** | | | **~2500** |
| `tests/` | ~12 files | — | ~1500 |
| **測試小計** | | | **~1500** |
| **總計** | **41 new** | **9 mod** | **~5820** |

---

## 執行原則

> **寧可小步多次，不可大步一次失敗。**

1. 每個 Task 應可獨立 commit、獨立 rollback
2. 每個 Phase 完成後執行該 Phase 驗證檢查點再進入下一 Phase
3. Phase 4.1.8 (單元測試) 完成後必須達到 `--cov-fail-under=100`
4. Breaking Change (Task 4.2.1) 必須同步修改所有 3 個呼叫點
5. 前端 TypeScript 編譯必須通過 (`npm run build`)
6. 所有 `momentum/` 檔案不得 import `api.*`

<!-- STATUS: CONVERGED / READY TO FREEZE -->

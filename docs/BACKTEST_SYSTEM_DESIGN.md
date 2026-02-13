# 回測系統架構設計 (Backtest System Design)

> **Authority**: 本文件定義回測系統的完整架構設計  
> **Version**: 1.0  
> **Created**: 2026-02-13  
> **Status**: Design Document（待實現）

---

## 📋 目錄

1. [系統定位](#系統定位)
2. [架構設計](#架構設計)
3. [模組規劃](#模組規劃)
4. [資料流設計](#資料流設計)
5. [性能設計](#性能設計)
6. [介面定義](#介面定義)
7. [實現路徑](#實現路徑)

---

## 系統定位

### 回測系統在整體架構中的位置

```
┌─────────────────────────────────────────────────────┐
│              量化研究工作平台                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [1] 資料層 (DataExtraction)                        │
│      ↓ K線數據、市場數據                             │
│                                                     │
│  [2] 案例搜尋 (CaseSearch)                          │
│      ↓ 觸發案例、Pattern 候選                        │
│                                                     │
│  [3] 特徵工程 (FeatureEngineering)                  │
│      ↓ 6514 特徵、IC 篩選                           │
│                                                     │
│  [4] 機器學習 (Analysis)                            │
│      ↓ XGBoost 預測、SHAP 解釋                      │
│                                                     │
│  [5] 參數優化 (Optimization)                        │
│      ↓ Optuna 最佳參數組合                          │
│                                                     │
│  [6] ⭐ 回測驗證 (Backtest) ⭐ ← 本文件              │
│      ↓ 歷史模擬、績效評估                           │
│                                                     │
│  [7] 視覺化 (Frontend)                              │
│      → 圖表展示、報告生成                            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 核心價值

**回測系統是策略驗證的最後一道防線**：

1. **驗證策略有效性**：在歷史數據上模擬交易，評估策略是否真的賺錢
2. **評估風險**：計算最大回撤、夏普比率、勝率等風險指標
3. **發現過擬合**：檢驗策略是否只在訓練期有效，測試期失效
4. **優化入場離場**：測試不同的入場/離場條件，找出最佳配置

### 與傳統回測系統的差異

| 特性 | 傳統回測系統 | 本系統回測 |
|------|-------------|-----------|
| **輸入** | 手動編寫策略邏輯 | ML 模型預測信號 + Optuna 優化參數 |
| **目的** | 驗證已知策略 | 驗證 AI 發現的 Pattern |
| **複雜度** | 簡單邏輯（if-else） | 複雜特徵（6514 維） + XGBoost 預測 |
| **優化方式** | 網格搜索參數 | Optuna 貝葉斯優化 |
| **結果** | 單一策略報告 | 多策略對比、SHAP 解釋 |

---

## 架構設計

### 解耦架構原則

遵循 **REFACTOR_ARCHITECTURE_V4** 的 7 條規則：

```python
# ✅ Rule 1: momentum/ 不 import api/
# ✅ Rule 2: 跨 Domain 使用 Protocol 注入
# ✅ Rule 3: 使用 Factory 創建物件
```

### 模組目錄結構

```
momentum/Backtest/                    # 新增 Domain
├── __init__.py
├── backtest_engine.py                # 核心回測引擎
├── position_manager.py               # 部位管理（開倉、平倉、加減碼）
├── trade_executor.py                 # 交易執行模擬
├── performance_calculator.py         # 績效指標計算
├── risk_analyzer.py                  # 風險分析
├── report_generator.py               # 報告生成
├── vectorized_backtest.py            # 向量化回測（性能優化版）
└── types.py                          # 類型定義（Trade, Position, BacktestResult）

api/services/
└── backtest_service.py               # 回測任務服務

api/routes/
└── backtest.py                       # REST API 路由

api/models/
└── backtest_models.py                # Pydantic Models

frontend/src/app/backtest/
└── page.tsx                          # 回測結果頁面

tests/momentum/Backtest/
├── test_backtest_engine.py
├── test_position_manager.py
└── test_performance_calculator.py
```

### Protocol 定義

**添加到 `momentum/core/protocols.py`**：

```python
from typing import Protocol, Dict, List
import pandas as pd

class IBacktestEngine(Protocol):
    """回測引擎介面"""
    
    def run_backtest(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        strategy_params: Dict,
        initial_capital: float = 100000.0
    ) -> Dict:
        """
        執行回測
        
        Parameters:
        -----------
        symbol : str
            交易標的（例如：BTCUSDT）
        timeframe : str
            K線週期（例如：12h, 1d）
        start_date : str
            回測開始日期（ISO 8601）
        end_date : str
            回測結束日期（ISO 8601）
        strategy_params : Dict
            策略參數（例如：{"rsi_threshold": 30, "stop_loss_pct": 0.05}）
        initial_capital : float
            初始資金（預設 10 萬）
            
        Returns:
        --------
        Dict
            回測結果，包含：
            - trades: List[Dict] 交易記錄
            - equity_curve: List[Dict] 權益曲線
            - metrics: Dict 績效指標
            - risk_analysis: Dict 風險分析
        """
        ...

class IPositionManager(Protocol):
    """部位管理介面"""
    
    def open_position(
        self,
        timestamp: int,
        price: float,
        size: float,
        direction: str
    ) -> Dict:
        """開倉"""
        ...
    
    def close_position(
        self,
        timestamp: int,
        price: float
    ) -> Dict:
        """平倉"""
        ...
    
    def get_current_position(self) -> Dict:
        """取得當前持倉"""
        ...

class IPerformanceCalculator(Protocol):
    """績效計算器介面"""
    
    def calculate_metrics(self, trades: List[Dict], equity_curve: List[Dict]) -> Dict:
        """
        計算績效指標
        
        Returns:
        --------
        Dict
            - total_return: float 總報酬率
            - sharpe_ratio: float 夏普比率
            - max_drawdown: float 最大回撤
            - win_rate: float 勝率
            - profit_factor: float 獲利因子
            - avg_win: float 平均獲利
            - avg_loss: float 平均虧損
            - total_trades: int 總交易次數
        """
        ...
```

### Factory 函數

**添加到 `momentum/factories.py`**：

```python
from momentum.Backtest.backtest_engine import BacktestEngine
from momentum.Backtest.position_manager import PositionManager
from momentum.Backtest.performance_calculator import PerformanceCalculator
from momentum.core.protocols import IBacktestEngine, IPositionManager, IPerformanceCalculator

def create_backtest_engine() -> IBacktestEngine:
    """創建回測引擎實例（使用 Protocol 注入）"""
    kline_reader = create_kline_storage_manager()
    position_manager = create_position_manager()
    performance_calculator = create_performance_calculator()
    
    return BacktestEngine(
        kline_reader=kline_reader,
        position_manager=position_manager,
        performance_calculator=performance_calculator
    )

def create_position_manager() -> IPositionManager:
    """創建部位管理器"""
    return PositionManager()

def create_performance_calculator() -> IPerformanceCalculator:
    """創建績效計算器"""
    return PerformanceCalculator()
```

---

## 模組規劃

### 1. BacktestEngine（核心引擎）

**職責**：
- 讀取 K 線數據
- 逐 bar 模擬交易
- 管理部位開平
- 計算績效指標
- 生成回測報告

**類別設計**：

```python
# momentum/Backtest/backtest_engine.py

from typing import Dict, List
import pandas as pd
from momentum.core.protocols import IKlineReader, IPositionManager, IPerformanceCalculator
from momentum.core.logging import get_logger

logger = get_logger(__name__)

class BacktestEngine:
    """
    回測引擎
    
    使用向量化計算優化性能，支援多種策略類型
    """
    
    def __init__(
        self,
        kline_reader: IKlineReader,
        position_manager: IPositionManager,
        performance_calculator: IPerformanceCalculator
    ):
        """
        初始化回測引擎
        
        Parameters:
        -----------
        kline_reader : IKlineReader
            K線數據讀取器（Protocol 注入）
        position_manager : IPositionManager
            部位管理器
        performance_calculator : IPerformanceCalculator
            績效計算器
        """
        self.kline_reader = kline_reader
        self.position_manager = position_manager
        self.performance_calculator = performance_calculator
        
    def run_backtest(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        strategy_params: Dict,
        initial_capital: float = 100000.0
    ) -> Dict:
        """
        執行回測（向量化版本）
        
        流程：
        1. 讀取 K 線數據
        2. 生成交易信號（根據 strategy_params）
        3. 模擬執行交易
        4. 計算績效指標
        5. 返回結果
        """
        logger.info(f"開始回測: {symbol} {timeframe}, 期間: {start_date} ~ {end_date}")
        
        # Step 1: 讀取 K 線數據
        klines = self._load_klines(symbol, timeframe, start_date, end_date)
        logger.info(f"讀取 K 線數據: {len(klines)} 根")
        
        # Step 2: 生成交易信號
        signals = self._generate_signals(klines, strategy_params)
        logger.info(f"生成交易信號: {signals['buy'].sum()} 買入, {signals['sell'].sum()} 賣出")
        
        # Step 3: 模擬執行交易（向量化）
        trades, equity_curve = self._execute_trades_vectorized(
            klines, signals, initial_capital
        )
        logger.info(f"執行交易: 共 {len(trades)} 筆交易")
        
        # Step 4: 計算績效指標
        metrics = self.performance_calculator.calculate_metrics(trades, equity_curve)
        logger.info(f"總報酬率: {metrics['total_return']:.2%}, 夏普比率: {metrics['sharpe_ratio']:.2f}")
        
        # Step 5: 風險分析
        risk_analysis = self._analyze_risk(trades, equity_curve)
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": initial_capital,
            "trades": trades,
            "equity_curve": equity_curve,
            "metrics": metrics,
            "risk_analysis": risk_analysis
        }
    
    def _load_klines(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> pd.DataFrame:
        """讀取 K 線數據（透過 Protocol）"""
        return self.kline_reader.read_klines(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
    
    def _generate_signals(self, klines: pd.DataFrame, strategy_params: Dict) -> pd.DataFrame:
        """
        生成交易信號
        
        支援多種信號類型：
        1. RSI 超買超賣
        2. 均線交叉
        3. ML 模型預測（XGBoost）
        4. Pattern 觸發
        """
        # 這裡使用簡單 RSI 策略作為範例
        # 實際應該根據 strategy_params['signal_type'] 動態選擇策略
        
        signals = pd.DataFrame(index=klines.index)
        signals['buy'] = (klines['rsi'] < strategy_params.get('rsi_buy', 30))
        signals['sell'] = (klines['rsi'] > strategy_params.get('rsi_sell', 70))
        
        return signals
    
    def _execute_trades_vectorized(
        self,
        klines: pd.DataFrame,
        signals: pd.DataFrame,
        initial_capital: float
    ) -> tuple:
        """
        向量化執行交易（性能優化）
        
        使用 pandas 向量化操作，避免 Python 循環
        """
        # 向量化計算（待實現）
        # 這裡使用簡化版本作為範例
        trades = []
        equity_curve = []
        
        capital = initial_capital
        position = None
        
        for i in range(len(klines)):
            timestamp = klines.index[i]
            price = klines['close'].iloc[i]
            
            # 檢查信號
            if signals['buy'].iloc[i] and position is None:
                # 開多倉
                size = capital * 0.95 / price  # 使用 95% 資金
                position = {
                    'entry_time': timestamp,
                    'entry_price': price,
                    'size': size,
                    'direction': 'long'
                }
                logger.debug(f"開多倉: {timestamp}, 價格: {price:.2f}, 數量: {size:.4f}")
                
            elif signals['sell'].iloc[i] and position is not None:
                # 平倉
                pnl = (price - position['entry_price']) * position['size']
                capital += pnl
                
                trade = {
                    'entry_time': position['entry_time'],
                    'exit_time': timestamp,
                    'entry_price': position['entry_price'],
                    'exit_price': price,
                    'size': position['size'],
                    'pnl': pnl,
                    'return': pnl / (position['entry_price'] * position['size'])
                }
                trades.append(trade)
                position = None
                logger.debug(f"平倉: {timestamp}, 價格: {price:.2f}, PnL: {pnl:.2f}")
            
            # 記錄權益曲線
            current_value = capital
            if position is not None:
                current_value += (price - position['entry_price']) * position['size']
            
            equity_curve.append({
                'timestamp': timestamp,
                'equity': current_value
            })
        
        return trades, equity_curve
    
    def _analyze_risk(self, trades: List[Dict], equity_curve: List[Dict]) -> Dict:
        """風險分析"""
        # 計算風險指標（待實現）
        return {
            "var_95": 0.0,  # 95% VaR
            "cvar_95": 0.0,  # 95% CVaR
            "kelly_criterion": 0.0  # 凱利公式建議倉位
        }
```

### 2. PositionManager（部位管理）

**職責**：
- 管理開倉/平倉邏輯
- 追蹤當前持倉
- 處理加減碼
- 止損止盈檢查

**類別設計**：

```python
# momentum/Backtest/position_manager.py

from typing import Dict, Optional
from momentum.core.logging import get_logger

logger = get_logger(__name__)

class PositionManager:
    """
    部位管理器
    
    負責管理交易部位的生命週期
    """
    
    def __init__(self):
        self.current_position: Optional[Dict] = None
        self.position_history: list = []
        
    def open_position(
        self,
        timestamp: int,
        price: float,
        size: float,
        direction: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict:
        """
        開倉
        
        Parameters:
        -----------
        timestamp : int
            開倉時間戳
        price : float
            開倉價格
        size : float
            開倉數量
        direction : str
            方向（'long' or 'short'）
        stop_loss : float, optional
            止損價格
        take_profit : float, optional
            止盈價格
            
        Returns:
        --------
        Dict
            開倉記錄
        """
        if self.current_position is not None:
            logger.warning(f"已有持倉，無法開新倉: {self.current_position}")
            return None
        
        self.current_position = {
            'entry_time': timestamp,
            'entry_price': price,
            'size': size,
            'direction': direction,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'unrealized_pnl': 0.0
        }
        
        logger.info(f"開倉: {direction} {size:.4f} @ {price:.2f}")
        return self.current_position
    
    def close_position(self, timestamp: int, price: float) -> Dict:
        """
        平倉
        
        Returns:
        --------
        Dict
            平倉記錄（包含 PnL）
        """
        if self.current_position is None:
            logger.warning("無持倉，無法平倉")
            return None
        
        position = self.current_position
        pnl = self._calculate_pnl(position, price)
        
        closed_position = {
            **position,
            'exit_time': timestamp,
            'exit_price': price,
            'pnl': pnl,
            'return': pnl / (position['entry_price'] * position['size'])
        }
        
        self.position_history.append(closed_position)
        self.current_position = None
        
        logger.info(f"平倉: {price:.2f}, PnL: {pnl:.2f}")
        return closed_position
    
    def check_stop_loss_take_profit(self, current_price: float) -> Optional[str]:
        """
        檢查止損止盈
        
        Returns:
        --------
        Optional[str]
            'stop_loss' 或 'take_profit' 或 None
        """
        if self.current_position is None:
            return None
        
        position = self.current_position
        
        if position['direction'] == 'long':
            if position['stop_loss'] and current_price <= position['stop_loss']:
                logger.info(f"觸發止損: {current_price:.2f} <= {position['stop_loss']:.2f}")
                return 'stop_loss'
            if position['take_profit'] and current_price >= position['take_profit']:
                logger.info(f"觸發止盈: {current_price:.2f} >= {position['take_profit']:.2f}")
                return 'take_profit'
        
        elif position['direction'] == 'short':
            if position['stop_loss'] and current_price >= position['stop_loss']:
                logger.info(f"觸發止損: {current_price:.2f} >= {position['stop_loss']:.2f}")
                return 'stop_loss'
            if position['take_profit'] and current_price <= position['take_profit']:
                logger.info(f"觸發止盈: {current_price:.2f} <= {position['take_profit']:.2f}")
                return 'take_profit'
        
        return None
    
    def get_current_position(self) -> Optional[Dict]:
        """取得當前持倉"""
        return self.current_position
    
    def _calculate_pnl(self, position: Dict, exit_price: float) -> float:
        """計算 PnL"""
        if position['direction'] == 'long':
            return (exit_price - position['entry_price']) * position['size']
        else:  # short
            return (position['entry_price'] - exit_price) * position['size']
```

### 3. PerformanceCalculator（績效計算）

**職責**：
- 計算報酬率、夏普比率
- 計算最大回撤
- 計算勝率、獲利因子
- 生成績效摘要

**類別設計**：

```python
# momentum/Backtest/performance_calculator.py

from typing import Dict, List
import pandas as pd
import numpy as np
from momentum.core.logging import get_logger

logger = get_logger(__name__)

class PerformanceCalculator:
    """
    績效計算器
    
    計算各種回測績效指標
    """
    
    def calculate_metrics(self, trades: List[Dict], equity_curve: List[Dict]) -> Dict:
        """
        計算完整的績效指標
        
        Returns:
        --------
        Dict
            包含所有績效指標的字典
        """
        if not trades:
            logger.warning("無交易記錄，返回空績效")
            return self._empty_metrics()
        
        # 轉換為 DataFrame 方便計算
        trades_df = pd.DataFrame(trades)
        equity_df = pd.DataFrame(equity_curve)
        
        metrics = {
            # 報酬相關
            'total_return': self._calculate_total_return(equity_df),
            'annualized_return': self._calculate_annualized_return(equity_df),
            'cagr': self._calculate_cagr(equity_df),
            
            # 風險相關
            'volatility': self._calculate_volatility(equity_df),
            'max_drawdown': self._calculate_max_drawdown(equity_df),
            'max_drawdown_duration': self._calculate_max_drawdown_duration(equity_df),
            
            # 風險調整報酬
            'sharpe_ratio': self._calculate_sharpe_ratio(equity_df),
            'sortino_ratio': self._calculate_sortino_ratio(equity_df),
            'calmar_ratio': self._calculate_calmar_ratio(equity_df),
            
            # 交易相關
            'total_trades': len(trades),
            'win_rate': self._calculate_win_rate(trades_df),
            'profit_factor': self._calculate_profit_factor(trades_df),
            'avg_win': self._calculate_avg_win(trades_df),
            'avg_loss': self._calculate_avg_loss(trades_df),
            'avg_return_per_trade': trades_df['return'].mean(),
            'max_consecutive_wins': self._calculate_max_consecutive_wins(trades_df),
            'max_consecutive_losses': self._calculate_max_consecutive_losses(trades_df),
        }
        
        logger.info(f"績效計算完成: 總報酬 {metrics['total_return']:.2%}, 夏普比率 {metrics['sharpe_ratio']:.2f}")
        return metrics
    
    def _calculate_total_return(self, equity_df: pd.DataFrame) -> float:
        """計算總報酬率"""
        initial_equity = equity_df['equity'].iloc[0]
        final_equity = equity_df['equity'].iloc[-1]
        return (final_equity - initial_equity) / initial_equity
    
    def _calculate_annualized_return(self, equity_df: pd.DataFrame) -> float:
        """計算年化報酬率"""
        total_return = self._calculate_total_return(equity_df)
        days = (equity_df['timestamp'].iloc[-1] - equity_df['timestamp'].iloc[0]).days
        years = days / 365.25
        if years == 0:
            return 0.0
        return (1 + total_return) ** (1 / years) - 1
    
    def _calculate_cagr(self, equity_df: pd.DataFrame) -> float:
        """計算複合年均成長率（CAGR）"""
        return self._calculate_annualized_return(equity_df)
    
    def _calculate_volatility(self, equity_df: pd.DataFrame) -> float:
        """計算波動率（年化）"""
        returns = equity_df['equity'].pct_change().dropna()
        if len(returns) == 0:
            return 0.0
        return returns.std() * np.sqrt(252)  # 假設一年 252 個交易日
    
    def _calculate_max_drawdown(self, equity_df: pd.DataFrame) -> float:
        """計算最大回撤"""
        equity = equity_df['equity']
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        return drawdown.min()
    
    def _calculate_max_drawdown_duration(self, equity_df: pd.DataFrame) -> int:
        """計算最大回撤持續期（天數）"""
        equity = equity_df['equity']
        cummax = equity.cummax()
        drawdown = equity - cummax
        
        # 找出回撤期間
        in_drawdown = drawdown < 0
        drawdown_periods = []
        start = None
        
        for i, is_dd in enumerate(in_drawdown):
            if is_dd and start is None:
                start = i
            elif not is_dd and start is not None:
                drawdown_periods.append(i - start)
                start = None
        
        if start is not None:
            drawdown_periods.append(len(in_drawdown) - start)
        
        return max(drawdown_periods) if drawdown_periods else 0
    
    def _calculate_sharpe_ratio(self, equity_df: pd.DataFrame, risk_free_rate: float = 0.02) -> float:
        """計算夏普比率"""
        returns = equity_df['equity'].pct_change().dropna()
        if len(returns) == 0:
            return 0.0
        excess_return = returns.mean() - risk_free_rate / 252
        return excess_return / returns.std() * np.sqrt(252) if returns.std() > 0 else 0.0
    
    def _calculate_sortino_ratio(self, equity_df: pd.DataFrame, risk_free_rate: float = 0.02) -> float:
        """計算索提諾比率（只考慮下行風險）"""
        returns = equity_df['equity'].pct_change().dropna()
        if len(returns) == 0:
            return 0.0
        excess_return = returns.mean() - risk_free_rate / 252
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 0.0
        return excess_return / downside_std * np.sqrt(252) if downside_std > 0 else 0.0
    
    def _calculate_calmar_ratio(self, equity_df: pd.DataFrame) -> float:
        """計算卡瑪比率（年化報酬 / 最大回撤）"""
        annual_return = self._calculate_annualized_return(equity_df)
        max_dd = abs(self._calculate_max_drawdown(equity_df))
        return annual_return / max_dd if max_dd > 0 else 0.0
    
    def _calculate_win_rate(self, trades_df: pd.DataFrame) -> float:
        """計算勝率"""
        winning_trades = (trades_df['pnl'] > 0).sum()
        return winning_trades / len(trades_df) if len(trades_df) > 0 else 0.0
    
    def _calculate_profit_factor(self, trades_df: pd.DataFrame) -> float:
        """計算獲利因子（總獲利 / 總虧損）"""
        total_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        total_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        return total_profit / total_loss if total_loss > 0 else float('inf')
    
    def _calculate_avg_win(self, trades_df: pd.DataFrame) -> float:
        """計算平均獲利"""
        winning_trades = trades_df[trades_df['pnl'] > 0]
        return winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0.0
    
    def _calculate_avg_loss(self, trades_df: pd.DataFrame) -> float:
        """計算平均虧損"""
        losing_trades = trades_df[trades_df['pnl'] < 0]
        return losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0.0
    
    def _calculate_max_consecutive_wins(self, trades_df: pd.DataFrame) -> int:
        """計算最大連續獲利次數"""
        wins = (trades_df['pnl'] > 0).astype(int)
        return self._max_consecutive(wins)
    
    def _calculate_max_consecutive_losses(self, trades_df: pd.DataFrame) -> int:
        """計算最大連續虧損次數"""
        losses = (trades_df['pnl'] < 0).astype(int)
        return self._max_consecutive(losses)
    
    def _max_consecutive(self, series: pd.Series) -> int:
        """計算最大連續次數（通用函數）"""
        max_count = 0
        current_count = 0
        for value in series:
            if value == 1:
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0
        return max_count
    
    def _empty_metrics(self) -> Dict:
        """返回空績效指標"""
        return {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'total_trades': 0
        }
```

---

## 資料流設計

### 完整資料流

```
┌──────────────────────────────────────────────────────────┐
│ 1. 用戶輸入                                               │
│    - 標的：BTCUSDT                                        │
│    - 週期：12h                                            │
│    - 期間：2024-01-01 ~ 2024-12-31                       │
│    - 策略參數：{"rsi_buy": 30, "rsi_sell": 70}           │
│    - 初始資金：100,000 USDT                              │
└────────────┬─────────────────────────────────────────────┘
             ↓
┌────────────┴─────────────────────────────────────────────┐
│ 2. BacktestEngine.run_backtest()                         │
│    - 讀取 K 線數據（透過 IKlineReader Protocol）          │
│    - 生成交易信號（根據策略參數）                          │
└────────────┬─────────────────────────────────────────────┘
             ↓
┌────────────┴─────────────────────────────────────────────┐
│ 3. 逐 Bar 模擬交易                                        │
│    for each bar in klines:                               │
│        if buy_signal and no_position:                    │
│            PositionManager.open_position()               │
│        if sell_signal and has_position:                  │
│            PositionManager.close_position()              │
│        check_stop_loss_take_profit()                     │
│        update_equity_curve()                             │
└────────────┬─────────────────────────────────────────────┘
             ↓
┌────────────┴─────────────────────────────────────────────┐
│ 4. PerformanceCalculator.calculate_metrics()             │
│    - 計算總報酬率、夏普比率、最大回撤                      │
│    - 計算勝率、獲利因子                                   │
│    - 生成權益曲線                                         │
└────────────┬─────────────────────────────────────────────┘
             ↓
┌────────────┴─────────────────────────────────────────────┐
│ 5. 返回結果                                               │
│    {                                                     │
│        "trades": [...],          # 交易記錄              │
│        "equity_curve": [...],    # 權益曲線              │
│        "metrics": {...},         # 績效指標              │
│        "risk_analysis": {...}    # 風險分析              │
│    }                                                     │
└────────────┬─────────────────────────────────────────────┘
             ↓
┌────────────┴─────────────────────────────────────────────┐
│ 6. 前端展示                                               │
│    - 權益曲線圖表                                         │
│    - 交易記錄表格                                         │
│    - 績效指標面板                                         │
│    - 風險分析報告                                         │
└──────────────────────────────────────────────────────────┘
```

---

## 性能設計

### 向量化計算

**目標**：MacBook M1 上，1 年 12h 週期數據（約 730 根 K 線）回測時間 < 1 秒

**優化策略**：

1. **使用 pandas 向量化操作**（避免 Python 循環）：
   ```python
   # ❌ 慢（Python 循環）
   for i in range(len(df)):
       if df['rsi'].iloc[i] < 30:
           signals.append('buy')
   
   # ✅ 快（向量化）
   signals = (df['rsi'] < 30).astype(int)
   ```

2. **Numba JIT 編譯**（針對無法向量化的邏輯）：
   ```python
   from numba import jit
   
   @jit(nopython=True)
   def calculate_equity_curve(prices, signals, initial_capital):
       # 編譯成機器碼，速度提升 10-100 倍
       ...
   ```

3. **並行回測**（多標的同時回測）：
   ```python
   import asyncio
   
   async def batch_backtest(symbols: List[str]):
       tasks = [backtest_engine.run_backtest(symbol, ...) for symbol in symbols]
       results = await asyncio.gather(*tasks)
       return results
   ```

### 性能基準

| 資料規模 | 目標時間 | 優化方法 |
|---------|---------|---------|
| 1 標的，1年，12h | < 1 秒 | 向量化 + Numba |
| 10 標的，1年，12h | < 5 秒 | 並行回測 |
| 100 標的，1年，12h | < 30 秒 | 批次處理 + 快取 |

---

## 介面定義

### REST API

**添加到 `api/routes/backtest.py`**：

```python
from fastapi import APIRouter, HTTPException
from api.models.backtest_models import BacktestRequest, BacktestResponse
from api.services.backtest_service import BacktestService

router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])
backtest_service = BacktestService()

@router.post("/run", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """執行回測"""
    try:
        result = await backtest_service.run_backtest(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/result/{task_id}")
async def get_backtest_result(task_id: str):
    """取得回測結果"""
    result = backtest_service.get_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="回測結果不存在")
    return result
```

### Pydantic Models

**添加到 `api/models/backtest_models.py`**：

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class BacktestRequest(BaseModel):
    """回測請求"""
    symbol: str = Field(..., description="交易標的")
    timeframe: str = Field(..., description="K線週期")
    start_date: str = Field(..., description="開始日期（ISO 8601）")
    end_date: str = Field(..., description="結束日期（ISO 8601）")
    strategy_params: Dict = Field(..., description="策略參數")
    initial_capital: float = Field(default=100000.0, description="初始資金")

class Trade(BaseModel):
    """單筆交易"""
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    return_pct: float

class EquityCurvePoint(BaseModel):
    """權益曲線點"""
    timestamp: str
    equity: float

class BacktestMetrics(BaseModel):
    """績效指標"""
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int

class BacktestResponse(BaseModel):
    """回測結果"""
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    initial_capital: float
    trades: List[Trade]
    equity_curve: List[EquityCurvePoint]
    metrics: BacktestMetrics
```

---

## 實現路徑

### Phase 1: 基礎架構（1-2 天）

**目標**：建立模組骨架，通過架構合規檢查

- [ ] 創建 `momentum/Backtest/` 目錄
- [ ] 定義 Protocol (`IBacktestEngine`, `IPositionManager`, `IPerformanceCalculator`)
- [ ] 添加 Factory 函數到 `momentum/factories.py`
- [ ] 創建空類別（BacktestEngine, PositionManager, PerformanceCalculator）
- [ ] 執行架構合規檢查（0 violations）

**驗證**：
```bash
grep -r "from api\." momentum/Backtest/  # 預期：0 結果
pytest tests/momentum/Backtest/test_structure.py -v
```

### Phase 2: 核心邏輯（3-5 天）

**目標**：實現基本回測功能（簡單策略）

- [ ] 實現 `BacktestEngine.run_backtest()` （使用 Python 循環版本）
- [ ] 實現 `PositionManager.open_position/close_position()`
- [ ] 實現 `PerformanceCalculator.calculate_metrics()`（基礎指標）
- [ ] 編寫單元測試（覆蓋率 > 80%）

**驗證**：
```bash
pytest tests/momentum/Backtest/ -v --cov=momentum.Backtest --cov-fail-under=80
```

### Phase 3: 性能優化（2-3 天）

**目標**：向量化計算，達成性能基準

- [ ] 向量化交易執行邏輯
- [ ] 使用 Numba JIT 優化關鍵路徑
- [ ] 性能測試（1年 12h 資料 < 1 秒）
- [ ] 並行回測支援

**驗證**：
```python
# 性能測試
import time
start = time.time()
result = backtest_engine.run_backtest(...)
elapsed = time.time() - start
assert elapsed < 1.0, f"回測時間 {elapsed:.2f}s 超過 1 秒"
```

### Phase 4: API 整合（2-3 天）

**目標**：提供 REST API，支援前端調用

- [ ] 創建 `api/services/backtest_service.py`
- [ ] 創建 `api/routes/backtest.py`
- [ ] 定義 Pydantic Models (`api/models/backtest_models.py`)
- [ ] WebSocket 實時進度（可選）
- [ ] API 測試

**驗證**：
```bash
pytest tests/api/test_backtest_route.py -v
curl -X POST http://localhost:8000/api/v1/backtest/run -d '{"symbol": "BTCUSDT", ...}'
```

### Phase 5: 前端整合（待項目1-3完成後，1-2 週）

**目標**：圖表展示回測結果

- [ ] 創建 `frontend/src/app/backtest/page.tsx`
- [ ] 權益曲線圖表（Recharts）
- [ ] 交易記錄表格
- [ ] 績效指標面板
- [ ] PNG 匯出功能

**驗證**：
```bash
cd frontend && npm run dev
# 手動測試圖表功能
```

---

## 總結

### 回測系統架構特點

1. **完全解耦**：遵循 7 條架構規則，可獨立開發
2. **Protocol 注入**：透過 `IKlineReader` 讀取數據，不直接依賴 DataExtraction
3. **向量化計算**：性能優化，支援大規模回測
4. **可擴展**：支援多種策略類型（RSI, ML, Pattern）

### 與現有系統整合

```
DataExtraction (K線) → Backtest (驗證)
FeatureEngineering (特徵) → XGBoost (預測) → Backtest (驗證)
Optimization (最佳參數) → Backtest (驗證)
```

### 開發時程

- Phase 1-4: **8-13 天**（後端完成）
- Phase 5: **7-10 天**（前端整合，等項目1-3完成後）
- **總計**: 約 **3-4 週**

---

**文檔維護**：
- 任何實現細節變更需更新本文件
- 性能基準測試結果需記錄到「性能設計」章節
- 新增策略類型需補充到範例程式碼

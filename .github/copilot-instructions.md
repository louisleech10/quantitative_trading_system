# AI Agent Instructions for Quantitative Trading System

> Quick reference guide for AI coding agents (GitHub Copilot, Claude, Cursor, etc.)

## 🎯 System Overview

**ML-first strategy research platform** — discover trading patterns from historical data, not just backtest known strategies.

**Architecture**: FastAPI backend (`api/`) → Core engines (`momentum/`) → Next.js frontend (`frontend/`) → HDF5 data storage (`data_cache/`)

**Key distinction**: This is a *research platform*, not an execution system. Focus: pattern discovery → ML optimization → backtesting.

---

## 📁 Critical Directories

### Backend (`api/`)
- **`api/main.py`** - FastAPI app entry, lifespan management, router registration
- **`api/routes/`** - Thin route handlers (case_search.py, chart.py, config.py, two_stage_search.py)
- **`api/services/`** - Heavy business logic (search_task_service.py, batch_download_service.py, chart_data_service.py)
- **`api/core/`** - Config (Settings from pydantic-settings), logging (ColoredFormatter), middleware
- **`api/models/`** - Pydantic request/response models

### Core Engines (`momentum/`)
- **`momentum/DataExtraction/`** - Case search engine, parallel search, kline download, HDF5 storage
  - `case_search_engine.py` - 20-parameter search framework with FilterCondition class
  - `parallel_search_engine.py` - Async multi-symbol concurrent search
  - `kline_storage.py` - HDF5 read/write/append operations with metadata management
- **`momentum/Indicator/`** - Technical indicator modules (pure functions, accept/return DataFrames)

### Frontend (`frontend/src/`)
- **`app/`** - Next.js 15 App Router pages (page.tsx, layout.tsx)
- **`components/`** - React components (charts/, shared UI)
- **`store/`** - Zustand state management (searchStore.ts - global search results/config)
- **`lib/types.ts`** - TypeScript interfaces matching backend models

### Data (`data_cache/`)
- **HDF5 files** - `{SYMBOL}_{timeframe}.h5` (e.g., BTCUSDT_12h.h5)
- **Structure**: Multi-level groups (symbol/timeframe), datasets with metadata
- ⚠️ **NEVER commit or generate fake data** - these are real market data

---

## 🚀 Quick Start Commands

```bash
# Backend (from project root)
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python run_api.py  # → http://localhost:8000, docs at /docs

# Frontend
cd frontend
npm install
npm run dev  # → http://localhost:3000

# Tests (pytest expected but not explicitly configured)
python test_kline_downloader.py  # Run individual test files
```

**Environment variables**: Set `BINANCE_API_KEY` and `BINANCE_SECRET_KEY` (checked in `api/core/config.py`). Not required for all features but needed for live data downloads.

---

## 🔑 Project-Specific Patterns

### Data Truth Principle
```python
# ❌ NEVER do this
symbols = ['BTC', 'ETH', 'DOGE']  # Hardcoded data
fake_prices = [45000, 3000, 0.08]

# ✅ ALWAYS do this
symbols = config.get_symbols()  # From config/API
prices = binance_client.get_prices(symbols)  # Real source
```

### Logging Standards
```python
# Use api.core.logging.get_logger()
from api.core.logging import get_logger
logger = get_logger(__name__)

# ✅ Good patterns
logger.info(f"Processing {len(symbols)} symbols")  # INFO for normal flow
logger.error(f"Failed to download {symbol}: {str(e)}", exc_info=True)  # ERROR with traceback

# ❌ Avoid
print("Debug message")  # Use logger
logger.debug("Loop iteration 12453")  # Too noisy in tight loops
```

### Error Classification & Retry Logic
```python
# Pattern from parallel_search_engine.py, kline_storage.py
from enum import Enum

class FailureType(Enum):
    RATE_LIMIT = "rate_limit"  # Retryable
    NETWORK_ERROR = "network"  # Retryable
    INVALID_SYMBOL = "invalid"  # Not retryable
    
def classify_error(error: Exception) -> FailureType:
    error_msg = str(error).lower()
    if '429' in error_msg or 'rate limit' in error_msg:
        return FailureType.RATE_LIMIT
    # ... more classification logic
    
# Apply backoff for retryable errors
```

### Async Service Pattern (FastAPI + asyncio)
```python
# api/services/ pattern
class SearchTaskService:
    async def execute_positive_search(self, request: SearchConfigRequest):
        task_id = str(uuid.uuid4())
        asyncio.create_task(self._run_search_task(task_id, request))
        return {"task_id": task_id}
    
    async def _run_search_task(self, task_id: str, request: SearchConfigRequest):
        try:
            # Heavy work in background
            results = await self.parallel_engine.search_cases_parallel(...)
            self.task_manager.update_status(task_id, "completed", results)
        except Exception as e:
            logger.error(f"Task {task_id} failed", exc_info=True)
            self.task_manager.update_status(task_id, "failed", error=str(e))
```

### HDF5 Storage Operations
```python
# Pattern from momentum/DataExtraction/kline_storage.py
import h5py

# Write with metadata
with h5py.File(hdf5_path, 'a') as f:
    group = f.require_group(f"{symbol}/{timeframe}")
    dataset = group.create_dataset('klines', data=df.values, compression='gzip')
    group.attrs['time_range'] = f"{start_time}_{end_time}"
    group.attrs['last_updated'] = datetime.now().isoformat()

# Read specific time range
df = pd.read_hdf(hdf5_path, key=f"{symbol}/{timeframe}")
df_filtered = df[(df['open_time'] >= start_ms) & (df['close_time'] <= end_ms)]
```

### Frontend State Management (Zustand)
```typescript
// frontend/src/store/searchStore.ts pattern
import { create } from 'zustand';

interface SearchState {
  currentResult: SearchResult | null;
  isLoading: boolean;
  setSearchResult: (result: SearchResult) => void;
}

export const useSearchStore = create<SearchState>((set) => ({
  currentResult: null,
  isLoading: false,
  setSearchResult: (result) => set({ currentResult: result }),
}));

// Usage in components
const { currentResult, setSearchResult } = useSearchStore();
```

---

## 🧪 Testing Approach

**Location**: Top-level `test_*.py` files (not in a `tests/` directory)  
**Framework**: Standard Python (no pytest fixtures visible, but pytest expected)  
**Pattern**: Function-based tests with descriptive names

```python
# Example from test_kline_downloader.py
def test_1_single_download_ethusdt():
    """測試1: 單一標的下載 - ETHUSDT 12小時"""
    logger.info("開始測試1...")
    # Test implementation with detailed logging
    
def test_4_storage_integration():
    """測試4: HDF5存儲整合 - 驗收標準: 數據自動保存到HDF5，可以正確讀取"""
```

**Run tests individually** (no suite runner discovered):
```bash
python test_kline_downloader.py
python test_kline_storage.py
```

---

## ⚡ Performance Guidelines

**Target platform**: MacBook M1 (8-core, 16GB RAM)  

**Optimization hierarchy** (from best to worst):
1. **Vectorized pandas/numpy** - Always prefer `df['column'].apply()` over Python loops
2. **Numba JIT** - For unavoidable numerical loops
3. **Async/multiprocessing** - For I/O-bound or embarrassingly parallel tasks
4. **Python loops** - Last resort, profile first

**Example transformation**:
```python
# ❌ Slow (Python loop)
results = []
for i in range(len(df)):
    results.append(df['close'].iloc[i] / df['open'].iloc[i] - 1)

# ✅ Fast (vectorized)
price_change_pct = (df['close'] / df['open'] - 1)
```

**Specific tools mentioned**: Optuna (hyperparameter tuning), pandas-ta/TA-Lib (indicators)

---

## 📋 Pre-Commit Checklist

Before submitting code:
- [ ] No hardcoded symbols/prices/fake data
- [ ] All external API calls have try/except with error classification
- [ ] Logging: INFO for key events, ERROR with `exc_info=True`
- [ ] Variables named clearly (no `df1`, `temp`, `x`)
- [ ] Vectorized operations where applicable (check pandas docs)
- [ ] Update `docs/` if architecture/API changes (ARCHITECTURE.md, API_SPECIFICATION.md)
- [ ] Add test case or smoke test for new features
- [ ] No large binary files staged for commit (check `.gitignore` for `data_cache/`)

---

## 📚 Documentation Structure

**Start here**:
- `README.md` - System overview, tech stack, roadmap (in Chinese)
- `docs/ARCHITECTURE.md` - Detailed system architecture (~4000 lines)
- `docs/DEVELOPMENT_GUIDE.md` - Ultra Think 3-step process, coding standards (~2500 lines)

**Reference**:
- `docs/API_SPECIFICATION.md` - API endpoints and models
- `docs/FEATURE_ROADMAP.md` - 24-week development plan
- `docs/KLINE_DATA_SPECIFICATION.md` - HDF5 data format specification

---

## 🚫 Common Pitfalls to Avoid

1. **Breaking API contracts** - Changes in `api/models/` must be backward-compatible or versioned
2. **Replacing vectorized code with loops** - Always benchmark before changing existing numeric algorithms
3. **Committing HDF5/CSV data** - Check `.gitignore`, use `data_cache/` directory only
4. **Ignoring error types** - Not all errors should be retried (classify first)
5. **Over-logging in loops** - Kills performance; log summaries instead
6. **Mixing UI and logic** - Keep route handlers thin; heavy work goes in `api/services/`

---

## 🔍 Finding Examples

**Need to add a case search filter?**  
→ See `momentum/DataExtraction/case_search_engine.py` (FilterCondition class, evaluate method)

**Need to add an API endpoint?**  
→ Copy pattern from `api/routes/case_search.py`, implement service in `api/services/`

**Need to add a chart component?**  
→ See `frontend/src/components/charts/TakerRatioChart.tsx` (Lightweight Charts integration)

**Need to add a technical indicator?**  
→ See `momentum/Indicator/Base_Indicator_Reference.py` (pure function pattern)

**Questions?** → Search docs/ for detailed explanations or ask for specific file examples.

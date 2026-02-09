# AI Agent Instructions for Quantitative Trading System

> Quick reference guide for AI coding agents (GitHub Copilot, Claude, Cursor, etc.)  
> **Last Updated**: 2026-02-09 | **Version**: 2.1

## 🎯 System Overview

**ML-first strategy research platform** — discover trading patterns from historical data, not just backtest known strategies.

**Architecture**: FastAPI backend (`api/`) → Core engines (`momentum/`) → Next.js 15 frontend (`frontend/`) → HDF5 data storage (`data_cache/`)

**Key distinction**: This is a *research platform*, not an execution system. Focus: pattern discovery → ML optimization → backtesting.

**Current Status** (2026 Q1): Phase 3 completed (optimization system, chart signals). Active development on Phase 4 (pattern discovery).

### 📍 Product Vision & Evolution Path

**Long-term goal**: Evolve from tool → assistant → autonomous AI researcher

```
V1.0 (Current - 2026 Q1-Q2):  Manual UI operation → Export results (CSV/PNG/AI-readable JSON)
V2.0 (2026 Q3-Q4):            Chat natural language → AI executes research → Conversational analysis
V3.0 (2027+):                 Fully autonomous AI Agent → Proposes strategies → Human approval
```

**Implications for development**:
- All new features must be **backward compatible** (V2.0 won't break V1.0 REST APIs)
- Architecture must support **independent deployment** (future: Agent service in separate container)
- **Decoupling rules** apply to all versions (see [docs/PRODUCT_VISION.md](../docs/PRODUCT_VISION.md))

**V1.0 Current Gap**: AI-readable export format (structured JSON/Markdown) - see ADR-002 in PRODUCT_VISION.md

---

## 📁 Critical Directories

### Backend (`api/`)
- **`api/main.py`** - FastAPI app entry, lifespan management, router registration
- **`api/routes/`** - Thin route handlers (case_search.py, chart.py, config.py, optimization.py, signal_analysis.py)
- **`api/services/`** - Heavy business logic:
  - `search_task_service.py` - Async case search orchestration
  - `optimization_task_service.py` - Optuna hyperparameter optimization
  - `chart_data_service.py`, `chart_signal_service.py` - Chart data & signal generation
  - `batch_download_service.py` - Parallel kline data download
  - `signal_analysis_service.py` - Signal statistics & density analysis
- **`api/core/`** - Config (Settings from pydantic-settings), logging (ColoredFormatter), middleware
- **`api/models/`** - Pydantic request/response models
- **`api/websocket/`** - WebSocket handlers (optimization_ws.py - real-time optimization progress)

### Core Engines (`momentum/`)
- **`momentum/DataExtraction/`** - Case search engine, parallel search, kline download, HDF5 storage
  - `case_search_engine.py` - 30-parameter search framework (6 trigger + 24 future performance + 2 counter-example)
  - `parallel_search_engine.py` - Async multi-symbol concurrent search with retry logic
  - `kline_storage.py` - HDF5 read/write/append operations with metadata management
- **`momentum/Indicator/`** - Technical indicator modules (pure functions, accept/return DataFrames)
- **`momentum/Optimization/`** - Optuna-based parameter optimization system
- **`momentum/Analysis/`** - Signal analysis, density calculation, statistical testing

### Frontend (`frontend/src/`)
- **`app/`** - Next.js 15 App Router pages (page.tsx, layout.tsx)
- **`components/`** - React components:
  - `charts/` - Lightweight Charts integration (TakerRatioChart, MultiPaneChartNew)
  - `optimization/` - 9+ components (MetricsPanel, DensityComparisonChart, StabilityChart, TrialHistoryTable)
  - `search/`, `case/` - Search interface and case management
- **`store/`** - Zustand state management:
  - `searchStore.ts` - Global search results/config
  - `optimizationStore.ts` - Optimization task state & results
- **`lib/types.ts`** - TypeScript interfaces matching backend models
- **`hooks/`** - Custom React hooks (useWebSocket for optimization progress)

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

# Tests (pytest configured in pytest.ini)
pytest                           # Run all tests
pytest tests/api/                # Backend tests only
pytest -v --tb=short             # Verbose with short tracebacks
python test_kline_downloader.py  # Legacy standalone test files

# Development
pytest --cov=momentum --cov-report=html  # Coverage report
```

**Environment variables**: Set `BINANCE_API_KEY` and `BINANCE_SECRET_KEY` in `.env` (see `api/core/config.py`). Optional for most features but required for live data downloads.

---

## 🔑 Project-Specific Patterns

### 0. First Principle Thinking
```
All code and architecture decisions start from First Principles
Ask "why" until you reach fundamental truths
Challenge assumptions before implementing
Document the reasoning behind non-obvious decisions
```

### 1. Data Truth Principle
```python
# ❌ NEVER do this
symbols = ['BTC', 'ETH', 'DOGE']  # Hardcoded data
fake_prices = [45000, 3000, 0.08]

# ✅ ALWAYS do this
symbols = config.get_symbols()  # From config/API
prices = binance_client.get_prices(symbols)  # Real source
```

### 2. Logging Standards
```python
# Use api.core.logging.get_logger()
from api.core.logging import get_logger
logger = get_logger(__name__)

# ✅ Good patterns
logger.info(f"Processing {len(symbols)} symbols")  # INFO for normal flow
logger.error(f"Failed to download {symbol}: {str(e)}", exc_info=True)  # ERROR with traceback
logger.warning("API key not set, limited functionality")  # WARN for degraded state

# ❌ Avoid
print("Debug message")  # Use logger instead
logger.debug("Loop iteration 12453")  # Too noisy in tight loops
logger.info(f"Processing {symbol}")  # Inside hot loops - log summaries instead
```

### 3. Ultra Think Development Process
```
MANDATORY 3-step process for all code generation:

Step 1 - Initial Generation:
  Generate working code that implements the feature
  Include basic error handling and logging
  Focus on correctness, not perfection

Step 2 - Self Review:
  Review Step 1 code and create To-do List
  Check: fake data? error handling? logs? naming? duplicates? performance? security?
  Output: List of improvements (DO NOT modify code yet)

Step 3 - Optimize & Refactor:
  Apply all items from Step 2 To-do List
  Generate production-ready final version
  Add comments for complex logic

See docs/DEVELOPMENT_GUIDE.md for detailed examples and checklist
```

### 4. Error Classification & Retry Logic
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

### 5. Async Service Pattern (FastAPI + asyncio)
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

### 6. HDF5 Storage Operations
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

### 7. Frontend State Management (Zustand)
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

### 8. WebSocket Real-Time Updates
```python
# Pattern from api/websocket/optimization_ws.py
from fastapi import WebSocket

@router.websocket("/ws/optimization/{task_id}")
async def optimization_progress(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        while True:
            progress = await task_service.get_progress(task_id)
            await websocket.send_json(progress)
            if progress["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from task {task_id}")
```

### 9. Frontend Component Patterns (Ultra Think)
```typescript
// Pattern from frontend/src/components/optimization/*.tsx
// All major components follow this structure:

/**
 * ComponentName.tsx
 * 
 * STEP 1 - THINK: Purpose and requirements
 * STEP 2 - REVIEW: Issues to address
 * STEP 3 - OPTIMIZE: Final implementation
 * 
 * Features:
 * - Feature 1 description
 * - Feature 2 description
 */

// Empty state handling
if (!data || data.length === 0) {
  return <EmptyState message="No data available" />;
}

// PNG export for charts
const handleExportPNG = () => {
  const element = chartRef.current;
  html2canvas(element).then(canvas => {
    const link = document.createElement('a');
    link.download = `${componentName}_${Date.now()}.png`;
    link.href = canvas.toDataURL();
    link.click();
  });
};

// Custom tooltips with detailed info
const CustomTooltip = ({ active, payload }: TooltipProps) => {
  if (!active || !payload?.[0]) return null;
  return (
    <div className="bg-white p-3 border rounded shadow-lg">
      {/* Detailed info display */}
    </div>
  );
};
```

---

## 🧪 Testing Approach

**Location**: `tests/` directory (formal pytest structure) + legacy top-level `test_*.py`  
**Framework**: pytest (configured in `pytest.ini`)  
**Pattern**: Function-based tests with Chinese docstrings for clarity

```python
# Modern pattern - tests/api/test_optimization.py
import pytest
from api.services.optimization_task_service import OptimizationTaskService

@pytest.fixture
async def optimization_service():
    return OptimizationTaskService()

async def test_start_optimization_task(optimization_service):
    """測試啟動優化任務"""
    result = await optimization_service.start_task(config)
    assert result["status"] == "running"

# Legacy pattern - test_kline_downloader.py (still valid)
def test_1_single_download_ethusdt():
    """測試1: 單一標的下載 - ETHUSDT 12小時"""
    logger.info("開始測試1...")
    # Direct test execution with detailed logging
```

**Run tests**:
```bash
pytest                    # All tests with pytest
pytest -v --tb=short      # Verbose with short tracebacks
pytest -m "not slow"      # Skip slow tests
pytest tests/api/         # Specific directory
python test_*.py          # Legacy standalone tests
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
- [ ] **Ultra Think completed**: Step 1 (generate) → Step 2 (review) → Step 3 (optimize)
- [ ] **No hardcoded data**: No symbols/prices/fake data (Data Truth Principle)
- [ ] **Error handling**: All external API calls have try/except with error classification
- [ ] **Logging**: INFO for key events, ERROR with `exc_info=True`, no logs in hot loops
- [ ] **Naming**: Variables clearly named (no `df1`, `temp`, `x`)
- [ ] **Performance**: Vectorized operations where applicable (pandas/numpy first)
- [ ] **Type hints**: All functions have proper type annotations
- [ ] **Tests**: New features have test coverage (pytest for backend, manual for frontend)
- [ ] **Docs**: Update `docs/` if architecture/API changes (ARCHITECTURE.md, API_SPECIFICATION.md)
- [ ] **Git**: No large binary files staged (check `.gitignore` for `data_cache/`, `*.h5`)
- [ ] **Frontend**: TypeScript compilation passes, no console errors, responsive design tested
- [ ] **Decoupling**: No Rule 1-7 violations (see below) - check with `grep -r "from api\." momentum/`

---

## 🏗️ Decoupling Architecture Quick Reference

**Critical rules** (enforced by REFACTOR_ARCHITECTURE_V4 - see [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)):

### The 7 Rules (Zero Tolerance)

| Rule | Summary | Quick Check |
|------|---------|-------------|
| **1** | `momentum/` NEVER imports `api/` | `grep -r "from api\." momentum/` → must be 0 results |
| **2** | Cross-Domain uses Protocol injection | `from momentum.core.protocols import I*` |
| **3** | `api/services/` uses `momentum/factories.py` | No `Engine()` or `Analyzer()` direct instantiation |
| **4** | Services don't import each other | No `from api.services.other_service import` |
| **5** | Config single source of truth | Read from `momentum/core/config.py` or `api/core/config.py` |
| **6** | Test config isolation | Tests run without `run_api.py` |
| **7** | DTOs don't cross domain boundaries | `api/models/` ↔ `momentum/core/contracts.py` no mutual dependency |

### Common Violations & Fixes

**❌ Violation 1: Service directly instantiates engine**
```python
# api/services/new_service.py
from momentum.Analysis.engine import Engine
self.engine = Engine()  # WRONG
```

**✅ Fix: Use Factory**
```python
# api/services/new_service.py
from momentum.core.protocols import IEngine

class NewService:
    def __init__(self, engine: IEngine):  # Inject Protocol
        self.engine = engine

# api/main.py
from momentum.factories import create_engine
service = NewService(engine=create_engine())
```

**❌ Violation 2: momentum imports api logging**
```python
# momentum/SomeDomain/module.py
from api.core.logging import get_logger  # WRONG
```

**✅ Fix: Use momentum logging**
```python
from momentum.core.logging import get_logger  # CORRECT
```

**❌ Violation 3: Cross-Domain direct import**
```python
# momentum/Analysis/feature_engineer.py
from momentum.DataExtraction.kline_storage import KlineStorageManager  # WRONG
self.storage = KlineStorageManager()
```

**✅ Fix: Protocol injection**
```python
from momentum.core.protocols import IKlineReader

class FeatureEngineer:
    def __init__(self, kline_reader: IKlineReader):  # CORRECT
        self.kline_reader = kline_reader
```

### When Adding New Features

**Checklist**:
1. Is this a new Domain? → Define in `momentum/{NewDomain}/`
2. Cross-Domain dependency? → Add Protocol to `momentum/core/protocols.py`
3. Used by API? → Add Factory function to `momentum/factories.py`
4. New config? → Add to `momentum/core/config.py` (domain-specific) or `api/core/config.py` (API-specific)
5. New DTO? → Define in `api/models/` (API) or `momentum/core/contracts.py` (momentum), NEVER both

**Example: Adding FeatureFactory (Task 1)**
- ✅ Lives in `momentum/FeatureEngineering/` (new Domain)
- ✅ Uses `IKlineReader` Protocol for K-line data (Rule 2)
- ✅ Built via `create_feature_factory()` in `momentum/factories.py` (Rule 3)
- ✅ Config from `momentum/core/config.py` (Rule 5)
- ✅ Tests run with `pytest tests/momentum/` (Rule 6)

### Why Decoupling Matters for V1 → V2 → V3

**Version evolution depends on clean architecture**:
- V1.0 (UI): `api/routes/` → `api/services/` → `momentum/`
- V2.0 (Chat): `api/chat/` → `api/services/` → `momentum/` (reuse same engines)
- V3.0 (Agent): `api/agent/` → `momentum/Agent/` → existing `momentum/` domains

**If violated**:
- ❌ Cannot deploy V2.0 Chat service independently
- ❌ Changes to V1.0 break V2.0
- ❌ Tests become integration tests (slow, brittle)

**Reference**: [docs/PRODUCT_VISION.md](../docs/PRODUCT_VISION.md) - Architecture Evolution Strategy

---

## 📚 Documentation Structure

**Start here**:
- `README.md` - System overview, tech stack, roadmap (in Chinese)
- `docs/PRODUCT_VISION.md` - V1/V2/V3 evolution plan, version goals, decoupling rationale
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
4. **Ignoring error types** - Not all errors should be retried (classify: rate_limit vs network vs invalid_symbol)
5. **Over-logging in loops** - Kills performance; log summaries instead (e.g., "Processed 1000 symbols in 5.2s")
6. **Mixing UI and logic** - Keep route handlers thin; heavy work goes in `api/services/`
7. **Skipping Ultra Think** - All code must go through 3-step process (THINK → REVIEW → OPTIMIZE)
8. **Hardcoded chart dimensions** - Use responsive design and handle empty/loading states
9. **Missing TypeScript types** - All props, state, and API responses must be typed
10. **Async without error boundaries** - Wrap async operations with proper try/catch and user feedback

---

## 🎨 UI/UX Patterns

### Component Structure (from optimization UI)
```
1. Empty state handling (no data message)
2. Loading state (skeleton or spinner)
3. Error state (retry button, error message)
4. Main content (responsive grid/flex)
5. Export functionality (PNG for charts, CSV for tables)
6. Keyboard shortcuts (Ctrl+A, Escape for tables)
7. Tooltips (custom with detailed info)
8. Color coding (green=good, yellow=medium, red=bad)
```

### Chart Best Practices
```typescript
// Responsive container
<ResponsiveContainer width="100%" height={400}>

// Always include empty state
if (!data || data.length === 0) return <EmptyStateComponent />;

// Custom tooltips for clarity
<Tooltip content={<CustomTooltip />} />

// Export functionality
<button onClick={handleExportPNG}>Export PNG</button>

// Color scales for data visualization
const getColor = (value: number) => {
  if (value > threshold1) return 'text-green-600';
  if (value > threshold2) return 'text-yellow-600';
  return 'text-red-600';
};
```

---

## 🔧 Configuration Management

### Backend Config Pattern
```python
# api/core/config.py - Pydantic Settings
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Use Field() for env var mapping and defaults
    debug: bool = Field(default=False, env="DEBUG")
    api_prefix: str = "/api/v1"
    
    # Path handling with Path objects
    data_cache_path: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent / "data_cache"
    )
    
    class Config:
        env_file = ".env"
        extra = "allow"  # Allow extra fields for extensibility
```

### Frontend Config Pattern
```typescript
// lib/config.ts or constants.ts
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

// Chart defaults
export const CHART_COLORS = {
  positive: '#10b981',  // green-500
  negative: '#ef4444',  // red-500
  neutral: '#6b7280',   // gray-500
};
```

---

## 📊 Data Flow Examples

### Case Search Flow
```
1. User inputs search params → frontend/src/app/search/page.tsx
2. POST /api/v1/search/execute → api/routes/case_search.py
3. SearchTaskService.execute() → api/services/search_task_service.py
4. CaseSearchEngine.search() → momentum/DataExtraction/case_search_engine.py
5. Results saved to CSV → data_cache/cases.json
6. Frontend polls GET /api/v1/search/task/{id} for status
7. Display results in ResultsTable component
```

### Optimization Flow
```
1. User clicks "Start Optimization" → frontend/src/app/optimization/page.tsx
2. POST /api/v1/optimization/start → api/routes/optimization.py
3. WebSocket connection opened → api/websocket/optimization_ws.py
4. OptimizationTaskService runs Optuna study → api/services/optimization_task_service.py
5. Real-time progress via WebSocket → frontend receives updates
6. Results stored and analyzed → display in MetricsPanel, DensityChart, etc.
7. Export available (CSV for trials, PNG for charts)
```

---

## 🔍 Finding Examples

**Need to add a case search filter?**  
→ [momentum/DataExtraction/case_search_engine.py](momentum/DataExtraction/case_search_engine.py) (FilterCondition class, 30-parameter framework)

**Need to add an API endpoint?**  
→ Copy pattern from [api/routes/optimization.py](api/routes/optimization.py), implement service in `api/services/`

**Need to add a chart component?**  
→ [frontend/src/components/charts/MultiPaneChartNew.tsx](frontend/src/components/charts/MultiPaneChartNew.tsx) (Lightweight Charts with synchronized panes)

**Need to add an optimization component?**  
→ [frontend/src/components/optimization/MetricsPanel.tsx](frontend/src/components/optimization/MetricsPanel.tsx) (responsive grid, color-coded metrics, tooltips)

**Need to add a technical indicator?**  
→ [momentum/Indicator/Base_Indicator_Reference.py](momentum/Indicator/Base_Indicator_Reference.py) (pure function pattern)

**Need WebSocket real-time updates?**  
→ [api/websocket/optimization_ws.py](api/websocket/optimization_ws.py) + [frontend/src/hooks/useWebSocket.ts](frontend/src/hooks/useWebSocket.ts)

**Questions?** → Search `docs/` for detailed explanations or ask for specific file examples.

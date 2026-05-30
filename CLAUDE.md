# Quantitative Trading System — Claude Code

**ML-first strategy research platform**: discover patterns → ML optimization → backtesting.  
Stack: FastAPI (`api/`) → Core engines (`momentum/`) → Next.js 15 (`frontend/`) → HDF5 (`data_cache/`)

**Vision**: V1.0 (manual UI, current) → V2.0 (chat/agent) → V3.0 (autonomous researcher).  
All code must support this evolution via clean decoupling.

---

## Multi-Agent 協作協議

`HANDOFF.md`（根目錄）是所有 agent 的共同交接文件。SessionStart hook 已設定自動注入。

- **每次開始工作**：HANDOFF.md 已自動注入 context，確認當前狀態
- **每次結束工作**：用 Write 工具更新 HANDOFF.md（≤ 30 行）
- **Context 壓縮前**：PreCompact hook 會提醒，優先更新 HANDOFF.md 再讓壓縮發生
- **其他 agent**：Codex 讀 `AGENTS.md`，Cursor 讀 `.cursorrules`，兩者都指向 HANDOFF.md

---

## Key Directories

**Backend**
- `api/main.py` — FastAPI app, lifespan, router registration
- `api/routes/` — thin route handlers only
- `api/services/` — all heavy business logic
- `api/models/` — Pydantic request/response models
- `api/websocket/` — WebSocket handlers (optimization, IC analysis, feature factory)
- `api/core/config.py` — Pydantic Settings, env vars

**Core Engines**
- `momentum/core/` — Protocols, Config, Contracts (architecture foundation)
- `momentum/factories.py` — all engine/service creation:
  - `create_feature_factory()`
  - `create_factor_return_analyzer()`, `create_factor_centrality_analyzer()`, `create_trend_analyzer()`, `create_parameter_sensitivity_analyzer()`, `create_rolling_oos_validator()`, `create_factor_orthogonalizer()`, `create_factor_exposure_analyzer()`, `create_long_short_analyzer()`, `create_feature_quality_diagnostics()`, `create_net_ic_analyzer()`
  - `create_probability_calibrator()`, `create_walk_forward_validator()`, `create_sample_weight_calculator()`, `create_adversarial_validator()`, `create_combinatorial_purged_cv()`, `create_learning_curve_analyzer()`
  - `create_backtest_engine()`, `create_position_sizer()`
- `momentum/DataExtraction/` — case search engine, parallel search, HDF5 storage
- `momentum/Indicators/` — dynamic config-driven indicator system
- `momentum/Analysis/` — IC Gatekeeper (12+10 modules), XGBoost+LightGBM engines
- `momentum/FeatureEngineering/` — Feature Factory (7-layer pipeline, Layer 6.5 preprocessing)
- `momentum/Optimization/` — Optuna (pluggable objectives: ModelHyperparam, StrategyBacktest)
- `momentum/Strategy/` — vectorized backtest, 12+ perf metrics, position sizing

**Frontend**
- `frontend/src/app/` — Next.js 15 App Router pages
- `frontend/src/components/` — React components (charts, optimization, ic-analysis, feature-factory, feature-browser, pattern, strategy)
- `frontend/src/store/` — Zustand stores
- `frontend/src/lib/types.ts` — TypeScript interfaces matching backend models
- `frontend/src/hooks/` — custom React hooks

**Data**: `data_cache/{SYMBOL}_{timeframe}.h5` — ⚠️ NEVER commit, NEVER fake.

---

## Dev Commands

```bash
source venv/bin/activate && python run_api.py   # backend → http://localhost:8000
cd frontend && npm run dev                       # frontend → http://localhost:3000
pytest                                           # all tests
pytest tests/api/ -v --tb=short
pytest --cov=momentum --cov-report=html
./scripts/check_decoupling_phase4.sh             # Rule 1/2/3/6 verification
```

---

## Non-Negotiable Principles

### Optimization Priority (Feature Factory / perf work)
1. Cross-tier repeatability (8GB/16GB/24GB/32GB)
2. Multi-symbol stability (OOM safety, resume/retry)
3. Data quality (no fake data, no cross-symbol contamination, no stale cache)
4. Shortest practical runtime — only after 1-3 are protected
5. Smallest practical output — no lossy numerical behavior
6. Quant finance best practice — document deviations

**Never** skip quality checks, weaken NaN/inf gates, or change output size without explicit user approval.

### Data Truth
No hardcoded symbols, prices, or metrics. All data from real API, config, or actual computation.

### Logging
```python
from api.core.logging import get_logger
logger = get_logger(__name__)
# INFO: normal flow | ERROR: with exc_info=True | no logs inside hot loops
```

### Error Classification
- Retryable: rate_limit, network timeout
- Non-retryable: invalid_symbol, logic error, data format

### Validate Assumptions Before Acting（實測 > 假設）

**Before writing any code, ask: "What am I assuming here, and do I actually know it's true?"**

A belief is not evidence. "It should work like X" is not "I verified it works like X."

The discipline:
1. **Name the assumption explicitly** — write it down in one sentence ("I assume the column uses underscore, not hyphen")
2. **Find the cheapest verification** — grep, read a real file, load actual data, add a temporary log
3. **Verify first, then plan, then code** — never the other way around
4. **If evidence contradicts the plan: stop, document the finding, update the plan** — do not implement what the evidence has disproved

This applies to everything: naming conventions, NaN patterns, execution paths, test fixtures, bug hypotheses, "obviously" true facts about the codebase, and anything else that would cause wasted or wrong work if it turned out to be false.

*Established after two incidents: (1) assumed `underscore` naming → missed real `hyphen` across entire run; (2) assumed "frontend misclassifies warmup as mid-hole" → nearly modified a correct classifier.*

---

## The 7 Decoupling Rules (Zero Tolerance)

| # | Rule | Quick Check |
|---|------|-------------|
| 1 | `momentum/` never imports `api/` | `grep -r "from api\." momentum/` → 0 results |
| 2 | Cross-domain dependency → Protocol injection | `from momentum.core.protocols import I*` |
| 3 | Services use factories, not direct engine instantiation | `from momentum.factories import create_*` |
| 4 | Services don't import each other | no `from api.services.X import` |
| 5 | Config single source of truth | `momentum/core/config.py` or `api/core/config.py` |
| 6 | Tests run without `run_api.py` | `pytest tests/momentum/` standalone |
| 7 | DTOs don't cross domain boundaries | `api/models/` ↔ `momentum/core/contracts.py` no mutual dep |

**Adding new features — checklist**:
- New Domain? → `momentum/{NewDomain}/`
- Cross-domain? → Protocol in `momentum/core/protocols.py`
- Used by API? → Factory in `momentum/factories.py`
- New config? → `momentum/core/config.py` (engine) or `api/core/config.py` (API)
- New DTO? → `api/models/` (API) or `momentum/core/contracts.py` (engine), never both

---

## Code Standards

**Python**: type hints on all functions; vectorize (pandas/numpy) over loops; Numba for unavoidable hot paths; docstrings in Chinese (project convention).

**TypeScript/React**: all props/state/API responses typed; Zustand for state; empty/loading/error states in all data components; `<ResponsiveContainer>` for all charts.

**Git commits**: `feat:` `fix:` `docs:` `refactor:` `perf:` `test:` `chore:`

**Quant pitfalls**:
- Overfitting: realistic win rates 55-65%, 10-20 key params, strict train/val/test split
- Data leakage: no future data in signals, test set used once only
- Replacing vectorized code with loops — always benchmark first

---

## Pre-Commit Checklist

- [ ] No hardcoded data/symbols/prices/fake metrics
- [ ] Error handling with retryable vs non-retryable classification
- [ ] No logging in tight loops (log summaries instead)
- [ ] Type hints complete (Python + TypeScript)
- [ ] Decoupling: `grep -r "from api\." momentum/` → 0 results
- [ ] `pytest` passes
- [ ] `npm run build` passes (if frontend changed)
- [ ] `docs/` updated if API/architecture changed

---

## Key Documentation

- `HANDOFF.md` — current task state, decisions, blockers (update before handoff)
- `docs/ARCHITECTURE.md` — full system architecture (~1900 lines)
- `docs/DEVELOPMENT_GUIDE.md` — coding standards
- `docs/API_SPECIFICATION.md` — all API endpoints (v5.0)
- `docs/PRODUCT_VISION.md` — V1/V2/V3 evolution plan, decoupling rationale

# DECOUPLING COMPLIANCE REVIEW - DRAFT v0.1

Generated: 2026-04-04
Scope: repository-wide static scan + manual spot verification
Baseline Rules: Rule 1 to Rule 7 in docs/全系統解耦Prompt.md

---

## 1) First-Principle Framing

The decoupling objective is not style cleanup. It is execution-boundary integrity.

- If a boundary can be crossed with direct concrete imports, deployment units are not independent.
- If service layers call each other directly, orchestration and domain logic become tangled and hard to replace.
- If mutable singletons or callback monkeypatches are used as shortcuts, runtime behavior depends on hidden global state.

Therefore, this review marks issues by whether they break independent testing/deployment assumptions, not by formatting preferences.

---

## 2) Compliance Matrix (Current Snapshot)

| Rule | Status | Evidence Count | Summary |
|---|---|---:|---|
| Rule 1: momentum must not import api | PASS | 0 | No reverse dependency found in momentum/ |
| Rule 2: no cross-domain concrete imports in momentum | FAIL | 10 | Cross-domain concrete imports remain in Feature/Indicators/Optimization |
| Rule 3: api/services must not directly construct/import momentum concrete objects | FAIL | 9 | Multiple services still import momentum domain classes directly |
| Rule 4: no service-to-service coupling | FAIL | 3 (+2 related) | Direct service imports found; private method usage across services also exists |
| Rule 5: no mutable global singleton shared across domains | WARNING | 0 strict + 13 risk patterns | Strict momentum->api settings import is clean, but mutable singleton patterns remain |
| Rule 6: no callback/closure bypass for boundaries | FAIL | 1 | Confirmed monkeypatch via lambda on private storage method |
| Rule 7: api/models and momentum/core no bidirectional coupling | PASS | 0 | No forbidden model/core cross-dependency found |

---

## 3) Detailed Findings

### [VIOLATION] Rule 2: momentum cross-domain concrete imports

#### Evidence (10)

1. momentum/FeatureEngineering/timeframe/tf_aligner.py:10
   - from momentum.DataExtraction.kline_storage import KlineStorageManager
2. momentum/FeatureEngineering/adapters/crypto_spot_adapter.py:9
   - from momentum.DataExtraction.kline_storage import KlineStorageManager
3. momentum/Indicators/data_source_manager.py:25
   - from momentum.DataExtraction.kline_storage import KlineStorageManager
4. momentum/Optimization/objectives/strategy_backtest.py:10
   - from momentum.Strategy.performance_metrics import PerformanceMetrics
5. momentum/Optimization/objectives/model_hyperparam.py:11
   - from momentum.Analysis.model_config import ModelConfigManager
6. momentum/Optimization/optuna_optimizer.py:98
   - from momentum.Analysis.signal_density_analyzer import SignalDensityAnalyzer
7. momentum/Optimization/optuna_optimizer.py:99
   - from momentum.Analysis.kline_cache import KlineCache
8. momentum/Optimization/optuna_optimizer.py:100
   - from momentum.Analysis.indicator_cache import IndicatorCache
9. momentum/Optimization/optuna_optimizer.py:101
   - from momentum.DataExtraction.kline_storage import KlineStorageManager
10. momentum/Optimization/optuna_optimizer.py:102
    - from momentum.Indicators.indicator_engine import IndicatorEngine

#### Why this matters

- Domain boundaries become compile-time coupled.
- Replacing one domain implementation forces code changes in another domain.
- Independent test isolation for each domain is weakened.

#### Required modifications

- Replace direct concrete imports with boundary interfaces in momentum/core/protocols.py where needed.
- For timeframe constants now taken from KlineStorageManager, move the mapping to a neutral utility (core-level) and reference that instead.
- In Optimization objectives, inject collaborators (or precomputed artifacts) through constructors/factory wiring, not direct class imports.
- Keep momentum/factories.py as the composition root exception.

---

### [VIOLATION] Rule 3: api/services direct momentum concrete imports

#### Evidence (9)

1. api/services/feature_toggle_service.py:15
   - from momentum.Analysis.feature_toggle_registry import DifficultyLevel, FeatureToggleRegistry
2. api/services/feature_factory_service.py:31
   - from momentum.DataExtraction.parallel_search_engine import FailureType, classify_error
3. api/services/feature_factory_service.py:33
   - from momentum.FeatureEngineering.feature_factory import FeatureGenerationResult
4. api/services/feature_factory_service.py:34
   - from momentum.FeatureEngineering.mcp.feature_factory_mcp import FeatureFactoryMCP
5. api/services/feature_factory_service.py:521
   - from momentum.DataExtraction.kline_storage import KlineStorageManager
6. api/services/optimization_task_service.py:30
   - from momentum.Optimization.objectives.model_hyperparam import ModelHyperparamObjective
7. api/services/optimization_task_service.py:31
   - from momentum.Optimization.objectives.strategy_backtest import StrategyBacktestObjective
8. api/services/lstm_task_service.py:204
   - from momentum.Analysis.lstm_engine import LSTMEngine, SequenceModelConfig
9. api/services/ic_analysis_service.py:23
   - from momentum.Analysis.ic_reporter import ICReporter

#### Why this matters

- API service layer is no longer just orchestration; it becomes coupled to domain internals.
- Any domain refactor requires API service rewrites.
- Runtime creation paths become fragmented (factory + direct instantiation mixed).

#### Required modifications

- Add/expand factory entry points in momentum/factories.py for objects currently imported directly.
- In optimization_task_service, create objectives through factory functions instead of importing objective classes.
- In ic_analysis_service and lstm_task_service, use factory-created adapters/reporters/engines rather than direct domain class imports.
- In feature_factory_service, remove direct KlineStorageManager import in export path and use factory-backed provider.
- In feature_toggle_service, avoid direct enum/class dependency on Analysis internals; depend on registry interface/factory output only.

---

### [VIOLATION] Rule 4: service-to-service coupling and internal method reach-through

#### Evidence (3 direct service imports)

1. api/services/export_service.py:136
   - from api.services.model_enhancement_service import get_model_enhancement_service
2. api/services/feature_factory_service.py:35
   - from api.services.feature_export_service import FeatureExportService
3. api/services/optimization_task_service.py:28
   - from api.services.optimization_output_service import get_optimization_output_service

#### Related coupling evidence (2 service->route imports)

1. api/services/export_service.py:127
   - from api.routes.pattern_analysis import model_task_service
2. api/services/model_enhancement_service.py:483
   - from api.routes.pattern_analysis import model_task_service

#### Internal/private API reach-through

- api/services/feature_factory_service.py:1002-1004
  - calls _infer_category/_infer_layer/_infer_level on FeatureExportService
- api/services/feature_factory_service.py:1769-1771
  - repeated calls to private methods from another service class
- api/services/feature_factory_service.py:305
  - monkeypatches private storage method via lambda (also Rule 6 violation)

#### Why this matters

- Service boundaries are bypassed.
- Private methods in one service become undocumented dependencies for another service.
- Routes and services become cyclic in responsibility.

#### Required modifications

- Move shared feature-name parsing logic from FeatureExportService private methods into a dedicated utility module with public API.
- Inject dependencies into services via constructor/app composition root, not via cross-service imports.
- Remove service->route imports by introducing task payload provider abstractions in service layer.

---

### Rule 5 Assessment: mutable singleton risk remains

#### Strict check (PASS)

- momentum imports of api.core.config.settings: 0

#### Risk patterns (13)

- Module-level service singletons (6):
  - api/services/optimization_output_service.py:564
  - api/services/xgboost_batch_service.py:1262
  - api/services/feature_toggle_service.py:103
  - api/services/export_service.py:152
  - api/services/model_enhancement_service.py:535
  - api/services/feature_factory_batch_service.py:357
- Singleton class patterns (7):
  - api/services/chart_data_service.py:983
  - api/services/optimization_task_service.py:134,137
  - api/services/chart_signal_service.py:53,55
  - api/services/signal_analysis_service.py:47,49

#### Interpretation

- Not an immediate Rule 5 hard fail under strict wording, but high coupling risk under concurrent/task-heavy runtime.
- Shared mutable state should be lifecycle-managed in app startup, not hidden globals.

#### Required modifications

- Replace implicit global singleton access with explicit dependency lifecycle (FastAPI app state / dependency provider).
- Keep thread-safety guarantees explicit in constructors and task registries.

---

### [VIOLATION] Rule 6: callback/closure bypass

#### Evidence (1 confirmed)

1. api/services/feature_factory_service.py:305
   - shadow_factory._storage.save_factory_output = lambda *_args, **_kwargs: ""

#### Why this matters

- This bypasses normal persistence contract by mutating private internals at runtime.
- Behavior depends on hidden monkeypatch side effects.

#### Required modifications

- Replace monkeypatch with explicit API contract:
  - Option A: add no_persist/dry_run flag in feature factory pipeline.
  - Option B: inject a NullStorage implementation via factory.

---

### Rule 1 and Rule 7 pass checks

- Rule 1:
  - grep ^from api\. in momentum/ -> 0
  - grep ^import api\. in momentum/ -> 0
- Rule 7:
  - api/models -> momentum/core forbidden import -> 0
  - momentum/core -> api/models forbidden import -> 0

---

## 4) Phased Remediation Plan (Draft)

### Phase 0: Guardrail first (prevent new violations)

- Add CI check commands for Rule 1/2/3/4/7 with fail-fast thresholds.
- Freeze baseline and reject any PR that increases violation count.

Exit criteria:
- No new violations introduced after this draft.

### Phase 1: Rule 4 cleanup (service boundaries)

- Remove all direct service->service imports.
- Remove all service->route imports.
- Extract shared feature parsing into utility/public API module.

Exit criteria:
- Rule 4 direct hits = 0
- service->route hits = 0
- no cross-service private method calls

### Phase 2: Rule 3 cleanup (API service purity)

- Replace direct momentum imports in api/services with factory/protocol adapters.
- Centralize object construction in momentum/factories.py or API composition root.

Exit criteria:
- Rule 3 hits = 0

### Phase 3: Rule 2 cleanup (domain independence)

- Remove cross-domain concrete imports inside momentum domains.
- Inject dependencies via protocols/artifacts where needed.

Exit criteria:
- Rule 2 hits = 0 (excluding momentum/factories.py composition root)

### Phase 4: Rule 5/6 hardening

- Replace global singleton risk patterns with explicit lifecycle management.
- Remove lambda monkeypatch path and implement explicit no_persist contract.

Exit criteria:
- Rule 6 confirmed violations = 0
- singleton usage reduced to documented, lifecycle-managed instances only

---

## 5) Definition of Done for this decoupling cycle

1. Rule 1 count = 0
2. Rule 2 count = 0 (excluding composition root)
3. Rule 3 count = 0
4. Rule 4 count = 0
5. Rule 6 count = 0
6. Rule 7 count = 0
7. Full test suite passes
8. API boots successfully
9. Decoupling docs updated to match actual state (no stale "0 violation" claims)

---

## Appendix A: Commands used in this review

```bash
# Rule 1
grep -rn --include='*.py' '^from api\.' momentum/
grep -rn --include='*.py' '^import api\.' momentum/

# Rule 2 (candidate scan excluding factories/core/same-domain)
grep -rn --include='*.py' '^from momentum\.' momentum/ | awk ...

# Rule 3
grep -rn --include='*.py' 'from momentum\.' api/services/ | grep -v 'from momentum.factories' | grep -v 'from momentum.core'

# Rule 4
grep -rn --include='*.py' 'from api.services' api/services/
grep -rn --include='*.py' 'from .*service' api/services/

# Rule 5 (strict + risk patterns)
grep -rn --include='*.py' 'from api.core.config import settings' momentum/
grep -rn --include='*.py' '^_[a-zA-Z0-9_]*service\s*:\s*Optional\[' api/services/
grep -rn --include='*.py' -E '_instance\s*=\s*None|def __new__\(' api/services/

# Rule 6
grep -rn --include='*.py' -E '\\.[A-Za-z_][A-Za-z0-9_]*\s*=\s*lambda' api/ momentum/

# Rule 7
grep -rn --include='*.py' '^from momentum\.core\.' api/models/
grep -rn --include='*.py' '^from api\.models\.' momentum/core/
```

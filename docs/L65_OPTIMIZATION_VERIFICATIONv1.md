# L6.5 Optimization Verification v1

## [Task 0.0] 2026-04-27

### Scope

- Batch 1: Task 0.0 — Golden Baseline Tier 1+2 and test inventory.
- Implemented only TODO-declared files and artifacts.
- Did not modify `momentum/` implementation code.

### Artifacts

- `scripts/build_l65_golden.py`
- `tests/conftest.py`
- `tests/golden/l65/test_l65_golden.py`
- `tests/golden/l65/tier1_structure/column_inventory.json`
- `tests/golden/l65/tier1_structure/schema_hash.txt`
- `tests/golden/l65/tier2_reduced/synthetic_baseline.parquet`
- `tests/golden/l65/tier2_reduced/d_star_synthetic.json`
- `tests/golden/l65/tier2_reduced/ETHUSDT_1h_2000rows.parquet`
- `tests/golden/l65/tier2_reduced/d_star_ETHUSDT_1h_2000rows.json`
- `tests/golden/l65/test_inventory.txt`

### Gate Results

| Gate / Check | Command | Result | Notes |
|---|---|---|---|
| §0.5 Python env | `./venv/bin/pytest --version` | PASS | pytest 8.4.2; configured Python is 3.9.6. |
| §0.5 packages | `./venv/bin/python -c 'import psutil, joblib, numba, statsmodels; ...'` | PASS | psutil 7.0.0, joblib 1.5.3, numba 0.60.0, statsmodels 0.14.6. |
| §0.5 cache dir | `test -d data_cache/feature_preprocessing && test -w data_cache/feature_preprocessing` | PASS | Exit 0; directory exists and is writable. |
| T0.1 collect inventory | `./venv/bin/pytest --collect-only tests -q` | PASS | Exit 0; latest direct summary collected 2078 tests; inventory file has 60 filtered L6.5/preprocessing nodeids. |
| T0.1 golden pytest | `./venv/bin/pytest tests -k l65_golden` | PASS | Exit 0; 4 passed. |
| Tier 1 artifact | `ls tests/golden/l65/tier1_structure/column_inventory.json` | PASS | File exists; test asserts 100 schema entries and 64-char SHA-256 hash. |
| Tier 2A artifact | `ls tests/golden/l65/tier2_reduced/synthetic_baseline.parquet` | PASS | File exists; test asserts 1000 rows x 100 columns. |
| Tier 2B artifact | `./venv/bin/python scripts/build_l65_golden.py --tier 2b --symbol ETHUSDT --tf 1h --max-rows 2000 --max-cols 500` | PASS | Reduced workload gate passed with available RAM 1.18GB >= required 1.06GB; wrote 2000 rows x 34 columns and 13 d_star entries. |
| Inventory artifact | `ls tests/golden/l65/test_inventory.txt` | PASS | File exists; 60 filtered nodeids. |
| Decoupling grep | `grep -r 'from api\.' momentum/FeatureEngineering/preprocessing/` | PASS | grep exit 1 with no output means 0 matches. |
| New-file ruff | `./venv/bin/ruff check scripts/build_l65_golden.py tests/conftest.py tests/golden/l65/test_l65_golden.py` | PASS | Exit 0; all checks passed. |
| Required broad ruff | `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/ api/services/ momentum/core/` | BLOCKED | Exit 1; 119 pre-existing lint errors outside Task 0.0 changes. Not fixed because Task 0.0 explicitly forbids modifying `momentum/` code and scope excludes `api/services/` cleanup. |

### Tier 2B Status

- Tier 2B source is `data_cache/feature_klines/kline_cache.h5`.
- Source verification: `ETHUSDT/1h/data` exists with 17,928 rows.
- Fixed the Task 0.0 RAM gate from a hard `available >= 4GB` check to a reduced-workload estimate because 8GB macOS can report `<4GB` immediately after boot.
- Rebuild command: `./venv/bin/python scripts/build_l65_golden.py --tier 2b --symbol ETHUSDT --tf 1h --max-rows 2000 --max-cols 500`.
- Result: CLI exited 0; reduced workload gate passed (`available RAM 1.18GB >= required 1.06GB`).
- Artifact verification: `ETHUSDT_1h_2000rows.parquet` exists with shape `(2000, 34)` and size 390,697 bytes; `d_star_ETHUSDT_1h_2000rows.json` exists with 13 entries and size 447 bytes.
- `tests/golden/l65/tier2_reduced/ETHUSDT_1h_2000rows.BLOCKED` no longer exists.

### Rule Confirmation

- R1.1: PASS — no `from api.` imports in `momentum/FeatureEngineering/preprocessing/`.
- R1.2: N/A for Task 0.0 — no cross-domain context object introduced.
- R1.3: N/A for Task 0.0 — batch service untouched.
- R1.4: N/A for Task 0.0 — no new environment variables introduced.
- R1.5: PASS — new tests run independently with `./venv/bin/pytest` and do not require `run_api.py`.
- Rule 2 Logging: PASS — new logs use `momentum.core.logging.get_logger`; no per-column info logs.
- Rule 3 Error Handling: PASS — Tier 1/2A CLI still exits code 2 if reduced gate fails; Tier 2B unavailable data or insufficient reduced workload RAM writes explicit blocked marker; pytest missing exits code 2.
- Rule 4 Naming: PASS — new module/function names are descriptive; no prohibited placeholder names.
- Rule 5 Type Hints: PASS — new functions include Python 3.9-compatible typing; no `X | Y` syntax.
- Rule 6 Performance: PASS — synthetic generation and transforms use vectorized numpy/pandas except deterministic AR(1) fixture construction.
- Rule 7 Fallback: N/A for Task 0.0 — no Phase fallback behavior changed.
- Rule 8 Git: PASS — no branch, commit, or push performed.

### Known Blockers / Warnings

- Required broad ruff remains BLOCKED by existing lint debt:
  - `momentum/FeatureEngineering/preprocessing/__init__.py:1 F401`
  - `momentum/FeatureEngineering/preprocessing/_numba_transforms.py:7 F401`
  - `momentum/FeatureEngineering/preprocessing/_numba_transforms.py:16 F401`
  - `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:306 F401`
  - plus existing `api/services/` lint errors such as F401, E402, F841, F821.
- These were not modified due Task 0.0's explicit boundary: do not modify `momentum/` code and do not alter unrelated API service files.

## [Task 0.1 + 0.2 + 0.4 + 0.5] 2026-04-27

### Scope

- Batch 2: Task 0.1 — FracDiff Apply-To-Layer Filter.
- Batch 2: Task 0.2 — precision 0.01 to 0.02 plus d_star cache version bump.
- Batch 2: Task 0.4 — per-run non_stationary classification cache.
- Batch 2: Task 0.5 — PreprocessingPanel FracDiff/ADF warning copy and snapshot test.
- Kept Task 0.3 full d_star cache context/migration architecture out of scope; Batch 2 only bumped the existing d_star cache helpers to `cache_version: "v2"` with precision invalidation.

### Artifacts

- `config/scan_config.yaml`
- `momentum/core/config.py`
- `momentum/FeatureEngineering/preprocessing/_non_stationary_cache.py`
- `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py`
- `tests/feature_engineering/preprocessing/test_layer_filter.py`
- `tests/feature_engineering/preprocessing/test_precision_corr.py`
- `tests/feature_engineering/preprocessing/test_non_stationary_cache.py`
- `frontend/src/components/feature-factory/PreprocessingPanel.tsx`
- `frontend/src/components/feature-factory/__tests__/PreprocessingPanel.test.tsx`
- `frontend/src/components/feature-factory/__tests__/__snapshots__/PreprocessingPanel.test.tsx.snap`
- `frontend/vitest.config.ts`
- `frontend/package.json`
- `frontend/package-lock.json`
- `docs/L65_OPTIMIZATION_TODO.md`
- `docs/L65_OPTIMIZATION_VERIFICATIONv1.md`

### Gate Results

| Gate / Check | Command | Result | Notes |
|---|---|---|---|
| Decoupling grep | `grep -r "from api\." momentum/FeatureEngineering/preprocessing/` | PASS | grep exit 1 with no output means 0 matches. |
| Required broad ruff | `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/ api/services/ momentum/core/` | BLOCKED | Exit 1; 118 existing lint errors remain outside Batch 2 files. Batch 2 Python files report 0 errors after removing one unused local import. |
| Batch 2 focused ruff | `./venv/bin/ruff check momentum/core/config.py momentum/FeatureEngineering/preprocessing/_non_stationary_cache.py momentum/FeatureEngineering/preprocessing/feature_preprocessor.py tests/feature_engineering/preprocessing/test_layer_filter.py tests/feature_engineering/preprocessing/test_precision_corr.py tests/feature_engineering/preprocessing/test_non_stationary_cache.py` | PASS | Exit 0; all checks passed. |
| Python Batch Gate | `./venv/bin/pytest tests/feature_engineering/preprocessing -k "layer_filter or precision or non_stationary or unknown_layer or high_nan_no_adf"` | PASS | Exit 0; 9 passed, 0 failed, 0 errors. |
| Frontend Batch Gate | `cd frontend && npm run test -- PreprocessingPanel` | PASS | Exit 0; 1 test file passed, 1 test passed, 0 failures; initial run wrote 1 snapshot, rerun did not update snapshots. |

### Rule Confirmation

- R1.1: PASS — no `from api.` imports in `momentum/FeatureEngineering/preprocessing/`.
- R1.2: N/A for Batch 2 — no cross-domain context object introduced; Task 0.3 remains separate.
- R1.3: N/A for Batch 2 — batch service untouched.
- R1.4: PASS — new environment variable parsing is centralized in `momentum/core/config.py`.
- R1.5: PASS — new tests run with `./venv/bin/pytest` and do not require `run_api.py`.
- Rule 2 Logging: PASS — warnings/info use existing momentum logger; no per-column info logs were added.
- Rule 3 Error Handling: PASS — invalid env overrides and cache read failures fall back safely with warnings/cache miss.
- Rule 4 Naming: PASS — new helper/cache names are descriptive.
- Rule 5 Type Hints: PASS — new Python typing is Python 3.9-compatible; no `X | Y` syntax.
- Rule 6 Performance: PASS — FracDiff layer filtering now happens before non_stationary ADF selection for non-target layers.
- Rule 7 Fallback: PASS — `legacy` profile and `FFACT_FRACDIFF_APPLY_TO_LAYERS=ALL` remain available.
- Rule 8 Git: PASS — no branch, commit, or push performed.

### Implementation Notes

- Task 0.1: added layer allow-list parsing, `optimized` default `L1,L2`, `legacy` default `L1,L2,L3,L4`, `ALL` override, and unknown-layer warning/skip behavior.
- Task 0.2: changed default FracDiff precision to `0.02`, added `FFACT_FRACDIFF_PRECISION_OVERRIDE`, and versioned existing d_star cache payloads as `v2` with precision mismatch invalidation and atomic save.
- Task 0.4: added in-memory per-instance `NonStationaryCache`; high-NaN columns skip ADF and are cached as stationary for the current run.
- Task 0.5: replaced mutual-exclusion copy with yellow informational warnings, preserved non-blocking controls, and added Vitest snapshot coverage.

### Known Blockers / Warnings

- Required broad ruff remains BLOCKED by existing lint debt outside Batch 2 scope. The remaining 118 errors are concentrated in pre-existing files such as `api/services/task_manager.py`, `api/services/search_task_service.py`, `api/services/standalone_search_service.py`, `api/services/xgboost_batch_service.py`, and `api/services/kline_data_service.py`.
- Batch 2 focused ruff is clean, so no remaining lint errors are attributable to the Batch 2 Python changes.
- Installing frontend test dependencies reported npm audit warnings: 10 vulnerabilities (4 moderate, 5 high, 1 critical). They were not remediated because dependency-security cleanup is outside this TODO batch.

## [Task 0.3] 2026-04-27

### 範圍

- Batch 3: Task 0.3 — d_star Cache Key 與 Schema 修正。
- 實作 `PreprocessingContext`、context-aware `DStarCache`、deterministic data fingerprint、feature schema hash、atomic write、legacy migration audit dry-run。
- 移除 L6.5 d_star cache 的 `default/default` 有效讀寫路徑；舊 cache 僅可被 migration script 稽核或隔離。
- 未擴展 Task 0.6 multi-symbol batch hardening，也未改動 `api/services/` 既有 lint 債務。

### 交付物

- `momentum/FeatureEngineering/preprocessing/_d_star_cache.py`
- `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py`
- `momentum/FeatureEngineering/preprocessing/__init__.py`
- `momentum/FeatureEngineering/preprocessing/_numba_transforms.py`
- `momentum/FeatureEngineering/feature_factory.py`
- `momentum/factories.py`
- `momentum/core/config.py`
- `scripts/migrate_d_star_cache.py`
- `tests/feature_engineering/preprocessing/test_d_star_isolation.py`
- `tests/feature_engineering/preprocessing/test_d_star_atomic_write.py`
- `tests/feature_engineering/preprocessing/test_d_star_stale_invalidation.py`
- `tests/feature_engineering/preprocessing/test_d_star_legacy_migration_audit.py`
- `tests/feature_engineering/preprocessing/test_cache_version_invalid.py`
- `tests/feature_engineering/preprocessing/test_precision_corr.py`
- `docs/L65_OPTIMIZATION_TODO.md`
- `docs/L65_OPTIMIZATION_VERIFICATIONv1.md`

### Gate 結果

| Gate / Check | Command | Result | Notes |
|---|---|---|---|
| 解耦 grep | `grep -r 'from api\.' momentum/FeatureEngineering/preprocessing/` | PASS | Exit 1 且無輸出，代表 0 matches。 |
| preprocessing/core ruff | `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/ momentum/core/` | PASS | Exit 0；All checks passed。 |
| Required broad ruff | `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/ api/services/ momentum/core/` | BLOCKED | Exit 1；115 errors，全部位於既有 `api/services/`。本 Task 修改範圍內的 `preprocessing/` 與 `momentum/core/` 已為 0 errors。 |
| Task 0.3 pytest | `./venv/bin/pytest tests/feature_engineering/preprocessing -k "d_star_isolation or atomic_write or stale_invalidation or legacy_migration_audit or cache_version_invalid"` | PASS | Exit 0；9 passed, 9 deselected。 |
| Migration dry-run | `python scripts/migrate_d_star_cache.py --dry-run` | PASS | Exit 0；dry-run 找到 1 筆 legacy/audit record；未執行 migrate/quarantine 實體搬移。 |
| Precision regression | `./venv/bin/pytest tests/feature_engineering/preprocessing/test_precision_corr.py -q` | PASS | Exit 0；3 passed，確認 precision cache version 與 mismatch invalidation 仍通過。 |
| New-file focused ruff | `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/_d_star_cache.py scripts/migrate_d_star_cache.py tests/feature_engineering/preprocessing/test_d_star_*.py tests/feature_engineering/preprocessing/test_cache_version_invalid.py` | PASS | Exit 0；All checks passed。 |

### Gate ID 對照

- T0.5: PASS — `test_d_star_isolation.py` 驗證不同 symbol/timeframe 同欄名 cache 檔獨立且 `get()` 不互相干擾。
- T0.6 / C3: PASS — `test_d_star_atomic_write.py` 模擬 100 次 multi-thread 寫入，所有讀回 payload 均為 valid JSON。
- T0.11: PASS — `test_d_star_stale_invalidation.py` 覆蓋 `data_fingerprint`、`feature_schema_hash`、`sample_size`、`nan_policy` 任一變更皆 cache miss。
- T0.12: PASS — `test_d_star_legacy_migration_audit.py` 驗證 legacy `default/default` 只產 audit/quarantine 決策，無 direct hit、無寫回 legacy path。
- T0.B5: PASS — `test_cache_version_invalid.py` 驗證舊 v1 / legacy default cache 不 direct hit，重建後 payload 為 `cache_version: v2`。

### §0 規則確認

- R1.1: PASS — `momentum/FeatureEngineering/preprocessing/` 無 `from api.`。
- R1.2: PASS — 新增 `PreprocessingContext` 使用 `@dataclass(frozen=True)`，無直接 import API service。
- R1.3: N/A for Task 0.3 — batch service 未改；已新增 `momentum.factories.create_feature_preprocessor()` 供後續 Task 0.6 composition-root 使用。
- R1.4: PASS — 新增 `FFACT_DSTAR_CACHE_MIGRATE_LEGACY` 解析集中於 `momentum/core/config.py`。
- R1.5: PASS — 新增測試可單獨以 `./venv/bin/pytest` 執行，不依賴 `run_api.py`。
- Rule 2 Logging: PASS — d_star cache hit/miss summary 使用 `[L6.5]`，cache schema/mismatch log 使用 `[d_star_cache]`；未新增 per-column info log。
- Rule 3 Error Handling: PASS — JSON parse failure、schema mismatch、stale metadata 皆為 cache miss/rebuild；atomic write failure 會 warning，不回寫 legacy path。
- Rule 4 Naming: PASS — 新模組 `_d_star_cache.py`、script `migrate_d_star_cache.py`、cache path `d_star_{SYMBOL}_{TIMEFRAME}_{config_hash[:12]}.json`。
- Rule 5 Type Hints: PASS — 新增函式與類別具 Python 3.9-compatible typing，未使用 `X | Y`。
- Rule 6 Performance: PASS — fingerprint 以 deterministic sample/hash 為主；d_star cache lookup 不在 inner loop 寫 log；chunked path 維持 shared cache 並在最後 flush。
- Rule 7 Fallback: PASS — legacy profile 不恢復 `default/default` cache；legacy cache 只能由 migration script audit/quarantine。
- Rule 8 Git: PASS — 未建立 branch、commit 或 push。

### 已知阻塞 / 警告

- Required broad ruff 仍 BLOCKED：115 個錯誤全部位於既有 `api/services/`，包含 F401 / E402 / F841 / F811。依 Task 0.3 約束「只允許在 TODO 範圍內實作；不改無關區塊」，本批未清理 `api/services/`。
- `python scripts/migrate_d_star_cache.py --dry-run` 會 append audit JSONL 至 `data_cache/feature_preprocessing/d_star_migration_audit.jsonl`；此為 TODO 指定 audit log 副作用，未搬移或改寫 legacy cache 檔。
- Tier 3 / Frozen full-scale baseline 仍屬 U1 Frozen blocker；本 Task 僅完成 Batch 3 development Gate。

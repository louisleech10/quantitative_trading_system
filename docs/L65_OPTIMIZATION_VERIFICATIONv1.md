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

## [Task 0.6] 2026-04-28

### 範圍

- Batch 4: Task 0.6 — Multi-Symbol Batch Hardening。
- 實作 heavy batch process-wide 單一執行、tier-aware `concurrent_symbols`、RAM gate、per-item checkpoint、resume API、WebSocket batch event schema 擴充，以及 per-item RSS / T0.P7 memory sanity 紀錄。
- 保持 Task 0.6 邊界：未新增前端 Batch Panel，未執行 full-scale / Frozen benchmark，未清理既有 `api/services/` ruff 債務。

### 交付物

- `api/services/feature_factory_batch_service.py`
- `api/routes/feature_factory.py`
- `api/models/feature_factory_models.py`
- `api/websocket/feature_factory_ws.py`
- `momentum/FeatureEngineering/utils/hardware_utils.py`
- `momentum/core/config.py`
- `tests/api/test_feature_factory_batch_resume.py`
- `docs/L65_OPTIMIZATION_TODO.md`
- `docs/L65_OPTIMIZATION_VERIFICATIONv1.md`

### Gate 結果

| Gate / Check | Command | Result | Notes |
|---|---|---|---|
| Task 0.6 pytest | `./venv/bin/pytest tests/api/test_feature_factory_batch_resume.py -q` | PASS | 4 passed in 1.99s。`test_checkpoint_failure` 的 `OSError: simulated checkpoint failure` 是預期錯誤注入，用於驗證 checkpoint 寫入失敗時任務不中止。 |
| Batch 4 keyword gate | `./venv/bin/pytest tests -k 'ram_gate or checkpoint_failure or resume_not_found' -q` | PASS | 3 passed, 2097 deselected, 3 warnings in 3.24s。warnings 為既有 pandas `FutureWarning`。 |
| 解耦 grep | `grep -r 'from api\.' momentum/FeatureEngineering/preprocessing/` | PASS | `wc -l` 確認 0；直接 grep exit 1 且無輸出代表 0 matches。 |
| 本次修改檔案 ruff | `./venv/bin/ruff check api/services/feature_factory_batch_service.py api/routes/feature_factory.py api/models/feature_factory_models.py api/websocket/feature_factory_ws.py momentum/FeatureEngineering/utils/hardware_utils.py momentum/core/config.py tests/api/test_feature_factory_batch_resume.py` | PASS | All checks passed。 |
| Required broad ruff | `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/ api/services/ momentum/core/` | BLOCKED | Exit 1；Found 115 errors，61 fixable。前段錯誤位於既有 `api/services/batch_download_service.py`、`case_import_service.py`、`chart_data_service.py`、`chart_signal_service.py` 等非 Task 0.6 修改範圍；本次修改檔案 focused ruff 為 0 errors。 |

### Gate ID 對照

- T0.9: PASS — `test_batch_resume_skips_completed_items` 建立 checkpoint 後 resume，只執行 queued `ETHUSDT`，跳過 completed `BTCUSDT`，route 設計為 `POST /api/v1/features/batch/{batch_id}/resume`。
- T0.B3: PASS — `test_ram_gate` mock available RAM < 4GB，`start_batch()` 回 `HTTPException(status_code=429)`，detail 含 `RAM gate`。
- T0.B4: PASS — `test_checkpoint_failure` mock `_write_checkpoint_atomic()` 拋 `OSError`，service 記錄 error log 但 batch 仍 completed。
- T0.B6: PASS — `test_resume_not_found` 透過 FastAPI route 驗證 invalid batch id 回 404，detail 為 `batch not found`。
- T0.P2 / C-OPT-2: PARTIAL DEV COVERAGE — 已實作 tier table、class-level lock、RAM gate、checkpoint 粒度 `(symbol,timeframe)`、resume skip completed；本輪未執行 8GB `10 symbols x 2 tf reduced` benchmark。
- T0.P7: PARTIAL DEV COVERAGE — checkpoint/WebSocket 已記錄 `rss_before_item_mb`、`rss_peak_item_mb`、`rss_after_gc_mb`，並實作單 item 與 20-item cumulative memory sanity heuristic；本輪未執行長跑 20-item RSS gate。

### §0 規則確認

- R1.1: PASS — `momentum/FeatureEngineering/preprocessing/` 無 `from api.`。
- R1.2: PASS — batch service 只透過 request/checkpoint/context metadata 協調；未在 `momentum/` 中直接 import API service。
- R1.3: PASS — `api/services/feature_factory_batch_service.py` 維持透過 `momentum.factories.create_feature_factory()` 建立 Feature Factory，未直接 `FeaturePreprocessor()`。
- R1.4: PASS — 新增 `FFACT_CONCURRENT_SYMBOLS_OVERRIDE` 與 `FFACT_BATCH_NESTED` 讀取集中於 `momentum/core/config.py`。
- R1.5: PASS — 新增測試可單獨以 `./venv/bin/pytest tests/api/test_feature_factory_batch_resume.py` 執行，不依賴 `run_api.py`。
- Rule 2 Logging: PASS — batch / memory / checkpoint log 使用 `[L6.5]` 前綴；未新增 per-column inner-loop info log。
- Rule 3 Error Handling: PASS — RAM gate 回 429；checkpoint write `OSError` 記錄但不終止；OOM-like item failure 分類為 `oom` 並降載 `concurrent_symbols=1`。
- Rule 4 Naming: PASS — checkpoint 檔名 `batch_state_{batch_id}.json`，函式名稱具體如 `_ram_gate()`、`_safe_persist_checkpoint()`、`get_tier_concurrent_symbols()`。
- Rule 5 Type Hints: PASS — 新增函式使用 Python 3.9-compatible typing，未使用 `X | Y`。
- Rule 6 Performance: PASS — `request.max_workers` 不再決定跨 symbol process fan-out；改由 tier table 控制 outer concurrency，8GB/16GB 預設 1。
- Rule 7 Fallback: PASS — `FFACT_CONCURRENT_SYMBOLS_OVERRIDE` 可覆蓋 tier table；`FFACT_BATCH_NESTED` 會強制 `concurrent_symbols=1` 防止巢狀展開。
- Rule 8 Git: PASS — 未建立 branch、commit 或 push。

### 已知阻塞 / 警告

- Required broad ruff 仍 BLOCKED：115 個錯誤位於既有 `api/services/` 等非 Task 0.6 修改範圍。本批依「不得改動與本 Task 無關區塊」未清理這些歷史 lint 債務；本次修改檔案 ruff 為 PASS。
- Full T0.P2 / T0.P7 performance gate 未執行：使用者本輪指定的 Batch Gate 為 pytest gate；`10 symbols x 2 tf reduced` 與 20-item RSS 長跑需另行排程，且會受本機 8GB 可用 RAM 波動影響。
- `test_checkpoint_failure` 會輸出預期 error log，這是驗證 R10 的錯誤注入，不代表測試失敗。

## [Task 0.7] 2026-04-28

### 範圍

- Batch 5: Task 0.7 — Frontend Batch Panel + Per-Symbol Output。
- 前端顯示 batch 進度、ETA、目前 symbol/timeframe、逐 symbol/timeframe output path、RSS 回收摘要、WebSocket 連線狀態與失敗/partial/paused 時的 resume 按鈕。
- WebSocket 使用既有 `/ws/features/batch/{task_id}` schema，支援 5 秒重連、最多 3 次；未新增後端流程或硬編 symbol list。
- 本批未清理既有 Python ruff 債務，未建立缺失的 `scripts/benchmark_l65.py`。2026-04-28 後續依賴修正已將此工作前移為 Task 0.8，不再等到 Task 3.1 才首次建立。

### 交付物

- `frontend/src/lib/types.ts`
- `frontend/src/store/featureFactoryStore.ts`
- `frontend/src/hooks/useFeatureFactory.ts`
- `frontend/src/components/feature-factory/BatchProgressPanel.tsx`
- `frontend/src/components/feature-factory/GenerationProgress.tsx`
- `frontend/src/components/feature-factory/BatchGenerationPanel.tsx`
- `frontend/src/components/feature-factory/__tests__/BatchProgressPanel.test.tsx`
- `docs/L65_OPTIMIZATION_TODO.md`
- `docs/L65_OPTIMIZATION_VERIFICATIONv1.md`

### Ultra Think 三步驟

- Step 1 初版：擴充 batch 型別與 Zustand batch slice；建立 BatchProgressPanel WebSocket / ETA / output path / resume UI；GenerationProgress 與 BatchGenerationPanel 共用同一面板。
- Step 2 自審：檢查 WebSocket 不因進度更新重連、舊 API polling payload 相容、resume 錯誤不吞掉、`results` 可補成 output paths、無硬編 symbol list、測試 fake timers 不造成假 timeout。
- Step 3 優化：修正 WebSocket effect dependency、補 Vitest WebSocket mock、將 hook 的 batch polling 改為背景備援同步，並修正測試 fake timer / duplicate text 斷言。

### Gate 結果

| Gate / Check | Command | Result | Notes |
|---|---|---|---|
| T0.10 frontend test | `cd frontend && npm run test -- BatchProgressPanel` | PASS | Exit 0；2 passed, 0 failed；耗時約 969ms，測試執行約 130ms。 |
| TypeScript/Pylance edited files | VS Code `get_errors` on edited frontend files | PASS | `types.ts`、store、hook、3 個 component、new test 皆無 error。 |
| 解耦 grep | `grep -r 'from api\.' momentum/FeatureEngineering/preprocessing/` | PASS | Exit 1 且無輸出，代表 0 matches。 |
| Required broad ruff | `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/ api/services/ momentum/core/` | BLOCKED | Exit 1；115 existing errors，61 fixable；主要位於既有 `api/services/` 未使用 import 等，非 Task 0.7 前端修改範圍。 |
| Phase 0 pytest gate | `./venv/bin/pytest tests/feature_engineering tests/api -k l65` | BLOCKED | Exit 5；目前 193 tests deselected、0 selected，表示現有 Python tests 未以 `l65` keyword/marker 命名。替代確認：`./venv/bin/pytest tests/feature_engineering tests/api -k layer_filter` 為 PASS，4 passed、189 deselected。 |
| T0.P1 benchmark command | `scripts/benchmark_l65.py --tier=8gb --max-rows=2000 --max-cols=500 --layers=L1,L2 --repeat=3` | BLOCKED | `scripts/benchmark_l65.py` 不存在；2026-04-28 依賴修正後改由 Task 0.8 先建立最小 benchmark harness，再進 Phase 1。執行代理另以核心 transform 模擬，2.89s / peak RSS 265.41MB / no OOM，但此模擬不可視為正式 Gate PASS。 |
| T0.P2 multi benchmark command | `scripts/benchmark_l65.py --tier=8gb --multi --symbols=10 --tfs=1h,12h --max-rows=2000 --max-cols=500` | BLOCKED | `scripts/benchmark_l65.py` 不存在，原命令不可執行。 |

### Gate ID 對照

- T0.10: PASS — `BatchProgressPanel.test.tsx` 覆蓋進度百分比、完成/失敗計數、ETA、per-symbol output link、RSS 摘要、失敗時 `Resume Batch` 按鈕、WebSocket `batch_progress` event 套用與 5 秒重連。
- T0.P1: BLOCKED — benchmark script 缺失，無法完成正式 8GB repeat gate；未觀察到正式 wall / RSS。
- T0.P2: BLOCKED — benchmark script 缺失，無法完成正式 10 symbols x 2 tf reduced gate。
- T0.P3 / T0.P5 / T0.P7: NOT RUN — Task 0.8 已被新增為 Phase 0 Gate closure 前置，負責補齊這些 Gate；T0.P7 的後端記錄能力已於 Task 0.6 建立，但本批未跑長測。
- C-OPT-5: BLOCKED — `scripts/compare_output_size.py` / formal L7 size gate 不存在於目前 repo，且本批未產生 L7 output。
- C-OPT-6: PASS by scope — 本批只改前端狀態/UI/test，未刪除特徵、未縮減 rolling windows、未改 Feature Factory schema。

### §0 規則確認

- R1.1: PASS — `momentum/FeatureEngineering/preprocessing/` 無 `from api.`。
- R1.2: N/A for Task 0.7 — 未新增 cross-domain context 或後端 domain dependency。
- R1.3: N/A for Task 0.7 — 未改 batch service / FeaturePreprocessor 建立流程。
- R1.4: N/A for Task 0.7 — 未新增 `FFACT_` 環境變數。
- R1.5: PASS — 新增前端 Vitest 可單獨執行；本批未新增 Python test。
- Rule 2 Logging: PASS — 本批未新增 Python logging；前端僅在 WebSocket parse failure 使用 browser console error。
- Rule 3 Error Handling: PASS — WebSocket parse failure 不會中斷 UI；WebSocket close 會 5 秒重連最多 3 次；resume API 失敗會寫入 store error。
- Rule 4 Naming: PASS — 新型別與 action 名稱具體，如 `BatchOutputPath`、`BatchItemRss`、`applyBatchEvent`、`resumeBatch`。
- Rule 5 Type Hints: N/A for Python；TypeScript interface 已完整補齊 batch schema 欄位。
- Rule 6 Performance: PASS — UI 狀態合併使用 Map 去重，未在 render 內做大型資料掃描；hook polling 改為背景備援，不阻塞前端提交流程。
- Rule 7 Fallback: PASS by compatibility — 保留既有 HTTP polling path，WebSocket 更新與 polling payload 共用 normalize 邏輯；不影響 backend fallback env。
- Rule 8 Git: PASS — 未建立 branch、commit 或 push。

### 已知阻塞 / 警告

- Required broad ruff 仍 BLOCKED by existing lint debt：本批為前端 Task，依「不改動與本 Task 無關區塊」未批量修改 `api/services/`。
- `./venv/bin/pytest tests/feature_engineering tests/api -k l65` 仍 BLOCKED：目前 Python tests 沒有 `l65` keyword/marker，需後續統一 test marker 或調整 Gate command。
- `scripts/benchmark_l65.py` 缺失導致 T0.P1/T0.P2 正式 Gate 無法執行；TODO 已於 2026-04-28 修正，新增 Task 0.8 / Batch 5.5 先建立最小 harness 並補齊 Phase 0 Gate，Task 3.1 僅做完整化與 CI 回歸。
- 因上述阻塞，Phase 0 → 1 Gate 尚未完全達成；本批僅能確認 Task 0.7 / T0.10 PASS。

## [TODO Gate Dependency Correction] 2026-04-28

### 決策

- 不允許在 Phase 0 → Phase 1 Gate 未通過時正式進入 Phase 1、Phase 2 或 Phase 3。
- 原 TODO 將 `scripts/benchmark_l65.py` 完整化放在 Task 3.1 / Batch 8，但 Batch 5 → 6 又要求 Phase 0 performance gates 通過；這會形成依賴倒置。
- 修正後新增 Batch 5.5 / Task 0.8：先建立 Phase 0 最小 benchmark harness 與 output size check，完成 T0.P1、T0.P2、T0.P3、T0.P5、T0.P7、C-OPT-5 後，才能進 Batch 6。
- Task 3.1 保留為 benchmark suite 完整化與 CI 回歸，不再作為 Phase 0 首次驗收位置。

### 文件更新

- `docs/L65_OPTIMIZATION_TODO.md`：依賴拓撲新增 Batch 5.5 / Task 0.8。
- `docs/L65_OPTIMIZATION_TODO.md`：Batch 5 快速參考改為只驗 T0.10；Phase 0 Gate 驗收移到 Batch 5.5。
- `docs/L65_OPTIMIZATION_TODO.md`：Phase 0 → Phase 1 Gate 新增硬規則：Gate 未通過時 Batch 6/7/8 均 blocked。
- `docs/L65_OPTIMIZATION_TODO.md`：Task 3.1 改為完整化 / 回歸驗證，不得作為 Phase 0 首次 PASS 依據。

### 狀態

- 文件決策：PASS。
- 程式碼實作：NOT RUN；Task 0.8 尚未執行。
- Phase 0 → Phase 1 Gate：仍 BLOCKED，直到 Task 0.8 實作並通過所有 Tier-A gates。

## [Task 0.8] 2026-04-28

### 範圍

- Batch 5.5: Task 0.8 — Phase 0 Benchmark Harness + Tier-A Gate Closure。
- 建立可直接呼叫的 Phase 0 benchmark harness 與 output size compare script。
- 實作 T0.P1/T0.P2/T0.P3/T0.P5/T0.P7 mode、JSON 結果輸出、d_star cache size 檢查、RSS 記錄、BLOCKED/FAIL/PASS 狀態語意。
- 未開始 Task 1.1 / 1.2；Phase 0 → 1 Gate 未標 PASS，因 T0.P2/T0.P7 仍受本機真實資料數量阻塞。

### 交付物

- `scripts/benchmark_l65.py`
- `scripts/compare_output_size.py`
- `tests/performance/test_l65_phase0_gate.py`
- `tests/feature_engineering/preprocessing/test_l65_phase0_gate.py`
- `benchmark_results/l65/phase0_gate_*.json`
- `benchmark_results/l65/output_size_phase0_*.json`
- `benchmark_results/l65/outputs/*.parquet`
- `data_cache/feature_preprocessing/d_star_*.json`
- `docs/L65_OPTIMIZATION_TODO.md`
- `docs/L65_OPTIMIZATION_VERIFICATIONv1.md`

### Gate 結果

| Gate / Check | Command | Result | Notes |
|---|---|---|---|
| Focused ruff | `./venv/bin/ruff check scripts/benchmark_l65.py scripts/compare_output_size.py tests/performance/test_l65_phase0_gate.py tests/feature_engineering/preprocessing/test_l65_phase0_gate.py` | PASS | Exit 0；All checks passed。 |
| Task 0.8 tests | `./venv/bin/pytest tests/performance/test_l65_phase0_gate.py tests/feature_engineering/preprocessing/test_l65_phase0_gate.py -q --tb=short` | PASS | 4 passed, 2 warnings in 0.19s；warnings 為既有 pandas `FutureWarning: 'H' is deprecated`。 |
| Required L65 pytest Gate | `./venv/bin/pytest tests/feature_engineering tests/api -k l65 -q --tb=short` | PASS | 1 passed, 193 deselected, 1 warning in 1.93s；新增 `tests/feature_engineering/preprocessing/test_l65_phase0_gate.py` 避免 0 selected。 |
| Decoupling grep | `grep -r 'from api\.' momentum/FeatureEngineering/preprocessing/` | PASS | Exit 1 且無輸出，代表 0 matches。 |
| Required broad ruff | `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/ api/services/ momentum/core/` | BLOCKED | Exit 1；115 pre-existing lint errors，主要在既有 `api/services/`；Task 0.8 新檔案 focused ruff 為 0 errors。 |
| T0.P1 | `scripts/benchmark_l65.py --tier=8gb --max-rows=2000 --max-cols=500 --layers=L1,L2 --repeat=3` | PASS | 最新 direct run：wall 1.56s、peak RSS 239MB、3 次皆無 OOM/SIGKILL。實際 real reduced workload 為 2000 rows × 34 cols。 |
| T0.P2 | `scripts/benchmark_l65.py --tier=8gb --multi --symbols=10 --tfs=1h,12h --max-rows=2000 --max-cols=500` | BLOCKED | `data_cache/feature_klines/kline_cache.h5` 僅 BTCUSDT、ETHUSDT 兩個 symbol 同時具備 1h/12h；不可用 synthetic 或重複 symbol 假裝 10 symbols。 |
| T0.P3 | `scripts/benchmark_l65.py --tier=8gb --cache-hit --symbols=ETHUSDT --tfs=1h --max-rows=2000 --max-cols=500 --repeat=2` | PASS | 最新 direct run：wall 1.03s、peak RSS 234MB、cache hit 13/13 = 100%。 |
| T0.P5 | `scripts/benchmark_l65.py --tier=8gb --synthetic --max-rows=1000 --max-cols=100 --full-l65` | PASS | 最新 direct run：wall 2.44s、peak RSS 231MB、無 OOM；output size delta 1.920792%。 |
| T0.P7 | `scripts/benchmark_l65.py --tier=8gb --multi --symbols=10 --tfs=1h,12h --max-rows=2000 --max-cols=500 --memory-sanity` | BLOCKED | 同 T0.P2：真實 HDF5 符合 1h/12h 的 symbol 數量不足 10；memory sanity 長跑 Gate 不可標 PASS。 |
| C-OPT-5 | `scripts/compare_output_size.py --phase=0` | PASS | 最新 direct run：status PASS、result_files_scanned 16、skipped_incompatible_workload 2（64×4 smoke outputs 被排除）、L7 parquet delta 均 ≤5%、d_star JSON 均 ≤5MB。 |

### Gate ID 對照

- T0.P1: PASS — ETHUSDT 1h reduced workload 可跑；wall/RSS 遠低於 Dev Gate 門檻；未發生 OOM/SIGKILL。
- T0.P2: BLOCKED — harness 可執行且正確拒絕不足資料；目前本機真實資料無法形成 10 symbols × 2 tf，不得標 PASS。
- T0.P3: PASS — d_star cache hit rate 達 100%，第二次執行 wall ≤10min。
- T0.P5: PASS — 1000×100 synthetic full-L6.5 wall ≤5min，且 output size 相對 golden baseline 在 ±5% 內。
- T0.P7: BLOCKED — 同 T0.P2，缺 20 item 真實長跑資料，無法驗收 per-item + cumulative RSS sanity。
- C-OPT-5: PASS — `compare_output_size.py` 只比對與 baseline workload row/column 規格相符的正式 artifact；smoke output 不參與 Gate，避免假 fail 或假 pass。

### §0 規則確認

- R1.1: PASS — `momentum/FeatureEngineering/preprocessing/` 無 `from api.`。
- R1.2: PASS — Task 0.8 新增 script/test 未在 `momentum/` 中導入 API service。
- R1.3: N/A — 未新增 API service composition；benchmark 直接呼叫既有 `FeaturePreprocessor` 與 golden helper。
- R1.4: PASS — 未新增 production env parser；benchmark 只在執行期間暫時設定既有 `FFACT_L65_OPTIMIZATION_PROFILE` / `FFACT_FRACDIFF_APPLY_TO_LAYERS`。
- R1.5: PASS — 新增測試可用 `./venv/bin/pytest` 直接執行，不依賴 `run_api.py`。
- Rule 2 Logging: PASS — benchmark 使用既有 momentum logger，未新增 per-column inner-loop info log。
- Rule 3 Error Handling: PASS — missing real data 回 `BLOCKED` 與 exit code 2；fail 回 exit code 1；pass 回 exit code 0。
- Rule 4 Naming: PASS — script、Gate ID、JSON 欄位命名具體；無 placeholder 名稱。
- Rule 5 Type Hints: PASS — 新增 Python typing 維持 Python 3.9-compatible，未使用 `X | Y`。
- Rule 6 Performance: PASS — L6.5 執行沿用向量化 pandas/numpy path；RSS sampler 使用背景 thread 低頻採樣。
- Rule 7 Fallback: PASS — 不以 synthetic-only 替代 ETHUSDT real Gate；資料不足時保留 BLOCKED。
- Rule 8 Git: PASS — 未建立 branch、commit 或 push。

### 已知阻塞 / 警告

- Phase 0 → Phase 1 Gate 仍 BLOCKED：初次 Task 0.8 執行時，T0.P2 與 T0.P7 因 `data_cache/feature_klines/kline_cache.h5` 僅 BTCUSDT、ETHUSDT 同時具備 1h/12h 而未跑；後續 10-symbol retest 見下一節。
- Required broad ruff 仍 BLOCKED by pre-existing lint debt：115 errors，集中於既有 `api/services/`；未在 Task 0.8 範圍內清理。
- `scripts/benchmark_l65.py` direct invocation 會在作為主程式執行時自動 re-exec 到專案 `venv/bin/python`；import 於 pytest 時不 re-exec，避免污染 test collection。
- Task 0.8 benchmark harness 將 d_star cache 固定寫入本 repo `data_cache/feature_preprocessing/`，避免既有 `MomentumConfig.from_project_root()` root 解析把 benchmark artifact 寫到 workspace 外。

## [Task 0.8 Retest] 2026-04-28

### 觸發原因

- 使用者重新下載同一個 `data_cache/feature_klines/kline_cache.h5`，補齊 10 個 symbols，要求重跑前次 BLOCKED 的 Gate。

### 資料檢查

- `data_cache/feature_klines/kline_cache.h5` 目前有 10 個非 metadata symbols：ADAUSDT、BCHUSDT、BNBUSDT、BTCUSDT、DOGEUSDT、ETHUSDT、LINKUSDT、SOLUSDT、TRXUSDT、XRPUSDT。
- 10 個 symbols 均具備 `1h`、`4h`、`12h` timeframes。
- 前次「真實 symbol 數不足」阻塞已解除。

### 重測結果

| Gate / Check | Command | Result | Notes |
|---|---|---|---|
| T0.P2 retest | `scripts/benchmark_l65.py --tier=8gb --multi --symbols=10 --tfs=1h,12h --max-rows=2000 --max-cols=500` | BLOCKED | 重新測試時 available RAM 1.48GB < 4.00GB，RAM gate 正確拒絕新 heavy work；未開始 20-item benchmark。 |
| T0.P7 retest | `scripts/benchmark_l65.py --tier=8gb --multi --symbols=10 --tfs=1h,12h --max-rows=2000 --max-cols=500 --memory-sanity` | BLOCKED | 重新測試時 available RAM 1.52GB < 4.00GB，RAM gate 正確拒絕新 heavy work；memory sanity 長跑仍未完成。 |
| RAM diagnostic | `./venv/bin/python -c 'import psutil; ...'` + `ps -axo pid,comm,rss | sort -nrk3 | head -15` | INFO | total 8.0GB、available 1.56GB、used 80.5%；主要 RSS 來源為 Visual Studio Code 與 Google Chrome 多個 process。 |

### 判定

- T0.P2 / T0.P7 狀態仍為 BLOCKED，但阻塞原因已從「HDF5 symbol 數不足」更新為「當前機器 available RAM 未達 4GB RAM gate」。
- Phase 0 → Phase 1 Gate 仍不可標 PASS；需在 available RAM ≥4GB 時重跑 T0.P2/T0.P7，或在符合 Gate 的 8GB-tier 環境重新執行。

### 2026-04-28 Sequencing Decision

- 使用者確認沒有更高規格機器，且 8GB macOS 重開後也可能長期 `available RAM < 4GB`。
- 決策：不得把 T0.P2/T0.P7 假標 PASS；但也不得因不可達的 4GB RAM gate 永久停止後續研發。
- 後續執行改採雙軌：
  - **Implementation track**：允許進入 Batch 6（Task 1.1 / 1.2）繼續實作與單元/回歸測試。
  - **Gate track**：Phase 0 → Phase 1 Gate、T0.P2、T0.P7 仍維持 BLOCKED / accepted risk，不得標綠；後續每次 benchmark/CI 文件都必須保留此 blocker。
- 理由：Batch 6/7 的目的本身就是改善 L6.5 performance / memory path；若硬等一個此 8GB 環境永遠達不到的 4GB available-RAM 啟動條件，會讓最佳化工作無法前進，反而違背 8GB repeatability 目標。

## [Task 1.1 + 1.2] 2026-04-28

### 範圍

- Batch 6: Task 1.1 — joblib loky slow-path 並行。
- Batch 6: Task 1.2 — Hurst prior + bounded search 取代純二分。
- 僅在 TODO 範圍內修改 L6.5 preprocessing slow path、Hurst prior helper、Phase 1 Gate 所需的最小 benchmark `--phase=1` 支援與對應測試。
- `FFACT_L65_SLOWPATH_PARALLEL` 預設仍為 OFF；Phase 1 benchmark 只在 `--phase=1` 執行期間明確啟用。
- 未清理既有 `api/services/` ruff 債務，未宣稱 T1.4 外部 Hurst reference gate 通過。

### Ultra Think 三步驟

- Step 1 初版：新增 `_slow_path_parallel.py`、`_hurst_prior.py`；在 `FeaturePreprocessor` 中接入可選 loky slow path 與 Hurst bounded d* search；補 `momentum/core/config.py` 的 centralized env parser。
- Step 2 自審：檢查不傳 DataFrame 給 joblib worker、slow path 不再經 ThreadPool 包 statsmodels ADF、Hurst 僅作 prior、所有 fallback 回完整二分或既有 serial/chunked path、Python 3.9 typing、無 `from api.`。
- Step 3 優化：補 focused tests、pickle failure fallback、nested protection、short-series bypass、degenerate fallback、bounded-fail fallback，以及 `scripts/benchmark_l65.py --phase=1` 最小 Gate 支援。

### 交付物

- `momentum/FeatureEngineering/preprocessing/_slow_path_parallel.py`
- `momentum/FeatureEngineering/preprocessing/_hurst_prior.py`
- `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py`
- `momentum/core/config.py`
- `scripts/benchmark_l65.py`
- `tests/feature_engineering/preprocessing/test_slow_path_parallel.py`
- `tests/feature_engineering/preprocessing/test_hurst_prior.py`
- `benchmark_results/l65/phase1_gate_*.json`
- `benchmark_results/l65/outputs/t1_p*_*.parquet`
- `docs/L65_OPTIMIZATION_TODO.md`
- `docs/L65_OPTIMIZATION_VERIFICATIONv1.md`

### Gate 結果

| Gate / Check | Command | Result | Notes |
|---|---|---|---|
| Focused ruff | `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/_hurst_prior.py momentum/FeatureEngineering/preprocessing/_slow_path_parallel.py momentum/FeatureEngineering/preprocessing/feature_preprocessor.py momentum/core/config.py scripts/benchmark_l65.py tests/feature_engineering/preprocessing/test_slow_path_parallel.py tests/feature_engineering/preprocessing/test_hurst_prior.py` | PASS | All checks passed；本次修改檔案 0 errors。 |
| Batch 6 pytest Gate | `./venv/bin/pytest tests/feature_engineering/preprocessing -k "slow_path_parallel or hurst_prior or nested_protection or pickle_fail or hurst_degenerate or short_series_bypass"` | PASS | 9 passed、0 failed、19 deselected。nested protection warning 與 pickle fallback error log 為預期錯誤注入。 |
| 解耦 grep | `grep -r 'from api\.' momentum/FeatureEngineering/preprocessing/ \| wc -l` | PASS | 輸出 `0`。 |
| Required broad ruff | `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/ api/services/ momentum/core/` | BLOCKED | 115 existing errors；集中於既有 `api/services/`，例如 `batch_download_service.py` F401/E402/F841。本次 Batch 6 修改檔案 focused ruff 為 PASS。 |
| T1.P1 Phase 1 benchmark | `scripts/benchmark_l65.py --tier=8gb --phase=1 --max-rows=2000 --max-cols=500` | PASS | 以 `./venv/bin/python scripts/benchmark_l65.py ...` 執行同腳本；exit 0、status PASS、gate_id T1.P1、wall 2.530703s、peak RSS 217MB、blocking_reason 空。 |
| T1.P3 Phase 1 cache-hit benchmark | `./venv/bin/python scripts/benchmark_l65.py --tier=8gb --phase=1 --cache-hit --max-rows=2000 --max-cols=500` | PASS | exit 0、status PASS、gate_id T1.P3、wall 2.801505s、peak RSS 232MB、cache_hit_rate 1.0。 |

### Gate ID 對照

- T1.1: PASS — `ParallelSlowPath(2)` 與 serial path 產出的 d_star 完全一致，FracDiff values `np.allclose(..., equal_nan=True)`。
- T1.2: PASS — `FFACT_BATCH_NESTED=1` 時 `get_slowpath_n_jobs(8)` 強制回 1；預設 `FFACT_L65_SLOWPATH_PARALLEL` 未設定時也回 1。
- T1.3: PASS — Hurst prior 測試覆蓋 bounded search，call_count unique d ≤ 5，bounded fail fallback 回完整搜尋。
- T1.4: BLOCKED / not pass — 目前缺 Mansukhani R/S 或 DFA 外部 reference 與 200+ 金融時序抽樣；依 ARH-2 不可標 PASS，也不可宣稱 Hurst estimator reference gate 完成。
- T1.B1: PASS — 模擬 joblib pickle failure，`FeaturePreprocessor` 記錄 fallback error 並回既有 serial/chunked slow path；未新增 per-column ThreadPool ADF。
- T1.B2: PASS — 全常數 degenerate series 不啟用 prior，回完整搜尋。
- T1.B3: PASS — series 長度 < 100 時 bypass prior，回完整搜尋。
- T1.P1: PASS — 8GB Phase 1 short-window wall ≤30min、peak RSS≤6GB；實測 wall 2.53s、peak RSS 217MB。
- T1.P3: PASS — 8GB Phase 1 cache-hit ≤5min；實測 wall 2.80s、cache hit 100%。
- C5: PASS by implementation/test — joblib worker 只接收 `np.ndarray` 與 metadata dict；未傳整張 DataFrame。

### §0 規則確認

- R1.1: PASS — `momentum/FeatureEngineering/preprocessing/` 無 `from api.`。
- R1.2: PASS — 本批未新增跨 Domain service import；Hurst / slow-path helper 皆為 preprocessing internal module。
- R1.3: N/A for Batch 6 — 未修改 `api/services/feature_factory_batch_service.py` 的 preprocessor 建立流程。
- R1.4: PASS — 新增 `FFACT_L65_SLOWPATH_PARALLEL` 解析集中於 `momentum/core/config.py`；未在 preprocessing 模組直接讀此 env。
- R1.5: PASS — 新增 pytest 可單獨用 `./venv/bin/pytest tests/feature_engineering/preprocessing -k ...` 執行，不依賴 `run_api.py`。
- Rule 2 Logging: PASS — joblib completion / fallback 以 group summary log；未新增 per-column info log。測試中的 error log 為預期 pickle fallback 注入。
- Rule 3 Error Handling: PASS — joblib OOM-like error 轉 `MemoryError` 向上拋給 batch downscale；pickle / non-OOM failure 回 serial/chunked slow path；Hurst invalid/bounded fail/short series 回完整二分。
- Rule 4 Naming: PASS — 新 internal modules `_slow_path_parallel.py`、`_hurst_prior.py`；函式名稱具體如 `process_fracdiff_column_values`、`find_min_d_with_prior`、`get_slowpath_n_jobs`。
- Rule 5 Type Hints: PASS — 新增函式與測試 typing 維持 Python 3.9-compatible，未使用 `X | Y`。
- Rule 6 Performance: PASS — slow path loky 僅處理單欄 ndarray；BLAS thread env 在 loky map 期間設為 1；registry slow path 不再經 ThreadPool full-groups 包 statsmodels ADF。
- Rule 7 Fallback: PASS — `FFACT_L65_SLOWPATH_PARALLEL=0` / unset 時回既有 serial path；default OFF 未改；legacy d_star shared cache 未恢復。
- Rule 8 Git: PASS — 未建立 branch、commit 或 push。

### 已知阻塞 / 警告

- Required broad ruff 仍 BLOCKED by pre-existing lint debt：115 errors 位於既有 `api/services/` 等非 Batch 6 修改範圍；依「不改動與本 Task 無關區塊」未清理。
- T1.4 仍為 BLOCKED / not pass：`compare_hurst_estimators()` 在未提供 external reference estimator 時會回 `blocked_not_pass=1.0`，測試只確認不會假標 PASS。
- Phase 1 → Phase 2 Gate 不可宣稱完全全綠：development command gate 已通過，但 ARH-2 外部 reference gate 仍需 reviewer / 外部資料補測。

## [Task 2.1 + 2.2] 2026-04-28

### 範圍

- Batch 7: Task 2.1 — Numba Fast ADF 實作。
- Batch 7: Task 2.2 — 1000+ 真實樣本 Fast ADF 驗證 Gate。
- Fast ADF 維持預設 OFF；僅在 `FFACT_USE_FAST_ADF=1` 或 `scripts/benchmark_l65.py --phase=2` gate env 中啟用。
- 本批未清理既有 `api/services/` ruff 債務，未執行 16/24/32GB full-scale / Frozen Gate。

### 交付物

- `momentum/FeatureEngineering/preprocessing/_fast_adf_numba.py`
- `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py`
- `momentum/FeatureEngineering/preprocessing/_slow_path_parallel.py`
- `momentum/core/config.py`
- `benchmark/adf.py`
- `scripts/benchmark_l65.py`
- `tests/feature_engineering/preprocessing/test_fast_adf_synthetic.py`
- `tests/feature_engineering/preprocessing/test_fast_adf_gate.py`
- `tests/golden/l65/fast_adf_gate_report.json`
- `docs/L65_OPTIMIZATION_TODO.md`
- `docs/L65_OPTIMIZATION_VERIFICATIONv1.md`

### Gate 結果

| Gate / Check | Command | Result | Notes |
|---|---|---|---|
| Fast ADF pytest | `./venv/bin/pytest tests/feature_engineering/preprocessing -k "fast_adf" -q` | PASS | 7 passed, 28 deselected；無 skipped。測試中有一條預期的 invalid `FFACT_USE_FAST_ADF` 格式 warning。 |
| T2.V1 report | `tests/golden/l65/fast_adf_gate_report.json` | PASS | `sample_count=1200`、`classification_agreement=1.0`、`d_star_median_diff=0.0`、`d_star_p95_diff=0.0`、`threshold_band_violations=0.0`、`final_dstar_corr_vs_baseline=1.0`。 |
| T2.P2 / T2.P2a | `python -m benchmark.adf` | PASS | Exit 0；Fast ADF mean 0.246ms、p99 0.475ms、fallback_count 0；MacKinnon mean 0.035ms、p99 0.118ms。 |
| T2.P1 | `scripts/benchmark_l65.py --phase=2 --max-rows=2000 --max-cols=500` | PASS | Exit 0；`gate_id=T2.P1`、wall 2.281692s、peak RSS 250MB、cache hit 1.0、blocking_reason 空字串。 |
| 解耦 grep | `grep -r 'from api\.' momentum/FeatureEngineering/preprocessing/` | PASS | Exit 1 且無輸出，代表 0 matches。 |
| Required broad ruff | `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/ api/services/ momentum/core/` | BLOCKED | Exit 1；`momentum/FeatureEngineering/preprocessing/` 與 `momentum/core/` 為 0 issues，失敗全在既有 `api/services/` 多檔 lint 債務。 |
| 本次修改檔案 ruff | `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/_fast_adf_numba.py momentum/FeatureEngineering/preprocessing/feature_preprocessor.py momentum/FeatureEngineering/preprocessing/_slow_path_parallel.py momentum/core/config.py scripts/benchmark_l65.py benchmark/adf.py tests/feature_engineering/preprocessing/test_fast_adf_synthetic.py tests/feature_engineering/preprocessing/test_fast_adf_gate.py` | PASS | Exit 0；All checks passed。 |

### Gate ID 對照

- T2.1: PASS — 100 個合成 stationary / non-stationary 樣本 classification 100% match statsmodels fixed-lag reference。
- T2.V1: PASS — 1200 個真實 HDF5 派生樣本跨 `ETHUSDT/BTCUSDT/BNBUSDT/SOLUSDT`、`1h/12h`、L1/L2/L3、price-like/return/rank/zscore strata，全 metric 通過。
- T2.B1: PASS — constant / singular design fallback statsmodels，p-value 安全回 1.0。
- T2.B2 / C4: PASS — p-value 落在 `[0.08, 0.12]` 時強制 statsmodels fallback，gate report `threshold_band_violations=0`。
- T2.B3: PASS — series 含 NaN 時 fallback statsmodels。
- T2.P1: PASS — Phase 2 short-window wall 2.28s ≤ 15min、peak RSS 250MB ≤ 6GB。
- T2.P2: PASS — 10000 calls Fast ADF mean 0.246ms ≤ 5ms、p99 0.475ms ≤ 15ms。
- T2.P2a / ARH-3: PASS — 10000 calls `mackinnonp` mean 0.035ms ≤ 1ms、p99 0.118ms ≤ 2ms。
- T2.P3 / T2.F1: NOT RUN — 16/24/32GB full-scale 與 Frozen Gate 仍需外部環境或 full-width proxy；不可宣稱 Frozen。

### §0 規則確認

- R1.1: PASS — `momentum/FeatureEngineering/preprocessing/` 無 `from api.`。
- R1.2: PASS — 本批新增 Fast ADF internal helper，未新增跨 Domain service import。
- R1.3: N/A for Batch 7 — 未修改 `api/services/feature_factory_batch_service.py` 的 preprocessor 建立流程。
- R1.4: PASS — 新增 `FFACT_USE_FAST_ADF` 解析集中於 `momentum/core/config.py`；preprocessing 模組透過 `get_fast_adf_enabled()` 讀取。
- R1.5: PASS — 新增 pytest 可單獨用 `./venv/bin/pytest tests/feature_engineering/preprocessing -k "fast_adf"` 執行，不依賴 `run_api.py`。
- Rule 2 Logging: PASS — 未新增 per-column info log；Fast ADF fallback 不在 hot loop 輸出 info。
- Rule 3 Error Handling: PASS — NaN、singular / `LinAlgError`、condition number > 1e10、threshold band 皆 fallback statsmodels。
- Rule 4 Naming: PASS — 新 internal module `_fast_adf_numba.py`；API 名稱 `adf_pvalue_fast()` 與輸出 p-value 一致。
- Rule 5 Type Hints: PASS — 新增函式與測試 typing 維持 Python 3.9-compatible，未使用 `X | Y`。
- Rule 6 Performance: PASS — ADF core 使用 Numba `@njit(cache=True, fastmath=False)`；statsmodels fallback 僅用於風險邊界。
- Rule 7 Fallback: PASS — `FFACT_USE_FAST_ADF=0` / unset 時維持 statsmodels；Fast ADF d_star cache 使用 `fast-adf-numba-v1` engine version 隔離，不重用 statsmodels d_star cache。
- Rule 8 Git: PASS — 未建立 branch、commit 或 push。

### 已知阻塞 / 警告

- Required broad ruff 仍 BLOCKED：失敗集中於既有 `api/services/` lint 債務；本批修改檔案 focused ruff 為 0 errors。依「不改動與本 Task 無關區塊」未清理 unrelated service 檔。
- T2.P3 / T2.F1 未執行：需外部 16/24/32GB 或 full-width proxy；目前只能宣稱 development gate PASS，不可宣稱 Phase 2 Frozen。
- `tests/golden/l65/fast_adf_gate_report.json` 為 runtime 覆寫 report，最近一次狀態為 PASS。

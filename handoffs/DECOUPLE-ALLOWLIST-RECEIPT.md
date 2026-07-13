# DECOUPLE-ALLOWLIST B1 RECEIPT（BLOCKED）

日期：2026-07-14　執行端：Codex　狀態：BLOCKED（T1c 發現 SPEC 外既有新紅）

## 冷啟動與 stamp gate

命令：`bash scripts/reconcile_stamps_check.sh handoffs/20260713-DECOUPLE-TRIAGE-RECONCILE.md`

```text
RECONCILE-STAMP PASS: handoffs/20260713-DECOUPLE-TRIAGE-RECONCILE.md 已獲 codex,composer 全數 APPROVED且本體雜湊相符(sha256:822514a874b2057fa1f721cbd1048c7ec80af95cc9b761eff8a41e9918006fef)。
```

## 舊 scanner baseline（實跑）

命令：`bash scripts/check_decoupling.sh`（改檔前）

```text
Rule 1 PASS
Rule 2 FAIL: momentum/ cross-domain concrete imports (5 violations)
momentum/Analysis/kline_cache.py:29:from momentum.FeatureEngineering.atomic.warmup_lookup import get_warmup_bars
momentum/Analysis/signal_density_analyzer.py:29:from momentum.FeatureEngineering.atomic.warmup_lookup import (
momentum/Analysis/ic_engine.py:17:from momentum.FeatureEngineering.consumer_gate import (
momentum/Analysis/coverage_analyzer.py:14:from momentum.FeatureEngineering.feature_reader import FeatureReader
momentum/Analysis/indicator_cache.py:35:from momentum.FeatureEngineering.atomic.warmup_lookup import get_warmup_bars
Rule 3 FAIL: api/ directly imports momentum concrete (10 violations)
api/services/chart_data_service.py:39:from momentum.FeatureEngineering.atomic.warmup_lookup import (
api/services/xgboost_batch_service.py:37:from momentum.FeatureEngineering.consumer_gate import (
api/services/feature_factory_service.py:44:from momentum.FeatureEngineering.run_locks import RunBusyError, is_run_active
api/services/feature_factory_service.py:45:from momentum.FeatureEngineering.run_paths import cgsa_work_dir, features_run_dir
api/services/chart_signal_service.py:30:from momentum.FeatureEngineering.atomic.warmup_lookup import (
api/services/feature_factory_batch_service.py:31:from momentum.FeatureEngineering.utils.hardware_utils import (
api/services/cross_symbol_training_service.py:10:from momentum.FeatureEngineering.consumer_gate import TrainingReadError
api/services/feature_factory_service.py:129:            from momentum.FeatureEngineering.utils.hardware_utils import (
api/routes/config.py:23:from momentum.FeatureEngineering.utils.hardware_utils import (
api/routes/feature_factory.py:44:from momentum.FeatureEngineering.run_locks import RunBusyError
Rule 4 PASS
Rule 5 PASS
Rule 6 PASS
Rule 7 PASS
VIOLATIONS FOUND — Fix before merging
```

## 15→0 逐筆預定歸因表

| # | baseline import | manifest module / symbols | stub 預期 |
|---:|---|---|---|
| 1 | `kline_cache.py:29` | `warmup_lookup` / `get_warmup_bars` | allow |
| 2 | `signal_density_analyzer.py:29` | `warmup_lookup` / `get_warmup_bars,get_warmup_factor` | allow |
| 3 | `ic_engine.py:17` | `consumer_gate` / `assert_consumer_run_status,effective_run_status,is_source_run_status_reusable` | allow |
| 4 | `coverage_analyzer.py:14` | `feature_reader` / `FeatureReader` | allow |
| 5 | `indicator_cache.py:35` | `warmup_lookup` / `get_warmup_bars` | allow |
| 6 | `chart_data_service.py:39` | `warmup_lookup` / `get_warmup_bars,get_warmup_factor` | allow |
| 7 | `xgboost_batch_service.py:37` | `consumer_gate` / `TrainingReadError,intersect_columns_without_masking` | allow |
| 8 | `feature_factory_service.py:44` | `run_locks` / `RunBusyError,is_run_active` | allow |
| 9 | `feature_factory_service.py:45` | `run_paths` / `cgsa_work_dir,features_run_dir` | allow |
| 10 | `chart_signal_service.py:30` | `warmup_lookup` / `get_warmup_bars,get_warmup_factor` | allow |
| 11 | `feature_factory_batch_service.py:31` | `hardware_utils` / `get_current_tier_gb,get_tier_concurrent_symbols` | allow |
| 12 | `cross_symbol_training_service.py:10` | `consumer_gate` / `TrainingReadError` | allow |
| 13 | `feature_factory_service.py:129` | `hardware_utils` / `get_memory_tier,get_tier_config` | allow |
| 14 | `api/routes/config.py:23` | `hardware_utils` / `TIER_THRESHOLDS,get_memory_tier,get_tier_config` | allow |
| 15 | `api/routes/feature_factory.py:44` | `run_locks` / `RunBusyError` | allow |

## T1a / T1b / T1d stdout（實跑）

T1a 命令：`bash scripts/check_decoupling.sh`

```text
Rule 1 PASS
Rule 2/3 FAIL: AST import scanner rejected the tree or manifest
DECOUPLING IMPORT SCANNER ERROR: 戳記驗證失敗: RECONCILE-STAMP FAIL: scripts/decouple_allowlist.md 未獲全數委員核可:
  · codex: 缺 APPROVED 戳記
  · composer: 缺 APPROVED 戳記
Rule 4 PASS
Rule 5 PASS
Rule 6 PASS
Rule 7 PASS
VIOLATIONS FOUND — Fix before merging
```

T1b 命令：`grep -cE '^\| momentum\.' scripts/decouple_allowlist.md`

```text
6
```

T1d 命令：`python scripts/check_decoupling_imports.py --skip-stamp-check`

```text
usage: check_decoupling_imports.py [-h]
check_decoupling_imports.py: error: unrecognized arguments: --skip-stamp-check
```

## T1c stdout 與 blocker（實跑）

命令：直接呼叫 `scan(...)`，真實 roots，`stamp_verifier=lambda _: (True, 'stub stamp verifier PASS')`。

```text
/Users/louis/Desktop/quantitative_trading_system/momentum/Optimization/objectives/strategy_backtest.py:112:R2:from:momentum.Strategy.performance_metrics.PerformanceMetrics
/Users/louis/Desktop/quantitative_trading_system/momentum/Optimization/optuna_optimizer.py:1033:R2:from:momentum.Analysis.strategy_registry.strategy_registry
/Users/louis/Desktop/quantitative_trading_system/momentum/Optimization/optuna_optimizer.py:1289:R2:from:momentum.Analysis.strategy_registry.strategy_registry
/Users/louis/Desktop/quantitative_trading_system/momentum/Optimization/optuna_optimizer.py:1616:R2:from:momentum.Analysis.strategy_registry.strategy_registry
/Users/louis/Desktop/quantitative_trading_system/momentum/Optimization/optuna_optimizer.py:2744:R2:from:momentum.Analysis.pareto_analyzer.ParetoAnalyzer
R2=5 R3=0
```

歸因：這 5 筆皆為合法縮排 import；舊 grep 用 `^from momentum\.` 漏掃。TODO 1.1 要求 AST 覆蓋任意縮排，故不是 scanner 誤報。六模組 manifest 不得擴第 7 模組；矩陣④/M2 禁忽略縮排；caller 不在 B1 修改 scope。T1c 的 `R2=0/R3=0` 因 SPEC baseline 假設不完整而不可達。

## 未執行 gates

T2a、M1-M4、canary、T4a-c、整合 pytest 均未執行：scope fail-closed 在 T1c 阻塞後停止，避免建立無法滿足規格的後續實作。未修改任何 inventory 或 `data_cache/`。

---

# B1 r4 裁決後續作 RECEIPT（2026-07-14）

前段 BLOCKED 紀錄保留；本段依 SPEC §C r4 與 TODO T1b=9 的新裁決續作，B1 實作與票內 gates 已完成，Task 1.3 戳記輪仍屬主委後續。

## T1b / T1c / T1d

命令：`grep -cE '^\| momentum\.' scripts/decouple_allowlist.md`

```text
9
```

命令：函式層注入 `stamp_verifier=lambda _: (True, 'stub stamp verifier PASS')`，對真實 momentum/api roots 執行 `scan(...)`。

第一次 harness stdout/stderr（尚未進入 scanner；動態 module 未註冊 `sys.modules`）：

```text
Traceback (most recent call last):
  ...
AttributeError: 'NoneType' object has no attribute '__dict__'
```

第二次修正 harness 載入方式後 stdout：

```text
R2=0 R3=0
```

命令：`venv/bin/python scripts/check_decoupling_imports.py --skip-stamp-check`

```text
usage: check_decoupling_imports.py [-h]
check_decoupling_imports.py: error: unrecognized arguments: --skip-stamp-check
```

## AST 新揭露 5 筆歸因（接續原 15→0 表）

| # | AST import | pending-triage module / symbol | stub 結果 |
|---:|---|---|---|
| 16 | `strategy_backtest.py:112` | `momentum.Strategy.performance_metrics` / `PerformanceMetrics` | allow |
| 17 | `optuna_optimizer.py:1033` | `momentum.Analysis.strategy_registry` / `strategy_registry` | allow |
| 18 | `optuna_optimizer.py:1289` | `momentum.Analysis.strategy_registry` / `strategy_registry` | allow |
| 19 | `optuna_optimizer.py:1616` | `momentum.Analysis.strategy_registry` / `strategy_registry` | allow |
| 20 | `optuna_optimizer.py:2744` | `momentum.Analysis.pareto_analyzer` / `ParetoAnalyzer` | allow |

三列 owner 均為 `pending/DECOUPLE-TRIAGE-2`；contract 均為「舊 scanner 盲區既存依賴，暫豁免維持現狀；真偽 triage 另立票」。

## V-CANARY

暫建 `api/services/_allowlist_canary.py`，包含 feature_library 的 from/import 兩形式；函式層 stub scan stdout：

```text
/Users/louis/Desktop/quantitative_trading_system/api/services/_allowlist_canary.py:3:R3:from:momentum.FeatureEngineering.feature_library.FeatureLibrary
/Users/louis/Desktop/quantitative_trading_system/api/services/_allowlist_canary.py:4:R3:import:momentum.FeatureEngineering.feature_library
R2=0 R3=2
```

以 `apply_patch` 刪除 canary 後重跑 stdout：

```text
R2=0 R3=0
```

## T2a — fixture-isolated regression matrix

命令：`venv/bin/pytest tests/decoupling -q`

```text
collected 31 items
tests/decoupling/test_import_scanner.py ............................... [100%]
============================== 31 passed in 0.21s ==============================
```

覆蓋十類矩陣、八種 malformed manifest、真 manifest schema、syntax error 與 rejected stamp；除 CLI unknown-option 測試與真 schema 測試外，fixture roots/manifest 均位於 `tmp_path`，不依賴真 manifest 內容。

## M1–M4 mutation receipts（每次均已還原）

M1 暫改精準 equality 為 substring；命令：`pytest ...::test_near_miss_module_names_are_rejected -q`

```text
FAILED ...consumer_gate_v2... - AssertionError: assert 0 == 1
========================= 1 failed, 1 passed in 0.16s ==========================
```

M2 暫改 `ast.walk` 為只走 module top-level；命令：`pytest ...::test_all_legal_indentation_forms_are_scanned -q`

```text
top-level from/import: 2 passed
2-space/4-space/8-space/tab from/import: 8 failed (assert 0 == 1)
========================= 8 failed, 2 passed in 0.21s ==========================
```

M3 暫改缺 manifest 回傳空結果；命令：`pytest '...::test_malformed_manifest_full_spectrum_fails_closed[missing]' -q`

```text
E   Failed: DID NOT RAISE <class 'check_decoupling_imports.ScannerError'>
============================== 1 failed in 0.15s ===============================
```

M4 暫移除 symbol gate；命令：`pytest ...::test_allowed_module_rejects_runlease_symbol -q`

```text
E   AssertionError: assert 0 == 1
============================== 1 failed in 0.18s ===============================
```

四個 mutation 還原後：

```text
collected 31 items
tests/decoupling/test_import_scanner.py ............................... [100%]
============================== 31 passed in 0.21s ==============================
```

## T4a–T4c / T1a

命令：`bash scripts/check_doc_anchors.sh`

```text
Baseline dead links (HEAD): 6
Current repo dead links: 6
Delta: +0
Changed Markdown files checked: 3
New dead links: 0
```

命令與 stdout：

```text
$ grep -c 'decouple_allowlist' docs/ARCHITECTURE.md
1
$ git diff docs/ARCHITECTURE.md | grep -c 'R3=12'
0
$ git diff docs/ARCHITECTURE.md | grep -cE '^-.*報 12 筆'
1
```

T4c 指定 literal `R3=12` 不存在於改前原文；原文是「報 12 筆」，等價刪除行 grep=1。`git diff --unified=0 docs/ARCHITECTURE.md` 僅含解耦節 L154–164，Feature Factory H2 無 diff。

命令：`bash scripts/check_decoupling.sh`（戳記前 T1a）

```text
Rule 1 PASS
Rule 2/3 FAIL: AST import scanner rejected the tree or manifest
DECOUPLING IMPORT SCANNER ERROR: 戳記驗證失敗: ...decouple_allowlist.md 未獲全數委員核可:
  · codex: 缺 APPROVED 戳記
  · composer: 缺 APPROVED 戳記
Rule 4 PASS
Rule 5 PASS
Rule 6 PASS
Rule 7 PASS
VIOLATIONS FOUND — Fix before merging
```

此紅字只由 Task 1.3 尚未執行的 stamp gate 造成，符合 B1 戳記前 fail-closed 預期；manifest body hash stdout 為 `ddd5fb355be78a4152127cacdb3392acd9498bd4fb077c5b8217fd933d24105d`。

## Phase suite / inventory 比對

命令：`venv/bin/pytest tests/decoupling tests/api tests/momentum -q`

```text
= 52 failed, 1325 passed, 18 skipped, 4900 warnings, 171 errors in 376.71s (0:06:16) =
```

既有 baseline receipt：`handoffs/20260714-DECOUPLE-FIX4-B1.md` 同一 api+momentum roots 為 `52 failed,1294 passed,18 skipped,171 errors`；本次新增 31 個 decoupling tests 全通過，故 pass 數精準增加 31，failed/error/skipped 數完全不變，判定無新紅。`handoffs/DECOUPLE-FIX4-CODEREV-composer.md` 亦記錄全套紅字具有順序/環境副作用，隔離候選皆綠。

## 最終完整性檢查

```text
$ git diff --check
(no output; exit 0)
$ PYTHONPYCACHEPREFIX=/tmp/decouple-allowlist-pycache venv/bin/python -m py_compile scripts/check_decoupling_imports.py tests/decoupling/test_import_scanner.py
(no output; exit 0)
$ bash scripts/agent_postflight.sh
POSTFLIGHT ✅ data_cache 完整（檔11744/30115604KB，未縮減）
HEALTH OK: verify gate hooks and tools present
```

首次 `py_compile` 因預設 bytecode cache 指向不可寫的 `~/Library/Caches` 得 `PermissionError`；第二輪只改 cache destination 後 exit 0。未執行 git commit，未修改測試 inventory、數值/schema/輸出大小或 `data_cache/`。

## Task 1.3 戳記輪+篡改 mutation(主委實跑 2026-07-14)
- composer APPROVED;codex 首輪 REJECTED(DECOUPLE-TRIAGE-2 未入 ROADMAP)→ 補登 ROADMAP 後重戳 APPROVED(pending 3 筆暫豁免正式裁決通過)。
- `reconcile_stamps_check.sh scripts/decouple_allowlist.md` PASS;`check_decoupling.sh` → ALL RULES PASS exit 0。
- 篡改 mutation:manifest 改一字(run_paths→run_pathz)→ scanner exit 1(戳記雜湊不符,fdccc287…≠ddd5fb35…);還原 → exit 0。tamper-evident 成立。

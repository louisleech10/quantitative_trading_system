# B1 Worker Logging — Composer 實作收尾

**SPEC**: `docs/B1_WORKER_LOGGING_SPEC.md` | **TODO**: `docs/B1_WORKER_LOGGING_TODO.md`  
**日期**: 2026-06-21 | **執行端**: Composer 2.5

## 修改檔案

| 檔案 | 變更 |
|---|---|
| `api/core/logging.py` | 新增 `init_worker_logging(path,symbol,tf)`、`_WorkerContextFilter`、idempotent marker |
| `api/services/feature_factory_batch_service.py` | Task1.1 `FFACT_API_LOG_PATH` 設/還原；Task2.1 `_compute_single` 入口呼叫；ProcessPool 建構失敗外層 `finally` 還原 |
| `tests/api/test_worker_logging.py` | 13 測（含 adv#1–#6 + smoke 1–4 子） |
| `tests/api/worker_logging_smoke_worker.py` | picklable 子進程 smoke worker |

## Codex adversarial 6 修補對應

| # | 處理 |
|---|---|
| adv#1 idempotent | `_ffact_worker_log_handler` marker；`_has_worker_log_handler()` 掛前檢查；`test_init_worker_logging_idempotent_single_line` |
| adv#2 不衝突 | 掛 `momentum`/`api` namespace（子進程 root=WARNING 且不得改 root level）；只 add handler；`test_init_worker_logging_preserves_existing_handlers` |
| adv#3 smoke | 父+1~4 子真 `FileHandler` 寫 JSON（padding 200）；`json.loads` 完整 id set；`test_worker_logging_smoke_multiprocess_append[1-4]` |
| adv#4 fail-open | setup 全包 try/except；`FileHandler` raise 仍生成；`generate_features` raise 仍 `RuntimeError` 計算失敗 |
| adv#5 diff scope | **未改** `generate_features` 參數/cache path/config_override；僅入口 logging + env |
| adv#6 env 還原 | previous None/value 兩測 + `ExplodingExecutor` ProcessPool 建構失敗還原；外層 `try/finally _restore_wave_env` |

## 驗證結果

```
pytest tests/api/ -k "worker_logging or worker_log_env" → 13 passed
python scripts/build_l65_golden_baseline.py --check → PASS (6 symbol×tf stable)
```

## smoke 結果

- child_count=1..4：每輪父+ N 子共 N+1 行，全可 `json.loads`，id set 完整，無 duplicate/partial
- 行長含 formatter + `[pid sym tf]` + 200 char padding

## byte check

`build_l65_golden_baseline.py --check` PASS — logging 未污染 L6.5 數值。

## diff scope 自證（adv#5）

`_compute_single` 僅新增 6 行（讀 `FFACT_API_LOG_PATH` → `init_worker_logging`）。`factory.generate_features(...)` 區塊（symbol/timeframe/config_override/force_regenerate/progress_callback/batch_id）**零改動**。

**設計備註**：子進程 root 預設 WARNING，掛 root 無法收 INFO 且 adv#2 禁改 root level → handler 掛 `momentum`+`api` logger（仍涵蓋 momentum.*/api.*，同一 FileHandler 實例）。

# IC1C-B0 RESULT — Task 0.1 G-OLD baseline 凍結

**task-id**: IC1C-B0  
**agent**: Grok (實作執行端)  
**date**: 2026-07-14  
**TODO**: docs/IC1C_NETIC_TODO.md Frozen r6 Task 0.1 / §B B0→B1 Gate  
**status**: DONE

## 產出檔

| 路徑 | 說明 |
|------|------|
| `scripts/ic1c_freeze_baseline.py` | `--baseline old\|new\|new2`；本批實作 old；new/new2 → NotImplementedError |
| `scripts/ic1c_validate_baseline.py` | 獨立 validator（T-F5 producer 不得自證） |
| `handoffs/ic1c_baseline/g_old.json` | G-OLD 全量輸出 + lineage |
| `handoffs/ic1c_baseline/g_old.sha256` | `6e23ff632cb9153b6f2b803bfc607a033151efa3b57a0fa22ac5ec91bdc36179` |

## 實作摘要（對齊 Task 0.1 入口偽碼）

1. fixture：`tests/fixtures/ic_api_real_kline.py` → `build_real_kline_frames` + 真 kline `data_cache/feature_klines/kline_cache.h5`（ETHUSDT/12h）
2. `summary={feat:{"ic_mean":spearman(feat,label)}}`（feature 名排序）
3. `turnover_data={feat: TurnoverAnalyzer.compute_quantile_turnover(...)}`
4. skipped 注入：`turnover_data.pop("oc_return")`；`summary["hl_range"]["ic_mean"]=float("nan")`
5. `NetICAnalyzer(現行 default config).batch_analyze(summary, turnover_data)` — **不跑 full deep pipeline**
6. `json.dumps(sort_keys=True, allow_nan=False)`；非有限 → null + `non_finite_fields`
7. lineage 頂層：`fixture_sha256` / `git_head` / `generated_by="ic1c_freeze_baseline --baseline old"`
8. **零程式碼變更**：未改 `momentum/` `api/` `frontend/` 任何既有檔

## 驗證命令與 stdout（逐字）

### CMD A — Task 0.1 驗證 / §B B0→B1 Gate

```
$ python scripts/ic1c_freeze_baseline.py --baseline old && python scripts/ic1c_validate_baseline.py handoffs/ic1c_baseline/g_old.json && shasum -a 256 -c handoffs/ic1c_baseline/g_old.sha256
[2026-07-14 17:08:41,205] INFO momentum.FeatureEngineering.strategy_registry: ✅ 成功註冊 EMAExtractor
/Users/louis/Desktop/quantitative_trading_system/venv/lib/python3.9/site-packages/joblib/_multiprocessing_helpers.py:44: UserWarning: [Errno 1] Operation not permitted.  joblib will operate in serial mode
  warnings.warn("%s.  joblib will operate in serial mode" % (e,))
2026-07-14 17:08:42,614 - momentum.Indicators.indicator_engine - INFO - Registered indicator: ema -> EMAIndicator
2026-07-14 17:08:42,915 - momentum.DataExtraction.kline_storage - INFO - KlineStorageManager initialized: /Users/louis/Desktop/quantitative_trading_system/data_cache/feature_klines/kline_cache.h5
2026-07-14 17:08:42,920 - momentum.DataExtraction.kline_storage - INFO - Read 1696 klines from ETHUSDT/12h in 0.004s
wrote handoffs/ic1c_baseline/g_old.json
sha256=6e23ff632cb9153b6f2b803bfc607a033151efa3b57a0fa22ac5ec91bdc36179
features=7
non_finite_fields=5
2026-07-14 17:08:44,517 - momentum.Indicators.indicator_engine - INFO - Registered indicator: ema -> EMAIndicator
[2026-07-14 17:08:44,561] INFO momentum.FeatureEngineering.strategy_registry: ✅ 成功註冊 EMAExtractor
2026-07-14 17:08:44,561 - momentum.FeatureEngineering.strategy_registry - INFO - ✅ 成功註冊 EMAExtractor
/Users/louis/Desktop/quantitative_trading_system/venv/lib/python3.9/site-packages/joblib/_multiprocessing_helpers.py:44: UserWarning: [Errno 1] Operation not permitted.  joblib will operate in serial mode
  warnings.warn("%s.  joblib will operate in serial mode" % (e,))
VALIDATE OK
  features=7 (min=5)
  skipped: oc_return=turnover_missing, hl_range=gross_ic_missing
  non_skipped_with_net_ic=5
  fixture_sha256=601c7e78f870d34b...
  git_head=97022a751708
handoffs/ic1c_baseline/g_old.json: OK
shell_exit=0
```

### CMD B — 決定性字面雙跑（§B r5）

```
$ h1=$(python scripts/ic1c_freeze_baseline.py --baseline old >/dev/null && shasum -a 256 handoffs/ic1c_baseline/g_old.json | cut -d' ' -f1); h2=$(python scripts/ic1c_freeze_baseline.py --baseline old >/dev/null && shasum -a 256 handoffs/ic1c_baseline/g_old.json | cut -d' ' -f1); [ "$h1" = "$h2" ]
shell_exit=0
h1=6e23ff632cb9153b6f2b803bfc607a033151efa3b57a0fa22ac5ec91bdc36179
h2=6e23ff632cb9153b6f2b803bfc607a033151efa3b57a0fa22ac5ec91bdc36179
```

### 佔位模式（new/new2）

```
$ python scripts/ic1c_freeze_baseline.py --baseline new
NotImplementedError: G-NEW freeze is Phase 1 (B1); implement after NetICAnalyzer B-strict rewrite
new_exit=2

$ python scripts/ic1c_freeze_baseline.py --baseline new2
NotImplementedError: G-NEW2 freeze is Phase 2 (B2); implement after API wiring
new2_exit=2
```

## g_old 內容抽樣（機器可掃）

- features 數=7（≥ fixture 7−2=5）
- `oc_return`: `{skipped:true, reason:turnover_missing}`
- `hl_range`: `{skipped:true, reason:gross_ic_missing}`
- non-skipped 5 欄皆含現行錯誤鍵 `net_ic`（G-OLD 故意保留）
- `non_finite_fields`=5 條 capacity.estimated_capacity_usd（無 volume → NaN→null）
- `fixture_sha256=601c7e78f870d34bea86932b6bdb21415cf66651ed389332e6d915cebacf95a2`
- `git_head=97022a7517087b5d83aef760283167d2f0a167a0`
- `generated_by=ic1c_freeze_baseline --baseline old`

## Scope

- 新增：`scripts/ic1c_freeze_baseline.py`、`scripts/ic1c_validate_baseline.py`、`handoffs/ic1c_baseline/g_old.{json,sha256}`、本 RESULT
- `git diff --stat momentum/ api/ frontend/` → 空（零既有程式碼變更）
- 未碰 `data_cache/` 寫入；未改 fixture

---

```
ASSUMPTIONS_VERIFIED:
  - NetICAnalyzer.batch_analyze 現行仍輸出 net_ic 鍵（G-OLD 故意保留；validator 斷言 non-skipped 必含）
  - fixture FEATURE_NAMES=7 欄含 oc_return/hl_range；inject 後 features=7、non-skipped=5
  - TurnoverAnalyzer.compute_quantile_turnover 可對 fixture 全欄產出有限 turnover（除 inject pop）
  - capacity.estimated_capacity_usd 在無 avg_daily_volume_usd 時為 NaN，sanitize 後為 null 並列入 non_finite_fields
  - 連續兩次 --baseline old 產出 g_old.json sha256 位元一致

TESTS_RUN:
  - python scripts/ic1c_freeze_baseline.py --baseline old && python scripts/ic1c_validate_baseline.py handoffs/ic1c_baseline/g_old.json && shasum -a 256 -c handoffs/ic1c_baseline/g_old.sha256 → exit 0（VALIDATE OK + g_old.json: OK）
  - h1/h2 決定性雙跑 → exit 0，h1==h2==6e23ff632cb9153b6f2b803bfc607a033151efa3b57a0fa22ac5ec91bdc36179
  - --baseline new / new2 → NotImplementedError exit 2（佔位符合 TODO）

FAILURES_SEEN: none

SCOPE_CHANGES: none（僅新增 scripts×2 + handoffs/ic1c_baseline + RESULT；未改 momentum/api/frontend）

NUMERIC_OR_SCHEMA_IMPACT: none（零 runtime 程式碼變更；僅凍結改前輸出快照）
```

STATUS: DONE

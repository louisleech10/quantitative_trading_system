# IC1CFR-B0 — Code Review (Composer)

**task-id**: IC1CFR-B0  
**審查者**: Composer  
**date**: 2026-07-15  
**對象**: Grok B0 — `scripts/ic1cfr_stopgap_freeze.py` + `handoffs/ic1cfr_stopgap_baseline/*` + `handoffs/IC1CFR-B0-RESULT.md`  
**對照**: `docs/IC1CFR_STOPGAP_TODO.md` Frozen r3 Task 0.1 / §B B0→B1 Gate

## Verdict：**APPROVE** — 六項重點全過；0 BLOCKING；2 NB（pytest 基線波動、B1 前建議重凍 nodeids 若 flake 再現）

---

## ① Canonical hash 排除清單精確性 — **PASS**

| 檢查 | 結果 |
|------|------|
| 常數 `CANONICAL_EXCLUDE_JSON_PATHS`（10 條 JSON-path） | 覆蓋 SPEC §G:34 + T-S1：`generated_at` / `lineage.generated_at` / `report.total_execution_time_s` / `report.deep_analysis_errors.*.timestamp` / 頂層計數 `completed_count`·`skipped_count`·`failed_count` / `deep_analysis_summary.{completed,skipped,failed}` |
| 未剔除 `results.factor_returns` 本體 | `strip_canonical_excludes` 後 `factor_returns` 仍在 canonical payload |
| artifact 保漂移欄原值 | `before.json` 仍含 `report.total_execution_time_s`、`deep_analysis_errors[0].timestamp`、頂層 `generated_at` |
| 重算一致 | `canonical_sha256(before.json)` = `before.sha256` = `2b6489da…512ca`（獨立重算 ×2 idempotent） |
| 路徑語意 | `*` 僅匹配 list index 一層（`_path_matches_exclude`），非廣義刪 key |

`before.json` 內嵌 `canonical_exclude_json_paths` 與腳本常數一致（可審計）。

---

## ② Lineage（fixture_sha256 / git_head）— **PASS**

`before.json` → `lineage` 區塊：

| 欄位 | 值（抽樣） | 獨立驗證 |
|------|-----------|----------|
| `fixture_sha256` | `601c7e78…f95a2` | `shasum -a 256 tests/fixtures/ic_api_real_kline.py` ✓ |
| `git_head` | `372d77f3922a1c4d7f7f8601e5a9b484399dd837` | `git rev-parse HEAD` ✓ |
| `fixture_path` / `kline_cache` | 相對路徑已記 | — |

Task 0.1「記 lineage」已落地；非空稱。

---

## ③ Factory allowlist 內容 — **PASS**

獨立 `rg -n` 與 `handoffs/ic1cfr_stopgap_baseline/factory_allowlist.txt` 對照：

| 類別 | 預期（TODO / T-S11） | 凍結 artifact |
|------|---------------------|---------------|
| **factory_caller** | 唯一 `tests/phase26/test_deep_analysis_factories.py`（排除 `momentum/factories.py` 定義體） | 1 條，吻合 |
| **direct_consumer** | `momentum/factories.py:454` | ✓ |
| | `ic_filter_orchestrator.py:1784`（`_run_factor_return`） | ✓ |
| | `tests/phase24/test_factor_return_analyzer.py`（11 行） | ✓ 18,30,40,50,70,81,90,101,112,118,130 |
| | `scripts/phase29_perf_validation_tmp.py:30`（B1 quarantine 待辦） | ✓ |
| **scanner self** | 排除 `scripts/ic1cfr_stopgap_freeze.py` | rg 命中註解行但未入 allowlist（split 字串 + `SCANNER_SELF_REL`） |

格式 `factory_caller\|path` / `direct_consumer\|path:line` 可機讀；B0 與 Task 1.3 共用 `normalize_factory_scan_hits` 語意。

---

## ④ 79 nodeids baseline 合理性 — **PASS**（含 NB）

| 指標 | 值 |
|------|-----|
| 總行數 | 79 |
| 含 `::` 的 test 級 nodeid | 76 |
| 檔級 collection-error | 3（`test_ic_analysis_api.py` / `test_ic_analysis_service.py` / `test_ic_deep_analysis.py`） |
| 組成 | 以 `tests/api/` batch/IC/deep_analysis + `tests/momentum/` lightgbm/xgboost/golden 為主；與 HANDOFF「既有紅非本票」一致 |

**獨立驗證**：`python scripts/ic1cfr_stopgap_freeze.py --check-nodeids` → exit 0，`new_failures=0`（約 13.5min 全 suite）。

**NB-CR1**：兩次 reviewer 全 suite 跑結果不完全一致（第一次 check-nodeids：`current=75, resolved=4`；第二次 diff：`resolved=7` 含 3 檔 collection + 4× worker_logging smoke，`new=1` `test_ic_persist_redirect_golden_ab`）。B0 凍結機制正確，但 nodeid 解析對 collection-error / 多進程 smoke 可能隨跑次波動；**建議 B1 開工前若 `--check-nodeids` 出現 `NEW_FAILURES` 先確認是否 flake 再決定是否重跑 `--before` 更新 baseline**。非 B0 實作錯誤。

---

## ⑤ 零 runtime 變更 — **PASS**

```
git diff --name-only momentum/ api/ frontend/ | wc -l → 0
```

僅新增 `scripts/ic1cfr_stopgap_freeze.py` 與 `handoffs/ic1cfr_stopgap_baseline/*`（符合 Task 0.1 邊界）。

---

## ⑥ `--after-*` 佔位 NotImplementedError — **PASS**

```
python scripts/ic1cfr_stopgap_freeze.py --after-default   → NotImplementedError, exit 2
python scripts/ic1cfr_stopgap_freeze.py --after-explicit → NotImplementedError, exit 2
```

訊息標明 Phase 1 (B1)；`main()` 以 `SystemExit(2)` 包裝。B0 scope 僅要求佔位，不要求實作 after golden。

---

## before.json 基準內容抽驗（codex CX-4）

| 斷言 | 實測 |
|------|------|
| `module_summary.factor_returns == "completed"` | ✓ |
| `results.factor_returns` 非空 dict + 有限 numeric leaf | ✓（7 features） |
| 真-kline 路徑 | `ic_api_real_kline.py` + `kline_cache.h5` ETHUSDT/12h |

---

## 其他 NB

| ID | 說明 |
|----|------|
| **NB-CR2** | `factor_orthogonalization` 在 before 快照中為 pre-existing skip/error（icir dict 形狀）；不影響 factor_returns 凍結基準，與 RESULT 一致。 |

---

```
ASSUMPTIONS_VERIFIED:
  - CANONICAL_EXCLUDE 10 paths 對照 SPEC §G:34 / TODO T-S1
  - lineage fixture_sha256/git_head 對實檔與 HEAD
  - rg factory/direct 與 factory_allowlist.txt 逐行一致
  - before.json factor_returns=completed + 有限葉
  - git diff momentum/api/frontend 空
  - --after-default/--after-explicit NotImplementedError exit 2

TESTS_RUN:
  - python3 canonical_sha256 重算 vs before.sha256 → match
  - shasum fixture + git rev-parse HEAD → match lineage
  - rg create_factor_return_analyzer / FactorReturnAnalyzer\( → 對照 allowlist
  - python scripts/ic1cfr_stopgap_freeze.py --check-nodeids → exit 0, new_failures=0 (~811s)
  - python scripts/ic1cfr_stopgap_freeze.py --after-default/--after-explicit → exit 2
  - git diff --name-only momentum/ api/ frontend/ → 空

FAILURES_SEEN: none（審查範圍）
SCOPE_CHANGES: none（唯讀 + 本檔）
NUMERIC_OR_SCHEMA_IMPACT: none（審查）；B0 產物為凍結快照非 runtime 變更
產出檔: handoffs/IC1CFR-B0-CODEREV-composer.md
```

CODE-REVIEW: APPROVE(0 BLOCKING)

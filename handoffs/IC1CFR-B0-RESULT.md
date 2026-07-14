# IC1CFR-B0 RESULT — Task 0.1 before baseline 凍結 + CODEREV 退修

**task-id**: IC1CFR-B0  
**agent**: Grok (B0 實作 / CODEREV 退修)  
**date**: 2026-07-15  
**TODO**: docs/IC1CFR_STOPGAP_TODO.md Frozen r3 Task 0.1 / §B B0→B1 Gate  
**status**: DONE（含 CODEREV 1 BLOCKING 退修）  
**CODEREV**: handoffs/IC1CFR-B0-CODEREV-codex.md → REJECT(1 BLOCKING) 已修

## 產出檔

| 路徑 | 說明 |
|------|------|
| `scripts/ic1cfr_stopgap_freeze.py` | `--before` / `--check-nodeids`；fail-closed collect；file-level 排除 `::` |
| `handoffs/ic1cfr_stopgap_baseline/before.json` | deep 全模組 enabled 輸出 + lineage（sort_keys，保漂移欄原值） |
| `handoffs/ic1cfr_stopgap_baseline/before.sha256` | **canonical** sha256（剔精確 JSON-path 漂移欄後） |
| `handoffs/ic1cfr_stopgap_baseline/factory_allowlist.txt` | factory_caller + direct_consumer 凍結集 |
| `handoffs/ic1cfr_stopgap_baseline/pytest_baseline_nodeids.txt` | suite failed+collection-error nodeid（**77** 條；全為 `::` test-level） |
| 本檔 | 驗收 receipt |

## CODEREV 退修摘要（2026-07-15）

針對 codex BLOCKING（fail-open + collection-error 誤加成 file-level allowlist）：

1. **fail-closed**：`collect_pytest_failed_nodeids()` 保留 subprocess `returncode`；`rc != 0` 且解析結果為空 → 印 `returncode` + stderr 摘要 → `SystemExit(1)`。禁止回 `[]` 讓 `check_nodeids` 當 baseline 子集 PASS。
2. **collection-error 正則**：file-level 只處理**行內不含 `::`** 的 `ERROR … .py`；ERRORS 區塊 `collecting` 路徑若含 `::` 也不入 file-level。
3. **重建 baseline**：同 suite 重跑 + 新 parser；移除 3 個假 file-only（與同檔 test nodeid 並存者）；確認 0 個真 collection error；並收錄重跑時多出的 1 個 test-level failure。

| 項目 | 舊 | 新 |
|------|----|----|
| nodeids 總數 | 79 | **77** |
| `::` test-level | 76 | **77** |
| file-only | 3 | **0** |
| 移除 | — | `tests/api/test_ic_analysis_api.py`、`…_service.py`、`…_deep_analysis.py`（假 collection error） |
| 新增 | — | `tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py::test_golden_redirect_on_off_sha256` |

## 實作摘要（對齊 Task 0.1）

1. 真-kline：`tests/fixtures/ic_api_real_kline.py` + `data_cache/feature_klines/kline_cache.h5` ETHUSDT/12h
2. `ICFilterOrchestrator` seed cache → `run_deep_analysis(force_modules=ALL10)` advanced + 各模組 enabled=True
3. `before.json`：`sort_keys` + `allow_nan=False`；非有限 number→null；**artifact 保** `total_execution_time_s` / error `timestamp` / `generated_at`
4. **canonical hash**：精確 JSON-path 常數 `CANONICAL_EXCLUDE_JSON_PATHS`（勿廣義刪 key）
5. factory allowlist：`rg create_factor_return_analyzer` callers + `rg FactorReturnAnalyzer\(` direct consumers
6. pytest baseline：`venv/bin/pytest tests/momentum/ tests/api/ tests/phase26/ -q` → 解析 FAILED/ERROR nodeid（修正後規則）
7. lineage：`fixture_sha256` / `git_head`
8. **零 runtime 變更**：未改 `momentum/` `api/` `frontend/` 既有檔

## 驗證命令與 stdout（逐字）

### CMD A — Task 0.1 驗證 / §B B0→B1 Gate（初凍；raw hash 後被 canonical 重跑覆寫，見 CODEREV NB）

```
$ python scripts/ic1cfr_stopgap_freeze.py --before
...
canonical_sha256=2b6489daaeb92fad717c039fc6cd5d4414f7282b9543c3f27629416f73f512ca
module_summary.factor_returns=completed
pytest_baseline_nodeids=79   # 初凍；退修後見 CMD E → 77
shell_exit=0
```

### CMD B — canonical 重跑一致

```
canonical=2b6489daaeb92fad717c039fc6cd5d4414f7282b9543c3f27629416f73f512ca
matches before.sha256=yes
module_summary.factor_returns=completed
```

### CMD C — 佔位模式

```
$ python scripts/ic1cfr_stopgap_freeze.py --after-default
NotImplementedError: --after-default is Phase 1 (B1); implement after default-off + sanitizer
exit:2

$ python scripts/ic1cfr_stopgap_freeze.py --after-explicit
NotImplementedError: --after-explicit is Phase 1 (B1); implement after ModuleUnavailableError path
exit:2
```

### CMD D — fail-closed 自測（CODEREV 退修；monkeypatch subprocess）

模擬 pytest `returncode=3`、stdout/stderr 僅 INTERNALERROR、**無可解析 nodeid**：

```
$ python - <<'PY'   # monkeypatch scripts/ic1cfr_stopgap_freeze.subprocess.run
# FakeProc: returncode=3, stdout="INTERNALERROR> Boom...", stderr="INTERNALERROR while collecting..."
# call collect_pytest_failed_nodeids()
running: .../venv/bin/pytest tests/momentum/ tests/api/ tests/phase26/ -q
shell_exit=1
fail_closed_empty_parse: PASS
```

stderr（fail-closed 訊息）：

```
FAIL: pytest returncode non-zero but no failure/collection nodeids parsed (INTERNALERROR / interrupt / exit 5 no-tests / unparseable). returncode=3
stderr_summary:
INTERNALERROR while collecting tests
no short test summary info

combined_tail:
INTERNALERROR> Boom during session

INTERNALERROR while collecting tests
no short test summary info
```

補充單元斷言（同 session）：
- `ERROR path.py::test` **不**再產生 file-level `path.py`（parse_regex: PASS）
- `rc==0` + 空解析 → 回 `[]` 合法（all_green_empty: PASS）
- `rc!=0` + 可解析 FAILED → 回 list，不 exit（rc_nonzero_with_nodeids: PASS）

### CMD E — 依修正規則重建 baseline nodeids

```
$ venv/bin/pytest tests/momentum/ tests/api/ tests/phase26/ -q
pytest_returncode=1
parsed_count=77
file_only_count=0
old_count=79 new_count=77
removed=3
  - tests/api/test_ic_analysis_api.py
  - tests/api/test_ic_analysis_service.py
  - tests/api/test_ic_deep_analysis.py
added=1
  + tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py::test_golden_redirect_on_off_sha256
wrote handoffs/ic1cfr_stopgap_baseline/pytest_baseline_nodeids.txt count=77
= 45 failed, 1496 passed, 18 skipped, 5166 warnings, 32 errors in 944.10s (0:15:44) =
```

結論：3 個 file-only **非**真 collection error（pytest summary 皆為 `ERROR path.py::test … redirect already active`）；重建後 file_only=0。

### Scope

```
$ git diff --name-only momentum/ api/ frontend/ | wc -l
0
```

退修僅動：`scripts/ic1cfr_stopgap_freeze.py`、`handoffs/ic1cfr_stopgap_baseline/pytest_baseline_nodeids.txt`、本 RESULT。

## 凍結產物抽樣

- `report.module_summary.factor_returns` == `"completed"`
- `report.results.factor_returns` 為非空 dict，含有限 numeric leaf
- `report.total_execution_time_s` **仍在 artifact**（僅 canonical 剔除）
- factory_caller 唯一：`tests/phase26/test_deep_analysis_factories.py`
- pytest baseline nodeids=**77**（全 `::`；0 file-level collection error）

## factory_allowlist 內容（凍結；未因退修改動）

```
factory_caller|tests/phase26/test_deep_analysis_factories.py
direct_consumer|momentum/Analysis/ic_filter_orchestrator.py:1784
direct_consumer|momentum/factories.py:454
direct_consumer|scripts/phase29_perf_validation_tmp.py:30
direct_consumer|tests/phase24/test_factor_return_analyzer.py:* (11 行)
```

---

```
ASSUMPTIONS_VERIFIED:
  - 真-kline ETHUSDT/12h 可經 build_real_kline_frames 產出 features；factor_returns=completed
  - canonical_sha256=2b6489daaeb92fad717c039fc6cd5d4414f7282b9543c3f27629416f73f512ca
  - 舊 baseline 3 file-only 為 ERROR path.py::test 正則前綴誤匹配，非真 collection error（CMD E 重跑 file_only=0）
  - rc!=0 且解析空 → SystemExit(1)（CMD D）
  - 零 runtime 變更

TESTS_RUN:
  - CMD D monkeypatch FakeProc rc=3 empty parse → shell_exit=1 + FAIL 訊息含 returncode=3（PASS）
  - parse unit：path.py::test 不進 file-level；真 ERROR path.py / collecting 仍進（PASS）
  - CMD E 全 suite pytest 重建 nodeids → 77 lines, 0 file-only, exit from pytest=1, writer ok
  - --after-default / --after-explicit → NotImplementedError exit 2（初凍）

FAILURES_SEEN:
  - CODEREV BLOCKING fail-open + file-level 誤匹配 → 本退修關閉
  - 初凍 factory_allowlist 曾誤收 scanner self → 已在初凍輪修

SCOPE_CHANGES: none（退修僅 script + nodeids baseline + RESULT）

NUMERIC_OR_SCHEMA_IMPACT: none（零 runtime；before.json / before.sha256 / factory_allowlist 未改）
```

STATUS: DONE

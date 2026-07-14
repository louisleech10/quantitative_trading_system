# IC1CFR-B1 — Code Review (Composer)

**task-id**: IC1CFR-B1 | **審查者**: Composer | **日期**: 2026-07-15  
**對照**: Frozen `docs/IC1CFR_STOPGAP_TODO.md` Phase 1 + `git diff HEAD` + `handoffs/IC1CFR-B1-RESULT.md` + 未追蹤 `factor_return_sanitizer.py` / `test_factor_return_stopgap.py`

## ① r1 B5 in-mem cache deepcopy 洩漏路徑

| 路徑 | 現碼 | 判定 |
|------|------|------|
| **全命中早退** `:1633-1638` `not force_set` → `deepcopy` → **sanitize** → return | `_sanitize_deep_report_factor_returns(cached)` 於 return 前套用 | **CLOSED**（r1 B5 主洩漏路徑已堵） |
| **force 非空 merge** `:1641-1642` 併舊 cache → `:1727` return | 未 sanitize | **NB1**（r3 grok NB-CACHE-MERGE 已列「非 TODO 必改」；default-off 後新 cache 無有限 FR；in-proc legacy 仍靠 API/reporter 邊界） |

`test_sanitizer_cache_hit_legacy` 注入 `_deep_analysis_cache` 後走早退路徑，log 見 `Deep analysis cache hit`，斷言 `status==unavailable` 且無有限葉 — **真測非假綠**。

## ② 七掛點具名測試

| 掛點 | 實作錨點 | 具名測 | 判定 |
|------|----------|--------|------|
| (a) orchestrator cache-hit | `ic_filter_orchestrator.py:1635-1636` | `test_sanitizer_cache_hit_legacy` | PASS |
| (b) API raw JSON | `ic_analysis_service.py:438-442` | `test_sanitizer_raw_json_legacy` | PASS* |
| (c) serializer + task storage + get | `:1194-1198`, `:727-728` | `test_sanitizer_task_storage_roundtrip` | PASS |
| (d) detailed CSV | `ic_reporter.py:209-212` | `test_sanitizer_csv_legacy` | PASS |
| (e) AI JSON | `:257-260` + `_build_module_summaries` FR 特例 | `test_sanitizer_ai_json_legacy` | PASS |
| (f) Markdown | `:300-303` | `test_sanitizer_markdown_legacy` | PASS |
| (g) export_all raw dump | `:351-354` | `test_sanitizer_export_all_legacy` | PASS |
| 冪等 | `factor_return_sanitizer.py` | `test_sanitizer_idempotent` | PASS |
| M2 | — | `test_mutation_m2_bypass_sanitizer` | PASS（monkeypatch identity → `0.11` 斷言紅） |

\* **NB2**: (b) 測試注入 `task_info["result"]`；production deep 存 `deep_analysis_result` 分離鍵。`json` 分支 sanitize `report` 非 `payload_for_export`（其他格式會 merge deep）。現況 JSON export 本就不含分離 deep → 無實際洩漏，但測試未覆蓋「僅 `deep_analysis_result` 含 legacy」路徑。

Task 1.1/1.3 另檔 `test_factor_return_stopgap.py`（四態 + allowlist + M1/M1b）；M1/M1b 探針真跑紅。

## ③ `momentum/factories.py` re-export

`create_ic_reporter` 旁新增 `sanitize_factor_returns` re-export（Rule 3：`api/services` 禁直 import `momentum.Analysis.*`）。B1 RESULT 已記 scope 擴大；Frozen r3 T-S11 預期 factories 為合法邊界。**可接受、屬必要**。

## ④ `module_summary` 保留 str status

`factor_return_sanitizer._is_results_style_factor_returns`: `str`/`None` → 不換佔位；`dict`/list → §U 佔位。修復先前把 `module_summary.factor_returns=="not_run"` 誤換成 union 致 `ResponseValidationError` 的路徑。**無已知漏洞**；`results.factor_returns` 與 summary 字串可短暫不一致（legacy `completed` + 佔位），stopgap 可接受。

## ⑤ §V 改寫表（7 筆）

| TODO 列 | 檔 | diff 內「舊斷言為何錯」 | 新斷言要點 | 判定 |
|---------|-----|-------------------------|------------|------|
| 1 | `phase24/test_deep_analysis_config.py:33` | ✓ | `enabled is False` | PASS |
| 2 | `momentum/test_tier_config.py:31` | ✓ | tier 後仍 False | PASS |
| 3 | `phase26/test_deep_analysis_integration.py` | ✓ 多處 | not_run / unavailable + 不入 errors | PASS |
| 4 | `api/test_ic_deep_analysis.py` serializes_numpy | ✓ | §U 佔位非 samples==128 | PASS |
| 5 | `momentum/test_export_formats.py:154` | ✓ | 無 0.11 + unavailable/status | PASS |
| 6 | `api/test_export_api.py:96` | ✓ | 200 + body 無 0.03 | PASS |
| 7 | `phase26/test_ic_reporter_deep_analysis.py` | ✓ | inject 後 unavailable | PASS |

## ⑥ 零非 FR 模組計算變更

`git diff HEAD`：`factor_return_analyzer.py` / `monotonicity_tester.py` / `long_short_*` / `net_ic_analyzer.py` **0 行**。FR runner 改 `raise ModuleUnavailableError`（下架非修算）；`ic_reporter`/`ic_analysis_service` 僅 export/sanitize 邊界；`phase29` quarantine。frontend store 僅 default-off。**PASS**。

## 獨立驗證（本輪實跑）

```
venv/bin/pytest tests/momentum/Analysis/test_factor_return_stopgap.py tests/api/test_ic_deep_analysis.py -k "sanitizer or factor_return" -q → 18 passed
bash scripts/mutation_probe_check.sh … → MUTATION-PROBE PASS (6 probes)
python scripts/ic1cfr_stopgap_freeze.py --after-default → exit 0, not_run, no results.factor_returns
python scripts/ic1cfr_stopgap_freeze.py --after-explicit → exit 0, unavailable union, no finite leaves
```

## 其他 NB

- **NB3**: 核心新檔 `momentum/Analysis/factor_return_sanitizer.py`、`tests/momentum/Analysis/test_factor_return_stopgap.py` 仍 `??` 未 commit；驗收前須入版。
- **NB4**: B0 `factory_allowlist.txt` 仍列 `orchestrator:1784` / `phase29:30`；B1 已移除兩處 `FactorReturnAnalyzer(`。守衛測「現況 ⊆ 凍結」仍綠（只擋新增繞路），建議 B2 前更新 B0 artifact 避免語意漂移。

## 結論

Phase 1 Tasks 1.1/1.2/1.3 對照 Frozen TODO 已落地；r1 主 cache-hit 洩漏已堵；七掛點具名測 + M1/M1b/M2 真測；§V 七筆齊；非 FR 計算未動。上列均為 NB，無需退修之 BLOCKING。

CODE-REVIEW: APPROVE (0 BLOCKING)

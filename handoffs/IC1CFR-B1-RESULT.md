# IC1CFR-B1 RESULT — Phase 1 + codex R2 退修

**task-id**: IC1CFR-B1  
**agent**: Grok (impl, fix-round 2 after codex CODEREV-R2 REJECT)  
**date**: 2026-07-15  
**status**: DONE (fix-round 2)

## Scope this round (R2 only)

### B-R2-1 cache force-merge 洩漏
- `ic_filter_orchestrator.run_deep_analysis`: cache-hit / force-merge / 全量重算 **單一收斂**於最終 return 前 `_sanitize_deep_report_factor_returns`
- compute 路徑寫 cache 前亦先 sanitize（避免 dirty legacy 再被 merge 讀出）
- 新具名測 `test_sanitizer_cache_force_merge_legacy`：cache 注入 `long_short_mean_return=0.42` + `force_modules=["trend_analysis"]` → FR §U + summary unavailable + completed_count==1

### B-R2-2 Markdown mutation oracle 假綠
- 新 helper `_assert_markdown_factor_returns_no_finite(md)`：解析**真實 MD 字串** `- factor_returns: {...}`，`ast.literal_eval` + `has_finite_numeric_leaf`，禁止 re-sanitize 輸入再驗
- `test_sanitizer_markdown_legacy` 改打真實 MD 產物
- 新 mutation `test_mutation_m2d_markdown_restore_size_meta`：monkeypatch `_build_module_summaries`→`{"factor_returns":{"size":1}}` 時 MD oracle 必紅

### 連帶 M1 探針
- 出口 sanitizer 統一後，僅恢復 runner 有限值仍被 sanitize 兜住 → M1 假綠
- `test_mutation_m1_restore_compute_batch` 改為同時繞 `_sanitize_deep_report_factor_returns`（雙層防線探針）

## Prior rounds (unchanged summary)

- Task 1.1 default-off 三態 + ModuleUnavailableError
- Task 1.2 sanitizer 七掛點 + save_report + count/list
- Task 1.3 AST factory gate
- §G after-default/explicit non-FR exact + self-prove
- codex R1 六條 CLOSED（cache-hit/save/inject/§G/AST/sanitizer oracle）

## B1→B2 Gate stdout（fix-round 2）

### G1 `venv/bin/pytest tests/momentum/Analysis/test_factor_return_stopgap.py tests/api/test_ic_deep_analysis.py -q`
```
======================== 46 passed, 1 warning in 17.63s ========================
```
receipt: `handoffs/_ic1cfr_b1_pytest.log`

### G2 `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_return_stopgap.py tests/api/test_ic_deep_analysis.py`
```
======================= 9 passed, 37 deselected in 2.21s =======================
MUTATION-PROBE PASS: 受審測試檔皆有探針(或行首 N/A+理由),靜態無空心/偽自證,且 9 個探針真跑過。
```
receipt: `handoffs/_ic1cfr_b1_mutation.log`

### G3 `python scripts/ic1cfr_stopgap_freeze.py --after-default`
```
self-prove non-FR gate red OK: target=factor_centrality diffs=1
module_summary.factor_returns=not_run
factor_returns_results_absent=yes
non_fr_exact_vs_before=pass
canonical_sha256=4fa6cd2e0768cbdd8dcb0a013f96d3c8d55a44450fe432d9e1dea4d63caa6d8c
```
exit 0；receipt: `handoffs/_ic1cfr_b1_after_default.log`

### G4 `python scripts/ic1cfr_stopgap_freeze.py --after-explicit`
```
self-prove non-FR gate red OK: target=factor_centrality diffs=1
module_summary.factor_returns=unavailable
factor_returns_union=unavailable
factor_returns_finite_leaves=no
non_fr_exact_vs_before=pass
canonical_sha256=35ca68a0674bb9a0ded4191ab1bba64ac1f1e3158e479c15aef36e57181a0fd5
```
exit 0；receipt: `handoffs/_ic1cfr_b1_after_explicit.log`

### G5 `bash scripts/check_decoupling.sh`
```
ALL RULES PASS — Ready to freeze
```
receipt: `handoffs/_ic1cfr_b1_decouple.log`

### 補充 `pytest -k factor_return -q`
```
=============== 29 passed, 3734 deselected, 5 warnings in 11.06s ===============
```
receipt: `handoffs/_ic1cfr_b1_factor_return_k.log`

## codex R2 BLOCKING 閉合對照

| # | 問題 | 修法 |
|---|------|------|
| B-R2-1 | force-merge 繞 cache-hit sanitize，legacy FR 0.42 洩漏 + completed=2 | 最終 return 單一收斂 sanitize；寫 cache 前 sanitize；`test_sanitizer_cache_force_merge_legacy` |
| B-R2-2 | MD 測對 re-sanitize 輸入 oracle，size:1 monkeypatch 仍綠 | `_assert_markdown_factor_returns_no_finite(md)` 打真實產物；`test_mutation_m2d_*` 必紅 |

## 產出檔（本輪 delta）

- `momentum/Analysis/ic_filter_orchestrator.py`（統一 sanitize 收斂）
- `tests/api/test_ic_deep_analysis.py`（force-merge 測 + MD oracle + m2d）
- `tests/momentum/Analysis/test_factor_return_stopgap.py`（M1 雙層探針）
- `handoffs/IC1CFR-B1-RESULT.md`（本檔）
- gate logs: `handoffs/_ic1cfr_b1_*.log`

## 不動清單（已遵守）

- `factor_return_analyzer.py` / `monotonicity_tester.py` 計算本體未改
- `long_short_analysis` 未動
- net_ic / trend dimensions 未動
- factory/class 本體保留
- 未碰 `data_cache/`

---

```
ASSUMPTIONS_VERIFIED:
  - codex R2: force_modules + deep cache 走 merge 非 cache-hit 早退(已對照 1640+/1726+ 結構)
  - 最終 return 單一 sanitize 後 force-merge 輸出 FR=unavailable、completed_count=1
  - Markdown oracle 解析實際字串產物; monkeypatch size:1 真紅
  - M1 僅破 runner 時 sanitize 兜底→探針改雙層拆除

TESTS_RUN:
  - venv/bin/pytest tests/momentum/Analysis/test_factor_return_stopgap.py tests/api/test_ic_deep_analysis.py -q → 46 passed
  - bash scripts/mutation_probe_check.sh … → MUTATION-PROBE PASS (9 probes)
  - python scripts/ic1cfr_stopgap_freeze.py --after-default → exit 0 + non_fr_exact_vs_before=pass
  - python scripts/ic1cfr_stopgap_freeze.py --after-explicit → exit 0 + non_fr_exact_vs_before=pass
  - bash scripts/check_decoupling.sh → ALL RULES PASS
  - pytest -k factor_return -q → 29 passed

FAILURES_SEEN:
  - G2 首輪: test_mutation_m1_restore_compute_batch DID NOT RAISE(統一 sanitize 兜底)→ M1 改同時繞 sanitizer 後 9 passed

SCOPE_CHANGES:
  - M1 探針語意擴為 runner+exit-sanitizer 雙層(因 R2 統一收斂屬設計副作用,非越界功能)
  - 未改 analyzer 本體;未改 B0 before.json

NUMERIC_OR_SCHEMA_IMPACT:
  - public run_deep_analysis 全出口(含 force-merge): finite FR → §U unavailable; completed_count 重算
  - cache 寫入前亦 sanitize(idempotent)
  - 非 FR 模組數值未改(§G exact 通過; canonical sha 與 R1 一致)
```

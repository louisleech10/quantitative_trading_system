# IC1C-B1 RESULT (rework after codex REJECT)
**task-id**: IC1C-B1
**date**: 2026-07-14
**scope**: Phase 1 Tasks 1.1/1.2/1.3/1.4 (B1 batch) + codex 4 BLOCKING 驗證鏈修復

## Codex BLOCKING 逐條處置

| # | BLOCKING | 處置 |
|---|----------|------|
| 1 | g_new 無 GROSS_ONLY 樣本 | `--baseline new` 雙 run：主 `result`=cost_enabled=False→GROSS_ONLY+SKIPPED；次 `result_cost_enabled`=True@10bps→COST_ENABLED+SKIPPED；profile 計數 GROSS_ONLY:4+COST_ENABLED:4+SKIPPED:3 |
| 2 | diff_manifest 自生成假綠 | 腳本寫死 feature/summary allowlist 常數；`_validate_*_against_allowlist` 對照；未核可欄→exit 1；`self_test_allowlist_rejects_bogus` + T1 `test_diff_allowlist_rejects_bogus_unapproved_field` |
| 3 | phase25 empty_aligned 遺失 | 移植 `test_compute_net_factor_return_empty_aligned` 入 T1；改寫理由表補列 |
| 4 | SCOPE_CHANGES 不實 / 非 B1 檔 | RESULT 誠實列出；`.claude/*` 與 `tests/golden/l65/test_inventory.txt` 為 session 副作用，本批未碰、由編排端處理 |

## Gate commands (B1→B2) verbatim stdout

### 1) pytest T1 + SCHEMA + T3 + export
```
======================== 59 passed, 1 warning in 0.51s =========================
pytest_exit=0
```
（含新增 `test_compute_net_factor_return_empty_aligned`、`test_diff_allowlist_rejects_bogus_unapproved_field`）

### 2) mutation_probe_check
```
======================= 9 passed, 37 deselected in 0.38s =======================
MUTATION-PROBE PASS: 受審測試檔皆有探針(或行首 N/A+理由),靜態無空心/偽自證,且 9 個探針真跑過。
mutation_exit=0
```

### 3) freeze --baseline new
```
wrote handoffs/ic1c_baseline/g_new.json
sha256=d77ce57335a13832176a53de5259e88fa6b90bcb0399fbc8e725b0662d12151e
profiles=GROSS_ONLY:4+COST_ENABLED:4+SKIPPED:3 features=7
diff_manifest=handoffs/ic1c_baseline/diff_manifest.json
non_finite_fields=0
freeze_exit=0
```

### 3b) allowlist self-test
```
self-test PASS: bogus_unapproved_field/bogus_summary rejected
selftest_exit=0
```

### 4) static greps
```
net_ic_proxy count: 0
ic_reporter exact net_ic field quote: (none)
```

### 5) profile equality 機檢
```
{'GROSS_ONLY': 4, 'COST_ENABLED': 4, 'SKIPPED': 3, 'OTHER': 0}
```

## Structured footer

### 改寫舊測試：舊斷言為何錯

| 舊斷言/測試 | 為何錯 / 處置 |
|-------------|---------------|
| `result["net_ic"]` / `compute_net_ic` | 相關係數減報酬率=無意義量;鍵全樹禁止 |
| `default_cost_bps=5/0/50` 驅動 | 寫死成本回退;無成本唯一=`cost_enabled=False`;0 非法 |
| `profitable_after_cost is False` (bool from IC 正負) | 1c 無 canonical 報酬分子,須 unavailable union |
| `factor_returns` 注入→`net_factor_return` 序列 | 1c 忽略注入,恒 unavailable(1c-FR) |
| `rank_correlation_gross_vs_net` / `avg_ic_loss_pct` | 混減衍生 summary,已刪 |
| `cost_sensitivity` 含 `net_ic` / 硬編 scenarios | 改 §T 階梯+僅 `cost_drag_return` |
| turnover `0.1-0.01×2=0.08` proxy | 固化混量綱+四腿計費 |
| proxy nan→nan | SPEC v1.1:負/非有限→raise,禁 clamp |
| export fixture `"net_ic":0.04` / 欄名 net_ic | 應 cost_drag_return 手算值 |
| phase25 近重複本（多數） | 同錯 API 固化,已刪 |
| `test_compute_net_factor_return_empty_aligned` | **非錯舊斷言**：deprecated 函式仍在,空對齊須守;phase25 刪時遺失→**移植入 T1** |

### 產出檔（本 rework 觸及）
- `scripts/ic1c_freeze_baseline.py`（雙 run 三 profile + 寫死 allowlist + self-test）
- `tests/momentum/Analysis/test_net_ic_analyzer.py`（empty_aligned + allowlist 負例）
- `handoffs/ic1c_baseline/g_new.{json,sha256}`（重凍）
- `handoffs/ic1c_baseline/diff_manifest.json`（含 allowlist 快照+value_changes）
- `handoffs/IC1C-B1-RESULT.md`（本檔）

### 既有 B1 本體（runtime 未改語意，codex 判 PASS）
- `momentum/Analysis/net_ic_analyzer.py` / `ic_config_schema.py` / `ic_filter_orchestrator.py`
- `momentum/Analysis/turnover_analyzer.py` / `ic_reporter.py`
- `config/ic_config.yaml`
- `tests/momentum/Analysis/test_net_ic_schema_profiles.py` / T3 / export
- deleted: `tests/phase25/test_net_ic_analyzer.py`（empty_aligned 已移植）

ASSUMPTIONS_VERIFIED: 雙 run 三 profile 鍵集合 equality；allowlist 拒絕 bogus_unapproved_field/bogus_summary；gross_ic/turnover vs G-OLD 等值(排除三注入)；cost_drag 獨立 numpy oracle atol=1e-12；empty_aligned 空 Series→[]+NaN；59 pytest 全綠 VERIFY:handoffs/IC1C-B1-RECEIPT.md(Claude 獨立重跑同結果)
TESTS_RUN: venv/bin/pytest tests/momentum/Analysis/test_net_ic_analyzer.py tests/momentum/Analysis/test_net_ic_schema_profiles.py tests/momentum/test_turnover_analyzer.py tests/momentum/test_export_formats.py -v → 59 passed；bash scripts/mutation_probe_check.sh … → MUTATION-PROBE PASS (9 probes)；python scripts/ic1c_freeze_baseline.py --baseline new → exit 0 sha256=d77ce57335a13832176a53de5259e88fa6b90bcb0399fbc8e725b0662d12151e profiles=GROSS_ONLY:4+COST_ENABLED:4+SKIPPED:3；python scripts/ic1c_freeze_baseline.py --self-test → PASS
FAILURES_SEEN: none this rework round
SCOPE_CHANGES: 本 rework 僅動 freeze 腳本+T1 兩測試+g_new/diff_manifest/RESULT；runtime 本體未再改。git worktree 另含 session 副作用非本 diff：`.claude/settings.json`、`.claude/gate/{audit,verify_audit}.log`、`tests/golden/l65/test_inventory.txt`（pytest collect 副作用）——**未碰、不納 B1 驗收**，由編排端隔離/revert。phase24 `default_cost_bps` 斷言仍屬 B2/T5。
NUMERIC_OR_SCHEMA_IMPACT: g_new schema 擴充 `result_cost_enabled` 雙樹（主 GROSS_ONLY、次 COST_ENABLED）；diff_manifest 改 allowlist 驅動；runtime analyzer 輸出 schema 不變

STATUS: DONE

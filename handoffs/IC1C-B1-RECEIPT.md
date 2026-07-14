# IC1C B1 驗收 receipt(2026-07-14,Claude 獨立實跑)

Gate B1→B2 命令實跑(非轉述):
```
venv/bin/pytest tests/momentum/Analysis/test_net_ic_analyzer.py tests/momentum/Analysis/test_net_ic_schema_profiles.py tests/momentum/test_turnover_analyzer.py tests/momentum/test_export_formats.py -q → 59 passed(退修後;首輪 57)
bash scripts/mutation_probe_check.sh <T1,T3> → MUTATION-PROBE PASS(9 probes 真跑)
python scripts/ic1c_freeze_baseline.py --baseline new → exit 0 sha256=d77ce573...d12151e,profiles=GROSS_ONLY:4+COST_ENABLED:4+SKIPPED:3
bash scripts/check_decoupling.sh → ALL RULES PASS
殘留 grep:'"net_ic"' in ic_reporter==0;net_ic_proxy 全 repo==0
```
Code review:composer APPROVED 0 BLOCKING(IC1C-B1-CODEREV-composer.md);codex 首輪 REJECT(4B,全在驗證鏈,runtime 4 Task PASS)→Grok 退修(三 profile 雙樹/allowlist 寫死+bogus 負例/empty_aligned 移植/SCOPE 誠實)→codex R2 APPROVED 4/4 CLOSED(IC1C-B1-CODEREV-R2-codex.md,含唯讀重跑 byte-equal+注入 bogus 實證紅)。
測試意義:59 tests=B-strict 契約(全樹無 net_ic 鍵/三 profile 恰等/§T 公式手算/fail-closed 域檢/summary 新契約/JSON strict);9 mutation probe=每支正確性測試證明「改壞會紅」;G-NEW golden=獨立 numpy oracle 全量重算+不變欄對 G-OLD 等值。

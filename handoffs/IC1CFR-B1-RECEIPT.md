# IC1CFR-STOPGAP B1 驗收 receipt(2026-07-14,Claude 獨立實跑)

Gate B1→B2 命令:
```
venv/bin/pytest tests/momentum/Analysis/test_factor_return_stopgap.py tests/api/test_ic_deep_analysis.py -q → 46 passed
bash scripts/mutation_probe_check.sh <兩檔> → MUTATION-PROBE PASS(9 probes 真跑)
python scripts/ic1cfr_stopgap_freeze.py --after-default → not_run + 無 results.factor_returns 節
python scripts/ic1cfr_stopgap_freeze.py --after-explicit → §U union / factor_returns_finite_leaves=no / non_fr_exact_vs_before=pass
bash scripts/check_decoupling.sh → ALL RULES PASS
```
Code review:composer APPROVED 0 BLOCKING;codex 三輪(REJECT 6B→REJECT 2B→APPROVE 全 CLOSED)。
codex 實證抓到的洩漏(全數修復並由其親自重跑確認):①`save_report()` raw json.dump 洩漏(SAVE_REPORT_LEAK 0.42,原七掛點未列)②cache-hit 只洗 results 未洗 summary/count ③inject 路徑 module_statuses list 形態 sanitizer 認不得 ④**cache force-merge 第二條洩漏路徑**(0.42)⑤consumer guard 可用 alias import/同行第二 ctor 繞過(改 AST 掃描)⑥sanitizer 測試兩類假綠(_SUMMARY_NULL_KEYS 清空/Markdown oracle 跑在重洗輸入上)。
最終設計:**public run_deep_analysis 最終 return 前單一收斂點統一 sanitize**+cache 寫入前亦 sanitize(冪等);codex 另跑三種 force 組合+cache writer 路徑確認無第三/第四洩漏路徑。
測試意義:46 tests=三態契約(not_run/unavailable union/deep-off)+七掛點+save_report+cache 三路徑+consumer guard;9 probes=改壞即紅;§G=非 FR 模組逐 JSON-path exact 比對(證明只下架該下架的)。

# IC1C B2 驗收 receipt(2026-07-14,Claude 獨立實跑)

Gate B2→B3 命令實跑:
```
pytest tests/api/test_ic_deep_analysis.py --collect-only -q → 20 collected exit 0
pytest tests/api/test_ic_deep_analysis.py tests/phase24/test_deep_analysis_config.py -q → 27 passed
mutation_probe_check.sh <T2,T5> → 4 probes PASS
npm --prefix frontend run test -- NetICChart → 8 passed
npm --prefix frontend run build → exit 0
python scripts/ic1c_freeze_baseline.py --baseline new2 → exit 0 sha256=57cdbc20...(API 三段 bootstrap,4 features 比對)
python scripts/ic1c_freeze_baseline.py --self-test → PASS(bogus 拒絕+r7b predicates 5 案例)
check_decoupling.sh → ALL RULES PASS
```
Code review 鏈:composer APPROVED 0B;codex 四輪(REJECT 5B→4B→1B→APPROVED 0B,全 CLOSED):G-NEW2 gross_ic 不變式(TODO r7/r7b Frozen 修訂,codex 核可)、離線可重現(codex 無網親測三命令)、TS 真 discriminated union+never 排除(codex tsc 構造混合物件紅實證)、T4 走真 production 路徑(useICAnalysis.startDeepAnalysis+mock fetch 422)、`?? 0` 假值剷除、同號 predicate 斷路器換手 composer 修(0 無號,(0.0,0.2) FAIL)。
測試意義:27 API tests=fail-closed 矩陣(422 域檢含 0/NaN/inf/字串/雙 override 入口/legacy 相容)+e2e unavailable+7bps fullstack wiring;8 前端 tests=成本輸入送達+三態 oracle+m4 probe;G-NEW2=API 傳導等值(排除注入,gross_ic 不變式)。

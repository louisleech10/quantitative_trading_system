# IC1C-FR-STOPGAP adversarial SPEC review — codex (2026-07-14)
範圍：唯讀核對 `docs/IC1CFR_STOPGAP_SPEC.md`、producer→API/export→TS/UI、legacy/load seam、phase26/export tests；裁決 REJECT。

- IC1CFR-CX-1｜BLOCKING｜證據：SPEC §A 所稱 `ic_config_schema.py:193`「預設模組清單」不存在（該行是 trend dimensions）；active `config/ic_config.yaml:115-116`、`api/models/ic_models.py:21-29`、`frontend/src/store/icAnalysisStore.ts:107,133,151` 仍預設 true，且 `_apply_tier_config:3369-3371` 對 intermediate/advanced 強制所有模組 true。反例：只把 `FactorReturnConfig.enabled=False`，有效設定仍 true；M1「恢復預設 enabled」也不是有效 mutation。
- IC1CFR-CX-2｜BLOCKING｜證據：`FactorEquityCurveChart` 並非 factor-return consumer；`page.tsx:790-794` 傳主流程 `quantile_returns`，chart `:79,92-110,143-155` 按不同 timestamp 子序列的陣列位置做 high-low、drawdown、Sharpe；producer `monotonicity_tester.py:43-55` 已丟 timestamp。反例：`factor_returns` runner 回 unavailable，該圖仍照畫有限 L-S；此同源同病路徑須獨立下架，不能靠 factor-return status。
- IC1CFR-CX-3｜BLOCKING｜證據：SPEC 只令 summary CSV 三欄 null；`ic_reporter.py:195-228,639-662` detailed CSV、`:230-321` AI/Markdown、`:323-359` export_all、`:728-778` report serialization 仍接受任意 legacy finite payload；`ic_analysis_service.py:433-468` 直接餵 deep result。反例：tests/api/test_export_api.py:92-100 注入 finite legacy payload，現有 status-only export tests 全可假綠。需單一 output-boundary sanitizer，覆蓋 API result、JSON/AI/CSV-detailed/Markdown/export_all、cache hit。
- IC1CFR-CX-4｜BLOCKING｜證據：Task 1.1 佔位 `{status,reason}` 缺 `value:null`，與 1c §U (`IC1C_NETIC_SPEC.md:32-36`) union 不同；「整模組 skipped」又未選定 `{skipped:true,reason}` profile。反例：TS 若建 `{status:'unavailable';value:null;reason}` discriminated union，後端現稿無法 type-safe parse。須選一個精確 shape、鍵集合、module_summary 狀態並全邊界同構。
- IC1CFR-CX-5｜BLOCKING｜證據：§G M1 恢復 enabled 後 runner 依 Task 1.1 仍回 unavailable，故條件②不會紅；全 report 另含 `total_execution_time_s` 與 error timestamp，未列 canonical compare allow/exclude；M2 的 sharpe 基線已因 reporter 讀 `sharpe`、analyzer 產 `sharpe_ratio` 而為 null。反例：錯誤 sanitizer 不生效但 runner placeholder 仍使 M1 綠。需對 sanitizer 做 finite-payload mutation，並逐 JSON path 比對而非未定義 byte 比對。
- IC1CFR-CX-6｜BLOCKING｜證據：`create_factor_return_analyzer()` 公開 factory 與 `scripts/phase29_perf_validation_tmp.py:30` 仍可直接產 finite 錯位值；SPEC 未列 exemption/denylist。反例：UI/API 下架後腳本仍消費 `compute_batch`。若 analyzer 本體刻意保留，consumer-map gate 至少須只允許 analyzer tests + stopgap runner，其他 caller fail。
- IC1CFR-CX-7｜NON-BLOCKING（§A 裁定）｜`long_short_analysis` **不同源、不同病，不納入本票**：`long_short_analyzer.py:33-36` 先 index-align，`:63-76` 分別算 long/short conditional returns，無 reset_index、無位置配對、無 LS cumulative。反例：它沒有宣稱逐期 self-financing L-S series；應列入 §G unchanged allowlist。其 irregular-subset Sharpe/命名可另票審，不是本次 timestamp mismatch。

既有測試紅表（靜態預測）：
| 節點 | 正確止血後 | 理由 |
|---|---|---|
| `phase26/test_deep_analysis_integration.py::test_run_deep_analysis_generates_report_and_progress` | RED→須改 | 現斷言 default report 含 `factor_returns`；真正 default-off 應不含或明確 unavailable profile。 |
| `phase26/test_ic_reporter_deep_analysis.py::test_inject_deep_analysis_serializes_required_keys` | 現況假綠→須加形狀/finite 否定 | fixture 明注入 finite LS，但只驗 key 存在。 |
| `test_export_formats.py::test_detailed_csv_factor_return_format` | RED→須改 | 現斷言 detailed CSV 含 `long_short_mean_return`。 |
| `test_export_formats.py::{test_summary_csv_columns_match_spec,test_export_all_creates_all_files}` | 現況假綠→須補值/全格式否定 | 只驗欄名/檔存在，不驗 finite 舊值被 scrub。 |
| `test_export_api.py::{test_export_csv_summary_200,test_export_csv_detailed_factor_return,test_export_ai_json_200,test_export_markdown_200}` | 現況假綠→須補 payload 否定 | fixture 注入 finite legacy，測試只驗 200/content-type。 |
| `phase26/test_deep_analysis_factories.py` | GREEN（保留） | SPEC 明定 analyzer 本體留待 FULL；但需 consumer denylist。 |

ASSUMPTIONS_VERIFIED: `rg` 全棧精確詞掃描；逐碼核對 analyzer/orchestrator/config/reporter/API/store/types/charts/tests；未發現 IC UI 的歷史 report import/load 路徑，故「舊 artifact 重新載入」目前只能做 component synthetic seam，非真實 ingestion。
TESTS_RUN: `rg -n -S '(factor_return|factor_returns|long_short_mean_return|ls_cumulative|long_short_analysis)' api momentum frontend/src tests scripts` + 指定檔 `nl/sed`，完成 consumer-map；未跑 pytest（使用者限定唯讀，且 repo 文件已記 collect 有 tracked side effect）。
FAILURES_SEEN: 兩次 read-only Python import probe 各等待 60s/30s 無輸出後終止；依 debug 上限停止，裁決只採靜態可定位證據。
SCOPE_CHANGES: none（僅新增本檔）；建議 SPEC 擴 scope 至 config YAML/API model/tier+store、FactorEquityCurveChart、集中 sanitizer、caller denylist 與列名測試。
NUMERIC_OR_SCHEMA_IMPACT: 審查未改數值/schema；提案會新增精確 unavailable module union，且移除所有對外 finite 錯位值，CSV 欄名可保留但值須空。
SPEC-REVIEW: REJECT(6 BLOCKING)

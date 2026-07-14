# IC1C-FR-STOPGAP TODO(**Frozen r3(2026-07-14)**——三輪三家 adversarial 全閉合(codex/composer/grok APPROVE),RECONCILE-STAMP 機檢 PASS(body 7bf42307)/基於 docs/IC1CFR_STOPGAP_SPEC.md v1.0 Frozen/2026-07-14;r1 三家 REJECT(codex 5B/composer 7B/grok 2B)→r2 T-S1~T-S8;codex r2 REJECT(4B)→r3 T-S9~T-S12(sanitizer 檔路徑+七掛點具名/nodeid --check-nodeids 機械 gate/allowlist 含 factories.py:454/前端 vitest 命令修正),見 handoffs/20260714-IC1CFR-STOPGAP-TODO-RECONCILE.md)

## §0 全域規則與約束(執行端讀完即可遵守)
- **目標=下架錯位因子報酬輸出,不修計算**:`factor_return_analyzer.py`/`monotonicity_tester.py` 計算本體**不動**(修復歸 1c-FR-FULL)。**不動清單**:`long_short_analysis`(r1 三家裁不同病,出 scope)、net_ic(已 B-strict)、trend dimensions(ic_config_schema:193)、factory/analyzer class 本體。
- **default-off 契約(選項 B,三態)**:①非顯式(含純 intermediate/advanced tier)→現行 `not_run`+無 results 節(零額外碼);②顯式開啟(`force_modules=["factor_returns"]` 或 config_override/modules enabled=true,**且 deep 全域開**)→runner `raise ModuleUnavailableError`→父迴圈專屬 except 分支寫 §U union `{status:"unavailable",value:null,reason:"ls_returns_timestamp_misaligned (1c-FR-FULL)"}`+summary `unavailable`+**不入 deep_analysis_errors**+不計 completed/skipped;③deep 全域關→force 亦 `not_run`(force 不跨 :1601 早退)。
- **鍵名**:config/API 側**單數 `factor_return`**;results/summary 側**複數 `factor_returns`**;勿混。
- **輸出邊界 sanitizer(T-S2,關鍵洩漏路徑全補)**:**momentum-side 純函式**(避免 momentum import api),兩端呼叫;掛點=①orchestrator 記憶體 cache hit `ic_filter_orchestrator.py:1629-1636`(`deepcopy→return cached` 繞過 runner,**此路徑必過 sanitizer**)②API raw JSON `ic_analysis_service.py:437-438`③service serializer+`task_info["deep_analysis_result"]`(:678,:827)+`get_deep_analysis_result`(:709)④detailed CSV⑤AI JSON⑥Markdown⑦export_all raw dump `ic_reporter.py:334-335`。冪等;涵蓋 legacy 有限 payload。
- **JSON strict**:禁有限 numeric leaf 落 factor_returns 節。
- 解耦 7 條不得破(`check_decoupling.sh` 全綠);離線可 collect(conftest stub);禁碰 data_cache;禁合成 fixture(用真-kline `tests/fixtures/ic_api_real_kline.py`)。
- 防假綠:改寫既有 factor_return 測試逐條附「舊斷言為何錯」;commit VERIFY:<receipt>。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 規模 |
|-------|---------|------|------|
| B0 | §G before 凍結 | 無 | 小 |
| B1 | 1.1+1.2+1.3(後端下架+sanitizer+factory gate) | B0 | 中 |
| B2 | 2.1+2.2(前端兩圖下架) | B1 | 小-中 |
- Gate B0→B1:`python scripts/ic1cfr_stopgap_freeze.py --before` exit 0(before.json+**canonical hash**:排除 total_execution_time_s/generated_at/error timestamp 後算,T-S1);另 factory allowlist 凍結(見 Task 0.1)。
- Gate B1→B2:`venv/bin/pytest tests/momentum/Analysis/test_factor_return_stopgap.py tests/api/test_ic_deep_analysis.py -q` 全綠+`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_return_stopgap.py tests/api/test_ic_deep_analysis.py` PASS+`python scripts/ic1cfr_stopgap_freeze.py --after-default && python scripts/ic1cfr_stopgap_freeze.py --after-explicit`(§G 三版本,T-S5)exit 0+`bash scripts/check_decoupling.sh` PASS。
- Gate B2 完(r3 修 codex-B2/B4,命令機械可判定):
  - 前端:`npm --prefix frontend run test -- src/components/ic-analysis/FactorReturnChart.test.tsx src/components/ic-analysis/FactorEquityCurveChart.test.tsx src/components/ic-analysis/NetICChart.test.tsx`(**分開 filter+具名檔路徑**;vitest 把整串當單一 literal 檔名會 rc=1 找不到測試,codex 實跑證)+`npm --prefix frontend run build`。
  - 後端回歸:`python scripts/ic1cfr_stopgap_freeze.py --check-nodeids`——腳本自跑 `venv/bin/pytest tests/momentum/ tests/api/ tests/phase26/ -q`(**與 B0 凍結時完全相同 suite/收集規則**)、解析 failed+collection-error nodeid、與 `handoffs/ic1cfr_stopgap_baseline/pytest_baseline_nodeids.txt` 做差集:**新增失敗非空→exit 1 並列出**;子集→exit 0。禁人工括號豁免。
- 執行端=Grok(workspace);審查=Codex+Composer。

## Phase 0 — §G before 凍結
### Task 0.1 — before baseline
- SPEC ref:§G　目標:凍結下架前 deep 全模組輸出(含 factor_returns 有限值,作對照)。
- 實作:新 `scripts/ic1cfr_stopgap_freeze.py --before|--after-default|--after-explicit`;`--before` 用真-kline fixture 跑 `run_deep_analysis`(全模組 enabled)→dump `handoffs/ic1cfr_stopgap_baseline/before.json`(sort_keys)+**canonical hash**(T-S1:hash 前剔除 total_execution_time_s/generated_at/error timestamp 等漂移欄,artifact 保原值);記 lineage;②`--after-explicit`=force_modules=["factor_returns"] 跑→`after_explicit.json`(§U union 對照);③**凍 factory allowlist+pytest baseline nodeids**:`rg -n "create_factor_return_analyzer" momentum api scripts tests`(唯一 caller=phase26)與 `rg -n "FactorReturnAnalyzer\("` direct consumer 集、全套件 failed/error nodeid → `handoffs/ic1cfr_stopgap_baseline/{factory_allowlist.txt,pytest_baseline_nodeids.txt}`。
- 驗證:`python scripts/ic1cfr_stopgap_freeze.py --before` exit 0;canonical 重跑 hash 一致(剔除漂移欄後);before.json 含 `results.factor_returns` 有限值+`module_summary.factor_returns=="completed"`(codex CX-4 基準)。
- 邊界:重跑 canonical hash 一致;非有限值不落 NaN 字面。
- 不可做:不改任何 runtime;canonical 不得剔除 factor_returns 本體值欄(只剔時間/計數 meta)。

## Phase 1 — 後端下架
### Task 1.1 — 四處預設關閉+tier 排除+runner raise+父迴圈 except 分支
- SPEC ref:Task 1.1/§C S-F9~F12　目標:default-off 三態契約落地。
- 實作要點:①四處預設 false:`ic_config_schema.py:173`(`FactorReturnConfig.enabled=False`)/`config/ic_config.yaml:115-116`/`api/models/ic_models.py:22`(`factor_return: bool=False` 單數)/`icAnalysisStore.ts:107,133,151`;②`_apply_tier_config:3371` 從 tier 強制 true 清單排除 `factor_return`(讀 :3335-3378 確認 clause,勿誤動他模組);③新 `ModuleUnavailableError`(放 momentum 適當 exceptions 模組);④`_run_factor_return` 改 `raise ModuleUnavailableError("ls_returns_timestamp_misaligned (1c-FR-FULL)")`(刪 compute_batch 呼叫);⑤父迴圈(:1665-1690)在 `except Exception` **之前**加 `except ModuleUnavailableError as e`:`base_report.results[module_name]={"status":"unavailable","value":None,"reason":str(e)}`+`base_report.module_summary[module_name]="unavailable"`(不 append deep_analysis_errors);⑥`completed_count`/skipped_count(:1698-1703)現碼只計 `"completed"`/`"skipped"` 字串→`unavailable` **自然排除,無需新增第三桶**(codex 修正)。
- 驗證:新 `tests/momentum/Analysis/test_factor_return_stopgap.py`:`test_default_off_not_run`/`test_pure_tier_not_run`(intermediate+advanced)/`test_explicit_enable_unavailable`(force+override 兩路徑→union+無有限葉+summary unavailable+`assert "factor_returns" not in [e.module for e in report.deep_analysis_errors]`)/`test_deep_off_not_run`;`pytest -k factor_return -q` 綠。
- 邊界:①force(deep 開)→union;②override enabled:true→union;③純 tier→not_run;④預設→not_run;⑤deep 關→not_run。
- 不可做:不動 analyzer/monotonicity 計算;不動 :193 trend;pure-tier 不當顯式開啟;不 append errors。

### Task 1.2 — 輸出邊界 sanitizer
- SPEC ref:Task 1.2/S-F3　目標:堵 legacy/cache 有限值。
- 實作要點:①新檔 **`momentum/Analysis/factor_return_sanitizer.py`**(路徑定死,r3 修 codex-B1;momentum-side 純函式,**禁 import api**)含 `sanitize_factor_returns(payload) -> dict` 冪等:遞迴把 `factor_returns` 節換佔位、summary 三欄(factor_return_ls_mean/sharpe/max_drawdown)→null;②掛 §0 七類掛點:(a) orchestrator cache-hit `ic_filter_orchestrator.py:1629-1636`(return cached 前)(b) API raw JSON `ic_analysis_service.py:437-438`(c) service `_serialize_deep_report`+task storage `task_info["deep_analysis_result"]`(:678,:827)+`get_deep_analysis_result`(:709)(d) detailed CSV (e) AI JSON (f) Markdown (g) export_all `ic_reporter.py:334-335`。
- 驗證(**七類各至少一具名測試**,防單條假綠;storage/get 可合併 round-trip;皆置於 `tests/api/test_ic_deep_analysis.py`,以 `venv/bin/pytest tests/api/test_ic_deep_analysis.py -k sanitizer -q` 全綠):`test_sanitizer_cache_hit_legacy`(a)+`test_sanitizer_raw_json_legacy`(b)+`test_sanitizer_task_storage_roundtrip`(c:寫入 task_info→`get_deep_analysis_result` 取出皆無有限葉)+`test_sanitizer_csv_legacy`(d)+`test_sanitizer_ai_json_legacy`(e)+`test_sanitizer_markdown_legacy`(f)+`test_sanitizer_export_all_legacy`(g)+`test_sanitizer_idempotent`(佔位再過→不變)。
- 邊界:①in-mem cache 命中舊有限→sanitize;②缺 factor_returns 鍵→不 crash;③冪等。
- 不可做:不動其他模組節;sanitizer 不 import api。

### Task 1.3 — factory gate+腳本 quarantine
- SPEC ref:Task 1.3/S-F6　目標:堵繞過 UI/API 的直接 analyzer 消費。
- 實作要點(T-S7,allowlist 凍死勿留執行端自由校準):①`scripts/phase29_perf_validation_tmp.py` 刪除或頂部 `raise SystemExit("quarantined: ls_returns misaligned, see 1c-FR-FULL")`;②守衛測試 `test_factor_return_consumer_allowlist`:讀 B0 凍結的 `factory_allowlist.txt`——**factory caller allowlist={`tests/phase26/test_deep_analysis_factories.py`}**(factory 定義不算 caller;實跑確認唯一 caller);**另掃 direct `FactorReturnAnalyzer(` production consumer,允許={`momentum/factories.py:454`(factory 定義體內建構,r3 補 codex-B3)、orchestrator `_run_factor_return`(:1780-1785)、phase24 analyzer 測}**,超出集合(新繞路)→紅;scanner 正規化規則(是否排除 factory 定義體)B0 artifact 與測試共用同一份。
- 驗證:`pytest tests/momentum/Analysis/test_factor_return_stopgap.py -k consumer -q` 綠;`rg create_factor_return_analyzer` caller⊆{phase26};`rg "FactorReturnAnalyzer\("` consumer⊆凍結集。
- 邊界:allowlist 由 B0 凍結檔載入(非測試內臆測)。
- 不可做:不刪 factory/class 本體(1c-FR-FULL 用);不把 orchestrator 寫進 **factory** 白名單(它走 direct 實例化,語意錯位)。

### Phase 1 §V mutation(同檔 probe,基線綠→注入紅→還原)
- M1 `test_mutation_m1_restore_compute_batch`(runner 恢復直出→`test_explicit_enable_unavailable` 紅);M1b `test_mutation_m1b_drop_tier_exclusion`(移除 tier 排除→`test_pure_tier_not_run` 紅);M2 `test_mutation_m2_bypass_sanitizer`(繞 sanitizer→legacy payload 測試紅)。

### §V 改寫表(T-S6,舊斷言逐筆為何錯;grep 命中全列)
| 檔:行 | 舊斷言 | 為何錯 |
|--------|--------|--------|
| `tests/phase24/test_deep_analysis_config.py:33` | `factor_return.enabled is True` | 預設改 False(止血) |
| `tests/momentum/test_tier_config.py:31` | tier 後 enabled is True | tier 排除 factor_return 強制 |
| `tests/phase26/test_deep_analysis_integration.py`(多處) | force→`completed` | 顯式開→`unavailable` 非 completed |
| `tests/api/test_ic_deep_analysis.py` | 注入 finite factor_returns+samples | sanitizer 下架→無有限葉 |
| `tests/momentum/test_export_formats.py:154` | 含 `long_short_mean_return` 有限值 | CSV 欄→null |
| `tests/api/test_export_api.py:96` | 同上 | 同上 |
| `tests/phase26/test_ic_reporter_deep_analysis.py` | 有限 factor_returns 節 | 佔位 |
執行端據實跑 grep 補漏並逐筆註記。

## Phase 2 — 前端下架
### Task 2.1 — FactorReturnChart+types
- SPEC ref:Task 2.1　目標:C22 區 factor_return 圖下架。
- 實作要點:①`FactorReturnChart.tsx`:讀到 union 佔位**或** legacy 有限值(無 status 鍵)→警示空態「錯位序列已下架,待 1c-FR 重建」;②`types.ts`:**改實際 `ICReport.factor_returns`/`FactorReturnData` 形狀為 §U discriminated union**(T-S4,非只新增型別);③掛載處 error/loading/empty 三態齊。
- 驗證:vitest `shows_unavailable_notice`+`legacy_finite_payload_not_rendered`+**同檔 M3 probe `test_mutation_m3_render_legacy`**(恢復畫 legacy→紅);`npm --prefix frontend run build` 綠(tsc 過=型別真改);`grep -n "1c-FR" FactorReturnChart.tsx`≥1。
- 邊界:①佔位;②legacy 有限;③缺鍵。
- 不可做:禁 fallback 數值。

### Task 2.2 — FactorEquityCurveChart 獨立下架(S-F2)
- SPEC ref:Task 2.2　目標:獨立同病圖(位置相減 equity curve)下架。
- 實作要點:①`FactorEquityCurveChart.tsx`(掛載 page.tsx:790-794):整圖→警示空態(同 2.1 文案);②producer `monotonicity_tester` 不動(1c-FR-FULL 修)。
- 驗證:vitest `equity_curve_unavailable_notice`+`equity_legacy_finite_not_rendered`+**同檔 M4 probe `test_mutation_m4_render_legacy_equity`**(恢復畫 legacy→紅,T-S3 正名);build 綠。
- 邊界:主流程與 deep 報告載入皆下架。
- 不可做:不改 quantile_returns 資料本體。

---
覆蓋追溯:SPEC Task 0.1/1.1/1.2/1.3/2.1/2.2(6/6)→同名;§C S-F9~F13→Task 1.1+§G;M1/M1b/M2→Phase 1 mutation、**M3→Task 2.1、M4→Task 2.2**(T-S3 正名);§G **三版本**(before/after-default/after-explicit)→Task 0.1+B1 Gate;§V 改寫表 7 筆→Phase 1 §V 節;factory allowlist→B0 凍結+Task 1.3;long_short_analysis 出 scope→§0 不動清單。
SPEC=docs/IC1CFR_STOPGAP_SPEC.md TODO=docs/IC1CFR_STOPGAP_TODO.md FOCUS=下架完整性+default-off 三態+sanitizer 邊界全覆蓋

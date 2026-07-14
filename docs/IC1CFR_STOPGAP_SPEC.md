# IC1C-FR-STOPGAP — 錯位因子報酬輸出止血 — SPEC

> 來源:handoffs/20260714-IC1CFR-NECESSITY-RECONCILE.md(四方委員會+使用者定案「立即止血」)　|　日期:2026-07-14　|　對應 TODO:docs/IC1CFR_STOPGAP_TODO.md(凍結後生)　|　版本:**v1.0 Frozen(2026-07-14)**——r4 三家 APPROVE(codex CX-1~4 CLOSED/grok/composer),RECONCILE-STAMP 機檢 PASS(body 66db1109);歷史 r4=(r3:composer APPROVE;codex 4B+grok 1B 收斂於 tier→佔位矛盾+控制流細節;r4 精化:pure-tier=not_run/ModuleUnavailableError 專屬 except/force 不跨 deep-off/§G before 用實凍值)

## §RISK 風險分級
- **大小**:中(fail-close 下架+邊界 sanitizer,不動計算核心)。
- **命中**:(a) 數值品質;(b) 跨模組。
- RISK-HIT: a,b
- 命中 (a) → 三家 adversarial(r1 已跑)+§G 隔離 golden。

## §A 假設與待使用者確認
- FACT-RECEIPT: `sed -n '85,90p' momentum/Analysis/factor_return_analyzer.py` → `ls_returns` reset_index 位置相減 timestamp 錯位(codex CODEX-1 實證,necessity 委員會複核 2026-07-14)。
- FACT-RECEIPT(r3 再更正): 預設 true 共**四處**——`ic_config_schema.py:172-173`(`FactorReturnConfig.enabled=True`)/`config/ic_config.yaml:115-116`/`api/models/ic_models.py:22`(欄位名=**單數 `factor_return: bool=True`**,勿寫成 factor_returns)/`frontend/src/store/icAnalysisStore.ts:107,133,151`;另 `momentum/Analysis/ic_filter_orchestrator.py::_apply_tier_config`(**def@:3335,強制 true@:3371**;非 ic_analysis_service,r3 更正 GROK-R2-B1)。`ic_config_schema.py:193`=trend dimensions 字串,本票不動。
- FACT-RECEIPT(r3,鍵名不一致警示): config/API 欄位=單數 `factor_return`;但 `module_summary` 與 orchestrator results 節鍵=**複數 `factor_returns`**(`ic_filter_orchestrator.py:1604`)。實作勿混用:config 側 singular、輸出/summary 側 plural。
- FACT-RECEIPT(r3,default-off 現行契約,CX-R2-1): `ic_filter_orchestrator.py:1603-1610` 模組未啟用時 `module_summary.factor_returns="not_run"` 且**不建 results.factor_returns 節**(runner 根本不入列 :1651-1657)——此為既有誠實狀態。
- FACT-RECEIPT(r2 新增,CX-2): `FactorEquityCurveChart` 走主流程 `quantile_returns`(page.tsx:790-794),producer `momentum/Analysis/monotonicity_tester.py:43-55` **丟 timestamp**,chart `:79,92-110,143-155` 按位置做 high-low/drawdown/Sharpe——**獨立同病路徑**(codex 實證 2026-07-14)。
- FACT-RECEIPT: `ic_reporter.py:579-592` deep summary 三欄+`:195-228,639-662` detailed CSV+`:230-359` AI/Markdown/export_all+`:728-778` serialization 皆可透傳 finite legacy payload(codex 實證)。
- **委員已裁(r1 三家一致)**:`long_short_analysis` **不同病**(index-align、無位置相減),出 scope,列 §G unchanged allowlist;其 irregular-subset Sharpe 語意另票候選。
- **待使用者確認**:待確認:無。**已確認結果**:`2026-07-14 使用者(AskUserQuestion)`:止血立即;1c-FR-FULL=1d 後近期。

## §C 約束與 consumer-map
- 觸點:①四處預設+tier 強制(§A);②orchestrator `_run_factor_return`(改佔位出口);③**output-boundary sanitizer**(S-F3):單一函式覆蓋 API result/detailed CSV/AI/Markdown/export_all/serialization/cache hit——`factor_returns` 節遞迴**禁任何有限 numeric leaf**(allowlist=`status`/`reason` 字串+`value:null`);④reporter 三欄(:579-592)讀佔位→null;⑤前端 `FactorReturnChart`+**`FactorEquityCurveChart`(獨立同病,Task 2.2)**+`types.ts`;⑥factory gate:`create_factor_return_analyzer` 保留(1c-FR-FULL 用)但 caller 白名單=analyzer 自身測試+stopgap runner,`scripts/phase29_perf_validation_tmp.py:30` 刪或標 quarantine;⑦既有測試 `grep -rn "long_short_mean_return\|quantile_returns_summary" tests/` 逐筆列改寫表。
- **default-off 契約定案(S-F9=選項 B,r4 精化;codex R3-CX-1~4+grok R3-B1 收斂)**:三態互斥,與 orchestrator 實際控制流(`ic_filter_orchestrator.py:1601-1700`)對齊——
  - **非顯式開啟(含純 tier preset:intermediate/advanced 皆算,factor_return 已從 tier 強制清單排除)**:module 不入 run_targets → **現行 `not_run`+無 results 節**(誠實,零額外碼)。**tier 不再是「顯式開啟」路徑**(r4 更正 r3 邊界③錯誤:codex CX-1/grok B1)。
  - **顯式開啟(僅二途:`force_modules=["factor_returns"]` 或 config_override/modules 明設 enabled=true,且 deep analysis 全域為開)**:runner `_run_factor_return` **raise 專屬 `ModuleUnavailableError(reason="ls_returns_timestamp_misaligned (1c-FR-FULL)")`**;父迴圈(:1665 區)**加一個先於通用 except 的專屬分支**:`results.factor_returns={"status":"unavailable","value":null,"reason":...}`(§U union)+`module_summary="unavailable"`+**不 append deep_analysis_errors**(非錯誤,是刻意下架)+`completed_count`/`skipped_count` 皆不計此模組(新增 unavailable 桶或明確排除)。此為唯一觸碰父迴圈處,精確可控(解 codex CX-2 寫入者)。
  - **force 不跨全域 deep-off**(codex CX-3):`:1601` deep disabled 早退在 force_set 建立前——裁定 force **不**繞過;deep 全關時 factor_returns 隨全體=`not_run`(無 runner 執行=無有限值,安全)。契約收窄至「deep 開 + 顯式開啟」。
  - **輸出邊界有限值**(cache/legacy/舊 report)→ sanitizer 轉佔位(Task 1.2)。
  - TS 涵蓋:節缺席(not_run/deep-off) | `{status,value,reason}` union(顯式開啟) | sanitizer 佔位;禁有限葉。
- 不動 `factor_return_analyzer.py`/`monotonicity_tester.py` 計算本體(1c-FR-FULL);不動 net_ic;`long_short_analysis` 不動。
- 解耦 7 條不得破;`check_decoupling.sh` 全綠;離線可 collect(沿 conftest stub)。

## §G Golden / Baseline(S-F5)
- 真-kline fixture(`tests/fixtures/ic_api_real_kline.py`)動工前跑 deep 全模組凍 `handoffs/ic1cfr_stopgap_baseline/before.json`;改後同 fixture:
  1. **逐 JSON path 比對**(非 byte):**僅比 `results[非 factor_returns 模組]` 本體**排序 dump 等值;**排除清單寫死**=`total_execution_time_s`/`generated_at`/error timestamp/壁鐘欄+**頂層計數**(`completed_count`/`skipped_count`/`deep_analysis_summary.completed` 等,因 factor_returns 狀態改變必漂,grok R2-NB3);
  2. **scope-expected 變更**(default-off golden 版本):`results.factor_returns` 節**改前有限值→改後缺席**(default off 不建節)+`module_summary.factor_returns`:**改前實凍值(成功 fixture 為 `completed`)→改後 `not_run`**(codex CX-4:用 before.json 實凍值,`enabled` 狀態不存在);另**顯式開啟 golden 版本**(force_modules 跑一次):節==§C union(遞迴無有限 numeric leaf)+summary==`unavailable`+不在 deep_analysis_errors;
  3. reporter summary 三欄+detailed CSV 對應欄==null 或欄缺席;AI/Markdown/export_all 無 finite FR 值(sanitizer 出口驗,注入 legacy finite payload 為 oracle)。
- 通過=比對腳本 exit 0(非 scope 模組 path 值 exact match,浮點欄 `atol=0`〔下架票不引入計算誤差,任何漂移=FAIL〕;before.json 存 sha256 防竄改);FAIL 列 path diff。

## §P Phase 與依賴
### Phase 1 — 後端下架(依賴:無)
**Task 1.1 — 四處預設關閉+tier 例外+runner 佔位(default-off=not_run)**
- 檔案:`ic_config_schema.py:173` enabled→False;`config/ic_config.yaml:115-116` 同步;`api/models/ic_models.py:22` **`factor_return: bool=False`(單數)**;`icAnalysisStore.ts:107,133,151` 預設 false;`ic_filter_orchestrator.py::_apply_tier_config:3371` 從 tier 強制 true 清單**排除 `factor_return`**;新例外 `ModuleUnavailableError`;`_run_factor_return` 改 `raise ModuleUnavailableError(...)`(不呼叫 compute_batch);父迴圈(:1665-1690)在通用 except **之前**加 `except ModuleUnavailableError` 分支寫 §C union+summary unavailable+不入 errors+不計 completed/skipped。
- 驗證:新 `tests/momentum/Analysis/test_factor_return_stopgap.py`:`test_default_off_not_run`(預設 request→summary `not_run`+無 results 節)+`test_pure_tier_not_run`(active_preset=intermediate/advanced 無 force/override→`not_run`,證 tier 排除生效)+`test_explicit_enable_unavailable`(force_modules 或 enabled=true override→union+無有限葉+summary `unavailable`+不在 deep_analysis_errors)+`test_deep_off_not_run`(deep 全關→force 亦 not_run);`pytest tests/momentum -k factor_return -q` 綠。
- 邊界:①`force_modules=["factor_returns"]`(deep 開)→union;②config_override enabled:true→union;③純 intermediate/advanced tier→**not_run**(非佔位,r4 更正);④預設→not_run 無節;⑤deep 全域關→not_run。
- 不可做:不動 analyzer/monotonicity_tester 本體;不動 trend dimensions(:193);不把 pure-tier 當顯式開啟(codex CX-1);不 append deep_analysis_errors(非錯誤)。
**Task 1.2 — 輸出邊界 sanitizer(S-F3)**
- 檔案:單一 `sanitize_factor_returns(payload)` 函式,掛在**所有對外輸出邊界**(執行端以 `grep -n "factor_returns\|def _serialize\|def _build.*csv\|export_all\|to_dict" ic_analysis_service.py ic_reporter.py` 定位精確行,r3 不寫死可能過時的行號):API result 序列化 / detailed CSV / AI JSON / Markdown / export_all / report 反序列化 / **cache 命中路徑**——任何來源之 `factor_returns` 節(含 legacy 有限 payload)→佔位;summary 三欄→null。sanitizer 為**冪等**(佔位再過一次不變)。
- 驗證:`tests/api/test_ic_deep_analysis.py::test_factor_return_sanitizer_legacy_payload`(注入 finite legacy payload→輸出無有限葉,CX-3 反例轉正式測試);export 各格式斷言。
- 邊界:①cache 命中舊結果→sanitize;②payload 缺 factor_returns 鍵→不注入不 crash。
- 不可做:不動其他模組節。
**Task 1.3 — factory gate+腳本 quarantine(S-F6)**
- 檔案:`scripts/phase29_perf_validation_tmp.py` 刪除(tmp 腳本)或頂部 raise+quarantine 註記;新守衛測試 `test_factor_return_factory_callers`:`grep create_factor_return_analyzer` caller 白名單=analyzer tests+orchestrator runner,超出→紅。
- 驗證:`pytest tests/momentum/Analysis/test_factor_return_stopgap.py -q` 綠。
- 邊界:白名單常數寫死於測試。
- 不可做:不刪 factory 本體。

### Phase 2 — 前端下架(依賴:Phase 1)
**Task 2.1 — FactorReturnChart+types**
- 檔案:`FactorReturnChart.tsx`:讀到佔位/legacy 有限值(無 status 鍵)→警示空態「錯位序列已下架,待 1c-FR 重建」;`types.ts` union 同構。
- 驗證:vitest `shows_unavailable_notice`+`legacy_finite_payload_not_rendered`;`npm --prefix frontend run build` 綠;`grep -n "1c-FR" FactorReturnChart.tsx` ≥1。
- 邊界:gross-only/缺鍵/舊 artifact 三態。
- 不可做:禁任何 fallback 數值。
**Task 2.2 — FactorEquityCurveChart 獨立下架(S-F2,CX-2)**
- 檔案:`FactorEquityCurveChart.tsx`(或掛載處 page.tsx:790-794):該圖以錯位 quantile_returns 做位置 high-low——整圖下架為警示空態(同 Task 2.1 文案);producer `monotonicity_tester` 不動(修復歸 1c-FR-FULL)。
- 驗證:vitest 具名 `equity_curve_unavailable_notice`;build 綠。
- 邊界:主流程(非 deep)報告載入同樣下架。
- 不可做:不改 quantile_returns 資料本體(其他消費者依委員 r1 掃描無同病位置相減者;委員 r2 複核)。

## §V 驗證策略(S-F5)
| # | Property | Oracle | test(檔:函式) | 同檔 probe |
|---|----------|--------|---------------|------------|
| M1 | 顯式開啟 runner 不可繞出有限值 | 恢復 `compute_batch` 直出(不 raise)→紅 | `test_factor_return_stopgap.py::test_explicit_enable_unavailable` | `test_mutation_m1_restore_compute_batch` |
| M1b | tier 排除生效:純 tier=not_run 非佔位 | 移除 tier 排除→intermediate 變 enable→跑 runner(仍 union 無有限葉,但 pure-tier not_run 測試轉態) | 同檔 `test_pure_tier_not_run` | `test_mutation_m1b_drop_tier_exclusion`(移除排除→`test_pure_tier_not_run` 紅) |
| M2 | sanitizer 有牙 | 注入 finite legacy payload→輸出無有限葉 | `test_ic_deep_analysis.py::test_factor_return_sanitizer_legacy_payload` | `test_mutation_m2_bypass_sanitizer` |
| M3 | 前端不畫 legacy 有限值 | 無 status+有限值 payload→空態 | T4 vitest `legacy_finite_payload_not_rendered` | 同檔 `test_mutation_m3_render_legacy` |
| M4 | equity curve 下架 | 該圖恒空態 | vitest `equity_curve_unavailable_notice` | 同檔 probe |
- Python 側 `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_return_stopgap.py tests/api/test_ic_deep_analysis.py`;前端 vitest 獨立驗收命令。
- 改寫表:`grep -rn "long_short_mean_return\|quantile_returns_summary" tests/` 逐筆列(舊斷言=固化錯位輸出形狀)。

## §R 回退
- 每 Phase 獨立 commit revert;佔位 additive;1c-FR-FULL 完成後同位點亮(含 equity curve)。

## §N N/A 登記
- 三方數據簽核鐵律全文:N/A——不生成/merge/split feature;改以三家 adversarial+隔離 golden 承擔(見上節)。
- `long_short_analysis`:N/A——r1 三家一致不同病,出 scope(irregular Sharpe 另票候選,記 ROADMAP)。

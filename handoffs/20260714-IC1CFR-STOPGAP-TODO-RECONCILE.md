# STOPGAP TODO 審查 RECONCILE(r1)— Claude 主編(2026-07-14)

verdicts: codex REJECT(5B)/composer REJECT(7B)/grok REJECT(2B) → TODO 退 r2。

## 合併裁決(全 ACCEPT;跨家同源合併)

| 主題 | 來源 | r2 落點 |
|------|------|---------|
| T-S1 §G before hash 矛盾 | codex-B1 | Task 0.1:dump 保原值但 **hash 前 canonicalize**(排除 total_execution_time_s/generated_at/error timestamp)再算;或凍一次+驗同 bytes。禁「兩次真跑 raw JSON 同 hash」。 |
| T-S2 sanitizer 掛點漏 cache/raw-JSON+放置檔 | codex-B2+composer-B4/B5+grok-NB-S2 | **關鍵洩漏路徑補全**:①orchestrator 記憶體 cache hit `:1629-1636` `deepcopy→return cached` 繞過 runner/sanitizer→**cache 命中出口也過 sanitizer**;②API raw JSON `ic_analysis_service.py:437-438`;③export_all raw dump `ic_reporter.py:334-335`;④service serializer+`task_info["deep_analysis_result"]`(:678,:827)+`get_deep_analysis_result`(:709)。sanitizer=**momentum-side 純函式**(避免 momentum import api),兩端呼叫(orchestrator cache-hit + api 邊界);逐掛點各具名測試。 |
| T-S3 M3/M4 probe 綁錯 | codex-B3+composer-B1/B2+grok-B2 | Task 2.1 加同檔 `test_mutation_m3_render_legacy`(FactorReturnChart legacy 不畫);Task 2.2 probe 改 `test_mutation_m4_render_legacy_equity`;§V+覆蓋追溯同步 M3→2.1/M4→2.2。 |
| T-S4 types.ts 未改實際形狀 | composer-B3 | Task 2.1 明改 `ICReport.factor_returns`/`FactorReturnData` 為 §U union 形狀(非只加新型別)。 |
| T-S5 §G 顯式開啟版本缺 after 檔 | composer-B6 | Task 0.1/freeze 腳本加 `--after-explicit`(force_modules 跑一次)→`after_explicit.json`:節==§U union+summary unavailable+不在 errors;Gate 三版本(before/after-default/after-explicit)。 |
| T-S6 §V 改寫表缺逐筆 | composer-B7+grok-NB-R1 | §0/新 §V 節列 grep 命中逐筆表(grok 清單):tests/phase24/test_deep_analysis_config.py:33、test_tier_config.py:31、phase26/test_deep_analysis_integration.py(force→completed 多處)、api/test_ic_deep_analysis.py(注入 finite)、test_export_formats.py:154、api/test_export_api.py:96、phase26/test_ic_reporter_deep_analysis.py;各附「舊斷言為何錯」。 |
| T-S7 factory 白名單交執行端=不可 | grok-B1+codex-B5 | **B0 凍死精確 invocation allowlist**:實跑 `rg create_factor_return_analyzer` 現況=**唯一 caller `tests/phase26/test_deep_analysis_factories.py`**(factory 定義不算 caller);orchestrator:1780-1785+phase24 測試是**直接 `FactorReturnAnalyzer(` 實例化非 factory**。Task 1.3 改:①factory-caller allowlist={phase26 factory 測};②另掃 **direct `FactorReturnAnalyzer(` production consumer**,允許={orchestrator runner、phase24 analyzer 測};③phase29 tmp 腳本 quarantine。勿把 orchestrator 寫進 factory 白名單(語意錯位)。 |
| T-S8 B2 backend gate 無 pass/fail 判定 | codex-B4 | §B B2 backend gate 改:**frozen baseline nodeid 集差分**(改前全套件 failed/error nodeid 凍為 allowlist,改後不得新增失敗);禁「既有紅非本票」人工括號豁免。 |

## 通過項(委員確認,r2 保留)
- Task 1.1 專屬 except 在通用前+union/summary/不入 errors;現碼計數只計 completed/skipped(:1698-1703)→unavailable 自然排除,**無需發明第三計數**(codex 修正我 SPEC「新增 unavailable 桶」措辭,r2 對齊)。
- gate 工具離線可解析。

## 下一步
TODO r2 → 三家閉合 → 戳記 → 實作。

## r2 輪閉合記錄(2026-07-14,Claude 補記)
- codex r2:T-S1(canonical hash)/T-S3(M3-M4)CLOSED;REJECT(4B)=B1(sanitizer 檔路徑未定+七掛點漏具名測試)+B2(baseline nodeid 無機械 gate 命令)+B3(direct allowlist 漏 momentum/factories.py:454 factory 定義體建構)+**B4 新洞**(codex 實跑 `npm --prefix frontend run test -- "NetIC|FactorReturn|FactorEquity"` → vitest 當單一 literal 檔名,rc=1 找不到測試=gate 零測試假綠)。
- **r3 裁決(全 ACCEPT)**:T-S9 sanitizer 檔路徑定死 `momentum/Analysis/factor_return_sanitizer.py`(momentum-side 純函式禁 import api)+七類掛點各具名測試(cache-hit/raw-JSON/task-storage round-trip/CSV/AI/Markdown/export_all/冪等);T-S10 `--check-nodeids` 機械 gate(腳本自跑同一 suite→解析 failed+collection-error→與 B0 baseline 差集→新增失敗 exit 1);T-S11 direct allowlist 補 `momentum/factories.py:454`+scanner 正規化規則 B0/測試共用;T-S12 前端 gate 命令改分開具名檔路徑(三檔)。
- TODO r3;交三家閉合(codex 驗 4B;composer/grok 驗其 r1 finding 對 r3)。

## 戳記
RECONCILE-STAMP: composer APPROVED 2026-07-14 sha256:7bf423071cb5d04454916f234b3c168d91724542c992e5aca98b5b8a8722e8bd task:IC1CFR-STOPGAP-TODO
RECONCILE-STAMP: codex APPROVED 2026-07-14 sha256:7bf423071cb5d04454916f234b3c168d91724542c992e5aca98b5b8a8722e8bd task:IC1CFR-STOPGAP-TODO
RECONCILE-STAMP: grok APPROVED 2026-07-14 sha256:7bf423071cb5d04454916f234b3c168d91724542c992e5aca98b5b8a8722e8bd task:IC1CFR-STOPGAP-TODO

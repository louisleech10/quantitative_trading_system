# STOPGAP SPEC 審查 RECONCILE(r1)— Claude 主編(2026-07-14)

verdicts: codex REJECT(6B)/composer REJECT(3B)/grok REJECT(4B) → SPEC 退回 r2。

## 合併裁決(全 ACCEPT)

| 主題 | 來源 | r2 落點 |
|------|------|---------|
| S-F1 行號錯誤+預設 true 四處 | CX-1+GROK-B1 | FACT 更正 `:173`;Task 1.1 擴為關閉四處預設(schema:173/yaml:115-116/ic_models:21-29/store:107,133,151)+`_apply_tier_config:3369-3371` tier 強制 true 對 factor_return 例外;`:193` trend dimensions 不動(grok:另決策) |
| S-F2 FactorEquityCurveChart=獨立同病路徑 | CX-2(推翻 COMPOSER-1/GROK-N5 的「非消費者→出 scope」) | 裁 codex 勝(monotonicity_tester:43-55 丟 timestamp+chart 位置相減實證):新 Task 2.2 獨立下架該圖(同警示空態);producer 端 quantile_returns 序列標 unverified 或不動(僅 UI 下架,producer 修復歸 1c-FR-FULL,委員 r2 複核此選擇) |
| S-F3 輸出邊界 sanitizer | CX-3+GROK-B3+N1 | 單一 output-boundary sanitizer 覆蓋 API result/detailed CSV/AI/Markdown/export_all/serialization/cache hit:factor_returns 節遞迴**無有限 numeric leaf**(allowlist=status/reason);mutation 綁 sanitizer(注入 finite legacy payload→紅) |
| S-F4 佔位形狀 | CX-4+COMPOSER-7+COMPOSER-2 | 定案:模組頂層單一 §U union `{status:"unavailable", value:null, reason}`(非 per-feature);TS 同構;module_summary 狀態=`unavailable` |
| S-F5 §G 修正 | CX-5+GROK-B4+B2 | 改逐 JSON path 比對(排除 total_execution_time_s/generated_at/壁鐘);M1 改=繞過佔位恢復 `compute_batch` 直出→紅+M1b(config_override/tier 繞道→仍無有限葉);M2 改=sanitizer 注入 finite payload→紅 |
| S-F6 factory/腳本殘留 | CX-6 | consumer gate:`create_factor_return_analyzer` 保留(1c-FR-FULL 要用)但 grep 白名單=analyzer tests+stopgap runner;`scripts/phase29_perf_validation_tmp.py:30` 處置(刪或標 quarantine 註記) |
| S-F7 long_short_analysis 不同病 | CX-7+GROK-④+composer 同 | 出 scope,列 §G unchanged allowlist;其 irregular-subset Sharpe 語意另票(記 ROADMAP 候選) |
| S-F8 reporter sharpe 鍵漂移 | GROK-N2+CX-5 | 附帶記錄:`sharpe` vs `sharpe_ratio` 現值本已 null;止血後 null 契約測試釘死 |

## 下一步
SPEC r2 → 三家閉合 → 戳記 → TODO → 實作(Grok)。

## r2 輪閉合記錄(2026-07-14,Claude 補記)
- codex R2:6/6 原 BLOCKING CLOSED;新 R2-CX-1(default-off=not_run+無節 vs §C 要求 unavailable 佔位/§G 佔位節=互斥,二選一)。
- composer R2:3/3 CLOSED;新 R2-COMPOSER-1(同 default-off 契約矛盾)+R2-COMPOSER-2(Task 1.1 `ic_models` 欄位名錯:實際單數 factor_return)。
- grok R2:4/4 CLOSED;新 R2-B1(`_apply_tier_config` 實在 ic_filter_orchestrator.py:3335/3371 非 ic_analysis_service)+R2-B2(欄位名複數錯)+3 NB(sanitizer 行錨/module_summary 寫入者/頂層計數§G邊界)。
- **r3 裁決(全 ACCEPT)**:S-F9 default-off 契約=**選項 B**(codex/composer 一致):預設關閉維持誠實 not_run+無節;顯式開啟才回佔位 union+summary unavailable(runner 寫入);sanitizer 堵 legacy/cache 有限值;§G 分 default-off + 顯式開啟兩 golden 版本。FACT 更正:_apply_tier_config@orchestrator:3335/3371、ic_models 欄位單數 factor_return、config singular vs summary/results plural 鍵名警示、default-off 現行 not_run 契約(:1603-1610)。§G 頂層計數(completed/skipped count)入排除清單。sanitizer 行錨改 grep 定位(不寫死)。M1 oracle 改「顯式開啟佔位」。
- SPEC r3=v0.3;交三家 r3 閉合。

## r3 輪閉合記錄(2026-07-14,Claude 補記)
- composer r3 APPROVE(0B,4 NB);codex r3 REJECT(4B:CX-1 tier→佔位矛盾/CX-2 unavailable summary 無寫入者/CX-3 force 跨 deep-off/CX-4 §G before 態 enabled 不存在);grok r3 REJECT(1B:B1 同 CX-1 tier 矛盾)+4 NB。
- **r4 裁決(全 ACCEPT)**:S-F10 pure-tier(intermediate/advanced 純 preset)=**not_run 非佔位**(tier 從強制清單排除,不再是顯式開啟路徑;codex CX-1/grok B1);S-F11 顯式開啟(force_modules 或 override enabled=true)→runner **raise ModuleUnavailableError**→父迴圈專屬 except 分支寫 §U union+summary unavailable+不入 errors+不計 completed/skipped(唯一觸父迴圈處,解 CX-2);S-F12 force **不**跨全域 deep-off(CX-3,契約收窄);S-F13 §G before 態用 before.json 實凍值(成功 fixture=completed,非 enabled;CX-4)。NB:sanitizer 行錨改 grep、§V 改寫表草案入 TODO、factory 白名單字面對 repo 校準(grok R3-NB4 交實作查)。
- SPEC r4=v0.4;交三家 r4 閉合。

## 戳記
RECONCILE-STAMP: composer APPROVED 2026-07-14 sha256:66db1109f30b393bf7f307c3671f1889d62f15ef7b5a28dcf2c4d27f92008777 task:IC1CFR-STOPGAP
RECONCILE-STAMP: codex APPROVED 2026-07-14 sha256:66db1109f30b393bf7f307c3671f1889d62f15ef7b5a28dcf2c4d27f92008777 task:IC1CFR-STOPGAP
RECONCILE-STAMP: grok APPROVED 2026-07-14 sha256:66db1109f30b393bf7f307c3671f1889d62f15ef7b5a28dcf2c4d27f92008777 task:IC1CFR-STOPGAP

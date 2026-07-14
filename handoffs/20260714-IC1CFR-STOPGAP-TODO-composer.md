# IC1CFR-STOPGAP-TODO — Adversarial Review (Composer)

> **TASK_ID**: `IC1CFR-STOPGAP-TODO:adversarial`  
> **審查對象**: `docs/IC1CFR_STOPGAP_TODO.md`(基於 Frozen `docs/IC1CFR_STOPGAP_SPEC.md` v1.0)  
> **審查者**: Composer | **日期**: 2026-07-14  
> **方法**: SPEC 逐條對照 TODO + repo 實碼抽驗(唯讀)

## Verdict：五項焦點均有 BLOCKING 缺口 → **REJECT**

---

## ① 前端兩圖下架完整性（FactorReturnChart + FactorEquityCurveChart 三態 oracle）

| 項 | SPEC/TODO 要求 | repo 現況 / TODO 缺口 | 判定 |
|----|----------------|-------------------------|------|
| FactorReturnChart 三態 | Task 2.1:①佔位 ②legacy 有限 ③缺鍵 + vitest 雙測 | 現碼仍畫 `quantile_returns_summary` 數值(`FactorReturnChart.tsx:16-21`);TODO 有 `shows_unavailable_notice`+`legacy_finite_payload_not_rendered` | **PASS(計劃)** |
| FactorEquityCurveChart 三態 | Task 2.2:主流程+deep 皆下架;M4 恒空態 | 現碼用 `report.quantile_returns` 位置相減(`page.tsx:791-794`,`FactorEquityCurveChart.tsx:79-155`);TODO **僅** `equity_curve_unavailable_notice`,**無**對應 `legacy_finite_*` vitest(與 2.1 不對稱) | **B1 BLOCKING** |
| M3/M4 探針歸屬 | §V: M3=FactorReturnChart legacy; M4=equity probe | Task 2.2 將 `test_mutation_m3_render_legacy` 寫在 equity 下(**名稱挪用 M3**);Phase 2 mutation 區**未列 M4** | **B2 BLOCKING**(見⑤) |
| 掛載三態 | Task 2.1「error/loading/empty 三態齊」 | `page.tsx` 僅 `ChartErrorBoundary`;兩圖無 loading prop、無 vitest 覆蓋 loading | **NB1** |

---

## ② types.ts union

| 項 | SPEC S-F4 / §C | TODO Task 2.1 | 判定 |
|----|----------------|---------------|------|
| 模組頂層 §U union | `results.factor_returns={status,value,reason}` **單一物件**,非 per-feature | TODO 寫「FactorReturn 型別=discriminated union」但未改 `ICReport.factor_returns`/`FactorReturnData` 形狀 | **B3 BLOCKING** |
| 現型別 | — | `ICReport.factor_returns?: FactorReturnData`=`Record<feature,{quantile_returns_summary,...}>`(`types.ts:2120,2231-2240`);與後端 union **結構衝突**,build 可能過但語意假綠 | |
| 可複用模式 | — | `ConditionalMetricUnion`(`types.ts:2464-2478`)已存在;TODO 未要求同構 `FactorReturnModuleUnion` 並替換 `ICReport` 欄位 | |
| Equity 路徑 | Task 2.2 獨立同病 | **無** `QuantileReturnData`/equity 掛載型別調整(主流程 `quantile_returns` 仍 finite) | **NB2** |

---

## ③ sanitizer 邊界全覆蓋（legacy/cache）

| 邊界 | SPEC Task 1.2 | TODO Task 1.2 | repo 佐證 | 判定 |
|------|---------------|---------------|-----------|------|
| API serialize | ✓ | grep 掛點 | `_serialize_deep_report`→`get_deep_analysis_result`(`ic_analysis_service.py:1179-722`) | **PASS(計劃)** |
| reporter 六出口 | CSV/AI/Markdown/export_all/detailed | 同左 | `ic_reporter.py:113-361,579-592` | **PASS(計劃)** |
| task cache | cache 命中 | `:1633-1637` 錨點 | **錯锚**:該區為 orchestrator merge cache(`ic_filter_orchestrator.py:1635-1636`),非 API;應含 `task_info["deep_analysis_result"]` 讀寫 + `get_deep_analysis_result` | **B4 BLOCKING** |
| orchestrator in-mem cache | SPEC「cache hit」泛稱 | **未列** | `:1629-1632` 直接 `deepcopy` 返回,可繞過新 runner/sanitizer 洩漏舊有限 `factor_returns` | **B5 BLOCKING** |
| legacy 反例測 | M2 + 各格式 | `test_factor_return_sanitizer_legacy_payload` | 現有 `test_deep_analysis_result_serializes_numpy_scalars` **斷言 finite FR 直通**(`test_ic_deep_analysis.py:274-288`)——與止血矛盾,且未入改寫表 | **NB3** |

---

## ④ §G 兩版本比對可證偽

| 項 | SPEC §G:35 | TODO | 判定 |
|----|------------|------|------|
| before 凍結 | 有限 `results.factor_returns`+summary `completed` | Task 0.1 `--before`+sha256 | **PASS** |
| default-off after | 節缺席+summary `not_run` | Gate B1→B2 一句帶過 | **PASS(意圖)** |
| **顯式開啟 golden** | force 跑:節==§U union+summary unavailable+無 errors | Gate 寫「顯式 union」但 Task 0.1/`ic1cfr_stopgap_freeze.py` **無** `--after-explicit`/`after_explicit.json`/第二 fixture 步驟 | **B6 BLOCKING** |
| 排除清單 | 壁鐘+頂層計數 | Task 0.1 未寫進腳本實作要點 | **NB4** |
| 腳本存在性 | — | `scripts/ic1cfr_stopgap_freeze.py` **尚無**(預期),但雙 golden 契約須在 Task 0.1 凍結 | |

---

## ⑤ 覆蓋追溯無漏

| 追溯聲稱 | 實核 | 判定 |
|----------|------|------|
| Task 0.1/1.1/1.2/1.3/2.1/2.2(6/6) | 同名存在 | **PASS** |
| §C S-F9~F13 | SPEC 正文標號僅 S-F2/3/5/6/9;S-F10~13 為 r4 RECONCILE 裁決 | 追溯字面可接受,但 **S-F4(union 形狀)** 未映射到 Task 2.1 | **NB5** |
| M1/M1b/M2/M3 | Phase 1 列 M1/M1b/M2;M3 錯掛 Task 2.2;**M4 缺失** | **B2**(同①) |
| §V 改寫表 | SPEC §V+RECONCILE「草案入 TODO」 | TODO §0 僅原則,**無逐筆表**;`grep` 命中 6 檔含 `phase26/test_deep_analysis_integration.py`(多處 `completed`/`factor_returns in results`)未列 | **B7 BLOCKING** |
| custom preset 顯式開啟 | r4 NB1:`module_overrides` | `test_explicit_enable` 僅 force+override;未覆蓋 `:3354-3358` | **NB6** |

---

## BLOCKING 摘要（7）

1. **B1** — Equity 圖缺 legacy finite `quantile_returns` vitest oracle(與 Return 圖三態不對稱)  
2. **B2** — M3/M4 mutation 追溯錯位;Phase 2 未列 M4  
3. **B3** — `types.ts` 未對齊模組頂層 §U union(S-F4);仍 per-feature `FactorReturnData`  
4. **B4** — sanitizer cache 錨點錯誤;未覆蓋 API `deep_analysis_result` 讀寫  
5. **B5** — 漏 orchestrator `_deep_analysis_cache` 命中返回(:1629-1632)  
6. **B6** — §G 顯式開啟 golden 未在 Task 0.1/freeze 腳本可操作化  
7. **B7** — §V 改寫表缺失;phase26 等既有測試未追溯  

## 修復建議（最小補丁）

- Task 0.1:freeze 腳本增 `--mode default-off|explicit-enable`;after 跑兩輪比對;排除清單寫死  
- Task 1.2:掛點清單增 `orchestrator._deep_analysis_cache` 讀取、`task_info` 存取;刪錯行號  
- Task 2.1:`FactorReturnModuleUnion` 替換 `ICReport.factor_returns`;對齊 `ConditionalMetricUnion`  
- Task 2.2:增 `legacy_finite_quantile_not_rendered`;M4 probe 獨立命名;M3 僅留 FactorReturnChart  
- 文末增 §V 改寫表(≥`phase26/*`+`test_ic_deep_analysis.py:257-288`+export tests)

---

ASSUMPTIONS_VERIFIED: `FactorReturnChart.tsx`,`FactorEquityCurveChart.tsx`,`page.tsx:790-800`,`types.ts:2120,2231-2240,2464-2478`,`ic_filter_orchestrator.py:1629-1637,3354-3371`,`ic_analysis_service.py:709-722`,`test_ic_deep_analysis.py:257-288`,`tests/phase26/test_deep_analysis_integration.py:96-269`;`scripts/ic1cfr_stopgap_freeze.py`→不存在(預期)
TESTS_RUN: review-only(`rg`/`Read`);未跑 pytest/vitest
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none(審查);TODO 若按現稿實作 TS union 與後端 schema 將漂移
產出檔: `handoffs/20260714-IC1CFR-STOPGAP-TODO-composer.md`

TODO-REVIEW: REJECT(7 BLOCKING)

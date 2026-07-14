# IC1CFR-STOPGAP-TODO — Adversarial Review R3 (Composer)

> **TASK_ID**: `IC1CFR-STOPGAP-TODO`  
> **審查對象**: `docs/IC1CFR_STOPGAP_TODO.md` r3（裁決 `handoffs/20260714-IC1CFR-STOPGAP-TODO-RECONCILE.md` T-S1~T-S12）  
> **審查者**: Composer | **日期**: 2026-07-14  
> **方法**: r1 七項 BLOCKING 逐條對照 r3 TODO + repo 唯讀抽驗 + codex r2 四 B 回歸

## Verdict：**APPROVE** — r1 七 B 全關；codex r2 四 B 已由 T-S9~T-S12 關閉；r3 新掃僅 NB

---

## r1 七 BLOCKING 關閉核對

| ID | r1 缺口 | r3 落點 | 抽驗 | 判定 |
|----|---------|---------|------|------|
| **B1** | Equity 圖缺 legacy finite vitest | Task 2.2:`equity_legacy_finite_not_rendered`+`test_mutation_m4_render_legacy_equity` | 與 2.1 三態對稱 | **CLOSED** |
| **B2** | M3/M4 probe 錯掛、追溯缺 M4 | Task 2.1 M3 / Task 2.2 M4；文末追溯 `M3→2.1、M4→2.2` | 名稱與 §V SPEC 表一致 | **CLOSED** |
| **B3** | `types.ts` 未改 `ICReport.factor_returns` 實形狀 | Task 2.1 T-S4：改 `ICReport.factor_returns`/`FactorReturnData` 為 §U discriminated union；build 驗 tsc | 現碼仍 `FactorReturnData=Record<...>`(預期未實作) | **CLOSED(計劃)** |
| **B4** | sanitizer cache 錨錯；漏 API `deep_analysis_result` | §0+Task 1.2(c)：`task_info`(:678,:827)+`get_deep_analysis_result`(:709)+`_serialize_deep_report` | 現碼錨點存在(`ic_analysis_service.py:668-722,1179`) | **CLOSED** |
| **B5** | 漏 orchestrator in-mem cache 早退 | §0+Task 1.2(a)：`ic_filter_orchestrator.py:1629-1636` `deepcopy→return cached` 必過 sanitizer | 現碼 `:1629-1632` 早退、`1635-1636` merge 皆在錨區 | **CLOSED** |
| **B6** | §G 缺 `--after-explicit` golden | Task 0.1 `--after-explicit`→`after_explicit.json`；Gate B1→B2 三版本 | freeze 腳本尚無(預期)但契約可操作 | **CLOSED** |
| **B7** | §V 改寫表缺失 | Phase 1 §V 表 7 筆+「grep 補漏」；覆蓋 phase26/api/export/reporter | `rg long_short_mean_return\|quantile_returns_summary tests/` 命中 4 檔，表涵 3 檔+phase26 多處；`phase24/test_factor_return_analyzer.py` 為 analyzer 單測(計算不動)→合理出表 | **CLOSED** |

---

## codex r2 四 B 回歸（T-S9~T-S12）

| codex r2 | r3 修訂 | 抽驗 | 判定 |
|----------|---------|------|------|
| B1 sanitizer 檔路徑+七掛點具名測 | T-S9：`momentum/Analysis/factor_return_sanitizer.py`+7 具名 pytest | 路徑定死、掛點(a-g)與 §0 一致 | **CLOSED** |
| B2 `--check-nodeids` 機械 gate | T-S10：§B B2 後端 gate 自跑 suite+差集 exit 1 | 命令可機械判定 | **CLOSED** |
| B3 direct allowlist 漏 `factories.py:454` | T-S11：允許集含 `:454`+B0/測試共用正規化 | `rg FactorReturnAnalyzer\(` 命中 factories/orchestrator/phase24/phase29 | **CLOSED** |
| B4 vitest filter 零測試假綠 | T-S12：三檔具名路徑 | 實跑 `npm --prefix frontend run test -- FactorReturnChart.test.tsx FactorEquityCurveChart.test.tsx NetICChart.test.tsx`→rc=0(僅 NetIC 存在 8 passed)；單跑 FR+Equity 兩檔→rc=1 No test files | **CLOSED(語法)**；見 NB-R3-1 |

---

## r3 新掃（NON-BLOCKING）

| ID | 發現 | 嚴重度 |
|----|------|--------|
| **NB-R3-1** | Gate B2 三檔路徑中 FR/Equity test 檔尚未存在時，vitest 可因 NetIC 單檔 rc=0（M3/M4 未實際被選中）。實作 B2 前須確認三檔皆存在且 M3/M4 測試計數>0 | NB |
| **NB-R3-2** | `export_analysis` JSON 分支 `:437-438` 現 dump `report` 非 `:433-435` 的 `payload_for_export`（deep_report 未併入 JSON）。sanitizer 掛點正確但實作須一併修正序列化對象 | NB |
| **NB-R3-3** | SPEC §G:34 要求比對排除 `completed_count`/`skipped_count` 等頂層計數；Task 0.1 T-S1 僅列時間戳漂移欄+「等漂移欄」。freeze 腳本實作宜凍精確 JSON-path allowlist（codex r2 NB 延續） | NB |
| **NB-R3-4** | `test_explicit_enable_unavailable` 未點名 custom preset `module_overrides.factor_return=true`(`:3354-3358`)；與 override 同歸 unavailable 分支，無繞路（R4 codex NON-BLOCKING 延續） | NB |
| **NB-R3-5** | Task 2.1「loading 三態」仍無 vitest（r1 NB1 延續） | NB |
| **NB-R3-6** | `test_ic_deep_analysis.py:257-288` 已入 §V 表（泛稱注入 finite）；實作時須改為 sanitizer 斷言而非 finite 直通 | NB |

---

## 覆蓋追溯快核

- SPEC Task 0.1/1.1/1.2/1.3/2.1/2.2(6/6)：同名 ✓  
- §G 三版本 + §V 改寫表 + M3/M4 正名：文末追溯 ✓  
- `scripts/ic1cfr_stopgap_freeze.py`：尚不存在（B0 預期產物）✓  

---

ASSUMPTIONS_VERIFIED: `docs/IC1CFR_STOPGAP_TODO.md` r3、`handoffs/20260714-IC1CFR-STOPGAP-TODO-RECONCILE.md` T-S1~S12、`ic_filter_orchestrator.py:1629-1636,1780-1785,3354-3358`、`ic_analysis_service.py:403-444,668-722,1179`、`momentum/factories.py:451-454`、`frontend/src/lib/types.ts:2120,2231-2240,2464-2478`；`rg create_factor_return_analyzer`→唯一 caller `tests/phase26/test_deep_analysis_factories.py`
TESTS_RUN: `npm --prefix frontend run test -- src/components/ic-analysis/FactorReturnChart.test.tsx src/components/ic-analysis/FactorEquityCurveChart.test.tsx src/components/ic-analysis/NetICChart.test.tsx`→rc=0,1 file 8 passed；`npx vitest run` 僅 FR+Equity 兩檔→rc=1 No test files；review-only `rg`/Read
FAILURES_SEEN: none（審查範圍）
SCOPE_CHANGES: none（唯讀+本檔+戳記）
NUMERIC_OR_SCHEMA_IMPACT: none（審查）；實作期 TS union+下架 schema 變更已於 TODO 標記
產出檔: `handoffs/20260714-IC1CFR-STOPGAP-TODO-R3-composer.md`

TODO-REVIEW-R3: APPROVE(0 BLOCKING)

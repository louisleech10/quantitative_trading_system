# IC1CFR-STOPGAP — Adversarial Review R3 (Composer)

> **TASK_ID**: `IC1CFR-STOPGAP:adversarial-r3`  
> **審查對象**: `docs/IC1CFR_STOPGAP_SPEC.md` v0.3 r3  
> **審查者**: Composer | **日期**: 2026-07-14  
> **對照**: r2 `handoffs/20260714-IC1CFR-STOPGAP-R2-composer.md`(2B)、`handoffs/20260714-IC1CFR-STOPGAP-RECONCILE.md` r3 輪補記

## Verdict：r2 兩條 BLOCKING 已關；r3 無新 BLOCKING → APPROVE

---

## r2 兩條 BLOCKING 重跑

| ID | r2 主張 | r3 落點 | 反例重跑 | 判定 |
|----|---------|---------|----------|------|
| R2-COMPOSER-1 / R2-CX-1 | default-off 與 `unavailable` 佔位互斥；Task 1.2「缺鍵不注入」與 §G 佔位 oracle 衝突 | **S-F9 選項 B** §C:23-27 三態互斥；Task 1.1:41-42 預設維持 `not_run`+無節；§G:33-34 分 default-off / 顯式開啟雙 golden；測試 `test_default_off_not_run`+`test_explicit_enable_placeholder` | `ic_filter_orchestrator.py:1655-1656` disabled 不入 runner；`:1694-1696` setdefault `not_run`；`:1603-1610` tier 全關亦 `not_run`；Task 1.2:48「缺鍵不注入」與選項 B 一致（僅顯式路徑建節） | **CLOSED** |
| R2-COMPOSER-2 | Task 1.1 寫 `factor_returns` 複數，實碼單數 `factor_return` | §A:13-14 單數警示+config/results 鍵名分離；Task 1.1:41 `` `factor_return: bool=False`(單數) `` | `api/models/ic_models.py:22` `factor_return: bool = True`；`ic_analysis_service.py:1141` 映射 `modules.factor_return`；`MODULE_ENABLED_PATHS` 鍵 `factor_return` vs runner 名 `factor_returns` 已在 §A 明示 | **CLOSED** |

---

## r2 MAJOR 殘留複核

| ID | r2 | r3 | 判定 |
|----|-----|-----|------|
| R2-COMPOSER-3 | §A 錯掛 `ic_analysis_service`；Task 1.1 缺 orchestrator | §A:13 `_apply_tier_config@orchestrator:3335/3371`；Task 1.1:41 列 `ic_filter_orchestrator.py` tier+`_run_factor_return` | **CLOSED** |
| R2-COMPOSER-4 | §G 無 Phase 0 具名 task；`before.json` MISSING | §G:32 仍「動工前跑」無 Task 0.1；`test -f handoffs/ic1cfr_stopgap_baseline/before.json`→**MISSING** | **OPEN (NB)** |
| R2-COMPOSER-5 | 改寫表未列舉 | §V:77 仍「逐筆列」；`rg` 命中 4 檔未寫入 SPEC | **OPEN (NB)** |
| R2-NB2 (grok) | 誰寫 `module_summary=unavailable` | §C:25-26+Task 1.1:41 標 runner 路徑寫入 unavailable；但 orchestrator 成功迴圈 `:1667` 仍一律 `completed`——oracle 在 §G/測試已釘，實作須加 branch | **PARTIAL→NB** |

---

## r3 新洞掃描

### R3-NB1 — §G Phase 0 baseline 仍無具名 task **NON-BLOCKING**

- §G:32 要求動工前凍 `before.json`，無 Task 0.1 / 捕獲命令 / 負責 Phase。
- 實測 baseline 檔仍不存在；不阻斷 Phase 1 開工，但 golden 腳本首次跑前須補捕獲步驟（建議 TODO 生後補 Task 0.1）。

### R3-NB2 — §V 改寫表仍無草案 **NON-BLOCKING**

- `rg -n "long_short_mean_return|quantile_returns_summary" tests/` → 4 檔：`test_export_formats.py`、`test_export_api.py`、`phase24/test_factor_return_analyzer.py`、`phase26/test_ic_reporter_deep_analysis.py`。
- SPEC 仍只要求「逐筆列」；實作期可 grep 自補，非契約矛盾。

### R3-NB3 — `module_summary` 寫入機制措辭不精 **NON-BLOCKING**

- `_run_factor_return` 僅回傳 dict，無法直接寫 `module_summary`；`:1667` 成功路徑固定 `completed`。
- §C/§G②/`test_explicit_enable_placeholder` 已要求顯式開啟→`unavailable`；執行端需在 orchestrator loop 對佔位 union 映射 summary（或等價 sentinel），非 SPEC 邏輯矛盾。

### R3-NB4 — cache/legacy sanitizer 與 `module_summary` 一致性 **NON-BLOCKING**

- §C 第三子彈+Task 1.2 覆蓋 finite payload→佔位與 reporter 三欄→null；未明示 cache 命中時 `module_summary.factor_returns` 是否由 `completed` 改寫 `unavailable`。
- 輸出邊界 sanitizer 若只改 `results.factor_returns`，模組狀態徽章可能短暫不一致；M2 oracle 以「無有限葉」為主，可實作時一併收斂。

### 已掃、不開 BLOCKING

| 焦點 | r3 判定 |
|------|---------|
| CX-2 EquityCurve Task 2.2 | **PASS**（維持 r2 閉合） |
| S-F3 sanitizer 邊界 | **PASS**（Task 1.2 grep 定位+冪等+M2） |
| singular/plural 鍵名 | **PASS**（§A:14 警示） |
| tier 強制 true 排除 | **PASS**（Task 1.1:3371 排除 `factor_return`） |
| M1/M1b/M2/M3/M4 可證偽 | **PASS** |
| long_short 出 scope | **PASS** |
| force_modules 鍵 `factor_returns` | **PASS**（與 runner 表鍵一致） |

---

## 覆蓋追溯

| 焦點 | r3 判定 |
|------|---------|
| ① 前端下架 | **PASS** |
| ② CSV / sanitizer | **PASS** |
| ③ §U / 三態契約 | **PASS**（選項 B 閉合 r2 最大洞） |
| ④ long_short 同病 | **PASS** |
| ⑤ 可證偽 | **PASS**（NB：baseline 捕獲步驟待 TODO） |

---

ASSUMPTIONS_VERIFIED: `ic_filter_orchestrator.py:1603-1610,1651-1696,1779-1785,3335-3371`; `ic_models.py:22`; `ic_config_schema.py:172-173`; `config/ic_config.yaml:115-116`; `icAnalysisStore.ts:107,133,151`; `ic_analysis_service.py:1141`; SPEC r3 §C S-F9 / Task 1.1 / §G 雙 golden
TESTS_RUN: `sed`/`rg`/`test -f` 上述路徑；`test -f handoffs/ic1cfr_stopgap_baseline/before.json`→MISSING；review-only 未跑 pytest/vitest
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（審查）；r3 定案 default-off=not_run+無節、顯式開啟=佔位+unavailable
產出檔: `handoffs/20260714-IC1CFR-STOPGAP-R3-composer.md`

SPEC-REVIEW-R3: APPROVE(0 BLOCKING)

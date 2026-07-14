# IC1CFR-STOPGAP SPEC r2 閉合 — Grok(2026-07-14)

**task-id**: IC1CFR-STOPGAP  
**角色**: r1 原委員(grok) r2 重跑  
**對象**: `docs/IC1CFR_STOPGAP_SPEC.md` v0.2 r2  
**裁決來源**: `handoffs/20260714-IC1CFR-STOPGAP-RECONCILE.md` S-F1~S-F8  
**模式**: 唯讀(僅本檔寫入;REJECT 故不 stamp)

---

## 方法(可重現)

| 步 | 證據 |
|----|------|
| 讀 r1 自寫 4B + RECONCILE + SPEC r2 | 文件 |
| 核 B1 四處預設+`:193` | `sed`/`nl`:`ic_config_schema.py:172-173` enabled=True;`config/ic_config.yaml:115-116`;`ic_models.py:22` `factor_return: bool = True`;store `:107,:133,:151`;`:192-194`=trend dimensions |
| 核 tier 強制 true | `rg _apply_tier_config` → **`ic_filter_orchestrator.py:3335`**, force-true 迴圈 **`:3369-3371`**; `ic_analysis_service.py` 僅 1541 行、**無**此函式 |
| 核 B2/M1 寫法 | SPEC §V M1/M1b 對 RECONCILE S-F5 |
| 核 B3 整模組+sanitizer+Q 圖 | §C/§G/Task1.2/2.1; `FactorReturnChart.tsx:19` 仍吃 `quantile_returns_summary` |
| 核 B4 meta 排除 | §G 排除清單+scope-expected |
| 核 S-F2 equity | `FactorEquityCurveChart.tsx:79,92-110,143-155` 位置 high-low;page `:790-794`;monotonicity 丟 timestamp 累積序列 |
| 核 Task 1.1 欄位名 | `DeepAnalysisModules.factor_return`(單數) vs SPEC 寫 `factor_returns` |

---

## r1 四條 BLOCKING 逐條判決

### B1 — FACT/Task1.1 錯誤編輯目標 `:193` → **CLOSED**

| 檢查項 | r2 | 實測 |
|--------|-----|------|
| FACT 改指 enabled | `:172-173` FactorReturnConfig.enabled | 真 |
| `:193` 不動聲明 | trend dimensions 字串,本票不動 | 真(`:192-194`) |
| 四處預設 | schema/yaml/ic_models/store | 行號均命中 true 預設 |
| Task1.1 刪「:193 清單移除」 | 無此指令 | 真 |

原危害(改 dimensions 不關模組)已消除。  
**殘差升級為新洞 R2-B1**(見下):r2 把 `_apply_tier_config:3369-3371` 誤掛在 `ic_analysis_service.py`。

### B2 — M1 與「顯式開啟仍佔位」互斥 → **CLOSED**

| r1 要求 | r2 |
|---------|-----|
| M1=繞過佔位 / 恢復 `compute_batch` 直出→紅 | §V M1 + probe `test_mutation_m1_restore_compute_batch` |
| M1b=override/API/tier 開啟仍無有限葉 | §V M1b + `test_all_enable_paths_placeholder` + tier exclusion probe |

與 Task1.1「顯式開啟/force/tier 皆佔位」邏輯一致,可證偽。

### B3 — §G denylist 窄 + 非整模組佔位 → **CLOSED**

| r1 要求 | r2 |
|---------|-----|
| 整模組佔位、遞迴無有限 numeric leaf | §C/§G② allowlist=`status`/`reason`+`value:null` |
| 覆蓋 UI 實畫 `quantile_returns_summary` | 佔位後無有限葉;Task2.1 legacy 不畫 |
| sanitizer 邊界 | Task1.2 + M2 注入 finite legacy |
| (附帶) equity 同病 | S-F2→Task2.2 獨立下架(推翻 r1 N5「非消費者」;codex 實證本輪複核:**成立**) |

r1 N5 撤回:equity curve 為**獨立同病路徑**(monotonicity 序列丟 timestamp + chart 位置相減),納入 scope 正確。

### B4 — §G 未排除時間/計數 meta → **CLOSED**(原修法項)

| r1 修法 | r2 |
|---------|-----|
| 非 byte;比 `results[module]` | 逐 JSON path |
| 排除 `total_execution_time_s`/`generated_at`/壁鐘 | 寫死排除清單 |
| `module_summary.factor_returns` scope-expected | 有 |
| atol=0 | 有 |

**殘差 NB**(不升級 BLOCKING):若比對腳本掃**整包** deep JSON 而非僅 `results[*]`,則 `completed_count`/`skipped_count`/`deep_analysis_summary.completed` 在 `module_summary.factor_returns→unavailable` 時必漂——建議在 §G 明示「頂層計數屬 scope-expected 或排除」。依字面「`results[module]` 本體」可解讀為不比頂層計數 → 原 B4 關閉。

---

## r2 新洞

### R2-B1 — FACT 誤標 `_apply_tier_config` 所在檔 **BLOCKING**

- **SPEC 寫**:`ic_analysis_service.py::_apply_tier_config:3369-3371`
- **實測**:
  - `api/services/ic_analysis_service.py` = **1541 行**,無 `_apply_tier_config`
  - 真身=`momentum/Analysis/ic_filter_orchestrator.py:3335` def;中間/進階 preset 全模組 `enabled=True` 在 **`:3369-3371`**
- **危害**:同 B1 類——執行端依 FACT 開錯檔/改不到 tier 強制 true;中階 preset 會把 schema 預設 false **打回 true**(仍靠 runner 佔位止血,但「預設關閉+tier 例外」產品閘失效,且 M1b tier probe 對不到正確編輯點)。
- **修法**:FACT+Task1.1 改 `ic_filter_orchestrator.py:_apply_tier_config`(`:3369-3371` 迴圈內對 `factor_return` section 跳過強制 true,或 force 後再寫回 false——二擇一寫死)。

### R2-B2 — Task1.1 API 欄位名複數錯誤 **BLOCKING**

- **SPEC Task1.1**:`api/models/ic_models.py:21-29` `factor_returns: bool=False`
- **實測**:`DeepAnalysisModules.factor_return: bool = True`(**單數**,`:22`);全棧 override 鍵亦為 `factor_return`(service `:1141`)
- **危害**:執行端若照字面新增/改 `factor_returns` 欄 → 與 Pydantic/前端 `factor_return` 脫鉤,「API 預設關閉」靜默無效。
- **修法**:改寫為 `factor_return: bool = False`(單數);全文區分 config 鍵 `factor_return` vs results 鍵 `factor_returns`。

### R2-NB1 — Task1.2 sanitizer 行錨部分失準 **NON-BLOCKING**

- 標 `:433-468`=export 分流(可用);`:1198` 實為 `_attach_cross_symbol_context`,**非** FR 序列化主閘。
- API 主路徑應釘:`_serialize_deep_report`(`:1179-1191`)+`get_deep_analysis_result`(`:709-722`)+export `:433+`+reporter 各出口。
- §C 已要求覆蓋 API result;行錨錯但不致改錯語意檔——建議 r3 修正錨點,不單列 BLOCKING。

### R2-NB2 — Task1.1 未逐步寫「誰寫 module_summary=unavailable」 **NON-BLOCKING**

- 現況 runner 成功後 orchestrator **一律** `module_summary[m]="completed"`(`:1667`)。
- §C 契約=`unavailable`;僅改 `_run_factor_return` 回傳佔位不夠。
- 執行端讀 §C 應能補;建議 Task1.1 加一步:佔位成功路徑寫 summary / 或 runner 回傳可識別 sentinel 由 loop 映射。

### R2-NB3 — `completed_count` 與 §G 邊界 **NON-BLOCKING**

- 見 B4 殘差;請在比對腳本契約一句話釘死範圍。

### 已掃、不開洞

| 項 | 裁定 |
|----|------|
| M1/M1b/M2/M3/M4 | 可證偽,閉合 B2 |
| long_short_analysis | 維持不同病,出 scope(與 r1④一致) |
| Task2.2 UI-only、不動 monotonicity 本體 | 可接受;主鏈 `QuantileReturnChart` 吃分位 mean(mask 對齊),非位置 L-S,勿誤下架 |
| factory 保留+phase29 quarantine | 與 S-F6 一致;`phase29` 直呼 `FactorReturnAnalyzer` 存在 |
| force_modules 鍵 `factor_returns` | Task1.1 邊界① 複數正確(runner 表鍵) |
| S-F8 sharpe 鍵 | null 契約可接受 |

---

## 總評

r2 對 grok r1 的 **B1–B4 原訴求均已對症落地**(行號 enabled、M1 互斥重寫、整模組無有限葉+sanitizer、§G 去壁鐘+path 比對),方向與 RECONCILE S-F1~S-F8 一致,equity 納入亦正確。

**不可 APPROVE**:r2 在修 B1 時引入兩處**與 B1 同型**的可執行錯誤——(1) tier 函式掛錯檔 (2) API 模組欄位複數錯名。任一带進實作會造成「以為關了其實沒關到正確開關」的靜默失敗。

```
ASSUMPTIONS_VERIFIED: schema:173 enabled;yaml:115-116;ic_models factor_return 單數:22;store 107/133/151;_apply_tier_config 在 orchestrator:3335/3369-3371 非 service;FactorReturnChart 吃 Q summary;EquityCurve 位置 high-low;M1/M1b 文案閉合 r1 B2;§G 排除壁鐘
TESTS_RUN: 靜態 nl/sed/rg 行號與呼叫圖(未跑 pytest;審查票)
FAILURES_SEEN: none
SCOPE_CHANGES: none(唯讀+本產出)
NUMERIC_OR_SCHEMA_IMPACT: none
```

SPEC-REVIEW-R2: REJECT(2 BLOCKING)

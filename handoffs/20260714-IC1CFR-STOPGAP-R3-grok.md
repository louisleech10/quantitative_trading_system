# IC1CFR-STOPGAP SPEC r3 閉合 — Grok(2026-07-14)

**task-id**: IC1CFR-STOPGAP  
**角色**: r2 原 REJECT 委員(grok) r3 重跑  
**對象**: `docs/IC1CFR_STOPGAP_SPEC.md` **v0.3 r3**  
**裁決來源**: `handoffs/20260714-IC1CFR-STOPGAP-RECONCILE.md` r2 輪補記(S-F9 選項 B)  
**模式**: 唯讀(僅本檔寫入;REJECT 故不 stamp RECONCILE)

---

## 方法(可重現)

| 步 | 證據 |
|----|------|
| 讀 r2 自寫 2B+3NB + RECONCILE r2 補記 + SPEC r3 | 文件 |
| 核 R2-B1 檔/行 | `nl`: `_apply_tier_config` **def@orchestrator:3335**; force-true **`:3371`**; `ic_analysis_service.py` 1541 行、**無**此函式 |
| 核 R2-B2 單數欄位 | `api/models/ic_models.py:22` `factor_return: bool = True`; Task1.1/§A 寫單數 False |
| 核 singular vs plural | config 鍵 `factor_return`(MODULE_ENABLED_PATHS:61; schema/yaml); results/summary 鍵 `factor_returns`(`:1604`,`:1639`,`:1731`) |
| 核 default-off 現行契約 | deep 整包 off:`:1603-1610`; 單模組 off: runner 不入列 `:1651-1657` + setdefault `not_run` `:1694-1696` |
| 核 R2-NB1 sanitizer | Task1.2 改 `grep` 定位、不寫死行號 |
| 核 R2-NB2 writer | §C/Task1.1 明列 summary=`unavailable`、寫入者=runner 路徑 |
| 核 R2-NB3 §G 計數 | 排除 `completed_count`/`skipped_count`/`deep_analysis_summary.completed` |
| 掃 r3 新洞 | Task1.1 邊界③ vs 選項 B+tier 排除; loop `:1667`; factory 白名單字面 |

---

## r2 五條閉合判決

### R2-B1 — `_apply_tier_config` 掛錯檔 → **CLOSED**

| 檢查項 | r3 | 實測 |
|--------|-----|------|
| §A 檔名 | `ic_filter_orchestrator.py::_apply_tier_config` | 真;service 無此函式 |
| def / force-true 行 | def@:3335, 強制 true@:3371 | `nl` 命中 `:3371` `data[section][field] = True` |
| Task1.1 編輯點 | 同 orchestrator:3371 對 `factor_return` 排除 | 與 FACT 一致 |
| 標 GROK-R2-B1 更正 | 有 | 真 |

原危害(開錯檔改不到 tier 強制 true)已消除。

### R2-B2 — API 欄位複數錯名 → **CLOSED**

| 檢查項 | r3 | 實測 |
|--------|-----|------|
| Task1.1 | `factor_return: bool=False`(**單數**) | 對齊 `DeepAnalysisModules.factor_return:22` |
| §A 警示 | config 單數 vs summary/results 複數 | `factor_return` enabled 路徑 vs `factor_returns` runner/summary 鍵 |
| force_modules 複數 | 邊界① `["factor_returns"]` | runner 表鍵正確 |

原危害(改錯欄靜默無效)已消除。

### R2-NB1 — sanitizer 行錨失準 → **CLOSED**

Task1.2:「執行端以 `grep -n ...` 定位精確行,r3 不寫死可能過時的行號」。覆蓋面仍列 API/CSV/AI/Markdown/export_all/反序列化/cache。行錨過期類洞關閉。

### R2-NB2 — module_summary=unavailable 寫入者 → **CLOSED**(殘差見 R3-NB2)

§C 定案「寫入者=runner 本身」+ Task1.1 明列佔位成功時 `module_summary.factor_returns="unavailable"`;§G 顯式開啟 golden 要求 summary==`unavailable`;M1/測試 oracle 可證偽。  
**殘差(不升級復開)**:現行成功路徑 loop **`:1667` 一律 `"completed"`**,runner 函式只 return dict、無 `base_report` 把手——實作必同時改 loop 映射(或等价),SPEC 未點名 `:1667`。見 R3-NB2。

### R2-NB3 — 頂層計數 §G 邊界 → **CLOSED**

§G 排除清單寫死含 `completed_count`/`skipped_count`/`deep_analysis_summary.completed` 等(因 factor_returns 狀態改變必漂)。原 B4 殘差關閉。

### 附:S-F9 default-off 契約(r2 他家 B,本家複核)

選項 B 三態互斥與碼一致:
- 未啟用 → `not_run`+不建 `results.factor_returns`(1651-57/1694-96)
- 顯式開啟 → 佔位 union+summary `unavailable`(待實作)
- 邊界 sanitizer 堵 legacy/cache 有限葉

§G 分 default-off / 顯式開啟兩 golden — 與選項 B 對齊。**但 Task1.1 邊界③ 與該契約互斥 → 新 B**(下節)。

---

## r3 新洞

### R3-B1 — Task1.1 邊界③「tier→佔位」與選項 B + tier 排除互斥 **BLOCKING**

**矛盾鏈(r3 自身)**:
1. §C / S-F9 選項 B:預設關閉(不 force/override/**tier**)→ **誠實 `not_run`+無節**
2. Task1.1:四處預設 `False` + `_apply_tier_config:3371` 對 `factor_return` **排除 tier 強制 true**
3. 實測後果:schema/yaml/API modules 預設 false、intermediate/advanced 不再把該模組打回 true → `_is_module_enabled` false → **不入 `run_targets`** → summary `not_run`、無 `results.factor_returns`
4. 同 Task 邊界③卻寫:**「intermediate/advanced tier→佔位(排除生效)」**
5. §C 顯式開啟括號仍列「**tier 強制**」——與「本模組排除 tier 強制」衝突

**反例(可構造)**:
- 實作嚴格依 1–2 改碼後,跑「僅 active_preset=intermediate、無 force_modules、無 modules/override 開 FR」→ 觀測 **not_run+無節**
- 依邊界③ / 誤讀「tier 屬顯式開啟」寫的 `test_all_enable_paths_placeholder` 期望 **佔位+unavailable** → 紅;或為過測而**不做** tier 排除、只靠 runner 佔位 → 破壞「預設關閉」產品閘(中階仍 force-true 後跑 runner,summary 語意變 completed→需再映 unavailable,且與選項 B「不 force 則 not_run」不符)

**修法(須寫死唯一 oracle)**:
- 邊界③改為:`intermediate/advanced`(僅 preset、無 force/modules/override 開啟)→ **`not_run`+無節**(證明排除生效)
- §C 顯式開啟列表:**刪「tier 強制」**或註「Task1.1 後 factor_return 不再被 tier force-true;tier 排除後非顯式路徑=not_run」
- M1b / mutation:`drop_tier_exclusion` → 排除被拿掉後 intermediate 會 enable → 仍**無有限葉**(佔位);排除存在時 pure-tier → **not_run**(可另函式,勿與 佔位 混期望)

### R3-NB1 — §G(2) before 態寫 `enabled→not_run` **NON-BLOCKING**

`module_summary` 實際取值=`completed`/`not_run`/`skipped`/`unavailable`(目標),**從無字面 `"enabled"`**。default-on 現況 before 應為 **`completed→not_run`**(default-off 後)。易誤導 golden 腳本作者;不阻 fail-close 數值,但應改字。

### R3-NB2 — summary 寫入機制未釘 loop `:1667` **NON-BLOCKING**(R2-NB2 殘差)

Task1.1 稱 runner 寫 `module_summary=unavailable`,但架構上 summary 由 orchestrator 成功分支 `:1667` 寫死 `"completed"`。建議加一句:「佔位結果(頂層 `status==unavailable`)時成功路徑映 summary=`unavailable`,勿留 `completed`」。測試已要求 summary 值 → 假綠風險低。

### R3-NB3 — §A default-off 行錨偏 deep-整包 **NON-BLOCKING**

§A 引 `:1603-1610` 稱「模組未啟用」——該段是 **`_is_deep_analysis_enabled` false**(整包 deep off)的全模組 `not_run` 表。  
**單模組** default-off 真錨=`:1651-1657`(不入 runner)+`:1694-1696`(setdefault not_run)+不寫入 `results`。契約文字對、錨點易誤導。

### R3-NB4 — Task1.3 factory 白名單字面與 repo 不符 **NON-BLOCKING**

`rg create_factor_return_analyzer`:定義在 `factories.py`;**唯一測試 caller**=`tests/phase26/test_deep_analysis_factories.py`。  
orchestrator runner **直例化** `FactorReturnAnalyzer`(`:1780-1785`),**不**呼 factory;phase29 亦直例化。  
白名單寫「analyzer tests+orchestrator runner」字面不準——應含 phase26 factory 測試、並釐清 gate 是 grep factory 還是連直例化。意圖(阻新 production caller)可讀,執行端需自補。

### 已掃、不開洞

| 項 | 裁定 |
|----|------|
| 四處預設 true 行號(schema:173/yaml:115-116/ic_models:22/store:107,133,151) | 仍真;Task 改 False 目標正確 |
| `:193` trend dimensions 不動 | 真(`dimensions` 含字串 factor_return,非 enabled 開關) |
| Equity curve 獨立同病 | 複核成立(monotonicity 丟 timestamp+chart 位置 high-low/Sharpe);Task2.2 必要 |
| Option B 雙 golden + sanitizer 冪等 + value:null union | 可證偽、與 1c §U 同構方向正確 |
| long_short_analysis 出 scope | 維持 |
| M1=繞過佔位恢復 compute_batch | 與「顯式開啟仍佔位」一致 |
| analyzer `:70-71` reset_index + `:87` 位置相減 | bug 仍在;本票不動本體正確 |
| 不 stamp | REJECT 故未改 RECONCILE |

---

## 總評

r3 **完整收下** grok r2 的 2 BLOCKING + 3 NB 之修法方向(orchestrator 行錨、單數欄位、singular/plural 警示、sanitizer grep、summary 寫入者聲明、§G 頂層計數排除、選項 B 三態)。r1→r2 原訴求無復開。

**不可 APPROVE**:Task1.1 **邊界③** 與 S-F9 選項 B +「tier 排除 force-true」在可執行 oracle 上**互斥**(pure intermediate → 實為 `not_run`,SPEC 寫 `佔位`)。此為與 r2-B1/B2 同型的「執行端照字面會寫錯測/錯行為」洞,須 r4 一句話釘死後再 stamp。

```
ASSUMPTIONS_VERIFIED: R2-B1 orchestrator:3335/3371;R2-B2 factor_return 單數:22;plural results:1604/1639;default-off 1651-57+1694-96;store 107/133/151;§G 計數排除;sanitizer grep 無死行號;Equity 位置相減仍成立
TESTS_RUN: 靜態 nl/sed/rg 行號與呼叫圖(未跑 pytest;審查票)
FAILURES_SEEN: none
SCOPE_CHANGES: none(唯讀+本產出)
NUMERIC_OR_SCHEMA_IMPACT: none(審查);R3-B1 要求 pure-tier oracle=not_run 非佔位
產出檔: handoffs/20260714-IC1CFR-STOPGAP-R3-grok.md
RECONCILE_STAMP: not applied (REJECT)
```

SPEC-REVIEW-R3: REJECT(1 BLOCKING)

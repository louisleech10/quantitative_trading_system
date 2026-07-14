# IC1C-B2 Code Review (Composer)

**task-id**: IC1C-B2  
**reviewer**: composer (code reviewer)  
**date**: 2026-07-14  
**scope**: Grok B2 實作 — `git diff HEAD` + `handoffs/IC1C-B2-RESULT.md`  
**authority**: Frozen `docs/IC1C_NETIC_TODO.md` Phase 2 (Tasks 2.1–2.2) + `docs/IC1C_NETIC_SPEC.md` §U  
**method**: 唯讀 diff/源碼對照 + 獨立 gate 複跑

---

## Phase 2 逐 Task 驗收

### Task 2.1 — API typed request + HTTP 422

| 檢查項 | 結果 | 證據 |
|--------|------|------|
| `NetICAnalysisRequest` + 非 None 一律驗域 | PASS | `api/models/ic_models.py:33-53`；`test_cost_bps_range_422` unit_cases |
| `cost_enabled=True` 缺 bps → 422 | PASS | HTTP case + unit `cost_bps=None` |
| `cost_bps=0`/1000.1/NaN/inf → 拒 | PASS | HTTP(0/1000.1) + unit(NaN/inf/0) |
| `DeepAnalysisRequest.net_ic` 預設 `cost_enabled=False` | PASS | `Field(default_factory=NetICAnalysisRequest)` |
| T-F12 雙入口 `config_override.net_ic_analysis` 整節 reject | PASS | `DeepAnalysisRequest` + `ICAnalyzeRequest` validators；`test_config_override_net_ic_rejected` |
| `_build_deep_module_override` typed 最後注入 | PASS | `base` 先 pop `net_ic_analysis`，`_deep_merge(base, typed)`；`test_build_deep_module_override_typed_last` |
| request 欄 `net_ic` → config 鍵 `net_ic_analysis` 映射 | PASS | `ic_analysis_service.py:1149-1155` |
| T-F16 union 序列化保三鍵 | PASS | `_CONDITIONAL_METRIC_KEYS` + 三鍵分支；`test_e2e_unavailable_union_shape` `allow_nan=False` |
| 舊 request 無 `net_ic` → GROSS_ONLY | PASS | `test_legacy_request_gross_only` |
| 7bps fullstack → artifact `cost_bps==7` | PASS | `test_cost_bps_fullstack_wiring` |
| M7/M10 API probes | PASS | `test_mutation_m7_*` / `test_mutation_m10_api_*`；mutation_probe_check 4/4 |
| M4 backend passthrough probe | PASS | `test_mutation_m4_drop_cost_passthrough` |
| `types.ts` request 同構 | PASS | `NetICAnalysisRequest` + `DeepAnalysisConfig.net_ic` |

### Task 2.2 — 前端全鏈 + G-NEW2

| 檢查項 | 結果 | 證據 |
|--------|------|------|
| DeepAnalysisConfigPanel 啟用成本 + bps | PASS | checkbox `net-ic-cost-enabled` + input `min=0.1` `step=0.1` |
| store `netIcConfig` + `buildDeepAnalysisRequest` | PASS | `icAnalysisStore.ts:28-29,262-275` |
| useICAnalysis payload 帶 `net_ic` | PASS | `useICAnalysis.ts:328` |
| page wiring + report flatten | PASS | `buildDeepAnalysisRequest`；`moduleResults` 展平至 `deepAnalysisReport` |
| NetICChart 刪硬編 5bps/scenarios/0.1 | PASS | 靜態 grep `useState(5)|turnover ?? 0.1` → 0 |
| Y 軸/標題 `cost_drag_return` | PASS | `NetICChart.tsx:179`；禁「Net IC」軸名 |
| scenario 自後端 `cost_sensitivity` | PASS | `scenarioOptions` useMemo |
| FeatureTierPanel 文案正名 | PASS | 「成本拖累(報酬空間)」 |
| T4 vitest 五具名 + m4 probe | PASS | `NetICChart.test.tsx` 5/5 |
| G-NEW2 三段 bootstrap | PASS | `freeze_new2()` 1a/1b/1c；產出 `g_new2.{json,sha256}` |
| `npm run build` | PASS | RESULT build_exit=0（reviewer 未重跑 build，vitest+pytest 已綠） |

---

## 五項重點稽核

### ① 前端全鏈三欄（UI / store / types）防幽靈

**PASS**

| 欄位 | types.ts | store | UI / hook |
|------|----------|-------|-----------|
| `cost_enabled` | `NetICAnalysisRequest` | `netIcConfig` | `DeepAnalysisConfigPanel` checkbox |
| `cost_bps` | 同上 `number \| null` | `setNetIcConfig` / `buildDeepAnalysisRequest` | bps input（enabled 時顯示） |
| request 鍵名 `net_ic` | `DeepAnalysisConfig.net_ic` | `buildDeepAnalysisRequest.net_ic` | `useICAnalysis.startDeepAnalysis` |
| 模組鍵 `net_ic_analysis` | `DeepAnalysisModules` | `deepAnalysisModules` | panel 模組列 + `page` `data=` |
| §U union 輸出 | `ConditionalMetricUnion` on 3 metrics | — | `NetICChart` 不讀裸 `profitable` |

無 `useState(5)` / `default_cost_bps` / turnover `0.1` fallback 殘留。`buildDeepAnalysisRequest` 與 hook 雙路皆帶 `net_ic`，m4 前後端 probe 可偵測 drop。

### ② T4 三態 oracle + m4 前端 probe 自證

**PASS**

| 具名測試 | oracle | 結果 |
|----------|--------|------|
| `sends_cost_bps` | UI/store 7 → payload `cost_bps:7` | PASS |
| `shows_error_on_422` | `formError` 含 `cost_bps` 文案可見 | PASS（元件級；見 NB-1） |
| `shows_empty_on_all_skipped` | `netic-empty` 非 spinner | PASS |
| `shows_no_data_when_turnover_missing` | 空態 + 無 scatter 點 | PASS |
| `test_mutation_m4_frontend_drop_cost` | patch builder 丟 cost → assert 紅 | PASS（真自證：外層 `expect().toThrow()`） |

後端 `test_mutation_m4_drop_cost_passthrough` 與 `test_cost_bps_fullstack_wiring` 互補，覆蓋 API→engine 7bps。

### ③ T5 改寫理由（`default_cost_bps==5`）

**PASS**

- 檔頭 + `test_ic_config_contains_deep_analysis_sections` 註解「舊斷言為何錯」。
- 刪 `default_cost_bps==5`；改斷言 `cost_enabled=False` / `cost_bps=None` / `not hasattr(..., "default_cost_bps")`。
- 新增 `test_net_ic_cost_validator`（0/NaN/inf/上界/enabled 缺 bps）+ `test_mutation_m10_config_drop_validator`。
- YAML fixture 改 `cost_enabled`/`cost_bps`（`test_load_ic_config_three_layer_merge_deep_analysis`）。

### ④ 三處現場調適可接受性

| 調適 | 判定 | 理由 |
|------|------|------|
| NaN/inf 422：HTTP + Pydantic unit 分拆 | **可接受** | JSON 無法字面傳 NaN/inf；`test_cost_bps_range_422` unit_cases 覆蓋 `{disabled,NaN}`/`{enabled,inf}` 等，與 FastAPI 422 同源 validator |
| G-NEW2 允許 `gross_ic` 路徑差 | **可接受（附註）** | G-NEW=freeze spearman vs API=IC `ic_mean` 為既有路徑差；比對仍強制 turnover 等值、`cost_bps==10`、獨立 `_canonical_cost_drag` oracle、除 `gross_ic` 外逐鍵等值 + SCHEMA_COST_ENABLED；符合 SPEC §G「G-NEW2 僅驗 API 傳導」意圖（見 NB-2） |
| `batchDate.test.ts` eslint 最小修 | **可接受** | 刪未用參數解 build gate；SCOPE_CHANGES 已披露；與 IC1C 無行為耦合 |

### ⑤ types.ts union 同構 + 無 conditional 裸表示

**PASS**

- 新增 `ConditionalMetricUnion`；`net_factor_return` / `breakeven_cost_bps` / `profitable_after_cost` 皆為 union。
- 刪舊 `profitable_after_cost?: boolean`、`breakeven_cost_bps?: number`、`cost_sensitivity[].net_ic`。
- `cost_drag_return` / `gross_ic` / `turnover` 為 §U 允許之裸有限數值欄，非 conditional metric。
- `NetICAnalysisRequest.cost_bps?: number | null` 為 request 可選欄，非輸出 union 殘留。

---

## 獨立 gate 複跑（reviewer VERIFY）

```bash
venv/bin/pytest tests/api/test_ic_deep_analysis.py tests/phase24/test_deep_analysis_config.py -q
# → 27 passed in 13.55s

bash scripts/mutation_probe_check.sh tests/api/test_ic_deep_analysis.py tests/phase24/test_deep_analysis_config.py
# → MUTATION-PROBE PASS (4 probes)

npm --prefix frontend run test -- NetICChart --run
# → 5 passed

rg -n "useState\(5\)|turnover \?\? 0\.1|\|\| ?0\.1" frontend/src/components/ic-analysis/NetICChart.tsx
# → 0 matches

rg "default_cost_bps" api/ frontend/src/ config/ic_config.yaml
# → 僅 ic_config_schema docstring 提及「無 default_cost_bps」
```

---

## 非 BLOCKING 備註

1. **T4 `shows_error_on_422`** 為 `DeepAnalysisConfigPanel` 元件級（靜態 `formError` prop）；`page.tsx` 已將 `deepAnalysisStatus==='failed' && error` 接到 `formError`，POST 422 經 `catch→setError` 可達，但無 hook/E2E 單測釘死——建議 B3 前可補一則 MSW 422 測（不阻 B2）。
2. **G-NEW2** 字面偏離 TODO「逐 feature sha256 等值」（因 `gross_ic` 排除），但補強 oracle 充分；應在 RESULT/commit 保留路徑差說明（已寫）。
3. **`buildDeepAnalysisRequest`** `cost_bps` 三元運算兩分支相同（`:271-273`），可後續簡化為單表達式。
4. **`NetICChart` `gross_ic ?? 0`** 為繪圖軸 fallback（非 turnover 幽靈）；若 gross_ic 缺而 turnover 在，會畫在 0——實務上非 skipped feature 必有 gross_ic，風險低。
5. **`batchDate.test.ts`** 超出 TODO 列檔但為 build 阻斷修復；已於 SCOPE_CHANGES 披露。

---

## 裁決摘要

B2 對照 Frozen TODO Phase 2 + SPEC §U：**Task 2.1/2.2 全項 PASS**；前端三欄同構、T4 三態+m4 自證、T5 改寫附理由、三處現場調適均可接受；獨立 gate 27 pytest + 4 mutation + 5 vitest 綠。

CODE-REVIEW: APPROVE (0 BLOCKING)

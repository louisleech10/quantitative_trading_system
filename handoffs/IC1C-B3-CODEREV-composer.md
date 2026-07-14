# IC1C-B3 Code Review (Composer)

**task-id**: IC1C-B3  
**reviewer**: composer (code reviewer)  
**date**: 2026-07-14  
**scope**: Grok B3 — `git diff HEAD`（`NetICChart.tsx` / `docs/API_SPECIFICATION.md` / `tests/conftest.py` / `handoffs/ic1c_baseline/g_new2.*`）+ `handoffs/IC1C-B3-RESULT.md`  
**authority**: Frozen `docs/IC1C_NETIC_TODO.md` Task 3.1 + r7 離線鐵則 + `docs/IC1C_NETIC_SPEC.md` §T/§U  
**method**: 唯讀 diff/源碼對照 + 獨立 gate 複跑

---

## 四項重點稽核

### ① UI 註記（繁中 + gross-only + per_rebalance）

**PASS**

| 檢查項 | 結果 | 證據 |
|--------|------|------|
| 繁中說明文案 | PASS | `NET_IC_COST_SEMANTICS_NOTE` =「成本為每次再平衡(per-rebalance),未年化;不同 timeframe 間不可直接比較」 |
| `per_rebalance` grep=3 | PASS | `grep -n per_rebalance NetICChart.tsx` → 行 15/17/18，count=3 |
| 四態皆顯示註記 | PASS | loading/error → `CardDescription` + `data-testid="netic-cost-semantics-note"`；empty/chart → `<p>` 同 testid；chart Tooltip 內嵌 `netic-tooltip-semantics` |
| gross-only 模式 | PASS | empty：`Gross IC（未啟用成本）` + 註記；chart：`Gross-only 模式（未啟用成本）` + 註記；`hasAnyCost=false` 時 Y 軸 hide、不強求 `cost_drag_return` |
| 後端字面值錨點 | PASS | `NET_IC_COST_SEMANTICS = 'per_rebalance_not_annualized'` export，對齊 `net_ic_analyzer._COST_SEMANTICS` |

**NB-1（非阻斷）**: `NetICChart.test.tsx` 仍無 `netic-cost-semantics-note` / tooltip 可見性斷言；B3 Gate 僅要求 grep≥1，行為已在源碼四態+Tooltip 覆蓋。建議後續補 1–2 則 RTL（對齊 TODOREV ADV 建議）。

### ② `docs/API_SPECIFICATION.md` Net IC 與實作一致

**PASS**

| 契約點 | 文件 | 實作 | 一致 |
|--------|------|------|------|
| typed `net_ic` 驗域 | §14.11.1 | `NetICAnalysisRequest._validate_cost_params` | ✓ |
| 雙入口 reject `config_override.net_ic_analysis` | §14.11.1 422 表 | `DeepAnalysisRequest` + `ICAnalyzeRequest` validators | ✓ |
| §U 三 profile 鍵集合 | §14.11.1 表 | `net_ic_analyzer.batch_analyze` GROSS_ONLY/COST_ENABLED/SKIPPED | ✓ |
| `cost_semantics` / `turnover_semantics` | §14.11.1 | `_COST_SEMANTICS` / `_TURNOVER_SEMANTICS` | ✓ |
| conditional union 三欄 | §14.11.1 | `_unavailable()` → status/value/reason | ✓ |
| 1c-FR unavailable reason | §14.11.1 | `canonical_factor_return_series_not_built (1c-FR)` | ✓ |
| 路由 | §14.11 POST/GET | `api/routes/ic_analysis.py` `/deep-analysis/{task_id}` | ✓ |

**NB-2**: 舊 §14.11「SHAP 解釋」占位已替換為 Deep Analysis + §14.11.1；SHAP 仍在 §10.13/10.14，屬文件糾偏非回歸。

### ③ `tests/conftest.py` 越界裁決（Binance `Client.ping` stub）

**核可（收窄）— 非 BLOCKING**

| 維度 | 裁決 |
|------|------|
| Task 3.1 字面允許檔 | 僅 `NetICChart.tsx` + docs（TODO:135）→ **conftest 字面越界** |
| Frozen r7 離線鐵則 | TODO:20「B2/B3 Gate…`api.main` import 的 Binance ping 須 fixture/conftest 層 stub」→ **Gate 前置授權** |
| B2 審查先例 | `IC1C-B2-CODEREV-codex` B2：無 stub 時 collect/new2 觸外網 FAIL → 本變更閉合該缺口 |
| 實作形態 | 模組載入時 `Client.ping = lambda: {}`，沿用 `ic_persist_redirect` 同層模式；`freeze_new2` 腳本亦自帶 stub（雙重隔離可接受） |
| 收窄建議 | 保留現狀即可過 Gate；長期可收斂為 pytest plugin autouse fixture（獨立技術債，非 B3 阻斷） |

**程序瑕疵（NB-3）**: `IC1C-B3-RESULT.md` 寫 `SCOPE_CHANGES: none`，但 `conftest.py` 確有 diff → 應更正為「r7 離線 enabler」。

### ④ 零 schema / G-NEW2 features byte 等值

**PASS**

```bash
# reviewer 獨立複驗
python3 -c "…"  # HEAD vs working tree result.features → equal: True
venv/bin/python scripts/ic1c_freeze_baseline.py --baseline new2
# → exit 0; sha256=6db9b13e…; compared_features=4 exclude=['hl_range','oc_return','zscore_20']
```

- `result.features` 與 `HEAD:handoffs/ic1c_baseline/g_new2.json` **字節級一致**（重跑後仍 True）。
- 檔案級 sha 變因僅 `git_head`（`2133c77…`→`04ac6fb…`），符合零 payload 變更敘述。
- 未改 `momentum/`、`api/`、`frontend/src/lib/types.ts`（diff 確認）。

**NB-4**: RESULT 內 `features_only_sha256=4f7fbcbc…` reviewer 未能以同標籤重算對照；**不影響**「features dict 等值」主張（已獨立證實）。

---

## 獨立 gate 複跑（reviewer VERIFY）

```bash
grep -c per_rebalance frontend/src/components/ic-analysis/NetICChart.tsx
# → 3

npm --prefix frontend run test -- NetICChart
# → 8 passed

npm --prefix frontend run build
# → exit 0

venv/bin/python scripts/ic1c_freeze_baseline.py --baseline new2
# → exit 0 (reviewer 重跑)
```

---

## 裁決摘要

B3 對照 Frozen Task 3.1：**UI 繁中註記四態+Tooltip、gross-only 正確、per_rebalance=3**；**API 文件 §14.11/§14.11.1 與 `ic_models`/`net_ic_analyzer`/路由一致**；**G-NEW2 features 等值、零 schema**；**conftest stub 依 r7 核可為 Gate enabler**（RESULT 應補記 scope）。

CODE-REVIEW: APPROVE (0 BLOCKING)
